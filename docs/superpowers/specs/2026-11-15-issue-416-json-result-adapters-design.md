# Issue #416: json_result を claude_code・codex・cursor に展開し、request_prompt を接続する

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/416
- 実行許可: 利用者が issue-to-pr を明示して起動した（2026-11-15。引数は `#416 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review devin_swe2_max --implement devin_swe2_max --assign implement=devin_swe2_max --assign inspect=devin_swe2_max,claude-code_ollama_opus_max,pi_openai-codex_gpt6-sol_xhigh`）。推奨案で設計を決め、実装・検証・commit・push・PR 作成と、`--merge` の PR 修正ループ（マージは `finalize.py` だけ）まで進める許可である。内容の承認（`approved`）ではない
- 先行依存: #425 は PR #461（merge commit `9800cf36445dd4f1ec67df6e911060df39d8622e`）でマージ済み。#425 の Issue は open のままだが、#416 へのコメント（2026-11-15T07:19Z）で例示境界の仕様が確定している
- 作業 base: `usaturn/create-reso-world` `main` `9800cf36445dd4f1ec67df6e911060df39d8622e`

## 意図

結果が JSON の役割（implement・self-review・fix-check・inspect・spec-review・design-review）に claude_code・codex・cursor を割り当てたとき、

- 完了した作業が「文章 → 裸の JSON」の形のせいで `response_failed` になって捨てられないようにする（claude_code）
- 訂正形（古い JSON → 文章 → 新しい JSON）や設定例の object を、誤って成功の payload にしないようにする（claude_code・codex・cursor）
- adapter ごとに手で足している JSON 指示を、共有の `request_prompt` に揃える（pi・claude_code・codex・cursor）

pi の抽出は PR #423、例示境界は PR #461 で済んでおり、この Issue は残りの接続だけを行う。

## 目標・非目標

目標:

- claude_code・codex・cursor の JSON 抽出を `json_result.json_object`（最後の有効な object、#425 の例示境界）にする
- pi・claude_code・codex・cursor の JSON 指示を `request_prompt` 経由にする
- runtime 文書（`tools/agent_runner/runtimes/{claude-code,codex,cursor}.rst`）の「応答と失敗の判定」を新しい抽出仕様に合わせ、pi.rst を確認する

非目標（Issue の対象外をそのまま引き継ぐ）:

- `json_result.py` のスキャナの書き直し（docstring の追記は除く）
- 例示境界の再決定（#425 で確定済み）
- devin のプロンプト・抽出・テストの変更
- 各 adapter の完了条件・隔離・認証・承認の診断の変更
- 実 CLI・有料モデル・実 API での再現
- 上流 usaturn/agent-workspace への問い合わせ・変更（#457 で扱う）
- #349 のボードの変更

失敗とみなすもの（技術的に動いても）: 壊れた回答・設定例の object・古い object を成功にする、診断より回答を優先するようになる、devin の依頼文が変わる。

## 現状

| adapter | 抽出 | JSON 指示 |
|---|---|---|
| pi | `json_object`（PR #423） | `prompt_lines` の後に `"Return your final answer as a JSON object."` |
| claude_code | 独自 `_json_object`: 全体 JSON か `json` fence 内の **先頭** の閉じた object。裸の JSON は不可 | `prompt_lines` の後に pi と同じ文 |
| codex | 独自 `_json_object`: 全体 JSON か、最初の `{`/`[` から 1 個だけ decode（**先頭**、空 object は拒否、後ろに `{`/`[` があれば拒否）。`turn.completed` での pending error の解除判定にも使う | `request.prompt` の直後に `JSON_REQUEST` と同じ文、その後に `prompt_lines` |
| cursor | 独自 `_json_object`: 全体 JSON か、最初の `{` から 1 個だけ decode（**先頭**） | codex と同じ並び |
| devin | `json_object` | 独自の文（変更しない） |

