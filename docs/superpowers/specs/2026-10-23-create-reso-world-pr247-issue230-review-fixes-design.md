# PR #247（Issue #230）のレビュー修正: サイクル 1〜2

## 管理

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/247（`feat/issue-230-agent-runner-tests`、base `main`）。閉じる Issue: #230
- 状態: completed
- 実装の Spec・Plan: `docs/superpowers/specs/2026-10-23-create-reso-world-issue230-agent-runner-tests-design.md`・`docs/superpowers/plans/2026-10-23-create-reso-world-issue230-agent-runner-tests.md`（どちらも draft）
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/230 --merge --assign implement=self …`。issue-to-pr の `--merge` により、PR の作成後に PR 修正ループ（pr-review-fix-loop、run `59424bd17e124ff1b1cda99a67f44715`）を回し、各サイクルの計画は review-fix-planning の完遂の依頼として扱う（結論 2 では `finalize.py` がマージと関連 Issue の更新を行う）。内容の承認（approved）ではない
- planner: claude-opus-5-5（claude-code）。サイクルの番号: 1（PR の判断の記録は空だった）
- DOC_ROOT・CODE_ROOT（専用の worktree）: `/workspaces/reso-world/.worktrees/issue-230-agent-runner-tests`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD は PR の head `c899bd4` と一致したので再利用した。片付けの対象にしない）
- 修正と自己レビューの担当（ループの `planning.run_roles_options` は `--template /workspaces/reso-world/.devcontainer/agent-runner.toml --assign implement=self`）: `implement` は `self`（利用者の指定）、`self-review`・`fix-check` は `self`（雛形の既定）。自己レビューは `run_roles.py --phase self-review` の 1 回
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#247-feat-issue-230-agent-runner-tests/verified/c899bd42fd88.json`（親の main checkout の下）。工程の記録: 同じ場所の `c899bd42fd88.planning.json`

## レビュアーの構成

ループの `review` が agent-runner の workflow `review` の role `inspect` で 4 人を並行に起動した。4 人とも 1 回目で受け付けられた（`rejected`・`retained` なし）。

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | pi-gpt | `c899bd42fd88` | はい | Needs manual verification |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `c899bd42fd88` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `c899bd42fd88` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 256K Extra High | cursor | cursor-grok47 | `c899bd42fd88` | はい | Approve |

## 指摘の一覧と振り分け

指摘は 3 件（Medium 2・Info 1）。確認済みの一覧（review-verify、mode cycle）が 3 件とも `confirmed` とした（`not_reproduced`・`unverified` は 0）。

| 判断 | 元の指摘 | 確認済み | 分類 | 根拠 |
| --- | --- | --- | --- | --- |
| F-1 | `gpt-6.1-sol#M-1@c899bd42fd88` | V-1 | 対応する | DSH の中断（turn_end の reason.kind が aborted）を interrupted にする `dsh.py:161-162` の最後の代表 `test_abort_maps_to_interrupted` を 4c4a964 が消した。戻り値を response_failed・awaiting_authentication にする変異、条件を False にする変異で、残したテストは全て通り、中断の後に fallback の担当が起動して batch が success になる。致命的: DSH は雛形の担当（`dsh-ccd`・`dsh-go`）にある runtime で、DSH 自身が turn を中断したときに、この分類の回帰が検出されずに別の担当が起動し、成功として報告される（危険な操作が進む・失敗を成功と報告する）。#228・#230 の利用者の決定（S は消さない）にも反する。(c) 誤った理由で削除された回帰ガード |
| F-2 | `gpt-6.1-sol#M-2@c899bd42fd88` | V-2 | 対応する | payload_check が False を返したときに invalid_result にする `runner.py:290` の `is True` の最後の代表 `[returns-false]` を消した。`is not None` にする変異で、拒否した payload を success として返し、残したテストは全て通る。致命的: 利用側の `implement_task.py:203-209` は検証の失敗で False を返すので、回帰すると検証に通らない実装の結果を成功として取り込む（失敗を成功と報告する）。(c) |
| S-1 | `SWE-2-Max#I-1@c899bd42fd88` | V-3 | 対応しない | claude_code・pi の `test_adapter.py` に、消した pytestmark（`outside_runner`）を説明するコメントが残る。事実として正しいが、2 ファイルのテストは run_workflow を呼ばず（`AGENT_RUNNER_DEPTH` に左右されない）、レビュアーは `AGENT_RUNNER_DEPTH=1` の中で 365 件を通した。コメントだけの問題で致命的ではない |

