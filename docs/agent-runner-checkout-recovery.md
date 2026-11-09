# agent-runner の checkout 監査と worktree 登録の回収

runner の監査は、登録された checkout の変化を観測する。書き込み元は特定できない。runner が保護するのは依頼された checkout だけで、特定できなければ全登録を保護する。保護する checkout の変化・消失・監査不能は `outside_changes` となり、受け取り入口が成果を拒否する。保護しない checkout の内容の変化・回収・監査不能は `unprotected_changes` として報告するだけで、起動も受け取りも止めない。main worktree も、依頼された checkout でなければ保護しない（[共通インターフェース](../tools/agent_runner/interfaces.rst)）。担当がほかのセッションの worktree や、依頼された checkout でない親の checkout に書き込んでも止まらないので、`unprotected_changes` を確かめ、必要なら成果を確かめ直す。

`checkout_audit` の `unavailable_before` / `unavailable_after` は、変化が無かったことを確認できない状態である。`locked` と `prunable` は登録の情報であり、削除の許可ではない。監査は repair・remove・prune を自動実行しない。

## 登録と所有者を照合する

対象リポジトリの main checkout で、現在の状態と登録を確認する。

```bash
git status --porcelain
git worktree list --porcelain
git rev-parse --path-format=absolute --git-common-dir
```

監査が示すパスに対応する `<git-common-dir>/worktrees/<id>/gitdir` と `HEAD` を読む。`gitdir` の内容が対象パスの `.git` と一致することを確認する。所有者は、作成した run の記録（PR レビューなら保存済みの `session.json`、runner なら `result.json` の `work_dir`・`stop_confirmed`）と、PR・Issue・作業ログを照合する。名前や HEAD だけで所有者を推測しない。

次を区別する。

| 状態 | 操作 |
| --- | --- |
| 本体を移動した | 所有者が移動先を確認し、下の個別 repair を行う |
| 一時的な unmount、アクセス権不足、Git のエラー | 接続や権限を復旧して再診断する |
| `locked`、所有者不明、run の停止未確認 | 登録を残して所有者へ引き継ぐ |
| rebuild で消えたことと所有する run の停止を確認できた | 未保存データを確認し、下の個別回収へ進む |

rebuild の候補は、対象が旧コンテナの `/tmp` に作られ、run の記録が現在のコンテナの起動より前にあり、本体が無いものとなる。`stat` の日時、`ps -p 1 -o lstart=`、postCreate のログは補助情報として照合する。日時が古い、`/tmp` にある、`prunable` と表示される、という条件だけでは消失を確定できない。コンテナの外へ移動・退避した可能性、所有者が保持を指示した記録、まだ動くプロセスが無いかも確認する。

## 移動先がある場合

所有者が確認した移動先 1 件を指定する。

```bash
git worktree repair '/確認した移動先の絶対パス'
git worktree list --porcelain
git -C '/確認した移動先の絶対パス' status --porcelain
```

移動先の HEAD・index・未保存ファイルを確認し、runner の起動前監査をやり直す。repair が失敗した場合、登録を削除して作り直さない。

## 本体が消えた登録を個別回収する

この操作は、所有者が対象の登録・run の停止・本体の消失を確認した後に行う。通常のマージ後の整理だけを依頼された場合は、この回収の実行許可にはならない。エージェントは、照合した登録と保存予定を具体的に示して、所有者の判断を得る。

まず HEAD・index・reflog 等の登録情報をコピーする。HEAD が既存の branch に含まれていても、index に未 commit の内容が残る場合がある。次の例では、その index の内容と HEAD の履歴を回収用 commit・ref・bundle に保存する。各コマンドの終了コード 0 を確認してから次へ進む。未解決の merge、submodule、読めない HEAD/index がある場合は、この手順で回収を続けず、所有者が個別に復元する。既に消えた untracked ファイルや、index に入っていなかった編集は、この保存では復元できない。

`CHECKOUT_ROOT`・`ENTRY_NAME`・`WORKTREE_PATH` は、上で照合した値に置き換える。

```bash
CHECKOUT_ROOT='/workspaces/reso-world'
ENTRY_NAME='<照合した登録の id>'
WORKTREE_PATH='/tmp/<照合した run>/worktree'
COMMON_DIR=$(git -C "$CHECKOUT_ROOT" rev-parse --path-format=absolute --git-common-dir)
REGISTRATION="${COMMON_DIR:?}/worktrees/${ENTRY_NAME:?}"
RECOVERY_SESSION=$(uv run --no-project python "$CHECKOUT_ROOT/.agents/scripts/agent_tmp.py" mkdir checkout-recovery)
cp -a -- "$REGISTRATION" "$RECOVERY_SESSION/registration"
test -f "$RECOVERY_SESSION/registration/index"
RECOVERY_HEAD=$(git --git-dir="$REGISTRATION" rev-parse --verify 'HEAD^{commit}')
RECOVERY_TREE=$(env GIT_INDEX_FILE="$RECOVERY_SESSION/registration/index" git -C "$CHECKOUT_ROOT" write-tree)
RECOVERY_COMMIT=$(git -C "$CHECKOUT_ROOT" commit-tree "$RECOVERY_TREE" -p "$RECOVERY_HEAD" -m 'Preserve disappeared worktree index')
RECOVERY_REF="refs/agent-recovery/$(basename "$RECOVERY_SESSION")"
git -C "$CHECKOUT_ROOT" update-ref "$RECOVERY_REF" "$RECOVERY_COMMIT" ''
git -C "$CHECKOUT_ROOT" bundle create "$RECOVERY_SESSION/history.bundle" "$RECOVERY_REF"
git -C "$CHECKOUT_ROOT" bundle verify "$RECOVERY_SESSION/history.bundle"
```

bundle の検証が成功したら、所有者が必要な HEAD の履歴と staged の内容を保存できたことを確認する。回収用 ref とセッションディレクトリは、その確認が終わるまで保持する。これらを push や PR に含めない。

削除の直前に `git worktree list --porcelain` と登録情報を再確認する。対象は同じ登録であり、`locked` ではなく、移動先・新たな所有者・再起動した run が無いことを確認する。パスが再作成されていたら remove へ進まない。確認した消失パス 1 件だけを指定する。

```bash
test ! -e "$WORKTREE_PATH" && test ! -L "$WORKTREE_PATH"
git -C "$CHECKOUT_ROOT" worktree remove -- "$WORKTREE_PATH"
git -C "$CHECKOUT_ROOT" worktree list --porcelain
```

対象の登録だけが消え、ほかの missing / locked 登録が残ることを確認し、元の依頼の起動前監査をやり直す。remove が拒否されたら止める。`--force`、ロック解除、一括 `git worktree prune`、`.git/worktrees/` の直接削除で通さない。dry-run と実行の間に別の登録が消失しても巻き込まないよう、対象を限定する。

Git の仕様は [git-worktree](https://git-scm.com/docs/git-worktree) を参照する。回収用 ref・登録情報・bundle の片付けは、所有者が復元不要と確認した後に、その保存物だけを対象に行う。
