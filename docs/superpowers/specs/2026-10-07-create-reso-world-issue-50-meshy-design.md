# Issue #50: Meshy CLI と Blender / ResoLoop 連携

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/50
- 基準 HEAD: `b1b0614`（origin/main）
- 状態: completed
- 完了範囲: 初回実装・ローカル検証・PR 作成と、PR #54 のレビュー修正・検証・自己レビュー。実機受入は未確認。
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
- `status` / `wait --timeout N` / `download [--timeout N]`: 既存 ID だけで再開する。FAILED / CANCELED は成功にしない。download は GLB とテクスチャを含む生成物を保存し、当該取得の総待ち時間だけを任意に延長できる。
- `list --resource text-to-3d|image-to-3d`: 送信結果不明時の照合用。生成しない。
- `attach --operation NAME --task-id ID`: 人間が照合した既存 ID を GET で確認し、ID・type・resource と operation の対応を検査してから紐付ける。refine の preview ID 自体は拒否する。POST しない。
- `balance`: キー設定後に明示的な認証・残高確認を行う。`auth status` の masked credential は出力しない。
- `convert`: 後述の Blender 変換・export。API キー不要で、Meshy に通信しない。

保存先は `<world>/content/generated/meshy/<NAME>/operation.json`、元ファイルはその下の `source/`、変換結果は `converted/`。CLI journal は `<world>/.resoloop/meshy-cli/operations/`。ワークスペースの bind mount 内なので rebuild 後にも残る。生成済みモデルは採用時にプロジェクトの既存方針に従って保持する。API の一時 URL だけに依存しない。

operation.json は schema、操作 UUID、kind / resource、要求条件、入力画像のパスと SHA-256、処理段階、task_id / status / progress、download manifest、変換結果を持つ。CLI の生出力や Authorization を保存しない。許可した項目だけ抽出し、キー文字列が混入した値は出力・保存前に伏せる。CLI の stderr / traceback をそのまま返さない。

入力・出力・journal の symlink と project 外への逸脱を拒否する。NAME は単一の安全な path segment。manifest は一括置換し、操作ごとの非ブロッキング lock を持つ。API 実行中は lock を保持する。ローカル画像の内容が plan 時から変化したら submit を拒否する。

Task 1 レビューで、公式 CLI が API エラー本文を journal の `error` に書く経路を確認した。ラッパー出力の除去だけでは不十分なため、`scripts/meshy_cli_guard.mjs` を Node の preload として起動し、検証済み 0.4.0 の journal JSON 書込み経路で error 本文を保存前に除去し、キー文字列・認証 field を書かせない。継承された Node debug / preload は破棄し、ラッパー自身が指定する guard のみを有効化する。これはユーザーが委任した推奨案の範囲で、秘密情報非保存の要件を満たすための補強である。CLI 更新時は実際の書込み経路を再確認する。

## 3. 生成条件と再送禁止

`ai_model` は明示値（既定は `latest`）として記録する。text preview は形状だけ、refine はテクスチャ生成として別の有料操作にする。image は `should_texture` を明示し、テクスチャありの場合は `enable_pbr`、`texture_resolution`（推奨 `2k`）、`remove_lighting`、`image_enhancement`、`target_formats=[glb]` を明示する。ultra を自動有効化しない。任意 JSON passthrough、rig、animation、複数件生成は追加しない。

POST 前に stage を `submitting` に保存する。受け付けた ID が見つかれば、それがエラー応答に含まれていても失わず保存する。CLI timeout、異常終了、不正 JSON、シグナル中断、結果不明は `unknown` にし、同じ operation の submit は禁止する。CLI journal と list で照合して attach する。既知 ID がある submit は生成を再送しない。新しく生成し直す場合は新しい NAME と課金の明示許可が必要。

wait の timeout / interruption、download の失敗では ID と段階を保持し、そのコマンドだけ再開する。download は成功ファイルを保持し、CLI の `--overwrite` を使った既存タスクの再ダウンロードを許容するが、ローカル path の検証を省略しない。download 全体が完了し、manifest の主 GLB が実在するまで変換可能にしない。asset key 付き GLB は共通 helper で `model.glb` を一意に選ぶ。すべて key 無しの古い manifest に限り、従来どおり単一の取得済み GLB を選ぶ。

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

## PR #54 のレビュー修正（2026-10-07）

### 対象・実行許可・結論

