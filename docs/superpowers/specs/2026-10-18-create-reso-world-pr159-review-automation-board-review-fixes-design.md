# PR #159 のレビュー修正（#116 のボード）

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/159（branch `docs/issue-116-review-automation-board`、Refs #116）
- 検証した HEAD: `81ccc0167469c193575b86659b860cf239fa3e78`（レビューの対象 HEAD と同じ）
- 状態: completed（結論 1。内容の明示承認は記録していない）
- 関連: `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md`（直した Spec）、`docs/superpowers/plans/2026-10-18-create-reso-world-issue116-review-automation-board.md`
- 実行許可: 2026-10-18（JST）、利用者が `/review-fix-planning #159` を指示した（完遂）。この PR の修正、検証、既存 PR への push、状況コメントの投稿が許可されている。PR の内容であるボード（#116 と子 #149〜#158 の本文・依存）の修正も、この PR の修正に含めた。マージは結論 2 のときだけで、今回は行わない

## 入力

`reviews/#159-docs-issue-116-review-automation-board/` の 3 ファイル。どれも対象 HEAD は `81ccc0167469`。

- `claude-opus-5-5.md`（Low 2・Info 1）
- `openai-codex-gpt-6.1-sol.md`（Medium 1）
- `SWE-2-Max.md`（Low 1・Info 1）

## 全指摘と分類

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| codex M-1 | #153 が #150 より先にマージでき、雛形の既定のレビュアーが未定義になる | 対応する | 再現した（下記）。開始手順のとおり #150 より先に #153 か #155 を入れると、runner の全てのコマンドが `invalid_reference` で止まる（主要な処理が止まる） |
| claude L-1 | D-10 の保存先の変更に、review-fix-planning のレビューディレクトリの解決を合わせる子がいない | 対応する | #153 の本文は「#146 が not_planned なら D-10 の形で入れる」。その場合、今の review-fix-planning の `#番号` の解決は `reviews/` の直下しか見ないので、全ての PR で 0 件になって止まる（主要な処理が止まる）。担当の無い計画上の変更でもある |
| claude L-2 | D-7 の pytest の `pythonpath` に `tools` を加えると、`from tools.agent_runner ...` が import できない | 対応しない | 値の誤りは事実だが、#149 の受け入れ（`uv run pytest tools` が通る）が収集の失敗ですぐに止めるので、誤った値のまま `main` に入る経路が無い |
| claude I-1 | Plan の冒頭が参照する Spec の版 `b2bd038` が D-8 の追記の前 | 対応しない | Plan の「完了」に追記（`b6f9651`）を記録してある。承認は記録しておらず（draft）、取り違えで誤った結果になる経路が無い |
| SWE L-1 | 「確認した事実」の pi のランチャーの列挙が 9 個中 4 個 | 対応しない | 列挙は網羅を主張していない。D-13 の判断に使うランチャー（`pigs`・`pixg`・`piccd`・`pigod`、`pigemf` の有無）は正しい |
| SWE I-1 | 「#146 の branch は未 push」の記述が執筆後に古くなった | 対応しない | 日付付きの記録で、Spec の commit の時点では正しい。#153 の着手の条件は #146 の Issue の状態で判断する |

件数: 解消済み 0 / 対応する 2 / 対応しない 4。

仕様の論点として残すもの: L-2 の値（`pythonpath` にはルートの `"."` を加える）は #149 の実装で受け入れのテストが決める。

## 対応する

### M-1: 雛形が参照する agent の定義の順序

再現: 移植元 `a47b2065` の `tools/agent_runner/config.py` の `load_config` は、全ての workflow の担当（`agents`・`fallback`）が `[agents.*]` に定義されていることを確かめ、無ければ `invalid_reference` を出す。CLI の全てのコマンドがこれを通る。雛形 `.devcontainer/agent-runner.toml` を子の担当の節（D-12）に分け、#149＋#151＋#152＋#153 の節だけで組むと `invalid_reference`、#150 の節を足すと通った。

修正: #153（`pr-review-v2`）の直接の先行に #150（`runner-adapters`）を足した。#156（`fix-loop`）の #150 は #155 を通して入るので、冗長な辺として外した（辺は 13 本のまま、並行の波は変わらない）。Spec の D-19、子 #153・#156 の本文、#116 の実行マップ・公開台帳・図と、GitHub の `blocked_by` を合わせた。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| ボードの依存のとおりにどの順で子をマージしても、雛形が参照する agent は、参照を足す子の先行（推移的を含む）が定義している | #153 の `[workflows.review.assignments.inspect]`（`pi-gpt`・`devin-swe`・`claude-opus`・`pixg` は #150、`dsh-ccd` は #151） | 修正する | 下の閉包の検査 |
| 同上 | #155 の `[workflows.fix.assignments.implement]`（`claude-opus` は #150） | 修正する（#153 の修正で推移的に満たす） | 同上 |
| 同上 | #157 の `[workflows.issue.assignments.implement]`（`self`） | 既に満たす（`self` は定義が要らない） | 同上 |
| 同上 | #149 の `[roles.*]`、#150・#151 の `[agents.*]`（参照を持たない） | 既に満たす | 同上 |
| 同上 | 個人設定（#149 の `place_agent_runner_config` が雛形を写す） | 既に満たす（どの時点の雛形も検査を通るので、写したものも通る） | 同上 |
| 同上 | #156 の直接の先行の #150（雛形の節を持たない） | 修正する（冗長な辺を外し、入力として本文に書く） | `blocked_by` の読み戻し |

