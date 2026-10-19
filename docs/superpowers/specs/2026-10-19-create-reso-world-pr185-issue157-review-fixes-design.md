# PR #185（Issue #157）のレビュー修正の選別

## 管理・実行許可

- 状態: completed（結論 2: 修正不要でマージ）
- 対象: usaturn/create-reso-world PR #185（`feat/issue-157-issue-to-pr-implement`、`Closes #157`）。現行 HEAD `25e06972fc3eb29a02a765c219e2e30b8077d75c`
- 実行許可: 利用者の「`/issue-to-pr #157 --merge` 相当で進めて」（2026-10-19）。#157 の Spec の D-157-13 のとおり、PR の作成後のレビュー修正のサイクル（最大 3 回）と、修正不要と確かめられたときのマージ・関連 Issue の更新まで。review-fix-planning は「完遂」の流れで、判断基準（現行 HEAD で到達できる致命的な指摘だけを直す）、三択の結論、修正後の自己レビューは最大 1 回を保つ
- サイクル: 1 回目。関連 Spec: `docs/superpowers/specs/2026-10-19-create-reso-world-issue157-issue-to-pr-implement-design.md`
- 専用の worktree: `/workspaces/reso-world/.worktrees/issue-157-issue-to-pr-implement`（PR の branch を checkout 済み、clean、HEAD が PR の head。このスキルの片付けの対象にしない）

## 入力

レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#185-feat-issue-157-issue-to-pr-implement/`。既定のレビュアー（agent-runner の workflow `review` の `inspect`）を runner の CLI で並行に起動した（2026-10-19T12:08Z〜12:28Z）。

| レビュアー | 対象 HEAD | runner の state | 指摘 | 計画の入力 |
| --- | --- | --- | --- | --- |
| `pi-gpt`（gpt-6.1-sol） | `25e06972fc3e` | success | 0 | した |
| `dsh-ccd`（deepseek/deepseek-v4.1-flash、`finalize-parent` で保存） | `25e06972fc3e` | success | 0 | した |
| `claude-opus`（claude-opus-5-5） | `25e06972fc3e` | success | 2（M-1・L-1）、未検証の候補 1（U-1） | した |
| `devin-swe`（SWE-2 Max） | `25e06972fc3e` | response_failed（helper は保存済み。runner の adapter が回収の段で拒んだ） | 0 | した（保存済みの成果を読む。移植元のループと同じ扱い） |
| `pixg`（grok-4.7） | — | awaiting_authentication（2.6 秒） | — | しない（runner の失敗。起動し直さない） |

runner の `outside_changes` は `/tmp/pr-review-182-177dc8a7/worktree`（起動の前から監査できない登録）と `.worktrees/issue-155-review-fix-roles`（#155 のセッションが 12:21Z・12:26Z に commit）で、どちらもレビュアーの変更ではない。PR の head は `refs/pr-review/repos/usaturn/create-reso-world/185` に固定し、全レビューの対象 HEAD がその祖先であることを確かめた。

## 分類

解消済み 1 / 対応する 0 / 対応しない 2

| ID | 区分 | 根拠 |
| --- | --- | --- |
| U-1 `accept` が拒否（終了コード 1）したときの次の操作が SKILL.md に無い | 解消済み | 現行の SKILL.md で振る舞いを確かめた（下の「確認」）。`accept` が `git commit failed` で拒否した場面で、3 回とも hook の回避・手での取り込み・`self` での引き取りをせず、その Task で止まって報告した。疑われた誤り（取り込めないまま次の Task に進む）は再現しない |
| M-1 同じリポジトリの他の worktree で並行作業があると、担当の成果が `rejected` になり `accept` でも取り込めない | 対応しない | 設計の是非（レビュアーも【要設計判断】）。現行 HEAD で再現した（下の「確認」）が、挙動は移植元 `a47b2065` と同じ安全側の拒否で、誤った取り込み・データの消失・誤った対象への操作は起きない。手順のとおりに使うと、依頼し直しは再試行の上限（1 回）までで止まり、並行作業による拒否であることが報告される（振る舞いの評価で 3/3）。並行作業の中でも取り込めるようにする方法（確認したパスを `accept` に渡す、判定の対象を feature worktree と main checkout に絞る）は、他の checkout への書き込みの合図をどう扱うかの判断が要るので持ち越しの候補とし、PR の説明の既知の制限に条件と回避方法を書く |
| L-1 `test_implement_task_run.py` の git の隔離が `implement_task.py` 自身の git に届かず、利用者の全体の git 設定で `test_accept_commits_uncommitted_changes_with_message` が失敗する | 対応しない | 致命的でない。利用者の全体の git 設定が一時リポジトリでの commit を失敗させるとき（署名の必須、失敗する hook）だけのテストの失敗で、誤った結果を通すものではない。この Dev Container と利用者の設定（`git config --global` に `commit.*`・`gpg.*`・`core.hooksPath` が無い）では起きない。#166 の対策（`GIT_*` を引き継がない）は `_git` が `GIT_*` を除くので保たれている。PR の説明の既知の制限に書く |

