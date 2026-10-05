# Issue #22 移植の比較表・README の整合・rebuild での確認 設計

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象: Issue #22（親 #17。ボードのキー `issue17-maatlog-pi-claude-port`、子のキー `c5-integration`）。PR は Plan の Task 4 で作る
- 基準: 移植先は `main` の `01affb7`（#19〜#21 の PR #25・#26・#27 と PR #30 のマージ後。Issue 本文の基準 `9699e94` から進んでいる）。移植元は usaturn/maatlog-poc の `1f2aadb`（Issue の指定）。移植元の `main` は 2026-10-05 02:55 UTC 時点で `e1f042e` に進んでいるが、差分は 5 章の D-1 のとおり取り込まない
- 経路: brainstorming の written-spec 経路。変更は文書とテストの例外の 1 行（D-15）だけの bounded な作業だが、#17 の運用ルールが全ての子に Spec と Plan を求めているため、書面の Spec を作る
- 状態: draft
- 実行許可: 利用者の 2026-10-05 の指示「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」。この Spec の判断（5 章の D-1〜D-15）は、その指示に基づきエージェント（Claude Code、claude-opus-5-5）が推奨値で決めたもので、Spec 自体の明示承認は得ていない
- 関連 Plan: `docs/superpowers/plans/2026-10-05-issue-22-integration.md`
- レビュー修正: `docs/superpowers/specs/2026-10-05-pr33-issue-22-integration-review-fixes-design.md`（PR #33。この Spec を変えた修正もそこに記録した）
- 作成: 2026-10-05

## 1. 目的

#17 の移植全体について、移植元の基準コミットの全ファイルを対象にしたファイル別の比較表を `docs/maatlog-poc-porting.md` に残す。#18〜#21 の変更を前提に README の記述を全体で整え、既存環境向けの更新手順を 1 か所にまとめる。Dev Container の rebuild で確かめる項目と、rebuild 前の基準値を記録し、利用者の rebuild 後に結果を書き込める形にする。

## 2. 範囲

変更するファイル（`tests/skills/test_legacy_references.py` を除き、#22 の「編集してよいファイル」。テストの変更は D-15）:

- `docs/maatlog-poc-porting.md`（新規）: 比較表、網羅の確認、指示文・MCP の読み込み、rebuild での確認と記録
- `.devcontainer/README.md`: 「秘密情報」の変数の例、「API トークン」節、新設する「既存環境の更新」節。PR #33 のレビュー修正で、「Superpowers スキルの探索パス」配下の同名の `#####` の見出しを改名した（6 章）
- `README.md`: 「構成」の `docs/` の説明、「エージェントで作業する」の pi の項目、「対象外」の rebuild 後の確認の参照先
- `tests/skills/test_legacy_references.py`: 移植元の名前を禁じるガードの例外（`EXCLUDED`）に `docs/maatlog-poc-porting.md` を 1 行足す（D-15。実装中に分かった）
- この Spec と Plan

変更しないファイル:

- `docs/integration.md`。rebuild の確認項目は比較表と同じ文書に置く（D-7）
- `.devcontainer/run-tests.bash`・`scripts/check-layout.sh`・`.github/workflows/ci.yml`。統合で変更が必要になる箇所が無い
- 他の子から引き継いだコードの変更は無い。#18・#19・#20・#21 の Spec と Issue のコメントを確かめ、引き継ぎの記録があるのは README「API トークン」節の整合（#20 → #22）と rebuild での確認だけだった。`install_beforehand.bash` の `STEP_TOTAL` は 25 のまま（#19 の引き継ぎ）、#21 は #22 への変更依頼が無い

### 範囲外

- テストの追加と、上の例外の 1 行以外のテストの変更（`tests/**`・`.devcontainer/test-*.bash`）。#22 の編集範囲に無い。比較表の網羅は Plan の一時スクリプトで確かめ、結果を比較表に記録する（D-11）
- `.agents/skills/**`・`.claude/skills/**`・`.agents/monitoring-runtimes.md`、レビュー系ツール、ワールドのプロジェクト、ResoLoop の lock と導入・検証処理、`docs/superpowers/` の既存の文書、認証情報と個人設定
- 移植と関係しない README の記述の誤り。README の「変更の流れ」と `.devcontainer/README.md` の「テストの実行」は CI が push と PR のたびに走ると書いているが、2026-10-05 から GitHub Actions はリポジトリ全体で無効になっている（利用者の指示による一時的な設定の可能性がある）。README の「構成」とテストの例はワールドに `slum03/` を挙げていない。どちらも #17 の移植と無関係なので変えない（D-12）
- Dev Container の rebuild の実行と、実認証を伴う pi / Claude Code / サブエージェント / MCP のスモークテスト。rebuild は利用者が行い、この子は手順・確認項目・基準値を用意する

## 3. 現状

### 3.1 子の Spec の比較表の行

- #18（`2026-10-04-issue-18-remove-excluded-agents-design.md` 9 章）: 12 行。dsh・Grok Build・`ccda` の除外と、`devcontainer.json`・`initialize.bash`・`zshrc.txt`・README・テストの適応
- #19（`2026-10-04-issue-19-pi-migration-design.md`「ファイル別比較表（#22 の集約用）」）: 18 行。PR #27 のレビュー修正で足した `pi_json.py`・setup 2 本・ルート `README.md` の行を含む。移植元のパスの列が無く、移植先のパスだけを書いている
- #20（`2026-10-04-issue-20-pi-launchers-design.md` 9 章）: 13 行
- #21（`2026-10-04-issue-21-claude-code-design.md`「ファイル別比較と判断」）: 14 行
- レビュー修正の Spec（PR #24・#25・#26・#27）は、#19 の表に入った行を除き、比較表の行を足していない