検証（閉包の検査）: 各子について、その子と先行の連鎖の全ての子の雛形の節だけを組み合わせ、移植元の `load_config` で検査した。修正後の依存では 10 件とも通った。対照として修正前の依存で同じ検査をすると、#153・#155 の 2 件が `invalid_reference` で失敗した（検査が欠陥を検出できる）。子の任意のマージの順は、先行で閉じた集合になるので、子ごとの閉包が通れば全ての順で通る。

### L-1: 保存先を読む既存の箇所の担当

修正: D-10 に、保存先を読む・説明する既存の箇所も #153（`pr-review-v2`）が同じ PR で合わせることを足した。#153 の担当に review-fix-planning の `SKILL.md` の「第1引数の解決」の節と手順 2 のレビューディレクトリ・`PR_REPO` の決め方（D-10 に合わせる場合だけ）と、`docs/resoloop-meshy-workflow.md` の保存先の文を足し、受け入れに「マージの時点で `/review-fix-planning #<番号>` が新しい配置を解決できる（#146 の結果に関係なく）」を足した。#155（`review-fix-roles`）の担当は、その節を除く全体にした。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| 保存先を変える子は、同じ PR で、保存先を決める・読む・説明する既存の箇所を全て新しい配置に合わせる（`main` のどの時点でも、書く側と既存の読む側の配置が一致する） | pr-review の helper と `SKILL.md` | 既に満たす（#153 の担当） | #153 の本文の「範囲と禁止」 |
| 同上 | `AGENTS.md` の「PR レビュー結果」の行 | 既に満たす（#153 の担当） | 同上 |
| 同上 | repo-cleanup-after-merge の pr-review のセッションとレビューディレクトリの箇所 | 既に満たす（#153 の担当、保存先の変更に合わせる場合だけ） | 同上 |
| 同上 | review-fix-planning の「第1引数の解決」と手順 2 | 修正する（#153 に割り当て、#155 から外した） | 生成スクリプトの担当の照合（節が分かれていること）と、#153・#155 の本文の読み戻し |
| 同上 | `docs/resoloop-meshy-workflow.md` の「PR のレビューと修正」の保存先の文 | 修正する（#153 に割り当て） | #153 の本文の読み戻し |
| 同上 | review-verify（#154）・pr-review-fix-loop（#156）・`review_target.py`（#152） | 対象外（新しい入口で、D-10 の形で作る。#153 より前に #154 が入った場合、resoloop の PR のレビューは明示したパスで読む） | — |
| 同上 | `.gitignore` の `/reviews/` | 既に満たす（下の階層も無視される） | `git show 81ccc01:.gitignore` |
| 同上 | `docs/resoloop-fork-workflow.md` の古い checkout の表 | 対象外（過去の作業の片付けの記録で、保存先の規則ではない） | — |

同じ条件の再発: この PR の 1 回目のレビュー修正なので、きっかけには当たらない。

## 結論

結論 1（修正して push）。Spec の D-10・D-19 とこの文書を PR の head に commit し、既存の PR へ push する（push の結果は PR の状況コメントに書く）。ボードは GitHub 側で修正した（`blocked_by` の入れ替え、子 #149〜#158 の本文の更新、#116 の本文の更新）。

## 実行した検証

- 生成スクリプトの照合: 子 10 件、依存 13 本、循環なし、担当の重なりは節で分かれている（終了コード 0）
- 閉包の検査（M-1）: 修正後 10 件とも通過、修正前の対照で 2 件失敗
- GitHub の読み戻し: #116 の Sub Issue（全ページ）が子 10 件、各子の `blocked_by`（全ページ）が生成元の 13 本と一致。子 10 件の本文が生成したものと一致。#116 の本文と公開台帳が一致
- 書き込みの前の確認: 子と #116 の本文が、前回の書き込みから変わっていないことを確かめてから更新した
- `bash scripts/check-layout.sh`: PASS。`git diff --check`: 問題なし。変更は `docs/superpowers/` の文書だけで、`README.md` の「テスト」のほかの入口はコードとテストを変えていないので実行していない

## 自己レビュー

修正後に 1 回だけ、コントローラーが自分で 3 観点を見た（サブエージェントは使っていない）。自己レビューの後に修正はしていない。

- 反証: 雛形のほかの参照（`fallback`、`[workflows.review]` の後処理のスクリプト、`pi-gemf`、Grok Build の agent）を確かめた。`fallback` は雛形に無く、後処理のスクリプトは参照する節と同じ #153 の担当、`pi-gemf` は既定から参照されず、Grok Build の agent は移植先にコマンドが無いので #150 が定義しない。review-fix-planning の解決の節は、#146 が先にマージされても #153 の担当の節として合わせられる。致命的な指摘は無い
- PR 全体: 修正後の Spec・Plan の全文と PR の本文を読んだ。PR の本文の「依存は 6 つの波」「`blocked_by` を 13 本」は修正後も正しい。致命的な指摘は無い
- 検証の検出力: 閉包の検査は修正前の依存で 2 件失敗し、検出力がある。L-1 は担当の割り当ての修正で、実行して確かめる挙動は無く、本文の読み戻しで確かめた
- 指摘として扱わなかった点: review-verify（#154）は #153 より前にマージされ得て、その間は resoloop の PR のレビューを `#番号` で見つけられない。新しい入口で既存の流れが使うのは #153 の後になり、明示したパスで読めるので、致命的ではない
