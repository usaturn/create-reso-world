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

通常ツールでは手順 7（親の更新）と 10（fork sync）を実行しない。常設 checkout の HEAD・ローカル base branch とそれを保持する worktree は変更せず残す。手順 8 の Git 操作先は `CLEANUP_ROOT`、取り込みの再確認先は `CLEANUP_BASE` とする。手順 9 の基準も `CLEANUP_BASE` とし、remote の base / HEAD を候補から除外する。リモート削除は従来どおり別の明示確認が必要。手順 11 は `git -C "$CLEANUP_ROOT"` で報告し、親が更新されたとは書かない。

### 通常ツールの削除候補の照合

手順 1 の対象外を除き、手順 2 の fetch 後、手順 3 で branch の候補を調べる際に実行する。直前の対象照合と同じシェルで、候補 worktree の絶対パス `CLEANUP_CANDIDATE` と対応する `PR_NUMBER` を設定する。これは候補の判定だけであり、成功後も所有・clean・ignored ファイルの手順 4 と、手順 5 の削除条件を省かない。

```bash
: "${CLEANUP_ROOT:?対象照合を先に実行する}" "${CLEANUP_CANDIDATE:?候補 worktree の絶対パス}" "${PR_NUMBER:?対応 PR}"
CANDIDATE_CONTEXT=$(managed_cleanup_context base-read "$CLEANUP_CANDIDATE") || exit 66
test "$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .common_dir)" = "$CLEANUP_COMMON_DIR" || exit 66
test "$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .registry_commit)" = "$(printf '%s' "$CLEANUP_CONTEXT" | jq -er .registry_commit)" || exit 66
CLEANUP_CANDIDATE=$(printf '%s' "$CANDIDATE_CONTEXT" | jq -er .checkout)
test "$CLEANUP_CANDIDATE" != "$CLEANUP_ROOT" || exit 66
CLEANUP_BRANCH=$(git -C "$CLEANUP_CANDIDATE" symbolic-ref --short HEAD) || exit 66
test "$CLEANUP_BRANCH" != "$CLEANUP_BASE_BRANCH" || exit 66
git -C "$CLEANUP_ROOT" merge-base --is-ancestor "refs/heads/$CLEANUP_BRANCH" "$CLEANUP_BASE" || exit 66
CLEANUP_PR=$(gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json state,headRefName,headRefOid) || exit 66
CLEANUP_HEAD=$(git -C "$CLEANUP_CANDIDATE" rev-parse HEAD) || exit 66
printf '%s' "$CLEANUP_PR" | jq -e --arg branch "$CLEANUP_BRANCH" --arg head "$CLEANUP_HEAD" \
  '.state == "MERGED" and .headRefName == $branch and .headRefOid == $head' >/dev/null || exit 66
```

拒否された候補は削除せず理由を報告する。共通 Git ディレクトリが違う・未マージ・PR 対応不明なら、親の worktree や同 origin の別 clone が clean でも残す。通常ツールの登録だけで pr-review の session や失敗 clone の staging の削除を許可しない。

### fork の経路（`external/resoloop`）だけの手順

fork の checkout は、`scripts/resoloop-fork.sh checkout <ref>` や `install <ref>` が取り出したコミットで detached HEAD になっていることが多く、利用者が作業ブランチにいることもある。`build` はこれを動かさない。この前提から、fork の経路は次の順で進める。

1. ユーザー確認を得てから（Claude Code では AskUserQuestion）、手順 10 の `sync` を先に実行し、fork の `main` を上流へ追従させる。手順 2 の `fetch --prune` の前でよい
2. マージ済みかの判定（手順 3）は、上流 `orange3134/resoloop` 発の PR は `upstream/main` を、fork 内（`usaturn/resoloop` 発）の PR は `origin/main` を基準にする。`sync` を先に済ませていないと、上流でマージ済みの PR がこの fork の `origin/main` ではまだ未取り込みに見える
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

それ以外の branch ごとに次を実行する。

```bash
git log --oneline origin/main..<branch>
```

- 出力が空: `origin/main` に取り込み済みである。`gh pr list --state all` の対応する要素が `"state": "MERGED"` であることも確認する。
- 出力がある: 未取り込みである。この branch と対応する worktree は削除しない。

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

この手順は、`worktree/` が無くなった残骸ディレクトリだけに適用する。手順 1・5 で残した worktree を含むディレクトリは消さない。helper が拒否したセッションと、`session.json` に `run_context` を持つセッションは、worktree が無くても対象にしない。worktree を外してからこの手順で消す迂回をしない。停止未確認の失敗セッションを、年齢や PID の不在を根拠に即時に消さない。

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

