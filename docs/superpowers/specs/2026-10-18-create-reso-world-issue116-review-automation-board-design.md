# Issue #116: 複数モデルの PR レビューの自動化を取り入れる（親の範囲と子 Issue への分割）

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/116（親・メモ。この文書でボード `review-automation-board` にする）
- 検証した基準 HEAD: 移植先 `84f417f8712dedc12304fd3896687c061ce6da17`（`origin/main`）、移植元 usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`（`main`、2026-10-17T19:08Z）。Issue の候補の表は `3bc4769833ccc085ec2696ab8941bb83aa20c1cf` の時点のもので、その後の 28 コミットに、この Issue の範囲を変えるものは無い（DSH の対話用 TUI の撤去 #722・#723 は、もともと持ち込まない部分）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue116-review-automation-board.md`
- 実行許可: 2026-10-18（JST）、利用者が `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/116` で「着手してください」と指示し、着手の範囲の確認に「ボード作成まで」を選んだ。推奨案で範囲と分割を決めること、隔離 worktree での Spec・Plan の commit、子 Issue の作成、GitHub の親子関係と依存の登録、#116 の本文の更新、push と PR の作成（`Refs #116`）まで許可されている。子の実装、マージは含まない。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

usaturn/agent-workspace の、複数モデルの PR レビューを自動で回す仕組み（agent_runner、DSH の headless のレビュアー、pr-review の新しい版、review-verify、review-fix-planning の役割の実行と最終化、pr-review-fix-loop、issue-to-pr の `--implement`・`--merge`）を create-reso-world に取り入れる。量が多い（移植元のコードとテストで 3 万行ほど）ので、1 回の実装で扱える大きさの子 Issue に分け、依存と担当ファイルを決めて、別々のセッションが並行して進められるボードにする。

#116 の冒頭の「着手するエージェントへの注意（利用者決定: 2026-10-18）」は、利用者が決めた方針であり、この文書と全ての子 Issue に適用する。この文書の判断は、その方針を満たす範囲で技術的な接続と分割を決めるものである。

## 確認した事実（2026-10-18）

- 先行の #114・#115 は close 済み。#116 に open PR・予約 ref・worktree・branch は無く、Sub Issue も無い
- 移植先は Python 3.14.4（`uv run --no-project python --version`）。ルートの `pyproject.toml` は `requires-python = ">=3.12"`、依存は pydantic、dev は pytest・pyyaml。`tools/` は無い。テストの入口は `README.md` の「テスト」（`uv run pytest tests/skills .agents/skills .agents/scripts` など）
- 移植元の agent_runner は `tools/agent_runner/`（コード 4,276 行、テスト 7,910 行）。Python 3.14 の構文（括弧の無い `except A, B:`）を使う。adapter は `adapters/__init__.py` の固定の名前の表から読み込む方式で、具体的な adapter は各ファイルに分かれている（`claude_code`・`codex`・`cursor`・`devin`・`pi`・`dsh`・`grok_build`）。`Runtime` の型も同じ 7 つを持つ
- 移植元のスキルの helper は `Path(__file__).resolve().parents[4]` から `tools.agent_runner` を読み、`uv run --project tools/devenv --locked` で動く。`review_run.py`（pr-review）は `tools.agent_runner.dsh_identity` を、`dispatch.py`（review-verify）・`run_roles.py`・`loop.py`・`implement_task.py` は runner の本体を使う。`finalize.py` と移植元の `resolve_issue.py` は `tools.workspace`（`projects.toml`）を使う
- 移植元のテストは `tools.test_support.plugin` の `outside_runner` を `pytest_plugins` で読み込む。`create_workspace`・`write_registry` は agent-workspace の構成を作る
- 移植元の雛形 `.devcontainer/agent-runner.toml` は、agent の定義、役割（inspect・implement・self-review・fix-check）、workflow の割り当て（review・fix・issue）と review の後処理（`review_run.py finalize-parent`・`attach-runner`）を持つ。レビュアーの既定は `pi-gpt`・`devin-swe`・`dsh-ccd`・`claude-opus`・`pixg`
- 移植先には `claude`・`devin`・`codex`・`agent`（Cursor）・`pi`・`pigs`・`pixg`・`piccd`・`pigod` がある。`pigemf` は無い（#125 の PR #141 が open）。`dsh` は無い（#18 で撤去）。`bwrap` は入っている（bubblewrap 0.11.1）
- DSH の headless の adapter はプラグインを導入しない。移植元は `@deepseek-ai/dsh@0.2.0-rc.2` を npm で入れる。Command Code の provider プラグインは `web` の profile にだけ入れている
- 移植元のレビューの保存先は、親の main checkout の `reviews/<owner>/<repo>/#<PR>-<branch>/`。移植先は `AGENTS.md` の表で、create-reso-world は `reviews/#<PR>-<branch>/`、resoloop は `external/resoloop/reviews/`、その他は `CODE_ROOT` の `reviews/`。#146（open）は、手元の branch `fix/issue-146-pr-review-repo-identity`（未 push、2026-10-18）で、保存先を `reviews/<owner>/<repo>/#<PR>-<branch>/` に変えている
- `scripts/superpowers_context.py` は create-reso-world と resoloop（origin/upstream）の経路を固定で持ち、それ以外は明示した `CODE_ROOT` と remote 1 件の一致で扱う。issue-to-pr の `resolve_issue.py` は 3 つのリポジトリを固定値で持ち、`--merge` などのオプションを「#116 で入れる予定」として終了コード 2 で止める（`FUTURE_OPTIONS`）
- create-reso-world は private で、ruleset・branch protection の API は「Upgrade to GitHub Pro or make this repository public to enable this feature.」（403）を返す。Actions は無効。利用者の権限は admin
- pr-review の保存先・識別に関わる open の Issue: #146（PR の所属リポジトリ）、#134（HEAD が動いたときの保存拒否の後）、#59（`gh pr diff` が 300 ファイル超で 406）

