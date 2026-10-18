# Context7 を `ctx7` CLI と `find-docs` に移す 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Context7 を MCP Server（npx）と Pi の context7-pi から外し、版を固定した `ctx7` CLI と `find-docs` だけで使えるようにする。

**Architecture:** `ctx7` は新しい `.devcontainer/install_ctx7.bash` が固定した版で `npm install -g` し、`install_beforehand.bash` の 1 手順から呼ぶ。MCP の設定から `context7` を外し、Context7 しか無い `.cursor/mcp.json`・`.codex/config.toml` は削除する。Pi はセットアップでの導入をやめ、`.pi/settings.json` の `autoload: false` の差分でプロジェクト単位に読み込みを止める。

**Tech Stack:** bash（postCreate・導入スクリプト・テスト）、pytest（`tools/devenv_migration/tests`）、Pi 1.3.0、ctx7 0.8.0、Node.js v24.21.0

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue162-ctx7-cli-design.md`

- 状態: `draft`（内容の明示承認は受けていない。実行許可は Spec の「管理・実行許可」のとおり）

## Global Constraints

- `CTX7_CLI_VERSION="0.8.0"`。版は `.devcontainer/install_ctx7.bash` にだけ書く
- `ctx7 setup`・`ctx7 remove`・`ctx7 upgrade` をセットアップ・スキルから実行しない
- 共有の `~/.pi` の `npm:@upstash/context7-pi` を消さない（撤去の処理にも警告にも加えない）
- `.pi/settings.json` の差分は `"extensions": ["!**"]`・`"skills": ["!**"]`・`"prompts": ["!**"]`・`"themes": ["!**"]`（空配列では止まらない）
- `google-dev-knowledge` と `+builtin:mcp` は変えない。`cod` の `CONTEXT7_API_KEY` の入力も変えない
- キーの値をリポジトリ・ログ・PR に書かない。確かめるときは有無だけを表示する
- テストは `AGENTS.md` の「テストの採用基準」に従う。文面・設定値を照合するテストは書かない

## Review Focus

1. 版の出力に前後の空白・改行が付く `ctx7 --version` → 一致として扱う（Task 1 の成功ケースは改行付きの出力で確かめる）
2. 古い版の `ctx7` が PATH の前のほうにある環境 → 導入後の版の不一致で止まり、どの `ctx7` かを表示する（Task 1 の版の不一致のケース）
3. 共有の `~/.pi` に context7-pi が登録済みのまま Rebuild → 登録が 1 つだけ残り、`pi remove` されない（Task 2 の `test_pi_shared_packages.py`）
4. ワールド（`worlds/<name>` の `.pi` symlink）で起動した Pi → ルートと同じ `.pi/settings.json` を読み、context7-pi が読み込まれない（Task 2 の Pi の確認は symlink を持つ一時のプロジェクトでも行う）
5. `ctx7` が無い環境でエージェントが `find-docs` を使う → `npx ctx7` で補わず、止まってセットアップを案内する（Task 4 の行動比較）

---

### Task 1: `ctx7` の導入スクリプトとセットアップの手順

**テストの要否:** 要る。導入の成功と失敗の分岐、`ctx7 setup` を実行しないという安全条件を、スクリプトを実行して確かめる。

**Files:**
- Create: `.devcontainer/install_ctx7.bash`
- Create: `.devcontainer/test-install-ctx7.bash`
- Modify: `.devcontainer/install_beforehand.bash`（`STEP_TOTAL` を 31 に、`Installing Meshy CLI` の手順の後に `Installing the pinned Context7 CLI (ctx7)` の手順を足す）

**Interfaces:**
- Produces: `bash .devcontainer/install_ctx7.bash`（引数なし。成功で終了コード 0、失敗で `[install_ctx7] ERROR: ...` を stderr に出して 1）。`readonly CTX7_CLI_VERSION="..."` の行（テストと README が参照する）

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-install-ctx7.bash`。`test-install-gitleaks.bash` と同じ形（`set -euo pipefail`、`mktemp -d` と trap、`fail()`）。版は `install_ctx7.bash` の `readonly CTX7_CLI_VERSION="..."` から読む（テストに版を写さない）。

