# Issue #18 Grok Build・ccda・dsh の導線の撤去 設計

- 対象: usaturn/create-reso-world Issue #18（親 #17。ボードのキー `issue17-maatlog-pi-claude-port`、子のキー `c1-exclusions`）
- 基準: `main` の `9699e94`。移植元は usaturn/maatlog-poc の `1f2aadb`
- 経路: brainstorming の written-spec 経路。変更は既存コードの範囲が決まった撤去（bounded）だが、利用者がすべての子 Issue に Spec と Plan を求めているため、書面の Spec を作る
- 状態: draft。2026-10-04 に利用者が #17 のボード（子 Issue の構成と、着手できる子の Spec・Plan・引き継ぎ書の作成まで）を承認した。この Spec の判断は、エージェント（Claude Code、claude-opus-5-5）が推奨値で決めたもので、Spec 自体の明示承認はまだ得ていない
- 作成: 2026-10-04

## 1. 目的

リポジトリが管理する Grok Build・`ccda`（`claude-alibaba`）・dsh（DeepSeek Harness）の導入・起動・マウント・ポート・更新・案内・テストの導線をなくす。pi で xai / Grok モデルを使う設定（`pixg`、pi-superagents の Grok の tier）と、DeepSeek を使う pi ランチャーや Claude Code のランチャー（`pigod`、`ccdd`、`ccddg` など）は変えない。

## 2. 範囲

対象は #18 の「編集してよいファイル」に限る。

- `.devcontainer/devcontainer.json`、`.devcontainer/initialize.bash`
- `.devcontainer/dsh-settings.yaml`・`.devcontainer/dsh-cordis.patch.yml`（削除）
- `.devcontainer/install_beforehand.bash` のうち、dsh の導入手順と定数、bind mount の書き込み確認リストの `.grok`・`.dsh`、`STEP_TOTAL`
- `.devcontainer/zshrc.txt` のうち、`claude-alibaba` / `ccda`、`cc_launcher_unsets` の `MAAS_ANTHROPIC_TOKEN`、`update()` の `grok update`、関連するコメント
- `.devcontainer/README.md` のうち、dsh・Grok Build・`ccda` に関わる節と記述
- `.devcontainer/docs/herdr-session-cwd-restore.md` の grok の例示
- `AGENTS.md`・`README.md` の対象エージェントの一覧
- テスト: `.devcontainer/test-initialize-mounts.bash`、`.devcontainer/test-readme.bash`、`.devcontainer/test-shell-tools.bash`、`.devcontainer/test-herdr-migration.bash`（`ccda` と `MAAS_ANTHROPIC_TOKEN` の部分）、`tests/scripts/test-docs.bash`

`.devcontainer/mounts.bash` は、マウントの書き方を変えないので編集しない。

### 範囲外

- スキル（`.agents/skills/**`・`.claude/skills/**`）と `.agents/monitoring-runtimes.md`。#17 でスキルは対象外とした。`herdr-agent-task`・`pi-model-name`・`pr-review` などのスキルや `monitoring-runtimes.md` が grok に触れていても変えない
- pi で xai / Grok モデルを使う設定（`pixg`、`pi-superagents/*.json`、`pi-superagents-exec.zsh`、README の `pixg` の節）。#20 の担当
- `install_beforehand.bash` の pi の拡張・MCP・pi-distill（#19）、`zshrc.txt` の pi の環境変数（#19）と Claude ランチャーの本体（#21）
- `docs/superpowers/` の過去の Spec・Plan（dsh を対象エージェントとした 2026-09-26 の再設計の記録を含む）と `docs/integration.md`
- ホストの `~/.grok`・`~/.dsh`、認証情報、利用者のセッション
- Dev Container の rebuild による確認（#22 がまとめて行う）

## 3. 現状

`main`（`9699e94`）で、撤去対象が残っている場所は次のとおり。移植先は Grok Build の CLI を導入していないが、mount と `update()` の項目が残っている。

