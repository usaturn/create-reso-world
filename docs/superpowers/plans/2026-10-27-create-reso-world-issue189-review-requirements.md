# Issue #189 レビュー修正前の要件照合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正前の要件対応と保証変更の委任確認を既存の review-fix 手順へ接続する。
**Architecture:** 共通参照1章を初回実装とレビュー修正に共用し、SKILLの分類後・経路表作成前と implement prompt の引き渡しを接続する。
**Tech Stack:** Markdown、既存eval JSON、既存検証コマンド。
**Spec:** `docs/superpowers/specs/2026-10-27-create-reso-world-issue189-review-requirements-design.md`
**状態:** draft。利用者のissue-to-pr実行許可で進め、承認済みとは記録しない。

## Global Constraints

- 採否、計画のみ／完遂、自己レビュー最大1回、公開・マージ権限、既存の補助指示2〜6は変えない。文言一致のpytestを追加しない。
- 既存 Spec 内の対応メモと経路表を使い、新しい帳票・helper・schema は作らない。
- RoleInput の5キーは変えず prompt 内の情報とする。

## Review Focus

1. 経路表を作ってから要件を読む逆順にならない（C1、Task 1シナリオA）。
2. 計画のみと完遂、範囲内／外の縮小を混同しない（C3、シナリオB）。
3. 既存文書が無いPRでも虚構のSpec・承認を作らない（C1、机上追跡）。
4. issue-to-prの担当Task割当・共有条件を退行させない（C2、参照元照合）。
5. promptの情報を増やすためにRoleInputのschemaを変えない（C4、差分確認）。

## 実装前の要件照合

| 条件 | 担当／対応 | 観測と方法 |
|---|---|---|
| C1 | Task 1、SKILL手順4＋既存Specの必須内容、共通参照1章 | 要件対応→経路表→方針の順をシナリオAと構造で確認 |
| C2 | Task 1、共通参照1章、execution1章 | 統合担当の役割・共有前提と検証を渡す。controllerが共有の用語・順序・参照を確認 |
| C3 | Task 1、設計見直し手順3 | 委任なし／あり、計画のみをシナリオBで対比 |
| C4 | Task 1、execution1章 | 除外範囲・共有前提・必要証拠がpromptにありschemaは不変 |
| C5 | Task 1、全差分 | 既存の分類・回数・権限を変更せず、pytestを追加しない |

## 実行方式・予算

SDD、1 Task、同期のsp-implementer、task review、その後branch review。taskScheduling=parallelだが、3文書が共有する順序・用語を同時に変えるので1つの依存waveとする。別Taskのworktreeは不要、専用feature worktreeで行う。

能動時間240分。準備・設計30分、実装・行動確認30分、検証・レビュー30分、PR10分、ループ最大3×約45分＋修正5分。子は実装目安25分（保存5分）、評価・レビュー目安10分（保存2分）。同期APIで生存中の実装子をkillせず、起動前宣言のない強制停止をしない。CLIレビューの期限はrunnerの45分を使う。
同種の信頼性失敗は再試行1回、レビュー修正はSDD上限、PRループは3サイクル。安全の失敗・Issue予算100%は停止。phase境界・50%・100%・worker失敗直後にcheckpoint。縮小候補は追加シナリオや表現整形だけで、C1〜C5は落とさない。独立評価で改善未観測なら未実証と記録し、検査を成功にしない。SESSIONは `/workspaces/reso-world/tmp/agents/issue-189.rfny9g8t`、SDD領域はその `sdd/issue189-review-requirements/`。ループ用検証ログは終了まで保持する。

