# Issue #378: issue-to-pr 未 push 時の条件付き base 前進追随 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- **状態:** `draft`（`issue-to-pr` による実行許可に基づき `draft` のままコミットする。確認用コピーは作らない）
- **Goal:** `issue-to-pr` の実行中に `origin` の base が前進したとき、全作業ブランチが未 push であることを条件に #350 R11 の安全条件を満たせば新しい base へ rebase（worktree 未作成時は再捕捉）し、必須検証をやり直したうえで公開・PR 作成まで止まらず続行できるようにする。
- **Architecture:** `.agents/skills/issue-to-pr/scripts/resolve_base.py` に初期捕捉の排他保存（`--write-state`）、所有パス・衝突・未 push・上限検査（`--inspect-advance`）、rebase と連鎖追記（`--advance`）、必須検証コマンド排他固定（`--set-verify-cmds`）と再検証実行（`--reverify`）、公開前・PR 作成前ゲート（`--check-publish-gate`・`--check-pr-gate`）を追加し、`.agents/skills/issue-to-pr/SKILL.md` の 2 章 6・5 章の実行ブロックから呼び出す。未前進の通常 run では両ゲートとも追加ファイルなしで即座に終了コード 0 を返し既存互換を保つ。
- **Tech Stack:** Python 3.14 標準ライブラリ（`resolve_base.py` は `uv run --no-project python` で起動）、Bash / Zsh 共通シェルスクリプトブロック、Git CLI、`pytest`（`uv run --project <checkout> --locked pytest`）。
- **Spec:** `docs/superpowers/specs/2026-11-12-issue-378-rebase-base-design.md`（commit `bb05350eaf5150d762845d0662f4bff4684f4ea7`）
- **実行方式と理由:** 2 章 3 の `implement_task.py check --implement pi_opencode-go_deepseek4-flash_max` で `self: false` と確定しているため、`SKILL.md` 4 章 4 の規則に従い `implement_task.py run` で `pi_opencode-go_deepseek4-flash_max` に Task 1 → Task 2 を直列委譲し、各 Task の取り込み後に SDD の Task レビューを行う。`--merge` が有効（`merge-disabled.txt` 不在）なため 4 章 8 に従い SDD の最終ブランチ全体レビューは PR 修正ループの 1 サイクル目で代える。
- **Global Constraints:**
  - `.agents/skills/issue-to-pr/SKILL.md` の **4 章（`## 4. 推奨案 → Spec → Plan → 実装` から `## 5. 検証・PR・完了` の直前まで）は 1 文字も変更しない**（open の #417 が対象とする節）。
  - `.agents/skills/issue-to-pr/scripts/implement_task.py`（#389・#390 が所有）、`scripts/scan-before-push.sh`、`tools/agent_runner/` は変更しない。
  - `resolve_base.py` は Python 標準ライブラリと同ディレクトリの `git_env.py`・`resolve_issue.py` だけで実装し、`pydantic` 等の外部パッケージを import しない。
  - テストは `AGENTS.md`「テストの採用基準」の `S`（気付けない損害）だけを書く。`SKILL.md` の固定文言照合（`F`）、ヘルプや引数不足だけの検査（`L`）、別ファイルでの同じ守りの重複（`D`）は書かない。
  - 日本語表現は `AGENTS.md`「日本語表現」節の言い換え規則を厳守する。
- **Review Focus:**
  1. 未検証の `(base, HEAD)` や不完全な検証コマンド配列、`code-base.json` の直接書き換えで `publish`・`pr` が通る抜け道が無いか。
  2. 未前進の通常 run で既存 8 件の `test_resolve_base.py` と全既存 `test_base_workflow.py`（`test_resumed_shell_stops_before_pr_creation_when_base_moved` を含む）が無変更の挙動で通るか。
  3. ブロックが `exit 2` で中断した後の別シェル（新しい `bash -c`）で `inspect-advance` → `advance` → `reverify` → `diff` → `publish` → `pr` が `$SESSION/base-env.bash` を通じて完結するか。

## 受け入れ基準

- **動作環境:**
  - Ubuntu 26.04 LTS Dev Container 上の Linux / Bash 環境、Python 3.14。
  - `resolve_base.py` はプロジェクト仮想環境を使わない `uv run --no-project python`（または標準ライブラリの `sys.executable`）で動作し、テストは `uv run --project <checkout> --locked pytest .agents/skills/issue-to-pr/tests` および `bash scripts/check-layout.sh` で動作すること。
  - Git 操作は継承した `GIT_*` を `git_env.py` で除去し（remote 通信時のみ `transport_auth=True`）、テストでは一時 `HOME` とローカル bare リポジトリを用いて外部ネットワークや実 GitHub・実モデルにアクセスしないこと。
- **実入力:**
  - 非 ASCII を含むブランチ名（例: `統合/プラグイン`）、空白を含むディレクトリパス（例: `parent with spaces`）、複数行の日本語を含む Issue 本文・PR 本文・前提確認メモ（`advance-premise.txt`）。
  - `DOCS_SEPARATE = false`（`usaturn/create-reso-world` および `AGENTS.md` で宣言した通常ツール）と、`DOCS_SEPARATE = true`（`usaturn/resoloop` や登録済み通常ツール `sample-owner/other-tool` と `usaturn/create-reso-world` 文書 worktree の 2 リポジトリ構成）の両方。
  - 必須検証コマンド配列（省略形 `["cmd", "arg", ...]`、および実行先を明示した `{"cwd": "code" | "docs" | "parent", "argv": ["cmd", "arg", ...]}`）。
