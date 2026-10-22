# PR #246（Issue #232）レビュー修正 サイクル 1

## 管理

- 対象: usaturn/create-reso-world PR #246（`feat/issue-232-review-helper-tests`）、Issue #232
- 状態: completed
- 結論: 1 修正して push
- 実行許可: 利用者の `/issue-to-pr #232 --merge`。issue-to-pr の `--merge` が PR 修正ループ（pr-review-fix-loop、run `e8aa86021b2943378a4031e475c98377`）を回し、その中で review-fix-planning の完遂（既定）を行った。この PR の承認済みの実装修正と、修正不要のときのマージ・関連 Issue の更新の実行許可として扱う
- サイクル: 1。reviewed_head `776a6b63e0f277782557f71faf9b337490cb5c68`
- planner: claude-opus-5-5（claude-code）
- 修正と自己レビューの担当（`run_roles.py` の割り当て。雛形 `.devcontainer/agent-runner.toml` の適用）: implement は `claude-opus`（runner が観測したモデルは claude-opus-5-5、`stop_confirmed: true`、545 秒）、self-review・fix-check は `self`
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#246-feat-issue-232-review-helper-tests/verified/776a6b63e0f2.json`
- 工程の記録: 同じディレクトリの `verified/776a6b63e0f2.planning.json`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `776a6b63e0f2` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 | cursor | `776a6b63e0f2` | はい | Needs manual verification |
| `SWE-2-Max.md` | SWE-2 Max | devin | `776a6b63e0f2` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | `776a6b63e0f2` | はい | Needs manual verification |

PR 修正ループの判定: 4 人とも 1 回目で受け付けられた（`rejected` なし）。

## 指摘の一覧と振り分け

対応する 7 / 対応しない 3 / 解消済み 1（指摘 13 件を 11 の判断にまとめた）。

| 判断 | 出典 | 区分 | 根拠 |
| --- | --- | --- | --- |
| F1 | gpt-6.1-sol#M-1 | 対応する | 空の検証の記録を拒否する唯一のテストを D として消した。残した `failed` は要素の終了コードの検査で、空の一覧では走らない。拒否が壊れると、検証していない記録でマージ・Issue の close まで進む（未検証のマージ、高） |
| F2 | gpt-6.1-sol#M-2 | 対応する | `check_pair` の位置の照合の唯一のテストを D として消した。ID・重大度の照合とは別の分岐（記録の取り違え、中） |
| F3 | SWE-2-Max#L-1/A（gpt-6.1-sol#L-1、Grok-4.7#L-1） | 対応する | 語境界のテストを「S 低/迷い」と分類しながら重さを理由に消した。#228 の決定 6 と「迷いは残す」に反する |
| F4 | Grok-4.7#M-1 | 対応する | `stopped` の `stop_reason` の区分の検査のテストを L として消したが、拒否が壊れるとエラーにならずに区分の無い停止の記録が通る（`AGENTS.md` の L のただし書きで S。記録の取り違え、中） |
| F5 | Grok-4.7#M-2 | 対応する | `fixes_pushed` の `commit` が `reviewed_head` と同じ記録の拒否の唯一のテストを、`INVALID_RECORDS` の一括の削減で消した（誤った結果の報告、中） |
| F6 | SWE-2-Max#L-1/B | 対応する | open でない PR への記録の投稿を拒否するテストを「実害が小さい」として消した。MERGED は `test_finalize.py` の例が確かめるが、CLOSED だけを通す壊し方を検出するテストが無い（確認済みの一覧 V-2）。S と分類したものを重さで消さない（決定 6） |
| R1 | Grok-4.7#L-2 | 解消済み | open の確認を外すと、残した `test_finalize.py::test_manual_merge_before_posting_keeps_the_merge[same_head]` が失敗する（確認済みの一覧 V-3、HEAD `776a6b63e0f2`）。指摘の「残ったテストに検出が無い」は再現しない |
| F7 | deepseek-deepseek-v4.1-flash#M-1 | 対応する | 停止していない記録の空の `seats` と、再実行したレビュアーがいない記録の拒否のテストを消した。壊れると、再レビューしていない記録で finalize がマージまで進む（未検証のマージ、高） |
| S1 | gpt-6.1-sol#L-2 | 対応しない | diff の設定のテストは外すとエラーで止まる（V-9）が、日本語のパスのテストは quotePath を外すとエラーにならずに誤ったパスになる（V-10）ので S。前者も残して損害は無い（書きすぎ）ので迷いとして残し、#236（integration）が L の残りを整理するときに見直す |
| S2 | Grok-4.7#I-1 | 対応しない | PR の差分の変更ではない。前後の数の Issue への記録は、issue-to-pr の完了報告で行う |
| S3 | SWE-2-Max#I-1、deepseek-deepseek-v4.1-flash#L-1 | 対応しない | Spec の Task 4・5 の節の数と注記の食い違い（文書、致命的でない）。F1〜F7 で同じ節を書き直すので、実装の担当が実測に合わせた |

