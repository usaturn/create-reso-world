---
name: issue-to-pr
description: "Issue の URL・#番号を指定して『着手して』『実装して PR まで』『推奨案で進めて』と依頼されたときに使う。PR の番号・URL、PR レビュー・レビュー指摘の修正計画、ボードの親 Issue からの子の選択には使わない。"
argument-hint: "<Issue> [--implement AGENT] [--merge [--max-cycles N] [--assign ROLE=AGENT[,AGENT]]... [--template PATH] [--config PATH]]"
---

# Issue to PR

## 1. 入口と委任の範囲

このスキルによる着手を、**通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示**として扱う。質問、設計・Spec・Plan の確認、実行方式、終了方法の選択は追加で尋ねない。AGENTS.md の「曖昧なら確認する」は、ここでは仕様の意味を変える判断・安全境界・後述の停止条件に適用する。実在しない承認や検証結果を記録しない。マージは、`--merge` のときにループの中の `finalize.py` が行うものだけで、それ以外ではしない。

- **Claude Code など:** `superpowers:using-superpowers` を読み、以下の流れを開始する。
- **Pi:** 自動 bootstrap や設定を変更しない。明示 `/sp-brainstorm` から開始し、このスキルを使う。明示 `/skill:issue-to-pr` から読み込まれた場合も opt-in として、`brainstorming` を直接読んで開始できる。
- Pi で自然言語の依頼しかなく、明示 `/sp-*`・`/skill:*` 限定の指示がある場合は、読み取りだけで入力を解決し、次の入口を案内して終了する。モデルがスラッシュコマンドを実行したふりをしない。

```text
/sp-brainstorm <解決した Issue URL> issue-to-pr を使い、推奨案で進めて途中で止めずに PR まで作成せよ
```

一度明示入口から開始した run では、工程ごとに次のコマンド入力を求めず、各スキルを読んで最後まで続ける。ランタイムの明示された承認・ツール制限は迂回しない。

**オプションは `--implement`・`--merge`・ループ用のオプション（`--merge` と一緒のときだけ）を受け付ける。** ほかのオプション（`--hold-action`・`--fresh-review` を含む）は、2 章の helper が理由を出して終了コード 2 で止まる。そのまま止まって理由を伝える。オプションを外して続けない。

### `--implement`

Plan の Task を実装する担当は、agent-runner の `workflows.issue` の `implement` で決まる（雛形 `.devcontainer/agent-runner.toml` < 個人設定 < `--implement`）。雛形の既定は `self`（このセッションが自分で実装する）。

- `--implement AGENT`（`--implement=AGENT` も同じ）は、その回だけ一次担当を置き換える。値は agent-runner の設定にある agent 名か `self`。`fallback` は設定のものを保つ
- Issue の参照の前でも後でも書け、1 回だけ書ける
- 担当の検査は 2 章の 3、依頼の手順は 4 章の「Task の実装を runner の担当に依頼する」

### `--merge`

`--merge` は、PR を作った後に PR 修正ループ（pr-review-fix-loop）を回し、修正不要と確かめられたら、マージと関連 Issue の更新まで進める指示である。ループの中の判断（致命的な指摘だけを直す、三択の結論、修正後の自己レビューは最大 1 回）は review-fix-planning のままで、マージはその `finalize.py` だけが行う。

- 有効なのは、**利用者のメッセージ（スラッシュコマンドの引数を含む）に `--merge` という語が書かれているときだけ**。自然文の「マージまで」「マージして」は `--merge` として扱わない。モデルが自分でこのスキルを選んだ run で `--merge` を補わない
- ループ用のオプションは `--max-cycles N`・`--assign ROLE=AGENT[,AGENT]`（複数可）・`--template PATH`・`--config PATH` で、名前・値・意味は pr-review-fix-loop の `start` と同じ。`--merge` と一緒のときだけ受け付ける。`--merge` もループ用のオプションも、Issue の参照の前でも後でも書ける。**利用者が書いたものだけを、書いた順に渡す。** 既定値を足さない（ループの既定はサイクルの上限 3、レビュアーと担当は agent-runner の設定のとおり）
- `--hold-action` は受け付けない（このリポジトリの review-fix-planning には判断保留が無く、ループも受け付けない）。`--fresh-review` も受け付けない（作ったばかりの PR には再利用するレビューが無い）
- ループの `--assign implement=…` はレビュー修正の担当（`workflows.fix` の `implement`）で、Plan の Task の担当（`--implement`）ではない。ループの `--template`・`--config` も `implement_task.py check` には渡さない
- 使えるのは、`TARGET_REPO`（2 章の 5）が usaturn/create-reso-world か usaturn/resoloop のときだけ（ループが扱え、`finalize.py` がマージしてよい範囲）
- `--merge` のときは、Plan の実行予算（4 章の 3）にループの段階を含める（目安はサイクルの上限 ×（レビューの期限 45 分＋計画・修正））
- 手順は 2 章の 3 の `check-options`、5 章の検証の記録と「`--merge` のとき: PR の作成後のループ」。`--merge` が無い run は PR の作成で終わり、ループもマージもしない

