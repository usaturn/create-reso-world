# Issue #156 pr-review-fix-loop（レビュー修正ループ）を取り入れる

- 文書管理・対象: `usaturn/create-reso-world`、Issue #156（親 #116、ボード `review-automation-board`、子のキー `fix-loop`）
- 基準 HEAD: `8f5074ac14b43803b334f8256e4273b97a40a0f3`（`origin/main`、2026-10-19。#155 の PR #186 のマージ）
- 移植元: `usaturn/agent-workspace@415b3669dc06d045fe81fb15be7d82f8864c5cef`（#155 と同じ基準）。2026-10-19 の移植元の `main`（`ff3629057a786809971c25ef27bff2adef877287`）との差は `.devcontainer/agent-runner.toml` の 1 行だけで、`.agents/`・`tools/` は同じ
- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者が 2026-10-20（JST）に `/issue-to-pr #156 --merge` と指示した。この版の issue-to-pr は `--merge` を受け付けない（#158 で入る。helper が「#116 で入れる予定」と終了コード 2 で止めた）。2026-10-19 に利用者が確認した運用（#157・#155 の「`--merge` 相当」）に従い、オプションを外して着手し、PR の作成後にレビュー修正のサイクル（D-17）を回し、修正不要と確かめたら PR をマージして #156 を閉じるまでの実行許可として扱う。どれも実行の許可であり、この文書の内容の承認ではない。以下の判断は、確認を取らずに決めたエージェントの判断である
- Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue156-pr-review-fix-loop.md`
- 参照: ボードの Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md` の D-1〜D-24、#116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」、#155 の Spec `docs/superpowers/specs/2026-10-19-create-reso-world-issue155-review-fix-roles-design.md`、#155 からの申し送り（#156 のコメント 6269930398、#116 のコメント 6269370814）

## 意図

`/pr-review-fix-loop <PR>` で、agent-runner で並行に起動したレビュアーのレビューと、review-fix-planning による修正・push・最終化を、マージ・停止・サイクルの上限まで繰り返せるようにする。スキルを起動したセッション（司令塔）が review-fix-planning の手順で判断し、helper（`scripts/loop.py`）が、PR ごとのロック、PR の HEAD の照合、レビュアーの結果の検査、同じ commit の再レビューの省略、判断の記録の照合、資源の回収を受け持つ。#158 の issue-to-pr の `--merge` は、この helper の `check-options` と `start` を使う。

#116 の利用者決定により、判断の基準（現行 HEAD で確かめた致命的な指摘だけを直す）、三択の結論、修正後の自己レビューは最大 1 回は review-fix-planning のまま変えない。loop は判断の記録を照合するだけで、採否を決めない。

## 確認した事実（2026-10-19〜20）

