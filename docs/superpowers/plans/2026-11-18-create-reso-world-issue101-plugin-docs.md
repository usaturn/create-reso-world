# Issue #101 プラグイン文書と最小例 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: `draft`（内容の承認は記録していない。実行許可は Spec の「管理・実行許可」のとおり）

**Goal:** `usaturn/resoloop:feat/plugin-v2` に、プラグイン4機能の利用者・作者向けの文書（英日）と、4機能を全部使う最小例 `examples/plugins/hello/` を足し、文書の手順どおりに実行して出力が一致することを確かめる。

**Architecture:** 文書は `docs/PLUGINS.md`（英語）と `docs/PLUGINS.ja.md`（日本語）に一元化し、README 3種と `skills/codex/resonite-build/SKILL.md` からは短い節で案内する。最小例は Python + uv の `hello` プラグインで、コマンド・スキル・UIX レシピ・tools をそれぞれ1つ持つ。機能コードは変えず、文書の値と出力例はビルドした CLI の実行結果から写す。

**Tech Stack:** .NET SDK 10.0.201（`global.json`）、ResoLoop CLI（`feat/plugin-v2` のビルド）、uv、Python 3、git、Markdown

**Spec:** `docs/superpowers/specs/2026-11-18-create-reso-world-issue101-plugin-docs-design.md`（create-reso-world、文書用ブランチ `docs/create-reso-world-issue-101-plugin-docs`）

## Global Constraints

- コード base: `usaturn/resoloop` `feat/plugin-v2` @ `cae50506401577f840fb22d81ea5aa87d5fa9c2b`。作業ブランチ `feat/create-reso-world-issue-101-plugin-docs`、worktree `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-101-plugin-docs`（以下 `CODE_ROOT`）
- 変えてよいファイル: `docs/PLUGINS.md`、`docs/PLUGINS.ja.md`、`README.md`・`README_JA.md`・`README-DETAILS.md` のプラグインの節、`skills/codex/resonite-build/SKILL.md` のプラグインの段落、`examples/plugins/hello/` の下。ほかは変えない（`src/`・`tests/`・`*.csproj` を含む）
- 上流 main が変えた行に触れない: `README-DETAILS.md` の 196〜237 行目付近と 373〜378 行目付近、`SKILL.md` の 47〜62 行目付近
- 名前: プラグイン `hello`、コマンド `hello`、スキル `hello-guide`、レシピのローカル名 `hello-card`（外部名 `hello:hello-card`）、prototype `hello.card`、tools `uv`（doctor の項目 `plugin:hello:uv`）
- 対応版: `"resoloop": {"minVersion": "0.2.0"}`。`maxVersionExclusive` は書かない
- README と README-DETAILS から docs・examples へのリンクは GitHub の絶対 URL `https://github.com/usaturn/resoloop/blob/feat/plugin-v2/<path>`（ディレクトリは `/tree/feat/plugin-v2/<path>`）。`docs/PLUGINS.md` と `docs/PLUGINS.ja.md` の間のリンクと、文書から `examples/` への相対リンクはそのままでよい（どちらも pack されない）
- 文書に書く値（上限・既定値・メッセージ・エラーコード・出力）は `CODE_ROOT` のコードとビルドした CLI の実行結果から写す。Spec や Issue の要約から写さない
- 公開版 0.2.0（NuGet）にプラグイン機構は無い。文書はプラグインを `feat/plugin-v2` の機能として書き、出力例に「0.2.0 の feat/plugin-v2 で確認」と注記する（日本語版も同じ意味の注記）
- 常設のテストは足さない（AGENTS.md「テストの採用基準」の F。Spec E12）
- `CODE_ROOT` の中に、コミットしないファイルを残さない（`bin/`・`obj/` などのビルドの出力は除く）。実行照合の導入元・ワールドのプロジェクト・一時 Git リポジトリは `mktemp -d` で Git 管理外に作る。`examples/plugins/hello/` の中で `uv run`・`uv sync` を実行しない（`.venv` ができる）。`uv lock` だけを実行してよい

## Review Focus

