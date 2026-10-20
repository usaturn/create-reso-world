# Issue #135: push の前の Gitleaks の誤検出を減らし、止まったときの扱いを決める Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** resoloop の識別子では push の前の検査が止まらず、テスト用の偽の値などで止まったときは、エージェントがこの作業の未 push の commit を直して続けられるようにする。秘密情報の検出は弱めない。

**Architecture:** `.gitleaks.toml` に、値が resoloop の識別子の形のときだけ `generic-api-key` から外す 3 つ目の除外を足す。`AGENTS.md` に直してよい条件を書き、`issue-to-pr`・`review-fix-planning` の SKILL.md をそれに合わせる。`test_meshy.py` の偽の値を実行時に組み立てる。

**Tech Stack:** gitleaks 8.30.1（Go の RE2）、bash 5.2、Python（uv）

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue135-gitleaks-false-positives-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/135
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-135-gitleaks-false-positives`（branch `fix/issue-135-gitleaks-false-positives`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: Spec の「管理・実行許可」と同じ（`/issue-to-pr #135 --merge`）
- 実行方式: inline（`superpowers:executing-plans`）。振る舞いの比較だけ Agent ツールのサブエージェントを使う。理由は Spec の D-135-6
- セッションディレクトリ（ledger・検証のログ・評価の回答。commit しない）: `/workspaces/reso-world/tmp/agents/issue-135.0p5yz3oi/`

## Global Constraints

- 3 つ目の除外の正規表現は Spec の 1 の文字列そのまま。`targetRules = ["generic-api-key"]`、`regexTarget = "secret"`。既存の 2 つの除外は変えない
- この PR で足す行（テスト・文書・SKILL.md・評価）に、今の base の設定（`origin/main` の `.gitleaks.toml`）で止まる形の値を書かない。テストの値は実行時に組み立て、文書では `<16 進 8 桁>` のように置き換える。各 commit の後に `bash /workspaces/reso-world/scripts/scan-before-push.sh -C .` で確かめる
- `scripts/scan-before-push.sh` は変えない
- 直してよい条件は Spec の 2 の 2 項目（この作業の未 push の commit、値の出どころ）。どちらかを満たさなければ止まる

## Review Focus

- 識別子の形に見えて、塊の中に無作為な英数字を含む値（`<接頭辞>_<無作為>_<16 進 8 桁>`）を除外しないこと。Task 1 の負の例と実際の検査で確かめる
- `regexTarget = "secret"` が、gitleaks の `Secret`（引用符の内側）全体に対して判定されること（Python の `re` の結果と RE2 の結果がずれない）。Task 1 の実際の検査で確かめる
- 既存の 2 つの除外（マニフェストの `"key"`・偽のトークン）が、3 つ目を足した後も同じに働くこと。`test-ci.bash` の既存の例が通ることで確かめる
- 直してよい条件の「値の出どころ」を、エージェントが「偽の値に見える」で代えないこと。評価の (gb) で確かめる
- 既に push した commit の行を直すために、履歴の書き換え・force push をしないこと。評価の (gc) で確かめる

## 要件と Task・検証の対応

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 1 識別子の commit で止まらない | Task 1 | 実際の検査が成功し HEAD の SHA を出す | `test-scan-before-push.bash` の追加の場合 |
| 2 トークン・無作為な値では止まる | Task 1 | 実際の検査が検出で止まる | `test-scan-before-push.bash` の追加の場合、`test-ci.bash` の負の例 |
| 3 止まったときの手順と、スキルとの整合 | Task 3 | `AGENTS.md`・2 つの SKILL.md の文面、評価の回答 | 振る舞いの比較 (ga)〜(gd) |
| 4 履歴の全体の検出 | Task 4 | 検出が `placement_key` と偽の値だけ、`d2d0533` は 0 件 | gitleaks の全体の走査（ログはセッションディレクトリ） |
| 5 `test_meshy.py` | Task 2 | 同じ値で、テストが通る | `uv run pytest tests/scripts/test_meshy.py` |
| 6 この PR が今の base の検査を通る | 全 Task（Task 4 で最終確認） | `scan-before-push.sh` が SHA を出す | 各 commit の後と push の前 |
| 7 入口のテスト | Task 4 | 基準と同じ PASS | `README.md` の「テスト」の 3 つ |

共有する前提は 2 つ（3 つ目の除外の正規表現、今の base の設定で止まる値を足さないこと）。Task 1 が正規表現を決め、Task 3 の文書は正規表現を書き写さず `.gitleaks.toml` を参照する。今の base の設定での検査は Task 4 が統合して確かめる。

