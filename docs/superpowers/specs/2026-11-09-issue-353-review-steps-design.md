# Issue #353: opt-in の Spec・設計レビューと実装担当の既定変更

## 管理・実行許可

- 状態: `completed`（2026-11-10 のレビュー修正と検証を反映。内容の承認 SHA はない）
- 対象: https://github.com/usaturn/create-reso-world/issues/353 / 親 #349
- repository: `usaturn/create-reso-world`、PR base: `main`
- base: `refs/heads/main` / `b61b36a3e11f969f4e4ab41c401dadfa00a86e90`、origin: `https://github.com/usaturn/create-reso-world.git`
- 実行許可: 利用者の明示 issue-to-pr 入力 `#353 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max` と、続く「#364が完了したことを確認して作業を実行してください。」。通常の設計判断・検証・commit・push・新規 PR・指定ループ内 finalize によるマージを含む。安全条件の免除ではない。
- CODE_ROOT = DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-353-review-steps`
- SESSION: `/workspaces/reso-world/tmp/agents/issue-353._kkg4w5l`
- 先行: #350・#364 は closed / completed。PR #362 (`144f3ed535fe969aa79ed1fe132128d176017cb8`) と #371 (`b61b36a3e11f969f4e4ab41c401dadfa00a86e90`) の base 包含を確認済み。

## 目的と範囲

利用者が明示した run にだけ、Plan 前の Spec レビューと、その前の設計レビューを追加する。別担当の失敗を自己レビューの成功へ読み替えず、レビュー対象の版と指摘の採否を保存する。既定の Plan 実装担当を sonnet xhigh に変更し、レビュー修正（`fix.implement`）は main の #377 の `self` を維持する。

変更対象は Issue 本文の「変更してよい」に限る。主な対象は issue-to-pr の scripts・tests・SKILL.md、`.devcontainer/agent-runner.toml`、`.devcontainer/README.md`、`README.md`、`tools/agent_runner/interfaces.rst` の roles/割り当て節と関連 config テスト。文書の Spec/Plan はこの PR に含める。

対象外: adapter、checkout_policy、runner の監査 API、dsh_removed、個人設定を導入する実装、loop.py、finalize.py、dispatch.py、run_roles.py、review-eval、ワールド、#364 の再実装。AW の projects.toml・docs_draft Spec 方式・Hold・スキル全文は移植しない。

## Approaches / 決定記録

| ID | 選択した案 | 検討した別案 | 理由 / 委任または停止条件 |
|---|---|---|---|
| D1 | AW `0eea76aa` の review_spec/review_design のスキーマ・状態遷移を参考に、CRW の保存・監査を適用 | 全面独自実装 / AW スキル全文の置換 | 既存の挙動を保持し、移植差分を限定する。Issue の通常設計委任。 |
| D2 | review helpers の Kind で共通処理を再利用 | 2 helpers の実装複製 | 版確認・受付・cleanup の守りを一元化する。 |
| D3 | ledger は SESSION の下、Spec は DOC_ROOT に commit | Spec 隣の ledger | worktree 回収で記録を失わない。`--ledger-dir` は省略時に環境変数 SESSION を使い、未設定・不適切なら終了コード2で停止。推測した場所へ保存しない。 |
| D4 | `claude-code_sonnet_default` を `claude-code_sonnet_xhigh` に置換し effort=xhigh | model_key で両方を残す | #353 の coordinator 決定 https://github.com/usaturn/create-reso-world/issues/353#issuecomment-6743479597 。両方を残すと model=sonnet が重複する。 |
| D5 | opt-in の値は明示引数だけで選ぶ | 設定・fallback だけで自動起動 | 不要な有料レビューを起動しない。無指定では新 helpers の check も実行しない。 |
| D6 | 今回の run の spec-review/design-review はともに無効 | 本 Issue の実装で追加するオプションを今回にも補う | 利用者入力に両オプションはない。builder check を1回行う。 |
| D7 | Plan の各 Task は指定した runner 担当へ直列依頼 | controller の self 実装 | implement_task.py check: agents=[pi_opencode-go_deepseek4-flash_max], fallback=[], self=false。利用者指定を保持する。 |
| D8 | PR 後は3サイクル上限の既存ループ | 独自レビュー・直接マージ | check-options の max_cycles=3 は既定の適用。inspect は claude-code_opus_default / devin_swe2_max / pi_opencode-go_deepseek4-flash_max、fix.implement は pi_opencode-go_deepseek4-flash_max（利用者指定）、self-review/fix-check は self（既定）、fallback は全て空。template は親の .devcontainer/agent-runner.toml、ループ用 config 指定なし。 |

## 設計

### 1. 入力と設定

`resolve_issue.py` は `--spec-review AGENT` / `--design-review AGENT` と `=AGENT` を各1回受け付ける。値は `[A-Za-z0-9][A-Za-z0-9_.-]*`。重複・欠値・特殊文字は既存の入力エラーとして拒否する。JSON に `spec_review` / `design_review` を追加し、無指定は null。--merge の位置に依存せず loop_args に混ぜない。既存の --base と捕捉 SHA、登録ツール/ワールドの拒否は変えない。

`implement_task.project(config, role_name=ROLE, *, writes=True)` は選択した role の一人の担当・json・期待 writes を検査する。投影によって別 role への除外条件を黙って捨てない。`remove_attempts(repository, batch) -> (removed, retained)` を既存 cleanup から切り出し、停止未確認・機密を含む領域・dirty worktree は残す。summarize に unprotected_changes を加え、outside_changes の拒否は維持する。require_auditable_workflow と runner の preflight は残す。

roles.spec-review / roles.design-review は writes=false、result_shape=json、deadline_seconds=1800。雛形に両 review roles の assignment は作らない。明示引数を一次担当として workflow issue に投影し、個人設定で明示された fallback は保持する。`self` は runner を起動せず、依頼文を controller に返す。

### 2. 共通レビューライフサイクル

両 helpers は check / review / submit / decide / cleanup を持つ。AW と同じ ReviewRequest: spec_path（絶対パス）、repository（レビューするコード checkout）、revision（その完全 HEAD SHA）、issue（repo/number/url/title/body）、context（日本語・複数行可）。Spec は別 DOC_ROOT にあることを許す。request.repository の HEAD を確認し、Spec の UTF-8 生バイトを SHA-256 で結び付ける。

保存先は `LEDGER_ROOT/<spec-stem>.spec-review/review-<k>/`、設計レビューは `.design-review`。LEDGER_ROOT は明示 --ledger-dir または SESSION。runner-dir も新しい外部ディレクトリにする。repository checkout と Spec の DOC_ROOT のどちらの worktree にも、ledger・runner の記録を置かない。resolve した実パスを用いて symlink 経由の脱出も拒否し、両保存先が互いを消し得る包含関係も拒否する。`_admit`・次回受付・cleanup が同じ保存先の履歴を見る。記録を Spec の隣に探索し直さない。

review は設定・保存先・対象・受付順を検査してから新規 request.json / spec.md / prompt.txt を保存する。self は state=self と prompt_path を返し、controller が結果 JSON を submit する。外部実行は run_workflow(concurrency=1, payload_check=...) を使い、停止確認、結果の形・review_id・spec_sha256、外部書込 outside_changes、Spec/HEAD の変化を検査する。unprotected_changes は報告するがそれだけで失敗にしない。未完了・異常終了は failed であり指摘0件ではない。actual_agent / identity / fallback の事実を記録し、self へ暗黙移行しない。

submit は self 専用。取り違えた ID/版・重複した結果は受理せず、検査が通らない内容を completed にしない。現在の Spec が変わっていれば失敗として記録する。decide の入力検査に失敗した場合は採否も反映後 snapshot も書かない。既存の結果・採否は上書きしない。

cleanup は共有 remove_attempts を使い、停止を確認できた試行だけを force なしで回収する。消せなかった完全パスを返す。runner 出力は安全に片付いた場合だけ消し、review ledger は残す。runner が記録を返さなかった領域は不明として残す。

### 3. Spec レビュー

ReviewResult は review_id/spec_sha256/status(completed|incomplete)/findings/incomplete。Finding は id/section/problem/evidence/impact/severity(important|minor)/suggestion。Decision は id/decision(adopt|reject|needs_judgment)/reason/reflected_in。全 findings を重複なく採否に含める。採用には reflected_in と Spec の変更が必要。これは意味的な反映を自動で証明するものではないため、controller は各指摘と反映箇所の意味を確認する。

needs_judgment があれば stop。初回に important を採用したときだけ同じ assignment で再レビューを1回行う。その他は plan。2回目は新たな要求を増やさず残る未確認を成功にしない。採否未完・停止未確認・閉じた gate の後に新規レビューを始めない。

### 4. 設計レビュー

Concern は id/decision_ref/problem/evidence/alternative/tradeoffs/impact/recommendation(keep|change|ask_user)/severity(blocking|worth_considering)。DesignReviewResult は review_id/spec_sha256/status/verdict(sound|concerns|wrong_approach)/assessment/concerns/questions_for_user/incomplete。DesignDecision は id/decision/changes_what_is_built/reason/reflected_in。

完了した設計レビューは1回だけ。Spec レビューの ledger があれば _admit が開始を拒否する。wrong_approach / blocking / questions_for_user / needs_judgment のどれかがあれば、採否によらず stop。changes_what_is_built=true と ask_user の指摘は adopt 不可。採否は全 concern を一意に覆い、採用の反映確認は Spec と同じ。正常時の next は continue。

### 5. スキルの順序と既定担当

Spec と決定記録を DOC_ROOT に commit → 指定時のみ設計レビュー → 指定時のみ Spec レビュー（通常の builder check を代替）、無指定なら builder check 1回 → writing-plans。設計レビューは builder check を代替しない。新しいフローも Spec・Plan は draft のまま commit し、SESSION に置くレビュー記録を commit しない。

issue workflow の implement の既定は claude-code_sonnet_xhigh。fix workflow の implement は main の #377 の self を維持する（#353 の当初の変更は issue にだけ適用する）。既存個人設定の sonnet_default 参照は、利用者が手動で xhigh へ直す。自動移行やユーザ設定の変更はしない。agents のない review assignment 節は invalid_type になること、fallback は個人設定で指定することを記す。README/設定コメント/interfaces.rst の意味を揃え、監査節・CLI 例・model_key は変えない。

## 受け入れ基準・防御範囲・検証

環境: 現行 Dev Container、uv の Python、既存 Pydantic/pytest と fake adapter・一時 Git。実モデル/API/PR をテスト入力として起動しない。開発 Task の担当と実 PR のレビューは上記に明示した回数・割り当てだけを実行する。

実入力: `#42 --merge --spec-review self --design-review fake-agent --assign inspect=fake-agent`、オプション無指定、Issue/context に複数行の日本語、UTF-8/CRLF の Spec。外部結果は独立に構成した ID/ハッシュ/採否を用い、取り違えと正常完了を対にして観測する。

