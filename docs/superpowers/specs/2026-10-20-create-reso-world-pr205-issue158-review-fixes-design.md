# PR #205（Issue #158）のレビュー修正の選別（1 回目）

- 文書管理・対象: `usaturn/create-reso-world`、PR #205（`feat/issue-158-issue-to-pr-merge`）、Issue #158（親 #116、ボード `review-automation-board`）
- 状態: `completed`
- 実行許可: 利用者の `/review-fix-planning #205`（2026-10-20 JST）。計画で止める指示が無いので完遂として扱い、結論 2 のマージと関連 Issue の更新まで許可されている。内容の承認ではない
- 現行 HEAD: `6268254218447d650693f2b3031581f97051488f`（PR の head）。merge-base は `d29c93c12a817ca45cb8d0eb918a0a07615916ce` で、選別の時点の `origin/main` の先端と同じ（base は進んでいない）
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#205-feat-issue-158-issue-to-pr-merge/`
- planner: claude-opus-5-5（Claude Code）。親の main checkout（`d29c93c`、`origin/main` と同じ）の review-fix-planning・review-verify・monitoring-long-tasks を使った
- サイクル: 1（PR に判断の記録は無い）
- 専用の worktree: `/workspaces/reso-world/.worktrees/issue-158-issue-to-pr-merge`（issue-to-pr の run が作った feature worktree。PR の head ブランチを checkout していて、未コミットの変更が無く HEAD が PR の head なので、そのまま使った。このセッションが作ったものではないので片付けない）
- 関連: 実装の Spec `docs/superpowers/specs/2026-10-20-create-reso-world-issue158-issue-to-pr-merge-design.md`、Plan `docs/superpowers/plans/2026-10-20-create-reso-world-issue158-issue-to-pr-merge.md`

## レビュアーの構成

4 人のレビュアーが、2026-10-20 05:53Z から現行 HEAD をレビューした（実行記録の `runner` は 4 件とも null）。

| レビューファイル | モデル（ランタイム） | レビュー HEAD | Mode | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5（claude-code） | `626825421844` | Initial | はい | Approve |
| `gpt-6.1-sol.md` | gpt-6.1-sol（pi） | `626825421844` | Initial | はい | Approve |
| `Grok-4.7.md` | Grok 4.7（cursor） | `626825421844` | Initial | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max（devin） | `626825421844` | Initial | はい | Approve |

- 4 件とも、候補一覧 `findings/<レビューファイル名>-626825421844.json` が `review_findings.py validate` と `check-pair` を通った。実行記録 4 件も `validate` を通った。指摘は claude-opus-5-5 の L-1（Low）の 1 件だけ。Unverified candidates は 0 件
- 入力から外したファイルは無い

## 全指摘と分類

分類: 解消済み 0 / 対応する 0 / 対応しない 1

| 判断 ID | 区分 | 重大度（報告） | 内容 | 根拠 |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5#L-1@626825421844` | 対応しない | Low | issue-to-pr の 5 章の結果の表で、ループのエラーの行のマージの欄が一律に「していない」（`.agents/skills/issue-to-pr/SKILL.md:224`）。`finalize.py` がマージした後の `cycle-end`・`finish` のエラーでは、マージ済みの PR を未マージと報告させる | 致命的でない（下の「L-1 の判断」） |

### L-1 の判断

- 現行 HEAD での確認: 実在する（確認済みの一覧の V-1、confirmed）。PR head の隔離 worktree で、pr-review-fix-loop の fixture（偽の gh・bare remote）を使い、結論 2 の順序（記録の投稿 → Spec の commit の push → `finalize.py` のマージ → `cycle-end` → `finish`）で次を再現した
  - マージの後の `cycle-end` が、gh api user の失敗で終了コード 5（`github`）。PR はマージ済みで、`run.json` の `result` は null のまま（`status` の `next` は `cycle-end`）
  - マージの後の `cycle-end` が、`spec_commit` の欠けた `finalize.py` の結果で終了コード 4（`merge_mismatch`）。PR はマージ済み
  - `cycle-end` が `merged: true` を記録した後の `finish` が、停止を確認できない資源で終了コード 7（`resources`）。`run.result.merged` は true
  - 対照: マージの前の段階のエラーでは、マージは起きない（`cycle-begin` の gh の失敗は再現した。`review` と `start` の `lock_held` は、計画の前に止まることをコードで確かめた）
