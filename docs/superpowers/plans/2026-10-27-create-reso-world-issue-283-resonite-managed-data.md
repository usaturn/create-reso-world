# ProtoFlux 用の Resonite managed data の共有 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WSL 側の専用ディレクトリにコピーした Resonite の managed DLL を、コンテナから読み取り専用で読めるようにし、用意と確認の手順を README に書く（Issue #283）。

**Architecture:** `devcontainer.json` の mount を 1 つ足し、`initialize.bash` がその共有元を空の実ディレクトリとして作る（リンク・ファイルなら止まる）。版の選択と確認は既存の `resoloop doctor`・`flux check`・`flux build` に任せ、手順を `.devcontainer/README.md` に書く。

**Tech Stack:** bash（`initialize.bash` はホストの WSL で、テストはコンテナで動く）、Dev Container の `mounts`、ResoLoop 0.2.0、flux-sdk 1.9.0

**Spec:** `docs/superpowers/specs/2026-10-27-create-reso-world-issue-283-resonite-managed-data-design.md`

- 状態: `draft`（issue-to-pr の run。実行許可は Spec の「管理と実行許可」。内容の承認ではない）
- 実行方式: `superpowers:executing-plans`。このセッションが inline で Task 1・2 を順に実装し、Task 3 で統合の確認と、別のサブエージェントによるブランチ全体のレビューを行う（Spec の D7）
- 検証の入口: worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`

## Global Constraints

- 共有元（WSL）: `${HOME}/.local/share/create-reso-world/resonite-managed-data`、共有先（コンテナ）: `/home/vscode/.local/share/create-reso-world/resonite-managed-data`
- mount の書式: `"source=${localEnv:HOME}/.local/share/create-reso-world/resonite-managed-data,target=/home/vscode/.local/share/create-reso-world/resonite-managed-data,type=bind,readonly"`（`.devcontainer/mounts.bash` が読む 1 行 1 mount の形）
- `initialize.bash` は DLL を探さない・コピーしない・中身を変えない。`RESONITE_MANAGED_DATA_PATH` を生成しない
- 共有元がリンクか、実ディレクトリでないものなら、`initialize.bash` は mkdir の前に理由を表示して終了コード 1
- DLL・その記録はリポジトリに入れない。`.devcontainer` にワークスペースの絶対パスを書かない（`test-readme.bash`）
- テストは AGENTS.md の「テストの採用基準」。README の文言・DLL の一覧のテストは書かない

## Review Focus

1. 既存の利用者が更新した直後（共有元が無い）: `initialize.bash` が空の実ディレクトリを作って通る → Task 1 の既存の一時 HOME の実行（テストの 4）が確かめる
2. 写真フォルダの手順をまねて共有元をリンクにした: `initialize.bash` が止まり、コピーする手順へ案内する → Task 1 のテストの 5
3. リンク先が消えたリンク（壊れたリンク）: 存在の確認より先に `-L` で調べるので、同じく止まる → Task 1 の実装（`[ -L ]` を先に評価する）
4. Windows のパスに空白・括弧がある（`C:\Program Files (x86)\...`）: README のコマンドは `wslpath -u '<パス>'` と `"$src"` で引用する → Task 2
5. 既にある版のフォルダへコピーし直して版が混ざる: README のコピー先の作成は `mkdir`（`-p` なし）にして、既にあれば止める → Task 2

## 受け入れ基準

- **動作環境:** Dev Container（Ubuntu 26.04）の bash で、`initialize.bash` のコピーを一時 HOME（`env HOME=...` のワンショット）で実行する。実際の initializeCommand は WSL のホストで動くが、使うのは bash の `test`・`mkdir`・`printf` だけで差は無い。rebuild・Docker の mount・実 DLL での check/build はこの run の対象外（マージの後に利用者が確かめる）
- **実入力:**
  - `devcontainer.json` は `//` のコメント行を含む JSONC。mount は 1 行 1 つで、オプションは `type=bind` の後ろに `,readonly` や `,consistency=cached` が続く
  - 共有元の状態: 無い／空の実ディレクトリ／`2026.9.18.82` のような版のサブディレクトリに `FrooxEngine.dll` がある実ディレクトリ／実ディレクトリへのリンク
  - README の Windows のパスは `C:\Program Files (x86)\Steam\steamapps\common\Resonite` のように空白・括弧を含みうる
