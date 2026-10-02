# 2026-10-02 PR #8 レビュー選別と修正方針（第 5 回）

- 対象 PR: usaturn/create-reso-world#8（ブランチ `docs/list-shrink-recreate-split`、現行 HEAD `d1ad157597ddeda4df3a5efb11202493ef09df7c`）
- 状態: **2026-10-02 にユーザ承認済み（「進めて。」）。F1 の文書修正を実施し、本書とあわせて PR #8 のブランチにコミットする。PR への状況コメントは push の後に更新する**
- 目的: 第 4 回の修正後に集まったレビュー 9 件から、現行のコミット済み文書でまだ生きている指摘だけを選び、残った 1 件の記録の事実誤認を直す。
- **brainstorming 経路: bounded**。既存文書（第 2 回の選別記録）の 1 行の事実修正のみ。コード・公開インターフェース・state 形式・計画の手順は変えない。`review-fix-planning` の指定により bounded でも Spec を保存する。
- 未コミットの既存 Spec、別 worktree の差分、指定ディレクトリ外のレビューは入力にも根拠にもしていない。fork への本実装・実機の変更・上流提出は範囲外。

以下では次の略記を使う（第 4 回と同じ衝突しない命名）。行番号はすべて `HEAD5` のもの。

- `HEAD5`: 現行 HEAD `d1ad157597ddeda4df3a5efb11202493ef09df7c`
- `PLAN`: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- `DESIGN`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`
- `REC-R`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md`
- `REC-1`: `docs/superpowers/specs/2026-10-02-pr8-docs-review-fixes-design.md`
- `REC-2`: `docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md`
- `REC-3`: `docs/superpowers/specs/2026-10-02-pr8-round3-review-fixes-design.md`
- `REC-4`: `docs/superpowers/specs/2026-10-02-pr8-round4-review-fixes-design.md`

## 2. 入力の固定

`reviews/#8-docs-list-shrink-recreate-split/` の全 9 ファイルを読んだ。

| ファイル | レビューの対象 HEAD | 状態 |
|---|---|---|
| SWE-2-Max.md | `b851852385b2` → `d1ad157597dd`（5 回） | 読了 |
| claude-sonnet-5-5.md | `c6749fc01605` → `d1ad157597dd`（4 回） | 読了 |
| commandcode-deepseek-deepseek-v4.1-flash.md | `c6749fc01605` → `d1ad157597dd`（3 回） | 読了 |
| deepseek-deepseek-v4.1-flash.md | `b851852385b2` → `913a0f805917`（2 回） | 読了 |
| gpt-6-sol.md | `c6749fc01605`（1 回） | 読了 |
| grok-4.7.md | `c6749fc01605` → `913a0f805917`（2 回） | 読了 |
| opencode-go-muse-spark-1.3-contributor.md | `913a0f805917` → `d1ad157597dd`（2 回） | 読了 |
| qwen3.8-max.md | `b851852385b2` → `d1ad157597dd`（4 回） | 読了 |
| xai-grok-4.7.md | `b851852385b2` → `d1ad157597dd`（3 回） | 読了 |

## 3. 検証方法

- 現行 HEAD の特定: `gh pr view 8` の headRefOid と `git rev-parse origin/docs/list-shrink-recreate-split` が `HEAD5` で一致。
- 対象は文書のみの PR で実行対象のコードを含まないため、「現行 HEAD での再現」は `git show HEAD5:<path>` のコミット済み blob と `gh pr view 8 --json body` の本文との照合で行った。working tree のファイルは検証根拠に使っていない。
- 挙動の再現を要する指摘は無かったため、隔離 worktree は作らなかった（第 2〜4 回と同じ基準）。
- commandcode I-1 の操作数は、PLAN の `**変更:**`・`**新規作成:**` ヘッダを `HEAD5` の blob で機械的に集計して確かめた（文書 12、source/test 66＝変更 64＋新規作成 2）。

## 4. 正式な指摘の分類（29 件）

