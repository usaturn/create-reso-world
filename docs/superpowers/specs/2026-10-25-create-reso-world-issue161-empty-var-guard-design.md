# review-fix-planning: 空の変数で別の対象を書き換える呼び出しを `${VAR:?}` で止める

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/161
- 状態: `completed`（PR #271 のサイクル 1 で修正し、2026-10-26 の判断の記録の round 3 で追加修正不要を確認した。末尾の最終確認を参照）。内容の明示承認は受けていない
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
| SKILL.md 手順 3 | `git -C "$MAIN_ROOT" worktree add --detach "$WT" "$REVIEWED_HEAD"` | `MAIN_ROOT` | cwd が同じリポジトリの別の clone なら、その clone に worktree を登録する（サイクル 1 のレビューの指摘） | `MAIN_ROOT` に付ける | `git -C "${MAIN_ROOT:?}" worktree add --detach "$WT" "$REVIEWED_HEAD"` |
| SKILL.md 専用の worktree の手順 2 | コードブロックの `REPO_MAIN="$MAIN_ROOT"` と `git -C "$REPO_MAIN" worktree list --porcelain`（手順 3 で `FIX_WT` を選ぶもと） | `MAIN_ROOT`・`REPO_MAIN` | cwd が PR の head ブランチを checkout 済みの別の clone なら、その worktree を一覧に出し、手順 3 で `FIX_WT` に選ばれる。手順 4 の共通 context が同じ Git を照合するのは既知の経路（create-reso-world・resoloop）だけなので、`CODE_ROOT` を明示する経路では、その後の書き込みがその worktree に入る（サイクル 1 の自己レビューの指摘） | 付ける | `REPO_MAIN="${MAIN_ROOT:?}"`・`git -C "${REPO_MAIN:?}" worktree list --porcelain` |
| SKILL.md 専用の worktree の手順 3 | どこでも checkout されていないときの `git -C "$REPO_MAIN" worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"` | `REPO_MAIN` | 手順 2 の fetch が別の clone に PR の head の commit を持ち込むので、cwd がその clone なら、そこにブランチと worktree を作る（サイクル 1 のレビューの指摘。`FIX_WT` が空のときは git の BUG で止まり、意図したブランチだけが残る） | `REPO_MAIN` に付ける | `git -C "${REPO_MAIN:?}" worktree add -b "$HEAD_BRANCH" "$FIX_WT" "$HEAD_SHA"` |
| SKILL.md 専用の worktree の手順 3 | `git -C "$FIX_WT" merge --ff-only "$HEAD_SHA"` | `FIX_WT` | cwd の checkout を PR の head へ fast-forward する（親の checkout なら detached HEAD が `origin/main` から動く） | `FIX_WT` に付ける | `git -C "${FIX_WT:?}" merge --ff-only "$HEAD_SHA"` |
| SKILL.md 専用の worktree の手順 3 | ローカルブランチだけがあるときの `git -C "$REPO_MAIN" worktree add "$FIX_WT" "$HEAD_BRANCH"` | `REPO_MAIN` | cwd が同じ名前のブランチを持つ別のリポジトリなら、そのリポジトリの worktree を `FIX_WT` に作る（直前の `merge-base` の確認を別の呼び出しにしたとき。全体レビューの指摘） | `REPO_MAIN` に付ける | `git -C "${REPO_MAIN:?}" worktree add "$FIX_WT" "$HEAD_BRANCH"` |
| SKILL.md 専用の worktree の手順 5 | `git -C "$REPO_MAIN" branch -D "$HEAD_BRANCH"` | `REPO_MAIN` | cwd のリポジトリにある同じ名前のブランチを消す | `REPO_MAIN` に付ける | `git -C "${REPO_MAIN:?}" branch -D "$HEAD_BRANCH"` |
| SKILL.md 結論 2 の手順 6 | `git -C "$MAIN_ROOT" add -- <Spec>`・`git -C "$MAIN_ROOT" commit --amend --no-edit` | `MAIN_ROOT` | cwd の checkout の HEAD の commit を、そこの index の内容を含めて作り直す | 付ける | `git -C "${MAIN_ROOT:?}" add -- <Spec>`・`git -C "${MAIN_ROOT:?}" commit --amend --no-edit` |
| SKILL.md 結論 3 | `git -C "$MAIN_ROOT" reset --keep "$HEAD_SHA"` | `MAIN_ROOT` | cwd のブランチを PR の head へ動かす | `MAIN_ROOT` に付ける | `git -C "${MAIN_ROOT:?}" reset --keep "$HEAD_SHA"` |
| SKILL.md 結論 3 | `git -C "$MAIN_ROOT" restore --staged --worktree -- <Spec>` | `MAIN_ROOT` | cwd の checkout の同じパスの変更を捨てる | 付ける | `git -C "${MAIN_ROOT:?}" restore --staged --worktree -- <Spec>` |
| execution.md 1 章 | `git -C "$MAIN_ROOT" cherry-pick <commit>` | `MAIN_ROOT` | cwd のブランチに担当の commit を取り込む（runner の worktree は同じリポジトリなので commit がある） | 付ける | `git -C "${MAIN_ROOT:?}" cherry-pick <commit>` |
| execution.md 3.4 節 | 補足のコメントの `gh pr comment <PR> --repo <repo> --body-file <file>`（`merge_parent` の補足も同じ形） | `PR_NUMBER`・`PR_REPO`（変数で書いたとき） | cwd のブランチの PR に投稿する | 付ける | `gh pr comment "${PR_NUMBER:?}" --repo "${PR_REPO:?}" --body-file <file>` |
| SKILL.md 手順 2・結論 2 の手順 6・実装後の手順 4 | `gh pr view "$PR_NUMBER" --repo "$PR_REPO" --json ...` | `PR_NUMBER`・`PR_REPO` | 手順 2 は直後の `fetch_pull_head` の `int(PR_NUMBER)` と、共通 context の `--repo` の検査で止まる。ほかは `headRefOid` を検証した `HEAD_SHA` と比べ、別の PR なら止まる | 変えない | — |
| SKILL.md 手順 3 | `git -C "$MAIN_ROOT" worktree remove --force "$WT"` | `MAIN_ROOT` | `WT` は対象のリポジトリに登録するので、別の clone・別のリポジトリでは `is not a working tree` で止まる。同じリポジトリでは同じ worktree を対象にする | 変えない | — |
| SKILL.md 専用の worktree の手順 2・5 | `fetch "$PR_REMOTE" "pull/$PR_NUMBER/head"`・`worktree remove "$FIX_WT"` | `REPO_MAIN`・`PR_REMOTE`・`PR_NUMBER` | fetch は FETCH_HEAD と remote の追跡 ref・objects だけを変え（空の番号では `invalid refspec` で止まる）、ガードを付けた `REPO_MAIN=` の行の後にある。`worktree remove` は、別の clone・別のリポジトリには登録が無いので `is not a working tree` で止まる | 変えない | — |
| SKILL.md 結論 2 の手順 2・6、結論 3、実装後の手順 4 | `git -C "$MAIN_ROOT"` の `fetch`・`rev-parse`・`diff`・`status`・`log`・`merge-base` | `MAIN_ROOT` | fetch は FETCH_HEAD と remote の追跡 ref だけを変え、ほかは読むだけで、比べる値が合わずに止まる | 変えない | — |
| SKILL.md 作業終了前の PR 投稿・round-records.md | `upsert_pr_comment.py --pr "$PR_NUMBER" --repo "$PR_REPO"`・`gh api ... "repos/$PR_REPO/issues/$PR_NUMBER/comments"` | `PR_NUMBER`・`PR_REPO` | `--pr` は `int`、`--repo` は形の検査で止まる。`gh api` は 404 で止まる | 変えない | — |
| execution.md 3 章 | `finalize.py --record-file "$ROUND_JSON" ... --spec-commit "$SPEC_COMMIT"` | 記録の PR・head、`SPEC_COMMIT` | `gh` を起動する前に `environment:` で止まる | 変えない | — |
| execution.md 3.4 節 | `gh pr checks <PR> --repo <repo> --watch`・`gh pr view <PR> --repo <repo> --json state,mergedAt,headRefOid` | — | 読むだけ。待った後・報告の後は、記録の PR で `finalize.py` を再実行する | 変えない | — |

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 結論 2 の手順 8（Issue の第 1 の対象） | 変えない。`finalize.py` が空の値で止まることを実行で確かめる | `finalize.py` に空の値の検査を足す。SKILL.md にシェルの `gh pr merge` を書き戻し、`${VAR:?}` にする | #155 でマージは `finalize.py` に移った。記録の検査・`view_pr` の照合・head の照合が、空の値を `gh` の前に止める。書き戻すと、範囲・CI・base・記録の照合を省くマージの手順を増やす | issue-to-pr による通常判断の委任 |
| 調べる範囲 | review-fix-planning の SKILL.md と `references/`（変えるのは SKILL.md と execution.md） | SKILL.md だけ（Issue の「同じファイル」の字句どおり）。他のスキル（issue-to-pr、pr-review-fix-loop）も | Issue の対象は #155 の前の SKILL.md で、結論 2 の最終化の手順（補足のコメントを含む）は今は execution.md にある。他のスキルの呼び出しは Issue の範囲の外 | 同上 |
| 付ける基準 | 空の値で別の PR・リポジトリ・checkout を書き換える呼び出しの、その変数だけに付ける。cwd が同じリポジトリの別の clone のときも含めて判定する。push の先を決める `gh pr view` と、`FIX_WT` を選ぶ手順 2 の `REPO_MAIN`・`worktree list` を含める | 書き込みの変数すべてに付ける。呼び出しの中の変数すべてに付ける | Issue の指定（止まるだけのものは変えない）。`HEAD_SHA`・`HEAD_BRANCH`・`HEAD_REMOTE` は空なら git が止まる（Issue と再現で確かめた）ので、付けても守りが増えない | 同上 |
| `gh` の番号と `--repo` | 両方に付ける | 番号だけに付ける | `--repo ""` は指定なしと同じで cwd のリポジトリになる。番号だけに付けると、リポジトリの変数が空のときに、別のリポジトリの同じ番号の PR を書き換える | 同上 |
| 規則の文 | SKILL.md の「共通 context の確認」の最後に 2 文を足す | Issue のとおり手順 8 の位置に 1 文（手順 8 が無い）。付けた各行に理由を書く。Red flags に別の項目を足す | 共通 context の確認は書き込みの直前に変数をそろえる手順で、付けた呼び出しはどれもそこを通る。各行に書くと同じ理由が 14 か所に並ぶ。書いていない呼び出し（結論 2 の手順 8 の、参照している Issue へのコメントなど）にも同じ基準を当てられる | 同上 |
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
3. **変えないもの**: 「調べた呼び出し」の「変えない」の git の行が、空の値で止まるか、FETCH_HEAD と remote の追跡 ref だけを変える。cwd が対象の linked worktree・同じリポジトリの別の clone・別のリポジトリのどれでも確かめる（一時リポジトリでの再現）
4. `README.md` の「テスト」のコマンド（ワールドの行を除く）と `git diff --check` が終了コード 0

