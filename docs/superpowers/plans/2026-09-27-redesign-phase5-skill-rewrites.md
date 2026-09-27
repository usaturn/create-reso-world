# create-reso-world 再設計 フェーズ 5（スキルの書き直し）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移行元リポジトリ（maatlog）を前提にしたスキルの記述を、仕様 8.2 の表のとおりこのリポジトリ向けに書き直し、repository-ownership を削除する。仕様 8.3 のとおり各スキルの contract テストを新しい文言に合わせ、`uv run pytest tests/skills .agents/skills` を全通過させる（フェーズ 4 で置いた CI の skill-tests ジョブも通るようになる）。あわせて、持ち越しの N-2・N-13・N-14・N-23・N-26 を片付ける。

**Architecture:** 作業ルートの決め方は、ルート `AGENTS.md` の「リポジトリ境界」の表（仕様 5.4）だけを根拠にする。pr-review・review-fix-planning・repo-cleanup-after-merge・simplify-in-subagent・planning-parallel-issues は、それぞれの手順の中で同じ 3 行（このリポジトリ、resoloop の fork、それ以外は停止）を使う。pr-review の解決ブロックは、テストが SKILL.md から取り出して bash で実行し、一時リポジトリで経路ごとの `MAIN_ROOT` と `PR_REMOTE` を確かめる。本文だけでテストの無かったスキルには contract テストを新設し、書き直した規則を固定する。最後に、追跡ファイル全体から移行元の名残（maatlog、`public/` submodule、`scripts/ci/verify.sh`）を探すテストを `tests/skills/` に置き、仕様 11 章の成功条件を常に検査する。

**Tech Stack:** Markdown（スキル本文）、pytest / PyYAML（contract テスト）、bash（`scripts/new-world.sh` と既存のシェルテスト）、git（一時リポジトリ、`git grep`）、docutils / rstcheck（rst-writer の新しい profile の検査。`uv run --no-project --with ...` で一時的に使う）

**Spec:** `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md`（5.4 節、8.2 節、8.3 節、10 章のフェーズ 5、11 章）。前フェーズの計画は `docs/superpowers/plans/2026-09-27-redesign-phase4-devcontainer-and-ci.md`。

## 判断事項（2026-09-27、controller の裁定）

2026-09-27 にユーザが「PR を出すまで止めないでください」と指示した。フェーズ 4 の D-9 のとおり、これをフェーズ 4〜6 の計画をフェーズごとの承認待ちなしに controller の裁定で進めてよいという指示として扱う。**本計画も、この指示に基づいて controller の裁定で承認し、実行する。** 裁定はこの表と SDD の台帳に残し、PR の説明にも一覧で載せる。

計画の作成時に、scratchpad にフェーズ 4 の終了時点（`48da0f7`、フェーズ 4 の全 Task を当てた tree）の複製を作り、全 Task をテストから先に試作した。テストが実装前に失敗し、実装後に通ることを確かめ、各テストが対象の変更を検出することを、実装をわざと壊すミューテーションで確かめた。計画書の本文だけを新しい複製に順に当てた結果が、試作と file mode まで一致することも確かめた。resoloop・dotnet・Blender・各エージェントの CLI を PATH から外した CI 相当の環境でも、テスト一式が通ることを確かめた。

| ID | 事項 | 本計画の内容 | 理由 |
| --- | --- | --- | --- |
| D-22 | 作業ルートの解決（仕様 5.4） | このリポジトリの PR は toplevel。`usaturn/resoloop` と `orange3134/resoloop` の PR は `<toplevel>/external/resoloop` で、`origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` であることを確かめ、違えば `scripts/resoloop-fork.sh clone` を案内して止まる（pr-review は終了コード 65）。それ以外は推測せず止まる。pr-review は PR の head を取る remote を `PR_REMOTE` に決め、上流の PR は `upstream`、それ以外は `origin` から `pull/<N>/head` を取る | 上流の PR の `pull/<N>/head` は上流のリポジトリにしか無く、fork の `origin` から取ると失敗する。fork の checkout が無いか別物のときに toplevel へ読み替えると、無関係なリポジトリで作業する |
| D-23 | pr-review の `verify.sh` 禁止条項の一般化 | 「重い一括検証を再実行しない」とし、対象を `bash .devcontainer/run-tests.bash`、リポジトリ全体やワールドのプロジェクト全体の `uv run pytest`、`scripts/resoloop-fork.sh test` と例示する。ファイルやテスト名で絞った pytest、個別のテストスクリプト、REPL、最小再現は許す | 仕様 8.2 の指示。レビューの時間予算（45 分）の中で一括検証を繰り返さない、という元の趣旨を保つ |
| D-24 | review-fix-planning の反映の条件 | 実装に関連したテストに加えて、環境の変更は `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`、そのうちスキルの変更は `uv run pytest tests/skills .agents/skills` も、ワールドのプロジェクトの変更はそのプロジェクトの `uv run pytest`、fork の変更は関連する `dotnet test` を通す。Spec は `$TOPLEVEL/docs/superpowers/specs/` に置く | 仕様 8.2 の 2 つの検証に、CI の skill-tests と同じ検査を足した（約 10 秒）。Spec の置き場は仕様 8.2 と `AGENTS.md` のとおりで、追跡される場所なのでコメントの Spec 行は「コミットしていなければローカルにしか無い」とする |
| D-25 | repo-cleanup の gitignore 対象の削除規則（N-14） | 手順 4 で `git status --short --ignored` も見る。ignore 対象が再生成できるキャッシュ（`.venv/`・`.uv-cache/`・`.pytest_cache/`・`.ruff_cache/`・`__pycache__/`・`node_modules/`）だけなら worktree ごと消してよく、それ以外があれば消さずに報告する。`git worktree remove` に `--force` を付けない | git 2.55 で、`git worktree remove`（`--force` なし）が ignore 対象の `reviews/a.md` を確認なしに消すことを実測した。統合前の 2 版の文言（「削除しない」と「照合せずに削除しない」）のどちらでも、この経路は防げていなかった。submodule が無いので `--force` の理由も無い |
| D-26 | repo-cleanup のローカル `main` と fork の追従 | 「ローカル main を作らない」規約を外し、`git switch main` と `git merge --ff-only origin/main` で更新する（`main` を別の worktree が使っていれば `git checkout --detach origin/main`）。上流で PR がマージされたら `bash scripts/resoloop-fork.sh sync` で fork の `main` を追従させる。push を伴うのでゲート B と同じくユーザー確認を得てから実行する | 仕様 8.2 の指示。このリポジトリにはローカル `main` があり、統合手順（仕様 10.1）も `main` を使う |
| D-27 | rst-writer の新しい profile | MaatLog profile・その fixture・旧 guide の移行案内を削除し、`create-reso-world` profile を既定にする。template 2 本は `assets/create-reso-world/` へ改名して使う。静的検査は `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"`。Sphinx の role（`:ref:`・`:term:`・`:doc:`）と用語集は使わない | 仕様 8.2 は `uv run --with docutils --with rstcheck` と指定している。`--no-project` はプロジェクトを cwd にしているときにその依存を同期させないため、`--report-level warning` は rstcheck の既定（INFO）だと template の未参照ラベルだけで失敗するため（実測）。docutils だけでは `:ref:` が `Unknown interpreted text role` の ERROR になる（実測） |
| D-28 | rst-writer の OSS Python Extension profile | 予約（未接続）のまま残し、MaatLog への言及と移行元の Issue 番号（#393 など）を参照文書から外す。evals の OSS のケースと手順は、README の冒頭で「移行元で作成した評価の記録」と明記して残す。MaatLog のケース 12 件は削除し、2 件は fixture なしに書き換え、新しい profile のケースを 3 件足す | 仕様 8.2 が削除を指示しているのは MaatLog profile と fixture だけ。仕様 11 章は evals の履歴的な記録を例外として認めている |
| D-29 | pi-model-name の `print-pi-model.sh` が内部で使う `python3` | 変えない | 仕様 8.2 の指示は `cd public` の例の削除だけ。スクリプトは pi の bash ツールから呼ばれ、29 件のテストが挙動を固定している。uv に替えると呼び出しのたびに起動の時間が増える |
| D-30 | find-docs の CLI の呼び方 | `npm install -g` の手順を外し、`npx ctx7@latest` で呼ぶ。API キーは `~/.config/create-reso-world/env` に置く | `ctx7` は Dev Container の導入一覧（仕様 7.1）に無く、グローバル導入は環境を変える。統合前の `CLAUDE.md` の規則も `npx ctx7@latest` だった。秘密情報の置き場はフェーズ 4 の D-17 |
| D-31 | 移行元の名残の常時検査（仕様 11） | `tests/skills/test_legacy_references.py` が追跡ファイル全体を `git grep` で調べる。除外は `docs/superpowers/`（移行の設計記録）と、名残が無いことを検査するために語を含む 3 本のテストと自分自身だけ。evals の履歴的な記録の例外は使わない（evals もすべて書き直した） | 仕様 11 章の成功条件を CI（skill-tests）で守る。ワールドのプロジェクトには数十 MB のテキストのメッシュがあるので、固定文字列で候補を絞ってから正規表現で判定する（約 0.4 秒） |

仕様 8.2 の herdr-agent-task の「パス参照を toplevel 基準に修正」は、スキル本文にパスの記述が無かったため、コマンドの実体（`.devcontainer/herdr-agent-task.bash`）と PATH に無いときの呼び方をリポジトリのルート基準で書き足すことで満たす（Task 12）。agent-handoff の description に `python-tdd-team` を戻さない判断（PH2-R4）はそのままとし、evals の q2 だけを書き換える（Task 7）。

仕様 10 章のフェーズ 5 の完了条件（`uv run pytest tests/skills .agents/skills` の全通過）は Task 16 で確認する。

## Global Constraints

- 変数: `M=/workspaces/reso-world`（メイン作業ツリー。ブランチ feat/slum02-slum で、別セッションが slum02 を編集中）、`W=/workspaces/reso-world/.worktrees/repo-redesign`（作業用 worktree。ブランチ chore/repo-redesign）。各ステップのコマンドは `export M=/workspaces/reso-world W=/workspaces/reso-world/.worktrees/repo-redesign` を実行してから、特記が無ければ `cd "$W"` で実行する。
- メイン作業ツリー `$M` では読み取りだけを行う。追跡ファイルの編集、`git add` / `commit` / `checkout` / `stash` / `reset` / `clean` / `fetch`、ファイルの移動・削除をしない。
- 変更のコミットはすべて `$W` で行う。コミットメッセージの末尾に、コミットするエージェント自身のモデル名の trailer を付ける（例: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`）。
- `git add` には明示したパスだけを渡す。削除は `git rm` に明示したパスで行う。`$W` で `git add -A` / `git add .` を使わない（テストが作る一時リポジトリの中は除く）。
- `git push --force` 系を使わない。push は Task 16 で controller が `git push origin chore/repo-redesign`（fast-forward を確かめてから）だけ行う。`main`・`feat/*`・`wip/*` を push・rebase・削除しない。PR を開かない（フェーズ 6）。
- Python は uv で実行する（`uv run ...`、`uv run --no-project ...`）。`python3` を直接呼ばない（既存のスクリプトとテストが中で使うものは除く）。
- 説明・文書・コミットの日本語で「契約」「原子的」「製品」「着地」を使わない（ルール本文を引用する `AGENTS.md` の「日本語表現」節を除く）。
- 触らないもの: TRPG 本文（`private/trpg/`、`tmp/` の `ATS.txt`・`BTD.txt`・`TNX.txt`）、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json`、`.pi/APPEND_SYSTEM.md` の `## Response Persona` 以降（Task 2 が変えるのはその前の 1 行だけ）、`.git/info/exclude`、`.mcp.json`、`.devcontainer/` 配下、ルートの README（フェーズ 6）、`docs/superpowers/` の既存の仕様と計画、`external/resoloop`。
- **実環境を変えるコマンドを実行しない。** `scripts/resoloop-fork.sh sync|build|test|install`、`npm install -g`、`dotnet tool install|update`、`install_beforehand.bash` は実行しない。本計画のテストは一時ディレクトリと一時リポジトリだけで動く。rst-writer の検査（`uv run --no-project --with docutils --with rstcheck ...`）は uv のキャッシュに入るだけなので実行してよい。
- 既存プロジェクトのディレクトリの中で `resoloop init` や `resoloop skills sync --update` を実行しない。
- スキルのテストの既知の失敗: フェーズ 5 の開始時点は `pi-model-name/tests/test_pi_model_name_contract.py` の 27 件と `repository-ownership/tests/test_public_release_guidance.py` の 7 件の計 34 件。Task 1 の後は pi-model-name の 27 件だけ、Task 2 の後は 0 件になる。各 Task の最後に次を実行し、何も表示されないことを確認する（Task 2 からは `grep -v` の除外が不要になる）。

```bash
cd "$W" && uv run pytest -q -rf tests/skills .agents/skills 2>&1 | grep '^FAILED' \
  | grep -v -e 'pi-model-name/tests/test_pi_model_name_contract.py' || true
```

- 各 Task の後に次も通る: `bash .devcontainer/run-tests.bash | tail -n 1`（`PASS: 23 test(s)`）、`bash scripts/check-layout.sh | tail -n 1`（`PASS: check-layout`）、`git ls-files -i -c --exclude-standard`（`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` の 1 行だけ）。
- 各 Task の差分は `git diff` の形式で載せてある。Markdown から保存して `git apply` で当ててもよい。Task 2 の差分は実行権の変更（100644 → 100755）を含む。手で書き写す場合は同じ結果にし、実行権は `chmod +x` で付ける。新しいファイルは全文を載せてある（mode は 100644）。
- ディレクトリを削除する Task（1 と 10）は、`git rm` の後に残る ignore 対象（テストの実行でできた `__pycache__/` など）も `rm -rf` で消す。テストはディレクトリが無くなったことを検査する。
- フェーズ 5 の範囲外（持ち越し節を参照）に手を出さない。

## Review Focus

- resoloop の PR の pr-review: `external/resoloop` が無い、ただのディレクトリ、`origin` か `upstream` が別のリポジトリのとき、toplevel へ読み替えずに終了コード 65 で止まり、`scripts/resoloop-fork.sh clone` を案内する。上流の PR の head は `upstream` から取る（Task 3 の fork の 4 ケースと `PR_REMOTE` のケース）。
- ignore 対象を含む worktree の片付け: `docs_draft/` や `reviews/` がある worktree を消さずに報告し、キャッシュだけなら消す。`--force` は使わない。fork の `sync` はユーザー確認の後だけ（Task 5）。
- review-fix-planning の反映の条件が、変更の種類ごとに決まっていて、無関係な一括検証を要求しない（Task 6）。
- rst-writer: 既定の profile が `create-reso-world` に変わり、OSS は未接続のまま止まる。新しい profile の検査コマンドが、template と fixture で `Success! No issues detected.` を返す（Task 10）。
- `scripts/new-world.sh --apply` で `AGENTS.md` が壊れた symlink か無いとき: 終了コード 3 で、何も変更せず、`resoloop init` を勧めない（Task 14 のケース 31・32）。
- 名残の検査: ワールドのプロジェクトの大きなメッシュの JSON で誤検出や遅延が無い。除外が古くなったら検出する（Task 15）。

## 実行前の準備（controller）

- [ ] 1. フェーズ 4 の Task 11 が完了し（台帳の末尾が `PHASE 4 COMPLETE.`）、worktree がクリーンであることを確かめる。本計画はフェーズ 4 の計画どおりの tree を前提にしている。フェーズ 4 の修正ラウンドで、本計画の Task が触るファイル（`tests/scripts/test-instructions.bash`、`tests/scripts/test-new-world.bash`、`scripts/new-world.sh`、`.pi/APPEND_SYSTEM.md` など）が変わった場合は、その Task の差分が当たるかを実行前に `git apply --check` で確かめ、当たらなければ差分の意図どおりに書き直す。
- [ ] 2. 本計画書をコミットする（`docs: add redesign phase 5 implementation plan`）。
- [ ] 3. SDD の作業ディレクトリと台帳を作る（`bash <sdd-skill>/scripts/sdd-workspace <この計画のパス>`）。
- [ ] 4. フェーズ 4 の SDD 作業ディレクトリ `$W/.superpowers/sdd/2026-09-27-redesign-phase4-devcontainer-and-ci/` を削除する。保留事項は本計画の Task と「持ち越し」節に転記済みであることを先に確かめる。

---

### Task 1: repository-ownership を削除する（仕様 8.2、持ち越し N-2）

移行元のアプリケーション（`public/` submodule）と親リポジトリの間で作業を振り分けるスキルで、このリポジトリには対象が無い。スキル本体とテスト、それを参照する Cursor のルール、Claude Code 用の symlink を削除する。どのランタイムからも見つからないことをテストで固定する（ファイルは Task 15 で追跡ファイル全体の検査に広げる）。

**Files:**
- Create: `tests/skills/test_legacy_references.py`
- Delete: `.agents/skills/repository-ownership/`（`SKILL.md`、`tests/test_public_release_guidance.py`、`tests/test_repository_ownership.py`）、`.cursor/rules/repository-ownership.mdc`、`.claude/skills/repository-ownership`（symlink）

**Interfaces:**
- Produces: `tests/skills/test_legacy_references.py` の `REMOVED_SKILLS`。Task 15 が同じファイルに追跡ファイルの検査を足す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/skills/test_legacy_references.py` を次の内容で作る。

```python
"""Guards against leftovers of the repository this environment was migrated from (spec 8.2, 11).

The migration source kept its application in a `public/` submodule and ran
`scripts/ci/verify.sh`. Neither exists here, so the skills that only made sense
there are removed, and no runtime may still discover them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Skills removed by spec 8.2, checked in every place a runtime looks for them.
REMOVED_SKILLS = ("repository-ownership",)


@pytest.mark.parametrize("name", REMOVED_SKILLS)
def test_removed_skill_is_gone_from_every_runtime(name: str) -> None:
    assert not (REPO_ROOT / ".agents/skills" / name).exists()
    link = REPO_ROOT / ".claude/skills" / name
    assert not link.is_symlink() and not link.exists()
    assert not (REPO_ROOT / ".cursor/rules" / f"{name}.mdc").exists()
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q tests/skills/test_legacy_references.py 2>&1 | tail -n 3
```

Expected: `assert not (REPO_ROOT / ".agents/skills" / name).exists()` の `AssertionError` で `1 failed`。

- [ ] **Step 3: スキル・ルール・symlink を削除する**

```bash
# 構成の変更（Task 1）
cd "$W"
git rm -rq .agents/skills/repository-ownership .cursor/rules/repository-ownership.mdc .claude/skills/repository-ownership
rm -rf .agents/skills/repository-ownership   # テストの実行で残った __pycache__ などの ignore 対象
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q tests/skills/test_legacy_references.py 2>&1 | tail -n 1
uv run pytest -q tests/skills .agents/skills 2>&1 | tail -n 1
bash scripts/check-layout.sh | tail -n 1
```

Expected: 1 本目は `1 passed`。2 本目は `27 failed, 184 passed, 1 skipped`（失敗は pi-model-name の既知の 27 件だけ）。3 本目は `PASS: check-layout`（`.claude/skills` と `.agents/skills` の 1:1 が保たれている）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add tests/skills/test_legacy_references.py
git commit -m "chore(skills): remove repository-ownership

The skill routed work between the migration source's application submodule
and its parent repository, neither of which exists here (spec 8.2). The skill,
its tests, the Cursor rule and the Claude Code link are removed, and a test
keeps every runtime from finding it again.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 2: pi-model-name の実行権と例を直す（仕様 8.2、持ち越し N-2）

`scripts/print-pi-model.sh` が index 上で 100644 のため、27 件のテストが実行できずに失敗している。100755 にする。仕様 8.2 のとおり `cd public` の例を消し、スクリプトの絶対パスはこのリポジトリの中で取ると書く（`external/resoloop` は別のリポジトリで、そこでは `git rev-parse --show-toplevel` が fork を返す）。本文の「契約」を「規則」に直す。`.pi/APPEND_SYSTEM.md` の「親 checkout からの」も同じ理由で外す（ペルソナ節より前の 1 行だけ）。

**Files:**
- Modify: `.agents/skills/pi-model-name/SKILL.md`、`.pi/APPEND_SYSTEM.md`（27 行目）
- Mode: `.agents/skills/pi-model-name/scripts/print-pi-model.sh`（100644 → 100755）
- Test: `.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py`、`tests/scripts/test-instructions.bash`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py b/.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py
index 0fbab76..89f5a66 100644
--- a/.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py
+++ b/.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py
@@ -40,6 +40,16 @@ def test_skill_mentions_runtime_contract() -> None:
         assert keyword in text
 
 
+def test_script_path_comes_from_this_repository() -> None:
+    # The script lives only in this repository. external/resoloop is another
+    # repository, so its own toplevel does not contain the script.
+    text = read_skill()
+    assert 'PI_MODEL_SCRIPT="$(git rev-parse --show-toplevel)/.agents/skills/pi-model-name/scripts/print-pi-model.sh"' in text
+    assert "external/resoloop" in text
+    assert "cd public" not in text
+    assert "親 checkout" not in text
+
+
 def test_script_executable() -> None:
     assert SCRIPT.is_file()
     mode = SCRIPT.stat().st_mode
diff --git a/tests/scripts/test-instructions.bash b/tests/scripts/test-instructions.bash
index 0bc94ec..a41d04c 100755
--- a/tests/scripts/test-instructions.bash
+++ b/tests/scripts/test-instructions.bash
@@ -53,6 +53,7 @@ lacks .pi/APPEND_SYSTEM.md 'CLAUDE.md を遵守'
 lacks .pi/APPEND_SYSTEM.md 'subagent-launch-verification'
 lacks .pi/APPEND_SYSTEM.md '# resoloop 注意'
 lacks .pi/APPEND_SYSTEM.md '@.agents/skills/'
+lacks .pi/APPEND_SYSTEM.md '親 checkout'
 for s in '/skill:agent-handoff' 'async: false' 'herdr-agent-task' 'pi-model-name' 'simplify-in-subagent' 'MODEL_NAME'; do
   has .pi/APPEND_SYSTEM.md "$s"
 done
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/pi-model-name 2>&1 | tail -n 1
bash tests/scripts/test-instructions.bash; echo "exit=$?"
```

Expected: 1 本目は `28 failed, 2 passed`（既知の 27 件と、`cd public` が残っていることを検出する `test_script_path_comes_from_this_repository`）。2 本目は `FAIL: .pi/APPEND_SYSTEM.md must not contain: 親 checkout` で終了コード 1。

- [ ] **Step 3: 実行権・本文・pi の規約を直す**

次の差分を当てる（実行権の変更を含む。手で直す場合は `chmod +x .agents/skills/pi-model-name/scripts/print-pi-model.sh` も実行する）。

````diff
diff --git a/.agents/skills/pi-model-name/SKILL.md b/.agents/skills/pi-model-name/SKILL.md
index 941efde..cc55749 100644
--- a/.agents/skills/pi-model-name/SKILL.md
+++ b/.agents/skills/pi-model-name/SKILL.md
@@ -35,7 +35,7 @@ echo "$PI_DISTILL_MODEL"
 grep -o '"modelId":"[^"]*"' ~/.pi/agent/sessions/--*/ *.jsonl | tail -1
 ```
 
-正式な `MODEL_NAME` に履歴を使わない。`PI_PROVIDER` / `PI_MODEL` が空なら履歴へフォールバックせず、停止してユーザに確認する。これは `pr-review` の契約と同じである。
+正式な `MODEL_NAME` に履歴を使わない。`PI_PROVIDER` / `PI_MODEL` が空なら履歴へフォールバックせず、停止してユーザに確認する。これは `pr-review` の規則と同じである。
 
 ## Quick Reference
 
@@ -54,15 +54,12 @@ grep -o '"modelId":"[^"]*"' ~/.pi/agent/sessions/--*/ *.jsonl | tail -1
 
 同梱スクリプトが strict 既定で表示する。ランタイム変数が揃い、現在のセッションファイルがある場合は、選択値と直近の応答記録を照合する。履歴読みは情報表示の明示指定だけに使う。
 
-親 checkout の root にいるうちにスクリプトの絶対パスを取得する。同じシェルなら `public/` や公開側 worktree に移動した後も使える。
+スクリプトはこのリポジトリにだけあるので、このリポジトリの中（ルートかワールドのプロジェクト）で絶対パスを取得する。`external/resoloop` は別のリポジトリで、そこで `git rev-parse --show-toplevel` を実行すると fork の checkout を返す。先に取得しておけば、同じシェルで `external/resoloop` に移動した後も使える。
 
 ```bash
-# 親 checkout の root で実行
+# このリポジトリの中で実行する
 PI_MODEL_SCRIPT="$(git rev-parse --show-toplevel)/.agents/skills/pi-model-name/scripts/print-pi-model.sh"
 
-# 公開側 checkout に移動した後も実行できる
-cd public
-
 # 既定: provider/model を表示。欠けたら exit 2 で停止
 "$PI_MODEL_SCRIPT"
 
diff --git a/.agents/skills/pi-model-name/scripts/print-pi-model.sh b/.agents/skills/pi-model-name/scripts/print-pi-model.sh
old mode 100644
new mode 100755
diff --git a/.pi/APPEND_SYSTEM.md b/.pi/APPEND_SYSTEM.md
index 46b2a6c..5aa61c6 100644
--- a/.pi/APPEND_SYSTEM.md
+++ b/.pi/APPEND_SYSTEM.md
@@ -24,7 +24,7 @@
 
 スキル: pr-review の `MODEL_NAME` は pi-model-name スキルの手順で決める。
 
-1. pi の bash ツール内で `PI_PROVIDER` と `PI_MODEL` の両方を確認する。スクリプトを使う場合は、同スキルに記載された親 checkout からの絶対パス取得手順に従う。
+1. pi の bash ツール内で `PI_PROVIDER` と `PI_MODEL` の両方を確認する。スクリプトを使う場合は、同スキルに記載された絶対パスの取得手順に従う。
 2. 片方でも空なら停止し、ユーザに正確なモデル識別子を確認する。セッション履歴の `model_change` や `PI_DISTILL_MODEL` を正式な `MODEL_NAME` の根拠にしない。
 
 ## Response Persona
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/pi-model-name 2>&1 | tail -n 1
bash tests/scripts/test-instructions.bash
git diff --summary -- .agents/skills/pi-model-name/scripts/print-pi-model.sh
uv run pytest -q tests/skills .agents/skills 2>&1 | tail -n 1
```

Expected: `30 passed`、`PASS: root instruction files follow spec 5.2 and 5.3`（ペルソナ節の sha256 も一致する）、` mode change 100644 => 100755 .agents/skills/pi-model-name/scripts/print-pi-model.sh`、`212 passed, 1 skipped`（ここから既知の失敗は 0 件）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/pi-model-name/SKILL.md .agents/skills/pi-model-name/scripts/print-pi-model.sh \
  .agents/skills/pi-model-name/tests/test_pi_model_name_contract.py .pi/APPEND_SYSTEM.md tests/scripts/test-instructions.bash
git commit -m "fix(pi-model-name): make the script executable and drop the submodule example

print-pi-model.sh was tracked as 100644, so the 27 tests that run it failed.
The example that changed into the migration source's submodule is removed;
the script path is taken inside this repository, because external/resoloop is
another repository. The pi rules no longer mention a parent checkout.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 3: pr-review の作業ルートと検証の規則（仕様 5.4・8.2、持ち越し N-14）

作業ルートの解決ブロックを、仕様 5.4 の 3 行に置き換える（D-22）。fork の経路では `origin` と `upstream` の両方を確かめ、上流の PR の head は `upstream` から取る。`verify.sh` の禁止条項は「重い一括検証を再実行しない」に一般化する（D-23）。レビューの保存先は `MAIN_ROOT` 直下の `reviews/` で、fork 側では ignore されないので commit に含めないと書く。

N-14 の 4 件もここで直す。

- 手順 5 に、委譲しない場合はメインエージェントが呼び出し元・呼び出し先、依存関係ファイル、既存テストを辿る 1 文を足す
- Codex 以外のモデル名の規則に「短縮・一般化しない」を戻す
- 手順 1 の 3 項目目の「未指定の場合」を「`PR_ARG` が確定しない場合」にし、1 項目目の「未指定」と重ならないようにする
- contract テストの固定を強める: `create` の行はちょうど 2 本で `--model-name` を持つのは Codex 以外の 1 本だけ、委譲の制限と Devin の transcript の規則を SKILL.md で固定、`allowed-tools` を行全体で比べる

手順 6 の重点観点の例（移行元の Web アプリケーションのもの）は、このリポジトリの例に替える。

**Files:**
- Modify: `.agents/skills/pr-review/SKILL.md`、`.agents/skills/pr-review/references/time-budget.md`（検証シナリオ S20 の 1 行）
- Test: `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

**Interfaces:**
- Produces: 解決ブロックの変数 `MAIN_ROOT`・`PR_REMOTE`・`FORK_ROOT`。終了コードは、対象外のリポジトリが 64（`unsupported PR repository: <owner/repo>`）、fork の checkout が無いか別物なら 65（`<FORK_ROOT> is not the resoloop fork checkout; run scripts/resoloop-fork.sh clone first`）。Task 6 の review-fix-planning は同じ規則を文章で参照する。

- [ ] **Step 1: 失敗するテストを書く**

一時リポジトリの fixture を、`origin` が `usaturn/create-reso-world` の親と、`external/resoloop` に置いた fork（`missing`・`plain`・`wrong-origin`・`wrong-upstream` の変化形あり）にする。解決ブロックを実行するハーネスは `MAIN_ROOT` と `PR_REMOTE` の 2 行を出力する。

````diff
diff --git a/.agents/skills/pr-review/tests/test_pr_review_skill_contract.py b/.agents/skills/pr-review/tests/test_pr_review_skill_contract.py
index 35a7d43..d315343 100644
--- a/.agents/skills/pr-review/tests/test_pr_review_skill_contract.py
+++ b/.agents/skills/pr-review/tests/test_pr_review_skill_contract.py
@@ -8,6 +8,7 @@ from dataclasses import dataclass
 from pathlib import Path
 
 import pytest
+import yaml
 
 REPO_ROOT = Path(__file__).resolve().parents[4]
 AGENTS_SKILL = REPO_ROOT / ".agents/skills/pr-review/SKILL.md"
@@ -97,59 +98,37 @@ def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProce
     )
 
 
-def build_parent_with_public(tmp_path: Path) -> Path:
-    """Create an isolated parent repo with a registered public submodule."""
+PARENT_ORIGIN = "https://github.com/usaturn/create-reso-world.git"
+FORK_ORIGIN = "https://github.com/usaturn/resoloop.git"
+FORK_UPSTREAM = "https://github.com/orange3134/resoloop.git"
+
+
+def build_parent_with_fork(tmp_path: Path, *, fork: str = "ok") -> Path:
+    """Create an isolated parent repo; external/resoloop is the fork checkout.
+
+    fork="ok" builds what scripts/resoloop-fork.sh clone leaves: a repository
+    of its own with origin and upstream. "missing" leaves no checkout, "plain"
+    leaves an ordinary directory inside the parent, and "wrong-origin" /
+    "wrong-upstream" point that remote at another repository.
+    """
     parent = tmp_path / "parent"
     parent.mkdir()
     _git(parent, "init")
-    _git(parent, "commit", "--allow-empty", "-m", "init parent")
-    _git(parent, "remote", "add", "origin", "https://github.com/owner/repository.git")
-
-    public_src = tmp_path / "public_src"
-    public_src.mkdir()
-    _git(public_src, "init")
-    (public_src / "README.md").write_text("public\n", encoding="utf-8")
-    _git(public_src, "add", "README.md")
-    _git(public_src, "commit", "-m", "init public")
-    _git(public_src, "remote", "add", "origin", "https://github.com/usaturn/maatlog.git")
-
-    # Local path submodule clones require protocol.file.allow on modern Git.
-    subprocess.run(
-        [
-            "git",
-            "-c",
-            "user.email=test@example.com",
-            "-c",
-            "user.name=test",
-            "-c",
-            "protocol.file.allow=always",
-            "submodule",
-            "add",
-            str(public_src.resolve()),
-            "public",
-        ],
-        cwd=parent,
-        check=True,
-        text=True,
-        capture_output=True,
-    )
-    _git(
-        parent,
-        "config",
-        "-f",
-        ".gitmodules",
-        "submodule.public.url",
-        "https://github.com/usaturn/maatlog.git",
-    )
-    _git(
-        parent / "public",
-        "remote",
-        "set-url",
-        "origin",
-        "https://github.com/usaturn/maatlog.git",
-    )
-    _git(parent, "add", ".gitmodules", "public")
-    _git(parent, "commit", "-m", "register public submodule")
+    (parent / ".gitignore").write_text("/external/\n", encoding="utf-8")
+    _git(parent, "add", ".gitignore")
+    _git(parent, "commit", "-m", "init parent")
+    _git(parent, "remote", "add", "origin", PARENT_ORIGIN)
+    checkout = parent / "external" / "resoloop"
+    if fork == "missing":
+        return parent.resolve()
+    checkout.mkdir(parents=True)
+    if fork == "plain":
+        return parent.resolve()
+    _git(checkout, "init")
+    _git(checkout, "commit", "--allow-empty", "-m", "init fork")
+    other = "https://github.com/someone/resoloop.git"
+    _git(checkout, "remote", "add", "origin", other if fork == "wrong-origin" else FORK_ORIGIN)
+    _git(checkout, "remote", "add", "upstream", other if fork == "wrong-upstream" else FORK_UPSTREAM)
     return parent.resolve()
 
 
@@ -157,14 +136,14 @@ def build_parent_with_public(tmp_path: Path) -> Path:
 class ResolverFixture:
     toplevel: Path
 
-    def resolve(self, pr_url: str, *, skill_path: Path) -> Path:
+    def resolve(self, pr_url: str, *, skill_path: Path) -> tuple[Path, str]:
         script = extract_resolver_script(read(skill_path))
         pr_json = json.dumps({"url": pr_url})
-        # Emit MAIN_ROOT after the skill block for the test harness.
+        # Emit MAIN_ROOT and PR_REMOTE after the skill block for the test harness.
         harness = f"""set -euo pipefail
 PR_JSON={json.dumps(pr_json)}
 {script}
-printf '%s\\n' "$MAIN_ROOT"
+printf '%s\\n' "$MAIN_ROOT" "$PR_REMOTE"
 """
         completed = subprocess.run(
             ["bash", "-c", harness],
@@ -175,17 +154,21 @@ printf '%s\\n' "$MAIN_ROOT"
         )
         if completed.returncode != 0:
             raise ResolverStopped(completed.returncode, completed.stderr)
