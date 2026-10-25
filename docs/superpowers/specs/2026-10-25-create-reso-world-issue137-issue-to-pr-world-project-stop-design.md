# Issue #137: issue-to-pr をワールドのプロジェクトの作業で止める

- 状態: draft
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #137](https://github.com/usaturn/create-reso-world/issues/137)
- 検証したコードの HEAD: `origin/main` `115f7c3065c422e121c5617289f0181d39f85773`（2026-10-25T01:30Z の着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue137-issue-to-pr-world-project-stop.md`
- 関連: #114・PR #136（issue-to-pr の追加。2026-10-17 にマージ済み）、PR #147（#114 の Spec・Plan の completed）
- 実行許可: 利用者の `/issue-to-pr #137 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

独自の `.git` を持たないワールドのプロジェクト（`worlds/slum02` など）を cwd にして「#N に着手して。推奨案で進めて」と頼むと、エージェントは issue-to-pr を選び、create-reso-world の worktree・Spec・Plan・PR を作る。ワールドのプロジェクトは git の追跡対象外なので worktree に実体が無く、Spec・Plan だけの PR ができる。その PR の `Closes #N` で、ワールドの作業が済まないまま Issue が閉じる。issue-to-pr を、ワールドのプロジェクトの作業では使わず、使われても worktree を作る前に止まるようにする。

## 着手時の確認

1. Issue の「反映先」は、PR #136 に入れるか別の PR にするかを利用者が決めるとしていた。PR #136 は 2026-10-17 にマージ済みで、利用者がこの Issue を `/issue-to-pr` で指示したので、別の PR で直す
2. `git check-ignore -q .` の終了コード（2026-10-25 に実測）: `worlds/slum02` とその下の `tests/` は 0、リポジトリのルート・`.worktrees/<topic>`・`external/resoloop` は 1、git の外（`/tmp`）は 128。独自の `.git` を持つ `worlds/asakusa01`・`worlds/reso-workshop` は 1（自分のリポジトリのルート）
3. スキルの探索（2026-09-26 の調査の記録）: Claude Code は cwd から git のルートまでの `.claude/skills`、Codex・pi は `.agents/skills` を読む。独自の `.git` を持たないワールドのプロジェクトからは、ルートの issue-to-pr が見える。Cursor は cwd の下だけを読む
4. `resolve_issue.py` は、2 章の 3 で「現在の checkout を cwd として」実行する読み取り専用の helper で、呼び出し元は `SKILL.md` とそのテストだけ。`#N` は cwd の origin で解決するので、`worlds/slum02` からは create-reso-world の Issue として解決できてしまう
5. PR #136 の評価の (h)（cwd がルートで、本文がワールドのプロジェクトを明記）は、文面に書く前から 3/3 で止まった（`evals/validation.md`）。止まるかが本文の書き方に左右される

## 変更の内容

1. `resolve_issue.py` が、入力を読む前に cwd で `git check-ignore -q .` を実行する。終了コード 0（git が追跡しないディレクトリの中）なら、理由と進め方を出して終了コード 2 で止まる。1 なら続ける。それ以外（git の外、git を起動できない）も、確かめられないとして終了コード 2 で止まる
2. `SKILL.md` の description の「使わない」に、ワールドのプロジェクトを cwd にしているときと、Issue がワールドの作業のときを足す
3. `SKILL.md` の 2 章に、helper のこの停止（3）と、本文・コメントを読んだ後の停止（4。Issue がワールドのプロジェクトの中身を変える作業を含む）を書き、止まった後の扱いを「ワールドの作業で止まったとき」に書く
   - worktree・branch・Spec・Plan・PR を作らない。ワールドの作業は、そのプロジェクトを cwd にし、プロジェクトの `AGENTS.md` に従って進める（独自の `.git` を持たないプロジェクトでは branch・PR を使わない。`AGENTS.md` の「プロジェクト運用」）。ワールドの作業とリポジトリの変更の両方を含む Issue は、分けるよう伝える（最後の全体レビューの指摘で足した）
   - 利用者が明示して起動した run（`/issue-to-pr`、Pi の `/skill:issue-to-pr`・`/sp-brainstorm`）: 理由と進め方を伝えて終える
   - モデルが自分の判断でこのスキルを選んだ run: このスキルを離れる。cwd がその Issue のワールドのプロジェクトなら、ワールドの作業として進める。そうでなければ進め方を伝えて終える
4. 「停止時の報告」の停止条件に、この 2 つを足す
5. `evals/scenarios.json` に、cwd がワールドのプロジェクトの場面を 2 つ（自然文の依頼、`/issue-to-pr`）足し、`evals/validation.md` に評価の結果を書く

## 対象外

- ワールドのプロジェクトの `AGENTS.md`・雛形（`templates/world-project/`）・`scripts/new-world.sh` の変更（Issue の反映先は `.agents/skills/issue-to-pr/` だけ）
- 独自の `.git` を持つワールドのプロジェクト（asakusa01・reso-workshop）。Claude Code からはルートの issue-to-pr が見えない見込みで、`#N` は自分の origin（usaturn/reso-world-sensoji・usaturn/reso-workshop）で解決されて helper の対象外のリポジトリとして止まる。URL で create-reso-world の Issue を指定したときは helper では止まらず、2 章の 4 の判断（変更の内容 3）が守る。見えないかの実測はしない
- ワールドの作業で Issue をいつ閉じるか（プロジェクトの作業の流れの範囲）
- 他のスキル（pr-review・review-fix-planning など）の同じ扱い