- opt-in と loop_args の分離: T1、無指定 null と明示値、危険な入力が外部起動へ進まないこと。
- role の書込権限・scope/cleanup 退行: T1、実行する S テストと既存テスト。
- 記録の外部保存・版/ID/採否・順序・停止の両側: T2、fake runner と self ライフサイクルで S テスト。
- 順序・builder check 代替・既定担当・手動移行: T3、設定の実読込と、旧/新スキルの同一シナリオ実行記録。固定文言のテストは追加しない。
- 既存の --base / pinned SHA / DOCS_SEPARATE / 登録ツール / ワールド停止 / Refs/Closes: T1/T3 の既存回帰と最終 diff で確認。

テストは S（失敗の成功扱い、取り違え、記録消失、書込権限、順序違反）のみに限定する。F の名前・コメントの一致、L の構文/例外だけの追加テストは作らない。既定 agent の固定名テストは不要。通常の不正入力のパーサ検証は一時実行で代える。

controller は上記条件ごとに Task の証拠を照合し、最後の変更後の関連検証とブランチ全体レビューを行う。base の移動・claim 喪失・有料担当の失敗・安全失敗・Gitleaks の失敗は既存の停止規則に従う。未確認を完了にしない。

## レビュー修正（2026-11-10、サイクル 1）

PR #376 に対して、`pr-review-fix-loop` のサイクル 1 で得たレビュー結果を選別し、必要な修正を行った。planner は `deepseek-v4.1-flash`（claude-code）、サイクルは 1、レビュー対象 HEAD は `1628ff29b68745097911b867576b2b32e47816b9`。

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルの扱い |
|---|---|---|---|---|
| `claude-opus-5-5.md` | `claude-opus-5-5` | claude-code | `1628ff29b687` | 受理（Approve、Info 1 件） |
| `deepseek-v4.1-flash.md` | `deepseek-v4.1-flash` | pi | `1628ff29b687` | 再実行して受理（Approve、Medium 2 件） |
| （レビューファイルなし） | `devin_swe2_max` | devin | — | runner の期限切れで拒否。指摘 0 件として扱わない |