## 2. 入力・対象・競合の確認

1. 作業対象に適用される AGENTS.md を読む（ルートの「リポジトリ境界」「Spec・Plan の保存と公開」「GitHub Actions」を含む）。
2. スキルの実ディレクトリを `SKILL_DIR` とし、create-reso-world の main checkout `PARENT_ROOT` を求めて、`origin` が usaturn/create-reso-world であることを確かめる。

   ```bash
   PARENT_ROOT=$(dirname "$(git -C "$SKILL_DIR" rev-parse --path-format=absolute --git-common-dir)")
   git -C "$PARENT_ROOT" remote get-url origin
   ```

3. `INPUT` は、**利用者が書いた引数の先頭から、Issue の参照とオプションのうち最後のものまでを、書かれたまま切り出した文字列**である。後ろに続く自然文は含めない（`#12 推奨案で進めて` なら `#12`、`#12 --merge --max-cycles 2 途中で止めずに` なら `#12 --merge --max-cycles 2`）。語を足したり並べ替えたりしない。現在の checkout を cwd として、読み取り専用の helper を実行する。

   ```bash
   uv run --no-project python "$SKILL_DIR/scripts/resolve_issue.py" -- "$INPUT"
   ```

   - 受け付ける表記: `https://github.com/<owner>/<repo>/issues/N`、`<owner>/<repo>#N`、`#N`（**現在の checkout の origin** で解決する。番号からリポジトリを推測しない）。対象は usaturn/create-reso-world・usaturn/resoloop・usaturn/resoloop-meshy だけ
   - 成功: 終了コード 0、`repo`・`number`・`url`・`title`・`body`・`merge`・`implement` の JSON。`merge` は `--merge` が無ければ `null`、あれば `{"loop_args": [...]}`（利用者が書いた順のループ用のオプション。パスは絶対パス）。`implement` は `--implement` の値か `null`。**最初に `repo` と `title` を利用者に表示する。** 失敗: 終了コード 2 と stderr の理由。副作用に進まずに止まる
   - helper は入力の検証と Issue の確認だけで、競合・予約・承認を確かめた証拠にはならない
   - `merge` が `null` でなければ、続けて `PARENT_ROOT` の `loop.py` で、ループ用のオプションと agent-runner の設定を検査する。`loop_args` の要素を順に、それぞれ 1 つの引数として渡す（空なら引数なし）。

     ```bash
     uv run --project "$PARENT_ROOT" --locked python \
       "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" check-options <loop_args の各要素>
     ```

     終了コード 0 なら、出力の `options`・`assignments` を Spec の決定記録に写す（既定値は既定の適用と書き、利用者の指定と書かない）。終了コード 2 なら `reason`（argparse の拒否は stderr）を利用者に伝えて止まる。worktree・Herdr・予約のどれにも触れない。

   - 続けて Plan の実装の担当を検査する。`implement` が `null` でなければ `--implement <implement の値>` を付け（値は 1 つの引数として渡す）、`null` なら付けない。

     ```bash
     uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/implement_task.py" check [--implement <値>]
     ```

     終了コード 0 なら、出力の `assignment`（`agents`・`fallback`）と `self` を Spec の決定記録に写す（雛形の既定の `self` は既定の適用と書き、利用者の指定と書かない）。終了コード 2 なら `reason` を利用者に伝えて止まる（設定に無い agent、`agents` が 2 つ以上、`implement` の役割の `writes = false` など）。worktree・Herdr・予約のどれにも触れない。

