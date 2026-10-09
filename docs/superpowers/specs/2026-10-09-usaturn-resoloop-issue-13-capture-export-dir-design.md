# usaturn/resoloop Issue #13: コンテナ上の capture の早期停止と、Windows の写真フォルダのマウント

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/resoloop/issues/13（関連: #12）
- 実装対象: `usaturn/resoloop`（上流 `orange3134/resoloop`）と `usaturn/create-reso-world` の `.devcontainer/`
- 状態: approved（2026-10-09 にユーザーが「進めてください」で承認。承認した版: `04a74fd`）
- 調査したコード HEAD: resoloop `9cf7178f02a696cd91ae5fb092b9078e98f25beb`、create-reso-world `2b260b69fea36e0f2fc2616cf4d8bcf1a9e93b83`
- Plan: `../plans/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-13-screenshots`（ブランチ `feat/resoloop-13-screenshot-mount`）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-13-capture-export-dir`（ブランチ `fix/issue-13-capture-export-dir`）

## 経緯と決定事項

ユーザーは Issue #13 への対応を指示し、「slum02・slum03 ではエージェントが自力でスクリーンショットを取得していたはず」と述べた。調査の結果を示したうえで、次をユーザーが選んだ。

- 対応範囲: resoloop の修正と Dev Container のマウントの両方
- リンクの作り方: ユーザーが WSL で 1 回だけ手動で作る（補助スクリプト・自動検出はしない）
- 環境変数: リンクがあるときだけコンテナに渡す
- 設計 1（resoloop）と設計 2（Dev Container）は、会話で提示した内容のとおりに了承済み

## 調査結果

### 過去のワールドでの capture

Resonite の `capture` が成功した記録は無い。

| プロジェクト | 結果 |
| --- | --- |
| akichi | 4 カメラとも `CAPTURE_EXPORT_TIMEOUT`（`artifacts/akichi/delivery-report.json`） |
| MyResoniteProject | 2 回とも `CAPTURE_EXPORT_TIMEOUT` |
| slum02 | `CAPTURE_EXPORT_TIMEOUT`（`artifacts/slum02/qa/capture-attempt.json`） |
| slum03 | `CAPTURE_EXPORT_TIMEOUT` 1 回、ほかは「not run (screenshot dir not mounted)」 |

Claude Code・Codex・pi のセッション記録にも、capture の成功出力は無い。エージェントが自分で用意した画像は Blender のプレビュー描画である（slum02 の `artifacts/slum02/preview/*.png` は `review.md` に「Cycles CPU、頂点カラー表示」とある）。Resonite 上の材質・文字・透明の見え方は、エージェント自身では確認できていなかった。

### 原因

1. `devcontainer.json` は `--network=host` で動き、`ws://localhost:PORT` が Windows の Resonite に届く。CLI は loopback の接続を同じマシンとみなし、`--screenshots-dir` が無くても止めない（`src/RLoop.Cli/Program.cs:205`）。
2. Linux に `~/Pictures` が無いと `Environment.GetFolderPath(MyPictures)` は空文字を返す。`Path.Combine("", "Resonite")` が相対パスになり、作業ディレクトリ直下の `Resonite` を監視先にする（`src/RLoop.Core/ScreenshotDirectoryResolver.cs:15-18`）。
3. `ScreenshotExport` は監視先の親があることだけを確かめる。撮影の指示は成功し、写真は Windows 側に保存されるが、CLI は届かないファイルを `--capture-timeout`（既定 60 秒）まで待つ。

### 接続越しの画像の受け取り（Issue の期待動作 2）

ResoniteLink 0.13.1（NuGet の最新版）には Import 系のメッセージしか無く、アセットのデータを読み出す手段が無い。上流の Yellow-Dog-Man/ResoniteLink#89 では、Frooxius が「アセット保護の仕組みができるまで、ResoniteLink にアセットの読み出しは入れない」と述べている。このため対応しない。

## 目的と成功条件

1. 写真の保存先を CLI から読めない構成では、接続も一時 Slot の作成もせずに、すぐ `CAPTURE_EXPORT_DIR_UNREACHABLE` で止まる。作業ディレクトリ直下の `Resonite` を監視先にしない。
2. capture の失敗（`CAPTURE_EXPORT_DIR_UNREACHABLE`・`CAPTURE_EXPORT_TIMEOUT`・`CAPTURE_DIRECTORY_NOT_FOUND`）のエラーに、監視先とその指定元、調べた候補、対処が入る。
3. Dev Container で、ユーザーが WSL に 1 回リンクを作って rebuild すると、エージェントが `resoloop capture` で Resonite の画像を取得できる。
4. リンクが無い Dev Container では、成功条件 1 のとおりすぐに止まる。

## 選択肢と採用理由

1. **採用: resoloop の早期停止と診断 ＋ 任意の読み取り専用マウント ＋ リンクがあるときだけ環境変数を渡す。** 撮影を可能にする経路と、使えない構成ですぐに止める経路の両方がそろう。
2. 環境変数を `containerEnv` で常に渡す。生成ファイルは不要だが、リンクが無いときも空のフォルダを監視してタイムアウトまで待つ。この環境で成功条件 4 を満たせないため不採用。
3. resoloop が Linux で `/mnt/c/Users/*/Pictures/Resonite` などを自動で探す。Windows のドライブ全体をコンテナに見せる必要があり、利用者の写真などが広く見える。resoloop が特定の環境の配置を知ることにもなるため不採用。

## 設計 1: resoloop

### 既定の保存先の解決

`ScreenshotDirectoryResolver.ResolveDefault` は、Pictures の既知フォルダが空文字（取得できない）のとき、`Resonite` を候補に入れない。OneDrive の候補も無く、候補が 1 つも無いときは `CAPTURE_EXPORT_DIR_UNREACHABLE` を投げる。

候補がある場合の挙動は変えない。Windows で Pictures があれば、初回の書き出しを待つ既存の挙動と、OneDrive のリダイレクト先の検出をそのまま使う。Linux に `~/Pictures` がある場合も既存どおり `~/Pictures/Resonite` を返し、届かなければ下記の診断付きのタイムアウトになる。

戻り値の型（`string`）は変えない。統合テストが `ResolveDefault()` をそのまま呼んでいるため。

### 止めるタイミング

`Program.cs` の capture は、保存先の解決（207 行）を ResoniteLink への接続（208・209 行）より前に行う。この順序を保ち、`CAPTURE_EXPORT_DIR_UNREACHABLE` は接続も一時 Slot の作成もせずに返る。

### 指定元の受け渡し

`ConfigResolution.Sources["screenshotsDirectory"]`（`cli`・`environment:RESOLOOP_SCREENSHOTS_DIR`・設定ファイルのパス）を、既定の解決のときは `default` として、`LiveCaptureService.CaptureAsync` の末尾の省略可能な引数で `ScreenshotExport` に渡す。省略時は `default` 扱いとし、統合テストの呼び出しは変えない。

### エラーの仕様

既存のメッセージの文言は変えず、`context` と `suggestions` を足す。

| コード | 終了コード | context | 発生する場面 |
| --- | --- | --- | --- |
| `CAPTURE_EXPORT_DIR_UNREACHABLE`（新規） | 3（ConfigurationError） | `picturesFolder`（取得した Pictures、取れなければ空文字）、`candidates`（調べた候補のパスと存在の有無）、`oneDriveCandidatesChecked`（Windows でだけ true） | 指定が無く、既定の候補も無い |
| `CAPTURE_DIRECTORY_NOT_FOUND`（既存） | 6（既存のまま） | `directory`、`directorySource` | 監視先も親も無い |
| `CAPTURE_EXPORT_TIMEOUT`（既存） | 8（既存のまま） | `directory`、`directorySource`、`directoryExistedBeforeCapture`、`imagesBeforeCapture`、`waitSeconds` | 待ち時間内に画像が届かない |

`CAPTURE_EXPORT_DIR_UNREACHABLE` と `CAPTURE_EXPORT_TIMEOUT` の `suggestions` には、次の対処を英語で入れる。

- `--screenshots-dir`・`RESOLOOP_SCREENSHOTS_DIR`・`screenshotsDirectory` のどれかで、この CLI から読めるフォルダを指定する
- Resonite が別のマシンやこのコンテナの外（例: Windows のホストと Linux の Dev Container）で動いているなら、その Pictures/Resonite をマウントして、そのマウント先を指定する
- タイムアウトでは、加えて対象のワールドが表示中か、レンダラーが動いているかを確かめる

### 文書と同梱スキル

- `README-DETAILS.md` の In-game screenshots の節: 新しいエラーと、コンテナから使うときはホストの写真フォルダのマウントが要ることを追記する
- `skills/codex/resonite-build/SKILL.md` の capture の手順: `CAPTURE_EXPORT_DIR_UNREACHABLE` では再試行せず、ユーザーに保存先の設定を頼むか、ユーザーの目視確認に回すことを、既存の文の範囲で短く追記する

## 設計 2: Dev Container

### マウント

`devcontainer.json` の `mounts` に 1 件足す。

```text
source=${localEnv:HOME}/.local/share/create-reso-world/resonite-screenshots,
target=/home/vscode/.local/share/create-reso-world/resonite-screenshots,type=bind,readonly
```

既存の規則（ソース `~/<rel>` とターゲット `/home/vscode/<rel>` が同じ相対パス、`mounts.bash` で `initialize.bash` と突き合わせる）に合わせる。読み取り専用にして、コンテナから Windows の写真を変更・削除できないようにする。

### ホスト側の準備（`initialize.bash`）

1. `~/.local/share/create-reso-world/resonite-screenshots` がシンボリックリンクで、リンク先が無いときは、リンク先のパスと「/mnt/c が見えるか、Resonite が写真を 1 枚保存したかを確かめるか、リンクを消す」旨を表示して終了コード 1 で止まる。Docker がマウントに失敗する前に、原因の分かるメッセージを出すため。
2. 既存の `mkdir -p` の一覧に上記のパスを足す。無ければ空のディレクトリを作り、リンクならそのまま使う。
3. スクリプトと同じディレクトリの `resonite-screenshots.env` を毎回書き直す。パスがシンボリックリンクなら `RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots` の 1 行、そうでなければ空にする。

### 環境変数の受け渡し

`devcontainer.json` の `runArgs` に `--env-file` と `${localWorkspaceFolder}/.devcontainer/resonite-screenshots.env` を足す。`.gitignore` に `/.devcontainer/resonite-screenshots.env` を足す。マウントと同じくコンテナの作成時に決まるので、リンクを作った後は rebuild が要る。

### postCreate（`install_beforehand.bash`）

マウントしたディレクトリを書き込み可能にする処理の対象に、読み取り専用のこのマウントを入れない。

### 手順の文書（`.devcontainer/README.md`）

「Resonite ワールド開発ツール」の節に、任意の設定として次を書く。

1. Windows の PowerShell で `[Environment]::GetFolderPath('MyPictures')` を実行し、Pictures の場所（OneDrive の場合を含む）を調べる
2. その下に `Resonite` フォルダが無ければ、Resonite で写真を 1 枚撮る
3. WSL で空のディレクトリを `rmdir` し、`ln -s /mnt/c/Users/<名前>/.../Pictures/Resonite ~/.local/share/create-reso-world/resonite-screenshots` を実行する
4. Dev Container を rebuild し、コンテナで `echo "$RESOLOOP_SCREENSHOTS_DIR"` と `ls` で確かめる

## テスト

AGENTS.md のテストの採用基準に従う。

resoloop（xUnit、`tests/RLoop.Tests`）:

- Pictures が空文字で OneDrive の候補も無いとき、相対パスを返さずに `CAPTURE_EXPORT_DIR_UNREACHABLE` を投げ、context に `picturesFolder` と `candidates` が入る（今回の不具合の再発防止）
- タイムアウトのエラーの context に、指定元・撮影前の存在・撮影前の画像の数・待った秒数が入る
- 既存の既知フォルダの規則・OneDrive の検出・タイムアウト・曖昧な書き出しのテストが通り続ける

create-reso-world（`.devcontainer/test-initialize-mounts.bash`）:

- マウントの固定一覧に 1 件足す。ホストの永続領域の増減を守るための既存の固定値なので更新する
- `initialize.bash` を一時ディレクトリにコピーして実行し、リポジトリの `.devcontainer/resonite-screenshots.env` を書き換えない。空のディレクトリなら env ファイルが空、リンク先があるリンクなら変数の 1 行、リンク先が無いリンクなら終了コード 1 とメッセージ
- postCreate が読み取り専用のマウントを書き込み可能化の対象から外していること（既存の検査 4 の除外）

テストを書かない部分（README・SKILL.md の文面）は、`git diff` の確認で代える。

## 検証

1. resoloop: `dotnet build` と `dotnet test tests/RLoop.Tests`
2. create-reso-world: `bash .devcontainer/test-initialize-mounts.bash` と `bash scripts/check-layout.sh`
3. コンテナでの再現: 修正版の resoloop を `scripts/resoloop-fork.sh install` で導入し、リンクが無い今の状態で `resoloop capture ... --camera NAME --output out.jpg` が、Resonite に接続せずにすぐ `CAPTURE_EXPORT_DIR_UNREACHABLE` で止まることを確かめる。導入した修正版は戻さずに残す。次の rebuild（検証 4 の前にユーザーが行う）で公開版に戻る
4. 実機の撮影（ユーザーの作業が要る）: ユーザーがリンクを作って rebuild した後、`ResoLoop_Test_Capture_*` の一時 Slot だけを使う撮影で画像が届き、エージェントが画像を読めることを確かめる。rebuild でセッションが切れるため、agent-handoff の引き継ぎを残す。リンクがあれば環境変数で保存先が決まるので、rebuild 後に公開版の resoloop に戻っていても撮影できる

## 範囲外

- 接続越しの画像の受け取り（ResoniteLink が対応していない）
- `hostPathMappings` などのパスの対応付け。capture は既存の `screenshotsDirectory` で足りるため、#12 で扱う
- リンクを作る補助スクリプトと、起動時の自動検出
- loopback の接続を同じマシンとみなす判定（`Program.cs:205`）の変更
- 上流 orange3134/resoloop への PR と NuGet の公開

## 作業場所と公開

- resoloop の変更は CODE_ROOT のブランチ `fix/issue-13-capture-export-dir` にコミットする
- Dev Container の変更とこの Spec・Plan は DOC_ROOT のブランチ `feat/resoloop-13-screenshot-mount` にコミットする。create-reso-world 自身の変更を含むので、文書はその PR に含める
- push・fork PR・create-reso-world の PR の作成とマージは、ユーザーの明示指示があるときだけ行う。それまでは「公開未実施」と報告する
