# Issue #119: push の前に Gitleaks で未 push の commit を検査する

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/119
- 検証した基準 HEAD
  - 移植先: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（create-reso-world の `origin/main`）。Issue の比較基準 `71607d9` から進んだのは #126（文書だけ）
  - 移植元: `49c2e93e836154b13e2d30ec39ac8c7b0843fc56`（usaturn/agent-workspace の `main`）。Issue の比較基準 `d3f4151` からの 5 commit は `.devcontainer/install_beforehand.bash` と `.agents/skills/repository-ownership/SKILL.md` を変えていない
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue119-gitleaks-pre-push.md`
- 実行許可: 2026-10-17 21:11 JST、利用者が「#119 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ。」と指示した。推奨案での実装、専用の worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージと rebuild は利用者が行う。下の判断は、確認を取らずに決めたエージェントの判断である

## 意図

エージェントは「リポジトリ境界」の 3 つのリポジトリ（usaturn/create-reso-world、usaturn/resoloop、usaturn/resoloop-meshy）に push する。usaturn/resoloop は public で、push した時点で公開される。create-reso-world は CI に gitleaks ジョブを持つが、private の CI を止めているので一度も実行されない。push の前に手元で Gitleaks を実行し、まだ push していない commit に秘密情報が無いかを確かめてから push する仕組みを、agent-workspace の `install_pinned_gitleaks` と `scan_before_push` から取り入れる。

## 確認した事実（2026-10-17）

Gitleaks 8.30.1（`gitleaks_8.30.1_linux_x64.tar.gz`）を使い捨ての一時リポジトリで実行して確かめた。

- **F-1 版と SHA-256**: 移植元の `GITLEAKS_ARCHIVE_SHA256`（`551f6fc8…f2470eb`）は、release の `gitleaks_8.30.1_checksums.txt` の `linux_x64.tar.gz` の値、ダウンロードした tar.gz の `sha256sum` と一致する。CI の gitleaks ジョブの `GITLEAKS_VERSION` も 8.30.1
- **F-2 作業ツリーの設定**: `--config` を渡さないと、検査するディレクトリの `.gitleaks.toml` を読む（全パスを除外する allowlist を置くと検出 0 件）。`GITLEAKS_CONFIG_TOML` の内容も読む。`--config` を渡すと、`GITLEAKS_CONFIG` より優先される
- **F-3 `.gitleaksignore`**: 検査するディレクトリの `.gitleaksignore` は、`--gitleaks-ignore-path` に別のファイルを渡しても読まれる（fingerprint を書くと検出 0 件）
- **F-4 inline の allow**: 行末の `gitleaks:allow` は既定で効き、`--ignore-gitleaks-allow` で無効になる
- **F-5 マージ commit**: マージ commit の中だけで足した内容（`git merge --no-commit` の後に足したファイル）は、`--log-opts` に `--diff-merges` を付けないと検出されない。`--diff-merges=separate` で検出される
- **F-6 git の失敗**: `--log-opts` の範囲が解決できないとき、範囲内の object が壊れているときは、`ERR` の行（`error="stderr is not empty"` など）と「no leaks found」を出して**終了コード 0** で終わる。設定ファイルの構文の誤り・不在は終了コード 1
- **F-7 push の形**: `git push -u origin <SHA>:refs/heads/<branch>` は push には成功するが、upstream を設定しない
- **F-8 push する箇所**: このリポジトリで新しい commit を push する手順は、`review-fix-planning` の「実装後」手順 5 と結論 2 の手順 6、`docs/resoloop-fork-workflow.md` の「上流へ PR を出すときの流れ」手順 5、`docs/resoloop-meshy-workflow.md` の「開発の流れ」手順 5。公開済みの commit だけを送る push は、`scripts/resoloop-fork.sh sync`（上流の `main` を fork の `main` へ）、`planning-parallel-issues` の claim ref の作成（既存の base の SHA）、`repo-cleanup-after-merge` のブランチ削除
- **F-9 Dev Container**: gitleaks は入っていない。再設計のフェーズ 4（`docs/superpowers/plans/2026-09-27-redesign-phase4-devcontainer-and-ci.md`）で「gitleaks はコンテナに入れない」としたが、CI が止まっている今はその前提が成り立たない
- **F-10 移植元の範囲**: `scan_before_push` は base を `origin/main` に固定し、`assert_working_root`（`projects.toml` の登録との照合）を前提にする。`gitleaks git` の終了コードだけで成否を決めるので、F-6 の失敗を成功として扱う
- **F-11 git の設定と属性**（実装後の自己レビューで確かめた）: リポジトリの git の設定に `color.ui=always`（または `color.diff=always`）があると、gitleaks は色付きの diff の追加行を読めず、終了コード 0 で「no leaks found」と出す。`--log-opts` に `--no-color` を足すと検出する。textconv の設定（`diff.<driver>.textconv`）も内容を差し替えて隠せ、`--no-textconv` で検出する。branch に `* -diff` の `.gitattributes` を足すと内容が binary 扱いになって見逃し、`GIT_ATTR_SOURCE=<base の SHA>` で属性を base から読ませると検出する。`GIT_ATTR_SOURCE` が不正なら git が失敗し、gitleaks は `ERR` を出す

## 判断

### D-1 構成

- `.devcontainer/install_gitleaks.bash`: 承認済みの版の Gitleaks を `~/.local/bin/gitleaks` に置く。`install_beforehand.bash` は新しいステップからこれを呼ぶ
- `scripts/scan-before-push.sh`: push の前の検査。`repository-ownership` は持ち込まない（#116 で見直し中）ので、移植元の関数をスクリプトにする

導入を `install_beforehand.bash` に直接書かず別のスクリプトにするのは、rebuild しないで導入できるようにするため（今のコンテナには gitleaks が無い）と、偽の `curl` で導入を試せるようにするためである。`install_resoloop.bash`・`install_meshy.bash` と同じ形にする。

### D-2 版をそろえる方法

- 版と SHA-256 は `install_gitleaks.bash` の `GITLEAKS_VERSION`・`GITLEAKS_ARCHIVE_SHA256` にだけ書く
- CI の gitleaks ジョブ（`gitleaks/gitleaks-action` の env）は値を直接書く必要があるので、`GITLEAKS_VERSION` はそのまま残す。`tests/scripts/test-ci.bash` に、両者が同じであることの検査を足す（2 つのファイルを読んで比べる。版の値をテストに写さない）
- `scan-before-push.sh` は、`gitleaks version` が `install_gitleaks.bash` の版と同じときだけ検査する。F-6 の失敗の検出は、この版のログの形と終了コードに依存するためである。版は、スクリプト自身と同じ checkout の `.devcontainer/install_gitleaks.bash` の `readonly GITLEAKS_VERSION="<版>"` の 1 行から読む（実行はしない）。1 行に決まらなければ止まる

### D-3 base と範囲

- base は `--base <remote>/<branch>` で指定し、既定は `origin/main`。`<remote>` は最初の `/` の前まで（remote 名に `/` は使わない前提）で、その remote が無ければ止まる
- `git fetch --no-tags <remote> +refs/heads/<branch>:refs/remotes/<remote>/<branch>` で base を取り直し、`refs/remotes/<remote>/<branch>` を commit に解決する。HEAD も検査の前に commit に解決する
- 範囲は移植元・CI の PR の検査と同じ `<base>..<HEAD>` とする。push 済みの feature branch の commit も範囲に入り、もう一度検査される
- `-C <dir>` で検査する checkout を指定できる（既定は現在のディレクトリ）。`git rev-parse --show-toplevel` のルートで検査する

### D-4 `.gitleaks.toml` の無いリポジトリの設定

base に `.gitleaks.toml` があればそれを使い、無ければ Gitleaks の既定の規則だけで検査する（Issue の案 1）。既定の規則のときも、`[extend] useDefault = true` だけの設定を一時ファイルに書いて `--config` で渡す（F-2 のとおり、渡さないと作業ツリーの `.gitleaks.toml` を読むため）。

| 案 | 採否 | 理由 |
| --- | --- | --- |
| 既定の規則だけ | 採用 | 他のリポジトリを変えずに済む。usaturn/resoloop は上流の fork で、上流との差分を増やさない。検査するのは新しい commit だけなので、過去の履歴の誤検出には当たらない。後で base に `.gitleaks.toml` を足せば、そのまま使われる |
| create-reso-world の `.gitleaks.toml` | 不採用 | 除外の 2 件は、ワールドのマニフェストの識別子と、このリポジトリのテストの偽のトークン向けである。他のリポジトリでは除外を広げるだけになる |
| 各リポジトリに `.gitleaks.toml` を足す | 不採用 | 他のリポジトリへの PR が要り、この Issue の反映先（create-reso-world の `main` への PR）を超える。誤検出が実際に出たときに、そのリポジトリで判断する |

「無い」と「取得に失敗した」は区別する。`git ls-tree` が失敗したら止まり、出力が空のときだけ既定の規則にする。

### D-5 検査を緩めない

- 環境変数 `GITLEAKS_*` をすべて外してから gitleaks を実行する（`GITLEAKS_CONFIG`・`GITLEAKS_CONFIG_TOML` を含む）
- 設定は D-4 の一時ファイルを `--config` で渡す。作業ツリーの `.gitleaks.toml` は使わない
- 検査する checkout のルートに `.gitleaksignore`（ファイルでも symlink でも）があれば止まる（F-3）。`--gitleaks-ignore-path` には空のファイルを渡す
- `--ignore-gitleaks-allow` で inline の allow を無視する（F-4）
- `--log-opts="--no-color --no-ext-diff --no-textconv --diff-merges=separate <base>..<HEAD>"` で、git の設定に左右されない diff を読み（F-11）、マージ commit も各親との差分として検査する（F-5）。`--no-ext-diff` は `git log -p` が外部 diff を使わないことの念押しである
- gitleaks を `GIT_ATTR_SOURCE=<base の SHA>` で実行し、属性を作業ツリーではなく base から読ませる（F-11）。base が binary とした種類のファイルは、CI と同じく検査しない

### D-6 失敗を成功として扱わない

次のどれでも終了コードを 0 以外にし、SHA を出さない。

- gitleaks が無い、版が違う（D-2）、`install_gitleaks.bash` から版を読めない
- 引数の誤り、git の checkout でない、remote が無い、fetch・commit の解決・設定の取得の失敗、`.gitleaksignore` がある
- gitleaks の終了コードが 0 以外（検出を含む）
- gitleaks の出力に `ERR`・`FTL` の行がある（F-6。終了コードが 0 でも失敗にする）

標準出力には成功したときの SHA だけを出し、ログは標準エラーに出す。`--redact` で秘密の値を伏せ、`--verbose` で検出した commit・ファイル・規則を表示する。

### D-7 push の形

```bash
SHA="$(bash <create-reso-world のルート>/scripts/scan-before-push.sh [-C <checkout>] [--base <remote>/<branch>])" \
  && [ -n "$SHA" ] && git -C <checkout> push <remote> "$SHA:refs/heads/<branch>"
