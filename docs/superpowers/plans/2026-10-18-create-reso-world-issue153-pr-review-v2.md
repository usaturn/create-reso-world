# Issue #153 pr-review v2 Implementation Plan

> 2026-10-19 PR #182 修正: 利用者の「Issue #183 を解決する形で、PR#182 を修正せよ」に基づき、DSH保存経路と必要なrunner隔離を変更する。最新の決定・実行範囲は `docs/superpowers/specs/2026-10-19-create-reso-world-issue116-dsh-native-write-policy-design.md` と対のPlanを参照。以下のtools除外・公式API待ち・DSH再開未許可は過去時点の記録であり、今回の実装を制限しない。有料並行レビューの未完了は維持する。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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
- 実行方式: subagent-driven-development。追加調査で現行workspace helperのjournal/inspect/abandon/sessionsは移植元に無いと確認したため、workspace/runner/手順統合の3つの検証可能な単位に分ける。公開する呼び出し元APIをbriefへ渡し、実装担当を1件ずつ直列に起動する。モデルはpi-superagents roleの設定を使いoverrideしない。

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
5. 外部 checkout の旧 reviews と曖昧な番号入力: 新配置だけを自動解決し、旧配置を勝手に読まない（Task 3）。

## 実行予算

- 能動時間 180分。似た先行 #150/#151 と異なり adapter 実装はなく、4 helper の適応と3 Task・実機3レビューが中心。準備/設計25分、helper適応65分、手順統合20分、回帰/全体レビュー35分、公開/実機/記録35分を目安とする。
- 2026-10-19の利用者の「提案どおりに再開してください」により追加30分、有効総予算210分。ledgerの初期180分は履歴として変更せず、resume-1/checkpointに延長を記録した。許可は拒否操作のメタデータ調査と未実施の非runner入口確認に限り、DSHの権限拡張・別経路での再試行を含まない。
- ledger: `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/budget.jsonl`（開始済み）。SDD補助scriptの出力が worktree 内に置かれる場合は使わず、この session に progress.md・brief・diff package を保存する。これは AGENTS.md の未追跡成果物の置き場所を優先するため。
- 共有feature worktreeに書く実装子・pytest・shell・layout・pushは中断する worker の対象にしない。pi の foregroundで終了まで待ち、終了コードとログを確認する。
- 実機: 対話レビュー1回（このセッションが他者本文を読む前に実施）。並行runnerは `dsh-ccd` と `devin-swe` を各1回、fallbackなし。実機はこの子のPRだけ。役割期限は900秒、親 wrapper は task_watch `--deadline-seconds 1200 --reserve-seconds 120 --no-progress-seconds 600 --stop INT --stop-grace-seconds 30 --max-repeated-failures 2`、escalate-kill無し。wrapper の進捗ファイルは SESSION 内、result-file も SESSION 内に置く。runner は同期で停止確認まで待つ。
- スキル評価は同じ非対話の場面で「無し1回・あり1回」の dry-run、実モデルのレビュー起動とは分ける。無しの結果は取得済みで、helper/schema/資格情報隔離の手順不足により停止。正確な手順を確認できるかをありで比較し、固定文言テストで代えない。
- 同じ信頼性の失敗は原因を変えた再試行1回まで。認証・安全・権限拒否、Gitleaks失敗は即停止。必要なAPI失敗を成功扱いしない。予算100%では停止して残作業を報告する。
- checkpoint: Spec/Plan完了、各Task完了、50%/100%、worker失敗直後。成果増加/同じ失敗/付随処理比率/残りを記録する。
- contingency: 予算不足なら実装済み範囲と残る受入れを handoff へ保存し予約を解放する。DSH認証・#174の既存adapterをこの子で直さない。許可なく新Issueへ分割せず持ち越し候補として記録する。

---

### Task 1: workspace・候補pairと保存先を適応する

**Files:**
- Modify: `.agents/skills/pr-review/scripts/pr_review_workspace.py`
- Modify: `.agents/skills/pr-review/tests/test_pr_review_workspace.py`
- Create: `.agents/skills/pr-review/tests/test_port_routing.py`

