# Issue #364: checkout 監査の説明の整合

## 管理・実行許可

- 状態: `completed`（review-fix-planning の修正・検証完了。実行許可であり、内容の承認ではない）
- 対象: usaturn/create-reso-world#364
- 利用者の指示: `#364 --merge --assign inspect=claude-code_opus_default`（issue-to-pr の明示入口）
- 許可: 推奨案の選択、文書修正、検証、commit・push・PR、指定のレビュー修正ループと finalize.py によるマージ。
- 基準: origin / refs/heads/main / `7f008486fdf43d9d79b84d0adcde02fc4e41d8ef`。Issue 本文と coordinator の [決定](https://github.com/usaturn/create-reso-world/issues/364#issuecomment-6743480154) は main を要求する。先行 #350 は PR #362 でマージ済み。#364 はボードの子ではない。

## 意図と範囲

#350 後の `tools/agent_runner/interfaces.rst`「期限と保持」と食い違う4か所の説明だけを直し、利用者・controller が `unprotected_changes` を確認できるようにする。

- `.agents/monitoring-runtimes.md`: agent-runner の同期実行と停止確認の末尾。
- `.agents/skills/pr-review-fix-loop/references/records.md`: `review.batch` の表の1行。
- `.devcontainer/README.md`: cursor の `writes = false` の段落。
- `docs/agent-runner-checkout-recovery.md`: 冒頭段落。

実装、テスト、設定、回収手順、ほかの段落、#350 の過去の Spec・Plan は変更しない。workflow で必須の本 Spec・Plan だけは同じ PR に含める。

## 必要な説明

1. runner が保護するのは依頼の `repository` の checkout。特定できなければ全登録を保護する。main worktree も対象でなければ保護しない。
2. 保護する checkout の変化・消失・監査不能は `outside_changes` で、受け取り入口が拒否する。runner 自体は観測を警告として返す。
3. 保護しない checkout（main worktree も、依頼対象でなければ保護しない）の内容の変化・回収・監査不能は `unprotected_changes`。報告のみで起動・受け取りを止めず、利用者・controller が確認し必要なら成果を確かめ直す。
4. 他セッションと担当による変更の因果を断定しない。既存の注意を残す。
5. `review.batch` には両方の項目を説明し、`unprotected_changes` が古い記録には無いことを示す。

各文書で定義を複製するのではなく、その利用場面に必要な情報を記す。保護対象を特定できない場合の全登録という例外は、保護対象を説明する文に併記する。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由 / 委任・停止条件 |
| --- | --- | --- | --- |
| 修正範囲 | 4か所を現在の仕様に合わせる | 監査説明全体の再構成、実装変更 | Issue の推奨案に合い、後続 #353・#356・#357 の所有を侵さない。仕様の意味や範囲が変わるなら停止 |
| 実装担当 | `self` / executing-plans、1 Task | SDD のファイル別実装 | implement_task.py check の既定適用。単一の意味を4か所に反映する小変更なので直列で統合する |
| 検証 | 差分・仕様との意味照合・既存検査 | 文言固定テスト | 文書の固定値は AGENTS.md の F。新規テストは不要 |
| レビューループ | inspect は利用者指定の `claude-code_opus_default` | 既定の複数レビュアー | check-options 成功。max_cycles=3 は既定適用。fix.implement=`claude-code_opus_default`、fix.self-review / fix.fix-check=`self`、fallback はいずれも空（既定の適用） |

## 受け入れと検証

Dev Container の専用 linked worktree で日本語の4段落を編集する。保護対象、別 checkout、特定不能、古い記録の各場合を現行 interfaces.rst と意味で照合する。`git diff` が上記4か所と本 Spec・Plan のみであること、`git diff --check` と `bash scripts/check-layout.sh` の終了コード0を確認する。README の共通検査も実行し、結果を PR とセッションの検証記録に残す。

文書からコードの挙動変更や sandbox の保証を導かない。実 CLI の追加評価、回収・repair・削除、後続 Issue の開始は対象外。

## 実行記録（PR 作成前）

- Task 1 は `80c299b126d8463054e6c80dc2c22da65d35131a` で実装。指定4か所だけの差分（7行追加・5行削除）を条件1〜5と意味で照合した。
- `git diff --check`、`bash scripts/check-layout.sh` は終了コード0。新規テストなし（F）。独立した全体レビューは Critical / Important / Minor いずれも0件。
- レビュー子の初回依頼は scope 宣言の不足で未実施。`Review scope: branch` を追加して再送し、全体レビューを完了した。追加の内容裁定・保留項目はない。
- 最終 clean HEAD での共通検証は、この記録の commit 後に行い、結果を PR と `/workspaces/reso-world/tmp/agents/issue-364.95_cvygq/validation.json` に記録する。未実行の検査を成功とは記載しない。
- Task・意味照合・独立レビューの証拠は同セッションの `task-1.diff`、`task-1-layout.log`、`branch-review.md`、`sdd/2026-11-09-issue-364-checkout-audit-docs/progress.md`。

## PR #371 / サイクル1のレビュー修正

実行許可は冒頭の `--merge` による完遂。planner は `gpt-6.1-sol` / pi。既存の本 Spec を更新し、別の Spec は作らない。

| レビューファイル | モデル / runtime | 対象 HEAD | 今回実行 | 結果 |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `2e841135901f` | はい | Approve、Info 1件 |
| `gpt-6.1-sol-commit-cbbb94ff7c0c9937042eedf50ab895868b7d4bb8.md` | gpt-6.1-sol / pi | `cbbb94ff7c0c` | 修正後の自己レビュー1回 | Approve、新規指摘0件 |

### 全指摘の分類と要件対応

- **対応する1件**: `claude-opus-5-5#I-1@2e841135901f`。loop review は `tool_root`（普段は親の checkout）を repository として渡すため、親の変化は `outside_changes` に入る。親を非保護側へ無条件に含める説明では controller が通常の経路で誤った欄を確認するので、事実誤認として採用した。Info の表記は採否の根拠にしていない。
- 解消済み0件・対応しない0件・未確認0件（初回の採否）。修正後の fix-check で原指摘は `not_reproduced`、新規指摘なし。
- 既存の条件1〜5と範囲は維持する。親が対象の場合も条件1に含まれていたため、意味を変える設計変更ではなく、その条件を4か所に正確に反映する修正。統合担当は controller。
- 同じ守る条件の過去のレビュー修正はなく、再発・修正起因の回帰・自己レビューでの再発には当たらない。

### 守る条件と影響経路

| 守る条件 | 経路 | 判定・観測結果 | 検証・証拠 |
| --- | --- | --- | --- |
| repository の checkout を保護、特定不能なら全登録 | loop review → tool_root → snapshot/audit → 両区分 | 既に満たす。親対象は親が outside、linked 対象は親が unprotected | 現行 HEAD の隔離fixtureで両側を実行、特定不能は fake `_toplevel=None` で全登録を確認。`i-1-reproduction.log` |
| 文書が同じ確認先を案内 | 指定4か所 → controller・利用者 | 修正済み。records は tool_root が保護側と明示、他3か所は親が依頼対象でない場合に限定 | 修正 commit `cbbb94ff7c0c9937042eedf50ab895868b7d4bb8` と interfaces.rst・loop.py の引数を意味照合。fix-check の4主張・4ファイル・57候補を確認 |
| 旧記録・因果の注意・実装は不変 | 4か所 → 既存の記録・回収手順 | 既に満たす。古い記録への注記と因果断定不可を維持 | 差分は4か所のみ。実装・設定・テストの blob に差はなく、影響しない既存検証の前提は不変 |

### 実行・検証・自己レビュー

- 修正担当: 設定の既定 `claude-code_opus_default`、実観測モデル `claude-opus-5-5`。1依頼、747.0秒、終了コード0・停止確認済み。4か所だけの修正を controller が取り込んだ。
- 初回 clean HEAD `2e841135901fed828b629ab7bf6fb1821ca946cc`: Bash27件、pytest1,354件、layout/diff はすべて終了コード0。
- 修正後 clean HEAD `cbbb94ff7c0c9937042eedf50ab895868b7d4bb8`: controller が Bash27件、スキルpytest726件、layout/diff を再実行してすべて0（`fix-1-validation.json`）。実装・設定は不変なので、初回の tools/.agents/scripts 成功は影響しない経路の証拠として保持する。
- `run_roles.py --phase self-review` は1回。self-review / fix-check は設定どおり `self`、観測モデル `gpt-6.1-sol`。観点2のPR全体レビューは指摘0、観点1の反証と観点3の検出力は原指摘解消・新規テスト不要(F)・未確認なし。自己レビュー後の実装修正はなく、2回目の自己レビューは実施していない。
- 確認済み一覧と工程記録: `reviews/usaturn/create-reso-world/#371-fix-issue-364-checkout-audit-docs/verified/2e841135901f.json`・同 `.planning.json`、`cbbb94ff7c0c.fix-check.json`。自己レビューの保存・cleanup は成功。詳細ログは親の `tmp/agents/issue-364.95_cvygq/`。
- 結論1: 修正して既存 PR へ反映する。push・コメント・次サイクル・マージの結果は実行後の状況コメントと最終報告に残す。
