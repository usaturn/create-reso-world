# Issue #315 Meshy wrapper の remesh 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の run の実行許可で実行する。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/315
- base: `main` `28ef59b17a94191663597c927e66791425a3a864`

**Goal:** wrapper に `--kind remesh` と `thumbnail` コマンドを足し、成功済みの image operation を Meshy 側で remesh して、remesh 後の GLB だけを取得できるようにする。

**Architecture:** remesh は別の operation として保存し、共通の `submit()`（一度だけの送信）・`query()`・`download()` をそのまま通す。送信の前に `image-to-3d get` で元の task を確かめる。サムネイルは operation.json を書かずに `thumbnail/` へ取得する。

**Tech Stack:** Python 標準ライブラリ（`uv run --no-project`）、meshy-cli 0.4.0、Node の preload（`scripts/meshy_cli_guard.mjs`）、pytest（偽の `meshy` CLI）。

**Spec:** `docs/superpowers/specs/2026-11-07-issue-315-meshy-remesh-design.md`

## Global Constraints

- `--target-polycount` は 100〜300,000 の整数、既定 30,000。`--topology` は `triangle`（既定）か `quad`。`target_formats` は `["glb"]` に固定
- 保存する remesh の request は `{"payload": {"input_task_id", "target_polycount", "topology", "target_formats"}, "source_operation"}` だけ。resource は `remesh`
- 元の operation は読むだけで、ロックもファイルの書き込みもしない
- `text` / `image` / `refine` の既存の挙動を変えない
- テストは Spec の D8 の 3 関数と `ATTACH_KINDS` の 1 組み合わせだけ（利用者の指示「テストを作りすぎない」）
- Meshy の有料の API は送信しない（Spec の D9）。偽の CLI だけを使う

## Review Focus

- remesh の task に `thumbnail_url` が無いとき: `thumbnail` は CLI のエラーで `thumbnail_download_failed` になり、operation.json を変えない（書かない設計なので、テストは足さない）
- remesh 以外の kind に `--target-polycount`・`--topology`・`--source-operation` を付けたとき: plan で止まり、operation を作らない（Task 4 の fixture の実行で確かめる）
- 元の operation が image でない・成功していない・task ID が無いとき: plan で止まる（Task 4 の fixture の実行）。壊れても送信の前の確認（Task 1 のテスト）で止まる
- `--target-polycount` が範囲外・整数でないとき: plan で止まる（Task 4 の fixture の実行）
- `list --resource remesh` と remesh の operation の `status` / `wait` / `download` が `remesh` の resource で CLI を呼ぶ（Task 1 のテストの download の引数と、Task 4 の fixture の実行）

## 受け入れ基準

Spec の「受け入れ基準」の「この run で確かめる」と同じ。

- 動作環境: Dev Container 内で `uv run --no-project scripts/meshy.py` を実行できる（meshy-cli 0.4.0、Blender 5.0.1）
- 実入力（fixture）: 成功済みの image operation を元に `plan --kind remesh --source-operation <name> --target-polycount 30000 --topology triangle` で request を作り、偽の CLI に対して submit・wait・download まで進む。create の `--data` は `{"input_task_id": <元の task ID>, "target_polycount": 30000, "topology": "triangle", "target_formats": ["glb"]}` だけ
- 実入力（実 GLB）: Spec の D10 の一時プロジェクトで、remesh の operation の convert が成功し、report の `triangles` が出る
- 防御範囲: `--confirm-paid` なしでは送信しない。二重送信・`submitting` / `unknown` での再送をしない（共通の `submit()`）。元の task が成功していない・type が違う・ID が違うときは create を呼ばない。remesh の plan・submit・download で元の operation のディレクトリが変わらない。保存した request に `model_url` などを足すと送信しない。サムネイルの取得は完了した download の記録と `source/` を変えず、GLB を取得しない。キーを表示・保存しない
- 対象外の反例: 既存のテスト 138 件が通る。image 以外・成功していない operation を元にした remesh、remesh 以外の kind への remesh の引数は plan で止まる

