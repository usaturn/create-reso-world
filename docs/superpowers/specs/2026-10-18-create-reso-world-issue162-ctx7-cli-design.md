# Context7 を MCP・Pi 拡張から `ctx7` CLI と `find-docs` に移す

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/162
- 状態: `draft`（内容の明示承認は受けていない）
- 調査時 HEAD: `3e3c1a3`
- 利用者の指示: Claude Code のセッションで `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/162`
- 実行許可: issue-to-pr の委任範囲に従い、通常の判断を推奨案で決め、検証・commit・push・PR 作成まで進める。マージ、共有の `~/.pi` からの context7-pi の削除、ユーザー側の設定（`~/.claude.json`・`~/.codex/config.toml`・claude.ai のコネクタ）の変更、他のリポジトリの変更は含まない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-162-ctx7-cli`、branch `feat/issue-162-ctx7-cli`（`origin/main` `3e3c1a3` から作成）
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue162-ctx7-cli.md`
- 参考: usaturn/xrift-poc#49 と、その PR usaturn/xrift-poc#51（2026-10-18 時点で open、head `645a7dd`）

## 意図と範囲

Context7 の MCP Server は `npx -y @upstash/context7-mcp` で起動している。2026-10-18 に usaturn/xrift-poc の Dev Container で、npx の一時展開物（`~/.npm/_npx/<hash>/`）の欠けから `MODULE_NOT_FOUND` になり、Pi と Claude Code の両方で使えなくなった。このリポジトリも同じ起動に頼っているので、同じ壊れ方で使えなくなる。

Context7 は、Dev Container のセットアップが版を固定して入れる `ctx7` CLI と、既存の `find-docs` スキルだけで使う。MCP Server と Pi の Context7 拡張（`npm:@upstash/context7-pi`）はこのリポジトリでは使わない。`google-dev-knowledge` など Context7 以外の MCP は残す。

`npm:@upstash/context7-pi` は MCP も npx も使わないので、今回の障害の影響は受けない。それでも止めるのは、拡張が足すツール（`resolve-library-id`・`query-docs`）・スキル（`context7-docs`）・コマンド（`/c7-docs`）が `find-docs` と同じ役割で並び、どちらを使うかがモデル任せになるためである。共有の `~/.pi` は他のリポジトリ（xrift-poc・agent-workspace・wabun-rst-ulint-poc）のセットアップも使い、そちらはまだこの拡張を入れる。共有の `~/.pi` からは削除せず、このリポジトリのセットアップでの導入をやめ、プロジェクトの `.pi/settings.json` で読み込みを止める。

### 範囲外

- 共有の `~/.pi` からの `npm:@upstash/context7-pi` の削除（すべてのリポジトリが移行した後に利用者が行う）
- `~/.npm/_npx` の壊れた展開物の修復と、最初の原因の調査
- ユーザー側の設定と claude.ai の Context7 コネクタ（`mcp__claude_ai_Context7__*`）。外すかどうかは利用者が決める。2026-10-18 に確かめたとき、`~/.claude.json` の `mcpServers` と `~/.codex/config.toml` の `mcp_servers` に Context7 は無かった
- 新規・Rebuild 後のコンテナでの確認（再ビルドは利用者が行う）

## 必要な挙動

