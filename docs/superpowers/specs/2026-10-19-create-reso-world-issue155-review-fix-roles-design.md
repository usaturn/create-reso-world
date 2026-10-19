# Issue #155 review-fix-planning に役割の実行（run_roles）と最終化（finalize）をつなぐ

- 文書管理・対象: `usaturn/create-reso-world`、Issue #155（親 #116、ボード `review-automation-board`、子のキー `review-fix-roles`）
- 基準 HEAD: `8083a85eeb09c24818f9e00f537672a3217e6b78`（`origin/main`、2026-10-19）
- 移植元: `usaturn/agent-workspace@415b3669dc06d045fe81fb15be7d82f8864c5cef`（`main`、2026-10-19）。ボードの基準 `a47b2065` からの差は D-2
- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者が 2026-10-19 に `/issue-to-pr #155` と指示した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。着手の後に、利用者が「`/issue-to-pr #155 --merge` 相当で進めて」と指示した。これを、PR の作成後にレビュー修正のサイクル（D-13）を回し、修正不要と確かめたら PR をマージして #155 を閉じるまでの実行許可として扱う。どちらも実行の許可であり、この文書の内容の承認ではない。以下の判断は、D-15（2026-10-19 の利用者の決定）を除き、確認を取らずに決めたエージェントの判断である
- Plan: `docs/superpowers/plans/2026-10-19-create-reso-world-issue155-review-fix-roles.md`
- 参照: ボードの Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md` の D-1〜D-24、#116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」

## 意図

review-fix-planning が、agent-runner の設定の割り当てで、修正の実装・修正後の自己レビュー・修正の確認を runner で実行し（`run_roles.py`）、修正が不要なときに `finalize.py` で状況の投稿・マージ・関連 Issue の更新を行えるようにする。判断の記録（review-records）を読み書きし、次のサイクルや PR 修正ループ（#156）へ判断を引き継げるようにする。

#116 の利用者決定により、移植先の review-fix-planning の判断基準（現行 HEAD で確かめた致命的な指摘だけを直す）、三択の結論、修正後の自己レビューは最大 1 回、を変えない。runner・helper・記録は、この規則の中の手段として足す。

## 確認した事実（2026-10-19）

- 先行の #153（PR #182、`954bf1c`）と #154（PR #171、`03d9aac`）は `state_reason=completed` で close 済みで、PR は `main` に入っている。#149・#150・#151・#152 と、#169（PR #179、`34e7b67`。`review_records.read_state` の `trusted_login`）も completed で close 済み
- 移植元の `run_roles.py` が使う名前は、移植先にすべてある: `tools.agent_runner`（`load_config`・`resolve_config_path`・`run_workflow`・`Workflow`・`ConfigError`・`RunnerError`）、`tools.agent_runner.config.validate_config`、`tools.agent_runner.workspace`（`require_auditable_checkouts`・`resolve_revision`・`git_common_dir`・`CheckoutAuditError`・`WorkspaceError`）、review-verify の `dispatch.py`（`FixInput`・`check_review_directories`・`snapshot_review`・`review_changes`・`observed_verifier`・`time_limits`・`assigned_externally`・`fix_check_write_exceptions`・`failure_category`・`load_review_findings`）、`review_target.py`（`default_parent_root`・`repository_reviews_root`・`TargetError`）、pr-review の `review_run.py`（`helper_write_exceptions`。venv は `tool_root/.venv`）
- 移植先に無いもの: review-verify の `dispatch.py` の `assigned_read_only_sandbox`（移植元 #731）。移植先の codex の adapter も `writes=false` の役割を `-s read-only` で起動する（`tools/agent_runner/adapters/codex.py:202`）
- 移植元の `finalize.py` は `tools.workspace`（`projects.toml` の `ci_required`）を使う。移植先には無く、入れない（#116 の利用者決定、ボードの D-5）
- 移植先の `upsert_pr_comment.py` は記録なしの投稿だけを持ち、自分のマーカーを本文中の部分一致で探し、投稿者で絞らない。`.agents/review-records.md` 7.4 は、#155 で記録付きの投稿をつなぎ、記録付き・記録なしのどちらでも照合を `OWNER`・`MEMBER`・`COLLABORATOR` または認証済み利用者自身のコメントに限ると定める
- 記録付きの投稿は、`outcome` が `fixes_pushed` なら `commit`、それ以外なら `reviewed_head` が PR の head と同じときだけ投稿できる（7.4 の 2）
- 移植先の review-fix-planning の結論 2 は、create-reso-world の PR では、完了した Spec を PR の head に commit して push してからマージする（`AGENTS.md`「create-reso-world 自身の変更に伴う文書は、その作業の PR に含める」）。移植元は review-fix の Spec を commit しない
- review-verify の `fix-check.md` は、呼び出し側が `review_dir` を D-10 のパスに一致させると書く。`dispatch.py` はこれを強制せず、`review_dir` とその祖先・`verified` のリンクだけを拒否する。dispatch から accept までは `review_dir` 全体の snapshot を照合する
- pr-review の `review_run.py` の `read_records` は `trusted_login` を渡さない
- 雛形 `.devcontainer/agent-runner.toml` には `[workflows.review]` まであり、`[workflows.fix]` は無い。`claude-opus` は #150 が定義済み
- SKILL.md の手順のテスト（`tests/test_review_fix_planning_skill_contract.py`）は、SKILL.md の `--pr "$PR_NUMBER"` を含む bash ブロックが 1 つで、投稿ブロックが外部への操作の前に共通 context の確認で止まることを、ブロックを実行して確かめる
- #156 の移植元の `loop.py` は、`run_roles.py` の `project`・`reject_dsh_review_agents`・`reject_codex_review_agents`・`RoleInputError`・`failure_reason` と `roles.json`、`finalize.py` の結果（`outcome`・`merged`・`issues`・`stop_reason`）を使う。マージ済みなら PR の head がそのサイクルの HEAD と同じことを確かめる

## 判断（決定記録）

各項目に、選択した案・検討した別案・選択理由・委任の指示または停止の条件を書く。

### D-1 判断基準・三択・自己レビューの上限

- 選択した案: 移植先の SKILL.md の「依頼の種類と結論」「分類の仕様」（致命的・3 区分）「三択の結論」「修正後の自己レビュー」（最大 1 回、その後の修正は再レビューせずに記録する）「同じ条件の再発と設計の見直し」を残し、runner・helper・記録を、その規則の中の手段として足す。移植元の SKILL.md の構成と `references/decisions.md`（H・D1・N・Hold）は採否の基準として持ち込まない。移植元の結果の語（`fixes_pushed`・`no_fix_needed`・`stopped`）は、記録の `outcome` の値としてだけ使う
- 検討した別案: 移植元の SKILL.md に置き換える。`decisions.md` を参照として持ち込む
- 選択理由: #116 の利用者決定。移植元の規則は、自己レビューの枠を使った後に必須の修正でレビューの根拠が失われると停止するが、移植先は直して検証し、再レビューしないことを記録して push する。持ち込むと結論が変わる
- 委任の指示・停止の条件: 利用者決定のとおりで、議論し直さない。変える必要が出たら #116 にコメントし、調整役が決める

### D-2 移植元の基準

- 選択した案: 移植元 `415b366` の review-fix-planning の scripts・tests を基にする。ボードの基準 `a47b2065` からの差は #731（self-review・fix-check への codex の担当の拒否）だけである。移植先の review-verify には判定の関数が無く、変えられないので、同じ判定（`READ_ONLY_SANDBOX_RUNTIMES = {"codex"}`、一次担当と fallback、`self` を除く）を `run_roles.py` の中に置く
- 検討した別案: ボードの基準 `a47b2065` に固定する
- 選択理由: 移植先でも codex は read-only の sandbox で起動し、pr-review・review-verify の helper が uv のキャッシュ・一時ディレクトリ・保存先に書けない。割り当てると戻せない 1 回枠だけを消費する。#156 が `415b366` 以降の `loop.py` を移植すると `reject_codex_review_agents` を呼ぶ
- 委任の指示・停止の条件: review-verify の `dispatch.py` 自身（codex の fix-check を直接 dispatch する経路）には #731 の拒否が無いまま残る。#154 の領域なので #116 に申し送る

### D-3 `run_roles.py`

- 選択した案: 移植元の `run_roles.py` を、名前と入出力を変えずに置く（下の「インターフェース」）。移植先への適応は、helper の読み込み先を移植先の #149・#152・#153・#154 の実装にすること、uv の起動を `uv run --project "$TOPLEVEL" --locked python`（ルートの project。`tools/devenv` は無い）にすること、codex の判定（D-2）だけである。DSH の拒否（移植元 #671・#675）はそのまま持つ
- 検討した別案: implement と self-review を別のスクリプトにする。SKILL.md から runner の CLI を直接使う
- 選択理由: `run_roles.py` の入出力と関数は、#156 が使う共有インターフェースで、#155 が決める（#116 の「共有インターフェースと担当」）。移植元の名前と形を変えなければ、#156 はそのまま接続できる（#116「移植元の名前と形は移植のために変えない」）
- 委任の指示・停止の条件: なし

### D-4 `finalize.py` の CI とマージの範囲

- 選択した案: `tools.workspace` を使わず、2 つの固定値を `finalize.py` に持つ。`--registry` は無くす
  - CI の要否（ボードの D-5、`AGENTS.md`「GitHub Actions」）: `usaturn/create-reso-world`・`usaturn/resoloop-meshy` は確かめない。`usaturn/resoloop` は PR の checks が成功していること。表に無いリポジトリは確かめる（知らない対象を免除しない）
  - マージしてよい範囲（移植先の SKILL.md「マージしてよい範囲」）: `usaturn/create-reso-world`・`usaturn/resoloop` だけ。範囲外は GitHub に問い合わせる前に `permission:` で止める
- 検討した別案: CI の表だけを持ち、マージの範囲は SKILL.md の手順だけで守る。issue-to-pr の `resolve_issue.py` の表を読み込んで共有する
- 選択理由: マージは取り消せない操作なので、手順だけでなく、マージを実行する helper でも範囲を守る（#116「マージ権限を変えない」）。`resolve_issue.py` の表は Issue の対象（3 つのリポジトリ）で、マージの範囲と違う。resoloop-meshy は CI の表にあるが（ボードの D-5）、マージの範囲の外なので、CI を見る前に止まる
- 委任の指示・停止の条件: なし

### D-5 結論 2 の Spec の commit（`--spec-commit`）

- 選択した案: `finalize.py` に `--spec-commit <SHA>` を足す。create-reso-world の PR の結論 2 では、planner が次の順で進める
  1. 完了した Spec を専用の worktree でローカルに commit する（S。親は検証した HEAD）
  2. PR の head がまだ検証した HEAD のうちに、記録付きの状況コメント（`no_fix_needed`）を `upsert_pr_comment.py --records-file` で投稿する
  3. S を「push の前の秘密情報の検査」の形で fast-forward で push する
  4. `finalize.py --spec-commit S` を実行する

  `--spec-commit` があるとき、`finalize.py` は投稿しない。代わりに、(a) このサイクルの自分の状況コメントの記録が渡した記録と同じこと、(b) GitHub の比較（`repos/<repo>/compare/<reviewed_head>...<S>`）で S が `reviewed_head` の直接の子の 1 commit で、変更が `docs/superpowers/specs/` の直下の Markdown 1 ファイル（追加か変更）だけであること、(c) PR の head が S であることを確かめ、S を `--match-head-commit S` でマージする。`--spec-commit` は create-reso-world の PR だけで受け付ける。結果には `spec_commit` を入れる
- 検討した別案: (i) 結論 2 では Spec を PR に載せず、文書用のブランチに置く（公開未実施）。(ii) 記録付きの投稿の head の規則（review-records.md 7.4）を緩め、Spec だけの子を許す。(iii) create-reso-world の PR では `finalize.py` を使わず、今の手順でマージする
- 選択理由: 記録付きの投稿は、`no_fix_needed` では PR の head が `reviewed_head` と同じときだけ投稿できる（#152 の仕様）。移植先の結論 2 は Spec を PR の head に載せてからマージするので、そのままでは投稿できない。(i) は `AGENTS.md` の公開の規則に反する。(ii) は #152 の仕様の変更で、調整役の判断が要る。(iii) は create-reso-world の PR に `finalize.py` が届かず、#156 の `--finalize-result` も使えない。投稿を Spec の push の前に移せば、7.4 も `AGENTS.md` も変えずに済む
- 委任の指示・停止の条件: 比較の検査が通らない、記録が投稿されていない・食い違うときは `environment:` で止め、マージしない。#156 の `loop.py` は、マージ済みなら PR の head がサイクルの HEAD と同じことを確かめるので、`spec_commit` のときの照合を #156 に申し送る

### D-6 `upsert_pr_comment.py` の記録付きの投稿と認証済みの login

- 選択した案: 移植元の記録付きの投稿（`--records-file`、`upsert(..., record=None)`、`view_pr`・`find_round_comment_id`・`_checked_record`・`_check_pull_request`・`_round_target`）を移す。review-records.md 7.4 のとおり、記録付き・記録なしのどちらでも、照合の対象を `OWNER`・`MEMBER`・`COLLABORATOR` または認証済み利用者自身のコメントに限る。login は helper が `gh api user --jq '.login // empty'` で取り、失敗・空なら投稿せずに止める（終了コード 64）。同じ login を `read_state(..., trusted_login=login)` に渡す。`finalize.py` も同じ関数で login を取る。マーカーは行全体の一致で比べる
- 検討した別案: login を SKILL.md のシェルで取り、`--trusted-login` で helper に渡す
- 選択理由: 投稿ブロックは SKILL.md の手順のテストが実行し、外部への操作の前に共通 context の確認で止まることを確かめている。シェルで先に `gh api user` を呼ぶと、その確認より前に外へ問い合わせる。helper の中なら、PR の解決と同じ `gh` の経路で取得・検査でき、`--trusted-login` の渡し忘れで三つの区分だけを読む挙動に黙って戻ることも無い
- 委任の指示・停止の条件: 既存の挙動の変化として、記録なしの投稿も、信頼しない投稿者のマーカー付きコメントを自分のコメントとして更新しなくなる（7.4 が求める）。`upsert(pr, repo, model_name, markdown, *, runner=None)` の呼び方は保つ

### D-7 判断の記録の写し方

- 選択した案: 新しい記録は `review-records/v2`（`provenance` つき）で書く。移植先の 3 区分を `state` に写す: 解消済み → `resolved`、対応する → `fix`、対応しない → `skip`（`revisit_when` が必須）。`hold` は使わない（移植先に判断保留は無い）。`unverified` は結論 3（`stopped`）の記録でだけ使う（停止の原因で確かめ終えられなかった指摘。`unverified_reason` に足りない確認を書く）。`severity` にはレビューの重大度のラベルを写す（`U-<n>` だけの判断は null）が、採否の根拠にしない。`d1` は書かない。`fix` の `reason` には、致命的である理由（実在する構成で到達できる条件）と (a)〜(d) のどれに当たるかを書く。planner が確認の途中で見つけた PR の欠陥（SKILL.md の「自己確認」）は、参照を `planner#S-<n>@<reviewed_head の先頭 12 桁>` とし、`severity` には planner の見積もりを書く（記録の検査は参照のファイル名を形式だけで確かめ、レビュアーの構成と照合しない）。三択を `outcome` に対応させる: 結論 1 → `fixes_pushed`（`commit` は push した SHA）、結論 2 → `no_fix_needed`、結論 3 → `stopped`（`stop_reason` は `permission:`・`environment:`・`external:` に具体的な障害）。前のサイクルの判断の扱いは review-records.md 8.4 に従う
- 検討した別案: v1 で書く。`hold`・`unverified` を結論 1・2 でも使う
- 選択理由: review-records.md 6.2 は新しい記録を v2 と定める。移植先の「未確認は結論ではない」により、未確認を残したまま修正不要・push にしない（`no_fix_needed` の照合も `unverified` を拒否する）
- 委任の指示・停止の条件: 記録を読めない（壊れた記録・`gh` の失敗）ときは、判断を引き継げないので結論 3 にする（review-records.md 8.4。結論 3 の「環境」「外部障害」に当たる）