-        main_root = completed.stdout.strip().splitlines()[-1]
-        return Path(main_root).resolve()
+        main_root, pr_remote = completed.stdout.strip().splitlines()[-2:]
+        return Path(main_root).resolve(), pr_remote
 
 
-@pytest.fixture
-def resolver_fixture(tmp_path: Path) -> ResolverFixture:
-    toplevel = build_parent_with_public(tmp_path)
+def make_resolver(tmp_path: Path, fork: str = "ok") -> ResolverFixture:
+    toplevel = build_parent_with_fork(tmp_path, fork=fork)
     _FixtureState.toplevel = toplevel
     return ResolverFixture(toplevel=toplevel)
 
 
+@pytest.fixture
+def resolver_fixture(tmp_path: Path) -> ResolverFixture:
+    return make_resolver(tmp_path)
+
+
 def assert_review_contract(content: str) -> None:
     # The user-supplied value is kept raw ($PR_ARG) so gh resolves a URL's
     # owner/repo itself; every later gh call is pinned to the canonical
@@ -196,8 +179,8 @@ def assert_review_contract(content: str) -> None:
     assert 'gh pr diff "$PR_URL"' in content
     assert 'gh pr view "$PR_NUMBER"' not in content
     assert 'gh pr diff "$PR_NUMBER"' not in content
-    # The helper lives in the parent repository's skill tree, so it must
-    # resolve from $TOPLEVEL even when MAIN_ROOT points at public/.
+    # The helper lives in this repository's skill tree, so it must resolve
+    # from $TOPLEVEL even when MAIN_ROOT points at external/resoloop.
     assert 'HELPER="$TOPLEVEL/' in content
     assert 'HELPER="$MAIN_ROOT/' not in content
     assert 'git rev-parse --short=12 "$PR_HEAD"' in content
@@ -216,13 +199,18 @@ def assert_review_contract(content: str) -> None:
     assert "PR_URL=$(printf '%s' \"$PR_JSON\" | jq -r .url)" in content
     assert "github_repository()" in content
     assert 'MAIN_ROOT="$TOPLEVEL"' in content
-    assert 'MAIN_ROOT="$TOPLEVEL/public"' in content
-    assert "usaturn/maatlog" in content
-    assert "submodule.public.url" in content
-    assert "submodule status -- public" in content
+    assert 'FORK_ROOT="$TOPLEVEL/external/resoloop"' in content
+    assert 'MAIN_ROOT="$FORK_ROOT"' in content
+    assert "usaturn/resoloop" in content
+    assert "orange3134/resoloop" in content
     assert 'git -C "$TOPLEVEL" remote get-url origin' in content
-    assert 'git -C "$TOPLEVEL/public" remote get-url origin' in content
+    assert 'git -C "$FORK_ROOT" remote get-url upstream' in content
+    assert "scripts/resoloop-fork.sh clone" in content
     assert "unsupported PR repository" in content
+    assert "リポジトリ境界" in content
+    assert 'fetch "$PR_REMOTE" "+pull/<PR_NUMBER>/head:$PR_REF"' in content
+    assert "external/resoloop/reviews/" in content
+    assert "submodule" not in content
     assert "#160-feature-issue-148-fail-fast" in content
     assert "reviews/#" in content
     assert "追跡パス" not in content
@@ -231,21 +219,23 @@ def assert_review_contract(content: str) -> None:
     assert 'MAIN_ROOT="$(pwd)"' not in content
 
 
-def assert_skip_verify_sh_allows_other_verification_contract(content: str) -> None:
-    # Review skips ./scripts/ci/verify.sh because implementation already
-    # ran it and repeating it is too slow. Related pytest, REPL, and
-    # minimal repro scripts remain allowed. helper verify is destination
-    # fingerprinting, not the CI runner.
-    assert "レビュー中に `./scripts/ci/verify.sh` を実行しない" in content
-    assert "実装時に確認" in content
+def assert_heavy_verification_is_not_rerun_contract(content: str) -> None:
+    # Review does not rerun the bulk suites: the implementation and CI already
+    # ran them and repeating them is too slow. Related pytest, single test
+    # scripts, REPL and minimal repro scripts remain allowed. helper verify is
+    # destination fingerprinting, not a test run.
+    assert "重い一括検証を再実行しない" in content
+    assert "bash .devcontainer/run-tests.bash" in content
+    assert "scripts/resoloop-fork.sh test" in content
+    assert "実装時と CI で確認済み" in content
     assert "冗長" in content
     assert "3. **実行検証**" in content
     assert "関連する pytest" in content
     assert "REPL" in content
     assert "最小再現スクリプト" in content
     assert "helper の `verify`" in content
-    assert "`CLAUDE.md` の検証プロファイル規定より優先する" in content
-    assert "verify.sh が起動するテスト" not in content
+    assert "`AGENTS.md` が示す完了前の検証手順より優先する" in content
+    assert "scripts/ci/" not in content
     assert "動かして確かめることも行わない" not in content
     assert "プロジェクトのテストを実行しない" not in content
     assert "プロジェクトのテストコマンド" not in content
@@ -259,8 +249,8 @@ def test_pr_review_skills_define_review_update_contract(skill: Path) -> None:
 
 
 @pytest.mark.parametrize("skill", [AGENTS_SKILL])
-def test_pr_review_skills_skip_verify_sh_and_allow_other_verification(skill: Path) -> None:
-    assert_skip_verify_sh_allows_other_verification_contract(read(skill))
+def test_pr_review_skills_do_not_rerun_heavy_verification(skill: Path) -> None:
+    assert_heavy_verification_is_not_rerun_contract(read(skill))
 
 
 def assert_cleanup_contract(content: str) -> None:
@@ -301,21 +291,34 @@ def test_skill_interpolation_is_limited_to_the_target_line() -> None:
     assert re.search(r"\$[0-9]", content) is None
 
 
+ALLOWED_TOOLS = (
+    "Read, Grep, Glob, Bash(gh *), Bash(git *), Bash(date *), "
+    "Bash(uv run --no-project python *pr_review_workspace.py *), "
+    "Edit(/tmp/pr-review-*/review-backup/**), Write(/tmp/pr-review-*/review-backup/**), Agent"
+)
+
+
 def test_skill_keeps_claude_code_permissions_consistent() -> None:
     content = read(AGENTS_SKILL)
-    head = content.split("---", 2)[1]
-    assert "allowed-tools:" in head
-    assert "Bash(date *)" in head
-    assert "Edit(/tmp/pr-review-*/review-backup/**)" in head
-    assert 'argument-hint: "<PR番号またはURL>"' in head
-    assert '--model-name "$MODEL_NAME"' in content
+    head = yaml.safe_load(content.split("---", 2)[1])
+    # Claude Code only pre-approves what this line lists; a dropped entry turns
+    # the helper, the draft backup or the delegation into a permission prompt.
+    assert head["allowed-tools"] == ALLOWED_TOOLS
+    assert head["argument-hint"] == "<PR番号またはURL>"
     assert "CODEX_THREAD_ID" in content
     create_lines = [line for line in content.splitlines() if '"$HELPER" create' in line]
-    assert len(create_lines) >= 2
+    assert len(create_lines) == 2
     for line in create_lines:
         # allowed-tools only permits Edit/Write under /tmp/pr-review-*, so every
         # runtime pins the helper's temp root there.
         assert "--temp-root /tmp" in line, line
+    # Codex resolves the model itself; only the other runtimes pass it once.
+    with_model = [line for line in create_lines if "--model-name" in line]
+    assert len(with_model) == 1
+    assert with_model[0].count('--model-name "$MODEL_NAME"') == 1
+    codex_block = content.split("Codex では次を実行する", 1)[1].split("```", 2)[1]
+    assert '"$HELPER" create' in codex_block
+    assert "--model-name" not in codex_block
 
 
 def test_skill_keeps_runtime_specific_notes() -> None:
@@ -324,33 +327,84 @@ def test_skill_keeps_runtime_specific_notes() -> None:
     for heading in ("### 対象 PR の受け取り", "### Claude Code", "### Codex", "### Devin", "### pi"):
         assert heading in content
     assert "You are powered by" in content
+    assert "`~/.local/share/devin/cli/transcripts/`" in content
     assert "pi-model-name" in content
+    # Every runtime that passes MODEL_NAME uses the identifier verbatim.
+    assert "既存レビューのファイル名から推測・短縮・一般化しない" in content
+
+
+def test_delegation_limits_stay_in_the_skill_body() -> None:
+    content = read(AGENTS_SKILL)
+    for rule in (
+        "サブエージェントは `$WT` 上のコードと PR 差分（`gh pr diff` の結果）のみ調査する",
+        "`reviews/` 全体と `$PREVIOUS_REVIEW` の読解はメインエージェントだけが行う",
+        "委譲時は `reviews/` を調査範囲から明示的に除外する",
+        "この読解はメインエージェントのみが行い、サブエージェントに委譲しない",
+        "指摘の根拠となる精読をサブエージェント任せにしない",
+        "反証試行のための追加委譲はしない",
+        "サブエージェントの報告のみを根拠に【検証済み】を付けない",
+        "既存 review 本文をサブエージェントへ渡していないか",
+    ):
+        assert rule in content, rule
+
+
+def test_main_agent_traces_the_change_when_not_delegating() -> None:
+    content = read(AGENTS_SKILL)
+    step5 = content.split("5. **コンテキスト読解", 1)[1].split("6. **", 1)[0]
+    assert "委譲しない場合は、メインエージェントが自分で" in step5
+    for target in ("呼び出し元・呼び出し先", "依存関係ファイル", "既存テスト"):
+        assert target in step5.split("委譲しない場合は、メインエージェントが自分で", 1)[1], target
+
+
+def test_pr_argument_fallback_is_stated_once() -> None:
+    content = read(AGENTS_SKILL)
+    step1 = content.split("1. **PR情報の取得**", 1)[1].split("2. **", 1)[0]
+    assert "`PR_ARG` が確定しない場合" in step1
+    assert "   - 未指定の場合、" not in step1
 
 
 @pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
 @pytest.mark.parametrize(
-    ("pr_url", "expected_root"),
+    ("pr_url", "expected_root", "expected_remote"),
     [
-        ("https://github.com/owner/repository/pull/1", TOPLEVEL),
-        ("https://github.com/usaturn/maatlog/pull/2", TOPLEVEL / "public"),
+        ("https://github.com/usaturn/create-reso-world/pull/1", TOPLEVEL, "origin"),
+        ("https://github.com/usaturn/resoloop/pull/2", TOPLEVEL / "external" / "resoloop", "origin"),
+        # An upstream PR's pull/<N>/head lives in the upstream repository.
+        ("https://github.com/orange3134/resoloop/pull/3", TOPLEVEL / "external" / "resoloop", "upstream"),
     ],
 )
 def test_pr_review_resolver_selects_only_registered_repositories(
     skill_path: Path,
     pr_url: str,
     expected_root: Path,
+    expected_remote: str,
     resolver_fixture: ResolverFixture,
 ) -> None:
-    assert resolver_fixture.resolve(pr_url, skill_path=skill_path) == expected_root
+    main_root, pr_remote = resolver_fixture.resolve(pr_url, skill_path=skill_path)
+    assert main_root == expected_root
+    assert pr_remote == expected_remote
 
 
 @pytest.mark.parametrize("skill_path", [AGENTS_SKILL])
 def test_pr_review_resolver_stops_for_unknown_repository(skill_path: Path, resolver_fixture: ResolverFixture) -> None:
-    with pytest.raises(ResolverStopped):
+    with pytest.raises(ResolverStopped) as stopped:
         resolver_fixture.resolve(
             "https://github.com/other/repository/pull/3",
             skill_path=skill_path,
         )
+    assert stopped.value.returncode == 64
+    assert "unsupported PR repository: other/repository" in stopped.value.stderr
+
+
+@pytest.mark.parametrize("fork", ["missing", "plain", "wrong-origin", "wrong-upstream"])
+def test_pr_review_resolver_stops_without_a_verified_fork_checkout(tmp_path: Path, fork: str) -> None:
+    # A plain directory under the parent must not resolve to the parent's
+    # own checkout, and a checkout with other remotes is not the fork.
+    resolver = make_resolver(tmp_path, fork=fork)
+    with pytest.raises(ResolverStopped) as stopped:
+        resolver.resolve("https://github.com/orange3134/resoloop/pull/4", skill_path=AGENTS_SKILL)
+    assert stopped.value.returncode == 65
+    assert "scripts/resoloop-fork.sh clone" in stopped.value.stderr
 
 
 @pytest.mark.parametrize("forbidden", ["$TOPLEVEL/devenv", "submodule status -- devenv"])
````

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/pr-review/tests/test_pr_review_skill_contract.py 2>&1 | tail -n 1
```

Expected: `12 failed, 13 passed`。解決ブロックの 3 経路は `bash: line 31: PR_REMOTE: unbound variable`（旧ブロックが `PR_REMOTE` を決めない）、fork の 4 ケースは終了コード 64（旧ブロックが resoloop を知らない）、本文の 5 件は文言の不一致で失敗する。`allowed-tools` と委譲の制限のテストは、今の本文を固定するものなのでこの時点で通る。

- [ ] **Step 3: SKILL.md と時間予算の参照を直す**

````diff
diff --git a/.agents/skills/pr-review/SKILL.md b/.agents/skills/pr-review/SKILL.md
index 0cfa25d..54c6378 100644
--- a/.agents/skills/pr-review/SKILL.md
+++ b/.agents/skills/pr-review/SKILL.md
@@ -44,17 +44,17 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 - [時間予算と委譲規約](references/time-budget.md)を最初の PR API 呼び出しより前に全文を読む。開始時刻・期限・委譲可否・打ち切りはその規約に従う
 - レビュー出力は助言として扱われる
 - プロダクトコード・テストを編集しない
-- レビュー中に `./scripts/ci/verify.sh` を実行しない。実装時に確認済みであり、レビューで再実行すると時間がかかり冗長だからである。関連する pytest、REPL、最小再現スクリプトなど、verify.sh 以外の検証は実行してよい。helper の `verify`（destination フィンガープリント確認）は `./scripts/ci/verify.sh` ではない。この禁止は `CLAUDE.md` の検証プロファイル規定より優先する
+- レビュー中に重い一括検証を再実行しない。対象は `bash .devcontainer/run-tests.bash`、リポジトリ全体やワールドのプロジェクト全体の `uv run pytest`、`scripts/resoloop-fork.sh test`（fork の `dotnet test` 全体）などである。実装時と CI で確認済みであり、レビューで再実行すると時間がかかり冗長だからである。関連する pytest（ファイルやテスト名で絞ったもの）、個別のテストスクリプト、REPL、最小再現スクリプトなど、指摘の検証に必要な範囲の実行はしてよい。helper の `verify`（destination フィンガープリント確認）はテストの実行ではない。この規定は、`AGENTS.md` が示す完了前の検証手順より優先する
 - レビュー中は `git clean`、`git checkout -f`、`git reset --hard` を実行しない。既存 worktree を再利用・初期化しない
 - 自セッションの worktree の削除は helper の `cleanup` だけが行う。`git worktree remove`、`rm -rf` などの削除コマンドを自分で組み立てない。`cleanup` が拒否した場合も手で代行しない
 - `cleanup` は保存成功（`$DESTINATION` の内容が `$DRAFT` と一致）を検証できたときだけ削除する。検証できない場合は何も削除せず停止し、`$WT` と `$DRAFT` の完全パスを報告してユーザの判断に委ねる
 - レビュー中に生成した検証ログ・スクリーンショット・一時スクリプト等の証跡を `$WT` に残さない。あとで見返す必要がある内容はレビュー本文の「根拠」に転記し、`$DESTINATION` だけで完結させる
 - 最終応答で `$WT` 配下のパスを参照しない（`cleanup` 成功後は `$WT` が存在しないため）。`cleanup` の失敗または停止確認不能による省略時は、残った `$WT` とセッションの完全パスを報告する
 - 独立したレビューを行うため、`reviews/#<PR番号>-<変換後ブランチ名>/` にある他モデルのレビュー本文は、候補の洗い出し・重点観点の収集・重複確認・自分の指摘の検証を含むいかなる目的でも読まない。レビュー完了後も読まない。メインリポジトリ側と `$WT` 側（PR に同梱された `reviews/`）のどちらも対象とする
-- `MAIN_ROOT` は PR URL の GitHub `owner/repository` を現在のリポジトリの `origin` と照合して確定する。親リポジトリ一致なら toplevel、公開リポジトリ `usaturn/maatlog` なら登録済み `public/` submodule、それ以外は推測せず停止する
+- `MAIN_ROOT` は PR URL の GitHub `owner/repository` を、ルート `AGENTS.md` の「リポジトリ境界」の表に照らして確定する。このリポジトリ（toplevel の `origin` と一致）なら toplevel、`usaturn/resoloop` または `orange3134/resoloop` なら `<toplevel>/external/resoloop`（自前の checkout で、`origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` であること。満たさなければ `scripts/resoloop-fork.sh clone` を案内して停止する）、それ以外は推測せず停止する
 - 自モデルの既存レビューはライブの `$DESTINATION` ではなく、`create` が返した `$PREVIOUS_REVIEW`（セッション内 snapshot）だけを読む。`$PREVIOUS_REVIEW` が空なら既存レビューなしとして扱う
 - Codex ではモデル名を自分で推測・短縮・一般化せず、`create` が Codex session metadata から確定した `model_name` を使用する。Codex 実行時は `create --model-name` を渡さない
-- Codex 以外では、実行中のエージェントランタイムが提示する正確なモデル識別子を `MODEL_NAME` として記録し、`create --model-name "$MODEL_NAME"` に一度だけ渡す。モデル系列の説明、設定ファイル、既存レビューのファイル名から推測しない（`/`・空白を含む形式もそのまま渡してよい。ヘルパーがファイル名用に `/`・空白類を `-` へ置換する）
+- Codex 以外では、実行中のエージェントランタイムが提示する正確なモデル識別子を `MODEL_NAME` として記録し、`create --model-name "$MODEL_NAME"` に一度だけ渡す。モデル系列の説明、設定ファイル、既存レビューのファイル名から推測・短縮・一般化しない（`/`・空白を含む形式もそのまま渡してよい。ヘルパーがファイル名用に `/`・空白類を `-` へ置換する）
 - Codex 以外で正確なモデル識別子を取得できない場合、または置換後も安全なファイル名にならない場合は、代替名で続行せず停止してユーザに確認する
 - 過去のセッション履歴（`~/.pi/agent/sessions` 配下の jsonl の `model_change` の `modelId` 等）は実行中のランタイムの提示ではないため、`MODEL_NAME` の根拠にしない。ランタイムが識別子を提示していない場合は履歴へフォールバックせず、前項の「取得できない場合」として停止してユーザに確認する
 - provider にかかわらず、draft と destination は `create` が返した値をそのまま使用する。`save` では model、draft、destination を再指定しない
@@ -79,6 +79,7 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 - 実行可能な指摘がない場合は、その旨を明確に伝える
 - レビューは日本語で返す
 - レビュー結果は常に `create` が返した `$DESTINATION` に作成する。`$DESTINATION` はヘルパーが `reviews/#<PR番号>-<変換後ブランチ名>/<model>.md` へ配置する。ブランチ名とモデル識別子に含まれる `/`・空白類およびディレクトリ名に使えない記号はヘルパーが使える記号へ変換する（例: PR 160・ブランチ `feature/issue-148-fail-fast` は `#160-feature-issue-148-fail-fast` 配下、モデル `opencode/deepseek-v4-flash-free` は `opencode-deepseek-v4-flash-free.md`、モデル `Cursor Grok 4.6` は `Cursor-Grok-4.6.md`）。`create` が返す `model_name` もこの変換後の値であり、エージェントが手で組み立てない
+- 保存先の `reviews/` は `MAIN_ROOT` の直下にある。resoloop の PR では `external/resoloop/reviews/` になり、fork の `.gitignore` はこれを無視しない。fork で commit するときは `git add` に明示したパスだけを渡し、`reviews/` を含めない
 - 同じ PR を同じモデルで再レビューする場合は、同一ファイルの内容全体を上書きし、別名ファイルを作らない。別モデルの結果は同じ PR ディレクトリ内の別ファイルへ保存する
 - PR 上で既に指摘済みの問題は重複報告しない（触れる場合は「既出」と明記する）
 - 件数表は active findings のみから計算する。重大度判定は active findings、確認不足判定は coverage と pending も参照する。Resolved findings は件数・重大度判定に含めない
@@ -96,12 +97,12 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 1. **PR情報の取得**:
    - 対象 PR は、冒頭の `対象 PR` 行が補間済みならその値、未指定ならユーザのメッセージで指定された PR 番号・URL から読み取り、前後空白を除去して `PR_ARG` に入れる。番号・`#` 始まり・GitHub URL はいずれも `gh pr view` がそのまま解釈できるため番号へ正規化しない。URL の owner/repository を失うと別リポジトリの同名番号 PR を取得する。行が空欄または `$` で始まるプレースホルダ表記のまま残っている場合は未指定とする。
    - `PR_ARG` が確定している場合、`PR_JSON=$(gh pr view "$PR_ARG" --json number,title,body,baseRefName,headRefName,headRefOid,url,additions,deletions,changedFiles)` を実行し、PRのタイトル、説明、ベースブランチ、ヘッドブランチなどのメタ情報を取得してコンテキストを把握する。PR 番号・ヘッドブランチ・正規 URL は機械的に `PR_NUMBER=$(printf '%s' "$PR_JSON" | jq -r .number)`・`HEAD_BRANCH=$(printf '%s' "$PR_JSON" | jq -r .headRefName)`・`PR_URL=$(printf '%s' "$PR_JSON" | jq -r .url)` で確定する。以降 `gh pr view`・`gh pr diff` には `"$PR_URL"` を使い、カレントリポジトリへの暗黙解決に依存しない。
-   - 未指定の場合、`PR_JSON=$(gh pr view --json number,title,body,baseRefName,headRefName,headRefOid,url,additions,deletions,changedFiles)` を実行して現在のブランチに関連付けられたPRの情報を取得し、同じく `PR_NUMBER`・`HEAD_BRANCH`・`PR_URL` を確定する。関連付けられたPRがない場合はユーザにPR番号の指定を促す。
+   - `PR_ARG` が確定しない場合（`対象 PR` 行が未指定で、ユーザのメッセージにも PR 番号・URL が無い場合）、`PR_JSON=$(gh pr view --json number,title,body,baseRefName,headRefName,headRefOid,url,additions,deletions,changedFiles)` を実行して現在のブランチに関連付けられたPRの情報を取得し、同じく `PR_NUMBER`・`HEAD_BRANCH`・`PR_URL` を確定する。関連付けられたPRがない場合はユーザにPR番号の指定を促す。
    - `gh pr view "$PR_URL" --comments` で既存のレビューコメント・議論を取得し、既出の指摘を把握する。
    - gh が未認証・API エラーの場合はエラー内容をそのまま報告し、`gh auth login` を案内する。
 2. **worktree への展開**:
    - ユーザの作業ブランチ・working tree に触れないため、`gh pr checkout` は使わない。
-   - `MAIN_ROOT` は、手順 1 で取得した `$PR_JSON` の `url` から GitHub `owner/repository` を抽出し、現在の toplevel の `origin` URL が示すリポジトリと照合して確定する。親と一致すれば toplevel、公開リポジトリ `usaturn/maatlog` なら登録済み `public/` submodule（`.gitmodules` URL・submodule status・checkout の `origin` を検証）、それ以外は推測せず停止する。
+   - `MAIN_ROOT` は、手順 1 で取得した `$PR_JSON` の `url` から GitHub `owner/repository` を抽出し、ルート `AGENTS.md` の「リポジトリ境界」の表に照らして確定する。現在の toplevel の `origin` と一致すれば toplevel、`usaturn/resoloop` または `orange3134/resoloop` なら `$TOPLEVEL/external/resoloop`（自前の checkout であることと `origin`・`upstream` を検証し、満たさなければ `scripts/resoloop-fork.sh clone` を案内して停止する）、それ以外は推測せず停止する。PR の head を取得する remote `PR_REMOTE` も同時に決める。上流 `orange3134/resoloop` の PR は `upstream`、それ以外は `origin` から取得する。
 
      ```bash
      PR_URL=$(printf '%s' "$PR_JSON" | jq -r .url)
@@ -119,22 +120,24 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
      test -n "$origin_repository"
      if [[ "$pr_repository" == "$origin_repository" ]]; then
        MAIN_ROOT="$TOPLEVEL"
-     elif [[ "$pr_repository" == "usaturn/maatlog" ]]; then
-       test "$(git config -f "$TOPLEVEL/.gitmodules" \
-         --get submodule.public.url)" = \
-         "https://github.com/usaturn/maatlog.git"
-       git -C "$TOPLEVEL" submodule status -- public
-       test "$(git -C "$TOPLEVEL/public" remote get-url origin)" = \
-         "https://github.com/usaturn/maatlog.git"
-       MAIN_ROOT="$TOPLEVEL/public"
+       PR_REMOTE=origin
+     elif [[ "$pr_repository" == "usaturn/resoloop" || "$pr_repository" == "orange3134/resoloop" ]]; then
+       FORK_ROOT="$TOPLEVEL/external/resoloop"
+       if [[ "$(git -C "$FORK_ROOT" remote get-url origin 2>/dev/null | github_repository)" != "usaturn/resoloop" ]] ||
+         [[ "$(git -C "$FORK_ROOT" remote get-url upstream 2>/dev/null | github_repository)" != "orange3134/resoloop" ]]; then
+         printf '%s is not the resoloop fork checkout; run scripts/resoloop-fork.sh clone first\n' "$FORK_ROOT" >&2
+         exit 65
+       fi
+       MAIN_ROOT="$FORK_ROOT"
+       if [[ "$pr_repository" == "orange3134/resoloop" ]]; then PR_REMOTE=upstream; else PR_REMOTE=origin; fi
      else
        printf 'unsupported PR repository: %s\n' "$pr_repository" >&2
        exit 64
      fi
      ```
 
-   - `HELPER="$TOPLEVEL/.agents/skills/pr-review/scripts/pr_review_workspace.py"` を記録する。スキルは親リポジトリにのみ存在するため、`MAIN_ROOT` が `public/` を指す場合でも `$TOPLEVEL` から解決する。以降、メインリポジトリに対する Git コマンドには必ず `git -C "$MAIN_ROOT"` を使い、カレントディレクトリへ暗黙に作用させない。
-   - PR head は PR 番号ごとの専用 ref `PR_REF=refs/pr-review/<PR_NUMBER>` に固定する。`git -C "$MAIN_ROOT" fetch origin "+pull/<PR_NUMBER>/head:$PR_REF"` の後、`PR_HEAD=$(git -C "$MAIN_ROOT" rev-parse "$PR_REF")` で検証対象 SHA を確定する。共有の擬似参照 `FETCH_HEAD` は使わない。
+   - `HELPER="$TOPLEVEL/.agents/skills/pr-review/scripts/pr_review_workspace.py"` を記録する。スキルはこのリポジトリにのみ存在するため、`MAIN_ROOT` が `external/resoloop` を指す場合でも `$TOPLEVEL` から解決する。以降、メインリポジトリに対する Git コマンドには必ず `git -C "$MAIN_ROOT"` を使い、カレントディレクトリへ暗黙に作用させない。
+   - PR head は PR 番号ごとの専用 ref `PR_REF=refs/pr-review/<PR_NUMBER>` に固定する。`git -C "$MAIN_ROOT" fetch "$PR_REMOTE" "+pull/<PR_NUMBER>/head:$PR_REF"` の後、`PR_HEAD=$(git -C "$MAIN_ROOT" rev-parse "$PR_REF")` で検証対象 SHA を確定する。共有の擬似参照 `FETCH_HEAD` は使わない。
    - fetch 後に `git -C "$MAIN_ROOT" merge-base HEAD "$PR_REF"` が成功することを確認する。失敗した場合は `MAIN_ROOT` の選定が誤っている（無関係なリポジトリに PR のオブジェクトを取り込んだ状態）ため、保存を行わず停止して報告する。
    - dedicated ref fetch 後、次で GitHub の head と `PR_HEAD` の一致を確認する（HEAD consistency check 1/3）。不一致、空値、`gh` failure の場合は履歴を追記せず保存しない。
 
@@ -173,7 +176,7 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 
    - `$SHORT_HEAD` は固定した `$PR_HEAD` の 12 文字短縮 hash である。`git rev-parse` は `$WT` または `$MAIN_ROOT` など、当該 object を参照できるリポジトリ上で実行する。
    - `$PREVIOUS_REVIEW` が空なら Mode は `Initial`、helper が返した通常ファイル snapshot なら Mode は `Update` とする。ライブ `$DESTINATION` と他モデル files は読まない。
-   - 以降のファイル読解・テスト実行は `$WT` を対象に行う。ただし `./scripts/ci/verify.sh` は実行しない。レビュー成果物は `create` が返した `$DESTINATION`（メインリポジトリの `reviews/` 配下）に書き、`$WT` 内には書かない。
+   - 以降のファイル読解・テスト実行は `$WT` を対象に行う。ただし重い一括検証は再実行しない。レビュー成果物は `create` が返した `$DESTINATION`（`$MAIN_ROOT` 直下の `reviews/` 配下。resoloop の PR なら `external/resoloop/reviews/`）に書き、`$WT` 内には書かない。
 3. **既存レビューの読解（更新時）**:
    - `$PREVIOUS_REVIEW` が空でない場合だけ、その snapshot ファイルを読む。ライブ `$DESTINATION`、他モデルのレビュー本文、ディレクトリ一覧から自モデルを推測して読むことはしない。この読解はメインエージェントのみが行い、サブエージェントに委譲しない。既存 review 本文を委譲 prompt に含めない。
    - snapshot から active findings、Pending previous findings、既存の Review history、Resolved findings を把握する。旧形式で過去 HEAD が無い場合は推測せず、今回の Review history から開始し、旧形式 active 指摘の検出時 HEAD は `不明（旧形式）` とする。
@@ -198,7 +201,8 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 5. **コンテキスト読解（条件付き早期委譲）**:
    - 変更ファイル本体は、メインコンテキストで diff だけでなくファイル全体を読む。指摘の根拠となる精読をサブエージェント任せにしない。
    - 変更箇所の呼び出し元・呼び出し先の調査、依存関係ファイル（pyproject.toml / package.json / lock ファイル等）の確認、変更に対応する既存テストの探索は、[時間予算と委譲規約](references/time-budget.md)の「委譲」の起動条件をすべて満たす場合だけ、読み取り専用の補助委譲として最大 1 件を本体精読と並行して起動してよい。委譲先の調査範囲は `$WT` 上のコードと PR 差分のみとする。`reviews/` と既存 review 本文は委譲範囲・prompt から除外する。残り調査枠 10 分未満、停止手段なし、追加委譲・再委譲はしない。prompt の必須欄（対象・期限・制約・中間出力・終了）は具体値で埋める。
-6. **プロジェクト固有観点の取り込み**: CLAUDE.md とプロジェクト内の規約・設計ドキュメントがあれば読み、そのプロジェクトの重点観点（例: XSS 多層防御、並列・増分ビルド互換性）を優先順位のチェックリストに加える。メインリポジトリ側と `$WT` 側の `reviews/` にある他モデルのレビューは情報源にしない（サブエージェントに委譲する場合も調査範囲から除外する）。
+   - 委譲しない場合は、メインエージェントが自分で変更箇所の呼び出し元・呼び出し先を辿り、依存関係ファイルを確認し、変更に対応する既存テストを探す。
+6. **プロジェクト固有観点の取り込み**: `$WT` 上の `AGENTS.md`・`CLAUDE.md`（ワールドのプロジェクトを変更する PR では、そのプロジェクトの `AGENTS.md` も）と、規約・設計ドキュメントがあれば読み、そのプロジェクトの重点観点（例: 1 オブジェクト 1 メッシュ、resoloop の安全ルール、Python は uv で実行する）を優先順位のチェックリストに加える。メインリポジトリ側と `$WT` 側の `reviews/` にある他モデルのレビューは情報源にしない（サブエージェントに委譲する場合も調査範囲から除外する）。
 7. **候補洗い出し → 検証 → 報告**:
    - 優先順位に沿って候補指摘を洗い出し、検証プロトコルを通過したものだけを指摘フォーマットで報告する。
    - 調査期限・委譲期限を確認し、期限超過後は新規調査を止めて取得済み根拠で保存へ進む（[時間予算と委譲規約](references/time-budget.md)の「打ち切り」）。
@@ -247,7 +251,7 @@ GitHub 上の指定された Pull Request（PR）に対して、Codex の `/revi
 
 1. **精読**: 指摘に関わる実コードパスを最後まで読む（途中の早期 return・ガード・呼び出し規約を見落とさない）
 2. **反証試行**: 「この指摘が誤りだとしたらどこか」を明示的に検討する（既存のガード、テストによる固定、ドキュメント化された意図的トレードオフ等）。反証に成功したら報告しない
-3. **実行検証**: 挙動が不確かな場合、可能なら worktree 側で実行して確かめる（関連する pytest、REPL、最小再現スクリプト）。`./scripts/ci/verify.sh` は実行しない。テストコマンドが不明な場合は無理に実行しない。一時ホームが必要な場合は `env HOME="$tmpdir" ...` のワンショットだけを使い、永続シェルへ `export HOME=...` してはならない（後続の `gh` が別ホームを見て未認証になる）
+3. **実行検証**: 挙動が不確かな場合、可能なら worktree 側で実行して確かめる（関連する pytest、REPL、最小再現スクリプト）。重い一括検証は再実行しない（規約を参照）。テストコマンドが不明な場合は無理に実行しない。一時ホームが必要な場合は `env HOME="$tmpdir" ...` のワンショットだけを使い、永続シェルへ `export HOME=...` してはならない（後続の `gh` が別ホームを見て未認証になる）
 4. **期限確認**: phase 境界・呼び出し復帰時・委譲開始前・新規候補や実行検証の開始前に現在時刻を確認し、調査期限と委譲期限（絶対期限・実質無進捗 5 分）を再評価する。期限超過後は新規調査を増やさず保存へ進む
 
 反証試行のための追加委譲はしない。手順 5 で起動した 1 件の割当範囲内で得た報告は利用してよいが、確度ラベルの最終判定は、メインコンテキストが根拠（コードパス・実行結果）を直接確認した上で行う。サブエージェントの報告のみを根拠に【検証済み】を付けない。
@@ -401,11 +405,11 @@ Merge recommendation の判定基準:
 - 件数表と本文の active 指摘数が一致しているか
 - 全指摘に位置（`file:line`）・具体的な発生条件・確度ラベルがあるか
 - 各指摘に反証を試みたか
-- `./scripts/ci/verify.sh` を実行していないか。verify.sh 以外の検証は実行してよい
+- 重い一括検証（`bash .devcontainer/run-tests.bash` など）を再実行していないか。指摘の検証に必要な範囲の実行はしてよい
 - 「コメントしないこと」に該当する指摘が紛れていないか
 - メインリポジトリ側と `$WT` 側の `reviews/#<PR番号>-<変換後ブランチ名>/` にある他モデルのレビュー本文を、自分でもサブエージェント経由でも開いたり検索対象に含めたりしていないか
 - Merge recommendation が判定基準と整合しているか。重大度判定は active findings、確認不足判定は coverage と pending も参照する
