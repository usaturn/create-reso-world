---
name: repo-cleanup-after-merge
description: Use when ユーザーが、PR がマージされた後のローカルリポジトリの片付けを依頼する場合。マージ済み branch の削除、使い終わった worktree の整理、レビュー用の使い捨て worktree の残骸の掃除、作業ツリーの origin/main への追従が対象。未マージの作業のリベース、コンフリクト解消、リリース作業には使用しない。例:「PR が全て Merge されたことを確認して branch, worktree を整理してローカルを更新して」「マージ済みのブランチを消して」「worktree を掃除して」「origin/main に追従して」「リポジトリを整理して」
allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(git *), Bash(gh *), Bash(ls *), Bash(diff *), Bash(mktemp *), Bash(cmp *), Bash(find *), Bash(cp *), Bash(rm *), Bash(uv run --no-project python -c *), Bash(uv run --no-project python *pr_review_workspace.py sessions *), Bash(uv run --no-project python *pr_review_workspace.py reap-check *), Bash(uv run --no-project python *pr_review_workspace.py cleanup --strict-reap *), Bash(bash scripts/resoloop-fork.sh sync)
---

# マージ後のリポジトリ整理

## 概要

PR がマージされた後に、ローカルの branch / worktree / 残骸を片付け、作業ツリーを `origin/main` に追従させる。ただし、`MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/`・`worlds/` の追跡ファイルを削除する更新は自動実行せず、README の「追跡解除コミットを取り込む」の保全手順を利用者へ案内する。

**中核原則: 整理とは「消すこと」ではなく「もう失うものが無いと確かめてから消すこと」である。**

git の操作はほぼ全て取り消せる。取り消せないのは次の 2 つだけであり、この 2 つにだけ注意を集中する。

- **ゲート A**: git 管理外ファイルの `rm` — 復元手段が無い
- **ゲート B**: リモートへの push（ブランチ削除を含む）— 他人が見る共有物への外向き操作

## 対象リポジトリの確定

整理対象の PR が属するリポジトリで root を決める。対応はルート `AGENTS.md` の「リポジトリ境界」の表に従う。

- `usaturn/create-reso-world`（このリポジトリ）の PR: リポジトリのルート（`git rev-parse --show-toplevel`）が root である
- `usaturn/resoloop` または `orange3134/resoloop` の PR: fork の checkout `external/resoloop`（リポジトリのルート基準）が root である。Git コマンドは `git -C external/resoloop ...`、`gh` 呼び出しには PR が属するリポジトリに合わせて `--repo usaturn/resoloop` か `--repo orange3134/resoloop` を付けて実行する。checkout が無い、または `origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` でない場合は、`scripts/resoloop-fork.sh clone` を案内して停止する
- 採用済み台帳の通常ツール: 下の「通常ツールの対象照合」を実行し、返された常設 checkout だけを root にする。同じ origin の別 clone や親 checkout に切り替えない
- それ以外: 推測せず停止する

両方にまたがる整理は、リポジトリごとにこの手順を回す。pr-review の `session.json` の `destination` は相対パス。version 7 は `main_root`、version 8 は `parent_root` に結合して正式保存先を得る。version 8 の `target_root` は Git 操作先であり、保存先ではない。新規レビューは全リポジトリとも create-reso-world の親 checkout の `reviews/<owner>/<repo>/#<PR>-<branch>/` に保存する。旧配置は移さない。

### branch の取り込み判定

手順 3、通常ツールの削除候補の照合、手順 8、ゲート B は、この判定で `ancestor` または `pr` が返った branch だけを「取り込み済み」とみなす。判定は read-only で、branch・ref・worktree を変更しない。同じシェルで次のブロックを実行してから、`cleanup_branch_evidence` を呼ぶ。引数は順に、対象 checkout、対象 repository、明示した PR 番号、branch 名、候補 ref（`refs/heads/...` または `refs/remotes/...`）、選択した取り込み先 base ref、省略可能な検証済みの fork（`EXPECTED_HEAD_REPO`。`owner/name`、空可）である。候補 ref の現在値と PR の `headRefOid` が一致し、PR が `MERGED` で、`headRefName` が branch と一致するときだけ判定する。さらに、`isCrossRepository` が false の PR か、`isCrossRepository` が true で PR の head repository（`headRepositoryOwner.login`/`headRepository.name`）が 7 番目の引数と大小文字を区別せずに一致する PR だけを受け付ける。7 番目が空・省略（6 引数の呼び出し）なら同じ repository の PR だけを判定する。候補が base の祖先なら `ancestor`、祖先でなくても `mergeCommit` が base に到達可能なら `pr` を返す。PR の照会失敗、`state`・`headRefName`・`headRefOid`・`isCrossRepository` の欠落、検証済みの fork ではない cross-repository の PR（7 番目が空、head repository の欠落・不一致、無関係な fork）、head 不一致、未統合 base は保持する。PR 型で必要な `mergeCommit` を読めない場合も保持する。`gh` は必ず `--repo` で対象 repository を固定し、返却値を推測で補わない。

7 番目の値は `cleanup_expected_head_repo` で経路から決める。`CLEANUP_ROUTE` が `fork` のときだけ `EXPECTED_HEAD_REPO` を返し、`create`・`managed`（未設定を含む）では空にする。手順 3 とゲート B はこの関数を使い、環境に残った `EXPECTED_HEAD_REPO` で cross-repository の PR を候補にしない。経路の値が不明なときは、取り込み判定を行わずに停止する。

```bash
cleanup_branch_evidence() {
  if [ "$#" -ne 6 ] && [ "$#" -ne 7 ]; then
    printf '%s\n' 'cleanup: 取り込み判定の引数が足りない' >&2
    return 2
  fi
  local checkout=$1 repo=$2 number=$3 branch=$4 candidate_ref=$5 base_ref=$6
  local expected_head_repo=${7:-}
  local head pr_json fields state head_name head_oid cross merge_oid head_repo
  if ! head=$(git -C "$checkout" rev-parse --verify --quiet "${candidate_ref}^{commit}"); then
    printf 'cleanup: 候補 ref を読めない: %s\n' "$candidate_ref" >&2
    return 1
  fi
  if ! pr_json=$(gh pr view "$number" --repo "$repo" --json state,headRefName,headRefOid,mergeCommit,isCrossRepository,headRepository,headRepositoryOwner); then
    printf 'cleanup: PR #%s を照会できない\n' "$number" >&2
    return 1
  fi
  if ! fields=$(printf '%s' "$pr_json" | jq -r '[.state, .headRefName, .headRefOid, (.isCrossRepository | tostring), (.mergeCommit.oid // "")] | @tsv'); then
    printf 'cleanup: PR #%s の応答を読めない\n' "$number" >&2
    return 1
  fi
  IFS=$'\t' read -r state head_name head_oid cross merge_oid <<< "$fields"
  if [ "$state" != MERGED ] || [ "$head_name" != "$branch" ] || [ "$head_oid" != "$head" ]; then
    printf 'cleanup: PR #%s と branch %s の対応を確認できない\n' "$number" "$branch" >&2
    return 1
  fi
  if [ "$cross" != false ]; then
    if ! head_repo=$(printf '%s' "$pr_json" | jq -r 'if (.headRepositoryOwner.login | type) == "string" and (.headRepository.name | type) == "string" and .headRepositoryOwner.login != "" and .headRepository.name != "" then .headRepositoryOwner.login + "/" + .headRepository.name else "" end'); then
      head_repo=
    fi
    expected_head_repo=$(printf '%s' "$expected_head_repo" | tr '[:upper:]' '[:lower:]')
    head_repo=$(printf '%s' "$head_repo" | tr '[:upper:]' '[:lower:]')
    if [ "$cross" != true ] || [ -z "$expected_head_repo" ] || [ "$head_repo" != "$expected_head_repo" ]; then
      printf 'cleanup: PR #%s の head repository を検証済みの fork と確認できない\n' "$number" >&2
      return 1
    fi
  fi
  if git -C "$checkout" merge-base --is-ancestor "$head" "$base_ref" 2>/dev/null; then
    printf 'ancestor\n'
    return 0
  fi
  if [ -n "$merge_oid" ] \
    && git -C "$checkout" rev-parse --verify --quiet "${merge_oid}^{commit}" >/dev/null 2>&1 \
    && git -C "$checkout" merge-base --is-ancestor "$merge_oid" "$base_ref" 2>/dev/null; then
    printf 'pr\n'
    return 0
  fi
  printf 'cleanup: branch %s は %s に取り込まれていない\n' "$branch" "$base_ref" >&2
  return 1
}

cleanup_branch_pr_number() {
  if [ "$#" -ne 4 ]; then
    printf '%s\n' 'cleanup: PR 番号の判定引数が足りない' >&2
    return 2
  fi
  local checkout=$1 repo=$2 branch=$3 candidate_ref=$4 head pr_list pr_count numbers
  local limit=100
  if ! head=$(git -C "$checkout" rev-parse --verify --quiet "${candidate_ref}^{commit}"); then
    return 1
  fi
  if ! pr_list=$(gh pr list --state all --head "$branch" --repo "$repo" --json number,headRefName,headRefOid --limit "$limit"); then
    return 1
  fi
  if ! pr_count=$(printf '%s' "$pr_list" | jq -er 'if type == "array" then length else error("not an array") end'); then
    return 1
  fi
  if [ "$pr_count" -ge "$limit" ]; then
    printf 'cleanup: PR 一覧が取得上限 %s 件に達したため対応を確定できない\n' "$limit" >&2
    return 1
  fi
  if ! numbers=$(printf '%s' "$pr_list" | jq -r --arg branch "$branch" --arg head "$head" '[.[] | select(.headRefName == $branch and .headRefOid == $head) | .number] | if length == 1 then .[0] else empty end'); then
    return 1
  fi
  [ -n "$numbers" ] || return 1
  printf '%s\n' "$numbers"
}

cleanup_expected_head_repo() {
  case "${CLEANUP_ROUTE:-create}" in
    fork)
      : "${EXPECTED_HEAD_REPO:?fork の経路では EXPECTED_HEAD_REPO（checkout の origin の owner/name）を設定する}"
      printf '%s\n' "$EXPECTED_HEAD_REPO"
      ;;
    create|managed)
      printf '%s\n' ''
      ;;
    *)
      printf 'cleanup: CLEANUP_ROUTE が不明なため取り込み判定を行わない: %s\n' "$CLEANUP_ROUTE" >&2
      return 1
      ;;
  esac
}

cleanup_remote_repo_key() {
  local url=$1
  case "$url" in
    git@github.com:*) url=${url#git@github.com:} ;;
    ssh://git@github.com/*) url=${url#ssh://git@github.com/} ;;
    https://github.com/*) url=${url#https://github.com/} ;;
    *) return 1 ;;
  esac
  while [ "${url%/}" != "$url" ]; do
    url=${url%/}
  done
  url=${url%.git}
  case "$url" in
    */*/* | /* | */ | '') return 1 ;;
    */*) ;;
    *) return 1 ;;
  esac
  printf '%s\n' "$url" | LC_ALL=C tr '[:upper:]' '[:lower:]'
}
```