1. `.mcp.json`・`.pi/mcp.json` に `context7` が無く、`google-dev-knowledge` は今のまま残る。`.pi/settings.json` の `+builtin:mcp` も残る
2. `.cursor/mcp.json` と `.codex/config.toml` を削除する（どちらも Context7 の設定しか無い）
3. セットアップ（postCreate）は `ctx7` を `CTX7_CLI_VERSION`（0.8.0）に固定して `npm install -g` する。導入の失敗・PATH に無い・`ctx7 --version` が固定した版と違う、のどれでも `ERROR` 行を出してセットアップを止める。`ctx7 setup` は実行しない
4. セットアップは `npm:@upstash/context7-pi` を入れない。共有の `~/.pi` に登録があっても消さない
5. このリポジトリ（ルートと、`.pi` の symlink で同じ設定を読むワールド）で起動した Pi に、context7-pi のツール・スキル・プロンプトが読み込まれない。他の拡張のツール・コマンドは変わらない
6. `find-docs` は、インストール済みの `ctx7` だけを直接実行する。`ctx7` が無ければセットアップを案内して止まり、npx・MCP・Pi の拡張・claude.ai のコネクタに切り替えない。`ctx7` の更新の案内（`Update available`）に従わない。`ctx7 setup` を実行しない
7. `cod` が `CONTEXT7_API_KEY` を尋ねる処理は残す（Codex から `ctx7` を呼ぶときにも使う）
8. `.devcontainer/README.md` に、導入・版の更新・認証・既存の MCP や拡張からの移行・動作確認を書く

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| xrift-poc#49 との関係 | xrift-poc#51 の本文に記録された確認の結果（Pi の差分の書き方）に合わせて着手する。この環境でも同じ確認をやり直す | xrift-poc#51 のマージを待つ | Issue は「そこで確かめた方法に合わせる」と書き、マージを前提にしていない。確認の結果は #51 の本文にあり、この Spec の調査で同じ結果を得た（下の「Pi の差分」）。#51 のレビューで方法が変わったら、このリポジトリも追って直す | issue-to-pr による通常判断の委任 |
| `.cursor/mcp.json` | ファイルを削除する | 空の `mcpServers` を残す | Issue が選択を任せている。サーバーの無い設定は働きが無く、README の「初回に承認を求められる」の注意も要らなくなる。`.cursor/rules/` は残るので `.cursor/` も残る | Issue の「決める」の委任 |
| `.codex/config.toml` | ファイルを削除する | コメントだけのファイルを残す | `[mcp_servers.context7_stdio]` を外すと設定が何も残らない。コメントだけ残しても Codex の挙動は変わらず、README の trust の注意だけが残って紛らわしい | issue-to-pr による通常判断の委任 |
| `ctx7` の導入の置き場所 | `.devcontainer/install_ctx7.bash` を作り、`CTX7_CLI_VERSION` をそこにだけ書く。`install_beforehand.bash` の手順 1 つから呼び、失敗ならセットアップを止める | xrift-poc と同じく `install_beforehand.bash` の中の関数にする | このリポジトリは版を固定するツールを `install_gitleaks.bash`・`install_meshy.bash` の別スクリプトで入れている。別スクリプトなら、版を上げたときに Rebuild せずに同じスクリプトで入れ替えられ、テストもスクリプトをそのまま実行できる（`install_beforehand.bash` の断片を切り出さずに済む）。Issue の「`install_beforehand.bash` で導入し、失敗でセットアップを止める」は、呼び出しの手順で満たす | issue-to-pr による通常判断の委任 |
| `ctx7` の版 | 0.8.0 | 版を固定しない（`@latest`） | Issue の指定。2026-10-18 の npm の latest（2026-10-16 公開）。`engines.node` は `>=22.13.0` で、Dev Container の Node.js は v24.21.0 | Issue の指定 |
| 導入の確認 | `npm install -g` の終了コード、`command -v ctx7`、`ctx7 --version` の出力（前後の空白を除く）と `CTX7_CLI_VERSION` の一致 | 実体のパスが `npm root -g` の下にあることも検査する | Issue の 3 条件。実体のパスは、版が一致していれば機能に影響せず、`ctx7` の実体が npx に依存しないことは移行時の確認と README の「動作確認」で確かめる | Issue の指定 |
| `ctx7` の導入のテスト | 新しい `.devcontainer/test-install-ctx7.bash`。偽の `npm`・`ctx7` を置いた一時の PATH で `install_ctx7.bash` を実行し、成功・導入の失敗・PATH に無い・版の不一致を確かめる。成功時に `ctx7` を `--version` 以外で呼ばない（`ctx7 setup` を実行しない）ことも確かめる | `test-install-beforehand.bash`・`test_pi_installer_isolation.py` にケースを足す（Issue の例） | Issue は既存のテストを例に挙げているが（「など」）、このリポジトリでは導入スクリプトごとにテストを置いている（`test-install-gitleaks.bash`・`test-install-meshy.bash`）。`run-tests.bash` は `.devcontainer/test-*.bash` をすべて実行するので、追加の登録は要らない。`ctx7 setup` を呼ばないことは、共有の場所に書き込まないという安全条件なので検査する | Issue の「テスト」 |
| Pi の差分 | `.pi/settings.json` の `packages` に `{"source": "npm:@upstash/context7-pi", "autoload": false, "extensions": ["!**"], "skills": ["!**"], "prompts": ["!**"], "themes": ["!**"]}` を置く | Issue の例の空配列（`"extensions": []` など） | 2026-10-18 にこの worktree で Pi 1.3.0 を RPC モードで起動し（モデルを呼ばない。読み込んだツールを書き出すプローブ拡張を使う）、確かめた。変更前と空配列では `query-docs`・`resolve-library-id`・`/c7-docs`・`skill:context7-docs` が読み込まれ、`"!**"` では 4 つとも読み込まれず、他のツール 20 個・コマンド 58 個は変更前と同じだった。`.pi/npm` は作られなかった。xrift-poc#51 の結果と同じ | Issue の「確かめた方法に合わせる」 |
| 廃止した拡張の扱い | context7-pi を撤去の処理（`remove_pi_*`）にも警告にも加えない | `pi-lens` と同じく `remove_pi_*` で消す | 他のリポジトリが共有の `~/.pi` で使い続ける。消すとそれらの Pi からも外れ、次のセットアップでまた入る | Issue の指定 |
| `test_pi_shared_packages.py` | Plannotator は新しい home でも入り、context7-pi は登録があれば 1 つだけ残り、どちらも `pi remove` されないことを確かめる形に直す | context7-pi を入れないことも検査する | 共有の `~/.pi` の登録を消さないことは、他のリポジトリを壊さないための安全条件なので残す。入れないことだけを確かめるのは、削除した項目が無いことの検査に当たる（`AGENTS.md` の「テストの採用基準」）。移行時に一度だけ確かめる | — |
| `tests/scripts/test-agent-config.bash` | Codex の項目の検査を外し、MCP の header の検査だけを残す | ファイルごと消す | `.codex/config.toml` を消すので Codex の検査は成り立たない。header の鍵の直書きの検査は、private の CI を止めている間に直書きを止める唯一の検査で、残す | — |
| `find-docs` の書き方 | 英語のまま、前提（`command -v ctx7`、無ければ止まる、切り替えない、更新の案内に従わない、`ctx7 setup` をしない）、ID のリダイレクト、シェルの無いサブエージェント、認証（`CONTEXT7_API_KEY` と `ctx7 login` の保存先）、エラーの表を足す。例の ID は実測で直す | xrift-poc の日本語の版で置き換える | このリポジトリの `find-docs` は英語で書かれている。内容は xrift-poc#51 に合わせ、このリポジトリの秘密情報の置き場所（`~/.config/create-reso-world/env`）に合わせる | — |
| `AGENTS.md` | 「最新ドキュメントの取得」の 1 行目を、`find-docs` の手順で `ctx7` を使い、npx・MCP・Pi の拡張に切り替えないことに書き換える。3 回までの行は残す | 変えない | `AGENTS.md` は常に読まれる。Claude Code では claude.ai の Context7 コネクタが MCP のツールとして見え、サーバーの案内文が使うよう促すので、スキルを読む前にも切り替えないことが分かるようにする。書き換える行の「正本」は、`AGENTS.md` の日本語表現の規則に合わせて使わない | — |
| 移植の記録（`docs/maatlog-poc-porting.md`） | #125 の context7-pi の行と、Context7 に触れる箇所に、#162 で変えたことを追記する | 書き換えない | この文書は「#125 の行が現在の判断」としているので、そのままだと現在の判断と食い違う。過去の観測の記録（rebuild の表）は書き換えない | — |
| テストの範囲 | 実行して確かめるのは `ctx7` の導入（新しいテスト）と共有の登録を消さないこと（既存のテストの修正）だけ。設定・文書の変更はテストを書かない | 設定から Context7 が消えたことをテストにする | `AGENTS.md` の「テストの採用基準」。JSON・TOML が読めることと、Context7 が残らないことは移行時に一度だけ確かめる | Issue の「テスト」 |

