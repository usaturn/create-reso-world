# Issue #341: Devin の agent 名を devin_swe2_max に直し、SWE-2 Medium を追加する

## 管理・実行許可

- 状態: `draft`（issue-to-pr の実行許可で進める。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/341（取り込み元は usaturn/agent-workspace#858、移植元は PR #859・マージコミット `b7bd40743b76716801be184cb4401efb9b664256`）
- 利用者の指示（Claude Code の `/issue-to-pr`）: `https://github.com/usaturn/create-reso-world/issues/341 --merge --implement claude-code_sonnet_default --assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`
  - 1 回目の指示（`--assign inspect=pi_openai-codex_gpt6-sol_xhigh`）は、agent 名が設定に無く `check-options` が `invalid_reference` で止まった。worktree 等は作らずに止め、利用者が名前を直して指示し直した
- 許可された範囲: 通常の設計判断を推奨案で決めること、Spec・Plan、実装（Task は runner の担当に依頼）、課金の無い検証、commit・push・PR の作成、指定の PR 修正ループと、その中の `finalize.py` によるマージ・関連 Issue の更新。個人設定・認証情報は変えない。本物の担当の起動は、Plan に書いた Task の実装依頼とループのレビュー・修正に限る
- 固定した base: usaturn/create-reso-world / origin / `refs/heads/main` / `25b7b5a020e5f67d74807534e1b3390a54c9c5b1`（Issue が現状を確かめた SHA と同じ）。親 Issue・要求 base・先行 Issue・既存 PR・予約は無い
- 文書の置き場所: create-reso-world 自身の変更なので、Spec・Plan はコードと同じ worktree・PR に入れる（`DOCS_SEPARATE=false`）

## 目的

Devin の agent 名を、ほかの agent と同じ命名規則に揃える。今の `devin_swe2-max_default` は、effort の軸である `max`（SWE-2 の tier）を model の段に置き、effort の段を `default`（runtime の既定に任せる）にしているので、max を明示しているのに既定任せと読める。同じ構造の `cursor_grok4_xhigh`（`model = "grok-4.7-xhigh"`）は slug の実効値を effort の段に置いている。あわせて SWE-2 Medium を `--assign` で選べるようにする。

## 現状（base で確認した事実）

