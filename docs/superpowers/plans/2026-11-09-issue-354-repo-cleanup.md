# Issue #354 Repo Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Implementation tasks are dispatched sequentially with issue-to-pr/scripts/implement_task.py to the user-selected runner agent; no nested agents.

**Goal:** squash/rebase で取り込まれた branch と、終了 PR の残存 pinned ref を、所有・保存・競合の保護を維持して整理できるようにする。

**Architecture:** SKILL 内の実行可能な判定・コマンドを fake gh と使い捨て Git で検証する。branch と ref は独立の安全判断とし、同じ SKILL を触るため直列に変更する。controller が共通条件・最終版の証拠を照合する。

**Tech Stack:** Markdown, Bash, Git, jq, Python/pytest via uv.

**Spec:** `docs/superpowers/specs/2026-11-09-issue-354-repo-cleanup-design.md` (`draft`、内容承認ではなく利用者の issue-to-pr 実行許可)。

## Global Constraints

- 編集は `.agents/skills/repo-cleanup-after-merge/SKILL.md` と同 `tests/`、本 Spec・Plan に限る。手順 5 と `pr_review_workspace.py` は変更しない。
- CLEANUP_BASE・fork sync・version 7/8 の gate A の照合本体・removable・--force 禁止・ignored gate は維持する。
- 祖先型/PR型とも対象 repository の MERGED PR と branch/headRefOid の一致が必要。別 repository・未マージ・対応不明は保持。PR型は mergeCommit が選択した base に含まれることも確かめる。
- local main/base、open PR、dirty/ignored、locked/prunable、所有不明の worktree は保護する。remote branch 削除は別の明示確認が必要。
- ref の削除は対応 PR の MERGED/CLOSED、open PR と現行・保持中 session が使わないこと、所属確定、読取値による compare-and-delete が必要。未知なら保持する。
- run_context 無し version7 + helper exit1 の例外だけを gate A/ガードレールに合わせる。version8・run_context 有り・exit2 は保持。
- テストに実 gh/API・実 runner を使わない。Python は uv。HOME はワンショット、継承 GIT_* を除く。rm/rmdir の変数は ${VAR:?}、他セッションの stash・広域 pkill・worktree prune は使わない。

## 受け入れ基準（実装担当とレビュー担当で同文を使う）

動作環境: Linux Dev Container の Bash/Git/jq、uv/pytest。実 gh の代わりに引数も検証する fake を使い、Git は一意の一時 repository。入力は空白入りのパス、非 ASCII/複数行の追跡内容、祖先・squash・rebase で取り込まれた branch と PR の JSON、repo 修飾および旧形式 ref。

防御範囲: MERGED と branch/head の完全一致に基づき、選んだ base に取り込まれた branch だけを候補にする。PR 不明・OPEN・head 不一致・cross repository・未統合 base は保持。ref は MERGED/CLOSED かつ open PR/現行・保持中 session の非使用を確認し、所属不明/並行更新は保持。version7 の狭い例外以外の helper 拒否は迂回しない。remote 削除は別の利用者確認。対象外: 実際の利用者の branch/ref/worktree の掃除、helper の変更、上記既存の安全境界の緩和。

## Review Focus

- 通常ツールの既存祖先必須が PR 型を拒否し続けないこと（Task 1 の managed fixture 正例）。
- -d の upstream 判定が取り込み先確認を迂回しないこと（Task 1、未統合/更新済み head の保持）。
- リモート候補提示が祖先型の一覧だけに戻らないこと（Task 1 の適用シナリオ、F の一覧テストは追加しない）。
- セッション無しの ref を扱いつつ helper sessions が全所有者を返すという誤った前提を置かないこと（Task 2 の適用シナリオ）。
- fork/upstream の同番号・ref更新競合を別対象の削除にしないこと（Task 2 の実行テスト/適用シナリオ）。

## 実行方式・予算

指定 `--implement pi_opencode-go_deepseek4-flash_max`、check は self=false、fallback無し。runner に1 Taskずつ依頼し、controller が取り込みとテスト、読み取り専用 sp-review が Task と全体をレビューする。

能動時間 360 分。準備/設計35、Task1 45、Task2 40、全体確認/公開30、PRループ最大3×70=210分を目安とする。runner implement は役割の既定90分、inspect45分。runner は同期実行で期限/停止確認を担当し、pi bash には timeout を付けない。任意の kill は行わず、停止不明は保留。読み取り専用シナリオ2回、Taskレビュー各1回と修正の限定再確認、全体レビュー1回と修正1波を予定。ループ inspect は利用者指定3担当、最大3サイクル。

同じ reliability の再試行1回、Task retry/rejected 最大1回。failed はその Task で停止し controller 実装へ切替えない。安全失敗は全体停止。phase境界、50%/100%、worker失敗直後に checkpoint。ledger は `tmp/agents/issue-354.6j_g6j_0/budget.jsonl`、SDD領域は同セッションの `sdd/2026-11-09-issue-354-repo-cleanup/`。検証記録はマージ用に保持し、不要と確認できるまで消さない。

## contingency（代替策）

- 初回REDがAPI出力の表記差なら意味を保つ最小修正を ledger に記録。安全条件の意味変更・scope追加は停止する。
- 旧refがfork/upstreamのどちらか確定できない場合は保持と理由報告。所属を推測した削除や helper 改変で解決しない。
- 大きな自動cleanupツールへ拡張せず、セッション照合など判断が必要な部分は手順に明記し、実行可能な安全ゲートとシナリオで検証する。
- base移動・新たな競合を観測したら SHA を差し替えず停止。予算100%で延長せず残作業と再開証拠を報告する。

