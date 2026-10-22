# Issue #234: .devcontainer と tools/devenv_migration のテストを、新しい採用基準で減らす

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/234（親 #228、ボード `test-reduction-board`、子のキー `devcontainer-tests`。先行 #229 は completed で close、PR #240 は `main` の `481a047` にマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-23-create-reso-world-issue234-devcontainer-tests.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-234-devcontainer-tests`（branch `feat/issue-234-devcontainer-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-23、利用者が次のとおり指示した

  ```text
  /issue-to-pr #234 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #234`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う。この指示は rebuild の実施を含まない（rebuild は利用者が行う）
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`、`assign = {}`、`template = .devcontainer/agent-runner.toml`、`config = null`（いずれも既定の適用。利用者の指定は無い）。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー・修正の確認が `self`（いずれも既定の適用で、`fallback` なし）
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形の既定の適用。利用者の指定ではない）
- 予約: `refs/heads/agent-claims/issue-234` = `6e64a16a1eb04e960dcde616c065f77ce8269b99`（https://github.com/usaturn/create-reso-world/issues/234#issuecomment-6345076660）
- 基準: `origin/main` の `481a047`（2026-10-22 UTC）。#234 の本文の基準値は `5a6b096` で、同じ計測で pytest 419 件・bash 18 本（437 件）・5,778 行を `481a047` で再計測して一致した

## 意図

Dev Container のテスト（`.devcontainer/test-*.bash`、`.devcontainer/tests/`）と `tools/devenv_migration` のテストを、`AGENTS.md` の「テストの採用基準」（F・F∩S・L・S・D）で 1 つずつ分類し、S（F∩S を含む）と D の代表だけを残す。使われなくなった経路（済んだ一度きりの移行）は、使われていないことを確かめたものに限り、コードとテストを一緒に撤去する。結果として、この領域のテストが減り、棚卸しの表に全テストの分類と理由が残る。

## 範囲と禁止

Issue #234 の「範囲と禁止」のとおり。変えるのは次だけ。

- `.devcontainer/test-*.bash`（`test-install-meshy.bash` を除く）、`.devcontainer/tests/`、`tools/devenv_migration/tests/`
- 撤去する経路のコード: `.devcontainer/install_beforehand.bash`（pi の節だけ）、`.devcontainer/pi-provider-setup.py`（`settings_update` と `--settings-check`・`--settings-clean`）
- 撤去した経路を説明する `.devcontainer/README.md`・`docs/` の行（`.devcontainer/README.md` の「テストの実行」の節、`README.md` の「テスト」の節、`pyproject.toml`、ルートの `conftest.py`、`tools/test_support/`、`.devcontainer/run-tests.bash` は `integration` の担当で変えない）
- この Spec と Plan

変えないもの: Meshy の導入と検査、mount の定義（`devcontainer.json`・`mounts.bash`・`initialize.bash`）、`agent-runner*.toml`、`AGENTS.md`、ほかの領域のテストとコード（`scripts/setup_pi_superagents.zsh` の警告を含む。#235 の担当）。ランチャーの名前・引数と、撤去しない postCreate の段は変えない。

## 決定記録

各項目: 選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件。

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- |
| D-234-1 | 済んだ一度きりの移行（pi-subagents の置換後片付け、pi-mcp-adapter・pi-distill・pi-lens の撤去、`pi-provider-setup.py` の settings の preflight と clean）を、コードとテストごと撤去する。`install_pi_extensions` は `@teelicht/pi-superagents` の導入と導入後の登録確認だけを残す | 撤去せずテストを L として消す（掃除が残り、旧拡張を再導入する経路が無いのに処理だけが動く）。#234 の手がかりが約 475 行を撤去候補にしている | #228 の決定 5。今の環境に旧 4 パッケージは無く（下の「撤去の根拠」）、呼び出し元は `install_beforehand.bash` だけで、`~/.pi` の旧登録を再導入する導入はこのリポジトリに無い | 根拠が確かめられた範囲に限る。他のコンテナの未 rebuild の旧版が再登録する経路は未確認で、既知の制限に書く |
| D-234-2 | `test_pi_agent_paths.py` を消し、残す 7 件を `test_pi_provider_setup.py` に移す | 7 件を `test_pi_agent_paths.py` に残す | 兄弟ファイルからの import が無くなり、`pyproject.toml` の `pythonpath` の 2 つ目（`tools/devenv_migration/tests`）が不要になる。同じ `pi-provider-setup.py` を試すテストが 1 ファイルにまとまる | `pyproject.toml` は `integration` の担当なので、#228 にコメントして依頼する（この子では変えない） |
| D-234-3 | `test-pi-migrations.bash`（pytest の二重実行）、`test_pi_installer_isolation.py`・`.devcontainer/tests/pi-launcher-install.bash`・`test-pi-openai-codex.bash`（互いを安全に動かすためだけのもの）を消す | `test-pi-openai-codex.bash` の S を探す | 手がかりのとおり。ランチャーの配置漏れ・OAuth 未設定は、初回の利用で `command not found` や案内つきの exit 1 として現れる（L）。`~` の展開は `test_pi_provider_setup.py` に残す代表が受け持つ | – |
| D-234-4 | `test-herdr-status.bash`・`test-herdr-agent-task.bash` を消す（全場面が L）。`test-herdr-migration.bash` は F∩S（unset の一覧・POLLUTED_ の隔離・資格情報の送り先）と session.json 修復の S を残し、縮める | 3 本とも残す | 残りはサイドバーの表示と、引数の誤りで 64 になる終了コードだけで、壊れても作業の結果は変わらない | F∩S は消さない（Issue の指定） |
| D-234-5 | F∩S として残す: mount の一覧（`test-initialize-mounts.bash`）、unset する環境変数の一覧（`test-herdr-migration.bash`）、`/workspaces/reso-world`・`/home/vscode` を書かない検査（`test-readme.bash`・`test-shell-tools.bash`）、削除の既定値（`test-cleanup-workspace.bash`）、資格情報の送り先 | 絶対パスの検査と削除の既定値を F として消す | #229 の申し送り 1。worktree や一時 HOME から親の checkout や実際の HOME を操作する損害は、エラーにならずに残る | 防ぐ損害と理由をテストのコメントに書く |
| D-234-6 | 守りの重さが高の S で代表に絞ったものは、使い捨てのコピーで守りを壊し、残したテストが失敗することを 1 回ずつ確かめる | 確かめない | Issue の受け入れ | 失敗しなければ、そのテストは守りになっていないので直す |
| D-234-7 | S か L か迷うものは残し、棚卸しの表に「迷い」と書く | 件数のために消す | #228 の決定 6。数を合わせるために気付けない損害を防ぐテストを消さない | `integration` の一覧の先頭に並ぶ |
| D-234-8 | 実装は inline の `superpowers:executing-plans` を基本とし、独立した 4 つのファイル群（pi の Python 設定、pi の導入と移行、herdr、その他の bash）は、新しい文脈のサブエージェントに同期で任せる | `implement_task.py` で runner の担当に依頼する（`self` が true なので使わない） | 4 群は担当ファイルが分かれており、棚卸しの分析も同じ分け方で済んでいる。`install_beforehand.bash` を触るのは pi の導入と移行の群だけ | 担当ファイルの外を変えない。全体のテストを同時に回さない（#218） |

## 撤去の根拠（#228 の「撤去」の確かめ）

| 撤去する経路 | 変更するファイル |
| --- | --- |
| pi-subagents → pi-superagents の置換の後片付け（旧登録の検出、`pi remove npm:pi-subagents`、マニフェストの残骸掃除、残存検査） | `.devcontainer/install_beforehand.bash` の `install_pi_extensions` |
| pi-mcp-adapter の撤去と settings の `-builtin:mcp` の除去 | 同 step `Removing npm:pi-mcp-adapter …` 全体 |
| pi-distill（と単独登録の `pi-extensions-tool-display`・`pi-extensions-i18n`）の撤去 | 同 step `Removing npm:pi-distill …` 全体 |
| pi-lens の撤去 | 同 step `Removing npm:pi-lens …` 全体 |
| settings の preflight と clean | `install_beforehand.bash` の `--settings-check` 呼び出しと、`pi-provider-setup.py` の `settings_update`・`--settings-check`・`--settings-clean`（`--agent-dir` と `setup` は `scripts/setup_pi*.zsh` が呼ぶので残す） |
| step 数 | `STEP_TOTAL` を 32 から 29 にする（`install_pi_extensions` の step は残り、撤去は 3 step） |

使われていない根拠:

1. 今の環境に対象が無い: `~/.pi/agent/settings.json` の `packages` は 8 件で旧 4 パッケージを含まず、`~/.pi/agent/npm/package.json`・`package-lock.json` にも `pi-subagents`・`pi-mcp-adapter`・`pi-distill`・`pi-lens` の文字列が無い（2026-10-23 に grep で確認。`extensions` は空）
2. 呼び出し元: `remove_pi_mcp_adapter`・`remove_pi_distill`・`remove_pi_lens`・`--settings-check`・`--settings-clean` を呼ぶのは `install_beforehand.bash` だけ（`git grep`）。`install_pi_extensions` を取り出すのは `test-pi-superagents.bash` だけ
3. 文書・雛形・設定からの参照: `.devcontainer/README.md` の説明だけ（同じ変更で直す）。`docs/maatlog-poc-porting.md` は凍結した移植の記録なので変えない。`devcontainer.json`・`agent-runner*.toml` に参照は無い
4. step 数への依存: `STEP_TOTAL` と step の数の一致を見るのは `test-verify-resonite-tooling.bash`（この子で消す L）だけ。ほかのテストは step の見出しを参照するだけで番号に依存しない
5. 共有 `~/.pi` への再導入: このリポジトリの導入は旧 4 パッケージを入れない。

### 既知の制限

- ホスト側で旧版のリポジトリから rebuild していないコンテナ（agent-workspace・xrift-poc など）があれば、その rebuild が旧パッケージを再登録しうる。撤去後はこのリポジトリの rebuild で自動掃除されない。残っていたら手で `pi remove npm:<名前>` する（`.devcontainer/README.md` に残す）。`.devcontainer/README.md` が他のリポジトリの導入の停止を記録している（xrift-poc#16・create-reso-world#117）ので、再導入は起きない見込みだが、ホストの状態は確かめられない
- `herdr-git-status.bash` の `git status` に `--no-optional-locks` が無い（F3 の観察。この子の範囲外、変えない）
- `cleanup-workspace.bash` 本体の安全条件（未コミット変更のある worktree を消さない、使用中を消さない）を確かめるテストが、領域内に無い（F4 の観察。足さない）

## 処置の概要と見積もり

| 群 | 前（件 / 行） | 後（件 / 行、見積もり） | 内容 |
| --- | --- | --- | --- |
| pi の Python 設定（F1） | 359 / 1,505 | 38 / 約 720 | agent_paths 146→7（`test_pi_provider_setup.py` へ移す）、provider_setup 80→13、vertex 133→18 |
| pi の導入と移行（F2） | 63 / 2,161 | 2 / 約 490 | 撤去する経路のテストと、互いを安全に動かすためのテストを消す。`test-pi-superagents.bash` は 46 場面から 9 つの関数に |
| herdr（F3） | 3 / 1,225 | 1 / 約 425（実測 435） | 2 本を消し、`test-herdr-migration.bash` を縮める |
| その他の bash（F4） | 12 / 887 | 10 / 約 385 | 2 本を消し、残りを S の場面に絞る |
| 合計 | 437 / 5,778 | 約 51 / 約 2,020 | 件数 約 12%、行数 約 35% |

件数は pytest の件数と bash の 1 本を 1 件と数える計測（#228 の「計測」）に合わせた。行数は実装後に実測して「計測の結果」に書く。

## 検証

- 領域: `uv run --locked pytest tools/devenv_migration`、`bash .devcontainer/run-tests.bash .devcontainer/test-*.bash`
- 全体: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`
- 重さが高の守りの確認（D-234-6）: 各棚卸しの「壊し方案」から、重さが高の守りを使い捨てのコピー（`/tmp` に `mktemp -d`）で壊し、残したテストが失敗することを 1 回ずつ確かめる。結果を「計測の結果」に書く
- 削除したファイルへの参照: `git grep` で、消したテストのファイル名と撤去した関数名が、文書・スクリプト・設定に残っていないことを確かめる（`docs/maatlog-poc-porting.md` などの凍結した記録を除く）

## rebuild の後の確認（利用者が rebuild した後に実施し、結果を Issue #234 に記録する）

1. rebuild の前に `~/.pi/agent/settings.json` と `~/.pi/agent/npm/package.json`・`package-lock.json` を `cp -p` で退避する
2. rebuild の後、postCreate のログの最後が `[29/29]` になる
3. `pi list` に `npm:@teelicht/pi-superagents` と `npm:@plannotator/pi-extension` がある
4. `settings.json` が退避した版と `packages`・`extensions`・`theme` で一致する
5. `ls ~/.pi/agent/npm/node_modules` に `pi-subagents`・`pi-mcp-adapter`・`pi-distill`・`pi-lens` が無い
6. `PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 pigo` が `bwrap` の argv を出す

## 棚卸しの表

全テスト（関数・クラス・parametrize の群・bash の場面）の分類と理由。F1〜F4 は分析の分担で、同じ群の記録をそのまま載せる（分析時点の記述。処置は上の決定記録と合わせて読む）。分類の記号は F 固定値 / F∩S / L 気付ける / S 気付けない損害 / D 重複 / 撤去 / 迷い。

### 棚卸し F1: pi の Python 設定テスト 3 ファイル（読み取り専用の分析）

対象: `tools/devenv_migration/tests/` の `test_pi_agent_paths.py`（146）・`test_pi_provider_setup.py`（80）・`test_pi_vertex_launchers.py`（133）。計 359 件・1,505 行。
対象コード: `.devcontainer/pi-provider-setup.py`（`--agent-dir`・`--settings-check`・`--settings-clean`・`setup`）、`.devcontainer/pi-superagents-exec.zsh`、`pigemf`/`pigemp`/`pigema`（名前とモデルだけが違う）、`scripts/setup_pi*.zsh`。

