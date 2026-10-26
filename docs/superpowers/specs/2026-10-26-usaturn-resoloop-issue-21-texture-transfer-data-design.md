# usaturn/resoloop#21 画素データでテクスチャを送る取り込み（`--texture-transfer data`）の設計

## 管理

| 項目 | 値 |
| --- | --- |
| 文書管理リポジトリ | usaturn/create-reso-world（branch `docs/resoloop-issue-21-texture-transfer-data`） |
| 対象 | usaturn/resoloop Issue #21（https://github.com/usaturn/resoloop/issues/21） |
| 実装の branch | usaturn/resoloop `feat/issue-21-texture-transfer-data`（`origin/main` = 上流 main `4077350` から作成） |
| 状態 | draft |
| 関連 | usaturn/create-reso-world#277（再現の記録と create-reso-world 側の変更）、usaturn/resoloop#12・#16（以前のパス変換 hostPathMap。`709d57d`） |

### 実行許可

- 利用者の指示: `/issue-to-pr https://github.com/usaturn/resoloop/issues/21 --merge`
- 着手時に、Issue の「fork の main は上流と同じに保つ」と `--merge`（fork の main へのマージ）が食い違うことを確認した。利用者は一度「PR まで・マージしない」を選び、続けて「やっぱりマージしてください」と指示した。したがって `--merge` のとおり、PR の作成後に PR 修正ループを回し、修正不要なら `finalize.py` が fork の main へマージする。マージすると fork の main は上流から分かれ、上流がこの機能を取り込むまで `scripts/resoloop-fork.sh sync` は止まる（利用者に説明済み）
- 許可された範囲: Issue #21 の実装、実機での確認、fork への push、fork の PR と create-reso-world の文書 PR の作成、ループの中の修正とマージ。上流（orange3134/resoloop）への Issue・PR・コメントは範囲外（Issue の「上流 PR に向けて」）
- この文書の承認（`approved`）は得ていない。利用者の実行指示は実行許可であり、内容の承認ではない

## 背景と目的

CLI と Resonite がファイルシステムを共有しない構成（WSL2 上の Dev Container、別の PC）では、`ImportTexture2DFile` に渡した CLI 側のパス（`/workspaces/...`）を Resonite が開けず、新規テクスチャを含む `resoloop apply` が必ず失敗する（既定の 30 秒で `REQUEST_TIMEOUT`、延ばすと約 52 秒後に `ASSET_IMPORT_FAILED`）。メッシュは CLI が中身を `ImportMeshRawData` で送るので影響を受けない。

テクスチャも中身を送れば、Resonite からパスが読めるかどうかに左右されなくなる。設定 1 つで、CLI が画像を復号し、画素を `ImportTexture2DRawData` で送れるようにする。

## 目標

- `--texture-transfer data` で、コンテナや別の PC の CLI から新規テクスチャを含む bundle を apply でき、もう一度 `diff` すると 0 件になる
- 既定の `file` の挙動は変えない（同じ PC で使っている人に影響しない）
- 復号できない画像は、ワールドを変える前に専用のエラーで止まる
- 実機で `file` と `data` を比べた結果（Issue の「実装の前に確かめること」の 1〜4）を記録する

## 対象外

- audio の生データ送信（`ImportAudioClipRawData`）。`data` でも audio は今までどおりファイルで取り込む
- HDR 画像（Radiance `.hdr`）の生データ送信（`ImportTexture2DRawDataHDR`）。`data` では復号できない画像として止める
- 接続先が別ホストかを判定して自動で切り替えること、`file` で失敗したら `data` で送り直すこと（Issue の「検討した他の案」で見送り済み）
- 上流への Issue・PR、create-reso-world 側の変更（`initialize.bash` の環境変数、README。create-reso-world#277 で扱う）

## 仕様

### 設定

- 名前と値: `textureTransfer` = `file` | `data`。既定は `file`
- 指定の方法: CLI `--texture-transfer`、環境変数 `RESOLOOP_TEXTURE_TRANSFER`、`.resoloop.json` とユーザー設定（`~/.resoloop/config.json`）の `textureTransfer`
- 優先順位: 既存の設定と同じ（CLI > 環境変数 > `.resoloop.json` > ユーザー設定）。`--verbose` の `configSources` に出どころを出す
- 値の大文字・小文字と前後の空白は区別しない。ほかの値は `INVALID_TEXTURE_TRANSFER` で止める（CLI の値は終了コード 2、環境変数・設定ファイルの値は 3。`context` に値と出どころ）

