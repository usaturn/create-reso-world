# Issue #20 pi ランチャーとサブエージェントの tier の移植 設計

- 対象: usaturn/create-reso-world Issue #20（親 #17。ボードのキー `issue17-maatlog-pi-claude-port`、子のキー `c3-pi-launchers`）
- 基準: `main` の `b2ea728`（Issue 本文の基準 `9699e94` の後に #23 が入った。#23 の変更は `.codex/config.toml`・`README.md`・`tests/scripts/test-agent-config.bash` だけで、この子の担当ファイルとは重ならない）。移植元は usaturn/maatlog-poc の `1f2aadb`（2026-10-04 07:58 UTC に `main` の HEAD が同じであることを確認した）
- 経路: brainstorming の written-spec 経路。変更は既存のランチャーとテストの範囲が決まった修正（bounded）だが、利用者がすべての子 Issue に Spec と Plan を求めているため、書面の Spec を作る
- 状態: draft。利用者は 2026-10-04 に「推奨案で進めて、途中で止めずに PR まで作成して」と指示した。この Spec の判断は、その指示に基づきエージェント（Claude Code、claude-opus-5-5）が推奨値で決めたもので、Spec 自体の明示承認は得ていない
- 作成: 2026-10-04

## 1. 目的

全 pi ランチャー（`pigo`・`pigod`・`pigou`・`piccg`・`piccd`・`piga`・`pigs`・`pigl`・`pixg`）とサブエージェントの provider / model / thinking を移植元に揃える。移植先にしかない `pigou` は維持する。別のランチャーを同時に使っても tier が混線しない仕組み（bwrap の bind によるランチャー別設定）を保ち、Herdr のスクロール履歴を残すために pi を `--tui-mode regular` で起動する。

## 2. 範囲

#20 の「編集してよいファイル」のうち、実際に変更するのは次のファイルである。

- `.devcontainer/pi-superagents-exec.zsh`（`--tui-mode regular`）
- `.devcontainer/pi-superagents/pigs.json`・`pixg.json`（tier）
- `.devcontainer/pigs`・`.devcontainer/pixg`（認証の確認と環境変数の互換）
- `.devcontainer/test-pi-superagents.bash`・`.devcontainer/test-pi-openai-codex.bash`
- `.devcontainer/README.md` のうち「ChatGPT Pro の GPT-6 ランチャー」「SuperGrok / X Premium の Grok 4.7 ランチャー」「pi-superagents のランチャー別 model tier」の節と、新設する「pi の TUI モードと Herdr のスクロール履歴」の節
- この Spec と Plan

編集してよいが変更しないファイル（移植元との差分が、決定済みの配置の違いと `pigou` だけのため）:

- `.devcontainer/pigo`・`pigod`・`pigou`・`piccg`・`piccd`・`piga`・`pigl`（差分は setup スクリプトの案内のパス `.devcontainer/` と `scripts/` の違いだけ）
- `.devcontainer/pi-superagents/` の `pigo`・`pigod`・`pigou`・`piccg`・`piccd`・`piga`・`pigl` の JSON（移植元と同一。`pigou.json` は移植先だけ）
- `.devcontainer/setup_pi_superagents.zsh`・`setup_pi_opencode_go.zsh`・`setup_pi_commandcode_goat.zsh`（差分はパスと `pigou` とコメントの言い回しだけ。4.5 節）
- `.agents/sp-implementer.md`（移植元と同一）

### 範囲外

