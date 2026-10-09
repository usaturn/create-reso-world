# usaturn/resoloop Issue #12: Resonite が読めるパスへの対応付けと、テクスチャ取り込み失敗の案内

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/resoloop/issues/12
- 実装対象: `usaturn/resoloop`（上流 `orange3134/resoloop`）
- 状態: approved（2026-10-09 にユーザーが「途中で止めずに推奨案で進めて PR して」と指示した。各段階の承認を待たずに推奨案で進める事前の許可であり、内容の確認は PR で受ける）
- 調査したコード HEAD: resoloop `4c70365`（fork main）、create-reso-world `64e7a57`
- Plan: `../plans/2026-10-09-usaturn-resoloop-issue-12-host-path-map.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-12-host-path-map-docs`（ブランチ `docs/resoloop-12-host-path-map`）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-12-host-path-map`（ブランチ `fix/issue-12-host-path-map`）

## 調査結果

### 実機での確認（2026-10-09、Resonite 2026.9.18.82 / ResoniteLink 0.13.1.0、Windows 11、ポート 40778）

4x4 の PNG を `ImportTexture2DFile` で取り込んだ。取り込みは asset を Resonite のローカル保存先へ入れるだけで、Slot は作らない。

| Resonite に渡したパス | 結果 | 応答までの時間 |
| --- | --- | --- |
| `/workspaces/reso-world/tmp/resoloop-12-probe/probe-texture.png`（コンテナのパス） | 失敗。`System.IO.DirectoryNotFoundException: Could not find a part of the path 'C:\workspaces\...'` | 約 52 秒 |
| `C:\resoloop-probe-missing\probe-texture.png`（存在しないパス） | 同じ例外 | 約 51 秒 |
| `\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world\tmp\resoloop-12-probe\probe-texture.png` | 成功（`local://.../*.png`） | 数秒以内 |