## 検証の結果

2026-10-25、`2707500`（Task 1）と `8627f97`（全体レビューの後の修正）で確かめた（PR の作成の前の結果。サイクル 1 の修正と検証は、末尾の「PR #271 のレビュー修正（サイクル 1）」）。bash 5.3.9・zsh 5.9・git 2.55.0・gh 2.101.0・gitleaks 8.30.1。script とログはセッションディレクトリ `/workspaces/reso-world/tmp/agents/issue-161.4te9xs1z/repro/` にある（コミットしない）。

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

## PR #271 のレビュー修正（サイクル 1）

- 実行許可: 利用者の `/issue-to-pr #161 --merge --max-cycles 3`。issue-to-pr の 5 章のとおり PR 修正ループ（run `696b5b7febb448f28835107f04b77062`）を回し、review-fix-planning の完遂で判断した。結論 1 として修正を push し、状況コメントを投稿する。マージは次のサイクル以降の `finalize.py` が行う
- planner: `claude-opus-5-5`（claude-code）。サイクル 1（判断の記録の round 1）で、前のサイクルの記録は無い
- 対象: PR の head `3a15f6d575e35fad0f551546eb07c81467544e30`（merge-base は `c1fdc56`）。base の `main` は PR #272 のマージで `08255ca` に進んだが、変わったのは `.devcontainer/` の 4 ファイルで、この PR のファイルとは重ならない
- 入力: `reviews/usaturn/create-reso-world/#271-fix-issue-161-merge-var-guard/` の 4 つのレビューファイルと `findings/*-3a15f6d575e3.json`（4 件とも validate・check-pair が通った）
- 確認済みの一覧: `verified/3a15f6d575e3.json`（review-verify の mode cycle。確認担当は planner 自身）。confirmed 1・not_reproduced 0・unverified 0。レビュアーが実行しなかった README の「テスト」・`finalize.py` の実行・新しい形の個別の実行などは、PR の作成の前の記録で閉じ、残りは無い
- 工程の記録: `verified/3a15f6d575e3.planning.json`。修正の確認: `verified/ab1e8629062d.fix-check.json`（と `.statement-candidates.json`・`.fix-check.md`）
- 修正と自己レビューの担当（`run_roles.py` の割り当て。雛形 `.devcontainer/agent-runner.toml` の既定）: implement は `claude-opus`、self-review と fix-check は `self`。自己レビューは `run_roles.py --phase self-review` の呼び出し 1 回

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | 今回再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | claude-opus | `3a15f6d575e3` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `3a15f6d575e3` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `3a15f6d575e3` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7（レビューファイルの表記。担当の識別は Grok 4.7 256K Extra High） | cursor | cursor-grok47 | `3a15f6d575e3` | はい | Approve |

