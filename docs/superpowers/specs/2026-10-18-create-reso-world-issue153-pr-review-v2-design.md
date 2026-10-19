# Issue #153: pr-review の非対話入口・全体差分・DSH の親保存

## 管理・実行許可

- 対象: `usaturn/create-reso-world`、https://github.com/usaturn/create-reso-world/issues/153
- 親: #116、ボード `review-automation-board`、子キー `pr-review-v2`
- 状態: draft（内容承認ではない）
- 実行許可: 利用者の `/skill:issue-to-pr #153`。同スキルに従い、通常の設計判断を推奨案で決め、Spec・Plan・実装・検証・commit・push・main 向け PR 作成まで進める。マージ・rebuild・認証設定変更は含まない。
- 基準: `origin/main` = `1335f410e624355cd558029bdcdad65eaa944ed8`。移植元: `usaturn/agent-workspace` の `a47b2065fddad76b7475752fd0088af0733de204`。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-153-pr-review-v2`、branch `feat/issue-153-pr-review-v2`。PARENT_ROOT は `/workspaces/reso-world`。
- 予約: `refs/heads/agent-claims/issue-153`、SHA `83bcb7048656aa990e2ba7ee9a0590ec3941c512`、セッション `6f2ec92e-caff-47d7-bd5c-a99cb9d6e322`。
- 親 #116 冒頭の「着手するエージェントへの注意（利用者決定: 2026-10-18）」と親 Spec D-1〜D-24 が適用される。tools/workspace・projects.toml は導入せず、review-fix-planning の致命的な指摘だけを直す基準・三択の結論・修正後の自己レビュー最大1回を変えない。
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue153-pr-review-v2.md`

## 意図・受け入れ

対話と runner の非対話で同じ prepare → PR 全体差分 → complete を使う。レビュー本文・候補 JSON・実行記録を親 checkout の `reviews/<owner>/<repo>/#<PR>-<branch>/` に保存する。DSH は親の取得済み情報だけを読み、親が停止と live HEAD を照合して正式保存する。

1. `uv run pytest .agents/skills/pr-review` が成功する。移植元の文言照合テストは持ち込まず、実行挙動だけを検査する。
2. 301 ファイル以上の PR 相当差分を手元の git で読み、本文と候補を保存できる（#59）。
3. レビュー中の HEAD 変更を保存時に拒否し、draft・state を保持する。明示的に新しいセッションを始め直せ、古い成果を保存しない（#134）。
4. fork と上流は PR 所属リポジトリで分離される。Git 操作の checkout と保存先を取り違えない。名前の規則は review_target.py に集約する。
5. 番号・URL の読取は新配置だけを解決する。旧レビューは自動で読まず、移動・上書きしない。cleanup と review-fix-planning の読取と説明も同じ PR でそろえる。
6. この子の PR で対話レビュー1回、DSH を含む2人を runner で並行起動する確認1回を行い、それぞれ本文・候補 JSON が保存されることを確かめる。成功を偽装せず、失敗時は reason・stop_confirmed・残存先を報告する。
7. README のテスト入口（Python 全体・shell 回帰・layout）、runner の雛形の check と git diff --check が成功する。private repository の Actions は無効なので CI は確認しない。

## 着手の根拠

2026-10-18 UTC、#150/#151/#152/#146 は全て CLOSED/COMPLETED。必要な PR #173/#170/#164/#160 は base main に MERGED で、その merge commit が最新 origin/main に含まれることを確認した。#151 の実DSH確認は #175 に分離されており、コード完了とは区別する。ローカルの dsh は 0.2.0-rc.2。#153 の open PR・既存 branch/worktree・担当・予約は取得前に無かった。既存 pr-review は 221 passed、終了コード0（28.46秒）。

## 範囲・禁止

変更するのは `.agents/skills/pr-review/`、`.devcontainer/agent-runner.toml` の workflows.review（after_run と assignments.inspect）、AGENTS.md の「PR レビュー結果」の行、repo-cleanup-after-merge の pr-review セッション・保存先を扱う箇所、review-fix-planning/SKILL.md の「第1引数の解決」と手順2の保存先・PR_REPO 決定、docs/resoloop-meshy-workflow.md の保存先の文、およびこの Spec・Plan。

`.agents/scripts/review_*.py`、tools/、ほかのスキル・workflow・agent・role は変更しない。旧レビューと他モデルのレビュー本文は読まない。共有インターフェースの変更が必要なら #116 に報告し、担当範囲を勝手に広げない。

## 決定記録

### D-1 移植する単位