## 判断

### 範囲

- **D-1 着手の範囲**: この作業は、子 Issue への分割とボードの公開までとする（利用者の選択）。子の Spec・Plan・実装は、各子の作業で行う。#116 は全ての子が終わるまで open のままにする
- **D-2 子の大きさ**: 1 つの子は、1 回のセッションで移植・テスト・PR まで終えられる量にする。runner の本体と adapter、pr-review と review-verify のように、移植元で別のスキル・別のファイルになっているものは別の子にする。移植元のファイルを丸ごと写すのではなく、注意書きの方針に合わせて変える前提で量を見積もる
- **D-3 持ち込まないもの**: #116 の「持ち込まないもの」に加えて、`tools/agent_runner/adapters/grok_build.py` とその runtime の文書・テスト（#17 で Grok Build を除外したため）、`scripts/ci/`（移植先には無い。検証は `README.md` の「テスト」で行う）、`version-export`・`python-extension-docs`・`rst-writer` の移植元の変更（この Issue と関係が無い）
- **D-4 完了の条件**: #116 は、次がそろったら completed で close する
  1. `main` で `README.md` の「テスト」の入口（runner のテストを含める）が通る
  2. 雛形の既定のレビュアーを runner で並行に起動し、各レビュアーの結果（DSH の headless を含む）がレビューディレクトリに保存される
  3. review-verify が確認済みの一覧（`verified/<HEAD>.json`）を作る
  4. review-fix-planning が、移植先の判断基準（致命的な指摘だけを直す、三択の結論、修正後の自己レビューは最大 1 回）を保ったまま、`run_roles.py` で役割を実行し、`finalize.py` で修正不要の最終化を行う
  5. pr-review-fix-loop がレビュー → 修正 → push を、マージ・停止・上限まで回せる
  6. issue-to-pr が `--implement`・`--merge` を受け付ける（`FUTURE_OPTIONS` による拒否が無い）
  7. #17・#18 の DSH の記録（`.devcontainer/README.md`、`docs/maatlog-poc-porting.md`）が今回の判断に合っている

### リポジトリの振り分けと CI（注意書きの方針の適用）

