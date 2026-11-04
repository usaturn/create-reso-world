# Issue #309 Herdr の復元で Pi のペインをランチャーから再開する 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の実行許可。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/309

**Goal:** ランチャーから起動した Pi のペインを、Herdr が復元するときに `<ランチャー> --session <今のセッションファイル>` で再開させる。

**Architecture:** 共通ヘルパが bwrap に `--setenv PI_SUPERAGENTS_LAUNCHER <ランチャー>` を渡す。setup が `~/.pi/agent/extensions/herdr-launcher-resume.ts` に置く Pi の拡張が、TUI の Pi の `session_start` のたびに、`source: "herdr:pi"` で `pane.report_agent_session` に `resume_argv` を付けて Herdr のソケットへ報告する。

**Tech Stack:** TypeScript（型注釈の無い、Node 24 の型除去と Pi の読み込みの両方で動く形）、zsh（ヘルパ・setup）、bash（テスト）、Herdr 0.9.5、Pi 1.5.0、bubblewrap 0.11

**Spec:** `docs/superpowers/specs/2026-11-05-issue-309-herdr-pi-launcher-resume-design.md`

## Global Constraints

- 報告: method `pane.report_agent_session`、`source: "herdr:pi"`、`agent: "pi"`、`pane_id: $HERDR_PANE_ID`、`seq`、`session_start_source: <event.reason>`、`agent_session_path: <セッションファイル>`、`resume_argv: [<ランチャー>, "--session", <パスか ID>]`。改行で終わる 1 行の JSON を `$HERDR_SOCKET_PATH` の UNIX ソケットへ送る（Herdr の連携と同じ形）
- `seq` = `max(前の seq + 1, Date.now() * 1000)`
- 動く条件: `HERDR_ENV=1`、`HERDR_SOCKET_PATH` と `HERDR_PANE_ID` がある、`PI_SUPERAGENTS_LAUNCHER` が `^[a-z][a-z0-9_-]*$`、`ctx.mode === "tui"`、セッションファイルが絶対パス
- `--session` に渡す値: パスにアポストロフィも制御文字（U+0000〜U+001F・U+007F）も無ければパス。あればセッション ID（`^[A-Za-z0-9-]+$` のとき）。どちらも使えなければ報告しない
- やり直し: 応答が `resume_not_accepted`、または送信の失敗・応答なし（1 回の待ちは 2000 ms）のとき、0・250・500・1000・2000・4000 ms の間隔で最大 6 回送る。新しい `session_start` が来たら、前のやり直しは次の送信の前に止める（`globalThis[Symbol.for("create-reso-world.herdr-launcher-resume")]` の世代番号）
- 拡張は例外を外に出さない（Pi ごと終了するため）
- 拡張のファイル: リポジトリ `.devcontainer/pi-herdr-launcher-resume.ts` → 配置先 `~/.pi/agent/extensions/herdr-launcher-resume.ts`
- Herdr の連携のファイル（`herdr-agent-state.ts`）・pi-superagents・Herdr 本体は変えない
- テストは一時の `HOME`・一時のソケットだけを使い、利用者の `~/.pi`・既定の Herdr のセッションを変えない

## Review Focus

- 起動直後の競合: Herdr の連携が状態を報告する前の報告は `resume_not_accepted` になる。やり直しで通る（実機の確認で見る。テストしない理由は Spec の D5）
- `/new` の直後に前のセッションのやり直しが遅れて届く: 世代番号で止まる（Task 1 のテスト）
- 子 Pi（`--mode json`）が親と同じ `HERDR_PANE_ID` と `PI_SUPERAGENTS_LAUNCHER` を継承する: TUI でないので報告しない（Task 1 のテスト）
- パスに空白を含むセッションファイル（cwd に空白）: argv の 1 要素として渡し、Herdr が引用して入力する（実機の確認で `echo` の結果を見る範囲。テストの入力にも空白を含むパスを使う）
- Herdr のソケットが無い・応答しない: 例外を出さず、Pi の起動を待たせない（`session_start` の処理は報告を待たない）

