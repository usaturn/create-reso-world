# 外部ツールリポジトリ共通管理基盤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通常の外部ツールを登録データと repo 固有の規則で追加でき、取得・対象判定・Issue/PR・レビュー・片付けまで同じ経路で扱えるようにする。

**Architecture:** 採用済み親 checkout のコミット済み台帳を共有 loader が読み、実 checkout と Git common-dir を照合する。読取 resolver と取得の副作用を分離し、既存 helper / skill を利用側として接続する。Emission は台帳の一項目であり、個別コードは作らない。

**Tech Stack:** Python >=3.14、標準ライブラリ（tomllib/dataclasses/subprocess/fcntl/ctypes）、Git、uv、pytest。新しい依存を増やさない。

**Spec:** `docs/superpowers/specs/2026-11-06-emission-editor-repository-management-design.md`、現行保存版 `c654fafaa9eb7cdb6d2136c31f8239f44bb5c7a9`。利用者は参照版 `b8c9b4253a5cd3431c9e2e6320649c2de14c15d8` と最低 Python 3.14 への明示変更を承認した。

- 状態: approved
- 内容確認・実行許可: 利用者が `23d4c2ca4e10c36c8fff7340e5481dd0bdf6c5a9` の確認コピーとtiming.md記録方式を提示した質問に「実装して」と回答。まず本共通基盤Planを実装する許可として記録する。後続Emission移行、公開・親への採用・外部操作は許可に含めない。
- 草稿の確認状態: writing-plans の最終自己点検を実施済み。実装進捗は各Taskのチェックと末尾の記録で管理する。
- 実行状態: **安全の失敗により全体停止**。Task4の初期テストでfake Git wrapperを抜け、GitHubへの無許可のHTTPS pushを試行した。認証エラーで失敗した記録があり、成功した公開は確認されていない。Task4の修正済みという報告だけで再開せず、隔離の確認方針と利用者の再開指示を待つ。
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/emission-repo-management`
- PARENT_ROOT: `/workspaces/reso-world`
- ブランチ: `docs/emission-repo-management`。基準コード `28ef59b17a94191663597c927e66791425a3a864`。着手時に実際の BASE を別途記録する。
- Issue / PR: なし。実行方式は選択済みの subagents/TDD/per-task review/lineage-only。実行許可は上記の本Plan範囲のみ。
- 後続: `2026-11-06-emission-editor-onboarding.md`。本 Plan は新 GitHub repo の作成・ソース移行を行わず、それだけでも検証できる成果物を作る。
- 公開: ローカルの文書コミットのみ。push / PR / merge は別許可。公開未実施。

## Global Constraints

- 共通基盤と新しい Emission Editor リポジトリの Python は最低 3.14（`requires-python = ">=3.14"`）とする。
- 正式な Spec・Plan は引き続き create-reso-world の `docs/superpowers/` に置く。
- 登録は「この機構が扱える対象」を定義するだけである。repo 作成・clone・実装・push・PR・マージ・release・実機操作の実行許可は、利用者の指示と各ワークフローで別に確認する。
- 未登録・checkout 不在・remote 不一致・候補が複数のときに、親 checkout や近くの repo へ fallback しない。
- Emission Editor 用の `scripts/emission-editor.sh` や共通機構の代わりとなる個別取得手順は作らない。
- 旧 world / state / sealed source / SourceMap / 本体パネル、参考先の非公開コードを変更・移動・転載しない。実機・本物の repo 作成をテストに使わない。
- 既存 parent / fork の特殊経路と、未登録でも明示 CODE_ROOT を与える PR レビュー・承認済み review-fix を保持する。登録済み通常ツールの自動マージは追加しない。

## Review Focus

1. 未採用 branch の台帳や親の外の symlink が操作対象を増やさないこと — Task1 の committed-registry / containment の S。
2. origin が同じ別 clone や GIT 環境の混入でも修正・削除先を取り違えないこと — Task2 の identity の S。
3. 同時取得、最終配置先の割込み、途中失敗で既存物を失わないこと — Task3 の排他・非置換の S。
4. 新規登録だけで入力解決から PR 対象まで届き、未対応 `--merge` は先に止まること — Task4 の fake workflow の S。
5. cleanup や単一ファイル helper の呼出しが親を誤選択しないこと — Task2/5 の実行経路の S。import の構文エラー自体は L のため永続テストを足さない。

---

## 受け入れ基準

- **動作環境:** 既存 Dev Container、Python 3.14 以上、uv、Git。親の pyproject は既に >=3.14。Linux の排他・非置換 rename を使い、未対応環境では既存物を変更せず停止する。
- **実入力:** `emission-editor` / `usaturn/resonite-emission-editor` / `external/emission-editor` / base `main` / CI `disabled`。一時 fixture では第2ツール `sample-owner/other-tool` / `external/other-tool` / base `development` / CI `required`、Issue 本文 `材質の変更\n元値を保持する`、空白を含む親パスを使う。
- **防御範囲:** 台帳は `schema_version=1` と `tools.<key>`、各項目は `repository,path,base_branch,ci` のみ。keyは `[a-z0-9](?:[a-z0-9-]*[a-z0-9])?`、repositoryは既存GitHub parserと同じowner/repo形式、base_branchは展開しないliteral heads refとして `git check-ref-format` で検証する。ci は `required|disabled`。通常ツール profile は manual merge。absolute / `..` / 重複・親子重複 / 予約済み既存 repo との衝突 / 祖先 symlink 脱出を拒否する。資格情報付き URL・曖昧 remote・異なる実送信先を拒否する。
- **保持する反例:** 既存 ResoLoop fork の upstream PR と、未登録 repo の明示 CODE_ROOT PR review-fix は引き続き通る。未登録 repo の新規実装、任意 setup/release、親への fallback は通らない。
- **成功の範囲:** fake/local Git で登録から各利用側まで動くこと。repo 登録や check の成功を、GitHub 作成・公開・CI設定・実機準備の完了にしない。

## 実行予算・監視・記録

利用者の「時間制限なし」を維持し、能動時間の上限と共有実装・テストを殺す外側 timeout は設けない。目安は Task1–3 各45–90分、Task4–5 各60–120分だが許可上限ではない。各 Task 境界・失敗直後・能動60分ごとに、成果/残作業/方法を checkpoint する。有限予算がないので50%/100%の閾値は使わない。

既存 `issue_budget.py` は正の有限分数が前提で無制限を表現できない。`inf` や架空の上限を渡さず、SESSION の `timing.md` に開始/終了/利用者待ち・再開を UTC で記録し、能動時間を集計する方式を提案する。これは `.agents/execution-budget.md` の JSONL helper 使用からの今回限定の例外であり、時間上限なしという指示だけで承認済みと扱わない。利用者は確認質問に「実装して」と回答し、この記録方式を含む本Planの実行を許可した。同 helper の拡張は本 Plan に混ぜない。

SESSION は `agent_tmp.py mkdir external-tools-impl` で作る親の一意領域。SDD は `SESSION/sdd/2026-11-06-external-tools-framework/` を mkdir して使用する。各担当は主要作業別の実測時間を報告する。子の時間を全体に二重加算しない。

worker の絶対期限は設けない。10分ごとに進捗を確認できる runtime では監視し、変化なし2回で stall を報告するが kill しない。pi の同期 subagent は戻るまで待ち、結果・終了情報・レポートを確認する。無出力/レポートなしは成功にしない。同じ信頼性失敗の再試行は1回まで、2回目は方法変更。安全の失敗は全体停止・再試行なし。

Task は1→2→3→4→5。Task3と4には一部独立性があるが、このpi運用では同期直列・同worktree writer1件を守る。Task ごとに実装担当と読み取り専用レビュアーを分け、同じ受け入れ基準を渡す。レビュー子はテストしない。Plan のチェックは controller が更新し、全体レビュー前に作業領域を削除しない。

## ファイル構成と共通インターフェース

新規 `tools/external_tools/`:
- `models.py`: frozen dataclass `ToolSpec(key: str, repository: str, relative_path: str, base_branch: str, ci: Literal["required", "disabled"])`、`Registry(parent_root: Path, commit: str, entries: tuple[ToolSpec, ...])`、`ManagedTarget(spec: ToolSpec, checkout: Path, common_dir: Path, base_remote: str, registry_commit: str)`。`CheckResult(status: Literal["ready", "missing", "mismatch", "blocked"], path: Path, common_dir: Path | None, reason_code: str | None, registry_commit: str)`、`CloneResult(status: Literal["cloned", "present", "blocked", "failed"], path: Path, staging: Path | None, reason_code: str | None, registry_commit: str)`。`ExternalToolsError(ValueError)` は秘密を含まない `reason_code: str` と説明だけを持つ。
- `registry.py`: `parse_registry(data: bytes, *, parent_root: Path, commit: str) -> Registry`、`load_active_registry(parent_root: Path) -> Registry | None`、`Registry.find_repository(repository: str) -> ToolSpec | None`。
- `identity.py`: GIT環境を隔離した読取 Git、URL/checkout/実送信先の照合、`resolve_managed_target(registry: Registry, repository: str, *, operation: str, code_root: Path | None = None) -> ManagedTarget`、`validate_transport_destination(target: ManagedTarget, *, direction: Literal["fetch", "push"]) -> None`。後者もローカル設定の検査だけで通信しない。context script を逆importせず、循環依存を作らない。
- `cli.py` / `__main__.py`: `main(argv: Sequence[str] | None = None) -> int`、list/show/check/clone。引数で任意 executable / registry を実操作へ注入できるようにしない。
- `clone.py`: `clone_tool(registry: Registry, key: str) -> CloneResult`。test seam は内部の subprocess adapter のみ。
- `tests/`: 守りを実装するモジュールごとの S。`conftest.py` の `workspace` は `parent: Path`、`registry: Registry`、`adopted_sha: str`、`registered: Path`、`linked: Path`、`other_clone: Path`、`repository: str` を持つ fixture。一時親の origin/main と detached HEAD に採用 commit を置き、候補変更は別 branch に置く。transport は fake、ローカル Git の fixture 作成だけを実行する。既存 fixture を再利用できる所は再利用する。

通常 profile は `managed-tool-v1`。operation は `implement, review-workspace, review-fix, base-read, cleanup` を区別する。managed toolの `review-workspace` / `cleanup` は常設 checkout、`review-fix` / `implement` は同common-dirの名前付きbranchのlinked worktree、`base-read` は同common-dirの常設checkoutまたはlinked worktreeのrootだけを許す。削除候補自体の所有・PR マージ確認は既存 cleanup の条件を追加で課す。既存parent/fork/未登録明示CODE_ROOTのoperation条件は変更しない。

台帳がまだ無い旧親は managed entry なしとして既存経路だけを保持する。壊れた/読めない台帳を empty として握り潰さない。CLI は台帳不在を明示エラーにする。運用台帳は検証済み常設親の detached HEAD の blob から読み、その HEAD がローカル origin/main の祖先であることを確認する（読取時は fetch しない）。親の作業ツリー、feature branch/worktree、外部 repo の台帳候補を操作に使わない。候補parseは読取検証専用で、clone等は active registry を再読込して commit/内容の一致を要求する。

CLI の成功終了は list/show=0、check は ready だけ0、clone は cloned/present だけ0。その他の状態は非0かつ上記 status/reason_code をJSONで返す。Path はJSONで文字列化する。context helper は `ExternalToolsError` を exit66へ変換し、既存の入力64/fork65/11キーを保持する。

### Task 1: 採用済み台帳の読み込みと配置境界

**Files:** Create `external-tools.toml`, `tools/external_tools/{__init__,models,registry}.py`, `tools/external_tools/tests/{conftest,test_registry}.py`。

**Interfaces:** Consumes 親の検証済み常設 root。Produces 上記 `ToolSpec` / `Registry` / parse/load/find。台帳には Spec の Emission 項目1件を登録するが、cloneやGitHub作成は行わない。

**テスト:** S。登録先のすり替え・範囲外操作・候補による昇格を防ぐ。TOML構文・Pythonバージョンの値だけの F/L テストは追加しない。

- [x] **Step 1:** `workspace` fixture を作り、`test_active_registry_ignores_unadopted_candidate`、`test_registry_rejects_escaping_or_overlapping_target` を RED にする。前者は採用commitのtoolだけを返し、候補追加を返さない。後者は `../outside`、祖先symlinkから外への脱出、`external/one` とその子の重複、既存fork予約先、lock名の範囲を脱出する `../key` の拒否を、その守りの代表として扱い、正しい別2項目も通す。
  ```python
  active = load_active_registry(workspace.parent)
  assert active is not None and active.commit == workspace.adopted_sha
  assert active.find_repository("sample-owner/unadopted") is None
  parsed = parse_registry(two_valid_entries, parent_root=workspace.parent, commit=workspace.adopted_sha)
  assert parsed.find_repository("sample-owner/other-tool").relative_path == "external/other-tool"
  ```
- [x] **Step 2:** `uv run pytest tools/external_tools/tests/test_registry.py -q` を実行し、未実装の守りで失敗することを確認する。
- [x] **Step 3:** parse/load/find を実装。repoの大小文字正規化、pathの予約範囲/重複、親の origin と common-dir、採用blobの読取を行う。既存 `external/resoloop` / `external/resoloop-meshy` と親自身は台帳から上書きできない。候補schemaのparseは可能だが操作用loaderは親HEADだけ。
- [x] **Step 4:** 同テストを GREEN にし、`uv run python -c 'import sys; assert sys.version_info >= (3,14)'`、TOML実parseと `git diff --check` を確認する。親pyproject/lockは既に3.14対応なので理由なく更新しない。
- [x] **Step 5:** 対象ファイルだけをcommit。Taskレビューを受け、controller が完了を記録する。

### Task 2: 共通 identity・読取CLI・既存 context との接続

**Files:** Create `tools/external_tools/{identity,cli,__main__}.py`, `tools/external_tools/tests/{test_identity,test_cli}.py`。Modify `scripts/superpowers_context.py`, `tests/scripts/test_superpowers_context.py`, `.agents/scripts/tests/test_review_target.py` と、helperをコピーする `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`, `.agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py` の fixture。

**Interfaces:** Consumes Task1。Produces `resolve_managed_target` と読取CLI。既存 `resolve_context(...)` の11キー、exit64/65/66、`review_target.target_checkout(...)` の root/remote 仕様を変えない。追加の証拠は common CLI/型から取得し、互換JSONへ無条件にキーを足さない。

**テスト:** S。別clone/GIT環境/URL書換えによる誤対象、親へのfallback、既存例外経路の喪失を防ぐ。import経路の検査は既存実行テスト/一時smokeで代える。

- [x] **Step 1:** `test_managed_target_uses_registered_common_dir` を RED にする。同 origin の別cloneを拒否し、登録元のlinked worktreeは許可されたoperationで通す。`test_git_environment_cannot_redirect_identity` は一時の別repoを指す GIT環境を与えても元対象を返す。実push先の不一致は既存 `select_push_remote` 相当の守りとして代表1件を置く。
  ```python
  resolved = resolve_managed_target(workspace.registry, workspace.repository, operation="review-workspace")
  repair = resolve_managed_target(workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.linked)
  assert resolved.checkout == workspace.registered
  assert repair.common_dir == resolved.common_dir
  with pytest.raises(ExternalToolsError):
      resolve_managed_target(workspace.registry, workspace.repository, operation="review-fix", code_root=workspace.other_clone)
  assert snapshot_after == snapshot_before  # fixture内のHEAD/refs/index/作業ファイルを前後比較
  ```
- [x] **Step 2:** `uv run pytest tools/external_tools/tests/test_identity.py tools/external_tools/tests/test_cli.py tests/scripts/test_superpowers_context.py .agents/scripts/tests/test_review_target.py -q` を実行し、REDを確認する。
- [x] **Step 3:** registered分岐を document/fork の既存分岐と未知repo明示CODE_ROOTの間へ接続。既存 fork の origin/upstream 再照合を managed tool に誤適用しない。実origin/全pushurlの照合・資格情報を伏せた診断を共有する。CLIの list/show/check はネットワークも変更も行わず、missing/mismatch は非0で理由を返す。
- [x] **Step 4:** helperの直接実行は、自分のファイル位置から同じ親worktreeの package を読み込む。既存 `sys.modules['tools']` や cwd/PYTHONPATH 由来の別packageを再利用せず、必要ならファイル位置固定の専用package名でロードする。コピーfixtureにも実際の共通packageを配置する。`test_context_cannot_load_foreign_tools_package` を既存contextテストへ追加し、偽packageの対象すり替えが起きず正しいtargetを返すことをSで確認する。上記suiteと `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`、`.agents/skills/pr-review-fix-loop/tests/test_loop_reviewer_protocol.py` を GREEN にする。
- [x] **Step 5:** commit・Taskレビュー。未登録明示CODE_ROOTの正例、fork上流base、review-copyの親/文書だけの検証が保持された証拠を報告する。

### Task 3: 1件限定・排他・非置換の取得

**Files:** Create `tools/external_tools/clone.py`, `tools/external_tools/tests/test_clone.py`。Modify `cli.py` の clone 分岐のみ。

**Interfaces:** Consumes Tasks1–2。Produces `clone_tool(...)`。`CloneResult.status` は `cloned|present|blocked|failed`、path / staging / reason_code / registry_commit を返す。presentは完全に検証できた既存checkoutだけ。dirty・不一致・未知残骸はblocked。

**テスト:** S。利用者所有部分の上書き、競合、失敗を成功とする報告を防ぐ。ネットワークは内部adapterをfake化し、本物のclone・認証を使わない。

- [x] **Step 1:** `test_existing_target_is_never_changed`、`test_concurrent_clone_has_one_publisher`、`test_publish_refuses_new_destination` を RED にする。sentinel bytes/既存Git snapshotを保持し、正しい空き先では1件だけ取得が完了する。同じ配置テストで、検査後に祖先を外へのsymlinkへ差し替えても外側のsentinelと最終位置へ書き込まないことを確認する。途中Git失敗の代表はstatus=failedとstaging保持を検査する。
  ```python
  assert sentinel.read_bytes() == before
  assert fake_remote_calls == [authorized_repository]
  assert successful_publishers == 1
  assert failed_result.status == "failed"
  ```
- [x] **Step 2:** `uv run pytest tools/external_tools/tests/test_clone.py -q` を同期実行し、REDを確認する。
- [x] **Step 3:** 親common-dir内の `.git/external-tools/locks/<key>.lock` を O_NOFOLLOW と非待機flockで開き、競合はBUSYで返す。検証済みexternal内の一意stagingにinit→origin追加→指定branch取得→detached checkout。local mainを作らず、Git checkout hookを無効化する。各repoのsetupは実行しない。lockの祖先とstaging/配置先の祖先も検証し、範囲外symlinkや差替えを通さない。保持したdirectory fdに対する配置と直前の再照合で、検査済みパスのすり替えを防ぐ。親registry commitと送り先を取得前・配置直前に再確認する。
- [x] **Step 4:** 配置は Linux `renameat2(RENAME_NOREPLACE)` の小さい内部wrapperで行う。未対応/既存destは停止し、上書きする `os.rename` やcopyへのfallbackはしない。stagingと最終先は同一filesystemに置く。自身の失敗領域も自動削除せず返す。テストをGREENにし、CLIの取得対象省略・既存dirtyで書込が進まないことを代表のfake経路で確認する。
- [x] **Step 5:** commit・Taskレビュー。HOMEはワンショット隔離だけ、rm変数には`:?`を付ける。実repoの取得はこのTaskで実行しない。

### Task 4: Issue→PR の対象解決と手動マージprofile

**Files:** Modify `.agents/skills/issue-to-pr/scripts/{resolve_issue,resolve_base}.py`, `.agents/skills/issue-to-pr/SKILL.md`, 同testsの `test_resolve_issue.py`, `test_resolve_base.py`, `test_base_workflow.py`。Modify `.agents/skills/review-fix-planning/scripts/finalize.py` と `tests/test_finalize.py` は managed-tool拒否に必要な箇所のみ。

**Interfaces:** Consumes Task2のregistry/target。`supported(repo: str, *, parent_root: Path | None = None) -> str` と `resolve_target(reference: str, cwd: Path, *, parent_root: Path | None = None) -> tuple[str, int]` は旧呼出しも保持。`resolve_base(checkout: Path, repo: str, base: str | None, required_bases: list[str], expected_sha: str | None) -> dict[str, str]` の署名・JSONを保持。検証済み環境から親を渡し、未知repoの探索をしない。通常toolの `--merge` はgh照会/予約/書込前に拒否する。

**テスト:** S。別repo/baseへのPR、未対応mergeの進行、CI免除の波及を防ぐ。既存のshell手順実行テストはFではないので意味を保つ。

- [ ] **Step 1:** 別名toolをfixture台帳だけに追加した `test_registered_tool_flows_to_issue_and_base` と `test_managed_merge_stops_before_github_call` をREDにする。fake Issue本文は複数行の日本語。base未指定では第2toolの `development` を選び、明示 `--base release` は `release` を選ぶ。同じ代表経路で既定baseをmain固定にしないことを検査する。正しいnon-mergeはtool repo/refへ届き、merge拒否ではfake呼出しが空になる。
  ```python
  assert resolved_repo == registered_repo
  assert captured_base["repo"] == registered_repo
  assert captured_base["branch"] == ("release" if base_explicit else "development")
  assert github_calls_for_rejected_merge == []
  ```
- [ ] **Step 2:** `uv run pytest .agents/skills/issue-to-pr/tests .agents/skills/review-fix-planning/tests/test_finalize.py -q` でREDを確認する。
- [ ] **Step 3:** lexical入力検証→repo解決→profile検査→Issue読取の順で接続。`#N` はcwd自身のoriginで解決する既存条件を維持。`base_explicit=False` の main仮値は通常toolの台帳baseへ置換し、`resolve_base` への直接の base=None も同じ規則にする。既存3repoの既定mainと required-base の矛盾拒否は保持する。base-readでも常設/common-dir/送信先を検査し、既存のrefを更新しないbase取得とSHA再確認を緩めない。finalizeはmanaged手動profileをネットワーク前に拒否し、未知repoのCI必須既定も維持する。
- [ ] **Step 4:** SKILLの固定対象表を共通target結果とrepo側規則の読取へ置換し、コードrepoと文書repoのbase・PRを区別する。変更前にwriting-skills/skill-creatorの該当手順を読む。恒久テストはSのみ。shellブロックの実行テストと上記suiteをGREENにする。
- [ ] **Step 5:** commit・Taskレビュー。登録だけで権限が増えないこと、既存parent/fork/meshyの動作を報告する。

