# Issue #321 現状と食い違う記述の修正と、新規開発の入口の文書

- 状態: completed
- 対象: usaturn/create-reso-world の `main`（基準 `4aa1ca04e51ec4bfe75873455e5465248edf2b81`）
- Issue: [#321](https://github.com/usaturn/create-reso-world/issues/321)（ボード [#320](https://github.com/usaturn/create-reso-world/issues/320) `new-dev-procedures-board` の子 `facts-and-entry`）
- 作成: Claude Code（Opus 5.5）。planning-parallel-issues の手順で、利用者の依頼「#320 着手」による。下の「決めたこと」はエージェントの判断であり、利用者の承認ではない
- 承認: なし（`approved_commit` は未設定）
- Plan: `docs/superpowers/plans/2026-11-07-issue-321-facts-and-entry.md`

## 目的

1. create-reso-world の現状（PUBLIC に移ったが、GitHub Actions は無効のまま）と食い違う記述を直す
2. このリポジトリの対象を、利用者の決定のとおり書き直す: Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発。どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）
3. 新規開発の入口の文書 `docs/new-development.md` の骨組みを作り、`README.md` から辿れるようにする。後続の子（#323・#324・#328）が自分の節に本文を書く

理由: ボード #320 の後続の子は、この文書の見出しと、`AGENTS.md` の「リポジトリ概要」の対象の説明を前提にする。食い違いを残したまま手順の文書を書くと、手順が誤った前提（CI が動く、非公開である）を写す。

## 守る前提（#320 から写す）

利用者の決定（2026-11-07）のうち、この子に関係するもの。議論し直さない。

- create-reso-world は PUBLIC だが、GitHub Actions は無効のままにする。有効にしても、ローカルで同じ検査を実行するので時間がかかるだけである。プライベートで開発したい場合もあるので、CI は基本的に無効にする。記述だけを実態に合わせる
- LICENSE の選定は対象外のままにし、`README.md` の記述だけを事実に合わせる
- 対象は「目的」の 2 のとおり

「ResoLoop の開発との関係」の条件のうち、この子に関係するもの。

- 条件 1: `AGENTS.md` の「リポジトリ境界」「ResoLoop の版管理」、`README.md` の「ResoLoop の版」、`docs/resoloop-fork-workflow.md`、`docs/resoloop-meshy-workflow.md`、`scripts/resoloop-fork.sh`、`scripts/resoloop-meshy.sh` を変えない
- 条件 2: `AGENTS.md` の「GitHub Actions」で、公開リポジトリ（usaturn/resoloop は Actions が有効）の CI を確認する規則を残す
- 条件 3: #103 が担当する箇所（`README.md` の「Meshy から小物を取り込む」の節と「構成」の `meshy.py` の記述、`.devcontainer/README.md` の Meshy の記述）を変えない

## 範囲

### 変えるもの

| ファイル | 範囲 |
| --- | --- |
| `AGENTS.md` | 「リポジトリ概要」の節。「GitHub Actions」の節の 1 行目（create-reso-world の CI の記述） |
| `README.md` | 冒頭、「構成」（`meshy.py（生成・変換）` の文字列を除く）、「変更の流れ」、「対象外」の 1 文目、入口の文書への案内 |
| `.devcontainer/README.md` | 「テストの実行」の節の、create-reso-world の CI の記述（177 行目と 193〜194 行目。下の「決めたこと」の D2） |
| `tests/scripts/test-agent-config.bash` | 13 行目のコメントだけ |
| `docs/new-development.md` | 新規 |
| `docs/superpowers/specs/`・`plans/` | この子の Spec・Plan |

### 変えないもの

- `AGENTS.md` のほかの節と、「GitHub Actions」の 2 行目（登録済み通常ツールの CI の照合）・3 行目（CI を作らない、新しいリポジトリの Actions を無効にする）
- `README.md` の「Meshy から小物を取り込む」「ResoLoop の版」の節、「構成」の `meshy.py（生成・変換）`、「テスト」の節
- `.devcontainer/README.md` のほかの記述。「テストの実行」の節のコードブロックのコメント（`CI の devcontainer-tests` などのジョブ名）と 198 行目「CI では Blender によるワールドのビルドは行わない」は、残す `ci.yml` の内容として正しいので変えない
- `.github/workflows/ci.yml`（D1 で残すと決めた）
- `docs/` のほかの文書、`scripts/`、`templates/`、`.agents/`（スキル）、`tools/`
- GitHub の Actions の設定、LICENSE の追加

## 設計

### 1. 食い違いの直し方

| 箇所 | 今の記述 | 直した後に言うこと |
| --- | --- | --- |
| `AGENTS.md` の「GitHub Actions」の 1 行目 | 料金の問題でプライベートの create-reso-world の CI は使わず停止しているため、CI の確認は不要。パブリックの CI は停止していない為、確認すること | (a) create-reso-world は公開リポジトリだが Actions は無効（`enabled=false`）のままにし、CI の結果は確認しない。理由は利用者の決定のとおり（ローカルで同じ検査を実行する、プライベートで開発したい場合もあるので CI は基本的に無効）。(b) Actions が有効な公開リポジトリ（usaturn/resoloop など）の作業では CI を確認する。(a) と (b) を別の行にする |
| `AGENTS.md` の「リポジトリ概要」の 1 文目 | resoloop と Blender で Resonite 上に 3D モデルやワールドを作成する開発環境 | 「目的」の 2 の対象。主に resoloop と Blender を使う。新規開発の入口は `docs/new-development.md`。2 文目以降（`worlds/`、従来位置、resoloop-meshy）は変えない |
| `README.md` の冒頭（3 行目） | resoloop と Blender で Resonite のワールドを作るための開発環境（Dev Container） | 同上の対象。入口の文書への案内を 1 文足す（「4. README からの案内」） |
| `README.md` の「変更の流れ」（245 行目） | CI（`.github/workflows/ci.yml`）も push と PR のたびに同じ検査を行う | Actions が無効なので `ci.yml` は動かず、ローカルの「テスト」が検査になる。push の前に `scripts/scan-before-push.sh` で秘密情報を検査する（CI の gitleaks ジョブが動かないため） |
| `README.md` の「変更の流れ」（246 行目） | 設計と実装計画は、対象のリポジトリにかかわらず `docs/superpowers/` に置く | 規則を写さず、`AGENTS.md` の「Spec・Plan の保存と公開」と `docs/superpowers/README.md` を案内する（D3） |
| `README.md` の「対象外」（259 行目） | リポジトリの公開と LICENSE の選定、Git LFS、Rebuild を伴う確認の自動化は対象外である | 「リポジトリの公開」を外す。リポジトリは公開済みで、LICENSE は選んでいない（選定は引き続き対象外）ことを書く。2 文目以降（`docs/integration.md` と移植の記録の案内）は `.devcontainer/README.md` の 102 行目が参照するので変えない |
| `README.md` の「構成」 | `tools/` は `external_tools` だけ、`scripts/` は一部だけ | 「3. 構成の照合」 |
| `.devcontainer/README.md` の 177 行目 | CI（`.github/workflows/ci.yml`）も同じコマンドを実行する | `ci.yml` は同じコマンドを定義しているが、create-reso-world は Actions を無効にしているので動かない。コードブロックのコメントのジョブ名は `ci.yml` のもの |
| `.devcontainer/README.md` の 193〜194 行目 | CI の gitleaks ジョブは `.gitleaks.toml` で秘密情報の混入を検査する。private の CI は止めているので、push の前に手元で `scripts/scan-before-push.sh` を実行する | `ci.yml` の gitleaks ジョブも Actions が無効なので動かない。push の前に手元で `scripts/scan-before-push.sh` を実行する |
| `tests/scripts/test-agent-config.bash` の 13 行目 | private リポジトリの CI は停止しており gitleaks も実行されないので、この検査だけが直書きを止める | create-reso-world は Actions を無効にしていて CI の gitleaks は動かないので、ローカルで実行するこの検査で直書きを止める |

### 2. `.github/workflows/ci.yml` の扱い（D1）

残す。Actions は有効にしない。

- 推奨の理由: 利用者の決定は「記述だけを実態に合わせる」で、設定の削除を求めていない。`docs/maatlog-poc-porting.md` の移植の記録（162 行目）が `ci.yml` の存在を記録しており、範囲外の文書を古くしない。`.devcontainer/README.md` のコードブロックのコメントのジョブ名も、そのまま正しい
- 代案（削除）を採らない理由: 範囲外の記録を古くする。利用者が将来 Actions を有効にするときに、検証済みの設定を失う
- 残すことの注意: `ci.yml` は動かないので、ローカルのコマンドとずれても気付かない。文書には「動かない」とだけ書き、ローカルのコマンドを基準にする

### 3. 構成の照合

`README.md` の「構成」のコードブロックを、追跡しているファイルの実態（`git ls-tree --name-only HEAD` とその下）に合わせる。

- `scripts/`: 今の 4 つに、`resoloop-meshy.sh`（Meshy プラグインの checkout）、`scan-before-push.sh`（push の前の秘密情報の検査）、`superpowers-review-copy.sh` とその Python の補助（Spec・Plan の確認用コピー）、`setup_pi*.zsh`（pi の設定）を足す。`meshy.py（生成・変換）` の文字列は変えない（#103）。`meshy_*.py`・`meshy_cli_guard.mjs` は `meshy.py` の補助なので、#103 の担当の記述に入れず、行を足さない
- `tools/`: `external_tools`、`agent_runner`（別のエージェントを非対話で起動して結果を回収する）、`devenv_migration`（pi の設定の移行のテスト）、`test_support`（共有のテストの fixture）
- `docs/`: `new-development.md`（新規開発の入口）を先頭に挙げ、外部ツールの運用、Meshy、AR 広告の手引き、ワールドの記録（`docs/worlds/`）を足す
- `tests/`: `tests/fixtures/` を足す
- `.agents/`: スキルのほか、`scripts/` と、監視・実行予算・レビューの共通の手引きがあることを書く
- 足すトップレベルの行: `.github/workflows/ci.yml`（Actions が無効なので動かない）、`.pi/`（pi の設定）
- 書き直す行では「正本」を使わない（`AGENTS.md` の「日本語表現」）

コードブロックの中の各行の正確な文言は Plan で決める。

### 4. README からの案内

`README.md` の冒頭に 1 文を足し、`docs/new-development.md` へリンクする。Issue の「`README.md` からこの文書への案内を 1 か所置く」は `README.md` の中の数で、`README.md` の案内はこの 1 文だけにする。「構成」の `docs/` の行に `new-development.md` を挙げるのは一覧であり、案内に数えない。

`README.md` の外では、`AGENTS.md` の「リポジトリ概要」にも入口の文書を書く（D8）。

### 5. `docs/new-development.md` の構成

ボード #320 で決めたファイル名と見出しを使う。名前は変えない。

```
# 新規開発の入口
（目的: 新しく開発を始めるときに最初に読む。対象の説明。共通の決まりは AGENTS.md）
## ワールド・モデル        ← 1 行の説明。本文は #323
## ツール                  ← 1 行の説明。本文は #324
## ResoLoop プラグイン     ← 1 行の説明と、#105 を待つ準備中であることと #328 への案内。本文は #328
## そのほかの開発          ← 既存の経路への案内（この子が書く）
```

- 「ワールド・モデル」「ツール」「ResoLoop プラグイン」は、見出しと 1 行の説明だけにする。1 行の中で、手順が準備中であることと担当の Issue を示す
- まだ無い文書（`docs/new-world-development.md`・`docs/new-tool-development.md`・`docs/new-plugin-development.md`）へのリンクは置かない
- 「そのほかの開発」の案内先: ResoLoop 本体とプラグイン機構（`docs/resoloop-fork-workflow.md`、#95 のボード）、既存の Meshy プラグインのリポジトリ（`docs/resoloop-meshy-workflow.md`）、Meshy の素材（`docs/meshy-resoloop.md`）、登録済みの外部ツールの運用（`docs/external-tools-workflow.md`）
- 文書内のリンクは `docs/` からの相対パス、Issue は完全な URL にする（GitHub の画面とローカルの両方で辿れるように）
- Spec・Plan の置き場所の規則は写さず、`AGENTS.md` を案内する（#322 が規則を変えても古くならない）

## インターフェース（この子が決める）

- `docs/new-development.md` のファイル名と 4 つの見出し「ワールド・モデル」「ツール」「ResoLoop プラグイン」「そのほかの開発」。#323・#324・#325・#328・#329 が使う
- `AGENTS.md` の「リポジトリ概要」の対象の説明。全ての子が手順の対象の範囲として使う

## 決めたこと（エージェントの判断）

| 番号 | 決めたこと | 代案と採らない理由 |
| --- | --- | --- |
| D1 | `ci.yml` を残す（設計の 2） | 削除: 範囲外の記録を古くし、利用者の決定「記述だけを実態に合わせる」を超える |
| D2 | `.devcontainer/README.md` の 193〜194 行目も直す。Issue の表には無いが、同じ節の「private の CI は止めている」という同じ食い違いで、Issue の「作業中に見つけた食い違いは、この子の範囲のファイルなら直す」と受け入れの grep の条件に当たる | 直さない: 受け入れの grep で、非公開とする記述が残る |
| D3 | `README.md` の「変更の流れ」の Spec・Plan の 1 文は、規則を写さず `AGENTS.md` の「Spec・Plan の保存と公開」と `docs/superpowers/README.md` を案内する | そのまま残す: #322 が規則を変えると古くなるが、#322 の担当に `README.md` は無い |
| D4 | 範囲外の `.agents/skills/issue-to-pr/evals/scenarios.json` の 56 行目（「private の create-reso-world の CI は確かめない」）は直さず、実装の作業で #320 にコメントする | この子で直す: スキルは範囲外（#321 の「変えないもの」） |
| D5 | `AGENTS.md` の「GitHub Actions」の 1 行目を 2 行に分ける（create-reso-world の扱いと、Actions が有効な公開リポジトリの確認） | 1 行のまま: 2 つの規則が混ざり、条件 2 の規則が読み取りにくい |
| D6 | `docs/new-development.md` に、対象の説明と、共通の決まりは `AGENTS.md` にあるという案内の段落を置く（全体の構成はこの子の担当） | 見出しだけ: 入口として何の文書か分からない |
| D7 | 入口の文書の 3 つの準備中の節は、1 行の中で担当の Issue を完全な URL で示す | Issue を書かない: 読み手が準備状況を辿れない |
| D8 | `AGENTS.md` の「リポジトリ概要」にも、新規開発の入口が `docs/new-development.md` であることを書く。どのエージェントも毎回読むので、後続の子の担当が入口に行き着ける | `README.md` だけにする: エージェントは `README.md` を必ずは読まない |

builder check（別のサブエージェントが、この Spec だけで計画を立てられるかを確かめた。2026-11-07）の問いは 1 件で、入口への案内の数え方の食い違いだった。設計の 4 と D8 で決めた。あわせて受け入れ基準 6 の比較を、`#322` が先にマージされても誤って失敗しない `origin/main...HEAD` にした。

## 受け入れ基準

#321 の「受け入れ」のとおり。

1. 「設計の 1」の表の食い違いがすべて直っている
2. `git grep -nE 'プライベート|private|料金の問題|ci\.yml' -- ':!docs/superpowers' ':!reviews'` の結果に、create-reso-world を非公開とする記述、料金を CI 停止の理由とする記述、CI が push・PR のたびに動くとする記述が残っていない。ただし D4 の範囲外の 1 件は残り、#320 へのコメントで扱う。基準の `4aa1ca04` での結果の分類は下の表。実装の作業は、直した後の結果をこの表と照らして Spec に追記する
3. Actions が無効のまま（`gh api repos/usaturn/create-reso-world/actions/permissions` が `"enabled": false`）
4. `AGENTS.md` の「GitHub Actions」に、Actions が有効な公開リポジトリの CI を確認する規則、登録済み通常ツールの CI の照合、新しいリポジトリの Actions を無効にする規則が残っている
5. `README.md` から `docs/new-development.md` に辿れ、「そのほかの開発」の案内先がすべて実在するパスか Issue である
6. `git diff origin/main...HEAD` の変更が「変えるもの」の中だけにある
7. テストを足していない（文書の変更で、「テストの採用基準」の F に当たる）

### 基準での grep の結果の分類（`4aa1ca04`）

| 一致 | 分類 | 扱い |
| --- | --- | --- |
| `AGENTS.md:167` | 非公開・料金を理由とする | 直す |
| `README.md:245` | CI が push・PR のたびに動くとする | 直す |
| `.devcontainer/README.md:177` | CI が同じコマンドを実行するとする | 直す |
| `.devcontainer/README.md:194` | 非公開とする（private の CI） | 直す（D2） |
| `tests/scripts/test-agent-config.bash:13` | 非公開とする | 直す |
| `.agents/skills/issue-to-pr/evals/scenarios.json:56` | 非公開とする | 範囲外。#320 にコメント（D4） |
| `docs/maatlog-poc-porting.md:162` | `ci.yml` があることの記録 | 事実のまま（D1）。変えない |
| `scripts/resoloop-meshy.sh:75` | usaturn/resoloop-meshy が private であること | create-reso-world の記述ではない。変えない |
| そのほか（`.gitignore` の `/private/`、`docs/integration.md` の `private/trpg/`、テストの `private` の識別子・データ、`private` socket・command・runtime logs など） | 別の意味の `private` | 変えない |

## 依存の証拠（2026-11-07 10:53 UTC）

- #321 は open、`blocked_by` は 0 件、コメントは予約の記録だけ
- 予約: `refs/heads/agent-claims/issue-321` = `9baa6762d08a2e2f36055a0914971a59da362a77`（このセッションの空コミット）
- 開いている PR #327（Issue #326）は `.devcontainer/README.md` の 371 行目以降だけを変え、この子の箇所（177・193〜194 行目）と重ならない
- #103（open）の担当箇所は変えない。`README.md` の「構成」の `scripts/` の行は `meshy.py（生成・変換）` と同じ行なので、#103 と同時にマージするときは後の PR が rebase する（#320 の「衝突したときは、後からマージする PR が rebase する」）

## 検証

- 作業場所: `.worktrees/issue-321-facts-and-entry`（ブランチ `docs/issue-321-facts-and-entry`、最新の `origin/main` から）
- `git diff --check`
- `bash scripts/check-layout.sh`（基準で `PASS`）
- `bash tests/scripts/test-agent-config.bash`（基準で `PASS`）
- 受け入れ基準 2 の `git grep` と、分類の表との照合
- `gh api repos/usaturn/create-reso-world/actions/permissions`
- `README.md` と `docs/new-development.md` の相対リンクの実在の確認（一時のスクリプト。コミットしない）
- `git diff --name-only origin/main...HEAD` と、`AGENTS.md`・`README.md`・`.devcontainer/README.md` の差分の節が「変えるもの」の中だけにあることの確認

## 範囲外

- create-reso-world の Actions を有効にすること、LICENSE を選ぶこと、`ci.yml` を変えること
- `docs/new-world-development.md`・`docs/new-tool-development.md`・`docs/new-plugin-development.md` と、入口の文書の 3 つの節の本文
- Spec・Plan の置き場所の規則（#322）
- スキル（`.agents/skills/`）の中の食い違い（D4 のとおり #320 にコメント）

## 実装の確認（2026-11-07）

実装は issue-to-pr（利用者の指示 `/issue-to-pr #321 --merge`）で行った。planning のブランチ `docs/issue-321-facts-and-entry`（Spec・Plan のコミット済み、claim は解放済み）をそのまま使い、`origin/main` の `afa86e09`（PR #327 を含む）に rebase してから Plan の Task 1〜4 を実施した。`.devcontainer/README.md` の 177・193 行目は PR #327 の後も同じ位置で、重ならなかった。

| コマンド | 結果 |
| --- | --- |
| `git diff --check` | 出力なし |
| `bash scripts/check-layout.sh` | `PASS: check-layout`（終了コード 0） |
| `bash tests/scripts/test-agent-config.bash` | `PASS: MCP headers use env references` |
| `gh api repos/usaturn/create-reso-world/actions/permissions` | `{"enabled":false,...}`（無効のまま） |
| `git diff --name-only origin/main...HEAD` | `.devcontainer/README.md`、`AGENTS.md`、`README.md`、`docs/new-development.md`、Spec、Plan、`tests/scripts/test-agent-config.bash` の 7 つだけ |
| `AGENTS.md` の hunk | 「リポジトリ概要」と「GitHub Actions」の 2 つだけ |
| 相対リンクの実在確認（`README.md`・`docs/new-development.md`） | すべて実在 |
| まだ無い `docs/new-*-development.md` へのリンク | なし |

grep（`プライベート|private|料金の問題|ci\.yml`、`docs/superpowers`・`reviews` を除く）の残りの一致:

| 一致 | 分類 |
| --- | --- |
| `AGENTS.md:167`、`README.md:17`・`253`、`.devcontainer/README.md:177`・`193` | 直した後の文。「`ci.yml` は動かない」と、「プライベートで開発したい場合もある」という方針の説明 |
| `.agents/skills/issue-to-pr/evals/scenarios.json:56` | 非公開を前提にした食い違いだが範囲外（D4）。#320 にコメント |
| `docs/maatlog-poc-porting.md:162`、`scripts/resoloop-meshy.sh:75` | 事実（`ci.yml` の記録、usaturn/resoloop-meshy が private） |
| そのほか（`.gitignore`、`docs/integration.md` の `private/`、スキルの文面・テストの `private` の識別子など） | 別の意味の `private` |

表の各行と直した文の対応:

| 食い違い | 直した場所 |
| --- | --- |
| `AGENTS.md` 167 行目 | 2 行に分けた（create-reso-world は Actions 無効、有効な公開リポジトリでは CI を確認） |
| `README.md` の「変更の流れ」 | CI は動かず、ローカルの実行だけが検査になると書いた |
| `.devcontainer/README.md` 177 行目、193〜194 行目（D2） | 動かないことを書いた |
| `test-agent-config.bash` 13 行目 | 公開済みで Actions 無効と書いた |
| `README.md` の「対象外」 | 公開済み。LICENSE は未選定 |
| `README.md` 冒頭、`AGENTS.md` の「リポジトリ概要」 | 新しい対象の説明と入口の文書への案内 |
| `README.md` の「構成」 | 実在するパスと照合して書き直した（`meshy.py` の行は 1 文字も変えていない） |

## レビュー修正 サイクル 1（2026-11-07）

PR #332 の head `794c30267c49ec50232ce73fce7e0a7df796ee41` に対する review-fix-planning（pr-review-fix-loop の 1 サイクル目）の結果である。実行許可は利用者の `/pr-review-fix-loop #332` の起動で、内容の承認（`approved`）ではない。

### 結論

結論 2（修正不要としてマージ）。「対応する」は 0 件、分類は解消済み 0 / 対応する 0 / 対応しない 0（指摘が 0 件）。

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation | 指摘 |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol` | gpt-6.1-sol | pi | `794c30267c49` | はい | Approve | 0 件 |
| `SWE-2-Max` | SWE-2 Max | devin | `794c30267c49` | はい | Approve | 0 件 |

`pi_commandcode_deepseek4-flash_max`（deepseek）は、runner の期限切れ（`timed_out`、終了コード -15）で結果を受け付けられなかった。指摘 0 件ではなく失敗として扱い、レビュアーの構成と判断の入力には含めない。診断は `reviews/usaturn/create-reso-world/#332-docs-issue-321-facts-and-entry/loop/8b5106349a8b4a31a798fa781b89bc72/cycle-1/diagnostics/` にある。

planner は Claude Code の claude-sonnet-5-5（司令塔が自分で判断した。修正・自己レビュー・修正の確認の担当は起動していない）。サイクルの番号は 1（PR に前の判断の記録は無い）。

### 確認した内容

- 2 人のレビューファイル（指摘 0 件）の全文と、PR の説明・Issue #321 の受け入れ条件を読んだ
- PR の変更 7 ファイルのうち、`.devcontainer/README.md`・`AGENTS.md`・`README.md`・`docs/new-development.md`・`tests/scripts/test-agent-config.bash` の差分を全文確認した。base `afa86e09` から head までで、変更は範囲内の 7 ファイルだけ
- `docs/new-development.md` の相対リンク先 4 文書と、`README.md`「構成」に挙げたディレクトリ・ファイルの実在を確かめた
- `gh api repos/usaturn/create-reso-world/actions/permissions` は `{"enabled":false}`
- 確認済みの一覧（`verified/`）は作っていない。指摘が 0 件で、結論 1 の自己レビュー・修正の確認を行わないため

### 検証（head `794c30267c49`、worktree `.worktrees/issue-321-facts-and-entry`）

| コマンド | 結果 |
| --- | --- |
| `git diff --check afa86e09 HEAD` | 出力なし（終了コード 0） |
| `bash scripts/check-layout.sh` | `PASS: check-layout`（終了コード 0） |
| `bash tests/scripts/test-agent-config.bash` | `PASS: MCP headers use env references`（終了コード 0） |

base（`origin/main` の先端 `afa86e0967ec71135a37365fd15933e819acf6e1`）は head の祖先で、head にそのまま含まれる。文書だけの変更で、テストは足していない。
