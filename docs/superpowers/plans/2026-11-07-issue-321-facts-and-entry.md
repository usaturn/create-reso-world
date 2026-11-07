# Issue #321 現状と食い違う記述の修正と、新規開発の入口の文書 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- 承認: なし。実行の前に、下の「受け入れ基準」の 3 点を利用者に示して確認を得る（`AGENTS.md` の「SDD 実行運用」。`issue-to-pr` で着手した run だけは同スキルに従って省略する）

**Goal:** create-reso-world の CI と公開状態の記述を事実に合わせ、対象の説明を書き直し、新規開発の入口 `docs/new-development.md` を作る。

**Architecture:** 文書だけの変更。CI の事実（Task 1）、対象の説明と入口の文書（Task 2）、`README.md` の「構成」「対象外」（Task 3）、受け入れの確認と記録（Task 4）に分ける。各 Task は担当の節だけを変え、ほかの子・#103 の担当箇所に触れない。

**Tech Stack:** Markdown、Bash のコメント、`git grep`、`gh api`、`uv run --no-project python`（一時のリンク確認）

**Spec:** `docs/superpowers/specs/2026-11-07-issue-321-facts-and-entry-design.md`

## Global Constraints

- 作業場所は `.worktrees/issue-321-facts-and-entry`（ブランチ `docs/issue-321-facts-and-entry`、基準 `4aa1ca04e51ec4bfe75873455e5465248edf2b81`）。親の checkout では追跡ファイルを編集しない
- 変えてよいのは Spec の「変えるもの」の表だけ。`AGENTS.md` の「リポジトリ境界」「ResoLoop の版管理」「Spec・Plan の保存と公開」、`README.md` の「Meshy から小物を取り込む」「ResoLoop の版」「テスト」、`.github/workflows/ci.yml`、`scripts/`・`templates/`・`.agents/`・`tools/`、ほかの `docs/` を変えない
- `README.md` の「構成」の `├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、meshy.py（生成・変換）、check-layout.sh（レイアウト検査）` の行は 1 文字も変えない（#103 の担当の `meshy.py（生成・変換）` を含む）
- `AGENTS.md` の「GitHub Actions」の 2 行目（登録済み通常ツールの CI の照合）と 3 行目（CI を作らない、新しいリポジトリの Actions を無効にする）は 1 文字も変えない
- `docs/new-development.md` のファイル名と見出し「ワールド・モデル」「ツール」「ResoLoop プラグイン」「そのほかの開発」は変えない。まだ無い `docs/new-world-development.md`・`docs/new-tool-development.md`・`docs/new-plugin-development.md` へのリンクを置かない
- テストを足さない（文書の変更。`AGENTS.md` の「テストの採用基準」の F）
- GitHub の Actions の設定を変えない。LICENSE を足さない
- 書く文では「正本」「着地」を使わない（`AGENTS.md` の「日本語表現」）
- push・PR の作成・マージは、利用者の指示があるときだけ行う。push の前に `scripts/scan-before-push.sh` で検査する

## Review Focus

- `README.md` の「構成」のコードブロックで、`meshy.py` の行を書き換えていないか（`git diff` で、その行が `-` に出ないこと）
- 直した文が「Actions が無効だから CI の確認をしない」を create-reso-world だけに言い、usaturn/resoloop の CI を確認する規則を消していないか
- `docs/new-development.md` の相対リンクが `docs/` からの相対で書かれ、実在するか（`../AGENTS.md` のように親を指すものを含む）
- `README.md` の「対象外」の 2 文目以降（`.devcontainer/README.md` の 102 行目が参照する移植の記録の案内）を消していないか
- `.devcontainer/README.md` のコードブロックのコメントのジョブ名（`CI の devcontainer-tests` など）と 198 行目を、範囲外なのに書き換えていないか

---

## 受け入れ基準

