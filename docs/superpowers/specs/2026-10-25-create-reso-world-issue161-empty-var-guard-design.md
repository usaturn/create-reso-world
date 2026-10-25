# review-fix-planning: 空の変数で別の対象を書き換える呼び出しを `${VAR:?}` で止める

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/161
- 状態: `draft`（内容の明示承認は受けていない）
- 調査時 HEAD: `c1fdc56`（Issue の記述は `8659aa9` の時点のもの）
- 利用者の指示: Claude Code のセッションで `/issue-to-pr #161 --merge --max-cycles 3`
- 実行許可: issue-to-pr の委任範囲に従い、通常の判断を推奨案で決め、検証・commit・push・PR 作成まで進める。`--merge` により、PR を作った後に PR 修正ループを回し、修正不要と確かめられたら、ループの中の `finalize.py` がマージと関連 Issue の更新を行う。それ以外のマージ、他のリポジトリの変更、実際の PR をマージ・編集して確かめることは含まない
- ループの設定（`loop.py check-options`）: サイクルの上限 3 は利用者の指定。レビュアー（`claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`）とレビュー修正の担当（`implement` は `claude-opus`、`self-review`・`fix-check` は `self`）は、雛形 `.devcontainer/agent-runner.toml` の既定の適用
- Plan の Task の担当（`implement_task.py check`）: `self`（雛形の既定の適用。`--implement` の指定なし）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-161-merge-var-guard`、branch `fix/issue-161-merge-var-guard`（`origin/main` `c1fdc56` から作成）
- Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue161-empty-var-guard.md`

## 意図と範囲

Claude Code の Bash は、呼び出しをまたいでシェルの変数を保たない。対象を変数で指定した呼び出しを別の呼び出しで実行すると変数が空になり、安全のための指定が別の意味に変わる（gh 2.101.0、`cli/cli` の trunk のソースで確認）。

- `gh pr edit`・`gh pr comment`・`gh pr merge`・`gh pr view` は、空のセレクタ（`""`）を受け付け、cwd の現在のブランチの PR を対象にする（`pkg/cmd/pr/shared/finder.go` の `opts.Selector == ""`。`--repo` を使うときの引数の確認は `len(args)` だけを見る）
- `--repo ""` は指定なしと同じで、cwd のリポジトリを対象にする（`pkg/cmdutil/repo_override.go` の `override == ""`）
- `git -C ""` は cwd のまま実行する

Issue は結論 2 の手順 8 の `gh pr merge` を対象にしていたが、#155（PR #186）でマージは `finalize.py` に移り、今の SKILL.md にシェルの `gh pr merge` は無い。`finalize.py` は PR の番号・リポジトリ・head を判断の記録から取り、`review_records.validate_record`（`pr.repository` は owner/name、`pr.number` は 1 以上の整数、`reviewed_head` は完全な SHA）、`view_pr`（返った PR の URL・番号が記録と同じ）、head の照合を通した値だけで `gh pr merge` を呼ぶ。Issue の関連に書かれた「マージを `finalize.py` に移した後も、PR の番号・リポジトリ・head の SHA が空なら止まることを保つ」は、変更しなくても満たしている（「検証と受け入れ条件」の 2）。

残りは Issue の「確かめてから決めるもの」である。review-fix-planning の SKILL.md と、結論 2 の最終化の手順を移した `references/` の、PR をセレクタで指定する `gh` と `git -C` の呼び出しを全部調べ、変数が空だと別の PR・リポジトリ・checkout を書き換えるものだけに `${VAR:?}` を付ける。空なら止まるものは変えない。

変更は次の 2 ファイルと、この Spec・Plan に限る。

- `.agents/skills/review-fix-planning/SKILL.md`
- `.agents/skills/review-fix-planning/references/execution.md`

`finalize.py` などの helper、`references/round-records.md`（空の値で 404・検査で止まる呼び出しだけ）、他のスキル、evals、過去の Spec・Plan は変えない。

## 必要な挙動

1. 下の「調べた呼び出し」で「付ける」とした行を、表の「新しい形」にする。その変数が空・未設定なら、bash・`zsh -f` の両方で、コマンドを起動する前にシェルが止まる
2. 値があるときは、今までと同じ引数でコマンドを起動する
3. SKILL.md の「共通 context の確認」の最後に、次の 2 文を足す（#145 で `AGENTS.md` に足した文と同じ書き方）。「書き込みの対象の PR・リポジトリ・checkout を変数で指定し、その変数が空だと別の対象を書き換える呼び出しは、変数を `${VAR:?}` で書く。`gh` は空の番号で cwd のブランチの PR を、空の `--repo` で cwd のリポジトリを、`git -C ""` は cwd の checkout を対象にするので、呼び出しを分けるときも `:?` を外さない。」
4. Red flags の「`--match-head-commit` を付けずにマージしようとしている」に、値が空の場合を含める
5. `finalize.py` は変えない。空の値の記録と空の `--spec-commit` で、`gh` を起動せずに止まる

