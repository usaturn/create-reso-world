# Issue #52: Resonite model preproduction design

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/52
- コード対象: `usaturn/resoloop`（origin）、`orange3134/resoloop`（upstream）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-52-preproduction-docs`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-52-preproduction`
- コード基点: `99c59be98df0f10b0a8e58781b7f4f67029016f5`（origin/main = upstream/main）
- 状態: `completed`（実装・検証完了。文書内容の個別承認は未取得）
- 関連 Plan: `docs/superpowers/plans/2026-10-08-create-reso-world-issue-52-model-preproduction.md`
- 実行許可: ユーザーの「Issue #52 に着手、途中で止めずに推奨案で進めて PR まで作成」に基づき、設計・計画の個別承認待ちを省略し、隔離 worktree で実装・検証・コード PR と文書 PR の公開まで行う。未作成だった文書の内容が個別承認されたとは記録しない。マージ、Meshy の課金、画像送信、既存ワールド変更は含まない。

## 目的と完了条件

一品物の 3D アセットを、ソフトウェア向け TDD に接続せず、比較可能な仕様・受入条件・制作経路・構造・工程・引き継ぎへ整理する。`resonite-model-preproduction` を ResoLoop の bundled skill として `init` / `skills sync` で配布する。制作そのものは既存スキルへ渡し、個別のモデルを生成・編集しない。

## 方針の比較

1. **採用: 集約した SKILL.md + 必須の制作引き継ぎテンプレート。** 7 段階の判断と安全条件を本文に置き、長い出力項目は同梱 reference に分離。既存の明示的な resource/配布リストを使う。読みやすさと完全な引き継ぎを両立する。
2. 全内容を 1 ファイルに収める: 配布は簡単だが出力テンプレートを含めると本文が重くなる。
3. 複数の新規スキル/ソフトウェア自動化: 前工程の判断には過剰。既存 build/Blender/Meshy の責務を重複しやすいので不採用。

## スキル構造

- `skills/codex/resonite-model-preproduction/SKILL.md`: trigger、操作しない境界、以下の 7 フェーズとレビュー条件。
- `skills/codex/resonite-model-preproduction/references/build-handoff.md`: 仕様・受入・経路・構造・計画の情報を失わない Markdown テンプレート。SKILL.md から作成時に読む指示を出す。空欄で完了とせず、非該当は理由付きで記録。
- `BundledSkillManager.Names/Files` と `RLoop.Core.csproj`: 両ファイルを登録・埋込み。既存の lock/hash/conflict 保護を変更しない。
- README と `resonite-build` に前工程への導線を追加する。既存の制作ワークフローや CLI の再実装はしない。

### 1. Concept Exploration

用途、hero/background/repeated、static/moving、visual direction、視認距離/最短距離/把持/配置数、入力資料、外部送信禁止、寸法接続精度、編集可能性を整理する。情報の軽微な不足は仮定を明示して進め、重大な方向の相違だけ確認する。秘密情報・送信/課金許可は推測しない。

### 2. Asset Specification

実装ツールより先に、Purpose、Visual Direction、Physical Dimensions、Dimensional Tolerance、Silhouette、Major/Secondary Forms、Focal Details、Materials、Surface Condition、Color/Emission、Viewing Conditions、Interaction Requirements、Moving Parts/Pivots、Runtime Considerations、Editability、Source Inputs、Reference Images、Non-Goals、Assumptions を定義。実寸は単位と許容差を含め、制御寸法の測定方法も計画する。

### 3. Acceptance Definition

Visual/Geometry/Material/Runtime の 4 分類。正面・側面・背面・45 度と視認距離、形状と比率、寸法、浮遊/交差/normals、素材/texture/emission、部品分離/pivot、配置数/collider/interaction を比較可能にする。全経路に共通し、ポリゴン数/texture size の一律上限は設けない。品質と実行コストは役割・距離・配置数に応じる。

### 4. Production Route Selection

