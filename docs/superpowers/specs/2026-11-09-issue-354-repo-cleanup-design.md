# Issue #354: マージ済み branch と残存 pinned ref の整理

## 管理・実行許可

- 状態: `completed`（実行許可であり内容の承認ではない。PR #373 のレビュー修正 サイクル5の確認を反映）
- 対象: usaturn/create-reso-world #354、親 #349、base `main`
- 利用者の指示: `/skill:issue-to-pr #354 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。続けて「#364が完了したことを確認して作業を実行してください。」
- 委任: 通常の設計判断、検証、commit、push、PR、指定ループの finalize によるマージ。実際の利用者の branch/ref/worktree を掃除する許可ではない。
- #364 は closed/completed、PR #371 は MERGED。merge commit `b61b36a3e11f969f4e4ab41c401dadfa00a86e90` は捕捉 base に含まれる。直接の先行 #351 も closed/completed。
- base は origin / refs/heads/main / `b61b36a3e11f969f4e4ab41c401dadfa00a86e90` に固定する。

## 目的・現状

祖先判定だけでは squash/rebase の元 branch を残してしまう。通常 branch の判定は merged PR と local tip の一致を要求しておらず、手順 8 とゲート B も祖先型だけである。また、helper が見ないセッション無しの ref と version 7 が残す ref に整理経路が無い。既存の手順 5 が許可する version 7 の狭い例外とゲート A・ガードレールの保持規則が食い違う。

## 要件

R1. 取り込みの証拠を祖先型と PR 型にする。どちらも対象 repository に明示した PR の `state == MERGED`、branch 名と `headRefOid` の完全一致を確認する。`isCrossRepository` が true、対応不明、欠落・照会失敗は原則保持する。ただし fork の経路の上流 PR は、`CLEANUP_ROUTE=fork` で、PR の head repository が検証済みの fork（`EXPECTED_HEAD_REPO`、`usaturn/resoloop`）と一致し、`TARGET_ROOT` が親 checkout の `external/resoloop` と一致する場合に限り受理する。無関係な fork と所属不明は保持する。PR 型では `mergeCommit` が選択した取り込み先 base に到達可能なことも確認し、別 base にしか入っていない PR を取り込み済みにしない。`git log` が非空なことだけでは拒否しない。

R2. 手順 3・通常ツールの候補照合・手順 8 の `-D` の再確認・ゲート B の候補提示で同じ意味の判定を使う。`-d` が拒否しても、直前に R1 を再確認した branch だけを `-D` にできる。他 worktree が保持する branch、既存 local main/base、open PR、dirty/ignored の保護は維持する。リモート branch は祖先一覧だけに限定せず PR 型も提示するが、削除には必ず別のユーザー確認が必要。

R3. `refs/pr-review/repos/<owner>/<repo>/<N>` と旧 `refs/pr-review/<N>` を一覧から調べる。セッション無しの ref も対象。対応 repository と PR を確定し、PR が MERGED/CLOSED、関連する全 open PR と現行・保持中の session が ref を使わないことを確認したものだけ削除できる。session の照会が成功しただけで完全な一覧としない（登録のない残骸・bundle 等も考慮）。unknown は保持。fork/upstream で旧 ref の所属が一意に分からなければ、片方の終了だけで消さない。ref の現在値を読んで `git update-ref -d <ref> <読んだ値>` で compare-and-delete。並行更新で値が変わったら保持し、新しい値で無条件にやり直さない。

R4. coordinator の決定 https://github.com/usaturn/create-reso-world/issues/354#issuecomment-6743479090 を本文より優先。version 7 の ref は SKILL の残存 ref 手順で扱い、`pr_review_workspace.py` は一切変更しない。手順 5 は変更せず、`run_context` の無い version 7 が helper に終了コード 1 で拒否された場合だけ通常の clean/worktree/ゲート A 経路へ進めることをゲート A・ガードレールにも明記。version 8、run_context 付き、終了コード 2 は保持する。`removable` を保存・停止・所有の検証の代わりにしない。

## 範囲と除外

編集は `.agents/skills/repo-cleanup-after-merge/SKILL.md` の対象判定・手順 3・8・ゲート B・残存 refs・ゲート A/ガードレールの例外整合、および同 `tests/`、本 Spec・Plan。手順 5、helper、CLEANUP_BASE、fork sync、version 7/8 の gate A の照合本体、removable 定義、force 禁止、ignored gate は変更しない。AW の projects.toml・submodule force は移植しない。実環境の掃除や remote branch 削除、設定・CI の追加は対象外。

## 決定記録

| ID | 選択した案 | 検討した別案 | 理由・委任/停止条件 |
|---|---|---|---|
| D1 | SKILL 内の実行できる判定と fake gh/使い捨て Git のテスト | 文言だけの追記、別 helper 新設 | 安全条件を実行で確かめる。新 helper は所有範囲外。判定と削除の証拠を揃える |
| D2 | R1 の PR head と取り込み先の証拠 | branch 名/MERGED だけ、祖先のみ | 再利用 branch・後追い commit・未統合 base の誤削除を防ぎ squash/rebase に対応 |
| D3 | ref は手順で所属・open PR・session を照合し CAS | helper version7 の改変、prefix 一括削除 | coordinator の明示決定。判定不能なら保持する |
| D4 | 手順5を維持し gate A/ガードレールへ例外を揃える | version7 を全面保持 | coordinator の明示決定。保護の意味が変わる変更は停止 |
| D5 | Task を runner に直列依頼 | controller が実装、同時書込 | `--implement` の指定。check は self=false、agents=[pi_opencode-go_deepseek4-flash_max]、fallback=[]。失敗時に controller へ切替えない |
| D6 | PR 後に指定 inspect 3名と implement のループ | マージしない、自前でマージ | 利用者の --merge。max_cycles=3 は既定、inspect と implement は利用者指定。self-review/fix-check は既定 self。通常の範囲/安全停止は維持 |

## 検証方針

動作環境は Linux Dev Container、Bash、Git、gh の fake、uv/pytest。`mktemp` 相当の一意の一時 Git repository に非 ASCII・複数行の内容と空白入りパスを用意する。祖先・squash・rebase の正例、未マージ・PR 不明・head 不一致・別 repo/base の反例を実行する。ref は閉じた PR の削除正例と open PR/session/所属不明/並行更新の保持を確かめる。外部の実 PR/API をテストには使わない。HOME はワンショットで隔離し GIT_* を除去する。

追加テストは実際の気付きにくい誤削除・誤分類・競合を防ぐ S と、実際の不具合の再発防止だけ。文言・frontmatter の写し合わせ、一般的な構文/オプションの L テストは追加しない。同じ守りは代表1件。SKILL のコードブロックを抽出して実行し、単なる文字列検査にしない。writing-skills の無し/ありの適用シナリオは別の読み取り専用担当で各1回、作業前後を比較する。

## 実行記録（公開前）

- Task1 は `9361d044`、base 除外の修正は `d9180ca3`。Task2 は `0d27e0e3`、symbolic ref/CAS/session 検証の修正は `4a7219b8`。全体レビューの root/大小文字/一覧上限/重複テスト修正は `9be97ac9`。
- 指定 runner は全依頼で `pi_opencode-go_deepseek4-flash_max`、観測モデルは `opencode-go/deepseek-v4.1-flash`、effort max。Task1 2依頼（約1191秒・115秒）、Task2 2依頼（約825秒・390秒）、全体修正1依頼（約405秒）。全て importable/accepted、停止確認 true、cleanup の retained は無し。
- 各 Task と限定再レビュー、最後の全体レビューと1回の修正・限定再レビューを実施。最後の関連テストは controller が clean HEAD `9be97ac9` で51件成功、終了コード0。追加テストはS、重複CASテストはDとして代表へ集約した。
- R1/R2: 実 Git の祖先/squash/rebase と、未マージ・不明・head/base不一致を確認。最後の修正で残存 TARGET_ROOT の別 clone 削除、repository 大小文字の session 取り違え、100件での一意性誤判定を再現して防いだ。
- R3/R4: session 無し終了PRのref削除正例、open/current session、曖昧な旧ref、symbolic ref、一覧後の更新、所属の型/形式不正の保持を確認。手順5/helperは変更しない。GREEN適用では旧形式の複数所属・不完全なsession一覧は保持、version7の限定例外のみ従来経路と判定した。
- GREENの担当がrebase入力に「mergeCommitがnull」という未提示の前提を加えたため、その部分は採用しない。入力はAと同じreachableなmergeCommitであり、実rebase履歴テストと公式REST/GraphQL資料をcontrollerが照合した。欠落時は安全側に保持する。
- skill-efficiency-check は終了コード0、Issues/Warningsなし。別helperファイルへの分離は所有範囲外なので、SKILL内の実行ブロックを維持する。
- 共通の全体検証・scan・PR・指定ループは、この記録の後で実行し、HEAD/base/ログをPRとセッションへ記録する。未実行を成功としない。

## 既知の baseline

変更前の読み取り専用適用シナリオで、squash/rebase は `git log` が非空のため保持、セッションの無い ref は手順が無いため保持となった。version7 の例外と gate A の衝突も残る。これは新しい手順で改善すべき挙動であり、機械テストと合わせて再確認する。

## PR #373 サイクル2の修正方針（実装・検証）

実行許可: 利用者の「破棄してやり直してください」と、PR #373 の review-fix-planning 完遂（loop run `7b99a6f023664832ab25d035d4185720`）。planner は deepseek-v4.1-flash / claude-code。入力 HEAD は `3b8f55365c9b`、レビューは loop の reuse で 3 件（claude-opus-5-5・deepseek-v4.1-flash・SWE-2 Max）。確認済みの一覧は `reviews/usaturn/create-reso-world/#373-fix-issue-354-repo-cleanup/verified/3b8f55365c9b.json`。

