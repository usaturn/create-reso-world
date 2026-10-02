# PR #8 第4回レビュー修正 Spec

## 1. 状態・目的・範囲

- 状態: **2026-10-02 にユーザ承認済み（「進めて。」）。F1 の文書修正を実施し、本書を PR #8 のブランチにコミットする。F2 の PR 本文更新と状況コメントは push の後に行うため、その最終結果は既存 PR #8 の状況コメントを参照**。
- 対象: https://github.com/usaturn/create-reso-world/pull/8 （OPEN、draft）。
- `PR_REPO`: `usaturn/create-reso-world`。
- `TOPLEVEL` / `MAIN_ROOT`: `/workspaces/reso-world`。origin は `https://github.com/usaturn/create-reso-world.git` と一致。
- 対象ブランチ: `docs/list-shrink-recreate-split`（worktree `.worktrees/list-shrink-spec`）。
- 選別時の現行 HEAD: `913a0f8059170e5e6828dc6530c0fe254181fecb`（以下 `HEAD4`。`gh pr view 8` の headRefOid と `git fetch origin` 後の `origin/docs/list-shrink-recreate-split` が一致することを確認）。
- 正規の入力: `reviews/#8-docs-list-shrink-recreate-split/` 配下の全 9 ファイル。Git の追跡状態にかかわらず入力とした。
- 目的: 現行のコミット済み文書に残る指摘だけを選び、第 3 回の修正の追随漏れ（計画冒頭の SDK 記録、PR 本文）を処理する。
- 成功条件: 「.NET SDK 10.0.401」の記録すべてに `global.json` の pin との関係の注記が付くこと。PR 本文の「ファイル」節が PR の差分のファイルと一致し、「設計の承認状況」が反映済みの回までを記録すること。
- **brainstorming 経路: bounded**。既存の文書（計画）1 行への注記と、既存 PR の本文の更新のみ。コード・公開インターフェース・state 形式は変えない。`review-fix-planning` の指定により bounded でも Spec を保存する。
- 共有ルートの未コミットの Spec・plan、別 worktree の差分、指定ディレクトリ外のレビューは入力にも根拠にもしていない。fork への本実装・実機確認は範囲外。

以下では次の略記を使う。行番号はすべて `HEAD4` のもの。第 2・3 回の記録は同じ略記（`FIRST`・`CURRENT`）を別の対象に使っているため（qwen I-8 の論点）、本書では衝突しない名前にした。略記は本書の中だけで有効である。

- `PLAN`: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- `DESIGN`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`
- `REC-R`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md`（R-01〜R-65 の記録）
- `REC-1`: `docs/superpowers/specs/2026-10-02-pr8-docs-review-fixes-design.md`（PR #8 第 1 回）
- `REC-2`: `docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md`（第 2 回）
- `REC-3`: `docs/superpowers/specs/2026-10-02-pr8-round3-review-fixes-design.md`（第 3 回）
- `BASE`: ResoLoop の `b3a84ae9b4d09cb60a298879e1cf56e3cf0bd888`。

## 2. 入力の固定

| レビュー入力ファイル | 冒頭の対象 HEAD | 履歴・補足 |
| --- | --- | --- |
| `SWE-2-Max.md` | `913a0f805917` | Initial `b851852385b2`、Update `c6749fc01605`・`bf84763825fd`・`913a0f805917` |
| `claude-sonnet-5-5.md` | `913a0f805917` | Initial `c6749fc01605`、Update `bf84763825fd`・`913a0f805917` |
| `deepseek-deepseek-v4.1-flash.md` | `913a0f805917` | Initial `b851852385b2`、Update `913a0f805917` |
| `grok-4.7.md` | `913a0f805917` | Initial `c6749fc01605`、Update `913a0f805917` |
| `opencode-go-muse-spark-1.3-contributor.md` | `913a0f805917` | Initial のみ |
| `qwen3.8-max.md` | `913a0f805917` | Initial `b851852385b2`、Update `bf84763825fd`・`913a0f805917` |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `bf84763825fd` | Initial `c6749fc01605`、Update `bf84763825fd` |
| `xai-grok-4.7.md` | `bf84763825fd` | Initial `b851852385b2`、Update `bf84763825fd` |
| `gpt-6-sol.md` | `c6749fc01605` | Initial のみ |

## 3. 検証方法

