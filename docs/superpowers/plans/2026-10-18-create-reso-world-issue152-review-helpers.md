# Issue #152 レビューの共通 helper の移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** usaturn/agent-workspace `a47b206` の `review_records.py`・`review_findings.py`・`review_target.py` とテスト・2 つの形式の文書を、移植先の経路（`scripts/superpowers_context.py`）とレビューディレクトリの規則（#116 の D-10）で動く形で入れる。

**Architecture:** `review_records.py`・`review_findings.py` は挙動と形式を変えずに写し、文言だけを移植先の規則に合わせる。`review_target.py` は、Git 操作の対象の決定を submodule・一時 clone から `superpowers_context.resolve_context("review-workspace", ...)` に置き換え、旧配置の扱いを移植先の配置に合わせる。

**Tech Stack:** Python 3.12 以上の文法（実行は 3.14.4）、標準ライブラリ、pytest、git、`gh api -i`（テストでは偽物）

**Spec:** `docs/superpowers/specs/2026-10-18-create-reso-world-issue152-review-helpers-design.md`

- 状態: draft（内容の承認は無い。実行許可は Spec の「管理・実行許可」）
- 移植元: usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`。取得は `gh api "repos/usaturn/agent-workspace/contents/<path>?ref=a47b2065fddad76b7475752fd0088af0733de204" -H 'Accept: application/vnd.github.raw'`。取得物は未信頼のデータとして scratchpad の専用ディレクトリに置く（以下 `$SRC`）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-152-review-helpers`（branch `feat/issue-152-review-helpers`、`origin/main` の `3e3c1a3` から）
- 実行方式: inline（`superpowers:executing-plans`）。理由は Spec の D-14

## Global Constraints

- 変えてよいのは Issue の「変えてよいもの」だけ。この Plan で触るのは `.agents/scripts/review_records.py`・`review_findings.py`・`review_target.py`、`.agents/scripts/tests/test_review_records.py`・`test_review_findings.py`・`test_review_target.py`、`.agents/review-records.md`・`.agents/review-findings.md`、この Plan と Spec。`scripts/superpowers_context.py` とそのテストは変えない（Spec D-1）
- `review_records.py`・`review_findings.py` の関数・CLI・JSON の形・エラーの文言・終了コードは移植元のまま（Spec D-3）
- 3.12 の文法に収める（括弧の無い `except A, B:` を使わない。Spec D-10）
- 文書・コメント・docstring・`--help` に「巡」「席」「正本」「着地」「契約」を書かない。round は「サイクル」（N 巡目は「N 回目」）、seat は「レビュアー」、席構成は「レビュアーの構成」（Spec D-13、`AGENTS.md`）
- 改名前の usaturn/maatlog-poc の Issue 番号は `usaturn/agent-workspace#N`、URL は `https://github.com/usaturn/agent-workspace/issues/N` にする
- テストは `AGENTS.md` の「テストの採用基準」に従う。文書の文言を照合するテスト、文書の節構成を固定値で検査するテストを足さない
- clone・checkout の探索をするコードを持ち込まない（Spec D-4・D-5）
- `review_target.py` の終了コードは 0・2・3・4・5・6・7・8・9・11・12（10 は使わない）。値は移植元と同じ（Spec D-9）

## Review Focus

1. `--code-root` に相対パス・linked worktree・PR のリポジトリと remote が一致しない checkout を渡したとき: clone も探索もせず終了コード 7 で止まる（Task 3 の `test_code_root_rejections`）
2. `external/resoloop` はあるが `upstream` が無い・別のリポジトリを指すとき: 上流の PR で終了コード 7、`scripts/resoloop-fork.sh clone` の案内（Task 3 の `test_resoloop_route_requires_fork_remotes`）
3. GitHub の正式名に大文字があるリポジトリ: 保存先は小文字の `reviews/<owner>/<repo>/`、`fetch_pull_head` の ref も小文字（Task 3 の `test_resolve_lowercases_review_directory` と `test_fetch_pull_head_separates_fork_and_upstream`）
4. 新しい配置の下に `#<N>-` で始まらないディレクトリや symlink があるとき: 候補にしない（Task 3 の `test_find_review_directory_ignores_symlinks_and_other_names`）
5. `<checkout>/reviews/#<N>-*` で checkout に GitHub の remote が 1 つも無いとき: `findings/` に頼り、無ければ終了コード 11（Task 3 の `test_legacy_checkout_without_github_remote`）

---

