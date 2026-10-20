# Issue #200: bash のテストを直接実行しても、外から渡された `GIT_*` のリポジトリを書き換えない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/200（親 Issue・ボード・先行 Issue・コメントは無い）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue200-bash-test-git-env.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-200-bash-test-git-env`（branch `fix/issue-200-bash-test-git-env`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #200` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #200`）まで行う。マージはしない
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- 基準: `origin/main` の `d29c93c`

## 意図

PR #194（#166）は、bash のテストに `GIT_*` を渡さない処理を入口の `.devcontainer/run-tests.bash` に入れ、テストを 1 本ずつ直接実行する場合を既知の制限（D-166-5）として残した。linked worktree で `git rebase --exec 'bash tests/scripts/test-xxx.bash'` を実行すると、git は `GIT_DIR` を export するので、一時リポジトリを作るテストの `git init`・`git -C <一時ディレクトリ>` が作業中のリポジトリの共有の設定（`core.bare=true` など）・ブランチ・index を書き換える。終了コード 0 で終わるテストもあり、rebase の成功から気づけない。直接実行でもランナー経由でも、テストの git が外から渡された `GIT_*` を使わないようにする。

## 確認した事実（2026-10-20）

- #200 に open PR・予約・worktree・branch は無い。ボードの子ではない
- `.devcontainer/run-tests.bash` が実行する bash のテストのうち、git を使うのは 12 本。うち一時リポジトリを作って書き込むのは Issue の 8 本（`tests/scripts/` の `test-check-layout`・`test-new-world`・`test-resoloop-fork`・`test-resoloop-meshy`・`test-scan-before-push`・`test-superpowers-review-copy`、`.devcontainer/` の `test-herdr-status`・`test-report-resoloop-skills`）と、既に冒頭で除いている `.devcontainer/test-run-tests.bash`
- 残りの 3 本（`tests/scripts/test-file-modes.bash`・`test-gitignore.bash`、`.devcontainer/test-readme.bash`）は、作業中のリポジトリを `git ls-files`・`git check-ignore`・`git grep` で読むだけで書き込まない。`.devcontainer/test-pi-superagents.bash` は文字列に `git` を含むだけで git を起動しない
- 8 本のうち 7 本（`test-herdr-status` 以外）は、冒頭で `GIT_CONFIG_NOSYSTEM`・`GIT_CONFIG_GLOBAL`・`GIT_AUTHOR_NAME` などを自分で export する。`GIT_*` を除く処理は、その export より前に置く必要がある。`test-herdr-status` の `GIT_CORE` は export しないシェル変数で、`compgen -e` の対象にならない
- `test-run-tests.bash` は `set -euo pipefail` の直後に `while IFS= read -r name; do unset "$name"; done < <(compgen -e -X '!GIT_*')` を置く（PR #194）。`run-tests.bash` も同じ 1 行でテストの前に除く
- 8 本を `run-tests.bash` で実行すると、すべて通る（合計 約 2 分 18 秒。`test-new-world` 62 秒、`test-check-layout` 37 秒、`test-scan-before-push` 25 秒）。ランナーは既に `GIT_*` を除いているので、テストの冒頭で除いても、ランナー経由の実行の環境は変わらない
- 修正の前の再現（使い捨ての clone の linked worktree で、その管理領域を `GIT_DIR` に export して直接実行）の結果は Plan の検証の記録に書く

## 設計

### 1. 8 本の冒頭で `GIT_*` を除く

8 本それぞれの `set -euo pipefail` の直後（テストが自分で `GIT_*` を export するより前）に、`test-run-tests.bash` と同じ 1 行と、理由を書いた短いコメントを置く。テストとそこから起動するスクリプト・git のすべてが、外から渡された `GIT_*` を引き継がない。テストの対象のスクリプト（`scripts/` など）は変えない。

### 2. `.devcontainer/README.md` に、今後のテストの書き方を足す

「テストの実行」の「実環境を変えない」の文の後に、一時リポジトリを作るテストは冒頭で外から渡された `GIT_*` を除くこと（理由: `git rebase --exec` が export する `GIT_DIR`。1 本だけ直接実行しても効く）と、新しく足すテストも同じ形にすることを書く。

### 3. 検証（テストは足さない。D-200-3）

