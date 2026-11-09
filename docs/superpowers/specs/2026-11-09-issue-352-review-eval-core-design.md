# Issue #352: review-eval の基盤（設定・私有 store・capture・inventory・ledger・packets・docs）

## 管理・実行許可

- 状態: draft（内容の承認は記録していない）
- 対象: https://github.com/usaturn/create-reso-world/issues/352（親ボード #349 の子 `review-eval-core`）
- 実行許可: 利用者の明示 `/issue-to-pr` と引数
  `#352 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max`。
- 許可の範囲: 通常の設計判断を推奨案で決めること、検証、commit、push、PR の作成、PR 修正ループ（`finalize.py`）によるマージまで。設計内容の承認ではない。
- 基準: usaturn/create-reso-world / origin / refs/heads/main / `0b5bcb60fd24692b0de3aa2224a7d5847f121bea`（#352 本文の「対象 branch: main」「PR の base は main」と一致）。着手時に捕捉した `144f3ed535fe969aa79ed1fe132128d176017cb8` から、push の前の確認までに PR #366（emission editor の文書と、同 Issue #3 に限る `AGENTS.md` の委任）のマージで進んだ。利用者が 2026-11-09 に「rebase して続行」を選んだので（決定 D13）、rebase してから base を取り直し、検証をやり直した。
- 予約: `refs/heads/agent-claims/issue-352` = `ffa8cdce9a98e0f7122640c566dc550f9418e337`（#352 の issuecomment-6734204168 に記録）。
- 着手前の確認: #352 に先行（`blocked_by`）・コメント・既存 PR・branch・worktree・claim は無かった。親 #349 の実行マップでも先行なし。

## 目的

`tools/review_eval` を新設し、4 経路（pr-review・pr-review-fix-loop・review-fix-planning・review-verify）が保存するレビュー記録を、上書き・削除される前に出典付きで私有の保存先へ写せる土台を作る。
収集は既定で無効とし、設定ファイル・承認の記録・`store init` が揃ったときだけ動く。
この子は収集の土台（設定・store・capture・inventory・ledger・packets・CLI・docs）までを作る。4 経路の helper への接続は #357（`review-eval-hooks`）が行う。

## 移植元と現状（調査の結果）

- 移植元: usaturn/agent-workspace（AW）`0eea76aa` の `tools/review_eval/`（18 ファイル、約 5,800 行）と、テスト補助 `tools/test_support/review_eval.py`・`review_eval_ledger.py`。全ファイルを `gh api` で取得し、tree の blob SHA と `git hash-object` が一致することを確かめた。
- AW 固有の依存は次の 5 か所だけである。ほかのモジュール（`canonical`・`models`・`formats`・`scanner`・`store`・`ledger`・`ledger_ops`・`ledger_state`・`packets`）は AW の環境の値を参照しない。
  1. `config.py` の `check_registered`（`tools.workspace.load_registry` で `projects.toml` を読む）と、それを呼ぶ `config.load_active`・`capture._collect`・`cli._config_check`
  2. `shim.py` の既定の設定パス（`~/.config/agent-workspace/review-eval.toml`）と、hook の起動（`uv run --project <tool_root>/tools/devenv`）
  3. `capture.identify_review_dir` と `inventory._legacy_dirs` の旧配置の判定（`reviews/#<N>-*` だけ）
  4. テスト補助の `write_projects_toml`（git の checkout と `projects.toml` を作る）
  5. `README.rst`・`sources.rst` の AW のパス・コマンド・`public/reviews/`
