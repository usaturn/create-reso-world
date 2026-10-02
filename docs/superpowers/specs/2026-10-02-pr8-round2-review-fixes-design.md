# PR #8 第2回レビュー修正 Spec

## 1. 状態・目的・範囲

- 状態: **2026-10-02にユーザ承認済み。5テーマの文書・計画修正と関連検証を実施した。commit / push / PR 更新の最終結果は既存 PR #8 の状況コメントを参照**。
- 対象: https://github.com/usaturn/create-reso-world/pull/8 （OPEN）。
- `PR_REPO`: `usaturn/create-reso-world`。
- `TOPLEVEL` / `MAIN_ROOT`: `/workspaces/reso-world`。origin は `https://github.com/usaturn/create-reso-world.git` と一致。
- 対象ブランチ: `docs/list-shrink-recreate-split`。
- 選別時の現行 HEAD: `c6749fc016053ff1d98274ee4d6225c83067f4fb`（以下 `CURRENT`）。計画時の取得・検証終了時と承認後の着手時に GitHub の HEAD と一致した。以下の分類表はこの時点での裁定を保存している。
- 旧レビュー HEAD: `b851852385b27299f02d4cfcb526295b75f0cd34`（以下 `PREVIOUS`）。
- 正規の入力: `reviews/#8-docs-list-shrink-recreate-split/` 配下の全8ファイル。Git の追跡状態にかかわらず入力とした。
- 目的: 現行のコミット済み文書・計画に残る指摘だけを選び、後続の実装者が計画どおりに進められる状態にする。
- 成功条件: 追加済みテスト2件が意図した条件を検証すること、実機の確認・後片付けが選択した接続先を使うこと、両候補に参照がある中断で危険な削除を案内しないこと、PR 本文が検証済みの範囲を誤って伝えないこと。
- **brainstorming 経路: bounded**。既存の計画・復旧案内の局所修正であり、公開インターフェース・state 形式・エラーコード・セッションをまたぐ自動再開の仕様は変えない。`review-fix-planning` の指定により bounded でも Spec を保存する。
- 未コミットの既存 Spec、別 worktree、指定ディレクトリ外のレビューは入力にも根拠にもしていない。元の A/B の設計判断の見直し、fork への本実装、実機の変更は範囲外。

以下では次の略記を使う。行番号はすべて `CURRENT` のもの。