子の表の判断の表記は揃っていない。「削除」（#19 の `setup_pi_tool_display.py`）、「新規・適応」「既存維持・適応」（#19）、「不採用 (D-2)」「既存維持・編集対象外」（#21）がある。

### 3.2 子の表に無い移植元のファイル

移植元 `1f2aadb` のツリーは blob 455 件と submodule（gitlink）1 件（`public`）。スキル（`.agents/skills/**` 85 件、`.claude/skills/**` 109 件）とレビュー系ツール（`tools/**` 183 件など）を除く 79 件を移植先と突き合わせた。子の表に無いのは次のファイルで、#22 が判断する（4.2 節）。

- `.agents/monitoring-runtimes.md`、`.agents/review-records.md`、`.agents/scripts/**`（4 件）
- `.codex/.gitkeep`、`.cursor/rules/repository-ownership.mdc`、`.cursor/rules/shell-env-hygiene.mdc`（移植先と同一）、`.devin/skills/**`（3 件）
- `.devcontainer/cleanup-workspace.bash`、`herdr-agent-task.bash`・`herdr-git-status.bash`・`herdr-status-updater.bash`・`herdr.toml`（4 件とも同一）、`herdr-pr-review.bash`・`herdr-pr-review-launch.bash`・`herdr-pr-review.toml`、`starship.toml`、`test-herdr-agent-task.bash`、`test-herdr-status.bash`
- `.github/workflows/ci.yml`、`.gitignore`、`.gitmodules`、`public`、`README.md`、`opencode.json`
- `scripts/add_pi_skills_setting.py`、`scripts/ci/verify-devenv.sh`、`tools/__init__.py`
- `install_beforehand.bash` と `zshrc.txt` のうち、どの子も扱っていない節（`public` の checkout、Gitleaks・Playwright の導入、Cursor / Devin のモデル固定の alias、移植先固有の補助関数など）

### 3.3 README の不整合

- `.devcontainer/README.md`「API トークン」節: `OPENCODE_API_KEY` の説明が `pigo`・`pigod`・`pigou` だけを挙げ、`pigs`・`pixg` の `cheap` tier（#20）と、環境変数が必須の `ccdu`（#21）に触れていない。`GOOGLE_DEV_KNOWLEDGE_API_KEY`（#19 の pi の組み込み MCP。Claude Code の `.mcp.json` も同じ変数を使う）、`DEEPINFRA_TOKEN` を使う `ccdd`・`ccddg`、旧名 `OPENCODE_GO_API_KEY` の扱いも無い
- 「秘密情報」節の変数の例に `GOOGLE_DEV_KNOWLEDGE_API_KEY` が無い
- 既存環境向けの手順が、`ccda`（「秘密情報」）、Claude Code（「Claude Code の起動と更新」）、pi の cleanup（「pi の旧拡張・MCP 設定の移行」）、`PI_DISTILL_*`（「組み込み MCP と廃止した拡張」）、ランチャーと tier（「pi の TUI モードと Herdr のスクロール履歴」）に分かれ、順序と、rebuild で自動的に変わるものと変わらないものの区別が無い
- ルート `README.md`「エージェントで作業する」は Codex・Cursor・Devin の初回の注意を書いているが、pi の project trust（`.pi/settings.json`・`.pi/mcp.json` を読むのに必要）が無い。「対象外」は rebuild 後の確認を `docs/integration.md`（2026-09 の再設計の手順）だけに案内している

### 3.4 検証の基準（`01affb7`、この worktree）

- `bash scripts/check-layout.sh`: PASS（#17 に記録された slum03 の既知の失敗は解消している）
- `bash .devcontainer/run-tests.bash`: 27 本すべて PASS
- `uv run pytest -q tests/skills .agents/skills`: 516 passed、1 skipped
- 旧構成への言及: `git grep` で、`docs/superpowers/`・スキル・ワールド・テストを除くと、`pi-distill`・`PI_DISTILL`・`context7-pi`・`ccda`・`dsh`・`grok update`・`scripts/setup_pi` などは `.devcontainer/README.md` の意図した注記と `cleanup_pi_mcp.py` の撤去対象の一覧にだけ残る

### 3.5 現行コンテナの状態（rebuild 前）

2026-10-05 03:00 UTC ごろ、このセッションのコンテナで読み取り専用のコマンドだけを使って確かめた。認証情報の値は表示していない。このコンテナは移植前の `main` から作られている。

- Pi 1.0.2、Claude Code 2.1.289。`dsh` が PATH にある（`grok` は無い）。`/home/vscode` 配下の mount は 14 件で、`~/.dsh` と `~/.grok` を含む
- `PI_DISTILL_ERROR_RETRY_COUNT`・`PI_DISTILL_MODEL`・`PI_DISTILL_TIMEOUT_SECONDS`・`PI_EXTENSIONS_LOCALE`・`MAAS_ANTHROPIC_TOKEN` が export されている
- `pi list` に `npm:@upstash/context7-pi` がある。`pi-mcp-adapter`・`pi-distill` は無い。settings の `extensions` は空配列
- `~/.pi/agent/models.json` の provider は `commandcode`・`deepinfra`・`deepinfra-distill`・`opencode-go`
- `pigo`・`pigs`・`pixg` の dry-run の argv に、ヘルパが付ける `--tui-mode regular` が無い（`--tui-mode` は利用者が渡した 1 つだけ。配置済みの共通ヘルパが #20 より前の版）
- `pigs`・`pixg` のランチャー別 tier は、すでに #20 の値（`cheap` などが `opencode-go/deepseek-v4.1-flash`）。`~/.pi` はホストと共有しているため、別の環境で更新した結果と考えられる
- `claude plugin list` に、`.claude/settings.json` の `enabledPlugins` の 5 つ（`example-skills`・`feature-dev`・`ripgrep`・`superpowers`・`web-quality-skills`）がある