## 実行予算

- Issue 全体の能動時間: 300 分（18:10Z 開始。#307 の実績が PR まで約 45 分＋ループ 1 サイクル。今回は実機の調査が長い）
- phase の目安: 調査・Spec・Plan 60 分（済み）、Task 1 40 分、Task 2 30 分、検証・全体レビュー 30 分、PR 15 分、ループ 1〜3 サイクル（1 サイクル 45 分のレビュー＋計画・修正 15 分）
- worker: 実装は self なので runner の担当は無い。全体レビューのサブエージェントは同期で 20 分。ループの担当の期限は pr-review-fix-loop の設定のとおり
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回。安全の失敗は再試行しない
- checkpoint: 各 Task の完了、全体の検証の後、PR の作成の後、予算の 50%（20:40Z）と 100%（23:10Z）
- 縮小・切り出し・方法変更の候補: (1) ID への切り替え（パスが検証を通らないとき）が実機で動かなければ、報告しない形に縮小する (2) 実機の復元の確認が Herdr の操作で詰まったら、`session.json` の `agent_resume` の確認までにして PR に記録する (3) README を手順だけに絞る

## contingency

- Node 24 が拡張の `.ts` を import できない（型除去の制限）: 拡張から型注釈を除いた形を保つ。読めない構文が残っていると最初の RED で分かったら、その構文を JavaScript の形に直す（意味は変えない）
- テストの偽のソケットが Herdr と違う応答の形を要る: Herdr の応答は `{"id":…,"result":{"type":"ok"}}` か `{"id":…,"error":{"code":…,"message":…}}` の 1 行（実機で確かめた形）。違う形が要ると分かったら停止して Spec の事実を確かめ直す
- 実機の確認で、拡張の報告が Herdr の連携の状態の報告（working / idle）を止めると分かった: 実装を進めず、Spec の事実 4 が崩れたので停止して報告する
- 実機の確認で、復元が `resume_argv` を使わないと分かった: Spec の事実 8 が崩れたので停止して報告する

## 受け入れ基準

- 動作環境: この Dev Container（Ubuntu 26.04、zsh、Node.js 24.22、bubblewrap 0.11.1）、Herdr 0.9.5、Pi 1.5.0。実機の確認は名前付きのテスト用 Herdr セッションで行い、既定のセッションのペインに触れない
- 実入力:
  - セッションファイル: `/home/vscode/.pi/agent/sessions/--workspaces-reso-world--/2026-11-04T05-45-06-950Z_01a1a516-f284-7681-8ce3-8fc54af9ca5c.jsonl` の形。テストでは一時ディレクトリの、空白を含むパス（`…/sessions dir/2026-11-05T00-00-00-000Z_<UUID>.jsonl`）
  - `session_start` の `event.reason`: `startup`（起動）、`new`（`/new`）
  - `ctx.mode`: `tui`（対話）、`json`（pi-superagents の子）
  - ランチャー名: `pigs`（13 個のランチャーは `.devcontainer/pi-superagents/*.json` から導く）
- 防御範囲:
  - 対象: Herdr の中で、ランチャーから起動した TUI の Pi の、起動とセッションの切り替え
  - 対象外の反例: `ctx.mode` が `tui` でない Pi は報告しない。`PI_SUPERAGENTS_LAUNCHER` が無い Pi（素の `pi`）、Herdr の外、セッションファイルの無い Pi も報告しない（L。実行で確かめる）
  - 反例として通すもの: 空白を含むセッションファイルのパスは、そのままパスで報告する