- 偽の `npm`（`$tmp/bin`）: 引数を `$CALLS` に `npm <args>` で記録する。`FAIL_NPM=1` なら終了コード 1。`PLACE_CTX7=0` でなければ `$NPM_BIN/ctx7` に偽の `ctx7` を置く
- 偽の `ctx7`: 引数を `ctx7 <args>` で記録し、`--version` のときだけ `printf '%s\n' "$FAKE_VERSION"`
- `PATH="$tmp/bin:$NPM_BIN:/usr/bin:/bin"`。各ケースの前に `$NPM_BIN/ctx7` と `$CALLS` を消す

| ケース | 環境 | 期待 |
|---|---|---|
| 成功 | `FAKE_VERSION=<固定した版>` | 終了コード 0。`$CALLS` に `npm install -g ctx7@<固定した版>` があり、`ctx7` で始まる行は `ctx7 --version` の 1 行だけ |
| 導入の失敗 | `FAIL_NPM=1` | 終了コード 0 以外、出力に `[install_ctx7] ERROR: `、`ctx7` で始まる行が無い |
| PATH に無い | `PLACE_CTX7=0` | 終了コード 0 以外、出力に `[install_ctx7] ERROR: ` |
| 版の不一致 | `FAKE_VERSION=0.0.0-unexpected` | 終了コード 0 以外、出力に `[install_ctx7] ERROR: ` と `0.0.0-unexpected` |

最後に `PASS: ...` を出す。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-install-ctx7.bash`
Expected: FAIL（`install_ctx7.bash` が無いので版を読めない）

- [ ] **Step 3: `.devcontainer/install_ctx7.bash` を書く**

`install_gitleaks.bash` と同じ形。冒頭のコメントに、版はここにだけ書くこと、更新の手順は `.devcontainer/README.md` の「Context7 CLI（ctx7）」、Rebuild せずに入れ替えるときもこのスクリプトを実行すること、`ctx7 setup` を実行しない理由（共有の `~/.claude`・`~/.claude.json`・`~/.codex` などに書き込み、`find-docs` とも重複する）を書く。順に `npm install -g "ctx7@${CTX7_CLI_VERSION}"`、`command -v ctx7`、`ctx7 --version`（空白を除いて比べる）。版の不一致のメッセージには、見つかった版・固定した版・`command -v ctx7` のパスを入れる。成功したら版とパスを 1 行で出す。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/test-install-ctx7.bash`
Expected: `PASS: ...`、終了コード 0

- [ ] **Step 5: セットアップの手順を足す**

`install_beforehand.bash` の `step "Installing Meshy CLI (local verification only)"` の手順の後に、`step "Installing the pinned Context7 CLI (ctx7)"` と `if ! bash .devcontainer/install_ctx7.bash; then fail "Context7 CLI installation failed."; fi` を足す。手順の前のコメントに、`find-docs` が使うこと・版と確認は `install_ctx7.bash` にあることを 1 行で書く。`STEP_TOTAL` を 31 にする。