- **動作環境:** Dev Container（Ubuntu 26.04 LTS）の `.worktrees/issue-321-facts-and-entry`。`gh` は usaturn として認証済み。読むのは GitHub の画面（Markdown の表示）とエディタ
- **実入力:** 日本語の Markdown（全角の括弧・読点、`「」` の節名、コードブロック内の罫線 `├──`・`│`）。Bash のコメント 1 行（日本語）。`git grep` の結果（`path:line:本文` の形の複数行）
- **防御範囲:**
  - 対象: create-reso-world を非公開とする記述、料金を CI 停止の理由とする記述、CI が push・PR のたびに動くとする記述（Spec の「基準での grep の結果の分類」で「直す」の 5 件）。対象の説明の 2 か所（`README.md` の冒頭、`AGENTS.md` の「リポジトリ概要」）。`README.md` の「構成」「対象外」
  - 対象外の反例: `scripts/resoloop-meshy.sh:75`（usaturn/resoloop-meshy が private であることで、事実）、`docs/maatlog-poc-porting.md:162`（`ci.yml` があることの記録で、事実）、別の意味の `private`（`.gitignore` の `/private/`、テストの識別子など）は変えない。`.agents/skills/issue-to-pr/evals/scenarios.json:56` は食い違いだが範囲外で、#320 にコメントするだけ
  - 残す規則: `AGENTS.md` の「GitHub Actions」の、Actions が有効な公開リポジトリの CI を確認する規則、登録済み通常ツールの CI の照合、新しいリポジトリの Actions を無効にする規則
- **テスト:** 足さない（F）。代わりの検証は Task 4 のコマンド

## 実行予算

- 全体の能動時間: 90 分（文書 5 ファイルと Spec の追記。似た文書だけの Issue の実績が 1 時間前後）。単純な変更なので ledger は省く（`.agents/execution-budget.md` の「適用範囲」）
- phase の目安: Task 1〜3 で 50 分、Task 4 で 20 分、PR（指示がある場合）で 20 分
- 再試行: 同じ失敗は 1 回まで。`check-layout.sh` か `test-agent-config.bash` が 2 回失敗したら、その Task の変更を見直し、直せなければ止めて報告する
- checkpoint: Task 3 の後と Task 4 の後。予算の 100%（90 分）で止めて報告する
- 縮小の候補: 「構成」の照合（Task 3）を、`tools/`・`scripts/` の 2 行の修正だけに絞る

## contingency（代替策）

- `origin/main` が基準から進み、変える箇所の行番号や文がずれていたら、Spec の「設計の 1」の表の「今の記述」で該当の文を探し直す。文が既に直っていたら、その行は「直す」から外して Task 4 の表に「先に直っていた」と書く
- #103 か #322 が先にマージされ、`README.md` の「構成」の `scripts/` の行や「変更の流れ」の行が変わっていたら、その行の今の文を保ったまま、この Plan の追記だけを rebase で当て直す。#103 の担当の文字列は書き換えない
- PR #327 が先にマージされて `.devcontainer/README.md` が変わっても、171 行目以降の別の節なので、この Plan の箇所はそのまま当てる。衝突したら後からマージする側が rebase する（#320 の運用）
- 受け入れの `git grep` に、表に無い新しい一致が出たら、Spec の分類の表に 1 行足して分類する。範囲のファイルの食い違いなら直し、範囲外なら #320 へのコメントに足す
- `check-layout.sh` が、この変更と関係の無い理由（ローカルのワールドの状態など）で失敗したら、基準の `origin/main` の checkout でも同じく失敗するかを確かめ、関係が無いと示せたら結果を Spec に記録して続ける

---

### Task 1: create-reso-world の CI の記述を事実に合わせる

**Files:**
- Modify: `AGENTS.md`（「GitHub Actions」の 1 行目。基準の 167 行目）
- Modify: `README.md`（「変更の流れ」。基準の 244〜246 行目）
- Modify: `.devcontainer/README.md`（「テストの実行」の 177 行目と 193〜194 行目）
- Modify: `tests/scripts/test-agent-config.bash`（13 行目のコメント）