- 対象は文書のみの PR で実行対象のコードを含まないため、「現行 HEAD での再現」は `HEAD4` で作った隔離 worktree（`mktemp` 配下、SHA の一致を確認）のコミット済みファイル、`git show 913a0f8:<path>`、`gh pr view 8 --json body` の本文との照合で行った。共有ルートの working tree のファイルは検証根拠に使っていない。検証後に worktree と一時ディレクトリは撤去した。
- 実行の再現を要する指摘は無い。計画のコードの実行結果は、grok-4.7 が `HEAD4` の計画の 78 操作を `BASE` に当てたコピーで記録した結果（Release ビルド警告 0、`RLoop.Tests` 397 件・`RLoop.IntegrationTests` 19 件成功、A の修正前比較 FAIL 11 / PASS 326、B の修正前比較 FAIL 53 / PASS 344）を、補助項目の判定の根拠に使った。本セッションでは再実行していない。

## 4. 正式な全指摘の分類

**28 件: 解消済み 20 / 対応する 4 / 判断保留 0 / 対応しない 4。** 各ファイルの active の指摘と「Resolved findings」節の指摘をすべて数え、同じ内容の複数モデルの指摘も入力単位では落とさない。修正は 2 テーマにまとめる。

| ID | 入力・元ID | 指摘 | 分類 | `HEAD4` の根拠・判断 |
| --- | --- | --- | --- | --- |
| RF4-01 | SWE F-02 | 置き換え元の削除の進捗を `"fields"` 段階で報告する | 対応しない | PLAN:2152 は変わらず `"fields"`。上流の移動元削除の進捗報告に合わせた設計判断で、RFP-07・RF2-02・RF3-11 で 3 回記録済み。レビュー自身も現状維持を推奨。仕様の是非の論点で (a)〜(d) を満たさない |
| RF4-02 | SWE I-2 | PLAN:22 の「.NET SDK 10.0.401」に pin の注記が無い | 対応する (b) | 再現: `10.0.401` の出現は PLAN:22・REC-2:96・REC-2:183 の 3 か所（REC-3 の記述は指摘の引用）で、注記が無いのは PLAN:22 だけ。REC-3 の F3（RF3-21）で (b) と判定した記録の食い違いと同じものが、計画側に残っている。F1 |
| RF4-03 | SWE I-3 | D-30 の補足が「同じ型の key がほかに無い」前提を落としている | 対応しない | DESIGN:480 の D-30 行は、補足の直前の文で同じ型の key がほかにある場合を別の規則として書いている。補足は規範として 7.7 を参照し、計画のコード（PLAN:3241-3243）も 7.7（DESIGN:247-249）と同じく同じ型の key の判定を先に評価する。どちらの分岐でも「候補を削除しない、`supersededId` を除去しない」という結論は同じで、qwen も同じ点を検討して指摘しなかった。索引の語句の精度の問題で、事実誤認とまでは言えず (a)〜(d) を満たさない |
| RF4-04 | SWE F-01 | nullable 参照外し（CS8602）2 か所 | 解消済み | PLAN:422 は `stateComponent!`・`sourceSlot!`。grok-4.7 が `HEAD4` の計画を当てたコピーの Release ビルドで警告 0 を記録 |
| RF4-05 | SWE I-1 | D-30 行が両候補参照の例外を反映していない | 解消済み | DESIGN:480 の末尾に補足が入っている（RF3-19/F1） |
| RF4-06 | claude M-1 | 自己参照テストの引数順が逆 | 解消済み | PLAN:1991 は changed=3 件・initial=4 件。grok-4.7 の 397 件成功の記録に当該テストを含む |
| RF4-07 | claude I-1 | PR 本文が未再生の B3/B4 の変更を述べない | 解消済み | PR 本文 30 行目が、全件再生の対象外のコード変更 2 か所・追加テスト 2 件を明記 |
| RF4-08 | commandcode H-1 | 自己参照テストの引数順が逆 | 解消済み | RF4-06 と同じ指摘 |
| RF4-09 | commandcode H-2 | 書き込みカウンタを戻さず応答喪失が発火しない | 解消済み | PLAN:3006 に `client.ResetWriteCounts();` |
| RF4-10 | deepseek L-1 | PR 本文の検証数値が古い | 解消済み | PR 本文 28-32 行目が 394 件・33 か所・固定 7 件・最終予定 397 件・FAIL 53/PASS 344 を区別して記載 |
| RF4-11 | deepseek I-1 | Spec 冒頭が D-33 を欠く | 解消済み | DESIGN:3 は D-27〜D-33 |
| RF4-12 | gpt H-1 | strict validate と Slot の削除に接続先が無い | 解消済み | PLAN:4215（`validate --strict --url auto --session`）、PLAN:4224（Step 6 の `inspect` と削除を同じ宛先へ）、PLAN:4225（失敗時も同じ宛先確認） |
| RF4-13 | gpt M-1 | 両候補が参照される中断でも削除を案内する | 解消済み | DESIGN:247 の分岐、PLAN:3236-3244 の `multipleReferencedCandidates`、PLAN:3742 の固定テスト |
| RF4-14 | grok H-1 | 自己参照テストの引数順が逆 | 解消済み | RF4-06 と同じ指摘。grok-4.7 自身が `HEAD4` で解消を確認 |
| RF4-15 | muse L-1 | PLAN:22 の「.NET SDK 10.0.401」に pin の注記が無い | 対応する (b) | RF4-02 と同じ指摘。F1 |
| RF4-16 | qwen I-5 | Spec 8 章のテスト列挙が後から追加の 3 件に追随していない | 対応しない | 3 テスト名は DESIGN に 0 件、PLAN の 1985・2995・3742 行にあることを確認。8 章は網羅を主張しておらず誤りではない。RF3-22 と同じ判断で、Info 級の記載漏れのため (a)〜(d) を満たさない |
| RF4-17 | qwen I-6 | PLAN:22 の「.NET SDK 10.0.401」に注記が無い | 対応する (b) | RF4-02 と同じ指摘。F1 |
| RF4-18 | qwen I-7 | PR 本文の「ファイル」節が第 3 回の Spec を欠き、「設計の承認状況」が第 2 回で止まっている | 対応する (b) | 再現: PR の差分は 6 ファイルだが、本文 10-14 行目は 5 ファイルだけを挙げ、REC-3 のファイル名は本文に 1 度も現れない。22 行目は第 2 回までの反映だけを記録する。DESIGN:398 はレビュー修正後に本文を更新する規則を「このリポジトリの PR でも同じ」としている。F2 |
| RF4-19 | qwen I-8 | REC-2 と REC-3 で略記 `FIRST`・`CURRENT` が別の対象を指す | 対応しない | 各文書は 1 節で略記を定義しており、文書の中では一意に解決できる。過去の回の記録で、事実誤認ではなく (a)〜(d) を満たさない。本書では衝突しない略記を使った（1 節） |
| RF4-20 | qwen L-1 | PR 本文の検証数値が古い | 解消済み | RF4-10 と同じ |
| RF4-21 | qwen L-2 | Spec 7.8 の plan フィルターの主張を固定するテスト・確認手順が無い | 解消済み | 懸念の中心（`recreate` が `--changes-only` から漏れる）は `BASE` の `Program.cs`・`Models.cs` の照合で起きないことが REC-R の RFP-08 に記録済みで、レビュー自身も解消とした。保険のテストは RF3-04 で採用しないと記録済み |
| RF4-22 | qwen I-1 | Spec 冒頭が D-33 を欠く | 解消済み | RF4-11 と同じ |
| RF4-23 | qwen I-2 | `SaveSlotIndexes` / `SaveSlotIndexesAsync` の表記の不一致 | 解消済み | DESIGN の出現は 16 件すべて `SaveSlotIndexesAsync` |
| RF4-24 | qwen I-3 | 「392 件中 23 件」が同じ節の 394 件と説明なしに食い違う | 解消済み | REC-R:132 に状態が特定できない旨の注記（RF3-20/F2） |
| RF4-25 | qwen I-4 | REC-2 の「.NET SDK 10.0.401」が `BASE` の pin と両立しない | 解消済み | REC-2:96 に注記、REC-2:183 に参照、PR 本文 31 行目も同期済み（RF3-21/F3）。同じ記録の残りの箇所は RF4-02 で扱う |
| RF4-26 | xai M-1 | NOT_CONVERGED で置き換え元の無い key の `supersededId` が残る | 解消済み | PLAN:2606 で投げる前に片付ける（RFP-05） |
| RF4-27 | xai L-1 | 自己参照があると他の `initialFields` が渡らない | 解消済み | PLAN:2057 は `component.AwaitsVerification ? null : component.Spec.Key`（RFP-06） |
| RF4-28 | xai I-1 | Spec 冒頭が D-33 を欠く | 解消済み | RF4-11 と同じ |

