# Issue #310 子 Pi の model の照合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（実行許可: `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/310 --merge`。内容の承認ではない）
- base: `main` `edd4ffd622efcc72b7a79d48201d3e07959f8de8`

**Goal:** pi-superagents の子 Pi が、tier の model（`--models`）と違う model で最初の要求を送る前に終了コード 1 で止まり、ランチャーは照合を読み込ませない設定では起動しない。

**Architecture:** このリポジトリの Pi の拡張 `pi-superagents-model-guard.ts` を、setup が `~/.pi/agent/extensions/subagent.d/` に置き、各ランチャーの tier 設定の `superagents.extensions` に挙げる。子 Pi の `session_start` で `ctx.model` と `--models` を照合する。共通ヘルパは、tier 設定が照合の拡張を挙げ、そのファイルが在ることを起動前に確かめる。

**Tech Stack:** TypeScript（Pi の拡張。Node.js 24 の型除去で読める範囲の構文だけ）、zsh（共通ヘルパ・setup）、bash（テスト）、Pi 1.5.0、pi-superagents 1.14.4

**Spec:** `docs/superpowers/specs/2026-11-05-issue-310-pi-child-model-guard-design.md`

## Global Constraints

- 拡張のソースは `.devcontainer/pi-superagents-model-guard.ts`、配置先は `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts`、tier 設定に挙げる文字列は `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts`
- 出力の先頭は `[pi-superagents-model-guard]`。止めるときだけ stderr に書き、終了コード 1（`process.exit(1)`）。例外の内容・資格情報・タスクの本文は書かない
- thinking level の集合は `off`・`minimal`・`low`・`medium`・`high`・`xhigh`・`max`
- pi-superagents・Pi 本体は変えない
- `.devcontainer/` にワークスペースの絶対パスを書かない（`.devcontainer/test-readme.bash`）
- テストで Pi を起動するときは `env -i` で資格情報の環境変数を渡さず、stdin を `/dev/null` にし、`PI_OFFLINE=1` と一時の `PI_CODING_AGENT_DIR`・`HOME` を使う。偽のサーバー以外へ要求を送らない
- テストの採用基準（`AGENTS.md`）の S だけを書く

## Review Focus

1. tier 設定の model の ID が `/` を含む（`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017`、`commandcode/meta/muse-spark-1.3-contributor`）: provider は最初の `/` の前で、ID は残り全体として一致させる。Task 1 の通る例に `/` を含む ID を使う
2. 利用者が編集した tier 設定（BOM 付き、`superagents` に他のキーがある、拡張を `~/` でなく絶対パスで挙げる）: ランチャーの検査は、`~/` を `HOME` で展開した結果と絶対パスの両方を受け付け、BOM を外して読む。Task 2 のテストの設定は BOM と他のキーを含め、通る例の 1 つは絶対パスで挙げる
3. 大文字小文字だけが違う model（`FakeOK/Model-A`）: Pi は同じ model に解決するので通す（Task 1 の規則。テストは書かない＝ D）
4. Pi が `session_start` の前に要求を送るよう変わる: Task 1 のテストが偽のサーバーへの要求の件数で気付く
5. setup をランチャーの中で実行する: 既存の拒否（`test_setup_refuses_inside_a_launcher`）が、拡張の配置より前に止まることを保つ。Task 2 で配置の位置を拒否の後にする

## 受け入れ基準

Spec の「受け入れ基準」をそのまま使う。実装担当・レビュー担当の双方に同じ本文を渡す。

1. ランチャーの tier 設定で起動した子 Pi が、`--models` の model と違う model を選ぶとき（資格情報が無い、ID の誤り、同じ ID の別の provider、部分一致）、最初の要求の前に終了コード 1 で終わる。pi-superagents の実行記録（`run-history.jsonl` の error、`meta.json` の error、親の結果）に、照合の拡張の出力が残る
2. 要求どおりの model に解決できる子 Pi は、今までどおり動く
3. 止めたときの出力は、要求された model・Pi が選んだ model・理由を含み、例外の内容・資格情報・タスクの本文を含まない
4. 13 のランチャーのリポジトリの tier 設定が照合の拡張を挙げ、`setup_pi_superagents.zsh` が通常と `--if-absent` のどちらでも照合の拡張を置く
5. tier 設定が照合の拡張を挙げていない、または照合の拡張のファイルが無いとき、ランチャーは起動せずに直し方を案内する
6. `.devcontainer/README.md` に、照合の仕組み・止まったときの見方・既存の環境での手順・#305 の検査との関係・対象外を書く
7. 検証の入口（`README.md` の「テスト」。ワールドの行を除く）がすべて通る