| 指摘 | 分類 | 根拠 |
| --- | --- | --- |
| `deepseek-v4.1-flash#H-1@3b8f55365c9b` | 対応する（引き継ぎ） | `MAIN_ROOT` 不在 + 古い `TARGET_ROOT` が同じ remote の別 clone を指すと、手順 8 がその clone の取り込み済み branch を削除する。誤った対象への操作で致命的。(a) 隔離再現 V-1。 |
| `claude-opus-5-5#M-1@3b8f55365c9b` | 対応する（引き継ぎ） | fork の上流 PR は常に `isCrossRepository: true` のため、取り込み済みでも共通判定が保持を返し、SKILL が示す通常の fork 手順が機能しない。主要な処理の停止で致命的、D1。(a) 隔離再現 V-2。 |
| `SWE-2-Max#L-1@3b8f55365c9b` | 対応しない（引き継ぎ） | `evals/evals.json` の期待文が手順 3 の更新に追随していない。文書のみで非致命的、`evals.json` は変更範囲外。見直す条件: 期待文の更新が変更範囲に入ったとき、または利用者が指定したとき。 |
| `SWE-2-Max#U-1@3b8f55365c9b` | 解消済み（引き継ぎ） | 対応している v7/v8 の session は main checkout を要求し、linked root の session は helper が拒否するため再現しない。V-4 の `not_reproduced`。 |
| `fix-check#V-1@1a1f7d4bbd8c` | 対応する（新規） | 前の fork 作業の `CLEANUP_ROUTE=fork`・`TARGET_ROOT`・`EXPECTED_HEAD_REPO` が同じシェルに残り `MAIN_ROOT` を失うと、別 clone の branch を削除した。経路の値だけで削除先を決めていた。`TARGET_ROOT` が `$PARENT_ROOT/external/resoloop` と一致することを削除の前に確かめる。 |
| `fix-check#V-3@1a1f7d4bbd8c` | 対応する（新規） | ゲート B が環境に残った `EXPECTED_HEAD_REPO` をそのまま渡し、create/managed でも cross-repository の PR をリモート削除候補に提示し得た。`cleanup_expected_head_repo` で経路から決め、create/managed（未設定を含む）では空にする。 |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c#L-2@1a1f7d4bbd8c` | 対応する（新規） | Spec R1 と Plan の Global Constraints・受け入れ基準が cross-repository を一律保持と述べ、検証済み fork の例外と食い違う。将来 M-1 を再導入し得るため、Spec/Plan を実装に合わせる。 |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c#L-3@1a1f7d4bbd8c` | 対応する（新規） | `-D` 直前の再確認ガードを削除しても既存テストが通る。再確認の 2 回目で PR が OPEN に変わった場合に branch を削除しない負例を足す。 |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c#L-4@1a1f7d4bbd8c` | 対応する（新規） | 手順 3 の新しいブロックが `CHECKOUT` の空値を検査せず、`git -C ""` が呼び出し元の cwd を読む。`:?` で空値を拒否する。 |