- Git 管理下の場所へコピーした導入元: 利用者が例を別の Git リポジトリの中（ルートでない場所）へコピーすると `PLUGIN_SOURCE_INVALID` になる。文書のクイックスタートが「Git 管理外にコピーするか、コピー先で `git init` してそのルートを渡す」と案内し、その両方を実行照合で通す（Task 2・Task 5）
- 空白と日本語を含むパス: ワールドのプロジェクトと導入元のパスに空白・日本語があっても、文書のコマンド（引用の付け方を含む）がそのまま動く（Task 5 で `作業 ワールド` を使う）
- コマンド名より後ろの引数: `--json`・`--`・空文字・`--project=x` をプラグインへそのまま渡すことを、`hello` の出力で確かめ、文書の例と一致させる（Task 1・Task 5）
- `package/` を変えない実行: `uv run --locked` と Python の実行が `package/` に書き込まず、2回目以降の実行・`plugin list` で `PLUGIN_MODIFIED` にならない（Task 1・Task 5）
- remove の後に残るもの: `plugin remove hello --yes` が `.resoloop/plugins/hello/`（`data/` を含む）を消し、配った `.agents/skills/hello-guide/` を残す。文書の注意と一致させる（Task 1・Task 5）

## 受け入れ基準

- 動作環境: Linux の本 Dev Container。.NET は `global.json`（SDK 10.0.201、`rollForward: latestPatch`）。uv と git はコンテナのもの。Windows は実行しないので確認済みと報告しない（PR の Windows CI の結果は CI の結果として別に書く）。Resonite・Blender・認証情報は使わない
- 実入力: `examples/plugins/hello/` を `mktemp -d` の Git 管理外の場所へコピーした導入元（パスに `導入 元` を含める）と、そのコピーを `git init` して commit した一時 Git リポジトリ（ローカルのルートとして、また `file://` URL と `--ref main` で導入）。ワールドのプロジェクトは `mktemp -d` の下の `作業 ワールド` に `resoloop init` で作る。`hello` へ渡す引数は `--json`・`--`・空文字・`日本語 引数`・`--project=x` を含む。doctor の不足の出方は導入元のコピーの manifest の `tools` に `{"name": "missing-tool", "executable": "resoloop-hello-missing-tool", "versionArgs": ["--version"], "required": true}` を足した一時的な導入元で1回確かめる（項目は `plugin:hello:missing-tool`。最小例には足さない）
- 文書の内容: `docs/PLUGINS.md` と `docs/PLUGINS.ja.md` が D-1〜D-6 と4機能を説明し、導入・一覧・削除、`plugin remove` が `data/` を消す注意、コマンドの呼び出しの取り決め、スキル・レシピの配布、manifest の書き方、導入元の確かめ方と記録との照合、信頼・ハッシュ・サンドボックスの違い、現行の利用条件（旧不具合の追跡状況と分けて書く）、`init`・`skills sync` のテキスト出力にプラグインの結果が出ないこと（`--json` の `plugins` を見る）が書かれている。`README.md`・`README_JA.md` のプラグインの節から `docs/PLUGINS.md`（日本語版は `docs/PLUGINS.ja.md`）へ辿れる
- 実行照合: 文書の手順どおりに Spec E13 の代表操作を1回ずつ実行し、文書に載せた help と出力が、パスなどの置き換え（文書に置き換えの規則を書く）を除いて実際と一致する。スキルは `.agents/skills/hello-guide/SKILL.md` が package の内容と同じバイト列、レシピは `uix recipe describe hello:hello-card`・`uix recipe export` の出力と `$recipe` を使った宣言の `validate` の成功、doctor は `plugin:hello:uv` の項目が文書の期待どおりであること（本体の項目の失敗と分け、`ready: true` は要求しない）、remove の後に `.resoloop/plugins/hello/` が無く `.agents/skills/hello-guide/` が残ること
- 防御範囲: 文書にするのは4機能と D-1〜D-6 のそのままの仕様で、縮小・再設計しない。ハッシュは署名でもサンドボックスでもないこと、悪意ある同一ユーザへの完全な防御は対象外であることを書き、防げるものとして書かない。対象外（してはいけない例）: 旧例の `maxVersionExclusive: 0.2.0` をコピーする、ResoLoop リポジトリの下位ディレクトリをそのまま `plugin install` に渡す案内をする、open の状態だけで #110〜#112 を未修正と書く（文書には Issue 番号を書かない）、公開版 0.2.0 にプラグインがあると書く、上流で変わった行や所有範囲の外の節を変える、機能コード・テストを変える
- 英日: `docs/PLUGINS.md` と `docs/PLUGINS.ja.md`、`README.md` と `README_JA.md` のプラグインの節で、見出しの順と内容（コマンド・値・注意）が対応している
- 回帰: `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build` が成功する

