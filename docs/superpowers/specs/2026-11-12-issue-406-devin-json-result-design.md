# Issue #406: devin の最後の発話が文章の後に JSON を続く形の救済（json_result 移植）

- 状態: `draft`
- Issue: https://github.com/usaturn/create-reso-world/issues/406
- 対象リポジトリ: usaturn/create-reso-world（`TARGET_REPO`。文書も同じ worktree・PR に入れる）
- base: `main` @ `ae4b6e71361314fb3de6008f8d31b830fec90f3c`（捕捉済み。`--base` 未指定の既定）
- 作業ブランチ: `fix/issue-406-devin-json-result`

## 管理・実行許可

利用者の指示（2026-11-12、スラッシュコマンドの引数と自然文）:

> `/issue-to-pr #406 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`
>
> 「pi_alibaba_qwen4-max_max を動かす為に、 ANTHROPIC_AUTH_TOKEN を MAAS_ANTHROPIC_TOKEN として渡してください。」
> 「途中でメインがマージされたら、追随して作業を止めずに続行してください。」

許可された範囲:

- issue-to-pr スキルの通常の委任（推奨案での設計判断、検証・commit・push・PR 作成までの継続）。設計・Spec・Plan の確認質問はしない
- `--merge`: PR 作成後の PR 修正ループ（pr-review-fix-loop）と、修正不要のときの `finalize.py` によるマージ・関連 Issue の更新。ループのオプションは利用者が書いた `--assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh` だけ（サイクル上限は既定の 3）
- 設計レビュー担当 `pi_openai-codex_gpt6-sol_xhigh`、Spec レビュー担当 `pi_alibaba_qwen4-max_max`、Plan の Task 実装担当 `pi_alibaba_qwen4-max_max`（いずれも明示値。個人設定の fallback は空で保持）
- runner 起動時の key 渡し: `pi_alibaba_qwen4-max_max` を使う起動（Spec レビュー・Task 実装・ループの implement / inspect）では、`ANTHROPIC_AUTH_TOKEN` の値を `MAAS_ANTHROPIC_TOKEN` としてワンショットで渡す（永続 export しない）。`pi_openai-codex_gpt6-sol_xhigh` の `OPENCODE_API_KEY` は `with_keys.py` が env ファイルから補う
- main の追随: 作業中に `origin/main` が進んだ場合、捕捉 SHA が新しい main の祖先である（fast-forward である）ときに限り、base を再捕捉して feature ブランチを rebase し、検証をやり直して続行する。祖先でなくなった（force push・履歴の書き換え）場合は停止する。追随のたびに旧・新 SHA と再検証の内容を SESSION に記録する

この指示は内容の承認（`approved`）ではない。Spec は `draft` のままコミットする。

## 意図と背景

`tools/agent_runner/adapters/devin.py` の `collect` は、export の最後の agent の発話が「文章 → 空行 → JSON」や「文章 → fence 付き JSON」の形だと、JSON の部分が正しくても `response_failed` にする（`_json_object` が回答の先頭からしか読まないため）。結果が JSON の役割（implement・self-review・fix-check・inspect）では、担当が作業と commit を終えていても結果が捨てられ、issue-to-pr はその Task で止まる。実際に #402 の Task 2（commit `d747b6f3` が捨てられ、同じ Task を別の担当がやり直し）と #401 の Spec レビュー 2 回で発生した。

usaturn/agent-workspace では同じクラスの問題が先に対策済みで（ac4f505 → cb2e488 → 9b61a68 → da12509・fe8c29a・1b3f635、#918 / PR #934）、実運用で鍛えられた `tools/agent_runner/adapters/json_result.py` がある。本 Issue はその移植を指示している。

## 受け入れ基準・防御範囲・動作環境

### 動作環境