### `data` のとき

- 対象は kind が `texture`（`texture2d`）で、plan が `create`（新規・変更あり）の asset。`resdb:` などの URI の asset と、取り込み済みで変わっていない asset（`no-op`）は今までどおり
- CLI が画像を復号し、RGBA 8 bit の画素を上の行から順に並べて `ImportTexture2DRawData` で送る（ResoniteLink の `Span2D` は `x + y * width`、公式 UnitySDK は下からの行を上からに並べ替えて送っている）。`colorProfile` の値は実機の比較で決める（「実機での確認」）
- 復号は StbImageSharp（`2.30.16`、Unlicense OR MIT、managed のみ）を使い、RLoop.Core に置く。Core は ResoniteLink の型を参照しない規約なので、画素は Core の型（幅・高さ・RGBA のバイト列・colorProfile）で表し、adapter が `ImportTexture2DRawData` に詰める（バイト列をそのまま `RawBinaryPayload` にして複製しない）
- 送る前の確認: plan（apply の変更前の準備を含む）で、対象の画像のヘッダーを読み、StbImageSharp が扱えない形式（WebP など）と HDR は `ASSET_TEXTURE_UNDECODABLE`（終了コード 6）で止める。`context` に asset の key・パス・理由。`file` へ自動で切り替えない（コンテナでは約 52 秒待って失敗するだけなので）
- 画素の全体の復号は取り込みの直前に 1 枚ずつ行う（大きな画像を全部メモリに持たない）。ヘッダーは読めて本体が壊れている画像は、そこで同じエラーで止まる。apply は asset の取り込みを Slot・Component の変更より先に行うので、ワールドは変わらない
- audio の asset を新規に取り込む plan では、警告 `ASSET_AUDIO_FILE_TRANSFER` を出す（audio は Resonite が自分のホストでファイルを開くので、`data` でも別ホストでは失敗しうる）
- 取り込み済みかどうかの判定（state の `SourceHash`。CLI 側で画像ファイルの SHA-256 を計算）は変えない。転送方式を切り替えても、変わっていない画像は取り込み直さない

### `file` のとき

- 取り込みの経路は今までどおり（`ImportTexture2DFile` にパスを渡す）
- テクスチャの取り込みが `REQUEST_TIMEOUT` か、パスが見つからない `ASSET_IMPORT_FAILED`（Resonite のエラーに `DirectoryNotFoundException`・`FileNotFoundException` を含む）で失敗したら、エラーの `suggestions` に `--texture-transfer data`（`RESOLOOP_TEXTURE_TRANSFER=data`）の案内を足し、`context` に asset の key とパスを足す。エラーのコードと終了コードは変えない

### 文書

- `README-DETAILS.md`: 設定の優先順位の一覧、Blender の節（テクスチャの転送方式、エラー、警告）
- `docs/BLENDER.md`・`docs/DECLARATIVE.md`: 画像のパスが Resonite から読める必要がある、という記述に `data` を足す
- `skills/codex/resonite-blender/SKILL.md`（同梱スキル）: 別ホスト・コンテナのときの手順
- 実機での確認の結果: `docs/TEXTURE-TRANSFER.md`（新規。測定の記録は README-DETAILS か、そこからリンクする文書に置く規約）
- CLI のヘルプ（Global options、Environment の一覧）
- `README.md`・`README_JA.md` は概要だけなので変えない

## 実機での確認

Issue の「実装の前に確かめること」を、Core の復号と adapter の生データ送信を作った後、WorldService に組み込む前に行う。結果で `colorProfile` と EXIF の扱いを決めてから組み込む。