- 動作環境: Dev Container（Ubuntu 26.04 LTS）、Pi 1.5.0、pi-superagents 1.14.4、Node.js 24、zsh、bwrap。子 Pi は pi-superagents が `--mode json -p` で、stdin を閉じて起動する
- 実入力: 子 Pi の argv の `--models` は 1 件で、`<provider>/<id>:<thinking>`（例: `openai-codex/gpt-6.1-sol:xhigh`、`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017:high`）。ランチャーの tier 設定は利用者が編集しうる JSON（BOM、`superagents` の他のキー、拡張が書き足すキー）
- 防御範囲: 対象は、ランチャーから起動した Pi の pi-superagents の子で、`--models` を渡されたもの。対象外の反例は、`--models` の無い子、`--model` で起動した Pi、thinking の違い（`fakeok/model-a:max` が `high` になる）、要求の時点の資格情報のエラー（`!command` の失敗。別の model に切り替わらない）、ランチャーを通さない Pi、agent-workspace の setup による共有の設定の置き換え

## 要件と Task の対応

| 受け入れ基準 | 担当 Task | 観測する結果 | 検証方法 |
|---|---|---|---|
| 1 | Task 1 | 偽のサーバーへの要求 0 件・終了コード 1・stderr の照合の出力 | `bash .devcontainer/test-pi-superagents-model-guard.bash` |
| 1（実行記録） | Task 4 | pi-superagents が終了コード 1 の子の stderr を `result.error` にする（Spec の事実 6） | ソースの該当箇所（`child-runner.ts` の `finish`・`finalizeChildResult`）を Task 4 で読み直す。pi-superagents は変えない |
| 2 | Task 1 | 一致する model で偽のサーバーに要求が届く | 同上 |
| 3 | Task 1 | 例外の文字列が stderr に出ない | 同上 |
| 4 | Task 2 | 13 の JSON が挙げる・setup が置く | `node` で 13 の JSON を読む一時の確認、`run_setup` の後のファイルの確認（コミットしない） |
| 5 | Task 2 | 拡張を挙げない設定で bwrap に進まない | `bash .devcontainer/test-pi-superagents.bash` |
| 6 | Task 3 | README の節 | `git diff` の確認 |
| 7 | Task 4 | 入口の終了コード 0 | `README.md` の「テスト」の 3 コマンド |

共有する前提: 拡張のパス（配置先と tier 設定の文字列）を Task 1（拡張・テスト）、Task 2（ヘルパ・setup・設定・テスト）、Task 3（README）が使う。統合担当は Task 4 で、3 か所のパスが Global Constraints と一致することを `git grep` で確かめる。

---

### Task 1: 子 Pi の model の照合の拡張

**Files:**
- Create: `.devcontainer/pi-superagents-model-guard.ts`
- Create: `.devcontainer/test-pi-superagents-model-guard.bash`

