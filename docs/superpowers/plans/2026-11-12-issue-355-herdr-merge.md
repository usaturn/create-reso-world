# Issue #355 herdr-merge 実装 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** issue-to-pr の Herdr ペイン終了状態（`:END`/`:Glitch`）と `--merge` の改良（統合 base 無効化・最終レビュー代替・既存 PR 案内の base 分岐）、loop.py の `--issue-number`/`--issue-repository` を実装する

**Architecture:** loop.py の Herdr 節に start 専用の表示引数 2 つを足し、ペイン名を Issue 起点では `<repo>:#<N>` にする。issue-to-pr SKILL.md の実行ブロック（input/target）と本文に、merge 無効化の記録（`merge-disabled.txt`）とペイン終了状態の規則を足す。テストは fake Herdr・実 Git の fixture で S の項目だけを固定する

**Tech Stack:** Python 3.14 / uv / pytest（loop.py は pydantic・argparse。SKILL.md の bash ブロックは test_base_workflow.py が実 Git で実行）

**Spec:** `docs/superpowers/specs/2026-11-12-issue-355-herdr-merge-design.md`（コミット済み・draft。決定記録 D1〜D10 と設計レビュー 2 回の記録が定義元）

## Global Constraints

- 編集してよいファイルは Spec の「編集範囲と所有」に限る。`loop.py` の reconcile・診断・collect、`finalize.py`、`pr-review`、`issue-to-pr/SKILL.md` の 1 章・4 章 1〜7、`tools/agent_runner`、`.devcontainer/agent-runner.toml`・`.devcontainer/README.md` は触らない
- テストは AGENTS.md の採用基準で S のみ。F（文言写し）・L（気付ける拒否）のテストは書かない。拒否のテストには正しく通る例を残す
- 日本語表現は AGENTS.md に従う（「契約」「原子的」「製品」「着地」「正本」「巡」「席」「実行器」を使わない）
- commit trailer: `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- Python は uv 必須（python3 禁止）。テストの隔離は fixture に従い、実 GitHub・実 Herdr・実 API を使わない
- `--issue-number` は正整数、`--issue-repository` は `owner/repo` 形式で `--issue-number` と一緒。どちらも start 専用で `_add_option_arguments` に入れない
- ペイン名: Issue 起点は `<Issue の repo の repo 部分>:#<Issue番号>`、loop 単独は `PR#<PR番号>`。`--issue-repository` があればそれを、無ければ PR の repo を使う
- `merge-disabled.txt` は input ブロックが `merge` 非 null かつ `base != main` のときに書く。check-options はこのファイルがある run では起動しない

## Review Focus

- クロス repo（Issue と PR の repo が異なる）で `--issue-repository` を渡したとき、ペイン名が PR の repo から再導出されず開始時の Issue 識別を保つこと（Task 1 のテストが固定）
- `--issue-number 0`・形式違反の `--issue-repository` がロック取得前に拒否され、ロック・run・herdr 呼び出しが残らないこと（Task 1）
- 統合 base + `--merge` で `merge-disabled.txt` が input ブロック時点で存在し、PR 作成まで進むこと。既定 base + `--merge` ではできないこと（Task 2）
- rename 失敗・Herdr ハングでも start が戻り、失敗が `herdr_pane.state=failed` と warnings に残ること（Task 1・既存ハングテスト）
- SKILL.md の bash ブロック変更後も `test_base_workflow.py` の既存ケース（pinned SHA・scan・PR 照合・GIT_* 隔離）が通ること（Task 2・3 の検証）

## 受け入れ基準

- **動作環境**: Dev Container（Ubuntu 26.04）・uv・pytest。テストは fixture が一時 HOME・GIT_* を隔離し、fake の gh・herdr・git を使う。実 GitHub・実 Herdr・実モデルは使わない
- **実入力**:
  - `loop.py start "#900" --controller-model <ID> --controller-runtime claude-code --issue-number 355 --issue-repository usaturn/create-reso-world`（fixture の PR は usaturn/create-reso-world#900）
  - `--issue-number 0` / `--issue-number -1` / `--issue-number abc`（argparse）/ `--issue-repository no-slash` / `--issue-number` なしの `--issue-repository usaturn/create-reso-world`
  - `check-options --issue-number 355` / `check-options --issue-repository usaturn/create-reso-world`
  - INPUT `--base=統合/プラグイン #42 --merge`（非 ASCII の branch 名）と `#42 --merge`（既定 base）
