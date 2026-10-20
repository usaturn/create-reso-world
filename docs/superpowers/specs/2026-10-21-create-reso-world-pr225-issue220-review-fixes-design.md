# PR #225（Issue #220）のレビュー修正: サイクル 1

## 管理

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/225（`fix/issue-220-dsh-tmp-hardlinks`、base `main`）。閉じる Issue: #220
- 状態: completed
- 実装の Spec・Plan: `docs/superpowers/specs/2026-10-21-create-reso-world-issue220-dsh-tmp-hardlinks-design.md`・`docs/superpowers/plans/2026-10-21-create-reso-world-issue220-dsh-tmp-hardlinks.md`（どちらも draft）
- 実行許可: 2026-10-21（JST）、利用者が `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/220 --merge --assign implement=self` で着手を指示した。issue-to-pr の `--merge` により、PR の作成後に PR 修正ループ（pr-review-fix-loop、run `8055105af7114bb4a81a9668997eaa0b`）を回し、その計画の工程として review-fix-planning を完遂で実行する。完遂は、その PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う
- planner: claude-opus-5-5（claude-code）。サイクル: 1（この PR に判断の記録は無かった）
- DOC_ROOT・CODE_ROOT（専用の worktree）: `/workspaces/reso-world/.worktrees/issue-220-dsh-tmp-hardlinks`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD は PR の head と一致したので再利用した。片付けの対象にしない）
- 修正と自己レビューの担当（ループの `planning.run_roles_options`）: `implement` は `self`（利用者の指定 `--assign implement=self`）、`self-review`・`fix-check` は `self`（雛形の既定）。修正が無いので `run_roles.py` は使っていない

## レビュアーの構成

ループの `review` が agent-runner の workflow `review` の role `inspect` で 4 人を並行に起動した（割り当ては個人設定の適用）。claude-opus の 1 回目は、PR の head の fetch で `github.com` の名前解決に失敗し、pr-review が `failed` を返したので、ループが `payload` の段階で却下し、同じサイクルで 1 回だけ再実行した（再実行の前に、`github.com` の名前解決・`git ls-remote`・GitHub API が通ることを確かめた）。再実行の後は 4 人とも受け付けられた。1 回目の pr-review のセッション `/tmp/pr-review-225-faab078d` は、ループの `retained` として残っている。

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `59e63a61f9ae` | はい | Approve |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | claude-opus | `59e63a61f9ae` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `59e63a61f9ae` | はい | Approve |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | pi-gpt | `59e63a61f9ae` | はい | Approve |

## 指摘の一覧と振り分け

- 指摘は SWE-2-Max の I-1（Info）の 1 件だけ。ほかの 3 人は指摘 0 件。4 人とも未確認の候補は 0 件（候補一覧 `findings/<model>-59e63a61f9ae.json` は 4 件とも `validate`・`check-pair` を通過）
- 分類: 解消済み 0 / 対応する 0 / 対応しない 1
- 確認中に PR が持ち込んだ致命的な欠陥は見つからなかった（自己確認の指摘なし）
- 設計の見直しのきっかけ: なし（以前のレビュー修正が無い）

| 指摘 | 区分 | 根拠 | 見直す条件 |
| --- | --- | --- | --- |
| `SWE-2-Max#I-1@59e63a61f9ae`（`.devcontainer/README.md:597`・`tools/agent_runner/adapters/dsh.py:10-11` の「TMPDIR のハードリンクは消す」が、ディレクトリをまたぐ組で後に残る名前に触れない。`tools/agent_runner/runner.py:168` のコメント「never a target or the content」が不正確） | 対応しない | 記述の精度の問題で、致命的ではない。確認済みの一覧の V-1 で、記述どおりでない入力（親子・兄弟・3 つの名前の組、書き込めないディレクトリ）を実行して確かめたが、後に残る名前はリンク数 1 で redact され、消せなかったハードリンクは報告されて成功にならない。秘密の値の露出・データの消失・誤った操作や結果は起こらない。残る名前と順序は実装の Spec の D-220-2・D-220-7 と `_prune_scratch` の docstring に書いてある | TMPDIR に残る名前を手順・ツールが前提にするようになったとき、またはこの説明の誤解による誤った操作が報告されたとき |