### D-8 SKILL.md の接続と references

- 選択した案: 「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方（#153 の担当）は変えずに、次を変える
  - 手順 1: 判断の記録を読み、サイクルの番号と前の判断を決める（`references/round-records.md`）
  - 手順 3: 確認済みの一覧（D-9）を根拠の 1 つとして使う
  - 手順 4: 分類を記録の `state` に写す（D-7）
  - 結論 1: 修正は `run_roles.py --phase implement`、自己レビューは `--phase self-review` の 1 回（`references/execution.md`）。push の後に記録付きで投稿する
  - 結論 2: 状況の投稿・CI・マージ・関連 Issue の更新は `finalize.py`（D-4・D-5）
  - 結論 3: PR が open で記録を読めた場合は、記録付きで投稿する（`stopped`）。ただしマージしてよい範囲の外のリポジトリ（上流の `orange3134/resoloop` など）では、今の規則（commit・push まで行ったターンだけ投稿が必須）を保ち、投稿を必須にしない（外部のリポジトリへの書き込みを増やさない）
  - 修正後の自己レビュー: 1 回は `run_roles.py --phase self-review` の 1 回の呼び出し。self-review の役割（pr-review の非対話の入口で、`--review-commit` を使う PR 全体の再レビュー）が観点 2、fix-check の役割（review-verify の fix_check）が観点 1・3 を受け持つ
  - 作業終了前の PR 投稿: 投稿ブロックに `--records-file "$ROUND_JSON"` を足す。計画のみで承認を待つターンに投稿するときは `stopped`（`permission: 計画のみの依頼のため、実装の承認を待つ`）の記録にし、承認・push の後に同じサイクル（同じ番号と `reviewed_head`）のコメントを `fixes_pushed` に更新する（新しい記録の結果に承認待ち（`awaiting_approval`）を書かないため。review-records.md 6.2）
  - 合理化の表・Red flags: 自己レビューの役割の外で pr-review を起動しない、2 回目の `run_roles.py --phase self-review` を起動しない、記録なしの投稿に切り替えない、を足す

  新しい `references/execution.md`（役割の実行と最終化）と `references/round-records.md`（記録の作り方と投稿）は、移植元の同名の文書を基に、移植先の 3 区分・結論・パス・規則に直して置く。移植元の `references/decisions.md`・`porting.md` は持ち込まない