解消済み 24 / 対応する 1 / 判断保留 0 / 対応しない 4。

### 現行 HEAD で再検証した指摘（7 件）

| ID | 元の指摘 | 分類 | 根拠 |
|---|---|---|---|
| RF5-01 | SWE F-02: 置き換え元の削除の進捗を `"fields"` 段階で報告する | 対応しない | `HEAD5` の PLAN:2152-2153 は変わらず `"fields"`。上流 `b3a84ae` の移動元削除の進捗報告に合わせた設計判断で、RFP-07・RF2-02・RF3-11・RF4-01 と 4 回記録済み。レビュー自身も現状維持を推奨。仕様の是非の論点で (a)〜(d) を満たさない |
| RF5-02 | SWE I-3: D-30 の補足が「同じ型の key がほかに無い」前提を落としている | 対応しない | `HEAD5` の DESIGN:480 は補足の直前の文で同じ型の key がある場合を別規則として書き、計画のコード（PLAN:3241-3243）も同じ型の判定を先に評価する。どちらの分岐でも結論は同じで、索引の語句の精度の問題。事実誤認とは言えず (a)〜(d) を満たさない（RF4-03 と同じ判断） |
| RF5-03 | commandcode I-1: REC-2 の「文書変更10操作」が計画の実際の文書操作 12 件と合わない | **対応する (b)** | `HEAD5` の REC-2:95 が「文書変更10操作」と書くが、同じ集計規則（`**変更:**`・`**新規作成:**` を 1 操作）での PLAN の文書操作は 12 件（Task A2 の 520 行・Task A3 の 895 行・Task B8 の 3797-3920 行の 10 件）。source/test の 66 は記録と一致するため数え方の差では説明できず、REC-4 が引く「78 操作」（66+12）とも食い違う。コミット済み文書の事実誤認 |
| RF5-04 | gpt-6-sol H-1: 実機確認の strict validate と削除に接続先を渡す | 解消済み | 検出時 HEAD は `c6749fc01605`。`HEAD5` の PLAN C2 は Step 3 の `validate "$DOC" --strict --url auto --session <SessionId> --json`、Step 4 の diff・apply・inspect、Step 6 の `inspect ID` と `slot delete ID --yes`、失敗時手順のすべてに接続先が明記され（PLAN:4215・4224-4225・4230 付近）、明示 URL 経路の置き換え規則と接続先を再確認できない場合は削除せず止まる条件もある。RF4-12 の反映どおり |
| RF5-05 | gpt-6-sol M-1: 置き換え前後の両方が参照される中断で削除を案内しない | 解消済み | 検出時 HEAD は `c6749fc01605`。`HEAD5` の DESIGN:247-249 は「同じ型の key がほかに無く、`referencedBy` が空でない候補が 2 件以上」分岐を持ち、候補の削除や `supersededId` の除去を案内せず参照元の確認・張り替え・再検査を先に行うと明記。PLAN:3236-3244 の `multipleReferencedCandidates` が同じ分岐を実装し、B7 のテスト（PLAN:3742）が固定する。第 2 回修正（D-30 補足・7.7）の反映どおり |
| RF5-06 | qwen I-5: Spec 8 章のテスト列挙が後から追加の 3 件に追随していない | 対応しない | `HEAD5` の DESIGN を grep し 3 テスト名は 0 件、PLAN:1985・2995・3742 に実在。8 章は網羅を主張しておらず誤りではない。RF3-22・RF4-16 と同じく Info 級の記載漏れで (a)〜(d) を満たさない |
| RF5-07 | qwen I-8: REC-2 と REC-3 で略記 `FIRST`・`CURRENT` が別の対象を指す | 対応しない | `HEAD5` の REC-2:22 と REC-3:21 を現物で再確認し、`FIRST` の指示先が異なるまま。各文書は自節で略記を定義し文書内では一意に解決できる。過去の回の記録で事実誤認ではなく (a)〜(d) を満たさない（RF4-19 と同じ判断） |

