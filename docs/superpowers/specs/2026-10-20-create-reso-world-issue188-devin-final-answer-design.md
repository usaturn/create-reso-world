# Issue #188: devin adapter が、ツールを使った実行の成功を response_failed にしないようにする

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/188（親・ボードなし。関連 #116・#150・#156・#158）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue188-devin-final-answer.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-188-devin-tool-run-stdout`（branch `fix/issue-188-devin-tool-run-stdout`、`origin/main` の `8f5074a` から作成）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #188` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #188`）まで行う。マージはしない
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- Plan の実装の担当: `implement_task.py check` の結果は `agents = ["self"]`・`fallback = []`。個人設定 `~/.config/agent-runner/config.toml` の `[workflows.issue.assignments.implement]` が雛形と同じ `self` を持つ（利用者の `--implement` の指定は無い）

## 意図

devin の担当がツールを使って成功した実行（実際のレビューはすべて当てはまる）を、runner が `response_failed` と記録しないようにする。既定のレビュアー `devin-swe` の結果が毎回失敗になると、#156（レビュー修正ループ）・#158（`--merge`）が runner の結果でレビュアーの成否を数えたときに、devin のレビューを除外・再試行・失敗の報告の対象にしてしまう。

「途中で切れた stdout や、壊れた最後の発話を成功にしない」という今の `collect` の意図（`tools/agent_runner/adapters/devin.py` の 234–235 行のコメント）は保つ。

## 確認した事実（2026-10-20）

- `collect` は、結果が JSON の役割で、export（ATIF）の最後の発話と stdout 全体の両方が `_json_object` で 1 つの JSON として読めることを求める。`_json_object` は先頭から読み、先頭の fence だけを許す
- ローカルに残る実際の 2 件（devin 3000.11.92、model `SWE-2 Max`）を読んだ
  - #186: `tmp/agents/issue-155.8zy2dh0_/loop/cycle1/runner/4c8509e10b9f42d2a9261ab934ca53fe/attempt-1/`。export は 52 step、最後の step は `source: agent`・`tool_calls: []`、本文は fence 付きの JSON
  - #185: `tmp/agents/issue-157.e6surmvx/review/cycle-1/runner/6d5531268ba24ba58823abd9e3555fc8/attempt-1/`。export は 40 step、最後の step は同じ形
  - どちらも、stdout は export の空でない agent の発話（#186 は 23 件、#185 は 15 件）をすべて順に、区切りなしで含む（#186 の stdout の先頭 2623 文字は、export の agent の発話の欄に無い発話）。最後の発話は直前の発話に続けて同じ行から始まり、stdout は「最後の発話 + 改行 1 つ」で終わる
  - どちらも、stdout と最後の発話に診断行（`_DIAGNOSTIC_LINE`）は無く、export に error の step も無い。今の `collect` は stdout 全体を `_json_object` で読めずに `response_failed` を返す
- runner は stdout を `execute` で秘匿値を除きながら書き、`export.json` を `collect` の前に同じ値で除く（`tools/agent_runner/runner.py` の 466–502 行）
- 雛形 `.devcontainer/agent-runner.toml` の役割（inspect・implement・self-review・fix-check）は、すべて `result_shape = "json"`
- `tools/agent_runner/runtimes/devin.rst` は「返す payload は標準出力から取り出す」「現在の CLI による実機検証は未実施」と書いている。`tools/agent_runner/interfaces.rst` は devin の stdout の形を書いていない
- pr-review の `SKILL.md` と `references/noninteractive.md` は、devin の stdout に途中の発話が連結されることを前提に、最終の JSON を 1 つの fence に入れるよう指示し、「既存の Devin adapter がこの形式を object として回収する」と書く。今はこの前提が成り立っていない
- 偽の CLI（`tools/agent_runner/tests/adapters/devin/fake_cli.py`）は `--fake-stdout` のファイルをそのまま書くので、実際の形の stdout も変えずに再現できる

## 設計

`collect` の成功の判定を次のようにする。診断の優先（stderr、stdout と最後の発話の診断行、export の error の step）と、最後の step の検査（`_final_agent_message`）は変えない。