- `.devcontainer/agent-runner.toml` の Devin の agent は `devin_swe2-max_default`（`model = "swe-2-max"`、`model_key` なし）だけで、既定の `[workflows.review.assignments.inspect]` が参照している
- 旧名を参照する現行の記述は `.devcontainer/agent-runner.toml` と `.devcontainer/README.md` だけ（`docs/superpowers/` の過去の Spec・Plan、`.agents/skills/issue-to-pr/evals/validation.md` の当時の記録、テストの入力例 `devin-swe` を除く）
- この環境の個人設定 `~/.config/agent-runner/config.toml` に Devin の agent 名は無い
- `devin models list`（devin 3000.12.28、2026-11-08T08:34:41Z）の SWE-2 は `swe-2-high`・`swe-2-medium`・`swe-2-max` と `-lightning` の 3 つ。記録は親 checkout の `tmp/agents/issue-341.8ff800qg/devin-models-swe2.txt`
- Devin の adapter は `--model <agent.model>` だけを渡し、effort を渡す引数は無い。名前の付け方はこの制約とは別に決める
- 同一モデルの判定（`tools/agent_runner/config.py`）は、agent ごとに `{model}`、`model_key` があれば `{model, model_key}` の比較集合を作り、同じ役割の候補間に共通要素があれば `duplicate_model` で拒否する。既存の `tools/agent_runner/tests/test_config.py` が `model_key` の比較を確かめている

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 改名 | `devin_swe2-max_default` を `devin_swe2_max` に改名し、`model_key = "swe-2"` を付ける | 旧名を残して新名を足す／旧名の alias を作る | Issue の対応内容 1。alias・旧名の併存は Issue の対象外 | 推奨案での委任 |
| Medium の追加 | `devin_swe2_medium`（`runtime = "devin"`、`command = ["devin"]`、`model = "swe-2-medium"`、`model_key = "swe-2"`、`env = ["HOME", "PATH"]`）を足す。既定の割り当てには入れない | `swe-2-high` も足す／既定のレビュアーに入れる | Issue の対応内容 2。high と lightning は対象外。既定の構成は変えない | `devin models list` に `swe-2-medium` が無ければ追加をやめて報告する（2026-11-08 に有ることを確認済み） |
| 既定のレビュアー | `[workflows.review.assignments.inspect]` の 2 人目だけを `devin_swe2_max` に直す。順序と他の 2 人は変えない | 構成を見直す | Issue の対応内容 1（既定の構成は変えない） | 推奨案での委任 |
| 雛形のコメント | Devin の 2 agent の前に、SWE-2 の tier を `--model` の UID で選ぶこと、tier を名の effort の段に置くこと、同じ `model_key` で同じ役割に並べられないことを短く書く | コメントを書かない | 移植元と同じく、名前の意図を雛形の中で読めるようにする | 推奨案での委任 |
| 命名規則（README） | 「agent の命名と同一モデルの比較」の規則に、tier はモデルの種類（`sol`・`flash` など）を指し、slug に含まれる effort の軸の tier（Devin の `swe-2-max` の `max`、Cursor の `grok-4.7-xhigh` の `xhigh`）は model の段に入れず effort の段に置くこと、effort は設定値 → slug に含まれる実効の effort → `default` の順で決めることを足す。例に `devin_swe2_max` を加える | 移植元の README の節をそのまま写す | 移植元とは README の構成が違う（本リポジトリの節は箇条書きでなく段落）。構成を保って差分だけ取り込む（Issue の目的） | 推奨案での委任 |
| 既定のレビュアー・`model_key` の説明（README） | 既定の `review.inspect` の記述を新しい名前に直し、`model_key` の段落に SWE-2 の 2 agent を足す。Medium は既定に入っておらず `--assign` で選べること、`devin_swe2_max` と同じ役割に並べられないことを書く | 「追加する 5 agent」の表に Medium を足す | その表は当時の追加の記録として読めるので触らず、現在の説明の段落に書く | 推奨案での委任 |
| 旧名からの移行（README） | 「Command Code GOAT の契約終了後の移行」の後に新しい節を作り、`devin-swe`・`devin_swe2-max_default` から `devin_swe2_max` への移行を書く。#305 の旧名対応表は書き換えない。個人設定に旧名の `[agents.*]` を残すと雛形の `model_key` を継承せず、`devin_swe2_medium` と同じ役割に並べても拒否されないこと、旧名の節を消して雛形を継承させる手順も書く | #305 の表の行を書き換える／#305 の移行の節に追記する | Issue の対応内容 4。#305 の表は当時の変更記録。節を分けると、#340（同じ README の別の節）とも重ならない | 推奨案での委任 |
| 過去の記録 | `docs/superpowers/` の Spec・Plan、レビュー・実行記録、`evals/validation.md`、テストの入力例の agent 名は書き換えない | 一括で置換する | Issue の対応内容 5 | 推奨案での委任 |
| ランチャー | `.devcontainer/zshrc.txt` の `dev`（`devin --model swe-2-max`）などの名前・引数は変えない | 合わせて直す | 命名規則はランチャーの実行ファイル名や実際の model ID を改名しない（README の既存の規則） | 推奨案での委任 |
| テスト | 新しいテストは書かない。名前の誤りは `check`・`list` と雛形の読み込みでエラーになる（L）。`model_key` の比較は既存の `tools/agent_runner/tests/test_config.py` が確かめている（D）。README の文言は F | 雛形の agent 名・既定の構成を照合するテストを書く | Issue の受け入れ条件と AGENTS.md の「テストの採用基準」 | 推奨案での委任 |
| Task の実装の担当 | `implement_task.py check --implement claude-code_sonnet_default` の出力は `assignment = {"agents": ["claude-code_sonnet_default"], "fallback": []}`、`self = false`。担当は利用者の指定（`--implement`）、`fallback` が空なのは個人設定・雛形の値の適用 | self で実装する | `self = false` なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task を 1 つずつ順に依頼する | 依頼が `failed` か、再試行の上限に達した `retry`・`rejected` なら、その Task で止まり、self で引き取らない |
| 統合の確認 | 共有する条件（雛形の名前と README の記述の一致、設定の読み込み、同一モデルの判定）は、司令塔（self）が統合担当として確かめる | 各 Task の担当に任せる | 2 つの Task が同じ名前・同じ判定に依存する | 検証の失敗が解消しなければ止まる |
| PR 修正ループ | `loop.py check-options` の出力: `max_cycles = 3`（既定の適用）、`assign = {"implement": ["claude-code_sonnet_default"], "inspect": ["pi_openai-codex_gpt6-sol_max"]}`（利用者の指定）、`template = .devcontainer/agent-runner.toml`（既定の適用）、`config = null`。割り当ては review.inspect = `pi_openai-codex_gpt6-sol_max`、fix.implement = `claude-code_sonnet_default`（どちらも利用者の指定）、fix.self-review・fix.fix-check = `self`（既定の適用）、fallback はすべて空 | ループの既定の構成を使う | 利用者が書いたループ用のオプションだけを、書いた順に渡す | ループの停止・エラーでは止まる。ループは親 checkout の `loop.py` と旧雛形を使い、レビュアー・修正の担当は明示の指定なので、改名の影響を受けない |
| Issue の指定 | PR 本文は `Closes #341` | `Refs #341` | 受け入れ条件はどれもマージ前にローカルで確かめられ、rebuild・実機・個人設定の移行は要らない（この環境の個人設定に Devin の名前が無い） | 推奨案での委任 |