- 確認中に PR が持ち込んだ欠陥で、上の 2 件と原因の違うものは見つからなかった。上の 2 件と同じ原因に頼る経路で見つけたものは、「守る条件と影響経路」の「修正する」の行にした（自己確認の指摘としては分けない）
- 設計の見直しのきっかけ: なし（以前のレビュー修正が無い）
- PR の説明の既知の制限: 書き足すものは無い（「対応しない」の S-1 は保証と食い違わない）

## 守る条件と影響経路

原因は 3 つあった（3 つ目は修正後の自己レビューで見つけた）。

- **原因 1（F-1）:** 初回の監査は中断の分類の変異 m01127・m00954・m01223・m01224 を lost として見つけたが、判定で「失敗の種類だけが変わる」として L にした（根拠に挙げた PR #170 の既知の制限は、応答の前のログで診断が上書きされる場合だけの話だった）。失敗の種類が `runner.py:604` の fallback の続行・停止を決める場合（停止の状態の interrupted が続行の状態になる場合）を、判定の前提が見落とした
- **原因 2（F-2）:** 監査の演算子（条件・複合条件の項・文・一覧の要素・定数）に値の緩和が無く、`is True` を緩める変異を作らなかった。厳密な判定だけを検出するテストが lost として現れず、理由の文で D にした

**守る条件 1:** 担当が報告した中断（interrupted）は fallback を始めない状態のまま保たれ、それを壊す変更を残したテストが検出する。
**守る条件 2:** 呼び出し側の検査・中間イベントの形の厳密な判定（`True` だけを受け入れる）を緩める変更を、残したテストが検出する。
**守る条件 3（修正後の自己レビューで見つけた形）:** 消した D のテストが守る受け渡し（停止の event などの引数）を、別の層の代表ではなく、その受け渡しを通るテストが検出する。