- **防御範囲**: 別 pane を操作しない・無効値はロック前に拒否・check-options は新引数を拒否・統合 base はループ設定に依存せず続行・クロス repo で Issue 識別を保持。対象外の反例: loop 単独起動は `PR#<番号>` を維持、既定 base の `--merge` は従来どおり適用、`--issue-number` のみの呼び出しは PR の repo にフォールバック（AW 互換）

## 実行方式

- superpowers:subagent-driven-development の形で、Task を 1 つずつ `implement_task.py run`（担当 `pi_alibaba_qwen4-max_max`）に依頼する。並行しない。runner 起動は `with_keys.py` 経由 + `MAAS_ANTHROPIC_TOKEN="${ANTHROPIC_AUTH_TOKEN:?}"` の環境前置
- 作業領域: `tmp/agents/issue-355.puoplwnc/sdd/2026-11-12-issue-355-herdr-merge/`（ledger・brief・報告・review package）。`sdd-workspace`・`task-start`・`task-done` は使わない
- Task レビューは司令塔が行う（diff の精読・関連テストの同期実行・受け入れ基準との照合）。実装担当の自己レビューで代えない
- 最後のブランチ全体レビューは現行スキルに従い行う（この run は変更前のスキルで動く。新設の 4 章 8 はマージ後の run から効く）。最も能力の高いモデルのサブエージェントに依頼する
- この run のループは親 checkout の変更前 `loop.py` を使うため、`--issue-number`・`--issue-repository` は渡さない（設計レビュー 2 回目 D1）。ループ中のペイン名は `PR#<番号>`。マージ成功の確認後に、司令塔が新設の 3 章の規則に従い `create-reso-world:#355:END` へ手動で更新する（導入 run 限りの適用）
- 共有条件の統合確認: ペイン名のラベル形式（Task 1 の loop.py と Task 3 の issue-to-pr 3 章）と `merge-disabled.txt` の記録・消費（Task 2 の input ブロックと 5 章）は、Task 3 のレビューと最終全体レビューで条件単位に照合する

## 実行予算

- Issue 全体の能動時間: 300 分（ledger 開始済み。根拠: 設計・レビュー 60 分、Plan 30 分、実装の司令塔 90 分、検証・PR 30 分、ループの司令塔 90 分。ループの壁時計はサイクル上限 3 ×（レビュー 45 分＋計画・修正）で能動時間には加算しない）
- worker の期限: implement 5400 秒/Task（role 既定）、inspect 2700 秒、design/spec-review 1800 秒。無進捗の打ち切りは runner の期限管理に任せる（事前宣言の独自停止はしない）
- 再試行の上限: 同じ失敗は 1 回まで（既定）。Task の `retry` verdict は 2 回まで文脈を足して再依頼し、上限で方法変更を裁定する（利用者の「停止せず最適な案」委任の範囲で、記録して続行）
- checkpoint: phase の境界・予算 50%/100%・worker 失敗直後。ledger は `tmp/agents/issue-355.puoplwnc/budget.jsonl`
- 縮小・切り出し・方法変更の候補: レビュー担当の連続失敗時は担当を self に切り替える（記録する）。実装の連続失敗時は司令塔が inline で実装する（記録する）。main が進んだら再捕捉・rebase・再検証で追随する（run 限りの委任）

## contingency（代替策）

- piaq（pi_alibaba_qwen4-max_max）が `response_failed`（JSON 前の説明文）を返したら: cleanup の前に stdout.log の末尾を確認し、結果 JSON があれば其原因を記録する。成功扱いにはせず、同じ担当に「結果は JSON のみ・code fence 可・説明文を付けない」の文脈を足して 1 回再依頼する。それでも失敗したら担当を self に切り替えて司令塔がレビューする（裁定を ledger に記録）
- 検証の失敗: systematic-debugging で調べ、最小修正を runner 依頼または裁定で入れる。仕様の意味が変わる場合は利用者の委任（最適な案を出して続行）の範囲で最小の仕様維持案を選び記録する
- main の前進: recheck_bases が移動を観測したら、新 SHA を再捕捉 → feature branch を rebase → 関連テストを再実行 → 記録を更新して続行する（push 前の scan と PR 照合は省略しない）
- ループの全レビュアー失敗: 1 回だけ再試行し、それでも失敗したら司令塔の自己レビューで review-fix-planning の結論 2 の手順を行い finalize する（裁定を記録）

## Task 1: loop.py の --issue-number / --issue-repository とペイン名

**Files:**
- Modify: `.agents/skills/pr-review-fix-loop/scripts/loop.py`（Herdr 節 `rename_pane`・`start`・`dispatch`・CLI の start 引数）
- Modify: `.agents/skills/pr-review-fix-loop/SKILL.md`（起動節の `--issue-number`・`--issue-repository`・Herdr の項・check-options の項）
- Test: `.agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py`・`tests/test_loop_check_options.py`