### 指摘の分類

| ID | 区分 | 内容 |
|---|---|---|
| `deepseek-v4.1-flash#M-1` | 対応する | 準備前に終わった一次担当の worktree 不在を拒否し、有効な fallback の結果を失う（Medium、現行 HEAD で再現） |
| `deepseek-v4.1-flash#M-2` | 対応する | 外部レビュー中に CODE_ROOT の HEAD が変わっても completed と記録する（Medium、現行 HEAD で再現） |
| `claude-opus-5-5#I-1` | 対応しない | `review-fix-planning` の旧 opus 既定の記述。動作は変わらず、致命的でない。#353 の所有外 |

解消済みの指摘はない。I-1 は `revisit_when`: `review-fix-planning` の所有者が既定の記述を更新するとき、または利用者が指定したとき。

### 修正内容

- M-1: `review_spec.assess` で、`attempt.work_dir` が存在しない場合に `attempt.payload is None` かつ `attempt.request_path` も `None` または存在しなければ準備失敗として対象外にし、payload を持つ試行や `request_path` が残る試行は拒否する。worktree 自体が symlink のときも拒否する。docstring も同じ意味に更新した。
- M-2: `review_spec.start` で `assess` の後に `implement.head(repository)` を読み、`request.revision` と違えば `the repository changed during the review`、読めなければ `the repository cannot be read after the review` を理由に加える。`review_design.py` も同じ `start` を共有する。
- 変更ファイル: `.agents/skills/issue-to-pr/scripts/review_spec.py`、`.agents/skills/issue-to-pr/tests/test_review_spec.py`。修正 commit は `7053c02ebd81e6afef292817bacc2ad5056c48ef`。

### 守る条件と影響経路

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果 |
|---|---|---|---|---|---|
| 準備前に worktree と request.json が無い試行は監査対象外、request.json が残る不在だけ拒否する | `review_spec.assess`（外部 spec review） | 修正する | 正例 completed、負例 failed + missing worktree | 新規 S テスト 2 件 | 120 passed に含まれる |
| 同上 | `review_design`（共有 `assess`） | 既に同じ経路 | 同じ判定 | 共有実装の代表テスト + review_design の既存テスト | 120 passed に含まれる |
| 同上 | `submit`（self） | 対象外 | self は batch の attempt を持たない | 既存の submit テスト | 120 passed に含まれる |
| 同上 | `test_reviewer_worktree_change_fails...` | 既に満たす | worktree が存在して変更されたら failed | 既存テスト | 120 passed に含まれる |
| 外部レビュー開始後に CODE_ROOT の HEAD が変わったら completed にしない | `review_spec.start`（外部 spec review） | 修正する | HEAD 変化で failed + repository changed | 新規 S テスト | 120 passed に含まれる |
| 同上 | `review_spec.start`（外部 design review、共有） | 修正する（同じ `start`） | 同じ理由で failed | review_spec の代表テスト + review_design の既存テスト | 120 passed に含まれる |
| 同上 | `submit`（self） | 既に満たす | 820-827 行で repository HEAD を確認 | 既存の submit テスト | 120 passed に含まれる |
| 同上 | 通常の外部レビュー（HEAD 不変） | 既に満たす | completed のまま | 既存の external review テスト | 120 passed に含まれる |

同じ条件の再発と設計の見直しのきっかけには当たらない。最初のレビュー修正で、原因は初回実装の適用漏れである。M-2 は外部と self の両方が使う共通の `start` で条件を保つ形にした。

### 検証

- `uv run --locked pytest .agents/skills/issue-to-pr/tests tools/agent_runner/tests/test_config.py -q`: 120 passed in 168.48s、終了コード 0
- `uvx --offline ruff check --select E4,E7,E9,F .agents/skills/issue-to-pr/scripts/review_spec.py .agents/skills/issue-to-pr/tests/test_review_spec.py`: All checks passed、終了コード 0
- `bash scripts/check-layout.sh`: PASS、終了コード 0
- `bash .devcontainer/run-tests.bash`: PASS 27 tests、終了コード 0
- `uv run pytest tests/skills .agents/skills -q`: 746 passed in 530.74s、終了コード 0
- `git diff --check 1628ff29...HEAD`: 終了コード 0
- 修正後の自己レビュー（`run_roles.py --phase self-review` 1 回）: self-review（pr-review 全体）は active findings 0、fix-check は新しい指摘 0。fix-check では環境全体のテスト（C-6）を再実行しなかったが、司令塔が修正後に `run-tests.bash` 27 件と `tests/skills` 746 件を実行して終了コード 0 を確認した。
- fix-check の対照: 修正のガードを外すと、追加した 2 つのテスト（fallback の受理、HEAD 変化の拒否）が失敗することを確認した。

### 結論・実行許可・記録

- 結論: 1（修正して push）。修正 commit `7053c02e` とこの Spec の commit を PR #376 の head へ push する。
- 実行許可: 明示 issue-to-pr 入力 `#353 ... --merge ...` と、2026-11-10 の「#353の作業を引き継いでください」。内容の承認ではない。
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#376-feat-issue-353-review-steps/verified/1628ff29b687.json`
- fix-check: `reviews/usaturn/create-reso-world/#376-feat-issue-353-review-steps/verified/7053c02ebd81.fix-check.json`
- 工程の記録: `reviews/usaturn/create-reso-world/#376-feat-issue-353-review-steps/verified/1628ff29b687.planning.json`
- 判断の記録と状況コメント: サイクル 1 の `review-fix-planning` コメント（PR #376）

## レビュー修正（2026-11-10、サイクル 2）

PR #376 のサイクル 2 で得たレビュー結果と、サイクル 2 の自己レビュー・fix-check の結果を反映した。planner は `deepseek-v4.1-flash`（claude-code）、サイクルは 2、レビュー対象 HEAD は `adfe7ebc1e9c6f65e7ed28d43baab81b1757a3f7`。

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルの扱い |
|---|---|---|---|---|
| `claude-opus-5-5.md` | `claude-opus-5-5` | claude-code | `adfe7ebc1e9c` | 受理（Approve、指摘 0） |
| `SWE-2-Max.md` | `SWE-2 Max` | devin | `adfe7ebc1e9c` | 受理（Approve、指摘 0） |
| `deepseek-v4.1-flash.md` | `deepseek-v4.1-flash` | pi | `adfe7ebc1e9c` | 受理（Approve、M-3 1 件） |

