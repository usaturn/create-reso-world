# 非対話レビューの入口と結果

## 入力

対話・非対話とも `scripts/review_run.py prepare` → 固定された全体差分のレビュー → `complete` の順を使う。呼び出し元ごとの private command で手順を切り替えない。ランナーの外側の Request / Receipt / Result は [agent-runner](../../../../tools/agent_runner/interfaces.rst) のまま。この文書の結果は Receipt.payload に入るJSON objectであり、Receiptやresult.jsonをworkerが自作するものではない。

| 引数 | 意味 |
|---|---|
| `--pr` | 必須。番号・`#番号`は親origin、URLはそのrepo。非対話で欠けたらfailed。別repoの同じ番号を探さない |
| `--runtime` | 必須。claude-code / devin / pi / codex / cursor |
| `--model-name` | 現runtimeが提示した正確なモデルだけ。Codexは省略。Piは省略すれば実PI_MODELを使うがPI_PROVIDERも必須。指定値の不一致は拒否 |
| `--request` | runnerが渡した実Request JSON。run_id/request_id/agent_id/roleを使用し、work_dir=cwd、result_shape=jsonを照合。非runnerなら省略し未観測をunknownにする |
| `--review-commit` | 任意の40桁SHA。省略はresolve時のPR head。明示指定はPR全体の対象commitであり、commit単体diffの指定ではない |
| `--source-root` | 対象 commit を持つ main checkout の絶対パス（`CODE_ROOT`）。既知経路以外は必須で、PR base repo と一致する remote が 1 件必要。ResoLoop の上流 PR は origin でなく upstream を使う。linked worktree の未 push object は main checkout と共有。checkout の探索・clone はしない |
| `--records-comments` | 任意。PRコメントの全ページJSON（`gh api --paginate --slurp`の結果）。ローカル判断の記録も渡せる。共有parserで対象PRを照合・集約。省略なら同じPRのコメントを全ページ取得する |
| `--temp-root` | 任意のセッション親領域。セッション自体はhelperが一意に作り再利用しない |

非対話の assistant 最終出力は complete/fail の JSON payload 1 回だけ。挨拶、作業前の宣言、途中説明、JSON後の解説を出さず、ツール呼び出しだけでレビューを進める。Devin headlessのstdoutは途中assistant textも連結する。抑止漏れへの防御としてDevinだけは最終JSONを1つの `json` コードフェンスに載せる（既存adapterが対応済み）。途中にJSONフェンスを出さず、JSONの外に説明を付けない。回収されるobjectの内容は同じ。phaseはdraftのcoverageへ記録する。

runnerのrequestはそのattemptに渡されたものだけを読む。callerがpathを示せばそれを使う。既存runnerでは起動cwdの親の `request.json` がそれに当たる。別attemptのrequestを探索しない。completeも起動時と同じcwdで呼ぶ。レビュー用WTは別の隔離領域であり、そこへcdしたままrequest検査を実行しない。

runnerの役割が `writes=false`（`inspect` など）のとき、その指示はレビュー対象（review用WTの追跡ファイルを含む）・どのcheckoutの追跡ファイル・他担当の成果を変更しないという意味である。helperが管理する実行記録・セッション（WT・backup・draft・state）・正式保存・保存ロック・Gitのworktree登録とref・uvの環境への書き込みはこれに当たらず、callerがrunnerの作業範囲の指示に「Caller-authorized exceptions」として列挙する。許可項目は `scripts/review_run.py` の `helper_write_exceptions(*, tool_root, parent, parent_git, review_dir, number, source_git=None, source_shallow)` の戻り値を caller が `run_workflow(..., write_exceptions=...)`（CLI は繰り返しの `--write-exception`）に渡す。自動で付くとは仮定しない。外部 checkout では `source_git` をその Git 共通ディレクトリにし、親の保存ロックと区別する。`source_shallow` には、その checkout が浅いかを `pr_review_workspace.uses_owned_history` で判定して渡す。浅い checkout では helper が履歴をセッション内の所有 Git に取得し、元の Git は読むだけなので、親と同じ Git でも許可は親の保存ロックだけになる。