- `PLAN`: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- `DESIGN`: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`
- `FIRST`: `docs/superpowers/specs/2026-10-02-pr8-docs-review-fixes-design.md`
- `BASE`: ResoLoop の `b3a84ae9b4d09cb60a298879e1cf56e3cf0bd888`。計画・レビューが前提として指定しているコミット。`external/resoloop` の origin / upstream がそれぞれ `usaturn/resoloop` / `orange3134/resoloop` であることを確認し、コミット済み blob だけを参照した。

## 2. 入力の固定

| レビュー入力ファイル | 冒頭の対象 HEAD | 履歴・補足 |
| --- | --- | --- |
| `SWE-2-Max.md` | `c6749fc01605` | Initial は `b851852385b2`。F-01 は Resolved findings に移動済み |
| `deepseek-deepseek-v4.1-flash.md` | `b851852385b2` | Initial |
| `qwen3.8-max.md` | `b851852385b2` | Initial |
| `xai-grok-4.7.md` | `b851852385b2` | Initial |
| `claude-sonnet-5-5.md` | `c6749fc01605` | Initial |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `c6749fc01605` | Initial |
| `gpt-6-sol.md` | `c6749fc01605` | Initial |
| `grok-4.7.md` | `c6749fc01605` | Initial。`xai-grok-4.7.md` とは別入力 |

## 3. 正式な全指摘の分類

**18件: 解消済み9 / 対応する7 / 判断保留0 / 対応しない2。** 同一内容の複数モデルの指摘も入力単位では落とさず数える。修正は5テーマにまとめる。重大度や票数ではなく、現行 HEAD の根拠で選別した。

| ID | 入力・元ID | 指摘 | 分類 | 現行 HEAD の根拠・判断 |
| --- | --- | --- | --- | --- |
| RF2-01 | SWE F-01 | nullable 警告2箇所 | 解消済み | `CURRENT` の PLAN:421、3117 は `stateComponent!` 等に修正済み。計画の source/test ブロックを適用したコピーもコンパイルした |
| RF2-02 | SWE F-02 | 置き換え元の削除の進捗が `fields` | 対応しない | DESIGN:186 と FIRST の RFP-07 が上流の移動元削除に合わせる設計判断を明示。表示の好みであり (a)〜(d) を満たさない |
| RF2-03 | deepseek L-1 | PR 本文の件数・決定事項範囲が古い | 解消済み | 検証時の PR 本文は過去の再生394件・最終予定396件・33箇所・固定7件・D-1〜D-33を区別して記載済み |
| RF2-04 | deepseek I-1 | 冒頭で D-33 を落としている | 解消済み | `CURRENT` の DESIGN:3 は D-27〜D-33 |
| RF2-05 | qwen L-1 | PR 本文の旧数値 | 解消済み | RF2-03 と同じ現行 PR 本文の照合で旧数値361・13・4・D-26の記載は解消済み |
| RF2-06 | qwen L-2 | CLI の plan フィルターのテスト・確認手順不足 | 対応しない | BASE の `Program.cs`:540–542 は create/delete だけを等値で絞り、changes-only は `Changes` を使う。`Models.cs`:284 は no-op 以外を含むので recreate も表示される。既存の正常な経路への保険のテスト追加であり、削除された回帰ガードでもない |
| RF2-07 | qwen I-1 | 冒頭で D-33 を落としている | 解消済み | `CURRENT` の DESIGN:3 は D-27〜D-33 |
| RF2-08 | qwen I-2 | `SaveSlotIndexes` / `SaveSlotIndexesAsync` の不一致 | 解消済み | `CURRENT` の DESIGN は Async 表記に統一済み。非 Async の識別子は残存0件 |
| RF2-09 | xai M-1 | NOT_CONVERGED 前に旧元が消えた key を片付けない | 解消済み | `CURRENT` の PLAN:2602–2612 が例外前に index 保存・supersededId 消去・checkpoint を行う。RF2-15 のテスト設定だけを一時コピーで正すと、この片付けと再読込のアサーションが成功した |
| RF2-10 | xai L-1 | 自己参照で他の initialFields が作成時に渡らない | 解消済み | `CURRENT` の PLAN:2055–2056 は Awaiting verification の自己 key も除外する。RF2-12 の引数だけを一時コピーで正すと、作成応答喪失後の Enabled=true を確認できた |
| RF2-11 | xai I-1 | 冒頭で D-33 を落としている | 解消済み | `CURRENT` の DESIGN:3 は D-27〜D-33 |
| RF2-12 | claude M-1 | 自己参照テストが3→4件の拡大になっている | 対応する (a) | PLAN:1990–1991 をそのまま適用すると置き換え先が存在せず Single が失敗。F1 |
| RF2-13 | claude I-1 | PR 本文が未再生の B3/B4 のコード変更を明示しない | 対応する (b) | PLAN:21 はコード変更2箇所とテスト2件の未再生を明示。一方、現行 PR 本文はコードブロックを検証に使った変更から生成したと一般化し、その後の変更をテスト2件だけで説明している。F5 |
| RF2-14 | commandcode H-1 | 自己参照テストの引数順が逆 | 対応する (a) | RF2-12 と同じ失敗を現行計画の再生で確認。F1 |
| RF2-15 | commandcode H-2 | 初期 apply 後の Writes をリセットせず喪失が発火しない | 対応する (a) | PLAN:3003–3006 をそのまま適用すると ThrowsAsync が「例外なし」で失敗。F2 |
| RF2-16 | gpt H-1 | strict validate / slot delete に接続先が無い | 対応する (a) | PLAN:4176、4185。隔離した URL 未設定の CLI 実行で両方とも exit 3 / RESONITE_LINK_URL_MISSING。F3 |
| RF2-17 | gpt M-1 | 両候補が参照される中断でも「他方を削除」と案内する | 対応する (a) | PLAN:3240、DESIGN:247。管理参照2件の一方を張り替えた直後に中断・再読込すると、両候補に referencedBy があり、この削除案内が出ることを実行確認。F4 |
| RF2-18 | grok H-1 | 自己参照テストの引数順が逆 | 対応する (a) | RF2-12 と同じ失敗を現行計画の再生で確認。F1 |

**仕様論点の記録:** `fields` 進捗は既存の設計判断を維持する。plan フィルターの追加テストも今回の修正には含めない。判断保留はない。

## 4. 未検証候補・付帯提案の扱い

レビューの「Unverified candidates」「Test suggestions」も全件読んだ。正式指摘の修正に直接必要な検証は F1〜F5 に統合し、それ以外を念のため追加しない。以下は補助項目として別集計する。

**14項目: 解消済み1 / 対応する1 / 判断保留0 / 対応しない12。** 正式指摘と合わせた入力項目数は32（解消済み10 / 対応する8 / 判断保留0 / 対応しない14）。「対応する」8行は重複を含み、修正テーマ数は5のまま。

| ID | 入力・項目 | 分類 | 根拠・扱い |
| --- | --- | --- | --- |
| AUX-01 | SWE V-1: 追加2テストの書き込み位置 | 対応する (a) | 実行すると2件とも失敗し、F1・F2 のテスト設定を正すと2件とも成功。正式指摘に統合 |
| AUX-02 | SWE V-2: B8 件数の独立再集計 | 対応しない | 件数の不一致という事実は提示されていない。F4 による件数変更だけ整合させ、実装時の既存 Expected ゲートは維持する |
| AUX-03 | SWE V-3: 短い宣言の既存テスト、上流提出手順の持ち越し | 対応しない | 確認未実施という記録であり、現行の誤動作・事実誤認は示されていない |
| AUX-04 | deepseek U-1: アンカー・ビルドの独立裏付け不足 | 対応しない | source/test 66操作のアンカー一意一致とビルドは本セッションで確認。文書全変更・中間全件までの再検証を求める範囲は保険で、独立した不具合ではない |
| AUX-05 | deepseek U-2: 実機のリスト挙動未確認 | 対応しない | 計画 C2 が実施・判定を後続作業として明示している。ユーザのワールドで未承認の操作をしない |
| AUX-06 | claude U-1: Test.Renderer の Enabled / Target が未登録かもしれない | 解消済み | BASE の `ApplyWorkflowTests.cs`:1719–1729 は fields / initialFields から登録する。F1 のテスト引数のみを正したコピーで Enabled=true のアサーションも成功 |
| AUX-07 | claude U-2: B5 実装前の FAIL 16 / 17 件内訳 | 対応しない | 算術不整合はなく、実測していないという候補のみ。各 Task の既存ゲートに委ね、新しい一括再生を条件にしない |
| AUX-08 | commandcode U-1: Task 別の累積全件数 | 対応しない | 独立した数値不一致の指摘ではない。既存の Task 別ゲートを維持 |
| AUX-09 | commandcode U-2: 実機の型・メンバー名 | 対応しない | C2 自体が type describe 等で確認し、相違時に止まると明示している |
| AUX-10 | commandcode U-3: autosquash の環境依存 | 対応しない | 未検証という候補で再現した不具合はない。レビュー範囲を履歴操作の改設計へ広げない |
| AUX-11 | qwen U-1: Spec 3.1/3.2 の上流照合不足 | 対応しない | 本セッションのアンカー照合・関連経路の実行でも独立した不一致は確認されていない。全文再調査の追加提案は採らない |
| AUX-12 | deepseek T-1: 数値更新時に PR 本文更新を必須化する追記 | 対応しない | 旧数値は既に解消済み。再発防止の運用追記は (a)〜(d) を満たさない。F5 の事実誤認訂正だけ行う |
| AUX-13 | claude T-2: 応答喪失の再試行で重複しないことも追加 Assert | 対応しない | 重複作成の新しい誤動作は示されていない。F1 の本来の Enabled 検証だけを修復する |
| AUX-14 | commandcode T-3: 新規44メソッドの個別 filter 一覧を追記 | 対応しない | 既存の Task ゲートに加える便宜上の検証であり、今回の再現に必要ない |

その他の Test suggestions はすべて正式指摘の修正・検証方法の再掲であり、対応は元 ID と同じ（SWE は RF2-02、qwen は RF2-05〜08、xai は RF2-09〜10、grok は RF2-18、gpt は RF2-16〜17、claude T-1 は F1、commandcode T-1〜2 は F1〜2、deepseek T-2 は RF2-04）。deepseek L-1 内の運用追記提案も AUX-12 に含めた。

## 5. 現行 HEAD での検証結果

検証対象の文書・source/test は `git show <commit>:<path>` から取得した。main checkout の未コミット source/test は読んでいない。

- `mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX"` で `/tmp/review-fix-planning.qdCVAC` を作成し、その下に PR の `CURRENT` を checkout した detached worktree を作った。HEAD の完全一致を確認した。
- worktree 内の `replay/` に BASE の `git archive` を展開した。現行 PLAN の新規作成・変更指示のうち source/test に該当する **66操作**を順に適用した。すべての変更アンカーが一意に一致した。文書変更10操作は今回の関連テストに不要なので適用していない。
- .NET SDK `10.0.401` で関連テストを実行した。ビルドは成功し、出力に警告・エラーの報告はなかった。全396件や実機を検証したとは扱わない。

