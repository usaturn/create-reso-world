# Issue #420 Cleanup Metadata Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 不完全な保存済みメタデータで削除が先に進むことを防ぎ、入力復元後の通常回収を維持する。

**Architecture:** review_spec の cleanup 専用読取検査を最初の副作用前に行う。保存形式・削除成功証拠・JSONL の復旧機構を変更せず、design は既存委譲を使う。読める記録から保持一覧を作り、CleanupInputError で拒否する。

**Tech Stack:** Python、既存 Pydantic モデル、pytest、uv、実 Git worktree/agent-runner と fake adapter。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-420-cleanup-preflight-design.md`。状態 draft、issue-to-pr の実行許可。指定 Spec レビュー1回のminor S1〜S4を反映済み（decide next=plan）。内容承認と混同しない。

## Global Constraints

- 正規の失敗レビューも回収可能にし、failed result の不一致だけで拒否しない。
- 不正メタデータは cleanup.lock 作成・receipt 再追記・対象削除より前に拒否する。
- 証拠なし missing を成功にせず、過去の削除証拠・保存済み失敗記録を後付け・書換えしない。
- 実モデル・実サービス・資格情報をテストに使わない。実モデルは指定 workflow 担当だけ。
- 同一 worktree に同時書込しない。テスト・下書き・ログ等の未追跡作業物は controller の SESSION に置く。
- 恒久テストは AGENTS.md の S 代表だけ。F/L/D は追加せず、一時検証か既存検査を使う。

## 実行方式とファイル構成

実装は利用者指定 `pi_openai-codex_gpt6-terra_xhigh`（fallback=[]、self=false）へ implement_task.py で1 Taskずつ依頼するSDD。controller は統合・Task review・公開・loop を担当する。source を self が引き取らない。単一境界の変更なので Task を分割して同じ検証を重ねない。

- `.agents/skills/issue-to-pr/scripts/review_spec.py`: cleanup 専用検査と拒否情報。既存 _request_of を他コマンドまで無差別に厳格化しない。
- `.agents/skills/issue-to-pr/tests/test_review_spec.py`: S の代表回帰。既存 fixture/FakeReviewAdapter を使用。
- `.agents/skills/issue-to-pr/scripts/review_design.py`: 原則変更不要、既存委譲を一時検証。
- `.agents/skills/issue-to-pr/tests/test_review_design.py`: 原則変更不要、同じガードの重複恒久テストを追加しない。
- 文書はこの Plan と Spec のみ。SKILL.md/README の手順変更や過去 Spec の書換えはしない。

## Review Focus

次は恒久テストの組合せ網羅ではなく、Task1 Step5 の一時検証と既存 S で確認する。

1. `mode=self` に改変した external 記録が成功 no-op にならず、正規の未submit self は no-op。
2. failed result が不一致・incomplete・null でも、正規メタデータなら安全な対象を回収できる。
3. 保存後に元 Spec/HEAD が更新されても、保存済み spec.md を基準に回収できる。
4. runner_dir が相対・空・NUL・非文字列、request が object でない場合は対象を推測削除しない。
5. fallback の全試行が拒否一覧に入り、復元後に全対象を回収できる。design でも同じ意味。

## 受け入れ基準（実装担当・タスクレビュー担当へ同文を渡す）

Linux Dev Container・uv・実 Git worktree・実 agent-runner＋fake adapter/CLI で検証する。日本語・複数行/CRLF の Spec/Issue と非 ASCII runner パスを使い、成功単一試行・失敗 primary＋成功 fallback を扱う。saved request の review_id 欠落、spec_sha256 欠落、review_id=null/型不正で、全対象の実体・Git登録・既存 ledger/runner メタデータ・CODE_ROOT HEAD/status・Spec が不変のまま構造化拒否し、完全パス・照合先・理由を示す。一時fixtureだけ元requestの生バイトを復元すれば、別通常CLIで回収完了し再実行no-opとなる。Spec/design共通経路、正常対照、全保持試行を確認する。private receipt/証拠・common-dir・symlink・停止未確認の既存拒否とJSONL単発障害からの復旧を維持する。過去の証拠なしmissingは成功化・証拠後付けせずretainedのまま。任意の破損修復、同時手編集の新しいトランザクション、他セッション回収、runner/implement cleanup再設計は対象外。正常生成されたfailedレビューと未submit selfの回収/no-opを妨げない。

## 要件・原因・検証の対応

| 条件 | 担当 | 観測・証拠 |
|---|---|---|
| 削除後の必須値参照失敗を防ぐ | Task1 | S代表のRED→GREEN、欠落/nullの一時変種、拒否前後のbytes/登録比較 |
| 保存済みレビューと対応、別対象を選ばない | Task1 | completed識別不一致の代表S、保存Spec写しとの照合・相対パス一時検証 |
| 復元後の通常回収とno-op | Task1 | 実runner作成＋別CLIプロセスで復元→回収→反復 |
| design・fallback・保持一覧 | Task1 + controller統合 | 一時検証と既存design委譲S、全試行path・records確認 |
| #419復旧・既存拒否・証拠なしmissing | Task1 + controller統合 | 既存Sを変更せず実行、過去消失はretained維持 |
| 共有する入力→保存→検証→削除順序 | controller統合 | Spec→Plan→Task report→現行HEADのログを条件ごとに照合。件数のみで完了しない |

### Task 1: Cleanup の削除前検査と代表回帰

**Files:**
- Modify: `.agents/skills/issue-to-pr/scripts/review_spec.py`（cleanup、_cleanup_records、およびcleanup専用ヘルパ）
- Test: `.agents/skills/issue-to-pr/tests/test_review_spec.py`

**Interfaces:**
- Consumes: `cleanup(review_dir: Path, kind: Kind = SPEC_REVIEW) -> dict[str, Any]`、`CleanupInputError(reason, retained=..., records=...)`、既存 `BatchResult`・種類別result・_attempt_map・_cleanup_success。
- Produces: 呼出し仕様・正常結果は不変。cleanup専用の `_check_cleanup_metadata(review_dir: Path, request: dict[str, Any], record: dict[str, Any] | None, kind: Kind) -> None`（または同等の小さな検査ヘルパ）を副作用前に適用し、不正を `CleanupInputError` の既存CLI出力へ接続する。必要な文脈はread-onlyに収集する。

**テストの要否:** S。必須メタデータ不正で削除が進むと、例外で気付いても証拠・登録が失われ復元後も回収不能になる。代表の1本で欠落→無変更拒否→復元→回収→no-opを確かめる。型・欠落フィールド全組合せはDのため恒久化しない。別レビュー識別情報の取り違えは独立したSとして必要なら代表1本を置く。既存Sは維持する。

- [ ] **Step 1: S代表の失敗テストを書く**

`test_cleanup_preserves_targets_until_request_metadata_is_restored` を実runner＋FakeReviewAdapterで作る。review_idを欠落させて別CLIの拒否を実行し、worktree実体・登録・runner/ledger bytes（不正入力を含む実行直前のsnapshot）・CODE_ROOT HEAD/status・Specを前後比較する。retainedに全試行とrunner、recordsにrequest/review/spec.md/試行依頼があることも損害確認に添える。元requestだけ復元した後は別CLIで回収し、再実行no-opを確かめる。正常対照を含める。新しい対応照合の独立Sを追加する場合は `test_cleanup_rejects_a_completed_review_identity_mismatch` で正常対照も確かめる。

- [ ] **Step 2: REDを確認する**

`uv run --project /workspaces/reso-world --locked pytest .agents/skills/issue-to-pr/tests/test_review_spec.py -k 'preserves_targets_until_request_metadata_is_restored or completed_review_identity_mismatch' -q`。現行では欠落時に対象が先に削除され、対応不一致も拒否されないことでFAILすること。構文/fixture誤りをREDと呼ばない。出力をSESSIONへ保存する。

- [ ] **Step 3: 最小の削除前検査を実装する**

Specの削除前検査1〜5と反映済みS1〜S4を実装する。必要値の厳密な形・保存値自体の絶対パス・保存済みSpec写し・completed resultの対応を確認する。failed resultは正常に不一致を含み得るので、一律の成功result要求を追加しない。selfを名乗るexternalの誤成功を防ぎ、未submit selfを維持する。読むことができるbatchから保持一覧を集め、最初の副作用より前に構造化拒否。_cleanup_recordsにspec.mdを加える。過去の証拠なしmissingや削除成功証拠の規則は緩めない。

- [ ] **Step 4: GREENと既存回帰を確認する**

Step2のコマンドと `uv run --project /workspaces/reso-world --locked pytest .agents/skills/issue-to-pr/tests -q` を実行する。さらにプロジェクトsuite `uv run --project /workspaces/reso-world --locked pytest tests/skills .agents/skills .agents/scripts tools -q` を同期実行し、失敗は省略せず報告する。`git diff --check` も実行する。

- [ ] **Step 5: controller が一時検証をSESSIONへ保存して実行する**

implement_task.py の担当は許可2ファイル以外へ書けないため、担当はStep1〜4と6を行い、TaskResultのconcernsに検証内容・所要時間を記す。controllerがrunnerログを保全してreportを作り、本StepをTaskレビュー前に実行する。担当へ外部ファイル書込を要求してhelperの制限を迂回しない。

コミットしない検査を `/workspaces/reso-world/tmp/agents/issue-420.xlpq2lqf/` 下へ置く。実runner＋fake、通常CLIの独立プロセスで、正常Spec/design、review_id欠落/spec_sha256欠落/null・代表型不正、fallback保持一覧、mode/相対runner/nested request不正、completed不一致、正規failed不一致/null、未submit self、元Spec更新後の回収を確かめる。入力間の直積は作らず、各独立条件の代表にする。既存のJSONL復旧/private/common-dir/symlink/停止未確認/missingのSで重複ガードを補完する。検査は実資源・実モデル・認証情報を使わず、一時Gitだけを操作する。スクリプトとログの絶対パス・入力/結果・前後不変性を報告する。

- [ ] **Step 6: Commitと報告**

指定2ファイルだけstageして `fix: validate cleanup metadata before removing review artifacts` でcommitする。自己レビューし、TaskResultでTask結果、コミット、RED/GREEN・回帰の各コマンドと終了コード、変更の要点、懸念、着手からの時間と内訳を報告する。個別ログ/reportは担当に書かせずcontrollerがrunnerログから保存する。子を起動しない。push/PR/Issue/ref操作はしない。テスト・lintは同期で完了を待つ。

## controller 統合・最終検証・公開

Task1の開始BASEを記録し、取り込み後に同じ受け入れ基準・brief/report/diffを読み取り専用Task reviewerへ渡す。controller自身で関連検証を同期実行し、指摘の採否・同一担当への修正依頼・再確認はSDDに従う。--merge適用のためPR前の最終ブランチ全体レビューだけ省き、PR後のループ1回目へ委ねる。

最後のcommit後・clean HEADで必須検証を実行し、argv/exit/log/HEAD/baseを記録する。必須コマンド（cwd=code）:

1. `bash .devcontainer/run-tests.bash`
2. `bash scripts/check-layout.sh`
3. `uv run --project /workspaces/reso-world --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
4. `git diff --check`

