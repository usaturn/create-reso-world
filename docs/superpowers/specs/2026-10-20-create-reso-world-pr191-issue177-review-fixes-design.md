# PR #191（Issue #177）のレビュー修正の選別（1 回目）

- 文書管理・対象: `usaturn/create-reso-world`、PR #191（`fix/issue-177-review-verify-dir-precheck`）、Issue #177
- 状態: `completed`
- 実行許可: 利用者の `/review-fix-planning #191`（2026-10-20 JST）。計画で止める指示が無いので完遂として扱い、結論 2 のマージと関連 Issue の更新まで許可されている。内容の承認ではない
- 現行 HEAD: `dba2f6c20d8d3a9d24158f8b8a6c0e96e46b9f16`（PR の head）。base `origin/main` `8f5074ac14b43803b334f8256e4273b97a40a0f3` は merge-base と同じで、head の祖先
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#191-fix-issue-177-review-verify-dir-precheck/`
- planner: claude-opus-5-5（Claude Code）。親の main checkout（`8f5074a`）の review-fix-planning・review-verify・monitoring-long-tasks を使った
- サイクル: 1（PR に判断の記録は無い）
- 関連: 実装の Spec `docs/superpowers/specs/2026-10-20-create-reso-world-issue177-review-verify-dir-precheck-design.md`、Plan `docs/superpowers/plans/2026-10-20-create-reso-world-issue177-review-verify-dir-precheck.md`

## レビュアーの構成

4 人のレビュアーが、2026-10-19 17:27–17:41Z に現行 HEAD をレビューした（実行記録の `runner` は null）。

| レビューファイル | モデル（ランタイム） | レビュー HEAD | Mode | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol（pi） | `dba2f6c20d8d` | Initial | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max（devin） | `dba2f6c20d8d` | Initial | はい | Approve |
| `Grok-4.7.md` | Grok 4.7（cursor） | `dba2f6c20d8d` | Initial | はい | Approve |
| `claude-opus-5-5.md` | claude-opus-5-5（claude-code） | `dba2f6c20d8d` | Initial | はい | Approve |

- 4 件とも、候補一覧 `findings/<レビューファイル名>-dba2f6c20d8d.json` が `review_findings.py validate` と `check-pair` を通った。指摘 0 件、Unverified candidates 0 件
- 入力から外したファイルは無い

## 全指摘と分類

分類: 解消済み 0 / 対応する 0 / 対応しない 0（4 人とも指摘 0 件）

レビュアーが指摘にしなかった観察（判断の対象ではない。記録のために残す）:

- root の `lstat` が `PermissionError` のときも `review_dir must be an existing directory` と表示する（claude-opus-5-5・Grok-4.7）。終了コード 2 で担当を起動しないことは同じで、表示の精度だけの差である。PR の説明に既知の Minor として書かれている
- 書き込みできない `verified/` での accept の失敗（claude-opus-5-5）。Issue #177 の受け入れ条件と実装の Spec の D-2 の対象外で、PR はこの扱いを変えていない

## 確認の範囲

- 読んだもの: 4 件のレビューファイルと候補一覧・実行記録、PR の全体差分（6 ファイル、+468/−5）と変更ファイルの全文（`dispatch.py`・`test_dispatch.py`・`test_run_roles.py`・`fix-check.md`・実装の Spec・Plan）、呼び出し元の `run_roles.py` の全文、`review-verify/tests/conftest.py` の `managed_state` とテストの fixture、条件を述べる文書（review-verify の `SKILL.md`・`references/cycle.md`・`references/fix-check.md`、review-fix-planning の `references/execution.md`、`review_target.py` の `resolve`、両スキルの evals）
- `check_review_directories`・`reject_review_links`・`snapshot_review` の呼び出し元は、`dispatch.py` の `dispatch()` と `run_roles.py` の `fix_context` だけである（`git grep`）。fix_check の dispatch を直接呼ぶほかのスキルは無い。`run_roles.py` の手順（`execution.md` 59 行）は `FIX_STAGING` を起動の前に作るので、新しい検査で止まらない
- PR head の隔離 worktree で、関連テスト `test_dispatch.py`・`test_run_roles.py` → 197 passed（103 秒）
- 同じ隔離 worktree で、レビュアーが試していない入力 35 件 → すべて期待どおり
  - `dispatch.main`（外部の担当・`self`）: root の親が mode 000 → 終了コード 2（`review_dir must be an existing directory`）。root 自体が mode 600・000 → 終了コード 2（`PermissionError`）。root が UNIX ソケット・FIFO、`verified` が UNIX ソケット・FIFO・参照先の無いリンク、存在しない祖先を `..` で通るパス、祖先が通常ファイル → 終了コード 2 と期待した分類。どれも担当を起動せず、`tmp_path` 全体（パス・種類・mode・bytes・リンク先）が前後で同じ
  - 空白と日本語を含む root で、`verified` が無い・既存のディレクトリ → 外部の dispatch と accept が終了コード 0 で 2 件を保存し、既存のファイルを残す。`self` の `main` は終了コード 0
  - 起動の後に `verified` を FIFO・ソケットにする → accept は終了コード 1 で `verified` を列挙する。root を通常ファイルにする → 終了コード 2。どれも 1 行の理由で、traceback にならない
  - `run_roles.run`（外部の担当）と `run_roles.main`（雛形の既定の `self`・`self`、空の個人設定）: 保存先が無い・通常ファイル・親が mode 000・`verified` が通常ファイル → `ValueError` か終了コード 2 と分類の文、保存先自体が mode 600 → `PermissionError`。どれも予約（`activities`）・起動・出力先・ロックが無い。正常な保存先では終了コード 0 で `pre_push_review` を 1 件予約する
