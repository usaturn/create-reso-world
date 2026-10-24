# Issue #132: superpowers の SDD の作業領域を worktree の外に置く

- 状態: completed（PR #262 のサイクル 1 で修正不要と判断した。末尾の「PR #262 のレビュー修正（サイクル 1）」）
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #132](https://github.com/usaturn/create-reso-world/issues/132)
- 検証したコードの HEAD: `origin/main` `dcdc0d9adee1f4e6757c1e584ae5a581169b1ac5`（2026-10-24T19:10Z の着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue132-sdd-workspace-outside-worktree.md`
- 関連: #123・PR #130（worktree の中にコミットしないファイルを作らない規則）、#131・PR #190、PR #224・PR #257（作業領域を `tmp/agents/` に置いて進めた記録。Issue のコメント）
- 実行許可: 利用者の `/issue-to-pr #132 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

superpowers の subagent-driven-development・executing-plans の作業領域（ledger・Task の brief・報告・review package・テストのログ）が worktree の `.superpowers/sdd/` に残り、マージ後の repo-cleanup-after-merge がその worktree を消さずに止まる。`AGENTS.md` の「worktree の中に、コミットしないファイルを作らない」とも食い違う。作業領域の扱いを決め、`AGENTS.md` の規則と repo-cleanup-after-merge の手順をそろえる。

## 着手時の確認

1. superpowers の版は、Claude Code が 7.0.0、pi・Codex・Devin が 7.0.1。どの版も、スクリプトの引数は次のとおりで同じだった
   - `sdd-workspace PLAN_FILE`: `git rev-parse --show-toplevel` の `.superpowers/sdd/<plan>/` と `.superpowers/sdd/.gitignore` を作る。場所を変える引数・環境変数は無い
   - `task-brief PLAN_FILE N [OUTFILE]`（subagent-driven-development）と `review-package PLAN_FILE BASE HEAD [OUTFILE]`: OUTFILE を渡すと `sdd-workspace` を呼ばない
   - `task-start PLAN_FILE N`（executing-plans）: `task-brief` を OUTFILE なしで呼ぶ。`task-done PLAN_FILE N BASE -- CMD`: `sdd-workspace` を呼び、テストのログと ledger の行を作業領域に書く。どちらも場所を変えられない
2. 一時リポジトリで実行した（7.0.0）。OUTFILE を渡した `task-brief`・`review-package` は、どちらも終了コード 0 で、リポジトリに何も作らなかった。`task-start` は `.superpowers/sdd/.gitignore`・`.superpowers/sdd/p/plan-path`・`.superpowers/sdd/p/task-2-brief.md` を作った
3. PR #190・#224・#257 は、作業領域（PR #190 は ledger だけ）を `tmp/agents/` のセッションディレクトリに置いて進めた。PR #224・#257 は `review-package` に OUTFILE を渡した。マージの後、どの worktree にも `.superpowers/` は無かった（Issue のコメント）。PR #224 のコメントは `task-brief` に出力先の指定が無いとしていたが、確認 1 のとおり 3 つ目の引数で指定できる
4. repo-cleanup-after-merge の手順 4 は、`.superpowers/` を利用者の確認が要る ignore 対象に挙げ、毎回止まるなら生成側を worktree の外に出すよう求めている。Issue の「検証」にある `tests/test_repo_cleanup_after_merge_contract.py` は、#228 のテストの削減（`3fba20d`）で無くなっている
5. 実行予算の ledger は、すでに `tmp/agents/<topic>.XXXXXX/budget.jsonl` に置く決まりである（`.agents/execution-budget.md`）

## 変更の内容

1. `AGENTS.md` の「コミットしないファイルの置き場所」の表に、superpowers の作業領域の行を足す。置き場所は `tmp/agents/<topic>.XXXXXX/sdd/`
2. `AGENTS.md` の「SDD 実行運用」に、作業領域の使い方を 1 項目で書く。スキルの言う `.superpowers/sdd/<plan>/` の代わりにセッションディレクトリの `sdd/` を使う。`sdd-workspace`・`task-start`・`task-done` は使わない。`task-brief` と `review-package` は出力先を `sdd/` の下に指定する。BASE は Task の開始時に `git rev-parse HEAD` で控え、ledger（`progress.md`）の完了の行は、テストが通ったときだけ `task-done` と同じ書式で手で書く（`task-start`・`task-done` が担っていたことの代わり）
3. repo-cleanup-after-merge の手順 4 の「毎回ここで止まるなら…」に、`.superpowers/sdd/` の生成元（superpowers のスクリプト）と、`AGENTS.md` の「SDD 実行運用」が置き場所を定めていることを 1 文で書く。削除の判定は変えない

## 対象外

- 今残っている `.superpowers/` の片付け（Issue の範囲外。片付けのときに利用者の確認を得て行う）
- repo-cleanup-after-merge の削除の判定（`.superpowers/` は今までどおり利用者の確認が要る）
- superpowers の上流への提案（案 C）。持ち越し候補として PR に書く
- task-start・task-done の代わりのスクリプト（D3）
- 新しいテスト（D6）

