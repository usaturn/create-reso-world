# PR #130: agent_tmp と作業の安全規則（Issue #123）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/130（`feat/issue-123-agent-tmp-safety-rules` → `main`）
- 関連 Issue: #123（本文の `Closes #123`）。本文で参照しているだけの Issue は #124（#123 に統合済みで close）・#131・#132・#115
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue123-agent-tmp-safety-rules-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue123-agent-tmp-safety-rules.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `38d779fcc832086a1ba39aab7c3e8d20738de9c4`。base `main` は `cd602e6` で、PR の分岐点と同じ（base は進んでいない）
- 状態: completed
- 実行許可: 利用者が 2026-10-17（JST）に `/review-fix-planning #130` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-123-agent-tmp-safety-rules`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#130-feat-issue-123-agent-tmp-safety-rules/` の 3 ファイル。対象 HEAD はどちらも取得した `pull/130/head`（`38d779f`）の祖先である。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `38d779fcc832` | Approve | Info 1 件（I-1） |
| `gpt-6.1-sol.md` | `7e806a427482` | Approve | なし |
| `grok-4.7.md` | `38d779fcc832` | Approve | なし |

`7e806a4` から `38d779f` の差分は `.devcontainer/README.md`・`AGENTS.md`（置き場所の表の 1 行）・PR の Spec・Plan だけで、`.agents/`・`pyproject.toml`・`.github/`・`README.md`・`CLAUDE.md` は同じ（`git diff --quiet` で確認）。GPT のレビューのコードの結論は現行 HEAD にも当てはまる。

## 分類

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| I-1 | Opus（Info） | review-fix-planning の「実装後」の手順 2（変更の種類に応じた検証）は、`.agents/` の変更に `run-tests.bash` と `check-layout.sh` だけを挙げ、pytest はスキルを変えたときの `tests/skills .agents/skills` だけ。`.agents/scripts` を変える review-fix で手順 2 を文面どおりに実行すると `.agents/scripts/tests` が走らない | 対応しない。記述は現行 HEAD でもそのとおり（`.agents/skills/review-fix-planning/SKILL.md:307`）だが、同じ節の手順 1 が「変更ファイルをカバーするテスト」を走らせると定めており、`agent_tmp.py` を変える修正ではそこで `.agents/scripts/tests/test_agent_tmp.py` が走る。手順のとおりに進めても誤った結果にはならず、記載の網羅の論点である（レビュアーも「実害は限定的」とする）。SKILL.md はこの PR の差分に無い |

分類: **解消済み 0 / 対応する 0 / 対応しない 1**。GPT・Grok のレビューは指摘が無い。

仕様の論点として残すもの: review-fix-planning の手順 2 の pytest に `.agents/scripts` を足すかは、次にこのスキルを変えるときに合わせて決めればよい。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件。この PR に以前のレビュー修正は無い）。

## 確認の範囲

- PR の変更 10 ファイル: `.agents/scripts/agent_tmp.py`・`.agents/scripts/tests/test_agent_tmp.py`・PR の Spec の全文、`AGENTS.md`・`CLAUDE.md`・`README.md`・`.devcontainer/README.md`・`.github/workflows/ci.yml`・`pyproject.toml` の差分と周辺の節、Plan の追記
- 関連: `.gitignore`（41 行目の `tmp/`）、`.devcontainer/run-tests.bash`（pytest を呼ばない）、`scripts/check-layout.sh`（`.agents/skills` と `.claude/skills` の対応だけを見る）、`scripts/superpowers_context.py`（`PARENT_ROOT` の照合）、`git grep` による `agent_tmp`・`tmp/agents`・`pytest tests/skills` の参照（`docs/superpowers/` を除くと、変更ファイルと review-fix-planning の SKILL.md、過去の移植の記録 `docs/maatlog-poc-porting.md` だけ）、PR のコメント（持ち越しの再調査）、Issue #123・#124・#131・#132・#115 の状態と本文
- 自己確認:
  - `agent_tmp.py` は親の checkout を cwd ではなくスクリプトの置き場所から求め、common dir が `.git` でない checkout を拒否する。`mkdir` は topic の形（`/` と先頭の `.`・`-` を含まない）を検査し、`tmp/agents` の実体が親の checkout の中にあって git に無視されることを確かめてから `mkdtemp`（0700）で作る。不正な入力では何も作らない（テストの不正な topic・無視されない `tmp`・外を指す symlink・追跡するディレクトリを指す symlink の各ケースで確認されている）
  - 実環境で、この worktree の写しから `uv run --no-project python .agents/scripts/agent_tmp.py root` が `/workspaces/reso-world`（終了コード 0）を返し、共通 context の helper が返す `parent_root` と一致する。`git -C /workspaces/reso-world check-ignore -v tmp/agents` は `.gitignore:41:tmp/` に一致する
  - `AGENTS.md` の「作業の安全」は、ワールドの作業と置き場所の表への書き込みを「追跡するファイルの編集」から明示的に外しており、「プロジェクト運用」と食い違わない。`CLAUDE.md` から消した削除の規則は、`@AGENTS.md` で読み込む「作業の安全」の「削除」に同じ内容がある
  - `pyproject.toml` の `testpaths` の変更で、既定の `uv run pytest` の収集に `test_agent_tmp.py` の 21 件が入る（全 495 件。`--collect-only`）
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い（`/tmp` の固定名と SDD の作業領域は、PR が持ち越した #131・#132 で扱われている）

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `38d779f` | `uv run pytest .agents/scripts -q` | 21 passed（13.71 秒） |
| PR head `38d779f` | `uv run pytest --collect-only -q` | 495 件を収集、うち `test_agent_tmp.py` が 21 件 |
| PR head `38d779f` | `bash scripts/check-layout.sh` | PASS |
| PR head `38d779f` | `bash .devcontainer/run-tests.bash` | `PASS: 30 test(s)`、終了コード 0（約 7 分。別のセッションの `run-tests.bash` と並行して動いた） |

PR はスキル（`.agents/skills/`・`tests/skills/`）を変えていないので、`uv run pytest tests/skills .agents/skills` は反映の条件にしていない（PR 本文に `299f381` での 495 passed の記録がある。`299f381` 以降の変更は文書だけ）。base は PR の分岐点から進んでいないので、merge した一時的なツリーでの検証は不要。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外に置いた。検証の前後で worktree の `git status --porcelain --ignored` は、再生成できるキャッシュ（`.venv/`・`__pycache__/`）のほかに変わっていない。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-17 12:57Z ごろ）から Spec の記録まで約 12 分。レビューと PR・Issue の読み込み 約 2 分、変更ファイルと関連の読み込み・自己確認 約 4 分（`run-tests.bash` の待ち時間と重ねた）、検証（`.agents/scripts` の pytest・収集・`check-layout.sh`・`run-tests.bash`）約 8 分（`run-tests.bash` の待ち時間が大半）。