## 要件の対応メモ

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| D1・D2 plan と request | 1 | operation.json の request・resource | Task 1 のテスト、Task 4 の fixture |
| D3 送信の前の確認 | 1 | create の有無と引数 | Task 1 のテスト |
| D4 request の検査 | 1 | `model_url` で CLI を呼ばない | Task 1 のテスト |
| D5 サムネイル | 2 | manifest と `source/` が不変、引数 | Task 2 のテスト |
| D6 kind・resource・ガード | 1 | attach の受け入れ・拒否、journal の書き込み | Task 1 のテスト（attach）、Task 4 の実 CLI の preload の実行 |
| D7 文書 | 3 | 手順の記述 | Task 4 で文書のコマンドを fixture で実行 |
| D10 実 GLB の convert | 4 | convert の成功と report | Task 4 |

共有する入力・状態: operation.json の形（`load_operation`）と CLI の引数の並び（`_cli` の先頭 7 個の後）を Task 1・2 が共有する。統合の確認は Task 4（全テストと fixture の実行）が持つ。

---

### Task 1: remesh の kind（plan・検査・送信前の確認・attach・ガード）

**Files:**
- Modify: `scripts/meshy_workflow.py`（`RESOURCES`、`load_operation`、`plan`、`_validate_request`、`submit`、`query` の `expected_type`）
- Modify: `scripts/meshy.py`（`plan` の引数）
- Modify: `scripts/meshy_cli_guard.mjs`（journal の `resource` に `remesh`）
- Test: `tests/scripts/test_meshy.py`

**テストの要否:** 要る（Issue の「テスト方針」の S: 送信前の確認、request の書き換えの拒否、元の記録の不変、attach の種別）。ガードの許可は L（足し忘れは送信の前に CLI が止まる）なのでテストしない。

**Interfaces:**
- Produces: `RESOURCES = ("text-to-3d", "image-to-3d", "remesh")`。kind `remesh` の operation（resource `remesh`）。エラーコード `successful_image_operation_required`（plan）、`successful_image_task_required`（submit）、`invalid_target_polycount`、`remesh_requires_source_operation`、`remesh_options_require_remesh_kind`
- Produces（テスト）: `SOURCE_TASK = "source-image-task"`、`succeeded_image(world, name="src")`（CLI を呼ばずに、成功済みの image operation を作る。plan の後に operation.json の task を `{"task_id": SOURCE_TASK, "status": "SUCCEEDED", "progress": 100}`、stage を `succeeded` に書き換える）

- [ ] **Step 1: 失敗するテストを書く**

`test_remesh_checks_source_task_and_never_changes_source_operation`（`anomaly` を `status`・`type`・`id` で parametrize）:
- `succeeded_image(world)` の後、`project_snapshot(src のディレクトリ)` を控え、`plan --operation asset --kind remesh --source-operation src`
- 異常な応答（status `FAILED` / type `text-to-3d-preview` / task_id `different-returned-task`）で `submit` が失敗し、stage が `planned`、どの呼び出しにも `create` が無い
- 正しい応答 `{"task_id": SOURCE_TASK, "status": "SUCCEEDED", "type": "image-to-3d", "resource": "image-to-3d"}` で `submit` が通り、最後の 2 回の呼び出しの `args[7:]` が `["image-to-3d", "get", SOURCE_TASK]` と `remesh create ...`。create に `--model-url` が無く、`--data` が `{"input_task_id": SOURCE_TASK, "target_polycount": 30000, "topology": "triangle", "target_formats": ["glb"]}`
- completed の manifest（key `model.glb`）で `download` が通り、呼び出しの `args[7:10]` が `["download", "--resource", "remesh"]`
- 最後に `project_snapshot(src のディレクトリ)` が控えと一致する

