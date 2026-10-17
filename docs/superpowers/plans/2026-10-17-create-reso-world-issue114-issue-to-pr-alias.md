# Issue #114 issue-to-pr と alias の実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue から PR までを推奨案で進める `issue-to-pr` スキル（入力を確かめる helper とテスト、行動比較の記録を含む）と、モデルを固定した Cursor・Devin の alias を入れる。

**Architecture:** `.agents/skills/issue-to-pr/` に `SKILL.md`、標準ライブラリだけの `scripts/resolve_issue.py`、pytest の `tests/`、行動比較の `evals/` を置き、`.claude/skills/issue-to-pr` から symlink する。alias は `.devcontainer/zshrc.txt` を書き換え、README と移植の記録を合わせる。

**Tech Stack:** Python 3.12+（標準ライブラリ）、pytest、zsh、gh CLI

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue114-issue-to-pr-alias-design.md`

- 状態: draft（利用者の明示承認は得ていない。実行許可は Spec の「管理・実行許可」）
- 基準 HEAD: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`

## Global Constraints

- 扱うリポジトリは `usaturn/create-reso-world`・`usaturn/resoloop`・`usaturn/resoloop-meshy` の 3 つだけ（D-1）
- 受け付ける表記は `https://github.com/<owner>/<repo>/issues/N`・`<owner>/<repo>#N`・`#N`（D-3）
- `resolve_issue.py` は標準ライブラリだけ。`pyproject.toml`・`uv.lock`・`README.md` の「テスト」の節を変えない（D-5、範囲外）
- `-` で始まる語は拒否する。移植元のオプションは「#116 で入れる予定」と理由を出す（D-6）
- 失敗は終了コード 2、stderr は `issue-to-pr:` で始める。成功は終了コード 0 で `repo`・`number`・`url`・`title`・`body` の JSON（D-7）
- 文言を照合するテストは書かない（D-17、`AGENTS.md` の「テストの採用基準」）
- alias の定義は Spec の D-20 のとおり（下の Task 3 に写す）

## Review Focus

- `#N` を、`origin` が無い・GitHub 以外・対象外のリポジトリの checkout で渡す → 他のリポジトリに切り替えずに拒否する（Task 1 のテスト `test_number_with_unusable_origin_stops`）
- 上流の `orange3134/resoloop#N` を渡す → fork と取り違えずに拒否する（Task 1 の `test_rejects_input_before_looking_up_issue`）
- 利用者の引数に自然文が残った `#42 推奨案で` → 語を捨てずに拒否する（同上）
- `gh` が別のリポジトリの Issue や PR を返す、URL の大文字小文字が違う → owner/repo の大文字小文字だけを許し、ほかは拒否する（Task 1 の `test_accepts_repo_casing_only_in_response_url`・`test_rejects_mismatched_or_closed_response`）
- `--merge=1` のような `=` 付きの形 → 名前で判定して #116 の理由を出す（Task 1 の `test_rejects_options_with_reason`）

---

### Task 1: `resolve_issue.py` とテスト

テスト: 要る。入力の解析・拒否・応答の照合は、コードを実行して確かめる分岐である（D-18）。

**Files:**
- Create: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`
- Create: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`
- Create: `.agents/skills/issue-to-pr/SKILL.md`（frontmatter だけの仮置き。本文は Task 2。`tests/skills/test_skill_frontmatter.py` がスキルのディレクトリに `SKILL.md` を要求するため）
- Create: `.claude/skills/issue-to-pr`（`../../.agents/skills/issue-to-pr` への symlink。`scripts/check-layout.sh` の検査 4）