## 4. 設計

### 4.1 比較表 `docs/maatlog-poc-porting.md`

構成は次のとおり。

1. 冒頭: 対象（#17 と子 #18〜#22）、移植元と移植先の基準、移植元の最新 `main` との差分の扱い
2. 判断の区分（D-3）と読み方（パスの書き方、1 ファイルを複数の行に分ける場合、子の表記の示し方）
3. 比較表。列は Issue の指定どおり「移植元のパス」「移植先のパス」「判断」「理由」「担当 Issue」。領域ごとの小見出しで分ける: pi 本体・拡張・MCP／pi のランチャー・モデル・サブエージェント／Claude Code／Grok Build・`ccda`・dsh／Dev Container・シェル・文書の共有ファイル／対象外（スキル・レビュー系ツール・pi の Context7）／対象外（MaatLog 固有と他のエージェント）
4. 網羅の確認: 方法と結果（4.4 節）
5. 指示文・MCP の読み込み: ルートとワールドを cwd にした場合に、各エージェントが何を読むかと、確かめた方法（4.5 節）
6. rebuild での確認: 手順、確認項目と記録、実認証のスモークテスト（4.6 節）

行の作り方:

- 子の表の行は、判断と理由を変えずに集める。移植元のパスが無い #19 の行は、移植元のファイル（`scripts/setup_pi.zsh` など）を補う。補うのはパスの列だけで、判断は変えない
- 移植元のパスの列は、リポジトリのルートからの完全なパスで書く（`pigo.json`・`pigod.json` のような省略をしない）。スキルとレビュー系ツールはディレクトリ単位の `**` で書き、行の中にファイル数とディレクトリ名を書く（D-2）
- 1 つのファイルを節ごとに別の子が担当した場合（`install_beforehand.bash`・`zshrc.txt`・`.devcontainer/README.md`）は、節ごとに行を分ける。どの子も扱わなかった節は #22 の行にする
- 移植先にだけあるファイル（`pigou`、`cleanup_pi_mcp.py`、`pi_json.py`、テストなど）は、移植元のパスを「なし」とし、関係する領域の小見出しに置く（子の表と同じ並びで読める）
- 担当 Issue の列は、判断を記録した Issue を書く。#17 本文で範囲外と決めた項目は「#17」とする

### 4.2 #22 が判断する行