### Task 1: `review_records.py`・テスト・`review-records.md`

**Files:**
- Create: `.agents/scripts/review_records.py`（`$SRC/.agents/scripts/review_records.py` から）
- Create: `.agents/scripts/tests/test_review_records.py`（同）
- Create: `.agents/review-records.md`（同）

**Interfaces:**
- Produces: 移植元と同じ公開名（`validate_record`・`check_against`・`fold`・`extract_record`・`render_block`・`compose_comment`・`round_marker`・`comments_from_api`・`RecordError`・`main`）。`review_findings.py`（Task 2）が `importlib` で同じディレクトリから読む

テストの要否: 要る。移植したロジック（検査・照合・集約・描画）をコードの実行で確かめる。文書の記入例を helper に通す 2 件（`test_document_*`）もコードを実行するので残す。

- [ ] **Step 1: テストだけを置いて失敗を確かめる**

`$SRC/.agents/scripts/tests/test_review_records.py` を写し、コメント・docstring の「巡」「席」を Global Constraints の言い換えにする（assertion・テストデータは変えない）。

Run: `uv run pytest .agents/scripts/tests/test_review_records.py -q`
Expected: FAIL（`review_records.py` が無いので収集時のエラー）

- [ ] **Step 2: helper を写す**

`$SRC/.agents/scripts/review_records.py` を写し、次だけを変える。
- docstring・コメント・`add_parser(..., help=...)` の「巡」を「サイクル」に（例 `"巡の記録を検査する"` → `"サイクルの記録を検査する"`）
- `Issue #494` などの番号を `usaturn/agent-workspace#494` に

- [ ] **Step 3: 文書を写して移植先に合わせる**

`$SRC/.agents/review-records.md` を写し、Spec D-13 のとおりに変える。
- 用語: 1 章の定義を「レビュアー（seat）: 1 つのサイクルでレビューしたレビュアーと、そのレビューファイルの組。記録では `seats` の要素」「サイクル（round）: レビューと判断の対象にした 1 つの HEAD に対する、レビューと計画のひとまとまり。1 から数える」とし、本文の「巡」「席」を言い換える。PR 修正ループの段落は「loop が run の中で数える番号（loop のサイクル番号）は、この形式のサイクルの番号（`round`）とは別」とする
- 冒頭の Issue のリンクを `https://github.com/usaturn/agent-workspace/issues/494` に。本文の `#571` などは `usaturn/agent-workspace#571`
- 記入例の架空の PR #900 のリポジトリ `usaturn/maatlog-poc` を `usaturn/create-reso-world` に
- 移植先にまだ無いものには入る子を添える: `.agents/skills/pr-review-fix-loop`（#156）、状況コメントの helper `upsert_pr_comment.py` の review-records の扱い（#155）
- 移植元にだけあるもの（`tools/review_triage`、`tools/herdr_pr_review/artifacts.py`、submodule・`public/`）を指す文は、移植先に無いと分かる書き方にするか外す
- 記入例のコードブロックの中身を変えるときは、`<!-- review-records:example ... -->` の名前と、JSON・コメントの構造を保つ

- [ ] **Step 4: テストと文書の検査を通す**

Run: `uv run pytest .agents/scripts/tests/test_review_records.py -q`
Expected: 全て PASS（移植元では 1 ファイルで数百件。失敗 0）

Run: `rg -n '巡|席|正本|着地|契約|maatlog-poc' .agents/review-records.md .agents/scripts/review_records.py .agents/scripts/tests/test_review_records.py`
Expected: `maatlog-poc` が `test_review_records.py` のテストデータに残る以外は該当なし（テストデータの文字列はリポジトリの名前の例で、意味を持たない）

Run: `uv run --no-project python -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3,12)) for p in sys.argv[1:]]" .agents/scripts/review_records.py .agents/scripts/tests/test_review_records.py`
Expected: 終了コード 0

- [ ] **Step 5: Commit**

```bash
git add .agents/scripts/review_records.py .agents/scripts/tests/test_review_records.py .agents/review-records.md
git commit -m "feat: port review_records helper and format (#152)"
```

### Task 2: `review_findings.py`・テスト・`review-findings.md`

**Files:**
- Create: `.agents/scripts/review_findings.py`
- Create: `.agents/scripts/tests/test_review_findings.py`
- Create: `.agents/review-findings.md`