## 要件照合（Spec の条件 → Task）

| Spec の条件 | 担当 Task | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 最小例が4機能を持ち、`package/` を変えずに動く（B1〜B3、E1〜E7） | Task 1 | install・実行・sync・recipe・doctor・remove が成功し、2回目の実行の後も `plugin list` に問題が無い | Task 1 の Step 3、Task 5 |
| 英語の文書が D-1〜D-6・4機能・安全・エラーを説明する（A2、A4、A5、4.1） | Task 2 | 6章の見出しと各章の項目がある。出力例が実際と一致する | Task 2 の自己点検、Task 5 |
| 日本語の文書が英語版と対応する（A1、A6、R8） | Task 3 | 見出しの順と内容が対応し、yomiyasu の検査を通した | Task 3 のレビュー（司令塔が yomiyasu を実行）、Task 5 |
| README 3種と SKILL.md の節（A3、C1、C5、E10、E11） | Task 4 | 英日の節が対応し、絶対 URL で辿れる。上流で変わった行に触れていない | Task 4 の Step 4、Task 5 |
| 文書の手順どおりの実行照合と回帰（受け入れ基準の実行照合・回帰） | Task 5（統合担当、司令塔） | 文書のコマンドを写したスクリプトがすべて期待どおり。build・test が成功 | Task 5 |
| C6 の別 Issue | PR の作成時（Plan の外、司令塔） | Issue が起票され、PR と相互にリンクされる | `gh issue view` |

共有する前提（複数の Task が使う値）: Global Constraints の名前・URL・対応版・注記の文言、Task 1 の Interfaces。これらの照合は Task 5 が受け持つ。

## 実行予算

- Issue 全体の能動時間: 600 分（Issue の見積もり 6〜12 時間、Task 5 件、外部担当への依頼とレビュー2件を含む）。ledger は `/workspaces/reso-world/tmp/agents/issue-101.pqf8trrw/budget.jsonl`
- phase の目安: 準備・Spec・レビュー 150 分 / Task 1〜4（runner の担当）240 分 / Task 5 と最終レビュー 90 分 / PR・CI・Issue 更新 60 分 / 予備 60 分
- worker の期限: 実装の担当（`claude-code_sonnet_xhigh`）は runner の `implement` の役割の期限 90 分。runner が停止を確かめるので、司令塔は `task_watch.py` の打ち切りを宣言しない（共有の feature worktree に書く担当は打ち切りの対象外）
- 再試行の上限: 同じ Task の `retry`・`rejected` は1回まで（同じ失敗の再試行1回）。Task のレビュー指摘の修正の依頼は Task ごとに2回まで
- checkpoint: 各 Task の取り込み後、予算の 50%（300 分）と 100%、担当の失敗の直後
- 縮小・切り出し・方法変更の候補: (1) 日本語版の分量を英語版と同じ見出し・同じ項目のまま短くする (2) 出力例を install・list・remove・doctor の4つに絞る（A4 の最低限） (3) Git URL の実演を文書の説明と実行照合だけにする (4) 担当の失敗が続いたら、利用者に担当の変更を尋ねる（自分で引き取らない）

## contingency（代替策）

