# maatlog-poc からの移植の比較表

[usaturn/maatlog-poc](https://github.com/usaturn/maatlog-poc) の pi と Claude Code の設定を、このリポジトリへ移植したときの記録である（Issue #17、子 Issue #18〜#22）。移植元の全ファイルについて、移植したか、移植先に合わせて変えたか、持ち込まなかったかを、理由と担当 Issue とともに残す。

pi の部分は後に Issue #125（2026-10-17）で usaturn/agent-workspace の `715d98168ab60011a98a42476ffea2759d4866d7` を基に置き換えた。下表の #125 の行が現在の判断であり、#17〜#22 の過去の Spec と rebuild の観測結果は履歴として残す。

Context7 の扱いは、さらに Issue #162（2026-10-18）で変えた。Context7 は `find-docs` スキルから、postCreate が固定した版で入れる `ctx7` CLI だけで使う。MCP の `context7`（`.mcp.json`・`.pi/mcp.json`）を外し、`.codex/config.toml` と `.cursor/mcp.json` を消した。context7-pi は導入をやめ、`.pi/settings.json` で読み込みを止めたが、共有の `~/.pi` の登録は消さない。下表の Context7 に触れる #125 の行には、理由の列に #162 の変更を追記した。「指示文・MCP の読み込み」の表は 2026-10-05 の確認の記録で、書き換えていない。

#243 で DSH 担当と導入を撤去したため、専用の比較行・確認手順を外した。#18・#151・#209 の詳細と当時の記録は Git の履歴を参照する。

利用者が参照する現在の手順は `README.md` と `.devcontainer/README.md` にある。既存の環境への反映は `.devcontainer/README.md` の「既存環境の更新」を参照する。

## 基準

- 移植元: usaturn/maatlog-poc の [`1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a`](https://github.com/usaturn/maatlog-poc/tree/1f2aadb864cb03e674ba96b0b2fbbd103caa1a6a)。ファイル（blob）455 件と submodule 1 件（`public`）
- 移植先: このリポジトリの `main`。比較を始めた時点は `9699e94`、#18〜#21 の変更がそろった時点は `01affb7`
- 移植元の `main` は 2026-10-05 02:55 UTC 時点で `e1f042e` に進んでいる。追加の 17 コミットで変わった 28 ファイルは、レビュー系ツール（`tools/herdr_pr_review/**`・`pr-review-fix-loop`・`.devcontainer/herdr-pr-review.toml`）、`.devcontainer/README.md` のその説明、`CLAUDE.md` の「正本」の言い換えの規則だけである。最後のものは、このリポジトリの `AGENTS.md` に同じ文がある。どれも取り込まない

## 判断の区分

| 判断 | 意味 |
| --- | --- |
| 移植 | 移植元の内容（撤去を含む）を、そのまま取り込んだ |
| 適応 | 移植元の方針を、移植先の構成（配置、ランチャー、安全策など）に合わせて取り込んだ |
| 既存維持 | 移植先の現状を保った。移植元と同一、移植先の方が新しい、移植先にだけある、のいずれか |
| 除外 | 検討して持ち込まなかった。#17 の除外項目と、各子 Issue が採用しなかったもの |
| 対象外 | 比較の範囲外とした。#17 の「対象外とした項目」（スキル、レビュー系ツール、pi の Context7）、MaatLog 固有のもの、pi と Claude Code 以外のエージェントとツール |

## 読み方

- パスはリポジトリのルートからの相対パスで書く。`**` はそのディレクトリの配下の全ファイルを表す
- 移植元のパスが「なし」の行は、移植先にだけあるファイルや変更である
- 移植元のパスの列で移植元の見出しを「」で引くときは、見出しの中のバッククォートを省く（`public/` などを含む見出し）。下の「網羅の確認」が、この列のバッククォートの中をパスとして読むため
- 1 つのファイルを節ごとに別の子 Issue が担当した場合は、節ごとに行を分けた
- 担当 Issue は、その判断を記録した Issue である。#17 の本文で範囲外と決めた項目は #17 とした
- 移植の後に判断を見直した行は、見直した Issue を担当 Issue に書く（pi は #125、Cursor と Devin の alias は #114）。下の「網羅の確認」の結果は、見直す前の 2026-10-05 の時点のものである
- 子 Issue の Spec が別の表記（「削除」「不採用」など）を使った行は、判断の後ろに括弧でその表記を残した。表記を揃えただけで、判断は変えていない
- 各子 Issue の判断の詳細は、その Spec にある: #18 `docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md`、#19 `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`、#20 `docs/superpowers/specs/2026-10-04-issue-20-pi-launchers-design.md`、#21 `docs/superpowers/specs/2026-10-04-issue-21-claude-code-design.md`、#22 `docs/superpowers/specs/2026-10-05-issue-22-integration-design.md`

## 比較表

### pi 本体・拡張・MCP

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の pi の導入、旧拡張の撤去（`Removing npm:pi-mcp-adapter`・`Removing npm:pi-distill`）、拡張の導入、`models.json` の配置 | 同じファイルの pi 節 | 移植 | agent-workspace の pi 節を採用。context7-pi と Plannotator を導入・保持し、旧 adapter・distill・lens を撤去する。独自 cleanup と撤去前バックアップを廃止。非 pi の節は保持する。後に #162 で context7-pi の導入をやめた（登録は消さない） | #125 |
| なし | `.devcontainer/cleanup_pi_mcp.py`（削除） | 適応 | 独自 cleanup を削除し、agent-workspace の導入節で撤去する。context7-pi は撤去しない | #125 |
| なし | `.devcontainer/pi_json.py`（削除） | 適応 | 独自 JSON helper と setup の事前検査を削除し、agent-workspace の setup にそろえる | #125 |
| なし | `.devcontainer/tests/fake_pi_packages.py`（削除） | 適応 | 旧 cleanup と一緒に削除。共有登録の保持は tools/devenv_migration/tests/test_pi_shared_packages.py で実行検査する | #125 |
| なし | 旧テスト2本（削除） | 適応 | agent-workspace の MCP 移行・Vertex の pytest に置換。入口は .devcontainer/test-pi-migrations.bash | #125 |
| なし | `.devcontainer/setup_pi_tool_display.py`（削除） | 適応（#19: 削除） | 廃止した拡張への調整を行わない。移植元は pi-distill の廃止とともにこの調整を持たない | #19 |
| `scripts/setup_pi.zsh` | `scripts/setup_pi.zsh` | 移植 | 配置を scripts/ に移し、agent-workspace と同じ内容にする。旧 .devcontainer/ に残す判断を変更した | #125 |
| `.devcontainer/pi-models.json` | 同じ | 移植 | agent-workspace と同じ定義にし、雛形から union-alpha を除く。利用者の既存 models.json は上書きしない | #125 |
| `.devcontainer/zshrc.txt` の pi の環境変数 | 同じファイルの同じ箇所 | 適応 | `PI_EXTENSIONS_LOCALE` と `PI_DISTILL_*` の設定と説明を削除した。ランチャーと `update()` は保つ | #19 |
| `.pi/settings.json` | 同じ | 適応（#19: 新規・適応） | `extensions` を `["+builtin:mcp"]` にした。移植元にある MaatLog 専用の `version-export` の skills は含めない | #19 |
| `.pi/mcp.json` | 同じ | 移植 | agent-workspace と同じ。context7 と Google Developer Knowledge の設定を使う。後に #162 で context7 を外した | #125 |
| `.pi-lens.json` | 同じ | 既存維持 | 移植先の ignore（`tmp`・`.venv`・`artifacts`・`.resoloop`・`external`・`private`）は移植元を包含する | #19 |
| `.pi/APPEND_SYSTEM.md` | 同じ | 適応 | 現行 role API の説明を合わせ、ワールド cwd・handoff・persona・Superpowers 内での同期直列委譲というこの環境の制限を保持する | #125 |
| なし | `.devcontainer/test-install-beforehand.bash` | 適応 | cleanup の実行の順序と、廃止した helper が呼ばれないことを検査する | #19 |
| なし | `tests/scripts/test-agent-config.bash`・`tests/scripts/test-instructions.bash` | 適応（#19: 既存維持・適応） | agent-config の既存の検査は保ち、instructions に廃止した指示が無いことの検査を足した。共有の pi の設定とワールドの cwd の検査は cleanup のテストにまとめた | #19 |
| `.devcontainer/README.md` の pi の拡張・MCP・pi-distill の節（「pi-distill の撤去（#508）」「setup スクリプトを使う場面」） | 同じファイルの pi 節 | 適応 | agent-workspace の現在の撤去と共有拡張の保持へ更新。独自の自動バックアップは廃止し、利用者の古いバックアップとモデルは残す | #125 |

### pi のランチャー・モデル・サブエージェント

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/pi-superagents-exec.zsh` | 同じ | 移植 | agent-workspace と同一。setup の案内は scripts/。Vertex の ADC overlay と子への継承を含む | #125 |
| `.devcontainer/pi-superagents/pigs.json`・`.devcontainer/pi-superagents/pixg.json` | 同じ | 移植 | `cheap`（`pixg` は `balanced` も）を `opencode-go/deepseek-v4.1-flash` の `max` にした | #20 |
| `.devcontainer/pi-superagents/pigo.json`・`.devcontainer/pi-superagents/pigod.json`・`.devcontainer/pi-superagents/piccg.json`・`.devcontainer/pi-superagents/piccd.json`・`.devcontainer/pi-superagents/piga.json`・`.devcontainer/pi-superagents/pigl.json` | 同じ | 既存維持 | 移植元と同一 | #20 |
| なし | `.devcontainer/pi-superagents/pigou.json`（削除） | 適応 | 独自の pi ランチャー pigou を削除。Claude Code の ccdu は変更しない | #125 |
| `.devcontainer/pigs` | 同じ | 移植 | agent-workspace と同一。setup の案内も scripts/ に統一 | #125 |
| `.devcontainer/pixg` | 同じ | 移植 | agent-workspace と同一。setup の案内も scripts/ に統一 | #125 |
| `.devcontainer/pigo`・`.devcontainer/pigod`・`.devcontainer/piccg`・`.devcontainer/piccd`・`.devcontainer/piga`・`.devcontainer/pigl` | 同じ | 移植 | agent-workspace と同一。setup の案内も scripts/ に統一。pigemf・pigemp・pigema とその tier も追加 | #125 |
| なし | `.devcontainer/pigou`（削除） | 適応 | 独自ランチャーを削除。利用者の既存ファイルは自動削除しない | #125 |
| `scripts/setup_pi_superagents.zsh`・`scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `scripts/` の同名3ファイル | 移植 | 配置を scripts/ に移し、agent-workspace と同一。旧 .devcontainer/ 維持と pigou の保持を取り消す | #125 |
| `scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` | `scripts/` の同名2ファイル | 移植 | 独自 pi_json の検査・バックアップをやめ、agent-workspace の内容にそろえる | #125 |
| `.devcontainer/install_beforehand.bash` のランチャーの配置と `setup_pi_superagents.zsh --if-absent` の呼び出し | 同じファイルの同じ手順 | 移植 | 11本と共通ヘルパを配置し、scripts/setup_pi_superagents.zsh --if-absent を実行する | #125 |
| `.agents/sp-implementer.md` | 同じ | 既存維持 | 移植元と同一 | #20 |
| `.devcontainer/test-pi-superagents.bash` | 同じ | 適応 | agent-workspace の版を採用。削除ガードを適用し、設定値だけを転記したtierテストを省く。実行・構造検査を残す | #125 |
| `.devcontainer/test-pi-openai-codex.bash` | 同じ | 適応 | agent-workspace の版を採用し、削除ガードだけ適用 | #125 |
| `.devcontainer/README.md` の GPT-6・Grok 4.7・TUI モード・tier の節 | 同じファイルの pi 節 | 適応 | agent-workspace の構成へ統一。Vertex・Plannotator・新しい配置と検証入口を説明する | #125 |

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

### Grok Build・`ccda`

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の Grok Build の導入、`skills add` の `-a grok` | 同じファイルの Grok Build 関連の処理 | 除外 | #18 で旧手順を撤去した | #18 |
| `.devcontainer/devcontainer.json` の `.grok` の mount、`pnpmVersion` の固定、`forwardPorts` の `3080` | 同じファイルの同じ箇所 | 適応 | 撤去し、pnpm は `"none"` にした。`name`・dotnet・`remoteEnv`・秘密情報の mount・`--network=host` の差分は、移植先が新しいので保つ | #18 |
| `.devcontainer/initialize.bash` の `.grok` | 同じ | 適応 | 撤去した。他の差分は移植先が新しいので保つ | #18 |
| `.devcontainer/zshrc.txt` の `grok update`、`cc_launcher_unsets` | 同じファイルの `ccda`、`MAAS_ANTHROPIC_TOKEN`、`grok update`、コメント | 除外 | 撤去した。移植元も `ccda` を撤去済み | #18 |
| `.devcontainer/README.md` の Grok Build の記述 | 同じファイルのツールの表と導入説明 | 適応 | #18 で導入しない方針に更新 | #18 |
| `.devcontainer/docs/herdr-session-cwd-restore.md` | 同じ | 適応 | grok の例を外した。maatlog 固有のパスは移植先で汎用化済みなので保つ | #18 |
| `.devcontainer/test-herdr-migration.bash` の `ccda` の検査 | 同じファイル | 適応 | `ccda` の検査を外し、再混入の検査を足した。here-string などの差分は移植先が新しいので保つ | #18 |
| なし | `.devcontainer/test-initialize-mounts.bash`・`.devcontainer/test-readme.bash`・`.devcontainer/test-shell-tools.bash`・`tests/scripts/test-docs.bash` | 適応 | 除外したものを必須にしていた検査を新しい方針に合わせ、再混入の検査を足した | #18 |

### Dev Container・シェル・文書の共有ファイル

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.devcontainer/install_beforehand.bash` の Codex・Cursor・Devin・uv・Starship・Herdr・共有スキル（herdr / find-skills）の導入と、`pi-subagents` から `@teelicht/pi-superagents` への置き換え | 同じファイルの同じ手順 | 既存維持 | 移植先の手順で足りる。`pi-subagents` の置き換えは移植元と同等（差分はコメントの Issue 番号だけ） | #22 |
| `.devcontainer/install_beforehand.bash` の `~` 配下の書き込み可能なディレクトリの用意、apt の設定、基本パッケージとロケール、Herdr の補助スクリプトの配置、作業領域の掃除、`~/.zshrc` への連結 | 同じファイルの同じ手順 | 既存維持 | 移植先の手順で足りる。違いは、ディレクトリの一覧（除外したツールの保存先は #18 で撤去し、移植先は秘密情報の置き場 `~/.config/create-reso-world` を持つ）、移植先だけが導入する `blender`、基本パッケージの前の重複した `apt update`（移植先は直前の手順の 1 回だけ）、移植元だけが置くレビュー系ツールの herdr-pr-review（移植先は `cleanup-workspace.bash` を symlink ではなくコピーで置く）と、コメントの Issue 番号 | #22 |
| `.devcontainer/install_beforehand.bash` の `public` の checkout、Gitleaks と Playwright の導入 | なし | 対象外 | MaatLog の公開アプリケーションと検証のための手順 | #22 |
| なし | `.devcontainer/install_beforehand.bash` の ResoLoop の導入と Resonite のツールの確認 | 既存維持 | 移植先にだけある手順 | #22 |
| `.devcontainer/zshrc.txt` の Cursor と Devin の alias（`cur`・`curo`・`dev`・`devo`・`devs` のモデルの固定） | 同じファイルの `cur`・`curo`・`dev`・`devs`・`devo` | 移植 | usaturn/agent-workspace の `3bc4769`（#515 の定義）に合わせてモデルを固定し、`curo`・`devs`・`devo` を足した。#17 の実行ボードでは、どの子も変えないとして対象外にしていた | #114 |
| `.devcontainer/zshrc.txt` の `maatlog_periodic_cleanup` と `update()` | 同じファイルの `workspace_periodic_cleanup` と `update()` | 既存維持 | 移植先は定期の掃除を汎用化し、`update()` は無いツールを飛ばす `update_if_present` を使う。`grok update` の撤去は #18 | #22 |
| なし | `.devcontainer/zshrc.txt` の `require_command`・`update_if_present`、秘密情報の `env` の読み込み、.NET のツールの PATH | 既存維持 | 移植先にだけある補助 | #22 |
| `.devcontainer/zshrc.txt` のほかの行で扱わない設定（シェルの基本設定、PATH、git の alias、`genv`・`cod`・`buni`、`EDITOR`・`LANG`、Herdr の起動の関数、Starship の初期化） | 同じファイルの同じ箇所 | 既存維持 | 移植元と同じ。違いは、関数の `require_command` の呼び出し（移植先にだけある補助）と、bun の補完のパス（移植先は `$BUN_INSTALL` を使う）だけ | #22 |
| `.devcontainer/cleanup-workspace.bash` | 同じ | 既存維持 | 移植先は汎用化した版（`WORKSPACE_CLEANUP_*`）。移植元の版は対象外のレビュー系ツールの reaper CLI に依存する | #22 |
| `.devcontainer/herdr-agent-task.bash`・`.devcontainer/herdr-git-status.bash`・`.devcontainer/herdr-status-updater.bash`・`.devcontainer/herdr.toml` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.devcontainer/test-herdr-agent-task.bash`・`.devcontainer/test-herdr-status.bash` | 同じ | 既存維持 | 移植先が新しい（here-string で SIGPIPE を避ける）。コメントの言い換えは、移植元だけのコメントの言い換えの行で扱う | #22 |
| `.devcontainer/zshrc.txt`・`.devcontainer/test-herdr-migration.bash`・`.devcontainer/test-pi-superagents.bash`・`.devcontainer/test-herdr-agent-task.bash` のコメントの言い換え（「正本」を「基準」「元ファイル」に、「契約」を「仕様」にしたもの） | 同じファイル（コメントは変えない） | 除外 | 移植元は `AGENTS.md` の日本語表現の規則に合わせてコメントを言い換えた。これらのファイルは #22 の編集範囲外で、言い換えは動作に関わらないので取り込まない。移植先の `AGENTS.md` にも同じ規則があるので、言い換えはこれらのファイルを変える別の作業で行う | #22 |
| `.devcontainer/starship.toml` | 同じ | 既存維持 | 移植先は cwd から上へ最寄りの `.venv` を探し、ワールドごとの `.venv` に対応する。移植元はリポジトリのルートの `.venv` だけを見る | #22 |
| `.cursor/rules/shell-env-hygiene.mdc` | 同じ | 既存維持 | 移植元と同一 | #22 |
| `.gitignore` | 同じ | 既存維持 | 移植先の追跡の方針（2026-09-26 の再設計の 4.4 節）を保つ。`docs_draft/`・`/.worktrees/`・`/.claude/worktrees/` は移植先にもある。MaatLog と Node.js 向けの除外は持ち込まない | #22 |
| `.devcontainer/README.md` の pi の「API トークン」 | 同じファイルの「秘密情報」「API トークン」と新設の「既存環境の更新」 | 適応 | #18〜#21 の変更に合わせて、変数の説明と既存環境の手順をまとめた | #22 |
| `.devcontainer/README.md` の「Codex で CLAUDE.md を指示ファイルとして読む」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 同じファイルの「エージェントの読み込みの制約」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 既存維持 | 移植先の Codex は `AGENTS.md` を直接読むので、fallback の設定は不要と説明している。Herdr と導入の節は移植先の構成（9 本のランチャー、5 つのプラグイン）で書いてある | #22 |
| `.devcontainer/README.md` の「pi のモデル定義とランチャー」「モデル定義の正」 | 同じファイルの pi 節 | 適応 | scripts/ の setup と11本のlauncherへ統一。host network のため Plannotator は REMOTE=0 で loopback の空いているポートを使う。WSL の mirrored モードで bind を塞ぐため、固定範囲と forwardPorts は使わない | #125 |
| `.devcontainer/README.md` の冒頭の説明と「public/ checkout の検査と復旧」「npm への一本化（#147）と既存環境の移行」 | なし | 対象外 | MaatLog の親子リポジトリと `public/` submodule（Playwright の導入を含む）、yarn からの移行の手順 | #22 |
| `.devcontainer/README.md` の「PR レビューの一括起動（herdr-pr-review）」 | なし | 対象外 | レビュー系ツール | #17 |
| `README.md` | `README.md` | 対象外 | 移植元の README は MaatLog の開発ワークスペースの説明で、エージェントの設定を含まない。移植先の README の更新は下の行と #18 の行 | #22 |
| なし | `README.md` の ResoLoop の版の説明 | 適応（PR #27 のレビュー修正） | ResoLoop の導入の説明を `.devcontainer/resoloop.lock` の nuget / fork モードに合わせた | #19 |
| なし | `README.md` の「構成」「エージェントで作業する」「対象外」 | 適応 | この比較表への参照と、pi の project trust の注意を足した | #22 |
| なし | `docs/maatlog-poc-porting.md`（この文書） | 適応 | #17 の比較表と rebuild での確認の記録 | #22 |
| なし | `tests/skills/test_legacy_references.py` の `EXCLUDED` | 適応 | この文書は移植元の全ファイルを載せる移行の記録なので、追跡ファイルに移植元の名前を禁じるガードの例外にした。設計記録（`docs/superpowers`）と同じ扱い | #22 |

### スキル・レビュー系ツール・pi の Context7 の判断

| 移植元のパス | 移植先のパス | 判断 | 理由 | 担当 Issue |
| --- | --- | --- | --- | --- |
| `.agents/skills/**`（85 件。agent-handoff、find-docs、herdr-agent-task、monitoring-long-tasks、pi-model-name、planning-parallel-issues、pr-review、pr-review-fix-loop、repo-cleanup-after-merge、repository-ownership、review-fix-planning、simplify-in-subagent、version-export） | `.agents/skills/` | 対象外 | スキルは移植・統合しない。移植先の現在の内容と `.claude/skills/` の symlink の構成を保つ。後に #115（2026-10-17）で、`monitoring-long-tasks` を usaturn/agent-workspace の版を基に置き換えた（maatlog-poc の版ではない） | #17 |
| `.claude/skills/**`（109 件。agent-handoff、herdr-agent-task、monitoring-long-tasks、planning-parallel-issues、pr-review、pr-review-fix-loop、python-extension-docs、repo-cleanup-after-merge、repository-ownership、review-fix-planning、rst-writer、version-export） | `.claude/skills/` | 対象外 | 同上。後に #115（2026-10-17）で、`monitoring-long-tasks` を usaturn/agent-workspace の版を基に置き換えた（maatlog-poc の版ではない） | #17 |
| `.agents/monitoring-runtimes.md` | 同じ | 対象外 | スキルが参照する文書。移植先の内容を保つ。後に #115（2026-10-17）で、usaturn/agent-workspace の版を基に `task_watch.py` の節と pi の行を足した（maatlog-poc の版ではない） | #17 |
| `.agents/review-records.md`・`.agents/scripts/**`（4 件。`agent_tmp.py`・`review_records.py` とそのテスト） | なし | 対象外 | レビュー系ツール。後に #115（2026-10-17）で入れた `.agents/scripts/issue_budget.py` は usaturn/agent-workspace から取り入れたもので、この行の移植元のファイルとは別物 | #17 |
| `.devcontainer/herdr-pr-review.bash`・`.devcontainer/herdr-pr-review-launch.bash`・`.devcontainer/herdr-pr-review.toml` | なし | 対象外 | レビュー系ツール | #17 |
| `tools/__init__.py`・`tools/herdr_pr_review/**`（116 件）・`tools/review_triage/**`（37 件）・`tools/devenv/**`（3 件）・`tools/devenv_migration/**`（16 件）・`tools/test_support/**`（10 件） | なし | 対象外 | レビュー系ツールとその支援 | #17 |
| `.devcontainer/install_beforehand.bash` の `npm:@upstash/context7-pi` の導入、`.pi/mcp.json` の `context7` | 同じファイルと `.pi/mcp.json` | 移植 | #17 の対象外とする判断を変更し、context7-pi と MCP の context7 を導入・保持する。共有 ~/.pi の登録が消える問題を解消する。後に #162（2026-10-18）で、Context7 を `ctx7` CLI と `find-docs` に移し、context7-pi の導入と MCP の context7 を外した。共有 ~/.pi の登録は消さず、`.pi/settings.json` で読み込みを止める | #125 |

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

### PR #141 のレビュー修正による追加差分（2026-10-18）

`715d981` との初回比較の結果は上表の履歴として残す。以後、provider setup 3本は完全一致ではない。
`~` の解決・BOM の読み取り・失敗通知・mode と共有先の保護を、専用の
`.devcontainer/pi-provider-setup.py` へまとめた。旧 cleanup / pi_json は復活させていない。
Codex テストの隔離 helper と外側 pytest は、private `/tmp` の後に対象リポジトリを読み取り専用で
明示 mount し、`/tmp` の worktree でも同じ検証を行う。正常対照・拒否理由・副作用を確認する実行回帰を追加した。
判断と検証結果は Issue #125 の Spec の「PR #141 レビュー修正」に記録する。

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
| pi | `AGENTS.md` を cwd から祖先まで読む（project trust に関係なく読む） | `.agents/skills` を cwd から git のルートまで読む。project trust が必要 | `.pi/settings.json`（`+builtin:mcp`）・`.pi/mcp.json`（Google Developer Knowledge）・`.pi/APPEND_SYSTEM.md` は cwd の直下だけを読む。ワールドは `.pi -> ../.pi` で同じ設定を読む。project trust が必要 |
| Codex | `AGENTS.md` を git のルートから cwd まで読む | `.agents/skills` を cwd から git のルートまで読む | `.codex/config.toml`（`context7_stdio`）は、プロジェクトを trust したときだけ読む |

確かめた方法（2026-10-05、`01affb7` の後の作業ブランチ）:

- `bash scripts/check-layout.sh` がワールドの `.pi -> ../.pi`、`.claude/settings.json` の symlink、`.claude/skills/` の symlink を検査し、PASS した
- `tests/scripts/test-instructions.bash`・`tests/scripts/test-agent-config.bash`・`.devcontainer/tests/test_pi_mcp_cleanup.py`（ルートと各ワールドの cwd から `.pi/settings.json`・`.pi/mcp.json` を読む検査を含む）が PASS した
- 各ワールドで `.pi`・`.claude/settings.json` の解決先と `CLAUDE.md` の内容を静的に確かめた
- 実際の CLI での読み込みは project trust の承認が要るので、rebuild 後の確認の R-11 で確かめる

## rebuild での確認

### 手順

1. ホストの作業ツリー（`/workspaces/reso-world`）を最新の `origin/main` に追従させる。rebuild は作業ツリーの `.devcontainer/` を使う。#22 の PR は文書とテストの例外（`EXCLUDED` の 1 行とそのコメント）だけを変え、導入スクリプトと設定ファイルを変えないので、`origin/main`（`01affb7` 以降）で rebuild すれば、移植の結果を確かめられる
2. `.devcontainer/README.md` の「既存環境の更新」に従って、ホストの `~/.config/create-reso-world/env` を見直す
3. VS Code で Dev Containers: Rebuild Container を実行する
4. 下の表の各項目を「確認のコマンド」で確かめ、「rebuild 後」の列に結果を書く。R-8、R-11 は利用者の設定を変える操作や対話の承認を含むので、利用者が行うか、利用者の了承を得てから行う

### 確認項目と記録

「rebuild 前」は、移植前の `main` から作られたコンテナで 2026-10-05 に読み取り専用のコマンドで確かめた値である。「rebuild 後」は、`e21121e`（PR #33 のマージ後の `main`）で 2026-10-05 に rebuild したコンテナで確かめた値で、R-6・R-8 の設定を変えるコマンドは利用者の了承を得て実行した。認証情報の値は記録しない。「確認のコマンド」も値を表示しない（R-4 は変数名だけを出す）。

| 番号 | 確認項目 | 確認方法 | 期待する結果 | rebuild 前（2026-10-05） | rebuild 後 |
| --- | --- | --- | --- | --- | --- |
| R-1 | postCreate が全手順を完了する | Dev Containers のログ（postCreateCommand の出力） | `[install_beforehand] [25/25] Installing Herdr` まで進み、エラーで止まっていない | （記録なし） | 利用者が Dev Containers のログで、`[install_beforehand] [25/25] Installing Herdr` までエラーで止まらずに進んだことを確かめた。コンテナ内でも `herdr` が配置され、`herdr --version` は `herdr 0.9.3` を返す |
| R-3 | Grok Build・pnpm の追加導入・3080 は無し | `grok` のコマンド、npm の大域パッケージの `pnpm`、`pnpm` の実体（R-3 のコマンド）と、VS Code の「ポート」 | Grok Build は無し。npm の大域パッケージに pnpm は無い。corepack の pnpm shim は残ってよい。3080 は転送しない | `grok` は無い。`pnpm` は npm の大域パッケージ（`pnpm@12.4.1`） | `grok` は無い。npm の大域パッケージは `(empty)`。`pnpm` は `corepack/dist/pnpm.js` の shim。`forwardPorts` は `[8000]` で、3080 で待ち受けるプロセスは無い（VS Code の「ポート」の表示は見ていない） |
| R-4 | 廃止した環境変数が新しいシェルに無い | 新しいシェルの環境変数の名前（R-4 のコマンド。値は表示しない） | 何も出ない（`MAAS_ANTHROPIC_TOKEN` は `env` から消した場合）。残っていれば変数名だけが出て、値は出ない | `PI_DISTILL_*` の 3 つ、`PI_EXTENSIONS_LOCALE`、`MAAS_ANTHROPIC_TOKEN` がある | `MAAS_ANTHROPIC_TOKEN` だけが出る。利用者が rebuild の後に `~/.zshrc` の末尾へ手動で書き戻した `export` 行によるもので、リポジトリの設定からではない。`PI_DISTILL_*`・`PI_EXTENSIONS_LOCALE` は無い |
| R-5 | 撤去した拡張が残らず、設定とモデルが残る | `pi list --no-approve`（プロジェクトの trust を問わない）、pi 管理の npm マニフェストの依存、settings の `extensions`、`models.json` の provider（R-5 のコマンド） | `pi-mcp-adapter`・`@upstash/context7-pi`・`pi-distill`・`pi-extensions-tool-display`・`pi-extensions-i18n` が無い。`extensions` に `-builtin:mcp` が無い。provider は rebuild 前と同じ | `@upstash/context7-pi` が登録され、npm マニフェストにもある。`extensions` は空。provider は `commandcode`・`deepinfra`・`deepinfra-distill`・`opencode-go` | 5 つの拡張は `pi list` にも npm マニフェストにも無い。`extensions` は `[]`。provider は `commandcode`・`deepinfra`・`deepinfra-distill`・`opencode-go` で rebuild 前と同じ |
| R-6 | バックアップは変更が必要なときだけ作られる | バックアップの一覧を見て、cleanup を再実行してから同じ一覧を見る（R-6 のコマンド） | rebuild で 1 つ作られ（rebuild 前に `@upstash/context7-pi` があるため）、再実行では増えない | `migration-backups` は無い | rebuild で `pi-retired-u1wtbqna` が 1 つ作られ、cleanup の再実行（終了コード 0）では増えない |
| R-7 | 全ランチャーが `--tui-mode regular` で起動し、追加の指定が後ろに残る | 9 本のランチャーの dry-run（R-7 のコマンド）。dry-run でも、argv を出す前に各ランチャーの前提を確かめる: `piga`・`pigs`・`pigl` は Codex OAuth、`pixg` は xAI OAuth（どちらも `~/.pi/agent/auth.json`）、`piccg`・`piccd` は `COMMANDCODE_API_KEY` と `models.json` の commandcode の定義（`piccd` は DeepSeek のモデルも）、`pigou` は `models.json` の `union-alpha` の定義。9 本に共通の `bwrap`・共通ヘルパ・ランチャー別の設定は rebuild で配置される | 前提がそろったランチャーは、pi の引数の先頭に `--tui-mode`・`regular` があり、後ろに `--tui-mode`・`fullscreen` が残る。前提が無いランチャーは案内を出して終了するので、「前提が未設定のため未確認」と記録する | `pigo`・`pigs`・`pixg` の 3 本で確かめ、ヘルパが付ける `--tui-mode regular` が無い（`--tui-mode` は利用者が渡した 1 つだけ） | 前提がそろった 8 本（`pigo`・`pigod`・`piccg`・`piccd`・`piga`・`pigs`・`pigl`・`pixg`）は、pi の引数の先頭が `--tui-mode`・`regular`、末尾が `--tui-mode`・`fullscreen`。`pigou` は `models.json` に `union-alpha` が無いので案内を出して終了した（前提が未設定のため未確認） |
| R-8 | `pigs`・`pixg` の tier がリポジトリの値になる | setup を `--if-absent` なしで実行してから、`pigs`・`pixg` のランチャー別の設定の tier をリポジトリの値と比べる（R-8 のコマンド） | 一致する（差分が出ない）。変更があった設定はバックアップされる | すでに一致している（ホストと共有する `~/.pi` を別の環境で更新済みと考えられる） | setup の前も後も、`pigs`・`pixg` の tier はリポジトリの値と一致する。setup は `pigo`・`pigod`・`piccd`・`pigs`・`pixg` の設定を置き直し、元の設定を `config.json.bak.20261005-185053` に退避した。置き直しで消えたのは、pi-superagents の `default-config.json` と同じ値の `commands.sp-implement-parallel` と `makeSuperpowersSkillsOptInOnly` だけ |
| R-9 | Claude Code のランチャーがそろい、`ccda` が無い | Claude Code の alias と関数（R-9 のコマンド） | 3 つの alias と 6 つの関数がある。`ccda`・`claude-alibaba` は無い | alias は `ccd` だけ。`ccda`・`claude-alibaba` がある | alias は `ccd`・`ccdo`・`ccds`、関数は `ccdd`・`ccddg`・`ccdu`・`claude-deepinfra`・`claude-deepinfra-glm`・`claude-opencode-union`。`ccda`・`claude-alibaba` は `none` |
| R-10 | Claude Code のプラグインが宣言と一致する | `claude plugin list`（R-10 のコマンド） | `example-skills`・`feature-dev`・`ripgrep`・`superpowers`・`web-quality-skills` がある | 5 つともある | 5 つとも user のスコープで有効 |
| R-11 | pi がルートとワールドでプロジェクトの設定を読む | ルートと、ワールドの代表として `slum02/` で素の `pi` を起動し、project trust を承認してから `/mcp` を開く（4 つのワールドは同じ `.pi -> ../.pi` を持ち、R-12 の `check-layout.sh` が検査する） | `google-dev-knowledge` が表示される（キーが無ければ接続のエラーを 1 回通知する） | 未確認 | 素の `pi` の `/mcp` の代わりに、ルートと `slum02/` で `pi mcp list` を実行し、どちらも `google-dev-knowledge: connected, 3 tools (codemode, project)` を出した。`/workspaces/reso-world` は rebuild 前から `~/.pi/agent/trust.json` で trust 済みなので、承認の操作は無かった |
| R-12 | テスト一式が通る | リポジトリのルートでテスト一式を実行する（R-12 のコマンド） | すべて成功する | PASS、27/27、516 passed・1 skipped（`01affb7` の worktree） | PASS、27/27、516 passed・1 skipped（`test-instructions.bash` を直した後の `eb7c539` の worktree）。直す前の `e21121e` では、`test-instructions.bash` が失敗して 26/27 だった（PR #34 が AGENTS.md に `## GitHub Actions` の節を足したが、AGENTS.md の節の一覧を固定値と比べる検査が更新されていなかった。この検査は不要と判断して削除した）。親の checkout の pytest は、無視対象の `.agents/skills/repository-ownership/tests/__pycache__/` の残骸で 2 件失敗し、残骸を消すと通った |

### #125 以降の確認で変わる点

上の rebuild 表は 2026-10-05 の観測記録で、再検証結果ではない。#125 以降は R-5 で context7-pi と Plannotator の登録を保持し、R-6 の自動バックアップは作らない。R-7 は pigou を除く11本、R-11 は Context7 も確認する。現行の反映手順と未検証項目は `.devcontainer/README.md` と Issue #125 を参照する。以下のコマンドは現行の配置に更新し、削除済み cleanup は実行しない。

### 確認のコマンド

表のセルにはコマンドを書かない。表のセルでは `|` を `\|` と書く必要があり、Markdown のソースから写すとシェルが別のコマンドとして実行する（R-4 では環境変数の値がすべて表示される）。コマンドは次のブロックから写し、リポジトリのルートで実行する。R-4・R-9 は `zsh -i` で `~/.zshrc` を読むので、新しい端末を開いたときと同じく、24 時間に 1 回の作業領域の掃除（`cleanup-workspace.bash`）がバックグラウンドで動くことがある（利用者の設定は変えない）。

読み取り専用のコマンド（利用者の設定を変えない）:

```bash
# R-3
command -v grok
npm ls -g --depth=0 pnpm
readlink -f "$(command -v pnpm)"
# R-4（変数名だけを出し、値は出さない）
zsh -ic 'env' 2>/dev/null | grep -oE '^(PI_DISTILL_[A-Z_]+|PI_EXTENSIONS_LOCALE|MAAS_ANTHROPIC_TOKEN)='
# R-5（`--no-approve` は、プロジェクトの trust を決めていないときの確認を出さない）
pi list --no-approve
jq '.dependencies' ~/.pi/agent/npm/package.json
jq '.extensions' ~/.pi/agent/settings.json
jq '.providers | keys' ~/.pi/agent/models.json
# R-6（過去のバックアップの一覧だけ。#125 以降は自動作成しない）
ls -d ~/.pi/agent/migration-backups/pi-retired-*
# R-7
for l in pigo pigod piccg piccd piga pigs pigl pixg pigemf pigemp pigema; do PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 $l --tui-mode fullscreen; done
# R-9（標準入力を閉じる。端末から実行しても、`~/.zshrc` の末尾が herdr を起動しない）
zsh -ic 'alias ccd ccdo ccds; whence -w ccdd ccddg ccdu claude-deepinfra claude-deepinfra-glm claude-opencode-union ccda claude-alibaba' </dev/null
# R-10
claude plugin list
# R-12
bash scripts/check-layout.sh
bash .devcontainer/run-tests.bash
uv run pytest tests/skills .agents/skills
```

利用者の設定を変えるコマンド（利用者が行うか、利用者の了承を得てから実行する）:

```bash
# R-6: #125 で独自 cleanup を廃止したため再実行しない。過去の確認結果だけを上表に残す
# R-8: tier を置き直し、pigs と pixg の tier をリポジトリの値と比べる（一致すれば何も出ない）
zsh scripts/setup_pi_superagents.zsh
for l in pigs pixg; do diff <(jq -cS .superagents.modelTiers ~/.pi/agent/extensions/subagent.d/$l/config.json) <(jq -cS .superagents.modelTiers .devcontainer/pi-superagents/$l.json); done
```

### 実認証のスモークテスト（別枠）

次は実際の認証と provider への接続が要るので、この記録の対象外とし、未検証である。

- pi の 11 ランチャーの起動と応答（OpenCode Go、Command Code、ChatGPT Pro の Codex OAuth、xAI OAuth、Vertex ADC）
- Plannotator の Windows ブラウザーでの Plan 確認と承認／修正要求（#125）
- pi-superagents の子 Pi の tier ごとの起動
- `ccdd`・`ccdd --model fable`・`ccddg`（DeepInfra）と `ccdu`（OpenCode Go）
- Claude Code の Google Developer Knowledge の MCP の接続（pi の接続は R-11 の `pi mcp list` で確かめた）