- 検討した別案: 移植元の SKILL.md の 6 節の構成に書き直す。コマンドをすべて SKILL.md の本文に書く
- 選択理由: 判断の規則の文面を残したまま手段だけを差し替えると、旧版との判断の差が出にくい（D-12 で確かめる）。詳しいコマンドを references に置くと、SKILL.md の手順のテストの前提（`--pr "$PR_NUMBER"` を含む bash ブロックが 1 つ）も保てる
- 委任の指示・停止の条件: なし

### D-9 確認済みの一覧・工程の記録・fix-check の保存先

- 選択した案:
  - 手順 3 で `REVIEW_DIR/verified/<HEAD12>.json` を確かめる。無い・不正・現行 HEAD のものでない・今回のレビュアーの入力と合わないときは、review-verify（mode cycle）で作る。一覧の判定（`confirmed`・`not_reproduced`・`unverified`）は根拠の 1 つで、分類は「分類の仕様」で決める。review-verify が一覧を作れないときは、理由を Spec に書いて自分の検証を続ける。結論 1 の自己レビュー（fix_check）は一覧が無いと始められないので、そのときは結論 3（環境）にする
  - 工程の記録（`REVIEW_DIR/verified/<HEAD12>.planning.json`、review-findings v2）: 自己レビューの前に仮の版（`outcome` は `stopped`、`comment_id` は null、`activities` に `pre_push_review` を入れない）を作り、`run_roles.py` が枠を予約する。サイクルの最後に同じファイルを更新し、予約の行を消さない。確認済みの一覧が無いサイクルでは作らない
  - fix-check の `review_dir` には、自分の一意の作業ディレクトリの中に作った独立の保存先を渡す（入力の一覧だけを写し、symlink にしない）。外部の担当は accept、self は validate の後に、成果 2 件と要約を同じ内容で `REVIEW_DIR/verified/` に取り込む。同じ名前で内容が違うファイルが既にあれば上書きせずに止める
