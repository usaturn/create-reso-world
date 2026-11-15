# review-eval の収集を 4 経路 7 関数の保存点に接続する（#357）設計

## 管理・実行許可

- 状態: `draft`（`approved` ではない。内容の承認は受けていない）
- 対象: https://github.com/usaturn/create-reso-world/issues/357 （親ボード #349 の子 `review-eval-hooks`）
- 利用者の指示（2026-11-15、引用）: `/issue-to-pr #357 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_opencode-go_deepseek4-flash_max --implement pi_opencode-go_deepseek4-flash_max --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`
- 許可された範囲: issue-to-pr の委任（通常の設計判断を推奨案で決め、検証・commit・push・PR 作成・PR 修正ループ・`finalize.py` によるマージまで進める）。この指示は実行許可であり、Spec の内容の承認ではない
- 反映先: `usaturn/create-reso-world`、base `main@eb9e378bd803a77c75fa01a30d92ccf0b3682f48`、branch `feat/issue-357-review-eval-hooks`。Spec・Plan はコードと同じ PR に入れる

## 目的

`tools/review_eval` の収集（#352 の `capture.collect`）を、pr-review・review-verify・review-fix-planning・pr-review-fix-loop の helper の保存点から呼ぶ。review-eval が有効なときだけ、保存済みのレビュー記録を私有の store へ写す。既定（設定なし）は今までと同じで、何も書かない。収集の例外・遅延・失敗で、呼び出し元の結果 JSON・終了コード・標準出力を変えない。

なぜ今か: 各 helper はレビュー記録を review_dir に保存して上書きするが、保存点が収集を呼ばないため、有効にしても上書き前の版が store に残らない（`tools/review_eval/sources.rst` の分類 3）。接続を後回しにするほど、失われる版（分類 5）が増える。

## 目標・非目標・避けること

- 目標
  - 7 関数（下表）が保存点で収集を呼ぶ。有効な一時 config・初期化済みの一時 store で、保存済みの記録が store に写る（各経路 1 回以上テストで確認）
  - 無効（設定なし・`enabled = false`・`REVIEW_EVAL_CONFIG=""`）・store 未初期化・`sources` の対象外・runner の子では、store に何も書かず、helper の結果・終了コード・標準出力が変わらない
  - `attach-runner` は 30 秒の期限を review_dir 全体で共有し、期限を超えた分を収集せず、after_run を失敗させない
- 非目標
  - `tools/review_eval/**` の内部の変更（`capture.collect` と `shim.run_hook` の公開 API だけを使う。`run_hook` の既知の制約も直さない）
  - 実データ収集の有効化、過去記録の調査、replay 評価、`projects.toml` 前提のテスト補助
  - helper の結果形式・終了コード・標準出力・既存の保存処理の変更、helper 全体の AW 版への置き換え
- 避けること（技術的に動いても失敗）
  - 収集の失敗・遅延で helper の終了コードや標準出力の JSON が変わる
  - テストが利用者の実設定（`~/.config/create-reso-world/review-eval.toml`）や実 store を読む・書く
  - runner の子（レビュアー・実装担当のプロセス）が私有 store に書く

## 現状（2026-11-15、base `eb9e378b`）

- 7 helper のどれも `capture.collect`・`shim.run_hook` を呼ばない（`rg 'review_eval' .agents` で一致なし）
- 起動方法
  - `--project <TOOL_ROOT> --locked`（pydantic あり）: `review_run.py`・`dispatch.py`・`finalize.py`・`run_roles.py`・`loop.py`・`review_findings.py`（review-verify の SKILL.md は `--project --locked` で `validate` を呼ぶ）
  - `--no-project`（標準ライブラリだけ）: `upsert_pr_comment.py`（review-fix-planning の SKILL.md）。`review_findings.py` も docstring で「`--no-project` で動く」とし、標準ライブラリだけで書かれている
- `review_run.py`・`dispatch.py`・`run_roles.py`・`loop.py` は先頭で `sys.path` に repo root（`Path(__file__).resolve().parents[4]`）を足している。`finalize.py`・`upsert_pr_comment.py`・`review_findings.py` は足していない
- `tools/review_eval/README.rst`「経路・保存点を足す手順」: `tools.review_eval` は関数の中で import し、呼び出しは `except Exception` で囲む。`--no-project` の helper は `shim.py` をファイルパスで読み込み、subprocess で `hook` を起動する
- `shim.run_hook` は子プロセスへ `environ` を渡さず、相対パスを `cwd=tool_root` で解決し直す（#357 の 2026-11-09 の引き継ぎコメント）。設定が見つからないと `disabled` で黙る