**Interfaces:**
- Consumes: なし
- Produces: `AGENTS.md` の「GitHub Actions」の 1・2 行目の新しい文（Task 4 が照合する）

テスト: 足さない（F。文書と Bash のコメント）。代わりに Step 5 の検証を行う。

- [ ] **Step 1: `AGENTS.md` の「GitHub Actions」の 1 行目を、次の 2 行に置き換える**

今の行: `- 料金の問題でプライベートの usaturn/create-reso-world の CI は使わず停止しているため、CI の確認は不要。パブリックの CI は停止していない為、確認すること`

```markdown
- usaturn/create-reso-world は公開リポジトリだが、GitHub Actions は無効（`enabled=false`）のままにし、CI の確認は不要。同じ検査をローカルで実行するので、有効にしても時間がかかるだけである。プライベートで開発したい場合もあるので、CI は基本的に無効にする。`.github/workflows/ci.yml` は残してあるが動かない
- Actions が有効な公開リポジトリ（usaturn/resoloop など）の作業では、CI を確認する
```

続く 2 行（「登録済み通常ツールの CI は…」「テストを作っても CI…」）は変えない。

- [ ] **Step 2: `README.md` の「変更の流れ」を次に置き換える**

```markdown
- 変更は作業ブランチで行い、`main` へは PR で入れる。並行作業には `.worktrees/` 配下の worktree を使う（git の追跡対象外）。
- PR を出す前に、下の「テスト」をすべて通す。このリポジトリは公開しているが GitHub Actions を無効にしているので、CI（`.github/workflows/ci.yml`）は動かず、ローカルの実行だけが検査になる（`AGENTS.md` の「GitHub Actions」）。
- push の前に `scripts/scan-before-push.sh` で秘密情報を検査する（`AGENTS.md` の「push の前の秘密情報の検査」）。
- 設計と実装計画（Spec・Plan）の置き場所は `AGENTS.md` の「Spec・Plan の保存と公開」に、運用は `docs/superpowers/README.md` にある。ローカルの下書きは `docs_draft/`（git の追跡対象外）に置く。
```

- [ ] **Step 3: `.devcontainer/README.md` の「テストの実行」の 2 か所を直す**

177 行目を次に置き換える。

```markdown
リポジトリのルートで次を実行する。`.github/workflows/ci.yml` も同じコマンドを定義している（下のコメントのジョブ名はこのファイルのもの。skill-tests のジョブは pytest の `tools` を除く）が、create-reso-world は GitHub Actions を無効にしているので動かない。検査はここでの実行だけである。
```

193〜194 行目の `CI の gitleaks ジョブは … 秘密情報の混入を検査する。private の CI は止めているので、push の前に手元で` を、次の 2 行に置き換える（195 行目の `（ルートの AGENTS.md の…）` 以降は変えない）。

```markdown
`ci.yml` の gitleaks ジョブは `.gitleaks.toml`（既定の規則に、resoloop の識別子と偽のトークンの除外を足したもの）で
秘密情報の混入を検査するが、Actions を無効にしているので動かない。push の前に手元で `scripts/scan-before-push.sh` を実行する
```

コードブロックの中のコメントと、198 行目の「CI では Blender によるワールドのビルドは行わない。」は変えない。

- [ ] **Step 4: `tests/scripts/test-agent-config.bash` の 13 行目のコメントを置き換える**

```bash
# create-reso-world は GitHub Actions を無効にしていて CI の gitleaks は動かないので、ローカルで実行するこの検査で直書きを止める
```

- [ ] **Step 5: 検証する**

Run: `git diff --check && bash tests/scripts/test-agent-config.bash`
Expected: `git diff --check` は何も出さず、`PASS: MCP headers use env references`