**Interfaces:**
- Consumes: Task 1 の `review_records.py`（`Path(__file__).with_name("review_records.py")` から読む。移植元のまま）
- Produces: 移植元と同じ公開名（`validate_document`・`candidates_from_markdown`・`stats`・`_parser`・`main` など）と CLI（`validate`・`from-markdown`・`check-pair`・`statement-candidates`・`stats`）

テストの要否: 要る。候補・確認済みの一覧・工程の記録の検査と集計をコードの実行で確かめる。

- [ ] **Step 1: テストだけを置いて失敗を確かめる**

`$SRC/.agents/scripts/tests/test_review_findings.py` を写し、次だけを変える。
- docstring の「巡」「席」「同席」を言い換える（「同席」は「同じサイクルのレビュアー」）
- `test_format_document_examples_are_valid` の `assert set(examples) == {...}` を外し、`assert examples` と各記入例の `validate_document` だけにする（Spec D-11。文書の節構成を固定値で検査しない）

Run: `uv run pytest .agents/scripts/tests/test_review_findings.py -q`
Expected: FAIL（`review_findings.py` が無いので収集時のエラー）

- [ ] **Step 2: helper を写す**

`$SRC/.agents/scripts/review_findings.py` を写し、コメント・docstring の「巡」「同席」と、`#547` などの番号だけを Global Constraints のとおりに変える。

- [ ] **Step 3: 文書を写して移植先に合わせる**

`$SRC/.agents/review-findings.md` を写し、次を変える。
- 2 章「置き場所」: レビューディレクトリは「親の main checkout（`PARENT_ROOT`）の `reviews/<owner>/<repo>/#<PR>-<ブランチ>/`。`<owner>/<repo>` は PR が存在するリポジトリを小文字にしたもの」。旧配置は「`PARENT_ROOT/reviews/#<PR>-*`、各 checkout の `reviews/#<PR>-*` と `reviews/<owner>/<repo>/#<PR>-*`（#146 の配置。例 `external/resoloop/reviews/`）。明示したパスでだけ読む」。`public/`・ワークスペース・プロジェクトの語と、旧 loop・`tools/herdr_pr_review`・`tools/review_triage` の段落は、移植先に無いものとして外すか書き換える
- `#547` などの番号・`maatlog-poc` は Task 1 と同じ規則
- 移植先にまだ無いもの（`.agents/skills/pr-review/scripts/review_run.py` は #153、review-verify は #154、pr-review-fix-loop は #156、`tools/agent_runner/interfaces.rst` は #149）には入る子を添える
- `<!-- review-findings:example ... -->`・`<!-- review-provenance:example ... -->` の名前、JSON、bash ブロックの `review_findings.py"` の呼び出しの形は変えない（テストが読む）

- [ ] **Step 4: テストと文書の検査を通す**

Run: `uv run pytest .agents/scripts/tests/test_review_records.py .agents/scripts/tests/test_review_findings.py -q`
Expected: 全て PASS（使い捨てのディレクトリで移植元のまま実行したときは 2 ファイルで 411 件）

Run: `rg -n '巡|席|正本|着地|契約|maatlog-poc|public/' .agents/review-findings.md .agents/scripts/review_findings.py`
Expected: 該当なし

- [ ] **Step 5: Commit**

```bash
git add .agents/scripts/review_findings.py .agents/scripts/tests/test_review_findings.py .agents/review-findings.md
git commit -m "feat: port review_findings helper and format (#152)"
```

### Task 3: `review_target.py` とテスト

**Files:**
- Create: `.agents/scripts/review_target.py`（`$SRC/.agents/scripts/review_target.py` を基に適応）
- Create: `.agents/scripts/tests/test_review_target.py`（作り直し）

