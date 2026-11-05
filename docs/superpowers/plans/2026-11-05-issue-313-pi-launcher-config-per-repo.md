# Issue #313 ランチャー別の設定をリポジトリごとの場所に分ける 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft（issue-to-pr の run。実行許可は Spec の「管理」）
- Issue: https://github.com/usaturn/create-reso-world/issues/313

**Goal:** このリポジトリのランチャー別の tier 設定を `~/.pi/agent/extensions/subagent.d/create-reso-world/<launcher>/config.json` に移し、共有の `~/.pi` で agent-workspace の setup が `subagent.d/<launcher>/` を書き換えても、このリポジトリのランチャーが止まらないようにする。

**Architecture:** 共通ヘルパに設定のディレクトリを組み立てる関数 `pi_launcher_dir` を 1 つ置き、bind 元・起動前の検査（tier・照合の拡張・`pigt`/`pidid` の model）がすべてそれを使う。`setup_pi_superagents.zsh` は配置先を同じ場所に変え、旧位置は読まず・書かず・消さない。照合の拡張の場所と 13 の tier 設定は変えない。

**Tech Stack:** zsh（ヘルパ・setup）、bash（テスト）、Node.js 24（JSON の読み取り）、bwrap、pytest（`tools/devenv_migration/tests/`）

**Spec:** `docs/superpowers/specs/2026-11-05-issue-313-pi-launcher-config-per-repo-design.md`

## Global Constraints

- 新しい位置: `${HOME}/.pi/agent/extensions/subagent.d/create-reso-world/<launcher>/config.json`（HOME から組み立てる。`PI_CODING_AGENT_DIR` は使わない）
- 旧位置 `${HOME}/.pi/agent/extensions/subagent.d/<launcher>/` のファイルは、ヘルパも setup も読まず、書かず、退避せず、消さない
- 照合の拡張は `${HOME}/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` のまま。`.devcontainer/pi-superagents/<launcher>.json` は変えない
- agent-workspace のリポジトリと、利用者の `~/.pi` は変えない
- テストは一時 HOME（`env HOME=...`）だけを使う

## 受け入れ基準

Spec の「受け入れ基準」1〜8 と「動作環境・実入力・防御範囲」をそのまま満たす。要点:

- 動作環境: Dev Container（Ubuntu 26.04 LTS）、zsh、bwrap、Node.js 24、Pi 1.5.0、pi-superagents 1.14.4。`~/.pi` は agent-workspace の Dev Container と共有する bind mount
- 実入力: 旧位置は、agent-workspace の形（`superagents.extensions` に `~/.pi/agent/extensions/subagent.d/pi-superagents-tier-guard.ts` だけ、tier はこのリポジトリと同じ）、このリポジトリの以前の setup の形、`superagents.extensions` の無い古い形、利用者が編集した形のどれか。新しい位置は、無い・setup が書いた・利用者が編集した、のどれか
- 防御範囲: このリポジトリのランチャー・共通ヘルパ・`setup_pi_superagents.zsh`（`--if-absent` と provider の setup からの呼び出しを含む）。対象外は agent-workspace のランチャー・setup・拡張、共有の bind 先の停止用の設定、`~/.pi/agent/extensions/` 直下の拡張

## 要件の対応

