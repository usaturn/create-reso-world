# 2026-10-02 PR #8 レビュー選別と修正方針（第 6 回）

- 対象 PR: usaturn/create-reso-world#8（ブランチ `docs/list-shrink-recreate-split`、現行 HEAD `cca3a9016d21d246f93102fc93f4e405ac04e8d2`）
- 状態: **2026-10-02 にユーザ承認済み（「進めて。」）。F2 の文書修正を実施し、本書とあわせて PR #8 のブランチにコミットする。F1 の PR 本文の更新と状況コメントは push の後に行う**
- 目的: 第 5 回の修正後に集まったレビュー 9 件から、現行のコミット済み文書と PR 本文でまだ生きている指摘だけを選び、PR 本文の追随漏れと第 5 回の記録のチェックリストの状態を直す。
- **brainstorming 経路: bounded**。既存文書（第 5 回の選別記録）のチェックボックス 3 か所と PR 本文の追記のみ。コード・公開インターフェース・state 形式・計画の手順は変えない。`review-fix-planning` の指定により bounded でも Spec を保存する。
- 未コミットの既存 Spec、別 worktree の差分、指定ディレクトリ外のレビューは入力にも根拠にもしていない。fork への本実装・実機の変更・上流提出は範囲外。

以下では次の略記を使う（第 4・5 回と同じ衝突しない命名）。行番号はすべて `HEAD6` のもの。

- `HEAD6`: 現行 HEAD `cca3a9016d21d246f93102fc93f4e405ac04e8d2`
- `PLAN`: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- `DESIGN`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`
- `REC-R`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md`
- `REC-1`: `docs/superpowers/specs/2026-10-02-pr8-docs-review-fixes-design.md`
- `REC-2`: `docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md`
- `REC-3`: `docs/superpowers/specs/2026-10-02-pr8-round3-review-fixes-design.md`
- `REC-4`: `docs/superpowers/specs/2026-10-02-pr8-round4-review-fixes-design.md`
- `REC-5`: `docs/superpowers/specs/2026-10-02-pr8-round5-review-fixes-design.md`

## 2. 入力の固定

`reviews/#8-docs-list-shrink-recreate-split/` の全 9 ファイルを読んだ。

| ファイル | レビューの対象 HEAD | 状態 |
|---|---|---|
| SWE-2-Max.md | `b851852385b2` → `cca3a9016d21`（6 回） | 読了 |
| claude-sonnet-5-5.md | `c6749fc01605` → `cca3a9016d21`（5 回） | 読了 |
| commandcode-deepseek-deepseek-v4.1-flash.md | `c6749fc01605` → `cca3a9016d21`（4 回） | 読了 |
| deepseek-deepseek-v4.1-flash.md | `b851852385b2` → `913a0f805917`（2 回） | 読了 |
| gpt-6-sol.md | `c6749fc01605`（1 回） | 読了 |
| grok-4.7.md | `c6749fc01605` → `913a0f805917`（2 回） | 読了 |
| opencode-go-muse-spark-1.3-contributor.md | `913a0f805917` → `cca3a9016d21`（3 回） | 読了 |
| qwen3.8-max.md | `b851852385b2` → `cca3a9016d21`（5 回） | 読了 |
| xai-grok-4.7.md | `b851852385b2` → `d1ad157597dd`（3 回） | 読了 |

各ファイルの Review history から `cca3a9016d21` の回を除くと、REC-5 §2 の表（最終 HEAD と回数）と全行が一致する。

## 3. 検証方法

- 現行 HEAD の特定: `gh pr view 8` の headRefOid と `git rev-parse origin/docs/list-shrink-recreate-split` が `HEAD6` で一致。
- 対象は文書のみの PR で実行対象のコードを含まないため、「現行 HEAD での再現」は `git show HEAD6:<path>` のコミット済み blob と、`gh pr view 8 --json body`・`gh pr diff 8 --name-only` との照合で行った。working tree のファイルは検証根拠に使っていない。
- 挙動の再現を要する指摘は無かったため、隔離 worktree は作らなかった（第 2〜5 回と同じ基準）。
- PR 本文: 「## ファイル」節は 7 ファイル（REC-4 まで）、`gh pr diff 8 --name-only` は 8 ファイルで、欠けているのは REC-5。「## 設計の承認状況」の最後の文は第 4 回で終わり、第 5 回への言及は無い。
- REC-5 §7（140-144 行）は 5 項目すべて `- [ ]`。同じ文書の §8（146-151 行）は F1 の修正・検証・コミットの実施を記録し、`HEAD6` のコミット `cca3a90` に REC-2:95 の修正と REC-5 自体が含まれる。比較として REC-2:162-168・REC-3:141-146 は実施済みの項目をすべて `- [x]`、REC-4:171-178 はコミットより後に行う 178 行目だけを `- [ ]` にしている。