- CRW の review_dir は AW と同じ `PARENT_ROOT/reviews/<owner>/<repo>/#<N>-<branch>/`（`.agents/scripts/review_target.py`）で、`/reviews/` は gitignore の対象である。記録の形式も同じ（`review-findings/v2` の `KINDS`、`pr-review-fix-loop/v1` の run・cycle・diagnostic、pr-review の `## Review timing`、`findings/`・`runs/`・`verified/`・`loop/<run_id>/cycle-<n>/` の配置）。4 経路の helper（`review_run.py`・`dispatch.py`・`finalize.py`・`run_roles.py`・`upsert_pr_comment.py`・`review_findings.py`・`loop.py`）も同じ名前で存在する。
- CRW の `reviews/` の直下には `usaturn/`（新配置）と `old/` があり、`old/` の下に旧配置 `#<N>-<branch>/` が約 40 個ある。`external/resoloop/reviews/#<N>-*` にも、resoloop の旧配置が 10 個ある。
- CRW は Python 3.14（`requires-python = ">=3.14"`）で、AW の `except A, B:`（括弧の無い複数例外）をそのまま使える。root の `pyproject.toml` は pydantic を依存に持ち、`testpaths` に `tools` を含むので `tools/review_eval/tests` も収集される（変更不要）。
- CRW の `tools/test_support/plugin.py` に `outside_runner` fixture がある（AW と同じ）。AW の `tools/test_support/isolation.py`（テストの起動時に `REVIEW_EVAL_CONFIG` を空にする全体のプラグイン）に当たるものは CRW に無い。

## 範囲と除外

変更するファイルは #352 本文の「変更してよい」に限る。

- `tools/review_eval/`（新規）: `__init__.py`・`__main__.py`・`cli.py`・`config.py`・`models.py`・`canonical.py`・`formats.py`・`capture.py`・`scanner.py`・`shim.py`・`inventory.py`・`store.py`・`ledger.py`・`ledger_ops.py`・`ledger_state.py`・`packets.py`・`README.rst`・`sources.rst`・`tests/`
- `README.md`: 「構成」の `tools/` の行に `review_eval` を足すだけ
- `pyproject.toml`・`.gitignore`: 確認だけで変更しない（理由は決定 D10）

除外（#352 本文のとおり）: 4 経路の helper への `collect` の呼び出し（#357）、`projects.toml`・`tools/workspace`・`tools/devenv` の追加、`write_projects_toml`、実データの収集の有効化、過去の記録の調査、`reviews/old` の移行、`tools/test_support/` の変更（所有外。全体の隔離プラグインは #357 への持ち越し）。

## 設計

### 1. 移植の方針

AW `0eea76aa` の `tools/review_eval` を基準にし、上の 5 か所だけを CRW に合わせて変える。
次の 11 ファイルは AW の内容を変えずに置く: `__init__.py`・`__main__.py`・`canonical.py`・`models.py`・`formats.py`・`scanner.py`・`store.py`・`ledger.py`・`ledger_ops.py`・`ledger_state.py`・`packets.py`（`__init__.py` は空）。
CLI のサブコマンド・終了コード・JSON の形・store の形（`review-eval-store/v1`）・observation と failure の形・台帳（`review-eval-ledger/v1`）・packet と回答の形は AW と同じにする。#357 は `capture.collect` と `shim.run_hook` を AW と同じ引数で使える。

### 2. 設定（`config.py`・`shim.py`）

- パス: 環境変数 `REVIEW_EVAL_CONFIG`。空文字は明示の無効。未設定のときは `$XDG_CONFIG_HOME/create-reso-world/review-eval.toml`（`XDG_CONFIG_HOME` が絶対パスのときだけ。それ以外は `$HOME/.config/create-reso-world/review-eval.toml`）。
- ファイルが無ければ `not_configured`（無効）で、何も書かない。`enabled = false` も何も書かない。
- 形式は AW と同じ（`schema_version = 1`・`enabled`・`approved_by`・`approved_on`・`store`・`workspace_root`・`max_store_bytes`・`max_artifact_bytes`・`max_sweep_files`・`scan_timeout_seconds`・`lock_timeout_seconds`・`secret_scanner`・`[[sources]]`）。
- `enabled = true` のときは `approved_by`・`approved_on`・`sources` が必須（AW と同じ）。
- `store` と `workspace_root` は絶対パスの必須の項目で、既定値は無い。`store` は `workspace_root/reviews` の中に置けない（AW と同じ）。CRW では `workspace_root` に親 checkout（`PARENT_ROOT`）を書く。
- `sources` は明示の許可リストで、登録（`projects.toml`・`external-tools.toml`）を照合しない。`check_registered` を削除し、`load_active`・`capture._collect`・`cli._config_check` から呼び出しを外す。代わりに各 source の形を検証する。
  - `repo` は `<owner>/<repo>`。owner は `[A-Za-z0-9][A-Za-z0-9-]*`、repo は `[A-Za-z0-9._-]+` で `.` 始まりでない（`capture` の review_dir の規則と、`inventory.review_dirs` が走査できる形に合わせる）
  - `routes` は 4 経路の空でない部分集合で、重複しない（AW と同じ）
  - `since` と `until` が両方あれば `since <= until`
  - `repo` は大文字・小文字を区別せずに重複しない（AW と同じ）