- [ ] **Step 6: セットアップのテストを実行する**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-ctx7.bash .devcontainer/test-install-beforehand.bash .devcontainer/test-verify-resonite-tooling.bash`
Expected: `PASS: 3 test(s)`

- [ ] **Step 7: 実物で導入する**

Run: `bash .devcontainer/install_ctx7.bash && readlink -f "$(command -v ctx7)" && npm root -g`
Expected: 終了コード 0、`[install_ctx7] Context7 CLI 0.8.0 installed at ...`。実体が `$(npm root -g)/ctx7/dist/index.js`（`~/.npm/_npx` ではない）

- [ ] **Step 8: Commit**

```bash
git add .devcontainer/install_ctx7.bash .devcontainer/test-install-ctx7.bash .devcontainer/install_beforehand.bash
git commit -m "feat: install the pinned ctx7 CLI in postCreate (#162)"
```

### Task 2: Pi の context7-pi の導入をやめ、読み込みを止める

**テストの要否:** 既存のテストを直す。`test_pi_shared_packages.py` は context7-pi を新しい home でも入れることを前提にしている。共有の登録を消さないことは安全条件なので残し、入れないことの検査は足さない（削除した項目が無いことだけの検査に当たる）。読み込みを止めることは Pi の実起動で一度だけ確かめる。

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（`step "Installing the pi extensions"` の一覧から `npm:@upstash/context7-pi` を外し、手順の前に理由のコメントを 3 行以内で書く）
- Modify: `.pi/settings.json`
- Modify: `tools/devenv_migration/tests/test_pi_shared_packages.py`

**Interfaces:**
- Consumes: なし
- Produces: `.pi/settings.json` の `packages`（README が引用する）

- [ ] **Step 1: テストを直す**

`SHARED_PACKAGES` を、セットアップが入れる `INSTALLED_PACKAGES = ("npm:@plannotator/pi-extension",)` と、他のリポジトリが共有の `~/.pi` に入れ、このリポジトリは消さない `KEPT_PACKAGE = "npm:@upstash/context7-pi"` に分ける。docstring と定数のコメントに、context7-pi を残す理由（#162、他のリポジトリが使う）を書く。`registered` のパラメータは今のまま（`True` のとき両方を初めから登録する）。2 回の実行のそれぞれで次を確かめる。

- `INSTALLED_PACKAGES` がそれぞれ 1 つだけある
- `registered` なら `KEPT_PACKAGE` が 1 つだけある
- `npm:unrelated-user-package`・`extensions`・`theme` は今の検査のまま
- 最後に、`removals` に `INSTALLED_PACKAGES` と `KEPT_PACKAGE` のどれも無い

- [ ] **Step 2: 直したテストが今の実装で通ることを確かめる**

Run: `uv run --no-project --with pytest python -m pytest -q tools/devenv_migration/tests/test_pi_shared_packages.py`
Expected: 2 passed

- [ ] **Step 3: 一覧から外し、`.pi/settings.json` に差分を書く**

`.pi/settings.json`:

```json
{
  "extensions": ["+builtin:mcp"],
  "packages": [
    {
      "source": "npm:@upstash/context7-pi",
      "autoload": false,
      "extensions": ["!**"],
      "skills": ["!**"],
      "prompts": ["!**"],
      "themes": ["!**"]
    }
  ]
}
```

- [ ] **Step 4: Pi のテストを実行する**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-migrations.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-install-beforehand.bash`
Expected: `PASS: 3 test(s)`

- [ ] **Step 5: Pi の実起動で確かめる（一度だけ）**

scratchpad のプローブ（`pi --mode rpc --no-session --no-mcp --offline --approve -e <probe.ts>` に `{"type":"get_commands"}` を送り、`session_start` で `pi.getAllTools()` の名前を書き出す）を、worktree と、worktree の `.pi` への symlink だけを持つ一時のディレクトリ（ワールドと同じ形）で実行する。
Expected: どちらも `query-docs`・`resolve-library-id`・`c7-docs`・`skill:context7-docs` が無く、他のツール・コマンドは変更前の記録（`before.tools`・`before.commands`）から 4 つを除いたものと同じ。worktree に `.pi/npm` ができない。

あわせて、Rebuild に相当する確認として、`test_pi_shared_packages.py` の一時の home での実行記録に `context7` の `pi install` が無いことを一度だけ見る（`removals` と fake pi の呼び出しの記録）。

- [ ] **Step 6: Commit**

```bash
git add .devcontainer/install_beforehand.bash .pi/settings.json tools/devenv_migration/tests/test_pi_shared_packages.py
git commit -m "feat: stop installing and loading context7-pi in this repository (#162)"
```

### Task 3: MCP の設定から Context7 を外す

**テストの要否:** 既存のテストを直す。`tests/scripts/test-agent-config.bash` は `.codex/config.toml` を読む。Codex の検査を外し、MCP の header の鍵の直書きの検査を残す。Context7 が残らないことの検査は足さない。

**Files:**
- Modify: `.mcp.json`、`.pi/mcp.json`（`context7` の項目だけを消す）
- Delete: `.cursor/mcp.json`、`.codex/config.toml`
- Modify: `tests/scripts/test-agent-config.bash`（冒頭のコメント・Codex の検査・PASS の文）

**Interfaces:**
- Consumes: なし
- Produces: なし

- [ ] **Step 1: 設定を変え、テストを直す**

`test-agent-config.bash` は、`.pi/mcp.json`・`.mcp.json` の HTTP header が `${NAME}` の参照だけであることの検査だけにする。冒頭のコメントと PASS の文もそれに合わせる。