### Task 5: レビュー・cleanup・共通規約まで接続して統合確認

**Files:** Modify `AGENTS.md`, `README.md`, `.agents/skills/{pr-review,review-fix-planning,pr-review-fix-loop,repo-cleanup-after-merge}/SKILL.md` の対象解決に関係する箇所。Create `docs/external-tools-workflow.md`、`.agents/skills/repo-cleanup-after-merge/tests/test_managed_target.py`。必要なfixture更新は既存context/review testsに限定する。

**Interfaces:** Consumes Task2のtargetとTasks3–4の共通手順。Produces「登録データ + repo-owned AGENTS/READMEだけで通常toolを追加する」正式運用。review保存先と既存CLIは変更しない。

**テスト:** S。cleanupが他repo/worktreeを削除しないことと、利用側までidentityが保たれる一連の経路。文書の名前一覧や見出し一致だけのFは増やさない。

- [ ] **Step 1:** `test_managed_cleanup_resolves_only_registered_common_dir` をREDにする。既存の手順抽出方式で対象判定のshellを実行し、マージ済みの対象fixtureだけを候補にする。同じoriginの別clone・未マージ・親のworktreeは残る。正しい対象の正例も持つ。
  ```python
  assert cleanup_target == registered_checkout
  assert unrelated_worktree.exists()
  assert unmerged_branch_still_exists
  ```
