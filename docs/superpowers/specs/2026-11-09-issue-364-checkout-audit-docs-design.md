# Issue #364: checkout 監査の説明の整合

## 管理・実行許可

- 状態: `draft`（実行許可であり、内容の承認ではない）
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
3. main worktree を含む保護しない checkout の内容の変化・回収・監査不能は `unprotected_changes`。報告のみで起動・受け取りを止めず、利用者・controller が確認し必要なら成果を確かめ直す。
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
