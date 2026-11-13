> 移植元 usaturn/agent-workspace commit 6e71fae4d25f217b23ce2409517cf602437a3cbf の過去の評価記録。以下の環境・パス・コマンド・結果は当時の履歴であり、このリポジトリでの実行手順や今回の成功を示さない。

# issue-authoring の整形モードの行動比較と dry-run

実施日: 2026-11-09（UTC）。シナリオと方法は [reshape-scenarios.json](reshape-scenarios.json) に定義した。ここには controller が実行した fixture 評価と #869 の dry-run の観測を、再現に必要な範囲で記録する。実在の Issue の本文・ラベル・native の親子関係は変更していない。

## 方法

- ランタイムと実際のモデル: Claude Code（`claude-sonnet-5-5`）と Pi（`opencode-go/deepseek-v4.1-flash`、thinking max）。実行した argv は `reshape-scenarios.json` の `method.runtimes` に記録した。
- ガイドの commit: GREEN1 は `2637ce6f5cd8559bbcdc75ead6126b6f7969b16f`、GREEN2 は `8b137cc53ce729d4c6026fcc89b25e1ef56724db` のガイドを使った。RED はどちらもガイドを注入していない。
- 比較: 同じ架空の親 #9001 と子の fixture を、ガイド無し（RED）とガイドあり（GREEN）で各 1 回ずつ実行した。GREEN のガイドは `SKILL.md`、`references/reshaping.md`、`.agents/issue-format.md`、`planning-parallel-issues/references/issue-board.md` の本文をプロンプトへ直接注入した。自動スキル発見には頼っていない。
- 隔離: `eval_worker.py` が fixture と依頼を標準入力で渡した。Claude Code は `--tools ''`、Pi は `--no-tools` などで道具を無効にした。`GH_` と `GITHUB_` で始まる環境変数を除き、`GH_CONFIG_DIR` を空のディレクトリにした。評価の cwd はログ用のディレクトリで、実在の Issue は使っていない。
- 出力: `actions`（実行済みではなく計画）、`proposed_body`、`child_body`、`explanation` を持つ JSON 1 個。回答の中の「実行した」「保存した」という表現は、道具が無効なので実行結果として扱わない。
- 実行時間: task_watch の `watch-*/final.json` の `elapsed_seconds`。deadline は 600 秒、停止は TERM、猶予は 30 秒。時間にはプロセスの起動と終了も含む。
- 採点: `extract_results.py` が最後の assistant 出力を読み、候補本文を `reshape_issue.py` の `verify_body` に通した。そのうえで、仕様の合格条件である狭い 3 条件（承認前の書き込みが計画に無い、管理対象と子の先頭マーカーが一致、archive がある）を人が確認した。`verify_body().ok` は archive の中身の一致も含むため、狭い 3 条件の合格とは分けて扱った。
- archive のバイト比較: `manual-archive-observation.json` が、提案された archive の中身を fixture の本文と比較した。端末の LF の有無まで見た。

## 結果

| 実行 | ガイド | 時間 | exit | 道具の呼び出し | 承認前の書き込みの計画 | 管理対象・子マーカー | archive | 狭い 3 条件 | 状態 |
|---|---|---:|---:|---:|---|---|---|---|---|
| Claude RED | 無し | 40.723 秒 | 0 | 0 | 無し | 不一致（管理対象の CRLF を LF に変換） | 無し | 不合格 | 完了 |
| Pi RED | 無し | 186.220 秒 | 0 | 0 | 無し | 一致 | 無し | 不合格 | 完了 |
| Claude GREEN1（`2637ce6`） | あり | 151.787 秒 | 0 | 0 | 無し | 一致 | あり | 合格 | 完了 |
| Pi GREEN1（`2637ce6`） | あり | 417.226 秒 | 0 | 0 | 無し | 一致 | あり | 合格 | 完了 |
| Claude GREEN2（`8b137cc`） | あり | 169.063 秒 | 0 | 0 | 無し | 一致 | あり | 合格 | 完了 |
| Pi GREEN2（`8b137cc`） | あり | 600.535 秒 | 143（TERM） | 不明 | 不明 | 不明 | 不明 | 不明 | 未完了 |

