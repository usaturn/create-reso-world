# Issue #176 レビュー修正の収束改善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 要件の取り落としと原因の適用漏れを、既存手順の具体化で防ぐ。
**Architecture:** 共通の判断を `review-fix-planning/references/convergence.md` に置き、両スキルの計画・検証・公開判断へ接続する。新しい helper や帳票は作らない。
**Tech Stack:** Markdown、既存の JSON evals、既存 pytest・Bash 検証。
**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue-176-review-convergence-design.md` @ `ec93346`

## 管理・実行許可

- 状態: `draft`。文書管理・対象: `usaturn/create-reso-world` [#176](https://github.com/usaturn/create-reso-world/issues/176)。基準 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`。
- 利用者の `issue-to-pr #176` の実行許可で検証・commit・push・PR 作成まで進める。承認を捏造せず、マージしない。
- CODE_ROOT = DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-176-review-convergence`。PARENT_ROOT: `/workspaces/reso-world`。
- 実行方式: inline（executing-plans）。2 Task が同じ参照・判断条件を共有するため、担当ごとの実装より逐次の整合確認を優先する。読み取り専用の builder check・行動 pilot・最後のブランチ全体レビューは別の fresh context とする。

## Global Constraints

- AGENTS.md、review-verify、review helper、将来の修正ループ、#120 の全 SDD 向け移植、PR #173 のコードは変更しない。
- 致命的な指摘の採否、自己レビュー最大1回、権限・公開・マージの範囲は維持する。
- 文書の固定文言テスト・全件変異テスト・有料実機の反復を追加しない。
- 既存成果物を拡張し、全組み合わせや別帳票を一律に要求しない。
- 未実施の行動評価、main 反映、運用効果を成功扱いしない。
- 一時資料・ledger は `/workspaces/reso-world/tmp/agents/issue-176.ezhmi15b/` に置き、worktree 内には作らない。上流スキルの workspace/task-start/task-done/review-package スクリプトは worktree 内に一時成果物を作るため使わず、この ledger と同等の Task・BASE・検証・裁定記録で代える。

## Review Focus

- 共通前提のない単純変更を、別帳票・全件網羅へ膨らませない（Task 2 の小変更シナリオ）。
- 不正を拒否する修正で正常入力・拒否後の次操作を壊さない（Task 1 の両側検証、Task 2）。
- 正規化を変えた後に旧 HEAD のテスト成功を流用しない（Task 1 の公開前判断、pilot S2）。
- 同一原因の別経路を重複として捨てず、別原因・新要求も自動採用しない（Task 1 の二軸分類、Task 2）。
- fixture/fake が実装と同じ前提を共有しても、件数だけで信頼しない（Task 1 の独立した根拠、pilot S1）。

## 要件・検証の対応と統合担当

| Spec | Task・成果物 | 観測する結果・検証 | 担当 |
|---|---|---|---|
| A | Task 1、issue-to-pr の 4章・5章、共通参照の要件照合 | Task・検証・共有条件の所有者が対応し、保証を狭めない。pilot S1 と机上照合 | controller |
| B | Task 1、review-fix-planning の経路表 | 原因から経路を導き、3区分と理由を記録。Task 2 のシナリオ | controller |
| C | Task 1、共通参照と既存表 | 観測結果・現行版の証拠、両側・順序・独立性を扱う。pilot S1/S2 | controller |
| D | Task 1、公開前・自己レビュー | 原因の4分類と採否の3分類を混同しない。Task 2 と最終レビュー | controller |
| E | Task 1、既存の規則との diff | 採否・上限・境界・既存の対照検証を維持。最終レビュー | controller |
| F | Task 2、evals と convergence-validation.md | 同一packet、回答、限界、実施済み/未実施が区別される | controller |

両スキルの「完了」と共通参照の「証拠」が同じ意味であることは controller が統合確認する。ファイル別の成功をそのまま全体の成功としない。

### Task 1: 共通判断と既存2スキルへの接続

**Files:**
- Create: `.agents/skills/review-fix-planning/references/convergence.md`
- Modify: `.agents/skills/issue-to-pr/SKILL.md`
- Modify: `.agents/skills/review-fix-planning/SKILL.md`

**Interfaces:** 共通参照に要件照合、原因から経路、検証と閉じ方の節を作り、両スキルが相対パスで読む。Task 2 はこの手順を入力に評価する。
**テスト:** 新規 pytest 不要。文書手順だけであり、固定文言テストは作らない。改善前 pilot 実施済み（主要判断は満たすが、最終修正後・全経路の証拠の更新が不十分）。構造・参照検査と改善後 pilot で代える。

- [ ] BASE を ledger へ記録し、既存の経路表・採否・自己レビュー・公開規則を読む。
- [ ] 共通参照を書く。観測可能な条件から要件対応・因果経路を作り、両側・順序・期待値の独立性・現行版証拠を既存の表へ記す方法を定義する。
- [ ] issue-to-pr の Plan 作成時・実装指示・統合検証で参照を必読にする。
- [ ] review-fix-planning の経路表を拡張し、自己レビュー・公開前に原因単位で照合する。採否・上限・権限の規則は変えない。
- [ ] skill-efficiency-check を両スキルへ `uv run --no-project python <installed-script> <skill-dir>` で実行し、参照先を確認。Expected: 構造エラーなし（既存由来の warning は記録）。`git diff --check`。明示パスで commit。

### Task 2: シナリオ・比較記録・全体検証

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`
- Modify: `.agents/skills/review-fix-planning/evals/evals.json`
- Create: `.agents/skills/review-fix-planning/evals/convergence-validation.md`
- Update: 本 Spec・Plan の結果節

