# Issue #351: 停止確認済みの失敗レビューセッションの退役と、定期掃除の helper 検証

## 管理・実行許可

- 状態: draft（内容の承認は記録していない）
- 対象: https://github.com/usaturn/create-reso-world/issues/351（親ボード #349 の子 `review-retire`）
- 実行許可: 利用者の明示 `/issue-to-pr` と引数
  `#351 --implement claude-code_sonnet_default --merge --assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`。
- 許可の範囲: 通常の設計判断を推奨案で決めること、検証、commit、push、PR の作成、PR 修正ループ（`finalize.py`）によるマージまで。設計内容の承認ではない。
- 基準: usaturn/create-reso-world / origin / refs/heads/main / `690001b64ade22e91dfe54a9ad84a12c5d63931a`（#351 本文の「対象 branch: main」「PR の base は main」と一致）。
- 予約: `refs/heads/agent-claims/issue-351` = `c42d7afb74dd0e72254a782fdd1864a330f4e00d`（#351 の issuecomment-6724089439 に記録）。
- 着手前の確認: #351 に先行（`blocked_by`）・コメント・既存 PR・branch・worktree は無い。#350 は別セッションが予約中だが、所有ファイルは重ならない。

## 目的

停止を確認できた失敗レビューセッションを、未保存の成果を失わずに退役できるようにする。あわせて、定期掃除（`.devcontainer/cleanup-workspace.bash`）が `/tmp/pr-review-*` を helper の検証なしに `rm -rf` しないようにし、`repo-cleanup-after-merge` に失敗セッションの退役手順とゲート A の保護を足す。

## 現状（調査の結果）

- `pr_review_workspace.py cleanup` は「本文が保存済み」のセッションだけを消す。worktree の dirty・ignored を確かめずに `git worktree remove --force` する（`review_run.py complete` が保存の直後に呼ぶ前提）。保存しなかった失敗セッションを消す経路は、試行 ID を知る呼び出し元が使う `abandon`（`fail --abandon` を含む）だけである。
- 定期掃除は `/tmp/pr-review-*` を、使用中・年齢・git の clean だけで判定し、登録済み worktree を `git worktree remove --force` してから親ディレクトリを `rm -rf` する。`review-backup/` の未保存の draft・編集済みの候補・`previous-review.md` も消える。loose な `pr-review-*` ファイルも、同じ PR 番号のディレクトリが無く 1 日経てば消す。
- 定期掃除は `install_beforehand.bash` が `~/bin/cleanup-workspace.bash` へ**コピー**し、`zshrc.txt` が 24 時間ごとにそのコピーを実行する。コピーはリポジトリの外にあるので、AW（symlink で置く）のように自分の位置から helper を探す方法は、そのままでは使えない。
- 実行記録（`reviews/<owner>/<repo>/#<PR>-<branch>/runs/*.json`）は `review_run.py` が書き、`attach-runner` が runner の観測値（`runner.attempt.state`・`stop_confirmed` など）を結び付ける。`session.json` の `run_context` は記録の相対パス・開始時刻・reviewer・雛形の digest（`findings_scaffold`）を持つ。AW の実装（`0eea76aa` の `_validate_reapable_session`）は同じ形の情報を使っている。

## 範囲と除外

変更するファイルは #351 本文の「変更してよい」に限る。

- `.agents/skills/pr-review/scripts/pr_review_workspace.py`
- `.devcontainer/cleanup-workspace.bash`
- `.agents/skills/repo-cleanup-after-merge/SKILL.md`（手順 5・ゲート A と、手順に必要な `allowed-tools`）
- `.agents/skills/pr-review/references/noninteractive.md`
- `.agents/skills/pr-review/tests/test_pr_review_workspace.py`、`.devcontainer/test-cleanup-workspace.bash`

除外: AW の helper 全体の置き換え、`abandon`（`fail --abandon` を含む）の削除・改名、`refs/pr-review/<N>` の AW 形式、submodule worktree への `--force` の手順、`projects.toml`、review 保存形式・review-findings v2、`review-eval` の収集、`sessions` の判定の変更。`install_beforehand.bash`・`zshrc.txt`・`devcontainer.json` も変えない（所有外）。

## 設計

### 1. helper の退役 API

#### CLI

```text
pr_review_workspace.py reap-check --state <session.json> [--allow-failed] [--operator-confirmed-stopped REASON]
pr_review_workspace.py cleanup    --state <session.json> [--strict-reap] [--allow-failed] [--operator-confirmed-stopped REASON]
```

