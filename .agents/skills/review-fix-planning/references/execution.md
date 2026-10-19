# 役割の実行と修正不要の最終化

review-fix-planning の完遂で、修正の実装・修正後の自己レビュー・修正の確認を agent-runner の担当で実行し（`scripts/run_roles.py`）、修正が不要なときに状況の投稿・マージ・関連 Issue の更新を行う（`scripts/finalize.py`）手順である。採否・結論・自己レビューの回数は [SKILL.md](../SKILL.md) の規則で決める。ここに書く helper は、その規則の中で使う手段であり、runner の `success` は応答を回収したことであって、修正の合格ではない。

- `TOPLEVEL` は読んだスキルの source checkout（共通 context の `tool_root`）、`MAIN_ROOT` は専用の worktree（共通 context の `code_root`）、`REVIEW_DIR` は「第1引数の解決」で決めたレビューディレクトリ、`HEAD_SHA` はレビュー対象の PR の head である
- helper は `uv run --project "$TOPLEVEL" --locked python` で動かす。対象 checkout や cwd から helper の置き場所を推測しない
- 依頼・記録・結果の JSON と run の出力は、親の main checkout（`PARENT_ROOT`）の `tmp/agents/` に作ったセッションディレクトリ（`SESSION`）の中に置く。runner の出力先（`--output-dir`）は、その中の存在しない新しいパスにする

```bash
SESSION="$(uv run --no-project python "$TOPLEVEL/.agents/scripts/agent_tmp.py" mkdir "review-fix-planning-pr$PR_NUMBER")"
```

agent-runner の設定は、雛形（`$TOPLEVEL/.devcontainer/agent-runner.toml`）→ 個人設定 → 明示した `--assign` の順に重なる。雛形の既定は、`implement` が `claude-opus`、`self-review`・`fix-check` が `self` である。PR 修正ループ（#156）から呼ばれたときは、ループが返す `planning.run_roles_options`（`--template`・`--config`・`--assign`）をそのまま付ける。存在しない担当や、投影できない設定を `self` に黙って置き換えない。

## 1. 修正の実装（`--phase implement`）

SKILL.md の結論 1 の手順 1 で、「対応する」項目を設定の担当に直させる。

依頼の JSON（RoleInput）は次の 5 項目だけを持つ。ほかのキーは拒否される。

| キー | 値 |
| --- | --- |
| `repository` | `MAIN_ROOT` の絶対パス |
| `source_head` | `HEAD_SHA`（レビュー対象の push 済み HEAD）の完全な SHA。途中で別の HEAD に置き換えない |
| `revision` | 修正を始める commit の完全な SHA（通常は `HEAD_SHA`） |
| `pr` | `{"repository": "$PR_REPO", "number": $PR_NUMBER}` |
| `prompt` | `{"implement": "<完全な依頼>"}` |

`prompt.implement` は、それだけで作業できるように書く。

- 「対応する」項目ごとの原指摘の参照、致命的である理由、守る条件と影響経路の表、Spec の修正方針、担当するファイル、作業に入らない範囲
- 実行する検証のコマンドと、テストを足すかどうかの理由（`AGENTS.md`「テストの採用基準」を定義元として参照させる）
- 作業は runner が用意した worktree（`Request.work_dir`）の中だけで行い、ほかの worktree・未コミットの変更を使わない。入れ子の担当の起動、予約 ref・Issue・PR の更新、push、マージをしない
- 結果の JSON に、行った操作、作った commit、実行した検証の argv・HEAD・終了コード、終わらなかったこと、残したパスを書く。測れない識別情報は `unknown` にする

```bash
uv run --project "$TOPLEVEL" --locked python \
  "$TOPLEVEL/.agents/skills/review-fix-planning/scripts/run_roles.py" \
  --phase implement --request "$SESSION/implement-request.json" --output-dir "$SESSION/implement-run"
```

- 割り当てが `self` なら外部を起動しない。`roles.json` の `self_prompts.implement` を司令塔が自分で実行する
- 外部の担当なら、停止の確認（各 attempt の `stop_confirmed`）の後に、実際の Request・Result の role・agent・commit・work_dir を照合し、その commit の差分だけを確かめてから `MAIN_ROOT` に取り込む（runner の worktree は同じ Git を使うので、`git -C "$MAIN_ROOT" cherry-pick <commit>` で取り込める）。応答の `success` を、テストの合格や commit の成功とみなさない
- 取り込んだ後は、SKILL.md の「実装後」の手順 1〜3 を司令塔が行う。既存の PR の head ブランチ以外のブランチ・PR を作らない
- 終了コード: 0 は回収した（`self` を含む）、1 は失敗・停止未確認・領域の変更、2 は入力・設定・起動の誤り（理由は標準エラー出力）
- 起動の前の checkout の監査で止まったとき（終了コード 1、標準出力の `category` が `environment`）は、`checkout_audit` に挙がったパスと状態を報告し、結論 3（環境）にする。worktree の登録を勝手に消したり直したりしない