### 前のサイクルの判断

- `M-1`・`M-2`: サイクル1の `fix` を現行 HEAD で確認し、`resolved`（修正 commit `7053c02e`、追加テスト、サイクル2の 3 レビュアーが active findings 0）。
- `I-1`: サイクル1の `skip` を引き継ぐ（新しい根拠なし）。

### 指摘の分類

| ID | 区分 | 内容 |
|---|---|---|
| `deepseek-v4.1-flash#M-3` | 対応する | 成功した試行の worktree 不在を監査せず受理する（Medium、safety、現行 HEAD で再現） |
| `deepseek-v4.1-flash-commit-6fa1e57f926e#S-1` | 対応する | worktree を clean な checkout への symlink に置き換えると監査を回避する（High、safety、self-review） |
| `fix-check#V-1` | 対応する | Spec の M-1 記述が payload 条件を欠く（fix-check。この Spec 更新で解消） |

### 修正内容

- M-3: `review_spec.assess` の skip を、`attempt.payload is None` かつ `request_path` も None/不在の準備失敗だけに限定した。payload を持つ試行は worktree 不在なら拒否する。修正 commit `6fa1e57f`。
- S-1: `review_spec.assess` で `attempt.work_dir.is_symlink()` のときは、参照先の HEAD/status を読まずに拒否する。修正 commit `a13852a3`。
- V-1: この Spec の M-1 記述を、payload の有無と symlink を含む最終条件に更新した。コードの変更はない。

### main の #377 との競合解消

- main `1b0df121`（PR #377「Update agent-runner」）の取り込みで `.devcontainer/agent-runner.toml` が競合した。利用者の決定（2026-11-10）に従い、main の新しい既定を優先した。
- 解消: `review.inspect` は main の `claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`、`fix.implement` は main の `self` を採用した。`issue.implement` は #353 の `claude-code_sonnet_xhigh`、`roles.spec-review`・`roles.design-review`、`claude-code_sonnet_xhigh` エージェント、Spec・README・interfaces.rst の説明を残した。
- `README.md`・`.devcontainer/README.md`・`tools/agent_runner/interfaces.rst` の既定の記述を、issue は sonnet xhigh、fix は main の self に揃えた。
- 競合解消はマージ commit に含める。マージ結果で関連テストと環境全体のテストを再実行する。

### 守る条件と影響経路

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 |
|---|---|---|---|---|
| payload を持つ試行の worktree が無い場合は監査せず受理しない | `review_spec.assess`（外部 spec/design review 共有） | 修正する | valid payload + workdir/request 不在 → failed | 新規 S テスト（M-3） |
| worktree が symlink なら受理しない | `review_spec.assess` | 修正する | clean checkout への symlink + valid payload → failed + symlink | 新規 S テスト（S-1） |
| payload を持たず準備前に終わった試行は対象外 | `review_spec.assess` | 既に満たす | primary payload なし + worktree/request 不在 → skip、fallback completed | 既存の fallback テスト |
| request.json が残る worktree 不在は拒否 | `review_spec.assess` | 既に満たす | failed + missing | 既存の missing-after-preparation テスト |
| self の submit | `submit` | 対象外 | batch の attempt を持たない | 既存の submit テスト |

M-3 は M-1 修正の回帰（きっかけ 2）であり、点の修正ではなく payload の有無で監査対象を決める条件を 1 か所にまとめた。S-1 は PR が追加した `assess` の symlink 経路で、worktree 自体の symlink を拒否する。保証を狭めていない。

### 自己レビュー・fix-check

- 自己レビューは `run_roles.py --phase self-review` を 1 回実行。self-review は `6fa1e57f` で High の S-1（symlink、safety）を 1 件見つけ、修正した。2 回目の自己レビューは行っていない（S-1 修正後の再レビューはしていない）。
- fix-check は `6fa1e57f` の M-3 を確認し、主張 C-1〜C-6 は holds、C-7（環境全体のテストの再実行）は未実施で残した。V-1（Spec の M-1 記述の不一致）を 1 件見つけ、この Spec の更新で解消する。fix-check の結果は `verified/6fa1e57f926e.fix-check.json`。
- ガードを外した対照で、M-3・S-1 の追加テストが失敗することを確認した。

### 検証

- `uv run --locked pytest .agents/skills/issue-to-pr/tests tools/agent_runner/tests/test_config.py -q`: 122 passed in 158.27s、終了コード 0
- `uvx --offline ruff check --select E4,E7,E9,F .agents/skills/issue-to-pr/scripts/review_spec.py .agents/skills/issue-to-pr/tests/test_review_spec.py`: All checks passed、終了コード 0
- `bash scripts/check-layout.sh`: PASS、終了コード 0
- `git diff --check adfe7ebc...HEAD`: 終了コード 0
- `bash .devcontainer/run-tests.bash`: PASS 27 tests、終了コード 0
- `uv run pytest tests/skills .agents/skills -q`: 781 passed in 586.11s、終了コード 0

未確認の事項: なし。

### 結論・実行許可・記録

- 結論: 1（修正して push）。M-3 の `6fa1e57f`、S-1 の `a13852a3`、およびこの Spec の commit を PR #376 の head へ push する。
- 実行許可: 明示 issue-to-pr 入力 `#353 ... --merge ...` と、2026-11-10 の「#353の作業を引き継いでください」。内容の承認ではない。
- 確認済みの一覧: `verified/adfe7ebc1e9c.json`
- fix-check: `verified/6fa1e57f926e.fix-check.json`
- 工程の記録: `verified/adfe7ebc1e9c.planning.json`
- 状況コメント: サイクル 2 の `review-fix-planning` コメント（PR #376）

## レビュー修正（2026-11-10、サイクル3・限定再設計）

planner: `openai-codex/gpt-6.1-sol`（pi）。レビュー対象は `bfd1a72e53382242195640b2df13ac1e686364ea`。サイクル1/2の履歴は当時の実装・判断を示し、現在の監査・回収条件は本節の状態表に従う。

### 実行許可・入力

利用者は、引き継ぎとinspect変更の後に一旦停止し、全面削除の是非を相談した。提案した「既存実装を保存し、worktreeの状態・監査・後片付けだけを限定再設計する」に対し、「提案通りに作業を実施してください」と明示した。これは当該安全境界の再設計の実行許可であり、全面削除・保証の縮小・内容の承認SHAを意味しない。元のissue-to-pr `--merge` と所有範囲は維持する。

