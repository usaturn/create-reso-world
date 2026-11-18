# usaturn/resoloop#33 プラグイン機構の上流提出用ブランチ Implementation Plan

- 状態: `draft`（利用者の実行指示は実行許可として記録し、内容の承認にしない）
- Spec: `docs/superpowers/specs/2026-11-19-usaturn-resoloop-issue33-plugin-upstream-branch-design.md`
- 対象: https://github.com/usaturn/resoloop/issues/33 。`CODE_ROOT` は `<PARENT_ROOT>/external/resoloop/.worktrees/issue-33-plugin-system`（ブランチ `feat/plugin-system`）。`DOC_ROOT` は `<PARENT_ROOT>/.worktrees/resoloop-issue-33-plugin-upstream`（ブランチ `docs/resoloop-issue-33-plugin-upstream`）
- 入力の SHA は Spec の「管理・実行許可」のとおり（`SRC_SHA`・`UPSTREAM_SHA`・fork `main`）

## 受け入れ基準

Spec の「4. 受け入れ条件」をそのまま使う（動作環境・実入力・防御範囲・完了条件 1〜7）。

## 実行方式

`superpowers:executing-plans`（司令塔が inline で実行する）。rebase と競合解消は司令塔が所有する worktree で直接行うという利用者の指示と、Task が同じブランチへの逐次の変更であることによる。

## Task

### Task 1: rebase と履歴の整理

1. `CODE_ROOT` で `git rebase --onto UPSTREAM_SHA a7be2dd`（競合が出たら両側の意図を保って解消し、内容を記録する）。
2. `git rev-parse HEAD^{tree}` が `43d17f10e8adac2201a8879f366995c26357bf1c` と一致することを確かめる。
3. 件名末尾の `(create-reso-world#N)`・`(#N)` を除く（`UPSTREAM_SHA..HEAD` だけ）。tree が変わらないこと、コミット数が 35 であることを確かめる。

- テスト: 不要（履歴の操作。tree の照合で確かめる）。

### Task 2: fork 向け記述の整理

Spec 2.4 のとおり 7 ファイルを直し、1 つ以上のコミットにする。英日の内容をそろえる。

- 検証: 共通検索範囲の `git grep` が一致なし（終了コード 1）。README の絶対 URL のパス（`docs/PLUGINS.md`・`docs/PLUGINS.ja.md`・`examples/plugins/hello`）が `git ls-tree HEAD` に存在する。ガイド内の相対リンクの先が存在する。
- テスト: 不要（文言・リンクは F。検索と tree の照合で代える）。

### Task 3: Linux の検証と統合の修正

`dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build` を実行する。失敗したら `systematic-debugging` で原因を調べ、上流の変更とプラグインの挙動を両立させる最小の修正をコミットして Task 2 の検証からやり直す。

- テスト: 統合で見つかった不具合が S に当たる場合だけ足す。

### Task 4: 差分のレビューと公開、Windows CI

1. `UPSTREAM_SHA..HEAD` の差分（ファイル一覧と、上流と双方が変更した 3 ファイル）をレビューし、プラグイン機構・文書・統合の修正だけであること、fork `main` 固有のコミットが無いことを確かめる。
2. `scan-before-push.sh -C CODE_ROOT --base upstream/main` の SHA を `refs/heads/feat/plugin-system` へ push する。`UPSTREAM_SHA` を `refs/heads/ci/issue-33-upstream-base` へ push する（公開済みのコミットだけ）。
3. `gh pr create --repo usaturn/resoloop --base ci/issue-33-upstream-base --head feat/plugin-system` で検証用 PR を作り、`CI / windows` の完了を待つ。run の `head_sha`（merge commit）の tree と最終候補の tree の一致を確かめる。
4. 成功したら検証用 PR をマージせず close する。失敗したら原因を直すコミットを足して push し、Linux の検証からやり直す。

### Task 5: 記録と引き渡し

1. `feat/plugin-v2`・fork `main` の先端が着手時の SHA のままであること、`feat/plugin-system` の先端が最終候補であることを `git ls-remote` で確かめる。上流 `main` が進んでいれば差分を記録する（追従しない）。
2. Issue #33 に結果をコメントし、close する。Spec・Plan に実行記録を足して文書専用 PR を作る。

## 実行予算

- 全体の能動時間: 300 分（Issue の見積もり 3〜6 時間）。目安: 準備・文書 60 分、Task 1〜2 60 分、Task 3 45 分、Task 4 60 分（CI の待ち 20 分の上限 ×最大 3 回）、Task 5 30 分
- 再試行の上限: 同じ原因の失敗は 1 回まで。Windows CI の修正と再実行は 3 回まで
- checkpoint: 各 Task の境界、予算の 50%・100%、CI が失敗した直後
- 縮小・方法変更の候補: 下の contingency

## contingency（代替策）

- rebase の競合が多く、直線化で解消結果を保てない（Task 1.2 の tree が一致しない）: `git rebase --abort` し、`git merge --squash` 相当ではなく、`UPSTREAM_SHA` の上へ元のコミットを順に cherry-pick して差を特定する。それでも一致しないときは、差分を記録して止まり、利用者に報告する（tree の不一致を成功にしない）
- fork の Actions が動かない・権限が無い: 完了できた範囲（Linux の検証まで、未 push か push 済みか）と阻害要因を報告して止まる。Windows を未検証のまま完了にしない
- 検証対象の確定後に上流が進む: 追従せず、差分を #105 への引き継ぎ事項として記録する
- gitleaks の検出: AGENTS.md の「push の前の秘密情報の検査」に従う