| Spec の受け入れ基準 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 bind 元と検査が同じ新しい位置 | 1 | dry-run の `--bind` の直後が新しい位置。`pigt`・`pidid` の検査が新しい位置の編集を見る | `test_launchers_wrap_pi_with_their_own_config`・`test_unverifiable_or_unsupported_tiers_stop_before_pi`（場所を新しい位置に直す） |
| 2 setup が旧位置を書かない | 1 | 旧位置のバイト列と退避の数が変わらず、新しい位置にリポジトリの設定 | 新しいテスト `test_setup_leaves_legacy_launcher_configs_untouched` |
| 3 往復が無い | 1（統合の確認） | setup の後に旧位置を agent-workspace の形にしても、ヘルパの dry-run が bwrap まで進む | 一時的な確認（コミットしない。L） |
| 4 旧位置があるときの表示・新しい位置が無いときの案内 | 1 | setup の出力に注意の行、無いときは既存の案内で終了コード 1 | 一時的な確認・既存の `test_missing_config_fails_closed` |
| 5 新旧どちらの中でも setup が止まる | 1 | 終了コード が 0 でなく、何も書かない | `test_setup_refuses_inside_a_launcher`（新しい位置）・旧位置は一時的な確認 |
| 6 照合の拡張と tier 設定が変わらない | 1・2 | `git diff` に `.devcontainer/pi-superagents/`・`pi-superagents-model-guard.ts` が無い | `git diff --stat` |
| 7 文書と表示 | 2 | README と 2 つの setup の表示が新しい位置を指す | `git grep -n 'subagent\.d/'` の確認 |
| 8 検証の入口 | 2（統合） | 3 つのコマンドが終了コード 0 | `README.md` の「テスト」 |

共有する前提: ヘルパの `pi_launcher_dir` と setup の `LAUNCHER_ROOT` は同じ場所を指す（setup はヘルパを source しないので 2 か所に書く。ずれるとランチャーが「設定が見つかりません」で止まる＝ L）。統合の確認は Task 1 の最後の一時的な確認で行う。

## Review Focus

1. setup を旧位置を重ねたランチャー（更新の前に起動した Pi・agent-workspace のランチャー）の中で実行する: 何も書かずに止まる（Task 1 の一時的な確認）
2. 新しい位置が無く旧位置だけがある既存の環境でランチャーを起動する: 旧位置を読まず、setup の実行を案内して終了コード 1（既存の検査。Task 1 の一時的な確認）
3. `pigt`・`pidid` の起動前の model の検査と bind 元が別のファイルを見る: 同じファイルを見る（`test_unverifiable_or_unsupported_tiers_stop_before_pi` が新しい位置の編集で止まることで確かめる）
4. `--if-absent`（rebuild）で新しい位置が無い: リポジトリの設定が置かれ、旧位置は変わらない（Task 1 の一時的な確認）
5. 旧位置に利用者が編集した tier がある: 写さないが、setup の出力で写す必要を伝える（Task 1 の一時的な確認）

---

### Task 1: ヘルパと setup の場所を変え、テストを合わせる

**Files:**
- Modify: `.devcontainer/pi-superagents-exec.zsh`（`pi_launcher_dir` を足し、`pi_launcher_require_models`・`pi_superagents_exec` で使う。冒頭の説明に場所と理由を 1〜2 行）
- Modify: `scripts/setup_pi_superagents.zsh`（`LAUNCHER_ROOT`・照合の拡張の配置先・ランチャーの中の拒否・旧位置の注意・冒頭の説明）
- Modify: `.devcontainer/test-pi-superagents.bash`（場所の変数を足して既存のテストを新しい位置に直し、新しいテストを 1 件）
- Modify: `tools/devenv_migration/tests/test_pi_vertex_launchers.py`・`tools/devenv_migration/tests/test_pi_provider_setup.py`（準備の場所）

**Interfaces:**
- Produces: `pi_launcher_dir <launcher>` — REPLY に `${HOME}/.pi/agent/extensions/subagent.d/create-reso-world/<launcher>` を入れる（標準出力に出さない）。setup の `LAUNCHER_ROOT="${EXT_DIR}/subagent.d/create-reso-world"`、`SUBAGENT_D="${EXT_DIR}/subagent.d"`（照合の拡張の置き場所と旧位置）
- テストの変数: `LAUNCHER_CONFIG_ROOT='.pi/agent/extensions/subagent.d/create-reso-world'`（HOME からの相対）

