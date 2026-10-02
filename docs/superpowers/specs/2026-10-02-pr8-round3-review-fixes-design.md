# PR #8 第3回レビュー修正 Spec

## 1. 状態・目的・範囲

- 状態: **2026-10-02 にユーザ承認済み（「進めてください。」）。F1〜F3 の文書修正を実施した。commit / push / PR 更新の最終結果は既存 PR #8 の状況コメントを参照**。
- 対象: https://github.com/usaturn/create-reso-world/pull/8 （OPEN）。
- `PR_REPO`: `usaturn/create-reso-world`。
- `TOPLEVEL` / `MAIN_ROOT`: `/workspaces/reso-world`。origin は `https://github.com/usaturn/create-reso-world` と一致。
- 対象ブランチ: `docs/list-shrink-recreate-split`。
- 選別時の現行 HEAD: `bf84763825fd4fb03e5b267b132136227e92a9b8`（以下 `CURRENT`。`gh pr view 8` の headRefOid と `git fetch origin pull/8/head` の FETCH_HEAD で一致を確認）。
- 正規の入力: `reviews/#8-docs-list-shrink-recreate-split/` 配下の全 8 ファイル。Git の追跡状態にかかわらず入力とした。
- 目的: 現行のコミット済み文書・計画に残る指摘だけを選び、残る Info 級の記録の食い違いを処理する。
- 成功条件: 決定事項テーブル（12 章）が session-changed の現行の復旧規則を正しく索引すること、検証記録の数値が後の読者を再び照合作業に走らせないこと。
- **brainstorming 経路: bounded**。既存の文書（設計 Spec の決定事項表・2 件のレビュー修正記録）への注記と PR 本文 1 行の修正のみ。コード・公開インターフェース・state 形式は変えない。`review-fix-planning` の指定により bounded でも Spec を保存する。
- 未コミットの既存 Spec・plan（`docs/superpowers/plans/2026-09-30-...-round6-...`、`docs/superpowers/specs/2026-09-29-asset-url-...` の untracked 2 件）、別 worktree の差分、指定ディレクトリ外のレビューは入力にも根拠にもしていない。fork への本実装・実機確認は範囲外。

以下では次の略記を使う。行番号はすべて `CURRENT` のもの。

- `PLAN`: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- `DESIGN`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`
- `FIRST`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md`
- `SECOND`: `docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md`
- `BASE`: ResoLoop の `b3a84ae9b4d09cb60a298879e1cf56e3cf0bd888`。`external/resoloop` のコミット済み blob だけを参照した。

## 2. 入力の固定

| レビュー入力ファイル | 冒頭の対象 HEAD | 履歴・補足 |
| --- | --- | --- |
| `SWE-2-Max.md` | `bf84763825fd` | Initial `b851852385b2`、Update `c6749fc01605`・`bf84763825fd` |
| `deepseek-deepseek-v4.1-flash.md` | `b851852385b2` | Initial のみ |
| `qwen3.8-max.md` | `bf84763825fd` | Initial `b851852385b2`、Update `bf84763825fd` |
| `xai-grok-4.7.md` | `bf84763825fd` | Initial `b851852385b2`、Update `bf84763825fd` |
| `claude-sonnet-5-5.md` | `bf84763825fd` | Initial `c6749fc01605`、Update `bf84763825fd` |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `bf84763825fd` | Initial `c6749fc01605`、Update `bf84763825fd` |
| `gpt-6-sol.md` | `c6749fc01605` | Initial のみ |
| `grok-4.7.md` | `c6749fc01605` | Initial のみ |

## 3. 検証方法

- 対象は文書のみの PR で実行対象のコードを含まないため、「現行 HEAD での再現」は `git show bf84763825fd:<path>` のコミット済み blob、`gh pr view 8` の本文、上流 `BASE` のコミット済み blob（`global.json`・`Program.cs` 等）との照合で行った。working tree のファイルは検証根拠に使っていない。
- 挙動の再現を要する指摘は残っていない（前回までに隔離コピーでの再現が記録済み。残る指摘はすべて文書記述の照合で判定できる）。今回は worktree 検証を行っていないため撤去対象の一時環境は無い。