RED の Claude は、元本文の管理対象に含まれる CRLF を LF に変換したため `managed_ranges_match=false` になった。RED の Pi は管理対象を保ったが、親にも子にも archive を作らなかった。どちらの RED も、行動計画としては承認前の書き込みを実行しないとしていた。したがって、今回の比較では「承認前の書き込みを計画しない」だけでは RED と GREEN を区別できず、archive の有無と管理対象のバイト保持が主な差になった。

GREEN1 の 2 回は、狭い 3 条件を満たした。ただし、archive の中身をバイト比較すると、親子とも端末の LF が 1 文字欠けていた（親 382→381、子 111→110）。`verify_body` の `archive_matches` は false で、`ok` も false である。これは「archive がある」の合格と「archive 全体が元本文と一致する」の不合格が同居した状態であり、完全なバイト保存ができたとは扱わない。

GREEN2 の Claude も、同じ狭い 3 条件を満たしたが、archive の端末 LF の欠落も同じで、`verify_body().ok` は false だった。GREEN2 の Pi は 600.535 秒で deadline に達し、watcher が TERM を送って停止を確認した。exit は 143 で、残存 PID は無く、`result.json` と最終回答は無い。判定不能であり、合格にも失敗にも数えない。

### GREEN のガイド修正後の扱い

Task2 のガイド修正後に、同じ fixture で GREEN2 を 1 回だけ取り直した。GREEN1 が狭い 3 条件を満たした後にガイドを修正して再評価したため、この GREEN2 は `reshape-scenarios.json` の `method.retake` が定める「合格条件を満たした後にガイドを修正して同じ fixture を再評価する場合」の取り直しに当たる。使ったガイドは `8b137cc` である。controller の裁定では、`2637ce6` の両ランタイムの比較を、変更していない 3 つの行動の節の証拠として残す。`8b137cc` の 2 つのガイド修正は、保存結果のキーの説明と、管理対象が無い本文でも独立した開始指示を確認する点だけを変え、静的レビューで確認した。current HEAD で Pi の完全な比較は取れていないため、両ランタイムの current HEAD 合格とは主張しない。3 回目の評価はせず、失敗・不明の結果を残す。

## #869 の dry-run

`usaturn/agent-workspace#869` の最新 snapshot を読み取り、`prepare` → `build` → `publish_issue.py draft update` → `verify` の順に実行した。`publish` は実行していない。snapshot と成果物は `/workspaces/agent-workspace/tmp/agents/issue-874-dry-run.dc3ict9j/` に残した。以下の `EVIDENCE` はこのディレクトリを指す。

```bash
EVIDENCE=/workspaces/agent-workspace/tmp/agents/issue-874-dry-run.dc3ict9j

uv run --project tools/devenv --no-sync python .agents/skills/issue-authoring/scripts/reshape_issue.py prepare \
  --repo usaturn/agent-workspace --issue 869 \
  --read-json "$EVIDENCE/issue-869.json" --out-dir "$EVIDENCE/prepare-869"

uv run --project tools/devenv --no-sync python .agents/skills/issue-authoring/scripts/reshape_issue.py build \
  --repo usaturn/agent-workspace --issue 869 \
  --read-json "$EVIDENCE/issue-869.json" \
  --segments-file "$EVIDENCE/segments-869.json" --out-dir "$EVIDENCE/build-869"

uv run --project tools/devenv --no-sync python .agents/skills/issue-authoring/scripts/publish_issue.py draft update \
  --repo usaturn/agent-workspace --issue 869 \
  --read-json "$EVIDENCE/issue-869.json" \
  --body-file "$EVIDENCE/build-869/body.md" \
  --metadata-file "$EVIDENCE/metadata-869.json" \
  --remove-label enhancement \
  --add-label "type: feature" --add-label "area: issue-workflow" \
  --add-label "priority: P2" --add-label "size: XL" --add-label "source: planned" \
  --out-dir "$EVIDENCE/draft-869"

uv run --project tools/devenv --no-sync python .agents/skills/issue-authoring/scripts/reshape_issue.py verify \
  --repo usaturn/agent-workspace --issue 869 \
  --read-json "$EVIDENCE/issue-869.json" \
  --draft "$EVIDENCE/draft-869" --out-dir "$EVIDENCE/verify-869"
```