- 対象: `usaturn/create-reso-world` PR #54、`feat/issue-50-meshy`。
- 検証したコミット済み HEAD: `22ff0e042079d00d5c3851824bd27dbcdf5a8ab8`。
- 入力: `reviews/#54-feat-issue-50-meshy/` の全4ファイル（deepseek-deepseek-v4.1-flash.md、claude-opus-5-5.md、xai-grok-4.7.md、SWE-2-High.md）。各対象 HEAD は `22ff0e042079`。
- 実行許可: ユーザーが `review-fix-planning #54` を指定。計画のみの指定はなく、スキルの完遂経路に従って選別・必要な修正・検証・自己レビュー・既存 PR への push・状況コメントまで行う。課金 API、実キーの使用、Windows / Resonite への操作は行わない。
- 結論: **1 修正して既存 PR へ push**。入力の全17項目は、解消済み4 / 対応する3 / 対応しない10。候補も一覧から落とさず判定する。指摘の重大度ラベルや票数は判断根拠にしない。
- 文書: 同じ Issue・PR・テーマの既存 Spec（このファイル）を更新する。別のレビュー回用 Spec は作らず、初回の設計・実施結果は上の節に履歴として残す。

### 全指摘と候補の判定

ID の先頭は D=deepseek、C=claude、G=grok、S=SWE。U は各レビューの Unverified candidates。

| ID | 入力の項目 | 分類 | 現行 HEAD の根拠・到達条件 |
| --- | --- | --- | --- |
| D-I1 | list / balance の operation が無視される | 対応しない | parser は受理し execute は参照しない。照会はアカウント単位であり、生成・対象への書込みはない。絞込み機能の設計・help の問題で致命的ではない。S-I1 と同じ論点。 |
| D-U1 | 空 mesh の bounds が名前付き拒否にならない | 解消済み | 0頂点 POSITION accessor の GLB を実 Blender 5.0.1 で処理すると `active_uv_required` の名前付き拒否で停止し、blend はない。報告された bounds への到達を再現しなかった。 |
| C-M1 | 2つの GLB を download 後に convert できない | 対応する | `downloaded` まで進むが `source_glb` は `unique_glb_required`。公式 API は image task の pre_remeshed_glb をサポートし、外部の既存 task を attach する経路で到達する。既定 create が追加 GLB を返すとは主張しない。manifest の key を捨てるため、主 GLB を選べず主要な変換処理が止まる。 |
| C-L1 | refine に preview task を attach できる | 対応する | 偽 CLI の SUCCEEDED preview を refine に attach すると stage=succeeded、preview ID が固定される。復旧手順で誤った成果を refine として使う。人間の照合に加え、機械的に確認できる kind/resource と preview ID の検査が必要。 |
| C-L2 | download の固定120秒上限 | 対応する | `_call` の待ち上限で download が毎回 cli_timeout となり、同じ ID を再取得しても完了しない。8k / 大きな資産と低速回線は利用可能な構成。試験では待ち上限だけ0.3秒に短縮して実 subprocess timeout と ID 保持を再現した。 |
| C-U1 | 実 Meshy 素材が convert の非対応条件に当たる | 対応しない | opaque / exporter 対応素材への限定と拒否条件は Spec §4 / 運用手順に明記。任意の Meshy 出力の変換成功は保証していない。実生成物の受入は未実施であり、対応範囲を広げる設計変更は今回行わない。 |
| C-U2 | 8k 変換が300秒を超える可能性 | 対応しない | 300秒 / 親310秒の上限と安全な停止をコード・回帰試験で確認。画素ループの推定だけでは実変換が必ず失敗する根拠にならない。大きな変換の実時間は未確認であり、無制限の変換成功は保証しない。 |
| C-U3 | image ai_model の API 受理 | 解消済み | 現行公式 Image to 3D API は ai_model を列挙し latest をサポート。Context7 と公式ページ本文を照合した。実課金生成を実施したという意味ではない。 |
| G-M1 | result:null の確定失敗を unknown に固定 | 対応しない | auth / result:null で一般エラーとなり unknown に保存、2回目の create はないことを再現。Spec §3 は送信後の CLI 異常・結果不明を再送禁止と定義。診断の粗さと同一 plan の再試行可否は設計論点。CLI 自身も terminal journal を同じ UUID では再送しないため、planned に戻す案は採用しない。未作成を外部で確定するまでは新規 create もしない。 |
| G-L1 | list が先頭10件だけ | 対応しない | 公式 CLI の page1 / size10 と wrapper の引数を照合。運用手順は recent task だけであり、特定できなければ停止と明記。全履歴照合・自動復旧を保証する設計ではない。 |
| S-L1 | plan 中断で0バイト manifest | 対応しない | save_operation を失敗させると空 manifest が残り、名前の再利用は拒否される。既存 plan や課金 task の消失はなく、新しい名前で offline plan を作れる。中断時の回復性改善は致命的ではない。 |
| S-L2 | 不存在 operation に lock / directory 作成 | 対応しない | status ghost は invalid_or_missing_operation で停止し、ghost/.lock が残る。API 呼出しも既存データの変更もない。操作用の空ディレクトリが残る軽微な副作用である。 |
| S-L3 | 破損 GLB に named report がない | 対応しない | 12byte GLB の実 Blender 処理で report / blend はなく、wrapper は安全に失敗する。破損入力の診断不足であり、成果の誤公開や元データの破損はない。既存の staging 撤去試験も通る。 |
| S-L4 | 第三者 CLI が通常の環境変数を継承 | 対応しない | MESHY_* / debug / proxy 等は除外、残りは信頼して導入する固定版 CLI に継承。GH_TOKEN 等の外部送信・保存経路は確認されていない。全環境 allowlist 化は設計選択で、今回の漏えい修正としては扱わない。 |
| S-I1 | list / balance の operation が無視される | 対応しない | D-I1 と同じ。原入力の2件として数え、修正はしない。 |
| S-U1 | image ai_model の受理 | 解消済み | C-U3 と同じ公式 API 仕様で確認。 |
| S-U2 | 実 CLI の journal が guard を通過するか | 解消済み | 一時 npm prefix の公式0.4.0 operation-store の beginOperation / updateOperation を実 writer と guard で実行。temp→rename が成功し、accepted ID は保持、error / sentinel key は書込み前に除去された。外部通信・実キーは使用しない。 |