- 設定の誤りは `ConfigError` で、メッセージに設定値を含めない（AW と同じ。pydantic の `loc` と `type` だけを出す）。
- `shim.run_hook` は `uv run --project <tool_root> --locked python -m tools.review_eval hook ...` を `cwd=<tool_root>` で起動する。`tool_root` は CRW の親 checkout の root（root の `pyproject.toml`・`uv.lock` を使う）。それ以外（runner の子では起動しない、`enabled` が true のときだけ起動する、失敗を標準エラーの 1 行にする）は AW と同じ。

### 3. 旧配置と範囲外の配置（`capture.py`・`inventory.py`）

- 旧配置は `reviews/#<N>-*`（AW と同じ）と `reviews/old/#<N>-*`（CRW が旧配置を移した場所）の 2 つ。`identify_review_dir` は、`reviews` からの相対パスが `(#<N>-*)` か `("old", #<N>-*)` のとき `legacy_layout` にする。
  - `collect` は旧配置の本文を取らず、`legacy_layout` の failure を 1 件書いて `held` を返す（AW と同じ動作）。failure の `pr` はディレクトリ名の番号、`repository` は null。
  - `reconcile` の `counts.legacy_layout` は、`reviews/` と `reviews/old/` の直下の `#<N>-*`（symlink を除く）の合計にする。
  - `reviews/old/<repo>/#<N>-*`（3 階層）は、owner が `old` の新配置として扱う（GitHub の owner 名として有効なため、旧配置と区別できる）。
- `external/*/reviews/`（resoloop などの checkout の中の旧配置）は `workspace_root/reviews` の外なので範囲外である。`collect` は `out_of_scope`（`outside_reviews`）で何も書かず、`reconcile` は走査も計数もしない。
- 旧配置を取り込む手順は AW と同じ（利用者が repo を確かめ、`reviews/<owner>/<repo>/#<N>-<branch>/` へ複製してから `ingest` する。元は移さない）。この子では移行しない。

### 4. 秘密検査

AW と同じ。既定は gitleaks の `dir`（`--redact`・`--exit-code 99`・JSON レポート・`--ignore-gitleaks-allow`・空の ignore ファイル、`GITLEAKS_CONFIG*` を外す）。検出したら本文を保存せず、`withheld_secret` の observation（形式名は既知のものだけ、SHA・入力のパスは残さない）と `secret_withheld` の failure を書く。検出値・本文を JSON・ログ・標準出力・標準エラーに書かない。CRW の gitleaks は `.devcontainer/install_gitleaks.bash` が入れる版で、`dir` を使える。

### 5. テスト

- テストの補助は `tools/review_eval/tests/support.py` に置く（AW の `tools/test_support/review_eval.py` と `review_eval_ledger.py` をまとめ、`write_projects_toml` を削除し、一時の設定ファイルだけを書く）。`tools/test_support/` は所有外なので変えない。
- `tools/review_eval/tests/conftest.py` の autouse fixture が、各テストの前に `REVIEW_EVAL_CONFIG` を空文字にする（このディレクトリのテストが利用者の実設定を読まないため。AW の isolation プラグインに当たる）。収集を有効にして確かめるテストは、テストの中で一時の設定に上書きする。
- テストは fake の記録・fake の Git（`tmp_path` の中の review_dir）・fake の scanner だけを使い、実 PR・実データ・実 store・ネットワーク・実 gitleaks を使わない。秘密検査のテストは、`ghp_` を含むファイルを gitleaks の JSON レポートの形で報告する偽の scanner を使う（AW は実 gitleaks を使っていた。#352 本文の「fake の scanner だけ」に合わせて変える）。トークンはテストの実行時に組み立て、ファイルに書かない。
- 実 gitleaks での既定の argv の確認は、コミットしない手動の確認で行う（Plan の Task 6）。

