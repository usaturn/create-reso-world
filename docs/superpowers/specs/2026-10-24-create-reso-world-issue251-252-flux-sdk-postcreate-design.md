# Issue #251・#252: flux-sdk を postCreate で導入し、文書を実際の挙動に合わせる Design

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/251 、https://github.com/usaturn/create-reso-world/issues/252
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/251 https://github.com/usaturn/create-reso-world/issues/252 --merge 2つ同時に対応して`。設計判断は推奨案で決め、PR の作成後に PR 修正ループを回し、修正不要なら `finalize.py` がマージする。内容の承認（approved）ではない
- 入力の検査: `resolve_issue.py` は Issue を 1 つだけ受け付けるので、`<Issue の URL> --merge` を 1 件ずつ検査した（どちらも終了コード 0、`loop_args` は空、`implement` は null）
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-251-issue-252-flux-sdk`（branch `feat/issue-251-issue-252-flux-sdk`、基準 `origin/main` の `a48b643`）
- ループ・担当の設定: `loop.py check-options` は既定の適用（サイクルの上限 3、テンプレート `.devcontainer/agent-runner.toml`、レビュアーは pi-gpt・devin-swe・pi-deepseek・cursor-grok47、修正は claude-opus、自己レビューと修正の確認は self）。利用者の指定は無い。Plan の実装は `implement_task.py check` の `self`（雛形の既定の適用。利用者の指定なし）
- 前提の確認: #251 が着手の条件にした PR #250 は 2026-10-23T16:44:12Z にマージ済み（`360d971`）。両 Issue に親 Issue・blocked_by は無い。同じ Issue の open PR・claim ref・branch・worktree は無い

## 目的と範囲

Dev Container の作成時（postCreate）に、ProtoFlux 用の flux-sdk（NuGet の `Papaltine.FluxSDK`、コマンド `flux-sdk`）を、ResoLoop が検証している版で導入する（#251）。あわせて、PR #250 で `.devcontainer/README.md` に入った flux-sdk の節の不正確な 2 か所を、実際の挙動に合わせる（#252）。

変えるもの:

- `.devcontainer/install_flux_sdk.bash` を新設する
- `.devcontainer/install_beforehand.bash` に、上のスクリプトを呼ぶステップを足す（失敗しても警告して続ける）
- `.devcontainer/README.md`: flux-sdk の節（#252 の 2 か所を含む）、「Resonite ワールド開発ツール」の 1 文、「導入ツール一覧」の表の 1 行
- `README.md` の「ResoLoop の版」: flux-sdk は版を固定して postCreate で導入する、の 1 文
- `docs/resoloop-fork-workflow.md` の「対象外」: 参照先の節名と、postCreate で導入されることに合わせる
- `docs/integration.md` の「Rebuild 後に確かめること」の 2: flux-sdk の確認を足す（#251 の rebuild での確認に使う）

対象外: Resonite 本体の managed data の用意（ホスト側に依存する）、CI への追加、ワールド側の ProtoFlux 実装、`zshrc.txt` の `update()`（版を固定するので更新の項目は置かない）、完了済みの Spec・Plan（#248 の Spec の「導入の方法: 文書だけにする」は、この Spec の D-3 で置き換わる。#248 の文書は履歴として書き換えない）。

## 調べた事実（2026-10-24）

- NuGet の `Papaltine.FluxSDK` の最新の安定版は 1.10.0。1.9 系の安定版は 1.9.0 だけ
- ResoLoop（NuGet の 0.1.0、上流 `orange3134/resoloop` の `main`）:
  - `FluxCompatibility.SupportedSeries = "1.9"`。`resoloop doctor` の `flux-sdk` の確認は、`flux-sdk` を起動して版を読めるかと、版が 1.9 系（`1.9` か `1.9.` で始まる）かだけを見る。Resonite の版は見ない
  - Resonite の版との既知の非互換（`FluxRuntimeCompatibility`）は、Resonite 2026.9.2.1275 と Flux-SDK 1.9.0+e674229… の組で `RangeLoopInt` を使う manifest を、`flux deploy-manifest`（と manifest の `flux watch`）のときに `FLUX_RUNTIME_NODE_INCOMPATIBLE` で止める。`flux validate-manifest` は `--resonite-version`・`--flux-version` を渡したときだけ確かめる
  - `doctor` と `FLUX_SDK_NOT_FOUND` の案内は、どちらも `Papaltine.FluxSDK 1.9.0` を挙げる
- 一時 HOME での実測（このコンテナ、.NET 10 SDK）:
  - `dotnet tool update --global Papaltine.FluxSDK --version 1.9.0 --allow-downgrade` は、未導入なら導入し（終了コード 0）、同じ版が導入済みなら「既にインストールされています」で 0、1.10.0 からは 1.9.0 に戻して 0
  - NuGet に届かないとき（`HTTPS_PROXY` を閉じたポートに向けた）は、同じ版が導入済みでも終了コード 1
  - `dotnet tool list --global` の行は `papaltine.fluxsdk 1.9.0 flux-sdk`。実行ファイルは `~/.dotnet/tools/flux-sdk`
  - `flux-sdk --version` は `Flux SDK Version: 1.9.0+e674229…` を表示し、続けてサブコマンドの一覧を出して終了コード 2 で終わる
  - `resoloop flux status` は、managed data が無くても、`flux-sdk` を起動して版を読めれば成功する（終了コード 0）。`resoloop doctor` は `flux-sdk` を `pass`、`resonite-managed-data` を `warning` にする
  - `dotnet tool update --global`（パッケージ ID なし）は「パッケージ ID を指定するか、update all オプション (--all) を使用する必要があります。」で終了コード 1（#252 の 1）

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-1 2 つの Issue の進め方 | 1 つの worktree・1 つの PR で両方に対応し、PR 本文に `Closes #251`・`Closes #252` を書く | Issue ごとに別の PR を並行して作る、順に作る | どちらも `.devcontainer/README.md` の同じ節を書き換え、#252 の 2 か所は #251 で書き直す文の中にある。別の PR にすると同じ行で衝突し、先にマージした方に合わせて書き直しが要る。`finalize.py` は `closingIssuesReferences` の Issue をすべて閉じて確かめる | 利用者の「2つ同時に対応して」。issue-to-pr の helper は 1 件ずつしか受け付けないので、各 Issue を個別に検査した |
| D-2 版 | 1.9.0 に固定し、`install_flux_sdk.bash` の `FLUX_SDK_VERSION` に書く | 最新を使う（今は 1.10.0）、`1.9.*` のような範囲で入れる | ResoLoop が検証しているのは 1.9 系で、案内も 1.9.0。最新の 1.10.0 は検証範囲の外で、`doctor` が warning にする。#41 の「常に最新」は ResoLoop 本体の方針で、ResoLoop が互換を決めている flux-sdk には当てはめない。範囲で入れると、ResoLoop が観測していない版の組み合わせに黙って変わり得る。ResoLoop が案内する版を変えたら定数を合わせる（文書に書く） | 推奨案で進める |
| D-3 導入の置き場所 | `.devcontainer/install_flux_sdk.bash` を新設し、`install_beforehand.bash` の ResoLoop の確認の直後に、独立したステップとして呼ぶ | `install_resoloop.bash` に足す | `install_resoloop.bash` は「ResoLoop を最新にする」スクリプトで、失敗すると postCreate を止め、rebuild しない更新にも使う。flux-sdk は版を固定し、失敗しても止めないので、性質が違う。`install_ctx7.bash`・`install_gitleaks.bash`・`install_meshy.bash` と同じく、ツールごとのスクリプトにする | 推奨案で進める |
| D-4 導入の成否と動作確認 | スクリプトの成功は、(1) `dotnet tool update ... --allow-downgrade` が成功する（失敗しても、固定した版が導入済みなら警告してその版を使う）、(2) `dotnet tool list --global` の版が固定した版と同じ、(3) `~/.dotnet/tools/flux-sdk --version` が表示する版が固定した版と同じ、の 3 つ。`resoloop flux status` と managed data は成否に含めない | `resoloop flux status` の成功も求める、`flux-sdk --version` の終了コードで判定する | managed data はホスト側の用意で、コンテナ作成時には無いのが普通である。導入の成否（このスクリプト）と、ProtoFlux の作業の準備（`resoloop doctor` の `resonite-managed-data`）を分ける。`flux-sdk --version` は版を表示しても 2 で終わるので、終了コードでは判定できない。(3) は、配置したコマンドがこのコンテナで起動できることの確認になる | 推奨案で進める |
| D-5 失敗の扱い | スクリプトは理由を 1 行出して終了コード 1 で終わる。postCreate は `WARN: ...; continuing.` を出して続ける。固定した版が導入済みで更新だけ失敗したときは、スクリプトが WARN を出して 0 で終わる | postCreate を止める | #251 の範囲（失敗してもコンテナ作成を止めない）。ProtoFlux を使わない作業には要らず、後から同じスクリプトで入れ直せる | 推奨案で進める |
| D-6 環境変数・mount | `RESONITE_MANAGED_DATA_PATH`・`RESOLOOP_FLUX_EXECUTABLE` を `devcontainer.json` で渡さず、managed data も mount しない | `devcontainer.json` の `containerEnv` や mount で渡す | managed data は Windows ホストの Resonite（Steam のライブラリの場所は利用者ごとに違う）にあり、#251 の対象外。`flux-sdk` は `remoteEnv.PATH` の `/home/vscode/.dotnet/tools` に入るので、`RESOLOOP_FLUX_EXECUTABLE` は要らない。どちらも文書で、必要なときに設定するものとして案内する | 推奨案で進める |
| D-7 テスト | テストは足さない。一時 HOME での実際の導入と、NuGet に届かない状態での実行で確かめ、結果を Plan と PR に書く | モックの `dotnet` で、導入・再実行・失敗の警告をテストする | 壊れたときは、どれもエラーか警告として現れる（採用基準の L）。導入の失敗は postCreate の WARN 行に出る。版の違い・`--allow-downgrade` が効かないことは (2) の照合で失敗になり、WARN が出る。導入されていないことは、`resoloop doctor` の `flux-sdk` の warning と、`resoloop flux` の `FLUX_SDK_NOT_FOUND` で、初めて使うときに分かる | 迷ったら書かない（採用基準） |
| D-8 文書 | `.devcontainer/README.md` の節名を「ProtoFlux 用の flux-sdk」にし、既定で導入されること・版・失敗時・確認方法を書く。#252 の 2 か所は、更新のコマンドを `dotnet tool update --global Papaltine.FluxSDK --version <版> --allow-downgrade` にし、`doctor` が見るもの（起動できるか・1.9 系か）と、Resonite の版との非互換が配備のときの `FLUX_RUNTIME_NODE_INCOMPATIBLE` で分かることを書く。ルート `README.md` には、Issue が直すとした flux-sdk の記述が #250 で無くなっているので、「ResoLoop の版」に 1 文を足す | ルート `README.md` は変えない | #251 の受け入れ基準は 3 つの文書が実際の挙動と一致すること。ResoLoop は最新、flux-sdk は固定、という違いはルートの「ResoLoop の版」を読む人に要る | 推奨案で進める |
| D-9 rebuild での確認 | PR では rebuild しない。代わりに一時 HOME で、実際の NuGet からの導入・再実行・1.10.0 からの戻し・NuGet に届かない状態を確かめる。rebuild の確認は `docs/integration.md` の「Rebuild 後に確かめること」に足し、利用者が #251 に記録する | このセッションの HOME に導入して確かめる | エージェントはコンテナを rebuild できない。利用者の環境（`~/.dotnet/tools`）を PR の検証のために変えない（AGENTS.md の「一時 HOME」）。managed data のある環境での `resoloop flux status`・`doctor` の確認もこの環境ではできないので、未確認と書く | 未確認の項目を PR・最終報告に書く |

