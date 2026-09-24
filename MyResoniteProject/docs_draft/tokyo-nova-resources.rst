Tokyo N◎VA 西部スラム街区 — Task 3 リソース記録
=====================================================

対象
----

Task 3 の街区拡張を再生成・検証するための記録。既存の北地区と共通環境を維持し、`TokyoNova_WestSlum` 所有ルート内だけに市街地メッシュ、施設、衝突判定、局所照明を追加する。資料との対応と創作上の区別は ``tokyo-nova-design.rst`` と ``world-reference.rst``、北地区の既存アセットは ``tokyo-nova-assets.rst`` を参照。

* 決定的な配置・seed: ``content/tokyo-nova/layout.json``（seed ``240918``）。
* 形状ソース: ``modeling/tokyo_nova/{districts,interiors,skyline}.py`` と共通 ``geometry.py`` / ``props.py``。
* Blender source: ``artifacts/tokyo-nova/city.blend``。Blender 5.0.1 で保存後に再オープンし、UV / 法線を検査した。
* 全アセット一覧・配置・材質・パーツ・寸法: ``artifacts/tokyo-nova/city-resource-report.json`` の ``city.asset_catalog``（76 kind）。
* ResoLoop 用 export: ``content/tokyo-nova/city/export/``。合成済み適用文書: ``content/tokyo-nova/city/city-apply.json``。
* 適用 state: ``.resoloop/tokyo-nova/state/blockout.json``。実行ログ・画像・接続結果は ``.resoloop/tokyo-nova/`` 配下で、街区の再生成 source には含めない。

生成
----

Blender の再生成は ResoLoop 経由で行う。北地区アセットを含めた全体 source を作る:

.. code-block:: console

   resoloop blender run modeling/tokyo_nova/build.py --arg=--sector --arg=all --arg=--output --arg=artifacts/tokyo-nova/city.blend --json

保存後に再オープン検査を通し、export 先の追加・削除・三角形・材質・draw section を確認する。既存 export を無確認で上書きしない。export の ``model.apply.json`` を layout と既存 north manifest に合成する:

.. code-block:: console

   uv run python -m modeling.tokyo_nova.pipeline --integrate-city content/tokyo-nova/city/export/model.apply.json --city-apply-output content/tokyo-nova/city/city-apply.json

合成文書は ownership key ``tokyo-nova-west-slum``、root key ``root``、expanded-node limit ``60000`` を保持する。root の位置は ``[0, 30, 120]``、回転なし・単位スケール。Plaza は root-local Y=0 に保たれるため既存 Ground を動かさない。

内容とアクセス
--------------

* **24棟**を個別の高さ・setback・用途・屋上要素で構成。素材の色替えだけの複製ではなく、長屋、診療所、浴場、共同住宅、工房、地下施設、倉庫、店舗など輪郭・設備の異なる建物群とした。
* **19施設**: 北の立ち食い屋台、端末修理・中古店、共同洗濯場、夜間食料棚、支援学習室、夜間診療室、共同浴場、寄り合い長屋、補修・溶接ヤード、小型機械工房、地下小劇場、古着仕立て・縫い直し、転用倉庫、蓄電池交換所、地下酒場「余白」、再生材置場、お守りと修繕糸、中古ゲーム卓、共同炊事場。
* **18のアクセス確認対象**（16室内＋屋上アクセス2か所）。扉開口、扉前 corridor、可視パーツ由来 collider、階段・屋上 ramp/rail、および route 接続を出力形状と照合する。案内文だけの理想化 registry は使わない。
* 中央広場は連続 **20 × 20 m = 400 m²**。浅いひび・補修・水濡れ表現を歩行面から分離し、四方の進入口、二つの周回路、屋上への連続経路を配置した。
* **76種類**の用途別 prop をカタログ化。雨樋・AC・ダクト・計器・排水、家具・洗濯・炊事、端末・診療用具・関節外装、教材・寝具、台車・ホイスト・静的二輪部品、シアター・アーケード・縫製・お守り・倉庫用品など。内訳は resource report を正とする。
* 日本語の施設名は今回の創作。実在企業名・公式施設の移設・確認していない図版の再現ではない。資料の根拠と不採用事項は ``world-reference.rst`` に記録。

リソース実測
------------

Blender 再オープン後の値と ResoLoop export 値は異なる集計段階のため併記する。

+-------------------+-------------+-------------+-------------+----------------+
| セクター          | assemblies  | named parts | triangles   | mesh batches   |
+===================+=============+=============+=============+================+
| 北地区            | 6           | 423         | 12,599      | 51             |
+-------------------+-------------+-------------+-------------+----------------+
| 新規建築・街路    | 21          | 2,797       | 52,636      | 11             |
+-------------------+-------------+-------------+-------------+----------------+
| 室内・prop        | 114         | 806         | 22,664      | 18             |
+-------------------+-------------+-------------+-------------+----------------+
| skyline / sky     | 3           | 250         | 4,680       | 9              |
+-------------------+-------------+-------------+-------------+----------------+
| **合計**          | **144**     | **4,276**   | **92,579**  | **89**         |
+-------------------+-------------+-------------+-------------+----------------+