## 対応する項目の修正方針と、守る条件と影響経路

共通の理由: この PR は #228 の「削除と採用の基準」で F・L・D の余りだけを消し、S（壊れてもエラーにならない損害を防ぐテスト）を残すことが要件である（#228 の決定 6、`AGENTS.md` の「テストの採用基準」）。下の 7 件は、守りの分岐が独立しているのに D として消した、または S と分類したまま重さを理由に消したテストで、レビュアーが守りの分岐だけを壊したコピーで残ったテストが全て通ることを確かめた。消したままマージすると、守りが回帰しても気付けない（(c) 理由なく削除された回帰ガード。棚卸しに書いた理由が事実に合わない）。どれも base `481a047` にあったテストを、最小の形で戻す。

| ID | 戻すテスト（base `481a047` の位置） | 守りのコード | 守る条件 | 損害 / 重さ |
| --- | --- | --- | --- | --- |
| F1 gpt-6.1-sol#M-1@776a6b63e0f2 | `test_finalize.py` の `test_missing_or_wrong_verification_stops_before_network` の `missing`（`commands=[]`）の 1 例（base 268・273 行） | `finalize.py` の検証の記録の `commands` が空の拒否（`or not commands`） | 検証コマンドが 0 件の記録では最終化（投稿・マージ・Issue の close）を始めない | 未検証のマージ / 高 |
| F2 gpt-6.1-sol#M-2@776a6b63e0f2 | `test_review_findings.py` の `_move_location` と `test_check_pair_names_each_mismatch` の位置の 1 行（base 744・758 行） | `review_findings.py` の `check_pair` の位置の照合 | 同じ指摘の Markdown と JSON の位置が違う組を拒否する | 記録の取り違え / 中 |
| F3 SWE-2-Max#L-1@776a6b63e0f2/A（gpt-6.1-sol#L-1、Grok-4.7#L-1） | `test_review_findings.py` の `test_statement_candidates_does_not_count_a_term_inside_a_longer_word`（base 1906 行） | `review_findings.py` の `_word_pattern` の前後の境界 | 語は前後が英数字と `_` でない位置だけに当たる | 誤った候補 / 低（S と分類したので消さない） |
| F4 Grok-4.7#M-1@776a6b63e0f2 | `test_review_records.py` の `test_stopped_round_requires_a_concrete_allowed_category`（base 1030 行。例は `permission:`・`iteration_limit: 1`・`確認待ち` の 3 つに絞る）と、正しく通る例として `test_stopped_round_preserves_category_and_pending_decisions`（base 1018 行。`permission` の 1 つに絞る） | `review_records.py` の `_check_outcome` の `stop_reason` の区分 | `stopped` の `stop_reason` は `permission`・`environment`・`external` と空でない具体的な理由 | 記録の取り違え / 中 |
| F5 Grok-4.7#M-2@776a6b63e0f2 | `test_review_records.py` の `INVALID_RECORDS` の `commit-equal-to-reviewed`（base 570 行） | `_check_outcome` の `fixes_pushed` の `commit` と `reviewed_head` の比較 | 新しい commit の無い `fixes_pushed` を拒否する | 誤った結果の報告 / 中 |
| F6 SWE-2-Max#L-1@776a6b63e0f2/B | `test_upsert_pr_comment.py` の `test_records_post_rejects_a_closed_pull_request`（base 690 行。例は CLOSED にした。MERGED は `test_finalize.py` の `test_manual_merge_before_posting_keeps_the_merge[same_head]` が既に確かめる（確認済みの一覧 V-3）。CLOSED だけを通す壊し方を検出するテストは他に無い（V-2）） | `upsert_pr_comment.py` の `_check_pull_request` の `state != "OPEN"` | open でない PR に記録を投稿しない | 誤った対象への書き込み / 低（S と分類したので消さない） |
| F7 deepseek-deepseek-v4.1-flash#M-1@776a6b63e0f2 | `test_review_records.py` の `INVALID_RECORDS` の `empty-seats`（base 294 行）と `no-rerun-seat`（base 330〜341 行） | `review_records.py` の `seats` が空の拒否と、`rerun` が true のレビュアーが無い記録の拒否 | 停止していないサイクルは、空でない `seats` と、`reviewed_head` を再実行したレビュアーを 1 人以上持つ | 再レビューしていない記録での未検証のマージ / 高 |

