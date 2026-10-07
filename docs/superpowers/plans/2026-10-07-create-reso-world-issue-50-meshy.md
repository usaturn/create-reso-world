# Meshy CLI / ResoLoop 連携 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** API キーを永続化せず、安全に Meshy の生成・再開・保存・Blender 変換を行える共通経路を追加する。

**Architecture:** 公式 CLI の通信・journal・download を薄い Python ラッパーから使う。Blender 内の素材変換を独立スクリプトに分け、Resonite への反映は手動の確認ゲートを残す。

**Tech Stack:** Node.js、`meshy-cli@0.4.0`、uv / Python 標準ライブラリ、Blender bpy、ResoLoop。

**Spec:** `docs/superpowers/specs/2026-10-07-create-reso-world-issue-50-meshy-design.md`

- 文書管理・対象: `usaturn/create-reso-world` Issue #50
- 基準 HEAD: `b1b0614`
- 状態: completed
- 完了範囲: 実装・ローカル検証・PR 作成。実機受入は未確認。
- PR: https://github.com/usaturn/create-reso-world/pull/54
- 作業ルート: `/workspaces/reso-world/.worktrees/issue-50-meshy`
- 実行方法: 推奨の subagent-driven-development。ユーザーは推奨案で Spec / Plan から PR まで進め、確認待ちを省略するよう指示した。内容の事前承認とは区別する。

## Global Constraints

- API 処理は実行環境の `MESHY_API_KEY` だけを使う。
- `.env`、rc、mount、containerEnv / remoteEnv、OAuth、キー引数・キーを含むプロンプトを追加しない。
- create は `--async --operation-id ID` を使う。
- 操作 ID はローカル記録であり、サーバー側の重複実行防止ではない。
- CLI の生出力や Authorization を保存しない。
- CLI timeout、異常終了、不正 JSON、シグナル中断、結果不明は `unknown` にし、同じ operation の submit は禁止する。
- wait の timeout / interruption、download の失敗では ID と段階を保持し、そのコマンドだけ再開する。
- 独立した物体を無条件に join しない。
- apply は自動実行しない。
- 課金 API、Windows の操作、Resonite の変更、マージはこの許可に含めない。
- 文書やモデル名の固定値テストは作らない。

## Review Focus

1. CLI がキーを stdout / stderr / error に混ぜた場合も漏らさない（Task 1 の sentinel テスト）。
2. accepted ID を持つ error と不正 JSON / interruption でも再送しない（Task 1）。
3. NAME、画像、manifest、journal / download が symlink や project 外を指す場合は操作しない（Task 1 / 2）。
4. packed MR と複数オブジェクトの GLB を実際に変換し、画像・寸法・個体を保つ（Task 2）。
5. export 失敗時は途中 bundle を公開しない。Windows の未確認を成功扱いしない（Task 2 / 3）。

## ファイル構成

- `.devcontainer/install_meshy.bash`: 公式 CLI の導入・認証なし確認。
- `scripts/meshy.py`: argparse、plan / API / convert コマンドの窓口。
- `scripts/meshy_workflow.py`: path・manifest・lock・状態遷移・CLI subprocess の標準ライブラリ実装。
- `scripts/meshy_cli_guard.mjs`: 検証済み CLI の journal 書込み前に API エラー本文・認証情報を除去する Node preload。
- `scripts/meshy_blender.py`: bpy による GLB、変換、統計、.blend 保存。
- `scripts/meshy_conversion.py`: manifest の download から GLB を選び、ResoLoop の run / export を順に実行。
- `tests/scripts/test_meshy.py`, `tests/scripts/test_meshy_conversion.py`: 実行挙動の回帰。
- `tests/fixtures/meshy/`: Blender fixture 生成スクリプトと必要な試験用コード。生成バイナリは tmp に作る。
- `.agents/skills/meshy-resoloop/SKILL.md`, `.claude/skills/meshy-resoloop`: 共通スキルと参照。
- `docs/meshy-resoloop.md`, README 2 ファイル: 運用手順。

