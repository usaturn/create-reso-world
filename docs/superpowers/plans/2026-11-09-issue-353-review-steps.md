# Issue #353 Review Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 明示 opt-in の Spec・設計レビューを追加し、Plan 実装とレビュー修正の既定を sonnet xhigh にする。

**Architecture:** AW `0eea76aa` のレビュー用スキーマ・状態遷移を参考に、CRW の workflow issue / preflight / 外部 SESSION 記録に適応する。Kind が共通の保存・実行・結果検査を担い、設計レビューだけの停止条件を review_design が持つ。

**Tech Stack:** Python（uv）、既存 Pydantic、pytest、fake adapters / temporary Git、TOML / Markdown / RST。

**Spec:** `docs/superpowers/specs/2026-11-09-issue-353-review-steps-design.md`（状態 draft、実行許可は明示 issue-to-pr と再開指示。承認 SHA はない）

## Global Constraints

- 対象 repository: usaturn/create-reso-world。base は refs/heads/main / b61b36a3e11f969f4e4ab41c401dadfa00a86e90 に固定する。
- --spec-review / --design-review は利用者の明示引数だけで有効にし、loop_args に入れない。今回の run は両方無指定。
- レビュー記録は SESSION の下、Spec/Plan は DOC_ROOT に commit。ledger-dir の既定は環境変数 SESSION、未設定なら拒否する。
- 既存の --base / pinned SHA / DOCS_SEPARATE / 登録ツール / ワールド停止 / Refs/Closes / require_auditable_workflow / dsh_removed / 個人設定導入は維持する。
- テストは S に限る。F の文言・名前・一覧の固定値、L の構文・例外だけのテストは追加しない。既存 S を消さず、同じ守りを複数層へ増やさない。
- テストは fake adapter と一時 Git のみ。実 CLI/API/PR/認証情報を使うテストを作らない。HOME 差替えはワンショット、Git 環境を隔離する。
- 担当は pi_opencode-go_deepseek4-flash_max、fallback=[]。各 Task を直列に runner へ依頼し、失敗で self に引き取らない。push/PR/claim/Issue は controller だけが扱う。

## Review Focus

1. Spec が別 DOC_ROOT にある入力: コード HEAD と Spec の生バイトの両方を確認し、記録をどちらの worktree にも置かない（T2）。
2. stale ID/ハッシュ、採否の欠落・重複: completed や次工程を返す前に拒否し、拒否で採否 snapshot を書かない（T2）。
3. ledger と runner の包含・symlink: cleanup がレビュー履歴や利用者領域を消さない（T2）。
4. read-only role の誤設定と unprotected_changes: 権限が違えば実行せず、outside_changes の拒否を残し、報告だけの変更を成功/失敗の根拠として混同しない（T1/T2）。
5. opt-in と --merge の混在: 利用者の指定を落とさず、設定だけで有料レビューを起動せず、順序と builder check 代替を一貫させる（T1/T3）。

## 受け入れ基準（各 brief に同じ本文を転記する）

動作環境は現行 Dev Container と uv の Python。実入力は複数行の日本語を含む Issue/context、UTF-8/CRLF の Spec、`#42 --merge --spec-review self --design-review fake-agent --assign inspect=fake-agent`、および両レビュー無指定。防御範囲は、明示 opt-in、結果/依頼/版の対応、採否の一意な全件対応、記録の外部保存・上書き禁止、権限、順序、停止と cleanup。反例は誤った版・ID、不完全レビュー、採否漏れ/重複/未反映、wrong_approach/blocking/利用者への問い、既存 Spec レビュー後の設計レビュー、worktree 内の記録、停止未確認の試行である。対象外は意味的な Spec 反映の自動証明、adapter/監査 API/個人設定導入の変更、実サービスによるテスト、他 Issue の変更。通常の判断は Spec の委任に従い、未知・未確認を成功扱いしない。

## Task と条件の対応・統合担当

T1 は入力と共有処理、T2 はレビューの安全なライフサイクル、T3 は利用者の入口と設定・説明を担当する。controller が、同じ --ledger-dir の伝播、Kind の対応、admit→submit→decide→cleanup の順序、role の writes、fallback、builder check の条件、opt-in 未指定の非起動を統合確認する。Task 単体の件数を全体の証拠へ読み替えない。

