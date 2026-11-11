---
name: issue-to-pr
description: "Issue の URL・#番号を指定して『着手して』『実装して PR まで』『推奨案で進めて』と依頼されたときに使う。PR の番号・URL、PR レビュー・レビュー指摘の修正計画、ボードの親 Issue からの子の選択には使わない。ワールドのプロジェクト（`worlds/<name>/` と従来位置）を cwd にしているときや、Issue がワールドの作業のときも使わない（そのプロジェクトを cwd にして、その `AGENTS.md` に従って進める）。"
argument-hint: "<Issue> [--base BRANCH] [--implement AGENT] [--spec-review AGENT] [--design-review AGENT] [--merge [--max-cycles N] [--assign ROLE=AGENT[,AGENT]]... [--template PATH] [--config PATH]]"
---

# Issue to PR

## 1. 入口と委任の範囲

このスキルによる着手を、**通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示**として扱う。質問、設計・Spec・Plan の確認、実行方式、終了方法の選択は追加で尋ねない。AGENTS.md の「曖昧なら確認する」は、ここでは仕様の意味を変える判断・安全境界・後述の停止条件に適用する。実在しない承認や検証結果を記録しない。マージは、`--merge` のときにループの中の `finalize.py` が行うものだけで、それ以外ではしない。

- **Claude Code など:** `superpowers:using-superpowers` を読み、以下の流れを開始する。
- **Pi:** 自動 bootstrap や設定を変更しない。明示 `/sp-brainstorm` から開始し、このスキルを使う。明示 `/skill:issue-to-pr` から読み込まれた場合も opt-in として、`brainstorming` を直接読んで開始できる。
- Pi で自然言語の依頼しかなく、明示 `/sp-*`・`/skill:*` 限定の指示がある場合は、読み取りだけで入力を解決し、次の入口を案内して終了する。モデルがスラッシュコマンドを実行したふりをしない。

```text
/sp-brainstorm <解決した Issue URL> issue-to-pr を使い、推奨案で進めて途中で止めずに PR まで作成せよ
```

一度明示入口から開始した run では、工程ごとに次のコマンド入力を求めず、各スキルを読んで最後まで続ける。ランタイムの明示された承認・ツール制限は迂回しない。

**オプションは `--base`・`--implement`・`--spec-review`・`--design-review`・`--merge`・ループ用のオプション（`--merge` と一緒のときだけ）を受け付ける。** ほかのオプション（`--hold-action`・`--fresh-review` を含む）は、2 章の helper が理由を出して終了コード 2 で止まる。そのまま止まって理由を伝える。オプションを外して続けない。

### `--base`

`--base BRANCH`（`--base=BRANCH` も同じ）はコードの PR の向き先。Issue の前後どちらでも 1 回だけ指定できる。未指定は既存 parent / fork / meshy では `main`、登録済み通常ツールでは採用済み台帳の `base_branch`。対象 repository の `origin` に存在する branch 名だけを受け付ける（例: `#42 --base feat/plugin-v2`）。revision 式、tag、完全 ref、別 remote は使わない。base branch の新設・reset・force push で代えない。

親 Issue・handoff の現行の統合/base 指示を全文から確認し、要求値と根拠の URL/パスを記録する。複数の要求が異なる・意味が曖昧なら停止。要求が対象の既定 base と違うときは `--base` での明示が必要。既定と同じ要求なら未指定でも進める。既存 3 repo の既定は引き続き `main` であり、別の要求に合うと推測しない。2 章で取得した repository / origin / 完全 heads ref / SHA を以後固定する。外部コードの文書用 base は別の create-reso-world / origin / main。

### `--implement`

Plan の Task を実装する担当は、agent-runner の `workflows.issue` の `implement` で決まる（雛形 `.devcontainer/agent-runner.toml` < 個人設定 < `--implement`）。雛形の既定は `self` で、このセッション（司令塔）が自分で実装する。`--implement AGENT` か個人設定で別の担当を選べる。`--implement` は `agents` を置き換え、`fallback` は設定のものを保つ。

- `--implement AGENT`（`--implement=AGENT` も同じ）は、その回だけ一次担当を置き換える。値は agent-runner の設定にある agent 名か `self`。`fallback` は設定のものを保つ
- Issue の参照の前でも後でも書け、1 回だけ書ける
- 担当の検査は 2 章の 3、依頼の手順は 4 章の「Task の実装を runner の担当に依頼する」

### `--spec-review` と `--design-review`

Spec レビューと設計レビューは、利用者がこの 2 つの引数を書いた run だけで行う。雛形・個人設定にレビューの assignment や fallback があっても、引数が無ければ helper の `check` も runner も起動しない。`--merge` と一緒でも `loop_args` には入れない（PR 修正ループの `--assign` とは別）。

- `--spec-review AGENT` / `--design-review AGENT`（`=AGENT` も同じ）は、その run のレビュー担当を置き換える。値は agent-runner の agent 名か `self`。各 1 回だけ書ける
- 明示した担当が一次担当になり、個人設定の `fallback` は保つ。設定だけでは担当を選ばない
- `--spec-review` を指定した run は、通常の builder check の代わりに Spec レビューを行う。Spec レビューが失敗しても builder check で代えない
- `--design-review` は builder check を代替しない。設計レビューの後、Spec レビューが無ければ builder check を 1 回行う。両方指定したときは設計レビュー → Spec レビュー → Plan の順で、builder check は行わない

### `--merge`

`--merge` は、PR を作った後に PR 修正ループ（pr-review-fix-loop）を回し、修正不要と確かめられたら、マージと関連 Issue の更新まで進める指示である。ループの中の判断（致命的な指摘だけを直す、三択の結論、修正後の自己レビューは最大 1 回）は review-fix-planning のままで、マージはその `finalize.py` だけが行う。

- 有効なのは、**利用者のメッセージ（スラッシュコマンドの引数を含む）に `--merge` という語が書かれているときだけ**。自然文の「マージまで」「マージして」は `--merge` として扱わない。モデルが自分でこのスキルを選んだ run で `--merge` を補わない
- ループ用のオプションは `--max-cycles N`・`--assign ROLE=AGENT[,AGENT]`（複数可）・`--template PATH`・`--config PATH` で、名前・値・意味は pr-review-fix-loop の `start` と同じ。`--merge` と一緒のときだけ受け付ける。`--merge` もループ用のオプションも、Issue の参照の前でも後でも書ける。**利用者が書いたものだけを、書いた順に渡す。** 既定値を足さない（ループの既定はサイクルの上限 3、レビュアーと担当は agent-runner の設定のとおり）
- `--hold-action` は受け付けない（このリポジトリの review-fix-planning には判断保留が無く、ループも受け付けない）。`--fresh-review` も受け付けない（作ったばかりの PR には再利用するレビューが無い）
- ループの `--assign implement=…` はレビュー修正の担当（`workflows.fix` の `implement`）で、Plan の Task の担当（`--implement`）ではない。ループの `--template`・`--config` も `implement_task.py check` には渡さない
- 使えるのは、`TARGET_REPO`（2 章の 5）が usaturn/create-reso-world か usaturn/resoloop のときだけ（ループが扱え、`finalize.py` がマージしてよい範囲）
- `--merge` のときは、Plan の実行予算（4 章の 3）にループの段階を含める（目安はサイクルの上限 ×（レビューの期限 45 分＋計画・修正））
- 手順は 2 章の 3 の `check-options`、5 章の検証の記録と「`--merge` のとき: PR の作成後のループ」。`--merge` が無い run は PR の作成で終わり、ループもマージもしない

## 2. 入力・対象・競合の確認

1. 作業対象に適用される AGENTS.md を読む（ルートの「リポジトリ境界」「Spec・Plan の保存と公開」「GitHub Actions」を含む）。
2. スキルの実ディレクトリを `SKILL_DIR` とし、create-reso-world の main checkout `PARENT_ROOT` を求めて、`origin` が usaturn/create-reso-world であることを確かめる。

   ```bash
   set -euo pipefail
   git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
   while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
   git_common_dir="$(git -C "$SKILL_DIR" rev-parse --path-format=absolute --git-common-dir)" || exit 2
   PARENT_ROOT="$(dirname "$git_common_dir")" || exit 2
   git -C "$PARENT_ROOT" remote get-url origin || exit 2
   ```