## 調べた呼び出し

「空のとき」は、その変数だけを外した新しいシェルで、ほかの変数に値があるときの結果である（一時リポジトリと偽の `gh` で再現した。「検証と受け入れ条件」の 1・3）。

| 場所 | 呼び出し | 空にした変数 | 空のとき | 判定 | 新しい形 |
|---|---|---|---|---|---|
| SKILL.md 三択の結論の冒頭 | `gh pr edit --body-file`（引数を書いていない） | `PR_NUMBER`・`PR_REPO` | cwd のブランチの PR の本文を書き換える | 付ける | `gh pr edit "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --body-file <file>` |
| SKILL.md 実装後の手順 5 | push の前の `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json headRepository,headRepositoryOwner,headRefName`（push の先の `HEAD_BRANCH` を決める） | `PR_NUMBER` | cwd のブランチの PR の head ブランチを push の先にする。次の共通 context の再実行（`HEAD_REPO`・`HEAD_BRANCH` 付き）が `CODE_ROOT` のブランチと照合して止めるので、このガードは再実行を飛ばしたときの二重の守りになる（飛ばすと、その PR の上に積んだ修正なら fast-forward で通る） | 付ける | `gh pr view "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --json headRepository,headRepositoryOwner,headRefName` |
| SKILL.md 実装後の手順 5 | 検査付きの push（`scan-before-push.sh -C "$MAIN_ROOT"`・`git -C "$MAIN_ROOT" push`） | `MAIN_ROOT` | cwd の checkout の HEAD を検査して PR の head へ push する。cwd が PR の head の上に積んだ checkout なら fast-forward で通る（それ以外は non-fast-forward で拒否される） | `MAIN_ROOT` に付ける | `-C "${MAIN_ROOT:?}"`（2 か所） |
| SKILL.md 専用の worktree の手順 3 | `git -C "$FIX_WT" merge --ff-only "$HEAD_SHA"` | `FIX_WT` | cwd の checkout を PR の head へ fast-forward する（親の checkout なら detached HEAD が `origin/main` から動く） | `FIX_WT` に付ける | `git -C "${FIX_WT:?}" merge --ff-only "$HEAD_SHA"` |
| SKILL.md 専用の worktree の手順 3 | ローカルブランチだけがあるときの `git -C "$REPO_MAIN" worktree add "$FIX_WT" "$HEAD_BRANCH"` | `REPO_MAIN` | cwd が同じ名前のブランチを持つ別のリポジトリなら、そのリポジトリの worktree を `FIX_WT` に作る（直前の `merge-base` の確認を別の呼び出しにしたとき。全体レビューの指摘） | `REPO_MAIN` に付ける | `git -C "${REPO_MAIN:?}" worktree add "$FIX_WT" "$HEAD_BRANCH"` |
| SKILL.md 専用の worktree の手順 5 | `git -C "$REPO_MAIN" branch -D "$HEAD_BRANCH"` | `REPO_MAIN` | cwd のリポジトリにある同じ名前のブランチを消す | `REPO_MAIN` に付ける | `git -C "${REPO_MAIN:?}" branch -D "$HEAD_BRANCH"` |
| SKILL.md 結論 2 の手順 6 | `git -C "$MAIN_ROOT" add -- <Spec>`・`git -C "$MAIN_ROOT" commit --amend --no-edit` | `MAIN_ROOT` | cwd の checkout の HEAD の commit を、そこの index の内容を含めて作り直す | 付ける | `git -C "${MAIN_ROOT:?}" add -- <Spec>`・`git -C "${MAIN_ROOT:?}" commit --amend --no-edit` |
| SKILL.md 結論 3 | `git -C "$MAIN_ROOT" reset --keep "$HEAD_SHA"` | `MAIN_ROOT` | cwd のブランチを PR の head へ動かす | `MAIN_ROOT` に付ける | `git -C "${MAIN_ROOT:?}" reset --keep "$HEAD_SHA"` |
| SKILL.md 結論 3 | `git -C "$MAIN_ROOT" restore --staged --worktree -- <Spec>` | `MAIN_ROOT` | cwd の checkout の同じパスの変更を捨てる | 付ける | `git -C "${MAIN_ROOT:?}" restore --staged --worktree -- <Spec>` |
| execution.md 1 章 | `git -C "$MAIN_ROOT" cherry-pick <commit>` | `MAIN_ROOT` | cwd のブランチに担当の commit を取り込む（runner の worktree は同じリポジトリなので commit がある） | 付ける | `git -C "${MAIN_ROOT:?}" cherry-pick <commit>` |
| execution.md 3.4 節 | 補足のコメントの `gh pr comment <PR> --repo <repo> --body-file <file>`（`merge_parent` の補足も同じ形） | `PR_NUMBER`・`PR_REPO`（変数で書いたとき） | cwd のブランチの PR に投稿する | 付ける | `gh pr comment "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --body-file <file>` |
| SKILL.md 手順 2・結論 2 の手順 6・実装後の手順 4 | `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json ...` | `PR_NUMBER`・`PR_REPO` | 手順 2 は直後の `fetch_pull_head` の `int(PR_NUMBER)` と、共通 context の `--repo` の検査で止まる。ほかは `headRefOid` を検証した `HEAD_SHA` と比べ、別の PR なら止まる | 変えない | — |
| SKILL.md 手順 3 | `git -C "$MAIN_ROOT" worktree add --detach "$WT" "$REVIEWED_HEAD"`・`worktree remove --force "$WT"` | `MAIN_ROOT` | 別のリポジトリでは `invalid reference`・`is not a working tree` で止まる。同じリポジトリでは同じ worktree を対象にする | 変えない | — |
| SKILL.md 専用の worktree の手順 2・3・5 | `fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"`・`worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"`・`worktree remove "$FIX_WT"` | 各変数 | `invalid refspec`・`invalid reference`（別のリポジトリには `HEAD_SHA` の commit が無い）・`not a valid branch name`・`is not a working tree` で止まる。`FIX_WT` が空の `worktree add -b` は git の BUG で止まり、意図したブランチ（PR の head）だけが残る | 変えない | — |
| SKILL.md 結論 2 の手順 2・6、結論 3、実装後の手順 4 | `git -C "$MAIN_ROOT"` の `fetch`・`rev-parse`・`diff`・`status`・`log`・`merge-base` | `MAIN_ROOT` | 読むだけで、比べる値が合わずに止まる | 変えない | — |
| SKILL.md 作業終了前の PR 投稿・round-records.md | `upsert_pr_comment.py --pr "$PR_NUMBER" --repo "$PR_REPO"`・`gh api ... "repos/$PR_REPO/issues/$PR_NUMBER/comments"` | `PR_NUMBER`・`PR_REPO` | `--pr` は `int`、`--repo` は形の検査で止まる。`gh api` は 404 で止まる | 変えない | — |
| execution.md 3 章 | `finalize.py --record-file "$ROUND_JSON" ... --spec-commit "$SPEC_COMMIT"` | 記録の PR・head、`SPEC_COMMIT` | `gh` を起動する前に `environment:` で止まる | 変えない | — |
| execution.md 3.4 節 | `gh pr checks <PR> --repo <repo> --watch`・`gh pr view <PR> --repo <repo> --json state,mergedAt,headRefOid` | — | 読むだけ。待った後・報告の後は、記録の PR で `finalize.py` を再実行する | 変えない | — |

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 結論 2 の手順 8（Issue の第 1 の対象） | 変えない。`finalize.py` が空の値で止まることを実行で確かめる | `finalize.py` に空の値の検査を足す。SKILL.md にシェルの `gh pr merge` を書き戻し、`${VAR:?}` にする | #155 でマージは `finalize.py` に移った。記録の検査・`view_pr` の照合・head の照合が、空の値を `gh` の前に止める。書き戻すと、範囲・CI・base・記録の照合を省くマージの手順を増やす | issue-to-pr による通常判断の委任 |
| 調べる範囲 | review-fix-planning の SKILL.md と `references/`（変えるのは SKILL.md と execution.md） | SKILL.md だけ（Issue の「同じファイル」の字句どおり）。他のスキル（issue-to-pr、pr-review-fix-loop）も | Issue の対象は #155 の前の SKILL.md で、結論 2 の最終化の手順（補足のコメントを含む）は今は execution.md にある。他のスキルの呼び出しは Issue の範囲の外 | 同上 |
| 付ける基準 | 空の値で別の PR・リポジトリ・checkout を書き換える呼び出しの、その変数だけに付ける。push の先を決める `gh pr view` を含める | 書き込みの変数すべてに付ける。呼び出しの中の変数すべてに付ける | Issue の指定（止まるだけのものは変えない）。`HEAD_SHA`・`HEAD_BRANCH`・`HEAD_REMOTE` は空なら git が止まる（Issue と再現で確かめた）ので、付けても守りが増えない | 同上 |
| `gh` の番号と `--repo` | 両方に付ける | 番号だけに付ける | `--repo ""` は指定なしと同じで cwd のリポジトリになる。番号だけに付けると、リポジトリの変数が空のときに、別のリポジトリの同じ番号の PR を書き換える | 同上 |
| 規則の文 | SKILL.md の「共通 context の確認」の最後に 2 文を足す | Issue のとおり手順 8 の位置に 1 文（手順 8 が無い）。付けた各行に理由を書く。Red flags に別の項目を足す | 共通 context の確認は書き込みの直前に変数をそろえる手順で、付けた呼び出しはどれもそこを通る。各行に書くと同じ理由が 11 か所に並ぶ。書いていない呼び出し（結論 2 の手順 8 の、参照している Issue へのコメントなど）にも同じ基準を当てられる | 同上 |
| Red flags | 既存の `--match-head-commit` の項目に、値が空の場合を足す | 新しい項目を足す | Issue の指定。マージは `finalize.py` だけが行うので、手でのマージを止める既存の項目に含めれば足りる | 同上 |
| 実装後の手順 5 の push | `MAIN_ROOT` だけに付ける | 変えない（Issue は `HEAD_REMOTE`・`HEAD_BRANCH` が空なら止まることを確かめた）。push の変数すべてに付ける | `MAIN_ROOT` が空だと cwd の checkout を検査して push し、PR の head の上に積んだ checkout なら通る（再現）。`HEAD_REMOTE`・`HEAD_BRANCH`・`TOPLEVEL` は空なら止まる | 同上 |
| SKILL.md 手順 3 の `rm -rf -- "$REPRO_ROOT"` | 変えない | `AGENTS.md` の「削除」に合わせて `${REPRO_ROOT:?}` にする | 空なら何も消さない（`rm -rf -- ''` は終了コード 0 で何もしない）。別の対象を書き換えないので、Issue の範囲の外 | 同上 |
| テスト | 書かない | 文面に `${VAR:?}` があるかを照合する pytest | 文面の変更（Issue の指定。`AGENTS.md` の「テストの採用基準」の F）。止まるかどうかはシェルの展開で決まるので、文書から写した形を実行して確かめる | 同上 |
| 行動比較 | 行わない | writing-skills の無し/ありの比較 | #145 と同じく、付けた形はエージェントの判断ではなくシェルの展開で止まり、効果は実行で確かめられる。新しいスキルを作る変更でもない | 同上 |

