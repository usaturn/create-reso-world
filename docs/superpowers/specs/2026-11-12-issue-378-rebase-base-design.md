# Issue #378: issue-to-pr における未 push 時の条件付き base 前進追随（rebase と再検証）設計

## 管理・実行許可

- 状態: `draft`（内容の承認は記録していない。`issue-to-pr` による実行許可に基づき `draft` のままコミットする）
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/378
- 対象リポジトリ: `usaturn/create-reso-world`（`DOCS_SEPARATE = false`、PR の base: `main`）
- 捕捉した基準 base: `usaturn/create-reso-world` / `origin` / `refs/heads/main` / `c3a8e113c3af010fac94820266b93e107d6dbfaf`
- 先行・競合の確認:
  - 先行の #353（`issue-review-steps`、PR #376）と #355（`herdr-merge`、PR #413）はどちらも `state_reason=completed` で close 済み
  - #378 は親 Issue を持たないボード外の follow-up であり（#349 の「ボード外の follow-up と所有」で確認）、open PR・マージ済み対応 PR・`refs/heads/agent-claims/issue-378`・既存の worktree / branch は着手時に存在しない
  - 同じ `.agents/skills/issue-to-pr/SKILL.md` を対象とする #417 は 4 章（レビュー・実装ランナー実行中の checkout 書き込み禁止ガイダンス）を対象としており、未着手（claim・PR・branch なし）であることを確認した。本変更では 4 章に触れない
- 利用者の指示（2026-11-12、原文）:
  > `/issue-to-pr #378 --merge`
  > `--spec-review pi_opencode-go_deepseek4-flash_max`
  > `--implement pi_opencode-go_deepseek4-flash_max`
  > `--assign implement=pi_opencode-go_deepseek4-flash_max`
  > `--assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`
  > `途中でメインがマージされたら、追随して作業を止めずに続行してください。`
- 許可された範囲:
  - `issue-to-pr` スキルの通常の委任（推奨案での設計判断、検証・commit・push・PR 作成の継続）および `--merge`（PR 修正ループの `finalize.py` によるマージと関連 Issue の更新まで）
  - この run 限りの追加委任: 本作業中に `origin/main` が前進した場合、未 push であれば新 SHA への rebase・捕捉 base の更新・再検証を行って続行し、PR 作成後であれば公開済みブランチを書き換えずに `pr-review-fix-loop` / `review-fix-planning` の既存の `base_moved` 再検証経路で続行する（検査や再検証の省略は許可しない）
- 事前検査（2 章 3 の helper 出力）:
  - `loop.py check-options`: `max_cycles: 3`（既定の適用）、`template: "/workspaces/reso-world/.devcontainer/agent-runner.toml"`（既定の適用）、`config: null`（既定の適用）、`assign.implement: ["pi_opencode-go_deepseek4-flash_max"]`（利用者指定）、`assign.inspect: ["devin_swe2_max", "pi_opencode-go_deepseek4-flash_max", "claude-code_opus_default"]`（利用者指定）、`assignments.fix.self-review: {"agents": ["self"], "fallback": []}`（既定の適用）、`assignments.fix.fix-check: {"agents": ["self"], "fallback": []}`（既定の適用）、各 `fallback: []`（既定の適用）
  - `implement_task.py check`: `assignment: {"agents": ["pi_opencode-go_deepseek4-flash_max"], "fallback": []}`（`agents` は利用者指定 `--implement`、`fallback: []` は設定の保持）、`self: false`、`template: "/workspaces/reso-world/.devcontainer/agent-runner.toml"`、`config: "/home/vscode/.config/agent-runner/config.toml"`
  - `review_spec.py check`: `assignment: {"agents": ["pi_opencode-go_deepseek4-flash_max"], "fallback": []}`（`agents` は利用者指定 `--spec-review`、`fallback: []` は個人設定の保持）、`self: false`、`template: "/workspaces/reso-world/.devcontainer/agent-runner.toml"`、`config: "/home/vscode/.config/agent-runner/config.toml"`
  - `--design-review`: 未指定（起動しない）

