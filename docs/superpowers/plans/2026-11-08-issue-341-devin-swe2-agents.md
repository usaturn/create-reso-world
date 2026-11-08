# Devin の agent 名の変更と SWE-2 Medium の追加 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 雛形の Devin の agent を `devin_swe2_max` に改名して `devin_swe2_medium` を足し、README の命名規則・説明・移行手順を合わせる。

**Architecture:** 既存の雛形 TOML と `.devcontainer/README.md` への差分の取り込みだけで、コードは変えない。Task 1・2 は runner の担当（`claude-code_sonnet_default`）に 1 つずつ順に依頼し、設定の読み込み・同一モデルの判定・全体の検証（Task 3）は司令塔が統合担当として行う。

**Tech Stack:** TOML、Markdown、uv、既存の `tools/agent_runner`。

**Spec:** `docs/superpowers/specs/2026-11-08-issue-341-devin-swe2-agents-design.md`

状態: `draft`。issue-to-pr の実行許可で進める。内容の承認ではない。

## Global Constraints

- 新しい名前は `devin_swe2_max`（`model = "swe-2-max"`）と `devin_swe2_medium`（`model = "swe-2-medium"`）。どちらも `runtime = "devin"`、`command = ["devin"]`、`model_key = "swe-2"`、`env = ["HOME", "PATH"]`
- 既定の `[workflows.review.assignments.inspect]` は `["pi_openai-codex_gpt6-sol_max", "devin_swe2_max", "pi_opencode-go_deepseek4-flash_max"]`。Medium は既定のどの割り当てにも入れない
- `swe-2-high`・lightning 系、ほかの agent の改名、旧名の alias、個人設定の書き換えはしない
- README の #305 の旧名対応表、`docs/superpowers/` の過去の Spec・Plan、`.agents/skills/issue-to-pr/evals/validation.md`、テストの入力例、`.devcontainer/zshrc.txt` のランチャーは変えない
- 新しいテストは書かない（Spec の決定記録「テスト」）
- 日本語は AGENTS.md の「日本語表現」に従う
- 固定 base は usaturn/create-reso-world / `refs/heads/main` / `25b7b5a020e5f67d74807534e1b3390a54c9c5b1`。移動を観測したら止まる。マージはループの `finalize.py` だけ

## 受け入れ基準

- 動作環境: WSL2 上の Dev Container（Ubuntu 26.04）、uv が管理する Python、worktree `/workspaces/reso-world/.worktrees/issue-341-devin-swe2-agents` のルートを cwd にする。runner の担当の中では `AGENT_RUNNER_DEPTH=1` なので `python -m tools.agent_runner check`・`list` は `nested_invocation` で拒否される。担当は `load_config` と pytest で確かめ、`check`・`list` は司令塔が行う
- 実入力: 実際の雛形 `.devcontainer/agent-runner.toml`、実際の個人設定 `~/.config/agent-runner/config.toml`（Devin の名前は無い）、`AGENT_RUNNER_CONFIG` で指す一時的な個人設定（親 checkout の `tmp/agents/issue-341.8ff800qg/` の下に置き、コミットしない）、日本語の README の段落
- 防御範囲:
  - 対象: 同じ役割に `devin_swe2_max` と `devin_swe2_medium` を並べると、起動の前に `duplicate_model` で拒否される
  - 受け入れる反例: どちらか 1 つだけを、ほかのモデルの agent と同じ役割に並べた設定（例: `["pi_openai-codex_gpt6-sol_max", "devin_swe2_medium"]`）
  - 対象外: 個人設定に旧名 `[agents.devin_swe2-max_default]` の完全な定義（`model = "swe-2-max"`、`model_key` なし）を残し、`devin_swe2_medium` と並べた設定は拒否されない。README はこの挙動を「拒否されない」と書き、旧名の節を消す手順を案内する

## Review Focus