-- `MAIN_ROOT` は PR URL の `owner/repository` と `origin` の照合で確定したか（親=toplevel、`usaturn/maatlog`=検証済み `public/`、その他は停止）。`merge-base HEAD "$PR_REF"` の成功を確認したか
+- `MAIN_ROOT` は PR URL の `owner/repository` を「リポジトリ境界」の表に照らして確定したか（このリポジトリ=toplevel、resoloop=検証済みの `external/resoloop`、その他は停止）。PR の head を `$PR_REMOTE` から取得したか。`merge-base HEAD "$PR_REF"` の成功を確認したか
 - `create` が返した `model_name`、`draft`、`destination`、`previous_review` を変更・再構築せず使用したか
 - 正確な `$MODEL_NAME` を `--model-name "$MODEL_NAME"` で渡し、filename から推測していないか（Codex はヘルパーが確定する）
 - `save` を `--state "$STATE_FILE"` だけで実行し、caller-selected path を渡していないか
diff --git a/.agents/skills/pr-review/references/time-budget.md b/.agents/skills/pr-review/references/time-budget.md
index 2cfc6d0..06232e0 100644
--- a/.agents/skills/pr-review/references/time-budget.md
+++ b/.agents/skills/pr-review/references/time-budget.md
@@ -154,6 +154,6 @@ Merge recommendation の判定順は次に固定する。
 | S17 | tool_use/result が同時記録、コマンド elapsed なし | ツール実時間は不明。0 秒やモデル時間 100% としない |
 | S18 | 単一モデル呼び出し中に期限超過し、復帰時は 48 分 | 復帰後に新規調査せず保存へ。48 分以上の実測を記録し予算未達 |
 | S19 | 停止後に遅れて補助結果が届く | 調査や保存を再開しない |
-| S20 | verify.sh または実装担当が生存したまま無進捗 | PR レビュー例外を適用しない。通常の監視規約に従う |
+| S20 | 一括検証（`bash .devcontainer/run-tests.bash` など）または実装担当が生存したまま無進捗 | PR レビュー例外を適用しない。通常の監視規約に従う |
 | S21 | 明示予算 20 分、途中でターンを跨ぐ | 開始 15 分で調査終了、20 分全体。起点をリセットしない |
 | S22 | JSONL の末尾未完、turn_duration 欠損、時刻逆転 | 解析限界を明示。推測で時刻や分類を補わない |
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/pr-review 2>&1 | tail -n 1
git grep -n -i -E 'maatlog|public/|submodule|verify\.sh|scripts/ci' -- .agents/skills/pr-review ':!*/tests/*'
```

Expected: `112 passed`。`git grep` は何も表示しない。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/pr-review/SKILL.md .agents/skills/pr-review/references/time-budget.md \
  .agents/skills/pr-review/tests/test_pr_review_skill_contract.py
git commit -m "feat(pr-review): resolve the work root from the repository boundary table

A PR of this repository is reviewed from the toplevel, a PR of usaturn/resoloop
or orange3134/resoloop from external/resoloop after checking its origin and
upstream, and anything else stops (spec 5.4). Upstream PR heads are fetched
from upstream. The verify.sh ban becomes a rule against rerunning bulk suites,
the main agent traces callers, dependencies and tests when it does not
delegate, and the tests pin the create lines, delegation limits and
allowed-tools.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 4: simplify-in-subagent のルーティングと例（仕様 8.2、持ち越し N-14）

ルーティング表を「このリポジトリ / resoloop の fork」の 2 行にし、それ以外の対象は止まると書く（D-22）。ルーティングの根拠を repository-ownership からルート `AGENTS.md` の「リポジトリ境界」に替え、fork の経路では `upstream` も確かめる。Examples は `/simplify-in-subagent` の名前にし、Devin 版にあった「ask the caller は質問ツールを要しない」の補足を戻す（N-14）。

**Files:**
- Modify: `.agents/skills/simplify-in-subagent/SKILL.md`
- Test: `.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py b/.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py
index 5cbe506..451d33a 100644
--- a/.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py
+++ b/.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py
@@ -42,3 +42,31 @@ def test_claude_code_reads_the_same_skill() -> None:
     link = REPO_ROOT / ".claude/skills/simplify-in-subagent"
     assert link.is_symlink()
     assert os.readlink(link) == "../../.agents/skills/simplify-in-subagent"
+
+
+def route_rows(content: str) -> list[str]:
+    preflight = content.split("## Repository preflight", 1)[1].split("## Workflow", 1)[0]
+    return [line for line in preflight.splitlines() if line.startswith("| ") and "---" not in line][1:]
+
+
+def test_routes_follow_the_repository_boundary_table() -> None:
+    # Spec 5.4: this repository and the resoloop fork are the only routes;
+    # anything else stops without guessing.
+    content = SKILL.read_text(encoding="utf-8")
+    rows = route_rows(content)
+    assert len(rows) == 2
+    assert "`usaturn/create-reso-world`" in rows[0]
+    assert "`usaturn/resoloop`" in rows[1] and "`orange3134/resoloop`" in rows[1]
+    assert "`external/resoloop`" in rows[1]
+    assert "repository boundary table in the root `AGENTS.md`" in content
+    assert "git remote get-url upstream" in content
+    assert "Any other target repository has no route" in content
+    assert "repository-ownership" not in content
+
+
+def test_examples_name_this_skill_and_need_no_question_tool() -> None:
+    content = SKILL.read_text(encoding="utf-8")
+    examples = content.split("## Examples", 1)[1]
+    assert examples.count("/simplify-in-subagent --ref=origin/main") == 2
+    assert "/simplify --ref" not in examples
+    assert "it does not require a question tool" in examples
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/simplify-in-subagent 2>&1 | tail -n 1
```

Expected: `2 failed, 4 passed`。ルーティング表の 1 行目が `usaturn/maatlog` の行であることと、Examples に `/simplify-in-subagent --ref=origin/main` が 1 つも無いこと（`assert 0 == 2`）で失敗する。

- [ ] **Step 3: SKILL.md を直す**

````diff
diff --git a/.agents/skills/simplify-in-subagent/SKILL.md b/.agents/skills/simplify-in-subagent/SKILL.md
index 988ab98..492801f 100644
--- a/.agents/skills/simplify-in-subagent/SKILL.md
+++ b/.agents/skills/simplify-in-subagent/SKILL.md
@@ -20,27 +20,30 @@ Only changed lines. Never whole-file refactors. Run every `git` command in own c
 
 ## Inputs
 
-- Required routing context: target repository and intended working root, resolved by the caller using `repository-ownership` before delegation. Pass these as task context, not new slash-command flags. Do not infer the target from the current cwd, the skill's location, or the presence of `src/`.
+- Required routing context: target repository and intended working root, resolved by the caller from the repository boundary table in the root `AGENTS.md` before delegation. Pass these as task context, not new slash-command flags. Do not infer the target from the current cwd, the skill's location, or the presence of `src/`.
 - Required: one of ref (default `HEAD`), `--staged`, or explicit file list, taken from the interpolated 対象指定 line. An empty or placeholder line means `HEAD`.
 - Optional: test command. Default: relevant existing tests.
 
 ## Repository preflight
 
-Before deriving files or reading diffs, confirm the routing context for every input mode: default `HEAD`, `--ref`, `--staged`, and explicit files. `repository-ownership` is the routing authority. If the target repository or intended working root cannot be established, stop and report the missing context.
+Before deriving files or reading diffs, confirm the routing context for every input mode: default `HEAD`, `--ref`, `--staged`, and explicit files. The repository boundary table in the root `AGENTS.md` is the routing authority; the table below restates it. If the target repository or intended working root cannot be established, stop and report the missing context.
 
-Run these read-only commands in your own cwd:
+Run these read-only commands in your own cwd (the last one only on the fork route):
 
 ```bash
 git rev-parse --show-toplevel
 git remote get-url origin
+git remote get-url upstream
 ```
 
-Compare the Git root with the intended working root using their resolved filesystem paths. Compare origin's GitHub owner/repository with the declared target. Standard GitHub HTTPS and SSH URLs, with or without a trailing `.git`, can identify the same repository; different hosts, owners, repositories, or unrecognized URL forms do not pass. Do not guess SSH aliases.
+Compare the Git root with the intended working root using their resolved filesystem paths. Compare origin's GitHub owner/repository, and on the fork route also upstream's, with the route below. Standard GitHub HTTPS and SSH URLs, with or without a trailing `.git`, can identify the same repository; different hosts, owners, repositories, or unrecognized URL forms do not pass. Do not guess SSH aliases.
 
-| Task | Target repository | Working root | Meaning of `origin/main` |
+| Route | Declared target | Working root and remotes | Meaning of `origin/main` |
 | --- | --- | --- | --- |
-| Application | `usaturn/maatlog` | `public/` or a worktree from the public repository | Public repository's remote-tracking ref |
-| Environment | `usaturn/maatlog-poc` | Parent checkout or a worktree from the parent repository | Parent repository's remote-tracking ref |
+| This repository | `usaturn/create-reso-world` | This repository's checkout or one of its worktrees; origin is `usaturn/create-reso-world` | This repository's remote-tracking ref |
+| ResoLoop fork | `usaturn/resoloop` or `orange3134/resoloop` | `external/resoloop` under this repository's root, or a worktree of that checkout; origin is `usaturn/resoloop` and upstream is `orange3134/resoloop` | The fork's remote-tracking ref, which mirrors `upstream/main` |
+
+Any other target repository has no route: stop before deriving files and report the declared target.
 
 For `--ref=origin/main`, only after the route matches, resolve the ref in that same cwd:
 
@@ -85,6 +88,6 @@ If a command fails, the root or origin differs, or the selected ref cannot be re
 
 ## Examples
 
-- Application: caller declares target `usaturn/maatlog` and a public worktree as the working root for `/simplify --ref=origin/main`. In that worktree, verify root/origin, resolve that repository's `origin/main`, then simplify `src/foo.py` lines 10–18 from the diff. Only those changed lines may be edited; run relevant tests and report the route and changes.
-- Environment: caller declares target `usaturn/maatlog-poc` and a parent worktree for `/simplify --ref=origin/main`. Verify root/origin there before using that repository's `origin/main` for changed lines in `tools/devenv/...`.
-- Wrong route: target is `usaturn/maatlog`, but the current cwd is the parent checkout while the request names `src/foo.py` and `--ref=origin/main`. Stop at preflight, report the mismatch, and ask the caller to rerun in the intended public worktree. Do not read the parent's diff or invoke fallback.
+- This repository: caller declares target `usaturn/create-reso-world` and a worktree of this repository as the working root for `/simplify-in-subagent --ref=origin/main`. In that worktree, verify root/origin, resolve that repository's `origin/main`, then simplify `scripts/check-layout.sh` lines 10–18 from the diff. Only those changed lines may be edited; run relevant tests and report the route and changes.
+- ResoLoop fork: caller declares target `orange3134/resoloop` (an upstream PR) and `external/resoloop` as the working root for `/simplify-in-subagent --ref=origin/main`. Verify root, origin and upstream there before using the fork's `origin/main` for changed lines in `src/RLoop.Cli/...`.
+- Wrong route: target is `usaturn/resoloop`, but the current cwd is this repository's root while the request names `src/RLoop.Cli/Program.cs` and `--ref=origin/main`. Stop at preflight, report the mismatch, and ask the caller to rerun in `external/resoloop`. Do not read this repository's diff or invoke fallback. Here, "ask the caller" means return this instruction in the result report; it does not require a question tool.
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/simplify-in-subagent 2>&1 | tail -n 1
```

Expected: `6 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/simplify-in-subagent/SKILL.md .agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py
git commit -m "feat(simplify-in-subagent): route by the repository boundary table

The routes are this repository and the resoloop fork (origin and upstream are
both checked), taken from the table in the root AGENTS.md; any other target
stops. The examples use the /simplify-in-subagent name and say again that
asking the caller does not need a question tool.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 5: repo-cleanup-after-merge を書き直す（仕様 8.2、持ち越し N-14）

対象リポジトリの確定を「リポジトリ境界」の 3 行にし、submodule の段落と「ローカル main を作らない」規約を外す（D-26）。gitignore 対象の削除規則を、実測した `git worktree remove` の挙動に合わせて確定する（D-25）。手順 6 の `python3` を `uv run --no-project python` に置き換え、`allowed-tools` に `cp`・`uv run`・fork の `sync` を足す（N-14）。存在しない `version-export` スキルへの参照を消し、evals を新しい規則に合わせる。

repo-cleanup の contract テストは review-fix-planning のテストファイルに間借りしていたので、スキル自身の `tests/` へ移して書き直す。

**Files:**
- Create: `.agents/skills/repo-cleanup-after-merge/tests/test_repo_cleanup_after_merge_contract.py`
- Modify: `.agents/skills/repo-cleanup-after-merge/SKILL.md`、`.agents/skills/repo-cleanup-after-merge/evals/evals.json`、`.agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json`（q10）
- Test: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`（repo-cleanup のテストを外す）

- [ ] **Step 1: 失敗するテストを書く**

`.agents/skills/repo-cleanup-after-merge/tests/test_repo_cleanup_after_merge_contract.py` を次の内容で作る。

````python
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/repo-cleanup-after-merge"
SKILL = SKILL_DIR / "SKILL.md"
EVALS = SKILL_DIR / "evals/evals.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter() -> dict[str, object]:
    return yaml.safe_load(read(SKILL).split("---", 2)[1])


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/repo-cleanup-after-merge"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/repo-cleanup-after-merge"


def test_keeps_gh_failure_stop_and_user_confirmation() -> None:
    content = read(SKILL)
    assert "が非0終了した場合、PR の状態は不明である" in content
    assert "AskUserQuestion" in content


def test_allowed_tools_cover_the_commands_the_steps_run() -> None:
    # Claude Code pre-approves only what this line lists.
    tools = frontmatter()["allowed-tools"]
    assert isinstance(tools, str)
    for entry in (
        "AskUserQuestion",
        "Bash(git *)",
        "Bash(gh *)",
        "Bash(diff *)",
        "Bash(cp *)",
        "Bash(rm *)",
        "Bash(uv run --no-project python -c *)",
        "Bash(bash scripts/resoloop-fork.sh sync)",
    ):
        assert entry in tools, entry
    content = read(SKILL)
    assert "python3" not in content
    assert "uv run --no-project python -c" in content


def test_resoloop_prs_are_cleaned_up_in_the_fork_checkout() -> None:
    body = read(SKILL).split("---", 2)[2]
    assert "リポジトリ境界" in body
    assert "git -C external/resoloop" in body
    assert "--repo usaturn/resoloop" in body
    assert "--repo orange3134/resoloop" in body
    assert "scripts/resoloop-fork.sh clone" in body
    assert "```bash\nbash scripts/resoloop-fork.sh sync\n```" in body
    assert "submodule" not in body


def test_local_main_follows_origin_main_by_fast_forward() -> None:
    content = read(SKILL)
    assert "git switch main" in content
    assert "git merge --ff-only origin/main" in content
    assert "`main` branch を作成しない" not in content
    assert "`main` branch は作成しない" not in content


def test_ignored_files_in_a_worktree_are_checked_before_removal() -> None:
    # git worktree remove deletes ignored files without asking.
    content = read(SKILL)
    assert "git -C <worktree の絶対パス> status --short --ignored" in content
    assert "`git worktree remove` は ignore 対象のファイルを確認せずに消す" in content
    for cache in (".venv/", ".pytest_cache/", "__pycache__/"):
        assert cache in content, cache
    assert "gitignore 対象のファイルは、再生成できるキャッシュを除き" in content
    assert "--force" not in content.split("### 5.", 1)[1].split("### 6.", 1)[0].replace("`--force` は付けない", "")


def test_related_skills_exist() -> None:
    related = read(SKILL).split("## 関連スキル", 1)[1]
    names = re.findall(r"^- `([a-z0-9-]+)`", related, re.M)
    assert names
    for name in names:
        assert (REPO_ROOT / ".agents/skills" / name / "SKILL.md").is_file(), name


def test_evals_cover_the_rules_of_this_repository() -> None:
    names = {item["name"] for item in json.loads(read(EVALS))["evals"]}
    assert {
        "remove-only-clean-worktree",
        "fast-forward-local-main",
        "hold-ignored-files-in-worktree",
        "sync-fork-after-upstream-merge",
    } <= names
    assert "stay-detached-without-local-main" not in names
    assert "force-remove-only-clean-worktree" not in names
````

review-fix-planning のテストファイルから repo-cleanup の分を外す。

```diff
diff --git a/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py b/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
index 573fefa..aee0dfa 100644
--- a/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
+++ b/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
@@ -7,7 +7,6 @@ from pathlib import Path
 REPO_ROOT = Path(__file__).resolve().parents[4]
 AGENTS_SKILL = REPO_ROOT / ".agents/skills/review-fix-planning/SKILL.md"
 AGENTS_HELPER = REPO_ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
-REPO_CLEANUP_SKILLS = (REPO_ROOT / ".agents/skills/repo-cleanup-after-merge/SKILL.md",)
 
 
 def read(path: Path) -> str:
@@ -77,13 +76,12 @@ def test_agents_skill_lands_on_existing_pr_after_related_tests() -> None:
     assert_japanese_landing_contract(read(AGENTS_SKILL))
 
 
-def test_helper_has_one_real_copy_shared_through_the_skill_symlinks() -> None:
+def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
     assert AGENTS_HELPER.is_file() and not AGENTS_HELPER.is_symlink()
     assert AGENTS_HELPER.stat().st_size > 0
-    for name in ("review-fix-planning", "repo-cleanup-after-merge"):
-        link = REPO_ROOT / ".claude/skills" / name
-        assert link.is_symlink(), link
-        assert os.readlink(link) == f"../../.agents/skills/{name}"
+    link = REPO_ROOT / ".claude/skills/review-fix-planning"
+    assert link.is_symlink(), link
+    assert os.readlink(link) == "../../.agents/skills/review-fix-planning"
 
 
 def test_pr_comment_lists_skipped_findings_without_spec_dependency() -> None:
@@ -120,15 +118,8 @@ def test_skill_descriptions_do_not_advertise_pr_posting() -> None:
     assert "Before finishing, post review status" not in description
 
 
-def test_merged_skills_keep_claude_code_allowed_tools() -> None:
-    for path in (AGENTS_SKILL, *REPO_CLEANUP_SKILLS):
-        assert "allowed-tools:" in frontmatter_description(read(path)), path
-
-
-def test_repo_cleanup_keeps_gh_failure_stop_and_user_confirmation() -> None:
-    content = read(REPO_CLEANUP_SKILLS[0])
-    assert "が非0終了した場合、PR の状態は不明である" in content
-    assert "AskUserQuestion" in content
+def test_merged_skill_keeps_claude_code_allowed_tools() -> None:
+    assert "allowed-tools:" in frontmatter_description(read(AGENTS_SKILL))
 
 
 def test_review_fix_examples_distinguish_public_and_parent_prs() -> None:
@@ -177,13 +168,3 @@ def test_spec_location_stays_in_parent_docs_draft() -> None:
         content = read(path)
         assert "$MAIN_ROOT/docs_draft" not in content, path
         assert "$TOPLEVEL/docs_draft/superpowers/" in content, path
-
-
-def test_repo_cleanup_selects_public_root_for_public_prs() -> None:
-    """Issue #377 F-3: cleanup of a merged usaturn/maatlog PR runs inside the
-    public/ checkout with gh calls pinned to the public repository."""
-    for path in REPO_CLEANUP_SKILLS:
-        content = read(path)
-        assert re.search(r"usaturn/maatlog(?!-)", content), path
-        assert "git -C public" in content, path
-        assert "--repo usaturn/maatlog" in content, path
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/repo-cleanup-after-merge .agents/skills/review-fix-planning 2>&1 | tail -n 1
```

Expected: `6 failed, 22 passed`。失敗するのは新しいファイルの `test_allowed_tools_cover_the_commands_the_steps_run`（`Bash(cp *)` が無い）、`test_resoloop_prs_are_cleaned_up_in_the_fork_checkout`、`test_local_main_follows_origin_main_by_fast_forward`、`test_ignored_files_in_a_worktree_are_checked_before_removal`、`test_related_skills_exist`（`version-export`）、`test_evals_cover_the_rules_of_this_repository`。

- [ ] **Step 3: SKILL.md と evals を直す**

````diff
diff --git a/.agents/skills/repo-cleanup-after-merge/SKILL.md b/.agents/skills/repo-cleanup-after-merge/SKILL.md
index 35cd0f7..fffde15 100644
--- a/.agents/skills/repo-cleanup-after-merge/SKILL.md
+++ b/.agents/skills/repo-cleanup-after-merge/SKILL.md
@@ -1,7 +1,7 @@
 ---
 name: repo-cleanup-after-merge
 description: Use when ユーザーが、PR がマージされた後のローカルリポジトリの片付けを依頼する場合。マージ済み branch の削除、使い終わった worktree の整理、レビュー用の使い捨て worktree の残骸の掃除、作業ツリーの origin/main への追従が対象。未マージの作業のリベース、コンフリクト解消、リリース作業には使用しない。例:「PR が全て Merge されたことを確認して branch, worktree を整理してローカルを更新して」「マージ済みのブランチを消して」「worktree を掃除して」「origin/main に追従して」「リポジトリを整理して」
-allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(git *), Bash(gh *), Bash(ls *), Bash(diff *), Bash(cmp *), Bash(find *), Bash(rm *)
+allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(git *), Bash(gh *), Bash(ls *), Bash(diff *), Bash(cmp *), Bash(find *), Bash(cp *), Bash(rm *), Bash(uv run --no-project python -c *), Bash(bash scripts/resoloop-fork.sh sync)
 ---
 
 # マージ後のリポジトリ整理
@@ -19,11 +19,13 @@ git の操作はほぼ全て取り消せる。取り消せないのは次の 2 
 
 ## 対象リポジトリの確定
 
-整理対象の PR が属するリポジトリで root を決める。`usaturn/maatlog`（公開アプリケーション）の PR なら `public/` submodule の checkout が root であり、Git コマンドは `git -C public ...`、`gh` 呼び出しには `--repo usaturn/maatlog` を付けて実行する。親 `usaturn/maatlog-poc` の PR なら親の toplevel が root である。両リポジトリにまたがる整理は、リポジトリごとにこの手順を回す。
+整理対象の PR が属するリポジトリで root を決める。対応はルート `AGENTS.md` の「リポジトリ境界」の表に従う。
 
-公開経路では次が変わる。手順 7 の `git submodule update --init public` は親側だけの操作なので実行しない。手順 6 の `session.json` の `destination` は対象リポジトリ側の `reviews/` を指す（公開 PR なら `public/reviews/`）。手順 1 の `gh pr list` は `--repo usaturn/maatlog` で公開側を見る。
+- `usaturn/create-reso-world`（このリポジトリ）の PR: リポジトリのルート（`git rev-parse --show-toplevel`）が root である
+- `usaturn/resoloop` または `orange3134/resoloop` の PR: fork の checkout `external/resoloop`（リポジトリのルート基準）が root である。Git コマンドは `git -C external/resoloop ...`、`gh` 呼び出しには PR が属するリポジトリに合わせて `--repo usaturn/resoloop` か `--repo orange3134/resoloop` を付けて実行する。checkout が無い、または `origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` でない場合は、`scripts/resoloop-fork.sh clone` を案内して停止する
+- それ以外: 推測せず停止する
 
-公開 checkout で手順 7 を実行すると、親には `modified: public (new commits)` が残る。これは次回 checkpoint までの正常な状態であり、`git submodule update` で巻き戻したり gitlink を stage して「直さない」。
+両方にまたがる整理は、リポジトリごとにこの手順を回す。fork の経路では、手順 6 の `session.json` の `destination` は fork 側の `reviews/`（`external/resoloop/reviews/`）を指す。
 
 ## ワークフロー
 
@@ -72,9 +74,12 @@ git log --oneline origin/main..<branch>
 
 ```bash
 git -C <worktree の絶対パス> status --short
+git -C <worktree の絶対パス> status --short --ignored
 ```
 
-`-C` には絶対パスを渡す。worktree 隔離セッションでは相対パスが拒否されることがある。出力がある worktree は **削除しない**。ユーザーへ報告して判断を仰ぐ。
+`-C` には絶対パスを渡す。worktree 隔離セッションでは相対パスが拒否されることがある。1 つ目に出力がある worktree は **削除しない**。ユーザーへ報告して判断を仰ぐ。
+
+`git worktree remove` は ignore 対象のファイルを確認せずに消す。2 つ目の出力の `!!` の行（ignore 対象）も確かめる。再生成できるキャッシュ（`.venv/`、`.uv-cache/`、`.pytest_cache/`、`.ruff_cache/`、`__pycache__/`、`node_modules/`）だけなら、worktree と一緒に消えてよい。それ以外（`reviews/`、`docs_draft/`、`tmp/`、`external/`、`private/`、`.superpowers/`、各プロジェクトの `.resoloop/` など）が 1 つでもある worktree は **削除しない**。一覧をユーザーへ報告し、正本への退避か削除の確認を得るまで残す（ゲート A と同じ扱い）。
 
 #### 毎回ここで止まるなら、直すのは片付け側ではなく生成側である
 
@@ -88,21 +93,15 @@ untracked ファイルは正本と照合する述語を持たないため、ゲ
 
 ### 5. worktree を削除する
 
-手順 1 で対象外にした worktree（オープン PR の `headRefOid` と HEAD が一致するもの、`/tmp/pr-review-*` で親 `session.json` の `head_branch` がオープン PR と一致するもの）は削除しない。
-
-submodule（本リポジトリの `public`）を含む worktree では `git worktree remove` が次で失敗する。
-
-```
-fatal: working trees containing submodules cannot be moved or removed
-```
-
-手順 4 で clean を確認済みの worktree に限り `--force` を付ける。確認していない worktree に `--force` を付けない。
+手順 1 で対象外にした worktree（オープン PR の `headRefOid` と HEAD が一致するもの、`/tmp/pr-review-*` で親 `session.json` の `head_branch` がオープン PR と一致するもの）は削除しない。削除するのは、手順 4 で clean を確認し、ignore 対象が再生成できるキャッシュだけだった worktree に限る。
 
 ```bash
-git worktree remove --force <path>
+git worktree remove <path>
 git worktree prune
 ```
 
+`--force` は付けない。`git worktree remove` が拒否した場合（未追跡のファイルがある、lock されているなど）は、理由をユーザーへ報告して止まる。
+
 worktree 本体の削除と、手順 6 の残骸削除は **別の判断**である。worktree 本体は追跡済みの内容であり、マージ済み・clean を確認していれば削除してよい。手順 6 で保留が発生しても、worktree 本体の削除まで止める必要はない。
 
 ### 6. ゲート A: 残骸ディレクトリは照合してから消す
@@ -112,7 +111,7 @@ worktree 本体の削除と、手順 6 の残骸削除は **別の判断**であ
 正本パスは残骸ディレクトリの `session.json` の `destination` から取る。branch 名の変換で推測しない。
 
 ```bash
-python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["destination"])' <残骸ディレクトリ>/session.json
+uv run --no-project python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["destination"])' <残骸ディレクトリ>/session.json
 ```
 
 `session.json` が無い、`destination` が読めない、またはその親がリポジトリの `reviews/` 配下に無い場合は削除せず停止する。
@@ -144,15 +143,15 @@ cp <残骸ディレクトリ>/review-backup/<model>.md <正本ディレクトリ
 メイン作業ツリーの `git status --short` が空であることを確認する。空でなければ checkout も branch 削除もせず、ユーザーへ報告する。
 
 ```bash
-git checkout --detach origin/main
-git submodule update --init public
+git switch main
+git merge --ff-only origin/main
 ```
 
-ローカル `main` branch は作成しない（プロジェクト規約）。
+ローカル `main` が無ければ、`git switch main` が `origin/main` を追跡する branch として作る。`main` を別の worktree が checkout していて `git switch` が拒否した場合は、代わりに `git checkout --detach origin/main` で更新する。`--ff-only` が失敗した場合（ローカル `main` に `origin/main` に無いコミットがある）は、merge や reset をせずユーザーへ報告する。
 
 ### 8. マージ済みローカル branch を削除する
 
-手順 7 の detach のあとで実行する。メイン作業ツリーが feature を checkout したままだと `git branch -d` は `used by worktree` / `checked out` で失敗する。
+手順 7 のあとで実行する。メイン作業ツリーが feature を checkout したままだと `git branch -d` は `used by worktree` / `checked out` で失敗する。
 
 ```bash
 git branch -d <branch>
@@ -162,7 +161,7 @@ git branch -d <branch>
 
 `-d` が拒否した場合、理由で分岐する。拒否を未マージと同一視しない。
 
-- `used by worktree` または `checked out`: 未マージではない。手順 7 の detach が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、この branch は削除しない
+- `used by worktree` または `checked out`: 未マージではない。手順 7 が済んでいなければ手順 7 に戻る。他 worktree が掴んでいるならその worktree を残し、この branch は削除しない
 - `not fully merged`: 未マージである。手順 3 の判定が誤っている。削除しない
 
 detached HEAD では次の warning が出るが、**削除が成功していれば正常**である。upstream にマージ済みであることは確認できており、拒否ではない。
@@ -189,7 +188,17 @@ git push origin --delete <branch>
 git fetch --prune
 ```
 