- `reap-check` は読むだけで、常に厳密な判定を行う。`--allow-failed` で失敗セッションの退役も判定する。
- `cleanup --strict-reap` は `reap-check` と同じ判定を、保存ロックの外で 1 回、保存ロックの中でもう 1 回行い、2 回目が通ったときだけ消す。
- `cleanup --allow-failed` は `--strict-reap` と一緒のときだけ受け付ける。`--operator-confirmed-stopped` は `--allow-failed` と一緒のときだけ受け付け、空白だけの理由を拒否する（どちらも終了コード 2、何も変えない）。
- `--strict-reap` の無い `cleanup` は今の挙動を変えない（`review_run.py complete` が保存の直後に呼ぶ経路）。返り値に `retirement: "saved"`・`stop_evidence: null`・`retained_paths: null` を足すだけにする。

#### 終了コードと出力

| 終了コード | 意味 | 出力 |
| --- | --- | --- |
| 0 | `reap-check`: 退役できる。`cleanup --strict-reap`: 退役した | stdout に 1 行の JSON。`status`（`eligible` / `retired`）、`retirement`（`saved` / `failed`）、`stop_evidence`、`session_dir`、`state_file`、`worktree`、`retained_paths: null`。`cleanup` は今の `destination`・`pr_ref`・`pr_ref_status` も返す |
| 1 | 状態は読めたが退役できない。何も変えない | stdout に 1 行の JSON。`status: "retained"`、`reason`、`retirement`（`saved` か `failed`。`--allow-failed` で失敗の判定に進んだものは、実行記録を結び付けられなくても `failed`。Task 4 のレビューの後に実装に合わせて変更）、`stop_confirmation_needed`（拒否の理由が停止の確認だけのとき true）、`retained_paths`（`state_file`・`session_dir`・`worktree`） |
| 2 | 引数の誤り、または状態を PR レビューのセッションとして読めない（`load_state` の失敗、version 6 以前を含む）。何も変えない | stderr に `error: ...`（今の形） |

`retained_paths` は review_run.py の慣習（失敗時に残したもの、成功時は null）に合わせる。

#### 分類

1. `load_state` で状態を読む（失敗は終了コード 2）。
2. 失敗の判定に進むのは `--allow-failed` があり、`run_context` を持ち、下の「saved の条件」を満たさないセッションだけ。saved の条件を満たすもの（`review_run.py complete` が保存した後に cleanup だけが失敗し、記録が `failed`（`failed_at: cleanup`）か `started` のまま残ったものを含む）は、実行記録にかかわらず `saved` として扱う。それ以外は `run_context` が指す実行記録を読み、`status` が `success` 以外（`started`・`failed`）なら `retirement: "failed"`、`success` なら `saved` として扱う（saved の条件を満たさないので拒否される）。`run_context` が無いセッション（version 7 と、`review_run.py` を使わない version 8）は `saved` として扱う。
3. 実行記録の結び付け（AW と同じ考え方を CRW の形に合わせる）: 記録のパスは `run_context.run_record` を、`state` の PR repository・PR 番号・head branch・model と `run_context.started_at`、セッションディレクトリ名の接尾辞から作った期待値と一致させる。`reviews/` の外・途中の symlink は拒否する。記録は `review_findings.validate_document` で検査し、`kind: review_run`、`pr`、`reviewed_head`（= `commit`）、`pr_head`、`reviewer`（`review_file` を除く）、`timing.started_at` がセッションと一致することを確かめる。結び付けられなければ退役しない（終了コード 1）。
4. runner が `success` で、記録がそれを `failed` で打ち消していない（記録が `started`）ものは、失敗セッションとして退役しない（成功した run の成果を失わないため）。

#### 共通の検査（saved・failed とも）

- セッションディレクトリが `pr-review-<PR番号>-<8 文字>` の名前で、`session.json` が通常ファイルで、途中に symlink が無い。
- 直下の項目は `session.json`・`review-backup/`・`worktree/`、あれば `create-journal.jsonl`、owned-history なら `repo/` だけ（`.session.json.*` などの書きかけを含め、それ以外があれば退役しない）。
- `create-journal.jsonl` があれば、作成の処理が終わっている（journal のロックを取れる）。`cleanup --strict-reap` は消し終わるまでそのロックを保持する。owned-history は既存の `owned_attempt_repository` で、所有 Git であることと、ほかの worktree を持たないことを確かめる。
- worktree は登録済みで lock されておらず、その対象 Git の linked worktree で、detached・HEAD が `commit`。`git status --porcelain --untracked-files=all` が空、skip-worktree・assume-unchanged の項目が無い、submodule にも変更・未追跡・ignored が無い。ignored のファイルは、repo-cleanup-after-merge の手順 4 と同じ再生成できるキャッシュ（`.venv/`・`.uv-cache/`・`.pytest_cache/`・`.ruff_cache/`・`__pycache__/`・`node_modules/`）だけを許す。

