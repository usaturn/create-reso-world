# Issue #427 実装計画: review_records の文字列欄で単一サロゲートを拒否する

- 状態: `draft`
- Spec: `docs/superpowers/specs/2026-11-15-issue-427-surrogate-text-design.md`
- 実行許可: Spec の「管理・実行許可」のとおり（issue-to-pr、`--merge`）。内容の承認ではない

## 実行方式と理由

`implement_task.py check` の `self` が false（`--implement pi_alibaba_qwen4-max_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task 1 を runner の担当に依頼する。変更は共通の検査関数と `_text()`・`_pattern()` からの呼び出しの数行、テスト 1 件で、同じ守りを実装とテストで扱うため 1 Task にまとめる。Task 2 の確認は司令塔が自分で行う。`--merge` が適用されるので、最終のブランチ全体レビューはループの 1 サイクル目で代える。

## 要件・原因・検証の対応

| Spec の条件 | Task | 観測・検証 |
| --- | --- | --- |
| 共通の関数を `_text()`・`_pattern()` から呼び、UTF-8 にエンコードできない値を拒否（D1・D2） | Task 1 | 追加テスト（両方の入口）、Task 2 の 4 欄 × 3 コマンド |
| 読取経路はコメント ID と欄を示す（D3） | Task 1 のテスト、Task 2 の `fold` | `comment 12345: <欄>: must be UTF-8 encodable`、終了コード 65 |
| 投稿経路はネットワーク操作の前に止まる（D3） | Task 2 | FakeGh＋実 subprocess の text パイプで書込み 0 件、読取の前に停止 |
| 正常値・文字としてのバックスラッシュ・既存の記録を維持 | Task 1 のテストの通る例、Task 2 の対照、既存テスト | 終了コード 0、出力に値が変わらず残る |
| `agent_id_for()` は変えない・重複行を許容し #426 の対照は 65（D4）、文書は変えない（D6） | Task 1 の担当ファイル | `git diff --stat` が 2 ファイルだけ |

## 受け入れ基準

- 動作環境: `/workspaces/reso-world/.worktrees/issue-427-surrogate-text`（隔離 worktree）、uv 管理の CPython、通常の UTF-8 出力環境。実 GitHub への投稿・実サービスへの書込みはしない
- 実入力:
  - Issue の再現手順のスクリプトで作る、JSON エスケープ `\ud800` を含む記録とコメント（`x\ud800y`）。異常にする欄は `decisions[0].reason`・`seats[0].model`・`stop_reason` の `external:` より後の 3 つと、`decisions[0].carry_over.issue` の URL の所有者の部分で、1 欄ずつ変える。#426 の対照として `planner.model` にも入れる
  - 対照: 正常な日本語・絵文字（例: `外部の障害で停止 🚧`）、文字としてのバックスラッシュを含む `x\\ud800y`（JSON では `"x\\\\ud800y"`）、既存の記録（既存のテストの記録）
- 防御範囲:
  - 対象: CLI の `validate`・`render`・`fold` と、`upsert_pr_comment.py` の `_checked_record()`（ネットワーク操作の前の検査）
  - 対象外の反例: 無信頼投稿者のコメント（従来どおり読み飛ばし、`ignored_comments` に入る）、GitHub に生のサロゲートを保存する経路、`upsert_pr_comment.py` の記録の無いコメントの経路（`compose_body()`）、実 API・実ネットワークでの確認、既存記録の一括移行、`agent_id_for()` の #426 の検査の変更
- 期待する結果:
  - 4 つの異常な欄のそれぞれで、`validate`・`render` は終了コード 65 と `<欄>: must be UTF-8 encodable` を stderr に出し、`fold` は終了コード 65 と `comment 12345: <欄>: must be UTF-8 encodable` を出す。未捕捉の `UnicodeEncodeError` のトレースバックを出さない
  - #426 の対照の `planner.model` は 3 コマンドとも終了コード 65 で、`planner.model: must be UTF-8 encodable` を 1 行以上含む（同じ行が 2 つ出てもよい）
  - 対照の入力は、従来どおり 3 コマンドとも終了コード 0 で、値を変えずに出力する
  - `upsert_pr_comment.py` は、異常な記録で書込みを 0 件のまま、PR・コメントの読取の前に `RecordError` 由来のエラーで止まる

## Task 1: 共通の UTF-8 エンコードの検査を `_text()`・`_pattern()` に足し、代表のテストを 1 件足す

- 担当ファイル:
  - `.agents/scripts/review_records.py`
  - `.agents/scripts/tests/test_review_records.py`
- 内容:
  1. `review_records.py`: `_is_control()` の近くに、文字列が UTF-8 にエンコードできるかを返す小さな関数（例: `_encodable(value: str) -> bool`。`value.encode("utf-8")` の `UnicodeEncodeError` で偽）を足す
     - `_text()`（175 行付近）: 値が文字列であることを確かめた直後に、エンコードできなければ `problems.add(where, "must be UTF-8 encodable")` を加える。空白・制御文字・HTML マーカーの検査とは独立に調べる（この問題を加えた後も、ほかの検査を続ける。空白だけの値の早期 return より前に置く）。docstring に、UTF-8 にエンコードできない文字列（単一サロゲート）を拒否することを 1 文足す
     - `_pattern()`（195 行付近）: 値が文字列でエンコードできなければ、正規表現に一致するかに関係なく `problems.add(where, "must be UTF-8 encodable")` を加えて戻る（既存の `must be <description>` は、文字列でない・一致しないときだけ従来どおり出す）
  2. `agent_id_for()` の `try: model.encode("utf-8") except UnicodeEncodeError` は変えない（Spec D4）
  3. `test_review_records.py`: 既存の `test_collect_records_reports_surrogate_model_with_comment_id`（741 行付近）の直後に 1 件足す。`round_v2()` などの既存の記録から `outcome` が `stopped` で `stop_reason` が `external: ...` の記録を作り（既存のヘルパーで作れる形を使う）、`stop_reason` を `"external: x\ud800y"` にしたコメント（ID 12345）を `collect_records()` に渡すと、問題に `comment 12345: stop_reason: must be UTF-8 encodable` が含まれることを確かめる。同じテストの中で、`stop_reason` を `"external: x\\ud800y"`（文字としてのバックスラッシュ）にした記録は `collect_records()` を通り、値が変わらず残ることも確かめる（拒否のテストに通る例を残す）。さらに `_pattern()` の入口として、`state` が `skip` で `carry_over.issue` を持つ判断（既存のテストの記録に無ければ、既存の `skip` の判断の作り方に合わせて作る）の `carry_over.issue` を `https://github.com/x\ud800y/repo/issues/1` にしたコメントを渡し、`decisions[0].carry_over.issue: must be UTF-8 encodable`（`comment <ID>: ` 付き）で拒否されることを確かめる。コメントに、守る損害（検証が通った記録が後段の出力で落ち、`fold` がコメント ID を示さない）を 1 行書く