**Interfaces:**
- Produces: Pi の拡張のモジュール。`export default function (pi: { on(event: "session_start", handler: (event: unknown, ctx: any) => Promise<void> | void): void }): void`。`session_start` で `process.argv.slice(2)` の `--models`（最後の指定）を読み、`ctx.model`（`{provider, id}`）と `ctx.modelRegistry.getAll()` を 1 回ずつ読む
- テストの要否: 要（S）。壊れると、子が黙って別の model・別の provider に要求を送る。例外の内容が実行記録に残ると秘密が漏れうる

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-pi-superagents-model-guard.bash`（`set -euo pipefail`、`TEST_ROOT="$(mktemp -d)"`、`trap 'rm -rf -- "${TEST_ROOT:?}"' EXIT`、`.devcontainer/test-pi-herdr-launcher-resume.bash` と同じ形）。`pi` が無ければ `SKIP:` を stderr に書いて 0 で終わる。

準備:
- 偽のサーバー（node の `http`、`127.0.0.1` の空いているポート）。受けた要求を 1 行ずつファイルに書き、400 を返す（Pi が再試行しない）
- `PI_CODING_AGENT_DIR` の `models.json`: provider `fakeok`（`apiKey` あり、`api: "openai-completions"`、`baseUrl` が偽のサーバー、models `model-a`（`reasoning: true`）と `vendor/model-b`）と、provider `fakenokey`（`apiKey` なし、models `model-a`）
- Pi の起動: `env -i PATH="<node の dir>:/usr/bin:/bin" HOME=... PI_CODING_AGENT_DIR=... PI_OFFLINE=1 pi --mode json -p --no-session --models <pattern> --no-extensions --extension <拡張> 'Task: test' < /dev/null`。`timeout 60` を付ける

テスト（各関数の前に「防ぐ損害」をコメントで書く）:

```bash
# 防ぐ損害: 名指しの provider に資格情報が無いと、Pi は警告だけを出して同じ ID を持つ別の provider の model を選び、
# 終了コード 0 で要求を送る（#310）。照合が ID だけを見ると通してしまう。通る例: 要求どおりに解決できる model。
test_mismatched_model_stops_before_the_first_request() {
    # fakenokey/model-a:high → Pi は fakeok/model-a を選ぶ
    # assert: 終了コード 1、偽のサーバーへの要求 0 件
    # assert: stderr に "[pi-superagents-model-guard]"、"fakenokey/model-a:high"、"fakeok/model-a" が含まれる
    # 通る例: fakeok/vendor/model-b:high → 偽のサーバーに要求が 1 件以上届き、stderr に "[pi-superagents-model-guard]" が無い
}