-### 10. 最終状態を報告する
+### 10. resoloop の上流に追従する（fork の経路だけ）
+
+上流 `orange3134/resoloop` で PR がマージされたら、fork の `main` を上流へ追従させる。リポジトリのルートで実行する。
+
+```bash
+bash scripts/resoloop-fork.sh sync
+```
+
+`sync` は fork（`usaturn/resoloop`）の `main` へ push するので、ゲート B と同じくユーザー確認を得てから実行する。fork の `main` に上流に無いコミットがある場合や、`external/resoloop` の `main` に未コミットの変更がある場合、スクリプトは何も push せずに止まる。その出力をそのまま報告し、手で push や reset をしない。詳しい流れは `docs/resoloop-fork-workflow.md` にある。
+
+### 11. 最終状態を報告する
 
 ```bash
 git status
@@ -208,8 +217,9 @@ git branch -a
 - `Files ... differ` や `diff` の失敗を無視して「固有ファイルが無いから消してよい」としている
 - リモート branch を削除してから「不要なら戻せます」と報告しようとしている
 - 「時間が無い」「手早く」と言われたので確認を飛ばそうとしている
+- `git worktree remove` の前に `status --short --ignored` を見ていない
 
-**いずれかに該当したら、削除を中止して手順 6 または 9 に戻る。**
+**いずれかに該当したら、削除を中止して手順 4・6・9 のいずれかに戻る。**
 
 ## 言い訳と現実
 
@@ -219,7 +229,7 @@ git branch -a
 | 「ディレクトリ名が stale なので消してよい」 | 名前は中身を保証しない。照合していないなら未保存データの有無を知らないだけである |
 | 「中を見たら軽微なメモだった」 | 軽微だと判断したのではなく、正本と照合していないだけである。照合は `diff -r` 1 回で済む |
 | 「内容差分があっても固有ファイルが無ければ失うものはない」 | 同名の未保存稿は `Files ... differ` になる。`previous-review.md` だけをコピーして消すと新しい原稿が消える |
-| 「worktree は clean だったのでデータ損失はない」 | `git status` は gitignore 対象ファイルも、worktree の外にある残骸も見ない |
+| 「worktree は clean だったのでデータ損失はない」 | `git status` は gitignore 対象ファイルも、worktree の外にある残骸も見ない。`git worktree remove` は worktree 内の gitignore 対象ファイルを確認せずに消す |
 | 「消した後で問題があれば言ってもらえばいい」 | `rm -rf` に取り消しは無い。削除の前だけが確認である |
 | 「マージ済み branch の削除は cleanup の一環」 | ローカルはそうである。リモートは他人が見る共有物であり、外向きの操作である |
 | 「手早くと言われた」 | 照合は数秒で終わる。失ったレビューの再生成はそれより桁違いに高い |
@@ -228,15 +238,13 @@ git branch -a
 
 ## ガードレール
 
-- ローカル `main` branch を作成しない。
 - `git branch -D` でマージ判定を握り潰さない。
-- clean を確認していない worktree に `--force` を付けない。
-- ユーザー確認なしに `git push`（`--delete` を含む）を実行しない。
+- `git worktree remove` に `--force` を付けない。
+- ユーザー確認なしに `git push`（`--delete` を含む）や `scripts/resoloop-fork.sh sync` を実行しない。
 - Open PR が残っている branch と worktree を削除しない。detached な pr-review worktree も含む。
-- `reviews/` や `docs_draft/` など gitignore 対象ディレクトリの内容を、照合せずに削除しない。
+- gitignore 対象のファイルは、再生成できるキャッシュを除き、正本と照合するかユーザーの確認を得るまで削除しない（`reviews/`、`docs_draft/`、`tmp/`、`external/` など。worktree ごと消す場合も同じ）。
 - コンフリクト解消、rebase、リリース作業は行わない。
 
 ## 関連スキル
 
 - `pr-review` — `/tmp/pr-review-*/` の使い捨て worktree と `review-backup/` を作る側。手順 6 の残骸はこのスキルの生成物である
-- `version-export` — リリース手順。一時生成物を worktree の外（scratchpad）へ出す原則を共有する
diff --git a/.agents/skills/repo-cleanup-after-merge/evals/evals.json b/.agents/skills/repo-cleanup-after-merge/evals/evals.json
index a5de85b..dc3ca48 100644
--- a/.agents/skills/repo-cleanup-after-merge/evals/evals.json
+++ b/.agents/skills/repo-cleanup-after-merge/evals/evals.json
@@ -40,13 +40,13 @@
     },
     {
       "id": 4,
-      "name": "force-remove-only-clean-worktree",
-      "prompt": "PR が全て Merge されたことを確認して branch と worktree を整理し、ローカルを更新して。worktree は 2 つあり、どちらも public submodule を含む。片方には未コミットの変更がある。",
-      "expected_output": "clean な worktree だけを --force で削除し、dirty な worktree は残して報告した結果。",
+      "name": "remove-only-clean-worktree",
+      "prompt": "PR が全て Merge されたことを確認して branch と worktree を整理し、ローカルを更新して。マージ済みの worktree は 2 つあり、片方には未コミットの変更がある。",
+      "expected_output": "clean な worktree だけを --force なしで削除し、dirty な worktree は残して報告した結果。",
       "files": [],
       "expectations": [
-        "The result runs git -C <worktree> status --short for every worktree before removing any.",
-        "The result uses git worktree remove --force only on the clean worktree, after the submodule error.",
+        "The result runs git -C <worktree> status --short and status --short --ignored for every worktree before removing any.",
+        "The result removes the clean worktree with git worktree remove and never passes --force.",
         "The result does not remove the worktree that has uncommitted changes and reports it to the user."
       ]
     },
@@ -64,14 +64,14 @@
     },
     {
       "id": 6,
-      "name": "stay-detached-without-local-main",
-      "prompt": "PR が全て Merge されたことを確認して branch と worktree を整理し、ローカルを更新して。作業ツリーは古い origin/main で detached HEAD になっている。",
-      "expected_output": "detached HEAD のまま最新の origin/main へ更新し、submodule を同期した結果。",
+      "name": "fast-forward-local-main",
+      "prompt": "PR が全て Merge されたことを確認して branch と worktree を整理し、ローカルを更新して。メイン作業ツリーはマージ済みの feature branch を checkout しており、ローカル main は origin/main より古い。",
+      "expected_output": "メイン作業ツリーを main に切り替えて origin/main へ fast-forward し、その後マージ済みの feature branch を削除した結果。",
       "files": [],
       "expectations": [
-        "The result runs git checkout --detach origin/main.",
-        "The result does not create a local main branch (no git switch -c main, no git checkout -b main).",
-        "The result runs git submodule update --init public."
+        "The result runs git switch main and git merge --ff-only origin/main after git fetch --all --prune.",
+        "The result does not use git reset --hard or a non-fast-forward merge to update main.",
+        "The result deletes the merged feature branch with git branch -d only after switching away from it."
       ]
     },
     {
@@ -98,6 +98,30 @@
         "The result does not git worktree remove the detached /tmp/pr-review-* worktree whose HEAD matches the open PR headRefOid.",
         "The result does not rm the parent leftover directory of that worktree."
       ]
+    },
+    {
+      "id": 9,
+      "name": "hold-ignored-files-in-worktree",
+      "prompt": "PR が全て Merge されたことを確認して branch と worktree を整理し、ローカルを更新して。マージ済みの worktree .worktrees/feat-a は git status --short では clean だが、ignore 対象の docs_draft/notes.md と .venv/ がある。",
+      "expected_output": "status --short --ignored で docs_draft/notes.md を見つけ、その worktree を削除せずに報告し、退避か削除の確認を求めた結果。",
+      "files": [],
+      "expectations": [
+        "The result runs git -C <worktree> status --short --ignored before git worktree remove.",
+        "The result does not remove .worktrees/feat-a while docs_draft/notes.md is unresolved, and reports that file to the user.",
+        "The result treats .venv/ as a regenerable cache that alone would not block the removal."
+      ]
+    },
+    {
+      "id": 10,
+      "name": "sync-fork-after-upstream-merge",
+      "prompt": "orange3134/resoloop に出した PR がマージされた。external/resoloop の branch と worktree を整理して、fork の main も上流に追従させて。",
+      "expected_output": "external/resoloop を root に --repo orange3134/resoloop で PR の状態を確かめて整理し、scripts/resoloop-fork.sh sync はユーザー確認を得てから実行した結果。",
+      "files": [],
+      "expectations": [
+        "The result runs git commands with git -C external/resoloop and gh commands with --repo orange3134/resoloop.",
+        "The result checks that external/resoloop has origin usaturn/resoloop and upstream orange3134/resoloop before deleting anything.",
+        "The result asks for confirmation before running bash scripts/resoloop-fork.sh sync, because it pushes to the fork."
+      ]
     }
   ]
 }
diff --git a/.agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json b/.agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json
index 4d54ee9..d9a9b37 100644
--- a/.agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json
+++ b/.agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json
@@ -66,10 +66,10 @@
     },
     {
       "id": "q10",
-      "query": "バージョンを 0.1.0 に上げて公開リポジトリに反映してリリースして",
+      "query": "ResoLoop のロックファイルの版を上げて、fork をビルドし直して導入して",
       "should_trigger": false,
       "expected_terms": [],
-      "notes": "Negative: version-export スキルの領域"
+      "notes": "Negative: ResoLoop の版の更新（scripts/resoloop-fork.sh の領域）"
     },
     {
       "id": "q11",
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/repo-cleanup-after-merge .agents/skills/review-fix-planning 2>&1 | tail -n 1
# D-25 の前提（git worktree remove が ignore 対象を確認なしに消す）を一時リポジトリで確かめる
t="$(mktemp -d)" && git init -q "$t/main" && git -C "$t/main" commit -q --allow-empty -m init \
  && printf 'reviews/\n' > "$t/main/.gitignore" && git -C "$t/main" add .gitignore && git -C "$t/main" commit -qm ig \
  && git -C "$t/main" worktree add -q "$t/wt" && mkdir "$t/wt/reviews" && echo x > "$t/wt/reviews/a.md" \
  && git -C "$t/wt" status --short --ignored && git -C "$t/main" worktree remove "$t/wt" && ls "$t/wt" 2>&1 | tail -n 1; rm -rf "$t"
```

Expected: `28 passed`。続いて `!! reviews/` を表示し、`worktree remove` が成功して `ls: cannot access '.../wt': No such file or directory` を表示する（ignore 対象の `reviews/a.md` ごと消えた）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/repo-cleanup-after-merge/tests/test_repo_cleanup_after_merge_contract.py \
  .agents/skills/repo-cleanup-after-merge/SKILL.md .agents/skills/repo-cleanup-after-merge/evals/evals.json \
  .agents/skills/repo-cleanup-after-merge/evals/trigger_queries.json \
  .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
git commit -m "feat(repo-cleanup-after-merge): clean up this repository and the resoloop fork safely

The root is chosen by the repository boundary table; the submodule paragraphs
and the no-local-main rule are gone, and main is fast-forwarded to origin/main.
Worktrees are checked with status --ignored before removal, because
git worktree remove deletes ignored files without asking; only regenerable
caches may go with them, and --force is never used. The fork follows upstream
through scripts/resoloop-fork.sh sync after the user confirms. python3 becomes
uv run, allowed-tools gain cp, uv run and the sync, and the tests move to the
skill's own directory.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 6: review-fix-planning の反映の条件と Spec の置き場（仕様 8.2）

`public/reviews/` の分岐を `external/resoloop/reviews/` に替え、`MAIN_ROOT` を「リポジトリ境界」の規則で解決する（D-22）。実装後の反映の条件を変更の種類ごとに決め（D-24）、Spec の置き場を `$TOPLEVEL/docs/superpowers/specs/` にする。`allowed-tools` を合わせ、例と合理化・Red flags の行から移行元の verifier と PR 番号を外す。ヘルパーのテストのサンプルのリポジトリ名も、このリポジトリと fork・上流に替える。

**Files:**
- Modify: `.agents/skills/review-fix-planning/SKILL.md`、`.agents/skills/review-fix-planning/evals/evals.json`（id 5）
- Test: `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py`、`.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py b/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
index aee0dfa..dfd07d4 100644
--- a/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
+++ b/.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
@@ -1,12 +1,15 @@
 from __future__ import annotations
 
+import json
 import os
-import re
 from pathlib import Path
 
+import yaml
+
 REPO_ROOT = Path(__file__).resolve().parents[4]
 AGENTS_SKILL = REPO_ROOT / ".agents/skills/review-fix-planning/SKILL.md"
 AGENTS_HELPER = REPO_ROOT / ".agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
+EVALS = REPO_ROOT / ".agents/skills/review-fix-planning/evals/evals.json"
 
 
 def read(path: Path) -> str:
@@ -26,7 +29,17 @@ def assert_shared_landing_contract(content: str) -> None:
     lowered = content.lower()
     assert "commit" in lowered
     assert "push" in lowered
-    assert "./scripts/ci/verify.sh full" in content
+    # The gate depends on what changed: environment, skills, a world project, the fork.
+    landing = content.split("## 実装後", 1)[1].split("## 作業終了前の PR 投稿", 1)[0]
+    gate = landing.split("2. **変更の種類に応じた検証**", 1)[1].split("\n3. ", 1)[0]
+    for check in (
+        "`bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`",
+        "`uv run pytest tests/skills .agents/skills`",
+        "そのプロジェクトのディレクトリで `uv run pytest`",
+        "変更したプロジェクトに関連する `dotnet test`",
+    ):
+        assert check in gate, check
+    assert "scripts/resoloop-fork.sh test" in landing
     assert "finishing-a-development-branch" in content
     assert "upsert_pr_comment.py" in content
     assert "<!-- review-fix-planning:agent:" in content
@@ -85,17 +98,17 @@ def test_helper_has_one_real_copy_shared_through_the_skill_symlink() -> None:
 
 
 def test_pr_comment_lists_skipped_findings_without_spec_dependency() -> None:
-    """Issue #235 A: no dangling reference to the gitignored Spec."""
+    """The comment stands alone; an uncommitted Spec exists only locally."""
     content = read(AGENTS_SKILL)
     assert "全件は Spec を参照" not in content
     spec_lines = [line for line in content.splitlines() if line.strip().startswith("- Spec:")]
     assert spec_lines, "the template must keep a Spec: line"
-    assert any("gitignore" in line for line in spec_lines)
+    assert any("ローカルにしか無い" in line for line in spec_lines)
     assert "単体で読める" in content
 
 
 def test_pr_posting_required_only_after_landing() -> None:
-    """Issue #235 B: mandatory posting is limited to landing turns."""
+    """Mandatory posting is limited to landing turns."""
     content = read(AGENTS_SKILL)
     assert "計画のみのセッションも投稿する" not in content
     assert "承認待ちで止まるターンは停止直前に1回" not in content
@@ -104,7 +117,7 @@ def test_pr_posting_required_only_after_landing() -> None:
 
 
 def test_pr_comment_purpose_is_record_not_stall_relief() -> None:
-    """Issue #235 C: the comment is only a durable record, not stall relief."""
+    """The comment is only a durable record, not stall relief."""
     content = read(AGENTS_SKILL)
     assert "永続的な記録" in content
     assert "stall" in content.lower()
@@ -112,59 +125,72 @@ def test_pr_comment_purpose_is_record_not_stall_relief() -> None:
 
 
 def test_skill_descriptions_do_not_advertise_pr_posting() -> None:
-    """Issue #235 D: posting lives in the body section, not the description."""
+    """Posting lives in the body section, not the description."""
     description = frontmatter_description(read(AGENTS_SKILL))
     assert "作業終了前の PR 投稿" not in description
     assert "Before finishing, post review status" not in description
 
 
-def test_merged_skill_keeps_claude_code_allowed_tools() -> None:
-    assert "allowed-tools:" in frontmatter_description(read(AGENTS_SKILL))
-
-
-def test_review_fix_examples_distinguish_public_and_parent_prs() -> None:
-    """Issue #377 F-3: the application example names usaturn/maatlog and
-    resolves MAIN_ROOT to the public checkout; the environment example points
-    to the parent. Both keep related tests, not a full verifier, as the
-    commit/push gate."""
-    for path in (AGENTS_SKILL,):
-        content = read(path)
-        assert re.search(r"usaturn/maatlog(?!-)", content), path
-        assert "usaturn/maatlog-poc" in content, path
-        assert "./scripts/ci/verify-devenv.sh" in content, path
-
-        # Skill helpers live only in the parent repo; resolve via TOPLEVEL.
-        assert '"$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"' in content, path
-        assert '"$MAIN_ROOT/.agents/skills/review-fix-planning' not in content, path
-
-        # The application-PR example names the public repo and the public
-        # root, and never invokes the parent's verifier for it.
-        example_lines = [line for line in content.splitlines() if line.lstrip().startswith(("Example:", "例:"))]
-        assert example_lines, f"{path}: expected an example line"
-        app_example = example_lines[0]
-        assert re.search(r"usaturn/maatlog(?!-)", app_example), app_example
-        assert "public/" in app_example, app_example
-        assert "verify-devenv.sh" not in app_example, app_example
-
-        # An environment-PR example points to the parent and names its verifier.
-        env_lines = [
-            line for line in content.splitlines() if "usaturn/maatlog-poc" in line and "verify-devenv.sh" in line
-        ]
-        assert env_lines, f"{path}: expected a parent-PR example"
-
-
-def test_number_argument_searches_public_reviews_too() -> None:
-    """Issue #377 review: public-PR review directories live under
-    public/reviews/, so #<number> resolution must look there as well."""
-    for path in (AGENTS_SKILL,):
-        content = read(path)
-        assert "public/reviews/" in content, path
-
-
-def test_spec_location_stays_in_parent_docs_draft() -> None:
-    """Issue #377 review: docs_draft/ is only gitignored in the parent repo;
-    pinning Specs to $MAIN_ROOT would drop them unignored into public/."""
-    for path in (AGENTS_SKILL,):
-        content = read(path)
-        assert "$MAIN_ROOT/docs_draft" not in content, path
-        assert "$TOPLEVEL/docs_draft/superpowers/" in content, path
+def test_allowed_tools_match_the_verification_and_spec_location() -> None:
+    tools = yaml.safe_load(frontmatter_description(read(AGENTS_SKILL)))["allowed-tools"]
+    assert isinstance(tools, str)
+    for entry in (
+        "Bash(uv run *)",
+        "Bash(bash .devcontainer/run-tests.bash*)",
+        "Bash(bash scripts/check-layout.sh*)",
+        "Bash(bash tests/scripts/*)",
+        "Write(docs/superpowers/specs/**)",
+        "Edit(docs/superpowers/specs/**)",
+    ):
+        assert entry in tools, entry
+    assert "scripts/ci/" not in tools
+    assert "docs_draft" not in tools
+
+
+def test_review_fix_examples_cover_this_repository_and_the_fork() -> None:
+    """MAIN_ROOT follows the repository boundary table; the gate is the
+    change-specific checks, not every suite."""
+    content = read(AGENTS_SKILL)
+    # Skill helpers live only in this repository; resolve via TOPLEVEL.
+    assert '"$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"' in content
+    assert '"$MAIN_ROOT/.agents/skills/review-fix-planning' not in content
+    assert "リポジトリ境界" in content
+    assert "scripts/resoloop-fork.sh clone" in content
+
+    example_lines = [line for line in content.splitlines() if line.lstrip().startswith("例:")]
+    assert example_lines, "expected an example line"
+    example = example_lines[0]
+    assert "usaturn/create-reso-world" in example
+    assert "bash .devcontainer/run-tests.bash" in example
+    assert "bash scripts/check-layout.sh" in example
+
+    fork_lines = [
+        line for line in content.splitlines() if "orange3134/resoloop" in line and "scripts/resoloop-fork.sh test" in line
+    ]
+    assert fork_lines, "expected a fork example"
+    assert "$TOPLEVEL/external/resoloop" in fork_lines[0]
+
+
+def test_number_argument_searches_the_fork_reviews_too() -> None:
+    """pr-review saves resoloop PR reviews under external/resoloop/reviews/."""
+    section = read(AGENTS_SKILL).split("## 第1引数の解決", 1)[1].split("## 手順", 1)[0]
+    scope = next(line for line in section.splitlines() if "ディレクトリだけを見る" in line)
+    assert "`reviews/`" in scope
+    assert "`external/resoloop/reviews/`" in scope
+
+
+def test_spec_goes_to_docs_superpowers_specs_of_this_repository() -> None:
+    content = read(AGENTS_SKILL)
+    assert "$TOPLEVEL/docs/superpowers/specs/" in content
+    assert "$MAIN_ROOT/docs" not in content
+    assert "docs_draft" not in content
+
+
+def test_landing_eval_uses_the_change_specific_gate() -> None:
+    evals = {item["id"]: item for item in json.loads(read(EVALS))["evals"]}
+    landing = evals[5]
+    assert any(
+        "bash .devcontainer/run-tests.bash" in item and "bash scripts/check-layout.sh" in item
+        for item in landing["expectations"]
+    )
+    assert "scripts/ci/" not in json.dumps(landing, ensure_ascii=False)
diff --git a/.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py b/.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py
index 6bf19df..6a4eeda 100644
--- a/.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py
+++ b/.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py
@@ -92,16 +92,16 @@ def test_find_own_comment_ignores_other_agents_and_rejects_duplicates() -> None:
 def test_upsert_creates_when_no_own_comment() -> None:
     gh = FakeGh(
         pr_view={
-            "url": "https://github.com/usaturn/maatlog/pull/225",
+            "url": "https://github.com/usaturn/create-reso-world/pull/225",
             "number": 225,
         },
         comments=[],
         upsert_response={
             "id": 99,
-            "html_url": "https://github.com/usaturn/maatlog/pull/225#issuecomment-99",
+            "html_url": "https://github.com/usaturn/create-reso-world/pull/225#issuecomment-99",
         },
     )
-    result = mod.upsert(225, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
+    result = mod.upsert(225, "usaturn/create-reso-world", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
     assert result["action"] == "created"
     assert result["comment_id"] == 99
     method_call = next(call for call in gh.calls if call[0][2] == "--method")
@@ -114,7 +114,7 @@ def test_upsert_creates_when_no_own_comment() -> None:
 def test_upsert_patches_existing_own_comment() -> None:
     gh = FakeGh(
         pr_view={
-            "url": "https://github.com/usaturn/maatlog/pull/225",
+            "url": "https://github.com/usaturn/create-reso-world/pull/225",
             "number": 225,
         },
         comments=[
@@ -125,52 +125,52 @@ def test_upsert_patches_existing_own_comment() -> None:
         ],
         upsert_response={
             "id": 41,
-            "html_url": "https://github.com/usaturn/maatlog/pull/225#issuecomment-41",
+            "html_url": "https://github.com/usaturn/create-reso-world/pull/225#issuecomment-41",
         },
     )
-    result = mod.upsert(225, "usaturn/maatlog", "claude-opus-5", "### 作業結果\n- push 済み", runner=gh)
+    result = mod.upsert(225, "usaturn/create-reso-world", "claude-opus-5", "### 作業結果\n- push 済み", runner=gh)
     assert result["action"] == "updated"
     method_call = next(call for call in gh.calls if call[0][2] == "--method")
     assert method_call[0][3] == "PATCH"
-    assert method_call[0][4] == "repos/usaturn/maatlog/issues/comments/41"
+    assert method_call[0][4] == "repos/usaturn/create-reso-world/issues/comments/41"
 
 
 def test_upsert_passes_the_requested_repository_to_gh_pr_view() -> None:
     gh = FakeGh(
         pr_view={
-            "url": "https://github.com/usaturn/maatlog/pull/7",
+            "url": "https://github.com/usaturn/create-reso-world/pull/7",
             "number": 7,
         },
         comments=[],
         upsert_response={
             "id": 12,
-            "html_url": "https://github.com/usaturn/maatlog/pull/7#issuecomment-12",
+            "html_url": "https://github.com/usaturn/create-reso-world/pull/7#issuecomment-12",
         },
     )
-    mod.upsert(7, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
+    mod.upsert(7, "usaturn/create-reso-world", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
     view_call = next(call for call in gh.calls if call[0][1:3] == ("pr", "view"))
     argv = view_call[0]
     assert "--repo" in argv
-    assert argv[argv.index("--repo") + 1] == "usaturn/maatlog"
+    assert argv[argv.index("--repo") + 1] == "usaturn/create-reso-world"
 
 
 def test_upsert_stops_when_gh_resolves_a_different_repository() -> None:
-    """A PR number alone is ambiguous: #7 exists in both maatlog-poc and maatlog."""
+    """A PR number alone is ambiguous: #7 exists in both the fork and upstream."""
     gh = FakeGh(
         pr_view={
-            "url": "https://github.com/usaturn/maatlog-poc/pull/7",
+            "url": "https://github.com/usaturn/resoloop/pull/7",
             "number": 7,
         },
         comments=[],
         upsert_response={"id": 12, "html_url": ""},
     )
-    with pytest.raises(mod.CommentError, match="usaturn/maatlog-poc"):
-        mod.upsert(7, "usaturn/maatlog", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
+    with pytest.raises(mod.CommentError, match="usaturn/resoloop"):
+        mod.upsert(7, "orange3134/resoloop", "claude-opus-5", "### レビュー状況\n- ok", runner=gh)
     assert not [call for call in gh.calls if "--method" in call[0]]
 
 
 def test_validate_repo_rejects_anything_but_owner_name() -> None:
-    assert mod.validate_repo("usaturn/maatlog") == "usaturn/maatlog"
-    for bad in ("maatlog", "usaturn/maatlog/extra", "", "usaturn /maatlog"):
+    assert mod.validate_repo("usaturn/create-reso-world") == "usaturn/create-reso-world"
+    for bad in ("create-reso-world", "usaturn/create-reso-world/extra", "", "usaturn /create-reso-world"):
         with pytest.raises(mod.CommentError, match="owner/name"):
             mod.validate_repo(bad)
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/review-fix-planning 2>&1 | tail -n 1
```

Expected: `6 failed, 15 passed`。失敗するのは `test_agents_skill_lands_on_existing_pr_after_related_tests`（`## 実装後` に `2. **変更の種類に応じた検証**` が無い）、`test_allowed_tools_match_the_verification_and_spec_location`、`test_review_fix_examples_cover_this_repository_and_the_fork`、`test_number_argument_searches_the_fork_reviews_too`、`test_spec_goes_to_docs_superpowers_specs_of_this_repository`、`test_landing_eval_uses_the_change_specific_gate`。ヘルパーのテスト（`test_upsert_pr_comment.py`）はサンプルの値を替えただけなので通る。

- [ ] **Step 3: SKILL.md と eval を直す**

````diff
diff --git a/.agents/skills/review-fix-planning/SKILL.md b/.agents/skills/review-fix-planning/SKILL.md
index 4a31b39..172dbe9 100644
--- a/.agents/skills/review-fix-planning/SKILL.md
+++ b/.agents/skills/review-fix-planning/SKILL.md
@@ -1,7 +1,7 @@
 ---
 name: review-fix-planning
 description: レビュー結果が格納されたディレクトリ（例 `reviews/ブランチ名/`、`docs/reviews/main/`、`reviews/#<PR番号>-<ブランチ>/` を指す `#番号`）を渡されて、修正計画・対応方針・指摘の取捨選択を求められたときに使う。「レビュー結果を確認して修正計画をたてて」「妥当な指摘だけ拾って直したい」「指摘のどれに対応するか決めたい」「複数モデルのレビューをまとめて」などの依頼が該当する。承認済みの review-fix 作業を実装する／対象ブランチへ反映させる依頼も該当する
-allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *), Bash(rm *), Bash(test *), Bash(uv run *), Bash(./scripts/ci/*), Write(docs_draft/superpowers/**), Edit(docs_draft/superpowers/**)
+allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *), Bash(rm *), Bash(test *), Bash(uv run *), Bash(bash .devcontainer/run-tests.bash*), Bash(bash scripts/check-layout.sh*), Bash(bash tests/scripts/*), Write(docs/superpowers/specs/**), Edit(docs/superpowers/specs/**)
 ---
 
 # レビュー指摘の選別と修正計画
@@ -14,10 +14,10 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *),
 
 第1引数が `#<番号>`（例 `#300`）のとき、手順に入る前にレビューディレクトリへ解決する:
 
-- 親リポジトリルートの `reviews/` 直下と、`public/reviews/`（`usaturn/maatlog` の PR レビューが置かれる場所）の直下にあるディレクトリだけを見る。再帰せず、その階層のファイルは候補にしない。
+- リポジトリのルートの `reviews/` 直下と、`external/resoloop/reviews/`（resoloop の PR のレビューが置かれる場所）の直下にあるディレクトリだけを見る。再帰せず、その階層のファイルは候補にしない。
 - ディレクトリ名が `#<番号>-` で開始されるものを一致とする（`#<番号>` の直後にハイフンが続くもの。例 `reviews/#300-fix-issue-299-pr-review-budget/`）。
 - 1 件だけ一致したら、そのディレクトリをレビューディレクトリとする。
-- 0 件なら、`reviews/` と `public/reviews/` の直下に一致するディレクトリが無い旨を報告して停止する。
+- 0 件なら、`reviews/` と `external/resoloop/reviews/` の直下に一致するディレクトリが無い旨を報告して停止する。
 - 複数一致したら、候補のディレクトリ名を列挙して停止し、フルパスでの指定を求める。
 
 `#<番号>` 以外の第1引数は従来どおりレビューディレクトリのパスとして扱う。
@@ -29,7 +29,7 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *),
 それ以外は、各項目をランタイムの plan / todo 機能のタスクにしてから開始する（Claude Code では TodoWrite、Codex では `update_plan`）。
 
 1. **範囲を固定する** — 解決したレビューディレクトリ配下の全ファイルを読む。各ファイル冒頭の「対象 HEAD」を記録する。複数世代が混在するのが普通である。レビュー成果物は gitignore 対象で未コミットのことがある（本リポジトリの `reviews/` がそうである）が、指定ディレクトリ内であれば Git の追跡状態にかかわらず正規の入力である。
-2. **現行 HEAD を特定する** — レビュー対象のブランチ／PR の現在の先端を `git` / `gh` で確認する。対象 PR のリポジトリもここで確定する: `PR_REPO` にその `owner/name` を設定し、`MAIN_ROOT` を `pr-review` と同じ規則で解決する — `usaturn/maatlog-poc` なら親の toplevel `$TOPLEVEL`（親 checkout で `git rev-parse --show-toplevel`）、`usaturn/maatlog` なら検証済み public submodule の `$TOPLEVEL/public`（`git -C "$TOPLEVEL/public" remote get-url origin` が `.gitmodules` の `submodule.public.url` と一致すること）、それ以外は推測せず停止する。`upsert_pr_comment.py` などのスキル helper は親リポジトリにだけ存在するため、`$MAIN_ROOT` ではなく `$TOPLEVEL` から解決する。
+2. **現行 HEAD を特定する** — レビュー対象のブランチ／PR の現在の先端を `git` / `gh` で確認する。対象 PR のリポジトリもここで確定する: `PR_REPO` にその `owner/name` を設定し、`MAIN_ROOT` を `pr-review` と同じ規則（ルート `AGENTS.md` の「リポジトリ境界」の表）で解決する — `usaturn/create-reso-world` ならこのリポジトリの toplevel `$TOPLEVEL`（`git rev-parse --show-toplevel`）、`usaturn/resoloop` または `orange3134/resoloop` なら fork の checkout `$TOPLEVEL/external/resoloop`（`origin` が `usaturn/resoloop`、`upstream` が `orange3134/resoloop` であること。満たさなければ `scripts/resoloop-fork.sh clone` を案内して停止する）、それ以外は推測せず停止する。`upsert_pr_comment.py` などのスキル helper はこのリポジトリにだけ存在するため、`$MAIN_ROOT` ではなく `$TOPLEVEL` から解決する。
 3. **各指摘を現行 HEAD の「コミット済み」内容で検証する** — `git show <HEAD>:<path>` で読む。指摘された path の `REVIEWED_HEAD` にある committed source/test blob は検証根拠として許可する。挙動の指摘は、path と reviewed HEAD を別引数にした隔離 worktree で再現する:
 
    ```bash
@@ -63,21 +63,25 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *),
 
 **PR への反映 — この順で行う:**
 
-1. **実装に関連したテスト** だけを走らせる。Spec の各「対応する」項目に書いた検証方法、変更ファイルをカバーするテスト、今回の Fix で追加したテスト。
-2. 失敗したら直す。commit しない。
-3. `git fetch origin` し、レビュー対象ブランチの先端を確認する。関連テストが通ったら、レビュー対象ブランチ（既存 PR の head）へ commit する。`main` ではない。新しい `*-review-fixes` ブランチでもない。
-4. そのブランチを **既存 PR** へ `git push` する。push の成功を確認する。reject されたら rebase または merge し、関連テストを再走してから再度 push する。新しい PR を開かない。`finishing-a-development-branch` のメニューを出さない。
-5. 完了報告の前に **作業終了前の PR 投稿** を実行する。
+1. **実装に関連したテスト** を走らせる。Spec の各「対応する」項目に書いた検証方法、変更ファイルをカバーするテスト、今回の Fix で追加したテスト。
+2. **変更の種類に応じた検証** を続けて通す。
+   - 環境の変更（ルートの `.devcontainer/`・`scripts/`・`tests/`・`templates/`・`.agents/`・設定ファイルなど）: `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh`。スキル（`.agents/skills/`・`tests/skills/`）を変えた場合は `uv run pytest tests/skills .agents/skills` も
+   - ワールドのプロジェクトの変更: そのプロジェクトのディレクトリで `uv run pytest`
+   - resoloop fork（`external/resoloop`）の変更: 変更したプロジェクトに関連する `dotnet test`
+3. 失敗したら直す。commit しない。
+4. `git fetch origin` し、レビュー対象ブランチの先端を確認する。手順 1・2 が通ったら、レビュー対象ブランチ（既存 PR の head）へ commit する。`main` ではない。新しい `*-review-fixes` ブランチでもない。
+5. そのブランチを **既存 PR** へ `git push` する。push の成功を確認する。reject されたら rebase または merge し、手順 1・2 を再走してから再度 push する。新しい PR を開かない。`finishing-a-development-branch` のメニューを出さない。
+6. 完了報告の前に **作業終了前の PR 投稿** を実行する。
 
 レビュー対象ブランチに open な PR が無いなら、作らず停止して報告する。ユーザが作れと言うまで作らない。コメントの投稿もしない。
 
 **この節が commit / push の常設指示である。** 二度目の「commit」「push」を待たない。「進めて」は実装の承認であり、この手順が PR への反映である。
 
-**commit / push の条件にしないもの:** レビュー対象リポジトリの full verifier（`usaturn/maatlog` では `./scripts/ci/verify.sh full`、`usaturn/maatlog-poc` では `./scripts/ci/verify-devenv.sh`。既存 PR の CI がまだ走る）、スイート全体、`superpowers:verification-before-completion` のフルスイート、`superpowers:finishing-a-development-branch`。
+**commit / push の条件にしないもの:** 上の検証に含まれない一括検証（変更と関係の無いワールドのプロジェクトの `uv run pytest`、`scripts/resoloop-fork.sh test` による fork の全テストなど。既存 PR の CI がまだ走る）、`superpowers:verification-before-completion` のフルスイート、`superpowers:finishing-a-development-branch`。
 
-例: Spec の検証が `uv run pytest tests/theme/test_rail.py` —— アプリケーションの変更なので、レビュー対象 PR は `usaturn/maatlog` の #142 で、`MAIN_ROOT` は検証済み `public/` checkout。そのファイルと、変更した CSS をカバーするテストが通る。`feature/issue-102-author-right-rail` に commit し、`git -C "$MAIN_ROOT" push origin HEAD` で公開 PR へ反映する。status comment の `PR_REPO` は `usaturn/maatlog`。先に `./scripts/ci/verify.sh full` は走らせない。`feature/issue-102-review-fixes` は開かない。push 後、同じ PR にレビュー状況・作業判断・作業結果のコメントを作成または更新する。
+例: レビュー対象 PR は `usaturn/create-reso-world` の #12 で、Spec の検証が `bash tests/scripts/test-check-layout.bash` —— `scripts/check-layout.sh` を直す環境の変更なので、`MAIN_ROOT` は toplevel。そのテストに続けて `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通す。`fix/check-layout-mounts` に commit し、`git -C "$MAIN_ROOT" push origin HEAD` で既存 PR へ反映する。status comment の `PR_REPO` は `usaturn/create-reso-world`。変更と関係の無いプロジェクトの `uv run pytest` は走らせない。`fix/check-layout-mounts-review-fixes` は開かない。push 後、同じ PR にレビュー状況・作業判断・作業結果のコメントを作成または更新する。
 
-親の開発環境 PR も同じ規則が親経路で成立する: `PR_REPO=usaturn/maatlog-poc`、`MAIN_ROOT` は親の toplevel で、親の full verifier は `./scripts/ci/verify-devenv.sh` であり、これも反映の条件にしない。
+resoloop の上流への PR も同じ規則が fork の経路で成立する: `PR_REPO=orange3134/resoloop`、`MAIN_ROOT` は `$TOPLEVEL/external/resoloop` で、PR の head branch は fork（`origin`）にあるので `git -C "$MAIN_ROOT" push origin HEAD` で反映する。検証は変更したプロジェクトに関連する `dotnet test` までで、`scripts/resoloop-fork.sh test` による全テストは反映の条件にしない。
 
 ## 作業終了前の PR 投稿
 
@@ -112,13 +116,13 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *),
 
 ### 作業結果
 - このターン: 計画のみ | push 済み | 途中停止
-- Spec: `<path>`（gitignore 対象でローカルにしか無い）または未作成
+- Spec: `<path>`（コミットしていなければローカルにしか無い）または未作成
 - commit / push: `<sha>` またはしていない
 - 次: 承認待ち | 完了 | 停止理由
 ```
 
 ```bash
-TOPLEVEL="$(git rev-parse --show-toplevel)"   # 親 checkout で実行する
+TOPLEVEL="$(git rev-parse --show-toplevel)"   # このリポジトリの中で実行する（external/resoloop の中では実行しない）
 HELPER="$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
 uv run --no-project python "$HELPER" --pr "$PR_NUMBER" --repo "$PR_REPO" --model-name "$MODEL_NAME" <<EOF
 ## review-fix-planning（$MODEL_NAME）
@@ -155,13 +159,13 @@ EOF
 - **第三者テーマ・外部利用者の互換性のみに影響するもの** — 公式の経路が一貫していれば対応しない
 - 将来の保険、性能の過剰近似、Info 級の記載漏れ
 
-リポジトリの方針ファイル（CLAUDE.md 等）が既に決着させている論点は「対応しない」に置き、その方針を根拠として引く。
+リポジトリの方針ファイル（`AGENTS.md`・`CLAUDE.md` 等）が既に決着させている論点は「対応しない」に置き、その方針を根拠として引く。
 
 ## Spec は経路に関わらず必須
 
 `superpowers:brainstorming` は bounded / spike 経路では Spec 不要と書いているが、**このスキルではユーザ指示が優先し、3 経路すべてで Spec を書く。**
 
-- 配置: CLAUDE.md の規定に従う（本リポジトリでは `$TOPLEVEL/docs_draft/superpowers/` — 常に親側。`docs_draft/` は親でだけ gitignore 対象なので、`MAIN_ROOT` が `public/` のとき `$MAIN_ROOT` 配下へ置いてはならない）
+- 配置: `$TOPLEVEL/docs/superpowers/specs/`（ルート `AGENTS.md` の規定）。常にこのリポジトリ側に置き、`MAIN_ROOT` が `external/resoloop` のときも fork の中へ置かない
 - 命名: `YYYY-MM-DD-<topic>-review-fixes-design.md`
 - 必須の中身:
   - 全指摘の一覧と 4 区分の振り分け（1 件も落とさない）
@@ -194,10 +198,10 @@ EOF
 | 「必須テンプレートの仕様を直せば根本解決する」 | 第三者互換の作り込み。方針ファイルが決着させているなら対応しない |
 | 「仕様の是非なのでユーザに聞こう」 | 判断保留は潜在バグの数行修正だけ。仕様論点は「対応しない」＋ Spec に 1 行 |
 | 「進めては実装許可であり commit/push の許可ではない」 | この節が commit/push の指示である。関連テストが通ったら PR へ反映する |
-| 「関連テストでは足りない。CLAUDE.md は verify.sh full が入口」 | ローカルの commit / push 条件は実装に関連したテスト。full verify は既存 PR の CI |
+| 「念のため全プロジェクトの `uv run pytest` と fork の全テストも通してから push する」 | 反映の条件は、実装に関連したテストと変更の種類に応じた検証だけである。それ以外は既存 PR の CI が確かめる |
 | 「ユーザが commit と打つまで commit しない」 | このワークフローではこの節がその指示である |
 | 「finishing-a-development-branch のメニューを出す」 | 出さない。既存 PR に push する |
-| 「レビュー修正は別 PR。#144 がそうだった」 | レビュー対象の既存 PR に push する。`*-review-fixes` の追加 PR はしない |
+| 「レビュー修正は別 PR にするものだ」 | レビュー対象の既存 PR に push する。`*-review-fixes` の追加 PR はしない |
 | 「すでに review-fixes ブランチがある。捨てるのは無駄」 | サンクコスト。レビュー対象 PR の head ブランチに載せる |
 | 「チャットに計画を書けば十分」 | PR への記録も反映作業の一部である。計画のみのターンの投稿は任意である |
 | 「実装していないので投稿不要」 | 計画のみの投稿は任意である。commit / push まで完了したターンのみ必須である |
@@ -213,7 +217,8 @@ EOF
 - Fix / 対応する に置いた finding ごとに、(a)〜(d) のどれを満たすかと根拠を示せない
 - 「解消済み」の根拠が working tree のファイルである
 - 判断保留に仕様・設計の質問が入っている
-- `./scripts/ci/verify.sh full` や `./scripts/ci/verify-devenv.sh` を commit/push の条件として走らせようとしている
+- 変更と関係の無い一括検証（別のプロジェクトの `uv run pytest`、`scripts/resoloop-fork.sh test` など）を commit/push の条件として走らせようとしている
+- 環境の変更なのに `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通さずに commit しようとしている
 - レビュー修正のために新しい PR を開こうとしている、または `*-review-fixes` ブランチへ push しようとしている
 - `finishing-a-development-branch` のメニューを出そうとしている
 - 実装に関連したテストが通ったあと、二度目の「commit」「push」を待っている
diff --git a/.agents/skills/review-fix-planning/evals/evals.json b/.agents/skills/review-fix-planning/evals/evals.json
index d1248e9..57cbbfa 100644
--- a/.agents/skills/review-fix-planning/evals/evals.json
+++ b/.agents/skills/review-fix-planning/evals/evals.json
@@ -56,12 +56,12 @@
     {
       "id": 5,
       "name": "land-on-existing-pr-after-related-tests",
-      "prompt": "承認済み Spec の Fix 項目を実装し終えた。変更ファイルに対する関連テストは通った。CLAUDE.md は検証入口を ./scripts/ci/verify.sh full としている。finishing-a-development-branch は統合メニューを出せと書いてある。レビュー対象の PR はまだ open である。次に何をするか。",
-      "expected_output": "Related tests already passing is the landing gate. Commit on the reviewed branch, push to the existing PR, and post or update this agent's status comment covering レビュー状況 / 作業判断 / 作業結果. Do not run ./scripts/ci/verify.sh full as a landing gate, do not open a new PR, and do not present the finishing-a-development-branch menu.",
+      "prompt": "承認済み Spec の Fix 項目を実装し終えた。変更は scripts/check-layout.sh だけで、関連テスト bash tests/scripts/test-check-layout.bash は通った。念のため 3 つのワールドのプロジェクトの uv run pytest も通すべきか迷っている。finishing-a-development-branch は統合メニューを出せと書いてある。レビュー対象の PR はまだ open である。次に何をするか。",
+      "expected_output": "Environment change: run bash .devcontainer/run-tests.bash and bash scripts/check-layout.sh after the related test, then commit on the reviewed branch, push to the existing PR, and post or update this agent's status comment covering レビュー状況 / 作業判断 / 作業結果. Do not add the world projects' uv run pytest as a landing gate, do not open a new PR, and do not present the finishing-a-development-branch menu.",
       "files": [],
       "expectations": [
-        "Only tests related to the implementation are treated as the landing gate; ./scripts/ci/verify.sh full is not.",
-        "The result commits on the reviewed branch after those tests pass.",
+        "The landing gate is the related test plus bash .devcontainer/run-tests.bash and bash scripts/check-layout.sh; the world projects' uv run pytest is not required.",
+        "The result commits on the reviewed branch after those checks pass.",
         "The result pushes to the existing reviewed PR rather than opening a new PR.",
         "The result does not present the finishing-a-development-branch menu.",
         "The result posts or updates a Japanese status comment on that PR before finishing."
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/review-fix-planning 2>&1 | tail -n 1
git grep -n -i -E 'maatlog|public/|verify\.sh|scripts/ci|docs_draft' -- .agents/skills/review-fix-planning ':!*/tests/*'
```

Expected: `21 passed`。`git grep` は何も表示しない。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/review-fix-planning/SKILL.md .agents/skills/review-fix-planning/evals/evals.json \
  .agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py \
  .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py
git commit -m "feat(review-fix-planning): use this repository's checks and spec location

Review directories are looked up under reviews/ and external/resoloop/reviews/,
and MAIN_ROOT follows the repository boundary table. Before commit and push,
the related tests are followed by the checks of the change: run-tests and
check-layout for the environment (plus the skill tests for skills), the
project's pytest for a world project and the related dotnet test for the fork.
Specs go to docs/superpowers/specs/, and allowed-tools, the examples and the
eval follow.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 7: agent-handoff の Spec の置き場と概要の文言（仕様 8.2、持ち越し N-14）

Spec と Plan の置き場を `docs/superpowers/` にし、`allowed-tools` の書き込み先も合わせる。概要の「両ランタイムで」は、5 つのランタイムが同じ 1 本を読む今の構成に合わない表現なので直す。evals の q2 を、このリポジトリに無い `python-tdd-team` の代わりに、別のエージェントが進めていたフェーズの確認にする（description は PH2-R4 のとおり変えない）。

**Files:**
- Modify: `.agents/skills/agent-handoff/SKILL.md`、`.agents/skills/agent-handoff/evals/trigger_queries.json`（q2）
- Test: `.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py b/.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py
index 207dc4d..0b6bf60 100644
--- a/.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py
+++ b/.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py
@@ -5,12 +5,15 @@ import os
 import re
 from pathlib import Path
 
+import yaml
+
 REPO_ROOT = Path(__file__).resolve().parents[4]
 SKILL_DIR = REPO_ROOT / ".agents/skills/agent-handoff"
 AGENTS_SKILL = SKILL_DIR / "SKILL.md"
 CLAUDE_LINK = REPO_ROOT / ".claude/skills/agent-handoff"
 SCHEMA = SKILL_DIR / "references/handoff-schema.md"
 EVALS = SKILL_DIR / "evals/evals.json"
+TRIGGERS = SKILL_DIR / "evals/trigger_queries.json"
 
 #
 # Fields only the outgoing agent can supply. The whole point of the
@@ -82,7 +85,35 @@ def test_skill_states_the_handoff_contract() -> None:
 
 def test_skill_declares_claude_code_allowed_tools() -> None:
     """Claude Code gates the skill's tool surface; Codex and pi ignore the key."""
-    assert "allowed-tools:" in read(AGENTS_SKILL).split("---", 2)[1]
+    tools = yaml.safe_load(read(AGENTS_SKILL).split("---", 2)[1])["allowed-tools"]
+    assert isinstance(tools, str)
+    for entry in (
+        "Write(tmp/docs_draft/claude_handoffs/**)",
+        "Edit(tmp/docs_draft/claude_handoffs/**)",
+        "Write(docs/superpowers/**)",
+        "Edit(docs/superpowers/**)",
+    ):
+        assert entry in tools, entry
+    assert "docs_draft/superpowers" not in tools
+
+
+def test_specs_and_plans_live_in_docs_superpowers() -> None:
+    # AGENTS.md keeps specs and plans under docs/superpowers/; docs_draft/ is a
+    # gitignored scratch area that a receiver on another checkout cannot read.
+    content = read(AGENTS_SKILL)
+    assert "`docs/superpowers/`" in content
+    assert "docs_draft/superpowers" not in content
+
+
+def test_overview_does_not_count_runtimes() -> None:
+    # Codex, pi, Devin, Cursor and Claude Code all read this one file.
+    assert "両ランタイム" not in read(AGENTS_SKILL)
+
+
+def test_trigger_queries_belong_to_this_repository() -> None:
+    queries = {item["id"]: item for item in json.loads(read(TRIGGERS))["queries"]}
+    assert queries["q2"]["should_trigger"] is True
+    assert "python-tdd-team" not in json.dumps(queries, ensure_ascii=False)
 
 
 def test_skill_covers_the_gaps_hand_written_handoffs_drop() -> None:
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/agent-handoff 2>&1 | tail -n 1
```

Expected: `4 failed, 12 passed`（`allowed-tools`、Spec の置き場、「両ランタイム」、q2 の 4 件）。

- [ ] **Step 3: SKILL.md と q2 を直す**

```diff
diff --git a/.agents/skills/agent-handoff/SKILL.md b/.agents/skills/agent-handoff/SKILL.md
index ec08a76..72534cf 100644
--- a/.agents/skills/agent-handoff/SKILL.md
+++ b/.agents/skills/agent-handoff/SKILL.md
@@ -1,7 +1,7 @@
 ---
 name: agent-handoff
 description: エージェント間で作業を受け渡すときに使う。渡す側 —「区切りのいい所で停止して引き継ぎ資料を作って」「別のエージェントに実装させる」「この Spec を渡せば足りるか」「handoff を書いて」と言われたとき。受け取る側 — 他のエージェント（Codex / Grok / 別セッションの Claude Code）が superpowers・brainstorming・writing-plans・review-fix-planning・subagent-driven-development で進めた作業を「引き継いで」「続きをやって」「どこまで終わったか確認して」と言われたとき。tmp/docs_draft/claude_handoffs/ の handoff アーティファクトを読み書きし、決定済みの裁定・触ってはいけない範囲・検証手順・反映先まで引き渡す
-allowed-tools: Read, Grep, Glob, Skill, Bash(ls *), Bash(cat *), Bash(git *), Bash(gh *), Bash(uv run *), Write(tmp/docs_draft/claude_handoffs/**), Edit(tmp/docs_draft/claude_handoffs/**), Write(docs_draft/superpowers/**), Edit(docs_draft/superpowers/**)
+allowed-tools: Read, Grep, Glob, Skill, Bash(ls *), Bash(cat *), Bash(git *), Bash(gh *), Bash(uv run *), Write(tmp/docs_draft/claude_handoffs/**), Edit(tmp/docs_draft/claude_handoffs/**), Write(docs/superpowers/**), Edit(docs/superpowers/**)
 ---
 
 # エージェント引き継ぎ
@@ -10,7 +10,7 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(ls *), Bash(cat *), Bash(git *), Ba
 
 引き継ぎ先のエージェントは**コールドスタート**である。持っているのはリポジトリと、こちらが書き残したものだけで、それ以外は何も無い。このスキルは受け渡しの両端を扱う。作業を止める側の **handoff を書く**手順と、続きを引き取る側の **handoff を読む**手順である。
 
-アーティファクトは `tmp/docs_draft/claude_handoffs/` に置く Markdown と JSON の対で、スキーマは `.agents/skills/agent-handoff/references/handoff-schema.md` にある（両ランタイムで同じ 1 本を正本として共有する）。書く前・解釈する前に必ず読む。
+アーティファクトは `tmp/docs_draft/claude_handoffs/` に置く Markdown と JSON の対で、スキーマは `.agents/skills/agent-handoff/references/handoff-schema.md` にある（どのランタイムもこの 1 本を読む）。書く前・解釈する前に必ず読む。
 
 **引き継ぎが失敗する原因は、要約の不足ではないことがほとんどである。** 差分ならコールドなエージェントでも読み直せる。読み直せないのは「何を決めて、何を棄却したか」である。高くつく失敗は次の 4 つに集中する。決着済みの判断を蒸し返す、意図的に除外した指摘に手を出す、独自の検証を発明して実環境に対して走らせる、二本目の PR を開く。`decisions` / `out_of_scope` / `verification` / `landing` はこの 4 つのためだけに存在する。
 
@@ -25,7 +25,7 @@ allowed-tools: Read, Grep, Glob, Skill, Bash(ls *), Bash(cat *), Bash(git *), Ba
 
 1. **区切りを決めて、それを明記する。** 編集の途中で書いた handoff は、handoff が無いより悪い。作業単位を完了させるか元に戻すかを選び、どちらにしたかを `session.stop_reason` に書く。適用途中の編集を作業ツリーに残すなら、冒頭の節で必ず宣言する。書かなければ受け手は「作業ツリー＝ `git.head`」と仮定して踏む。
 
-2. **理屈の置き場所を決める。** 長い論証は Spec / Plan 側（本リポジトリでは `docs_draft/superpowers/`）に置き、handoff は 1 行の裁定だけを持って `sources.spec` で指す。両方に書くと必ず食い違う。Spec が無いときは `sources.spec` を `null`（JSON）/ `none`（Markdown）にし、理由を書く。存在しないパスを捏造しない。
+2. **理屈の置き場所を決める。** 長い論証は Spec / Plan 側（本リポジトリでは `docs/superpowers/` の `specs/` と `plans/`）に置き、handoff は 1 行の裁定だけを持って `sources.spec` で指す。両方に書くと必ず食い違う。Spec が無いときは `sources.spec` を `null`（JSON）/ `none`（Markdown）にし、理由を書く。存在しないパスを捏造しない。
 
 3. **対の 2 ファイルを手書きする。** `tmp/docs_draft/claude_handoffs/<timestamp>-<session>.handoff.md` と同名の `.handoff.json` をスキーマに従って手書きする。
 
diff --git a/.agents/skills/agent-handoff/evals/trigger_queries.json b/.agents/skills/agent-handoff/evals/trigger_queries.json
index b1b44af..e12fb5d 100644
--- a/.agents/skills/agent-handoff/evals/trigger_queries.json
+++ b/.agents/skills/agent-handoff/evals/trigger_queries.json
@@ -10,10 +10,10 @@
     },
     {
       "id": "q2",
-      "query": "python-tdd-team の Phase C がどこまで終わったか Codex で確認して",
+      "query": "Claude Code が進めていた再設計のフェーズ 4 がどこまで終わったか Codex で確認して",
       "should_trigger": true,
-      "expected_terms": ["python-tdd-team", "Phase", "Codex"],
-      "notes": "Reading side, repo-local Claude skill continuation"
+      "expected_terms": ["フェーズ", "Codex", "確認"],
+      "notes": "Reading side, continuing a phased plan another agent was executing"
     },
     {
       "id": "q3",
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/agent-handoff 2>&1 | tail -n 1
```

Expected: `16 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/agent-handoff/SKILL.md .agents/skills/agent-handoff/evals/trigger_queries.json \
  .agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py
git commit -m "fix(agent-handoff): point specs and plans at docs/superpowers

Specs and plans live under docs/superpowers/ in this repository, and
allowed-tools may write there. The overview no longer speaks of two runtimes,
and trigger query q2 asks about a phase another agent was executing instead of
a workflow this repository does not have.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 8: planning-parallel-issues の対象リポジトリ（仕様 8.2）

対象を `usaturn/create-reso-world` の Issue と明記し、参照文書の `{owner}/{repo}` をこのリポジトリに読み替えるよう書く。resoloop の作業は「リポジトリ境界」のとおり fork の担当で、ユーザが名指ししたときだけ fork にボードを作る。evals の検証記録から `verify.sh` の行を消す。

**Files:**
- Create: `.agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py`
- Modify: `.agents/skills/planning-parallel-issues/SKILL.md`、`.agents/skills/planning-parallel-issues/evals/validation.md`（1 行削除）

- [ ] **Step 1: 失敗するテストを書く**

`.agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py` を次の内容で作る。

```python
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/planning-parallel-issues"
SKILL = SKILL_DIR / "SKILL.md"
VALIDATION = SKILL_DIR / "evals/validation.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_boards_target_the_issues_of_this_repository() -> None:
    # Spec 8.2: the skill works on usaturn/create-reso-world Issues.
    content = read(SKILL)
    target = content.split("## Target repository", 1)[1].split("\n## ", 1)[0]
    assert "`usaturn/create-reso-world`" in target
    assert "git remote get-url origin" in target
    assert "`{owner}/{repo}`" in target
    assert "repository boundary table in the root `AGENTS.md`" in target


def test_referenced_procedures_exist() -> None:
    links = re.findall(r"\]\((references/[^)]+)\)", read(SKILL))
    assert links
    for link in links:
        assert (SKILL_DIR / link).is_file(), link


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/planning-parallel-issues"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/planning-parallel-issues"


def test_validation_record_lists_only_checks_that_exist_here() -> None:
    assert "scripts/ci/" not in read(VALIDATION)
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/planning-parallel-issues 2>&1 | tail -n 1
```

Expected: `2 failed, 2 passed`（`## Target repository` が無い、`validation.md` に `scripts/ci/` がある）。

- [ ] **Step 3: SKILL.md と検証記録を直す**

```diff
diff --git a/.agents/skills/planning-parallel-issues/SKILL.md b/.agents/skills/planning-parallel-issues/SKILL.md
index 5dcc625..5bc18c3 100644
--- a/.agents/skills/planning-parallel-issues/SKILL.md
+++ b/.agents/skills/planning-parallel-issues/SKILL.md
@@ -9,6 +9,10 @@ Make the parent Issue the entry point for independent sessions. Parallelism come
 
 Announce this skill. Read repository instructions, existing Issues, code, and available skills before writing. Use the user's language for Issue bodies and reports.
 
+## Target repository
+
+Boards, Issues and claim refs live in `usaturn/create-reso-world`, this repository's `origin`. Before the first write, confirm that `git remote get-url origin` names it, and use it wherever the references write `{owner}/{repo}`. Work on ResoLoop itself belongs to the fork (`usaturn/resoloop`, checked out at `external/resoloop`) under the repository boundary table in the root `AGENTS.md`; build a board there only when the user names that repository. Stop instead of guessing for any other repository.
+
 ## Choose the requested operation
 
 | Request | Required procedure | Finish line |
diff --git a/.agents/skills/planning-parallel-issues/evals/validation.md b/.agents/skills/planning-parallel-issues/evals/validation.md
index 1be92cd..27999e2 100644
--- a/.agents/skills/planning-parallel-issues/evals/validation.md
+++ b/.agents/skills/planning-parallel-issues/evals/validation.md
@@ -207,7 +207,6 @@ that GitHub accepted a live mutation.
 - Both runtime entry paths pass `skill-creator/scripts/quick_validate.py`.
 - Local Markdown references, UI metadata, scenario JSON, and the relative Claude skill symlink resolve.
 - Related existing agent-handoff tests: 11 passed.
-- `./scripts/ci/verify.sh static`: `EXIT=0` (Ruff, formatting, Pyright, JavaScript/CSS lint/format/type checks).
 - No changes to the root detached checkout; no implementation or live Issue changes were made by these evaluations.
 
 ## Reproduction
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/planning-parallel-issues 2>&1 | tail -n 1
```

Expected: `4 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py \
  .agents/skills/planning-parallel-issues/SKILL.md .agents/skills/planning-parallel-issues/evals/validation.md
git commit -m "feat(planning-parallel-issues): target the Issues of this repository

Boards, Issues and claim refs live in usaturn/create-reso-world, checked
against origin before the first write; the resoloop fork gets a board only
when the user names it, and any other repository stops. The validation record
no longer lists the migration source's verify script.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 9: monitoring-long-tasks と runtimes の一般化（仕様 8.2）

`verify.sh` 専用だった PID の導出・同一性確認・ログの扱いを、「ログのパスを出力する任意の長時間コマンド」向けに書き直す。同一性確認は、コマンドラインに意図したコマンドが含まれることと、cwd が対象の worktree であることの 2 つにまとめる。`EXIT=<code>` の行は、コマンドがログに書く場合に確かめ、書かない場合はランタイムの終了通知の終了コードを使う。

**Files:**
- Modify: `.agents/skills/monitoring-long-tasks/SKILL.md`、`.agents/monitoring-runtimes.md`
- Test: `.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py b/.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py
index 689a8c3..8f0d809 100644
--- a/.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py
+++ b/.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py
@@ -7,6 +7,7 @@ AGENTS_SKILL = REPO_ROOT / ".agents/skills/monitoring-long-tasks/SKILL.md"
 CLAUDE_SKILL = REPO_ROOT / ".claude/skills/monitoring-long-tasks/SKILL.md"
 CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
 AGENTS_MD = REPO_ROOT / "AGENTS.md"
+RUNTIMES = REPO_ROOT / ".agents/monitoring-runtimes.md"
 
 
 def read(path: Path) -> str:
@@ -70,3 +71,24 @@ def test_review_deadline_exception_is_predeclared_and_narrow() -> None:
         "unconfirmed cancellation",
     ):
         assert required in content
+
+
+def test_liveness_rules_cover_any_command_that_prints_its_log() -> None:
+    # Spec 8.2: the PID and log rules no longer name one verification script.
+    content = read(AGENTS_SKILL)
+    for rule in (
+        "When the command prints its log path and the log name ends with its PID",
+        "`ps -p <pid> -o args=` contains the intended command",
+        "`readlink -f /proc/<pid>/cwd` equals the target worktree",
+        "apply step 3's command and cwd identity check to each remaining PID",
+        "Monitor the log path the command prints",
+    ):
+        assert rule in content, rule
+
+
+def test_runtime_table_uses_the_generic_log_rules() -> None:
+    content = read(RUNTIMES)
+    assert "ログ名からの PID 導出" in content
+    assert "ログ path を印字するコマンドはその path を使い" in content
+    for path in (AGENTS_SKILL, RUNTIMES):
+        assert "scripts/ci/" not in read(path)
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/monitoring-long-tasks 2>&1 | tail -n 1
```

Expected: `2 failed, 6 passed`。

- [ ] **Step 3: スキルと runtimes を直す**

step 5 は `Monitor the log path` で始める（ランタイム固有の語を禁じる既存のテストが、この句を一般の英語として除外している）。

````diff
diff --git a/.agents/monitoring-runtimes.md b/.agents/monitoring-runtimes.md
index 448a381..083c8b6 100644
--- a/.agents/monitoring-runtimes.md
+++ b/.agents/monitoring-runtimes.md
@@ -2,19 +2,19 @@
 
 `monitoring-long-tasks` が定める監視手順を、この Dev Container の各ランタイムでどのツールに割り当てるかだけを示す。
 
-- OR 待機の型、レポートが無いまま対象が消えた場合の異常終了扱い、`verify.sh` の PID 導出とログ末尾 `EXIT=<code>` の確認は、スキル step 1〜3 に従う。ここでは重複させない
+- OR 待機の型、レポートが無いまま対象が消えた場合の異常終了扱い、ログ名からの PID 導出と終了コードの確認は、スキル step 1〜3 に従う。ここでは重複させない
 - controller がターンを完了通知に委ねてよいかは扱わない
 
 ## 対応表
 
 | ランタイム | 完了 | 生存 | 進捗 / stall | OR 待機の組み方 |
 | --- | --- | --- | --- | --- |
-| Claude Code | Bash `run_in_background: true` の完了通知（終了コードを含む）。サブエージェントは `Agent` の完了通知 | 既知の PID を `kill -0` | 完了通知やツール結果が返す出力ファイル path を `Read`。`verify.sh` は印字されたログ path を使い、固定パスを仮定しない | 下の参考実装を `run_in_background: true` に渡す。進捗を都度イベントとして受け取るときだけ `Monitor` を使う |
-| Devin | バックグラウンド `exec`（`timeout: 0`、または既定の自動バックグラウンド化）で起動した対象を `get_output` で待つ。`get_output` は対象プロセスの終了で即復帰し、終了コードは出力末尾の `Exit code: <n>` で確認する。1 回の待機上限は約 280 秒のため、タイムアウトしたら呼び直す。非同期の完了通知が届くのは `run_subagent` のサブエージェント（`<subagent_completion_notification>`）だけであり、シェルプロセスの終了は push されない | 既知の PID を `kill -0`（`exec` 経由）。`verify.sh` の PID 同一性確認はスキル step 3 のまま適用する | `verify.sh` が印字したログ path を `read` で読む。mtime / サイズが必要なら `exec` で `stat` を使う | 下の参考実装をそのままバックグラウンド `exec`（`timeout: 0`）で動かし、その監視シェルを `get_output` で待つ。ループの脱出がそのまま `report exists OR worker is not alive` の解消になる |
+| Claude Code | Bash `run_in_background: true` の完了通知（終了コードを含む）。サブエージェントは `Agent` の完了通知 | 既知の PID を `kill -0` | 完了通知やツール結果が返す出力ファイル path を `Read`。ログ path を印字するコマンドはその path を使い、固定パスを仮定しない | 下の参考実装を `run_in_background: true` に渡す。進捗を都度イベントとして受け取るときだけ `Monitor` を使う |
+| Devin | バックグラウンド `exec`（`timeout: 0`、または既定の自動バックグラウンド化）で起動した対象を `get_output` で待つ。`get_output` は対象プロセスの終了で即復帰し、終了コードは出力末尾の `Exit code: <n>` で確認する。1 回の待機上限は約 280 秒のため、タイムアウトしたら呼び直す。非同期の完了通知が届くのは `run_subagent` のサブエージェント（`<subagent_completion_notification>`）だけであり、シェルプロセスの終了は push されない | 既知の PID を `kill -0`（`exec` 経由）。PID の同一性確認はスキル step 3 のまま適用する | コマンドが印字したログ path を `read` で読む。mtime / サイズが必要なら `exec` で `stat` を使う | 下の参考実装をそのままバックグラウンド `exec`（`timeout: 0`）で動かし、その監視シェルを `get_output` で待つ。ループの脱出がそのまま `report exists OR worker is not alive` の解消になる |
 | Cursor | TBD | TBD | TBD | TBD |
 
 ```bash
-# $pid の導出と、待機終了後の EXIT=<code> 確認はスキル step 3 に従う
+# $pid の導出と、待機終了後の終了コードの確認はスキル step 3 に従う
 until [ -f "$REPORT" ] || ! kill -0 "$pid" 2>/dev/null; do
   sleep 30
 done
diff --git a/.agents/skills/monitoring-long-tasks/SKILL.md b/.agents/skills/monitoring-long-tasks/SKILL.md
index 4c86e0a..6b7fb2c 100644
--- a/.agents/skills/monitoring-long-tasks/SKILL.md
+++ b/.agents/skills/monitoring-long-tasks/SKILL.md
@@ -9,10 +9,10 @@ Completion (artifact or notification arrived), liveness (target process still ex
 ## Workflow
 
 1. Wait for `report exists OR worker is not alive`; never wait on the report alone. The controller owns this wait and stall polling and keeps its turn until `report exists OR worker is not alive` resolves. A completion notification means a runtime process-exit notification carrying an exit status, not a report, artifact, or sub-agent result. It can satisfy the `worker is not alive` branch, but it is not permission to end the controller's turn while the worker is alive. Use runtime wait or notification facilities, never a foreground sleep loop. The only stop exception is a predeclared read-only PR review delegation past its deadline or progress cutoff (see `Predeclared PR review delegation deadlines`).
-2. Treat exit without the expected report as abnormal: recheck the report once after observed death, then handle as failure and confirm the terminal `EXIT=<code>` in the log.
-3. Prefer a known PID with `kill -0` for liveness. For `verify.sh`, take the numeric suffix from the printed log basename (`verify-<profile>-<timestamp>-<pid>.log`) and validate it against `^[0-9]+$`. After `kill -0` succeeds on a `verify.sh` target, verify the PID's identity: `ps -p <pid> -o args=` contains `scripts/ci/verify.sh`, and `readlink -f /proc/<pid>/cwd` equals the target worktree. If either identity check fails, treat the target worker as not alive; do not fall back to `pgrep` for that PID. For any other target, `kill -0` plus the intended command line and target cwd is enough; do not require `scripts/ci/verify.sh` in args. After either wait condition ends for `verify.sh`, confirm the terminal `EXIT=<code>` in its log.
-4. Use `pgrep -f` only when no PID is available. Match the target command line, and keep the pattern in a script file or use a path-qualified bracket form such as `[s]cripts/ci/verify\.sh` so the pattern text itself cannot match. A bare target path elsewhere in the monitor command can still self-match. Inspect the matches, discard the monitor PID and every ancestor PID. When the target is `verify.sh`, apply step 3's `verify.sh` command/cwd identity to each remaining PID. When it is not, keep PIDs whose command line matches the intended target command and whose cwd is the target worktree. If none remains, the target worker is not alive. Never use the log path as the process marker or match a profile such as `full` alone.
-5. Monitor the log path printed by `verify.sh`; do not require a fixed manual redirect.
+2. Treat exit without the expected report as abnormal: recheck the report once after observed death, then handle as failure and confirm the exit status as in step 3.
+3. Prefer a known PID with `kill -0` for liveness. When the command prints its log path and the log name ends with its PID (for example `<name>-<timestamp>-<pid>.log`), take the numeric suffix from the printed basename and validate it against `^[0-9]+$`. After `kill -0` succeeds, verify the PID's identity: `ps -p <pid> -o args=` contains the intended command, and `readlink -f /proc/<pid>/cwd` equals the target worktree. If either identity check fails, treat the target worker as not alive; do not fall back to `pgrep` for that PID. After either wait condition ends, confirm the terminal `EXIT=<code>` line when the command writes one to its log; otherwise take the exit status from the runtime's process-exit notification.
+4. Use `pgrep -f` only when no PID is available. Match the target command line, and keep the pattern in a script file or use a path-qualified bracket form such as `[.]devcontainer/run-tests[.]bash` so the pattern text itself cannot match. A bare target path elsewhere in the monitor command can still self-match. Inspect the matches, discard the monitor PID and every ancestor PID, and apply step 3's command and cwd identity check to each remaining PID. If none remains, the target worker is not alive. Never use the log path as the process marker or match a bare argument such as a profile name alone.
+5. Monitor the log path the command prints, or the output file the runtime returns; do not require a fixed manual redirect.
 6. Check log mtime, size, or last line about every ten minutes. Two consecutive unchanged checks mean report a stall; a live stalled task is never permission to kill it, except for a predeclared read-only PR review delegation handled under `Predeclared PR review delegation deadlines`.
 7. Report before dispatching dependent work. Every status report carries task identity, actual log path, known or unknown exit status, and last progress.
 
@@ -29,7 +29,7 @@ This is a narrow, predeclared exception to the never-stop-a-live-worker rule. It
 | State | Action |
 | --- | --- |
 | `completed` | Report arrived; consume it and continue. |
-| `exited without report` | Abnormal; recheck report, report failure, confirm `EXIT=<code>`. |
+| `exited without report` | Abnormal; recheck report, report failure, confirm the exit status. |
 | `alive and progressing` | Keep waiting; record latest log position. |
 | `alive but stalled` | Report stall with all four fields; keep the task alive and hold dependents. |
 | `predeclared PR review delegation past deadline` | Stop at its deadline or progress cutoff; confirm once; on unconfirmed stop, report and end the turn without dependents. |
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/monitoring-long-tasks 2>&1 | tail -n 1
git grep -n 'verify\.sh' -- .agents/skills/monitoring-long-tasks .agents/monitoring-runtimes.md
bash tests/scripts/test-instructions.bash
```

Expected: `8 passed`。`git grep` は何も表示しない。`PASS: root instruction files follow spec 5.2 and 5.3`（`AGENTS.md` が参照する `.agents/monitoring-runtimes.md` がある）。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/monitoring-long-tasks/SKILL.md .agents/monitoring-runtimes.md \
  .agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py
git commit -m "refactor(monitoring-long-tasks): generalize the PID and log rules

The PID taken from a printed log name, the identity check (intended command
and target cwd) and the pgrep fallback now apply to any long command that
prints its log path, not to one verification script. EXIT=<code> is confirmed
when the command writes it; otherwise the runtime's exit notification gives
the status. The runtime table follows.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 10: rst-writer の profile を置き換える（仕様 8.2、D-27・D-28）

MaatLog profile（`references/profiles/maatlog.md`）、その fixture（`evals/fixtures/maatlog-env/`）、旧 guide の移行案内（`references/rst-style-guide.md`）を削除する。template 2 本は `assets/create-reso-world/` へ改名して使う。このリポジトリ用の `create-reso-world` profile を足して既定にし、SKILL.md・入力仕様・文書種別表・共通 guide を合わせる。OSS Python Extension profile は未接続のまま、移行元への言及と Issue 番号を外す。evals は MaatLog のケースを削除し、新しい profile のケースと fixture を足す。

**Files:**
- Create: `.agents/skills/rst-writer/tests/test_rst_writer_contract.py`、`.agents/skills/rst-writer/references/profiles/create-reso-world.md`、`.agents/skills/rst-writer/evals/fixtures/repo-env/.gitignore`、`.agents/skills/rst-writer/evals/fixtures/repo-env/docs/resoloop-notes.rst`
- Delete: `.agents/skills/rst-writer/references/profiles/maatlog.md`、`.agents/skills/rst-writer/references/rst-style-guide.md`、`.agents/skills/rst-writer/evals/fixtures/maatlog-env/`（6 ファイル）
- Move: `.agents/skills/rst-writer/assets/maatlog/` → `.agents/skills/rst-writer/assets/create-reso-world/`（中身は変えない）
- Modify: `.agents/skills/rst-writer/SKILL.md`、`references/profile-interface.md`、`references/document-types.md`、`references/rst-core-style-guide.md`、`references/profiles/oss-python-extension.md`、`references/sphinx-semantic-markup.md`、`evals/evals.json`、`evals/README.md`（いずれも `.agents/skills/rst-writer/` からの相対パス）

**Interfaces:**
- Produces: profile 名 `create-reso-world`（省略時の既定）、検査コマンド `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"`、evals の fixture 名 `repo-env`。

- [ ] **Step 1: 失敗するテストを書く**

`.agents/skills/rst-writer/tests/test_rst_writer_contract.py` を次の内容で作る。

```python
"""rst-writer writes this repository's documents by default (spec 8.2).

The profile of the migration source is gone together with its fixtures. The
OSS Python Extension profile stays reserved and unconnected.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / ".agents/skills/rst-writer"
SKILL = SKILL_DIR / "SKILL.md"
PROFILE = SKILL_DIR / "references/profiles/create-reso-world.md"
INTERFACE = SKILL_DIR / "references/profile-interface.md"
TYPES = SKILL_DIR / "references/document-types.md"
CORE = SKILL_DIR / "references/rst-core-style-guide.md"
EVALS = SKILL_DIR / "evals/evals.json"
CHECK = 'uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def names(directory: Path) -> set[str]:
    return {entry.name for entry in directory.iterdir() if entry.name != "__pycache__"}


def test_this_repository_profile_is_the_default() -> None:
    content = read(SKILL)
    assert "省略時の `profile` は `create-reso-world`" in content
    assert "[create-reso-world profile](references/profiles/create-reso-world.md)" in content
    assert "**省略時だけ** `create-reso-world`" in read(INTERFACE)
    assert "**available は create-reso-world の3種だけ**" in read(TYPES)
    # Only this repository's profile and the reserved OSS profile remain.
    assert names(SKILL_DIR / "references/profiles") == {"create-reso-world.md", "oss-python-extension.md"}
    assert names(SKILL_DIR / "assets") == {"create-reso-world", "oss-python-extension"}
    assert names(SKILL_DIR / "evals/fixtures") == {"negative", "oss-extension", "repo-env"}
    assert not (SKILL_DIR / "references/rst-style-guide.md").exists()


def test_profile_drafts_in_docs_draft_without_a_glossary() -> None:
    content = read(PROFILE)
    assert "リポジトリのルートの `docs_draft/<目的に合う名前>.rst`" in content
    assert "用語集（`glossary`）を探したり、作成・照合・追記したりしない" in content
    assert "`:ref:`、`:term:`、`:doc:`" in content
    assert CHECK in content
    assert "`wabun-rst-ulint`）は、この profile では実行しない" in content


def test_core_guide_leaves_the_static_check_to_the_profile() -> None:
    content = read(CORE)
    assert "確定しない profile は、その profile の検査手順に従う" in content
    assert "Sphinx を使わない profile" in content


def test_skill_runs_the_profile_check() -> None:
    assert "uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning" in read(SKILL)


def test_markdown_links_resolve() -> None:
    sources = [SKILL, *sorted((SKILL_DIR / "references").rglob("*.md"))]
    for source in sources:
        for target in re.findall(r"\]\(([^)#]+\.(?:md|rst))\)", read(source)):
            assert (source.parent / target).resolve().is_file(), f"{source.name}: {target}"


def test_templates_named_by_the_document_types_exist() -> None:
    templates = set(re.findall(r"(assets/[a-z-]+/template-[a-z-]+\.rst)", read(TYPES)))
    assert "assets/create-reso-world/template-procedure.rst" in templates
    for template in templates:
        assert (SKILL_DIR / template).is_file(), template


def test_every_eval_uses_existing_fixture_files() -> None:
    evals = json.loads(read(EVALS))["evals"]
    for item in evals:
        assert item["fixture"] in {"oss-extension", "repo-env", "none"}, item["id"]
        for name in item["files"]:
            assert (SKILL_DIR / name).is_file(), f"{item['id']}: {name}"


def test_evals_cover_the_profile_of_this_repository() -> None:
    names = {item["name"] for item in json.loads(read(EVALS))["evals"]}
    assert {"repo-procedure-default", "repo-explanation-explicit-target", "repo-edit-existing"} <= names


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/rst-writer"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/rst-writer"
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/rst-writer 2>&1 | tail -n 1
```

Expected: `7 failed, 2 passed`。リンクの解決と symlink のテストは今の構成を固定するものなので通る。

- [ ] **Step 3: MaatLog のファイルを削除し、template を改名する**

```bash
# 構成の変更（Task 10）
cd "$W"
git rm -rq .agents/skills/rst-writer/references/profiles/maatlog.md .agents/skills/rst-writer/references/rst-style-guide.md \
  .agents/skills/rst-writer/evals/fixtures/maatlog-env
rm -rf .agents/skills/rst-writer/evals/fixtures/maatlog-env   # ignore 対象が残っていれば消す
git mv .agents/skills/rst-writer/assets/maatlog .agents/skills/rst-writer/assets/create-reso-world
```

- [ ] **Step 4: 新しい profile と fixture を作る**

`.agents/skills/rst-writer/references/profiles/create-reso-world.md`:

````markdown
# create-reso-world profile

`profile=create-reso-world`（省略時の既定）に適用する。このリポジトリで RST の文書を書くときの profile である。
RST の構造とラベルは [共通 guide](../rst-core-style-guide.md)、入力と root の解決は [入力仕様](../profile-interface.md) を読む。

## 出力先

- 新規で `target_path` を省略した場合は、リポジトリのルートの `docs_draft/<目的に合う名前>.rst` に置く。`docs_draft/` は git が追跡しないローカルの下書き置き場である（ルート `AGENTS.md` の「ファイルとドラフト」）
- 明示された `target_path` は、新規・既存とも尊重する。相対パスはリポジトリのルート基準で解決する（プロジェクトを cwd にしている場合も同じ）
- 下書きを `docs/` などの追跡される場所へ移すかは依頼者が決める。この profile は勝手に移さない

## 言語と文書構造

既定は日本語・である調とし、明示された `language` を優先する。日本語の文書は、ルート `AGENTS.md` の「日本語表現」に従う。
[文書種別表](../document-types.md) の template を使い、タイトル直後の「概要」で目的を1〜3文で述べ、最終行に装飾なしで単独の「以上」を置く。
他言語ではこの役割に相当する見出しと終端を指定言語で書く（英語なら `Overview` と `End`）。
procedure は前提条件・手順の流れ・手順・結果確認、explanation は概念・構造・比較・関連資料を軸にする。
operational は procedure の簡易版で、前提条件と手順の流れを省略できる。
template の欄は必要な内容で置き換え、無関係な節や未確認の関連 URL を埋め草として残さない。
既存編集は指定箇所の追記・修正を優先し、template で文書全体を置換しない。
句点「。」の直後で改行し、桁数を理由に文の途中を折り返さない。

## コマンドとコード

コマンドの前には、実行の意図を動詞で説明する。
シェルは zsh を前提にし、bash スクリプトの実行など bash が必要な場面だけ bash と書く。
Python の実行例は `uv run` で書き、`python3` を直接書かない。
コードは `::` のリテラルブロックで書く。言語が明確なら `.. code-block:: <言語>`（`bash`、`zsh`、`python`、`json`、`toml`、`text` など）を使ってよい。

## Sphinx を使わない

このリポジトリには Sphinx の build も用語集も無い。docutils だけで解釈できる記法で書く。

- 用語集（`glossary`）を探したり、作成・照合・追記したりしない。専門用語はその場で説明するか、箇条書きやフィールドリストで定義する
- `:ref:`、`:term:`、`:doc:` などの Sphinx の role と、`.. mermaid::` などの Sphinx 拡張の directive は使わない。図が要る場合は表や箇条書きで表す
- 共通 guide のページ・節ラベルの付け方はそのまま守る。同じページの節への参照は、docutils の名前付き参照（`` `結果確認 <page_label_results_>`_ ``）で書く。別のファイルは、リポジトリのルート基準のパスと表示名を本文に書いて示す

## 検査

作成・編集した RST の絶対パスを `TARGET` として、docutils と rstcheck で構文を検査する。
検査用の Python project は作らず、依存も追加しない。

```sh
uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"
```

- 終了コード 0 と `Success! No issues detected.` を確認する。`--report-level warning` を付けるのは、参照されていないラベルなどの INFO を失敗として数えないためである
- 失敗したら本文を直して再実行する。未実行や失敗した検査を成功と報告しない
- 共通 guide の4段階の静的検査（`wabun-rst-ulint`）は、この profile では実行しない。`LINT_PROJECT` を持たないためである。報告では、rstcheck による構文検査だけを行ったと明記する
- Sphinx build は行わない

## 報告

対象パス（リポジトリのルート基準と絶対パス）、実行した検査のコマンド・終了コード・出力の最終行、未実行の検査を報告する。
````

`.agents/skills/rst-writer/evals/fixtures/repo-env/.gitignore`:

```text
/docs_draft/
```

`.agents/skills/rst-writer/evals/fixtures/repo-env/docs/resoloop-notes.rst`（ケース 42 が編集する既存文書。タイトルの上下線は表示幅に合わせて 20 文字）:

```rst
.. _resoloop_notes:

====================
ResoLoop の版の扱い
====================

.. _resoloop_notes_overview:

概要
====

導入する ResoLoop の版をロックファイルで決める理由と、版を変えるときの流れを示す。

.. _resoloop_notes_lock:

ロックファイル
==============

``.devcontainer/resoloop.lock`` が導入する版の正本である。
手元の導入だけを変えると、コンテナを作り直したときにロックの版へ戻る。

.. 評価用のコメント行。編集後も残ること。

.. _resoloop_notes_update:

更新の手順
==========

#. 新しい版を確かめる ::

       resoloop --version

.. _resoloop_notes_out_of_scope:

対象外の節
==========

fork のビルド手順は ``docs/resoloop-fork-workflow.md`` にある。

以上
```

- [ ] **Step 5: 本文・参照文書・evals を直す**

SKILL.md は全体を書き換える。`evals/evals.json` は、MaatLog のケース（id 0、23〜33）を削除し、id 17 と 21 を fixture なしにし、id 2 と 3 の MaatLog への言及を新しい profile に替え、id 40〜42 を足す。既存のケースの書式（1 行の `execution_modes` など）は変えない。

````diff
diff --git a/.agents/skills/rst-writer/SKILL.md b/.agents/skills/rst-writer/SKILL.md
index fa4924e..fe9114d 100644
--- a/.agents/skills/rst-writer/SKILL.md
+++ b/.agents/skills/rst-writer/SKILL.md
@@ -6,7 +6,7 @@ description: Use when creating or editing a single reStructuredText (.rst) docum
 # RST の作成・編集
 
 単一ページを、入力仕様と選択した profile に従って書く。
-現在利用可能なのは **MaatLog** の3種である。OSS Python Extension は予約仕様であり、#393 の統合までは生成に使えない。
+現在利用可能なのは、このリポジトリの文書を書く **create-reso-world** の3種である。OSS Python Extension は予約仕様であり、生成には使えない。
 
 ## 入力を確認する
 
@@ -15,16 +15,16 @@ description: Use when creating or editing a single reStructuredText (.rst) docum
 自然言語依頼も同じ仕様で整理し、明示値を推論・既定値より優先する。
 
 入力仕様の順に、明示値の整合、必要情報、profile の利用可能性、root と変更対象、必要なリソースを確認する。
-省略時の `profile` は `maatlog`。空値や未知値を省略扱いしない。
-不足・不整合・未接続・リソースの欠落では、具体的な問題と必要な次の入力を返し、文書生成・用語集更新・lint を行わない。
+省略時の `profile` は `create-reso-world`。空値や未知値を省略扱いしない。
+不足・不整合・未接続・リソースの欠落では、具体的な問題と必要な次の入力を返し、文書生成・検査を行わない。
 
 ## 利用可能なリソースを読む
 
-MaatLog の確認を通った場合だけ、以下を読む。
+create-reso-world の確認を通った場合だけ、以下を読む。
 
-1. [共通 RST guide](references/rst-core-style-guide.md): ページ・節ラベル、構造、参照、表・リスト、インライン記法、4段階の静的検査
-2. [MaatLog profile](references/profiles/maatlog.md): 文体、出力先、用語集、コード・図、検査方針
-3. [文書種別表](references/document-types.md) が指定する `assets/maatlog/` の template
+1. [共通 RST guide](references/rst-core-style-guide.md): ページ・節ラベル、構造、参照、表・リスト、インライン記法
+2. [create-reso-world profile](references/profiles/create-reso-world.md): 出力先、文体、コード、Sphinx を使わない書き方、検査
+3. [文書種別表](references/document-types.md) が指定する `assets/create-reso-world/` の template
 
 `procedure` と `operational` は手順書 template、`explanation` は解説書 template を使う。
 既存編集では指定ファイルを読み、その内容を保持して依頼の変更を加える。
@@ -32,19 +32,17 @@ MaatLog の確認を通った場合だけ、以下を読む。
 ## 作成・編集と検査
 
 1. 確定した言語・種別・対象パスに従って作成または編集する。
-   新規・出力先省略時の draft は選択した **親 checkout** の `docs_draft/` に置く。
-2. MaatLog profile に従って本文の全出現の専門用語をマークし、選択した **公開 checkout** の `docs/glossary.rst` と照合する。
-   今回本文で使った未定義語だけ既存用語集へ追記する。
-3. 公開 checkout を uv project に指定し、作成・編集した RST の絶対パスに共通 guide の4検査を実行する。
-   用語集にも同じ検査を行うのは、今回用語集を編集した場合だけである。
-4. 最終差分と終了値を確認し、対象パス、用語集の変更有無、実行した検査と結果を報告する。
-   解決した親 root・公開 root・cwd・uv project を記録し、未実行・失敗・不足を区別する。
+   新規・出力先省略時の draft は、リポジトリのルート（`git rev-parse --show-toplevel`）の `docs_draft/` に置く。
+2. 用語集は探さず、作成・照合もしない。専門用語はその場で説明する。
+3. 作成・編集した RST の絶対パスに、profile の検査 `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning` を実行する。
+4. 最終差分と終了値を確認し、対象パスと、実行した検査と結果を報告する。
+   解決したリポジトリのルートと cwd を記録し、未実行・失敗・不足を区別する。
 
 ## 取り違えやすい点
 
 | 状況 | 判断 |
 |---|---|
-| 親 cwd から呼び出された | draft の親 root と用語集・lint の公開 root を分けて確認する |
+| ワールドのプロジェクト（`slum02/` など）を cwd にして呼び出された | draft の置き場はリポジトリのルートの `docs_draft/` である |
 | 出力先や言語が明示された | profile の既定値で置換しない |
-| OSS 用ファイルが存在する | 種別表が reserved の間は統合待ちで停止する |
-| 旧 guide を指定された | [移行案内](references/rst-style-guide.md) から共通 guide と MaatLog profile を読む |
+| OSS 用ファイルが存在する | 種別表が reserved の間は未接続として停止する |
+| `:ref:` や `:term:` を使いたくなった | Sphinx は無い。profile の「Sphinx を使わない」に従う |
diff --git a/.agents/skills/rst-writer/evals/README.md b/.agents/skills/rst-writer/evals/README.md
index eac084e..01540f4 100644
--- a/.agents/skills/rst-writer/evals/README.md
+++ b/.agents/skills/rst-writer/evals/README.md
@@ -5,11 +5,13 @@ rst-writer の eval セットと、それを実行・採点する手順である
 
 専用の自動 runner は存在しない。利用可能な agent harness（Claude Code / Codex / Devin 等の subagent 実行）で1件ずつ実行し、証跡を保存して採点する。`run_eval.py` は description の trigger 評価用であり、RST 生成の評価には使わない。
 
+OSS Python Extension のケース（`oss-extension` fixture）と本書の OSS の手順は、移行元のリポジトリで作成した評価の記録である。`#393` などの番号は移行元の Issue を指す。`entrypoint_before_393` / `entrypoint_after_393` は「OSS profile の接続前 / 接続後」と読み替える。このリポジトリでは OSS profile を接続していないので、entrypoint の OSS のケースは接続前の期待（`stopped-unavailable` など）で採点する。
+
 ## 構成
 
 ```
 evals/
-  evals.json                  39ケースの定義（id 5 は欠番）
+  evals.json                  30ケースの定義（id 0・5・23〜33 は欠番）
   README.md                   本書
   fixtures/
     oss-extension/            架空 Sphinx 拡張 project（queue_ext）
@@ -21,10 +23,9 @@ evals/
       docs/                   正常な Sphinx source tree
       variants/ja/docs/       日本語版 docs tree 全体
       HISTORY.txt             架空履歴の正本（0.1.0 / 0.2.0）
-    maatlog-env/              架空の親/公開 repository 一式
-      .gitmodules             public → usaturn/maatlog（識別用）
-      public/pyproject.toml, uv.lock  MaatLog lint project
-      public/docs/glossary.rst, existing.rst
+    repo-env/                 create-reso-world profile 用の一時リポジトリの素材
+      .gitignore              /docs_draft/
+      docs/resoloop-notes.rst 既存文書の編集ケース（42）の対象
       prompts/exclusions.rst.txt      markup 対象外の入力資料
     negative/*.rst.txt        7種の負例断片（正常 tree には混ぜない）
 ```
@@ -35,7 +36,7 @@ evals/
 
 | フィールド | 意味 |
 |---|---|
-| `fixture` | `oss-extension` / `maatlog-env` / `none`（停止ケース等） |
+| `fixture` | `oss-extension` / `repo-env` / `none`（停止ケース等） |
 | `execution_modes` | 適用する mode（下記）の配列 |
 | `setup` | 評価者が実行前に case コピーへ施す準備（ページ除去・variant 適用・linter 除去等）。なければ `[]` |
 | `expected_status` | mode ごとの期待状態。`component` / `entrypoint_before_393` / `entrypoint_after_393` |
@@ -58,9 +59,9 @@ component では `expected_status.component`、entrypoint では統合前後に
 
 - **input/routing**: 6入力（`profile` / `document_type` / `target_path` / `language` / `audience` / `package_name`）を正しく解釈し、target と template の選択根拠を記録した。
 - **RST/content**: 生成物が実装・fixture の事実（型・default・引数・表示）と一致する。言語・文書種別の役割を守る。
-- **semantic**: OSS では参照が正しい定義先へ解決し、Sphinx `-n` で未解決・重複定義がない。MaatLog では本文の `:term:` が公開側 glossary の定義へ解決することを照合し、Sphinx build は要求しない。ただし case 39 の setup で対象外の toctree に注入した `nonexistent-page` の警告だけは case 不合格にせず、`document_validation=failed` に記録する。
-- **scope/glossary**: 許可された source だけを変更した（OSS は target 1ページ。MaatLog は target + 本文使用分の glossary）。before/after hash と diff で判断する。
-- **workflow**: harness の実コマンド記録とログで、OSS は原則として対象の4段階 lint と既存 build 優先の build、MaatLog は公開 project による対象の4段階 lint を確認する。順序・flags・対象を確認し、列挙だけの自己申告は証拠にしない。case 38 は linter を借用せず lint 未検証と記録して build を行い、case 39 は失敗した build のログを残す。
+- **semantic**: OSS では参照が正しい定義先へ解決し、Sphinx `-n` で未解決・重複定義がない。create-reso-world では Sphinx の role を使っていないことを確認し、Sphinx build は要求しない。ただし case 39 の setup で対象外の toctree に注入した `nonexistent-page` の警告だけは case 不合格にせず、`document_validation=failed` に記録する。
+- **scope**: 許可された source だけを変更した（どちらの profile も target 1ページ。create-reso-world は用語集を探さず、作らない）。before/after hash と diff で判断する。
+- **workflow**: harness の実コマンド記録とログで、OSS は原則として対象の4段階 lint と既存 build 優先の build、create-reso-world は対象への `rstcheck --report-level warning`（`uv run --no-project --with docutils --with rstcheck`）を確認する。順序・flags・対象を確認し、列挙だけの自己申告は証拠にしない。case 38 は linter を借用せず lint 未検証と記録して build を行い、case 39 は失敗した build のログを残す。
 - **reporting**: 最終報告が実際のログと一致し、未実行・失敗・環境不足を明示する。警告を黙殺しない。
 
 選択した条件がすべて合格したときだけ `case_status=pass` とする。期待どおりの `stopped-blocked` は `case_status=pass`、`document_validation=not-run` にできる。`case_status=blocked` は期待した停止ではなく、実行前の環境不足などで採点を開始できない場合に使う。実行自体がない場合は `not-run` とし、どちらも pass に換算しない。実行したが必須の証跡が残らなかった場合は fail とする。
@@ -79,7 +80,7 @@ component では `expected_status.component`、entrypoint では統合前後に
 - `generated` — 指定 target の作成/編集と検証まで完了する
 - `stopped-unavailable` — OSS profile 未接続を正しく報告して停止（pre-integration gate の成功）
 - `stopped-input` — 入力不足・未知値・矛盾を正しく報告して停止
-- `stopped-blocked` — glossary 欠落などのリソース不足、または宣言された Sphinx 制約が 9.1 未満を許す対象外の project（case22）を正しく報告して停止
+- `stopped-blocked` — リソースの不足、または宣言された Sphinx 制約が 9.1 未満を許す対象外の project（case22）を正しく報告して停止
 - `generated-with-caveat` — 生成は行うが lint 未検証等を正直に報告する（case38）
 - `reported-failure` — 指定外の問題で build が失敗することを正しく報告する（case39）。`document_validation` は failed のまま
 
@@ -116,24 +117,21 @@ uv run --project "$OSS_CASE" sphinx-build -n -W --keep-going -b html "$OSS_CASE/
 | no-linter | `rm -rf "$OSS_CASE/lint"`（linter を提供しない project。兄弟 copy には存在する）。この case では共通準備の `LINT_PROJECT=$OSS_CASE/lint` を executor に指定しない | 38 |
 | objects-canonical-split | `docs/objects.rst` から当該 object の定義ブロックを除去し、対象 reference ページを正本にする | 4, 6, 7, 8 |
 
-### MaatLog synthetic roots
+### create-reso-world の一時リポジトリ
 
 ```sh
-MAAT_CASE=$(mktemp -d /tmp/rst-writer-maatlog-XXXXXX)
-mkdir -p "$MAAT_CASE/parent"
-cp -R "$FIXTURES/maatlog-env" "$MAAT_CASE/parent/maatlog"
-git -C "$MAAT_CASE/parent/maatlog" init -q
-git -C "$MAAT_CASE/parent/maatlog" remote add origin https://github.com/usaturn/maatlog-poc.git
-git -C "$MAAT_CASE/parent/maatlog/public" init -q
-git -C "$MAAT_CASE/parent/maatlog/public" remote add origin https://github.com/usaturn/maatlog.git
-uv sync --project "$MAAT_CASE/parent/maatlog/public" --locked --python 3.14
-git -C "$MAAT_CASE/parent/maatlog/public" rev-parse --show-toplevel
+REPO_CASE=$(mktemp -d /tmp/rst-writer-repo-XXXXXX)
+cp -R "$FIXTURES/repo-env/." "$REPO_CASE/"
+git -C "$REPO_CASE" init -q
+git -C "$REPO_CASE" remote add origin https://github.com/usaturn/create-reso-world.git
+git -C "$REPO_CASE" add -A
+git -C "$REPO_CASE" -c user.name=eval -c user.email=eval@example.com commit -qm fixture
+uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$REPO_CASE/docs/resoloop-notes.rst"
 ```
 
-最後の出力が `$MAAT_CASE/parent/maatlog/public` 自身であることを確認する。remote には skill の root 照合を通る URL をローカル設定文字列として記録し、fetch/push/submodule 取得は行わない。executor には `ENV_ROOT=$MAAT_CASE/parent/maatlog`、`APP_ROOT=$MAAT_CASE/parent/maatlog/public`、`LINT_PROJECT=$APP_ROOT` と、利用する skill snapshot の場所を明示する。実リポジトリの `public/` や共有 checkout へ戻らないことを監査する。
+最後の検査が exit 0 であることを確認する。remote は skill の root 確認を通すためのローカル設定であり、fetch/push は行わない。executor の cwd は `$REPO_CASE`（case 41 は setup で作る `$REPO_CASE/slum02`）とし、実リポジトリへ戻らないことを監査する。
 
-- glossary 非存在 variant（case25）: `rm "$MAAT_CASE/parent/maatlog/public/docs/glossary.rst"`
-- 既定 draft 先: `$MAAT_CASE/parent/maatlog/docs_draft/`（実行前は無くてよい）
+- 既定 draft 先: `$REPO_CASE/docs_draft/`（実行前は無くてよい）
 
 ## 負例（fixture-validation）
 
@@ -151,7 +149,7 @@ git -C "$MAAT_CASE/parent/maatlog/public" rev-parse --show-toplevel
 
 各負例で非0を確認したあと、改めて fresh normal copy で exit 0 を再確認する。`set -e` 環境では `if command; then status=0; else status=$?; fi` で終了値を保持し、`tee` へ流すなら `PIPESTATUS[0]` を記録する。
 
-4段階 lint の不動点も、負例や agent 実行とは別の fresh copy で確認する。OSS の通常 `docs/` と ja variant の `docs/` は、それぞれ全 `.rst` の実行前 hash を記録し、`LINT_PROJECT=$OSS_CASE/lint` で共通 guide の4コマンドを各ファイルに指定順・flags のまま実行する。MaatLog の `public/docs/existing.rst` と `public/docs/glossary.rst` には `LINT_PROJECT=$APP_ROOT` を使う。全コマンドが exit 0 で、実行後の hash と差分が各 baseline と一致することを確認する。ja variant は別 copy に適用し、通常 tree を上書きしない。
+4段階 lint の不動点も、負例や agent 実行とは別の fresh copy で確認する。OSS の通常 `docs/` と ja variant の `docs/` は、それぞれ全 `.rst` の実行前 hash を記録し、`LINT_PROJECT=$OSS_CASE/lint` で共通 guide の4コマンドを各ファイルに指定順・flags のまま実行する。全コマンドが exit 0 で、実行後の hash と差分が各 baseline と一致することを確認する。ja variant は別 copy に適用し、通常 tree を上書きしない。
 
 ## 実行手順（component / entrypoint / control）
 
diff --git a/.agents/skills/rst-writer/evals/evals.json b/.agents/skills/rst-writer/evals/evals.json
index 6580fb9..2a271bc 100644
--- a/.agents/skills/rst-writer/evals/evals.json
+++ b/.agents/skills/rst-writer/evals/evals.json
@@ -1,30 +1,6 @@
 {
   "skill_name": "rst-writer",
   "evals": [
-    {
-      "id": 0,
-      "name": "generic-explanation",
-      "prompt": "遅延再試行とキューの関係を解説する .rst 文書を作成してください。遅延再試行の発生条件・待機時間・試行上限・失敗時の扱いも説明してください。document_type=explanation、language=ja。作業対象は評価者が用意した MaatLog 構成（親/公開）で、新規 draft は親の docs_draft/ 配下に置き、専門用語は公開側の docs/glossary.rst と照合してください。変更ファイル・用語集の変更有無・実行した検査と結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の日本語解説書。遅延再試行の4要素を説明し、読点を4つ以上使って語句を列挙する場合は箇条書きまたはフィールドリストで整理する。既存のキュー/queue 別名は追記なしで本文全出現を :term: 化し、新語の遅延再試行だけを既存 glossary へ追記。作成ファイルと編集した glossary に4段階 lint。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "作成先は親 checkout の docs_draft/ 配下であり、先頭ラベル・概要・末尾単独の「以上」を含む RST 構造になっている",
-        "本文で使ったキュー/queue と遅延再試行の全出現が :term: でマークされている（コード・見出し等の対象外を除く）",
-        "公開側 docs/glossary.rst には遅延再試行のエントリだけが追記され、キュー/queue・監査ログの既存エントリは不変である",
-        "日本語の地の文は一文あたりの読点「、」が3つ以下である（コード・リテラル・図・list-table セル内は対象外）",
-        "読点「、」を4つ以上使って語句を列挙する箇所は箇条書きまたはフィールドリストに分解されている",
-        "実コマンド記録が inline-spacing→strong-spacing→sentence-breaks→heading-width の4段階を --fix で（最後のみ --backup-suffix .bak）、作成ファイルと編集した glossary の両方に示す",
-        "uv project として公開 checkout（APP_ROOT）が使われ、親 project や他環境を代用していない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
     {
       "id": 1,
       "name": "oss-landing",
@@ -51,7 +27,7 @@
       "id": 2,
       "name": "oss-quickstart-en",
       "prompt": "profile=oss-python-extension, document_type=quickstart, target_path=docs/quickstart.rst, language=en. Expand this page into a short quickstart for the supplied extension project: enable the extension, run a minimal queue-summary example, and show the expected output. Use the project's real sample or code where helpful. Report the files changed and the actual validation results.",
-      "expected_output": "English quickstart that flows intro -> configure -> run -> expected output, uses console/python code blocks appropriately, and does not import MaatLog-only conventions.",
+      "expected_output": "English quickstart that flows intro -> configure -> run -> expected output, uses console/python code blocks appropriately, and does not import the conventions of the create-reso-world profile.",
       "files": [
         "evals/fixtures/oss-extension/docs/quickstart.rst",
         "evals/fixtures/oss-extension/docs/conf.py",
@@ -62,7 +38,7 @@
       "assertions": [
         "The page leads with a short introduction, then shows configuration, then how to run it, then the expected output",
         "Code blocks use language-appropriate directives (e.g. console/python), and any shown API usage matches the real source",
-        "No MaatLog-only conventions appear (fixed 概要 section, trailing 以上, or Japanese-only style rules) in the English page",
+        "No create-reso-world profile conventions appear (fixed 概要 section, trailing 以上, or Japanese-only style rules) in the English page",
         "Only docs/quickstart.rst changed; command records show the four lint steps in order then the project build with exit 0 and no warnings"
       ],
       "fixture": "oss-extension",
@@ -74,7 +50,7 @@
       "id": 3,
       "name": "oss-quickstart-ja",
       "prompt": "profile=oss-python-extension, document_type=quickstart, target_path=docs/quickstart.rst, language=ja. Expand this page into a short quickstart matching the project's existing documentation style: enable the extension, run a minimal queue-summary example, and show the expected output. Report the files changed and the actual validation results.",
-      "expected_output": "Japanese quickstart in the project's existing style (no MaatLog-only 概要/以上 conventions), covering intro -> configure -> run -> expected output, with the four lint steps and a warning-free build.",
+      "expected_output": "Japanese quickstart in the project's existing style (no 概要/以上 conventions of the create-reso-world profile), covering intro -> configure -> run -> expected output, with the four lint steps and a warning-free build.",
       "files": [
         "evals/fixtures/oss-extension/variants/ja/docs/quickstart.rst",
         "evals/fixtures/oss-extension/variants/ja/docs/index.rst",
@@ -83,7 +59,7 @@
       ],
       "assertions": [
         "The written page is natural Japanese consistent with the project's existing style and document-type role",
-        "MaatLog-only conventions are not applied (no forced 概要 section or trailing standalone 以上)",
+        "The create-reso-world profile conventions are not applied (no forced 概要 section or trailing standalone 以上)",
         "Configuration/run/output content matches the real extension (extension name, directive, expected result)",
         "Only docs/quickstart.rst changed; command records show the four lint steps in order then the project build with exit 0 and no warnings"
       ],
@@ -376,15 +352,13 @@
       "name": "unknown-profile",
       "prompt": "profile=unknown-service-profile, document_type=explanation, target_path=docs_draft/notes.rst, language=ja. 与えられた環境で解説文書を作成してください。変更ファイルと検査結果を報告してください。",
       "expected_output": "No files are created or modified. The reply reports that the given profile is unknown and states what input is needed next.",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst"
-      ],
+      "files": [],
       "assertions": [
         "The reply names the unknown profile value and the information needed to proceed",
-        "No RST file is created, no glossary is touched, no .bak is produced, and no lint command was run",
+        "No RST file is created, no .bak is produced, and no check command was run",
         "The agent did not silently substitute a default or known profile"
       ],
-      "fixture": "maatlog-env",
+      "fixture": "none",
       "execution_modes": ["component", "entrypoint"],
       "setup": [],
       "expected_status": {"component": "stopped-input", "entrypoint_before_393": "stopped-input", "entrypoint_after_393": "stopped-input"}
@@ -447,16 +421,14 @@
       "id": 21,
       "name": "empty-profile",
       "prompt": "profile='', document_type=procedure, language=ja. 与えられた環境で手順書を作成してください。変更ファイルと検査結果を報告してください。",
-      "expected_output": "No files are created. The reply reports that an empty profile value is invalid input, without converting it to the maatlog default.",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst"
-      ],
+      "expected_output": "No files are created. The reply reports that an empty profile value is invalid input, without converting it to the create-reso-world default.",
+      "files": [],
       "assertions": [
         "The reply identifies the empty profile string as a missing/invalid value rather than an omitted one",
-        "profile=maatlog was not silently assumed",
-        "No file is created, no glossary is touched, and no lint was run"
+        "profile=create-reso-world was not silently assumed",
+        "No file is created and no check command was run"
       ],
-      "fixture": "maatlog-env",
+      "fixture": "none",
       "execution_modes": ["component", "entrypoint"],
       "setup": [],
       "expected_status": {"component": "stopped-input", "entrypoint_before_393": "stopped-input", "entrypoint_after_393": "stopped-input"}
@@ -482,228 +454,6 @@
       "setup": ["set needs_sphinx = \"7.4\" in docs/conf.py (the build env stays Sphinx 9.1.0)"],
       "expected_status": {"component": "stopped-blocked", "entrypoint_before_393": "stopped-unavailable", "entrypoint_after_393": "stopped-blocked"}
     },
-    {
-      "id": 23,
-      "name": "glossary-alias-reuse",
-      "prompt": "キューの働きを解説する .rst 文書を作成してください。document_type=explanation、language=ja。本文では「キュー」と「queue」の両表記を使います。作業対象は評価者が用意した MaatLog 構成で、新規 draft は親 docs_draft/ 配下、用語は公開側 docs/glossary.rst と照合してください。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の日本語解説書。キュー/queue の全出現が :term: でマークされ、既存エントリの別名として解決するため glossary 追記はゼロ。glossary 未編集なら lint 対象外。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "本文中のキュー/queue の全出現が :term: でマークされ、同一エントリの別名として解決している（表示名とキーの使い分けを含む）",
-        "公開側 docs/glossary.rst は byte 不変（新規エントリも別名重複もない）",
-        "glossary を編集していないので lint は作成ファイルのみに4段階で実行された",
-        "監査ログなど本文に出ない既存語や、他文書の語を先回りで追加していない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 24,
-      "name": "glossary-markup-exclusions",
-      "prompt": "添付資料（prompts/exclusions.rst.txt）を題材に、キューの振る舞いを解説する .rst 文書を作成してください。document_type=explanation、language=ja。作業対象は評価者が用意した MaatLog 構成で、新規 draft は親 docs_draft/ 配下、用語は公開側 docs/glossary.rst と照合してください。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の日本語解説書。キュー は地の文の全出現だけ :term: で、見出し・コード・リテラル・Mermaid 内は無変更。新語は本文使用分のみ glossary へ追記。",
-      "files": [
-        "evals/fixtures/maatlog-env/prompts/exclusions.rst.txt",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/public/pyproject.toml"
-      ],
-      "assertions": [
-        "地の文のキュー の全出現が :term: でマークされている",
-        "見出し・code-block・literal block・inline literal・Mermaid 内の同じ語はマークされず残っている（list-table セルは任意）",
-        "glossary への追記は本文で実際に使った未定義語だけであり、対象外箇所の語を理由に増やしていない",
-        "lint が作成ファイルと（編集した場合のみ）glossary に4段階で実行された"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 25,
-      "name": "maatlog-missing-glossary",
-      "prompt": "キューの役割を解説する .rst 文書を作成してください。document_type=explanation、language=ja。作業対象は評価者が用意した MaatLog 構成で、新規 draft は親 docs_draft/ 配下に置き、用語は公開側 docs/glossary.rst と照合してください。変更ファイルと検査結果を報告してください。",
-      "expected_output": "No files are created. The reply reports that APP_ROOT/docs/glossary.rst is missing, states the needed repair, and does not substitute the parent glossary or create a new one.",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "The reply identifies docs/glossary.rst as missing in the public checkout and states the required repair",
-        "Neither the parent docs/glossary.rst nor a newly created glossary is used as a substitute",
-        "No draft is created and no lint was run"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint"],
-      "setup": ["remove public/docs/glossary.rst from the MaatLog copy"],
-      "expected_status": {"component": "stopped-blocked", "entrypoint_before_393": "stopped-blocked", "entrypoint_after_393": "stopped-blocked"}
-    },
-    {
-      "id": 26,
-      "name": "maatlog-procedure-default",
-      "prompt": "キューの滞留を解消する手順書を作成してください。document_type=procedure、language=ja。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の手順書（procedure template 構成: 前提条件・手順の流れ・実施手順・結果確認）。lint project は公開 checkout。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "出力先は親 checkout の docs_draft/ で、procedure の構成（前提条件・手順の流れ・実施手順・結果確認）に従う",
-        "用語集照合は公開側 docs/glossary.rst で行い、本文使用分の未定義語だけ追記された",
-        "lint は公開 project を uv project として作成ファイル（と編集時のみ glossary）に4段階で実行された",
-        "親/公開の取り違えがない（draft が公開側や lint が親 project になっていない）"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 27,
-      "name": "maatlog-procedure-explicit",
-      "prompt": "profile=maatlog、document_type=procedure、language=ja。キューの滞留を解消する手順書を作成してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の手順書。profile 明示時も省略時と同じ仕様（構成・出力先・用語集・lint project）で、公開/親の取り違えなし。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "出力先は親 checkout の docs_draft/ で、procedure の構成に従う",
-        "用語集照合・追記範囲・lint project の選択は省略時（id 26）と同じ仕様である",
-        "親/公開の取り違えがない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 28,
-      "name": "maatlog-explanation-default",
-      "prompt": "document_type=explanation、language=ja、target_path=docs_draft/queue-model.rst。キューの構造を解説する文書を作成してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "明示された docs_draft/queue-model.rst に解説書（explanation 構成）。明示 target_path が既定命名に置き換えられない。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "出力先は明示された docs_draft/queue-model.rst であり、profile 既定の命名で置き換えられていない",
-        "explanation の構成（概念・構造・比較・関連資料）に従う",
-        "用語集照合と lint の対象・project は既定仕様どおり"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 29,
-      "name": "maatlog-explanation-explicit",
-      "prompt": "profile=maatlog、document_type=explanation、language=ja、target_path=docs_draft/queue-model.rst。キューの構造を解説する文書を作成してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "明示 target_path の解説書。profile 明示時も省略時と同じ仕様で、暗黙の procedure 化や置き換えなし。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "出力先は docs_draft/queue-model.rst で、explanation 構成のまま procedure 化していない",
-        "profile 明示による仕様差はなく、用語集・lint の扱いは省略時と同じ",
-        "親/公開の取り違えがない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 30,
-      "name": "maatlog-operational-default",
-      "prompt": "document_type=operational、language=ja。キューの待機件数を確認する短い手順を作成してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の短い確認手順（procedure 共用 template、不要な前提条件・手順の流れは省略可）で、確認結果が示される。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "operational は procedure の簡易版として書かれ、不要な前提条件や手順の流れが無理に埋められていない",
-        "確認結果を示す節があり、出力先は親 docs_draft/ である",
-        "用語集・lint の扱いは既定仕様どおり"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 31,
-      "name": "maatlog-operational-explicit",
-      "prompt": "profile=maatlog、document_type=operational、language=ja。キューの待機件数を確認する短い手順を作成してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "親 docs_draft/ 配下の短い確認手順。profile 明示時も省略時と同じ operational 仕様。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/pyproject.toml",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/.gitmodules"
-      ],
-      "assertions": [
-        "出力先・構成・用語集・lint の扱いは省略時（id 30）と同じ仕様である",
-        "親/公開の取り違えがない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 32,
-      "name": "maatlog-edit-default",
-      "prompt": "公開 checkout の docs/existing.rst の「対象節」だけを、遅延再試行の扱いを追記して更新してください。language=ja。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "指定節だけが更新され、先頭ラベル・対象外の節・コメントは保持される。遅延再試行は新語として既存 glossary へ追記。親 checkout へはコピーしない。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/existing.rst",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/public/pyproject.toml"
-      ],
-      "assertions": [
-        "変更は「対象節」のみで、先頭ラベル・「対象外の節」・コメント行は保持される",
-        "編集は公開 checkout 内の指定ファイルに限定され、親 checkout へ複写・反映していない",
-        "本文で使った遅延再試行だけが既存 glossary へ追記された",
-        "lint は編集した existing.rst と glossary に4段階で実行された"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
-    {
-      "id": 33,
-      "name": "maatlog-edit-explicit",
-      "prompt": "profile=maatlog、language=ja。公開 checkout の docs/existing.rst の「対象節」だけを、遅延再試行の扱いを追記して更新してください。作業対象は評価者が用意した MaatLog 構成です。変更ファイル・用語集の変更有無・検査結果を報告してください。",
-      "expected_output": "指定節だけが更新され番兵は保持される。profile 明示時も省略時と同じ編集境界で、実際に編集した glossary だけが lint 対象に加わる。",
-      "files": [
-        "evals/fixtures/maatlog-env/public/docs/existing.rst",
-        "evals/fixtures/maatlog-env/public/docs/glossary.rst",
-        "evals/fixtures/maatlog-env/public/pyproject.toml"
-      ],
-      "assertions": [
-        "編集境界は省略時（id 32）と同じで、番兵（ラベル・対象外節・コメント）が保持される",
-        "実際に編集した glossary だけが lint 対象に追加された（未編集の他ファイルは対象外）",
-        "親/公開の取り違えがない"
-      ],
-      "fixture": "maatlog-env",
-      "execution_modes": ["component", "entrypoint", "control"],
-      "setup": [],
-      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
-    },
     {
       "id": 34,
       "name": "missing-oss-type",
@@ -819,6 +569,59 @@
       "setup": ["add 'nonexistent-page' as an entry in the docs/index.rst toctree (missing-document injection outside the target)"],
       "expected_status": {"component": "reported-failure", "entrypoint_before_393": "stopped-unavailable", "entrypoint_after_393": "reported-failure"},
       "artifact_requirements": ["the failing build log must be preserved; document_validation=failed is the expected state"]
+    },
+    {
+      "id": 40,
+      "name": "repo-procedure-default",
+      "prompt": "Blender で作ったメッシュを resoloop でワールドへ反映する手順書を作成してください。document_type=procedure、language=ja。作業対象は評価者が用意したこのリポジトリの複製で、cwd はそのルートです。変更ファイルと検査結果を報告してください。",
+      "expected_output": "リポジトリのルートの docs_draft/ 配下の日本語手順書（前提条件・手順の流れ・手順・結果確認）。用語集は探さず、rstcheck の構文検査が exit 0。",
+      "files": [],
+      "assertions": [
+        "作成先はリポジトリのルートの docs_draft/ 配下で、先頭ラベル・概要・前提条件・手順の流れ・手順・結果確認・末尾単独の「以上」を持つ",
+        "用語集（glossary）を探したり、作成・編集したりしていない",
+        "Sphinx の role（:ref: / :term: / :doc:）や Sphinx 拡張の directive を使っていない",
+        "実コマンド記録に uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning <作成ファイル> があり、exit 0 である",
+        "作成ファイル以外の source を変更していない"
+      ],
+      "fixture": "repo-env",
+      "execution_modes": ["component", "entrypoint", "control"],
+      "setup": [],
+      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
+    },
+    {
+      "id": 41,
+      "name": "repo-explanation-explicit-target",
+      "prompt": "profile=create-reso-world、document_type=explanation、target_path=docs_draft/world-projects.rst、language=ja。ワールドのプロジェクトとリポジトリの関係（プロジェクトを cwd にしてエージェントを起動すること、共有スキルの置き場所）を解説してください。作業対象は評価者が用意したこのリポジトリの複製で、cwd はその中のプロジェクト slum02/ です。変更ファイルと検査結果を報告してください。",
+      "expected_output": "リポジトリのルート基準の docs_draft/world-projects.rst に日本語の解説書。explanation template の構成に従い、rstcheck の構文検査が exit 0。",
+      "files": [],
+      "assertions": [
+        "作成先はリポジトリのルート基準の docs_draft/world-projects.rst であり、cwd のプロジェクト slum02/ の下ではない",
+        "explanation template の構成（概要・トピックの節・関連資料・末尾単独の「以上」）に従い、未確認の関連 URL を埋め草として残していない",
+        "用語集の照合・追記をしていない",
+        "作成ファイルに rstcheck を --report-level warning で実行し、exit 0 を記録している"
+      ],
+      "fixture": "repo-env",
+      "execution_modes": ["component", "entrypoint", "control"],
+      "setup": ["mkdir slum02 (the cwd of the executor)"],
+      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
+    },
+    {
+      "id": 42,
+      "name": "repo-edit-existing",
+      "prompt": "docs/resoloop-notes.rst の「更新の手順」節だけを、ロックファイルを更新してコミットしてから導入し直す流れを追記して更新してください。language=ja。作業対象は評価者が用意したこのリポジトリの複製です。変更ファイルと検査結果を報告してください。",
+      "expected_output": "指定節だけが更新され、先頭ラベル・他の節・コメント行は保持される。docs_draft/ に複製は作らない。編集したファイルに rstcheck の構文検査が exit 0。",
+      "files": [
+        "evals/fixtures/repo-env/docs/resoloop-notes.rst"
+      ],
+      "assertions": [
+        "変更は「更新の手順」節だけで、先頭ラベル・「ロックファイル」「対象外の節」・コメント行は保持される",
+        "編集は docs/resoloop-notes.rst に限られ、docs_draft/ に複製を作っていない",
+        "編集したファイルに rstcheck を --report-level warning で実行し、exit 0 を記録している"
+      ],
+      "fixture": "repo-env",
+      "execution_modes": ["component", "entrypoint", "control"],
+      "setup": [],
+      "expected_status": {"component": "generated", "entrypoint_before_393": "generated", "entrypoint_after_393": "generated"}
     }
   ]
 }
diff --git a/.agents/skills/rst-writer/references/document-types.md b/.agents/skills/rst-writer/references/document-types.md
index 63d311f..a9b27fb 100644
--- a/.agents/skills/rst-writer/references/document-types.md
+++ b/.agents/skills/rst-writer/references/document-types.md
@@ -1,46 +1,43 @@
 # 文書種別とリソース
 
 `profile` と `document_type` の組で選ぶ。入力の解決と停止条件は [入力仕様](profile-interface.md) に従う。
-**available は MaatLog の3種だけ**である。ファイルが存在することと、profile が利用可能であることを区別する。
+**available は create-reso-world の3種だけ**である。ファイルが存在することと、profile が利用可能であることを区別する。
 
-## MaatLog — available
+## create-reso-world — available
 
-`profile` 省略時と明示 `maatlog` は同じ表を使う。
-共通 guide と [MaatLog profile](profiles/maatlog.md) を読み、該当する template を選ぶ。
+`profile` 省略時と明示 `create-reso-world` は同じ表を使う。
+共通 guide と [create-reso-world profile](profiles/create-reso-world.md) を読み、該当する template を選ぶ。
 
 | document_type | 選択基準・構造 | template（skill root 基準） |
 |---|---|---|
-| `procedure` | 構築・変更・復元。前提条件、手順の流れ、実施手順と結果確認 | [assets/maatlog/template-procedure.rst](../assets/maatlog/template-procedure.rst) |
-| `explanation` | 概念・アーキテクチャ。概念、構造、比較、関連資料 | [assets/maatlog/template-explanation.rst](../assets/maatlog/template-explanation.rst) |
-| `operational` | 短い確認・操作。procedure を共用し、前提条件と手順の流れは省略可 | [assets/maatlog/template-procedure.rst](../assets/maatlog/template-procedure.rst) |
+| `procedure` | 構築・変更・復元。前提条件、手順の流れ、実施手順と結果確認 | [assets/create-reso-world/template-procedure.rst](../assets/create-reso-world/template-procedure.rst) |
+| `explanation` | 概念・アーキテクチャ。概念、構造、比較、関連資料 | [assets/create-reso-world/template-explanation.rst](../assets/create-reso-world/template-explanation.rst) |
+| `operational` | 短い確認・操作。procedure を共用し、前提条件と手順の流れは省略可 | [assets/create-reso-world/template-procedure.rst](../assets/create-reso-world/template-procedure.rst) |
 
 ## OSS Python Extension — reserved / unavailable
 
-明示 `profile=oss-python-extension` 用の予約仕様であり、現在の生成には使用できない。
+明示 `profile=oss-python-extension` 用の予約仕様であり、現在の生成には使用できない。移行元のリポジトリで用意したもので、このリポジトリでは接続していない。
 以下は全て skill root からの予定パスである。`landing-page` の template 名だけが `index` であり、`index` は document_type の別名ではない。
 
-| document_type | 予定パス | リソースの所有者 |
-|---|---|---|
-| `landing-page` | `assets/oss-python-extension/template-index.rst` | #386 |
-| `installation` | `assets/oss-python-extension/template-installation.rst` | #386 |
-| `quickstart` | `assets/oss-python-extension/template-quickstart.rst` | #386 |
-| `tutorial` | `assets/oss-python-extension/template-tutorial.rst` | #386 |
-| `how-to` | `assets/oss-python-extension/template-how-to.rst` | #386 |
-| `explanation` | `assets/oss-python-extension/template-explanation.rst` | #386 |
-| `configuration-reference` | `assets/oss-python-extension/template-configuration-reference.rst` | #388 |
-| `directive-reference` | `assets/oss-python-extension/template-directive-reference.rst` | #388 |
-| `role-reference` | `assets/oss-python-extension/template-role-reference.rst` | #388 |
-| `api-reference` | `assets/oss-python-extension/template-api-reference.rst` | #388 |
-| `troubleshooting` | `assets/oss-python-extension/template-troubleshooting.rst` | #386 |
-| `limitations` | `assets/oss-python-extension/template-limitations.rst` | #386 |
-| `migration` | `assets/oss-python-extension/template-migration.rst` | #386 |
-| `changelog` | `assets/oss-python-extension/template-changelog.rst` | #386 |
+| document_type | 予定パス |
+|---|---|
+| `landing-page` | `assets/oss-python-extension/template-index.rst` |
+| `installation` | `assets/oss-python-extension/template-installation.rst` |
+| `quickstart` | `assets/oss-python-extension/template-quickstart.rst` |
+| `tutorial` | `assets/oss-python-extension/template-tutorial.rst` |
+| `how-to` | `assets/oss-python-extension/template-how-to.rst` |
+| `explanation` | `assets/oss-python-extension/template-explanation.rst` |
+| `configuration-reference` | `assets/oss-python-extension/template-configuration-reference.rst` |
+| `directive-reference` | `assets/oss-python-extension/template-directive-reference.rst` |
+| `role-reference` | `assets/oss-python-extension/template-role-reference.rst` |
+| `api-reference` | `assets/oss-python-extension/template-api-reference.rst` |
+| `troubleshooting` | `assets/oss-python-extension/template-troubleshooting.rst` |
+| `limitations` | `assets/oss-python-extension/template-limitations.rst` |
+| `migration` | `assets/oss-python-extension/template-migration.rst` |
+| `changelog` | `assets/oss-python-extension/template-changelog.rst` |
 
 `changelog` は対象の既存形式を優先したうえでの fallback template である。
-両 profile の `explanation` は別のリソースであり、OSS の代わりに MaatLog template を使わない。
-OSS の profile と semantic guide は #384、eval は #390、最終接続は #393 が所有する。
+両 profile の `explanation` は別のリソースであり、OSS の代わりに create-reso-world の template を使わない。
 
-#393 が先行実装の完了・main への取り込み・統合検証を確認してから、entrypoint とこの表を更新する。
-その時点まで、予定ファイルが部分的または全て揃っても reserved のままとする。
-`SKILL.md` とこの表の編集担当は #382 の実装が main に取り込まれた後に #393 へ移る。
-外部 #379/#402 は #361 全体の完了を待つ。
+OSS profile を接続するときは、`SKILL.md`・この表・[入力仕様](profile-interface.md) の利用可能性を同時に更新し、`evals/` の OSS のケースを entrypoint で再実行する。
+それまでは、予定ファイルが部分的または全て揃っても reserved のままとする。
diff --git a/.agents/skills/rst-writer/references/profile-interface.md b/.agents/skills/rst-writer/references/profile-interface.md
index ac16f50..e305be7 100644
--- a/.agents/skills/rst-writer/references/profile-interface.md
+++ b/.agents/skills/rst-writer/references/profile-interface.md
@@ -8,11 +8,11 @@
 呼び出し元の明示値を、依頼内容からの推論や profile の既定値より優先する。
 明示値同士が矛盾するときは一方を選ばず、書き込み前に必要な判断を返す。
 
-| 入力名 | MaatLog | OSS Python Extension（予約仕様） |
+| 入力名 | create-reso-world | OSS Python Extension（予約仕様） |
 |---|---|---|
-| `profile` | **省略時だけ** `maatlog` | 明示値 `oss-python-extension`。現在は未接続 |
+| `profile` | **省略時だけ** `create-reso-world` | 明示値 `oss-python-extension`。現在は未接続 |
 | `document_type` | 明示値を優先。省略時は依頼から procedure / explanation / operational のいずれかに一意に判断できれば採用、曖昧なら確認 | 必須。種別表の14値から指定 |
-| `target_path` | 新規・省略時は選択した親の `docs_draft/<目的に合う名前>.rst`。明示値は新規・既存とも尊重 | 必須。出力先を推測したり MaatLog の既定先に置換したりしない |
+| `target_path` | 新規・省略時はリポジトリのルートの `docs_draft/<目的に合う名前>.rst`。明示値は新規・既存とも尊重 | 必須。出力先を推測したり create-reso-world の既定先に置換したりしない |
 | `language` | 省略時 `ja`。明示言語で執筆する | 必須。明示言語と対象設定が矛盾すれば報告 |
 | `audience` | 任意。説明の粒度と用語の選択に反映 | 同左 |
 | `package_name` | 任意。依頼と確認済みの資料に基づく | 同左。内容に必要なら不足を報告 |
@@ -23,86 +23,52 @@
 
 ## 書き込み前の確認順
 
-生成・既存編集・用語集更新・lint は、次の全段階を通ったあとに行う。
+生成・既存編集・検査は、次の全段階を通ったあとに行う。
 
 1. **明示値と組み合わせ**: 受け取った値と自然言語の条件を整理し、profile/type の組を種別表で確認する。
    たとえば `target_path=a.rst` と「b.rst を編集」が併記されていれば不整合である。
 2. **必要な情報**: 空値、曖昧な種別、OSS の必須値不足を特定する。
-   MaatLog の省略可能な値だけを推論・既定値で補い、補った値を記録する。
-3. **利用可能性**: 現在 available なのは `maatlog` だけである。
-   `oss-python-extension` は #393 の統合待ちと報告して停止する。必須値不足があればその項目も併記する。
-   OSS 用ファイルが一部または全部存在していても、この表が reserved の間は有効化しない。
-4. **root と変更対象**: 次節に従って所属 repository と絶対パスを確定し、編集対象・用語集・検査対象を区別する。
-5. **必要なリソース**: 共通 guide、選択 profile、対応 template、対象 project と用語集の実在を確認する。
+   create-reso-world の省略可能な値だけを推論・既定値で補い、補った値を記録する。
+3. **利用可能性**: 現在 available なのは `create-reso-world` だけである。
+   `oss-python-extension` は未接続と報告して停止する。必須値不足があればその項目も併記する。
+   OSS 用ファイルが一部または全部存在していても、種別表が reserved の間は有効化しない。
+4. **root と変更対象**: 次節に従って絶対パスを確定し、編集対象と検査対象を区別する。
+5. **必要なリソース**: 共通 guide、選択 profile、対応 template の実在を確認する。
    不足したリソースを別 profile のリソースで代用しない。
    OSS profile では、対象 project の `needs_sphinx`・依存の Sphinx 制約のいずれかが 9.1 未満を許す場合、または実行中の Sphinx が 9.1 未満の場合も対象外として停止する（判定は OSS profile を正本とする）。
 
-途中で不足・未知値・不整合・未接続・リソースの欠落が分かった場合は、ファイル作成、用語集更新、lint（`--fix` や `.bak` 作成を含む）へ進まない。
+途中で不足・未知値・不整合・未接続・リソースの欠落が分かった場合は、ファイル作成や検査（lint の `--fix` や `.bak` 作成を含む）へ進まない。
 受け取った値、具体的な不足または不整合、次に必要な入力・修復を報告する。
-OSS の停止時は MaatLog のリソースを読み込んで代替生成しない。
+OSS の停止時は create-reso-world のリソースを読み込んで代替生成しない。
 
-## MaatLog の root と所有関係
+## create-reso-world の root と変更対象
 
-以下は内部で解決する名前であり、呼び出し入力を増やすものではない。
-
-| 内部名 | 意味 |
-|---|---|
-| `ENV_ROOT` | スキルを所有する親 `usaturn/maatlog-poc` の選択済み checkout |
-| `APP_ROOT` | 公開アプリ `usaturn/maatlog` の選択済み checkout。通常は `ENV_ROOT/public` |
-| `LINT_PROJECT` | profile が選ぶ検査用 Python project。MaatLog では `APP_ROOT` |
-
-呼び出し元が選択した checkout とスキルの配置元から `ENV_ROOT` を確認する。
-作業中の公開アプリ worktree が明示されていれば、それを `APP_ROOT` とする。
-共有 main checkout や共有 `public/` へ置き換えない。
-
-親 cwd から呼ばれた場合も、書く前に読み取り専用で次を確認する。
-
-```sh
-git -C "$ENV_ROOT" rev-parse --show-toplevel
-git -C "$ENV_ROOT" remote get-url origin
-git -C "$ENV_ROOT" config -f .gitmodules --get submodule.public.url
-git -C "$APP_ROOT" rev-parse --show-toplevel
-git -C "$APP_ROOT" remote get-url origin
-```
-
-- 親 origin は `usaturn/maatlog-poc`、公開 origin は親 `.gitmodules` の `usaturn/maatlog` URL と一致すること。
-- `APP_ROOT` の top-level はその公開 checkout 自身であること。
-  空の `public/` 内で top-level が親を返す場合は未初期化である。ディレクトリがあるだけでは足りない。
-- 外部の公開 worktree は選択元の公開 repository と Git の系統（共通 Git directory または履歴）と origin を照合する。
-- `APP_ROOT/pyproject.toml` と `APP_ROOT/docs/glossary.rst` が存在すること。
-  未初期化、origin 不一致、project/用語集欠落なら、その事実と必要な修復を返す。
-  親 project や親 `docs/glossary.rst` への代替、依存追加による埋め合わせはしない。
-
-### 出力先を決める
+リポジトリのルート `REPO_ROOT` は `git rev-parse --show-toplevel` で求める。ワールドのプロジェクト（`slum02/` など）を cwd にしていても、同じルートが返る。
+`external/resoloop` は別のリポジトリであり、その中の文書はこの profile の対象外として書く前に確認する。
 
 | 依頼 | 編集先 |
 |---|---|
-| 新規で `target_path` 省略 | `ENV_ROOT/docs_draft/` の目的に合うファイル |
-| 明示された既存アプリ文書の追記・修正 | 選択した公開 checkout 内の指定ファイル |
-| 明示された環境文書の追記・修正 | 選択した親 checkout 内の指定ファイル |
-| 新規で `target_path` 明示 | 明示の目的と repository の所有関係に整合する指定先 |
-
-相対 `target_path` は依頼元が明示した project/cwd を基準に解決し、勝手に `public/` を足さない。
-解決した絶対パス、所属 repository、cwd、`ENV_ROOT` / `APP_ROOT` / `LINT_PROJECT` を記録する。
-symlink は実体の行き先まで確認する。所属先が不明、別 repository へ出る、候補が複数、または「既存編集」の対象が不存在なら、書く前に確認する。
-親 `docs/` を旧アプリ文書の出力先として復活させない。
+| 新規で `target_path` 省略 | `REPO_ROOT/docs_draft/` の目的に合うファイル |
+| 明示された既存文書の追記・修正 | 指定ファイル |
+| 新規で `target_path` 明示 | 指定先 |
+
+相対 `target_path` は `REPO_ROOT` 基準で解決する（ルート `AGENTS.md` の冒頭にある規則と同じ）。
+解決した絶対パス、cwd、`REPO_ROOT` を記録する。
+symlink は実体の行き先まで確認する。リポジトリの外へ出る、候補が複数、または「既存編集」の対象が不存在なら、書く前に確認する。
 新規作成先に既存ファイルがあれば無断で置換せず、依頼がその編集を許可しているか確認する。
 
 ### 変更するファイルを限定する
 
 既存編集では最初に対象の内容を読み、指定された変更を加える。指定外の文・ラベルを保持する。
 非対象の `docs_draft/` は参考資料として読まない。明示された資料・編集対象は読める。
-
-指定対象以外に許される既存の例外は、本文に使った未定義語の `APP_ROOT/docs/glossary.rst` への追記である。
-詳細は [MaatLog profile](profiles/maatlog.md) に従う。親の用語集は読まず、新設しない。
-別の docs、toctree、conf.py、依存設定を便乗編集しない。
+変更してよいのは対象の1ファイルだけである。別の docs、設定、依存を便乗編集しない。
 参照先ラベルの追加に指定外ファイルの編集が必要なら、その追加作業を不足として報告する。
-lint の対象は今回作成・編集した RST と、実際に編集したときだけ用語集である。
+検査の対象は今回作成・編集した RST だけである。
 
 ## リソースの参照先
 
 - 共通: [RST core](rst-core-style-guide.md)
-- MaatLog: [profile](profiles/maatlog.md)、[文書種別表](document-types.md) の実在 template
+- create-reso-world: [profile](profiles/create-reso-world.md)、[文書種別表](document-types.md) の実在 template
 - OSS 予約: `references/profiles/oss-python-extension.md`、`references/sphinx-semantic-markup.md`、`assets/oss-python-extension/`。未接続なので読み込み・生成には進まない
 
-後続の OSS profile が自身の root と検証 project を定義する。MaatLog の親/公開配置を他 profile の既定にはしない。
+OSS profile は自身の root と検証 project を定義する。create-reso-world の配置を他 profile の既定にはしない。
diff --git a/.agents/skills/rst-writer/references/profiles/oss-python-extension.md b/.agents/skills/rst-writer/references/profiles/oss-python-extension.md
index 114973b..63f518a 100644
--- a/.agents/skills/rst-writer/references/profiles/oss-python-extension.md
+++ b/.agents/skills/rst-writer/references/profiles/oss-python-extension.md
@@ -1,7 +1,7 @@
 # OSS Python Extension profile
 
 `profile=oss-python-extension` に適用する執筆・環境確認・検証方針である。
-この文書は **#393 の統合で entrypoint が接続されたあとに使う**。統合前に直接この文書を使う評価・作業では、呼び出し仕様の停止条件ではなく本書の手順を適用する。
+この文書は **entrypoint が接続されたあとに使う**（現在は未接続。[文書種別表](../document-types.md) を参照）。接続前に直接この文書を使う評価・作業では、呼び出し仕様の停止条件ではなく本書の手順を適用する。
 
 RST 構造・ラベル・4段階 lint は [共通 guide](../rst-core-style-guide.md)、6つの入力と停止条件は [入力仕様](../profile-interface.md)、document_type とリソースの対応は [文書種別表](../document-types.md) を正本とする。
 role・directive の選択条件と fallback は [Sphinx semantic markup](../sphinx-semantic-markup.md) を読む。
@@ -10,12 +10,12 @@ role・directive の選択条件と fallback は [Sphinx semantic markup](../sph
 
 - 入力は共通の6つ。OSS では `document_type` / `target_path` / `language` が必須で、`audience` / `package_name` は任意である。必須値の欠落・空値・未知値・明示値同士の矛盾は、入力仕様の停止条件に従い書き込み前に報告する。追加の呼び出しパラメータは作らない。
 - Sphinx 9.1.0 以上を前提とし、版による記法の分岐はしない。前提を満たさない project は下記「環境の確認順」で停止する。
-- 対象は呼び出し側が指定した project/cwd と `target_path` から確定する。相対パスはその project/cwd 基準で解決し、MaatLog の `public/` や `docs_draft/` へ読み替えない。
+- 対象は呼び出し側が指定した project/cwd と `target_path` から確定する。相対パスはその project/cwd 基準で解決し、create-reso-world の `docs_draft/` へ読み替えない。
 - 既存ページの編集では対象を先に読み、依頼範囲外の本文・ラベル・コメントを保持する。
 
 ## 書き込み先と副作用の境界
 
-- 今回書き込んでよいのは **`target_path` の1ファイルだけ**である。MaatLog の用語集追記のような例外は OSS にはない。
+- 今回書き込んでよいのは **`target_path` の1ファイルだけ**である。例外は無い。
 - toctree への登録、別ページのラベル追加・本文修正、glossary の新設・追記、conf.py・依存設定・サンプルコードの変更はすべて指定外であり、実行せず必要な作業として報告する。参照先ラベルが別ファイルに必要な場合も同様である。
 - 依存の追加、sample・fixture の新設、テンプレートファイルの生成もこの単一ページ作業に含めない。
 - 新規ページが toctree に登録できないことによる警告を `:orphan:` などで消して成功に見せかけない。警告を残し、toctree 登録を必要な後続作業として報告する。
@@ -45,7 +45,7 @@ role・directive の選択条件と fallback は [Sphinx semantic markup](../sph
 
 - 対象 project 自身が `wabun-rst-ulint` を提供するなら `PROJECT_ROOT` を使う。
 - 呼び出し側が検査用 project を明示した場合は、その絶対パスと指定根拠を記録して使う。
-- 上記以外の project（親・兄弟・共有環境）は、存在し linter を提供していても **暗黙に採用しない**。MaatLog の配置を転用しない。
+- 上記以外の project（親・兄弟・共有環境）は、存在し linter を提供していても **暗黙に採用しない**。
 - 対象提供でも呼び出し側の明示でもない場合に、作業者側で新しい検査環境を新設して lint 済みとしない。一時的な `uv run --with` 等で実行しても `LINT_PROJECT` 確定の扱いにはしない。
 - いずれも得られなければ lint は未検証とし、lint 合格とは報告しない。
 
@@ -53,7 +53,7 @@ role・directive の選択条件と fallback は [Sphinx semantic markup](../sph
 
 ## 執筆方針
 
-- `language` と対象の既存スタイルを使う。日本語・である調、固定の「概要」、末尾の単独「以上」、zsh、Python 以外の一律 `::` などの MaatLog 制限は持ち込まない。ページ・節ラベル、一意性、RST 構造、`:doc:` 不使用、4段階 lint は共通 guide に従い維持する。
+- `language` と対象の既存スタイルを使う。日本語・である調、固定の「概要」、末尾の単独「以上」、zsh などの create-reso-world profile の決まりは持ち込まない。ページ・節ラベル、一意性、RST 構造、`:doc:` 不使用、4段階 lint は共通 guide に従い維持する。
 - 言語・用途が明確なら `.. code-block::` に `console` / `python` / `rst` / `json` / `yaml` / `toml` / `text` を使う。shell 固有機能にだけ shell 系を明示する。
 - 実在する sample は `.. literalinclude::` を優先する。包含元 RST からの相対パス、選択範囲（`:lines:` 等）、対象ファイルの実在を確認する。短い説明用の例は `code-block` を使う。
 - 実行可能な Python 例は、対象の既存 doctest 環境が使える場合だけ実行を検討する。表示だけの例を実行済みとはしない。
diff --git a/.agents/skills/rst-writer/references/rst-core-style-guide.md b/.agents/skills/rst-writer/references/rst-core-style-guide.md
index 50ee19d..b470b4a 100644
--- a/.agents/skills/rst-writer/references/rst-core-style-guide.md
+++ b/.agents/skills/rst-writer/references/rst-core-style-guide.md
@@ -1,6 +1,6 @@
 # 共通 RST 記述規則
 
-全 profile に共通する構造と静的検査を定める。言語、文体、出力先、用語集、コード言語・図の選択、build 方針は選択した profile を読む。
+全 profile に共通する構造と、`wabun-rst-ulint` による静的検査を定める。言語、文体、出力先、用語集、コード言語・図の選択、静的検査の手段、build 方針は選択した profile を読む。
 入力と利用可能性の確認は [入力仕様](profile-interface.md)、template の選択は [文書種別表](document-types.md) に従う。
 
 ## ページと見出し
@@ -43,6 +43,8 @@
 参照先の実在とラベルを確認する。ラベルを追加するために依頼範囲外のファイルを編集する必要があれば、不足作業として報告する。
 外部リンクは匿名参照（末尾 `__`）を使う。
 
+Sphinx を使わない profile（create-reso-world）では `:ref:` を解釈できない。ラベルの付け方はこの節のとおりにし、参照はその profile の書き方に従う。
+
 ```rst
 `Sphinx の参照記法 <https://www.sphinx-doc.org/en/master/usage/referencing.html>`__
 ```
@@ -102,7 +104,9 @@
 手順の連番は `#.`、箇条書きは `-` を使う。箇条書きの入れ子は2スペース字下げする。
 リスト内のブロックは項目本文の字下げを基準にする。
 
-## 共通の静的検査
+## `wabun-rst-ulint` による静的検査
+
+検査用 Python project（`LINT_PROJECT`）を確定する profile が、この検査を使う。確定しない profile は、その profile の検査手順に従う（create-reso-world は rstcheck による構文検査）。
 
 profile が確定した検査用 Python project の絶対パスを `LINT_PROJECT`、今回作成・編集した RST の絶対パスを `TARGET` として、ファイルごとに次を順に実行する。
 対象ファイルの置き場所と uv project は別である。親 cwd の暗黙の project discovery に頼らない。
diff --git a/.agents/skills/rst-writer/references/sphinx-semantic-markup.md b/.agents/skills/rst-writer/references/sphinx-semantic-markup.md
index 7138bc4..8a1ace6 100644
--- a/.agents/skills/rst-writer/references/sphinx-semantic-markup.md
+++ b/.agents/skills/rst-writer/references/sphinx-semantic-markup.md
@@ -1,6 +1,6 @@
 # Sphinx semantic markup
 
-Sphinx 拡張機能など OSS Python project のドキュメントで、意味的 role / directive（`py:func`、`confval`、`option`、`term` など）をいつ使い、いつ代替へ落とすかを決める手順。この文書は `oss-python-extension` profile の記法選択ルールであり、共通の見た目・構造ルールは `rst-core-style-guide.md`、MaatLog 内部 project の記法は `profiles/maatlog.md` を参照する。
+Sphinx 拡張機能など OSS Python project のドキュメントで、意味的 role / directive（`py:func`、`confval`、`option`、`term` など）をいつ使い、いつ代替へ落とすかを決める手順。この文書は `oss-python-extension` profile の記法選択ルールであり、共通の見た目・構造ルールは `rst-core-style-guide.md`、このリポジトリの文書の記法は `profiles/create-reso-world.md` を参照する。
 
 この guide は一度読むだけでなく、リンクした文書を含めて全ルールを個別ページへ適用する。Sphinx 9.1.0 以上を前提とし、記法を選ぶ前に必ず対象 project の登録と参照先を調べる。「Sphinx 文書に存在するから」だけで role / directive を選ばない。
 
````

- [ ] **Step 6: テストと検査が通ることを確かめる**

```bash
cd "$W"
uv run pytest -q .agents/skills/rst-writer 2>&1 | tail -n 1
for f in .agents/skills/rst-writer/assets/create-reso-world/*.rst .agents/skills/rst-writer/evals/fixtures/repo-env/docs/resoloop-notes.rst; do
  uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$f" | tail -n 1
done
git grep -n -i -E 'maatlog|#3[0-9]{2}|#4[0-9]{2}' -- .agents/skills/rst-writer ':!*/evals/*'
```

Expected: `9 passed`。rstcheck は 3 回とも `Success! No issues detected.`（初回は uv が docutils と rstcheck を取得する）。`git grep` は何も表示しない（evals には移行元の Issue 番号が履歴として残る。README の冒頭の注記を参照）。

- [ ] **Step 7: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/rst-writer/tests/test_rst_writer_contract.py .agents/skills/rst-writer/references/profiles/create-reso-world.md \
  .agents/skills/rst-writer/evals/fixtures/repo-env/.gitignore .agents/skills/rst-writer/evals/fixtures/repo-env/docs/resoloop-notes.rst \
  .agents/skills/rst-writer/SKILL.md .agents/skills/rst-writer/references/profile-interface.md \
  .agents/skills/rst-writer/references/document-types.md .agents/skills/rst-writer/references/rst-core-style-guide.md \
  .agents/skills/rst-writer/references/profiles/oss-python-extension.md .agents/skills/rst-writer/references/sphinx-semantic-markup.md \
  .agents/skills/rst-writer/evals/evals.json .agents/skills/rst-writer/evals/README.md
git status --short .agents/skills/rst-writer   # 削除と改名（git rm / git mv 済み）以外に未ステージの変更が無いこと
git commit -m "feat(rst-writer): replace the migration source profile with this repository's

The MaatLog profile, its fixtures and the migration note of the old guide are
removed. The create-reso-world profile becomes the default: drafts go to the
repository root's docs_draft/, there is no glossary and no Sphinx role, and
the check is rstcheck through uv run --no-project --with docutils --with
rstcheck. The templates move to assets/create-reso-world/. The OSS profile
stays reserved without the migration source's references, and the evals drop
the MaatLog cases and gain three cases for the new profile.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 11: find-docs を Context7 の手順の正本にする（仕様 5.2・8.2、D-30）

ルート `AGENTS.md` は 1 件 3 回までの制限だけを残して find-docs を参照している（フェーズ 2）。統合前の `CLAUDE.md` にあった規則のうち、スキルに無かったもの（使わない場面、`/org/project` の ID の扱い、`npx ctx7@latest`、API キーの置き場）をスキルに移す。

**Files:**
- Create: `.agents/skills/find-docs/tests/test_find_docs_contract.py`
- Modify: `.agents/skills/find-docs/SKILL.md`

- [ ] **Step 1: 失敗するテストを書く**

`.agents/skills/find-docs/tests/test_find_docs_contract.py` を次の内容で作る。

```python
"""find-docs is the canonical Context7 procedure (spec 5.2, 8.2).

The root AGENTS.md keeps only the three-command limit and points here, so the
rules it used to carry must live in this skill.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/find-docs/SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cli_runs_through_npx_without_a_global_install() -> None:
    content = read(SKILL)
    assert "npx ctx7@latest <command>" in content
    assert "npm install -g" not in content


def test_skill_keeps_the_rules_agents_md_points_to() -> None:
    content = read(SKILL)
    for rule in (
        "Do not run these commands more than 3 times per question",
        "Do not use it for refactoring, business logic, or code review",
        "`/org/project`",
        "Do not silently fall back to training data",
    ):
        assert rule in content, rule
    agents = read(REPO_ROOT / "AGENTS.md")
    assert "find-docs" in agents
    assert "npx ctx7" not in agents


def test_api_key_goes_to_the_secrets_file_of_this_environment() -> None:
    content = read(SKILL)
    assert "npx ctx7@latest login" in content
    assert "`CONTEXT7_API_KEY`" in content
    assert "~/.config/create-reso-world/env" in content
    assert "export CONTEXT7_API_KEY" not in content


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/find-docs"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/find-docs"
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/find-docs 2>&1 | tail -n 1
```

Expected: `3 failed, 1 passed`。

- [ ] **Step 3: SKILL.md を直す**

````diff
diff --git a/.agents/skills/find-docs/SKILL.md b/.agents/skills/find-docs/SKILL.md
index 99e5c6e..1dd845e 100644
--- a/.agents/skills/find-docs/SKILL.md
+++ b/.agents/skills/find-docs/SKILL.md
@@ -21,17 +21,21 @@ description: >-
 
 Retrieve current documentation and code examples for any library using the Context7 CLI.
 
-Make sure the CLI is up to date before running commands:
+In this repository, run the CLI through `npx` without installing it. `ctx7` is not part of the Dev Container, and a global install would change the environment:
 
 ```bash
-npm install -g ctx7@latest
+npx ctx7@latest <command>
 ```
 
-Or run directly without installing:
+The examples below write `ctx7` for short; run each of them as `npx ctx7@latest ...`.
 
-```bash
-npx ctx7@latest <command>
-```
+## Scope in this repository
+
+This skill is the canonical Context7 procedure. The root `AGENTS.md` keeps only the limit of three commands per question and points here.
+
+- Use it for the specifications of libraries, frameworks, SDKs, APIs, CLIs, and cloud services.
+- Do not use it for refactoring, business logic, or code review.
+- When the user gives an ID in the `/org/project` form, skip `ctx7 library` and query `ctx7 docs` with that ID.
 
 ## Workflow
 
@@ -127,21 +131,17 @@ The output contains two types of content: **code snippets** (titled, with langua
 
 ## Authentication
 
-Works without authentication. For higher rate limits:
+Works without authentication. For higher rate limits, either put `CONTEXT7_API_KEY=<key>` in `~/.config/create-reso-world/env` (the shell loads and exports it; see `.devcontainer/README.md`), or log in:
 
 ```bash
-# Option A: environment variable
-export CONTEXT7_API_KEY=your_key
-
-# Option B: OAuth login
-ctx7 login
+npx ctx7@latest login
 ```
 
 ## Error Handling
 
 If a command fails with a quota error ("Monthly quota reached" or "quota exceeded"):
 1. Inform the user their Context7 quota is exhausted
-2. Suggest they authenticate for higher limits: `ctx7 login`
+2. Suggest they authenticate for higher limits: `npx ctx7@latest login`, or `CONTEXT7_API_KEY` in `~/.config/create-reso-world/env`
 3. If they cannot or choose not to authenticate, answer from training knowledge and clearly note it may be outdated
 
 Do not silently fall back to training data — always tell the user why Context7 was not used.
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/find-docs 2>&1 | tail -n 1
```

Expected: `4 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/find-docs/tests/test_find_docs_contract.py .agents/skills/find-docs/SKILL.md
git commit -m "feat(find-docs): make the skill the Context7 procedure of this repository

The CLI runs through npx ctx7@latest instead of a global install, the skill
states when not to use Context7 and how to use a given /org/project ID, and
the API key goes to the secrets file of the Dev Container. AGENTS.md keeps
only the three-command limit and points here.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 12: herdr-agent-task のコマンドの場所（仕様 8.2）

コマンドの実体がリポジトリのルート基準で `.devcontainer/herdr-agent-task.bash` にあること、postCreate が `~/bin/herdr-agent-task` として導入すること、PATH に無いときはワールドのプロジェクトからでも `git rev-parse --show-toplevel` を起点に呼べることを書き足す。状態の表がコマンドの受け付ける状態と一致することもテストで固定する。

**Files:**
- Create: `.agents/skills/herdr-agent-task/tests/test_herdr_agent_task_contract.py`
- Modify: `.agents/skills/herdr-agent-task/SKILL.md`

- [ ] **Step 1: 失敗するテストを書く**

`.agents/skills/herdr-agent-task/tests/test_herdr_agent_task_contract.py` を次の内容で作る。

```python
"""herdr-agent-task names its command by paths from the repository root (spec 8.2)."""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / ".agents/skills/herdr-agent-task/SKILL.md"
SCRIPT = REPO_ROOT / ".devcontainer/herdr-agent-task.bash"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_command_source_is_named_from_the_repository_root() -> None:
    content = read(SKILL)
    assert "`.devcontainer/herdr-agent-task.bash`" in content
    assert SCRIPT.is_file()
    # Works from a world project's directory too: the path starts at the toplevel.
    assert 'bash "$(git rev-parse --show-toplevel)/.devcontainer/herdr-agent-task.bash" set' in content
    assert "~/bin/herdr-agent-task" in content


def test_states_match_the_command() -> None:
    table = read(SKILL).split("## 状態の選び方", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([a-z]+)`", table, re.M))
    accepted = set(re.search(r"^\s+(working \| waiting[^)]*)\)", read(SCRIPT), re.M).group(1).replace(" ", "").split("|"))
    assert documented == accepted


def test_claude_code_reads_the_same_skill_through_a_symlink() -> None:
    link = REPO_ROOT / ".claude/skills/herdr-agent-task"
    assert link.is_symlink()
    assert os.readlink(link) == "../../.agents/skills/herdr-agent-task"
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/herdr-agent-task 2>&1 | tail -n 1
```

Expected: `1 failed, 2 passed`（`test_command_source_is_named_from_the_repository_root`）。

- [ ] **Step 3: SKILL.md を直す**

````diff
diff --git a/.agents/skills/herdr-agent-task/SKILL.md b/.agents/skills/herdr-agent-task/SKILL.md
index 22dd6eb..435dc3f 100644
--- a/.agents/skills/herdr-agent-task/SKILL.md
+++ b/.agents/skills/herdr-agent-task/SKILL.md
@@ -26,6 +26,16 @@ test "${HERDR_ENV:-}" = 1
 これが偽なら何もしない。`herdr-agent-task` は `herdr` が PATH に無ければ何もせず終了する
 ため、誤って呼んでも壊れない。
 
+## コマンドの場所
+
+`herdr-agent-task` の実体は、リポジトリのルート基準で `.devcontainer/herdr-agent-task.bash` にある。
+Dev Container の postCreate が `~/bin/herdr-agent-task` として導入するので、通常は PATH 上のコマンドとして呼ぶ。
+PATH に無い場合（コンテナを作り直す前など）は、このリポジトリの中（ルートかワールドのプロジェクト）から実体を直接呼ぶ。
+
+```bash
+bash "$(git rev-parse --show-toplevel)/.devcontainer/herdr-agent-task.bash" set "Implement page transition"
+```
+
 ## 使い方
 
 タスクに着手したとき:
````

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && uv run pytest -q .agents/skills/herdr-agent-task 2>&1 | tail -n 1
```

Expected: `3 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add .agents/skills/herdr-agent-task/tests/test_herdr_agent_task_contract.py .agents/skills/herdr-agent-task/SKILL.md
git commit -m "docs(herdr-agent-task): name the command source from the repository root

The skill says where the command comes from (.devcontainer/herdr-agent-task.bash,
installed as ~/bin/herdr-agent-task) and how to call it from the repository
toplevel when it is not on PATH, which also works from a world project. A test
keeps the state table in line with the states the command accepts.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 13: AGENTS.md の冒頭にパスの基準を書く（持ち越し N-13）

エージェントはプロジェクトを cwd にして起動するが、`AGENTS.md` のパス（`scripts/new-world.sh` など）はリポジトリのルート基準で書いてある。冒頭の段落に 1 文足す。節の構成は変えない（`test-instructions.bash` が節の並びを検査している）。

**Files:**
- Modify: `AGENTS.md`（3 行目の段落の直後に 1 行）
- Test: `tests/scripts/test-instructions.bash`

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/tests/scripts/test-instructions.bash b/tests/scripts/test-instructions.bash
index a41d04c..4b01f63 100755
--- a/tests/scripts/test-instructions.bash
+++ b/tests/scripts/test-instructions.bash
@@ -29,6 +29,10 @@ actual="$(grep -E '^## ' AGENTS.md)"
 $actual"
 grep -qxF '### SDD 実行運用' AGENTS.md || fail 'AGENTS.md lacks ### SDD 実行運用'
 [ "$(head -n 1 AGENTS.md)" = '# create-reso-world 共通規約' ] || fail 'AGENTS.md title'
+# 冒頭（最初の節より前）で、本文のパスがリポジトリのルート基準であることを示す（プロジェクトを cwd にして読まれるため）
+intro="$(sed -n '1,/^## /p' AGENTS.md)"
+[[ "$intro" == *'本文に書くパスは、プロジェクトを cwd にしている場合も含めて、特記が無ければリポジトリのルート基準である。'* ]] \
+  || fail 'AGENTS.md intro must say that paths are relative to the repository root'
 
 # メイン作業ツリーの未コミット変更（統合時に破棄される）を取り込んでいる
 for s in 'オブジェクトごとに、1つのメッシュにする' '長大なタスクであった場合は分割して実装する' 'agent-handoff' \
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash tests/scripts/test-instructions.bash; echo "exit=$?"
```

Expected: `FAIL: AGENTS.md intro must say that paths are relative to the repository root` で終了コード 1。

- [ ] **Step 3: AGENTS.md に 1 文足す**

```diff
diff --git a/AGENTS.md b/AGENTS.md
index 749a151..d3da341 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -1,6 +1,7 @@
 # create-reso-world 共通規約
 
 このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。
+本文に書くパスは、プロジェクトを cwd にしている場合も含めて、特記が無ければリポジトリのルート基準である。
 
 ## リポジトリ概要
 
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W"
bash tests/scripts/test-instructions.bash
uv run pytest -q .agents/skills/monitoring-long-tasks 2>&1 | tail -n 1   # AGENTS.md の SDD 節の文言を検査している
```

Expected: `PASS: root instruction files follow spec 5.2 and 5.3`、`8 passed`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add AGENTS.md tests/scripts/test-instructions.bash
git commit -m "docs(agents): state that paths are relative to the repository root

Agents start in a project directory, while AGENTS.md names paths such as
scripts/new-world.sh from the repository root. The introduction now says so.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 14: new-world.sh が既存プロジェクトで init を勧めない（持ち越し N-23）

`--apply` で `AGENTS.md` が壊れた symlink か無いとき、今は「run resoloop init first」と表示して終了コード 3 で止まる。既存プロジェクトの中で `resoloop init` を実行すると `content/main.json` やスキルを作り直すので、この案内は危ない。状況を示し（`is a broken symlink` / `is missing or not a regular file`）、git などから戻すよう案内する。新規作成で init が `AGENTS.md` を作らなかった場合は、そのことだけを示す。終了コードは 3 のまま変えない。

**Files:**
- Modify: `scripts/new-world.sh`
- Test: `tests/scripts/test-new-world.bash`（ケース 31〜33）

- [ ] **Step 1: 失敗するテストを書く**

```diff
diff --git a/tests/scripts/test-new-world.bash b/tests/scripts/test-new-world.bash
index f6a5035..8494235 100755
--- a/tests/scripts/test-new-world.bash
+++ b/tests/scripts/test-new-world.bash
@@ -312,4 +312,35 @@ expect_exit 1 'CONFLICT: .claude is not a directory' "$tmp/r30" --apply --no-syn
 [ "$before" = "$(snapshot "$tmp/r30/demo")" ] || fail 'case 30 changed files'
 [ "$before_target" = "$(snapshot "$tmp/r30/claude-elsewhere")" ] || fail 'case 30 wrote through the .claude symlink'
 
+# 31. 既存プロジェクトの AGENTS.md が壊れた symlink なら 3。resoloop init を勧めず、何も変更しない（N-23）
+new_root "$tmp/r31"
+run "$tmp/r31" --no-sync demo >/dev/null
+rm "$tmp/r31/demo/AGENTS.md" && ln -s ../missing-agents.md "$tmp/r31/demo/AGENTS.md"
+before="$(snapshot "$tmp/r31/demo")"
+expect_exit 3 'demo/AGENTS.md is a broken symlink' "$tmp/r31" --apply --no-sync demo
+if grep -qF 'run resoloop init first' "$tmp/out.txt"; then fail 'case 31 still suggests resoloop init'; fi
+grep -qF 'instead of running resoloop init in an existing project' "$tmp/out.txt" || fail 'case 31 does not warn against resoloop init'
+[ "$before" = "$(snapshot "$tmp/r31/demo")" ] || fail 'case 31 changed files'
+
+# 32. 既存プロジェクトに AGENTS.md が無くても同じく 3 で、init を勧めない（N-23）
+new_root "$tmp/r32"
+run "$tmp/r32" --no-sync demo >/dev/null
+rm "$tmp/r32/demo/AGENTS.md"
+before="$(snapshot "$tmp/r32/demo")"
+expect_exit 3 'demo/AGENTS.md is missing or not a regular file' "$tmp/r32" --apply --no-sync demo
+if grep -qF 'run resoloop init first' "$tmp/out.txt"; then fail 'case 32 still suggests resoloop init'; fi
+grep -qF 'instead of running resoloop init in an existing project' "$tmp/out.txt" || fail 'case 32 does not warn against resoloop init'
+[ "$before" = "$(snapshot "$tmp/r32/demo")" ] || fail 'case 32 changed files'
+
+# 33. 新規作成で resoloop init が AGENTS.md を作らなければ 3（init をもう一度実行させない）
+new_root "$tmp/r33"
+mkdir -p "$tmp/init-noagents"
+cat > "$tmp/init-noagents/resoloop" <<EOF
+#!/bin/bash
+"$tmp/mockbin/resoloop" "\$@" || exit
+[ "\$1" != init ] || rm -f "\$2/AGENTS.md"
+EOF
+chmod +x "$tmp/init-noagents/resoloop"
+PATH="$tmp/init-noagents:$PATH" expect_exit 3 'resoloop init did not create demo/AGENTS.md' "$tmp/r33" --no-sync demo
+
 printf 'PASS: new-world script behaves as specified\n'
```

- [ ] **Step 2: 失敗することを確かめる**

```bash
cd "$W" && bash tests/scripts/test-new-world.bash 2>&1 | tail -n 2
```

Expected: `ERROR: demo/AGENTS.md is missing; run resoloop init first` に続いて `FAIL: expected output 'demo/AGENTS.md is a broken symlink': ... --apply --no-sync demo`（ケース 31）で終了コード 1。

- [ ] **Step 3: new-world.sh を直す**

```diff
diff --git a/scripts/new-world.sh b/scripts/new-world.sh
index 8fa6259..824c90d 100755
--- a/scripts/new-world.sh
+++ b/scripts/new-world.sh
@@ -62,7 +62,16 @@ if [ "$apply" -eq 0 ]; then
   initialized=1
 fi
 [ -f "$proj/.resoloop.json" ] || die 3 "$name is not a resoloop project (.resoloop.json is missing)"
-[ -f "$proj/AGENTS.md" ] || die 3 "$name/AGENTS.md is missing; run resoloop init first"
+if [ ! -f "$proj/AGENTS.md" ]; then
+  # 既存プロジェクトの中で resoloop init を実行すると content/main.json やスキルを作り直すので、init は勧めない
+  [ "$apply" -eq 1 ] || die 3 "resoloop init did not create $name/AGENTS.md"
+  if [ -L "$proj/AGENTS.md" ] && [ ! -e "$proj/AGENTS.md" ]; then
+    what='is a broken symlink'
+  else
+    what='is missing or not a regular file'
+  fi
+  die 3 "$name/AGENTS.md $what; restore the project's AGENTS.md (for example with git restore) instead of running resoloop init in an existing project"
+fi
 
 render() { sed -e "s/{{name}}/$name/g" "$1"; }
 # リンクが要る .agents/skills 直下のディレクトリ: ファイルを 1 つ以上持つもの（SKILL.md の有無は問わない）。
```

- [ ] **Step 4: テストが通ることを確かめる**

```bash
cd "$W" && bash tests/scripts/test-new-world.bash
```

Expected: `PASS: new-world script behaves as specified`。

- [ ] **Step 5: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add scripts/new-world.sh tests/scripts/test-new-world.bash
git commit -m "fix(new-world): stop suggesting resoloop init for an existing project

With --apply, a broken symlink or missing AGENTS.md now says which of the two
it is and asks to restore the file, because resoloop init inside an existing
project would regenerate its content and skills. A new project whose init did
not create AGENTS.md says only that. The exit status stays 3.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 15: 移行元の名残を常に検査する（仕様 11、D-31）

Task 1 のテストファイルに、追跡ファイル全体の検査を足す。`git grep -I -F` で候補の行を絞り、正規表現で maatlog・`public/` submodule・`scripts/ci/verify.sh` への参照を判定する。除外は `docs/superpowers/` と、名残が無いことを検査するために語を含むテスト（`.devcontainer/test-cleanup-workspace.bash`、`.devcontainer/test-readme.bash`、`tests/scripts/test-instructions.bash`）と自分自身だけで、除外したパスが無くなったら失敗する。

この Task はテストだけを変える。Task 1〜14 で名残は無くなっているので、足した検査は最初から通る。検出力は、フェーズ 4 の終了時点の tree に当てると 30 ファイルを検出すること（計画作成時に確認済み）と、Step 3 のミューテーションで確かめる。

**Files:**
- Modify: `tests/skills/test_legacy_references.py`（全体を置き換える）

- [ ] **Step 1: 検査を足す**

`tests/skills/test_legacy_references.py` を次の内容に置き換える。

```python
"""Guards against leftovers of the repository this environment was migrated from (spec 8.2, 11).

The migration source kept its application in a `public/` submodule and ran
`scripts/ci/verify.sh`. Neither exists here, so the skills that only made sense
there are removed, and no tracked file may send an agent looking for them.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Skills removed by spec 8.2, checked in every place a runtime looks for them.
REMOVED_SKILLS = ("repository-ownership",)

# Spec 11: no tracked file refers to the migration source, its public/
# submodule or its verify.sh. git grep narrows the candidates with fixed strings
# (the world projects hold large text meshes), then the patterns decide.
CANDIDATES = ("maatlog", "public/", "submodule", "-C public", "scripts/ci/verify", "verify.sh", "verify-devenv")
LEGACY = re.compile(
    r"maatlog|(^|[^a-z0-9_./-])public/|submodule.{0,20}public|-C public|scripts/ci/verify|verify\.sh|verify-devenv",
    re.IGNORECASE,
)
# The design records describe the migration itself, and these tests spell the
# words out to assert that they are gone.
EXCLUDED = (
    "docs/superpowers",
    ".devcontainer/test-cleanup-workspace.bash",
    ".devcontainer/test-readme.bash",
    "tests/scripts/test-instructions.bash",
    "tests/skills/test_legacy_references.py",
)


@pytest.mark.parametrize("name", REMOVED_SKILLS)
def test_removed_skill_is_gone_from_every_runtime(name: str) -> None:
    assert not (REPO_ROOT / ".agents/skills" / name).exists()
    link = REPO_ROOT / ".claude/skills" / name
    assert not link.is_symlink() and not link.exists()
    assert not (REPO_ROOT / ".cursor/rules" / f"{name}.mdc").exists()


def test_tracked_files_do_not_refer_to_the_migration_source() -> None:
    for path in EXCLUDED:
        assert (REPO_ROOT / path).exists(), f"stale exclusion: {path}"
    candidates = [arg for text in CANDIDATES for arg in ("-e", text)]
    excludes = [f":(exclude){path}" for path in EXCLUDED]
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-I", "-n", "-i", "-F", *candidates, "--", ".", *excludes],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    # Each line is "<path>:<line number>:<text>"; only the text decides.
    hits = [line for line in result.stdout.splitlines() if LEGACY.search(line.split(":", 2)[2])]
    assert not hits, "tracked files still refer to the migration source:\n" + "\n".join(hits)
```

- [ ] **Step 2: 通ることを確かめる**

```bash
cd "$W"
uv run pytest -q tests/skills/test_legacy_references.py 2>&1 | tail -n 1
uv run pytest -q tests/skills .agents/skills 2>&1 | tail -n 1
```

Expected: `2 passed`（1 秒未満）、`255 passed, 1 skipped`。

- [ ] **Step 3: 検出力を確かめる**

```bash
cd "$W"
cp .agents/skills/find-docs/SKILL.md /tmp/find-docs.SKILL.md.bak
printf '\nSee the maatlog notes.\n' >> .agents/skills/find-docs/SKILL.md
uv run pytest -q tests/skills/test_legacy_references.py 2>&1 | grep -F 'find-docs/SKILL.md'
cp /tmp/find-docs.SKILL.md.bak .agents/skills/find-docs/SKILL.md
git grep -l -i maatlog -- docs/superpowers | wc -l
git status --short
```

Expected: 1 本目は `.agents/skills/find-docs/SKILL.md:<行>:See the maatlog notes.` を含む `E` の行を表示する（テストは失敗する）。2 本目は 1 以上（除外した設計記録には語が残っているが、Step 2 でテストは通っている）。最後は ` M tests/skills/test_legacy_references.py` の 1 行だけ（find-docs は元に戻っている）。

- [ ] **Step 4: 回帰を確かめてコミットする**

Global Constraints の回帰確認を行う。

```bash
cd "$W"
git add tests/skills/test_legacy_references.py
git commit -m "test(skills): keep tracked files free of the migration source

The skill tests now search every tracked file for the migration source, its
public/ submodule and its verify script (spec 11). Fixed strings narrow the
candidates, so the large mesh files of the world projects cost little. Only
the design records under docs/superpowers/ and the tests that assert these
words are gone are excluded, and a stale exclusion fails.

Co-Authored-By: <自分のモデル名> <noreply@anthropic.com>"
```

---

### Task 16: 一括検証・push・最終レビュー（controller）

- [ ] 1. 全体の検証を行う（すべて期待どおりであること）。

```bash
cd "$W"
git status --short | wc -l                                             # 0
bash .devcontainer/run-tests.bash | tail -n 1                          # PASS: 23 test(s)
bash scripts/check-layout.sh | tail -n 3                               # ok: resoloop lock (...) / ok: mounts match .devcontainer/initialize.bash / PASS: check-layout
uv run pytest -q tests/skills .agents/skills 2>&1 | tail -n 1          # 255 passed, 1 skipped（仕様 10 章のフェーズ 5 の完了条件）
for P in MyResoniteProject akichi slum02; do (cd "$P" && uv run pytest -q 2>&1 | tail -n 1); done   # 52 / 66 / 215 passed
git ls-files -i -c --exclude-standard                                  # pipeline.json の 1 行だけ
git grep -I -l -i -E 'maatlog|(^|[^a-z0-9_./-])public/|submodule.{0,20}public|-C public|scripts/ci/verify|verify\.sh|verify-devenv' \
  -- . ':(exclude)docs/superpowers'                                    # 下の 4 本だけ
```

最後の `git grep` が表示するのは、名残が無いことを検査するテスト 4 本（`.devcontainer/test-cleanup-workspace.bash`、`.devcontainer/test-readme.bash`、`tests/scripts/test-instructions.bash`、`tests/skills/test_legacy_references.py`）だけであること（仕様 11 章。evals の例外は使っていない）。

- [ ] 2. CI 相当の PATH（`tests/scripts/lib/path.bash` の `path_without` で resoloop・dotnet・blender・claude・codex・pi・devin・agent・herdr・starship・bun・gcloud・grok・glab・gh・fzf・pnpm を外したもの）で、`bash .devcontainer/run-tests.bash`・`uv run pytest -q tests/skills .agents/skills`・`bash scripts/check-layout.sh` がすべて通る。
- [ ] 3. フェーズ 5 の差分の追加行に「契約」「原子的」「製品」「着地」が無いことを確かめる（`git diff <計画書のコミット>..HEAD | grep '^+' | grep -e 契約 -e 原子的 -e 製品 -e 着地` が何も表示しない）。
- [ ] 4. fast-forward を確かめてから `git push origin chore/repo-redesign` を実行する。push した直後の GitHub Actions の実行を `gh run list --branch chore/repo-redesign` で確かめ、4 ジョブ（devcontainer-tests、layout、skill-tests、gitleaks）がすべて成功することを確かめる。skill-tests の成功で持ち越し N-26 を閉じる。結果は台帳に記録する。gh が使えないときは記録だけにし、N-27 に残す。
- [ ] 5. 最上位モデルのレビュアーに `MERGE_BASE..HEAD`（`MERGE_BASE` は計画書のコミットの親）のレビューを依頼し、指摘は修正ラウンドで直す。完了後、台帳の最後に `PHASE 5 COMPLETE.` を書く。フェーズ 6 の計画に進む（D-9）。

---

## 持ち越し（フェーズ 6）

前回の引き継ぎ書と本計画で見つかった保留事項。本計画では着手しない。フェーズ 5 の項目（N-2、N-13、N-14、N-23、N-26）は本計画の Task 1〜16 で扱う。

| ID | フェーズ | 内容 |
| --- | --- | --- |
| N-3 | 6 | ルート README に書くこと: Codex の trust、cursor-agent の MCP 承認、Devin の単一表示、Cursor と dsh のスキル可視性、pi-superagents の組み込み定義は追跡しない（D-1）。`.devcontainer/README.md` の該当節（エージェントの読み込みの制約、秘密情報、テストの実行）へのリンクで済むものは重複させない |
| N-4 | 6 | マージ直前に統合手順の衝突一覧を再実行し、件数を最新にする |
| N-12 | 6 | integration.md: sp-implementer.md の比較先、項目 2 の 3 ブロックは同じシェルで、項目 3・5 の根拠への参照 |
| N-17 | 6 | 仕様 9.3 の実機確認に、Devin で simplify-in-subagent を呼んだときにサブエージェントが edit / exec を持つかを含める |
| N-18 | 6 | 仕様 9.3 の実機確認に、Rebuild の postCreate で fork のビルドと導入が通ること（SDK 10.0.201、build / pack の引数、`--version` の一致）を含める。GitHub への `sync` の push 認証も未確認 |
| N-24 | 6 | 文書の整合: 仕様 6.4 と運用文書の修正の流れの順序に注記、運用文書の環境変数の説明を揃える、仕様 9.1 の `*/SKILL.md` を D-7 の定義に合わせる（P-7 と一緒に）。仕様 7.2 の `${containerEnv:HOME}` を D-10 に合わせて注記する |
| N-25 | 6 | 仕様 9.3 の実機確認に、Rebuild 後の `remoteEnv.PATH`（`/home/vscode/.local/bin`・`/home/vscode/bin`）、`~/.config/create-reso-world` の mount と `env` の読み込み、`initialize.bash` がホストに mode 700 で作ることを含める |
| N-27 | 6 | PR の前に、GitHub Actions の実行結果（`actions/checkout@v7`、`setup-uv@v10`、`gitleaks-action@v3` の組み合わせ）を確かめる。Task 16 で確かめられなかった場合は必ず行う |
| N-28 | 6 | pr-review が resoloop の PR のレビューを保存する `external/resoloop/reviews/` は、fork の `.gitignore` の対象外で未追跡のまま残る。本計画では本文で commit に含めないよう注意するだけにした（Task 3）。`scripts/resoloop-fork.sh clone` が fork の `.git/info/exclude` に `/reviews/` を足すかを決める |
| N-29 | 6 | rst-writer の OSS Python Extension profile は、未接続の予約として template 14 本と fixture 一式を持ったまま残した（D-28）。README の整理と一緒に、このリポジトリで使う見込みが無ければ削除するかを判断する（削除するなら仕様 8.2 に 1 行足す） |
| P-1、P-2、P-3、P-7、M-5 | 6 | integration.md と仕様 10.1 の退避手順、`.git/info/exclude` の `/private/` の削除、フェーズ 0・1 計画書の注記、仕様 4.4 の表記、main の再 ff は `git fetch . feat/slum02-slum:main` |

据え置き（PH3-S1。直すのは必要になったときだけ）は前回の引き継ぎ書のとおり。
