# Issue #307 ランチャーを通さない Pi の同梱既定 model を止める 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の実行許可。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/307

**Goal:** ランチャーを通さない Pi（素の `pi`、Herdr の復元）と、tier が欠けたランチャーの設定で、pi-superagents が同梱の既定 model（`opencode-go/glm-5.3-flash` など）へ黙って子の要求を送る経路を止める。

**Architecture:** setup が共有の bind 先 `~/.pi/agent/extensions/subagent/config.json` に、未知のトップレベルのキーを持つ停止用の設定を置き、ランチャーの外では拡張を無効にする。ランチャーの共通ヘルパは、起動前に tier（cheap・balanced・max）の model がそろっているかを確かめる。README に経路と調べ方を書く。

**Tech Stack:** zsh（ヘルパ・setup）、Node.js 24（JSON の読み取り）、bash（テスト）、pi-superagents 1.14.4、Pi 1.5.0、bwrap

**Spec:** `docs/superpowers/specs/2026-11-04-issue-307-pigs-tier-model-design.md`

## Global Constraints

- 停止用のキー: `launcherRequired_doNotRemove_restartPiViaLauncher`（setup・README・テストで同じ文字列）
- 確かめる tier: `cheap`・`balanced`・`max`。値は文字列か `{ "model": … }`。model は `provider/model`（最初の `/` の前後が空でない）。thinking は確かめない
- 退避名は既存と同じ `config.json.bak.YYYYMMDD-HHMMSS`、衝突したら `.1`, `.2`, …
- 停止用の設定は通常と `--if-absent` の両方で揃える。キーを持つ JSON のオブジェクトなら残す
- エラーにファイルの中身を出さない
- テストは一時の `HOME` だけを使い、利用者の `~/.pi` を変えない（`env HOME=… ` のワンショット）
- pi-superagents・Pi・Herdr のファイルは変えない

## Review Focus

- 共有の `config.json` が symlink・ディレクトリ: setup は触らずに止まる（L。エラーで止まるのでテストしない）
- 共有の `config.json` が壊れた JSON・BOM 付き・配列: 停止用ではないとみなし、退避して置き換える（どれも拡張は止まるか既定に落ちるので、置き換える側が安全）
- ランチャーの設定が BOM 付き: ヘルパは BOM を外して読む（`pi_launcher_require_models` と同じ）。拡張が読めなければ拡張側で止まる
- provider の無い model（`glm-5.3-flash`）: ヘルパが止める（子 Pi の曖昧な照合で別 provider に解決させない）
- `--if-absent` と通常の起動の差: 停止用の設定はどちらでも同じ関数で揃える。テストは rebuild の経路の `--if-absent` を代表にする

## 実行予算

- Issue 全体の能動時間: 300 分（14:07Z 開始。似た規模の PR #294・#301 の実績が 1 サイクルで 2〜3 時間）
- phase の目安: 調査・Spec・Plan 35 分、実装（Task 1〜3）60 分、検証・全体レビュー 30 分、PR 15 分、ループ 1〜2 サイクル（1 サイクル 45 分のレビュー＋計画・修正 15 分）
- worker: 実装は self なので runner の担当は無い。全体レビューのサブエージェントは同期で 20 分。ループの担当の期限は pr-review-fix-loop の設定のとおり
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回。安全の失敗は再試行しない
- checkpoint: 各 Task の完了、全体の検証の後、PR の作成の後、予算の 50%（16:37Z）と 100%（19:07Z）
- 縮小・切り出し・方法変更の候補: (1) 拡張の実コードでの停止の確認がテストで動かないときは、手で確かめて PR に記録し、テストからは外す (2) README の調べ方を短くする (3) Herdr の再開・子の照合は最初から範囲外（後続の Issue）

## contingency