- **原因 3（自己レビューの L-2）:** D の代表を、理由の文で別の層（`process.execute` に取り消し済みの event を直接渡すテスト）に決め、消したテストが通る受け渡し（`hooks.run_after_run` → `execute` の `cancel`）を代表が通らなかった。キーワード引数の値の差し替えは、どの演算子にも無かった

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 1 | `dsh.py:161-162`（aborted → interrupted） | 修正する | 戻した `test_abort_maps_to_interrupted` が 3 種の変異で失敗し、変異なしで通る | 修正の commit の写しに変異を当てて実行 | `f43d192` の写しで 3 種とも失敗、変異なしで通過（`audit/c1/repro/logs/fixcheck.jsonl`） |
| 1 | `dsh.py:369-372`・`dsh_identity.py:57-58`（v4 のログが無いときは分類を置き換えない。m01951・m01901 は中断も response_failed にする） | 修正する | 戻した `test_missing_identity_preserves_known_failure[MISSING_CREDENTIAL-awaiting_authentication]` が m01951・m01901 で失敗する | 同上。中断の流れは、使い捨てのテスト（aborted の stream・ログ無し）を変異の写しで実行 | `f43d192` の写しで 2 個とも失敗。使い捨てのテストは変異で interrupted でなくなる（`c899bd4` の写し）。縮めた木の全体は 2 個とも検出しない（`/tmp` 以外の basetemp による既知の 1 件の失敗を除く） |
| 1 | `runner.py:557`（保持物があるときは success だけを response_failed にする。m03231 は中断も置き換える） | 修正する（迷い） | 戻した `test_nonregular_receipt_is_rejected_before_adapter_reads_it` が m03231 で失敗する | 同上 | `f43d192` の写しで失敗。縮めた木の全体（364 件）は検出しない。中断と保持物の組み合わせはコードを読んだ判断で、実行していない |
| 1 | `runner.py:553-556`（runner 自身の取り消し・期限） | 既に満たす | 残したテストが検出する | 初回の監査の記録 | m02996・m02997・m03074・m03170 を `test_role_deadline_covers_fallback_attempts[4.0]` が検出（本走査と縮めた木） |
| 1 | `runner.py:604`（fallback を止める集合） | 対象外 | — | — | 集合から interrupted を外す m03253 と `runner.py:555` の m03117・m03172・m03173 は基準のテストも検出しない（この PR が失わせた守りではない。#236 への申し送り） |
| 1 | ほかの adapter の中断の分類（claude_code・pi・codex・cursor・devin）と「失敗の種類」の L の判定 | 既に満たす | 状態の差し替え（interrupted・timed_out → response_failed）を残したテストが検出する、または基準も検出しない | 値の変異の 2 段の走査。L の判定の理由を全て読み直す | 差し替えの 4 個のうち lost は `dsh.py:162`（上の行）と `process.py:400`（L: runner の取り消しの確認で interrupted のまま）だけ。ほかの「失敗の種類」の L は、どちらの状態でも fallback を続けるか、runner の取り消し・期限で同じ状態に終わる |
| 2 | `runner.py:290`（payload_check の `is True`） | 修正する | 戻した `[returns-false]` が `is not None` の変異で失敗し、変異なしで通る | 修正の commit の写しに変異を当てて実行 | `f43d192` の写しで失敗（`[raises]` は通る）、変異なしで通過 |
| 2 | `dsh.py:140`（input も truncated も無い tool_call を受け付けない。v0070） | 修正する（迷い） | 戻した tool_call のケースが v0070 で失敗する | 同上 | `f43d192` の写しで失敗 |
| 3（自己レビューの L-2） | `hooks.py:49-56`（後処理に run の cancel を渡す。SIGINT で中断した run では後処理を起動しない） | 修正する | 戻した `test_after_run_is_not_started_after_an_interrupted_run` が cancel を新しい event にする変異（k0024）で失敗し、変異なしで通る | 修正の commit の写しに変異を当てて実行 | `48d7dc4` の写しで失敗、変異なしで通過。`c899bd4`・`f43d192` の全体は検出しない（自己レビューの再現） |
| 3 | 停止の event・期限・環境・cwd・伏せ字・パスの安全を運ぶほかのキーワード引数（`cancel`・`deadline_seconds`・`timeout`・`env`・`cwd`・`dir_fd`・`secrets`・`preserve`・`required_paths`・`follow_symlinks`・`strict`・`check`・`stop_confirmed`） | 既に満たす／対象外 | 消すテストが覆う 57 個のうち、縮めた木が検出しない変異を基準の木が検出するか | `bin/gen_kwarg_ops.py` の 58 個（覆う 57 個）を、縮めた木（`f43d192` の木）と基準の木で流す | 縮めた木 39 個を検出。基準だけが検出した 2 個は k0024（上の行）と k0023（`hooks.py:49` の期限を 1e9。止まらない後処理で CLI が戻らず目に見える。L）。16 個は基準も検出しない（対象外、#236 への申し送り: `hooks.py:49` の `secrets=()`、`runner.py:126` の `follow_symlinks=True`、`cli.py:144` の cancel など） |
| 2 | 守りのコードのほかの `True`・`False`・`None` との比較と、返す・代入する状態 | 既に満たす／対象外 | 消すテストが覆う 191 個のうち、縮めた木が検出しない変異を基準の木が検出するか | `bin/gen_value_ops.py` の 219 個（覆う 191 個）を縮めた木と基準の木で流す | 縮めた木 39 個を検出。基準の木だけが検出した 15 個は、上の 3 行の守り 3 個と L の 12 個（runner の形の確認で invalid_result、runner の取り消しの確認、CLI の表示、届かない空の環境）。137 個は基準も検出しない（対象外、#236 への申し送り） |