### 守る条件の設計・再発の見直し

H-1 は、前の全体レビューで扱った削除先の同定の適用漏れに当たる（同じ守る条件の 2 回目）。両 root が存在するときの比較だけでは、`MAIN_ROOT` の無い create 呼び出しと正当な fork 入力を区別できない。経路を明示する `CLEANUP_ROUTE` を導入し、`create` は `MAIN_ROOT`、`fork` は `PARENT_ROOT/external/resoloop` と一致する `TARGET_ROOT` + `EXPECTED_HEAD_REPO`、`managed` は `CLEANUP_ROOT` を削除先とする。経路を決められない・root が欠ける・別 checkout を指す場合は、branch・ref・HEAD を変更する前に停止する。

最初の修正は `CLEANUP_ROUTE` だけで削除先を決めていたため、前の fork 作業の変数が同じシェルに残る入力で別 clone を削除した（fix-check V-1）。経路の値だけでなく、fork の削除先が親 checkout の `external/resoloop` と一致することを確かめる形に直した。ゲート B も同じ経路判定を通し（V-3）、手順 3 は対象 checkout の空値を拒否する（L-4）。

M-1 は、PR が追加した cross-repository の一律保持の回帰。cross-repository をすべて拒否すると fork の通常手順が止まり、すべて受け付けると無関係な fork の branch を削除し得る。`cleanup_branch_evidence` に 7 番目の引数（検証済みの fork の `owner/name`）を足し、PR の head repository がそれと一致するときだけ cross-repository を受け付ける。`create` と `managed` は空に固定し、無関係な fork と head 不明は保持する。

比較: 点の fallback 分岐を増やす案は同定条件が分散するため不採用。cross-repository を全面保持する保証縮小は、Issue #354 の「fork 経路を変えない」に反するため不採用。経路・削除先・head の所属を明示して 1 か所で判定する案を選ぶ。

| 守る条件 | 経路 | 判定 | 変更前／観測する結果 | 検証・assertion | 証拠 |
| --- | --- | --- | --- | --- | --- |
| create の削除先は `MAIN_ROOT` だけ | 手順 8 の create・別呼び出し | 修正する | `MAIN_ROOT` なし + stale `TARGET_ROOT` = 別 clone → 全 ref/HEAD 不変で停止 | 実 Git 2 clone。実行前後の全 ref/HEAD 比較。拒否理由が `CLEANUP_ROUTE` か `MAIN_ROOT` | `test_step8_stops_when_only_a_stale_target_root_is_set`（実行済み） |
| fork の削除先は `$PARENT_ROOT/external/resoloop` と一致 | 手順 8 の fork | 修正する | stale な fork 変数で `TARGET_ROOT` = 別 clone → 全 ref/HEAD 不変で停止 | 実 Git 3 clone。実行前後の全 ref/HEAD 比較。`external/resoloop` の不一致を確認 | `test_step8_stops_when_a_stale_fork_route_points_at_a_foreign_checkout`（実行済み） |
| fork の cross-repository は検証済み head だけ | 手順 3・8・ゲート B・通常ツール | 修正する | 正例: head = `usaturn/resoloop`（大小文字違いを含む）で `ancestor`/`pr`。反例: 無関係 fork・head 欠落・expected 空・6 引数 → 保持 | fake gh の正例と反例。既存の cross-repository 保持も維持 | `test_branch_evidence_accepts_an_upstream_pr_only_from_the_verified_fork`、`test_step8_uses_the_route_specific_root`（実行済み） |
| create・managed では stale `EXPECTED_HEAD_REPO` を無効にする | 手順 3・8・ゲート B | 修正する | create に `EXPECTED_HEAD_REPO` が残っても手順 3・ゲート B が cross-repository の PR を候補にしない | `cleanup_expected_head_repo` の経路判定。ゲート B の create/fork 正例と反例 | `test_gate_b_clears_a_stale_fork_expectation_on_the_create_route`、`test_step8_uses_the_route_specific_root` の create ケース（実行済み） |
| 経路不明・root 欠落・別 checkout は削除前停止 | 手順 8 | 修正する | `MAIN_ROOT` なし + `TARGET_ROOT` のみ、route 不明、`MAIN_ROOT` と `TARGET_ROOT` が別 → ref/HEAD 不変 | 実行 | H-1・V-1 のテスト、既存の競合ケース、`test_steps_8_and_11_stop_when_main_root_is_unset_instead_of_using_callers_repo` |
| `-D` の直前に同じ判定をやり直す | 手順 8 の `not fully merged` 経路 | 修正する | 再確認で PR が OPEN に変わったら branch を削除しない | fake gh の 2 回目を OPEN に切り替える。削除後に branch が残ることを確認 | `test_step8_stops_when_the_dash_d_recheck_loses_the_pr_evidence`（実行済み） |
| 対象 checkout の空値は cwd に fallback しない | 手順 3 | 修正する | `CHECKOUT` などが空なら停止し、`git -C ""` を実行しない | `:?` の追加。空値の拒否は L（呼び出し側の即時エラー）として個別テストを足さない | `: "${CHECKOUT:?...}"` ほか（静的確認） |
| 既存の create 正例・祖先/squash/rebase・managed・無関係 fork 保持 | 各経路 | 既に満たす（変更影響を確認） | 削除・候補の結果が従来どおり | 既存テスト 57 件 | 57 passed（11.15 秒） |
| 失敗時に何も変えない | route・root・head の検証失敗 | 修正する | 失敗の前後で全 ref/HEAD が不変 | 実行前後の状態比較。中心のガードを外した対照で負例が失敗する | 下の変異対照 |
| `evals.json` の期待文 | evals/evals.json | 対象外 | 文言の陳腐化は非致命的。変更範囲外 | 静的照合 | L-1 の `skip` |