## 2. 修正後の自己レビュー（`--phase self-review`、1 回だけ）

SKILL.md の「修正後の自己レビュー」の 1 回は、この呼び出しの 1 回である。self-review（PR 全体の再レビュー）と fix-check（修正の確認）の 2 つの役割を、1 回の `run_workflow` で同時に動かす。個別の review-verify の dispatch を追加で起動しない。

### 2.1 起動の前にそろえるもの

1. 修正をローカルで commit し、「実装後」の手順 1〜3 の検証が通っている。`revision` はその HEAD
2. 確認済みの一覧 `REVIEW_DIR/verified/<source_head の先頭 12 文字>.json`（SKILL.md の手順 3）。無ければ自己レビューを始められないので、結論 3（環境）にする
3. 工程の記録の仮の版 `REVIEW_DIR/verified/<source_head の先頭 12 文字>.planning.json`。形は `.agents/review-findings.md` 6 章の v2。`outcome` は仮に `stopped`、`comment_id` は null、`activities` には実際に行った工程だけを書き、`pre_push_review` は入れない。`review_findings.py validate` を通す。同じファイルを、サイクルの最後に更新する（[round-records.md](round-records.md) 7 章）
4. fix-check の独立の保存先 `FIX_STAGING="$SESSION/fix-check-review"`。作ってから、入力の確認済みの一覧を `cp` で `$FIX_STAGING/verified-input.json` に写す（symlink にしない）。self-review の役割が `REVIEW_DIR` に保存するので、fix-check の保存先を `REVIEW_DIR` にすると、dispatch から accept までの保存先の照合で拒否される。保存先は起動の前に作っておく（起動の後に作った保存先は受け取れない）
5. 修正の確認の入力 `FIX_INPUT`（review-verify の `fix_check` の 7 項目）

| キー | 値 |
| --- | --- |
| `repository` | `MAIN_ROOT` |
| `from` | `source_head` |
| `to` | `revision` |
| `fix_ids` | 「対応する」判断の ID（判断の記録の `id`） |
| `fix_sections` | Spec の「対応する」項目の修正方針・守る条件と影響経路の表・実行した検証の全文 |
| `verified_file` | `$FIX_STAGING/verified-input.json` |
| `review_dir` | `$FIX_STAGING` |

### 2.2 依頼

依頼の JSON は 1 章と同じ 5 項目で、`revision` を修正後の HEAD にし、`prompt` に `self-review` と `fix-check` の両方を書く。

- `prompt["self-review"]`: pr-review の本体と `.agents/skills/pr-review/references/noninteractive.md` を読み、非対話の入口で PR 全体を再レビューする。`prepare --pr "$PR_URL" --runtime <自分の runtime> --request <その attempt の request.json> --review-commit <revision> --source-root <対象の main checkout> --records-comments <PR の全コメントの JSON>` → prepare が返す固定の全体差分・変更ファイルの全文・関連するコードとテスト → `complete`。merge-base から修正後の HEAD までの全体差分であり、修正だけの差分のレビューではない。守る条件・影響経路・実行した検証・未確認の事項を渡し、指摘に再現の手順か根拠（ファイルと行）を付けさせる。出力は `complete` の payload
- `prompt["fix-check"]`: 渡した 7 項目だけで review-verify の `fix_check` を行う。SKILL.md の観点 1（反証: 修正した条件が破れる入力・操作順・経路、旧版との挙動の差）と観点 3（検証の検出力: 追加・変更したテストが修正の対象の欠陥を検出できるか）を確認の対象に含める

`run_roles.py` は、fix-check の依頼に固定の指示・7 項目・review-verify の SKILL.md を足し、全体の依頼に「自分の役割の依頼だけを実行する」指示を付ける。

```bash
uv run --project "$TOPLEVEL" --locked python \
  "$TOPLEVEL/.agents/skills/review-fix-planning/scripts/run_roles.py" \
  --phase self-review --request "$SESSION/self-review-request.json" --output-dir "$SESSION/self-review-run" \
  --planning-file "$REVIEW_DIR/verified/${SOURCE_HEAD:0:12}.planning.json" --fix-input "$SESSION/fix-input.json"
```

### 2.3 1 回の枠

