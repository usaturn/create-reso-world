# Issue #91 open3d のシステムのライブラリ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** rebuild した Dev Container で、手作業の apt なしに open3d 0.20.0 を import できるようにする。

**Architecture:** `.devcontainer/install_beforehand.bash` の基本パッケージの `apt install` の行に `libegl1 libgl1` を足し、`.devcontainer/README.md` に導入の理由を書く。open3d 本体は Dev Container の全体には入れず、使う側が uv で入れる。

**Tech Stack:** bash（postCreate）、apt（Ubuntu 26.04 resolute）、uv、open3d 0.20.0（cp314 manylinux_2_35）

**Spec:** `docs/superpowers/specs/2026-10-16-create-reso-world-issue91-open3d-devcontainer-design.md`

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`、Issue #91（親 #95、子のキー `open3d-devcontainer`）
- 基準 HEAD: `e7eb72a1602ac03e723bc50c9734773102947df1`（`main`）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 実行許可: 2026-10-16（JST）、利用者の「#91 に着手せよ。途中で止めずに推奨案で PR まで作成して」。推奨案での実装、commit、push、PR の作成まで。マージと rebuild は利用者が行う
- 実行方法: Native（このセッションでインライン実行）。エージェントの判断で、利用者に実行方法を選んでもらう段は省いた。Task が 2 つで互いのインターフェースに依存せず、誤りの影響は rebuild 時の apt の失敗（postCreate が ERROR 行を出して止まる）にとどまるため。サブエージェントは利用者が求めていないので使わず、レビューは自己レビューと PR での利用者の確認で行う
- 作業場所: worktree `.worktrees/issue-91-open3d`、ブランチ `feat/issue-91-open3d-devcontainer`

## Global Constraints

- 変えてよいのは `.devcontainer/install_beforehand.bash` の基本パッケージの `apt install` の行と、`.devcontainer/README.md` の導入するものの説明（`python3-numpy` と同じ箇所）だけ（#95 のボード）
- 同じ 2 ファイルの Meshy CLI の段と記述、`STEP_TOTAL` は変えない（#103）
- 足すパッケージは `libegl1`・`libgl1` の 2 つ（Spec D-2）
- テストは足さない（Spec D-5、`AGENTS.md` の「テストの採用基準」）
- 確認のコマンドは `uv run --no-project --with open3d==0.20.0 python -c "import open3d"`
- PR の本文は `Refs #91`（Spec D-7）。CI は作らない・確かめない（private の create-reso-world は Actions 無効）

## Review Focus

- 新しいコンテナで `libegl1`・`libgl1` の候補が見つからない → `apt install` が失敗し、postCreate が `ERROR: apt install of the base packages failed.` で止まること。resolute/main に `1.7.0-3` があることを `apt-cache policy` で確かめる（Task 1 Step 3）
- 既に手で入れてあるコンテナで postCreate を再実行する → `apt install -y` は入れ済みのパッケージを飛ばして成功すること（apt の既定の挙動。手で入れたものは manual のまま）
- 画面の無い環境（`DISPLAY` も `WAYLAND_DISPLAY` も空）で import する → CPU だけの import が成功すること（Task 1 Step 4、今のコンテナは両方空）
- rebuild の後に Blender の依存として入るライブラリ（`libglx0`・`libglvnd0`・X11 系・`libusb-1.0-0`）が欠ける → 今回の 2 つ以外に手で入れたものが無いことを `ldd` と `/var/log/dpkg.log` で確かめる（Task 1 Step 4、結果は Spec の「確認した事実」）
- rebuild の後の import の確認は利用者の rebuild を待つ → Task 2 で、利用者に頼むコマンドと記録先（#91）を PR と Issue に書く

## planning の成果物

#95 の「開始手順」の 4〜7 に従い、Spec・この Plan・handoff の 2 ファイル（`tmp/docs_draft/claude_handoffs/`）を作り、manifest と中身を #91 に公開し、取り出して SHA-256 を照合してから planning: ready にする。そのあと、実行許可にもとづいて下の Task を実行する。

---

### Task 1: apt の行と README

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（「Installing the base packages」のステップの `apt install` の行）
- Modify: `.devcontainer/README.md`（「Resonite ワールド開発ツール」の最初の段落と、その直後に足す段落）

