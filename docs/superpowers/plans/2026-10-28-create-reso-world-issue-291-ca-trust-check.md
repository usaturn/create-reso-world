# Issue #291 トラストストアの確認と更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理: usaturn/create-reso-world。対象: usaturn/create-reso-world #291
- 状態: draft（内容の承認は未取得。`/issue-to-pr #291 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge` の実行許可で進める）
- 設計時の base: `4f7e64f5fb9655fed59bff12121474c538cfb109`

**Goal:** 開発コンテナの主なクライアントが eMudhra の侵害された中間CA を信頼していないことを 1 つのコマンドで確かめられるようにし、postCreate で `ca-certificates` を最新へ上げる。

**Architecture:** `.devcontainer/verify-ca-trust.bash` が 6 つのクライアントで確認用ホストへ接続し、出力にある証拠だけで 3 つの判定に分ける。postCreate は `apt update` の直後の独立した step で `ca-certificates` を上げる。文書は `.devcontainer/README.md` に集め、ルートの README からは参照する。

**Tech Stack:** bash、OpenSSL 3.5 の `s_client`/`s_server`、curl、git、`uv run --no-project python`、Node.js の `fetch`、`uv pip compile`。

**Spec:** `docs/superpowers/specs/2026-10-28-create-reso-world-issue-291-ca-trust-check-design.md`

## Global Constraints

- 判定の表示は「信頼していない」「信頼している」「判定不能」の 3 語。終了コードは 0（すべて信頼していない）・1（信頼している がある）・2（それ以外で 判定不能 がある）・64（使い方の誤り）
- 「信頼していない」は、OpenSSL の検証コード 2・19・20・21・23・27・28、Node.js の `UNABLE_TO_GET_ISSUER_CERT`・`SELF_SIGNED_CERT_IN_CHAIN`・`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`・`UNABLE_TO_VERIFY_LEAF_SIGNATURE`・`CERT_REVOKED`・`CERT_UNTRUSTED`・`CERT_REJECTED`、uv の `invalid peer certificate:` に続く `UnknownIssuer`・`Revoked`・`Other(OtherError(CertDistrusted))` だけ
- 成立の証拠は拒否の証拠より優先する。どちらも無ければ判定不能
- 既定のホストは `dv-g3b-emudhra`・`dv-g3b-aaa-emudhra`・`dv-g3b-noct-emudhra`・`dv-g3b-aaa-noct-emudhra` の `.we-have-a-problem.com`、ポート 443
- クライアント側のタイムアウト 15 秒、外側の `timeout` 30 秒。uv は `UV_HTTP_RETRIES=0`
- 外部ホストへの接続を postCreate・`run-tests.bash`・テストに入れない。`verify-ca-trust.bash` は `test-*.bash` の名前にしない
- Python は `uv run --no-project python`（`.devcontainer/` の例外の `python3` を使わない）
- コミットしないファイルは `PARENT_ROOT/tmp/agents/issue-291.a29a7sdq/` に置く

## Review Focus

1. 確認用ホストの証明書が期限切れ・名前の不一致になったとき、「信頼していない」と報告しない → Task 1 の期限切れの状態のテスト
2. 接続できない・タイムアウト・コマンドが無いときに 0 で終わらない → Task 1 の閉じたポートのテスト（タイムアウトとコマンドの欠如は同じ「証拠が無ければ判定不能」の規則で、代表の 1 件とする）
3. 利用者の環境が信頼させた CA を各クライアントへ渡したとき（`SSL_CERT_FILE` など）、実際の出力の形で「信頼している」になる → Task 1 の信頼させた状態のテスト
4. 外から渡された CA の環境変数（`SSL_CERT_FILE` など）がテストの結果を変えない → Task 1 のテストはそれらを外して実行する
5. `apt-get` が失敗したときに postCreate の step が成功扱いにならない → Task 2 のテスト

---

## 受け入れ基準