- 選択: 移植元の4 helper（pr_review_workspace.py、pr_review_parent.py、review_run.py、review_run_record.py）と references/evidence.md・noninteractive.md を基に、既存の安全条件と移植先 resolver へ適応する。SKILL.md はその入口を説明する形へ更新する。
- 別案: 既存 helper のみに非対話を継ぎ足す。
- 理由: 親保存・候補 pair・provenance・run 記録を後続 #155/#156 と同じ公開の形で使える。重複実装を減らす。
- 委任: issue-to-pr の推奨案での設計判断。上流の過去の評価結果は本環境の成功として写さない。

### D-2 保存先と checkout の分離

- 選択: 保存先・保存ロック・fingerprint は PARENT_ROOT 基準。worktree/ref/object 操作は review_target.resolve が返す target_root/base_remote を使う。新しい target state は version 8 とし parent_root・target_root・target_kind・pr_repo を保持する。現行 version 7 の repository state は repo identity を含む既存の意味で保持し、上流の version 7（target state）と衝突させない。
- 別案: CODE_ROOT に成果を置く／現行の version 7 を別の意味に流用する。
- 理由: D-10 の親保存と #146 の fork/upstream 分離を両立し、残存セッションを誤解釈しない。
- 委任: 親 Spec D-10/D-11。既存の legacy create 互換経路にも pr_repo を要求し、安全条件を弱めない。

### D-3 resolver と専用 Git 領域

- 選択: review_target.py の命名・対象解決・fetch_pull_head API をそのまま使う。未知の repository は利用者の明示した source-root（code-root 相当）を resolver に渡し、main checkout と remote 一致を確かめる。resoloop の upstream PR では origin 一致を要求せず、resolver の base_remote=upstream を使う。既存 checkout を探索・clone しない。
- 別案: 上流の CloneTarget・tools/workspace・projects.toml を持ち込む／remote を origin に固定する。
- 理由: #152 の公開仕様と AGENTS.md のリポジトリ境界を守る。
- 委任: 親の利用者決定。親準備と DSH だけは helper が所有する一時 Git 領域を git init/fetch で作れる。これは欠けた対象 checkout を clone する経路ではなく、照合済み checkout/remote から完全な bundle を作るための隔離領域。既存 checkout を unshallow したり共有の追跡 ref/tag/FETCH_HEAD を動かしたりしない。

### D-4 共通入口と出力

- 選択: review_run.py の prepare/complete/fail/prepare-parent/finalize-parent/attach-runner を維持する。通常は PR head、明示 review-commit はその commit までの PR 全体を merge-base から読む。diff_command は `git -C <WT> diff --find-renames <base>..<reviewed_head>`。
- 別案: 非対話だけ別の手順／gh pr diff／commit 単体差分。
- 理由: #59 のAPI上限を避け、対話と runner を同じ検査に通す。
- 委任: 子 Issue の指定。本文は `<model>.md`、指定commitは `<model>-commit-<fullSHA>.md`。候補 JSON は findings/ 配下。prepare 成功は prepared、DSH 子 complete は staged、親の保存・cleanup 後だけ success。CLI の未観測値を推測で補わない。

### D-5 DSH の親保存

- 選択: 認証済み親が PR/参照 Issue の情報・コメント・判断記録と Git bundle を snapshot に固定する。descriptor の path/sha256 と bundle digest を子で検査する。子は GitHub token・API・remote fetch を使わず、専用領域でレビューし、draft digest を固定して staged を返す。親が runner の実 Request/Identity/停止確認/sensitive cleanup と成果の対応を検査し、live PR HEAD を保存ロック内で照合して保存・cleanupする。
- 別案: DSH に GitHub token を渡す／子の success 宣言だけを信頼する。
- 理由: 既存 DSH の限定 grant を広げず、動いた HEAD や改変された staging を正式成果にしない。
- 委任: 子 Issue の明示制約。認証不足・権限拒否を別 HOME・cache・full-access で回避しない。

### D-6 記録と雛形

- 選択: 候補 v2・本文 pair と run 記録を上流の形で保存。Unverified candidates は U-n 見出しか「なし」で始める。review workflow の after_run は finalize-parent → attach-runner の順。既定レビュアーは pi-gpt・devin-swe・dsh-ccd・claude-opus・pixg。
- 別案: 結果の件数だけ回収／記録をモデルが手書きする。
- 理由: 外側 success と payload success を区別でき、後続 #155/#156 が provenance を照合できる。
- 委任: 親 D-12/D-13。実行にはルートの Python 3.14 project を `uv run --project <skill-source-root> --locked python` で使う。tools/devenv と grok-build は移植しない。個人設定は書き換えない。