- 環境: Windows 11 の Resonite 2026.9.18.82 / ResoniteLink 0.13.1、CLI は WSL2 上の Dev Container。利用者に Resonite の起動と、試験用のワールドを開くことを、接続の直前に依頼する
- `file` の比較対象は、Resonite から読めるパス（`\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world\...`）を直接 `ImportTexture2DFile` に渡して取り込む
- 試験用のプログラムは、コミットしない作業領域（`tmp/agents/issue-21.*`）に置き、worktree の RLoop.Core・RLoop.ResoniteLink を参照する。ワールドへの変更は `ResoLoop_Test_TextureTransfer_*` の Slot の下に限り、終わったらその Slot だけを消す
- 見比べ方: 色の異なる平らな区画を格子に並べた画像（左上と右下の区画を変えて上下・左右の反転も分かるようにする）を、UIX の Image で並べて表示し、`Uncompressed=true` にして撮影する。区画の中央の画素を読み、`file` と `data` の差を比べる（8 bit で差が 3 以下を一致とする）

| 項目 | 内容 | 判定と決め方 |
| --- | --- | --- |
| 1. 色 | sRGB のカラー画像、アルファ付きの PNG、ノーマルマップ（`IsNormalMap=true`）、データ用の画像（`PreferredProfile=Linear`）を、`file` と、`data` の `colorProfile` 未指定・`sRGB`・`Linear` で比べる | 全部で `file` と一致した値を採用する。明示の値と未指定が同じ結果なら明示の値を採る。どの値も一致しなければ止まって報告する（Issue の 5: パス変換を代わりの案として出し直す） |
| 2. 形式 | JPEG（EXIF の向き 6）、16 bit の PNG、パレットの PNG、グレースケールの PNG | EXIF の向きを Resonite が反映するなら、CLI の復号でも反映する。16 bit は 8 bit に落ちる差（丸めの範囲）なら記録だけにする |
| 3. 大きさ | 2048²（16 MiB）と 4096²（64 MiB）を `data` で送り、時間を `file` と比べる | 送れなければ、上限を確かめて plan で止める確認を足すかを決める |
| 4. 保存と再読込 | `data` で取り込んだ asset の URL の形、ワールドの保存で resdb に移るか、再読込の後の `diff` が 0 件か | 利用者にワールドの保存と開き直しを依頼する。0 件にならなければ原因を調べる |

受け入れの確認: 組み込んだ後、Dev Container の CLI（worktree のビルド。利用者の global の `resoloop` は差し替えない）で、新規テクスチャを含む bundle を `--texture-transfer data` で apply し、もう一度 `diff` して 0 件になること、`file` で同じ bundle が今までどおり失敗し、新しい案内が出ることを確かめる。

## テストの方針

対象リポジトリの `AGENTS.md`（引数の解析・設定の優先順位・値の変換・エラーコードのオフラインテストを保つ）と、create-reso-world の「テストの採用基準」（壊れても気付けない損害を防ぐものだけ）の両方を満たす最小の組にする。

- 設定: `textureTransfer` の優先順位と、不正な値の拒否（1 件ずつ）
- 復号: 上下・左右の向きと RGBA の並び、グレースケール・パレット・16 bit の PNG の展開（誤ると、テクスチャが反転・変色したまま気付けない）
- 変更前の停止: 復号できない画像で、`data` の apply がワールドを変えずに `ASSET_TEXTURE_UNDECODABLE` で止まること（壊れると、変更の途中で止まる）。正しく通る例として、同じ文書で `file` なら止まらないこと
- 経路: `data` でテクスチャが生データの取り込みに、audio がファイルの取り込みに回り、audio の警告が出ること
- `file` の失敗の案内は、文言を照合するだけになるので、テストを書かずに実機で確かめる
- 実機の確認は、コミットしない試験用のプログラムで行い、結果を `docs/TEXTURE-TRANSFER.md` に記録する。opt-in の統合テストは足さない（`file` の比較にはパスの橋渡しが要り、上流の利用者の環境で再現できないため）