## 実行予算

`.agents/execution-budget.md` に従う。ledger は `/workspaces/reso-world/tmp/agents/issue-135.0p5yz3oi/budget.jsonl`（2026-10-20 14:37Z に `start`、予算 400 分）。

1. 全体の能動時間: 400 分。根拠: #158（スキルの変更と評価、ループ 1 サイクル）が 360 分。#135 は設定・テスト・文書とスキル 2 つの評価に、ループ（上限 3 サイクル、1 サイクル 45 分のレビューと計画・修正）が加わる
2. phase の目安: 準備（読み・Spec・Plan）60 分 / Task 1 40 分 / Task 2 10 分 / Task 3 70 分 / Task 4（統合・全体レビュー・PR）60 分 / ループ 150 分 / 予備 10 分
3. worker: 評価のサブエージェント（Agent ツール）は 1 回 15 分を見込み、30 分で回答が無ければ stall として記録する（Agent ツールは task_watch で止められないので、宣言による打ち切りはしない）。検証のコマンド（`run-tests.bash`・pytest・履歴の走査）は `run_in_background` の完了通知で待ち、10 分ごとにログの mtime を確かめる。ループは pr-review-fix-loop の SKILL.md の監視に従う
4. 再試行の上限: 同じ失敗の再試行は 1 回まで（評価のサブエージェントの無回答、検証の一時的な失敗）。安全の失敗（秘密情報の検出が本物の疑い）は再試行せず止まる
5. checkpoint: 各 Task の境界、予算の 50%（200 分）と 100%（400 分）、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: 評価の回数を各 2 回にする / 比較で外れた場面の文面の直しを 1 回に限り、残りは PR の既知の制限に書く / `review-fix-planning` の変更を外して別 Issue の候補にする（その場合は `AGENTS.md` に「スキルが止まると定める手順はそれに従う」を書く）

## contingency

- 3 つ目の除外が、この PR の検査（今の base の設定）に影響することは無い（base の設定を使うので）。この PR の行が今の設定で止まったら、Global Constraints のとおり値を組み立て直す
- 振る舞いの比較で、変更の後の版が期待を外したら、文面を 1 回だけ直して同じ場面を再評価する。再評価でも外れたら、外れた場面と回答を PR の既知の制限に書く

### Task 1: 3 つ目の除外と、その検査

**Files:**
- Modify: `.gitleaks.toml`（末尾に `[[allowlists]]` を足し、先頭のコメントを 3 つの除外の説明にする）
- Modify: `tests/scripts/test-ci.bash`（除外の数・3 つ目の属性・正負の例）
- Modify: `tests/scripts/test-scan-before-push.bash`（「成功する」と「検出して止まる」の節に、リポジトリの設定での場合）
- Modify: `.devcontainer/README.md:128`（除外の説明）

**テストの要否:** 書く。除外の正規表現（安全条件）と実際の gitleaks の判定を、コードを実行して確かめる（Spec の D-135-4）。

**Interfaces:**
- Produces: `.gitleaks.toml` の 3 つ目の除外（`regexTarget = "secret"`）。`test-ci.bash` は、`regexTarget = "secret"` の除外のうち偽のトークンに当たるものを偽のトークンの除外、当たらないものを識別子の除外として見分ける

- [ ] **Step 1: `test-ci.bash` に失敗するテストを書く**

`assert len(allowlists) == 3`。偽のトークンの除外は `next(a for a in allowlists if a["regexTarget"] == "secret" and re.search(a["regexes"][0], fake_token))`、識別子の除外は残りの `regexTarget == "secret"` の 1 つで、`targetRules == ["generic-api-key"]` と正規表現が 1 つであることを確かめる。

- 正の例（`re.search` が当たる）: 接頭辞 `mat`・`ul_mat`・`pbr_mat`・`mesh` に、`material`・`Slum02`・`rubber`・`NeonSign`・`LOD0`・`001`・`-`・`__`・入れ子の 16 進 8 桁を組み合わせ、末尾を `_` と 16 進 8 桁にした識別子
- 負の例（当たらない）: 区切りの無い無作為な値（`fake_token[::-1]`）、`"msy_" + fake_token`、塊に無作為な英数字を含む `mat_material_<fake_token の一部>_<16 進 8 桁>`、16 進 8 桁で終わらない `mat_material_x`、16 進が大文字の末尾、`ghp_` で始まる値
- 正の例は文字列の連結（`"_".join(...)`）で組み立て、行に識別子そのものを書かない（Global Constraints）