3. `INPUT` は、**利用者が書いた引数の先頭から、Issue の参照とオプションのうち最後のものまでを、書かれたまま切り出した文字列**である。後ろに続く自然文は含めない（`#12 推奨案で進めて` なら `#12`、`#12 --merge --max-cycles 2 途中で止めずに` なら `#12 --merge --max-cycles 2`）。語を足したり並べ替えたりしない。読み取り専用の helper を、起動したときの cwd のまま（checkout のルートへ `cd` せずに）実行する。

   `SESSION` は `PARENT_ROOT/tmp/agents/` の、この run のセッションディレクトリ（`agent_tmp.py mkdir issue-N`）にする。以降の Bash ブロックは配列・変数・関数を共有する。別シェルに移るときは、最初に `set -euo pipefail` を実行し、保存 JSON から同じ値を読み戻し（読み込みの失敗は `|| exit 2` で止める）、関数を定義し直す。publish が scan で決める SHA は `SESSION` のファイル（`code-sha.txt`・`docs-sha.txt`）に保存し、`pr` ブロックは同じシェルでも別シェルでも先頭でそこから読む（無い・空なら PR を作る前に止まる）。文書を分けるかの `DOCS_SEPARATE` も、`pr` ブロックは `target.json` から決め直す。各ブロックは先頭で helper と同じ規則（`scripts/git_env.py`）により継承した `GIT_*` を除去し（remote の認証に使う transport の設定 `TRANSPORT_AUTH` は残す）、検証・worktree・diff・scan・push・PR 作成で同じ Git 環境を使う。ブロックは bash と zsh のどちらでもそのまま実行できる。**停止は errexit に頼らない。** ランタイムがブロックを `&&` の並びの中の `eval` で実行すると（Claude Code の Bash ツール）`set -e` は効かないので、失敗すると後続が無効になるコマンド（helper と値の読み込み、`recheck_bases`、`[ -n … ]`、`jq -e`、worktree の作成、push、PR の作成と保存）に `|| exit 2` を付けている。`set -euo pipefail` は errexit が効くシェルでの二重の守りとして残す。ブロックは先頭から最上位のコマンド列として実行し、`|| exit 2` を外したり、`if` の条件や `&&` / `||` の一部に包んだりしない。終了コードが 0 でないブロックの後は、次のブロックへ進まない。base の取得をやり直して SHA を差し替えない。引数は引用と Bash 配列で渡し、`eval` しない。

   <!-- base-workflow:input -->
   ```bash
   set -euo pipefail
   git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
   while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
   uv run --no-project python "$SKILL_DIR/scripts/resolve_issue.py" --parent-root "$PARENT_ROOT" -- "$INPUT" > "$SESSION/issue.json" || exit 2
   merge_requested="$(jq -r '.merge != null' "$SESSION/issue.json")" || exit 2
   if [ "$merge_requested" = true ]; then
     merge_base="$(jq -r .base "$SESSION/issue.json")" || exit 2
     if [ "$merge_base" != main ]; then
       printf '%s\n' "BASE が統合用 branch（${merge_base}）のため --merge を適用しない。ループと finalize.py は既定 branch（main）へのマージと Issue の close を前提にする" > "$SESSION/merge-disabled.txt" || exit 2
     fi
   fi
   ```

   - 受け付ける表記: `https://github.com/<owner>/<repo>/issues/N`、`<owner>/<repo>#N`、`#N`（**現在の checkout の origin** で解決する。番号からリポジトリを推測しない）。対象は既存 parent / fork / meshy と、検証済み常設親の採用済み台帳にある通常ツール。未登録 repo の新規実装は扱わない
   - 成功: 終了コード 0、`repo`・`number`・`url`・`title`・`body`・`merge`・`implement`・`spec_review`・`design_review`・`base`・`base_explicit` の JSON。`merge` は `--merge` が無ければ `null`、あれば `{"loop_args": [...]}`（利用者が書いた順のループ用のオプション。パスは絶対パス）。`implement` は `--implement` の値か `null`。`spec_review`・`design_review` は明示値か `null`。`base` は branch 名（未指定は対象の既定 base）、`base_explicit` は利用者が指定したかの真偽値。`--base` は `merge.loop_args` には含めず、ループにも渡さない。**最初に `repo` と `title` を利用者に表示する。** 失敗: 終了コード 2 と stderr の理由。副作用に進まずに止まる
   - cwd が git の追跡しないディレクトリ（ワールドのプロジェクトなど）の中にあると（`git check-ignore -q .` が成功する）、helper は入力を読む前に終了コード 2 で止まる。下の「ワールドの作業で止まったとき」に従う
   - helper は入力の字句検証 → repo 解決 → profile 検査 → Issue 読取の順で進む。登録済み通常ツールの `--merge` は GitHub 照会の前に止める。登録は作成・clone・実装・公開・マージの許可ではない
   - helper は入力・対象の検証と Issue の確認だけで、競合・予約・承認を確かめた証拠にはならない
   - `merge` が非 null で `base` が `main` でないとき、input ブロックは理由を `$SESSION/merge-disabled.txt` に記録する（下の 5 の規則: 統合用 branch では `--merge` を適用しない）。`issue.json` の `merge` は非 null のままにする
   - `merge` が `null` でなく、かつ `merge-disabled.txt` が無いときだけ、続けて `PARENT_ROOT` の `loop.py` で、ループ用のオプションと agent-runner の設定を検査する。無効化された run はループ設定の検査を起動せず（使わないループの設定の不備で PR 作成が止まらないようにする）、記録された理由を利用者に伝えて `--merge` が無い run として続ける。`loop_args` の要素を順に、それぞれ 1 つの引数として渡す（空なら引数なし）。

     ```bash
     uv run --project "$PARENT_ROOT" --locked python \
       "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" check-options <loop_args の各要素>
     ```

     終了コード 0 なら、出力の `options`・`assignments` を Spec の決定記録に写す（既定値は既定の適用と書き、利用者の指定と書かない）。終了コード 2 なら `reason`（argparse の拒否は stderr）を利用者に伝えて止まる。worktree・Herdr・予約のどれにも触れない。

   - 続けて Plan の実装の担当を検査する。`implement` が `null` でなければ `--implement <implement の値>` を付け（値は 1 つの引数として渡す）、`null` なら付けない。

     ```bash
     uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/implement_task.py" check [--implement <値>]
     ```

     終了コード 0 なら、出力の `assignment`（`agents`・`fallback`）と `self` を Spec の決定記録に写す（雛形の既定の `self` は既定の適用と書き、利用者の指定と書かない）。終了コード 2 なら `reason` を利用者に伝えて止まる（設定に無い agent、`agents` が 2 つ以上、`implement` の役割の `writes = false` など）。worktree・Herdr・予約のどれにも触れない。

   - 続けて、明示されたレビューの担当だけを検査する。`spec_review`・`design_review` が `null` なら、その helper の `check` を起動しない（設定だけを理由に起動しない）。値があるときだけ、対応する helper を実行する。

     ```bash
     uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/review_design.py" check --design-review <値>
     uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/review_spec.py" check --spec-review <値>
     ```

     終了コード 0 なら、出力の `assignment`（`agents`・`fallback`）と `self` を決定記録に写す（明示値と、個人設定で保たれた `fallback` を区別して書く）。終了コード 2 なら `reason` を利用者に伝えて止まる（設定に無い agent、`agents` が 2 つ以上、レビュー役割の `writes` が `true`、`agents` の無い個人設定の assignment など）。worktree・Herdr・予約のどれにも触れない。ループ用の `--template`・`--config` はここに渡さない。

4. 本文、全ページのコメント、依存関係を読む。本文が利用者の承認・判断を求めていて、決定の記録が無ければ、推奨案での委任で代えずに止まる。Issue がワールドのプロジェクト（`worlds/<name>/` と従来位置）の中身を変える作業を含むときも止まり、下の「ワールドの作業で止まったとき」に従う（雛形の `templates/world-project/` や `scripts/new-world.sh` など、追跡するファイルの変更は当たらない）。
5. 実装の対象 `TARGET_REPO` を決める。既定は helper の `repo`。本文に実装対象が明記されていればそれを使い、Issue の repo と混同しない。既存 parent / fork / meshy または採用済み台帳の通常ツールだけを扱う。対象 checkout を共通 context helper で解決し、その `code_root` を `TARGET_ROOT` にする。未知 repo に明示 `CODE_ROOT` を渡して新規実装を許可しない（その経路は PR レビュー・承認済み review-fix 専用）。

   <!-- base-workflow:target -->
   ```bash
   set -euo pipefail
   git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
   while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
   target_args=()
   if [ "$TARGET_REPO" = usaturn/resoloop-meshy ]; then
     target_args+=(--code-root "$PARENT_ROOT/external/resoloop-meshy")
   fi
   uv run --no-project python "$PARENT_ROOT/scripts/superpowers_context.py" \
     --operation review-workspace --parent-root "$PARENT_ROOT" --repo "$TARGET_REPO" \
     "${target_args[@]}" > "$SESSION/target.json" || exit 2
   TARGET_ROOT="$(jq -er .code_root "$SESSION/target.json")" || exit 2
   DOCS_SEPARATE="$(jq -r 'if (.document_repository | type) == "string" and (.repository | type) == "string" then .document_repository != .repository else error("target.json lacks document_repository") end' "$SESSION/target.json")" || exit 2
   merge_requested="$(jq -r '.merge != null' "$SESSION/issue.json")" || exit 2
   if [ "$merge_requested" = true ] && [ ! -f "$SESSION/merge-disabled.txt" ]; then
     case "$TARGET_REPO" in
       usaturn/create-reso-world|usaturn/resoloop) ;;
       *) printf '%s\n' 'この対象は手動マージです。--merge を外して指示し直してください' >&2; exit 2 ;;
     esac
   fi
   ```

   - `BASE` が統合用 branch（既定の `main` 以外）のときは `--merge` を適用しない（判定と記録は 3 の input ブロック）。理由（ループと `finalize.py` は既定 branch へのマージと Issue の close を前提にする）を利用者に伝え、`--merge` が無い run として続ける。ループ用オプションは使わず、最終の全体レビューを行い、CI 必須の対象は CI green を確認して PR の作成で終える
   - 上の手動マージ拒否（meshy・登録済み通常ツール）は `merge_requested=true` かつ `merge-disabled.txt` が無いときだけ適用する。無効化済みの run は `--merge` なしとして続行する（対象・権限の確認は維持）
   - 登録済み通常ツールは `managed-tool-v1`（手動マージ）。context の結果は常設 checkout に限り、実装は後で作る同 common-dir の名前付き branch の linked worktree で行う。台帳が壊れている・未採用・checkout 不在・remote/送信先不一致・候補が複数なら停止し、親や近くの repo に切り替えない。clone・探索はしない
   - 検証コマンド・編集範囲・追加の実行許可は、解決した repo 自身の `AGENTS.md` と `README.md` を読んで決める。登録済み通常ツールの base / CI は共通 CLI（`PARENT_ROOT` で `uv run --no-project python -m tools.external_tools list`、対象 key の `show`）の採用済み情報を使う。`ci=required` は PR checks の成功を確認し、`disabled` だけを免除する。別 repo や未知 repo に CI 免除を広げない
   - 既存 parent / fork / meshy の特殊経路・検証・CI はルート `AGENTS.md`、`README.md`、fork は `docs/resoloop-fork-workflow.md`、meshy は `docs/resoloop-meshy-workflow.md` に従う。不在時も各手順書の clone コマンドを案内して停止し、自動取得しない
   - コードの PR / base は `TARGET_REPO` / `TARGET_ROOT` のもの。Spec・Plan を置くリポジトリは context の `document_repository` で決まる（ルート `AGENTS.md` の「Spec・Plan の保存と公開」）。target ブロックは、それが context の `repository` と違うか（どちらも helper が小文字にした名前で比べる）を `DOCS_SEPARATE` にする。`true` なら create-reso-world の `DOC_ROOT` に保存し、文書 PR を create-reso-world / main に分離する。`false` なら（create-reso-world 自身と、`AGENTS.md` で宣言した通常ツール）、Spec・Plan をコードと同じ worktree・PR に入れ、文書専用の PR を出さない。通常ツールを登録しただけで文書の保存先やマージ許可は変わらない