- **防御範囲:**
  - **通す対象条件（正例）:**
    1. 未前進の通常 run（`code-base.json["sha"] == code-base.initial.json["sha"]`、かつ `DOCS_SEPARATE=true` 時は `docs-base.json["sha"] == docs-base.initial.json["sha"]`、かつ `base-advances.jsonl` 不在）では、`reverified.json`・`owned-paths.json`・`required-verify-cmds.json`・PR 本文の rebase 記載が無くても `--check-publish-gate` と `--check-pr-gate` が即座に終了コード 0 を返し、既存の全ワークフローがそのまま成功すること。
    2. 全作業ブランチ（`CODE_BRANCH` および `DOCS_SEPARATE=true` 時の `DOC_BRANCH`）が `origin` に未 push の状態で base が fast-forward 前進し、非空の `owned-paths.json`（`code` および `DOCS_SEPARATE=true` 時の `docs`）および `<old_sha>..HEAD` 変更ファイルと重ならず、`pre_worktree`（worktree 未作成、`old_head/new_head` は両方 `null`）または clean な線形 worktree（`merge-tree` 非衝突）であり、各対象リポジトリの累計前進回数が 3 回以内で、`advance-premise.txt` に非空の前提確認が書かれているとき、`inspect-advance` → `advance`（rebase・古い検証記録削除・`base-advances.jsonl` 追記・state JSON 一括更新・`$SESSION/base-env.bash` 更新）→ `--set-verify-cmds` → `reverify`（全必須コマンド終了コード 0・`reverified.json` と `checks.json` 保存）→ PR 本文への全前進の旧/新 SHA（7 桁以上）と必須検証コマンド記載 → `diff` → `publish` → `pr` が、失敗後の別シェル再開や連続前進（上限 3 回）を含めて終了コード 0 で成功すること。
  - **拒否する反例・境界条件（負例、すべて副作用や部分更新を残さず終了コード 2 で拒否）:**
    1. `--write-state` の既存ファイルまたは `initial.json` に対する再実行、symlink 指定、`code-base.json` / `docs-base.json` の手動書き換え、`base-advances.jsonl` の欠損・連鎖不一致・レコードスキーマ違反（`pre_worktree` で `old_head/new_head` が `null` でない、`worktree` で 40 桁小文字 hex SHA でない、`DOCS_SEPARATE=false` で `target == "docs"` がある等）。
    2. `CODE_BRANCH` または `DOCS_SEPARATE=true` 時の `DOC_BRANCH` が既に `origin` に存在する状態（`publish` 途中で `DOC_BRANCH` だけ push 済みの場合や PR 作成前を含む）での `--inspect-advance` / `--advance`、および push 後の `pr` ブロックでの base 移動。
    3. base 未移動、非 fast-forward 変化（巻き戻し・別系統への差し替え）、空の所有パス配列（`{"code": []}` や `DOCS_SEPARATE=true` 時の `docs: []`）、`..`・`.`・先頭 `/`・空文字を含む不正な所有パス、正規化後の同一パス重複（親ディレクトリと配下ファイルの和集合は受理）、worktree の片方のみ存在、未コミット変更、`<old_sha>..HEAD` のマージコミット、`<old_sha>..HEAD` 変更ファイルとの重複、`merge-tree` 衝突、対象ごとの累計前進 3 回超過（4 回目）、`--inspect-advance` 後〜`--advance` 前のさらなる remote / worktree 変化。
    4. 古い `checks.json` から `required-verify-cmds.json` を自動生成しないこと（古い `checks.json` は `--advance` で削除）、`--set-verify-cmds` 後のコマンド削減・`cwd` 変更・差し替え、`--reverify` への不完全なコマンド一覧指定、`--reverify` 内の非 0 終了コマンド（`reverified.json` と `checks.json` を残さない）、`--reverify` 省略、`--reverify` 成功後の追加コミット（stale HEAD）や未コミット変更・ログ欠損/SHA-256 不一致、PR 本文での旧/新 SHA または必須検証コマンド記載欠落。

## 要件・原因・検証の対応

| Spec 要件・安全境界 | 担当 Task | 観測できる結果・検証手段 |
| --- | --- | --- |
| `--write-state` による `initial.json` 排他保存と二重捕捉拒否（Spec 1.1） | Task 1, Task 2 | `test_resolve_base.py::test_advance_guards_and_state_chain`、`test_base_workflow.py`（`capture` ブロック実行） |
| 非空の `owned-paths.json`（`code` / `docs` 両対応）と、正規化後の同一パス重複・不正パスの拒否、親ディレクトリ + 配下ファイルの和集合の受理（Spec 1.2, 1.3） | Task 1 | `test_resolve_base.py::test_advance_guards_and_state_chain`（空リスト拒否、`code` の同一パス重複拒否、`DOCS_SEPARATE=true` の `docs` の同一パス重複拒否、親子の和集合での非重複成功と、変更ファイルが親ディレクトリ配下と重なる場合の拒否） |
| `pre_worktree`（`TARGET_ROOT` / `PARENT_ROOT` 使用、`old_head/new_head: null`）と `worktree` rebase・失敗時ロールバック・上限 3 回（Spec 1.3, 1.4） | Task 1 | `test_resolve_base.py::test_advance_guards_and_state_chain`（`pre_worktree` → ゲート通過、非 FF・push 済み・変更重複・衝突・dirty 時の無副作用拒否、3 回成功と 4 回目拒否） |
| `--set-verify-cmds`（`cwd: code/docs/parent` 正規化、差し替え拒否、古い `checks.json` 非流用）と `--reverify`（非 0 終了拒否、ログ SHA-256）（Spec 1.4, 1.5） | Task 1 | `test_resolve_base.py::test_advance_guards_and_state_chain`（古い `checks.json` 削除、不完全コマンド拒否、`exit 1` 拒否、`cwd: "docs"` 成功、stale HEAD 拒否） |
| `--check-publish-gate`・`--check-pr-gate`（通常 run の即時 0 終了、前進時の連鎖・再検証・PR 本文記載の強制）（Spec 1.6） | Task 1, Task 2 | `test_resolve_base.py`（全既存 8 件 + 新規 1 件）、`test_base_workflow.py`（全既存ケース + 新規 `test_unpushed_base_advance_requires_reverify_and_pr_record`） |
| `SKILL.md` の実行ブロック自己完結（`|| exit 2`、`$SESSION/base-env.bash`、失敗後の別シェル復帰、`scan-before-push.sh` / `advance` 後の連続前進追随、4 章非編集）（Spec 2.1–2.3, D5） | Task 2（統合確認兼務） | `test_base_workflow.py::test_unpushed_base_advance_requires_reverify_and_pr_record`、`git diff` による 4 章無変更確認、`bash scripts/check-layout.sh`、隔離 `mktemp -d` 手動検証 |