- [ ] **Step 2:** `uv run pytest .agents/skills/repo-cleanup-after-merge/tests -q` でREDを確認する。
- [ ] **Step 3:** 各skillを同じresolverへつなぐ。cleanupのparent更新/fork syncを通常toolから呼ばない。AGENTSは台帳を参照する共通規則にし、未知repoの既存review-fix例外を残す。共通運用文書に登録の採用、取得、repo-owned検証、CI照合、手動merge、新規tool追加、失敗stagingの扱いを書く。CI disabled は実設定の Actions=false を、required は実際のPR checksをcontrollerが読取確認する。registry成功だけで未知repoのCIを免除せず、ローカルcheckはネットワーク確認済みと表示しない。
- [ ] **Step 4:** Task1–5の対象suiteと `uv run pytest` を同期実行。cloneはfake、一時Gitのみ。読取CLIは親への台帳採用前は未採用/不在として止まることを実行し、候補台帳を採用済みとして見せない。`git diff --check` とGit差分を確認する。
- [ ] **Step 5:** commit・Taskレビュー後、SDDの全体レビュー（Review scope: branch）。指摘処理後の全suiteと状態を確認し、正式規則として利用するには親への採用が必要と報告する。push/PR/mergeは許可なく行わない。finishingは全体レビューと所定cleanup後だけ。