| 段階 | exit | status | 主な出力 |
|---|---:|---|---|
| prepare #869 | 0 | `prepared` | `managed_count=1`、`segment_count=2`、本文 29,723 文字、残り 35,813 文字、archive 無し |
| build #869 | 0 | `built` | 本文 59,583 文字、残り 5,953 文字、`archive_added=true`、`archive_reused=false`、`preservation.ok=true` |
| draft update #869 | 0 | `draft_saved` | `sha256=a2915cbb1e03f6aed3e5d2f4c10dc8eaec0f43fc8c4ff34c37e0fca4e6e5c0a6`、警告なし |
| verify #869 | 0 | `verified` | `draft_sha256` が draft の SHA と一致、`expected_body_sha256` と `snapshot_body_sha256` が一致（`30b224f8e2ab1c22ff20abdf372129a0e4abec633d5b0c3048a678031ec01c45`）、`preservation_report.ok=true`、metadata あり |
| publish | 未実行 | — | `result.json` の `publication` は `not attempted` |

verify の保存検査は、管理対象 1 件の数・順序・バイト列、子の先頭マーカー、archive の存在・内容・包みの一致、metadata の存在がすべて true だった。最終 draft の本文は 62,183 文字で、上限内に収まった。承認対象にできる SHA は `a2915cbb1e03f6aed3e5d2f4c10dc8eaec0f43fc8c4ff34c37e0fca4e6e5c0a6` であり、draft の SHA と verify の `draft_sha256` が一致した。

成果物:

- snapshot: `EVIDENCE/issue-869.json`
- build 本文: `EVIDENCE/build-869/body.md`
- build 差分: `EVIDENCE/build-869/diff.patch`
- draft: `EVIDENCE/draft-869/draft.json`
- preview: `EVIDENCE/draft-869/preview.md`
- verify 本文: `EVIDENCE/verify-869/body.md`
- verify 差分: `EVIDENCE/verify-869/diff.patch`
- 保存検査: `EVIDENCE/verify-869/preservation.json`
- 実行記録: `EVIDENCE/steps.json`、`EVIDENCE/result.json`

### 上限とその他の入力

- #779 は `prepare` が exit 0 の `prepared`（本文 36,392 文字、管理対象 1 件）になった。`build` は exit 1 の `too_large` で、`original_length=36392`、`managed_length=36392`、`assembled_length=72898`、`limit=65536`、`remaining=-7362` を示して停止した。元本文と管理対象を削らずに長さと残量を示したので、この入力では期待どおりである。
- #220 と #780 は snapshot の読み取りと `prepare` だけを実行した。#220 は `prepared`（本文 9,813 文字、管理対象 0 件）、#780 は `prepared`（本文 3,040 文字、管理対象 1 件）で、どちらも exit 0。build と draft は作っていない。
- #869 の publish は実行していない。state、native の親子関係、依存関係も変えていない。

## CLI の順序と停止条件

- 順序は `prepare` → `build` → `publish_issue.py draft update` → `verify`。`draft update` は GitHub を読むだけで、`verify` が通るまで承認を求めない。`publish` は verify の SHA と一致する案を見せ、利用者の承認を得た後だけ実行する。非対話の実行は draft までで終える。
- `prepare` は snapshot の repo・番号・URL の不一致、PR、未登録 repo、管理範囲の対応の破損、未知の `planning-parallel-issues` の行、archive や metadata の破損、管理対象と archive・metadata の重なりで非 0 になる。出力先が空でない場合も拒否する。
- `build` は管理対象・先頭マーカー・archive の保存検査に失敗した場合と、`too_large` の場合に非 0 で止まる。`too_large` は元本文長・管理対象長・組立後長・上限・残量を出す。`preservation_failed` でも元本文・管理対象・archive を書き換えない。
- `draft update` は `check_failed`、`conflict`、`secret_detected`、`too_large`、`unknown_label`、`not_an_issue`、`scan_failed` で止まる。`secret_detected` が archive の中なら archive を消さず、位置と理由を報告して止まる。`conflict` は最新 snapshot から `prepare` をやり直す。
- `verify` は `draft_sha256` を出力する。`draft update` の `sha256` との一致は、承認前にエージェントが `references/reshaping.md` の 6 に従って確認する。`expected_body_sha256` と `snapshot_body_sha256` の不一致、`preservation_report.ok=false` では止まる。`too_large` と `preservation_failed` では元本文・管理対象・archive を削らない。

