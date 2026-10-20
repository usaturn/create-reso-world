# Issue #209: DeepSeek Harness を 0.2.1-rc.2 に更新する

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/209（親 Issue・ボード・先行 Issue は無い。コメントは無い）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue209-dsh-0-2-1-rc-2.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-209-dsh-0-2-1-rc-2`（branch `feat/issue-209-dsh-0-2-1-rc-2`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #209 --merge` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #209`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）で修正不要と確かめられたら、ループの `finalize.py` がマージと関連 Issue の更新を行う
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- ループのオプション: `loop.py check-options` は `max_cycles = 3`・`assign = {}`・`template = .devcontainer/agent-runner.toml`・`config = null`（どれも既定の適用。利用者が書いたループ用のオプションは無い）。割り当ては review/inspect が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、fix/implement が `claude-opus`、self-review・fix-check が `self`
- 基準: `origin/main` の `f2350a4`。この時点の `uv run pytest tools/agent_runner/tests/adapters/dsh -q` は 283 件成功（Issue の記載時の `6becc65` の 277 件から増えている）

## 意図

agent-runner の headless レビュアー（`dsh-ccd`・`dsh-go`）が使う DeepSeek Harness の固定を `0.2.0-rc.2` から `0.2.1-rc.2` に上げる。版の置き換えだけでなく、`tools/agent_runner/adapters/dsh.py` が頼る profile・patch・sandbox・承認の文面・JSON イベント・session ログの形が新しい版でも成り立つことを確かめ、成り立たないところだけを直す。

## 確認した事実（2026-10-20）

### 公開状況

- npm の dist-tag は `latest`・`next` とも `0.2.1-rc.2`（2026-10-17T08:36Z）。`alpha` の `0.2.1-alpha.5` は 2026-10-16 で `rc.1` より前。`0.2.1` 系に `rc.2` より新しい候補版は無く、Issue の前提は変わらない

### 導入

- 一時の HOME・npm cache・npm prefix で、`npm install -g --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty @deepseek-ai/dsh@0.2.1-rc.2` が成功し、`dsh --version` は `0.2.1-rc.2`。同じ手順の `0.2.0-rc.2` も成功する
- allowlist の 3 つは新版にもあり、`@deepseek-ai/dsh-subprocess-local` は `0.2.1-rc.2`、`koffi` 3.1.1・`node-pty` 1.2.0-beta.15 は旧版と同じ。`koffi.node`・`pty.node` も配置される
- allowScripts の対象外の警告（`@google/genai`・`protobufjs`）は新旧で同じで、新しく増えたものは無い
- 既存の導入の上書き: `0.2.0-rc.2` の prefix の写しに `0.2.1-rc.2` を入れる（rebuild しない更新）と、`0.2.1-rc.2` の写しに `0.2.0-rc.2` を入れる（戻す）は、どちらも成功し、`dsh --version` が入れた版になる

### アダプターが頼るもの（ソースの比較）