**仕様論点の記録:** `fields` 進捗は上流の先例に合わせる設計判断（RFP-07・RF2-02・RF3-11）を維持する。D-30 の補足の語句（RF4-03）、Spec 8 章の列挙（RF4-16）、過去の回の記録の略記（RF4-19）は変えない。判断保留は無い。

## 5. 未検証候補・付帯提案の扱い

レビューの「Unverified candidates」「Test suggestions」も全件読んだ。正式指摘の修正の検証に当たるものは F1・F2 に統合し、それ以外を念のため追加しない。**29 項目: 解消済み 13 / 対応しない 12 / 正式指摘へ統合 4。**

| ID | 入力・項目 | 分類 | 根拠・扱い |
| --- | --- | --- | --- |
| AUX4-01 | SWE V-1: 追加 2 テストの書き込み位置 | 解消済み | レビュー自身が終了扱い。grok-4.7 の `HEAD4` での 397 件成功に両テストを含む |
| AUX4-02 | SWE V-2: B8 の件数（397 件中 FAIL 53 / PASS 344、B 追加 60 件）の独立再集計 | 解消済み | grok-4.7 が `HEAD4` の計画を当てたコピーで `src/` を A に戻して FAIL 53 / PASS 344 を実測し、PASS 予定の 7 件が失敗リストに無いことを記録 |
| AUX4-03 | SWE V-3: 既存テストが B5 の前に PASS する主張、上流提出手順 | 対応しない | 差分の無い範囲の未検証候補で、誤動作・事実誤認は示されていない。Task ごとの Expected が実装時に確かめる |
| AUX4-04 | SWE V-4: B7 theory の「参照候補 1 件以下」が書き込み順に依存する | 解消済み | grok-4.7 の `HEAD4` での 397 件成功に B7 の theory を含む |
| AUX4-05 | SWE T-1: `fields` 進捗のキャプチャテスト | 対応しない | RF4-01 と同じ判断 |
| AUX4-06 | SWE T-2: I-2・I-3 は文書の修正で対応できる | 正式指摘へ統合 | I-2 は F1、I-3 は RF4-03 の判断に含める |
| AUX4-07 | claude U-1: `Test.Renderer` の `Enabled` が偽クライアントに無いかもしれない | 解消済み | grok-4.7 の 397 件成功、commandcode の 12 ケース成功に `Enabled=true` のアサートを含む |
| AUX4-08 | claude U-2: B5 Step 2 の「17 件のうち 16 件が FAIL」の内訳 | 対応しない | 算術の不整合は示されていない。実装時の B5 Step 2 の数え合わせに委ねる |
| AUX4-09 | claude U-3: 案内文に張り替えの具体的な操作が無い | 対応しない | 案内は Resonite 上で参照先を確かめて張り替える手順を示し、危険な操作を勧めない。文言の分かりやすさの提案で実害は無い（AUX-07 と同じ） |
| AUX4-10 | claude T-1: 自己参照の除外を戻すと FAIL することの確認 | 解消済み | REC-2 の 9 節がこのミューテーションを記録済み |
| AUX4-11 | claude T-2: B5 Step 2 の内訳の照合 | 対応しない | AUX4-08 と同じ |
| AUX4-12 | commandcode U-1: Task ごとの中間 Expected の件数 | 対応しない | 最終 397 件と A4 の比較（FAIL 11 / PASS 326）は grok-4.7 が実測で一致。Task ごとの全件実測は実装時の既存のゲート |
| AUX4-13 | commandcode U-2: B8 Step 2 の FAIL 53 / PASS 344 の実測 | 解消済み | AUX4-02 と同じ |
| AUX4-14 | commandcode U-3: C2 の型・メンバー名が実機と違う可能性 | 対応しない | C2 自体が `type search` / `type describe` での確認と、相違時に止まる条件を含む。ユーザの指示の下で実施する |
| AUX4-15 | commandcode T-1: B7 の 12 ケースを実装時に実行する | 対応しない | 実装時の Task ゲートの再掲 |
| AUX4-16 | commandcode T-2: B8 Step 2 の実測照合 | 解消済み | AUX4-02 と同じ |
| AUX4-17 | commandcode T-3: 各 Task の Expected の件数照合 | 対応しない | AUX4-12 と同じ |
| AUX4-18 | deepseek U-1: 計画の目印の一意性とビルドの独立した裏付け | 解消済み | grok-4.7 が `HEAD4` の 78 操作で目印が 1 か所だけ一致し、Release ビルド警告 0 を記録 |
| AUX4-19 | deepseek U-2: 実機でのリスト縮小の挙動が未確認 | 対応しない | 計画 Task C2 が実施条件（ユーザの明示的な指示）と判定手順を規定済み |
| AUX4-20 | deepseek T-1: B3 の自己参照テスト | 解消済み | PLAN:1985 に追加済み。grok-4.7 の 397 件成功に含む |
| AUX4-21 | deepseek T-2: B5 の NOT_CONVERGED テスト | 解消済み | PLAN:2995 に追加済み。同上 |
| AUX4-22 | deepseek T-3: B7 の両候補参照テスト | 解消済み | PLAN:3742 に追加済み。同上 |
| AUX4-23 | gpt T-1: strict validate と削除の接続先を固定する | 解消済み | RF4-12 と同じ根拠 |
| AUX4-24 | gpt T-2: 両候補参照の中断を固定するテスト | 解消済み | RF4-13 と同じ根拠 |
| AUX4-25 | muse T-1: PLAN:22 に注記が入り、他の数値が変わらないことを確認する | 正式指摘へ統合 | F1 の検証に含める |
| AUX4-26 | muse T-2: 注記の無い SDK 表記が残っていないことを grep で確かめる | 正式指摘へ統合 | F1 の検証に含める |
| AUX4-27 | qwen U-1: Spec 3.1・3.2 の上流コードの記述の全文照合 | 対応しない | AUX-13 と同じ判断。grok-4.7 の 78 操作の目印一致と全件成功が計画の前提を裏付ける。残りは Task 0 と各 Task の停止ゲートが確かめる |
| AUX4-28 | qwen T-1: I-5〜I-8 はテスト不要 | 正式指摘へ統合 | 各本件（RF4-16〜RF4-19）の扱いに含める |
| AUX4-29 | qwen T-2: plan フィルターの任意のテスト | 対応しない | RF3-04 と同じ判断 |