## 4. 正式な全指摘の分類

**22 件: 解消済み 16 / 対応する 3 / 判断保留 0 / 対応しない 3。** 同一内容の複数モデルの指摘も入力単位では落とさず数える。修正は 3 テーマにまとめる。

| ID | 入力・元ID | 指摘 | 分類 | `CURRENT` の根拠・判断 |
| --- | --- | --- | --- | --- |
| RF3-01 | deepseek L-1 | PR 本文の検証数値・決定事項範囲が古い | 解消済み | `gh pr view 8` の本文が 394 件・33 箇所・固定 7 件・D-1〜D-33・最終予定 397 件・FAIL 53/PASS 344 を記載済み。DESIGN:398 に再発防止の「このリポジトリの PR でも同じ」も追加済み（RFP-01） |
| RF3-02 | deepseek I-1 | Spec 冒頭が D-33 を欠く | 解消済み | `CURRENT` の DESIGN:3 は D-27〜D-33（RFP-02） |
| RF3-03 | qwen L-1 | PR 本文の旧数値 | 解消済み | RF3-01 と同一指摘。同じ本文照合で解消を確認 |
| RF3-04 | qwen L-2 | plan フィルター主張を固定するテスト・確認手順がない | 対応しない | RFP-08・RF2-06 で記録済み。`BASE` の `Program.cs`・`Models.cs` 照合で Spec 7.8 の主張自体は正しい。残るのは保険のテスト追加のみで (a)〜(d) を満たさない |
| RF3-05 | qwen I-1 | Spec 冒頭が D-33 を欠く | 解消済み | RF3-02 と同一指摘 |
| RF3-06 | qwen I-2 | `SaveSlotIndexes` / `SaveSlotIndexesAsync` の表記不一致 | 解消済み | `CURRENT` の DESIGN に非 Async の単独表記 0 件を grep で確認（RFP-04） |
| RF3-07 | xai M-1 | NOT_CONVERGED で置き換え元の無い key の `supersededId` が残る | 解消済み | `CURRENT` の PLAN:2309 が投げる前の片付け（index 保存・`supersededId` 消去・checkpoint）を規定（RFP-05） |
| RF3-08 | xai L-1 | 自己参照で他の `initialFields` が渡らない | 解消済み | `CURRENT` の PLAN:2057 は `component.AwaitsVerification ? null : component.Spec.Key`（RFP-06） |
| RF3-09 | xai I-1 | Spec 冒頭が D-33 を欠く | 解消済み | RF3-02 と同一指摘 |
| RF3-10 | SWE F-01 | nullable 参照外し（CS8602）2 箇所 | 解消済み | `CURRENT` の PLAN:422・3069・3098・3119 は `stateComponent!`。3070 行は同一式内で `!` 適用後の参照で警告にならない（commandcode が修正後計画の適用コピーでビルド 0 警告を確認） |
| RF3-11 | SWE F-02 | 置き換え元削除の進捗が `"fields"` | 対応しない | RFP-07・RF2-02 で「上流の移動元削除の進捗報告（`BASE` の WorldService.cs）に合わせる」設計判断を 2 回記録済み。レビュー自身も現状維持を推奨。仕様の是非の論点であり (a)〜(d) を満たさない |
| RF3-12 | claude M-1 | 自己参照テストの引数順が逆 | 解消済み | `CURRENT` の PLAN:1990-1991 は changed=3 件・initial=4 件（RF2-12/F1） |
| RF3-13 | claude I-1 | PR 本文が未再生の B3/B4 変更を述べない | 解消済み | `gh pr view 8` の本文 28-32 行が過去の全件再生・後からのコード変更 2 箇所・第 2 回の 12 ケース・予定件数を区別（RF2-13/F5） |
| RF3-14 | commandcode H-1 | 自己参照テストの引数順が逆 | 解消済み | RF3-12 と同一指摘（RF2-14/F1） |
| RF3-15 | commandcode H-2 | Writes リセット無しで応答喪失が発火しない | 解消済み | `CURRENT` の PLAN:3006 に `client.ResetWriteCounts();`（RF2-15/F2） |
| RF3-16 | gpt H-1 | strict validate / slot delete に接続先が無い | 解消済み | `CURRENT` の PLAN C2 Step 3〜6・失敗時の後片付けが `--url auto --session <SessionId>`（明示 URL 経路では確認済み URL）を明記（RF2-16/F3） |
| RF3-17 | gpt M-1 | 両候補が参照される中断でも削除を案内する | 解消済み | `CURRENT` の DESIGN:247-248・PLAN:3236 の `multipleReferencedCandidates` 分岐と B7 の固定テスト（RF2-17/F4） |
| RF3-18 | grok H-1 | 自己参照テストの引数順が逆 | 解消済み | RF3-12 と同一指摘（RF2-18/F1） |
| RF3-19 | SWE I-1 | D-30 行が両候補参照の例外を反映していない | 対応する (b) | `CURRENT` で再現: DESIGN:480 の D-30 行は「管理 Component の参照が今指している方を残す」規則のままだが、247-248 行には第 2 回修正（RF2-17/F4）で決定・実装済みの「`referencedBy` が空でない候補が 2 件以上なら削除・`supersededId` 除去を案内しない」分岐がある。決定事項の索引が現行の復旧規則を正しく記録していない事実誤認。F1 |
| RF3-20 | qwen I-3 | 「392 件中 23 件が失敗」が同じ節の 394 件と説明なしに食い違う | 対応する (b) | `CURRENT` で再現: FIRST:129-130 は最終 394 件、FIRST:132 は 392 件を記録し、差の 2 件の説明が 5 文書のどこにもない検証記録の不整合。ユーザ確認で当時のツリー状態は不明・再現不可と判明。F2 |
| RF3-21 | qwen I-4 | round2 Spec の「.NET SDK 10.0.401」が BASE の pin と両立しない | 対応する (b) | `CURRENT` で再現: SECOND:96・183 が `10.0.401` と記録するが、`BASE` の `global.json` は `10.0.201`・`latestPatch` で replay コピーに同梱される。`latestPatch` は同一フィーチャバンド（10.0.2xx）内でのみ解決し、`dotnet --list-sdks` は 10.0.201・10.0.401 の両方が導入済み。記録どおりコピーの内側で実行したなら解決値は 10.0.201 になり記録と矛盾し、外側から実行したならその旨の記録が無い。PR 本文 31 行にも同じ記述。F3 |
| RF3-22 | qwen I-5 | Spec 8 章のテスト列挙が後から追加の 3 件に追随していない | 対応しない | `CURRENT` の DESIGN 8 章に 3 テスト名・対応シナリオが無いことは確認したが、8 章は網羅を主張しておらず誤りではない（レビュー自身も明記）。Info 級の記載漏れで (a)〜(d) を満たさない |