- 対照: base のコードに PR head の 2 つのテストファイルを当てて、新しいテストを実行 → 8 failed・1 passed。新しい負例 8 件は変更前の欠陥を検出し、起動の後の `verified` の 1 件は変更前から通る回帰の防止である（PR の説明と同じ）
- `git diff --check 8f5074ac14b4 dba2f6c20d8d` → 終了コード 0
- 確認中に、PR が持ち込んだ致命的な欠陥は見つからなかった（自己確認なし）

### 確認済みの一覧と工程の記録

- 確認済みの一覧: レビューディレクトリの `verified/dba2f6c20d8d.json`（mode cycle、v2、指摘 0 件、`validate` 終了コード 0）と要約 `verified/dba2f6c20d8d.md`。review-verify の cycle の手順で、司令塔が自分で作った
- 閉じた範囲: run_roles の入口での通常ファイル・親 mode 000（Grok-4.7 の未実施）、`lstat` の `PermissionError`（SWE-2-Max の未実施）、検査と snapshot の間の同時変更（Grok-4.7 の未実施。対象外と文書化されており、snapshot と起動の後の照合を PR が変えていないことを読んで確かめた）、上の追加の入力と対照
- 残った範囲: リポジトリ全体の検証は、下の「実行した検証と結果」で実行した。本物の担当での dispatch と accept は、費用がかかり Issue・Plan に無いので実行しない（AGENTS.md「エージェント運用」）
- 工程の記録: レビューディレクトリの `verified/dba2f6c20d8d.planning.json`（サイクルの最後に書く）

## 結論

結論 2（修正不要としてマージ）。

- 修正の担当と自己レビュー: 修正が無いので `run_roles.py` は使わず、自己レビュー（1 回枠）も行わない（回数 0）
- base: マージの前（2026-10-19 18:15Z）に `git fetch origin main` で取り直し、`origin/main` が `8f5074ac14b4` のままで head の祖先であることを確かめた。base を merge した一時的なツリーでの検証は不要
- CI: create-reso-world は private で CI を止めているため確かめない（AGENTS.md「GitHub Actions」）
- マージしてよい範囲: `usaturn/create-reso-world` の open で draft でない PR（18:15Z に open・draft でない・MERGEABLE を確かめた）
- 最終化: 親の main checkout（`8f5074a`）の review-fix-planning の `finalize.py` を `--spec-commit` 付きで使う。この PR は `finalize.py`・`run_roles.py`・投稿の helper を変えていない
- PR の説明の既知の制限: 「対応しない」の指摘が無いので書き足さない

## 実行した検証と結果

PR の head `dba2f6c20d8d3a9d24158f8b8a6c0e96e46b9f16` の専用の worktree（`.worktrees/issue-177-review-verify-dir-precheck`、未コミットの変更なし）で、2026-10-19 17:51–18:14Z に順に実行した。

- `bash .devcontainer/run-tests.bash`: 33 本 PASS（終了コード 0、649 秒）
- `bash scripts/check-layout.sh`: PASS（終了コード 0）
- `uv run pytest tests/skills .agents/skills`: 1257 passed（終了コード 0、765 秒）
- 実行の後も、worktree の HEAD は `dba2f6c20d8d` のままで、未コミットの変更は無い

この Spec だけの commit は、上の検証の後に PR の head に載せる（検証した head の直接の子で、変更はこの 1 ファイルだけ）。

## 役割・回数・時間

- 担当: 選別・確認・最終化とも planner（claude-opus-5-5、self）。修正の担当と自己レビューの担当（self-review・fix-check）は無い。自己レビューの回数は 0
- 時間（UTC、2026-10-19）: 着手の時刻は記録していない（最初に記録した時刻は 17:46:30）。確認済みの一覧（review-verify の cycle）17:46:30–17:58:44（734 秒）、全体の検証 17:51:01–18:14:36（確認と並行）、選別の記録と Spec 〜18:16