#### saved の条件

- 本文の draft があり、保存先（`destination`）に同じ内容がある（既存の `require_saved_review`）。`saved_findings` なら候補も同じく保存済み（既存の `require_saved_findings`）。
- `review-backup/` には本文の draft、候補の draft（保存しなかった場合も含む。AW と同じ）、`state.previous_review` がある場合の `previous-review.md` だけがある。`previous-review.md` は `destination_fingerprint` の sha256 と一致する。

#### failed の条件

- `previous_review` が null で、`review-backup/` に `previous-review.md` が無い（あれば全体を保持する）。
- `review-backup/` は空か、`run_context.findings_scaffold` の名前と sha256 が一致する雛形だけ。本文の draft があれば、内容にかかわらず保持する。雛形の digest が記録されていなければ、雛形のファイルも未知として保持する。
- 停止の証拠: `--operator-confirmed-stopped` の理由があれば `{"source": "operator", "reason": ...}`。無ければ記録の `runner` が `stop_confirmed: true` で、`attempt.state` が `self` 以外であること（`{"source": "runner", "run_record_status": ..., "state": ..., "exit_code": ..., "elapsed_seconds": ..., "stop_confirmed": true}`）。停止の確認はほかの検査がすべて通った後に行い、これだけで拒否したときに `stop_confirmation_needed: true` を返す。利用者の理由が補うのは停止の確認だけで、成果・未知のファイル・Git の検査は迂回しない。

#### 退役の操作（`cleanup --strict-reap`）

保存ロック（version 7 は `main_root`、version 8 は `parent_root` の共通 Git ディレクトリのロック。既存の `cleanup`・`save`・`abandon` と同じ）を取り、判定をやり直してから、既存の `cleanup` と同じ順に行う。version 8 は固定した PR の ref を `pr_head` と一致するときだけ消し、`git worktree remove --force <worktree>`（検査で clean を確かめた後だけ）、worktree が消えたことを確かめてからセッションディレクトリを消す。実行記録・保存済みの本文と候補は消さない。

### 2. 定期掃除

- `/tmp/pr-review-*` のディレクトリは、symlink・使用中・`MIN_AGE_DAYS` 未満を今までどおり除いた後、`python3 "$PR_REVIEW_HELPER" reap-check --allow-failed --state "$dir/session.json"` を実行する。終了コード 0 のときだけ、`cleanup --strict-reap --allow-failed` を実行する。スクリプト自身は pr-review のディレクトリを `rm -rf` も `git worktree remove` もしない。`--operator-confirmed-stopped` は使わない（人の確認の代わりにしない）。
- helper の場所は、環境変数 `WORKSPACE_CLEANUP_PR_REVIEW_HELPER`、無ければスクリプトの実体の 1 つ上のディレクトリの `.agents/skills/pr-review/scripts/pr_review_workspace.py`。通常ファイルとして見つからなければ、pr-review のディレクトリをすべて保持し、理由とパスを報告する（`~/bin` のコピーから動く定期実行はこれに当たる。下の「既知の制約」）。`python3` を使うのは、`.devcontainer/` のブートストラップの例外（AGENTS.md）による。helper は標準ライブラリだけで動く。
- 報告: 退役したものは `retired pr-review session: <dir>: <helper の JSON>`、保持したものは `keep (...): <dir>: <helper の出力>`、dry-run は `dry-run: would retire pr-review session: <dir>: <reap-check の JSON>`。最後に `pr-review cleanup: retired=<数> kept=<数>`。
- loose な `pr-review-*` ファイルは出所と内容を確かめられないので削除せず、`protected loose pr-review file (unverifiable provenance): <path>` と件数を報告する（AW と同じ）。
- `review-fix-planning.*` の掃除は変えない。

### 3. repo-cleanup-after-merge