## 修正方針

- base `7a8e4b7` のテストの本文をそのまま戻す（実装の Spec の D-230-8: 残す S のテストの中身を変えない）。戻したのは 6 件（`f43d192` で 5 件、自己レビューの後の `48d7dc4` で `test_after_run_is_not_started_after_an_interrupted_run`）で、370 → 371 件・7,171 行（34.9%・68.9%）になった。パラメータは検出する代表だけにする（`test_missing_identity_preserves_known_failure` は MISSING_CREDENTIAL、`test_invalid_intermediate_event_is_not_ignored` は tool_call のケースを足す）。消していた `FifoAdapter` と `LaunchSpec` の import を戻す
- 新しいテストは書かない（#228 の決定 6、`AGENTS.md`「テストの採用基準」）。基準も検出しない守り（`runner.py:604` など）は #236 に申し送る
- 実装の Spec の棚卸しの表・計測・決定記録（D-230-14）・監査（「サイクル 1 のレビューを受けた確認」）・迷いの一覧・申し送りを直す
- 検討した別案: (a) 指摘の 2 件だけを戻す — 同じ原因に頼る経路が残り、次のサイクルで同じ形の指摘が続く（#232・#235 の経緯）ので採らない。(b) 値の緩和を全ての演算子に広げる（`==` の反転など） — 予算を超え、既存の演算子（条件を False にする）と重なる部分が多いので、指摘の 2 つの形（比較の緩和・状態の差し替え）に絞った

## 実行した検証と結果

| コマンド・確認 | 対象 | 結果 |
| --- | --- | --- |
| 戻した 5 件（9 ケース）の実行 | 専用の worktree（`f43d192` の commit の前の作業ツリー） | 9 件通過 |
| 変異の検出（`audit/c1/repro/run_fixcheck.sh`） | `f43d192` の写し（`git archive`）、PID 名前空間 | 変異なし: 9 件通過。8 個の変異（V-1 の 3 種、m01951・m01901、m03231、`is not None`、v0070）で、戻したテストがそれぞれ失敗 |
| `uv run --locked pytest -p no:cacheprovider -q tools/agent_runner`（`--basetemp` は `/tmp` の mktemp） | `f43d192`・`48d7dc4`（どちらも clean） | 370 件通過（34.58 秒）・371 件通過（36.78 秒）、どちらも終了コード 0 |
| `bash .devcontainer/run-tests.bash` | `f43d192`・`48d7dc4` | どちらも PASS: 23 test(s)、終了コード 0 |
| `bash scripts/check-layout.sh` | `f43d192`・`48d7dc4` | どちらも PASS: check-layout、終了コード 0 |
| 計測（`pytest --collect-only`・`git ls-files … \| xargs cat \| wc -l`） | `48d7dc4` | 371 件・7,171 行・29 ファイル（34.9%・68.9%）。`f43d192` は 370 件・7,158 行 |
| push の前の秘密情報の検査（`scripts/scan-before-push.sh --base origin/main`） | `f43d192`（自己レビューの前、push しない）と push する Spec の commit | `f43d192` は no leaks found（8 commits）、終了コード 0。push の前にもう一度検査する（結果は状況コメント） |
| 戻した後処理のテストの変異の検出 | `48d7dc4` の写し、PID 名前空間 | 変異なし: 通過。k0024（`hooks.py:49` の cancel を新しい event）で失敗 |

## 自己レビュー

`run_roles.py --phase self-review` の 1 回（`/workspaces/reso-world/tmp/agents/review-fix-planning-pr247.ja_lu9tk/self-review-run`。工程の記録に `pre_push_review` の枠を 1 件予約）。割り当ては self-review・fix-check とも `self` で、司令塔が 2 つのサブエージェント（claude-opus-5-5、Claude Code）に同時に任せた（1 回と数える）。対象は `f43d192`（push していない修正の commit）。