helper の実行には pydantic を持つ読んだ skill の source checkout のルート project（`pyproject.toml`・`uv.lock`）を使用する。`TOPLEVEL` は**読んだskillのsource checkoutのroot**、`RUN_HELPER`も同じ版。レビュー対象repoや今のcwdからhelperの置き場所を推測しない。例えばcallerがfeature版skillを指定したときは、そのfeature版のhelperを使う。uv の Python は3.14以上、lock を変更しない。最初の helper 呼び出しより前に `RUN_HELPER="$TOPLEVEL/.agents/skills/pr-review/scripts/review_run.py"` を設定する。

## prepare

読み込んだskillのsource root・PR・runtime・正確なmodelを具体値へ設定して呼ぶ。非対話の例（不要な任意引数は行ごと省く。空の文字列を渡さない）:

```bash
RUN_HELPER="$TOPLEVEL/.agents/skills/pr-review/scripts/review_run.py"
uv run --project "$TOPLEVEL" --locked python "$RUN_HELPER" prepare \
  --pr "$PR_ARG" --runtime "$RUNTIME" --model-name "$MODEL_NAME" \
  --request "$REQUEST" \
  --review-commit "$REVIEW_COMMIT" --source-root "$SOURCE_ROOT" \
  --records-comments "$COMMENTS_JSON"
```

Codexはmodel-nameを省き、Piも現在envから読むときは省く。通常headならreview-commitを省く。非runnerならrequestを省く。source-rootやrecords-commentsも省略できる。既存の `pr_review_workspace.py create --target` / legacy呼び方は他callerの互換のため残すが、このskillの別手順にはしない。

成功は exit0・`status: prepared`。返されたstate_file / worktree / draft / findings_draft / previous_review / destination / reviewer / reviewed_head / pr_head / base / records / diff_command / attempt_idをそのまま使う。モデル名・パス・対象を作り直さない。prepare は resolve、照合済み base remote/commit object 確認、PR head fetch、API head照合、fresh detached worktree、destination snapshot、merge-base、v2候補scaffoldを作る。merge-base用のbase fetchは、そのfresh worktreeの専用refに固定し、共有の追跡ref・tag・FETCH_HEADを更新しない。専用refは既存helperのworktree cleanupで一緒に消える。対象 checkout が shallow の場合は、照合済み remote からセッション内の所有 Git repository へ完全な履歴を直接取得する。指定された未 push commit の object は元 checkout から取得する。元の shallow boundary・共有 ref・FETCH_HEAD は変えず、complete が保存・cleanup まで行う。

- 本体・参照の変数はprepareの値に対応する。WT=worktree、BASE=base、REVIEWED_HEAD=reviewed_head、PR_HEAD=pr_head、PREVIOUS_REVIEW=previous_review（nullなら空）。呼び出しを跨いでシェル変数が残るとは仮定しない。
- `diff_command` は `git -C <WT> diff --find-renames <base>..<reviewed_head>`。全体を読み、変更ファイルは全文を読む。指定commitにliveのgh pr diffを混ぜない。
- 通常headの `review_file` は従来stem、指定commitは `<model>-commit-<fullSHA>.md`。同じcommitをPR headとして読む場合と明示commitとして読む場合も別保存になる。
- そのsave先のsnapshotが無ければ `Initial`、有れば `Update`。指定commitでもhistoryのModeはこの2値のみとし、列とheadの12桁は維持する。指定commitは保存名、候補JSONの `reviewed_head`、Review timing の `pr_head` / `review_kind`、Review coverage で区別し、判断の記録が受け付けないModeを追加しない。
- `records.decisions` のsources/state/history、最後のroundsのreviewed_head/outcome/commitを読み、本体の判断済み指摘と前回修正の重点確認へ使う。記録の取得失敗は「記録なし」と推測せずfailed。無い記録は空の状態として正常。
- scaffoldのschema/kind/source/pr/reviewed_head/base/reviewer/skillは固定。変更できるのはcoverage/findings/unverified_candidates。coverage.readを実際の精読範囲で埋める。空scaffoldを指摘0として完了させない。
- 本文は出力templateに従い、同じ指摘・ID・位置を書く。draftが無い・JSONが無い・不整合なら保存成功にならない。

## 実行記録

helper は、resolveの後の実行ごとに、親の `reviews/<owner>/<repo>/#<PR>-<branch>/runs/<開始時刻>-<model>-<接尾辞>.json` へ実行記録（`kind: review_run`）を書く。形式・状態の移り方・書き込みの失敗の扱いは [review-findings](../../../review-findings.md) 4.1節に定義する。モデルは記録を書かず、手で直さない。

