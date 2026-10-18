# Issue #153 pr-review v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 対話・非対話の PR 全体レビューと、DSH の認証情報を渡さない親保存を導入する。

**Architecture:** 移植元の4 helperを、既存 review_target.py / superpowers_context.py に適応する。保存先とロックは親 checkout、Git 操作は検証済み対象 checkout または helper 所有の専用領域に分ける。対象情報・Request・Identity・draft・HEAD・候補 pair を照合してから保存する。

**Tech Stack:** Python >=3.14、uv、既存 pydantic/pytest、git、gh、tools.agent_runner。依存追加なし。

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue153-pr-review-v2-design.md`

## 管理・実行許可

- 状態: draft。利用者の `/skill:issue-to-pr #153` は実行許可であり、Spec/Plan の内容承認ではない。
- 対象: `usaturn/create-reso-world` #153、親 #116 / `review-automation-board` / `pr-review-v2`。
- CODE_ROOT = DOC_ROOT = `/workspaces/reso-world/.worktrees/issue-153-pr-review-v2`、branch `feat/issue-153-pr-review-v2`。
- PARENT_ROOT = `/workspaces/reso-world`。基準 `1335f410e624355cd558029bdcdad65eaa944ed8`。
- 移植元の基準 `usaturn/agent-workspace@a47b2065fddad76b7475752fd0088af0733de204`。読み取り用 snapshot は `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/donor/`。`upstream-files.tsv` の blob SHA を基準とする。外部 checkout の探索・clone はしない。
- 実行方式: inline（executing-plans）。2 Taskが同じ helper の公開仕様に密接に依存し、順次統合するため。独立調査・builder check・スキルの無し/ありの比較・最後の全体レビューのみ fresh role を使う。

## Global Constraints

- 親 #116 冒頭の「着手するエージェントへの注意（利用者決定: 2026-10-18）」と親 Spec D-1〜D-24 に従う。tools/workspace・projects.toml は導入しない。
- review-fix-planning の致命的な指摘だけを直す判断基準、三択の結論、修正後の自己レビュー最大1回を変更しない。
- `.agents/scripts/review_*.py`、tools/、ほかの子の担当箇所を変更しない。
- 正式保存先は `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/`。PR base側の repository は小文字化し、fork/head repository と混同しない。名前の規則は review_target.py に集約する。
- 外部コード対象は明示した main checkout と remote 一致が必須。resoloop の upstream PR は base_remote=upstream を使う。
- 旧配置・他モデルのレビュー本文を読まず、移動・上書きしない。共有追跡 ref/tag/FETCH_HEAD と他 worktree を変えない。
- DSH 子へ GitHub token を渡さず、子は snapshot/bundle だけで動く。staged は success ではない。親が停止・Identity・Request・digest・live HEAD を照合する。
- 新 target state は version 8、現行 repository state version 7 の意味と repo identity を保つ。
- Python は uv 必須。起動は `uv run --project <skill-source-root> --locked python`。tools/devenv・grok-build は導入しない。
- テストは実コードを実行する挙動だけ。文書文面・設定値・モデル一覧だけの照合を新設・移植しない。
- ユーザ確認用 Spec/Plan コピーは作らず draft のまま同じ PR で公開する。マージ・force push・rebuild・認証設定変更・新規CIはしない。

## Review Focus

1. PR base repo と origin が異なる upstream: 指定 checkout と base_remote を使い、別 repo の同番号を取得しない（Task 1）。
2. 旧 version 7 の state と新 target state: 別の意味として誤解釈せず、既存の repo identity 検査を保つ（Task 1）。
3. shallow checkout と同時レビュー: 自セッションで必要な objects/base を確保し、共有 refs を動かさない（Task 1）。
4. DSH の staged 結果の改変・停止未確認・HEAD変更: 正式な保存を拒否し draft/state を残す（Task 1）。
5. 外部 checkout の旧 reviews と曖昧な番号入力: 新配置だけを自動解決し、旧配置を勝手に読まない（Task 2）。

## 実行予算