`test_edited_remesh_request_cannot_send_local_model`: remesh を plan した後、operation.json の payload に `model_url`（プロジェクトの `input.png` のパス）を足すと `submit` が失敗し、`world.calls() == []`。

`ATTACH_KINDS` に `("remesh", "remesh", "remesh")` を足し、`plan_attach` の remesh では `succeeded_image(world)` の後に remesh を plan する。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run --project . --locked pytest -q tests/scripts/test_meshy.py -k "remesh"`
Expected: FAIL（`--kind remesh` が argparse で拒否される）

- [ ] **Step 3: 実装する**

- `meshy.py` の plan: `--kind` に `remesh`、`--source-operation`、`--target-polycount`（`type=int`、既定 `None`）、`--topology`（choices `triangle`/`quad`、既定 `None`）。help に「remesh 専用」と「remesh では `--model`・`--pbr`・`--texture-resolution` を使わない」を書く
- `plan`: remesh 以外で remesh の引数があれば `remesh_options_require_remesh_kind`。remesh では `--prompt`・`--image`・`--preview-task-id`・`--texture` があれば `remesh_requires_source_operation`、`--source-operation` が無くても同じ。元を `load_operation` で読み、kind `image`・`_task_id` が有効・status `SUCCEEDED` でなければ `successful_image_operation_required`。polycount の範囲外は `invalid_target_polycount`
- kind から resource を決める処理（`image`→`image-to-3d`、`remesh`→`remesh`、ほか `text-to-3d`）を 1 か所にまとめ、`plan` と `_validate_request` で使う
- `_validate_request`: remesh は Spec の D4 の条件で検査する（ほかの kind の分岐の前に処理する）
- `submit`: refine の preview の確認と remesh の確認を、`(resource, task_id, task_type, error_code)` を受け取る 1 つの関数にまとめる。remesh は `("image-to-3d", input_task_id, "image-to-3d", "successful_image_task_required")`。create は `--data` だけで、追加のフラグを付けない
- `query` の `expected_type` に `"remesh": "remesh"`、`load_operation` の kind に `remesh`
- `meshy_cli_guard.mjs`: journal の `resource` の許可に `remesh`

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run --project . --locked pytest -q tests/scripts/test_meshy.py`
Expected: すべて PASS（既存 138 件と新しい組み合わせ）

- [ ] **Step 5: commit**

```bash
git add scripts/meshy.py scripts/meshy_workflow.py scripts/meshy_cli_guard.mjs tests/scripts/test_meshy.py
git commit -m "feat: add the Meshy remesh kind to the wrapper"
```

### Task 2: サムネイルだけを取得する `thumbnail`

**Files:**
- Modify: `scripts/meshy_workflow.py`（`thumbnail` を追加、`execute` から呼ぶ）
- Modify: `scripts/meshy.py`（`thumbnail` のサブコマンド、`--operation`・`--timeout`）
- Test: `tests/scripts/test_meshy.py`

**テストの要否:** 要る（Issue の「テスト方針」の S: 完了した download の記録を消さない）。

**Interfaces:**
- Consumes: `_download_files`、`_safe_tree`、`_mkdir`、`_call`（既存）
- Produces: `thumbnail(project, name, operation, env, timeout=None) -> {"thumbnail": {"path", "bytes", "sha256"}}`。エラーコード `thumbnail_download_failed`

- [ ] **Step 1: 失敗するテストを書く**