| 対象 | 場所 |
| --- | --- |
| dsh | `install_beforehand.bash` の定数 `DSH_VERSION`・`DSH_COMMANDCODE_PROVIDER_VERSION` と手順「Installing DeepSeek Harness」（関数 `install_deepseek_harness`）、書き込み確認リストの `~/.dsh`。`devcontainer.json` の `~/.dsh` の mount、`pnpmVersion: "12.4.1"`（dsh の plugin のため）、`forwardPorts` の `3080`（dsh web）。`initialize.bash` の `~/.dsh`。雛形 `dsh-settings.yaml`・`dsh-cordis.patch.yml`。`.devcontainer/README.md` のツール表の行、「エージェントの読み込みの制約」の項目、「DeepSeek Harness（dsh）」の節。`AGENTS.md`・`README.md` の対象エージェントの一覧と「Cursor と dsh」の項目 |
| Grok Build | `devcontainer.json`・`initialize.bash`・書き込み確認リストの `~/.grok`。`zshrc.txt` の `update_if_present grok grok update` と `require_command` のコメント。README のツール表の `grok / gcloud / glab / bun` の行。Herdr の文書の PATH の例示 |
| `ccda` | `zshrc.txt` の `claude-alibaba` / `ccda` 関数、`cc_launcher_unsets` の `MAAS_ANTHROPIC_TOKEN`、共有リストのコメント。README のツール表の Claude Code の行と、「秘密情報」の節の `MAAS_ANTHROPIC_TOKEN` |
| テスト | `test-initialize-mounts.bash`（期待する mount の一覧に `.dsh`・`.grok`。食い違いの検出の例に `.dsh`・`.grok`）、`test-readme.bash`（ツール表の行と「dsh は」の記述を必須にしている）、`test-shell-tools.bash`（`update()` が grok を飛ばすことを必須にしている）、`test-herdr-migration.bash`（`ccda` と `MAAS_ANTHROPIC_TOKEN` を検査している）、`tests/scripts/test-docs.bash`（「Cursor と dsh」を必須にしている） |

## 4. 設計

### 4.1 dsh

- `install_beforehand.bash` から、定数 2 つとそのコメント、手順「Installing DeepSeek Harness」の全体（関数定義と呼び出し）、書き込み確認リストの `"${HOME}/.dsh"` を削除する。手順が 1 つ減るので `STEP_TOTAL` を 26 から 25 にする
- `devcontainer.json` から `~/.dsh` の mount を削除する。`pnpmVersion` は `"none"` にし、コメントを「pnpm を使うツールは無いため導入しない（省略すると latest が入る）」にする（判断 D-1）。`forwardPorts` から `3080` とそのコメントを削除し、`[8000]` にする（D-2）
- `initialize.bash` から `"${HOME}/.dsh"` を削除する
- `dsh-settings.yaml`・`dsh-cordis.patch.yml` を `git rm` する
- `.devcontainer/README.md` から、ツール表の dsh の行、「エージェントの読み込みの制約」の dsh の項目、「DeepSeek Harness（dsh）」の節（ファイルの末尾まで）を削除する。「次の 2 つは」を「次のエージェントは」にする。ツール表の後に、既存環境向けの注記を置く（4.5）

### 4.2 Grok Build

- `devcontainer.json`・`initialize.bash`・書き込み確認リストから `~/.grok` を削除する
- `zshrc.txt` の `update()` から `update_if_present grok grok update` を削除し、`require_command` のコメントの「grok・」を外す
- `.devcontainer/README.md` のツール表の行を `gcloud / glab / bun` にし、mount と `initialize.bash` の列から `~/.grok` を、`update()` の列から `grok update` を外す（`—` にする）
- `.devcontainer/docs/herdr-session-cwd-restore.md` の PATH の例示を「bun、opencode など」にする

### 4.3 ccda

- `zshrc.txt` から `claude-alibaba` / `ccda` 関数と、`cc_launcher_unsets` の `-u MAAS_ANTHROPIC_TOKEN` を削除する（D-3）。共有リストのコメントを「プロバイダ切替ランチャー（ccdd / ccddg / ccdu）」にする
- `.devcontainer/README.md` のツール表の Claude Code の行から `ccda` を外す。「秘密情報」の節の対象の例から `MAAS_ANTHROPIC_TOKEN` を外し、使わなくなったので `env` から削除するよう注記する。残すと、プロバイダ切替ランチャーの子プロセスにも渡るため

### 4.4 ルートの文書

- `AGENTS.md` と `README.md` の対象エージェントの一覧を「Claude Code、Codex、pi、Cursor、Devin」にする
- `README.md` の「Cursor と dsh: スキルの一部が見えない。」を「Cursor: スキルの一部が見えない。」にする