### Task 1: 要件照合・委任確認・引き渡しを一体で接続する

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`
- Modify: `.agents/skills/review-fix-planning/references/convergence.md`
- Modify: `.agents/skills/review-fix-planning/references/execution.md`
- Modify: `.agents/skills/review-fix-planning/evals/evals.json`（2件だけ追加）
- Modify: `.agents/skills/review-fix-planning/evals/convergence-validation.md`（今回の限定評価・構造確認を追記、過去の記録は変更しない）

**Interfaces:** PRの約束・制限、既存Spec・Plan、今回の修正方針／検証を入力に、既存Specの要件対応と経路表、implement promptを出力する。controllerが全体の順序・入力・委任根拠・共有条件を統合確認する。

**テストの要否:** pytest追加なし（F/L）。文書の行動確認・参照の実在・JSON解析・diff・既存検査で代える。

- [x] Step 1: 変更前シナリオの回答要約 `SESSION/baseline.md` を読む。保証縮小の行動失敗は未観測と保ち、前提条件の順序不足と既存の読取経路を確認する。
- [x] Step 2: 共通参照1章にreview-fixでの入力と対応先を追加し、初回実装のTask割当を維持する。SKILL手順4で分類→要件対応→経路表→方針の順に接続し、要件対応を既存Specの必須内容へ含める。
- [x] Step 3: 設計見直し手順3に保証を狭める案の選択前の委任確認と根拠記録を置く。範囲外の完遂は元の保証維持、計画のみは既存承認手順。開示だけでは許可にならない。
- [x] Step 4: execution1章のpromptに条件・除外範囲・共有前提・統合担当の確認と必要な証拠を追加する。RoleInput、helper、frontmatterは変更しない。
- [x] Step 5: evalsへ2ケース追加、validationへ変更前の限界と構造確認を追記する。controllerが同じケースを変更後の新しい子で1回確認し、結果を記録する（実装子は別agentを起動しない）。
- [x] Step 6: 変更対象のMarkdown相対リンク先の実在、JSON/ID一意性、`git diff --check`、`uv run --no-project python /home/vscode/.pi/agent/npm/node_modules/@howaboua/pi-skill-skill-creator/skills/skill-creator/scripts/skill-efficiency-check.py .agents/skills/review-fix-planning` を確認する。フル検査はcontrollerが最終記録後に同期で実施する。`uv run pytest tests/skills .agents/skills` を実装子で1回通す。
- [x] Step 7: 許可した5ファイルだけstageして `docs: connect review-fix requirement and delegation checks` でcommit。自己確認、コマンド・結果・所要時間をreportへ記す。Planの完了チェックはcontrollerが行う。

## 統合・公開

controllerが変更後行動確認、task review、SpecとPlanの全条件照合、branch reviewを実施。SDD領域を片付けてfinishingスキルで既に指定済みのPR作成へ進む。最終commit後、clean HEADでREADME非ワールド3コマンド、diff・参照を検証し、HEAD・base・argv・終了コード・ログをSESSIONへ残す。Issueの競合を再確認しGitleaks検査付きpush、PRを作成（Closes #189）。親checkoutのloop.pyに利用者が指定した `--max-cycles 3` だけ渡しレビュー・修正・finalizeを実施する。モデル不明、ツール・API障害、競合は所定の停止条件で報告し迂回しない。

## 実装・検証記録

- Task 1 commit: `627402a`。指定5ファイルのみ、実装22分48秒（うち関連pytest6分54秒、全体pytest7分03秒）。関連697件／全体1237件が成功、diff・参照・JSON・checker成功。未変更descriptionのwarning1件は維持。
- 変更後の限定シナリオは同一2ケースを1回、54.4秒。保証維持・委任境界・共有担当を提案したが、Aは分類前に要件照合を置く順序不一致があった。全面的GREEN・改善効果・運用収束は未実証と評価文書に記録。
- task review: 仕様適合、品質Approved、Critical/Importantなし。順序不一致と既存warningは検証の限界として記録した。最終HEADのREADME3検証とbranch review、公開・ループの結果はセッションのログ・PRコメントで記録し、未実施を成功と書かない。
- 文書の実装上のC1〜C5はTask 1と構造照合で対応。モデルの完全遵守や運用改善の効果は保証しない。