## contingency（代替策）

- 最初のREDで既存JSON/helperコピーの前提が違えば、意味を保ったfixture/import修正だけをledgerに記録して続行。操作範囲やJSON仕様を広げる必要があれば停止し、設計変更を相談する。
- renameat2や排他が使えない環境ではcloneを明示的に未対応として停止。既存物を置換するfallbackは禁止。
- ワークフロー接続が大きすぎる場合はTask単位で未完了として切り出す。resolverだけを汎用基盤完成と報告しない。
- 台帳採用前は旧親が新toolを扱えなくても正しい停止である。実装用台帳を親へ手コピーして回避しない。
- 予算helperの無制限対応、forkの一括移行、自動merge、他runtimeの拡張へ脱線しない。安全の失敗なら成果を保持して全体停止する。

## 完了の証拠と後続ゲート

各Taskの実行結果・所要時間・レビュー裁定はSESSION `/workspaces/reso-world/tmp/agents/external-tools-impl.19cduyzx` に保存する。

- Task1完了: `bfe1bc6..a1c37a67`。台帳と採用済みblob・配置境界を実装。レビューの親子symlink/Git replaceとcontrollerのexternal外配置の指摘を修正し、限定再レビューはImportant残件0。Task suite19件をcontrollerも再実行、担当の全体suite1276件成功。初回実装1043秒・修正742秒（同期検証含む）。重複テスト1件のMinorはledgerへ記録し全体レビューで再確認する。
- Task2完了: `9b78d8b..07269475`。共有identity・読取CLI・11キー互換contextとコピーfixtureを実装。コピーした.gitで別rootを許す指摘を修正し、限定再レビューは残件0。担当は関連89件（51subtests）/全体1289件、controllerは関連78件と修正後identity10件を再実行し成功。初回1353秒・修正862秒（同期検証含む）。
- Task3完了: `86eafbbe..898fa8c4`。flock・fd保持・非置換renameによる1件取得とstaging保持、CLIを実装。statusが隠すtracked変更の誤成功を修正し、限定再レビューは残件0。担当Task suite45件/全体1303件、controller clone14件が成功。初回23分25秒・修正15分39秒（同期検証含む）。inode再照合テストの重複Minorは全体レビューに引き継ぐ。
- Task4は未完了: 実装担当が `b444df49` に7ファイルをコミットしたが、controllerの検証と独立レビューは未実施。初期テストの2ケースで `git -C <fixture-doc-worktree> push origin ...` がfakeを抜け、`usaturn/create-reso-world` への実HTTPS transportを試みて認証エラーとなった。担当はfake修正後にテストを継続し、全体1307件（最終fixture修正前）と対象168件/45subtests（修正後）の成功を報告したが、安全の失敗を成功扱いせず、controllerは報告受領後に全体停止した。実送信内容や資格情報使用の網羅確認はしていない。報告・失敗ログはSESSIONの `sdd/2026-11-06-external-tools-framework/task-4-report.md` 等に保持する。Task4の実装からコミットまで44分29秒、子終了まで約46分55秒。
- Task5、最終全体レビュー、統合確認、公開・親への採用は未実施。Task4を完了にせず、既知のMinor2件も最終レビュー待ちのまま保持する。完了しても公開や親への採用は別の事実である。後続のEmission Planは、親へ共通基盤と登録が採用されたcommitを確認するまで実装を開始しない。

