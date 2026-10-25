# Issue #265: AGENTS.md の SDD の作業領域の手順を補う

- 状態: completed（PR #267 のサイクル 1 で修正不要と判断した。末尾の「PR #267 のレビュー修正（サイクル 1）」）
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #265](https://github.com/usaturn/create-reso-world/issues/265)
- 検証したコードの HEAD: `origin/main` `115f7c3065c422e121c5617289f0181d39f85773`（2026-10-25T02:00Z ごろの着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue265-sdd-workspace-steps.md`
- 関連: #132・PR #262（`AGENTS.md:180` の手順を足した。確認済みの一覧 `reviews/usaturn/create-reso-world/#262-fix-issue-132-sdd-workspace-outside-worktree/verified/a35e109cf64f.json` の V-1・V-2・V-4）、Spec `docs/superpowers/specs/2026-10-25-create-reso-world-issue132-sdd-workspace-outside-worktree-design.md`
- 実行許可: 利用者の `/issue-to-pr #265 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

`AGENTS.md` の「SDD 実行運用」の、superpowers の作業領域を `tmp/agents/<topic>.XXXXXX/sdd/` に置く手順（PR #262）を、そのとおりに実行して止まらず、スキルの決まりと食い違わない形に補う。

## 着手時の確認

1. superpowers の版は、Claude Code が 7.0.0、Codex・pi・Devin が 7.0.1。`task-brief`・`review-package`・`task-done` は、Claude Code・Codex・pi・Devin の 4 か所とも同じ内容（`cmp` で一致）だった
2. `task-brief PLAN N [OUTFILE]` と `review-package PLAN BASE HEAD [OUTFILE]` は、OUTFILE の親ディレクトリを作らずに `> "$out"` で書く（`task-brief` の 36 行目、`review-package` の 50 行目）。`agent_tmp.py mkdir` はセッションディレクトリだけを作るので、今の手順では最初の `task-brief` が終了コード 1 で止まる（Issue の背景 1、V-2）
3. スクリプトの既定の出力先は、`sdd-workspace` が決める `.superpowers/sdd/<plan>/`（`<plan>` は `basename PLAN .md`）の下の `task-<N>-brief.md` と `review-<base7>..<head7>.diff`（`git rev-parse --short`）。review package は範囲ごとの名前なので、修正後の再レビューで前のものを上書きしない
4. 完了の行の書式と条件は、7.0.0・7.0.1 とも次のとおり
   - executing-plans: `task-done` が Task のテストを実行し、終了コード 0 のときだけ `Task <N>: complete (commits <base7>..<head7>, tests: <command> → <result>)` を ledger に足す（`<result>` は出力の最後の空でない行）
   - subagent-driven-development: スクリプトを使わず controller が書く。Task のレビューが clean のとき `Task <N>: complete (commits <base7>..<head7>, review clean)`、修正の上限（5 回）で残りの指摘をすべて parked にしたとき `Task <N>: complete (commits <base7>..<head7>, <K> parked)`
   - 再開の判定は、どちらも ledger の 1 行目が自分の Plan を指し、行頭が `Task <N>: complete` の行で行う
5. 作業領域を Plan ごとに分けない今の `sdd/` では、同じセッションディレクトリで 2 つ目の Plan の Task 1 を同じ出力先に `task-brief` すると、終了コード 0 のまま 1 つ目の brief が置き換わる（V-4）。`sdd-workspace` は Plan ごとに `.superpowers/sdd/<plan>/` を分けている

## 変更の内容

1. `AGENTS.md` の「SDD 実行運用」の作業領域の項目（今の 180 行目）を次の内容に直す
   - 作業領域はセッションディレクトリの `sdd/<plan>/`（`<plan>` は Plan のファイル名から `.md` を除いた名前）にし、最初に `mkdir -p` で作る
   - `task-brief`・`review-package` に渡す出力先のファイル名は、スクリプトの既定（`task-<N>-brief.md`・`review-<base7>..<head7>.diff`）にする
   - 完了の行は、SDD は Task のレビューが clean か、上限で残りを parked にしたときにスキルの書式で、executing-plans は Task のテストが通ったときだけ `task-done` と同じ書式で書く
   - そのほか（使わないスクリプト、BASE の控え方）は今のまま
2. `AGENTS.md` の「コミットしないファイルの置き場所」の表の、superpowers の作業領域の行の置き場所を `tmp/agents/<topic>.XXXXXX/sdd/<plan>/` に直す

## 対象外

- superpowers の上流への提案（作業領域の場所を変える引数）
- repo-cleanup-after-merge の判定と手順 4 の文（`tmp/agents/` を指しており、今回の変更と食い違わない）
- `task-start`・`task-done` の代わりのスクリプト（#132 の D3 のまま）
- 新しいテスト（D6）

## 受け入れ条件

1. `AGENTS.md` の手順どおりに、新しいセッションディレクトリで `task-brief`・`review-package` を実行すると、終了コード 0 で、リポジトリ（作業する worktree の代わりの一時リポジトリ）に何も作られない。7.0.0 と 7.0.1 のスクリプトで確かめる（Issue の受け入れ基準 1）
2. 同じセッションディレクトリで 2 つ目の Plan の Task 1 の brief を作っても、1 つ目の Plan の brief と ledger が残る（Issue の背景 3）
3. 修正後の再レビューの review package は、前の review package を上書きしない（Issue の背景 4）
4. SDD と executing-plans の完了の行の条件と書式が、それぞれのスキル（7.0.0・7.0.1 の SKILL.md、`task-done`）の決まりと一致する（Issue の受け入れ基準 2）
5. 表の行と「SDD 実行運用」の項目が、同じ置き場所を指して食い違わない

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | `AGENTS.md` の作業領域の項目を 1 項目のまま直す（Issue の推奨） | (a) 作業領域の項目と ledger の項目の 2 つに分ける。(b) `sdd/` の作成と完了の行を担う補助スクリプトをリポジトリに作る | Issue の推奨のとおり。項目を分けると「SDD 実行運用」の構成が変わり、`AGENTS.md` の指示文を簡潔に保つ方針（Issue の「決めること」）にも反する。(b) は #132 の D3 と同じく保守とテストが増え、上流の版で引数が変わると食い違う | 委任: `/issue-to-pr #265 --merge --max-cycles 3` の推奨案での決定 |
| D2 | 作業領域を `sdd/<plan>/`（`<plan>` は Plan のファイル名から `.md` を除いた名前）にし、最初に `mkdir -p` で作る | (a) Plan ごとにセッションディレクトリを分ける。(b) `sdd-workspace` のように `plan-path` の印を書いて、同じ名前の Plan を区別する | `sdd-workspace` と同じ名前の付け方で、スキルの「この Plan の workspace」をそのまま読み替えられる。(a) は実行予算の ledger（`budget.jsonl`）とセッションディレクトリが 1 対 1 という `.agents/execution-budget.md` の前提と合わない。(b) は、Plan が `docs/superpowers/plans/` の 1 か所にあって日付付きのファイル名で一意なので要らない。ledger の 1 行目も Plan のパスを持つ | 委任: 推奨案での決定 |
| D3 | 完了の行は、SDD は Task のレビューが clean か、上限で残りを parked にしたときにスキルの書式で、executing-plans は Task のテストが通ったときだけ `task-done` と同じ書式で書く | (a)「完了の行はスキルのとおり」とだけ書く。(b) 今のまま（`task-done` の書式に統一） | executing-plans の「テストが通ったときだけ」は `task-done` が担っていた条件で、`task-done` を使わない以上、条件を書かないと失われる（PR #262 のブランチ全体のレビューの指摘 1）。SDD はスキルが完了の時点と書式を決めているので、条件を短く添えて書式はスキルに任せる。(b) は SDD のスキルと食い違う（V-1） | 委任: 推奨案での決定 |
| D4 | 出力先のファイル名はスクリプトの既定（`task-<N>-brief.md`・`review-<base7>..<head7>.diff`）にする | 名前を指定しない（今のまま） | 範囲ごとの名前にすると、修正後の再レビューの review package が前のものを上書きしない（着手時の確認 3）。SDD のスキルは報告のファイル名を brief の名前から作る（`task-N-brief.md` → `task-N-report.md`）ので、既定の名前に合わせると報告の名前もスキルどおりになる | 委任: 推奨案での決定 |
| D5 | 表の行の置き場所も `sdd/<plan>/` に直す | 表は `sdd/` のまま | 表と本文が別の場所を指すと、どちらに従うか迷う（受け入れ条件 5） | 委任: 推奨案での決定 |
| D6 | テストを書かない | 手順の文言や手順の実行を確かめるテストを足す | 変更は規則の文書だけで、文書の文言を写すテストは `AGENTS.md` の「テストの採用基準」の F（Issue の「検証」も同じ）。`sdd/` が無いときの失敗は終了コード 1 と `No such file or directory` で現れる（L）。代わりに、`AGENTS.md` に書いた手順のコマンドを一時リポジトリで実行し（受け入れ条件 1〜3）、README の「テスト」と `git diff` の確認を行う | `AGENTS.md` の「テストの採用基準」 |
| D7 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `.devcontainer/agent-runner.toml`、`--config` なし、inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #265 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D8 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形と個人設定の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #265 --merge --max-cycles 3`。`check` は終了コード 0 |