#### 前提（F2 との境界）

- `--settings-clean` の呼び出し元は `install_beforehand.bash:439`（pi-mcp-adapter の撤去）だけ。F2 が撤去するなら、`pi-provider-setup.py` の clean 経路も撤去対象。`--settings-check`（:288・:396）と `--agent-dir`（`scripts/setup_pi*.zsh` 3 本）は残る。
- `test_pi_agent_paths.py` は `test_pi_mcp_adapter_migration.py` から `INSTALL_SCRIPT, ROOT, MigrationHarness, _harness, _invalid_settings, _snapshot, isolated_command` を、`test_pi_provider_setup.py` から `Harness, SETUPS` を import する。F2 が前者を消すと、残す分は `ROOT`・`_snapshot`・`isolated_command` を自分で持つ必要がある。
- 提案: `test_pi_agent_paths.py` の残る 7 件は `test_pi_provider_setup.py`（同じ `pi-provider-setup.py` を試す）へ移して `test_pi_agent_paths.py` を消す。すると兄弟 import が無くなり、`pyproject.toml` の `pythonpath` の 2 つ目は `integration` が外せる（その旨を親にコメント）。
- `--if-absent` の保持は `test-pi-superagents.bash:644-653,683-` にあるので、vertex 側の同種の 1 件は D。

#### (1) 棚卸しの表

分類: F / F∩S / L / S / D / 撤去 / 迷い。重さ: 高 = 秘密情報の漏れ・データ消失・誤った対象への破壊的操作、中 = 誤った結果、低 = 表示など。

##### test_pi_agent_paths.py（146 → 7）

| テスト群 | 現件数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_path_probe_isolation_protects_storage_outside_its_fixture` | 1 | L | テストの補助（bwrap の隔離）自体の検査。壊れてもプロダクトの損害は無く、隔離が壊れればほかのテストが実環境に書く前に bwrap のエラーで気付く | 消す |
| `test_settings_check_and_cleanup_use_the_selected_path`（12 kind × roundtrip 2） | 24 | S（解決先の取り違え）+ D | `--agent-dir` が Pi の選ぶ設定ディレクトリと違うと、別の `settings.json`・`models.json`・`auth.json` を読み書きする。誤った対象への書き込み（中）。kind の大半（dot-tilde-root・named・unknown・trailing-newline など）はまれな書き方で D。roundtrip の `--settings-clean` は撤去が前提 | 代表化 + 4 件（unset・tilde・relative・symlink-parent。Pi 本体による oracle 照合を残す。`--settings-clean` の部分は F2 の撤去に従い外す） |
| `test_relative_tilde_preflight_preserves_all_managed_state`（kind 4 × entry 2 × invalid 3） | 24 | L（+ 撤去） | 不正な `settings.json`（symlink・hardlink・構文）で `--settings-check` が非 0 とメッセージで止まる。止まらなくても、その後で書き換える処理（`--settings-clean`）は撤去対象。`migration` 経路（12 件）は mcp-adapter の撤去と一緒に消える | 消す |
| `test_manifest_cleanup_and_postcheck_use_pi_selected_directory`（4 関数 × 5 kind × 2） | 40 | 撤去 | `install_pi_extensions` の旧 pi-subagents 掃除、`remove_pi_mcp_adapter`・`remove_pi_distill`・`remove_pi_lens` は済んだ一度きりの移行。F2 が撤去する前提（残すなら L: 掃除の失敗は exit 1 とメッセージ） | 消す |
| `test_provider_setup_uses_lexical_path_before_validation_or_writes`（4 field × invalid 4 × raw 2） | 32 | D（invalid≠None は `test_pi_provider_setup.py` の拒否テストと重複、`agent\n\n` は異常な書き方） | 正例（invalid=None, `alias/../agent`）は誤ったディレクトリへの models/auth の書き込みを防ぐ（中）。opencode は models と auth の両方を書く | 代表化 + 1 件（`setup_pi_opencode_go.zsh`・invalid=None・`alias/../agent`） |
| `test_oauth_precheck_reads_pi_selected_auth_not_symlink_parent_decoy` | 4 | L + D | 誤判定は OAuth 無しで起動して Pi が認証エラーを出す、または起動を止める。どちらも利用時に気付く。symlink 親の囮は異常な設定 | 消す |
| `test_commandcode_precheck_reads_pi_selected_models_not_decoy` | 4 | L + D | 同上（commandcode の models 事前確認。誤れば起動エラー） | 消す |
| `test_vertex_mount_uses_lexical_directory_before_resolving_auth_link` | 1 | D | vertex の auth overlay の対象ディレクトリは `test_real_namespace_masks_auth...` と symlink 検査（`linked_auth`）が確かめる。alias の書き方だけの違い | 消す |
| `test_setup_pins_resolved_directory_for_its_followup_pi_commands`（3 script × 3 raw） | 9 | D | 3 本は同じ `--agent-dir` を使う。後続の Pi 呼び出しに解決済みパスを渡す守り（誤ったディレクトリへの更新）。3 つの書き方も同じ処理 | 代表化 + 1 件（`setup_pi_opencode_go.zsh`・`alias/../agent`） |
| `test_launcher_pins_same_directory_before_executing_pi`（3 raw） | 3 | D | `pi_superagents_exec` が正規化したパスを `PI_CODING_AGENT_DIR` に渡す守り（中）。書き方 3 つは同じ処理 | 代表化 + 1 件（`alias/../agent`） |
| `test_provider_only_update_keeps_installed_launcher_and_helper_compatible`（4 launcher） | 4 | L | 古い helper が `pi_agent_directory` を持たないと、起動時に関数が無いエラーで落ちる | 消す |

##### test_pi_provider_setup.py（80 → 13）

| テスト群 | 現件数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_setup_targets_the_same_agent_directory_as_pi`（3 script × 6 directory） | 18 | S + D | 引用した `~/` をそのまま書く、cwd 変更後に相対パスを解く、は誤ったディレクトリへの書き込み（中）。3 script は同じ `--agent-dir` を使う | 代表化 + 4 件（opencode × None・`relative agent`・`~`・`~/.pi/agent`。`""`・`absolute` は D） |
| `test_update_preserves_other_providers_permissions_and_bom_input`（3 script × 2 encoding） | 6 | S + D | 他の provider と既存の鍵を消さない、秘密のファイルを 0600 に保つ、バックアップも 0600、冪等（データ消失・秘密の公開、高）。BOM の拒否は解析エラーで L | 代表化 + 1 件（opencode・utf-8） |
| `test_new_models_are_private_even_under_public_umask`（3 script） | 3 | S + D | 新規の `models.json`（鍵を含む）が umask で公開されない（秘密情報の漏れ、高） | 代表化 + 1 件 |
| `test_rejected_models_change_no_managed_state`（3 script × 8 invalid） | 24 | S（symlink）+ L + D | 構文・型の誤りは「models.json」付きの非 0 で止まる（L）。symlink・hardlink の先へ書かず、共有ファイルを置き換えない（中: 黙って共有が外れる）。残りの invalid は同じ `plain_file`/`load_object` | 代表化 + 2 件（opencode × syntax・symlink。拒否と状態不変。正例は `update_preserves`） |
| `test_rejected_auth_changes_neither_models_nor_other_state`（7 invalid） | 7 | S + D | 認証の symlink 先を置き換えない、models も変えない（秘密を含む共有の消失、高）。ほかの invalid は同じ検査 | 代表化 + 1 件（symlink） |
| `test_invalid_source_is_rejected_before_any_side_effect`（3 × 4） | 12 | L | リポジトリ自身の `pi-models.json` が壊れた場合。初回利用で `pi-models.json` 付きのエラー | 消す |
| `test_missing_launcher_helper_is_rejected_before_any_managed_change` | 2 | L | 配布物の欠落。「helper source not found」で止まる | 消す |
| `test_missing_opencode_key_is_rejected_before_models_change` | 1 | L | API キーが無いとメッセージ付きで止まる | 消す |
| `test_existing_opencode_key_is_preserved_without_environment_key` | 1 | S | 環境変数が無いときに保存済みの鍵を消さず、出力に出さない（データ消失・秘密の漏れ、中〜高） | 残す |
| `test_existing_fixed_name_tmp_and_its_shared_target_are_untouched` | 3 | S + D | 固定名の `models.json.tmp` の symlink 経由で利用者のファイルを上書きしない（誤った対象の破壊、高。過去の不具合）。3 script は同じ `setup` | 代表化 + 1 件 |
| `test_io_failure_never_truncates_files_and_cleans_unused_staging`（fsync・replace-model・replace-auth） | 3 | S + D | 入出力の失敗でファイルを切り詰めず、バックアップと staging を整える（データ消失、高）。例外は出る（L）が状態は黙って残る | 代表化 + 2 件（fsync・replace-auth。replace-model は D） |

##### test_pi_vertex_launchers.py（133 → 18）

3 つのランチャー（pigemf/pigemp/pigema）は名前とモデルだけが違う。以下は `pigemf` を代表にする。