- self-review（観点 2: PR 全体）: `reviews/…/claude-opus-5-5-commit-f43d1928b233910e9b48276894fbec04190214fb.md`。Critical・High 0、Low 2・Info 1・未検証の候補 1、Merge recommendation は Needs manual verification
- fix-check（観点 1: 反証、観点 3: 検証の検出力）: `reviews/…/verified/f43d1928b233.fix-check.json`（と `.statement-candidates.json`・`.fix-check.md`）。新しい指摘 4 件（confirmed）、主張 20 件のうち holds 16・violates 2（C-5・C-14）・unchecked 2（C-8・C-11）、変更ファイル 4 件は passed。未確認の事項 (1)（保持物のある中断が fallback を始める）は、fix-check が実行で確かめた（m03231 で `a:response_failed → b:success`）

| 指摘 | 分類 | 判断と根拠 |
| --- | --- | --- |
| self-review L-1（棚卸しの表の理由が「…」で切れる） | 対応しない | 分類・理由・扱いは全ての行にあり、受け入れ条件は満たす。切れた理由の全文は監査の記録（`audit/final-inventory.json`）にある。誤った結果・データの消失は起きない |
| self-review L-2（中断した run で後処理を起動しない守りの代表が hooks を通らない） | 対応する | 守る条件 3。`48d7dc4` で戻した。致命的: 回帰すると、SIGINT（利用者の停止）の後にも後処理（雛形の review の finalize-parent・attach-runner）が起動し、2 回目の Ctrl-C も後処理を止めない（interfaces.rst「後処理」の保証が黙って破れる）。#228・#230 の決定（S は消さない）にも反する。(c) |
| self-review I-1（参照するレビュー修正の Spec が commit に無い） | 解消済み | この Spec の commit に含めて push する |
| self-review U-1（代表が別のファイルにある D のほかの 63 行） | 対応しない | 疑いだけで再現が無い。初回の監査（条件・文・一覧の要素・定数）、値の変異 191 個、受け渡しの引数の差し替え 57 個で、消したテストだけが検出する変異は上の守りのほかに無かった。ほかの形の変異は未確認（実装の Spec の申し送り） |
| fix-check V-1（申し送りの行数が 68.5% のまま） | 対応する | (b) Spec の件数が実装と食い違う。`48d7dc4` で直した（68.9%） |
| fix-check V-2（レビュー修正の Spec が commit に無い） | 解消済み | self-review の I-1 と同じ。この Spec の commit に含める |
| fix-check V-3（lost の判定の表が L のまま、m01167 の扱いが v0070 と食い違う） | 対応する | (b) #236 がこの表で一覧を作ると、戻した S のテストを L として再び消す判断になる。`48d7dc4` で 4 行を S・迷いに改め、集計に注記した |
| fix-check V-4（FIFO のテストは中断だけの置き換えを検出しない） | 対応しない | 基準からある守りの穴（中断だけを置き換える変更は基準の全体も検出しない）。この PR は新しいテストを書かない（#228 の決定 6）。Spec の過大な記述は V-3 と同じ修正で直し、穴は #236 に申し送った |

- 自己レビューの後の修正（`48d7dc4`: L-2 のテストを戻し、V-1・V-3・V-4 の記述を直した）は再レビューしていない（自己レビューは 1 回まで）。修正の後に関連テスト・`run-tests.bash`・`check-layout.sh` と、戻したテストの変異の検出を確かめた
- fix-check の C-8・C-11（値の変異の 2 段の走査と、ほかの adapter の L の判定の読み直し）は、fix-check が走査を再実行していないので未確認のまま（記録は `audit/c1/res/`）

## 結論

結論 1（修正して push）。修正の commit は `f43d192`・`48d7dc4`。この Spec を `completed` で commit し、`scripts/scan-before-push.sh` の検査を通した commit を既存の PR の head に push する。PR の本文の件数（371 件・7,171 行）とレビュー修正の節も更新する。

## サイクル 2

- 対象 HEAD: `7867cf563f83d5b1a675a3edd44f8da219a40566`（サイクル 1 で push した commit）。サイクルの番号: 2（PR の判断の記録の round 1 の次）
- planner: claude-opus-5-5（claude-code）。修正と自己レビューの担当は使っていない（修正が無い）
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#247-feat-issue-230-agent-runner-tests/verified/7867cf563f83.json`。工程の記録: 同じ場所の `7867cf563f83.planning.json`