runner は JSON の役割の payload を空でない dict に限る（`tools/agent_runner/runner.py` の `invalid_result`）。上流 usaturn/agent-workspace（`2625352607d658f9682d3c67afe0b002971af8e1`）は、pi・claude_code が `json_object`、codex・cursor が `first_json_object` で、4 つとも `request_prompt` を最初の部分に使う。

## 方式の比較

1. **採用: 4 adapter とも共有ヘルパーを直接呼ぶ。** claude_code・codex・cursor の独自 `_json_object` を消して `json_object` を import し、JSON 指示を `request_prompt(context.request.prompt, shape)` にする。上流と同じ構成で、抽出規則は `json_result.py` の 1 か所だけになる。
2. 不採用: 各 adapter の `_json_object` を残し、中で `json_object` を呼ぶ薄い wrapper にする。呼び出し箇所の差分は小さいが、規則の置き場所が 2 層になり、上流とも pi とも構成がずれる。
3. 不採用: codex・cursor だけ `first_json_object` にする（上流と同じ）。2026-11-15 の利用者の決定（最後の有効な object に統一）に反する。

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」の順に書く。

- **D1 抽出の選択ポリシー**: claude_code・codex・cursor とも `json_object`（最後の有効な object）。/ 別案: codex・cursor は上流どおり `first_json_object`。/ 理由: 訂正形で古い object を成功にする危険を除くため。Issue の「決定済みの事項」2026-11-15 の利用者の決定。上流が先頭選択を維持する意図は #457 で確認する。/ 利用者の決定。
- **D2 例示境界**: #425 の境界（PR #461 の `json_object` の docstring と #416 へのコメント）をそのまま使い、adapter 側で追加の判定をしない。/ 別案: なし。/ 理由: Issue の決定済み事項。/ 利用者の決定。
- **D3 空 object `{}`**: codex の「空 object を拒否する」独自規則は残さず、`json_object` の結果（空 object も返る）に従う。最終的には runner が空の dict を `invalid_result` にするので、成功にはならない。/ 別案: codex・cursor で空 object を飛ばす（上流の `first_json_object` と同じ）。/ 理由: 最後の object が空なら、それより前の object へ戻るのは「先行結果への巻き戻り」で、この Issue が防ぐ形そのものである。pi・devin と同じ扱いになる。/ 委任（エージェントの判断）。
- **D4 codex の pending error の解除判定**: `turn.completed` で、直前の message が JSON の役割で有効かを見る判定も `json_object` に替え、さらに抽出した dict が空でないことを要求する（設計レビュー D1 の採用）。/ 別案: 解除判定だけ旧規則を残す、または `json_object` の結果が None でないことだけを見る。/ 理由: 抽出規則は最終 payload と同じ関数にして重複を避ける。一方、空 object は runner が `invalid_result` にする成功にできない応答なので、それでエラーを解除すると、認証エラー → `{}` → `turn.completed` が `awaiting_authentication` から `invalid_result` に変わり、診断を変えない条件に反する。空でない有効な object だけがエラーを解除する。/ 委任（設計レビューの指摘で変更）。
- **D5 `first_json_object` の扱い**: ヘルパーとテストを残し、docstring に「現行の adapter からは呼ばない。上流との対応と #457 の確認結果のために残す」と書く。/ 別案: 削除する。/ 理由: #425 で例示境界を合わせたばかりで、#457 の結果次第で再び使う可能性がある。削除は #457 の結論を先取りする。/ Issue が委任。
- **D6 JSON 指示の文言と位置**: 4 adapter とも `request_prompt` を依頼文の最初の部分に使い、その後に `prompt_lines`（skill の指示）を続ける。claude_code の Bash の timeout の案内は今の位置（最後）のまま。pi・claude_code の文は `"Return your final answer as a JSON object."` から `JSON_REQUEST`（`"Answer with a single JSON object as your final message."`）に変わり、skill の指示より前に移る。codex・cursor は文言も位置も変わらない（呼び出し方だけが変わる）。/ 別案: pi・claude_code で今の位置（skill の指示の後）に `JSON_REQUEST` を足す。/ 理由: `request_prompt` は「依頼文 + JSON 指示」を返す関数で、後ろに置くと関数を使わずに文字列を足すことになり、接続の意味が無くなる。上流・codex・cursor と同じ並びになる。/ Issue が委任。
- **D7 shape の取り方**: 各 adapter が今使っている値（pi・claude_code は `context.role.result_shape`、codex・cursor は `context.request.result_shape`）を変えない。runner は `request.result_shape` を `role.result_shape` から作るので同じ値である。/ 理由: 範囲外の変更を増やさない。/ 委任。
- **D8 テスト**: 追加するのは S の代表だけ（下の「テスト」）。devin のテスト（`test_invalid_final_json_does_not_return_nested_fragment`）と `test_json_result.py` の U1 の層またぎの重複は、devin を変えないので触らない。/ 別案: この作業で D の整理をする。/ 理由: devin は対象外で、devin のテストを消すと devin の接続の守りが無くなるかを別に判断する必要がある。/ Issue が「検討」として委任。
- **D9 claude_code の未閉鎖の `json` fence**: 旧 `_json_object` は閉じない fence 内の object を拒否していたが、`json_object` は受け付ける（pi.rst の「未閉鎖の fence 内でも有効な JSON object は受け付ける」と同じ）。既存テスト `test_invalid_fence_cannot_salvage_inner_json` の `'```json\n{"ok":true}'` の場合は、新しい仕様に合わせて削除する。もう一方の場合（壊れた外側の object の中の object を拾わない）は残す。/ 別案: claude_code だけ未閉鎖 fence を拒否する規則を足す。/ 理由: object 自体は完全に decode でき、壊れた候補も無い。claude_code の完了条件（`result` イベントの `subtype = success`）は別にあるので、途中で切れた出力は完了条件で拒否される。pi と規則を揃える。/ 委任。
- **D10 Spec・設計レビュー**: 利用者の指定どおり、設計レビュー（`pi_openai-codex_gpt6-sol_xhigh`）→ Spec レビュー（`devin_swe2_max`）の順に行い、builder check は行わない。/ 利用者の指定。