- 検討した別案: fix-check の `review_dir` に `REVIEW_DIR` をそのまま渡す
- 選択理由: `run_roles.py` は self-review と fix-check を同時に動かし、self-review（pr-review）は `REVIEW_DIR` に保存する。dispatch から accept までは `review_dir` 全体の snapshot を照合するので（#154）、同じディレクトリだと accept が拒否する。移植元も同じ理由で独立の保存先を使う。最終の保存先は取り込み先の `REVIEW_DIR`（D-10）である
- 委任の指示・停止の条件: review-verify の `fix-check.md` の「呼び出し側が `review_dir` を D-10 のパスに一致させる」と、`run_roles.py` 経由の独立の保存先は食い違う。review-verify は #155 の「変えないもの」なので、#116 に申し送る

### D-10 雛形の `[workflows.fix.assignments.*]`

- 選択した案: `implement` は `["claude-opus"]`、`self-review` と `fix-check` は `["self"]`（ボードの D-13、移植元の雛形と同じ）。`exclude_same_model_as` は置かない
- 検討した別案: `implement` も `self` にする
- 選択理由: ボードの D-13 で決まっている。`claude-opus` は #150 が定義済みで、雛形の検査（`invalid_reference`）を通る
- 委任の指示・停止の条件: なし

### D-11 テスト