```

検査した SHA をそのまま push し、検査の後に変わった HEAD を push しない。`-u` は付けない（F-7）。

### D-8 規則と手順への組み込み

- `AGENTS.md` に「push の前の秘密情報の検査」の節を足す。D-7 の形、検出・失敗で止まったら push しないこと、誤検出でも `.gitleaksignore`・inline の allow・作業ツリーの設定で回避せず利用者に報告すること、除外を足すなら base の `.gitleaks.toml` を先に変えること、対象にしない push（F-8 の公開済みの commit だけを送る push）を書く
- `review-fix-planning`: 「実装後」手順 5 の push を D-7 の形にし、base は `"$PR_REMOTE/<PR の base>"`、push 先は `"$HEAD_REMOTE"` の `"$HEAD_BRANCH"` にする。スクリプトは照合済みの `$TOPLEVEL`（create-reso-world）から呼ぶ。結論 2 の手順 6 と例の 2 か所は、この手順 5 の push を参照する形にする
- `docs/resoloop-fork-workflow.md` の手順 5 は `--base upstream/main`（作業ブランチを `upstream/main` から作るため）、`docs/resoloop-meshy-workflow.md` の手順 5 は既定の `origin/main` で D-7 の形にする
- `.devcontainer/README.md`: 導入ツール一覧に Gitleaks の行を足し、「テストの実行」の gitleaks の段落に、手元の検査と rebuild しないときの導入を書く

### D-9 CI

- `devcontainer-tests` ジョブに `bash .devcontainer/install_gitleaks.bash` と `~/.local/bin` の `GITHUB_PATH` への追加を足す。`tests/scripts/test-scan-before-push.bash` が実際の gitleaks を使うためである
- gitleaks ジョブは変えない（版は D-2 の検査でそろえる）。private の CI は止まっているので、どちらも実行では確かめない

### D-10 テスト

- `tests/scripts/test-scan-before-push.bash`（新規）: PATH 上の実際の gitleaks で、bare の origin を持つ一時リポジトリを検査する。偽のトークンは実行時に作り、テストのファイルにはトークンの形の文字列を書かない（このリポジトリ自体の検査で検出されないため）。gitleaks が無ければ、導入の手順を表示して失敗する（skip しない）
  - 検出する: 通常の commit、マージ commit の中だけで足した内容、inline の `gitleaks:allow` を付けた行、作業ツリーと branch の `.gitleaks.toml`・`GITLEAKS_CONFIG`・`GITLEAKS_CONFIG_TOML` で全部を除外しようとした場合（base に設定がある場合と無い場合の両方）、git の設定の `color.ui=always`・`color.diff=always`、textconv、branch で足した `* -diff` の `.gitattributes`（F-11）
  - 止まる: `.gitleaksignore` がある、base の設定が壊れている、範囲内の object が壊れている（F-6）、base の remote・branch が無い、gitleaks の版が違う、gitleaks が 0 以外で終わる
  - 成功する: 秘密情報の無い commit とマージ commit（標準出力が HEAD の SHA だけ）、base の `.gitleaks.toml` の allowlist が除外する値（base の設定を使っていることの確認）
  - 失敗したときは標準出力が空であることも確かめる
- `.devcontainer/test-install-gitleaks.bash`（新規）: 偽の `curl` と、偽の gitleaks を入れた tar.gz で、ネットワークを使わずに導入を実行する
  - SHA-256 が合わないと失敗し、既にある `~/.local/bin/gitleaks` を変えない
  - SHA-256 を差し替えた写しで、導入が成功し、取得する URL が版から作られ、mode 755 で置かれる
  - ダウンロードの失敗、展開した gitleaks の版の違いで失敗し、既にあるものを変えない
- `tests/scripts/test-ci.bash`: CI の `GITLEAKS_VERSION` が `install_gitleaks.bash` の版と同じことを足す

### D-11 移植元との違い

| 項目 | 移植元 | 移植先 | 理由 |
| --- | --- | --- | --- |
| 形 | `repository-ownership` の関数 | `scripts/scan-before-push.sh` | Issue の「移植先での形」 |
| 照合 | `assert_working_root`（`projects.toml`） | 指定した checkout のルート | `projects.toml` が無い。対象リポジトリの確認は「リポジトリ境界」の規則のまま |
| base | `origin/main` に固定 | `--base`、既定は `origin/main` | fork への PR（`upstream/main`）と、`review-fix-planning` の PR の base に合わせる |
| base に設定が無いとき | 対象外（使わない） | 既定の規則（D-4） | resoloop と resoloop-meshy に設定が無い |
| 失敗の判定 | 終了コードだけ | 終了コードと `ERR`・`FTL` の行、版の確認 | F-6 |
| git の設定・属性 | `log.diffMerges` だけを固定 | 色・外部 diff・textconv を切り、属性を base から読む | F-11 |
| 環境変数 | `GITLEAKS_CONFIG`・`GITLEAKS_CONFIG_TOML` を外す | `GITLEAKS_*` をすべて外す | 同じ目的で、名前を数え上げない |
| 出力 | `--redact` | `--redact --verbose` | 何が検出されたかを、値を伏せたまま示す |
| 導入 | `install_beforehand.bash` の関数 | `install_gitleaks.bash`。展開した gitleaks の版を確かめてから置く | D-1。置いた後の確認で失敗すると、既にある gitleaks を置き換えた後になるため |

### D-12 PR と Issue

PR の本文は `Refs #119` にし、マージで #119 を自動で close しない。受け入れ基準の動作環境（作り直した Dev Container）は、利用者の rebuild の後にしか確かめられないためである。