### 実行した検証

- RED: 新しい `--json` フィールドに対する既存の正例と M-1 の新規テストが失敗（11 failed / 43 passed）。判定関数だけを実装し手順 8 を変更前のままにした版では、H-1 のテストが失敗し、stdout に `Deleted branch merged-feature` が出て別 clone の branch が実際に削除された（2 failed / 52 passed）。
- GREEN: `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` → 57 passed（11.15 秒）。`git diff --check` → 終了コード 0。
- 環境の全体検証: ``bash .devcontainer/run-tests.bash` → 27 件 PASS、`bash scripts/check-layout.sh` → PASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools -q` → 1385 passed（594.69 秒）。すべて終了コード 0。`
- 変異対照: route フォールバック（H-1）、create の `EXPECTED_HEAD_REPO` 消去、head repository 検査（M-1）、fork の削除先の一致（V-1）、ゲート B の経路判定（V-3）、`-D` の再確認（L-3）をそれぞれ外した隔離 worktree で、対応する代表テストが失敗することを確認した。負例には異常を 1 つだけ入れ、他の入力は正常にした。
- 実 gh の読み取り: `gh pr list --head <branch> --repo orange3134/resoloop --state all --json ...` が fork の PR #19 を返し、`gh pr view 19` が `headRepository`・`headRepositoryOwner`・`isCrossRepository` を返すことを確認した（書き込みなし）。fork 手順 3 の PR 番号照会はこの経路で成立する（fix-check V-4 の未確認を解消）。
- 自己レビュー: `run_roles.py --phase self-review` の 1 回。self-review は `deepseek-v4.1-flash-commit-1a1f7d4bbd8c28be3b8c1f16ad1df09e8166b5e5.md` に Low 3 件（L-2・L-3・L-4）を記録し、すべてこのサイクルで修正した。修正後の再レビューはしていない。fix-check は `fix-check#V-1`・`V-2`・`V-3`・`V-4` を記録し、V-1・V-3・L-2（=V-2）を修正、V-4 は実 gh の読み取りで解消した。

### 実行の担当・時間

- 実装: `claude-code_opus_default`（実際のモデル claude-opus-5-5、claude-code）、約 260 秒。commit `1a1f7d4b`（実装担当の `c46247f7` を cherry-pick し、H-1 テストの拒否理由の assertion を足して amend）。
- レビュー修正: 司令塔（deepseek-v4.1-flash / claude-code）。commit `1faff0af2bac7a50cbd253623822aca32168d13a`。
- 自己レビュー・修正の確認: 既定の `self` で 1 回。fix-check は約 1703 秒、self-review は約 10 分。
- レビュアーの構成: `claude-opus-5-5.md`（claude-opus-5-5 / claude-code / `3b8f55365c9b` / Initial / Approve）、`deepseek-v4.1-flash.md`（deepseek-v4.1-flash / pi / `3b8f55365c9b` / Initial / Request changes）、`SWE-2-Max.md`（SWE-2 Max / devin / `3b8f55365c9b` / Initial / Approve）。
- サイクル: 2（loop の run `7b99a6f0…` のサイクル 1、判断の round は 2）。

## PR #373 サイクル3の修正（ゲート B の削除元 remote）

入力 HEAD は `c613393f`。レビューは gpt-6.1-sol（M-1、Medium、検証済み）と SWE-2 Max（active 0）。確認済みの一覧は `verified/c613393fbc64.json`。

| 指摘 | 分類 | 根拠 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1@c613393fbc64` | 対応する（新規） | ゲート B が PR の所属側の remote（`upstream`）を削除元に選び、fork の `origin` の branch を取りこぼす。上流に同名・同 OID の branch があると、fork の PR を根拠に上流 branch を候補にする。`134e7ce3` で remote 選択と fetch URL の検証を実装した。 |
| 前サイクルの fix 7 件（H-1・M-1・V-1・V-3・V-2/L-2・L-3・L-4） | 解消済み（変更） | `c613393f` の関連 57 テストと SWE-2 Max の再現で、各修正が現行 HEAD にあることを確認した。 |
| `SWE-2-Max#L-1@3b8f55365c9b` | 対応しない（引き継ぎ） | `evals.json` の期待文。非変更範囲で非致命的。 |
| `SWE-2-Max#U-1@3b8f55365c9b` | 解消済み（引き継ぎ） | v7/v8 の session は main checkout を要求し、linked root は helper が拒否する。 |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b#M-1@134e7ce35b18` / `fix-check#V-1@134e7ce35b18` | 対応する（新規） | ゲート B の削除コマンドが cwd 依存で、承認後の `git push` は push URL を使う。親 checkout や pushurl の別 repository の branch を削除し得る。`e79c662028be8bc4cf20fa7b70701813d2227846` で `git -C "$CHECKOUT"` と fetch URL・push URL の両方の検証を追加した。 |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b#L-1@134e7ce35b18` | 対応する（新規） | 新テストが URL 検証を remote 名の検証と区別できない。`REMOTE=origin` で fetch URL / push URL を上流にする負例を追加した。 |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b#L-2@134e7ce35b18` | 対応しない（新規） | fork の旧形式 `refs/pr-review/<N>` は 2 つの repository の所属を一意に確定できないため保持する。誤削除を避ける保守的な動作で非致命的。見直す条件: 旧形式 ref の所属を一意に決める仕様が coordinator により決まったとき。 |

### 守る条件の設計

ゲート B の削除元 remote は PR の head repository に対応させる。fork→upstream PR では、PR の照会先は `orange3134/resoloop`、取り込み先 base は `upstream/main`、削除元 remote は fork の `origin`（検証済み head repository `usaturn/resoloop`）とする。ゲート B は fork の経路で `REMOTE` の fetch URL と push URL の両方を GitHub の `owner/name` に正規化し、`EXPECTED_HEAD_REPO` と一致するときだけ候補を出す。サイクル4で、fetch と push のすべての URL、create・managed の `PR_REPO`、平文 HTTP の拒否に拡張した。承認後の削除と prune は `git -C "$CHECKOUT"` で検証済みの checkout に対して実行する。一致しない・URL を解釈できないときは、候補を出さずに停止する。

