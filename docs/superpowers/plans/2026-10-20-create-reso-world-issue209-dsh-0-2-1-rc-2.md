# Issue #209: DeepSeek Harness を 0.2.1-rc.2 に更新する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** headless レビュアー用の DSH の固定を `0.2.1-rc.2` に上げ、手順・由来の記録を新しい版に合わせ、実 CLI と偽 provider の通しで互換を確かめた結果を残す。

**Architecture:** 互換の確認（ソースの比較と、runner の実経路での新旧の通し）は Spec の段階で済み、アダプターの挙動は変えない。変更は導入スクリプトの版の 1 か所、`.devcontainer/README.md` の手順、版の由来のコメント、移植の記録への追記だけ。最後に、変更後の commit で入口のテストと実 CLI の通しをもう一度行う。

**Tech Stack:** bash、npm（`@deepseek-ai/dsh`）、Python 3.14 + uv（agent-runner）、bubblewrap

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue209-dsh-0-2-1-rc-2-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/209
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-209-dsh-0-2-1-rc-2`（branch `feat/issue-209-dsh-0-2-1-rc-2`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #209 --merge`）
- 実行方式: inline（`superpowers:executing-plans`）。理由は Spec の D-209-11
- 確認用スクリプト・導入物・ログ: `/workspaces/reso-world/tmp/agents/issue-209.5_nf818o/`（`e2e/dsh_e2e.py`、`install-0.2.1-rc.2/`・`install-0.2.0-rc.2/`、`swap-upgrade/`・`swap-rollback/`、`baseline/`。commit しない）

## Global Constraints

- 固定の版: `0.2.1-rc.2`。allowlist は `@deepseek-ai/dsh-subprocess-local,koffi,node-pty` のまま
- アダプター（`tools/agent_runner/adapters/dsh.py`）の patch・正規表現・判定、`dsh_identity.py`、fixture の内容は変えない（D-209-2・D-209-4）
- テストを足さない（コードの挙動を変えないため。`AGENTS.md` の「テストの採用基準」。版の値をテストに写さない）
- 実 API・実 key・共有 `~/.dsh` を使わない。今のコンテナの大域の `dsh` を入れ替えない
- `docs/maatlog-poc-porting.md` の R-3 は期待値と記録先だけを合わせ、rebuild 前後の実測列は書き換えない（D-209-7）

## Review Focus

- `install_deepseek_harness` の照合が、版を上げた後も導入された版と固定の不一致で止まること。`.devcontainer/test-install-beforehand.bash`（偽の npm・dsh で一致・不一致・失敗を確かめる、版に依存しないテスト）が通ることで確かめる
- README の上げる・戻す手順のコマンドが、導入スクリプトと同じ allowlist と書き方であること。Task 2 の手順で、README のコマンドの文字列を一時の prefix でそのまま実行して確かめる（一時の prefix の確認は Spec の段階で済んでいるが、README に書いた形で 1 回実行する）
- コメントの書き換えで、正規表現・fixture・テストの判定が変わっていないこと。Task 3 の `git diff` がコメント行だけであることと、DSH のテスト 283 件で確かめる
- 変更後の commit で、新版の実 CLI の通しが Spec の結果と同じであること（Task 4）
- 既存のコンテナの `dsh`（`0.2.0-rc.2`）を前提にした手順が README に残っていないこと（rebuild 後の確認の版）

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1. 固定が `0.2.1-rc.2`、照合を保つ、一時 prefix の新規導入で一致 | Task 1・Task 4 | `install_beforehand.bash` の `version`、`test-install-beforehand.bash` の PASS、`install-0.2.1-rc.2/install.log` の `install_exit=0` と `dsh --version` | `bash .devcontainer/run-tests.bash`、Spec の段階の導入の記録 |
| 2. 実 CLI と偽 provider で経路が通り、拒否と通常の失敗を取り違えない。新旧で同じ | Task 4 | `results-*.json` の 7 シナリオの状態・ツール結果の 1 行目・session・identity | `e2e/dsh_e2e.py` を変更後の commit で新版に対して実行し、Spec の表と比べる（新旧の比較は Spec の段階の `results-all.json`） |
| 3. `dsh-ccd`・`dsh-go` の定義のまま起動し、定義の値が session に残る | Task 4 | success の identity と go-offline の `request/header` | 同上 |
| 4. 入口のテストが成功 | Task 4 | 終了コード 0、DSH のテスト 283 件 | `README.md` の「テスト」の 3 つのコマンド |
| 5. README の上げる・戻す手順、rebuild 後の確認 | Task 2・Task 4 | README の記述、手順の実行結果 | Task 2 の Step 3 |
| 6. 共有 `~/.dsh` を使わず、分離を保つ | Task 1・Task 2 | mount・plugin の追加が無いこと | `git diff`（`.devcontainer/mounts.bash`・`devcontainer.json`・`initialize.bash` に変更が無い） |
| 7. #175 への記録 | PR の作成後（5 章） | #175 のコメント | `gh issue view 175 --comments` |