## Task 1: branch の取り込み判定を共通化する

**Files:** Modify `.agents/skills/repo-cleanup-after-merge/SKILL.md`（通常ツールの候補照合、手順3/8/ゲートB/対応ガードレール）。Modify/Create 同 `tests/`（既存 `test_managed_target.py` / `test_detached_update.py` との整合を含む）。

**Interfaces:** 入力は対象 checkout・repo・明示PR番号・branch・その候補ref・base ref。実行可能な read-only 判定をSKILLに置き、祖先型とPR型を返せる。手順8は同じ判定を直前に確認し、-dの取り込み拒否時だけPR型を含む確認で-Dを許す。ゲートBの候補にも同じ判定を使用する。具体的な局所関数名/構造は担当が既存テストと最小に整合させる。

**テストの要否:** 必要（S: 後追いcommit/別PR/別baseの誤削除、未取り込み誤判定の既知不具合）。固定文言・一覧だけの検査は不可。同じ守りを複数層で重ねず、代表の実行テストと通る例を残す。

- [ ] Step 1: SKILLから実行部分を抽出し、real temporary Git + fake ghで祖先/squash/rebaseの正例、未マージ・PR不明・head不一致・別repo・未統合baseの保持を検証するテストを書く。squash/rebaseは実際に commit graph を作り、祖先でないことを独立に確かめる。
- [ ] Step 2: 変更前に対象テストを `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` でRED確認し、実出力を報告する。新しいブロック不在だけでなく既存手順の失敗根拠も記録する。
- [ ] Step 3: Spec R1/R2 の判定を最小実装。gh は対象 --repo を常に固定し `state,headRefName,headRefOid,mergeCommit,isCrossRepository` を取得、未知は保持。リモート削除コマンドは自動実行しない。手順5は変更しない。
- [ ] Step 4: 同じ関連testsをGREEN確認、git diff --check、追加テストのS/D基準を自己確認する。
- [ ] Step 5: 対象パスだけstageし `feat: recognize PR-proven merged cleanup branches` でcommit。RED/GREEN・所要時間・懸念を返す。

## Task 2: 残存 pinned ref と version7 例外を整理する

**Files:** Modify `.agents/skills/repo-cleanup-after-merge/SKILL.md`（残存ref手順、ゲートA冒頭、Red Flags/ガードレールの整合）。Create/Modify 同 `tests/` の実行回帰テスト。

**Interfaces:** Task1の判定と独立。ref inventoryは `git for-each-ref`、PRは所属repo/番号を明示。削除は `git update-ref -d <ref> <読んだ値>`。open PR/sessionの照合・unknown保持は省かない。helper sessionsは登録済みworktreeしか列挙しないため、それだけで非使用としない。保護中sessionや孤立した状態も調べ、完全に確定できない場合は保持する。旧形式refはfork/upstream等の複数所属候補の一方だけで消さない。

**テストの要否:** 必要（S: open PR/現行sessionの取得先破壊、別repo誤削除、並行更新の消失）。SKILLの実行ゲートを抽出し、正例と守る反例で操作結果を観測する。version7の文章整合はFなので文言固定テスト不要、適用シナリオで検証する。

- [ ] Step 1: 既存refが処理されないbaselineと、CASなら並行更新を保持すべきことを実行で確認しテストを書く。少なくとも終了PRの削除正例と、open/current session/所属不明/読取後更新の保持を代表1件ずつ検証し、同じ守りを重複網羅しない。手順が判断を要求する部分はcontrollerの適用シナリオで補う。
- [ ] Step 2: REDを確認してから R3/R4 を実装。version7/8 helperは変えず、手順5は一字も変えない。gate Aとガードレールを既存例外に揃え、exit2とrun_context/version8の保護を維持する。
- [ ] Step 3: `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q`、`git diff --check`。変更範囲を自己確認する。
- [ ] Step 4: 対象だけstageし `feat: safely retire residual PR review refs` でcommit。RED/GREEN・所要時間・懸念を返す。

## 統合確認・公開（controller）

R1/R2→Task1の実行結果と修正後適用シナリオ、R3/R4→Task2の実行結果と同シナリオを対応付ける。共有するrepo/head/base/ref値の読取と再確認順はcontrollerが追う。Task成功件数だけで条件を満たしたとしない。

- [ ] 各Taskの実装と同文の受け入れ基準・Spec関連節を読み取り専用レビューへ渡し、指摘を原文で担当へ返す。
- [ ] 修正後適用シナリオ1回、最終全体レビュー1回、必要な修正は指定runner担当へ戻す。
- [ ] 最後のcommit後にcleanを記録し、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`git diff --check <captured-base>...HEAD` を実行。Issueの手動5ケースも同じ一時Gitで確認。scope内のskill効率検査はuv経由で実行し既存由来のwarningと区別する。
- [ ] HEAD/base/clean/argv/終了コード/ログを validation.json と finalize用 checks.json に保存。Specはdraftのまま実行結果を追記する。
- [ ] claim/Issue/競合/baseを再確認。全未push commitを親のscan-before-push.shで捕捉SHA付き検査し、そのSHAをpush。PRはボードの子なので `Refs #354`、同じPRにSpec/Planを含める。
- [ ] 指定 `--merge` ループを開始し、検証・記録・finalizeだけのマージ経路を守る。結果を子に記録後、自分のclaimだけ正確なSHA leaseで解放する。親の状態更新/子のcloseはcoordinatorの判断を尊重する。