## 接続する保存点（決定）

| helper（関数） | 経路 / event | 方式 | review_dir | 渡す記録 |
|---|---|---|---|---|
| `review_run.py`（`collect_outputs(command, parent, state, result)`） | pr-review / `prepare`・`complete`・`fail` | in-process | 結果の `run_record`（`<review_dir>/runs/*.json`）の 2 つ上、無ければ `review_file` の親 | 結果の `run_record`・`review_file`・`findings_file` のうち存在するもの（`files`）＋ sweep。`prepare` は上書き前の版を取るため sweep だけ |
| 同上 | pr-review / `attach-runner` | in-process、`allow_runner_child=True` | 結果の `attached`・`unchanged` の各 run record の 2 つ上。review_dir ごとにまとめる | その review_dir の run record ＋ sweep。全 review_dir で 1 つの `deadline = time.monotonic() + 30.0` を共有し、期限を過ぎたら残りの review_dir を呼ばない |
| `dispatch.py`（`collect_accepted(review_dir, files, verifier)`） | review-verify / `accept` | in-process | `dispatch.json` の `request.review_dir` | `accept` が返す `statement_candidates`・`fix_check` ＋ sweep。`context` に verifier の識別（agent・model のみ） |
| `review_findings.py`（`_collect_before_replacement(path)`） | review-verify / `validate` | shim の subprocess | 検査したファイルの親が `verified` のとき、その親の親。違えば呼ばない | sweep だけ（置き換え前の今の版を取る）。`validate` が成功（終了コード 0）したときだけ |
| `finalize.py`（`collect_result(record, record_file, result_file, result)`） | review-fix-planning / `finalize` | in-process、review_dir なし（`repository`・`pr` を渡す） | なし | 仮想記録 `@finalize/<reviewed_head 12 桁>/result.json`（保存した結果ファイルの bytes）。`--spec-commit` 無しで結果に `comment` があるとき（helper が投稿した）は、`@pr-comment/round-<round>/record.json`（`--record-file` の bytes）も |
| `run_roles.py`（`collect_review_dir(planning_file, phase)`） | review-fix-planning / `run_roles` | in-process | `--planning-file`（`<review_dir>/verified/<HEAD12>.planning.json`）の 2 つ上。`--planning-file` が無ければ呼ばない | `planning_file` ＋ sweep。`main` の `finally` で、成功・失敗のどちらでも |
| `upsert_pr_comment.py`（`collect_round_record(...)`） | review-fix-planning / `post` | shim の subprocess、review_dir なし | なし | `--records-file` があり投稿が成功したときだけ、仮想記録 `@pr-comment/round-<round>/record.json`（その bytes） |
| `loop.py`（`collect_records(event, run_dir, run, cycle, ...)`） | pr-review-fix-loop / `review`・`cycle_end`・`finish`・`recover` | in-process | `run_dir`（`<review_dir>/loop/<run_id>`）の 2 つ上 | sweep。`cycle_end` は `--record-file` の bytes を `@pr-comment/round-<round>/record.json`、`--finalize-result` の bytes を `@finalize/<サイクルの head 12 桁>/result.json` として渡す。`finish`・`recover` は `verify_loop_run=<run_id>` を渡す（参照の欠落を `lost_revision` に記録する） |

