# maatlog-poc からの移植の比較表

[usaturn/maatlog-poc](https://github.com/usaturn/maatlog-poc) の pi と Claude Code の設定を、このリポジトリへ移植したときの記録である（Issue #17、子 Issue #18〜#22）。移植元の全ファイルについて、移植したか、移植先に合わせて変えたか、持ち込まなかったかを、理由と担当 Issue とともに残す。

利用者が参照する現在の手順は `README.md` と `.devcontainer/README.md` にある。既存の環境への反映は `.devcontainer/README.md` の「既存環境の更新」を参照する。

## 基準

- 移植元: usaturn/maatlog-poc の [`1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`](https://github.com/usaturn/maatlog-poc/tree/1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a)。ファイル（blob）455 件と submodule 1 件（`public`）
- 移植先: このリポジトリの `main`。比較を始めた時点は `9699e94`、#18〜#21 の変更がそろった時点は `01affb7`
- 移植元の `main` は 2026-10-05 時点で `e1f042e` に進んでいる。追加の 17 コミットで変わった 28 ファイルは、レビュー系ツール（`tools/herdr_pr_review/**`・`pr-review-fix-loop`・`.devcontainer/herdr-pr-review.toml`）、`.devcontainer/README.md` のその説明、`CLAUDE.md` の「正本」の言い換えの規則だけである。最後のものは、このリポジトリの `AGENTS.md` に同じ文がある。どれも取り込まない

## 判断の区分

| 判断 | 意味 |
| --- | --- |
| 移植 | 移植元の内容（撤去を含む）を、そのまま取り込んだ |
| 適応 | 移植元の方針を、移植先の構成（配置、ランチャー、安全策など）に合わせて取り込んだ |
| 既存維持 | 移植先の現状を保った。移植元と同一、移植先の方が新しい、移植先にだけある、のいずれか |
| 除外 | 検討して持ち込まなかった。#17 の除外 3 項目（Grok Build・`ccda`・dsh）と、各子 Issue が採用しなかったもの |
| 対象外 | 比較の範囲外とした。#17 の「対象外とした項目」（スキル、レビュー系ツール、pi の Context7）、MaatLog 固有のもの、pi と Claude Code 以外のエージェントとツール |

## 読み方

- パスはリポジトリのルートからの相対パスで書く。`**` はそのディレクトリの配下の全ファイルを表す
- 移植元のパスが「なし」の行は、移植先にだけあるファイルや変更である
- 1 つのファイルを節ごとに別の子 Issue が担当した場合は、節ごとに行を分けた
- 担当 Issue は、その判断を記録した Issue である。#17 の本文で範囲外と決めた項目は #17 とした
- 子 Issue の Spec が別の表記（「削除」「不採用」など）を使った行は、判断の後ろに括弧でその表記を残した。表記を揃えただけで、判断は変えていない
- 各子 Issue の判断の詳細は、その Spec にある: #18 `docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md`、#19 `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`、#20 `docs/superpowers/specs/2026-10-04-issue-20-pi-launchers-design.md`、#21 `docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md`、#22 `docs/superpowers/specs/2026-10-05-issue-22-integration-design.md`

## 比較表

### pi 本体・拡張・MCP

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の pi の導入、旧拡張の撤去（`Removing npm:pi-mcp-adapter`・`Removing npm:pi-distill`）、拡張の導入、`models.json` の配置 | 同じファイルの同じ手順 | 適応 | 撤去は移植先の `cleanup_pi_mcp.py` で行い、pi の導入の直後・全拡張の導入の前に実行する。pi-distill と tool-display の調整の呼び出しを削除した。手順の数は変えず、`STEP_TOTAL` は 25 のまま。#18 と #20 の変更を保持する | #19 |
| なし | `.devcontainer/cleanup_pi_mcp.py` | 適応 | 既存の安全策（symlink・hard link の拒否、npm の巻き添えの防止）を保ち、pi-distill、単独登録の tool-display と i18n、`-builtin:mcp` の撤去を足した。`@upstash/context7-pi` と `pi-mcp-adapter` の撤去も続ける | #19 |
| なし | `.devcontainer/pi_json.py` | 適応（#19: 新規、PR #27 のレビュー修正） | cleanup と 3 つの provider setup が共有する JSON の読み込み（有限の数値の検査）・保存（一時ファイルでの置き換え、mode の保持）・バックアップ・リンクの拒否。移植元には無い | #19 |
| なし | `.devcontainer/tests/fake_pi_packages.py` | 適応 | `pi update --extensions` による再構築をオフラインで模擬し、撤去した拡張の再混入と導入の順序を検査する | #19 |
| なし | `.devcontainer/tests/test_pi_mcp_cleanup.py`・`.devcontainer/test-pi-mcp-cleanup.bash` | 適応（#19: 適応・維持） | 拡張の撤去、バックアップ、設定の保持、実 npm の依存の扱い、初回と再実行を検査する。wrapper の公開 CLI は保つ | #19 |
| なし | `.devcontainer/setup_pi_tool_display.py`（削除） | 適応（#19: 削除） | 廃止した拡張への調整を行わない。移植元は pi-distill の廃止とともにこの調整を持たない | #19 |
| `scripts/setup_pi.zsh` | `.devcontainer/setup_pi.zsh` | 適応 | deepinfra だけを同期する。配置は `.devcontainer/` のまま。既存のモデルと他の provider を保持する | #19 |
| `.devcontainer/pi-models.json` | 同じ | 適応 | `deepinfra-distill` だけを削除した。`union-alpha` などの移植先の定義は保つ | #19 |
| `.devcontainer/zshrc.txt` の pi の環境変数 | 同じファイルの同じ箇所 | 適応 | `PI_EXTENSIONS_LOCALE` と `PI_DISTILL_*` の設定と説明を削除した。ランチャーと `update()` は保つ | #19 |
| `.pi/settings.json` | 同じ | 適応（#19: 新規・適応） | `extensions` を `["+builtin:mcp"]` にした。移植元にある MaatLog 専用の `version-export` の skills は含めない | #19 |
| `.pi/mcp.json` | 同じ | 適応（#19: 新規・適応） | Google Developer Knowledge の HTTP の設定だけを移植した。`context7` は含めない（pi の Context7 は #17 で対象外） | #19 |
| `.pi-lens.json` | 同じ | 既存維持 | 移植先の ignore（`tmp`・`.venv`・`artifacts`・`.resoloop`・`external`・`private`）は移植元を包含する | #19 |
| `.pi/APPEND_SYSTEM.md` | 同じ | 適応 | 正式なモデル名の根拠としての `PI_DISTILL_MODEL` の記述だけを削除した。persona と Superpowers の role API の運用は保つ。移植元の旧 API の記述は持ち込まない | #19 |
| なし | `.devcontainer/test-install-beforehand.bash` | 適応 | cleanup の実行の順序と、廃止した helper が呼ばれないことを検査する | #19 |
| なし | `tests/scripts/test-agent-config.bash`・`tests/scripts/test-instructions.bash` | 適応（#19: 既存維持・適応） | agent-config の既存の検査は保ち、instructions に廃止した指示が無いことの検査を足した。共有の pi の設定とワールドの cwd の検査は cleanup のテストにまとめた | #19 |
| `.devcontainer/README.md` の pi の拡張・MCP・pi-distill の節（「pi-distill の撤去（#508）」「setup スクリプトを使う場面」） | 同じファイルの「pi の旧拡張・MCP 設定の移行」「組み込み MCP と廃止した拡張」「setup スクリプトを使う場面」 | 適応 | 移行、バックアップ、既存の provider の保持を説明し、pi-distill を使う手順を削除した | #19 |

### pi のランチャー・モデル・サブエージェント

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/pi-superagents-exec.zsh` | 同じ | 移植 | pi を `--tui-mode regular` で起動する。setup の案内のパスは `.devcontainer/` のまま | #20 |
| `.devcontainer/pi-superagents/pigs.json`・`.devcontainer/pi-superagents/pixg.json` | 同じ | 移植 | `cheap`（`pixg` は `balanced` も）を `opencode-go/deepseek-v4.1-flash` の `max` にした | #20 |
| `.devcontainer/pi-superagents/pigo.json`・`.devcontainer/pi-superagents/pigod.json`・`.devcontainer/pi-superagents/piccg.json`・`.devcontainer/pi-superagents/piccd.json`・`.devcontainer/pi-superagents/piga.json`・`.devcontainer/pi-superagents/pigl.json` | 同じ | 既存維持 | 移植元と同一 | #20 |
| なし | `.devcontainer/pi-superagents/pigou.json` | 既存維持 | 移植先にだけあるランチャー | #20 |
| `.devcontainer/pigs` | 同じ | 移植 | `OPENCODE_GO_API_KEY` から `OPENCODE_API_KEY` への引き継ぎを足した。Codex OAuth の確認は保つ。案内のパスは `.devcontainer/` | #20 |
| `.devcontainer/pixg` | 同じ | 移植 | Codex OAuth の確認をやめ、引き継ぎを足した。案内のパスは `.devcontainer/` | #20 |
| `.devcontainer/pigo`・`.devcontainer/pigod`・`.devcontainer/piccg`・`.devcontainer/piccd`・`.devcontainer/piga`・`.devcontainer/pigl` | 同じ | 既存維持 | 差分は setup の案内のパスだけ。setup スクリプトを `.devcontainer/` に置く決定に合わせる | #20 |
| なし | `.devcontainer/pigou` | 既存維持 | 移植先にだけあるランチャー。`--tui-mode regular` は共通ヘルパで付く | #20 |
| `scripts/setup_pi_superagents.zsh`・`scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `.devcontainer/` の同名のファイル | 適応 | 配置は `.devcontainer/` に残す。`pigou` を保ち、コメントの言い回しは移植先のまま | #20 |
| `scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `.devcontainer/` の同名のファイル | 適応（PR #27 のレビュー修正） | 入力の事前検査、`pi_json` による保存とバックアップ、`~` の展開を `setup_pi.zsh` と揃えた。provider の選択とランチャーは変えていない | #19 |
| `.devcontainer/install_beforehand.bash` のランチャーの配置と `setup_pi_superagents.zsh --if-absent` の呼び出し | 同じファイルの同じ手順 | 既存維持 | 呼び出し方は変えない（#20 の D-11）。移植先は `pigou` を含む 9 本を置く。`--if-absent` が共通ヘルパを毎回更新する | #20 |
| `.agents/sp-implementer.md` | 同じ | 既存維持 | 移植元と同一 | #20 |
| `.devcontainer/test-pi-superagents.bash` | 同じ | 適応 | `--tui-mode`、argv の一致、tier、`pixg` の認証、引き継ぎ、ヘルパの更新の検査を取り込んだ。here-string と `pigou` の検査は保つ。pi-distill の検査は #19 が別のテストで行う | #20 |
| `.devcontainer/test-pi-openai-codex.bash` | 同じ | 適応 | `--tui-mode`、全ランチャーの配置の検査、Pi 0.99.1 を取り込んだ。導入の手順の切り出しは移植先の手順に合わせた | #20 |
| `.devcontainer/README.md` の GPT-6・Grok 4.7・TUI モード・tier の節 | 同じファイルの同じ節 | 適応 | tier、認証、Pi の最小版、`--tui-mode regular` の節を移植し、`pigou` と `.devcontainer/` のパスに合わせた。既存環境の更新手順を足した | #20 |

### Claude Code

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/zshrc.txt` の `ccd`・`ccdo`・`ccds` | 同じファイルの alias | 移植 | `ccd` はモデルを固定せず、`ccdo` は opus、`ccds` は sonnet で起動する | #21 |
| `.devcontainer/zshrc.txt` の `claude-deepinfra`・`ccdd` | 同じ名前の関数 | 移植 | fable を `zai-org/GLM-5.3`、opus を `deepseek-ai/DeepSeek-V4.1-Flash` にし、既定を `--model opus` にした | #21 |
| `.devcontainer/zshrc.txt` の `claude-deepinfra-glm`・`ccddg` | 同じ名前の関数 | 既存維持 | 4 つのモデルの割り当てと既定の opus が一致する | #21 |
| `.devcontainer/zshrc.txt` の `cc_launcher_unsets` | 同じ名前の配列 | 既存維持 | 移植先は `ccdu` の入力のキーも含む。`.devcontainer/test-herdr-migration.bash` の `expected_unsets` と完全に一致することを検査する | #21 |
| なし | `.devcontainer/zshrc.txt` の `claude-opencode-union`・`ccdu` | 既存維持 | 移植先にだけある機能。モデル、認証の優先順位、子プロセスの設定を変えない | #21 |
| `.claude/settings.json` | 同じ | 既存維持 | env・marketplace・`feedbackSurveyRate` は一致する。移植先だけが `feature-dev` を足している | #21 |
| `.devcontainer/install_beforehand.bash` の Claude Code とプラグインの導入 | 同じファイルの同じ手順 | 既存維持 | 移植先は 5 つのプラグインを導入する上位集合。`.devcontainer/test-install-beforehand.bash` が宣言との一致を検査する | #21 |
| `CLAUDE.md` の AskUserQuestion・監視・言語の運用 | `CLAUDE.md` | 適応 | `@AGENTS.md` とワールドの指示の継承を保ち、終了コードの確認を含む監視の手順への参照をはっきりさせた | #21 |
| `CLAUDE.md` の共通規約 | `AGENTS.md` | 既存維持 | リポジトリの境界、uv、設計、文書、SDD の監視は既に定めてある。MaatLog 固有の親子リポジトリ、CI の免除、リリースの権限、検証の入口、文書の配置は持ち込まない | #21 |
| `.mcp.json` | 同じ | 既存維持（#21: 既存維持・編集対象外） | 移植元と同一。移植元に `.claude/agents/` の追加の定義は無い | #21 |
| `.claude/settings.local.json` | なし | 除外 | 個人設定。取得・コピー・コミットしない | #21 |
| `scripts/poke_claude_onboarding.py`・`scripts/unpoke_claude_onboarding.py` | なし | 除外（#21: 不採用） | `~/.claude.json` はファイルの bind mount なので、一時ファイルからの置き換えが失敗し得る。onboarding の状態を書き換えず、通常の初回設定を使う | #21 |
| `.devcontainer/test-herdr-migration.bash` の Claude のランチャーの検査 | 同じファイル | 適応 | fake CLI に渡る argv・環境変数・終了コードを実行して確かめる | #21 |
| なし | `.devcontainer/README.md` の「Claude Code の起動と更新」 | 適応 | 移植元の `.devcontainer/README.md` に Claude Code のランチャーの節は無い（#21 の Spec の「Claude Code の案内」の行）。alias、モデルの対応、認証、手動の更新、onboarding のスクリプトを採用しないことを説明する | #21 |

### Grok Build・`ccda`・dsh

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/dsh-launcher.bash`・`.devcontainer/dshccd`・`.devcontainer/dshccd.patch.yml`・`.devcontainer/dshgo`・`.devcontainer/dshgo.patch.yml` | なし | 除外 | dsh は #17 で除外した。持ち込まない | #18 |
| `.devcontainer/dsh-cordis.patch.yml` | `.devcontainer/dsh-cordis.patch.yml`（削除） | 除外 | 同上。移植先の既存のファイルも撤去した | #18 |
| なし | `.devcontainer/dsh-settings.yaml`（削除） | 除外 | 移植先にだけあった dsh の雛形 | #18 |
| `.devcontainer/install_beforehand.bash` の dsh 0.2.0 系の導入（pi-tui の profile、managed block、ランチャーの配置）、Grok Build の導入、`skills add` の `-a grok` | 同じファイルの dsh 0.1.5 の導入と定数、書き込みの確認のリストの `.grok`・`.dsh` | 除外 | 移植元の手順は持ち込まず、移植先の手順も撤去した | #18 |
| `.devcontainer/devcontainer.json` の `.grok`・`.dsh` の mount、`pnpmVersion` の固定、`forwardPorts` の `3080` | 同じファイルの同じ箇所 | 適応 | 撤去し、pnpm は `"none"` にした。`name`・dotnet・`remoteEnv`・秘密情報の mount・`--network=host` の差分は、移植先が新しいので保つ | #18 |
| `.devcontainer/initialize.bash` の `.grok`・`.dsh` | 同じ | 適応 | 撤去した。他の差分は移植先が新しいので保つ | #18 |
| `.devcontainer/zshrc.txt` の `grok update`、`cc_launcher_unsets` | 同じファイルの `ccda`、`MAAS_ANTHROPIC_TOKEN`、`grok update`、コメント | 除外 | 撤去した。移植元も `ccda` を撤去済み | #18 |
| `.devcontainer/README.md` の dsh・Grok Build の記述 | 同じファイルの dsh の節、ツールの表、読み込みの制約、秘密情報 | 適応 | 案内を撤去し、既存環境向けの注記を足した | #18 |
| `.devcontainer/docs/herdr-session-cwd-restore.md` | 同じ | 適応 | grok の例を外した。maatlog 固有のパスは移植先で汎用化済みなので保つ | #18 |
| なし | `AGENTS.md`・`README.md` の対象エージェントの一覧 | 適応 | 一覧から dsh を外した | #18 |
| `.devcontainer/test-herdr-migration.bash` の `ccda` の検査 | 同じファイル | 適応 | `ccda` の検査を外し、再混入の検査を足した。here-string などの差分は移植先が新しいので保つ | #18 |
| なし | `.devcontainer/test-initialize-mounts.bash`・`.devcontainer/test-readme.bash`・`.devcontainer/test-shell-tools.bash`・`tests/scripts/test-docs.bash` | 適応 | 除外したものを必須にしていた検査を新しい方針に合わせ、再混入の検査を足した | #18 |

### Dev Container・シェル・文書の共有ファイル

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の Codex・Cursor・Devin・uv・Starship・Herdr・共有スキル（herdr / find-skills）の導入と、`pi-subagents` から `@teelicht/pi-superagents` への置き換え | 同じファイルの同じ手順 | 既存維持 | 移植先の手順で足りる。`pi-subagents` の置き換えは移植元と同等（差分はコメントの Issue 番号だけ） | #22 |
| `.devcontainer/install_beforehand.bash` の `public` の checkout、Gitleaks と Playwright の導入 | なし | 対象外 | MaatLog の公開アプリケーションと検証のための手順 | #22 |
| なし | `.devcontainer/install_beforehand.bash` の ResoLoop の導入と Resonite のツールの確認 | 既存維持 | 移植先にだけある手順 | #22 |
| `.devcontainer/zshrc.txt` の Cursor と Devin の alias（`cur`・`curo`・`dev`・`devo`・`devs` のモデルの固定） | 同じファイルの `cur`・`dev` | 対象外 | #17 の実行ボードで、Cursor と Devin の alias はどの子も変えないと決めた | #17 |
| `.devcontainer/zshrc.txt` の `maatlog_periodic_cleanup` と `update()` | 同じファイルの `workspace_periodic_cleanup` と `update()` | 既存維持 | 移植先は定期の掃除を汎用化し、`update()` は無いツールを飛ばす `update_if_present` を使う。`grok update` の撤去は #18 | #22 |
| なし | `.devcontainer/zshrc.txt` の `require_command`・`update_if_present`、秘密情報の `env` の読み込み、.NET のツールの PATH | 既存維持 | 移植先にだけある補助 | #22 |
| `.devcontainer/cleanup-workspace.bash` | 同じ | 既存維持 | 移植先は汎用化した版（`WORKSPACE_CLEANUP_*`）。移植元の版は対象外のレビュー系ツールの reaper CLI に依存する | #22 |
| `.devcontainer/herdr-agent-task.bash`・`.devcontainer/herdr-git-status.bash`・`.devcontainer/herdr-status-updater.bash`・`.devcontainer/herdr.toml` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.devcontainer/test-herdr-agent-task.bash`・`.devcontainer/test-herdr-status.bash` | 同じ | 既存維持 | 移植先が新しい（here-string で SIGPIPE を避ける） | #22 |
| `.devcontainer/starship.toml` | 同じ | 既存維持 | 移植先は cwd から上へ最寄りの `.venv` を探し、ワールドごとの `.venv` に対応する。移植元はリポジトリのルートの `.venv` だけを見る | #22 |
| `.cursor/rules/shell-env-hygiene.mdc` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.gitignore` | 同じ | 既存維持 | 移植先の追跡の方針（2026-09-26 の再設計の 4.4 節）を保つ。`docs_draft/`・`/.worktrees/`・`/.claude/worktrees/` は移植先にもある。MaatLog と Node.js 向けの除外は持ち込まない | #22 |
| `.devcontainer/README.md` の pi の「API トークン」 | 同じファイルの「秘密情報」「API トークン」と新設の「既存環境の更新」 | 適応 | #18〜#21 の変更に合わせて、変数の説明と既存環境の手順をまとめた | #22 |
| `.devcontainer/README.md` の「Codex で `CLAUDE.md` を指示ファイルとして読む」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 同じファイルの「エージェントの読み込みの制約」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 既存維持 | 移植先の Codex は `AGENTS.md` を直接読むので、fallback の設定は不要と説明している。Herdr と導入の節は移植先の構成（9 本のランチャー、5 つのプラグイン）で書いてある | #22 |
| `.devcontainer/README.md` の「pi のモデル定義とランチャー」「モデル定義の正」 | 同じファイルの同じ節 | 既存維持 | 差分は setup スクリプトのパス（移植先は `.devcontainer/` に置く）と、移植先にだけある `pigou` の説明だけ | #22 |
| `.devcontainer/README.md` の「public/ checkout の検査と復旧」「npm への一本化（#147）と既存環境の移行」 | なし | 対象外 | MaatLog の `public/` submodule と、yarn からの移行の手順 | #22 |
| `.devcontainer/README.md` の「PR レビューの一括起動（herdr-pr-review）」 | なし | 対象外 | レビュー系ツール | #17 |
| `README.md` | `README.md` | 対象外 | 移植元の README は MaatLog の開発ワークスペースの説明で、エージェントの設定を含まない。移植先の README の更新は下の行と #18 の行 | #22 |
| なし | `README.md` の ResoLoop の版の説明 | 適応（PR #27 のレビュー修正） | ResoLoop の導入の説明を `.devcontainer/resoloop.lock` の nuget / fork モードに合わせた | #19 |
| なし | `README.md` の「構成」「エージェントで作業する」「対象外」 | 適応 | この比較表への参照と、pi の project trust の注意を足した | #22 |
| なし | `docs/maatlog-poc-porting.md`（この文書） | 適応 | #17 の比較表と rebuild での確認の記録 | #22 |
| なし | `tests/skills/test_legacy_references.py` の `EXCLUDED` | 適応 | この文書は移植元の全ファイルを載せる移行の記録なので、追跡ファイルに移植元の名前を禁じるガードの例外にした。設計記録（`docs/superpowers`）と同じ扱い | #22 |

### 対象外: スキル・レビュー系ツール・pi の Context7

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.agents/skills/**`（85 件。agent-handoff、find-docs、herdr-agent-task、monitoring-long-tasks、pi-model-name、planning-parallel-issues、pr-review、pr-review-fix-loop、repo-cleanup-after-merge、repository-ownership、review-fix-planning、simplify-in-subagent、version-export） | `.agents/skills/` | 対象外 | スキルは移植・統合しない。移植先の現在の内容と `.claude/skills/` の symlink の構成を保つ | #17 |
| `.claude/skills/**`（109 件。agent-handoff、herdr-agent-task、monitoring-long-tasks、planning-parallel-issues、pr-review、pr-review-fix-loop、python-extension-docs、repo-cleanup-after-merge、repository-ownership、review-fix-planning、rst-writer、version-export） | `.claude/skills/` | 対象外 | 同上 | #17 |
| `.agents/monitoring-runtimes.md` | 同じ | 対象外 | スキルが参照する文書。移植先の内容を保つ | #17 |
| `.agents/review-records.md`・`.agents/scripts/**`（4 件。`agent_tmp.py`・`review_records.py` とそのテスト） | なし | 対象外 | レビュー系ツール | #17 |
| `.devcontainer/herdr-pr-review.bash`・`.devcontainer/herdr-pr-review-launch.bash`・`.devcontainer/herdr-pr-review.toml` | なし | 対象外 | レビュー系ツール | #17 |
| `tools/__init__.py`・`tools/herdr_pr_review/**`（116 件）・`tools/review_triage/**`（37 件）・`tools/devenv/**`（3 件）・`tools/devenv_migration/**`（16 件）・`tools/test_support/**`（10 件） | なし | 対象外 | レビュー系ツールとその支援 | #17 |
| `.devcontainer/install_beforehand.bash` の `npm:@upstash/context7-pi` の導入、`.pi/mcp.json` の `context7` | なし | 対象外 | pi の Context7 は持ち込まない。移植先の `cleanup_pi_mcp.py` による `@upstash/context7-pi` の撤去は続ける。Claude Code・Codex・Cursor の Context7 と `find-docs` は変えない | #17 |

### 対象外: MaatLog 固有・他のエージェント

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.gitmodules`・`public` | なし | 対象外 | MaatLog の `public/` submodule（公開アプリケーション） | #17 |
| `.github/workflows/ci.yml`・`scripts/ci/verify-devenv.sh` | なし（移植先は自分の `.github/workflows/ci.yml` を持つ） | 対象外 | MaatLog の CI と検証の入口 | #17 |
| `.cursor/rules/repository-ownership.mdc` | なし | 対象外 | Cursor の設定で、MaatLog の親子リポジトリの規約 | #17 |
| `.codex/.gitkeep` | なし（移植先は `.codex/config.toml` を持つ） | 対象外 | standalone Codex の新しい設定は #17 の範囲外 | #17 |
| `.devin/skills/**`（3 件。pr-review、simplify-in-subagent） | なし | 対象外 | Devin の設定とスキル | #17 |
| `opencode.json` | なし | 対象外 | OpenCode CLI の設定（Superpowers のプラグインと pyright の LSP）。移植先は OpenCode CLI を導入しない。`ccdu` と `pigo` などは OpenCode Go の API を使うが、この設定は使わない | #22 |
| `scripts/add_pi_skills_setting.py` | なし | 除外 | pi は `.agents/skills` を cwd から git のルートまで自動で読むので不要。`~/.pi/agent/settings.json` に `.claude/skills` の絶対パスを足すと、ホストと共有する `~/.pi` を通じて他のワークスペースの pi にも効く。スキルの読み込みは #17 で対象外 | #22 |

## 網羅の確認

移植元のファイルがすべていずれかの行に当たることを、次の方法で確かめた（#22 の Plan の一時スクリプト）。

1. GitHub の API で移植元 `1f2aadb` のツリーを取得し、ファイル（blob）と submodule（gitlink）のパスを列挙する
2. 上の比較表の「移植元のパス」の列から、バッククォートで囲んだパスを取り出す。`**` で終わるものはそのディレクトリの配下全体、それ以外は完全一致として扱う
3. 移植元の全パスが、いずれかの行に当たることを確かめる
4. 表に書いたパス（`**` を除く）が、移植元に存在することを確かめる
5. 判断の列が 5 つの区分のどれかで、担当 Issue の列が #17〜#22 のどれかであることを確かめる

結果（2026-10-05）: 移植元の 456 件（blob 455 件、gitlink 1 件）がすべていずれかの行に当たり、表の移植元のパスはすべて移植元に存在した。判断と担当 Issue の列もすべて定めた値だった。

## 指示文・MCP の読み込み

リポジトリのルートと 4 つのワールド（`MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/`）を cwd にしたときに読まれるものは次のとおり。

| エージェント | 指示文 | スキル | プロジェクトの設定・MCP |
| --- | --- | --- | --- |
| Claude Code | `CLAUDE.md` を cwd から祖先まで読む。ルートとワールドの `CLAUDE.md` は `@AGENTS.md` で同じ階層の `AGENTS.md` を読み込む | `.claude/skills` を cwd から git のルートまで読む。ルートの `.claude/skills/<name>` は `.agents/skills/<name>` への symlink | `.mcp.json`（Context7、Google Developer Knowledge）は git のルートで解決する。ワールドの `.claude/settings.json` はルートの設定への symlink |
| pi | `AGENTS.md` を cwd から祖先まで読む | `.agents/skills` を cwd から git のルートまで読む | `.pi/settings.json`（`+builtin:mcp`）・`.pi/mcp.json`（Google Developer Knowledge）・`.pi/APPEND_SYSTEM.md` は cwd の直下だけを読む。ワールドは `.pi -> ../.pi` で同じ設定を読む。project trust が必要 |
| Codex | `AGENTS.md` を git のルートから cwd まで読む | `.agents/skills` を cwd から git のルートまで読む | `.codex/config.toml`（`context7_stdio`）は、プロジェクトを trust したときだけ読む |

確かめた方法（2026-10-05、`01affb7` の後の作業ブランチ）:

- `bash scripts/check-layout.sh` がワールドの `.pi -> ../.pi`、`.claude/settings.json` の symlink、`.claude/skills/` の symlink を検査し、PASS した
- `tests/scripts/test-instructions.bash`・`tests/scripts/test-agent-config.bash`・`.devcontainer/tests/test_pi_mcp_cleanup.py`（ルートと各ワールドの cwd から `.pi/settings.json`・`.pi/mcp.json` を読む検査を含む）が PASS した
- 各ワールドで `.pi`・`.claude/settings.json` の解決先と `CLAUDE.md` の内容を静的に確かめた
- 実際の CLI での読み込みは project trust の承認が要るので、rebuild 後の確認の R-11 で確かめる

## rebuild での確認

### 手順

1. ホストの作業ツリー（`/workspaces/reso-world`）を最新の `origin/main` に追従させる。rebuild は作業ツリーの `.devcontainer/` を使う。#22 の PR は文書だけを変えるので、`origin/main`（`01affb7` 以降）で rebuild すれば、移植の結果を確かめられる
2. `.devcontainer/README.md` の「既存環境の更新」に従って、ホストの `~/.config/create-reso-world/env` を見直す
3. VS Code で Dev Containers: Rebuild Container を実行する
4. 下の表の「確認方法」を実行し、「rebuild 後」の列に結果を書く。R-6 の `cleanup_pi_mcp.py` の再実行、R-8、R-11 は利用者の設定を変える操作や対話の承認を含むので、利用者が行うか、利用者の了承を得てから行う

### 確認項目と記録

「rebuild 前」は、移植前の `main` から作られたコンテナで 2026-10-05 に読み取り専用のコマンドで確かめた値である。認証情報の値は記録しない。確認方法のコマンドも値を表示しない（R-4 は変数名だけを出す）。

| 番号 | 確認項目 | 確認方法 | 期待する結果 | rebuild 前（2026-10-05） | rebuild 後 |
| --- | --- | --- | --- | --- | --- |
| R-1 | postCreate が全手順を完了する | Dev Containers のログ（postCreateCommand の出力） | `[install_beforehand] [25/25] Installing Herdr` まで進み、エラーで止まっていない | （記録なし） | 未記録 |
| R-2 | mount が 12 件で、dsh と Grok Build の mount が無い | `findmnt -rn -o TARGET \| grep -c '^/home/vscode'`、`findmnt -rn -o TARGET \| grep -E '/\.(dsh\|grok)$'` | 12 件、`.dsh`・`.grok` は無い | 14 件。`~/.dsh`・`~/.grok` がある | 未記録 |
| R-3 | dsh・Grok Build が無く、pnpm を npm で導入せず、転送するポートは 8000 だけ | `command -v dsh grok`、`npm ls -g --depth=0 pnpm`、`readlink -f "$(command -v pnpm)"`、VS Code の「ポート」 | `dsh`・`grok` は無い。npm の大域パッケージに `pnpm` が無い（`(empty)`）。Node の feature が `corepack enable` で置く `pnpm` の shim は残ってよい（`readlink -f` が `corepack/dist/pnpm.js` を指す）。3080 は転送しない | `dsh` がある。`grok` は無い。`pnpm` は npm の大域パッケージ（`pnpm@12.4.1`） | 未記録 |
| R-4 | 廃止した環境変数が新しいシェルに無い | `zsh -ic 'env' 2>/dev/null \| grep -oE '^(PI_DISTILL_[A-Z_]+\|PI_EXTENSIONS_LOCALE\|MAAS_ANTHROPIC_TOKEN)='` | 何も出ない（`MAAS_ANTHROPIC_TOKEN` は `env` から消した場合）。残っていれば変数名だけが出て、値は出ない | `PI_DISTILL_*` の 3 つ、`PI_EXTENSIONS_LOCALE`、`MAAS_ANTHROPIC_TOKEN` がある | 未記録 |
| R-5 | 撤去した拡張が残らず、設定とモデルが残る | `pi list`、`jq '.dependencies' ~/.pi/agent/npm/package.json`、`jq '.extensions' ~/.pi/agent/settings.json`、`jq '.providers \| keys' ~/.pi/agent/models.json` | `pi-mcp-adapter`・`@upstash/context7-pi`・`pi-distill`・`pi-extensions-tool-display`・`pi-extensions-i18n` が無い。`extensions` に `-builtin:mcp` が無い。provider は rebuild 前と同じ | `@upstash/context7-pi` が登録され、npm マニフェストにもある。`extensions` は空。provider は `commandcode`・`deepinfra`・`deepinfra-distill`・`opencode-go` | 未記録 |
| R-6 | バックアップは変更が必要なときだけ作られる | `ls -d ~/.pi/agent/migration-backups/pi-retired-*`、続けて `uv run --no-project .devcontainer/cleanup_pi_mcp.py` を再実行して同じ一覧を見る | rebuild で 1 つ作られ（rebuild 前に `@upstash/context7-pi` があるため）、再実行では増えない | `migration-backups` は無い | 未記録 |
| R-7 | 全ランチャーが `--tui-mode regular` で起動し、追加の指定が後ろに残る | `for l in pigo pigod pigou piccg piccd piga pigs pigl pixg; do PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 $l --tui-mode fullscreen; done`。dry-run でも、argv を出す前に各ランチャーの前提を確かめる: `piga`・`pigs`・`pigl` は Codex OAuth、`pixg` は xAI OAuth（どちらも `~/.pi/agent/auth.json`）、`piccg`・`piccd` は `COMMANDCODE_API_KEY` と `models.json` の commandcode の定義（`piccd` は DeepSeek のモデルも）、`pigou` は `models.json` の `union-alpha` の定義。9 本に共通の `bwrap`・共通ヘルパ・ランチャー別の設定は rebuild で配置される | 前提がそろったランチャーは、pi の引数の先頭に `--tui-mode`・`regular` があり、後ろに `--tui-mode`・`fullscreen` が残る。前提が無いランチャーは案内を出して終了するので、「前提が未設定のため未確認」と記録する | `pigo`・`pigs`・`pixg` の 3 本で確かめ、ヘルパが付ける `--tui-mode regular` が無い（`--tui-mode` は利用者が渡した 1 つだけ） | 未記録 |
| R-8 | `pigs`・`pixg` の tier がリポジトリの値になる | `zsh .devcontainer/setup_pi_superagents.zsh` の後に `jq -cS .superagents.modelTiers ~/.pi/agent/extensions/subagent.d/pigs/config.json` と `.devcontainer/pi-superagents/pigs.json` を比べる（`pixg` も同じ） | 一致する。変更があった設定はバックアップされる | すでに一致している（ホストと共有する `~/.pi` を別の環境で更新済みと考えられる） | 未記録 |
| R-9 | Claude Code のランチャーがそろい、`ccda` が無い | `zsh -ic 'alias ccd ccdo ccds; whence -w ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union ccda claude-alibaba'` | 3 つの alias と 6 つの関数がある。`ccda`・`claude-alibaba` は無い | alias は `ccd` だけ。`ccda`・`claude-alibaba` がある | 未記録 |
| R-10 | Claude Code のプラグインが宣言と一致する | `claude plugin list` | `example-skills`・`feature-dev`・`ripgrep`・`superpowers`・`web-quality-skills` がある | 5 つともある | 未記録 |
| R-11 | pi がルートとワールドでプロジェクトの設定を読む | ルートと `slum02/` で素の `pi` を起動し、project trust を承認してから `/mcp` を開く | `google-dev-knowledge` が表示される（キーが無ければ接続のエラーを 1 回通知する） | 未確認 | 未記録 |
| R-12 | テスト一式が通る | `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest tests/skills .agents/skills` | すべて成功する | PASS、27/27、516 passed・1 skipped（`01affb7` の worktree） | 未記録 |

### 実認証のスモークテスト（別枠）

次は実際の認証と provider への接続が要るので、この記録の対象外とし、未検証である。

- pi の 9 ランチャーの起動と応答（OpenCode Go、Command Code、ChatGPT Pro の Codex OAuth、xAI OAuth）
- pi-superagents の子 Pi の tier ごとの起動
- `ccdd`・`ccdd --model fable`・`ccddg`（DeepInfra）と `ccdu`（OpenCode Go）
- pi と Claude Code の Google Developer Knowledge の MCP の接続