- **動作環境:** Ubuntu 26.04 の開発コンテナ（bash 5、OpenSSL 3.5.5、curl 8.18、git 2.55、uv 経由の Python 3.14、Node.js 24.22.1、uv 0.13.6）。実ホストの確認はネットワークが要る。テストは `127.0.0.1` の `openssl s_server` だけを使い、外部へ接続しない
- **実入力:** 引数なし（既定の 4 ホスト）、`localhost:1`（閉じたポート）、`localhost:<s_server のポート>`、`HOST`（ポート省略）。クライアントの出力は複数行で、curl は 6 行のエラー（`curl: (60) SSL certificate OpenSSL verify result: unable to get local issuer certificate (20)` を含む）、uv は `cause:` が続く複数行（`-vv` では TRACE が数十行）、git は `GIT_TRACE_CURL` の `<= Recv header: HTTP/1.0 200 ok`。結果の行と要約は日本語
- **防御範囲:** 対象は、TLS の成立（HTTP 応答）を「信頼している」・非 0 にすること、接続の拒否・名前解決の失敗・タイムアウト・コマンドが無い・期限切れや名前の不一致・想定外の出力を「判定不能」・非 0 にすること、発行者を信頼しない検証エラーだけを「信頼していない」にすること、`apt-get` の失敗で postCreate を止めること。対象外は、プロキシの CONNECT の応答による誤った「信頼している」（非 0 の側に倒れる）、ホスト側と Codex CLI・Blender など確認スクリプトの外のツール（点検は Issue に記録）、uv の設定ファイルの TLS の指定（`--no-config`）
- **Spec の条件との対応:**

  | Spec の条件 | 担当 Task | 観測する結果 | 検証 |
  | --- | --- | --- | --- |
  | 1 現行コンテナで 0・24 行が信頼していない | Task 4 | 実ホストへの実行の出力と終了コード | Task 4 Step 1 |
  | 2 到達できないと判定不能・非 0 | Task 1 | `localhost:1` で 6 行が判定不能 | `test-verify-ca-trust.bash` |
  | 3 信頼させると信頼している・非 0 | Task 1 | 6 行が信頼している | 同上 |
  | 4 期限切れを信頼していないにしない | Task 1 | 6 行が判定不能・非 0 | 同上 |
  | 5 postCreate の更新と失敗での停止 | Task 2 | 関数の終了コードと `apt-get` の引数 | `test-install-beforehand.bash`、このコンテナでの関数の実行 |
  | 6・7 README の案内 | Task 3 | 節と参照の実在 | Task 3 Step 2 |
  | 8 点検の Issue への記録 | Task 4 | Issue のコメントの URL | Task 4 Step 3 |

- **共有する条件:** 判定の規則と表示（Global Constraints）を Task 1 が実装し、Task 3 の README と Task 4 の実行結果が同じ語と終了コードを使う。統合担当は Task 4（このセッション）で、README の記述と実際の出力を突き合わせる

## 実行方式

`superpowers:executing-plans`（このセッションが実装する）。`implement_task.py check` の `self` が true。実装の根拠になる各クライアントの実際の出力の観測をこのセッションが持ち、README（Task 3）が確認スクリプト（Task 1）の出力に依存し、Task が少なく逐次に進むため。最後のブランチ全体のレビューは、新しいサブエージェント 1 つに依頼する。

## 実行予算

- 能動時間の予算: 300 分（Issue 全体。`--merge` のループの段階を含む）。根拠: 実装の Task が 4 つ、ループは 1〜3 サイクル（1 サイクルはレビューの期限 45 分と計画・修正 20 分ほど）
- phase の目安: 準備・Spec・Plan 45 分、実装（Task 1〜3）90 分、統合の検証・点検の記録・PR 30 分、ループ 135 分
- worker: 最後の全体レビューのサブエージェント 1 つ。絶対期限 30 分、無進捗の打ち切り 15 分、予約枠なし。ループの中の担当の期限は pr-review-fix-loop と agent-runner の設定に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（信頼性の失敗）。安全の失敗は再試行しない
- checkpoint: phase の境界、予算の 50%（150 分）と 100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: uv の `-vv` の応答の記録が不安定なら、uv の成立の証拠を「終了コード 1 と `No solution found`」に変える（方法変更）。テストが遅い・不安定なら、期限切れの状態を残して信頼させた状態と閉じたポートを 1 回の実行にまとめる（縮小）。README のホスト側の案内の詳細は持ち越し候補にできる（切り出し）
- ledger: `/workspaces/reso-world/tmp/agents/issue-291.a29a7sdq/budget.jsonl`、作業領域: 同じディレクトリの `sdd/2026-10-28-create-reso-world-issue-291-ca-trust-check/`

## contingency（代替策）

- 最初の RED で、あるクライアントの実際の出力が Spec の初期観測と違う（例: Python が別の検証コード、uv が別の文言）: 判定の意味（発行者を信頼しない理由だけを拒否とする）を保つ最小の変更を ledger に残して続ける。期限切れ・名前の不一致を拒否に含める変更は意味が変わるので行わない
- `openssl s_server -accept 127.0.0.1:0` が待ち受けのポートを表示しない: 空いているポートを `uv run --no-project python` の `socket` で選んでから起動する
- 信頼させた状態で、あるクライアントが渡した CA を読まない: そのクライアントの CA の指定方法（設定ファイルを一時 `HOME` に置くなど）に変える。読ませられなければ、そのクライアントだけ信頼させた状態の確認から外し、Spec の決定記録に縮小として書く
- 実ホストの確認（Task 4）が判定不能を含む（ネットワーク障害）: 1 回だけやり直す。続くときは止めずに結果をそのまま PR と Issue に書き、受け入れ条件 1 を未確認として残す。信頼している が出たら止まって報告する（安全の失敗）