# 防ぐ損害: 例外の内容（資格情報・コマンドの文字列を含みうる）を書くと、pi-superagents が子の stderr を
# run-history.jsonl・meta.json・親の結果に残し、秘密が記録に漏れる。
test_exception_details_are_not_written() {
    # node のサブプロセスで拡張を import し、process.argv に "--models fakeok/model-a" を入れ、
    # model の getter が "secret-" + "value-" + 乱数 を含む Error を投げる ctx で session_start を呼ぶ
    # assert: 終了コード 1、stderr に "[pi-superagents-model-guard]" があり、秘密の文字列が無い
}
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-pi-superagents-model-guard.bash`
Expected: FAIL（拡張のファイルが無いため Pi が拡張を読めない、または import が失敗する）

- [ ] **Step 3: `.devcontainer/pi-superagents-model-guard.ts` を実装する**

- 冒頭のコメントに、目的（#310）、子 Pi の読み込まれ方（`superagents.extensions`・`--no-extensions`）、`process.exit(1)` を使う理由（print モードに終了コード付きで止める API が無い）、例外を自分で捕まえる理由を書く
- `--models` の読み方は Pi の引数の解析と同じ: `--` で止め、後の `--models` が勝ち、カンマで分けて空白を除き、空を捨てる。`--models` が無ければ何もしない
- 一致の規則は Spec の D2（thinking の接尾辞を外す、glob は一致しない、知っている provider は provider と ID、それ以外は ID 全体、大文字小文字を区別しない）
- `ctx.model` が無い・`getAll` が関数でない・形が違う → 止める（Pi の API が変わった旨と、拡張を新しい Pi に合わせる必要がある旨）
- 止めるときの行: 1 行目 `[pi-superagents-model-guard] ERROR: 子 Pi が、要求された model と違う model で要求を送ろうとしています。最初の要求の前に終了します。`、続けて字下げした `要求された model（--models）: <値>`、`Pi が選んだ model: <provider/id か なし>`、理由、主な原因（子 Pi の環境にその provider の資格情報が無い、model ID の誤り、catalog が古い）、確かめ方（ランチャーの外の素の `pi` で `pi --list-models <provider>`）
- 例外は `try/catch` で捕まえ、内容を書かずに止める

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/test-pi-superagents-model-guard.bash`
Expected: PASS。続けて、拡張の 1 行を変えた変異（一致を ID だけにする、`catch` で `String(error)` を書く）でそれぞれ FAIL になることを一時的に確かめ、元に戻す（変異はコミットしない）

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/pi-superagents-model-guard.ts .devcontainer/test-pi-superagents-model-guard.bash
git commit -m "feat: stop pi-superagents children before they use a model other than the tier model"
```

### Task 2: ランチャーの起動前の検査・setup の配置・tier 設定

**Files:**
- Modify: `.devcontainer/pi-superagents-exec.zsh`（`pi_launcher_require_tiers` の後に新しい関数。`pi_superagents_exec` から呼ぶ）
- Modify: `scripts/setup_pi_superagents.zsh`（ヘッダの「作成するもの」、配置）
- Modify: `.devcontainer/pi-superagents/*.json`（13 ファイル）
- Modify: `.devcontainer/test-pi-superagents.bash`（`make_home`・`model_home`・`test_incomplete_tiers_fail_closed` の設定、新しいテスト）

**Interfaces:**
- Consumes: Task 1 の拡張のファイル `.devcontainer/pi-superagents-model-guard.ts`
- Produces: `pi_launcher_require_model_guard <launcher> <config>`（zsh。0 で通す、1 で止める）。setup は `${HOME}/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` を毎回置く
- テストの要否: 起動前の検査は要（S。壊れると照合が無いまま子が動く）。setup の配置と 13 の JSON は不要（F。欠けると起動前の検査が止める＝ L）。代わりに一時の確認で、13 の JSON が挙げていること、setup の両方のモードでファイルが置かれることを確かめる

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-pi-superagents.bash`:
- `make_home` の `with-config`: 設定に `"extensions":["~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts"]` を足し、`${home}/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` に空でないファイルを置く
- `model_home` が書き直す設定にも同じ `extensions` を足す
- `test_incomplete_tiers_fail_closed` が書く 2 つの設定にも同じ `extensions` を足す（tier の検査で止まることを確かめ続けるため）
- 新しいテスト:

```bash
# 防ぐ損害: pi-superagents は tier 設定の superagents.extensions に挙げた拡張だけを子 Pi に読み込ませる。照合の拡張を
# 挙げていない設定（--if-absent で残った既存の設定など）や、拡張のファイルが無い環境で起動すると、子は tier の model を
# 使えないときに黙って別の model に要求を送る（#310）。代表はヘルパ。
# 通る例: BOM 付きで superagents に他のキーがあり、拡張を絶対パスで挙げた設定。
test_missing_model_guard_fails_closed() {
    # 1) 通る例 → 出力の 1 行目が bwrap
    # 2) tier はそろっているが extensions が無い設定 → 終了コード 1、出力が空、stderr に "[pigs]"・設定のパス・
    #    "setup_pi_superagents.zsh" が含まれる
    # 3) 設定は挙げているが拡張のファイルが無い → 終了コード 1、出力が空
}
```

テストの実行の一覧（ファイル末尾）に `test_missing_model_guard_fails_closed` を足す。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: FAIL（2) の設定が bwrap に進む）

- [ ] **Step 3: 実装する**

- `pi_launcher_require_model_guard`: 拡張のパスは `${HOME}/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts`。通常のファイルとして在り、設定（BOM を外して JSON として読む）の `superagents.extensions` が配列で、`~` / `~/...` を `HOME` で展開した要素か絶対パスの要素のどれかがそのパスと等しければ 0。読めない・形が違う・無い → 1。設定の中身はエラーに出さない。止めるときの案内は、設定のパス・拡張のパス・照合が無いと何が起きるか・`zsh scripts/setup_pi_superagents.zsh`（ランチャー別の設定を退避してから置き換える）・tier を編集している場合は `superagents.extensions` に `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` を足すこと
- `pi_superagents_exec`: `pi_launcher_require_tiers` の直後に `pi_launcher_require_model_guard "${launcher}" "${config}" || return 1`
- setup: `readonly MODEL_GUARD_SOURCE="${REPO_ROOT}/.devcontainer/pi-superagents-model-guard.ts"`。ランチャーの中での実行の拒否より後、herdr-launcher-resume の配置の後に `mkdir -p "${LAUNCHER_ROOT}"` と `install -m 0644` で毎回置き、`print -r -- "extension: <配置先>"` を出す。ヘッダの「作成するもの」に足す
- 13 の JSON: `superagents` の最初のキーとして `"extensions": ["~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts"]` を足す（各ファイルの字下げに合わせる）

- [ ] **Step 4: テストと一時の確認**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: PASS

一時の確認（コミットしない）:
- `for f in .devcontainer/pi-superagents/*.json; do node -e '...extensions に配置先の文字列があるか...' "$f"; done` が 13 件とも成功
- 一時 HOME で `zsh scripts/setup_pi_superagents.zsh` と `--if-absent` を実行し、どちらでも配置先のファイルが `.devcontainer/pi-superagents-model-guard.ts` と同じバイト列になる（偽の `bwrap` と `pi` を PATH に置く。`test-pi-superagents.bash` の `run_setup` と同じ形）
- 変異: `pi_superagents_exec` から呼び出しを外すと新しいテストが FAIL になる（元に戻す）

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/pi-superagents-exec.zsh scripts/setup_pi_superagents.zsh .devcontainer/pi-superagents/*.json .devcontainer/test-pi-superagents.bash
git commit -m "feat: require the child model guard in launcher tier configs"
```

### Task 3: README

**Files:**
- Modify: `.devcontainer/README.md`

**Interfaces:**
- Consumes: Task 1・2 のパス・出力の先頭・案内のコマンド
- テストの要否: 不要（F。文書の文言）。代わりに `git diff` の確認と `bash .devcontainer/test-readme.bash`

- [ ] **Step 1: 書き換える**

- 「pi のモデル定義とランチャー」の配置の一覧: 照合の拡張 → `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` を足し、「この 4 種」を「この 5 種」にして、参照先に新しい節を足す
- 「Terra / DeepInfra ランチャーの既存環境への追加」の「新しい tier-guard 拡張は追加しない。」: #305 の起動前の検査（認証を解決しないメタデータの検査）は `pigt`・`pidid` に残し、子 Pi が実行時に model を解決できないときの切り替えは、全ランチャーで子 Pi の中の照合（新しい節）が止める、という関係に書き換える
- 「pi-superagents のランチャー別 model tier」の「`bwrap` が無い、…ランチャーは起動せずに案内を出す。」に、照合の拡張を挙げていない設定・拡張のファイルが無い場合を足す
- 「ランチャーを通さない Pi と同梱の既定 model」の「次は扱っていない（#307 の持ち越し）。」の箇条を、新しい節への参照に置き換える。「子が意図しない model で動いた疑いがあるときは」の記録の一覧に、照合で止まった子の error を足す
- 新しい節 `#### 子 Pi の model の照合`（「ランチャーを通さない Pi と同梱の既定 model」と「Herdr の復元とランチャー」の間）: 何を防ぐか（Pi は `--models` を資格情報のある model からだけ解決し、解決できないと警告だけで別の model を使う）、仕組み（拡張の場所、`superagents.extensions`、`session_start` の `ctx.model` と `--models` の照合、一致の規則の要点）、止まったときの出力の例と記録の場所（`run-history.jsonl`・`meta.json`・親の結果）、止まったときの直し方、既存の環境の手順（ランチャーが止まったら `zsh scripts/setup_pi_superagents.zsh`、tier を編集していれば `superagents.extensions` に足す）、agent-workspace の `pi-superagents-tier-guard.ts` との関係（別のファイル。agent-workspace の setup が置き換えた設定はランチャーが止める）、対象外（`--models` の無い子、thinking の違い、要求の時点の資格情報のエラー）

- [ ] **Step 2: 確認**

Run: `git diff -- .devcontainer/README.md` を読み、パス・コマンドが Task 1・2 と一致することを確かめる。`bash .devcontainer/test-readme.bash`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .devcontainer/README.md
git commit -m "docs: describe the child Pi model guard"
```

### Task 4: 統合の確認・全体レビュー

**Files:** なし（確認と、必要なら Spec・Plan の記録の追記）

- テストの要否: 不要（統合の確認）

- [ ] **Step 1: 共有する前提の照合** — `git grep -n 'pi-superagents-model-guard' -- .devcontainer scripts` で、配置先・tier 設定の文字列・ヘルパの検査・README が Global Constraints の値と一致する
- [ ] **Step 2: 実行記録の確認** — pi-superagents 1.14.4 の `child-runner.ts` の `finish`（終了コードが 0 でないときの `stderrBuf` → `result.error`）と `finalizeChildResult`（`finishRun`・`writeMetadata` の `error`）を読み直し、受け入れ基準 1 の記録の経路を確かめる
- [ ] **Step 3: 検証の入口** — worktree のルートで次を実行し、終了コードとログのパスを記録する（ログは `PARENT_ROOT/tmp/agents/issue-310.*/`）
  - `bash .devcontainer/run-tests.bash`
  - `bash scripts/check-layout.sh`
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools`
- [ ] **Step 4: Spec→Plan→Task→証拠の照合** — 受け入れ基準ごとに、上の表の観測結果が得られたかを確かめる
- [ ] **Step 5: ブランチ全体のレビュー** — base `edd4ffd6` からの差分を、新しいサブエージェント（読み取りだけ）にレビューさせる。受け入れ基準の本文を渡す。指摘の採否は controller が裁定して ledger に書く