### レビューの Resolved findings（解消確認済みの履歴・22 件）

いずれも各レビューが解消確認時 HEAD を記録し、本セッションの抜取照合（RF5-04・05 の確認で参照した箇所と同一の規範文・コード）と矛盾しない。再分類: すべて解消済み。

| ID | 元の指摘 | 解消確認時 HEAD |
|---|---|---|
| RF5-08 | SWE F-01: 計画のコードブロックの nullable 参照外し 2 箇所 | `c6749fc01605` |
| RF5-09 | SWE I-1: D-30 の索引が新しい案内分岐を欠く | `913a0f805917` |
| RF5-10 | SWE I-2: PLAN:22 の SDK 記録に pin の注記が無い | `d1ad157597dd` |
| RF5-11 | claude M-1: 新テストの `ApplyRubbleAsync` 引数順 | `bf84763825fd` |
| RF5-12 | claude I-1: PR 本文が B3・B4 の変更を述べていない | `bf84763825fd` |
| RF5-13 | commandcode H-1: 同じく引数順 | `bf84763825fd` |
| RF5-14 | commandcode H-2: B5 テストの書き込み位置の数え直し漏れ | `bf84763825fd` |
| RF5-15 | deepseek L-1: PR 本文の検証結果が現行と一致しない | `913a0f805917` |
| RF5-16 | deepseek I-1: Spec 冒頭の決定事項範囲が古い | `913a0f805917` |
| RF5-17 | grok-4.7 H-1: 自己参照テストが伸びる文書を apply する | `913a0f805917` |
| RF5-18 | opencode L-1: PLAN:22 の SDK 記録に注記が無い | `d1ad157597dd` |
| RF5-19 | qwen L-1: PR 本文の数値が修正前の値 | `bf84763825fd` |
| RF5-20 | qwen L-2: Spec 7.8 の plan フィルター主張を固定する手段が無い | `bf84763825fd` |
| RF5-21 | qwen I-1: 決定事項範囲が D-33 を欠く | `bf84763825fd` |
| RF5-22 | qwen I-2: `SaveSlotIndexes` 表記揺れ | `bf84763825fd` |
| RF5-23 | qwen I-3: 「392 件中 23 件」記録の母数の食い違い | `913a0f805917` |
| RF5-24 | qwen I-4: REC-2 の SDK 記録と `global.json` pin の不整合 | `913a0f805917` |
| RF5-25 | qwen I-6: PLAN:22 に F3 の注記が無い | `d1ad157597dd` |
| RF5-26 | qwen I-7: PR 本文のファイル一覧・承認状況の追随漏れ | `d1ad157597dd` |
| RF5-27 | xai M-1: 検証失敗時に state に残る作り直しが案内に出ない | `bf84763825fd` |
| RF5-28 | xai L-1: 自己参照で他の initialFields が渡されない | `bf84763825fd` |
| RF5-29 | xai I-1: 冒頭の決定事項範囲が D-33 を落とす | `bf84763825fd` |

## 5. 補助項目の分類（31 項目）

レビューの Unverified candidates と Test suggestions。対応しない 28 / 統合 3。いずれも指摘ではなく、計画が実装時の Task ゲートで確かめると明記した確認項目、計画に既にあるテストの言い換え、解消済み項目への追従提案、または任意提案である。