| 実行 | 結果 | 確認したこと |
| --- | --- | --- |
| 既存の追加2テストを filter 実行 | exit 1、0 PASS / 2 FAIL | 自己参照テストは Sequence contains no matching element。NOT_CONVERGED テストは Expected IOException / No exception was thrown |
| 一時コピーのテスト設定だけを F1/F2 の案に変更し、同じ2テストを filter 実行 | exit 0、2 PASS / 0 FAIL | 本体の実装ブロックを変えず、引数順と ResetWriteCounts のみで本来のアサーションが通る |
| 両候補に参照がある中断の検証用 Fact を一時コピーだけに追加 | exit 1、1 FAIL | 旧候補 C13 は4要素で C16 から参照、新候補 C15 は3要素で C14 から参照。session-changed で Writes=0 のまま、remove the other という案内が出るため安全性の Assert が失敗 |
| URL 未設定・隔離 HOME で strict validate | exit 3 | RESONITE_LINK_URL_MISSING。接続前に停止 |
| 同じ隔離設定で slot delete REVIEW-NONEXISTENT-ID --yes --json | exit 3 | RESONITE_LINK_URL_MISSING。接続前に停止し、実機への削除は一切していない |

両参照の最小再現は、`RubbleWorld(..., watcher: true)` を使って Materials 4→3件を適用し、`ApplyRubbleAsync` のリセット後に `LoseResponseOnWrite=2`（置き換え先の作成の次、source の参照張り替え）で止めるもの。喪失設定を解除して `ReloadWorld` 後に apply すると、両 candidates の referencedBy が各1件となる。既存 B7 の単純な再読込テストだけではこの位置を固定していない。

