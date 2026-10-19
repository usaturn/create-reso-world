# Issue #177 review-verify の dispatch で、保存できない review_dir を起動の前に拒否する

- 文書管理・対象: `usaturn/create-reso-world`、Issue #177（ラベル `bug`。親 Issue・依存なし）
- 基準 HEAD: `8f5074a6`（`origin/main`、2026-10-20）。Issue の検証 commit `03d9aac7` から `.agents/skills/review-verify/` に変更は無い
- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者が 2026-10-20 に `/issue-to-pr #177` と指示した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける（マージはしない）。これは実行の許可であり、この文書の内容の承認ではない。以下の判断は、確認を取らずに決めたエージェントの判断である
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、利用者の指定ではない
- Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue177-review-verify-dir-precheck.md`

## 意図

review-verify の `dispatch.py`（mode `fix_check`）は、`review_dir` が無い、または `review_dir/verified` が通常ファイルのとき、結果を保存できないことが起動の前に分かるのに、外部の担当を起動する。担当の期限は最大 1800 秒で、回収に成功しても `accept` が拒否するので、時間と API の利用が無駄になる。起動の前の入力の検査で拒否し、外部の担当も runner の成果物も作らないようにする。

`verified` が通常ファイルのときの traceback の文面の改善だけは目的にしない（Issue の「重要性」）。

## 確認した事実（2026-10-20、`8f5074a6`）

- `check_review_directories`（`dispatch.py:205-208`）は、`review_dir`・その全祖先・`verified` のリンクだけを拒否する
- `snapshot_review`（`dispatch.py:211-254`）は先頭で `check_review_directories` を呼び、`review_dir` が無ければ `{}` を返す
- `dispatch`（`dispatch.py:292-294`）は `check_review_directories` と `snapshot_review` の後に `run_workflow` で担当を起動する。`run_workflow` が `--output-dir` を作る。`self` の割り当てでも `run_workflow` が成果物（`dispatch.json`）を作る
- `accept`（`dispatch.py:503-505`）は `review_dir` が無ければ終了コード 2。511 行で起動時の snapshot と照合する。537 行の `verified_dir.mkdir(exist_ok=True)` は `verified` が通常ファイルだと `FileExistsError` になる
- `main` は `ValueError`・`OSError` を終了コード 2 にし、`REQUEST_ERRORS` にある文だけを stderr に出す（ほかは型の名前だけ）
- review-fix-planning の `run_roles.py` の `fix_context`（`run_roles.py:301-311`）は、`verifier.check_review_directories` と `verifier.snapshot_review` を呼んでから、1 回枠を予約（`reserve_review`）して fix-check の担当を起動する。同じ欠陥を持ち、1 回枠も消費する。`main` は `ValueError` を終了コード 2 にし、理由に `verifier.failure_category` を使う
- review-fix-planning の手順（`references/execution.md` 59 行）は、fix-check の保存先 `FIX_STAGING` を起動の前に作ると書いている。テストの fixture（`test_run_roles.py` の `inputs`）も作っている
- review-verify の手順（`references/fix-check.md` 19 行）は、`review_target.py resolve` の `review_dir` を保存先にすると書くが、いつ作るかを書いていない。`resolve` は「保存先（存在しなくてよい）」を返す（`review_target.py:414-421`）。cycle の手順（`references/cycle.md` 33 行）は「PR照合・保存先のリンク/書込み可否の確認後、必要な D-10 ディレクトリを作る」
- `test_dispatch.py` の fixture `verification_input` は、`review_dir` に存在しないパス（`tmp_path / "review"`）を渡している。fixture `scenario` は作っている

## 受け入れ条件（Issue #177）

| ID | 条件 |
| --- | --- |
| A-1 | 外部の担当の起動と runner の成果物の作成より前に、`review_dir` が既存のディレクトリであること、`verified` が無いかディレクトリであることを検査する。既存のリンクの拒否を弱めない |
| A-2 | 保存できなければ入力不備として非 0 で終了し、adapter を起動せず、run/output-dir・保存先・参照先・既存のファイルを変えない。各負例は異常を 1 つだけ入れ、状態の全体を比較する |
| A-3 | 保存先を暗黙に作らず、通常ファイルを削除・置換しない。呼び出し側の PR 照合と root の準備を前提にする |
| A-4 | 正常な root と未作成の `verified` では、外部の起動と accept の保存が成功し続ける |
| A-5 | 起動の後に保存先が消えた・変わった場合の accept の拒否、snapshot の全体の照合、停止の確認を保つ |
| A-6 | fix-check の手順に root の準備の時点を合わせる。文面の一致だけのテストは足さない |

## 判断（決定記録）

各項目に、選択した案・検討した別案・選択理由・委任の指示または停止の条件を書く。

### D-1 検査を置く関数

- 選択した案: `dispatch.py` の `check_review_directories` を「起動の前の保存先の検査」にする。いまのリンクの検査を `reject_review_links` に分けて、`check_review_directories` はそれを呼んだ後に root と `verified` の種類を確かめる。`snapshot_review` は `reject_review_links` だけを呼ぶ（いまと同じ挙動）
- 検討した別案:
  1. `check_review_directories` をそのまま強め、`snapshot_review` からも呼ぶ
  2. 新しい関数を作り、`dispatch()` からだけ呼ぶ
- 選択理由:
  - `run_roles.py` の `fix_context` は予約と起動の前に `check_review_directories` を呼んでいる。この名前の関数に検査を入れれば、`run_roles.py` を変えずに同じ欠陥（と 1 回枠の消費）も防げる。別案 2 は `run_roles.py` に同じ欠陥を残す
  - 別案 1 では、起動の後の snapshot（`review_changes`）が、`verified` が通常ファイルに変わったときに例外になり、変わったパスではなく `<review snapshot unavailable>` を出す。拒否は保たれるが、利用者に見える理由が粗くなる。分ければ、起動の後の照合はいまのまま変わったパスを列挙する
- 委任の指示・停止の条件: `run_roles.py` のコードは変えない（#155 で決めた呼び出し側の接続を変えない）。`run_roles.py` への効果はテストで確かめる（D-6）

### D-2 検査の条件

- 選択した案: `lstat` で判定する。root は `S_ISDIR` でなければ拒否する（無い、通常ファイル、祖先が通常ファイルで `NotADirectoryError`、を含む）。`verified` は `FileNotFoundError` なら通し、`S_ISDIR` なら通し、それ以外の種類（通常ファイル・FIFO など）は拒否する。リンクは先に `reject_review_links` が拒否する。root を読めない（`PermissionError`）など、`verified` の `lstat` のその他の `OSError` は、そのまま上げる（`main` が終了コード 2 にする）
- 検討した別案: `os.access(W_OK)` で書き込み権限も確かめる。`Path.is_dir()` で判定する
- 選択理由: Issue の条件は root の存在と種類、`verified` の種類に限られる。`os.access` は root 権限・ACL・読み取り専用の mount で実際の書き込みの成否と一致しないことがあり、誤った拒否・通過を生む。`is_dir()` はリンクを辿るので、リンクの拒否と別の観測になる
- 委任の指示・停止の条件: 書き込み権限の検査は対象外（「対象外」）

### D-3 `self` の割り当てにも適用する

- 選択した案: 割り当てに関係なく、`dispatch()` の起動の前に検査する
- 検討した別案: 外部の担当に割り当てたときだけ検査する
- 選択理由: `self` でも司令塔は同じ `review_dir/verified/` に保存する（`fix-check.md` の「保存する結果」）。`run_workflow` は `self` でも成果物を作るので、A-1 の「runner の成果物の作成より前」に当たる。割り当てで入力の条件を変えると、手順が割り当てに依存する
- 委任の指示・停止の条件: なし

### D-4 終了コードと stderr

- 選択した案: `ValueError` で拒否する（`main` が終了コード 2）。文を `REQUEST_ERRORS` に足し、stderr にパスを含まない分類として出す: `review_dir must be an existing directory`、`verified must be absent or a directory`
- 検討した別案: 新しい例外の型と終了コードを足す。いまのリンクの文も `REQUEST_ERRORS` に足す
- 選択理由: `fix-check.md` は終了コード 2 を「設定・入力の誤り」と定めており、保存先の不備は入力の誤りに当たる。`run_roles.py` も `ValueError` を終了コード 2 にし、同じ `failure_category` で理由を出すので、呼び出し側を変えずに同じ文が出る。リンクの文は Issue の対象外で、変えない
- 委任の指示・停止の条件: なし

### D-5 手順書（A-6）

- 選択した案: review-verify の `references/fix-check.md` を直す
  - 19 行: PR の照合と保存先のリンクの確認の後、dispatch の前に `OUTPUT_REVIEW_DIR` を作る（cycle の「新規成果物の保存先」と同じ時点）。`verified/` は作らなくてよい。起動の後に作った保存先は受け取れない
  - 36 行: dispatch は起動の前に、`review_dir` が既存のディレクトリで、`verified` が無いかディレクトリであることを確かめ、満たさなければ担当も成果物も作らない。保存先を作らない
  - 41 行の終了コード 2 に、保存先の不備を含める
- 検討した別案: review-fix-planning の `references/execution.md` も直す
- 選択理由: execution.md 59 行は既に「保存先は起動の前に作っておく」と書き、82 行の「予約より前に止まる誤り」の「fix-input の誤り」が `review_dir` の不備を含む。変える記述が無い
- 委任の指示・停止の条件: 文面の一致のテストは足さない（AGENTS.md「テストの採用基準」）

### D-6 テスト

- 選択した案:
  - `test_dispatch.py`: fixture `verification_input` で `review_dir` を作る（新しい入力の条件に合わせる）。負例は、root が無い・root が通常ファイル・`verified` が通常ファイル、の 3 つを、外部の担当と `self` の 2 つの割り当てで、`main` から実行する。adapter を読み込んだら失敗する loader を渡し、終了コード 2、stderr の分類、`tmp_path` 全体の状態（パス・種類・mode・bytes・リンク先）が前後で同じことを確かめる。起動の後に `verified` を通常ファイルにした場合は、accept が終了コード 1 で、変わったパス `verified` を列挙し、ファイルを残すことを確かめる（Issue の再現 6 の起動の後の版。D-1 の分割の理由の確認）
  - `test_run_roles.py`: `run_roles.run` の self-review で、fix-check の保存先が無い・`verified` が通常ファイル、の 2 つで、予約の前に `ValueError` で止まり、adapter が起動されず、planning の `activities` が空のまま、run の出力先とロックが作られないことを確かめる
  - 正常系（A-4）と起動の後の拒否（A-5）は、既存のテスト（`test_accept_saves_the_tool_output_unchanged_with_the_observed_verifier`、`test_unchanged_existing_results_and_temporary_probe_outputs_are_allowed`、`test_accept_exits_2_when_the_review_directory_is_missing`、`test_review_directory_changes_are_rejected_before_publishing` ほか）を変えずに通す
- 検討した別案: Issue の再現を `dispatch()` の関数の呼び出しだけで確かめる。`run_roles.py` はテストしない
- 選択理由: `main` から実行すると、終了コード・stderr・出力先の不作成を、利用者の入口で確かめられる。`run_roles.py` の挙動は D-1 で意図して変えるので、1 回枠を消費しないこと（安全の条件）をテストで守る
- 委任の指示・停止の条件: なし

## 対象外

- 書き込み権限の事前の検査（D-2）
- `accept` の `mkdir`・一時ファイルの作成の失敗の扱い（起動の前の検査で、通常の経路では `verified` が通常ファイルの状態に至らない。起動の後の変更は snapshot の照合が拒否する）
- 検査と snapshot の間、snapshot と起動の間の同時変更（`check_review_directories` の「同時変更の sandbox ではない」のまま）
- リンクの拒否の文、`run_roles.py` のコード、review-fix-planning の手順書

## 要件と経路の対応

| 経路 | 判定 | 観測する結果と確かめ方 |
| --- | --- | --- |
| `dispatch.main` → `dispatch()` の起動の前（外部・`self`） | 修正する | 3 つの単一の異常 × 2 つの割り当てで、終了コード 2・分類の文・adapter 未起動・`tmp_path` 全体の不変（A-1・A-2・A-3） |
| `run_roles.run`（self-review）→ `fix_context` → 予約 | 修正する（コードは `dispatch.py` だけ） | 2 つの単一の異常で `ValueError`、adapter 未起動、`activities` が空、出力先とロックが無い |
| `snapshot_review`（起動の前・後） | 既に満たす（変えない） | リンクの拒否はそのまま。起動の後に `verified` を通常ファイルにすると accept が 1 で `verified` を列挙（A-5） |
| `accept` の root の消失・変更・停止未確認 | 既に満たす | 既存テストを変えずに通す（A-5） |
| 正常な root と未作成の `verified` | 既に満たす | 既存の受け取りのテストを通す（A-4） |
| `fix-check.md` の手順 | 修正する | 差分を読み、cycle の保存先の時点・`dispatch.py` の検査と一致することを確かめる（A-6） |