## 実行方式

`superpowers:executing-plans`（このセッションが inline で実装する）。Task は順に依存し（拡張 → ランチャーの検査と設定 → 文書）、`test-pi-superagents.bash` と README を複数の Task で触る。Pi 1.5.0・pi-superagents 1.14.4 の内部の確かめた事実を子に渡すのが重い。最後のブランチ全体のレビューだけを新しいサブエージェントに依頼する。作業領域は `PARENT_ROOT/tmp/agents/issue-310._0ihrq92/sdd/2026-11-05-issue-310-pi-child-model-guard/`。

## 実行予算

- Issue 全体の能動時間の予算: 480 分（ledger `PARENT_ROOT/tmp/agents/issue-310._0ihrq92/budget.jsonl`）。根拠: #307・#309（同じ領域、3〜4 Task、`--merge`）の実績と、ループの上限 3 サイクル ×（レビューの期限 45 分＋計画・修正 30 分）。ledger は 05:49 に始めたので、それより前の約 25 分（入力の確認・調査）は数えていない
- phase の目安: 準備・調査・Spec・Plan 60 分、Task 1 45 分、Task 2 60 分、Task 3 30 分、Task 4（検証・全体レビュー）45 分、PR 15 分、ループ 225 分
- worker: 全体レビューのサブエージェントは期限 30 分。ループの worker は pr-review-fix-loop の既定（レビューの期限 45 分）に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（信頼性）。安全の失敗（想定外の外部送信、実の資格情報の使用）は全体停止
- checkpoint: 各 Task の後、予算の 50%・100%、検証の失敗の直後、ループの各サイクルの後
- 縮小・切り出し・方法変更の候補: 実 Pi を使うテストが不安定なら、偽の ctx で `session_start` を呼ぶ単体テストに方法を変え（要求の前に止まることは Spec の事実 4 の実験の記録で補う）、PR に明記する。README の節が長くなりすぎたら要点だけにし、詳細は Spec を参照させる

## contingency（代替策）

- Pi 1.5.0 で `ctx.model` が `session_start` の時点で未設定の場合（Spec の事実 4 と違う）: `ctx.scopedModels` に要求の model があり、かつ `ctx.model` があれば一致を見る形に変える。意味（最初の要求の前に違う model を止める）を保てないなら止まって報告する
- 実 Pi のテストで偽のサーバーへの要求が再試行で遅い場合: 応答を 400 にする（Spec の実験で再試行しないことを確かめた）
- 既存のテストが新しい検査で落ちる場合: テスト用の設定に照合の拡張を足す（Task 2 の Step 1）。既存の守りの意味を変える変更が要るなら、ledger に理由を書いてから行う
- base が進んだ場合: issue-to-pr の停止条件に従い、新しい SHA を採用せず止まって報告する

## 完了

（実行後に記録する）