**Interfaces:**
- Produces（Task 2 の `SKILL.md` が使う）:
  - CLI: `uv run --no-project python "$SKILL_DIR/scripts/resolve_issue.py" -- "$INPUT"`。cwd の checkout の `origin` で `#N` を解決する
  - 成功: 終了コード 0、stdout に `{"repo": "usaturn/resoloop", "number": 18, "url": "https://github.com/usaturn/resoloop/issues/18", "title": "...", "body": "..."}`。`repo` は `SUPPORTED_REPOSITORIES` の表記（小文字）、`url` は `gh` の応答のまま
  - 失敗: 終了コード 2、stdout は空、stderr は `issue-to-pr: <理由>`
  - モジュールの定数 `SUPPORTED_REPOSITORIES = ("usaturn/create-reso-world", "usaturn/resoloop", "usaturn/resoloop-meshy")`、`FUTURE_OPTIONS`（`--merge`・`--implement`・`--max-cycles`・`--hold-action`・`--assign`・`--template`・`--config`・`--fresh-review`）
  - 関数: `parse_input(text: str) -> str`（参照を 1 つ返す）、`resolve_target(reference: str, cwd: Path) -> tuple[str, int]`、`fetch_issue(repo: str, number: int) -> dict[str, str | int]`、`main(argv: list[str] | None = None) -> int`。いずれも拒否は `ValueError`

- [ ] **Step 1: テストを書く**

移植元 `ec13c3e` の `tests/test_resolve_issue.py` の作り（`git init` した checkout、PATH の先頭に置いた `gh` の代わりのスクリプト、`subprocess` で CLI を実行）に合わせる。`gh` の代わりは、`issue view <N> --repo <repo>` の形と `EXPECTED_REPO` を確かめ、呼ばれたら `GH_CALLED` のファイルを作り、`GH_FAIL` があれば 404 で失敗し、それ以外は `GH_RESPONSE` を出す。

- `test_resolves_supported_forms_without_changing_git`: parametrize。`https://github.com/usaturn/resoloop/issues/42`→`usaturn/resoloop`、`usaturn/resoloop-meshy#42`、`Usaturn/Create-Reso-World#42`→`usaturn/create-reso-world`、`#42`（origin が `https://github.com/usaturn/create-reso-world.git`・`git@github.com:usaturn/resoloop.git`・`ssh://git@github.com/usaturn/resoloop-meshy`）。終了コード 0、JSON の 5 項目、`git status --porcelain` と `git for-each-ref` が実行の前後で同じ
- `test_accepts_repo_casing_only_in_response_url`: 応答の URL が `https://github.com/USATURN/Create-Reso-World/issues/42` でも成功し、`url` は応答のまま
- `test_rejects_input_before_looking_up_issue`: parametrize。`https://github.com/usaturn/create-reso-world/pull/42`、`https://github.com/other/repo/issues/42`、`other/repo#42`、`orange3134/resoloop#42`、`resoloop#42`、`42`、`#0`、`#042`、`#42; touch injected`、`#42 #43`、`#42 推奨案で`、空文字列、`https://github.com/usaturn/resoloop/issues/42?x=1`、`https://github.com/usaturn/resoloop/issues/42#c`。終了コード 2、stdout 空、stderr が `issue-to-pr:` で始まり、`GH_CALLED` が無く、`injected` が作られない
- `test_rejects_options_with_reason`: parametrize。`#42 --merge`、`#42 --merge=1`、`--implement self #42`、`#42 --max-cycles 2`、`#42 --fresh-review` は stderr に `#116` を含む。`#42 --foo` は stderr に `未知のオプション` を含み `#116` を含まない。どれも `GH_CALLED` が無い
- `test_number_with_unusable_origin_stops`: parametrize。origin が `https://github.com/other/repo.git`、`https://github.com/orange3134/resoloop.git`、`https://gitlab.com/usaturn/create-reso-world.git`、origin なし（`upstream` だけ）、checkout の外の cwd。終了コード 2、`GH_CALLED` が無い
- `test_rejects_mismatched_or_closed_response`: parametrize。state `CLOSED`、URL が `/pull/42`、番号 99、URL が別のリポジトリ、`http://`、`https://github.com.evil.test/...`、末尾の `/`・`?`・`#`、`/issues/042`。終了コード 2、stdout 空
- `test_rejects_malformed_response`: parametrize。`not JSON`、`[]`、`{}`、`{"number": "42", ...}`（型違い）、`{"number": true, ...}`。終了コード 2
- `test_reports_gh_failure`: `GH_FAIL=1` で終了コード 2、stderr に `404`