### Task 1: 入力と共有 runner 処理

**Files:**
- Modify: `.agents/skills/issue-to-pr/scripts/implement_task.py`
- Modify: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`
- Test: `.agents/skills/issue-to-pr/tests/test_implement_task.py`
- Test: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`

**Interfaces:**
- Consumes: 現行 Config / Assignment / BatchResult（unprotected_changes）と既存の cleanup。
- Produces: `project(config: Config, role_name: str = ROLE, *, writes: bool = True) -> Config`。
- Produces: `remove_attempts(repository: Path, batch: BatchResult) -> tuple[list[str], list[dict[str, str]]]`。
- Produces: resolve_issue JSON の `spec_review: str | None`, `design_review: str | None`。

- [ ] Step 1: S テストを先に追加し RED を確認する。期待 writes=false の review role は false なら投影でき、true なら実行権限を与えない。opt-in 無指定は null、--merge の後ろの明示レビュー値を取り出し loop_args は元の --assign だけになることを1件で確認する（別の担当を起動する損害を防ぐ）。既存 cleanup/scope の回帰は既存テストを使う。
- [ ] Step 2: 上記 project/remove_attempts を実装する。既存の project の依存除外条件、一人の担当/json/権限検査、cleanup の force 不使用、停止・機密・dirty の保持を変えない。summarize に unprotected_changes を足す。
- [ ] Step 3: パーサへ両オプションを追加する。IMPLEMENT_VALUE と同形、重複・欠値・不正値を拒否する。--merge の前後で独立して処理し、既存 --base と repo 解決は変えない。L の不正値だけの検証は一時実行で行い、テストを増やさない。
- [ ] Step 4: `uv run --locked pytest .agents/skills/issue-to-pr/tests -q`、`uvx --offline ruff check --select E4,E7,E9,F .agents/skills/issue-to-pr/scripts/implement_task.py .agents/skills/issue-to-pr/scripts/resolve_issue.py` を同期実行する。PASS / 終了コード0を期待。S テストに理由をコメントし、diff を確認する。
- [ ] Step 5: 上記4ファイルの変更だけを明示 stage し、`feat(issue-to-pr): add review options and shared runner helpers` で commit。commands・RED/GREEN・懸念・Task 内訳と所要時間を結果に返す。

### Task 2: Spec と設計レビューの helpers

**Files:**
- Create: `.agents/skills/issue-to-pr/scripts/review_spec.py`
- Create: `.agents/skills/issue-to-pr/scripts/review_design.py`
- Create: `.agents/skills/issue-to-pr/tests/test_review_spec.py`
- Create: `.agents/skills/issue-to-pr/tests/test_review_design.py`

**Interfaces:**
- Consumes: Task 1 の project / remove_attempts と現行 runner API。
- Produces: Spec に定めた ReviewRequest/ReviewResult/Decisions、Kind、DESIGN_REVIEW、check/review/submit/decide/cleanup の CLI。
- AW の参照ファイル（採用版ではない）: `/workspaces/reso-world/tmp/agents/issue-353._kkg4w5l/upstream/review_spec.py` と `review_design.py`。全体を読んで差分を限定するが、AW の保存先・preflight は採用しない。