必ず仕様・受入条件の後で選ぶ。5 経路: Resonite native、Blender authored、Meshy-assisted Blender、Hybrid、Existing asset adaptation。選択理由、不採用案、入力・権利・source format、外部送信制約、Meshy 適性、Blender cleanup、native finishing、fallback を記録する。

Meshy はベース生成だけ。参考画像、有機/不規則/損傷形状には候補。精密寸法・機械構造・可動部/pivot・厳密 topology/UV・外部送信禁止には Blender を優先する。rig/animation/shape key 等は現 exporter の対応を確認し、静的 export + native runtime 化または明示的な別経路を計画し、対応できると偽らない。

### 5. Model Architecture

オブジェクト別の 1 mesh、部品/所有範囲/material/可動部/pivot/collider/再利用/hierarchy を設計。Meshy 範囲と、保持・削除・Blender 再構築・texture/channel 補正・native collider/Components/interaction/ProtoFlux を生成前に区分する。`.blend` や取得した原本などの保存と編集可能性を計画に残す。

### 6. Production Planning

Phase 0 入力/経路確認、1 blockout/base、2 silhouette/proportion/candidate、3 primary forms/cleanup、4 secondary detail、5 materials/textures、6 integration、7 visual validation、8 targeted refinement。各段階の成果と gate を指定する。最終的な実 Resonite capture、寸法・構造検査、material review、runtime 確認は後続 build に渡し、前工程で実施済みとしない。

完成後は満足した形状・承認比率・採用済み生成部を保持し、局所修正を優先。全体再構築は構造的問題だけ。Meshy 再生成は追加の有料操作なので既存生成物の局所修正を先に検討する。

### 7. Build Handoff

テンプレートを埋め、目標・visual direction・役割/距離・寸法/許容差・required features・仕様・受入・経路/理由・入力/外部送信制約・Meshy 適性・有料操作案/許可状態・構造/部品/material/pivot・construction/cleanup/native finishing・production phases/gates/views・runtime・fallback・non-goals・assumptions/open questions を渡して終了する。

## 境界と許可

- 前工程では Meshy API/status/download/retry/recovery/conversion、Blender 操作、world 変更、`apply`、ProtoFlux 実装、capture をしない。認証情報の要求・表示・保存も禁止。
- 有料操作案は件数・予算・モデル・texture/PBR/解像度・送信対象を含むが、許可ではない。Build Handoff の承認と課金/画像送信許可は別。`Paid Operation Approval Status: not-authorized-at-preproduction-stage` を記録し、既存の許可が提示されても実行担当が再照合する。
- 外部の `meshy-resoloop` は同梱ではない。参照はスキル名で行い、不在なら課金を開始せず導入/別経路を報告。#50 の wrapper・秘密情報・journal・変換処理を複製しない。
- handoff はまず `resonite-build` に渡す。native/Blender は build→必要に応じて resonite-blender、Meshy は build が別途の明示許可と meshy-resoloop を確認→Blender finishing→native integration/verification。
- 3D アセット/一品物の制作 script/見た目には unit test/TDD を適用しない。再利用できる importer/exporter/add-on/pipeline/ライブラリなどソフトウェアは通常のテスト方針を維持する。

## 検証方針

文書に固定文言・スキル一覧を照合するテストは追加しない。既存の ProjectInitializerTests（13 件）が init、sync、missing 復旧、ユーザー編集 conflict、reference 復旧、lock 移行を実行する。登録/埋込みは実 CLI の一時プロジェクトで新スキルと reference の導入・欠損復旧・変更保護を確認する。全文回帰、pack/install の無通信 smoke、skill efficiency checker、frontmatter/参照先、diff を検査する。

スキルの動作は baseline と新スキルの代表 dry-run で確認する。秘密画像＋精密寸法＋可動蓋＋20 配置では Meshy を除外し、前工程で実コマンドを開始しないこと。画像使用が可能な岩/布では Meshy を候補にしつつ未許可状態と cleanup/fallback を維持すること。既存 asset の利用権・仕様確認も含める。

## 調査・初回検証