1. export の最後の発話（`_final_agent_message` の値）を回答とする
2. stdout がその回答で終わることを確かめる。回答の前後の空白を除いた文字列が stdout に最後に現れる位置を探し、その後ろが次の条件をすべて満たすときだけ「終わる」とする
   - 回答の最後の行の残り（次の改行まで）が空白だけ
   - 続く行が、今の `_json_object` の後ろの行の規則を満たす: `{`・`[`・```` ``` ```` で始まる行が無く、認証・承認の語（`_failure_status`）が無い
3. 終わるときは、回答を役割の形で読む。JSON の役割は `_json_object(回答)` の object、text の役割は回答の文字列を payload にする。読めなければ `response_failed`
4. 終わらないとき（stdout が空、回答が stdout に無い、回答の後ろが条件に合わない）は、今の失敗の経路（`_failure_status(stdout) or "response_failed"`）にする

後ろの行の規則は、`_json_object` と 2 の判定で同じものを使う（1 つの関数にまとめる）。adapter の docstring と `runtimes/devin.rst` を、この規則に合わせて直す。

## 受け入れ条件

| # | 条件 | 確かめ方 |
| --- | --- | --- |
| C1 | 途中の発話の後に、区切りなしで fence 付きの JSON が続き、改行で終わる stdout と、途中の step が tool を呼び、同じ JSON を最後の発話に持つ export で、`success` と payload（object）が得られる | 偽の CLI の出力を使う単体のテストと、runner を通すテスト |
| C2 | 最後の発話が途中で切れている（JSON が閉じていない）とき、stdout も同じ文字列で終わっていても `success` にしない | 単体のテスト |
| C3 | stdout が最後の発話で終わらないとき（stdout が回答の途中で切れている、回答の後ろに別の JSON の行が続く、回答と同じ行に別の文字が続く）は `success` にしない | 単体のテスト（異常を 1 つずつ入れる） |
| C4 | export の最後の step が tool を呼んでいるとき、stdout が同じ回答で終わっていても `success` にしない | 単体のテスト |
| C5 | 今の負例（診断の優先、export の error、空の stdout、export の欠落・破損、空の最後の発話、後ろの壊れた JSON・診断）を保つ。JSON の後ろの通常の進捗行は今のまま許す | 既存のテストを、検査の目的を変えずに新しい規則の入力へ揃えて通す |
| C6 | `uv run pytest tests/skills .agents/skills .agents/scripts tools` と README の「テスト」の入口が通る | 実行して終了コードを見る |
| C7 | 実際の 2 件（#185・#186）の stdout・export に新しい `collect` を当てると `success` で、payload が最後の発話の JSON と一致する | ローカルのファイルを読むだけの一回の確認（テストに写さない） |
| C8 | adapter の docstring と `runtimes/devin.rst` の記述が新しい規則と一致する | 差分の確認と rstcheck |

## 除外範囲

- 診断行の検査の範囲は変えない（下の D-188-4）
- `prepare`（起動の argv・prompt）、他の adapter、runner、`interfaces.rst` は変えない
- pr-review の `SKILL.md`・`references/noninteractive.md` は変えない（修正後に記述が成り立つ）
- devin・他の担当を実機で起動しない。移植元（usaturn/agent-workspace）の adapter は確かめない

## 決定記録

### D-188-1 回答の取り出し元

- 選択した案: (a) export の最後の発話を回答とし、stdout はその回答で終わることだけを確かめる
- 検討した別案: (b) stdout から最後の JSON（fence）を取り出し、export の最後の発話と比べる。(c) stdout を見ず、export の最後の発話だけで判断する
- 選択理由: (b) は fence の無い回答（pr-review 以外の役割は fence を求めていない）や、JSON の文字列の中の ```` ``` ```` で取り出し位置を誤る。(c) は途中で切れた stdout、回答の後ろに別の JSON・診断が続く stdout を成功にし、今の意図を失う。(a) は Issue の推奨案で、途中の発話だけを許す
- 委任指示: issue-to-pr の推奨案での委任（Issue の推奨案と同じ）

### D-188-2 「stdout が回答で終わる」の判定