**Interfaces:**
- Consumes: review_target.py の `resolve(argument, *, parent_root, code_root=None, runner=...)`、`target_checkout(parent_root, repository, code_root=None)`、`fetch_pull_head(checkout, repository, number, head_sha, *, remote)`、命名関数、PullRequest、require_parent_root。review_findings.py の schema/pair。
- Produces: donor workspace helperの `_load_script/load_review_target/target_errors/_target_call/artifact_model/parse_target/require_target_checkout/require_review_commit/create/load_state/session_target/session_repository/save/cleanup` と findings helper。必要な呼出しsignatureはdonor review_run.py/pr_review_parent.pyを確認して合わせる。require_target_checkoutはparent_rootを追加引数にしてresolverで照合してよい。target state=8（parent_root/target_root/target_kind/pr_repo/base_remote）、旧state=7（main_root/pr_repository）。

**テスト:** 必要。実Gitとファイルによる保存・pair rollback・HEAD/対象照合・cleanup・state互換の挙動。既存221件のうち実行テストは維持する。

- [ ] Step 1: donor testsの候補pair/target関連を既存fixtureへ適応して先に書く。元の #146 と journal/inspect/abandon/sessions のテストは残す。文言テストは増設しない。GIT_*を隔離し、fake ghとローカルbare remoteだけ使う。
- [ ] Step 2: 対象テストを実行し、新target/pair機能が無いためのREDを記録する。
- [ ] Step 3: donorは丸ごと置換せず、現行workspaceのjournal/inspect/abandon/sessions・read-only snapshot・git(pass_fds,new_session)を保持してtarget/pairを統合する。命名規則はreview_targetへ集約。既存createはrepository引数とattempt_idを保持し、新target経路は別のstate版で保存する。新規通常経路は親へ保存し、旧経路を自動で読まない。
- [ ] Step 4: CloneTarget/clone_repositoryは導入せず、JSONをPullRequest/既存resolverで検証。source-root=明示code-root、upstreamはbase_remoteを使う。DSH parent_inputではbundleから専用Gitへ取得する。新しい通常targetには検証済みtarget_rootが必須で、欠けたcheckoutのcloneは禁止。対象用refも `refs/pr-review/repos/<owner>/<repo>/<N>` にする。
- [ ] Step 5: 本文/candidate pair、fingerprint、live HEADをlock内で検査し、コピー失敗をrollbackする。301ファイルのgit全体差分を読んで保存/cleanupする実行テストを追加。moving HEAD拒否・draft保持・新規sessionで再開、fork/upstream同番号、外部checkout、version7/8、pair rollbackを検査する。
- [ ] Step 6: `uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py .agents/skills/pr-review/tests/test_port_routing.py`。Expected: 全PASS。self-review後、明示pathだけstageしてcommitし、RED/GREEN・件数・時間・未解消の懸念をreportへ保存する。

### Task 2: runner の共通入口・親入力・親保存を適応する

**Files:**
- Modify (接続時の限定修正): `.agents/skills/pr-review/scripts/pr_review_workspace.py` の cleanup の成功返却に、既存 compare-and-delete が確定した `pr_ref` と `pr_ref_status` を足す。削除順・条件・v7挙動は変えない。
- Create: `.agents/skills/pr-review/scripts/pr_review_parent.py`
- Create: `.agents/skills/pr-review/scripts/review_run.py`
- Create: `.agents/skills/pr-review/scripts/review_run_record.py`
- Create: `.agents/skills/pr-review/tests/test_review_run.py`

**Interfaces:**
- Consumes: Task1のworkspace公開関数、review_records.read_state、review_findings、tools.agent_runner.models.Request/Identity/BatchResult、dsh_identity.read_session_identity。Task1が変更したsignatureはreportとbriefで受け渡す。
- Produces: donorのprepare/complete/fail/prepare-parent/finalize-parent/attach-runner、JSONはdonor noninteractive.mdの形。Requestとprovenanceは変更しない。

**テスト:** 必要。request/identity/digest/停止/HEAD/bundle/run記録の実行挙動。本文文字列・雛形の一覧検査は持ち込まない。

