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
- 利用者の続行指示（2026-11-15、設計レビューの `decide` が `next: stop`（`blocking: D1`）を返して止まった後）: 「現在止まっていることは許可されていません。必ず推奨案で進めることがスキルで規定されているはずです。ここで停止したことはバグとみなしてIssueを上げてください。」。これにより、設計レビューの blocking の指摘を採用・反映した状態で Spec レビュー以降へ進む。停止をバグとして起票する（別 Issue）
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

### D2. 検査の場所は共通の `_text()` と `_pattern()` にする

- 選択した案: UTF-8 にエンコードできるかを調べる小さな共通の関数を作り、`_text()` と `_pattern()` の両方から呼ぶ。問題は既存の `_Problems` に `<欄>: must be UTF-8 encodable` として加える（#426 の `planner.model: must be UTF-8 encodable` と同じ文言）。`_pattern()` では、正規表現に一致しても、エンコードできない値を拒否する
- 検討した別案: (a) `_text()` だけに足す。(b) 欄ごとに検査を足す。(c) `validate_record()` の最後に記録全体を `json.dumps(..., ensure_ascii=False).encode("utf-8")` で調べる。(d) `_ISSUE` の正規表現を ASCII に狭める
- 選択理由: 記録の自由記述・1 行の欄は、すべて `_text()`（`identity_problems()`・`_conditional_text()` を含む）を通る。それ以外の文字列欄は `_pattern()` か、ASCII の正規表現を直接使う検査（`DECISION_ID`・`FINDING_REF`。`_NAME` などは ASCII の文字クラスだけ）か、固定の選択肢（`_choice()`）で検査される。このうち `_pattern()` に渡す `_ISSUE` は URL の所有者・リポジトリの部分に `[^/\s]+` を使うので、単一サロゲートにも一致する（設計レビュー D1 の指摘。`decisions[].carry_over.issue`）。`_pattern()` にも検査を置けば、将来ほかの正規表現が非 ASCII を受け付けても同じ守りが働く。オブジェクトのキーは `_keys()` で既知の名前に限られる。(a) は `carry_over.issue` が漏れる。(b) は欄の追加で漏れる。(c) はどの欄が壊れているかを示せない。(d) は Issue の URL の形式の意味を変え、守りが正規表現ごとに散らばる
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（共通の検証境界）。設計レビュー（1 回目）の D1 を採用して `_pattern()` を加えた

### D3. 読取・描画・投稿の経路は、既存の検証の呼び出しで拒否を受け取る

- 選択した案: 新しい呼び出しを足さない。各経路はすでに `validate_record()` を通るので、`_text()`・`_pattern()` の拒否がそのまま次の形で現れる
  - `validate`・`render`: `RecordError` → `main()` が問題を stderr に出し、終了コード 65
  - `fold`: `collect_records()` → `extract_record()` → `validate_record()` の `RecordError` に `comment <ID>: ` が付く → 終了コード 65
  - `upsert_pr_comment.py`: `_checked_record()` の `validate_record()` が、ネットワーク操作の前に `RecordError` を出す
- 検討した別案: `main()` で `UnicodeEncodeError` を捕捉する
- 選択理由: 捕捉だけでは検証と後段の食い違いが残り、コメント ID・欄も示せない。拒否を検証に置けば、どの経路も外部操作や出力の前に止まる
- 委任指示または停止条件: Issue の受け入れ条件（読取経路でコメント ID と対象欄を示す、投稿側も外部操作の前に検査する）

### D4. `agent_id_for()` の #426 の検査は変えない

- 選択した案: `agent_id_for()` の `try: model.encode("utf-8") except UnicodeEncodeError` はそのまま残す
- 検討した別案: `_text()` の検査で到達しなくなるので削る
- 選択理由: `agent_id_for()` は `identity_problems()` を先に呼ぶので、`_text()` の変更後は同じ文言で先に拒否される。残しても挙動は変わらず、#426 の修正をやり直さない（Issue の対象外）。`planner.model` の問題が `_check_planner()` の `_text()` と `agent_id_for()` の 2 か所から同じ文言で出ることがあるが、制御文字など既存の問題でも同じ重なりがあり、拒否の結果（終了コード 65）は変わらない。重複した行は許容し、`_Problems` で同じ問題を 1 行にまとめる変更はしない（Spec レビュー S2）。#426 の対照の `planner.model` は、3 コマンドとも終了コード 65 で、stderr に `planner.model: must be UTF-8 encodable`（`fold` では `comment 12345: ` が付く）を 1 行以上含めばよい
- 委任指示または停止条件: 推奨案での委任。Issue の対象外「PR #426 のモデル名修正のやり直し」

### D5. テストは共通境界の代表 1 件にする