| 移植元のパス | 判断 | 理由 |
| --- | --- | --- |
| `.agents/monitoring-runtimes.md` | 対象外 | #17 の「対象外とした項目」（スキルが参照する文書）。担当は #17 |
| `.agents/review-records.md`・`.agents/scripts/**` | 対象外 | #17 の「対象外とした項目」（レビュー系ツール）。担当は #17 |
| `.codex/.gitkeep` | 対象外 | standalone Codex の新規設定は #17 の範囲外。移植先は `.codex/config.toml` を持つ |
| `.cursor/rules/repository-ownership.mdc` | 対象外 | Cursor の設定で、MaatLog の親子リポジトリ（`public/` submodule）の規約。#17 の「移植先への適応・非対象」 |
| `.cursor/rules/shell-env-hygiene.mdc` | 既存維持 | 移植元と同一 |
| `.devin/skills/**` | 対象外 | Devin の設定とスキル。#17 の範囲外 |
| `.devcontainer/cleanup-workspace.bash` | 既存維持 | 移植先は汎用化した版（`WORKSPACE_CLEANUP_*`）。移植元の版は対象外のレビュー系ツールの reaper CLI に依存する |
| `.devcontainer/herdr-agent-task.bash`・`herdr-git-status.bash`・`herdr-status-updater.bash`・`herdr.toml` | 既存維持 | 移植元と同一 |
| `.devcontainer/herdr-pr-review.bash`・`herdr-pr-review-launch.bash`・`herdr-pr-review.toml` | 対象外 | レビュー系ツール。担当は #17 |
| `.devcontainer/starship.toml` | 既存維持 | 移植先はワールドごとの `.venv` を cwd から上へ探す。移植元はリポジトリのルートの `.venv` だけを見る |
| `.devcontainer/test-herdr-agent-task.bash`・`test-herdr-status.bash` | 既存維持 | 移植先が新しい（here-string で SIGPIPE を避ける）。コメントの言い換えは、移植元だけのコメントの言い換えの行で扱う |
| `.devcontainer/zshrc.txt`・`.devcontainer/test-herdr-migration.bash`・`.devcontainer/test-pi-superagents.bash`・`.devcontainer/test-herdr-agent-task.bash` のコメントの言い換え（「正本」を「基準」「元ファイル」に、「契約」を「仕様」にしたもの） | 除外 | 移植元は `AGENTS.md` の日本語表現の規則に合わせてコメントを言い換えた。これらのファイルは #22 の編集範囲外で、言い換えは動作に関わらないので取り込まない。移植先の `AGENTS.md` にも同じ規則があるので、言い換えはこれらのファイルを変える別の作業で行う（PR #33 のレビュー修正で足した行） |
| `.devcontainer/install_beforehand.bash` のうち `public` の checkout、Gitleaks・Playwright の導入 | 対象外 | MaatLog の公開アプリケーションと検証の手順 |
| `.devcontainer/install_beforehand.bash` のうち Codex・Cursor・Devin・uv・Starship・Herdr・共有スキルの導入と `pi-subagents` の置き換え | 既存維持 | 移植先の手順で足りる。`pi-subagents` の置き換えの手順は移植元と同等（差分はコメントの Issue 番号だけ） |
| `.devcontainer/install_beforehand.bash` のうち `~` 配下の書き込み可能なディレクトリの用意、apt の設定、基本パッケージとロケール、Herdr の補助スクリプトの配置、作業領域の掃除、`~/.zshrc` への連結 | 既存維持 | 移植先の手順で足りる。違いは、ディレクトリの一覧（`.grok`・`.dsh` は #18 で撤去し、移植先は秘密情報の置き場 `~/.config/create-reso-world` を持つ）、移植先だけが導入する `blender`、基本パッケージの前の重複した `apt update`（移植先は直前の手順の 1 回だけ）、移植元だけが置くレビュー系ツールの herdr-pr-review（移植先は `cleanup-workspace.bash` を symlink ではなくコピーで置く）と、コメントの Issue 番号（PR #33 のレビュー修正で足した行） |
| なし（移植先の `install_beforehand.bash` の ResoLoop の導入と Resonite のツールの確認、`zshrc.txt` の `require_command`・`update_if_present`・秘密情報の `env` の読み込み・.NET のツールの PATH） | 既存維持 | 移植先にだけある手順と補助 |
| `.devcontainer/zshrc.txt` のほかの行で扱わない設定（シェルの基本設定、PATH、git の alias、`genv`・`cod`・`buni`、`EDITOR`・`LANG`、Herdr の起動の関数、Starship の初期化） | 既存維持 | 移植元と同じ。違いは、関数の `require_command` の呼び出し（移植先にだけある補助）と、bun の補完のパス（移植先は `$BUN_INSTALL` を使う）だけ（PR #33 のレビュー修正で足した行） |
| `.devcontainer/README.md` のうち「Codex で CLAUDE.md を指示ファイルとして読む」「Herdr サイドバーの設定移行」「エージェント向けツールの導入」 | 既存維持 | 移植先は同じ内容を移植先の構成（Codex は `AGENTS.md` を直接読む、9 本のランチャー、5 つのプラグイン）で書いてある |
| `.devcontainer/README.md` のうち「pi のモデル定義とランチャー」「モデル定義の正」 | 既存維持 | 差分は setup スクリプトのパス（移植先は `.devcontainer/` に置く）と、移植先にだけある `pigou` の説明だけ（PR #33 のレビュー修正で足した行） |
| `.devcontainer/README.md` のうち冒頭の説明と「public/ checkout の検査と復旧」「npm への一本化（#147）と既存環境の移行」 | 対象外 | MaatLog の親子リポジトリと `public/` submodule（Playwright の導入を含む）、yarn からの移行の手順 |
| `.devcontainer/README.md` のうち「PR レビューの一括起動（herdr-pr-review）」 | 対象外 | レビュー系ツール。担当は #17 |
| `.devcontainer/zshrc.txt` のうち Cursor / Devin の alias（`cur`・`curo`・`dev`・`devo`・`devs` のモデル固定） | 対象外 | #17 の実行ボードで「Cursor / Devin のエイリアスは誰も変えない」と決めた |
| `.devcontainer/zshrc.txt` のうち `maatlog_periodic_cleanup`、`update()` | 既存維持 | 移植先は `workspace_periodic_cleanup` に汎用化し、`update()` は無いツールを飛ばす `update_if_present` を使う。`grok update` の撤去は #18 |
| `.github/workflows/ci.yml` | 対象外 | MaatLog の CI と検証入口（`scripts/ci/verify-devenv.sh`）。移植先は自分の CI を持つ |
| `.gitignore` | 既存維持 | 移植先の追跡方針（2026-09-26 の再設計 4.4 節）を保つ。`docs_draft/`・`/.worktrees/`・`/.claude/worktrees/` は移植先にもある |
| `.gitmodules`・`public` | 対象外 | MaatLog の `public/` submodule。#17 の「移植先への適応・非対象」 |
| `README.md` | 対象外 | MaatLog の開発ワークスペースの説明で、エージェント設定を含まない。移植先の `README.md` は #18・#19・#22 が移植の結果に合わせて更新した（別の行） |
| `opencode.json` | 対象外 | OpenCode CLI の設定（Superpowers のプラグインと pyright の LSP）。#17 の対象は pi と Claude Code で、移植先は OpenCode CLI を導入しない。`ccdu` と `pigo` などは OpenCode Go の API を使うが、この設定は使わない |
| `scripts/add_pi_skills_setting.py` | 除外 | pi は `.agents/skills` を cwd から git のルートまで自動で読むので不要。`~/.pi/agent/settings.json` に `.claude/skills` の絶対パスを足すと、ホストと共有する `~/.pi` を通じて他のワークスペースの pi にも効く（現行の settings にも別のリポジトリの絶対パスが残っている）。スキルの読み込みは #17 で対象外 |
| `scripts/ci/verify-devenv.sh` | 対象外 | MaatLog の検証入口。#17 の「移植先への適応・非対象」 |
| `tools/__init__.py` | 対象外 | レビュー系ツールの package。担当は #17 |