| ID | 項目 | 分類 | 根拠 |
|---|---|---|---|
| AUX5-01 | SWE V-2: 397 件・FAIL 53/PASS 344 の独立再集計 | 対応しない | REC-4 AUX4-02 が grok-4.7 の `HEAD4` での実測を解消の根拠として記録。実装時の各 Task ゲートが確かめる |
| AUX5-02 | SWE V-3: `AShorterDeclaration…` の事前 PASS 主張と Part C 手順 | 対応しない | REC-4 AUX4-03 と同じ。Task ごとの Expected が実装時に確かめる |
| AUX5-03 | SWE V-4: B7 の既存 theory が維持できるか | 対応しない | REC-4 AUX4-04 と同じ |
| AUX5-04 | SWE T-1: F-02 の進捗キャプチャテスト | 対応しない | RF5-01 の判断に従属（AUX4-05 記録済み） |
| AUX5-05 | SWE T-2: I-3 は文書修正で対応可能 | 統合 | RF5-02 の扱いに含める（AUX4-06 記録済み） |
| AUX5-06 | claude U-1: B3 の `Enabled` が偽クライアントで拒否される可能性 | 対応しない | 実装時に B3 Step 2・4 の実行で確かめる計画上のゲート |
| AUX5-07 | claude U-2: B5 Step 2 の FAIL/PASS 内訳 | 対応しない | 実装時に B5 Step 2 で実測して Expected と照合するゲート |
| AUX5-08 | claude U-3: `multipleReferencedCandidates` の案内の具体性 | 対応しない | 案内は危険な操作を勧めない設計どおり。文言の分かりやすさは仕様論点 |
| AUX5-09 | claude T-1: B3 テストのミューテーション確認 | 対応しない | 実装時 Step 確認の言い換え |
| AUX5-10 | claude T-2: B5 Step 2 の内訳照合 | 対応しない | 同上 |
| AUX5-11 | commandcode U-1: 各 Task の Expected 件数 | 対応しない | 実装時の各 Task Step 4 のゲート |
| AUX5-12 | commandcode U-2: B8 Step 2 の FAIL 53/PASS 344 | 対応しない | 実装時の B8 Step 2 のゲート |
| AUX5-13 | commandcode U-3: Task C2 の型・メンバー名 | 対応しない | 実機確認は計画 Task C2 の範囲（ユーザ承認が前提） |
| AUX5-14 | commandcode U-4: 計画コードブロック全体の逐行再読 | 対応しない | 66 操作の再生・12 ケース実行の記録があり、実装時の Task ゲートが確かめる |
| AUX5-15 | commandcode T-1: Task の Expected 照合 | 対応しない | AUX5-11 と同じ |
| AUX5-16 | commandcode T-2: B8 Step 2 の実測 | 対応しない | AUX5-12 と同じ |
| AUX5-17 | commandcode T-3: B7 の 12 ケース実行 | 対応しない | 実装時ゲートの言い換え |
| AUX5-18 | commandcode T-4: I-1 はテスト不要 | 統合 | RF5-03 の扱いに含める |
| AUX5-19 | deepseek U-1: 66 操作のアンカーとビルド | 対応しない | 実装時 Task 0 Step 1・各 Task の停止ゲート |
| AUX5-20 | deepseek U-2: 実機での挙動 | 対応しない | 計画 Task C2 の範囲 |
| AUX5-21 | deepseek T-1: B3 の追加テスト | 対応しない | 計画が既に含むテスト（PLAN:1985） |
| AUX5-22 | deepseek T-2: B5 の追加テスト | 対応しない | 同上（PLAN:2995） |
| AUX5-23 | deepseek T-3: B7 の追加テスト | 対応しない | 同上（PLAN:3742） |
| AUX5-24 | deepseek T-4: 新規指摘に紐づく提案無し | 対応しない | 追加の変更を求めない記述 |
| AUX5-25 | gpt-6-sol T-1: H-1 の手順固定 | 対応しない | RF5-04 で解消済み。接続先指定は計画 C2 に明記済み |
| AUX5-26 | gpt-6-sol T-2: M-1 の中断テスト | 対応しない | RF5-05 で解消済み。B7 のテスト（PLAN:3742）がカバー |
| AUX5-27 | opencode T-1: L-1 の固定確認 | 対応しない | 解消済み項目の確認手順で追加の変更を求めない |
| AUX5-28 | opencode T-2: 将来の `10.0.401` grep | 対応しない | 任意の再発防止提案。現行で裸の記録 0 件を確認済み |
| AUX5-29 | qwen U-1: Spec 3.1・3.2 の上流コード全文照合 | 対応しない | AUX4-27 と同じ。Task 0 と各 Task の停止ゲートが確かめる |
| AUX5-30 | qwen T-1: I-5・I-8 はテスト不要 | 統合 | RF5-06・RF5-07 の扱いに含める |
| AUX5-31 | qwen T-2: 旧 L-2 の任意テスト | 対応しない | RFP-08・RF2-06・RF3-04・RF4-21 で記録済み |

