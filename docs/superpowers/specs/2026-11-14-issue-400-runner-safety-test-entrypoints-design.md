# Issue #400: runner の安全指示に、テスト・検証の入口の許可を明記する

## 管理・実行許可

- 状態: `draft`（issue-to-pr による実行委任。内容の承認は得ていない）
- 対象: https://github.com/usaturn/create-reso-world/issues/400
- 利用者指示（2026-11-14）: 「このIssueの残作業を実行してください。残作業が終わったらIssueを更新し、関連Issueも更新してください。このIssueは問題がなければ最後にクローズしてください。」
- issue-to-pr の委任として、推奨案で設計し、検証・commit・push・PR 作成まで進む。`--merge` の指定は無いため、PR のマージは行わない。Issue の完了条件は「変更が main にマージされ、マージ後のレビュー修正 run 3 回で目標値を評価できる状態になる」であり、マージ前のクローズはこの条件を満たさない。クローズの扱いは最終報告で利用者に明示する。
- repository: `usaturn/create-reso-world`。base: origin / `refs/heads/main` / `950186cdac1ff52f42f8b212235f06074e2c84d6`。
- Spec・Plan はコードと同じ worktree・PR に含める。確認用コピーは作らない。

## 目的と原因

agent-runner は全担当の依頼文の先頭に安全指示を 1 行で付ける。現在の文言は「python・python3 を直接起動しない」「`python -` へ heredoc を渡さない」「uv を使う」を禁じるが、リポジトリが用意したテスト・検証の入口が内部で python3 を使う場合まで禁止するかは読み手に委ねられている。

PR #399 のレビュー修正ループでは、inspect 担当が `.devcontainer/test-herdr-migration.bash` を「直接の python3 起動を含む」と解釈して実行せず、より狭い一時プローブで代えた。同じサイクルの他の担当は実行しており、解釈が分かれている。実行しなくてもエラーにならないため、テストより狭い確認のまま成果が返る。

安全指示の意図は、担当自身が python・python3 を起動して uv 環境の外や heredoc で任意の Python コードを実行することを防ぐことにある。リポジトリの入口（`bash .devcontainer/run-tests.bash`、`bash .devcontainer/test-*.bash`、`bash scripts/check-layout.sh` など）の内部利用まで禁じる意図ではない。文言に許可を明記して、担当による解釈のばらつきを減らす。

## 範囲・除外

変更する。

- `tools/agent_runner/runner.py` の安全指示（先頭 1 行）に、リポジトリのテスト・検証の入口は内部で python3 を使っても実行してよいことと、自分で python・python3 を包むコマンドを作ることは許可しないことを足す。
- `tools/agent_runner/tests/test_runner.py` の既存 F∩S テスト `test_write_exceptions_follow_the_work_scope_lines` に、許可と禁止の両方を確かめる assertion を足す。

変更しない。

- `.devcontainer/test-*.bash` から python3 を除く書き換え（AGENTS.md の例外の範囲）。
- `exception_lines()`、`.agents/skills/review-fix-planning/tests/test_run_roles.py`、段落構造、他の安全指示（git stash・pkill -f・killall・PID 所有）。
- 担当が実行したコマンドを runner が監査する仕組み。
- プロンプト全文や段落構造だけを固定する新しいテスト。

## 設計

### 検討した案

- **A（採用）: 先頭の安全指示の 1 行に許可文を足す。** 禁止文の直後、末尾の「writes=true/false 共通・write exceptions で解除しない」の前に置く。既存の行・段落構造を変えず、#415 の `exception_lines()` が最初の空行までを読む前提を保つ。呼び出し側の変更も不要。
- **B: 許可を別の行・段落として足す。** 読みやすくなるが、`exception_lines()` が例外見出しを見失う可能性があり、runner の `test_write_exceptions_follow_the_work_scope_lines` と CLI テストが前提にする 2 行構造も変わる。#415 との結合方針に反するため採用しない。
- **C: 呼び出し側が write exception としてテスト入口を渡す。** 文言の解釈問題は残り、全呼び出し側の変更が要る。許可の範囲も担当ごとにばらつくため採用しない。

### 採用する文言

禁止文の直後に次を足す（英語、既存の 1 行に連結し、生成する文字列に改行を足さない）。

> You may run the repository's test and verification entry points, such as bash .devcontainer/run-tests.bash, bash .devcontainer/test-*.bash, and bash scripts/check-layout.sh, even when they use python3 internally; this does not permit wrapping python or python3 in a command of your own.

- 許可するのは「リポジトリのテスト・検証の入口」に限る。例示は Issue の実入力にある 3 種類。
- 「even when they use python3 internally」で、AGENTS.md の例外による `.devcontainer/` の python3 利用を含むことを示す。
- 「does not permit wrapping python or python3 in a command of your own」で、禁止回避のための任意のラッパーを許可しないことを示す。
- 既存の「Do not run python or python3 directly, and do not pass a heredoc to python -; use uv run for Python.」と「These safety restrictions apply whether writes=true or writes=false and are not lifted by write exceptions.」はそのまま残す。

### テストの更新方針

既存の代表 1 件を更新する。新しい恒久テストは作らない。プロンプト全文・段落構造の固定は F であり、壊れても気付けない損害を防ぐ F∩S ではない。既存テストは、先頭行が安全指示 1 行であること、write exceptions の有無で同じ先頭行になることを既に確かめている。ここに次の assertion を足す。