---

### Task 1: CLI 導入と、再送しない Meshy 操作

**Files:**
- Create: `.devcontainer/install_meshy.bash`, `.devcontainer/test-install-meshy.bash`
- Modify: `.devcontainer/install_beforehand.bash`
- Create: `scripts/meshy.py`, `scripts/meshy_workflow.py`, `scripts/meshy_cli_guard.mjs`, `tests/scripts/test_meshy.py`

**Interfaces:**
- Produces: `meshy.py --project PATH plan|submit|status|wait|download|list|attach|balance`。
- `plan --operation NAME --kind text|image|refine [--prompt TEXT] [--image PATH] [--preview-task-id ID] [--model latest] [--texture true|false] [--pbr true|false] [--texture-resolution 2k|4k|8k]`。
- 他の操作は `--operation NAME`、submit は `--confirm-paid`、wait は `--timeout SECONDS`、list は `--resource text-to-3d|image-to-3d`、attach は `--task-id ID`。
- Produces: `operation.json` の `schema_version`, `operation_id`, `kind`, `resource`, `request`, `stage`, `task`（`task_id`, `status`, `progress`）, `downloads`（`state`, `files`）を Task 2 / 3 が使う。
- Produces: `load_operation(project: Path, name: str) -> dict`, `save_operation(project: Path, name: str, operation: dict) -> None`, `operation_dir(project: Path, name: str) -> Path`, `operation_lock(project: Path, name: str)` context manager、`safe_path(project: Path, path: Path) -> Path`。追加の内部 helper は必要に応じて選べる。

**テスト:** 必要。認証経路、送信前後の状態、安全条件を実行で確かめる。

- [x] **Step 1: fake npm / meshy を使う failing installer test を追加する。** キーなしの成功、npm 失敗、実行ファイルなし、version / help 失敗を試す。キー値を CLI に渡さない。バージョン文字列の一致だけのテストは作らない。
- [x] **Step 2: `bash .devcontainer/test-install-meshy.bash` が未実装により失敗することを確認する。**
- [x] **Step 3: installer を実装する。** `npm install -g meshy-cli@0.4.0` を使い、`env -u MESHY_API_KEY meshy --no-update-check --version` / `--help` でローカル確認する。postCreate の専用 step を追加し STEP_TOTAL を実際の step 数に合わせる。他サービスの設定を変更しない。
- [x] **Step 4: fake CLI を subprocess として起動する workflow tests を追加し RED を確認する。**
  - 未設定 / 空 / 空白 / placeholder のキーは、保存済み credentials がある想定でも fake CLI 呼出しゼロ。
  - plan / help はキーなし・CLI なしで成功。
  - sentinel キーを fake CLI が stdout / stderr / nested error に出しても、表示・manifest に sentinel はない。argv にキーを含まない。
  - create の envelope `result.task.task_id`、`result.task_id`、`result.submission.task_id` を保存し、accepted error でも二度目の create をしない。
  - unknown / malformed JSON / subprocess timeout / interruption で task を再生成しない。
  - wait timeout / FAILED と partial download を成功扱いせず、次回は既存 ID のみ使用。
  - image の内容変化、NAME の traversal、symlink の出力・journal、同一操作の同時 submit を拒否。
  - list / attach / balance は生成せず、条件外の URL / credentials / debug env を引き継がない。