- [ ] **Step 2: 検証**

Run: `bash .devcontainer/run-tests.bash tests/scripts/test-agent-config.bash && jq empty .mcp.json .pi/mcp.json .pi/settings.json && rg -n -i context7 .mcp.json .pi/mcp.json; test ! -e .cursor/mcp.json && test ! -e .codex/config.toml && echo removed`
Expected: `PASS: 1 test(s)`、`jq` が終了コード 0、`rg` は何も出さない、`removed`

- [ ] **Step 3: MCP の接続を確かめる（一度だけ）**

- Pi: worktree で `pi mcp list --approve`（trust はそのプロセスだけ）。Expected: `google-dev-knowledge` だけ。`context7` が無い
- Claude Code: 親の checkout の外の一時ディレクトリに `.mcp.json` を写して `claude mcp list`。Expected: `google-dev-knowledge` だけ。キーの値は表示しない

- [ ] **Step 4: Commit**

```bash
git add -A .mcp.json .pi/mcp.json .cursor/mcp.json .codex/config.toml tests/scripts/test-agent-config.bash
git commit -m "feat: remove the Context7 MCP servers from the agent configs (#162)"
```

### Task 4: `find-docs` と `AGENTS.md`

**テストの要否:** 要らない（SKILL.md と規約の文面の変更）。代わりに、実物の `ctx7` でコマンドを確かめ、`writing-skills` の無し/ありの行動比較と、Claude Code・Pi での取得を行う。

**Files:**
- Modify: `.agents/skills/find-docs/SKILL.md`
- Modify: `AGENTS.md`（「最新ドキュメントの取得」の 1 行目）

**Interfaces:**
- Consumes: Task 1 の `ctx7`（この Dev Container に導入済み）
- Produces: なし

- [ ] **Step 1: 実物の `ctx7` で例を確かめる**

`ctx7 library react "..."`・`ctx7 docs /facebook/react "..."`・`ctx7 docs /prisma/prisma "..."`・`ctx7 docs /vercel/next.js "..."` を実行し、リダイレクトの表示と終了コードを記録する。`ctx7 whoami` の表示、`CONTEXT7_API_KEY` の有無（値は出さない）も記録する。

- [ ] **Step 2: 変更前の行動を記録する（無し）**

`ctx7` を PATH から外し、`npm`・`npx` を呼び出しを記録するだけの偽物にした PATH で、変更前の `find-docs` を読む `claude -p` に、ライブラリの質問（React の `useEffect` の後始末）をさせる。Expected（変更前）: `npx ctx7@latest` を試す

- [ ] **Step 3: `find-docs` を書き換える**

英語のまま、xrift-poc#51 の内容に合わせる。

- 冒頭の npx の指示を「Prerequisite: use only the installed `ctx7`」に置き換える: `command -v ctx7`、無ければ止まって Rebuild か `bash .devcontainer/install_ctx7.bash` を案内する（自分で `npm install` しない）、`npx ctx7`・Context7 の MCP Server・claude.ai の Context7 コネクタ・Pi の context7-pi（`resolve-library-id`・`query-docs`・`/c7-docs`）に切り替えない、`Update available`・`ctx7 upgrade`・`npm install -g ctx7@latest` に従わない（版は `CTX7_CLI_VERSION` を変える PR で上げる）、`ctx7 setup`・`ctx7 remove` を実行しない
- シェルを使えないサブエージェントは、親かシェルを使える worker に頼み、頼めなければ取得できなかったことを書く
- 例の ID を Step 1 の実測に合わせ、ライブラリ ID のリダイレクトの節（新しい ID で 1 回だけやり直し、3 回の回数に含める）を足す
- 認証: `CONTEXT7_API_KEY`（`~/.config/create-reso-world/env`）を基本とし、有無だけを確かめるコマンド、`ctx7 whoami` は `ctx7 login` の状態だけを出すこと、`ctx7 login` の保存先（`~/.config/context7/credentials.json`、Rebuild で消える）
- エラーの表（`ctx7` が無い・リダイレクト・not found・quota）。quota の手順は今のまま
- Common Mistakes に「`ctx7` が無いときに npx や npm install で補わない」を足す