### 指摘の振り分け

レビューの指摘: 解消済み 0 / 対応する 1 / 対応しない 0。

- 対応する: `deepseek-deepseek-v4.1-flash#L-1@3a15f6d575e3`（確認済みの一覧の V-1。報告の重大度は Low）
  - 内容: checkout を指す変数（`MAIN_ROOT`・`REPO_MAIN`）だけが空で、cwd が同じリポジトリの別の clone のとき、SKILL.md:87 の `worktree add --detach` と SKILL.md:166 の `worktree add -b` が、その clone に worktree とブランチを作る。166 行は、直前の 157 行の fetch がその clone に PR の head の commit を持ち込み、FETCH_HEAD の照合も通るので、止まらない
  - 致命的である理由: 誤った対象（別の clone）への操作。このマシンには resoloop の別の clone が `/workspaces/reso-world/tmp/` の下に 3 つあり、resoloop の PR の review-fix で、呼び出しを分けて変数が失われると（#161 の前提）到達できる。作った worktree の場所（`.worktrees/<…>-review-fix`）が残り、次の完遂も「専用の worktree」の手順 3（パスが既にある）で止まる
  - 確認: (a) 再現した誤動作。SKILL.md の文字列のまま、一時リポジトリで再現した（`verified/3a15f6d575e3.json` の V-1）
  - PR 起因: 既存（4 行とも base にある）。この Spec の「調べた呼び出し」が、87・166 行を「変えない（止まる）」と誤って判定していた