- 選択した案: 移植元の `test_run_roles.py`・`test_finalize.py`・`test_upsert_pr_comment.py` を基にし、偽の `gh`・偽の adapter・一時の Git だけを使う。実際の PR をマージするテストにしない
  - `test_run_roles.py`: PR の slug を移植先の例にし、venv のパスを `ROOT/.venv` にする
  - `test_finalize.py`: `projects.toml` の fixture を外し、固定値（D-4）と `--spec-commit`（D-5）の正常・拒否の場面に置き換える
  - `test_upsert_pr_comment.py`: 移植元の記録付きの投稿の場面を移し、認証済みの login の場面（取得の失敗・空で止まる、自分の login のコメントを読む・更新する、`CONTRIBUTOR` を信頼しない）を足す。既存のテストの偽の `gh` に login と投稿者を足す
  - SKILL.md の手順のテスト（`test_review_fix_planning_skill_contract.py`）は移植先の版を保つ。移植元の版（文面の照合）は写さない。`AGENTS.md`「テストの採用基準」に反する移植元のテスト（文言の照合など）は写さない
- 検討した別案: 移植元のテストを全部そのまま写す
- 選択理由: Issue の受け入れ条件と `AGENTS.md`「テストの採用基準」
- 委任の指示・停止の条件: なし

