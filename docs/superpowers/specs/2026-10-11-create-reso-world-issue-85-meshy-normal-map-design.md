# Issue #85: Meshy GLB の tangent normal UV 指定を安全に正規化する

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/85
- 参考: https://github.com/usaturn/resoloop/issues/17
- 調査したコード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`
- 状態: completed（実装・レビュー・offline 検証完了。内容の個別承認は未取得）
- 関連 Plan: `docs/superpowers/plans/2026-10-11-create-reso-world-issue-85-meshy-normal-map.md`
- 実行許可: ユーザーの「途中で止めずに推奨案で完了する」により、質問・Spec/Plan 承認待ちを省略し、下記の狭い修正を実行する。承認済みと推測しない。
- 公開: https://github.com/usaturn/create-reso-world/pull/88 （base main、head fix/issue-85-meshy-normal-map）。追加指示「PRしてくださ。」により push・PR 作成を許可。merge・Issue close は未実施。
- `PARENT_ROOT`: `/workspaces/reso-world`
- `DOC_ROOT` / `CODE_ROOT`: `/workspaces/reso-world/.worktrees/issue-85-meshy-normal-map`

## 目的と原因

Blender 5.0.1 の glTF importer は、単一の既定 UV を使う法線マップにも
`Normal Map.uv_map = "UVMap"` を設定する。`scripts/meshy_blender.py` は非空の
指定をすべて拒否しており、Meshy の PBR refine が変換できない。
導入済み ResoLoop exporter も非空を拒否するため、検査だけを外しても直らない。
素材と全メッシュの UV の対応を検証し、安全に同じ UV を使う指定だけを空に戻す。

調査で実 GLB → import → convert の拒否を2回再現した。メモリ内で安全な名前だけを
空に戻す実験では保存・export が成功し、PBS_Metallic の NormalMap、NormalScale、
normal texture の pixels を確認した。API・課金・実ワールド操作は行っていない。

## 変更する仕様

1. 接続された tangent Normal Map の `uv_map == ""` は、これまでどおり許可する。
   空指定に新しい単一 UV 制限を加えない。
2. 非空の名前は、その素材を使う変換対象の**全メッシュ**に UV がちょうど1つあり、
   active UV が存在し、その名前が元の `uv_map` と同じ場合だけ許可する。
   任意の実際の UV 名を比較し、`UVMap` の固定 whitelist は使わない。
3. 非空なのに mesh user が不明・0件、別名、複数 UV、UV 不在、共有素材の一部だけ
   不一致なら `Rejected(material.name, "tangent_normal_active_uv_required")` とする。
4. 共有ノードの元の名前で全ユーザーを検査してから、既存の normal image 検査を通し、
   `node.uv_map = ""` に正規化する。途中で空にして後続の不一致を隠さない。
5. graph の既存制約（TANGENT、定数 Strength、Color 出力、Non-Color、直接画像、
   unlinked Vector、Flat/Repeat/Linear）を維持する。画像・強度・UV 座標を変えない。
6. material の利用先は converter の scene mesh/material slots から集める。
   `material.users` の数や最初のメッシュだけを安全判定に使わない。
7. `adapt_material(material, defaults, cache, *, mesh_users=())` とし、
   `mesh_users` はこの素材を使う `bpy.types.Mesh` の列。
   既存の3引数呼び出しは空指定では動き、非空指定は利用先不明として安全に拒否する。
8. `convert()` は既存の active/render UV 同期を維持し、各素材の全 mesh user を渡す。

## 受け入れと検証

- 法線マップ付き・単一 UV の実 GLB を wrapper の convert → export → offline validate
  で通し、saved blend の空指定と packed Non-Color normal image、
  apply bundle の PBS_Metallic.NormalMap / NormalScale、texture provider の IsNormalMap、
  texture asset の実在と画像 pixels を確認する。
- UV の不一致、名前が同じでも複数 UV、共有素材の一部の不一致を実 bpy で拒否し、
  拒否で元の名前が消えないことを確かめる。
- 任意の一致名、共有素材、空の既存経路と graph safety を実 bpy で確認する。
- normal UV の検査を緩めるオプションは追加しない。既存の
  `--allow-culling-change` は normal と独立した明示同意であり、既存の安全条件を
  保つため fixture の full convert でも引き続き必要。culling gate の回帰も保つ。
- normal fixture は既存の2メッシュ・共有素材に asymmetric 2×2 normal image と
  非既定 Strength 0.65 を加える。実行時に GLB を生成し、binary はコミットしない。
- 文書だけを照合するテストは追加しない。runbook の検証済み範囲を更新する。

## 対象外と制約

ResoLoop checkout / 導入済み exporter / world の同梱写しの更新、UV bake、複数 UV の
対応拡大、material copy、オブジェクト結合、API・課金、live apply、Windows 実機確認、
culling 仕様の変更、無関係な既存テストの修正は行わない。
Issue #17 と安全条件を揃えるが、他リポジトリへの変更許可とは解釈しない。

既存 baseline: configured pytest は 481 passed / 1 failed / 1 skipped。
失敗は `tests/skills/test_legacy_references.py::test_tracked_files_do_not_refer_to_the_migration_source`
が既存 `.devcontainer/test-initialize-mounts.bash:20` の履歴コメントを検出するもの。
skip は他 Git process の cwd を読めない環境条件。既存 conversion suite は54 passed。
新規失敗と混同せず最終結果で明記する。

## 担当側の選択

既存の3引数 APIを保つ keyword-only context と、結合された1タスクを採用する。
TDD の失敗理由は現在の named-UV 拒否であることを記録する。
複数 UV の空指定の既存挙動を変えず、名前付きの安全性だけを拡張する。
詳細な test helper の構成は実装担当に任せ、関係ない構造変更はしない。

## 完了記録（2026-10-11）

- 実装 commit: `cdcf6da9a8f623c8abcf3bd65a4d7c8568a518a5`。最終文書修正: `d5e3809ab0198b879cab00f59666f5a2cb7bb7c4`。コードの実行対象は前者から不変。
- Task review: Spec compliant / Task quality Approved。Final branch review: Ready to merge Yes、Critical/Important なし。文書の UV 不在時のエラー説明を1回修正し、scoped re-review で ADDRESSED・新規問題なし。
- 実 conversion suite: 83 passed、必要な Blender/ResoLoop 検証 skip 0。法線 GLB の convert/export/validate、normal provider と pixels/Strength、UV/階層/素材共有、27 real-bpy safety ケースを実行。
- controller の最終 scripts suite: 282 passed + 144 subtests、skip 0（257.79秒、exit 0）。初回の無変更 CLI setup に cli_timeout が1件あり、該当ケース単独と全 suite の再実行では再現しなかった。原因未確定としてログを残した。
- controller の configured repository suite: 482 passed / 1 failed、skip 0（239.28秒、exit 1）。冒頭の既存 legacy-reference failure が残る。全体テスト成功とは扱わない。
- ruff、diff-check、check-layout は exit 0。active LSP は host の bpy/mathutils 不在、runtime の動的 import、旧 fixture の tuple 推論等の9診断あり。既存 baseline 6診断と比較し、LSP clean とは報告しない。実 bpy 実行と lint の結果は区別する。
- Evidence: `tmp/issue-85-investigation/report.md`、`tmp/issue-85-task-1/implementation-report.md`、`tmp/issue-85-controller/controller-report.md`、同ディレクトリの review と実行 logs（作業 worktree 内のローカル資料）。
- 所要: 調査24分47秒、実装19分18秒、Task review約5分、controller test commands13分05秒、Final review約10分、文書fix1分37秒、re-review約2分。セッション全体は約85分（計画・記録・統合確認を含む）。
- Final review の対象外判断を確認: 空指定の追加制限は上記互換性判断を維持し、公開版/latest・rebuild・Windows/live・課金 API の保証は追加しない。任意の converter-level shared mismatch テスト追加提案は、現実装が正しく既存のadapter+E2E検査があるため今回追加しない。
- PR 作成前はローカル保持で完了し、親 checkout の origin/main detached HEAD は変更しなかった。その後、追加指示により下記の公開を実施。

## 公開記録（2026-10-11）

- ユーザーの追加指示「PRしてくださ。」に基づき、既存ブランチを origin に push し、PR #88 を main 向けに作成した。実装・設計内容は変更せず、公開状態の記録のみ更新する。内容の承認・merge・Issue close の許可とは解釈しない。
- 公開前の再確認: `uv run --frozen pytest tests/scripts/test_meshy_conversion.py -q -rs` は83 passed / skip 0（143.48秒、exit 0）。ruff、diff-check、check-layout も exit 0。ログは worktree の `tmp/issue-85-publication/conversion.log`。
- PR 本文に既存の全体テスト失敗1件と LSP／実測版／offline 範囲の制約を明記した。private repository の CI は運用上停止中のため追加のCI待ちは行わない。
- 公開元は `origin/fix/issue-85-meshy-normal-map`。PR は OPEN、draft ではない。親 checkout・world・外部リポジトリを変更せず、worktree を保持する。
