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

`issue-to-pr` の実行中に捕捉済みの base（`CODE_BASE_SHA`、および `DOCS_SEPARATE != false` のときの `DOC_BASE_SHA`）が `origin` 上で前進したとき、**まだどの作業ブランチも push していない**ことを前提に、#350 R11 の裁定条件（fast-forward・所有ファイルおよび変更ファイルとの非重複・衝突なし・`preflight` と `checkout_policy` を含む設計前提の不変・回数上限内）を満たせば新しい base へ rebase して捕捉値とシェル状態（`$SESSION/base-env.bash` を含む）を更新し、**新しい `(base, HEAD)` の組み合わせで必須検証をやり直したうえで**、利用者の再指示を待たずに公開・PR 作成まで続行できるようにする。

### 非目標・変更しない安全境界

- **未検証の `(base, HEAD)` を公開・マージしない安全条件（#196）は変えない。** rebase 後に必須検証の再実行を通さずに `publish`・`pr` が成功する経路を作らない
- **検査なしの SHA 差し替えを許さない。** `resolve_base.py --expected-sha`、`recheck_bases`、`scripts/scan-before-push.sh --expected-base-sha` 自体は引き続き base の移動で非 0 を返し、その Bash ブロック内の後続コマンド（古い SHA での `worktree add`・`diff`・`scan`・`push`・`gh pr create`）を即座に中断する。未 push 時はブロック中断後に run 全体を止めず 2 章 6 の前進追随フロー（`inspect-advance` → 前提確認 → `advance` → `reverify` → 中断した工程のやり直し）へ進み、push 済みまたは追随条件不成立のときだけ run 全体を停止して報告する
- **push 済みのブランチを rebase・force push しない。** 作業ブランチのいずれかが `origin` に存在する状態（`publish` での片方または両方の push 後、および PR 作成後）での base 移動は `issue-to-pr` の rebase 対象外とし、push 後〜PR 作成前は run を停止して報告し、PR 作成後の `--merge` ループでは既存の `review-fix-planning` / `finalize.py` の `base_moved` 再検証経路に委ねる
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

`SESSION` ディレクトリ内のファイルで初期捕捉・所有パス・前進履歴・必須検証・再検証結果の対応を一貫して検査する。`resolve_base.py` は `uv run --no-project python` で実行されるため、Python 標準ライブラリと既存の同ディレクトリモジュール（`git_env.py`・`resolve_issue.py`）だけで実装する。`DOCS_SEPARATE` は環境変数に頼らず、常に `$SESSION/target.json` の `document_repository != repository`（両方とも文字列であることを検証）から判定する。

1. **初回捕捉（`--write-state <path>`）とシェル状態の保存（`$SESSION/base-env.bash`）**
   - `capture` ブロックはリダイレクト上書き（`>`）ではなく `resolve_base.py ... --write-state "$SESSION/code-base.json"`（文書分離時は `--write-state "$SESSION/docs-base.json"` も）を呼ぶ。
   - `--write-state` は出力先 `<stem>.json` と対になる初期固定ファイル `<stem>.initial.json`（`code-base.initial.json` / `docs-base.initial.json`）の両方がまだ存在せず symlink でないことを確かめ、両方とも排他作成（`"x"` モード）で同じ JSON を書き出す。既にどちらかが存在する場合は終了コード 2 で拒否する（`capture` の再実行による黙った上書きを防止）。
   - `code-base.json`・`docs-base.json` の JSON 形式は従来どおり `{"repo", "remote", "branch", "ref", "sha"}` の 5 キーを維持し、既存の読み取り箇所との互換性を保つ。
   - `capture` ブロックは末尾で `TARGET_ROOT`・`TARGET_REPO`・`PARENT_ROOT`・`DOCS_SEPARATE`・`CODE_BASE_BRANCH`・`CODE_BASE_SHA`（および `DOCS_SEPARATE != false` 時の `DOC_BASE_SHA`）と `recheck_bases` 関数定義を `$SESSION/base-env.bash` に書き出す。終了コード 2 で中断した後の別シェルでも `source "$SESSION/base-env.bash"` で同じ変数と関数を復元できる。

2. **所有パスの定義と更新時点（`$SESSION/owned-paths.json`）**
   - 形式（UTF-8 の通常ファイル、symlink 不可）:
     ```json
     {
       "code": ["path/to/file_or_dir", "..."],
       "docs": ["docs/superpowers/specs/", "docs/superpowers/plans/"]
     }
     ```
   - 各要素は空でないリポジトリ相対 POSIX パスとし、先頭 `/`・空要素・`.`・`..` セグメント・NUL 文字を含むパスは終了コード 2 で拒否する（末尾 `/` は正規化して除去し、ルート全体を指す `/` や `""` は拒否する）。2 つのパス `a`・`b` の重複は `a == b` または `a` が `b/` 配下、または `b` が `a/` 配下（双方向のディレクトリ包含・ファイル一致）で判定する。
   - **空リスト禁止:** `code` は常に 1 件以上の配列であることを必須とし、空配列 `[]` は終了コード 2 で拒否する（空リストで所有ファイル重複検査を素通りさせない）。`DOCS_SEPARATE` が `true` のときは `docs` も 1 件以上の配列であることを必須とし、`DOCS_SEPARATE` が `false` のときは `docs` は省略または `[]` とする（`DOCS_SEPARATE=false` なのに `docs` に非空配列が渡された場合も混同防止のため終了コード 2 で拒否する）。
   - **生成元・更新時点と `code` / `docs` への振り分け:**
     1. **worktree 作成前（2 章 6、`capture` の直後）:** 司令塔が 2 章 5〜6 で確認した Issue 本文の「変更してよい」「変更候補」または対象モジュール/スキルディレクトリを `code` に入れ、Spec・Plan 保存先ディレクトリ（`"docs/superpowers/specs/"`・`"docs/superpowers/plans/"`）を `DOCS_SEPARATE=false` なら `code` に、`DOCS_SEPARATE=true` なら `docs` に入れて `$SESSION/owned-paths.json` を作成する。
     2. **Spec・Plan 作成後（4 章 3 の Plan コミット直後、実装開始前）:** リポジトリごとに振り分けて `$SESSION/owned-paths.json` を更新する:
        - `DOCS_SEPARATE=false`（`DOC_ROOT == CODE_ROOT`）のとき: 初期の `code` パス、Plan の全 Task の `allowed_files`、およびコミットした Spec・Plan のファイルパスの和集合を `code` に入れ、`docs` は `[]` とする。
        - `DOCS_SEPARATE=true`（`DOC_ROOT != CODE_ROOT`）のとき: 初期の `code` パスと `CODE_ROOT` を対象とする実装 Task の `allowed_files` の和集合を `code` に入れ、初期の `docs` パスと `DOC_ROOT`（`create-reso-world` 側）にコミットした Spec・Plan のファイルパス（および `DOC_ROOT` 側の文書 Task があればその担当パス）の和集合を `docs` に入れる（別リポジトリのパスを他方のリストに混ぜない）。

