# ResoLoop の版と fork の運用

仕様: `docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md`（版のロックを廃止した設計）。この文書は、最新の公開版の導入と、fork（usaturn/resoloop）のビルドを一時的に使う日々の手順をまとめる。

## 仕組み

- ResoLoop は常に NuGet の最新の公開版を使い、版を固定しない。公開版は今はプレリリース（`0.1.0-preview.N`）だけなので、`--prerelease` を付けて導入する。
- Dev Container の postCreate（`.devcontainer/install_beforehand.bash`）は `.devcontainer/install_resoloop.bash` を実行する。このスクリプトは `dotnet tool update --global ResoLoop --prerelease --allow-downgrade` で最新を導入し（未導入なら導入、導入済みなら更新）、`resoloop --version` が導入した版と一致することを確かめる。NuGet に届かず更新できなくても、導入済みの版があれば警告してその版のまま続ける。導入済みの版が無ければ postCreate を失敗させる。
- コンテナの起動のたび（postStart）には更新しない。rebuild せずに最新へ上げるときは、手で `bash .devcontainer/install_resoloop.bash` を実行する。
- postCreate は続けて `.devcontainer/report-resoloop-skills.bash` で、各プロジェクトの `resoloop skills sync --check` の結果を表示する。差分があっても失敗しない。`scripts/check-layout.sh` も、新しい版による同梱スキルの更新（`SKILL_SYNC_REQUIRED`）は `warn:` の表示にとどめ、手で編集した同梱スキル（`SKILL_SYNC_CONFLICT`）は失敗にする。更新は差分を確かめてから `resoloop skills sync --update` で行う。
- `.devcontainer/verify-resonite-tooling.bash` は、`resoloop --version` が動いて版を表示することだけを確かめる（版の値は比べない）。

## 最新の公開版へ上げる・戻す

```bash
bash .devcontainer/install_resoloop.bash
```

fork のビルドを導入している状態からも、このコマンドで最新の公開版に戻る（fork のビルドの版は公開版より大きくなり得るので、`--allow-downgrade` を付けている）。使っている版は `resoloop --version`、または `bash scripts/resoloop-fork.sh status` の `installed version` で確かめる。

## fork のビルドを一時的に使う

上流に未取り込みの修正を使いたいときは、fork のブランチ（またはコミット）を指定してビルドし、導入する。

```bash
bash scripts/resoloop-fork.sh install fix/<topic>
```

`install` は次の順で進める。

1. `external/resoloop` が無ければ clone する（`origin` が fork、`upstream` が上流）。
2. `origin` と `upstream` を fetch し、`<ref>` を解決して detached で取り出す。`origin` に同じ名前のブランチがあればそれを使い、無ければ git がそのまま解決できる名前（コミット、タグ、ローカルのブランチ、`upstream/main` など）として扱う。push していないローカルのコミットは、コミットの SHA で指定する。
3. 版を決める。`<csproj の Version>.fork.<コミット日（UTC、YYYYMMDD）>.g<短い SHA>`（例: `0.1.0-preview.17.fork.20261006.gabc1234`）。同じコミットからは同じ版になる。
4. その版が導入済みなら、ビルドせずに照合だけ行う。違えば、`global.json` が要求する SDK を確かめ、ビルドして `dotnet tool update --global ResoLoop --add-source <checkout>/artifacts/fork --version <版> --allow-downgrade` で導入する。
5. `resoloop --version` がその版を返すことを確かめる。