最初の修正 `134e7ce3` は remote の選択と fetch URL の検証だけだったため、承認後の削除が cwd の repository と push URL に依存する経路が残った（自己レビュー M-1、fix-check V-1）。削除コマンドの checkout 固定と push URL の検証を追加した。

| 守る条件 | 経路 | 判定 | 変更前／観測する結果 | 検証・assertion | 証拠 |
| --- | --- | --- | --- | --- | --- |
| 削除元 remote は head repository に対応する | 手順 9・ゲート B | 修正する | `REMOTE=upstream` は fork の branch を候補にせず、上流に同名 branch があるとそれを候補にする | 2 remote の実 Git。正例 `REMOTE=origin`、反例 `REMOTE=upstream`。refs/remotes と remote 設定の不変 | `test_gate_b_deletes_upstream_pr_branches_only_from_the_verified_fork_remote`（実行済み） |
| 削除と prune は検証済み checkout に固定する | 手順 9 の削除 | 修正する | cwd の親 checkout の remote branch を削除し、fork の branch が残る | 親と fork の 2 checkout。削除後の fork と親の remote ref を比較 | `test_gate_b_deletion_uses_the_verified_checkout_not_the_caller_cwd`（実行済み） |
| push URL も head repository に対応する | ゲート B の候補提示 | 修正する | fetch URL が fork、push URL が別 repository のとき、候補を出して別 repository を削除する | `remote.<name>.pushurl` を上流にする負例。候補を出さない | `test_gate_b_deletes_upstream_pr_branches_only_from_the_verified_fork_remote` の push URL ケース（実行済み） |
| URL 検証を remote 名の検証と区別する | テスト | 修正する | `REMOTE=origin` で URL が上流でも通る実装を検出できない | fetch URL の負例と push URL の負例 | 同テストの fetch URL ケース（実行済み） |
| create・managed の既存挙動 | ゲート B | 既に満たす | 従来の候補 | 既存テスト | 59 passed（11.13 秒） |
| 前サイクルの fix 7 件 | 各経路 | 解消済み | 修正前の欠陥が再現しない | 57 tests と SWE-2 Max の再現 | 判定の記録 |
| 旧形式 ref（fork） | 残存 ref | 対象外（保持） | 2 repository の所属を一意に確定できないため保持する | 実行 | 自己レビュー L-2 の保持確認 |
| 実際の remote branch 削除 | 手順 9 の承認後 | 対象外 | テストでは実行しない | 静的確認 | 外部 push は対象外 |

### 実行した検証