## PR #267 のレビュー修正（サイクル 1）

- 実行許可: 利用者の `/issue-to-pr #265 --merge --max-cycles 3` による PR 修正ループ（run `e199dded1c01465884bb198ba7b4570c`）の計画。review-fix-planning の完遂（修正不要なら `finalize.py` でマージし、関連 Issue を更新する）
- planner: claude-opus-5-5（claude-code）。サイクル 1、判断の対象の HEAD は `2fba571374c4999513d1869866df822edf13fdab`
- 入力: `reviews/usaturn/create-reso-world/#267-fix-issue-265-sdd-workspace-steps/` の 4 つのレビューファイルと `findings/*-2fba571374c4.json`（どれも `validate`・`check-pair` が 0）。確認済みの一覧 `verified/2fba571374c4.json`（review-verify、mode cycle）は confirmed 0・not_reproduced 0・unverified 0

| レビューファイル | モデル / ランタイム | レビュー HEAD | 今回再実行 | 推奨 |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `2fba571374c4` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max / devin | `2fba571374c4` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash / pi | `2fba571374c4` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 / cursor | `2fba571374c4` | はい | Approve |

### 指摘の分類（解消済み 0 / 対応する 0 / 対応しない 0）

4 人のレビュアーとも、指摘・未確認の候補は 0 件だった。前のサイクルの判断の記録は無い。「対応する」が無いので、「守る条件と影響経路」の表と設計の見直しは無い。