`cleanup_branch_pr_number` は、同じ branch 名と head を持つ PR がちょうど 1 件のときだけ番号を返す。0 件・複数件・照会失敗では何も返さず、呼び出し側は branch を保持する。一覧が取得上限（100 件）に達した場合も、次のページに同じ branch と head の PR が残り得るため、一意性を断定せず保持する。

### 通常ツールの対象照合

読んだ skill の source checkout を `TOOL_ROOT`、常設親を `PARENT_ROOT`、整理対象 PR の base repository を `PR_REPO` として事前に設定する。`CODE_ROOT` を指定するなら登録済み常設 checkout の絶対パスだけ。登録は削除の許可ではない。[共通運用](../../../docs/external-tools-workflow.md)を読み、整理の依頼と対象 repo 自身の `AGENTS.md`・`README.md` を確認する。

```bash
set -euo pipefail
: "${TOOL_ROOT:?skill の source checkout}" "${PARENT_ROOT:?常設親}" "${PR_REPO:?整理対象 repository}"
# 後続の git -C も、呼出元の GIT_DIR 等に向けない。
for git_env in "${!GIT_@}"; do unset "$git_env"; done
managed_cleanup_context() {
  uv run --no-project python -c '
import json
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
from tools.external_tools.registry import load_active_registry
from tools.external_tools.identity import resolve_managed_target
from tools.external_tools.models import ExternalToolsError
try:
    registry = load_active_registry(Path(sys.argv[2]))
    if registry is None:
        raise ExternalToolsError("registry_missing", "Permanent parent has no adopted registry.")
    target = resolve_managed_target(registry, sys.argv[3], operation=sys.argv[4],
                                    code_root=Path(sys.argv[5]) if sys.argv[5] else None)
    print(json.dumps({"checkout": str(target.checkout), "common_dir": str(target.common_dir),
                      "base_remote": target.base_remote, "base_branch": target.spec.base_branch,
                      "registry_commit": target.registry_commit}))
except ExternalToolsError as error:
    print(f"cleanup: {error.reason_code}: {error}", file=sys.stderr)
    sys.exit(66)
' "$TOOL_ROOT" "$PARENT_ROOT" "$PR_REPO" "$1" "$2"
}
CLEANUP_CONTEXT=$(managed_cleanup_context cleanup "${CODE_ROOT:-}") || exit 66
CLEANUP_ROOT=$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .checkout)
CLEANUP_COMMON_DIR=$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .common_dir)
CLEANUP_BASE_REMOTE=$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .base_remote)
CLEANUP_BASE_BRANCH=$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .base_branch)
CLEANUP_BASE="refs/remotes/$CLEANUP_BASE_REMOTE/$CLEANUP_BASE_BRANCH"
```

各呼び出しで対象照合を再実行する。手順 1–6 の Git は `git -C "$CLEANUP_ROOT" ...`（または同じシェルで `cd -- "$CLEANUP_ROOT"` 後）、gh は必ず `--repo "$PR_REPO"` を付ける。sessions の `--repo` も `CLEANUP_ROOT`。手順 2 の fetch は照合済みの `CLEANUP_BASE_REMOTE` だけに限定する（`--all` にしない）。base は台帳の literal ref `CLEANUP_BASE` を使い、`origin/main` に固定しない。

通常ツールでは手順 7（親の更新）と 10（fork sync）を実行しない。常設 checkout の HEAD・ローカル base branch とそれを保持する worktree は変更せず残す。手順 8 は `CLEANUP_ROUTE=managed` で実行し、Git 操作先は `CLEANUP_ROOT`、取り込みの再確認先は `CLEANUP_BASE` とする。`EXPECTED_HEAD_REPO` は設定せず、同じ repository の PR だけを判定する（下の候補照合も 7 番目に空を渡す）。手順 9 の基準も `CLEANUP_BASE` とし、remote の base / HEAD を候補から除外する。リモート削除は従来どおり別の明示確認が必要。手順 11 は `git -C "$CLEANUP_ROOT"` で報告し、親が更新されたとは書かない。

### 通常ツールの削除候補の照合

手順 1 の対象外を除き、手順 2 の fetch 後、手順 3 で branch の候補を調べる際に実行する。直前の対象照合と同じシェルで、候補 worktree の絶対パス `CLEANUP_CANDIDATE` と対応する `PR_NUMBER` を設定し、先に「branch の取り込み判定」のブロックを実行する。これは候補の判定だけであり、成功後も所有・clean・ignored ファイルの手順 4 と、手順 5 の削除条件を省かない。

```bash
: "${CLEANUP_ROOT:?対象照合を先に実行する}" "${CLEANUP_CANDIDATE:?候補 worktree の絶対パス}" "${PR_NUMBER:?対応 PR}"
CANDIDATE_CONTEXT=$(managed_cleanup_context base-read "$CLEANUP_CANDIDATE") || exit 66
test "$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .common_dir)" = "$CLEANUP_COMMON_DIR" || exit 66
test "$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .registry_commit)" = "$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .registry_commit)" || exit 66
CLEANUP_CANDIDATE=$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .checkout)
test "$CLEANUP_CANDIDATE" != "$CLEANUP_ROOT" || exit 66
CLEANUP_BRANCH=$(git -C "$CLEANUP_CANDIDATE" symbolic-ref --short HEAD) || exit 66
test "$CLEANUP_BRANCH" != "$CLEANUP_BASE_BRANCH" || exit 66
CLEANUP_EVIDENCE=$(cleanup_branch_evidence "$CLEANUP_CANDIDATE" "$PR_REPO" "$PR_NUMBER" "$CLEANUP_BRANCH" "refs/heads/$CLEANUP_BRANCH" "$CLEANUP_BASE" "") || exit 66
printf 'cleanup: %s の取り込みの証拠: %s\n' "$CLEANUP_BRANCH" "$CLEANUP_EVIDENCE"
```

拒否された候補は削除せず理由を報告する。共通 Git ディレクトリが違う・未マージ・PR 対応不明なら、親の worktree や同 origin の別 clone が clean でも残す。`git log` の出力が空でないことだけを未取り込みの根拠にせず、squash/rebase は `pr` の証拠で候補にする。通常ツールの登録だけで pr-review の session や失敗 clone の staging の削除を許可しない。

### fork の経路（`external/resoloop`）だけの手順

fork の checkout は、`scripts/resoloop-fork.sh checkout <ref>` や `install <ref>` が取り出したコミットで detached HEAD になっていることが多く、利用者が作業ブランチにいることもある。`build` はこれを動かさない。この前提から、fork の経路は次の順で進める。

1. ユーザー確認を得てから（Claude Code では AskUserQuestion）、手順 10 の `sync` を先に実行し、fork の `main` を上流へ追従させる。手順 2 の `fetch --prune` の前でよい
2. マージ済みかの判定（手順 3）は、上流 `orange3134/resoloop` 発の PR は `upstream/main` を、fork 内（`usaturn/resoloop` 発）の PR は `origin/main` を基準にする。fork の上流 PR は常に cross-repository なので、手順 3・8・ゲート B では `CLEANUP_ROUTE=fork`、`PARENT_ROOT=<create-reso-world の main checkout>`、`TARGET_ROOT=$PARENT_ROOT/external/resoloop`、`EXPECTED_HEAD_REPO=usaturn/resoloop`（checkout の origin）を設定し、PR の head repository が一致するときだけ取り込み済みと判定する。ゲート B では PR の照会先・取り込み先 base・削除元 remote を分け、上流 PR なら `PR_REPO=orange3134/resoloop`、`BASE_REF=upstream/main`、`REMOTE=origin` とする。削除する head branch は fork（`origin`）にあり、`REMOTE=upstream` にしない。手順 8 は `TARGET_ROOT` が `$PARENT_ROOT/external/resoloop` と一致することも確かめる。`sync` を先に済ませていないと、上流でマージ済みの PR がこの fork の `origin/main` ではまだ未取り込みに見える
3. 手順 7（メイン作業ツリーを `origin/main` の detached HEAD に更新する操作）は実行しない。`external/resoloop` の HEAD は、detached でもブランチでもそのまま残す。誤って動かしていた場合は、`git -C external/resoloop reflog` で元の位置を確かめて戻す

`bash scripts/resoloop-fork.sh sync` と `git -C external/resoloop ...` は、エージェントがどの作業ディレクトリから開始していても、リポジトリのルート（`cd "$(git rev-parse --show-toplevel)"`）で実行する。

## ワークフロー

### 1. 何も消す前に状態を把握する

次の read-only コマンドを実行する。

```bash
git status
git worktree list --porcelain
git branch -vv
git remote -v
gh pr list --state open --json number,title,headRefName,headRefOid
gh pr list --state all --limit 20 --json number,title,state,headRefName,mergedAt
```

`gh` が非0終了した場合、PR の状態は不明である。マージ判定を推測で進めず、エラーを報告して停止する。

Open PR が 1 件以上ある場合、次は **整理対象外**である。残存 PR をユーザーへ報告し、それ以外だけを進める。

- `headRefName` に一致する branch
- その branch をチェックアウトしている worktree
- `git worktree list --porcelain` の `HEAD` が、オープン PR の `headRefOid` と一致する worktree（detached でも対象外）
- パスが `/tmp/pr-review-*` で、HEAD がオープン PR の `headRefOid` と一致するか、親の `session.json` の `head_branch` がオープン PR の `headRefName` である worktree と、その親ディレクトリ

Open PR の有無にかかわらず、`git worktree list --porcelain` で `prunable` または `locked` の行を持つ worktree も **整理対象外**である。パスと行の内容を控え、手順 11 で報告する。

- `prunable` は、登録パスに接続できないという情報である。本体の消失や削除の許可を示さない。本体を別の場所へ移動して `git worktree repair` をまだしていない worktree や、親ディレクトリだけが消えて所有者の照合を待っている別 run の登録にも出る
- `locked` は、所有する run などが削除を止めている印である

`/tmp/pr-review-*` の worktree は、オープン PR の一覧との照合に加えて、pr-review の helper の `sessions` で、それぞれの session の PR が終了したかを確かめる。fork の経路では、fork と上流の PR が同じ checkout を使い、番号・branch・head まで重なり得るので、片方のリポジトリの PR 一覧では判定できない。リポジトリのルートで次を実行する。

```bash
uv run --no-project python .agents/skills/pr-review/scripts/pr_review_workspace.py sessions --repo <整理対象のメイン作業ツリーの絶対パス>
```