修正後の自己レビューの指摘（self-review の `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f.md` と fix-check の `verified/ab1e8629062d.fix-check.json`。同じ問題を両方が挙げたものは 1 件にまとめた）: 対応する 1 / 対応しない 1。

- 対応する: `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f#L-1@ab1e8629062d` と `fix-check#V-1@ab1e8629062d`
  - 内容: 「専用の worktree」の手順 2 のブロックを `MAIN_ROOT` が空のまま実行し、cwd が PR の head ブランチを checkout 済みの別の clone だと、`REPO_MAIN` も空になり、162 行の `worktree list` がその clone の worktree を出し、手順 3 の「別の worktree で checkout されている」でそれが `FIX_WT` に選ばれる。手順 4 の共通 context が同じ Git を照合するのは既知の経路（create-reso-world・resoloop）だけで（`scripts/superpowers_context.py:248-251`）、`CODE_ROOT` を明示する経路では通るので、その後の `${MAIN_ROOT:?}` 付きの書き込みも、その別の clone の worktree に入る（fix-check が再現し、create-reso-world の経路では同じ操作が終了コード 66 で止まった）
  - 致命的である理由: 誤った対象（別の clone の worktree）への commit・index の変更。`CODE_ROOT` を明示する経路（`AGENTS.md` の「リポジトリ境界」の「それ以外」）はサポートしている使い方で、到達できる
  - 確認: (a) 再現した誤動作（fix-check の V-1）
  - 設計の見直しのきっかけ: 自己レビューでの再発（この回に直した守る条件が、別の経路で破れていた）
- 対応しない: `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f#I-1@ab1e8629062d` と `fix-check#V-2@ab1e8629062d`（この Spec の「調べた呼び出し」の 61・62 行と受け入れ条件の 3、PR の説明が、`ab1e862` のガードを反映していない）。設計の記録の食い違いで、手順のとおりに進めて誤った結果にはならないので致命的ではない。結論 1 の手順 6（公開の前に Spec と PR の説明を実装に合わせる）で、この Spec と PR の説明を直した
- fix-check が挙げた検証の弱い点（未設定だけで空文字列を試していない、cwd が別の clone だけ、など）は、確かめの script に空文字列の場面と、手順 2 のブロック全体の実行を足して閉じた（下の「検証」）

### 設計の見直し