## 要件と Task の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| D1・D3 報告の内容 | 1 | 偽のソケットが受けた 1 件目の JSON の各項目 | `test_reports_launcher_resume_and_follows_session_switch` |
| D3 セッションの切り替えで報告し直す・前のやり直しが後から届かない | 1 | 2 件目以降のパスと `seq`、新しいパスの後に前のパスが来ない | 同上 |
| D3 TUI でない Pi は報告しない | 1 | 偽のソケットが何も受けない | `test_non_tui_pi_does_not_report` |
| D2 ランチャー名を渡す | 2 | 各ランチャーの dry-run の argv の `--setenv PI_SUPERAGENTS_LAUNCHER <ランチャー>` | `test_launchers_wrap_pi_with_their_own_config` |
| D4 拡張の配置 | 2 | 一時 HOME の `~/.pi/agent/extensions/herdr-launcher-resume.ts` が拡張と同じ内容 | setup の実行と `cmp` |
| 事実 1〜8 との整合（実機） | 2 | テスト用セッションの `session.json` の `agent_resume`、`/new` の後の更新、復元でペインに入力されたコマンド | 実機の確認の記録 |
| D6 文書 | 2 | README の節 | 通読と `git diff` |

共有する条件: 環境変数の名前 `PI_SUPERAGENTS_LAUNCHER`（Task 1 の拡張、Task 2 のヘルパ・テスト・README）と、拡張のファイルの名前（Task 1 で作り、Task 2 の setup・README が使う）。統合の確認は Task 2 の最後の実機の確認で行う。

## 実行方式

executing-plans（self）。Task が 2 つで、Task 2 の実機の確認がこのセッションで調べた Herdr の観測（テスト用セッションの操作）に依存するため。最後にブランチ全体のレビューを新しいサブエージェントで行う。

### Task 1: Herdr に再開コマンドを報告する Pi の拡張

**Files:**
- Create: `.devcontainer/pi-herdr-launcher-resume.ts`
- Create: `.devcontainer/test-pi-herdr-launcher-resume.bash`