`--repo` は、create-reso-world では手順 7 の `MAIN_ROOT`（`git worktree list --porcelain` の先頭）、fork の経路では `external/resoloop` の絶対パスである。helper は各 session の `session.json` に固定された所属リポジトリ（version 7 の `pr_repository`、version 8 の `pr_repo`）と PR 番号で `gh pr view` を呼び、その PR が `MERGED` か `CLOSED` のときだけ `removable: true` を返す。何も変更しない。version 8 の checkout session は `target_root` に登録される。bundle session は専用 Git repository と `.staging/` にあり、対象 checkout の一覧に現れないことがある。未報告・照合不能を削除許可とせず、version 8 は下記のとおり保持する。

- `removable: false` の worktree とその親ディレクトリは **整理対象外**である。`reason`（session.json が無い・読めない、所属を持たない version 6 以前の session、`locked`・`prunable`、オープン、gh の失敗など）を控え、手順 11 で報告する
- helper が終了コード 0 以外で終わったら、`/tmp/pr-review-*` の worktree はすべて整理対象外にする
- 番号・branch・commit が一致することや、片方のリポジトリの PR 一覧に無いことを、session の PR が終了した根拠にしない

### 2. リモートを取り込む

```bash
git fetch --all --prune
```

**マージ判定より前に必ず実行する。** ローカルの `origin/main` は古いのが普通であり、fetch 前の「マージ済みか」の判定は誤る。

### 3. マージ済みか判定する

`usaturn/create-reso-world` の既存ローカル `main` は保持対象であり、この判定から除外する。古い・分岐している場合もそのまま残し、対応する PR の `MERGED` 確認は要求しない。fork の経路でも `external/resoloop` のローカル `main`（ベース branch）を同様に除外し、削除しない。

それ以外の branch ごとに、branch の現在の head と対応する PR 番号を確定し、「branch の取り込み判定」を実行する。PR 番号は `cleanup_branch_pr_number` で、branch 名と head が一致する PR がちょうど 1 件のときだけ採用する。0 件・複数件・照会失敗なら対応不明として保持する。base は create-reso-world では `origin/main`、通常ツールでは `CLEANUP_BASE`、fork では上流 PR なら `upstream/main`、fork 内 PR なら `origin/main` を使う。手順 3 の `EXPECTED_HEAD_REPO` は `cleanup_expected_head_repo` で経路から決める。fork の経路では checkout の origin（`usaturn/resoloop`）を設定し、上流 PR の head repository がそれと一致するときだけ cross-repository の PR を判定する。create-reso-world と通常ツール（`CLEANUP_ROUTE` の未設定を含む）では空にし、環境に残った値を使わない。

```bash
# 同じシェルで「branch の取り込み判定」のブロックを先に実行する。
CHECKOUT=<対象 checkout>
PR_REPO=<対象 repository>
BASE_REF=<選択した取り込み先 base ref>
BRANCH=<branch>
: "${CHECKOUT:?対象 checkout}" "${PR_REPO:?対象 repository}" "${BASE_REF:?取り込み先 base ref}" "${BRANCH:?branch}"
EXPECTED_HEAD_REPO=$(cleanup_expected_head_repo) || exit 1
PR_NUMBER=$(cleanup_branch_pr_number "$CHECKOUT" "$PR_REPO" "$BRANCH" "refs/heads/$BRANCH") || {
  printf 'branch %s は対応 PR を 1 件に確定できないため保持する\n' "$BRANCH" >&2
  exit 1
}
EVIDENCE=$(cleanup_branch_evidence "$CHECKOUT" "$PR_REPO" "$PR_NUMBER" "$BRANCH" "refs/heads/$BRANCH" "$BASE_REF" "$EXPECTED_HEAD_REPO") || {
  printf 'branch %s は取り込みを確認できないため保持する\n' "$BRANCH" >&2
  exit 1
}
printf 'branch %s: %s (PR #%s)\n' "$BRANCH" "$EVIDENCE" "$PR_NUMBER"
```

- `ancestor` または `pr` が返った branch だけを取り込み済みとして次の手順へ進める。`pr` は squash/rebase で head が base の祖先でなくても、PR の `mergeCommit` が同じ base に到達可能な場合だけ返る。
- 判定できない branch は削除しない。`git log --oneline <base>..<branch>` が非空であることだけを未取り込みの根拠にしない。逆に、出力が空でも PR の対応を確認できなければ保持する。

fork の経路で上流 PR を判定する場合は基準が異なる。「fork の経路だけの手順」を見る。

### 4. 削除候補の worktree ごとに clean を確認する

`usaturn/create-reso-world` のメイン作業ツリーと、ローカル `main` を checkout している他の worktree は削除対象から外す。手順 7 は detached checkout なので、他 worktree が `main` を保持していても進められる。`main` を解放するためにその worktree を削除・detach・更新しない。

以下の dirty / ignore 対象ファイルに関する削除・退避のユーザー確認は、削除候補の worktree にだけ必要である。ただし、保持するメイン作業ツリーも手順 7 の `MAIN_ROOT` の clean 確認は省略せず、dirty または status 失敗なら checkout と後続の branch 削除を停止する。

```bash
git -C <worktree の絶対パス> status --short
git -C <worktree の絶対パス> status --short --ignored
```

`-C` には絶対パスを渡す。worktree 隔離セッションでは相対パスが拒否されることがある。1 つ目に出力がある worktree は **削除しない**。ユーザーへ報告して判断を仰ぐ。

clean とするのは、2 つの終了コードがどちらも 0 で、1 つ目の出力が空のときだけである。登録パスが無い・移動した・読めない worktree では、出力が空のまま終了コードが 0 以外（`cannot change to` なら 128）になる。この worktree は clean を確認できていないので削除せず、手順 11 で報告する。

`git worktree remove` は ignore 対象のファイルを確認せずに消す。2 つ目の出力の `!!` の行（ignore 対象）も確かめる。再生成できるキャッシュ（`.venv/`、`.uv-cache/`、`.pytest_cache/`、`.ruff_cache/`、`__pycache__/`、`node_modules/`）だけなら、worktree と一緒に消えてよい。それ以外（`reviews/`、`docs_draft/`、`tmp/`、`external/`、`private/`、`.superpowers/`、各プロジェクトの `.resoloop/` など）が 1 つでもある worktree は **削除しない**。一覧をユーザーへ報告し、正本への退避か削除の確認を得るまで残す（ゲート A と同じ扱い）。

#### 毎回ここで止まるなら、直すのは片付け側ではなく生成側である

削除候補の worktree にある untracked ファイルは正本と照合する述語を持たないため、ゲート A の対象として必ず人間の判断を要求する。同じ種類のファイルで毎回止まるのは、**worktree 内に判定不能な生成物を残す手順が上流にある**ということである。ゲートを緩めて解決してはならない。

報告時は「どのスキル・どの手順の生成物か」を添えて指摘し、生成側を次の原則へ合わせるよう促す。たとえば `.superpowers/sdd/` は superpowers の subagent-driven-development・executing-plans のスクリプト（`sdd-workspace`・`task-start`・`task-done`）の生成物で、ルート `AGENTS.md` の「SDD 実行運用」が置き場所を `tmp/agents/` に定めている。

**生成物は worktree の外（scratchpad / `mktemp -d`）に出す。** untracked が発生しないので手順 4 で止まらない。本スキルは worktree 直下の untracked を機械的に照合する述語を持たない。手順 6 のゲート A は `session.json` を持つ残骸ディレクトリ専用であり、worktree 内に残す限り毎回ユーザー確認になる。

`.gitignore` への追加で黙らせてはならない。gitignore 対象は、再生成できるキャッシュを除き、本スキルのガードレールで照合なしの削除を禁じており、`git status` からも消えるため、照合する術が無いまま残り続ける。

### 5. worktree を削除する

#### pr-review のセッションは helper で退役させる

手順 1 の `sessions` が `removable: true` を返し、手順 1 のオープン PR の対象外にも当たらない `/tmp/pr-review-*` のセッション（version 7・8 とも）は、先に helper の `reap-check` → `cleanup --strict-reap` で退役させる。`STATE_FILE` は候補ディレクトリ直下の `session.json` の絶対パスである。リポジトリのルートで、次の順に実行する。

1. `uv run --no-project python .agents/skills/pr-review/scripts/pr_review_workspace.py reap-check --allow-failed --state "$STATE_FILE"`
2. 1 の終了コードが 0（`status: "eligible"`）のときだけ、`uv run --no-project python .agents/skills/pr-review/scripts/pr_review_workspace.py cleanup --strict-reap --allow-failed --state "$STATE_FILE"`

- 終了コード 0（`status: "retired"`）: worktree・残骸・自セッションの ref の処理まで済んでいる。このセッションを下の通常の worktree 削除と手順 6 に回さない
- 終了コード 1: 退役しない。stdout の JSON（`status: "retained"`）の `reason`・`retirement`（`saved` か `failed`）・`stop_confirmation_needed`・`retained_paths` を控え、worktree ごと保持して手順 11 で報告する
- 終了コード 2: 引数の誤り、または状態を読めない。stderr の `error: ...` を控え、同じく保持して手順 11 で報告する
- `run_context` を持つセッションと version 8 のセッションは、helper が拒否しても、通常の worktree 削除や手順 6 へ迂回しない。`run_context` の無い version 7 のセッションだけは、終了コード 1 で拒否されたときに限り（終了コード 2 は状態を読めず `run_context` の有無も判定できないので、保持する）、下の今までの経路（手順 4 の clean の確認、`git worktree remove`、手順 6）を使える
- `--force` は付けない。helper を使わずに pr-review のディレクトリを `rm -rf` しない

拒否の `stop_confirmation_needed` が `true`（停止の確認だけが足りない失敗セッション）のときに限り、担当のプロセスと子孫の停止を実際に確かめた人が、その確認内容を空白だけでない理由にして `--operator-confirmed-stopped "$CONFIRMED_STOP_REASON"` を付け、`cleanup --strict-reap --allow-failed` を実行できる。年齢・PID が無いこと・モデルの `fail` は確認の代わりにならない。エージェントが理由を作らず、利用者が確認して指示したときだけ実行する。

#### 通常の worktree 削除

削除してよいのは、手順 4 で clean を確認し、ignore 対象が再生成できるキャッシュだけだった次の worktree に限る。

- 手順 3 でマージ済みと判定した branch を checkout している worktree
- 手順 1 の `sessions` が `removable: true` を返し、session.json が version 7 で `run_context` を持たず、手順 1 のオープン PR の対象外にも当たらず、上の helper が退役させなかった `/tmp/pr-review-*` の worktree

version 8 の session（`target_kind=checkout`・`bundle` とも）と `.staging/` は、helper の `cleanup --strict-reap` 以外の方法では削除しない。`removable: true` でも保存 pair・停止・所有の確認を省略できない。現行の helper で対応と所有を確認できない過去の session は、完全パスと理由を報告して保持する。