## 目的と非目標

### 目的（観測できる結果）

`issue-to-pr` の実行中に捕捉済みの base（`CODE_BASE_SHA`、および `DOCS_SEPARATE != false` のときの `DOC_BASE_SHA`）が `origin` 上で前進したとき、**まだどの作業ブランチも push していない**ことを前提に、#350 R11 の裁定条件（fast-forward・所有ファイルおよび変更ファイルとの非重複・衝突なし・設計前提の不変・回数上限内）を満たせば新しい base へ rebase して捕捉値を更新し、**新しい `(base, HEAD)` の組み合わせで検証をやり直したうえで**公開・PR 作成まで続行できるようにする。

### 非目標・変更しない安全境界

- **未検証の `(base, HEAD)` を公開・マージしない安全条件（#196）は変えない。** rebase 後に再検証を通さずに `publish`・`pr` が成功する経路を作らない
- **停止したままの経路で捕捉値を緩めない。** `resolve_base.py --expected-sha` は引き続き base の移動で終了コード 2 を返し、`recheck_bases` が失敗したブロックはそのまま停止する
- **push 済みのブランチを rebase・force push しない。** 作業ブランチのいずれかが `origin` に存在する状態（`publish` での push 後、および PR 作成後）での base 移動は `issue-to-pr` の rebase 対象外とし、push 後〜PR 作成前は停止して報告し、PR 作成後の `--merge` ループでは既存の `review-fix-planning` / `finalize.py` の `base_moved` 再検証経路に委ねる
- **`--base` の選択・要求照合・統合ブランチでの `--merge` 無効化（`merge-disabled.txt`）は変えない**
- **`implement_task.py`（#389・#390 が所有）および `SKILL.md` 4 章（#417 が対象とする節）は変更しない**

## 編集範囲

変更するファイル:

- `.agents/skills/issue-to-pr/scripts/resolve_base.py`
- `.agents/skills/issue-to-pr/SKILL.md`（2 章 6・5 章、および矛盾防止のための 2 章 3・停止時の報告の最小注記のみ。4 章は編集しない）
- `.agents/skills/issue-to-pr/tests/test_resolve_base.py`
- `.agents/skills/issue-to-pr/tests/test_base_workflow.py`
- `docs/superpowers/specs/2026-11-12-issue-378-rebase-base-design.md`（本書）
- `docs/superpowers/plans/2026-11-12-issue-378-rebase-base.md`（Plan）

## 設計

### 1. 状態ファイルと「黙った書き換え」を防ぐ連鎖

`SESSION` ディレクトリ内のファイルで初期捕捉・前進履歴・再検証の対応を一貫して検査する。`resolve_base.py` は `uv run --no-project python` で実行されるため、Python 標準ライブラリと既存の同ディレクトリモジュール（`git_env.py`・`resolve_issue.py`）だけで実装する。

1. **初回捕捉（`--write-state <path>`）**
   - `capture` ブロックはリダイレクト上書き（`>`）ではなく `resolve_base.py ... --write-state "$SESSION/code-base.json"`（文書分離時は `--write-state "$SESSION/docs-base.json"` も）を呼ぶ。
   - `--write-state` は対象ファイルと対になる初期固定ファイル（`code-base.initial.json` / `docs-base.initial.json`）の両方がまだ存在しないこと、symlink でないことを確かめて排他作成（`"x"` モード）する。既に存在する場合は終了コード 2 で拒否する（`capture` の再実行による黙った上書きを防止）。
   - `code-base.json`・`docs-base.json` の JSON 形式は従来どおり `{"repo", "remote", "branch", "ref", "sha"}` の 5 キーを維持し、既存の読み取り箇所との互換性を保つ。