- `.devcontainer/install_beforehand.bash`。ランチャーの配置と `setup_pi_superagents.zsh --if-absent` の呼び出しは変えない（変える必要もない。4.6 節）
- `.devcontainer/pi-models.json`・`setup_pi.zsh`・`cleanup_pi_mcp.py`（#19）、`.devcontainer/zshrc.txt`（#18・#19・#21）
- 移植元の `test-pi-superagents.bash` にある pi-distill の撤去のテスト（`test_install_script_drops_pi_distill`・`test_remove_distill_*`）。これらは `install_beforehand.bash` の `remove_pi_distill()` を検査するもので、撤去処理とその検査は #19 の担当（#19 は `test-install-beforehand.bash` などで検査する）。この子では持ち込まない
- `.devcontainer/README.md` の「pi-distill の分離」「API トークン」「setup スクリプトを使う場面」の節（pi-distill と DeepInfra の記述を含むため #19、全体の整合は #22）
- `.agents/skills/**`・`.claude/skills/**`・`.pi/APPEND_SYSTEM.md`、ワールドのプロジェクト、ResoLoop、`docs/superpowers/` の既存の文書
- Dev Container の rebuild（#22）。実認証を使う確認

## 3. 現状

移植元 `1f2aadb` と移植先 `b2ea728` の比較（`diff -u`）で、この子の担当ファイルの差分は次のとおり。

| ファイル | 差分 |
| --- | --- |
| `pi-superagents-exec.zsh` | 移植元は `pi --tui-mode regular "$@"` で起動する（Pi 1.0.0 の fullscreen の既定を避ける）。移植先は `pi "$@"`。ほかは setup の案内のパスだけ |
| `pi-superagents/pigs.json` | 移植元の cheap は `opencode-go/deepseek-v4.1-flash`（`max`）、移植先は `openai-codex/gpt-6-luna`（`xhigh`） |
| `pi-superagents/pixg.json` | 移植元の cheap と balanced は `opencode-go/deepseek-v4.1-flash`（`max`）、移植先は cheap が `openai-codex/gpt-6-luna`（`xhigh`）、balanced が `xai/grok-4.7`（`high`）。max は同じ |
| `pigs` | 移植元は Codex OAuth の確認に加えて、`OPENCODE_GO_API_KEY` から `OPENCODE_API_KEY` への互換の export を持つ |
| `pixg` | 移植元は xAI OAuth だけを確認し、Codex OAuth の確認をやめ、`OPENCODE_GO_API_KEY` の互換の export を持つ |
| 他のランチャー・setup スクリプト | setup の案内のパス（`scripts/` と `.devcontainer/`）、`pigou` の有無、コメントの言い回しだけ |
| `test-pi-superagents.bash` | 移植元は上記の変更の検査（`--tui-mode regular`、実際の argv と dry-run の argv の一致、`pigs` の子プロセスへの API キーの引き継ぎ、tier 表）、setup のヘルパの更新の検査、pi-distill の撤去の検査を持ち、`pigou` の検査が無い。移植先は PR #15 で `grep -q` を here-string で受ける形に直している |
| `test-pi-openai-codex.bash` | 移植元は `pigs` の cheap の行を外し、`--tui-mode regular` を期待し、install の検査を全ランチャーに広げ、ライブ確認の Pi の最小版を 0.99.1 にしている。移植先は here-string の形 |

確認した事実:

- 9 本のランチャーはすべて `pi_superagents_exec` を通して pi を起動する。ヘルパの 1 か所で全ランチャーに `--tui-mode regular` が付く
- 導入済みの Pi 1.0.2 の `dist/cli/args.js` は `--tui-mode` の値を見つけるたびに上書きする（後の指定が勝つ）。`--tui-mode` は 1.0.0 より前に実験的な fullscreen とともに入っており、1.0.0 で既定が fullscreen になった（Pi の CHANGELOG）
- Pi の CHANGELOG では、GPT-6.1 Sol（`gpt-6.1-sol`）は 0.99.1 で追加された。移植先の README とライブ確認の「0.87.1 以上」は、`pigs`・`piga`・`pigl` の balanced / max が使う GPT-6.1 Sol には足りない
- `setup_pi_superagents.zsh` は `--if-absent` でも共通ヘルパを毎回 `install -m 0644` で置き直す。既存環境は `--if-absent` の再実行でヘルパを更新できる
- `install_beforehand.bash` は、ランチャーを「Placing the launchers」の手順で `~/.local/bin` に置き、ヘルパは次の「Writing the pi-superagents launcher configs」の手順で `setup_pi_superagents.zsh --if-absent` が置く。#18（PR #24、未マージ）の後は、この次の手順が dsh から「Installing the shared skills」に変わる
- CI（`.github/workflows/ci.yml`）は `bubblewrap` を入れてから `run-tests.bash` を実行する