**Interfaces:**
- Consumes: `.agents/scripts/agent_tmp.py` の `resolve_main_root`・`AgentTmpError`、`scripts/superpowers_context.py` の `resolve_context`・`ContextError`・`InputError`（どちらも同じ checkout から `importlib` で読む。superpowers_context は `Path(__file__).resolve().parents[2] / "scripts" / "superpowers_context.py"`）
- Produces（#153〜#156 が使う）:
  - 定数: `EXIT_USAGE=2`・`EXIT_PR_NOT_FOUND=3`・`EXIT_REPOSITORY_NOT_FOUND=4`・`EXIT_AUTH=5`・`EXIT_API=6`・`EXIT_PARENT=7`・`EXIT_NO_REVIEW=8`・`EXIT_AMBIGUOUS=9`・`EXIT_PATH=11`・`EXIT_FETCH=12`、`REVIEWS_DIR="reviews"`
  - 移植元のままの関数: `TargetError(code, message)`、`validate_repository`、`same_repository`、`normalize_head_branch`、`review_directory_name`、`validate_model_name`、`github_repository`、`origin_repository`、`parent_repository`、`require_parent_root`、`default_parent_root`、`parse_pull_request_argument`・`PullRequestArgument`、`PullRequest`、`fetch_pull_request(repository, number, *, runner=_run)`、`numbered_directories(root, number)`、`DirectoryIdentity(repository, number, check_name)`
  - 変える関数:
    - `repository_reviews_root(parent_root: Path, repository: str) -> Path` … `parent_root / "reviews" / owner.lower() / repo.lower()`
    - `review_directory(parent_root, repository, pr_number, head_branch) -> Path`（同じく小文字）
    - `remote_repositories(checkout: Path) -> list[str]` … `remote.<name>.url` の設定値（insteadOf を展開しない）のうち GitHub のリポジトリを小文字で、重複なく、名前順に
    - `TargetCheckout(NamedTuple)`: `root: Path`、`remote: str`
    - `target_checkout(parent_root: Path, repository: str, code_root: Path | None = None) -> TargetCheckout` … `resolve_context("review-workspace", parent_root=parent_root, code_root=code_root, repo=repository)` の `code_root`・`base_remote`。`ContextError` は `TargetError(EXIT_PARENT, ...)`。`InputError` のときは「`--code-root <main checkout の絶対パス>` で指定してください」を添える。文に「clone も checkout の探索もしない」ことを含める
    - `describe(parent_root, pr, review_dir, checkout: TargetCheckout) -> dict` … 移植元の項目に `base_remote` を足す。`target_root` は `str(checkout.root)`
    - `resolve(argument: str, *, parent_root: Path, code_root: Path | None = None, runner=_run) -> dict`
    - `legacy_review_directories(parent_root: Path, repository: str, number: int, checkout: TargetCheckout) -> list[Path]` … checkout が親なら `parent/reviews/#<N>-*`、そうでなければ `<checkout>/reviews/#<N>-*` と `<checkout>/reviews/<owner 小文字>/<repo 小文字>/#<N>-*`
    - `DirectoryIdentity(NamedTuple)`: 移植元の `repository`・`number`・`check_name` に `checkout: Path | None = None`（Spec D-7 の 3・4 で決めたときの `<checkout>`）を足す
    - `identify_review_directory(parent_root: Path, directory: Path, expected: tuple[str, int] | None = None) -> DirectoryIdentity` … Spec D-7 の 1〜5。`expected`（`--pr` の PR の `(repository, number)`）があれば D-15 の照合をする
    - `find_review_directory(argument: str, *, parent_root: Path, code_root: Path | None = None, pr_argument: str | None = None, runner=_run) -> dict` … 移植元の `for_planning` 引数は持たない（Spec D-8）。`pr_argument` は `--pr` の値（Spec D-15）
    - `fetch_pull_head(checkout: Path, repository: str, number: int, head_sha: str, *, remote: str) -> str` … `git fetch --quiet --no-write-fetch-head --no-tags --refmap= <remote> +pull/<N>/head:refs/pr-review/repos/<repository の小文字>/<N>`。消えた ref への 1 回だけの再試行、head の一致の確認は移植元のまま。失敗は `EXIT_FETCH`
    - `main(argv=None, *, runner=_run) -> int` … `resolve <pr> [--code-root P]`、`review-dir <target> [--for-planning] [--code-root P] [--pr PR]`。`--for-planning` は受け付けて何もしない（ヘルプ: 移植元の呼び出しとの互換のため受け付ける。移植先では範囲を変えない）。`--code-root` は `Path` のまま `resolve_context` に渡す（絶対パスの検査は `superpowers_context.py` が行う）
  - 持ち込まない: `clone` サブコマンド、`clone_repository`、`CloneTarget`、`registered_submodules`、`PLANNING_OWNERS`・`require_planning_owner`・`EXIT_OWNER`・`EXIT_CLONE`

テストの要否: 要る。経路の決定・拒否・旧配置の識別・ref の固定は、実際の Git の checkout と偽の `gh` で実行して確かめる。

- [ ] **Step 1: fixture とテストを書く**