Run: `git grep -nE 'プライベート|private|料金の問題|ci\.yml' -- AGENTS.md README.md .devcontainer/README.md tests/scripts/test-agent-config.bash`
Expected: 一致は、Step 1〜3 で書いた `ci.yml` は動かないという文と、`AGENTS.md` の「プライベートで開発したい場合もある」の方針の説明だけ。`料金の問題`・`private の CI`・`private リポジトリの CI`・`push と PR のたびに` を含む行が無い

Run: `git diff -U0 AGENTS.md | grep -E '^[-+]' | grep -v '^[-+]{3}'`
Expected: `-` の行は基準の 167 行目だけ、`+` の行は Step 1 の 2 行だけ

- [ ] **Step 6: コミット**

```bash
git add AGENTS.md README.md .devcontainer/README.md tests/scripts/test-agent-config.bash
git commit -m "docs: align CI descriptions with disabled GitHub Actions (#321)"
```

trailer はランタイムが求めるもの（Claude Code なら `Co-Authored-By:` の行）を付ける。

### Task 2: 対象の説明を書き直し、新規開発の入口の文書を作る

**Files:**
- Modify: `AGENTS.md`（「リポジトリ概要」の段落の 1 文目と 2 文目の前半）
- Modify: `README.md`（冒頭の 3〜5 行目）
- Create: `docs/new-development.md`

**Interfaces:**
- Consumes: なし
- Produces: `docs/new-development.md` の見出し `## ワールド・モデル`・`## ツール`・`## ResoLoop プラグイン`・`## そのほかの開発`（#323・#324・#325・#328・#329 が使う）。`AGENTS.md` の「リポジトリ概要」の対象の説明

テスト: 足さない（F）。代わりに Step 4 の検証を行う。

- [ ] **Step 1: `AGENTS.md` の「リポジトリ概要」の段落の先頭を置き換える**

今の先頭: `[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite 上に 3D モデルやワールドを作成する開発環境。Dev Container の定義と共通の規約・スキル・雛形を管理する。`

置き換え後（同じ段落の続き「ワールドのプロジェクトはローカルの作業物で…」以降は変えない）:

```markdown
Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発を行う開発環境。どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）。主に [resoloop](https://github.com/orange3134/resoloop) と Blender を使い、Dev Container の定義と共通の規約・スキル・雛形を管理する。新しく開発を始めるときの入口は `docs/new-development.md` である。
```

- [ ] **Step 2: `README.md` の冒頭の 3〜5 行目を次の 5 行に置き換える**

```markdown
Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発のための開発環境（Dev Container）。
どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）。主に [resoloop](https://github.com/orange3134/resoloop) と Blender を使う。
コーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）で作業する前提で、共通の規約とスキルをリポジトリに置いている。
ワールドのプロジェクトはローカルの作業物であり、このリポジトリでは追跡しない（issue #57）。
新しく開発を始めるときは、[docs/new-development.md](docs/new-development.md) から開発の種類ごとの手順に進む。
```

- [ ] **Step 3: `docs/new-development.md` を作る**

本文は次のとおり（見出しの名前とリンク先はボード #320 で決めたもの。言い回しの小さな調整はよいが、見出し・リンク先・各節の役割は変えない）。