レビュアーが判断しなかった範囲は、確認済みの一覧で閉じた（Devin の 7.0.1 のスクリプトの実体、README の一括検証、空白・相対パス、同名の Plan、条件を述べる文書）。実装サブエージェントのある SDD を、実際のエージェントが新しい項目で最後まで進める挙動は、本物の担当を起動する確認になるので未確認のまま残る（executing-plans は、この Issue の issue-to-pr の run が新しい規則どおりに進めた）。

### 結論と検証

- 結論: 2（修正不要でマージ）
- 自己レビュー: 未実施（修正が無いため。`run_roles.py` は実行していない）
- 検証（検証の記録の `base` は下の先端）: base `main` の先端は、レビューの間に PR #266 のマージで `14a774b45953580f4a248b572d7542e02b4851b9` に進み、head の祖先ではなかった。head `2fba571` にその先端を一時の隔離 worktree で merge したツリー（`cd4ebc0`、競合なし。push しない）で、`bash .devcontainer/run-tests.bash` 0（23 test(s) PASS）、`bash scripts/check-layout.sh` 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` 0（1225 passed）、手順の確認 `verify-sdd-steps.bash` 0（7.0.0・7.0.1 とも ALL PASS）。検証の前後で、そのツリーに未 commit の変更は無かった。head だけのツリーでも、issue-to-pr の最後の検証で同じ 4 つが 0 だった