`test_thumbnail_keeps_completed_download_and_fetches_only_thumbnail`: text の operation を submit・status（SUCCEEDED）・download（completed、key `model.glb`）まで進めた後、operation.json の byte 列と `project_snapshot(source/)` を控える。`FAKE_DOWNLOAD_FILES` を `{"thumbnail.png": "png-fixture"}`、応答を key `thumbnail.primary`・パス `<operation>/thumbnail/thumbnail.png` の completed の manifest にして `thumbnail --operation asset` を実行し、次を確かめる:
- 出力の `thumbnail.path` が `<operation>/thumbnail/thumbnail.png`
- operation.json の byte 列と `source/` の snapshot が控えと一致する
- 最後の呼び出しの `args[7:]` の先頭が `["download", "--resource", "text-to-3d", "--task-id", TASK]`、`--asset` の値が `thumbnail.primary`、`--all` が無く、`--output-dir` が `<operation>/thumbnail`

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run --project . --locked pytest -q tests/scripts/test_meshy.py -k thumbnail`
Expected: FAIL（`thumbnail` が argparse で拒否される）

- [ ] **Step 3: 実装する**

Spec の D5 のとおり。task ID と status `SUCCEEDED` が無ければ `successful_existing_task_required`。`download --resource <resource> --task-id <id> --asset thumbnail.primary --overwrite --output-dir <operation>/thumbnail` を呼び、manifest が `completed`・ファイル 1 件・key `thumbnail.primary`・status `written` / `skipped`・`_download_files` で不正なし、でなければ `thumbnail_download_failed`。operation.json は書かない。`execute` は他の operation のコマンドと同じロックの中で呼ぶ

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run --project . --locked pytest -q tests/scripts/test_meshy.py`
Expected: すべて PASS

- [ ] **Step 5: commit**

```bash
git add scripts/meshy.py scripts/meshy_workflow.py tests/scripts/test_meshy.py
git commit -m "feat: download only the Meshy thumbnail of a succeeded task"
```

### Task 3: 文書

**Files:**
- Modify: `docs/meshy-resoloop.md`
- Modify: `.agents/skills/meshy-resoloop/SKILL.md`

**テストの要否:** 要らない（文書の文言は F）。代わりに Task 4 で、文書に書いたコマンドを fixture のプロジェクトで実行する。

- [ ] **Step 1: `docs/meshy-resoloop.md` に「Remesh: 三角形数を減らす」の節を「状態・journal と再開」の前に足す**

内容: 対象（成功済みの image operation だけ、別 operation・別の課金 1 件。公表値は 1 件 5 credits で、送信前に公式料金を確かめる）、手順（`thumbnail` → `thumbnail/thumbnail.png` の確認 → `plan --kind remesh` → request の確認と承認 → `submit --confirm-paid` → `wait` → `download` → `convert`）、元の operation を変えず元の GLB を取得しないこと、送信の前に元の task を確かめること、保持期間（Enterprise 以外は API の生成物が最大 3 日で削除される。生成から 3 日以内にサムネイルの確認・remesh・ダウンロードを終え、期限切れなら生成し直す。期限切れの応答は未確認）、三角形数の目安（複数体を並べ後で部品に分ける人型は 1 体 20,000〜40,000、既定 30,000。`target_polycount` は面の数で形によってずれるので convert の report の `triangles` で確かめる）、`topology`（`triangle` が既定、`quad` はリグ・細分化向け）、`decimation_mode`・`model_url` は使えないこと

- [ ] **Step 2: 同じ文書の既存の記述を更新する**

「課金の承認」に remesh が別の課金操作であること、「状態・journal と再開」の list の例に `--resource remesh`、attach の type の一覧に「remesh は `remesh`」、保存先の表に `thumbnail/`、「検証済み範囲と未検証」の NOT verified に「課金を伴う remesh、remesh 後のテクスチャの保持・三角形数、期限切れの元の task の応答」

- [ ] **Step 3: SKILL.md の手順 5 の後に 1 行足す**

「三角形数を減らすときは、成功した image operation のサムネイルを `thumbnail` で確かめてから `--kind remesh`（別の課金 1 件、生成から 3 日以内）。手順の Remesh の節に従う」

- [ ] **Step 4: commit**

```bash
git add docs/meshy-resoloop.md .agents/skills/meshy-resoloop/SKILL.md
git commit -m "docs: describe the Meshy remesh and thumbnail steps"
```