- [ ] **Step 2: 実行して失敗を確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr/tests -q`
Expected: FAIL（`resolve_issue.py` が無い）

- [ ] **Step 3: `resolve_issue.py` を実装する**

移植元 `ec13c3e` の `resolve_issue.py` の形（正規表現の `fullmatch`、`run_readonly`、URL の照合）を保ち、`tools.workspace` と pydantic を外す。語の分割は `shlex.split`（移植元 `84469b9` の `parse_input` と同じ）。応答の検査は、`number` が `bool` でない `int`、`title`・`body`・`url` が `str`、`state` が `OPEN`・`CLOSED`・`MERGED` のどれか。`origin` の URL は `https://github.com/`・`git@github.com:`・`ssh://git@github.com/` の 3 形を受け付け、末尾の `.git`・`/` を外して小文字で比べる。

- [ ] **Step 4: 実行して通ることを確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr/tests -q` → 全件 PASS
Run: `uv run pytest tests/skills -q` → PASS（仮置きの `SKILL.md` の frontmatter）
Run: `bash scripts/check-layout.sh` → 検査 4 を含めて PASS

- [ ] **Step 5: コミットする**

```bash
git add .agents/skills/issue-to-pr .claude/skills/issue-to-pr
git commit -m "feat(skills): add issue-to-pr issue resolver (#114)"
```

### Task 2: `SKILL.md` と行動比較

テスト: 書かない。文面の確かめは `superpowers:writing-skills` の行動比較で行い、文言を照合するテストを作らない（D-17）。代わりの検証は下の Step 1・3 の比較と、`uv run pytest tests/skills .agents/skills`・`bash scripts/check-layout.sh`。

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`（本文）
- Create: `.agents/skills/issue-to-pr/evals/scenarios.json`、`.agents/skills/issue-to-pr/evals/validation.md`
- Modify: `AGENTS.md` の「Spec・Plan の保存と公開」に 1 項目（D-8）

**Interfaces:**
- Consumes: Task 1 の CLI と出力

- [ ] **Step 1: スキル無しの基準を取る（RED）**

`evals/scenarios.json` に、1 つの指示文にまとめるシナリオを書く。どれも読み取りだけの評価で、ツールを使わず、次に何をし、利用者に何を報告するかを答えさせる。

- (a) 同じ Issue に open PR がある（PR の URL と base `main` を事実として渡す）→ 新しい worktree を作らずに止まり、URL と base を報告し、レビューは `/pr-review <PR の URL>` と伝える
- (b) `--merge` 付きで起動し、helper が `#116` の理由で終了コード 2 → 副作用に進まず止まり、理由を伝える
- (c) create-reso-world の Issue で、本文に「実装の対象: usaturn/resoloop」→ 実装は `external/resoloop/.worktrees/` の worktree、Spec・Plan は create-reso-world の文書用の worktree、コードの PR は `Refs <Issue の URL>`、文書専用の PR、public なので checks を確かめる
- (d) create-reso-world の通常の Issue → 確認を求めずに Spec・Plan を `draft` でコミットし、確認用のコピーを作らず、`README.md` の「テスト」で検証し、`Closes #N` の PR を作り、マージしない
- (e) 親 Issue が統合用の branch を向き先に指定 → worktree を作らずに止まる

スキル無し（`AGENTS.md` だけ）で、新しいサブエージェント（model `sonnet`）に 2 回答えさせ、全回答を人手で読んで期待と違う点を記録する。

- [ ] **Step 2: `SKILL.md` の本文を書く（GREEN）**

移植元 `ec13c3e` の章立て（1. 入口と委任の範囲、2. 入力・所有者・競合の確認、3. Herdr と作業場所、4. 推奨案 → Spec → Plan → 実装、5. 検証・PR・完了、停止時の報告）に合わせ、Spec の D-1〜D-16 に置き換える。対象のリポジトリごとの checkout・worktree・remote の確認・検証の入口・CI を 1 つの表にする。`PARENT_ROOT` は `SKILL_DIR` の git common dir の親で求め、`origin` が create-reso-world の main checkout であることを確かめる。Pi の入口の扱いは移植元のまま残す。

- [ ] **Step 3: スキル有りで比べる（REFACTOR）**

Step 1 と同じ指示文に `SKILL.md` の全文を足し、新しいサブエージェント（model `sonnet`）に 2 回答えさせる。期待から外れた回答があれば、`SKILL.md` を直して取り直す。結果を `evals/validation.md` に、スキル無し・有りの表と、行っていない確認（実際の Issue での起動、Pi・Codex での評価）とともに書く。