## Plan 自己点検の記録

controllerがSpecと既存helper/fixtureを照合した（実装・テスト実行ではない）。

1. 仕様網羅: Spec5.1→Task1、5.2→Task2、5.3→Task3、5.4→Task4–5、5.5→Task5。Spec4/6/7の公開・移行は後続Plan、Spec8の共通基盤条件は本Planの受け入れ基準へ対応する。
2. 手順: 採用台帳と候補parse、読取とclone、通常profileと既存例外を分離。既定baseがmain以外の登録と明示指定の差をTask4へ追加した。
3. 型: dataclassのfield/status、contextの11キー、fixture、resolve_target/resolve_baseの引数を具体化。scriptとpackageの循環importを禁止した。
4. Review Focus: 5項目をTask1/2/3/4/5のSへ対応付けた。helperが別のpackageを選ぶ問題は単なるimport失敗ではなく対象すり替えのSとしてTask2で確認する。F/Lの恒久テストは追加しない。
5. 分量: 関数本体を計画へ書かず、境界と署名・代表assertに限定した。実装Task/レビューは全件未実施。

内容確認・実行許可とtiming.md記録例外は上記のとおり受領。承認参照SHAは23d4c2ca4e10c36c8fff7340e5481dd0bdf6c5a9のまま保持する。公開・親への採用・後続移行は別ゲート。