所有パス・必須コマンドはPlan commit直後SESSIONに固定する。捕捉baseをrecheckし、未pushの前進があれば専用helperで検査・最大累計3回の追随・全必須コマンドの再検証を行う。衝突・所有パス重複・前提変更・公開後のbase移動は停止。spec-reviewed/reflectedのhashはSESSIONのdecide記録を使い、Specへ後付けして同hashと主張しない。

全条件の証拠が揃ってからscanしたSHAをpushし、main向けPRへ `Closes #420`、決定理由・実行方式・検証・所要時間を記載する。指定3レビュアーのloop、採否/修正、finalize以外ではマージしない。

## 実行予算

能動時間360分（準備/Spec60、実装とTask review90、統合検証/公開30、最大3サイクルのloop180）。SESSION `/workspaces/reso-world/tmp/agents/issue-420.xlpq2lqf/` のbudget.jsonl、SDDは同配下sdd/2026-11-13-issue-420-cleanup-preflight/。phase境界・50%/100%・失敗直後にcheckpoint。100%と安全失敗は停止。

Specレビューは1回完了（1049秒）、important採用なし。実装役はrunnerの90分期限、PRレビューは45分期限。同期呼出しをtimeoutで中断しない。共有feature書込・テストに停止watchを追加しない。runner隔離attemptはrunnerの期限/停止確認を使う。追加watchを使う場合だけ、事前に絶対期限5400秒/予約300秒/無進捗900秒/INT・30秒猶予・再試行1回を宣言し、停止未確認なら保留する。担当failedは別モデル/selfに切替せず停止。retry/rejectedは同じ原因1回まで、Task review修正はSDD上限内で同担当へ依頼する。

## contingency（代替策）

最初のREDでfixture/実出力の前提差なら、意味を保つ最小修正をledgerに記録して継続。保証の意味・防御範囲を変える場合は停止。過剰な全schema検証が正規failed回収を阻む場合は、cleanupが使う必要値とcompleted対応に限定し、正規failedの対照を確認する。採否基準の後付け変更はしない。実runnerの準備不良はfixtureの一時Gitだけ修正し、実資源のprune/手動修復で迂回しない。予算不足では未検証条件・残りと必要時間を報告し、要件を満たしたふりでPR/mergeしない。