**Interfaces:**
- Produces: `rename_pane(number: int, *, repository: str, issue_number: int | None = None, issue_repository: str | None = None) -> HerdrPane`。`start(..., issue_number: int | None = None, issue_repository: str | None = None)`。Task 3 が issue-to-pr 5 章の起動引数としてこの 2 引数を参照する
- Consumes: 既存の `HerdrPane`（state/pane_id/label/reason）・`LoopError(code, stage, reason)`・fixture の `env.start(**options)`・`no_herdr` autouse fixture

**テストの要否**: S（誤ったペイン対象の操作・Issue 識別の上書き・無効値の黙認・ロック残留・失敗の成功報告は気付きにくい損害）。非整数の argparse 拒否は L なので書かない

- [ ] **Step 1: 失敗するテストを書く**（test_loop_herdr_pane.py）

fake herdr（呼び出し argv を JSONL に記録して exit 0）を PATH 先頭に置く fixture を足す。テスト:
- `test_start_without_issue_number_renames_current_pane_to_pr_label`: `env.start()` → `herdr_pane.state == "renamed"`、`label == "PR#900"`、fake の記録は 1 行だけで `["pane","rename","w1:p9","PR#900"]`（HERDR_PANE_ID は fixture で設定）、run.json の herdr_pane が同じ
- `test_start_with_issue_number_uses_issue_label`: `env.start(issue_number=355)` → `label == "create-reso-world:#355"`、呼び出しは現在の pane への 1 回だけ
- `test_start_with_issue_repository_keeps_issue_repo_label`: `env.start(issue_number=355, issue_repository="other-owner/other-repo")` → `label == "other-repo:#355"`（PR の repo から再導出しない）
- `test_start_rejects_non_positive_issue_number_before_lock`: `env.start(issue_number=0)` が `LoopError`（code 2・stage arguments）を送出（`pytest.raises`）、lock.json が無い・run_dir が無い・fake の記録が空。`-1` も同様に 1 件（parametrize）
- `test_start_rejects_invalid_issue_repository`: `issue_repository="no-slash"`（issue_number 付き）と `issue_repository="other-owner/other-repo"`（issue_number なし）が code 2・arguments、ロック・run・herdr 呼び出し無し
- `test_start_succeeds_when_rename_fails`: fake が exit 1 → start は ok、`herdr_pane.state == "failed"`・`reason` 非空・warnings に rename 失敗を含む
- 既存の `test_start_succeeds_when_herdr_hangs` は変更しない

test_loop_check_options.py に `test_check_options_rejects_issue_context_options`: `loop.main(["check-options", "--issue-number", "355", "--template", str(isolated.template)])` と `--issue-repository usaturn/create-reso-world` のそれぞれが `SystemExit`（`exc.value.code == 2`、argparse の拒否）を送出し、`assert_untouched(isolated)` を満たす（`pytest.raises(SystemExit)` で受ける。既存の `check_options` ヘルパーは argparse 拒否では使えない）

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py .agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py -q`
Expected: 新テストが FAIL（`start()` が `issue_number` を受け付けない・check-options が新引数を受け付ける）

- [ ] **Step 3: 実装**

- `rename_pane` のシグネチャとラベル: `label = f"{(issue_repository or repository).rsplit('/', 1)[-1]}:#{issue_number}" if issue_number is not None else f"PR#{number}"`。docstring を更新
- `start` に `issue_number`・`issue_repository` を追加。先頭の検証（controller 検証の直後・check_options の前）で: `issue_number is not None and issue_number < 1` → `LoopError(2, "arguments", "--issue-number は正整数にする")`。`issue_repository is not None` のとき `issue_number is None` なら `LoopError(2, "arguments", "--issue-repository は --issue-number と一緒に渡す")`。形式は `owner/repo`（`/` ちょうど 1 つ・両側非空）違反で `LoopError(2, "arguments", "--issue-repository は owner/repo 形式にする")`
- 呼び出し: `pane = rename_pane(pr.number, repository=pr.repository, issue_number=issue_number, issue_repository=issue_repository)`
- `dispatch` の start に `issue_number=args.issue_number, issue_repository=args.issue_repository`
- CLI: `begin.add_argument("--issue-number", type=int, help=...)`・`begin.add_argument("--issue-repository", help=...)`（`_add_option_arguments` には入れない）
- SKILL.md 起動節: Spec D7 のとおり（2 引数の説明・Herdr の項の書き換え・check-options が受け付けない旨）

- [ ] **Step 4: テストが通ることを確認**

Run: Step 2 と同じ + `uv run pytest .agents/skills/pr-review-fix-loop/tests -q`（退行）
Expected: すべて PASS

- [ ] **Step 5: commit**

```bash
git add .agents/skills/pr-review-fix-loop/scripts/loop.py .agents/skills/pr-review-fix-loop/SKILL.md .agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py .agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py
git commit -m "feat(pr-review-fix-loop): start --issue-number/--issue-repository for issue pane identity

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## Task 2: --merge の統合 base 無効化（input ブロックの記録とテスト）

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（2 章 3 の input ブロック・check-options 呼出条件、2 章 5 の target ブロック・本文、5 章のループ節冒頭）
- Test: `.agents/skills/issue-to-pr/tests/test_base_workflow.py`