- [ ] Step 1: 独立に構成した UTF-8/CRLF の Spec・ID・ハッシュで、self の完了→採否→次工程の正例と取り違えの拒否を S テストにする。欠落/重複/未反映の採否が decisions.json/reflected.md を残さないこと、既存記録を上書きしないことを確認し RED を記録する。
- [ ] Step 2: review_spec を実装する。Spec 記載のスキーマ・Kind・同担当で1回だけ再レビュー、SESSION 配下 ledger / 新規 runner-dir、repository/Spec DOC_ROOT 双方の記録保護・包含/実パス検査を実装する。`--ledger-dir` は明示または SESSION、未設定は入力エラー。既存の --template/--config の fallback を保持し、実行前に require_auditable_workflow を呼ぶ。
- [ ] Step 3: fake adapter / injected run_workflow で、incomplete・不一致・outside_changes・停止未確認が failed となることと、unprotected_changes のみでは completed となり報告が残る正例を確認する。cleanup は停止・機密・dirty を保持し、正常な外部 run の出力だけを消して ledger は残す。共通の守りは spec tests に置き design 側へ重複しない。
- [ ] Step 4: review_design を Kind の共通処理で実装する。sound→continue と、wrong_approach/blocking/questions_for_user/needs_judgment→stop、changes_what_is_built/ask_user の adopt 拒否、Spec レビュー開始後と2回目の設計レビューを拒否する S テストを先に RED→GREEN で確認する。_admit は同じ外部 ledger-root を見る。
- [ ] Step 5: `uv run --locked pytest .agents/skills/issue-to-pr/tests -q`、`uvx --offline ruff check --select E4,E7,E9,F .agents/skills/issue-to-pr/scripts/review_spec.py .agents/skills/issue-to-pr/scripts/review_design.py` を同期実行する。PASS / 終了コード0を期待。S の理由をテストに記し、一般的な例外・文言・スキーマ型だけのテストは追加しない。
- [ ] Step 6: 上記4ファイルを明示 stage し、`feat(issue-to-pr): add opt-in spec and design review gates` で commit。CLI/JSON の使い方、RED/GREEN、Task 内訳と所要時間を結果に返す。

