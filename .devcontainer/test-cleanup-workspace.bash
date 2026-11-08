#!/bin/bash
# .devcontainer/cleanup-workspace.bash の設定と dry-run を、一時ディレクトリだけを対象に検査する。仕様 7.2 節
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/.devcontainer/cleanup-workspace.bash"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "${TEST_ROOT:?}"' EXIT
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

HELPER="$REPO_ROOT/.agents/skills/pr-review/scripts/pr_review_workspace.py"
T="$TEST_ROOT/current"
R="$TEST_ROOT/main"
mkdir -p "$T" "$TEST_ROOT/home"
git init -q -b main "$R"
printf 'x\n' > "$R/README.md"
git -C "$R" add README.md
git -C "$R" -c user.name=Test -c user.email=test@example.com commit -q -m init
SHA="$(git -C "$R" rev-parse HEAD)"

json_field() { python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
create_session() { # $1=model $2=attempt
    python3 "$HELPER" create --repo "$R" --pr-repo usaturn/create-reso-world --pr-number 4 \
        --commit "$SHA" --head-branch fix/x --model-name "$1" --temp-root "$T" --attempt-id "$2"
}

c1="$(create_session model-a a1)"
S1_STATE="$(json_field state_file <<<"$c1")"
S1_DRAFT="$(json_field draft <<<"$c1")"
S1="$(dirname "$S1_STATE")"
printf '# review\n\nfinding\n' > "$S1_DRAFT"
python3 "$HELPER" save --state "$S1_STATE" >/dev/null
c2="$(create_session model-b a2)"
S2_STATE="$(json_field state_file <<<"$c2")"
S2_DRAFT="$(json_field draft <<<"$c2")"
S2="$(dirname "$S2_STATE")"
printf '# unsaved draft\n' > "$S2_DRAFT"
mkdir -p "$T/pr-review-42-abandoned"
printf 'diff\n' > "$T/pr-review-42-diff.patch"
printf 'notes\n' > "$T/pr-review-notes.txt"

run_cleanup() {
    HOME="$TEST_ROOT/home" WORKSPACE_CLEANUP_TMP_ROOT="$T" WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 "$@" bash "$SCRIPT"
}

# 1. dry-run は保存済みを退役対象と報告するだけで、何も消さない
output="$(run_cleanup env WORKSPACE_CLEANUP_DRY_RUN=1)"
[[ "$output" == *"dry-run: would retire pr-review session: $S1"* ]] \
    || fail "dry-run did not report the saved session
$output"
for p in "$S1" "$S2" "$S2_DRAFT" "$T/pr-review-42-abandoned" "$T/pr-review-42-diff.patch"; do
    [ -e "$p" ] || fail "dry-run removed $p"
done

# 1b. 実行: 保存済みだけ退役し、未保存の draft・状態の無いディレクトリ・loose ファイルは消さない
output="$(run_cleanup)"
[ ! -e "$S1" ] || fail "saved session was not retired
$output"
for p in "$S2" "$S2_DRAFT" "$T/pr-review-42-abandoned" "$T/pr-review-42-diff.patch"; do
    [ -e "$p" ] || fail "cleanup removed $p
$output"
done
[[ "$output" == *"retired pr-review session: $S1"* ]] || fail "no retired line
$output"
grep -q "^keep .*: $S2:" <<<"$output" || fail "no keep line for the unsaved session
$output"
grep -q "^keep .*: $T/pr-review-42-abandoned" <<<"$output" || fail "no keep line for the stateless directory
$output"
[[ "$output" == *"protected loose pr-review file (unverifiable provenance): $T/pr-review-42-diff.patch"* ]] \
    || fail "no protected loose file line
$output"
[[ "$output" == *"protected loose pr-review file (unverifiable provenance): $T/pr-review-notes.txt"* ]] \
    || fail "no protected line for the loose file without a PR number
$output"

# 1c. スクリプトの位置が解決できないとき（stdin から起動）は、cwd の相対パスや cwd 由来の場所にある
#     コードを helper として実行せず、pr-review を保持する。定期実行の cwd は不定のため
CWD_TRAP="$TEST_ROOT/trap/a/b"
for base in "$CWD_TRAP" "$TEST_ROOT/trap"; do
    mkdir -p "$base/.agents/skills/pr-review/scripts"
    printf 'import pathlib\npathlib.Path(%s).touch()\nraise SystemExit(0)\n' "'$TEST_ROOT/trap-ran'" \
        > "$base/.agents/skills/pr-review/scripts/pr_review_workspace.py"
done
output="$(cd "$CWD_TRAP" && HOME="$TEST_ROOT/home" WORKSPACE_CLEANUP_TMP_ROOT="$T" WORKSPACE_CLEANUP_MIN_AGE_DAYS=0 \
    WORKSPACE_CLEANUP_DRY_RUN=1 bash <"$SCRIPT")"
[ ! -e "$TEST_ROOT/trap-ran" ] || fail "helper was taken from the cwd
$output"
grep -q "^keep (pr-review helper unavailable: ): $S2" <<<"$output" || fail "no unavailable keep line
$output"

# 2. 設定の既定値: 変数を渡さなければ /tmp、1 日、dry-run なし。
#    削除の範囲（/tmp 配下で 1 日より古いもの）を固定値で守る。既定値を広げると、使用中のレビュー用
#    worktree や /tmp 以外のディレクトリを消すため、スクリプトの値から期待値を作らない
config="$(
    env -u WORKSPACE_CLEANUP_TMP_ROOT -u WORKSPACE_CLEANUP_DRY_RUN -u WORKSPACE_CLEANUP_MIN_AGE_DAYS \
    bash -c '
        source <(sed -n "/^readonly TMP_ROOT=/,/^readonly DRY_RUN=/p" "$1")
        printf "%s|%s|%s" "$TMP_ROOT" "$MIN_AGE_DAYS" "$DRY_RUN"
    ' _ "$SCRIPT"
)"
[ "$config" = '/tmp|1|0' ] || fail "unexpected default configuration: $config"

printf 'PASS: workspace cleanup retires only saved sessions and keeps its default scope\n'