- 承認・拒否の文面: `dsh-tools` の `serviceAsk` の 5 種と `dsh-sandbox` の `approveEscalation` の 5 種は新旧で同じ文字列。ツールの失敗の `Error: ${...}` の包みと、PTC の `code run failed (${kind}): ...` も同じ
- JSON 投影: `dsh-headless` の `json-stream-*.js` は新旧で同じファイル。`dsh-headless` の変更は、子の subagent の終了を待つことと、Agent の失敗が後の `turn/end` で回復しなければ `{"type":"error","message":...}` を出して終了コード 1 で終わること。アダプターの `_classify()` は `error` イベントを `_diagnostic()` に回すので、扱いは変わらない
- headless profile: `dsh --profile headless --patch <アダプターと同じ形の patch> --dump-config` は新旧とも終了コード 0 で、patch の 9 個の plugin ID（`sandbox`・`llm-pi-ai`・`agent-default-model`・`approval`・`permission`・`sandbox-policy`・`session-persistence-jsonl`・`session-title-llm`・`plugin-package-inventory-deepseek`）はすべて構成に現れ、設定が重なる
- 新版の headless で増えた・変わったもの
  - `credentials`・`authorization`・`deepseek-account` を headless 自身が無効にする（保存済みの key を読まない変更）。アダプターは呼び出しごとの環境変数名で key を渡すので、影響は無い
  - `web-deepseek-api`（DeepSeek Search・Fetch API の provider）が登録されるが、`web` の `searchProvider: deepseek-official`・`fetchProvider: http` は旧版と同じで、選ばれない。`web`・`web-search-deepseek`・`tool-web` は旧版の headless でも有効
  - `remote-access`（API Gateway の権限判定。モデルに見えない）
  - `working-directory`・`tool-working-directory`（session の作業ディレクトリを変えるツール `working_directory`）。README によれば header は元のプロジェクトを指したままで、書き込み権限も変えない。外側の bubblewrap と `sandbox-policy` の `workspaceRoot` は変わらない
  - system prompt の `personaSuffix`（`Your working directory is {{cwd}}.`）が消えた。`tool-ralph`・`skill-badge`（旧版でも無効）が消えた
- ツールの mode: `DSH_TOOLS_MODE` の既定は新旧とも `native`。新版は mode を `native`・`ptc` の 2 つにした。アダプターは `DSH_TOOLS_MODE` を設定しない
- pi-ai は `0.87.1` → `1.3.0`。`opencode-go` の `deepseek-v4.1-flash` は新版にもあり（`openai-completions`、`max` を持つ）、組み込みの接続先が `https://opencode.ai/zen/go/v1` から `https://opencode.ai/inference/go/v1` に変わった。`dsh-go` は patch に `baseURL` を書かず、この組み込みの定義を使う

### 実 CLI と偽 provider での通し（runner の実経路）

`run_workflow` に、実アダプターを包む `adapter_loader` を渡して実行した。worktree の作成・bubblewrap・停止確認・`collect()`・session ログの identity・redact・回収は runner の実経路のままで、違いは次だけ。

- `dsh-ccd` の形（`commandcode`・`deepseek/deepseek-v4.1-flash`・`max`）: patch の `llm-pi-ai` の `baseURL` を、ローカルの偽 OpenAI 互換サーバー（`/provider/v1/chat/completions`、SSE）に向けた
- `dsh-go` の形（`opencode-go`・`deepseek-v4.1-flash`・`max`）: 接続先は変えず、bubblewrap に `--unshare-net` を足してネットワークを切った（外部に何も送らない）
- key は偽の値。使い捨てのリポジトリに `.env`（`COMMANDCODE_API_KEY`・`OPENCODE_API_KEY`・`DEEPSEEK_API_KEY` の囮）を commit した

新旧の CLI で同じ 7 つのシナリオを実行し、状態・終了コード・JSON イベントの並び・ツール結果の 1 行目・session ログの形・観測した identity はすべて一致した。

| シナリオ | 偽 provider の応答 | 結果（新旧とも） |
| --- | --- | --- |
| success | JSON の本文 | `success`、payload あり、identity `commandcode / deepseek/deepseek-v4.1-flash / max` |
| tool-error-recovered | `read` で存在しないファイル → JSON | ツール結果 `Error: cannot read ...: not found` の後 `success` |
| escalation-denied | `bash` に `sandbox_permissions: danger-full-access` → JSON | ツール結果 `Error: the user rejected escalating this command to "danger-full-access"; ...` で `awaiting_approval` |
| ptc-escalation-denied | `DSH_TOOLS_MODE=ptc`、`run_code` から同じ `bash` → JSON | `Error: code run failed (exception): ToolCallError: the user rejected escalating ...` で `awaiting_approval` |
| ptc-caught-read | `run_code` の中で `read` の失敗を捕まえる → JSON | ツール結果 `completed` で `success` |
| auth-401 | HTTP 401（`invalid_api_key`） | 終了コード 1、`response_failed`（下の「範囲外で見つけた既存の挙動」） |
| go-offline | （ネットワーク無し） | `request/header` に `opencode-go / deepseek-v4.1-flash / max` が記録され、`TRANSPORT: Connection error.` で `response_failed` |

