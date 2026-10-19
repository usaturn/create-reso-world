# repo-cleanup-after-merge のゲート A の一時ファイルを `mktemp -d` のディレクトリに置く

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/131
- 状態: `draft`（内容の明示承認は受けていない）
- 調査時 HEAD: `8f5074a`
- 利用者の指示: Claude Code のセッションで `/issue-to-pr #131`
- 実行許可: issue-to-pr の委任範囲に従い、通常の判断を推奨案で決め、検証・commit・push・PR 作成まで進める。マージ、手順 6 以外の手順・他のスキルの変更は含まない
- 実装の担当: `self`。`.devcontainer/agent-runner.toml` の雛形の既定を適用した（`implement_task.py check` の `assignment` は `agents: ["self"]`・`fallback: []`）。利用者の指定ではない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-131-gate-a-mktemp`、branch `fix/issue-131-gate-a-mktemp`（`origin/main` `8f5074a` から作成）
- Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue131-gate-a-mktemp.md`

## 意図と範囲

`.agents/skills/repo-cleanup-after-merge/SKILL.md` の手順 6（ゲート A）は、`diff -rq` の stdout・stderr を `/tmp/gate-a.out`・`/tmp/gate-a.err` に書き、その中身で pr-review の残骸（`review-backup/`）を消してよいかを決める。この Dev Container では複数のセッションを並行して動かしており（2026-10-17 の時点で 5 つ）、同じ名前のファイルに書くと他のセッションの結果を読み、照合していない残骸を消すおそれがある。`reviews/` は git が保護せず、残骸がレビュー結果の唯一の版になることがある。

`AGENTS.md` の「`/tmp` 直下に固定名のファイルを作らない。`mktemp -d` で一意のディレクトリを作り、その中に置く」（PR #130）に合わせ、手順 6 のコマンド例を、その実行が作ったディレクトリに書いて読み、最後に消す形にする。

### 範囲外

- 削除の 3 条件、`<model>.md` のコピー、`Files ... differ` の保留（変えない）
- 手順 6 以外の手順と、他のスキル
- #123 の Spec・Plan にある固定名への言及（当時の記録なので書き換えない）
- 削除の可否をシェルで判定して出力すること

## 必要な挙動

1. 手順 6 のコマンド例が `/tmp` 直下の固定名のファイルを使わない。`mktemp -d "${TMPDIR:-/tmp}/repo-cleanup-gate-a.XXXXXX"` で作ったディレクトリに `diff` の stdout・stderr を書く
2. 判定に使う 2 つの出力を、同じ実行が作った同じディレクトリから読み、見出しで分けて表示する。`diff` の終了コードも表示する
3. 表示した後、同じ実行の中で空値ガード付きの `rm -rf -- "${GATE:?}"` でディレクトリを消す
4. 本文の `/tmp/gate-a.err` の参照を、表示の見出しに合わせる
5. コピーの後の述語の再実行は、同じブロックを実行し直す（新しいディレクトリを作る）。判定の条件は変わらない
6. frontmatter の `allowed-tools` に `Bash(mktemp *)` を足す

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 一時ディレクトリの作り方 | `mktemp -d "${TMPDIR:-/tmp}/repo-cleanup-gate-a.XXXXXX"` | 引数なしの `mktemp -d`、Claude Code の scratchpad、`tmp/agents/`（`agent_tmp.py`） | `review-fix-planning`・`review-verify` の `mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX"` と同じ形で、中断して残ってもどのスキルの物か分かる。scratchpad は Claude Code にしか無い。判定の出力は消えても困らない中間出力なので、`AGENTS.md` の表では `/tmp` の `mktemp -d` に当たり、`tmp/agents/` には当たらない | issue-to-pr による通常判断の委任 |
| 消す時点 | 1 回の実行の中で、出力を表示した直後に消す | Issue の「判定した後に」を文字どおりに読み、判定の後の別の呼び出しで `rm -rf -- "${GATE:?}"` を実行する | Claude Code の Bash など、シェルの変数が次の呼び出しに残らないランタイムがある。後の呼び出しでは `GATE` が空になり、空値ガードで止まってディレクトリが残る。判定の材料は表示した中身そのものなので、表示の後に消しても判定は変わらない。コピーの後の再実行も、新しいディレクトリで行える | issue-to-pr による通常判断の委任（Issue の受け入れ基準 3 つは満たす） |
| 出力の読み方 | 同じブロックの中で `cat` し、`--- stderr ---`・`--- stdout ---` の見出しで分けて表示する | ディレクトリのパスを表示し、別の呼び出し（Read など）で読む | パスを別の呼び出しへ写すと、写し間違いで他の実行のファイルを読むおそれが残る。同じブロックで読めば、読むファイルは必ずその実行が作った物になる | issue-to-pr による通常判断の委任 |
| 判定の自動化 | しない。判定は今までどおり表示を読んで行う | シェルで 3 条件を判定し、削除の可否を出す | Issue が「判定の条件は変えない」としている。述語の扱い（空の `grep` だけを削除許可にしない、など）を書き換えることになる | Issue の範囲 |
| `allowed-tools` | `Bash(mktemp *)` を足す | 変えない | frontmatter は手順が実行する外部コマンド（`diff`・`rm`・`cp` など）を並べている。新しく使う `mktemp` を足して一覧と手順を揃える。`cat`・`echo`・`printf` は既存の手順（手順 7 の `printf` など）でも並べていないので足さない | issue-to-pr による通常判断の委任 |
| テスト | 書かない。書き換えたコマンド例を `SKILL.md` から取り出し、一時の fixture で実行して確かめる | 固定名が無いことを照合するテストを足す | `AGENTS.md` の「テストの採用基準」。文書の変更で、文言の照合（作らない型 1）・旧文言が無いことの検査（型 2）に当たる | Issue の「検証」 |

## 検証

- `SKILL.md` の手順 6 のブロックを取り出し、`<残骸ディレクトリ>`・`<正本ディレクトリ>` を一時の fixture のパスに置き換えて bash で実行する。次の各場合で、削除の 3 条件を判定できる表示が出て、実行の後に `repo-cleanup-gate-a.*` が残らないことを確かめる
  - 削除してよい: `review-backup/` が `previous-review.md` と、正式な保存先と同じ `<model>.md` だけ
  - 削除しない: `Files ... differ` がある
  - 削除しない（コピーの対象）: `previous-review.md` 以外の `Only in ...review-backup` がある
  - 削除しない: 正式な保存先（`<正本ディレクトリ>`）が無い（stderr に出て、終了コード 2）
- 違う fixture で 2 つの実行を同時に動かし、それぞれが自分の fixture の結果だけを表示する
- README の「テスト」のコマンド（ワールドの行を除く）と `git diff` の確認
