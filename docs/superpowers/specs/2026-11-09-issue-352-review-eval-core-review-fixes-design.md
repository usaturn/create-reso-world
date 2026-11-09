# PR #367 のレビュー修正: review-eval の基盤

- 状態: completed（サイクル 1 の結論 1: 修正して push、サイクル 2 の結論 2: 修正不要でマージ。内容の承認ではない）
- 対象: https://github.com/usaturn/create-reso-world/pull/367（Issue #352、親ボード #349 の子 `review-eval-core`）
- 実行許可: 利用者の `/issue-to-pr #352 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max` の `--merge` による PR 修正ループ（pr-review-fix-loop）の完遂。review-fix-planning の規則（致命的な指摘だけを直す、三択の結論、修正後の自己レビューは 1 回まで）で進める。内容の承認ではない
- 元の Spec: `docs/superpowers/specs/2026-11-09-issue-352-review-eval-core-design.md`、Plan: `docs/superpowers/plans/2026-11-09-issue-352-review-eval-core.md`
- サイクル: 1（PR に前の判断の記録は無い）。planner: claude-opus-5-5（claude-code）
- 現行 HEAD（レビュー対象）: `01491f1f9dca7b0e234f19e09e6ff4da7fe3efca`、base `0b5bcb60fd24692b0de3aa2224a7d5847f121bea`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `01491f1f9dca` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `01491f1f9dca` | はい | Approve |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash | pi | `01491f1f9dca` | はい | Approve |

- ループの run: `71750ad1b87b4f9cb4a4655e141edc6d`（`reviews/usaturn/create-reso-world/#367-feat-issue-352-review-eval-core/loop/`）
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#367-feat-issue-352-review-eval-core/verified/01491f1f9dca.json`（confirmed 4、claude-opus-5-5 が review-verify の cycle で作成）
- 工程の記録: 同じディレクトリの `verified/01491f1f9dca.planning.json`

## 全指摘と分類

レビュアーの指摘: 解消済み 0 / 対応する 1 / 対応しない 3。自己レビューの指摘: 対応しない 2（下の表の最後の 2 行）

| 判断 ID | 出典 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `gpt-6.1-sol#M-1@01491f1f9dca` | gpt-6.1-sol M-1（Medium） | 対応する（fix） | 致命的: README の `reconcile`・`ingest --repo` の手順どおりに、GitHub の表記のまま大文字を含む repo 名（設定の検証が受け付ける）を使うと、未観測のファイルがあるのに「0 件・終了コード 0」と報告し、取りこぼしを成功として扱う。(a) 再現した誤動作（確認済みの一覧 V-1。owner だけ・repo だけ・CLI 引数だけの大文字のどれでも反する） |
| `gpt-6.1-sol#M-2@01491f1f9dca` | gpt-6.1-sol M-2（Medium） | 対応しない（skip） | 既定の `max_sweep_files = 2000` では、1 つの review_dir に observation を作れない新しいファイルが 2000 件以上ないと起こらない。縮めた設定（再現は 1）でも `status`・`reconcile` が終了コード 1 で未処理の failure と未観測を出すので、黙って失われない。見直す条件: `max_sweep_files` を小さくする運用を始めるとき、または #357 の接続で sweep が主な取得経路になるとき |
| `deepseek-v4.1-flash#M-1@01491f1f9dca` | deepseek-v4.1-flash M-1（Medium） | 対応しない（skip） | `shim.run_hook` はこの PR に呼び出し元が無く（接続は #357）、この PR では到達しない。見直す条件: #357 が helper から `run_hook` を呼ぶとき（設定・review_dir・files・records を絶対パスにし、`environ` を子の環境に渡す）。持ち越し: #357 |
| `deepseek-v4.1-flash#L-1@01491f1f9dca` | deepseek-v4.1-flash L-1（Low） | 対応しない（skip） | 不正な UTF-8 の設定は traceback と非 0 の終了で表に出る（エラーで気付ける）。`collect` は `failed` を返して store に書かない。見直す条件: 設定を UTF-8 以外で書く運用が出たとき |
| `claude-opus-5-5-commit-416f15e087ed4ef43db01c8436fa1b6cb3373c68#L-1@416f15e087ed` | 自己レビュー（self-review）L-1（Low） | 対応しない（skip） | `deepseek-v4.1-flash#M-1@01491f1f9dca` と同じ問題（`shim.run_hook` の相対パス）。この PR に呼び出し元が無く到達しない。見直す条件は同じ判断のとおり |
| `fix-check#V-1@416f15e087ed` | 修正の確認（fix-check）V-1 | 対応しない（skip） | 修正後は、手で作った大文字を含むディレクトリ（`reviews/Usaturn/alpha/`）を `reconcile`・`ingest --repo` が列挙しない（修正前は設定と大小文字が同じなら列挙した）。CRW のツールは小文字の保存先しか作らず（`review_target.py`）、手での移行はこの PR の範囲外で、README の手順（新配置の場所に `ingest --review-dir` する）では取れるので、実在する構成で到達しない。見直す条件: 旧配置の移行を行うとき（README の複製の手順に小文字の規則を足す）、または大文字の owner/repo のディレクトリを作るツールが出たとき |