**テストの要否:** 不要。パッケージの一覧と文書の変更で、コードを実行して確かめる挙動が無い。代わりに Step 3〜6 の検証を行う。

**Interfaces:**
- Consumes: なし
- Produces: rebuild の後に `libEGL.so.1`・`libGL.so.1` があること（#90 の入力）

- [ ] **Step 1: apt の行を変える**

```bash
if ! sudo apt install -y vim tig ripgrep fzf jq bubblewrap libglib2.0-0t64 blender python3-numpy libegl1 libgl1; then
```

- [ ] **Step 2: README を変える**

最初の段落の 1 文目を次にする。

```markdown
Dev Container の作成時に .NET 10 SDK、Blender、glTF import / export 用の `python3-numpy`、open3d が読む `libegl1`・`libgl1` を導入し、ResoLoop は NuGet の最新の公開版を
```

「Blender の GUI、ホスト側のネットワーク設定はこのセットアップの対象外とする。」の後に次の段落を足す。

```markdown
`libegl1`・`libgl1` は、Meshy の物の UV の展開（UVAtlas）に使う open3d のためのものである。open3d は CPU だけで使うときも、
import のときに `libEGL.so.1`・`libGL.so.1` を読み、無いと `ImportError` で止まる。open3d 本体は Dev Container の全体には入れず、使う側が uv で入れる。
rebuild の後は `uv run --no-project --with open3d==0.20.0 python -c "import open3d"` で確かめられる（open3d と依存の 59 パッケージを取得し、展開すると 1 GB を超える）。
GPU（CUDA）と open3d の表示機能は対象外とする。
```

- [ ] **Step 3: 構文と候補を確かめる**

Run: `bash -n .devcontainer/install_beforehand.bash && apt-cache policy libegl1 libgl1 | grep -E '^[a-z]|Candidate'`
Expected: 構文エラーなし。`libegl1`・`libgl1` の Candidate が `1.7.0-3`

- [ ] **Step 4: 今のコンテナで import と依存を確かめる**

Run: `uv run --no-project --with open3d==0.20.0 python -c "import open3d; print(open3d.__version__)"`
Expected: `0.20.0`（今のコンテナには手で入れた 2 つがあるので、rebuild の後の証明にはならない。rebuild の後の確認は Task 2）

- [ ] **Step 5: 既存のテストを流す**

Run: `bash .devcontainer/run-tests.bash`
Expected: 最後の行が `PASS: <N> test(s)`。失敗があれば、基準 HEAD（`e7eb72a`）でも失敗するかを確かめて切り分ける

- [ ] **Step 6: 差分を確かめてコミットする**

Run: `git diff --stat && git diff`
Expected: 2 ファイルだけが変わり、Meshy の段・`STEP_TOTAL` に差分が無い

```bash
git add .devcontainer/install_beforehand.bash .devcontainer/README.md
git commit -m "feat(devcontainer): install libegl1 and libgl1 for open3d (#91)"
```

### Task 2: PR と Issue の記録

**Files:**
- Modify: この Plan（実行の記録）

**テストの要否:** 不要。公開と記録の作業。

**Interfaces:**
- Consumes: Task 1 のコミット
- Produces: create-reso-world への PR（`Refs #91`）、#91 の状態のコメント

- [ ] **Step 1: Plan に実行の記録を足してコミットする**（Task 1 の結果、所要時間）
- [ ] **Step 2: push して PR を作る**

```bash
git push -u origin feat/issue-91-open3d-devcontainer
gh pr create --base main --head feat/issue-91-open3d-devcontainer --title "Dev Container に open3d 用の libegl1・libgl1 を入れる（#91）" --body-file <本文>
```

本文には、変更、判断（Spec D-1〜D-7 の要点）、検証の結果、rebuild の後に利用者に頼む確認（`uv run --no-project --with open3d==0.20.0 python -c "import open3d"`）、`Refs #91` を書く。

- [ ] **Step 3: #91 に状態を書く**

`planning: ready`、`implementation: in-progress`（PR 作成済み、マージと rebuild の後の確認待ち）、PR の URL、manifest のコメント、次の作業（利用者のマージ → rebuild → import の確認を #91 に記録 → completed で close）を書く。予約は、まだ自分の SHA のときだけ解放する。
