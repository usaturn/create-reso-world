# Issue #251・#252: flux-sdk を postCreate で導入する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** postCreate が flux-sdk 1.9.0 を導入し（失敗しても警告して続け、何度実行しても壊れない）、文書を「既定で導入される」挙動と #252 の 2 か所に合わせる。

**Architecture:** `.devcontainer/install_flux_sdk.bash` を新設し、`install_beforehand.bash` の ResoLoop の確認の直後に独立したステップとして呼ぶ。構造は `install_resoloop.bash`（更新前の版の読み取り → `dotnet tool update` → 一覧と `--version` の照合）に合わせ、失敗だけを postCreate 側で警告に変える。

**Tech Stack:** bash、.NET 10 SDK の `dotnet tool`、NuGet の `Papaltine.FluxSDK`

**Spec:** `docs/superpowers/specs/2026-10-24-create-reso-world-issue251-252-flux-sdk-postcreate-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/251 、https://github.com/usaturn/create-reso-world/issues/252
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-251-issue-252-flux-sdk`（branch `feat/issue-251-issue-252-flux-sdk`、基準 `origin/main` の `a48b643`）
- 実行許可: Spec の「管理」と同じ（`--merge`）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true。Task は 2 つで、Task 2 の文書は Task 1 のスクリプトの名前・表示・挙動を書くので、逐次に同じ文脈で進める方が、委譲する文脈の手間より小さい。最後にブランチ全体のレビューを別のサブエージェントで行う
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-251.pc55xz67`（ledger `budget.jsonl`、検証のログ、一時 HOME）

## Global Constraints

- 固定する版: `FLUX_SDK_VERSION=1.9.0`（パッケージ ID `Papaltine.FluxSDK`、一覧の ID は `papaltine.fluxsdk`、コマンド `flux-sdk`、配置 `~/.dotnet/tools/flux-sdk`）
- 導入のコマンド: `dotnet tool update --global Papaltine.FluxSDK --version "$FLUX_SDK_VERSION" --allow-downgrade </dev/null`
- スクリプトの表示の接頭辞: `Flux-SDK setup: `。失敗は終了コード 1
- postCreate のスクリプト全体に `set -e` を付けない既存の方針を保ち、このステップの失敗は `warn` で続ける
- 検証で利用者の `~/.dotnet/tools` を変えない。導入を伴う確認は `env HOME="<一時 HOME>" ...` のワンショットで行う（AGENTS.md の「一時 HOME」）
- テストはコミットしない（Spec の D-7）

## Review Focus

1. 固定した版が導入済みで NuGet に届かない（rebuild でない postCreate の再実行や手動の再実行）: WARN を出して終了コード 0。未導入のまま届かないときは終了コード 1 で、postCreate は WARN で続ける
2. 利用者が手で別の版（1.10.0 など）を入れていた: `--allow-downgrade` で 1.9.0 に戻る。戻らなければ一覧の照合で失敗する
3. `flux-sdk --version` が終了コード 2 で終わる: 終了コードで失敗にせず、表示した版で判定する
4. `dotnet tool list --global` の ID の大文字小文字（`papaltine.fluxsdk`）: 大文字小文字を区別せずに探す
5. PATH の別の `flux-sdk`: 照合は `~/.dotnet/tools/flux-sdk` を直接呼ぶ

（どれもコミットするテストは書かない。Task 1 の検証の手順で、一時 HOME の実際の実行として確かめる）

## 実行予算

- Issue 全体の能動時間の予算: 240 分（調査・Spec・Plan 30 分、実装と検証 45 分、PR の作成 15 分、PR 修正ループ最大 3 サイクル × 約 50 分）。ledger は Spec を書いた後の 2026-10-24T05:29Z に開始した（それ以前の調査は約 15 分）
- worker の期限: ブランチ全体のレビューのサブエージェントは 20 分。ループのレビュアーの期限はループの設定のとおり
- 再試行の上限: 同じ signature の信頼性の失敗（NuGet への接続・`run-tests.bash` の負荷）は 1 回まで。安全の失敗（利用者の HOME を変えた、など）は再試行せず止まる
- checkpoint: Task 1 の後、Task 2 の後、検証の後、PR の作成の後、ループの各サイクルの後
- 縮小・方法変更の候補: NuGet に届かず一時 HOME で導入を確かめられなければ、スクリプトの検証をモックの `dotnet` での一時的な実行に切り替え、実際の導入を未確認として PR に書く

## 要件と Task・検証の対応

| Spec の条件 | Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| postCreate で 1.9.0 が入る（D-2・D-3） | 1 | 一時 HOME の一覧に `papaltine.fluxsdk 1.9.0` | Task 1 の Step 3 |
| 2 回目もエラーなく完了 | 1 | `unchanged` と終了コード 0 | Task 1 の Step 4 |
| 別の版から戻る | 1 | 1.10.0 から 1.9.0 に戻る | Task 1 の Step 5 |
| NuGet に届かない（D-5） | 1 | 導入済みは WARN と 0、未導入は 1 | Task 1 の Step 6 |
| postCreate は止まらない（D-5） | 1 | 失敗するスクリプトでもステップが WARN を出して続く | Task 1 の Step 7 |
| 導入と動作確認を分ける（D-4） | 1・2 | スクリプトは managed data を見ない。文書に `doctor` の `resonite-managed-data` で確かめると書く | Task 1 のコードの確認、Task 2 の Step 2 |
| 環境変数・mount を足さない（D-6） | 1・2 | `devcontainer.json` に差分が無い | 検証の `git diff --stat` |
| 文書が既定で導入される挙動と一致（D-8） | 2 | 古い記述が無い | Task 2 の Step 2 |
| #252 の 2 か所 | 2 | 更新のコマンドにパッケージ ID と `--version`、`doctor` の確認内容 | Task 2 の Step 2 |

共有する条件: Task 2 の文書が書くスクリプトの名前・表示（`WARN` の文言）・版・導入のコマンドは、Task 1 が作るものと同じでなければならない。統合の確認は、検証の Step で文書の記述と Task 1 の実行の出力を突き合わせて行う（担当: inline の実装者＝このセッション）。

---

### Task 1: `install_flux_sdk.bash` と postCreate のステップ

**Files:**
- Create: `.devcontainer/install_flux_sdk.bash`（実行権限 755。ほかの `install_*.bash` に合わせる）
- Modify: `.devcontainer/install_beforehand.bash`（`STEP_TOTAL`、冒頭のコメント、「Verifying the Resonite development toolchain」と「Reporting the bundled ResoLoop skills」の間）

**Interfaces:**
- Produces: `bash .devcontainer/install_flux_sdk.bash`（引数なし）。成功時の標準出力は `Flux-SDK setup: installed flux-sdk 1.9.0.` / `Flux-SDK setup: flux-sdk 1.9.0 is installed (unchanged).` / `Flux-SDK setup: flux-sdk 1.9.0 is installed (was <版>).` のどれか。更新だけ失敗したときは標準エラーに `Flux-SDK setup: WARN: updating Papaltine.FluxSDK failed (is NuGet reachable?); keeping 1.9.0.`。失敗は標準エラーに `Flux-SDK setup: <理由>` と終了コード 1
- Produces: postCreate のステップ名 `Installing the ProtoFlux SDK (flux-sdk)`、失敗時の WARN `Installing the ProtoFlux SDK (flux-sdk) failed; continuing. Retry with: bash .devcontainer/install_flux_sdk.bash`

**テストの要否:** 不要。壊れたときは postCreate の WARN 行・一覧の照合の失敗・`resoloop doctor` の warning として現れる（採用基準の L。Spec の D-7）。代わりに下の Step 3〜7 の実際の実行で確かめ、ログを `$SESSION/verify/` に残す。

- [ ] **Step 1: `install_flux_sdk.bash` を書く**

  Spec の「`install_flux_sdk.bash` の仕様」のとおり。`install_resoloop.bash` の形（`set -euo pipefail`、`fail()`、更新前の版 → update → 一覧 → `--version` の照合 → 3 通りの成功の表示）に合わせる。一覧の版は `awk 'tolower($1) == "papaltine.fluxsdk" && !found { print $2; found = 1 }'`。`--version` の版は `Flux SDK Version: ` の行の残りから `+` 以降と前後の空白を除いたもの。`--version` の終了コードは `|| true` で無視し、理由（版を表示して 2 で終わる）をコメントに書く。冒頭のコメントに目的・仕様のパス・版を固定する理由を短く書く。

- [ ] **Step 2: `install_beforehand.bash` にステップを足す**

  `STEP_TOTAL` を 29 から 30 にする。冒頭のコメントの「継続してよい処理（同梱スキルの状態の表示と workspace cleanup）」に flux-sdk の導入を足す。「Verifying the Resonite development toolchain」の直後に次を置く（コメントは Spec の D-3・D-5 の要点を 2 行ほど）。

  ```bash
  step "Installing the ProtoFlux SDK (flux-sdk)"
  if ! bash .devcontainer/install_flux_sdk.bash; then
      warn "Installing the ProtoFlux SDK (flux-sdk) failed; continuing. Retry with: bash .devcontainer/install_flux_sdk.bash"
  fi
  ```

- [ ] **Step 3: 構文と、一時 HOME での初回の導入**

  Run: `bash -n .devcontainer/install_flux_sdk.bash && bash -n .devcontainer/install_beforehand.bash`、`shellcheck`（あれば）。続けて `H="$(mktemp -d "$SESSION/home.XXXXXX")"` を作り、`env HOME="$H" bash .devcontainer/install_flux_sdk.bash`
  Expected: 終了コード 0、`installed flux-sdk 1.9.0.`。`env HOME="$H" dotnet tool list --global` に `papaltine.fluxsdk 1.9.0 flux-sdk`

- [ ] **Step 4: 2 回目**

  Run: 同じ `H` で `env HOME="$H" bash .devcontainer/install_flux_sdk.bash`
  Expected: 終了コード 0、`flux-sdk 1.9.0 is installed (unchanged).`

- [ ] **Step 5: 別の版から戻る**

  Run: `env HOME="$H" dotnet tool update --global Papaltine.FluxSDK --version 1.10.0` の後に `env HOME="$H" bash .devcontainer/install_flux_sdk.bash`
  Expected: 終了コード 0、`flux-sdk 1.9.0 is installed (was 1.10.0).`

- [ ] **Step 6: NuGet に届かない**

  Run: `env HOME="$H" HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 bash .devcontainer/install_flux_sdk.bash`（導入済み）と、新しい一時 HOME `H2` で同じ（未導入）
  Expected: 導入済みは標準エラーに `WARN: ... keeping 1.9.0.` と `unchanged` で終了コード 0。未導入は `Flux-SDK setup: installing Papaltine.FluxSDK 1.9.0 from NuGet failed ...` で終了コード 1

- [ ] **Step 7: postCreate のステップが続く**

  Run: `install_beforehand.bash` から Step 2 の 4 行と `warn()` を `sed` で取り出し、`install_flux_sdk.bash` を常に失敗する偽物に差し替えた一時ディレクトリで `bash` 実行する（一時的な確認。コミットしない。置き場所は `$SESSION/verify/`）
  Expected: 標準エラーに `[install_beforehand] WARN: Installing the ProtoFlux SDK (flux-sdk) failed; continuing. ...`、終了コード 0

- [ ] **Step 8: Commit**

  ```bash
  git add .devcontainer/install_flux_sdk.bash .devcontainer/install_beforehand.bash
  git commit -m "feat: install the pinned flux-sdk in postCreate (#251)"
  ```

### Task 2: 文書を既定で導入される挙動に合わせる（#251 の文書・#252）

**Files:**
- Modify: `.devcontainer/README.md`（「導入ツール一覧」の表、「Resonite ワールド開発ツール」の flux-sdk の 1 文、「ProtoFlux 用の flux-sdk（必要なときだけ）」の節）
- Modify: `README.md`（「ResoLoop の版」）
- Modify: `docs/resoloop-fork-workflow.md`（「対象外」）
- Modify: `docs/integration.md`（「Rebuild 後に確かめること」の 2）

**Interfaces:**
- Consumes: Task 1 の Produces（スクリプトのパス、版、WARN の文言、導入のコマンド）

**テストの要否:** 不要（文書の変更。採用基準の F）。代わりに Step 2 の `rg` と、Spec の「調べた事実」との照合。

- [ ] **Step 1: 文書を書く**

  - `.devcontainer/README.md`
    - 表: Gitleaks の行の後に `| flux-sdk（ProtoFlux） | install_flux_sdk.bash（NuGet の Papaltine.FluxSDK を FLUX_SDK_VERSION に固定して入れ、flux-sdk --version を確かめる。失敗しても postCreate は警告して続ける。「ProtoFlux 用の flux-sdk」の節） | — | — | — | — |`（コードの部分は既存の行と同じくバッククォートで囲む）
    - 「Resonite ワールド開発ツール」の「ProtoFlux 用の flux-sdk は既定のセットアップでは導入しない。…」を、postCreate が `.devcontainer/install_flux_sdk.bash` で ResoLoop が検証している版を導入する、と節への参照に置き換える
    - 節名を「ProtoFlux 用の flux-sdk」にし、本文を次の内容にする: 既定で導入されること（パッケージ ID・コマンド・スクリプト）、版を 1.9.0 に固定する理由（ResoLoop の検証範囲は 1.9 系で、NuGet の最新の 1.10 系は外）と、ResoLoop が案内する版が変わったら `FLUX_SDK_VERSION` を合わせること、失敗しても postCreate は WARN を出して続けること、再導入・別の版から戻すときは同じスクリプト、手で入れるときのコマンド `dotnet tool update --global Papaltine.FluxSDK --version <版> --allow-downgrade`（未導入なら導入する。#252 の 1）、`resoloop doctor` の `flux-sdk` が見るのは起動できるかと 1.9 系かだけで、Resonite の版との既知の非互換は配備（`resoloop flux deploy-manifest`）のときの `FLUX_RUNTIME_NODE_INCOMPATIBLE` で分かること（#252 の 2）、managed data と `RESONITE_MANAGED_DATA_PATH`・`RESOLOOP_FLUX_EXECUTABLE`（既存の文を保ち、`flux-sdk` は PATH に入るので通常は要らないと書く）、確認は `resoloop flux status`（managed data が無くても成功する）と、ProtoFlux の作業の準備は `resoloop doctor` の `flux-sdk`・`resonite-managed-data` が warning でないこと、`resonite-flux` スキルへの参照
  - `README.md` の「ResoLoop の版」: fork の段落の前に、「ProtoFlux 用の flux-sdk は、ResoLoop と違って版を固定し（ResoLoop が検証している版）、postCreate で導入する。詳細は `.devcontainer/README.md` の「ProtoFlux 用の flux-sdk」」の 1 文
  - `docs/resoloop-fork-workflow.md` の「対象外」: 「flux-sdk は、fork のビルドの運用には含めない。postCreate が導入し、版と確認は `.devcontainer/README.md` の「ProtoFlux 用の flux-sdk」に従う。」
  - `docs/integration.md` の 2: 「`dotnet tool list --global` に `papaltine.fluxsdk 1.9.0` があり、`resoloop doctor --json` の `flux-sdk` が `pass` である（postCreate の出力に flux-sdk の WARN が無い）」を足す

- [ ] **Step 2: 文書の照合**

  Run: `rg -n "flux-sdk|FluxSDK|必要なときだけ" .devcontainer/README.md README.md docs/resoloop-fork-workflow.md docs/integration.md`
  Expected: 「必要なときだけ」「導入しない」が無い。更新のコマンドにパッケージ ID と `--version` がある。節名の参照（「ProtoFlux 用の flux-sdk」）がすべて実在の見出しと一致する。WARN の文言・版・スクリプト名が Task 1 と同じ

- [ ] **Step 3: Commit**

  ```bash
  git add .devcontainer/README.md README.md docs/resoloop-fork-workflow.md docs/integration.md
  git commit -m "docs: describe the flux-sdk installed by postCreate (#251, #252)"
  ```

## 検証（全体）

- [ ] `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` の終了コードが 0（README.md の「テスト」。ワールドの行は除く）
- [ ] `git diff --stat origin/main...HEAD` が、Task 1・2 のファイルと Spec・Plan だけ（`devcontainer.json`・`zshrc.txt` に差分が無い）
- [ ] 最後の commit の後に検証し、HEAD・`git status --porcelain` が空だったこと・各コマンドの argv と終了コード・ログの完全パスを `$SESSION/verification.md` に、`finalize.py` の `--checks-file` の形のファイルを `$SESSION/checks.json` に置く
- [ ] ブランチ全体のレビュー（別のサブエージェント。Spec・Plan・差分を渡す）

## 完了

### 所要時間（PR の作成まで。UTC）

- 合計: 約 25 分（着手 05:20 ごろ〜レビュー修正の commit 05:42。最初のコマンドの時刻は記録していない。worktree の作成は 05:24）
- 調査・Spec・Plan: 約 11 分（〜05:30。NuGet の版、ResoLoop の `doctor`・`flux status`・非互換の検出、一時 HOME での `dotnet tool update` の挙動）
- Task 1: 約 2 分（〜05:32）。Task 2: 約 1 分（〜05:33）
- ブランチ全体のレビュー: 約 6 分（サブエージェント、opus）。指摘の確認と修正: 約 3 分（〜05:42）

### Plan からの変更（ledger の Ruling）

- `STEP_TOTAL` は 29→30 にせず 29 のまま。`d33f01d`（#243）がステップを 1 つ外したときに 29 のまま残り（ステップは 28）、今回の追加でステップが 29 になって一致した
- ledger は `sdd-workspace` の worktree の中（`.superpowers/sdd/`）ではなく、セッションディレクトリの `sdd/progress.md` に置いた（AGENTS.md の「コミットしないファイルの置き場所」）
- shellcheck はこの環境に無いので省いた（`bash -n` と実際の実行で代えた）

### 検証（Task 1 の Step 3〜7。一時 HOME、実際の NuGet）

| 場面 | 結果 |
| --- | --- |
| 初回 | 終了コード 0、`installed flux-sdk 1.9.0.`、一覧に `papaltine.fluxsdk 1.9.0 flux-sdk` |
| 2 回目 | 終了コード 0、`unchanged` |
| 1.10.0 からの戻し | 終了コード 0、`is installed (was 1.10.0).` |
| NuGet に届かない・導入済み | 終了コード 0、`WARN: updating Papaltine.FluxSDK failed (is NuGet reachable?); keeping 1.9.0.` |
| NuGet に届かない・未導入 | 終了コード 1、`installing Papaltine.FluxSDK 1.9.0 from NuGet failed (is NuGet reachable?).` |
| postCreate のステップ（失敗する偽物に差し替え） | `[install_beforehand] WARN: Installing the ProtoFlux SDK (flux-sdk) failed; continuing. ...` を出して次へ進み、終了コード 0 |

全体の検証（`run-tests.bash`・`check-layout.sh`・pytest）は、この記録の commit の後に実行し、結果を PR 本文とセッションディレクトリの `verification.md` に書く。

### ブランチ全体のレビュー

Critical 0・Important 0・Minor 5。Minor のうち 3 件（版を合わせるきっかけを `doctor` の suggestion と書いていた、同じスクリプトで「入れ直せる」と書いていた、`resoloop flux status` の成功だけで導入を確かめられると書いていた）は、今回書いた文書が実際の挙動と食い違うので Important に上げて直した（`7b4cb98`）。実際の挙動で確かめた: `flux status` は 1.10.0 でも終了コード 0、系列の外は `doctor` が `outside tested series 1.9.x` の warning、uninstall してから実行し直すと導入される。1 件（`STEP_TOTAL` の Plan との食い違い）は上の「Plan からの変更」に書いた。残る 1 件は持ち越し: `install_beforehand.bash` の workspace cleanup のコメント「（唯一の意図的なベストエフォート）」が以前から不正確（同梱スキルの表示も続行する）

### 未確認

- 実際の rebuild での導入・再実行（利用者が `docs/integration.md` の「Rebuild 後に確かめること」の 2 で確かめ、#251 に記録する）
- managed data のある環境での `resoloop flux status`・`resoloop doctor` の `resonite-managed-data`