- 呼ぶ時点: 各サブコマンドの保存処理の後で、標準出力に結果を書く前。loop は 4 サブコマンドを `try/finally` で囲み、`LoopError` で止まった（hold などで記録を保存した）場合も `run_dir` が存在すれば収集する。例外は外へ出さない
- 仮想パスの round・head は記録の値（`round`・`reviewed_head`、loop はサイクルの `head`）から作る。`tools/review_eval/inventory.py` が `@finalize/{head[:12]}/result.json`・`@pr-comment/round-{round}/record.json` を引くので、その形に合わせる。値が無い・不正なときはその仮想記録を渡さない
- in-process の関数は `from tools.review_eval.capture import collect, VirtualRecord` を関数の中で import する。repo root が `sys.path` に無い helper（`finalize.py`）は、関数の中で `Path(__file__).resolve().parents[4]` を足してから import する。import の失敗を含むすべての例外を `except Exception` で握りつぶす
- shim の関数は `tools/review_eval/shim.py` を `importlib.util.spec_from_file_location` で読み込み、`run_hook(tool_root=<repo root の絶対パス>, ...)` を呼ぶ。渡すパスはすべて `resolve()` した絶対パスにする。`REVIEW_EVAL_CONFIG` が空でない相対パスなら、呼ぶ前に `os.environ` の値を絶対パスに置き換える（子は `os.environ` を継ぐ。helper はこの直後に終了するので、他の処理に影響しない）
- runner の子: `capture.collect` と `run_hook` が `AGENT_RUNNER_DEPTH` を見て何もしない。helper 側で同じ判定を重ねない。例外は `attach-runner` の `allow_runner_child=True` だけ
- 無効時: helper 側では有効かを判定せず、`collect`（`disabled`・`out_of_scope`・`store_not_initialized` を返す）と `run_hook`（設定が無ければ起動しない）に任せる（Issue の「エージェントに任せる事項」のどちらでもよい案のうち、判定を 1 か所に保つ案）
- `context` に入れるのは helper 名・サブコマンド・runner の識別子（agent・model）など、本文・秘密を含まない短い値だけ

## 古い `dispatch.json`

`dispatch.py` の `main` と `run_roles.py` の出力は既に `batch.get("unprotected_changes", [])`／`BatchResult.unprotected_changes` で読み、`accept` は `unprotected_changes` を読まない。今回は変更しない。`unprotected_changes` の無い `dispatch.json` を `accept` しても `KeyError` にならず、収集まで進むことをテストで確かめる（Issue の受け入れ条件）。

## テストの隔離

- 既存の helper のテストも、接続後は保存点で `collect` を呼ぶ。利用者の実設定を読ませないため、所有する tests ディレクトリの `conftest.py`（`.agents/skills/{pr-review,review-verify,review-fix-planning,pr-review-fix-loop}/tests/conftest.py`、`.agents/scripts/tests/conftest.py`。無いものは新規）に、`REVIEW_EVAL_CONFIG` を空文字にする autouse の fixture を足す。リポジトリ root の `conftest.py` と `tools/test_support/` は所有外なので変えない
- 収集を有効にして確かめるテストは、テストの中で `monkeypatch.setenv("REVIEW_EVAL_CONFIG", <tmp の設定>)` に上書きする。設定は `tools/review_eval/tests/support.py` の `write_collection_config`（偽の scanner）で書き、store は `review-eval store init` 相当の API で初期化する。`workspace_root` は `tmp_path`、review_dir は `tmp_path/reviews/usaturn/create-reso-world/#900-feature-demo/`
- `HOME` はワンショットの一時ディレクトリ、`GIT_*` は既存の conftest が除去する。実 PR・ネットワーク・実データ・秘密値・モデル本文は使わない。記録本文には複数行・非 ASCII（日本語）を含める

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）の feature worktree の root で `uv run --locked pytest`。review-eval は既定で無効
- 実入力: review_dir の `<model>.md`（複数行・日本語）・`findings/*.json`・`runs/*.json`・`verified/*.json`・`verified/*.planning.json`・`loop/<run_id>/run.json`・`cycle-<n>.json`、review-verify の `dispatch.json`（`unprotected_changes` 無しの古い形を含む）、finalize の結果 JSON、判断の記録 JSON（`review-records/v2`）
- 防御範囲
  - 書かない条件: 設定なし・`enabled = false`・`REVIEW_EVAL_CONFIG=""`・store 未初期化・`sources` で対象外・runner の子（`attach-runner` 以外）・期限超過
  - 対象の反例（写す）: 有効な設定と初期化済み store。`attach-runner` は `AGENT_RUNNER_DEPTH` があっても写す
  - 収集が例外を投げても（`collect` を例外にする差し替え）、helper の終了コード・標準出力は収集なしと同じ