## 実行予算と contingency（代替策）

### 実行予算

- **Issue 全体の能動時間予算:** 270 分（`$SESSION/budget.jsonl` で計測中。Spec 作成 + Spec レビュー 2 回で約 65 分経過、残り約 205 分）。
- **フェーズ目安:**
  - Plan 作成・コミット・`owned-paths.json` / `verify-cmds.json` 固定: 15 分
  - Task 1 実装委譲 + SDD Task レビュー + 修正（必要時）: 55 分
  - Task 2 実装委譲 + SDD Task レビュー + 修正（必要時）: 55 分
  - 最終全体検証・隔離手動検証・Gitleaks scan・push・PR 作成: 20 分
  - `--merge` ループ（`pr-review-fix-loop` 1〜3 サイクル + `finalize.py`）: 60 分
- **worker 期限・無進捗打ち切り:**
  - `implement` worker 期限: 90 分（`.devcontainer/agent-runner.toml` 既定）。
  - 生存・進捗確認間隔: 600 秒（10 分）。2 回連続（20 分）で出力ログが増えず子プロセスも無ければ stall として扱い確認・打ち切る。
- **失敗の種類ごとの再試行上限:**
  - 同一失敗署名に対する `implement_task.py run` の再試行（`retry` / `rejected`）: 各 Task あたり最大 1 回（初回と合わせて最大 2 試行）。Task レビュー指摘の修正依頼は 1 サイクル（重大・重要指摘が残ればさらに 1 回まで）。上限到達または `verdict: failed` / 停止未確認時は `self` で引き取らず直ちに停止する。
- **checkpoint 時点:** 能動時間の 50%（135 分）・80%（216 分）・100%（270 分）および各 Task 完了時。
- **縮小・切り出し・方法変更の候補:**
  - 80% 超過時は PR 修正ループでの軽微な文面調整を深追いせず安全条件（S）の収束を優先する（ただし必須検証・安全ゲート・全既存テスト維持は縮小しない）。

### contingency（代替策）

1. **最初の RED で CLI 引数や既存 helper 関数の型・挙動の細部が想定と異なった場合:** Spec の安全境界と外部仕様が変わらない範囲（内部補助関数の分割や `argparse` の排他検証方法の調整）であれば SDD ledger（`progress.md`）に理由を記録して継続する。Spec の安全条件・編集禁止範囲が変わる場合は停止して報告する。
2. **外部実装担当（`pi_opencode-go_deepseek4-flash_max`）が `retry`（`NEEDS_CONTEXT` 等）を返した場合:** 不足していた既存コード引用やエラー出力を `prompt` に補って新しい `RUN_DIR` で 1 回だけ再依頼する（前の `RUN_DIR` は先に `cleanup` する）。`failed` または再試行上限到達時は `self` で実装せず、Herdr ペイン名規則に従って停止報告を行う。
3. **本作業中に `origin/main` が前進した場合:** 利用者の明示委任に従い、未 push であれば新 `origin/main` へ rebase して `code-base.json` を更新し、全検証を新 `(base, HEAD)` でやり直してから公開・PR 作成へ進む。PR 作成後であれば `pr-review-fix-loop` / `review-fix-planning` の既存の `base_moved` 一時マージ再検証経路で続行する。

---

## Task 1: `resolve_base.py` の前進検査・rebase・再検証・公開/PR ゲート実装と単体 S テスト

- **担当ファイル（`allowed_files`）:**
  - `.agents/skills/issue-to-pr/scripts/resolve_base.py`
  - `.agents/skills/issue-to-pr/tests/test_resolve_base.py`
- **テストの要否と理由:** **要（区分 `S`）**。`--write-state` の上書き防止、push 済み・非 fast-forward・所有パスの同一重複・変更ファイルの包含重複・衝突・上限超過時の拒否、必須検証コマンドの改ざん・省略・失敗・stale HEAD の拒否は、壊れてもエラーにならず未検証の `(base, HEAD)` 公開や公開済み履歴の破壊を招く `S` に当たる。既存の 8 テストはすべて維持し、新規テストは重複（`D`）を避けて 1 関数 `test_advance_guards_and_state_chain` に集約する。引数不足や `--help` のテスト（`L`）は書かない。

### 実装仕様（Task 1）

1. **既存モードの完全互換と `--write-state <path>`:**
   - 既存の `--checkout`・`--repo`・`--base`・`--required-base`・`--expected-sha` 呼び出し（新モードフラグ無し）は今までどおり動くこと。
   - `--write-state <path>`（任意の `Path`）が指定された場合:
     - `resolve_base(...)` が成功した後にだけファイル作成を行う（失敗時は何も作らず終了コード 2・標準出力空）。
     - `<path>`（例: `code-base.json`）と `initial_path = path.with_name(f"{path.stem}.initial{path.suffix}")`（例: `code-base.initial.json`）の親ディレクトリが実在する非 symlink ディレクトリであること、および両ファイルがまだ存在せず symlink でもないことを確かめ、`os.open(..., os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)` で両方とも同じ JSON（末尾改行付き）を書き出す。片方の作成後に他方が失敗した場合は作った方を消して終了コード 2 を返す。
     - `--write-state` 指定時はファイルへ書き出し、標準出力には何も出さない（未指定時は従来どおり JSON を標準出力に出す）。

