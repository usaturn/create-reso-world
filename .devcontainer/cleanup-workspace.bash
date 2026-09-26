#!/bin/bash
#
# .devcontainer/cleanup-workspace.bash
#
# ディスクを圧迫する使い捨て debris を安全に掃除する。
#   - /tmp/pr-review-* の残骸（pr-review スキルが `worktree` サブディレクトリに
#     git worktree を作る。save 成功時には worktree・session state を
#     自動削除するが、異常終了や cleanup 失敗時には残るため掃除は必要。
#     残骸の大半は「登録されたままの worktree」で、単純な rm -rf は git 側の
#     worktree 登録と不整合を起こすため使えない。なお loose なセッション状態
#     ファイルは pr-review 側の削除対象に含まれないため、ディレクトリの有無と
#     独立に片付ける）
#   - /tmp/review-fix-planning.XXXXXX の残骸（review-fix-planning スキルが mktemp で
#     作る隔離 worktree。スキルは手順 3 の検証直後に自分で worktree remove と親削除を
#     行うが、異常終了時には残るため本スクリプトが安全網として pr-review と同じ
#     安全条件で掃除する。公式 mktemp のドット区切り（review-fix-planning.*）のみ対象。
#     ハイフン区切りの歴史的残骸（-wt / -head.txt 等）は対象外で手動対応）
#
# 安全条件（すべて AND で判断する）:
#   - 未コミット変更のある git 作業ツリーを含むものは削除しない
#   - 使用中（プロセスの cwd）と判定できるものは削除しない
#   - 経過日数のみを削除条件にしない
#   - 冪等に何度でも実行できる。削除した対象と件数を必ず出力する
#   - git worktree として登録済みのものは、上記の安全条件を満たす場合に限り
#     `git worktree remove --force`（1 回。locked worktree は外さない）で
#     git 管理と整合させて撤去する。submodule を update --init した worktree は
#     --force 無しでは `working trees containing submodules cannot be moved or
#     removed` で失敗するため。--force は dirty も消すので、status --porcelain が
#     取得できて空のときにだけ呼ぶ。status 失敗は判定不能として残す。
#     撤去後に残った親ディレクトリ（session.json 等）を削除する
#   - loose なセッション状態ファイル（pr-review-<PR>-*.patch / *session.env /
#     pr-review-<PR>.diff 等、/tmp 直下に置かれるもの）は、ディレクトリの
#     削除有無とは無関係に、実行のたびに独立したパスで TMP_ROOT 全体を
#     走査して片付ける（ディレクトリ削除に従属させると、ディレクトリを
#     自分で消す pr-review の残したファイルが二度と片付かないため）。同じ PR 番号の
#     pr-review-<PR>-* ディレクトリが他に 1 つも残っていない場合に限り、
#     ディレクトリと同じ MIN_AGE_DAYS を満たすものだけ削除する。1 つでも
#     残っていれば、他インスタンスがまだ参照し得るため一切触らない
#
# 環境変数（既定値はコンテナの実運用、テストでは差し替える）:
#   WORKSPACE_CLEANUP_TMP_ROOT       pr-review-* / review-fix-planning.* を探すルート（既定 /tmp）
#   WORKSPACE_CLEANUP_MIN_AGE_DAYS   最終更新からの最小経過日数。0 以下で無効化（既定 1）
#   WORKSPACE_CLEANUP_DRY_RUN        1 で実際には削除・git worktree remove をせず
#                                  対象だけ表示する（既定 0）

set -u

readonly TMP_ROOT="${WORKSPACE_CLEANUP_TMP_ROOT:-/tmp}"
readonly MIN_AGE_DAYS="${WORKSPACE_CLEANUP_MIN_AGE_DAYS:-1}"
readonly DRY_RUN="${WORKSPACE_CLEANUP_DRY_RUN:-0}"

# cleanup_pr_review_dirs が削除した（dry-run では削除するとみなした）ディレクトリ。
# loose ファイルの掃除は「同じ PR 番号のディレクトリがもう残っていないか」で
# 判断するため、dry-run でも実行と同じ結論になるようここに記録する。
REMOVED_PR_DIRS=()