```markdown
# 新規開発の入口

このリポジトリで新しく開発を始めるときに、最初に読む文書。開発の種類ごとに、手順の文書へ案内する。

このリポジトリが対象にするのは、Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発である。どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）。

作業場所、Spec・Plan の置き場所、push の前の検査などの共通の決まりは、ルートの [AGENTS.md](../AGENTS.md) にある。

## ワールド・モデル

Resonite のワールドと、Blender などで作るモデル（ResoLoop のプロジェクト）を新しく作る。手順は [#323](https://github.com/usaturn/create-reso-world/issues/323) で準備中。

## ツール

Resonite 内のツール（装備ツール・操作 UI・ProtoFlux）と、Resonite と連携する外部ツール（独立したリポジトリ）を新しく作る。手順は [#324](https://github.com/usaturn/create-reso-world/issues/324) で準備中。

## ResoLoop プラグイン

ResoLoop のプラグインのリポジトリを新しく作る。準備中: プラグイン機構が上流にマージされ（[#105](https://github.com/usaturn/create-reso-world/issues/105)）、公開版の ResoLoop で使えるようになってから、[#328](https://github.com/usaturn/create-reso-world/issues/328) で手順をまとめる。

## そのほかの開発

新規開発の手順の対象ではないが、既に手順がある開発。

- ResoLoop 本体とプラグイン機構: [resoloop-fork-workflow.md](resoloop-fork-workflow.md)（fork の usaturn/resoloop の運用）と、[#95](https://github.com/usaturn/create-reso-world/issues/95) のボード
- 既存の Meshy プラグイン（usaturn/resoloop-meshy）: [resoloop-meshy-workflow.md](resoloop-meshy-workflow.md)
- Meshy で作る素材: [meshy-resoloop.md](meshy-resoloop.md)
- 登録済みの外部ツールの運用: [external-tools-workflow.md](external-tools-workflow.md)
```

- [ ] **Step 4: 検証する**

Run（一時のリンク確認。ファイルに保存しない）:

```bash
uv run --no-project python - README.md docs/new-development.md <<'PY'
import re, sys
from pathlib import Path
bad = []
for name in sys.argv[1:]:
    path = Path(name)
    for target in re.findall(r"\]\(([^)#]+)\)", path.read_text(encoding="utf-8")):
        if target.startswith("http"):
            continue
        if not (path.parent / target).exists():
            bad.append(f"{name}: {target}")
print("\n".join(bad) or "OK: all relative links exist")
sys.exit(1 if bad else 0)
PY
```

Expected: `OK: all relative links exist`

Run: `grep -n '^## ' docs/new-development.md`
Expected: 次の 4 行がこの順で出る: `## ワールド・モデル`、`## ツール`、`## ResoLoop プラグイン`、`## そのほかの開発`

Run: `grep -nE 'new-(world|tool|plugin)-development' docs/new-development.md README.md AGENTS.md`
Expected: 何も出ない（まだ無い文書へのリンクが無い）

Run: `grep -c 'docs/new-development.md' README.md AGENTS.md`
Expected: `README.md:1`（冒頭の案内の 1 か所。Task 3 の「構成」は `docs/` を付けずに `new-development.md` と書く）と `AGENTS.md:1`（「リポジトリ概要」。Spec の D8）

Run: `git diff --check`
Expected: 何も出ない

- [ ] **Step 5: コミット**

```bash
git add AGENTS.md README.md docs/new-development.md
git commit -m "docs: describe repository scope and add new-development entry (#321)"
```

### Task 3: `README.md` の「構成」と「対象外」を事実に合わせる

**Files:**
- Modify: `README.md`（「構成」のコードブロック、「対象外」の 1 文目）

**Interfaces:**
- Consumes: Task 2 の `docs/new-development.md`（「構成」の `docs/` の行で挙げる）
- Produces: なし

テスト: 足さない（F）。代わりに Step 3 の検証を行う。

- [ ] **Step 1: 「構成」のコードブロックを次に置き換える**

`├── scripts/ …meshy.py（生成・変換）、check-layout.sh（レイアウト検査）` の行は今の文字列のまま残し、その下に続きの行を足す。