**仕様論点の記録:** `fields` 進捗は上流先例に合わせる設計判断（RFP-07・RF2-02）を維持。plan フィルターの追加テスト、Spec 8 章の列挙追加は含めない。判断保留はない。

## 5. 未検証候補・付帯提案の扱い

レビューの「Unverified candidates」「Test suggestions」も全件読んだ。正式指摘の修正に直接必要な検証は F1〜F3 に統合し、それ以外を念のため追加しない。**27 項目: 解消済み 9 / 対応しない 16 / 正式指摘へ統合 2。**

| ID | 入力・項目 | 分類 | 根拠・扱い |
| --- | --- | --- | --- |
| AUX-01 | SWE V-1: 追加 2 テストの書き込み位置 | 解消済み | commandcode が `CURRENT` の計画の 66 操作適用コピーで関連 12 ケースを実行し両テスト PASS（LoseResponseOnWrite の位置も記録どおり） |
| AUX-02 | SWE V-2: B8 件数の独立再集計 | 対応しない | 算術は整合。不一致という事実は示されていない。実装時の B8 Step 2 の既存ゲートに委ねる |
| AUX-03 | SWE V-3: 既存テストの B5 前 PASS 主張・上流提出手順の持ち越し | 対応しない | 差分の無い範囲の未検証候補。現行の誤動作・事実誤認は示されていない |
| AUX-04 | SWE V-4: B7 theory の「参照候補 ≤ 1」が書き込み順に依存 | 対応しない | watcher が同じ apply で作られる構造と整合。実装時の B7 Step 2 の Expected（10 件）が最終確認 |
| AUX-05 | claude U-1: `Test.Renderer` の `Enabled` が偽クライアントに未登録かも | 解消済み | RF2 の AUX-06 と同じ結論。commandcode の 12 ケース実行で `Enabled=true` のアサートが成功済み |
| AUX-06 | claude U-2: B5 Step 2 の FAIL/PASS 内訳 | 対応しない | 算術不整合なし。実装時の Step 2 の数え合わせに委ねる |
| AUX-07 | claude U-3: 新しい案内文に張り替えの具体コマンドが無い | 対応しない | 案内文は Resonite 上で参照先を確認・張り替える手順を指示しており、resoloop CLI の有無は問題の前提にならない。文言の分かりやすさの提案で実害なし（Info 以下） |
| AUX-08 | commandcode U-1: Task ごとの中間 Expected | 対応しない | 最終 397 件と関連 12 ケースは一致済み。Task 別の全件実測は実装時の既存ゲート |
| AUX-09 | commandcode U-2: B8 Step 2 の FAIL 53/PASS 344 実測 | 対応しない | AUX-02 と同じ。実装時の Step 2 の手順に委ねる |
| AUX-10 | commandcode U-3: C2 の型・メンバー名が実機と違う可能性 | 対応しない | C2 自体が `type search`/`type describe` での確認と相違時の停止を手順に含む。ユーザ承認後の実施 |
| AUX-11 | deepseek U-1: 計画のアンカー・ビルドの独立裏付け | 解消済み | commandcode が `CURRENT` で source/test 66 操作のアンカー一意一致とビルド 0 警告を確認 |
| AUX-12 | deepseek U-2: 実機でのリスト縮小の挙動未確認 | 対応しない | 計画 Task C2 が実施条件（ユーザの明示的な指示）と判定手順を規定済み。未承認の実機操作はしない |
| AUX-13 | qwen U-1: Spec 3.1・3.2 の上流全文照合 | 対応しない | 抜取照合（`BuildComponentPlans`・`Program.cs`・`Models.cs`）は一致。全文再照合は保険で、計画の Task 0・各 Task の停止ゲートが残りを確かめる |
| AUX-14 | SWE T-1: `fields` 進捗のキャプチャテスト | 対応しない | RF3-11（F-02）の「対応しない」判断と同じ |
| AUX-15 | SWE T-2: D-30 行の補足 | 正式指摘へ統合 | RF3-19 の修正方法そのもの |
| AUX-16 | claude T-1: 自己参照除外を戻すと FAIL する確認 | 解消済み | SECOND §9 がミューテーション（除外を戻すと `Enabled=false` で FAIL）を記録済み |
| AUX-17 | claude T-2: B5 Step 2 の内訳照合 | 対応しない | AUX-06 と同じ |
| AUX-18 | commandcode T-1: B7 の 12 ケースを実装時に実行 | 対応しない | 実装時の Task ゲートの再掲。新しい一括再生を条件にしない |
| AUX-19 | commandcode T-2: B8 Step 2 の実測照合 | 対応しない | AUX-09 と同じ |
| AUX-20 | commandcode T-3: 各 Task の Expected 件数照合 | 対応しない | AUX-08 と同じ |
| AUX-21 | deepseek T-1: 数値更新時に PR 本文も更新する手順の追加 | 解消済み | DESIGN:398 に「（このリポジトリの PR でも同じ）」追加済み（RFP-01） |
| AUX-22 | deepseek T-2: Spec 冒頭の D-33 修正 | 解消済み | RF3-02 の修正済みと同じ |
| AUX-23 | qwen T-1: I-3/I-4/I-5 にテスト不要の注記 | 正式指摘へ統合 | 各本件（RF3-20・RF3-21・RF3-22）の扱いに含める |
| AUX-24 | qwen T-2: plan フィルターの任意テスト | 対応しない | RF3-04（L-2）と同じ判断 |
| AUX-25 | gpt T-1: strict validate / 削除の接続先を固定 | 解消済み | RF3-16（F3）で反映済み |
| AUX-26 | gpt T-2: 両候補参照の中断を固定するテスト | 解消済み | RF3-17（F4）で新 Fact 追加済み |
| AUX-27 | grok T-1: 自己参照テストの引数を直す | 解消済み | RF3-12（F1）で修正済み |