## 受け入れ条件

1. cwd が `worlds/slum02` の「#N に着手して」の場面で、worktree・branch・PR を作らずに、ワールドの作業として進める（行動比較で 3/3）
2. PR #136 の (a)〜(j) の結果が変わらない（行動比較で、期待は今の `evals/scenarios.json` のもの）
3. `resolve_issue.py` は、cwd が git の追跡しないディレクトリの中なら、Issue を読む前（`gh` を呼ぶ前）に終了コード 2 で止まり、Git の状態を変えない。cwd が追跡するディレクトリなら、今までどおり解決する

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | cwd の確かめは `resolve_issue.py` で行う | (a) `SKILL.md` に、モデルが `git check-ignore -q .` を実行する手順を書く。(b) helper で、cwd が `<PARENT_ROOT>/worlds/` の下かをパスで確かめる | helper は、どのランタイムでも 2 章の 3 で同じ cwd で必ず実行され、副作用の前に止められる。(a) はモデルが手順を飛ばすと進む。(b) は従来位置のプロジェクトや、`tmp/` などの追跡しない場所を拾えず、配置が変わると外れる。`git check-ignore` は `.gitignore` を基準に「git の追跡対象外」を判定する | 委任: `/issue-to-pr #137 --merge --max-cycles 3` の推奨案での決定。Issue の直し方の案 2 の条件と同じ |
| D2 | 終了コード 0・1 以外も止める（確かめられないときは進まない） | 0 だけを止め、ほかは続ける | helper は「現在の checkout」で実行する決まりで、git の外から実行する流れは無い（着手時の確認 4）。止まる側に倒しても、今の使い方を妨げない | 委任: 推奨案での決定 |
| D3 | 本文がワールドの作業を含むかは、2 章の 4 でモデルが判断する。雛形・`scripts/new-world.sh` など追跡するファイルの変更は当たらないと例を書く | helper が本文の `worlds/` などの文字列で止める | ワールドの雛形やツールの Issue も `worlds/` に触れるので、文字列では誤って止まる。(h) は今の文面でも 3/3 で止まっていて、手順として明記すれば足りる。ワールドの作業とリポジトリの変更が混じる Issue は、PR の `Closes #N` でワールドの作業が済まないまま閉じるので止める | 委任: 推奨案での決定 |
| D4 | 止まった後の扱いを、起動の仕方で分ける（明示の起動は伝えて終える。モデルが選んだ run はスキルを離れ、cwd がそのプロジェクトならワールドの作業として進める） | (a) どちらも伝えて終える。(b) どちらもワールドの作業として進める | 受け入れ条件 1 は、自然文の依頼でワールドの作業として進めることを求める。明示の `/issue-to-pr` の委任は PR までの流れで、Resonite のワールドを変える作業に黙って切り替えると、委任の範囲を越える。(a) は受け入れ条件 1 を満たさない | 委任: 推奨案での決定。Issue の直し方の案 2（止まって案内する）と受け入れ条件 1（ワールドの作業として進める）の両方を満たす |
| D5 | description にも「使わない」を足す（helper の停止と併用） | helper の停止だけにする | 自然文の依頼で、スキルを読み込まずにワールドの作業に進める。helper は、description で外れたときの守りになる | 委任: Issue の直し方の案 1 |
| D6 | テストは `tests/test_resolve_issue.py` に 1 件足す（git が追跡しないディレクトリの下からの起動を、`gh` を呼ばずに止める）。確かめられないとき（D2）のテストは書かない | 停止の文言、description、`SKILL.md` の文面を確かめるテスト | 停止が壊れると、エラーにならずに Spec・Plan だけの PR ができ、マージで Issue が閉じる（`AGENTS.md` の S）。正しく通る例は、ルートから解決する既存のテストが担う。D2 の経路は git の外からの起動で、ワールドのプロジェクトの損害につながらない。文言・frontmatter の照合は F。`SKILL.md` の振る舞いは行動比較で確かめる | `AGENTS.md` の「テストの採用基準」 |
| D7 | 行動比較は、Claude Code の Agent ツールで起動した新しいサブエージェント（model `sonnet`）で、1 回の起動で 1 回答。cwd がワールドの 2 場面を、対照（`origin/main` の `SKILL.md`）と比較（変更後）で各 3 回。(a)〜(j) は比較の版で 3 回。実装中に、比較で (i) が分かれたので、原因を切り分けるために対照でも (a)〜(j) を 3 回取った（Plan の Task 3 の Ruling） | (a)〜(j) も対照と比較で取る。回数を増やす | Issue の直し方の案 3 と受け入れ条件のとおり。(a)〜(j) の対照の結果は `validation.md` に記録済みで、変わらないことは比較の版だけで確かめられる。本物のモデルを起動する確認なので、回数は Plan に書いた分に限る（`AGENTS.md` の「エージェント運用」） | 委任: 推奨案での決定 |
| D8 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `.devcontainer/agent-runner.toml`、`--config` なし、inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #137 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D9 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形と個人設定の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #137 --merge --max-cycles 3`。`check` は終了コード 0 |