- [ ] **Step 4: `AGENTS.md` に 1 項目を足す**

「Spec・Plan の保存と公開」の「ユーザに Spec・Plan の確認を依頼する前に…」の後に足す: issue-to-pr で進める run は利用者に確認を求めないので確認用のコピーを作らず、Spec・Plan は `draft` のまま PR（他のリポジトリの作業では文書専用の PR）で公開する。利用者の実行指示は実行許可として記録し、`approved` にしない。

- [ ] **Step 5: 検証してコミットする**

Run: `uv run pytest tests/skills .agents/skills -q` → PASS
Run: `bash scripts/check-layout.sh` → PASS

```bash
git add .agents/skills/issue-to-pr AGENTS.md
git commit -m "feat(skills): add issue-to-pr skill text and behavior evals (#114)"
```

### Task 3: alias

テスト: 書かない。設定値と一覧だけの変更である。代わりの検証は、`.devcontainer/test-readme.bash`（`run-tests.bash` に含まれる）と、5 つの alias の実際の起動。

**Files:**
- Modify: `.devcontainer/zshrc.txt:65-66`
- Modify: `.devcontainer/README.md` のツールの表（Cursor・Devin の行）
- Modify: `docs/maatlog-poc-porting.md` の Cursor と Devin の alias の行

- [ ] **Step 1: alias を書き換える**

```zsh
alias cur="agent --model grok-4.7-xhigh --yolo"
alias curo="agent --model claude-opus-5-5-xhigh --yolo"
alias dev="devin --model swe-2-max --permission-mode dangerous"
alias devs="devin --model gpt-6-1-sol-xhigh --permission-mode dangerous"
alias devo="devin --model claude-opus-5-5-xhigh --permission-mode dangerous"
```

- [ ] **Step 2: README と移植の記録を合わせる**

ツールの表の「zshrc の関数」を、Cursor は `cur`、`curo`（alias）、Devin は `dev`、`devs`、`devo`（alias）にする。移植の記録の行は、判断を「移植」、担当 Issue を #114 にし、理由に「agent-workspace の `3bc4769`（#515 の定義）に合わせた。#17 の実行ボードでは、どの子も変えないとして対象外にした」と書く。

- [ ] **Step 3: 実際に起動して確かめる**

scratchpad の空のディレクトリを cwd にし、`zshrc.txt` の 5 つの alias の行だけを読み込んだ zsh で、各 alias に `-p` と短い指示（「OK とだけ答えて。ツールは使わない」）を付けて起動する。Devin は非対話の起動に workspace の trust が要るので `--respect-workspace-trust false` を足す。終了コード 0 と応答を確かめ、使ったモデルを各 CLI の表示（Cursor は `--output-format json` の出力、Devin は応答か `--output-format` の出力）で確かめる。

- [ ] **Step 4: 検証してコミットする**

Run: `bash .devcontainer/run-tests.bash` → PASS

```bash
git add .devcontainer/zshrc.txt .devcontainer/README.md docs/maatlog-poc-porting.md
git commit -m "feat(devcontainer): pin Cursor and Devin alias models (#114)"
```

## 実行方式

`superpowers:executing-plans`（このセッションで実装する）。Task は 3 つで、Task 2 は Task 1 の CLI を前提にし、行動比較の判断に会話の文脈が要る。最後に、新しいレビュアー（サブエージェント）がブランチ全体をレビューする。

## 最後の検証と PR

- `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`（`README.md` の「テスト」）
- push と `gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-114-agent-workspace-port`。本文は `Refs #114`（rebuild の後の確認が残るので、マージで自動で close しない）
- rebuild の後に利用者が確かめる項目を #114 にコメントする（D-23）
- private の create-reso-world は CI を止めているので確かめない

## Contingency

- 行動比較で、スキル有りでも期待を外す回答が 2 回続いたら、`SKILL.md` を直して 1 回だけ取り直し、残った差を `validation.md` に書いて進む
- alias のモデルが起動で拒否されたら、そのモデルを今の CLI の一覧の名前で確かめ直す。一覧に無ければ移植元の定義を変えず、PR と #114 に記録する
- #115 が先にマージされたら、`main` に追従してからテストを実行し直す