2. **前進検査（`--inspect-advance`）**
   - 呼び出し:
     ```text
     resolve_base.py --inspect-advance --session "$SESSION" \
       --owned-paths-file "$SESSION/owned-paths.txt" \
       --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
       --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
       [--max-advances 3]
     ```
   - `$SESSION/target.json`・`code-base.json`・`code-base.initial.json`（および `DOCS_SEPARATE` が真なら `docs-base.json`・`docs-base.initial.json`）を読み、次の機械的条件をすべて検査する（作業ツリーや state ファイルは書き換えず、オブジェクト取得のみ従来どおり `--no-tags --no-write-fetch-head --refmap=` で行う）:
     1. **未 push 条件:** `CODE_BRANCH`（および `DOCS_SEPARATE` が真なら `DOC_BRANCH`）について、対象 checkout の `origin` に対する `git ls-remote --refs origin refs/heads/<branch>` が空であること。1 つでも remote に存在する場合は「push 済み」として終了コード 2 で拒否する。
     2. **移動の有無:** `code`（および `DOCS_SEPARATE` が真なら `docs`）の remote 先端 SHA を取得し、少なくとも一方が捕捉済み `sha` から変化していること。どちらも変化していなければ終了コード 2 で拒否する。
     3. **前進回数の上限:** `$SESSION/base-advances.jsonl` の既存記録を読み、前進する各リポジトリの累計前進回数が `max_advances`（既定 `3`）未満であること。上限に達していれば終了コード 2 で拒否する。
     4. **fast-forward 条件:** 前進した各リポジトリで `git merge-base --is-ancestor <old_sha> <new_sha>` が成立すること。巻き戻しや force push による非 fast-forward 変化は終了コード 2 で拒否する。
     5. **所有パスとの非重複:** `$SESSION/owned-paths.txt`（1 行 1 パス、リポジトリ相対パス。空ファイル可だがファイル自体の存在は必須、`..` や絶対パスは拒否）を読み、`code` が前進した場合は `<old_sha>..<new_sha>` の変更ファイル（`git diff --name-only -z`）が所有パス（ファイル一致またはディレクトリ包含の双方向）と 1 件も重ならないこと。
     6. **worktree の状態・変更非重複・非衝突:** 対象 worktree（`CODE_ROOT` / `DOC_ROOT`）が既に存在する場合、その worktree が対象 checkout の共通 Git ディレクトリに属する先頭ディレクトリであり、期待するローカルブランチを指し、`git status --porcelain --untracked-files=normal` が空で、`<old_sha>` が `HEAD` の祖先であり、`<old_sha>..HEAD` にマージコミットが無く（`git rev-list --merges` が空）、`<old_sha>..HEAD` の変更ファイルが `<old_sha>..<new_sha>` の変更ファイルと重ならず、`HEAD != old_sha` のとき `git merge-tree --write-tree HEAD <new_sha>` が終了コード 0 で衝突しないこと。
   - すべて満たす場合は、各対象の `old_sha`・`new_sha`・`<old_sha>..<new_sha>` のコミット一覧（SHA と件名）・変更ファイル一覧・`owned-paths.txt` の SHA-256 を含む検査結果 JSON を標準出力に出して終了コード 0 を返す。1 つでも満たさない場合は標準出力を空にし、旧/新 SHA と不成立理由を標準エラーに出して終了コード 2 を返す。