- 偽 provider が受けた要求の `Authorization` はすべて呼び出しごとの偽 key で、`.env` の囮は使われていない。要求は応答ごとに 1 回で、session のタイトル生成などの追加の LLM 呼び出しは無い。要求には `reasoning_effort: max` と `thinking` が付く
- session ログは `sessions/*/<id>/session.v4.jsonl` の 1 つで、header は `type: session`・`version: 4`・`isSeeded: false`、`cwd` は runner の worktree。`request/header` の `data.header.config` と `assistant/message` の `data.message.source`（`kind: model`）の形も同じ
- すべての試行で `stop_confirmed` は true、`outside_changes` は空

### 範囲外で見つけた既存の挙動

- 最初の要求が 401 のとき、`_classify()` は `awaiting_authentication` を返すが、モデルの応答が無い session では `read_session_identity()` が `ValueError`（`DSH session has no observed assistant route`）を出し、`collect()` が `response_failed` に上書きする。新旧で同じで、成功と取り違えることは無い。偽 CLI のテスト（`test_runner.py` の `auth`）は session ログを作らないので、この経路を通らない

## 設計

### 1. 固定を上げる

`.devcontainer/install_beforehand.bash` の `install_deepseek_harness` の `version` を `0.2.1-rc.2` にする。allowlist・`npm install -g --allow-scripts=...`・`dsh --version` の照合はそのまま保つ。

### 2. `.devcontainer/README.md` を新しい版に合わせる

- ツール表の DSH の行の版
- headless の前提: 新しい版の headless は保存済みの key を読まず、key は呼び出しごとの環境変数で渡すこと（アダプターの変数名は呼び出しごとに作るので、作業対象の `.env` が key を与えることは無い）を足す
- rebuild 後の確認の版
- rebuild せずに上げる手順と、旧い固定（`0.2.0-rc.2`）へ戻す手順（`npm install -g --allow-scripts=... @deepseek-ai/dsh@<版>` と `dsh --version`）。DSH の状態は呼び出しごとの `DSH_HOME` にあり、共有の状態の移行は要らないこと

### 3. 版の由来のコメントを直す

アダプターの `_TOOL_APPROVAL_REASON` のコメントと、`test_adapter.py` の文面・fixture の由来のコメントに、`0.2.1-rc.2` で同じ文面・同じ包みを確かめたことを書く。正規表現・fixture の内容・判定は変えない。

### 4. 移植の記録の文書

`docs/maatlog-poc-porting.md` の比較表の DSH の行（#151）に、#209 で `0.2.1-rc.2` に上げたことと現在の版の参照先を追記する。R-3（rebuild の確認の表）は 2026-10-05 の記録として書き換えない。

### 5. 検証

- `README.md` の「テスト」の入口（ワールドの行を除く）。`uv run pytest tools/agent_runner/tests/adapters/dsh -q`（基準の 283 件）を含む
- 上の「実 CLI と偽 provider での通し」を、変更の後の commit で新版に対してもう一度実行し、同じ結果になること
- 実 API の確認は、この PR では行わない（D-209-6）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-209-1 上げる版は `0.2.1-rc.2`**
  - 選択: `0.2.1-rc.2`
  - 別案: `0.2.1-alpha.5`、正式版を待つ
  - 理由: 着手時の確認で `latest`・`next` とも `0.2.1-rc.2` で、より新しい候補版は無い。`alpha.5` は `rc.1` より前