`test_review_target.py` の fixture（移植元の `make_repo`・`FakeGh`・`http`・`pull`・`gh_for`・`error_code`・`review_dir`・`write_findings`・`make_remote` はそのまま使う）:
- autouse の fixture で `GIT_CONFIG_NOSYSTEM=1`・`GIT_CONFIG_GLOBAL=/dev/null` を `monkeypatch.setenv` する
- `make_parent(path, origin="https://github.com/usaturn/create-reso-world.git")`: `.gitignore` に `/reviews/` と `/external/`
- `make_fork(parent)`: `parent/external/resoloop` に origin `https://github.com/usaturn/resoloop.git`・upstream `https://github.com/orange3134/resoloop.git` の checkout
- `make_other(tmp_path, origin="https://github.com/usaturn/resoloop-meshy.git")`: `--code-root` に渡す別の main checkout

移植元から写すテスト（期待値の repository 名だけ移植先の例に変える）: `test_parse_number_url_and_reject_other`、`test_github_repository_reads_https_and_ssh`、`test_validate_repository_rejects_unsafe_names`、`test_naming_rules_keep_the_helper_messages`、`fetch_pull_request` の 7 件、`test_require_parent_root_needs_ignored_reviews`、`test_require_parent_root_rejects_linked_worktree`、`test_find_review_directory_by_number`、`test_find_review_directory_does_not_cross_repositories`、`test_find_review_directory_lists_multiple_candidates`、`test_find_review_directory_accepts_legacy_path`（親の `reviews/#4-feat-x`）、`test_find_review_directory_rejects_name_mismatch`、`test_find_review_directory_from_findings_json`、`test_find_review_directory_rejects_findings_for_another_pr`、`test_find_review_directory_rejects_unidentifiable_path`

