# Issue #425 JSON example boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JSONC/JSON5 の設定例の後ろの正常結果を採用し、壊れた例を無視して古い結果を成功にしない。
**Architecture:** 既存 json_result の走査に局所的な言語分類と位置条件を加える。例内の壊れた候補は例終端後の結果が必要。既存 result fence 優先・正常例の候補化・first/last 選択を維持する。
**Tech Stack:** Python 標準 json、pytest、uv、既存 fake collect fixture。
**Spec:** `docs/superpowers/specs/2026-11-15-issue-425-json-example-boundary-design.md`

状態: `draft`。issue-to-pr の実行許可で進めるが、内容の承認を得たとは記録しない。Spec と同じ branch/PR へ含める。確認コピーは作らない。

## Global Constraints

- 結果 fence は info の最初の語が大文字小文字を無視して `json` と完全一致する場合。言語なし fence も既存どおり結果として扱う。閉じた明示非 JSON fence と閉じた inline code span は例。
- result fence の内側の inline code と入れ子の非 JSON fence は例として認識しない。壊れた object 候補は後続結果があっても拒否する。
- 例内の壊れた object 候補は、その例の終端より後ろに有効な結果がある場合だけ不問にする。例内の別の正常 object では条件を満たさない。複数の壊れた例では最後の例が基準。
- `json_object(text: str) -> dict[str, object] | None` は最後の正常 object（空 object を含む）を返す。正常 array は丸ごと消費し、内側 object で後続条件を満たさない。
- `first_json_object(text: str) -> dict[str, object] | None` は先頭の非空 object 選択を維持し、選択した候補自体が最後の壊れた例の終端より後ろに無ければ None。array 内の object を選ぶ既存経路では array の開始位置を使う。別候補への差し替えはしない。
- 壊れた候補が一つもない正常 object のみの jsonc/json5 例は候補になる。後続無し・OLD 先行でもこの限界を維持する（Spec D3 の委任判断）。
- 裸の壊れた候補・json/言語なし fence 内の壊れた候補・wrapper 内の正常 fragment 救済禁止を維持する。スキャナ全面書換え、他 adapter の接続・選択変更、request_prompt 接続はしない。
- 不具合の再現は保存した偽イベントとローカル collect のみ。実 CLI・有料モデル・実 API を起動しない。指定された workflow 担当の起動とは区別する。
- テストは AGENTS.md の S の代表だけ。共有ガードは json_result のテストへ置き、adapter ごとの重複と文書の文字列照合テストは追加しない。Python は uv 経由。

## Review Focus

- 例内に壊れた候補と正常 object が共存しても、終端外の結果無しに成功にしない（Task 1 の新規 S テスト）。
- 一度後続結果があっても、さらに壊れた例が続いたら拒否する（controller 一時 probe。位置条件の組合せを重複コミットしない）。
- inline code と非 JSON 入れ子 fence を result fence 内で例と誤認しない（既存 crossed-by-inline テスト、controller 一時 probe）。
- 先頭選択 helper が OLD + 壊れた例 + DONE を OLD として新たに成功にしない（Task 1 の新規 S テスト）。
- 正常 object の例、未閉鎖 fence、空 object と array の扱いが Spec の限定と一致する（controller 一時 probe。正常例の限界を追加機能にしない）。

## 受け入れ基準（実装担当・Task レビュアーへ同じ本文を渡す）

- 動作環境: Dev Container、捕捉した main 以降の parser と pi/devin collect。保存した偽イベントだけを使用し、実 CLI・有料モデル・実 API で再現しない。
- 実入力: `設定例:\n` に続く閉じた複数行 jsonc（`{"名前":"試験", "enabled": true /* comment */}`）または json5（`{"名前":"試験", "enabled": true,}`）fence、続く `結果:\n` と `{"status":"DONE"}`（json fence または裸）。両経路で success/payload 一致。
- 防御範囲: OLD + 壊れた jsonc/json5 例で終端後の有効結果が無い場合は response_failed/payload None。例の中の後続 object・nested fragment で救済しない。壊れた json/JSON/言語なし fence、裸の壊れた候補、wrapper 内の正常 fragment 救済を拒否する。
- 限界・対象外: 正常 object だけの例は候補のまま。first/last の通常選択、既存の array の扱い、未閉鎖 fence の扱いを維持する。全面 scanner 移植・別 adapter 接続は行わない。
- 証拠: helper の Red/Green、代表 S ガード、controller の両 collect 経路の陽性/陰性、docstring と runtime 文書の意味一致。共有前提は例終端の位置・候補の位置・結果 fence の優先で、統合担当が同じ実入力から保存 receipt/payload まで照合する。

---

### Task 1: 共有 parser の例示境界と文書を一致させる

担当: runner の `pi_opencode-go_deepseek4-flash_max`（明示、fallback 空）、controller による取り込み後レビュー。