合計の内訳: 正式 22 件 + 補助 27 項目 = 49 項目（解消済み 25 / 対応する 3 / 判断保留 0 / 対応しない 19 / 統合 2）。

## 6. 修正方針と検証方法

### F1: D-30 行に両候補参照の例外を追記する（RF3-19）

- 根拠: **(b)** 決定事項の索引（DESIGN:480）が、247-248 行に実装済みの「`referencedBy` が空でない候補が 2 件以上なら削除・`supersededId` 除去を案内しない」分岐を記録していない。テーブルだけを読むと復旧規則の例外が欠落する。
- 方針: D-30 行のセルの末尾に「（補足: `referencedBy` が空でない候補が 2 件以上ある場合は、候補の削除や `supersededId` の除去を案内せず、参照元の確認と張り替えを先に行う。第 2 回レビュー修正）」程度の 1 文を足す。新しい D- 番号は振らない（第 2 回修正の記録は SECOND にあり、ここは索引の追随）。
- 検証: `git show` で修正後の D-30 行が例外を含むこと、247-248 行の規範テキストと条件・結論が一致することを目視確認。

### F2: 「392 件」の比較記録に状態が特定不能である旨を注記する（RF3-20）

- 根拠: **(b)** FIRST:132 の「392 件中 23 件が失敗」は同じ節の最終 394 件（129-130 行）と説明なしに食い違い、後の読者に照合作業を強いる検証記録の不整合。
- 方針: ユーザ確認で当時のツリー状態は不明・再現不可と判明したため、数値を捏造せず「この比較を実行した時点のツリー状態は記録に残っておらず、母数 392 と最終の 394 件の関係は後から再導出できない」旨を括弧の後に 1 文注記する。使い捨て環境の記録なので数値そのものは変更しない。
- 検証: `git show` で FIRST:132 に注記が入ること、他の数値記録（394・53/344 など）に変更が無いことを確認。