- `run_roles.py` は、起動の前に工程の記録の `activities` に `stage=pre_push_review` を 1 件足す（排他ロックと一括置換）。司令塔は手で書き足さない（予約済みとして拒否され、その枠は消せない）
- 失敗・中断でも枠は戻らない。2 回目の呼び出しは拒否される。別のファイル名・別のモデル・別の phase 名で上限を回避しない
- 予約より前に止まる誤り（設定の投影、DSH・codex の担当、依頼・fix-input・確認済みの一覧の誤り、出力先が既にある、checkout の監査）では枠を消費しない。直してからもう一度呼んでよい

self-review・fix-check には、runtime が `dsh` の担当（`dsh-ccd`・`dsh-go`）も `codex` の担当も、一次担当・fallback のどちらにも割り当てられない。DSH は pr-review の親の準備（`prepare-parent`・保存先への書き込み・`staged` の保存）が要るが `run_roles.py` はしない。codex は `writes=false` の役割を read-only の sandbox で起動し、pr-review・review-verify の helper が uv のキャッシュ・一時ディレクトリ・保存先に書けない。どちらも完了できずに枠だけを消費するので、`run_roles.py` が予約の前に終了コード 2 で止める。`implement` は対象外である。

外部の担当に割り当てた役割には、その役割の helper の書き込み（pr-review の `helper_write_exceptions`、review-verify の `fix_check_write_exceptions`）を、runner の作業範囲の指示の例外として `run_roles.py` が渡す。各行の末尾に `(self-review role only)`・`(fix-check role only)` が付く。`self` の役割には渡さない。

### 2.4 受け取りと判定

- 標準出力の `pending_self` に挙がった役割は、司令塔が実行する（使えるサブエージェントに任せてもよく、1 回と数える）。実行していない役割を完了にしない
- self の fix-check: `fix-check-receipt/dispatch.json` の `prompt` に従って確認し、確認済みの一覧（`mode: fix_check`）と文書の候補を `review_findings.py validate` に通してから `$FIX_STAGING/verified/` に保存する。自分の model・runtime・provenance と実際の時間を書き、外部の担当の識別情報を作らない
- 外部の fix-check: 次で受け取る。終了コード 0 のときだけ受け取る。担当の「passed」だけを取り込まない

  ```bash
  uv run --project "$TOPLEVEL" --locked python \
    "$TOPLEVEL/.agents/skills/review-verify/scripts/dispatch.py" accept \
    --run-dir "$SESSION/self-review-run/<artifact_dir の名前>/fix-check-receipt"
  ```

- 外部の self-review: runner の state・終了コード・停止の確認と、payload の `status`・run・request・actual_agent・role、repository・PR・review commit、保存された本文と候補の 2 件、cleanup と残ったパスを照合する。保存された成果を直接直さない
- 取り込み: `$FIX_STAGING/verified/` の `<to の先頭 12 文字>.fix-check.json` と `.statement-candidates.json` を、同じ内容で `REVIEW_DIR/verified/` に写し、要約 `<to の先頭 12 文字>.fix-check.md` を書く。同じ名前で内容が違うファイルが既にあれば、上書きせずに止める
- 指摘は SKILL.md の「分類の仕様」で判定する。fix-check 自身の指摘（出典の無いもの）は `fix-check#V-<n>@<to の先頭 12 文字>` として扱う。致命的な指摘は直して「実装後」の手順 1〜3 をやり直し、2 回目の自己レビューはしない。再レビューしていないことを Spec と状況コメントに書く
- 終了コード 0 は回収（`self` を含む）であり、レビューの合格ではない。1（失敗・停止未確認・保存先の変更）のときは、停止を確かめられない資源を消さず、残ったパスを報告する。自己レビューを終えられなければ結論 3 にする（枠は消費済みで、2 回目はできない）

## 3. 修正不要の最終化（`finalize.py`）

SKILL.md の結論 2 の手順 1〜5（検証、base との一時的な merge での検証、マージしてよい範囲）が済んだ後に使う。

### 3.1 入力

- 検証の記録 `CHECKS_JSON`: 検証した HEAD と、実際に実行したコマンドと終了コードをそのまま書く。helper は HEAD・形式・成功を照合するだけで、ファイルを作れば検証したことになるわけではない

  ```json
  {"head": "<HEAD_SHA>", "commands": [{"argv": ["bash", ".devcontainer/run-tests.bash"], "exit_code": 0}]}
  ```

- 判断の記録 `ROUND_JSON`（`outcome: no_fix_needed`、[round-records.md](round-records.md)）と、マージの前の採否・検証の状況を書いた状況の本文 `STATUS_BODY`。マージ済み・Issue の更新済みと先に書かない