3. **前進検査（`--inspect-advance`）**
   - 呼び出し:
     ```text
     resolve_base.py --inspect-advance --session "$SESSION" \
       --owned-paths-file "$SESSION/owned-paths.json" \
       --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
       --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
       [--max-advances 3]
     ```
   - `$SESSION/target.json` から `TARGET_ROOT = target.json["code_root"]`・`PARENT_ROOT = target.json["parent_root"]`・`DOCS_SEPARATE` を読み、既存と同じ checkout 検証を行ったうえで、`code-base.json`・`code-base.initial.json`（および `DOCS_SEPARATE` が `true` なら `docs-base.json`・`docs-base.initial.json`）を読む。
   - **worktree 未作成時（`pre_worktree`）の Git 実行先:** remote 照会（`ls-remote`）・オブジェクト取得（`fetch --no-tags --no-write-fetch-head --refmap=`）・`merge-base --is-ancestor`・コミット一覧取得・base 間の変更ファイル取得（`git diff --name-only -z <old_sha> <new_sha>`）はすべて常設の **`TARGET_ROOT`**（`code` 側）および **`PARENT_ROOT`**（`DOCS_SEPARATE=true` の `docs` 側）で実行する。`--code-root` / `--doc-root` がまだ存在しない段階（worktree 作成直前）でも失敗しない。
   - `--code-root`（および `DOCS_SEPARATE=true` 時の `--doc-root`）の存在状態は次で判定する:
     - どちらもディスク上に存在しない（symlink でもない）場合: `phase = "pre_worktree"`。
     - どちらもディスク上に実ディレクトリとして存在する場合: `phase = "worktree"`。
     - 片方だけが存在する場合、または通常ファイル・symlink である場合: 不整合な状態として終了コード 2 で拒否する。
   - 次の機械的条件をすべて検査する（作業ツリーや state ファイルは書き換えない）:
     1. **ブランチ指定と未 push 条件:** `--code-branch` が空でない有効なブランチ名であり、`DOCS_SEPARATE=true` のときは `--doc-branch` も空でない有効なブランチ名であること（空なら終了コード 2）。`TARGET_ROOT` の `origin` に対する `git ls-remote --refs origin "refs/heads/$CODE_BRANCH"`（および `DOCS_SEPARATE=true` なら `PARENT_ROOT` の `origin` に対する `git ls-remote --refs origin "refs/heads/$DOC_BRANCH"`）がすべて空であること。`publish` の途中で `DOC_BRANCH` だけ先に push 済みの場合を含め、1 つでも remote に存在する場合は「push 済み」として終了コード 2 で拒否する。
     2. **初期連鎖の整合と移動の有無:** 既存の `base-advances.jsonl`（無ければ 0 件）の全レコードがスキーマ（後述 1.4）を満たし `initial.json -> current.json` の連鎖と整合していること。そのうえで `code`（および `DOCS_SEPARATE=true` なら `docs`）の remote 先端 SHA を取得し、少なくとも一方が現在の捕捉済み `sha` から変化していること。どちらも変化していなければ終了コード 2 で拒否する。
     3. **前進回数の上限:** `$SESSION/base-advances.jsonl` の既存記録を読み、今回前進する各対象（`target == "code"` / `"docs"`）ごとの累計前進回数が `max_advances`（既定 `3`）未満であること。上限に達していれば終了コード 2 で拒否する。
     4. **fast-forward 条件:** 前進した各対象で `git merge-base --is-ancestor <old_sha> <new_sha>` が成立すること。巻き戻しや force push による非 fast-forward 変化は終了コード 2 で拒否する。
     5. **所有パスとの非重複（`code`・`docs` 両対応）:** `$SESSION/owned-paths.json` を検証し、`code` が前進した場合は `TARGET_ROOT` の `<old_code_sha>..<new_code_sha>` の変更ファイルが `owned-paths.json["code"]` と 1 件も重ならないこと。`DOCS_SEPARATE=true` で `docs` が前進した場合は `PARENT_ROOT` の `<old_doc_sha>..<new_doc_sha>` の変更ファイルが `owned-paths.json["docs"]` と 1 件も重ならないこと。
     6. **worktree の状態・変更非重複・非衝突（`phase == "worktree"` のとき）:** 存在する `CODE_ROOT`（および `DOCS_SEPARATE=true` なら `DOC_ROOT`）のそれぞれについて、対象 checkout の共通 Git ディレクトリに属する worktree ルートであり、現在のブランチが期待する `CODE_BRANCH` / `DOC_BRANCH` と一致し、`git status --porcelain --untracked-files=normal` が空で、現在の捕捉 `<old_sha>` が `HEAD` の祖先であり、`<old_sha>..HEAD` にマージコミットが無く（`git rev-list --merges <old_sha>..HEAD` が空）、対象側が前進している場合は `<old_sha>..HEAD` の変更ファイルが `<old_sha>..<new_sha>` の変更ファイルと 1 件も重ならず、`HEAD != old_sha` のとき `git merge-tree --write-tree HEAD <new_sha>` が終了コード 0 で衝突しないこと。
   - すべて満たす場合は、`phase`・`docs_separate`・`owned_paths_sha256`・各対象（`code` および該当時は `docs`）の `advanced`・`old_sha`・`new_sha`・`<old_sha>..<new_sha>` のコミット一覧（SHA と件名）・変更ファイル一覧を含む検査結果 JSON を標準出力に出して終了コード 0 を返す。1 つでも満たさない場合は標準出力を空にし、旧/新 SHA と不成立理由を標準エラーに出して終了コード 2 を返す。