6. **worktree を作る前に**次を調べる。どれかあれば、新しい作業を作らずに状態を報告して止まる。古い予約も、作った人が分からない既存の worktree・branch も使い回さない。
   - 同じ Issue の open PR（`TARGET_REPO` と、文書専用の PR を出す場合は create-reso-world。linked Issue、本文、branch を見る。最初のページだけで判定しない）
   - 同じ Issue のマージ済みの PR があり（探し方は open PR と同じ）、本文・コメントから、PR にする作業が残っていないと分かる（残りがマージの後の確認だけ、など）。その PR の URL と残りの確認を報告する
   - create-reso-world の `refs/heads/agent-claims/issue-N`、コメントに記録された未解放の担当
   - `TARGET_ROOT`（と文書用の worktree を作る場合は `PARENT_ROOT`）の既存の worktree、ローカル・remote の branch（`issue-N` を番号の境界で照合し、N=58 と N=580 を混同しない）
   - 未完了の先行 Issue・必要な未マージ PR

   既存の open PR で止まるときは、その PR の URL と base（`gh pr view <PR> --repo <repo> --json url,baseRefName`）を報告し、レビューは `/pr-review <PR の URL>`、指摘の修正の計画は `review-fix-planning` で行えると伝える。案内には PR の URL を使う（番号だけでは、別のリポジトリの PR を cwd の origin の PR として解決する）。`--merge` があっても、既存の PR をループに乗せない（`loop.py start` を実行しない）。ループで続けるかは利用者が決める。base が対象 repository の既定 branch なら、続けるなら `/pr-review-fix-loop <PR の URL>` で行えると案内する。base がそれ以外（統合用 branch など）ならループを案内せず、`/pr-review <PR の URL>`（マージしない）だけを案内する（ループはマージまで進めてしまうため）。

   worktree を作る直前と、push・PR の作成の前に、Issue の状態と競合を調べ直す。新しい競合や close があれば止まり、この run で作った worktree・branch と他者の作業を区別して報告する。

   **base の確定:** 競合を確認した後、worktree の前に、根拠とともに確認した親 Issue・handoff の要求 base を `$SESSION/required-bases.txt` に 1 行に 1 つの branch で書く（`printf '%s\n' <branch>... > "$SESSION/required-bases.txt"`）。要求が無ければ空のファイルにする（`: > "$SESSION/required-bases.txt"`）。シェルの配列や変数で渡さない（別の呼び出しのシェルには残らず、bash では未定義の配列が黙って空になる）。capture は同じシェルでも別シェルでもこのファイルから読み、無い・読めないときは worktree の前に止まる。Issue の repository でなく `TARGET_REPO` / `TARGET_ROOT` を使う。次の helper は objects だけを取得し、remote-tracking ref や FETCH_HEAD を更新しない。成功時の JSON（`repo`・`remote`・`branch`・`ref`・`sha`）を保存する。終了コード 2 は副作用の前に停止し、理由を伝える。

   <!-- base-workflow:capture -->
   ```bash
   set -euo pipefail
   git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
   while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
   base_args=()
   base_explicit="$(jq -r .base_explicit "$SESSION/issue.json")" || exit 2
   if [ "$base_explicit" = true ]; then
     explicit_base="$(jq -r .base "$SESSION/issue.json")" || exit 2
     base_args+=(--base "$explicit_base")
   fi
   required_bases="$(cat "$SESSION/required-bases.txt")" || exit 2
   while IFS= read -r required; do [ -z "$required" ] || base_args+=(--required-base "$required"); done <<< "$required_bases"
   uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
     --checkout "$TARGET_ROOT" --repo "$TARGET_REPO" "${base_args[@]}" > "$SESSION/code-base.json" || exit 2
   CODE_BASE_BRANCH="$(jq -r .branch "$SESSION/code-base.json")" || exit 2
   CODE_BASE_SHA="$(jq -r .sha "$SESSION/code-base.json")" || exit 2
   if [ "$DOCS_SEPARATE" != false ]; then
     uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
       --checkout "$PARENT_ROOT" --repo usaturn/create-reso-world > "$SESSION/docs-base.json" || exit 2
     DOC_BASE_SHA="$(jq -r .sha "$SESSION/docs-base.json")" || exit 2
   fi
   recheck_bases() {
     uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
       --checkout "$TARGET_ROOT" --repo "$TARGET_REPO" --base "$CODE_BASE_BRANCH" \
       --expected-sha "$CODE_BASE_SHA" > "$SESSION/code-base-recheck.json" || return
     if [ "$DOCS_SEPARATE" != false ]; then
       uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
         --checkout "$PARENT_ROOT" --repo usaturn/create-reso-world --base main \
         --expected-sha "$DOC_BASE_SHA" > "$SESSION/docs-base-recheck.json" || return
     fi
   }
   ```

   `recheck_bases` は origin の対象と完全 ref の先端を捕捉した SHA に照合する。worktree の直前、差分の確認、scan の前、全 scan 後の各 push の直前、各 PR 作成の直前と作成後に実行する。移動を観測したら新 SHA を採用せず停止し、旧/新 SHA・差分・必要な再検証を報告する。複数 repository を一括ロックする保証はない。

7. ボードの子（GitHub の親 Issue があり、子か親の本文にボードのキーがある）は **`planning-parallel-issues` 必須**。予約・先行条件・成果の公開・所有権の再確認・解放はそちらに従い、このスキルに写さない。親からの子の選択は担当外。

`gh issue`・`gh pr` には毎回 `--repo` を付ける。`gh api` は `--repo` を受け付けないので、`repos/<owner>/<repo>/...` の完全な endpoint で対象を固定し、一覧は `--paginate` で取る。

### ワールドの作業で止まったとき

worktree・branch・Spec・Plan・PR を作らない（ワールドのプロジェクトは create-reso-world の git の追跡対象外で worktree に実体が無く、`Closes #N` の PR をマージすると、ワールドの作業が済まないまま Issue が閉じる）。ワールドの作業は、そのプロジェクトを cwd にし、プロジェクトの `AGENTS.md` に従って進める（独自の `.git` を持たないプロジェクトでは branch・PR を使わない。`AGENTS.md` の「プロジェクト運用」）。リポジトリのファイルを変える作業は、checkout のルートで起動し直す。両方を含む Issue は、ワールドの作業とリポジトリの変更に分けるよう伝える。

- 利用者が明示して起動した run（`/issue-to-pr`、Pi の `/skill:issue-to-pr`・`/sp-brainstorm`）: 理由と進め方を伝えて終える。ワールドの作業には進まない
- モデルが自分の判断でこのスキルを選んだ run: このスキルを離れる。cwd がその Issue のワールドのプロジェクトなら、ワールドの作業として進める。そうでなければ進め方を伝えて終える

## 3. Herdr と作業場所

着手の条件がそろったら、`HERDR_ENV=1` のときに `herdr-agent-task` と `herdr` を読む。**現在の pane** の名前とタスクを設定する。ほかの pane や focus を変えない。ペイン名は `<Issue の repo の repo 部分>:#<Issue 番号>`（例: `create-reso-world:#355`）にする。repo 部分は解決した Issue の repo（`issue.json` の `repo`）で、実装の対象（`TARGET_REPO`）や PR の repo から作らない。Issue と実装対象が別リポジトリでも、同じ Issue の識別を保つためである。

```bash
ISSUE_REPO="$(jq -r .repo "$SESSION/issue.json")" || exit 2
pane_label="${ISSUE_REPO##*/}:#${NUMBER:?}"
herdr pane rename "${HERDR_PANE_ID:?}" "$pane_label" && ISSUE_PANE_ID="${HERDR_PANE_ID}" && ISSUE_PANE_LABEL="$pane_label"
herdr-agent-task set "Issue #$NUMBER 実装・PR作成"
```

