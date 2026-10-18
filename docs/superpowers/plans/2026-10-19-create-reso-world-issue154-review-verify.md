# Issue #154 review-verify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 全レビュアーの候補をコミット済み内容で確認する cycle と、push 前の fix_check を移植する。
**Architecture:** 既存 review_findings/review_target と agent_runner を利用する。入口 SKILL.md からモード別参照へ進み、fix_check の外部実行と受け取りは dispatcher が担当する。
**Tech Stack:** Python >=3.14、uv、pydantic、pytest、git、Markdown。
**Spec:** `docs/superpowers/specs/2026-10-19-create-reso-world-issue154-review-verify-design.md`

文書管理・対象: usaturn/create-reso-world #154。基準 HEAD `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`。状態 `draft`。内容承認は未記録、実行許可は Spec 冒頭。実行方式は利用者指定の SDD。専用スキルと dispatcher は別の検証単位なので2 Taskにする。

## Global Constraints

- 変更は `.agents/skills/review-verify/` と `.claude/skills/review-verify`、この Spec/Plan に限る。
- 根拠はコミット済み HEAD と隔離実行。採否・重大度の再評価・修正設計・push 可否を決めない。
- 失敗・時間切れ・環境不足は `unverified` と `missing_checks`。票数を根拠にしない。
- `repository`, `from`, `to`, `fix_ids`, `fix_sections`, `verified_file`, `review_dir` が fix_check の7入力。
- 出力は `review-findings/v2`、保存先は D-10 の `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/verified/`。
- root の uv 環境を使い、tools/devenv・tools/workspace・projects.toml・checkout の探索/clone は入れない。
- 共有雛形は変更しない。fix workflow は明示した config で供給する。
- scratch・レポート・ログは親 checkout の `tmp/agents/issue-154.c3b8xs2c/`。worktree 内にはコミットする成果物と再生成可能キャッシュだけを置く。

## Review Focus

- JSON と Markdown の候補数・対象 PR の不一致: cycle は Markdown に戻って coverage を残す（Task 1 の行動評価）。
- 手元修正と未入力の計画: HEAD と7入力だけを使う（Task 1 の行動評価、Task 2 の入力テスト）。
- 停止未確認・checkout 監査不能: 成功や無変更として受け取らない（Task 2）。
- 保存先 symlink・起動後の変更: リンク先を書かず受け取りを拒否する（Task 2）。
- payload と inventory の欠落・改変、identity 未観測: 検査で拒否または unknown にする（Task 2）。

## 実行予算

Issue 全体180分（前回消費約10分、今回残170分）。準備・設計25分、Task 1 25分、Task 2 55分、レビュー/修正35分、全検証/PR30分を目安とする。予算 ledger は上記 session の budget.jsonl。前回 ledger は ended のため変更せず、残予算で新規開始済み。

worker は Task 1 25分、Task 2 55分、レビュー各15分を目安とし、末尾5分を報告保存に使う。共有worktreeの実装workerと検証コマンドは打ち切らず、終了まで監視する。読み取り専用の委譲もこの run では強制停止せず、無進捗10分なら状態を確認して保存を依頼する。実質進捗・レポート・agent状態を確認し、10分ごとの観測を残す。

同じ信頼性の失敗は再試行1回まで、上限で方法変更。安全の失敗は全体停止。phase 境界、50%、100%、失敗直後に checkpoint。100%で停止して残作業を報告する。contingency: dispatcher の問題は独立した失敗条件ごとに修正、実機の可用性に依存する評価は fake adapter と対話委譲で境界を検証し、未実施の実機確認は成功扱いしない。受け入れ条件の縮小は記録して報告する。

### Task 1: スキルの入口・cycle・fix_check 手順と行動評価

**Files:** Create `.agents/skills/review-verify/SKILL.md`, `references/cycle.md`, `references/fix-check.md`, `evals/evals.json`, `evals/validation.md`; create relative symlink `.claude/skills/review-verify` → `../../.agents/skills/review-verify`。

**Interfaces:** Consumes existing `.agents/review-findings.md`, `review_target.py`, `review_findings.py`, upstream exact files in session `upstream/`。Produces both mode workflows and dispatcher CLI documentation with the exact seven inputs from Global Constraints. Task 2 implements that CLI; do not create a fake dispatcher in this task.

テスト: 文書・symlink の文字列照合テストは不要。スキル構文、参照の実在、実行による cycle fixture と無し/あり行動比較で確認する。

- [x] baseline `/workspaces/reso-world/tmp/agents/issue-154.c3b8xs2c/baseline-eval.md` を読む。採否・push 判断を担当した誤りと出力形式の欠落を評価項目にする。upstream を参照し、この環境に必要な情報だけ残す。
- [x] 入口と参照を実装する。resolver の clone / 登録済み submodule / tools/devenv / 別owner一律拒否を移植しない。未知対象の明示 --code-root と番号/URL経路での候補PR照合を書く。cycleの未読候補の手動回収、隔離実行、別入力/文書/PR起因、v2形式、保存、後片付けを保つ。
- [x] fix_check は upstream の完全入力、主張・全変更ファイル・文書候補の全件照合、時間、self/外部、観測 identity、accept、エラー分類を保つ。詳しい形式は既存 helper 文書を参照する。実在しないスキル・仕様へのリンクを作らない。
- [x] 一意の fixture git repo と D-10 の保存先を session 内に作り、review_findings helper で v2 cycle 一覧と要約を作成・validateする。証拠はコミット済み版から取り、例には fake 情報だけを使う。再実行手順を evals に記録する。
- [x] controller が同じ pressure scenario を新しい評価agentに skillありで実行させる。実測結果を validation.md に記録し、baseline/ありを比較する（未実施を成功と書かない）。この追記は同じ Task の完了前に行う。
- [x] quick_validate.py、構造/リンク検査、git diff --check、check-layoutを実行。dispatcher は Task 2 の未作成出力なので参照先検査の保留事項として報告する。変更パスだけ commit、自己レビュー、所要時間/検証を task-1-report.md に報告。