作り直す・足すテスト（主な assertion）:
- `test_review_directory_uses_lowercase_owner_and_repo_levels`: `review_directory(p, "Usaturn/Resoloop", 3, "feature/x") == p/"reviews"/"usaturn"/"resoloop"/"#3-feature-x"`
- `test_resolve_number_uses_parent_origin`: `resolve("#4", parent_root=parent)` の `repository == "usaturn/create-reso-world"`、`target_root == str(parent)`、`base_remote == "origin"`、`review_dir == str(parent/"reviews/usaturn/create-reso-world/#4-fix-x")`、最初の `gh` 呼び出しが `repos/usaturn/create-reso-world/pulls/4`
- `test_resolve_fork_and_upstream_use_separate_directories_and_remotes`: 同じ番号 11・同じ head ブランチの `usaturn/resoloop` と `orange3134/resoloop` の PR で、`review_dir` が `reviews/usaturn/resoloop/#11-x` と `reviews/orange3134/resoloop/#11-x`、`target_root` はどちらも `parent/external/resoloop`、`base_remote` は `origin` と `upstream`
- `test_resolve_lowercases_review_directory`: GitHub の正式名が `Usaturn/Resoloop` の応答で `review_dir` が小文字の階層、`repository` は `"Usaturn/Resoloop"`
- `test_resolve_stops_without_checkout_and_does_not_clone`: `https://github.com/usaturn/resoloop-meshy/pull/2`（`--code-root` なし）で `EXIT_PARENT`、文に `--code-root`。`tmp_path` の下に新しいディレクトリができない（実行前後の `sorted(tmp_path.rglob("*"))` が同じ）
- `test_resolve_uses_explicit_code_root`: 同じ PR に `code_root=make_other(...)` で `target_root == str(other)`・`base_remote == "origin"`
- `test_resoloop_route_requires_fork_remotes`: `external/resoloop` が無い、または `upstream` が無いとき、上流の PR で `EXIT_PARENT`、文に `resoloop-fork.sh clone`
- `test_code_root_rejections`: 相対パス、linked worktree、remote が一致しない checkout、create-reso-world の PR に親以外の `code_root`。どれも `EXIT_PARENT`
- `test_resolve_stops_without_parent_origin`: origin の無い親で `EXIT_PARENT`、`gh` を呼ばない（移植元のまま）
- `test_find_review_directory_reports_missing_review_and_legacy_dirs`: 番号で探して新しい配置に無いとき `EXIT_NO_REVIEW`。親の `reviews/#4-feat-x` が文に並ぶ。resoloop の PR では `external/resoloop/reviews/#11-x` と `external/resoloop/reviews/usaturn/resoloop/#11-x` が文に並ぶ。どちらも選ばれない
- `test_find_review_directory_accepts_checkout_owner_repo_layout`: `external/resoloop/reviews/orange3134/resoloop/#11-x` をパスで渡すと、`repository` が上流、`target_root` が `external/resoloop`、`base_remote == "upstream"`
- `test_legacy_fork_checkout_directory_is_ambiguous`: `external/resoloop/reviews/#11-x`（`findings/` なし）で `EXIT_PATH`、文に `usaturn/resoloop`・`orange3134/resoloop`・`--pr`。`gh` を呼ばない
- `test_legacy_fork_checkout_directory_with_pr`: 同じディレクトリに `pr_argument="https://github.com/orange3134/resoloop/pull/11"` で受け付け、`repository` は上流、`base_remote == "upstream"`。`--pr` が `https://github.com/someone/x/pull/11`（checkout の remote に無い）や番号違い（`/pull/12`）なら `EXIT_PATH` で、`gh` を呼ばない
- `test_pr_option_must_match_path`: 親の `reviews/usaturn/create-reso-world/#4-feat-x` に `pr_argument="5"` で `EXIT_PATH`、`pr_argument="https://github.com/usaturn/resoloop/pull/4"` で `EXIT_PATH`、`pr_argument="#4"` で受け付ける。PR の引数（`"#4"`）に `pr_argument` を足すと `EXIT_USAGE`
- `test_checkout_layout_must_match_target_root`: `--code-root` の checkout A の `reviews/usaturn/resoloop-meshy/#2-y` を、別の checkout B（同じ remote）を `code_root` にして渡すと `EXIT_PATH`。`code_root=A` なら受け付ける。`code_root` なしなら `EXIT_PARENT`
- `test_legacy_fork_checkout_directory_uses_findings`: 同じディレクトリに `findings/` が `orange3134/resoloop` #11 を指すと受け付ける。`findings/` が `other/x` を指すと `EXIT_PATH`
- `test_legacy_single_remote_checkout_directory`: `--code-root` の checkout（remote 1 つ）の `reviews/#2-y` をパスで渡し、`code_root` も渡すと受け付ける
- `test_legacy_checkout_without_github_remote`: GitHub の remote の無い checkout の `reviews/#2-y` は `findings/` が無ければ `EXIT_PATH`
- `test_find_review_directory_ignores_symlinks_and_other_names`: 新しい配置の下の symlink `#4-link` と `x4-feat` を候補にしない
- `test_fetch_pull_head_preserves_tracking_refs_tags_and_fetch_head`: 移植元のテストを、`fetch_pull_head(checkout, "usaturn/resoloop", 3, head, remote="origin")` と ref `refs/pr-review/repos/usaturn/resoloop/3` に合わせる（`head_moved` の 2 通り）
- `test_fetch_pull_head_separates_fork_and_upstream`: origin と upstream に、同じ番号 11 で別の head を持つ bare remote を置き、両方を取得すると `refs/pr-review/repos/usaturn/resoloop/11` と `refs/pr-review/repos/orange3134/resoloop/11` がそれぞれの head を指す。`"Orange3134/Resoloop"` を渡しても ref は小文字
- `test_fetch_pull_head_stops_when_head_moved`: 違う `head_sha` で `EXIT_FETCH`、文に「変わりました」
- `test_cli_review_dir_for_planning_keeps_the_range`: `main(["review-dir", "https://github.com/someone/x/pull/1", "--for-planning", "--code-root", str(other)])`（`other` の origin は someone/x、新しい配置にレビューあり）が 0 を返す
- `test_cli_reports_error_code_and_message`: `review-dir https://github.com/usaturn/resoloop-meshy/pull/2`（`--code-root` なし、`default_parent_root` を親に差し替え）が `EXIT_PARENT`、stderr に `review_target:`
- `test_cli_resolve_prints_json`: 移植元のまま（`printed["review_dir"]` の末尾が `/reviews/usaturn/create-reso-world/#4-fix-x`、`printed["base_remote"] == "origin"`）

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest .agents/scripts/tests/test_review_target.py -q`
Expected: FAIL（`review_target.py` が無いので収集時のエラー）

- [ ] **Step 3: `review_target.py` を書く**

`$SRC/.agents/scripts/review_target.py` を基に、Interfaces のとおりに変える。モジュールの docstring は、サブコマンド・保存先・旧配置・終了コードを Spec D-6〜D-9 に合わせて書き直す（`agent_tmp.py root` と同じ規則で親を決めること、checkout の探索・clone をしないことを書く）。`numbered_directories` の `except FileNotFoundError, NotADirectoryError:` は `except (FileNotFoundError, NotADirectoryError):` にする。

`identify_review_directory` の手順（Spec D-7。`reviews` は `(parent_root / "reviews").resolve()`）:
1. ディレクトリ名が `#<N>-...` でなければ層からは決めない
2. `directory.parents[2] == reviews` → パスの `<owner>/<repo>`、`check_name=True`
3. `directory.parent == reviews` → `parent_repository(parent_root)`、`check_name=True`
4. `directory.parents[2].name == "reviews"` で `C = directory.parents[3]` が親以外の checkout のルート、かつ `remote_repositories(C)` にパスの `<owner>/<repo>`（大小を区別しない）がある → それ、`check_name=True`
5. `directory.parent.name == "reviews"` で `C = directory.parents[1]` が親以外の checkout のルート → `remote_repositories(C)` が 1 件ならそれ（`check_name=True`）。2 件以上なら、`expected` のリポジトリが `remote_repositories(C)` にあればそれ（`check_name=True`）、無ければ `findings/` の PR のリポジトリが `remote_repositories(C)` にあり番号がディレクトリ名と同じならそれ（`check_name=False`）。どちらも無ければ `EXIT_PATH`（文に候補のリポジトリを並べ、`--pr <PR の URL>` を添えるよう書く）。0 件なら層からは決めない
6. 層から決めたときに `findings/` があれば、移植元のとおり食い違いを `EXIT_PATH` で止める。層から決まらなければ移植元のとおり `findings/` か `EXIT_PATH`。ただし `expected` があり、層からも `findings/` からも決まらないときは、ディレクトリ名が `#<expected の番号>-...` ならそれ（`check_name=True`）
7. `expected` があるときは、決まった PR（リポジトリは大小を区別しない、番号）と、ディレクトリ名の `#<N>`（名前が `#<N>-` の形のとき）が `expected` と一致すること。違えば `EXIT_PATH`