旧loop `c8e022a0a20d48ff80172e4e71475161` はDevin再実行の結果がない中断を検出した。関連プロセス不在を確認し、helperのrecoverでabandoned・lock解放済み。旧cycle-endは行わず、修正後の新しいrunへ引き継ぐ。拒否・中断を指摘0件とは扱わない。

| レビューファイル | モデル/runtime | HEAD | 入力の扱い |
|---|---|---|---|
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | bfd1a72e5338 | 旧loop受理、M-1 |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | bfd1a72e5338 | 旧loop受理、H-1/L-1/I-2 |
| SWE-2-Max.md | SWE-2 Max / devin | bfd1a72e5338 | 旧loopはpayload拒否。保存済み初回成果を別途検証し、計画入力に含めた。再実行の成果はない |

利用者指定の新inspectは `claude-code_opus_xhigh,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。未登録のopus/xhighは利用者のOKに基づきSESSIONの作業専用templateにだけ追加し、check-options成功。共有・個人設定は変更していない。implementは既存の明示指定 `pi_opencode-go_deepseek4-flash_max`、fallbackなし。

### 分類

| 指摘 | 判断 | 根拠 |
|---|---|---|
| deepseek H-1 / opus M-1 | 対応する（統合） | 祖先symlinkで別実体を監査してcompleted、最終symlinkのcleanupで参照先を削除することを隔離実行で確認。安全性の欠陥 |
| deepseek L-1 | 対応する | 両promptがIssue repoだけをrepositoryと表示し、対象checkoutを含まない。別repoの規則を選ぶ誤りにつながる |
| deepseek I-2 | 対応する | Planに従うとfixの既定をsonnetに戻す。Spec/設定と実行指示が矛盾する |
| SWE L-1 | 対応しない | self submit中のSpec消失は明示エラーで拒否し、元のSpec復元後に同じ結果を再submitしてcompletedへ回復することを実行確認。失敗保存方式の統一は今回の致命的修正ではない |
| SWE I-1 | 対応しない | TOMLコメントの30分の根拠・位置・1回制の説明不足。設定値とスキルの手順は正しく、動作を誤らせない |
| 旧opus I-1 | 対応しないを引き継ぐ | review-fix-planningの旧既定記述は所有外、新しい根拠なし |

SWE L-1は復元後も回復不能・記録消失・成功誤報を示す新しい再現、または利用者の名指しで見直す。SWE I-1はコメントを所有する別タスクか利用者の名指しで見直す。過去のM-1/M-2/M-3/S-1/V-1は既存ガードと履歴を確認し、以前のfixを現行HEADで解消済みとする。S-1の祖先・回収への適用漏れは今回のH-1として扱う。

### 守る条件の設計

S-1の `a13852a3` は最終要素のsymlinkを監査側でだけ拒否し、祖先・登録実体・回収が同じ前提を共有していなかった。同じ条件の2回目なので点の修正を続けず、状態分類を共有する形へ見直した。最初の今回修正 `fdd8c8f0` でも「準備前に不在」「異常消失」「以前に回収した」の区別が不足したため、利用者の実行指示に従って限定再設計した。

比較した案は、各呼出元へのガード追加、共有する状態分類と最小回収記録、全面削除/runner・sandboxの新設。共有分類と最小記録を選び、他の機能の破棄・新しい一般的な復旧基盤・保証の縮小は採用しない。opt-in、Spec/IDの照合、採否、設計レビューの停止条件、準備失敗からのfallback、停止/機密/dirtyの保護は維持する。

| 状態 | 確認する事実 | 監査/cleanup |
|---|---|---|
| 準備前不在 | 停止確認済み、非成功、payload/依頼記録なし、worktree不在・未登録 | 監査対象外、回収対象なし。成功した試行を準備前と推測しない |
| 登録実体 | 正規の絶対path、全構成要素にsymlinkなし、同repositoryの登録、同common-dir、Gitで読める実体 | HEAD/statusを監査。回収はforceなしのGitだけ。dirtyなら保持 |
| 予期しない消失 | 成功/payload/依頼記録/登録の事実があるが実体なし、回収実績なし | failed/retained、runner出力とledgerを保持 |
| 不適切・確認不能 | symlink、未登録、別common-dir、非正規path、lstat/Git等の読取失敗 | 成功根拠にも削除対象にもしない |
| helper回収済み | 同じreview/batch/runnerに対応する実績があり、現在も不在・未登録 | cleanupの再実行はno-op。新しいレビュー受理の根拠にはしない |
| 回収後の再出現 | 実績があるpath/runner領域に実体・リンク・登録が再出現 | 新しい対象として削除せず保持 |
| 停止未確認/機密 | stop未確認またはsensitive_pathsあり | 実体を監査せずfailed/retained。不在を安全扱いしない |

`implement_task.classify_attempt_worktree` を実装/レビューの監査と共有cleanupが利用する。`remove_attempts(repository, batch)` の既存呼出し・戻り値を維持し、review cleanupは回収済みpathと成功通知を任意引数で渡す。designレビューは共通処理を使い、別実装を増やさない。

成功した回収だけをreview ledgerの `cleanup.jsonl` へ追記し、review_id/kind/Specハッシュ/batch.run_id/runner_dir/当該batchのpathへ結び付ける。既存の結果・採否は上書きしない。実績のない消失を完了と推測せず、部分回収の再実行では成功済みの対象を再操作しない。記録のI/O失敗は明示停止/保持とし、削除済みの実体が元に戻ったとは報告しない。

自己レビューで、この新記録がhardlinkだと別ファイルへ追記する欠陥を確認した（下記H-1）。同じ変更が生んだ安全性の欠陥なので、回収記録の所有する実体も境界に含め、読取前と追記前で同じprivate regular file検査を使う設計に見直した。共有inode・symlink・非regular・対応不一致・破損を、最初の削除を含む副作用より前に拒否する。既存の専用ファイルと部分/再実行の挙動は保つ。

### 受け入れ基準・影響経路と実行証拠

環境は現行Dev Containerとuv、fake adapterと一時Git。日本語/複数行UTF-8のSpec・Issue、正常結果、準備失敗+fallback、成功試行のmissing+unregistered、元の登録文字列を保つ祖先symlink、同pathの別common-dir、初回/部分/繰返し回収、回収後の再出現、hardlinkの記録を扱う。sandbox・実APIによるテスト・runner/adapters/他スキルの変更は対象外。停止済み試行を前提とし、悪意ある同時書換え全般への耐性を追加したとは主張しない。

統合担当はcontroller。関連テストの件数だけでなく、入力→共有分類→監査→保存→回収→再実行まで同じ条件が維持されることを確認した。

| 守る条件 | 経路/変更前 | 判定 | 観測する結果/assertion | 最終コード版と実行証拠 |
|---|---|---|---|---|
| 別実体を監査/削除しない | spec/design共有assess、remove_attempts。祖先symlinkを受理、最終symlinkの参照先を削除 | 修正する | failed/retained、参照先bytes/mode/リンク/登録保持 | `79429596`、controller独立再現 `repro-final-code.json` と関連141件成功 |
| 準備前/異常消失を区別 | 成功したmissing+未登録でも出力を削除 | 修正する | missing成功試行でrunner/ledger保持、準備失敗fallbackは成功 | `79429596`、独立再現/関連141件 |
| 回収済み/再出現を区別 | review.cleanupは過去の成功を保存しなかった | 修正する | 部分/繰返しcleanup正常、再出現は保持、結果を上書きしない | `79429596`、private receipt/partial/repeat/reappearanceのSテストと関連suite |
| 記録の共有実体へ書かない | 新しいappendがhardlinkへ追記 | 修正する | 削除前に拒否、別ファイルbytes/mode/inode・登録・runner・既存記録保持 | `79429596`、`hardlink-receipt-fixed.json`。不正記録を拒否し全対象保持 |
| 通常操作/停止・機密・dirty | implement/review/designの共通回収 | 既に満たす条件を維持 | cleanだけ回収、その他保持、fallback/版検査を維持 | `79429596`、関連141件・skills800件 |
| 対象の取り違えを防ぐ | spec/design compose_promptがIssue repoだけを出した | 修正する | code checkout/Issue repoを別ラベルで生成 | `79429596`、独立prompt生成で両値確認、コードのラベル照合 |
| 既定担当を誤って変更しない | Planがfixもsonnet、Spec draftと記載 | 修正する | issue=sonnet xhigh/fix=self/Spec completedに整合 | `fdd8c8f0`のPlan修正と最終差分/設定/参照照合。後続は当該値を変更していない |
| self submitの消失時の記録方式 | Spec消失はエラー、復元で回復 | 対象外 | SWE L-1のskip理由に従う | 一時再現で復元後completed。今回この経路を変更していない |

テストはSだけを追加し、共有ガードは実装モジュールの代表へまとめた。祖先負例は元の登録文字列を維持し、他の異常がガードを隠さない。文書/名前の固定値テストは追加していない。

失敗時は参照先のbytes/mode/リンク・worktree登録・runner/ledger・既存結果の前後を比較した。中心symlinkガードを1つだけ外す隔離対照では、元の登録文字列を保った祖先pathがcompletedになり、安全条件の破れを検出した。private receiptの共有inodeガードだけを外す隔離対照でも、新規hardlink負例1件が失敗した（exit1）。いずれも専用worktreeのガードを外しておらず、対照用worktreeは回収した。

### 自己レビュー・担当・検証結果

- `run_roles.py --phase self-review` は1回だけ。self-review/fix-checkはいずれもselfで、自己レビュー枠の予約を保持した。PR全体レビューは `gpt-6.1-sol`（pi）のprepare/completeが成功、cleanup成功。High H-1（hardlink）とInfo I-2（重複/複数異常のテスト）を記録した。
- fix-checkは6主張・6変更ファイル・209文書候補を列挙して検査し、回収記録H-1をV-1、テストの問題をV-2として確認した。確認対象版は `87403ff0`。当該版の違反記録を上書きして修正済みにしていない。
- 修正: 子 `8e083090` → 専用worktree `fdd8c8f0`（最初の境界/prompt/Plan）、子 `e358abeb` → `87403ff0`（共有状態と最小回収記録）、子 `6e442fa9` → `79429596`（private receipt・代表負例の整理）。既存実装/履歴を削除していない。
- 自己レビュー後の修正は再レビューしていない。最後の変更後にcontrollerが独立再現・対照・関連/環境検証をやり直した。未実施はその修正後の追加レビューと実モデル/APIによるテストであり、成功とは報告しない。
- 全実装担当は `pi_opencode-go_deepseek4-flash_max`。runner観測は `deepseek-v4.1-flash / opencode-go / max`、fallbackなし、成功した3依頼はstop_confirmed=true。途中の補正依頼は利用者停止で中断し、結果なし・プロセス不在を確認、成果を取り込んでいない。
- 実装担当は限定再設計と自己レビュー後修正で各1回 `python3` を使った（機械的編集/使い捨てprobe）。規約違反として残す。テスト/検証はuvで実行し、違反を規約遵守や検証成功へ読み替えない。

最終コード `79429596a26b989bd1f808aa18c66be1cd938bb8` でcontrollerが同期実行:

- 関連pytest: **141 passed in 171.31s**、exit0。
- `bash .devcontainer/run-tests.bash`: **27件成功**、exit0。
- `uv run pytest tests/skills .agents/skills -q`: **800 passed in 556.46s**、exit0。
- 変更Pythonのruff E4/E7/E9/F、layout、`git diff --check bfd1a72e...HEAD`: すべてexit0。
- 独立再現: hardlink拒否前後で別ファイル/登録/runner保持、最終/祖先symlink・別repo・missing成功を拒否/保持、正常回収と両prompt生成を確認。

証拠の保存先は `/workspaces/reso-world/tmp/agents/issue-353-c3.e0m_q84t`（controller-checks.jsonlと各ログ、独立再現、対照差分/結果、全担当の役割/結果）。所要時間はrunner実測で最初の実装764.92秒、限定再設計2759.02秒、自己レビュー後修正899.32秒。自己レビューは400.02秒。未測定のcontroller能動時間を0や推測値で補わない。

確認済み一覧: `verified/bfd1a72e5338.json`。自己レビュー: `gpt-6.1-sol-commit-87403ff0b7629aef19b7b9024ac631c87296dd3e.md`。fix-check: `verified/87403ff0b762.fix-check.json`。工程の記録: `verified/bfd1a72e5338.planning.json`。保存先はいずれもPR #376のレビューディレクトリ。

結論は1（修正して既存PRへpush）。公開後のSHA・状況コメント・新loop・マージ結果はPR/loop記録とhandoffに記し、このSpecへ結果追記だけのcommitを増やさない。

## レビュー修正（2026-11-10、判断サイクル4）

planner: `openai-codex/gpt-6.1-sol`（pi）。対象HEADは `3afb44b1fa2a936bcb3c2a4416ea8f62ff8ddb41`。利用者のhandoff指定による継続と、既存のissue-to-pr `--merge`・review-fix-planningの完遂指示を実行許可とする。内容の承認SHAはない。完了済みPlanの通常実装は再開しない。

新loop `a0f75c1805f24bae84901334639e1ccb` のサイクル1で、指定のopus xhighとDeepSeek maxは受理、SWE-2 Maxはrunnerのrate_limit（response_failed、exit1）で拒否、stop_confirmed=true。拒否を指摘0件とは扱わず、runner失敗の再試行はしない。今回のSWE成果はない。前のskip3件は新しい根拠がないため引き継ぐ。

### 指摘・自己確認の採否

| 参照 | 判断 | 根拠・見直す条件 |
|---|---|---|
| claude-opus-5-5#L-1@3afb44b1fa2a | 対応しない | symlink/`..`を含む手組みのoutput-dirでrejected/retainedを再現。正規化した実pathの再現ではimportable/回収成功（agent_tmp自体を使った実行ではなく、公式pathの性質はコードで照合）。対象外の出力先表記に限る停止で、別対象操作や成功誤報はない。公式pathでの再現、データ損害、利用者の名指しで見直す。 |
| claude-opus-5-5#L-2@3afb44b1fa2a | 対応しない | implementの部分回収後の再cleanupでis missingを再現。通常手順は1回回収してretainedを保持・報告するため、通常の取り込みを妨げない。reviewの再cleanupは回収記録を持つ。通常手順への影響、消失・誤操作の再現、利用者の名指しで見直す。 |
| claude-opus-5-5#L-3@3afb44b1fa2a | 対応しない | receipt追記のI/O失敗で後続worktreeの報告漏れを再現。ただし失敗がretainedとして明示され、後続実体・登録・runnerを保持し、追記を戻した再cleanupは完了。失敗報告の列挙不足であり、成功誤報や削除ではない。回復不能・消失・成功誤報、利用者の名指しで見直す。 |
| planner#S-1@3afb44b1fa2a | 対応する | SKILL.md:299はdecide前にreflected SHAをSpec自身へ記入させる。両reviewの正常手順でSpec内の値とdecideが記録する値の不一致を再現。公式手順の誤った版記録で、分類(b)の事実誤認に該当する。 |
| planner#S-2@3afb44b1fa2a | 対応しない | 採否の欠落/重複テストが未反映ガードに隠れることを、対象の全件対応ガードだけを外した隔離対照で確認。現行の全件対応ガードは存在し、欠落を受理する実装の欠陥や回帰ガードの削除ではない。将来の検出力改善として見送り、実装側の採否漏れ・記録破損の再現、または名指しで見直す。 |
| planner#S-3@3afb44b1fa2a | 対応しない | test_review_spec.py:265-274は同じ保存先実体を直接とsymlinkで確認するD重複。テスト採用基準との不一致は記録するが、現在のガード・動作を損なわない重複整理だけを今回の致命的修正へ足さない。テストを所有する別タスク、利用者の名指しで見直す。 |

前セッションの再現と確認済み一覧を救出し、復旧controllerが独立の読み取り専用担当でS-1の両経路と採否の整合を確認した。この調査は15変更ファイルの全文確認とは扱わない。その後、予約済み自己レビューの担当が15変更ファイル全文と関連依存を読み、不足していた固定全体差分とbase AGENTSはcontrollerがファイルで渡し、同じ役割の残りの照合を終えた。各担当の読取範囲・未知の識別情報は保存レビューに区別して記した。controllerは今回の全変更・両decideの生バイト記録・影響する手順を直接確認し、隔離した修正後commitで実行検証した。S-1の原指摘は「反映後 SHA を Spec 自身へ事前記入する手順が循環しています」。S-2は「採否の欠落・重複テストが別の拒否条件に隠されています」、S-3は「同じ実体を別パスで確認する D テストがあります」。

### 守る条件と影響経路

S-1は既存の記録手順の誤りで、今回までのworktree境界の修正とは別の原因。過去にこの条件を修正した記録はなく、設計の見直しのきっかけには該当しない。統合担当はcontroller。

条件は、decideが保存する反映後snapshotの生バイトとSHAが一致し、同じSHAを記録するために対象Specを再変更しないこと。Specには採否理由・反映箇所と決定時に既知の情報を残し、decide後に得たreflected SHAはSESSIONと最終報告に保存する方法を推奨する。Spec自身へハッシュを埋める案は自己参照になるため採用しない。hash計算仕様・版検査を変える案は不要で、helperは変更しない。

| 守る条件 | 経路 | 判定 | 観測する結果・方法 | 証拠 |
|---|---|---|---|---|
| 最終SpecのSHAをそのSpecへ埋めない | SKILL.md共通採否手順→spec.decide | 修正する | 複数行日本語/CRLFのSpecを使うself正常ライフサイクル。Spec変更を終えてdecideし、戻り値・decisions.json・reflected.md・現在SpecのSHAが一致、後処理でSpec不変 | ee787309の隔離版で重要指摘採用→rereview、指摘なし→plan。全SHAとcommit blobが一致、SESSION記録前後のSpec不変。旧手順は不一致。controller/self-review-lifecycle.log |
| 同上 | 共通手順→design.decide | 修正する（同じ手順） | sound/continueの正常入力でも同じ比較。SESSIONへの記録だけを追加する | ee787309の隔離版でsound/採用の両方→continue、全SHAとcommit blob一致・SESSION記録で不変。同じprobeで旧手順の不一致も確認 |
| 採否・停止・再レビューの検査を維持 | 両helperのdecide/submit、SKILLの分岐 | 既に満たす | 本体は変更しない。既存関連回帰と最終差分で確認 | helper差分なし。両decideを精読、修正後の関連141件/自己レビュー内の絞った30件が成功。文書候補64件・5主張・変更1ファイルのfix-check検査を完了 |

動作環境は現行Dev Container/uv、一時Gitとself/fakeのみ。文書の固定文言を写すFテストは作らず、手順を実行する使い捨てprobeで検証する。実モデルによるスキル挙動比較を追加しない。実装は既定を推測せず、loopから渡されたDeepSeek maxへ1件依頼する。担当の実装・検証は同期で待ち、以後の自己レビューはこのsource_headの枠を最大1回だけ使う。以前のbfd1a72eの予約は再利用しない。

### 修正・検証・自己レビューの結果

修正は指定の `pi_opencode-go_deepseek4-flash_max` に1件依頼した。観測モデルはopencode-go/deepseek-v4.1-flash/max、stop_confirmed=true、326.26秒（batch329.67秒）。子commit6365b61bを差分確認してee787309193f51fadc0cd8090b5544065e4a3b75へ取り込んだ。変更はSKILL.mdの共通採否/decide/停止報告だけで、helper・設定・テストは変更していない。runnerのoutside_changesは空、保護対象外の既存不在worktree等はunprotected_changesとして記録し、他の作業領域を修復・削除していない。

controllerはee787309で関連141 passed（216.78秒）、環境27件成功、skills800 passed（672.43秒）、layout/diff --check成功を同期で確認し、自己レビュー前のGitleaksも成功した。複数行日本語CRLF/別code-doc checkoutの手順probeで、旧手順の不一致と新手順の4正常分岐を比較した。返値・decisions.json・reflected.md・現在Spec・commit blobの一致はhashlibとgitの生バイト比較で確認した。固定文言テストや有料モデルによる反復評価は追加していない。

run_roles.pyのself-reviewを1回だけ予約し、self-review=self/fix-check=selfを実行した。自己レビューの固定PR全体差分は15ファイル、結果はactive0、helperの保存/cleanup成功。fix-checkはcontrollerが行い、文書候補64件（consistent25/unrelated39）、5主張、変更1ファイルを全件照合し、新しい違反なし。自己レビュー後のコード修正はない。このSpecの結果追記は今回の実質修正と同じ公開単位の最後に1回だけcommitし、公開後の結果だけのcommitは増やさない。

自己レビュー: `gpt-6.1-sol-commit-ee787309193f51fadc0cd8090b5544065e4a3b75.md`、修正確認: `verified/ee787309193f.fix-check.json`。今回の自己レビューは約790秒、fix-checkの記録対象143秒（既存検証の再利用分を0秒に換算していない）。前のsource_headの枠は再利用していない。

結論は1（修正して既存PRへpush）。今回の採否は前の13判断に新しい6判断を加え、resolved10/fix1/skip8。S-1だけを今回の致命的修正として採用した。push・判断コメント・次のloop・最終化の結果はPR/loop記録とhandoffに記す。

救出元SESSION: `/workspaces/reso-world/tmp/agents/issue-353-c4.6gq06jrc`（repro-round4.py/json）。復旧・検証SESSION: `/workspaces/reso-world/tmp/agents/pr376-recovery.vwhu4pkm`。controller-checks.jsonl、controller/self-review-lifecycle.log、fix-checkと担当のroles/logを保持する。各実測のargv/HEAD/exitを記録し、前セッションの未記録時間は推測しない。

## 最終確認（2026-11-10、判断サイクル5）

対象HEADは68195dfd85d106b1ff063210de78e34f38351d67。plannerはopenai-codex/gpt-6.1-sol（pi）、状態completedを維持し、内容承認SHAがないことと実行許可を区別する。新runはe9373b20933147faa4a579978bebe93c、今回の利用者指定どおりinspect=claude-code_opus_default/devin_swe2_max/pi_opencode-go_deepseek4-flash_max。旧runのxhigh成果を救出したサイクルを完了してから、割当を手編集せず新runへ切り替えた。

3レビュアー全員の現行pairはhelperが受理し、新しいactive/未確認候補は0。Opusは約113秒、SWEは約570秒、DeepSeekは約393秒、レビュー工程全体は約643秒。SWE本文には存在しない履歴参照・規模の不正確な記述があるため、その説明を事実の根拠には採用せず、正式な19判断の記録・現行committed source・他の実行証拠で確認した。成果の受理と内容の正しさは区別する。

前回S-1を解消済みに変更した。SKILL/helperのblobはee787309から変わっておらず、生バイトprobeの前提が保たれている。前回の採否を含む19判断はresolved11/skip8、対応する指摘0。skipは新しい根拠がないため維持し、既知の制限と回避方法はPR本文に記載済み。新たな実装修正・自己レビューの再予約は行っていない。

検証は対象HEADのままと、最新base70634b5d1ad7bc7bab24ca6258edfed0a7c16fe7を隔離worktreeでmergeした一時commit33897ce67863bafccb79d7e7393b8260bdd52b22の両方で実行した。両方とも環境テスト27件・layout・diff --checkが成功し、skillsはheadで800 passed（605.85秒）、mergeしたツリーで803 passed（644.37秒）。一時mergeをPRへpushしていない。検証後にそのworktreeを回収した。argv/実際のHEAD/base/exit/ログは復旧SESSIONのfinal-validation.jsonl、検証したツリーはverified-merge.json、finalize入力はfinalize-checks.json。

利用者は、mainが最後の確認から進んでも途中停止せず完了まで対応するよう追加指示した。これはmainの前進を理由とする打ち切りをせず、新しい先端を含めて必要な検証をやり直す実行許可として記録し、baseの値だけを書き換えて検証を省く許可とは扱わない。

結論は2（追加修正不要、最終化へ進む）。本節はマージ前の確認記録であり、マージ・関連Issue更新の成功を先取りしない。確認済み一覧はverified/68195dfd85d1.json。判断コメントとfinalize結果・マージ結果はPR/loopと引き継ぎ記録へ保存し、公開後の結果だけを足すcommitは作らない。

## #390 による訂正（追記）

上の #L-2・#L-3 の行は当時の判断として残し、書き換えない。後続の #390 で次を確認した。

- #L-3 の「追記を戻した再cleanupは完了」という一般化は、成功証拠を保存できる環境での限られた回復を指す。#390 では、worktree の削除成功後に cleanup.jsonl の追記だけが単発で失敗した場合に、削除成功を独立した成功証拠として残し、別プロセスの通常 cleanup が欠落したイベントだけを追記して回復する仕様にした。証拠を保存できない crash、証拠保存自体の失敗、不明な破損・途中書込みは自動回復の対象外で、失敗を成功にしない。訂正の根拠と仕様は `docs/superpowers/specs/2026-11-12-issue-390-review-cleanup-design.md` の「成功証拠と復旧の仕様」にある。
- #L-2 の implement cleanup の部分回収後の再cleanup は、今回の #390 と関連するケースだが対象外とする。implement cleanup の回収方法は変えず、callback 失敗後に残りの試行と run_dir を削除せず報告する範囲だけを加えた。review cleanup の成功証拠・lock・保持一覧の仕様を implement cleanup へ広げない。