2. **共通検証ヘルパー（標準ライブラリのみ）:**
   - 通常ファイル読み取りは `path.is_symlink()` や `not path.is_file()` をすべて `ValueError`（終了コード 2）で拒否する。
   - `$SESSION` は実在する非 symlink ディレクトリであることを検証する。
   - `$SESSION/target.json` を読み、`code_root`（`TARGET_ROOT`）・`parent_root`（`PARENT_ROOT`）・`repository`・`document_repository` がすべて空でない文字列であることを検証し、`docs_separate = (document_repository != repository)` とする。`TARGET_ROOT` について `resolve_base` と同じ checkout 検証（`require_tracked_cwd`、`--show-toplevel` 一致、`supported(repository)`、通常ツールなら `managed_target(repo, code_root=TARGET_ROOT)`、および `require_origin(TARGET_ROOT, repo)`）を行い、`docs_separate` が `True` なら `PARENT_ROOT` についても同様に `"usaturn/create-reso-world"` として checkout・origin 検証を行う。
   - 状態 JSON（`code-base.json`・`code-base.initial.json`、および `docs_separate` 時は `docs-base.json`・`docs-base.initial.json`）を読み、5 キー（`repo`・`remote == "origin"`・`branch`・`ref == f"refs/heads/{branch}"`・40 桁小文字 hex の `sha`）を検証する。
   - **`base-advances.jsonl` の検証:**
     - ファイルが存在しない場合は空リスト `[]`。存在する場合は通常ファイル（symlink 不可）かつ 1 行以上の非空 JSONL であることを要求し（空ファイルは不正）、各行の JSON オブジェクトが次の全項目を持つことを検証する:
       - `target`: `"code"` または `"docs"`（`not docs_separate` のとき `"docs"` は `ValueError`）
       - `repo`: 非空文字列。`target == "code"` なら `supported(record["repo"]) == repo`、`"docs"` なら `supported(record["repo"]) == "usaturn/create-reso-world"`
       - `branch`: 対象側の state JSON の `branch` と一致
       - `ref`: `f"refs/heads/{branch}"` と一致
       - `old_sha`, `new_sha`: 40 桁小文字 hex SHA であり `old_sha != new_sha`
       - `phase`: `"pre_worktree"` または `"worktree"`
       - `old_head`, `new_head`: `phase == "pre_worktree"` のときは **両方 `None`（JSON `null`）**、`phase == "worktree"` のときは **両方 40 桁小文字 hex SHA**。それ以外は `ValueError`
       - `changed_files`: `list[str]`（全要素が `str`）
       - `premise_note`: `isinstance(..., str)` かつ `.strip() != ""`
     - 連鎖検証関数 `_verify_state_chain(...)`:
       - `"code"` レコード列について: 0 件なら `code_state["sha"] == code_initial["sha"]`。1 件以上なら先頭の `old_sha == code_initial["sha"]`、隣接要素で `prev["new_sha"] == curr["old_sha"]`、末尾の `new_sha == code_state["sha"]`。
       - `docs_separate` が `True` なら `"docs"` レコード列についても同様に `docs_initial["sha"] -> ... -> docs_state["sha"]` を検証する。
   - **`owned-paths.json` の検証:**
     - JSON オブジェクトを読み、`code` が 1 件以上の `list[str]` であること、`docs_separate` が `True` なら `docs` も 1 件以上の `list[str]`、`False` なら `docs` は省略または `[]`（非空なら `ValueError`）であることを検証する。
     - 各パスの正規化: 空文字列・NUL 文字・先頭 `/`・バックスラッシュを拒否し、`stripped = raw.rstrip("/")` が空・`"."` の場合や `stripped.split("/")` に `""`・`"."`・`".."` が含まれる場合は `ValueError`。
     - リスト内の重複判定: 正規化後の文字列が完全一致する場合（例: `docs/superpowers/specs` と `docs/superpowers/specs/`）だけを `ValueError` とする。親ディレクトリと配下ファイル（例: `src/ours` と `src/ours/file.txt`）は和集合として受理する。
     - 前進した base の変更ファイルと所有パスとの重なり判定: `a == b or a.startswith(b + "/") or b.startswith(a + "/")`（双方向のディレクトリ包含・ファイル一致）。