4. 本文、全ページのコメント、依存関係を読む。本文が利用者の承認・判断を求めていて、決定の記録が無ければ、推奨案での委任で代えずに止まる。
5. 実装の対象 `TARGET_REPO` を決める。既定は helper の `repo`。本文が実装の対象を明記していれば（「実装の対象: usaturn/resoloop」など）それに従う。3 つの外なら止まる。`merge` があり、`TARGET_REPO` が usaturn/resoloop-meshy なら止まる（ループが `CODE_ROOT` なしで checkout を決められず、`finalize.py` がマージしてよい範囲の外）。`--merge` を外して指示し直せることを伝える。`TARGET_REPO` の行で checkout（`TARGET_ROOT`）と remote を確かめる。checkout が無い・remote が違うときは「無いとき」の案内をして止まる。checkout を探したり clone したりしない。

   | `TARGET_REPO` | `TARGET_ROOT` | 確かめる remote | 無いとき | 検証の入口 | CI |
   | --- | --- | --- | --- | --- | --- |
   | usaturn/create-reso-world | `$PARENT_ROOT` | `origin` | — | worktree のルートで `README.md` の「テスト」のコマンド（ワールドの行を除く） | private で止めている。確かめない |
   | usaturn/resoloop | `$PARENT_ROOT/external/resoloop` | `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop | `scripts/resoloop-fork.sh clone` を案内 | worktree で `dotnet test ResoLoop.slnx --nologo` | public。PR の checks が green になるのを確かめる |
   | usaturn/resoloop-meshy | `$PARENT_ROOT/external/resoloop-meshy` | `origin` が usaturn/resoloop-meshy | `bash scripts/resoloop-meshy.sh clone` を案内 | worktree で `uv run pytest` | Actions を無効にしている。確かめない |

6. **worktree を作る前に**次を調べる。どれかあれば、新しい作業を作らずに状態を報告して止まる。古い予約も、作った人が分からない既存の worktree・branch も使い回さない。
   - 同じ Issue の open PR（`TARGET_REPO` と、文書専用の PR を出す場合は create-reso-world。linked Issue、本文、branch を見る。最初のページだけで判定しない）
   - create-reso-world の `refs/heads/agent-claims/issue-N`、コメントに記録された未解放の担当
   - `TARGET_ROOT`（と文書用の worktree を作る場合は `PARENT_ROOT`）の既存の worktree、ローカル・remote の branch（`issue-N` を番号の境界で照合し、N=58 と N=580 を混同しない）
   - 未完了の先行 Issue・必要な未マージ PR
   - 親 Issue か handoff が、`main` 以外（統合用の branch など）を PR の向き先に指定している。この版は未対応なので、黙って `main` に向けない

   既存の open PR で止まるときは、その PR の URL と base（`gh pr view <PR> --repo <repo> --json url,baseRefName`）を報告し、レビューは `/pr-review <PR の URL>`、指摘の修正の計画は `review-fix-planning` で行えると伝える。案内には PR の URL を使う（番号だけでは、別のリポジトリの PR を cwd の origin の PR として解決する）。`--merge` があっても、既存の PR をループに乗せない（`loop.py start` を実行しない）。ループで続けるかは利用者が決め、続けるなら `/pr-review-fix-loop <PR の URL>` で行える。

   worktree を作る直前と、push・PR の作成の前に、Issue の状態と競合を調べ直す。新しい競合や close があれば止まり、この run で作った worktree・branch と他者の作業を区別して報告する。
7. ボードの子（GitHub の親 Issue があり、子か親の本文にボードのキーがある）は **`planning-parallel-issues` 必須**。予約・先行条件・成果の公開・所有権の再確認・解放はそちらに従い、このスキルに写さない。親からの子の選択は担当外。

`gh issue`・`gh pr` には毎回 `--repo` を付ける。`gh api` は `--repo` を受け付けないので、`repos/<owner>/<repo>/...` の完全な endpoint で対象を固定し、一覧は `--paginate` で取る。

## 3. Herdr と作業場所

着手の条件がそろったら、`HERDR_ENV=1` のときに `herdr-agent-task` と `herdr` を読む。**現在の pane** の名前とタスクを設定する。ほかの pane や focus を変えない。

```bash
herdr pane rename "${HERDR_PANE_ID:?}" "Issue#${NUMBER:?}"
herdr-agent-task set "Issue #$NUMBER 実装・PR作成"
```

現在の pane が分からない・rename が失敗したときは、別の pane を推測せず、rename を省いて続け、最終報告に書く。

**必須:** `superpowers:using-git-worktrees` に従い、status・worktree 一覧・ignore を確かめて、**`TARGET_ROOT` の最新の `origin/main`** から `TARGET_ROOT/.worktrees/<名前>` に新しい worktree を作る（`git -C "$TARGET_ROOT" fetch origin` の後、`git -C "$TARGET_ROOT" worktree add -b <branch> .worktrees/<名前> origin/main`）。

- 名前は `issue-N-<要約>`、branch は `feat/issue-N-<要約>` か `fix/issue-N-<要約>`。Issue が `TARGET_REPO` と別のリポジトリにあるときは、名前と branch の `issue-N` の前にそのリポジトリ名を付ける（create-reso-world の #203 を resoloop で実装するなら `create-reso-world-issue-203-<要約>`）
- `TARGET_REPO` が create-reso-world でなければ、Spec・Plan 用に `PARENT_ROOT/.worktrees/<名前>` にも、branch `docs/<名前>` の worktree を `origin/main` から作る（Issue が create-reso-world の外にあるときは、`<名前>` の先頭にそのリポジトリ名を付ける）
- main checkout（detached HEAD）では編集しない

以降、create-reso-world の Spec・Plan を置く checkout を `DOC_ROOT` と呼ぶ（`TARGET_REPO` が create-reso-world なら実装の worktree、ほかは文書用の worktree）。

## 4. 推奨案 → Spec → Plan → 実装

1. **`superpowers:brainstorming` 必須。** 利用者はこの指示で質問を省くことを選んでいるので、問答をせずに推奨案を選ぶ。意図・受け入れ条件・編集禁止を整理する。
2. Spec を `DOC_ROOT` の `docs/superpowers/specs/` に書いて commit する。冒頭に管理・実行許可（利用者の指示の引用、許可された範囲、状態 `draft`）を書き、`approved` にしない。**決定記録**を設け、各項目に「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」を残す。確認用のコピー（`scripts/superpowers-review-copy.sh`）は作らない。
3. **`superpowers:writing-plans` 必須。** Plan を `DOC_ROOT` の `docs/superpowers/plans/` に作って commit する。実在する Spec のパス、Task、担当ファイル、検証の入口（2 章の表）、実行方式と理由、contingency を書く。AGENTS.md の SDD 実行運用に従う。実装前に [要件・原因・検証の対応](../review-fix-planning/references/convergence.md) の「1. 実装前の要件照合」を読み、Spec の条件・除外範囲と Task・観測結果・検証を照合する。共有する入力・状態・順序・外部仕様の確認は統合担当の Task にする。単純な変更は Plan の短い対応メモでよく、別帳票は作らない。
4. 実行方式は次で決める。ランタイムのツール仕様を確かめ、存在しない一覧操作や同期フラグを渡さない。リポジトリが要求する起動条件を満たせなければ inline を選ぶ。

   | 条件 | 選ぶ方式 |
   |---|---|
   | 2 章の 3 の `check` の `self` が false | 下の「Task の実装を runner の担当に依頼する」（`superpowers:subagent-driven-development` の形で、各 Task を runner の担当に依頼する） |
   | `self` が true で、Task が独立し、文脈を子に渡しきれ、同期委譲を使える | `superpowers:subagent-driven-development` |
   | `self` が true で、同じファイルの逐次変更、1–2 Task、委譲不可 | `superpowers:executing-plans` |

   Pi の `/sp-implement` は直列実行、`/sp-implement-parallel` は依存を満たした独立 Task を別 worktree で並列実行する入口。SDD なら常に parallel という対応ではない。同じファイルを同時に書かせない。run 中は選んだスキルで続け、コマンド再入力待ちにしない。
5. 選んだスキルの実装・TDD・レビューに従い、最後のブランチ全体のレビューを省かない。実装担当（inline なら自分）へ、照合した条件・除外範囲・共有前提・必要な証拠を渡す。個別 Task の成功だけで共通条件を満たしたとせず、統合担当が条件単位で確認する。スキルを作る場合は `superpowers:writing-skills` の無し/ありの振る舞い比較を行い、固定文言の検査テストで代用しない。テストは AGENTS.md の「テストの採用基準」に従い、迷ったら書かない。検証の失敗は `systematic-debugging` で調べ、解消できなければ止まる。

### Task の実装を runner の担当に依頼する（`self` 以外のとき）

`superpowers:subagent-driven-development` を読み、Task を実装するサブエージェントの代わりに、`implement_task.py` で runner の担当に Task を 1 つずつ順に依頼する（並行しない）。runner の担当は入れ子に agent を起動できないので、Plan 全体を 1 回で渡さない。

1. **出力先:** `uv run --no-project python "$PARENT_ROOT/.agents/scripts/agent_tmp.py" mkdir issue-<N>-implement` で作ったセッションディレクトリ（`SESSION`）の下の、存在しないパス（例: `$SESSION/task-2-attempt-1`）を依頼ごとの `RUN_DIR` にする。`/tmp` の下に置かない（DSH の隔離（bubblewrap）は `/tmp` を差し替えて起動するので、`/tmp` の下では失敗する。ログは後で読む）
2. **依頼の JSON（`REQUEST_JSON`）:** 次の 6 項目だけを書き、`$SESSION` の下にファイルで置く。
   - `repository`: feature worktree（`TARGET_ROOT/.worktrees/<名前>`）の root の絶対パス。`revision`: その HEAD の完全な SHA（未 commit の変更を残さない）
   - `task`: 1 行の Task 名。`allowed_files`: Plan のその Task の担当ファイル（root からの相対パス。`/` で終わればディレクトリ）
   - `commit_message`: Plan の commit の手順のメッセージ（担当が commit できなかったときに helper が使う）
   - `prompt`: 担当がそれだけで作業できる依頼。Plan のその Task の全文、Spec の関係する節、受け入れ基準（Task をレビューする担当に渡すものと同じ）、実行する関連テストと静的チェック、テストの要否と理由。担当がどのスキルを読めるかはランタイムで違うので、スキルを前提にしない。作業範囲・禁止事項・返す JSON の形は helper が足す
3. **依頼:** 終わるまで待つ（`implement` の役割の期限は 90 分。`monitoring-long-tasks` に従い、Claude Code では `run_in_background: true` の完了通知で待つ）。

   ```bash
   uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/implement_task.py" run \
     --request "$REQUEST_JSON" --output-dir "$RUN_DIR" [--implement <値>]
   ```

   出力の `verdict` で次を決める。どの `verdict` でも、次の依頼を出す前・止まる前に、その依頼の `RUN_DIR` を 5 のとおり片付ける。

   | `verdict` | 次の操作 |
   | --- | --- |
   | `importable` | `implement_task.py accept --run-dir "$RUN_DIR"`。判定を今の状態でやり直し、担当が commit しなかったとき（`helper_commit`）は helper が `commit_message` で commit してから、feature worktree に `--ff-only` で取り込む |
   | `no_changes` | 取り込むものは無い。Task のレビューで、変更が要らないことを確かめる |
   | `retry`（担当が `BLOCKED`・`NEEDS_CONTEXT`） | `result.concerns`・`result.incomplete` に答える文脈を `prompt` に足し、同じ担当に新しい依頼をする（新しい `RUN_DIR`）。回数は Plan の「実行予算」の再試行の上限まで。上限に達したら止まる |
   | `rejected`（`outside_changes`、取り込みの前の確認に反した） | 取り込まない。再試行の上限の中で依頼し直すか止まるかを決め、`reasons` と理由を ledger に書く |
   | `failed`（停止を確認できない、期限切れ・認証待ち・起動の失敗、`fallback` が尽きた。結果の形の誤りは runner が `fallback` の次の候補を試し、尽きたらここに入る） | その Task で止まる |

4. **確認とレビュー:** 取り込んだ後、feature worktree で関連テストと静的チェックを実行し、SDD の Task のレビューを行う。指摘の修正も同じ担当に新しい依頼として出す（新しい `RUN_DIR`。`revision` は取り込んだ後の HEAD）
5. **依頼ごとの記録と後片付け:** 依頼し直し（`retry`・`rejected`）も指摘の修正も、それぞれ 1 つの依頼として数える。1 つの依頼の `verdict` を処理し終えるたびに、その依頼の `RUN_DIR` について次の順に行う。依頼し直すときも、前の依頼の `RUN_DIR` を片付けてから新しい依頼を出す（Task の最後にまとめると、止まる経路で前の依頼の runner の worktree の登録が残る）
   1. SDD の ledger に、Task 名と何回目の依頼か、`requested_agent`・`actual_agent`・`identity`（runner が観測したモデル）、`elapsed_seconds`、`verdict`（`accept` を実行したらその結果も）を書く。`cleanup` は `RUN_DIR`（`task.json` とログを含む）を消すので、先に書く
   2. `implement_task.py cleanup --run-dir "$RUN_DIR"` を実行する。時点は、`importable` は `accept` の後（取り込めなかった場合も）、`no_changes`・`retry`・`rejected` は ledger に書いた直後、止まるとき（`failed`、上限に達した `retry`・`rejected`）は停止の報告の前。停止を確認した試行の worktree の登録を外し（force しない）、何も残らなければ `RUN_DIR` を消す
   3. 終了コード 1 は、残したもの（`retained`。停止を確認できない試行、`sensitive_paths` のある試行など）があることを示す。それだけでは止まらない。完全パスを ledger に書き、最終報告（止まるときは停止の報告）に含める。force・`rm -rf` で消さない

   `run` が終了コード 2（`status: error`）で終わったときは `task.json` が無く、`cleanup` を使えない。`RUN_DIR` が存在すれば、その完全パスを停止の報告に書く。`reason` が `checkout_audit` なら、`checkout_audit` に並んだ登録（消えた worktree など）を報告して止まる。他の作業の領域でありうるので、自分で prune・削除しない。セッションディレクトリは、すべての依頼の `cleanup` の後に空になったときだけ `rmdir` で消す。中身が残っていれば消さずに完全パスを報告する（`rm -rf` で消すと runner の worktree の登録だけが残り、runner を使う入口が起動の前の監査で止まる）

失敗を理由に、このセッションが `self` で実装を引き取らない（`tools/agent_runner/interfaces.rst` の「失敗を理由に別モデルへ暗黙に切り替えない」と同じ）。止まった Task の後の Task・最後の全体レビュー・PR には進まない。担当を変えるかは利用者が決める。すべての Task を取り込めたときの最後の全体レビューと PR は、`self` のときと同じ。PR 本文には、5 章の項目に加えて、割り当て（雛形・個人設定・`--implement` のどれで決まったか）、runner が観測した agent・モデル、Task ごとの依頼の回数と所要時間を書く。

## 5. 検証・PR・完了

- **`verification-before-completion` と `finishing-a-development-branch` 必須。** 終了方法は PR の作成を選び、改めて選択肢を尋ねない。検証は 2 章の表の入口で行う。長時間の検証・子・CI は `monitoring-long-tasks` 必須で、終了を待ち、終了コードと実ログを確かめる。
- `--merge` のときは、最後の commit の後に検証し、検証した HEAD、そのときの `git status --porcelain` が空だったこと、各コマンドの argv と終了コード、ログの完全パスを `PARENT_ROOT/tmp/agents/` のセッションディレクトリに記録する。同じ場所に、`finalize.py` の `--checks-file` の形（`{"head": "<HEAD>", "commands": [{"argv": [...], "exit_code": 0}]}`。この 2 項目だけ）のファイルも作る。ループで再利用する条件になる（下の「`--merge` のとき: PR の作成後のループ」の 5）
- 統合確認では [要件・原因・検証の対応](../review-fix-planning/references/convergence.md) の「3. 検証と閉じ方」を読む。Spec→Plan→Task→実行証拠を条件単位で照合し、判定の両側・意味のある操作順・検証の独立した根拠・最後の修正で影響した経路を確認する。要件の欠落や未確認をテスト件数や別版のレビューで埋めず、必要な証拠が揃ってから公開する。
- worktree で明示したパスだけを stage・commit する。push は `finishing-a-development-branch` の `git push -u` ではなく、`AGENTS.md` の「push の前の秘密情報の検査」の形で、次の順に行う。検査のスクリプトは、どの対象でも `PARENT_ROOT` のものを使う（外部の checkout には無く、作業中の branch のものはその branch が書き換えられる）。

  ```bash
  SCAN="$PARENT_ROOT/scripts/scan-before-push.sh"
  CODE_SHA="$(bash "$SCAN" -C <コードの worktree>)" && [ -n "$CODE_SHA" ] \
    && DOC_SHA="$(bash "$SCAN" -C <文書の worktree>)" && [ -n "$DOC_SHA" ] \
    && git -C <文書の worktree> push origin "${DOC_SHA:?}:refs/heads/docs/<名前>" \
    && git -C <コードの worktree> push origin "${CODE_SHA:?}:refs/heads/<branch>"
  ```

  どれかを push する前に、公開する worktree をすべて検査する。`TARGET_REPO` が create-reso-world なら、文書の worktree はコードの worktree と同じなので、`DOC_SHA` の 2 行を除く。SHA が空だと refspec が branch の削除になるので、呼び出しを分けるときも `:?` を外さない。検査の後に commit を足したら、検査からやり直す。CI の修正などの再 push も同じ形で行う。
- push の後に `gh pr create --repo "$TARGET_REPO" --base main --head <branch>` で PR を作る。SHA を指定した push では upstream が設定されないので、`--head` を省かない。既存の PR が見つかったら重複して作らない。`--merge` のときは draft にしない（`finalize.py` は draft を拒否する）。
- PR 本文: Issue が `TARGET_REPO` にあれば `Closes #N`、別のリポジトリにあれば `Refs <Issue の URL>`（マージで別のリポジトリの Issue を閉じない）。変更概要、**Spec の決定と理由、実行方式と理由**、実行した検証と結果、作業時間と主要 Task 別の内訳を書く。未実行の確認を成功と書かない。
- `TARGET_REPO` が create-reso-world でなければ、続けて、上で push した文書用の branch から create-reso-world に Spec・Plan だけの PR を作る。本文は `Refs <Issue の URL>` とコードの PR の URL。コードの PR の本文にも文書の PR の URL を足す。
- CI は 2 章の表のとおり。public のリポジトリは PR の checks が green になってから完了とする。失敗したら直すか、直せなければ止まる。`--merge` のときは、PR の作成後に CI を待たずにループへ進む（マージの前に `finalize.py` が CI の成功を確かめ、実行中なら `wait_for: ci` で待つ。PR の変更による失敗は、review-fix-planning が致命的な指摘として直す）。
- `--merge` のときのループの `finalize.py` によるマージを除き、マージ・タグ・リリース・デプロイ・プロビジョニングは行わない。admin マージ・auto-merge・force push・branch の削除は、どの場合もしない。
- ボードの子の成果の公開・予約の解放は `planning-parallel-issues` に従う。自分の所有物だけを扱う。`--merge` のときは、PR の作成の直後には解放しない。ループの `finish` の後（ループのエラーで `finish` まで進めないときは、止まった時点）に、結果と再開の方法を子 Issue に書いてから解放する。
- 完了したら Herdr のタスクを completed にし、PR の URL、検証結果、worktree・branch、実在する Spec・Plan・残したログの絶対パス、所要時間を報告する。`--merge` が無ければ、レビューは `/pr-review <PR の URL>` で行えることを 1 行で伝える。尋ねて止まらない。`--merge` のときは、この 1 行の代わりに、下の節の 6 の報告を加える。

