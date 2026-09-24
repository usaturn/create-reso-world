TokyoNova 北地区・詳細アセット
===============================

この文書は Task 2 で追加した北地区の Blender アセット、公開ヘルパー API、再生成・適用手順と、検証上の制約を記録する。街区レイアウトと所有ルートは Task 1 のものを使い、Resonite 上の変更は ResoLoop 経由で既存の ``TokyoNova_WestSlum`` 配下に限定する。

構成
----

* ``modeling/tokyo_nova/geometry.py`` — 決定的なメッシュプリミティブ。
* ``modeling/tokyo_nova/materials.py`` — 共有 Principled マテリアル設定と Blender 材料生成。
* ``modeling/tokyo_nova/props.py`` — 名前付きパーツから成る再利用可能アセンブリ。
* ``modeling/tokyo_nova/north.py`` — 北地区カタログ、配置、物理看板と独立表示可能な AR 表示。
* ``modeling/tokyo_nova/build.py`` — 編集可能な Blender source、UV / normal 検査、resource report。
* ``modeling/tokyo_nova/sector_pipeline.py`` — Blender export を既存の所有 manifest に安全に合成。
* ``content/tokyo-nova/layout.json`` — seed と街区配置、北地区アセット宣言。
* ``content/tokyo-nova/north/export/`` — ResoLoop 用の material batch mesh、``model.apply.json``、export report。
* ``content/tokyo-nova/north/north-apply.json`` — 既存 blockout と合成した適用 manifest。
* ``artifacts/tokyo-nova/north.blend`` — Blender 5.0.1 で再オープンを確認した編集可能 source。生成 binary は Git に含めず、``artifacts/tokyo-nova/north-resource-report.json`` に集計を保存する。

座標は全て Resonite の XYZ（Y-up、メートル）。Blender 境界で一度だけ XZY に変換する。詳細アセットは所有 root の子 Slot 内のメッシュ頂点に位置を焼き込むため、親 root の world pose や既存 Ground の高さを変更しない。

再利用 API
----------

``modeling.tokyo_nova.geometry``:

* ``mesh(name, vertices, faces, material) -> MeshData`` — index を検査した任意ポリゴン。
* ``box(name, center, size, material) -> MeshData`` — center 基準の六面体。
* ``beveled_box(name, center, size, bevel, material) -> MeshData`` — 厚みを保持する面取り box。
* ``cylinder(name, center, radius, depth, material, segments=16) -> MeshData`` — Y 軸方向の蓋付き円柱。
* ``pipe(name, start, end, radius, material, segments=8) -> MeshData`` — 任意の二点間の閉じた管。

全寸法はメートル。 ``MeshData`` は検査済み vertex / face と material key を保持する immutable dataclass である。

``modeling.tokyo_nova.materials``:

* ``build_materials() -> dict[str, dict[str, Any]]`` は編集可能な値の独立コピーを返す。
* ``make_blender_materials() -> dict[str, Any]`` は Blender の ``bpy`` 内で共有 Principled 材料を作る。

``modeling.tokyo_nova.props``:

* ``create(kind: str, origin: tuple[float, float, float], rotation: float = 0) -> Assembly`` は origin（Resonite XYZ、m）と world-up 回りの yaw（rad）を受け、識別可能な全パーツを返す。
* ``modeled_kinds() -> tuple[str, ...]`` は対応 kind を安定順で返す。
* ``Assembly.bounds`` は配置済み AABB、``Assembly.transformed_parts()`` は yaw と origin を頂点に焼き込んだ ``MeshData`` 群。
* 現在の kind は ``food_stall``、``terminal_repair``、``patched_housing_facade``、``pocket_phone``。

``modeling.tokyo_nova.north``:

* ``asset_catalog() -> list[dict[str, Any]]`` は寸法、材質、部品、摩耗、配置、認識特徴を含む宣言を返す。
* ``build_north_sector(layout: dict[str, Any]) -> list[Assembly]`` は layout の stable building key を使って詳細アセット、濡れ / 乾き分けした舗装、共用 canopy、AR panel を配置する。
* ``sign_manifest_entries(layout: dict[str, Any]) -> dict[str, Any]`` は物理看板と AR 表示の別々の Slot 群を返す。

``modeling.tokyo_nova.build`` と ``sector_pipeline``:

* ``resource_report(assemblies, layout=None) -> dict[str, Any]`` は実パーツ由来の batch / vertex / triangle 数、bounds、material を集計する。
* ``build_blend(layout_path: Path, output_path: Path) -> dict[str, Any]`` は Blender で source collection と preview-only collection を生成し、保存後に再オープンして mesh / UV / normal を検査する。
* ``enrich_layout(layout) -> dict[str, Any]`` は入力を変更せず north catalog を追加する。
* ``integrate_north_manifest(base_path: Path, export_path: Path, output_path: Path) -> dict[str, Any]`` は stable root / ownership key を検査し、export asset を相対 path にして合成する。既存 north のキーだけを置換し、未確認 ID や他所有物を prune しない。

