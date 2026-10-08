# Issue #52 Model Preproduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ResoLoop に制作開始前の `resonite-model-preproduction` スキルを配布し、モデル固有の仕様・制作計画を既存 build に引き継ぐ。

**Architecture:** 7 フェーズを 1 つの SKILL.md に集約し、必須 Build Handoff テンプレートを reference として同梱。既存 init/sync の resource 登録を使い、lock/conflict の実装は変更しない。

**Tech Stack:** Markdown/YAML frontmatter、C#/.NET 10 embedded resources、既存 xUnit、ResoLoop CLI。

**Spec:** `docs/superpowers/specs/2026-10-08-create-reso-world-issue-52-model-preproduction-design.md`（DOC_ROOT 内）。

- 文書管理: `usaturn/create-reso-world`
- 対象: https://github.com/usaturn/create-reso-world/issues/52 / コード `usaturn/resoloop`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-52-preproduction-docs`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-52-preproduction`
- コード基点: `99c59be98df0f10b0a8e58781b7f4f67029016f5`
- 状態: `completed`（実装・検証完了。内容の個別承認は未取得）
- 実行許可: ユーザーが個別の確認待ちを省略して推奨案で PR 作成まで進めるよう指示。内容の個別承認ではなく、設計・計画・実装・検証・新規ブランチの push/PR 作成の実行許可として記録。マージ・課金・画像送信・既存ワールド変更なし。

## Global Constraints

- 配布元は `skills/codex/resonite-model-preproduction/`。インストール先 `.agents/skills/` や親 checkout を実装元として編集しない。
- フェーズは Concept Exploration → Asset Specification → Acceptance Definition → Production Route Selection → Model Architecture → Production Planning → Build Handoff。
- 前工程では実際の生成・Blender/world 編集・apply・capture・認証情報の要求/表示/保存をしない。
- 5 経路は Resonite native / Blender authored / Meshy-assisted Blender / Hybrid / Existing asset adaptation。ツール選定より先に仕様・受入条件を決める。
- Meshy はベース生成だけ。課金/画像送信許可は handoff の承認とは別。許可状態は `not-authorized-at-preproduction-stage`。
- `meshy-resoloop` は外部スキルで、不在時は実行しない。#50 の運用を複製しない。後続制作は `resonite-build` が引き受ける。
- 3D アセット/一品物 script/文言には unit test/TDD を作らない。再利用ソフトウェアの通常テストは維持する。
- 定数・一覧をテストへ写さない。既存のユーザー編集/conflict 安全性を保持する。
- 実装担当は同期でテスト完了を待ち、レビュー担当は読み取り専用。予約 ref・GitHub・公開操作は controller のみ。

## Review Focus

以下は文書の固定文言テストではなく、dry-run/構造検査/CLI smoke で確認する。

1. 秘密参考画像と厳密寸法/ヒンジ: 外部送信しない経路、個別 pivot、寸法測定を計画し、前工程で操作しない。
2. Meshy 候補だが実行未許可: 有料操作案と別途の明示許可、cleanup、fallback を区別する。
3. Template の埋込み/Files への登録漏れ: 実 init と sync 復旧で support file まで使えること。
4. 利用者が SKILL.md を変更済み: update の preflight conflict で保持し、他の欠損ファイルも部分的に書かないこと。
5. rig/animation/transmission、既存 asset の権利: サポート済みと推測せず別経路/適応を計画すること。

---

### Task 1: 制作前工程スキルを完成し配布経路に統合する

**Files:**
- Create: `skills/codex/resonite-model-preproduction/SKILL.md`
- Create: `skills/codex/resonite-model-preproduction/references/build-handoff.md`
- Modify: `src/RLoop.Core/BundledSkillManager.cs`（Names/Files）
- Modify: `src/RLoop.Core/RLoop.Core.csproj`（embedded resources）
- Modify: `skills/codex/resonite-build/SKILL.md`（前工程への導線のみ）
- Modify: `README.md`, `README_JA.md`, `README-DETAILS.md`, `docs/BLENDER.md`（該当する紹介/一覧、最小の更新）
- Execute existing tests: `tests/RLoop.Tests/ProjectInitializerTests.cs` と solution 全体。

**Interfaces:**
- Consumes: 現行 `BundledSkillManager.Names`, `Files`, `LoadBundledFile(string)`、ProjectInitializer.Init、Sync の既存挙動。
- Produces: `<project>/.agents/skills/resonite-model-preproduction/SKILL.md` と `references/build-handoff.md`。引き継ぎ受取は `resonite-build`。

**テスト要否:** 新規 unit test 不要。変更は文書/雛形/登録値で、配布ロジックは既存テストが実行する。既存テストの単なる名前・文言・件数の写経をしない。代わりに既存 tests と実 init/sync/pack/install を実行する。実ロジック変更が必要と判明した場合のみ、不具合/入出力に対する挙動テストを先に追加する。