### 3.2 順序

**create-reso-world の PR**（Spec を PR の head に載せる）:

1. Spec を `completed` にして、`MAIN_ROOT` でローカルに commit する（S）。`git -C "$MAIN_ROOT" rev-parse HEAD^` が `HEAD_SHA` と同じで、`git -C "$MAIN_ROOT" diff --name-only HEAD^ HEAD` が Spec の 1 ファイルだけであることを確かめる
2. PR の head がまだ `HEAD_SHA` であることを確かめてから、記録付きで状況コメントを投稿する（[round-records.md](round-records.md) 6 章）。記録付きの投稿は、PR の head が `reviewed_head` と同じときだけ通る
3. S を SKILL.md の「実装後」の手順 5 の検査付きの push で、fast-forward で push する
4. `finalize.py` を `--spec-commit S` で実行する。helper は投稿しない。投稿済みの記録が渡した記録と同じこと、GitHub の比較で S が `reviewed_head` の直接の子の 1 commit で、変更が `docs/superpowers/specs/` の直下の Markdown 1 ファイルだけであること、PR の head が S であることを確かめてから、S を `--match-head-commit` でマージする

**usaturn/resoloop の PR**（Spec は create-reso-world の文書用ブランチに置く）: `finalize.py` を `--spec-commit` 無しで実行する。helper が状況を投稿し、CI の成功を確かめてからマージする。

```bash
uv run --project "$TOPLEVEL" --locked python \
  "$TOPLEVEL/.agents/skills/review-fix-planning/scripts/finalize.py" \
  --record-file "$ROUND_JSON" --body-file "$STATUS_BODY" --checks-file "$CHECKS_JSON" \
  --result-file "$SESSION/finalize-result.json" --spec-commit "$SPEC_COMMIT"
```

`--spec-commit` を使わないときは、その行を省く（空の文字列を渡さない）。

### 3.3 helper が確かめること

- マージしてよい範囲は `usaturn/create-reso-world` と `usaturn/resoloop` の、open で draft でない PR だけ。範囲外は GitHub に問い合わせる前に `permission:` で止まる（SKILL.md の「マージしてよい範囲」）
- CI: `usaturn/resoloop` は PR の checks が成功していること。`usaturn/create-reso-world` は確かめない（`AGENTS.md`「GitHub Actions」）
- 認証済みの login を取り、PR の全コメントの記録と照合する。マージは `--merge --match-head-commit`（squash・rebase は使わない）。admin・auto マージ、ブランチの削除はしない
- マージの後に MERGED・`mergedAt`・head を読み戻し、同じリポジトリの closing Issue だけを close して読み戻す
- 同じ head で既にマージ済みなら、このサイクルの自分の記録が渡した記録と同じときだけ、投稿もマージもせずに Issue の更新を続ける。記録が無い・食い違うまま手でマージされていれば、Issue を更新せずに `merged: true` の `stopped` を返す

### 3.4 結果

- 終了コード 0 で、結果の `outcome` が `no_fix_needed` のときだけ、最終化が終わった
- 終了コード 1 は `stopped`。`stop_reason`・`merged`・更新した `issues` を読む。`wait_for` があれば、待てば進む停止である。`ci`（公開の CI が実行中・待機中）は `gh pr checks <PR> --repo <repo> --watch` を `monitoring-long-tasks` で監視して待ち、`mergeable`（GitHub がマージの可否を計算中）は少し間を置いて、どちらも同じ記録・本文・検証の記録で再実行する。期限を決め、過ぎても解消しなければ結論 3 として報告する
- 状況の本文の不備・PR 上の過去の記録との食い違いは `environment:`、`gh`・API の失敗は `external:`、範囲外は `permission:` で返る
- マージの後の Issue の更新の失敗も `stopped` だが、マージ済みであることを隠さずに報告し、同じ head・同じ記録で再実行して復旧する
- 終了コード 2 は入力・結果ファイルの障害。操作の後の保存の失敗では、標準出力の JSON に実際の `merged`・`issues` が残るので、終了コード 2 だけから「何もしていない」と推測しない

## 4. 後片付け

- 成果を Spec と状況コメントに写した後に、自分のセッションディレクトリを `rm -rf -- "${SESSION:?}"` で消す。失敗・復旧に使う記録は残し、完全パスを報告する
- runner の worktree は、停止を確かめて成果を保存した後に、`.agents/monitoring-runtimes.md` の「agent-runner の同期実行と停止確認」のとおり登録を外す。停止を確かめられない worktree・変更が残る worktree は消さない