## 担当とループの設定（helper の検査結果）

- Plan の Task の実装: `implement_task.py check --implement devin_swe2_max` → `assignment.agents = ["devin_swe2_max"]`（`--implement` の明示）、`fallback = []`（個人設定のまま）、`self = false`
- 設計レビュー: `review_design.py check --design-review pi_openai-codex_gpt6-sol_xhigh` → `agents = ["pi_openai-codex_gpt6-sol_xhigh"]`（明示）、`fallback = []`
- Spec レビュー: `review_spec.py check --spec-review devin_swe2_max` → `agents = ["devin_swe2_max"]`（明示）、`fallback = []`
- PR 修正ループ: `loop.py check-options` → `max_cycles = 3`（既定の適用）、`assign.implement = ["devin_swe2_max"]`・`assign.inspect = ["devin_swe2_max", "claude-code_ollama_opus_max", "pi_openai-codex_gpt6-sol_xhigh"]`（利用者の指定）、`self-review`・`fix-check` は `self`（既定の適用）、`template` は雛形の既定

## 設計

### 抽出

- `tools/agent_runner/adapters/claude_code.py`: `_FENCE` と `_json_object` を消し、`_payload` で `json_object` を使う
- `tools/agent_runner/adapters/codex.py`: `_json_object` を消し、`turn.completed` の解除判定と最終 payload の両方で `json_object` を使う。解除判定は、抽出した dict が空でないときだけ pending error を消す（D4）
- `tools/agent_runner/adapters/cursor.py`: `_json_object` を消し、最終 payload で `json_object` を使う
- 完了イベントの選び方（claude_code の `result`、codex の最後の completed `agent_message` と `turn.completed`、cursor の `result`）、malformed event の扱い、認証・承認の診断は変えない

