#!/bin/bash
#
# .devcontainer/cleanup-workspace.bash
#
# ディスクを圧迫する使い捨て debris を安全に掃除する。
#   - /tmp/pr-review-* のセッション: このスクリプトは削除も git worktree remove もしない。
#     symlink・使用中・MIN_AGE_DAYS 未満を除いた後、pr-review スキルの helper
#     （pr_review_workspace.py）に判定と退役を任せる。
#       1. `reap-check --allow-failed --state <dir>/session.json` が終了コード 0 のときだけ
#       2. `cleanup --strict-reap --allow-failed --state <dir>/session.json` で退役する
#     終了コード 0 以外（保存していない本文、dirty な worktree、session.json が無い
#     ディレクトリなど）はすべて保持して理由を報告する。`--operator-confirmed-stopped`
#     は使わない（人の確認の代わりにしない）
#   - helper は WORKSPACE_CLEANUP_PR_REVIEW_HELPER、無ければ、このスクリプトの実体が
#     <root>/.devcontainer/ にあるときだけ <root>/.agents/skills/pr-review/scripts/
#     pr_review_workspace.py。通常ファイルとして見つからなければ（~/bin のコピーから
#     実行した場合など）、pr-review のディレクトリはすべて保持する
#   - loose な pr-review-* ファイル（pr-review-<PR>-diff.patch など）は出所と内容を確かめられない
#     ので削除せず、保護したものとして報告する
#   - /tmp/review-fix-planning.XXXXXX の残骸（review-fix-planning スキルが mktemp で
#     作る隔離 worktree。スキルは手順 3 の検証直後に自分で worktree remove と親削除を
#     行うが、異常終了時には残るため本スクリプトが安全網として掃除する。
#     公式 mktemp のドット区切り（review-fix-planning.*）のみ対象。
#     ハイフン区切りの歴史的残骸（-wt / -head.txt 等）は対象外で手動対応）
#
# review-fix-planning の安全条件（すべて AND で判断する）:
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
#     撤去後に残った親ディレクトリを削除する
#
# 環境変数（既定値はコンテナの実運用、テストでは差し替える）:
#   WORKSPACE_CLEANUP_TMP_ROOT       pr-review-* / review-fix-planning.* を探すルート（既定 /tmp）
#   WORKSPACE_CLEANUP_MIN_AGE_DAYS   最終更新からの最小経過日数。0 以下で無効化（既定 1）
#   WORKSPACE_CLEANUP_DRY_RUN        1 で実際には退役・削除をせず対象だけ表示する（既定 0）
#   WORKSPACE_CLEANUP_PR_REVIEW_HELPER  pr_review_workspace.py の場所（既定は上記）

set -u

readonly TMP_ROOT="${WORKSPACE_CLEANUP_TMP_ROOT:-/tmp}"
readonly MIN_AGE_DAYS="${WORKSPACE_CLEANUP_MIN_AGE_DAYS:-1}"
readonly DRY_RUN="${WORKSPACE_CLEANUP_DRY_RUN:-0}"

# pr-review の helper の場所。スクリプトの位置が解決できなければ空のパスになり、
# 通常ファイルでないので pr-review を保持する（止まらない）。
resolve_pr_review_helper() {
    if [ -n "${WORKSPACE_CLEANUP_PR_REVIEW_HELPER:-}" ]; then
        printf '%s' "$WORKSPACE_CLEANUP_PR_REVIEW_HELPER"
        return 0
    fi
    local self root
    # BASH_SOURCE[0] が空（stdin から起動など）だと readlink -f が cwd を返すので、先に弾く
    self=""
    if [ -n "${BASH_SOURCE[0]:-}" ]; then
        self="$(readlink -f -- "${BASH_SOURCE[0]}" 2>/dev/null)" || self=""
    fi
    if [ -z "$self" ] || [ ! -f "$self" ]; then
        printf '%s' ''
        return 0
    fi
    # <root>/.devcontainer/ にある実体だけが相対で探せる。~/bin のコピーなどの 1 つ上は
    # $HOME などの無関係な場所になり、そこの同名のコードを無人で実行してしまうため探さない
    if [ "$(basename -- "$(dirname -- "$self")")" != ".devcontainer" ]; then
        printf '%s' ''
        return 0
    fi
    root="$(dirname -- "$(dirname -- "$self")")"
    printf '%s' "${root}/.agents/skills/pr-review/scripts/pr_review_workspace.py"
}
PR_REVIEW_HELPER="$(resolve_pr_review_helper)"

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