## 4. 設計

### 4.1 `--tui-mode regular`

`pi_superagents_exec` の argv の `pi` の直後に `--tui-mode regular` を置き、その後にランチャーとユーザの引数を続ける。

```zsh
        # Pi 1.0.0 の fullscreen 既定を避け、Herdr の通常のスクロール履歴を残す。
        pi --tui-mode regular "$@"
```

- dry-run（`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1`）も実際の起動も同じ `args_` 配列を使うので、表示と exec の argv は一致する。これをテストで固定する（4.7 節）
- ユーザの追加引数はこの後ろに並ぶため、`--tui-mode fullscreen` を渡せば Pi の解析で後の指定が勝つ。素の `pi` と `settings.json` には影響しない

### 4.2 tier

`pigs.json` の cheap を `{"model": "opencode-go/deepseek-v4.1-flash", "thinking": "max"}` にする。`pixg.json` の cheap と balanced を同じ値にする。他のランチャーの tier は移植元と同一なので変えない。`pigou.json`（全 tier が `opencode-go/union-alpha` の `max`）は維持する。

変更後の tier 表（model / thinking）:

| launcher | cheap | balanced | max |
| --- | --- | --- | --- |
| `pigo` | `opencode-go/muse-spark-1.3-contributor` / max | `opencode-go/muse-spark-1.3-contributor` / max | `opencode-go/deepseek-v4.1-flash` / max |
| `pigod` | `opencode-go/muse-spark-1.3-contributor` / max | `opencode-go/deepseek-v4.1-flash` / max | `opencode-go/deepseek-v4.1-flash` / max |
| `pigou` | `opencode-go/union-alpha` / max | `opencode-go/union-alpha` / max | `opencode-go/union-alpha` / max |
| `piccg` | `commandcode/meta/muse-spark-1.3-contributor` / max | `commandcode/meta/muse-spark-1.3-contributor` / max | `commandcode/deepseek/deepseek-v4.1-flash` / max |
| `piccd` | `commandcode/meta/muse-spark-1.3-contributor` / max | `commandcode/deepseek/deepseek-v4.1-flash` / max | `commandcode/deepseek/deepseek-v4.1-flash` / max |
| `piga` | `openai-codex/gpt-6-luna` / xhigh | `openai-codex/gpt-6.1-sol` / xhigh | `openai-codex/gpt-6-astra` / max |
| `pigs` | `opencode-go/deepseek-v4.1-flash` / max | `openai-codex/gpt-6.1-sol` / xhigh | `openai-codex/gpt-6.1-sol` / max |
| `pigl` | `openai-codex/gpt-6-luna` / xhigh | `openai-codex/gpt-6.1-sol` / xhigh | `openai-codex/gpt-6.1-sol` / xhigh |
| `pixg` | `opencode-go/deepseek-v4.1-flash` / max | `opencode-go/deepseek-v4.1-flash` / max | `xai/grok-4.7` / xhigh |

### 4.3 認証の確認と環境変数の互換