検証終了時に `git worktree remove --force` が成功してから親ディレクトリを削除し、両方の不存在を確認した。**Spec 作成・承認待ちまで検証 worktree やログを残していない**。再検証は新しい mktemp から始める。上記の一時コピーへの変更は再現・反証用であり、リポジトリへの実装ではない。

## 6. 修正方針と検証方法

### F1: 自己参照テストの引数順を直す（RF2-12 / 14 / 18、AUX-01）

- 根拠: **(a)** 現行計画を適用すると、作り直しではなく拡大になりテストが失敗する。
- 方針: PLAN:1990–1991 の `ApplyRubbleAsync` を、第2引数 changed=材料3件、第3引数 initial=材料4件にする。helper の仕様（PLAN:1329–1339）や本体の self 除外は変えない。`LoseResponseOnWrite=1` と Enabled=true の検証を維持する。
- 検証: BASE に修正後の計画の source/test ブロックを適用した一時コピーで `FullyQualifiedName~ARecreateReferencingItselfKeepsItsOtherInitialFields` を実行して PASS を確認する。作成された別IDの Renderer に Enabled=true が書かれることを確認する。必要な失敗確認は自己参照の除外だけを元に戻したコピーで行い、一般的なテスト拡張はしない。
- 件数: テスト修復なので増減なし。B3 の9件・累積356件という予定は維持する。

