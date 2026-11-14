# Issue #440 実装計画: 採用照合の識別情報の不一致を未評価と診断にする

- 状態: `draft`
- Spec: `docs/superpowers/specs/2026-11-15-issue-440-adoption-identity-mismatch-design.md`
- 実行許可: Spec の「管理・実行許可」のとおり（issue-to-pr、`--merge`）。内容の承認ではない

## 実行方式と理由

`implement_task.py check` の `self` が false（`--implement pi_alibaba_qwen4-max_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task 1 を runner の担当に依頼する。コード・テスト・文書の変更は同じ判定の規則を共有し、分けると表現と挙動がずれるため 1 Task にまとめる。Task 2 の確認は司令塔が自分で行う（統合担当）。`--merge` が適用されるので、最終のブランチ全体レビューはループの 1 サイクル目で代える。

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04 LTS）の worktree で、既存の uv・Python 環境から実行する。GitHub・認証・実モデルには接続しない
- 実入力: Issue の再現手順の入力。`document_v2()` の `claude-opus-5-5`・`claude-code` を `SWE-2-Max`・`devin` に置き換え、`v2_adoption_round()` の seats[0] の `model` を `SWE-2 Max`（空白）にしたもの。対照は同じ入力で seats[0] の `model` を `SWE-2-Max` のままにしたもの。`model` の文字列は正規化せず、観測値のまま出力に現れる
- 期待する結果:
  - 対照（識別情報が完全一致）: 2 人の担当の `adopted` が `[1, 1]`、`provenance.diagnostics` が `[]`
  - 表記差（実行識別子が一致し `model` だけ異なる）: 先頭担当の `adopted` が `null`、もう一方は `1` のまま。`provenance.diagnostics` が 1 件で、`kind: "identity_mismatch"`、`source`、`review_file`、`actor`（`model: "SWE-2-Max"`）、`recorded`（`model: "SWE-2 Max"` を含む）を持つ
  - 片側だけ unknown（`session_id` は一致、seats[0] の `run_id`・`request_id` が `unknown`、`model` だけ異なる）: 表記差と同じく先頭担当が `null`、診断 1 件。`recorded` の `model` と `unknown` の値が観測値のまま
  - 観測値が重ならない（actor は `run_id` だけ、seats[0] は `session_id` だけを観測、`model` だけ異なる）: 先頭担当が `null`、診断 1 件
  - 複数 source（先頭担当（同じレビューファイル）に採用された source が `…#H-1@<head>` と `…#H-2@<head>` の 2 件で、どちらも seats[0] の `model` だけが違う）: 先頭担当が `null`、診断が source ごとに 2 件
  - 別 session: `adopted` が 0、`diagnostics` が `[]`（既存テストのとおり）
  - actor の実行識別子がすべて unknown: `adopted` が `null`、`diagnostics` が `[]`（既存テストのとおり）
  - 候補（seats）の実行識別子がすべて unknown（inputs は観測済み、seats[0] だけ全 unknown、`model` も異なる）: 先頭担当の `adopted` が `null`、`diagnostics` が `[]`
  - どの条件も `stats` の CLI の終了コードは 0
- 防御範囲: 対象は、v2 records で Fix を決めたサイクルの seats に、actor と `session_id`・`run_id`・`request_id` が矛盾せず（どれも、両方で観測されて食い違っていない。部分的な unknown・観測値が重ならない場合を含む）、`_actor_identity` の他の値（`model`・`runtime`・`provenance` の他のキー）が違う担当がある場合。対象外（変えない）: 識別情報の完全一致（採用 1）、両方で観測された実行識別子が 1 つ以上食い違う候補しか無い場合（0）、actor または候補の実行識別子がすべて unknown（null、診断なし）、v1 records・records なし・別 PR・検出 HEAD の違う参照の扱い、`documents`・`reviewers`・`severity_drift`・`runs` の値、保存時の検査（`review_records.py`）、過去の記録、モデル名の正規化・別名辞書

## Task 1: 採用照合の不一致を未評価にし、診断を出す

- 担当ファイル:
  - `.agents/scripts/review_findings.py`
  - `.agents/scripts/tests/test_review_findings.py`
  - `.agents/review-findings.md`