```
.
├── AGENTS.md                  共通規約（CLAUDE.md は @AGENTS.md を読み込む）
├── .agents/                   共有スキル（skills/。.claude/skills/ はここへの symlink）、補助スクリプト（scripts/）、監視・実行予算・レビューの手引き
├── .pi/                       pi の設定（プロジェクトを trust すると読まれる。下の「エージェントで作業する」）
├── .devcontainer/             Dev Container の設定、導入スクリプト、テスト（詳細は .devcontainer/README.md）
├── .github/workflows/ci.yml   CI の定義（GitHub Actions を無効にしているので動かない。下の「変更の流れ」）
├── scripts/                   new-world.sh（プロジェクトの作成）、resoloop-fork.sh（fork の運用）、meshy.py（生成・変換）、check-layout.sh（レイアウト検査）
│                              resoloop-meshy.sh（Meshy プラグインの checkout）、scan-before-push.sh（push の前の秘密情報の検査）、
│                              superpowers-review-copy.sh（Spec・Plan の確認用コピー）、setup_pi*.zsh（pi の設定）
├── tools/                     external_tools（登録済み外部ツールの共通 resolver・取得 CLI）、agent_runner（別のエージェントの非対話の起動と結果の回収）、
│                              devenv_migration（pi の設定の移行のテスト）、test_support（共有のテストの fixture）
├── external-tools.toml        通常ツールの登録候補（運用には常設親への採用が必要）
├── templates/world-project/   プロジェクトの雛形
├── docs/                      新規開発の入口（new-development.md）、設計と計画（superpowers/）、fork・Meshy プラグイン・外部ツールの運用、
│                              Meshy の素材、AR 広告と agent-runner の手引き、統合手順、ワールドの記録（worlds/）、設定の移植の記録
├── tests/                     スクリプトのテスト（tests/scripts/）、スキルのテスト（tests/skills/）、テストの fixture（tests/fixtures/）
└── worlds/<name>/             ワールドのプロジェクト（resoloop のプロジェクト。ローカル専用で git の追跡対象外）
```

- [ ] **Step 2: 「対象外」の 1 文目を置き換える**

今の文: `リポジトリの公開と LICENSE の選定、Git LFS、Rebuild を伴う確認の自動化は対象外である。`

```markdown
LICENSE の選定、Git LFS、Rebuild を伴う確認の自動化は対象外である。リポジトリは公開済みだが、LICENSE はまだ選んでいない。
```

続く「Rebuild 後の確認は、…」の 2 文は変えない。

- [ ] **Step 3: 検証する**

Run: `git diff -U0 README.md | grep -F 'meshy.py（生成・変換）'`
Expected: `-` で始まる行が無い（`meshy.py` の行を変えていない）

Run: 「構成」で挙げたパスの実在を確かめる

```bash
for p in AGENTS.md CLAUDE.md .agents/skills .agents/scripts .claude/skills .pi .devcontainer/README.md .github/workflows/ci.yml \
  scripts/new-world.sh scripts/resoloop-fork.sh scripts/meshy.py scripts/check-layout.sh scripts/resoloop-meshy.sh \
  scripts/scan-before-push.sh scripts/superpowers-review-copy.sh tools/external_tools tools/agent_runner \
  tools/devenv_migration tools/test_support external-tools.toml templates/world-project docs/new-development.md \
  docs/superpowers docs/worlds tests/scripts tests/skills tests/fixtures; do
  [ -e "$p" ] || echo "missing: $p"
done; ls scripts/setup_pi*.zsh >/dev/null && echo "OK: paths exist"
```

Expected: `missing:` の行が無く、`OK: paths exist`

Run: `git diff --check`
Expected: 何も出ない

- [ ] **Step 4: コミット**

```bash
git add README.md
git commit -m "docs: update README layout and out-of-scope to current facts (#321)"
```

### Task 4: 受け入れを確かめ、Spec に記録し、範囲外の食い違いを #320 に知らせる

**Files:**
- Modify: `docs/superpowers/specs/2026-11-07-issue-321-facts-and-entry-design.md`（末尾に「実装の確認（YYYY-MM-DD）」の節を足す）

**Interfaces:**
- Consumes: Task 1〜3 のコミット
- Produces: Spec の確認の記録、#320 のコメント