- Issue の再現と同じ形の検証用スクリプト（`PARENT_ROOT/tmp/agents/` のセッションディレクトリに置き、commit しない）で、修正の前と後の 8 本を直接実行し、clone の共有の設定・HEAD・index・refs・`status` を比べる。修正の前は変わり、後は変わらないこと
- 修正の後の commit で、`git rebase --exec 'bash tests/scripts/test-new-world.bash'` を実行し、共有の設定が変わらず、main の checkout の `git status` が通ること
- `README.md` の「テスト」の入口（ワールドの行を除く）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-200-1 8 本それぞれの冒頭に 1 行を置く（Issue の案 (a)）**
  - 選択: 8 本の `set -euo pipefail` の直後に、`test-run-tests.bash` と同じ 1 行を置く
  - 別案: (b) `tests/scripts/lib/` に関数を置いて読む、(c) 文書で直接実行を禁じる
  - 理由: Issue の推奨。(b) は `.devcontainer/test-*.bash` が lib を読まないので 2 つの形が混ざり、`tests/scripts/` でも lib を読むのは 2 本だけ。(c) は手順・例（review-fix-planning の SKILL.md、Plan 13 本）の書き方と食い違い、守られなかったときに実害が出る
- **D-200-2 対象は一時リポジトリに書き込む 8 本だけ**
  - 選択: 作業中のリポジトリを読むだけの 3 本（`test-file-modes`・`test-gitignore`・`test-readme`）は変えない
  - 別案: git を使う bash のテストすべてに入れる
  - 理由: 読むだけの git は `GIT_DIR` が linked worktree の管理領域でも同じ内容を読み、書き換えない。Issue の対象も 8 本。足しても害は無いが、守る挙動の無い変更になる
- **D-200-3 回帰テストは足さず、再現と同じ形の検証で確かめる**
  - 選択: commit しない検証用スクリプトで、修正の前に変わり後に変わらないことを確かめ、結果を Plan と PR に記録する
  - 別案: (a) 8 本を `GIT_DIR` 付きで直接実行して比べる bash のテストを `tests/scripts/` に足す、(b) 全部の bash のテストを同じ形で実行するテストを足す
  - 理由: 守る挙動は各テストの冒頭の同じ 1 行で、PR #194 の D-166-6（unittest の 2 本の 1 行の変更は、テストを足さず統合確認で確かめた）と同じ形。(a) は 8 本のパスの一覧をテストに写し（`AGENTS.md` の「作らない型」の 3）、`run-tests.bash` の実行時間が約 2 分 18 秒増える。(b) は一覧を写さないが、bash のテスト全体の時間が約 2 倍になる。今後足すテストへの適用は、2 の文書で伝える
  - 既知の制限: 今後足すテストが 1 行を書き忘れても、テストでは検出しない（ランナー経由の実行は `run-tests.bash` が守る）
- **D-200-4 今後のテストの書き方は `.devcontainer/README.md` に書く**
  - 選択: 「テストの実行」の節の、「実環境を変えない」の文の直後
  - 別案: (a) `AGENTS.md` の「テストの採用基準」、(b) 書かない
  - 理由: bash のテストの実行と前提を書いた場所で、Issue の対象も同じ文。`AGENTS.md` はテストを書くかの基準で、テストの書き方は書いていない。(b) では Issue の「今後足す bash のテストも同じ形にする」が伝わらない
- **D-200-5 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は 8 本の同じ 1 行と文書の 1 文で、子に文脈（置く位置の条件・再現の形）を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. 8 本それぞれを、使い捨ての clone の linked worktree を cwd にし、その管理領域を `GIT_DIR` に export して直接実行しても、clone の共有の設定・各 checkout の HEAD・index・refs・`status` が変わらない。修正の前の同じ実行では変わる
2. 8 本は、`GIT_DIR` を export した直接実行でも通る（終了コード 0）
3. 修正の後の commit で `git rebase --exec 'bash tests/scripts/test-new-world.bash' HEAD~1` を実行しても、共有の設定に `core.bare` が書かれず、main の checkout の `git status` が通る
4. `README.md` の「テスト」の入口（ワールドの行を除く）が、変更の前の基準と同じ結果になる
5. `.devcontainer/README.md` の「実環境を変えない」が、直接実行でも成り立つ

## 範囲外

- テストの対象のスクリプト（`scripts/`・`.devcontainer/` の本体）の変更
- 作業中のリポジトリを読むだけの bash のテスト（D-200-2）
- pytest・unittest のテスト（PR #194 で対応済み）
- 手順・例（review-fix-planning の SKILL.md、`docs/superpowers/plans/`）の書き換え。修正の後は直接実行しても安全になる
- 書き忘れを検出するテスト（D-200-3 の既知の制限）

## 実装者に任せること

- コメントの文面（`test-run-tests.bash` のコメントに合わせる）
- 検証用スクリプトの細部