4. **前進適用・rebase・シェル状態の自立更新（`--advance`）**
   - 司令塔は `--inspect-advance` が出力した `$SESSION/advance-inspection.json` のコミット一覧と変更ファイル一覧を読み、設計の前提（**`preflight` 条件・`checkout_policy`（`tools/agent_runner/checkout_policy.py` 等の checkout 監査条件）・外部仕様・共有インターフェース・適用される `AGENTS.md` の規則**）が変わっていないことを確かめ、確認結果と根拠を `$SESSION/advance-premise.txt` に 1 行以上で書く。前提が変わっている・判断できない場合は `--advance` を呼ばずに run を停止して報告する。
   - 呼び出し:
     ```text
     resolve_base.py --advance --session "$SESSION" \
       --inspection "$SESSION/advance-inspection.json" \
       --owned-paths-file "$SESSION/owned-paths.json" \
       --premise-file "$SESSION/advance-premise.txt" \
       --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
       --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
       [--max-advances 3]
     ```
   - `--advance` は `--premise-file` が空でない通常ファイル（symlink 不可）であること、`owned-paths.json` の SHA-256 が `--inspection` の `owned_paths_sha256` と一致すること、`phase` と各対象の `old_sha`・`new_sha` が live の再検査結果と完全一致すること（検査後にさらに base や worktree が変化していないこと）を含め、`--inspect-advance` の全条件を再検証する。
   - `phase == "worktree"` の場合、前進した対象の worktree で開始前の `<old_head>`（40 桁 hex SHA）を控え、`git -C <worktree> rebase --onto <new_sha> <old_sha>` を実行し、完了後の `<new_head>`（40 桁 hex SHA）を取得する。万一 rebase が非 0 で失敗した場合は直ちに `git -C <worktree> rebase --abort`（rebase 進行中のとき）を実行し、既に片方の worktree を rebase 済みだった場合も事前に控えた clean な `<old_head>` へ `git -C <other_worktree> reset --hard <old_head>` で戻してから、state ファイルを一切更新せずに終了コード 2 で停止する。`phase == "pre_worktree"` の場合は worktree 操作を行わず、`old_head` と `new_head` はどちらも `null` とする。
   - 成功したら、`SESSION` 内の古い `$SESSION/reverified.json`・`$SESSION/checks.json`・`$SESSION/code-sha.txt`・`$SESSION/docs-sha.txt` を削除（無効化）する（既存の `checks.json` から `required-verify-cmds.json` を自動生成する経路は設けない。必須検証コマンドは常に `--set-verify-cmds` で明示固定する）。
   - 続けて、前進した各対象の監査レコードを `$SESSION/base-advances.jsonl` に 1 行 1 JSON オブジェクトで追記したうえで、`code-base.json`（および該当時は `docs-base.json`）を一時ファイルからの `os.replace` で一括更新する。
   - **`base-advances.jsonl` の有効レコードスキーマ（`--inspect-advance`・`--reverify`・両ゲートで共通検証）:**
     - `target`: `"code"` または `"docs"`（`DOCS_SEPARATE=false` のとき `"docs"` は不正）
     - `repo`: 非空文字列（`target == "code"` は `target.json["repository"]` と大文字小文字無視で一致、`"docs"` は `"usaturn/create-reso-world"`）
     - `branch`: 非空文字列（対象 base JSON の `branch` と一致）
     - `ref`: `"refs/heads/" + branch`
     - `old_sha`・`new_sha`: 40 桁小文字 hex SHA であり `old_sha != new_sha`
     - `phase`: `"pre_worktree"` または `"worktree"`
     - `old_head`・`new_head`: `phase == "pre_worktree"` のときは**両方とも `null`**、`phase == "worktree"` のときは**両方とも 40 桁小文字 hex SHA**（片方だけ `null` や逆の組み合わせは不正として終了コード 2 で拒否）
     - `changed_files`: 文字列配列（`list[str]`）
     - `premise_note`: 非空文字列
   - **同一シェルおよび別シェルへの反映:** `<!-- base-workflow:advance -->` ブロックは前のブロックが `exit 2` で終わった後の新しいシェルから単独起動されても動くよう、先頭で `$SESSION/target.json` から `TARGET_ROOT`・`TARGET_REPO`・`PARENT_ROOT`・`DOCS_SEPARATE` を読み、`resolve_base.py --advance` の成功直後に更新後の `code-base.json`（および `docs-base.json`）から `CODE_BASE_BRANCH`・`CODE_BASE_SHA`（および `DOC_BASE_SHA`）を読み込み、`recheck_bases` 関数を再定義し、`$SESSION/base-env.bash`（および既存の `$SESSION/resume.bash` があればその内容）を最新値で書き換えてから `recheck_bases || exit 2` を実行する。この末尾の `recheck_bases` が非 0 で失敗した場合（`advance` の直後にさらに remote の base が前進した場合）も、未 push である限り 2 章 6 の同じ前進追随ループ（上限 3 回まで）に再度入る。