### 守る条件と影響経路

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 |
| --- | --- | --- | --- | --- |
| F1 | `finalize.py` の検証の記録の検査（`commands` の空・要素の終了コード） | 修正する（テストを戻す） | 空の `commands` で `stopped`・`environment:`・`gh` を呼ばない | 戻したテストが通る。`or not commands` だけを外したコピーで戻した例が失敗する |
| F2 | `check_pair` の ID・重大度・位置・未確認候補の照合 | 修正する | 位置だけが違う組で `not in the Markdown` | 同上（位置の照合だけを外したコピーで失敗） |
| F3 | `statement_candidates` の `_word_pattern` | 修正する | `LIMIT_VALUE` の行に `LIMIT` が入らない | 同上（境界を外したコピーで失敗） |
| F4 | `_check_outcome` の `stopped` の分岐 | 修正する | 3 つの不正な理由が `stop_reason` の問題で拒否され、`permission: …` は通る | 同上（区分の検査を外したコピーで拒否の例が失敗、正しい例は通る） |
| F5 | `_check_outcome` の `fixes_pushed` の分岐 | 修正する | `commit: must differ from reviewed_head` | 同上 |
| F6 | `upsert_pr_comment.py` の `_check_pull_request` | 修正する | `CLOSED` の PR で `not open`、`pr view` だけを呼ぶ | 同上（CLOSED だけを通すコピーで失敗） |
| F7 | `review_records.py` の `seats` の空・`rerun` の検査 | 修正する | `seats: must not be empty unless the round stopped`、`seats: at least one seat must have rerun true unless the round stopped`。F4 の正しい例（`stopped` で `seats=[]`）が、停止したサイクルでは空を許す側を確かめる | 同上（2 つの検査をそれぞれ外したコピーで、対応する例が失敗） |
| 共通 | ほかの残したテスト・領域の全体 | 既に満たす | 領域の pytest が通る | `uv run --locked pytest .agents/scripts .agents/skills/review-fix-planning .agents/skills/review-verify` |

### 棚卸しの表の更新

`docs/superpowers/specs/2026-10-22-create-reso-world-issue232-review-helper-tests-design.md` の「棚卸し」の該当行を、戻したテストの分類（S と重さ、または迷い）と「残す」に直す。戻したテストを含む節の見出しの件数・行数と、「検証の記録」の前後の数を、実測（`pytest --collect-only -q`、`wc -l`、Issue の「検証」の計測）に合わせる。Task 5 の節の見出しの数は、base の実測（`test_run_roles.py` 49 件・725 行、`test_upsert_pr_comment.py` 75 件・840 行）に直す。Task 4 の節の「戻した後の確認は未再実施」は、「検証の記録」の表のとおり controller が再確認したことに直す。

### 実装と取り込み