- prepareはresolve直後に `started` で作り、完了時に入力の指紋（request・前回レビュー・判断の記録・差分の規模）を書き足す。作れなければprepareをfailedにする。resolve前の失敗は記録しない
- completeは `success` か `failed`（`complete`・`save`・`cleanup`）、`fail --state` は `failed`（`review`）にする。強制終了・タイムアウトでは `started` のまま残る
- prepare・complete・failの返却JSONは `run_record`（記録の完全パス、無ければnull）を持つ。作成後の更新に失敗したときだけ `run_record_error` を足し、レビューのstatusは変えない

## セッションの退役

定期掃除（`.devcontainer/cleanup-workspace.bash`）と repo-cleanup-after-merge は、どちらも `pr_review_workspace.py reap-check --allow-failed` → `cleanup --strict-reap --allow-failed` でセッションを退役させる。

- 定期掃除が helper を見つけられるのは、リポジトリの `.devcontainer/cleanup-workspace.bash` から実行したときだけである。24 時間ごとに動く `~/bin` のコピーは helper を見つけられず、pr-review のセッションをすべて保持して報告するだけになる
- 失敗セッションの停止の証拠は、`attach-runner` が実行記録の `runner` 欄に書いた `stop_confirmed: true` で、かつ `attempt.state` が `self` 以外であることである。`attach-runner` を省いた失敗セッションは、停止を確認できず保持される
- 失敗セッションは、未保存の draft・編集した候補・`previous-review.md`・未知のファイルがあれば保持する。保存済みのセッションは、再レビュー（`previous-review.md` が destination と一致するもの）も含めて退役できる
- 保持するときは終了コード 1 と `status: "retained"` の JSON（`reason`・`retirement`・`stop_confirmation_needed`・`retained_paths`）を返す。状態を読めない、または引数の誤りは終了コード 2 と stderr の `error: ...` で、何も変えない。定期掃除は `--operator-confirmed-stopped` を使わない

## complete

```bash
uv run --project "$TOPLEVEL" --locked python "$RUN_HELPER" complete --state "$STATE_FILE"
```

completeはrequestのbytes/hashとbinding、読んだ主要skillのhash、候補の固定項目とcoverageを検査する。同じv2 reviewer/provenance/timingを候補と本文の自動生成 `Review timing` に記録してから、既存helperのsave --findingsを呼ぶ。lock内でworktree commit、現在のPR head、destination fingerprint、候補schema/pairを検査し、両ファイルを保存する。候補コピー後に本文保存が失敗すれば既存のrollbackを使う。成功後だけhelperのcleanupを呼ぶ。

本文のReview timingを二重に手書きしない。全体予算・調査期限・phase内訳・委譲状態/省略理由・超過理由はReview coverageへ書き、自動生成の実測と区別する。timingはprepare開始からdraft確定までの実測UTC/経過秒数、waiting_secondsは未計測ならnull。save_seconds / cleanup_seconds / total_secondsは最終payloadの別計測であり、本文を保存後に追記しない。

成功payloadの必須項目:

| キー | 内容 |
|---|---|
| schema_version | 1 |
| status | success。fail/検査拒否/cleanup失敗はfailed |
| run_id/request_id/agent_id/role | 実Requestの値。非runnerで取得不能ならunknown |
| attempt_id | prepareが作った試行ID。残った試行を `pr_review_workspace.py abandon --session-dir` で指定するときに使う。この欄の無い古いセッションはnull |
| repository/pr_number | PR base側repoと番号 |
| pr_head/reviewed_head | resolve時のPR headと実レビュー対象のfullSHA。指定commitなら違うことがある |
| review_file/findings_file | 保存された成果2件の完全パス。helperが決定しpair検査済み |
| active_findings | active件数。successかつ0で初めて「検査済み成果の指摘0」と扱う |
| cleanup | success。削除拒否はfailed、未実施はnot_attempted。fail --abandonでは試行を消せたらsuccess |
| cleanup_details | helperの削除結果。pr_ref_status=repinnedなら後続セッションのrefを残した理由と完全名を報告。deleted/missingも区別する。keptは試行のheadが分からずrefを残した。fail --abandonで消せなければerrorに理由 |
| retained_paths | failed時の残存確認先worktree/draft/session/pr_ref。途中cleanup済みを含み得る。成功とfail --abandonで消したときはnull。削除済みWTを成果参照にしない |
| reason | successはnull、failedは具体的理由 |
| reviewer/timing | 保存成果と同じ実行情報・時刻 |
| save_seconds/cleanup_seconds/total_seconds | 実測。未実施を実測0にしない |
| run_record | 実行記録の完全パス。更新に失敗したときだけ run_record_error に理由 |