合計の内訳: 正式 28 件 + 補助 29 項目 = 57 項目（解消済み 33 / 対応する 4 / 判断保留 0 / 対応しない 16 / 統合 4）。

## 6. 修正方針と検証方法

### F1: 計画冒頭の SDK 記録に pin との関係の注記を足す（RF4-02・RF4-15・RF4-17）

- 根拠: **(b)** PLAN:22 の「12ケースすべてが成功した（.NET SDK 10.0.401）」は、REC-2:96・183 と同じ実行の記録だが、第 3 回の F3 の注記が及んでいない。`BASE` の `global.json` は `10.0.201`・`latestPatch` で一時コピーに含まれ、`latestPatch` は同じフィーチャバンド（10.0.2xx）の中でしか解決しないため、コピーの内側で実行したなら 10.0.401 にはならない。計画は実装者が単独で読む文書であり、PLAN:9 の Tech Stack（SDK 10.0.201）とも説明なしに食い違う。
- 方針: PLAN:22 の括弧を次のようにする。数値は変えない。

  変更前:

  ```markdown
  12ケースすべてが成功した（.NET SDK 10.0.401）。
  ```

  変更後:

  ```markdown
  12ケースすべてが成功した（.NET SDK 10.0.401。この値は pin の対象外の cwd で測ったホスト側の値の可能性があり、一時コピーの内側で実行した dotnet には `global.json`（10.0.201・`latestPatch`）により 10.0.2xx 系が解決される。実装時の Task ゲートは pin の内側で実行する）。
  ```