共有する前提は「アダプターの挙動を変えない」と「版の値は導入スクリプトと README の 2 か所」だけで、Task 4（統合確認）が、変更後の commit で入口のテストと実 CLI の通しをまとめて確かめる。

## 実行予算

- Issue 全体の能動時間の予算: 360 分（ledger: `/workspaces/reso-world/tmp/agents/issue-209.5_nf818o/budget.jsonl`。ledger の開始は 23:45 JST で、それより前の準備と調査の約 20 分は含まない）。目安は調査と Spec・Plan 90 分（済み）、Task 1〜3 30 分、Task 4 40 分（テストと通しの待ちが大半）、レビューと PR 30 分、PR 修正ループ 最大 3 サイクル × 60 分（レビューの期限 45 分＋計画・修正）
- worker は使わない（inline）。長時間の実行（`run-tests.bash`・pytest・`dsh_e2e.py`）はバックグラウンドで実行し、終了コードで確かめる。1 回の期限は 50 分（`dsh_e2e.py` は `timeout 3000`）
- 再試行の上限: 同じ signature の信頼性の失敗（テストの時間切れ・環境の I/O の停止・npm の取得の失敗）は 2 回まで。安全の失敗（実 API への送信・共有 `~/.dsh` への書き込みの疑い）は再試行せず止まる
- checkpoint: Task 3 の後、Task 4 の後（`budget show`）、PR 修正ループの各サイクルの後
- 縮小・方法変更の候補: 入口のテストが環境の要因で落ちたら、基準（`f2350a4`）の同じ実行と比べて差分だけを判定する。実 CLI の通しが環境の要因で動かなければ、Spec の段階の結果（同じ HEAD のアダプター）と、変更がコメント・文書だけであることで代え、PR に明記する

## Task 1: 導入スクリプトの固定を上げる

テストの要否: 足さない。守る挙動（照合で止まる）は既存の `test-install-beforehand.bash` が版に依存せずに確かめている。版の値をテストに写すのは「作らない型」の 3。

**Files:**
- Modify: `.devcontainer/install_beforehand.bash:176`（`install_deepseek_harness` の `local -r version="0.2.0-rc.2"`）

- [ ] **Step 1:** `version` を `"0.2.1-rc.2"` にする。`native_scripts`・`npm install -g --allow-scripts=...`・照合は変えない
- [ ] **Step 2:** `bash .devcontainer/test-install-beforehand.bash` を実行する。期待: `PASS: postCreate parses, ...` と終了コード 0
- [ ] **Step 3:** commit する（`git add .devcontainer/install_beforehand.bash`、メッセージ `feat: pin DSH headless CLI to 0.2.1-rc.2 (#209)`）

## Task 2: `.devcontainer/README.md` を新しい版に合わせる

テストの要否: 足さない（文書だけの変更）。代わりに、書いたコマンドを一時の prefix で実行し、`test-readme.bash` を含む `run-tests.bash` で確かめる。

**Files:**
- Modify: `.devcontainer/README.md` のツール表の DSH の行（31 行目付近）、DSH の説明の段落（44〜49 行目付近）、「DSH headless レビュアー」の節（566〜590 行目付近）