- 先行 #155 は `state_reason=completed` で close、PR #186 は `main` にマージ済み（`8f5074a`）。着手の時点で、#156 に open PR・予約 ref・worktree・branch は無かった
- 移植元の `loop.py` が使う名前は、`review_target.require_planning_owner` を除いて移植先にすべてある（`tools.agent_runner` の `Assignment`・`BatchResult`・`Config`・`ConfigError`・`Request`・`Result`・`RunnerError`・`load_config`・`resolve_config_path`・`run_workflow`、`adapters` の `Adapter`・`load_adapter`、`hooks.run_after_run`、`review_records` の `comments_from_api`・`read_state`・`extract_record`・`validate_record`・`check_against`・`RecordError`、`review_findings` の `validate_document`・`check_pair`、pr-review の `review_run` の `helper_write_exceptions`・`prepare_parent`・`finalize_parent_batch`・`parent_data`・`workspace`・`FAILURES`、`run_roles` の `project`・`reject_dsh_review_agents`・`reject_codex_review_agents`・`RoleInputError`・`failure_reason`）。移植先の worktree で import して確かめた
- 移植先の `review_target.py` は planning の owner の制限を持たない（`--for-planning` は互換のために受け付けるだけ）。PR の Git 操作の対象は `target_checkout`（`scripts/superpowers_context.py` の `review-workspace`）で決まり、`CODE_ROOT` を渡さなければ create-reso-world（親）と usaturn/resoloop・orange3134/resoloop（`external/resoloop`）だけが決まる。終了コードは移植元と一部違う（10 が無く、12 は fetch）
- 移植先の review-fix-planning には判断保留（Hold）が無い。全ての指摘を「解消済み・対応する・対応しない」に振り分け、判断の記録の `state` に写す（#155 の D-7）
- 移植先の DSH の adapter は、`sandbox_write_paths` が空でないと起動を拒否する（`tools/agent_runner/adapters/dsh.py`）。runner は DSH の試行に、その attempt の review-scratch・outbox・HOME・tmp・state だけを書き込みの例外として付け、呼び出し側の `write_exceptions` を DSH には渡さない（`tools/agent_runner/runner.py`、#183）
- 移植先の pr-review の `helper_write_exceptions` は `source_git`・`runtime` を受け取る。`--source-root` を使わないレビュアーの helper は、PR の Git 操作の対象の checkout（resoloop の PR なら `external/resoloop`）の Git に review の worktree・ref を書く
- 判断の記録を読む処理は、認証済みの login（`gh api user --jq '.login // empty'`）を `read_state(..., trusted_login=login)` に渡し、取得の失敗・空のときは止まる（#169、`.agents/review-records.md` 8.1）
- #155 の `finalize.py` は、create-reso-world の PR の結論 2 で `--spec-commit S` を使い、検証した HEAD の直接の子の Spec だけの commit S を `--match-head-commit S` でマージし、結果に `spec_commit` を入れる。移植元の `cycle-end` はマージ済みのとき PR の head がサイクルの HEAD と同じことを確かめるので、そのままでは成功したマージを `merge_mismatch` にする
- 移植先の review-fix-planning の `references/execution.md` は、PR 修正ループから呼ばれたときに `planning.run_roles_options` を `run_roles.py` にそのまま付けると書いている
- 雛形 `.devcontainer/agent-runner.toml` の `[workflows.review]` は、`after_run` で `review_run.py finalize-parent` → `attach-runner` を実行する。inspect の既定は `pi-gpt`・`devin-swe`・`dsh-ccd`・`claude-opus`。個人設定 `~/.config/agent-runner/config.toml` は雛形と同じ内容
- 移植先の helper は、ルートの project で `uv run --project <root> --locked python` で動く（ボードの D-7）。`tools/devenv` は無い
- DSH の隔離は `/tmp` を tmpfs に差し替えるが、attempt と親の入力は読み取り専用で見せ直す。`/tmp` に置いた runner の出力も扱える（#183 の Spec。「/tmp 一律禁止とはしない」）
- `.agents/monitoring-runtimes.md` の注記は「PR 修正ループの使い方は #156 で足す」としている
- `devin-swe` は、ツールを使った成功でも runner の回収が `response_failed` になることがある（#188、open）。#187（rebuild 後に残る worktree の登録で runner の入口が止まる）も open

## 判断（決定記録）

各項目に、選択した案・検討した別案・選択理由・委任の指示または停止の条件を書く。

### D-1 判断の基準・三択・自己レビューの上限

- 選択した案: loop は判断をしない。司令塔が、親の main checkout の review-fix-planning の完遂の手順で判断し、loop は判断の記録を照合する。移植元の SKILL.md の Hold・H・D1 への言及は持ち込まない
- 検討した別案: 移植元の SKILL.md の計画の節をそのまま写す
- 選択理由: #116 の利用者決定。移植先の review-fix-planning は判断保留を持たない
- 委任の指示・停止の条件: 利用者決定のとおりで、議論し直さない

### D-2 移植元の基準

- 選択した案: 移植元 `415b366` の `pr-review-fix-loop` を基にする
- 検討した別案: ボードの基準 `a47b2065`
- 選択理由: `415b366` までに入った #731（codex のレビュアーの拒否）を、#155 が移植した `run_roles.reject_codex_review_agents` で使う。#155 と基準をそろえる
- 委任の指示・停止の条件: なし

### D-3 扱う PR の範囲

- 選択した案: `start` が、PR を読んだ後、ロックを取る前に `review_target.target_checkout(親, PR のリポジトリ)`（`CODE_ROOT` なし）で Git 操作の対象の checkout を決め、決まらなければ終了コード 2（`arguments`）で止める。扱えるのは create-reso-world と usaturn/resoloop・orange3134/resoloop の PR。移植元の「`usaturn` 配下だけ」（`require_planning_owner`）は持ち込まない
- 検討した別案: (i) `usaturn` 配下だけに固定値で制限する。(ii) `--code-root` を足して任意のリポジトリを扱う。(iii) 検査せず、レビュアーの失敗で止める
- 選択理由: 移植元の制限の理由は「review-fix-planning と同じ範囲」だった。移植先の review-fix-planning は上流の orange3134/resoloop の PR も fork の経路で扱い、`review_target.py` も owner の制限を外している。レビュアーの pr-review は `--source-root` なしで `target_checkout` を使うので、決まらない PR では全員が失敗する。費用のかかるレビュアーの起動の前に止める。(ii) はインターフェースの追加で、#156 の範囲を超える
- 委任の指示・停止の条件: usaturn/resoloop-meshy など `CODE_ROOT` が要る PR は扱えない（既知の制限として PR と #116 に書く）。マージは finalize.py の範囲（create-reso-world・usaturn/resoloop）のまま