- **防御範囲:**
  - 対象: managed data の共有元のリンクの拒否と、実ディレクトリの中身の保持／読み取り専用の mount が `resonite-managed-data` と `resonite-screenshots` の 2 つであること／mount の一覧が 16 個であること
  - 対象外: 写真フォルダのリンク（今までどおり許す）、共有元の中のリンク（コンテナの中では mount の外を指して読めないだけで、公開範囲は増えない）、ファイルの共有元（`mkdir -p` のエラーでも止まる L。`initialize.bash` は明示的に止めるが、テストは書かない）、DLL の版の一致（利用者が確かめる）

## 要件の対応

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 読み取り専用の専用ディレクトリだけを mount | Task 1 | mount の一覧が 16 個、readonly の一覧が 2 つ | テストの 2・3、変異で readonly を外すと失敗 |
| 2 無ければ空の実ディレクトリを作り、中身を変えない | Task 1 | 一時 HOME に作られ、DLL の偽ファイルが残る | テストの 4・5 |
| 3 リンク・ファイルなら止まる | Task 1 | リンクの共有元で終了コードが 0 でない | テストの 5、変異で検査を外すと失敗 |
| 4 未設定でも起動する | Task 1 | 空の HOME で `initialize.bash` が 0 | テストの 4（rebuild は利用者） |
| 5 版を自動で選ばない | Task 1・2 | env-file に `RESONITE_MANAGED_DATA_PATH` が無い | `git diff` で生成処理が変わっていないこと、README の手順が明示の指定だけ |
| 6 README・integration.md の手順 | Task 2 | 手順・見え方・元のエラーの読み方がある | DLL が無い状態で README のコマンドを実行し、出力が書いたとおりか |
| 7 DLL をリポジトリに入れない | Task 1・2 | 追加ファイルが設定・文書・テストだけ | `git diff --stat` |
| 8 除外範囲 | Task 3 | ResoLoop・ワールド・利用者の HOME に変更が無い | `git diff --name-only`、作業の記録 |

共有する前提は 2 つで、Task 3（統合）が確かめる。(a) 共有元・共有先のパスの文字列が `devcontainer.json`・`initialize.bash`・テスト・README で同じ。(b) README が説明する ResoLoop・flux-sdk の挙動（設定の優先順位、`doctor --library-path`、`flux check --json` の `error.context.stderr`、`flux build --out`）が導入済みの 0.2.0・1.9.0 と合う。

---

### Task 1: managed data の mount と共有元の作成

テスト: 要る。readonly の一覧は権限を決める設定値（F∩S）、リンクの拒否は公開範囲の境界（S）で、どちらも壊れてもエラーにならない。mount の一覧の更新は既存の F∩S のテストが求める。

**Files:**
- Modify: `.devcontainer/test-initialize-mounts.bash`
- Modify: `.devcontainer/devcontainer.json`（写真フォルダの mount の次）
- Modify: `.devcontainer/initialize.bash`（写真フォルダのリンクの検査の次と、`mkdir -p` の一覧）

**Interfaces:**
- Produces: 共有元・共有先のパス（Global Constraints）と、リンクのときの `initialize.bash` の終了コード 1。Task 2 の README はこれを説明する