5. **必須検証コマンドの固定（`--set-verify-cmds`）と再検証の実行（`--reverify`）**
   - **必須検証コマンドの固定（`--set-verify-cmds`）:**
     ```text
     resolve_base.py --set-verify-cmds --session "$SESSION" --commands-file "$SESSION/verify-cmds.json"
     ```
     - `$SESSION/verify-cmds.json` は、2 章 5 と Plan で定めたその run の必須検証コマンド配列（1 件以上）を持つ通常ファイルとする。各要素は次のどちらかで書け、正規化して保存する:
       - 文字列リスト `["uv", "run", ...]`（省略形。`{"cwd": "code", "argv": [...]}` に正規化する）
       - オブジェクト `{"cwd": "code" | "docs" | "parent", "argv": ["bash", "scripts/check-layout.sh"]}`（`"code"` は `CODE_ROOT`、`"docs"` は `DOC_ROOT`（`DOCS_SEPARATE=true` のときのみ許可）、`"parent"` は `PARENT_ROOT` を実行 cwd とする。任意の生パス指定は拒否する）
     - これにより、空白を含むパスでも分割ずれを起こさず、`DOCS_SEPARATE=true` の run で `DOC_ROOT` や `PARENT_ROOT` 側の検証が必要な場合も正確に表現・実行できる。
     - `$SESSION/required-verify-cmds.json` が未作成なら正規化後の配列を排他作成（`"x"` モード）で保存する。既に存在する場合、正規化後の配列が完全に一致すれば終了コード 0（再検証ループでの再実行に冪等）、1 箇所でも異なれば（件数削減・`cwd` 変更・軽いコマンドへの差し替え）終了コード 2 で拒否する。
   - **再検証の実行（`--reverify`）:**
     ```text
     resolve_base.py --reverify --session "$SESSION" \
       [--commands-file "$SESSION/verify-cmds.json"] \
       --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}"
     ```
     - `$SESSION/required-verify-cmds.json` が存在し有効な正規化配列（1 件以上）であることを必須とする。`--commands-file` が渡された場合は正規化後に `$SESSION/required-verify-cmds.json` と完全一致することを検査し、不完全な一覧や別コマンドであれば `reverified.json` を作らず終了コード 2 で拒否する（省略時は `required-verify-cmds.json` をそのまま使う）。
     - 実行前に、(a) `initial.json` から `base-advances.jsonl` を経て現在の `code-base.json`（および `DOCS_SEPARATE=true` 時は `docs-base.json`）に至る連鎖とスキーマが整合し `len(base-advances.jsonl) >= 1` であること、(b) remote の先端が現在の `code-base.json`（および `docs-base.json`）と一致すること、(c) `CODE_ROOT`（および `DOCS_SEPARATE=true` 時は `DOC_ROOT`）が存在し clean（`git status --porcelain --untracked-files=normal` が空）で、各 base SHA が各 `HEAD` の祖先であることを確かめる。
     - 既存の `$SESSION/reverified.json`・`$SESSION/checks.json` があれば実行前に削除する。各コマンドを指定された `cwd`（`"code"` → `CODE_ROOT`、`"docs"` → `DOC_ROOT`、`"parent"` → `PARENT_ROOT`）で、継承した `GIT_*` を除去した環境にて順に同期実行し、標準出力・標準エラーを `$SESSION/reverify-<番号>.log` に保存する。終了コードが非 0 のコマンドが 1 つでもあれば、`reverified.json` と `checks.json` を作らないまま失敗ログを残して終了コード 2 で停止する。
     - 全コマンド成功後、再度 worktree が clean で `HEAD` と remote base SHA が変化していないことを確かめ、`$SESSION/reverified.json` と `finalize.py` 互換の `$SESSION/checks.json` を一括書き出しする。
     - `$SESSION/reverified.json` の項目:
       - `docs_separate`: `bool`
       - `advance_count`: `base-advances.jsonl` の総レコード数（`int >= 1`）
       - `code_base_sha`: 検証時点の `code-base.json["sha"]`
       - `code_head_sha`: 検証時点の `CODE_ROOT` `HEAD` 完全 SHA
       - `doc_base_sha`: `DOCS_SEPARATE=true` 時は `docs-base.json["sha"]`、`false` 時は `null`
       - `doc_head_sha`: `DOCS_SEPARATE=true` 時は `DOC_ROOT` `HEAD` 完全 SHA、`false` 時は `null`
       - `required_verify_sha256`: `$SESSION/required-verify-cmds.json` の SHA-256
       - `commands`: 各要素 `{"cwd": "code" | "docs" | "parent", "argv": [...], "exit_code": 0, "log_path": "...", "log_sha256": "..."}`
     - `$SESSION/checks.json` の項目: `{"head": code_head_sha, "base": code_base_sha, "commands": [{"argv": [...], "exit_code": 0}, ...]}`。

6. **公開前ゲート（`--check-publish-gate`）と PR 作成前ゲート（`--check-pr-gate`）**
   - **通常 run（未前進）の共通判定:** `code-base.json["sha"] == code-base.initial.json["sha"]`（かつ `DOCS_SEPARATE=true` のときは `docs-base.json["sha"] == docs-base.initial.json["sha"]`）であり、かつ `$SESSION/base-advances.jsonl` が存在しない場合、`--check-publish-gate` と `--check-pr-gate` は**どちらも** `reverified.json`・`owned-paths.json`・`required-verify-cmds.json`・PR 本文の rebase 記載を要求せず、即座に終了コード 0 を返す。
   - **前進あり（または初期値不一致）のときの `--check-publish-gate` 検査項目（`publish` ブロックで最初の `recheck_bases` の直後・`scan-before-push.sh` の前に呼ぶ）:**
     1. `$SESSION/base-advances.jsonl` が 1 件以上のレコードを持ち、全レコードが 1.4 の有効レコードスキーマ（`pre_worktree` では `old_head == null` かつ `new_head == null`、`worktree` では両方 40 桁 hex SHA を含む）を満たし、`target == "code"` の連鎖が `code-base.initial.json["sha"] -> ... -> code-base.json["sha"]` と完全一致すること（`code` 前進が 0 件なら `code-base.json["sha"] == code-base.initial.json["sha"]`）。`DOCS_SEPARATE=true` なら `target == "docs"` についても `docs-base.initial.json["sha"] -> ... -> docs-base.json["sha"]` が完全一致すること（`DOCS_SEPARATE=false` なのに `target == "docs"` レコードがあれば拒否）。これにより `code-base.json` の手動書き換えや履歴削除を拒否する。
     2. `$SESSION/required-verify-cmds.json` と `$SESSION/reverified.json` が両方とも通常ファイル（symlink 不可）として存在し、次の各項目がすべて一致すること:
        - `reverified["docs_separate"] == DOCS_SEPARATE`
        - `reverified["advance_count"] == len(base_advances)`（`base-advances.jsonl` の総レコード数）
        - `reverified["required_verify_sha256"] == sha256(required-verify-cmds.json)`
        - `[{"cwd": c["cwd"], "argv": c["argv"]} for c in reverified["commands"]] == required_verify_cmds`（1 件以上、順序・`cwd`・引数とも完全一致）
        - `reverified["code_base_sha"] == code-base.json["sha"]`
        - `reverified["code_head_sha"] == git -C "$CODE_ROOT" rev-parse HEAD`、かつ `CODE_ROOT` の `git status --porcelain --untracked-files=normal` が空で `code_base_sha` が `code_head_sha` の祖先であること（再検証後の追加コミット = stale HEAD や未コミット変更を拒否）
        - `DOCS_SEPARATE=true` のとき: `reverified["doc_base_sha"] == docs-base.json["sha"]`、`reverified["doc_head_sha"] == git -C "$DOC_ROOT" rev-parse HEAD`、かつ `DOC_ROOT` が clean で `doc_base_sha` が `doc_head_sha` の祖先であること（`false` のときは両方 `null`）
        - 各 `commands[i]` の `exit_code == 0`、`log_path` が `$SESSION` 内の実在する通常ファイル（symlink 不可）であり、`sha256(log_path) == commands[i]["log_sha256"]` であること
     - 1 項目でも不成立なら終了コード 2 で `publish` を止める。
   - **前進あり（または初期値不一致）のときの `--check-pr-gate` 検査項目（`pr` ブロックで最初の `recheck_bases` の直後・`gh pr create` の前に呼ぶ）:**
     1. 上記 `--check-publish-gate` の全項目を満たすこと。
     2. `$SESSION/code-sha.txt` の SHA が `reverified["code_head_sha"]` と一致し、`DOCS_SEPARATE=true` のときは `$SESSION/docs-sha.txt` の SHA が `reverified["doc_head_sha"]` と一致すること。
     3. `base-advances.jsonl` の `target == "code"` の各レコードについて `--code-pr-body` ファイルに `old_sha[:7]` と `new_sha[:7]` が含まれ、`DOCS_SEPARATE=true` で `target == "docs"` の各レコードについて `--doc-pr-body` ファイルに `old_sha[:7]` と `new_sha[:7]` が含まれること。さらに `required-verify-cmds.json` の各エントリの `argv` について、`--code-pr-body` ファイルに `" ".join(argv)` または `shlex.join(argv)` が含まれること。
     - 1 項目でも不成立なら `gh pr create` の前に終了コード 2 で止める。