**テストの要否:** 要る。setup が旧位置（agent-workspace のランチャーの設定）を書き換えると、エラーにならずに往復が戻る（S: 別の対象の上書き）。bind 元の場所は既存の S のテストを新しい位置に直して守る。旧位置を重ねた中での拒否・往復が無いこと・表示は D・L・F なので、一時的な確認で代える（Spec の D8）。

- [ ] **Step 1: 失敗するテストを書く**

`.devcontainer/test-pi-superagents.bash` に `LAUNCHER_CONFIG_ROOT` を足し、既存のテストの `subagent.d/<launcher>` の設定の場所をすべて `${home}/${LAUNCHER_CONFIG_ROOT}/<launcher>` に直す（照合の拡張の `subagent.d/pi-superagents-model-guard.ts` と、`test_missing_model_guard_fails_closed` の agent-workspace の拡張の文字列は変えない）。新しいテストを足して末尾の一覧に登録する。

```bash
# 防ぐ損害: 共有の ~/.pi では、agent-workspace の setup が subagent.d/<launcher>/ に自分のランチャーの設定を書く。
# このリポジトリの setup がそこを書き換えると、エラーにならずに agent-workspace の設定が置き換わり、2 つの setup の
# 往復が戻る（#313）。通常の実行（置き換える方）を代表にする。通る例: 新しい位置にリポジトリの設定が置かれる。
test_setup_leaves_legacy_launcher_configs_untouched() {
    # home="${TEST_ROOT}/setup-legacy"; legacy="${home}/.pi/agent/extensions/subagent.d/pigt"
    # legacy/config.json に agent-workspace の形（extensions は ~/.pi/agent/extensions/subagent.d/pi-superagents-tier-guard.ts、
    #   tier は .devcontainer/pi-superagents/pigt.json と同じ）を置き、cp で写しを取る
    # run_setup "$home" >/dev/null
    # cmp -s 写し legacy/config.json || fail "setup must not rewrite the legacy launcher config"
    # [ "$(find "$legacy" -name 'config.json.bak*' | wc -l)" = 0 ] || fail "setup must not back up the legacy launcher config"
    # cmp -s "${CONFIG_DIR}/pigt.json" "${home}/${LAUNCHER_CONFIG_ROOT}/pigt/config.json" || fail "setup must place the repository config"
}
```

