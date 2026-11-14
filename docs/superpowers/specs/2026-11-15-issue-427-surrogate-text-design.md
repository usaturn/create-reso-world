# Issue #427: review_records の文字列欄で単一サロゲートを拒否する

## 管理・実行許可

- 状態: `draft`
- 対象: https://github.com/usaturn/create-reso-world/issues/427
- 利用者の指示（2026-11-15、`/issue-to-pr` の引数）:

  ```text
  #427 --merge
  --design-review pi_openai-codex_gpt6-sol_xhigh
  --spec-review pi_opencode-go_deepseek4-flash_max
  --implement pi_alibaba_qwen4-max_max
  --assign implement=pi_alibaba_qwen4-max_max
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh
  ```

- 許可された範囲: issue-to-pr の委任により、通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで続ける。`--merge` により、PR 作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと関連 Issue の更新を行う。これは実行許可の記録であり、内容の承認（`approved`）ではない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-427-surrogate-text`（branch `fix/issue-427-surrogate-text`、base `origin/main` `273ace19215430fa05042a512d63dc19e4e3a058`）。Spec・Plan はコードと同じ worktree・PR に入れる（`DOCS_SEPARATE=false`）

## 背景

`.agents/scripts/review_records.py` の文字列欄の検査 `_text()` は、型・空白・制御文字・HTML コメントのマーカーを調べるが、UTF-8 にエンコードできない単一サロゲート（JSON の `\ud800` を復号した値）を調べない。#426 で `planner.model` だけは `agent_id_for()` の中で拒否するようにしたが、ほかの欄（`decisions[].reason`・`seats[].model`・`stop_reason` など）は検証を通る。

検証を通った記録は、後段で UTF-8 に書き出すときに未捕捉の `UnicodeEncodeError` で落ちる。

| 経路 | 現状 |
| --- | --- |
| CLI `validate` | 終了コード 0（受理） |
| CLI `render`（`sys.stdout.write`） | `UnicodeEncodeError`、終了コード 1 |
| CLI `fold`（`sys.stdout.write`） | `UnicodeEncodeError`、終了コード 1、コメント ID の診断なし |
| `upsert_pr_comment.py`（`_checked_record()` を通った後、`GhRunner` の `subprocess.run(input=..., text=True)`） | PR・login・コメントの読取の後に `UnicodeEncodeError`、書込は 0 件 |

検証の結果と後段の処理が食い違うので、「検証を通ったから出力できる」という前提が崩れている。

## 決定記録

### D1. 単一サロゲートは拒否する（エスケープして保持しない）

- 選択した案: UTF-8 にエンコードできない文字列を、記録の検証で不正な値として拒否する
- 検討した別案: (a) 出力・投稿のすべてで `ensure_ascii=True` などのエスケープを使い、値を保持する。(b) `errors="replace"` などで置換する
- 選択理由: 単一サロゲートは正しい Unicode テキストではなく、通常のモデル識別子や日本語の文章から生じない（Issue の「問題と影響」）。(a) は描画・`fold` の出力・投稿本文・`extract_record()` の往復確認・GitHub の保存のすべてで同じ変換をそろえる必要があり、1 か所の漏れで同じ不具合が再発する。また GitHub のコメント本文は人が読むので、`ensure_ascii=True` にすると日本語が読めなくなる。#426 の `planner.model` も拒否で直しており、それと扱いがそろう。(b) は値を黙って変えるので、受け入れ条件（黙って置換・欠落させない）に反する
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（拒否かエスケープかの仕様選択）による委任

### D2. 検査の場所は共通の `_text()` にする

- 選択した案: `_text()` に「UTF-8 にエンコードできること」の検査を足し、問題は既存の `_Problems` に `<欄>: must be UTF-8 encodable` として加える（#426 の `planner.model: must be UTF-8 encodable` と同じ文言）
- 検討した別案: (a) 欄ごとに検査を足す。(b) `validate_record()` の最後に記録全体を `json.dumps(..., ensure_ascii=False).encode("utf-8")` で調べる
- 選択理由: 記録の自由記述・1 行の欄は、すべて `_text()`（`identity_problems()`・`_conditional_text()` を含む）を通る。それ以外の文字列欄は、ASCII の正規表現（`_pattern()`・`DECISION_ID`・`FINDING_REF`・`_UTC`）か固定の選択肢（`_choice()`）で検査されるので、単一サロゲートを含む値はすでに拒否される。オブジェクトのキーは `_keys()` で既知の名前に限られる。(a) は欄の追加で漏れる。(b) はどの欄が壊れているかを示せない
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（共通の検証境界）

### D3. 読取・描画・投稿の経路は、既存の検証の呼び出しで拒否を受け取る

- 選択した案: 新しい呼び出しを足さない。各経路はすでに `validate_record()` を通るので、`_text()` の拒否がそのまま次の形で現れる
  - `validate`・`render`: `RecordError` → `main()` が問題を stderr に出し、終了コード 65
  - `fold`: `collect_records()` → `extract_record()` → `validate_record()` の `RecordError` に `comment <ID>: ` が付く → 終了コード 65
  - `upsert_pr_comment.py`: `_checked_record()` の `validate_record()` が、ネットワーク操作の前に `RecordError` を出す
- 検討した別案: `main()` で `UnicodeEncodeError` を捕捉する
- 選択理由: 捕捉だけでは検証と後段の食い違いが残り、コメント ID・欄も示せない。拒否を検証に置けば、どの経路も外部操作や出力の前に止まる
- 委任指示または停止条件: Issue の受け入れ条件（読取経路でコメント ID と対象欄を示す、投稿側も外部操作の前に検査する）

### D4. `agent_id_for()` の #426 の検査は変えない

- 選択した案: `agent_id_for()` の `try: model.encode("utf-8") except UnicodeEncodeError` はそのまま残す
- 検討した別案: `_text()` の検査で到達しなくなるので削る
- 選択理由: `agent_id_for()` は `identity_problems()` を先に呼ぶので、`_text()` の変更後は同じ文言で先に拒否される。残しても挙動は変わらず、#426 の修正をやり直さない（Issue の対象外）。`planner.model` の問題が `_check_planner()` の `_text()` と `agent_id_for()` の 2 か所から同じ文言で出ることがあるが、制御文字など既存の問題でも同じ重なりがあり、拒否の結果（終了コード 65）は変わらない
- 委任指示または停止条件: 推奨案での委任。Issue の対象外「PR #426 のモデル名修正のやり直し」

### D5. テストは共通境界の代表 1 件にする

- 選択した案: `.agents/scripts/tests/test_review_records.py` に 1 件足す。`planner.model` 以外の欄（`stop_reason` の `external:` より後）に `x\ud800y` を入れたコメントを `collect_records()` に渡し、`comment 12345: stop_reason: must be UTF-8 encodable` で拒否されることと、同じ欄に文字としてのバックスラッシュを含む `x\\ud800y` を入れた記録が通ることを確かめる
- 検討した別案: 欄 × caller（`validate`・`render`・`fold`・投稿）の組み合わせを網羅する
- 選択理由: 検証が不正な値を受理して成功を返すと、後段の失敗と検証結果が食い違い、`fold` はコメント ID を示さずに落ちる（AGENTS.md の S）。守りは `_text()` の 1 か所なので、代表 1 件にする（D）。拒否のテストに通る例を残す。CLI の終了コード・投稿経路は、下の「受け入れ基準」の手動の確認で確かめ、テストにしない
- 委任指示または停止条件: Issue の受け入れ条件（テストは共通境界の代表 1 件）

### D6. 文書は変えない

- 選択した案: SKILL.md・references の文書は変えない
- 検討した別案: review-records の欄の規則を説明する文書に、UTF-8 の条件を足す
- 選択理由: 文書の欄の規則は、記録を書く担当が普通に従う内容で、単一サロゲートは正しい Unicode テキストではない。拒否の文言が欄名と理由を示すので、文書が無くても直し方が分かる
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（関連するドキュメントの更新の要否）

## 変更するもの

- `.agents/scripts/review_records.py`: `_text()` に UTF-8 エンコードの検査を足す。文字列であることを確かめた後、空白・制御文字の検査とは独立に調べる（ほかの問題があっても、この問題を落とさない）
- `.agents/scripts/tests/test_review_records.py`: D5 の 1 件

## 受け入れ基準

- 動作環境: `/workspaces/reso-world/.worktrees/issue-427-surrogate-text`（隔離 worktree）、uv 管理の CPython、通常の UTF-8 出力環境。実 GitHub への投稿・実サービスへの書込みはしない
- 実入力:
  - Issue の再現手順のスクリプトで作る、JSON エスケープ `\ud800` を含む記録とコメント。異常にする欄は `decisions[0].reason`・`seats[0].model`・`stop_reason` の `external:` より後の 3 つで、1 欄ずつ変える
  - 対照: 正常な日本語・絵文字（例: `外部の障害で停止 🚧`）、文字としてのバックスラッシュを含む `x\\ud800y`（JSON では `"x\\\\ud800y"`）、既存の記録（既存のテストの記録）
- 防御範囲:
  - 対象: CLI の `validate`・`render`・`fold` と、`upsert_pr_comment.py` の `_checked_record()`（ネットワーク操作の前の検査）
  - 対象外の反例: 無信頼投稿者のコメント（従来どおり読み飛ばし、`ignored_comments` に入る）、GitHub に生のサロゲートを保存する経路、実 API・実ネットワークでの確認、既存記録の一括移行
- 振る舞い:
  - 3 つの異常な欄のそれぞれで、`validate`・`render` は終了コード 65 と `<欄>: must be UTF-8 encodable` を stderr に出し、`fold` は終了コード 65 と `comment 12345: <欄>: must be UTF-8 encodable` を出す。未捕捉の `UnicodeEncodeError` のトレースバックを出さない
  - 対照の入力は、従来どおり 3 コマンドとも終了コード 0 で、値を変えずに出力する
  - `upsert_pr_comment.py` は、異常な記録を既存の FakeGh と実 subprocess の text パイプでつないだ模擬で、書込みを 0 件のまま `RecordError` 由来のエラー（`CommentError` 系）で止まる。PR・コメントの読取の前に止まる
- 検証:
  - 上の振る舞いを、Issue の再現手順の 3 コマンドで欄ごとに 1 回ずつ確かめる（結果は PR 本文に書く）
  - 投稿経路は、一時的なスクリプト（コミットしない）で 1 回確かめる
  - `uv run --locked pytest .agents/scripts/tests/test_review_records.py` と、関係するテスト（`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`）・`ruff check`・`ruff format --check`・型検査（リポジトリの既存の入口）が通る

## 対象外

- 実 GitHub への POST/PATCH、実 API・実ネットワークでの挙動確認
- 無信頼投稿者のコメントの扱い・信頼境界の変更
- 欄 × caller の組み合わせ網羅のテスト、文言・網羅性だけの改善
- 過去の記録の一括移行・全走査
- PR #426 のモデル名修正のやり直し
- `review_records.py` 以外のスクリプトの文字列検査。`upsert_pr_comment.py` の記録の無いコメントの経路（`compose_body()`。`--model-name` と Markdown のファイルだけを使い、`review_records` の検証を通らない）も含む
