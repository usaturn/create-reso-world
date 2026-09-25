# slum02 作業時間記録

| Task | 着手 | 完了 | 所要 | メモ |
|---|---|---|---|---|
| Task 0 | 2026-09-25T16:21:51Z | 2026-09-25T16:22:39Z | 約1分 | スキャフォールド一式・フォント取得・スモークテスト・疎通確認 |
| Task 1 | 2026-09-25T16:25:35Z | 2026-09-25T16:28:39Z | 約3分 | geometry.py 実装（akichi 移植 + 開口壁/チューブ/Assembly統合）、TDD RED→GREEN |
| Task 2 | 2026-09-25T16:32:09Z | 2026-09-25T16:33:44Z | 約2分 | materials.py（44素材 + NOISES 6種 + make_blender_materials）、vcolor.py（value_noise3 + 5段階汚れマスク）実装、TDD RED→GREEN、テスト9件は初回で全通過（マスク定数の調整なし） |
| Task 3 | 2026-09-25T16:37:52Z | 2026-09-25T16:48:00Z | 約10分 | layout.py（決定論レイアウト・検証・視線レイキャスト）+ layout.json、TDD RED→GREEN、視線遮断は初回で失敗 0（高さ調整なし）、tower-20 を lane との衝突回避のため変更、小屋候補領域を絞り込み |
| Task 4 | 2026-09-25T16:53:45Z | 2026-09-25T16:58:00Z | 約4分 | sectors/blender_io/build/preview/uv 移植、Blender 5.0.1 API 実測、頂点カラー色空間実測（Linear, FLOAT_COLOR/POINT）、AO ベイク＋プレビューのスモーク。Eevee は libEGL 不在で abort するため Cycles を事前選択 |