### `--merge` のとき: PR の作成後のループ

PR を作った後（`TARGET_REPO` が create-reso-world でなければ、文書の PR も作った後）、このセッションが司令塔としてループを回す。

1. `HERDR_ENV=1` なら、Herdr のタスクを `herdr-agent-task set "PR #<PR の番号> レビュー・マージ"` に変える。ペインの名前は `start` が `PR#<番号>` に変えるので、自分で変えない
2. `PARENT_ROOT` の `.agents/skills/pr-review-fix-loop/SKILL.md` をファイルとして読む（`disable-model-invocation: true` なので、Skill ツールでは起動できない）
3. `PARENT_ROOT` の `loop.py` で `start` を実行する。feature worktree の `loop.py` は使わない（`loop.py` は置き場所からスキルと helper を決めるので、PR で変えているものでレビューさせない）。`<PR の URL>` はコードの PR。文書の PR はループに乗せず、マージもしない（URL と状態を報告する）

   ```bash
   uv run --project "$PARENT_ROOT" --locked python \
     "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" start "<PR の URL>" \
     --controller-model "<あなたの正確なモデル ID>" --controller-runtime "<ランタイム>" \
     <loop_args の各要素>
   ```

4. サイクルは、pr-review-fix-loop の SKILL.md の「サイクル」「終わり方」「止まったとき」「監視」に従う
5. **検証の記録の再利用:** 1 サイクル目で修正不要となり、サイクルの HEAD が上で記録した HEAD と同じなら、その記録を review-fix-planning の結論 2 の手順 1 の検証の記録（`finalize.py` の `--checks-file`）に使ってよい。条件は、同じ HEAD、検証のときに未 commit の変更が無い、すべての終了コードが 0、ログが残っていること。どれかを確かめられなければ、計画の中で検証し直す。base が進んでいたときの merge の検証（結論 2 の手順 2）は省かない
6. **終了:** ループの結果で次のように報告する。run ID、`<review_dir>/loop/<run_id>/` の完全パス、サイクルごとの結果、ループの段階の所要時間も書く

   | ループの結果 | 報告 | マージ |
   | --- | --- | --- |
   | `no_fix_needed` | 完了。関連 Issue は、finalize の結果に含まれる、更新後に観測した state を書く | した |
   | `fixes_pushed`（`ended_by: cycle_limit`） | 未完了。修正は push 済みで、サイクルの上限に達した。続けるなら `/pr-review-fix-loop <PR の URL>` | していない |
   | `stopped` | 停止。`stop_reason` を書く。`merged: true` なら、マージ済みであることを分けて書く | 結果のとおり |
   | ループのエラー（`lock_held`、全レビュアーの失敗、資源の停止を確認できない など） | 停止。ループの `stage`・`reason`・`next` と、残した資源の完全パスを書く | していない |