- Dev Container（Ubuntu 26.04 LTS、Python 3.14、uv）。devin CLI 3000.12.x の出力の形
- テストは偽の CLI（`tools/agent_runner/tests/adapters/devin/fake_cli.py`）と手元に残る実際の出力だけで行い、実 CLI・モデル・API は起動しない
- 実際の出力の記録: `tmp/agents/issue-402.ht7fd2ih/task-2-failed-evidence/stdout.log`（#402 Task 2 の失敗時の stdout。export.json は回収で消えた）

### 実入力

1. 本文の形（実際の発生）: 最後の発話が複数行の文章（日本語・英語混在、backtick を含む）→ 空行 → JSON object。例: `All done — the setup script is tracked as 100644, matching the other \`setup_pi*.zsh\` scripts (they're invoked as \`zsh scripts/…\`). Tree is clean after the linear commit on \`03fb4c29\`.` の後に空行を挟んで `{"status": "DONE", "commit": "d747b6f3...", ...}` が続く
2. コメントの形（#401 の Spec レビューの発生）: 文章の後に ```` ```json ```` fence 付きの JSON が続く
3. 訂正の形: 古い fence 付き JSON → 文章（日本語）→ 新しい fence 付き JSON

### 防御範囲（対象）

- 上の 3 つの形で `success` になり、payload は最後の有効な JSON object と一致する（訂正では古い JSON でなく新しい JSON を採用する）
- JSON の後ろに文章が続く形・インデントされた JSON も受け付ける（スクラッチで確認済み。コミットするテストの陽性対照は Issue が指定する 3 形）
- 散文中の `{name}` のような brace は object 候補にしない

### 防御範囲（対象にしない反例）

- 最後の発話が文章だけの場合は `response_failed`。途中の発話に JSON があっても拾わない（#188 の隔離。agent-workspace の `collect` にはこの穴があるため、取り出しロジックだけを移植する）
- JSON が途中で切れている・壊れた object 候補がある場合は `response_failed`。前の有効な JSON にフォールバックしない
- stdout が回答で終わる確認（`_ends_with`・`_plain_tail`）と、認証・承認の診断の扱い（stderr と export の error step だけを見る）は変えない
- 他 adapter（claude_code・codex・cursor・pi）への展開は別の Issue とし、ここでは変更しない

### 既知の限界（移植元と同じ・意図を推測しない設計のトレードオフ）

- 結果の後ろに有効な JSON の例が来た場合、例を採用する
- 散文が壊れた JSON を引用している場合（例: `Do not output {"status": DONE}.`）、有効な結果が続いても応答全体を拒否する

## 設計

### 移植（D1）

`tools/agent_runner/adapters/json_result.py` を新設し、usaturn/agent-workspace @ `f65dd6a23f1d8b9bdaa3b68d9cfbe607c25ec822` の同名ファイル（`json_result.py` の最終更新は 1b3f635、#918 / PR #934）をそのまま移植する。`json_object()`・`first_json_object()`・`request_prompt()` とモジュール docstring・ヘルパ一式を含む 345 行。スキャナを「もっと単純に」書き直さない（fence・インラインコードの境界は複数の修正を経て現在の形になっており、書き直しは回帰を招く）。移植の正は byte 一致で確かめる: 期待 sha256 は `a636a027b87cdfa095e838f30a0d4ba1ad49c22a4ba33225428c3f4368495bac`。参照コピーは SESSION（`tmp/agents/issue-406.95mq71g7/`）の `port-source/json_result.py`（固定 revision から取得した byte コピー）。再取得が必要な場合は `gh api "repos/usaturn/agent-workspace/contents/tools/agent_runner/adapters/json_result.py?ref=f65dd6a23f1d8b9bdaa3b68d9cfbe607c25ec822" --jq .content | base64 -d` で固定 commit から取得して照合する。

### devin への組み込み（D2）

