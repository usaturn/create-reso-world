# Issue #402 piaq（Token Plan の qwen4-max-preview）取り込み Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（issue-to-pr の実行許可で作成。内容の承認ではない）
- 対象: usaturn/create-reso-world #402

**Goal:** Alibaba Cloud Model Studio の Token Plan の `qwen4-max-preview` で Pi を起動する `piaq`、既存環境への setup、runner agent `pi_alibaba_qwen4-max_max` を、本リポジトリの形で足す。

**Architecture:** provider 定義は `.devcontainer/pi-models.json` に足し、新規コンテナは `install_beforehand.bash`、既存環境は新しい `scripts/setup_pi_alibaba.zsh`（`pi-provider-setup.py` 経由）で反映する。`piaq` は `piccd` と同じ形で、定義と key を確かめてから `pi_superagents_exec` で Pi を起動する。tier 設定は `setup_pi_superagents.zsh` の `LAUNCHERS` が置く。

**Tech Stack:** zsh（ランチャー・setup）、python3（`pi-provider-setup.py`。uv 導入前でも動く）、bash（`.devcontainer/test-*.bash`）、pytest（`tools/devenv_migration/tests`）、TOML（agent-runner）

**Spec:** `docs/superpowers/specs/2026-11-11-issue-402-piaq-token-plan-design.md`

## Global Constraints

- provider 名は `alibaba`、モデルは `qwen4-max-preview`（主）と `qwen3.8-flash`（tier の cheap）
- `providers.alibaba` の値は移植元（usaturn/agent-workspace `4c425ab1dd3afe55192e752d179af566b0650a23` の `.devcontainer/pi-models.json`）と JSON として同一にする（Spec D1）
- key は `MAAS_ANTHROPIC_TOKEN`。ファイルに書かない。判定は `ccda` と同じ `*[A-Za-z0-9]*`。値を表示しない
- tier 設定の拡張は `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts`
- `[workflows]` は変えない。ほかの provider・ランチャー・`ccda` を変えない
- テストは Spec D8 の T1・T2 だけ。偽の key は `dummy-...` か実行時に組み立てた値。実 key を写さない
- python は uv で実行する（`.devcontainer/` 配下の bootstrap と zsh ヘルパーの中の python3 は例外）

## 受け入れ基準

（Spec の「受け入れ基準」をそのまま写す。controller は実装担当・レビュー担当の brief にこの節の本文を写す）

- 動作環境: Dev Container（Pi 1.5.2）。新規のコンテナ（`install_beforehand.bash` の配置と、models.json の雛形）と、`~/.pi/agent/models.json` を既に持つ既存のコンテナ（`setup_pi_alibaba.zsh` で反映）。agent-runner は個人設定が無い環境と、個人設定（`~/.config/agent-runner/config.toml`）を重ねる環境
- 実入力: `MAAS_ANTHROPIC_TOKEN` を export した通常のシェル（ランチャー起動セッションの外）からの `piaq -p "1+1 の答えを数字だけで答えて"` と対話起動。agent-runner の最小の依頼（改行と日本語を含む短いプロンプト、`--assign inspect=pi_alibaba_qwen4-max_max`）
- 防御範囲（対象）:
  - `MAAS_ANTHROPIC_TOKEN` が未設定・空・ASCII の英数字を含まない（NBSP・BOM・全角空白だけを含む）とき、`piaq` は値を表示せずに終了コード 1 で終わり、Pi を起動しない
  - models.json・provider・モデルの定義が無いとき、`piaq` は setup の案内を出して終了コード 1
  - setup は既存の models.json のほかの provider を保ち、変更するときは更新前に退避する。2 回目は何も変えない
  - key の値が models.json・ランチャーの出力・Pi のセッション記録・agent-runner の result とログに出ない
  - agent-runner の子には `env` に挙げた変数だけが渡る（既存の allowlist のまま）