rename が成功したときだけ `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL` が確定する。run の間この 2 つを保持し、終了状態の更新（下の「ペイン名の終了状態」）にも同じラベルを使う。現在の pane が分からない・rename が失敗したときは、別の pane を推測せず、rename を省いて続け、最終報告に書く。この run では `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL` が確定しないので、終了状態の更新もしない。

**必須:** `superpowers:using-git-worktrees` に従い、status・worktree 一覧・ignore を確かめる。名前と未使用の branch を下の規則で決め、コードの絶対パスを `CODE_ROOT`、branch を `CODE_BRANCH` にする。文書を分離する場合はその絶対パスを `DOC_ROOT`、branch を `DOC_BRANCH` にし、分離しない場合は `DOC_ROOT="$CODE_ROOT"`。再確認後、捕捉した SHA から新しい worktree を作る（未更新の `origin/<branch>` を開始点にしない）。

- 名前は `issue-N-<要約>`、branch は `feat/issue-N-<要約>` か `fix/issue-N-<要約>`。Issue が `TARGET_REPO` と別のリポジトリにあるときは、名前と branch の `issue-N` の前にそのリポジトリ名を付ける（create-reso-world の #203 を resoloop で実装するなら `create-reso-world-issue-203-<要約>`）
- `DOCS_SEPARATE` が `true` なら、Spec・Plan 用に `PARENT_ROOT/.worktrees/<名前>` にも、branch `docs/<名前>` の worktree を文書用に捕捉した main の SHA から作る（Issue が create-reso-world の外にあるときは、`<名前>` の先頭にそのリポジトリ名を付ける）
- main checkout（detached HEAD）では編集しない

<!-- base-workflow:worktree -->
```bash
set -euo pipefail
git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
recheck_bases || exit 2
git -C "$TARGET_ROOT" worktree add -b "$CODE_BRANCH" "$CODE_ROOT" "$CODE_BASE_SHA" || exit 2
if [ "$DOCS_SEPARATE" != false ]; then
  git -C "$PARENT_ROOT" worktree add -b "$DOC_BRANCH" "$DOC_ROOT" "$DOC_BASE_SHA" || exit 2
fi
```

以降、Spec・Plan を置く checkout を `DOC_ROOT` と呼ぶ（`DOCS_SEPARATE` が `false` なら実装の worktree、`true` なら create-reso-world の文書用の worktree）。

### ペイン名の終了状態（Issue 起点の run だけ）

`HERDR_ENV=1` で、かつ開始時の rename が成功して `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL` が確定している run だけ、終了時にペイン名を更新する。開始時の rename が失敗・スキップだった run は更新しない（ラベルが確定していないため）。別の pane を探さず、rename の再帰的な再試行もしない。この表示処理で既存の停止・回収・マージ権限は変えない。

| run の結果 | ペイン名 |
| --- | --- |
| 対応 PR のマージ成功を確認（finalize の `merged: true`、ループの `no_fix_needed` でマージ済みなど） | 確認した時点で `${ISSUE_PANE_LABEL}:END` |
| 予期しない障害で中断 | 停止報告の前に `${ISSUE_PANE_LABEL}:Glitch` |
| PR 作成だけの完了・マージ未実施・通常の工程区切り/待機・想定された停止 | 名前を維持 |

マージ成功を確認した時点で:

```bash
herdr pane rename "${ISSUE_PANE_ID:?}" "${ISSUE_PANE_LABEL}:END"
```

予期しない障害で中断するとき（停止報告の前）:

```bash
herdr pane rename "${ISSUE_PANE_ID:?}" "${ISSUE_PANE_LABEL}:Glitch"
```

分類は次のとおり。ループ helper の `stopped`・`error` の値だけで決めず、`stage`・`reason` と実際の原因で分類する。

- **予期しない障害（`:Glitch`）:** 必要なツール/API の失敗、担当の起動・結果形式の失敗（設計レビュー・Spec レビューの失敗を含む）、全レビュアーの失敗、資源の停止未確認、解消できない検証失敗、後片付けなどの実行障害。マージ後に関連 Issue の更新などが失敗して中断する場合は `Glitch` を優先し、報告ではマージ成功と未完了の後続処理を分ける
- **想定された停止（名前を維持）:** 不正入力・設定の事前拒否、競合・claim/ロック、Issue の closed 化、未完了依存、明示承認待ち、許可されない操作・安全境界での停止、Spec/設計レビューの `decide` の `stop`、builder check の利用者判断、PR の HEAD 移動、base の捕捉後の移動、実行予算・サイクルの上限。CI 待ちなどの待機や、run を中断せず再試行・回復する一時的な失敗も `Glitch` にしない

終了状態の rename が失敗しても、元の停止理由・マージ結果を隠さず、それと別に「pane 名が未更新であること」を報告する。

## 4. 推奨案 → Spec → Plan → 実装

1. **`superpowers:brainstorming` 必須。** 利用者はこの指示で質問を省くことを選んでいるので、問答をせずに推奨案を選ぶ。意図・受け入れ条件・編集禁止を整理する。
2. Spec を `DOC_ROOT` の `docs/superpowers/specs/` に書いて commit する。冒頭に管理・実行許可（利用者の指示の引用、許可された範囲、状態 `draft`）を書き、`approved` にしない。**決定記録**を設け、各項目に「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」を残す。確認用のコピー（`scripts/superpowers-review-copy.sh`）は作らない。

### Spec・設計レビュー（明示されたときだけ）

`--spec-review` / `--design-review` が無い run は、この節の helper を起動せず、3 の builder check に進む。ある run は、Spec の commit の後、writing-plans の前に次を行う。設計レビュー → Spec レビューの順で、`--design-review` が無ければ設計レビューを省き、`--spec-review` が無ければ Spec レビューを省く。Spec レビューがある run は builder check を行わない。設計レビューは builder check を代替しない。

レビューの記録は `SESSION` の下だけに置き、コード・Spec の worktree には置かない。`--ledger-dir` には常に `"$SESSION"` を明示する（環境変数や既定値に任せない）。外部担当の runner の出力先も、`SESSION` の下のまだ存在しないパス（例: `"$SESSION/review-runner/design-1"`）にする。`review-runner` のような親ディレクトリは、外部レビューの前に `mkdir -p "$SESSION/review-runner"` で作り、runner-dir 自体はまだ存在しない状態を保つ（実 runner は親を作らない）。ledger と runner-dir が互いを含む場合、worktree の中にある場合、symlink の場合は helper が終了コード 2 で拒否する。拒否されたら、別の場所を推測せずに止まる。

**依頼 JSON は、設計レビュー・Spec レビュー・再レビューのそれぞれを始める直前に作る。** ファイル名は review ごとに分け（例: `"$SESSION/<spec-stem>.design-request.json"`・`"$SESSION/<spec-stem>.spec-request.json"`・`"$SESSION/<spec-stem>.spec-rereview-request.json"`）、`ReviewRequest` を書く。`spec_path` は `DOC_ROOT` の Spec の絶対パス、`repository` はレビューする `CODE_ROOT` の絶対パス、`revision` はその時点の `git -C "$CODE_ROOT" rev-parse HEAD` の完全 SHA、`issue` は `issue.json` の `repo`・`number`・`url`・`title`・`body`、`context` は Issue のコメントの要点・適用する AGENTS.md・受け入れ条件など（複数行の日本語可）。`spec_path` と `repository` は別の worktree でよい。**Spec を commit した後は `CODE_ROOT` の HEAD が変わりうる（`DOC_ROOT` と `CODE_ROOT` が同じ checkout なら必ず変わる）ので、前のレビューの依頼を使い回さず、review の直前に今の HEAD で作り直す。** helper は review の開始時に `revision` と現在の HEAD を照合し、違えば終了コード 2 で拒否する。

   ```json
   {
     "spec_path": "/abs/DOC_ROOT/docs/superpowers/specs/...-design.md",
     "repository": "/abs/CODE_ROOT",
     "revision": "<CODE_ROOT の完全 HEAD SHA>",
     "issue": {"repo": "usaturn/create-reso-world", "number": 42, "url": "https://github.com/usaturn/create-reso-world/issues/42", "title": "...", "body": "..."},
     "context": "複数行の日本語の文脈"
   }
   ```