| テスト群 | 現件数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_launch_reaches_pi_without_adc...`（3 launcher） | 3 | S + D | 引数・cwd・環境・終了コードを保って Pi に届く。ほかの vertex テストの正例にもなる。引数の引用の誤りは黙って別の入力になる（中） | 代表化 + 1 件 |
| `test_cloud_defaults_precedence_and_api_key_removal`（3 × 4） | 12 | S + D | `GOOGLE_CLOUD_API_KEY` を Pi の環境から外す（秘密情報の漏れ、高）。project/location の優先順位の誤りは課金先の取り違え（中）。`legacy`・空文字の組はまれな書き方 | 代表化 + 2 件（既定値のみ・主要 3 変数の優先） |
| `test_real_namespace_masks_auth_for_parent_and_child_preserving_saved_files`（3 × 5 × 2） | 30 | S + D | #578 の中核。保存済みの OAuth を Pi が消費・更新して失わない、親子の Pi 両方に効く、秘密を出さない、保存済みの auth を書き換えない（データ消失・秘密情報の漏れ、高） | 代表化 + 3 件（(None, stored)・(None, 無し)・(`~/.custom agent`, stored)。`relative agent` は下の `relative_agent_dir...` が担当） |
| `test_linked_auth_reaches_parent_and_child_without_changing_host_state`（3 × 3） | 9 | S + D | symlink・hardlink の auth を正規化してマウントし、共有の auth を書き換えない（共有データの破壊、中。壊れれば bwrap のエラーでも気付くが、書き換えは黙って起きる） | 代表化 + 2 件（absolute symlink・hardlink） |
| `test_nonauth_state_and_settings_lock_remain_host_backed`（3） | 3 | S + D | agent dir 全体を隠すと、セッションや設定が失われる（データ消失、高） | 代表化 + 1 件 |
| `test_concurrent_launchers_initialize_only_empty_missing_auth` | 1 | S | 同時起動で保存済みの auth を置き換えない、不正な JSON・公開権限・staging を残さない（競合、高） | 残す |
| `test_dry_run_is_argv_only_and_never_reads_or_creates_auth`（3） | 3 | L | 表示専用の経路。FIFO を読めば固まって明らかに気付く。ほかのテストの補助（モデル ID の取得）として使うだけ | 消す（補助 `_launcher_model` は残る） |
| `test_invalid_auth_configuration_fails_closed_without_secret_output`（4 content） | 4 | S + D | 壊れた auth を黙って `{}` にせず、解析エラーに秘密を載せず、Pi を起動しない（秘密情報の漏れ、高）。入力 4 通りは同じ経路 | 代表化 + 1 件（`'{"synthetic-secret":'`） |
| `test_missing_any_used_vertex_model_stops_before_pi_and_auth_reads`（3） | 3 | S + D | catalog に無いモデルで Pi のあいまい一致に落ちて別のモデルで動く（誤った結果、中）。親と tier 子の全モデルを確かめる | 代表化 + 1 件 |
| `test_catalog_with_only_used_vertex_models_reaches_pi`（3） | 3 | S + D | 上の拒否に対する正例（使うモデルだけが catalog にあれば通る） | 代表化 + 1 件 |
| `test_native_oauth_refresh_and_request_do_not_consume_saved_tokens`（3 × expired 2） | 6 | S + D | 読み取り専用の snapshot に残った OAuth を Pi が更新し、新しいトークンを保存できず失う（認証情報の消失、高）。親子の両方 | 代表化 + 1 件（expired=True） |
| `test_native_vertex_sdk_receives_saved_or_explicit_adc_path`（3 × 2 × 3 × 3） | 54 | S + D | 保存済み・明示の ADC のパスを SDK に渡す。明示の指定を上書きして別の資格情報で動く（誤った結果、中）。保存名の引用符・改行は異常な書き方 | 代表化 + 3 件（(key有・未指定・保存名あり)、(key有・`explicit`・保存名あり)、(key無・未指定・保存名なし)） |
| `test_setup_seeds_vertex_tiers_and_preserves_existing_configs_on_rebuild` | 1 | D | `--if-absent` の保持は `test-pi-superagents.bash` にもある（実装している `setup_pi_superagents.zsh` 側のテストに置く） | 消す |
| `test_relative_agent_dir_stays_fixed_when_a_child_changes_cwd` | 1 | S | 相対の agent dir が子の cwd で解け、overlay を外れる（秘密・認証の取り違え、中） | 残す |

#### (2) 処置後の見積もり

| ファイル | 件数 前 → 後 | 行数 前 → 後（見積もり） |
| --- | --- | --- |
| `test_pi_agent_paths.py` | 146 → 7（`test_pi_provider_setup.py` へ移し、ファイルを消す） | 448 → 約 90（移した後） |
| `test_pi_provider_setup.py` | 80 → 13 | 285 → 約 150 |
| `test_pi_vertex_launchers.py` | 133 → 18 | 772 → 約 480（native probe・fixture が大半） |
| 計 | 359 → 38（約 11%） | 1,505 → 約 720（約 48%） |

行数は probe の JS 文字列・fixture・Harness が残るため、件数ほど減らない。`_real_namespace_probe`（約 65 行）・`_native_namespace_probe`（約 45 行）・OAuth/ADC の body（約 160 行）は S の中核なので残す。

#### (3) 撤去候補と根拠

- `test_manifest_cleanup_and_postcheck_use_pi_selected_directory`（40）・preflight の `migration` 経路（12）: F2 が `remove_pi_mcp_adapter`/`remove_pi_distill`/`remove_pi_lens`/旧 pi-subagents 掃除を撤去する前提。根拠の確かめは F2 担当（`~/.pi/agent/settings.json` と `npm/package*.json` に 4 つの名前が無いことを確認済み: grep 0 件）。F2 が撤去しない場合は L として消す（掃除の失敗は `exit 1` とメッセージ）ので、どちらでも消える。
- `pi-provider-setup.py` の `--settings-clean`（`settings_update(check_only=False)` の書き込み側）: 呼び出し元は `install_beforehand.bash:439` のみ（`git grep` で確認）。F2 が撤去するなら clean 経路も撤去（コード）。テスト側は agent_paths の roundtrip 部分が該当。

#### (4) 重さが高の守りの壊し方案（使い捨てコピー `/tmp` で、残したテストが失敗することを 1 回ずつ確かめる）

| 守り | 残したテスト | 壊し方 |
| --- | --- | --- |
| 認証の overlay（#578、保存済み OAuth を消費しない） | `test_real_namespace_masks_auth...`・`test_native_oauth_refresh...` | `pi-superagents-exec.zsh:260` の `--ro-bind-data 3 "${auth_file:A}"` を外す、または `--bind` に変える |
| `GOOGLE_CLOUD_API_KEY` を外す | `test_cloud_defaults_precedence_and_api_key_removal` | `pigemf` の `unset GOOGLE_CLOUD_API_KEY` を削除 |
| 他の provider・鍵を消さない / 0600 | `test_update_preserves...`・`test_new_models_are_private...` | `pi-provider-setup.py:83` の mode を `0o644`、または `providers[provider]` 代入を `data["providers"] = {provider: ...}` に |
| 固定名 tmp の symlink 先を上書きしない | `test_existing_fixed_name_tmp...` | `stage()` の `tempfile.mkstemp` を `path.with_suffix(".tmp")` への `open("wb")` に |
| symlink・hardlink の先へ書かない | `test_rejected_models...`（symlink）・`test_rejected_auth...` | `plain_file()`（:32-38）の本体を `return` に |
| 入出力の失敗でファイルを切り詰めない | `test_io_failure...` | `os.replace(temporary, path)`（:116）を `path.write_bytes(payload)` に |
| 同時起動の競合 | `test_concurrent_launchers...` | `pi-superagents-exec.zsh:176` 付近の空 auth の作成（`{}`・0600）を、存在確認なしの毎回上書きに |
| 壊れた auth で秘密を出さない | `test_invalid_auth_configuration...` | 解析エラーのメッセージにファイルの内容を足す |
| セッションなどの状態が host に残る | `test_nonauth_state_and_settings_lock...` | overlay を agent dir 全体の `--tmpfs` に変える |

#### (5) 補助の fixture で一緒に消せるもの

- `test_pi_vertex_launchers.py`: `_launcher_model`・`_used_vertex_models`・`_catalog` は残るテストが使う。消えるのは dry-run テスト専用の使い方だけ（補助は残る）。`LAUNCHERS` は 1 つだけ使うが、`sandbox` が 3 launcher の config を作るので、`pigemp`/`pigema` を消す場合は `LAUNCHERS` を `("pigemf",)` にできる。ただし ランチャー自体は消さない（名前・引数は変えない）。モデル ID の取得に `pigemp`/`pigema` が要るテストは無い。
- `test_pi_provider_setup.py`: `Harness.run(source=..., api_key=...)` の `source` は消す `invalid_source`・`missing_launcher_helper` 専用 → 引数ごと消せる。`api_key=None` は `existing_opencode_key` が使うので残す。
- `test_pi_agent_paths.py`: `_native_agent_directory`・`_symlink_parent` は残す 7 件が使う。`_named_tilde`（named kind 専用）は消せる。
- 移行後の依存: `INSTALL_SCRIPT`・`MigrationHarness`・`_harness`・`_invalid_settings` は消えるテストだけが使う。`test_pi_mcp_adapter_migration.py` のものなので F2 の担当。

### F2 棚卸し: pi の導入・移行まわり（#234 / devcontainer-tests）

分析のみ（ファイルは未編集）。基準: `AGENTS.md` の「テストの採用基準」、#228 の「削除と採用の基準」。
worktree: `/workspaces/reso-world/.worktrees/issue-234-devcontainer-tests`（main 481a047）。

#### (1) 棚卸しの表

分類: F 固定値 / F∩S / L 気付ける / S 気付けない損害 / D 重複 / 撤去 / 迷い。S の重さは高・中・低。

##### 1-1. `tools/devenv_migration/tests/test_pi_mcp_adapter_migration.py`（50 件・353 行）

| テスト群 | 件数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_cleanup_accepts_bom_and_preserves_other_settings` | 2 | 撤去 | `remove_pi_mcp_adapter`（済んだ一度きりの移行）の検査 | ファイルごと削除 |
| `test_relist_failure_stops_before_settings_cleanup` | 1 | 撤去 | 同上 | 同上 |
| `test_manifest_only_removal_uses_selected_agent_dir` | 8 | 撤去 | 同上（agent dir 4 通り × マニフェスト 2 種） | 同上 |
| `test_manifest_left_after_removal_is_rejected` | 8 | 撤去 | 同上 | 同上 |
| `test_successful_removal_preserves_unrelated_settings` | 4 | 撤去 | 同上 | 同上 |
| `test_invalid_settings_rejects_before_any_managed_change` | 18 | 撤去 | `--settings-check` の preflight。呼び出し元は撤去する 3 つの節と「Installing pi」の preflight だけ（下の 3-1）。symlink・hardlink・fifo などを 9 通り×2 で網羅する D でもある | 同上 |
| `test_pi_installation_preflight_precedes_external_mutations` | 4 | 撤去 | 同上 | 同上 |
| `test_settings_io_failure_leaves_no_partial_or_staged_files` | 2 | 撤去 | `settings_update` の staging 後始末。`settings_update` ごと撤去 | 同上 |
| `test_settings_noop_creates_or_changes_nothing` | 3 | 撤去 | `--settings-check/--settings-clean` の no-op。同上 | 同上 |
| 補助 `MigrationHarness`・`_harness`・`isolated_command`・`_snapshot`・`FAKE_PI` | – | 補助 | 撤去する経路用。`isolated_command` を `test_pi_agent_paths.py` が import している（下の 5） | 同時に削除 |

##### 1-2. `tools/devenv_migration/tests/test_pi_shared_packages.py`（2 件・110 行）

| テスト | 件数 | 分類 | 理由・重さ | 処置 |
| --- | --- | --- | --- | --- |
| `test_rebuild_preserves_shared_packages[registered=True]` | 1 | S 中 | rebuild が共有 `~/.pi` の他リポジトリの登録（context7-pi）・利用者の packages / extensions / theme を黙って消さない。#162 で実際に起きた「Context7 の cleanup で共有登録を消す」不具合の再発防止。消えても導入は成功し、他リポジトリの Pi が気付くのは後になる | 残す。`-builtin:mcp` の除去を期待する行（`extensions == ["user-local-extension"]`）は、除去の撤去に合わせて「settings.json の packages 以外が変わらない・`pi remove` が一度も呼ばれない」に直す。フラグメントの範囲は `Installing pi` 〜 `Installing the shared skills` のまま |
| `[registered=False]` | 1 | D | 同じ守りの未登録版 | 削除（`parametrize` を 1 件に） |

##### 1-3. `tools/devenv_migration/tests/test_pi_installer_isolation.py`（8 件・124 行）と `.devcontainer/tests/pi-launcher-install.bash`（48 行）