**Interfaces:** Task 1 の指示を改善後 packet に使用。既存 JSON の method・履歴は書き換えず、追加ケースの評価方法を別に明記する。
**テスト:** 新規 pytest 不要。evals は行動シナリオであり SKILL.md の文字列テストではない。JSON の構文・ID重複・参照実在、既存 helper テストと README の検証で代える。

- [ ] 要件欠落・共有条件・小変更、経路の適用漏れ・両側・独立性・原因分類・最終版証拠を扱う計9ケースを既存evalsへ追加。
- [ ] baseline と同じ2シナリオを新しい sp-research に渡す。今回は2スキルと共通参照のみ読み取りを許可し、採点基準・他版回答は渡さない。Expected: 必要な経路を未確認で閉じず、現行版の両側検証と統合を具体化する。改善が認められない場合も記録し、効果を捏造しない。
- [ ] convergence-validation.md に packet・生の回答・人手での比較、旧対策との差分、机上照合、未実施範囲を保存する。
- [ ] 下記の最終検証を同期実行し、終了コード・実ログを読む。Expected: exit 0。失敗は systematic-debugging で原因を調べ、解消不能なら停止。
- [ ] 明示パスで commit、最後のブランチ全体レビューを sp-review で1回実行。Critical/Important は1回の修正と再検証、2回目のレビューはしない。結果を Spec・Plan に追記。
- [ ] Issue の open・全ページのPR/コメント/予約・同番号branch/worktreeを再確認し、自分の作成物と区別する。scan-before-push が出す SHA のみ push、`--repo usaturn/create-reso-world --base main --head fix/issue-176-review-convergence` で PR 作成。CI は private のため確認しない。マージしない。

## 検証の入口

```bash
uv run pytest tests/skills .agents/skills/review-fix-planning/tests .agents/skills/issue-to-pr/tests
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
# 加えて JSON/ID・参照実在・skill-efficiency-check、git diff --check
```

ログは session 配下に保存し、最終の要約を本書・評価記録・PRへ転記して session を片付ける。worktree と branch は PR 用に残す。

## 実行予算

- 能動時間90分（開始 2026-10-18 21:33 UTC、ledger start は 21:34 UTC）。準備・設計20分、文書編集20分、評価と検証35分、レビュー・公開15分。利用者待ちなし。
- 実モデル呼び出しは最大5試行: baseline、builderのscope拒否、builder再送、改善後pilot、最終レビュー。追加の実機・モデル反復なし。拒否された試行をレビュー実施と数えない。
- pi の同期 role tool は deadline/stop を指定できない。期限・予約枠・無進捗の事前打ち切り宣言は付けられないため、偽の宣言はしない。各担当への作業目安5分・終了保存1分、foregroundで終了を待つ。stall時に勝手にkillしない。検証にも打ち切りを適用しない。
- 同じ信頼性失敗の再試行は1回まで、以後は方法変更。安全の失敗は再試行せず全体停止。
- checkpoint: phase境界、50%・100%、worker失敗直後。ledger は `/workspaces/reso-world/tmp/agents/issue-176.ezhmi15b/budget.jsonl`。100%で停止し延長しない。
- contingency: 評価が不鮮明なら改善効果 unknown として資料を残す。検証が環境で止まるなら原因と残作業を報告し、成功・PR作成にすり替えない。新規管理ツールや追加モデル評価へ拡大しない。

## 完了記録

- Task 1: 完了。BASE `dfd9a1d`、手順実装 `442d78c`。共通参照・両スキルを接続し、構造検査両方exit0・参照確認・diff check・同一2ケースの両条件pilotを実施。
- Task 2: evals 9件と評価記録を追加。JSON: 18件／20件、ID重複なし。READMEの非ワールド3コマンド: pytest **2568 passed / 1 skipped / 626.14秒 / exit0**、環境 **33件PASS / 444.9秒 / exit0**、layout **PASS / exit0**。ログを確認済み。
- 主要Taskの壁時計: 準備・設計 21:33〜21:43 UTC（約10分）、Task 1 の手順・pilot 21:43〜21:45（約2分）、Task 2 の評価記録・全体検証 21:45〜21:57（約12分）。担当個別の所要時間はrole toolから返らず不明、並行検証時間は二重加算しない。
- 予算checkpoint: 約23分／90分、失敗上限未到達、安全の失敗なし。受け入れ条件A〜Fの成果が増えたため継続。
- 裁定: upstreamのworkspace管理スクリプトの代わりに親tmpのledgerを使用。理由はworktree内の未コミット成果物を禁じるAGENTS.md。取りこぼしのリスクをTask・BASE・検証・裁定の明示記録で補った。他のセッションの作業物は触っていない。
- 最終レビュー・公開は未実施。状態は実行許可と内容承認を区別するため draft のまま維持し、結果を追記する。
