# Issue #176: レビュー修正の原因単位の完了判断

## 管理・実行許可

- 文書管理・対象: `usaturn/create-reso-world`、[Issue #176](https://github.com/usaturn/create-reso-world/issues/176)
- 状態: `draft`（内容の承認は得ていない。issue-to-pr の実行許可で進める）
- 利用者の指示: `issue-to-pr` スキルを明示して `#176` を指定。スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」を適用する。マージはしない。
- 基準 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-176-review-convergence`
- PARENT_ROOT: `/workspaces/reso-world`
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue-176-review-convergence.md`
- Issue が記録する旧ローカル版の worktree・branch は現在存在しない。旧版やその検証結果を復元・流用せず、現行 main から作成する。

## 目的と範囲

適用漏れ、回帰、共通の誤前提を次のレビューで発見し続ける循環を減らす。既存の表・検証・公開前判断を具体化し、別帳票や新しい進行管理ツールは作らない。

変更対象は `issue-to-pr` と `review-fix-planning` の手順、その共通参照資料、既存 evals。AGENTS.md、review-verify、review helper、将来のレビュー修正ループ、PR #173 の実装、#120 の全 SDD 向け規則は変更しない。#5・#120・#156 は関連テーマであり本作業の未完了の先行条件ではない。#173 はマージ済み。親 Issue・blocked_by・コメント・open PR・claim ref・既存の同番号 branch/worktree に競合は無い。

## 受け入れ条件

- A: Spec の条件・除外範囲を Plan の Task・検証へ対応付け、保証を狭めていないか実装前に照合する。別担当・別ファイルの共通入力、状態、順序、外部仕様の確認を統合担当へ割り当てる。
- B: 原因を「破れた前提と境界・操作順」で記述し、入口、変換、読取・書込、副作用、終了・復旧を因果関係のある範囲で追う。各経路を修正する／既に満たす／対象外に分類する。
- C: 修正する・既に満たす経路には観測結果と実行証拠を対応付ける。判定の拒否側・正常側、意味のある前後操作・中断・復旧、fixture/fake/期待値の独立した根拠を確かめる。文書変更は構造・参照・シナリオ判断の証拠で代える。
- D: 後続指摘を既存原因の適用漏れ／修正による回帰／別の原因／新しい要求に分ける。finding の採否三分類とは別軸とし、ID の一致や上限到達で解消扱いしない。最後の修正で影響する経路の証拠を更新する。
- E: 致命的な指摘の採否基準、自己レビュー最大1回、権限・公開・マージの境界を維持する。既存の安全ガードの対照検証は維持し、全件変異テスト・有料実機反復・文面一致テストを追加で必須にしない。
- F: 特定実装に依存しない評価シナリオと、実施済み・未実施を分けた評価記録を残す。机上確認や既存 pytest の成功を行動改善・main 反映の実証と呼ばない。

## 設計

`review-fix-planning/references/convergence.md` に A〜D の判断をまとめ、issue-to-pr は Plan 作成時・実装指示時・統合検証時に、review-fix-planning は原因分類・経路表作成時・自己レビュー・公開前に必要な節を読む。既存の経路表を拡張し、計画中の方法と実行済みの結果を区別する。単純な変更は既存 Plan/Spec/ledger に短く書き、全組み合わせの列挙を求めない。

共有参照の完了判断と両スキルの公開前判断が同じ保証を指すことは統合担当が確認する。個別のファイルレビューだけでは完了にしない。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|
| 既存手順に少数の必須の読み込み点と共通参照を追加 | 両スキルに全文を複製、新しい管理ツール/schema | 同じ条件と証拠の意味を維持し、重複・帳票を増やさない | issue-to-pr の通常設計判断の委任。参照不能なら公開しない |
| 初回から要件照合・因果経路・両側検証 | 再発時だけ設計見直し、レビュー回数増加 | 問題を次のレビューまで残さず、既存の再発時の規則を補う | A〜D は Issue 採用案。採否・自己レビュー上限は維持 |
| 同じ原因でも未確認経路を閉じない | 同系指摘の一括重複扱い、回数で強制成功 | 適用漏れと回帰を見分け、証拠の不足を隠さない | 実行結果が無ければ未確認。権限外の操作はしない |
| 文書に pytest は追加せず、既存テスト・構造検査・行動 pilot | 固定文言テスト、有料実機・全件変異テスト | AGENTS.md と Issue のテスト基準を守る | 未実施の行動評価を成功扱いしない |
| inline 実装と独立した読み取り専用評価・レビュー | Task ごとの別担当実装 | 共通参照と2スキルを逐次整合させる小規模文書変更 | executing-plans、最後のブランチ全体レビューは必須 |

## 検証・評価の境界

既存関連テストの baseline は 180 passed / 25.64 秒 / exit 0。新たな pytest は作らない。最終検証は README の非ワールド3コマンド、関連 helper テスト、JSON/ID・参照先・skill-efficiency-check・diff check。

行動評価は読み取り専用の意思決定シミュレーションのみで、実装・外部APIの操作能力を評価しない。モデル起動の試行は baseline 1、改善後1、builder check 2（最初の sp-review は scope 不足で拒否され、sp-research で再送）、最終レビュー1の合計5回までとする。拒否された試行を完了したレビューとは数えない。同一の2シナリオを baseline と改善後の fresh context に与える。本文作成前に baseline を実施済み。baseline は多くの目標行動を既に満たしたため、改善幅や統計的な効果は主張できない。改善後 pilot は本 run で実施する。シナリオは `.agents/skills/issue-to-pr/evals/scenarios.json` と `.agents/skills/review-fix-planning/evals/evals.json` へ追加し、共通の記録先 `.agents/skills/review-fix-planning/evals/convergence-validation.md` に実施方法・同一 pilot packet・両版の生の回答を保存する。baseline の生の回答は `/workspaces/reso-world/tmp/agents/issue-176.ezhmi15b/baseline.md` に確保済みで、終了前に記録先へ転記する。モデルの正確な識別子は tool が返さないため不明とし、異なるモデルの比較とは呼ばない。builder check の質問3件は、以上の保存先・改善後 pilot の実施・入力の固定で解消する。5反復以上の wording 比較・別モデル横断評価・実運用の退行評価は未実施と明記する。

## 結果

作業中。実行結果・最終レビュー・公開状態は完了時に追記する。main 反映・運用効果は本 run の完了条件にせず、未実施のまま記録する。