### D-7 テスト・実行方式

- 選択: 実行する helper のテストを先に移し、欠落による RED を観測してから実装を移す。#146 の実行テストを保ち、#59/#134 と外部 checkout の経路・parent/DSH binding を追加する。文面・モデル一覧だけを照合するテストは追加・移植しない。スキルの無し/ありの比較は同じ非対話 DSH の場面で各1回、別コンテキストの dry-run で手順・停止判断を比較する（純粋な参照手順のため文面 micro-test の反復はしない）。
- 別案: 上流の全テストを無条件コピー／文言の固定検査／多数の実モデル試行。
- 理由: AGENTS.md の採用基準と費用上限を守りつつ実行経路の安全を検証する。
- 委任: issue-to-pr。追加調査で、現行 workspace helper には移植元に無い journal/inspect/abandon/sessions と #146 の安全条件があると確認した。丸ごと置換せず、(1) workspace と候補pair、(2) runner・親入力・親保存、(3) 手順と読取側の3 Taskに分け、境界ごとに同期委譲する subagent-driven-development を選ぶ。各実装担当は1件ずつ直列に動かし、Taskレビューと最後の全体レビューは読み取り専用とする。独立調査・builder check・スキル比較も読み取り専用の subagent を使う。実装中の同期コマンドは終了コードとログを確認する。

## Builder check 後に具体化した事項

- 移植元は GitHub contents API の固定 commit から `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/donor/` に取得済み。`upstream-files.tsv` に blob SHA を保存し、Plan はこの snapshot を使う。引き継ぐ場合は同じ commit の各 path を contents API から新しい session dir へ取得し、blob SHA/内容を照合する。外部 checkout の clone はしない。
- 実機の構成: このセッションで、この子の PR を新入口で対話レビュー1回する。ほかのレビュー本文は読まずに完了する。runner の並行確認は `dsh-ccd` と `devin-swe` を各1回、fallbackなし。追加試行は失敗の原因を変えたとき1回までで、認証・安全の失敗は再試行しない。全体の branch review は fresh reviewer 1件で別途実施する。
- 起動の順: PR公開 → `prepare-parent --output-dir <SESSION/new-parent-input>` → descriptor を実 Request.prompt 末尾JSONの `parent_pr_data` に渡す → runner → `finalize-parent` → `attach-runner` → 結果の外側/内側と保存されたpairを確認。workflow に pre-run hook は足さない。
- DSH の子の領域は `PARENT_ROOT/reviews/<owner>/<repo>/#N-branch/.staging/<run>/<request>/<agent>/`。snapshot/bundle は caller 所有の `SESSION/new-parent-input`。target_kind は既存 checkout なら `checkout`、helper 所有の一時Git領域なら `bundle`（子の取得元を bundle だけに制限する。上流の `clone` から内部の呼出し側を合わせる）。成功したものだけ helper cleanup に任せ、失敗時は実在の残存先を記録し勝手に消さない。
- builder check の指摘は、既存API・手順・保存先の具体化としてこの節に反映した。利用者の内容承認を得たものとは扱わない。

## 未確定部分と停止条件

内部関数の細部は上流と既存テストを基準に実装者が決める。必要な API/ツールの失敗、依存/予約の競合、変更範囲の拡張、安全の失敗、予算超過、解消できない検証、Gitleaks の失敗では停止する。既存 #174/#175 の認証や adapter 本体をこの子で直さない。実機の並行レビューに失敗したら外側/内側の実結果を保持し、成功と報告しない。マージは利用者が行う。

## 公開前の実装・検証結果