- 許可: `repository's test and verification entry points`、3 つの入口のパス、`even when they use python3 internally`、`does not permit wrapping python or python3`。
- 禁止の維持: `do not run python or python3 directly`、`do not pass a heredoc to python -`。

`writes=true` 側は、先頭行の文字列が `role.writes` に依存しない実装（2 行目だけが変わる）ため、同じ守りの別組み合わせになる。恒久テストは増やさず、実装時に一時プローブで確認する。

## 受け入れ基準

- **動作環境:** Dev Container（Ubuntu 26.04 LTS）のリポジトリルート。`uv` と pytest が使えること。
- **実入力:** runner が `writes=true` と `writes=false` で生成する依頼文（書き込み例外あり・なしの両方）。許可の対象として `bash .devcontainer/run-tests.bash`、`bash .devcontainer/test-herdr-migration.bash`、`bash .devcontainer/test-cleanup-workspace.bash`、`bash scripts/check-layout.sh` を想定する。
- **防御範囲:** 許可するのはリポジトリが定めたテスト・検証の入口の実行だけ。担当自身による `python`・`python3` の直接起動、`python -` への heredoc、禁止回避のための任意のラッパーは対象外とし、禁止のままにする。
- [ ] runner の依頼文に、テスト・検証の入口は内部で python3 を使っても実行してよいこと、python・python3 の直接起動と heredoc は禁止のままであることが書かれる。
- [ ] `writes=true`・`writes=false` のどちらでも同じ許可・禁止の指示になる。write exceptions で外せない点は変えない。
- [ ] 安全指示の 1 行目・`writes=...` の行・例外の見出しと一覧・空行・caller 本文の順序を維持し、安全指示の途中に `\n`・`\n\n` を入れない。
- [ ] 既存の F∩S テストを更新し、許可と禁止の両方を確認する。
- [ ] `uv run --project . --locked pytest tools/agent_runner -q` が通る。
- [ ] 実装 worktree のルートで `uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` も通る。両変更が揃った状態で確認する。偽の adapter のみを使用し、有料モデルは起動しない。

## テスト採用基準

- 既存の `test_write_exceptions_follow_the_work_scope_lines` は S / F∩S（担当が安全指示を失って危険な実行を許す、または入口の許可を失って必要な検証を飛ばす）として維持し、今回の文言に対応させる。防ぐ損害をコメントに書く。
- プロンプト全文・段落構造の一致だけを目的とするテストは F のため追加しない。`writes=true` の確認は一時プローブ（コミットしない）で行う。
- 検証はリポジトリの入口（pytest）で行い、結果と終了コードを記録する。

## 決定記録

### D1: 許可文の置き場所

- 選択した案: 禁止文の直後、末尾の共通適用文の前。同じ 1 行に連結する。
- 検討した別案: 先頭（作業範囲の直後）、別行・別段落。
- 選択理由: 禁止の直後に許可を置くと、何が禁止で何が許可かを続けて読める。別行・別段落は #415 の前提を壊す。
- 委任指示または停止条件: 通常の設計判断の委任。段落構造を変える必要が生じたら進めず、#415 との結合方針を先に更新する。

### D2: テストの更新範囲

- 選択した案: 既存 F∩S テスト 1 件に assertion を足す。新しいテストは作らない。
- 検討した別案: 新しい代表テストの追加、プロンプト全文の固定、`writes=true` の恒久テスト追加。
- 選択理由: 既存テストが同じ先頭行を write exceptions の有無で確認している。`writes=true` は先頭行が依存しない実装のため、別組み合わせの重複になる。
- 委任指示または停止条件: 通常の設計判断の委任。守りを弱める変更は不可。

### D3: 公開と Issue の扱い

- 選択した案: PR を作成して完了を報告する。Issue は完了条件が main へのマージのため、マージ前にクローズしない。関連 Issue #415 には、両変更が揃った検証結果をコメントする。
- 検討した別案: PR 作成後に Issue をクローズする、`--merge` なしでマージする。
- 選択理由: issue-to-pr は `--merge` の指定が無い run でマージしない。Issue の完了条件もマージを前提にしている。
- 委任指示または停止条件: 利用者の明示指示（クローズ）と完了条件が矛盾するため、最終報告で扱いを明示する。マージの指示が別途あれば、その時点で判断する。

## 調査と検証の記録

- Issue 本文・全コメント（1 件）・関連 Issue #415 の状態を確認した。#415 の PR #438 は 2026-11-13 にマージ済みで、Issue #415 は open のまま。Issue #400 に対応する open / merged の PR、branch、claim は無い。
- main の `tools/agent_runner/runner.py` は未変更で、安全指示は旧文のまま（302〜305 行）。
- 既存の F∩S テストは `tools/agent_runner/tests/test_runner.py` の `test_write_exceptions_follow_the_work_scope_lines`。`writes=false` の同一条先頭行を、write exceptions あり・なしで確認している。
- 変更前のベースライン（2026-11-14、worktree のルート）: `uv run --project . --locked pytest tools/agent_runner -q` は 305 passed、終了 0。`uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` は 18 passed、終了 0。ログは `/workspaces/reso-world/tmp/agents/issue-400.2wum565u/logs/baseline.log`。
