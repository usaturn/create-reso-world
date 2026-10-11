# Issue #85: Meshy GLB の tangent normal UV 指定を安全に正規化する

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/85
- 参考: https://github.com/usaturn/resoloop/issues/17
- 調査したコード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`
- 状態: draft（内容の個別承認は未取得）
- 関連 Plan: `docs/superpowers/plans/2026-10-11-create-reso-world-issue-85-meshy-normal-map.md`
- 実行許可: ユーザーの「途中で止めずに推奨案で完了する」により、質問・Spec/Plan 承認待ちを省略し、下記の狭い修正を実行する。承認済みと推測しない。
- 公開: 未実施。push・PR 作成・merge・Issue close は今回の実行許可に含めない。
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