失敗payloadはstatus=failed・非ゼロ終了・reasonを返す。成果が無いときのactive_findingsとartifact pathはnull。保存済みでcleanupだけ失敗したときは保存した成果と件数、cleanup=failed、残るstate_fileを返す。完全パスのstate/draft/WT/refを添えて停止し、保存や削除を手で代行しない。補助worker停止未確認ならcomplete自体を呼ばない。

prepare前やレビュー途中に終了するときは、同じ通常入口でfailed objectを作る:

```bash
uv run --project "$TOPLEVEL" --locked python "$RUN_HELPER" fail \
  --request "$REQUEST" --reason "$REASON"
```

stateがある場合は `--state "$STATE_FILE"` を追加する。非runnerならrequestを省く。理由は観測した不足/失敗を具体的に書く。失敗後に通常headへfallbackしたり、別modelで保存したりしない。prepareの後にレビューせずに止めるときは、SKILL.mdの「保存しなかったとき」の条件で `--abandon` も付ける。helperは記録の後に試行を消し、結果を `cleanup`・`cleanup_details`・`retained_paths` に返す。

## callerが結果を回収するとき

1. runnerの外側state、exit_code、stop_confirmedを確認する。missing_result/invalid_result/timed_out/停止未確認を空レビューにしない。
2. payload.statusも確認する。外側がsuccessでもpayload.failedならレビュー成功ではない。prepared object はレビュー完了ではない。after_run を無効にした直接 caller、および after_run を実行しない Python API の caller は、BatchResult を result.json へ保存してから attach-runner を明示実行する。
3. payloadのrun/request/agent/roleを実Request/実担当Resultへ照合し、repo/PR/対象commitも依頼と一致することを確かめる。要求した担当とfallback後の実担当を混同しない。
4. successだけ成果2件とschema/pairを回収する。active件数だけでは完了の根拠にならない。保存済み成果を後から直接書き換えない。
5. provider/effort/session/CLIの未観測を設定で補わない。runnerが事後に観測したIdentityは外側結果として別に保持し、workerが観測できなかった欄を実測済みと扱わない。主要skillのpath/hashとprovenance.skillsは同じ値。runnerの観測値は、下の `attach-runner` が実行記録の `runner` 欄にだけ書く。

## 観測値の結び付け（attach-runner）

各レビュアーが固定 PR 全体を独立にレビューし、自モデルの Markdown/候補 pair だけを保存する。moving HEAD 拒否を指摘 0・保存成功にしない。

```bash
uv run --project "$TOPLEVEL" --locked python "$RUN_HELPER" attach-runner --result "$RESULT_JSON"
```

runnerの `result.json` の各試行を、run_id/request_id/agent_id/roleが `reviewer.provenance` と一致する実行記録と突き合わせ、Identity（null は unknown）と試行のstate/exit_code/elapsed_seconds/stop_confirmedを `runner` 欄に書く。provenanceのunknownは書き換えない。

- 書き先は親のmain worktreeの `reviews/<owner>/<repo>/#<PR>-<branch>/runs/*.json` のうち、形式を満たし置き場所とPRが合う記録だけ。workerが返したパスは使わない。対象外のファイルは `skipped` に数えるだけ
- 同じ値なら書かず `unchanged`。違う値が既にあれば、どのファイルにも書かずstatus=failed（終了コード1）
- 一致する記録の無い試行（PRが決まる前の失敗など）は `unmatched` にIDとstateを並べるだけ
- 雛形の workflow `review` は、runnerの後処理（`after_run`）でこのコマンドを呼ぶ。個人設定で止めた直接 caller と Python API の caller は、run の後に attach-runner を呼ぶ。after_run の失敗は runner の終了コードを変えないので、summary の after_run と更新後の payload を必ず確認する

停止条件: API/認証失敗、model未観測、wrong repo、commit object無し、moving PR head、worktree commit変更、request変更、skill変更、destination変更、成果欠落/不整合、cleanup拒否。いずれも利用者への確認待ちにせずfailedで終了する。moving PR headでも自動でレビューし直さない。
