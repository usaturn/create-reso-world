# ResoLoop の版管理と fork の運用

仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 6 章。この文書は、`.devcontainer/resoloop.lock` と `scripts/resoloop-fork.sh` を使う日々の手順をまとめる。

## 仕組み

- 導入する ResoLoop の版は `.devcontainer/resoloop.lock` を正とする。手元で `dotnet tool update` などを実行して導入だけを変えない。
- Dev Container の postCreate（`.devcontainer/install_beforehand.bash`）は `.devcontainer/install_resoloop.bash` を実行する。導入済みの版がロックの期待版と同じなら何もしない。違えば、`nuget` モードでは NuGet の公開版を `dotnet tool install` / `update --allow-downgrade` で導入し、`fork` モードでは `scripts/resoloop-fork.sh install` に任せる。最後に `resoloop --version` が期待版と一致することを確かめ、一致しなければ postCreate を失敗させる。
- `.devcontainer/verify-resonite-tooling.bash` と `scripts/check-layout.sh` もロックを読む。check-layout はロックの必須キーと、`RESOLOOP_FORK_SDK` が `devcontainer.json` の dotnet Feature の `additionalVersions` に含まれることを検査する。

### ロックのキー

| キー | 意味 |
| --- | --- |
| `RESOLOOP_MODE` | `fork`（fork をビルドして導入する）または `nuget`（NuGet の公開版を導入する） |
| `RESOLOOP_NUGET_VERSION` | `nuget` モードの期待版 |
| `RESOLOOP_FORK_ORIGIN` | fork（usaturn/resoloop）の URL。checkout の `origin` |
| `RESOLOOP_FORK_UPSTREAM` | 上流（orange3134/resoloop）の URL。checkout の `upstream` |
| `RESOLOOP_FORK_REF` | 導入するコミットを含む fork のブランチ（記録用） |
| `RESOLOOP_FORK_COMMIT` | 導入するコミット（40 桁） |
| `RESOLOOP_FORK_PACKAGE_VERSION` | `fork` モードの期待版。`dotnet pack` にこの版を渡す |
| `RESOLOOP_FORK_PR` | 修正を上流へ出した PR の URL（記録用） |
| `RESOLOOP_FORK_SDK` | fork の `global.json` が要求する .NET SDK。`devcontainer.json` の `additionalVersions` と揃える |

書式は `KEY=VALUE` の 1 行 1 項目で、値には英数字と `._:/@+-` だけを使う。9 個のキーはモードにかかわらずすべて必須。

**`RESOLOOP_FORK_COMMIT` を変えるときは `RESOLOOP_FORK_PACKAGE_VERSION` も必ず変える。** 導入済みの版が期待版と同じなら、`install` はビルドし直さずに終わる。版を据え置くと、新しいコミットは導入されない。

## checkout の位置と remote 構成

fork の checkout は `external/resoloop`（ルートの `.gitignore` で無視する）に置く。remote は次の 2 つで、`scripts/resoloop-fork.sh` はロックの URL と比べて食い違いがあれば止まる（末尾の `/` と `.git` の違いは同じ URL とみなす）。

- `origin`: https://github.com/usaturn/resoloop.git（fork）
- `upstream`: https://github.com/orange3134/resoloop.git（上流）

`/workspaces` 直下には置かない。`/workspaces` はコンテナ内の root 所有のディレクトリで、ホストと共有されるのはリポジトリ（`/workspaces/<repo>`）だけなので、直下に置いた checkout はコンテナを作り直すと消える。`external/` はリポジトリの中にあるので Rebuild 後も残り、次の postCreate は clone を省いて checkout とビルドだけを行う。

## `scripts/resoloop-fork.sh` のサブコマンド

| サブコマンド | 動作 | ネットワーク |
| --- | --- | --- |
| `clone` | `external/resoloop` に `origin` と `upstream` を持つ checkout を作る。既にあれば remote の URL を確かめるだけ | 取得のみ |
| `sync` | `upstream` と `origin` を fetch し、fork の `main` を `upstream/main` へ fast-forward で push する。ローカルの `main` も追従させる。fork の `main` に上流に無いコミットがあれば何も push せずに止まる | **fork へ push する** |
| `checkout` | ロックの `RESOLOOP_FORK_COMMIT` を detached で取り出す（手元に無ければ `origin` から fetch）。追跡ファイルに未コミットの変更があれば止まる | 必要なときだけ取得 |
| `build` | `RESOLOOP_FORK_SDK` があることを確かめ、`dotnet build ResoLoop.slnx -c Release` と `dotnet pack`（`artifacts/fork` に `ResoLoop.<期待版>.nupkg`）を実行する | NuGet の復元 |
| `test` | `dotnet test ResoLoop.slnx` を実行する。postCreate では実行しない | NuGet の復元 |
| `install` | 導入済みの版が期待版と違えば `clone` → `checkout` → `build` → `dotnet tool install` / `update --allow-downgrade` を実行する。最後に `resoloop --version` を照合する。`nuget` モードでは止まる | 取得と NuGet の復元 |
| `status` | ロックの期待版、導入済みの版、checkout の HEAD と状態、remote の構成を表示する。何も変更しない | なし |

`build`・`test` と `install` のビルドは `external/resoloop` に `cd` して実行する（dotnet は `global.json` をカレントディレクトリから探すため）。