## 決定記録

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 対応方針 | Issue の推奨どおり、転送方式の設定を足し、`data` で画素を送る | パス変換（#16）、常に `data`、失敗したら `data` で送り直す、自動判定 | Issue の比較のとおり。どの構成でも設定 1 つで動き、既定の挙動を変えない | 委任（推奨案） |
| D-2 | 設定の名前・値・優先順位 | `--texture-transfer` / `RESOLOOP_TEXTURE_TRANSFER` / `textureTransfer`、`file`・`data`、既存と同じ優先順位 | `--texture-mode`、真偽値の `--send-texture-pixels` | Issue の仕様の案のとおり。将来 audio の生データを足すときも値で広げられる | 委任（推奨案） |
| D-3 | 不正な値 | `INVALID_TEXTURE_TRANSFER` で止める（CLI は 2、環境変数・設定は 3） | 不正な値を無視して `file` | 黙って `file` になると、コンテナでは 52 秒待って失敗するまで誤りに気付けない | 委任 |
| D-4 | 復号の置き場所 | RLoop.Core に StbImageSharp を足し、画素は Core の型で adapter へ渡す | adapter（RLoop.ResoniteLink）で復号 | 変更前の確認（plan）が Core で行われる。Core は ResoniteLink の型を参照しない規約を守れる | 委任 |
| D-5 | 復号ライブラリ | StbImageSharp 2.30.16 | SixLabors.ImageSharp（利用条件のあるライセンス）、SkiaSharp（RID ごとのネイティブライブラリ） | Issue の条件（managed のみ、AGPL と両立、PNG・JPEG）を満たす。上流の意向は上流 PR の前に確かめる（範囲外） | 委任 |
| D-6 | 変更前の確認の深さ | ヘッダーだけを読む（形式と HDR の判定） | plan で全部を復号する | 大きな画像の全部の復号を plan と apply で 2 回しない。本体が壊れていても、asset の取り込みは Slot・Component の変更より先なのでワールドは変わらない | 委任 |
| D-7 | HDR | `data` では `ASSET_TEXTURE_UNDECODABLE` で止める | 8 bit に落として送る、`ImportTexture2DRawDataHDR` で送る | 黙って階調を落とさない。HDR の生データ送信は対象外（必要なら別 Issue） | 委任 |
| D-8 | audio | `data` でもファイルで取り込み、plan で `ASSET_AUDIO_FILE_TRANSFER` を警告 | audio も止める | Issue の仕様の案のとおり。同じ PC の Resonite なら audio は今までどおり取り込める | 委任（推奨案） |
| D-9 | `colorProfile` | 実機の比較で決める（「実機での確認」の 1 の決め方） | 推測で `sRGB` に固定 | ResoniteLink の公開物に既定の扱いの説明が無く、上流の規約が推測を禁じている | どの値も一致しなければ停止 |
| D-10 | EXIF の向き | 実機の比較で決める（Resonite が反映するなら CLI でも反映） | 常に無視、常に反映 | `file` と `data` で同じ見た目にするため | 委任 |
| D-11 | `file` の失敗の案内 | `REQUEST_TIMEOUT` とパスが見つからない `ASSET_IMPORT_FAILED` に `--texture-transfer data` の案内を足す | 新しいエラーコードに置き換える | 既存のエラーコードを使う利用者・スキルの挙動を変えない | 委任 |
| D-12 | 実機の確認の方法 | コミットしない試験用のプログラムで、`file`（橋渡しのパス）と `data` を並べて撮影し、区画の画素を比べる | opt-in の統合テストを足す、目視だけ | 上流の環境で再現できない橋渡しのパスを持ち込まない。画素を数値で比べる | 委任 |
| D-13 | 実装の担当と方式 | このセッションが `superpowers:executing-plans` で順に実装する | subagent-driven-development | `implement_task.py check` の `self` が true（雛形の既定の適用）。同じファイル（WorldService・Program）への逐次の変更で、途中に利用者の操作を要る実機の確認がある | 委任 |
| D-14 | `--merge` とループ | `--merge` のとおり、PR の作成後にループを回し、修正不要なら fork の main にマージする。ループのオプションは無し（`check-options` の結果: サイクルの上限 3、レビュアー claude-opus・devin-swe・pi-deepseek、修正の担当 claude-opus、いずれも既定の適用） | PR まで（利用者が一度選び、取り消した） | 利用者の明示の指示（「やっぱりマージしてください」） | ループの停止・エラーで停止 |
| D-15 | 受け入れの確認で使う CLI | worktree のビルドを `dotnet` で直接実行する | `scripts/resoloop-fork.sh install` で global に導入 | 利用者の global の `resoloop`（他のワールドの作業で使う）を差し替えない | 委任 |