- きっかけ: (1) 同じ守る条件の 2 回目。PR の作成の前の全体レビューの指摘で、ローカルブランチだけがあるときの `worktree add` を、空の `REPO_MAIN` で別のリポジトリに worktree を作るとして直した（`8627f97`）。その隣の 87・166 行が、同じ条件で漏れていた。(2) 自己レビューでの再発。87・166 行を直した後（`ab1e862`）、`FIX_WT` を選ぶ手順 2 のブロックで同じ条件が破れていた
- 守る条件: checkout を指す変数が空のとき、SKILL.md と `references/` の git の書き込みのうち、ブランチ・HEAD・index・作業ツリー・worktree の登録を変えるものは、cwd がどの checkout（対象の linked worktree、同じリポジトリの別の clone、別のリポジトリ）でも、起動の前に止まるか、対象と同じ Git だけを変える。後の書き込みの対象（`FIX_WT`）を選ぶ呼び出しも、空の変数で別の checkout を選ばない。fetch は FETCH_HEAD と remote の追跡 ref・objects しか変えないので、この条件の外とする
- 条件を保つ仕組み: その書き込みと、対象を選ぶ呼び出しの checkout の変数を `${VAR:?}` にして、シェルが起動の前に止まるようにする。ガードを付けない書き込みは、git 自身が止まる（`is not a working tree`）ものだけにする。手順 4 の共通 context の照合は既知の経路だけなので、それに頼らない
- 以前の修正で足りなかった理由: Task 1（`2707500`）と `8627f97` は、「別のリポジトリには commit・ブランチが無いので止まる」と判定し、cwd を対象のリポジトリ（linked worktree）と別のリポジトリだけで考えていた。同じリポジトリの別の clone は commit やブランチを持ちうるうえ、手順 2 の fetch が commit を持ち込む。`ab1e862` は、`FIX_WT` を選ぶ手順 2 のブロックが別の clone の worktree を選んでも、手順 4 の共通 context が止めると考えていたが、それは既知の経路だけだった
- 直し方の比較:
  - 点の修正を続ける（選んだ）: 87・166 行と、手順 2 のブロックの `REPO_MAIN="${MAIN_ROOT:?}"`・`worktree list` に `${VAR:?}` を付け、下の表で仕組みから全経路を数え直して、残りの書き込みが条件を満たす根拠を示す
  - 条件を 1 か所で保つ形にまとめる: 2 ファイルの `git -C` を、読み取りも含めてすべて `${VAR:?}` にするか、`scripts/superpowers_context.py` に、どの経路でも `CODE_ROOT` が最初に照合した checkout と同じ Git であることを照合させる。前者は Issue の「止まるだけのものは変えない」に反し、読み取りまで変えて差分が増える。後者は helper の仕様を変え、この PR の範囲（helper は変えない）を超える
  - PR の保証を狭める: 同じリポジトリの別の clone を cwd にする使い方を既知の制限にする。再現した誤った対象への操作が残るので選ばない
- 見直した内容（`515b72d`）は再レビューしていない（自己レビューは 1 回まで）

### 守る条件と影響経路

確かめる方法の「全経路」は `verify-clone-paths-2.bash`（`/workspaces/reso-world/tmp/agents/review-fix-planning-pr271.7fnznkf4/`。修正後の文書から命令を文字列のまま取り、cwd を同じリポジトリの別の clone にして、checkout の変数だけを未設定・空文字列にした新しいシェル（bash・`zsh -f`）で実行し、対象の clone1 と別の clone の clone2 の状態全体（すべての ref・HEAD・index・作業ツリー・worktree の登録・FETCH_HEAD）を前後で比べる）。clone2 は同じ名前のブランチと PR の commit を持ち、作業中の変更を置いた。手順 2 のブロックの確かめでは、clone2 が PR の head ブランチを worktree で checkout 済みにした。