**設計レビュー（`--design-review` があるときだけ）。** 次の helper を実行する。外部担当のときは `--runner-dir` を付け、`self` のときは付けない。`--runner-dir` はまだ存在しないパスにする。

   ```bash
   mkdir -p "$SESSION/review-runner" || exit 2
   uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/../../../tools/agent_runner/with_keys.py" -- \
     python "$SKILL_DIR/scripts/review_design.py" review \
     --request "$SESSION/<spec-stem>.design-request.json" \
     --ledger-dir "$SESSION" \
     --design-review <値> \
     --runner-dir "$SESSION/review-runner/design-1"
   ```

   `with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）。wrapper は後段と同じ checkout のものを使う。上の `$SKILL_DIR/../../../tools/agent_runner/with_keys.py` は helper と同じ checkout から導く。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す。helper に `--template`・`--config` を渡すときは、wrapper の `--` の前にも同じ値を渡す。wrapper と helper が同じ checkout のとき、渡さない既定では両方がその checkout の雛形と `resolve_config_path()` の個人設定を使うので、何も足さなくてよい。

   出力が `state: self` なら、`prompt_path` の依頼文を読み、出力の `review_id`・`spec_sha256` を使って結果 JSON を `"$SESSION/<spec-stem>.design-result.json"` に書く。

   ```json
   {
     "review_id": "<review の出力>",
     "spec_sha256": "<review の出力>",
     "status": "completed",
     "verdict": "sound",
     "assessment": "設計は妥当",
     "concerns": [],
     "questions_for_user": [],
     "incomplete": []
   }
   ```

   指摘があるときは、prompt の `RESULT_SHAPE` の全項目（`id`・`decision_ref`・`problem`・`evidence`・`alternative`・`tradeoffs`・`impact`・`recommendation`・`severity`）を埋める。`self` の結果は次の `submit` で記録する。`state: completed` なら外部担当のレビューが完了している。**review の標準出力は `findings` / `concerns` の件数だけなので、採否を作る前に、出力の `review_dir` にある `review.json` を読み、`result` の `findings` / `concerns` の本文を使う。** `state: failed`、`status: incomplete`、`review_id` / `spec_sha256` の不一致、`outside_changes`、Spec / HEAD の変化はレビュー失敗であり、指摘 0 件として扱わない。失敗したらそのレビューを成功にせず止まる。`unprotected_changes` は記録して報告するが、それだけで失敗にしない。

   ```bash
   uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/review_design.py" submit \
     --review-dir "<review_dir>" --result "$SESSION/<spec-stem>.design-result.json"
   ```

   `submit` の終了コード 1 はレビュー失敗、2 は結果の形・`review_id`・`spec_sha256` の拒否である。どちらも採否へ進まず止まる（拒否では `review.json` を作らない。`review_dir` と理由を報告する）。

**Spec レビュー（`--spec-review` があるときだけ）。** 設計レビューを行った場合はその採否を Spec に反映して commit した後、行っていない場合は Spec の commit 後に行う。**review を始める直前に、その時点の `CODE_ROOT` HEAD で新しい依頼 JSON（例: `"$SESSION/<spec-stem>.spec-request.json"`）を作り、`--request` に渡す。前の設計レビューの依頼を使い回さない。** 手順は設計レビューと同じで、`review_design.py` の代わりに `review_spec.py` を使い、`--design-review` の代わりに `--spec-review` を渡す。`review_spec.py review` も設計レビューと同じ wrapper（`$SKILL_DIR/../../../tools/agent_runner/with_keys.py`）を通す。`with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）。wrapper は後段と同じ checkout のものを使う。このパスは helper と同じ checkout から導く。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す。helper に `--template`・`--config` を渡すときは、wrapper の `--` の前にも同じ値を渡す。wrapper と helper が同じ checkout のとき、渡さない既定では両方がその checkout の雛形と `resolve_config_path()` の個人設定を使うので、何も足さなくてよい。結果は `status`・`findings`・`incomplete` を持ち、runner-dir は `"$SESSION/review-runner/spec-1"` のような新しいパスにし、親の `"$SESSION/review-runner"` は先に `mkdir -p` で作る（設計レビューを行わない run でも同じ）。`self` の結果は `{"review_id": "<review の出力>", "spec_sha256": "<review の出力>", "status": "completed", "findings": [], "incomplete": []}` の形で、指摘は prompt の `RESULT_SHAPE` の `id`・`section`・`problem`・`evidence`・`impact`・`severity`・`suggestion` を埋める。`review_spec.py submit --review-dir "<review_dir>" --result "$SESSION/<spec-stem>.spec-result.json"` で記録し、終了コード 1/2 は設計レビューと同じく停止する。設計レビューを 2 回目に始める場合や、Spec レビューの後に設計レビューを始める場合は、helper が拒否する。拒否されたら順序を変えずに止まる。

**採否を記録する。** 結果のすべての `findings` / `concerns` を、重複なく 1 回ずつ採否に含める。採用する指摘は Spec の該当箇所に反映し、`decide` の前に、既知のレビュー記録（`review_dir`・`review_id`・reviewed の SHA・担当・回数・`elapsed_seconds`・`requested_agent`・`actual_agent`・`identity`・`fallback` の使用・`outside_changes`・`unprotected_changes`）も決定記録に追記する。Spec の実質的な反映と、Spec に書くレビュー記録はこの時点で済ませる。reflected の SHA は `decide` が返すまで存在しないので、Spec に書かず、`decide` の後に SESSION と最終報告へ記録する。記録の追記だけを採用の反映にしない。

   ```json
   {"decisions": [
     {"id": "S1", "decision": "adopt", "reason": "...", "reflected_in": "..."},
     {"id": "S2", "decision": "reject", "reason": "...", "reflected_in": null}
   ]}
   ```

   設計レビューは `changes_what_is_built` を持ち、`true` の採用と `recommendation: ask_user` の採用はできない。採否を決められないときは `needs_judgment` にして止まる。

   ```json
   {"decisions": [
     {"id": "D1", "decision": "reject", "changes_what_is_built": false, "reason": "...", "reflected_in": null}
   ]}
   ```

   ```bash
   uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/review_spec.py" decide \
     --review-dir "<review_dir>" --decisions "$SESSION/<spec-stem>.spec-decisions.json"
   ```

   設計レビューでは `review_design.py decide` を使う。`decide` の終了コード 2 は、採否の欠落・重複・未反映、版の不一致などの拒否である。拒否では採否も反映後 snapshot も書かれないので、Spec を commit せずに止まり、変更内容と `review_dir` を報告する。成功したら、出力の `reviewed_spec_sha256`・`reflected_spec_sha256` を SESSION の記録に書き、最終報告に使う。`reflected_spec_sha256` は `decisions.json` と `reflected.md` の同じ値であり、Spec へ書き戻さない。commit するときは Spec を `reflected.md` と同じバイト列にし、その SHA が `reflected_spec_sha256` と一致する状態を保つ（SESSION への記録だけでは Spec を変えない）。出力の `next` が `stop` なら、記録してから止まる（Spec は commit しない）。設計レビューの `next: continue` は Spec を commit して次へ進む。Spec レビューの `next: plan` は Spec を commit して 3 へ進む。`next: rereview` は初回に `important` を採用したときだけで、Spec を commit してから、新しい依頼 JSON（例: `"$SESSION/<spec-stem>.spec-rereview-request.json"`）をその時点の `CODE_ROOT` HEAD で作り、同じ担当のまま新しい runner-dir で 1 回だけ再レビューする。前回の依頼の `revision` を使い回さない。2 回目を超える再レビュー、閉じた gate の後の新規レビュー、担当を変えた再レビューは helper が拒否するので、やり直さず止まる。

**後片付けと記録。** 結果と採否を記録したレビュー、および失敗して結果だけが記録されたレビューについて `cleanup --review-dir "<review_dir>"` を実行する。`self` では何もしない。外部担当では、停止を確認できた試行の worktree と、安全に片付いた runner-dir だけを消し、レビューの記録（ledger）は残す。`retained` は消さず、完全パスと理由を記録して最終報告（止まるときは停止報告）に含める。停止未確認の試行が残る場合は、そのレビューを成功扱いせず止まる。結果の記録が無いレビューでは `cleanup` を使わず、runner-dir のパスを報告する。`cleanup` の結果は SESSION の記録と最終報告に書き、レビュー済みの Spec の版を変えない。

3. **Spec の builder check と `superpowers:writing-plans` 必須。** Spec レビューを行った run は builder check を省略し、Spec レビューが代わる。設計レビューだけ、またはどちらも無い run は、`superpowers:brainstorming` の builder check（読み取り専用の別 context。サブエージェントが使えなければ自分で builder として読む）を 1 回行い、Spec に反映して commit する。利用者にしか決められない指摘が残るなら止まる。その後 Plan を `DOC_ROOT` の `docs/superpowers/plans/` に作って commit する。実在する Spec のパス、Task、担当ファイル、検証の入口（2 章の 5 で読んだ repo 側の規則）、実行方式と理由、contingency を書く。AGENTS.md の SDD 実行運用に従う。実装前に [要件・原因・検証の対応](../review-fix-planning/references/convergence.md) の「1. 実装前の要件照合」を読み、Spec の条件・除外範囲と Task・観測結果・検証を照合する。共有する入力・状態・順序・外部仕様の確認は統合担当の Task にする。単純な変更は Plan の短い対応メモでよく、別帳票は作らない。
4. 実行方式は次で決める。ランタイムのツール仕様を確かめ、存在しない一覧操作や同期フラグを渡さない。リポジトリが要求する起動条件を満たせなければ inline を選ぶ。

   | 条件 | 選ぶ方式 |
   |---|---|
   | 2 章の 3 の `check` の `self` が false | 下の「Task の実装を runner の担当に依頼する」（`superpowers:subagent-driven-development` の形で、各 Task を runner の担当に依頼する） |
   | `self` が true で、Task が独立し、文脈を子に渡しきれ、同期委譲を使える | `superpowers:subagent-driven-development` |
   | `self` が true で、同じファイルの逐次変更、1–2 Task、委譲不可 | `superpowers:executing-plans` |

   Pi の `/sp-implement` は直列実行、`/sp-implement-parallel` は依存を満たした独立 Task を別 worktree で並列実行する入口。SDD なら常に parallel という対応ではない。同じファイルを同時に書かせない。run 中は選んだスキルで続け、コマンド再入力待ちにしない。