- [ ] **Step 2: テストを実行して失敗を確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash`
Expected: 終了コード 1。最初に失敗するのは、新しい位置に設定を置いた既存のテスト（ヘルパが旧位置を見て「設定が見つかりません」）か、新しいテスト

- [ ] **Step 3: ヘルパを直す**

`pi_launcher_dir` を `pi_agent_directory` の後に定義する。`pi_launcher_require_models` は agent dir を別の変数に取ってから `pi_launcher_dir` を呼び、`"${REPLY}/config.json"` を渡す。`pi_superagents_exec` は関数の先頭で `local REPLY` を宣言して `pi_launcher_dir` から `launcher_dir` を決め、後ろの `local REPLY` の宣言は消す（`pi_agent_directory` の呼び出しは残す）。

- [ ] **Step 4: setup を直す**

- `SUBAGENT_D="${EXT_DIR}/subagent.d"`、`LAUNCHER_ROOT="${SUBAGENT_D}/create-reso-world"`
- 照合の拡張は `${SUBAGENT_D}/pi-superagents-model-guard.ts` に置く（`mkdir -p "${SUBAGENT_D}"`）
- ランチャーの中の拒否は `"${SUBAGENT_D}"/*(N/)` と `"${LAUNCHER_ROOT}"/*(N/)` の両方を見る
- ランチャーの loop で、新しい位置に設定が無くて置くときに `${SUBAGENT_D}/${launcher}/config.json` があれば印を付け、loop の後に 1 回だけ次を表示する（標準出力）

```text
注: ランチャー別の設定は ${LAUNCHER_ROOT}/<launcher>/config.json に置きます（#313）。旧位置の ${SUBAGENT_D}/<launcher>/config.json は、共有の ~/.pi で usaturn/agent-workspace の setup も書くので、読まず、変更もしません。旧位置で tier を編集していた場合は、新しい位置に写してください。
```

- 冒頭の「作成するもの」の説明を新しい位置と理由に直す

- [ ] **Step 5: Python のテストの準備を直す**

`test_pi_vertex_launchers.py` の 2 か所と `test_pi_provider_setup.py` の 1 か所の設定の場所を `.pi/agent/extensions/subagent.d/create-reso-world/<launcher>/config.json` にする（照合の拡張の場所は変えない）。

- [ ] **Step 6: テストを実行して通ることを確かめる**

Run: `bash .devcontainer/test-pi-superagents.bash && uv run pytest tools/devenv_migration/tests/test_pi_vertex_launchers.py tools/devenv_migration/tests/test_pi_provider_setup.py -q`
Expected: `OK test-pi-superagents`、pytest がすべて passed（環境で skip されるものはそのまま）

- [ ] **Step 7: 変異で新しいテストが守りを見ていることを確かめる（コミットしない）**

setup の `LAUNCHER_ROOT` を一時的に `${SUBAGENT_D}` に戻して `bash .devcontainer/test-pi-superagents.bash` を実行し、新しいテストが `setup must not rewrite the legacy launcher config` で失敗することを確かめてから戻す。ヘルパの `pi_launcher_require_models` だけを旧位置に戻したとき `test_unverifiable_or_unsupported_tiers_stop_before_pi` が失敗することも確かめて戻す。結果を ledger に書く

- [ ] **Step 8: 一時的な確認（コミットしない。`SESSION` の下の一時 HOME で行う）**

1. 一時 HOME で setup を実行した後、旧位置の `pigs/config.json` を agent-workspace の形にしても、`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` のヘルパが `bwrap` まで進む（受け入れ基準 3）
2. 旧位置だけがある一時 HOME で、ヘルパが新しい位置の「設定が見つかりません」と setup の案内で終了コード 1（基準 4）。そこで `--if-absent` の setup を実行すると、新しい位置に 13 の設定が置かれ、旧位置のバイト列が変わらず、注意の行が 1 回出る（基準 2・4、Review Focus 4・5）
3. 本物の bwrap で旧位置の `pigs/` を共有の bind 先へ重ねた中で setup を実行し、終了コード が 0 でなく、何も書かない（基準 5、Review Focus 1）

- [ ] **Step 9: Commit**

```bash
git add .devcontainer/pi-superagents-exec.zsh scripts/setup_pi_superagents.zsh .devcontainer/test-pi-superagents.bash \
  tools/devenv_migration/tests/test_pi_vertex_launchers.py tools/devenv_migration/tests/test_pi_provider_setup.py
git commit -m "fix: keep launcher tier configs in a per-repository directory (#313)"
```

### Task 2: 文書と表示を直し、全体を検証する

**Files:**
- Modify: `.devcontainer/README.md`（配置の一覧の 916〜920 行目付近、Plannotator の確認先の 969 行目付近、bind の図の 1486 行目付近、「子 Pi の model の照合」の agent-workspace の段落の 1590 行目付近）
- Modify: `scripts/setup_pi_commandcode_goat.zsh`（357〜358 行目の表示）、`scripts/setup_pi_opencode_go.zsh`（313 行目の表示）

**Interfaces:**
- Consumes: Task 1 の新しい位置と、setup の注意の行

**テストの要否:** 不要。文書と表示の文字列（F）。代わりに `git grep -n 'subagent\.d/'` で、残る旧位置の記述が、照合の拡張・agent-workspace の拡張・旧位置の説明・`docs/maatlog-poc-porting.md`（#17 の記録。変えない）・過去の Spec/Plan だけであることを確かめる。

- [ ] **Step 1: README を直す**

bind の図を新しい位置にし、その直後に、共有の `~/.pi` を usaturn/agent-workspace と使い合い、同じ名前のランチャーの設定を agent-workspace の setup が `subagent.d/<launcher>/` に書くので、このリポジトリの分は `subagent.d/create-reso-world/<launcher>/` に置くこと（#313）と、既存の環境の移行（setup か rebuild で新しい位置に置かれる、旧位置は読まず・変えない、tier を編集していたら写す）を書く。「子 Pi の model の照合」の agent-workspace の段落は、場所を分けたので agent-workspace の setup が置き換えてもこのリポジトリのランチャーは止まらない、という内容に直す。

- [ ] **Step 2: 2 つの setup の表示を新しい位置にする**

- [ ] **Step 3: 旧位置の記述の残りを確かめる**

Run: `git grep -n 'subagent\.d/' -- ':!docs/superpowers'`
Expected: 残るのは照合の拡張（`subagent.d/pi-superagents-model-guard.ts`）、agent-workspace の拡張、旧位置の説明、`docs/maatlog-poc-porting.md` の R-8 だけ

- [ ] **Step 4: Commit**

```bash
git add .devcontainer/README.md scripts/setup_pi_commandcode_goat.zsh scripts/setup_pi_opencode_go.zsh
git commit -m "docs: describe the per-repository launcher config dir (#313)"
```

- [ ] **Step 5: 検証の入口をすべて実行する（統合）**

Run（worktree のルート、ログは `SESSION/verify-<HEAD7>/`）:
`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`
Expected: 3 つとも終了コード 0

- [ ] **Step 6: ブランチ全体のレビュー**

新しいサブエージェント（読み取りだけ）に、base `2fa03f19` から HEAD までの差分、Spec、この Plan の受け入れ基準を渡してレビューを依頼する。指摘は採否を Spec の「全体レビューの判断」に記録し、採用したものを直して Step 5 をやり直す

## 実行予算

- 全体の能動時間: 300 分（#310 の実績は実装 2 時間ほど。今回は場所の変更とテストの調整で Task 2 つ。`--merge` のループの目安はサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 20 分）≒ 195 分を含む）
- phase の目安: 準備・Spec・Plan 40 分、Task 1 45 分、Task 2 と検証 35 分、全体レビュー 20 分、PR とループ 160 分
- worker: 全体レビューのサブエージェントは 1 体（期限 30 分。無進捗の打ち切りは harness の完了通知を待つ）。ループの worker の期限・打ち切りは pr-review-fix-loop の既定に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（既定）。`run-tests.bash` の環境由来の失敗（bwrap が使えないなど）は skip の扱いを確かめ、1 回だけやり直す
- checkpoint: Task 1 の後、Task 2 の後（PR の前）、予算の 50%・100%、ループのサイクルの境界
- 縮小・切り出し・方法変更の候補: 旧位置の注意の表示を外す（README の説明だけにする）、旧位置を重ねた中での setup の拒否を新しい位置だけにして持ち越す

## contingency（代替策）

- ヘルパの `local REPLY` の移動で zsh の挙動が変わる（後ろの `pi_agent_directory` の結果が消えるなど）: `pi_launcher_dir` を呼ぶ前後で別の名前の local に写す形に変える（意味は変えない）
- 本物の bwrap で mount を作れない環境（テストが SKIP する）: 拒否の確認は一時的な確認の 3 で行えないので、PR 本文に未確認として書く
- `tools/devenv_migration/tests/` が新しい位置以外の旧位置の前提を持っていて失敗する: 失敗したテストの準備だけを新しい位置に直す。テストの意味を変える必要があれば止まって報告する
- 全体レビューで C の方針そのものに反する指摘が出た: 方針は Spec の D1 で決めたので変えず、理由を「全体レビューの判断」に書く