### F3: SDK 記録「10.0.401」の再現性の注記と PR 本文の同期（RF3-21）

- 根拠: **(b)** SECOND:96・183 と PR 本文 31 行の「.NET SDK 10.0.401」は、`BASE` の `global.json`（`10.0.201`・`latestPatch`）が replay コピーに同梱される以上、記録どおりコピーの内側で実行したなら解決値は 10.0.2xx 系（この環境では 10.0.201）であり、記録と両立しない。
- 方針: ユーザ確認で実行 cwd は不明と判明したため、SECOND §5（96 行付近）に「記録の 10.0.401 は pin の対象外の cwd で測ったホスト側の値の可能性があり、replay コピーの内側で実行した dotnet は `global.json`（10.0.201・latestPatch）により 10.0.2xx 系が解決される。実装時の Task ゲート（pin の内側で実行）が本番の検証になる」旨を 1〜2 文注記する。§9（183 行）の括弧にも「同上」の短い参照を足す。PR 本文 31 行の同じ記述も `gh pr edit 8 --body-file` で同期する。
- 検証: `git show` で SECOND の 2 箇所に注記が入ること、`gh pr view 8 --json body` で本文 31 行が注記と矛盾しない表現になっていることを確認。

## 7. 承認後の反映と停止条件

1. 実装対象は DESIGN・FIRST・SECOND の上記 3 テーマの注記と、既存 PR #8 の本文のみ。fork のソース・計画コード・実機は触らない。
2. 作業場所は既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`、HEAD は `CURRENT` と一致）。着手前に `git fetch origin` と `gh pr view 8 --json headRefOid` で PR の先端を再確認し、変わっていれば今回の該当箇所だけ新 HEAD で照合する。
3. 検証は `git show` による文書照合、`git diff --check`、`bash scripts/check-layout.sh`。変更は文書のみで環境用の source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（前回と同じ範囲）。
4. 検証が失敗したら修正し、commit しない。全ワールドのテスト・fork 全件再実行を commit/push の追加条件にしない。
5. 検証後は **`docs/list-shrink-recreate-split` に commit して既存 PR #8 に push** する。新しい review-fixes branch / PR を作らない。open な PR が無ければ作らず停止する。
6. push 後は正確な実行モデル識別子を取得し、`$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py` で日本語の review-fix-planning 状況コメントを更新する。他エージェントのコメントを編集しない。

## 8. 作業チェックリスト

- [x] 全 8 レビュー入力と各対象 HEAD を固定
- [x] 現行 PR / リポジトリ / ブランチ / HEAD を確認（`gh pr view`・`git fetch origin pull/8/head`）
- [x] `git show <HEAD>:<path>` のコミット済み blob と `gh` の本文で各指摘を検証（working tree 未使用）
- [x] 全正式指摘と補助項目を 4 区分へ分類（判断保留は実行者しか答えられない事実確認のため `ask_user_question` で回答済み。I-3・I-4 とも「不明」→ 正直な注記に決定）
- [x] brainstorming の bounded 経路で修正方針を整理
- [x] ユーザの明示承認（2026-10-02、「進めてください。」）

## 9. 承認後の実装・検証記録（2026-10-02）

- 作業場所: 既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`）。着手時はクリーンで、HEAD は選別時の `CURRENT` と一致。共有ルートの未コミット文書は取り込まなかった。
- F1: DESIGN の D-30 行（480 行）の決定セル末尾に「補足: `referencedBy` が空でない候補が 2 件以上ある場合は、候補の削除や `supersededId` の除去を案内せず、参照元の確認と張り替えを先に行う（第 2 回レビュー修正、7.7）」を追記。
- F2: FIRST:132 の括弧内に「この比較を実行した時点のツリー状態は記録に残っておらず、母数の 392 と上の最終の 394 件の関係は後から再導出できない」を追記。数値は変更していない。
- F3: SECOND:96 に SDK 値が pin 対象外の cwd のホスト側の値の可能性と、コピー内側では `global.json` により 10.0.2xx が解決される注記を追加。SECOND:183 に「5 の注記どおり」の参照を追加。PR 本文 31 行は `gh pr edit` で同期。
- 検証: `git diff --check` と `bash scripts/check-layout.sh` を worktree で実行。変更は文書のみで環境用 source/tests に及ばないため `bash .devcontainer/run-tests.bash` は実施しない（第 2 回と同じ範囲）。
- commit / push・PR 本文更新・状況コメントの結果は既存 PR #8 の状況コメントに残す。