それ以外の worktree は削除せず、手順 11 で報告する。手順 1 で対象外にしたもの（オープン PR に対応するもの、`prunable`・`locked` のもの）のほかに、branch を checkout していない detached な worktree（PR 修正ループなど、別の run が作ったもの。上の `/tmp/pr-review-*` は除く）も対象外である。HEAD が `origin/main` から到達可能で clean でも、所有者が使っている作業場所かどうかは Git から分からない。`/tmp/pr-review-*` の worktree も detached だが、親の `session.json` に固定された所属リポジトリと PR 番号で、helper が PR の終了を確かめられるので、上の条件で選ぶ。

```bash
git worktree remove <path>
```

`--force` は付けない。`git worktree remove` が拒否した場合（未追跡のファイルがある、lock されているなど）は、理由をユーザーへ報告して止まる。

`git worktree remove` は対象の登録も消すので、続けて `git worktree prune` を実行しない。対象を限定しない `git worktree prune` は、片付け対象と関係の無い `prunable` な登録をすべて消す。repair 前の移動済み worktree の登録が消えると、`git worktree repair` で戻せず、移動先の本体は HEAD・index との対応を失う。存在しないパスへの `git worktree remove` も同じく登録を消すので、`prunable` な worktree に使わない。

worktree 本体の削除と、手順 6 の残骸削除は **別の判断**である。worktree 本体は追跡済みの内容であり、マージ済み・clean を確認していれば削除してよい。手順 6 で保留が発生しても、worktree 本体の削除まで止める必要はない。

### 6. ゲート A: 残骸ディレクトリは照合してから消す

`git worktree remove` は作業ツリーだけを消す。親ディレクトリに残る `session.json` や `review-backup/` は **git 管理外**であり、`git status` にも `git worktree list` にも現れない。

この手順は、`worktree/` が無くなった残骸ディレクトリだけに適用する。手順 1・5 で残した worktree を含むディレクトリは消さない。helper が拒否したセッションは、`run_context` の無い version 7 が終了コード 1 で拒否され、手順 5 の通常経路に進んだ場合を除き、worktree が無くても対象にしない。version 8、`run_context` を持つセッション、終了コード 2 のセッションは保持する。worktree を外してからこの手順で消す迂回をしない。停止未確認の失敗セッションを、年齢や PID の不在を根拠に即時に消さない。

残骸の `session.json` を版ごとに読む。version 7 は `main_root` + `destination` が正式保存先で、`pr_repository` と PR 番号も照合する。version 8 は `parent_root` + `destination` が本文で、候補の相対パスは helper の `findings_artifact_paths` が state の repository・PR 番号・model・commit から返す値を使い、同じ `parent_root` に結合する。`pr_repo` と PR 番号も照合する。候補パスを state の架空の欄から読んだり、手で命名したりしない。`target_root`（checkout または所有 bundle repository）へ保存先を結合しない。branch 名の変換で推測しない。

version 8 は本文と候補の pair・snapshot・bundle・実行記録を含み得るので、以下の version 7 のディレクトリ比較・単独 draft コピーを適用しない。レビューの共通 helper の通常 cleanup で照合できない残骸は保持し、所有者に完全パスと状態を報告する。未対応の回収コマンドや手動削除を組み立てない。version 6 以前、未知の版、state が無い・読めない場合も保持する。

**以下は version 7 の残骸だけ。** `main_root`・`destination`・`pr_repository` が読めず、repository/PR の対応を確かめられない場合、または結合した正式保存先がその checkout の `reviews/` 配下に無い場合は、削除せず停止する。相対パスの `..` や symlink による範囲外も拒否する。

`diff` の stdout・stderr は `mktemp -d` で作ったディレクトリに書き、同じブロックで表示してから消す。`/tmp` 直下の固定名のファイルは、並行するセッションの結果と混ざるので使わない。シェルの変数が次の呼び出しに残らないランタイムがあるので、ブロックは分けずに 1 回で実行する。

```bash
GATE=$(mktemp -d "${TMPDIR:-/tmp}/repo-cleanup-gate-a.XXXXXX") || exit 1
diff -rq <残骸ディレクトリ>/review-backup <正本ディレクトリ> > "$GATE/stdout" 2> "$GATE/stderr"
echo "diff の終了コード: $?"
echo '--- stderr ---'; cat -- "$GATE/stderr"
echo '--- stdout ---'; cat -- "$GATE/stdout"
rm -rf -- "${GATE:?}"
```

削除してよいのは、次をすべて満たすときだけである。空の `grep '^Only in .*review-backup'` だけを削除許可にしてはならない。

- `diff` の stderr（`--- stderr ---` の下）が空である。正本ディレクトリ不在はここに出る（終了コード 2）。stderr があれば削除しない
- stdout（`--- stdout ---` の下）に `Files ... differ` が無い
- stdout の `Only in ...review-backup` が、`previous-review.md` 以外に無い。`previous-review.md` はセッション snapshot であり、正本へコピーせず、この判定からも除外する

どれか一つでも欠ければ削除しない。

- `Only in ...review-backup` の対象が `<model>.md` なら正本へ `cp` する。コピーは非破壊であり、AskUserQuestion は不要。コピー後に上のブロックを実行し直す。ただし `session.json` に `pr_repository` が無い（version 6 以前の）残骸からはコピーしない。旧形式の保存先は fork と上流の PR で共有され得るので、所属を確かめられない draft を置かない。残骸を残し、パスを手順 11 で報告する
- `previous-review.md` は正本へコピーしない
- `Files ... differ` の `<model>.md` は正本を上書きしない。残すか別名退避するかをユーザーに確認し、確認が終わるまで残骸は消さない

```bash
cp <残骸ディレクトリ>/review-backup/<model>.md <正本ディレクトリ>/
```

`reviews/` は `.gitignore` 対象であり、git は一切保護しない。

### 7. メイン作業ツリーを origin/main の detached HEAD へ更新する

fork の経路ではこの手順を実行しない。「fork の経路だけの手順」を見る。

`usaturn/create-reso-world` では、ルート `AGENTS.md` に従い、ローカル `main` の有無にかかわらず detached HEAD にする。既存の `main` は古い・分岐している場合も変更せず保持する。作成・切り替え・reset・fast-forward は行わない。

入力 `MAIN_ROOT` は、手順 1 の `git worktree list --porcelain` の先頭の `worktree <絶対パス>`（メイン作業ツリー）から特定し、下のブロックを実行するシェルに事前に設定する。linked worktree やプロジェクトからの呼び出しでは、cwd や `git rev-parse --show-toplevel` の結果をメイン作業ツリーと取り違えない。パスを特定できなければ停止して報告する。

ブロック内でメイン作業ツリーの clean を再確認する。出力が空でない、または status が失敗した場合は checkout も後続の branch 削除もせず、ユーザーへ報告する。

続いて、HEAD と `origin/main` の tree 間で保護領域の追跡ファイル削除を read-only で調べる。取得失敗または削除対象が 1 件でもあれば、checkout と後続の branch 削除を停止する。`--no-renames` は、rename と判定されて元のパスの削除を見落とさないために必要である。

```bash
set -e
: "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}"
if ! tree_state=$(git -C "$MAIN_ROOT" status --short --untracked-files=all); then
    printf '%s\n' 'status の確認に失敗したため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if [ -n "$tree_state" ]; then
    printf '%s\n' "$tree_state"
    printf '%s\n' '作業ツリーが clean でないため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if ! deleted_world_paths=$(git -C "$MAIN_ROOT" diff --no-renames --name-only --diff-filter=D HEAD origin/main -- MyResoniteProject akichi slum02 slum03 worlds); then
    printf '%s\n' '保護領域の追跡ファイル削除を確認できないため、checkout と branch 削除を停止する。' >&2
    exit 1
fi
if [ -n "$deleted_world_paths" ]; then
    printf '%s\n' "$deleted_world_paths"
    printf '%s\n' '保護領域の追跡ファイルが削除されるため、checkout と branch 削除を停止する。README の「追跡解除コミットを取り込む」の保全手順を利用者へ案内する。' >&2
    exit 1
fi
if ! git -C "$MAIN_ROOT" checkout --detach --no-overwrite-ignore origin/main; then
    printf '%s\n' 'checkout に失敗したため、branch 削除を停止する。' >&2
    exit 1
fi
head_name=$(git -C "$MAIN_ROOT" rev-parse --abbrev-ref HEAD)
head_oid=$(git -C "$MAIN_ROOT" rev-parse HEAD)
origin_oid=$(git -C "$MAIN_ROOT" rev-parse origin/main)
if [ "$head_name" != HEAD ] || [ "$head_oid" != "$origin_oid" ]; then
    printf '%s\n' 'detached HEAD と origin/main の一致を確認できないため停止する。' >&2
    exit 1
fi
```

Git は通常 ignore 対象のファイルを確認なしに上書きするため、`--no-overwrite-ignore` を外さない。ただし、clean でも `--no-overwrite-ignore` でも追跡ファイルの削除は防げない。保護領域の削除検査を外したり、自動復元や `--force` で回避したりしない。checkout が失敗したらエラーを報告して停止し、`--force`・clean・reset や `main` への切り替えで回避しない。成功後も既存ローカル `main` は保持対象として報告し、手順 8 で削除しない。

### 8. マージ済みローカル branch を削除する

手順 7 が成功したあとで実行する（fork の経路では手順 7 を省略する）。手順 7 で停止した場合は branch 削除に進まない。`usaturn/create-reso-world` の既存ローカル `main` と、fork の経路では `external/resoloop` のローカル `main` は、マージ済みでも候補から必ず除外し、そのまま保持する。メイン作業ツリーが feature を checkout したままだと `git branch -d` は `used by worktree` / `checked out` で失敗する。

削除先は `CLEANUP_ROUTE`（`create`・`fork`・`managed`）で決める。ツール呼び出しごとにシェルや環境変数が引き継がれない実行環境があるため、手順 7 と別の呼び出しでこのブロックを実行するときも、その呼び出しで経路と削除先を設定する。経路の条件を満たさないときは、branch・ref・HEAD を何も変えずに削除の前で停止する。

- `create`（`usaturn/create-reso-world`）: 手順 7 で clean と detached HEAD を確認した `MAIN_ROOT` だけを削除先にする。`TARGET_ROOT` が同時に設定されていて別の checkout を指す場合は、どちらも削除せず停止する。`EXPECTED_HEAD_REPO` は環境に残っていても空にし、cross-repository の PR を受け付けない
- `fork`（`external/resoloop`）: `PARENT_ROOT` に親の create-reso-world main checkout、`TARGET_ROOT` に `$PARENT_ROOT/external/resoloop` の絶対パス、`EXPECTED_HEAD_REPO` に checkout の origin の `usaturn/resoloop`、`BASE_REF` に上流 PR なら `upstream/main`、fork 内 PR なら `origin/main` を設定する。削除の前に `TARGET_ROOT` が `$PARENT_ROOT/external/resoloop` と一致することを確かめ、一致しなければ削除しない。上流 PR は head repository が `EXPECTED_HEAD_REPO` と一致するときだけ取り込み済みと判定する。手順 7 を省略し、削除のために HEAD を動かさない。`MAIN_ROOT` は要求せず、設定するなら `TARGET_ROOT` と同じ checkout のときだけ許可する
- `managed`（通常ツール）: 対象照合の `CLEANUP_ROOT` を削除先にする。`EXPECTED_HEAD_REPO` は環境に残っていても空にする