### D-12 行動の評価

- 選択した案: 移植元の `evals/decision-packet.md`・`safety-packet.md` に相当する場面を、移植先の基準（3 区分・三択・自己レビュー 1 回・判断保留なし）と、`run_roles.py`・`finalize.py` の場面に合わせて作る。スキル無し・旧版（`main` の SKILL.md）・新版の 3 条件で、新しいコンテキストのサブエージェントに同じ packet を答えさせ、判断基準が変わっていないかを採点する。packet・採点の基準・結果を `evals/` に置き、`evals.json` に場面を足す
- 検討した別案: 移植元の packet をそのまま使う
- 選択理由: 移植元の packet の問いの一部（`hold-action`、H・D1、1 回枠の消費後の停止）は、移植先の規則では答えが違う
- 委任の指示・停止の条件: 旧版と新版で判断（区分・結論・自己レビューの回数）が食い違ったら、新版の文面を直してから PR を作る

### D-13 「`--merge` 相当」のサイクル

- 選択した案: PR の作成後、次のサイクルを最大 3 回まで回す（移植元の pr-review-fix-loop の既定の上限）
  1. 親の main checkout の pr-review で、agent-runner の設定（雛形と個人設定）の `workflows.review` の inspect のレビュアーを runner で並行に起動し、PR の現行 HEAD をレビューする
  2. 親の main checkout の review-fix-planning を完遂で実行する（PR で変更中の版は使わない）。結論 1 なら push して次のサイクルへ進み、結論 2 ならマージと #155 の close で終わり、結論 3 なら止まる
  3. 3 回目で修正を push したままなら、マージせずに未完了として報告する

  PR は draft にしない。実装の最後のブランチ全体のレビューは行わず、1 サイクル目のレビューで代える（移植元の `--merge`）。Task ごとのレビューは残す。予約は、サイクルの終了と結果の記録の後に解放する
- 検討した別案: `--merge` は未対応として止まる（今の issue-to-pr の規則）。PR の作成で止める
- 選択理由: 利用者の明示の指示。#116・ボードの D-21 のマージの条件（利用者の明示の指示）を満たす。main の版のスキルを使うのは、変更中のスキルで自分の PR を判断しないため（移植元も親の main worktree のスキルを使う）
- 委任の指示・停止の条件: レビュアーの起動の失敗、review-fix-planning の結論 3、サイクルの上限は、それぞれ停止として報告する

### D-15 現行の PR head を再実行したレビュアーがいないサイクル（利用者の決定）