5. 選んだスキルの実装・TDD・レビューに従い、最後のブランチ全体のレビューを省かない。実装担当（inline なら自分）へ、照合した条件・除外範囲・共有前提・必要な証拠を渡す。個別 Task の成功だけで共通条件を満たしたとせず、統合担当が条件単位で確認する。スキルを作る場合は `superpowers:writing-skills` の無し/ありの振る舞い比較を行い、固定文言の検査テストで代用しない。テストは AGENTS.md の「テストの採用基準」に従い、迷ったら書かない。検証の失敗は `systematic-debugging` で調べ、解消できなければ止まる。
8. 項目 5 の例外として、`--merge` が適用される run は、実装スキルの最終のブランチ全体レビュー（全 Task の後のブランチ全体のレビュー）を行わず、ループの 1 サイクル目で代える。Task ごとのレビューは残す。最終レビューに回すはずだった minor の指摘（ledger の `deferred`）は PR 本文に一覧で書く。`--merge` が無い（適用されないを含む）run は最終レビューを省かない。「適用される」は 5 章のループ節の冒頭のとおり `merge-disabled.txt` が無い run を指す

### Task の実装を runner の担当に依頼する（`self` 以外のとき）

`superpowers:subagent-driven-development` を読み、Task を実装するサブエージェントの代わりに、`implement_task.py` で runner の担当に Task を 1 つずつ順に依頼する（並行しない）。runner の担当は入れ子に agent を起動できないので、Plan 全体を 1 回で渡さない。

1. **出力先:** `uv run --no-project python "$PARENT_ROOT/.agents/scripts/agent_tmp.py" mkdir issue-<N>-implement` で作った実装担当用のセッションディレクトリ（`IMPLEMENT_SESSION`）の下の、存在しないパス（例: `$IMPLEMENT_SESSION/task-2-attempt-1`）を依頼ごとの `RUN_DIR` にする。run 全体の `SESSION` は再定義せず、base JSON・検証記録を保持する。ログは後で参照するため、AGENTS.md の「コミットしないファイルの置き場所」に従う
2. **依頼の JSON（`REQUEST_JSON`）:** 次の 6 項目だけを書き、`$IMPLEMENT_SESSION` の下にファイルで置く。
   - `repository`: feature worktree（`TARGET_ROOT/.worktrees/<名前>`）の root の絶対パス。`revision`: その HEAD の完全な SHA（未 commit の変更を残さない）
   - `task`: 1 行の Task 名。`allowed_files`: Plan のその Task の担当ファイル（root からの相対パス。`/` で終わればディレクトリ）
   - `commit_message`: Plan の commit の手順のメッセージ（担当が commit できなかったときに helper が使う）
   - `prompt`: 担当がそれだけで作業できる依頼。Plan のその Task の全文、Spec の関係する節、受け入れ基準（Task をレビューする担当に渡すものと同じ）、実行する関連テストと静的チェック、テストの要否と理由。担当がどのスキルを読めるかはランタイムで違うので、スキルを前提にしない。作業範囲・禁止事項・返す JSON の形は helper が足す
3. **依頼:** 終わるまで待つ（`implement` の役割の期限は 90 分。`monitoring-long-tasks` に従い、Claude Code では `run_in_background: true` の完了通知で待つ）。

   ```bash
   uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/../../../tools/agent_runner/with_keys.py" -- \
     python "$SKILL_DIR/scripts/implement_task.py" run \
     --request "$REQUEST_JSON" --output-dir "$RUN_DIR" [--implement <値>]
   ```

   `with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）。wrapper は後段と同じ checkout のものを使う。上の `$SKILL_DIR/../../../tools/agent_runner/with_keys.py` は helper と同じ checkout から導く。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す。helper に `--template`・`--config` を渡すときは、wrapper の `--` の前にも同じ値を渡す。wrapper と helper が同じ checkout のとき、渡さない既定では両方がその checkout の雛形と `resolve_config_path()` の個人設定を使うので、何も足さなくてよい。

   出力の `verdict` で次を決める。どの `verdict` でも、次の依頼を出す前・止まる前に、その依頼の `RUN_DIR` を 5 のとおり片付ける。

   | `verdict` | 次の操作 |
   | --- | --- |
   | `importable` | `implement_task.py accept --run-dir "$RUN_DIR"`。判定を今の状態でやり直し、担当が commit しなかったとき（`helper_commit`）は helper が `commit_message` で commit してから、feature worktree に `--ff-only` で取り込む |
   | `no_changes` | 取り込むものは無い。Task のレビューで、変更が要らないことを確かめる |
   | `retry`（担当が `BLOCKED`・`NEEDS_CONTEXT`） | `result.concerns`・`result.incomplete` に答える文脈を `prompt` に足し、同じ担当に新しい依頼をする（新しい `RUN_DIR`）。回数は Plan の「実行予算」の再試行の上限まで。上限に達したら止まる |
   | `rejected`（`outside_changes`、取り込みの前の確認に反した） | 取り込まない。再試行の上限の中で依頼し直すか止まるかを決め、`reasons` と理由を ledger に書く |
   | `failed`（停止を確認できない、期限切れ・認証待ち・起動の失敗、`fallback` が尽きた。結果の形の誤りは runner が `fallback` の次の候補を試し、尽きたらここに入る） | その Task で止まる |

4. **確認とレビュー:** 取り込んだ後、feature worktree で関連テストと静的チェックを実行し、SDD の Task のレビューを行う。指摘の修正も同じ担当に新しい依頼として出す（新しい `RUN_DIR`。`revision` は取り込んだ後の HEAD）
5. **依頼ごとの記録と後片付け:** 依頼し直し（`retry`・`rejected`）も指摘の修正も、それぞれ 1 つの依頼として数える。1 つの依頼の `verdict` を処理し終えるたびに、その依頼の `RUN_DIR` について次の順に行う。依頼し直すときも、前の依頼の `RUN_DIR` を片付けてから新しい依頼を出す（Task の最後にまとめると、止まる経路で前の依頼の runner の worktree の登録が残る）
   1. SDD の ledger に、Task 名と何回目の依頼か、`requested_agent`・`actual_agent`・`identity`（runner が観測したモデル）、`elapsed_seconds`、`verdict`（`accept` を実行したらその結果も）を書く。`cleanup` は `RUN_DIR`（`task.json` とログを含む）を消すので、先に書く
   2. `implement_task.py cleanup --run-dir "$RUN_DIR"` を実行する。時点は、`importable` は `accept` の後（取り込めなかった場合も）、`no_changes`・`retry`・`rejected` は ledger に書いた直後、止まるとき（`failed`、上限に達した `retry`・`rejected`）は停止の報告の前。停止を確認した試行の worktree の登録を外し（force しない）、何も残らなければ `RUN_DIR` を消す
   3. 終了コード 1 は、残したもの（`retained`。停止を確認できない試行、`sensitive_paths` のある試行など）があることを示す。それだけでは止まらない。完全パスを ledger に書き、最終報告（止まるときは停止の報告）に含める。force・`rm -rf` で消さない

   `run` が終了コード 2（`status: error`）で終わったときは `task.json` が無く、`cleanup` を使えない。`RUN_DIR` が存在すれば、その完全パスを停止の報告に書く。`reason` が `checkout_audit` なら、`checkout_audit` に並んだ登録（消えた worktree など）を報告して止まる。他の作業の領域でありうるので、自分で prune・削除しない。`IMPLEMENT_SESSION` は、すべての依頼の `cleanup` の後に空になったときだけ `rmdir` で消す。run 全体の `SESSION` はこの後片付けの対象にしない。中身が残っていれば消さずに完全パスを報告する（`rm -rf` で消すと runner の worktree の登録だけが残り、runner を使う入口が起動の前の監査で止まる）

失敗を理由に、このセッションが `self` で実装を引き取らない（`tools/agent_runner/interfaces.rst` の「失敗を理由に別モデルへ暗黙に切り替えない」と同じ）。止まった Task の後の Task・最後の全体レビュー・PR には進まない。担当を変えるかは利用者が決める。すべての Task を取り込めたときの最後の全体レビューは 4 章 8 に従い、PR は `self` のときと同じ。PR 本文には、5 章の項目に加えて、割り当て（雛形・個人設定・`--implement` のどれで決まったか）、runner が観測した agent・モデル、Task ごとの依頼の回数と所要時間を書く。

## 5. 検証・PR・完了

この章の「`--merge` のとき」は、`--merge` が適用された run（`merge-disabled.txt` が無い run。2 章 5 の規則で統合用 branch では無効化される）を指す。無効化された run は `--merge` が無い run として扱う。

- **`verification-before-completion` と `finishing-a-development-branch` 必須。** 終了方法は PR の作成を選び、改めて選択肢を尋ねない。検証は 2 章の 5 で確認した repo 側の入口で行う。長時間の検証・子・CI は `monitoring-long-tasks` 必須で、終了を待ち、終了コードと実ログを確かめる。
- `--merge` のときは、最後の commit の後に検証し、検証した HEAD、そのときの `git status --porcelain` が空だったこと、各コマンドの argv と終了コード、ログの完全パスを `PARENT_ROOT/tmp/agents/` のセッションディレクトリに記録する。実 PR 作成後の照合でも同じ base であることを確認し、検証したツリーが含むコード base の完全 SHA（`CODE_BASE_SHA`）を `base` に記録する。PR の `baseRefOid` や文書 main の SHA で代えない。同じ場所に、`finalize.py` の `--checks-file` の形のファイルも作る（形は review-fix-planning の `references/execution.md` の 3 章のとおり）。ループで再利用する条件になる（下の「`--merge` のとき: PR の作成後のループ」の 5）
- 統合確認では [要件・原因・検証の対応](../review-fix-planning/references/convergence.md) の「3. 検証と閉じ方」を読む。Spec→Plan→Task→実行証拠を条件単位で照合し、判定の両側・意味のある操作順・検証の独立した根拠・最後の修正で影響した経路を確認する。要件の欠落や未確認をテスト件数や別版のレビューで埋めず、必要な証拠が揃ってから公開する。
- 差分は捕捉した base から確認する。後続のレビューにも repository / ref / SHA と差分の根拠を渡し、`origin/main` 固定に戻さない。

  <!-- base-workflow:diff -->
  ```bash
  set -euo pipefail
  git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
  while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
  recheck_bases || exit 2
  git -C "$CODE_ROOT" diff "$CODE_BASE_SHA...HEAD" -- > "$SESSION/code.diff" || exit 2
  if [ "$DOCS_SEPARATE" != false ]; then
    git -C "$DOC_ROOT" diff "$DOC_BASE_SHA...HEAD" -- > "$SESSION/docs.diff" || exit 2
  fi
  ```

- worktree で明示したパスだけを stage・commit する。push は `finishing-a-development-branch` の `git push -u` でなく次の順。どれかを push する前に全 worktree を検査する。スクリプトは `PARENT_ROOT` のものを使う（外部 checkout には無く、feature のものは書き換えられる）。その版が `--expected-base-sha` 未対応なら停止し、親の更新が必要と報告する。別版で回避しない。検査後に commit を足したら検査からやり直す。CI 修正等の再 push も同じ形。

  <!-- base-workflow:publish -->
  ```bash
  set -euo pipefail
  git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
  while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
  SCAN="$PARENT_ROOT/scripts/scan-before-push.sh"
  recheck_bases || exit 2
  CODE_SHA="$(bash "$SCAN" -C "$CODE_ROOT" --base "origin/$CODE_BASE_BRANCH" --expected-base-sha "$CODE_BASE_SHA")" || exit 2
  [ -n "$CODE_SHA" ] || exit 2
  printf '%s\n' "$CODE_SHA" > "$SESSION/code-sha.txt" || exit 2
  if [ "$DOCS_SEPARATE" != false ]; then
    DOC_SHA="$(bash "$SCAN" -C "$DOC_ROOT" --base origin/main --expected-base-sha "$DOC_BASE_SHA")" || exit 2
    [ -n "$DOC_SHA" ] || exit 2
    printf '%s\n' "$DOC_SHA" > "$SESSION/docs-sha.txt" || exit 2
    recheck_bases || exit 2
    git -C "$DOC_ROOT" push origin "${DOC_SHA:?}:refs/heads/${DOC_BRANCH:?}" || exit 2
  fi
  recheck_bases || exit 2
  git -C "$CODE_ROOT" push origin "${CODE_SHA:?}:refs/heads/${CODE_BRANCH:?}" || exit 2
  ```

- Issue の状態・競合も再確認してから PR を作る。`PR_TITLE`、コード/文書の本文ファイル `CODE_PR_BODY` / `DOC_PR_BODY` を用意する。SHA push では upstream が無いので `--head` を省かない。既存 PR があれば重複作成しない。`--merge` でも draft にしない。作成直後に URL を保存し、実 PR の base 名と head SHA を照合してから次へ進む。

  <!-- base-workflow:pr -->
  ```bash
  set -euo pipefail
  git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
  while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
  DOCS_SEPARATE="$(jq -r 'if (.document_repository | type) == "string" and (.repository | type) == "string" then .document_repository != .repository else error("target.json lacks document_repository") end' "$SESSION/target.json")" || exit 2
  CODE_SHA="$(cat "$SESSION/code-sha.txt")" || exit 2
  [ -n "$CODE_SHA" ] || exit 2
  if [ "$DOCS_SEPARATE" != false ]; then
    DOC_SHA="$(cat "$SESSION/docs-sha.txt")" || exit 2
    [ -n "$DOC_SHA" ] || exit 2
  fi
  recheck_bases || exit 2
  CODE_PR_URL="$(gh pr create --repo "$TARGET_REPO" --base "$CODE_BASE_BRANCH" --head "$CODE_BRANCH" \
    --title "$PR_TITLE" --body-file "$CODE_PR_BODY")" || exit 2
  printf '%s\n' "$CODE_PR_URL" > "$SESSION/code-pr-url.txt" || exit 2
  gh pr view "$CODE_PR_URL" --repo "$TARGET_REPO" --json url,baseRefName,headRefOid > "$SESSION/code-pr.json" || exit 2
  jq -e --arg base "$CODE_BASE_BRANCH" --arg head "$CODE_SHA" --arg url "$CODE_PR_URL" \
    '.baseRefName == $base and .headRefOid == $head and .url == $url' "$SESSION/code-pr.json" || exit 2
  recheck_bases || exit 2
  if [ "$DOCS_SEPARATE" != false ]; then
    DOC_PR_URL="$(gh pr create --repo usaturn/create-reso-world --base main --head "$DOC_BRANCH" \
      --title "$PR_TITLE" --body-file "$DOC_PR_BODY")" || exit 2
    printf '%s\n' "$DOC_PR_URL" > "$SESSION/docs-pr-url.txt" || exit 2
    gh pr view "$DOC_PR_URL" --repo usaturn/create-reso-world --json url,baseRefName,headRefOid > "$SESSION/docs-pr.json" || exit 2
    jq -e --arg head "$DOC_SHA" --arg url "$DOC_PR_URL" \
      '.baseRefName == "main" and .headRefOid == $head and .url == $url' "$SESSION/docs-pr.json" || exit 2
    recheck_bases || exit 2
  fi
  ```

  不一致・base 移動ならループ・完了報告へ進まない。公開済みの branch・PR は自動 close・削除・base 変更で取り消さず、URL・実 base と捕捉値・残した資源を停止報告に書く。
- PR 本文の Issue の指定は次のとおり。`Closes` による Issue の自動 close は、PR が対象 repository の default branch にマージされたときだけ働き、マージの後の確認や調整役の close を待たない。非 default branch 向けの PR は `Closes` を書いてもそのマージでは Issue が自動 close されないため、完了報告では実際に観測した Issue の state を書く。以下の `Refs` / `Closes` の選択基準は変えない。
  - Issue が `TARGET_REPO` と別のリポジトリにある: `Refs <Issue の URL>`（マージで別のリポジトリの Issue を閉じない）
  - Issue が `TARGET_REPO` にあり、マージの後でなければ確かめられない項目（rebuild、実機、`resoloop` の導入など）が受け入れ条件・検証に残る: `Refs #N`
  - Issue が `TARGET_REPO` にあるボードの子（2 章の 7）: `Refs #N`。close と親の更新は、マージの後に調整役が行う
  - 上のどれにも当たらない: `Closes #N`