### D-4 `--hold-action` を持たない

- 選択した案: `start`・`check-options` から `--hold-action` を外し、`run.json` の `options` と、計画への案内（`planning`）からも `hold_action` を外す
- 検討した別案: 受け付けて記録だけし、計画には影響させない（形を移植元に合わせる）
- 選択理由: 移植先の review-fix-planning には判断保留が無く、値を渡す先が無い。受け付けると、`fix` で致命的でない指摘まで直るように見え、#116 の判断基準と食い違う
- 委任の指示・停止の条件: #158 の `FUTURE_OPTIONS`（ループ用のオプション）に `--hold-action` があるので、#158 と #116 にコメントする。#158 はループに渡すオプションから外す

### D-5 `--controller-runtime` の選択肢

- 選択した案: `claude-code`・`devin`・`pi`・`codex`・`cursor`（`grok-build` を外す）
- 検討した別案: 移植元のまま
- 選択理由: ボードの D-9
- 委任の指示・停止の条件: なし

### D-6 レビュアーへの依頼文

- 選択した案: 移植元の形（日本語の指示と、末尾の JSON の値）を保ち、移植先の pr-review に合わせる。helper は `uv run --project <tool_root> --locked python` で実行させる。参照文書は `references/time-budget.md`・`evidence.md`・`noninteractive.md`。禁止する一括検証は `README.md` の「テスト」のコマンド（`uv run pytest tests/skills .agents/skills .agents/scripts tools`・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`）。DSH には、prepare が返す固定の outbox（`dsh/tmp/exports/review.md`・`findings.json`）を native の write/edit で書き、bash・Python で書かないこと、拒否されたら fail で止まること、complete の `staged` をそのまま返すことを書く
- 検討した別案: #155 の「`--merge` 相当」で使った英語の依頼文を使う
- 選択理由: 依頼文と作業範囲の指示の検査（移植元の `test_loop_reviewer_protocol.py`）は、移植元の構造（末尾の JSON の値と、例外の行）に依存する。#155 の依頼文の DSH の要点は実機で通ったので取り込む
- 委任の指示・停止の条件: 文面の細部は実装者に任せる

### D-7 書き込みの例外

- 選択した案: DSH 以外のレビュアー向けに、`helper_write_exceptions(tool_root, parent, parent_git, review_dir, number, source_git=<PR の Git 操作の対象の checkout の Git の共通ディレクトリ>)` と、移植元の 1 行（ランタイムが起動したディレクトリに自分で作るファイル）を渡す。DSH の行は runner が自分で付けるので渡さない
- 検討した別案: DSH 用の一覧（`runtime="dsh"`）も、行の末尾に対象を書いて同じ一覧に並べる
- 選択理由: runner は DSH の試行に呼び出し側の例外を渡さない（#183）。resoloop の PR では helper の Git の書き込み先が `external/resoloop` になるので、`source_git` を渡さないと許可の一覧が実際と食い違う
- 委任の指示・停止の条件: なし

### D-8 DSH の起動

- 選択した案: `sandbox_write_paths` は常に空にする（移植元の `review_write_paths` を持ち込まない）。DSH の担当の環境から `GH_TOKEN`・`GITHUB_TOKEN` を外す（移植元のまま）。DSH がいるときは、起動の前に親で `prepare_parent` を行って依頼文に `parent_pr_data` を入れ、停止の後に `finalize_parent_batch` で確定する（移植元のまま）
- 検討した別案: 移植元のまま、レビューディレクトリと保存のロックを DSH に許可する
- 選択理由: 移植先の DSH の adapter は空でない許可を拒否する（pr-review の `noninteractive.md`「DSH の caller は sandbox_write_paths を空にする」）
- 委任の指示・停止の条件: なし

### D-9 判断の記録を読むときの認証済みの login

- 選択した案: `cycle-begin`（前の round の番号）と `cycle-end` の記録の読み取りで、`gh api user --jq '.login // empty'` の login を `read_state(..., trusted_login=login)` に渡す。取得の失敗・空なら終了コード 5（`github`）で止まる。`cycle-end` の照合（`exclude_comment_ids` を付けた読み直し）にも同じ login を使う
- 検討した別案: login を渡さない（移植元のまま）
- 選択理由: 上流の PR では利用者自身のコメントが `CONTRIBUTOR` になり、渡さないと利用者の記録を読まない（#169）。review-fix-planning の投稿・finalize.py と読み方をそろえる
- 委任の指示・停止の条件: レビュアーの pr-review（`review_run.read_records`）は login を渡さない（#153 の領域。#155 の D-14 の申し送りのまま）

### D-10 `cycle-end` の `spec_commit` の照合

- 選択した案: finalize の結果が `merged: true` で `spec_commit` を持つときは、PR がマージ済みで、PR の head が `spec_commit` と同じことを確かめる。`spec_commit` が無いときは、今の照合（PR の head がサイクルの HEAD）のまま。`spec_commit` が 40 桁か 64 桁の小文字の hex でなければ、finalize の結果として読まない（終了コード 2）
- 検討した別案: S の親がサイクルの HEAD であることも loop で確かめる
- 選択理由: #155 からの申し送り。S の形（検証した HEAD の直接の子で、Spec 1 ファイルだけの変更）は finalize.py が GitHub の比較で確かめ済み
- 委任の指示・停止の条件: なし

### D-11 runner の出力の置き場所

- 選択した案: `${TMPDIR:-/tmp}/create-reso-world-pr-loop-XXXXXX/cycle-<n>-review/`。回収は名前の接頭辞で確かめる（移植元の旧接頭辞は持ち込まない）
- 検討した別案: 親の `tmp/agents/` に置く（#155 の「`--merge` 相当」）
- 選択理由: `AGENTS.md` の「使い捨ての git worktree とその作業領域」は `/tmp` の一意のディレクトリ。DSH の隔離は `/tmp` に置いた出力も扱える（#183 の Spec）
- 委任の指示・停止の条件: なし

### D-12 helper の起動

- 選択した案: `next` のコマンドは `uv run --project <ROOT> --locked python <ROOT>/.agents/skills/pr-review-fix-loop/scripts/loop.py ...`（ROOT は loop.py を置いた checkout）
- 検討した別案: なし
- 選択理由: ボードの D-7
- 委任の指示・停止の条件: なし

### D-13 SKILL.md と references/records.md

- 選択した案: 移植元の節の構成（守ること・起動・サイクル・終わり方・止まったとき・監視・最終報告・記録・ランタイムごとの違い）を保ち、移植先に合わせる。`TOOL_ROOT` は親の main checkout、Hold の方針を外す、計画は review-fix-planning の完遂、`run_roles.py` に `planning.run_roles_options` を足す、`cycle-end` の `--round-dir` は finalize.py に渡した記録・本文・検証記録を置いた review-fix-planning のセッションディレクトリ、create-reso-world の PR の結論 2 は `--spec-commit`、扱う PR は D-3。frontmatter の `disable-model-invocation: true` を保つ
- 検討した別案: 移植先の review-fix-planning の SKILL.md にループの節を足す
- 選択理由: review-fix-planning は #156 の「変えないもの」。司令塔が読む順序と、移植元の記録の形を変えない
- 委任の指示・停止の条件: 文面の細部は実装者に任せる。判断の規則は review-fix-planning の SKILL.md に従わせ、loop の文書に写さない

### D-14 `.agents/monitoring-runtimes.md`

- 選択した案: 対応表の pi の行に、`loop.py review` も同期で戻るので bash ツールの foreground で実行し（`timeout` は付けない）、標準出力の JSON と終了コードを確かめること、中断・保持の回収は `loop.py status` と `recover --operator-confirmed-stopped` を使うことを足す。注記の「PR 修正ループの使い方は #156 で足す」を、足した内容に合わせて書き換える
- 検討した別案: 移植元の pi の行で置き換える
- 選択理由: #156 の担当（ボードの D-16）。移植先の pi の行は #115 で task_watch を前提に書き直されており、置き換えるとその内容が消える
- 委任の指示・停止の条件: なし

### D-15 テスト

- 選択した案: 移植元の `tests/` を基にし、偽の `gh`・偽の adapter・一時の Git だけを使う
  - PR を `usaturn/create-reso-world` にする（`target_checkout` が親を決められる名前）。偽の `gh` に `api user` を足す
  - 移植先で無くした機能のテスト（`--hold-action`、旧接頭辞、DSH への書き込みの許可）は写さない
  - 移植先で足した挙動のテストを足す: `target_checkout` が決められない PR を `start` がロックの前に止める、login の取得の失敗・空で `cycle-begin`・`cycle-end` が止まる、`CONTRIBUTOR` の利用者自身の記録を読む、`spec_commit` のマージを受け付けて食い違いを `merge_mismatch` にする、DSH 以外の例外が `source_git` を含み、DSH の担当に `sandbox_write_paths` を渡さない
  - DSH の親の準備・確定のテストは、移植先の pr-review の DSH の形（outbox と、`stdout.log` の書き込みの記録）に合わせる
  - SKILL.md の手順のテストは、`disable-model-invocation: true`（push・マージまで進むスキルをモデルが自分で起動しない）だけを残す。参照先の実在は検証の手順で確かめ、テストにしない
- 検討した別案: 移植元のテストを全部そのまま写す
- 選択理由: Issue の受け入れ条件と `AGENTS.md`「テストの採用基準」
- 委任の指示・停止の条件: 細かな分け方は実装者に任せる

### D-16 評価の記録

- 選択した案: 移植元の `evals/`（agent-workspace の実機の記録）は写さない。移植先では、(a) スキル無し・ありの行動の比較（`superpowers:writing-skills`）を `evals/` に置き、(b) 実機の 1 サイクルの記録は D-17 の review-fix の Spec と #156 のコメントに残す
- 検討した別案: 実機の記録を `evals/` に足して PR に載せる
- 選択理由: 移植元の記録は別のリポジトリの事実。実機の記録を後から PR に足すと、レビューした HEAD から変わる（#155 の D-15。現行の HEAD を再実行したレビュアーがいないサイクルは結論 3）。結論 2 で PR に載せられるのは Spec 1 ファイルだけ（finalize.py の `--spec-commit`）
- 委任の指示・停止の条件: なし

### D-17 実機の 1 サイクルと「`--merge` 相当」

- 選択した案: PR の作成後、この PR に loop を使う。`main` に loop.py がまだ無いので、PR の head を detached で置いた使い捨ての worktree（`/tmp` の一意のディレクトリ。以下 frozen tool root）の `loop.py` を使う（`tool_root` は frozen tool root。レビュアーが読む pr-review は `main` と同じ）。`start <PR> --controller-model claude-opus-5-5 --controller-runtime claude-code`（ループ用のオプションは付けない）→ サイクル → `finish`。計画は親の main checkout の review-fix-planning（完遂）で、`run_roles.py`・`finalize.py` も親の main checkout のものを使う。修正は review-fix-planning の手順どおり feature worktree（専用の worktree）で行う。修正不要なら finalize.py が `--spec-commit` でマージし、#156 を閉じる
- 検討した別案: (i) #155 と同じく手作りのスクリプトでレビュアーを起動し、loop を使わない（実機の確認は別の PR で行う）。(ii) 使い捨ての PR で実機の確認をする。(iii) feature worktree の `loop.py` を使う
- 選択理由: 利用者の `--merge` の指示（ボードの D-21 のマージの条件）。Issue の受け入れ（利用者が許可した PR で 1 サイクル）と「`--merge` 相当」を同じ run で満たし、本物のレビュアーの起動を増やさない。(iii) は、review-fix-planning が feature worktree を修正用の worktree として使うので、計画の途中の修正で実行中の helper が変わる。frozen tool root なら、run の間の helper は start の時点の版に固定される
- 委任の指示・停止の条件（builder check の 1 点目への判断）:
  - サイクルの修正が loop.py に入っても、同じ run は frozen tool root の版のまま続ける。修正した版は次のサイクルのレビュアーがレビューする
  - helper 自体の不具合で run を正しく進められない（helper の内部エラー、記録と実際の状態の食い違い）ときは、記録を手で直さず、`finish --abort`（できなければ run を残したまま）で止めて報告する。run を作り直してもサイクルは合計で 3 回までにする
  - マージの後の `cycle-end`・`finish` で見つかった不具合は、この PR では直せないので、持ち越しの候補として #116 と PR にコメントする（Issue は利用者の許可を得てから作る）
  - 移植元の SKILL.md の「feature worktree の `loop.py` を使わない」は、`main` に loop がある後の規則として残し、この PR だけの例外として PR に書く。レビュアーの起動の失敗・結論 3・サイクルの上限は停止として報告する
  - 本物の担当の起動の上限: サイクルは合計 3 回、各サイクルでレビュアー 4 人（runner の成功の後に受け付けなかったレビュアーの 1 回だけの再実行を含む）、結論 1 のたびに implement の担当（`claude-opus`）1 回。self-review・fix-check は雛形の既定（`self`）のまま

### D-18 範囲外と、調整役に申し送る論点

- `--hold-action` を持たないこと（D-4）→ #158・#116
- `CODE_ROOT` が要る PR（usaturn/resoloop-meshy など）を扱えないこと（D-3）
- レビュアーの pr-review の `read_records` が login を渡さないこと（#153 の領域、#155 の D-14）
- `devin-swe` の `response_failed`（#188）。loop は `rejected`（`runner`）として扱い、再実行しない。保存されたレビューは review-fix-planning が読む
- create-reso-world の PR の結論 1 の後に再利用が働かないこと（D-19）

### D-19 create-reso-world の PR では、結論 1 の後のサイクルで再利用が働かない

- 選択した案: 既知の制限として受け入れ、SKILL.md・PR・#116 に書く。create-reso-world の PR の結論 1 では、自己レビューの後に Spec を `completed` にして commit し、push する（review-fix-planning の結論 1 の手順 5〜7）。push した head は自己レビューした commit と違うので、次のサイクルの `cycle-begin` は再利用せず、レビュアーを起動し直す。usaturn/resoloop の PR（Spec は create-reso-world の文書用ブランチ）と、同じ head での run のやり直しでは再利用が働く
- 検討した別案: (i) Spec だけの commit を載せた head でも、親の commit のレビューを再利用する（finalize.py の `--spec-commit` と同じ形の確認）。(ii) review-fix-planning の手順を変え、Spec を自己レビューの前に commit する
- 選択理由: (i) は loop だけを変えても、review-fix-planning の手順 2（現行の head をレビューしたレビュアーがいないと結論 3。#155 の D-15、利用者の決定）で止まるので解決しない。(ii) は review-fix-planning（#156 の「変えないもの」）と利用者の決定の変更で、範囲を超える
- 委任の指示・停止の条件: builder check の 2 点目への判断。費用の上限は D-17 のとおり。再利用を広げるかは #116 に申し送り、調整役が決める

## インターフェース

```bash
uv run --project "$TOOL_ROOT" --locked python "$TOOL_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" <サブコマンド> ...
```

| サブコマンド | 引数 | 役割 |
| --- | --- | --- |
| `start <PR>` | `--controller-model`・`--controller-runtime`（必須）、`--max-cycles N`（1〜10、既定 3）、`--assign ROLE=AGENT[,AGENT]`（複数）、`--template`・`--config`、`--fresh-review` | オプションと設定の検査 → PR → 扱う範囲（D-3）→ ロック → `run.json` → Herdr のペインの名前 |
| `check-options` | `start` と同じ（`--fresh-review` を除く） | 検査だけ。PR・ロック・run・GitHub・Herdr に触れない。`{"status": "ok", "options", "assignments", "next": null}` |
| `cycle-begin --run DIR` | | 現在の HEAD の成果を再利用するか、レビュアーを起動するかを決める |
| `review --run DIR` | | レビュアーを runner で並行に起動して検査する（runner の成功の後に受け付けなかったレビュアーの、1 回だけの再実行を含む） |
| `cycle-end --run DIR` | `--role-run DIR`（複数）、`--finalize-result FILE`、`--round-dir DIR`、`--record-file FILE` | 判断の記録の照合と、サイクルの結果の記録 |
| `finish --run DIR` | `--abort "<permission\|environment\|external>: <具体的な障害>"` | 資源の確認とロックの解放 |
| `status [PR] [--run DIR]` | | 読み取りだけ。持ち主・状態・次の操作 |
| `recover --run DIR` | `--operator-confirmed-stopped "<確かめた事実>"` | 中断・保持した run の回収 |

- 出力は標準出力の JSON 1 つ（引数の書式の誤りだけは、終了コード 2 と標準エラー出力の usage）。終了コード: 0 成功、1 想定外の内部エラー、2 引数・入力（`arguments`・`config`）、3 排他・順序（`lock_held`・`not_owner`・`state`・`interrupted_review`）、4 対象の食い違い（`pr_not_open`・`head_moved`・`record_missing`・`record_inconsistent`・`pushed_head_mismatch`・`merge_mismatch`）、5 外部（`github`・`git`・`parent`・`parent_preparation`・`runner`・`after_run`）、6 全レビュアーの失敗、7 資源の停止を確認できない
- 記録は `<review_dir>/loop/`（`lock.json`、`<run_id>/run.json`・`cycle-<n>.json`・`cycle-<n>/`）。形式は移植元の `pr-review-fix-loop/v1` から `options.hold_action` を除いたもの
- `run.json` の `options` は `max_cycles`・`assign`・`template`・`config`・`fresh_review`。計画への案内 `planning` は `review_dir`・`pr_url`・`run_roles_options`

## 受け入れと確かめ方

| Issue の受け入れ条件 | 確かめ方 |
| --- | --- |
| 移植したテストが通る | `uv run pytest .agents/skills/pr-review-fix-loop`（偽の gh・偽の adapter・一時の Git） |
| 実機: 利用者が許可した PR で 1 サイクル（レビュアーの並行起動 → 計画 → 判断の記録） | D-17 の run。`<review_dir>/loop/<run_id>/` の記録と #156 のコメント |
| `no_fix_needed` からのマージは利用者の明示の指示があるときだけ | 利用者の `--merge` の指示（D-17） |
| テストは「テストの採用基準」に従う | 差分の確認と、ブランチ全体のレビュー |
| 全体の検証 | `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` |
| スキルの行動 | スキル無し・ありの行動の比較（D-16 (a)） |

## 範囲

変えるもの: `.agents/skills/pr-review-fix-loop/`（新規）、`.claude/skills/pr-review-fix-loop`（symlink）、`.agents/monitoring-runtimes.md` の pi の行の loop の部分とその注記、この Spec と Plan。

変えないもの: `.agents/skills/review-fix-planning/`・`pr-review/`・`review-verify/`・`issue-to-pr/`、`.agents/scripts/`、`tools/`、`AGENTS.md`、`.devcontainer/`、ほかの子の担当。

## 実装者に任せること

- SKILL.md・records.md の文面の細部（判断の規則は review-fix-planning に従わせる）
- テストの分け方と、移植元のテストのうち移植先で意味のあるものの選び方（`AGENTS.md`「テストの採用基準」の範囲で）
- 行動の比較の場面の細部

## 実行の記録（PR の作成の前、2026-10-19 UTC）

### 受け入れ条件と証拠

| Issue の受け入れ条件 | 証拠（対象版） |
| --- | --- |
| 移植したテストが通る | `uv run pytest .agents/skills/pr-review-fix-loop` 162 passed（`f69373e`）。`env AGENT_RUNNER_DEPTH=1` でも 162 passed。偽の gh・偽の adapter・一時の Git だけを使う。実際の pr-review の helper を動かすテスト（`test_loop_reviewer_protocol.py`）を含む |
| 実機: 利用者が許可した PR で 1 サイクル | PR の作成の後に D-17 の run で行う（この時点では未実施）。結果は review-fix の Spec と #156 のコメントに書く |
| `no_fix_needed` からのマージは利用者の明示の指示があるときだけ | 利用者の `--merge` の指示（D-17）。マージは finalize.py だけが行う |
| テストは「テストの採用基準」に従う | 差分の確認とブランチ全体のレビュー。文言の照合・運用で変わる値の写しは無い。SKILL.md の固定値のテストは `disable-model-invocation: true` の 1 件だけで、守る権限と理由をコメントに書いた |
| スキルの行動 | `evals/2026-10-20-issue156-behavior.md`。スキル無し（RED）の欠け 4 点を、スキルあり（GREEN）で満たした |

### 適応ごとの対照（変更前後）

適応を 1 つずつ外した `loop.py` で、対応するテストが失敗することを確かめ、元に戻して `cmp` で一致を確かめた。

| 外した適応 | 失敗したテスト |
| --- | --- |
| D-3（`require_target_checkout` の呼び出し） | `test_start_refuses_a_pr_whose_checkout_cannot_be_resolved`（1 failed） |
| D-9（login を空にする） | `test_records_need_the_authenticated_login`・`test_cycle_end_reads_the_authenticated_users_record`（4 failed） |
| D-10（サイクルの HEAD だけで照合する） | `test_cycle_end_accepts_a_spec_commit_merge`（1 failed） |
| D-10（`spec_commit` の形の検査） | `test_cycle_end_rejects_a_malformed_spec_commit`（4 failed） |
| D-7・D-8（移植元の書き込みの許可と例外のまま） | `test_write_exceptions_name_the_target_checkout_git`・`test_review_passes_no_sandbox_grants_and_strips_dsh_tokens`（2 failed、ほか 77 passed） |
| 例外の計算を出力ディレクトリの後に戻す | `test_review_stops_before_creating_output_when_the_checkout_cannot_be_resolved`（1 failed） |

### 全体の検証

- `f69373e`: `uv run pytest tests/skills .agents/skills .agents/scripts tools` 3377 passed（終了コード 0）、`bash .devcontainer/run-tests.bash` 33 本 PASS（0）、`bash scripts/check-layout.sh` PASS（0）、`env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/pr-review-fix-loop` 162 passed（0）。ログは `/workspaces/reso-world/tmp/agents/issue-156.vtjmipf1/verify-final/`
- `aa28c20`（SKILL.md の 1 行と Plan の名前だけの変更）: `uv run pytest tests/skills .agents/skills/pr-review-fix-loop/tests/test_pr_review_fix_loop_skill_contract.py` 32 passed、`bash scripts/check-layout.sh` PASS。続けて `bash .devcontainer/run-tests.bash` 33 本 PASS（0）、`uv run pytest .agents/skills/pr-review-fix-loop tests/skills` 193 passed（0）、`bash scripts/check-layout.sh` PASS（0）。ログは `/workspaces/reso-world/tmp/agents/issue-156.vtjmipf1/verify-final2/`
- 基準（`8f5074a`）: 3214 passed、33 本 PASS、PASS（`check-layout.sh` と `run-tests.bash` は使い捨ての worktree で実行）

### 独立した根拠

- 偽の gh と実装が同じ仮定に立たないよう、実際の pr-review の helper（`prepare` → 下書き → `complete`）を動かすテストで、移植先の `review_target`・`superpowers_context`・`pr_review_workspace` の実際の経路を通した（fetch の取得先だけを差し替えた）
- DSH の staged の確定は、移植先の実物の `prepare`・`complete`・`finalize_parent_batch` と、#183 の `stdout.log` の native write の記録で確かめた
- `gh api user --jq '.login // empty'` の出力の形（login と改行）は、#155 で実際の gh で確かめた形と同じ

### レビュー

- builder check（Spec）: 2 点。D-17（frozen tool root、サイクルの合計の上限）と D-19（再利用の既知の制限）に判断を書いた
- ブランチ全体のレビュー（新しいコンテキストのレビュアー、opus）: Critical 0・Important 0・Minor 6、判定は Ready to merge: Yes。Minor 1（`--role-run` のディレクトリを `cycle-end` の前に消しうる）は、文書どおりに進めると結論 1 で必ず誤るので Important に格上げして直した（`aa28c20`）。Minor 5（frozen tool root の名前）は Plan を直した。Minor 2（結論 2 で投稿の後に push が拒否されたときの道筋）・3（`CONTRIBUTOR` での前の run の記録のテスト）・4（移植元の旧形式の記録のテスト）・6（checkout の解決の失敗の分類）は持ち越す（PR の既知の制限と #116 のコメント）
- 実行の記録の判断（Ruling）と持ち越しの一覧は ledger `/workspaces/reso-world/tmp/agents/issue-156.vtjmipf1/sdd/progress.md`

### 所要時間（2026-10-19 UTC。着手 15:08Z から PR の作成の準備まで約 1 時間 45 分）

| 段階 | 時間 |
| --- | --- |
| 着手の条件・予約・worktree | 15:08–15:13 |
| 移植元・移植先の調査、Spec | 15:13–15:27 |
| Plan、Task 1（loop.py の移植と状態・検査のテスト） | 15:27–15:35 |
| Task 2（レビュアーの起動・DSH の親の処理）、builder check への判断 | 15:35–15:46 |
| Task 2 の追加、スキル無しの評価（RED）、Task 3（SKILL.md・records.md・監視の文書） | 15:46–16:01 |
| Task 4（スキルありの評価と記録） | 16:01–16:10 |
| Task 5（全体の検証・ブランチ全体のレビュー・修正） | 16:10–16:52 |