## 検証と受け入れ条件

| 受け入れ条件（Issue） | 確かめ方 |
|---|---|
| MCP の設定に Context7 が残らず、`google-dev-knowledge` は動く | `jq empty` で JSON が読めること、`rg -i context7` で 4 つの設定に残らないことを一度だけ確かめる。Pi は trust を一時に与えた `pi mcp list`、Claude Code は親の外の一時ディレクトリに写した設定で `claude mcp list` を実行し、`google-dev-knowledge` だけが出ることを確かめる |
| `ctx7` の版が固定され、導入・PATH・版の失敗でセットアップが止まる | `.devcontainer/test-install-ctx7.bash`。`test-verify-resonite-tooling.bash` が `STEP_TOTAL` と手順の数を比べる |
| Pi と Claude Code で `find-docs` から CLI を通して取得できる（可能なら Codex でも） | この Dev Container に `install_ctx7.bash` で `ctx7` を入れ、worktree で `claude -p` と `pi -p` に `find-docs` での取得を頼み、`ctx7 library`・`ctx7 docs` を実行したことを確かめる。`ctx7` を PATH から外したときに、止まって案内することも確かめる。Codex は認証があれば試す |
| このリポジトリのセットアップが context7-pi を入れず、Pi に読み込まれない | `install_beforehand.bash` の拡張の一覧の差分。Pi の RPC モードとプローブ拡張で、4 つのリソースが読み込まれないことを確かめる |
| `ctx7` の実体が npm のグローバルの `node_modules` の下にある | `readlink -f "$(command -v ctx7)"` が `$(npm root -g)/ctx7/` の下を指す |
| 再ビルドの後も `ctx7 --version`・`ctx7 library`・`ctx7 docs` が動く | 再ビルドは利用者が行う。PR に確認の手順（`.devcontainer/README.md` の「動作確認」）を書く |

あわせて `README.md` の「テスト」のコマンド（ワールドの行を除く）を実行する。

## 既知の制約

- ユーザー設定（共有の `~/.pi/agent/settings.json`）に `npm:@upstash/context7-pi` が無いと、`autoload: false` の差分の土台が無いため、Pi は project の `.pi/npm` に context7-pi を導入する（読み込みはしない。xrift-poc#51 の実測）。今の共有の `~/.pi` には他のリポジトリが入れた登録があるので、この状態にはならない。すべてのリポジトリが移行して共有の `~/.pi` から外すときは、`.pi/settings.json` のこの項目も外す（`.devcontainer/README.md` に書く）
- Claude Code は、親の checkout の下に置いた worktree から起動すると、祖先の親の checkout の `.mcp.json` も読む（xrift-poc#51 の観測）。マージ後に親の checkout を更新するまで、worktree の Claude Code には `context7` が残る