## 検証と受け入れ条件

1. **文書の形の実行**: 変更後の SKILL.md・execution.md にある新しい形と、`origin/main` の文書にある旧い形を、文書から文字列のまま取り出し、プレースホルダー（`<Spec>`・`<file>`・`<commit>`・`<base>`）だけを値に置き換えて実行する。`gh` は起動と引数を記録する実行ファイルを `PATH` の先頭に置き、`git` は一時リポジトリで実際に実行する。変数を外した新しいシェル（bash・`zsh -f`）で、次を確かめる
   - A. 新しい形・変数が未設定: コマンドを起動せずに止まる（終了コード 0 以外）。checkout・ブランチ・index・remote の状態が変わらない
   - B. 新しい形・変数が空文字列: A と同じ
   - C. 旧い形・変数が未設定（対照）: 「調べた呼び出し」の「空のとき」のとおり、別の対象を書き換える（偽の `gh` は空の引数で起動される）
   - D. 新しい形・値あり: 旧い形と同じ引数で起動し、同じ結果になる（`gh pr edit` は旧い形に引数が無いので、新しい形が番号と `--repo` を付けて起動することを確かめる）
2. **`finalize.py`**: 起動を記録して失敗を返す runner を渡し、記録の `pr.number`（空・0・null）、`pr.repository`（空）、`reviewed_head`（空）、`--spec-commit ""` のそれぞれで、`gh` を起動せずに `stopped` になる。正しい記録では `gh pr view` を起動する（対照）
3. **変えないもの**: 「調べた呼び出し」の「変えない」の git の行が、空の値で止まるか同じリポジトリを対象にする（一時リポジトリでの再現）
4. `README.md` の「テスト」のコマンド（ワールドの行を除く）と `git diff --check` が終了コード 0