- 防御範囲（対象にしない反例）:
  - 既存の Pi ランチャー（`piccd`・`pidid` など）と `ccda` の接続先・認証・モデルは変わらない。`pi-models.json` のほかの provider の定義を変えない
  - ランチャー起動セッションから key を補って新しい agent を使う経路
  - 他のランチャーの子に `MAAS_ANTHROPIC_TOKEN` が渡らないこと（`test-herdr-migration.bash` の既存の検査が引き続き通る）

## 要件と Task の対応

| 条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| key が不正なら Pi を起動しない／正しければ届く | 1 | 終了コード 1・dry-run 出力なし／`bwrap` の argv | T1 |
| 定義が無ければ setup を案内 | 1 | 終了コード 1 と `setup_pi_alibaba.zsh` の案内 | 一時 HOME で手動実行（L） |
| tier 設定が model guard の照合に通る | 1・4 | `piaq` が起動前の検査で止まらない | 実環境 |
| setup がほかの provider を保ち退避 | 2 | `keep` provider が残り、bak がある、2 回目は不変 | T2 |
| 新規コンテナへの配置 | 2 | `install -m 0755 .devcontainer/piaq` の行 | `test-install-beforehand.bash`・diff の確認 |
| runner agent | 3 | `check`・`list` に出る | agent-runner の `check`・`list`（4 で実行） |
| key の値が保存物に出ない | 4（統合） | 検索で一致 0 件 | 実環境 |
| 既存ランチャー・他の provider が不変 | 全体 | `git diff` で他の provider が変わらない | `run-tests.bash`・diff |

共有する条件: `piaq` が使うモデル ID（`qwen4-max-preview`）・provider 名・key の判定は Task 1・2・3 で共通。Task 2 の setup は Task 1 の `piaq` の `--model` を確かめる。統合の確認は Task 4（controller）が行う。

## Review Focus

- `MAAS_ANTHROPIC_TOKEN` が BOM・NBSP だけの値: `*[A-Za-z0-9]*` の判定がロケールに依らず拒否すること（T1 は全角空白を代表にする。Task 1 の Step 4 で NBSP・BOM・空・未設定も一時的に手で確かめる）
- 既存の `test_launchers_wrap_pi_with_their_own_config` が tier 設定の一覧から `piaq` を拾うので、`run_launcher` の環境に `alibaba` の定義と偽の key が無いと、`piaq` が起動前に止まりテストが落ちる（Task 1 で環境を与える）
- key が無い環境の setup: `pi --list-models` は key の無い provider を外すので、確認を省いて終了コード 0 にすること（Task 2 の T2 は key が無い環境で走る。T2 のハーネスの `pi` 偽物が `alibaba` を出すかどうかにかかわらず通ること）
- 共有の `~/.pi` で移植元の setup が同じ `providers.alibaba` を書いている: 値が同一なら setup は「already up to date」で退避ファイルを増やさないこと（Task 4 の実環境で確かめる）
- ランチャー起動セッションでの `piaq`: key が unset されるので、案内付きで終了コード 1 になること（Task 4 で確かめる）

---

### Task 1: provider 定義・`piaq`・tier 設定と key のテスト

テスト: 要（T1。S: 空白だけの key で起動すると誤った認証のまま進み、エラーで分からない）。

**Files:**
- Modify: `.devcontainer/pi-models.json`（`providers.alibaba` を足す）
- Create: `.devcontainer/piaq`（実行権限 0755）
- Create: `.devcontainer/pi-superagents/piaq.json`
- Modify: `scripts/setup_pi_superagents.zsh`（`LAUNCHERS` に `piaq`）
- Test: `.devcontainer/test-pi-superagents.bash`

**Interfaces:**
- Produces: コマンド `piaq [pi の引数...]`。終了コード 1 で止まる条件は Spec D2。起動時は `pi_superagents_exec piaq --provider alibaba --model qwen4-max-preview --models qwen4-max-preview --thinking max "$@"`
- Produces: `.devcontainer/piaq` に `--model qwen4-max-preview` の文字列がある（Task 2 の setup が確かめる。既存の setup と同じ形）

