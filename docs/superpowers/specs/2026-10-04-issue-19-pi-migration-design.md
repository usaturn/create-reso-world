# Issue #19: pi 拡張構成の移行仕様

## 目的と進め方

pi-distill と旧 MCP 拡張を撤去し、組み込み MCP と移植元の拡張構成を使う。ユーザの「推奨案で進めて、途中で止めずに PR まで作成して」という指示により、設計・計画の通常の確認待ちを省略して実装する。以下はエージェントの判断であり、人による個別の設計承認ではない。

## 基準・依存

- 移植元 `usaturn/maatlog-poc` main: `1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`。2026-10-04 に HEAD を再取得し、#17 の基準と一致した。
- 移植先 main: `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`。#17 の `9699e94` 以降の #18 / PR #24 と #20 / PR #25 を含む。#18 は completed で close、PR #24 は main にマージ済み、祖先判定も成功。
- worktree `.worktrees/issue-19-pi-migration`、branch `feat/issue-19-pi-migration`、取り込み先 main。#19 の予約 ref は別の空コミットで管理する。

## 推奨案と裁定

| ID | 判断 | 理由・代替案 |
| --- | --- | --- |
| D-1 | 既存 `cleanup_pi_mcp.py` を拡張する | 移植元の shell 処理をコピーする案よりも既存のリンク拒否・JSON 検証・npm 巻き添え防止を保持できる。別 helper は安全策を重複させるため採用しない。 |
| D-2 | 変更前の settings と npm マニフェストをバックアップする | bind mount の利用者設定を復旧可能にする。事前検査やバックアップに失敗した場合は pi remove を実行しない。 |
| D-3 | 既存 models.json は一切書き換えない | 同名 provider の利用者独自モデルを安全に判別できない。既存の deepinfra-distill は使われない定義として保持し、新規雛形・setup・環境変数から参照を除く。自動削除は採用しない。 |
| D-4 | 移植元の +builtin:mcp と Google Developer Knowledge を採用 | Context7 と version-export は除外。HTTP ヘッダーは環境変数参照だけを共有する。 |
| D-5 | pi-lens の現状を維持する | ignore は既に移植元を包含する。既存テストが禁止する $schema を追加する利点がない。 |
| D-6 | Native 実行と最後の独立レビュー | cleanup と provisioning の変更は同じインターフェースに依存するため、実装はこのセッションで直列に行う。 |

## ファイル別比較表（#22 の集約用）

| ファイル | 判断 | 移植・適応内容と依存 |
| --- | --- | --- |
| `.devcontainer/install_beforehand.bash` | 適応 | cleanup は pi 導入直後・全拡張導入前を維持。pi-distill と tool-display helper 呼び出しを削除。既存 step を増減しないので STEP_TOTAL=25 を維持。#18 と #20 の変更を保持。 |
| `.devcontainer/cleanup_pi_mcp.py` | 適応 | 既存安全策を維持し、pi-distill と単独登録の tool-display / i18n、-builtin:mcp を撤去する。 |
| `.devcontainer/tests/fake_pi_packages.py` | 適応 | update --extensions の再構築をオフラインで模擬し、撤去対象の再混入と導入順を検証する。 |
| `.devcontainer/tests/test_pi_mcp_cleanup.py`、`.devcontainer/test-pi-mcp-cleanup.bash` | 適応・維持 | 拡張撤去、バックアップ、設定保持、実 npm の依存処理、初回・再実行を検証。wrapper の公開 CLI は維持する。 |
| `.devcontainer/setup_pi_tool_display.py` | 削除 | 廃止した拡張への調整を行わない。 |
| `.devcontainer/setup_pi.zsh` | 適応 | deepinfra だけを同期。配置は .devcontainer のまま、既存 models と他 provider を保持する。 |
| `.devcontainer/pi-models.json` | 適応 | deepinfra-distill のみ削除。union-alpha その他の定義は維持。 |
| `.devcontainer/zshrc.txt` | 適応 | PI_EXTENSIONS_LOCALE と PI_DISTILL_* の設定・説明を削除。ランチャーと update は保持。 |
| `.pi/settings.json` | 新規・適応 | extensions=["+builtin:mcp"]。移植元固有 version-export の skills は含めない。 |
| `.pi/mcp.json` | 新規・適応 | google-dev-knowledge の HTTP 設定だけを移植。context7 を含めない。 |
| `.pi-lens.json` | 既存維持 | tmp / .venv / artifacts / .resoloop / external / private の ignore を保持。 |
| `.pi/APPEND_SYSTEM.md` | 適応 | 正式なモデル名の根拠についての PI_DISTILL_MODEL 記述だけを削除。persona と role API は保持。 |
| `.devcontainer/test-install-beforehand.bash` | 適応 | cleanup の実行順と廃止 helper が呼ばれないことを検査。 |
| `tests/scripts/test-agent-config.bash`、`test-instructions.bash` | 既存維持・適応 | agent-config は既存検査を維持し、instructions に廃止指示の除去を追加。共有 pi 設定・ワールド cwd の検査は cleanup suite に集約する。 |
| `.devcontainer/README.md` | 適応 | MCP / 拡張の移行・バックアップ・既存 provider の保持を説明し、pi-distill の現役利用手順を削除。 |