- origin/upstream と作業ルートを確認。親 checkout は未変更（origin/main detached）。コード checkout の未追跡 `reviews/` と別 worktree は触らない。
- baseline `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~ProjectInitializerTests --verbosity quiet`: 13 passed、0 failed、0 skipped。
- 読み取り専用 recon: 現行バンドルは明示的 resource/Files 登録。新テンプレートは両方への追加が必要。現 Blender exporter は static mesh 経路であり、runtime 可動部を別担当に渡す。
- baseline dry-run は実制作コマンドへの移行を示し、前工程の成果物・許可状態がまとまらなかった。新スキルでは操作開始せず Build Handoff で終了する。

## 実装・検証結果（2026-10-08）

- 実行した設計・計画の初版: `d04972cbe3c968343aad5e951c5b79243b859f4c`。個別の内容承認ではなく、冒頭に記録したユーザーの実行許可に基づく。
- 最終コード HEAD: `a648d41252a57313c499618617452022b6bce529`。コード PR: https://github.com/usaturn/resoloop/pull/10
- 実装: SKILL.md と `references/build-handoff.md`、Names/Files/csproj 登録、build と README/Blender 文書の導線。sync/lock/hash/conflict の実装と既存プロジェクトは変更なし。
- controller の新規検証: build 0 warnings / 0 errors、solution 448 unit + 19 reported integration passes / 0 failures。live opt-in 無効の integration は早期 return で、実 Resonite/Blender 検証ではない。
- 実 source + pack/install CLI: 両ファイルが source と一致、check は read-only、reference 欠損を update で復旧、利用者編集の conflict では欠損 reference の部分書込もせず保持、復元後 check clean。pack/install はローカル一時 feed のみで実施。
- YAML/参照先/resource 構造、skill-efficiency（新スキルは警告なし）、C# active LSP（0 diagnostics）、`git diff --check` を確認。
- 独立 task review → 3ケースの workflow dry-run → 変換制約/生成 mode/許可の明確化 → scoped re-review → whole-branch review → mode 別課金件数の修正 → scoped re-review が完了。最後の re-review は全指摘対応済み、新規 Critical/Important なし。
- text は preview と提案した refine を別操作に計上し、両方提案した場合のみ計2件。image は提案した image 生成1件につき1件で、自動で preview/refine を追加しない。両方とも課金/送信未許可の dry-run を確認。
- 新規 unit/prose/スキル名一覧テストなし。文書/登録値変更には既存挙動テストと実 CLI、構造検査を用いた。
- 未実施: Meshy API/課金/画像送信、実 Blender 制作、Resonite capture/runtime、通常プロジェクトへの sync、merge、NuGet release。公開 NuGet への同梱は別途 release が必要なため Issue は自動 close しない。
- 文書 PR と public CI の最終結果は公開記録節に追記する。

### 所要時間

| 担当・工程 | 記録 |
| --- | --- |
| controller 調査・設計・計画・隔離準備 | 12:17–12:26 JST（約9分） |
| 初回実装（authoring/配布/検証/報告） | 9分24秒。調査53秒、実装2分34秒、構造/build/回帰1分57秒、smoke準備/実行1分10秒、自己レビュー/commit43秒、報告2分7秒 |
| 変換制約/mode/許可の追記修正 | 最終確認まで6分31秒。調査52秒、修正29秒、構造39秒、build/回帰1分32秒、smoke18秒、自己レビュー17秒、報告/確認約2分24秒 |
| mode別件数の最終修正 | 03:59:11–04:06頃 UTC（約7分）。調査54秒、修正24秒、構造29秒、build/initializer22秒、smoke18秒、commit17秒、報告エラー復旧と再検証/報告を含む |
| controller 最終 build/回帰/pack/install/efficiency + LSP | 86.8秒、2026-10-08 13:09:59 JST 完了 |
| 調査・dry-run・レビュー子 | 同期実行で終了・成果を確認。読み取り専用ランタイムでは時計がないため個別実測なし。controller の全体経過時間に含む |