- [ ] Step 1: donor test_review_run.pyの実行テストだけ移し、parent originをcreate-reso-worldに、source-rootをcode-rootへ対応させる。`test_shipped_runner_template_commands_accept_result_path` の文字列検査は持ち込まない。
- [ ] Step 2: `uv run pytest .agents/skills/pr-review/tests/test_review_run.py`。Expected: 未導入helperによるRED。ログに保存する。
- [ ] Step 3: cleanup のcompare-and-delete結果を推測せずTask1 helperから返す（donorのcomplete実行テストが欠落によるREDを再現済み）。donor3helperを適応。通常resolveへsource-rootをcode-rootとして渡す。baseはbase_remoteからfresh worktree専用refへfetch。親入力は照合済みremoteから所有一時Gitへ完全historyをfetchしてbundle化し、既存checkoutをunshallowしない。DSHは親descriptor/bundleのdigestと対象を照合し子のGitHub/API/fetch無し。ROOTのuv projectへ変更しgrok-buildは除外する。
- [ ] Step 4: DSHはRequest/Identity/coverage/draft digestを照合してstaged、親はstop_confirmed/sensitive cleanup/対象/Request/Identity/digest/live HEADを照合してsave/cleanup。run記録をhelperが作り、runner値はattach-runner欄だけへ保存する。途中失敗はfailedと残存先を返す。
- [ ] Step 5: donorの実行テスト（shallow、同時session、共有refs不変、request/skill/draft改変、停止未確認、HEAD変更、記録失敗・保存後cleanup失敗）を通す。`uv run pytest .agents/skills/pr-review/tests/test_pr_review_workspace.py .agents/skills/pr-review/tests/test_port_routing.py .agents/skills/pr-review/tests/test_review_run.py` Expected: 全PASS。明示した4新規pathとcleanup返却の限定修正だけstageしてcommit、reportにRED/GREENと時間を記録する。

### Task 3: スキル・workflow・保存先を読む箇所をそろえ公開する

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
- Consumes: Task2のreview_run.pyとTask1のversion8 state（parent_root/target_root/pr_repo）。
- Produces: 新入口のrunbook、review workflow after_run=finalize-parent→attach-runner、既定inspect=[pi-gpt,devin-swe,dsh-ccd,claude-opus,pixg]。番号/URLの読取は review_target.py review-dir を使う。旧stateはmain_root、新stateはparent_rootを保存先の基準にする。

**テスト:** 文書・設定値のため新しい自動テスト不要。代替はスキル無し/ありの振る舞い比較、frontmatter/参照先の構造検査、実 config check、既存経路の実行テスト、全回帰とdiff確認。モデル一覧の固定照合は書かない。