### F2: 応答喪失位置の前に Writes をリセットする（RF2-15、AUX-01）

- 根拠: **(a)** 初期 apply 分の Writes が残り、LoseResponseOnWrite=3 が一致せずテストが失敗する。
- 方針: PLAN:3005 の直前に `client.ResetWriteCounts();` を1行足す。本体の NOT_CONVERGED 片付け処理は既に修正済みなので変更しない。
- 検証: 同じ一時コピーで `FullyQualifiedName~ANotConvergedApplyStillSettlesARecreateWhoseSourceIsGone` を実行して PASS。削除応答喪失が実際に発火し、r1 の supersededId が消え、r2 の取り消しと再読込後の apply が成功する既存 Assert を維持する。
- 件数: 増減なし。B5 の17件・累積379件という予定は維持する。

### F3: 実機手順の接続先を一貫させる（RF2-16）

- 根拠: **(a)** 第一候補の auto/session 経路では strict validate と後片付けが実行できない。既存 URL がある場合も別の接続先を使い得る。
- 方針: C2 の strict validate、削除直前の inspect、slot delete、失敗時の inspect と削除に、選択した同一の `--url auto --session <SessionId>` を明記する。型確認を含め、接続が必要な手順も同じ宛先を使う。明示 URL 経路では同じ確認済み URL を渡すことを説明する。再読込後は Step 5 で選び直した宛先を使い、古い session を使わない。
- 検証: C2 のコマンド・文章を照合し、接続が必要な全操作に同じ宛先が渡ること、URL 環境変数の有無に依存しないことを確認する。正しい接続先を渡す経路の実機実行はユーザの C2 承認後に行う。今回は安全な接続前エラーの再現と文書照合に限り、新しい手順テスト用サブシステムは作らない。

### F4: 両候補が参照されている場合の復旧案内を安全にする（RF2-17）

- 根拠: **(a)** 管理 Component の参照張り替え途中で中断すると両候補に referencedBy があり、現行 suggestions は残す候補を一意に決められず、参照を切る削除を案内する。
- 方針: PLAN の `RecreateInterrupted` の session-changed 分岐と DESIGN:247 を同期する。同型の別 key がある既存の慎重な案内を維持し、それが無くても **referencedBy が空でない候補が2件以上ある場合**は別の安全な案内にする。
  - 候補のどちらかの削除や supersededId の除去を、その場で案内しない。
  - state はそのまま保持し、各参照元を手で確認し、意図した参照先への張り替えが必要であることを明示する。
  - 参照の確認・張り替え後に再検査して候補の状態を確かめる。旧セッションの ID や候補のリスト長だけで削除対象を推測しない。
  - 参照された候補が0件または1件の場合の既存案内、reason、context、停止前の Writes=0 は維持する。自動張り替え・巻き戻しを新設しない。