- [x] **Step 5: `scripts/meshy_workflow.py` と CLI を実装する。** project の `.resoloop.json`、単一 NAME、すべての保存 path を確認する。plan は独占作成し既存 plan を上書きしない。manifest は os.replace、lock は flock LOCK_NB。
  - 保存先は `content/generated/meshy/NAME/operation.json`、source は `source/`、CLI config は `.resoloop/meshy-cli/`。入力画像の SHA-256 を検査。
  - `--output-schema v1 --format json --no-update-check --workspace PROJECT` を必ず渡す。create は `--async --operation-id UUID`。`--data` はラッパーが作った ai_model 等の JSON のみで、任意 passthrough は設けない。
  - text preview / refine と image の費用設定は Spec §3 に従い明示。image はローカル path を CLI に渡す。
  - API child env の MESHY_* は allowlist で構築。MESHY_API_KEY は env のみ、公式 base URL、silent、隔離 credentials path、更新通知無効。
  - POST 前に `submitting` を保存し、起動・出力処理失敗は `unknown` に保存。既存 ID ありは新規送信しない。unknown は list / attach だけで復旧。
  - 生 envelope / stderr は保存せず、許可した task / downloads / error.code と数値 balance のみ公開。キー混入値は伏せる。公式 CLI が journal にエラー本文を書かないよう Node preload guard を指定し、0.4.0 の `writeJsonFile` → `fs.writeFileSync` 経路を保存前に sanitise する。`NODE_DEBUG` / `NODE_DEBUG_NATIVE` も除外する。guard の実 Node 書込みテストで漏えいを検査する。
  - download は `--all --overwrite --output-dir SOURCE`、返却 paths の安全と実在を検査し、不完了では convert に進ませない。
- [x] **Step 6: `uv run --no-project --with pytest pytest tests/scripts/test_meshy.py -q` と installer tests、既存 installer test を同期実行し GREEN を確認する。**
- [x] **Step 7: 差分を自己確認しコミットする。** `feat: add env-only Meshy CLI workflow`。レポートに RED / GREEN、所要時間、未確認事項を記録する。

### Task 2: ローカル GLB の Blender 変換と bundle 公開

**Files:**
- Create: `scripts/meshy_blender.py`, `scripts/meshy_conversion.py`, `tests/scripts/test_meshy_conversion.py`, `tests/fixtures/meshy/create_fixture.py`
- Modify: `scripts/meshy.py`（convert を追加）, `.devcontainer/install_beforehand.bash`（base apt の NumPy）, `.devcontainer/verify-resonite-tooling.bash`（headless NumPy probe）

**Interfaces:**
- Consumes: Task 1 の load / save / lock / operation_dir / safe_path と manifest `downloads.files`（`key`, `path`, `status`, `sha256`, `bytes`）。
- Produces: `convert --operation NAME --height METERS [--yaw DEGREES] [--origin ground|center] --parent VERIFIED_SELECTOR [--name NAME] [--allow-culling-change]`。
- Produces: `convert_operation(project: Path, name: str, *, height: float, yaw: float, origin: str, parent: str, model_name: str, allow_culling_change: bool = False) -> dict`。converted の .blend、変換 report、bundle、operation の `conversion` を返す。
- Blender script argv: `--input GLB --output BLEND --report REPORT --height METERS --yaw DEGREES --origin ground|center --name NAME [--allow-culling-change]`（resoloop の `--arg=VALUE` 経路）。

**テスト:** 必要。小さいテクスチャ付きモデルを実際に Blender と exporter で処理する。API や Resonite には接続しない。