- [ ] **Step 1: 失敗するテストを書く** — `test_piaq_refuses_blank_key` を `.devcontainer/test-pi-superagents.bash` に足し、末尾の実行一覧に加える。

  - 一時 HOME（`make_home piaq with-config`）に、`.devcontainer/pi-models.json` の `alibaba` を含む models.json を置く
  - 全角空白（`$'\u3000'`）だけの `MAAS_ANTHROPIC_TOKEN` で `piaq` を dry-run（`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1`）で起動する: 終了コード 1、stdout が空（Pi の argv が出ない）、stdout+stderr に key の値が無い
  - 同じ HOME で `MAAS_ANTHROPIC_TOKEN=dummy-for-dry-run`: 終了コード 0、stdout の 1 行目が `bwrap`（陽性の対照）
  - 防ぐ損害と、陽性の対照を置く理由をコメントに書く
  - 既存の `run_launcher` に `MAAS_ANTHROPIC_TOKEN="dummy-for-dry-run"` を足し、`piaq` のときは HOME の models.json に `alibaba` の定義を置く（`test_launchers_wrap_pi_with_their_own_config`・`test_only_vertex_launchers_overlay_auth` が `piaq` を拾うため）。ヘルパの model guard の起動前の照合が `pidid` と同じく偽の catalog を必要とするなら、`pigt|pidid` と同じ `model_home` の扱いに `piaq` を加える

- [ ] **Step 2: テストが落ちることを確かめる**

  Run: `bash .devcontainer/test-pi-superagents.bash`
  Expected: `piaq` が無いことによる FAIL

- [ ] **Step 3: 実装する**

  - `pi-models.json`: 移植元の `providers.alibaba` を値ごと足す（Global Constraints）。ほかの provider は 1 バイトも変えない
  - `piaq`: `.devcontainer/piccd` の形（ヘルパの探索と source、`pi_agent_directory`、python3 の判定スクリプト）。Spec D2 のとおり models.json が無いときも `no-file` で止める。案内は `zsh scripts/setup_pi_alibaba.zsh`。key の判定は `[[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]`、案内は `read -rs 'MAAS_ANTHROPIC_TOKEN?Model Studio API key (非表示): ' && export MAAS_ANTHROPIC_TOKEN`（ランチャーの外のシェルで、値をコマンド行に書かずに export すること）
  - `piaq.json`: Spec D3
  - `setup_pi_superagents.zsh`: `LAUNCHERS` の `pidid` の後に `piaq`

- [ ] **Step 4: テストを通す・確かめる**

  Run: `bash .devcontainer/test-pi-superagents.bash` → `OK` で終了コード 0
  一時的な確認（コミットしない）: T1 の key の判定を外したコピーで T1 が落ちること。未設定・空・NBSP（`$'\u00a0'`）・BOM（`$'\ufeff'`）の key でも終了コード 1 で dry-run 出力が無いこと。一時 HOME で models.json が無い・`alibaba` が無い・モデルが無いときに案内付きの終了コード 1 になること
  Run: `jq . .devcontainer/pi-models.json >/dev/null` と `zsh -n .devcontainer/piaq`

- [ ] **Step 5: Commit**

  ```bash
  git add .devcontainer/pi-models.json .devcontainer/piaq .devcontainer/pi-superagents/piaq.json scripts/setup_pi_superagents.zsh .devcontainer/test-pi-superagents.bash
  git commit -m "feat: add piaq launcher for Alibaba Token Plan qwen4-max-preview (#402)"
  ```

### Task 2: 既存環境への setup と新規コンテナへの配置

テスト: 要（T2。S: setup がほかの provider を消す・退避しないとデータが失われてもエラーにならない）。