- 手順 5 の最初に「pr-review のセッションは helper で退役させる」を置く。対象は今までどおり、手順 1 の `sessions` が `removable: true` を返し、手順 1 のオープン PR の対象外にも当たらない `/tmp/pr-review-*` のセッション（version 7・8 とも）。`reap-check --allow-failed` → `cleanup --strict-reap --allow-failed` を実行し、成功したものは worktree・残骸・自セッションの ref の処理が済んだので、通常の worktree 削除とゲート A に回さない。
- helper が拒否したセッションは worktree ごと保持し、`reason` を手順 11 で報告する。`run_context` を持つセッションと version 8 は、通常の worktree 削除・ゲート A に迂回しない（今の version 8 の保持規則を保つ）。`run_context` の無い version 7 だけは、今までの経路（手順 4 の clean の確認、`git worktree remove`、ゲート A の照合）を使える（version 7 の削除経路を壊さない）。
- 拒否の理由が停止の確認だけ（`stop_confirmation_needed: true`）のときに限り、担当のプロセスと子孫の停止を実際に確かめた人がその内容を理由として `--operator-confirmed-stopped` を付けて実行できる。年齢・PID が無いこと・モデルの `fail` は確認の代わりにならず、エージェントが理由を作らない。
- ゲート A に「helper が拒否したセッションと `run_context` を持つセッションは、worktree が無くても対象にしない。worktree を外してからゲート A で消す迂回をしない。停止未確認の失敗セッションを即時に消さない」を足す。version 7 の照合の規則・`sessions` の読み取り専用の報告は変えない。
- `allowed-tools` に `reap-check` と `cleanup` の helper 呼び出し（`uv run --no-project python *pr_review_workspace.py reap-check *`・`... cleanup *`）を足す。手順のコマンドは今の `sessions` と同じく `uv run --no-project python` で書く。

### 4. noninteractive.md

「実行記録」の後に、定期掃除と repo-cleanup-after-merge が同じ `reap-check`／`cleanup --strict-reap --allow-failed` を使うこと、失敗セッションの停止の証拠は `attach-runner` が実行記録に書いた `stop_confirmed` であること（`attach-runner` を省いた失敗セッションは保持される）を書く。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
| --- | --- | --- | --- | --- |
| 実装の土台 | AW の `_validate_reapable_session` の考え方を、CRW の version 7/8・journal・owned-history・`findings_scaffold` に合わせて足す | AW の helper の置き換え | Issue が置き換えを禁じている。CRW の `inspect`・`abandon`・`sessions` を残す | 通常判断の委任 |
| 失敗の分類の根拠 | `run_context` が指す実行記録の `status` と `runner` | session の中のファイルの有無だけで判定 | 停止の証拠は runner の観測値にしか無い。記録はセッションの値と照合して取り違えを防ぐ | 結び付けられなければ保持 |
| 失敗セッションの雛形の判定 | `run_context.findings_scaffold` の sha256 と一致 | AW のように immutable から雛形を作り直して比べる | CRW は prepare が digest を記録しており（`abandon` と同じ基準）、1 バイトの編集も成果として残せる | digest が無ければ保持 |
| 保存済みの判定と失敗の判定の順序（Task 2 のレビューで変更） | `--allow-failed` でも、saved の条件を満たせば記録にかかわらず `saved` | 記録の `status` だけで分類する（当初の文言） | `complete` は保存の後に cleanup が失敗すると記録を `failed`（`cleanup`）にするので、当初の文言では、`--allow-failed` を必ず付ける定期掃除と repo-cleanup が保存済みのセッションを退役できない。受け入れ基準の A1・A6 を基準に直す | 保存済みなら停止の証拠を求めない（`--allow-failed` 無しの saved と同じ） |
| 停止の確認の順序 | ほかの検査の後に最後に行い、`stop_confirmation_needed` を返す | AW のように最初に確かめる | 「停止未確認だけが理由」のときだけ人の確認で補う、という手順を helper の出力で判断できる | 利用者の理由は停止の確認だけを補う |
| 終了コード | 0 退役可・1 退役不可・2 入力/状態の誤り | AW のようにすべて 2 | Issue のインターフェースの指定 | なし |
| `retained_paths` | 成功は null、拒否は `state_file`・`session_dir`・`worktree` | 成功時に残る成果のパスを入れる | review_run.py の既存の慣習に合わせる | なし |
| ignored のファイル | repo-cleanup の手順 4 と同じキャッシュ名だけ許す | AW のようにすべて拒否 | テストを実行したレビューの worktree が定期掃除で永久に残るのを避ける。手順 4 と基準を揃える | ほかの ignored があれば保持 |
| worktree が無い失敗セッション | 退役しない（保持） | AW の `allow_missing_worktree` を移植 | `load_state` の厳密な検査を緩めずに済む。Issue の受け入れに含まれない | 持ち越しに記録 |
| 定期掃除の helper の場所 | 環境変数 → スクリプトの実体からの相対。無ければ pr-review をすべて保持 | `session.json` の `parent_root` から helper を選ぶ／`/workspaces/*` を探す | データやディレクトリ名の推測で実行するコードを選ばない。見つからなければ安全側に倒す | `~/bin` のコピーは保持だけになる（既知の制約） |
| 定期掃除の Python | `python3`（ブートストラップの例外） | `uv run --no-project python` | `install_beforehand.bash` が uv の導入前に呼ぶことがある。helper は標準ライブラリだけ | なし |
| loose ファイル | 削除せず保護として報告 | 年齢と同じ PR のディレクトリの有無で消す（現状） | 出所を確かめられず、未保存の成果のことがある | なし |
| repo-cleanup の対象 | `sessions` の `removable: true` を条件に保ち、helper の判定を先に行う | 失敗セッションは PR の状態にかかわらず退役 | Issue が version 7/8 の保持規則と `sessions` の報告の維持を求めている | なし |
| handoff の対と復元 manifest | 作らない | planning だけのセッションと同じく作る | この run は同じセッションで実装・PR まで進み、Spec・Plan は PR のコミットで公開・復元できる | なし |
| 実行方式 | runner の担当（`claude-code_sonnet_default`）に Task を 1 つずつ依頼 | self で実装 | `implement_task.py check` の `self: false`（`--implement` の利用者の指定） | 担当が失敗しても self に切り替えない |
| ループの割り当て | inspect=`pi_openai-codex_gpt6-sol_max`、fix implement=`claude-code_sonnet_default`（利用者の指定）。サイクルの上限 3、fix の self-review・fix-check は self、fallback なし（既定の適用） | 既定のレビュアー | 利用者の指定をそのまま使う | `check-options` は終了コード 0 |

