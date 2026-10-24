# Issue #239: Devin の adapter が、モデルの発言を CLI の診断とみなさないようにする Design

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/239
- 実行許可: 利用者の `/issue-to-pr #239 --merge`。設計判断は推奨案で決め、PR の作成後に PR 修正ループを回し、修正不要なら `finalize.py` がマージする。内容の承認（approved）ではない
- 入力の検査: `resolve_issue.py -- "#239 --merge"` は終了コード 0（`repo` は usaturn/create-reso-world、`loop_args` は空、`implement` は null）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-239-devin-answer-diagnostics`（branch `fix/issue-239-devin-answer-diagnostics`、基準 `origin/main` の `bdbe02b`）
- ループ・担当の設定: `loop.py check-options` は既定の適用（サイクルの上限 3、テンプレート `.devcontainer/agent-runner.toml`、レビュアーは pi-gpt・devin-swe・pi-deepseek・cursor-grok47、修正は claude-opus、自己レビューと修正の確認は self）。利用者の指定は無い。Plan の実装は `implement_task.py check` の `self`（雛形の既定の適用。利用者の指定なし）
- 前提の確認: 親 Issue・sub-issue・blocked_by は無い（ボードの子ではない）。同じ Issue の open PR・claim ref・branch・worktree は無い。#242 が本 Issue を「マージ後の確認の候補」に挙げているが、予約ではなく「状況に合わなければ選び直してよい」とある

## 目的と範囲

`devin -p` は、モデルの発言（途中の応答と最終応答）をそのまま標準出力に書く。Devin の adapter（`tools/agent_runner/adapters/devin.py`）は、その標準出力と最終 ATIF 応答の行を CLI の診断として照合しているため、レビューがコードブロックなどで `Error: invalid api key` のような行を引用すると、正しい回答で終わっていても `awaiting_authentication` にして payload を捨てる。runner の失敗はループの再実行の対象にならないので、正しいレビューが黙って失われ、利用者には要らない再ログインを促す。

この変更では、認証・承認待ちの判定を、CLI 自身が失敗を書く経路（標準エラーと export の error の step）だけで行う。標準出力と最終 ATIF 応答は、回答の取り出しと形の確認にだけ使う。

変えるもの:

- `tools/agent_runner/adapters/devin.py`: `collect` の診断の経路、回答が無いときの分類、`_plain_tail`、`_DIAGNOSTIC_LINE` の削除、docstring とコメント
- `tools/agent_runner/tests/adapters/devin/test_adapter.py`: 旧挙動を確かめる 2 つのテストの削除と、新しい挙動のテスト（D-5）
- `tools/agent_runner/runtimes/devin.rst`: 「観測する情報と完了条件」と「検証と制約」

対象外:

- 他の adapter。claude-code・codex・cursor・pi の標準出力は JSON のイベントの stream で、モデルの発言は JSON の文字列の中にだけある（PR #237 の `_EVENT_STREAM_RUNTIMES` と同じ区別）
- 標準エラーの照合の範囲（全文を `_AUTH`・`_APPROVAL` で照合する今の形）と、`_AUTH`・`_APPROVAL` の正規表現
- `_export_failure` の分類（D-4）
- loop・pr-review 側の診断（PR #237 の `1092fa0` で、Devin の標準出力を原因の判定に使わない形になっている）と、runner の状態の扱い

## 調べた事実（2026-10-25、main `bdbe02b`）

- `devin.py` の `collect`（236〜256 行）は、次の順に判定する
  1. 標準出力と最終 ATIF 応答の行のうち `_DIAGNOSTIC_LINE`（43〜47 行。行頭の `error:`・`fatal:`・`not logged in` など）に当たる行を、標準エラーと合わせて `_failure_status`（110〜118 行）に渡す。`_AUTH` に当たれば `awaiting_authentication`、`_APPROVAL` に当たれば `awaiting_approval` として、回答の確認より先に返す
  2. 次に export の error の step（`_export_failure`。`source` が `error`、`is_error` が真、`error` がある step の message と error を照合する）
  3. 最終 ATIF 応答があり、標準出力がそれで終わるなら、回答を payload にする
  4. それ以外は `_failure_status(stdout)`（標準出力の全文。行頭の制限も無い）か `response_failed`
- `_plain_tail`（59〜64 行）は、標準出力の回答の後ろの行と、最終応答の JSON の後ろの文の両方に `_failure_status` を当て、認証・承認の語があれば回答として認めない。#188 の前は標準出力を回答として解析しており、その後ろの行を CLI の出力として照合していた名残である
- 一時的な再現（`Devin.collect` に偽の出力を与えた。ログは `/workspaces/reso-world/tmp/agents/issue-239.ctc8zcjz/repro-base-bdbe02b.log`）

  | 入力 | `bdbe02b` の結果 |
  | --- | --- |
  | 途中の応答のコードブロックで `Error: invalid api key` を引用し、正しい JSON で終わる | `awaiting_authentication`、payload なし |
  | 同じ形で `Error: connection refused` を引用する、引用しない | `success` |
  | 最終応答（text）のコードブロックで `Error: invalid api key`・`fatal: not logged in` を引用する | `awaiting_authentication` |
  | 最終応答が、JSON の後ろに引用の 1 行を持つ | `awaiting_authentication` |
  | 回答が無い（最後の step が tool を呼ぶ、export が無い）、発話に「login」「authentication」がある | `awaiting_authentication` |
  | 標準エラーに実機の `Error: Login canceled`、または export の error の step に `invalid api key` | `awaiting_authentication` |

- 実機（devin 3000.11.205、認証情報の無い一時 HOME。認証が無いのでモデルは起動されない）: `devin -p --prompt-file ... --export ... --respect-workspace-trust false` は終了コード 1 で終わり、標準エラーに `Error: Login canceled`、標準出力には端末の制御列 `ESC[?2004l` だけを書き、export を作らない。今の `_AUTH` は標準エラーのこの行を `awaiting_authentication` にする
- 手元に残る実機の記録 7 件（devin 3000.11.92。#150・#153・#155・#157・PR #182 の確認）は、どれも標準エラーが空、標準出力の最終応答の後ろは改行だけ、最終応答は JSON で、診断に見える行は無い。今の adapter ではすべて `success`
- runner（`runner.py` の 384〜386 行）は、非 0 終了のとき、adapter の状態が `awaiting_authentication`・`awaiting_approval`・`interrupted` 以外なら `response_failed` にする。`awaiting_*` は非 0 終了でも残る。fallback に進むかどうかは `awaiting_*` と `response_failed` で同じ
- 雛形の役割はどれも `result_shape = "json"` で、Devin（`devin-swe`）は `inspect` のレビュアーに使われる。現実の発生経路は「途中の応答で引用し、最後に JSON で答える」形である

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-1 診断に使う経路 | 認証・承認待ちは、標準エラーと export の error の step だけで判定し、回答の確認より先に返す。標準出力と最終 ATIF 応答は、回答の取り出しと形の確認にだけ使う | (a) コードブロックの中の行を除いて照合を続ける (b) 正しい回答があるときだけ、標準出力・最終応答の診断を無視する (c) 今のまま | `devin -p` の標準出力はモデルの発言の平文で、行の形では引用と CLI の出力を区別できない（PR #237 のサイクル 2 で loop が Devin の標準出力を使わなくした理由と同じ）。(a) は字下げした引用や行頭から始まる文を拾い続け、区切りなしに連結される応答ではコードブロックの開閉もずれうる。(b) は回答の無い実行の誤分類を残す（D-2）。実機の未ログインは標準エラーに出るので、受け入れ条件 2 は標準エラーと export で満たせる | Issue の「直し方の方向」と受け入れ条件。推奨案で進める |
| D-2 回答の無い実行 | 標準エラーと export に失敗が無く、回答も無い（export が無い、最後の step が tool を呼ぶ、標準出力が回答で終わらない）ときは、標準出力の内容によらず `response_failed` | 標準出力のうち `_DIAGNOSTIC_LINE` に当たる行だけで分類を残す | 回答の無い実行でも標準出力はモデルの発言で、`_AUTH` は「login」「authentication」「401」「forbidden」のようなレビューの普通の語に当たる。認証のコードをレビュー中に止まった実行が `awaiting_authentication` になり、runner は非 0 終了でもそれを残すので、要らない再ログインを促す（Issue の影響の 3 つ目）。行頭に限っても、引用した行で同じことが起きる。実機の未ログインは標準エラーで分類できる | 推奨案で進める |
| D-3 回答の後ろの行 | `_plain_tail` は、JSON のような行（先頭の空白を除いて `{`・`[`・```` ``` ```` で始まる行）だけを見て、認証・承認の語では判定しない。標準出力の回答の後ろと、最終応答の JSON の後ろの両方に当てはまる | 標準出力の回答の後ろだけ、語の確認を残す | 最終応答の JSON の後ろの文はモデルの発言で、語の確認は正しい回答を捨てる（上の表の 4 行目）。標準出力の回答の後ろは、実機の 7 件では改行だけである。CLI の失敗は標準エラーと非 0 終了で現れ、adapter が `success` を返しても runner が非 0 終了を `response_failed` にするので、語の確認をやめても CLI の失敗が成功にはならない。後ろに JSON や壊れた JSON が続く実行を認めない確認は残す | 推奨案で進める |
| D-4 export の error の step | 変えない。今までどおり、error の step の message と error を照合する | agent の step では error の欄だけを照合する | Issue は export の error の step を判定に使う経路として残している（受け入れ条件 2）。実機の error の step の例が無く、CLI が失敗の文を message と error のどちらに書くか分からない。どちらでも、その実行は失敗として扱われ、違いは失敗の種類の分類だけである | 対象外。実機の例が得られたら別の Issue で扱う |
| D-5 テスト | 旧挙動を確かめる 2 つ（`test_text_diagnostic_with_valid_export_is_not_success`・`test_final_atif_diagnostic_overrides_successful_stdout`）を消す。#239 の回帰として、途中の応答と最終応答の JSON の後ろで `Error: invalid api key` を引用した出力が、回答があれば `success`（payload あり）、回答が無ければ `response_failed` になるテストを 1 つ（2 ケース）足す。export の error の step の認証の失敗が、正しい回答より優先して `awaiting_authentication` になるテストを 1 つ足す。標準エラーの `test_diagnostics_override_plausible_success` は残す | 経路（標準出力・最終応答・JSON の後ろ・回答の無い実行）ごとに別のテストにする。実機の `Error: Login canceled` を固定値で確かめる | 壊れても例外にならず、正しいレビューが runner の失敗として捨てられ、認証待ちと報告される（採用基準の S。誤っているがもっともらしい結果）。1 つの出力に引用を 2 か所置くと、標準出力・最終応答・JSON の後ろの語の確認のどれを戻しても `success` のケースが失敗し、回答の無い実行の分類を戻すと `response_failed` のケースが失敗するので、経路ごとのテストは重複（D）になる。export の error の step を正しい回答より優先する確認は、今のテスト（`test_export_error_fields_override_answer`）では、標準出力が回答で終わらないために、確認を外しても失敗しない。受け入れ条件 2 が名指しする経路なので、ここで 1 件足す（S。失敗を成功と報告する）。消す 2 つは、どちらも #239 が取りやめる挙動を確かめており、残る守り（回答で終わらない標準出力は失敗）は `test_tool_run_stdout_not_ending_with_final_answer_fails` が確かめる | 採用基準。迷う項目は書かない |
| D-6 文書 | `devin.rst` の「観測する情報と完了条件」を新しい判定に書き換え、既知の制限の 2 文を消す。「検証と制約」に、3000.11.205 の未ログインの観測を書く | `interfaces.rst` も書き換える | `interfaces.rst` の「明示的な認証/承認待ちの診断を優先する」は、どの経路を診断とするかを adapter に任せており、そのままで新しい挙動と矛盾しない | 推奨案で進める |
| D-7 実機の確認 | 調査での 1 回（認証情報の無い一時 HOME。モデルは起動されない）だけ。修正後は、手元の実機の記録 7 件を `collect` に通し、すべて `success` で payload が変わらないことを確かめる | 実際のモデルでレビューを起動し、引用の行を含む回答を確かめる | 実際の担当の起動は費用がかかり、AGENTS.md は Issue・Plan に書いた回数に限る。引用を含む出力の形は、記録の形（区切りなしの連結、改行だけの後ろ）と偽の出力で再現できる | 追加の起動はしない |
| D-8 この PR のループ | ループは親の checkout（main）の runner を使うので、devin-swe がこの PR の差分の `Error: invalid api key` を引用すると、main の adapter がそのレビューを `awaiting_authentication` で捨てうる。起きたら、この不具合の実際の発生として記録し、PR と Issue に書く | ループのレビュアーから devin-swe を外す | 利用者の `--merge` はループの既定の構成で回す指示で、レビュアーの構成を変える指定は無い。Issue は実際の run での発生を未観測としており、起きればその観測になる | ループの手順（pr-review-fix-loop）に従う。1 人の却下だけでは止めない |

## 変更後の `collect`

1. 標準エラーを `_failure_status` で照合し、当たればその状態（`awaiting_authentication`・`awaiting_approval`）で、payload なし
2. 当たらなければ、export の error の step（`_export_failure`）。当たればその状態で、payload なし
3. 最終 ATIF 応答があり、標準出力がその回答で終わる（`_ends_with`）なら、`_payload` の結果（JSON 形式の役割では空でない JSON object、text では空でない文字列）
4. それ以外は `response_failed`

`_ends_with` は今のまま（回答の最後の行がそこで終わり、後ろは `_plain_tail` を満たす行だけ）。`_plain_tail(tail)` は「どの行も、先頭の空白を除いて `{`・`[`・```` ``` ```` で始まらない」だけを確かめる。`_DIAGNOSTIC_LINE` は使わなくなるので消す。

## 受け入れ基準と確かめ方

| 受け入れ基準 | 確かめ方 |
| --- | --- |
| 回答の本文（コードブロックの中を含む）に `Error: invalid api key` などの行があっても、正しい回答で終わる出力は `success` になる（Issue の受け入れ条件 1） | D-5 の回帰テストの `success` のケース。一時的な再現の 1・4・5 行目に当たる入力が、修正後に `success` で payload を持つ |
| 標準エラーや export の error の step に出た本当の認証の失敗は、今までどおり `awaiting_authentication` になる（Issue の受け入れ条件 2） | `test_diagnostics_override_plausible_success`（標準エラー）と D-5 の export のテスト。一時的な再現で、実機の標準エラー（`Error: Login canceled`）と export の error の step が修正後も `awaiting_authentication` |
| 回答の無い実行は、標準出力の語によらず `response_failed`（D-2） | D-5 の回帰テストの `response_failed` のケース。一時的な再現の「回答が無い」2 つ |
| 回答の後ろの JSON・壊れた JSON、回答で終わらない標準出力、tool を呼ぶ最後の step は、今までどおり成功にしない | 既存のテスト（`test_truncated_later_stdout_cannot_reuse_completion`・`test_tool_run_stdout_not_ending_with_final_answer_fails`・`test_tool_run_final_step_calling_tool_fails` など） |
| 実機の記録 7 件は今までどおり `success` で、payload が変わらない | 一時的な再現で、修正の前後の結果を比べる |
| 既存の検査が通る | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。補助に `uvx ruff check`（変更したファイル） |