テスト: 足さない。この Task の全体が代わりの検証である。

- [ ] **Step 1: 受け入れの grep を実行し、Spec の分類の表と照らす**

Run: `git grep -nE 'プライベート|private|料金の問題|ci\.yml' -- ':!docs/superpowers' ':!reviews'`
Expected: Spec の「基準での grep の結果の分類」で「直す」とした 5 件が、非公開・料金・push と PR のたびに動く、を言わない文に変わっている。残る一致は、Task 1 で書いた「`ci.yml` は動かない」「プライベートで開発したい場合もある」の文、`.agents/skills/issue-to-pr/evals/scenarios.json:56`、`docs/maatlog-poc-porting.md:162`、`scripts/resoloop-meshy.sh:75`、別の意味の `private` だけ

- [ ] **Step 2: Actions が無効のままであることを確かめる**

Run: `gh api repos/usaturn/create-reso-world/actions/permissions`
Expected: `"enabled":false` を含む

- [ ] **Step 3: 変更の範囲を確かめる**

Run: `git diff --name-only origin/main...HEAD`
Expected: 次の 7 つだけ: `.devcontainer/README.md`、`AGENTS.md`、`README.md`、`docs/new-development.md`、`docs/superpowers/plans/2026-11-07-issue-321-facts-and-entry.md`、`docs/superpowers/specs/2026-11-07-issue-321-facts-and-entry-design.md`、`tests/scripts/test-agent-config.bash`（Spec・Plan は planning の作業で同じブランチにコミット済み）

Run: `git diff origin/main...HEAD -- AGENTS.md | grep -E '^@@'`
Expected: hunk は「リポジトリ概要」（基準の 7 行目付近）と「GitHub Actions」（基準の 167 行目付近）の 2 つだけ

- [ ] **Step 4: リポジトリの検査を実行する**

Run: `bash scripts/check-layout.sh; echo "exit=$?"`
Expected: `PASS: check-layout` と `exit=0`（基準でも成功した）

Run: `bash tests/scripts/test-agent-config.bash`
Expected: `PASS: MCP headers use env references`

- [ ] **Step 5: Spec に「実装の確認」の節を足す**

Step 1〜4 の実行日時、コマンド、結果（grep の一致を 1 行ずつ分類した表、Actions の応答、`git diff --name-only` の結果、検査の終了コード）を書く。状態は `draft` のまま変えない。

- [ ] **Step 6: 範囲外の食い違いを #320 に知らせる（Spec の D4）**

本文をファイルに書いてから投稿する（`--body-file`）。内容: `.agents/skills/issue-to-pr/evals/scenarios.json` の 56 行目が「private の create-reso-world の CI は確かめない」と、非公開を前提にしていること。#321 の範囲外（スキル）なので直していないこと。直す担当は調整役が決めること。

Run: `gh issue comment 320 --repo usaturn/create-reso-world --body-file <書いたファイル>`
Expected: コメントの URL が出る

- [ ] **Step 7: コミット**

```bash
git add docs/superpowers/specs/2026-11-07-issue-321-facts-and-entry-design.md
git commit -m "docs: record #321 acceptance checks"
```

## 反映

- ブランチ `docs/issue-321-facts-and-entry` から `main` への PR を 1 つ作る（利用者の指示があるときだけ）。本文に `Closes #321` と、Spec の「実装の確認」の要約を書く。既存の PR があれば作り直さない
- push は `SHA="$(bash scripts/scan-before-push.sh -C <worktree>)" && [ -n "$SHA" ] && git -C <worktree> push origin "${SHA:?}:refs/heads/docs/issue-321-facts-and-entry"` の形で行う
- マージは利用者が行う（利用者が明示した指示がある場合を除く）。create-reso-world の CI は確かめない
- PR を作ったら、#321 に PR の URL と `implementation: in-progress` を書く。マージされたら #321 は completed で close する