**Files:**
- Create: `scripts/setup_pi_alibaba.zsh`
- Modify: `.devcontainer/install_beforehand.bash`（Pi ランチャーの配置の step の見出しと `install -m 0755 .devcontainer/piaq "${HOME}/.local/bin/piaq"`）
- Test: `tools/devenv_migration/tests/test_pi_provider_setup.py`

**Interfaces:**
- Consumes: Task 1 の `.devcontainer/piaq`（`--model qwen4-max-preview`）、`pi-models.json` の `providers.alibaba`
- Produces: `zsh scripts/setup_pi_alibaba.zsh`（引数なし。key は不要。終了コード 0 で `models.json` の `providers.alibaba`、`~/.local/bin/piaq`・`pi-superagents-exec.zsh` を反映）

- [ ] **Step 1: 失敗するテストを書く** — `test_update_preserves_other_providers_and_private_permissions` を `@pytest.mark.parametrize("script", ["setup_pi_opencode_go.zsh", "setup_pi_alibaba.zsh"])` で引数化し、`SETUPS` に `"setup_pi_alibaba.zsh": "alibaba"` を足す。`Harness` の偽の `pi` の `--list-models` は、`SETUPS[script]` の provider を出すようにする（環境変数で渡すなど）。auth.json の検査は opencode-go のときだけ。テストのコメントに防ぐ損害を書く（既存の 1 行コメントを広げる）

- [ ] **Step 2: テストが落ちることを確かめる**

  Run: `uv run pytest tools/devenv_migration/tests/test_pi_provider_setup.py -q`
  Expected: `setup_pi_alibaba.zsh` が無いことによる FAIL（opencode-go の引数は PASS）

- [ ] **Step 3: 実装する** — `scripts/setup_pi_alibaba.zsh` を `scripts/setup_pi_commandcode_goat.zsh` の形で書く（Spec D4 の 1〜5）。`--agent-dir` の解決と `export PI_CODING_AGENT_DIR` は既存の setup と同じ。key の判定は `ccda` と同じ。key があるときだけ `pi --list-models <model>` の 1・2 列目で `alibaba` の 2 モデルを確かめる。最後の案内は `zsh scripts/setup_pi_superagents.zsh --if-absent`（Spec D4 の 5）。key の値を表示しない。`install_beforehand.bash` に `piaq` の配置を足す