- [ ] **Step 4: `AGENTS.md` を書き換える**

「最新ドキュメントの取得」の 1 行目を「ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は、find-docs スキルの手順で Context7 CLI（`ctx7`）を使って確認する。npx・Context7 の MCP Server・Pi の Context7 拡張に切り替えない」にする。2 行目（3 回まで）は残す。

- [ ] **Step 5: 変更後の行動と取得を確かめる**

- 無し → あり: Step 2 と同じ環境で、新しい `find-docs` を読む `claude -p`。Expected: `command -v ctx7` で止まり、セットアップを案内する。偽の `npx`・`npm` の記録が空
- Claude Code: worktree で `claude -p`（`find-docs` を使う指示と同じ質問）。Expected: `command -v ctx7` → `ctx7 library` → `ctx7 docs` を実行して答える
- Pi: worktree で `pi -p --approve`（使える provider で）。Expected: 同上
- Codex: `codex exec` が認証済みなら同上。認証が無ければ未実施と記録する
- Run: `bash .devcontainer/run-tests.bash tests/scripts/test-instructions.bash tests/scripts/test-docs.bash` と `uv run pytest tests/skills .agents/skills`
- Expected: すべて成功

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/find-docs/SKILL.md AGENTS.md
git commit -m "docs: make find-docs use only the installed ctx7 CLI (#162)"
```

### Task 5: README と移植の記録

**テストの要否:** 要らない（文書）。`.devcontainer/test-readme.bash`（ツールの表と実装の突き合わせ）と `tests/scripts/test-docs.bash` で確かめる。

**Files:**
- Modify: `.devcontainer/README.md`
- Modify: `README.md`（「エージェントで作業する」の Codex・cursor-agent・pi の注意）
- Modify: `docs/maatlog-poc-porting.md`

**Interfaces:**
- Consumes: Task 1〜4 の名前（`install_ctx7.bash`、`CTX7_CLI_VERSION`、`.pi/settings.json` の項目）
- Produces: なし

- [ ] **Step 1: `.devcontainer/README.md`**

- 「導入ツール一覧」の表に `Context7 CLI（ctx7）` の行（導入方法: `install_ctx7.bash`（npm の `ctx7@0.8.0` を固定して入れ、`ctx7 --version` を確かめる）、他の列は `—`）
- 「Meshy CLI と生成物の受け渡し」の後に「## Context7 CLI（ctx7）」節: 導入（固定した版、実体は npm のグローバルの `node_modules`、`ctx7 setup` を実行しない理由、`update` では更新しない）、更新（`npm view ctx7 version engines`、`CTX7_CLI_VERSION` を変え、`bash .devcontainer/install_ctx7.bash`、動作確認、PR）、`Update available` に従わないこと、移行（外した設定の一覧、リポジトリの外の設定の表: Claude Code のユーザースコープ・Codex のユーザー設定・claude.ai のコネクタ・共有の `~/.pi`）、Pi の差分（JSON、`"!**"` と空配列の違い、project trust、土台が無いときの `.pi/npm`、すべてのリポジトリが移行したら項目も外す、撤去・警告に加えない理由、RPC での確認のコマンド）、認証（`CONTEXT7_API_KEY` を `env` に書く、`cod`、`ctx7 login` の保存先と Rebuild、`ctx7 whoami`、テレメトリは `CTX7_TELEMETRY_DISABLED` で止められる）、動作確認、トラブルシュート
- 「既存環境の更新」の手順 3 の context7-pi の記述、「pi の旧拡張・MCP 設定の移行」の context7-pi の記述と手動の `pi install`、「組み込み MCP と廃止した拡張」の `.pi/mcp.json` の説明、「API トークン」の `CONTEXT7_API_KEY` を、新しい構成に合わせる

- [ ] **Step 2: `README.md`**

Codex の注意（`.codex/config.toml` の MCP）と cursor-agent の注意（`.cursor/mcp.json`）を外し、pi の注意を「`.pi/settings.json`（組み込み MCP の有効化と context7-pi の読み込みの停止）と `.pi/mcp.json`（Google Developer Knowledge の MCP サーバー）」にする。Context7 は `find-docs` から `ctx7` で使うことを 1 行で足し、`.devcontainer/README.md` の「Context7 CLI（ctx7）」を指す。

- [ ] **Step 3: `docs/maatlog-poc-porting.md`**

冒頭の #125 の段落の後に、#162（2026-10-18）で Context7 を `ctx7` CLI と `find-docs` に移したこと（MCP の `context7`・`.codex/config.toml`・`.cursor/mcp.json` を外し、context7-pi の導入をやめて `.pi/settings.json` で読み込みを止めた。共有の `~/.pi` の登録は消さない）を 1 段落で書く。「スキル・レビュー系ツール・pi の Context7 の判断」の #125 の context7-pi の行と、`.pi/mcp.json` の行の理由に「後に #162 で…」を足す。rebuild の表（過去の観測）は書き換えない。

- [ ] **Step 4: 検証**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash tests/scripts/test-docs.bash && git diff --check`
Expected: `PASS: 2 test(s)`、`git diff --check` が何も出さない

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/README.md README.md docs/maatlog-poc-porting.md
git commit -m "docs: document the ctx7 CLI and the Context7 migration (#162)"
```

### Task 6: 全体の検証・レビュー・PR

**テストの要否:** 新しいテストは作らない。`README.md` の「テスト」の全体を実行する。

- [ ] **Step 1: 全体のテスト**

Run（worktree のルートで）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`
Expected: すべて終了コード 0。長くかかるものは `monitoring-long-tasks` で終了コードと実ログを確かめる