3. **新 CLI モード（相互排他。既存の通常捕捉モードとも排他）:**
   - **`--inspect-advance`:**
     - 引数: `--session <Path>`、`--owned-paths-file <Path>`、`--code-root <Path>`、`--code-branch <str>`、`--doc-root <Path>`（省略時 `code_root`）、`--doc-branch <str>`（省略時 `""`）、`--max-advances <int>`（既定 `3`、`>= 1`）。
     - `_verify_state_chain` を検証する。
     - `validate_branch(code_branch, TARGET_ROOT)`（および `docs_separate` 時は `doc_branch` が非空で `validate_branch(doc_branch, PARENT_ROOT)`）。
     - **未 push 検査:** `git(TARGET_ROOT, "ls-remote", "--refs", "origin", f"refs/heads/{code_branch}", transport_auth=True)` が空文字列であること（注意: `--exit-code` を付けないこと。未存在時に終了コード 0・空出力になる）。`docs_separate` 時は `PARENT_ROOT` の `refs/heads/{doc_branch}` も空文字列であること。非空なら `ValueError("作業ブランチが既に origin に push 済みのため rebase できません")`。
     - **worktree 存在フェーズ判定:** `code_root`（および `docs_separate` 時は `doc_root`）に `is_symlink()` があれば拒否。両方とも `not exists()` なら `phase = "pre_worktree"`、両方とも `is_dir()` なら `phase = "worktree"`、それ以外（片方だけ存在、または通常ファイル）は `ValueError`。
     - 各対象（`"code"`、および `docs_separate` 時は `"docs"`）について、`resolve_base(checkout, target_repo, state["branch"], [], None)` と同じ手順で remote 先端 `new_sha` を取得・fetch・commit 型確認する。両方とも `new_sha == old_sha` なら `ValueError("origin の base は移動していません")`。
     - 前進している各対象について:
       - 既存 `base-advances.jsonl` の該当 `target` 件数が `max_advances` 未満であること（`>= max_advances` なら拒否）。
       - `git merge-base --is-ancestor <old_sha> <new_sha>`（終了コード 0 でなければ非 fast-forward として拒否）。
       - `git -C <checkout> diff --name-only -z <old_sha> <new_sha>` で変更ファイル一覧を取り、対応する `owned-paths`（`code` または `docs`）と 1 件でも重なれば拒否。
       - `git -C <checkout> log --format=%H%x09%s <old_sha>..<new_sha>` でコミット一覧 `[{"sha": ..., "subject": ...}]` を取る。
     - `phase == "worktree"` の場合、存在する各 worktree（`code_root`、および `docs_separate` 時は `doc_root`）について:
       - `Path(git(wt, "rev-parse", "--show-toplevel")).resolve() == wt.resolve()` かつ、`Path(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve() == Path(git(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()` であること。
       - `git(wt, "symbolic-ref", "--quiet", "--short", "HEAD") == expected_branch` であること。
       - `git(wt, "status", "--porcelain", "--untracked-files=normal") == ""` であること。
       - `old_sha` が `HEAD` の祖先であり、`git(wt, "rev-list", "--merges", f"{old_sha}..HEAD") == ""` であること。
       - その対象側が前進している場合、`git -C <wt> diff --name-only -z <old_sha> HEAD` の変更ファイルが `<old_sha>..<new_sha>` の変更ファイルと 1 件も重ならず、`head_sha != old_sha` のとき `git merge-tree --write-tree <head_sha> <new_sha>` が終了コード 0 であること。
     - 成功時は検査結果 JSON（`phase`、`docs_separate`、`owned_paths_sha256`、`targets`: `{"code": {"advanced": bool, "old_sha": ..., "new_sha": ..., "commits": [...], "changed_files": [...]}, ...}`）を標準出力に出して終了コード 0 を返す。
   - **`--advance`:**
     - 引数: `--inspect-advance` と同じ引数 + `--inspection <Path>` + `--premise-file <Path>`。
     - `--premise-file` が非空の通常ファイルであること、`--inspection` JSON を読み、現在の `--inspect-advance` 再実行結果と `phase`・`docs_separate`・`owned_paths_sha256`・各 `targets[k]["old_sha"]`・`targets[k]["new_sha"]`・`targets[k]["advanced"]` が完全一致することを検証する。
     - `phase == "worktree"` の場合、前進した対象の worktree を順に `rebase --onto <new_sha> <old_sha>` する（事前に各 `old_head` を記録し、失敗時は `rebase --abort` と既 rebase 側の `reset --hard <old_head>` で完全ロールバックして終了コード 2）。成功後は各 `new_head` を記録する（`phase == "pre_worktree"` では `old_head = None, new_head = None`）。
     - 古い `$SESSION/reverified.json`・`$SESSION/checks.json`・`$SESSION/code-sha.txt`・`$SESSION/docs-sha.txt` が存在すれば削除する（symlink があっても `unlink` し、古い `checks.json` から `required-verify-cmds.json` を作らない）。
     - 前進した各対象のレコードを `$SESSION/base-advances.jsonl` に追記し、`code-base.json`（および `docs` 前進時は `docs-base.json`）を同ディレクトリの一時ファイル + `os.replace` で一括更新し、更新結果 JSON を標準出力に出して終了コード 0 を返す。
   - **`--set-verify-cmds`:**
     - 引数: `--session <Path>`、`--commands-file <Path>`。
     - `$SESSION/target.json` から `docs_separate` を読む。`--commands-file` の JSON 配列（1 件以上）を正規化する:
       - 要素が `list` なら `{"cwd": "code", "argv": elem}`、要素が `dict` ならキーが `{"cwd", "argv"}` のみで `cwd in ("code", "docs", "parent")`（ただし `not docs_separate` で `cwd == "docs"` は拒否）。`argv` は 1 要素以上の `list[str]` で `argv[0].strip() != ""` かつ全要素が NUL を含まない `str`。
     - `$SESSION/required-verify-cmds.json` が存在しなければ排他作成（`"x"` モード）で保存して終了コード 0。既に通常ファイルとして存在する場合は、内容が正規化後のリストと完全一致するときだけ終了コード 0 を返し、1 箇所でも異なれば終了コード 2 で拒否する。
   - **`--reverify`:**
     - 引数: `--session <Path>`、`--commands-file <Path>`（省略可）、`--code-root <Path>`、`--doc-root <Path>`（省略時 `code_root`）。
     - `$SESSION/required-verify-cmds.json` を読み検証する。`--commands-file` 指定時は正規化後に完全一致することを検証する。
     - `base-advances.jsonl` が 1 件以上あり `_verify_state_chain` が成立すること、remote の現在の先端 SHA が `code-base.json["sha"]`（および `docs_separate` 時は `docs-base.json["sha"]`）と一致すること、`code_root`（および `docs_separate` 時は `doc_root`）が検証済み worktree で clean であり各 base SHA が各 `HEAD` の祖先であることを検証する。
     - 既存の `reverified.json`・`checks.json` があれば先に削除する。
     - 各コマンド `i`（`1` 始まり）を `cwd_map = {"code": code_root, "docs": doc_root, "parent": parent_root}[entry["cwd"]]`、`env=git_environment(transport_auth=False)` で同期実行し、stdout + stderr を `$SESSION/reverify-{i}.log`（通常ファイル、symlink 拒否）に書き出す。`returncode != 0` なら直ちに `ValueError` で終了コード 2（`reverified.json`・`checks.json` 無し）。
     - 全コマンド成功後、再度 worktree が clean で `HEAD` と remote base SHA が変化していないことを検証し、`$SESSION/reverified.json` と `$SESSION/checks.json` を一時ファイル + `os.replace` で書き出し、結果 JSON を標準出力に出して終了コード 0 を返す。
   - **`--check-publish-gate` と `--check-pr-gate`:**
     - `--check-publish-gate` 引数: `--session <Path>`、`--code-root <Path>`、`--doc-root <Path>`（省略時 `code_root`）。
     - `--check-pr-gate` 引数: 上記 + `--code-pr-body <Path>`、`--doc-pr-body <str>`（空文字または省略可、`docs_separate` で `"docs"` 前進があるときは必須）。
     - Spec 1.6 のとおり、未前進の通常 run（`code_state["sha"] == code_initial["sha"]`、該当時は `docs_state["sha"] == docs_initial["sha"]`、かつ `base-advances.jsonl` 不在）なら両方とも即座に終了コード 0 を返す。
     - 前進あり（または初期値不一致）のときは Spec 1.6 の全項目（連鎖とスキーマ、`required-verify-cmds.json` と `reverified.json` の全フィールド・`advance_count`・`required_verify_sha256`・worktree clean と HEAD 一致・ログ実在と `log_sha256`、さらに `--check-pr-gate` では `code-sha.txt` / `docs-sha.txt` 一致および PR 本文への各前進 `old_sha[:7]`・`new_sha[:7]` と各必須コマンド `" ".join(argv)` または `shlex.join(argv)` の記載）を検証し、1 項目でも欠ければ終了コード 2 で拒否する。