* Blender source: 55,128 vertices、89 mesh objects（北地区51、新規38）、89/89 UV 対応。resource report の valid-normal polygons は45,147。
* ResoLoop export: 194,469 vertices、79,980 triangles、15 materials、38 draw sections、38 mesh assets。実時間描画用に静的 material batch へまとめた後の値。
* Exporter の既定目安を超える警告が3件ある: 50,000 triangles、8 materials、16 draw sections。内容は上の通り **79,980 / 15 / 38**。この density とマテリアル/描画区分は意図的に維持したが、対象視距離と実機性能の測定は未完了。負荷が問題になる場合は silhouette/detail の優先度をレビューしてから atlas / shared batch 化を検討する。
* live export に画像 texture はない。Principled の色・metallic・roughness、形状化した錆・ひび・補修跡、および濡れ/乾き材質で構成する。画像転送・texture sampling は本 Task の達成事項に数えない。
* 衝突判定は可視建築・床・rail 等から抽出した **1,362件**の plan。建物ごとの安定 Slot 群の下に native collider を置く。既存北地区の個別 collider はそのまま保持。
* owned native point light は **12灯**。内向き dome、cloud/horizon glow、遠景 silhouette は街区所有メッシュ。Global Skybox / world lighting は変更していない。
* 音、fan/steam/drip motion、avatar/spawn 操作は追加していない。

検証・適用
----------

.. code-block:: console

   resoloop validate content/tokyo-nova/city/city-apply.json --json
   resoloop validate content/tokyo-nova/city/city-apply.json --strict --url ws://localhost:54238/ --json
   resoloop diff content/tokyo-nova/city/city-apply.json --changes-only --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/
   resoloop apply content/tokyo-nova/city/city-apply.json --ndjson-progress --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/
   resoloop test content/tokyo-nova/city/city-apply.json --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/

offline validation: 493 slots / 2,367 components / 765 references、strict: 493 / 2,368 / 765。どちらも valid、issue 0。plan は assets 38 create、Slots 91 create、Components 1,467 create / 344 update、delete 0。344 updates は既存 ``BLOCKOUT`` の汎用 MeshRenderer / BoxCollider（各172件）だけで、完成メッシュと geometry-derived collider へ置き換えるための更新。placeholder Slot は削除せず、root/global/shared content は変更しない。

apply は exit 0。Slot 91 created / 402 unchanged / 0 deleted、Component 1,467 added / 344 updated / 557 unchanged / 0 deleted、38 assets imported / 51 reused。適用後に root ``TokyoNova_WestSlum`` の transform ``[0, 30, 120]``、plaza、city mesh group、21個の建物 collider group、12灯、既存 north mesh/sign/AR/collision group を再観測した。delete は0。同じ文書と state の再 apply も exit 0 で、Slot / Component の create / update / delete 0、89 assets unchanged。

``resoloop test`` は1/1 passだが ``structuralOnly=true`` / ``verification=partial``。実際のアバター操作や歩行を試す probe は含まない。world save/reload も実施していないため、Resonite セッション上の変更とローカルに保存した成果物を区別し、永続保存済みとは扱わない。

画像レビューと制約
------------------

CPU Cycles の offline preview（640 × 360、8 samples）を以下に保存した。保存対象の manifest / mesh ではなく、geometry-only の確認画像である。

* ``.resoloop/tokyo-nova/task3-render/city-overhead-offline.png`` — 広場と街区全体。
* ``.resoloop/tokyo-nova/task3-render/plaza-eye-offline.png`` — 目線の広場・入口。
* ``.resoloop/tokyo-nova/task3-render/clinic-interior-offline.png``、``theatre-interior-offline.png`` — 室内の構成。
* ``.resoloop/tokyo-nova/task3-render/roof-overlook-offline.png`` — 屋上 rail と遠景。

1回目の室内 image は低光量で部品が読みにくかったため、確認 render 中だけ材料 base color の emission ``0.18`` を使って診療台・カーテン・道具と theater prop の位置を見やすくした。材料値を render 後に復元し、保存した ``city.blend`` と live manifest に preview light/emission は含めていない。広場/屋上の画像は暗い夜景として意図した範囲だが、低 sample の noise と Resonite runtime exposure の影響は残る。

live ``resoloop capture`` を ``plaza_north_eye`` で90秒試したが、Resonite の screenshot export から ``CAPTURE_EXPORT_TIMEOUT`` が返り、実画像は得られなかった。終了後に ``InteractiveCamera`` を find し、temporary camera が残っていないことを確認。したがって live exterior / interior / roof の見え方、日本語の可読性、VR 歩行・collider feel は未検証。内外の最終明るさを offline preview だけで保証しない。