- 能動時間 180分。似た先行 #150/#151 と異なり adapter 実装はなく、4 helper の適応と2 Task・実機3レビューが中心。準備/設計25分、helper適応65分、手順統合20分、回帰/全体レビュー35分、公開/実機/記録35分を目安とする。
- ledger: `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/budget.jsonl`（開始済み）。SDD補助scriptの出力が worktree 内に置かれる場合は使わず、この session に progress.md・brief・diff package を保存する。これは AGENTS.md の未追跡成果物の置き場所を優先するため。
- inline の実装・pytest・shell・layout・pushは中断する worker の対象にしない。pi の foregroundで終了まで待ち、終了コードとログを確認する。
- 実機: 対話レビュー1回（このセッションが他者本文を読む前に実施）。並行runnerは `dsh-ccd` と `devin-swe` を各1回、fallbackなし。実機はこの子のPRだけ。役割期限は900秒、親 wrapper は task_watch `--deadline-seconds 1200 --reserve-seconds 120 --no-progress-seconds 600 --stop INT --stop-grace-seconds 30 --max-repeated-failures 2`、escalate-kill無し。wrapper の進捗ファイルは SESSION 内、result-file も SESSION 内に置く。runner は同期で停止確認まで待つ。
- スキル評価は同じ非対話の場面で「無し1回・あり1回」の dry-run、実モデルのレビュー起動とは分ける。無しの結果は取得済みで、helper/schema/資格情報隔離の手順不足により停止。正確な手順を確認できるかをありで比較し、固定文言テストで代えない。
- 同じ信頼性の失敗は原因を変えた再試行1回まで。認証・安全・権限拒否、Gitleaks失敗は即停止。必要なAPI失敗を成功扱いしない。予算100%では停止して残作業を報告する。
- checkpoint: Spec/Plan完了、各Task完了、50%/100%、worker失敗直後。成果増加/同じ失敗/付随処理比率/残りを記録する。
- contingency: 予算不足なら実装済み範囲と残る受入れを handoff へ保存し予約を解放する。DSH認証・#174の既存adapterをこの子で直さない。許可なく新Issueへ分割せず持ち越し候補として記録する。

---

### Task 1: 共通 prepare/complete と親保存の helper を適応する