- 回帰ガード: B7 に1 Fact を追加し、管理参照2件の一方の張り替え後に喪失→再読込→apply を行う。session-changed、両 candidates の referencedBy、Writes=0、削除・state 修復を早まらない suggestions を固定する。
- 検証: 新 Fact が元の案内で FAIL、修正後 PASS。既存の `AWorldReloadDuringARecreateStopsBeforeAnyWrite` を併せて実行し、0/1参照・同型別 key の既存の扱いを変えないことを確認する。
- 数値の整合: 新 Fact 1件を B7 に追加するため、B7 は9→10件、最終予定396→397件。B8 の修正前比較の予定は全397件中 FAIL 53 / PASS 344、B追加60件中固定7件。B3/B5/B6までの予定は維持する。計画の Expected・PR B の将来の本文テンプレート・最終予定件数を同期する。これらは**算術上の予定**であり、今回の全件実測ではない。過去の試作394件・ミューテーション33箇所という履歴は書き換えない。

### F5: PR 本文の検証済み範囲を訂正する（RF2-13）

- 根拠: **(b)** 現在のコードブロックすべてが過去の再生に使われたように読める記述が、PLAN:21 の未再生のコード変更と一致しない。
- 方針: 過去の394件・33箇所の検証と、その後の B3/B4 のコード変更2箇所・追加テスト2件を区別する。今回の関連テストのみの再生結果と、F4 の案内変更・新 Fact も区別して記録する。最新全397件や実機が検証済みであるかのように書かない。履歴として正しい過去の結果は維持する。
- 検証: 反映後の `gh pr view 8 --repo usaturn/create-reso-world --json body` を PLAN 冒頭と照合し、「過去に全件確認した版」「その後に変更した範囲」「今回確認した関連テスト」「まだ実装時に確認する予定件数」を区別できることを確認する。

## 7. 承認後の反映と停止条件

1. 実装対象は PLAN / DESIGN の上記修正、この Spec の承認・結果記録、および既存 PR #8 の本文のみ。元の A/B を fork に本実装しない。
2. 既存 PR の現行 HEAD を fetch / gh で再確認する。変わっていれば今回の該当項目だけ新 HEAD で照合する。未コミットの既存ファイルは取り込まない。
3. F1 / F2 / F4 の関連 filter テストと F3 / F5 の文書照合、`git diff --check`、`bash scripts/check-layout.sh` を実施する。変更が文書だけでなく環境用 source/tests に及ぶ場合は `bash .devcontainer/run-tests.bash` も必要。実機操作は承認対象に含めない。
4. 関連検証が失敗したら修正し、commit しない。全ワールドのテスト・fork 全件再実行を commit/push の追加条件にしない。計画本文にある将来の全件ゲートは削除しない。
5. 検証後は **`docs/list-shrink-recreate-split` に commit して既存 PR #8 に push** する。新しい review-fixes branch / PR を作らない。open な PR が無ければ作らず停止する。
6. push 後は正確な実行モデル識別子を取得し、`$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py` で日本語の review-fix-planning 状況コメントを更新する。他エージェントのコメントを編集しない。
7. 計画ターンは Spec を提示して承認待ちで停止した。後続の「進めてください。」により2026-10-02に明示承認を受けたため、実装・既存 PR への反映へ進んだ。計画ターンの任意コメントは未投稿。実装ターンの push 後の状況コメントは必須とする。

## 8. 作業チェックリスト・所要時間

- [x] 全8レビュー入力と各対象 HEAD を固定
- [x] 現行 PR / リポジトリ / ブランチ / HEAD を確認
- [x] committed source と隔離コピーで該当指摘を検証
- [x] 全正式指摘と補助項目を4区分へ分類
- [x] brainstorming の bounded 経路で修正方針を整理
- [x] 検証 worktree を撤去してから Spec を保存
- [x] ユーザの明示承認（2026-10-02、「進めてください。」）

作業時間は2026-10-02 16:23〜16:46 JST、約23分。主要内訳: 入力固定・規約確認 約4分、再生準備と関連経路検証 約11分、分類・Spec作成と自己点検 約8分。正式18件・補助14項目の ID 一意性と区分別件数、文書の空欄・末尾空白を検査した。`git diff --check` と `bash scripts/check-layout.sh` は成功。tracked の作業差分は0件で、この新規 Spec だけを作成した。検証用の worktree 登録と親ディレクトリの撤去も確認済み。