## 4. 正式な指摘の分類（35 件）

解消済み 25 / 対応する 6（2 テーマ） / 判断保留 0 / 対応しない 4。

### 現行 HEAD で再検証した指摘（12 件）

| ID | 元の指摘 | 分類 | 根拠 |
|---|---|---|---|
| RF6-01 | SWE F-02: 置き換え元の削除の進捗を `"fields"` 段階で報告する | 対応しない | `HEAD6` の PLAN:2152-2153 は変わらず `"fields"`。上流 `b3a84ae` の移動元削除の進捗報告に合わせた設計判断で、RFP-07・RF2-02・RF3-11・RF4-01・RF5-01 と 5 回記録済み。レビュー自身も現状維持を推奨。仕様の是非の論点で (a)〜(d) を満たさない |
| RF6-02 | SWE I-3: D-30 の補足が「同じ型の key がほかに無い」前提を落としている | 対応しない | `HEAD6` の DESIGN:480 は補足の直前の文で同じ型の key がある場合を別規則として書き、PLAN:3234-3244 も `sameTypeKeys` を `multipleReferencedCandidates` より先に評価する。どちらの分岐でも「候補を削除しない」結論は同じで、索引の語句の精度の問題。レビュー自身も RF5-02 の判断を支持（RF4-03・RF5-02 と同じ判断） |
| RF6-03 | SWE I-4: PR 本文の「ファイル」節と「設計の承認状況」が第 5 回に追随していない | **対応する (b)** → F1 | §3 のとおり、本文のファイル一覧（7 件）が差分（8 件）と一致せず、承認状況も第 4 回で止まる。DESIGN:398 は「レビュー修正の後は `gh pr edit --body-file` で更新する（このリポジトリの PR でも同じ）」と定める。同種の RF4-18 は第 4 回で対応済み |
| RF6-04 | commandcode I-2: 同上 | **対応する (b)** → F1 | RF6-03 と同じ事実 |
| RF6-05 | opencode I-1: 同上（あわせて、本文と状況コメントのどちらを正とするかの明記を提案） | **対応する (b)** → F1 | RF6-03 と同じ事実。提案の後半は DESIGN:398 が「本文を更新する」と既に定めているため、本書 §7 に本文更新の項目を入れることで扱い、既存文書は変えない |
| RF6-06 | qwen I-9: 同上（あわせて、REC-5 §7 に本文更新の項目が無いことが原因と指摘） | **対応する (b)** → F1 | RF6-03 と同じ事実。REC-5 §7 への項目の追加は過去の回の計画の書き換えになるため行わず、本書 §7 に本文更新の項目を入れる |
| RF6-07 | SWE I-5: REC-5 §7 のチェックボックスが実施済みの項目も `[ ]` のまま | **対応する (b)** → F2 | §3 のとおり、REC-5 §7 の項目 1〜3（REC-2:95 の修正、`git diff --check` と `check-layout.sh`、§8 の記録とコミット）は `cca3a90` の内容と §8 で実施済みと確かめられるのに未実施と表示され、同じ文書内で食い違う |
| RF6-08 | commandcode I-3: 同上 | **対応する (b)** → F2 | RF6-07 と同じ事実 |
| RF6-09 | qwen I-5: Spec 8 章のテスト列挙が後から追加の 3 件に追随していない | 対応しない | `HEAD6` の DESIGN を grep し 3 テスト名は 0 件、PLAN:1985・2995・3742 に実在。8 章は網羅を主張しておらず誤りではない。RF3-22・RF4-16・RF5-06 と同じく Info 級の記載漏れで (a)〜(d) を満たさない |
| RF6-10 | qwen I-8: REC-2 と REC-3 で略記 `FIRST`・`CURRENT` が別の対象を指す | 対応しない | `HEAD6` の REC-2:22 と REC-3:21 で `FIRST` の指示先は異なるままだが、各文書は自節で略記を定義し文書内では一意に解決できる。過去の回の記録で事実誤認ではない（RF4-19・RF5-07 と同じ判断） |
| RF6-11 | gpt-6-sol H-1: 実機確認の strict validate と削除に接続先を渡す | 解消済み | 検出時 HEAD は `c6749fc01605`。`HEAD6` の PLAN:4215 が `validate "$DOC" --strict --url auto --session <SessionId> --json`、PLAN:4224 が `inspect`・`slot delete` の両方に同じ宛先、PLAN:4225 が失敗時の手順にも宛先を付け、接続先を再確認できない場合は削除せず止まる。明示 URL の経路の置き換え規則は PLAN:4178 |
| RF6-12 | gpt-6-sol M-1: 置き換え前後の両方が参照される中断で削除を案内しない | 解消済み | 検出時 HEAD は `c6749fc01605`。`HEAD6` の DESIGN:247 に「`referencedBy` が空でない候補が 2 件以上」の分岐があり、候補の削除や `supersededId` の除去を案内しない。PLAN:3236-3244 の `multipleReferencedCandidates` が同じ分岐を実装し、B7 のテスト（PLAN:3742）が固定する |