- [ ] **Step 2: 失敗を確かめる**

Run: `bash tests/scripts/test-ci.bash`
Expected: `assert len(allowlists) == 3` で失敗する

- [ ] **Step 3: `test-scan-before-push.bash` に、リポジトリの設定での場合を書く**

`new_repo "$root/.gitleaks.toml"` で base にリポジトリの設定を置く。値はすべて実行時に組み立てる（識別子は `printf` で、無作為な値は既存の `$token` と同じく `sha256sum` から作り、`base64` で英字の大小と数字を混ぜる）。

- 止まる（`expect_leak`）: `api_key = "<区切りの無い無作為な値>"`、`api_key = "msy_<無作為>"`、`api_key = "mat_material_<無作為>_<16 進 8 桁>"`、`token = "$token"`（`ghp_`）。それぞれ 1 つの `new_repo` で
- 通る（`expect_success`）: 1 つの `new_repo` で、`key = '<識別子>'`（Python）、`KeyError: '<識別子>'`、`"mesh_key": "<識別子>"`（JSON）、入れ子の `pbr_mat_..._<16 進 8 桁>_<16 進 8 桁>` を 1 つのファイルに書いた commit

- [ ] **Step 4: 失敗を確かめる**

Run: `bash tests/scripts/test-scan-before-push.bash`
Expected: 通る場合の `expect_success` で失敗する（今の設定では識別子で止まる）

- [ ] **Step 5: `.gitleaks.toml` に 3 つ目の除外を足す**

`description` に、resoloop の `key()` が作る形であること、塊に英字と数字が入り混じる値（無作為な値）は除外しないこと、を英語で書く。先頭のコメントを、3 つの除外（マニフェストの `"key"`、識別子の値、偽のトークン）の説明にする。`.devcontainer/README.md` の「resoloop のマニフェストが持つ識別子の除外」を「resoloop の識別子の除外」にする。

- [ ] **Step 6: テストが通ることを確かめる**

Run: `bash tests/scripts/test-ci.bash && bash tests/scripts/test-scan-before-push.bash`
Expected: 2 つとも PASS

- [ ] **Step 7: Commit と検査**

```bash
git add .gitleaks.toml tests/scripts/test-ci.bash tests/scripts/test-scan-before-push.bash .devcontainer/README.md
git commit -m "fix: allow resoloop identifiers in the gitleaks generic rule (#135)"
bash /workspaces/reso-world/scripts/scan-before-push.sh -C .
```

Expected: 検査が SHA を出す（今の base の設定で止まらない）

### Task 2: `test_meshy.py` の偽の値を実行時に組み立てる

**Files:**
- Modify: `tests/scripts/test_meshy.py:20`

**テストの要否:** 足さない。値は変えず組み立て方だけを変えるので、既存のテストが通ることで確かめる。

- [ ] **Step 1: `KEY` を `"_".join(("msy", "test", "secret", "sentinel", "123456"))` にする**

上に 1 行、検査に当たらないよう実行時に組み立てる理由（`tests/scripts/test-ci.bash` と同じ考え方）をコメントで書く。

- [ ] **Step 2: テストを実行する**

Run: `uv run pytest -q -p no:cacheprovider tests/scripts/test_meshy.py`
Expected: 変更の前と同じ件数が PASS

- [ ] **Step 3: Commit と検査**

`git commit -m "test: build the fake Meshy key at run time (#135)"` の後、`scan-before-push.sh -C .` が SHA を出す

### Task 3: 止まったときの手順（`AGENTS.md`・SKILL.md）と振る舞いの比較