## 受け入れ基準

| # | 条件 | 確かめ方 |
| --- | --- | --- |
| A1 | 保存済みセッションは従来どおり退役できる（`cleanup` も `cleanup --strict-reap` も） | 既存の cleanup のテストと、新しい saved の退役のテスト |
| A2 | 停止確認済みの失敗セッションは `reap-check --allow-failed` → `cleanup --strict-reap --allow-failed` で退役し、実行記録は残る | 新しいテスト（prepare → fail → attach-runner の stop_confirmed） |
| A3 | 停止未確認の失敗セッションは、理由が無ければ退役しない（終了コード 1、`stop_confirmation_needed: true`）。理由があれば退役する | 新しいテスト |
| A4 | 本文の draft・`previous-review.md`・編集した候補・未知のファイルがある失敗セッションは、`--allow-failed` と理由があっても保持する | 新しいテスト |
| A5 | `--strict-reap` は保存ロックの中で判定し直す（判定の後に足されたファイルを消さない） | 新しいテスト |
| A6 | 定期掃除は helper が拒否したセッション（`session.json` が無いものを含む）を消さず、理由とパスを報告する。保存済みのセッションは退役させる | `test-cleanup-workspace.bash` |
| A7 | version 8 のセッションと `sessions` の `removable` の判定、`inspect`・`abandon`・`fail --abandon` を壊さない | 既存のテストが通る |
| A8 | version 7 の削除経路を壊さない | 既存のテストと A1 |

## 既知の制約と持ち越し

- `~/bin/cleanup-workspace.bash`（コピー）から動く 24 時間ごとの定期掃除は helper を見つけられないので、pr-review のセッションを保持して報告するだけになる。退役は、リポジトリの `.devcontainer/cleanup-workspace.bash` の実行（コンテナ作成時の `install_beforehand.bash` と手動）と repo-cleanup-after-merge の手順 5 で行う。コピーから helper を使えるようにするには `install_beforehand.bash`（symlink にする、または helper のパスを渡す）の変更が要り、#351 の所有外なので、親 #349 で所有の移動として提案する。
- worktree が無い失敗セッション（AW の `allow_missing_worktree`）は扱わない。
- version 7 の `cleanup` が固定した ref を持たない既存の挙動は変えない（#354 `repo-cleanup` の範囲）。