### レビューの Resolved findings（解消確認済みの履歴・23 件）

いずれも各レビューが解消確認時 HEAD を記録し、本セッションの抜取照合（PLAN:22 の SDK 注記、DESIGN:3 の決定事項範囲、REC-2:95 の文言、PLAN の文書操作 12 件・全 78 件）と矛盾しない。再分類: すべて解消済み。

| ID | 元の指摘 | 解消確認時 HEAD |
|---|---|---|
| RF6-13 | SWE F-01: 計画のコードブロックの nullable 参照外し 2 箇所 | `c6749fc01605` |
| RF6-14 | SWE I-1: D-30 の索引が新しい案内分岐を欠く | `913a0f805917` |
| RF6-15 | SWE I-2: PLAN:22 の SDK 記録に pin の注記が無い | `d1ad157597dd` |
| RF6-16 | claude M-1: 新テストの `ApplyRubbleAsync` 引数順 | `bf84763825fd` |
| RF6-17 | claude I-1: PR 本文が B3・B4 の変更を述べていない | `bf84763825fd` |
| RF6-18 | commandcode H-1: 同じく引数順 | `bf84763825fd` |
| RF6-19 | commandcode H-2: B5 テストの書き込み位置の数え直し漏れ | `bf84763825fd` |
| RF6-20 | commandcode I-1: REC-2 の「文書変更10操作」が実数 12 件と合わない | `cca3a9016d21` |
| RF6-21 | deepseek L-1: PR 本文の検証結果が現行と一致しない | `913a0f805917` |
| RF6-22 | deepseek I-1: Spec 冒頭の決定事項範囲が古い | `913a0f805917` |
| RF6-23 | grok-4.7 H-1: 自己参照テストが伸びる文書を apply する | `913a0f805917` |
| RF6-24 | opencode L-1: PLAN:22 の SDK 記録に注記が無い | `d1ad157597dd` |
| RF6-25 | qwen L-1: PR 本文の数値が修正前の値 | `bf84763825fd` |
| RF6-26 | qwen L-2: Spec 7.8 の plan フィルター主張を固定する手段が無い | `bf84763825fd` |
| RF6-27 | qwen I-1: 決定事項範囲が D-33 を欠く | `bf84763825fd` |
| RF6-28 | qwen I-2: `SaveSlotIndexes` 表記揺れ | `bf84763825fd` |
| RF6-29 | qwen I-3: 「392 件中 23 件」記録の母数の食い違い | `913a0f805917` |
| RF6-30 | qwen I-4: REC-2 の SDK 記録と `global.json` pin の不整合 | `913a0f805917` |
| RF6-31 | qwen I-6: PLAN:22 に F3 の注記が無い | `d1ad157597dd` |
| RF6-32 | qwen I-7: PR 本文のファイル一覧・承認状況の追随漏れ（第 3 回分） | `d1ad157597dd` |
| RF6-33 | xai M-1: 検証失敗時に state に残る作り直しが案内に出ない | `bf84763825fd` |
| RF6-34 | xai L-1: 自己参照で他の initialFields が渡されない | `bf84763825fd` |
| RF6-35 | xai I-1: 冒頭の決定事項範囲が D-33 を落とす | `bf84763825fd` |