- [ ] Step 1: 無しのdry-run結果をSESSIONへ記録する（helper契約不足・concurrency誤解・資格情報隔離不足で停止）。donorのSKILL/referencesを読み、Task1/2で動作を確かめた入口へ適応する。PI_MODEL/PI_PROVIDERの取得規則・他モデル本文禁止・helper失敗時の手動代行禁止・時間予算と監視を保つ。tool rootは読んだskillのsource checkout。
- [ ] Step 2: noninteractive.mdでprepare-parentとdescriptorの明示的な事前作成、DSH子のstagedと親のsuccess、固定HEAD/baseのgit diff、保存pair・記録・失敗と残存先を説明する。Unverified candidatesは見出しか「なし」で始める。tools/devenv/grok-build/registry前提を持ち込まない。
- [ ] Step 3: 新配置を保存・読む・説明する箇所を同時に更新。review-fix-planningの第1引数はreview_target.py review-dirで対象repositoryを照合し、旧パスは明示時だけ。repo-cleanupはstate versionごとに正式保存先を組み立て、安全確認できなければ保留する。ほかの節は変更しない。
- [ ] Step 4: TOMLにreviewのafter_run2コマンド（`uv run --project . --locked python .agents/skills/pr-review/scripts/review_run.py ... --result {result}`）と既定inspectを追加する。個人設定とagent/role/fix/issueの節は変更しない。`uv run --project . --locked python -m tools.agent_runner check --config .devcontainer/agent-runner.toml` を実CLIのhelpと照合して実行。Expected: exit0、invalid_reference無し。
- [ ] Step 5: 同じDSH非対話場面をfresh研究roleに、新SKILLとreferencesを読んでdry-runさせる。prepare-parent→prepare→git全体差分→complete/staged→停止確認→finalize-parent→attach-runner、レビュー別保存とmoving HEAD拒否を確認する。結果を無しの結果と比較してSESSIONに保存する。
- [ ] Step 6: `uv run pytest .agents/skills/pr-review`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` をworktreeルートで同期実行しログとexitを確認する。Expected: 全exit0。構造検査・skill-efficiency-checkはwarningを精読し、実行に関係ない一般的提案だけで本文を膨らませない。`git diff --check`成功、担当外差分無しを確認する。
- [ ] Step 7: 明示pathだけstageしてcommitし、実装担当はここでreportして終了。以下は調整役がTaskレビュー後に行う。Issue状態・PR競合・claim所有を再確認し、親checkoutのscan-before-push.shで全未pushcommitを検査し、出力SHAをそのままpush。main向けPRを作る。Closes #153、#59/#134は検証で解消できたときだけClosesを足す。
- [ ] Step 8: このセッションの対話pr-reviewをこのPRで1回、新入口から実行する。他モデル本文を読まず、本文と候補pairの保存/cleanup結果を記録する。親snapshot/bundleを新しいSESSION内へprepare-parentし、実Requestにdescriptorを付けたrunnerでdsh-ccd/devin-swe各1回を並行起動する（900秒、fallback無し）。task_watchで宣言して同期終了を待ち、外側state/exit/stop_confirmed、payload、pair保存、run記録を照合する。失敗は成功とせず停止する。
- [ ] Step 9: branch全体のdiff package・Spec・Plan・テスト結果をfresh sp-reviewへ渡し、requesting-code-reviewに従い全体レビューを1回行う。指摘があれば真偽と影響を確認し、必要な修正を1回のpassでRED→GREEN・回帰確認する。2回目の自己レビューはせず未再レビューを記録する。修正pushにも再度Gitleaksを使う。
- [ ] Step 10: Spec/Planに結果・所要時間・持ち越しを記録しdraftのままcommit/scan/push、PR本文を実結果で更新する。Spec/PlanをGitHubから新しい領域に復元しbytes/hashを照合、manifestを子Issueに公開する。handoffを作る場合はagent-handoff schemaに従い同様に復元する。子はopenのまま（マージ待ち）。自分のclaimだけexact-SHA leaseで解放し不在確認、Herdrをcompleted、実在pathとPR URLを報告する。

## 自己点検

Specの受入れ1〜7をTask1/2の実行検査とTask3の統合/実機/公開に対応させた。共有APIはTask1の出力をTask2で、Task2の入口をTask3で使い、review_target.pyの変更は計画に含めていない。未確定のsource取得・DSH pre-run・staging配置はSpecのbuilder check節で決めた。検証と実機は別に記録する。

## 進捗・公開前結果

Task1/2とTask3の文書・設定は実装・Taskレビュー済み。全体レビューの2件を1回の修正wave `021973e` で解消し、修正差分の再レビューは両件ADDRESSED、新規Critical/Important無し。最終コードのPython全体2652passed（565.88秒）、対象304passed（234.39秒）、shell33PASS、layoutPASS、すべてexit0。構造・実config・diff検査も成功。現時点で実機・公開の手順は未完了。

主要時間: 準備/設計約14分、Task1実装38分＋修正7分、Task2実装約28分、Task3約7分、最後の修正約8分、ほか独立レビュー・最終回帰。並行検証は二重加算しない。Task1初回pytestに240秒timeoutがあり、その後は同期の長い実行で成功。Task2が指示に反して全体回帰を追加した11分14秒は運用上の超過として記録する。

Ruling: SDD資料はworktree外SESSIONへ置いた（AGENTS優先）。内部target_kindはcloneでなくbundleとし、DSHの入力元をbundleだけに制限した。Task2接続ではcleanupの確定済みref状態を返す2項目を追加し、外部で推測しない。公開前に全体レビューを先に行い、実機はPR公開後に行う。いずれも実行許可内の通常判断であり、内容承認を記録したものではない。

#134は保存拒否の実行挙動とfresh-session再開まで検証し、残存セッションの運用の全条件は解消済みとしない。PRはRefs #134とし、Issueに結果を報告する。#59は301ファイル保存を確認しCloses対象。

## 初回実機での停止・引き継ぎ（再開前の記録）

PR #182 を作成済み（main向け、マージ無し）。parallel runの実結果はpartial_success。Devinの本文/候補保存とcleanupはsuccess、DSHはawaiting_approvalで成果無し。DSHのworkspace-write拒否を観測し、権限・cache・HOMEを変えた回避や再試行は行っていない。両attempt stop_confirmed=true、sensitive_paths=[]、outside_changes=[]。finalize-parent/attach-runner exit0はDSHレビュー成功を意味しない。wrapper exit1、watcher exited_incomplete、全プロセス停止確認済み。

非runner入口は依頼先sp-reviewにBash/書込ツールが無く未実施（実モデルのレビューを実行したとは数えない）。Task3の公開は済んだが、実機受け入れはblockedで未完了。残る検証を成功扱いしてPlanをcompletedにしない。

記録: `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/live-summary.json`、`live-runner/result.json`、`watch-live/final.json`。次はDSHの拒否操作と必要な権限の確認、通常のBash/書込可能なpiセッションで非runner入口の実行。必要な利用者判断を得る前に再起動しない。新しいPR HEADへ動いた後は古いsnapshotを再利用せずprepare-parentから作る。成功済みDevinは再実行しない。

## resume-1: 拒否操作の特定と非runner入口の実行

- 利用者の再開指示を受け、Issue #153のclaimを新しく取得した。新しいbranch/PRは作らず、PR #182・既存feature worktreeを継続した。コード変更はしていない。
- DSHの失敗は、正式保存先の`.staging/<run>/<request>/<agent>/pr-review-182-*/review-backup/`にある自身のMarkdown draftへのnative `write`。tool-call名・引数キー・対象パス・拒否診断だけを取得し、レビュー本文・thinkingは読まなかった。
- 根拠: `tools/agent_runner/adapters/dsh.py:210,232–236`の追加grantは`dsh_sandbox.py:47–53`のbubblewrap bindに渡る。一方、導入済みDSH `0.2.0-rc.2`の`@deepseek-ai/dsh-sandbox-policy/README.md:147`では追加writable roots未対応。session cwdを主workspaceとするDSH自身のnative filesystem policyへ追加grantは伝わらない。現在の設定のまま成功させるサポート済み経路は確認できなかった。
- full-access化、別cwd/HOME/cache、bashへの書き込み切替などの迂回とDSH再試行は実施しない。adapter/tools/外部依存/許可範囲の変更はこの子の許可外で、方針の具体的な利用者判断と親 #116の調整が必要。新Issueは勝手に作らない。
- 非runner入口は本Piセッション（実測`openai-codex` / `gpt-6.1-sol`）で1回実行。`prepare → 固定base..HEADのローカル全体差分取得 → review Markdown/candidates pair作成 → complete/save/cleanup`は全exit0、payload `success`、cleanup `success`、`pr_ref_status=deleted`。対象HEADは`a6e394059279d8b44611654deb82b32ada6b189a`。一意session `/tmp/pr-review-182-6ec2767b`とworktreeはhelperが削除し、成果2件とrun記録は親reviewsへ残した。bindingは非runnerのためunknown、runnerはnull。5分14.98秒（314.976秒）。
- 成果: `reviews/usaturn/create-reso-world/#182-feat-issue-153-pr-review-v2/gpt-6.1-sol.md`、`findings/gpt-6.1-sol-a6e394059279.json`、`runs/20261019T032735Z-gpt-6.1-sol-6ec2767b.json`（いずれもPARENT_ROOT基準）。active指摘0だが、全テスト全文・差分全行の精読を主張せず、実DSH保存も未達なので判定は`Needs manual verification`。入口の保存成功を、独立した第三者レビューやPR全体の受け入れ完了としない。
- 固定HEADの隔離worktreeでキャッシュ書込を止めた対象pytest: **6 passed / 97 deselected / 11.58秒 / exit0**。通常depth-1のhead/指定commit/未pushcommit、fake DSHの隔離tempの証跡保存、Pi識別子の欠落/不一致拒否、非runnerのunknownを実行。fake DSH成功をnative writeの実機成功に読み替えない。全体回帰・有料Devinは再実行していない。
- 今回の証跡は`/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/resume-1/`の`dsh-denied-metadata.json`、`dsh-context7.txt`、`nonrunner-prepared.json`、`nonrunner-checks.log`、`live-nonrunner-result.json`。コードは変わらず、正式Spec/Planはdraft、実機受け入れ全体はblocked/not readyを維持する。