| テスト | 件数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_actual_codex_suite_never_calls_external_installers` | 1 | 撤去（補助専用） | `test-pi-openai-codex.bash` を安全に動かすためだけのテスト（Issue の手がかり）。`test-pi-openai-codex.bash` を消すので存在理由が無い | 削除 |
| `test_invalid_boundaries_emit_nothing_and_execute_nothing` | 5 | 同上 | 同上 | 削除 |
| `test_only_launcher_section_runs` | 1 | 同上 | 同上 | 削除 |
| `test_fragment_cannot_modify_repository_or_access_host_network` | 1 | 同上 | 同上 | 削除 |
| `pi-launcher-install.bash`（`pi_run_launcher_install`） | – | 補助 | 上の 2 ファイルだけが使う（`git grep` で確認済み） | 削除（`.devcontainer/tests/` ごと空になる） |

##### 1-4. `.devcontainer/test-pi-openai-codex.bash`（1 本・191 行）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| `test_launchers_accept_tilde_agent_dir` | D | `PI_CODING_AGENT_DIR` の `~` 展開は `test_pi_agent_paths.py` が実装側（ヘルパと setup）で多数確かめている。壊れれば OAuth 案内で止まる L でもある | 削除 |
| `test_missing_oauth_guides_login_without_requesting_api_key` | L | メッセージ付きの exit 1。案内文は F | 削除 |
| `test_install_places_all_launchers_with_regular_mode` | L | ランチャーの配置漏れ・差異は初回起動で `command not found` / 古い版として見える。`cmp` による一覧照合は F | 削除 |
| `test_live_openai_codex_models`（`PI_CODEX_LIVE_CHECK=1` のときだけ動く） | L | それ自体が実環境の検査。通常の実行では何もしない | 削除 |

##### 1-5. `.devcontainer/test-pi-migrations.bash`（1 本・12 行）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 6 つの pytest ファイルを実行 | D | `uv run pytest`（`testpaths` に `tools`）が同じファイルを集めて実行する二重実行 | 削除 |

##### 1-6. `.devcontainer/test-pi-superagents.bash`（1 本・46 場面・1,323 行）

| # | 場面 | 分類 | 理由・重さ | 処置 |
| --- | --- | --- | --- | --- |
| 1 | `dry_run_emits_bwrap_command` | D | bind src/dst の位置は #13（全ランチャー）と同じ守り。`--tui-mode regular` の先頭は #14 側で見ていたが、#14 も消す。argv の形そのものは #7 が実行で確かめる | 削除 |
| 2 | `bind_target_ignores_pi_coding_agent_dir` | S 中 | tier の bind 先が `PI_CODING_AGENT_DIR` に引きずられると、拡張が読む `~/.pi/agent/extensions/subagent` に重ならず、tier が黙って効かない（モデル割当が変わる）。エラーにならない | 残す（短くする） |
| 3 | `missing_config_fails_closed`（ヘルパ） | 迷い（L 寄り・低） | config が無いと exit 1 とメッセージ。壊れた（fail-open）場合は、tier が効かないまま起動して気付きにくい。守りはヘルパ側にあるので代表はここ | 残す。`integration` の一覧で先頭に並べる |
| 4 | `missing_bwrap_fails_closed` | S 高 | bwrap が無いときに止まらないと、サンドボックス（mount namespace による分離）無しで Pi が起動する。権限・サンドボックスの境界 | 残す |
| 5 | `dry_run_one_prints_argv_without_exec` | D | #7 が dry-run の出力を使って検証する。`=1` で exec しないことは #7 の dry-run 側（出力を得られること）に含まれる | 削除 |
| 6 | `dry_run_zero_execs_bwrap` | D | #7 が `=0` で fake bwrap を exec して見ている | 削除 |
| 7 | `actual_and_dry_run_argv_match` | S 中 | dry-run の argv と実際に bwrap へ渡る argv が食い違うと、argv を見るほかの全ての検査が意味を失い、通るのに実際は違う（誤っているがもっともらしい結果） | 残す（`=0` の exec 検査を兼ねる） |
| 8 | `commandcode_models_are_defined_in_pi_models` | L | 定義が無いモデルは子 Pi の起動時にエラー | 削除 |
| 9 | `configs_contain_no_credentials` | L | 秘密情報のコミットは Gitleaks（push 前の検査）が検出する既存の検査 | 削除 |
| 10 | `configs_are_minimal_partial_configs` | F | tier 設定の schema（キーの集合・tier 名）を写して照合 | 削除 |
| 11 | `pigs_opencode_key_reaches_child_process` | L | キーの引き継ぎを誤れば、子 Pi が認証エラー（OpenCode の 401）になる。4 通りの組み合わせは D でもある | 削除 |
| 12 | `launcher_files_are_executable` | L | ファイルの実行権限（`command not found` / Permission denied で気付ける） | 削除 |
| 13 | `launchers_wrap_pi_with_their_own_config` | S 中 | 各ランチャーが自分の tier 設定を重ねる対応（bind src/dst の位置）。別ランチャーの設定を重ねても起動は成功し、モデル割当（費用・能力）が黙って変わる。ランチャー一覧は設定ファイルから導くので漏れない。#1 の守りを代表として含む | 残す |
| 14 | `launchers_select_regular_and_forward_user_arguments` | L | `--tui-mode regular` の欠落は画面が崩れる、引数の欠落は起動できない／効かないが即座に見える。commandcode の定義確認は #8 と D | 削除 |
| 15 | `only_vertex_launchers_overlay_auth` | S 高 | `pi_google_vertex_models` に登録し忘れると、保存済みの Vertex key / OAuth が overlay（読み取り専用・OAuth 除去）無しで Pi に渡る。資格情報の取り扱い。実装側のテストは `test_pi_vertex_launchers.py`（F1 の担当）。ランチャー一覧との照合は F1 側に無い（要確認、F1 の結果と突き合わせて D にならないか調整） | 残す |
| 16 | `pixg_oauth_guidance` | L | OAuth 未設定のときの exit 1 とメッセージ。`~` 展開の確認は agent_paths 側と D | 削除 |
| 17 | `commandcode_key_check_runs_before_launch` | L | メッセージ付きの exit 1 | 削除 |
| 18 | `launcher_missing_config_fails_closed` | D | #3 と同じ守り（実装はヘルパ） | 削除 |
| 19 | `run_launcher_ignores_external_pi_coding_agent_dir` | D | #2 と対になるテスト用ハーネスの確認。ハーネス（`run_launcher`）が環境を固定する前提は、使う側を残すなら #2 のように自分で `env` を指定すれば足りる | 削除 |
| 20 | `setup_places_all_launcher_configs` | L | 配置されなければ、ランチャーが「設定が見つかりません」で止まる | 削除 |
| 21 | `setup_backs_up_modified_config` | D | #22 が 1 世代目の退避を含めて確かめる | 削除 |
| 22 | `setup_preserves_prior_generation_on_name_collision` | S 中 | 利用者が編集した config を退避せず上書きする、同一秒の退避で前の世代を上書きする、のどちらも気付けないデータ消失（利用者の tier 編集）。固定時刻の date shim で再現 | 残す |
| 23 | `setup_is_idempotent_without_changes` | L | 退避ファイルが溜まるだけで作業の結果は変わらない（重さ低、表示・整理の誤り） | 削除 |
| 24 | `setup_if_absent_preserves_user_edits` | S 高〜中 | rebuild のたびに `--if-absent` で呼ばれる。ここが壊れると、rebuild で利用者の tier 編集が（退避も無く）消える。データの消失 | 残す |
| 25 | `setup_output_mentions_each_launcher` | F | 出力にランチャー名が含まれることを確かめる（表示） | 削除 |
| 26 | `setup_leaves_user_settings_untouched` | S 中 | 共有の `settings.json`（書式・CRLF・世代バックアップ）を setup が書き換えない。`--if-absent` と通常の 2 モード×4 fixture×2 回の網羅は D | 残す。通常と `--if-absent` の 2 通り × `valid`（CRLF・タブ）1 fixture × 1 回、`missing` で作らないことを 1 通り（計 3 場面）に絞る |
| 27 | `setup_opencode_go_completion_mentions_bwrap_and_subagent_d` | F | 完了メッセージの文言を写して照合 | 削除（`make_setup_pi_fake`・`run_opencode_setup` も消える） |
| 28 | `setup_commandcode_goat_completion_mentions_bwrap_and_subagent_d` | F | 同上 | 削除（`run_commandcode_setup` も消える） |
| 29 | `install_removes_old_and_installs_new` | 撤去 / 残す（改） | pi-subagents の撤去は撤去。新拡張の導入の成功（`pi install --approve` が呼ばれ、登録される）は、下の改の場面に移す | 「導入の成功」として作り直して残す（旧拡張の登録は無し） |
| 30 | `install_removal_failure_is_fail_loud` | 撤去 | pi-subagents の撤去の失敗 | 削除 |
| 31 | `install_new_failure_is_fail_loud` | L | `pi install` 失敗で exit 1 とメッセージ（postCreate が止まる） | 削除 |
| 32 | `install_skips_remove_when_old_absent` | 撤去 | pi-subagents の撤去 | 削除 |
| 33 | `install_removes_stale_manifest_residue` | 撤去 | #289 の pi-subagents 残骸 | 削除 |
| 34 | `install_removes_stale_lockfile_residue` | 撤去 | 同上 | 削除 |
| 35 | `install_fails_when_manifest_residue_remains` | 撤去 | 同上 | 削除 |
| 36 | `install_fails_when_old_remains_after` | 撤去 | pi-subagents の残存検査 | 削除 |
| 37 | `install_fails_when_new_missing_after` | 迷い（L 寄り・中） | `pi install` が 0 を返したのに一覧に新拡張が無いとき exit 1。壊れる（検査が抜ける）と、postCreate は成功扱いで終わり、pigo / pigod で subagent ツールが無い状態になる（初回の利用で気付ける L の側面もある）。失敗を成功と報告する損害に当たりうるので残す | 残す（#29 の導入の成功と同じ場面ファイルにまとめる） |
| 38 | `install_fails_when_list_fails` | L | `pi list` 失敗で exit 1。メッセージ付き | 削除 |
| 39–45 | `remove_distill_*` | 撤去 | pi-distill の撤去 7 場面（`remove_pi_distill`） | 削除 |
| 46 | `pixg_live_model`（`PI_XAI_LIVE_CHECK=1` のときだけ） | L | それ自体が実環境の検査 | 削除 |

残す場面: #2、#3、#4、#7、#13、#15、#22、#24、#26（3 場面に絞る）、導入（#29 + #37 を改めた 1 つ）= 9 つの関数（26 が 3 場面）。

#### (2) 処置後の見積もり（件数・行数）

| ファイル | 前（件数 / 行） | 後（件数 / 行） |
| --- | --- | --- |
| `test_pi_mcp_adapter_migration.py` | 50 / 353 | 0 / 0（削除） |
| `test_pi_shared_packages.py` | 2 / 110 | 1 / 約 70 |
| `test_pi_installer_isolation.py` | 8 / 124 | 0 / 0（削除） |
| `.devcontainer/tests/pi-launcher-install.bash` | – / 48 | 0（削除） |
| `test-pi-openai-codex.bash` | 1 / 191 | 0（削除） |
| `test-pi-migrations.bash` | 1 / 12 | 0（削除） |
| `test-pi-superagents.bash` | 1 / 1,323 | 1 / 約 420（ヘルパ 約 130 行＋9 つの関数＋fake pi を導入用に縮小） |
| 合計 | 63 / 2,161 | 2 / 約 490 |

件数は、pytest の件数と bash の 1 本を 1 件と数える計測方法（Issue の「計測」）に合わせた。行数の見積もりは、`wc -l` で実測するまでの目安（誤差 ±80 行）。
`test_pi_agent_paths.py` の `isolated_command` 依存の分は F1 の処置で変わる（下の 5）。

#### (3) 撤去する経路と根拠

##### 3-1. 撤去するもの

| 撤去する経路 | 変更するファイルと範囲 |
| --- | --- |
| pi-subagents → pi-superagents の置換の後片付け（旧登録の検出・`pi remove npm:pi-subagents`・マニフェストの残骸掃除・残存検査） | `.devcontainer/install_beforehand.bash` の `install_pi_extensions`（300〜376 行付近）から、旧拡張に関する (1)〜(3) と事後の `*"npm:pi-subagents"*` 検査を取る。残すのは「導入前の `pi list` は不要」「`pi install --approve npm:@teelicht/pi-superagents`」「導入後の `pi list` で新拡張が在ること」。`agent_dir` の解決も不要になる。step の見出しを `Installing npm:@teelicht/pi-superagents` に直す（step 数は変わらない）。コメントの「旧拡張の置換」「テストが関数だけを取り出す」を新しい内容に直す |
| pi-mcp-adapter の撤去と settings の `-builtin:mcp` 除去 | `install_beforehand.bash` の step `Removing npm:pi-mcp-adapter …`（377〜445 行付近）全体 |
| pi-distill（＋単独登録の `pi-extensions-tool-display` / `pi-extensions-i18n`）の撤去 | step `Removing npm:pi-distill …`（446〜516 行付近）全体 |
| pi-lens の撤去 | step `Removing npm:pi-lens …`（517〜570 行付近）全体 |
| settings の preflight（`--settings-check`） | `install_beforehand.bash` の `Installing pi` 内の `--settings-check` 呼び出し（286〜290 行付近）と、`.devcontainer/pi-provider-setup.py` の `settings_update`（123〜141 行）と `--settings-check` / `--settings-clean` の分岐（150〜152 行）。`--agent-dir` と `setup` は `scripts/setup_pi*.zsh`（#235 の担当）が呼ぶので**残す** |
| step 数 | `readonly STEP_TOTAL=32` → `29`（撤去する 3 step 分）。`test-verify-resonite-tooling.bash`（F4 の担当）が `STEP_TOTAL` と `^step "` の数の一致を見るので、同じ変更で合う |

##### 3-2. 使われていない根拠

1. **今の環境に対象が残っていない**: `~/.pi/agent/settings.json` の `packages` は notify・pi-safe-search・pi-diet-ripgrep・superpowers・pi-simplify・skill-creator・@teelicht/pi-superagents・@plannotator の 8 件で、旧 4 パッケージは無い。`~/.pi/agent/npm/{package.json,package-lock.json}` にも `pi-subagents`・`pi-mcp-adapter`・`pi-distill`・`pi-lens` の文字列は無い（grep で確認）。`extensions` は空で `-builtin:mcp` も無い
2. **呼び出し元**: `git grep` で `remove_pi_mcp_adapter`・`remove_pi_distill`・`remove_pi_lens`・`--settings-check`・`--settings-clean` を呼ぶのは `install_beforehand.bash` だけ。`install_pi_extensions` を取り出すのは `test-pi-superagents.bash` だけ。`scripts/setup_pi_superagents.zsh:107` の `pi-subagents` 警告は表示だけで、別の担当（#235）のため触らない
3. **文書・雛形・設定の参照**: `.devcontainer/README.md`（下の 3-3）と、移植の記録 `docs/maatlog-poc-porting.md`（凍結した履歴。変更しない）。`.pi/settings.json` の `+builtin:mcp` は組み込み MCP を有効にする設定で、撤去の対象ではない。雛形（`devcontainer.json`・`agent-runner*.toml`）に旧拡張の参照は無い
4. **step 数への依存**: `STEP_TOTAL` と `grep -c '^step "'` の一致を見るのは `test-verify-resonite-tooling.bash` だけ。ほかの `test-*` は step の見出しを 1 番目（`Ensuring user-writable directories under ~`、`test-initialize-mounts.bash`）と DSH の step（`test-install-beforehand.bash`）で参照するだけで、番号には依存しない
5. **共有 `~/.pi` の再導入経路**: bind mount で共有される。このリポジトリの導入は旧 4 パッケージを入れない（`for extension in …` の一覧に無い）。`/workspaces` にある他のチェックアウトは reso-world だけで、旧パッケージを `pi install` する導入スクリプトは無い。ほかのコンテナ（agent-workspace・xrift-poc）の導入は、`.devcontainer/README.md` の pi-lens の節で導入をやめる Issue（xrift-poc#16・create-reso-world#117）が済んだと記録している。**未確認**: ホスト側でまだ旧版のリポジトリから rebuild していないコンテナがあれば、そのコンテナの rebuild が旧パッケージを再登録しうる。撤去後はこのリポジトリの rebuild で自動掃除されない（手で `pi remove`。README に残す）。これは「撤去してよい」の判断を変えないが、Spec に既知の制限として書く

##### 3-3. 文書の変更（撤去した経路を説明する行だけ）

`.devcontainer/README.md`:
- 84 行付近: 「pi の旧拡張の撤去と、settings の `-builtin:mcp` の除去。…」の bullet を、「Plannotator は導入・保持する。context7-pi は導入しないが共有の登録は消さない」だけにする
- 598〜632 行付近（「pi の旧拡張・MCP 設定の移行」）: 自動撤去・settings 検査・MCP cleanup の記述を削り、「自動撤去は #234 で外した。残っていれば手で `pi remove …` する」と手動コマンドの一覧を残す
- 1037〜1090 行付近（「pi-distill の撤去」「pi-lens の撤去」）: 「`install_beforehand.bash` はリビルド時に `pi remove …` で掃除する」「撤去後も残っていれば Dev Container の作成を止める」の文を、手動の手順に直す。共有 `~/.pi` の注意書きと `PI_DISTILL_*` の手順、`.pi-lens-probe-home/` の注意は残す
- 855〜856・1277〜1283 行付近: 削除するテスト（`test-pi-openai-codex.bash`・`test-pi-migrations.bash`）の実行例を消す。1277 行の「MCP 移行・Vertex の pytest は `test-pi-migrations.bash` が実行」は「`uv run pytest` が実行」に直す。※これらの行は「テストの実行」の節ではない（integration の担当は 「テストの実行」）が、削除したテストの参照を残さないための変更

`docs/maatlog-poc-porting.md` は移植の記録なので変更しない（`test-pi-migrations.bash` を入口と書いた行は凍結した履歴）。

##### 3-4. rebuild の後の確認（Spec 用）

1. rebuild 前に `~/.pi/agent/settings.json` と `npm/package.json`・`package-lock.json` を `cp -p` で退避する
2. rebuild 後、postCreate のログの最後が `[29/29]` になる
3. `pi list` に `npm:@teelicht/pi-superagents` と `npm:@plannotator/pi-extension` がある
4. `settings.json` が退避した版と `packages`・`extensions`・`theme` で一致する
5. `ls ~/.pi/agent/npm/node_modules` に `pi-subagents`・`pi-mcp-adapter`・`pi-distill`・`pi-lens` が無い
6. `pigo --help` 相当（`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1 pigo`）が `bwrap` の argv を出す

#### (4) 重さが高の守りの壊し方案（使い捨てコピーで、残したテストが失敗することを確かめる）

コピーの作り方: `d=$(mktemp -d)`（`/tmp` の一意のディレクトリ）に `git ls-files -z | xargs -0 cp --parents -t "$d"` で追跡ファイルを写し、そこで壊して実行する（テストは `ROOT` を自分の位置から求めるのでコピーの中が対象になる）。確認後は `rm -rf -- "${d:?}"`。

| 守り（重さ） | 壊し方（コピー内） | 失敗するべきテスト |
| --- | --- | --- |
| bwrap 不在で止まる（高） | `.devcontainer/pi-superagents-exec.zsh` の `if ! command -v bwrap …` を `if false` に | `test_missing_bwrap_fails_closed` |
| Vertex だけ auth overlay（高） | `pi_google_vertex_models` の `pigemp) reply=(…) ;;` を `pigemp) return 1 ;;` に | `test_only_vertex_launchers_overlay_auth`（Vertex の登録漏れ） |
| `--if-absent` が利用者の編集を保つ（高〜中） | `scripts/setup_pi_superagents.zsh` の `if (( if_absent )); then … continue` の分岐を消す | `test_setup_if_absent_preserves_user_edits` |
| 共有登録を消さない（中） | コピーの `install_beforehand.bash` の `Installing pi` 〜 `shared skills` の間に `pi remove npm:@upstash/context7-pi` を足す | `test_rebuild_preserves_shared_packages` |
| 退避世代を上書きしない（中） | `scripts/setup_pi_superagents.zsh` の `while [[ -e "${backup}" ]]` ループを消す | `test_setup_preserves_prior_generation_on_name_collision` |
| setup が settings を書き換えない（中） | `setup_pi_superagents.zsh` の末尾に `print "x" >> "${HOME}/.pi/agent/settings.json"` を足す | `test_setup_leaves_user_settings_untouched` |
| tier が別ランチャーの設定を重ねない（中） | ヘルパの `--bind "${launcher_dir}" "${shared_dir}"` を `--bind "${HOME}/.pi/agent/extensions/subagent.d/pigo" "${shared_dir}"` に | `test_launchers_wrap_pi_with_their_own_config` |
| argv の一致（中） | dry-run の `printf '%s\n' "${args_[@]}"` の前に引数を 1 つ足す | `test_actual_and_dry_run_argv_match` |