### 4.5 既存環境への影響と注記

- ホストの `~/.dsh`・`~/.grok` は削除しない。mount をやめるので、rebuild 後の Dev Container からは見えなくなる。rebuild する前のコンテナには、導入済みの `dsh` が残る。コンテナの中で dsh を消す手順は設けない。rebuild で消えるため（D-4）
- `.devcontainer/README.md` のツール表の後に、次の趣旨の注記を置く: dsh と Grok Build（`grok`）は導入も mount もしない。`ccda`（`claude-alibaba`）も置かない。ホストの `~/.dsh`・`~/.grok` は見えなくなるだけで削除しない。不要になったら利用者がホスト側で消す。rebuild する前のコンテナには `dsh` が残る
- 既存環境向けの手順の全体の整理は #22 が行う。この子は、撤去した箇所の注記に限る

### 4.6 再混入の検出

既存のテストに検査を足す。新しいテストファイルは作らない（D-5）。

- `test-initialize-mounts.bash`: 期待する mount の一覧から `.dsh`・`.grok` を外す（12 個）。一覧の完全一致で、mount を戻すと失敗する。食い違いの検出の例に使っていた `.dsh`（target の検査）と `.grok`（`initialize.bash` の検査）は `.pi` に替える（D-6）
- `test-readme.bash`: ツール表の必須の行から dsh を外し、`grok / gcloud / glab / bun` を `gcloud / glab / bun` にする。「dsh は」の必須の記述を外す。新しい節 6 で、`.devcontainer` の追跡ファイル（このテスト自身を除く）に、除外対象の導入・mount・起動の文字列が無いことを `git grep -E` で確かめる。パターンは、dsh の導入（`@deepseek-ai/dsh`、`DSH_`、`dsh-settings`、`dsh-cordis`、`dsh plugin`・`dsh web`・`dsh --`、`DeepSeek Harness`）、mount（`${HOME}/.dsh`・`/home/vscode/.dsh` の形と、`.grok` の同じ形）、pnpm の版の固定（`pnpmVersion": "<数字>`）、ポート `3080`、Grok Build の導入と更新（`x.ai/cli`、`grok update`、`-a grok`）、`ccda`（`function claude-alibaba`、`ccda ()`、`-u MAAS_ANTHROPIC_TOKEN`、`maas.aliyuncs`）。README の注記はホストに残るパス（`~/.dsh`）と名前を書くので、パターンは mount や定義の書き方に限る
- `test-shell-tools.bash`: `update()` が飛ばした項目に grok が無いことを確かめる。期待するツールの一覧から grok を外す
- `test-herdr-migration.bash`: 共有リストを使う関数を 3 つにし、期待する unset の一覧・テスト用の環境変数・検査するランチャーから `ccda` と `MAAS_ANTHROPIC_TOKEN` を外す。`zshrc.txt` に `claude-alibaba`・`ccda`・`MAAS_ANTHROPIC_TOKEN`・`maas.aliyuncs` が無いことを `assert_absent` で確かめる
- `tests/scripts/test-docs.bash`: 必須の記述「Cursor と dsh」を「Cursor: スキルの一部が見えない」にし、`AGENTS.md`・`README.md` に `dsh` が無いことを `lacks` で確かめる

## 5. 判断事項

いずれもエージェントが推奨値で決めた。利用者が覆せる。

