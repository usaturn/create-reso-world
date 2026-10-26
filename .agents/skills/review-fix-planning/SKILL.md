---
name: review-fix-planning
description: PR とレビュー結果のディレクトリ（例 `reviews/ブランチ名/`、`docs/reviews/main/`、`reviews/#<PR番号>-<ブランチ>/` を指す `#番号`）を渡されて、修正要否の確定・指摘への対応・修正計画・指摘の取捨選択を求められたときに使う。「PR とレビュー結果を確認して修正要否を確定して」「レビュー指摘に対応して」「レビュー結果を確認して修正計画をたてて」「妥当な指摘だけ拾って直したい」「指摘のどれに対応するか決めたい」「複数モデルのレビューをまとめて」などの依頼が該当する。承認済みの review-fix 作業を実装する／対象ブランチへ反映させる依頼も該当する
allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *), Bash(rm *), Bash(test *), Bash(uv run *), Bash(bash .devcontainer/run-tests.bash*), Bash(bash scripts/check-layout.sh*), Bash(bash tests/scripts/*), Bash(bash scripts/superpowers-review-copy.sh*), Write(docs/superpowers/specs/**), Edit(docs/superpowers/specs/**), Write(tmp/agents/**), Edit(tmp/agents/**)
---

# レビュー指摘の選別と修正

複数モデルのレビュー結果から、**現行 HEAD でまだ生きている致命的な指摘だけ**を選び、修正要否を確定する。既定では、結論を三択のどれかにして完了まで進める（下記「依頼の種類と結論」）。

**中核原則: レビューは過去の HEAD に対する助言である。現行コードで再現しない指摘は指摘ではない。**

## 依頼の種類と結論

依頼の文言で流れを選ぶ。

| 依頼 | 流れ |
|---|---|
| 計画で止めることを明示した依頼（「計画だけ」「承認を待って」「実装しないで」「Spec を見せて」など） | **計画のみ**: 手順 1–7 で Spec を書き、承認を得て停止する。承認後は **実装後** |
| 承認済み Spec の実装・反映だけの依頼 | **実装後** の手順だけ |
| それ以外のすべて（「修正要否を確定して」「指摘に対応して」「修正計画をたてて」を含む） | **完遂**（既定）: 手順 1–6 のあと、下記「三択の結論」のどれかを完了させる |

完遂の依頼は、その PR の承認済み実装修正（approved PR review-fix implementation）と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う。一般的な外部実装・Issue 実装への許可には広げない。

完遂の結論は次の三択だけである。

1. **修正が必要** — 推奨案を基本に修正し、検証と自己レビューを経て既存 PR へ push する
2. **修正が不要** — 必要な確認・検証を完了し、最終の状況コメントを投稿してマージし、関連 Issue を更新する
3. **停止** — 権限・環境・外部障害で自力では続けられない場合だけ。未完了であることと具体的な停止理由を報告する

**未確認は結論ではない。** 確認不足・未読・未検証は途中の状態である。自分で確かめて解消する。「追加確認が必要」を結論にして終えない。確認作業をユーザへ返さない。未確認の指摘を「修正不要」として扱わない。三択の完了条件を満たしたときだけ完了を報告する。

判断の記録（review-records）の読み書きは [round-records.md](references/round-records.md)、agent-runner の担当による修正・自己レビュー・修正の確認と、修正不要の最終化は [execution.md](references/execution.md) に従う。これらの helper は手段であり、採否・結論・自己レビューの回数はこの文書の規則で決める。

## 第1引数の解決

第1引数は PR 番号（`300`・`#300`）、PR URL、または既存レビューディレクトリのパス。**読んだ skill の source checkout** を `REVIEW_TOOL_ROOT` とし、その版の `.agents/scripts/review_target.py review-dir` だけで、レビュー本文を読む前に対象 repository と保存先を照合する。対象 checkout や cwd から helper の配置元を推測しない。

```bash
TARGET_ARGS=(review-dir "$REVIEW_INPUT" --for-planning)
if [[ -n "${CODE_ROOT:-}" ]]; then TARGET_ARGS+=(--code-root "$CODE_ROOT"); fi
# PR の URL が別に渡された明示パス入力のときだけ追加する。番号・URL 入力には --pr を付けない。
if [[ -n "${REVIEW_PATH_PR:-}" ]]; then TARGET_ARGS+=(--pr "$REVIEW_PATH_PR"); fi
REVIEW_CONTEXT=$(uv run --project "$REVIEW_TOOL_ROOT" --locked python \
  "$REVIEW_TOOL_ROOT/.agents/scripts/review_target.py" "${TARGET_ARGS[@]}") || exit
REVIEW_DIR=$(printf '%s' "$REVIEW_CONTEXT" | jq -r .review_dir)
PARENT_ROOT=$(printf '%s' "$REVIEW_CONTEXT" | jq -r .parent_root)
PR_REPO=$(printf '%s' "$REVIEW_CONTEXT" | jq -r .repository)
PR_NUMBER=$(printf '%s' "$REVIEW_CONTEXT" | jq -r .number)
PR_URL=$(printf '%s' "$REVIEW_CONTEXT" | jq -r .url)
```

- 番号は親 origin の PR、URL はその base repository の PR。新配置 `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/` だけを探す。別 repo の同じ番号や外部 checkout の旧配置を自動選択しない。
- 旧配置（親の `reviews/#<PR>-*`、各 checkout の `reviews/`）は明示したパスでだけ使う。fork と上流の両 PR を含む旧配置では PR URL を `REVIEW_PATH_PR` に添える。移動・自動コピーはしない。
- その他の repo は明示された main checkout の絶対パス `CODE_ROOT` と一致 remote 1 件が必要。既知の ResoLoop 経路は origin/upstream を照合し、上流 PR は `base_remote=upstream`。checkout の探索・clone はしない。
- 候補無し・複数・repository/番号/branch の不一致・API 失敗は、その理由を報告して停止する。ディレクトリ名・祖先関係から別 PR を推測しない。

## 手順

依頼が承認済み Spec の実装完了／PR への反映のみで、新しい選別を求めていないなら、手順 1–7 を再実行しない。レビュー対象のブランチ／PR を `git` / `gh` で確認してから **実装後** の反映手順だけを実行する。

それ以外は、各項目をランタイムの plan / todo 機能のタスクにしてから開始する（Claude Code では TodoWrite、Codex では `update_plan`）。完遂では「三択の結論」の各段もタスクにする。

1. **範囲を固定する** — 解決したレビューディレクトリ配下の全ファイルを読む。各ファイル冒頭の「対象 HEAD」を記録する。複数世代が混在するのが普通である。レビュー成果物は gitignore 対象で未コミットのことがある（本リポジトリの `reviews/` がそうである）が、指定ディレクトリ内であれば Git の追跡状態にかかわらず正規の入力である。レビュアーのファイルは直下の `<model>.md` で、`findings/`（候補一覧）・`verified/`（確認済みの一覧・工程の記録）・`runs/`（実行記録）はレビュアーではない。続けて PR の判断の記録を読み、このサイクルの番号と前の判断を決める（[round-records.md](references/round-records.md) 1 章。読むのは書き込み権限のある投稿者と認証済み利用者自身の記録だけ）。記録を読めないときは判断を引き継げないので、完遂では結論 3、計画のみでは停止して報告する。
2. **現行 HEAD を特定する** — 引数解決で照合した `PR_REPO`・`PR_NUMBER`・`PR_URL`・`REVIEW_DIR` を使い、ルート `AGENTS.md` の「リポジトリ境界」と下記「共通 context の確認」を後続の Git 操作より前に実行する。保存先は `PARENT_ROOT/reviews/`、Git 操作先は context の `MAIN_ROOT`（code_root）であり、同じとは限らない。修正用の明示 worktree は同じ Git repository（git-common-dir）の場合に使える。その他の repo は明示された絶対パス `CODE_ROOT` と一致 remote 1 件が必要で、推測しない。ResoLoop の不備は `scripts/resoloop-fork.sh clone` を案内して停止する。PR の状態・draft・base・head・本文・関連 Issue を `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json state,isDraft,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner,body,closingIssuesReferences` で読み、引数解決の repository/番号と一致することを確認する。helper は照合した `PR_REMOTE`（base_remote、上流 PR は upstream）から PR head を固定する。下の共通 API を、読んだ skill の `REVIEW_TOOL_ROOT` の project で実行する:

   ```bash
   PR_REF=$(uv run --project "$REVIEW_TOOL_ROOT" --locked python - "$REVIEW_TOOL_ROOT" "$MAIN_ROOT" "$PR_REPO" "$PR_NUMBER" "$HEAD_SHA" "$PR_REMOTE" <<'PY'
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("review_target", Path(sys.argv[1]) / ".agents/scripts/review_target.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
print(helper.fetch_pull_head(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5], remote=sys.argv[6]))
PY
   ) || exit
   ```

   `HEAD_SHA` は直前の `headRefOid`。共有の追跡 ref・tag・`FETCH_HEAD` を更新せず、所属 repository を含む専用 ref に固定する。各レビューファイルの対象 HEAD がすべて `git -C "$MAIN_ROOT" merge-base --is-ancestor <対象 HEAD> "$PR_REF"` を満たすことを確かめる。満たさなければ停止する（完遂では結論 3）。祖先関係は既に照合した PR の世代確認にだけ使い、所属 repository を選ぶ根拠にしない。続けて、Review history の最後の HEAD が `HEAD_SHA` の先頭 12 桁と同じレビューファイル（判断の記録で `rerun` が `true` になるレビュアー）が 1 つ以上あることを確かめる。1 つも無ければ、判断の記録を `stopped` 以外にできないので停止し（完遂では結論 3）、「現行の HEAD でレビューを取り直す」を次の操作として報告する。完遂では続けて下記「専用の worktree」を用意する。

3. **各指摘を現行 HEAD の「コミット済み」内容で検証する** — `git show <HEAD>:<path>` で読む。指摘された path の `REVIEWED_HEAD` にある committed source/test blob は検証根拠として許可する。挙動の指摘は、path と reviewed HEAD を別引数にした隔離 worktree で再現する:

   ```bash
   REPRO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX")"
   WT="$REPRO_ROOT/worktree"
   git -C "${MAIN_ROOT:?}" worktree add --detach "$WT" "$REVIEWED_HEAD"
   test "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$MAIN_ROOT" rev-parse "$REVIEWED_HEAD^{commit}")"
   ```

   `WT` はメイン checkout 外の一意な一時 path とする。SHA が一致しなければその worktree を根拠に使わず停止する。再現しないものは「解消済み」に落とす。

   **検証対象の source/test を working tree のファイルから読まない。** 手元の作業ツリーには誰かの未コミット変更が入っていることがあり、「もう直っている」という誤判定を生む。実際にこの誤判定は起きている。これは検証根拠の制約であり、入力であるレビュー成果物の読み取りには適用しない。例外は下記「専用の worktree」で、未コミットの変更が無く HEAD が PR の head と一致している間に限り、その中のファイルを committed content として読んでよい。

   **確認済みの一覧:** `REVIEW_DIR/verified/<現行 HEAD の先頭 12 文字>.json` が、PR・現行 HEAD・今回再実行したレビュアーの入力と合っていればそれを読み、無い・不正・古いときは review-verify（mode cycle）で作る。一覧の判定（`confirmed`・`not_reproduced`・`unverified`）は根拠の 1 つで、上の規則（コミット済みの内容・隔離 worktree）での確認と、「分類の仕様」の判定を代えない。review-verify が一覧を作れないときは、理由を Spec に書いて自分で確認を続ける。結論 1 の自己レビュー（修正の確認）は一覧が無いと始められないので、そのときは結論 3 にする。

   **確認の範囲:** 結論にかかわらず、全指摘、PR の変更ファイルの全文、関連する処理（呼出元・同じ判定をする分岐）とテストを読む。一時的なコードで再現するときは上の隔離 worktree を使い、専用の worktree を汚さない。指摘ごとの検証・再現と関連箇所の調査は、互いに独立していれば使えるサブエージェントに任せ、使えなければ自分で行う。サブエージェントの監視は `monitoring-long-tasks` スキルに従う。確認中に PR が持ち込んだ致命的な欠陥を見つけたら、出どころを「自己確認」として指摘と同じように扱う。PR と関係しない既存の問題は直さず、致命的なものだけ報告に書く。

   **閉じ込め:** このセッションが検証のために作る一時ファイル（HEAD メモ、ログ、pytest 出力、スクラッチ）はすべて `$REPRO_ROOT` 配下に置く。`${TMPDIR:-/tmp}` 直下へ `review-fix-planning-*`、`review-fix-planning-*.txt`、ハイフン区切り名（`review-fix-planning-wt` / `review-fix-planning-head` / `review-fix-planning-repro-root`）を作らない。そのルートに置いてよいのは `mktemp` が返したディレクトリだけである。

   **teardown（手順 3 の終わり）:** `$WT` を使う検証がすべて終わったら、このセッションの worktree を外し、続けて親ディレクトリを消す。Spec 作成や承認待ちまで残さない。あとで再検証が必要なら新しい `mktemp` を作る。消したディレクトリは再利用しない。

   ```bash
   git -C "$MAIN_ROOT" worktree remove --force "$WT" && rm -rf -- "$REPRO_ROOT"
   ```

   `worktree remove` が失敗したら親を `rm -rf` しない（git の worktree 登録が欠けたパスを指す）。停止し、`$WT` と `$REPRO_ROOT` の完全パスを報告する。残りは `.devcontainer/cleanup-workspace.bash` に委ねる。`worktree remove` 無しで `rm -rf` だけを組み立てない。
4. **下記「分類の仕様」に従って全指摘を 3 区分に振り分ける。** 「対応する」項目ごとに、下記「守る条件と影響経路」の表を作り、下記「同じ条件の再発と設計の見直し」のきっかけに当たるかを確かめる。区分は判断の記録の `state` に写す（解消済み → `resolved`、対応する → `fix`、対応しない → `skip`。[round-records.md](references/round-records.md) 3 章）。前のサイクルの判断は、その文書の引き継ぎの規則に従う。
5. **修正方針を決める** — 計画のみでは `superpowers:brainstorming` を呼び、選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。きっかけに当たった項目があれば、そのきっかけと根拠を渡して architectural にさせる。完遂では brainstorming を呼ばない（人の承認を必須の段として持つため）。推奨案を自分で決め、設計の選択があれば他の案と選んだ理由を Spec に残す。ユーザに問わない。きっかけに当たった項目は、点の修正ではなく設計の見直しで直す。
6. **Spec を書く** — 経路に関わらず必ず書く（下記「Spec は経路に関わらず必須」）。書く前に、下記「Spec のコミットと確認用コピー」の 1. で `DOC_ROOT` を確定し、`$DOC_ROOT/docs/superpowers/specs/` に書く。完遂でも書く。コミットの時期は「Spec のコミットと確認用コピー」の完遂の項に従う。
7. **承認を得て停止する**（計画のみ）— 下記「Spec のコミットと確認用コピー」に従って Spec をコミットし、確認用コピーを作ってから提示する。ユーザが明示的に「進めて」と言うまで実装に入らない。実装せず止まる場合の **作業終了前の PR 投稿** は任意であり、commit / push まで完了したターンのみ必須である。実装が終わったら **実装後** に従う。完遂では停止せず、下記「三択の結論」へ進む。

## 共通 context の確認

`PARENT_ROOT` は create-reso-world の main checkout。省略できるのはその main checkout 内の cwd だけで、linked・外部 cwd では明示する。`DOC_ROOT` は文書のコミット先として別に指定し、`DOC_BRANCH` に予定の文書ブランチ名を入れる。初期調査で文書先が未確定なら両方とも空でよいが、**Spec の書込・commit 前には両方を確定して再実行する**。`CODE_ROOT` は既知経路では省略できるが、修正用 worktree は明示する。既知経路の別 clone は origin URL が同じでも拒否する。

以下を手順 2 と、文書書込・commit、実装、fetch・push、コメント投稿の直前に再実行し、失敗したら後続操作を行わない。API で PR の head リポジトリとブランチを確認した後の push 前には `HEAD_REPO` と `HEAD_BRANCH` を両方設定して再実行する。取得先の `base_remote` と push 先の `head_remote` を流用しない。`HEAD_REPO` が空の初期調査では head の両引数を CLI に渡さない（`HEAD_BRANCH` は PR の表示用メタデータとして保持できる）。helper 不在は配置元と不足パスを報告して停止し、`CODE_ROOT` 側へフォールバックしない。

```bash
CONTEXT_PARENT="${PARENT_ROOT:-}"
if [[ -z "$CONTEXT_PARENT" ]]; then
  CONTEXT_PARENT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    printf 'Set PARENT_ROOT to the create-reso-world main checkout; cwd is not a checkout\n' >&2
    exit 66
  }
fi
CONTEXT_HELPER="$CONTEXT_PARENT/scripts/superpowers_context.py"
if [[ ! -f "$CONTEXT_HELPER" ]]; then
  printf 'Missing context helper %s; set PARENT_ROOT to the create-reso-world main checkout containing scripts/superpowers_context.py\n' "$CONTEXT_HELPER" >&2
  exit 66
fi
CONTEXT_JSON=$(uv run --no-project python "$CONTEXT_HELPER" --operation review-fix \
  --parent-root "$CONTEXT_PARENT" --doc-root "${DOC_ROOT:-}" --code-root "${CODE_ROOT:-}" \
  --repo "$PR_REPO" --doc-branch "${DOC_BRANCH:-}" \
  --head-repo "${HEAD_REPO:-}" --head-branch "${HEAD_REPO:+${HEAD_BRANCH:-}}") || exit 66
PARENT_ROOT=$(printf '%s' "$CONTEXT_JSON" | jq -r .parent_root)
TOPLEVEL=$(printf '%s' "$CONTEXT_JSON" | jq -r .tool_root)
MAIN_ROOT=$(printf '%s' "$CONTEXT_JSON" | jq -r .code_root)
CODE_ROOT="$MAIN_ROOT"
DOC_ROOT=$(printf '%s' "$CONTEXT_JSON" | jq -r '.doc_root // empty')
PR_REMOTE=$(printf '%s' "$CONTEXT_JSON" | jq -r .base_remote)
HEAD_REMOTE=$(printf '%s' "$CONTEXT_JSON" | jq -r '.head_remote // empty')
```

書き込みの対象の PR・リポジトリ・checkout を変数で指定し、その変数が空だと別の対象を書き換える呼び出しは、変数を `${VAR:?}` で書く。`gh` は空の番号で cwd のブランチの PR を、空の `--repo` で cwd のリポジトリを、`git -C ""` は cwd の checkout を対象にするので、呼び出しを分けるときも `:?` を外さない。

## 専用の worktree

完遂では、自己レビューの役割（`run_roles.py`）の外で `pr-review` スキルを使わず、PR の head ブランチを checkout した専用の worktree で、修正・Spec のコミット（PR が create-reso-world のとき）・push を行う。計画のみと、実装後だけの依頼では作らない。

1. 手順 2 の共通 context（`HEAD_REPO` 無し）で得た `MAIN_ROOT`・`PR_REMOTE` と、手順 2 の `gh pr view` の結果を使う。`HEAD_BRANCH` は `headRefName`、`HEAD_SHA` は `headRefOid` である。
2. PR の head を取得して SHA を照合し、checkout 済みの worktree を調べる。fork からの PR でも `pull/<N>/head` で取れる。

   ```bash
   REPO_MAIN="${MAIN_ROOT:?}"
   FIX_WT="$PARENT_ROOT/.worktrees/$(printf '%s' "$PR_REPO" | tr / -)-pr${PR_NUMBER}-review-fix"
   git -C "$REPO_MAIN" fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"
   test "$(git -C "$REPO_MAIN" rev-parse FETCH_HEAD)" = "$HEAD_SHA" || {
     printf 'PR head differs from gh pr view headRefOid; re-read the PR before creating the worktree\n' >&2
     exit 66
   }
   git -C "${REPO_MAIN:?}" worktree list --porcelain
   ```

3. `branch refs/heads/$HEAD_BRANCH` を持つ worktree の有無で、次のどれかにする。
   - どこでも checkout されておらず、ローカルブランチも無い: `git -C "${REPO_MAIN:?}" worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"`
   - ローカルブランチはあるが checkout されていない: `git -C "$REPO_MAIN" merge-base --is-ancestor "$HEAD_BRANCH" "$HEAD_SHA"` が成功するときだけ、`git -C "${REPO_MAIN:?}" worktree add "$FIX_WT" "$HEAD_BRANCH"` の後に `git -C "${FIX_WT:?}" merge --ff-only "$HEAD_SHA"`
   - 別の worktree で checkout されている: その worktree の `git status --porcelain` が空で、HEAD が `$HEAD_SHA` なら、それを `FIX_WT` として使う（片付けの対象にしない）
   - それ以外（ローカルブランチが PR に無いコミットを持つ、未コミットの変更がある、`FIX_WT` のパスが既にある）は、触らずに結論 3 にする
4. `CODE_ROOT="$FIX_WT"` とし、`HEAD_REPO`（`headRepositoryOwner` と `headRepository` の owner/name）と `HEAD_BRANCH` を設定して共通 context を再実行する。返る `MAIN_ROOT` は `FIX_WT` であり、以後の commit・push はそこで行う。
5. **片付け:** 結論 1 の push 後、結論 2 のマージ後、結論 3 の停止時（未コミットの変更が無いとき）に、このセッションが作った worktree を `git -C "$REPO_MAIN" worktree remove "$FIX_WT"` で外す（`--force` を付けない。失敗したら残して報告する）。このセッションが手順 3 の `-b` で作ったローカルブランチは、先端が push またはマージした head の SHA か、作成時の head の SHA（結論 3 でコミットを残さなかったとき）と同じことを確かめてから `git -C "${REPO_MAIN:?}" branch -D "$HEAD_BRANCH"` で消す。残すと、PR の head が rebase された後の完遂が手順 3（PR に無いコミット）で止まる。

## 守る条件と影響経路

「対応する」項目ごとに、修正の前に次の表を作り、Spec に残す。同じ原因の隣の経路が次のレビューで見つかる手戻りを防ぐためである。

先に [要件・原因・検証の対応](references/convergence.md) の「2. 原因から影響経路を作る」「3. 検証と閉じ方」を読む。初回の修正から、次の形で既存の表を作る。単純な変更は短い表でよく、別帳票は増やさない。

1. 破れている条件（守るべき性質）と、「どの前提が、どの境界・操作順で破れたか」を 1 文ずつ書く
2. 同じ条件に頼っている経路を、PR の差分外も含めて列挙する。変更する関数・helper の全呼出元、同じ判定をする別の分岐、同じ前提を持つ別ファイル、変更前の挙動を保つ必要がある呼出元を含める。原因から入口・変換・読取／書込・副作用・終了／復旧へ追い、関数名の一覧で止めない
3. 経路ごとに「修正する」「既に満たす（根拠）」「対象外（理由）」を決める。「修正する」「既に満たす」の行には、観測する結果と確かめる方法（テスト・コマンド・再現手順）を付ける。計画時の実行証拠は「未実施」とし、実行後に対象版・結果・証拠を記す

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
|---|---|---|---|---|---|
| （1 文） | （ファイル・関数・分岐） | 修正する／既に満たす／対象外 | （比較する状態・出力） | （テスト・コマンド・再現手順） | 未実施／対象版と観測結果・ログ等。対象外は理由 |

列挙は、その条件に頼る経路を確かめる作業であり、原因の異なる新しい問題を探す作業ではない。「修正する」の行は、PR の差分外でも同じ PR で直す。

## 同じ条件の再発と設計の見直し

「対応する」項目ごとに、表を作るときに次のきっかけに当たるかを確かめる。当たった項目は点の修正で直さず、設計の見直しに切り替える（経路の引き上げ）。同じ仕組みへの修正が、回帰と適用漏れを繰り返すのを止めるためである。

**きっかけ**（どれか 1 つ）:

1. **同じ守る条件の 2 回目** — 破れている条件、または直す仕組み（関数・state の項目・判定）が、同じ PR の以前の回で致命的な指摘として直したものと同じである。前の回の表で漏れた隣の経路も含む
2. **修正が生んだ回帰** — 指摘の原因が、同じ PR の以前のレビュー修正のコミットが入れた変更である
3. **自己レビューでの再発** — 修正後の自己レビューで、この回に直した条件がまた破れている、またはこの回の修正が原因の致命的な指摘が出た

後続の指摘は [要件・原因・検証の対応](references/convergence.md) の「2. 原因から影響経路を作る」に従い、既存原因の適用漏れ／修正による回帰／別の原因／新しい要求に分ける。採否の3区分とは別軸であり、同系・別IDというだけで重複として捨てたり、すべて採用したりしない。

以前の回は、同じテーマの Spec の記録（以前の回の表・結論・コミット）と、PR のコミット履歴（`git log`）のうちレビュー指摘の修正として入ったコミットで確かめる。回帰は `git log -L`・`git blame`、またはそのコミットの前後での再現で確かめる。以前のレビュー修正が Spec にも PR の履歴にも無ければ、1・2 には当たらない。数えるのは「対応する」項目だけである。

**計画のみでは**、brainstorming に経路を判定させるときに、当たったきっかけと根拠を渡し、architectural にさせる。Spec には下の 1〜3 を書いて承認を求める。

**完遂では**、止まらずに（結論 3 にしない）、結論 1 の修正の中で次を行う。

1. **守る条件を文書にする** — Spec に「守る条件の設計」を書く。条件を、再現した 1 経路ではなく、その仕組みが扱うすべての状態・操作順・停止位置で成り立つ性質として書く。条件を保つ仕組みと、以前の回の修正（コミット）それぞれで足りなかった理由も書く
2. **影響経路を全面的に見直す** — 表を、今回の指摘の経路からではなく仕組みから作り直す。その state の項目を書くすべての箇所、その関数のすべての呼出元、すべての停止・失敗の位置を列挙する。表に「変更前の挙動」と「確かめる assertion（何を比べるか）」の列を足す
3. **直し方を選び直す** — 少なくとも「点の修正を続ける」「条件を 1 か所で保つ形にまとめる」「PR の保証を狭めて条件を不要にする」を比べて推奨案を選び、他の案と理由を Spec に残す。条件が構造で成り立つ案を優先する。点の修正を続けるなら、列挙したすべての経路で条件が成り立つ根拠を書く。保証を狭めたら、PR の説明の保証と既知の制限を直す。PR の分割は第二の PR になるので行わず、より良いと考えたら他の案として残す
4. **全経路で確かめる** — 検証を、再現した場面だけでなく、列挙したすべての経路で条件を確かめる形にする。失敗時の扱いなら下記「失敗時の検証」に従う
5. 結論 1 の残りの手順に戻る。自己レビューの反証の担当には、守る条件の設計も渡す

きっかけ 3 で切り替えたときも、自己レビューの 2 回目はしない。見直した内容を再レビューしていないことを Spec と状況コメントに書く。

## 失敗時の検証

「対応する」項目の守る条件が、失敗・拒否・中断したときの扱い（「不正な入力なら何も変えずに止まる」「途中で止まっても中途半端な状態が残らない」など）であるとき、その修正の検証を次の形にする。終了コード・メッセージ・対象の 1 ファイルだけを見る検証は、別の状態が先に変わる実装を見逃す。

1. **状態全体を比べる** — 失敗させる前と後で、その処理が管理する状態全体を比べる。対象のファイルに加え、共有先（symlink の参照先、hard link の相手）、バックアップ、認証、一時ファイル、キャッシュ、外部コマンドの呼出しを含める。ファイルは有無・バイト列・mode・リンクの種類と参照先を見る。期待値は失敗させる前の状態から取り、固定値を書かない
2. **副作用の順序を確かめる** — 入力の不正で止める処理は、どの状態を変えるよりも前に、すべての入力（構文・値・必要な内部構造・保存先の種類）を検査しているかを確かめる。書き込みの途中の I/O の失敗は入力の不正と分け、何が残り、どこまで戻すかを Spec に書いて確かめる
3. **負例には異常を 1 つだけ入れる** — 他の条件は正常にし、想定した理由で拒否されたことと、状態が変わっていないことを確かめる。異常を 2 つ入れた負例は別の拒否の理由で止まり、確かめたいガードが無くても通る
4. **ガードを外した対照で検出力を確かめる** — 修正の中心になるガードを 1 つだけ外した版で、そのガードを確かめるすべての負例が失敗することを確かめる。ガードを外すのは、手順 3 と同じ `mktemp` の方法で作った隔離 worktree に修正後の内容を写したものだけで、専用の worktree では外さない。終わったら手順 3 の teardown と同じ方法で消す。安全に関わる境界のガードに絞り、すべてのコードの変異テストは求めない

テストを足すのは、致命的な指摘の修正と検証に要るときだけである（「分類の仕様」）。create-reso-world の PR で足すテストは `AGENTS.md`「テストの採用基準」に従う。比べた状態と、対照で失敗した負例の数を Spec に書く。

## 三択の結論

完遂では、手順 1–6 の後に次のどれか 1 つを完了させる。結論 1・2 では、「対応しない」とした指摘のうち実在する制約（直さないが事実として起こるもの）が PR の説明の保証と食い違うなら、PR の説明の既知の制限に条件と回避方法を書き足す（`gh pr edit "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --body-file <file>`）。同じ論点が次のレビューで繰り返し挙がるのを防ぐためである。どの結論でも、PR が open で判断の記録を読めた場合は、記録付きで状況を投稿する（下記「作業終了前の PR 投稿」。記録の結果は結論 1 が `fixes_pushed`、結論 2 が `no_fix_needed`、結論 3 が `stopped`）。ただし下記「マージしてよい範囲」の外のリポジトリでは、commit / push まで行ったターンだけ投稿が必須である。

### 結論 1: 修正して push する

「対応する」が 1 件以上あるとき。

1. 推奨案を基本に、`run_roles.py --phase implement` で設定の担当に修正させる（[execution.md](references/execution.md) 1 章。雛形の既定は `claude-opus`、割り当てが `self` なら司令塔が直す）。外部の担当の commit は、停止の確認と差分の確認の後に専用の worktree へ取り込み、応答の成功を修正の合格とみなさない。「守る条件と影響経路」の表の「修正する」の行は、PR の差分外も同じ PR で直す。「同じ条件の再発と設計の見直し」のきっかけに当たった項目は、その節の手順で直す
2. **実装後** の手順 1–3（実装に関連したテストと、変更の種類に応じた検証）を通す。失敗時の扱いを直したなら「失敗時の検証」も行う。失敗したら直す。base でも同じように失敗する既存のテストは、base での結果を根拠として Spec に記録し、先へ進めてよい。続けて、自己レビューの前に **実装後** の手順 5 の検査だけを実行する（push しない）。`AGENTS.md` の「push の前の秘密情報の検査」の条件を満たす検出は、ここでその commit を直して手順 2 をやり直す（自己レビューの後は、自己レビューした commit とその祖先を直せない）。それ以外の検出と検査の失敗は結論 3 にする
3. 下記「修正後の自己レビュー」を 1 回だけ行う
4. 自己レビューで出た致命的な指摘を直し、手順 2 をやり直す。2 回目のレビューはしない。致命的でない指摘は「対応しない」として記録する。この回に直した条件の再発や、この回の修正が原因の指摘は、きっかけ 3 として設計の見直しで直す
5. Spec に結果を書いて `completed` にする
6. **公開の前に揃える** — 次がすべて済むまで、Spec のコミットと push をしない。途中の修正を先に push しない
   - 最後の修正の後に、手順 2 の検証が通っている。影響した経路の観測結果・対象版・実行証拠を経路表に更新し、影響しない証拠を引き継ぐなら理由を書く。方法の予定・テスト名・注意共有だけの行を完了にしない
   - [要件・原因・検証の対応](references/convergence.md) の「3. 検証と閉じ方」で、修正する・既に満たす各行の証拠、対象外の理由、判定の両側・操作順・検証の独立性を照合している。原因の未解消を finding 件数や自己レビュー上限の到達で閉じない
   - 自己レビューの全指摘に判定がある（直した、または「対応しない」と理由）。未確認の事項は、未確認として Spec と状況コメントに書く
   - Spec と PR の説明に書いた件数・参照先・保証が、実装と検証の結果に合っている
   - 公開済みのコミットを書き換えない（force push しない）
7. Spec をコミットし（「Spec のコミットと確認用コピー」の完遂の項）、**実装後** の手順 4–6 で既存 PR の head へ push し、状況コメントを投稿する（判断の記録は `fixes_pushed`、`commit` は push した SHA）。工程の記録を更新し（[round-records.md](references/round-records.md) 7 章）、その後「専用の worktree」を片付ける

### 結論 2: 修正不要としてマージする

「対応する」が 0 件で、全指摘・変更ファイルの全文・関連処理とテストの確認が終わったとき。CI の確認・マージ・closing Issue の更新は `finalize.py` が行う（[execution.md](references/execution.md) 3 章）。状況の投稿は、create-reso-world の PR では Spec の push の前に planner が行い、それ以外の PR では `finalize.py` が行う。

1. PR の変更の種類に応じた検証（**実装後** の手順 2）を、専用の worktree で通し、実際に実行したコマンドと終了コードを検証の記録に残す
2. `git -C "$MAIN_ROOT" fetch "$PR_REMOTE" <base>` で base を取り直し、その先端の SHA（`git -C "$MAIN_ROOT" rev-parse "$PR_REMOTE/<base>"`）を検証の記録の `base` にする（[execution.md](references/execution.md) 3.1 節）。先端が head の祖先でなければ（`git -C "$MAIN_ROOT" merge-base --is-ancestor <その SHA> "$HEAD_SHA"` が失敗する）、手順 3 と同じ `mktemp` の隔離 worktree で head にその SHA を merge した一時的なツリーを作り、同じ検証を通して、そのコマンドと終了コードを検証の記録にする。この merge は push しない。検証後は手順 3 の teardown と同じ方法で消す
3. base と競合して merge できないときは、競合の解消を修正として扱い、結論 1 に切り替える
4. 下記「マージしてよい範囲」を確かめる。範囲外なら、ここで結論 3 にする（`finalize.py` も、範囲外の PR は GitHub に問い合わせる前に止める）
5. 判断の記録（`no_fix_needed`）と、マージの前の採否・検証の状況を書いた本文を作る（[round-records.md](references/round-records.md)）。検証の状況には、検証したツリー（head だけか、head に `base` を merge したツリーか）と `base` の SHA を書く。マージ済み・Issue の更新済みと先に書かない。本文の Spec の行（文書のコミット SHA）は、手順 6 の commit の後に書き足す
6. Spec に結果を書いて `completed` にし、コミットする。PR が create-reso-world のものなら Spec は PR の head に載るので、次の順で進める。確認していないコミットをマージに含めないため、**実装後** の手順 5 の「reject されたら rebase または merge」はここでは使わない
   - commit の前に、`gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRefOid` が検証した `HEAD_SHA` と一致することを確かめる
   - commit の後、`git -C "$MAIN_ROOT" rev-parse HEAD` を Spec のコミット（`SPEC_COMMIT`）として記録し、`git -C "$MAIN_ROOT" rev-parse HEAD^` が `HEAD_SHA` と一致し、`git -C "$MAIN_ROOT" diff --name-only HEAD^ HEAD` が Spec の 1 ファイルだけであることを確かめる
   - 状況コメントの投稿の直前と push の直前に、手順 2 と同じく base を取り直し、先端が検証の記録の `base` と同じことを確かめる。違えば、投稿・push をせずに手順 2〜5 を新しい先端でやり直し、Spec を直して、Spec のファイルだけを `git -C "${MAIN_ROOT:?}" add -- <Spec>` してから、`git -C "${MAIN_ROOT:?}" commit --amend --no-edit` で Spec のコミットを作り直す（push していないので書き換えてよい）。作り直したら、上の commit の後の確認からやり直す。手順 3 で結論 1 に切り替えるときは、Spec のコミットを結論 3 の「書き始めた Spec の扱い」の「push していない」の項の方法で取り消してから進める
   - PR の head がまだ `HEAD_SHA` のうちに、状況コメントを記録付きで投稿する（「作業終了前の PR 投稿」。記録付きの投稿は、PR の head が記録の `reviewed_head` と同じときだけ通る）
   - **実装後** の手順 5 の head の確認と共通 context の再実行の後、同じ手順 5 の検査付きの push で push する（fast-forward だけ。`--force` を付けない。検査で止まったら push せずに結論 3 にする。状況コメントは投稿済みなので、`AGENTS.md` の直し方は使わない）
   - 一致しない、または push が reject されたら、rebase も merge もせず結論 3 にする（停止理由: 検証中に PR の head か作業ツリーが変わった）。Spec のコミットは下記「結論 3」の「書き始めた Spec の扱い」に従う（取り消してよい条件を満たさなければ、取り消さずに残して報告する）

   PR が create-reso-world 以外のものなら、Spec は文書用ブランチにコミットし（「Spec のコミットと確認用コピー」）、状況の投稿は次の `finalize.py` が行う
7. 共通 context を再実行してから、`finalize.py` で最終化する。create-reso-world の PR では `--spec-commit "$SPEC_COMMIT"` を付ける（helper は投稿せず、投稿済みの記録、Spec の commit が検証した HEAD の上の Spec 1 ファイルだけであること、PR の head を確かめてから、その commit をマージする）。それ以外の PR では付けない（helper が投稿し、CI を確かめ、検証した head をマージする）。どちらでも helper は、投稿の前（`--spec-commit` が無いとき）とマージの直前に、PR の base ブランチの今の先端が検証の記録の `base` と同じことを確かめる。終了コード 0 で結果の `outcome` が `no_fix_needed` のときだけ、マージと closing Issue の更新が終わった。`wait_for` 付きの `stopped` は、`monitoring-long-tasks` で期限を決めて待ち、同じ入力で再実行する。`base_moved` 付きの `stopped`（検証した後に base が進んだ）は待っても解消しないので、[execution.md](references/execution.md) 3.4 節のとおり新しい先端で検証し直し、検証の記録を作り直してから再実行する。`merge_parent` 付きの `stopped`（マージの後に、merge commit の最初の親が検証の記録の `base` と違う・読めない）はマージ済みで、helper は関連 Issue を更新していない。どちらの場合も、[execution.md](references/execution.md) 3.4 節のとおり補足のコメントを投稿して結論 3 にする。読めないだけなら、原因が解消してから同じ入力で再実行すると読み直す。最初の親が違えば、待っても再実行しても解消しないので、再検証せずに止まる（merge commit のツリーでの再検証と再実行は、利用者の指示で別に行う）。PR の変更が原因の CI の失敗は致命的な指摘として結論 1 に切り替える。それ以外の `stopped` は結論 3 にする（`merged: true` ならマージ済み、`merged: null` ならマージ済みかを確かめられていないことを分けて報告する。`null` を未マージと書かず、[execution.md](references/execution.md) 3.4 節のとおり状態を読み直す）。結果に `error_detail`（`gh` の失敗の要点）があれば利用者への報告に書き、PR のコメント（判断の記録・状況の本文）には写さない（[execution.md](references/execution.md) 3.4 節）
8. PR の本文・タイトルで参照しているだけの Issue に、マージの結果と残りの作業をコメントする。本文のチェック項目のうち、この PR で完了したことが明らかなものは、本文を取り直してから `[x]` にする（`finalize.py` は closing Issue だけを扱う）
9. 工程の記録を更新し（[round-records.md](references/round-records.md) 7 章）、「専用の worktree」を片付ける

**base が進んだときのやり直し:** 手順 6 の再確認と手順 7 の `base_moved` によるやり直しは、このサイクルで合わせて 3 回まで。超えたら結論 3 にする（停止理由は `external: 検証の間に base が進み続けた`）。検証し直さずに、検証の記録の `base` だけを新しい先端に書き換えない。`finalize.py` が最後に base を確かめてから GitHub がマージを処理するまでの間の前進は止められない。helper はマージの後に merge commit の最初の親で見つけて止まる（[execution.md](references/execution.md) 3.4 節の `merge_parent`、3.5 節）。この停止はやり直しの回数に数えない。

**マージしてよい範囲:** `usaturn/create-reso-world` と `usaturn/resoloop` の、open で draft でない PR だけ。それ以外（上流の `orange3134/resoloop` など）は、修正不要と判定してもマージせず結論 3 にする。範囲外のリポジトリへのコメント投稿は、commit / push まで行ったターンだけ必須である。

### 結論 3: 停止する

次の場合だけ。未完了であること、具体的な停止理由、済んだ作業（コミット・push・投稿の有無）を報告する。PR が open で判断の記録を読めた場合は、`stopped` の記録（`stop_reason` は `permission:`・`environment:`・`external:` に続けて具体的な障害）を付けて状況を投稿する（マージしてよい範囲の外のリポジトリでは、commit / push まで行ったターンだけ必須）。

- 権限: マージしてよい範囲外、push・マージの権限が無い、`gh` の認証が無い
- PR の状態: draft、close 済み、マージ済み
- 環境: 共通 context の確認が止まった（exit 64〜66）、レビューと PR の対応を確かめられない（手順 2。`external/resoloop/reviews/` で PR の URL が無いときを含む）、現行の PR head を再実行したレビュアーがいない（手順 2）、判断の記録を読めない（壊れた記録）、検証中に PR の head が更新された（結論 2 の手順 6）、head ブランチが PR に無いコミットや未コミットの変更を抱えている、runner の起動の前の checkout の監査で止まった、確認済みの一覧が無く自己レビューを始められない、予約した自己レビューを終えられなかった、必要なツールが無い
- 外部障害: GitHub の API・ネットワークの障害（判断の記録・認証済みの login を取得できないときを含む）、CI 基盤の障害、検証の間に base が進み続けた（結論 2 のやり直しの上限）

未読・未検証、判断に迷う、修正が大きい、テストが失敗する（直す）、再現できない（根拠を付けて「解消済み」か「対応しない」にする）、同じ条件の再発（「同じ条件の再発と設計の見直し」で直す）は、結論 3 の理由にならない。

**書き始めた Spec の扱い:** 結論 3 では、Spec だけのコミットや Spec の変更を PR の head ブランチに残さない。残すと、次の完遂が「専用の worktree」の手順 3（PR に無いコミット、未コミットの変更）で止まり続ける。再利用した他の worktree では、持ち主の commit・push で draft の Spec が PR に入る。ただし、自分の Spec の変更だと取り消す直前に確かめられないものは取り消さない（worktree の持ち主や別のセッションの作業かもしれない）。報告に使う `git` の結果は、「専用の worktree」の片付けより前に集める。

- PR が create-reso-world 以外（`DOC_ROOT` は文書用ブランチ）: Spec を `draft` のまま文書用ブランチにコミットし、停止理由を書く
- create-reso-world の PR で、変更が Spec だけではない（head ブランチに Spec だけではないコミットがあるか、Spec 以外の未コミットの変更がある。このセッションの修正か他の作業かを問わない）、または下の取り消してよい条件を満たさない: 何も取り消さずに残す。報告に、ブランチ名（未コミットの変更があれば worktree のパスも）と、`git -C "$MAIN_ROOT" status --short`・`git -C "$MAIN_ROOT" log --oneline "$HEAD_SHA"..HEAD` の結果を書き、それを push するか捨てるまで次の完遂は「専用の worktree」の手順 3 で止まることを書く
- create-reso-world の PR で、変更が Spec だけ: 分類の結果と停止理由を報告に書き、次の条件を満たすときだけ取り消す
  - 結論 2 の手順 6 で Spec を push した後（マージなどで止まった）: 取り消すものは無い。先端は push した head で、片付けの対象になる
  - 結論 2 の手順 6 で Spec をコミットし、push していない: 手順 6 の commit 後の確認が通っていて、取り消す直前にも `git -C "$MAIN_ROOT" rev-parse HEAD` が記録した Spec のコミット、`git -C "$MAIN_ROOT" rev-parse HEAD^` が `HEAD_SHA`、`git -C "$MAIN_ROOT" status --porcelain` が空のときだけ、`git -C "${MAIN_ROOT:?}" reset --keep "$HEAD_SHA"` で取り消す
  - コミットしていない: `git -C "$MAIN_ROOT" rev-parse HEAD` が `HEAD_SHA` で、`git -C "$MAIN_ROOT" status --porcelain` に Spec のファイルしか出ないときだけ取り消す。追跡済みか `git add` 済みなら `git -C "${MAIN_ROOT:?}" restore --staged --worktree -- <Spec>` で戻し、追跡されていない新規のファイルは消す
  - 取り消した後、`git -C "$MAIN_ROOT" rev-parse HEAD` が `HEAD_SHA` で `git -C "$MAIN_ROOT" status --porcelain` が空であることを確かめる。そうなれば head ブランチは「専用の worktree」の片付けの対象になる。そうならなければ、上の「残す」と同じく報告する

### 修正後の自己レビュー

結論 1 の修正後に最大 1 回だけ行う。1 回は `run_roles.py --phase self-review` の 1 回の呼び出しである（[execution.md](references/execution.md) 2 章）。runner が self-review と fix-check の 2 つの役割を同時に動かし、起動の前に工程の記録に枠を 1 つ予約する。予約の後は失敗・中断でも枠は戻らず、2 回目の呼び出しは `run_roles.py` が拒否する。自己レビューのために、この呼び出しの外で `pr-review` スキルを起動しない。

- self-review の役割: pr-review の非対話の入口で、ローカルで commit した修正後の HEAD（`--review-commit`）の PR 全体を再レビューする。下の観点 2 を受け持つ
- fix-check の役割: review-verify の `fix_check` で、修正の主張・変更ファイル・関連する経路とテストを確かめる。`fix_sections` に「対応する」項目の修正方針・守る条件と影響経路の表・実行した検証を全文で渡し、依頼に観点 1 と観点 3 を書く
- 割り当てが `self` の役割は司令塔が実行する。使えるサブエージェントに 2 つの依頼を同時に任せてもよく、どちらも 1 回と数える
- self-review・fix-check に codex の担当は割り当てられない（`run_roles.py` が予約の前に止める）

1. **反証** — 「守る条件と影響経路」の表を渡し、修正した条件が破れる入力・操作順・経路と、旧版との挙動の差を探す。拒否側と正常側、影響する前後操作・復旧、fixture／fake／期待値が実装と共有する誤前提、経路を閉じる証拠の不足を確認する
2. **PR 全体** — 修正後の PR の全差分と変更ファイルの全文を読み、致命的な問題を探す
3. **検証の検出力** — 追加・変更したテストと検証が、修正対象の欠陥を実際に検出できるか（assertion が変更対象全体を見ているか、別の拒否理由に隠れていないか）。失敗時の扱いを直したなら「失敗時の検証」の 4 点で見る

レビュー担当には、守る条件・影響経路・実行した検証・未確認の事項を渡し、指摘に再現手順か根拠（ファイルと行）を付けさせる。指摘は「分類の仕様」で判定する。指摘 0 件を、未確認の事項が解消した証拠として扱わない。自己レビュー後の修正は再レビューしない。そのことを Spec と状況コメントに書く。

## Spec の正本を選んでから更新する

新しい Spec を書く前に、対象リポジトリ、Issue/PR 番号、テーマ、正本のパス（`docs/superpowers/specs/`・`plans/` 配下の実際のファイル）で現行の Spec/Plan を探す。ファイル名の basename や日付だけでは照合しない。

- 現行の正本が 1 件なら、それを更新する。過去の版は Git の履歴に残る。同じテーマの通常のレビュー修正では、回ごとの新規文書（roundN）を既定で作らない
- 候補が複数あって、文書の後継指定か明示パスで 1 件に確定できないときは、更新せず停止してユーザに確認する
- 本当に新しい Spec を作るのは、独立した承認を受けたアーキテクチャ再設計など、明示的な理由があるときだけである。その理由は新しい文書の冒頭に記録する
- 提示する Spec/Plan は、`draft` のままコミット済みであること（「Spec のコミットと確認用コピー」の手順 1）

## Spec のコミットと確認用コピー

Spec の正本は create-reso-world の `DOC_ROOT`（ルート `AGENTS.md` の定義）にだけ置く。`MAIN_ROOT` が別のリポジトリでも、そちらへ置かない。`DOC_ROOT` は `$TOPLEVEL` と同じとは限らない。`$TOPLEVEL` は、スキル helper と `scripts/superpowers-review-copy.sh` の配置元としてだけ使う。

1. **`DOC_ROOT` を確定してコミットする** — Spec を書く前に、コミット先のブランチの checkout を `DOC_ROOT` として確定する。コミット先は、`PR_REPO` が `usaturn/create-reso-world` ならレビュー対象ブランチ（実装を載せるブランチ）、それ以外なら create-reso-world の文書用ブランチ（テーマごとに 1 本。例 `docs/usaturn-resoloop-pr9-list-shrink`）である。既存の文書用ブランチがあれば再利用し、レビュー回ごとに作らない。`DOC_ROOT` を特定できない場合は推測せず停止する。Spec の作成・更新は `$DOC_ROOT` で行い、提示の前に `draft` のまま `$DOC_ROOT` でコミットする。
2. **確認用コピーを作る** — `PARENT_ROOT`（ユーザが読む create-reso-world の親 checkout）を確かめてから、次を `$TOPLEVEL` で実行する。名前は `<repo>-pr<N>-<topic>-spec.md` の形にする。既存のコピーは決して差し替えない。同じ名前での再コピーは、内容が同一なら `unchanged`、異なれば別名を案内して拒否される。正本が変わったら `...-r2-spec.md` のような別名で新しいコピーを公開する。旧コピーとユーザの注記は残る。スクリプトが拒否したら、worktree のパスだけを代わりに示さず、失敗を報告して止まる。

   ```bash
   bash scripts/superpowers-review-copy.sh --doc-root "$DOC_ROOT" --parent-root "$PARENT_ROOT" \
     --path docs/superpowers/specs/<file> --name <repo>-pr<N>-<topic>-spec.md
   ```

3. **提示する** — コピー先（`tmp/superpowers-review/...`）、文書コミットの SHA、正本のパスを示して承認を求める。承認はその SHA の版に結び付ける。
4. **公開する** — `PR_REPO` が create-reso-world なら、Spec は実装と同じ PR に載る。それ以外では、**実装後** の push の後で、同じテーマの文書専用 PR があれば文書用ブランチを push してそこへ反映する。文書専用 PR はコード修正の第二の PR ではない。文書専用 PR が無ければ push も PR の作成もせず、文書のコミット SHA を報告し、「公開未実施」と書いて作成の指示を求める。

**完遂では** 手順 2・3（確認用コピーと提示）を省き、承認を待たない。Spec は 1 回だけコミットする。結論 1 では自己レビュー後の修正と検証が終わってから push の前に、結論 2 ではマージの前に、結論・検証の結果・自己レビューの結果を書いて状態を `completed` にする。push・マージ・Issue 更新の結果は Spec に追記せず、状況コメントと完了報告に書く（記録だけのコミットを PR に足さないため）。結論 3 で止まったときは、「三択の結論」の結論 3 の「書き始めた Spec の扱い」に従う（create-reso-world の PR で修正が無ければ、Spec を head ブランチにコミットしない）。PR が create-reso-world のものなら、手順 1 の `DOC_ROOT` は専用の worktree である。手順 4 の公開の規則は変わらない。

## 実装後

明示・検証済み `CODE_ROOT` を使う任意リポジトリの、その PR の承認済み実装修正（approved PR review-fix implementation）は既存の対応経路として維持する。一般的な外部実装・Issue 実装と remote なしの PR 連携へ許可を広げない。実装前に承認済み版・現行版と具体的な実行許可を確認し、実質変更にその許可が及ばなければ再承認を求める。

この節は、計画のみの流れでユーザが Spec を明示承認し、対応する項目を実装し終えたあとに実行する。計画は手順 7 で止まる。完遂では「三択の結論」の結論 1・2 がこの節の手順を参照する。後続の依頼が、その承認済み実装を PR に反映するだけの場合もこの節を実行する。実装に入ったら、下記の手順の各段をタスクにする。

**PR への反映 — この順で行う:**

1. **実装に関連したテスト** を走らせる。Spec の各「対応する」項目に書いた検証方法、変更ファイルをカバーするテスト、今回の Fix で追加したテスト。
2. **変更の種類に応じた検証** を続けて通す。
   - 環境の変更（ルートの `.devcontainer/`・`scripts/`・`tests/`・`templates/`・`.agents/`・設定ファイルなど）: `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`。スキル（`.agents/skills/`・`tests/skills/`）を変えた場合は `uv run pytest tests/skills .agents/skills` も
   - ワールドのプロジェクトの変更: そのプロジェクトのディレクトリで `uv run pytest`
   - resoloop fork（`external/resoloop`）の変更: 変更したプロジェクトに関連する `dotnet test`
3. 失敗したら直す。commit しない。
4. commit・push の前に [要件・原因・検証の対応](references/convergence.md) の「3. 検証と閉じ方」を読み、経路表の観測結果・対象版・実行証拠、判定の両側・操作順・独立した根拠を照合する。最後の修正で影響した経路の証拠が不足していれば、必要な修正・検証と表の更新を終えるまで公開しない。承認済み Spec の反映だけの依頼でもこの照合は行うが、採否の選別や自己レビューをやり直す手順は追加しない。共通 context を再実行し、`git -C "$MAIN_ROOT" fetch "$PR_REMOTE"` で取得する。取得後に `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRefOid` でレビュー対象 PR の実際の先端も再確認する。手順 1・2 が通ったら、レビュー対象ブランチ（既存 PR の head）へ commit する。`main` ではない。新しい `*-review-fixes` ブランチでもない。
5. そのブランチを **既存 PR** へ push する。ルート `AGENTS.md` の「push の前の秘密情報の検査」に従い、検査した SHA を push する（`<base>` は PR の `baseRefName`）。検出や検査の失敗で止まったら push しない。`AGENTS.md` の「push の前の秘密情報の検査」の条件を満たす検出なら（完遂の結論 1 では、自己レビューした commit とその祖先は条件を満たさない）、その commit を直して手順 1 からやり直す。それ以外は停止して報告する（完遂では結論 3）:

   ```bash
   SHA="$(bash "$TOPLEVEL/scripts/scan-before-push.sh" -C "${MAIN_ROOT:?}" --base "$PR_REMOTE/<base>")" && [ -n "$SHA" ] \
     && git -C "${MAIN_ROOT:?}" push "$HEAD_REMOTE" "${SHA:?}:refs/heads/$HEAD_BRANCH"
   ```

   push の成功を確認する。reject されたら rebase または merge し、手順 1・2 を再走してから再度 push する。新しい PR を開かない。`finishing-a-development-branch` のメニューを出さない。対象リポジトリにかかわらず、すべての push の前に `gh pr view "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --json headRepository,headRepositoryOwner,headRefName` で PR の head リポジトリとブランチを確かめ、その確認結果を `HEAD_REPO`・`HEAD_BRANCH` に設定して共通 context を再実行し、返された `HEAD_REMOTE` へ push する。fork からの PR では base と head が別のリポジトリである。該当する remote が 1 つに決まらなければ推測せず停止する。
6. 完了報告の前に **作業終了前の PR 投稿** を実行する。

レビュー対象ブランチに open な PR が無いなら、作らず停止して報告する。ユーザが作れと言うまで作らない。コメントの投稿もしない。

**この節が commit / push の常設指示である。** 二度目の「commit」「push」を待たない。「進めて」は実装の承認であり、この手順が PR への反映である。

**commit / push の条件にしないもの:** 上の検証に含まれない一括検証（変更と関係の無いワールドのプロジェクトの `uv run pytest`、`scripts/resoloop-fork.sh test` による fork の全テストなど。既存 PR の CI がまだ走る）、`superpowers:verification-before-completion` のフルスイート、`superpowers:finishing-a-development-branch`。

例: レビュー対象 PR は `usaturn/create-reso-world` の #12 で、Spec の検証が `bash tests/scripts/test-check-layout.bash` —— `scripts/check-layout.sh` を直す環境の変更なので、`MAIN_ROOT` は toplevel。そのテストに続けて `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通す。`fix/check-layout-mounts` に commit し、手順 5 の API 確認と共通 context の再実行で得た `HEAD_REMOTE` を使い、手順 5 の検査付きの push（`--base "$PR_REMOTE/main"`）で既存 PR へ反映する。status comment の `PR_REPO` は `usaturn/create-reso-world`。変更と関係の無いプロジェクトの `uv run pytest` は走らせない。`fix/check-layout-mounts-review-fixes` は開かない。push 後、同じ PR にレビュー状況・作業判断・作業結果のコメントを作成または更新する。

resoloop の上流への PR も同じ規則が fork の経路で成立する: `PR_REPO=orange3134/resoloop`、`MAIN_ROOT` は `$TOPLEVEL/external/resoloop` で、取得は共通 context が返す `PR_REMOTE`（通常は `upstream`）を使い、PR の head branch は fork にあることを手順 5 の API と共通 context で確認する。その結果の `HEAD_REMOTE`（通常は `origin`）を使い、手順 5 の検査付きの push（`--base "$PR_REMOTE/main"`）で反映する。base（上流の `main`）に `.gitleaks.toml` が無いので、Gitleaks の既定の規則で検査される。検証は変更したプロジェクトに関連する `dotnet test` までで、`scripts/resoloop-fork.sh test` による全テストは反映の条件にしない。

## 作業終了前の PR 投稿

この節の目的は後続エージェント・レビュアーへの永続的な記録に限る。完了通知待ちの停止（stall）対策ではない。stall は監視側（Monitor / PID）の課題である。

コメントは単体で読めること。PR だけを読む読み手が Spec 無しで判断を理解できるように書く。

**commit / push まで完了したターン、完遂の結論 2（マージの前）、完遂の結論 3（PR が open で判断の記録を読めた場合。マージしてよい範囲の外のリポジトリでは、commit / push まで行ったターンだけ）では必須である。** commit / push まで実装したターンは push 後に1回投稿する。承認待ちで止まるだけのターンの投稿は任意である。同じサイクルの自分のコメントがあれば更新し、無ければ新規作成する。他エージェントのコメント・前のサイクルのコメントは読んでよいが編集しない。

**判断の記録:** 状況コメントには判断の記録（review-records v2）を付ける。記録を `$ROUND_JSON` に書いて検査し（[round-records.md](references/round-records.md) 2〜5 章）、下のブロックの helper に `--records-file` で渡す。`ROUND` はこのサイクルの番号（同じ文書の 1 章）である。記録の結果は、結論 1 が `fixes_pushed`、結論 2 が `no_fix_needed`、結論 3 が `stopped`。計画のみで承認を待つターンに投稿するときは `stopped`（`permission: 計画のみの依頼のため、実装の承認を待つ`）にし、承認・push の後に同じサイクルのコメントを `fixes_pushed` に更新する。helper は認証済みの login を自分で取り、書き込み権限のある投稿者か認証済み利用者自身のコメントだけと照合し、PR の head（`fixes_pushed` は `commit`、それ以外は `reviewed_head`）や前のサイクルの記録と合わない記録を投稿しない。拒否されたら記録の問題を直して投稿し直すか、止まって報告し、記録なしの投稿や手書きの `gh` の呼び出しに切り替えない。

レビュー対象ブランチに open な PR が無い場合は投稿しない。PR を作ることもしない。チャットで報告して止まる。

**リポジトリ:** レビュー対象 PR を持つ `owner/name` を `PR_REPO` にする。ヘルパーは作業ディレクトリから推測しないため、PR 番号だけで別リポジトリへ投稿されることはない。

**モデル識別子:** ランタイムが提示する正確な識別子を `MODEL_NAME` にする。ファイル名や系列名から推測しない。取得できなければ投稿せず確認する。

**コメントは日本語で書く。** 次の3見出しだけをこの順で使う。Spec 全文は貼らない。早期停止では分かる範囲を書き、未実施の節は `未実施` とする。PR への反映のみの依頼でも、承認済み Spec の要旨をレビュー状況と作業判断にまとめる。再検証はしない。

```markdown
## review-fix-planning（<MODEL_NAME>）

対象 PR: #<N>（`<branch>`） / サイクル: <round> / 現行 HEAD: `<sha>`

### レビュー状況
- 入力: `<review-dir>`（読んだファイルと各対象 HEAD）
- レビュアーの構成: レビューファイル・モデル・ランタイム・レビュー HEAD・このサイクルで再実行したか・Merge recommendation の表。入力から外したファイルと理由
- 前のサイクルの判断: 件数（引き継いだもの・見直したもの）
- 分類: 解消済み N / 対応する N / 対応しない N

### 作業判断
- 対応する: 各 ID と、致命的である理由・確認方法を 1 行
- 対応しない: 全件を ID と一行理由で記載する（件数要約のみにしない）
- 解消済み: 件数と代表根拠
- 設計の見直し: なし | 項目の ID、きっかけ（同じ守る条件の 2 回目／修正が生んだ回帰／自己レビューでの再発）、選んだ直し方

### 作業結果
- 結論: 1 修正して push | 2 修正不要でマージ | 3 停止（理由） | 計画のみ（承認待ち）
- 自己レビュー: `run_roles.py` の 1 回の担当（self-review・fix-check）と観点ごとの結果（自己レビュー後の修正は再レビューしていない） | 未実施
- このターン: 計画のみ | push 済み | マージ前の最終報告 | 途中停止
- Spec: `<path>` @ `<文書コミット SHA>`（create-reso-world。PR に載っていればその URL。push していなければローカルにしか無い（公開未実施））または未作成
- commit / push: `<sha>` またはしていない
- 次: 承認待ち | マージ | 完了 | 停止理由
```

```bash
# コメント投稿の直前にも、宣言済みの親から共通 context を再照合する
CONTEXT_HELPER="${PARENT_ROOT:-}/scripts/superpowers_context.py"
if [[ ! -f "$CONTEXT_HELPER" ]]; then
  printf 'Missing context helper %s; set PARENT_ROOT to the create-reso-world main checkout containing scripts/superpowers_context.py\n' "$CONTEXT_HELPER" >&2
  exit 66
fi
CONTEXT_JSON=$(uv run --no-project python "$CONTEXT_HELPER" --operation review-fix \
  --parent-root "${PARENT_ROOT:-}" --doc-root "${DOC_ROOT:-}" --code-root "${CODE_ROOT:-}" \
  --repo "$PR_REPO" --doc-branch "${DOC_BRANCH:-}" \
  --head-repo "${HEAD_REPO:-}" --head-branch "${HEAD_REPO:+${HEAD_BRANCH:-}}") || exit 66
TOPLEVEL=$(printf '%s' "$CONTEXT_JSON" | jq -r .tool_root)
HELPER="$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
if [[ ! -f "$HELPER" ]]; then
  printf 'Missing comment helper %s; check the verified PARENT_ROOT checkout\n' "$HELPER" >&2
  exit 66
fi
uv run --no-project python "$HELPER" --pr "$PR_NUMBER" --repo "$PR_REPO" --model-name "$MODEL_NAME" \
  --records-file "$ROUND_JSON" <<EOF
## review-fix-planning（$MODEL_NAME）

対象 PR: #$PR_NUMBER（\`$HEAD_BRANCH\`） / サイクル: $ROUND / 現行 HEAD: \`$HEAD_SHA\`

### レビュー状況
...
### 作業判断
...
### 作業結果
...
EOF
```

ヘルパーは 1 行目にエージェントのマーカー `<!-- review-fix-planning:agent:<sanitized> -->`、2 行目にサイクルのマーカーを付け、末尾に判断の記録のブロックを付ける。更新するのは、同じサイクルの自分のコメントだけである。`gh pr comment --edit-last` は使わない。同じ GitHub アカウントを共有する別エージェントのコメントを上書きしてしまう。ヘルパーが失敗したら stderr を報告して止まる（終了コード 64）。代替の `gh` 呼び出しを組み立てない。同じサイクルの自分のコメントが複数ある場合も停止する。

## 分類の仕様

全指摘をこの 3 区分のいずれかに置き、区分ごとの件数を出す。どの指摘もいずれか 1 つに属する。自己レビューで出た指摘と、確認中に自分で見つけた PR の欠陥も同じ基準で分ける。

| 区分 | ここに入れてよいもの |
|---|---|
| **解消済み** | 現行 HEAD のコードで検証し、再現しないと確認できたもの。根拠（コミット・該当行）を 1 行添える |
| **対応する** | 次の両方を満たすものだけ:<br>1. **致命的である**（下記）<br>2. **現行 HEAD で確認できた**: (a) 再現した誤動作、(b) 事実誤認の記述で、そのとおりに進めると誤った結果になるもの、(c) 理由なく削除された回帰ガード<br>加えて、(d) ユーザがその指摘を名指しで依頼したものは、致命的でなくても対応する |
| **対応しない** | それ以外すべて。理由を 1 行書く |

**致命的** とは、直さずにマージ・利用すると、実在する構成やサポートしている使い方で次のどれかが起こり得ることをいう。

- 秘密情報の露出
- データの消失・破損
- 了承の無い設定変更、誤った対象（リポジトリ・ファイル・共有先）への操作
- 手順・ツールのとおりに使うと誤った結果になる、主要な処理や CI が止まる
- セキュリティ上の問題

起こり得るかどうかは、発生条件が実在する構成・使い方で到達できるかで判断し、その条件を 1 行書く。レビューの重大度ラベル、何モデルが指摘したか、`Approve` かどうかでは決めない。

**「対応しない」が既定である。** 上の条件を満たさないものは全てここに入る。ドキュメント追記もテスト追加も対応である — 軽いから足しておく、をしない。

既定で「対応しない」に入る典型:

- **事実として正しいだけの指摘** — 記録の書き方、列挙の漏れ、表記の揺れ、網羅の粗さ
- **仕様・設計の是非**（「どちらの挙動が正しいか」）— ユーザに問わない。「対応しない」に置き、論点を Spec に 1 行残す
- **第三者テーマ・外部利用者の互換性のみに影響するもの** — 公式の経路が一貫していれば対応しない
- 将来の保険、性能の過剰近似、Info 級の記載漏れ

リポジトリの方針ファイル（`AGENTS.md`・`CLAUDE.md` 等）が既に決着させている論点は「対応しない」に置き、その方針を根拠として引く。

## Spec は経路に関わらず必須

`superpowers:brainstorming` は bounded / spike 経路では Spec 不要と書いているが、**このスキルではユーザ指示が優先し、3 経路すべてで Spec を書く。** 完遂でも書く。

- 配置: `$DOC_ROOT/docs/superpowers/specs/`（create-reso-world の checkout。ルート `AGENTS.md` の規定）。常にこのリポジトリ側に置き、`MAIN_ROOT` が `external/resoloop` や他のリポジトリの checkout のときも、そちらへ置かない
- 命名: `YYYY-MM-DD-<topic>-review-fixes-design.md`
- 必須の中身:
  - 全指摘の一覧と 3 区分の振り分け（1 件も落とさない）
  - 「解消済み」「対応しない」それぞれの根拠 1 行
  - 「対応する」項目ごとの修正方針と検証方法、「守る条件と影響経路」の表
  - 計画のみでは brainstorming が判定した経路名。完遂では結論（三択のどれか）、実行許可（依頼の文言の要旨）、実行した検証と結果、自己レビューの観点と結果
  - レビュアーの構成の表（レビューファイル・モデル・ランタイム・レビュー HEAD・このサイクルで再実行したか）、planner のモデル、サイクルの番号。完遂では、修正と自己レビューの担当（`run_roles.py` の割り当て）、自己レビューの回数（呼び出し 1 回）、確認済みの一覧と工程の記録のパス
  - きっかけに当たった項目は、きっかけと根拠、守る条件の設計、比べた直し方と選んだ理由。「失敗時の検証」を行ったときは、比べた状態と対照の結果

## スコープ

解決したレビューディレクトリと、そのレビューが対象とするブランチ／PR だけを扱う。

- **他の worktree やブランチの未コミット差分を読みに行かない。** 見つけても計画に取り込まない
- 同じ条件に頼る経路は、PR の差分外も確認して直す（「守る条件と影響経路」）。原因の異なる新しい問題を探しには行かない。確認中に見つけた PR の致命的な欠陥は手順 3 のとおり扱う
- 計画のみの流れでは、実装は承認後。計画フェーズでプロダクトコードを編集しない
- 実装後はレビュー対象の既存 PR に載せる。第二の PR を開かない
- PR への反映後は、レビュー状況・作業判断・作業結果をレビュー対象の既存 PR へ投稿する。実装せず止まるターンの投稿は、完遂の結論 2・3 では必須（範囲外のリポジトリの例外は「作業終了前の PR 投稿」）、計画のみの承認待ちでは任意である。第二の PR を開かない

## 合理化とその実態

| 言い訳 | 実態 |
|---|---|
| 「bounded だから Spec は要らない」 | ユーザ指示がスキルに優先する。3 経路すべてで書く |
| 「計画を全文提示したので承認は不要」 | 提示は承認ではない。明示的な「進めて」を待つ |
| 「ドキュメント 1 行なら過剰対応ではない」 | ドキュメントも対応。致命的でなく (d) でもなければ「対応しない」 |
| 「要設計判断だがテストを 1 本足すだけなら」 | テスト追加も対応。致命的な指摘の修正と検証に要るときだけ足す |
| 「別 worktree に既に差分があったので活かす」 | 誰の何か分からない差分は範囲外。指定された範囲だけを見る |
| 「4 モデルが指摘しているので当然対応する」 | 票数ではなく、致命的かどうかと現行 HEAD での確認が根拠 |
| 「計画のみで、brainstorming は自分で設計できるので省く」 | 計画のみでは、経路判定と承認ゲートを持つ brainstorming を呼ぶ |
| 「working tree を見たら直っていたので解消済み」 | それは誰かの未コミット差分かもしれない。`git show <HEAD>:<path>` で確かめる |
| 「必須テンプレートの仕様を直せば根本解決する」 | 第三者互換の作り込み。方針ファイルが決着させているなら対応しない |
| 「仕様の是非なのでユーザに聞こう」 | 仕様論点は「対応しない」＋ Spec に 1 行。ユーザに問わない |
| 「進めては実装許可であり commit/push の許可ではない」 | この節が commit/push の指示である。関連テストが通ったら PR へ反映する |
| 「念のため全プロジェクトの `uv run pytest` と fork の全テストも通してから push する」 | 反映の条件は、実装に関連したテストと変更の種類に応じた検証だけである。それ以外は既存 PR の CI が確かめる |
| 「ユーザが commit と打つまで commit しない」 | このワークフローではこの節がその指示である |
| 「finishing-a-development-branch のメニューを出す」 | 出さない。既存 PR に push する |
| 「レビュー修正は別 PR にするものだ」 | レビュー対象の既存 PR に push する。`*-review-fixes` の追加 PR はしない |
| 「すでに review-fixes ブランチがある。捨てるのは無駄」 | サンクコスト。レビュー対象 PR の head ブランチに載せる |
| 「チャットに計画を書けば十分」 | PR への記録も反映作業の一部である。計画のみのターンの投稿は任意である |
| 「実装していないので投稿不要」 | 計画のみの投稿は任意である。commit / push まで完了したターンと、完遂の結論 2・3 は必須である（範囲外のリポジトリでは commit / push まで行ったターンだけ） |
| 「push したのでコメントは不要」 | PR に結果を残すことも反映の一部である |
| 「--edit-last で十分」 | 同じ GitHub アカウントを共有する別エージェントのコメントを上書きする。自エージェントのマーカーを持つコメントだけを更新する |
| 「追加確認が必要と報告すれば終われる」 | 未確認は途中の状態。自分で確かめて三択のどれかにする |
| 「確認できなかったので修正不要」 | 未確認は修正不要の根拠にならない |
| 「念のためもう一度自己レビューする」 | 修正後の自己レビューは 1 回まで。出た致命的な指摘は直して検証だけ通す |
| 「正しい指摘だから直す」 | 致命的でなければ「対応しない」 |
| 「Approve が多い／重大度が Low なので修正不要」 | 判定は致命的かどうかと現行 HEAD での確認。票数やラベルではない |
| 「差分外なので直さない」 | 同じ条件に頼る経路は、差分外も同じ PR で直す |
| 「設計の選択なのでユーザに聞く」 | 完遂では推奨案を選び、他の案と理由を Spec に残す |
| 「修正不要なのでマージしてよい」（範囲外・draft の PR） | マージは usaturn/create-reso-world と usaturn/resoloop の open で draft でない PR だけ。それ以外は結論 3 |
| 「pr-review で再レビューする」 | 完遂の自己レビューは `run_roles.py --phase self-review` の 1 回の中で行う。その外で pr-review を起動しない |
| 「枠を使い切ったので、別の名前の工程の記録で予約し直す」 | 上限の回避である。2 回目の自己レビューはしない |
| 「runner が success を返したので修正は合格」 | success は応答の回収である。fix-check の受け取り・指摘の判定・検証の結果で判断する |
| 「記録付きの投稿が拒否されたので、記録なしで投稿する」 | 切り替えない。記録の問題を直して投稿し直すか、止まって報告する |
| 「finalize.py は手間なので gh pr merge で済ませる」 | 修正不要のマージは `finalize.py` で行う。範囲・head・CI・記録の照合を省かない |
| 「base が進んだだけなので、検証の記録の `base` を新しい先端に書き換えて再実行する」 | 検証の記録は実際に検証したツリーを書く。新しい先端を head に merge したツリーで検証し直してから作り直す |
| 「古いレビューでも現行 HEAD で確かめたので結論 2 にする」 | 現行の PR head を再実行したレビュアーがいなければ記録を作れない。結論 3 にしてレビューの取り直しを報告する |
| 「前の回と同じ条件だが、今回の経路は別なので点の修正で足りる」 | 同じ守る条件の 2 回目である。設計の見直しに切り替え、仕組みから経路を列挙し直す |
| 「回帰は、入れたコミットを直せば済む」 | 修正が生んだ回帰は、前の回の列挙が足りなかった証拠である。設計の見直しに切り替える |
| 「同じ問題が続いたので、止めて利用者に判断を仰ぐ」（完遂） | 完遂では止まらない。設計の見直しを修正の中で行う。計画のみなら architectural にさせる |
| 「拒否のテストは非ゼロ終了を確かめているので十分」 | 状態全体を比べる。対象のファイルが変わらなくても、バックアップや認証が先に変わることがある |
| 「異常を詰め込んだ負例 1 本で網羅できる」 | 別の拒否の理由で止まり、ガードの欠落を見逃す。負例には異常を 1 つだけ入れる |
| 「ガードを入れたのでテストも効いているはず」 | ガードを外した対照で、負例が失敗することを確かめる |
| 「直した分だけ先に push しておく」 | 検証・自己レビューの判定・記録の確認が揃うまで push しない |

## Red flags — 止まって手順に戻る

- Spec ファイルのパスを言えない
- 「対応する」に入れた項目の再現手順を言えない
- 解決した review directory 外から持ち込んだ finding / review artifact、または未コミットの source/test ファイルが検証根拠になっている（解決した review directory 内のレビュー成果物は追跡状態にかかわらず正規の入力である）
- 計画のみの流れで、ユーザの「進めて」を受け取らないまま実装を始めようとしている
- 対応する に置いた finding ごとに、致命的である理由と (a)〜(d) のどれを満たすかを示せない
- 「解消済み」の根拠が、未コミットの変更を含む working tree のファイルである
- 変更と関係の無い一括検証（別のプロジェクトの `uv run pytest`、`scripts/resoloop-fork.sh test` など）を commit/push の条件として走らせようとしている
- 環境の変更なのに `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通さずに commit しようとしている
- レビュー修正のために新しい PR を開こうとしている、または `*-review-fixes` ブランチへ push しようとしている
- `finishing-a-development-branch` のメニューを出そうとしている
- 実装に関連したテストが通ったあと、二度目の「commit」「push」を待っている
- 実装に関連したテストが失敗したまま commit しようとしている
- `${TMPDIR:-/tmp}` 直下へ `review-fix-planning-*` を書こうとしている
- `worktree remove` を飛ばして `rm -rf` だけしようとしている（git の worktree 登録が壊れる）
- 手順 3 のあと `$REPRO_ROOT` を残そうとしている
- mktemp ではなくハイフン区切り名（`review-fix-planning-wt` / `-head` / `-repro-root`）を使おうとしている
- commit / push まで完了したターン、または完遂の結論 2・3（範囲外のリポジトリでは commit / push まで行ったターンだけ）なのに、レビュー対象に open な PR があるのに status comment を投稿せず終了しようとしている
- `gh pr comment --edit-last` を使おうとしている
- 他エージェントの PR コメントを編集しようとしている
- 自エージェントのマーカーが既にあるのに新規コメントを作ろうとしている
- 結論が三択のどれでもない（「追加確認が必要」「様子見」で終えようとしている）
- 未確認の指摘を残したまま「修正不要」にしようとしている
- 2 回目の自己レビューを始めようとしている（`run_roles.py --phase self-review` を 2 回呼ぶ、工程の記録に `pre_push_review` を手で書き足す）
- self-review・fix-check に codex の担当を割り当てようとしている
- 範囲外のリポジトリ、draft の PR をマージしようとしている
- `--match-head-commit` を付けずに、または値が空のまま（`--match-head-commit ""` は head を照合しない）マージしようとしている、修正不要のマージを `finalize.py` を使わずに行おうとしている
- 検証し直さずに、検証の記録の `base` を新しい先端に書き換えようとしている
- 記録付きの投稿が拒否されたのに、記録なしで投稿しようとしている
- 完遂で、自己レビューの役割（`run_roles.py`）の外で `pr-review` スキルを呼ぼうとしている、または `superpowers:brainstorming` を呼ぼうとしている
- 「対応する」項目に、守る条件と影響経路の表が無い
- 専用の worktree を使わず、メイン checkout や他の作業中の worktree で修正しようとしている
- `external/resoloop/reviews/` のレビューで PR の URL が無いのに、祖先の確認やディレクトリ名で `PR_REPO` を決めようとしている
- 結論 3 で、修正が無いのに Spec だけのコミットを PR の head ブランチに残そうとしている
- きっかけに当たるのに、守る条件の設計を書かずに点の修正をしようとしている
- 同じ条件の再発を理由に結論 3 で止まろうとしている
- 失敗時の扱いを直したのに、検証が終了コード・メッセージ・対象の 1 ファイルしか見ていない
- 1 つの負例に異常を 2 つ以上入れている
- ガードを外した対照を専用の worktree で行おうとしている
- 自己レビューの指摘の判定や記録の確認が済む前に push しようとしている