- 検証:
  - `git diff` で変更が PLAN:22 の括弧の中だけであることを確かめる。
  - `grep -rn "10\.0\.401" docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md docs/superpowers/specs/2026-10-0[12]-*.md` の各出現が、注記を持つか、注記を参照するか、指摘の引用であることを確かめる。
  - 同じ段落のほかの数値（66 操作、12 ケース、397 件）が変わっていないことを確かめる。

### F2: PR 本文の「ファイル」節と「設計の承認状況」を更新する（RF4-18）

- 根拠: **(b)** PR 本文の「ファイル」節は 5 ファイルだけを挙げ、PR の差分にある REC-3 を欠く。「設計の承認状況」は第 2 回までの反映だけを記録する。DESIGN:398 は、レビュー修正の後に PR 本文を更新する規則をこのリポジトリの PR にも適用するとしている。
- 方針:
  - 本書（`docs/superpowers/specs/2026-10-02-pr8-round4-review-fixes-design.md`）は、第 2・3 回と同じく PR #8 のブランチにコミットする。
  - 「ファイル」節の末尾に次の 2 行を足す。
    - `docs/superpowers/specs/2026-10-02-pr8-round3-review-fixes-design.md`（第3回の選別と、D-30 の補足・検証記録2箇所の注記の記録）
    - `docs/superpowers/specs/2026-10-02-pr8-round4-review-fixes-design.md`（第4回の選別と、計画冒頭の SDK 記録の注記・この本文の更新の記録）
  - 「設計の承認状況」の最後の項目の末尾に次の 2 文を足す。
    - 「第3回では全8レビューを照合し、正式22件を解消済み16・対応3・対応しない3に選別し、決定事項 D-30 の補足と検証記録2箇所の注記を追加しました。第4回では全9レビューを照合し、正式28件を解消済み20・対応4（2テーマ）・対応しない4に選別し、計画冒頭の SDK 記録への注記とこの本文の更新を行いました。」
  - 本文のほかの節は変えない。`gh pr edit 8 --repo usaturn/create-reso-world --body-file <file>` で更新し、本文のファイルは一時ディレクトリに置く。
