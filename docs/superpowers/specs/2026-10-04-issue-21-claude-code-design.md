# Issue #21: Claude Code 設定とランチャーの移植

## 目的と進め方

親 Issue #17 の Claude Code 担当として、移植元にランチャーの挙動を揃え、移植先固有の `feature-dev` と `ccdu` を保つ。利用者は「推奨案で進めて、途中で止めずに PR まで作成」と指示した。以下の選択はエージェントの判断であり、個別の人間の設計承認を受けたとは扱わない。

既存機能の範囲が明確な変更だが、#17 の指定に従い Spec・Plan・handoff を作る。関連ファイルを直列に変更するため、実装は同じセッションで `executing-plans` を使う。最後に独立したレビューを実施し、main 向けの PR を 1 本作成する。マージと Dev Container rebuild は含めない。

## 比較基準と先行条件

- 移植元 `usaturn/maatlog-poc`: `1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`。開始時点でも main の HEAD はこの値。
- 移植先 `usaturn/create-reso-world`: `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`。PR #24（#18）、PR #25（#20）のマージを含む最新 origin/main。
- #18 は `state=closed`, `state_reason=completed`、PR #24 は main にマージ済み。#21 のネイティブ blocked_by は #18 のみ。開始時点で #21 の既存 PR・公開計画・予約 ref はない。
- 作業ブランチは `feat/issue-21-claude-code`、worktree は `.worktrees/issue-21-claude-code`。親 checkout の未追跡文書には触れない。

## ファイル別比較と判断

| 移植元 | 移植先 | 判断 | 理由・依存 |
| --- | --- | --- | --- |
| `.devcontainer/zshrc.txt`: ccd/ccdo/ccds | 同パスの alias | 移植 | ccd はモデルを固定せず、ccdo は opus、ccds は sonnet。cur/dev 等は範囲外 |
| 同ファイル: claude-deepinfra/ccdd | 同名関数 | 移植 | fable=`zai-org/GLM-5.3`、opus=`deepseek-ai/DeepSeek-V4.1-Flash`、既定 `--model opus` |
| 同ファイル: claude-deepinfra-glm/ccddg | 同名関数 | 既存維持 | 全 4 モデル割り当てと既定 opus が一致 |
| 同ファイル: cc_launcher_unsets | 同名配列 | 既存維持 | 移植先には ccdu 入力キーも含む。`test-herdr-migration.bash` の expected_unsets を基準に完全一致を検査 |
| 対応なし | claude-opencode-union/ccdu | 既存維持 | 移植先独自機能。モデル・認証優先順位・子プロセス設定を変えない |
| `.claude/settings.json` | 同パス | 既存維持 | env・marketplaces・feedbackSurveyRate は一致。移植先のみ feature-dev が追加済み |
| `.devcontainer/install_beforehand.bash` | 同パス | 既存維持 | 移植先は 5 プラグインを導入する上位集合。test-install-beforehand で宣言との一致を確認。#22 への変更依頼なし |
| `CLAUDE.md`: AskUserQuestion・監視・言語運用 | `CLAUDE.md` | 適応 | `@AGENTS.md` とワールドの指示継承を維持し、終了コード確認を含む監視手順への参照を明確にする |
| `CLAUDE.md`: 共通規約 | `AGENTS.md` | 既存維持 | リポジトリ境界、uv、設計、文書、SDD 監視は既に規定済み。MaatLog 固有の親子 repo、CI 免除、リリース権限、検証入口、文書配置は持ち込まない |
| `.mcp.json` | 同パス | 既存維持・編集対象外 | #21 では変更しない。移植元のツリーには `.claude/agents/` の追加定義がない |
| `.claude/settings.local.json` | 同パス | 除外 | 個人設定。取得・コピー・コミットしない |
| `scripts/poke_claude_onboarding.py`, `scripts/unpoke_claude_onboarding.py` | 対応なし | 不採用 (D-2) | 下記の bind mount と利用者状態への影響を避ける |
| ランチャーの検証 | `.devcontainer/test-herdr-migration.bash` | 適応 | fake CLI に渡る argv・環境変数・終了コードを実行して確認する |
| Claude Code の案内 | `.devcontainer/README.md`: Claude の節 | 適応 | alias・モデル対応・認証・手動更新・onboarding 不採用を説明する |

## 設計と決定

### D-1: ランチャーを必要な箇所だけ統合する（推奨）

一括コピーは pi、Cursor/Devin、Herdr、ccdu に影響するため採らない。現状維持では #21 のモデルと alias の受け入れ条件を満たさない。以下の値を明示的に適用する。