- `pigs`: 親 Pi と balanced / max は Codex を使うので、`pi_openai_codex_require_oauth` を維持する。cheap の子 Pi が使う opencode-go の資格情報は `auth.json` の api_key か `OPENCODE_API_KEY` で解決されるため、`pigo`・`pigod` と同じく起動前には確認しない
- `pixg`: `pi_xai_require_oauth` だけを確認し、`pi_openai_codex_require_oauth` の呼び出しとそのコメントを削除する（Codex を使う tier が無くなるため）
- 両方に、`pigo`・`pigod`・`pigou` と同じ互換の処理を足す。`OPENCODE_API_KEY` が空で `OPENCODE_GO_API_KEY` が設定されていれば `OPENCODE_API_KEY` に export する。`exec bwrap` → `pi` → 子 Pi と環境変数が引き継がれる
- 認証が無いときは従来どおり停止し、`/login openai-codex`（`pigs`）または `/login xai`（`pixg`）を案内する。設定が無いときの案内は `zsh .devcontainer/setup_pi_superagents.zsh` のまま

### 4.4 ランチャー別設定と同時起動

bwrap の bind（`~/.pi/agent/extensions/subagent.d/<launcher>` → `~/.pi/agent/extensions/subagent`）、`HOME` 基準の bind 先、設定や bwrap が無いときの停止は変えない。同時起動で tier が混線しないことは、各ランチャーが自分の設定ディレクトリを bind することの既存の検査で保つ。

### 4.5 setup スクリプト

3 本の setup スクリプトは変更しない。

- 配置は `.devcontainer/` に残すと決定済みなので、移植元の `scripts/` や `${0:A:h}/../.devcontainer` への書き換えは持ち込まない
- `pigou` の扱い（`setup_pi_opencode_go.zsh` の `LAUNCHER_NAMES`、`setup_pi_superagents.zsh` の `LAUNCHERS`）は維持する
- `setup_pi_commandcode_goat.zsh` のコメントの「正本」→「元データ」の言い換えは、動作に関係せず、移植先の規約（`AGENTS.md` は「正本」を使う）にも合わないので持ち込まない
- 冪等性、`--if-absent` での既存の設定の保持、明示的な実行でのバックアップ（同じ秒の衝突では連番）は既存の実装と検査のままでよい。`--if-absent` でもヘルパを最新にすることを検査で固定する（4.7 節）

### 4.6 既存環境への反映

- Dev Container の rebuild: `install_beforehand.bash` がランチャーを毎回上書きし、`setup_pi_superagents.zsh --if-absent` がヘルパを更新する。tier の設定は既存を保持するため、`pigs`・`pixg` の新しい tier は反映されない
- 既存環境では、リポジトリのルートで `zsh .devcontainer/setup_pi_superagents.zsh` を実行して tier の設定を置き直す（変更のある設定はバックアップされる）。このスクリプトはヘルパも更新する。`pigs`・`pixg` のランチャー自体は rebuild で置き直されるので、rebuild しない場合は `install -m 0755 .devcontainer/pigs ~/.local/bin/pigs`（`pixg` も同様）で置き直す
- この手順を README の新しい節に書く。`install_beforehand.bash` の変更は不要なので #22 に引き継ぐ事項は無い。#22 の rebuild の確認項目として、ランチャーの dry-run の argv に `--tui-mode regular` が出ることを渡す

### 4.7 テスト

移植元の検査を、移植先の書き方（here-string、`pigou` の維持、`.devcontainer/` のパス）に合わせて取り込む。

`test-pi-superagents.bash`:

- `test_dry_run_emits_bwrap_command`: pi の引数が `--tui-mode regular --provider opencode-go --model muse-spark-1.3-contributor` と完全一致することを足す
- `test_actual_and_dry_run_argv_match`（新規）: fake bwrap が記録した実際の argv と、dry-run の argv（先頭の `bwrap` を除く）が、空白を含む引数でも一致する
- `test_tier_tables`: `pigs`・`pixg` の行を 4.2 節の表に合わせる
- `write_pixg_auth` を削除し、`pixg` を使う検査は `write_xai_auth` を使う
- `test_launchers_forward_user_arguments` を `test_launchers_select_regular_and_forward_user_arguments` に置き換える。9 本すべてで、pi の引数が `--tui-mode regular`、provider、model、（`piccg`・`piccd` は `--models`）、thinking、ユーザの引数（`--resume --session 'session with spaces.jsonl' -- 'message with spaces'`）の順に完全一致する
- `test_opencode_key_reaches_child_process`（新規）: `pigs` と `pixg` を、環境変数を表示する fake bwrap で実際に起動し（`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=0`）、`OPENCODE_API_KEY` の値が「未設定 + 旧名あり → 旧名の値」「空 + 旧名あり → 旧名の値」「両方あり → 新名の値」「両方なし → 未設定」になる
- `test_pixg_oauth_guidance`: xAI OAuth だけで起動できることを確かめ、Codex OAuth が無いと止まる検査を削除する
- `test_setup_places_all_launcher_configs`: 置かれたヘルパがリポジトリのものとバイト単位で一致する
- `test_setup_if_absent_preserves_user_edits`: 古いヘルパを置いてから `--if-absent` を実行し、設定は保持され、ヘルパは最新になる
- `test_readme_documents_the_mechanism`: README が `--tui-mode regular` を説明していることを足す
- `pigou` の検査、`test_run_launcher_ignores_external_pi_coding_agent_dir`（`pigou` 版）は維持する

`test-pi-openai-codex.bash`:

- `pigs` の cheap の行を外す（Codex の tier の検査なので、opencode-go の cheap は `test-pi-superagents.bash` の tier 表で検査する）
- 期待する pi の引数の先頭に `--tui-mode regular` を足す
- `test_install_places_all_three_launchers` を `test_install_places_all_launchers_with_regular_mode` に置き換える。`install_beforehand.bash` の「Placing the launchers」から、その後の「Writing the pi-superagents launcher configs」の手順までを切り出して一時 HOME で実行し、ヘルパが最新であること、9 本すべてが実行可能でリポジトリと一致し、置かれた場所から dry-run で起動すると pi の引数が `--tui-mode regular` で始まり、最後がユーザの引数になることを確かめる。切り出しの終わりは「この 2 つ以外の次の `step`」にし、#18 で後続の手順が変わっても壊れないようにする
- ライブ確認（`PI_CODEX_LIVE_CHECK=1`）の Pi の最小版を 0.99.1 にする

## 5. 判断事項

| ID | 判断 | 代替案 | 理由 |
| --- | --- | --- | --- |
| D-1 | 基準を最新の `main`（`b2ea728`）にする | Issue 本文の `9699e94` | #17 の運用ルールは最新の `origin/main` から worktree を作るとしている。#23 の差分は担当ファイルと重ならない |
| D-2 | `--tui-mode regular` を共通ヘルパに 1 か所だけ置く | 各ランチャーに書く。`settings.json` の `tuiMode` | ヘルパなら 9 本に漏れなく効き、移植元と同じ。`settings.json` は利用者と #19 の担当で、素の `pi` にも効いてしまう |
| D-3 | `--tui-mode regular` をユーザの引数より前に置く | 後ろに置く | 利用者が `--tui-mode fullscreen` を渡したときに、Pi の後勝ちの解析でその指定を優先できる |
| D-4 | `pigs`・`pixg` の tier を移植元に揃える | 移植先の Luna を残す | #20 の受け入れ条件 |
| D-5 | `pigs`・`pixg` で opencode-go の資格情報を起動前に確認しない | `auth.json` か `OPENCODE_API_KEY` を確認する | 移植元と、opencode-go を使う既存の `pigo`・`pigod` に合わせる。cheap / balanced の子 Pi だけが使い、資格情報の解決は Pi に任せている |
| D-6 | `OPENCODE_GO_API_KEY` の互換を `pigs` と `pixg` の両方に入れ、両方を検査する | 移植元と同じく `pigs` だけを検査する | 受け入れ条件が子プロセスまでの引き継ぎを求めており、`pixg` にも同じ処理を入れるため |
| D-7 | setup スクリプトを変更しない | 移植元の言い回しやパスに合わせる | 配置は決定済み、`pigou` は維持、言い回しは移植先の規約に合わない |
| D-8 | pi-distill の撤去の検査を持ち込まない | `test-pi-superagents.bash` に持ち込む | 検査対象の `remove_pi_distill()` は #19 が `install_beforehand.bash` に入れるかを決める。先に検査だけ入れるとこの子のテストが失敗する |
| D-9 | ライブ確認と README の Pi の最小版を 0.99.1 にする | 0.87.1 のまま | GPT-6.1 Sol は Pi 0.99.1 で追加された（Pi の CHANGELOG）。移植元も 0.99.1 |
| D-10 | install の検査の切り出しの終わりを「次の別の `step`」にする | 移植元の「Installing DeepSeek Harness」、移植先の「Writing the pi-superagents」 | ヘルパの配置は「Writing」の手順にあるので含める必要がある。dsh の手順は #18 で消える |
| D-11 | `install_beforehand.bash` を変えない | ヘルパをランチャーと同じ手順で置く | `setup_pi_superagents.zsh --if-absent` が毎回ヘルパを更新するので不要。#20 の編集範囲外でもある |
| D-12 | README の新しい節は 9 本（`pigou` を含む）を挙げ、パスは `.devcontainer/` にする | 移植元の文面のまま | 移植先の構成に合わせる |