### ステップ（Task 1）

- [ ] **Step 1: 失敗する単体 S テスト `test_advance_guards_and_state_chain` を `.agents/skills/issue-to-pr/tests/test_resolve_base.py` に追加する**
  - 既存の 8 テスト関数は一切削らず維持する。
  - Spec 3.1 の全検証項目（`--write-state` 二重実行拒否、未前進時の両ゲート即時 0、`pre_worktree` 前進→worktree 作成→`--set-verify-cmds`→`--reverify`→両ゲート通過、空 `owned-paths` 拒否、正規化後の同一パス重複と親子包含の受理・変更ファイルの包含重複拒否、非 FF・push 済み・`code` の同一パス重複・`DOCS_SEPARATE=true` の `docs` の同一パス重複と `"cwd": "docs"` 成功・変更重複・`merge-tree` 衝突・dirty 時の無副作用拒否、3 回成功と 4 回目拒否、古い `checks.json` 非流用、`--set-verify-cmds` 差し替え拒否、不完全コマンド拒否、`exit 1` コマンド拒否、stale HEAD 拒否）をカバーする。
- [ ] **Step 2: RED を確認する**
  - Run: `uv run --project /workspaces/reso-world/.worktrees/issue-378-rebase-base --locked pytest .agents/skills/issue-to-pr/tests/test_resolve_base.py -k test_advance_guards_and_state_chain`
  - Expected: 未実装の新フラグにより FAIL（既存 8 テストは PASS）。
- [ ] **Step 3: `.agents/skills/issue-to-pr/scripts/resolve_base.py` に上記機能を実装する**
  - 標準ライブラリと `git_env.py`・`resolve_issue.py` のみを使用する。エラーメッセージに transport の生 URL・認証情報を含めない既存方針を維持する。
- [ ] **Step 4: GREEN と退行なしを確認する**
  - Run: `uv run --project /workspaces/reso-world/.worktrees/issue-378-rebase-base --locked pytest .agents/skills/issue-to-pr/tests/test_resolve_base.py`
  - Expected: 9 passed（既存 8 + 新規 1）。
  - Run: `bash scripts/check-layout.sh`
  - Expected: exit 0。
- [ ] **Step 5: コミットする**
  - Commit message: `feat(issue-to-pr): add unpushed base advance, reverify, and publish/pr gates`

---

## Task 2: `SKILL.md` の手順・実行ブロック更新とワークフロー統合 S テスト（統合確認を含む）

- **担当ファイル（`allowed_files`）:**
  - `.agents/skills/issue-to-pr/SKILL.md`
  - `.agents/skills/issue-to-pr/tests/test_base_workflow.py`
- **編集禁止の厳守:** `.agents/skills/issue-to-pr/SKILL.md` の **4 章（`## 4. 推奨案 → Spec → Plan → 実装` の見出し行から `## 5. 検証・PR・完了` の直前行まで）には一切変更を加えないこと**（`git diff` で 4 章に差分が無いことを確認する）。Plan コミット直後の `owned-paths.json` 更新や `--set-verify-cmds` 固定の説明は 2 章 6 と 5 章の側に書く。
- **テストの要否と理由:** **要（区分 `S`）**。`SKILL.md` の実シェルスニペットからゲート呼び出しや `|| exit 2`、別シェル用の `base-env.bash` 保存が落ちると、未検証のまま push・PR 作成されたり復帰不能になる `S` の損害が生じる。`SKILL.md` の文章を文字列検索する `F` テストは書かず、`procedure(<name>)` で抽出した実 Bash ブロックを実行する統合テスト `test_unpushed_base_advance_requires_reverify_and_pr_record` 1 件を `test_base_workflow.py` に追加し、全既存ケースを維持する。

### 実装仕様（Task 2）