- [ ] **Step 1: テストを先に直す**

  - 2 の固定一覧に `.local/share/create-reso-world/resonite-managed-data` を足し（`LC_ALL=C sort` の順で `resonite-screenshots` の前）、コメントの「15 個」を「16 個」にして、managed data に触れる
  - 3 を新しく足す: `devcontainer.json` の `//` で始まらない mount 行のうち、`type=bind` の後ろのオプションに `readonly` があるものの `<rel>` を集め、次と一致することを確かめる。理由（readonly が外れても起動はエラーにならず、コンテナから Windows の写真や、利用者がコピーした DLL を書き換え・消せる）をコメントに書く

    ```text
    .local/share/create-reso-world/resonite-managed-data
    .local/share/create-reso-world/resonite-screenshots
    ```

  - 既存の 3（一時 HOME での実行）を 4 にする
  - 5 を新しく足す: (i) 一時 HOME の共有元に `2026.9.18.82/FrooxEngine.dll`（中身 `dll`）を置いて `initialize.bash` を実行し、終了コード 0 で中身が `dll` のままであること。(ii) 別の一時 HOME で、共有元を一時ディレクトリへのリンクにして実行し、終了コードが 0 でないこと。理由（リンクを mount すると、リンク先がそのままコンテナに見え、エラーにならない）をコメントに書く

- [ ] **Step 2: 失敗を確かめる**

  Run: `bash .devcontainer/test-initialize-mounts.bash`
  Expected: `FAIL: unexpected mounts:` で終了コード 1

- [ ] **Step 3: mount と共有元の作成を足す**

  - `devcontainer.json`: Global Constraints の mount の行と、その前に 1 行のコメント（任意・#283・ProtoFlux 用に利用者が版ごとにコピーした DLL を読み取り専用で共有する・リンクは `initialize.bash` が拒否する）
  - `initialize.bash`: 写真フォルダの検査の次に、変数 `managed_data` を共有元にして、`[ -L "$managed_data" ] || { [ -e "$managed_data" ] && [ ! -d "$managed_data" ]; }` なら、パスと「DLL を版ごとのフォルダへコピーする（`.devcontainer/README.md`）」ことを stderr に書いて `exit 1`。`mkdir -p` の一覧の末尾（写真フォルダの次）に `"${HOME}/.local/share/create-reso-world/resonite-managed-data"` を足す。冒頭のコメントの書式（1 行に 1 つ `"${HOME}/<パス>"`）を守る

- [ ] **Step 4: 通ることを確かめる**

  Run: `bash .devcontainer/test-initialize-mounts.bash && bash scripts/check-layout.sh`
  Expected: `PASS: mounts agree with initialize.bash ...` と、check-layout の `ok: mounts match .devcontainer/initialize.bash` と `PASS: check-layout`

- [ ] **Step 5: 変異で守りを確かめる（コミットしない）**

  1. `devcontainer.json` の managed data の行から `,readonly` を外す → テストが FAIL。戻す
  2. `initialize.bash` のリンクの検査を `if false; then` にする → テストが FAIL。戻す
  3. `git diff --stat` が Step 3 の変更だけであること

- [ ] **Step 6: Commit**

  ```bash
  git add .devcontainer/test-initialize-mounts.bash .devcontainer/devcontainer.json .devcontainer/initialize.bash
  git commit -m "feat(devcontainer): share the Resonite managed data folder read-only (#283)"
  ```

### Task 2: 用意と確認の手順

テスト: 要らない。文書の文言は F。代わりに、DLL が無いこのコンテナで README のコマンドを実行し、書いた出力・JSON のパスと合うことを確かめる。

**Files:**
- Modify: `.devcontainer/README.md`（導入ツール一覧の表、「ProtoFlux 用の flux-sdk」の managed data の 2 項目、新しい節）
- Modify: `docs/integration.md`（「Rebuild 後に確かめること」）

**Interfaces:**
- Consumes: Task 1 のパスと、リンク・ファイルで止まる挙動

- [ ] **Step 1: 導入ツール一覧に 1 行足す**

  写真フォルダの行の次に「Resonite の managed data（任意、ProtoFlux）」。導入方法は「利用者が Windows の Resonite の DLL を版ごとのフォルダへコピーする（節への参照）」、mount は共有元（読み取り専用）、initialize.bash の mkdir も共有元、残りは `—`

- [ ] **Step 2: 「ProtoFlux 用の flux-sdk」の 2 項目を直す**

  managed data を「既定では mount しない」と書いた項目を、専用のフォルダを読み取り専用で mount し、版のフォルダを明示して指す、手順は新しい節、に直す。準備の確認の項目は、doctor の 2 つの確認に加えて非空のグラフの check・build が成功すること、と新しい節への参照にする