- テスト（採用基準の S。壊れても気付けない、無効時に黙って書く・有効時に黙って写さない・期限超過で after_run を失敗させる・収集の例外で結果が変わる、を防ぐ）
  - 4 経路の collection テスト（新規 4 ファイル）。各経路で「有効なら store に写る」1 件と「無効なら store に何も書かれず結果が同じ」1 件を代表にする。経路ごとに組み合わせを網羅しない
  - `attach-runner` の期限: 過去の deadline 相当（`time.monotonic` を進める差し替え）で、after_run の結果・終了コードが変わらず、期限後の review_dir を収集しないこと
  - 収集の例外: 1 経路の代表で、`collect` が例外でも結果が変わらないこと
  - 古い `dispatch.json` の `accept`
  - shim 経路（`upsert_pr_comment.py`・`review_findings.py validate`）は `run_hook` の呼び出し引数（絶対パス・仮想パス・route・event）と、無効時に subprocess を起動しないことを確かめる（実際の `uv run` の起動はしない）
- 既存テストの退行 0 件: 4 経路の tests と `.agents/scripts/tests`、`bash scripts/check-layout.sh`

## 文書

- `.agents/skills/pr-review-fix-loop/references/records.md` に「収集の保存点」の 1 節を足す（4 サブコマンドの後に収集すること、既定で無効、結果を変えないこと）
- `tools/review_eval/README.rst`・`sources.rst` の「#357 で接続する予定」は `tools/review_eval/**` の所有外なので変えない（記述の更新は review-eval-core 側の後続とし、PR 本文に書く）

## 決定記録

| # | 決定 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|---|
| D1 | 先行条件 #443 の扱い | open の #443 を待たずに着手する | #443 の完了を待つ | #443 は未着手で、推奨案 (a) は `tools/agent_runner/runner.py` だけを変え `loop.py` と重ならない。本 Issue の先行条件は「#443 が別案 (b) を選ぶ場合」に限る | issue-to-pr の委任。#443 が (b) で `loop.py` を変えて先に入ったら base 前進の追随で衝突を検出し、重なれば停止 |
| D2 | 収集の方式 | `--project` で動く helper は in-process、`upsert_pr_comment.py`・`review_findings.py` は shim の subprocess | すべて shim／すべて in-process | `sources.rst`・README の予定どおり。`review_findings.py` は `--no-project` でも動く仕様（docstring）なので、pydantic に依存しない shim にする | 委任 |
| D3 | 無効時の判定 | helper 側で判定せず `collect`・`run_hook` に任せる | helper 側で `shim.enabled_config` を先に見る | 判定を 1 か所に保ち、`collect` の `disabled` と同じ結果になる | 委任（Issue の「任せる事項」） |
| D4 | loop の収集時点 | 4 サブコマンドを `try/finally` で囲み、`LoopError` の後も `run_dir` があれば収集 | 成功したときだけ | hold・abort の記録も保存点で保存される。結果・終了コードは `finally` の中で変えない | 委任 |
| D5 | テストの隔離 | 所有する 5 つの tests ディレクトリの conftest に `REVIEW_EVAL_CONFIG=""` の autouse | root `conftest.py`・`tools/test_support/` に全体の隔離を作る | Issue が「所有する tests ディレクトリ内で完結」「所有外の共通基盤が要るなら停止」と決めている | 委任。所有外の変更が要ると分かれば停止して coordinator に相談 |
| D6 | finalize の判断の記録 | `--spec-commit` 無しで結果に `comment` があるときだけ `@pr-comment` を渡す | 常に渡す | sources.rst「投稿した finalize.py」。create-reso-world の PR は planner が `upsert_pr_comment.py` で投稿済みで、そちらが取る | 委任 |
| D7 | `review_findings.py` の review_dir | 検査したファイルの親が `verified` のときだけ、その親の親を sweep | 文書の `pr` から `review_target.py` で探す | SKILL.md は一時ファイルを `VERIFIED_DIR` に置く。推測で別の review_dir を選ばない | 委任 |
| D8 | README・sources.rst の「予定」記述 | 変えない | 本 PR で更新する | `tools/review_eval/**` は所有外（Issue の対象外） | 委任。PR 本文に残件として書く |

## 実装担当に任せること

- 各 `collect_*` の細部（`context` の項目、ファイルの存在確認、例外の握りつぶし方）
- collection テストの fixture の構成（偽の記録の作り方、`collect` の差し替え方法）
- `records.md` の 1 節の文面