### 2. `SKILL.md` の手順と実行ブロック更新（2 章 6 と 5 章）

Claude Code 等の Bash 実行環境では `eval '<block>' && true` の形で動くことがあり `set -e` だけでは途中失敗で止まらないため（`test_base_workflow.py` の `as_runtime` が検証する条件）、追加・変更するすべての `<!-- base-workflow:... -->` ブロックでも各コマンドに明示的な `|| exit 2` を付ける。また、ブロック失敗後に新しいシェルで次のブロックを実行するランタイムでも変数が欠落しないよう、`$SESSION/base-env.bash` の保存・更新を組み込む。

1. **2 章 6（`capture`・所有パス記録・未 push 時の前進追随フロー）**
   - `<!-- base-workflow:capture -->` ブロックの `resolve_base.py` 呼び出しを `--write-state "$SESSION/code-base.json"`（および `DOCS_SEPARATE != false` 時は `--write-state "$SESSION/docs-base.json"`）に更新し、末尾で `$SESSION/base-env.bash` に変数と `recheck_bases` 関数を保存する。
   - `capture` の直後（`worktree` の前）に初期の `$SESSION/owned-paths.json` を作り、4 章 3 の Plan コミット直後に 1.2 の振り分け規則に従って `$SESSION/owned-paths.json` を更新するとともに、Plan の必須検証コマンドを `$SESSION/verify-cmds.json` に書いて `--set-verify-cmds` で固定する手順を明記する。
   - 2 章 6 に自己完結した実行可能な `<!-- base-workflow:inspect-advance -->` と `<!-- base-workflow:advance -->` の Bash ブロックを追加する。`advance` ブロックは `$SESSION/target.json` と更新後の base JSON からすべての変数と `recheck_bases` を復元・更新し、`$SESSION/base-env.bash`（および既存の `$SESSION/resume.bash`）を書き換えたうえで `recheck_bases || exit 2` を実行する。別シェルで後続の `worktree`・`diff`・`publish` を実行するときは `source "$SESSION/base-env.bash"` で最新状態を読む。
   - **未 push の base 移動失敗からの復帰ループ（4 章は編集しない）:**
     - **対象となるすべての未 push 失敗点:** ① 3 章 `base-workflow:worktree` の `recheck_bases`、② 5 章冒頭の最終検証前の `recheck_bases`、③ 5 章 `base-workflow:diff` の `recheck_bases`、④ 5 章 `base-workflow:publish` における push 開始前の `recheck_bases` **および `scripts/scan-before-push.sh` の `--expected-base-sha` 不一致（`base moved`）失敗**、⑤ `base-workflow:advance` 末尾の `recheck_bases`（`advance` 中にさらに base が前進した場合）。
     - これらでブロックが非 0 終了したとき、司令塔は **run 全体を停止せず**直ちに次のループに入る:
       1. `<!-- base-workflow:inspect-advance -->` を実行して `$SESSION/advance-inspection.json` を得る（終了コード非 0 — 既に片方でも push 済み、非 fast-forward、所有/変更パス重複、衝突、累計前進 3 回の上限到達、または `scan-before-push.sh` の失敗原因が base 移動でなく秘密情報検出等だったため base 未移動 — ならここで run を停止して報告する）。
       2. `$SESSION/advance-inspection.json` のコミットと変更ファイルを確認し、`preflight`・`checkout_policy`・外部仕様・共有インターフェース・適用される `AGENTS.md` の前提が変わっていなければ根拠を `$SESSION/advance-premise.txt` に書く（前提が変わっていれば run を停止して報告する）。
       3. `<!-- base-workflow:advance -->` を実行する（末尾の `recheck_bases` がさらなる前進で失敗した場合は 1 に戻って再検査し、上限 3 回まで追随する）。
       4. 再開先: `worktree` 未作成（`pre_worktree`）だった場合は `<!-- base-workflow:worktree -->` をやり直して 4 章へ進む。`worktree` 作成済みだった場合は必ず 5 章の `<!-- base-workflow:reverify -->` を実行し、PR 本文（`CODE_PR_BODY` / `DOC_PR_BODY`）に全前進の旧/新 SHA と再検証コマンドを反映してから、`<!-- base-workflow:diff -->` → `<!-- base-workflow:publish -->` → `<!-- base-workflow:pr -->` を順に実行する。
     - **push 済みの検出点（`publish` で片方の push が済んだ後の `recheck_bases`、`base-workflow:pr` の `recheck_bases`、PR 作成後）で失敗したとき:** rebase せず従来どおり run を停止して旧/新 SHA・公開済み資源を報告する（PR 作成後の `--merge` ループでは既存の `review-fix-planning` / `finalize.py` の `base_moved` 再検証経路で扱う）。

2. **5 章（検証前の base 確認・`reverify`・`diff`・`publish`・`pr`・PR 本文）**
   - 5 章冒頭の検証手順に、(a) 必須検証コマンド配列を `$SESSION/verify-cmds.json` に用意して `--set-verify-cmds` で固定し、最終検証の前に `recheck_bases` を確認して未 push で base が前進していれば先に 2 章 6 の前進追随を行ってから検証すること（長い実装後の検証の二度手間を防ぐ）、(b) 1 回でも base 前進追随を行った run（`$SESSION/base-advances.jsonl` がある run、`pre_worktree` での前進を含む）では検証を `<!-- base-workflow:reverify -->` で実行して `$SESSION/reverified.json` と `$SESSION/checks.json` を記録すること、(c) 検証後に `diff` や push 前の `publish`（`scan-before-push.sh` を含む）でさらに base 前進を観測したときも 2 章 6 の前進追随の後に必ず `<!-- base-workflow:reverify -->` からやり直すことを明記する。
   - `<!-- base-workflow:publish -->` の最初の `recheck_bases || exit 2` の直後に `resolve_base.py --check-publish-gate --session "$SESSION" --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}" || exit 2` を追加する。
   - `<!-- base-workflow:pr -->` の最初の `recheck_bases || exit 2` の直後に `resolve_base.py --check-pr-gate --session "$SESSION" --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}" --code-pr-body "$CODE_PR_BODY" --doc-pr-body "${DOC_PR_BODY:-}" || exit 2` を追加する。
   - PR 本文の記載項目に「base 前進追随を行った run では、rebase（または worktree 作成前の再捕捉）を行ったこと、各前進の旧/新 base SHA、やり直した必須検証コマンドと結果を記載する」ことを追加する。