- 選択した案: レビューディレクトリの `<model>.md` のうち、Review history の最後の HEAD が現行の PR head と同じもの（判断の記録の `rerun` が `true` になるレビュアー）が 1 つも無いときは、結論 3（環境: 現行の HEAD を再実行したレビュアーがいない）にし、「現行の HEAD でレビューを取り直す」を次の操作として報告する
- 検討した別案: (i) 修正が要るときだけ、最新のレビュー HEAD を `reviewed_head` にして結論 1 まで進め、修正不要のときだけ止める。(ii) planner が agent-runner の既定のレビュアーで現行の HEAD のレビューを起動してから判断する
- 選択理由: 記録の形式（#152）は、`stopped` 以外の記録に `rerun` が `true` のレビュアーを 1 つ以上求め、記録付きの投稿と `finalize.py` は `no_fix_needed` のとき PR の head と `reviewed_head` が同じことを求める。今の review-fix-planning は古いレビューの指摘を現行 HEAD で確かめて結論 1・2 に進めるが、記録をつなぐとその記録を作れない。2026-10-19 に、builder check でこの論点を見つけ、利用者に確認した（AskUserQuestion）。利用者が「結論 3 で止める」を選んだ（移植元と同じ扱い）
- 委任の指示・停止の条件: 利用者の決定。結論 3 の環境の停止の条件が 1 つ増えることを #116 に記録する

### D-14 範囲外と、調整役に申し送る論点

- pr-review の `read_records` は `trusted_login` を渡さない。上流の PR では、利用者自身の判断の記録を pr-review が読まない（#153 の領域）
- review-verify の `dispatch.py` には #731 の codex の拒否が無い（#154 の領域。D-2）
- review-verify の `fix-check.md` の `review_dir` の文面と、`run_roles.py` の独立の保存先の食い違い（#154 の領域。D-9）
- review-records.md 7.4 の「移植先の今の helper は記録なしの投稿だけを持つ」は、この変更の後は事実と違う（#152 の領域）
- #156 の `loop.py` の、`spec_commit` のときのマージ済みの照合（D-5）
- 自己確認の参照 `planner#S-<n>@<HEAD12>`（D-7）は、review-records.md 2.1 に無い移植先の取り決めである（#152 の領域）
- 現行の PR head を再実行したレビュアーがいないサイクルを結論 3 にしたこと（D-15、利用者の決定）
- `run_roles.py` から実際の外部の担当（implement の `claude-opus` など）を起動する確認は、費用がかかるので行わない。テストは偽の adapter で行い、CLI は `self` の割り当てで実際の雛形を読む確認だけを行う

これらは `#116` にコメントし、調整役が決める。この PR では直さない。

## インターフェース

### `run_roles.py`

```bash
uv run --project "$TOPLEVEL" --locked python \
  "$TOPLEVEL/.agents/skills/review-fix-planning/scripts/run_roles.py" \
  --phase implement|self-review --request <role-input.json> --output-dir <新しいディレクトリ> \
  [--planning-file <絶対パス>] [--fix-input <fix-input.json>] \
  [--template <path>] [--config <path>] [--assign <role>=<agent|self>]...
```

- 依頼（RoleInput）: `repository`（絶対パス）・`source_head`・`revision`（完全な SHA）・`pr`（`repository`・`number`）・`prompt`（役割ごとの完全な依頼）の 5 項目だけ。未知のキーは拒否する
- `--phase implement` は `implement` だけ、`--phase self-review` は `self-review` と `fix-check` を 1 回の `run_workflow`（concurrency=2）で起動する。fallback と同じモデルの除外は保ち、投影できない設定は拒否する。`fix-check` の期限は 1800 秒に切り詰める
- 予約より前に止める入力: 設定の投影の誤り、self-review・fix-check への DSH・codex の担当（一次担当・fallback）、依頼の形、解決できない revision、既にある出力先、役割の依頼の欠け、checkout の監査の失敗、外部の self-review の書き込みの例外を作れない、fix-input と依頼の不一致、確認済みの一覧の誤り（`verified` でない、PR・`source_head` の不一致）、`review_dir` のリンク
- 予約: `--planning-file` の v2 の工程の記録に、`activities` の `stage=pre_push_review` を 1 件足す（排他ロックと一括置換）。既にあれば拒否する。失敗・中断でも戻さない
- 出力: `<artifact_dir>/roles.json`（`request`・`batch`・`self_prompts`・`review_changes`）、self-review では `<artifact_dir>/fix-check-receipt/dispatch.json`（review-verify の accept の入力）。標準出力は `state`・`artifact_dir`・`pending_self`・`outside_changes`・`checkout_audit`・`review_changes` の JSON
- 終了コード: 0 は全役割を回収した（`self` を含む。修正の合格ではない）、1 は失敗・停止未確認・領域の変更・checkout の監査の失敗、2 は入力・設定・起動の誤り（理由を標準エラー出力に出す）