**Files:**
- Modify: `tools/agent_runner/adapters/json_result.py`
- Test: `tools/agent_runner/tests/adapters/test_json_result.py`
- Modify: `tools/agent_runner/runtimes/pi.rst`
- Modify: `tools/agent_runner/runtimes/devin.rst`

**Interfaces:**
- Consumes: `_Fence`、`_example_fence(fence: _Fence) -> bool`、`_extract_object(text: str, *, first: bool) -> dict[str, object] | None` の既存状態と走査。
- Produces: `json_object` と `first_json_object` の既存 signature のまま、Global Constraints の位置条件を満たす結果。pi/devin adapter コードは変更不要。

**テスト要否:** S。単に言語判定を緩めると古い/例内の object をもっともらしい成功にするため、共有 helper で防御する。陽性は拒否一辺倒の実装を防ぐ対照。通常の API/型/構文や文書文言の固定値は L/F としてテストにしない。下記以外の組合せは一時 probe と既存テストで確認し、テストを増殖させない。

- [x] **Step 1: tests を先に追加する**
  - `test_jsonc_example_accepts_result_after_fence`: 複数行・日本語付き jsonc のコメント例 + json fence の DONE が `{"status":"DONE"}` と一致。
  - `test_malformed_example_requires_result_beyond_its_end`: OLD + json5 fence の `{"enabled": true,}` + 同じ fence 内の `{"status":"EXAMPLE"}`、fence を閉じて終了 → None。無条件無視と例内での条件解除の両方を防ぐ代表例。
  - `test_first_result_cannot_precede_malformed_example`: first helper で OLD + 壊れた jsonc fence + DONE → None。併せて OLD を置かない陽性では DONE を返す。先頭選択と最後の壊れた例の位置の関係を守る独立ガード。
  - 各ガードには防ぐ損害と S の理由をコメントする。既存 4 テストは維持。
- [x] **Step 2: Red を観測する**
  - `uv run --locked pytest tools/agent_runner/tests/adapters/test_json_result.py -q`
  - 少なくとも jsonc の陽性と json5 の終端外ガードが期待する理由で失敗することを確認する。単純言語変更だけの対照が OLD/EXAMPLE を返すことも必要に応じ一時的に確認する。失敗内容を報告に保存。
- [x] **Step 3: 局所実装**
  - `_example_fence` の完全一致判定と、壊れた例の終端より後ろの選択候補を必要とする状態を `_extract_object` へ加える。
  - 既存の候補の消費、正常例の候補化、result fence 優先、first の array 選択を維持する。全面 scanner 書換え・新依存は入れない。
  - module/function docstring と pi/devin の「応答と失敗の判定」を、json 完全一致・壊れた例の後続必須・result fence 優先・正常例の候補化に合わせる。RST の既存構造と記法を使う。