| ID | 事項 | 決定 | 代替案と採らない理由 |
| --- | --- | --- | --- |
| D-1 | `pnpmVersion` | `"none"` にする | キーを消すと Node feature の既定の `latest` が入る（devcontainers/features の node の README で確認）。リポジトリで pnpm を使うものは dsh だけで、`git grep` でも他に無い。`12.4.1` を残すと、理由の無い固定が残る |
| D-2 | `forwardPorts` | `3080` だけを外し、`8000` は残す | `8000` は dsh と関係が無く、用途の確認はこの子の範囲外 |
| D-3 | `cc_launcher_unsets` の `MAAS_ANTHROPIC_TOKEN` | 外す。README で `env` から削除するよう案内する | 子プロセスに渡さないよう残す案は、撤去した `ccda` の名残を共有リストに残し続ける。移植元も外している。#17 のボードで、外したリストを #21 が引き継ぐと決めている |
| D-4 | 既存環境の dsh・Grok Build | ホストのデータには触れない。コンテナの中の削除手順も設けない | postCreate で `npm uninstall -g @deepseek-ai/dsh` を実行する案は、rebuild で消えるものに手順を増やす。ホストの削除は利用者のデータに触れる |
| D-5 | 再混入の検出 | 既存のテストに検査を足す | 新しいテストファイルは #18 の担当ファイルの一覧に無い。既存のテストは同じ対象（mount、README、zshrc）をすでに読んでいる |
| D-6 | 食い違いの検出の例 | `.pi` の mount を使う | 撤去した `.dsh`・`.grok` を例に使うと、テストが撤去対象の存在を前提にする。`.pi` は撤去しない |
| D-7 | README の dsh の節 | 節ごと削除し、短い注記だけを置く | 移行の手順を詳しく残す案は、dsh を使い続ける人向けで、#17 の方針（除外）と合わない |
| D-8 | Task の分け方 | dsh、Grok Build、ccda、ルートの文書の 4 つにし、各 Task でテストを先に変える | 除外対象ごとに分けると、テストの失敗→成功を Task ごとに確かめられ、レビューもしやすい |
| D-9 | スキルの中の grok・dsh の記述 | 変えない | #17 でスキルは対象外とした。スキルの記述はランタイムの種類の説明で、導入の導線ではない |

## 6. インターフェース

- #19（pi 移行）は、この子の変更が入った `main` を前提に、`install_beforehand.bash` の `STEP_TOTAL`（25）と書き込み確認リストを引き継ぐ
- #21（Claude Code）は、`MAAS_ANTHROPIC_TOKEN` を外した `cc_launcher_unsets` と、`ccda` を外した `test-herdr-migration.bash` を引き継ぐ。共有リストの対象範囲の基準は、引き続き `test-herdr-migration.bash` の `expected_unsets`
- #22（統合）は、9 章の比較表の行を `docs/maatlog-poc-porting.md` にまとめる
- `test-readme.bash` の節 6 の除外のパターンは、後続の子も通す必要がある。後続が除外対象の文字列を `.devcontainer` に足すと失敗する

## 7. 受け入れ条件

- リポジトリ内に dsh・Grok Build・`ccda` / `claude-alibaba` の導入・起動・マウント・ポート・更新・案内が残らない。スキル、`docs/superpowers/` の過去の記録、撤去を説明する README の注記、再混入を検出するテストは除く
- `pixg` と pi-superagents の Grok モデル、`pigod` などの DeepSeek を使う pi ランチャー、`ccdd`・`ccddg`・`ccdu` の設定は変わらない
- 既存環境で postCreate を再実行しても、ホストの `~/.grok`・`~/.dsh` を削除も変更もしない
- 4.6 の検査が、除外対象を戻したときに失敗する
- `bash scripts/check-layout.sh` と `bash .devcontainer/run-tests.bash` は、`main` の既知の失敗（slum03 の resoloop スキルの未同期による `check-layout` と `tests/scripts/test-check-layout.bash`）以外が通る。`uv run pytest tests/skills .agents/skills` が通る

## 8. 検証

子の worktree のルートで実行する。実認証とホストの実設定は使わない。

```bash
bash .devcontainer/run-tests.bash .devcontainer/test-initialize-mounts.bash .devcontainer/test-readme.bash \
  .devcontainer/test-shell-tools.bash .devcontainer/test-herdr-migration.bash tests/scripts/test-docs.bash
bash scripts/check-layout.sh
bash .devcontainer/run-tests.bash
uv run pytest tests/skills .agents/skills
bash -n .devcontainer/install_beforehand.bash
zsh -n .devcontainer/zshrc.txt
```

`check-layout` と `tests/scripts/test-check-layout.bash` は、着手の時点でも slum03 の未同期が残っていれば失敗する。範囲外なので、その 2 件以外が通ることを確かめる。

## 9. 比較表の行

移植元のパスは maatlog-poc の `1f2aadb`、移植先のパスは create-reso-world。#22 がこの表を `docs/maatlog-poc-porting.md` にまとめる。この子の担当ファイルのうち、ここに無い差分は他の子の担当である。