アセット内容
------------

* **立ち食い屋台** — 取り替え跡のある波板庇、補強、縁付きカウンター、蓋・取っ手付き寸胴、器・箸・調味料、再利用容器、冷蔵カウンター、通気口、ファン、錆筋。
* **端末修理 / 中古店** — 開口とガラスのある店構え、45 cm モニター、35 cm 端末箱と着脱蓋、作業トレイ、部品箱、精密ドライバー、熱風器、はんだごて、ケーブル、作業灯。
* **補修長屋正面** — 実際のドア / 窓開口、深い窓枠、異なる雨戸、ひび割れ・補修跡・塗膜欠け、手すり付き上部増築、洗濯物、換気ルーバー付き AC、雨樋、サービス配線。
* **修理台の携帯端末** — body bounds ``[0.075, 0.008, 0.150] m``（幅・厚み・長さ）。角丸筐体、独立画面、ボタン、三眼カメラ、フラッシュ、取り外し可能な背面、端子とスピーカー溝。
* **街路 / 表示** — 濡れ・乾きの舗装、浅い水たまり、亀裂、排水溝、施設間の庇とサービス tray。物理日本語サインは AR と別 Slot。AR menu は ``0.8 × 0.5 m``、修理広告は ``2.0 × 0.7 m`` で、それぞれ独立して非表示にできる。

物理看板には ``FrooxEngine.TextRenderer`` を使う。低輝度の色味は定常で、点滅は追加しない。AR は都市形状や物理看板を隠さない薄い補助表示である。

再生成・export・適用
--------------------

既存環境の Blender は ResoLoop 経由で使う。新しい Blender をインストールしない。

.. code-block:: console

   resoloop blender run modeling/tokyo_nova/build.py --arg=--sector --arg=north --arg=--output --arg=artifacts/tokyo-nova/north.blend --json
   resoloop blender export artifacts/tokyo-nova/north.blend --output content/tokyo-nova/north/export --parent Root --name TokyoNovaNorth --collection TokyoNovaNorth --json

export 後は生成された ``model.apply.json`` を review し、Python の ``integrate_north_manifest`` に以下のように渡して既存 Task 1 blockout と合成する。

.. code-block:: python

   from pathlib import Path
   from modeling.tokyo_nova.sector_pipeline import integrate_north_manifest

   integrate_north_manifest(
       Path("content/tokyo-nova/blockout.json"),
       Path("content/tokyo-nova/north/export/model.apply.json"),
       Path("content/tokyo-nova/north/north-apply.json"),
   )

manifest は実際の行き先を再確認してから同じ state で検証・plan・apply する。

.. code-block:: console

   resoloop validate content/tokyo-nova/north/north-apply.json --json
   resoloop validate content/tokyo-nova/north/north-apply.json --strict --url ws://localhost:54238/ --json
   resoloop diff content/tokyo-nova/north/north-apply.json --changes-only --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/
   resoloop diff content/tokyo-nova/north/north-apply.json --deletes-only --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/
   resoloop apply content/tokyo-nova/north/north-apply.json --json --state .resoloop/tokyo-nova/state/blockout.json --url ws://localhost:54238/

この手順では ``--prune`` を追加しない。manifest key、asset path、delete 候補を個別確認し、同じ apply を再実行して書き込み 0 を確認する。再接続したときも state を引き継ぎ、ResoLoop ID は再観測する。

検証と制約
----------

Task 2 の source report は seed ``240918``、8 assembly、431 editable parts、11,834 vertices、16,351 triangles、17 shared materials、57 assembly/material mesh batch。保存後に Blender file を再オープンし、57/57 batch が UV を持つことを確認した。

画像素材の Windows host path import は共有 mount がなく ``ASSET_SOURCE_NOT_FOUND`` となった。north export に画像をあるかのように含めず、対応済み Principled base color / metallic / roughness と、個別の摩耗・ひび・錆筋・濡れ / 乾きの形状で置き換えた。 ``materials.ADAPTATION_NOTE`` にも明記する。Blender process は ``libEGL.so.1`` がなく、preview render は未実行。ResoLoop capture は前 Task 1 で有効な ``plaza_north_eye`` bookmark の export が ``CAPTURE_EXPORT_TIMEOUT`` となったため、北地区 / 携帯端末の runtime image は得られていない。従って silhouette、実画面上の日本語、実照明下の roughness / exposure の視覚評価は未実施であり、確認済みとは扱わない。

Task 2 の再適用、構造・リソース数、各マテリアル batch の UV / normals は構造上の検証であり、VR 内の歩行感や保存後の再読込を示すものではない。