## 6. インターフェース

- `install_beforehand.bash` からの呼び出し（各ランチャーの `install -m 0755`、`zsh .devcontainer/setup_pi_superagents.zsh --if-absent`）のパスと引数は変えない
- ランチャー別設定 `~/.pi/agent/extensions/subagent.d/<launcher>/config.json` の配置と bwrap の bind は変えない
- `PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` の出力の形式（1 行 1 要素の argv）は変えない。pi の引数の先頭に `--tui-mode` と `regular` の 2 行が増える
- #22 は 9 章の比較表の行を `docs/maatlog-poc-porting.md` にまとめ、rebuild で 4.6 節の確認を行う
- #19 は pi-distill の撤去を検査する（D-8）

## 7. 受け入れ条件

- 各ランチャーの provider / model / thinking と cheap / balanced / max の tier が移植元と一致する（`pigou` は維持）。`pigs` の cheap と `pixg` の cheap・balanced は `opencode-go/deepseek-v4.1-flash`（`max`）
- `pigs` は Codex OAuth を確認する。`pixg` は xAI OAuth だけを確認し、Codex OAuth が無くても起動する
- `OPENCODE_GO_API_KEY` から `OPENCODE_API_KEY` への互換の引き継ぎが、`pigs` と `pixg` の子プロセスまで届く
- 9 本すべてで pi の起動に `--tui-mode regular` が付き、実際の argv と dry-run の argv が一致する
- `setup_pi_superagents.zsh` は冪等で、`--if-absent` は既存の設定を保持してヘルパを更新し、明示的な実行では変更のある設定をバックアップする
- 認証や設定が無いときは停止し、正しいログイン手順か `.devcontainer/` の setup スクリプトを案内する
- README が新しい tier・認証・`--tui-mode regular`・既存環境の更新手順を説明する

## 8. 検証

worktree のルートで実行する。実認証とホストの `~/.pi` は使わない（fake の bwrap と一時 HOME）。

- 個別: `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-pi-openai-codex.bash` が PASS
- 全体: `bash .devcontainer/run-tests.bash` は、`main` で既知の失敗（slum03 の resoloop スキルの未同期による `tests/scripts/test-check-layout.bash`）以外が PASS
- `bash scripts/check-layout.sh` は slum03 の既知の失敗だけ
- `uv run pytest tests/skills .agents/skills` が通る（`main` の基準は 267 passed / 1 skipped）
- 変更前のテストを先に変えたとき、`--tui-mode`・tier・`pixg` の認証・互換の検査が失敗する（RED）ことを確かめてから実装する