SWE-2 Max の指摘は 0 件。

## 要件対応

- PR・元の Spec の約束: `sources` は明示の許可リストで、未登録 repo も書けば対象になる（Spec 2 章、D3）。`ingest --repo`・`reconcile` は設定した sources の review_dir を走査する（README.rst）。保存先は CRW の `reviews/<owner>/<repo>/#<N>-<branch>/`（`review_target.py` が owner/repo を小文字にする）
- 今回の修正: `inventory.review_dirs` が owner/repo を `.lower()` にしてから保存先を組み立てる。観測する結果: 大文字を含む repo 名でも reconcile が未観測を出し、`ingest --repo` が保存する。検証: 追加するテスト 1 件と `tools/review_eval/tests` 全体
- 除外: 対応しない 3 件、`identify_review_dir` の規則（実在するディレクトリ名を使う）、README.rst の文言
- 共有条件: repo 名の解釈（config の検証・`source_for`・reconcile の絞り込み・`review_dirs`・`store.observations`）。統合担当は planner で、下の経路表と追加のテストで確かめる

## 対応する項目の修正方針

`review_dirs` で `owner`・`name` の形を今のまま検査した後に `.lower()` にして、`workspace_root/reviews/<owner>/<name>` を組み立てる（`review_target._lower_parts` と同じ `.lower()`）。他の案: (1) 設定の検証で大文字を拒否する — GitHub の表記（大文字を含む owner）のまま書けなくなり、CLI の `--repo` の大文字は防げない。(2) 大小文字を区別しないディレクトリの探索 — CRW の保存先は常に小文字なので不要で、走査が増える。推奨案は保存先の規則と同じ正規化を 1 か所で行うもの。

## 守る条件と影響経路

守る条件: 有効な repo 指定（大小文字を問わない）で、`reconcile` と `ingest --repo` が CRW の小文字の保存先を列挙する。破れた前提: `review_dirs` が、保存先を小文字にする `review_target.py` の規則と別に、引数の大小文字のままパスを組み立てていた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 小文字の保存先を列挙する | `inventory.review_dirs` | 修正する | 大文字を含む repo でも `#<N>-*` を返す | `test_mixed_case_repo_lists_the_lowercase_review_dir` | HEAD `416f15e0`（`e1ae0587` を取り込んだ commit）で `test_mixed_case_repo_lists_the_lowercase_review_dir` が成功（`uv run --locked pytest tools/review_eval/tests -q` → 32 passed）。修正を外した対照（隔離 worktree で `inventory.py` だけを `01491f1f` に戻す）では、このテストだけが失敗（1 failed, 2 passed） |
| 同上 | `inventory._scan`（reconcile）→ `review_dirs(config, source.repo)` | 修正する（上の修正で） | reconcile が未観測を出し終了コード 1 | 同じテストの reconcile の assert | 同じテストの `main(["reconcile", "--repo", "Usaturn/Alpha"]) == 1` と unobserved の assert が成功（`416f15e0`） |
| 同上 | `cli._ingest` → `review_dirs(config, args.repo, args.pr)` | 修正する（上の修正で） | `ingest --repo USATURN/ALPHA` が保存する | 同じテストの ingest の assert | 同じテストの `main(["ingest", "--repo", "USATURN/ALPHA"]) == 0` と observation の assert が成功（`416f15e0`） |
| 同上 | `capture.identify_review_dir`・`Config.source_for`・reconcile の sources の絞り込み・`store.observations`・`inventory.inventory` | 既に満たす | 実在するディレクトリ名と casefold の比較を使う | コード読み（`capture.py:126-147`、`config.py:83-85`、`inventory.py:498`、`store.py:154-161`） | 01491f1f のコミット済みの内容で確認 |
| 同上 | 大文字のディレクトリ（`reviews/Usaturn/alpha/`） | 対象外 | ― | ― | CRW のツールは小文字の保存先しか作らない（`review_target.py`） |

## 実行した検証と結果

すべて HEAD `416f15e087ed4ef43db01c8436fa1b6cb3373c68` の専用の worktree（`.worktrees/issue-352-review-eval-core`、`GIT_*` を除いた環境）で実行した。