- [ ] **Step 1:** ツール表の版を `0.2.1-rc.2` にする
- [ ] **Step 2:** 説明の段落と「DSH headless レビュアー」の節に、次を書く
  - headless は保存済みの key を読まず（`0.2.1` 系で headless が `credentials`・`authorization`・`deepseek-account` を無効にした）、key はアダプターが呼び出しごとに作る環境変数名で渡すので、作業対象の `.env` や共有の保存済み key が使われないこと
  - rebuild 後の確認の版を `0.2.1-rc.2` にし、実機の記録先を #175（#151 からも辿れるように）にする
  - rebuild せずに上げる・戻す手順: `npm install -g --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty @deepseek-ai/dsh@<版>` の後に `dsh --version` で版を確かめる。戻す版は `0.2.0-rc.2`。DSH の状態は呼び出しごとの `DSH_HOME` にあり、移行する共有の状態は無いこと。戻した版は次の rebuild で固定の版に戻ること
- [ ] **Step 3:** README に書いた上げる・戻すのコマンドを、`/workspaces/reso-world/tmp/agents/issue-209.5_nf818o/` の下の新しい一時 prefix（`env HOME=... npm_config_cache=... npm install -g --prefix ...` で README と同じ引数）で実行し、`dsh --version` が上げた版・戻した版になることを確かめる。期待: 両方とも終了コード 0 で版が一致
- [ ] **Step 4:** commit する（`git add .devcontainer/README.md`、メッセージ `docs: update DSH headless procedures for 0.2.1-rc.2 (#209)`）

## Task 3: 版の由来のコメントと移植の記録を直す

テストの要否: 足さない（コメント・文書だけ）。代わりに `git diff` がコメント・文書の行だけであることと、DSH のテストで確かめる。

**Files:**
- Modify: `tools/agent_runner/adapters/dsh.py:45`（`# DSH 0.2.0-rc.2: dsh-tools.serviceAsk / dsh-sandbox.approveEscalation,`）
- Modify: `tools/agent_runner/tests/adapters/dsh/test_adapter.py:629`（文面の由来）・`:844`〜`:845`（fixture の由来）
- Modify: `docs/maatlog-poc-porting.md:108`（比較表の DSH の行）・`:227`（R-3）・`:244`〜`:247`（「#151 の DSH headless の確認で変わる点」）

- [ ] **Step 1:** `dsh.py:45` のコメントを、`0.2.0-rc.2` と `0.2.1-rc.2` で同じ文面であることが分かる形にする（例: `# DSH 0.2.0-rc.2 and 0.2.1-rc.2 (unchanged): dsh-tools.serviceAsk / dsh-sandbox.approveEscalation,`）。他の行は変えない
- [ ] **Step 2:** `test_adapter.py:629` を同じ形にする。`:844` の fixture の由来は、`0.2.0-rc.2` で生成したことを残し、`0.2.1-rc.2` の実 CLI（直接と PTC）でアダプターが読む 1 行目が同じことを確かめた旨を 1 行足す
- [ ] **Step 3:** `docs/maatlog-poc-porting.md:108` の理由の列の末尾に「#209 で `0.2.1-rc.2` に上げた（現在の版と手順は `.devcontainer/README.md`）」を足し、担当 Issue の列を `#151・#209` にする。R-3 の期待値の `dsh --version` を `0.2.1-rc.2`、実機の記録先を #175 にし、「#151 の DSH headless の確認で変わる点」の節にも書く。実測列は変えない（最終レビューの指摘で追加。ledger の Final: Ruling）
- [ ] **Step 4:** `git diff -U0` で、`dsh.py`・`test_adapter.py` の変更がコメント行だけであることを確かめる
- [ ] **Step 5:** `uv run pytest tools/agent_runner/tests/adapters/dsh -q` を実行する。期待: 283 passed
- [ ] **Step 6:** commit する（3 ファイル、メッセージ `docs: record DSH 0.2.1-rc.2 provenance (#209)`）

## Task 4: 統合確認（変更後の commit）

テストの要否: 足さない。入口のテストと、commit しない確認用スクリプトで確かめ、結果をこの Plan の「検証の記録」と PR に書く。

**Files:**
- Modify: この Plan の「検証の記録」（結果を書く）

