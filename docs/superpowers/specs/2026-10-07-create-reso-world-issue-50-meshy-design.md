# Issue #50: Meshy CLI と Blender / ResoLoop 連携

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/50
- 基準 HEAD: `b1b0614`（origin/main）
- 状態: completed
- 完了範囲: 実装・ローカル検証・PR 作成。実機受入は未確認。
- PR: https://github.com/usaturn/create-reso-world/pull/54
- Plan: `docs/superpowers/plans/2026-10-07-create-reso-world-issue-50-meshy.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-50-meshy`

## 実行許可と目的

ユーザーの指示は「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」。推奨する設計・計画の選択と確認待ちの省略、実装・ローカルコミット・作業ブランチの push・PR 作成を許可されたものとして記録する。作成前の内容を承認済みとは扱わない。Spec / Plan のコミット SHA と実行結果を後から記録する。課金 API、Windows の操作、Resonite の変更、マージはこの許可に含めない。

目的は、共通の CLI・手順を全エージェントから利用し、静的な生成物をローカルで再利用できるようにすること。秘密情報の保存を追加せず、待機失敗を重複課金へ結び付けない。実機確認できない受入項目は未確認として残す。

## 比較と採用案

1. **公式 CLI + 薄い Python ラッパー（採用）**: CLI の構造化出力・操作履歴・ダウンロードを使い、環境変数限定の認証、課金前確認、再送禁止、保存先をリポジトリ側で保証する。標準ライブラリだけで実装する。
2. CLI の直接操作だけを文書化: 実装量は少ないが、空キーから保存済み認証へのフォールバックや、再実行時の誤生成を防げない。
3. REST API を独自実装: 通信・画像入力・ダウンロードを重複実装することになり、Issue の公式 CLI 採用方針にも合わない。

## 確認済みの外部仕様

2026-10-07 に npm の `meshy-cli@0.4.0` の repository URL が `meshy-dev/meshy-cli`、実行名が `meshy` / `meshy-cli`、Node 要件が `>=22.12.0` であることを確認した。公開 tarball の `dist/` を照合した。

- https://github.com/meshy-dev/meshy-cli/blob/main/docs/scripting.md
- https://github.com/meshy-dev/meshy-cli/blob/main/docs/usage.md
- https://docs.meshy.ai/en/api/text-to-3d
- https://docs.meshy.ai/en/api/image-to-3d
- https://github.com/orange3134/resoloop/blob/main/docs/BLENDER.md

Context7 では `/websites/meshy_ai_en` を照会した。CLI と API 文書にはモデル世代・既定値の違いがあるため、CLI の prose を解析したり、`latest` の実体を固定世代として説明したりしない。

- `--output-schema v1 --format json` の `schema_version` は `meshy.cli/v1`。`ok` は CLI 操作の成否、`result.task.status` はサーバータスクの成否。
- create は `--async --operation-id ID` を使う。操作履歴は `MESHY_CONFIG_DIR/operations/`。操作 ID はローカル記録であり、サーバー側の重複実行防止ではない。
- `get` / `wait` の ID は `result.task.task_id`。送信後の失敗には `result.task_id` / `result.submission.task_id` が入る場合もある。
- `MESHY_API_KEY` が空・placeholder の場合は資格情報ファイルへフォールバックする。ラッパーは CLI 起動前に停止させる。
- `download --resource RESOURCE --task-id ID --all --output-dir DIR` は `result.downloads.files` にファイル情報を返す。固定ファイル名では選択しない。

## 1. インストールと認証

Blender の glTF import / export は OS の NumPy を必要とするため、base apt packages に `python3-numpy` を追加し、既存の headless probe でも import を確認する。現セッションでは sudo がコンテナの no-new-privileges 制限で拒否されたため、rebuild 後の標準環境の確認は未実施として残す。

`.devcontainer/install_meshy.bash` が公式 npm パッケージの検証済み版 `0.4.0` を導入する。`install_beforehand.bash` から必須ステップとして呼び、ステップ数を更新する。認証なしの `--version` / `--help` だけで確認し、キーを渡さない。導入失敗は postCreate の既存 fail 処理へ伝える。更新は版変更、公式仕様の照合、モック回帰、認証不要の CLI smoke の順で行う。既存 zsh の update() や他サービスの秘密情報 mount は変更しない。