| 移植元 | 移植先 | 判断 | 理由 |
| --- | --- | --- | --- |
| `.devcontainer/dsh-launcher.bash`・`dshccd`・`dshccd.patch.yml`・`dshgo`・`dshgo.patch.yml` | なし | 除外 | dsh は #17 で除外。持ち込まない |
| `.devcontainer/dsh-cordis.patch.yml` | `.devcontainer/dsh-cordis.patch.yml`（削除） | 除外 | 同上。移植先の既存のファイルも撤去する |
| なし | `.devcontainer/dsh-settings.yaml`（削除） | 除外 | 移植先にだけある dsh の雛形 |
| `.devcontainer/install_beforehand.bash` のうち dsh 0.2.0 系の導入（pi-tui の profile、managed block、ランチャーの配置）、Grok Build の導入、`skills add` の `-a grok` | `.devcontainer/install_beforehand.bash` のうち dsh 0.1.5 の導入と定数、書き込み確認リストの `.grok`・`.dsh` | 除外 | 移植元の手順は持ち込まず、移植先の手順も撤去する。他の差分は #19・#21・#22 の担当 |
| `.devcontainer/devcontainer.json` のうち `.grok`・`.dsh` の mount、`pnpmVersion` の固定、`forwardPorts` の `3080` | 同じファイルの同じ箇所 | 適応 | 撤去し、pnpm は `"none"` にする。`name`・dotnet・`remoteEnv`・秘密情報の mount・`--network=host` の差分は、移植先が新しいので既存維持 |
| `.devcontainer/initialize.bash` のうち `.grok`・`.dsh` | 同じ | 適応 | 撤去する。他の差分は移植先が新しいので既存維持 |
| `.devcontainer/zshrc.txt` のうち `grok update`、`cc_launcher_unsets` | 同じファイルの `ccda`、`MAAS_ANTHROPIC_TOKEN`、`grok update`、コメント | 除外 | 撤去する。移植元も `ccda` を撤去済み。他の差分は #19・#21 の担当 |
| `.devcontainer/README.md` のうち dsh・Grok Build の記述 | 同じファイルの dsh の節、ツール表、読み込みの制約、秘密情報 | 適応 | 案内を撤去し、既存環境向けの注記を足す |
| `.devcontainer/docs/herdr-session-cwd-restore.md` | 同じ | 適応 | grok の例示を外す。maatlog 固有のパスは移植先で汎用化済みなので既存維持 |
| なし | `AGENTS.md`・`README.md` | 適応 | 対象エージェントの一覧から dsh を外す |
| `.devcontainer/test-herdr-migration.bash` | 同じ | 適応 | `ccda` の検査を外し、再混入の検査を足す。here-string などの差分は移植先が新しいので既存維持 |
| なし | `.devcontainer/test-initialize-mounts.bash`・`test-readme.bash`・`test-shell-tools.bash`・`tests/scripts/test-docs.bash` | 適応 | 除外対象を必須にしていた検査を新方針にし、再混入の検査を足す |

## 10. リスクと関連作業

- PR #16（`docs/superpowers-document-lifecycle`、未マージ）も `AGENTS.md`・`README.md`・`tests/scripts/test-docs.bash` を変える。2026-10-04 に差分を確かめ、この子が変える行（`AGENTS.md` の 3 行目、`README.md` の 4・47 行目、`test-docs.bash` の 40 行目付近）とは重ならなかった。実装の着手時に最新の `origin/main` から始め、PR #16 が先にマージされていれば、その状態に合わせる
- `test-readme.bash` の節 6 の `git grep` は追跡ファイルだけを見る。新しいファイルは `git add` してから検査する
- `main` の既知の失敗（slum03 の未同期）は範囲外。修正しない

## 11. 計画の検証

Plan の手順は、scratchpad の使い捨ての worktree（`9699e94` から）で試作して確かめた。これは計画の検証で、実装の完了ではない。

- 4 つの Task のそれぞれで、テストだけを先に変えると失敗し（RED）、実装を入れると通る（GREEN）ことを再生して確かめた
- 除外対象を戻す変更（dsh の導入行、`3080`、`grok update`、`ccda` 関数、unset リストの `MAAS_ANTHROPIC_TOKEN`）を入れると、4.6 の検査が失敗することを確かめた
- 最終状態で `bash .devcontainer/run-tests.bash` は 25 本中 24 本が通り、失敗は `main` と同じ `tests/scripts/test-check-layout.bash`（slum03 の未同期）だけだった。`uv run pytest tests/skills .agents/skills` は 267 passed、1 skipped