## 要件と防御範囲

| # | 条件 | 観測する結果 |
| --- | --- | --- |
| R1 | 雛形に `devin_swe2_max`（`model = "swe-2-max"`、`model_key = "swe-2"`）と `devin_swe2_medium`（上の決定記録の値）が定義され、`devin_swe2-max_default` が残っていない（README の移行の説明・#305 の表と、`docs/superpowers/` など過去の記録を除く） | 雛形の読み込み結果と `git grep` |
| R2 | 既定の `[workflows.review.assignments.inspect]` が `["pi_openai-codex_gpt6-sol_max", "devin_swe2_max", "pi_opencode-go_deepseek4-flash_max"]` で、ほかの割り当ては変わらない | 雛形単独と実際の個人設定を重ねた実効の割り当て |
| R3 | リポジトリのルートで `uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner check` と `list` が成功し、2 つの agent が表示される | 終了コード 0 と `list` の出力 |
| R4 | 一時的な個人設定（`AGENT_RUNNER_CONFIG` で指す、コミットしないファイル）で 2 つを同じ役割に並べると、`check` が `duplicate_model` で止まる。反例として、どちらか 1 つだけをほかのモデルと並べた設定は受け入れられる | 終了コードと reason |
| R5 | 個人設定に旧名の `[agents.devin_swe2-max_default]`（`model = "swe-2-max"`、`model_key` なし）を残して `devin_swe2_medium` と同じ役割に並べると拒否されない（README に書く挙動が実際と一致する） | 一時的な個人設定での `check` の結果 |
| R6 | README の命名規則・既定のレビュアー・`model_key` の説明・移行の節が上の決定記録のとおりで、#305 の表は変わらない | `git diff` と記述の読解 |
| R7 | ルートの `README.md` の「テスト」にある `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` が通る | 終了コード 0 |

防御範囲: 同じ役割に同じ SWE-2 を並べる誤りを `model_key` で起動前に止める。対象外は、個人設定に旧名の定義を残した場合（雛形の `model_key` を継承しないので止まらない。README で移行を案内する）と、`swe-2-high`・lightning 系（定義しない）。

## 対象外

- 移植元 PR #859 に含まれる、本リポジトリに無いほかの改名（`claude-code_opus_xhigh`・`pi_openai-codex_gpt6-sol_xhigh` など）
- `swe-2-high` と `-lightning` 系の agent
- 個人設定の自動の書き換え、旧名の alias
- 過去のレビュー・実行記録・`docs/superpowers/` の Spec・Plan の書き換え
- 本物の Devin を起動する確認（`devin models list` の読み取りだけ行う）