- [ ] **Step 4: テストを通す・確かめる**

  Run: `uv run pytest tools/devenv_migration/tests/test_pi_provider_setup.py -q` → all passed
  Run: `bash .devcontainer/test-install-beforehand.bash` → 終了コード 0
  一時的な確認（コミットしない）: テストのコピーで、setup が `providers` を丸ごと置き換えるよう変えると T2 が落ちること
  Run: `zsh -n scripts/setup_pi_alibaba.zsh`

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/setup_pi_alibaba.zsh .devcontainer/install_beforehand.bash tools/devenv_migration/tests/test_pi_provider_setup.py
  git commit -m "feat: add setup_pi_alibaba and place piaq on rebuild (#402)"
  ```

### Task 3: runner agent と README

テスト: 不要（agent の定義は設定の値で F。壊れたら `agent-runner check`・`list` で L。README は文言で F）。代わりの検証: `agent-runner check`・`list`、`bash .devcontainer/test-readme.bash`、`git diff`。

**Files:**
- Modify: `.devcontainer/agent-runner.toml`（`[agents.pi_alibaba_qwen4-max_max]` を `pi_google-vertex_gemini4-argon_high` の後に。Spec D6）
- Modify: `.devcontainer/README.md`（Spec D7 の節）

**Interfaces:**
- Consumes: Task 1 の `piaq`、Task 2 の `setup_pi_alibaba.zsh`

- [ ] **Step 1: 実装する** — Spec D6 の agent とコメント（key が届く仕組みは Spec の「現状の観測」の 2 つの仕組みのとおりに書く）、Spec D7 の README の更新。ランチャーの本数・一覧を挙げる箇所は `grep -n '11 本\|13 本\|pidid' .devcontainer/README.md` などで洗い出し、実装の時点のコード（`install_beforehand.bash` の配置、`.devcontainer/pi-superagents/*.json` の数）を数えて合わせる。実機の観測は Task 4 で足すので、ここでは観測の見出しを作らない
- [ ] **Step 2: 確かめる**

  Run（リポジトリのルートで）: `uv run --project . --locked python -m tools.agent_runner check` と `... list`
  Expected: 終了コード 0、`list` に `pi_alibaba_qwen4-max_max`
  Run: `bash .devcontainer/test-readme.bash` → 終了コード 0

- [ ] **Step 3: Commit**

  ```bash
  git add .devcontainer/agent-runner.toml .devcontainer/README.md
  git commit -m "feat: add pi_alibaba_qwen4-max_max runner agent and document piaq (#402)"
  ```

### Task 4: 実環境の確認と README の観測（controller）

実環境の key と `~/.pi` を使うので、controller が行う。テスト: 不要（実機の観測）。

- [ ] `zsh scripts/setup_pi_alibaba.zsh`（既存の `~/.pi`）: 終了コード、増えた・変わった provider、退避ファイルの有無
- [ ] `zsh scripts/setup_pi_superagents.zsh --if-absent`: `piaq` の tier 設定が `subagent.d/create-reso-world/piaq/config.json` に置かれる
- [ ] 通常のシェル（`MAAS_ANTHROPIC_TOKEN` を export、ランチャーの外）で `piaq -p "1+1 の答えを数字だけで答えて" </dev/null`（1 回）: 終了コードと答え、セッション記録の provider・model・thinking
- [ ] 対話起動（1 回）: 疑似端末で `piaq` を起動して短い質問、`/quit`
- [ ] agent-runner: 個人設定が無い環境（`--config` に空のファイルなど既存の方法）と重ねた環境で `check`・`list`。`run --workflow review --assign inspect=pi_alibaba_qwen4-max_max`（改行と日本語を含む短いプロンプト、1 回）の state と `identity`
- [ ] ランチャー起動セッション相当（`MAAS_ANTHROPIC_TOKEN` を外した環境）で `piaq` が案内付きの終了コード 1
- [ ] key の値の検索: `~/.pi/agent/models.json`・Pi のセッション記録・runner の出力先・SESSION のログで一致 0 件（値は表示しない。`grep -rlF -- "$MAAS_ANTHROPIC_TOKEN"` の件数だけ）
- [ ] README に実機の観測を書いて commit（`docs: record piaq observations (#402)`）
- [ ] 最終の検証: `bash .devcontainer/run-tests.bash`、`uv run pytest tools/devenv_migration/tests tools/agent_runner -q`（agent_runner のテストの入口は README に従う）、`bash scripts/check-layout.sh`

## 実行方式と理由

`implement_task.py check` の `self` が false（`--implement devin_swe2_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で Task 1〜3 を 1 つずつ `devin_swe2_max` に依頼する（subagent-driven-development の形。並行しない）。Task 4 は実環境の key と `~/.pi` を使うので controller が行う。利用者の指示（2026-11-11）により、`devin_swe2_max` への依頼の `prompt` には、最後に「結果は JSON だけを返してください。JSON の前後に説明文・Markdown のコードフェンス・その他の文字を付けないでください。」を必ず書く。各 Task の後に controller がテストと静的チェックを実行し、Task のレビュー（controller）を行う。最後のブランチ全体のレビューは、`--merge` の PR 修正ループの 1 サイクル目で代える。

## 実行予算

- Issue 全体の能動時間の予算: 300 分（移植元 #931 の実績は約 60 分。runner の担当の起動、設計・Spec レビュー、PR 修正ループ最大 3 サイクル（各 45 分＋計画・修正）を含める）
- phase の目安: 準備・Spec・レビュー 60 分、Task 1〜3 各 30 分、Task 4 20 分、PR とループ 150 分
- worker: `implement` の役割の期限 90 分（runner の既定）。無進捗の打ち切りは runner の既定
- 再試行の上限: 同じ失敗の再試行は 1 回（`retry`・`rejected` を含め、Task ごとに依頼 3 回まで）
- checkpoint: Spec レビューの後、各 Task の後、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: README の観測を最小限にする。Task 3 の README を Task 4 にまとめる。runner の担当が同じ理由で 2 回失敗したら止まって報告（担当は利用者が決める。self で引き取らない）

## contingency（代替策）

- 最初の RED で、ヘルパの model guard の起動前の照合が偽の catalog を要すると分かったら、`pidid` と同じ `model_home` の扱いを `piaq` に使う（意味を保つ最小修正。ledger に書く）
- 実環境で tier の `alibaba/qwen3.8-flash` が model guard の照合に通らないときは、照合の失敗の内容を調べ、モデル定義（D1）を変えずに済む原因（catalog の再生成など）なら直す。定義を変える必要があれば、Spec の決定記録に変更として書く（移植元との同一性が崩れるため、理由を書く）
- `origin/main` が進んだら、feature branch に merge し（rebase・force push しない）、検証をやり直す（利用者の指示）。#401・#365 が先にマージされて `agent-runner.toml`・README が衝突したら、そちらの内容を保って解消する
- 実 API が失敗したら（認証・上限）、1 回だけ原因を確かめ、key や上限の問題なら観測できなかったこととして PR に書く。成功と書かない

## 完了

状態は `draft` のまま（実行の記録だけを足した）。

- 1 回目の run（`--implement devin_swe2_max`）: Task 1 を取り込んだ。Task 2 は担当の返答が JSON だけにならず `failed`（`runner: response_failed`）で停止した
- 2 回目の run（利用者の再指示 `--implement pi_xai_grok4_xhigh`、「Task 2 から続ける」）: Task 2〜3 を `pi_xai_grok4_xhigh`（`grok-4.7`）に依頼して取り込んだ。Task 4 は controller が行った

| Task | 担当（runner が観測したモデル） | 依頼の回数 | 所要 | Task のレビュー |
| --- | --- | --- | --- | --- |
| 1 | `devin_swe2_max`（SWE-2 Max） | 1 | 588 秒 | Approved |
| 2 | `devin_swe2_max`（failed）→ `pi_xai_grok4_xhigh`（grok-4.7） | 1＋2（うち修正 1） | 502 秒＋1197 秒＋560 秒 | 修正 1 回（T2 が退避の欠如を検出しなかった）の後に clean |
| 3 | `pi_xai_grok4_xhigh`（grok-4.7） | 1 | 674 秒 | Approved |
| 4 | controller | — | 約 15 分 | — |

controller の裁定（ledger の `Ruling:`）:

- Task 1: T1 の全角空白を `printf '\xe3\x80\x80'` で組み立てる担当の変更を採用（`$'\u3000'` は非 UTF-8 ロケールの bash で文字にならず T1 が空振りする）
- Task 2: 退避を止めた変異で T2 が通ることを確かめ、Spec D8 の T2 の守りの不足として修正に回した
- Task 3: 担当が `AGENT_RUNNER_DEPTH` を外して `agent-runner check`・`list` を実行した（読み取りのみ）。規約違反として記録し、controller が実行し直した
- Task 3: README の「無いときは終了コード 1」の誤読を招く文言を Task 4 の commit で直した

持ち越しの minor: `test-pi-superagents.bash` の models.json のコピーが 2 か所、`piaq` の判定ブロックが `piccd` と重複（Spec の指定）、T2 の `FAKE_PI_PROVIDER` の冗長と `pre_update` の重複、setup の Summary の `Models :` が 2 行、#402 の README の節が setup のヘルパの配置に触れていない