### 4.3 README の整合

`.devcontainer/README.md`:

- 「秘密情報」の変数の例に `GOOGLE_DEV_KNOWLEDGE_API_KEY` を足し、詳細は「API トークン」節を参照させる
- 「API トークン」節を、変数ごとに「使うもの」と「無いときの挙動」を書く形に書き直す。対象は `OPENCODE_API_KEY`（pi の OpenCode Go のランチャーは `auth.json` を優先して読むので通常は不要、`pigs`・`pixg` の `cheap` などの子 Pi も同じ、`ccdu` は環境変数が必須で優先順位を持つ、`setup_pi_opencode_go.zsh` の実行に必要）、`OPENCODE_GO_API_KEY`（旧名。OpenCode Go を使う `pigo`・`pigod`・`pigou`・`pigs`・`pixg` が `OPENCODE_API_KEY` に引き継ぎ、`ccdu` の 3 番目の候補）、`OPENCODE_GO_CLAUDE_API_KEY`（`ccdu` の最初の候補）、`DEEPINFRA_TOKEN`（pi の deepinfra と `ccdd`・`ccddg`）、`COMMANDCODE_API_KEY`（`piccg`・`piccd`）、`GOOGLE_DEV_KNOWLEDGE_API_KEY`（pi と Claude Code の Google Developer Knowledge の MCP）、`CONTEXT7_API_KEY`（`.codex/config.toml` の `env_vars` で Codex の `context7_stdio` に渡す。未設定なら `cod` が起動時に入力を求める。共有の `find-docs` スキルの Context7 の CLI と、Claude Code・Cursor の Context7 の MCP サーバーも、受け取った環境にあれば使い、無ければレート制限が低くなる）。値の例は書かない
- 新設の「既存環境の更新」節を「秘密情報」の次に置く。順序は、(1) 作業ツリーを最新の `origin/main` に追従させる、(2) ホストの `env` を見直す（`MAAS_ANTHROPIC_TOKEN` を消す、必要なら `GOOGLE_DEV_KNOWLEDGE_API_KEY` を足す）、(3) rebuild する（postCreate が自動で行うこと）、(4) rebuild では変わらないものを反映する（`pigs`・`pixg` の tier、pi の project trust、`models.json` に残る `deepinfra-distill` の任意の整理）、(5) 確認項目は、ルートの `README.md` の「対象外」が案内する移植の記録にある（D-14）。rebuild しない場合の手順は、既存の各節への参照で並べる。各節の詳細は書き写さない（D-8）

ルート `README.md`:

- 「構成」の `docs/` の説明に「pi と Claude Code の設定の移植の記録」を足す。ルートの `README.md` には移植元の名前を書かない（D-15）
- 「エージェントで作業する」に pi の項目を足す。project trust を承認すると `.pi/settings.json`（組み込み MCP）と `.pi/mcp.json`（Google Developer Knowledge）、`.pi/APPEND_SYSTEM.md`（pi 固有の指示）、プロジェクトのスキル（`.agents/skills`）が読まれ、ワールドは `.pi -> ../.pi` から同じ設定を読む。キーと詳細は `.devcontainer/README.md`
- 「対象外」の rebuild 後の確認の参照先に「`docs/` にある移植の比較表（Issue #22）の「rebuild での確認」」を足す（文書名に移植元の名前が入るので、名前では参照しない。D-15）

`.devcontainer/test-readme.bash` などの既存のテストが README の表や節を検査しているので、表の列と既存の節の見出しは変えない（6 章の例外を除く）。`test-readme.bash` は `.devcontainer/` 配下に移植元の名前（maatlog）、3 桁の Issue 番号、ワークスペースの絶対パス、除外したツールの導入の記述が入ることを禁じている。`.devcontainer/README.md` に書く文はこれらを含めない。ルートの `README.md` は `tests/scripts/test-docs.bash` が `##` の見出しの並びを固定しているので、見出しを足さない

### 4.4 網羅の確認

Plan の一時スクリプト（scratchpad に置き、リポジトリには入れない）で、次を確かめる。

1. 移植元 `1f2aadb` のツリーを GitHub の API で取得し、blob と gitlink のパスを列挙する（456 件）
2. `docs/maatlog-poc-porting.md` の「比較表」の節の表から「移植元のパス」の列を取り出し（`\|` はセルの区切りとしない）、バッククォートで囲んだ語のうち、先頭の要素が移植元のツリーの最上位の名前（`.devcontainer`・`scripts`・`README.md` など）に一致するものをパスとして扱う。`/**` で終わるものはディレクトリの配下全体、それ以外は完全一致とする
3. 移植元の全パスが、いずれかの行に当たることを確かめる
4. 表のパス（`**` 以外）が、すべて移植元のツリーに存在することを確かめる（書き間違いの検出）
5. 判断の列が 5 つの区分のどれかで、担当 Issue の列が #17〜#22 のどれかであることを確かめる

結果（件数と日時）を比較表の「網羅の確認」に書く。

### 4.5 指示文・MCP の読み込み

ルートと 4 つのワールド（`MyResoniteProject`・`akichi`・`slum02`・`slum03`）を cwd にした場合について、次をまとめる。