API 処理は実行環境の `MESHY_API_KEY` だけを使う。空白・空・placeholder をキーなしとして拒否する。`.env`、rc、mount、containerEnv / remoteEnv、OAuth、キー引数・キーを含むプロンプトを追加しない。CLI 子プロセスでは継承された `MESHY_*` の認証・URL・ログ設定を取り除き、キー、公式 API URL、silent ログ、プロジェクト内の状態ディレクトリ、資格情報の代替利用を避ける隔離パスを設定する。更新通知は無効化する。

README の手動入力例は zsh の `unset` → `read -rs` → `export` とする。継承範囲はそのシェルと新しい子プロセスであり、起動済みエージェント、別ターミナル、Herdr サーバーや VS Code 拡張に届くと仮定しない。値や env 全体を表示せず、設定有無だけ確認する。

## 2. ラッパーと保存形式

エントリポイントは `uv run --no-project <repo>/scripts/meshy.py --project <world> COMMAND`。project は既存の ResoLoop プロジェクトとし、`.resoloop.json` を確認する。標準ライブラリで実装し、外部サービスなしでテストできる。

- `plan --operation NAME --kind text|image|refine`: 認証・通信不要。text は preview、refine は既知の成功済み preview のテクスチャ段階、image はローカル画像から生成。prompt / image / preview-task-id とモデル・テクスチャ条件を記録する。
- `submit --operation NAME --confirm-paid`: この明示オプションは対象・件数・予算に関するユーザー許可の代替ではない。ひとつの plan につき最大ひとつの create を送信する。
- `status` / `wait --timeout N` / `download`: 既存 ID だけで再開する。FAILED / CANCELED は成功にしない。download は GLB とテクスチャを含む生成物を保存する。
- `list --resource text-to-3d|image-to-3d`: 送信結果不明時の照合用。生成しない。
- `attach --operation NAME --task-id ID`: 人間が照合した既存 ID を GET で確認して紐付ける。POST しない。
- `balance`: キー設定後に明示的な認証・残高確認を行う。`auth status` の masked credential は出力しない。
- `convert`: 後述の Blender 変換・export。API キー不要で、Meshy に通信しない。

保存先は `<world>/content/generated/meshy/<NAME>/operation.json`、元ファイルはその下の `source/`、変換結果は `converted/`。CLI journal は `<world>/.resoloop/meshy-cli/operations/`。ワークスペースの bind mount 内なので rebuild 後にも残る。生成済みモデルは採用時にプロジェクトの既存方針に従って保持する。API の一時 URL だけに依存しない。

operation.json は schema、操作 UUID、kind / resource、要求条件、入力画像のパスと SHA-256、処理段階、task_id / status / progress、download manifest、変換結果を持つ。CLI の生出力や Authorization を保存しない。許可した項目だけ抽出し、キー文字列が混入した値は出力・保存前に伏せる。CLI の stderr / traceback をそのまま返さない。

入力・出力・journal の symlink と project 外への逸脱を拒否する。NAME は単一の安全な path segment。manifest は一括置換し、操作ごとの非ブロッキング lock を持つ。API 実行中は lock を保持する。ローカル画像の内容が plan 時から変化したら submit を拒否する。

Task 1 レビューで、公式 CLI が API エラー本文を journal の `error` に書く経路を確認した。ラッパー出力の除去だけでは不十分なため、`scripts/meshy_cli_guard.mjs` を Node の preload として起動し、検証済み 0.4.0 の journal JSON 書込み経路で error 本文を保存前に除去し、キー文字列・認証 field を書かせない。継承された Node debug / preload は破棄し、ラッパー自身が指定する guard のみを有効化する。これはユーザーが委任した推奨案の範囲で、秘密情報非保存の要件を満たすための補強である。CLI 更新時は実際の書込み経路を再確認する。

## 3. 生成条件と再送禁止

`ai_model` は明示値（既定は `latest`）として記録する。text preview は形状だけ、refine はテクスチャ生成として別の有料操作にする。image は `should_texture` を明示し、テクスチャありの場合は `enable_pbr`、`texture_resolution`（推奨 `2k`）、`remove_lighting`、`image_enhancement`、`target_formats=[glb]` を明示する。ultra を自動有効化しない。任意 JSON passthrough、rig、animation、複数件生成は追加しない。

POST 前に stage を `submitting` に保存する。受け付けた ID が見つかれば、それがエラー応答に含まれていても失わず保存する。CLI timeout、異常終了、不正 JSON、シグナル中断、結果不明は `unknown` にし、同じ operation の submit は禁止する。CLI journal と list で照合して attach する。既知 ID がある submit は生成を再送しない。新しく生成し直す場合は新しい NAME と課金の明示許可が必要。