- `_payload` の `parsed = _json_object(text)` を `parsed = json_object(text)` に置き換え、`from tools.agent_runner.adapters.json_result import json_object` を追加する。成功判定は参照実装（agent-workspace の devin `_payload`）と同じ `parsed is not None`
- devin の `_json_object` は削除する
- `collect` の残りは一切変えない: `_final_agent_message`（最後の step が tool 呼び出しの無い agent 応答であること）・`_ends_with` / `_plain_tail`（stdout が回答で終わること）・`_failure_status` / `_export_failure`（認証・承認の診断）・`prepare` のプロンプト指示（`Return the final answer as one nonempty JSON object, without surrounding prose.` は現状のまま。指示だけでは文章の混入を防げないことが確認済み）
- `request_prompt()` は移植するが devin の `prepare` には接続しない（プロンプト指示は現状のままという Issue の指示）。`first_json_object()` は codex・cursor 展開（別 Issue）のために移植するだけで、ここでは使わない

### 移植に伴う挙動の変化（D3）

スクラッチ検証（SESSION の `scratch-verification.md`）で、既存の devin テスト・parser 回帰テスト 40 件が全て pass することを確認した。そのうえで、参照実装の挙動として次の 2 つの変化を受け入れる:

1. **閉じていない fence の中の完全な JSON**: 現行は拒否、移植版は採用する（例: `` ```json\n{"ok":true} ``）。fence が閉じていないとき、移植版のスキャナは fence を境界とみなさず通常の走査で完全な object を採用する。JSON 自体は途切れておらず、Issue の反例（JSON が途中で切れている・壊れた候補）に当たらない。既存の回帰テスト `test_devin_fence_failure_in_either_channel_is_read_only` は `_ends_with` の経路で失敗するため pass し続ける（このテストの守りは collect の読み取り専用性であり、パーサの fence 判定ではない）
2. **空 object `{}`**: 現行は拒否、移植版は adapter 層で success（payload `{}`）にする。ただし runner は `result_shape == "json"` のとき payload が空でない dict であることを必須で検査し（`tools/agent_runner/runner.py` の `isinstance(payload, dict) and bool(payload)`）、空なら `payload_check` の有無によらず `invalid_result` にする。さらに helper の `payload_check`（`TaskResult.model_validate` など）も必須フィールドの欠落で拒否する。したがって誤った成功にはならない。プロンプトの「空でない JSON object」指示は現状のまま

devin 層に fence の閉じ確認や空 object の拒否を足さない（境界ロジックの書き直しになり、移植の指示に反する）。

### ドキュメント（D6）

- `tools/agent_runner/runtimes/devin.rst` の「観測する情報と完了条件」の JSON の行（39 行目付近）を、移植後の挙動に更新する: 最終 ATIF 応答は `json_result.json_object` で読み、文章の後に JSON が続く形を受け付け、最後にデコードできた JSON object を採用すること、壊れた object 候補は応答全体を拒否すること（前の有効な JSON にフォールバックしない）、閉じたインラインコード span・閉じた非 JSON fence の中の壊れた候補は拒否に使わないこと、最後の発話だけ読む隔離は変わらないことを書く。「空でない JSON object であることを求め」の記述は D3.2 に合わせて直す
- `devin.py` のモジュール docstring に、回答の読み取りが `json_result.json_object` であることを短く追記する

### テスト（D5）

AGENTS.md の「テストの採用基準」に従う。守りはそれを実装しているモジュールのテストに置き、同じ守りの層またぎ重複は代表 1 件にする（設計レビュー concern D1 の採用。下の「設計レビュー記録」）。パーサ（`json_result`）が実装する拒否境界は `json_result` の単体テストに、devin が実装する隔離と runner 経路の救済は devin のテストに置く。偽の CLI のケースは既存の fixture 機構（`--fake-export` / `--fake-stdout`）で駆動する（`fake_cli.py` 自体は変更しない）。

**A. `json_result` の単体テスト（新設 `tools/agent_runner/tests/adapters/test_json_result.py`）** — パーサが実装する拒否境界の S 代表 1 件ずつと、拒否テストに伴う陽性の対照 1 件:

- U1: 閉じた fence 内の壊れた wrapper に完全な内部 object がある場合は `None`（内部・直前の有効 object を救済しない。agent-workspace の `test_collect_rejects_complete_result_inside_malformed_wrapper` のパーサ層への移植）
- U2: fence をインラインスパンが横切る壊れた訂正は `None`（`test_collect_rejects_broken_correction_inside_fence_crossed_by_inline_span` のパーサ層への移植）
- U3: 有効な object の後に途切れた候補がある場合は `None`（前の有効な JSON にフォールバックしない）
- U4: 文章 → 有効 object はその object を返す（U1〜U3 の拒否テストに対する「正しく通る例」。何でも拒否する実装で通らないようにする AGENTS.md の要件）

**B. devin のテスト（`tools/agent_runner/tests/adapters/devin/test_adapter.py` に追加）** — devin が実装する隔離と、実際の損害が起きた runner 経路の救済:

- T1: 最後の発話が文章だけで、途中の発話に JSON がある場合は `response_failed`・payload None（#188 の隔離。agent-workspace の collect の穴を持ち込まないことの代表。devin の `_final_agent_message` / `collect` が実装する守り）
- T2: `run_workflow` + 偽 CLI の端到端。Issue が指定する受け入れ 3 形（文章 → JSON・文章 → fence 付き JSON・訂正）をパラメータ化 1 件にまとめ、attempt が success で payload が最後の有効 JSON と一致することを確かめる（`test_retained_export_with_secrets_is_redacted_before_collection` と同じ起動機構。訂正は agent-workspace の `test_collect_uses_corrected_json_result` の適合）。陽性の対照であり、壊れると完了した作業が再び捨てられる＝本 Issue の損害の再発防止

重複の回避（D）: 受け入れ 3 形は T2 の偽 CLI 端到端 1 件に集約し、adapter 層の `_collect` で同じ救済を重ねない（設計レビュー concern D1）。既存テストがカバーする形（plain object・fenced object・配列の拒否・壊れた object の拒否・stdout の途切れ・診断の優先）は追加しない。`first_json_object`・`request_prompt` はこの Issue で使う経路が無いのでテストを足さない。D3 の 2 つの挙動変化を固定するテストも足さない（Issue の受け入れ条件の範囲外。rst に挙動を記載する）。

RED の確認: T2 の受け入れ 3 形は現行パーサで失敗する（救済の対象）。U1〜U4 は移植する `json_result` の単体テストなので、移植後はそのまま pass する（パーサの拒否境界が保たれることの確認）。T1 は現行でも pass する隔離の守りであり、移植で穴が開かないことを確かめる（移植前後で green を維持する）。

## 決定記録

| # | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | agent-workspace @ f65dd6a2 の `json_result.py` を byte 一致で移植 | (a) `_json_object` を拡張して末尾の fence 付き塊も受ける (b) 正規表現で最後の JSON を探す (c) プロンプト指示で運用回避 | Issue 本文が (a)〜(c) を破棄し、実運用で鍛えられた実装の移植を指示。書き直しは fence・インラインコード境界の回帰を招く | Issue 本文の対応方針（明示指示） |
| D2 | `_payload` を `json_object` + `is not None` に置換。隔離（最後の発話のみ・`_ends_with`）は維持 | stdout 全体を走査する agent-workspace の collect をそのまま移植 | Issue が隔離の維持を指示。stdout 走査は「最後の発話が文章だけ・途中に JSON」で古い JSON を拾う穴がある（Issue で実行確認済み） | Issue 本文の組み込み方（明示指示） |
| D3 | 参照実装の挙動を受け入れる（閉じていない fence の完全な JSON の採用・空 object の adapter 層 success）。devin 層の追加ガードなし | devin 層に fence の閉じ確認・空 object 拒否を足す | スキャナを書き直さない指示。既存テスト 40 件は pass（スクラッチ確認）。空 object は下流の payload_check が拒否し誤った成功にならない。閉じていない fence の JSON は途切れていない | 推奨案（issue-to-pr の委任）。設計レビューで確認 |
| D4 | `request_prompt`・`first_json_object` も移植するが接続しない | devin の prepare を `request_prompt` に切り替える | Issue が「プロンプトの JSON 指示は現状のまま」と指示。他 adapter への展開は別 Issue | Issue 本文（明示指示） |
| D5 | パーサの拒否境界 U1〜U4 を `test_json_result.py`（新設）に、devin の隔離 T1 と受け入れ 3 形の偽 CLI 端到端 T2（パラメータ化 1 件）を devin のテストに置く。未使用関数・D3 固定テストは作らない | 当初案: T1〜T7 をすべて devin のテストに置き単体テストを作らない | AGENTS.md の「守りはそれを実装しているモジュールのテストに置く」「D は代表 1 件」。設計レビュー concern D1 を採用（テスト配置のみの変更で、実装範囲・受け入れ条件・挙動は変わらない）。Issue の「偽の CLI にこれらのケースを追加」は受け入れ 3 形の T2 で満たす | Issue 本文のテスト指示 + AGENTS.md のテスト採用基準 + 設計レビュー concern D1 の採用 |
| D6 | devin.rst と devin.py docstring を移植後の挙動に更新 | ドキュメント変更なし | 挙動の説明（「空でない JSON object であることを求め」）が実装と食い違うため | 推奨案（issue-to-pr の委任） |
| D7 | 検証は `uv run pytest tools`（全体）+ `bash .devcontainer/run-tests.bash` + `bash scripts/check-layout.sh` + 実 evidence の再生。実 devin CLI は起動しない | 実 devin CLI での再現確認 | Issue の動作環境が「偽の CLI でのテストと、手元に残る実際の出力」。実 CLI 起動は費用がかかり、受け入れ条件は偽 CLI と記録でカバーできる | Issue 本文の受け入れ条件・検証 |
| D8 | 実行方式は SDD 形で `implement_task.py` により Task を 1 つずつ runner の担当（pi_alibaba_qwen4-max_max）に依頼。Task 1 = 移植 + 組み込み + テスト + ドキュメント（TDD を 1 Task 内で完結）、統合検証は controller が実行 | Task を移植とテストに分割 / controller が self で実装 | `--implement pi_alibaba_qwen4-max_max`（check の `self: false`）。TDD の RED/GREEN は同一 Task でないと成立しない。変更は 5 ファイル（`adapters/json_result.py` 新設・`tests/adapters/test_json_result.py` 新設・`adapters/devin.py`・`tests/adapters/devin/test_adapter.py`・`runtimes/devin.rst`）に凝集している | 利用者の `--implement` 指定 |
| D9 | main の追随は fast-forward に限り、再捕捉 → rebase → 再検証で続行 | base 移動で常に停止（スキルの既定） / 非 FF も追従 | 利用者が「途中でメインがマージされたら、追随して作業を止めずに続行」と明示指示。マージによる前進（祖先関係あり）に限り、履歴の書き換えは停止条件のまま | 利用者の自然文の明示指示。非 FF は停止 |
| D10 | `MAAS_ANTHROPIC_TOKEN` を `ANTHROPIC_AUTH_TOKEN` からワンショットで渡す | env ファイルに書く / 永続 export | 利用者の明示指示。README の規則（env ファイルに書かない・使うシェルで export）と整合。runner は起動時環境から子の環境を作るため、起動コマンドへの前置きで届く | 利用者の自然文の明示指示 |

### 担当の検査結果（2 章の 3 の helper 出力の転記）

- `loop.py check-options`（終了コード 0）: `options.max_cycles = 3`（既定の適用）、`options.assign = {implement: [pi_alibaba_qwen4-max_max], inspect: [pi_alibaba_qwen4-max_max, claude-code_sonnet_xhigh]}`（利用者の指定）、`options.template = /workspaces/reso-world/.devcontainer/agent-runner.toml`、`options.config = null`。`assignments`: review.inspect = 上記 2 担当（fallback なし）、fix.implement = pi_alibaba_qwen4-max_max（fallback なし）、fix.self-review = self、fix.fix-check = self（既定の適用）
- `implement_task.py check --implement pi_alibaba_qwen4-max_max`（終了コード 0）: `assignment.agents = [pi_alibaba_qwen4-max_max]`（利用者の指定）、`fallback = []`、`self = false`
- `review_design.py check --design-review pi_openai-codex_gpt6-sol_xhigh`（終了コード 0）: `assignment.agents = [pi_openai-codex_gpt6-sol_xhigh]`（利用者の指定）、`fallback = []`、`self = false`
- `review_spec.py check --spec-review pi_alibaba_qwen4-max_max`（終了コード 0）: `assignment.agents = [pi_alibaba_qwen4-max_max]`（利用者の指定）、`fallback = []`、`self = false`

### 設計レビュー記録（1 回目・採用反映済み）

- review_dir: `/workspaces/reso-world/tmp/agents/issue-406.95mq71g7/2026-11-12-issue-406-devin-json-result-design.design-review/review-1`（SESSION の下。コミットしない）
- review_id: `939a5e1952954da1bfd920f30a447cbb`
- reviewed spec sha256: `f62af03918dd4c8b20e3611538deed5c548001e7745095b12150003e12f72462`
- 担当: `pi_openai-codex_gpt6-sol_xhigh`（明示値）。requested_agent / actual_agent とも同じ。fallback の使用なし（fallback は空）
- identity: model `gpt-6.1-sol` / provider `openai-codex` / effort `xhigh` / session `01a1cc32-f7ca-7790-bc8a-0a02efb6ee8a`
- 回数: 1 回目（round 1）。elapsed_seconds: 195.33
- verdict: `concerns`（concern 1 件・questions_for_user なし・incomplete なし）
- outside_changes: なし。unprotected_changes: 他セッションの worktree 8 件（`/tmp/pr-review-376-*` の 4 件、`/tmp/review-fix-planning.*` の 2 件、`.worktrees/issue-355-herdr-merge`、`tmp/agents/issue-396.z5hf2du1/.../worktree`）。この run の所有物ではないため触らない（報告のみ）
- 採否: concern D1（テスト配置・severity worth_considering・recommendation change）を **採用**（`changes_what_is_built: false`）。パーサが実装する拒否境界を `json_result` の単体テスト（U1〜U4）に移し、受け入れ 3 形を偽 CLI 端到端のパラメータ化 1 件（T2）に集約して T1/T7 の層またぎ重複を解消した。devin の隔離テスト（T1）は維持。D5 とテスト節に反映済み。assessment の「空 object は runner の必須検査で拒否される」を確認し（`runner.py` の `isinstance(payload, dict) and bool(payload)`）、D3.2 の根拠に追記した

### Spec レビュー記録（1 回目・採用反映済み）

- review_dir: `/workspaces/reso-world/tmp/agents/issue-406.95mq71g7/2026-11-12-issue-406-devin-json-result-design.spec-review/review-1`（SESSION の下。コミットしない）
- review_id: `f316bf07f677461aa77555e18f4ec8cd`
- reviewed spec sha256: `ee05a377768273fdf0ad40ae488ff3bfe732b682fd5e8bb3079843a6c1f76ff7`（設計レビュー反映後のコミット `c4ce1a31` の版）
- 担当: `pi_alibaba_qwen4-max_max`（明示値）。requested_agent / actual_agent とも同じ。fallback の使用なし（fallback は空）
- identity: model `qwen4-max-preview` / provider `alibaba` / effort `max` / session `01a1cc3b-2202-722e-baed-bf662232e33d`
- 回数: 1 回目（round 1）。elapsed_seconds: 610.29
- status: `completed`（findings 3 件・すべて minor・incomplete なし）
- outside_changes: なし。unprotected_changes: 他セッションの worktree 12 件（`/tmp/pr-review-376-*` 4 件・`/tmp/review-fix-planning.*` 2 件・`.worktrees/issue-355-herdr-merge`・`.worktrees/issue-382-claude-bash-timeout-cap`・`.worktrees/issue-396-flaky-deadline-test`・`tmp/agents/issue-355.*` / `issue-382.*` / `issue-402-update.*` の runner worktree 3 件）。この run の所有物ではないため触らない（報告のみ）
- 採否: 3 件すべて **採用**（いずれも minor・表記/自己完結性の修正で設計の意味は変わらない）
  - S1: 検証の計画 4 の「コミットするテストは T1 が同じ形を代表する」を T2 に修正（D1 採用後の番号取り残し）
  - S2: D1 に期待 sha256・参照コピーのパス・再取得手順を明記し、検証の計画 5 を固定値との照合に修正
  - S3: D8 の「4 ファイル」を「5 ファイル」に修正しファイル名を列挙
- important の採用は無いため再レビューは行わない（helper の gate は plan へ）

### 競合の確認（2 章の 6）

- open PR: なし（全ページ確認）。#406 のマージ済み PR: なし（検索で当たった #381・#405・#403 は関連するだけの別 Issue の PR）
- `refs/heads/agent-claims/issue-406`: なし（issue-354 のみ）
- `issue-406` に一致する worktree・ローカル/remote branch: なし
- 未完了の先行 Issue・必要な未マージ PR: なし（#188・#402・#401 はマージ済み）
- 要求 base: 親 Issue・handoff ともになし（`required-bases.txt` は空）

## 編集の禁止

- 他 adapter（`claude_code.py`・`codex.py`・`cursor.py`・`pi.py`）と、それらのテスト・ドキュメント
- `collect` の隔離と診断のロジック（`_final_agent_message`・`_ends_with`・`_plain_tail`・`_failure_status`・`_export_failure`）と `prepare` のプロンプト指示
- 移植した `json_result.py` のスキャナ（byte 一致の移植）
- runner 本体・設定・issue-to-pr / review-fix-planning の helper
- CI ワークフロー（作成・有効化しない）

## 検証の計画

1. Task 1 の RED: T2 の受け入れ 3 形が現行パーサで失敗することを実行で確認（T1 の隔離は現行でも pass）
2. Task 1 の GREEN: `uv run pytest tools/agent_runner/tests/adapters/devin tools/agent_runner/tests/adapters/test_json_result.py tools/agent_runner/tests/adapters/test_parser_regressions.py -q` が全て pass
3. 統合検証（controller）: `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`
4. 実 evidence の再生: `tmp/agents/issue-402.ht7fd2ih/task-2-failed-evidence/stdout.log` の最後の発話（文章 → JSON）を移植後の collect に通し、success で payload が受け取れることを確認（スクラッチまたは一時テストで。コミットするテストは T2 が同じ形を代表する）
5. 移植の正: `json_result.py` の sha256 が D1 の固定値 `a636a027b87cdfa095e838f30a0d4ba1ad49c22a4ba33225428c3f4368495bac` と一致
6. 検証の記録: `--merge` のため、検証した HEAD・`git status --porcelain` が空・各コマンドの argv と終了コード・ログの完全パスを SESSION に記録し、`finalize.py` の `--checks-file` の形でも保存する

## 持ち越し候補（この Issue ではやらない）

- 他 adapter（codex・cursor・claude_code・pi）への `json_result` 展開（Issue が別 Issue と指示）
- `first_json_object`・`request_prompt` の接続と、そのテスト