- [ ] **Step 2: ブランチ全体のレビュー**

`origin/main..HEAD` を、新しいレビュアー 1 人に読み取り専用で見てもらう。Critical・Important を直し、Minor は理由を記録して採否を決める。

- [ ] **Step 3: Plan の「実行記録」に結果を書き、commit する**

- [ ] **Step 4: push と PR**

issue-to-pr の 5 章のとおり、`scan-before-push.sh` で検査した SHA を push し、`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-162-ctx7-cli`。本文に `Closes #162`、変更概要、Spec の決定と理由、実行方式と理由、検証と結果、既知の制約、利用者に確かめていただくこと（Rebuild 後の `ctx7`、親の checkout の更新後の `/mcp`・`pi mcp list`、claude.ai のコネクタの扱い）、作業時間を書く。

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。Task は互いの名前（`install_ctx7.bash`・`.pi/settings.json` の項目）を README が引用し、Task 4 は Task 1 で入れた実物の `ctx7` を使う。調査で得た Pi の実測（プローブ、変更前の記録）と xrift-poc#51 の内容を子に渡し直すと費用が大きく、同じファイル（`install_beforehand.bash`）を Task 1・2 で順に変える。最後のブランチ全体のレビューだけを新しいレビュアーに頼む。

## 実行予算

- 能動時間 180 分。着手（2026-10-18 19:11 JST）から数える。ledger は `/workspaces/reso-world/tmp/agents/issue-162.icutt74r/budget.jsonl`（19:19 開始）。根拠: 6 Task、設定・セットアップ・スキル・文書にまたがり、Claude Code・Pi の実起動の確認とブランチ全体のレビューを含む。似た規模の xrift-poc#51 は約 56 分
- phase の目安: 準備・設計 25 分、Task 1〜3 40 分、Task 4 35 分、Task 5 30 分、全体検証 20 分、レビュー・修正 20 分、公開・記録 10 分
- worker: ブランチ全体のレビュアー 1 人（同期の呼び出し、読み取り専用）。目安 15 分、保存の予約枠 2 分、無進捗 10 分。ランタイムに停止の API が無いので、事前宣言した打ち切りは適用せず、同期の終了を待つ。`claude -p`・`pi -p` の確認は 1 回 5 分で `timeout` をかける
- 再試行: 同じ信頼性の失敗は 1 回まで（2 回目で方法変更）。安全の失敗（共有の `~/.pi`・`~/.claude` などへの意図しない書き込み、キーの露出）は即時に全体停止
- checkpoint: phase の境界、予算の 50%（90 分）・100%、worker の失敗の直後。100% で自動延長せず止まる
- 縮小・切り出し・方法変更の候補: Pi の `pi -p` の取得が provider の認証で通らなければ別の provider に変え、それも通らなければ RPC の確認と Claude Code の取得だけにして PR に未実施と書く。Codex は認証が無ければ未実施とする。全体のテストの既知でない失敗は、範囲外を直さず原因を調べ、この変更と無関係なら PR に書く