- RED: `c613393f` の隔離 worktree に修正側のテストだけを写して実行した。`REMOTE=upstream` が「候補: fork-feature (pr, PR #7)」を出し、テストが失敗した（1 failed, 17 deselected）。
- GREEN: `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` → 59 passed（11.13 秒）。`git diff --check` → 終了コード 0。
- 変異対照: push URL の検証を外すとゲート B のテストが失敗し、削除コマンドの `-C "$CHECKOUT"` を外すと削除先のテストが失敗することを、隔離 worktree で確認した。負例には異常を 1 つだけ入れ、他の入力は正常にした。
- 全体検証: ``bash .devcontainer/run-tests.bash` → 27 件 PASS、`bash scripts/check-layout.sh` → PASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools -q` → 1387 passed（557.56 秒）。すべて終了コード 0。`
- 自己レビュー: `run_roles.py --phase self-review` の 1 回。self-review は `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b.md` に M-1・L-1・L-2 を記録し、M-1・L-1 を修正、L-2 を「対応しない」とした。fix-check は `134e7ce3.fix-check.json` に V-1（push URL）を記録し、修正した。修正後の再レビューはしていない。

### 実行の担当・時間

- 実装: `claude-code_opus_default`（実際のモデル claude-opus-5-5、claude-code）、約 137 秒。commit `134e7ce3`（実装担当の `d0c2ba07` を cherry-pick）。
- レビュー修正: 司令塔（deepseek-v4.1-flash / claude-code）。commit `e79c662028be8bc4cf20fa7b70701813d2227846`。
- 自己レビュー・修正の確認: 既定の `self` で 1 回。self-review 約 478 秒、fix-check 約 365 秒。
- レビュアーの構成: `gpt-6.1-sol.md`（gpt-6.1-sol / pi / `c613393fbc64` / Initial / Approve）、`SWE-2-Max.md`（SWE-2 Max / devin / `c613393fbc64` / Update / Approve）。
- サイクル: 3（loop の run `7b99a6f0…` のサイクル 2、判断の round は 3）。

## PR #373 サイクル4の修正（ゲート B の URL 正規化と全送信先）

入力 HEAD は `799dbb98`。レビューは gpt-6.1-sol（M-2・M-3）と SWE-2 Max（M-1）。確認済みの一覧は `verified/799dbb98321a.json`。

| 指摘 | 分類 | 根拠 |
| --- | --- | --- |
| `gpt-6.1-sol#M-2@799dbb98321a` | 対応する（新規） | fork の既存手順が許可する末尾 `/` 付きの URL をゲート B が拒否し、正常な fork checkout で候補を提示できない。`cleanup_remote_repo_key` で末尾 `/` を取り除いてから `.git` を取り除く。 |
| `gpt-6.1-sol#M-3@799dbb98321a` / `SWE-2-Max#M-1@799dbb98321a` | 対応する（新規） | `git remote get-url --push` は最初の 1 件だけを返すため、複数の pushurl（または複数の url）があると、承認後の削除が未検証 repository にも届く。fetch と push の全 URL を `--all` で検査し、1 件でも解釈不能・不一致なら停止する。 |
| `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e#L-1@9fe0d95bffb4` | 対応する（新規） | `cleanup_remote_repo_key` が平文 HTTP の URL を受理していた。HTTPS・SSH に限定し、HTTP を拒否する。 |
| `fix-check#V-1@9fe0d95bffb4` / `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e#I-1@9fe0d95bffb4` | 対応する（新規） | Plan と Spec のサイクル3の記述が「fetch と push の両方」のままで、変更後の「すべての URL」「create・managed は PR_REPO」を述べていない。両文書を更新した。 |
| `fix-check#V-2@9fe0d95bffb4` | 対応する（新規） | create・managed の URL 検査を省略する退行を既存テストが検出しない。same-repository の PR と fork の pushurl を使う負例を追加した。 |
| `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e#I-2@9fe0d95bffb4` | 対応する（新規） | Spec は `completed`、Plan は issue-to-pr の `draft` で、PR 本文の「両文書は draft」が Spec の状態と食い違う。PR 本文を Spec completed・Plan draft に更新した。 |
| 前サイクルの fix 2 件（`fix-check#V-1@134e7ce35b18`・`deepseek-v4.1-flash-commit-134e7ce3…L-1@134e7ce35b18`） | 解消済み（変更） | `799dbb98` の関連 59 テストと 2 名のレビューで、削除先の固定と push URL の検査を確認した。 |
| `SWE-2-Max#L-1@3b8f55365c9b` | 対応しない（引き継ぎ） | `evals.json` の期待文。非変更範囲で非致命的。 |
| `deepseek-v4.1-flash-commit-134e7ce3…L-2@134e7ce35b18` | 対応しない（引き継ぎ） | fork の旧形式 ref は 2 repository の所属を一意に確定できないため保持する。 |
| `SWE-2-Max#U-1@3b8f55365c9b` | 解消済み（引き継ぎ） | v7/v8 の session は main checkout を要求し、linked root は helper が拒否する。 |

### 守る条件の設計

ゲート B の期待 repository は、fork の経路では `EXPECTED_HEAD_REPO`、create・managed（`EXPECTED_HEAD_REPO` が空）では `PR_REPO` とする。fetch と push のそれぞれで `git remote get-url --all` / `git remote get-url --push --all` を使い、返った URL をすべて正規化して期待 repository と比べる。1 件でも解釈できない・一致しない URL があれば、候補を出す前に停止する。末尾 `/` と `.git` の表記差は同じ repository として扱い、平文 HTTP は受け付けない。削除は引き続き `git -C "$CHECKOUT" push "$REMOTE" --delete <branch>` とし、cwd に依存させない。

| 守る条件 | 経路 | 判定 | 変更前／観測する結果 | 検証・assertion | 証拠 |
| --- | --- | --- | --- | --- | --- |
| fetch と push の全 URL が期待 repository と一致する | ゲート B の候補提示 | 修正する | pushurl が [fork, 上流] だと 2 件目を検査せず、削除が上流にも届く | 2 pushurl の正例（[fork, fork]）と反例（[fork, 上流]）。refs/remotes と remote 設定の不変 | `test_gate_b_deletes_upstream_pr_branches_only_from_the_verified_fork_remote`（実行済み） |
| create・managed は `PR_REPO` の全 URL を検査する | ゲート B | 修正する | 期待 repository が空で URL 検査を通らない | same-repository の PR と fork の pushurl で候補を出さない | `test_gate_b_clears_a_stale_fork_expectation_on_the_create_route`（実行済み） |
| 末尾 `/` と `.git` の表記差を同一視し、HTTP を拒否する | URL 正規化 | 修正する | `.../resoloop/`・`.../resoloop.git/` を拒否し、HTTP を受理する | `cleanup_remote_repo_key` の一時確認と HTTP の負例 | `test_gate_b_deletes…` の HTTP 負例（実行済み） |
| 削除は検証済み checkout に固定する | 手順 9 の削除 | 既に満たす | cwd 依存の削除 | 既存の削除先テスト | 59 passed |
| 前サイクルの fix 2 件 | 各経路 | 解消済み | 修正前の欠陥が再現しない | 59 tests と 2 名のレビュー | 判定の記録 |
| `evals.json`・旧形式 ref | 文書・残存 ref | 対象外／保持 | 非致命的・所属不明 | 静的照合・保持 | L-1・L-2 の判断 |
| 実際の remote branch 削除 | 承認後 | 対象外 | テストでは実行しない | 静的確認 | 外部 push は対象外 |

### 実行した検証

- RED: `799dbb98` のテスト変更のみの状態で、2 件目の上流 pushurl の反例が失敗した（1 failed, 58 passed）。M-2 はレビュアーの隔離再現で、末尾 `/` の 2 表記が候補を出さないことを確認した。
- GREEN: `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` → 59 passed（11.79 秒）。`git diff --check` → 終了コード 0。
- 一時確認: `cleanup_remote_repo_key` が `https://github.com/usaturn/resoloop/`・`.../resoloop.git/`・`.../resoloop.git`・`.../resoloop//`・`git@github.com:usaturn/resoloop.git` を同じ `usaturn/resoloop` にし、`https://github.com/usaturn/` と `http://github.com/usaturn/resoloop.git` を拒否した。
- 変異対照: push の全 URL 検査を最初の 1 件に戻すとゲート B のテストが失敗し、HTTP を再び受理すると HTTP の負例が失敗し、create の `PR_REPO` fallback を外すと create 側の負例が失敗することを、隔離 worktree で確認した。末尾 `/` の除去を外す変異は 59 passed のままで、明示的なエラー停止の L として永続テストを追加していない。
- 全体検証: ``bash .devcontainer/run-tests.bash` → 27 件 PASS、`bash scripts/check-layout.sh` → PASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools -q` → 1387 passed（550.46 秒）。すべて終了コード 0。`
- 自己レビュー: `run_roles.py --phase self-review` の 1 回。self-review は `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e.md` に L-1（HTTP）・I-1（文書）・I-2（状態）を記録し、L-1・I-1・I-2 を修正した。fix-check は `9fe0d95bffb4.fix-check.json` に V-1（文書）・V-2（create 側のテスト）を記録し、修正した。修正後の再レビューはしていない。

### 実行の担当・時間

- 実装: `claude-code_opus_default`（実際のモデル claude-opus-5-5、claude-code）、約 114 秒。commit `9fe0d95b`（実装担当の `aa0b6988` を cherry-pick）。
- レビュー修正: 司令塔（deepseek-v4.1-flash / claude-code）。commit `9954e8cfcd3efd495dcb79a7f4c90816e4110b47`。
- 自己レビュー・修正の確認: 既定の `self` で 1 回。self-review 約 569 秒、fix-check 約 452 秒。
- レビュアーの構成: `gpt-6.1-sol.md`（gpt-6.1-sol / pi / `799dbb98321a` / Update / Approve）、`SWE-2-Max.md`（SWE-2 Max / devin / `799dbb98321a` / Update / Approve）。
- サイクル: 4（loop の run `7b99a6f0…` のサイクル 3、判断の round は 4）。この run はサイクル上限 3 に達するため、修正を push した後にマージせず `fixes_pushed` で終わる。

## PR #373 サイクル5の確認（コード修正不要）

- 実行許可: 利用者が明示した `/skill:pr-review-fix-loop https://github.com/usaturn/create-reso-world/pull/373 --assign inspect=devin_swe2_max,claude-code_opus_default`。既存PRの確認・採否・必要な修正・検証・push・finalizeまでであり、利用者のbranch/ref/worktreeの掃除や別PRの作成は含めない。
- planner: `openai-codex/gpt-6.1-sol` / pi（bash内のPI_PROVIDERとPI_MODELで確認）。loop run `23b349e63400400eaedfa92c4b57ee44` のサイクル1、判断のrecordは round 5。
- 入力HEAD: `89afc5fd3a14f1b9b1421a812cf70b31e8696a11`。既存専用worktreeがcleanかつ同じHEADであることを確認して借用した。他runの領域は変更・削除しない。
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#373-fix-issue-354-repo-cleanup/verified/89afc5fd3a14.json`、工程の記録は同stemの `.planning.json`。候補ペアと全7レビューHEADの祖先関係を検査した。
- 結論: **2 修正不要として最終化へ進む**。前の判断20件を引き継ぎ、前のfix6件を現行HEADで解消済みに変更した。解消済み18 / 対応する0 / 対応しない4。新しい受理形の追加や文言だけの修正・テスト追加は行わない。
- 実装担当・自己レビュー: コード修正なしのため `run_roles.py` は未実行。implementの設定はclaude-code_opus_default、self-review/fix-checkはselfだが、今回の担当実行や自己レビュー枠の消費は無い（0回）。同じ条件の再発に当たる「対応する」指摘も無い。

### レビュアーの構成

| ファイル | モデル / runtime | 対象HEAD | 今回の扱い | 推奨 |
| --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max / devin | `89afc5fd3a14` | 今回再実行・accepted | Approve |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `89afc5fd3a14` | 今回再実行・accepted | Approve |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash / pi | `3b8f55365c9b` | 古い入力、採否は引き継ぎ | Request changes |
| `gpt-6.1-sol.md` | gpt-6.1-sol / pi | `799dbb98321a` | 古い入力、採否は引き継ぎ | Approve |
| `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e.md` | deepseek-v4.1-flash / claude-code | `9fe0d95bffb4` | 古い入力、採否は引き継ぎ | Approve |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b.md` | deepseek-v4.1-flash / claude-code | `134e7ce35b18` | 古い入力、採否は引き継ぎ | Approve |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c28be3b8c1f16ad1df09e8166b5e5.md` | deepseek-v4.1-flash / claude-code | `1a1f7d4bbd8c` | 古い入力、採否は引き継ぎ | Approve |

現在HEADの2担当はrunner/成果物ともaccepted、rejectedは無し。古い5レビューの判断済み指摘は新しい修正要求として再採用せず、全レビューの未判断・Pending・Unverifiedが残っていないことを確認した。

### 全判断と根拠

| 判断ID | 分類 | 根拠 |
| --- | --- | --- |
| `deepseek-v4.1-flash#H-1@3b8f55365c9b` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `claude-opus-5-5#M-1@3b8f55365c9b` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `SWE-2-Max#L-1@3b8f55365c9b` | 対応しない（引き継ぎ） | 評価文の陳腐化は事実だが、文書のみで致命的ではない。evals.json は PR の変更許可範囲外である。 |
| `SWE-2-Max#U-1@3b8f55365c9b` | 解消済み（引き継ぎ） | 対応している v7/v8 の session の作成・読み込みは main checkout を要求し、linked root の session は helper が拒否するため再現しない。 |
| `fix-check#V-1@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `fix-check#V-3@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `fix-check#V-2@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c#L-3@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `deepseek-v4.1-flash-commit-1a1f7d4bbd8c#L-4@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 修正後の HEAD c613393f の関連 57 テストと SWE-2 Max の再現で、この指摘の修正が現行 HEAD にあり、対象の欠陥が再現しないことを確認した。 |
| `fix-check#V-4@1a1f7d4bbd8c` | 解消済み（引き継ぎ） | 実 gh の読み取りで、gh pr list --head <branch> --repo orange3134/resoloop --state all が fork の PR #19 を返し、gh pr view 19 が headRepository・headRepositoryOwner・isCrossRepository を返すことを確認した。コードの変更は不要。 |
| `gpt-6.1-sol#M-1@c613393fbc64` | 解消済み（引き継ぎ） | ゲート B の削除元 remote を head repository に対応させ、fetch URL を検証する修正を 134e7ce3 で実装した。削除コマンドの cwd 依存と push URL は別の指摘として e79c6620 で修正した。 |
| `fix-check#V-1@134e7ce35b18` | 解消済み（引き継ぎ） | 799dbb98 の関連 59 テストと 2 名のレビューで、削除と prune の git -C "$CHECKOUT" 固定、fetch URL と push URL の検査を確認した。 |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b#L-1@134e7ce35b18` | 解消済み（引き継ぎ） | 799dbb98 の関連 59 テストで、fetch URL・push URL の負例と削除先の固定を確認した。 |
| `deepseek-v4.1-flash-commit-134e7ce35b18a8c5cc448bf06dd5e19ad737d47b#L-2@134e7ce35b18` | 対応しない（引き継ぎ） | 旧形式 ref は fork/upstream の 2 repository の所属を一意に確定できないため保持する。誤削除を避ける保守的な動作で非致命的。 |
| `gpt-6.1-sol#M-2@799dbb98321a` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `gpt-6.1-sol#M-3@799dbb98321a` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e#L-1@9fe0d95bffb4` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `fix-check#V-1@9fe0d95bffb4` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `fix-check#V-2@9fe0d95bffb4` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `deepseek-v4.1-flash-commit-9fe0d95bffb4acb18f7cb472f220d4e510f9e12e#I-2@9fe0d95bffb4` | 解消済み（変更） | 89afc5fdのcommitted内容で解消を確認。関連59テスト、12入力の隔離ゲートB probe、Spec/Plan全URL・PR_REPOとlive PR本文の状態照合。HEAD/base統合とも必要検証成功。 |
| `SWE-2-Max#L-2@89afc5fd3a14` | 対応しない（新規） | 隔離再現で事実と確認。既存fork helper/managed resolverも同表記を受理せず、公式の通常経路の回帰ではない。明確なメッセージ付き安全停止で、誤削除・漏えい・誤対象操作は起きず致命的でない。対応するには受理範囲の新要件が必要。 |
| `planner#S-1@89afc5fd3a14` | 対応しない（新規） | Planはissue-to-pr時のdraftと実行予定、Specは後段review-fix完遂のcompletedで、同じ状態にする要件はない。古い参照・予定の記録は実行コード/削除条件に影響しない文書上の情報で非致命的。Spec冒頭のサイクル番号は今回の必須の記録更新で5へ進める。 |

「対応しない」の見直し条件: evalsの文言は変更範囲に入ったとき、旧形式refは所属を一意に確定できる仕様が決まったとき、URL表記は公式fork/managed resolverの受理範囲が広がったとき、文書状態は誤操作につながる具体的な利用経路が確認されたとき。いずれも利用者が名指しで指定した場合は見直す。

### 要件対応と統合確認

統合担当はplanner。Issue #354本文とcoordinator決定comment-6743479090、PRの保証・制限、既存Spec R1〜R4とPlanを照合した。共有するbranch取り込み判定、route/root/head repositoryの同定、refの所有と非使用の条件を個々のテスト成功だけでなく次の経路と結び付けた。

| 要件 | 現行の確認対象・観測結果 | 証拠 |
| --- | --- | --- |
| R1/R2: 祖先/squash/rebase、PR/head/base照合、誤対象の保持 | 手順3・8・ゲートB・通常ツールの共通関数と全呼出元、テスト全文。正常候補、未マージ/不明/別repo/base/head差の保持、-D前の再判定 | 隔離HEADの関連59テスト成功。全7変更ファイル全文の読取 |
| R2: fetch/push全送信先を同定、create/managedのPR_REPO | 2pushurlの正負例、HTTP拒否、末尾/と.git/受理。create/managedの正常候補と別pushurl停止をそれぞれ実行 | 一時probe 12入力、全ref/config不変、関連59テスト |
| R3: refの所有・非使用・終了PR、symbolic拒否、CAS | 旧形式の所属不明は保持、repo修飾refの正例、open/session/並行更新/symbolicの保持 | test_residual_refs.py全文と実行。旧形式refの制約は維持 |
| R4: version7限定例外と所有境界 | 手順5/helperを変更せず、run_context無しv7/exit1だけ既存経路。v8/run_context/exit2は保持 | 全体差分とcommitted本文・関連テスト |
| 文書の現在状態 | live PR本文はSpec completed・Plan draft。Planは初期計画としてdraft、Specはreview-fix完遂の状態 | PR読取とSpec/Plan全体の意味照合。古い計画注記から実行保証を追加しない |

L-2の独立再現では、抽出したゲートBが `.GIT`・`.Git`・ポート付きsshをexit1で拒否し、候補なし・全ref/config不変だった。末尾/、.git/、scp形式、ポート無しsshは正常候補を出した。fork helperのsame_urlとmanaged registry/contextのURL解析も前者を受理しておらず、既存の公式経路を壊す回帰ではない。これは明確な停止で気付けるLのため永続テストを足さない。既存の安全性テストはSの代表と正常側を維持し、同一守りの組合せ追加や固定文言のテストを増やさない。

### 実行した検証と残る範囲

検証したbase先端は `60af10023b74706e473c7e3c0ae56d820584479f`。これは入力HEADの祖先ではないため、別のmktemp隔離worktreeでHEADにこのbaseをmergeした一時commit `99ebcdd2a441d320ce68a7ba73a1c513713b608e`（tree `9a609193545937c5c61bd216578494e8f13e4a28`）も検証した。このmergeはpushしない。

| コマンド | 入力HEAD | baseとの統合ツリー |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 27件PASS / exit0 | 27件PASS / exit0 |
| `bash scripts/check-layout.sh` | PASS / exit0 | PASS / exit0 |
| `uv run --locked pytest -p no:cacheprovider tests/skills .agents/skills -q` | 759 passed / exit0（509.50秒） | 759 passed / exit0（530.43秒） |
| `git diff --check 60af1002...HEAD` | exit0 | exit0 |

- 隔離HEADの関連テストは59 passed（12.49秒）。一時probeは1 passed（0.81秒、12入力）で、実Gitとfake ghのみを使った。追加テストやコード変更は無い。
- validation/checksの記録にargv・終了コード・対象HEAD/tree・実測時間を保存した。HEADと統合ツリーの検証後はtracked差分なし。一時worktreeはgit worktree removeを通して回収した。
- 実環境の掃除、実GitHubへの削除push、実sessionの退役は対象外で未実行。managedは実登録ツールを触らずfake APIと一時Gitで経路の正負を実行した。これらを実機確認済みとはしない。
- 確認済みの一覧はconfirmed 2（新L-2と旧形式refの意図された保持）/ not_reproduced 11 / unverified 0。確認工程は1525.88秒。読取補助2件は全文・関連経路の確認で、採否とテスト実行はplannerが担当した。全体の判断工程は約42分（検証約21分を含む）。
- GitHub Actionsはこのリポジトリの規約どおり無効のまま。Specだけのcommitを入力HEADの直接の子として追加し、記録付きコメント・Gitleaks検査・fast-forward pushの後、finalizeがHEAD/base/merge親を照合する。push・マージ・Issueの結果はこのSpecに追記せず、状況コメントと完了報告へ記録する。