### Task 2: fix_check dispatcher と実行テストの移植

**Files:** Create `.agents/skills/review-verify/scripts/dispatch.py`, `tests/test_dispatch.py` (必要なら同 tests 内の conftest.py)。Task 1 文書の実装との不一致があれば同 skill 内で直す。

**Interfaces:** Consumes Task 1 skill bytes (SHA256), seven-input request, existing `tools.agent_runner` / `tools.agent_runner.config.validate_config` / workspace audit APIs, existing review_findings. Produces upstream-compatible dispatch/accept functions and CLI, dispatch.json, validated fix-check JSON/sidecar. Use downloaded source `upstream/scripts/dispatch.py`, `upstream/tests/test_dispatch.py` as reference. Do not read whole Plan; task brief and Global Constraints suffice.

テスト: 実行ロジック・安全条件・入出力があるため必要。文面一致や一覧の丸写し検査は移植しない。fake adapter が実際に subprocess と runner を動かし、fixture gitは実環境 GIT_* を継承しない。

- [x] 移植する実行テストを先に作り、dispatcher 未作成時の失敗を観測する。実装がないという意味の失敗を記録し、importミス等だけの失敗にしない。
- [x] dispatcher を移植する。uv例外は root `.venv` と uv cache に変更。selfは完全入力を返すだけ、外部は fix-check だけ。7入力不足/余分/不正、完全SHA、非空Fix節/IDを拒否する。
- [x] 上流の停止確認・checkout監査・review_dir snapshot/リンク拒否・inventory照合・validate・観測identity/期限を保持する。設定がまだ無いときは一時configでテストし、共有設定を追加しない。
- [x] テストで self、外部 success/failure、identity unknown、監査不能、停止未確認、保存先変更/リンク、inventory改変/追加、入力不備、CLI終了コード、機密値非表示を確認する。実際に accept で保存した JSON/sidecar は helper 検査を通す。
- [x] `uv run pytest .agents/skills/review-verify` とリポジトリの `uv run pytest tests/skills .agents/skills .agents/scripts tools` を同期実行して待つ。Task 1 文書に不一致を見つけたら直して再確認する。変更パスだけ commit、自己レビュー、RED/GREENのコマンド/出力と所要時間を task-2-report.md に記録。

## 最終検証と公開

各Taskの仕様・品質レビューを通し、最後にorigin/mainとの全差分を独立レビューする。最終レビューの修正は1回のまとめた委譲と1回の差分再レビュー。全検証を通し、結果と所要時間を文書/PRへ記録する。Issue/コメント/PR/予約の所有権を再確認、親checkoutのscan-before-push.shを通ったSHAをpushし、同branchからmain向けPRを1つ作成。`Closes #154` を記載しマージしない。成果を子Issueに公開後、自分の予約だけexact-SHA leaseで解放する。

## 実行記録

- Task 1: `57a6e71` と保存先修正 `9bb52c2`。cycle fixture は committed HEAD を隔離実行し、confirmed 1 / not_reproduced 1 / unverified 1、v2 validate と要約生成を確認。スキル無し/ありの判断シミュレーションを実施し、結果・評価時の版を evals/validation.md に記録した。旧配置の読取元とD-10出力先を分ける指摘は修正し、差分再レビューで解消を確認。
- Task 2: `4f83ddc` と主要skill照合の修正 `1a2ce01`。初回全体2000件、修正後の集中112件が成功。外部payloadが別の観測済みskillを主要skillにできる問題を再現し、dispatchが渡したpath/SHA256と保存前に照合するよう修正。差分再レビューで解消を確認。
- Dev Container の33本の検証、check-layout、15参照先の構造検査は終了0。修正後の全体回帰とブランチ全体レビュー・公開は続けて実施する。
- 各Taskは独立担当が実装・自己レビュー・commitし、別担当が仕様/品質と修正差分を確認した。Task 1 は約8.3分＋修正約1.9分、Task 2 は約10.6分＋修正約3分（検証の待機込み。初回時計取得前は一部未計測）。
- 初回REDのuv環境作成時にhardlink fallbackの警告が出たが、最終GREENには警告なし。履歴の出力は改変せず、全体レビューで確認する。
- SDDの台帳・brief・report・diffはAGENTS.mdの配置規約に合わせ親checkoutの一時セッションに保存した。スキル付属helperはworkspaceの保存先だけ適合させた。保存先の判断が誤りなら成果物パスの調整が必要で、実装の動作への影響はない。