## 受け入れ条件

1. `AGENTS.md` に従って SDD・executing-plans を使うと、作業領域が worktree に作られない（Issue の受け入れ基準の案 B の側）。`AGENTS.md` に書いた手順のコマンドを一時リポジトリで実行し、リポジトリに何も作られないことで確かめる
2. `AGENTS.md` の「コミットしないファイルの置き場所」の表・規則と食い違わない
3. repo-cleanup-after-merge の手順 4 が、`.superpowers/sdd/` を見つけたときに報告する生成元と直す先（`AGENTS.md` の「SDD 実行運用」）を示す。削除の判定は変わらない

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 案 B（作業領域を `tmp/agents/` のセッションディレクトリに置く手順を `AGENTS.md` に書く） | (A) Issue の本文の推奨。repo-cleanup-after-merge で、マージ済みの PR の worktree にある `.superpowers/sdd/` を worktree と一緒に消してよいものに加える。(C) 上流に提案し、入るまで A か B を使う。(A+B) 併用 | 本文の推奨は「作業領域の場所を変える引数・環境変数が無い」を前提にしていた。その後のコメントで `review-package` は出力先を指定でき（PR #224・#257）、3 つの PR が作業領域を `tmp/agents/` に置いて進められたと分かり、着手時の確認 1・2 で `task-brief` も指定できると分かった。B では `task-start`・`task-done` の機能（BASE の出力、テストが通ったときだけ完了の行を書くこと、テストのログの保存）を失う。BASE の控え方と、テストが通ったときだけ同じ書式で書く条件を `AGENTS.md` に書いて補う。B は `AGENTS.md` の規則に例外を作らず、片付けの削除ゲート（git 管理外のファイルを照合せずに消さない）を緩めない。A は、ledger の `Ruling:` の行など、まだ報告に写していない記録を照合なしで消しうる。B の手順を守らずに作業領域を作っても、今までどおり片付けが止まって利用者に確かめるので、記録を失う側に倒れない。A+B は削除ゲートを緩める点で A と同じ欠点を持つ。C は上流の採否と時期が分からず、Issue の受け入れ基準を満たせない | 委任: `/issue-to-pr #132 --merge --max-cycles 3` の推奨案での決定。受け入れ基準は A と B のどちらも認めているので、仕様の意味を変える判断に当たらない |
| D2 | 置き場所を `AGENTS.md` の「コミットしないファイルの置き場所」の表に、使い方を「SDD 実行運用」に書く | `.agents/execution-budget.md` に書く。新しい文書・スキルを作る | 置き場所の規則は `AGENTS.md` の表で一元管理しており、全ランタイムが読む。使い方は 1 項目で足り、別の文書にすると参照が増える | 委任: 推奨案での決定 |
| D3 | `sdd-workspace`・`task-start`・`task-done` を使わない。ledger と完了の行は手で書く | (a) task-start・task-done の代わりのスクリプトをリポジトリに作る。(b) `GIT_WORK_TREE` などで `--show-toplevel` を作業領域に向けて、元のスクリプトを使う | (a) は保守とテストが増え、上流の版で引数が変わると食い違う。(b) は差し替えた環境変数が `task-done` の実行するテストのコマンドに引き継がれ、別のリポジトリを読み書きしうる（`AGENTS.md` の S の「環境の隔離（`GIT_*`・`HOME`）」）。手で書く ledger は PR #224・#257 で使えている | 委任: 推奨案での決定 |
| D4 | 作業領域はセッションディレクトリの `sdd/` にする | セッションディレクトリの直下に ledger などを置く（PR #257） | プラグインの作業領域と同じ構成（ledger の `progress.md`、brief・報告・review package）を 1 か所にまとめられ、スキルの「workspace」をそのまま読み替えられる。実行予算の ledger（`budget.jsonl`）と同じセッションディレクトリに置き、片付けもその規則（作ったエージェントが消す）に従う | 委任: 推奨案での決定 |
| D5 | repo-cleanup-after-merge は削除の判定を変えず、手順 4 に生成元と直す先を 1 文で書く | 何も変えない | Issue の目的は規則と片付けの手順をそろえること。手順 4 は、止まったときに「どのスキル・どの手順の生成物か」を添えて報告するよう求めているので、そこにこの生成元と直す先を書く | 委任: 推奨案での決定 |
| D6 | テストを書かない | repo-cleanup-after-merge の判定や `AGENTS.md` の文言を確かめるテストを足す | 変更は規則の文書だけで、削除の判定（S）を変えない。文書の文言を写すテストは F に当たる。Issue の「検証」の、判定を変える場合の確かめ方は、判定を変えないので当てはまらない。代わりに、`AGENTS.md` に書いた手順のコマンドを一時リポジトリで実行し（受け入れ条件 1）、README の「テスト」と `git diff` の確認を行う | `AGENTS.md` の「テストの採用基準」 |
| D7 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `.devcontainer/agent-runner.toml`、`--config` なし、inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #132 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D8 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形と個人設定の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #132 --merge --max-cycles 3`。`check` は終了コード 0 |

## PR #262 のレビュー修正（サイクル 1）