以下は `usaturn/create-reso-world` 用である。削除は、手順 7 で更新した `MAIN_ROOT` を対象にする。ツール呼び出しごとにシェルや環境変数が引き継がれない実行環境があるため、手順 7 と別の呼び出しでこのブロックを実行するときも、その呼び出しで `MAIN_ROOT` を設定する。fork の経路では、リポジトリのルートで `git -C external/resoloop branch -d <branch>` に読み替える。fork では手順 7 を省略し、削除のために HEAD を動かさない。`MAIN_ROOT` の設定も要求しない。

```bash
git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" branch -d <branch>
```

`-D` は使わない。例外は、後述の `merge-base` 再確認で取り込み済みと確かめた branch だけである。

`-d` が拒否した場合、理由で分岐する。拒否を未マージと同一視しない。

- `used by worktree` または `checked out`: 未マージではない。手順 7 が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、この branch は削除しない
- `not fully merged`: そのまま未マージと断定しない。`-d` の取り込み判定は upstream と実行先の HEAD を基準にするため、upstream の remote-tracking ref が削除・prune 済みのときや、実行先の HEAD がその branch の取り込み点より古いときは、マージ済みでも拒否される。fork の経路では削除のために HEAD を動かさないので、古い detached HEAD へのこの拒否は普通に起きる。手順 3 と同じ基準へ再確認する。create-reso-world では `git -C "${MAIN_ROOT:?メイン作業ツリーの絶対パスを事前に設定する}" merge-base --is-ancestor <branch> origin/main`、fork の経路では `git -C external/resoloop merge-base --is-ancestor <branch> <基準>`（上流 PR の基準は `upstream/main`、fork 内 PR は `origin/main`）を実行する。取り込み済みならその branch に限り `git -C <対象> branch -D <branch>` で削除してよい。明示的な取り込み確認を済ませた上での削除であり、マージ判定を握り潰すことには当たらない（`-D` も worktree に掴まれた branch は拒否する）。未取り込み、または再確認できない場合は削除せず、手順 3 の結果とともにユーザーへ報告する

detached HEAD では次の warning が出るが、**削除が成功していれば正常**である。upstream にマージ済みであることは確認できており、拒否ではない。

```
warning: deleting branch '<branch>' that has been merged to
         'refs/remotes/origin/<branch>', but not yet merged to HEAD
```

### 9. ゲート B: リモート branch の削除はユーザー確認を得る

手順 8 でローカル branch を消すと対象名が手元から消える。リモート側から独立に洗い出す。

```bash
git branch -r --merged origin/main | grep -E '^ *origin/' | grep -vE 'origin/(HEAD|main)$'
```

候補が複数ある場合は、手順 1 で取得した `gh pr list --state all` の `headRefName` と突き合わせ、**どの PR 由来か**を添えて提示する。対応する PR が見つからないリモート branch は候補から外し、そのまま残す。

マージ済みでも、リモート branch の削除を独断で実行しない。対象を提示してユーザー確認を求め（Claude Code では AskUserQuestion を使う）、承認を得てから実行する。

```bash
git push origin --delete <branch>
git fetch --prune
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

`usaturn/create-reso-world` では `MAIN_ROOT` の HEAD が detached で `origin/main` と一致することを報告する。既存ローカル `main` と、それを checkout している他 worktree は「変更せず保持」として報告する。削除した対象、保留した対象、その理由も報告する。

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
- helper が拒否した pr-review のセッションを、`git worktree remove` で worktree を外してから手順 6 で消そうとしている。`--operator-confirmed-stopped` の理由をエージェントが作ろうとしている

**いずれかに該当したら、削除を中止して手順 1・4・5・6・9 のいずれかに戻る。**

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

- `git branch -D` でマージ判定を握り潰さない。使ってよいのは、手順 8 の `merge-base` 再確認で取り込み済みと確かめた branch だけである。
- `git worktree remove` に `--force` を付けない。
- 対象を限定しない `git worktree prune` を実行しない。
- `prunable`・`locked` な worktree と、branch を checkout していない別 run の worktree（手順 5 の `/tmp/pr-review-*` を除く）を `git worktree remove` しない。
- ユーザー確認なしに `git push`（`--delete` を含む）や `scripts/resoloop-fork.sh sync` を実行しない。
- Open PR が残っている branch と worktree を削除しない。detached な pr-review worktree も含む。
- pr-review のセッションは helper の `cleanup --strict-reap` で退役させる。拒否されたセッション（`run_context` を持つものと version 8 を含む）は、worktree の削除と手順 6 に回さず保持する。
- `--operator-confirmed-stopped` の理由を、エージェントが作らない。
- gitignore 対象のファイルは、再生成できるキャッシュを除き、正本と照合するかユーザーの確認を得るまで削除しない（`reviews/`、`docs_draft/`、`tmp/`、`external/` など。worktree ごと消す場合も同じ）。
- コンフリクト解消、rebase、リリース作業は行わない。

## 関連スキル

- `pr-review` — `/tmp/pr-review-*/` の使い捨て worktree と `review-backup/` を作る側。手順 6 の残骸はこのスキルの生成物である。手順 1 の `sessions` も同じ helper が提供する