### 守る条件と影響経路

「対応する」はいずれも現行 HEAD の再現した誤動作 (a)。C-M1 / C-L2 は主要処理の停止、C-L1 は誤った成果の確定で致命的と判定する。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| download 完了時に変換用の主 GLB を一意に選べる | `_download_files` → `download` | 修正する | key を保存し、主 GLB + backup GLB を実 download manifest で処理。曖昧な候補を成功扱いしない。 |
| 同上 | `source_glb` → convert の開始・処理後の再検査 | 修正する | 共通の選択 helper で主 asset key `model.glb` を使い、実 path / hash / bytes の既存検査を維持する。実 Blender 変換でも主 GLB を使用する。 |
| 同上 | 既存の key 無し schema1 manifest | 既に満たす（維持） | GLB が1件なら従来どおり使用、複数なら拒否。旧 manifest の移行は不要。 |
| attach が operation の kind/resource と一致する task だけを確定する | `query` の attach 分岐 | 修正する | 正しい3種類、種別不一致、resource 不一致、type 欠落、refine と preview 同一 ID を個別に検査。拒否前後の project 全体を比較する。 |
| 同上 | submit の refine preview 確認 | 既に満たす | 成功済み preview の ID / type / resource 検査の既存回帰を実行。 |
| 同上 | status / wait、submit で取得した既知 ID | 既に満たす | 既知 ID の一致検査・再送禁止・wait 再開の既存回帰を維持。既存の部分応答に type を新たに必須としない。 |
| 大きな資産の download を新しい create なしで再開できる | parser → execute → download → `_call` | 修正する | download に任意の `--timeout` を追加。遅い fake CLI を既定の短縮上限では失敗、長い指定では完了させ、同じ task ID / create 回数を比較する。 |
| 同上 | wait の timeout と status / balance / list の既定上限 | 既に満たす | 呼出しごとの timeout の既存挙動を維持。download の指定だけを変更し、全体の固定上限を上げない。 |
| 同上 | Blender の300秒上限 | 対象外 | API download の上限とは別。convert は offline・新規出力のみで、失敗時は公開しない。 |

### 直し方と選択理由