## 5. 補助項目の分類（34 項目）

レビューの Unverified candidates と Test suggestions。対応しない 30 / 統合 4。いずれも指摘ではなく、計画が実装時の Task ゲートで確かめると明記した確認項目、計画に既にあるテストの言い換え、解消済み項目への追従提案、または任意提案である。opencode が「検討したが報告に至らなかったもの」として挙げた 4 件は、レビュー自身が候補ではないと明記しているため数えない。

| ID | 項目 | 分類 | 根拠 |
|---|---|---|---|
| AUX6-01 | SWE V-3: `AShorterDeclaration…` の事前 PASS 主張と Part C 手順 | 対応しない | AUX4-03・AUX5-02 と同じ。Task ごとの Expected が実装時に確かめる |
| AUX6-02 | SWE V-2（終了扱いの維持）: 397 件・FAIL 53/PASS 344 の独立再集計 | 対応しない | レビュー自身が終了扱い。AUX4-02・AUX5-01 と同じ |
| AUX6-03 | SWE V-4（終了扱いの維持）: B7 の既存 theory の維持 | 対応しない | レビュー自身が終了扱い。AUX4-04・AUX5-03 と同じ |
| AUX6-04 | SWE 範囲の限定: REC-5 §2 の他モデル行は未照合 | 対応しない | レビュー自身が候補ではないと明記。本書 §2 の照合で全行一致 |
| AUX6-05 | SWE T-1: F-02 の進捗キャプチャテスト | 対応しない | RF6-01 の判断に従属 |
| AUX6-06 | SWE T-2: I-3・I-4・I-5 は文書で対応可能 | 統合 | RF6-02・F1・F2 の扱いに含める |
| AUX6-07 | claude U-1: B3 の `Enabled` が偽クライアントで拒否される可能性 | 対応しない | 実装時に B3 Step 2・4 の実行で確かめる計画上のゲート（AUX5-06 と同じ） |
| AUX6-08 | claude U-2: B5 Step 2 の FAIL/PASS 内訳 | 対応しない | 実装時に B5 Step 2 で実測して Expected と照合するゲート |
| AUX6-09 | claude U-3: `multipleReferencedCandidates` の案内の具体性 | 対応しない | 案内は危険な操作を勧めない設計どおり。文言の分かりやすさは仕様論点 |
| AUX6-10 | claude T-1: B3 テストのミューテーション確認 | 対応しない | 実装時 Step 確認の言い換え |
| AUX6-11 | claude T-2: B5 Step 2 の内訳照合 | 対応しない | 同上 |
| AUX6-12 | commandcode U-1: 各 Task の Expected 件数 | 対応しない | 実装時の各 Task Step 4 のゲート |
| AUX6-13 | commandcode U-2: B8 Step 2 の FAIL 53/PASS 344 | 対応しない | 実装時の B8 Step 2 のゲート |
| AUX6-14 | commandcode U-3: Task C2 の型・メンバー名 | 対応しない | 実機確認は計画 Task C2 の範囲（ユーザ承認が前提） |
| AUX6-15 | commandcode U-4: 計画コードブロック全体の逐行再読 | 対応しない | 66 操作の再生・12 ケース実行の記録があり、`HEAD6` で計画は無変更。実装時の Task ゲートが確かめる |
| AUX6-16 | commandcode U-5: REC-5 §2 の入力 9 ファイルとラウンド数 | 対応しない | 本セッションで 9 ファイルの Review history を読み、REC-5 §2 の全行が `cca3a9016d21` の回を除いた履歴と一致することを確認した（本書 §2） |
| AUX6-17 | commandcode T-1: Task の Expected 照合 | 対応しない | AUX6-12 と同じ |
| AUX6-18 | commandcode T-2: B8 Step 2 の実測 | 対応しない | AUX6-13 と同じ |
| AUX6-19 | commandcode T-3: B7 の 12 ケース実行 | 対応しない | 実装時ゲートの言い換え |
| AUX6-20 | commandcode T-4: I-2・I-3 はテスト不要 | 統合 | F1・F2 の扱いに含める |
| AUX6-21 | deepseek U-1: 66 操作のアンカーとビルド | 対応しない | 実装時 Task 0 Step 1・各 Task の停止ゲート |
| AUX6-22 | deepseek U-2: 実機での挙動 | 対応しない | 計画 Task C2 の範囲 |
| AUX6-23 | deepseek T-1: B3 の追加テスト | 対応しない | 計画が既に含むテスト（PLAN:1985） |
| AUX6-24 | deepseek T-2: B5 の追加テスト | 対応しない | 同上（PLAN:2995） |
| AUX6-25 | deepseek T-3: B7 の追加テスト | 対応しない | 同上（PLAN:3742） |
| AUX6-26 | deepseek T-4: 新規指摘に紐づく提案無し | 対応しない | 追加の変更を求めない記述 |
| AUX6-27 | gpt-6-sol T-1: H-1 の手順固定 | 対応しない | RF6-11 で解消済み。接続先指定は PLAN C2 に明記済み |
| AUX6-28 | gpt-6-sol T-2: M-1 の中断テスト | 対応しない | RF6-12 で解消済み。B7 のテスト（PLAN:3742）がカバー |
| AUX6-29 | opencode T-1: 本文のファイル節と差分の一致、承認状況の第 5 回の言及を確かめる | 統合 | F1 の検証方法に含める |
| AUX6-30 | opencode T-2: REC-2:95 の修正（RF5-03）の固定確認 | 対応しない | 解消済み項目（RF6-20）の確認手順で、追加の変更を求めない |
| AUX6-31 | opencode T-3: PLAN:22 の注記（L-1）の存続確認 | 対応しない | 解消済み項目（RF6-24）の確認手順で、追加の変更を求めない |
| AUX6-32 | qwen U-1: Spec 3.1・3.2 の上流コード全文照合 | 対応しない | AUX4-27・AUX5-29 と同じ。Task 0 と各 Task の停止ゲートが確かめる |
| AUX6-33 | qwen T-1: I-5・I-8・I-9 はテスト不要 | 統合 | RF6-09・RF6-10・F1 の扱いに含める |
| AUX6-34 | qwen T-2: 旧 L-2 の任意テスト | 対応しない | RFP-08・RF2-06・RF3-04・RF4-21・AUX5-31 で記録済み |