1. **`.agents/skills/issue-to-pr/SKILL.md` の更新箇所（すべて各コマンドに明示的な `|| exit 2` を付ける）:**
   - **2 章 3（76 行付近）の最小整合注記:**
     - 「終了コードが 0 でないブロックの後は、次のブロックへ進まない。base の取得をやり直して SHA を差し替えない。」を「終了コードが 0 でないブロックの後は、そのまま次のブロックへ進まない（未 push の base 前進で 2 章 6 の前進追随フローに入る場合を除く）。2 章 6 の未 push 条件付き前進追随の手順を除き、base の取得をやり直して SHA を差し替えない。」に更新し、`$SESSION/base-env.bash` による別シェル復元の説明を 1 文添える。
   - **2 章 6（`<!-- base-workflow:capture -->` と未 push 前進追随手順・ブロック）:**
     - `<!-- base-workflow:capture -->` で `resolve_base.py` に `--write-state "$SESSION/code-base.json"`（および `DOCS_SEPARATE != false` 時は `--write-state "$SESSION/docs-base.json"`）を渡し、末尾で `TARGET_ROOT`・`TARGET_REPO`・`PARENT_ROOT`・`DOCS_SEPARATE`・`CODE_BASE_BRANCH`・`CODE_BASE_SHA`・`SKILL_DIR`（`DOCS_SEPARATE != false` 時は `DOC_BASE_SHA` も）を `export` + `declare -p` で `$SESSION/base-env.bash` に書き出す。`CODE_ROOT`・`CODE_BRANCH` が設定済みなら `DOC_ROOT`（既定は `CODE_ROOT`）・`DOC_BRANCH` も追記し、最後に `recheck_bases` 関数を追記する。
     - `capture` の説明の後に、`owned-paths.json` の初期作成（`capture` 直後）と Plan コミット直後のリポジトリ別振り分け更新（`DOCS_SEPARATE=false` なら全パスを `code`、`true` なら `CODE_ROOT` 側を `code`・`DOC_ROOT` 側 Spec/Plan 等を `docs`、空配列不可）、および未 push のすべての base 移動失敗点（`worktree`・5 章冒頭・`diff`・`publish` の push 前 `recheck_bases` と `scan-before-push.sh` の `--expected-base-sha` 不一致・`advance` 末尾の `recheck_bases`）からの復帰ループ（`inspect-advance` → `preflight`・`checkout_policy`・外部仕様・共有インターフェース・`AGENTS.md` の前提確認と `$SESSION/advance-premise.txt` 作成 → `advance` → `worktree` または `reverify` → PR 本文更新 → `diff` → `publish` → `pr`、上限 3 回、push 済みや条件不成立は停止）を明記し、次の 2 ブロックを置く:
       - `<!-- base-workflow:inspect-advance -->`:
         ```bash
         set -euo pipefail
         if [ -f "$SESSION/base-env.bash" ]; then
           source "$SESSION/base-env.bash" || exit 2
         fi
         git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
         while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
         uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
           --inspect-advance --session "$SESSION" \
           --owned-paths-file "$SESSION/owned-paths.json" \
           --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
           --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
           > "$SESSION/advance-inspection.json" || exit 2
         ```
       - `<!-- base-workflow:advance -->`:
         ```bash
         set -euo pipefail
         if [ -f "$SESSION/base-env.bash" ]; then
           source "$SESSION/base-env.bash" || exit 2
         fi
         git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
         while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
         TARGET_ROOT="${TARGET_ROOT:-$(jq -er .code_root "$SESSION/target.json")}" || exit 2
         TARGET_REPO="${TARGET_REPO:-$(jq -er .repository "$SESSION/target.json")}" || exit 2
         PARENT_ROOT="${PARENT_ROOT:-$(jq -er .parent_root "$SESSION/target.json")}" || exit 2
         DOCS_SEPARATE="$(jq -r 'if (.document_repository | type) == "string" and (.repository | type) == "string" then .document_repository != .repository else error("target.json lacks document_repository") end' "$SESSION/target.json")" || exit 2
         DOC_ROOT="${DOC_ROOT:-$CODE_ROOT}"
         DOC_BRANCH="${DOC_BRANCH:-}"
         uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
           --advance --session "$SESSION" \
           --inspection "$SESSION/advance-inspection.json" \
           --owned-paths-file "$SESSION/owned-paths.json" \
           --premise-file "$SESSION/advance-premise.txt" \
           --code-root "$CODE_ROOT" --code-branch "$CODE_BRANCH" \
           --doc-root "${DOC_ROOT:-$CODE_ROOT}" --doc-branch "${DOC_BRANCH:-}" \
           > "$SESSION/advance-result.json" || exit 2
         CODE_BASE_BRANCH="$(jq -er .branch "$SESSION/code-base.json")" || exit 2
         CODE_BASE_SHA="$(jq -er .sha "$SESSION/code-base.json")" || exit 2
         if [ "$DOCS_SEPARATE" != false ]; then
           DOC_BASE_SHA="$(jq -er .sha "$SESSION/docs-base.json")" || exit 2
         fi
         recheck_bases() {
           uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
             --checkout "$TARGET_ROOT" --repo "$TARGET_REPO" --base "$CODE_BASE_BRANCH" \
             --expected-sha "$CODE_BASE_SHA" > "$SESSION/code-base-recheck.json" || return
           if [ "$DOCS_SEPARATE" != false ]; then
             uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
               --checkout "$PARENT_ROOT" --repo usaturn/create-reso-world --base main \
               --expected-sha "$DOC_BASE_SHA" > "$SESSION/docs-base-recheck.json" || return
           fi
         }
         export TARGET_ROOT TARGET_REPO PARENT_ROOT DOCS_SEPARATE CODE_BASE_BRANCH CODE_BASE_SHA SKILL_DIR CODE_ROOT CODE_BRANCH DOC_ROOT DOC_BRANCH
         declare -p TARGET_ROOT TARGET_REPO PARENT_ROOT DOCS_SEPARATE CODE_BASE_BRANCH CODE_BASE_SHA SKILL_DIR CODE_ROOT CODE_BRANCH DOC_ROOT DOC_BRANCH > "$SESSION/base-env.bash" || exit 2
         if [ "$DOCS_SEPARATE" != false ]; then
           export DOC_BASE_SHA
           declare -p DOC_BASE_SHA >> "$SESSION/base-env.bash" || exit 2
         fi
         declare -f recheck_bases >> "$SESSION/base-env.bash" || exit 2
         if [ -f "$SESSION/resume.bash" ]; then
           cat "$SESSION/base-env.bash" >> "$SESSION/resume.bash" || exit 2
         fi
         recheck_bases || exit 2
         ```
   - **5 章（`reverify`・`publish`・`pr`・PR 本文記載）:**
     - 最終検証の前に `$SESSION/verify-cmds.json` を用意し `recheck_bases` を確認して未 push 前進があれば先に 2 章 6 の前進追随を行うこと、および 1 回でも base 前進追随を行った run では次の `<!-- base-workflow:reverify -->` ブロックで必須検証コマンドを排他固定・実行して `$SESSION/reverified.json` と `$SESSION/checks.json` を作ることを明記する:
       ```bash
       set -euo pipefail
       git_unset="$(uv run --no-project python "$SKILL_DIR/scripts/git_env.py")" || exit 2
       while IFS= read -r git_env; do [ -z "$git_env" ] || unset "$git_env" || exit 2; done <<< "$git_unset"
       uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
         --set-verify-cmds --session "$SESSION" \
         --commands-file "$SESSION/verify-cmds.json" || exit 2
       uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
         --reverify --session "$SESSION" \
         --commands-file "$SESSION/verify-cmds.json" \
         --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}" || exit 2
       ```
     - `<!-- base-workflow:publish -->` の最初の `recheck_bases || exit 2` の直後に次を追加する:
       ```bash
       uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
         --check-publish-gate --session "$SESSION" \
         --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}" || exit 2
       ```
     - `<!-- base-workflow:pr -->` の最初の `recheck_bases || exit 2` の直後に次を追加する:
       ```bash
       uv run --no-project python "$SKILL_DIR/scripts/resolve_base.py" \
         --check-pr-gate --session "$SESSION" \
         --code-root "$CODE_ROOT" --doc-root "${DOC_ROOT:-$CODE_ROOT}" \
         --code-pr-body "$CODE_PR_BODY" --doc-pr-body "${DOC_PR_BODY:-}" || exit 2
       ```
     - PR 本文の記載項目に、base 前進追随を行った run では rebase（または worktree 作成前の再捕捉）を行ったこと・各前進の旧/新 base SHA・やり直した必須検証コマンドと結果を書くことを追加する。
   - **「停止時の報告」の最小整合注記:**
     - `base の不存在・不一致・捕捉後の移動` に `（2 章 6 の条件を満たして前進追随・再検証する場合を除く）` を補う。