### `finalize.py`

```bash
uv run --project "$TOPLEVEL" --locked python \
  "$TOPLEVEL/.agents/skills/review-fix-planning/scripts/finalize.py" \
  --record-file <round.json> --body-file <status.md> --checks-file <checks.json> --result-file <result.json> \
  [--spec-commit <SHA>]
```

- 検証の記録: `{"head": <reviewed_head>, "commands": [{"argv": [...], "exit_code": 0}, ...]}`。実際に実行した argv と終了コードを書く
- 順序（`--spec-commit` なし）: 入力の検査 → マージの範囲 → PR の状態・head → 全コメントとの照合 → CI → 状況の投稿 → PR の状態・head・CI の再確認 → `--merge --match-head-commit <reviewed_head>` → マージ済みと head の確認 → 同じリポジトリの closing Issue の close と読み戻し
- 順序（`--spec-commit` あり）: 入力の検査 → マージの範囲（create-reso-world だけ）→ PR の状態・head（S）→ 比較の検査 → 投稿済みの記録の照合（投稿しない）→ CI → `--merge --match-head-commit <S>` → マージ済みと head の確認 → closing Issue
- 結果: `{"outcome": "no_fix_needed"|"stopped", "merged": bool, "issues": [番号], "stop_reason"?, "wait_for"?: "ci"|"mergeable", "comment"?, "spec_commit"?}`。終了コード 0 は `no_fix_needed`、1 は `stopped`、2 は入力・結果ファイルの障害
- 同じ head で既にマージ済みなら、このサイクルの自分の記録が渡した記録と同じときだけ、投稿もマージもせずに Issue の更新を続ける。記録が無い・食い違うまま手でマージされていれば、Issue を更新せず `merged: true` の `stopped` を返す
- admin・auto マージ、ブランチの削除はしない

### `upsert_pr_comment.py`

- `--records-file <round.json>` を付けると記録付きの投稿（review-records.md 7.4）。付けなければ記録なしの投稿
- どちらも、`gh api user --jq '.login // empty'` で認証済みの login を取り、失敗・空なら投稿しない（終了コード 64）。照合の対象は `OWNER`・`MEMBER`・`COLLABORATOR` または login が一致するコメントだけ
- `upsert(pr, repo, model_name, markdown, *, runner=None, record=None)`

## 受け入れと確かめ方

| Issue の受け入れ条件 | 確かめ方 |
| --- | --- |
| 移植したテスト（偽の gh・偽の adapter・一時の Git）が通る。実 PR をマージするテストにしない | `uv run pytest .agents/skills/review-fix-planning`。テストは `gh` を偽物に差し替え、Git は一時ディレクトリ |
| `finalize.py` が、HEAD が動いた・公開リポジトリの CI が足りない・手でマージ済み・Issue の更新の失敗を、完了と誤らない | `test_finalize.py` の該当の場面（移植元の場面と、`--spec-commit` の場面） |
| `run_roles.py` が self・外部・混合の割り当てで同じ入力・成果・回数を守り、2 回目の自己レビューを拒否する | `test_run_roles.py` の該当の場面 |
| 行動の評価（スキル無し・旧版・新版） | D-12 の記録 |
| テストは「テストの採用基準」に従う | 差分の確認と、Task ごとのレビュー |
| 全体の検証 | `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` |

## 範囲

変えるもの: `.agents/skills/review-fix-planning/`（SKILL.md の「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方を除く）、`.devcontainer/agent-runner.toml` の `[workflows.fix.assignments.*]`、この Spec と Plan。

変えないもの: `.agents/scripts/review_*.py`、`tools/`、`.agents/skills/pr-review/`・`review-verify/`・`pr-review-fix-loop/`、`AGENTS.md`、`.agents/review-records.md`・`review-findings.md`、ほかの子の担当。

## 実装者に任せること

- references の文書の分け方と、移植元の文書からどこまで写すか（判断の規則に関わる部分は SKILL.md に従わせる）
- テストの細かな分け方と、移植元のテストのうち移植先で意味のあるものの選び方（`AGENTS.md`「テストの採用基準」の範囲で）
- 行動の評価の packet の細かな事実（移植元の場面に相当し、移植先の規則で答えが決まるもの）