## 実行記録

- 実行方式: `superpowers:executing-plans`。ledger は worktree の `.superpowers/sdd/` ではなく `PARENT_ROOT` の `tmp/agents/issue-162.icutt74r/progress.md`（`AGENTS.md` の「worktree の中に、コミットしないファイルを作らない」）
- Task 1（`bf74033`）: `test-install-ctx7.bash` の RED（`install_ctx7.bash lacks readonly CTX7_CLI_VERSION`）→ GREEN。版の検査を外す・`ctx7 setup` を足す、の 2 つの壊し方をどちらも捕まえた。実物の ctx7 0.8.0 をこのスクリプトで入れ、実体が `$(npm root -g)/ctx7/dist/index.js` であることを確かめた
- Task 2（`18d2fea`）: `test_pi_shared_packages.py` は 2 passed。`pi remove npm:@upstash/context7-pi` を足す壊し方を捕まえた。Pi の RPC のプローブで、ルートとワールドの形（`.pi` の symlink だけの一時ディレクトリ）のどちらでも context7-pi の 4 つのリソースが読み込まれず、他は変更前と同じ。`.pi/npm` はできない。`test-pi-migrations.bash`・`test-pi-superagents.bash` も PASS
- Task 3（`9a028ba`）: `jq empty` 3 ファイル成功。`pi mcp list`（worktree だけを trust した一時の agent ディレクトリ）は `google-dev-knowledge` だけ（変更前の親の checkout では `context7` も）。親の外の一時ディレクトリの `claude mcp list` は、新しい設定で `google-dev-knowledge` だけ、旧設定で `context7` もある。`~/.claude.json` に一時ディレクトリの項目は増えていない
- Task 4（`79abf0c`）: 実物の ctx7 で `/facebook/react`・`/prisma/prisma` はリダイレクトで終了コード 1、`/react/react`・`/vercel/next.js`・`/prisma/orm` は 0。行動比較（`ctx7` を PATH から外し、`npm`・`npx` を記録だけの偽物にした `claude -p --model sonnet`）: 変更前は `npx ctx7@latest library ...` を試して WebFetch に切り替えた。変更後は `command -v ctx7` で止まってセットアップを案内し、`npm`・`npx` の呼び出しは 0 件。取得: Claude Code（`claude -p`）、Pi（`pi -p`、commandcode の `deepseek/deepseek-v4.1-flash`、ツール呼び出しを記録するプローブ拡張で確認）、Codex（`codex exec`）のどれも `find-docs` → `command -v ctx7` → `ctx7 library` → `ctx7 docs` で取得した。Pi の `--mode json` は 300 秒で出力なしの timeout になり（信頼性の失敗 1 件）、`-p` に変えた。最初の `pi -p` がこの pane の Herdr のタスク名を書き換えたので戻し、以降は `HERDR_*` を外して実行した
- Task 5（`4051b8a`）: `test-readme.bash`・`test-docs.bash` PASS（Task 4 の時点の `test-docs.bash` の失敗は README の更新で解消）。README の RPC の確認コマンドを worktree（58 件、context7 なし）と親の checkout（`c7-docs` あり）で実行した
- Task 6: `4051b8a` で `bash .devcontainer/run-tests.bash` 33/33 PASS、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills .agents/scripts` 656 passed（すべて EXIT=0）
- ブランチ全体のレビュー（`3e3c1a3..4051b8a`、読み取り専用の新しいレビュアー）: Ready to merge: Yes。Critical・Important は 0。Minor 5 件（`AGENTS.md` に claude.ai のコネクタを名指ししていない、移行の表に利用者のローカルの `.claude/settings.local.json` が無い、移植の記録の #17 の行、空白除去を通るテストが無い、途中の commit で `test-docs.bash` が失敗する）は、影響が文書の言葉と記録の整合だけなので直さない
- 実行予算: 19:57 時点で ledger の能動時間 37 分（使用率 21%）、安全の失敗 0、信頼性の失敗 1（`pi-json-mode-timeout`、方法変更で解消）
