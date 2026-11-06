# Issue #315 Meshy wrapper に remesh（三角形数の削減）を追加する 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/315（#103 で wrapper を撤去するまでのつなぎ）
- 実行許可: 利用者の指示 `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/315 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- 作業中の利用者の追加指示（2026-11-07）: 「テストを作りすぎないようにしてください。このラッパーはいずれ削除することになります。」
- 許可された範囲: create-reso-world の `scripts/meshy.py`・`scripts/meshy_workflow.py`・`scripts/meshy_cli_guard.mjs`・`tests/scripts/test_meshy.py`・`docs/meshy-resoloop.md`・`.agents/skills/meshy-resoloop/SKILL.md`・この Spec と Plan の変更。Meshy の有料の API（生成・remesh）はこの run では送信しない（D9）
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` の `main`（`refs/heads/main`）`28ef59b17a94191663597c927e66791425a3a864`。親 Issue・handoff の base の要求は無い

## 目的

API で生成した Meshy のモデルを、Meshy 側で remesh してから、remesh 後のモデルだけをダウンロードできるようにする。生成直後のモデル（例: 客 A は 257 万三角形）を、VR ワールドに複数体並べられる 20,000〜40,000 三角形程度にする。巨大な GLB の転送とローカルでの再ベイクを避ける。remesh に課金する前に、生成結果をサムネイルだけで確認できるようにする。

## 確かめた事実（2026-11-07）

1. 導入済みの meshy-cli は 0.4.0。`remesh create` は `--input-task-id`・`--model-url`・`--topology`・`--target-polycount`・`--decimation-mode`・`--target-formats` と共通の `--async`・`--operation-id`・`--data` を持ち、`--data` の JSON に既定の `{"target_formats": ["glb"]}` とフラグを重ねる（`dist/cmd/remesh.js`・`dist/internal/task-command.js`）。`--model-url` はローカルのファイルパスも受け付け、そのファイルを送る
2. CLI の resource の登録（`dist/client/resource-registry.js`）では、remesh の resource は `remesh`、task の type は `remesh`。task view の `resource` は登録の id、`type` は API の `type` をそのまま返す（`dist/internal/task-view.js`）。journal の `resource` も登録の id（`remesh`）になる
3. サムネイルの asset key は `thumbnail.primary`（`thumbnail_url`、ファイル名 `thumbnail.png`）。`download --resource <id> --task-id <id> --asset thumbnail.primary --output-dir <dir>` で、その asset だけを取得する（`dist/internal/artifacts.js`・`dist/cmd/download.js`）。取得の manifest の各ファイルは `key`・`path`・`status` を持つ
4. wrapper の守りの場所: kind と resource は `RESOURCES`（`list --resource` の選択肢）、`plan`、`load_operation`（`convert` もここを通る）、`_validate_request`、attach の `expected_type` で決まる。`submit()` は `--confirm-paid` の必須、一度だけの送信、`submitting` / `unknown` での再送の拒否を kind によらず行う。refine は有料の POST の前に `text-to-3d get` で preview を確かめる
5. `scripts/meshy_cli_guard.mjs` は journal の `resource` を `text-to-3d` / `image-to-3d` に限っており、remesh の journal の書き込みを拒否する（送信の前に CLI が `local_io` で止まる）
6. `convert`（`scripts/meshy_conversion.py`）は `load_operation` を通り、kind・resource を見ない。`downloads.state == completed` と key `model.glb` の主 GLB を求める
7. このコンテナに、wrapper で作った成功済みの image operation（`content/generated/meshy/*/operation.json`）は無い（ファイルシステム全体を探して 0 件）。客 A の生成物も見つからない。remesh 後の実 GLB も無い（`tmp/Meshy_Ornate_Silver_Monocle.glb` は remesh 前の 1,123,050 三角形、remesh 後のものは `tmp/Ornate_Monocle/Ornate_Monocle.blend` だけ）
8. `docs/meshy-resoloop.md` の「課金の承認」と `.agents/skills/meshy-resoloop/SKILL.md` の手順 4 は、submit の前に、生成対象・operation 名・送信件数・予算上限・モデル・画像の外部送信を明示した許可を求める

## 決定記録

### D1. remesh の指定と保存する request