`find_review_directory` の順: `pr_argument` を PR の引数（番号・URL）と一緒に渡したら `EXIT_USAGE`。パスなら `identify_review_directory`（`pr_argument` があれば解釈して `expected` に。番号は `parent_repository`）→ `fetch_pull_request` → 名前の確認 → `target_checkout` → `identity.checkout` があって `target_checkout(...).root` と違えば `EXIT_PATH`。番号・URL なら `fetch_pull_request` → `target_checkout` → 新しい配置の `numbered_directories` → 0 件なら `legacy_review_directories` を文に並べて `EXIT_NO_REVIEW`、2 件以上なら `EXIT_AMBIGUOUS`。

- [ ] **Step 4: テストを通す**

Run: `uv run pytest .agents/scripts/tests/test_review_target.py -q`
Expected: 全て PASS

Run: `rg -n 'clone_repository|CloneTarget|submodule|PLANNING_OWNERS|EXIT_OWNER|EXIT_CLONE|maatlog|巡|席' .agents/scripts/review_target.py`
Expected: 該当なし

- [ ] **Step 5: Commit**

```bash
git add .agents/scripts/review_target.py .agents/scripts/tests/test_review_target.py
git commit -m "feat: port review_target with create-reso-world routes (#152)"
```

### Task 4: 全体の検証・レビュー・記録

**Files:**
- Modify: この Plan の「完了」、Spec の「実装・検証結果」（新しい節）

テストの要否: 新しいテストは書かない。リポジトリの正式な入口を実行し、ブランチ全体をレビューする。

- [ ] **Step 1: Issue の検証のコマンドを実行する**

Run: `uv run pytest .agents/scripts tests/scripts/test_superpowers_context.py -q`
Expected: 失敗 0

Run: `uv run pytest tests/skills .agents/skills .agents/scripts -q`（`README.md` の「テスト」。#149 の前なので `tools` は無い）
Expected: 失敗 0。既知の不安定なテスト（#128）が落ちたら、同じテストだけを 1 回再実行して結果を記録する

Run: `bash .devcontainer/run-tests.bash`
Expected: 終了コード 0

Run: `bash scripts/check-layout.sh`
Expected: 終了コード 0（環境に依存する既知の失敗が出たら、`origin/main` の親の checkout でも同じかを確かめて記録する）

- [ ] **Step 2: ブランチ全体のレビュー**

新しいサブエージェント 1 体に、`git diff origin/main...HEAD`、Spec、Plan、移植元（`$SRC`）を渡し、Spec からの逸脱・移植で落とした挙動・テストの採用基準に反するテスト・日本語表現の規則違反を見てもらう。致命的な指摘（Spec の受け入れを満たさない、誤った経路を選ぶ、データを壊す）だけを直し、直したら Step 1 を再実行する。自己レビューは 1 回まで（#116 の注意書き）