wait の timeout / interruption、download の失敗では ID と段階を保持し、そのコマンドだけ再開する。download は成功ファイルを保持し、CLI の `--overwrite` を使った既存タスクの再ダウンロードを許容するが、ローカル path の検証を省略しない。download 全体が完了し、manifest の GLB が実在するまで変換可能にしない。

## 4. Blender 変換・export

`scripts/meshy_blender.py` は `resoloop blender run` 内だけで bpy を使い、manifest から選んだ GLB を読み込む。実寸 height、yaw、origin（ground / center）、名前を指定できる。独立した物体を無条件に join しない。静的 mesh の物体単位とマテリアルを維持する。

GLTF の packed metallic / roughness（B / G）は分離した Non-Color grayscale 画像へ変換し、直接の Image Texture ノードへつなぎ直す。base color / emission は sRGB、normal / scalar は Non-Color。opaque Principled、active UV、Flat / Repeat / Linear の exporter 対応形式に合わせる。非対応のリンク・透明・transmission・coat・volume・displacement・rig / animation は対象名と理由を報告して停止する。`--pack-pbr` だけで任意 shader の変換が済むとは扱わない。

Task 2 レビューで culling の非保持と bounds 計算の不足を確認した。実寸・接地は world 変換した実頂点から求める。現 exporter は GLB の片面 / 両面設定を出力しないため、既定では素材名付きで停止する。利用者が `--allow-culling-change` でこの差を明示了承した場合だけ変換を許し、各素材の元設定と非保持の警告を report に残す。他の非対応素材を許可するオプションではない。ユーザーの推奨案への委任の範囲で安全側の追加ゲートを設ける。

GLB と元テクスチャは上書きしない。編集可能な .blend、分離テクスチャ、三角形数・mesh / material 数・画像寸法の report を保存する。変換先は新規ディレクトリで、失敗途中の成果物を正式な結果として公開しない。convert orchestration は `.blend` から `resoloop blender export --preserve-hierarchy --pack-pbr` を実行し、成功時だけ bundle を公開する。親 Slot はユーザーが確認した selector を引数で指定する。apply は自動実行しない。

## 5. Windows / Resonite の受入経路

最初にローカルで作った小さなテクスチャ付き fixture を変換・export する。Resonite ホストの texture file import には Windows が読めるパスが必要。Linux の絶対パスを Windows から読めると仮定しない。

推奨の当面の経路は bundle 一式を Windows へコピーし、Windows 版の最新公開 ResoLoop で diff / apply / test を実行すること。JSON だけでなく mesh・textures・report を渡す。Windows 版の実測 version、接続 URL と対象 Slot、bundle のパス、state の保存先を記録する。各 apply で同じ state を使い、Linux 側で同じ対象の別 state を作らない。既存 Linux state がある対象へ切り替える場合は、共有する state を移送し境界を再確認する。

既存の共有パスが両側で同じ絶対パスとして読めることを実証できる場合だけ、コンテナからの apply を使える。ResoLoop 本体の画像送信機能は今回変更しない。

受入では接続先・所有範囲を確認して diff をレビューし、明示許可後に apply。再適用の無変更、再起動後の保持、テクスチャ付き表示を確認する。実機・API key・有料生成の許可がないこの実装セッションでは、ここを未確認と記録し Issue を自動 close しない。

## 6. 共有スキルと検証

`.agents/skills/meshy-resoloop/SKILL.md` を追加し、root の `.claude/skills/meshy-resoloop` は既存方式の symlink にする。プロジェクトは祖先の共有スキルを利用できる既存方式と手動の明示パスで案内する。エージェント設定は変更しない。README / `.devcontainer/README.md` / `docs/meshy-resoloop.md` に実行例・費用確認・復旧・Windows handoff をまとめる。

自動テストは実行挙動に限定する。fake npm / CLI で導入の成否、キーなし拒否、秘密の非出力、送信不明の再送禁止、画像差し替え、lock・path 制約、ID 保存、wait / download 再開を確認する。Blender はローカル GLB fixture を実際に変換・export し、packed PBR の変換結果と非対応素材での停止を確認する。文書やモデル名の固定値テストは作らない。スキルは構文、参照、既存 layout 検査と trigger / non-trigger のレビューで確かめる。

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