| 起きたこと | 切り替える条件 | 代替策 |
| --- | --- | --- |
| `uv run --project ${pluginRoot} --locked` が `package/` に書き込み、`PLUGIN_MODIFIED` になる | Task 1 の Step 3 で2回目の実行か `plugin list` が問題を示す | `args` に `--no-sync` や `--frozen` を足すか、`UV_CACHE_DIR` などを `${pluginData}` に向ける形を試す。仕様の意味（Python + uv、`package/` を変えない）を保てる最小の変更を ledger に残す。保てなければ止まって報告する |
| uv が Python を取得できない・`requires-python` が合わない | Task 1 の Step 3 で起動に失敗 | `requires-python` をコンテナの Python に合う範囲に広げる。ネットワークに依存する形は文書の前提として書く |
| `uix recipe describe`・`export`・`validate` がレシピを拒否する | Task 1 の Step 3 | prototype を Slot だけの形（`tests/fixtures/plugins/integration/package/recipes/card.json` と同じ形）に縮める（Spec E5） |
| doctor が接続の待ちで長くかかる | Task 1 の Step 3 で 60 秒を超える | 文書と照合では `--url ws://127.0.0.1:1` を付けた形を使い、その理由を文書に書く |
| 文書の例と実際の出力が違う | どの Task でも | 文書を実際に合わせる。実際の挙動が D-1〜D-6 と違い、機能コードの不具合と考えられるときは、文書を直さずに止まり、司令塔が報告する（機能コードは変えない） |
| 実装の担当が `failed`・上限の `retry`/`rejected` | runner の verdict | その Task で止まり、利用者に報告する。自分で引き取らない |
| base（`feat/plugin-v2`）が前進した | `recheck_bases` の失敗 | issue-to-pr の「未 push の base 前進からの復帰」に従う |

---

### Task 1: 最小例 `examples/plugins/hello/`

**テストの要否:** 常設のテストは足さない（文書の例で、壊れたら実行照合で必ず気付く L/F）。代わりに Step 3 の実行照合を行う。

**Files:**
- Create: `examples/plugins/hello/resoloop-plugin.json`
- Create: `examples/plugins/hello/pyproject.toml`
- Create: `examples/plugins/hello/uv.lock`（`uv lock` で作る）
- Create: `examples/plugins/hello/hello.py`
- Create: `examples/plugins/hello/skills/hello-guide/SKILL.md`
- Create: `examples/plugins/hello/recipes/hello-card.json`

**Interfaces:**
- Consumes: なし
- Produces: Global Constraints の名前。`hello` の出力形式（テキストは argv を1行に1つ、続いて `RESOLOOP_PLUGIN_NAME`・`_COMMAND`・`_ROOT`・`_DATA`・`_PROJECT_ROOT`・`_HOST_ARGV`・`_HOST_VERSION` を `NAME=value` で1行に1つ。引数に `--json` があれば `{"argv": [...], "env": {...}}` の JSON 1つ）。終了コード 0。Task 2〜5 はこの出力を文書と照合する

- [ ] **Step 1: 6つのファイルを書く**

`resoloop-plugin.json` は Spec 4.2 の表のとおり（`program: "uv"`、`args: ["run", "--project", "${pluginRoot}", "--locked", "python", "${pluginRoot}/hello.py"]`）。`pyproject.toml` は依存の無い仮想プロジェクト（`[tool.uv] package = false`）。`hello.py` は標準ライブラリだけを使う。`SKILL.md` は frontmatter の `name: hello-guide` と `description`、`resoloop hello` の呼び方の数行。`hello-card.json` は `{"prototypes": {"hello.card": {...}}}` で、Component の型名は `src/RLoop.Core` の組み込みレシピ（`UixRecipes`）か既存の `examples/` が使う型だけを使う。manifest の `recipes[0]` は `prototype: "hello.card"`、`purpose`、`parameters: {"key": "..."}`。`tools[0]` は `{"name": "uv", "executable": "uv", "versionArgs": ["--version"], "required": true, "hint": "..."}`

- [ ] **Step 2: `uv lock` で `uv.lock` を作る**

Run: `uv lock --project examples/plugins/hello`
Expected: `examples/plugins/hello/uv.lock` ができ、`.venv` はできない（`git status --porcelain --ignored examples/plugins/hello` に `.venv` が無い）