1. 個人設定に旧名の完全な定義を残し、`devin_swe2_medium` と同じ役割に並べた設定 — 拒否されない。README がそう書いていること（Task 3 の Step 3 で実際の挙動を確かめる）
2. 個人設定が workflow の `agents`・`fallback` で旧名を参照するだけの設定 — 雛形から旧定義が消えるので `invalid_reference` で止まる。README の移行の節が、参照を新しい名前に変える手順を書いていること（Task 3 の Step 3）
3. 2 つの新しい agent を同じ役割に並べた設定 — `duplicate_model`。片方だけなら受け入れる（Task 3 の Step 2）
4. `--assign inspect=devin_swe2_medium` のように Medium を単独で選ぶ指定 — 受け入れる（`check` には `--assign` が無いので、`load_config` に同じ割り当てを渡して確かめる。Task 3 の Step 2）
5. README の #305 の表と過去の記録 — 変わらない（Task 3 の Step 5 の `git diff`）

---

### Task 1: 雛形の Devin の agent

**Files:**
- Modify: `.devcontainer/agent-runner.toml:116-120`（`[agents.devin_swe2-max_default]` の節）
- Modify: `.devcontainer/agent-runner.toml:171-172`（`[workflows.review.assignments.inspect]`）

**Interfaces:**
- Produces: agent 名 `devin_swe2_max`・`devin_swe2_medium` と `model_key = "swe-2"`。Task 2 の README と Task 3 の検証がこの名前と値を使う

- [ ] **Step 1: `[agents.devin_swe2-max_default]` の節を、コメント付きの 2 つの節に置き換える**

  同じ位置に、まず `#` のコメントを 2 行ほど書く: SWE-2 は tier（medium・high・max）を `--model` の UID で選ぶ。tier は effort の軸なので、名の effort の段に置く。2 つは同じ `model_key` なので同じモデルとして扱い、同じ役割に並べられない。続けて `[agents.devin_swe2_max]`、`[agents.devin_swe2_medium]` を Global Constraints の値で書く（キーの順は `runtime`・`command`・`model`・`model_key`・`env`）。

- [ ] **Step 2: 既定の inspect の 2 人目を `devin_swe2_max` に直す**

  `agents = ["pi_openai-codex_gpt6-sol_max", "devin_swe2_max", "pi_opencode-go_deepseek4-flash_max"]`。上のコメントは変えない。

- [ ] **Step 3: 雛形を読み込んで確かめる**

  Run:
  ```bash
  uv run --project /workspaces/reso-world --locked python -c "
  from pathlib import Path
  from tools.agent_runner.config import load_config
  c = load_config(Path('.devcontainer/agent-runner.toml'))
  print(sorted(n for n in c.agents if n.startswith('devin')))
  print({n: (c.agents[n].model, c.agents[n].model_key) for n in c.agents if n.startswith('devin')})
  print(c.workflows['review'].assignments['inspect'].agents)
  "
  git grep -n 'devin_swe2-max_default' -- .devcontainer/agent-runner.toml
  ```
  Expected: 1 行目が `['devin_swe2_max', 'devin_swe2_medium']`、2 行目が `swe-2-max`・`swe-2-medium` とどちらも `swe-2`、3 行目が Global Constraints の 3 人。`git grep` は何も出さず終了コード 1。

- [ ] **Step 4: 既存の設定のテストを実行する**

  Run: `uv run --project /workspaces/reso-world --locked pytest tools/agent_runner/tests/test_config.py -q`
  Expected: すべて passed。

- [ ] **Step 5: Commit**

  ```bash
  git add .devcontainer/agent-runner.toml
  git commit -m "feat(devcontainer): rename Devin agent to devin_swe2_max and add SWE-2 Medium (#341)"
  ```

**テストの要否:** 不要。名前・値の誤りは雛形の読み込みと `check`・`list` でエラーになる（L）。`model_key` の比較は既存の `test_config.py` が確かめている（D）。

### Task 2: README の命名規則・説明・移行

**Files:**
- Modify: `.devcontainer/README.md:839-842`（「agent の命名と同一モデルの比較」の規則の段落）
- Modify: `.devcontainer/README.md:860-862`（既定の `review.inspect` の記述）
- Modify: `.devcontainer/README.md:885-886`（`model_key` を付けた agent の段落）
- Modify: `.devcontainer/README.md:931` の後（「Command Code GOAT の契約終了後の移行」の節の末尾と、`## pi の旧拡張・MCP 設定の移行` の間）に新しい節