- 検証:
  - `gh pr view 8 --json body` の「ファイル」節のファイルと、`gh pr diff 8 --name-only` の 7 ファイル（本書を含む）が一致することを確かめる。
  - 更新前後の本文の差分が上の 3 か所（2 行と 2 文）だけであることを確かめる。

## 7. 承認後の反映と停止条件

1. 実装対象は PLAN:22 の注記（F1）、本書のコミット、既存 PR #8 の本文（F2）のみ。fork のソース・計画のコード・実機は触らない。
2. 作業場所は既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`、選別時の HEAD は `HEAD4` と一致）。着手前に `git fetch origin` と `gh pr view 8 --json headRefOid` で PR の先端を確かめ、変わっていれば今回の該当箇所だけ新しい HEAD で照合し直す。
3. 検証は 6 節の確認、`git diff --check`、`bash scripts/check-layout.sh`。変更は文書のみで環境用の source/tests に及ばないため、`bash .devcontainer/run-tests.bash` は実施しない（第 2・3 回と同じ範囲）。
4. 検証が失敗したら修正し、commit しない。全ワールドのテストや fork の全件の再実行を commit / push の条件にしない。
5. 検証の後、**`docs/list-shrink-recreate-split` に commit して既存 PR #8 に push** する。新しい review-fixes ブランチや PR は作らない。PR が open でなければ作らずに止まる。
6. push の後、F2 の本文更新を行い、`$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py` で日本語の review-fix-planning の状況コメントを作成または更新する（`MODEL_NAME` は `claude-opus-5-5`）。他のエージェントのコメントは編集しない。
7. 本書の 1 節の「状態」と 8 節のチェックリストを、承認と実施の結果に合わせて更新してからコミットする。

## 8. 作業チェックリスト

- [x] 全 9 レビュー入力と各対象 HEAD を固定
- [x] 現行 PR / リポジトリ / ブランチ / HEAD を確認（`gh pr view`・`git fetch origin`）
- [x] `HEAD4` の隔離 worktree・`git show`・`gh` の本文で各指摘を検証（共有ルートの working tree は不使用）。worktree と一時ディレクトリは撤去済み
- [x] 正式 28 件と補助 29 項目を 4 区分に分類
- [x] brainstorming の bounded 経路で修正方針を整理
- [x] ユーザの明示的な承認（2026-10-02、「進めて。」）
- [x] F1 の実施と検証
- [ ] commit / push、F2 の PR 本文の更新、状況コメント（本書のコミットより後に行うため、結果は PR #8 の状況コメントに残す）

## 9. 承認後の実装・検証記録（2026-10-02）

- 作業場所: 既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`）。着手時はクリーンで、HEAD は `HEAD4` と一致し、`gh pr view 8` の headRefOid も変わっていなかった。共有ルートの未コミット文書は本書以外取り込んでいない。
- F1: PLAN:22 の括弧を 6 節の変更後の文言にした。数値は変えていない。
- 検証: `git diff` で PLAN の変更が 22 行目の括弧の中だけであること、`10.0.401` の各出現が注記・注記の参照・指摘の引用のいずれかであることを確かめた。`git diff --check` と `bash scripts/check-layout.sh` を worktree で実行した。変更は文書のみで環境用の source/tests に及ばないため、`bash .devcontainer/run-tests.bash` は実施しない（第 2・3 回と同じ範囲）。
- F2 の本文更新、commit / push、状況コメントの結果は既存 PR #8 の状況コメントに残す。