**Interfaces:**
- Produces: `$SESSION/merge-disabled.txt`（理由 1 行）。Task 3 の 5 章本文がこのファイル名を参照する
- Consumes: `issue.json` の `merge`・`base`（resolve_issue.py の既存出力。変更しない）

**テストの要否**: S（統合 base でループがマージと Issue close まで進む損害・何でも無効化する退行は気付きにくい）

- [ ] **Step 1: 失敗するテストを書く**

`test_documented_flow_pins_worktree_diff_scan_and_pr` の parametrize に `(False, "#42 --merge", "main")` を足す。同テスト内に:
- `base != "main"` かつ `"--merge" in argument` のとき: `(workflow.session / "merge-disabled.txt").exists()` が True・内容に「main」以外の base 名と理由（ループと finalize.py が既定 branch へのマージと Issue の close を前提にすること）を含む
- `base == "main"` かつ `"--merge" in argument` のとき: `merge-disabled.txt` が存在しない
- 共通: `issue.json` の `merge` は `"--merge" in argument` なら非 null（既存の assert を維持）

input ブロックの直後（target の前）でファイルが存在することを確かめるため、`Workflow.run` に `before_target: str = ""` 引数を足し、chunks の `step("input")` と `step("target")` の間に挿入する。統合 base + --merge のケースでは `before_target='test -f "$SESSION/merge-disabled.txt"'` を渡す（input ブロックが書いたことを target の前で固定する）。

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest .agents/skills/issue-to-pr/tests/test_base_workflow.py -q`
Expected: 統合 base + --merge のケースが FAIL（merge-disabled.txt が無い）

- [ ] **Step 3: SKILL.md を実装**

- input ブロック（`base-workflow:input`）の resolve_issue の後に足す:
```bash
if [ "$(jq -r '.merge != null' "$SESSION/issue.json")" = true ]; then
  merge_base="$(jq -r .base "$SESSION/issue.json")" || exit 2
  if [ "$merge_base" != main ]; then
    printf '%s\n' "BASE が統合用 branch（${merge_base}）のため --merge を適用しない。ループと finalize.py は既定 branch（main）へのマージと Issue の close を前提にする" > "$SESSION/merge-disabled.txt" || exit 2
  fi
fi
```
- 2 章 3 の本文: check-options の呼出を「`merge` が非 null で、かつ `merge-disabled.txt` が無いときだけ」にし、無効化された run は理由を利用者に伝えて `--merge` なしとして続けることを書く
- 2 章 5 の本文: Spec D4 の規則を書く。target ブロックの手動マージ拒否を `if [ "$merge_requested" = true ] && [ ! -f "$SESSION/merge-disabled.txt" ]; then` で包む
- 5 章の「`--merge` のとき: PR の作成後のループ」冒頭: `merge-disabled.txt` がある run はループを始めない（Spec D4）

- [ ] **Step 4: テストが通ることを確認**

Run: Step 2 と同じ
Expected: すべて PASS（既存ケース含む）

- [ ] **Step 5: commit**

```bash
git add .agents/skills/issue-to-pr/SKILL.md .agents/skills/issue-to-pr/tests/test_base_workflow.py
git commit -m "feat(issue-to-pr): disable --merge on integration base before loop checks

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## Task 3: Herdr 終了状態・4 章 8・案内の base 分岐・README

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（3 章・4 章 8 と runner 節の 1 文・2 章 6 の既存 open PR 案内・5 章の完了報告と起動引数）
- Modify: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`（LOOP_OPTIONS 近くのコメントのみ）
- Modify: `README.md`（「エージェントで作業する」の issue-to-pr 項への注記）

**Interfaces:**
- Consumes: Task 1 の `--issue-number`・`--issue-repository`（5 章のループ起動引数に書く）。Task 2 の `merge-disabled.txt`（5 章のループ節冒頭は Task 2 で追加済み）
- Produces: `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL` の保持と `:END`/`:Glitch` の規則（この run の完了時にも司令塔が手動で適用する）

**テストの要否**: 不要（SKILL.md の文言は F。resolve_issue.py はコメントのみで挙動変化なし）。代わりの検証: check-layout.sh・issue-to-pr と pr-review-fix-loop の全テスト（ブロック抽出・contract の退行確認）・diff の精読・受け入れ条件との照合

- [ ] **Step 1: 3 章を書き換える**

開始時の rename を `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL`（`<Issue の repo の repo 部分>:#<N>`）の保持に変える。CRW の「pane 不明・rename 失敗は省いて続け最終報告に書く」を維持。「ペイン名の終了状態（Issue 起点の run だけ）」の節（表・予期しない障害/想定された停止の分類・Glitch 優先・失敗時報告・別 pane を探さない）を Spec D2 のとおり足す