## 2026-10-19: 最終修正・並行受け入れ・マージ

利用者の「提案どおりに実施してください。課金は好きなだけ実行していいです。」を実行許可とする。M-1 の設計は既存 #183 Spec に集約する。以前の有料起動回数の上限・マージ対象外は今回の実行を制限しない。今回の金額・総呼出回数は利用者が上限を設けていないが、同じ失敗を無検討で繰り返さない。

### 実行予算

能動時間の目安120分（修正・通信調査25、回帰・自己レビュー25、有料診断/並行受け入れ45、記録・公開・マージ25）。ledger は PARENT_ROOT/tmp/agents/pr182-final.e7tffksd/budget.jsonl。phase境界・50%・失敗直後に確認する。有料の実行は毎回対象・目的・期限・回数を事前記録し、新しい出力先とsnapshotを使う。最初は必要なら DSH の短い診断、最終は DSH/Devin各1回2並列で固定した修正後HEADを検証する。明示fallbackは使わない。

worker期限900秒、watcher1200秒、保存予約120秒、実質無進捗600秒、SIGINT/猶予30秒、KILLへの昇格なし。信頼性の同一失敗は1回再試行までとして、その後は原因・プロンプト負荷・provider/モデルの経路等を根拠付きで見直してから別の宣言で進む。安全/認証/権限拒否の迂回は行わない。費用を理由に必要な検証を省かず、課金許可を環境変更の許可へ広げない。通信障害が続く場合は失敗を保持し、受け入れ条件を成功へ読み替えない。