- PR 起因: 持ち込み（`c5de6cb` が表を足した。base の SKILL.md に「ループのエラー」の行は無い）
- 致命的かどうか: 致命的でない。発生条件（結論 2 のマージの後に GitHub の読み取りが一時的に失敗する、記録を取り違える、資源の停止を確認できない）は実在する構成で到達できるが、誤るのは最終報告のマージの欄の文面だけである
  - マージ・closing Issue の close（`finalize.py`）とループの記録（`status` の `next` の `cycle-end` を再実行すれば `merged: true` を記録する）は正しい
  - 実際の状態は GitHub で確かめられる。誤った報告に従って続けても、`loop.py start`（PR が open でないと止まる）・`resolve_issue.py`（closed の Issue で止まる）・`finalize.py`（同じ head では再マージしない）が二重の操作を止める
  - 秘密情報の露出・データの消失・了承の無い設定変更や誤った対象への操作・主要な処理の停止・セキュリティのどれにも当たらない。pr-review-fix-loop の SKILL.md の「最終報告」（issue-to-pr の 6 が従う）は「マージしたか」を書かせる
- 見直す条件: issue-to-pr の結果の表を機械的に読む処理（自動の報告・ボードの台帳の更新など）を足すとき、またはループのエラーの後の報告で、マージ済みの PR を未マージとして扱う操作（再実装・予約の取り直し）が実際に起きたとき
- 別 Issue の候補（起票はしない）: 結果の表のループのエラーの行のマージの欄を「結果のとおり」にし、`finalize.py` の結果の `merged` を確かめて書く（レビュアーの推奨と同じ）
- PR の説明: 実在する制約なので、PR の本文の「既知の制限」に、条件と回避方法（`finalize.py` の結果の `merged` か GitHub の PR の状態を確かめて報告する）を書き足した（SKILL.md の「三択の結論」の冒頭の規則）

## 確認の範囲

- 読んだもの: 4 件のレビューファイル・候補一覧・実行記録、PR の本文、Issue #158 の本文とコメント 4 件、親 #116 の #158 に関係する行、PR の全体差分（7 ファイル、+1128/−55）と変更ファイルの全文（`.agents/skills/issue-to-pr/SKILL.md`・`scripts/resolve_issue.py`・`tests/test_resolve_issue.py`・`evals/scenarios.json`・`evals/validation.md`、実装の Spec・Plan）
- 呼出元・関連の処理: `resolve_issue.py` の `parse_input`・`ParsedInput` の呼出元は同じファイルの `main` だけ（`git grep`）。pr-review-fix-loop の `loop.py` の `parse_assign`・`load_assignments`・`check_options`・`start`・`cycle_begin`・`cycle_end`・`finish`・`audit_resources`・`cleanup_output`・`require_target_checkout`・CLI（`_add_option_arguments`、`check-options` と `start` が同じ定義）と SKILL.md 全体、`finalize.py` の `MERGEABLE_REPOSITORIES`・`check_evidence`・CI（`wait_for: ci`）・draft の拒否・`--spec-commit`、review-fix-planning の SKILL.md の専用の worktree・結論 2 と `references/execution.md` の 3 章。PR は pr-review-fix-loop と review-fix-planning を変えていない（`git diff --quiet d29c93c 6268254`）
- 照合: SKILL.md の `--merge` の流れ（`check-options` を worktree の前に `PARENT_ROOT` の `loop.py` で実行、`loop_args` の各要素を 1 つの引数で足さずに渡す、draft にしない、CI を待たずにループへ進む、`PARENT_ROOT` の `loop.py start`、文書の PR をループに乗せない、usaturn/resoloop-meshy の `--merge` は止まる、既存の PR をループに乗せない、予約は `finish` の後に解放）は、`loop.py`・`finalize.py`・review-fix-planning の記述と一致した。食い違いは L-1 の 1 行だけ
- `resolve_issue.py` の入力の境界: 値はどれも 1 つの引数として次のコマンドに渡り、パスは絶対パスになる（`-` で始まる値が次のコマンドのオプションにならない）。`--hold-action=…`・`--fresh-review=…` も名前で拒否する。`--max-cycles` は ASCII の数字だけ。レビュアー 4 人の境界の入力（空白・非 ASCII・シェルの特殊文字・`~`・`=` の形・空の値・繰り返し・`--merge` の前後）の結果とも一致する
- PR head の隔離 worktree で、関連テスト（issue-to-pr の全テスト、`test_loop_check_options.py`、resoloop-meshy の PR の `start` が止まるテスト）→ 238 passed（終了コード 0）
- 確認中に、PR が持ち込んだ致命的な欠陥は見つからなかった（自己確認なし）。レビューの持ち越し（PR に記載済み）のうち、パスの値がシェルの特殊文字を通すことは、入力が利用者自身のもので権限の境界をまたがず、SKILL.md が各要素を 1 つの引数として渡すと定めるので致命的でない。検証の後に commit を足したときの記録の取り直しが書かれていないことは、同じ HEAD の条件で再利用されないだけで、計画の中で検証し直すので安全側に止まる

### 確認済みの一覧と工程の記録