**Files:**
- Rewrite: `.agents/skills/pr-review/scripts/pr_review_workspace.py`
- Create: `.agents/skills/pr-review/scripts/pr_review_parent.py`
- Create: `.agents/skills/pr-review/scripts/review_run.py`
- Create: `.agents/skills/pr-review/scripts/review_run_record.py`
- Modify: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`
- Create: `.agents/skills/pr-review/tests/test_review_run.py`
- Create: `.agents/skills/pr-review/tests/test_port_routing.py`（移植先固有の経路・301ファイル・state互換の挙動）

**Interfaces:**
- Consumes: `.agents/scripts/review_target.py` の `resolve(pr, *, parent_root, runner=None, code_root=None)`、`target_checkout(parent_root, repository, code_root=None)`、`fetch_pull_head(checkout, repository, number, head_sha, *, remote)`、命名関数、PullRequest、`require_parent_root`。実際の signature を再確認し未知の API を補わない。
- Consumes: `review_findings.py` の v2 candidate/schema/pair、`review_records.py` の read_state、`tools.agent_runner.models` の Request/Identity/BatchResult、`dsh_identity.read_session_identity`。
- Produces: 上流同名の4 helper と CLI（prepare/complete/fail/prepare-parent/finalize-parent/attach-runner）、JSONは上流 noninteractive.md の形。新しい target state は version 8。base_remote と resolver で照合した target_root を保持する。

**テスト:** 必要。Git・JSON解析・binding・保存・cleanup・同時実行・fail-closed の実行挙動がある。元の test_pr_review_skill_contract.py の文言検査は移植/増設しない。

- [ ] Step 1: 既存 helper と移植元4 helper/testsを読む。実行テストだけを先に移し、registry/clone fixture は実際のgit checkoutと fake gh API に置き換える。元の #146 の repo identity・拒否・保存・cleanup の検査を残す。移植元 test_review_run.py の config本文文字列検査は省き、必要なら実 config load/validation で代替する。
- [ ] Step 2: `uv run pytest .agents/skills/pr-review/tests/test_review_run.py` を実行し、新入口の欠落による RED を記録する（終了コード非0、未導入のhelper）。新 target 路線の命名・parent保存・upstream・moving HEAD も期待が異なる RED を記録する。
- [ ] Step 3: donor4 helperを適応する。CloneTarget/clone_repository依存は入れず既存resolverを呼ぶ。親準備では照合済み対象のremoteだけから、所有一時Gitへ完全なrefsをfetchしbundle化する。DSH子はbundleだけをfetchし、remote通信無し。upstreamと外部checkoutをoriginに読み替えない。legacy version7 stateと新version8を区別し、version7のpr_repo/パス検査を維持する。
- [ ] Step 4: 通常のprepareは明示source-rootをcode-rootとしてresolveへ渡し、base fetchは返されたbase_remoteを使う。run helperの source-root、parent helperの source-root、parse/load state のすべてで同じ対象を照合する。設定/役割にgrok-buildを追加せず、uv環境はルートにする。
- [ ] Step 5: 保存は本文/candidate pair・fingerprint・HEADをlock内で検査し、候補コピー後の本文失敗をrollbackする。DSHは実Request/Identity/stop_confirmed/sensitive cleanup/draft digest不一致を拒否。候補coverage空を指摘0にしない。記録はhelperが作り、runner値はattach-runner欄だけへ追記する。
- [ ] Step 6: #59 の回帰としてfixtureで301ファイルを変更し、git diffで全ファイルを読み、候補pairまで保存/cleanupする。#134はlive head変更拒否・draft/state保持・新規prepare後の保存を検査する。fork/upstream同番号、対象checkout無し/remote不一致、shallowと同時session、request/skill/draft改変と停止未確認を実行テストで検査する。
- [ ] Step 7: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py .agents/skills/pr-review/tests/test_review_run.py .agents/skills/pr-review/tests/test_port_routing.py`。Expected: 全てPASS。GIT_*等でテストが実checkoutへ書き込まないよう実行fixtureを分離する。
- [ ] Step 8: 明示した helper/test path だけstageし `feat: port shared pr-review preparation and parent finalization` でcommit。progressにテストのコマンド/件数/RED→GREENとTask別時間を残す。

### Task 2: スキル・workflow・保存先を読む箇所をそろえ公開する