## 範囲外

- push 済みの履歴の検査と書き換え、private の CI の再開（Issue の「対象にしない」）
- usaturn/resoloop・usaturn/resoloop-meshy への `.gitleaks.toml` の追加（D-4）
- CI の gitleaks ジョブを `scan-before-push.sh` に置き換えること
- 手元だけにある属性（`$GIT_DIR/info/attributes`、`core.attributesFile`）で binary 扱いにした場合。`GIT_ATTR_SOURCE` はこれらを置き換えない。`git log --text` で binary も検査する案は、CI と結果が変わり、画像などの中身を検査して誤検出を増やすので採らない
- `GIT_ATTR_SOURCE` を知らない古い git（Dev Container の git 2.55 で確かめた）
- 公開済みの commit だけを送る push（F-8）
- このリポジトリの外にあるスキル（superpowers の `finishing-a-development-branch` など）の手順の書き換え。`AGENTS.md` の規則が優先する
- #114 で取り込み中の `issue-to-pr` スキル（まだ `main` に無い）。取り込むときに `AGENTS.md` の規則に合わせる
- x86_64 以外の Dev Container

## 受け入れ基準との対応

| 受け入れ基準 | 対応 | 確かめ方 |
| --- | --- | --- |
| 未 push の commit に秘密情報があれば push の前に止まる | D-5・D-6・D-7 | `test-scan-before-push.bash` の通常の commit |
| マージ commit で入った内容も検出する | D-5（F-5） | 同じテストのマージ commit |
| `.gitleaksignore`・作業ツリーの設定・環境変数で緩められない | D-4・D-5 | 同じテストの `.gitleaksignore`・`.gitleaks.toml`・`GITLEAKS_CONFIG`・`GITLEAKS_CONFIG_TOML` |
| 検出・設定の取得・gitleaks 自体の失敗を成功として扱わない | D-6 | 同じテストの失敗の場合（標準出力が空） |
| 動作環境: 作り直した Dev Container、3 リポジトリの worktree | D-1・D-9 | この PR では今のコンテナに `install_gitleaks.bash` で導入して、create-reso-world の worktree と `external/resoloop`・`external/resoloop-meshy` の checkout で実行する。rebuild の後の確認は利用者に頼む |

## 検証

- `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`
- 今のコンテナで `bash .devcontainer/install_gitleaks.bash` を実際に実行する（release から取得し、SHA-256 を確かめて置く）
- この PR の push 自体を `scan-before-push.sh` で検査する