#### (5) 消せる補助・他の担当との調整

- 消せる補助: `MigrationHarness` とその関連（`test_pi_mcp_adapter_migration.py` の中）、`pi-launcher-install.bash`、`test-pi-superagents.bash` の `make_setup_pi_fake`・`run_opencode_setup`・`run_commandcode_setup`・fake pi の distill / manifest 分岐・`write_xai_auth`・`SETUP_OPENCODE`・`SETUP_COMMANDCODE`。`tools/test_support/` と `conftest.py` に、このグループだけが使う名前は無い
- **F1（`test_pi_agent_paths.py`）への依存**: `test_pi_agent_paths.py` が `from test_pi_mcp_adapter_migration import (…)`（`isolated_command`・`_harness` など）を読む。F1 は、(a) 撤去する経路のテスト（`test_settings_check_and_cleanup_use_the_selected_path`・`test_relative_tilde_preflight_preserves_all_managed_state`・`test_manifest_cleanup_and_postcheck_use_pi_selected_directory`。`--settings-check/--settings-clean` と `remove_pi_mcp_adapter` を使う）を撤去として消し、(b) 残るテストが使う `isolated_command` などを自分のファイル内に移す必要がある。`test_pi_provider_setup.py` の `settings_update` 依存は無い（`setup` / `stage` のみ）
- `pyproject.toml` の `pythonpath`（`tools/devenv_migration/tests`）は、F1 が兄弟モジュールの import をやめるまで変えない（integration の担当）
- F4 への申し送り: `test-verify-resonite-tooling.bash` が `STEP_TOTAL` と step 数を照合する。F2 の変更（32 → 29）で一致する
- `scripts/setup_pi_superagents.zsh:107-112` の pi-subagents 警告は #235 の範囲。撤去で意味が薄れるが、触らない
- F∩S は無し（この領域に、損害を防ぐ固定値のテストは無い）

### inventory-F3: herdr 系 bash テスト 3 本（読み取りのみの分析）

対象: `.devcontainer/test-herdr-migration.bash`（712 行・1 件）、`test-herdr-status.bash`（258 行・1 件）、`test-herdr-agent-task.bash`（255 行・1 件）。計 1,225 行・3 件（bash は 1 本 1 件。中の場面は下の表）。
コード側は変えない（撤去なし）。基準は `AGENTS.md` の「テストの採用基準」と #228。

#### (1) 棚卸しの表

##### test-herdr-migration.bash

| 場面群（関数） | 現数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| `test_launch_and_guards`（herdrstart: 非 TTY / `HERDR_ENV` / TMUX / herdr 不在のガード、updater の呼び出し回数、HOME から起動しても workspace へ cd） | 5 小場面 | L | 壊れると `zsh -ic` や rebuild の postCreate が herdr を起動したままハングする、入れ子で herdr が立つ、cd しないなど、普段のシェル起動で明らかに異常として現れる（devcontainer.json の loginInteractiveShell の注記）。updater の二重起動は flock で守られ、表示のみ | 消す |
| `test_session_cwd_repair` の修復成功（identity/pane の cwd を直し、worktree 配下・`agent_session`・未知フィールドを保つ、`.tmp` を残さない） | 1 | S（中: 利用者のセッション記録を失う・取り違える） | 壊れても例外にならず、復元先やセッションの再開情報が静かに変わる | 残す（代表） |
| 同: サーバー稼働中は無変更 | 1 | S（中） | 稼働中に書くと herdr の保存と競合し記録を上書きする。気付けない | 残す |
| 同: 不正な JSON は無変更 | 1 | L | 読み込みの例外は `|| true` で握るが、書き込みの前に落ちるので壊れても書かれない。ガードを外しても損害が出ない | 消す |
| 同: 未知の version（4）は無変更 | 1 | S（中） | ガードを外すと構造が同じに見える別形式を書き換えて、気付かずに壊す | 残す |
| 同: 修復先が不在 / 進入不可（2 通り） | 2 | D | 「壊れた cwd を別の壊れた cwd で置換しない」を 2 通りで確かめる。代表 1 件（不在）で足りる。進入不可は chmod 0444 に依存し root で意味を失う | 不在を 1 件に絞る |
| 同: サーバー状態の異常 5 通り（command_failure / malformed_json / missing_running / string_false / numeric_zero） | 5 | D | 同じ守り `running is not False`。`numeric_zero` は `== False`・`not running` への退行も検出できる | `numeric_zero` を代表に 1 件 |
| 同: 修復先がワークスペースルート自身（fzf キャンセル） | 1 | S（中-低: 修復不能な cwd を session に焼き付ける） | 焼き付いた後は自己修復できず、気付かない | 残す |
| `test_session_cwd_repair_multi_workspace` ① 先頭だけ修復し 2 件目は触らない | 1 | S（中: 複数 workspace が同じ identity に収束する） | `target_taken = True` を代入し忘れると 2 件が同一 identity になる。②では検出できない | 残す |
| 同 ② 修復先を既に持つ entry があれば無変更 | 1 | S（中） | 初期の `target_taken` 判定の退行を検出（①と別の変異） | 残す |
| 同 ③ 健全な兄弟 identity の pane は兄弟へ（起動中 workspace へ流さない、`agent_session` を保つ） | 1 | S（中-低）・迷い | pane を別 workspace へ流す退行は静かに起きる。ただし ①②と守りの近い箇所 | 残す（迷い。integration の一覧で先頭に並べる） |
| `test_cc_launcher_env_unsets` の `cc_launcher_unsets` と expected_unsets の完全一致 | 1 | F∩S（高: 親シェルの資格情報・プロバイダ切替・モデルピン留を子 claude へ漏らす） | 一覧の値そのものが守り | 残す（値は変えない） |
| 同: POLLUTED_ の値が 6 名前で漏れない / 入力元の資格情報を子へ残さない | 6 名前 | S（高: 秘密情報の漏れ）+ D | `claude-deepinfra` は `ccdd` と同じ関数（`function a b ()`）なので、名前違いは同じ実体。実装箇所は ccdd・ccddg・ccdu の 3 つ | 6 名前 → 3 関数（ccdd / ccddg / ccdu）。入力元キー非残留の検査は残す |
| 同: 各関数が実際に起動した裏付け（`ANTHROPIC_AUTH_TOKEN=fake-di` など） | 3 | S（隔離テストの空振り防止の対照） | 何も起動しなくても「漏れない」が通るので必要 | 残す（3 行） |
| `test_cc_launcher_arguments_and_models` alias 3 つ（ccd/ccdo/ccds）の argv 構造 | 3 | L | 権限確認を省くフラグが抜ければ起動時に確認が出て、`--model` が違えば明らかに別モデルになる。alias 定義をテンプレから写して比べる点は F でもある | 消す |
| 同: 関数 6 名前の argv（`--model X` 先頭、`--dangerously-skip-permissions`、空文字・空白・改行・glob を含む引数の素通し） | 6 名前 | L / F | 引数が壊れれば claude が異常な動作をして気付く。モデル名は運用で変わる固定値 | 消す |
| 同: 資格情報の送り先（`ANTHROPIC_BASE_URL`）と `ENABLE_CLAUDEAI_MCP_SERVERS=false`、`ANTHROPIC_AUTH_TOKEN`/`API_KEY` の渡し方 | 6 名前 | F∩S（高: 資格情報を別ホストへ送る、MCP で利用者のデータを他社モデルへ渡す） | 送り先を変えても動いてしまう | 残す。名前は 3 関数に絞り、argv の比較は外す |
| `test_cc_launcher_auth_and_exit_status` 資格情報なしで失敗し claude を呼ばない（6 名前 × unset/empty） | 12 | L | 呼んでしまっても認証エラーか login 画面で気付く。`is not set` の文言は F | 消す |
| 同: 子の終了コード 23 を返す、親シェルの `ANTHROPIC_MODEL`・`DEEPINFRA_TOKEN` が残る（6 名前） | 6 | S（低）・迷い | 終了コードを握りつぶすと失敗を成功と報告する。親の環境が関数に消される退行は静か。ただし対話ランチャーの影響は小さい | ccdd 1 件に絞って残す（迷い） |
| 同: ccdu のキー優先順位（dedicated/generic/go × 2 名前） | 6 | L | 誤ったキーは provider の認証エラーで気付く。優先順位は設計の選択 | 消す |

##### test-herdr-status.bash（8 関数）

| 場面群 | 現数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| git コアの状態（clean/staged/dirty/非 git）・ahead の `↑`（2 関数） | 2 | L | サイドバーの表示だけ。誤っても作業の結果を変えず、画面で一目で分かる（Issue の手がかりも L）。`git status` を読むだけで書き込みは無い | 消す |
| updater の dry-run（git・非 git・staged・dirty・cwd fallback、6 関数）、ブランチ名の短縮 | 6 | L | 同上。表示トークンの出力で、壊れれば表示が出ない・古いままになるだけ | 消す |

→ ファイルごと消す（258 行・1 件）。

##### test-herdr-agent-task.bash（24 関数）

| 場面群 | 現数 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- | --- |
| 引数・使い方の誤り（attention・不明 state・空/空白のタイトル・不正な TTL/最大長・pane id なし・title なし・不明なサブコマンド）が 64 で止まる | 10 | L | エラーで止まる経路の終了コード。呼び出し側がすぐ気付く | 消す |
| set/clear の出力（token・ttl・state_label を全 status へ、default working、--pane 優先、ttl 上書き、タイトルの切り詰め・改行/タブ/空白の整形・C ロケール） | 12 | L | サイドバーの表示だけ。壊れても作業の結果を変えない | 消す |
| herdr 不在は exit 0 の no-op | 1 | L | 壊れれば agents のタスク設定が非 0 で止まり、すぐ分かる | 消す |
| `herdr.toml` が `herdr config check` を通る | 1 | L | herdr 起動時に設定エラーとして出る（`herdr` 不在の環境では空振り） | 消す |

→ ファイルごと消す（255 行・1 件）。

#### (2) 処置後の見積もり

| 項目 | 前 | 後（見積もり） |
| --- | --- | --- |
| 件数（bash 1 本 = 1 件） | 3 | 1 |
| 行数 | 1,225 | 約 400〜450（migration のみ） |

migration の内訳の見積もり: 共通補助 約 110 行（`make_stub_home`・`run_zshrc_code`・セッション fixture は 1 つの Python ヘルパーにまとめて短縮）、修復（成功・稼働中・未知 version・修復先不在・numeric_zero・ルート自身）約 90、multi 約 80、unset の一覧 約 60、POLLUTED_・送り先・終了コード 約 80。`run_zshrc_tty` は `test_launch_and_guards` だけが使うので消す。`make_claude_probe` は送り先の検査に必要。

#### (3) 撤去候補と根拠

撤去（コードごと消す）候補は無い。

- `herdrstart`・`herdr_repair_session_cwd`・`cc_launcher_unsets`・ccdd/ccddg/ccdu は `zshrc.txt` から呼ばれ、README（`.devcontainer/README.md:502-504`）と `docs/herdr-session-cwd-restore.md` が説明している。
- `herdr-agent-task` は `.agents/skills/herdr-agent-task`・`issue-to-pr` の SKILL.md・`.pi/APPEND_SYSTEM.md` が呼ぶ。`herdr-status-updater`・`herdr-git-status` は `herdrstart` が起動する。
- 消すのはテストだけ。消すファイル名の参照: `test-herdr-status`・`test-herdr-agent-task` を参照する現行の文書は無い（`docs/superpowers/plans/*` と `docs/maatlog-poc-porting.md` は凍結した過去文書）。`test-herdr-migration.bash` は `.devcontainer/docs/herdr-session-cwd-restore.md:184` と `zshrc.txt:74`、`docs/maatlog-poc-porting.md:88` が参照するので、ファイルは残す。`zshrc.txt:74` のコメント「expected_unsets」は残る一覧の名前なので変更不要。
- `docs/maatlog-poc-porting.md:97,115,132` はテストの内容を書いた凍結済みの移植記録で、更新しない。
- 副次的な気付き（範囲外・変更しない）: `herdr-git-status.bash` の `git status` に `--no-optional-locks` が無く、updater の定期実行が index.lock を取り得る。テスト対象外で、この Issue では扱わない。

#### (4) 重さが高の守りの壊し方案（使い捨てコピーで、残したテストが失敗することを確かめる）

`zshrc.txt` を `mktemp -d` にコピーして変更し、テストの `ZSHRC_TEMPLATE` を差し替えて実行する（テストは `REPO_ROOT` 固定なので、リポジトリ全体をコピーして `.devcontainer/zshrc.txt` を変える）。