**Interfaces:**
- Consumes: Task 1 の agent 名と `model_key = "swe-2"`

- [ ] **Step 1: 命名規則の段落を一般化する**

  今の「model は系列・メジャー版・tier の小文字で表し、…effort 未指定は `default` とする。」を次の内容にする。段落の形は保つ。
  - tier はモデルの種類（`sol`・`flash` など）を指す
  - slug に含まれる effort の軸の tier（Devin の `swe-2-max` の `max`、Cursor の `grok-4.7-xhigh` の `xhigh`）は model の段に入れず、effort の段に置く
  - effort は設定値を使い、設定値が無ければ model の値（slug）に含まれる実効の effort を使い、どちらも無ければ `default` とする
  - 例: `devin_swe2_max` は Devin / SWE-2 / max（`model = "swe-2-max"` の slug の実効値）を表す。既存の `cursor_grok4_xhigh` も同じ規則であることが分かるように書く

  その後の「この規則は雛形の名前にだけ適用し、…改名しない。」の文は残す。

- [ ] **Step 2: 既定の `review.inspect` の記述を直す**

  `` `pi_openai-codex_gpt6-sol_max,devin_swe2-max_default,pi_opencode-go_deepseek4-flash_max` `` の 2 人目を `devin_swe2_max` にする。ほかの文は変えない。#305 の表（846-858 行）は変えない。

- [ ] **Step 3: `model_key` の段落に SWE-2 を足す**

  DeepSeek の文の後に、次の内容を足す。
  - SWE-2 の `devin_swe2_max`・`devin_swe2_medium` にも同じ `model_key = "swe-2"` を付けている
  - `devin_swe2_medium`（SWE-2 Medium）は既定のどの割り当てにも入っておらず、`--assign` か個人設定で選べる
  - 2 つは同じ `model_key` なので、同じ役割に並べると `duplicate_model` で拒否される

- [ ] **Step 4: 移行の節を足す**

  見出しは `### Devin の agent 名の変更（#341）`。次の内容を書く。
  - #341 で `devin_swe2-max_default` を `devin_swe2_max` に改名し、`devin_swe2_medium` を足した。#305 の表は当時の変更記録なので書き換えない。#305 より前の `devin-swe` も、今の名前は `devin_swe2_max`
  - 自動の移行・旧名の alias は無い。個人設定（上の「場所の解決規則」で確かめる）をバックアップしてから、workflow の `agents`・`fallback` の旧名（`devin-swe`・`devin_swe2-max_default`）を `devin_swe2_max` に変える。変えなければ `invalid_reference` で止まる
  - 個人設定に旧名の `[agents.*]` の節を残すと、雛形の `model_key = "swe-2"` を継承しないので、`devin_swe2_medium` と同じ役割に並べても同じモデルとして拒否されない。独自の上書きが無ければ旧名の節を消し、雛形の `devin_swe2_max` を継承させる。上書きが要るなら `[agents.devin_swe2_max]` に移してから旧名の節を消す
  - 編集後は、リポジトリのルートで上の `check` と `list` を実行する
  - この環境の個人設定には Devin の名前が無いので、移行は要らない

- [ ] **Step 5: 差分を確かめる**

  Run:
  ```bash
  git diff -- .devcontainer/README.md | grep -n '^[-+]' | head -80
  git grep -n 'devin_swe2-max_default\|devin-swe' -- .devcontainer/README.md
  ```
  Expected: 削除行（`-`）は Step 1〜3 の段落の行だけで、#305 の表の行は含まない。`git grep` が出す行は、#305 の表の 1 行と新しい節の中の旧名だけ。

- [ ] **Step 6: Commit**

  ```bash
  git add .devcontainer/README.md
  git commit -m "docs(devcontainer): document devin_swe2_max naming and migration (#341)"
  ```

**テストの要否:** 不要。README の文言を照合するテストは F に当たる。Step 5 の差分の確認と、Task 3 の実際の挙動との照合で代える。