### 6. 文書

- `README.rst`: AW の運用手順を CRW に合わせる（前提条件・コマンドの形 `uv run --locked python -m tools.review_eval`・設定パス・設定例の値・`sources` が明示の許可リストであること・旧配置と `external/*/reviews`・テストの隔離・検証コマンド）。「自動取得の接続点」は、#357 で接続する予定の表であり、この版では helper が `collect` を呼ばないことを明記する。実データの収集を有効化しないことを明記する。
- `sources.rst`: AW の 4 経路の対応表を、CRW の helper を読んで確かめた内容に直す。CRW に無い関数・確かめられなかった項目は「不明」と書く。収集の接続（AW の `review_run.collect_outputs` など）は「#357 で接続する」と書き、今あるものとして書かない。
- `README.md`: 「構成」の `tools/` の説明に `review_eval（レビュー記録の私有の保存先への収集。既定は無効）` を足す。

## 決定記録

各項目: 選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件。どれも利用者の承認ではなく、エージェントの決定である。

- **D1 移植の方針**: AW を基準にし、AW 固有の 5 か所だけを変える / 再設計、ledger・packets を除いた部分移植 / #352 本文が全モジュールを列挙し、#357 が AW と同じ API を前提にする。AW で検証済みの挙動を保ち、差分を小さくする / 委任（推奨案）。
- **D2 設定パス**: `${XDG_CONFIG_HOME}/create-reso-world/review-eval.toml`（XDG は絶対パスのときだけ） / `~/.config/review-eval/config.toml`（agent-runner の形）、AW の `agent-workspace/` のまま / AW の「ワークスペース名のディレクトリ」に直接対応し、#352 本文の「相当を CRW 向けに決める」に合う。相対の XDG を無視するのは XDG の仕様と agent-runner に合わせる / 委任。
- **D3 `sources` の検証**: 登録を照合せず、形（`<owner>/<repo>`・routes・期間・重複）を検証する / `external-tools.toml` の照合、検証なし / CRW の未登録 repo のレビュー経路を妨げない（#352 本文）。形の誤りは設定の誤りとして早く止める / 委任。
- **D4 `workspace_root`**: 設定の必須の絶対パスのまま / ツールの位置から推定、`PARENT_ROOT` を自動で解決 / ツールは worktree からも実行されるので位置からの推定は別の root を指しうる。明示の値は AW と同じで、取り違えが起きない / 委任。
- **D5 旧配置**: `reviews/#<N>-*` と `reviews/old/#<N>-*` を `legacy_layout`（保留・計数）、`external/*/reviews` は範囲外（計数しない） / `reviews/old` を `not_review_dir`（`failed`）にする、`external/*/reviews` を `legacy_layout` として数える / `failed` は保存点のたびに標準エラーに出て紛らわしい。`external/` を数えるには `workspace_root/reviews` の外を走査することになり、収集の範囲が広がる。3 階層の `reviews/old/<repo>/#<N>-*` は owner `old` として新配置と区別できる / 委任（#352 本文が Spec での決定を求めている）。
- **D6 hook の起動**: `uv run --project <tool_root> --locked` / `--no-project`、`tools/devenv` を作る / CRW は root の pyproject・uv.lock を使う（#352 本文）。pydantic が要る / 委任。
- **D7 テストの補助の置き場所**: `tools/review_eval/tests/support.py` と `conftest.py` / `tools/test_support/` に置く（AW と同じ） / `tools/test_support/` は #352 の「変更してよい」に無い。全体の隔離プラグインは、他の helper のテストが収集を呼ぶ #357 で要る（持ち越し） / 委任。
- **D8 テストの範囲**: AW の 19 件（capture 9・reconcile 1・store 3・ledger 3・packets 3）を移し、CRW 固有の S の項目を足す（無効時・承認の欠落で書かない、sources の許可リスト、旧配置と `external/*/reviews`、store の権限、`max_artifact_bytes`、reconcile の旧配置の計数） / AW のテストだけ、受け入れ条件ごとの網羅 / どれも、壊れてもエラーにならずに収集・漏れ・取り違えが残る項目（AGENTS.md の S）。CLI の `status`・`config check` の出力と終了コードはエラーの経路または表示なので、テストにせず手動で確かめる（L） / 委任。
- **D9 秘密検査のテスト**: 偽の scanner（gitleaks の JSON の形）で検出させる / AW どおり実 gitleaks / #352 本文の「fake の scanner だけ」。実 gitleaks の argv は手動で確かめる / 委任。
- **D10 `pyproject.toml`・`.gitignore`**: 変えない / testpaths に `tools/review_eval/tests` を足す、store のパスを ignore に足す / `testpaths` は既に `tools` を含む。store に既定値は無く、リポジトリの中に固定の store を作らない。`/reviews/` は既に ignore の対象 / 委任。
- **D11 README.md**: 「構成」の 1 行に足すだけ / 段落を足す、足さない / 入口は README.rst に置き（#352 本文）、構成の一覧に無いと見つけにくい / 委任。
- **D12 `status` の挙動**: AW どおり（設定が無ければ `{"enabled": false}` で 0、設定はあるが store を初期化していなければ 2、未処理の failure があれば 1） / `enabled = false` なら store を見ずに 0 / #352 本文の受け入れと一致し、AW と同じ表示を保つ / 委任。
- **D13 base の移動（利用者の判断）**: feature branch を新しい `main`（`0b5bcb60`）に rebase し、base を取り直して全検証をやり直してから公開する / ここで止める / 利用者が 2026-11-09 に選んだ（issue-to-pr の push の前の確認で base の移動を観測して止まり、確認した）。移動した commit は #352 の所有ファイルと重ならない / 利用者の判断（この run の、この移動に限る）。