- **D-209-2 アダプターの patch・正規表現・識別の解析は変えない**
  - 選択: コードの挙動は変えず、版の由来のコメントだけを直す
  - 別案: (a) 文面の変化に備えて正規表現を広げる、(b) 新版で増えた plugin を patch で無効にする
  - 理由: 文面・JSON 投影・失敗の包み・plugin ID・session ログの形は新旧で同じで、実 CLI の通しも新旧で一致した。(a) は通常の失敗を拒否と取り違える側の危険を増やす。違いが無いので回帰テストも足さない（Issue の「見つけた違いを直す場合は、実行できる回帰テストを足す」の条件に当たらない）
- **D-209-3 新版で増えた plugin（`web-deepseek-api`・`remote-access`・`working-directory`・`tool-working-directory`）は patch で無効にしない**
  - 選択: shipped の headless profile の既定のままにする
  - 別案: patch で `disabled: true` にする
  - 理由: `web-deepseek-api` は登録だけで選ばれず、Issue の対象外は新機能を有効にすることなので既定は変えなくてよい。`remote-access` はモデルに見えない。`working_directory` は書き込み権限を変えず、外側の bubblewrap と `workspaceRoot` で守る範囲は変わらない。無効にする ID を増やすと、旧版へ戻したときや次の版の更新で、存在しない ID の扱いを確かめる手間が増える
- **D-209-4 `ptc_tool_results.json` は作り直さず、由来のコメントを直す**
  - 選択: 内容はそのままにし、`0.2.0-rc.2` で作ったことと、`0.2.1-rc.2` の実 CLI で、アダプターが読む 1 行目が同じことを確かめたことを書く
  - 別案: (a) 新版の出力で作り直す、(b) 版に依存しない形にする
  - 理由: アダプターが読むのは 1 行目（拒否の理由）だけで、新版の実 CLI の出力の 1 行目は fixture と同じ。作り直しても変わるのはスタックのパスだけで、元の probe はリポジトリに無い。(b) は fixture の価値（実際の生成元の出力であること）を失う
- **D-209-5 `dsh-go` は、ネットワークを切った起動と経路の解決までを確かめる**
  - 選択: 接続先を差し替えず、`--unshare-net` で起動し、`request/header` に定義の provider・model・effort が記録され、接続の失敗で止まることを確かめる
  - 別案: (a) `dsh-go` も `baseURL` を偽 provider に向ける、(b) 実 API に偽 key で送る
  - 理由: (a) は `dsh-go` が頼る組み込みの定義の解決を通らない。(b) は外部へ送る。組み込みの接続先の変更（`zen` → `inference`）は上流の定義で、実 API で確かめるのは許可の範囲外
- **D-209-6 実 API の確認（#175 の許可済みの 1 回）は、この PR では使わない**
  - 選択: 利用者の rebuild 後に、#175 の受け入れとして `0.2.1-rc.2` で行う。この PR は「設定の検証」と「偽 key・偽 API での通し」を記録し、#175 に対象の版が変わったことを書く
  - 別案: 一時の prefix の新版で、いま 1 回を使う
  - 理由: #175 の実施条件は「rebuild は利用者が行う」と「rebuild 後の `dsh --version` の一致」で、この run では満たせない。いま使うと、rebuild 後の受け入れの回数が残らない。Issue の反映先も「この PR か、同じ版で行った記録」を認めている
  - 停止条件: 実 API を呼ぶ必要が出たら、回数を増やさずに止まる
- **D-209-7 `docs/maatlog-poc-porting.md` は、比較表の DSH の行に追記し、R-3 は書き換えない**
  - 選択: 比較表の行に「#209 で `0.2.1-rc.2` に上げた。現在の版は `.devcontainer/README.md`」を足し、担当 Issue に #209 を足す
  - 別案: (a) どちらも書き換えない、(b) R-3 の期待値も書き換える
  - 理由: 文書の冒頭が「現在の手順は README にある」と定め、Context7 の行も後の変更を追記する形を取っている。R-3 は 2026-10-05 の rebuild の確認の記録で、期待値を変えると記録と合わなくなる