- 実装: `run_roles.py --phase implement`（担当 `claude-opus`、観測したモデル claude-opus-5-5、545 秒、`stop_confirmed: true`）の commit `68035d39bb8ed8ed18e45cd974eb3809ed752d0d` を、差分が許可したファイルだけであることを確かめてから fast-forward で取り込んだ。担当は戻した例ごとに守りの分岐を外したコピーで失敗を確かめた（F3 は後ろの境界だけを確かめ、前の境界だけを外すコピーでは通る。base のテストのままで、新しいテストは書いていない）
- 司令塔の修正: 確認済みの一覧の V-2・V-3 を受けて、F6 の例を MERGED から CLOSED に変えた（commit `8438ecff15e0b1407eb7015e3dddb3fbb0345676`）。CLOSED だけを通すコピーで失敗することを確かめた


## 実装

- 1 回目（サイクル 1 の指摘 F1〜F7）: `run_roles.py --phase implement`（担当 `claude-opus`、観測したモデル claude-opus-5-5、545 秒、`stop_confirmed: true`、run `9053baffd4134773a3381ef0d75f97f5`）の commit `68035d39bb8e` を、差分が許可したファイルだけであることを確かめて取り込んだ。司令塔が F6 の例を CLOSED に変えた（`8438ecff15e0`。確認済みの一覧 V-2・V-3）
- 2 回目（自己レビューの指摘。下の「守る条件の設計」）: `run_roles.py --phase implement`（担当 `claude-opus`、観測したモデル claude-opus-5-5、1,597 秒、`stop_confirmed: true`、run `78cb23bd455c4f77bd718fbb5863fbb6`）の commit `f445400d5da5` を取り込んだ。base の例を 26 件戻した。runner の終了コードは 1（`outside_changes`）だったが、挙がった 4 つは #235 のセッション（PR #245 の PR 修正ループ）の worktree と `/tmp` の作業領域で、この担当のログに出てこず、`issue-235-script-tests` の変更は #235 の commit だった。この担当の変更ではないと判断して取り込んだ
- 変異の走査（2 回目の担当が実行）: 修正後の木で、戻した全分岐（単一行の `if` を `False` にした 26 件と置換 2 件）を領域の全体のテストで走らせ、すべて検出した（変異なしの基準は 417 passed）

## 検証（最後の修正の後、HEAD `f445400d5da5`、clean）