3. **前進適用と rebase（`--advance`）**
   - controller は `--inspect-advance` が出力したコミット一覧と変更ファイル一覧を確認し、設計の前提（外部仕様・共有インターフェース・preflight 条件・適用される `AGENTS.md` の規則）が変わっていないことを確かめ、根拠を `$SESSION/advance-premise.txt` に 1 行以上で書く。前提が変わっている・判断できない場合は `--advance` を呼ばずに停止する。
   - 呼び出し:
     ```text
     resolve_base.py --advance --session "$SESSION" \
       --inspection "$SESSION/advance-inspection.json" \
       --owned-paths-file "$SESSION/owned-paths.txt" \
       --premise-file "$SESSION/advance-premise.txt" \
       --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
       --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
       [--max-advances 3]
     ```
   - `--advance` は `--premise-file` が空でない通常ファイルであること、`owned-paths.txt` の SHA-256 が `--inspection` と一致すること、および live の remote SHA が `--inspection` に記録された `new_sha` と一致すること（検査後にさらに base が動いていないこと）を含め、`--inspect-advance` の全条件を再検証する。
   - 対象 worktree が存在する場合は `git -C <worktree> rebase --onto <new_sha> <old_sha>` を実行する。万一 rebase が非 0 で失敗した場合は直ちに `git -C <worktree> rebase --abort` を実行し、既に片方の worktree を rebase していた場合も元の `old_head` へ戻してから、state ファイルを更新せずに終了コード 2 で停止する。
   - 成功したら、`SESSION` 内の古い `$SESSION/reverified.json`・`$SESSION/checks.json`・`$SESSION/code-sha.txt`・`$SESSION/docs-sha.txt` を削除（無効化）し、`$SESSION/base-advances.jsonl` に監査レコード（`repo`・`branch`・`ref`・`old_sha`・`new_sha`・`phase`（`pre_worktree` または `worktree`）・`old_head`・`new_head`・`changed_files`・`premise_note`）を追記したうえで、`code-base.json`（および該当時は `docs-base.json`）を一時ファイルからの `os.replace` で一括更新する。
4. **再検証の実行と記録（`--reverify`）**
   - 呼び出し:
     ```text
     resolve_base.py --reverify --session "$SESSION" \
       --commands-file "$SESSION/reverify-cmds.json" \
       --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}"
     ```
   - `$SESSION/reverify-cmds.json` は 1 件以上のコマンド配列（`[["uv", "run", ...], ["bash", "scripts/check-layout.sh"]]` のような文字列リストの配列。空白を含むパスでも分割ずれを起こさない）を受け取る。
   - 実行前に `code-base.initial.json` から `base-advances.jsonl` を経て現在の `code-base.json`（および `docs-base.json`）に至る `old_sha -> new_sha` の連鎖が整合していること、remote の先端が現在の `code-base.json` / `docs-base.json` と一致すること、`CODE_ROOT`（および `DOC_ROOT`）が clean で各 base SHA が `HEAD` の祖先であることを確かめる。
   - 各コマンドを `CODE_ROOT` を cwd として（継承した `GIT_*` を除去した環境で）順に同期実行し、標準出力・標準エラーを `$SESSION/reverify-<番号>.log` に保存する。終了コードが非 0 のコマンドがあれば `$SESSION/reverified.json` を作らず（既存があれば消し）終了コード 2 で停止する。
   - 全コマンド成功後、再度 worktree が clean で `HEAD` と remote base SHA が変化していないことを確かめ、`$SESSION/reverified.json`（`code_base_sha`・`code_head_sha`・`docs_separate`・`doc_base_sha`・`doc_head_sha`・`advance_count`・`commands`（各 `argv`・`exit_code: 0`・`log_path`））と、`finalize.py` 互換の `$SESSION/checks.json`（`{"head": code_head_sha, "base": code_base_sha, "commands": [{"argv": ..., "exit_code": 0}]}`）を一括書き出しする。