---

### Task 1: 確認スクリプトとそのテスト

テストの要否: 要る（S）。接続の失敗や期限切れを「信頼していない」として 0 で終わると、守りが無いのに守られていると誤って報告する（気付けない損害）。拒否の正例（信頼させない状態で 0）を 1 件残す。

**Files:**
- Create: `.devcontainer/verify-ca-trust.bash`（実行権限を付ける）
- Create: `.devcontainer/test-verify-ca-trust.bash`

**Interfaces:**
- Produces: `bash .devcontainer/verify-ca-trust.bash [HOST[:PORT] ...]`。結果の行は `<表示名を 7 桁で左詰め>  <HOST:PORT>  <判定>  <根拠>`（表示名は `openssl`・`curl`・`git`・`python`・`node`・`uv` の順）。最後の行は `結果:` で始まる要約。終了コードは Global Constraints のとおり

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-verify-ca-trust.bash`（`set -euo pipefail` の直後に `GIT_*` を外す 1 行。一時ディレクトリに keyUsage 付きのテスト用 CA、`localhost` の SAN の証明書、`-not_before 20200101000000Z -not_after 20200102000000Z` の期限切れの証明書を作り、`openssl s_server -accept 127.0.0.1:0 -www` を起動して `ACCEPT` の行からポートを読む。実行は一時 `HOME` と、`SSL_CERT_FILE`・`SSL_CERT_DIR`・`CURL_CA_BUNDLE`・`GIT_SSL_CAINFO`・`NODE_EXTRA_CA_CERTS`・`NODE_OPTIONS`・`UV_NATIVE_TLS` を外した `env` で行う。終了時にサーバを止めて一時ディレクトリを消す）。確かめること:

```bash
# 信頼させない（正例）: 終了コード 0、6 行すべて「信頼していない」
run "$valid_port"            ; expect_rc 0 ; expect_count 信頼していない 6
# 信頼させた: 非 0、6 行すべて「信頼している」、「信頼していない」は 0 行
run_trusted "$valid_port"    ; expect_nonzero ; expect_count 信頼している 6 ; expect_count 信頼していない 0
# 信頼させた CA の期限切れの証明書: 非 0、「信頼していない」は 0 行、6 行すべて「判定不能」
run_trusted "$expired_port"  ; expect_nonzero ; expect_count 信頼していない 0 ; expect_count 判定不能 6
# 閉じたポート: 非 0、6 行すべて「判定不能」
run localhost:1              ; expect_nonzero ; expect_count 判定不能 6
```

`run_trusted` は `SSL_CERT_FILE`・`CURL_CA_BUNDLE`・`GIT_SSL_CAINFO`・`NODE_EXTRA_CA_CERTS` にテスト用 CA を渡す。`expect_count` は `^[a-z]+ +localhost:<port> +<判定>( |$)` の行を数える。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-verify-ca-trust.bash`
Expected: FAIL（スクリプトが無い）

- [ ] **Step 3: `.devcontainer/verify-ca-trust.bash` を実装する**

Spec の設計 1 のとおり。クライアントごとに `probe_<表示名> HOST PORT` が出力と終了コードを取り、`classify` が判定と根拠を決める。Python と Node.js の接続のコードは引数で HOST と PORT を受け取り（文字列に埋め込まない）、1 行目に `http <状態>`・`verify <コード> <文言>`・`error <名前> <文言>` を出す。判定不能の根拠は、コマンドが無いとき・タイムアウト（終了コード 124）のときはその旨、それ以外は出力の最後の空でない行（200 文字まで）。HOST は `^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$`、PORT は 1〜65535。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-verify-ca-trust.bash`
Expected: `PASS .devcontainer/test-verify-ca-trust.bash`

- [ ] **Step 5: commit**

```bash
git add .devcontainer/verify-ca-trust.bash .devcontainer/test-verify-ca-trust.bash
git commit -m "feat(devcontainer): 侵害された中間CA を信頼していないかを確かめる verify-ca-trust.bash (#291)"
```

### Task 2: postCreate で `ca-certificates` を上げる

テストの要否: 要る（S）。`apt-get` の失敗を成功扱いすると、古いトラストストアのまま postCreate が成功する（気付けない損害）。正例（成功して `apt-get` に `install` と `ca-certificates` が渡る）を 1 件残す。

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（`STEP_TOTAL`、`apt update` の step の直後に新しい step と関数）
- Modify: `.devcontainer/test-install-beforehand.bash`（末尾の PASS の前に追記）

**Interfaces:**
- Produces: 関数 `upgrade_ca_certificates()`（`sudo apt-get install -y ca-certificates`。失敗はそのまま返す）。step の表示は `Upgrading ca-certificates to the latest release`、失敗の表示は `fail "Upgrading ca-certificates failed."`

- [ ] **Step 1: 失敗するテストを追記する**

既存の `place_agent_runner_config` と同じく `sed -n '/^upgrade_ca_certificates() {$/,/^}$/p'` で関数を取り出し、偽の `sudo`（`exec "$@"`）と、引数を記録して `FAKE_APT_EXIT` で終わる偽の `apt-get` を PATH の先頭に置いて実行する。

```bash
FAKE_APT_EXIT=100 upgrade → 非 0 で終わる（fail: 'apt-get の失敗を成功として返した'）
FAKE_APT_EXIT=0   upgrade → 0 で終わり、記録した引数に install と ca-certificates がある
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-beforehand.bash`
Expected: FAIL（`no upgrade_ca_certificates in install_beforehand.bash`）

- [ ] **Step 3: 関数と step を足し、`STEP_TOTAL` を 31 にする**

- [ ] **Step 4: テストが通り、このコンテナで関数が動くことを確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-install-beforehand.bash`
Expected: PASS。続けて、関数を取り出して実行し（`sudo apt-get install -y ca-certificates`）、終了コード 0 と `ca-certificates is already the newest version` 相当の表示を確かめる。`grep -c '^step "'` が 31 であること