- コンテナの `/workspaces/reso-world` は WSL の `/home/usaturn/repo/reso-world` の bind mount であり、Windows からは `\\wsl.localhost\Gentoo\...` で読める。パスを対応付ければ取り込める。
- Resonite（Windows）は `/` で始まるパスを `C:\` 基準で解決する。
- Resonite がパスの誤りを返すまで約 50 秒かかる（`Elements.Core.FileUtil.GenerateFileSignatureAsync` の再試行と思われる）。CLI の要求タイムアウトの既定は 30 秒なので、既定の設定では必ず `REQUEST_TIMEOUT` になる。Issue の 2 つの症状（`ASSET_IMPORT_FAILED` と `REQUEST_TIMEOUT`）は、タイムアウトの長さの違いで説明できる。

### コード

- `ImportAssetAsync`（`src/RLoop.ResoniteLink/ResoniteLinkClientAdapter.cs:292`）は、texture と audio では CLI のパスをそのまま Resonite に渡す。mesh は CLI がファイルを読み、`ImportMeshRawData` で中身を送る。
- 取り込みの hash（`BuildAssetPlans`、`src/RLoop.Core/WorldService.cs:1270`）は CLI のパスで計算する。
- asset の取り込みは Slot の作成より前に行う。apply の失敗時の `context` には、すでに `slotsCreated` などの件数が入る（`WorldService.cs:684`）。Issue の補足「Slot が作られたかどうか」は今も報告されている。
- ResoniteLink 0.13.1 には中身を送る `ImportTexture2DRawData`（幅・高さ・`colorProfile`・color32 の画素）がある。

## 目的と成功条件

1. コンテナの CLI から、Windows の Resonite へテクスチャを含む bundle を apply できる。CLI のパスを Resonite が読めるパスへ変換する設定を、一度書けば使える。
2. 変換の設定が無く、Resonite が開けないパスを渡しそうなときは、plan/diff の段階で分かる。
3. 取り込みに失敗したとき、エラーから「Resonite のホストから読めないパス」が原因だと分かり、対処が示される。タイムアウトになった場合も、どの asset を待っていたか、Resonite に渡したパスが分かる。

## 選択肢と採用理由

1. **採用: パスの対応付けの設定 ＋ plan の警告 ＋ 失敗時の案内（Issue の期待動作 1・3・4）。** 実機で、対応付けたパスなら取り込めることを確かめた。変更は CLI の中で閉じ、取り込みの仕組みは変わらない。
2. 中身を送る取り込み（Issue の期待動作 2、`ImportTexture2DRawData`）。設定なしで動くが、PNG・JPG などの復号を CLI に入れる必要がある（依存の追加か自前の実装）。color profile・mipmap・圧縮の扱いや保存される URL の形式がファイル取り込みと変わる可能性があり、実機での比較が必要になる。上流の依存方針にも関わるため、今回は採用せず、必要なら別の Issue で扱う。
3. 接続先が別ホストかどうかを判定して警告する。ResoniteLink のセッション情報には Resonite の OS が無く、`localhost` でも別ホスト（`--network=host` のコンテナ）があるので、正確に判定できない。採用しない。代わりに、渡すパスの形（`/` 始まり）で判定する（設計 2）。

## 設計

### 1. 設定 `hostPathMap`

- 値は `FROM=TO` の 1 組。最初の `=` で分ける。`FROM` は CLI 側の絶対パスの接頭辞、`TO` は Resonite が読めるパスの接頭辞。
  - 例（このリポジトリの Dev Container）: `/workspaces/reso-world=\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world`
  - 例（Proton の Resonite と同じ Linux）: `/=Z:\`
- 指定元と優先順位は既存の設定と同じ: CLI `--host-path-map` → 環境変数 `RESOLOOP_HOST_PATH_MAP` → `.resoloop.json` の `hostPathMap` → ユーザー設定の `hostPathMap`。`--verbose` の `configSources` に指定元が出る。
- 複数の組は扱わない。必要になったら拡張する。
- 解析の誤り（`=` が無い、`FROM` が絶対パスでない、`TO` が空）は `INVALID_HOST_PATH_MAP`（exit 3）。`context` に値と指定元を入れる。解析は、Resonite に接続するコマンドの開始時に行う（Blender などの接続しないコマンドは止めない）。
- 変換の規則:
  - `FROM` の末尾の区切り文字を除いた接頭辞と、パスの区切りの位置で一致したときだけ変換する（`/workspaces/reso` は `/workspaces/reso-world/a.png` に一致しない）。一致しないパスはそのまま渡す。
  - 比較は Windows では大文字小文字を区別せず、それ以外では区別する。
  - 残りの部分の区切り文字は `TO` の形式に合わせる。`TO` が `\` を含むか `X:` で始まるなら `\`、それ以外は `/`。
- 変換するのは、Resonite がパスを開く種類（`texture`・`texture2d`・`audio`・`audioclip`）のファイルだけ。mesh と URI の asset は変換しない。hash は従来どおり CLI のパスで計算し、state には変換後のパスを保存しない（設定を変えても再取り込みしない）。
- 変換は Core（`WorldService`）で行い、アダプターには変換後のパスを渡す。アダプターは変更しない。どの種類を Resonite が開くかは Core の 1 か所で定める。

### 2. plan/diff の警告 `ASSET_HOST_PATH_UNMAPPED`

- 取り込みが必要（`create`）な texture・audio のうち、Resonite に渡すパスが `/` で始まり、`hostPathMap` で変換されないものがあれば、plan の `warnings` に 1 件だけ出す（severity `warning`、path `$assets`）。件数と最初のパスを本文に入れる。
- 本文は「Windows の Resonite はこのパスを開けない。`hostPathMap` を設定する。Resonite がこのホストで直接動いている場合は無視してよい」とする。
- apply は止めない（Linux でネイティブに動く Resonite なら読めるため）。
- Windows の CLI のパス（`C:\`・UNC）は警告しない。

### 3. 失敗時の案内

asset の取り込みで `RLoopException` が起きたら、`WorldService` で `context` に `asset`（key）、`kind`、`source`（CLI のパス）を足す。Resonite がパスを開く種類では `hostPath`（渡したパス）と `hostPathMap`（設定値、無ければ null）も足す。そのうえで次のように扱う。

- Resonite がパスを開く種類で、`ASSET_IMPORT_FAILED` の本文が `DirectoryNotFoundException` または `FileNotFoundException` を含む場合は、`ASSET_HOST_PATH_UNREACHABLE`（exit 3）に読み替える。CLI は plan の時点でファイルの存在を確かめているので、Resonite のホストから読めないことが原因とみなせる。Resonite の本文は `context.resoniteError` に残す。
  - 対処: `hostPathMap` が無ければ設定を案内する（例を示す）。あれば `TO` が Resonite のホストから読めるか確かめるよう案内する。Resonite のホストで apply する方法も示す。
- Resonite がパスを開く種類で `REQUEST_TIMEOUT` になった場合は、コードはそのままにして、対処を足す:「Resonite は開けないパスの報告に約 50 秒かかり、既定の要求タイムアウト（30 秒）より長い。`hostPath` が Resonite のホストから読めないなら `hostPathMap` を設定する。`--timeout 90` で再実行すると Resonite のエラーを受け取れる」。
- それ以外の失敗は、`context` を足すだけでコードと本文は変えない。
- 外側の catch が付ける件数（`slotsCreated` など）と再実行の案内は従来どおり。

### 4. 文書

- `README-DETAILS.md`: 設定の優先順位の一覧に `--host-path-map`・`RESOLOOP_HOST_PATH_MAP` を足す。Blender／asset の節に、コンテナや別ホストの Resonite へテクスチャを取り込む手順（`hostPathMap` の書き方、WSL の例、警告・エラーコード）を書く。
- `docs/BLENDER.md`・`docs/DECLARATIVE.md`: 「同じ絶対パスで読める共有先」の記述に `hostPathMap` を足す。
- `skills/codex/resonite-blender/SKILL.md`: 別ホストの記述を `hostPathMap` に合わせ、`ASSET_HOST_PATH_UNMAPPED`・`ASSET_HOST_PATH_UNREACHABLE` を見たら同じ apply を繰り返さず、利用者に設定を依頼するよう書く。
- CLI の help: Global options と Environment に足す。

## テスト

- 書く: `HostPathMap` の解析と変換の単体テスト。区切りの位置での一致、区切り文字の変換、一致しないパスの扱い、解析の誤りを確かめる。誤った変換は、取り込みのたびに約 50 秒待って失敗する形で現れるため、実行して確かめる価値がある。CI の dotnet test は Windows で動くので、パスは `Path.GetTempPath()` から作り、どちらの OS でも同じ期待値になるようにする。
- 書かない:
  - 設定の優先順位（既存の `Pick` を使い、他の設定のテストで確かめている）
  - 警告の条件とエラーの読み替え（実機で plan/apply を実行して確かめる。警告は `/` 始まりのパスでしか出ず、Windows の CI では実行されない）
  - 文書・SKILL.md・help の文面
- 実機の確認（ポート 40778）: `ResoLoop_Test_HostPathMap_*` の Slot だけを作る apply 文書で、次を確かめ、作った Slot を正確な ID で削除する。
  1. 設定なしの plan で `ASSET_HOST_PATH_UNMAPPED` が出る
  2. 設定なしの apply（既定 30 秒）で `REQUEST_TIMEOUT` になり、`context` に `asset`・`hostPath` があり、`slotsCreated` が 0
  3. 設定なしの apply `--timeout 90` で `ASSET_HOST_PATH_UNREACHABLE` になる
  4. `--host-path-map` ありの plan で警告が出ず、apply が成功し、StaticTexture2D の URL が入る

## 対象外

- 中身を送る取り込み（選択肢 2）
- 複数の対応付け
- create-reso-world の Dev Container で `RESOLOOP_HOST_PATH_MAP` を自動で渡すこと（`initialize.bash` は WSL のパスを知っているので可能だが、別の作業として扱う）