- [ ] **Step 3: ビルドした CLI で4機能を通す**

`dotnet build ResoLoop.slnx` の後、`mktemp -d` の中に `resoloop` のラッパー（`exec dotnet "$CODE_ROOT/src/RLoop.Cli/bin/Debug/net10.0/resoloop.dll" "$@"`）を作って `PATH` の先頭に置く。別の `mktemp -d` に `git -C "$CODE_ROOT" archive HEAD examples/plugins/hello` を展開して導入元（パスに空白と日本語を含める）にし、`resoloop init "<tmp>/作業 ワールド"` のプロジェクトで次を順に実行する。

| 操作 | Expected |
| --- | --- |
| `resoloop plugin install "<source>" --project "<project>"` | 終了コード 0 |
| `resoloop plugin list --project "<project>"` と `--json` | `hello` が問題なしで表示される |
| `resoloop --project "<project>" hello --json -- "" "日本語 引数" --project=x` と、引数なしの `resoloop --project "<project>" hello` | 終了コード 0。argv がそのまま出る。2回目の実行の後も `plugin list` に問題が無い |
| `resoloop skills sync "<project>" --update --json` | `plugins` に `hello-guide`。`<project>/.agents/skills/hello-guide/SKILL.md` が package と同じ内容 |
| `resoloop uix recipe describe hello:hello-card --project "<project>"`、`uix recipe export hello:hello-card --output "<project>/hello-card.json" --project "<project>"` | 終了コード 0。出力に `hello:hello-card` |
| `$recipe` を使う宣言（`{"$recipe":"hello:hello-card","$with":{"key":"demo"}}` を `children` に置いた schema v1 の文書を `<project>/content/` に置く）の `resoloop validate` | 成功 |
| `resoloop doctor --json --project "<project>" --url ws://127.0.0.1:1` | `plugin:hello:uv` の項目が成功。本体の接続の項目は失敗でよい |
| `resoloop plugin remove hello --yes --project "<project>"` | `.resoloop/plugins/hello/` が無く、`.agents/skills/hello-guide/` が残る |

各操作の実際の出力を担当の報告に入れる。期待と違えば contingency に従う。実行に使った一時ディレクトリは最後に消す（`rm -rf -- "${T:?}"` の形）。

- [ ] **Step 4: Commit**

```bash
git add examples/plugins/hello
git commit -m "docs(examples): add the hello plugin covering commands, skills, recipes and tools (create-reso-world#101)"
```

### Task 2: 英語の文書 `docs/PLUGINS.md`

**テストの要否:** 足さない（文書の固定値テストは F）。代わりに、文書のコマンドを実行して出力を照合する（Step 2）。

**Files:**
- Create: `docs/PLUGINS.md`

**Interfaces:**
- Consumes: Task 1 の名前と出力形式
- Produces: 6章の見出し（`## Overview`・`## Quick start`・`## For users`・`## For authors`・`## Safety and limits`・`## Errors`）。Task 3 は同じ順の日本語の見出しにし、Task 4 は `docs/PLUGINS.md` の絶対 URL を使う。出力例の注記「Verified with ResoLoop 0.2.0 on feat/plugin-v2」と、パスの置き換えの規則（`<project>`・`<source>` など）

- [ ] **Step 1: 6章を書く**