- [ ] **Step 5: commit**

```bash
git add .devcontainer/install_beforehand.bash .devcontainer/test-install-beforehand.bash
git commit -m "feat(devcontainer): postCreate で ca-certificates を最新へ上げる (#291)"
```

### Task 3: 文書

テストの要否: 要らない（F）。文書の文言を写すテストは書かない。代わりに、節と参照先の実在、README のコマンドの実行結果との突き合わせ、`bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash` で確かめる。

**Files:**
- Modify: `.devcontainer/README.md`（「既存環境の更新」と、その後に新しい節「トラストストアの確認（eMudhra 中間CA の侵害）」）
- Modify: `README.md`（「Dev Container を起動する」の 3）

**Interfaces:**
- Consumes: Task 1 のコマンド・判定・終了コード、Task 2 の step

- [ ] **Step 1: 文書を書く**

新しい節: 背景（Issue #291 と確認サイト `https://emudhra.we-have-a-problem.com/`）、確認のコマンドと、外部へ接続するので postCreate・`run-tests.bash` に入れていないこと、3 つの判定と終了コードの読み方の表、クライアントごとのトラストストアと「信頼している」になったときの更新方法の表、確認スクリプトの外のツール（Codex CLI・cursor-agent・devin・agy・gitleaks・Blender・GitHub CLI・Claude Code）の扱いと点検の記録（Issue #291）、ホスト側の更新（Windows 11、ブラウザ、WSL2 の Gentoo の `app-misc/ca-certificates` 20260816.3.125 以上、Docker Desktop 4.96.2 以上、Git for Windows 2.56.0.3 以上、VS Code 1.143.1 以上、Electron 44.9.1・43.8.1・42.11.16 以上で作られた Slack・Discord などのアプリ。コンテナの外は自動で確認できないこと）。「既存環境の更新」の postCreate の一覧、rebuild の後の確認、rebuild しない場合（`sudo apt-get update && sudo apt-get install -y ca-certificates`）に足す。ルートの README の 3 に確認のコマンドとホスト側の案内への参照を足す

- [ ] **Step 2: 確かめる**

Run: `bash .devcontainer/run-tests.bash .devcontainer/test-readme.bash` と、README に書いたコマンド・節の名前・ファイルの実在の確認（`grep`）
Expected: PASS、参照先がすべて実在する

- [ ] **Step 3: commit**

```bash
git add .devcontainer/README.md README.md
git commit -m "docs: トラストストアの確認とホスト側の更新の案内 (#291)"
```

### Task 4: 統合の検証と点検の記録（統合担当）

テストの要否: 要らない（実ホストへの接続はテストに入れない）。実行して結果を記録する。

- [ ] **Step 1: 実ホストで確かめる**

Run: `bash .devcontainer/verify-ca-trust.bash`（ログを `PARENT_ROOT/tmp/agents/issue-291.a29a7sdq/` に保存）
Expected: 終了コード 0、24 行が「信頼していない」

- [ ] **Step 2: 全体の検証**

Run: worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: すべて終了コード 0

- [ ] **Step 3: 点検の結果を Issue #291 にコメントする**

Spec の「初期観測」の点検の表と、Step 1 の結果を書く

- [ ] **Step 4: 条件ごとの照合と全体レビュー**

受け入れ基準の表の条件ごとに、Task の成果と観測を突き合わせる。README の判定・終了コード・コマンドが Task 1 の実際の出力と一致すること。新しいサブエージェント 1 つにブランチ全体のレビューを依頼する