- 選択した案: 前後の空白を除いた回答が stdout に最後に現れる位置の後ろを見て、同じ行の残りが空白だけ、続く行が今の後ろの行の規則を満たすときだけ「終わる」とする
- 検討した別案: stdout の末尾の完全一致（`endswith`）。同じ行に続く文字も、後ろの行の規則だけで許す
- 選択理由: 完全一致は、今の規則で許している JSON の後ろの進捗行（`test_plain_progress_after_json_does_not_invalidate_completion`）を拒む。同じ行に続く文字を許すと、`{"ok": true}, "x": 1}` のように stdout の最後の JSON が export と違う形でも成功になる。実際の 2 件は回答の後ろが改行 1 つだけで、この判定で成功になる
- 委任指示: issue-to-pr の推奨案での委任

### D-188-3 payload の取り出し元

- 選択した案: 回答（export の最後の発話）から取り出す。JSON の役割は object、text の役割は回答の文字列
- 検討した別案: 今のまま stdout から取り出す
- 選択理由: 実際の stdout には途中の発話が並ぶので、stdout からは JSON を読めず、text の役割では payload に途中の発話が混ざる。stdout が回答で終わることを確かめるので、JSON の役割の値は stdout の末尾と同じになる。runner は stdout を秘匿値を除きながら書くので、stdout の末尾と一致する回答にも、除く前の値は残らない。text の役割の payload は「stdout 全体」から「最後の発話」に変わるが、雛形の役割はすべて JSON なので、既定の割り当てには影響しない
- 委任指示: issue-to-pr の推奨案での委任

### D-188-4 診断行の検査

- 選択した案: 今のまま（stderr、stdout 全体と最後の発話の診断行、export の error の step）
- 検討した別案: export の途中の発話と突き合わせて、stdout の途中の発話を診断の対象から外す
- 選択理由: stdout のどこが発話でどこが CLI の出力かを分ける規則が必要になり、CLI の診断を見落とす恐れがある。Issue の対応の候補 (a) も「最後の発話の検査は今のまま」としている。実際の 2 件には該当する行が無い
- 残る制限: 途中の発話に、`Error:` などで始まり認証・承認の語を含む行があると、成功の実行を `awaiting_authentication`・`awaiting_approval` にする。失敗を成功にする向きではないので、この Issue では直さない。PR 本文の既知の制限に書く（Issue にするかは利用者が決める）
- 委任指示: issue-to-pr の推奨案での委任

### D-188-5 テスト

- 選択した案: 偽の CLI は変えず、テストのファイルに実際の形の stdout と export を作る helper を足す。C1〜C4 のテストを足し、stdout と最後の発話が別の文字列だった既存のテスト（`{"ok":true}` と `{"ok": true}` の違い、stdout だけに置いた回答など）は、検査の目的を保つように両方を揃える
- 検討した別案: 偽の CLI に「途中の発話を前に足す」オプションを足す。実際のファイル（#185・#186）をテストの fixture に写す
- 選択理由: `--fake-stdout` で任意の stdout を書けるので、偽の CLI を変える必要は無い。実際のファイルはレビューの本文を含み、大きく（export は 348 KB）、ローカルの作業物なので写さない。出力の解析で、実際に起きた不具合の再発を防ぐので、テストの採用基準の「書く」に当たる
- 委任指示: issue-to-pr の推奨案での委任

### D-188-6 文書

- 選択した案: adapter の docstring と `runtimes/devin.rst`（標準出力の扱い、payload の取り出し元、3000.11.92 の実際の出力の観測）を直す。`interfaces.rst` と pr-review の文書は変えない
- 検討した別案: Issue の「必要なら」に従い `interfaces.rst` にも書く
- 選択理由: devin の stdout の形を書いているのは docstring と `runtimes/devin.rst` だけで、`interfaces.rst` は adapter 共通の仕様だけを書いている
- 委任指示: issue-to-pr の推奨案での委任

### D-188-7 実機の確認

- 選択した案: この run では devin を起動しない。ローカルに残る #185・#186 の出力に新しい `collect` を当てて確かめる（C7）。実機の `state: success` は、Issue の検証のとおり、この PR のレビューで devin が既定のレビュアーとして動いたときに確かめる
- 検討した別案: この run で devin を 1 回起動する
- 選択理由: Issue が「そのための追加の起動はしない」と決めている。AGENTS.md も、本物の担当の起動を Issue・Plan に書いた回数に限る
- 委任指示: Issue の検証の記述