5. **公開前ゲート（`--check-publish-gate`）と PR 作成前ゲート（`--check-pr-gate`）**
   - `--check-publish-gate`: `publish` ブロックで `recheck_bases` の直後・`scan-before-push.sh` の前に呼ぶ。
     - `code-base.json["sha"] == code-base.initial.json["sha"]`（かつ `DOCS_SEPARATE` が真なら `docs-base.json["sha"] == docs-base.initial.json["sha"]`）であり、`base-advances.jsonl` が存在しない場合（= 一度も前進していない通常の run）は即座に終了コード 0 を返す。
     - それ以外の場合（1 回でも前進した、または `code-base.json` が初期値と異なる場合）は、(a) `initial.sha` から `base-advances.jsonl` の連鎖が現在の `state.sha` と完全一致すること（手動書き換えやログ削除の検出）、(b) `reverified.json` が存在し、`advance_count`・`code_base_sha`・現在の `CODE_ROOT` `HEAD`（および `DOCS_SEPARATE` 時は `doc_base_sha`・`DOC_ROOT` `HEAD`）と完全一致し、worktree が clean で全コマンドの `exit_code == 0` と実在する `log_path` を持つこと、を検証する。不成立なら終了コード 2 で `publish` を止める。
   - `--check-pr-gate`: `pr` ブロックで `recheck_bases` の直後・`gh pr create` の前に呼ぶ。
     - `--check-publish-gate` の検証（かつ `code-sha.txt` / `docs-sha.txt` が `reverified.json` の HEAD SHA と一致すること）に加え、`base-advances.jsonl` に記録された各前進について、コード側リポジトリの前進なら `--code-pr-body` に各 `old_sha[:7]`・`new_sha[:7]` と再検証したコマンド（各 `argv[0]` のベース名またはコマンド列）が含まれること、分離された文書側リポジトリの前進なら `--doc-pr-body` に各 `old_sha[:7]`・`new_sha[:7]` が含まれることを検査する。不成立なら PR 作成前に終了コード 2 で止める。

### 2. `SKILL.md` の手順更新（2 章 6 と 5 章）

1. **2 章 6（`capture` と未 push 時の base 前進追随）**
   - `capture` ブロックの `resolve_base.py` 呼び出しを `--write-state "$SESSION/code-base.json"` / `--write-state "$SESSION/docs-base.json"` に更新する。
   - `recheck_bases` の説明を更新し、移動を観測したときの扱いを次の 2 通りに明確化する:
     - **まだどの作業ブランチも push していないとき（worktree 作成直前・実装の Task 境界・5 章の検証前・`diff`・`publish` の push 前）:** `$SESSION/owned-paths.txt`（Issue・Plan の所有パス一覧）を用意して `base-workflow:inspect-advance` を実行し、機械的条件（未 push・fast-forward・非重複・非衝突・上限 3 回未満）と設計前提の不変を確認できれば `$SESSION/advance-premise.txt` を書いて `base-workflow:advance` で rebase・再捕捉し、5 章の検証（`base-workflow:reverify`）からやり直して続行する。条件を満たさない場合・上限超過・前提変化は新 SHA を採用せず停止する。
     - **いずれかの作業ブランチを push 済みのとき（`publish` の push 開始後・`pr` ブロック・PR 作成後）:** rebase せず従来どおり停止して旧/新 SHA・公開済み資源を報告する（PR 作成後の `--merge` ループはループ側の既存の `base_moved` 再検証経路で扱う）。
   - 実行可能な `<!-- base-workflow:inspect-advance -->` と `<!-- base-workflow:advance -->` の Bash ブロックを 2 章 6 に追加する。
2. **5 章（検証・`reverify`・`diff`・`publish`・`pr`・PR 本文）**
   - 5 章冒頭の検証手順に、長い実装の後の二度手間を防ぐため「最終検証の前に `recheck_bases` を確認し、未 push で base が前進していれば先に 2 章 6 の rebase を行ってから検証する」こと、および 1 回でも base 前進追随を行った run では検証を `<!-- base-workflow:reverify -->`（`$SESSION/reverify-cmds.json`）で実行して `$SESSION/reverified.json` と `$SESSION/checks.json` を記録することを明記する。
   - `publish` ブロックに `--check-publish-gate`、`pr` ブロックに `--check-pr-gate` を組み込む。
   - PR 本文の記載項目に「base 前進追随を行った run では、rebase したこと・旧/新の base SHA・やり直した検証コマンドと結果を記載する」ことを追加する。
3. **2 章 3 と停止時の報告の整合注記**
   - 2 章 3 の「base の取得をやり直して SHA を差し替えない」に「（2 章 6 の未 push 条件付き前進追随の手順を除く）」を補い、「停止時の報告」の「捕捉後の移動」に「（2 章 6 の条件を満たして rebase・再検証する場合を除く）」を補う。3 章（想定された停止でのペイン名維持）と 4 章には触れない。