### JSON 指示

- pi: `lines = [request_prompt(context.request.prompt, context.role.result_shape)]` の後に `prompt_lines`。末尾の独自の文を消す
- claude_code: 同じ形にし、Bash の timeout の案内は最後に残す
- codex・cursor: `_prompt` の最初の部分を `request_prompt(context.request.prompt, context.request.result_shape)` にし、独自の文を消す
- devin: 変えない

### 文書

- `runtimes/claude-code.rst`・`codex.rst`・`cursor.rst` の「応答と失敗の判定」の JSON の段落を、pi.rst と同じ内容（最後の object、結果 fence の判定、例示の扱い、壊れた候補での拒否、未閉鎖 fence）に書き換える。cursor.rst の「最初の JSON オブジェクトを取り出す」は削除する
- 依頼文の JSON 指示が共有の `request_prompt`（`JSON_REQUEST`）であることを、4 つの runtime 文書の起動の節に 1 行で書く
- pi.rst の抽出の記述は PR #461 で更新済みであることを確認し、指示の 1 行だけを足す
- `json_result.py` のモジュール docstring と `first_json_object` の docstring に D5 を反映する

## 受け入れ基準

- 動作環境: Dev Container、`uv run --locked`、偽イベント（`tools/agent_runner/tests/adapters/test_parser_regressions.py` の `_events`）と `prepare` の戻り値だけを使う。実 CLI・モデル・API は起動しない
- 実入力:
  - 文章 → 裸の JSON（複数行・非 ASCII）: `"レビュー完了。指摘は以下です。\n{\n  \"status\": \"completed\",\n  \"findings\": [\"日本語の指摘\"]\n}"`
  - 文章 → fence 付き JSON: `"Review complete.\n```json\n{\"status\": \"completed\", \"findings\": []}\n```"`
  - 訂正: `"```json\n{\"status\": \"OLD\"}\n```\nI corrected the result.\n```json\n{\"status\": \"NEW\"}\n```"`
  - JSONC の設定例 + 正常な最終結果: `test_json_result.py` の `test_jsonc_example_accepts_result_after_fence` と同じ形
  - 壊れた候補・途切れ: `"{\"status\": \"OLD\"}\nDone.\n{\"status\": \"DONE\","`、文章だけ: `"Review complete."`
- 合格条件:
  - claude_code・codex・cursor の collect が、文章 → 裸の JSON・訂正・JSONC の例 + 最終結果で `success` になり、payload が最後の有効な object と一致する
  - 同じ 3 adapter で、途切れ（先行する有効な object あり）・文章だけが `response_failed` になり、先行する object を返さない
  - pi・claude_code・codex・cursor の JSON の役割の stdin が `request_prompt(prompt, "json")` で始まり、`JSON_REQUEST` を 1 回だけ含み、旧文 `"Return your final answer as a JSON object."` を含まない。text の役割の stdin は `JSON_REQUEST` を含まない
  - codex で、認証エラーの後の空 object `{}` の完了 message はエラーを解除せず、`awaiting_authentication` のまま
  - devin の `prepare` の stdin と argv が base と同じ
  - 既存の adapter テスト（完了条件・診断・隔離）がすべて通る
- 防御範囲（対象）: 上の形で完了結果を採用し、壊れた回答・設定例の object・古い object を成功にしないこと
- 防御範囲（対象にしない反例）: 壊れた候補を含まない正常 object だけの例示は、後続結果が無ければ候補になる（#425 で委任された限界）。意味から例示かどうかを推測しない。実 CLI の出力形式の変化は扱わない

## テスト

AGENTS.md の「テストの採用基準」に従う。

- 追加（S、`tools/agent_runner/tests/adapters/test_parser_regressions.py`）:
  - claude_code・codex・cursor を parametrize した 1 つのテストで、訂正形の collect が最後の object（`NEW`）を payload にする。古い object を成功にする誤り（気付けない損害）を各 adapter の接続ごとに守る。3 つの adapter はそれぞれ別の呼び出し箇所なので D ではない。成功する形なので陽性対照も兼ねる
  - 同じ 3 adapter で、先行する有効な object の後に途切れた候補がある応答が `response_failed` になる。adapter 側の巻き戻りを守る。拒否の例には上の成功例が対になる
  - codex で、認証エラー → `{}` の message → `turn.completed` が `awaiting_authentication` のまま（D4）。空 object でエラーを解除すると、診断が `invalid_result` に変わって認証待ちに気付けない（S）。既存の `test_codex_fresh_completed_message_recovers_error`（空でない object での回復）が陽性対照になる
- 追加しない: 文章 → 裸の JSON・JSONC の例・壊れた候補の分類（`test_json_result.py` が `json_object` で守っており、adapter ごとに同じ規則を網羅すると D）。依頼文の文言（壊れても JSON でない応答が `response_failed` として見える L、文言の固定は F）。これらは一時的なスクリプトで確かめ、PR 本文に結果を書く
- 変更: `test_invalid_fence_cannot_salvage_inner_json` の未閉鎖 fence の場合を削除する（D9）
- `first_json_object` のテストは D5 のとおり残す

## contingency

- 既存テストが新しい抽出で落ちた場合: 落ちた入力が「新しい仕様で意味が変わる形」（未閉鎖 fence など）なら D9 と同じく仕様に合わせて直し、ledger に記録する。完了条件・診断のテストが落ちたら、実装の誤りとして直す（テストを変えない）
- `request_prompt` の位置を変えて既存の prompt テストが落ちた場合: 期待値を新しい並びに合わせる。devin のテストが落ちたら実装を戻す
- 外部担当（devin）の実装が `failed` で止まった場合: issue-to-pr の規則どおりその Task で止まり、自分で引き取らない

## 残すこと（builder に任せる）

- テスト関数名と fixture の細部
- runtime 文書の文の細部（意味は上の「文書」のとおり）

## レビュー記録

### 設計レビュー 1 回目

- helper: `review_design.py`（外部担当）。`requested_agent` / `actual_agent`: `pi_openai-codex_gpt6-sol_xhigh`（`--design-review` の明示。`fallback` は空のまま、使用なし）
- identity: model `gpt-6.1-sol`、provider `openai-codex`、effort `xhigh`
- `review_id`: `74d4b0797af145b190d3f20c9dc09e69`、reviewed の Spec SHA-256: `2edfeecbd8f6b93ee0c0dba581df19a7278a1ed4ac3de3b6cec51675bc93511e`、対象 revision `1e16a99a2a501f23b47ba6b4e5697267b8fc7b68`
- `elapsed_seconds`: 178.2、`outside_changes`: なし、`unprotected_changes`: 他の作業の `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の worktree 6 件（この作業の対象外。記録のみ）
- 判定: `concerns`（1 件）
- 採否: D1（blocking、codex のエラー解除で空 object を許すと認証・承認の診断が消える）を採用。D4・設計の codex・テスト・受け入れ基準に反映した
- `decide` の結果: `next: stop`（理由 `blocking: D1`）。reflected の Spec SHA-256 は `ce624d854375254c75238926eeace3aab1c81dd72a34333a0d13350cf67f552f`（commit `0f46416d`）。採用・反映済みの blocking で `wrong_approach`・`questions_for_user`・`needs_judgment`・作るものの変更が無いため、利用者の 2026-11-15 の続行指示（Issue #427 の run での指摘。#455 で修正を追跡中）に従い、止まらずに Spec レビューへ進んだ
- レビューの記録は commit しない: `PARENT_ROOT/tmp/agents/issue-416.q59dbn2x/2026-11-15-issue-416-json-result-adapters-design.design-review/review-1`