`CLEANUP_ROUTE` を設定しないときは、`MAIN_ROOT` だけが設定され `TARGET_ROOT` が未設定なら `create` とみなす。それ以外（特に `MAIN_ROOT` が未設定で `TARGET_ROOT` だけが残っている場合）は、古い `TARGET_ROOT` が同じ remote の別 clone を指している可能性があるため停止する。

`git branch -d` の前に、同じシェルで「branch の取り込み判定」を実行し、`PR_NUMBER`（手順 3 で確定した値）、`BASE_REF`（手順 3 と同じ取り込み先）、`PR_REPO` を設定する。`-d` は upstream や実行先の HEAD を基準にするので、それだけでは選択した base への取り込みを確かめられない。判定を先に通し、`-d` が成功しても別 base の upstream を根拠に削除されないようにする。`-D` は、`-d` が `not fully merged` で拒否したときに、同じ判定をもう一度通した branch だけに使う。

```bash
set -e
cleanup_same_checkout() {
  local left right
  if ! left=$(cd -- "$1" 2>/dev/null && pwd -P) || ! right=$(cd -- "$2" 2>/dev/null && pwd -P); then
    printf '%s と %s の checkout を確認できないため削除しない\n' "$3" "$4" >&2
    return 1
  fi
  if [ "$left" != "$right" ]; then
    printf '%s と %s が別の checkout を指すため削除しない\n' "$3" "$4" >&2
    return 1
  fi
}
route=${CLEANUP_ROUTE:-}
if [ -z "$route" ]; then
  if [ -n "${MAIN_ROOT:-}" ] && [ -z "${TARGET_ROOT:-}" ]; then
    route=create
  else
    printf '%s\n' 'CLEANUP_ROUTE（create・fork・managed）を決められないため削除しない。create-reso-world では MAIN_ROOT を設定する' >&2
    exit 1
  fi
fi
case "$route" in
  create)
    : "${MAIN_ROOT:?create の経路では MAIN_ROOT（メイン作業ツリーの絶対パス）を設定する}"
    if [ -n "${TARGET_ROOT:-}" ]; then
      cleanup_same_checkout "$MAIN_ROOT" "$TARGET_ROOT" MAIN_ROOT TARGET_ROOT || exit 1
    fi
    DELETE_ROOT=$MAIN_ROOT
    EXPECTED_HEAD_REPO=
    ;;
  fork)
    : "${TARGET_ROOT:?fork の経路では TARGET_ROOT（external/resoloop の絶対パス）を設定する}"
    : "${EXPECTED_HEAD_REPO:?fork の経路では EXPECTED_HEAD_REPO（checkout の origin の owner/name）を設定する}"
    : "${PARENT_ROOT:?fork の経路では親の create-reso-world checkout（PARENT_ROOT）を設定する}"
    if ! fork_expected=$(cd -- "$PARENT_ROOT/external/resoloop" 2>/dev/null && pwd -P) \
      || ! fork_target=$(cd -- "$TARGET_ROOT" 2>/dev/null && pwd -P) \
      || [ "$fork_expected" != "$fork_target" ]; then
      printf '%s\n' 'fork の経路の TARGET_ROOT が親 checkout の external/resoloop と一致しないため削除しない' >&2
      exit 1
    fi
    if [ -n "${MAIN_ROOT:-}" ]; then
      cleanup_same_checkout "$MAIN_ROOT" "$TARGET_ROOT" MAIN_ROOT TARGET_ROOT || exit 1
    fi
    DELETE_ROOT=$TARGET_ROOT
    ;;
  managed)
    : "${CLEANUP_ROOT:?managed の経路では対象照合の CLEANUP_ROOT を設定する}"
    DELETE_ROOT=$CLEANUP_ROOT
    EXPECTED_HEAD_REPO=
    ;;
  *)
    printf 'CLEANUP_ROUTE が不明なため削除しない: %s\n' "$route" >&2
    exit 1
    ;;
esac
: "${PR_REPO:?対象 repository}" "${PR_NUMBER:?対応 PR}" "${BASE_REF:?取り込み先 base ref}"
BRANCH=<branch>
EVIDENCE=$(cleanup_branch_evidence "$DELETE_ROOT" "$PR_REPO" "$PR_NUMBER" "$BRANCH" "refs/heads/$BRANCH" "$BASE_REF" "$EXPECTED_HEAD_REPO") || {
  printf 'branch %s の取り込みを確認できないため削除しない\n' "$BRANCH" >&2
  exit 1
}
printf '取り込みの証拠: %s (%s)\n' "$BRANCH" "$EVIDENCE"
if ! branch_delete_output=$(LC_ALL=C git -C "$DELETE_ROOT" branch -d "$BRANCH" 2>&1); then
  printf '%s\n' "$branch_delete_output" >&2
  case "$branch_delete_output" in
    *"not fully merged"*) ;;
    *) exit 1 ;;
  esac
  EVIDENCE=$(cleanup_branch_evidence "$DELETE_ROOT" "$PR_REPO" "$PR_NUMBER" "$BRANCH" "refs/heads/$BRANCH" "$BASE_REF" "$EXPECTED_HEAD_REPO") || {
    printf 'branch %s の取り込みを再確認できないため削除しない\n' "$BRANCH" >&2
    exit 1
  }
  printf '取り込みの証拠: %s (%s)\n' "$BRANCH" "$EVIDENCE"
  git -C "$DELETE_ROOT" branch -D "$BRANCH"
else
  printf '%s\n' "$branch_delete_output"
fi
```

`-d` が拒否した場合、理由で分岐する。拒否を未マージと同一視しない。

- `used by worktree` または `checked out`: 未マージではない。手順 7 が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、この branch は削除しない
- `not fully merged`: そのまま未マージと断定しない。`-d` の取り込み判定は upstream と実行先の HEAD を基準にするため、upstream の remote-tracking ref が削除・prune 済みのときや、実行先の HEAD がその branch の取り込み点より古いときは、取り込み済みでも拒否される。fork の経路では削除のために HEAD を動かさないので、古い detached HEAD へのこの拒否は普通に起きる。上のブロックは、この場合だけ同じ判定をもう一度実行し、`ancestor` または `pr` を再確認できた branch に限り `-D` を使う。未取り込み、または再確認できない場合は削除せず、手順 3 の結果とともにユーザーへ報告する。`-D` も worktree に掴まれた branch は拒否する

detached HEAD で `-d` が upstream を根拠に成功するときは、次の warning が出るが、**削除が成功していれば正常**である。選択した base への取り込みは事前の判定で確認済みであり、拒否ではない。

```
warning: deleting branch '<branch>' that has been merged to
         'refs/remotes/origin/<branch>', but not yet merged to HEAD
```

### 9. ゲート B: リモート branch の削除はユーザー確認を得る

手順 8 でローカル branch を消すと対象名が手元から消える。リモート側から独立に洗い出す。祖先の一覧だけに限定せず、手順 3 と同じ「branch の取り込み判定」で `ancestor` または `pr` が返る branch を提示する。PR の照会先（`PR_REPO`）、取り込み先 base（`BASE_REF`）、削除元 remote（`REMOTE`）を区別する。`REMOTE` は削除する head branch がある remote で、PR の head repository に対応させる。create-reso-world は `origin`、通常ツールは `CLEANUP_BASE_REMOTE`（same-repository の head remote）、fork は上流 PR でも fork 内 PR でも `origin`（検証済みの head repository `usaturn/resoloop`）にする。fork→上流の PR では、`PR_REPO` は PR が属する `orange3134/resoloop`、`BASE_REF` は `upstream/main` だが、`REMOTE` は `upstream` にしない。`PR_REPO` や `BASE_REF` の remote に合わせると、同名・同 OID の上流 branch を fork の PR を根拠に候補にし、承認後の `git -C "$CHECKOUT" push "$REMOTE" --delete` も上流を指す。`BASE_REF` と `EXPECTED_HEAD_REPO` は手順 3 と同じにする。`REMOTE` の URL は、期待する repository（fork の経路では `EXPECTED_HEAD_REPO`、create・managed では `PR_REPO`）と照合する。`git remote get-url --all` と `git remote get-url --push --all` で fetch URL と push URL をすべて読み、1 件ずつ GitHub の `owner/name` に正規化し（`git@github.com:`、`ssh://git@github.com/`、`https://github.com/` の形。平文 HTTP は受け付けない。末尾の `/` をすべて除いてから末尾の `.git` を除くので、`.../resoloop/`・`.../resoloop.git`・`.../resoloop.git/` は同じ repository になる）、期待する repository と大小文字を区別せずに比べる。承認後の `git push` は設定されたすべての push URL へ送るため、fetch URL や最初の 1 件だけを確かめない。1 件でも一致しない・解釈できない URL があれば、候補を出さずに停止する。削除と prune は `git -C "$CHECKOUT"` で検証済みの checkout に対して実行し、cwd の repository に依存させない。ゲート B も `cleanup_expected_head_repo` で `EXPECTED_HEAD_REPO` を経路から決め、create・managed（未設定を含む）では空にして、環境に残った値で cross-repository の PR を候補にしない。`BASE_REF` は `origin/main` と `refs/remotes/origin/main` のどちらでもよいため、比較の前に base の branch 名へ正規化し、一覧の ref 名と直接比べない。