- 選択した案: `plan --kind remesh --source-operation <name> [--target-polycount N] [--topology triangle|quad]`。`--target-polycount` は 100〜300,000 の整数で既定 30,000、`--topology` の既定は `triangle`。request は `{"payload": {"input_task_id", "target_polycount", "topology", "target_formats": ["glb"]}, "source_operation": <name>}`、resource は `remesh`。`--source-operation`・`--target-polycount`・`--topology` は remesh 以外の kind では拒否し、remesh では `--prompt`・`--image`・`--preview-task-id`・`--texture` を拒否する。`--model`・`--pbr`・`--texture-resolution` は既定値を持つので、remesh では使わない（help に書く）
- 検討した別案:
  - `--source-task-id` で task ID を直接受け取る: 元の operation の kind・status を確かめられず、別の生成物を誤って指す
  - 元の operation の記録に remesh の結果を書き足す: Issue の「元の operation の記録は読むだけで書き換えない」に反し、download・convert の記録と混ざる
- 選択理由: Issue の提案 1・2 のとおり。remesh の結果は別の operation になり、既存の download・convert・attach をそのまま使える。remesh 以外の kind で remesh の引数を受け付けると、image の生成時に remesh も指定したと誤解したまま、remesh されない生成に課金する（Issue の提案 7 の対象外）
- 委任指示: issue-to-pr の推奨案での委任

### D2. plan での元の operation の確認

- 選択した案: plan は `load_operation` で元の operation を読み、kind が `image`、task ID があり、status が `SUCCEEDED` であることを確かめて、task ID を `input_task_id` に保存する。元の operation のロックは取らず、ファイルを書かない
- 検討した別案: 元の operation のロックを取る（`.lock` を作り得るので、元の operation のディレクトリを変える）
- 選択理由: 元の記録は `save_operation` が一括で置き換えるので、読むだけなら途中状態を読まない。plan の確認は使い勝手のためで、守りの本体は D3 の送信前の確認
- 委任指示: issue-to-pr の推奨案での委任

### D3. 送信の前の確認

- 選択した案: `submit()` を共通のまま使い、remesh では有料の POST の前に `image-to-3d get <input_task_id>` を呼ぶ。ok、返った ID の一致、status `SUCCEEDED`、type `image-to-3d`、resource `image-to-3d` のどれかが外れたら、`successful_image_task_required` で止まり、create を呼ばない（stage は `planned` のまま）。create は `remesh create --async --operation-id <uuid> --data <payload>` で、`--model-url` などのフラグを渡さない
- 検討した別案: GET の `expires_at` で期限切れを送信の前に判定する（値の意味が文書・実測で確かめられていない）
- 選択理由: Issue の提案 3。保持期間を過ぎて削除された task は GET が失敗する見込みで、その場合も create の前に止まる（実際の応答は未確認。D9）
- 委任指示: issue-to-pr の推奨案での委任

### D4. 保存した request の検査

- 選択した案: `_validate_request` に remesh を足す。request の項目は `payload`・`source_operation` だけ、payload の項目は `input_task_id`・`target_polycount`・`topology`・`target_formats` だけ（集合の一致）。`input_task_id` は task ID の形、`target_polycount` は bool でない整数で 100〜300,000、`topology` は `triangle` / `quad`、`target_formats` は `["glb"]`、`source_operation` は operation 名の形、resource は `remesh`
- 選択理由: Issue の提案 4。`model_url`（ローカルのファイルが送られる）・`decimation_mode`・`resize_*`・`auto_size` などを、項目の集合の一致でまとめて拒否する
- 委任指示: issue-to-pr の推奨案での委任

### D5. サムネイルだけの取得

- 選択した案: 新しいコマンド `thumbnail --operation <name> [--timeout]`。task ID があり status が `SUCCEEDED` の operation（kind は問わない）について、`download --resource <resource> --task-id <id> --asset thumbnail.primary --overwrite --output-dir <operation>/thumbnail` を呼ぶ。manifest が `completed` で、ファイルが 1 件だけ、key が `thumbnail.primary`、status が `written` / `skipped`、パスが `thumbnail/` の中で symlink でなく実在することを確かめ、パス・byte 数・SHA-256 を出力する。operation.json は書かない
- 検討した別案:
  - `download --thumbnail`: download の状態（`downloads`・stage）を変える処理と分岐が混ざる
  - サムネイルの取得を operation.json に記録する: 記録を書かなければ、完了した download の記録を壊しようがない。出力の JSON とファイルで足りる