- [x] **Step 1: 調査結果と Spec を読み、周辺の bundled skill を確認。** skill-creator/writing-skills のガイドを適用。基準の ProjectInitializerTests 13 passed は controller 検証済み。baseline dry-run の欠落は Spec の調査節にある。
- [x] **Step 2: 新 SKILL.md を作成。** 全 Spec 項目を満たす短い operational body。7 フェーズ、5 経路の判断、blockout-first/候補 review、4 review gates、local refinement、ソフトウェアテスト例外、実行せず handoff で終了を明記。description は用途・trigger を簡潔に示し、実制作だけの依頼との境界を記す。
- [x] **Step 3: テンプレートを作成。** Spec の全 handoff 項目と Asset Specification/Acceptance の内訳を含め、非該当は理由付き、仮定・未承認状態・未実測を明記。本文から必須読込を指示。
- [x] **Step 4: 配布登録と導線を追加。** Names/Files/csproj の両ファイル登録。既存の explicit resource naming を使う。resonite-build は完成した handoff を消費し重複前工程に戻さない。紹介文とスキル一覧を更新する。
- [x] **Step 5: 構造と軽量検査。** `uv run --no-project` で skill-creator の `scripts/skill-efficiency-check.py` を実行。frontmatter と相対 reference の実在を確認。`git diff --check`。警告は意味を評価して記録する。
- [x] **Step 6: build/既存回帰を同期実行。** `dotnet build ResoLoop.slnx`、`dotnet test ResoLoop.slnx --no-build`。live integration は opt-in を有効化しない。全体テストの失敗/skip は理由とともに報告する。
- [x] **Step 7: 実 CLI smoke。** 一時ディレクトリで `init`→新スキルと reference を source と比較→`skills sync --check`。reference 削除→check が更新必要→update で復旧。SKILL.md の利用者変更＋reference 削除→update が conflict→変更を保持し欠損 reference を部分書込しない。source に復元して update→check clean。`dotnet pack`→一時 tool-path に install→同じ導入ファイルと sync を確認。既存利用者 project は変更しない。
- [x] **Step 8: 自己レビューしコミット、報告。** スコープ・参照先・禁則・テスト採用基準を確認。report に commands/results、未実施、経過時間と主要内訳を書く。GitHub/push は行わない。

## Controller の統合・公開

- [x] Spec/Plan を draft として DOC_ROOT ブランチにコミットし、immutable review copy と docs_draft 確認コピーを作る。承認されたとは記録しない。
- [x] task review（仕様と品質の両 verdict）、必要なら同 implementer へ修正依頼。
- [x] 新スキル読込後の代表 dry-run: 秘密画像/精密可動物、許可未取得の有機形状、既存 asset adaptation。実 API/モデル生成/ワールド操作はしない。trigger/non-trigger も確認。
- [x] 全ブランチの独立レビュー、controller の新規実行による最終 build/test/smoke/diff 確認。
- [x] 実装結果・検証・時間を既存文書に追記し、状態 completed に更新する。内容承認と実行完了を混同しない。
- [ ] `usaturn/resoloop` の feature PR と `usaturn/create-reso-world` の文書 PR を相互参照して作成。Issue #52 を cross-repository `Refs` で参照し、NuGet 未公開なので自動 close しない。public ResoLoop の CI を確認する。
- [ ] 未確認事項と両 PR URL を報告。マージ・通常 project の skills sync・NuGet release は行わない。

## 実行結果

- 実行初版は `d04972cbe3c968343aad5e951c5b79243b859f4c`、記録済みの連続実行許可で進めた。個別承認を得たとは扱わない。
- 最終コード HEAD: `a648d41252a57313c499618617452022b6bce529`。コード PR: https://github.com/usaturn/resoloop/pull/10
- Task 1 と独立レビュー、指摘修正、scoped re-review が完了。最終 re-review は全指摘対応済み、新規 Critical/Important なし。
- controller の新規 build: 0 warnings/errors。solution: 448 unit + 19 reported integration passes、0 failures（live opt-in は無効で、19件は早期 return）。
- source/pack-installed CLI で新スキルと reference の init、missing 復旧、check read-only、conflict 時の利用者変更/lock の保護と部分書込防止、復元後 clean を確認。
- YAML/参照先/resource、skill-efficiency（新スキルは警告なし）、active C# LSP（0 diagnostics）、diff 検査を確認。新規 prose/list unit test は追加していない。
- dry-run: 秘密画像の精密可動物は authored route、許可未取得の画像岩は Meshy proposal のみ、権利不明の rig/glass GLB は条件付き adaptation と fallback。trigger境界と text/image の件数/未許可状態を確認。
- 本文/テンプレートに変換制約・送信許可・生成 mode の明記を補い、imageにtext用preview/refineを誤って足さないようモード別の指示に修正した。既存要件の具体化であり、制作/APIワークフローは追加していない。
- 所要時間の担当別内訳は関連 Spec の「所要時間」節に保存。公開/CI 結果と全体所要時間は公開記録に追記する。
- 未実施: Meshy API/課金/画像送信、実 Blender/Resonite、実機capture/runtime、通常projectへの導入、merge、NuGet公開。公開版に含まれるまではIssueを自動closeしない。
