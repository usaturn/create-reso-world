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

## 実行記録（2026-11-19）

- 作業は完了した（状態は `draft` のまま。内容の承認は記録していない）。実行方式は inline（司令塔が直接実行）
- 提出用ブランチ: `usaturn/resoloop:feat/plugin-system` @ `c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b`（tree `9d1fa089f93de4e0c74afb63da64a83ca439b6a6`）。https://github.com/usaturn/resoloop/tree/feat/plugin-system
- rebase: `git rebase --onto 32309ca a7be2dd` は競合なしで 35 コミットを載せ替えた。rebase 直後の tree は `43d17f10e8adac2201a8879f366995c26357bf1c` で、`SRC_SHA` と `UPSTREAM_SHA` の 3-way merge の tree と一致した。件名末尾の内部 Issue 参照を除いた後も tree は同じ
- 追加コミット 3 件: `b12debf`（README 3 種と英日ガイドの fork 向け記述）、`34754fe`（コードコメント 2 行）、`c72deaf`（テストヘルパー 2 箇所。`/proc/<pid>/stat` の読み取り中にプロセスが回収されると ESRCH の `IOException` になり、`PluginCommandTests.NormalExitStopsLeftoverDescendants` が 1 回失敗した。本体と同じ ESRCH の扱いを足した。単独の再実行 3 回は修正前も成功しており、rebase に起因しない既存の不安定さである）
- 検索: 共通検索範囲の `git grep -nE "create-reso-world|usaturn|feat/plugin-v2"` は一致なし（終了コード 1）。README の絶対 URL のパスと、ガイドの相対リンクの先は最終候補の tree に存在する
- 差分: `UPSTREAM_SHA..c72deaf` は 53 ファイル（追加 44、変更 9）で、プラグイン機構・文書・最小例・テストだけ。fork `main` 固有のコミット（`ff77b91`）との共通部分は 0 件
- Linux: `c72deaf` で `dotnet build ResoLoop.slnx`（警告 0・エラー 0）と `dotnet test ResoLoop.slnx --no-build`（RLoop.Tests 639 件・RLoop.IntegrationTests 24 件、失敗 0）
- Windows: 検証用 PR https://github.com/usaturn/resoloop/pull/34 （base `ci/issue-33-upstream-base` = `UPSTREAM_SHA`。マージせず close）の run https://github.com/usaturn/resoloop/actions/runs/44378694937 が成功。checkout された merge commit `ea338405917e893dfe5b00ed78c7e65eb9ec8a6b` の tree は最終候補の tree と一致
- 完了時のリモート: `feat/plugin-v2` = `95d115a…`、fork `main` = `ff77b91…`（どちらも着手時のまま）、上流 `main` = `32309ca…`（2026-11-18T19:20Z の時点で前進なし）
- 未実施: Resonite・Blender を使う実機検証（対象外）。残したもの: 検証用ブランチ `ci/issue-33-upstream-base`（公開済みの上流コミットを指すだけ。不要になったら削除してよい）
- 能動時間: 約 60 分（準備・Issue 更新・文書 20 分、rebase と文書修正 10 分、Linux の検証と修正 15 分、公開と Windows CI 10 分、記録 5 分）