- Claude Code: `CLAUDE.md`（`@AGENTS.md`）を cwd から祖先まで読む。`.claude/skills` は cwd から git のルートまで、`.mcp.json` は git のルートで解決する。ワールドの `.claude/settings.json` はルートへの symlink
- pi: `AGENTS.md` を cwd から祖先まで、`.agents/skills` を cwd から git のルートまで読む。`.pi/settings.json`・`.pi/mcp.json`・`.pi/APPEND_SYSTEM.md` は cwd 直下だけを読むので、ワールドは `.pi -> ../.pi` で同じ設定を読む。`.agents/skills` と `.pi` の設定は project trust が必要で、`AGENTS.md` は trust に関係なく読む
- Codex: `AGENTS.md` を git のルートから cwd まで読み、`.codex/config.toml` は trust のあるときだけ読む

確かめる方法は、既存のテスト（`scripts/check-layout.sh` の symlink の検査、`tests/scripts/test-instructions.bash`、`tests/scripts/test-agent-config.bash`、`.devcontainer/tests/test_pi_mcp_cleanup.py` のワールドの cwd の検査）と、Plan の静的な確認（各ワールドの `.pi`・`.claude/settings.json`・`.claude/skills` の解決先と `CLAUDE.md` の内容）。実際の CLI で読み込みを確かめるのは、trust の承認が必要なので rebuild 後の確認項目にする。

### 4.6 rebuild での確認と記録

`docs/maatlog-poc-porting.md` の「rebuild での確認」に、次を書く。

- 手順: 作業ツリーを最新の `origin/main` に追従させてから Rebuild Container を実行する。この PR は文書とテストの例外の 1 行だけを変え、導入スクリプトと設定ファイルを変えないので、rebuild の結果は `origin/main`（`01affb7` 以降）と同じになる。postCreate のログで `[install_beforehand] [25/25]` まで進み、エラーで止まっていないことを確かめる
- 確認項目と記録の表。列は「番号」「確認項目」「確認方法」「期待する結果」「rebuild 前（2026-10-05）」「rebuild 後」。rebuild 前の列には 3.5 節の値を書き、rebuild 後の列は「未記録」とする。項目は Issue #22 と各子の引き継ぎから作る

| 番号 | 確認項目 | 出典 |
| --- | --- | --- |
| R-1 | postCreate が 25 手順を完了する | #19（`STEP_TOTAL` 25） |
| R-2 | `/home/vscode` 配下の mount が 12 件で、`~/.dsh`・`~/.grok` が無い | #18 |
| R-3 | `dsh`・`grok` が PATH に無い。pnpm を npm で導入しない（`pnpmVersion: "none"`。Node の feature が `corepack enable` で置く `pnpm` の shim は残る）。転送するポートは 8000 だけ | #18 |
| R-4 | 新しいシェルに `PI_DISTILL_*`・`PI_EXTENSIONS_LOCALE`・`MAAS_ANTHROPIC_TOKEN`（`env` に書いていない場合）が無い | #18・#19 |
| R-5 | `pi list` と pi 管理の npm マニフェストに、撤去対象の 5 拡張が無い。settings の `extensions` に `-builtin:mcp` が無く、他の拡張・独自モデル・認証が残る | #19 |
| R-6 | `agent/migration-backups/pi-retired-*` は変更が必要なときだけ作られる（整理済みなら増えない） | #19 |
| R-7 | 全 9 ランチャーの dry-run の argv に `--tui-mode regular` があり、追加引数の `--tui-mode fullscreen` が後ろに残る | #20 |
| R-8 | `zsh .devcontainer/setup_pi_superagents.zsh` で `pigs`・`pixg` の tier が #20 の値になる（変更があればバックアップされる） | #20 |
| R-9 | `ccd`・`ccdo`・`ccds` の alias と 6 つのプロバイダ関数がある。短い名前だけが権限確認を省略することは、R-12 の `.devcontainer/test-herdr-migration.bash` が fake CLI の argv で検査する | #21 |
| R-10 | `claude plugin list` に 5 プラグインがある | #21 |
| R-11 | pi の trust を承認すると、ルートとワールド（代表として `slum02/`。4 つのワールドは同じ `.pi -> ../.pi` を持ち、`check-layout.sh` が検査する）で `.pi/settings.json`・`.pi/mcp.json` が読まれる | #19・#22 |
| R-12 | `bash scripts/check-layout.sh`・`bash .devcontainer/run-tests.bash`・`uv run pytest tests/skills .agents/skills` が通る | #22 |

- 実認証のスモークテスト（別枠）: provider の実接続（`pigo` などの 9 ランチャー、`ccdd`・`ccdd --model fable`・`ccddg`・`ccdu`）、サブエージェントの子 Pi、pi と Claude Code の Google Developer Knowledge の MCP。いずれも未検証と明記する
- 確認方法のコマンドは認証情報の値を表示しない（R-4 は `grep -oE` で変数名だけを出す）。R-7 の dry-run は argv を出す前に各ランチャーの認証などの前提を確かめるので、前提が未設定のランチャーは未確認として記録する（PR #33 のレビュー修正の F-1・F-2）。コマンドは表のセルに書かず、表の下のコードブロックに、読み取り専用のものと利用者の設定を変えるものを分けて置く。セルの `\|` を写すと、シェルが別のコマンドとして実行するため（同じく F-14）
- 記録の方法: 利用者が rebuild し、trust を承認したあと、エージェントか利用者が確認方法のコマンドを実行して「rebuild 後」の列に書き、この PR（マージ前）か後続のコミットで残す

### 4.7 PR と Issue の閉じ方