- **D-5 置き換える箇所**: `tools/workspace`・`projects.toml` は入れない（利用者決定）。移植元が `Registry`・`find_repo`・`find_name`・`which`・`ci_required` を使う箇所は、次に置き換える
  - PR とレビューディレクトリの対象の決定（`review_target.py`）: `scripts/superpowers_context.py` と `AGENTS.md` の「リポジトリ境界」。resoloop の origin/upstream の区別、明示した `CODE_ROOT` と remote の照合、checkout の探索・clone の禁止を保つ。担当は `review-helpers`
  - CI の要否（`finalize.py`）: `AGENTS.md` の「GitHub Actions」。create-reso-world・resoloop-meshy は確かめない、usaturn/resoloop は PR の checks が green であることを確かめる。値は issue-to-pr の `resolve_issue.py` と同じく固定値で持つ（#114 の D-4）。担当は `review-fix-roles`
  - Issue の対象（`resolve_issue.py`）: #114 の移植先の版をそのまま基にする。担当は `issue-to-pr-implement`・`issue-to-pr-merge`
- **D-6 repository-ownership**: スキルは持ち込まない。push の前の検査は `scripts/scan-before-push.sh`、作業ルートの確認は既存の resolver を使う

### 共有のインターフェース

- **D-7 runner の置き場所と Python の環境**: 移植元と同じ `tools/agent_runner/` に置く。helper が `parents[4]` から読む相対の構成と、`tools.agent_runner` の import を変えずに済む。Python の環境はルートの `pyproject.toml` にまとめ、`tools/devenv` は作らない（移植先にはルートの 1 つしかない）。`requires-python` を `>=3.14` に上げ、pytest の `testpaths` と `pythonpath` に `tools` を加える。helper の起動は `uv run --project "$PARENT_ROOT" --locked python ...` にする。ruff・pyright は加えない（移植先の既存の検証に合わせる。加える場合は `runner-core` が理由を記録する）。担当は `runner-core`
- **D-8 テスト補助**: `tools/test_support/` に、移植するテストが使う汎用の部分だけを置く。`plugin.py` は `outside_runner` だけ、`texts.py` はそのまま、`dsh.py`（`write_session`）は `dsh-headless` が足す。`create_workspace`・`owned_worktree`・`write_registry`・`repos.py`・`registry.py`・`uv.py` は持ち込まない。それらを使うテストは、移植先の構成（実際の git の checkout、`superpowers_context.py` の経路）を作る fixture に、各子が自分のテストの中で置き換える。`create_parent_repo` を使う移植元の 3 モジュールのうち、`test_review_target.py` だけを `review-helpers` が作り直す。`test_agent_tmp.py`（移植先に自分の版がある）と `test_workspace.py`（`tools/workspace` を入れない）は持ち込まない
- **D-9 Grok Build**: `Runtime` の型と adapter の名前の表から `grok-build` を外す（`runner-core`）。pr-review-fix-loop の `--controller-runtime` の選択肢からも外す（`fix-loop`）
- **D-10 レビューディレクトリ**: 全てのリポジトリの PR のレビューを、親の main checkout（`PARENT_ROOT`）の `reviews/<owner>/<repo>/#<PR>-<branch>/` に置く（移植元と同じ形）。理由: #146 が同じ `<owner>/<repo>` の形を選んでおり、fork と上流の PR を分けられる。review-verify・pr-review-fix-loop は、レビューディレクトリから親の root を求める（`parents[3]`）。外部の checkout の中にレビューの成果を書かずに済む。旧配置（`reviews/#<PR>-*`、`external/resoloop/reviews/`）は、利用者が明示したパスでだけ読む（移植元の旧配置の扱いと同じ）。規則は `review_target.py` に置き（`review-helpers`）、pr-review の保存先と `AGENTS.md` の「コミットしないファイルの置き場所」の「PR レビュー結果」の行は `pr-review-v2` が合わせる。保存先を読む・説明する既存の箇所（review-fix-planning の「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方、`docs/resoloop-meshy-workflow.md` の保存先の文、repo-cleanup-after-merge）も、`pr-review-v2` が同じ PR で合わせる。書く側と読む側の配置を、`main` のどの時点でも一致させるため（#146 が not_planned で終わり、`pr-review-v2` が配置を変える場合も含む。PR #159 のレビュー修正）
  - 検討した別案: 移植先の今の配置（checkout ごとの `reviews/`）を保ち、移植するスクリプトの `parents[3]` などを全て書き換える。移植の差分が増え、fork と上流の混同（#146）が残るので採らない