## 停止時の報告

不正な入力（helper・`check-options`・`implement_task.py check` の終了コード 2）、`--merge` で `TARGET_REPO` が usaturn/resoloop-meshy、Task の依頼の `failed`、再試行の上限に達した `retry`・`rejected`、対象・remote の確認の失敗、競合、未完了の依存、Issue の明示の承認要求、`main` 以外の向き先の指定、禁止・取り消せない操作、想定外の外部送信、必要なツール・API の失敗、解消できない検証の失敗、push の前の検査の検出・失敗（gitleaks が無い・版が違うを含む）、ループの停止・エラーでは止まる。停止条件は「途中で止めずに」の例外であり、省略・成功扱い・別のリポジトリへの切り替えで回避しない。

検査で止まったら、どの worktree も push せず、PR を作らない。誤検出に見えても `AGENTS.md` のとおり回避しない。gitleaks は自分で導入せず、`bash "$PARENT_ROOT/.devcontainer/install_gitleaks.bash"` での導入を次の操作として報告する。検査が全部通った後の push や PR の作成が失敗して一部だけ公開されたら、公開済みの branch・PR を報告し、取り消さない。

**理由 / 現在の状態 / 実施済みの検証と終了コード / 存在する worktree・branch・Spec・Plan・ログ / 次の操作** を報告する。Task を runner の担当に依頼した run では、`cleanup` が残したもの（`retained`）と、`cleanup` を使えなかった `RUN_DIR` の完全パスも書く。ループで止まったときは、ループの `stage`・`reason`・`next`・run のディレクトリ・残した資源の完全パスも書く。作っていないパスは「未作成」と書く。通常の工程の区切り、推奨案の選択、実装方式の選択は停止の理由にしない。