- 選択理由: Issue の提案 6。GLB を取得せず、`downloads` の記録（完了した manifest を含む）を変えない。保存先を `source/` と分けるので、convert の主 GLB の選択にも混ざらない
- 委任指示: issue-to-pr の推奨案での委任

### D6. kind・resource の追加と journal のガード

- 選択した案: `RESOURCES` に `remesh`（`list --resource remesh`）、`load_operation` の kind に `remesh`、attach の `expected_type` に `remesh: "remesh"` を足す。`scripts/meshy_cli_guard.mjs` の journal の `resource` に `remesh` を許可する。status・wait・download・convert は既存の処理のまま remesh の operation に使える（resource の `remesh get` / `wait`、`download --resource remesh --all`）
- 選択理由: Issue の提案 5。ほかの検査（版・state・fingerprint・パス・秘密情報の除去）は変えない
- 委任指示: issue-to-pr の推奨案での委任

### D7. 文書

- 選択した案: `docs/meshy-resoloop.md` に「Remesh: 三角形数を減らす」の節を足す（サムネイルの確認 → remesh の plan → 承認 → submit → wait → download → convert、生成から 3 日以内に終えること、期限切れなら生成し直すこと、体ごとの三角形数の目安）。attach の type の一覧、list の例、未検証の範囲にも remesh を足す。`.agents/skills/meshy-resoloop/SKILL.md` の手順に 1 行だけ足す
- 検討した別案: SKILL.md を変えない（エージェントが remesh を知らずに、ローカルで減らす旧来の手順を選ぶ）
- 選択理由: Issue の提案 9。#103 で wrapper と一緒に撤去されるので、SKILL.md は最小の追記にとどめる
- 委任指示: issue-to-pr の推奨案での委任

### D8. テスト

- 選択した案: Issue の「テスト方針」の S だけを書く。利用者の追加指示（作りすぎない）に従い、テストの関数は 3 つと、既存の attach のテストの組み合わせ 1 つにする
  1. remesh の送信前の確認と元の記録（1 関数）: 元の task が成功していない・type が違う・ID が違うときに create を呼ばない（各組み合わせの後に、正しい応答で送信が通る）。plan・submit・download の前後で、元の operation のディレクトリが変わらない
  2. 書き換えた remesh の request の `model_url` を拒否し、CLI を呼ばない（1 関数）
  3. attach の種別の確認: 既存の `ATTACH_KINDS` に remesh を足す（既存の 2 関数の組み合わせが増える）
  4. サムネイルの取得が、完了した download の記録と `source/` を変えず、`--all` でなく `thumbnail.primary` だけを取得する（1 関数）
- テストにしないもの: `--confirm-paid` なしの拒否・二重送信・`unknown` での再送の拒否（共通の `submit()` の既存のテストで確かめている。D）、journal のガードへの許可の足し忘れ（送信の前に CLI がエラーで止まる。L）、引数の解析・plan での元の operation の確認・polycount の範囲（エラーで止まる。plan の確認が壊れても D3 で止まる。L・D）。これらは fixture での実行と `help` の実行で確かめる
- 委任指示: issue-to-pr の推奨案での委任と、利用者の追加指示

### D9. 有料の実機確認

- 選択した案: この run では Meshy の有料の API（image の生成・remesh）を送信しない。受け入れ基準の「実入力」（3 日以内・100 万三角形超の image operation を remesh して 24,000〜36,000 三角形、テクスチャの保持、元の GLB を取得しない）と、Issue の「確認が必要な点」（テクスチャの保持・topology の差・期限切れの応答）は、マージの後に利用者の許可を得て確かめる項目として残す。PR は `Refs #315` とし、Issue に手順をコメントする
- 検討した別案: Issue の「有料の実行は、元の生成と remesh の各 1 回に限る」を許可とみなして送信する
- 選択理由: 3 日以内の wrapper の image operation が無く（事実 7）、remesh の前に新しい image の生成が要る。どの画像を外部へ送り、どのプロジェクト・operation 名で生成するかは Issue に書かれておらず、`docs/meshy-resoloop.md` と SKILL.md の課金の承認（事実 8）を満たさない。委任された推奨案の範囲で課金の対象を推測しない
- 停止条件: 該当しない（有料の確認を除いた実装・検証・PR は進める）

### D10. 実 GLB での convert の確認