- [x] **Step 1: fixture generator を追加する。** Blender で opaque Principled の複数 mesh、sRGB albedo、packed MR を作って GLB を tmp に export する。別ケースでは非対応 transparency / transmission を持つ GLB を作る。
- [x] **Step 2: subprocess tests を追加し RED を確認する。** 実 GLB→blend→bundle の texture asset 実在、物体分離、指定 height・ground origin、MR 分離 Non-Color、統計値を検査。export に失敗する fake ResoLoop のケースでは正式 bundle と successful conversion がないことを検査する。manifest の GLB 名は固定せず download files から選ぶ。CLI / bpy がない環境だけ理由付き skip 可。
- [x] **Step 3: bpy 変換を実装する。** factory settings から glTF import。mesh と hierarchy を保持し、world 変換した実頂点の bounds で height / yaw / ground-center 調整を行う。rotated 非直方体の fixture を追加し、probe も実頂点で測る。GLB culling は既定で素材名付き拒否、`--allow-culling-change` がある場合だけ明示警告を report に残して続行。片面・両面の fixture と opt-in の検査を追加する。glTF importer の Separate Color / Separate RGB による B metallic / G roughness を単一 channel grayscale image へ分け、直接 image links へ直す。active UV、Flat / Repeat / Linear、sRGB / Non-Color を確認する。対応しない link / non-opaque / rig / animation は名前付きで停止。元 GLB は不変。画像を pack し編集可能な blend と三角形・素材・画像寸法 report を保存。
- [x] **Step 4: `convert_operation` を実装する。** completed downloads の実在 GLB を一意に選択する。hash / path・出力先を検査し lock を保持する。新しい temporary output で run と export を実行し、`.blend`・report・`model.apply.json` が揃って成功したときだけ converted を公開する。resoloop export は `--preserve-hierarchy --pack-pbr --parent SELECTOR`。失敗先を正式 manifest に成功として記録しない。既存変換の上書きは拒否する。apply はしない。
- [x] **Step 5: glTF に必要な `python3-numpy` を base apt list に追加し、既存 headless probe を `import bpy, numpy` へ拡張する。** `uv run --no-project --with pytest pytest tests/scripts/test_meshy.py tests/scripts/test_meshy_conversion.py -q` を同期実行して GREEN を確認する。現環境の sudo は no-new-privileges で拒否されているため、必要なら一時 uv NumPy wrapper の検証と標準 rebuild 未確認を区別する。既存 toolchain probe の挙動テストも実行する。
- [x] **Step 6: 自己確認して `feat: convert Meshy GLB assets for ResoLoop export` をコミットする。** Blender / ResoLoop の実測 version、fixture の結果、所要時間をレポートに記録する。

### Task 3: 共有スキル・手順と統合検証

**Files:**
- Create: `.agents/skills/meshy-resoloop/SKILL.md`, `.claude/skills/meshy-resoloop` symlink、`docs/meshy-resoloop.md`
- Modify: `README.md`, `.devcontainer/README.md`

**Interfaces:**
- Consumes: Task 1 / 2 の CLI と operation manifest。
- Produces: 全エージェント用の共通手順、Windows bundle handoff と実機受入 checklist。

**テスト:** 文書・SKILL の文言テストは不要。構造、参照、help 実行、既存 suite と layout で確認する。

- [x] **Step 1: `skill-creator` / `writing-skills` を読み、短い operational skill を追加する。** Meshy を使う場面（曖昧な有機形状・画像参考）と Blender の方がよい場面（寸法・機械構造・低ポリ再現）、キーの有無、対象・件数・予算・条件の明示許可、local fixture での事前確認、plan→submit→wait→download→convert→diff→apply のゲート、復旧をまとめる。ユーザーへキー値を要求しない。参照先は相対 path を skill directory 基準で解決する。
- [x] **Step 2: root の既存方式で `.claude/skills/meshy-resoloop -> ../../.agents/skills/meshy-resoloop` を作る。** プロジェクト祖先の共有スキルと明示的な repository-relative パスを案内し、同じ内容をコピーしたりエージェント設定を変えたりしない。
- [x] **Step 3: README 2 ファイルと `docs/meshy-resoloop.md` を更新する。** 公式版・更新、認証なし rebuild、zsh の非表示入力と継承制限、すべての CLI 例、text preview→refine、image、状態の保存先・rebuild 再開、ファイル manifest・素材制限を説明。
  - Windows の最新公開 ResoLoop の導入と実測 version 記録、bundle 一式受け渡し、PowerShell で URL / parent / state を明示した diff→apply→再apply / test を示す。共有 state は一つだけ、既存所有外に触らない。
  - 未実施: コンテナ rebuild、実 API 認証・残高・text/image generation、Windows の texture 付き表示・無変更再適用。これを明記し、PR は Refs #50（自動 close なし）。
