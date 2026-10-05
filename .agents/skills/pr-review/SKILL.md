---
name: pr-review
description: GitHub の指定した PR をレビューする。PRのメタデータ、説明、差分（diff）を gh CLI で取得し、使い捨て git worktree 上で検証した指摘を Severity・位置・根拠付きで reviews/#PR-branch/model.md に作成または更新する。PR番号・URLを指定したコードレビュー依頼で使用する
allowed-tools: Read, Grep, Glob, Bash(gh *), Bash(git *), Bash(date *), Bash(uv run --no-project python *pr_review_workspace.py *), Bash(uv run --no-project python *superpowers_context.py *), Edit(/tmp/pr-review-*/review-backup/**), Write(/tmp/pr-review-*/review-backup/**), Agent
argument-hint: "<PR番号またはURL>"
---

# GitHub PR レビュー

GitHub 上の指定された Pull Request（PR）に対して、Codex の `/review` に近い高品質なコードレビューを行います。git worktree を使用し、ユーザの作業ブランチ・working tree に触れずにレビューします。

対象 PR（スキル呼び出しの引数）: $ARGUMENTS

## ランタイム別の注意

このスキルの実体は `.agents/skills/pr-review/` の 1 つだけで、Claude Code は `.claude/skills/pr-review` の symlink 経由で同じファイルを読む。ヘルパーも `.agents/skills/pr-review/scripts/pr_review_workspace.py` の 1 本だけを使う。

### 対象 PR の受け取り

- 冒頭の `対象 PR` 行は、呼び出し引数を本文へ展開するランタイム（Claude Code、Devin）が埋める補間欄である。値が空欄、またはドル記号で始まるプレースホルダ表記のまま残っている場合は「未指定」とみなす
- 未指定のときは、ユーザのメッセージで PR 番号・URL が指定されていればそれを使う。どちらも無ければ手順 1 のとおり現在のブランチの PR を使う
- 引数を展開するランタイムは `＄ARGUMENTS` と `＄0`〜`＄9`（ドル記号と数字 1 文字）を呼び出し引数で置換する（この節では置換されないよう全角で書いている）。埋め込みのシェルコードに位置パラメータを書かず、入力は stdin か名前付き変数で受ける

### Claude Code

- frontmatter の `allowed-tools` は Edit と Write を `/tmp/pr-review-*/review-backup/**` に限っている。`create` には必ず `--temp-root /tmp` を渡し、ヘルパーの一時ディレクトリをこの範囲に置く
- `MODEL_NAME` は Claude Code ランタイムが提示する正確なモデル識別子を使う
- helper を呼ぶ Bash には `timeout: 600000` を指定する（規約の「helper の呼び出し」）

### Codex

- `create` に `--model-name` を渡さない。ヘルパーが `CODEX_THREAD_ID` と Codex の session metadata からモデル名を確定する

### Devin

- `MODEL_NAME` はシステムプロンプトの `You are powered by <MODEL>` が提示する識別子を使う（例: `SWE-2 High`）
- 過去のセッションの transcript（`~/.local/share/devin/cli/transcripts/` の `agent.model_name` など）は実行中のランタイムの提示ではないため、`MODEL_NAME` の根拠にしない

### pi

- `MODEL_NAME` は pi-model-name スキルの手順で決める。セッション履歴（`~/.pi/agent/sessions` 配下）の `model_change` は根拠にしない
- bash ツールの `timeout` は秒単位である。helper を呼ぶときは指定しないか 600 以上にする（規約の「helper の呼び出し」）

## 規約

- [時間予算と委譲規約](references/time-budget.md)を最初の PR API 呼び出しより前に全文を読む。開始時刻・期限・委譲可否・打ち切りはその規約に従う
- レビュー出力は助言として扱われる
- プロダクトコード・テストを編集しない
- レビュー中に重い一括検証を再実行しない。対象は `bash .devcontainer/run-tests.bash`、リポジトリ全体やワールドのプロジェクト全体の `uv run pytest`、`scripts/resoloop-fork.sh test`（fork の `dotnet test` 全体）などである。実装時と CI で確認済みであり、レビューで再実行すると時間がかかり冗長だからである。関連する pytest（ファイルやテスト名で絞ったもの）、個別のテストスクリプト、REPL、最小再現スクリプトなど、指摘の検証に必要な範囲の実行はしてよい。helper の `verify`（destination フィンガープリント確認）はテストの実行ではない。この規定は、`AGENTS.md` や他のスキルが求める完了前の検証より優先する（レビューでは一括検証を再実行しない）
- helper の呼び出し: `pr_review_workspace.py` の各サブコマンドは、fetch・`gh` など所要時間の読めない別の処理と同じツール呼び出しにまとめない（結果の JSON を読む `jq` は同じ呼び出しでよい）。ツール呼び出しにタイムアウトを指定できるランタイムでは、指定しないか 600 秒以上を指定する（上限が 600 秒未満のランタイムではその上限）。`create` は同時のレビューやストレージの書き込み待ちで数分かかることがあり、短いタイムアウトで打ち切ると worktree が残ってレビューを続けられなくなる。時間予算はフェーズの境界で確かめ、helper を打ち切って守らない
- レビュー中は `git clean`、`git checkout -f`、`git reset --hard` を実行しない。既存 worktree を再利用・初期化しない
- 自セッションの worktree の削除は helper の `cleanup` だけが行う。`create` が結果を返さずに中断した試行の残存物は、helper の `abandon` だけが片付ける（手順 2）。`git worktree remove`、`rm -rf` などの削除コマンドを自分で組み立てない。`cleanup`・`abandon` が拒否した場合も手で代行しない
- `cleanup` は保存成功（`$DESTINATION` の内容が `$DRAFT` と一致）を検証できたときだけ削除する。検証できない場合は何も削除せず停止し、`$WT` と `$DRAFT` の完全パスを報告してユーザの判断に委ねる
- レビュー中に生成した検証ログ・スクリーンショット・一時スクリプト等の証跡を `$WT` に残さない。あとで見返す必要がある内容はレビュー本文の「根拠」に転記し、`$DESTINATION` だけで完結させる
- 最終応答で `$WT` 配下のパスを参照しない（`cleanup` 成功後は `$WT` が存在しないため）。`cleanup` の失敗または停止確認不能による省略時は、残った `$WT` とセッションの完全パスを報告する
- 独立したレビューを行うため、`reviews/#<PR番号>-<変換後ブランチ名>/` にある他モデルのレビュー本文は、候補の洗い出し・重点観点の収集・重複確認・自分の指摘の検証を含むいかなる目的でも読まない。レビュー完了後も読まない。メインリポジトリ側と `$WT` 側（PR に同梱された `reviews/`）のどちらも対象とする
- `MAIN_ROOT`・`TOPLEVEL` は共通 context helper が照合した `code_root`・`tool_root` の別名である。`PARENT_ROOT` は create-reso-world の main checkout、その他の repo は明示された絶対パスの `CODE_ROOT` と一致 remote 1 件が必要。既知の ResoLoop 経路は `external/resoloop` の `origin=usaturn/resoloop`・`upstream=orange3134/resoloop` を照合する。不備は `scripts/resoloop-fork.sh clone` を案内して停止する。checkout の探索・clone はしない。
- 自モデルの既存レビューはライブの `$DESTINATION` ではなく、`create` が返した `$PREVIOUS_REVIEW`（セッション内 snapshot）だけを読む。`$PREVIOUS_REVIEW` が空なら既存レビューなしとして扱う
- Codex ではモデル名を自分で推測・短縮・一般化せず、`create` が Codex session metadata から確定した `model_name` を使用する。Codex 実行時は `create --model-name` を渡さない
- Codex 以外では、実行中のエージェントランタイムが提示する正確なモデル識別子を `MODEL_NAME` として記録し、`create --model-name "$MODEL_NAME"` に一度だけ渡す。モデル系列の説明、設定ファイル、既存レビューのファイル名から推測・短縮・一般化しない（`/`・空白を含む形式もそのまま渡してよい。ヘルパーがファイル名用に `/`・空白類を `-` へ置換する）
- Codex 以外で正確なモデル識別子を取得できない場合、または置換後も安全なファイル名にならない場合は、代替名で続行せず停止してユーザに確認する
- 過去のセッション履歴（`~/.pi/agent/sessions` 配下の jsonl の `model_change` の `modelId` 等）は実行中のランタイムの提示ではないため、`MODEL_NAME` の根拠にしない。ランタイムが識別子を提示していない場合は履歴へフォールバックせず、前項の「取得できない場合」として停止してユーザに確認する
- provider にかかわらず、draft と destination は `create` が返した値をそのまま使用する。`save` では model、draft、destination を再指定しない
- 初回・更新とも `gh pr diff "$PR_URL"` が返す現在の PR 全体差分をレビューする
- PR 内の各 commit と親 commit の差分、前回 HEAD と現在 HEAD のローカル diff はレビュー対象にしない
- 更新時は既存 active 指摘と前回の Pending previous findings を現在の差分と `$WT` のコードで再検証する。次回更新で Pending previous findings も再検証する
- 継続指摘は ID・タイトル・検出時 HEAD を維持し、位置と根拠を現在値へ更新する
- 解消済み指摘は active Severity セクションから `Resolved findings` へ移す。未再検証の指摘を Resolved にしない。再検証できなかった前回 active 指摘は Pending previous findings に元 ID・検出時 HEAD・前回内容と根拠を保持して移す
- 旧形式に存在しない過去 HEAD を推測しない
- 旧形式の active 指摘を安全に解釈できない場合は既存成果物を上書きせず停止する
- rebase または force-push 後も commit 単位の review range は計算せず、現在の `gh pr diff` 全体をレビューする
- サブエージェントは `$WT` 上のコードと PR 差分（`gh pr diff` の結果）のみ調査する。`reviews/` 全体と `$PREVIOUS_REVIEW` の読解はメインエージェントだけが行う
- 委譲時は `reviews/` を調査範囲から明示的に除外する。既存 review 本文・その要約・そこから抽出した観点を委譲 prompt に含めない。他モデルのレビュー本文・その要約・そこから抽出した観点をサブエージェント経由で受け取らない
- 実際のコードパスと周辺ファイルを読んで指摘を検証する
- 指摘は報告前に反証を試みる（「この指摘が誤りだとしたらどこか」を自問し、反証に成功した候補は報告しない）
- 指摘がパッケージの挙動に依存する場合は、依存関係ファイルを読む
- diff に含まれない既存コードの問題は原則対象外。ただし diff が既存の潜在バグを顕在化させる場合は指摘対象
- 非現実的なエッジケース、推測ベースのリスク、大規模な書き直し、過度に複雑な修正提案を避ける
- 適切な責務境界での小さな修正を優先する
- 重大で実行可能な問題に集中する
- 指摘が不確かな場合は【確認推奨】と明記する
- 実行可能な指摘がない場合は、その旨を明確に伝える
- レビューは日本語で返す
- レビュー結果は常に `create` が返した `$DESTINATION` に作成する。`$DESTINATION` はヘルパーが `reviews/#<PR番号>-<変換後ブランチ名>/<model>.md` へ配置する。ブランチ名とモデル識別子に含まれる `/`・空白類およびディレクトリ名に使えない記号はヘルパーが使える記号へ変換する（例: PR 160・ブランチ `feature/issue-148-fail-fast` は `#160-feature-issue-148-fail-fast` 配下、モデル `opencode/deepseek-v4-flash-free` は `opencode-deepseek-v4-flash-free.md`、モデル `Cursor Grok 4.6` は `Cursor-Grok-4.6.md`）。`create` が返す `model_name` もこの変換後の値であり、エージェントが手で組み立てない
- 保存先の `reviews/` は `MAIN_ROOT` の直下にある。resoloop の PR では `external/resoloop/reviews/` になり、fork の `.gitignore` はこれを無視しない。fork で commit するときは `git add` に明示したパスだけを渡し、`reviews/` を含めない。その他のリポジトリでは `$CODE_ROOT/reviews/` になり、その checkout の `.gitignore` が無視するとは限らないため、同じく `git add` に明示したパスだけを渡す。レビュー成果物は Spec・Plan ではないため、create-reso-world の `docs/superpowers/` へ集約しない
- 同じ PR を同じモデルで再レビューする場合は、同一ファイルの内容全体を上書きし、別名ファイルを作らない。別モデルの結果は同じ PR ディレクトリ内の別ファイルへ保存する
- PR 上で既に指摘済みの問題は重複報告しない（触れる場合は「既出」と明記する）
- 件数表は active findings のみから計算する。重大度判定は active findings、確認不足判定は coverage と pending も参照する。Resolved findings は件数・重大度判定に含めない
- 新規 ID は active / pending / resolved 全体で ID の衝突を避ける。pending と resolved の ID を再利用しない
- 補助委譲の省略・中断だけで本体が必要範囲を確認済みなら判定を悪化させない
- 確認不足・時間切れを理由に既存の保存拒否条件（HEAD 不一致・API 失敗・destination 変更・既存レビューの解釈不能）を飛ばさない。拒否時は上書きせず、エラーと保存前 draft の場所を報告する
- 停止確認不能なら cleanup を省略する。停止確認不能のときだけ cleanup を省略する限定条件であり、helper が失敗した場合の既存停止規則（削除を手で代行せず停止してパスを報告する）は保持する
- 最終応答には save/cleanup の結果と開始からの経過・全体実時間を載せ、保存済みレビューを後から直接書き換えない
- 既存 Review history と Resolved findings は削除・並べ替えず、今回分だけ追記する。同じ HEAD の再レビューでも Review history 行を追加する

## 手順

0. **時間予算の開始**:
   - [時間予算と委譲規約](references/time-budget.md)に従い、最初の PR API 呼び出しより前に開始時刻（UTC と epoch 秒）と予算（全体・調査期限・予約枠）を確定し、値をセッションの進捗記録に保持する。ユーザー指定の予算がある場合は開始時に値を確定する。
1. **PR情報の取得**:
   - 対象 PR は、冒頭の `対象 PR` 行が補間済みならその値、未指定ならユーザのメッセージで指定された PR 番号・URL から読み取り、前後空白を除去して `PR_ARG` に入れる。番号・`#` 始まり・GitHub URL はいずれも `gh pr view` がそのまま解釈できるため番号へ正規化しない。URL の owner/repository を失うと別リポジトリの同名番号 PR を取得する。行が空欄または `$` で始まるプレースホルダ表記のまま残っている場合は未指定とする。
   - `PR_ARG` が確定している場合、`PR_JSON=$(gh pr view "$PR_ARG" --json number,title,body,baseRefName,headRefName,headRefOid,url,additions,deletions,changedFiles)` を実行し、PRのタイトル、説明、ベースブランチ、ヘッドブランチなどのメタ情報を取得してコンテキストを把握する。PR 番号・ヘッドブランチ・正規 URL は機械的に `PR_NUMBER=$(printf '%s' "$PR_JSON" | jq -r .number)`・`HEAD_BRANCH=$(printf '%s' "$PR_JSON" | jq -r .headRefName)`・`PR_URL=$(printf '%s' "$PR_JSON" | jq -r .url)` で確定する。以降 `gh pr view`・`gh pr diff` には `"$PR_URL"` を使い、カレントリポジトリへの暗黙解決に依存しない。
   - `PR_ARG` が確定しない場合（`対象 PR` 行が未指定で、ユーザのメッセージにも PR 番号・URL が無い場合）、`PR_JSON=$(gh pr view --json number,title,body,baseRefName,headRefName,headRefOid,url,additions,deletions,changedFiles)` を実行して現在のブランチに関連付けられたPRの情報を取得し、同じく `PR_NUMBER`・`HEAD_BRANCH`・`PR_URL` を確定する。関連付けられたPRがない場合はユーザにPR番号の指定を促す。
   - `gh pr view "$PR_URL" --comments` で既存のレビューコメント・議論を取得し、既出の指摘を把握する。
   - gh が未認証・API エラーの場合はエラー内容をそのまま報告し、`gh auth login` を案内する。
2. **worktree への展開**:
   - ユーザの作業ブランチ・working tree に触れないため、`gh pr checkout` は使わない。
   - ルート `AGENTS.md` の「リポジトリ境界」に従い、次の共通 helper で fetch・worktree 作成より前に root と remote を照合する。`PARENT_ROOT` は明示された create-reso-world の main checkout を使う。省略できるのはその main checkout 内の cwd だけで、linked・外部 cwd では明示が必要。その他の repo の `CODE_ROOT` はユーザの依頼または確認済みの引き継ぎの絶対パスを使い、推測で埋めない。明示されていなければ空のままにする。`CODE_ROOT` は全経路で main checkout を要求し、既知経路と矛盾する指定も拒否する。helper の配置元を `CODE_ROOT` から導出しない。

     ```bash
     PR_URL=$(printf '%s' "$PR_JSON" | jq -r .url)
     CODE_ROOT="${CODE_ROOT:-}"
     CONTEXT_PARENT="${PARENT_ROOT:-}"
     if [[ -z "$CONTEXT_PARENT" ]]; then
       CONTEXT_PARENT=$(git rev-parse --show-toplevel 2>/dev/null) || {
         printf 'Set PARENT_ROOT to the create-reso-world main checkout; cwd is not a checkout\n' >&2
         exit 66
       }
     fi
     CONTEXT_HELPER="$CONTEXT_PARENT/scripts/superpowers_context.py"
     if [[ ! -f "$CONTEXT_HELPER" ]]; then
       printf 'Missing context helper %s; set PARENT_ROOT to the create-reso-world main checkout containing scripts/superpowers_context.py\n' "$CONTEXT_HELPER" >&2
       exit 66
     fi
     CONTEXT_JSON=$(uv run --no-project python "$CONTEXT_HELPER" --operation review-workspace \
       --parent-root "$CONTEXT_PARENT" --code-root "$CODE_ROOT" --repo "$PR_URL") || exit 66
     PARENT_ROOT=$(printf '%s' "$CONTEXT_JSON" | jq -r .parent_root)
     TOPLEVEL=$(printf '%s' "$CONTEXT_JSON" | jq -r .tool_root)
     MAIN_ROOT=$(printf '%s' "$CONTEXT_JSON" | jq -r .code_root)
     CODE_ROOT="$MAIN_ROOT"
     PR_REMOTE=$(printf '%s' "$CONTEXT_JSON" | jq -r .base_remote)
     ```

   - `HELPER="$TOPLEVEL/.agents/skills/pr-review/scripts/pr_review_workspace.py"` を記録し、通常ファイルとして存在しなければ配置元 `PARENT_ROOT` と欠けた helper パスを報告して fetch 前に停止する。スキルはこのリポジトリにのみ存在するため、`MAIN_ROOT` が `external/resoloop` を指す場合でも `$TOPLEVEL` から解決する。以降、メインリポジトリに対する Git コマンドには必ず `git -C "$MAIN_ROOT"` を使い、カレントディレクトリへ暗黙に作用させない。
   - PR head は PR 番号ごとの専用 ref `PR_REF=refs/pr-review/<PR_NUMBER>` に固定する。`git -C "$MAIN_ROOT" fetch "$PR_REMOTE" "+pull/<PR_NUMBER>/head:$PR_REF"` の後、`PR_HEAD=$(git -C "$MAIN_ROOT" rev-parse "$PR_REF")` で検証対象 SHA を確定する。共有の擬似参照 `FETCH_HEAD` は使わない。
   - fetch 後に `git -C "$MAIN_ROOT" merge-base HEAD "$PR_REF"` が成功することを確認する。失敗した場合は `MAIN_ROOT` の選定が誤っている（無関係なリポジトリに PR のオブジェクトを取り込んだ状態）ため、保存を行わず停止して報告する。
   - dedicated ref fetch 後、次で GitHub の head と `PR_HEAD` の一致を確認する（HEAD consistency check 1/3）。不一致、空値、`gh` failure の場合は履歴を追記せず保存しない。

     ```bash
     CURRENT_PR_HEAD=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)
     test "$CURRENT_PR_HEAD" = "$PR_HEAD"
     ```

   - `create` は試行 ID ごとに一度だけ実行する。ヘルパーは `/tmp/pr-review-<PR_NUMBER>-<ランダム値>/worktree` に新しい detached worktree を作り（`--temp-root /tmp` で固定する。Claude Code の `allowed-tools` と一致させるため、どのランタイムでも同じにする）、保存先 `$DESTINATION` の create 時フィンガープリント（存在有無、通常ファイル・directory・symlink・その他の種別、通常ファイルの内容 SHA-256 または symlink target text の SHA-256）を `session.json` に保存する。既存パスは再利用しない。destination が通常ファイルの場合はセッション backup へ snapshot し、そのパスを `previous_review` として返す。destination が directory・symlink・特殊 entry の場合は fail-closed で停止する。
   - `create` の前に試行 ID を決め、開始時刻と同じく進捗記録に残す。`create` が何も返さずに終わっても、この ID で自分の試行を指せる。helper は同じ PR に同じ ID の試行があれば worktree を作る前に拒否する。

     ```bash
     ATTEMPT_ID=$(date -u +%Y%m%dT%H%M%S%NZ)
     ```

   - Codex では次を実行する。helper が `CODEX_THREAD_ID` から model を解決する。

     ```bash
     SESSION_JSON=$(uv run --no-project python "$HELPER" create --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --commit "$PR_HEAD" --head-branch "$HEAD_BRANCH" --temp-root /tmp --attempt-id "$ATTEMPT_ID")
     ```

   - Codex 以外では、ランタイムから取得済みの正確な `MODEL_NAME` を使って次を実行する。

     ```bash
     SESSION_JSON=$(uv run --no-project python "$HELPER" create --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --commit "$PR_HEAD" --head-branch "$HEAD_BRANCH" --model-name "$MODEL_NAME" --temp-root /tmp --attempt-id "$ATTEMPT_ID")
     ```

   - `CODEX_THREAD_ID` が存在するのに異なる `--model-name` を渡した場合、または非 Codex で `--model-name` を省略した場合、helper は worktree 作成前に停止する。
   - `create` は進捗を工程ごとに stderr とセッション内の journal へ記録する。`create` の呼び出しが、結果の JSON も helper のエラー（`error:` で始まる行）も返さずに終わった場合（ツールのタイムアウト、ランタイムやシグナルによる中断など。シグナルで中断した `create` は `error:` ではなく `interrupted:` で始まる行を出す）は、`create` をそのまま再実行せず、次の順に扱う。
     1. 次の `inspect` を実行する。`status` が `running` なら `--wait 540` を付けてやり直し、終わるのを待つ。それでも `running` なら、`abandon` も再試行もせず停止して報告する。

        ```bash
        uv run --no-project python "$HELPER" inspect --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp
        ```

     2. `status` が `absent`・`failed` 以外なら、次の `abandon` で試行の残存物を片付ける。`abandon` は、試行が終わっていて、保存前の draft など helper が作った以外のファイルが無く、worktree がこのリポジトリの自セッションのものであるときだけ消す。拒否されたら削除を手で代行せず停止し、`inspect` の出力（工程・状態・残存パス）と拒否の理由を報告する。`failed` は helper のエラーで終わった試行なので、`abandon` も再試行もせず、下の helper のエラーと同じく扱う。

        ```bash
        uv run --no-project python "$HELPER" abandon --repo "$MAIN_ROOT" --pr-number "$PR_NUMBER" --attempt-id "$ATTEMPT_ID" --temp-root /tmp
        ```

     3. `abandon` が成功した、または `inspect` が `absent` を返した場合、調査期限まで 10 分以上残っていれば、新しい `ATTEMPT_ID` を決めて `create` を 1 回だけやり直してよい。残っていなければ停止して報告する。
     4. やり直した `create` も結果を返さなければ、同じく 1・2 を行い、再試行せずに停止して報告する。

     `inspect` の出力から `create` の結果（`worktree`・`state_file` など）を組み立てて続行しない。`create` が helper のエラー（`error:` で始まる行。journal があれば `inspect` の `status` は `failed`）で終わった場合は従来どおり停止して報告し、残存パスの報告に `inspect` を使ってよいが `abandon` はしない。
   - Codex rollout は追記中の末尾にある未完了 JSON レコードだけを無視する。改行済みの壊れた JSON レコード、正常な `turn_context.payload.model` の欠落は fail-closed で拒否する。モデル識別子に含まれる `/`・空白類はヘルパーが `-` に置換してファイル名に使う（例: `Cursor Grok 4.6` → `Cursor-Grok-4.6`）。`..` など置換後も安全なファイル名にならない識別子は fail-closed で拒否する。
   - `SESSION_JSON` の JSON から以下を一度だけ取得する。値を推測・再構築しない。ヘルパーが失敗した場合は、手動で代替 Git コマンドを実行せず停止してエラーを報告する（`create` が結果を返さずに中断した場合は上の `inspect`・`abandon` の手順に従う）。

     ```bash
     WT=$(printf '%s' "$SESSION_JSON" | jq -r .worktree)
     STATE_FILE=$(printf '%s' "$SESSION_JSON" | jq -r .state_file)
     DRAFT=$(printf '%s' "$SESSION_JSON" | jq -r .draft)
     DESTINATION=$(printf '%s' "$SESSION_JSON" | jq -r .destination)
     MODEL_NAME=$(printf '%s' "$SESSION_JSON" | jq -r .model_name)
     MODEL_SOURCE=$(printf '%s' "$SESSION_JSON" | jq -r .model_source)
     PREVIOUS_REVIEW=$(printf '%s' "$SESSION_JSON" | jq -r '.previous_review // empty')
     SHORT_HEAD=$(git rev-parse --short=12 "$PR_HEAD")
     ```

   - `$SHORT_HEAD` は固定した `$PR_HEAD` の 12 文字短縮 hash である。`git rev-parse` は `$WT` または `$MAIN_ROOT` など、当該 object を参照できるリポジトリ上で実行する。
   - `$PREVIOUS_REVIEW` が空なら Mode は `Initial`、helper が返した通常ファイル snapshot なら Mode は `Update` とする。ライブ `$DESTINATION` と他モデル files は読まない。
   - 以降のファイル読解・テスト実行は `$WT` を対象に行う。ただし重い一括検証は再実行しない。レビュー成果物は `create` が返した `$DESTINATION`（`$MAIN_ROOT` 直下の `reviews/` 配下。resoloop の PR なら `external/resoloop/reviews/`）に書き、`$WT` 内には書かない。
3. **既存レビューの読解（更新時）**:
   - `$PREVIOUS_REVIEW` が空でない場合だけ、その snapshot ファイルを読む。ライブ `$DESTINATION`、他モデルのレビュー本文、ディレクトリ一覧から自モデルを推測して読むことはしない。この読解はメインエージェントのみが行い、サブエージェントに委譲しない。既存 review 本文を委譲 prompt に含めない。
   - snapshot から active findings、Pending previous findings、既存の Review history、Resolved findings を把握する。旧形式で過去 HEAD が無い場合は推測せず、今回の Review history から開始し、旧形式 active 指摘の検出時 HEAD は `不明（旧形式）` とする。
   - 旧形式の active 指摘を安全に解釈できない場合は既存成果物を上書きせず停止する。
4. **差分収集**:
   - 次で PR 全体の差分を取得する。PR 内の各 commit 差分や前回 HEAD とのローカル diff は使わない。

     ```bash
     PR_DIFF=$(gh pr diff "$PR_URL")
     ```

   - `gh pr diff` 失敗時は履歴を追記せず保存しない。
   - 取得直後に HEAD consistency check 2/3 を実行する。不一致、空値、`gh` failure の場合は履歴を追記せず保存しない。

     ```bash
     CURRENT_PR_HEAD=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)
     test "$CURRENT_PR_HEAD" = "$PR_HEAD"
     ```

   - 規模判定は手順 1 で取得済みの `PR_JSON` の `additions`・`deletions`・`changedFiles` を使う（規模だけの API 往復を増やさない）。`additions + deletions` と `changedFiles` を上記 2/3 で確認した同一 HEAD に対応付け、空値・取得失敗・不一致は 0 にせず小規模とみなさない。変更量 300 行以下かつ変更ファイル 3 個以下の両方を満たせば既定は本体のみとする。バイナリ差分・規模不明・セキュリティ等は行数だけで軽量判定しない。詳細は[時間予算と委譲規約](references/time-budget.md)の「規模判定」に従う。

5. **コンテキスト読解（条件付き早期委譲）**:
   - 変更ファイル本体は、メインコンテキストで diff だけでなくファイル全体を読む。指摘の根拠となる精読をサブエージェント任せにしない。
   - 変更箇所の呼び出し元・呼び出し先の調査、依存関係ファイル（pyproject.toml / package.json / lock ファイル等）の確認、変更に対応する既存テストの探索は、[時間予算と委譲規約](references/time-budget.md)の「委譲」の起動条件をすべて満たす場合だけ、読み取り専用の補助委譲として最大 1 件を本体精読と並行して起動してよい。委譲先の調査範囲は `$WT` 上のコードと PR 差分のみとする。`reviews/` と既存 review 本文は委譲範囲・prompt から除外する。残り調査枠 10 分未満、停止手段なし、追加委譲・再委譲はしない。prompt の必須欄（対象・期限・制約・中間出力・終了）は具体値で埋める。
   - 委譲しない場合は、メインエージェントが自分で変更箇所の呼び出し元・呼び出し先を辿り、依存関係ファイルを確認し、変更に対応する既存テストを探す。
6. **プロジェクト固有観点の取り込み**: `$WT` 上の `AGENTS.md`・`CLAUDE.md`（ワールドのプロジェクトを変更する PR では、そのプロジェクトの `AGENTS.md` も）と、規約・設計ドキュメントがあれば読み、そのプロジェクトの重点観点（例: 1 オブジェクト 1 メッシュ、resoloop の安全ルール、Python は uv で実行する）を優先順位のチェックリストに加える。メインリポジトリ側と `$WT` 側の `reviews/` にある他モデルのレビューは情報源にしない（サブエージェントに委譲する場合も調査範囲から除外する）。
7. **候補洗い出し → 検証 → 報告**:
   - 優先順位に沿って候補指摘を洗い出し、検証プロトコルを通過したものだけを指摘フォーマットで報告する。
   - 調査期限・委譲期限を確認し、期限超過後は新規調査を止めて取得済み根拠で保存へ進む（[時間予算と委譲規約](references/time-budget.md)の「打ち切り」）。
   - 更新時は既存 active 指摘と前回の Pending previous findings を現在の差分と `$WT` のコードで再検証し、active・resolved・pending に分類する。未再検証の指摘を Resolved にせず、再検証できなかった前回 active 指摘は Pending previous findings へ移す。未読箇所を解消としない。再検証の最終判定と `$PREVIOUS_REVIEW` の解釈はメインエージェントが行う。
   - 継続指摘は ID・タイトル・検出時 HEAD を維持し、位置と根拠を現在値へ更新する。
   - 解消済み指摘は active Severity セクションから `Resolved findings` へ移し、解消確認時 HEAD に今回の `$SHORT_HEAD` と確認根拠を記録する。
   - Pending previous findings へ移す指摘は過去 ID・タイトル・元 Severity・検出時 HEAD・前回内容と根拠・今回未確認の理由を記録する。
   - 新規指摘には検出時 HEAD として今回の `$SHORT_HEAD` を設定する。
   - 新規 ID は active / pending / resolved 全体で ID の衝突を避ける。既存の Review history と Resolved findings は順序ごと維持する。
8. **レビュー結果の保存**:
   - draft 完成時の時刻を次で取得する。

     ```bash
     REVIEWED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
     ```

   - Review history に今回分を 1 行だけ追記する（既存行は削除・並べ替えない）。列は Reviewed at (UTC)・HEAD（`$SHORT_HEAD`）・Mode（`Initial` または `Update`）。同じ HEAD でも追記する。
   - draft/save 直前に HEAD consistency check 3/3 を実行する。不一致、空値、`gh` failure の場合は履歴を追記せず保存しない。

     ```bash
     CURRENT_PR_HEAD=$(gh pr view "$PR_URL" --json headRefOid --jq .headRefOid)
     test "$CURRENT_PR_HEAD" = "$PR_HEAD"
     ```

   - 完成したレビュー本文を `create` が返した `$DRAFT` へ書く。これはメインリポジトリと `$WT` の外部にある保存前の正本であり、保存後は手順 9 の `cleanup` がセッションディレクトリごと削除する。あとで見返す必要がある内容は `$DRAFT` の本文に含め、セッションディレクトリにしか無いファイルを残さない。保存先と draft は `create` が確定して返した `$DESTINATION`・`$DRAFT` のみを使い、パスを自分で組み立てない。
   - 時間切れでも HEAD チェックやフィンガープリント検証を飛ばさない。保存拒否時は上書きせず、エラーと保存前 draft の場所を報告する。
   - 保存は `uv run --no-project python "$HELPER" save --state "$STATE_FILE"` だけを実行する。`save` は共有ロック（Git 共通ディレクトリの `flock`）で最終検証とアトミックなコピーを直列化し、保存直前の検証として、確定した `$DESTINATION` が create 時フィンガープリントと一致することを確認してからアトミックに保存する。`reviews/` 配下の無関係な他モデルのファイルも、`reviews/` 外のメインリポジトリの変更（tracked ファイルの編集、untracked ファイルの追加、HEAD・branch の移動）も `save` を妨げない。ただし確定した `$DESTINATION` はこのセッションが保存するまで不変でなければならない。resolved path は `reviews/` 外への脱出検証だけに使い、fingerprint とアトミックな置換は lexical destination entry を対象にする。同じ PR・モデルの再レビューでは内容全体を上書きし、別名ファイルは作らない。
   - 途中確認用の `uv run --no-project python "$HELPER" verify --state "$STATE_FILE"` は残してよいが、`verify` も同じ共有ロックと上記の destination フィンガープリント検証を行う。ただし保存の安全性はその事前実行に依存しない。
   - 別モデルのレビュー結果は、`create` が返した `$DESTINATION` に従って同じ PR ディレクトリ内の別ファイルへ保存する。レビュー成果物を `$WT` 内には書かない。
9. **後片付けと報告**:
   - `save` が成功したら、続けて次を実行し、このセッションの worktree とセッションディレクトリ（`$DRAFT`・`previous-review.md`・`session.json` を含む）を削除する。

     ```bash
     uv run --no-project python "$HELPER" cleanup --state "$STATE_FILE"
     ```

   - `cleanup` は共有ロック下で、`$DESTINATION` が通常ファイルとして存在し内容が `$DRAFT` と一致すること（= 保存成功）と、削除対象が state file に固定された自セッションの linked worktree であることを確認してから削除する。どちらかを満たさない場合は何も削除せず失敗する。
   - `cleanup` が失敗した場合は削除を手で代行せず停止し、`$WT`・セッションディレクトリ・`$DESTINATION` の完全パスと失敗理由を報告してユーザの判断に委ねる。
   - `cleanup` は他の worktree、`$MAIN_ROOT` の working tree、`reviews/` 配下の他ファイルを変更しない。
   - 停止確認不能なら cleanup を省略する。停止確認不能のときだけ cleanup を省略する限定条件であり、helper が失敗した場合の既存停止規則は保持する。省略時は残った委譲 ID・停止状態・WT とセッションの完全パスを報告し、このターンを終了する。
   - 最終応答では save/cleanup の結果、`$DESTINATION` の完全パス、削除したセッションディレクトリのパス（省略時は省略理由と残した完全パス）、開始からの経過と全体実時間を報告する。保存済みレビューを後から直接書き換えない。`cleanup` 成功後は `$WT` 配下のパスは既に存在しないため案内に含めない。`create` をやり直した、または `abandon` を実行した場合は、試行 ID ごとの `inspect`・`abandon` の結果も報告する。

## 検証プロトコル

候補指摘 1 件ごとに、以下を順に行う:

1. **精読**: 指摘に関わる実コードパスを最後まで読む（途中の早期 return・ガード・呼び出し規約を見落とさない）
2. **反証試行**: 「この指摘が誤りだとしたらどこか」を明示的に検討する（既存のガード、テストによる固定、ドキュメント化された意図的トレードオフ等）。反証に成功したら報告しない
3. **実行検証**: 挙動が不確かな場合、可能なら worktree 側で実行して確かめる（関連する pytest、REPL、最小再現スクリプト）。重い一括検証は再実行しない（規約を参照）。テストコマンドが不明な場合は無理に実行しない。一時ホームが必要な場合は `env HOME="$tmpdir" ...` のワンショットだけを使い、永続シェルへ `export HOME=...` してはならない（後続の `gh` が別ホームを見て未認証になる）
4. **期限確認**: phase 境界・呼び出し復帰時・委譲開始前・新規候補や実行検証の開始前に現在時刻を確認し、調査期限と委譲期限（絶対期限・実質無進捗 5 分）を再評価する。期限超過後は新規調査を増やさず保存へ進む

反証試行のための追加委譲はしない。手順 5 で起動した 1 件の割当範囲内で得た報告は利用してよいが、確度ラベルの最終判定は、メインコンテキストが根拠（コードパス・実行結果）を直接確認した上で行う。サブエージェントの報告のみを根拠に【検証済み】を付けない。

検証結果に応じて、各指摘に確度ラベルを付ける:

- **【検証済み】**: コード精読または実行検証で裏付けがある
- **【確認推奨】**: もっともらしいが裏付けが不完全
- **【要設計判断】**: 挙動は確認済みだが、修正すべきか仕様とすべきかはユーザの判断が必要

## Severity 判定基準

| Severity | 基準                                                                                         |
| -------- | -------------------------------------------------------------------------------------------- |
| Critical | データ破壊・セキュリティ侵害・主要機能の停止が、通常の利用経路で発生する                     |
| High     | 実行時バグ・セキュリティ問題・破壊的挙動変更が、現実的な条件で発生する                       |
| Medium   | 特定条件下の実挙動不具合、互換性リスク、仕様未定義の挙動（設計判断が必要なものを含む）       |
| Low      | 実害は限定的だが対応が望ましい欠陥（依存下限未指定、稀なエッジケース、性能の二次的コスト等） |
| Info     | 実害なし。ドキュメント追随漏れ、スタイル逸脱、将来の再検討事項                               |

重大度は「影響 × 発生しやすさ」で判定し、迷ったら低い方に倒す（Severity インフレを防ぐ）。

## 指摘 1 件のフォーマット

各指摘は次のテンプレートに従う:

```markdown
### <ID>: <一行タイトル>【検証済み|確認推奨|要設計判断】

- 位置: `path/to/file.py:123`（複数箇所あれば列挙）
- 検出時 HEAD: `<12文字のshort-sha>` または `不明（旧形式）`
- 内容: 何が・どの条件（入力・状態・操作列）で起きるか
- 根拠: 読んだコードパス、実行した検証とその結果
- 推奨対応: 適切な責務境界での最小の修正案（あわせて固定すべきテスト）
```

- ID は Severity 別の連番（Critical: C-1、High: H-1、Medium: M-1、Low: L-1、Info: I-1）
- 「内容」には具体的な発生条件を必ず書く。「〜の可能性がある」だけの指摘は書かない
- 新規指摘の検出時 HEAD は今回の `$SHORT_HEAD` を設定する。継続指摘は検出時 HEAD を維持する。旧形式から移行する指摘で過去 HEAD が無い場合は `不明（旧形式）` とし、hash を生成・推測しない

## 優先順位

1. 実行時バグ
2. セキュリティ問題
3. 破壊的な挙動変更
4. 依存関係の互換性リスク
5. 不足しているテスト
6. 保守性リスク

## コメントしないこと

- 無害なフォーマット差分
- 命名の好み
- 根拠のない理論上の問題
- 差分と無関係な広範なリファクタリング
- 差分外の既存コードの問題（diff が顕在化させる場合を除く）
- 重要な不変条件を隠していないコメント不足
- リンタ・フォーマッタで機械的に検出できる指摘だけの列挙

## 出力

以下のテンプレートを使用する。指摘が 0 件の Severity セクションは省略する。件数表は active findings のみから計算する。重大度判定は active findings、確認不足判定は coverage と pending も参照する。

```markdown
- 対象: PR #<N> / head <12文字のshort-sha> / <YYYY-MM-DD>

## Review history

| Reviewed at (UTC) | HEAD                  | Mode                  |
| ----------------- | --------------------- | --------------------- |
| <RFC3339 UTC>     | `<12文字のshort-sha>` | Initial または Update |

## Summary

（総評 2〜4 文。何をレビューし、何を実行検証したかを含める）

| Severity | 件数 |
| -------- | ---- |
| Critical | n    |
| High     | n    |
| Medium   | n    |
| Low      | n    |
| Info     | n    |

## Critical

## High

## Medium

## Low

## Info

（各指摘は「指摘 1 件のフォーマット」に従う）

## Review coverage

（読んだ範囲・読めなかった範囲・実行検証・未実施の検証・委譲状態と省略・中断理由を記載する）

## Unverified candidates

（位置・具体的な疑い・確認済み根拠・不足根拠・次の確認方法を記載する。なければ「なし」と書く）

## Pending previous findings

（過去 ID・タイトル・元 Severity・検出時 HEAD・前回内容と根拠・今回未確認の理由を記載する。該当なしなら省略可）

## Test suggestions

（番号付きリスト。各項目にどの指摘（ID）を固定するテストかを明記する）

## Review timing

（開始 UTC・全体予算・調査期限・draft 時点経過・phase 内訳・委譲時刻と状態・超過理由を記載する）

## Merge recommendation

（下記基準で 1 つを選び、理由を 1 文添える）

## Resolved findings

### <過去のID>: <過去の指摘タイトル>

- 検出時 HEAD: `<12文字のshort-sha>` または `不明（旧形式）`
- 解消確認時 HEAD: `<今回の12文字のshort-sha>`
- 確認根拠: <現在のコードパスまたは実行検証による根拠>
```

- Review history の時刻は `$REVIEWED_AT`（`date -u +"%Y-%m-%dT%H:%M:%SZ"`）を使う。HEAD は `$SHORT_HEAD`（12 文字）。Mode は `$PREVIOUS_REVIEW` が空なら `Initial`、snapshot があれば `Update`
- 既存 Review history 行と既存 Resolved findings は削除・並べ替えず、今回分だけ追記する。同じ HEAD でも追記する
- Resolved findings が無い初回で解消も無い場合はセクションを省略してよい。更新で既存 Resolved findings がある場合は維持する

Merge recommendation の判定基準:

- **Request changes**: 【検証済み】の Critical / High が 1 件以上ある
- **Needs manual verification**: 【検証済み】の Critical / High がなく、active な【確認推奨】の High 以上・重要な未検証候補・未再検証の過去指摘・必要な検証の未実施・差分の実質的な未読箇所がある
- **Approve**: 上記に該当せず、【検証済み】の Critical / High が 0 件で残る指摘が Medium 以下または【要設計判断】のみ。補助委譲の省略・中断だけで本体が必要範囲を確認済みなら判定を悪化させない

## 出力前セルフチェック

- 冒頭の `対象 PR` 行から引数を読み取り、未指定判定を正しく行ったか
- `PR_HEAD`、`gh pr diff`、`$WT` が同じ headRefOid に対応しているか（3 地点の HEAD consistency check がすべて成功したか）
- 自モデルの `$PREVIOUS_REVIEW` 以外（ライブ `$DESTINATION`、他モデルのレビュー本文）を読んでいないか。既存 review 本文をサブエージェントへ渡していないか
- Review history に UTC、12 文字 HEAD、Mode（`Initial` または `Update`）が今回分として 1 行だけ追加されているか。既存行を削除・並べ替えていないか
- active 指摘の検出時 HEAD が維持または新規設定されているか。旧形式の不明 hash を生成していないか（`不明（旧形式）` を使う）
- 解消済み指摘が active counts から除かれ、Resolved findings に存在する（検出時 HEAD・解消確認時 HEAD・確認根拠付き）か
- 未再検証の指摘を Resolved にせず Pending previous findings に保持したか。新規 ID が active / pending / resolved 全体で ID の衝突を避けているか
- Review coverage・Unverified candidates・Pending previous findings・Review timing を記載したか（Pending previous findings は該当なしなら省略可）
- 最終応答に save/cleanup の結果と開始からの経過・全体実時間を記載したか
- 件数表と本文の active 指摘数が一致しているか
- 全指摘に位置（`file:line`）・具体的な発生条件・確度ラベルがあるか
- 各指摘に反証を試みたか
- 重い一括検証（`bash .devcontainer/run-tests.bash` など）を再実行していないか。指摘の検証に必要な範囲の実行はしてよい
- 「コメントしないこと」に該当する指摘が紛れていないか
- メインリポジトリ側と `$WT` 側の `reviews/#<PR番号>-<変換後ブランチ名>/` にある他モデルのレビュー本文を、自分でもサブエージェント経由でも開いたり検索対象に含めたりしていないか
- Merge recommendation が判定基準と整合しているか。重大度判定は active findings、確認不足判定は coverage と pending も参照する
- `MAIN_ROOT` は PR URL の `owner/repository` を「リポジトリ境界」の表に照らして確定したか（このリポジトリ=検証済みの親 main checkout、resoloop=検証済みの `external/resoloop`、その他は明示された `CODE_ROOT` を照合し、明示が無い・不一致なら停止）。PR の head を `$PR_REMOTE` から取得したか。`merge-base HEAD "$PR_REF"` の成功を確認したか
- helper の呼び出しを他の処理とまとめたり、600 秒未満のタイムアウトで打ち切ったりしていないか
- `create` に `--attempt-id "$ATTEMPT_ID"` を渡し、結果を返さなかった試行を `inspect`・`abandon` で扱ったか（拒否されたら手で消さずに停止したか）
- `create` が返した `model_name`、`draft`、`destination`、`previous_review` を変更・再構築せず使用したか
- 正確な `$MODEL_NAME` を `--model-name "$MODEL_NAME"` で渡し、filename から推測していないか（Codex はヘルパーが確定する）
- `save` を `--state "$STATE_FILE"` だけで実行し、caller-selected path を渡していないか
- `save` の返却した destination が存在し、最終応答にその完全パスを記載したか
- 同じ PR・モデルの再レビューで既存ファイルの内容全体を上書きし、別名ファイルを作っていないか
- レビュー成果物が `create` が返した `$DESTINATION` に書かれ、`$WT` 配下に無いか
- `git clean`、強制 checkout/reset を実行していないか。worktree の削除を `cleanup` 以外の手段で行っていないか
- 保存前に検証（確定 `$DESTINATION` のフィンガープリントが不変）が成功し、`save` の出力先が存在するか
- あとで見返す必要がある根拠をレビュー本文に転記し、`$WT` とセッションディレクトリにしか無い証跡ファイルに依存していないか
- `save` の成功後に `cleanup --state "$STATE_FILE"` を実行し、worktree とセッションディレクトリが削除されたか（停止確認不能で省略した場合は、省略理由と残した完全パスを報告したか）
- `cleanup` が失敗した場合に `git worktree remove` や `rm -rf` を手で組み立てず、停止してパスを報告したか
- 最終応答に `$DESTINATION` の完全パスと削除したセッションディレクトリを記載し、`$WT` 配下のパスを参照していないか（省略時は省略理由と残した完全パスを報告する）