| 守る条件 | 経路 | 判定 | 変更前の挙動 | 観測する結果 | 確かめる assertion | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 空の checkout の変数で、別の checkout のブランチ・HEAD・index・作業ツリー・worktree の登録を変えず、後の書き込みの対象にも選ばない | SKILL.md:155・162 専用の worktree の手順 2 のブロックの `REPO_MAIN="$MAIN_ROOT"` と `worktree list`（`MAIN_ROOT`・`REPO_MAIN`） | 修正する | 別の clone の worktree を一覧に出し、手順 3 で `FIX_WT` に選ばれた（既知の経路の外では手順 4 も通った） | ブロックが `REPO_MAIN=` の行で止まり、git を起動しない。値ありでは対象の worktree だけを出す | 終了コードが 0 以外、`MAIN_ROOT` の `parameter` のメッセージ、clone1・clone2 の状態が前後で同じ。値ありでは出力に clone2 が無い | 全経路の B155（ブロック全体）・G155・G162、対照（`3a15f6d` のブロック） | `515b72d` で ok（bash 127・zsh 1）。対照のブロックは clone2 の worktree（`branch refs/heads/fix/x`）を出した |
| 同上 | SKILL.md:87 手順 3 の `worktree add --detach "$WT" "$REVIEWED_HEAD"`（`MAIN_ROOT`） | 修正する | 別の clone に worktree を登録した | 起動の前に止まる | 終了コードが 0 以外、`parameter` のメッセージ、clone1・clone2 の状態が前後で同じ | 全経路の G87、対照 O87（`3a15f6d` の形） | ok。対照は clone2 に worktree を登録した |
| 同上 | SKILL.md:166 専用の worktree の手順 3 の `worktree add -b`（`REPO_MAIN`） | 修正する | 157 行の fetch の後、別の clone にブランチと worktree を作った | 同上 | 同上 | 全経路の G166、対照 O166 | ok。対照は clone2 に `refs/heads/fix/x` と worktree を作った |
| 同上 | SKILL.md:167 `worktree add "$FIX_WT" "$HEAD_BRANCH"`（`REPO_MAIN`、`8627f97`）・`merge --ff-only`（`FIX_WT`） | 既に満たす | `8627f97`・`2707500` の前は、別のリポジトリに worktree を作り、cwd を fast-forward した | 同上 | 同上 | 全経路の G167a・G167b | ok |
| 同上 | SKILL.md:171 `branch -D`（`REPO_MAIN`） | 既に満たす | `2707500` の前は、cwd のリポジトリの同じ名前のブランチを消した | 同上 | 同上 | 全経路の G171 | ok |
| 同上 | SKILL.md:259 `add`・`commit --amend`、:290 `reset --keep`、:291 `restore`（`MAIN_ROOT`） | 既に満たす | `2707500` の前は、cwd の checkout を書き換えた | 同上 | 同上 | 全経路の G259a・G259b・G290・G291 | ok |
| 同上 | SKILL.md:353-354 検査付きの push（`MAIN_ROOT`） | 既に満たす | `2707500` の前は、cwd の HEAD を検査して push した | 同上 | 同上（`$()` の中で止まるので終了コード 1） | 全経路の G354 | ok |
| 同上 | execution.md:45 `cherry-pick`（`MAIN_ROOT`） | 既に満たす | `2707500` の前は、cwd のブランチに担当の commit を載せた | 同上 | 同上 | 全経路の E45 | ok |
| 同上 | SKILL.md:104 `worktree remove --force "$WT"`、:171 `worktree remove "$FIX_WT"`（`MAIN_ROOT`・`REPO_MAIN`） | 既に満たす（git が止まる） | 変えていない | 別の clone・別のリポジトリには登録が無いので、`is not a working tree` で止まる。87・166 行を直したので、この流れが別の clone に登録を作ることも無い | 終了コードが 0 以外、clone1・clone2 の状態が同じ | 全経路の U104・U171 | ok（128） |
| 同上 | SKILL.md:157・252・349 の fetch（`REPO_MAIN`・`MAIN_ROOT`） | 対象外 | 変えていない | FETCH_HEAD と remote の追跡 ref・objects だけを変える。157 行は、ガードを付けた 155 行の後のブロックの中にある | clone1 は同じ、clone2 は FETCH_HEAD と `refs/remotes/` だけが変わる | 全経路の U157・U252・U349 | ok（FETCH_HEAD だけ） |
| 同上 | 読み取り（`rev-parse`・`merge-base`・`status`・`log`・`diff`）と、execution.md 3.2 節の「MAIN_ROOT でローカルに commit する」（命令の文字列が無い） | 対象外 | 変えていない | 読み取りは状態を変えず、比べる値が合わずに止まる。命令の文字列の無い commit は「共通 context の確認」の規則の文が当たる | ― | ― | 理由のとおり |
| 空の番号・`--repo` で別の PR を書き換えない（別の条件） | `gh pr edit`・`gh pr comment`・push の先を決める `gh pr view` | 対象外 | ― | `gh` は `--repo` で API に送るので、cwd の clone に依らない。空のセレクタはすでに `${VAR:?}` | ― | 文書の形の確かめ（`verify-doc-forms.bash`） | `515b72d` で 115 件が ok |

### 失敗時の検証

- 状態全体: clone1・clone2 の ref（`for-each-ref`）・HEAD・index（`write-tree`）・作業ツリー（`status`）・worktree の登録・FETCH_HEAD を前後で比べた。clone2 には作業中の変更と index の変更を置いた。期待値は実行の前の状態から取った
- 副作用の順序: `${VAR:?}` はシェルの展開で、git を起動する前に止まる（手順 2 のブロックは 1 行目で止まり、fetch も実行しない）
- 負例の異常は 1 つ: checkout の変数だけを未設定か空文字列にし、ほかの変数には値を入れた
- ガードを外した対照: 修正前（`3a15f6d`）の 87・166 行と手順 2 のブロックの文字列で、clone2 に worktree とブランチができ、clone2 の worktree が `FIX_WT` の候補に出た（対照の 3 つの形 × bash・`zsh -f` の 6 件が、書き換え・誤った選択を検出した）

### 修正