- Task1 `8112185`、中断時の所有 bundle Git 復旧 `8ef6ebb`、Task2 `454f827`、Task3 `fbacf7c`、参照修正 `baebbc7`。元の journal/inspect/abandon/sessions と #146 の repository identity を保持した。
- 全体レビューの Important 2件（通常 shallow の履歴不足・DSH の再現用 scratch が許可範囲外）を `021973e` の1回の修正で対応。実Gitの RED→GREEN と304件の対象回帰を確認し、1回の修正差分レビューで両件 ADDRESSED・新規 Critical/Important 無し。2回目の全体レビューは行っていない。
- 最終コードで `uv run pytest tests/skills .agents/skills .agents/scripts tools`: **2652 passed / 565.88秒 / exit0**。対象304件は234.39秒/exit0。shell **33 PASS/exit0**、layout **PASS/exit0**。shellはAGENTSの省略参照1件で失敗した後、実在の完全パスに直して33本を再実行した。
- スキル無し/ありの同一dry-runを各1回。無しはhelper/schema/資格情報隔離の手順・入出力仕様の不足で停止、ありは親入力→共通prepare→固定全体差分→staged→親保存を提示した。自己repo DSHのsource-rootに小さな不確実性が残る回答だったが、bundle-onlyと元checkout不在の実行回帰で確かめている。dry-runは実機成功の証拠にしない。
- #59は301ファイルの実Git差分からpair保存・cleanupまで成功し、Closes対象とする。#134はmoving HEAD拒否・draft保持・fresh-session再開を検証したが、残存セッションの運用判断の全条件を解消したとは主張せず、Refsと結果報告にとどめる。
- PR: https://github.com/usaturn/create-reso-world/pull/182（main向け）。Gitleaksは公開前11commits/359331bytesを検査し検出無し、検査SHA `9652ca9c6dc88a03ca1b013a8ec15f054deb60fd` をそのままpushした。
- 2026-10-19 00:16 UTC、実機の並行runは **partial_success**。`devin-swe` は外側/内側success・本文と候補pair保存・cleanup成功。`dsh-ccd` は外側 **awaiting_approval**（exit0）で成果無し。DSHログには自身の `workspace-write mode` の file access denied がある。承認・権限を拡張した再試行はしていない。両試行ともstop_confirmed=true、sensitive_paths空、outside_changes空。parent finalize/attachはexit0だが、DSH成果が無いので全体成功ではない。
- watcherは235.86秒でexited_incomplete（wrapper exit1）、watcher_alive/target_aliveともfalse、residual_pids空。保存元は `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/live-runner/result.json`、要約は同ディレクトリの `live-summary.json`。モデルのレビュー本文は判断の出所にしていない。
- 非runner入口の依頼先sp-reviewはBash/書き込みツールを持たず、prepare/completeは未実施、成果物も未作成。実機受け入れ全体は未完了であり、#153を完了扱いしない。必要な権限/実行セッションの確認後に、成功済みDevinを繰り返さず残るDSHと非runner入口を確認する。状態はdraft、実機のゲートはblocked。マージしていない。

## resume-1の確認結果（2026-10-19）

利用者の再開指示で追加30分、総予算210分として、拒否操作の調査と非runner入口確認を実施した。コード・設計・許可範囲は変えず、以下は検証結果の追記である。

- DSHの拒否対象は、`.staging/`にある自身のMarkdown draftへのnative `write`。tool-call/権限メタデータだけを調べた。adapterが追加するbubblewrapの書込bindは、DSH自身のnative filesystem policyの追加writable rootsにはならない。導入済み`0.2.0-rc.2`は追加roots未対応であり、現在の許可・設定のまま成功させるサポート済み手段は確認できなかった。別cwd/HOME/cache、full-access、別ツールへの切替による迂回は行わず、DSHを再試行していない。
- 通常のBash/write可能な本Piセッションで非runnerの共通入口を1回実行した。対象`a6e394059279d8b44611654deb82b32ada6b189a`、実測`openai-codex/gpt-6.1-sol`。prepare、固定merge-baseからの全体差分取得、Markdown/候補pair保存、cleanupはすべてexit0・success。run記録も保存し、所有session/worktreeと自身のpinned refはhelperが削除した。314.976秒。
- 対象pytestは6 passed / 97 deselected / 11.58秒 / exit0。通常shallowの3入力、fake DSH隔離tempの証跡、Pi識別子の拒否・非runner unknownを実行。未読範囲を成果に明示し、active指摘0でも判定は`Needs manual verification`。入口の実行成功は独立レビューや実機受け入れ全体の完了ではない。
- 成果はPARENT_ROOTの`reviews/usaturn/create-reso-world/#182-feat-issue-153-pr-review-v2/`の`gpt-6.1-sol.md`、`findings/gpt-6.1-sol-a6e394059279.json`、`runs/20261019T032735Z-gpt-6.1-sol-6ec2767b.json`。今回の調査・実行ログは既存SESSIONの`resume-1/`。成功済みDevinの有料再実行、全体回帰の再実行はしていない。
- 残るblockerはDSHのnative policyと保存先の整合。adapter/tools/依存/許可範囲の変更や別cwdでの実行は今回の許可に含まれない。親 #116へ調整事項を返し、具体的な方針判断前に実行しない。新Issue・PR・branchは作らず、#153とPR #182はopenのまま、Spec/Planはdraft、実機ゲートはblocked/not ready。PR HEADが動いた後の古いsnapshotは再利用しない。