**Files:**
- Rewrite: `.agents/skills/pr-review/SKILL.md`
- Modify: `.agents/skills/pr-review/references/time-budget.md`
- Create: `.agents/skills/pr-review/references/evidence.md`
- Create: `.agents/skills/pr-review/references/noninteractive.md`
- Remove/replace: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`（文言のみの検査を廃止。テスト不足を文面検査で補わない）
- Modify only workflows.review: `.devcontainer/agent-runner.toml`
- Modify only PR review row: `AGENTS.md`
- Modify only pr-review state/directory sections: `.agents/skills/repo-cleanup-after-merge/SKILL.md`
- Modify only argument-resolution and step2: `.agents/skills/review-fix-planning/SKILL.md`
- Modify only review save location sentence: `docs/resoloop-meshy-workflow.md`
- Record: このSpec・Plan

**Interfaces:**
- Consumes: Task1のreview_run.pyとversion8 state（parent_root/target_root/pr_repo）。
- Produces: 新入口のrunbook、review workflow after_run=finalize-parent→attach-runner、既定inspect=[pi-gpt,devin-swe,dsh-ccd,claude-opus,pixg]。番号/URLの読取は review_target.py review-dir を使う。旧stateはmain_root、新stateはparent_rootを保存先の基準にする。

**テスト:** 文書・設定値のため新しい自動テスト不要。代替はスキル無し/ありの振る舞い比較、frontmatter/参照先の構造検査、実 config check、既存経路の実行テスト、全回帰とdiff確認。モデル一覧の固定照合は書かない。

- [ ] Step 1: 無しのdry-run結果をSESSIONへ記録する（helper契約不足・concurrency誤解・資格情報隔離不足で停止）。donorのSKILL/referencesを読み、Task1で動作を確かめた入口へ適応する。PI_MODEL/PI_PROVIDERの取得規則・他モデル本文禁止・helper失敗時の手動代行禁止・時間予算と監視を保つ。tool rootは読んだskillのsource checkout。
- [ ] Step 2: noninteractive.mdでprepare-parentとdescriptorの明示的な事前作成、DSH子のstagedと親のsuccess、固定HEAD/baseのgit diff、保存pair・記録・失敗と残存先を説明する。Unverified candidatesは見出しか「なし」で始める。tools/devenv/grok-build/registry前提を持ち込まない。
- [ ] Step 3: 新配置を保存・読む・説明する箇所を同時に更新。review-fix-planningの第1引数はreview_target.py review-dirで対象repositoryを照合し、旧パスは明示時だけ。repo-cleanupはstate versionごとに正式保存先を組み立て、安全確認できなければ保留する。ほかの節は変更しない。
- [ ] Step 4: TOMLにreviewのafter_run2コマンド（`uv run --project . --locked python .agents/skills/pr-review/scripts/review_run.py ... --result {result}`）と既定inspectを追加する。個人設定とagent/role/fix/issueの節は変更しない。`uv run --project . --locked python -m tools.agent_runner check --config .devcontainer/agent-runner.toml` を実CLIのhelpと照合して実行。Expected: exit0、invalid_reference無し。
- [ ] Step 5: 同じDSH非対話場面をfresh研究roleに、新SKILLとreferencesを読んでdry-runさせる。prepare-parent→prepare→git全体差分→complete/staged→停止確認→finalize-parent→attach-runner、レビュー別保存とmoving HEAD拒否を確認する。結果を無しの結果と比較してSESSIONに保存する。
- [ ] Step 6: `uv run pytest .agents/skills/pr-review`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` をworktreeルートで同期実行しログとexitを確認する。Expected: 全exit0。構造検査・skill-efficiency-checkはwarningを精読し、実行に関係ない一般的提案だけで本文を膨らませない。`git diff --check`成功、担当外差分無しを確認する。
- [ ] Step 7: 明示pathだけstageしてcommit。Issue状態・PR競合・claim所有を再確認し、親checkoutのscan-before-push.shで全未pushcommitを検査し、出力SHAをそのままpush。main向けPRを作る。Closes #153、#59/#134は検証で解消できたときだけClosesを足す。
- [ ] Step 8: このセッションの対話pr-reviewをこのPRで1回、新入口から実行する。他モデル本文を読まず、本文と候補pairの保存/cleanup結果を記録する。親snapshot/bundleを新しいSESSION内へprepare-parentし、実Requestにdescriptorを付けたrunnerでdsh-ccd/devin-swe各1回を並行起動する（900秒、fallback無し）。task_watchで宣言して同期終了を待ち、外側state/exit/stop_confirmed、payload、pair保存、run記録を照合する。失敗は成功とせず停止する。
- [ ] Step 9: branch全体のdiff package・Spec・Plan・テスト結果をfresh sp-reviewへ渡し、requesting-code-reviewに従い全体レビューを1回行う。指摘があれば真偽と影響を確認し、必要な修正を1回のpassでRED→GREEN・回帰確認する。2回目の自己レビューはせず未再レビューを記録する。修正pushにも再度Gitleaksを使う。
- [ ] Step 10: Spec/Planに結果・所要時間・持ち越しを記録しdraftのままcommit/scan/push、PR本文を実結果で更新する。Spec/PlanをGitHubから新しい領域に復元しbytes/hashを照合、manifestを子Issueに公開する。handoffを作る場合はagent-handoff schemaに従い同様に復元する。子はopenのまま（マージ待ち）。自分のclaimだけexact-SHA leaseで解放し不在確認、Herdrをcompleted、実在pathとPR URLを報告する。

## 自己点検

Specの受入れ1〜7をTask1の実行検査とTask2の統合/実機/公開に対応させた。共有APIはTask1の出力をTask2で使い、review_target.pyの変更は計画に含めていない。未確定のsource取得・DSH pre-run・staging配置はSpecのbuilder check節で決めた。検証と実機は別に記録する。