| 起動名 | 既定の CLI 引数 | fable | opus | sonnet | haiku |
| --- | --- | --- | --- | --- | --- |
| ccd | --dangerously-skip-permissions | Claude Code の設定による | 同左 | 同左 | 同左 |
| ccdo | --dangerously-skip-permissions --model opus | 同上 | 同上 | 同上 | 同上 |
| ccds | --dangerously-skip-permissions --model sonnet | 同上 | 同上 | 同上 | 同上 |
| claude-deepinfra / ccdd | --model opus（ccdd のみ権限確認を省略） | zai-org/GLM-5.3 | deepseek-ai/DeepSeek-V4.1-Flash | deepseek-ai/DeepSeek-V4-Flash-0731 | openai/gpt-oss-20b |
| claude-deepinfra-glm / ccddg | --model opus（ccddg のみ権限確認を省略） | deepseek-ai/DeepSeek-V4.1-Flash | zai-org/GLM-5.3-Flash | deepseek-ai/DeepSeek-V4-Flash-0731 | openai/gpt-oss-20b |
| claude-opencode-union / ccdu | --model opus（ccdu のみ権限確認を省略） | union-alpha | union-alpha | union-alpha | union-alpha |

プロバイダ関数は既存の `env "${cc_launcher_unsets[@]}"` で子プロセスだけの設定を作り、末尾の `"$@"` を保つ。親シェルの値は変更しない。CLI 引数に空文字・空白・改行・glob・`--model` があっても順序と値を保ち、ユーザーのモデル指定を既定引数の後へ渡す。戻り値は Claude CLI の終了コード。

DeepInfra の入力は DEEPINFRA_TOKEN。ccdu は OPENCODE_GO_CLAUDE_API_KEY → OPENCODE_API_KEY → OPENCODE_GO_API_KEY の既存の非空値優先順位を保つ。必須キーがなければ子 CLI を呼ばずに非ゼロで止まる。実キーは使わない。

### D-2: onboarding の自動・手動スクリプトを不採用とする（推奨）

移植元の 2 スクリプトは `hasCompletedOnboarding` を変更し、バックアップを作って同じディレクトリの一時ファイルを `os.replace` する。移植先の `~/.claude.json` はファイル自体が bind mount されるため、この置換は EBUSY になり得る。また、このフラグは API 認証の代替ではなく、利用者の初回設定状態を変更する。

通常の Claude Code の初回設定を利用し、自動実行もしない。mount 対応の安全な更新・復元ツールまで採用する案は今回の目的に対して過剰なので採らない。`.devcontainer/poke_claude_onboarding.py`、`unpoke_claude_onboarding.py`、`test-claude-onboarding.bash` は作成しない。利用者の実設定へ書き込まない。

### D-3: 既存の共通規約とプラグイン構成を維持する

CLAUDE.md は AGENTS.md を読み込む形を維持する。Claude 固有の途中出力の扱いを monitoring-long-tasks に接続し、親 checkout の指示やワールドの AGENTS/CLAUDE は変更しない。共有ルールの新規追加は不要。

## 検証と受け入れ条件

1. ccd/ccdo/ccds を実際の zsh から呼び、fake CLI の argv が表と一致する。
2. 6 つのプロバイダ関数名でモデル割り当て、権限フラグ、全引数、環境の隔離、親シェル保持を確認する。
3. 認証欠落なら子 CLI を呼ばず失敗し、キー優先順位と Claude CLI の非ゼロ終了コードを保つ。
4. `bash .devcontainer/run-tests.bash .devcontainer/test-herdr-migration.bash .devcontainer/test-install-beforehand.bash` が成功する。プラグイン宣言と導入は既存テストで検証する。
5. `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills` を実行する。既知の slum03 未同期による check-layout と tests/scripts/test-check-layout.bash の失敗は名前と理由を報告し、範囲外の同期はしない。その他の失敗は調べる。
6. Spec、Plan、handoff 対の全内容を #21 に公開し、manifest のハッシュ・バイト数に従って新規ディレクトリへ復元する。
7. main 向けの PR を 1 本作成し、本文に `Closes #21` と検証・未検証事項を記載する。

検証は fake CLI と一時 HOME を使う。実認証、実 `~/.claude.json`、ローカル許可、ホストのセッションを変更しない。rebuild と実プロバイダへの API 呼び出しは #22 の統合検証に残す。

## 仕様確認と自己点検

Context7 の `/anthropics/claude-code` で設定の優先順位とモデル環境変数を確認した。モデル名・提供先の値は Issue の移植元基準から採用し、現在の API で利用可能との主張はしない。Spec の編集範囲、表の値、既知の失敗、非採用スクリプト、公開成果物が #21 と一致することを自己点検した。