終了コード: 0 成功、1 状態が期待と違う（git の checkout でない、remote の食い違い、未コミットの変更、コミットが `origin` に無い、fork の `main` が上流から分岐、導入後の版の不一致など）、2 使い方の誤り、3 前提不足（ロックの欠落・不正、git / dotnet が無い、SDK が無い、checkout が無い）、4 git や dotnet のコマンドの失敗。

環境変数 `RESOLOOP_LOCK_FILE`（ロックファイル）と `RESOLOOP_FORK_CHECKOUT`（checkout の位置）で既定の場所を差し替えられる。テストと特殊な運用向け。

## 状態を確かめる

```bash
bash scripts/resoloop-fork.sh status
```

`installed version` が `matches the lock` で、`checkout` が `matches the lock` かつ `clean`、`remotes` がロックと一致していれば、手元はロックどおりである。`installed version` が `DIFFERS from the lock` なら、ロックを正として `bash .devcontainer/install_resoloop.bash`（または `bash scripts/resoloop-fork.sh install`）で導入し直す。`checkout` が `DIFFERS from the lock` なら `bash scripts/resoloop-fork.sh checkout` でロックのコミットへ戻す。ただし、自分の作業ブランチにいるだけなら、そのままにしてよい（`install` はビルドが必要なときだけ checkout をロックのコミットへ切り替える）。

## 修正の流れ

1. `bash scripts/resoloop-fork.sh sync` で fork の `main` を上流に追従させる（fork へ push する）。
2. `git -C external/resoloop switch -c fix/<topic> upstream/main` で作業ブランチを作る。
3. 修正してコミットする。
4. `bash scripts/resoloop-fork.sh test` でテストを通す。
5. `git -C external/resoloop push -u origin fix/<topic>` で fork へ push する。ロックを変える前に push しておくと、別の環境の postCreate も `origin` からコミットを取得できる。
6. ロックを更新する。`RESOLOOP_FORK_REF=fix/<topic>`、`RESOLOOP_FORK_COMMIT` は `git -C external/resoloop rev-parse HEAD` の 40 桁、`RESOLOOP_FORK_PACKAGE_VERSION` は新しい版（例: `0.1.0-preview.14.pr2.20261001`）にする。
7. `bash scripts/resoloop-fork.sh install` でビルドして導入する。checkout は detached になるので、作業を続けるときは `git -C external/resoloop switch fix/<topic>` で戻る。
8. `bash scripts/check-layout.sh` が通ることを確かめ、ロックの変更をこのリポジトリにコミットする。
9. 上流へ PR を出したら、その URL を `RESOLOOP_FORK_PR` に記録する（例: `gh pr create --repo orange3134/resoloop --head usaturn:fix/<topic>`）。

`external/resoloop` の追跡ファイルに未コミットの変更があると、`install`（postCreate からの実行を含む）は `checkout` の段階で止まる。コミットするか stash してから `bash .devcontainer/install_resoloop.bash` を実行し直す。

## fork 内の PR と、上流のリリース後の切り替え

- fork 内の PR（usaturn/resoloop#1）はレビュー用であり、マージしない。
- 修正が上流にマージされてリリースされたら、ロックの `RESOLOOP_MODE=nuget` と `RESOLOOP_NUGET_VERSION=<リリース版>` を更新し、`bash .devcontainer/install_resoloop.bash` を実行する。fork 用のキーは記録として残す（どのモードでも必須）。

## 上流への PR 候補

- `resoloop init` が作る `.resoloop/.gitignore` に `cache/` が無い（このリポジトリでは `scripts/new-world.sh` が追記している）。
- `global.json` の `rollForward` が `latestPatch` なので、SDK の feature band（10.0.2xx と 10.0.4xx など）を跨げない。このため `devcontainer.json` の `additionalVersions` で 10.0.201 を追加している。

## `tmp/` にある旧 checkout の整理

再設計の前に手作業で作った checkout と作業記録が `tmp/` に残っている。削除は必要な内容を確かめてから手で行う（自動では消さない）。

| ディレクトリ | 中身 | 扱い |
| --- | --- | --- |
| `tmp/resoloop-blender5-uv-20260925` | remote はロックと同じで、HEAD はロックのコミット（ブランチ `fix/blender5-uv-export`）。未追跡の `reviews/` がある | `external/resoloop` がまだ無ければ、`reviews/` を必要に応じて退避してから `mv tmp/resoloop-blender5-uv-20260925 external/resoloop` で移し、`bash scripts/resoloop-fork.sh status` で確かめる。clone を省ける |
| `tmp/usaturn-resoloop-pr1` | fork 内 PR #1 のレビュー用 checkout。未追跡の `reviews/` がある | `reviews/` を必要に応じて退避してから削除する |
| `tmp/resoloop-uv0-fix-20260924` | 上流 v0.1.0-preview.13 の shallow checkout に、未コミットの草稿（4 ファイル）がある | `git -C tmp/resoloop-uv0-fix-20260924 diff > ~/resoloop-uv0-fix-draft.patch` で草稿を保存してから削除する |
| `tmp/resoloop-skills-20260924-1526` | git の checkout ではない作業記録（レビューと差分の Markdown など） | 必要なものを退避してから削除する |

## 対象外

flux-sdk の導入はこの運用の対象外とする。