## 6. 対応する項目の修正方針

### F1: REC-2:95 の「文書変更10操作」を実際の操作数に合わせる（RF5-03）

- 変更前: `…source/test に該当する **66操作**を順に適用した。すべての変更アンカーが一意に一致した。文書変更10操作は今回の関連テストに不要なので適用していない。`
- 変更後: `…文書変更12操作（Part A の Task A2・A3 にある 2 操作と、Task B8 の 10 操作）は今回の関連テストに不要なので適用していない。`（前の文は変えない）
- 理由: 文の集計の基準は「現行 PLAN の新規作成・変更指示」全体で、source/test の 66 と同じ母集団では文書の変更は 12 件（PLAN:520・895・3797・3809・3823・3840・3852・3866・3879・3892・3906・3920）。10 と書くと REC-4・grok-4.7 が記録した「78 操作」（66+12）と説明なしに食い違う。内訳を併記して「B8 の 10 操作だけを数えた」読み方も残る数字の意味を残す。
- 却下した案: 「10」のまま「Task B8 の文書変更10操作」とだけ書く案は、文の集計基準（PLAN 全体）と母数がずれて 66+10=76 の誤読を残すため採用しない。
- 検証方法: `git show HEAD:docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md | sed -n '95p'` が新しい文言であること、PLAN の文書 `**変更:**` ヘッダが 12 件であること（本書 §3 で確認済みの値の再掲でよい）、`git diff --check` と `bash scripts/check-layout.sh` が通ること。変更は文書のみで環境用の source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（第 2〜4 回と同じ範囲）。

**仕様論点の記録:** `fields` 進捗は上流の先例に合わせる設計判断（RFP-07・RF2-02・RF3-11・RF4-01）を維持する。D-30 補足の語句（RF5-02）、Spec 8 章の列挙（RF5-06）、過去の回の記録の略記（RF5-07）は変えない。判断保留は無い。

## 7. 実装のチェックリスト

- [ ] `.worktrees/list-shrink-spec`（`docs/list-shrink-recreate-split`）で REC-2 の 95 行目を F1 どおりに直す
- [ ] `git diff --check` と `bash scripts/check-layout.sh` を通す
- [ ] 本書の 8 節に実施記録を書き、F1 の修正と本書を `docs/list-shrink-recreate-split` にコミットする
- [ ] `git fetch origin` で先端を確認してから `git push origin HEAD` で既存 PR #8 へ反映する
- [ ] push 後、PR #8 にレビュー状況・作業判断・作業結果のコメントを作成または更新する

## 8. 実装の記録

- 作業場所: 既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`）。着手時はクリーンで、HEAD は `HEAD5` と一致し、`gh pr view 8` の headRefOid も変わっていなかった。共有ルートの未コミット文書（detached HEAD 上の他タスクの Spec）は取り込んでいない。
- F1: REC-2 の 95 行目を「文書変更10操作は今回の関連テストに不要なので適用していない。」から「文書変更12操作（Part A の Task A2・A3 にある 2 操作と、Task B8 の 10 操作）は今回の関連テストに不要なので適用していない。」へ修正した。それ以外の文・数値（66 操作・全件の記録・SDK の注記）は無変更。
- 検証: `grep -n '文書変更' REC-2` で 95 行目のみが新しい文言になったこと、PLAN の文書 `**変更:**` ヘッダが 12 件（§3 で集計済み）で記録と一致すること、`git diff --check`・`bash scripts/check-layout.sh` が通ったことを確かめた。変更は文書のみで環境用の source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（第 2〜4 回と同じ範囲）。
- コミット・push の結果は PR の状況コメントを参照。