## 受け入れ基準

#352 本文の「受け入れ」と同じ。各項目の確かめ方は Plan の受け入れ基準に書く。

- 設定ファイルが無いとき、`status` は `{"enabled": false}` を出して終了コード 0 になり、何も書かない
- `enabled = false` のとき、`capture.collect` は何も書かない
- `enabled = true` でも store を `store init` していなければ収集せず、`status` は終了コード 2 になる
- `approved_by`・`approved_on`・`sources` が欠けた `enabled = true` は設定エラーになる
- store は 0700、ファイルは 0600。既存を上書きしない（一時ファイル + `os.link`）
- blob と observation は上限を超えたら保存しない。上限・失敗理由を JSON に残す
- gitleaks が検出したら保存しない。検出値・モデル本文・秘密値を JSON・ログ・標準出力に書かない
- `sources` は明示の許可リストで、未登録 repo でも設定に書けば対象にできる
- `reviews/old` と `external/*/reviews` の扱いが Spec に明記され（上の 3 章）、テストで固定される
- `inventory`・`reconcile`・`ledger`・`packets` は fake の記録だけで動き、実 PR・実データ・ネットワークを使わない
- `uv run pytest tools/review_eval/tests` が通る
- 退行防止: `tools/` の既存テストと `bash scripts/check-layout.sh` が通る

## 持ち越し（#357 など）

- 全体のテストの隔離（AW の `tools/test_support/isolation.py`）: 他の helper のテストが `collect` を呼ぶようになる #357 で要る。`tools/test_support/` の所有は #357 か coordinator が決める
- 4 経路の helper への接続と、`sources.rst` の「改修」の列の実装（#357）
- 実データの収集の有効化、`reviews/old`・`external/*/reviews` の移行、過去の記録の調査（利用者の確認の後の別の作業）