| 守り（重さ） | 壊し方 | 失敗するはずの残したテスト |
| --- | --- | --- |
| サーバー稼働中の無変更（中） | `herdr_repair_session_cwd` の python の `status.get("running") is not False` の判定行を削除 | 稼働中の無変更、numeric_zero |
| 状態判定の厳密さ（中） | `is not False` を `not status.get("running")` に変更 | numeric_zero |
| 未知 version の無変更（中） | `data.get("version") != 3` の判定を削除 | 未知 version |
| 修復先がルート自身（中-低） | `[ "${workspace_dir%/}" != "${root%/}" ] || return 0` を削除 | ルート自身 |
| 修復先の不在（中-低） | `[ -d "$workspace_dir" ] && [ -x ... ] || return 0` を削除 | 修復先不在 |
| 複数 entry の収束防止（中） | `target_taken = True` の代入を削除 / 初期の `target_taken = any(...)` を `False` に | multi ①、multi ② |
| pane の流れ先（中-低、迷い） | `pane_target = identity if inside(identity, root) else workspace` を `workspace` に | multi ③ |
| 資格情報の漏れ（高） | ccddg の `env "${cc_launcher_unsets[@]}"` から配列を外す / 配列から `ANTHROPIC_API_KEY` を 1 つ削除 / ccdu の入力キー（`OPENCODE_API_KEY`）を unset の対象から外す | POLLUTED_・入力元非残留・expected_unsets の一覧一致 |
| 資格情報の送り先（高） | `ANTHROPIC_BASE_URL` を別の URL に変更 / `ENABLE_CLAUDEAI_MCP_SERVERS` を `true` に | 送り先の検査 |
| 終了コード（低、迷い） | ccdd の最後に `|| true` を足す | 終了コードの検査 |

各行は 1 回ずつ壊して、該当テストが非 0 で落ちることと、元のコピーで通ることを確かめる。

#### (5) 消せる補助

`test-herdr-migration.bash` の中で、消した場面だけが使うもの: `run_zshrc_tty`、`assert_contains` の大半（POLLUTED_・送り先の検査は `assert_absent`・python の assert で足りる）、`make_stub_home` の `herdr` スタブの `called TZ=...` ログ出力、`starship`・`herdr-status-updater` のスタブ（herdrstart を呼ばなくなれば不要。`source zshrc.txt` が `eval "$(starship init zsh)"` を呼ぶので `starship` スタブは残す）、`herdr.log` / `herdr.log.upd`。`write_multi_workspace_fixture` は 3 場面の fixture に統合できる。ほかのファイル・共有補助（`tools/test_support/` など）を使っていない。

### F4 棚卸し: その他の bash テスト（読み取り専用の分析。ファイルは未編集）

基準: `AGENTS.md` の「テストの採用基準」、#228 の「削除と採用の基準」。bash のテストは 1 本を 1 件と数える（件数は「ファイル数」、場面は行数に表れる）。
worktree: `.worktrees/issue-234-devcontainer-tests`（HEAD `481a047`）。

#### (1) 棚卸しの表

分類: F 固定値 / F∩S / L 気付ける / S 気付けない損害 / D 重複 / 撤去 / 迷い。重さは高・中・低（`#228` の定義）。

##### test-cleanup-workspace.bash（38 行・2 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. `WORKSPACE_CLEANUP_DRY_RUN=1` は表示するだけで消さない | S（中） | postCreate と zshrc が実行する、実際に削除するスクリプトの手動の確認手段（`.devcontainer/README.md:13`）。dry-run が削除してしまうと、確認のつもりで `/tmp` のレビュー用 worktree を消し、気付けない（誤った対象の削除）。 | 残す |
| 2. 既定値 `/tmp`・1 日・dry-run なし | F∩S | 削除の範囲の既定値（#229 の申し送り 1）。既定値が広がると使用中の worktree や `/tmp` 外を消す。実装の値から期待値を作らない固定値。 | 残す（理由は既にコメントにある） |

件数 1 → 1、行数 38 → 38（変更なし）。

##### test-readme.bash（43 行・3 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. README の道具の表の mount 列・initialize.bash 列を実装と比較 | F | 文書の表の今の値を実装と照合。ずれても動作は変わらない。 | 消す |
| 2. 表の zshrc 列・update() 列が zshrc.txt にある | F | 同上（文書の表）。 | 消す |
| 3. `.devcontainer` にワークスペースの絶対パス `/workspaces/reso-world` を書かない | F∩S | worktree や別名の checkout から実行しても親の checkout を操作する（#229 の申し送り 1）。禁止するパスの固定値。 | 残す。ファイルは `git grep` の 5 行ほどに縮める（`mounts.bash` の source と表の補助を消す） |

件数 1 → 1、行数 43 → 約 12。

##### test-run-tests.bash（47 行・4 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. 既定の対象（`--list`）が `test-*.bash` と `tests/scripts/*.bash`、`lib` を含まない | L | 実行すべきテストが落ちれば、そのテストが走らないだけでなく `README.md` の入口で一覧が見える。期待値は同じ glob の写しで F 寄り。誤りは run-tests の出力（PASS 件数・一覧）に現れる。 | 消す |
| 2. 失敗があれば終了コード 1（出力の字下げ・成功の出力を出さない・PASS/FAIL 行・要約行の書式） | S（中・終了コード）/ F（書式） | 失敗を成功（0）と報告すると、壊れた bash テストを見逃す（失敗を成功と報告する）。書式（`PASS ...`・字下げ・要約行）は表示であり L/F。 | 終了コード 1 の確認だけ残し、書式の検査は消す |
| 3. すべて通れば 0 | D（正例） | 場面 2 の拒否に対する正例（何でも失敗にする実装で通らないための 1 件）。件数の表示 `PASS: N test(s)` は消す。 | 終了コード 0 の確認だけ残す |
| 4. 外から渡された `GIT_*` をテストに渡さない（#166） | S（高） | linked worktree の `git rebase --exec` が export する `GIT_DIR` を渡すと、一時リポジトリのつもりのテストが実リポジトリの設定を書き換える（データの破壊・環境の隔離）。実際に起きた気付けない不具合。 | 残す |

件数 1 → 1、行数 47 → 約 27。

##### test-install-ctx7.bash（55 行・5 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. 固定した版を `npm install -g ctx7@版` で入れ、`ctx7` を `--version` 以外で呼ばない | S（中） | `ctx7 setup` は共有の `~/.claude`・`~/.codex` に MCP 設定とスキルを書く（Issue #234 の「残す S」）。誤って `setup` などを呼んでも、導入は成功し気付けない。 | 残す |
| 2. npm install の失敗で ERROR を出し止まる | L | `set -e` の終了と `fail` のメッセージ。postCreate は `if ! bash install_ctx7.bash; then fail` で止まる。 | 消す |
| 3. `ctx7` が PATH に無いと止まる | L | `command -v` の失敗でエラー終了。 | 消す |
| 4. 版の不一致で止まり、見つけた版を表示 | S（低） | ほかの ctx7 が PATH の先にあると、固定した版でない CLI を使うが、動くので気付けない。拒否の正例として場面 1 がある。 | 残す（場面 1 と同じ偽の npm を使い回し、2 場面に縮める） |

件数 1 → 1、行数 55 → 約 35。

##### test-install-gitleaks.bash（73 行・5 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. SHA-256 の不一致を拒否し、既にある gitleaks を変えない | S（高） | 秘密情報の検査（`scan-before-push.sh`）に使う実行ファイルの検証。改ざんされた archive を置く／既存の実行ファイルを壊すと、検査が通らないまま気付けない。Issue の「残す S」。 | 残す |
| 2. SHA が一致する archive では置く（中身の一致） | D（正例） | 場面 1 の拒否に対する正例（何でも拒否する実装で通らないため）。 | 残す。mode 755 の確認と取得 URL の確認は消す |
| 3. mode 755 で置く | L | 実行権限が無ければ `scan-before-push.sh` が起動できずエラー。 | 消す |
| 4. 取得 URL が `https://github.com/gitleaks/gitleaks/releases/download/v版/...` | F | 配布元の URL の今の値の照合（Issue の F の例）。取得に失敗すればエラー。 | 消す |
| 5. curl 失敗・展開した版の不一致で既存の gitleaks を変えない | D | 「失敗しても既にある gitleaks を変えない」は場面 1 と同じ守りで、実装も同じ（置き換えは最後の `install`）。代表は SHA の不一致。 | 消す |

件数 1 → 1、行数 73 → 約 40。

##### test-verify-resonite-tooling.bash（76 行・4 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. 版を表示する | L | 表示だけ。値は比べない。 | 消す |
| 2. resoloop／Blender が動かない・版が空なら失敗 | L | `verify-resonite-tooling.bash` はそれ自体が検査（Issue の L の例）。postCreate は失敗で `fail` する。 | 消す |
| 3. NumPy が使えない実 Blender を拒否 | L | NumPy が無ければ glTF の書き出し・Meshy の doctor が import エラーで止まる（#60）。検査が通っても使う時にエラーで現れる。 | 消す |
| 4. `STEP_TOTAL` が `step "` の数と同じ | L | 進捗表示（`[33/32]`）が出るだけ。作業の結果は変わらない。F2 が postCreate の手順を撤去したときに `STEP_TOTAL` を合わせる必要はあるが、テストは要らない。 | 消す |

ファイルごと削除。件数 1 → 0、行数 76 → 0。（`STEP_TOTAL` の更新は F2 に伝える。表示の食い違いのまま残らないよう、F2 が撤去と同時に更新する。）

##### test-report-resoloop-skills.bash（78 行・4 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. プロジェクトごとの結果を表示し、差分・失敗があっても 0 で終わる | S（中） | 同梱スキルの同期の要否を postCreate で知らせる唯一の経路。終了コード 6＋`SKILL_SYNC_REQUIRED` の読み違えで「最新」と表示すると、更新が必要なことに気付けない（誤った結果の報告）。常に 0 で終わる既存の挙動も、壊れると postCreate が止まる。 | 残す。ok・stale・edited の 3 つに絞る |
| 2. プロジェクト検出（ネスト・`.resoloop.json` の無いものを除く、`./` 付きで渡す） | D | 検出の誤りは該当プロジェクトの行が出ない／ `check failed` と見える（表示の異常）。場面 1 の状態の読み取りが代表。`-dash` の名前は L（オプションとして読まれればエラー）。 | 消す |
| 3. resoloop が無ければ表示して 0 | L | 表示のみ。 | 消す |
| 4. プロジェクトが 0 件なら表示して 0 | L | 表示のみ。 | 消す |

処置のとき、スクリプトは `git` を使わず作業ツリーを走査するので、`git init`・`GIT_*` の除去・`commit` を消し、一時ディレクトリにスクリプトを写すだけにする。
件数 1 → 1、行数 78 → 約 32。

##### test-install-resoloop.bash（105 行・7 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. 未導入なら `--prerelease` で最新を導入して版を表示 | D（正例） | 導入の基本経路。場面 3 との対比で、期待の `tool update` 呼び出しを固定する。 | 残す |
| 2. 最新を導入済み（unchanged） | D | 場面 1 と同じ update の呼び出し。表示が違うだけ。 | 消す |
| 3. fork のビルド（公開版より大きい版）から `--allow-downgrade` で最新の公開版へ戻す | S（中） | 戻せなければ update が拒否され、場面 4 の経路（警告して導入済みを維持）で fork のビルドが残る。「常に最新」（#45）が黙って崩れ、気付けない。 | 残す |
| 4. update に失敗しても導入済みなら警告して続ける | L | 壊れて失敗側に倒れれば、オフラインの rebuild が止まる（postCreate が `fail`）。 | 消す |
| 5. update に失敗し導入済みが無ければ失敗（名前の一部が一致するパッケージは導入済みでない） | L | 失敗が成功になれば、`dotnet tool list` が空のため直後の `ResoLoop is missing` で止まる。 | 消す |
| 6. `resoloop --version` と `dotnet tool list` の版が違えば失敗 | L | PATH の別の resoloop を使う誤りの検査。ずれは版の食い違いの表示や、後段の `verify-resonite-tooling` で現れる。 | 消す |
| 7. 前提の失敗（一覧が取れない・SDK 無し・shim 無し） | L | `set -e` とメッセージ付きの非 0 終了。 | 消す |

件数 1 → 1、行数 105 → 約 55（偽の dotnet が大半）。

##### test-resoloop-tool.bash（37 行・2 群）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. `resoloop_version_of`（版の取り出し） | L | 解析を誤れば `install_resoloop.bash` の版の突き合わせで止まる（Issue の L の例）。 | 消す |
| 2. `resoloop_installed_version`（`dotnet tool list` の読み取り・日本語の見出し・別パッケージを拾わない） | L | 誤れば `install_resoloop.bash` の `ResoLoop is missing...` か版の不一致で止まる。`scripts/resoloop-fork.sh` も同じ関数を使うが、失敗は導入の停止として現れる。 | 消す |

ファイルごと削除。件数 1 → 0、行数 37 → 0。

##### test-shell-tools.bash（106 行・7 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. ツールが無くても `zshrc.txt` の読み込みが成功し `command not found` を出さない | L | シェルを開くたびにエラーが見える。 | 消す |
| 2. `update()` は無いツールを飛ばして 0、飛ばした項目を表示 | L | 表示・終了コード。 | 消す |
| 3. `update()` はあるツールだけを更新（実行するコマンドの一覧） | F | `zshrc.txt` の今のコマンド行の写し。 | 消す |
| 4. `cod`・`genv`・`buni` はツールが無ければ 127 と理由。`buni` は bun が無いとき `node_modules` を消さない | S（高）: buni / L: cod・genv | bun が無いのに `rm -rf node_modules` だけが走ると、再導入できずデータ（依存）を失う（Issue の「残す S」）。cod・genv の 127 とメッセージは L（genv の fzf も L）。 | buni の場面だけ残す |
| 5. `BUN_INSTALL` は `$HOME` 基準／`zshrc.txt` に `/home/vscode` を書かない | L（BUN_INSTALL）/ F∩S（絶対パスの禁止） | 固定した HOME は一時 HOME や別の利用者で、実際の `/home/vscode` を操作する（#229 の申し送り 1）。`BUN_INSTALL` の値の確認は L。 | `/home/vscode` の禁止だけ残す |
| 6. 秘密情報の env を、あるときだけ読み込んで export／無いとき無出力 | L | export が無ければ API キーが無いというエラーで現れる。無出力は表示。 | 消す |
| 7. starship の `custom.uv_python`（最寄りの `.venv` の版） | L | プロンプトの表示。ずれは毎回目に入る。 | 消す |

`zsh -n`（構文）は L なので消す。
件数 1 → 1、行数 106 → 約 38（`run_zsh`・スタブ・`buni` の場面・絶対パスの禁止）。