3. **2 章 3 と停止時の報告の整合注記**
   - 2 章 3 の「終了コードが 0 でないブロックの後は、次のブロックへ進まない。base の取得をやり直して SHA を差し替えない」に「（未 push の base 前進で 2 章 6 の前進追随フローに入る場合を除く）」を補い、「停止時の報告」の「捕捉後の移動」に「（2 章 6 の条件を満たして前進追随・再検証する場合を除く）」を補う。3 章（想定された停止でのペイン名維持）と 4 章には触れない。

### 3. テスト方針（`AGENTS.md`「テストの採用基準」との照合）

`SKILL.md` の固定文言を文字列照合するテスト（F）や、引数不足・ヘルプ表示の検査（L）、同じ守りの別ファイル重複（D）は書かない。壊れても黙って損害（未検証の組み合わせの公開、不完全な検証コマンドでのゲート通過、所有ファイル重複の見落とし、push 済み履歴の書き換え、別シェル再開時の不整合）が生じる S の条件だけを、層ごとに代表テストへ集約する。

1. `.agents/skills/issue-to-pr/tests/test_resolve_base.py`:
   - 既存の 8 テスト（`test_base_movement_rejected` を含む全 8 件）を維持する。
   - 新規 S テスト 1 件（`test_advance_guards_and_state_chain`）: 実 Git リポジトリ（`DOCS_SEPARATE=false` と `DOCS_SEPARATE=true` の両方を含む）で次を検証する:
     - `--write-state` の二重書き込み拒否、および未前進通常状態で `--check-publish-gate`・`--check-pr-gate` が `reverified.json` 無しで終了コード 0 を返すこと
     - `pre_worktree`（`CODE_ROOT` 未作成）での前進検査・適用が `TARGET_ROOT` を使って成功し `old_head: null, new_head: null` の記録を作り、その後の worktree 作成・コミット・`--set-verify-cmds`・`--reverify` を経て `--check-publish-gate` と `--check-pr-gate` を通過すること
     - 空の所有パスリスト（`{"code": []}`、および `DOCS_SEPARATE=true` 時の `{"code": ["a"], "docs": []}`）の拒否
     - 非 fast-forward 変化の拒否、push 済みブランチの拒否、`code` 所有パス重複の拒否、`DOCS_SEPARATE=true` での `docs` 所有パス重複の拒否、および非重複時の `docs` + `code` 前進・`DOC_ROOT` rebase・`"cwd": "docs"` を含む必須検証コマンド実行での成功
     - worktree 変更重複・`merge-tree` 衝突・未コミット変更の拒否（いずれも拒否時に worktree `HEAD` と state JSON が不変であること）
     - 累計前進 3 回までの成功と 4 回目の拒否
     - 古い部分的な `checks.json` があっても `--advance` がそれを `required-verify-cmds.json` に流用せず削除すること、`--set-verify-cmds` 後のコマンド削減・差し替えの拒否、`--reverify` での不完全なコマンド一覧の拒否、非 0 終了コマンド（`exit 1`）で `reverified.json` が作られず `--check-publish-gate` が拒否すること、および `--reverify` 成功後に追加コミット（stale HEAD）を作ると `--check-publish-gate` が拒否すること