## 受け入れ基準とこの記録の関係

1. **snapshot と境界の扱い**: Task1 の helper と代表テスト、#220/#780/#869/#779 の `prepare` で確認した。PR・未登録・不明な境界の拒否はこの Task で新しい実入力を作っていない。
2. **管理範囲の保持**: Task1 の代表テストと #869 dry-run の `preservation.ok=true` で確認した。fixture 評価では GREEN1 の両ランタイムと GREEN2 の Claude が管理対象と子の先頭マーカーを保った。
3. **archive と metadata**: Task1 の代表テストと #869 の `archive_added=true`、`archive_matches=true` で確認した。fixture 評価は archive の存在だけを狭い合格条件にし、手動のバイト比較では端末 LF の欠落を確認した。既存 archive の再利用はこの dry-run では発生していない。
4. **SHA と差分**: #869 で draft の SHA と verify の `draft_sha256` が一致し、`expected_body_sha256` と `snapshot_body_sha256` が一致した。archive を除いた差分は `verify-869/diff.patch` に保存した。
5. **ラベル・タイトル・secret・conflict・非対話**: ラベルの差分は #869 の draft に渡した。タイトル、secret_detected、conflict の実入力はこの Task では起こしていない。非対話の publish 拒否もこの Task では新たに試しておらず、dry-run は publish を実行していないだけである。
6. **上限と #869**: #779 の `too_large` と #869 の build→draft update→verify 成功を上に記録した。
7. **行動比較**: 上記のとおり。出力だけの比較で、実 CLI の書き込み拒否や自動スキル発見は確かめていない。
8. **完了コメントと正式な検証**: この記録は完了コメントに載せる CLI・status・停止条件・成果物パスを用意する。完了コメントの投稿と正式な `verify-devenv.sh` は controller の後続作業で、この Task では実行していない。

## 証拠

fixture 評価のルートは `/workspaces/agent-workspace/tmp/agents/issue-874-eval.04xtzzsf/`。

- `eval_worker.py`: プロンプト、argv、隔離、実行方法
- `fixture.json`: 親と子の fixture
- `*.argv.json`、`*.result.json`: 実行した argv と exit
- `watch-*/final.json`: 実行時間、deadline、停止
- `*.response.txt`、`*.assessment.json`: 最後の回答と採点
- `assessments-final.json`: 6 件の評価（Pi GREEN2 は未完了）
- `manual-archive-observation.json`: archive の端末 LF の比較

#869 dry-run のルートは `/workspaces/agent-workspace/tmp/agents/issue-874-dry-run.dc3ict9j/`。主なファイルは上の「成果物」に列挙した。

## 限界

- 評価は道具を無効にした print モードの出力比較であり、モデルは helper も gh も実行していない。回答が「実行した」と書いていても実行結果ではない。実 CLI の書き込み拒否、自動スキル発見、対話の承認後に publish する流れは確かめていない。
- GREEN1 は `2637ce6`、GREEN2 は `8b137cc` のガイドで実行した。両ランタイムの完全な比較が取れているのは GREEN1 だけである。GREEN2 の Pi は deadline で停止して結果が無く、判定不能のまま残した。3 回目は実行していない。
- 各 variant は 1 回、モデルも 1 つずつである。ばらつきや他のモデルの挙動は分からない。時間は task_watch の実時間で、モデル API の処理時間だけではない。
- fixture 評価の archive は、モデルが手で組み立てた提案を採点したものである。端末 LF が欠けたため、完全なバイト保存の証拠にはならない。helper の実装がバイトを保つことは Task1 の代表テストと #869 dry-run で確認し、管理範囲を隠す候補を拒否することも Task1 の代表テストで確認した。ただし、それをモデルの出力の正しさに読み替えない。
- dry-run は 2026-11-09 に取得した #869 の snapshot を使う。再実行するときは snapshot が古くなっていないか確認し、変わっていれば `prepare` からやり直す。実投稿はしていない。
- 隔離は環境変数、空の `GH_CONFIG_DIR`、道具の無効化によるもので、OS の sandbox ではない。もっとも、評価中に道具の呼び出しは 0 件だった。
- 新しいテストは追加していない。この記録の値はテストで固定せず、JSON の解析、既存のスキル構造チェック、既存の整形テスト、ruff、Pyright で確認する。