pi-gpt・dsh-ccd・devin-swe は指摘 0 件。dsh-ccd が書いた `tests/scripts/test_superpowers_context.py` の 1 件の失敗は、PR の変更の外で、レビューの TMPDIR が親の checkout の中にあるための環境の要因（レビュアーの判断）なので、指摘として扱わない。

## 確認

- M-1: 隔離 worktree（`mktemp -d` の `/tmp/review-fix-planning.3sHNJ6/worktree`、HEAD `25e0697`。確認の後に `git worktree remove` と削除で片付けた）で、テストの `Fixture`・偽の担当を使い、担当ファイルの中だけを変えて commit する担当を runner で起動した。依頼の間に別の linked worktree のファイルを変えると `verdict: rejected`（`outside_changes: <別の worktree>`）、続く `accept` は `AcceptRefused`。別の worktree を変えない対照は `importable` で取り込めた。スクリプトは `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/review/cycle-1-repro_m1.py`
- U-1・M-1 の振る舞い: 現行の SKILL.md（`25e0697`、sha256 `fc548f11…`）を Claude Code の sonnet に Read で読ませ、3 つの場面（(za) 他のセッションの worktree だけが並んだ `rejected`、(zb) feature worktree が並んだ `rejected`、(zc) `accept` の拒否）を 3 回答えさせた（各回 Read 2 回だけ）。(za) は 3/3 が上限の中で 1 回だけ依頼し直し、再発したら止まって並行作業を報告する。(zb) は 3/3 が feature worktree の状態を読み取りで確かめ、変わっていれば止まる。(zc) は 3/3 が止まる。回答は `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/eval/cycle1-red-*.md`
- L-1: `implement_task.py` の `_git`（`literal_environ()` から `GIT_*` を除いた環境）と `tools/agent_runner/environ.py` の `literal_environ`（起動時の環境をキャッシュ）を読み、レビュアーの再現（一時 HOME の署名必須で 1 failed）と合うことを確かめた。利用者の `git config --global` に該当の設定が無いことを確かめた

「対応する」が 0 件なので、守る条件と影響経路の表、設計の見直しのきっかけの判定、修正後の自己レビューは無い。

## 結論 2 の手順と結果

- 検証: PR の作成の前に、同じ HEAD `25e0697`（検証の前後とも作業ツリーは clean）で `uv run pytest tests/skills .agents/skills .agents/scripts tools` 2988 passed（828.97 秒）、`bash .devcontainer/run-tests.bash` PASS 33 本、`bash scripts/check-layout.sh` PASS（ログ `/workspaces/reso-world/tmp/agents/issue-157.e6surmvx/verify/`）。その後に HEAD は変わっていないので、この結果を使う（#157 の Spec の D-157-13、移植元の `--merge` の「検証記録の再利用」と同じ条件）。この Spec の commit は `docs/superpowers/` だけの変更
- base: `origin/main` は `8083a85` のままで、PR の head の祖先（merge の一時ツリーは不要）
- CI: create-reso-world は private で Actions を止めているので確かめない（`AGENTS.md`）
- マージしてよい範囲: usaturn/create-reso-world の open で draft でない PR
- PR の説明の既知の制限に M-1・L-1 を書く（`gh pr edit --body-file`）
- マージは `gh pr merge --merge --match-head-commit`（この Spec の commit を push した後の HEAD）。関連 Issue の更新と、#157 の予約の解放は、マージの後に行う（結果は状況コメントと完了報告に書き、この Spec には追記しない）

## 持ち越しの候補（Issue は作っていない）

- 並行作業の中でも担当の成果を取り込める入口（M-1）。案: (B) `accept` に、controller が他の作業のものと確かめた `outside_changes` のパスを渡す（feature worktree と main checkout は渡せない）、(C) `implement_task.py` の判定の対象を feature worktree と main checkout に絞り、ほかは報告だけにする。どちらも移植元 `a47b2065` から変える判断で、他の checkout への書き込みの合図の扱いを決める必要がある。新しい Issue を作るのは利用者の許可を得てから