独立した読み取り専用の確認を `sp-research` に同期委譲したが、返却内容は暫定判断で、確定した照合根拠・所要時間は提示されなかったため採用しなかった。分類の根拠はすべて本体で照合・実行確認した。委譲ログ path / 終了コードはツール結果に明示されていない。本環境の subagent は同期限定の Superpowers role API であり、旧 API の list / capabilities / async 引数は提供されていない。

## 9. 承認後の実装・検証記録（2026-10-02）

- 承認後の作業場所: 既存の `.worktrees/list-shrink-spec`（ブランチ `docs/list-shrink-recreate-split`）。着手時はクリーンで、HEAD は選別時の CURRENT と一致。共有ルートの他の未コミット Spec は取り込まなかった。
- F1/F2: 既存テストの引数順・Writes の初期化のみ修復。本体の自己参照除外と NOT_CONVERGED 片付けは変えていない。
- F3: C2 の strict validate、型確認、inspect、削除、失敗時の後片付けに同じ接続先を渡すことを明記。明示 URL の経路、再読込後の再選択、接続先が確認できなければ削除せず止まる条件も同期した。
- F4: session-changed で参照された候補が複数ある場合だけ安全な案内を加え、B7 に `AWorldReloadWithBothRecreateCandidatesReferencedDoesNotSuggestDeletingEither` を1件追加。state 不変・Writes=0・両候補の参照と、早まった削除/記録除去を案内しないことを確認する。
- F5: PLAN 冒頭と PR 本文案で、過去の全件394件・33箇所、後からのコード変更2箇所・テスト2件、今回の関連12ケース、今後の全397件を区別した。Expected・将来の PR B の日英テンプレートは397 / 53 / 344 / 60 / 7で同期。過去の全件再生結果は変更していない。
- 一時環境: 新しい mktemp で `/tmp/review-fix-planning.nPNx8y` を作成し、その配下に CURRENT の detached worktree と BASE の archive コピーを用意した。計画の source/test 66操作の全アンカーが一意に一致した。
- Red: 元の F1/F2 と新しい F4 のテストが3件とも意図した理由で FAIL（引数順による候補不在、喪失未発火、安全でない削除案内）。
- Green: 修正後の F1/F2 と B7 の10ケースを filter 実行して **12 PASS / 0 FAIL、exit 0**。ミューテーション復元後の最終確認も同じ12ケースが成功した（約19秒、.NET SDK 10.0.401）。全397件・実機を実行したという記録ではない。
- ミューテーション: 作成時の自己参照除外だけを元に戻すと、F1 の修復済みテストが Enabled=false の Assert で FAIL（exit 1）。コードを復元してから最終 Green を実行した。
- 文書照合: source/test の最終コードブロックが Green の適用元と一致すること、Spec/Plan の suggestions 文言・接続先指定・将来件数・PR 本文案の検証範囲を照合して成功。
- 配置検証: 対象 worktree で `git diff --check` と `bash scripts/check-layout.sh` が成功（exit 0）。変更は文書3ファイルだけで、環境用コードや fork を変更していないため環境フルスイートは実施していない。
- 独立レビュー: `sp-review` に読み取り専用の task review を同期委譲。初回は scope 宣言不足で実施前に戻り、scope と upstream template を明示して再依頼した。レビュー完了、Critical 0 / Important 1 / Minor 0。指摘は将来の PR B 英語テンプレートの `52 of the 59` の更新漏れで、本体でも確認して `53 of the 60` に修正・再照合した。子の所要時間と終了コードは結果に明示されていない。実行検証は本体が担当した。
- 実装・検証・レビュー所要時間: 16:57〜17:20 JST、約23分。主要内訳は準備と Red 約4分、修正と Green・ミューテーション 約8分、独立レビューと指摘修正 約7分、最終確認と記録 約4分。commit/push・PR 更新・一時環境撤去の結果と所要時間は、既存 PR #8 の状況コメントに残す。