- [x] **Step 4: `meshy.py --help` / 各 command help、skill efficiency checker を uv で実行する。** trigger の例「Meshy で小物を生成」「Meshy タスクを再開」、non-trigger「普通の Blender モデリング」を読解レビューする。文言を固定したテストは追加しない。
- [x] **Step 5: 全追加 tests、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills -q`、`git diff --check` を実行する。** git add 後 `bash scripts/check-layout.sh` も実行。既存の bundle skills 更新警告は原因を区別して記録する。
- [x] **Step 6: 自己確認して `docs: document Meshy to Resonite workflow` をコミットする。** 全体レビューの結果を経て coordinator が文書にコミット SHA・検証・所要時間を追記し、確認用コピーを保存、push、PR を作る。公開前の無課金 smoke は coordinator が isolated npm prefix で実施する。

## 実施結果（2026-10-07）

- 実装・ローカル検証・PR 作成は完了。Issue の実 API / Windows / Resonite 受入は未確認であり、この completed は実機連携完了を意味しない。
- PR: https://github.com/usaturn/create-reso-world/pull/54 （OPEN、main 向け、マージ未実施）。
- 検証した実装 HEAD: `38db299eee65ab078f30d88354786299d69b77df`。初回 Spec / Plan: `4f8a362f37cdd007476a46333f4a64f413b78805`。設計補強: `3ada154`（journal 保護）、`93e3702`（NumPy / culling / bounds）。
- 特定内容版のユーザー承認 SHA は記録していない。推奨案で確認待ちなく PR まで進める明示指示に基づき実行した。レビューに基づく journal 保護・NumPy 依存・culling の限定承認ゲート・実頂点の寸法・暗黙 glTF 素材の保持を推奨案として採用した。
- 各 Task の独立レビューと全体レビューを実施。最終修正 `38db299` の scoped 再レビューは全指摘解消、新規指摘なし。

### 検証の根拠

| 検証 | 結果 |
| --- | --- |
| `bash .devcontainer/run-tests.bash` | 28 scripts PASS |
| `RESOLOOP_BLENDER_EXECUTABLE=/tmp/meshy-blender-task2 uv run pytest tests/scripts tests/skills .agents/skills -q` | 687 passed / 144 subtests passed、exit 0 |
| Ruff check / format（Python 7 ファイル）、Node / bash 構文、diff | PASS |
| `bash scripts/check-layout.sh` | PASS、既存 4 project の SKILL_SYNC_REQUIRED 警告 |
| 一時 npm prefix の公式 CLI 0.4.0、キーなし version / help | 成功。キーなし wrapper balance は env_key_required / exit 1、通信なし |
| 実 Blender 5.0.1 / ResoLoop 0.1.0-preview.17 | 複数物体、MR pixel、実頂点の寸法、暗黙・混在素材、bundle の offline validate を確認 |
| active LSP | Blender 専用 bpy / mathutils は外側 interpreter で未解決。実 Blender 試験で実行確認。補助の bool identity / helper exception 指摘は実際の厳密型検査・外側例外境界からレビュー済み |

現環境は OS NumPy がなく sudo が no-new-privileges により拒否された。実 GLB 試験は uv の NumPy を一時 wrapper で読み込んだ。標準 rebuild、実認証・残高・有料 text/image 生成、Windows の texture 表示・無変更再適用・保存再起動後の保持は未確認。`docs/meshy-resoloop.md` の受入 checklist を実施するまで Issue を close しない。

### 所要時間

最初の記録は 16:49 UTC、PR 作成・結果整理まで約 3 時間 34 分。子担当の着手から成果提出まで（レビュー・controller の統合時間は含めない）:

| 担当 | 初回 | レビュー修正 |
| --- | --- | --- |
| Task 1: CLI / API workflow | 31分33秒 | 21分00秒 |
| Task 2: Blender / bundle | 31分47秒 | 15分06秒 |
| Task 3: skill / docs | 9分57秒 | 5分29秒 |
| 最終修正: 暗黙素材・テスト・受入 checklist | 12分03秒 | — |

controller は調査・Spec / Plan（約14分）、各レビュー・裁定・統合、公式 CLI smoke、全体同期回帰2回（各約5分）、公開を担当した。並行した検証とレビューの時間は二重加算していない。