| コマンド | 終了コード | 結果 |
| --- | --- | --- |
| 担当: `uv run --locked pytest tools/review_eval/tests/test_reconcile.py -q`（修正の前、`01491f1f`） | 1 | 1 failed, 2 passed（新しいテストだけが失敗） |
| `uv run --locked pytest tools/review_eval/tests -q` | 0 | 32 passed |
| 対照: 隔離 worktree で `inventory.py` を `01491f1f` に戻して `uv run --locked pytest tools/review_eval/tests/test_reconcile.py -q -p no:cacheprovider` | 1 | 1 failed, 2 passed（`test_mixed_case_repo_lists_the_lowercase_review_dir`） |
| `uv run --locked pytest tools -q` | 0 | 400 passed |
| `bash scripts/check-layout.sh` | 0 | PASS |
| `bash scripts/scan-before-push.sh -C <worktree> --base origin/main` | 0 | 11 commits、no leaks found（push はまだしない） |

ログ: `PARENT_ROOT/tmp/agents/review-fix-planning-pr367.dmc5zq15/verify/`

## 自己レビュー

`run_roles.py --phase self-review` の 1 回（工程の記録に `pre_push_review` を 1 件予約）。self-review・fix-check とも割り当ては `self` で、司令塔（claude-opus-5-5）がサブエージェント 2 つ（claude-opus-5-5）に並行で任せた。自己レビュー後の修正は無いので、再レビューもしていない。

- self-review（pr-review の非対話の入口、`--review-commit 416f15e087ed`、merge-base からの PR 全体）: `claude-opus-5-5-commit-416f15e087ed4ef43db01c8436fa1b6cb3373c68.md`、Approve。指摘は L-1（`shim.run_hook` の相対パス）1 件で、deepseek M-1 と同じ問題として対応しない。観点 2（PR 全体）で致命的な問題なし
- fix-check（review-verify の `fix_check`、`fix-check-review/verified/416f15e087ed.fix-check.json`）: 対象の修正 `gpt-6.1-sol#M-1@01491f1f9dca` は成り立つ（主張 12 件中 holds 11）。観点 1（反証）: `reconcile`（`--repo` の有無・`--apply`）・`ingest --repo`（`--pr` の有無、設定は小文字で引数だけ大文字）で小文字の保存先を検出・保存、誤った形の `--repo` 6 通りは修正の前後とも終了コード 2。新しい問題 V-1（手で作った大文字のディレクトリ）を対応しないと判定。観点 3（検出力）: `inventory.py` だけを戻すと追加したテストだけが失敗し、owner だけ・name だけ・reconcile の経路だけ・ingest の経路だけを小文字にする 4 つの変異でも失敗した

## 結論

結論 1（修正して push）。対応する 1 件を直し、上の検証が通り、自己レビューに致命的な指摘は無かった。対応しない 5 件のうち、実在する制約（sweep の上限、`run_hook` の相対パス、不正な UTF-8 の設定、手で作る大文字のディレクトリ）は PR の説明の既知の制約に書き足す。

- 修正の担当: runner の `pi_opencode-go_deepseek4-flash_max`（観測したモデル deepseek-v4.1-flash、146 秒。割り当てはループの `--assign implement=...`）。commit `e1ae0587` を停止の確認と差分の確認の後に `416f15e0` として取り込んだ
- 自己レビューの回数: 1（`run_roles.py --phase self-review` の 1 回の呼び出し）

## サイクル 2（HEAD `b9ff24aecdc867a7c44af9adb2fbea78eac488df`）

- サイクル 1 の状況コメント: https://github.com/usaturn/create-reso-world/pull/367#issuecomment-6736147549（判断の記録 round 1、`fixes_pushed`、commit `b9ff24ae`）
- レビュアーの構成:

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `b9ff24aecdc8` | はい（Update） | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `b9ff24aecdc8` | はい（Update） | Approve |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash | pi | `b9ff24aecdc8` | はい（Update） | Approve |
| `claude-opus-5-5-commit-416f15e087ed….md` | claude-opus-5-5 | claude-code | `416f15e087ed` | いいえ（サイクル 1 の自己レビュー） | Approve |

- 確認済みの一覧: `verified/b9ff24aecdc8.json`（候補 0）
- 分類: 新しい指摘 0 件。前のサイクルの `fix` の `gpt-6.1-sol#M-1@01491f1f9dca` は解消（`resolved`、`changed`、前の状態 `fix`）。`skip` の 5 件は新しい根拠が無いので引き継ぐ
- 検証（head `b9ff24ae` のツリー。base `0b5bcb60` は head の祖先）: `uv run --locked pytest tools/review_eval/tests -q` 0（32 passed）、`uv run --locked pytest -q` 0（1354 passed）、`bash scripts/check-layout.sh` 0（PASS）、`bash .devcontainer/run-tests.bash` 0（27 PASS）、rstcheck 0（Success）。前後とも `git status --porcelain` は空。ログ: `PARENT_ROOT/tmp/agents/review-fix-planning-pr367.dmc5zq15/verify-c2/`
- 結論: 2（修正不要でマージ）。`finalize.py --spec-commit` で、この Spec だけの commit をマージする。マージ・Issue の更新の結果は状況コメントと完了の報告に書く