- マージの後でなければ確かめられない項目が残るときは、Issue の指定に関係なく、その項目を PR 本文と最終報告に書き、run の最後（`--merge` のときはループの終了の後）に、PR の URL とその項目を Issue へコメントする
- PR 本文には、変更概要、**Spec の決定と理由、実行方式と理由**、実行した検証と結果、作業時間と主要 Task 別の内訳も書く。Spec・設計レビューを行った run は、helper・`self` のどちらで行ったか、担当（明示値・保たれた `fallback`・`actual_agent`・`identity`）、回数、採否の要点、レビュー記録の `SESSION` のパス（commit しない）も書く。未実行の確認を成功と書かない。
- `DOCS_SEPARATE` が `true` なら、上の文書用 PR は Spec・Plan だけを含める。本文は `Refs <Issue の URL>` とコードの PR の URL。コードの PR の本文にも文書の PR の URL を足す。
- CI は 2 章の 5 で確認した対象ごとの規則に従う。CI 必須のリポジトリは PR の checks が green になってから完了とする。失敗したら直すか、直せなければ止まる。`--merge` のときは、PR の作成後に CI を待たずにループへ進む（マージの前に `finalize.py` が CI の成功を確かめ、実行中なら `wait_for: ci` で待つ。PR の変更による失敗は、review-fix-planning が致命的な指摘として直す）。
- `--merge` のときのループの `finalize.py` によるマージを除き、マージ・タグ・リリース・デプロイ・プロビジョニングは行わない。admin マージ・auto-merge・force push・branch の削除は、どの場合もしない。
- ボードの子の成果の公開・予約の解放は `planning-parallel-issues` に従う。自分の所有物だけを扱う。`--merge` のときは、PR の作成の直後には解放しない。ループの `finish` の後（ループのエラーで `finish` まで進めないときは、止まった時点）に、結果と再開の方法を子 Issue に書いてから解放する。
- 完了したら Herdr のタスクを completed にし、PR の URL、検証結果、worktree・branch、実在する Spec・Plan・残したログの絶対パス、所要時間、ペイン名の更新結果（3 章の「ペイン名の終了状態」のとおり `:END`・`:Glitch`・維持のどれか。開始時・終了時の rename の失敗やスキップがあったときは、その理由と pane 名が未更新であること）を報告する。`--merge` が無ければ、レビューは `/pr-review <PR の URL>` で行えることを 1 行で伝える。尋ねて止まらない。`--merge` のときは、この 1 行の代わりに、下の節の 6 の報告を加える。

### `--merge` のとき: PR の作成後のループ

`merge-disabled.txt` がある run（統合用 branch の子）はループを始めない。この節を使わず `--merge` が無い run と同じく PR の作成で終える。ここで改めて判断しない。この章の「`--merge` のとき」は、`--merge` が適用された run（`merge-disabled.txt` が無い run）を指す。