2. `.agents/skills/issue-to-pr/tests/test_base_workflow.py`:
   - 既存の全テスト（通常 run の `test_documented_flow_pins_worktree_diff_scan_and_pr`、push 後の PR 作成前に base が動いたときに停止する `test_resumed_shell_stops_before_pr_creation_when_base_moved` など）を維持する。
   - 新規 S テスト 1 件（`test_unpushed_base_advance_requires_reverify_and_pr_record`）: `SKILL.md` から抽出した実ブロック（`input`・`target`・`capture`・`worktree`・`diff`・`inspect-advance`・`advance`・`reverify`・`publish`・`pr`）を実行し、次の復帰・防御の一連の流れを検証する:
     - 未 push のまま remote の base が前進した状態で `publish`（`recheck_bases` または `scan-before-push.sh` 中の移動を含む）を実行すると終了コード 2 で止まり、remote に何も push されないこと
     - `code-base.json` を手動で新 SHA に書き換えてゲート回避を試みても `publish` が終了コード 2 で拒否すること
     - 失敗したブロックの後の**別シェル（新しい `bash -c` プロセス）**で `inspect-advance` → `advance` を実行すると、`advance` ブロック単独で成功して `$SESSION/base-env.bash` と `CODE_BASE_SHA` を更新し（`advance` 直後にさらに 2 回目の base 前進が起きた場合も同じループで追随でき）、`source "$SESSION/base-env.bash"` した別シェルで `recheck_bases` が成功すること
     - `advance` 後に `reverify` を省いて `publish` を再実行すると終了コード 2 で止まり push されないこと
     - `reverify` 実行後に `diff` → `publish` が成功し、PR 本文に全前進の旧/新 SHA と再検証コマンドが無い状態では再開シェルの `pr` が `gh pr create` の前に終了コード 2 で止まり、すべて記載した状態では `pr` が成功して新しい base 上のコミットが公開されること

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 提案 1（未 push 時の条件付き rebase + 再検証による続行）と、5 章の最終検証前 `recheck_bases` 確認（提案 3 の所有範囲内適用）を組み合わせ、未 push のすべての base 移動失敗（`worktree`・5 章冒頭・`diff`・`publish` の `recheck_bases`、`scan-before-push.sh` の `base moved`、`advance` 末尾の `recheck_bases`）から別シェルでも自立復帰する手順を定める | (a) 提案 2（停止のまま再開手順だけ書く）<br>(b) `recheck_bases` 内で自動 rebase する<br>(c) `implement_task.py` や 4 章にも base 検査を足す | (a) は並列 run の直列化と手動往復が残る。(b) は設計前提の確認と再検証を経ずに `publish` 内で push まで進む危険がある。(c) は `implement_task.py`（#389/#390）と `SKILL.md` 4 章（#417）の所有境界と競合する。明示ブロックと `$SESSION/base-env.bash` による未 push 復帰ループなら安全条件と所有境界の両方を守れる | `issue-to-pr` 1 章の推奨案委任および Issue #378 の「提案（案）」 |
| D2 | `capture` の `--write-state` で `initial.json` を排他保存し、Plan の検証から `--set-verify-cmds`（`cwd: code/docs/parent` 対応）だけで必須検証コマンドを排他固定したうえで、`--advance`（`base-advances.jsonl` と `$SESSION/base-env.bash` 更新）と `--reverify`（`reverified.json`）を `--check-publish-gate`・`--check-pr-gate` で項目ごとに機械照合する（未前進の通常 run は両ゲートとも即座に 0 を返す） | (a) 通常の `resolve_base.py` を再実行して `code-base.json` を上書きし、再検証は `SKILL.md` の文章だけで求める<br>(b) 任意のコマンド配列や古い `checks.json` の流用で `--reverify` を通す<br>(c) `code-base.json` のスキーマ自体に履歴配列を足す | (a) は捕捉値の黙った差し替えと区別できず、(b) は不完全なコマンド一覧で必須検証を省けてしまう（Issue の受け入れ「検証をやり直さずに公開・マージする経路が無い」を満たせない）。(c) は既存の 5 キー JSON を読む箇所を壊す。別ファイル連鎖と `--set-verify-cmds` 単独の排他固定なら通常 run の互換を保ちつつ改ざん・省略を確実に拒否できる | Issue #378 の「範囲と除外」「受け入れ」。連鎖不整合・必須検証不一致・再検証未実施時は終了コード 2 で停止 |
| D3 | 続行条件を (1) 全作業ブランチ（`CODE_BRANCH` および `DOCS_SEPARATE=true` 時の `DOC_BRANCH`）が `origin` に未 push、(2) fast-forward（`is-ancestor`）、(3) リポジトリ別に振り分けた非空の `owned-paths.json`（`code` と `DOCS_SEPARATE=true` 時の `docs`）および `<old_sha>..HEAD` 変更ファイルとの非重複、(4) `pre_worktree` では `TARGET_ROOT` / `PARENT_ROOT` で検査（`old_head/new_head` は `null`）し、`worktree` 作成済みでは clean な線形 worktree で `merge-tree` 非衝突かつ `rebase --onto` 成功（失敗時は他方も `old_head` へ戻す）、(5) `preflight`・`checkout_policy`・外部仕様・共有インターフェース・`AGENTS.md` を含む設計前提不変の `--premise-file` 記録、(6) 各対象リポジトリあたり最大 3 回まで、とする | (a) 回数上限を設けない、または 1 回だけにする<br>(b) 空の `owned-paths` を許す、または `docs` 側の所有パス振り分け・重複を見ない | (a) 無制限は活発な並列マージ下で再検証ループが収束せず実行予算を浪費し、1 回は 3 並列 run で不足する。3 回は `review-fix-planning` / `pr-review-fix-loop` の `base_moved` 上限と揃う。(b) 空リスト許容や `docs` 未振り分けは R11 の「所有ファイルとの重なりが無く衝突しなければ」の抜け道になるため、両リポジトリとも非空リストで機械検査する | #350 R11 の利用者裁定・Issue #378 本文。いずれか不成立・上限到達時は停止 |
| D4 | `--base` で指定された統合用ブランチ（例: `feat/plugin-v2`）にも同じ条件付き rebase・再検証規則を適用し、`CODE_BASE_BRANCH` 名・`required-bases.txt`・`merge-disabled.txt` は不変とする | 既定の `main` だけに限定し、統合用ブランチは常に停止させる | Issue #378 の背景事例 #100 自体が統合用ブランチ `feat/plugin-v2` での兄弟 PR マージによる前進であり、統合用ブランチこそ並列の子 Issue が順次マージされる場面が多い。fast-forward・非重複・再検証の安全条件は `main` と同じように成り立ち、`merge-disabled.txt` を維持するため誤マージの危険も無い | Issue #378「変更してはいけない」（統合 branch に同じ規則を適用するかは Spec で決める） |
| D5 | `SKILL.md` の編集は 2 章 6・5 章と、2 章 3・停止時の報告の括弧注記に限る。4 章（#417）と `implement_task.py`（#389/#390）は編集しない | 4 章の runner 実装節にも Task 境界の base 再確認手順を書き足す | #349 の所有表で #378 の編集範囲は `SKILL.md` 2 章 6・5 章と `resolve_base.py`・同 tests に定められており、4 章は open の #417 が対象としているため節の衝突を避ける | #349 の所有境界。他 Issue の所有ファイルの変更が必要になった場合は停止 |
| D6 | `resolve_base.py` は Python 標準ライブラリと既存の同ディレクトリモジュール（`git_env.py`・`resolve_issue.py`）だけで実装し、外部パッケージを使わない | `pydantic` 等で JSON スキーマ検証を行う | `SKILL.md` の各ブロックが `uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py"` で起動するため、プロジェクト仮想環境外の標準ライブラリだけで動く必要がある | 既存の起動インターフェース仕様 |
| D7 | Spec レビュー担当・Plan Task 実装担当・ループ修正担当は利用者指定の `pi_opencode-go_deepseek4-flash_max`、ループ inspect 担当は `devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default` とし、実装は `self: false` のため `implement_task.py run` で Task ごとに直列委譲する。PR 本文の Issue 指定は `Closes #378` とする | `self` での直接実装、`Refs #378` | 2 章 3 の `check` で `self: false` と確定しており、4 章の表と「失敗を理由に `self` で引き取らない」規則に従う。#378 は `TARGET_REPO` 内のボード外 Issue でマージ後の rebuild・実機確認を残さないため 5 章の規則により `Closes #378` に当たる | 利用者の明示オプション指定。外部担当の `failed`・再試行上限到達・Spec レビュー失敗時は停止 |

### Spec レビュー記録

#### 1 回目（`round: 1`）