## `install_flux_sdk.bash` の仕様

- 先頭で `set -euo pipefail`。失敗は `Flux-SDK setup: <理由>` を標準エラーに出して終了コード 1
- `dotnet` が無い、`dotnet tool list --global` が失敗する、は失敗
- 導入前の版を `dotnet tool list --global` から読む（パッケージ ID は大文字小文字を区別しない）
- `dotnet tool update --global Papaltine.FluxSDK --version "$FLUX_SDK_VERSION" --allow-downgrade </dev/null`
  - 失敗し、導入前の版が `FLUX_SDK_VERSION` なら、`Flux-SDK setup: WARN: ...; keeping <版>.` を出して続ける
  - 失敗し、それ以外（未導入・別の版）なら失敗
- 導入後の版が `FLUX_SDK_VERSION` と違えば失敗
- `"$HOME/.dotnet/tools/flux-sdk" --version` の出力の `Flux SDK Version: <版>` の版（`+` 以降を除く）が `FLUX_SDK_VERSION` と違う・読めなければ失敗（終了コードは見ない）
- 成功の表示は `install_resoloop.bash` と同じ形（`installed` / `is installed (unchanged)` / `is installed (was <版>)`）

## 受け入れ基準と確かめ方

| 受け入れ基準 | 確かめ方 |
| --- | --- |
| rebuild すると `dotnet tool list --global` に `Papaltine.FluxSDK` が出る（#251） | 一時 HOME で `install_flux_sdk.bash` を実行し、一覧に 1.9.0 が出ること。rebuild は利用者が `docs/integration.md` の手順で確かめる（未確認） |
| NuGet に届かなくてもコンテナ作成が失敗せず、警告が出る（#251） | 一時 HOME・NuGet に届かない状態で、未導入なら終了コード 1、導入済みなら WARN と 0。postCreate のステップは `if ! ...; then warn ...; fi` で続ける（構文の確認と、そのステップを取り出した一時的な実行） |
| 2 回目以降もエラーなく完了する（#251） | 一時 HOME で 2 回目を実行し、`unchanged` で 0。1.10.0 を入れた後に実行し、1.9.0 に戻ること |
| 3 つの文書が既定で導入される挙動と一致し、「必要なときだけ」「導入しない」が残らない（#251） | `rg -n "flux-sdk\|FluxSDK" .devcontainer/README.md README.md docs/resoloop-fork-workflow.md docs/integration.md` で、新しい記述だけが出ること |
| 更新のコマンドと `doctor` の記述が実際の挙動と一致する（#252） | 上の「調べた事実」との照合 |
| 既存の検査が通る | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` |