##### test-initialize-mounts.bash（107 行・8 場面）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| 1. `devcontainer.json` の mounts と `initialize.bash` が作るパスが同じ集合 | S（中） | initialize.bash が作らない mount の対象は Docker が root 所有で作り、以降の書き込みが権限で失敗する（`install_beforehand.bash` のコメントの事故）。2 の固定値は devcontainer.json だけを見るので、片方の誤りは 1 でしか検出できない。 | 残す（2 行） |
| 2. mount の一覧の固定値（14 個） | F∩S | mount の増減はホストの永続領域と秘密情報の露出に関わる（#36 C1）。Issue が F∩S として残す指定。 | 残す |
| 3. `initialize.bash` が一時 HOME にすべてを作り 2 回目も成功、`~/.claude.json` を消さない、秘密情報のディレクトリは 700 | S（高: `.claude.json`・中: 700） | `~/.claude.json` は認証・設定を持つ利用者所有のファイル（データの消失）。700 でないと秘密情報が読める。実行して確かめる。 | 残す（作成の確認は 1 つのループのまま） |
| 3b. `~/.claude.json` がディレクトリならエラーで終了 | L | メッセージ付きの非 0 の終了。 | 消す |
| 3c. `RESOLOOP_HOST_PATH_MAP` は WSL のときだけ env ファイルに書く | L | 誤ればテクスチャ取り込みが失敗として現れる（usaturn/resoloop#12 の経緯）。WSL 外で書かれても空でなければ接続エラー。 | 消す |
| 4. `install_beforehand.bash` の書き込み可能化の一覧が mount の一覧を含む | F | 2 つの一覧の突き合わせ。漏れた mount は初回の書き込みで権限エラーとして現れる。 | 消す |
| 5. `mounts_compare` の検出（余分な mount・余分な init・target 違い・コメントアウト・chmod 行・ファイル無し） | D/L | テストの補助（`mounts.bash`）自体の検査。場面 1 が補助を使う。補助が壊れれば場面 1 の実行が誤判定するが、`mounts.bash` は Issue の「変えないもの」なので補助の網羅は代表に絞る。拒否の正例として場面 1 の成功がある。 | 消す（`mounts.bash` は変えない） |

件数 1 → 1、行数 107 → 約 48。

##### test-install-beforehand.bash（122 行・5 群。pi の step は F2。ここは plugin 集合・agent-runner 個人設定・DSH）

| 場面 | 分類 | 理由 | 処置 |
| --- | --- | --- | --- |
| `bash -n` | L | 構文エラーは postCreate が即エラー。 | 消す |
| Claude Code のプラグインの集合が `enabledPlugins` と同じ | F | 2 つの一覧の突き合わせ。ずれれば入れたいプラグインが無いと使う時に分かる。 | 消す |
| `place_agent_runner_config`: 無いときだけ最小の個人設定を置き、既存の設定を上書きしない（XDG 3 通り×2 回） | S（中） | 利用者が書いた個人設定の上書き（#167）。XDG の 3 通りは同じ守りの D。 | 残す（`XDG_CONFIG_HOME` なしの 1 通り＋上書きされない確認） |
| 同: 壊れた symlink を置き換えない／書き込み先が無いと失敗 | D / L | 壊れた symlink は既存の設定を守る同じ守りの変種で D。書き込み不可は `mkdir`/`cp` の失敗で postCreate が止まる L。 | 消す |
| 置いた個人設定と読んでも雛形の値の変更が効く（#167） | S（中） | 雛形を丸写しすると、以降の雛形の変更が気付かないまま効かない（実際に起きた不具合）。 | 残す |
| DSH 導入 5 通り（success・npm-failure・missing-cli・version-failure・wrong-version） | success: D（正例）/ wrong-version: S（低）/ ほか: L | 版の不一致を許すと固定した DSH でないものをレビュアーに使うが、動くので気付けない。npm の失敗・CLI 無し・`--version` 失敗は `return 1` で postCreate が `fail`。 | success と wrong-version の 2 通りだけ残す（**迷い**: wrong-version を L とするなら 1 通りも要らない。残す方に倒す） |

件数 1 → 1、行数 122 → 約 68。

#### (2) 処置後の見積もり（F4 の 12 本）

| | 件数（本） | 行数 |
| --- | --- | --- |
| 現在 | 12 | 887（38+43+47+55+73+76+78+105+106+107+37+122） |
| 処置後 | 10 | 約 385（38+12+27+35+40+0+32+55+0+38+48+68） |

- 件数 83%、行数 43% が残る。ファイルが 1 本 1 件なので件数は 2 本の削除だけが効く。行数は場面の削除で半分以下になる。
- S（F∩S 含む）に当たるもの: dry-run の不削除、削除範囲の既定値、`run-tests` の終了コードと `GIT_*` の隔離、ctx7 の `--version` だけの呼び出しと版の不一致、gitleaks の SHA 不一致、スキル同期の状態の読み取り、fork の ResoLoop の戻し、buni の `node_modules`、`/home/vscode`・`/workspaces/reso-world` の禁止、mount の一覧と対応、`initialize.bash` の `~/.claude.json` と 700、個人設定の上書き、雛形の変更が効くこと、DSH の版の不一致。

#### (3) 撤去候補と根拠

撤去（コードごと）に当たるものは **無い**。この担当の対象コード（`install_*.bash`・`report-resoloop-skills.bash`・`resoloop-tool.bash`・`verify-resonite-tooling.bash`・`initialize.bash`・`cleanup-workspace.bash`）はすべて `install_beforehand.bash` などから現在も呼ばれている（`install_beforehand.bash:111,116,122,199,218,699`）。

- `mounts.bash` の `mounts_from_initialize`・`mounts_compare` はテストだけが使うが、`mounts.bash` は Issue の「変えないもの」なので手を付けない。`test-initialize-mounts.bash` の場面 1 が使い続ける。
- `resoloop-tool.bash` は `install_resoloop.bash` と `scripts/resoloop-fork.sh` が使うので残す（テストだけ消す）。
- `verify-resonite-tooling.bash` の `STEP_TOTAL` の検査を消すので、F2 が postCreate の手順を撤去したら `STEP_TOTAL`（現在 32）を実際の `step "` の数に合わせること。

#### (4) 重さが高の守りの壊し方案（使い捨てのコピーで、残したテストが失敗することを確かめる）

`mktemp -d` のコピーに `.devcontainer/` ごと写し、`bash <コピー>/.devcontainer/test-*.bash` を実行する（テストは自分の位置からルートを求める）。

| 守り（重さ） | 残すテスト | 壊し方 | 期待 |
| --- | --- | --- | --- |
| GitLeaks の SHA-256 検証（高） | `test-install-gitleaks.bash` | `install_gitleaks.bash` の `sha256sum -c --status - \|\| fail ...` の行を `true` にする（`sed -i '/sha256sum -c/,/fail "The downloaded/c true'`） | 不一致の archive を受け入れてテストが `FAIL` |
| 同: 失敗時に既存を変えない（高） | 同上 | `tar` の前（SHA の確認の前）に `install -m 0755 /dev/null "${HOME}/.local/bin/gitleaks"` を足す | `replaced gitleaks although the SHA-256 did not match` で `FAIL` |
| `run-tests` の `GIT_*` の隔離（高） | `test-run-tests.bash` | `run-tests.bash` の `while ... unset "$name"` の 1 行を消す | `a test changed the repository named by the inherited GIT_DIR` で `FAIL` |
| `run-tests` の終了コード（中） | 同上 | 最後の `exit 1` を `exit 0` にする | `expected exit 1` で `FAIL` |
| `buni` が bun の無いときに `node_modules` を消さない（高） | `test-shell-tools.bash` | `zshrc.txt` の `buni()` で `command -v bun` の確認を外す（確認を `true` に） | `buni removed node_modules although bun is missing` で `FAIL` |
| `initialize.bash` が `~/.claude.json` を消さない（高） | `test-initialize-mounts.bash` | `initialize.bash` の `.claude.json` を作る行を `: > "${HOME}/.claude.json"` に変える | `initialize.bash changed ~/.claude.json` で `FAIL` |
| 秘密情報のディレクトリの 700（中） | 同上 | `chmod 700` の行を消す | `must be mode 700` で `FAIL` |
| 個人設定の上書き禁止（中） | `test-install-beforehand.bash` | `place_agent_runner_config` の `[ -e ... ] \|\| [ -L ... ]` の早期 return を消す | `an existing personal config was overwritten` で `FAIL` |
| ctx7 の `--version` 以外の呼び出し（中） | `test-install-ctx7.bash` | `install_ctx7.bash` の末尾に `ctx7 setup` を足す | `installer ran ctx7 for more than its version` で `FAIL` |
| 絶対パスの禁止（F∩S） | `test-readme.bash`・`test-shell-tools.bash` | `.devcontainer/zshrc.txt` に `# /home/vscode` を、`.devcontainer/README.md` に `/workspaces/reso-world` を足す（コピー内の git 追跡に `git add`） | それぞれ `FAIL` |

高の守りの代表に絞った場面はない（高の守りは 1 ファイル 1 場面にしか残らない）ため、上は残した全場面の確認の案。実際の確認は、重さが高の 5 件（gitleaks 2 件・`GIT_*`・buni・`.claude.json`）を必須とし、ほかは余力で。`git grep` を使う絶対パスの禁止の確認はコピーを `git init`・`git add` しておく。

#### (5) 消せる補助

- 消すテストだけが使っていた補助: `test-readme.bash` の `column`・`ticks`・`mounts.bash` の source（表の照合）、`test-report-resoloop-skills.bash` の `git init` 一式と `GIT_*` の除去、`test-install-gitleaks.bash` の mode／URL の確認、`test-shell-tools.bash` の starship 用の Python 呼び出しと `uv_python_*.sh`、`test-install-beforehand.bash` の plugin 比較。いずれもテストファイルの中だけの補助で、別ファイルの補助は無い。
- 別ファイルの fixture・偽の CLI は無い（この 12 本はすべて自分で偽物を組み立てている）。`tools/test_support/` と `conftest.py` は触らない。
- 観察（担当外、変えない）: `cleanup-workspace.bash` の本体の安全条件（未コミット変更のある worktree を消さない、使用中を消さない）はこの領域のテストで確かめられていない。`tests/scripts` と `.agents/skills` の側にも対応するテストは見つからなかった（`git grep cleanup-workspace -- tests` は 0 件）。#234 の範囲外のため、新しいテストは足さない。

## 迷いの一覧（`integration` の一覧の先頭に並べる）

S か L か決められず、残したもの。

| テスト | 内容 | 残した理由 |
| --- | --- | --- |
| `test-pi-superagents.bash` の config 無しで止まる場面 | tier 設定が無いとき exit 1 | L 寄りだが、止まらずに tier が効かないまま起動すると気付きにくい（低） |
| 同 導入の場面（導入後の `pi list` に新拡張が無ければ exit 1） | 検査が抜けると postCreate が成功扱いで終わる | 初回の利用で気付ける L の面もあるが、失敗を成功と報告する損害に当たりうる（中） |
| `test-herdr-migration.bash` の multi ③ | 健全な兄弟 identity の pane の行き先 | S（中-低）か L か決めきれない |
| 同 ccdd の終了コード・親環境の保持 | 終了コードを握りつぶしても起動は成功する | 低 |
| `test-install-beforehand.bash` の DSH の版の不一致 | 固定した版でない CLI を使っても動く | L とも読める（低） |
| `test_concurrent_launchers_initialize_only_empty_missing_auth`（`test_pi_vertex_launchers.py`） | 先着の Pi が書いた auth を後着が上書きしないこと | 守りの確認で、`link` を `rename` に壊しても失敗しなかった（高）。空 `{}` どうしの競合では結果が同じで区別できない。この変更の前から同じ観測で、決定的な再現は難しい。空 auth の mode・内容・staging の後始末は守られている |

## 計測の結果

計測は #234 の「検証」のコマンドを、commit 済みの状態で実行した。値は PR #244 のレビュー修正（サイクル 1）の後の `2b30c3e` のもの（修正の前の `32ce013` では行数 2,501）。

| 指標 | 前（`481a047`） | 後 | 割合 |
| --- | --- | --- | --- |
| pytest（`tools/devenv_migration`） | 419 | 39 | 約 9% |
| bash のテスト（Meshy を除く） | 18 | 12 | 67% |
| 件数の合計 | 437 | 51 | 約 12%（目安の 1/3 以下を満たす） |
| 行数 | 5,778 | 2,518 | 約 44% |

- 件数は 1/3 以下に届いた。行数は約 44% で、1/3（1,926 行）には届かない。残りの行は、S の中核の長いシナリオ（vertex の native probe と OAuth/ADC の検査、`session.json` 修復の fixture、実際の git・プロセス・bwrap を動かす準備）で、Issue の見積もり（約 56%）よりは小さい。数を合わせるために気付けない損害を防ぐテストは消さない（#228 の決定 6）ので、行数の残りは `integration` の一覧で扱う
- 群ごとの実測の行数: `test_pi_provider_setup.py` 359、`test_pi_vertex_launchers.py` 691、`test_pi_shared_packages.py` 約 100、`test-pi-superagents.bash` 439、`test-herdr-migration.bash` 435、その他の bash 10 本 494
- 撤去: `install_beforehand.bash` は `STEP_TOTAL` 29（`grep -c '^step "'` も 29）。`bash -n` は通る。撤去した名前・ファイルへの参照は、`docs/superpowers/` と凍結した `docs/maatlog-poc-porting.md` 以外に残っていない（`git grep`、0 件）

### 重さが高の守りの確認（D-234-6）

`git archive` で `mktemp -d` に展開した使い捨てのコピーで、守りを 1 つずつ壊し、残したテストを実行した。元のコピーでは対象のテストがすべて通った。壊した後に失敗したか、の結果は次のとおり。

