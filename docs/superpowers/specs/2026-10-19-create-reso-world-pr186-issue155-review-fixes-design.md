# PR #186（Issue #155）のレビュー修正の選別（1 回目）

- 文書管理・対象: `usaturn/create-reso-world`、PR #186（`feat/issue-155-review-fix-roles`）、Issue #155
- 状態: `completed`
- 実行許可: 利用者の `/issue-to-pr #155` と「`/issue-to-pr #155 --merge` 相当で進めて」（2026-10-19）。`--merge` 相当のサイクルの 1 回目として、親の main checkout（`8083a85`。review-fix-planning は `origin/main` `d581f06` と同じ内容）の review-fix-planning を完遂で実行した。結論 2 のマージと関連 Issue の更新まで許可されている。内容の承認ではない
- 現行 HEAD: `f400291c7b6a3554f88c503129f15e0805adcfbc`（PR の head）。base `origin/main` `d581f064c6a801449b33ba2dc41dd3813d21668f` は head の祖先
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#186-feat-issue-155-review-fix-roles/`
- planner: claude-opus-5-5（Claude Code）
- 関連: 実装の Spec `docs/superpowers/specs/2026-10-19-create-reso-world-issue155-review-fix-roles-design.md`

## レビュアーの構成

agent-runner の設定（雛形と個人設定）の `workflows.review` の inspect の 5 人を、runner で並行に起動した（2026-10-19 13:26–13:52Z）。

| レビューファイル | モデル（ランタイム） | レビュー HEAD | Mode | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol（pi） | `f400291c7b6a` | Initial | はい | Approve |
| `claude-opus-5-5.md` | claude-opus-5-5（claude-code） | `f400291c7b6a` | Initial | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max（devin） | `f400291c7b6a` | Initial | はい | Approve |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash（dsh） | `f400291c7b6a` | Initial | はい | Approve |

- `pixg`（grok-4.7、pi）は、起動の直後に xAI の API が「クレジット切れ（403）」を返して終わり、レビューファイルは無い（runner の状態は `awaiting_authentication`。外部の障害）
- `devin-swe` は、helper がレビューファイルを保存したが、runner の応答の回収は `response_failed` だった（最終の JSON の形の問題）。レビューファイルは helper の検査を通って保存されているので、入力に含めた
- 前のサイクルの判断の記録は無い（1 回目）

## 全指摘と分類

分類: 解消済み 0 / 対応する 0 / 対応しない 3

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| `claude-opus-5-5#I-1@f400291c7b6a` 評価の記録が、載せ直しの前の commit（`a1c6cc4`・`f67a628`）を参照している | 対応しない | 事実として正しいが、評価した版は記録の SHA-256 で特定でき、載せ直しの後の commit（`724d4e9`・`72b243d`）は PR の Plan の「実行の記録」に残っている。誤った結果・停止にならない（致命的でない） |
| `claude-opus-5-5#U-1@f400291c7b6a` cursor の担当を self-review・fix-check に割り当てると、ask モードで helper を動かせず 1 回枠だけを消費する疑い | 対応しない | 既定の割り当て（`self`）では起きず、個人設定・`--assign` で cursor を選んだときだけ。起きても、予約の後の自己レビューが終わらずに結論 3 で止まる側に倒れ、誤ったマージ・データの消失・秘密の露出は起きない。cursor の ask モードでシェルを動かせないかは、Context7 の Cursor CLI の文書（2 回の問い合わせ。`-p` は書き込みとシェルを含む全ツール、`--force` が無いと変更は提案だけ）から確定できず、実機の確認は Issue・Plan の範囲外（費用）。拒否する runtime の一覧は移植元と #156 の `loop.py` と同じ codex だけで、広げるかは inspect の役割（#150・#153）にも関わる設計の判断なので、#116 に申し送る |
| `commandcode-deepseek-deepseek-v4.1-flash#L-1@f400291c7b6a` `--spec-commit` の最終化の途中で、利用者が検証した HEAD のまま手でマージすると、`finalize.py` が `merged: false` の `stopped` を返す | 対応しない | コードで確かめた（`finalize.py` の `check_view` が head の不一致で止まり、`merged` の代入はその後）。発生には、記録の投稿の後・Spec の push の前に、利用者が同じ PR を手でマージする競合が要る。誤ったマージや Issue の誤った更新は起きず、停止の理由（HEAD が変わった）とマージの状態は `gh pr view` で確かめられる（致命的でない）。マージ済みの PR を異なる head で見たときに `merged: false` になる順序は、`--spec-commit` の無い経路にもあり、移植元から引き継いでいる。PR の説明の既知の制限に、条件と回避方法を書き足す |

## 確認の範囲

- 全 4 ファイルのレビューと、PR の全 16 ファイル（実装の担当として全文を読んでいる）。指摘の 3 件は、現行 HEAD のコミット済みの内容で確かめた（I-1: `a1c6cc4`・`f67a628` が head の祖先でないこと、L-1: `finalize.py` の順序、U-1: `tools/agent_runner/adapters/cursor.py` の `--mode ask` と文書）
- 確認中に、PR が持ち込んだ致命的な欠陥は見つからなかった（自己確認なし）

## 結論

結論 2（修正不要としてマージ）。

- 検証: PR の head `f400291` で `uv run pytest tests/skills .agents/skills .agents/scripts tools`・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/review-fix-planning`（結果は下）
- base: `origin/main` は head の祖先なので、base を merge した一時的なツリーでの検証は不要
- CI: create-reso-world は private で CI を止めているため確かめない（AGENTS.md）
- マージしてよい範囲: `usaturn/create-reso-world` の open で draft でない PR
- 自己レビュー: 修正が無いので行わない
- 修正不要のマージは、親の main checkout の review-fix-planning（この PR より前の版）の手順で行う（`gh pr merge --merge --match-head-commit`）。この PR の `finalize.py` は、変更中のスキルなので使わない

## 実行した検証と結果

- PR の head `f400291c7b6a3554f88c503129f15e0805adcfbc`（2026-10-19 13:54–14:13Z、ログは `/workspaces/reso-world/tmp/agents/issue-155.8zy2dh0_/verify3/`）
  - `uv run pytest tests/skills .agents/skills .agents/scripts tools`: 3214 passed（終了コード 0、警告なし）
  - `bash .devcontainer/run-tests.bash`: 33 本 PASS（0）
  - `bash scripts/check-layout.sh`: PASS（0）
  - `env AGENT_RUNNER_DEPTH=1 uv run pytest .agents/skills/review-fix-planning`: 305 passed（0）
- この Spec だけの commit は、上の検証の後に PR の head に載せる（検証した head の直接の子で、変更はこの 1 ファイルだけ）