```bash
set -euo pipefail
: "${CHECKOUT:?対象 checkout}" "${PR_REPO:?対象 repository}" "${REMOTE:?対象 remote}" "${BASE_REF:?取り込み先 base ref}"
EXPECTED_HEAD_REPO=$(cleanup_expected_head_repo) || exit 1
# 削除元 remote は、fork では検証済みの head repository、create・managed では PR_REPO だけにする。
# 承認後の push は設定されたすべての push URL へ送るため、fetch と push の全 URL を確かめる。
expected_repo=${EXPECTED_HEAD_REPO:-$PR_REPO}
expected_key=$(printf '%s' "$expected_repo" | LC_ALL=C tr '[:upper:]' '[:lower:]')
for remote_kind in fetch push; do
  if [ "$remote_kind" = push ]; then
    remote_urls=$(git -C "$CHECKOUT" remote get-url --push --all "$REMOTE") || {
      printf 'cleanup: remote %s の push URL を読めないため候補を出さない\n' "$REMOTE" >&2
      exit 1
    }
  else
    remote_urls=$(git -C "$CHECKOUT" remote get-url --all "$REMOTE") || {
      printf 'cleanup: remote %s の fetch URL を読めないため候補を出さない\n' "$REMOTE" >&2
      exit 1
    }
  fi
  if [ -z "$remote_urls" ]; then
    printf 'cleanup: remote %s の %s URL が無いため候補を出さない\n' "$REMOTE" "$remote_kind" >&2
    exit 1
  fi
  while IFS= read -r remote_url; do
    if ! remote_key=$(cleanup_remote_repo_key "$remote_url"); then
      printf 'cleanup: remote %s の %s URL を GitHub の owner/name として解釈できないため候補を出さない: %s\n' "$REMOTE" "$remote_kind" "$remote_url" >&2
      exit 1
    fi
    if [ "$remote_key" != "$expected_key" ]; then
      printf 'cleanup: remote %s の %s URL（%s）が期待する repository %s と一致しないため候補を出さない\n' "$REMOTE" "$remote_kind" "$remote_url" "$expected_repo" >&2
      exit 1
    fi
  done <<EOF_URLS
$remote_urls
EOF_URLS
done
case "$BASE_REF" in
  refs/remotes/*/*) base_branch=${BASE_REF#refs/remotes/*/} ;;
  refs/heads/*) base_branch=${BASE_REF#refs/heads/} ;;
  */*) base_branch=${BASE_REF#*/} ;;
  *) base_branch=$BASE_REF ;;
esac
printf '%s\n' 'リモート branch の候補（削除はまだ行わない）:'
git -C "$CHECKOUT" for-each-ref --format='%(refname)' "refs/remotes/$REMOTE" | while IFS= read -r remote_ref; do
  branch=${remote_ref#"refs/remotes/$REMOTE/"}
  if [ "$branch" = HEAD ] || [ "$branch" = "$base_branch" ]; then
    continue
  fi
  if ! PR_NUMBER=$(cleanup_branch_pr_number "$CHECKOUT" "$PR_REPO" "$branch" "$remote_ref"); then
    printf '保持: %s（対応 PR を 1 件に確定できない）\n' "$branch" >&2
    continue
  fi
  if EVIDENCE=$(cleanup_branch_evidence "$CHECKOUT" "$PR_REPO" "$PR_NUMBER" "$branch" "$remote_ref" "$BASE_REF" "$EXPECTED_HEAD_REPO"); then
    printf '候補: %s (%s, PR #%s)\n' "$branch" "$EVIDENCE" "$PR_NUMBER"
  else
    printf '保持: %s（取り込みを確認できない）\n' "$branch" >&2
  fi
done
```

候補が複数ある場合は、上の出力の PR 番号を添えて提示する。対応する PR が見つからないリモート branch は候補から外し、そのまま残す。手順 1 で整理対象外にしたオープン PR の `headRefName` に一致する branch は、上の出力に候補として出ても削除候補にしない。

マージ済みでも、リモート branch の削除を独断で実行しない。対象を提示してユーザー確認を求め（Claude Code では AskUserQuestion を使う）、承認を得てから実行する。

```bash
git -C "$CHECKOUT" push "$REMOTE" --delete <branch>
git -C "$CHECKOUT" fetch --prune "$REMOTE"
```

### 残存 pinned ref を整理する

手順 9 のあと、手順 11 の前に実行する。fork の経路では手順 10 の sync を先に済ませてから実行する。`git for-each-ref` で `refs/pr-review` を一覧し、セッションを持たない ref も含めて、対応する repository と PR を確定できたものだけを片付ける。オブジェクト自体は PR の取得元に残るが、レビュー中の session が読む ref を消すと取得先を壊すため、PR の終了だけで決めない。

- `REF_CHECKOUT`: ref を読む checkout（create-reso-world は `MAIN_ROOT`、通常ツールは `CLEANUP_ROOT`、fork は `external/resoloop`）
- `REF_REPOS`: 旧形式 `refs/pr-review/<N>` の候補 repository。create-reso-world と通常ツールは `PR_REPO` だけ、fork の経路は `usaturn/resoloop` と `orange3134/resoloop` を改行で並べる。新形式 `refs/pr-review/repos/<owner>/<repo>/<N>` は ref 名の repository を使う
- `REF_SESSION_ROOT`: pr-review が使った一時ルート。既定は `${TMPDIR:-/tmp}`。別の `--temp-root` を使った可能性を排除できない場合は削除しない
- `REF_INVENTORY`: 一覧で読んだ `(ref, OID)` を保存するファイル。`mktemp` で作った一意のパスを指定し、削除ではこの保存値だけを使う

手順 1 の helper の `sessions` は登録済み worktree だけを列挙し、セッションを持たない ref、登録の無い残骸、bundle、別の `--temp-root` のセッションを網羅しない。helper が同じ repository と PR の session を保持と返したら、その ref は削除しない。下の関数は `REF_SESSION_ROOT` の `pr-review-*` も調べるが、これも全一覧ではない。保持中の session や所属を確定できないときは、その ref を保持して手順 11 で報告する。symbolic ref は参照先の branch を消さないように一覧に載せず、保持として報告する。session の所属は repository・PR 番号の型と形式を確かめ、読めない・不正な値は「別の PR」とみなさず保持する。GitHub の repository 名は大小文字を区別しないため、ref と session の repository 名は小文字に正規化して比較する。

```bash
cleanup_residual_ref_inventory() {
  if [ "$#" -ne 1 ]; then
    printf '%s\n' 'cleanup: 残存 ref 一覧の引数が足りない' >&2
    return 2
  fi
  local checkout=$1 ref oid symref listing
  if ! listing=$(git -C "$checkout" for-each-ref --format='%(refname) %(objectname) %(symref)' refs/pr-review); then
    return 1
  fi
  while IFS=' ' read -r ref oid symref; do
    [ -n "$ref" ] || continue
    if [ -n "$symref" ]; then
      cleanup_residual_ref_keep "$ref" "symbolic ref は削除しない: $symref"
      continue
    fi
    printf '%s %s\n' "$ref" "$oid"
  done <<< "$listing"
}

cleanup_residual_ref_keep() {
  printf '保持: %s（%s）\n' "$1" "$2" >&2
}

cleanup_residual_ref_repo_key() {
  printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'
}

cleanup_residual_ref_same_checkout() {
  local left=$1 right=$2
  [ -d "$left" ] && [ -d "$right" ] || return 1
  [ "$(cd -- "$left" && pwd -P)" = "$(cd -- "$right" && pwd -P)" ]
}

cleanup_residual_ref_retire() {
  if [ "$#" -ne 3 ]; then
    printf '%s\n' 'cleanup: 残存 ref の引数が足りない' >&2
    return 2
  fi
  local checkout=$1 ref=$2 expected=$3
  local number rest owner repo_name pr_json fields reported state head
  local session_root session_dir session_name version session_repo session_number
  local session_main_root target_kind target_root current current_symref symref status
  local -a repos=()
  case "$expected" in
    ''|*[!0-9a-f]*)
      cleanup_residual_ref_keep "$ref" '読んだ ref の値が commit SHA ではない'
      return 1
      ;;
  esac
  if symref=$(git -C "$checkout" symbolic-ref -q "$ref"); then
    cleanup_residual_ref_keep "$ref" "symbolic ref は削除しない: $symref"
    return 1
  else
    status=$?
    if [ "$status" -ne 1 ]; then
      cleanup_residual_ref_keep "$ref" 'ref の種別を確認できない'
      return 1
    fi
  fi
  case "$ref" in
    refs/pr-review/repos/*)
      rest=${ref#refs/pr-review/repos/}
      owner=${rest%%/*}
      rest=${rest#*/}
      repo_name=${rest%%/*}
      number=${rest#*/}
      case "$owner" in
        ''|*[!A-Za-z0-9-]*)
          cleanup_residual_ref_keep "$ref" 'repository を確定できない'
          return 1
          ;;
      esac
      case "$repo_name" in
        ''|*[!A-Za-z0-9._-]*)
          cleanup_residual_ref_keep "$ref" 'repository を確定できない'
          return 1
          ;;
      esac
      case "$number" in
        ''|*[!0-9]*)
          cleanup_residual_ref_keep "$ref" 'PR 番号を確定できない'
          return 1
          ;;
      esac
      repos=("$(cleanup_residual_ref_repo_key "$owner/$repo_name")")
      ;;
    refs/pr-review/*)
      number=${ref#refs/pr-review/}
      case "$number" in
        ''|*[!0-9]*)
          cleanup_residual_ref_keep "$ref" '旧形式 ref の PR 番号を確定できない'
          return 1
          ;;
      esac
      if [ -z "${REF_REPOS:-}" ]; then
        cleanup_residual_ref_keep "$ref" '旧形式 ref の所属 repository が未設定'
        return 1
      fi
      while IFS= read -r repo_name; do
        [ -n "$repo_name" ] && repos+=("$(cleanup_residual_ref_repo_key "$repo_name")")
      done <<< "$REF_REPOS"
      if [ "${#repos[@]}" -ne 1 ]; then
        cleanup_residual_ref_keep "$ref" '旧形式 ref の所属 repository を一意に確定できない'
        return 1
      fi
      ;;
    *)
      cleanup_residual_ref_keep "$ref" '残存 pinned ref の形式ではない'
      return 1
      ;;
  esac
  for repo_name in "${repos[@]}"; do
    if ! pr_json=$(gh pr view "$number" --repo "$repo_name" --json number,state,headRefOid); then
      cleanup_residual_ref_keep "$ref" "PR $repo_name#$number の状態を照会できない"
      return 1
    fi
    if ! fields=$(printf '%s' "$pr_json" | jq -er '[.number, .state, .headRefOid] | @tsv'); then
      cleanup_residual_ref_keep "$ref" "PR $repo_name#$number の応答を読めない"
      return 1
    fi
    IFS=$'\t' read -r reported state head <<< "$fields"
    if [ "$reported" != "$number" ] || [ -z "$state" ] || [ -z "$head" ]; then
      cleanup_residual_ref_keep "$ref" "PR $repo_name#$number の応答が一致しない"
      return 1
    fi
    case "$state" in
      MERGED|CLOSED) ;;
      *)
        cleanup_residual_ref_keep "$ref" "PR $repo_name#$number が $state"
        return 1
        ;;
    esac
  done
  session_root=${REF_SESSION_ROOT:-${TMPDIR:-/tmp}}
  if [ ! -d "$session_root" ]; then
    cleanup_residual_ref_keep "$ref" 'session の一時ルートを確認できない'
    return 1
  fi
  for session_dir in "$session_root"/pr-review-*; do
    if [ ! -e "$session_dir" ] && [ ! -L "$session_dir" ]; then
      continue
    fi
    session_name=${session_dir##*/}
    case "$session_name" in
      "pr-review-$number-"*) ;;
      *) continue ;;
    esac
    if [ -L "$session_dir" ] || [ ! -f "$session_dir/session.json" ]; then
      cleanup_residual_ref_keep "$ref" "session の状態を確認できない: $session_dir"
      return 1
    fi
    if ! version=$(jq -er 'if type == "object" then .version else error("not an object") end' "$session_dir/session.json" 2>/dev/null); then
      cleanup_residual_ref_keep "$ref" "session の状態を読めない: $session_dir"
      return 1
    fi
    case "$version" in
      7)
        if ! session_repo=$(jq -er '
          if (.pr_repository | type) == "string"
            and (.pr_repository | test("^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$"))
          then .pr_repository else error("invalid pr_repository") end
        ' "$session_dir/session.json" 2>/dev/null) \
          || ! session_number=$(jq -er '
            if (.pr_number | type) == "number" then
              (if .pr_number > 0 and .pr_number == (.pr_number | floor)
               then (.pr_number | floor) else error("invalid pr_number") end)
            elif (.pr_number | type) == "string" then
              (if (.pr_number | test("^[1-9][0-9]*$"))
               then .pr_number else error("invalid pr_number") end)
            else error("invalid pr_number") end
          ' "$session_dir/session.json" 2>/dev/null) \
          || ! session_main_root=$(jq -er '
            if (.main_root | type) == "string" and (.main_root | length) > 0
            then .main_root else error("invalid main_root") end
          ' "$session_dir/session.json" 2>/dev/null); then
          cleanup_residual_ref_keep "$ref" "session の所属を読めない: $session_dir"
          return 1
        fi
        if [ -z "$session_repo" ] || [ -z "$session_number" ] || [ -z "$session_main_root" ]; then
          cleanup_residual_ref_keep "$ref" "session の所属が欠けている: $session_dir"
          return 1
        fi
        session_repo=$(cleanup_residual_ref_repo_key "$session_repo")
        if [ "$session_number" != "$number" ] || [ "$session_repo" != "${repos[0]}" ]; then
          continue
        fi
        if ! cleanup_residual_ref_same_checkout "$session_main_root" "$checkout"; then
          if [ ! -d "$session_main_root" ]; then
            cleanup_residual_ref_keep "$ref" "session の checkout を確認できない: $session_dir"
            return 1
          fi
          continue
        fi
        cleanup_residual_ref_keep "$ref" "保持中の session がある: $session_dir"
        return 1
        ;;
      8)
        if ! session_repo=$(jq -er '
          if (.pr_repo | type) == "string"
            and (.pr_repo | test("^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$"))
          then .pr_repo else error("invalid pr_repo") end
        ' "$session_dir/session.json" 2>/dev/null) \
          || ! session_number=$(jq -er '
            if (.pr_number | type) == "number" then
              (if .pr_number > 0 and .pr_number == (.pr_number | floor)
               then (.pr_number | floor) else error("invalid pr_number") end)
            elif (.pr_number | type) == "string" then
              (if (.pr_number | test("^[1-9][0-9]*$"))
               then .pr_number else error("invalid pr_number") end)
            else error("invalid pr_number") end
          ' "$session_dir/session.json" 2>/dev/null) \
          || ! target_kind=$(jq -er '
            if (.target_kind | type) == "string" and (.target_kind | length) > 0
            then .target_kind else error("invalid target_kind") end
          ' "$session_dir/session.json" 2>/dev/null); then
          cleanup_residual_ref_keep "$ref" "session の所属を読めない: $session_dir"
          return 1
        fi
        if [ -z "$session_repo" ] || [ -z "$session_number" ] || [ -z "$target_kind" ]; then
          cleanup_residual_ref_keep "$ref" "session の所属が欠けている: $session_dir"
          return 1
        fi
        session_repo=$(cleanup_residual_ref_repo_key "$session_repo")
        if [ "$session_number" != "$number" ] || [ "$session_repo" != "${repos[0]}" ]; then
          continue
        fi
        case "$target_kind" in
          owned-history)
            continue
            ;;
          checkout)
            if ! target_root=$(jq -er '
              if (.target_root | type) == "string" and (.target_root | length) > 0
              then .target_root else error("invalid target_root") end
            ' "$session_dir/session.json" 2>/dev/null); then
              cleanup_residual_ref_keep "$ref" "session の checkout を読めない: $session_dir"
              return 1
            fi
            if ! cleanup_residual_ref_same_checkout "$target_root" "$checkout"; then
              if [ ! -d "$target_root" ]; then
                cleanup_residual_ref_keep "$ref" "session の checkout を確認できない: $session_dir"
                return 1
              fi
              continue
            fi
            cleanup_residual_ref_keep "$ref" "保持中の session がある: $session_dir"
            return 1
            ;;
          *)
            cleanup_residual_ref_keep "$ref" "session の対象種別を確認できない: $session_dir"
            return 1
            ;;
        esac
        ;;
      *)
        cleanup_residual_ref_keep "$ref" "未知の version の session がある: $session_dir"
        return 1
        ;;
    esac
  done
  if ! fields=$(git -C "$checkout" for-each-ref --format='%(objectname) %(symref)' "$ref"); then
    cleanup_residual_ref_keep "$ref" 'ref の現在値を読めない'
    return 1
  fi
  IFS=' ' read -r current current_symref <<< "$fields"
  if [ -n "$current_symref" ]; then
    cleanup_residual_ref_keep "$ref" "symbolic ref は削除しない: $current_symref"
    return 1
  fi
  if [ "$current" != "$expected" ]; then
    cleanup_residual_ref_keep "$ref" '読み取り後に ref の値が変わった'
    return 1
  fi
  if ! git -C "$checkout" update-ref --no-deref -d "$ref" "$expected"; then
    cleanup_residual_ref_keep "$ref" 'ref を compare-and-delete できない'
    return 1
  fi
  printf '削除: %s %s\n' "$ref" "$expected"
}
```