この導入は一時的な上書きである。次の rebuild、または `bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。上流がその修正をリリースしたら、戻すだけでよい。

## checkout の位置と remote 構成

fork の checkout は `external/resoloop`（ルートの `.gitignore` で無視する）に置く。remote は次の 2 つで、`scripts/resoloop-fork.sh` はこの URL と比べて食い違いがあれば止まる（末尾の `/` と `.git` の違いは同じ URL とみなす）。

- `origin`: https://github.com/usaturn/resoloop.git（fork）
- `upstream`: https://github.com/orange3134/resoloop.git（上流）

`/workspaces` 直下には置かない。`/workspaces` はコンテナ内の root 所有のディレクトリで、ホストと共有されるのはリポジトリ（`/workspaces/<repo>`）だけなので、直下に置いた checkout はコンテナを作り直すと消える。`external/` はリポジトリの中にあるので Rebuild 後も残る。

## `scripts/resoloop-fork.sh` のサブコマンド

| サブコマンド | 動作 | ネットワーク |
| --- | --- | --- |
| `clone` | `external/resoloop` に `origin` と `upstream` を持つ checkout を作る。既にあれば remote の URL を確かめるだけ | 取得のみ |
| `sync` | `upstream` と `origin` を fetch し、fork の `main` を `upstream/main` へ fast-forward で push する。ローカルの `main` も追従させる。fork の `main` に上流に無いコミットがあれば何も push せずに止まる | **fork へ push する** |
| `checkout <ref>` | `origin` と `upstream` を fetch し、`<ref>` を解決して detached で取り出す（解決の順は上の「fork のビルドを一時的に使う」の 2）。追跡ファイルに未コミットの変更があれば止まる | 取得のみ |
| `build` | HEAD のコミットから版を決め、`global.json` が要求する SDK を確かめて、`dotnet build ResoLoop.slnx -c Release` と `dotnet pack`（`artifacts/fork` に `ResoLoop.<版>.nupkg`）を実行する。版がコミットを名指すので、追跡ファイルに未コミットの変更があれば止まる | NuGet の復元 |
| `test` | `dotnet test ResoLoop.slnx` を実行する | NuGet の復元 |
| `install <ref>` | `clone` → `checkout <ref>` → 版の決定 →（導入済みの版と違えば）ビルド → `dotnet tool update --allow-downgrade` を実行し、`resoloop --version` を照合する | 取得と NuGet の復元 |
| `status` | 導入済みの版とその種類（`NuGet release` か `fork build`）、checkout の HEAD と状態、remote の構成を表示する。fork のビルドなら、checkout の HEAD がそのビルドのコミットかと、公開版へ戻すコマンドも表示する。何も変更しない | なし |

`build`・`test` と `install` のビルドは `external/resoloop` に `cd` して実行する（dotnet は `global.json` をカレントディレクトリから探すため）。SDK の確認も同じ場所で `dotnet --version` を実行し、`rollForward` を含む解決を dotnet に任せる。上流の `global.json` が要求する SDK は `devcontainer.json` の dotnet Feature の `additionalVersions` で入れている。上流が変えたら `additionalVersions` も合わせる。

終了コード: 0 成功、1 状態が期待と違う（git の checkout でない、remote の食い違い、未コミットの変更、`<ref>` を解決できない、fork の `main` が上流から分岐、csproj の版を読めない、導入後の版の不一致など）、2 使い方の誤り、3 前提不足（git / dotnet が無い、SDK が無い、checkout が無い）、4 git や dotnet のコマンドの失敗。

環境変数 `RESOLOOP_CHECKOUT`（checkout の位置）と `RESOLOOP_ORIGIN_URL`・`RESOLOOP_UPSTREAM_URL`（remote の URL）で既定の値を差し替えられる。テストと特殊な運用向け。

## 状態を確かめる

```bash
bash scripts/resoloop-fork.sh status
```

`installed version` が `NuGet release` なら公開版を使っている。`fork build` なら fork のビルドを使っており、`bash .devcontainer/install_resoloop.bash` で公開版に戻る。`checkout` の行は、HEAD・ブランチ（または `detached`）・未コミットの変更の有無を示す。`remotes` が `as expected` でなければ、`git -C external/resoloop remote set-url` で直す。

## 上流へ PR を出すときの流れ

1. `bash scripts/resoloop-fork.sh sync` で fork の `main` を上流に追従させる（fork へ push する）。
2. `git -C external/resoloop switch -c fix/<topic> upstream/main` で作業ブランチを作る。
3. 修正してコミットする。
4. `bash scripts/resoloop-fork.sh test` でテストを通す。
5. 秘密情報を検査してから fork へ push する: `SHA="$(bash scripts/scan-before-push.sh -C external/resoloop --base upstream/main)" && [ -n "$SHA" ] && git -C external/resoloop push origin "${SHA:?}:refs/heads/fix/<topic>"`。検査で止まったら push しない（`AGENTS.md` の「push の前の秘密情報の検査」）。
6. 手元で試すときは `bash scripts/resoloop-fork.sh install fix/<topic>` でビルドして導入する。checkout は detached になるので、作業を続けるときは `git -C external/resoloop switch fix/<topic>` で戻る。push していないコミットを試すときは、ブランチ名ではなく `git -C external/resoloop rev-parse HEAD` の SHA を渡す。
7. 上流へ PR を出す（例: `gh pr create --repo orange3134/resoloop --head usaturn:fix/<topic>`）。
8. 上流がマージしてリリースしたら、`bash .devcontainer/install_resoloop.bash` で公開版に戻す。

`external/resoloop` の追跡ファイルに未コミットの変更があると、`checkout`・`build`・`install` は止まる。コミットするか stash してから実行し直す。

## fork 内の PR

- fork 内の PR（usaturn/resoloop#1）はレビュー用であり、マージしない。

## 上流への PR 候補

- `resoloop init` が作る `.resoloop/.gitignore` に `cache/` が無い（このリポジトリでは `scripts/new-world.sh` が追記している）。
- `global.json` の `rollForward` が `latestPatch` なので、SDK の feature band（10.0.2xx と 10.0.4xx など）を跨げない。このため `devcontainer.json` の `additionalVersions` で 10.0.201 を追加している。

## `tmp/` にある旧 checkout の整理

再設計の前に手作業で作った checkout と作業記録が `tmp/` に残っている。削除は必要な内容を確かめてから手で行う（自動では消さない）。

| ディレクトリ | 中身 | 扱い |
| --- | --- | --- |
| `tmp/resoloop-blender5-uv-20260925` | remote は fork（`origin`）と上流（`upstream`）で、HEAD はブランチ `fix/blender5-uv-export` のコミット。未追跡の `reviews/` がある | `external/resoloop` がまだ無ければ、`reviews/` を必要に応じて退避してから `mv tmp/resoloop-blender5-uv-20260925 external/resoloop` で移し、`bash scripts/resoloop-fork.sh status` で確かめる。clone を省ける |
| `tmp/usaturn-resoloop-pr1` | fork 内 PR #1 のレビュー用 checkout。未追跡の `reviews/` がある | `reviews/` を必要に応じて退避してから削除する |
| `tmp/resoloop-uv0-fix-20260924` | 上流 v0.1.0-preview.13 の shallow checkout に、未コミットの草稿（4 ファイル）がある | `git -C tmp/resoloop-uv0-fix-20260924 diff > ~/resoloop-uv0-fix-draft.patch` で草稿を保存してから削除する |
| `tmp/resoloop-skills-20260924-1526` | git の checkout ではない作業記録（レビューと差分の Markdown など） | 必要なものを退避してから削除する |

## 対象外

flux-sdk は、fork のビルドの運用には含めない。ProtoFlux を使うときの導入と確認は `.devcontainer/README.md` の「ProtoFlux 用の flux-sdk（必要なときだけ）」に従う。