- 確認済みの一覧: レビューディレクトリの `verified/626825421844.json`（mode cycle、v2、指摘 1 件（V-1、confirmed）、`validate` 終了コード 0）と要約 `verified/626825421844.md`。review-verify の cycle の手順で、司令塔が自分で作った
- 閉じた範囲: L-1 の再現（claude-opus-5-5 の未実施）、usaturn/resoloop・usaturn/resoloop-meshy の `--merge` の helper の前提（Grok-4.7。2 つの checkout は実在し、`loop.py` は meshy の PR を `start` で止め、`finalize.py` のマージの範囲・CI・draft の扱いは SKILL.md と一致）、private の Actions（gpt-6.1-sol。AGENTS.md「GitHub Actions」により対象外）、関連テスト、候補一覧と実行記録の形
- 残った範囲: PR の作成後のループと usaturn/resoloop の `--merge` の実機（Issue #158 の受け入れは利用者が `--merge` を書いた run に限る）、resoloop・resoloop-meshy の実 checkout でのスキルの手順の実行（外部の操作）、別ランタイムでの振る舞いの比較と sonnet の取り直し（本物のモデルを起動する費用。AGENTS.md「エージェント運用」）、ruff・Pyright（この環境に無く、README の「テスト」に含まれない）。リポジトリ全体の検証は、下の「実行した検証と結果」で実行した
- 工程の記録: レビューディレクトリの `verified/626825421844.planning.json`（サイクルの最後に書く）

## 結論

結論 2（修正不要としてマージ）。

- 修正の担当と自己レビュー: 修正が無いので `run_roles.py` は使わず、自己レビュー（1 回枠）も行わない（回数 0）
- 実機のループ: Issue #158 の受け入れの「実機: 利用者が `--merge` を書いて指示した Issue で、PR の作成 → ループ → 結果の報告まで（利用者の指示があるときだけ）」は未実施のまま。この選別は `--merge` の run ではない。PR の本文の「行っていない確認」に書かれている
- base: 選別の時点の `origin/main` は `d29c93c`（merge-base と同じ）で、head は base の上にある。base を merge した一時的なツリーでの検証は要らない
- CI: create-reso-world は private で CI を止めているため確かめない（AGENTS.md「GitHub Actions」）
- マージしてよい範囲: `usaturn/create-reso-world` の open で draft でない PR（open・draft でない・MERGEABLE・CLEAN を確かめた）
- 最終化: 親の main checkout の review-fix-planning の `finalize.py` を `--spec-commit` 付きで使う。この PR は `finalize.py`・`run_roles.py`・投稿の helper を変えていない
- PR の説明の既知の制限: L-1 の条件と回避方法を書き足した

## 実行した検証と結果

PR の head `6268254218447d650693f2b3031581f97051488f` の専用の worktree（`.worktrees/issue-158-issue-to-pr-merge`、未コミットの変更なし）で、2026-10-20 06:23:32–06:49:43Z に順に実行した。README の「テスト」の 3 つで、Issue #158 の「検証」の一括の 3 つと同じである。

- `bash .devcontainer/run-tests.bash`: 33 本 PASS（終了コード 0、364 秒）
- `bash scripts/check-layout.sh`: PASS（終了コード 0）
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`: 3446 passed（終了コード 0、1205 秒）。skip・失敗は無い（PR の本文の記録（`e6405ef`）の 1 skipped は、他の git プロセスを除外できないときに skip する設計のテストで、今回は通った）
- 実行の前後とも、worktree の HEAD は `626825421844` で、未コミットの変更は無い
- base: 実行の後に取り直した `origin/main` も `d29c93c`（merge-base）のままで、head は base の上にある。base を merge した一時的なツリーでの検証（結論 2 の手順 2）の条件に当たらない
- 確認済みの一覧の作成の中で、PR head の隔離 worktree でも関連テスト（issue-to-pr の全テストと `test_loop_check_options.py` など）238 passed と、L-1 の再現（4 passed）を実行した（上の「確認の範囲」）

この Spec だけの commit は、上の検証の後に PR の head に載せる（検証した head の直接の子で、変更はこの 1 ファイルだけ）。

## 役割・回数・時間

- 担当: 選別・確認・最終化とも planner（claude-opus-5-5、self）。修正の担当と自己レビューの担当（self-review・fix-check）は無い。自己レビューの回数は 0
- 時間（UTC、2026-10-20）: 着手の時刻は記録していない（最初に記録した時刻は 06:20:29）。確認済みの一覧（review-verify の cycle）06:20:29–06:27:37（428 秒）、PR head の検証 06:23:32–06:49:43（1571 秒。run-tests.bash 364 秒・check-layout.sh 0 秒・pytest 1207 秒）。選別・記録・Spec は検証の待ちと並行した。待ち時間は計測していない