- 導入済みの拡張をテストから読めない（配置の違い、Node の型除去の制限、export の変更）: 拡張が無い環境（postCreate 前）だけ skip して表示し、拡張があるのに読めないときは失敗させる。読み方そのものが合わないと最初の RED で分かったら、意味を保つ最小の読み方の修正（複製先や import の調整）を ledger に残して続ける。直せなければ縮小の候補 (1) に切り替える
- 全ランチャーの tier の検査で既存のテストの準備（tier が空の `make_home`）が落ちる: 準備を tier のそろった設定に直す。検査の意味は変えない
- 拡張の検証が未知のトップレベルのキーを止めなくなっていると分かった: 実装を進めず、Spec の前提が崩れたので停止して報告する

## 受け入れ基準

- 動作環境: この Dev Container（Ubuntu 26.04、zsh、Node.js 24、bwrap）、Pi 1.5.0、pi-superagents 1.14.4。テストは一時の `HOME` で行い、利用者の `~/.pi` を変えない
- 実入力:
  - 共有の bind 先に、今回の環境と同じ同梱の既定の写し（balanced `opencode-go/glm-5.3-flash`）があるときの `setup_pi_superagents.zsh --if-absent`
  - `balanced` が無いランチャーの設定（`{"superagents":{"modelTiers":{"cheap":…,"max":…}}}`）での起動
  - リポジトリの `.devcontainer/pi-superagents/<launcher>.json` そのままの設定での起動
- 防御範囲:
  - 対象: ランチャーを通さない Pi が共有の bind 先を読む経路（素の `pi`、Herdr の復元）、ランチャーの設定の tier の欠け
  - 対象外: 子 Pi が設定した model を解決できないときの切り替え（pigt・pidid の起動前の検査を除く）、Herdr の復元の再開コマンド、`PI_CODING_AGENT_DIR` だけを変えた起動（拡張は `os.homedir()` を見るので変わらない）
  - 反例として通すもの: tier が揃ったリポジトリの設定でのランチャーの起動、文字列の形の tier、停止用のキーを持つ既存の共有設定（拡張が書き足したもの）

## 要件と Task の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| tier の欠けで止める（B） | 1 | balanced が無い設定で終了コード 1、bwrap に進まない | `test_incomplete_tiers_fail_closed` |
| 揃った設定・文字列の tier は通す | 1 | dry-run の argv の先頭が `bwrap` | 同上の通る例と既存のランチャーのテスト |
| 共有の bind 先を停止用にする（A） | 2 | 既存の写しが退避され、拡張の読み込みが `blocked: true` | `test_setup_guards_shared_bind_target` |
| 停止用のキーを持つ既存は残す | 2 | 2 回目で退避が増えない・内容が変わらない | 同上 |
| ランチャーの中は止めない | 2 | ランチャーのディレクトリの読み込みが `blocked: false` | 同上 |
| 経路・再開・調べ方の記録（C） | 3 | README の節 | 通読と `git diff` |

共有する条件: 停止用のキーの文字列（Task 2 の setup・テスト、Task 3 の README）と、`make_home` の準備（Task 1 で直し、Task 2 も使う）。統合の確認は Task 3 の最後の検証で行う。

## 実行方式

`superpowers:executing-plans`（このセッションが実装する）。`implement_task.py check` の `self` が true で、3 つの Task が同じテストのファイルを順に変えるため、並行にできない。最後にブランチ全体のレビューをサブエージェントに 1 回依頼する。

---

### Task 1: 全ランチャーで tier の欠けを起動前に止める

**Files:**
- Modify: `.devcontainer/pi-superagents-exec.zsh`（`pi_superagents_exec` の設定ファイルの存在の確認の直後）
- Test: `.devcontainer/test-pi-superagents.bash`

**テストの要否:** 書く（S）。壊れると、欠けた tier が同梱の既定 model で埋まり、エラーにならずに別 provider へ要求が送られる。

**Interfaces:**
- Produces: `pi_launcher_require_tiers <launcher> <config>`（0: そろっている、1: 理由を stderr に出す）。`make_home <name> with-config` は cheap・balanced・max のそろった設定を置く（Task 2 も使う）

