# Issue #418: pi adapter の JSON 結果抽出を json_result.json_object に移植する

- 状態: draft
- 対象リポジトリ: usaturn/create-reso-world
- Issue: https://github.com/usaturn/create-reso-world/issues/418
- 関連: #406（PR #410・devin 移植済み）、#414（同種・pi）、#416（包括展開・pi 部分重複）、#349（ボード所有）
- 作成日: 2026-11-13

## 管理・実行許可

利用者の指示（2026-11-13）:

> `/issue-to-pr #418 --merge --spec-review devin_swe2_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max`

issue-to-pr スキルによる着手。通常の設計判断は推奨案で決め、検証・commit・push・PR 作成・PR 修正ループ・マージまで継続する指示。Spec・Plan は draft のままコミットし、内容の承認（approved）にはしない。確認用コピーは作らない。

許可された範囲: `tools/agent_runner/adapters/pi.py`・`tools/agent_runner/runtimes/pi.rst`・pi adapter のテスト・`test_parser_regressions.py` の pi 部分。`--merge` によるループと finalize.py のマージを含む。

## 意図・背景

pi adapter の `_json_object` は「テキスト全体が JSON object」か「```json fence 内の object」しか受け付けない。モデルが結果 JSON の前に説明文（prose）を fence なしで付けると、回答が完了していても `response_failed` になり、有料の実行結果が失われる。#396 の Spec レビューで実際に発生し、別担当での再実行（約 10 分）が必要になった。

#406（PR #410）で devin adapter は `json_result.json_object` に移植済み。pi にも同じ移植を行い、prose + 非 fence JSON を受け付けるようにする。

## 決定記録

### D1: 代表 Issue の決定

- 選択した案: #418 を代表として着手する
- 検討した別案: #414（同種）・#416（包括展開）を代表にする
- 選択理由: 利用者が明示的に `#418` を指定して着手を指示した。#349 の coordinator 記録（2026-11-12T06:55:33Z）は「代表の Issue を 1 つに決めるまで複数セッションで同じファイルを編集しない」という調整ルールであり、利用者（coordinator 自身）の明示的な #418 指定が代表の決定に当たる。競合確認（2026-11-13）: open PR なし、claim ref なし、worktree・branch なし（#414・#416 も同様）。並行編集の競合はない
- 委任指示または停止条件: issue-to-pr の委任により推奨案で進める。#414・#416 の close・統合はこの run の範囲外（利用者の另行指示が必要）

### D2: 抽出関数の移植方式

- 選択した案: `_json_object` を削除し、`json_result.json_object` を import して `_payload` で使う（devin と同じ構成）
- 検討した別案: (a) 独自の fence regex を拡張して prose 前置きを受け付ける (b) `_json_object` を残し json_object をフォールバックにする
- 選択理由: Issue が `json_result.json_object`（#406 のポート）を明示。json_result は壊れた候補の拒否・巻き戻し禁止・example 境界を仕様化済みで、devin で実運用済み。(a) は拒否仕様の再実装になり D（重複）と保守コストが増える。(b) は古い抽出規則が残り、訂正で古い object を採用する問題が残る
- 委任指示または停止条件: 推奨案で進める。json_result.py のスキャナは書き換えない（#406 の指示を維持）

### D3: プロンプト指示の扱い

- 選択した案: pi の既存プロンプト指示（"Return your final answer as a JSON object."）を現状のまま維持する
- 検討した別案: `json_result.request_prompt` を接続する（agent-workspace の pi adapter と同じ構成）
- 選択理由: #406 の devin 移植は「指示だけでは文章の混入を防げない」ためプロンプト指示を現状のままにした。#418 は #406 の pi 版であり、同じ方針を踏襲する。`request_prompt` の接続は #416（包括展開）の範囲
- 委任指示または停止条件: 推奨案で進める

### D4: 回帰テストの更新

- 選択した案: `test_invalid_fence_cannot_salvage_inner_json` の parametrization から "pi" を外す（claude-code は残す）。未閉鎖 fence + 有効 JSON は json_result では接受されるため、旧 pi の拒否を固定したテストは pi に適用できなくなる
- 検討した別案: pi 用にテストケースを分割して残す
- 選択理由: 未閉鎖 fence の有効 JSON 接受は devin と同じ意図的な挙動変更。壊れた候補の拒否（閉鎖 fence 内の malformed JSON）は json_result の既存テストと pi の新規 S テストでカバーする。claude-code の変更は #416 の範囲なので触らない
- 委任指示または停止条件: 推奨案で進める

### D5: _classify の終端判定

- 選択した案: `_classify`・`_events`・`_payload` の終端判定ロジックは変更しない
- 検討した別案: なし（Issue が「緩めない」と明示）
- 選択理由: agent_end 以降の破損行・異常 stopReason・agent_settled の必須・認証/承認診断の優先は、JSON 抽出とは独立した安全境界。移植は `_payload` が呼ぶ抽出関数の差し替えに限る
- 委任指示または停止条件: 編集禁止。緩める変更は停止条件