- herdr（F3）14 通り、その他の bash（F4）の重さが高の守り（gitleaks の SHA-256 検証、失敗時に既存を保つ、`run-tests` の `GIT_*` の隔離、`buni`、`~/.claude.json`）と、余力の中・F∩S の守り（700、個人設定の上書き禁止、雛形の変更が効く、ctx7、`run-tests` の終了コード、`/workspaces/reso-world`・`/home/vscode` の禁止）は、すべて失敗した。詳細の表: `mutation-F3F4.md`（セッションディレクトリ）
- pi（F1・F2）の 20 通りのうち、F1-7（同時起動で先着の auth を上書きしない）以外は、壊すと残したテストが失敗した。F1-7 は上の「迷いの一覧」のとおり。F1-4・F1-9・F2-h は、狙ったテストより先に別のテストが落ちた（残したテストのどれかで検出される）。詳細の表: `mutation-F1F2.md`（セッションディレクトリ）

守りになっていないテスト: F1-7 の「先着の auth を後着が上書きしない」部分だけ（この変更で弱めたものではない）。

### レビュー修正（PR #244 サイクル 1）で直した分析の誤り

PR 修正ループのサイクル 1 で、分析の誤りで S の守りを消した 2 件が指摘され、最小の検査を戻した（`docs/superpowers/specs/2026-10-23-create-reso-world-pr244-issue234-review-fixes-design.md`）。下の F3・F4 の表の該当行は、分析時点の記述のままで、次のとおり読み替える。

- F3「関数 6 名前の argv」「6 名前 → 3 関数」: `claude-deepinfra` などは `ccdd` と同じ関数だが、`zshrc.txt` の 3 関数は呼ばれた名前（`$funcstack[1]`）で `--dangerously-skip-permissions` を分岐するので、名前違いは同じ実体ではない。通常名に権限確認の省略が付かないこと（F∩S・権限の境界）を、`test-herdr-migration.bash` に戻した（3 組すべて）
- F4 `test-run-tests.bash` の場面 1「既定の対象（`--list`）」を L としたこと: 出力は件数と名前を表示するだけで、期待値との比較も失敗も無く、`tests/scripts/*.bash` が既定の一覧から落ちると、そのテストが 1 本も走らないまま PASS と終了コード 0 になる（S）。両方の入口を含み `lib` を含まないことの検査を、ファイル名と件数を固定せずに戻した

### 守りの確認の詳細

### 守りの確認（F3・F4、HEAD の使い捨てコピー）

元のコピーで該当テストは全て通った（rc=0）。各行は壊して実行し、元に戻した。

| # | 守り | 重さ | 壊し方 | 実行したテスト | 結果（rc） |
| --- | --- | --- | --- | --- | --- |
| 1 | サーバー稼働中の無変更 | 中 | running 判定を削除 | test-herdr-migration | 失敗した rc=1: FAIL: running must leave session unchanged |
| 2 | 状態判定の厳密さ(numeric_zero) | 中 | is not False を not status.get に | test-herdr-migration | 失敗した rc=1:  |
| 3 | 未知 version の無変更 | 中 | version 判定を削除 | test-herdr-migration | 失敗した rc=1: FAIL: unknown_version must leave session unchanged |
| 4 | 修復先がルート自身 | 中低 | ルート自身の return を削除 | test-herdr-migration | 失敗した rc=1: FAIL: workspace_root must leave session unchanged |
| 5 | 修復先の不在 | 中低 | -d/-x の確認を削除 | test-herdr-migration | 失敗した rc=1: FAIL: missing_destination must leave session unchanged |
| 6 | 複数 entry の収束防止(代入) | 中 | target_taken = True を削除 | test-herdr-migration | 失敗した rc=1:  |
| 7 | 複数 entry の収束防止(初期値) | 中 | 初期の any(...) を False に | test-herdr-migration | 失敗した rc=1: FAIL: workspace entry must remain unchanged when repair target is taken |
| 8 | pane の流れ先(迷い) | 中低 | pane_target を workspace 固定 | test-herdr-migration | 失敗した rc=1:  |
| 10 | 資格情報の漏れ(ANTHROPIC_API_KEY を配列から削除) | 高 | 配列から 1 件削除 | test-herdr-migration | 失敗した rc=1: FAIL: cc_launcher_unsets must match expected_unsets exactly |
| 11 | 資格情報の漏れ(ccdu の入力キー OPENCODE_API_KEY を削除) | 高 | 配列から入力キーを削除 | test-herdr-migration | 失敗した rc=1: FAIL: cc_launcher_unsets must match expected_unsets exactly |
| 12 | 資格情報の送り先(URL) | 高 | ANTHROPIC_BASE_URL を別 URL に | test-herdr-migration | 失敗した rc=1:  |
| 13 | 資格情報の送り先(MCP) | 高 | ENABLE_CLAUDEAI_MCP_SERVERS=true | test-herdr-migration | 失敗した rc=1:  |
| 14 | 終了コード(迷い) | 低 | ccdd の claude 行に || true | test-herdr-migration | 失敗した rc=1: FAIL: CLI exit status and parent env (got 0) |
| 9 | 資格情報の漏れ(ccddg の配列) | 高 | ccddg の env から配列を外す（153 行） | test-herdr-migration | 失敗した rc=1: ccddg.log must not contain POLLUTED_ |
| 9b | 資格情報の漏れ(ccdu の配列) | 高 | ccdu の env から配列を外す（184 行） | test-herdr-migration | 失敗した rc=1: ccdu.log must not contain POLLUTED_ |

###2・6・8・12・13 の失敗の出力は Python の AssertionError（stdin の assert）。終了コードは全て 1。

#### F4

| # | 守り | 重さ | 壊し方 | 実行したテスト | 結果（rc） |
| --- | --- | --- | --- | --- | --- |
| 1 | gitleaks SHA-256 検証 | 高 | sha256sum -c の検証を true に | test-install-gitleaks | 失敗した rc=1: FAIL: installer accepted an archive that does not match the pinned SHA-256 |
| 3 | run-tests の GIT_* 隔離 | 高 | unset の行を削除 | test-run-tests | 失敗した rc=1: FAIL: a test changed the repository named by the inherited GIT_DIR |
| 4 | run-tests の終了コード | 中 | exit 1 を exit 0 に | test-run-tests | 失敗した rc=1: FAIL: expected exit 1, got 0 |
| 5 | buni が bun 無しで node_modules を消さない | 高 | require_command bun を削除 | test-shell-tools | 失敗した rc=1: FAIL: buni removed node_modules although bun is missing |
| 7 | 秘密情報ディレクトリの 700 | 中 | chmod 700 を削除 | test-initialize-mounts | 失敗した rc=1: FAIL: ~/.config/create-reso-world must be mode 700 |
| 8 | 個人設定の上書き禁止 | 中 | 既存の早期 return を削除 | test-install-beforehand | 失敗した rc=1: FAIL: an existing personal config was overwritten: /tmp/tmp.S7j3XWL7HX/home/.config/agent-runner/config.toml |
| 9 | ctx7 を --version 以外で呼ばない | 中 | 末尾に ctx7 setup | test-install-ctx7 | 失敗した rc=1: FAIL: installer ran ctx7 for more than its version: ctx7 --version ctx7 setup |
| 10 | 絶対パス禁止 (/workspaces/reso-world) | F∩S | README に追記 | test-readme | 失敗した rc=1: .devcontainer/README.md:1:/workspaces/reso-world FAIL: .devcontainer hard-codes the workspace path |
| 11 | 絶対パス禁止 (/home/vscode) | F∩S | zshrc.txt に追記 | test-shell-tools | 失敗した rc=1: 1:# /home/vscode FAIL: zshrc.txt must not hard-code /home/vscode |

再確認（上の壊し方が守りに当たっていなかった 3 件を差し替え）

| 守り | 重さ | 壊し方 | 実行したテスト | 結果 |
| --- | --- | --- | --- | --- |
| gitleaks 失敗時に既存を変えない | 高 | SHA 確認の前に既存の実行ファイルを上書き | test-install-gitleaks | 失敗した rc=1: FAIL: installer replaced gitleaks although the SHA-256 did not match |
| initialize が ~/.claude.json を消さない | 高 | touch の前に rm -f | test-initialize-mounts | 失敗した rc=1: FAIL: initialize.bash changed ~/.claude.json |
| 個人設定が雛形の丸写しでない(#167) | 中 | 最小の個人設定の代わりに雛形を丸写し | test-install-beforehand | 失敗した rc=1: FAIL: the minimal personal config was not placed at /tmp/tmp.8ovmV4T95g/home/.config/agent-runner/config.toml |
※ F4 表の 2・6・12 行は差し替え済み（下の再確認表が有効）

### 重さが高の守りの確認: F1（pi の Python 設定）・F2（pi の導入と移行）

commit 32ce013 を `git archive` で `mktemp -d` に展開した使い捨てコピーで、守りを 1 つずつ壊し、残したテストを実行した。元のコピーでは 4 つの対象（`test_pi_provider_setup.py`・`test_pi_vertex_launchers.py`・`test_pi_shared_packages.py`・`test-pi-superagents.bash`）はすべて終了コード 0。壊した後は `git checkout` で戻した。

| ID | 守り（重さ） | 壊し方（コピー内） | 失敗したテスト | 終了コード |
| --- | --- | --- | --- | --- |
| F1-1 | 保存済み OAuth を Pi が消費・更新して失わない（高） | `pi-superagents-exec.zsh` の `--ro-bind-data 3 …` を `--bind` に | `test_real_namespace_masks_auth_for_parent_and_child_preserving_saved_files` | 1 |
| F1-2 | `GOOGLE_CLOUD_API_KEY` を外す（高） | `pigemf` の `unset GOOGLE_CLOUD_API_KEY` を削除 | `test_cloud_defaults_precedence_and_api_key_removal` | 1 |
| F1-3a | 鍵を含む auth を 0600 に保つ（高） | `pi-provider-setup.py` の auth の mode を `0o644` に | `test_update_preserves_other_providers_and_private_permissions` | 1 |
| F1-3b | 他の provider・鍵を消さない（高） | `providers[provider] = …` を `data["providers"] = {provider: …}` に | 同上 | 1 |
| F1-4 | 固定名 tmp の symlink 先を上書きしない（高） | `stage()` の `mkstemp` を固定名 `.tmp` の `os.open` に | `test_update_preserves_other_providers_and_private_permissions`（`test_existing_fixed_name_tmp…` の前に落ちた） | 1 |
| F1-5 | symlink・hardlink の先へ書かない（高） | `plain_file()` を即 `return` に | `test_rejected_models_change_no_managed_state[symlink]` | 1 |
| F1-6 | 入出力の失敗でファイルを切り詰めない（高） | `os.replace(temporary, path)` を `path.write_bytes(…)` に | `test_new_models_are_private_even_under_public_umask` | 1 |
| F1-7 | 同時起動で保存済みの auth を置き換えない（高） | 空 auth の作成を `fs.linkSync`（EEXIST なら先着を尊重）から `fs.renameSync`（上書き）に | **失敗しなかった**（終了コード 0） | 0 |
| F1-7b | 同上（空 auth の mode・staging の後始末・内容） | `{ mode: 0o644 }` / `fs.rmSync(staging…)` を削除 / 内容を `[]` に | `test_concurrent_launchers_initialize_only_empty_missing_auth`（3 通りとも） | 1 |
| F1-8 | 壊れた auth で秘密を出さない（高） | `catch` で `auth.json` の中身を stderr に出す | `test_invalid_auth_configuration_fails_closed_without_secret_output` | 1 |
| F1-9 | セッションなどの状態が host に残る（高） | auth の overlay を agent dir 全体の `--tmpfs` に | `test_real_namespace_masks_auth_for_parent_and_child_preserving_saved_files`（`test_nonauth_state…` の前に落ちた） | 1 |
| F2-a | bwrap 不在で止まる（高） | `if ! command -v bwrap` を `if false` に | `test-pi-superagents.bash`: `missing bwrap must exit 1` | 1 |
| F2-b | Vertex だけ auth overlay（高） | `pigemp) reply=(…) ;;` を `pigemp) return 1 ;;` に | `test-pi-superagents.bash`: `pigemp … must overlay auth.json` | 1 |
| F2-c | `--if-absent` が利用者の編集を保つ（高〜中） | `setup_pi_superagents.zsh` の保持の分岐を削除 | `test-pi-superagents.bash`: `--if-absent must not overwrite an existing config` | 1 |
| F2-d | 共有登録を消さない（中） | `Installing the shared skills` の前に `pi remove npm:@upstash/context7-pi` を足す | `test_rebuild_preserves_shared_packages` | 1 |
| F2-e | 退避世代を上書きしない（中） | `while [[ -e "${backup}" ]]` の連番ループを削除 | `test-pi-superagents.bash`: `two generations must be preserved` | 1 |
| F2-f | setup が settings を書き換えない（中） | `setup_pi_superagents.zsh` の末尾で `settings.json` に追記 | `test-pi-superagents.bash`: `setup changed settings bytes` | 1 |
| F2-g | tier が別ランチャーの設定を重ねない（中） | `--bind "${launcher_dir}" …` の src を `subagent.d/pigo` に | `test-pi-superagents.bash`: `piccd bind src` | 1 |
| F2-h | dry-run と実 argv の一致（中） | dry-run の `printf` に引数 `extra` を足す | `test-pi-superagents.bash`: `bind dst must equal HOME-based shared dir`（位置のずれとして別の検査が先に落ちた） | 1 |

#### 判定

- F1-7 だけ、壊しても失敗しなかった。`test_concurrent_launchers_initialize_only_empty_missing_auth` は、起動前に auth が無い状態で複数のランチャーを同時に起動し、最後の内容が `{}`・mode 0600・staging の残りが無いことを確かめる。`link`（先着を尊重）と `rename`（後着が上書き）は、空 `{}` どうしの競合では結果が同じなので、この観測では区別できない（上書きが害になるのは、先着の Pi が OAuth を書き込んだ後に後着が空で上書きする場合で、決定的に再現しにくい）。空 auth の作成そのもの（mode・内容・staging の後始末）は F1-7b の 3 通りで守られている。
- F1-4、F1-9、F2-h は、狙ったテストより先に別のテストが落ちた。残したテストのどれかが失敗する点では守りになっている。
- 守りになっていないテストは F1-7 の「先着の auth を後着が上書きしない」部分のみ。

## rebuild の後の確認の結果

未実施（利用者が rebuild した後に、Issue #234 に記録する）。