2. **`.agents/skills/issue-to-pr/tests/test_base_workflow.py` の統合 S テスト追加:**
   - 既存テストと `Workflow.run` は維持する。
   - 注意点: `test_base_workflow.py` の `workflow` フィクスチャは `PATH` 先頭に `bin_dir/git` ラッパーを置いており、`SESSION` 環境変数がある状態で `git push` を呼ぶと `scans.jsonl` を要求し、`fetch` / `ls-remote` / `push` では `transports` マップを検査する。テスト準備として remote の `main` を前進させるときは、フィクスチャ外のシステム `git`（例: `shutil.which("git", path=os.defpath)` または `PATH` の 2 番目以降の `git`）で `docs-seed` から `str(workflow.remote)` に push すると安全に remote の `refs/heads/main` を前進させられる。
   - 新規テスト `test_unpushed_base_advance_requires_reverify_and_pr_record(workflow: Workflow, tmp_path: Path)` で `procedure(...)` から実ブロックを取り出し、Spec 3.2 の一連の流れを検証する:
     1. `input` → `target` → `capture` → `worktree` → `CODE_ROOT/change` コミット後、remote の `main` を所有外ファイル（例: `unrelated.txt`）のコミット `base_v2` へ前進させる。
     2. その状態で `publish` を実行すると終了コード 2 で失敗し、`workflow.remote` に `feat/issue-42-change` が push されていないこと。
     3. `code-base.json` の `sha` を手動で `base_v2` に書き換えても、`publish`（`--check-publish-gate`）が終了コード 2 で拒否し push されないこと（確認後に元の捕捉 SHA に戻す）。
     4. 失敗したブロックとは**別の新しい `bash -c` プロセス**で、`owned-paths.json`（`{"code": ["change", "docs/superpowers/specs", "docs/superpowers/specs/2026-11-12-issue-42-design.md", "docs/superpowers/plans", "docs/superpowers/plans/2026-11-12-issue-42.md"]}`）と `advance-premise.txt` を用意し、`SESSION`・`SKILL_DIR`・`PATH`・`HOME`・`GIT_CONFIG_NOSYSTEM` だけを持つ環境で `inspect-advance` → `advance` を実行すると成功し、さらに remote の `main` を 2 回目の前進 `base_v3`（例: `scan` 中または連続マージを模した 2 回目の非重複前進）へ進めて再度同じ環境で `inspect-advance` → `advance` を実行しても成功し、`source "$SESSION/base-env.bash"` した別シェルで `recheck_bases` が終了コード 0 で通ること。`resume.bash` に退避した `CUSTOM_RESUME_VAR` が保持され、`CODE_BASE_SHA` が最新値 `base_v3` になること。
     5. `reverify` を実行せずに `source "$SESSION/base-env.bash"` + `publish` を実行すると終了コード 2 で拒否され push されないこと。
     6. `verify-cmds.json`（空白を含むパスでも動く実コマンド配列）を用意し、`SESSION`・`SKILL_DIR`・`PATH`・`HOME`・`GIT_CONFIG_NOSYSTEM` だけを持つ別シェルで `reverify` を実行し、同じ環境の `diff` → `publish` が終了コード 0 で成功すること。
     7. 旧/新 SHA と再検証コマンドを書いていない `body.md` のまま再開シェルで `pr` を実行すると `gh pr create` の前に終了コード 2 で止まること。続いて 2 回分の旧/新 SHA（7 桁以上）と必須検証コマンドを `body.md` に記載して再開シェルで `pr` を実行すると終了コード 0 で PR が作られ、`workflow.remote` の `refs/heads/feat/issue-42-change` の親が `base_v3` になっていること。

### ステップ（Task 2）

- [ ] **Step 1: 失敗する統合 S テスト `test_unpushed_base_advance_requires_reverify_and_pr_record` を `.agents/skills/issue-to-pr/tests/test_base_workflow.py` に追加する**
- [ ] **Step 2: RED を確認する**
  - Run: `uv run --project /workspaces/reso-world/.worktrees/issue-378-rebase-base --locked pytest .agents/skills/issue-to-pr/tests/test_base_workflow.py -k test_unpushed_base_advance_requires_reverify_and_pr_record`
  - Expected: `SKILL.md` に `inspect-advance` 等のブロックがまだ無いため FAIL。
- [ ] **Step 3: `.agents/skills/issue-to-pr/SKILL.md` の 2 章 3・2 章 6・5 章・停止時の報告を更新する（4 章は編集しない）**
- [ ] **Step 4: GREEN・全既存テスト維持・4 章無変更・レイアウト検査を確認する**
  - Run: `uv run --project /workspaces/reso-world/.worktrees/issue-378-rebase-base --locked pytest .agents/skills/issue-to-pr/tests`
  - Expected: 全テスト PASS（124 passed）。
  - Run: `bash scripts/check-layout.sh`
  - Expected: exit 0。
  - Run: `git -C /workspaces/reso-world/.worktrees/issue-378-rebase-base diff HEAD -- .agents/skills/issue-to-pr/SKILL.md`（コミット前）または `git show -- .agents/skills/issue-to-pr/SKILL.md` で 4 章に変更が無いことを確認し、禁止日本語表現が混入していないことを確認する。
- [ ] **Step 5: コミットする**
  - Commit message: `feat(issue-to-pr): document unpushed base advance workflow and add e2e guard test`