### Task 3: 統合の確認と全体の検証（司令塔）

**Files:** 変更しない（このPlan の記録だけ）。一時的な個人設定は親 checkout の `tmp/agents/issue-341.8ff800qg/configs/` に置く。

**Interfaces:**
- Consumes: Task 1 の雛形、Task 2 の README

- [ ] **Step 1: 雛形単独と実際の個人設定で `check`・`list` を実行する（R1・R2・R3）**

  Run（worktree のルート）: `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner check` と `list` を、`AGENT_RUNNER_CONFIG` を付けない実際の解決（個人設定あり）と、`schema_version = 1` だけの一時設定を `AGENT_RUNNER_CONFIG` で指した場合の両方で実行する。
  Expected: どれも終了コード 0。`list` に `devin_swe2_max`・`devin_swe2_medium` があり、`devin_swe2-max_default` が無い。`load_config` の実効の inspect が Global Constraints の 3 人。

- [ ] **Step 2: 同一モデルの判定を確かめる（R4、Review Focus 3・4）**

  一時的な個人設定 3 つを `AGENT_RUNNER_CONFIG` で指して `check` を実行する。
  - `[workflows.review.assignments.inspect]` に `agents = ["devin_swe2_max", "devin_swe2_medium"]` — Expected: 終了コード 0 以外、reason が `duplicate_model`
  - `agents = ["pi_openai-codex_gpt6-sol_max", "devin_swe2_medium"]` — Expected: 終了コード 0
  - 同じ役割で `agents = ["devin_swe2_max"]`、`fallback = ["devin_swe2_medium"]` — Expected: `duplicate_model`

- [ ] **Step 3: README に書いた移行の挙動を確かめる（R5、Review Focus 1・2）**

  - 旧名 `[agents.devin_swe2-max_default]` の完全な定義（`runtime = "devin"`、`command = ["devin"]`、`model = "swe-2-max"`、`env = ["HOME", "PATH"]`）と、`agents = ["devin_swe2-max_default", "devin_swe2_medium"]` — Expected: 終了コード 0（拒否されない）
  - 定義を持たず `agents = ["devin_swe2-max_default"]` だけ — Expected: `invalid_reference`

- [ ] **Step 4: README の記述と雛形・実際の挙動を照合する（R6）**

  Task 2 の各段落を、Task 1 の雛形と Step 1〜3 の結果と照合する。名前・`model_key`・既定の構成・拒否される／されない条件が一致すること。

- [ ] **Step 5: 全体の検証（R7）と範囲の確認**

  Run（同期）:
  ```bash
  bash .devcontainer/run-tests.bash
  bash scripts/check-layout.sh
  uv run pytest tests/skills .agents/skills .agents/scripts tools
  git diff --stat 25b7b5a020e5f67d74807534e1b3390a54c9c5b1...HEAD
  git grep -n 'devin_swe2-max_default' -- ':!docs/superpowers' ':!.devcontainer/README.md'
  ```
  Expected: 3 つの検証が終了コード 0。変更ファイルは雛形・README・この Spec・Plan だけ。`git grep` は何も出さない。

- [ ] **Step 6: 最後の全体レビュー**

  固定 base からの差分を、新しい読み取り専用のレビュアー（サブエージェント）に、受け入れ基準と同じ本文を付けて渡す。Critical・Important の指摘は runner の担当に修正を依頼する（1 回まで）。

- [ ] **Step 7: 最後の commit の後、clean な HEAD で検証し直し、argv・終了コード・ログ・HEAD・base を親 checkout のセッションディレクトリに記録する**（issue-to-pr の 5 章）

**テストの要否:** 不要。Step 1〜3 は一時的な設定での実行で確かめ、コミットしない。

## 要件照合