- [ ] **Step 3: 新しい節「Resonite の managed data（ProtoFlux、任意）」を写真フォルダの節の前に足す**

  次をこの順で書く。コマンドは実際に使う形（引用付き）にする。

  1. 何のためか: flux-sdk の check・build・配備は Resonite の managed DLL を読む。自動探索はコンテナの中しか見ないので、Windows の DLL は見つからない
  2. 共有の仕組み: `initialize.bash` が共有元を空の実ディレクトリで作り、同じパスに読み取り専用で mount する。リンク・ファイルなら止まる（理由）。未設定でも起動する。DLL をリポジトリ・イメージに入れない。`initialize.bash` は版を選ばない
  3. 見え方: 未設定のときの doctor の `resonite-managed-data` の `warning` のメッセージ（実測の文）と、準備済みの判定（doctor の `flux-sdk`・`resonite-managed-data` が `pass`、非空のグラフの check・build が終了コード 0、`.brson` ができる）
  4. 手順: Windows（`Get-Process -Name '*Resonite*' | Select-Object Id, ProcessName, Path` で実行中のパス、`Get-ChildItem -LiteralPath '<インストール先>' -Filter FrooxEngine.dll -File -Recurse | Select-Object FullName` で DLL のフォルダ。`Resonite_Data\Managed` などを決め打ちしない。版は Resonite の表示か、コンテナの `resoloop status --json` の `data.resoniteVersion`）→ WSL（`src="$(wslpath -u '<FrooxEngine.dll のあるフォルダ>')"`、`mkdir -p` で共有元、`mkdir` で版のフォルダ、`cp -p -- "$src"/*.dll`、`sha256sum` で `SHA256SUMS` を作り `sha256sum --quiet -c` で照合。Resonite の更新中にコピーしない、フォルダ全体をコピーしない、11 個の DLL は最低限で、足りなければ SDK が示す）→ 初回だけ rebuild（以後の版の追加は mount 済みなので rebuild 不要）→ コンテナ（`findmnt -no OPTIONS <共有先>` が `ro` で始まる、`ls "$lib/FrooxEngine.dll"`）→ `resoloop doctor --library-path "$lib" --json | jq '.data.checks[] | select(.name == "flux-sdk" or .name == "resonite-managed-data")'` → `mktemp -d` に雛形と同じ `Main.pg`・`protograph.toml` を書き、`resoloop flux check ... --library-path "$lib" --json` と `resoloop flux build ... --out "$probe/Main.brson" --library-path "$lib" --json` の終了コードと `.brson` を確かめる
  5. 設定の保存: 優先順位（`--library-path` > `RESONITE_MANAGED_DATA_PATH` > cwd から上へ探す `.resoloop.json` の `resoniteManagedDataPath` > `~/.resoloop/config.json`）。プロジェクトの `.resoloop.json` に書く例。`~/.resoloop/config.json` は mount していないので rebuild で消える。古い環境変数が残ると優先される
  6. Resonite を更新したら: 新しい版のフォルダへコピーし、確認をやり直し、指す先を切り替える。古い版はホスト側で消す
  7. 元のエラーを確かめる: doctor は SDK の出力の最後の行しか出さない。`resoloop flux check ... --json 2> "$probe/check.error.json"` の後、`jq -r '.error.context.stderr' "$probe/check.error.json"` で、足りない DLL と探したディレクトリが読める（実測の抜粋を短く載せる）

- [ ] **Step 4: integration.md に 1 項目足す**

  「Rebuild 後に確かめること」の 4 の次に、任意の確認として: ホストに共有元が実ディレクトリで作られ、コンテナで `findmnt` が `ro` を示す。DLL を用意したら README の新しい節の手順で doctor と check・build を確かめる