- 実行許可: 利用者の `/issue-to-pr #132 --merge --max-cycles 3` による PR 修正ループ（run `07885eabf9f7415f80a8adaeabefe739`）の計画。review-fix-planning の完遂（修正不要なら `finalize.py` でマージし、関連 Issue を更新する）
- planner: claude-opus-5-5（claude-code）。サイクル 1、判断の対象の HEAD は `a35e109cf64fe905f5c86fede9f99a33a6de6330`
- 入力: `reviews/usaturn/create-reso-world/#262-fix-issue-132-sdd-workspace-outside-worktree/` の 3 つのレビューファイルと `findings/*-a35e109cf64f.json`（どれも `validate`・`check-pair` が 0）。確認済みの一覧 `verified/a35e109cf64f.json`（review-verify、mode cycle）は confirmed 4・not_reproduced 0・unverified 0

| レビューファイル | モデル / ランタイム | レビュー HEAD | 今回再実行 | 推奨 |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `a35e109cf64f` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash / pi | `a35e109cf64f` | はい | Needs manual verification |
| `Grok-4.7.md` | Grok 4.7 / cursor | `a35e109cf64f` | はい | Approve |

devin-swe は runner の `response_failed`（原因の分類は `rate_limit`、停止は確認済み）で、レビューファイルが無い。loop はこのレビュアーを却下し、計画の入力にしていない。

### 指摘の分類（解消済み 0 / 対応する 0 / 対応しない 4）

| 指摘 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `deepseek-deepseek-v4.1-flash#M-1@a35e109cf64f`（Medium） | `AGENTS.md:180` の「完了の行は `task-done` と同じ書式」は、SDD の完了の行（Task のレビューの後の `review clean`）と食い違う | 対応しない | 食い違いは確認した（V-1）。文は「テストが通ったときだけ」という必要条件で、Task のレビューを省いてよいとは書かない。SDD の完了の時点は SDD のスキルが決め、再開の判定はどちらの書式も行頭の `Task <N>: complete` で行う |
| `deepseek-deepseek-v4.1-flash#L-1@a35e109cf64f`（Low） | `sdd/` を作る段が無く、新しいセッションの最初の `task-brief`・`review-package` が終了コード 1 で止まる | 対応しない | 再現した（V-2、7.0.0・7.0.1）。無いディレクトリのパスを示すエラーで止まるだけで、worktree には何も作られない。気付ける失敗で、`mkdir` で続けられる |
| `deepseek-deepseek-v4.1-flash#L-2@a35e109cf64f`（Low） | Plan の Task 1 Step 2 の写しが、`7bd0605` の後の `AGENTS.md` と一致しない | 対応しない | 食い違いは確認した（V-3）。Plan は経緯の記録で、規則は `AGENTS.md` にある（`docs/superpowers/README.md`）。Plan の「完了」に `7bd0605` を記録している |
| `Grok-4.7#L-1@a35e109cf64f`（Low） | 同じ `sdd/` で 2 つ目の Plan を同じ出力先に `task-brief` すると、1 つ目の brief が置き換わる | 対応しない | 再現した（V-4）。issue-to-pr は Issue ごとにセッションディレクトリを作り、Plan は 1 つなので、通常の経路では起きない。brief は Task ごとに作り直し、ledger は 1 行目の Plan のパスで区別できる |

「対応する」が無いので、「守る条件と影響経路」の表と設計の見直しは無い。どの指摘も、実在する構成・使い方で誤った結果・データの消失・処理の停止に至る経路を示せなかった（SKILL.md の「致命的」に当たらない）。V-2・V-4 と、最後のブランチ全体のレビューの持ち越し（Plan の「完了」の指摘 2・3）は同じ性質で、PR 本文の持ち越し候補に挙げてある。

レビュアーが判断しなかった範囲は、確認済みの一覧で閉じた。SDD の実装サブエージェントが worktree の外の `sdd/` に報告を書く経路は、Claude Code のサブエージェントに `tmp/agents/issue-132.5u7egjt7/subagent-report-check/sdd/task-1-report.md` を書かせて確かめた（この環境の権限の設定）。pi・Codex・Devin のサブエージェントでの同じ経路は未確認のまま残る。Devin の superpowers 7.0.1 のスクリプトは 7.0.0 と同じ内容だった。

### 結論と検証

- 結論: 2（修正不要でマージ）
- 自己レビュー: 未実施（修正が無いため。`run_roles.py` は実行していない）
- 検証（検証の記録の `base` は下の先端）: base `main` の先端は、レビューの後に PR #260・#263・#261 のマージで `0ae40eeb97931b36b51cde93b8404ba9f3f39b1f` に進んだ。head `a35e109` にその先端を一時の隔離 worktree で merge したツリー（競合なし。push しない）で、`bash .devcontainer/run-tests.bash` 0（23 test(s) PASS、FAIL 0）、`bash scripts/check-layout.sh` 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` 0（1224 passed）。検証の前後で、そのツリーに未 commit の変更は無かった。head だけのツリーでも、issue-to-pr の最後の検証で同じ 3 つが 0 だった