## 9. 比較表の行

移植元のパスは maatlog-poc の `1f2aadb`、移植先のパスは create-reso-world。#22 がこの表を `docs/maatlog-poc-porting.md` にまとめる。

| 移植元 | 移植先 | 判断 | 理由 |
| --- | --- | --- | --- |
| `.devcontainer/pi-superagents-exec.zsh` | 同じ | 移植 | `pi --tui-mode regular` で起動する。setup の案内のパスは `.devcontainer/` のまま |
| `.devcontainer/pi-superagents/pigs.json`・`pixg.json` | 同じ | 移植 | cheap（`pixg` は balanced も）を `opencode-go/deepseek-v4.1-flash` の `max` にする |
| `.devcontainer/pi-superagents/pigo.json`・`pigod.json`・`piccg.json`・`piccd.json`・`piga.json`・`pigl.json` | 同じ | 既存維持 | 移植元と同一 |
| なし | `.devcontainer/pi-superagents/pigou.json` | 既存維持 | 移植先だけのランチャー |
| `.devcontainer/pigs` | 同じ | 移植 | `OPENCODE_GO_API_KEY` の互換を足す。Codex OAuth の確認は維持。案内のパスは `.devcontainer/` |
| `.devcontainer/pixg` | 同じ | 移植 | Codex OAuth の確認をやめ、互換を足す。案内のパスは `.devcontainer/` |
| `.devcontainer/pigo`・`pigod`・`piccg`・`piccd`・`piga`・`pigl` | 同じ | 既存維持 | 差分は setup の案内のパスだけ。`.devcontainer/` に残す決定に合わせる |
| なし | `.devcontainer/pigou` | 既存維持 | 移植先だけのランチャー。`--tui-mode regular` は共通ヘルパで付く |
| `scripts/setup_pi_superagents.zsh`・`setup_pi_opencode_go.zsh`・`setup_pi_commandcode_goat.zsh` | `.devcontainer/` の同名 | 適応 | 配置は `.devcontainer/` に残す。`pigou` を維持し、コメントの言い回しは移植先のまま |
| `.agents/sp-implementer.md` | 同じ | 既存維持 | 移植元と同一 |
| `.devcontainer/test-pi-superagents.bash` | 同じ | 適応 | `--tui-mode`・argv の一致・tier・`pixg` の認証・互換の引き継ぎ・ヘルパの更新の検査を取り込む。here-string と `pigou` の検査は維持。pi-distill の検査は #19 |
| `.devcontainer/test-pi-openai-codex.bash` | 同じ | 適応 | `--tui-mode`、全ランチャーの install の検査、Pi 0.99.1 を取り込む。install の切り出しの終わりは移植先の手順に合わせる |
| `.devcontainer/README.md` の GPT-6・Grok 4.7・TUI モード・tier の節 | 同じファイルの同じ節 | 適応 | tier・認証・Pi の最小版・`--tui-mode regular` の節を移植し、`pigou` と `.devcontainer/` のパスに合わせる。既存環境の更新手順を足す |

## 10. リスクと関連作業

- `pigs`・`pixg` の cheap（`pixg` は balanced も）は opencode-go の資格情報が無い環境では子 Pi が認証エラーになる。起動前には確認しない（D-5）ので、README で `setup_pi_opencode_go.zsh` の実行を案内する
- 既存環境は rebuild だけでは tier が変わらない（4.6 節）。README に手順を書き、#22 の rebuild の確認で扱う
- #18（PR #24）とは担当ファイルが重ならない。`test-pi-openai-codex.bash` の install の切り出しは、#18 の後の手順の並びでも動く形にする（D-10）
- #19 が `test-pi-superagents.bash` の `test_install_script_*` が見る `install_beforehand.bash` の pi-subagents の手順を変える場合は、#19 の側でそれらの検査を合わせる必要がある（この子は変えない）