- [ ] **Step 5: README のコマンドを、DLL が無いこのコンテナで実行して確かめる**

  `mktemp -d` の中で、doctor の jq、`flux check --json` の失敗と `error.context.stderr` の jq、`findmnt -no OPTIONS` を写真フォルダの共有先で実行し、README に書いた出力・パスと合うこと。`bash .devcontainer/test-readme.bash` が PASS

- [ ] **Step 6: Commit**

  ```bash
  git add .devcontainer/README.md docs/integration.md
  git commit -m "docs(devcontainer): explain how to prepare and check the Resonite managed data (#283)"
  ```

### Task 3: 統合の確認とブランチ全体のレビュー

テスト: 足さない。検証の入口の全体を実行する。

- [ ] **Step 1: 共有する前提の照合** — パスの文字列を `git grep -n 'resonite-managed-data'` で全部見て一致を確かめる。README の ResoLoop の挙動を `external/resoloop` の `upstream/main`（0.2.0）のソースと、Task 2 の Step 5 の実測で照合する
- [ ] **Step 2: 検証の入口をすべて実行する** — `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。終了コードとログを `PARENT_ROOT/tmp/agents/issue-283.*/` に残す
- [ ] **Step 3: 除外範囲** — `git diff --name-only origin/main...HEAD` が Spec・Plan・`.devcontainer` の 4 ファイル・`docs/integration.md` だけ
- [ ] **Step 4: ブランチ全体のレビュー** — 新しいサブエージェント（読み取り専用）に、Spec・受け入れ基準・差分を渡してレビューを依頼する。採否を ledger に書き、採用した指摘を直したら Step 2 からやり直す
- [ ] **Step 5: Plan の「完了」を書いて commit し、検証の記録（`--merge` の checks-file）を作る** — 最後の commit の後に検証し直す

## 実行予算

- Issue 全体の能動時間: 300 分（ledger の `budget start` 済み）。根拠: 似た規模の #277（設定と文書、1 サイクルで修正不要）の実績と、`--merge` のループの最大 3 サイクル × 約 60 分（レビューの期限 45 分＋計画・修正）
- phase の目安: 調査・Spec・Plan 60 分、Task 1 25 分、Task 2 35 分、Task 3 40 分（pytest は 7〜10 分）、PR 15 分、ループ 1 サイクル 60 分（最大 3 サイクル。上限は利用者の既定のまま）
- worker: Task 3 の Step 4 のレビューのサブエージェントは期限 30 分、無進捗の打ち切り 10 分。検証のコマンドは期限 30 分（pytest）・10 分（ほか）。ループの担当の期限は agent-runner の設定のまま
- 再試行の上限: 同じ失敗（同じ signature）の再試行は 1 回。安全の失敗は再試行しない
- checkpoint: Task の境界、PR の作成の直前、予算の 50%・100%、worker の失敗の直後
- 縮小・切り出し・方法変更の候補: README の節を手順と見え方だけに縮める（設定の保存・更新の手順を短くする）、readonly の検査を managed data の 1 つだけにする、ResoLoop の改善（Spec の「ResoLoop 側の改善候補」）は持ち越し候補のまま

## contingency（代替策）

- 最初の RED で `test-initialize-mounts.bash` の失敗の形が想定と違う（例: 一覧の比較より前に 1 の相互比較で止まる）: テストの意味（一覧・readonly・リンク）を変えずに、Step 2 の期待だけを実際の出力に合わせて ledger に残す
- `devcontainer.json` のオプションの書式が readonly の抽出と合わない: `.devcontainer/mounts.bash` と同じ正規表現の書き方に合わせる。`mounts.bash` の関数の出力の形は変えない（check-layout が `rel<TAB>target` の 2 列で読む）
- 検証の入口が、この変更と関係なく main でも失敗する: main の HEAD で同じコマンドを実行して比べ、main の失敗なら止まって報告する（#272 のときと同じ）
- README に書いた ResoLoop の挙動が実測と違う: 実測を基準に文を直す。ResoLoop の不具合と判断したら、Spec の「ResoLoop 側の改善候補」に足す（この Issue で直さない）
- 予算の 100%・安全の失敗: 止まって報告する

## 完了

（Task 3 の後に記入する）