## 6. 対応する項目の修正方針

### F1: PR 本文の「ファイル」節と「設計の承認状況」を更新する（RF6-03〜RF6-06）

- 時機: 本書と F2 を commit・push した後に行う。本書もこの PR の差分に加わるため、push 後の `gh pr diff 8 --name-only`（9 ファイル）に本文を合わせる。
- 「## ファイル」節の末尾（REC-4 の行の後）に次の 2 行を足す。
  - `` - `docs/superpowers/specs/2026-10-02-pr8-round5-review-fixes-design.md`（第5回の選別と、第2回の記録の文書操作数の修正の記録） ``
  - `` - `docs/superpowers/specs/2026-10-02-pr8-round6-review-fixes-design.md`（第6回の選別と、第5回の記録のチェックリストの修正・この本文の更新の記録） ``
- 「## 設計の承認状況」の最後の箇条の末尾に次の 2 文を足す（既存の文は変えない）。
  - `第5回では全9レビューを照合し、正式29件を解消済み24・対応1・対応しない4に選別し、第2回の記録の文書操作数（10→12）を直しました。第6回では全9レビューを照合し、正式35件を解消済み25・対応6（2テーマ）・対応しない4に選別し、第5回の記録のチェックリストの状態とこの本文を更新しました。`
- 手順: `gh pr view 8 --json body --jq .body` を scratchpad に保存し、上の追記だけを加えたファイルを `gh pr edit 8 --repo usaturn/create-reso-world --body-file <file>` で反映する。ほかの節（実装計画の検証・進め方など）は変えない。
- 却下した案: REC-5 §7 に本文更新の項目を後から足す案（qwen I-9 の推奨の一部）は、過去の回の計画を書き換えることになるため採用しない。再発防止は本書 §7 に本文更新の項目を入れることで扱う。本文と状況コメントのどちらを正とするかは DESIGN:398 が本文の更新を定めており、新しい規則は足さない。
- 検証方法: 更新後の `gh pr view 8 --json body --jq .body` の「## ファイル」節に挙がるパスの集合が `gh pr diff 8 --name-only` の 9 ファイルと一致すること、「## 設計の承認状況」に「第5回」「第6回」の文があること、更新前後の本文の差分が上の追記だけであること（`diff` で確認）。

