# Issue #85 Meshy Normal Map UV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 単一 UV と一致する法線マップを安全に正規化し、実 convert/export/validate を通す。

**Architecture:** converter が素材ごとの全 mesh user を adapter に渡し、非空の tangent UV の同値性を検証してから空に戻す。既存の空指定・graph safety・culling 同意・出版境界は維持する。実 GLB fixture と実 bpy の検査で入出力を守る。

**Tech Stack:** Python/uv/pytest、Blender 5.0.1 bpy、導入済み ResoLoop offline CLI。

**Spec:** `docs/superpowers/specs/2026-10-11-create-reso-world-issue-85-meshy-normal-map-design.md`

- 文書管理・対象: `usaturn/create-reso-world` Issue #85
- 検証した開始 HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`
- 状態: completed（全 Task と review 完了。全体 suite の既存失敗は残る。内容の個別承認は未取得）
- 実行許可: 「途中で止めずに推奨案で完了する」に基づく下記修正の連続実行。承認済みと推測しない。
- 公開: 未実施。push/PR/merge/Issue close はしない。

## Global Constraints

- 非空の normal UV は、その素材を使う全メッシュに UV がちょうど1つあり、active UV の名前が元の指定と一致するときだけ空に正規化する。
- 空の normal UV の既存挙動、TANGENT・定数 Strength・直接 Non-Color 画像・unlinked Vector・Flat/Repeat/Linear の検査を維持する。
- UV 座標・normal pixels・Strength・メッシュ分離・素材共有・階層を維持する。
- normal UV の許可オプションを追加しない。既存の --allow-culling-change は独立した明示同意として維持する。
- Python ツールは uv で実行する。API/課金/live 操作、ResoLoop や world の変更、無関係な既存テスト修正はしない。
- テストはコードを実行して挙動を確認する。文書・ソース本文の文字列照合テストは作らない。

## Review Focus

- 共有素材: 2つ目の mesh user の別名を見落とさず、拒否前に共有 node の名前を消さない。
- 複数 UV: active と同名の normal でも、非空なら曖昧な入力として拒否する。
- 互換性: 任意名の単一 UV を受け入れ、既存の空指定（複数 UV を含む）と3引数 adapter 呼び出しを保つ。
- graph safety: object-space normal、linked Strength、linked image Vector、sRGB normal を引き続き拒否する。
- 保存・export: packed normal image と非既定 Strength が blend と実 provider/asset まで届き、source GLB を変えない。

## Execution / baseline

結合された1 Task のため dependency-ready wave は [Task 1] のみ。
fixture・実装・E2E を別 writer に分割すると相互依存し、独立承認できないため同じ隔離 worktree で逐次実行する。
worktree: `/workspaces/reso-world/.worktrees/issue-85-meshy-normal-map`。
Task の実装・レビューは subagent に委譲し、root が plan のチェックを更新する。

baseline は Spec の既存失敗1件と環境skipを記録済み。修正の RED と混同しない。
pytest の一時 repo は親 Git を発見しない `/tmp` を使用する（repository 内の --basetemp は避ける）。

---

### Task 1: 全 mesh user による normal UV の安全な正規化と回帰検証

**Files:**
- Modify: `scripts/meshy_blender.py` (`adapt_material`, `convert`)
- Modify: `tests/fixtures/meshy/create_fixture.py` (`create`, CLI case choices)
- Test/Modify: `tests/scripts/test_meshy_conversion.py`
- Modify: `docs/meshy-resoloop.md` 検証済み範囲と normal UV の範囲
- 必要なら Create: `tests/fixtures/meshy/check_normal_uv.py`（実 bpy safety probe。長い probe をテスト本文に埋めずに置く）

**Interfaces:**
- Consumes: 現行 `convert(args)` の imported mesh objects、`image_input` と `Rejected`、
  test の `tools`, `glbs`, `world`, `replace_glb`, `convert`, `assert_unpublished`。
- Produces: `adapt_material(material, defaults, cache, *, mesh_users=())`。
  `mesh_users` は素材を使う bpy Mesh datablocks の列。省略時は非空指定を拒否、空指定は既存どおり。
  `convert` が素材ごとに該当メッシュ全件を渡す。CLIや manifest schema は変えない。

**テスト要否:** 必要。実不具合の再現・UV 同値性の分岐・共有 node の変更順序・保存/export の入出力を実行して守る。
文書のテストは不要で、diff 確認に代える。

- [x] **Step 1: 実 normal GLB fixture と失敗する回帰テストを書く。**
  `normal_map` case を生成側の choices と `glbs` に追加する。既存の2メッシュに同じ素材を使い、
  asymmetric Non-Color 2×2 normal image を直接 tangent Normal Map に接続し、Strength=0.65 にする。
  `test_real_conversion_preserves_normal_map` は replace_glb → convert を実行し、成功を期待する。
  成功後に実 `resoloop validate <bundle/model.apply.json> --json` を実行し、成功 exit と ok を確認する。
  saved blend を再読込し、normal uv_map が空、sole active/render UV、packed Non-Color pixels、
  Strength≈0.65 を検査する。bundle の実 PBS_Metallic.NormalMap→StaticTexture2D→asset を辿り、
  IsNormalMap=true、NormalScale≈0.65、画像の実在と pixels（PNG 誤差1/255）を確かめる。
  source bytes、2 mesh と階層・共有素材が保たれたことも既存 helper と probe で確認する。

- [x] **Step 2: focused test を実行して RED の理由を確認する。**
  Run: `uv run --frozen pytest tests/scripts/test_meshy_conversion.py -k normal_map -q -rs`。
  Expected: `blender_rejected:FixtureMaterial:tangent_normal_active_uv_required` による FAIL。
  tools skip、culling、CLI typo を RED として扱わない。既存 culling 同意のみ渡す。

- [x] **Step 3: 実 bpy の UV/graph safety ケースと最小実装を追加する。**
  `adapt_material` に keyword-only mesh_users を追加する。非空指定だけ、全 user の
  len(uv_layers)==1、active is not None、active.name == 元の uv_map を検査し、不明 users を拒否する。
  現行 normal graph と image_input 検査を維持し、その後に空へ正規化する。
  `convert` は素材の全使用メッシュを identity で集めて渡す。
  probe は任意名の単一一致、既存の空指定（単一/複数）、別名、複数UVの同名、
  users不明/UV不在、共有素材の不一致を両順序、共有一致を検査する。
  不一致時は material 名付き例外と元 uv_map の維持を確認する。
  object-space / linked Strength / linked Vector / sRGB normal の拒否も実ノードで確かめる。
  各新規挙動の実装前の失敗を記録し、既存拒否の safety test は既存挙動として記録する。

- [x] **Step 4: focused GREEN と全 conversion 回帰を実行する。**
  Run: `uv run --frozen pytest tests/scripts/test_meshy_conversion.py -q -rs`。
  Expected: 全件 passed、必要な Blender/ResoLoop 検証の skipped 0。
  3引数互換と全 user collection は実装 diff と呼び出し箇所を確認する。

- [x] **Step 5: runbook を更新し全体・静的検証を同期実行する。**
  `docs/meshy-resoloop.md` に単一 UV の normal GLB、normal provider・pixels・strength、
  convert/export/validate の検証と named UV の拒否範囲を記す。実測版と未検証範囲を明記する。
  Run: `uv run --frozen pytest -q -rs` と `uv run --frozen pytest tests/scripts -q -rs`。
  Expected: 新規失敗0。既存 baseline 失敗は名称と件数を報告する。省略しない。
  Run: `uvx ruff check scripts/meshy_blender.py tests/scripts/test_meshy_conversion.py tests/fixtures/meshy`、
  `git diff --check`、`bash scripts/check-layout.sh`。結果と終了コードを記録する。
  changed Python の active LSP 診断は controller が補助実行する。bpy 不在など環境制約は分けて記録する。

- [x] **Step 6: self-review・commit・作業報告を提出する。**
  `git diff` で共有素材の検査順序・画像の保持・既存 graph/culling 検査・対象外変更なしを確認する。
  対象ファイルのみ commit する。plan/spec の状態・チェックは controller 所有なので変更しない。
  report に RED/GREEN の command・該当 output・exit、full suite の既存失敗、
  変更ファイル、elapsed と主要内訳を書く。

## 実行結果

Task 1 の全 Steps は実行・独立レビュー済み。実装 `cdcf6da`、Task 判定 Approved、Final review は Critical/Important なし。最終文書修正 `d5e3809` の scoped re-review は ADDRESSED、新規問題なし。
controller の最終結果は scripts 282 passed + 144 subtests / skip 0、configured repository 482 passed / 既存失敗1 / skip 0。convert suite は83 passedで、実 normal GLB の export/validate を含む。
ruff・diff-check・layout は成功。LSP は Blender専用／動的 import と既存推論の制約があり clean ではない。詳細な結果・ログ・時間内訳は関連 Spec の完了記録と worktree の `tmp/issue-85-controller/controller-report.md` にある。
初回の CLI setup timeout は単独・全体再実行で再現せず、原因未確定として保持する。全体 green と主張しない。
公開未実施。今の worktree・ローカル commits を保持し、実装を再実行しない。公開・merge・Issue close は別途明示指示が必要。