- **D-209-8 README に、rebuild せずに上げる手順と戻す手順を書く**
  - 選択: 同じ `npm install -g --allow-scripts=...` で版を指定して上書きし、`dsh --version` で確かめる手順を、上げる・戻すの両方で書く
  - 別案: rebuild だけを手順にする
  - 理由: Issue の受け入れ基準が戻す手順の確認を求めている。上書きの上げ下げは一時の prefix で両方向とも確かめた。DSH の状態は呼び出しごとの `DSH_HOME` にあり、移行する共有の状態が無い
- **D-209-9 401 が `response_failed` になる既存の挙動は直さない**
  - 選択: 範囲外とし、Spec と PR 本文に記録する
  - 別案: `collect()` で、識別の失敗が `awaiting_authentication`・`awaiting_approval` を上書きしないようにする
  - 理由: 版によらない既存の挙動で、成功と取り違えることは無い。識別の失敗の扱いは「識別ログの欠落・不一致は成功にしない」という仕様の範囲で、変えるなら別の Issue で判断する
- **D-209-10 確認用のスクリプトは commit しない**
  - 選択: `PARENT_ROOT/tmp/agents/` のセッションディレクトリに置き、結果を Plan・PR に記録する
  - 別案: `tools/` に置いて次の版の更新でも使う
  - 理由: `AGENTS.md` はテストを偽の adapter・偽の CLI に限る。実 CLI の導入を前提にするスクリプトは通常のテストで動かせない。手順はこの Spec の「実 CLI と偽 provider での通し」に残る
- **D-209-11 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は版の 1 か所と文書・コメントで、調査の結果（比較と通し）を子に渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. `.devcontainer/install_beforehand.bash` の固定が `0.2.1-rc.2` で、allowlist・`--allow-scripts`・`dsh --version` の照合を保つ。一時の HOME・npm prefix での新規導入で `dsh --version` が `0.2.1-rc.2` を返す（利用者の実 key・共有 `~/.dsh` を使わない）
2. 実 CLI（`0.2.1-rc.2`）と偽 provider・偽 key で、headless の入力 → JSON イベント → 保存した session → 観測した identity の経路が通り、承認の拒否（直接・PTC）は `awaiting_approval`、通常のツールの失敗は拒否と取り違えずに `success` になる。新旧の CLI で結果が同じ
3. `dsh-ccd`・`dsh-go` の agent 定義（provider・model・effort・env）のまま新版が起動し、定義の provider・model・effort が session に記録される。既定のモデルは変えない
4. `uv run pytest tools/agent_runner/tests/adapters/dsh -q` が全件成功し、`uv run pytest tools/agent_runner`・`bash .devcontainer/run-tests.bash`・`README.md` の「テスト」の入口が成功する。skip で代えない
5. README に、新しい版での rebuild 後の確認・rebuild せずに上げる手順・旧い固定へ戻す手順がある。戻す手順は一時の prefix で確かめてある
6. 共有 `~/.dsh` を作らず、mount せず、plugin を入れない。呼び出しごとの `HOME`・`DSH_HOME`・`TMPDIR` の分離を保つ
7. #175 に、受け入れの対象の版が `0.2.1-rc.2` になったことと、この PR の記録（実 API は未実施）を書く

## 範囲外

- 実 API の確認（D-209-6。#175 で行う）と、#151・#175 の受け入れの完了
- 新しい機能（DeepSeek Search・Fetch、Git Worktrees など）を有効にすることと、既定のモデルの変更
- pi-tui・対話用ランチャー・provider プラグインの導入
- #198（`/tmp` のテストの前提）・#187（checkout の監査）・#183（native write の許可範囲）の修正
- 401 の分類（D-209-9）
- 今のコンテナに導入済みの `dsh`（`0.2.0-rc.2`）の更新。rebuild か README の手順で利用者が行う

## 実装者に任せること

- README・コメントの文面
- 確認用スクリプトの細部