- **D-11 #146・#134・#59 との関係**: `pr-review-v2` は pr-review の helper を置き換えるので、#146 と同じファイルを変える。`pr-review-v2` は #146 が close するまで着手しない（#146 は #116 の子ではないので GitHub の依存には登録せず、子の本文の「着手の条件」に書く）。#134 と #59 は、`pr-review-v2` が移植した版で再現するかを確かめ、解消していれば PR で `Closes`、残っていれば Issue に結果を書く
- **D-12 雛形 `.devcontainer/agent-runner.toml`**: 節ごとに担当を分ける。`schema_version` と `[roles.*]` は `runner-core`、DSH 以外の `[agents.*]` は `runner-adapters`、`[agents.dsh-*]` は `dsh-headless`、`[workflows.review]`（後処理）と `[workflows.review.assignments.inspect]` は `pr-review-v2`、`[workflows.fix.assignments.*]` は `review-fix-roles`、`[workflows.issue.assignments.implement]` は `issue-to-pr-implement`
- **D-13 レビュアーの構成**: 既定のレビュアーは移植元と同じ 5 人（`pi-gpt`・`devin-swe`・`dsh-ccd`・`claude-opus`・`pixg`）。どれも移植先にランチャーがある（`dsh-ccd` は `dsh-headless` の後）。`pi-gemf` は、`runner-adapters` の実装の時点で `main` に `pigemf` があるときだけ agent を定義し、既定には入れない。fix の実装は `claude-opus`、self-review・fix-check は `self`、issue の実装は `self`（移植元の雛形と同じ）
- **D-14 DSH に要る導入物**: dsh の CLI だけを、移植元と同じ版（`0.2.0-rc.2`）に固定して `.devcontainer/install_beforehand.bash` で入れる見込みとする。`~/.dsh` の mount、pi-tui、`cordis.patch.yml`、pnpm、ポート 3080、provider プラグインが要らないことを、`dsh-headless` が実際の headless の起動で確かめる。要るものが見つかったら、その子の Spec に理由を書いて足す。rebuild の後の確認は利用者が行い、結果を子 Issue に記録する
- **D-15 issue-to-pr のオプション**: `--implement` と `--merge` は、同じ `SKILL.md`・`resolve_issue.py` を変えるので、2 つの子に分けて順に行う。`--implement` は runner の adapter だけで動くので先に入れ、`--merge` は修正ループの後に入れる。`FUTURE_OPTIONS` から、`issue-to-pr-implement` は `--implement` を外し、`issue-to-pr-merge` は残り全て（`--merge` とループ用のオプション）を外して `FUTURE_OPTIONS` を無くす
- **D-16 監視の文書**: `.agents/monitoring-runtimes.md` の「agent-runner の同期実行と停止確認」の節と、`monitoring-long-tasks/SKILL.md` の agent_runner の使い方（result.json の `stop_confirmed` の確認など）は `runner-core`、pi の行の `loop.py`（PR 修正ループ）の部分は `fix-loop` が書く。#115 の既知の制限（`issue_budget.py` は同じ signature の分類を最後の記録で決める）に従い、runner の worker の失敗を ledger に書くときは、安全の失敗の後に同じ signature を別の分類で記録しない
- **D-17 `AGENTS.md`**: 「エージェント運用」への agent-runner の規則は `runner-core`、「コミットしないファイルの置き場所」の「PR レビュー結果」の行は `pr-review-v2` だけが変える。ほかの子は変えない。要るときは親にコメントする

### 子と依存

- **D-18 子の一覧**（キー: 目的）
  1. `runner-core`: agent_runner の本体・設定の検査・CLI・雛形の役割・テスト補助・Python の環境
  2. `runner-adapters`: DSH 以外の adapter（Claude Code・Codex・Cursor・Devin・pi）と、その runtime の文書・雛形の agent
  3. `dsh-headless`: DSH の headless の adapter・識別・隔離、dsh の CLI の導入、#17・#18 の記録の書き換え
  4. `review-helpers`: レビューの記録・候補・対象の共通 helper（`review_records.py`・`review_findings.py`・`review_target.py`）と、その仕様の文書
  5. `pr-review-v2`: pr-review の新しい版（非対話の入口、全体差分、DSH の親保存、保存先）
  6. `review-verify`: 全レビュアーの指摘を隔離した worktree で確かめ、確認済みの一覧を作るスキル
  7. `review-fix-roles`: review-fix-planning に、役割の実行（`run_roles.py`）・修正不要の最終化（`finalize.py`）・記録の検査をつなぐ。判断基準は変えない
  8. `fix-loop`: pr-review-fix-loop（レビュー → 修正 → push の繰り返し）
  9. `issue-to-pr-implement`: issue-to-pr の `--implement`（Plan の Task を runner の担当に依頼する）
  10. `issue-to-pr-merge`: issue-to-pr の `--merge`（PR の作成後にループを回す）