### Task A: M-1 修正と検証

- [x] 安全な Request 正規化を入口に集約し、digest / scratch / exports / context を統一。
- [x] 正常3表記のRED/GREEN、リンク・特殊file・cwd拒否、親保存までの回帰。
- テスト必要: 再現済みの実行時不具合とファイル境界の拒否を守る。

### Task B: 通信切り分け

- [x] 既存試行の時系列と導入済みCLIの終了経路を確認し、ローカルtimeout/取消とstream切断を分離。
- [x] 既存ログで原因範囲を絞れたため短い有料診断は省略。接続先等を変えず新しい並行受け入れを行う。
- テスト追加不要: 診断は外部通信の観測で、コミットするテストはfake CLIのみ。

### Task C: 回帰・自己レビュー・公開

- [x] 関連テスト、tests/skills と .agents/skills、shell回帰、layoutを実行。
- [x] 反証・PR全体・検出力の自己レビューを1回。指摘を対応して影響した検証を再実行。
- [ ] Spec/Planに修正結果を記し、Gitleaks検査したSHAを既存PRへpush。
- テスト追加不要: 既存の検証入口とTask Aのテストを使う。

### Task D: 最終受け入れとマージ

- [ ] 修正後の固定HEADでDSH/Devinの新しい2並列受け入れ。outer / payload / native evidence / pair / run記録 / cleanup / stopを照合。
- [ ] 受け入れで出た指摘は現行コードで判定し、必要な修正には再検証。変更後の成果を旧HEADの成功で代替しない。
- [ ] PR説明・#153/#183と関連Issueを実結果へ更新し、検証したHEADだけをマージ。親checkoutを最新origin/mainのdetached HEADへ更新。
- テスト追加不要: 有料実機受け入れとGitHub状態の確認を証拠にする。

### 公開前の実結果

M-1 の安全な入口を修正済み。追加12ケースを含む関連169 passed、残りのスキル729 passed、計898件成功。shell33系統・layout・実config check・diff検査も成功。自己レビュー3観点を1回行い、追加指摘なし。反証10ケースとガードを外す対照5負例で条件を確認した。詳細は既存 #183 Spec の M-1 検証記録と同じSESSIONのログを参照。

通信失敗は第10応答stream開始直後に発生し、runner/DSH期限や取消の証拠なし。元のsocket causeは記録されず切断主体までは未確定。新しい2並列の宣言とハーネスを acceptance-1/ に準備した。このcommit時点では有料試行を起動していない。Task C のpush、Task Dの受け入れ・Issue更新・mergeの実結果はPR/Issueへ追記し、検証したHEADを文書だけの追加commitで変えない。