- `ab1e862`（レビューの指摘）: SKILL.md の 87・166 行を `${MAIN_ROOT:?}`・`${REPO_MAIN:?}` にした。担当は claude-opus（claude-opus-5-5、claude-code 2.1.310、run `3872e753551841d9b2227a08c91b56f4`、58 秒、停止を確認済み）
- `515b72d`（自己レビューの指摘）: SKILL.md の 155 行を `REPO_MAIN="${MAIN_ROOT:?}"`、162 行を `git -C "${REPO_MAIN:?}" worktree list --porcelain` にした。担当は claude-opus（同じモデル、run `94855d740c004b15967cfd73c030ce5d`、44 秒、停止を確認済み）
- どちらも差分（2 行ずつ）を確かめてから、`cherry-pick --ff` で専用の worktree に取り込んだ
- この Spec: 「調べた呼び出し」の 87・155・162・166 行を「付ける」に移し、残りの理由を直した。状態を completed にした
- PR の説明: 呼び出しの数（11 → 14）、付けた呼び出しの一覧、「変えない」の理由を直し、このサイクルの修正と検証を足した

### 検証（`515b72d`、未 commit の変更なし）

- 全経路（`verify-clone-paths-2.bash <worktree> 3a15f6d`）: 84 件すべて ok（18 の形 × bash・`zsh -f` × 未設定・空文字列、手順 2 のブロック 8 件、対照 4 件）
- 文書の形（`verify-doc-forms.bash`）: 115 件すべて ok
- `git diff --check 3a15f6d HEAD`: 終了コード 0
- README の「テスト」: `bash .devcontainer/run-tests.bash` は PASS 23（0）、`bash scripts/check-layout.sh` は PASS（0）、`uv run pytest tests/skills .agents/skills .agents/scripts tools` は 1225 passed（0）。`ab1e862` でも同じ 3 つが 0 だった
- push の前の検査（`scan-before-push.sh`、自己レビューの前に `ab1e862` で）: 6 commit、検出なし

### 自己レビュー

`run_roles.py --phase self-review` を 1 回呼び、self-review と fix-check の 2 つの役割（どちらも `self`）を、新しい文脈のサブエージェント（Opus）に同時に任せた。

- 観点 1（反証）・観点 3（検証の検出力）: fix-check（06:57:10Z〜07:15:09Z）。confirmed 2（V-1・V-2）、主張 11 件のうち violates 1（手順 4 の共通 context の照合）、文書の候補 45 件のうち inconsistent 3（SKILL.md:168、この Spec の 61・62 行）。検証の弱い点を 4 つ挙げた
- 観点 2（PR 全体）: self-review（06:57:53Z〜07:13:21Z）。active 2 件（L-1 Low、I-1 Info）、Merge recommendation は Approve
- 結果の扱いは上の「指摘の振り分け」のとおり。自己レビューの後の修正（`515b72d`）は再レビューしていない

### 結論

1 修正して push する（判断の記録は `fixes_pushed`）。

## PR #271 の最終確認（2026-10-26、round 3）

### 実行許可と対象

- 利用者が pi で `pr-review-fix-loop #271` を明示的に起動した。完遂の修正・push・状況コメント・マージ・関連 Issue 更新の実行許可であり、内容の承認ではない
- planner: `gpt-6.1-sol`（runtime `pi`、provider `openai-codex`。bash の `PI_PROVIDER`・`PI_MODEL` で確認）
- loop run: `8e3eb200cbb4456185d79b0f5b461571`、loop のサイクル 1、判断の記録の round 3
- PR HEAD: `9e76938aa0fe6aaeadb85bfd1e3ded84ded40026`。既存の clean な worktree と head ブランチを再利用した
- 現行の4人の成果を helper が `reuse` としたため、新たな有料レビューは起動していない。以下の「現行 HEAD」は記録の `rerun: true`（HEAD 一致）を指す
- 修正・自己レビューの設定: implement `claude-opus`、self-review `self`、fix-check `self`。今回は修正不要なので `run_roles.py` は未実行、自己レビューの追加は0回。以前の自己レビュー1回は上の記録を維持する
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#271-fix-issue-161-merge-var-guard/verified/9e76938aa0fe.json`。PR・HEAD・現行4人の候補と一致し、validate と4件の check-pair が通った。工程の記録は同ディレクトリの `9e76938aa0fe.planning.json`

| レビューファイル | モデル | runtime | 実際の担当 | レビュー HEAD | 現行 HEAD | 推奨 |
| --- | --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | claude-opus | `9e76938aa0fe` | はい（再利用） | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `9e76938aa0fe` | はい（再利用） | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `9e76938aa0fe` | はい（再利用） | Approve |
| `Grok-4.7.md` | Grok 4.7 | cursor | cursor-grok47 | `9e76938aa0fe` | はい（再利用） | Approve |