- [x] **Step 4: Green と関連回帰を同期実行する**
  - `uv run --locked pytest tools/agent_runner/tests/adapters/test_json_result.py -q`
  - `uv run --locked pytest tools/agent_runner/tests -q`
  - `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
  - すべて終了コード 0。失敗は省略せず、原因と対象を報告する。文書の意味とコードを自己照合し、`git diff --check` を通す。
- [x] **Step 5: commit と報告**
  - 上記 4 パスだけ stage し、`fix: require a later result after malformed JSON examples` で commit。
  - Red/Green のコマンド・結果、作業時間と内訳、変更内容、残る懸念を helper の結果形式で返す。Spec/Plan や GitHub は編集しない。subagent/runner の入れ子起動をしない。

## 統合担当の確認・要件対応

担当は controller。実装 Task の取り込み後に以下を行う。新たなコード実装 Task ではない。テスト追加は不要（共有ガードは Task 1 に集約し、同じ規則の adapter 層の D を避ける）。

| 条件 | 入口・観測 | 証拠 |
|---|---|---|
| jsonc/json5 例 + 後続 json/裸 DONE | pi session→agent_end→agent_settled、devin stdout/export 一致 | SESSION の fake collect probe に入力・status・payload を保存 |
| OLD + 壊れた例で終端後結果無し | 同じ両 collect で response_failed/None | 同 probe、shared S テスト |
| 例内別 object で後続条件を満たさない | json_object(None)、first helper の OLD 拒否 | shared S テスト、Task レビュー |
| result fence 優先、裸候補、wrapper 拒否 | helper の既存テストと限定 probe | 入れ子 inline/非 JSON fence の反例を一時実行 |
| 複数例、正常例限界、空/array/first/未閉鎖 | 独立に組み立てた入力と期待値 | SESSION の一時 probe（コミットしない） |
| 文書の意味一致 | 4 変更ファイルの Task レビュー | 読み取り専用の spec compliance + task quality |

最終必須コマンド（Plan commit 直後に SESSION/verify-cmds.json に固定する）:

1. `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q`
2. `bash .devcontainer/run-tests.bash`
3. `bash scripts/check-layout.sh`
4. `uv run --locked python /workspaces/reso-world/tmp/agents/issue-425.55cedqeq/verify_examples.py`
5. `git diff --check`

捕捉済み base を再確認し、必要なら未 push の base 前進 helper でのみ追随・全必須コマンドを再検証する。検証した HEAD、空の status、argv、終了コード、完全ログパスを checks.json の finalize 形式に保存する。最後のブランチ全体レビューは `--merge` のループの 1 サイクル目で行う。CI は無効のままで追加しない。Gitleaks を通した同一 SHA を push する。

## 実行予算

- 全体の能動時間は 360 分（準備を含め約 60 分、実装・Task レビュー 60 分、統合・公開 30 分、ループ最大 3×60 分）。Issue の本体 1.5〜3 時間に、明示設計/Spec レビューと最大 3 サイクルのレビュー修正・マージ枠を加える。
- ledger は SESSION/budget.jsonl、SDD 作業領域は SESSION/sdd/2026-11-15-issue-425-json-example-boundary/。既に開始済みの ledger を再作成しない。
- runner 実装期限は設定の 90 分。専用 attempt 領域だけへ書く。監視は pi の同期 foreground、tool timeout を付けず helper の終了と stop_confirmed を待つ。controller が独自に期限延長・停止をしない。別の watchdog 宣言を作らないため予約枠・無進捗打ち切りは未設定。10 分以上の実行の進捗・停止は runner の監督と終了結果で確認する。
- Task レビュー子は同期・読み取り専用、テストを実行しない。実装依頼は 1 件ずつ。依頼し直しは同じ reliability 失敗で 1 回まで、Task の指摘修正は SDD の上限に従い、各回の依頼として記録・cleanup。安全の失敗、helper が定める failed、予算 100% は停止。
- checkpoint: Spec レビュー完了（記録済み）、Task 完了、公開直前、各ループ、50%・100%、失敗直後。能動時間は issue_budget.py を基準とし、開始以前の入力確認約 10 分は最終報告へ別記する。
- ループの reviewer 期限は設定の 45 分、最大 3 サイクル。使用率と成果で継続可否を判断する。自分で上限を延ばさない。

## contingency（代替策）

最初の Red が入力形の前提差を示した場合、意味を保つ最小修正だけ ledger に記録して継続する。保証の変更・未知の成功扱い・壊れた結果の救済には進まない。スキャナ全面移植が必要と判明したら #436 と調整が必要なため停止報告する。実装担当が失敗したら controller が self で引き取らない。

base が未 push で無関係な変更のみ前進した場合は issue-to-pr の inspect/advance/reverify に従い最大累計 3 回まで追随する。所有パスとの重複、push 済み、非 FF は停止。過剰な検証ケースは一時 probe に留め、S のガード・受け入れ入力を削らない。

## 完了記録

Task 1 は `f93c35ca685c3cae588c9e883cf6a98090eae4bf` で取り込み済み。明示担当 `pi_opencode-go_deepseek4-flash_max` の 1 回の依頼、実測 identity `deepseek-v4.1-flash/opencode-go/max`、elapsed=1404.39 秒。Red は helper の 2 failed/5 passed と、言語判定だけを変更した対照で json5 の例内 EXAMPLE を誤採用する失敗を観測。Green は helper 7 passed、runner 308 passed、全体 1587 passed（979.66 秒）、diff check 成功。controller が取り込み後の runner 308 passed と diff check を再確認した。

Task レビュー（sp-review、読み取り専用）は spec compliant / task quality approved、指摘なし。初回 dispatch は明示 scope が足りず NEEDS_CONTEXT、`Review scope: task` を明示して開始した。未検証項目として挙げた pi/devin collect の実経路は controller の `verify_examples.py` で確認し、全 40 確認成功（22 collect・18 helper、終了コード 0）。jsonc/json5 の複数行・非 ASCII 例 + fenced/bare DONE は両方 success、OLD と壊れた例のみは両方 response_failed/None。result fence 優先・複数例・正常例の限界・array/empty/first/未閉鎖も Spec と一致した。証拠: SESSION/integration-probe.log と probe-results-jttp6oty.json。

設計/Spec の cleanup および実装依頼 cleanup は停止確認済みで retained 空。依頼/結果・採否・ログの保存先は SESSION、実装依頼 JSON は `/workspaces/reso-world/tmp/agents/issue-425-implement.rwu0c7in/` に残す。Spec は再レビューで確定した内容・版を維持する。

Task 後の base 再照合で main 前進を検出した。未 push の inspect/advance/reverify で処理し、その旧/新 SHA と必須コマンドの結果を PR と SESSION に記録する。最終必須検証・Gitleaks・PR・ループはこの時点では未実施。PR は `Refs #425` とし、マージ後の同じ fake collect の再確認項目を Issue コメントへ残す。指定 loop/finalize の外でマージしない。