## 移行処理の仕様

公開起動方法 `uv run --no-project .devcontainer/cleanup_pi_mcp.py` と `PI_CODING_AGENT_DIR`（既定 ~/.pi/agent）を維持する。

1. 既存のパス安全検査、settings の packages / extensions、4 種の npm マニフェスト、撤去対象の installed path と MCP state を事前検査する。extensions はリストでなければ変更前に停止する。
2. 対象は npm の pi-mcp-adapter、@upstash/context7-pi、pi-distill、pi-extensions-tool-display、pi-extensions-i18n。版固定と object-form の登録も同じ名前で撤去する。設定が無くてもマニフェスト・installed path に残留があれば撤去する。
3. npm が存在する場合、root manifest と保持する npm 拡張の宣言が必要。欠損時は npm uninstall の巻き添えを防ぐため変更せず停止する。
4. 変更が必要なら `agent/migration-backups/pi-retired-*` の固有ディレクトリ（0700）に、存在する settings と4種のマニフェストを元の相対配置・元バイト列で保存する。リンクされたバックアップ保存先は拒否し、保存先を表示する。初回の空環境や既に整理済みならバックアップや settings を新設しない。
5. pi remove --no-approve に npm 状態の整合を委ね、各撤去の後と全撤去後に登録・マニフェスト・installed path の残留を検証する。未登録の場合の exit 1 は、対象名の正確な診断行があり残留が消えた場合だけ許容する。他の失敗は理由と非ゼロ終了を返す。処理途中での外部 CLI 失敗は自動ロールバックせず、バックアップを残して停止する。
6. 最新 settings を再読込し extensions の `-builtin:mcp` だけを除き、他の項目と順番を保持して置換保存する。既存ファイルの mode を保持する。認証、models、利用者の extension config と native mcp.json / mcp-auth.json は編集しない。
7. 既存4種の pi 専用 MCP state を従来どおり除去する。共有 MCP 設定と ~/.npm は対象外。

組み込み MCP のプロジェクト設定はルートと各ワールドの `.pi -> ../.pi` から読む。pi の project trust が必要。Google Developer Knowledge には利用者が GOOGLE_DEV_KNOWLEDGE_API_KEY を設定する。実認証を使った接続確認はこの子の検証に含めない。

## 受け入れ条件と検証

- 初回 provisioning、既存状態の cleanup / provisioning、再実行、fake update --extensions 後に5対象の登録・マニフェスト・インストール残留がない。
- -builtin:mcp だけが消え、独自の extensions / packages / モデル・認証・native MCP と persona が保持される。
- バックアップの元バイト列・固有性、unsafe storage、JSON / CLI エラー、manifest 欠損による停止を検証する。実 npm のローカル依存 fixture で distill の transitive helper 撤去を確認する。
- pi の新規モデル雛形・setup・zsh・指示文から現役の廃止 provider / 環境変数 / tool-display 調整が消える。
- `.pi/settings.json` と `.pi/mcp.json` をルートと4ワールド cwd から読める。Context7 と移植元固有 skill を含めない。
- 子 worktree で `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills`、個別テストを実行する。#17 に記録された slum03 スキル未同期の配置検査2件は既存失敗として比較して報告し、修正しない。
- Spec / Plan / handoff 2ファイルの全文と SHA-256 manifest を #19 に公開し、コメントのみから復元・照合する。
- main 向け PR を1本作成し本文に Closes #19 を記載する。マージは本タスクでは行わない。

## 対象外

スキル（pi-model-name の旧環境変数記述も保持）、共有 MCP、Claude Code、pi ランチャーとサブエージェント、dsh / mount、ワールドと ResoLoop、既存 Spec / Plan は編集しない。Dev Container rebuild と全体 README 整合は #22 が担当する。