- [ ] **Step 1: 準備とテストを書く**

`make_home` の `with-config` が書く設定を、3 tier がそろったもの（`{"superagents":{"modelTiers":{"cheap":"test/cheap","balanced":{"model":"test/balanced","thinking":"high"},"max":{"model":"test/max"}}}}`、cheap は文字列の形）にする。

`test_incomplete_tiers_fail_closed`（防ぐ損害をコメントに書く）:
- `make_home pigs with-config` の設定から `balanced` を除き、`run_helper` で起動 → 終了コード 1、stderr に `pigs` と設定のパス、stdout に `bwrap` が無い
- model を `glm-5.3-flash`（provider 無し）にした `balanced` も終了コード 1
- そろった設定（`make_home` のまま）は stdout の 1 行目が `bwrap`

- [ ] **Step 2: RED を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: `FAIL: ... must exit 1` で止まる（今のヘルパは tier を見ない）

- [ ] **Step 3: `pi_launcher_require_tiers` を実装し、`pi_superagents_exec` から呼ぶ**

Node の `-e` で読む（BOM を外す、例外はすべて失敗、出力は捨てる）。メッセージは `[<launcher>] ERROR:`、設定のパス、欠けた tier が同梱の既定 model に切り替わるので止めること、直し方（`.devcontainer/pi-superagents/<launcher>.json` に合わせて補う、または `zsh scripts/setup_pi_superagents.zsh` で置き直す。既存は退避される）。

- [ ] **Step 4: GREEN を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: `OK test-pi-superagents`

- [ ] **Step 5: Commit**

```bash
git add .devcontainer/pi-superagents-exec.zsh .devcontainer/test-pi-superagents.bash
git commit -m "fix: stop launchers when a pi-superagents tier is missing"
```

### Task 2: setup が共有の bind 先に停止用の設定を置く

**Files:**
- Modify: `scripts/setup_pi_superagents.zsh`
- Test: `.devcontainer/test-pi-superagents.bash`

**テストの要否:** 書く（S）。壊れると、ランチャーの外の Pi が同梱の既定 model の子を黙って動かす。既存の共有設定を退避せずに消すとデータを失う。

**Interfaces:**
- Consumes: Task 1 の `make_home`、既存の `run_setup`
- Produces: setup の `GUARD_KEY='launcherRequired_doNotRemove_restartPiViaLauncher'` と、共有の `config.json` を揃える処理（README が参照する挙動）

- [ ] **Step 1: テストを書く**

`test_setup_guards_shared_bind_target`（防ぐ損害をコメントに書く）:
- 一時の `HOME` の共有の bind 先に、同梱の既定の写し（`{"superagents":{"modelTiers":{"balanced":{"model":"opencode-go/glm-5.3-flash","thinking":"high"}}}}`）を置き、`run_setup "$home" --if-absent`
- 退避が 1 件で、バイト列が元と同じ（`cmp -s`）
- 共有の `config.json` がキーを持つ（Node で読む）
- 共有の `config.json` に `superagents` を書き足し（拡張の移行処理の代わり）、もう一度 `--if-absent` → 退避は 1 件のまま、内容も変わらない
- 拡張の実コード: `${HOME}/.pi/agent/npm/node_modules/@teelicht/pi-superagents`（テストの実行者の HOME）が無ければ `SKIP` を stderr に出してこの部分だけ省く。あれば `src`・`default-config.json`・`package.json` を `TEST_ROOT` に複製し（Node は `node_modules` の下の型除去を拒む）、`loadRuntimeConfigState(<複製>, <dir>, [])` の `blocked` が、共有の bind 先で `true`、`subagent.d/pigs` で `false`

- [ ] **Step 2: RED を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: 退避が 0 件で FAIL

- [ ] **Step 3: setup に共有の bind 先の処理を足す**