- 選択した案: `.agents/scripts/tests/test_review_records.py` に 1 件足す。`planner.model` 以外の欄（`stop_reason` の `external:` より後）に `x\ud800y` を入れたコメントを `collect_records()` に渡し、`comment 12345: stop_reason: must be UTF-8 encodable` で拒否されることと、同じ欄に文字としてのバックスラッシュを含む `x\\ud800y` を入れた記録が通ることを確かめる。同じテストの中で、`_pattern()` 経由の欄として `decisions[0].carry_over.issue`（URL の所有者の部分に `x\ud800y`）のコメントも `collect_records()` に渡し、`comment <ID>: decisions[0].carry_over.issue: must be UTF-8 encodable` で拒否されることを確かめる（Spec レビュー S1）
- 検討した別案: 欄 × caller（`validate`・`render`・`fold`・投稿）の組み合わせを網羅する
- 選択理由: 検証が不正な値を受理して成功を返すと、後段の失敗と検証結果が食い違い、`fold` はコメント ID を示さずに落ちる（AGENTS.md の S）。守りは共通の関数の 1 か所なので、テストは 1 件にする（D）。ただし共通の関数を呼ぶ入口は `_text()` と `_pattern()` の 2 つで、片方の呼び出しを外しても他方の確認では気付けないので、1 件の中で両方の入口を代表 1 欄ずつ確かめる（既存の `planner.model` のテストは `agent_id_for()` でも拒否されるため、`_text()` の守りの代わりにならない）。拒否のテストに通る例を残す。CLI の終了コード・投稿経路は、下の「受け入れ基準」の手動の確認で確かめ、テストにしない
- 委任指示または停止条件: Issue の受け入れ条件（テストは共通境界の代表 1 件）

### D6. 文書は変えない

- 選択した案: SKILL.md・references の文書は変えない
- 検討した別案: review-records の欄の規則を説明する文書に、UTF-8 の条件を足す
- 選択理由: 文書の欄の規則は、記録を書く担当が普通に従う内容で、単一サロゲートは正しい Unicode テキストではない。拒否の文言が欄名と理由を示すので、文書が無くても直し方が分かる
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（関連するドキュメントの更新の要否）

### レビューの記録

- 設計レビュー 1 回目: helper `review_design.py`（外部担当）。明示した担当 `pi_openai-codex_gpt6-sol_xhigh`（`fallback` なし）、`actual_agent` 同じ、`identity` は `openai-codex` / `gpt-6.1-sol`（effort `xhigh`）。`review_id` `877078374f1441ac9f532526d3230146`、reviewed の Spec SHA-256 `d3795769cb69c919484abb4f6882fdd5fab4d5516fef316116318a2e372ae785`（commit `c0d40a224d13ab6ac6a4e43c5816a20161bb8ef6`）、`elapsed_seconds` 114.6、`outside_changes` なし、`unprotected_changes` は他の作業の worktree 8 件（この run の checkout ではない）。verdict `concerns`、指摘 1 件
  - D1（blocking、`change`）: `_text()` だけでは `decisions[].carry_over.issue` の単一サロゲートを拒否できない → 採用。D2 を `_text()` と `_pattern()` の共通の関数に改め、受け入れ基準の実入力に `carry_over.issue` を加えた。作るもの（拒否）は変えない

- Spec レビュー 1 回目: helper `review_spec.py`（外部担当）。明示した担当 `pi_opencode-go_deepseek4-flash_max`（`fallback` なし）、`actual_agent` 同じ、`identity` は `opencode-go` / `deepseek-v4.1-flash`（effort `max`）。`review_id` `33c84fe343bb4dffbea67c16b15099f9`、reviewed の Spec SHA-256 `474ddb51431b1fbf7f38de1074d58b2986a58e0dd788e15678e41f63fbc4810b`（commit `66894d0d7b517ce2bb2b20eaf1ce2f15c6d58847`）、`elapsed_seconds` 1241.2、`outside_changes` なし、`unprotected_changes` は他の作業の worktree と親 checkout（この run の checkout ではない）。指摘 3 件
  - S1（important）: 代表テストが `_text()` 経由だけで、`_pattern()` 経由の `carry_over.issue` を守らない → 採用。D5 のテストで両方の入口を確かめる
  - S2（minor）: #426 の `planner.model` の対照が受け入れ基準から落ち、重複行の期待が無い → 採用。実入力に加え、D4 に期待（重複を許容）を書いた
  - S3（minor）: 型検査の入口が無い → 採用。検証を README の入口に限り、ruff は参考の実行にした

- Spec レビュー 2 回目（再レビュー）: 同じ担当・helper。`review_id` `f501f20cb45147feabba3d06fd0e8de3`、reviewed の Spec SHA-256 `925d5e0cbabbe09f4355556bee6dae044f4a287d97c9c04275bb2091b68d6b6c`（commit `cdc509be2c2433b56ca7a47033d0ad6b75ce8321`）、`identity` は `opencode-go` / `deepseek-v4.1-flash`（effort `max`）、`elapsed_seconds` 1481.1、`outside_changes` なし。指摘 3 件
  - S1（important）: 未知のキーにサロゲートがあると、問題文の stderr への出力で落ちる → 不採用。Python の `sys.stderr` の既定の `errors` は `backslashreplace` で、実際に `{"x\ud800y": 1}` を `validate` に渡すと `x\ud800y: unknown key` を出して終了コード 65、トレースバックは無かった（base の worktree で確認）。D2 の「キーは既知の名前に限られる」は値の検査の範囲の説明で、キーの拒否は既存の `_keys()` で働く
  - S2（minor）: README の `run-tests.bash` が検証から落ちている → 採用
  - S3（minor）: lint の成否が完了条件になっていない → 採用（形を変えて）。base で既に失敗するので、新しい指摘が増えないことを必須にした