PR を作った後（`DOCS_SEPARATE` が `true` なら、文書の PR も作った後）、このセッションが司令塔としてループを回す。ループが終わるまで、review-fix-planning の手順の外で feature worktree を変えない（未 commit の変更や PR に無い commit を残さない。review-fix-planning は、clean で HEAD が PR の head の worktree を修正に使い、そうでなければ結論 3 で止まる）。Spec・Plan への記録は PR を作る前に済ませ、ループの間の記録はセッションディレクトリと PR・Issue のコメントに置く。

1. `HERDR_ENV=1` なら、Herdr のタスクを `herdr-agent-task set "PR #<PR の番号> レビュー・マージ"` に変える。ペインの名前は `start` が 3 章・起動節の規則どおりのラベル（Issue 起点は `<repo>:#<N>`、単独起動は `PR#<番号>`）に改名するので、自分で変えない
2. `PARENT_ROOT` の `.agents/skills/pr-review-fix-loop/SKILL.md` をファイルとして読む（`disable-model-invocation: true` なので、Skill ツールでは起動できない）
3. `PARENT_ROOT` の `loop.py` で `start` を実行する。feature worktree の `loop.py` は使わない（`loop.py` は置き場所からスキルと helper を決めるので、PR で変えているものでレビューさせない）。`<PR の URL>` はコードの PR。文書の PR はループに乗せず、マージもしない（URL と状態を報告する）。issue-to-pr からの起動では `--issue-number <Issue の番号>` と `--issue-repository <Issue の repo>` を一緒に渡す（値は `issue.json` の `number`・`repo`）。これで `start` のペイン名は 3 章の開始時と同じ `<repo>:#<N>` になり、クロス repo でも PR の repo から再導出しない。この 2 つは表示用の引数で、`loop_args` には入れず、`check-options` にも渡さない（start 専用）。マージ権限・対象 Issue の推測には使わない

   ```bash
   uv run --project "$PARENT_ROOT" --locked python \
     "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" start "<PR の URL>" \
     --controller-model "<あなたの正確なモデル ID>" --controller-runtime "<ランタイム>" \
     --issue-number <Issue の番号> --issue-repository <Issue の repo（owner/repo）> \
     <loop_args の各要素>
   ```

4. 以降は pr-review-fix-loop の SKILL.md 全体（守ること・起動の注意・サイクル・終わり方・止まったとき・監視・最終報告）に従う。起動のコマンドは上の 3 のとおり
5. **検証の記録の再利用:** 1 サイクル目で修正不要となり、サイクルの HEAD が上で記録した HEAD と同じなら、その記録を review-fix-planning の結論 2 の手順 1 の検証の記録（`finalize.py` の `--checks-file`）に使ってよい。条件は、同じ HEAD、検証のときに未 commit の変更が無い、すべての終了コードが 0、ログが残っていること。どれかを確かめられなければ、計画の中で検証し直す。記録の形と base の扱い（結論 2 の手順 2）は review-fix-planning のとおりにし、実 PR の `baseRefName` を使い、base が進んでいたときの merge の検証は省かない。捕捉済み SHA を無検証で新値に書き換えず、既存の HEAD・base・merge 第1親・CI の guard を保つ
6. **終了:** pr-review-fix-loop の SKILL.md の「最終報告」の項目と、5 章の完了の報告の項目を書き、ループの結果で次の区分を加える。ループの段階の所要時間も書く。ペイン名は 3 章の「ペイン名の終了状態」に従って更新する（マージ成功の確認で `:END`、予期しない障害の中断は停止報告の前に `:Glitch`、それ以外は維持）

   | ループの結果 | 報告 | マージ |
   | --- | --- | --- |
   | `no_fix_needed` | 完了。関連 Issue は、finalize の結果に含まれる、更新後に観測した state を書く | した |
   | `fixes_pushed`（`ended_by: cycle_limit`） | 未完了。修正は push 済みで、サイクルの上限に達した。続けるなら `/pr-review-fix-loop <PR の URL>` | していない |
   | `stopped`（`ended_by: outcome`） | 停止。`stop_reason` を書く。`merged: true` なら、マージ済みであることを分けて書く | 結果のとおり |
   | ループのエラー（`lock_held`、全レビュアーの失敗、資源の停止を確認できない など。`finish --abort` で終えた run（`ended_by: abort`）を含む） | 停止。ループの `stage`・`reason`・`next` と、残した資源の完全パスを書く | PR の状態（`gh pr view <PR の URL> --json state,mergedAt,headRefOid`）を読み直して書く。読めなければ未確認（`finish --abort` の結果の `merged` が `true` なら、マージ済みと書く） |

## 停止時の報告

不正な入力（helper・`check-options`・`implement_task.py check` の終了コード 2）、cwd が git の追跡しないディレクトリの中・Issue がワールドの作業を含む（「ワールドの作業で止まったとき」）、`--merge` で `TARGET_REPO` が手動マージ対象（meshy・登録済み通常ツール。2 章 5 で `--merge` を無効化した run を除く）、Task の依頼の `failed`、再試行の上限に達した `retry`・`rejected`、対象・remote の確認の失敗、競合、マージ済みの PR で PR にする作業が残っていない Issue、未完了の依存、Issue の明示の承認要求、要求 base の未指定・矛盾・曖昧さ、base の不存在・不一致・捕捉後の移動、実 PR の base/head の不一致、禁止・取り消せない操作、想定外の外部送信、必要なツール・API の失敗、解消できない検証の失敗、push の前の検査の検出（`AGENTS.md` の条件で直せるものを除く）・失敗（gitleaks が無い・版が違うを含む）、ループの停止・エラーでは止まる。Spec・設計レビューでも、helper の終了コード 2（型・版・保存先・順序の拒否）、`state: failed`・`status: incomplete`・`review_id` / `spec_sha256` の不一致、採否の欠落・重複・未反映、設計レビューの `wrong_approach`・`blocking`・`questions_for_user`・`needs_judgment`、Spec レビューの後の設計レビューや 2 回目を超える再レビュー、停止未確認の `retained` では止まる。停止条件は「途中で止めずに」の例外であり、省略・成功扱い・別のリポジトリへの切り替えで回避しない。

検査で止まったら、どの worktree も push せず、PR を作らない。`AGENTS.md` の「push の前の秘密情報の検査」の条件を満たす検出なら、その commit を直し、検証（`--merge` のときは検証の記録も）と、公開するすべての worktree の検査をやり直して続ける。条件を満たさない検出では止まり、回避しない。gitleaks は自分で導入せず、`bash "$PARENT_ROOT/.devcontainer/install_gitleaks.bash"` での導入を次の操作として報告する。検査が全部通った後の push や PR の作成が失敗して一部だけ公開されたら、公開済みの branch・PR を報告し、取り消さない。

**理由 / 現在の状態 / 実施済みの検証と終了コード / 存在する worktree・branch・Spec・Plan・ログ / 次の操作** を報告する。Spec・設計レビューで止まったときは、`review_dir`・`review_id`・reviewed の SHA・`next`・`retained` の完全パスも書く。成功した `decide` があれば、その出力の reflected の SHA も書く。成功した `decide` が無いレビューでは reflected の SHA を「未作成」と書き、値を推測しない。reviewed の SHA は review の `spec_sha256`（成功した `decide` があれば出力の `reviewed_spec_sha256`）を使い、reflected の値で置き換えない。Task を runner の担当に依頼した run では、`cleanup` が残したもの（`retained`）と、`cleanup` を使えなかった `RUN_DIR` の完全パスも書く。ループで止まったときは、ループの `stage`・`reason`・`next`・run のディレクトリ・残した資源の完全パスも書く。作っていないパスは「未作成」と書く。通常の工程の区切り、推奨案の選択、実装方式の選択は停止の理由にしない。

## ランタイムごとの違い

- **Claude Code:** `/issue-to-pr <Issue> [--base BRANCH] [--implement AGENT] [--spec-review AGENT] [--design-review AGENT] [--merge [ループ用のオプション]]`。スラッシュコマンドの引数（`ARGUMENTS`）から、2 章の規則で `INPUT` を切り出す。モデルが自分の判断で Skill ツールからこのスキルを呼ぶときは、利用者のメッセージから同じ規則で `INPUT` を切り出して args に渡す。利用者が書いた `--base`・`--implement`・`--spec-review`・`--design-review`・`--merge`・ループ用のオプションは書かれたとおりに含め、書かれていないものは足さない（自然文の「マージまで」は `--merge` ではない）。pr-review-fix-loop は Skill ツールで起動せず、5 章のとおりファイルとして読む。
- **Pi:** `/skill:issue-to-pr` の引数から、2 章の規則で `INPUT` を切り出す。`/sp-brainstorm` から入るときは、Issue の URL を最初に書き、`--base`・`--implement`・`--spec-review`・`--design-review`・`--merge`・ループ用のオプションはその直後に続ける（`/sp-brainstorm <Issue URL> [--base BRANCH] [--implement AGENT] [--spec-review AGENT] [--design-review AGENT] [--merge [ループ用のオプション]] issue-to-pr を使い、…`）。1 章の入口を案内するときも、利用者が書いた `--base`・`--implement`・`--spec-review`・`--design-review`・`--merge`・ループ用のオプションだけを含める。
- **`--controller-model`・`--controller-runtime`（5 章のループ）:** `--controller-runtime` は Claude Code なら `claude-code`、Pi なら `pi`。`--controller-model` は、現在提示されている正確なモデル ID（Pi は pi-model-name のスキルで `PI_PROVIDER` と `PI_MODEL` を確かめる。pr-review-fix-loop の「ランタイムごとの違い」）。