旧自己レビュー `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f.md` は過去の判断の根拠として読み、現行 HEAD のレビュアーには数えない。loop の rejected は無い。レビューの過去の HEAD はいずれも現行 HEAD の祖先である。

### 全指摘の判断

解消済み2件 / 対応する0件 / 対応しない2件。round 2 の4件をすべて引き継ぎ、判断の変更は無い。

| 判断 ID（sources は以前の記録を維持） | 区分 | 根拠 |
| --- | --- | --- |
| `deepseek-deepseek-v4.1-flash#L-1@3a15f6d575e3` | 解消済み | `ab1e862` が SKILL.md:87・166 の checkout 変数にガードを追加。4人の現行レビューと確認済み一覧の実行証拠が、未設定・空文字列の拒否、状態不変、値ありの成功、旧版の対照を確認している |
| `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f#L-1@ab1e8629062d` | 解消済み | `515b72d` が SKILL.md:155・162 をガード。手順2のブロックが fetch 前に停止し、別 clone の worktree を選ばない。`fix-check#V-1@ab1e8629062d` も同じ判断 |
| `claude-opus-5-5-commit-ab1e8629062db08aeadb50d0ccd5f15d865d909f#I-1@ab1e8629062d` | 対応しない | 設計記録の記述の食い違いで、誤った実行結果を生まない。`9e76938` の公開前更新で表と PR 説明は修正済み。`fix-check#V-2@ab1e8629062d` も同じ判断。新しい見直し根拠は無い |
| `SWE-2-Max#I-1@9e76938aa0fe` | 対応しない | Plan の10件と現行14系統、PR説明の draft と Spec の completed の表記の差は実在するが、実行手順と採否を変えず致命的ではない。件数・状態を実行判断の根拠にする手順ができた場合に見直す |

全変更4ファイルの全文、対象選択・context・finalize と関連テストを確認した。独立した読み取り調査を sp-recon に委譲し、残存する致命的な欠陥は見つからなかった。新しい修正は無く、設計の見直しも追加しない。上の経路表のガードと証拠を引き継ぐ理由は、PR HEAD が以前の確認と同一であり、その後の差分が当該ガード・対象選択を変えていないためである。読み取り・fetch 等の対象外の理由も維持する。

### 検証と結論

- テストの追加・変更は不要。実装変更が無く、文書の件数や状態の固定値照合は `AGENTS.md` の F に当たる。既存の検証を実行する
- HEAD 単独と、最新 base を HEAD に merge した隔離 worktree の両方で、下表を同期実行した。検証用 merge は push せず、各 worktree は検証後に登録を外して削除した
- 前回 round 2 の停止原因だった Antigravity mount の不一致は、現在の base との組み合わせで run-tests と check-layout が通ることにより解消を確認した

| 検証したツリー | run-tests | check-layout | `uv run pytest tests/skills .agents/skills .agents/scripts tools` |
| --- | --- | --- | --- |
| HEAD `9e76938aa0fe` | 0（23 PASS） | 0（PASS） | 0（1225 passed） |
| HEAD + base `7b9380075e9bae9617f5a6a441aafc3ddffedf14` | 0（23 PASS） | 0（PASS） | 0（1225 passed） |
| HEAD + base `f0a346e729b5a3395bcfd1813f1ff576ce3809f6` | 0（23 PASS） | 0（PASS） | 0（1225 passed） |
| HEAD + base `ffe326fa3568a862ec18a56a79b5eaad47233cf3` | 0（23 PASS） | 0（PASS） | 0（1234 passed） |

base が進んだため再検証を2回行った。最終の検証用 merge commit は `454de04921733649c60fac5cce828f0e0f83e4f9`、tree は `7816b7d5057ad848c30b0bcf7e9ca9e24483c48f`。`git diff --check origin/main...HEAD` も0。未確認の指摘は無い。外部サービスの実 PR を空の引数で操作する検証はしていない（偽 gh と以前の記録の範囲を維持）。private リポジトリの停止中の CI は確認対象外。

結論2: 追加修正不要。マージ前の採否・検証を記録し、この Spec だけを HEAD の直接の子としてコミットする。その後の push・マージ・Issue 更新の結果は状況コメントと完了報告に残す。実行済みとは先に記載しない。

所要時間: 06:25Z ごろ着手、07:15Z までの確認約50分。そのうち検証は HEAD 約9.6分、merge ツリー3回で計約25.9分。最終化の所要時間は完了報告に記録する。