Spec 4.1 の各章の項目をすべて入れる。クイックスタートは Task 1 の Step 3 の手順を利用者向けにした形（`examples/plugins/hello/` を Git 管理外へ `cp -r` するか、コピー先で `git init` してそのルートを渡す。Git URL は `file://` の例と `--ref`）。manifest の欄は表にし、型・必須・上限を `PluginManifest.cs` から写す。環境変数は `PluginRuntimeEnvironment.cs`、エラーは各コードを投げる箇所から意味を写す。`init`・`skills sync` のテキスト出力にプラグインの結果が出ないことと、`SKILL_SYNC_REQUIRED` の文言が同梱スキル前提であることを、利用者向けの章に書く。doctor の終了コードと `ready` の読み方を書く。導入元の確かめ方には `plugin install --json` の `commit` と `install.json` の `commit` を使う（`plugin list` はコミットを出さない）。リンクの条件は、ローカル導入元のパスはリンクを解決した実体で判定し、管理領域とコピーする導入元の中のリンクは拒否する、と書く（`PluginPathPolicy.cs`・`PluginGit.cs`・`PluginInstallerTests.cs` で確かめる）。Spec 4.1 の「Safety and limits」に挙げた利用条件（導入元とプロジェクトの重なり、Git 外の導入元の `.git` の拒否、ignore されたファイル、スキルの配布が祖先を探さないこと、`--ref` の必須、失敗した導入の片付け）を入れ、D-2〜D-6 の各項に対応する利用条件・拒否条件をほかにもコードとテストで確かめて書く。doctor の不足の出方は受け入れ基準の「実入力」の一時的な導入元（`missing-tool`）で実行した出力から写す（最小例には足さない）

- [ ] **Step 2: 文書のコマンドを実行して出力を照合する**

Task 1 の Step 3 と同じ準備で、文書に書いたコマンドを書いた順に実行し、文書の出力例（置き換えの規則を当てたもの）と一致することを確かめる。help の行は `resoloop help` の出力と一字ずつ比べる。違えば文書を直す

- [ ] **Step 3: Commit**

```bash
git add docs/PLUGINS.md
git commit -m "docs: add the plugin guide for users and authors (create-reso-world#101)"
```

### Task 3: 日本語の文書 `docs/PLUGINS.ja.md`

**テストの要否:** 足さない（F）。代わりに、英語版との見出し・コマンド・値の対応と、yomiyasu の検査で確かめる。

**Files:**
- Create: `docs/PLUGINS.ja.md`

**Interfaces:**
- Consumes: Task 2 の見出し・出力例・置き換えの規則
- Produces: `docs/PLUGINS.ja.md` の6章（`## 概要`・`## クイックスタート`・`## 利用者向け`・`## 作者向け`・`## 安全と制限`・`## エラー`）。Task 4 の日本語の節がリンクする

- [ ] **Step 1: 英語版と同じ見出しの順・同じ内容で書く**

コマンド・出力例・値・エラーコードは英語版と同じものを使う（出力例は訳さない）。日本語は create-reso-world の AGENTS.md「日本語表現」と yomiyasu の決まり（意味・条件・数値・未確認の事項を変えない、補助動詞のひらがな、大げさな名詞を使わない）に従う。両文書の先頭に、もう一方の言語版への相対リンクを置く

- [ ] **Step 2: yomiyasu の検査を実行する**

Run: `uv run --no-project python /home/vscode/.claude/plugins/cache/yomiyasu/yomiyasu/3.2.0/skills/yomiyasu/scripts/yomiyasu_lint.py --doc-type manual - < docs/PLUGINS.ja.md`
Expected: error 0 件。warn・info の候補を1か所ずつ読み、直すか残す理由を報告に書く。スクリプトを実行できなければ、報告に `not_run` と理由を書く（司令塔が Task のレビューで実行する）

- [ ] **Step 3: Commit**

```bash
git add docs/PLUGINS.ja.md docs/PLUGINS.md
git commit -m "docs: add the Japanese plugin guide (create-reso-world#101)"
```

### Task 4: README 3種と SKILL.md の節

**テストの要否:** 足さない（F）。代わりに、リンク先の実在と、上流で変わった行に触れていないことを `git diff` で確かめる。

**Files:**
- Modify: `README.md`（「Blender modeling」の節の後、「Learn more」の前に `## Plugins`。既存の「Learn more」は変えない）
- Modify: `README_JA.md`（同じ位置に `## プラグイン`。既存の「さらに詳しく」は変えない）
- Modify: `README-DETAILS.md`（「Codex Skills」の節の後、「Tests」の前に `## Plugins`）
- Modify: `skills/codex/resonite-build/SKILL.md`（手順の一覧の後、「Automatic connection discovery」の前に1段落）