# helper の出力（stdout と stderr）を 1 行にする。
one_line() {
    local text="$1"
    text="${text//$'\n'/ }"
    printf '%s' "$text"
}

# /tmp/pr-review-* のセッションを helper 経由でだけ退役させる。
cleanup_pr_review_dirs() {
    local dir out rc retired=0 kept=0
    local helper_ok=0
    [ -f "$PR_REVIEW_HELPER" ] && helper_ok=1

    for dir in "${TMP_ROOT}"/pr-review-*; do
        [ -d "$dir" ] || continue

        if [ -L "$dir" ]; then
            echo "keep (symlink): ${dir}"
            kept=$((kept + 1))
            continue
        fi
        if path_is_in_use "$dir"; then
            echo "keep (in use by a running process): ${dir}"
            kept=$((kept + 1))
            continue
        fi
        if ! dir_is_old_enough "$dir"; then
            echo "keep (younger than ${MIN_AGE_DAYS}d): ${dir}"
            kept=$((kept + 1))
            continue
        fi
        if [ "$helper_ok" != 1 ]; then
            echo "keep (pr-review helper unavailable: ${PR_REVIEW_HELPER}): ${dir}"
            kept=$((kept + 1))
            continue
        fi
        if [ ! -f "${dir}/session.json" ]; then
            echo "keep (no session.json): ${dir}"
            kept=$((kept + 1))
            continue
        fi

        out="$(python3 "$PR_REVIEW_HELPER" reap-check --allow-failed --state "${dir}/session.json" 2>&1)"
        rc=$?
        if [ "$rc" -ne 0 ]; then
            echo "keep (reap-check exit ${rc}): ${dir}: $(one_line "$out")"
            kept=$((kept + 1))
            continue
        fi
        if [ "$DRY_RUN" = "1" ]; then
            echo "dry-run: would retire pr-review session: ${dir}: $(one_line "$out")"
            retired=$((retired + 1))
            continue
        fi

        out="$(python3 "$PR_REVIEW_HELPER" cleanup --strict-reap --allow-failed --state "${dir}/session.json" 2>&1)"
        rc=$?
        if [ "$rc" -eq 0 ]; then
            echo "retired pr-review session: ${dir}: $(one_line "$out")"
            retired=$((retired + 1))
        else
            echo "keep (cleanup exit ${rc}): ${dir}: $(one_line "$out")"
            kept=$((kept + 1))
        fi
    done

    echo "pr-review cleanup: retired=${retired} kept=${kept}"
}

# TMP_ROOT 直下の loose な pr-review-* ファイルは出所と内容を確かめられないので、
# 削除せず報告だけする。
cleanup_orphaned_pr_session_files() {
    local entry protected=0
    for entry in "${TMP_ROOT}"/pr-review-*; do
        [ -f "$entry" ] || continue
        echo "protected loose pr-review file (unverifiable provenance): ${entry}"
        protected=$((protected + 1))
    done
    echo "orphaned session file cleanup: protected=${protected}"
}

# review-fix-planning.* の残骸を掃除する。
# $1...: 呼び出し側が未クォート glob を展開して渡したパス
cleanup_tmp_dirs() {
    local kind="review-fix-planning"
    local removed=0 skipped=0 dir

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
            continue
        fi

        if rm -rf -- "$dir"; then
            echo "removed ${kind} debris: ${dir}"
            removed=$((removed + 1))
        else
            echo "failed to remove: ${dir}" >&2
            skipped=$((skipped + 1))
        fi
    done

    echo "${kind} cleanup: removed=${removed} skipped=${skipped}"
}

cleanup_review_fix_planning_dirs() {
    cleanup_tmp_dirs "${TMP_ROOT}"/review-fix-planning.*
}

main() {
    echo "=== workspace cleanup: $(date -u +%Y-%m-%dT%H:%M:%SZ) (root=${TMP_ROOT}) ==="
    cleanup_pr_review_dirs
    cleanup_orphaned_pr_session_files
    cleanup_review_fix_planning_dirs
}

main "$@"