| コマンド | 終了コード | 結果 |
| --- | --- | --- |
| `uv run --locked pytest .agents/scripts .agents/skills/review-fix-planning .agents/skills/review-verify` | 0 | 417 passed |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools` | 0 | 2,997 passed |
| `bash .devcontainer/run-tests.bash` | 0 | PASS: 33 test(s) |
| `bash scripts/check-layout.sh` | 0 | PASS |
| `git diff --check origin/main...HEAD` | 0 | — |

- 前後の数（Issue の計測、HEAD `f445400d5da5`）: 1,056 件 → 417 件（39.5%）、9,919 行 → 7,050 行（71.1%）。#232 の Spec の「検証の記録」と一致
- 要件・原因・検証の照合（`references/convergence.md` の 3）: 守る条件（base が検出した守りの分岐は、L・D と確かめたものを除き今も検出する）を、戻した全分岐の変異が KILLED になることで確かめた（判定の拒否側）。正しく通る側は、変異なしの基準の 417 passed と、F4・F7 の正しく通る例（停止したサイクルの空の `seats` と `permission:` の理由）で確かめた。L・D と確かめた分岐（自己レビューのファイルの M-1 の「同種箇所」）は、その根拠のまま残した
- 未確認の事項: 単一行の `if`/`elif` でない検査は、`review_records.py:613`・`616` のほかは走査していない。agent_tmp.py・issue_budget.py・review-verify の評価（bash）は走査の対象外。F3 の前の境界は base でも確かめていない。2 回目の修正（`f445400d5da5`）は再レビューしていない（2 回目の自己レビューはしない）

## 自己レビュー（1 回）

`run_roles.py --phase self-review` の 1 回の呼び出し（枠は `verified/776a6b63e0f2.planning.json` の `pre_push_review`）。self-review・fix-check とも割り当ては `self` で、司令塔が 2 つのサブエージェントに同時に任せた（合わせて 1 回）。対象は修正後の HEAD `8438ecff15e0`。

| 役割 | 成果 | 結果 |
| --- | --- | --- |
| self-review（pr-review の非対話の入口、PR 全体） | `claude-opus-5-5-commit-8438ecff15e0b1407eb7015e3dddb3fbb0345676.md` | Medium 2・Info 1・未確認 2。Approve |
| fix-check（review-verify の fix_check） | `verified/8438ecff15e0.fix-check.json`・`.statement-candidates.json`・`.fix-check.md` | 主張 14 件のうち holds 12・violates 2、新しい問題 3 |

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| self#M-1（5 件: finalize.py:213、review_records.py:708、review_target.py:517、review_findings.py:1690・1997） | 対応する | D として消したが、代表は別の分岐を通る。finalize.py:213 は README.md だけを変えた commit を Spec の commit として受け付ける（未検証のマージ、高） |
| self#M-2（run_roles.py:123） | 対応する | 書き込みできるレビューの役割の拒否を L として消したが、壊れるとエラーにならずに書き込み可の担当を起動する（権限の境界） |
| self#U-1（review_records.py の意味の検査 7 か所） | 対応する（迷い） | 壊れると誤った記録がエラーなしに投稿される。下流で L かは確かめていないので、迷いとして残す（#228「迷うものは残す」） |
| self#U-2（review_findings.py の 4 か所） | 対応する（迷い） | 同上（statement の候補・抜粋・common_terms） |
| 統計（review_findings.py 2151〜2215・2480・2578） | 対応する | 棚卸しで「S 低」と分類したまま重さで消していた（決定 6 に反する。self#M-1 の同種箇所の確認で判明） |
| fix-check#V-1・V-2（review_records.py:613・616） | 対応する | F4 で戻した例を 3 つに絞りすぎ、`stop_reason` の欠落と空白だけの理由を検出しない |
| self#I-1・fix-check#V-3 | 対応する | Spec の行数が実測と 1 行ずれる。#236（integration）が集計に使う数なので、そのままでは誤った集計になる（(b) 事実誤認の記述） |

自己レビューの後の修正は再レビューしていない（2 回目の自己レビューはしない）。

## 守る条件の設計（設計の見直し）

- きっかけ: 3（自己レビューでの再発。F4 で直した `stop_reason` の守りが V-1・V-2 で破れていた）と 1（同じ守る条件の 2 回目。サイクル 1 の F1・F2・F5・F7 と同じく、D として消したが代表が別の分岐だった self#M-1）
- 守る条件: base `481a047` のテストが検出した守りの分岐（単一行の `if`/`elif` の条件を `False` にした変異）は、L（壊れても例外・後段の失敗で見える）か D（別の検査が同じ入力を拒否する）と確かめたものを除き、今のテストも検出する。棚卸しの D・L の理由は、この変異の結果で確かめる
- 条件を保つ仕組み: モジュールごとの単一行の変異を、base と今のテストで走らせて比べる（自己レビューの担当が作った走査の道具）。base が検出し今が検出しないものを、L・D と確かめたものと、戻すものに分ける
- 以前の回の修正で足りなかった理由: サイクル 1 は、レビュアーが個別に見つけた 7 件だけを戻した。棚卸しの D・L の理由を、守りの分岐ごとに確かめていなかった
- 比べた直し方: (1) 見つかった分だけ戻す点の修正を続ける — 走査をしないと、次のレビューでまた別の分岐が見つかる。(2) 走査で、base が検出し今が検出しない分岐を全部挙げ、L・D と確かめたもの以外を戻す（選んだ案）— 条件が走査の結果で確かめられる。(3) この PR の保証を狭め、「S は残す」をやめる — #228 の決定 6 に反するので取れない
- 範囲と限界: 走査は単一行の `if`/`elif` だけで、`if` でない検査（`review_records.py:613` など）は個別に見た。対象は finalize.py・upsert_pr_comment.py・run_roles.py・review_target.py・dispatch.py・review_records.py・review_findings.py。agent_tmp.py・issue_budget.py・review-verify の評価（bash）は走査していない。L・D と確かめた分岐の一覧は、自己レビューのファイルの M-1 の「同種箇所」にある