### レビュアーの構成（サイクル 2）

ループの `review` が 4 人を並行に起動し、4 人とも 1 回目で受け付けられた（`rejected`・`retained` なし）。

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | pi-gpt | `7867cf563f83` | はい（Update） | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `7867cf563f83` | はい（Update） | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `7867cf563f83` | はい（Update） | Approve |
| `Grok-4.7.md` | Grok 4.7 256K Extra High | cursor | cursor-grok47 | `7867cf563f83` | はい（Update） | Approve |
| `claude-opus-5-5-commit-f43d1928b233910e9b48276894fbec04190214fb.md` | claude-opus-5-5 | claude-code | self（サイクル 1 の自己レビュー） | `f43d1928b233` | いいえ（古い） | Needs manual verification |

### 指摘の一覧と振り分け（サイクル 2）

| 判断 | 元の指摘 | 確認済み | 分類 | 根拠 |
| --- | --- | --- | --- | --- |
| サイクル 1 の F-1 | `gpt-6.1-sol#M-1@c899bd42fd88` | — | 解消済み | `7867cf5` の `test_abort_maps_to_interrupted` が分類の変異 3 種で失敗する（サイクル 1 の `f43d192` の写しでの記録。テストは同一）。サイクル 2 の deepseek も HEAD の写しで確かめた |
| サイクル 1 の F-2 | `gpt-6.1-sol#M-2@c899bd42fd88` | — | 解消済み | `[returns-false]` が `is not None` の変異で失敗する（同上） |
| サイクル 1 の自己レビューの L-2 | `claude-opus-5-5-commit-f43d1928…#L-2@f43d1928b233` | V-3（not_reproduced） | 解消済み | `48d7dc4` で戻したテストが k0024 で失敗する。`git diff 48d7dc4 7867cf5 -- tools/` は空 |
| サイクル 1 の fix-check の V-1・V-3 | `fix-check#V-1@f43d1928b233`・`fix-check#V-3@f43d1928b233` | — | 解消済み | 実装の Spec の 275 行は 68.9%、lost の判定の表の 4 行は S・迷い（`7867cf5` を git show で確かめた） |
| S-2 | `deepseek-deepseek-v4.1-flash#I-1@7867cf563f83` | V-1 | 対応しない | 棚卸しの表の 4 行が、行数を超える行番号（`skills.py:288-292`、`adapters/__init__.py:178-211` など）を挙げる。事実として正しいが、読む人は該当の行が無いことにすぐ気付き、誤った結果・データの消失は起きない。致命的でない |

- サイクル 1 で「対応しない」とした判断（SWE-2-Max の I-1、自己レビューの L-1・U-1、fix-check の V-4）は、新しい根拠が無いので引き継ぐ（確認済みの一覧の V-2・V-5 は同じ内容）
- 「対応する」は 0 件。設計の見直しのきっかけ: なし

### 検証と結論（サイクル 2）

| コマンド | 対象 | 結果 |
| --- | --- | --- |
| `uv run --locked pytest -p no:cacheprovider -q tools/agent_runner --basetemp /tmp/issue-230-c2-pytest.QO62Pa/bt` | `7867cf5`（専用の worktree、clean） | 371 件通過、終了コード 0 |
| `bash .devcontainer/run-tests.bash` | `7867cf5` | PASS: 23 test(s)、終了コード 0 |
| `bash scripts/check-layout.sh` | `7867cf5` | PASS: check-layout、終了コード 0 |

- 検証したツリーは head（`7867cf5`）だけ。base（`main` の先端 `7a8e4b70b721`）は head の祖先なので、merge したツリーでの検証は要らない
- 結論 2（修正不要としてマージ）。この節を足した Spec の commit を PR の head に載せ、`finalize.py --spec-commit` でマージと関連 Issue（#230）の更新を行う（結果は状況コメントと完了の報告に書く）