- C-M1: **asset key を保持し、download 完了判定と convert が同じ選択 helper を使う案を採用**。key 付きでは `model.glb` を一意に選ぶ。古い key 無し記録だけは従来の単一 GLB を許す。key の曖昧さ、primary 欠落、path/hash 不一致では止める。`--asset model.glb` のみ取得する案は元テクスチャ等の保存範囲を狭めるため不採用、任意 filename の決め打ち・manifest 手編集も不採用。
- C-L1: **GET の task ID / type / resource と refine の preview ID を検査してから保存する案を採用**。list の追加フィールドだけでは誤った task の確定を防げず、すべての status / wait に type を必須にする案は既知 ID の部分応答との互換を不要に変えるため不採用。
- C-L2: **download ごとの任意 timeout を採用**。未指定は現在の上限を保ち、利用者が既存 task の再取得だけ延長できる。全 API 呼出しの既定上限変更や無制限待ちは不採用。
- 過去の修正 `13a98bb` は journal の秘密非保存、`c9e02c4` は culling / 実頂点 bounds、`38db299` は暗黙 glTF 素材。今回の3条件と同じ致命的条件の再修正・修正コミット由来の回帰は確認されず、設計の見直しへの切替きっかけ1・2には該当しない。自己レビューで再発した場合はスキルのきっかけ3に従う。

### 失敗時の検証と作業項目

- attach 拒否は、初期化済みの正常 project / journal で実行。project 全体の path 有無・byte列・mode・symlink 参照先・hardlink の共有状態・一時ファイル / バックアップを snapshot し、拒否前後で同一とする。必要な GET は許可し、新しい create は0回。異常は1例につき1つだけ入れる。初回 CLI config の作成は既存挙動であり、この入力検査が完全な read-only 起動を追加するという保証ではない。
- attach の種別/resource ガードと preview ID ガードを、専用 worktree ではなく新しい一意な隔離 worktree 上の修正コピーで1つずつ外す。それぞれの負例が失敗することを確かめ、終了後は登録を外して親ディレクトリを消す。
- download 途中 timeout は I/O 中断で、source 内の完了済みファイルと task ID を保持、downloads は failed / partial、stage は succeeded。入力不正による無変更とは区別する。
- Task A（テスト必要）: 3不具合の failing regression を追加し RED を確認、最小修正で GREEN、既存 workflow / conversion 回帰を実行。守るロジック・分岐・I/O があるためテストを採用する。
- Task B（新規テスト不要）: 運用手順とこの Spec に主 GLB 選択、attach の確認、download timeout を反映。文面照合テストは作らず、help 実行・参照・diff を確認する。
- Task C（検証）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、関連 pytest、Ruff / 構文 / diff を実行。スキル自体は変えないのでスキル suite の再実行は反映の必須条件にしない。
- Task D（自己レビュー）: 1回だけ、反証・PR全体・検出力の3観点を読み取り専用で確認。指摘は同じ基準で判定し、必要な追修正後は検証だけやり直す。

### 調査時点の検証結果

- 隔離 worktree の HEAD / clean と API の PR head を照合。全20変更ファイル全文、関連呼出し、テスト、全入力の指摘と候補を調査した。読取り専用 recon が workflow と conversion / docs を分担し、非担当箇所の全文は controller が補完した。
- 修正前の `test_meshy.py` + `test_meshy_conversion.py`: **151 passed / 81.73秒 / exit 0**。現在の Blender 5.0.1 は利用者環境の NumPy 2.5.3 を読める。標準 rebuild 後の試験とは区別する。
- 3不具合と G-M1 / S-L1 / S-L2 / S-L3 を隔離 worktree で再現。D-U1 は名前付き拒否となり、成果は公開されない。
- Context7 3問合せと公式 API ページ、公開 npm 0.4.0 の TaskView / artifact / journal / error 処理を照合した。Context7 の旧パラメータ断片ではなく、現在の公式本文で texture_resolution=2k/4k/8k と ai_model=latest を確認した。
- 調査用の隔離 worktree とその親一時ディレクトリは Spec 更新前に撤去済み。既存の PR worktree を再利用しており、片付け時にこの既存 worktree / branch は削除しない。

### 修正・自己レビューの結果