| Spec の条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| R1 2 つの定義と旧名の不在 | Task 1（Step 1・3）、Task 3（Step 1・5） | 読み込み結果、`list`、`git grep` | `load_config`・`list`・`git grep` |
| R2 既定の inspect | Task 1（Step 2・3）、Task 3（Step 1） | 実効の割り当て | `load_config`（雛形単独と個人設定） |
| R3 `check`・`list` | Task 3（Step 1） | 終了コード 0 と `list` の出力 | CLI |
| R4 `duplicate_model` と反例 | Task 3（Step 2） | reason と終了コード | 一時的な個人設定 |
| R5 旧名の定義を残した挙動 | Task 3（Step 3） | 拒否されないこと／参照だけなら `invalid_reference` | 一時的な個人設定 |
| R6 README | Task 2、Task 3（Step 4・5） | 差分と記述の一致 | `git diff` と読解 |
| R7 全体の検証 | Task 3（Step 5・7） | 終了コード 0 | README の「テスト」の 3 コマンド |

共有する条件（雛形の名前・`model_key` と README の記述、設定の読み込み・同一モデルの判定）は、Task 3 で司令塔が統合担当として確かめる。`swe-2-medium` の存在は 2026-11-08T08:34:41Z に `devin models list` で確かめた（Spec の「現状」）。

## 実行方式

`implement_task.py check` の `self = false`（利用者の `--implement claude-code_sonnet_default`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、`superpowers:subagent-driven-development` の形を使う。Task 1・2 を 1 つずつ順に依頼し（並行しない）、取り込んだ後に司令塔が関連テストを実行し、Task のレビューを新しいサブエージェントに依頼する。Task 3 は司令塔が自分で行う。失敗を理由に self で実装を引き取らない。

作業領域（ledger・brief・報告・review package）は親 checkout の `tmp/agents/issue-341.8ff800qg/sdd/2026-11-08-issue-341-devin-swe2-agents/`、runner の依頼ごとの `RUN_DIR` は `agent_tmp.py mkdir issue-341-implement` で作るディレクトリの下に置く。

## 実行予算

- Issue 全体の能動時間: 360 分（#337 の実績 約 360 分の予算と同程度。Task 2 つ＋統合と、ループの最大 3 サイクル）。ledger は親 checkout の `tmp/agents/issue-341.8ff800qg/budget.jsonl`
- phase の目安: 準備・Spec・Plan 35 分、Task 1・2 の依頼と取り込み・レビュー 45 分、統合の確認・全体の検証・全体レビュー 35 分、公開 15 分、ループ 3 ×（レビュー 45 分＋計画・修正 30 分）＝ 225 分
- worker: runner の `implement` の役割の期限 90 分（`deadline_seconds = 5400`）。Task 1・2 は通常 15 分ほどで終わる見込み。無進捗の打ち切りは runner の期限に任せ、司令塔は途中で止めない。Task のレビュー・全体レビューのサブエージェントは同期で待つ
- 再試行の上限: 同じ信頼性の失敗の再試行は 1 回まで。`retry`・`rejected` の依頼し直しは Task ごとに 1 回まで、レビュー指摘の修正の依頼も Task ごとに 1 回まで。安全の失敗は再試行せず全体停止
- checkpoint: phase の境界、予算の 50%（180 分）・100%、runner の依頼が失敗した直後
- 縮小・切り出し・方法変更の候補: runner の担当が使えないときは止まり、担当を変えるかは利用者に返す（self での引き取りはしない）。README の移行の節で記述の意見が割れたら、Issue の対応内容 4 に書かれた項目に絞る。ループが上限に達したら、修正を push 済みのまま未完了として報告する

## contingency（代替策）

- 最初の確認で実出力・API の前提が違うと分かったら（例: `check` の reason の出し方、`load_config` の属性名）、仕様の意味を保つ最小の確かめ方の変更を ledger に残して続ける。意味が変わる場合は止まる
- runner の担当が `nested_invocation` などで検証できなかったと報告したら、司令塔が Task 3 で同じ検証を行い、担当に回避させない（`AGENT_RUNNER_DEPTH` を外さない）
- base の移動を観測したら、旧/新 SHA と必要な再検証を報告して止まり、捕捉した値を置き換えない
- 本物の Devin・有料のモデルを起動して確かめることはしない（`devin models list` の読み取りだけ）