実装の Plan の最終レビュー（opus のサブエージェント）が見送った Minor 4 件（同じ記述の精度の点を含む）は、このサイクルの入力ではない。Plan の「検証の記録」にある。

## 確認したこと

- 変更ファイルの全文（`git show 59e63a6:<path>` で `runner.py`・`adapters/dsh.py`・`.devcontainer/README.md`・`fake_cli.py`・`test_runner.py`・実装の Spec・Plan）と関連処理（`runner.py` の `_redact_runtime_tree`・`_dispose_home`・停止後の処理と state の決め方、`process.py` の `redact_file`、`adapters/dsh.py` の `prepare`、`dsh_sandbox.py` の `outer_command`・`main`）
- 確認済みの一覧（review-verify、mode cycle）: `reviews/usaturn/create-reso-world/#225-fix-issue-220-dsh-tmp-hardlinks/verified/59e63a61f9ae.json`（親の main checkout の下）。confirmed 1（V-1、文書の精度）・not_reproduced 0・unverified 0。`59e63a6` を detach で置いた隔離 worktree（`/tmp/review-fix-planning.GoGKBE`。確認の後に外して消した）で `_prune_scratch` と `_redact_runtime_tree` を直接呼び、次を確かめた
  - 同じディレクトリの組: 2 名とも消える。親子・兄弟・3 つの名前の組: 1 名がリンク数 1 で残り、内容は `[REDACTED]` に置き換わる。unsafe なし
  - 書き込めない（0500）ディレクトリの中の組: unlink に失敗し、2 名ともリンク数 2 のまま残って unsafe と報告され、内容は書き換わらない
- レビュアーが未実施とした範囲を、次のとおり閉じた
  - README の一括入口: 実装者が同じ HEAD の clean な feature worktree で実行した記録（3 本とも終了コード 0）を読んだ
  - リポジトリの実際のテストを偽の担当に実行させる再現: 実装者の `repro-base.json`（base は `response_failed`、Issue 本文と同じ 10 件）と `repro-fix.json`（`0ad7746` は `success`）を読んだ。`0ad7746` と `59e63a6` の差分は Plan の 1 ファイルだけ
  - 実際の DSH の担当（モデル）の起動: `AGENTS.md`「エージェント運用」で、本物の担当を起動する確認は Issue・Plan に書いた回数と対象に限る。Issue #220 と Plan は求めていないので対象外とし、上の再現で代えた
  - `st_nlink == 0` を返すファイルシステム: コードを読み、prune は消さず（`> 1`）、redact が報告する（`!= 1`）ので成功にならないことを確かめた。overlayfs などの `st_dev` は、この環境で作れず、既存の条件のままなので確認の残り（`coverage.remaining`）にした

## 結論

結論 2: 修正不要としてマージする。

### 検証

- head だけのツリー: issue-to-pr の 5 章の検証の記録を再利用した（1 サイクル目で修正不要、サイクルの HEAD が記録の HEAD と同じ、実行の前後とも `git status --porcelain` が空、すべての終了コードが 0、ログあり）。記録: `/workspaces/reso-world/tmp/agents/issue-220.z5vcohqb/verification-record.json`・`checks.json`（`finalize.py` の `--checks-file` には同じ内容の写しを使う）。HEAD `59e63a61f9ae0e14b5168a440a21f870a118979d`、base `4d41f1af42cee48cdf47124953d56797c0e0cad0`
  - `bash .devcontainer/run-tests.bash`: 0（`PASS: 33 test(s)`）
  - `bash scripts/check-layout.sh`: 0（`PASS: check-layout`）
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools`: 0（3520 passed）
- base の先端は `4d41f1a` のままで head の祖先なので、base を merge したツリーでの検証は要らない（状況の投稿と push の直前にも確かめる）
- CI: private のリポジトリの Actions は止めているので確かめない（`AGENTS.md`「GitHub Actions」）

### 自己レビュー

未実施（修正が無いため。`run_roles.py` は使っていない。自己レビューの回数 0）。

### PR の本文で参照しているだけの Issue

無い（PR の本文が参照する Issue は、閉じる #220 だけ）。

### 工程の記録

`reviews/usaturn/create-reso-world/#225-fix-issue-220-dsh-tmp-hardlinks/verified/59e63a61f9ae.planning.json`（状況コメントの投稿の後に更新する）。