- 既存の `config.json` が symlink・通常のファイル以外なら、触らずにエラーで終了する
- キーを持つ JSON のオブジェクトなら「保持」と表示して残す（Node で判定。BOM は外さない＝拡張と同じ）
- それ以外は、ランチャー別の設定と同じ退避の名前で退避してから、停止用の設定を書く（同じディレクトリの一時ファイルから `mv`）。退避の名前を作る処理は関数にして、ランチャーの退避と共有する
- キーの値は Spec の A の説明（理由・キーを消さない・ランチャーから起動し直す・README の節名）
- 冒頭のコメントの「作成するもの」と `--if-absent` の説明を直す

- [ ] **Step 4: GREEN を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: `OK test-pi-superagents`（拡張がある環境では SKIP が出ない）

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_pi_superagents.zsh .devcontainer/test-pi-superagents.bash
git commit -m "fix: disable pi-superagents outside launchers via the shared bind target"
```

### Task 3: README と統合の確認

**Files:**
- Modify: `.devcontainer/README.md`（「pi のモデル定義とランチャー」の配置の一覧、「pi-superagents のランチャー別 model tier」）

**テストの要否:** 書かない（文書。F）。代わりに通読と `git diff`、全体の検証。

- [ ] **Step 1: README を書く**

Spec の C の項目を、「pi-superagents のランチャー別 model tier」の「`bwrap` が無い…」の段落の後に節（`#### ランチャーを通さない Pi と同梱の既定 model`）として書く。配置の一覧に共有の停止用の設定を足し、「`bwrap` が無い、またはランチャー用の設定が無い場合」の段落に tier の欠けを足す。

- [ ] **Step 2: 統合の確認**

- 停止用のキーの文字列が setup・テスト・README で一致する（`grep -rn launcherRequired_doNotRemove_restartPiViaLauncher`）
- 全体の検証（下）を実行する

- [ ] **Step 3: Commit**

```bash
git add .devcontainer/README.md
git commit -m "docs: explain launcher-less pi-superagents fallback and recovery"
```

## 検証の入口

worktree のルートで `README.md` の「テスト」のコマンド（ワールドの行を除く）:

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
```

## 完了

- 実行: executing-plans（self、claude-opus-5-5）。開始 2026-11-04 14:07Z
- 所要時間（PR の作成まで）: 調査・Spec・Plan 約 15 分、Task 1 約 2 分、Task 2 約 3 分、Task 3 約 3 分、全体の検証とブランチ全体のレビュー約 12 分、修正 1 回（レビューの Critical 1 件・README 1 件・pytest の準備）約 10 分
- ブランチ全体のレビュー（opus のサブエージェント）: With fixes。Critical 1 件（ランチャーの中で setup を実行すると、停止用の設定がランチャーの設定を置き換え、成功と表示される）を `test_setup_refuses_inside_a_launcher` の RED→GREEN で修正。README の表示の場面の記述（Minor）を、素の `pi` を使う手順で毎回エラーが出て停止用のキーを消されかねないため Important に格上げして修正
- 持ち越した Minor: ヘルパの BOM の正規表現が `﻿` でなく文字そのもの（消えても止まる側に倒れる）、`test_incomplete_tiers_fail_closed` の stderr の文面の確認は L（既存のテストに書き方を揃えた）、テストのコメントと Spec の「移行処理は読み込みのたびに書き足す」は「変更があるときだけ」が正しい（結論は変わらない）
- 計画と違えたこと: 全体の pytest で、Task 1 の検査が `tools/devenv_migration/tests/` の準備（tier が空・cheap だけ）を止めた（19 件）。contingency のとおり、準備をそろった tier に直した（テストの意味は変えない）
- 検証: PR の前の最後の commit で、検証の入口の 3 コマンドを実行する（結果は PR 本文とセッションディレクトリの記録）
- ループ（pr-review-fix-loop）の結果は PR のコメントに残す