- **D-19 直接の先行**（ここから表・図・GitHub の依存を作る。13 本）
  - `runner-core`: なし
  - `review-helpers`: なし
  - `runner-adapters`: `runner-core`
  - `dsh-headless`: `runner-core`
  - `review-verify`: `runner-core`、`review-helpers`
  - `pr-review-v2`: `runner-adapters`、`dsh-headless`、`review-helpers`（`runner-core` の models は `runner-adapters`・`dsh-headless` を通して入る）
  - `issue-to-pr-implement`: `runner-adapters`
  - `review-fix-roles`: `pr-review-v2`、`review-verify`
  - `fix-loop`: `review-fix-roles`（`runner-adapters` は `review-fix-roles` を通して入る）
  - 雛形が参照する agent は、参照を足す子の先行が定義する。`pr-review-v2` の既定のレビュアーは `runner-adapters`・`dsh-headless`、`review-fix-roles` の fix の実装の `claude-opus` は `runner-adapters` が定義する。移植元の `load_config` は全ての workflow の担当の定義を確かめ、無ければ `invalid_reference` で全てのコマンドを止めるので、どの順で子をマージしても雛形が検査を通るようにする（PR #159 のレビュー修正で `pr-review-v2` に `runner-adapters` を足し、冗長になった `fix-loop` の `runner-adapters` を外した）
  - `issue-to-pr-merge`: `fix-loop`、`issue-to-pr-implement`
- **D-20 子の Issue の書き方**: 題は `[#116-N] ...`（#17 の子 #18 の形）。本文の冒頭に親とボードのキー、#116 の「着手するエージェントへの注意」への参照、その子に関係する制約を書く（注意書きの最後の項目）。planning・implementation の状態は `not-started` で作る
- **D-21 実機の確認の範囲**: 本物の担当（モデル）を起動する確認は、その子の実装の作業の中で、その子の PR か使い捨ての対象に限って行う。マージを伴う確認（`finalize.py`、修正ループの `no_fix_needed`、`--merge`）は、利用者の明示の指示があるときだけ行う。rebuild は利用者が行う

### ボードの運用

- **D-22 予約**: create-reso-world の `refs/heads/agent-claims/issue-N`（#95 と同じ手順）。ruleset と branch protection はプランで使えないことが 403 で明示され、Actions は無効なので、予約の ref で動くものは無い
- **D-23 Spec・Plan・handoff**: 子の Spec・Plan は create-reso-world の `docs/superpowers/` に置く。全ての子の実装の対象は create-reso-world なので、Spec・Plan は実装と同じ PR に入れる。handoff は `tmp/docs_draft/claude_handoffs/`
- **D-24 親の更新**: 実行マップと公開台帳は調整役だけが更新する。子のセッションは、自分の子 Issue にだけ状態を書く。#116 の本文のうち、利用者が書いた「着手するエージェントへの注意」と、メモの段階の記録（候補の範囲、`ec13c3e` の後の変更、持ち込まないもの、着手するときに決めること、先行）は残し、決めたことにこの文書の判断を添える

## 範囲外

- 子の Spec・Plan・実装・テスト・マージ（各子の作業）
- #146・#134・#59・#125・#120 の実装（関係は D-11・D-13 に書いた）
- `tools/workspace`・`projects.toml`・`repository-ownership` の導入（利用者決定）

## 実装者に任せること

- 各子の中のファイルの分け方、テストの移植の範囲（`AGENTS.md` の「テストの採用基準」に従う）、移植元の文書（`interfaces.rst`・`runtimes/*.rst`）を `.rst` のまま置くか Markdown にするか
- `runner-core` での ruff・pyright の扱い（D-7 の既定は加えない）
- 子の中で見つかった、注意書きの方針の範囲に収まる技術的な選択