- [ ] **Step 2: 4 章 8 と runner 節・2 章 6・5 章を書く**

- 4 章に項目 8 を**項目 5 の例外として**書く（Spec D3・Spec レビュー S1）。冒頭は「項目 5 の例外として、`--merge` が適用される run は、実装スキルの最終のブランチ全体レビュー（全 Task の後のブランチ全体のレビュー）を行わず、ループの 1 サイクル目で代える」。**項目 5 自体は編集しない**。runner 節の「すべての Task を取り込めたときの最後の全体レビューと PR は、self のときと同じ」は self・runner 両経路で項目 8 を指す形に書き換える（例:「すべての Task を取り込めたときの最後の全体レビューは 4 章 8 に従い、PR は self のときと同じ」）
- 2 章 6 の既存 open PR 案内を base で分ける（Spec D5）
- 5 章: ループの start に `--issue-number N --issue-repository <Issue の repo>` を渡すことを書く。項目 1 の「ペインの名前は start が PR#<番号> に変えるので、自分で変えない」を「ペインの名前は start が 3 章・起動節の規則どおりのラベル（Issue 起点は <repo>:#<N>、単独起動は PR#<番号>）に改名するので、自分で変えない」に書き換える（Spec レビュー S3）。完了報告にペイン名の更新結果を含める。「`--merge` のとき」は適用された run を指すことを明確にする

- [ ] **Step 3: resolve_issue.py のコメントと README**

- `LOOP_OPTIONS` の近くに「`--issue-number`・`--issue-repository` は issue-to-pr の入力オプションではなく、loop.py の start に司令塔が渡す表示用の別引数。loop_args には入れない」のコメント
- README.md の issue-to-pr 項にペイン名の変更（`Issue#<N>` → `<repo>:#<N>`、#355）と `:END`/`:Glitch` の 1〜2 文

- [ ] **Step 4: 検証**

Run: `bash scripts/check-layout.sh` と `uv run pytest .agents/skills/issue-to-pr/tests .agents/skills/pr-review-fix-loop/tests -q`
Expected: すべて PASS・check-layout ok

- [ ] **Step 5: commit**

```bash
git add .agents/skills/issue-to-pr/SKILL.md .agents/skills/issue-to-pr/scripts/resolve_issue.py README.md
git commit -m "feat(issue-to-pr): herdr pane end states and --merge review guidance

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## 検証（全体・PR 前）

- `uv run pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/issue-to-pr/tests -q`
- `bash scripts/check-layout.sh`
- 手動 fake Herdr: start（--issue-number あり/なし）・rename 失敗のペイン名を fake herdr で確認（マージ成功・障害・通常停止の :END/:Glitch はスキルの規則なので、fake 環境での rename コマンドの組み立てを確認する）
- 実行確認（L）: `resolve_issue.py -- '#355 --merge --issue-number 1'` が終了コード 2、`loop.py start --issue-number abc` が usage で 2、`check-options --issue-number 1` が 2
- 検証の記録（--merge 用）: HEAD・status が空・各コマンドの argv と終了コード・ログの完全パスを SESSION に記録し、finalize.py の --checks-file の形にする

## 完了の条件

- 受け入れ条件 1〜9 がすべて満たされ、統合確認（ラベル形式・merge-disabled の記録と消費）が条件単位で照合されている
- 最後のブランチ全体レビューが clean（または裁定済み）
- PR が作成され、ループ（--merge）がマージと関連 Issue の更新まで完了する
- PR 本文に既知の不整合（records.md の herdr_pane 節は #356・#357 の所有のためこの PR では更新しない）を明記する（Spec レビュー S2）