**Interfaces:**
- Consumes: Task 2・Task 3 のファイル名、Global Constraints の URL の形
- Produces: なし

- [ ] **Step 1: README.md と README_JA.md の節を書く**

4〜6行。プラグインでできることを1〜2文、`resoloop plugin install`・`resoloop plugin list` と `resoloop [--project DIR] COMMAND` の例、`feat/plugin-v2` の機能で NuGet の 0.2.0 には無いこと、`docs/PLUGINS.md`（日本語は `docs/PLUGINS.ja.md`）と `examples/plugins/hello/` への絶対 URL。英日の意味をそろえる

- [ ] **Step 2: README-DETAILS.md の節を書く**

`plugin install/list/remove`、プラグインのコマンド、`skills sync`、`uix recipe`、`doctor` の簡潔な表と、`docs/PLUGINS.ja.md`・`examples/plugins/hello/` への絶対 URL。この文書の既存の書き方（日本語の地の文）に合わせる

- [ ] **Step 3: SKILL.md の段落を書く**

英語で2〜3行。プロジェクトにプラグインがあれば `resoloop plugin list --json` で確かめ、`resoloop [--project DIR] COMMAND` で呼ぶ。コマンド名より後ろの引数はプラグインに渡ること。詳細の案内は既存の段落と同じく「`docs/PLUGINS.md` in the resoloop repository」と書く（このファイルは pack されて利用者のプロジェクトへ配られるので、プロジェクトの中の相対パスとして読める書き方にしない）

- [ ] **Step 4: 差分の範囲を確かめる**

Run: `git diff --stat cae50506 -- README.md README_JA.md README-DETAILS.md skills/codex/resonite-build/SKILL.md` と `git diff -U0 cae50506 -- README-DETAILS.md skills/codex/resonite-build/SKILL.md`
Expected: 追加の行だけで、削除・変更の行が無い。追加の位置が上流で変わった行の範囲の外

- [ ] **Step 5: Commit**

```bash
git add README.md README_JA.md README-DETAILS.md skills/codex/resonite-build/SKILL.md
git commit -m "docs: link the plugin guide from the READMEs and the build skill (create-reso-world#101)"
```

### Task 5: 統合の照合（司令塔）

**テストの要否:** 足さない。この Task 自体が実行照合である。

**Files:**
- なし（`CODE_ROOT` を変えない。スクリプトとログは `/workspaces/reso-world/tmp/agents/issue-101.pqf8trrw/walkthrough/` に置く）

**Interfaces:**
- Consumes: Task 1〜4 の成果

- [ ] **Step 1: 文書のクイックスタートと利用者向けの章のコマンドを写したスクリプトを作り、新しい一時ディレクトリで実行する**

受け入れ基準の「実入力」と「実行照合」をすべて通す。ローカルの Git 管理外の導入元、`git init` したルート、`file://` URL と `--ref main` の3つの導入元を使う。Git URL の導入では、`plugin install --json` の `commit` と `<project>/.resoloop/plugins/hello/install.json` の `commit` が、一時リポジトリの `git rev-parse main` と一致することを確かめる（`plugin list` はコミットを出さない）。リンク経由のローカル導入元（導入元へのディレクトリの symlink）が受け付けられ、実体のパスが記録されることも1回確かめる。受け入れ基準の「実入力」の一時的な導入元（`missing-tool`）で、doctor が `plugin:hello:missing-tool` を不足として示し、その出方が文書と一致することも1回確かめる。出力を文書の例と比べ、違いを一覧にする

- [ ] **Step 2: 回帰を確かめる**

Run: `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build`（`CODE_ROOT` で）
Expected: どちらも終了コード 0

- [ ] **Step 3: 英日の対応と範囲を確かめる**

`docs/PLUGINS.md` と `docs/PLUGINS.ja.md` の見出しを並べて比べる。README の英日の節を比べる。`git diff --name-only cae50506...HEAD` が所有範囲のファイルだけであること。`git status --porcelain --ignored` で `CODE_ROOT` にビルドの出力以外の未追跡ファイルが無いこと。`README_JA.md` の節・`README-DETAILS.md` の節・`docs/PLUGINS.ja.md` に yomiyasu の検査を実行する（記録は `--state-dir` でセッションディレクトリに置く）