**Interfaces:**
- Produces: `export default function (pi)`。`pi.on("session_start", (event, ctx) => void)` を登録する。`event.reason: string`、`ctx.mode: string`、`ctx.sessionManager.getSessionFile(): string | undefined`、`ctx.sessionManager.getSessionId(): string | undefined` を使う。環境変数は工場関数の呼び出しのときに読む
- テストの要否: 書く（S）。Spec の D5 の 2 件。防ぐ損害をテストのコメントに書く

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-pi-herdr-launcher-resume.bash`: `mktemp -d` の一時ディレクトリに Node の ES モジュールのテストを書き出し、`node` で実行する。テストは偽の Herdr（`net.createServer` を一時ディレクトリの `herdr.sock` で listen。1 行の JSON を受けるたびに記録し、`agent_session_path` が「拒否するパス」なら `{"id":…,"error":{"code":"resume_not_accepted","message":"…"}}`、それ以外は `{"id":…,"result":{"type":"ok"}}` を返す）を立て、`process.env` に `HERDR_ENV=1`・`HERDR_SOCKET_PATH`・`HERDR_PANE_ID=w9:p9`・`PI_SUPERAGENTS_LAUNCHER=pigs` を入れてから拡張を import し、偽の `pi`（`on(name, fn)` で handler を保持）で工場関数を呼ぶ。

- `test_reports_launcher_resume_and_follows_session_switch`（防ぐ損害: Herdr は `resume_argv` の無い報告やパスの変更で `agent_resume` を消さないので、切り替えの後に報告し直さないか、前のセッションのやり直しが後から届くと、復元で前のセッションが黙って開く）:
  - 旧パス `<tmp>/sessions dir/2026-11-05T00-00-00-000Z_old.jsonl`（拒否するパス）で `session_start({reason: "startup"}, {mode: "tui", …})`、300 ms 後に新パス `<tmp>/sessions dir/2026-11-05T00-00-01-000Z_new.jsonl` で `session_start({reason: "new"}, …)`、そこから 9 秒待つ
  - 受けた要求のうち新パスの最初の 1 件: `method === "pane.report_agent_session"`、`params.source === "herdr:pi"`、`params.agent === "pi"`、`params.pane_id === "w9:p9"`、`params.session_start_source === "new"`、`params.agent_session_path === 新パス`、`params.resume_argv` が `["pigs", "--session", 新パス]` と等しい、`Number.isSafeInteger(params.seq)`
  - 旧パスの要求が少なくとも 1 件あり、その `session_start_source === "startup"`、`resume_argv[2] === 旧パス`
  - 新パスの最初の要求より後に、旧パスの要求が無い
  - 新パスの最初の要求の `seq` が、それより前のすべての要求の `seq` より大きい
- `test_non_tui_pi_does_not_report`（防ぐ損害: 子 Pi は親の `HERDR_PANE_ID` を継承するので、報告すると子のセッションが親のペインの再開先になり、復元で別のセッションが黙って開く）: 別のパスで `session_start({reason: "startup"}, {mode: "json", …})`、1 秒待って、そのパスの要求が 0 件

- [ ] **Step 2: テストを実行して失敗を確かめる**

Run: `bash .devcontainer/test-pi-herdr-launcher-resume.bash`
Expected: FAIL（拡張のファイルが無いので import に失敗する）

- [ ] **Step 3: `.devcontainer/pi-herdr-launcher-resume.ts` を実装する**

Global Constraints の値どおりに書く。冒頭のコメントに、目的（#309）、Herdr の連携の横に置く理由、`source: "herdr:pi"`・`seq`・`session_start_source`・世代番号が要る理由（Spec の事実 2〜6・10）を短く書く。送信は Herdr の連携と同じく `net.createConnection` で接続し、応答の 1 行を JSON として読んで `error.code` を見る。`session_start` の handler は送信を待たずに戻る。

- [ ] **Step 4: テストを実行して通ることを確かめる**

Run: `bash .devcontainer/test-pi-herdr-launcher-resume.bash`
Expected: `OK test-pi-herdr-launcher-resume`、終了コード 0

- [ ] **Step 5: テストの効きを確かめる（コミットしない一時の変異）**

拡張の世代番号の確認を外す、`ctx.mode` の確認を外す、の 2 つをそれぞれ一時的に入れてテストが FAIL になることを確かめ、元に戻す（`git diff` が空になることを確かめる）。あわせて、同じ偽のソケットを使う一時のスクリプト（scratchpad に置き、コミットしない）で、L として書かない次の 4 つを確かめて記録する: `PI_SUPERAGENTS_LAUNCHER` が無い・`PI/../x` のように素のコマンド名でないと報告しない、`getSessionFile()` が `undefined` だと報告しない、パスにアポストロフィを含むと `resume_argv` が `["pigs", "--session", <ID>]` になる、ソケットが無くても例外が出ない。

- [ ] **Step 6: commit**

```bash
git add .devcontainer/pi-herdr-launcher-resume.ts .devcontainer/test-pi-herdr-launcher-resume.bash
git commit -m "feat: report launcher resume command to Herdr from Pi"
```

### Task 2: ランチャー名の受け渡し・拡張の配置・文書・実機の確認

**Files:**
- Modify: `.devcontainer/pi-superagents-exec.zsh`（`pi_superagents_exec` の `args_` の `--bind` の前）
- Modify: `.devcontainer/test-pi-superagents.bash`（`test_launchers_wrap_pi_with_their_own_config`）
- Modify: `scripts/setup_pi_superagents.zsh`（ヘルパの `install` の隣、冒頭の配置先の一覧）
- Modify: `.devcontainer/README.md`（「ランチャーを通さない Pi と同梱の既定 model」）

**Interfaces:**
- Consumes: Task 1 の拡張のファイル `.devcontainer/pi-herdr-launcher-resume.ts` と環境変数 `PI_SUPERAGENTS_LAUNCHER`
- テストの要否: ランチャー名の受け渡しは書く（S。既存の全ランチャーのテストに足す）。配置・README は書かない（L・F。Spec の D5）。代わりに一時 HOME の setup の実行と実機の確認

- [ ] **Step 1: 失敗するテストを書く**

`test_launchers_wrap_pi_with_their_own_config` の各ランチャーの繰り返しで、argv の中から `--setenv` の次が `PI_SUPERAGENTS_LAUNCHER` の位置を探し、その次の要素が `${launcher}` と等しいことを確かめる（無ければ `"${launcher} must pass its name to Pi via --setenv PI_SUPERAGENTS_LAUNCHER"` で fail）。防ぐ損害のコメントに「別のランチャーの名前で再開されると、復元した Pi の tier の model が黙って変わる」を足す。

- [ ] **Step 2: テストを実行して失敗を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: FAIL（`must pass its name`）

- [ ] **Step 3: ヘルパと setup を変える**

- `pi_superagents_exec`: `args_` の `--bind` の前に `--setenv PI_SUPERAGENTS_LAUNCHER "${launcher}"` を足す。冒頭のコメントに、Herdr の復元のための名前であること（#309）を 1〜2 行で書く
- `setup_pi_superagents.zsh`: ヘルパの `install` の後に `install -m 0644 "${REPO_ROOT}/.devcontainer/pi-herdr-launcher-resume.ts" "${EXT_DIR}/herdr-launcher-resume.ts"` と表示 `extension: <パス>` を足す。冒頭の配置先の一覧にも 1 行足す

- [ ] **Step 4: テストを実行して通ることを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: `OK test-pi-superagents`、終了コード 0

- [ ] **Step 5: 配置を一時 HOME で確かめる**

Run: `tmp="$(mktemp -d)"; env HOME="$tmp" zsh scripts/setup_pi_superagents.zsh --if-absent && cmp .devcontainer/pi-herdr-launcher-resume.ts "$tmp/.pi/agent/extensions/herdr-launcher-resume.ts"; echo "exit=$?"; rm -rf -- "${tmp:?}"`
Expected: `extension:` の表示、`exit=0`

- [ ] **Step 6: README を書き換える**

「ランチャーを通さない Pi と同梱の既定 model」の「Herdr の復元の後に上のメッセージが出たら…」の段落の前に、ランチャーで再開する仕組み（ヘルパが名前を渡し、拡張が `<ランチャー> --session <セッションファイル>` を報告する。`/new` などで切り替えると報告し直す。素の `pi`・子 Pi は対象外）と、既存の環境での反映（ランチャーの外のシェルで `zsh scripts/setup_pi_superagents.zsh --if-absent` を実行し、ランチャーの Pi を起動し直す。起動し直すまでの Pi は今までどおり Pi で再開される）を書く。上のメッセージの段落は「拡張の配置の前に起動した Pi や素の `pi` が復元されたとき」に書き換える。「次は扱っていない」の 1 点目を消し、利用者がランチャーに付けた追加の引数は再開で再現しないことを書く。「pi の TUI モードと Herdr のスクロール履歴」の段落の setup の説明にも、拡張を毎回更新することを足す。

- [ ] **Step 7: 実機で確かめる（テスト用 Herdr セッション）**

名前付きのセッション（`herdr --session <名前> server`。呼び出しは `HERDR_*` を外した `env -u …` で行う）のペインで、worktree のランチャーを `zsh <worktree>/.devcontainer/pigs --session-dir <一時ディレクトリ> -e <worktree>/.devcontainer/pi-herdr-launcher-resume.ts` で起動し、次を記録する。既定のセッションのペインに触れない。終わったらセッションを止めて消す（`herdr session stop` / `herdr session delete`）。

1. 起動の後: テスト用セッションの `session.json` の `agent_resume.argv` が `["pigs", "--session", <セッションファイル>]` で、`agent_session.value` と同じパス（起動直後の `resume_not_accepted` をやり直しで越える）
2. `/new` の後: `agent_resume.argv[2]` と `agent_session.value` が新しいパス
3. サーバーの再起動の後: ペインに `pigs --session <新しいパス>` が入力され、Pi が起動する（`agent` が `pi`）

- [ ] **Step 8: commit**

```bash
git add .devcontainer/pi-superagents-exec.zsh .devcontainer/test-pi-superagents.bash scripts/setup_pi_superagents.zsh .devcontainer/README.md
git commit -m "feat: resume launcher Pi panes through the launcher on Herdr restore"
```

## 検証の入口

worktree のルートで `README.md` の「テスト」のコマンド（ワールドの行を除く）:

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
```

## 完了

（実行後に記録する）