**Files:**
- Modify: `AGENTS.md`（「push の前の秘密情報の検査」の 3 つ目の項目）
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（「停止時の報告」の停止条件と「検査で止まったら」の段落）
- Modify: `.agents/skills/review-fix-planning/SKILL.md`（「実装後」の手順 5 の 1 文目）
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`（(ga)〜(gd) を足し、(m) の `added` に #135 で期待が (ga) に変わったことを書く）
- Modify: `.agents/skills/issue-to-pr/evals/validation.md`（#135 の節）

**テストの要否:** 書かない（文書と SKILL.md の文面の変更。`AGENTS.md` のテストの採用基準）。代わりに `superpowers:writing-skills` の振る舞いの比較（RED → GREEN）を行う。

- [ ] **Step 1: `superpowers:writing-skills` を読み、評価の指示文を作る**

シナリオは Spec の 5 の (ga)〜(gd)。共通の状況は `scenarios.json` の `context` と (k) の共通の状況（push・PR の作成の直前、gitleaks は固定の版）。各シナリオで、次の操作・push する branch・作る PR・利用者への報告を答えさせる。ツールは指定のファイルの Read だけ。指示文と回答はセッションディレクトリの `evals/` に置く。

- [ ] **Step 2: RED（変更の前）**

`origin/main`（`f2350a4`）の `AGENTS.md`・`issue-to-pr/SKILL.md`・`review-fix-planning/SKILL.md` を scratchpad に置き、Agent ツール（model `sonnet`）の新しいサブエージェントに 3 回答えさせる。期待を外した点を記録する（(ga)・(gd) で止まる、が予想）。

- [ ] **Step 3: 文面を変える**

`AGENTS.md`: 今の 3 つ目の項目（「検出や失敗で止まったら push しない。…」）を、(1) 止まったら push しない・回避の仕組みを使わない、(2) Spec の 2 の 2 条件を満たす誤検出なら commit を直してよい（直し方・分割や符号化の禁止・検証のやり直し・報告に書くこと）、(3) それ以外は利用者に報告し、除外が要るなら base の `.gitleaks.toml` を先に変える、の 3 項目にする。

`issue-to-pr`: 停止条件を「push の前の検査の検出（`AGENTS.md` の条件で直せるものを除く）・失敗」にし、「誤検出に見えても `AGENTS.md` のとおり回避しない」を「`AGENTS.md` の条件を満たす誤検出なら、その commit を直し、検証（`--merge` のときは検証の記録も）と、公開するすべての worktree の検査をやり直して続ける。それ以外は止まり、回避しない」にする。

`review-fix-planning`: 手順 5 の「検出や検査の失敗で止まったら push せずに停止して報告する（完遂では結論 3）」を「検出や検査の失敗で止まったら push しない。`AGENTS.md` の条件を満たす誤検出なら、その commit を直して手順 1 からやり直す。それ以外は停止して報告する（完遂では結論 3）」にする。

- [ ] **Step 4: GREEN（変更の後）**

変えた 3 ファイルで Step 2 と同じ指示文を 3 回答えさせる。外れたら contingency のとおり 1 回だけ直して再評価する。

- [ ] **Step 5: 記録**

`scenarios.json` に (ga)〜(gd)、`validation.md` に #135 の節（評価方法と範囲、結果の表、行っていない確認）を書く。シナリオの値は書かず、「偽の API キーの例」のように書く。

- [ ] **Step 6: 構文の確認・Commit と検査**

Run: `uv run --no-project python -c "import json; json.load(open('.agents/skills/issue-to-pr/evals/scenarios.json'))"`、`bash tests/scripts/test-instructions.bash`、`bash tests/scripts/test-docs.bash`
Expected: どれも成功

`git commit -m "docs: let agents fix their own unpushed false positives (#135)"` の後、`scan-before-push.sh -C .` が SHA を出す

### Task 4: 統合確認

**Files:** この Plan の「検証の記録」

**テストの要否:** 足さない。この Task が検証そのもの。

- [ ] **Step 1: 履歴の全体の走査**

`main` の HEAD の履歴を、作業ツリーの `.gitleaks.toml` で `gitleaks git --report-format json` で走査し、変更の前（56 件）と比べる。`d2d0533^..d2d0533` も走査する。
Expected: 55 件（`slum03/artifacts/` の `placement_key` 54 件と `test_meshy.py` の偽の値 1 件）。`d2d0533` は 0 件

- [ ] **Step 2: ブランチ全体のレビュー**

新しいコンテキストのレビュアー（Agent ツール、model `opus`）に、Spec・Plan と `origin/main...HEAD` の差分を渡す。致命的な指摘は直し、関係するテストをやり直す。

- [ ] **Step 3: 記録して commit**

下の「検証の記録」に、Step 1・2 の結果、Task 1〜3 の検証、所要時間を書き、commit する。入口のテストは、この commit（最後の commit）で Step 4 に実行し、結果は PR 本文とセッションディレクトリの検証の記録に書く（この記録の commit の後に実行するため）。

- [ ] **Step 4: 最後の commit での入口のテストと検査**

Run（worktree のルート）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest -q -p no:cacheprovider tests/skills .agents/skills .agents/scripts tools`
Expected: すべて終了コード 0。`--merge` の検証の記録（HEAD・`git status --porcelain` が空・argv・終了コード・ログのパス・`--checks-file` の形のファイル）をセッションディレクトリに作り、`scan-before-push.sh -C .` が SHA を出すことを確かめる

## 検証の記録

（Task 4 で書く）
