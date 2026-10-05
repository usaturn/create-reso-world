---
name: review-fix-planning
description: PR とレビュー結果のディレクトリ（例 `reviews/ブランチ名/`、`docs/reviews/main/`、`reviews/#<PR番号>-<ブランチ>/` を指す `#番号`）を渡されて、修正要否の確定・指摘への対応・修正計画・指摘の取捨選択を求められたときに使う。「PR とレビュー結果を確認して修正要否を確定して」「レビュー指摘に対応して」「レビュー結果を確認して修正計画をたてて」「妥当な指摘だけ拾って直したい」「指摘のどれに対応するか決めたい」「複数モデルのレビューをまとめて」などの依頼が該当する。承認済みの review-fix 作業を実装する／対象ブランチへ反映させる依頼も該当する
allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *), Bash(rm *), Bash(test *), Bash(uv run *), Bash(bash .devcontainer/run-tests.bash*), Bash(bash scripts/check-layout.sh*), Bash(bash tests/scripts/*), Bash(bash scripts/superpowers-review-copy.sh*), Write(docs/superpowers/specs/**), Edit(docs/superpowers/specs/**)
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

## 第1引数の解決

第1引数が `#<番号>`（例 `#300`）のとき、手順に入る前にレビューディレクトリへ解決する:

- リポジトリのルートの `reviews/` 直下と、`external/resoloop/reviews/`（resoloop の PR のレビューが置かれる場所）の直下にあるディレクトリだけを見る。再帰せず、その階層のファイルは候補にしない。
- ディレクトリ名が `#<番号>-` で開始されるものを一致とする（`#<番号>` の直後にハイフンが続くもの。例 `reviews/#300-fix-issue-299-pr-review-budget/`）。
- 1 件だけ一致したら、そのディレクトリをレビューディレクトリとする。
- 0 件なら、`reviews/` と `external/resoloop/reviews/` の直下に一致するディレクトリが無い旨を報告して停止する。
- 複数一致したら、候補のディレクトリ名を列挙して停止し、フルパスでの指定を求める。

`#<番号>` 以外の第1引数は従来どおりレビューディレクトリのパスとして扱う。

PR の URL（`https://github.com/<owner>/<repo>/pull/<N>`）か番号が別に渡されたら、`<owner>/<repo>` を `PR_REPO`、`<N>` を `PR_NUMBER` にする。レビューディレクトリ名の `#<番号>` が `PR_NUMBER` と食い違うときは、推測せず停止する。

## 手順

依頼が承認済み Spec の実装完了／PR への反映のみで、新しい選別を求めていないなら、手順 1–7 を再実行しない。レビュー対象のブランチ／PR を `git` / `gh` で確認してから **実装後** の反映手順だけを実行する。

それ以外は、各項目をランタイムの plan / todo 機能のタスクにしてから開始する（Claude Code では TodoWrite、Codex では `update_plan`）。完遂では「三択の結論」の各段もタスクにする。

1. **範囲を固定する** — 解決したレビューディレクトリ配下の全ファイルを読む。各ファイル冒頭の「対象 HEAD」を記録する。複数世代が混在するのが普通である。レビュー成果物は gitignore 対象で未コミットのことがある（本リポジトリの `reviews/` がそうである）が、指定ディレクトリ内であれば Git の追跡状態にかかわらず正規の入力である。
2. **現行 HEAD を特定する** — レビュー対象のブランチ／PR の現在の先端を `git` / `gh` で確認し、対象 PR の `owner/name` を `PR_REPO` に設定する。ルート `AGENTS.md` の「リポジトリ境界」に従い、下記「共通 context の確認」を後続の Git 操作より前に実行する。`pr-review` と同じ共通 helper だが、修正用の明示 worktree は同じ Git repository（git-common-dir）に属する場合に使える。その他の repo は、ユーザの依頼または確認済みの引き継ぎで明示された絶対パスの `CODE_ROOT` と一致 remote 1 件が必要で、推測せず停止する。レビューディレクトリは `CODE_ROOT` 配下の `reviews/` をフルパスで受け取る。ResoLoop の不備は `scripts/resoloop-fork.sh clone` を案内して停止する。helper は `$MAIN_ROOT` ではなく照合済みの `$TOPLEVEL`（tool_root）から解決する。PR の状態・draft かどうか・base・head・本文・関連 Issue は `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json state,isDraft,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner,body,closingIssuesReferences` で読む。レビューと PR の対応も確かめる。`git -C "$MAIN_ROOT" fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"` の後、各レビューファイルの対象 HEAD がすべて `git -C "$MAIN_ROOT" merge-base --is-ancestor <対象 HEAD> FETCH_HEAD` を満たすこと。PR の URL が無く、対象のリポジトリが 1 つに決まらないとき（`external/resoloop/reviews/` は usaturn/resoloop と orange3134/resoloop の両方の PR を含み、番号が重なる）は、候補ごとに共通 context とこの確認を行い、満たすものが 1 件だけのときにそれを `PR_REPO` にする。満たさない、または 1 件に決まらないときは推測せず停止する（完遂では結論 3）。完遂では、続けて下記「専用の worktree」を用意する。
3. **各指摘を現行 HEAD の「コミット済み」内容で検証する** — `git show <HEAD>:<path>` で読む。指摘された path の `REVIEWED_HEAD` にある committed source/test blob は検証根拠として許可する。挙動の指摘は、path と reviewed HEAD を別引数にした隔離 worktree で再現する:

   ```bash
   REPRO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX")"
   WT="$REPRO_ROOT/worktree"
   git -C "$MAIN_ROOT" worktree add --detach "$WT" "$REVIEWED_HEAD"
   test "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$MAIN_ROOT" rev-parse "$REVIEWED_HEAD^{commit}")"
   ```

   `WT` はメイン checkout 外の一意な一時 path とする。SHA が一致しなければその worktree を根拠に使わず停止する。再現しないものは「解消済み」に落とす。

   **検証対象の source/test を working tree のファイルから読まない。** 手元の作業ツリーには誰かの未コミット変更が入っていることがあり、「もう直っている」という誤判定を生む。実際にこの誤判定は起きている。これは検証根拠の制約であり、入力であるレビュー成果物の読み取りには適用しない。例外は下記「専用の worktree」で、未コミットの変更が無く HEAD が PR の head と一致している間に限り、その中のファイルを committed content として読んでよい。

   **確認の範囲:** 結論にかかわらず、全指摘、PR の変更ファイルの全文、関連する処理（呼出元・同じ判定をする分岐）とテストを読む。一時的なコードで再現するときは上の隔離 worktree を使い、専用の worktree を汚さない。指摘ごとの検証・再現と関連箇所の調査は、互いに独立していれば使えるサブエージェントに任せ、使えなければ自分で行う。サブエージェントの監視は `monitoring-long-tasks` スキルに従う。確認中に PR が持ち込んだ致命的な欠陥を見つけたら、出どころを「自己確認」として指摘と同じように扱う。PR と関係しない既存の問題は直さず、致命的なものだけ報告に書く。

   **閉じ込め:** このセッションが検証のために作る一時ファイル（HEAD メモ、ログ、pytest 出力、スクラッチ）はすべて `$REPRO_ROOT` 配下に置く。`${TMPDIR:-/tmp}` 直下へ `review-fix-planning-*`、`review-fix-planning-*.txt`、ハイフン区切り名（`review-fix-planning-wt` / `review-fix-planning-head` / `review-fix-planning-repro-root`）を作らない。そのルートに置いてよいのは `mktemp` が返したディレクトリだけである。

   **teardown（手順 3 の終わり）:** `$WT` を使う検証がすべて終わったら、このセッションの worktree を外し、続けて親ディレクトリを消す。Spec 作成や承認待ちまで残さない。あとで再検証が必要なら新しい `mktemp` を作る。消したディレクトリは再利用しない。

   ```bash
   git -C "$MAIN_ROOT" worktree remove --force "$WT" && rm -rf -- "$REPRO_ROOT"
   ```

   `worktree remove` が失敗したら親を `rm -rf` しない（git の worktree 登録が欠けたパスを指す）。停止し、`$WT` と `$REPRO_ROOT` の完全パスを報告する。残りは `.devcontainer/cleanup-workspace.bash` に委ねる。`worktree remove` 無しで `rm -rf` だけを組み立てない。
4. **下記「分類の仕様」に従って全指摘を 3 区分に振り分ける。** 「対応する」項目ごとに、下記「守る条件と影響経路」の表を作る。
5. **修正方針を決める** — 計画のみでは `superpowers:brainstorming` を呼び、選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。完遂では brainstorming を呼ばない（人の承認を必須の段として持つため）。推奨案を自分で決め、設計の選択があれば他の案と選んだ理由を Spec に残す。ユーザに問わない。
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

## 専用の worktree

完遂では `pr-review` スキルを使わず、PR の head ブランチを checkout した専用の worktree で、修正・Spec のコミット（PR が create-reso-world のとき）・push を行う。計画のみと、実装後だけの依頼では作らない。

1. 手順 2 の共通 context（`HEAD_REPO` 無し）で得た `MAIN_ROOT`・`PR_REMOTE` と、手順 2 の `gh pr view` の結果を使う。`HEAD_BRANCH` は `headRefName`、`HEAD_SHA` は `headRefOid` である。
2. PR の head を取得して SHA を照合し、checkout 済みの worktree を調べる。fork からの PR でも `pull/<N>/head` で取れる。

   ```bash
   REPO_MAIN="$MAIN_ROOT"
   FIX_WT="$PARENT_ROOT/.worktrees/$(printf '%s' "$PR_REPO" | tr / -)-pr${PR_NUMBER}-review-fix"
   git -C "$REPO_MAIN" fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"
   test "$(git -C "$REPO_MAIN" rev-parse FETCH_HEAD)" = "$HEAD_SHA" || {
     printf 'PR head differs from gh pr view headRefOid; re-read the PR before creating the worktree\n' >&2
     exit 66
   }
   git -C "$REPO_MAIN" worktree list --porcelain
   ```

3. `branch refs/heads/$HEAD_BRANCH` を持つ worktree の有無で、次のどれかにする。
   - どこでも checkout されておらず、ローカルブランチも無い: `git -C "$REPO_MAIN" worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"`
   - ローカルブランチはあるが checkout されていない: `git -C "$REPO_MAIN" merge-base --is-ancestor "$HEAD_BRANCH" "$HEAD_SHA"` が成功するときだけ、`git -C "$REPO_MAIN" worktree add "$FIX_WT" "$HEAD_BRANCH"` の後に `git -C "$FIX_WT" merge --ff-only "$HEAD_SHA"`
   - 別の worktree で checkout されている: その worktree の `git status --porcelain` が空で、HEAD が `$HEAD_SHA` なら、それを `FIX_WT` として使う（片付けの対象にしない）
   - それ以外（ローカルブランチが PR に無いコミットを持つ、未コミットの変更がある、`FIX_WT` のパスが既にある）は、触らずに結論 3 にする
4. `CODE_ROOT="$FIX_WT"` とし、`HEAD_REPO`（`headRepositoryOwner` と `headRepository` の owner/name）と `HEAD_BRANCH` を設定して共通 context を再実行する。返る `MAIN_ROOT` は `FIX_WT` であり、以後の commit・push はそこで行う。
5. **片付け:** 結論 1 の push 後、結論 2 のマージ後、結論 3 の停止時（未コミットの変更が無いとき）に、このセッションが作った worktree を `git -C "$REPO_MAIN" worktree remove "$FIX_WT"` で外す（`--force` を付けない。失敗したら残して報告する）。このセッションが作ったローカルブランチは、先端が push またはマージした head の SHA と同じことを確かめてから `git -C "$REPO_MAIN" branch -D "$HEAD_BRANCH"` で消す。

## 守る条件と影響経路

「対応する」項目ごとに、修正の前に次の表を作り、Spec に残す。同じ原因の隣の経路が次のレビューで見つかる手戻りを防ぐためである。

1. 破れている条件（守るべき性質）を 1 文で書く
2. 同じ条件に頼っている経路を、PR の差分外も含めて列挙する。変更する関数・helper の全呼出元、同じ判定をする別の分岐、同じ前提を持つ別ファイル、変更前の挙動を保つ必要がある呼出元を含める
3. 経路ごとに「修正する」「既に満たす（根拠）」「対象外（理由）」を決める。「修正する」「既に満たす」の行には、確かめる方法（テスト・コマンド・再現手順）を付ける

| 守る条件 | 経路 | 判定 | 確かめる方法 |
|---|---|---|---|
| （1 文） | （ファイル・関数・分岐） | 修正する／既に満たす／対象外 | （テスト・コマンド・再現手順） |

列挙は、その条件に頼る経路を確かめる作業であり、原因の異なる新しい問題を探す作業ではない。「修正する」の行は、PR の差分外でも同じ PR で直す。

## 三択の結論

完遂では、手順 1–6 の後に次のどれか 1 つを完了させる。結論 1・2 では、「対応しない」とした指摘のうち実在する制約（直さないが事実として起こるもの）が PR の説明の保証と食い違うなら、PR の説明の既知の制限に条件と回避方法を書き足す（`gh pr edit --body-file`）。同じ論点が次のレビューで繰り返し挙がるのを防ぐためである。

### 結論 1: 修正して push する

「対応する」が 1 件以上あるとき。

1. 推奨案を基本に修正する。「守る条件と影響経路」の表の「修正する」の行は、PR の差分外も同じ PR で直す
2. **実装後** の手順 1–3（実装に関連したテストと、変更の種類に応じた検証）を通す。失敗したら直す。base でも同じように失敗する既存のテストは、base での結果を根拠として Spec に記録し、先へ進めてよい
3. 下記「修正後の自己レビュー」を 1 回だけ行う
4. 自己レビューで出た致命的な指摘を直し、手順 2 をやり直す。2 回目のレビューはしない。致命的でない指摘は「対応しない」として記録する
5. Spec に結果を書いて `completed` にし、コミットする（「Spec のコミットと確認用コピー」の完遂の項）
6. **実装後** の手順 4–6 で既存 PR の head へ push し、状況コメントを投稿する。その後「専用の worktree」を片付ける

### 結論 2: 修正不要としてマージする

「対応する」が 0 件で、全指摘・変更ファイルの全文・関連処理とテストの確認が終わったとき。

1. PR の変更の種類に応じた検証（**実装後** の手順 2）を、専用の worktree で通す
2. `git -C "$MAIN_ROOT" fetch "$PR_REMOTE" <base>` で base を取り直し、base が PR の分岐点より先に進んでいれば（`git -C "$MAIN_ROOT" merge-base --is-ancestor "$PR_REMOTE/<base>" "$HEAD_SHA"` が失敗する）、手順 3 と同じ `mktemp` の隔離 worktree で head に base を merge した一時的なツリーを作り、同じ検証を通す。この merge は push しない。検証後は手順 3 の teardown と同じ方法で消す
3. base と競合して merge できないときは、競合の解消を修正として扱い、結論 1 に切り替える
4. ルート `AGENTS.md` の「GitHub Actions」の規定で CI を確認する対象のリポジトリなら、`gh pr checks "$PR_NUMBER" --repo "$PR_REPO"` ですべての check の成功を確かめる。実行中なら `monitoring-long-tasks` スキルに従って待つ。PR の変更が原因の失敗は致命的な指摘として結論 1 に切り替え、基盤の障害なら結論 3 にする
5. 下記「マージしてよい範囲」を確かめる。範囲外なら、ここで結論 3 にする
6. Spec に結果を書いて `completed` にし、コミットする。PR が create-reso-world のものなら Spec は PR の head に載るので、次の順で push する。確認していないコミットをマージに含めないため、**実装後** の手順 5 の「reject されたら rebase または merge」はここでは使わない
   - commit の前に、`gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRefOid` が検証した `HEAD_SHA` と一致することを確かめる
   - commit の後、`git -C "$MAIN_ROOT" rev-parse HEAD^` が `HEAD_SHA` と一致し、`git -C "$MAIN_ROOT" diff --name-only HEAD^ HEAD` が Spec の 1 ファイルだけであることを確かめる
   - **実装後** の手順 5 の head の確認と共通 context の再実行の後、`git -C "$MAIN_ROOT" push "$HEAD_REMOTE" HEAD` で push する（fast-forward だけ。`--force` を付けない）
   - push 後、`HEAD_SHA` を `git -C "$MAIN_ROOT" rev-parse HEAD` に更新する
   - 一致しない、または push が reject されたら、rebase も merge もせず結論 3 にする（停止理由: 検証中に PR の head が更新された。Spec のコミットはローカルのブランチに残る）
7. 最終の状況コメントを投稿する（「作業終了前の PR 投稿」）
8. 検証した head だけをマージする

   ```bash
   gh pr merge "$PR_NUMBER" --repo "$PR_REPO" --merge --match-head-commit "$HEAD_SHA"
   ```

9. 関連 Issue を更新する
   - 手順 2 で読んだ `closingIssuesReferences` の Issue: マージ後に自動で close されていなければ、結果をコメントして close する
   - PR の本文・タイトルで参照しているだけの Issue: マージの結果と残りの作業をコメントする。本文のチェック項目のうち、この PR で完了したことが明らかなものは、本文を取り直してから `[x]` にする
10. 「専用の worktree」を片付ける

**マージしてよい範囲:** `usaturn/create-reso-world` と `usaturn/resoloop` の、open で draft でない PR だけ。それ以外（上流の `orange3134/resoloop` など）は、修正不要と判定してもマージせず結論 3 にする。範囲外のリポジトリへのコメント投稿は、commit / push まで行ったターンだけ必須である。

### 結論 3: 停止する

次の場合だけ。未完了であること、具体的な停止理由、済んだ作業（コミット・push・投稿の有無）を報告する。書き始めた Spec があれば `draft` のままコミットし、停止理由を書く。

- 権限: マージしてよい範囲外、push・マージの権限が無い、`gh` の認証が無い
- PR の状態: draft、close 済み、マージ済み
- 環境: 共通 context の確認が止まった（exit 64〜66）、レビューと PR の対応を確かめられない（手順 2）、検証中に PR の head が更新された（結論 2 の手順 6）、head ブランチが PR に無いコミットや未コミットの変更を抱えている、必要なツールが無い
- 外部障害: GitHub の API・ネットワークの障害、CI 基盤の障害

未読・未検証、判断に迷う、修正が大きい、テストが失敗する（直す）、再現できない（根拠を付けて「解消済み」か「対応しない」にする）は、結論 3 の理由にならない。

### 修正後の自己レビュー

結論 1 の修正後に最大 1 回だけ行う。`pr-review` スキルは使わない。使えるサブエージェントが複数あれば、次の 3 観点を別々に同時に担当させ、それを 1 回と数える。使えなければ、自分で全観点を 1 回だけ見る。

1. **反証** — 「守る条件と影響経路」の表を渡し、修正した条件が破れる入力・操作順・経路と、旧版との挙動の差を探す
2. **PR 全体** — 修正後の PR の全差分と変更ファイルの全文を読み、致命的な問題を探す
3. **検証の検出力** — 追加・変更したテストと検証が、修正対象の欠陥を実際に検出できるか（assertion が変更対象全体を見ているか、別の拒否理由に隠れていないか）

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

**完遂では** 手順 2・3（確認用コピーと提示）を省き、承認を待たない。Spec は 1 回だけコミットする。結論 1 では自己レビュー後の修正と検証が終わってから push の前に、結論 2 ではマージの前に、結論・検証の結果・自己レビューの結果を書いて状態を `completed` にする。push・マージ・Issue 更新の結果は Spec に追記せず、状況コメントと完了報告に書く（記録だけのコミットを PR に足さないため）。結論 3 で止まったら、書き始めた Spec を `draft` のままコミットし、停止理由を書く。PR が create-reso-world のものなら、手順 1 の `DOC_ROOT` は専用の worktree である。手順 4 の公開の規則は変わらない。

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
4. 共通 context を再実行し、`git -C "$MAIN_ROOT" fetch "$PR_REMOTE"` で取得する。取得後に `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRefOid` でレビュー対象 PR の実際の先端も再確認する。手順 1・2 が通ったら、レビュー対象ブランチ（既存 PR の head）へ commit する。`main` ではない。新しい `*-review-fixes` ブランチでもない。
5. そのブランチを **既存 PR** へ `git -C "$MAIN_ROOT" push "$HEAD_REMOTE" HEAD` する。push の成功を確認する。reject されたら rebase または merge し、手順 1・2 を再走してから再度 push する。新しい PR を開かない。`finishing-a-development-branch` のメニューを出さない。対象リポジトリにかかわらず、すべての push の前に `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRepository,headRepositoryOwner,headRefName` で PR の head リポジトリとブランチを確かめ、その確認結果を `HEAD_REPO`・`HEAD_BRANCH` に設定して共通 context を再実行し、返された `HEAD_REMOTE` へ push する。fork からの PR では base と head が別のリポジトリである。該当する remote が 1 つに決まらなければ推測せず停止する。
6. 完了報告の前に **作業終了前の PR 投稿** を実行する。

レビュー対象ブランチに open な PR が無いなら、作らず停止して報告する。ユーザが作れと言うまで作らない。コメントの投稿もしない。

**この節が commit / push の常設指示である。** 二度目の「commit」「push」を待たない。「進めて」は実装の承認であり、この手順が PR への反映である。

**commit / push の条件にしないもの:** 上の検証に含まれない一括検証（変更と関係の無いワールドのプロジェクトの `uv run pytest`、`scripts/resoloop-fork.sh test` による fork の全テストなど。既存 PR の CI がまだ走る）、`superpowers:verification-before-completion` のフルスイート、`superpowers:finishing-a-development-branch`。

例: レビュー対象 PR は `usaturn/create-reso-world` の #12 で、Spec の検証が `bash tests/scripts/test-check-layout.bash` —— `scripts/check-layout.sh` を直す環境の変更なので、`MAIN_ROOT` は toplevel。そのテストに続けて `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通す。`fix/check-layout-mounts` に commit し、手順 5 の API 確認と共通 context の再実行で得た `HEAD_REMOTE` を使い、`git -C "$MAIN_ROOT" push "$HEAD_REMOTE" HEAD` で既存 PR へ反映する。status comment の `PR_REPO` は `usaturn/create-reso-world`。変更と関係の無いプロジェクトの `uv run pytest` は走らせない。`fix/check-layout-mounts-review-fixes` は開かない。push 後、同じ PR にレビュー状況・作業判断・作業結果のコメントを作成または更新する。

resoloop の上流への PR も同じ規則が fork の経路で成立する: `PR_REPO=orange3134/resoloop`、`MAIN_ROOT` は `$TOPLEVEL/external/resoloop` で、取得は共通 context が返す `PR_REMOTE`（通常は `upstream`）を使い、PR の head branch は fork にあることを手順 5 の API と共通 context で確認する。その結果の `HEAD_REMOTE`（通常は `origin`）を使って `git -C "$MAIN_ROOT" push "$HEAD_REMOTE" HEAD` で反映する。検証は変更したプロジェクトに関連する `dotnet test` までで、`scripts/resoloop-fork.sh test` による全テストは反映の条件にしない。

## 作業終了前の PR 投稿

この節の目的は後続エージェント・レビュアーへの永続的な記録に限る。完了通知待ちの停止（stall）対策ではない。stall は監視側（Monitor / PID）の課題である。

コメントは単体で読めること。PR だけを読む読み手が Spec 無しで判断を理解できるように書く。

**commit / push まで完了したターンと、完遂の結論 2（マージの前）では必須である。** commit / push まで実装したターンは push 後に1回投稿する。承認待ちで止まるだけのターンの投稿は任意である。同じエージェントの既存コメントがあれば更新し、無ければ新規作成する。他エージェントのコメントは読んでよいが編集しない。

レビュー対象ブランチに open な PR が無い場合は投稿しない。PR を作ることもしない。チャットで報告して止まる。

**リポジトリ:** レビュー対象 PR を持つ `owner/name` を `PR_REPO` にする。ヘルパーは作業ディレクトリから推測しないため、PR 番号だけで別リポジトリへ投稿されることはない。

**モデル識別子:** ランタイムが提示する正確な識別子を `MODEL_NAME` にする。ファイル名や系列名から推測しない。取得できなければ投稿せず確認する。

**コメントは日本語で書く。** 次の3見出しだけをこの順で使う。Spec 全文は貼らない。早期停止では分かる範囲を書き、未実施の節は `未実施` とする。PR への反映のみの依頼でも、承認済み Spec の要旨をレビュー状況と作業判断にまとめる。再検証はしない。

```markdown
## review-fix-planning（<MODEL_NAME>）

対象 PR: #<N>（`<branch>`） / 現行 HEAD: `<sha>`

### レビュー状況
- 入力: `<review-dir>`（読んだファイルと各対象 HEAD）
- 分類: 解消済み N / 対応する N / 対応しない N

### 作業判断
- 対応する: 各 ID と、致命的である理由・確認方法を 1 行
- 対応しない: 全件を ID と一行理由で記載する（件数要約のみにしない）
- 解消済み: 件数と代表根拠

### 作業結果
- 結論: 1 修正して push | 2 修正不要でマージ | 3 停止（理由） | 計画のみ（承認待ち）
- 自己レビュー: 観点と結果（自己レビュー後の修正は再レビューしていない） | 未実施
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
uv run --no-project python "$HELPER" --pr "$PR_NUMBER" --repo "$PR_REPO" --model-name "$MODEL_NAME" <<EOF
## review-fix-planning（$MODEL_NAME）

対象 PR: #$PR_NUMBER（\`$HEAD_BRANCH\`） / 現行 HEAD: \`$HEAD_SHA\`

### レビュー状況
...
### 作業判断
...
### 作業結果
...
EOF
```

ヘルパーは `<!-- review-fix-planning:agent:<sanitized> -->` を付与し、そのマーカーを持つコメントだけを更新する。`gh pr comment --edit-last` は使わない。同じ GitHub アカウントを共有する別エージェントのコメントを上書きしてしまう。ヘルパーが失敗したら stderr を報告して止まる。代替の `gh` 呼び出しを組み立てない。自エージェントのマーカーを持つコメントが複数ある場合も停止する。

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

## スコープ

解決したレビューディレクトリと、そのレビューが対象とするブランチ／PR だけを扱う。

- **他の worktree やブランチの未コミット差分を読みに行かない。** 見つけても計画に取り込まない
- 同じ条件に頼る経路は、PR の差分外も確認して直す（「守る条件と影響経路」）。原因の異なる新しい問題を探しには行かない。確認中に見つけた PR の致命的な欠陥は手順 3 のとおり扱う
- 計画のみの流れでは、実装は承認後。計画フェーズでプロダクトコードを編集しない
- 実装後はレビュー対象の既存 PR に載せる。第二の PR を開かない
- PR への反映後は、レビュー状況・作業判断・作業結果をレビュー対象の既存 PR へ投稿する。実装せず止まるターンの投稿は任意である。第二の PR を開かない

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
| 「実装していないので投稿不要」 | 計画のみの投稿は任意である。commit / push まで完了したターンのみ必須である |
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
| 「pr-review で再レビューする」 | 完遂の自己レビューはこのスキルの中で行う。pr-review は使わない |

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
- commit / push まで完了したターンなのに、レビュー対象に open な PR があるのに status comment を投稿せず終了しようとしている
- `gh pr comment --edit-last` を使おうとしている
- 他エージェントの PR コメントを編集しようとしている
- 自エージェントのマーカーが既にあるのに新規コメントを作ろうとしている
- 結論が三択のどれでもない（「追加確認が必要」「様子見」で終えようとしている）
- 未確認の指摘を残したまま「修正不要」にしようとしている
- 2 回目の自己レビューを始めようとしている
- 範囲外のリポジトリ、draft の PR をマージしようとしている
- `--match-head-commit` を付けずにマージしようとしている
- 完遂で `pr-review` スキルや `superpowers:brainstorming` を呼ぼうとしている
- 「対応する」項目に、守る条件と影響経路の表が無い
- 専用の worktree を使わず、メイン checkout や他の作業中の worktree で修正しようとしている