# $1 配下に実行中プロセスの cwd があれば真を返す（現在使用中の判定）。
path_is_in_use() {
    local dir="$1" target proc_cwd link
    target="$(cd "$dir" 2>/dev/null && pwd -P)" || return 1
    [ -n "$target" ] || return 1
    for proc_cwd in /proc/[0-9]*/cwd; do
        [ -e "$proc_cwd" ] || continue
        link="$(readlink -f "$proc_cwd" 2>/dev/null)" || continue
        case "$link" in
            "$target" | "$target"/*) return 0 ;;
        esac
    done
    return 1
}

# $1 が MIN_AGE_DAYS 以上前に更新されていれば真を返す。MIN_AGE_DAYS <= 0 なら常に真。
dir_is_old_enough() {
    local dir="$1"
    if [ "$MIN_AGE_DAYS" -le 0 ] 2>/dev/null; then
        return 0
    fi
    local threshold=$((MIN_AGE_DAYS - 1))
    [ -n "$(find "$dir" -maxdepth 0 -mtime "+${threshold}" 2>/dev/null)" ]
}

# $1（basename）から PR 番号を取り出して stdout に出す。
# `pr-review-<数字>` の直後が 行末・`-`・`.` のいずれかであるものだけを受け付ける。
# 取り出せなければ 1 を返す（安全側: 対象外にする）。
pr_number_of() {
    local base="$1"
    if [[ "$base" =~ ^pr-review-([0-9]+)([-.].*)?$ ]]; then
        printf '%s' "${BASH_REMATCH[1]}"
        return 0
    fi
    return 1
}

# $1（絶対パス、実パス化済み）が自分自身のリポジトリの
# `git worktree list --porcelain` に登録されていれば真を返す。
# git worktree list は常に自分自身を含むため、単純な grep ではなく
# 一覧を実パスに正規化して自分と突き合わせる。
worktree_is_registered() {
    local real_gitdir="$1" registered_paths wp real_wp
    registered_paths="$(git -C "$real_gitdir" worktree list --porcelain 2>/dev/null \
        | awk '/^worktree /{ $1=""; sub(/^ /, ""); print }')"
    while IFS= read -r wp; do
        [ -n "$wp" ] || continue
        real_wp="$(cd "$wp" 2>/dev/null && pwd -P)" || continue
        if [ "$real_wp" = "$real_gitdir" ]; then
            return 0
        fi
    done <<<"$registered_paths"
    return 1
}

# 登録済み worktree $1（絶対パス）を `git worktree remove --force` で撤去する。
# --force は 1 回だけ（locked は残す）。呼び出し元が porcelain 成功かつ空を保証する。
release_registered_worktree() {
    local wt="$1" err
    if [ "$DRY_RUN" = "1" ]; then
        echo "dry-run: would run: git worktree remove --force ${wt}"
        return 0
    fi
    if err="$(git -C "$wt" worktree remove --force "$wt" 2>&1)"; then
        echo "released registered worktree via git worktree remove: ${wt}"
        return 0
    fi
    echo "failed to release worktree (kept as-is): ${wt}: ${err}" >&2
    return 1
}

# $1 配下に見つかった git 作業ツリーをすべて検査する。
#   - git 状態が判定不能、または未コミット変更がある -> 1 を返す（呼び出し元は
#     ディレクトリ全体を削除しない）
#   - 登録済みでクリーン -> git worktree remove で撤去する（失敗したら 1 を返す）
#   - 未登録でクリーン（既に手動 remove 済みの抜け殻）-> 何もしない
# すべて安全に処理できたら 0 を返す（この後ディレクトリ全体を rm -rf してよい）。
resolve_git_worktrees_inside() {
    local dir="$1" git_entry gitdir real_gitdir status_out
    local -a git_entries=()

    # 削除・remove で配下を変更しながら同時に find で辿ると事故りやすいため、
    # 対象一覧を先に確定させてから処理する。
    while IFS= read -r -d '' git_entry; do
        git_entries+=("$git_entry")
    done < <(find "$dir" -mindepth 1 -maxdepth 3 -name .git -print0 2>/dev/null)

    for git_entry in "${git_entries[@]}"; do
        # 先に親 worktree を remove すると配下の submodule .git が消える。
        [ -e "$git_entry" ] || continue
        gitdir="$(dirname "$git_entry")"

        if ! git -C "$gitdir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo "block (unverifiable git state): ${gitdir}" >&2
            return 1
        fi

        real_gitdir="$(cd "$gitdir" && pwd -P)"

        status_out="$(git -C "$real_gitdir" status --porcelain 2>/dev/null)" || {
            echo "block (unverifiable git state): ${real_gitdir}" >&2
            return 1
        }
        if [ -n "$status_out" ]; then
            echo "block (uncommitted changes): ${real_gitdir}" >&2
            return 1
        fi

        if worktree_is_registered "$real_gitdir"; then
            if ! release_registered_worktree "$real_gitdir"; then
                return 1
            fi
        fi
    done
    return 0
}

# $1 が REMOVED_PR_DIRS に含まれていれば真を返す。
_is_removed_pr_dir() {
    local needle="$1" item
    for item in ${REMOVED_PR_DIRS[@]+"${REMOVED_PR_DIRS[@]}"}; do
        [ "$item" = "$needle" ] && return 0
    done
    return 1
}

# $1 が残りの引数のいずれかと一致すれば真を返す。
_contains() {
    local needle="$1" item
    shift
    for item in "$@"; do
        [ "$item" = "$needle" ] && return 0
    done
    return 1
}

# ディレクトリ削除とは独立に、TMP_ROOT 直下の loose なセッション状態ファイル
# （pr-review-<PR>-diff.patch、pr-review-<PR>-session.env、pr-review-<PR>.diff 等）
# を片付ける。
#
# pr-review スキルは save 成功時に自身の worktree・セッション
# ディレクトリを削除する。そのため「ディレクトリを削除したとき」を契機にすると
# loose ファイルには二度と掃除が来ない。ディレクトリの有無と独立に走らせる。
#
# 安全条件は従来どおり:
#   - 同じ PR 番号のディレクトリが 1 つでも残っていれば触れない
#     （そのインスタンスがまだ参照しているかもしれないため）
#   - MIN_AGE_DAYS を満たすものだけ削除する
#
# dry-run と live の乖離について: REMOVED_PR_DIRS は「削除した（dry-run では
# 削除するとみなした）」ディレクトリを記録するが、dry-run は
# `git worktree remove --force` / `rm -rf` を実際には実行しないため、それらが
# 実運用で失敗し得るケース（ロック・権限・レース等）を検知できない。
# そのため乖離が起きるとすれば常に dry-run が過剰報告する方向にのみ起きる:
# live で実削除が失敗すればディレクトリは物理的に残り、このディレクトリは
# REMOVED_PR_DIRS に入らないため surviving 判定で「まだ残っている」と扱われ、
# 同じ PR の loose ファイルは保護される。dry-run が「消せる」と報告した loose
# ファイルを live が誤って消してしまう方向には乖離しない。
cleanup_orphaned_pr_session_files() {
    local entry base pr removed=0
    local -a surviving=()

    # まだ生き残っている PR 番号を集める。cleanup_pr_review_dirs が削除した
    # （dry-run では削除するとみなした）ディレクトリは生存扱いにしない。
    for entry in "${TMP_ROOT}"/pr-review-*; do
        [ -d "$entry" ] || continue
        _is_removed_pr_dir "$entry" && continue
        base="$(basename "$entry")"
        pr="$(pr_number_of "$base")" || continue
        surviving+=("$pr")
    done

    for entry in "${TMP_ROOT}"/pr-review-*; do
        [ -f "$entry" ] || continue
        base="$(basename "$entry")"
        pr="$(pr_number_of "$base")" || continue
        if _contains "$pr" ${surviving[@]+"${surviving[@]}"}; then
            continue
        fi
        dir_is_old_enough "$entry" || continue

        if [ "$DRY_RUN" = "1" ]; then
            echo "dry-run: would remove orphaned session file: ${entry}"
            removed=$((removed + 1))
            continue
        fi
        if rm -f -- "$entry"; then
            echo "removed orphaned session file: ${entry}"
            removed=$((removed + 1))
        else
            echo "failed to remove orphaned session file: ${entry}" >&2
        fi
    done

    echo "orphaned session file cleanup: removed=${removed}"
}

# $1: ログ用 kind（pr-review / review-fix-planning）
# $2: 削除したディレクトリを追記する配列名。空なら記録しない
# $3...: 呼び出し側が未クォート glob を展開して渡したパス
cleanup_tmp_dirs() {
    local kind="$1"
    local acc_name="$2"
    shift 2
    local removed=0 skipped=0 dir
    local -a _cleanup_tmp_dirs_unused=()
    local -n _removed_acc="${acc_name:-_cleanup_tmp_dirs_unused}"

    for dir in "$@"; do
        [ -d "$dir" ] || continue

        if path_is_in_use "$dir"; then
            echo "skip (in use by a running process): ${dir}"
            skipped=$((skipped + 1))
            continue
        fi

        if ! dir_is_old_enough "$dir"; then
            echo "skip (younger than ${MIN_AGE_DAYS}d): ${dir}"
            skipped=$((skipped + 1))
            continue
        fi

        if ! resolve_git_worktrees_inside "$dir"; then
            echo "skip (dirty or unverifiable git worktree inside): ${dir}"
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$DRY_RUN" = "1" ]; then
            echo "dry-run: would remove ${kind} debris: ${dir}"
            removed=$((removed + 1))
            _removed_acc+=("$dir")
            continue
        fi

        if rm -rf -- "$dir"; then
            echo "removed ${kind} debris: ${dir}"
            removed=$((removed + 1))
            _removed_acc+=("$dir")
        else
            echo "failed to remove: ${dir}" >&2
            skipped=$((skipped + 1))
        fi
    done

    echo "${kind} cleanup: removed=${removed} skipped=${skipped}"
}

cleanup_pr_review_dirs() {
    cleanup_tmp_dirs "pr-review" REMOVED_PR_DIRS "${TMP_ROOT}"/pr-review-*
}

cleanup_review_fix_planning_dirs() {
    cleanup_tmp_dirs "review-fix-planning" "" "${TMP_ROOT}"/review-fix-planning.*
}

main() {
    echo "=== workspace cleanup: $(date -u +%Y-%m-%dT%H:%M:%SZ) (root=${TMP_ROOT}) ==="
    cleanup_pr_review_dirs
    cleanup_orphaned_pr_session_files
    cleanup_review_fix_planning_dirs
}

main "$@"
