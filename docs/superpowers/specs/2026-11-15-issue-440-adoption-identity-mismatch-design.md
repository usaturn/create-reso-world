# Issue #440: レビュー採用実績をモデル名の表記差で未採用 0 件と誤判定しない

## 管理・実行許可

- 状態: `draft`
- 対象: https://github.com/usaturn/create-reso-world/issues/440
- 利用者の指示（2026-11-15、`/issue-to-pr` の引数）:

  ```text
  #440 --merge
  --design-review pi_openai-codex_gpt6-sol_xhigh
  --spec-review pi_opencode-go_deepseek4-flash_max
  --implement pi_alibaba_qwen4-max_max
  --assign implement=pi_alibaba_qwen4-max_max
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh
  ```

- 許可された範囲: issue-to-pr の委任により、通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで続ける。`--merge` により、PR 作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと関連 Issue の更新を行う。これは実行許可の記録であり、内容の承認（`approved`）ではない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-440-adoption-model-label`（branch `fix/issue-440-adoption-model-label`、base `origin/main` `273ace19215430fa05042a512d63dc19e4e3a058`）。Spec・Plan はコードと同じ worktree・PR に入れる（`DOCS_SEPARATE=false`）

## 背景

`review_findings.py stats` の `provenance.executions[].adopted` は、確認済みの一覧（`verified`）の入力の担当と、v2 の判断記録（`review-records/v2`）で Fix を決めたサイクルの `seats` の担当を照合して数える（`.agents/review-findings.md` 7.1 節）。照合する `_adoption_matches` は、`_actor_identity` が返す `{"model", "runtime", "provenance"}` の辞書全体を完全一致で比べる。

このため、実行識別子（`session_id`・`run_id`・`request_id`）を含む `provenance` がすべて同じでも、`model` の文字列だけが違う（PR #439 の `SWE-2 Max` と `SWE-2-Max`）と一致せず、`False` を返す。`_provenance_stats` は `False` を未採用として扱うので、採用済みの指摘が終了コード 0 のまま `adopted: 0` になり、診断も出ない。

改善前（Issue の基準値、main `8a791a12`）:

| 条件 | 終了コード | 先頭担当の adopted |
|---|---|---|
| model と実行識別情報が同じ | 0 | 1 |
| 実行識別情報は同じ、model だけハイフンと空白が異なる | 0 | 0（診断なし） |
| 別 session | 0 | 0 |
| 実行識別子がすべて unknown | 0 | null |

## 目標

- 表記差・識別情報の不一致を、黙って未採用 0 件と確定しない
- 同じ実行と確認できる採用（識別情報の完全一致）は 1 件として残す
- 同じ実行と確認できない不一致は、診断を出して未評価（`null`）にし、推定で採用を付けない
- 別 session の 0、全 unknown の null、PR・指摘の参照・検出 HEAD の境界を保つ
- `model` などの観測値は、正確な文字列のまま保存・出力する

## 対象外（Issue のとおり）

- 過去の記録・観測モデル名の書き換え、全ランタイム共通のモデル別名辞書の導入
- マージ判定・Issue close・review_eval の有効化
- PR #439 の status 応答形・テスト重複の再開、#429・#434 の内容
- 保存時（`review_records.py` の `validate_record`・候補一覧の書き込み）の検査の追加

## 決定記録

### D1. 不一致の検出を集計時（`_adoption_matches`）に置く

- 選択した案: `stats` の採用照合の中で不一致を検出し、未評価と診断にする。保存時の検査は足さない
- 検討した別案: (a) 判断記録の保存時（`review_records.py`）に、seats の `model` と確認済みの一覧の `model` の一致を検査して拒否する。(b) 両方に置く
- 選択理由: 誤集計が起きるのは集計時であり、既に保存された記録（PR #439 など）も集計時の検査でしか守れない。保存時の拒否は、記録を書く流れ（review-fix-planning の保存）を止める新しい失敗を作り、Issue の範囲（集計の誤判定）を超える。保存側の表記の統一は、モデル別名辞書の導入に近く、対象外に当たる
- 委任指示または停止条件: Issue の「保存時の整合検査と集計時の診断の配置」はエージェントに任せる事項。issue-to-pr の推奨案で決める

### D2. 「実行識別子が一致するのに、ほかの識別情報が違う」を不一致として未評価にする

- 選択した案: `_adoption_matches` で、完全一致する候補が無いとき、候補の中に、actor と `session_id`・`run_id`・`request_id` の 3 つが同じ値で、そのうち 1 つ以上が `unknown` でないものがあれば、`None`（未評価）を返し、不一致を診断に記録する。完全一致があれば今までどおり `True`、実行識別子が違う候補だけなら今までどおり `False`（別 session の 0）
- 検討した別案: (a) 実行識別子が一致すれば `model` の違いを無視して `True`（採用 1）にする。(b) `model` を正規化（空白とハイフンを同一視）して比べる。(c) `model` だけを比較から外し、`runtime`・`provenance` の完全一致で `True` にする
- 選択理由: `run_id` は runner の BatchResult の値で、同じバッチの複数レビュアーが共有しうる。`session_id` だけが観測された実行では、同じ session の中でモデルを切り替えられる。実行識別子の一致だけでは「同じモデルの同じ実行」と確かめられないため、(a)(c) は推定で採用を付けることになり、受け入れ条件「確認できない不一致は診断する」「推定で採用を付けない」に反する。(b) はファイル名用の置換と同じく別のモデルを一律に同一視し、受け入れ条件「ファイル名用の置換で別モデルを一律に同一視しない」に反する。未評価にすれば、黙って 0 にする誤りは無くなり、正しい値が分からないことが出力で分かる
- 対象: `model` の表記差に限らず、実行識別子が一致したうえでの `runtime`・`provenance` のほかの値（`agent_id`・`provider`・`effort`・`cli_version`・`role`・`skills`）の違いも同じに扱う（Issue の「表記差・識別情報の不一致」）
- 委任指示または停止条件: Issue の目標値「モデルが本当に異なる可能性を排除できなければ、不一致を診断して未評価または拒否」の範囲内の選択。推奨案で決める

### D3. 診断を `provenance.diagnostics` に出す

- 選択した案: `stats` の出力の `provenance` に `diagnostics`（配列）を足す。各要素は `{"kind": "identity_mismatch", "source": <指摘の参照>, "review_file": <レビューファイル>, "actor": <確認済みの一覧の識別情報>, "recorded": [<実行識別子が一致した seats の識別情報>...]}`。識別情報は `_actor_identity` の形（`model`・`runtime`・`provenance`）で、観測値をそのまま入れる。同じ要素は 1 回だけ出す。不一致が無ければ空配列
- 検討した別案: (a) 標準エラーに警告を出す。(b) 終了コード 65 で止める
- 選択理由: `stats` の利用者は JSON を読むので、出力の中にあれば機械的に見つけられ、終了コードを変えずに既存の呼び出しを壊さない。(b) は過去の記録が 1 件あるだけで集計全体が使えなくなる。既存のキーの値は変えず、`provenance` に新しいキーを足すだけにする（7.2 節の `runs` と同じ足し方）
- 委任指示または停止条件: 推奨案で決める

### D4. テストは S の代表 1 件と、正しく採用される対照

- 選択した案: `.agents/scripts/tests/test_review_findings.py` に、Issue の再現と同じ fixture（`document_v2`・`v2_adoption_round`）で、seats の `model` だけを変えた入力が `adopted: None` と `diagnostics` 1 件になり、同じ fixture で `model` が一致する入力が `adopted: 1`・`diagnostics: []` になることを確かめるテストを 1 件足す
- 検討した別案: 別 session・全 unknown・runtime の違いなども足す
- 選択理由: AGENTS.md「テストの採用基準」の S（誤っているがもっともらしい集計）に当たる。別 session（`test_provenance_stats_does_not_credit_a_later_round_from_another_session`）と全 unknown（`test_provenance_stats_leaves_adoption_unevaluated_when_identifiers_are_unobserved`）は既存のテストがあり、受け入れ条件どおり重複させない。runtime などの違いは同じ分岐の組み合わせなので D に当たり足さない
- 委任指示または停止条件: 推奨案で決める

### D5. 文書 `.agents/review-findings.md` 7.1 節に診断を書き足す

- 選択した案: 7.1 節の採否の段落に、「実行識別子が一致してほかの識別情報が違う場合は未評価にし、`diagnostics` に出す」ことと `diagnostics` の形を書き足す
- 選択理由: `stats` の出力の仕様を定めるのは 7.1 節であり、新しいキーをそこで説明しないと利用者が意味を読めない

## 振る舞いの表（実装後）

| 条件 | 終了コード | 先頭担当の adopted | diagnostics |
|---|---|---|---|
| model と実行識別情報が同じ | 0 | 1 | なし |
| 実行識別子は同じ、model だけ異なる | 0 | null | 1 件（`identity_mismatch`） |
| 別 session（実行識別子が異なる） | 0 | 0 | なし |
| 実行識別子がすべて unknown | 0 | null | なし |

v1 の判断記録、records の無い集計、別 PR の records、検出 HEAD の違う参照は、今までどおり（`_adoption_matches` の前で決まる）。

## 受け入れ基準

- 動作環境: Ubuntu 26.04 LTS の Dev Container、既存の uv・Python 環境。外部サービス・実モデルを呼ばない
- 実入力: Issue の再現手順の入力（`document_v2()` の `claude-opus-5-5`・`claude-code` を `SWE-2-Max`・`devin` に置き換え、seats[0] の `model` を `SWE-2 Max` にしたもの）。`model` は空白・ハイフンを含む文字列のまま扱う
- 防御範囲: 対象は、v2 records で Fix を決めたサイクルの seats に、actor と実行識別子が一致し識別情報の他の値が違う担当がある場合。対象外の反例として、識別情報が完全一致する場合（採用 1）、実行識別子が違う場合（0）、actor の実行識別子がすべて unknown の場合（null、診断なし）を変えない

## 検証

- `uv run --locked pytest .agents/scripts/tests/test_review_findings.py`
- Issue の再現手順を 4 条件で実行し、戻り値・診断・件数を確かめる
- README.md「テスト」のうち、変更に関係する `uv run pytest tests/skills .agents/skills .agents/scripts tools` と `bash scripts/check-layout.sh`
- `uv run ruff check` と `uv run ruff format --check` を変更したファイルに実行する

## レビュー記録

### 設計レビュー（1 回目）

- 実行: helper `review_design.py`（外部担当）。明示値 `--design-review pi_openai-codex_gpt6-sol_xhigh`、`fallback` なし。`actual_agent` は同じ、`identity` は `openai-codex` / `gpt-6.1-sol` / effort `xhigh`
- `review_id`: `9b92dea11c294eeda7c5ea3f0b49c650`、reviewed の Spec SHA-256: `2990347cad57b1b87b24e116bdf56bca627d57c988636454348ff7820d7e1cf9`、所要 約 136 秒
- 結果: `verdict: sound`、concerns 0 件、質問なし。`outside_changes` なし。`unprotected_changes` は他の作業の worktree 8 件（この run の対象外。記録だけ）
- 採否: 指摘が無いので採否は空