PR の本文には Issue の指定どおり `Closes #22` を書く。#22 の完了の証拠は「PR のマージ」「rebuild の確認の記録」「completed での close」なので、PR の本文に「rebuild 後の結果を `docs/maatlog-poc-porting.md` に記録してからマージする」というマージの条件を書く（D-10）。

## 5. 判断事項

| ID | 判断 | 代替案 | 理由 |
| --- | --- | --- | --- |
| D-1 | 移植先の基準を最新の `main`（`01affb7`）、移植元を `1f2aadb` にする。移植元の `main`（`e1f042e`）の追加差分は取り込まない | 移植元も `e1f042e` に上げる | Issue が `1f2aadb` を指定している。追加の 17 コミットの 28 ファイルは、レビュー系ツール（`tools/herdr_pr_review/**`・`pr-review-fix-loop`・`herdr-pr-review.toml`）と、`.devcontainer/README.md` のその説明、`CLAUDE.md` の「正本」の言い換えの規則だけで、最後のものは移植先の `AGENTS.md` に同じ文がある |
| D-2 | スキルとレビュー系ツールはディレクトリ単位の行にし、それ以外はファイル単位にする | 456 行すべてを書く | 対象外の 380 件余りを 1 行ずつ書くと、判断の要る行が埋もれる。ディレクトリ名とファイル数を書けば網羅は追える |
| D-3 | 判断の区分を、移植（移植元の内容や撤去をそのまま取り込む）、適応（移植先の構成に合わせて取り込む）、既存維持（移植先の現状を保つ。同一、移植先が新しい、移植先固有）、除外（検討して持ち込まない。#17 の除外 3 項目と各子の不採用）、対象外（#17 が範囲外とした項目、MaatLog 固有、pi / Claude Code 以外のエージェントとツール）と定める。子の表記は判断の後ろに括弧で残す | 子の表記をそのまま使う | Issue の 5 区分に揃えると集計と読み比べができる。表記を揃えるだけで判断は変えないので、子の Issue への記録は要らない |
| D-4 | 子の表に無い移植元のファイルは #22 が判断し、担当 Issue を #22 にする。#17 本文で範囲外とした項目は #17 にする | すべて #22 にする | 判断がどこで決まったかを追える |
| D-5 | `scripts/add_pi_skills_setting.py` を除外にする | 移植する | 4.2 節。pi の自動探索で足り、共有の `~/.pi` に絶対パスを残す副作用がある |
| D-6 | `opencode.json` を対象外にする | 移植する | 4.2 節。OpenCode CLI は移植先に無く、#17 の対象（pi / Claude Code）でもない |
| D-7 | rebuild の確認項目と記録は `docs/maatlog-poc-porting.md` に置き、`docs/integration.md` は変えない | `docs/integration.md` に足す | `docs/integration.md` は 2026-09 の再設計の統合手順で、仕様の節番号に結び付いている。移植の基準・判断・確認を 1 つの文書にまとめると追いやすい |
| D-8 | 既存環境の更新手順は `.devcontainer/README.md` の新しい節に順序だけをまとめ、詳細は既存の節へのリンクにする | 詳細を書き写す／比較表の文書に置く | 利用者が読むのは README。書き写すと同じ説明が 2 か所になり、片方だけが古くなる |
| D-9 | rebuild 前の基準値を、現行コンテナで読み取り専用のコマンドだけを使って記録する | 記録しない／`install_beforehand.bash` を実行して確かめる | rebuild の前後を比べられる。導入スクリプトは bind mount された利用者の設定を変えるので実行しない |
| D-10 | PR は `Closes #22` とし、rebuild の記録をマージの条件として PR の本文に書く | `Refs #22` にして後で閉じる | Issue の指定に従う。PR は文書とテストの例外の 1 行だけを変え、導入スクリプトと設定ファイルを変えないので、利用者はマージ前に `main` で rebuild でき、記録を同じ PR に足してからマージできる |
| D-11 | テストを追加しない。既存のテストの変更は D-15 の例外の 1 行だけにする。網羅は一時スクリプトで確かめて結果を記録する | 比較表の網羅を検査するテストを足す | #22 の編集範囲にテストが無い。検査には移植元のツリー（別リポジトリ）が要り、固定した基準の記録なので繰り返し検査する価値が低い |
| D-12 | 移植と無関係な README の記述（CI の無効化、`slum03/` の記載漏れ）は変えない | 直す | #22 の範囲は移植に伴う整合。Actions の無効化は一時的な設定の可能性がある |
| D-13 | 予約は PR の作成と作業報告まで保持し、計画の成果物（Spec・Plan・引き継ぎ書）を #22 に公開して復元を確かめてから実装に進む | 計画の公開を省く | #17 の運用ルールと、#20 の 1 セッションでの前例に従う |
| D-14 | `.devcontainer/README.md` には比較表の文書名を書かず、ルートの `README.md` の「対象外」から案内する | `test-readme.bash` の禁止語の例外を足す | `.devcontainer/` に移植元の名前を残さないという既存の規則（2026-09-26 の再設計）を保つ。テストは #22 の編集範囲外 |
| D-15 | `tests/skills/test_legacy_references.py` の `EXCLUDED` に `docs/maatlog-poc-porting.md` を足し、ルートの `README.md` は移植元の名前を使わずに比較表を案内する | 比較表の文書名を変え、内容から移植元の名前・`public`・`scripts/ci/verify-devenv.sh` を伏せる／ガードを変えずに比較表を `docs/superpowers/` に置く | このガード（2026-09-26 の再設計の 11 章）は、設計記録（`docs/superpowers`）以外の追跡ファイルが移植元を指すことを禁じる。比較表は Issue が文書名と、移植元の全ファイル（`public`・`scripts/ci/verify-devenv.sh` を含む）を載せることを指定した移行の記録で、設計記録と同じ理由で例外にあたる。伏せると記録として役に立たず、置き場所や名前を変えると Issue のインターフェースから外れる。エージェントが読む README は例外にせず、ガードの検出を保つ。実装中（全体の pytest）に分かった判断で、利用者の「推奨案で PR まで」の指示の範囲で決めた |