- [ ] **Step 1:** `git status --porcelain` が空で、HEAD が Task 3 の commit であることを確かめる
- [ ] **Step 2:** 入口のテストを worktree のルートで実行する（バックグラウンド、ログは `issue-209.5_nf818o/verify/`）
  - `bash .devcontainer/run-tests.bash`
  - `bash scripts/check-layout.sh`
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools`
  - 期待: すべて終了コード 0。基準（`f2350a4`）と比べて失敗が増えていない
- [ ] **Step 3:** `E2E_TAG=final uv run --project <worktree> --locked python -B /workspaces/reso-world/tmp/agents/issue-209.5_nf818o/e2e/dsh_e2e.py <worktree> /workspaces/reso-world/tmp/agents/issue-209.5_nf818o 0.2.1-rc.2` を実行する（出力先を Spec の段階の結果と分けるため、実行前に `e2e/0.2.1-rc.2` を `e2e/0.2.1-rc.2-spec` に移す）。期待: Spec の表と同じ 7 つの結果
- [ ] **Step 4:** 結果（検証した HEAD、各コマンドの argv・終了コード・ログの完全パス）を「検証の記録」に書き、commit する（この Plan だけ、メッセージ `docs: record Issue #209 verification`）
- [ ] **Step 5:** Step 4 の commit は Plan だけの変更だが、`--merge` の検証の再利用（issue-to-pr 5 章）は「PR の head と同じ HEAD」が条件なので、Step 4 の commit（最後の commit）で `git status --porcelain` が空なことを確かめ、Step 2 の 3 つのコマンドをもう一度実行する。実 CLI の通し（Step 3）は、アダプター・テストが Step 3 の HEAD から変わっていないので繰り返さない
- [ ] **Step 6:** Step 5 の HEAD・argv・終了コード・ログの完全パスを `issue-209.5_nf818o/verify/` に記録し、`finalize.py` の `--checks-file` の形（review-fix-planning の `references/execution.md` の 3 章）のファイルも作る。この記録は commit しない（PR 本文に転記する）

## 検証の記録

ログはすべて `/workspaces/reso-world/tmp/agents/issue-209.5_nf818o/` の下にある（commit しない）。

- 基準（`f2350a4`）: `uv run pytest tools/agent_runner/tests/adapters/dsh -q` → 283 passed（`baseline/dsh-tests.log`）
- 導入（Spec の段階）: 一時の HOME・npm cache・prefix で `npm install -g --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty @deepseek-ai/dsh@0.2.1-rc.2` → `install_exit=0`、`dsh --version` → `0.2.1-rc.2`（`install-0.2.1-rc.2/install.log`）。旧版も同じ手順で `0.2.0-rc.2`
- 上書きの上げ下げ: `swap-upgrade.result`（`0.2.0-rc.2` → `0.2.1-rc.2`）・`swap-rollback.result`（`0.2.1-rc.2` → `0.2.0-rc.2`）とも終了コード 0 で版が一致
- Task 1: `bash .devcontainer/test-install-beforehand.bash` → PASS
- Task 2: README に書いたコマンドを、文字列はそのままで `npm_config_prefix` だけ一時の場所に向けて実行し、`dsh --version` が `0.2.0-rc.2` → `0.2.1-rc.2` → `0.2.0-rc.2`、どれも終了コード 0（`readme-procedure/`。観測した版の値は `readme-procedure/versions.txt`）
- Task 3: `uv run pytest tools/agent_runner/tests/adapters/dsh -q` → 283 passed（`sdd/task3-dsh-tests.log`）。`tools/` の差分はコメント行だけ
- Task 4（HEAD `077ed13`、検証の前後とも `git status --porcelain` は空。`verify-1/`）
  - `bash .devcontainer/run-tests.bash` → 終了コード 0、33 本 PASS（475 秒）
  - `bash scripts/check-layout.sh` → 終了コード 0
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools` → 終了コード 0、3501 passed（1196 秒）
  - 実 CLI と偽 provider の通し（新版、`e2e/results-final.json`）→ 7 シナリオとも、Spec の段階の新版（`e2e/results-all.json`）と旧版の結果に一致
- ブランチ全体のレビュー（opus、`f2350a4..077ed13`）: Critical・Important なし、Minor 3。R-3 の期待値の指摘は直した（`f4b2ae5`）。dsh-go の上流の接続先への実接続が未確認であることは PR と #175 に書く
- 最後の HEAD での入口のテストのやり直し（Task 4 の Step 5）は、この記録の commit の後に行い、結果は PR 本文と `verify-2/` に書く

## 完了

（PR の作成後に書く）