最初に一覧だけを表示し、`(ref, OID)` を `REF_INVENTORY` に保存する。削除はまだ行わない。

```bash
set -euo pipefail
: "${REF_CHECKOUT:?ref を読む checkout}" "${REF_REPOS:?旧形式 ref の候補 repository}" "${REF_INVENTORY:?一覧を保存するファイル}"
printf '%s\n' "残存 pinned ref（削除はまだ行わない。一覧: $REF_INVENTORY）:"
cleanup_residual_ref_inventory "$REF_CHECKOUT" | tee "$REF_INVENTORY"
```

一覧の各 ref について、上の関数を実行する。`REF_OID` は `REF_INVENTORY` に保存した一覧の値をそのまま渡す。削除の前に inventory を取り直さず、保存した値と現在値が違えば保持する。

```bash
set -euo pipefail
: "${REF_CHECKOUT:?ref を読む checkout}" "${REF_REPOS:?旧形式 ref の候補 repository}" "${REF_INVENTORY:?一覧を保存したファイル}"
REF_SESSION_ROOT="${REF_SESSION_ROOT:-${TMPDIR:-/tmp}}"
while IFS=' ' read -r REF REF_OID; do
  [ -n "$REF" ] || continue
  cleanup_residual_ref_retire "$REF_CHECKOUT" "$REF" "$REF_OID" || true
done < "$REF_INVENTORY"
```

### 10. resoloop の上流に追従する（fork の経路だけ）

上流 `orange3134/resoloop` で PR がマージされたら、fork の `main` を上流へ追従させる。リポジトリのルートで実行する。fork の経路ではこの手順を手順 3 の判定より先に行う。「fork の経路だけの手順」を見る。

```bash
bash scripts/resoloop-fork.sh sync
```

`sync` は fork（`usaturn/resoloop`）の `main` へ push するので、ゲート B と同じくユーザー確認を得てから実行する（Claude Code では AskUserQuestion を使う）。fork の `main` に上流に無いコミットがある場合、スクリプトは何も push せずに止まる。`external/resoloop` で `main` を checkout していて未コミットの変更がある場合は、fork の `main` への push を済ませてから、ローカルの `main` を動かさずに止まる（出力に `origin/main is already synced` と出る）。その出力をそのまま報告し、手で push や reset をしない。詳しい流れは `docs/resoloop-fork-workflow.md` にある。

### 11. 最終状態を報告する

以下は `usaturn/create-reso-world` 用である。status は更新対象の `MAIN_ROOT` で確認する。手順 8 と同様、このブロックを実行する呼び出しでも `MAIN_ROOT` を設定する。fork の経路では、リポジトリのルートで各 Git コマンドに `-C external/resoloop` を指定し、最初の行は `git -C external/resoloop status` に読み替える。fork では `MAIN_ROOT` の設定を要求しない。

```bash
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" status
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" worktree list
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" branch -a
```

`usaturn/create-reso-world` では `MAIN_ROOT` の HEAD が detached で `origin/main` と一致することを報告する。既存ローカル `main` と、それを checkout している他 worktree は「変更せず保持」として報告する。削除した対象、保留した対象、その理由も報告する。残存 pinned ref を削除または保持した場合は、ref 名・repository・PR・理由を報告する。

手順 1 で控えた `prunable`・`locked` な worktree と、`sessions` が `removable: false` を返した `/tmp/pr-review-*`（`reason` を添える）と、手順 4・5 で削除しなかった worktree は、パスと理由（`prunable` や `locked` の行の内容、`git -C` の終了コード、branch を持たない別 run の worktree であること）を添えて、所有者の確認が要るものとして報告する。移動済みの worktree は、所有者が移動先を確かめて `git worktree repair <移動先>` を個別に行う。本体が無い登録は、所有する run の停止と対応を確かめた所有者が、対象を限定して回収を判断する。このスキルでは repair も回収も行わない。

手順 5 で helper が退役させたセッションは、退役済みとして報告する。helper が拒否したセッション（終了コード 1・2）は、ディレクトリのパスと `reason`（終了コード 2 は stderr の `error: ...`）、`retirement`、`stop_confirmation_needed`、`retained_paths` を添えて、所有者の確認が要るものとして報告する。`stop_confirmation_needed: true` のものは、担当と子孫の停止を確かめた人の確認が要ると明記する。

## Red Flags: 手を止めてワークフローに戻る