- 選択した案: remesh 後の実 GLB が無いので（事実 7）、この run のセッションディレクトリ（`tmp/agents/issue-315.*`）に作る一時プロジェクトで、kind `remesh`・resource `remesh` の operation の記録（`downloads` が `completed`、key `model.glb`）に、Meshy の実 GLB（`tmp/Meshy_Ornate_Silver_Monocle.glb` の写し、remesh 前）を置いて `convert` を実行する。remesh の operation が `load_operation` と convert を通ることと、Meshy の GLB（法線マップ付き）の変換が通ることを確かめる。remesh 後の GLB での確認は D9 の残りに含める
- 検討した別案: Blender で `Ornate_Monocle.blend` を GLB に書き出して使う（Meshy の出力ではないので、remesh 後の GLB の確認にならない）
- 選択理由: 無料・offline で、Issue の提案 8 のうち確かめられる部分を確かめる。結果は remesh 後の GLB の確認と読み替えない
- 委任指示: issue-to-pr の推奨案での委任

### D11. 実行方式

- 選択した案: `superpowers:executing-plans`（このセッションが inline で実装する）
- 検討した別案: `superpowers:subagent-driven-development`
- 選択理由: Task が同じファイル（`scripts/meshy_workflow.py`・`tests/scripts/test_meshy.py`）を順に変える。`implement_task.py check` の `self` が true
- 委任指示: issue-to-pr の 4 章の表

### D12. 担当とループのオプション

- Plan の Task の担当: `self`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。`--implement` の指定なし）
- ループのオプション: 利用者の指定なし。既定の適用で、サイクルの上限 3、レビュアー `cursor_grok4_xhigh`・`devin_swe2-max_default`・`pi_commandcode_deepseek4-flash_max`、修正の担当 `claude-code_opus_default`、自己レビュー・fix-check は `self`（`loop.py check-options` の出力）

## 受け入れ基準

### この run で確かめる

- 動作環境: Dev Container 内で `uv run --no-project scripts/meshy.py` を実行できる（meshy-cli 0.4.0、Blender 5.0.1）
- 実入力（fixture）: 成功済みの image operation を元に `plan --kind remesh --source-operation <name> --target-polycount 30000 --topology triangle` で request を作り、偽の CLI に対して submit・wait・download・convert の前段まで進む。create の `--data` は `{"input_task_id": <元の task ID>, "target_polycount": 30000, "topology": "triangle", "target_formats": ["glb"]}` だけ
- 実入力（実 GLB）: D10 の一時プロジェクトで、remesh の operation の convert が成功し、report の `triangles` が出る
- 防御範囲:
  - `--confirm-paid` なしでは送信しない。同じ operation の二重送信、`submitting` / `unknown` での再送をしない（共通の `submit()`）
  - 元の task が成功していない・type が違う・ID が違うときは create を呼ばない
  - remesh の plan・submit・download で、元の operation の記録（ディレクトリの中身）が変わらない
  - 保存した request に `model_url` などを足すと送信しない
  - サムネイルの取得は、完了した download の記録と `source/` を変えず、GLB を取得しない
  - キーを表示・保存しない（既存の守り）
- 対象外の反例: `text` / `image` / `refine` の既存の挙動は変わらない（既存のテスト 138 件が通る）。`image` 以外の operation や、成功していない operation は remesh の元にできない（plan で止まる。fixture で確かめる）。remesh 以外の kind に `--target-polycount` などを付けると plan で止まる

### マージの後に利用者の許可を得て確かめる（D9）

- 生成から 3 日以内の、三角形数 100 万超の成功済み image operation を、サムネイルで確認してから `topology=triangle`・`target_polycount=30000` で remesh し、ダウンロードした GLB の三角形数（`convert` の report の `triangles`）が 24,000〜36,000 になり、テクスチャが保持され、元の GLB がダウンロードされない。範囲を外れたら数値を記録して利用者が判断する
- remesh 後の実 GLB で `convert` が通る
- `topology` による見た目の差、保持期間を過ぎた元の task を remesh しようとしたときの API の応答

## 対象外

- 画像から 3D 化の作成時に remesh を同時に指定する方法（Issue の提案 7）
- `image` 以外の operation（`text` / `refine` など）や `model_url` を remesh の元にすること
- remesh の要件を Meshy プラグインへ引き継ぐか（#103 で決める）
- クレジットの消費量の実測・最適化