- `review_dir`: `/workspaces/reso-world/tmp/agents/issue-378.pu_as9oz/2026-11-12-issue-378-rebase-base-design.spec-review/review-1`
- `review_id`: `092b76c6442a4934af77e8b43aaa24a0`
- `reviewed_spec_sha256`: `14d26db81107a255e9c9f85b57f30806d7eade1985675687b76e8370b2398dd9`
- 実行手段・担当: `review_spec.py` helper（`mode: external`）、`requested_agent: "pi_opencode-go_deepseek4-flash_max"`、`actual_agent: "pi_opencode-go_deepseek4-flash_max"`、`fallback` 使用なし（`fallback: []`、`fallback_exhausted: false`）
- `identity`: `{"model": "deepseek-v4.1-flash", "provider": "opencode-go", "effort": "max", "session_id": "01a1ced6-3bd2-71e5-ae03-8cef96e6e682", "cli_version": null, "skill_versions": {}}`
- `elapsed_seconds`: `536.4333000979968`（試行: `533.2670667560014`）
- `outside_changes`: `[]`
- `unprotected_changes`: `["/tmp/pr-review-376-2f0d17b0/worktree", "/tmp/pr-review-376-79fe98e5/worktree", "/tmp/pr-review-376-7f95b4e6/worktree", "/tmp/pr-review-376-c9a6d3e9/worktree", "/tmp/review-fix-planning.9AkFc2/worktree", "/tmp/review-fix-planning.a6ogtH/worktree", "/workspaces/reso-world/.worktrees/issue-390-review-cleanup", "/workspaces/reso-world/.worktrees/issue-408-launcher-key-derivation"]`（他セッションの並行 worktree・一時レビュー残骸であり本 worktree 外）
- 指摘と採否（全 9 件採用）:
  - `S1`（`important`, `adopt`）: `advance` ブロックで `CODE_BASE_BRANCH`・`CODE_BASE_SHA`・`DOC_BASE_SHA` を再読込し `recheck_bases` を実行する手順とテストを設計 1.4・2.1・3.2 に追加
  - `S2`（`important`, `adopt`）: 「ブロック中断」と「run 全体の停止」を区別し、未 push の失敗点から `inspect-advance` → `advance` → `worktree` または `reverify` → `diff` → `publish` → `pr` へ復帰する制御フローと失敗からの復帰テストを非目標・設計 2.1・3.2・D1 に追加
  - `S3`（`important`, `adopt`）: `$SESSION/owned-paths.json` の生成元・更新時点（`capture` 直後と Plan コミット直後）と空リスト拒否規則・テストを設計 1.2・2.1・3.1・D3 に追加
  - `S4`（`important`, `adopt`）: `owned-paths.json` を `code` / `docs` の両方に対応させ、`DOCS_SEPARATE=true` 時の `docs` base 前進重複検査とテストを設計 1.2・1.3・3.1・D3 に追加
  - `S5`（`important`, `adopt`）: `--set-verify-cmds` で必須検証コマンドを排他固定し、`--reverify` と両ゲートでコマンド配列一致・ログ SHA-256・非 0 終了拒否を照合する仕様とテストを設計 1.5・1.6・3.1・D2 に追加
  - `S6`（`important`, `adopt`）: 未前進の通常 run では `--check-publish-gate` と `--check-pr-gate` の両方が即座に終了コード 0 を返すことを明記し、前進時の照合項目と stale HEAD テストを設計 1.6・3.1 に明記
  - `S7`（`important`, `adopt`）: `pre_worktree` 時は常設の `TARGET_ROOT` / `PARENT_ROOT` で Git 操作を実行する仕様とテストを設計 1.3・3.1 に明記し、4 章を編集しない方針に合わせて 2 章 6 から「Task 境界」を除外
  - `S8`（`important`, `adopt`）: 設計前提の確認項目に `checkout_policy` を設計 1.4・2.1・D3 へ追加
  - `S9`（`minor`, `adopt`）: `test_resolve_base.py` の既存テスト数を 8 件に修正（設計 3.1）

#### 2 回目（`round: 2`）

- `review_dir`: `/workspaces/reso-world/tmp/agents/issue-378.pu_as9oz/2026-11-12-issue-378-rebase-base-design.spec-review/review-2`
- `review_id`: `e3b0b23f8eef4617a8e54ccb21927939`
- `reviewed_spec_sha256`: `e5efdb307c7efd8df90aa43fbca2e4a5ee6a0205f1100ead40759f1562b12213`
- 実行手段・担当: `review_spec.py` helper（`mode: external`）、`requested_agent: "pi_opencode-go_deepseek4-flash_max"`、`actual_agent: "pi_opencode-go_deepseek4-flash_max"`、`fallback` 使用なし（`fallback: []`、`fallback_exhausted: false`）
- `identity`: `{"model": "deepseek-v4.1-flash", "provider": "opencode-go", "effort": "max", "session_id": "01a1ceec-f497-71b0-8202-0ed0d34d163b", "cli_version": null, "skill_versions": {}}`
- `elapsed_seconds`: `1745.0103302450152`（試行: `1741.9474491690053`）
- `outside_changes`: `[]`
- `unprotected_changes`: `["/tmp/pr-review-376-2f0d17b0/worktree", "/tmp/pr-review-376-79fe98e5/worktree", "/tmp/pr-review-376-7f95b4e6/worktree", "/tmp/pr-review-376-c9a6d3e9/worktree", "/tmp/review-fix-planning.9AkFc2/worktree", "/tmp/review-fix-planning.a6ogtH/worktree", "/workspaces/reso-world/.worktrees/issue-408-launcher-key-derivation", "/workspaces/reso-world/tmp/agents/issue-408.kwkykzl6/review-runner/spec-1/73627b9946d1473cb52f044f36426755/attempt-1/worktree"]`（他セッションの並行 worktree・一時レビュー残骸であり本 worktree 外）
- 指摘と採否（全 6 件採用）:
  - `S10`（`important`, `adopt`）: 未 push の復帰ループ対象に `scan-before-push.sh` の `--expected-base-sha` 不一致（`base moved`）失敗と `advance` ブロック末尾の `recheck_bases` 失敗および 2 章 3 の終了コード非 0 注記を含め、連続前進テストを設計 1.4・2.1・2.3・3.2・D1 に追加
  - `S11`（`important`, `adopt`）: `base-advances.jsonl` の有効レコードスキーマ（`pre_worktree` では `old_head == null, new_head == null`、`worktree` では両方 40 桁 hex SHA）と `pre_worktree -> reverify -> publish/pr ゲート` 通過テストを設計 1.4・1.6・3.1・D3 に追加
  - `S12`（`important`, `adopt`）: `capture` と `advance` で `$SESSION/base-env.bash`（および既存 `resume.bash`）を書き出し、`advance` ブロックが失敗後の新しいシェルでも `target.json` と base JSON から自立実行できる仕様と別シェル復帰テストを設計 1.1・1.4・2.1・3.2 に追加
  - `S13`（`important`, `adopt`）: 古い `checks.json` から `required-verify-cmds.json` を自動生成する経路を廃止し、`--set-verify-cmds` だけで必須検証コマンドを排他固定する仕様とテストを設計 1.4・1.5・3.1・D2 に反映
  - `S14`（`minor`, `adopt`）: 必須検証コマンド要素に `cwd`（`"code" | "docs" | "parent"`）を持てる正規化形式を定義し、`DOCS_SEPARATE=true` での `docs` 側検証コマンド実行テストを設計 1.5・1.6・3.1・D2 に追加
  - `S15`（`minor`, `adopt`）: Plan コミット直後の `owned-paths.json` 更新時にリポジトリ別（`CODE_ROOT` 側 Task は `code`、`DOC_ROOT` 側 Spec/Plan/Task は `docs`）へ振り分ける規則を設計 1.2・2.1・D3 に明記
