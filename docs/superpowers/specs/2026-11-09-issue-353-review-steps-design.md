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

利用者が明示した run にだけ、Plan 前の Spec レビューと、その前の設計レビューを追加する。別担当の失敗を自己レビューの成功へ読み替えず、レビュー対象の版と指摘の採否を保存する。既定の Plan 実装・レビュー修正担当を sonnet xhigh に変更する。

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

両 workflow の implement の既定は claude-code_sonnet_xhigh。既存個人設定の sonnet_default 参照は、利用者が手動で xhigh へ直す。自動移行やユーザ設定の変更はしない。agents のない review assignment 節は invalid_type になること、fallback は個人設定で指定することを記す。README/設定コメント/interfaces.rst の意味を揃え、監査節・CLI 例・model_key は変えない。

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
- `uv run pytest tests/skills .agents/skills -q`: 748 passed in 495.80s、終了コード 0

未確認の事項: なし。

### 結論・実行許可・記録

- 結論: 1（修正して push）。M-3 の `6fa1e57f`、S-1 の `a13852a3`、およびこの Spec の commit を PR #376 の head へ push する。
- 実行許可: 明示 issue-to-pr 入力 `#353 ... --merge ...` と、2026-11-10 の「#353の作業を引き継いでください」。内容の承認ではない。
- 確認済みの一覧: `verified/adfe7ebc1e9c.json`
- fix-check: `verified/6fa1e57f926e.fix-check.json`
- 工程の記録: `verified/adfe7ebc1e9c.planning.json`
- 状況コメント: サイクル 2 の `review-fix-planning` コメント（PR #376）