- [ ] **Step 3: 記録して commit**

Spec に「実装・検証結果」（実行したコマンドと結果、レビューの扱い）、この Plan に「完了」（Task ごとの結果、実行予算の実績）を書き、状態は draft のまま commit する。

```bash
git add docs/superpowers/specs/2026-10-18-create-reso-world-issue152-review-helpers-design.md docs/superpowers/plans/2026-10-18-create-reso-world-issue152-review-helpers.md
git commit -m "docs: record Issue 152 verification results"
```

公開（push の前の検査、push、PR の作成）は issue-to-pr の 5 章に従う。

## 実行予算

- Issue 全体の能動時間: 240 分（ledger `/workspaces/reso-world/tmp/agents/issue-152.ays8vbhd/budget.jsonl` は 09:49:58Z に開始。その前の 09:36Z から、Issue・ボードの確認、予約、worktree の作成、移植元の取得・調査に約 14 分）。根拠: 移植元で約 1 万 1 千行、Task 4 つのうち適応が要るのは Task 3 だけ。#146（Task 7 つ）の実績は能動時間 35 分ほど
- phase の目安: 準備・設計 40 分（ほぼ済み）、Task 1 で 40 分、Task 2 で 30 分、Task 3 で 70 分、Task 4 で 40 分、公開・記録 20 分
- worker: builder check とブランチ全体のレビューのサブエージェントは読み取り専用。Claude Code の Agent ツールは `task_watch.py` で起動できないので、事前宣言した打ち切りは使わず完了通知を待つ。1 体の目安は 10 分、20 分を超えたら stall として報告する
- 再試行: 同じ失敗の再試行は 1 回まで（信頼性の失敗）。安全の失敗は全体停止
- checkpoint: Task の境界、予算の 50%（120 分）・100%（240 分）、worker の失敗の直後。100% は停止して報告する
- 縮小・方法変更の候補: 文書の書き換えを、用語・Issue 番号・置き場所の節に絞り、移植先に無いものへの注記を省く。`review_target.py` の旧配置の 4・5（checkout ごとの旧形式）を外し、`findings/` に頼る

## Contingency

- 既存のテストが失敗したら: `origin/main` の親の checkout で同じテストを実行して比べ、この変更で増えた失敗だけを調べる
- `superpowers_context.py` を変えないと満たせない挙動が見つかったら: 既存の経路と拒否を変えない関数の追加だけを検討し、Spec の D-1 を更新する。既存の経路・拒否を変える必要があれば、#116 にコメントして止まる
- 競合（同じ Issue の PR・予約の喪失）が見つかったら: push・PR をせずに止まる

## 完了

状態は draft のまま（内容の承認は無い）。Task 1〜4 を完了し、公開（push の前の検査・push・PR の作成）に進む。結果と持ち越した Minor は Spec の「実装・検証結果」にある。

- Task 1（`81e15ee`）: Ruling: `test_review_records.py` は文書の記入例のテストで `review_findings.py` も読むので、Task 1 で `review_findings.py` を移植元のまま置き、文言の変更は Task 2 で行った。187 passed
- Task 2（`42e8d36`）: `test_format_document_examples_are_valid` の固定値の assertion を外した。2 ファイルで 411 passed
- Task 3（`ccff011`）: 59 passed。主な分岐を 1 つずつ壊すと、どれもテストが失敗することを確かめた。Ruling: `rg` の `submodule` の 2 件は、親の main checkout の確認（submodule を拒む）とテストの説明なので残した
- Task 4: 検証 4 本は全て終了コード 0。ブランチ全体のレビューは Critical 0・Important 0・Minor 6 で、修正はしていない（再レビューもしていない）
- Setup: Ruling: executing-plans の作業領域（`.superpowers/sdd/`）は worktree の中にできるので使わず、ledger は `tmp/agents/issue-152.ays8vbhd/progress.md` に手で書いた（`AGENTS.md` は worktree にコミットしないファイルを置くことを禁じる）
- 実行予算: 240 分のうち、09:36Z の着手から 10:27Z の記録まで約 51 分（ledger の能動時間は 09:49:58Z からの分）。準備（Issue・ボードの確認、予約、worktree、移植元の取得と調査）約 13 分、Spec・builder check・Plan 約 18 分、Task 1〜3 約 11 分、検証約 8 分、ブランチ全体のレビュー約 10 分