### Task 4: 統合の確認（fixture の実行・実 CLI の preload・実 GLB の convert・全テスト）

**Files:** なし（確認だけ。ログはセッションディレクトリ `tmp/agents/issue-315.cciobdzw/` に置く）

**テストの要否:** 要らない（L の項目の確認と、実ファイルでの確認）。

- [ ] **Step 1: help と fixture の実行**

`uv run --no-project scripts/meshy.py --project <一時プロジェクト> plan --help` と `thumbnail --help`。一時プロジェクト（`.resoloop.json` だけ）で、remesh 以外の kind への `--target-polycount`、image でない元・成功していない元・範囲外の polycount（`99`・`300001`）・整数でない polycount の plan が終了コード 1 で止まり、operation.json を作らないこと。成功済みの image の元から `--target-polycount 30000 --topology triangle` の plan が通り、request が受け入れ基準の形であること

- [ ] **Step 2: 実 CLI の preload で remesh の journal を書けること**

既存の `test_real_node_cli_preload_keeps_accepted_id_without_persisting_key` と同じ形の一時的なスクリプト（コミットしない。セッションディレクトリに置く）で、journal の `resource: "remesh"` の書き込みがガードを通り、`resource: "convert"` は拒否されることを確かめる

- [ ] **Step 3: 実 GLB の convert（Spec の D10）**

セッションディレクトリに一時プロジェクトを作り、kind `remesh`・resource `remesh`・`downloads` が completed（key `model.glb`）の operation の `source/` に `tmp/Meshy_Ornate_Silver_Monocle.glb` を写して `convert --operation <name> --height 0.05 --parent <任意の selector> --allow-culling-change` を実行する。終了コード 0 と report の `triangles` を記録する。期限 30 分

- [ ] **Step 4: 全テストと静的な確認**

Run（worktree のルート）:
- `bash .devcontainer/run-tests.bash`
- `bash scripts/check-layout.sh`
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`
- `node --check scripts/meshy_cli_guard.mjs`、`uv run --no-project python -m py_compile scripts/meshy.py scripts/meshy_workflow.py`

Expected: すべて終了コード 0

## 実行予算

- Issue 全体の能動時間: 330 分（実装 90 分・確認 45 分・PR 15 分・ループ最大 3 サイクル × 60 分。似た規模の #313 の実績から）
- phase の目安: Task 1 50 分、Task 2 25 分、Task 3 20 分、Task 4 45 分、PR 15 分、ループ 180 分
- worker: 実装は inline（このセッション）で worker なし。Task 4 の convert は期限 30 分・無進捗 10 分で打ち切る。ループのレビュアーは pr-review-fix-loop の期限（45 分）
- 再試行の上限: 同じ失敗の再試行は 1 回まで
- checkpoint: Task の境界、PR の作成後、予算の 50%・100%、convert の失敗の直後
- 縮小・切り出し・方法変更の候補: 実 GLB の convert が Blender・ResoLoop の環境で動かなければ、fixture の GLB で `load_operation` の受け入れだけを確かめ、実 GLB の確認をマージの後の残りに回す。サムネイルの実装が CLI の manifest の形で通らなければ、Spec の D5 の範囲で manifest の検査を緩めず、停止して報告する

## contingency（代替策）

- 最初の RED で、偽の CLI の応答の形と CLI 0.4.0 の実装の前提が違うと分かった場合（例: task view の `resource` が `remesh` でない）は、CLI の実装（`dist/`）を読み直し、意味を保つ最小の修正を ledger に記録して続ける。守りを弱める変更になるなら止まる
- 実 GLB の convert が、remesh と無関係な既存の拒否（culling・法線マップなど）で止まるときは、拒否の理由を記録し、remesh の operation が `load_operation` を通ったこと（拒否が Blender の段階で出たこと）を確認できれば、それを結果として報告する
- 既存のテストが壊れたら systematic-debugging で調べ、既存の挙動を変えない形に直す。直せなければ止まる