## 検証の結果

2026-10-25、`2707500`（Task 1）と `8627f97`（全体レビューの後の修正）で確かめた。bash 5.3.9・zsh 5.9・git 2.55.0・gh 2.101.0・gitleaks 8.30.1。script とログはセッションディレクトリ `/workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/` にある（コミットしない）。

| 確かめ | 結果 |
|---|---|
| 1. 文書の形の実行（`verify-doc-forms.bash`） | 編集の前は、新しい形が文書に無いので失敗した（最初の 12 の形と、レビューの後に足した `worktree add` の形のそれぞれ）。編集の後は 115 件すべて通った（文書の照合 13、git の 9 つの形 × bash・`zsh -f` × A〜D、`gh` の 3 つの形 × bash・`zsh -f` × 5 つの変数の状態） |
| A・B（新しい形・未設定／空文字列） | どれも起動の前に止まった。bash は `<VAR>: parameter null or not set`（終了コード 127。push は `$()` の中で止まるので 1）、zsh は `<VAR>: parameter not set`（1）。checkout・ブランチ・index・worktree・origin の状態は変わらず、偽の `gh` は起動されなかった（番号か `--repo` の片方だけが空のときも） |
| C（旧い形・未設定） | 「調べた呼び出し」の「空のとき」のとおり書き換えた。親の checkout の detached HEAD が PR の head へ動いた（`merge --ff-only`）。別の worktree では、HEAD が index の内容ごと作り直され（`commit --amend`）、PR の head へ動き（`reset --keep`）、変更が捨てられ（`restore`）、担当の commit が載り（`cherry-pick`）、index に Spec が載った（`add`）。別のリポジトリでは同じ名前のブランチが消え（`branch -D`）、worktree ができた（`worktree add`）。積んだ checkout の HEAD が PR の head ブランチに push された。偽の `gh` は空のセレクタ・空の `--repo` で起動された |
| D（値あり） | git の 9 つの形は、新旧で終了コード 0・同じ状態。`gh pr view`・`gh pr comment` は新旧で同じ引数、`gh pr edit` は新しい形が番号と `--repo` を付けて起動した |
| 2. `finalize.py`（`finalize-empty-values.py`） | 記録の `pr.number` が空・0・null、`pr.repository` が空、`reviewed_head` が空のとき `environment: 状況記録が不正で最終化を開始できない`、`--spec-commit ""` のとき `environment: --spec-commit が完全なcommit SHA（小文字の16進数40桁か64桁）ではない` で、どれも `gh` を 0 回起動して `stopped`（`merged: null`）。正しい記録では、最初に `gh pr view 900 --repo usaturn/create-reso-world ...` を起動した |
| 3. 変えないもの（`git-empty-vars.bash` の後半） | 別のリポジトリでの `worktree add`（commit を指定した 4 つの形）・`worktree remove --force`・空の refspec の `fetch`、空の値の `merge --ff-only`・`branch -D`・`reset --keep` は終了コード 1・128 で止まり、別のリポジトリのブランチは残った。`rm -rf -- ''` は終了コード 0 で何も消さなかった。同じリポジトリでも、`worktree add -b x <path> ''`・`worktree add <path> ''` は `invalid reference` で止まった |
| 4. `git diff --check`・`README.md` の「テスト」 | `git diff --check` は終了コード 0。README のテストは最後の commit の後に実行するので、結果は PR 本文と、セッションディレクトリの `verification/record.md` に書く |

全体レビュー（新しい文脈のサブエージェント、Opus、`c1fdc56..2707500`）は Critical 0・Important 0・Minor 4 で、Ready to merge は Yes。Review Focus の 5 件はどれも確かめられ、レビュアーの再実行でも 106 件が通った。

- Minor 1（`worktree add "$FIX_WT" "$HEAD_BRANCH"` は、`REPO_MAIN` が空で、cwd が同じ名前のブランチを持つ別のリポジトリだと止まらない）: この PR が足した規則の対象そのもので、この Spec の「止まる」も事実と違ったので、Important に付け直して直した（`8627f97`。「調べた呼び出し」に行を足した）
- Minor 2（S2 の理由が、push の前の共通 context の再実行による照合を書き落としていた）: 「調べた呼び出し」の理由を直した。規則の文は変えない
- Minor 3（`rm -rf -- "$REPRO_ROOT"` が `AGENTS.md` の「削除」に合わない）: 決定記録のとおり変えない
- Minor 4（共通 context の再実行で `CODE_ROOT` を渡し忘れると、`MAIN_ROOT` が親の checkout になり、`cherry-pick` などが親の detached HEAD を動かす）: 空の値とは別の既存の経路なので、この PR では直さず、持ち越し候補にする