### F2: REC-5 §7 の実施済みの項目を `[x]` にする（RF6-07・RF6-08）

- 変更: REC-5 の 140-142 行目（REC-2:95 の修正、`git diff --check` と `check-layout.sh`、§8 の記録とコミット）の `- [ ]` を `- [x]` にする。項目の文言は変えない。
- 143-144 行目（push と状況コメント）は `- [ ]` のままにする。REC-4:178 と同じく、文書のコミットより後に行う項目で、結果は PR の状況コメントに記録する扱い（REC-5 §8 の最終行もそれを参照している）。
- 却下した案: 143-144 行目も実施済みとして `[x]` にする案は、第 2〜4 回の記法（コミット後の項目は未チェックのまま PR の状況コメントで記録）から外れ、レビューも求めていないため採用しない。
- 検証方法: `git show HEAD:docs/superpowers/specs/2026-10-02-pr8-round5-review-fixes-design.md | sed -n '140,144p'` で `[x]` が 3 行・`[ ]` が 2 行であること、`git diff` の変更がその 3 行の `[ ]`→`[x]` と本書の追加だけであること、`git diff --check` と `bash scripts/check-layout.sh` が通ること。変更は文書のみで環境用の source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（第 2〜5 回と同じ範囲）。

**仕様論点の記録:** `fields` 進捗は上流の先例に合わせる設計判断（RFP-07・RF2-02・RF3-11・RF4-01・RF5-01）を維持する。D-30 補足の語句（RF6-02）、Spec 8 章の列挙（RF6-09）、過去の回の記録の略記（RF6-10）は変えない。判断保留は無い。

## 7. 実装のチェックリスト

- [x] 全 9 レビュー入力と各対象 HEAD を固定
- [x] 現行 PR / リポジトリ / ブランチ / HEAD を確認（`gh pr view`・`git fetch origin`）
- [x] `git show HEAD6:<path>` のコミット済み blob と `gh` の本文・差分一覧で各指摘を検証（working tree 未使用。挙動の再現が不要なため隔離 worktree は作らない）
- [x] 正式 35 件と補助 34 項目を 4 区分に分類
- [x] brainstorming の bounded 経路で修正方針を整理
- [x] ユーザの明示的な承認（2026-10-02、「進めて。」）
- [x] `.worktrees/list-shrink-spec`（`docs/list-shrink-recreate-split`）で F2 を実施し、`git diff --check` と `bash scripts/check-layout.sh` を通す
- [x] 本書の 8 節に実施記録を書き、F2 の修正と本書を `docs/list-shrink-recreate-split` にコミットする
- [ ] commit / push、F1 の PR 本文の更新（DESIGN:398）、状況コメント（本書のコミットより後に行うため、結果は PR #8 の状況コメントに記録する）

## 8. 実装の記録

- 作業場所: 既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`）。着手時はクリーンで、HEAD は `HEAD6` と一致し、`git fetch origin` 後の `origin/docs/list-shrink-recreate-split` と `gh pr view 8` の headRefOid も `HEAD6` のままだった。本書は共有ルートで起草し、この worktree へ移してからコミットした（共有ルートに複製は残していない）。共有ルートの未コミット文書（他タスクの Spec）は取り込んでいない。
- F2: REC-5 の 140-142 行目の `- [ ]` を `- [x]` にした。項目の文言と 143-144 行目（push・状況コメント）は無変更。
- 検証: `sed -n '140,144p' REC-5` で `[x]` 3 行・`[ ]` 2 行であること、`git diff` の変更が REC-5 の 3 行と本書の追加だけであること、`git diff --check`・`bash scripts/check-layout.sh` が通ったことを確かめた。変更は文書のみで環境用の source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（第 2〜5 回と同じ範囲）。
- F1（PR 本文の更新）・コミット・push の結果は PR の状況コメントを参照。