- 内容:
  1. `_adoption_matches` を、照合の結果と、不一致の診断に使う情報を呼び出し元に返せる形にする（戻り値の型を変えるか、診断を受け取る引数を足すかは担当が決める）。判定の順序は次のとおり
     - 今の早期の `True`（v1）・`None`（provenance なし、actor の実行識別子がすべて unknown、候補なし）は変えない
     - 識別情報の完全一致の候補があれば `True`
     - 完全一致が無く、actor と実行識別子が「矛盾しない」候補があれば、`None` にし、その候補（複数あればすべて）を診断に渡す。「矛盾しない」は、`session_id`・`run_id`・`request_id` のどれも、両方で観測されて（`unknown` でなく）値が食い違っていないこと（それぞれ同じ値か、どちらかが `unknown`。両方の観測値が重ならない場合も含む）。候補の実行識別子がすべて `unknown` ならここに当たらない
     - それ以外は今のまま（実行識別子がすべて unknown の候補があれば `None`、無ければ `False`）。actor 側の全 unknown の `None` を完全一致の判定より先に置く今の順序も変えない
  2. `_provenance_stats` が、照合で不一致になったときに `entry["adopted"] = None` にし、`{"kind": "identity_mismatch", "source": <reference_key(source)>, "review_file": <レビューファイル名>, "actor": <_actor_identity(original, "find")>, "recorded": [<実行識別子が矛盾しなかった候補の _actor_identity>...]}` を診断に足す。診断は `adopted` の計算と独立に集める。records がその文書に適用される（records があり `records.pr` が文書の `pr` と一致する）とき、採用された各 source（`adopted_refs` にある参照）を照合し、先の source の不一致で `adopted` が既に `null` になっていても後の source の照合を省かない（`adopted` の値と数え方は変えない）。同じ内容の要素は 1 回だけにし、出力の順序は決まった順（例: JSON 文字列の昇順）にする。戻り値の辞書に `"diagnostics"` を足す（不一致が無ければ `[]`）。`model` などの値は観測値のまま入れ、書き換えない
  3. テスト: `test_review_findings.py` に、受け入れ基準の「対照」「表記差」「片側だけ unknown」「候補だけ全 unknown」の 4 つの入力を同じ fixture から作り、`stats` の結果の 2 人の担当の `adopted` と `provenance.diagnostics` を確かめるテストを 1 件足す（`pytest.mark.parametrize` でまとめる）。期待値: 対照は `[1, 1]` と `[]`。表記差・片側だけ unknown は先頭が `None`、もう一方が `1`、診断 1 件（`kind`・`source`・`review_file`・`actor` と `recorded` の `model`、片側だけ unknown では `recorded` の `run_id`・`request_id` の `unknown` も観測値のまま）。候補だけ全 unknown は先頭が `None`、もう一方が `1`、`[]`。runtime 差・観測値が重ならない場合・複数 source のテストは足さない（Spec D4。Task 2 で確かめる）。別 session・actor 側の全 unknown のテストは既にあるので足さない。既存テストの期待値は変えない（`diagnostics` キーの追加で壊れる箇所があれば、そこだけ直す）
  4. 文書: `.agents/review-findings.md` 7.1 節の採否の段落（「採否は records.pr が一致する資料だけに適用し、…」）に、実行識別子が矛盾しない（それぞれ同じ値か片方が unknown。部分的な unknown を含む）のに他の識別情報が違う場合は採用を推定せず `adopted` を null にし、`provenance.diagnostics` に出すことと、要素の形を書き足す。日本語表現は AGENTS.md の「日本語表現」に従う
- テストの要否: 書く。表記差で採用を黙って 0 にする誤りは、終了コード 0 のままもっともらしい集計になるので、AGENTS.md「テストの採用基準」の S に当たる。代表 1 件と、正しく採用される対照を同じテストに置く
- 検証（担当が実行する）: `uv run pytest .agents/scripts/tests/test_review_findings.py -q` が成功、`uv run --locked python -m py_compile .agents/scripts/review_findings.py .agents/scripts/tests/test_review_findings.py` が成功（ruff はリポジトリの依存でも README の検査でもなく、base の既存コードでも失敗するため使わない。実行中に判明して差し替えた）、`git diff --stat` が上の 3 ファイルだけ
- commit メッセージ: `fix: report adoption identity mismatches instead of counting zero (#440)`

## Task 2: 4 条件の確認と回帰（司令塔）

- 担当ファイル: なし（記録は SESSION の下）
- 内容: Issue の再現スクリプトを拡張した一時スクリプトで、対照・表記差・片側だけ unknown・観測値が重ならない・別 session・actor 全 unknown・候補全 unknown・複数 source の各条件をオフラインで 1 回ずつ実行し、先頭担当の `adopted` と `diagnostics` を受け入れ基準と照合する。表記差の入力を公開 CLI `stats --records` にも与え、終了コード 0 と同じ結果を確かめる
- 回帰: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash scripts/check-layout.sh`
- テストの要否: 書かない（一時的な実行で確かめ、結果を PR に書く）

## 実行予算

- Issue 全体の能動時間の予算: 4 時間（Issue の見積もり上限 2 時間に、設計・Spec レビューとループを加えた）。phase の目安: Spec・設計レビュー・Spec レビュー 60 分、Plan 15 分、Task 1 の依頼と取り込み 45 分、Task 2 の確認 20 分、PR 作成 15 分、ループ 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）
- worker の期限: `implement` の役割の期限 90 分。無進捗の打ち切りは runner の既定に従う
- 再試行の上限: Task 1 の `retry`・`rejected` は合わせて 2 回まで（初回を含めて 3 回）。Task のレビュー指摘の修正の依頼は 2 回まで
- checkpoint: Task 1 の取り込み後（差分が 3 ファイルに限られるか）、Task 2 の後（受け入れ基準の全項目）
- 縮小・切り出し・方法変更の候補: 文書の書き足しを最小（1 文と形）にする

## contingency（代替策）

- Task 1 の担当が `failed` で止まったら、その Task で止まる（司令塔が引き取らない）
- 担当の変更が 3 ファイルの外に及んだら取り込まず（`rejected`）、範囲を明示して依頼し直す
- 最初の RED で fixture の形が想定と違う（例: seats の `provenance` が `inputs` と別の値を持つ）と分かったら、受け入れ基準の意味（表記差は未評価と診断、完全一致は採用 1）を保つ最小修正を ledger に残して続ける。意味が変わる場合は止まる
- base が前進したら issue-to-pr の 2 章 6 の前進追随に従う