## 6. インターフェース

- コード、導入スクリプト、ランチャー、設定ファイルは変えない。`install_beforehand.bash` の `STEP_TOTAL`（25）、ランチャーの argv、`cleanup_pi_mcp.py` の起動方法は #18〜#21 のまま
- `docs/maatlog-poc-porting.md` は記録の文書で、利用者の現在の手順は README に書く（`docs/superpowers/README.md` の「履歴と現行仕様」と同じ考え方）
- `.devcontainer/README.md` の既存の節の見出しは変えない（テストと他の文書のリンクが参照する）。例外として、新設の「既存環境の更新」と同名だった「Superpowers スキルの探索パス」配下の `#####` の見出しを「pi-superagents の版の更新」に改名した。この見出しを参照する箇所とテストが無いことを確かめた（PR #33 のレビュー修正の F-6）

## 7. 受け入れ条件

Issue #22 の受け入れ条件との対応:

- 比較表が、除外 3 項目と #17 の「対象外とした項目」を含め、移植元 `1f2aadb` の全ファイル（blob 455 件と gitlink 1 件）を網羅し、判断・理由・担当 Issue を追える → 4.1・4.2・4.4 節
- 初回セットアップと既存環境の再実行の両方で、個人の認証情報と独自モデルを失わず、旧拡張の再混入や重複ツールがない → #19・#20 のテスト（cleanup の初回・再実行・バックアップ、setup の `--if-absent`）が通ることと、R-5・R-6・R-8 の確認項目。手順は「既存環境の更新」
- rebuild の手順と確認項目を用意し、rebuild 前の基準値を記録する。rebuild 後の結果は利用者の rebuild の後に記録する。実認証のスモークテストは未検証と明記する → 4.6 節
- ルートとワールドの cwd で、指示文・MCP が意図した範囲で読み込まれ、スキルの読み込みと symlink が回帰しない → 4.5 節と R-11
- `bash scripts/check-layout.sh`・`bash .devcontainer/run-tests.bash`・`uv run pytest tests/skills .agents/skills` が通る

## 8. 検証

worktree のルートで実行する。実認証とホストの設定は使わない。

- `bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash tests/scripts/test-docs.bash`（README の表と文書の検査）
- `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest -q tests/skills .agents/skills`（基準: PASS、27/27、516 passed / 1 skipped）
- 4.4 節の網羅の確認スクリプト
- 4.5 節の静的な確認
- README の「節名」の参照が、参照先のファイルの見出しとして存在すること（Plan の一時スクリプト）
- `uv run pytest -q tests/skills/test_legacy_references.py`（比較表を例外にした後も、README などへの移植元の名前の混入を検出すること）
- `git diff --stat origin/main...HEAD` で、変更が 2 章の 4 ファイル（文書 3 つとテストの例外の 1 行）と、この Spec・Plan・PR #33 のレビュー修正の Spec だけであること（`origin/main` は作業中に進むので、分岐点からの差分で比べる）

## 9. 比較表の行

この子の行は 4.2 節の表で、`docs/maatlog-poc-porting.md` に担当 #22（#17 の範囲外の項目は #17）として入れる。README の整合の行は次のとおり。

| 移植元のパス | 移植先のパス | 判断 | 理由 |
| --- | --- | --- | --- |
| `.devcontainer/README.md` の pi の「API トークン」 | `.devcontainer/README.md` の「秘密情報」「API トークン」と新設の「既存環境の更新」 | 適応 | #18〜#21 の変更に合わせて変数の説明と既存環境の手順をまとめる |
| なし | `README.md` の「構成」「エージェントで作業する」「対象外」 | 適応 | 比較表への参照（移植元の名前は使わない）と pi の trust の注意を足す |
| なし | `tests/skills/test_legacy_references.py` の `EXCLUDED` | 適応 | 移行の記録である比較表を、設計記録と同じくガードの例外にする（D-15） |
| なし | `docs/maatlog-poc-porting.md`（新規） | 適応 | #17 の比較表と rebuild の確認の記録 |

## 10. リスクと関連作業

- 比較表の表記を揃える（D-3）ときに、子の判断を読み違えると記録が誤る。子の表記を括弧で残し、Plan で子の表の全行と突き合わせる
- `.devcontainer/README.md` の「API トークン」節を書き直すと、#19・#20・#21 の記述と食い違うおそれがある。ランチャーの実装（`pigs`・`pixg`・`zshrc.txt` の `ccdu`）と `.mcp.json`・`.pi/mcp.json`・`.codex/config.toml` を読んで書く
- rebuild の記録が無いまま PR がマージされると、`Closes #22` で Issue が閉じる。PR の本文のマージ条件で防ぐ。閉じた場合は、記録を後続のコミットで足し、#22 に追記する
- 親 #17 の実行ボードとチェックリストの更新は調整役が行う。この子は #22 にだけ書く