- [ ] **Step 4: 違いがあれば、担当に修正を依頼する**

指摘は原文のまま担当に渡す（AGENTS.md の SDD 実行運用）。修正の後、Step 1〜3 をやり直す

## 完了

- コード: `usaturn/resoloop` の `feat/create-reso-world-issue-101-plugin-docs`、base `cae50506`、検証した HEAD `5b1a179c419c21e77198a0e619b4bf557ef4c5bd`（作業ツリーは clean）
- コミット: Task 1 `3689b096`、Task 2 `bdc2730e`（2回目の依頼）と修正 `99ad929a`、Task 3 `db8a8511` と修正 `eb7aa353`、Task 4 `978cfbdd`、最終レビューの修正 `5b1a179c`
- 実行方式: Task 1〜4 と各修正を agent-runner の `claude-code_sonnet_xhigh`（観測したモデル `claude-sonnet-5-5`）に1つずつ依頼し、Task のレビューと最終のブランチ全体のレビューは司令塔のサブエージェント（Task 1・4 と再レビューは sonnet、Task 2・3 と最終レビューは opus）が行った。Task 5 は司令塔が行った
- 依頼の回数と所要時間（runner の elapsed）: Task 1 は1回（187 秒）。Task 2 は3回で、1回目は空値ガードの無い `rm` が承認待ちになり `failed`（1075 秒、取り込まない）、利用者の決定で同じ担当に依頼し直した2回目（1179 秒）と、レビューの修正（485 秒）。Task 3 は2回（747 秒と修正 61 秒）。Task 4 は1回（114 秒）。最終レビューの修正は1回（446 秒）
- Task 5 の検証（司令塔、HEAD `5b1a179c`、Linux の本 Dev Container）:
  - `dotnet build ResoLoop.slnx`: 終了コード 0、警告 0
  - `dotnet test ResoLoop.slnx --no-build`: 終了コード 0（RLoop.Tests 592 件、RLoop.IntegrationTests 22 件、失敗 0）
  - 文書の bash ブロックを書かれた順に実行し、続く出力ブロックと置き換えの規則で照合した（プロジェクトは `作業 ワールド`）。英語版・日本語版とも bash 18、出力 25 がすべて一致
  - 追加の照合 15 項目がすべて成功: `git init` したルートのローカル導入、ResoLoop の checkout の下位ディレクトリの拒否（`PLUGIN_SOURCE_INVALID`）、リンク経由の導入元と実体のパスの記録、`file://` と `--ref main` の導入で `plugin install --json` と `install.json` の `commit` が一時リポジトリの SHA と一致、`plugin list --json` にコミットが出ない、`missing-tool` を足した一時的な導入元の doctor（`plugin:hello:uv` は pass、`plugin:hello:missing-tool` は fail、終了コード 0、`ready: false`）、削除後に `.resoloop/plugins/hello` が無い
  - 英日のコードブロックは、手で書いた構成図2つの注釈を除いて同一。見出し 34 個の順と階層が一致
  - 差分は所有範囲の 12 ファイルだけで、README 3種と `SKILL.md` は追加と、最終レビューで直した節の中の書き換えだけ。上流 main が変えた行には触れていない
  - 日本語（`docs/PLUGINS.ja.md`、README_JA.md と README-DETAILS.md の節、この Spec・Plan）は yomiyasu の検査ツールで意味が変わるおそれのある箇所を確かめた
- 実行していないこと: Windows での実行（PR の Windows CI は CI の結果として別に扱う）、Resonite・Blender
- 所要時間: 着手（2026-11-18 13:40Z ごろ）から Task 5 の完了（16:25Z ごろ）まで約 2 時間 45 分。うち利用者の確認待ち 2 回（base の指定、Task 2 の失敗の後の進め方）。準備・Spec・設計レビュー・Spec レビュー・Plan に約 35 分、Task 1〜4 とレビューに約 105 分、Task 5 と最終レビュー・修正に約 25 分