### Task 3: スキル・role・既定担当と説明の統合

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`
- Modify: `.devcontainer/agent-runner.toml`
- Modify: `.devcontainer/README.md`
- Modify: `README.md`
- Modify: `tools/agent_runner/interfaces.rst`（roles と workflow issue の割り当ての節だけ）
- Conditional test adjustment: `tools/agent_runner/tests/test_config.py`（既存の挙動テストの期待値変更が必要な場合だけ。固定 agent 名テストは新設しない）

**Interfaces:**
- Consumes: Task 2 の CLI。controller が事前に提供する旧スキルの同一シナリオ適用結果。
- Produces: 明示 opt-in→check→Spec 保存/commit→設計レビュー→Spec レビューまたは builder check→Plan の一貫した手順、json の結果/採否作成例、cleanup と停止/PR の記録。

- [ ] Step 1: writing-skills と skill-creator、RST 編集は rst-writer を読む。controller の RED 記録を確認する。子の中からモデルや subagent を起動しない。
- [ ] Step 2: SKILL.md を targeted edit する。両レビュー無指定なら helper check も起動しない。--spec-review 時は builder check を置換し、--design-review は置換しない。ledger-dir は必ず SESSION を明示し、runner の新規パスも外部 SESSION 下にする。request/result/decisions の作成、採否後 Spec commit、再レビュー上限、型/版/順序の失敗・停止、実行時間・fallback/identity・保存/retained パスを記録する。既存の安全ブロックを削らない。
- [ ] Step 3: roles.spec-review と roles.design-review を writes=false / json / 1800 秒で追加し、レビュー assignment は雛形に作らない。sonnet_default は sonnet_xhigh に置き換え、model=sonnet / effort=xhigh、issue/fix implement の既定を変更する。Issue 指定のコメントを実際の意味で揃える。
- [ ] Step 4: README と interfaces.rst の該当説明を更新する。個人設定の旧名は手動置換、agents のない review assignment 節の invalid_type、明示引数と fallback の関係を記す。#364 が直した監査節、model_key、CLI 例、dsh_removed、導入実装は変えない。
- [ ] Step 5: テスト追加は原則不要（文書/一覧/既定名は F、設定不整合は L）。`uv run --locked pytest .agents/skills/issue-to-pr/tests tools/agent_runner/tests/test_config.py -q`、一時 config に対する両 helper check の0/2、旧名なしでの load_config と実際の assignments、`bash scripts/check-layout.sh` を同期実行する。個人設定導入は変更しないので install-beforehand テストの追加・変更は不要。必要なら既存検証を実行する。
- [ ] Step 6: `git diff --check` と RST の参照/構造・関連設定の実読込を確認して、担当ファイルだけを明示 stage し、`feat(issue-to-pr): document review flow and default to sonnet xhigh` で commit。GREEN の同一シナリオを controller が新スキル付きで1回行う。Task 内訳と所要時間を報告する。

## 実行方式・レビュー・統合検証

self=false の指定に従い subagent-driven-development の各 Task の実装を、親の implement_task.py で指定 runner に直列依頼する。依頼は6項目の JSON。各依頼の取り込みと ledger 転記の後、次の依頼/停止より前に cleanup を行う。レビュー子は読み取り専用、テストは実装担当または controller が同期実行する。brief は Task 全文と受け入れ基準・該当 Spec・Global Constraints を同じ本文で実装担当/レビュアーへ渡す。controller は Task 開始時 BASE を保存し、その BASE からの diff を渡す。

Task レビューは各1回、指摘修正は SDD 上限内。最終全体レビュー1回（具体的不具合の再現だけ controller が追加実行）。SKILL の reference フロー評価は変更前/変更後の同じ2シナリオを各1子で計2回（字句一致テストではない）。①両レビュー指定で builder check の重複なし・順序/保存/採否、②無指定で新 helpers を起動せず builder check 1回。モデルの追加比較や5回反復はしない。

最終 commit 後 clean HEAD に対し、上記 pytest 一式、ruff（変更 Python）、layout、diff --check、必要な一時 fake check を実行し、argv/終了コード/完全ログパス/HEAD/base を SESSION に保存する。対象 Actions は enabled=false を確認済み。全体 pytest の並行実行は禁止で、親ボードの統合確認に委ねる。範囲を明示した関連回帰を使う。

公開は captured base を再照合し、親の scan-before-push.sh --expected-base-sha を成功させ、その SHA だけを push。PR は Refs #353（ボードの子）で作成する。--merge は親のループを指定3レビュアー構成で最大3サイクル。各45分の期限と修正時間を予算に含める。直接マージ・force push・他者作業の回収は禁止。

## 実行予算

能動時間の上限480分。目安は準備35分、実装/Task レビュー150分、統合検証/PR25分、ループ195分（3×レビュー45分+計画/修正20分）、余裕75分。Task 実装の runner role の絶対期限は90分（fallback 込み）、ループ inspect は45分。controller は同期 foreground で終了まで待つ。追加の no-progress kill は行わない（この API では実装 worker の実質進捗を宣言形式で観測できず、推測で止めない）。各 worker は残り10分を結果保存・検証記録に確保し、新規調査を広げない。

同じ信頼性失敗の再試行は1回まで（ただし implement_task failed はその時点で停止し self に移行しない）。安全失敗は再試行なし。checkpoint は準備/各 Task/検証/各ループサイクル、予算50%/100%、worker失敗直後。100%で延長せず停止する。

ledger は `/workspaces/reso-world/tmp/agents/issue-353._kkg4w5l/budget.jsonl`、SDD 記録は同 SESSION の `sdd/2026-11-09-issue-353-review-steps/`。保存した検証をループで使う間は消さず、残った場合は最終報告に完全パスを書く。runner の出力は依頼ごとに cleanup、retained は消さず報告する。

## 実行中の検証調整

Task 1 で、ruff は pyproject/uv.lock に未導入、uvx の全ルール14件は変更前と同じであることを観測した。依存追加や無関係な修正を避け、上記の静的検証を `uvx --offline ruff check --select E4,E7,E9,F` と新規指摘の差分確認へ調整した。全ルール成功とは報告しない。機能・安全条件は変更しない。

## contingency（代替策）

最初の RED で実 API の形が想定と違うときは、Spec の意味を保つ最小修正だけを ledger に裁定として記録する。共有する形の修正は次 Task にインターフェースとして渡す。意味が変わる・所有外の変更が必要な場合は停止する。

helper の配置方法で行き詰まったときは共通 Kind のまま内部分割を最小化し、追加の機能/自動移行/再試行基盤は作らない。実装担当の BLOCKED/NEEDS_CONTEXT には不足文脈を足して上限内で同じ担当へ依頼し直す。失敗後に controller が実装を肩代わりしない。親 base の移動、claim 喪失、Gitleaks/認証/権限/停止確認の失敗は既存停止規則どおり資源を保存して報告する。