## 受け入れ基準

### 動作環境

- Dev Container（Ubuntu 26.04）・`uv run pytest` による偽 pi イベント出力のテスト
- 実 CLI・モデル・API は起動しない（Issue が明示）

### 実入力

pi の `collect` 経路（`_classify` → `_payload` → 抽出関数）に、偽の NDJSON イベント（`session` → `agent_end`（assistant メッセージに以下のテキスト）→ `agent_settled`）を与える:

1. **prose + 非 fence JSON**（修正本体）: `"Review complete. The findings are below.\n{\"status\": \"completed\", \"findings\": []}"` → success・payload は最後の有効 object
2. **prose + fence 付き JSON**: `"Done.\n```json\n{\"status\": \"completed\"}\n```"` → success
3. **全体 JSON**: `"{\"ok\": true}"` → success（既存テストでカバー済み・陽性対照）
4. **訂正形**: 古い fence JSON → prose → 新しい fence JSON → success・payload は**最後の**有効 object
5. **壊れた候補**（example 外）: `"{\"ok\": true}\n{\"broken\": }"` → response_failed（以前の有効結果に巻き戻らない）
6. **prose のみ**: `"Just text, no JSON here."` → response_failed
7. **未閉鎖 fence + 有効 JSON**: `` "```json\n{\"ok\":true}" `` → success（devin と同じ・意図的変更）
8. **JSON 文字列内の backtick**: fence 内に `` ```python `` を含む文字列 → success・payload は完全な object（既存回帰テストでカバー）

### 防御範囲

- 対象: pi adapter の `collect` 経路における JSON 抽出（`_payload` → `json_object`）
- 対象外（変更しない）:
  - `_classify` の終端判定（agent_end 必須・agent_settled 必須・破損行拒否・異常 stopReason 拒否・認証/承認診断優先）
  - `_events` の NDJSON パース・破損行の位置保持
  - `prepare` の argv 構築・プロンプト指示
  - `_identity` の観測範囲
  - json_result.py のスキャナ（書き換えない）
  - 他 adapter（claude_code・codex・cursor）— #416 の範囲
  - `request_prompt` の接続 — #416 の範囲
- 反例: 壊れた候補が example（非 JSON 言語の閉鎖 fence・閉鎖 inline code span）内にある場合は拒否しない（json_result の仕様どおり）。example 内の有効 object は通常の候補として扱う

## 編集範囲

| ファイル | 変更内容 |
|---|---|
| `tools/agent_runner/adapters/pi.py` | `_json_object`・`_FENCE` を削除。`json_result.json_object` を import。`_payload` を差し替え。モジュール docstring を更新 |
| `tools/agent_runner/runtimes/pi.rst` | 50 行目の「object 全体か JSON code fence 内の object を受け付ける」を新しい仕様に更新 |
| `tools/agent_runner/tests/adapters/pi/test_adapter.py` | S テストを追加: prose + JSON の成功・壊れた候補の拒否（collect 経路） |
| `tools/agent_runner/tests/adapters/test_parser_regressions.py` | `test_invalid_fence_cannot_salvage_inner_json` の parametrization から "pi" を外す |

## テストの採用基準

- **S（書く）**: pi collect 経路で prose + 非 fence JSON が success になること。壊れた候補が response_failed になること。これらが壊れると、完了した有料実行が失われる（prose 拒否）、または誤った結果が成功として採用される（壊れた候補の接受）— エラーにならず気付けない損害
- **D（重複しない）**: json_result の単体テスト（`test_json_result.py`）は既存。同じ抽出規則の網羅はそちらに任せる。pi 側の S テストは「pi adapter が json_object を正しく配線している」ことの確認であり、json_object 自体の規則テストとは守りが異なる（配線を戻したら pi テストは失敗するが json_result テストは通る）
- **陽性対照**: 拒否テストには正しく通る例（prose + JSON の成功）を少なくとも 1 件残す
- **F（書かない）**: pi.rst の文言を写して照合するテストは書かない。文書更新は `git diff` と構成確認で代える
- **L（書かない）**: import エラー・構文エラーは既存の pytest 実行で気付ける

## approaches（検討した方式）

1. **json_object への差し替え（採用）**: devin と同じ構成。`_json_object` と `_FENCE` を削除し、`json_object` を import。拒否仕様は json_result に一元化。最小の変更で #406 の恩恵を pi に届ける
2. **独自 fence regex の拡張（不採用）**: prose 前置きを受け付けるよう `_FENCE` を拡張する。拒否仕様（壊れた候補・example 境界・巻き戻し禁止）を再実装する必要があり、json_result との D（重複）と保守コストが増える。Issue が json_result を明示
3. **フォールバック併用（不採用）**: `_json_object` を残し、None のとき json_object にフォールバックする。古い抽出規則が残り、訂正で古い object を採用する問題（#416 の表で実測済み）が残る。2 つの抽出規則が並存し、挙動の予測が難しくなる