## 変更するもの

- `.agents/scripts/review_records.py`: UTF-8 エンコードの検査の共通の関数を足し、`_text()` と `_pattern()` から呼ぶ。`_text()` では文字列であることを確かめた後、空白・制御文字の検査とは独立に調べる（ほかの問題があっても、この問題を落とさない）
- `.agents/scripts/tests/test_review_records.py`: D5 の 1 件

## 受け入れ基準

- 動作環境: `/workspaces/reso-world/.worktrees/issue-427-surrogate-text`（隔離 worktree）、uv 管理の CPython、通常の UTF-8 出力環境。実 GitHub への投稿・実サービスへの書込みはしない
- 実入力:
  - Issue の再現手順のスクリプトで作る、JSON エスケープ `\ud800` を含む記録とコメント。異常にする欄は `decisions[0].reason`・`seats[0].model`・`stop_reason` の `external:` より後の 3 つ（Issue の再現）と、`decisions[0].carry_over.issue` の URL の所有者の部分（設計レビュー D1）で、1 欄ずつ変える。#426 の対照として `planner.model` にも同じ値を入れ、Issue の評価方法どおり終了コードと stderr を比べる（Spec レビュー S2。期待は D4）
  - 対照: 正常な日本語・絵文字（例: `外部の障害で停止 🚧`）、文字としてのバックスラッシュを含む `x\\ud800y`（JSON では `"x\\\\ud800y"`）、既存の記録（既存のテストの記録）
- 防御範囲:
  - 対象: CLI の `validate`・`render`・`fold` と、`upsert_pr_comment.py` の `_checked_record()`（ネットワーク操作の前の検査）
  - 対象外の反例: 無信頼投稿者のコメント（従来どおり読み飛ばし、`ignored_comments` に入る）、GitHub に生のサロゲートを保存する経路、実 API・実ネットワークでの確認、既存記録の一括移行
- 振る舞い:
  - 4 つの異常な欄のそれぞれで、`validate`・`render` は終了コード 65 と `<欄>: must be UTF-8 encodable` を stderr に出し、`fold` は終了コード 65 と `comment 12345: <欄>: must be UTF-8 encodable` を出す。未捕捉の `UnicodeEncodeError` のトレースバックを出さない
  - 対照の入力は、従来どおり 3 コマンドとも終了コード 0 で、値を変えずに出力する
  - `upsert_pr_comment.py` は、異常な記録を既存の FakeGh と実 subprocess の text パイプでつないだ模擬で、書込みを 0 件のまま `RecordError` 由来のエラー（`CommentError` 系）で止まる。PR・コメントの読取の前に止まる
- 検証:
  - 上の振る舞いを、Issue の再現手順の 3 コマンドで欄ごとに 1 回ずつ確かめる（結果は PR 本文に書く）
  - 投稿経路は、一時的なスクリプト（コミットしない）で 1 回確かめる
  - `uv run --locked pytest .agents/scripts/tests/test_review_records.py` と、関係するテスト（`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`）、README の「テスト」の `uv run pytest tests/skills .agents/skills .agents/scripts tools` と `bash scripts/check-layout.sh` が通る。README の `bash .devcontainer/run-tests.bash` も通す（`worlds/<name>` のテストは追跡対象外なので対象外。Spec レビュー 2 回目の S2）。リポジトリには lint・型検査の入口が無い（`pyproject.toml` の dev 依存は pytest と pyyaml だけ）。lint は `uvx ruff check` と `uvx ruff format --check` を変更した 2 ファイルに実行し、base（`273ace19`）の同じ 2 ファイルの結果と比べて、新しい指摘・format の差分が増えないことを必須にする。base の時点で既存の指摘（`FLY002` 2 件）と format の差分があり、終了コード 0 は変更の範囲外の修正を要するので求めない。型検査は行わない（Spec レビュー S3、2 回目の S3）

## 対象外

- 実 GitHub への POST/PATCH、実 API・実ネットワークでの挙動確認
- 無信頼投稿者のコメントの扱い・信頼境界の変更
- 欄 × caller の組み合わせ網羅のテスト、文言・網羅性だけの改善
- 過去の記録の一括移行・全走査
- PR #426 のモデル名修正のやり直し
- `review_records.py` 以外のスクリプトの文字列検査。`upsert_pr_comment.py` の記録の無いコメントの経路（`compose_body()`。`--model-name` と Markdown のファイルだけを使い、`review_records` の検証を通らない）も含む