- 「Merge 済みなので役目は終えている」を根拠に git 管理外ファイルを消そうとしている
- 「ディレクトリ名が `stale` / `tmp` / `pr-review-*` だから」を削除の根拠にしている
- 中身を正本と照合せずに「軽微なメモ」「レビューのメタデータ」と分類している
- `rm -rf` を実行しようとしているが、直前に `diff` または `cmp` を実行していない
- `Files ... differ` や `diff` の失敗を無視して「固有ファイルが無いから消してよい」としている
- 手順 5 の削除対象に当たらない worktree を、「実体が無い」「`prunable`」「HEAD が `origin/main` から到達可能」を根拠に消そうとしている
- 一括 `git worktree prune` の代わりに、`prunable` な登録を `git worktree remove` で 1 件ずつ消そうとしている
- リモート branch を削除してから「不要なら戻せます」と報告しようとしている
- 「時間が無い」「手早く」と言われたので確認を飛ばそうとしている
- `git worktree remove` の前に `status --short --ignored` を見ていない
- `/tmp/pr-review-*` の session を、番号・branch・commit の一致や、片方のリポジトリの PR 一覧に無いことを根拠に、終了した PR のものとみなそうとしている
- helper が拒否した pr-review のセッションを、`run_context` の無い version 7 が終了コード 1 で拒否された場合以外に、`git worktree remove` で worktree を外してから手順 6 で消そうとしている。version 8・`run_context` 有り・終了コード 2 を保持せずに進もうとしている。`--operator-confirmed-stopped` の理由をエージェントが作ろうとしている
- `refs/pr-review/*` を、`git for-each-ref` の一覧だけで一括削除しようとしている。所属 repository と PR、PR の終了、open PR・保持中 session の非使用を確かめていない
- session が無い、または helper の `sessions` が何も返さないことを、ref を削除してよい証拠にしている。登録の無い残骸・bundle・別の一時ルートを確認していない
- `git update-ref -d <ref>` を読んだ値なしで実行している、または並行更新で失敗した削除を新しい値でやり直している
- symbolic ref を通常の pin として削除しようとしている。一覧で読んだ値を保存せず、削除の前に inventory を取り直している。session の repository・PR 番号が配列や数値など不正な型なのに、別の PR の session として無視している
- 旧形式 `refs/pr-review/<N>` を、fork と上流の片方の PR が終了しただけで消そうとしている
- `git log --oneline <base>..<branch>` が非空だから未取り込み、空だから取り込み済みと決めつけている。PR と head の対応、squash/rebase の `mergeCommit` を確かめていない
- `git branch -d` が成功したので、選択した base に取り込まれているとみなしている。upstream がその branch 自身を指していても `-d` は成功する
- `TARGET_ROOT` の既存値が手順 7 の `MAIN_ROOT` と別の checkout を指しているのに、片方を削除先に選ぼうとしている
- `MAIN_ROOT` が未設定で `TARGET_ROOT` だけが残っているシェルで、`CLEANUP_ROUTE` を確かめずに `TARGET_ROOT` を削除先にしようとしている
- fork の経路で、`TARGET_ROOT` が `$PARENT_ROOT/external/resoloop` と一致することを確かめずに、残った `CLEANUP_ROUTE=fork` で別 clone を削除しようとしている
- cross-repository の PR を、`fork` の経路以外で、または head repository が `EXPECTED_HEAD_REPO` と一致することを確かめずに取り込み済みとみなしている。create・managed の経路に前の fork 作業の `EXPECTED_HEAD_REPO` を残している
- ゲート B で `cleanup_expected_head_repo` を通さず、環境に残った `EXPECTED_HEAD_REPO` で cross-repository の PR を候補に出そうとしている
- fork→上流の PR のリモート branch を、PR の所属や取り込み先 base に合わせて `upstream` から列挙・削除しようとしている。削除元 remote は head repository に対応する `origin` である
- ゲート B で、`REMOTE` の fetch URL・push URL のうち最初の 1 件だけを確かめている、または create・managed で URL を確かめていない。fetch と push のすべての URL が期待する repository（fork は `EXPECTED_HEAD_REPO`、create・managed は `PR_REPO`）と一致しない remote は候補に出さない
- ゲート B の承認後の削除で `git -C "$CHECKOUT"` を付けず、cwd の repository の remote を操作しようとしている。push URL が fetch URL と異なる remote を検証していない
- PR 一覧の取得上限に達したのに、その中の 1 件を一意な対応とみなしている
- session の repository 名の大小文字差を別 repository とみなし、同じ PR の ref を削除しようとしている

**いずれかに該当したら、削除を中止して手順 1・4・5・6・9 のいずれか、または残存 pinned ref の一覧に戻る。**

## 言い訳と現実

| 言い訳 | 現実 |
|---|---|
| 「PR は Merge 済みだから、レビュー成果物の役目も終わった」 | マージされたのは追跡対象のコードだけである。git 管理外のレビュー結果は 1 バイトもマージされていない |
| 「ディレクトリ名が stale なので消してよい」 | 名前は中身を保証しない。照合していないなら未保存データの有無を知らないだけである |
| 「中を見たら軽微なメモだった」 | 軽微だと判断したのではなく、正本と照合していないだけである。照合は `diff -r` 1 回で済む |
| 「内容差分があっても固有ファイルが無ければ失うものはない」 | 同名の未保存稿は `Files ... differ` になる。`previous-review.md` だけをコピーして消すと新しい原稿が消える |
| 「worktree は clean だったのでデータ損失はない」 | `git status` は gitignore 対象ファイルも、worktree の外にある残骸も見ない。`git worktree remove` は worktree 内の gitignore 対象ファイルを確認せずに消す |
| 「`prunable` で実体が無いので、登録を消しても失うものは無い」 | `prunable` は登録パスに接続できないという情報である。本体を移動しただけでも出る。親ディレクトリが消えた登録も、所有する run が照合を待っていることがある。消した登録は repair で戻せない |
| 「HEAD が `origin/main` から到達可能で clean なので、detached な worktree を消しても失うものは無い」 | 追跡内容は失わなくても、別の run が使っている作業場所と登録を奪う。branch を持たない worktree の所有者は Git から分からない。例外は、helper の `sessions` が PR の終了を確かめた（`removable: true`）`/tmp/pr-review-*` だけである |
| 「一括 prune は危ないので、消してよい登録だけを `git worktree remove` で個別に消せばよい」 | 存在しないパスへの `remove` も、prune と同じく登録を消す。どの登録を消すかは所有者が照合して決める。片付けの手順では決めない |
| 「番号も branch も head も同じ PR がマージ済みなので、このレビューの session も終わっている」 | fork と上流は同じ checkout を使い、番号・branch・head が重なり得る。session に固定された所属リポジトリで PR の状態を確かめた `removable: true` だけが候補である |
| 「失敗セッションの担当は、年齢も PID も見えないので止まっているはず」 | 年齢・PID が無いことは停止の確認ではない。`reap-check` が `stop_confirmation_needed: true` で拒否したら保持し、停止を実際に確かめた人の理由がある場合だけ `--operator-confirmed-stopped` で実行する |
| 「消した後で問題があれば言ってもらえばいい」 | `rm -rf` に取り消しは無い。削除の前だけが確認である |
| 「マージ済み branch の削除は cleanup の一環」 | ローカルはそうである。リモートは他人が見る共有物であり、外向きの操作である |
| 「手早くと言われた」 | 照合は数秒で終わる。失ったレビューの再生成はそれより桁違いに高い |
| 「untracked が出るのは仕方ない。毎回訊けばよい」 | 訊かれるのは、判定不能な生成物を作り続けている上流の手順があるからである。生成側を直せば訊く必要そのものが無くなる |
| 「毎回同じ確認で面倒なので `.gitignore` に入れる」 | `git status` から消えるだけで、復元不能なファイルであることは変わらない。gitignore 対象は、再生成できるキャッシュを除き、本スキルのガードレールで照合なしの削除を禁じており、判定不能なまま残り続ける |

## ガードレール

- `git branch -D` でマージ判定を握り潰さない。使ってよいのは、手順 8 で「branch の取り込み判定」を `-d` の前と `-D` の直前に通し、`ancestor` または `pr` を再確認できた branch だけである。削除先は `CLEANUP_ROUTE` で決め、create-reso-world（`create`）では手順 7 で確認した `MAIN_ROOT`、fork（`fork`）では `TARGET_ROOT`（`$PARENT_ROOT/external/resoloop` と一致することを削除の前に確かめたもの）、通常ツール（`managed`）では `CLEANUP_ROOT` にする。`MAIN_ROOT` と `TARGET_ROOT` が別の checkout を指すとき、経路を決められないとき（`MAIN_ROOT` が無く `TARGET_ROOT` だけが残っているときを含む）は削除しない。cross-repository の PR は、`fork` の経路で head repository が `EXPECTED_HEAD_REPO` と一致するときだけ取り込み済みとみなす。ゲート B も `cleanup_expected_head_repo` で `EXPECTED_HEAD_REPO` を経路から決め、stale な値で cross-repository の PR を候補にしない。
- ゲート B の削除元 remote（`REMOTE`）は PR の head repository に対応させ、PR の照会先（`PR_REPO`）や取り込み先 base（`BASE_REF`）と混同しない。fork の経路では `REMOTE=origin` とする。fetch URL と push URL はすべて（`--all`）読み、末尾の `/` と `.git` を除いて `owner/name` に正規化し、期待する repository（fork は `EXPECTED_HEAD_REPO`、create・managed は `PR_REPO`）と比べる。1 件でも一致しない・解釈できない URL があれば、候補を出さずに停止する。削除と prune は `git -C "$CHECKOUT"` で検証済みの checkout に対して実行し、cwd の repository に依存させない。
- `git branch -d` の upstream 判定だけを削除の根拠にしない。削除の前に、選択した base と明示した PR の `headRefOid`・`mergeCommit` を同じ判定で確かめる。
- `git worktree remove` に `--force` を付けない。
- 対象を限定しない `git worktree prune` を実行しない。
- `prunable`・`locked` な worktree と、branch を checkout していない別 run の worktree（手順 5 の `/tmp/pr-review-*` を除く）を `git worktree remove` しない。
- ユーザー確認なしに `git push`（`--delete` を含む）や `scripts/resoloop-fork.sh sync` を実行しない。
- Open PR が残っている branch と worktree を削除しない。detached な pr-review worktree も含む。
- pr-review のセッションは helper の `cleanup --strict-reap` で退役させる。拒否されたセッションは、`run_context` の無い version 7 が終了コード 1 で拒否された場合を除き、worktree の削除と手順 6 に回さず保持する。version 8、`run_context` を持つセッション、終了コード 2 は保持する。
- 残存 pinned ref は、`refs/pr-review` の一覧から所属 repository と PR を確定し、PR が MERGED/CLOSED で、open PR と現行・保持中の session が使っていないことを確かめたものだけを `git update-ref --no-deref -d <ref> <読んだ値>` で削除する。一覧で読んだ値は保存し、削除の前に inventory を取り直さない。読取後に値が変わったら保持し、新しい値で再実行しない。symbolic ref は削除せず、参照先を消さない。所属が一意でない旧形式 ref は保持する。session の所属は型と形式を検証し、repository 名は大小文字を区別せず正規化して比較し、不正なら保持する。
- helper の `sessions` の成功を全 session の一覧とみなさない。登録の無い残骸・bundle・別の一時ルートを確認できず、非使用を確定できない ref は保持する。
- `--operator-confirmed-stopped` の理由を、エージェントが作らない。
- gitignore 対象のファイルは、再生成できるキャッシュを除き、正本と照合するかユーザーの確認を得るまで削除しない（`reviews/`、`docs_draft/`、`tmp/`、`external/` など。worktree ごと消す場合も同じ）。
- コンフリクト解消、rebase、リリース作業は行わない。

## 関連スキル

- `pr-review` — `/tmp/pr-review-*/` の使い捨て worktree と `review-backup/` を作る側。手順 6 の残骸はこのスキルの生成物である。手順 1 の `sessions` も同じ helper が提供する