## ランタイムごとの違い

- **Claude Code:** `/issue-to-pr <Issue> [--implement AGENT] [--merge [ループ用のオプション]]`。スラッシュコマンドの引数（`ARGUMENTS`）から、2 章の規則で `INPUT` を切り出す。モデルが Skill ツールでこのスキルを呼ぶときは `--merge` を付けない。pr-review-fix-loop は Skill ツールで起動せず、5 章のとおりファイルとして読む。
- **Pi:** `/skill:issue-to-pr` の引数から、2 章の規則で `INPUT` を切り出す。`/sp-brainstorm` から入るときは、Issue の URL を最初に書き、`--implement`・`--merge`・ループ用のオプションはその直後に続ける（`/sp-brainstorm <Issue URL> [--implement AGENT] [--merge [ループ用のオプション]] issue-to-pr を使い、…`）。1 章の入口を案内するときも、利用者が書いた `--implement`・`--merge`・ループ用のオプションだけを含める。
- **`--controller-model`・`--controller-runtime`（5 章のループ）:** `--controller-runtime` は Claude Code なら `claude-code`、Pi なら `pi`。`--controller-model` は、現在提示されている正確なモデル ID（Pi は pi-model-name のスキルで `PI_PROVIDER` と `PI_MODEL` を確かめる。pr-review-fix-loop の「ランタイムごとの違い」）。