- テストの要否: 1 件書く。検証が単一サロゲートを受理して成功を返すと、後段の失敗と検証結果が食い違い、`fold` はコメント ID を示さずに落ちる（AGENTS.md の S）。守りは共通の関数の 1 か所で、入口は `_text()` と `_pattern()` の 2 つなので、各入口の代表 1 欄だけを確かめ、欄 × caller の組み合わせは網羅しない（D）
- 検証（担当が実行する）: `uv run --locked pytest .agents/scripts/tests/test_review_records.py -q` が成功、変更した 2 ファイルに `uvx ruff check` と `uvx ruff format --check` を実行し、base で既にある指摘（`FLY002` 2 件）・format の差分のほかに新しい指摘が無いこと（追加・変更した行は `ruff format` の形にそろえる。既存の行は整形しない）、`git diff --stat` が上の 2 ファイルだけ。実装前に追加テストが失敗する（RED）ことも確かめる
- commit メッセージ: `fix(review-records): reject UTF-8 unencodable text fields (#427)`

## Task 2: 再現手順と投稿経路の確認（司令塔）

- 担当ファイル: なし（記録は SESSION の下）
- 内容:
  1. Issue の再現手順のスクリプトで、4 つの異常な欄（`carry_over.issue` は `state: skip` の判断を持つ記録で作る）と 2 つの対照（日本語・絵文字、文字としてのバックスラッシュ）の記録とコメントを作り、`validate`・`render`・`fold` を各 1 回実行して終了コード・stderr を記録する。#426 の対照の `planner.model` も同じく実行する
  2. 投稿経路: 一時的なスクリプト（SESSION の下）で、`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py` の FakeGh と同じ形の偽の runner を、実 subprocess の text パイプ（`subprocess.run(["cat"], input=..., text=True)` など）とつなぎ、異常な記録の `upsert()` が書込み 0 件・読取 0 件で止まることと、対照の記録が模擬投稿まで進むことを確かめる
  3. 既存テスト: `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`（README の「テスト」）、`bash scripts/check-layout.sh`。`bash .devcontainer/run-tests.bash`。lint は変更した 2 ファイルに `uvx ruff check`・`uvx ruff format --check` を実行し、base（`273ace19`）の同じ 2 ファイルの結果（`FLY002` 2 件と format の差分）と比べて新しい指摘・format の差分が増えないことを確かめる（型検査の入口は無いので行わない）
- テストの要否: 書かない（一時的な実行で確かめ、結果を PR に書く）

## 実行予算

- Issue 全体の能動時間の予算: 4 時間（Issue の見積もり上限）。phase の目安: Spec・設計レビュー・Spec レビュー 60 分、Plan 15 分、Task 1 の依頼と取り込み 45 分、Task 2 の確認 20 分、PR 作成 15 分、ループ 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）
- worker の期限: `implement` の役割の期限 90 分。無進捗の打ち切りは runner の既定に従う
- 再試行の上限: Task 1 の `retry`・`rejected` は合わせて 2 回まで（初回を含めて 3 回）。Task のレビュー指摘の修正の依頼は 2 回まで
- checkpoint: Task 1 の取り込み後（差分が 2 ファイルに限られるか、テストが通るか）、Task 2 の後（受け入れ基準の全項目）
- 縮小・切り出し・方法変更の候補: 投稿経路の模擬確認が既存の FakeGh で組めない場合は、`_checked_record()` を直接呼んで `CommentError` 系で止まり、runner の呼び出しが 0 件であることの確認に縮める

## contingency（代替策）

- Task 1 の担当が `failed` で止まったら、その Task で止まる（司令塔が引き取らない）
- 担当の変更が 2 ファイルの外に及んだら取り込まず（`rejected`）、範囲を明示して依頼し直す
- 最初の RED で、既存のヘルパーで `stop_reason` または `carry_over.issue` の記録が作れないと分かったら、同じ入口を通る別の欄（`_text()` なら `decisions[0].reason`、`_pattern()` で非 ASCII を受ける欄はほかに無いので `carry_over.issue` は記録を手で組み立てる）に替える。意味を保つ最小修正として ledger に残して続ける
- Task 2 で、ある経路が `validate_record()` を通らず拒否されないと分かったら、Spec D3 の前提が違うので止まる（検査の場所を変えるのは意味の変更）
- base が前進したら issue-to-pr の 2 章 6 の前進追随に従う