### 3. テスト方針（`AGENTS.md`「テストの採用基準」との照合）

`SKILL.md` の固定文言を文字列照合するテスト（F）や、引数不足・ヘルプ表示の検査（L）、同じ守りの別ファイル重複（D）は書かない。壊れても黙って損害（未検証の組み合わせの公開、push 済み履歴の書き換え、競合・重複ファイルの上書き）が生じる S の条件だけを、層ごとに代表 1 件ずつテスト化する。

1. `.agents/skills/issue-to-pr/tests/test_resolve_base.py`:
   - 既存の 7 テスト（`test_base_movement_rejected` を含む）を維持する。
   - 新規 S テスト 1 件（`test_advance_guards_and_state_chain`）: `--write-state` の二重書き込み拒否、非 fast-forward 変化の拒否、push 済みブランチの拒否、`owned-paths.txt` 重複・worktree 変更重複・`merge-tree` 衝突・未コミット変更の拒否（いずれも worktree HEAD と `code-base.json` が不変であること）、上限 3 回超過（4 回目）の拒否、および条件を満たす 3 回までの前進で rebase と `code-base.initial.json -> base-advances.jsonl -> code-base.json` の連鎖が成立することを実 Git で検証する。
2. `.agents/skills/issue-to-pr/tests/test_base_workflow.py`:
   - 既存のケース（push 後の PR 作成前に base が動いたときに停止する `test_resumed_shell_stops_before_pr_creation_when_base_moved` を含む）をすべて維持する。
   - 新規 S テスト 1 件（`test_unpushed_base_advance_requires_reverify_and_pr_record`）: `SKILL.md` から抽出した実ブロック（`input`・`target`・`capture`・`worktree`・`diff`・`inspect-advance`・`advance`・`reverify`・`publish`・`pr`）を実行し、(a) `code-base.json` の直接書き換えによるゲート回避が `publish` で拒否されること、(b) `advance` 後に `reverify` を省くと `publish` が終了コード 2 で止まり remote に push されないこと、(c) `reverify` 実行後に PR 本文に旧/新 SHA が無ければ `pr` が `gh pr create` の前に止まり、旧/新 SHA と再検証コマンドを記載すれば PR 作成まで成功して新しい base 上のコミットが公開されることを検証する。

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 提案 1（未 push 時の条件付き rebase + 再検証による続行）と、5 章の最終検証前 `recheck_bases` 確認（提案 3 の所有範囲内適用）を組み合わせる | (a) 提案 2（停止のまま再開手順だけ書く）<br>(b) `recheck_bases` 内で自動 rebase する<br>(c) `implement_task.py` にも base 検査を足す | (a) は並列 run の直列化と手動往復が残る。(b) は設計前提の確認と再検証を経ずに `publish` 内で push まで進む危険がある。(c) は `implement_task.py` が現在 open の #389/#390 の所有であり競合する。明示ブロック（`inspect-advance` / `advance` / `reverify`）と 5 章検証前の確認なら安全条件と所有境界の両方を守れる | `issue-to-pr` 1 章の推奨案委任および Issue #378 の「提案（案）」 |
| D2 | `capture` の `--write-state` で `code-base.initial.json` を排他保存し、`--advance` の `base-advances.jsonl` と `--reverify` の `reverified.json` を `publish`・`pr` のゲート（`--check-publish-gate`・`--check-pr-gate`）で機械照合する | (a) 通常の `resolve_base.py` を再実行して `code-base.json` を上書きし、再検証は `SKILL.md` の文章だけで求める<br>(b) `code-base.json` のスキーマ自体に履歴配列を足す | (a) は捕捉値の黙った差し替えと区別できず、再検証や PR 本文記載を忘れたまま公開する経路が残る（Issue の受け入れ「検証をやり直さずに公開・マージする経路が無い（テストで固定する）」を満たせない）。(b) は既存の 5 キー JSON を読む箇所や既存テストを壊す。別ファイル連鎖なら既存互換を保ちつつ改ざん・省略を確実に拒否できる | Issue #378 の「範囲と除外」「受け入れ」。連鎖不整合・再検証未実施時は終了コード 2 で停止 |
| D3 | 続行条件を (1) 全作業ブランチが `origin` に未 push、(2) fast-forward（`is-ancestor`）、(3) `owned-paths.txt` および `<old_sha>..HEAD` 変更ファイルとの非重複、(4) clean な線形 worktree で `merge-tree` 非衝突かつ `rebase --onto` 成功、(5) `--premise-file` への設計前提不変の記録、(6) 各対象リポジトリあたり最大 3 回まで、とする | (a) 回数上限を設けない、または 1 回だけにする<br>(b) `owned-paths.txt` を見ず `merge-tree` 非衝突だけで通す | (a) 無制限は活発な並列マージ下で再検証ループが収束せず実行予算を浪費し、1 回は 3 並列 run で不足する。3 回は `review-fix-planning` / `pr-review-fix-loop` の `base_moved` 上限（サイクルあたり 3 回）と揃う。(b) 同一ファイル内の別行変更は `merge-tree` が通っても意味的競合を起こしやすいため、R11 の「所有ファイルとの重なりが無く衝突しなければ」を文字どおり機械検査する | #350 R11 の利用者裁定・Issue #378 本文。いずれか不成立・上限到達時は停止 |
| D4 | `--base` で指定された統合用ブランチ（例: `feat/plugin-v2`）にも同じ条件付き rebase・再検証規則を適用し、`CODE_BASE_BRANCH` 名・`required-bases.txt`・`merge-disabled.txt` は不変とする | 既定の `main` だけに限定し、統合用ブランチは常に停止させる | Issue #378 の背景事例 #100 自体が統合用ブランチ `feat/plugin-v2` での兄弟 PR マージによる前進であり、統合用ブランチこそ並列の子 Issue が順次マージされる場面が多い。fast-forward・非重複・再検証の安全条件は `main` と同じように成り立ち、`merge-disabled.txt` を維持するため誤マージの危険も無い | Issue #378「変更してはいけない」（統合 branch に同じ規則を適用するかは Spec で決める） |
| D5 | `SKILL.md` の編集は 2 章 6・5 章と、2 章 3・停止時の報告の括弧注記に限る。4 章（#417）と `implement_task.py`（#389/#390）は編集しない | 4 章の runner 実装節にも base 再確認手順を書き足す | #349 の所有表で #378 の編集範囲は `SKILL.md` 2 章 6・5 章と `resolve_base.py`・同 tests に定められており、4 章は open の #417 が対象としているため節の衝突を避ける | #349 の所有境界。他 Issue の所有ファイルの変更が必要になった場合は停止 |
| D6 | `resolve_base.py` は Python 標準ライブラリと既存の同ディレクトリモジュール（`git_env.py`・`resolve_issue.py`）だけで実装し、外部パッケージを使わない | `pydantic` 等で JSON スキーマ検証を行う | `SKILL.md` の各ブロックが `uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py"` で起動するため、プロジェクト仮想環境外の標準ライブラリだけで動く必要がある | 既存の起動インターフェース仕様 |
| D7 | Spec レビュー担当・Plan Task 実装担当・ループ修正担当は利用者指定の `pi_opencode-go_deepseek4-flash_max`、ループ inspect 担当は `devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default` とし、実装は `self: false` のため `implement_task.py run` で Task ごとに直列委譲する。PR 本文の Issue 指定は `Closes #378` とする | `self` での直接実装、`Refs #378` | 2 章 3 の `check` で `self: false` と確定しており、4 章の表と「失敗を理由に `self` で引き取らない」規則に従う。#378 は `TARGET_REPO` 内のボード外 Issue でマージ後の rebuild・実機確認を残さないため 5 章の規則により `Closes #378` に当たる | 利用者の明示オプション指定。外部担当の `failed`・再試行上限到達・Spec レビュー失敗時は停止 |