- C-M1 / C-L1 / C-L2 を修正。変更は workflow / parser / conversion と関連2テスト・運用手順・この Spec の7ファイルに限定。初回 Plan は完了した実装履歴なので変更しない。
- 実装担当は19件の期待した RED assertion failure（14件の既存動作の対照は PASS）を確認してから修正。focused GREEN は33 passed。既存の安全条件を含む2ファイル全体は192 passed、skip なし。
- controller の最終再実行: `env -u MESHY_API_KEY uv run --no-project --with pytest pytest tests/scripts/test_meshy.py tests/scripts/test_meshy_conversion.py -q --tb=short` → **192 passed / 97.66秒 / exit 0**。
- 環境の回帰: `bash .devcontainer/run-tests.bash` → **28 scripts PASS / 125秒 / exit 0**。`bash scripts/check-layout.sh` → **PASS / 2秒 / exit 0**、既存4 project の SKILL_SYNC_REQUIRED 警告は未変更。
- Ruff check / format（変更した Python 5ファイル）、Python 構文、Node guard 構文、help 実行、`git diff --check` は PASS。
- attach の独立負例は13件（kind/type/resource 9、同一 preview ID 1、既存の ID 一致条件3）。全 project の bytes / mode / path有無 / inode / nlink / symlink参照先 / hardlink共有状態 / source / journal / cache / backup / staging / temp を前後比較して不変を確認。GET 以外の追加コマンドと create はない。
- 隔離 worktree の修正コピーで kind/resource ガードのみ外すと対応する9負例すべてが assertion failure、preview ID ガードのみ外すと対応する1負例が assertion failure。各 exit 1。ガード復元後は13負例すべて PASS / exit 0。専用 PR worktree のガードは外していない。
- active LSP probe は5ファイルを対象に実行。既存の厳密 bool identity と外側例外境界に対する補助 heuristic 8件、2ファイルの判定は inconclusive。LSP が全面 clean であるとは主張しない。これらは今回の変更部分ではなく、実回帰・Ruff と照合した。

自己レビューは **1回・3観点**（反証、PR全体、検出力）を別々の読み取り専用担当へ直列委譲した。scope / diff が不足した初期 dispatch はレビューを開始せず、読み取り可能な差分を揃えてから実施した。全 PR 差分・全20変更ファイル全文の確認に未読範囲はない。致命的な新規指摘は0件、設計の見直しのきっかけ3はなし。自己レビュー後の実装修正はなく、2回目のレビューは行っていない。

| 自己レビュー ID | 提案 | 分類 | 理由 |
| --- | --- | --- | --- |
| SR-T1 | timeout 前に書いたファイルの保持を新しい slow fake でも検査する | 対応しない | 新テストは送信済み ID と同一取得の待ち時間延長を検査する。途中ファイル保持は既存 partial-download 回帰と実装で確認しており、新しい破損の再現や削除されたガードはない。追加の安全網だけなので足さない。 |
| SR-T2 | skipped primary / failed duplicate-primary の追加分岐テスト | 対応しない | 共通 selector は failed も一意性の判定に含め、主候補は written / skipped に限る。誤動作の再現はなく、検査している既存条件をさらに列挙する保険だけなので足さない。 |

入力17件は4 / 3 / 10、自己レビュー提案2件は0 / 0 / 2。**全19件の合計は、解消済み4 / 対応する3 / 対応しない12**。自己レビューで対象外とした論点（実機受入、素材拡大、8k実時間、照会範囲、result:null再試行、plan/破損入力の診断、全環境allowlist、敵対的パス置換、初回CLI設定作成、既知IDのtype必須化、予算自動判定、checkout自動移動、PowerShell5.1対応）は、上の一覧・対応範囲・元の明示的な確認ゲートに照らして追加修正しない。実機の未確認事項は、指摘0件を根拠に解消した扱いにしていない。

標準 rebuild、実 API の認証・残高・課金生成・実生成物、Windows / Resonite の texture 表示・再適用・保存再起動後の保持、実際の8k変換時間は引き続き未確認。PR 説明にも既知の制限と回避経路を記載する。今回は結論1であり、マージ・Issue close は行わない。push / コメントの結果は本 Spec ではなく状況コメントと完了報告へ記録する。

### このレビュー修正の所要時間

controller の計測開始は22:14:10 UTC、最終回帰完了は23:24:55 UTC（70分45秒、初期のタスク表示・最初の情報取得は計測外）。主な区間は、調査・分類・Spec準備22:14:10〜22:43:59（29分49秒）、実装担当22:43:59〜22:53:17（9分18秒）、統合検証・ガード対照・自己レビュー3席・判定22:53:17〜23:22:40（29分23秒）、最終回帰・記録23:22:40〜23:24:55（2分15秒）。コミット・push・コメント・片付けはこれ以降の区間として完了報告に記録する。

実装担当の実測内訳: source / 条件確認116秒、test編集・RED76秒、最小修正・focused GREEN99秒、安全条件の追加検査・手順6秒、全2ファイル回帰103秒、静的検査・diff確認・報告158秒。recon / review 担当のランタイムには時計がなく、各担当の独立した実測時間は取得できないため推定値は使用しない。
