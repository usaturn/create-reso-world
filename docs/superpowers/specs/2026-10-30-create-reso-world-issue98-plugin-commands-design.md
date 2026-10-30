# create-reso-world#98 プラグインのコマンドの起動・終了・doctor と組み込み名 catalog 設計

## 管理

- 状態: `draft`（内容の承認は無い。下の実行許可は内容の承認ではない）
- Issue: [usaturn/create-reso-world#98](https://github.com/usaturn/create-reso-world/issues/98)（親 [#95](https://github.com/usaturn/create-reso-world/issues/95)、ボードのキー `resoloop-plugins-board`、子のキー `plugin-commands`）
- 実装の対象: `usaturn/resoloop`。base は `feat/plugin-v2`。最初に捕捉したのは `dd0b40fb216b0c9fbd82da44903195a885104015`（F #297 の PR usaturn/resoloop#26 のマージ）。文書の base は create-reso-world `main` の `acd288c3e81a6c108136e37815e718a0fe088195`
- base の変更: 実行の中断中（2026-10-30、利用上限）に `feat/plugin-v2` が `0143618cdf455324c07d5fd093b394bea47ad02b`（#99 の PR usaturn/resoloop#27、#100 の PR usaturn/resoloop#28 のマージ）に進んだ。issue-to-pr の停止条件に当たるので利用者に確認し、「新しい base で続ける」の選択を受けた。未 push のブランチを `0143618` に rebase し（衝突なし、共有するファイルなし）、build・テスト・一時の確認をやり直した。設計の内容は変えていない
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/98 --base feat/plugin-v2`。issue-to-pr の規定により、通常の設計判断を推奨案で決め、Spec・Plan・実装・検証・commit・push・PR 作成まで進める。`--merge` が無いのでマージ・ループはしない。上流への投稿・fork main の更新・リリース・グローバル導入はしない
- 予約: create-reso-world `refs/heads/agent-claims/issue-98` / `3e57bf9a2be48e979c16f67f4dfd16de3af0806c`（session `a8430e79-1c8f-4a68-82bb-75724b138d3d`、[着手記録](https://github.com/usaturn/create-reso-world/issues/98#issuecomment-6523005163)）
- 先行の確認: F #297 は `state_reason=completed`。PR #26 の head `cc925fb` と merge `dd0b40f` が base の祖先であることを確認した
- 実装の担当: agent-runner の `workflows.issue.implement` は雛形の既定の `self`（利用者の指定ではない）

## 1. 目的と範囲

親 #95 の D-4 を実装する。組み込みに無い名前を、導入済みのプラグインのコマンドとして `resoloop [--project DIR] <コマンド> [引数...]` で実行し、プラグインが宣言した外部ツールを `doctor` で確かめる。CLI への結線（`Program.cs`）は I #298 が行う。#98 は I がそのまま呼べる API と、I・#102 が依存する呼び出しの仕様を固定する。

### 変えるファイル（Issue の所有範囲）

| ファイル | 役割 |
| --- | --- |
| `src/RLoop.Core/Plugins/PluginCommandRunner.cs`（新規） | 子プロセスの起動・待機・停止。プロセスの閉じ込め（Linux のプロセスグループ、Windows の Job）と実行ファイルの解決を含む |
| `src/RLoop.Core/Plugins/PluginRuntimeEnvironment.cs`（新規） | 子へ渡す argv の展開と環境変数の組み立て。変数名の定数 |
| `src/RLoop.Core/Plugins/PluginToolProbe.cs`（新規） | doctor 用の外部ツールの確認（期限付き） |
| `src/RLoop.Cli/PluginCommandDispatch.cs`（新規） | 生 argv の分離、プロジェクト・プラグインの解決、lease の保持、シグナルの処理 |
| `src/RLoop.Cli/PluginDoctorChecks.cs`（新規） | プラグインのツール確認を `DoctorCheck` に変換 |
| `src/RLoop.Cli/BuiltinCommandCatalog.cs`（新規） | 組み込みの先頭コマンド名と予約名一式 |
| `tests/RLoop.Tests/PluginCommandTests.cs`・`PluginToolProbeTests.cs`（新規） | S の代表テスト |
| `tests/fixtures/plugins/commands/`（新規） | テスト時にビルドする偽のプラグインのプログラム |

### 変えないもの

F の所有ファイル（`SemanticVersion.cs`・`PluginNames.cs`・`PluginErrors.cs`・`PluginManifest.cs`・`PluginInstallRecord.cs`・`PluginRegistry.cs`・`PluginInstaller.cs`・`PluginGit.cs`・`PluginPathPolicy.cs`・`PluginProjectLock.cs`）、`Program.cs`・`CommandLine.cs`（I の専有）、スキル配布（#99）・レシピ（#100）のコード、fork main、上流。F の API は呼ぶだけで変更しない。

### 対象外

- `Program.cs` への結線、help へのプラグインのコマンドの一覧、doctor の出力への組み込み（I #298）
- 文書と最小例（#101）。この Spec の 3 章が文書の元になる
- 端末の対話（端末からの入力、端末の設定の変更）。プラグインのコマンドは非対話で動く前提にする（3.4）
- 本体が SIGKILL などで強制終了された場合の Linux の子孫の停止（3.5）。プロセスグループを自分で抜ける子孫（`setsid` 等）の停止
- 署名・サンドボックス・悪意ある同一ユーザへの完全な防御（親 #95 と同じ）
- macOS などの Linux・Windows 以外の OS。起動しようとすると `PLUGIN_COMMAND_START_FAILED` で止まる（F の Git の起動と同じ範囲）

## 2. 調べた現在の構造（base `dd0b40f`）

- `Program.Main` は最初に `ParsedArguments.Parse` で全引数を解析する。このパーサは `--` を拒否し、未知のオプションに続く値を食い、`--help`・`--version`・`--json` を本体の指定として扱う。プラグインへ渡す生引数は、この解析の前に分けないと復元できない
- 組み込みの先頭名は、接続前の分岐（`version`・`help`・`init`・`skills`・`uix`・`schema`・`manifest`・`bundle`・`discover`・`blender`・`doctor`・`flux`・`logs`・`validate`・`type`・`scene`・`capture`）と、接続後の `RunResonite`（`status`・`ping`・`hierarchy`・`find`・`observe`・`inspect`・`slot`・`component`・`type`・`import`・`apply`・`diff`・`plan`・`validate`・`test`・`uix`・`item`・`tool`）にある。未知の名前は接続した後の `RunResonite` の `default` で `UNKNOWN_COMMAND` になる
- 比較は名前ごとに大小文字の扱いが違う（`bundle`・`schema` は区別、ほかの多くは区別しない）
- F の `PluginRegistry.OpenVerified()` は、プロジェクトの `plugins/.lock` を `FileShare.None` で開いたまま全件を照合し、その lease を返す。lease の間は別の install・remove も、同じプロジェクトのプラグイン管理への呼び戻しも `PLUGIN_PROJECT_BUSY` になる（F の Spec 3 章）。管理領域が無ければ空の lease
- `PluginNameReservations(commands, skills, recipes)` は呼出元が渡す予約名。F の Spec は「CLI の catalog は #98、結線時に同梱スキル・レシピと合わせて #298 が渡す」とする。並行の #99（PR usaturn/resoloop#27）は `reservations` に「#98 の catalog」を渡す前提で、自分で `BundledSkillManager.Names` を足している
- F の Git の起動（`PluginGit` の private な入れ子クラス）は、親が先に終わった後の子孫の停止を `Process.Kill(entireProcessTree)` では保証できなかったため、Linux のプロセスグループと Windows の Job Object で閉じ込めている。private で F の所有ファイルの中にあるため、#98 からは呼べず、切り出しも F のファイルの変更になる
- `PluginInstaller` は導入時に `data/` を作り、Unix の実行ビットを保つ。`data/` は照合の対象外
- 設定は `ConfigResolver.Resolve(開始ディレクトリ, CLI の値)`。`commandTimeoutSeconds` の既定は 900 秒、環境変数 `RESOLOOP_COMMAND_TIMEOUT_SECONDS`。既存の設定用の環境変数は `RESOLOOP_*`（`RESOLOOP_FLUX_EXECUTABLE` 等）と `RESONITE_*`
- doctor は `DoctorCheck(Name, Status, Required, Message, Suggestion)` の一覧から、Required の全件が `pass` なら `Ready`。終了コードは準備の可否に関係なく 0（既存の挙動）
- 公開 CI は `windows-latest` だけで unit test を実行する。Linux はこの Dev Container で実行する。F のテストは `tests/fixtures/plugins/core/git-probe` の C# プロジェクトをテスト時に `dotnet build` して偽のプログラムにしている

## 3. 設計

### 3.1 呼び出しの構文と分岐

`PluginCommandDispatch.Parse(args)` が、既存のパーサより前に生の `args` を分類する。

1. 先頭から `--project DIR` と `--project=DIR` を読む（本体が解釈する指定はこれだけ）
2. 次のトークンを候補にする。候補が無い、`-` で始まる、または組み込み名（3.2、大小文字を区別しない）なら `null` を返す。`null` は「既存の流れで処理する」の意味で、既存の構文・出力を変えない
3. それ以外は `PluginInvocation(Project, Command, Arguments)` を返す。`Arguments` は候補より後のトークンをそのまま（順序・値・空文字・改行・`--help`・`--version`・`--json`・`--`・`;`・`$()` を含めて）持つ
4. 候補があるときに限り、`--project` の値が空、または `--project` が 2 回以上あれば `INVALID_ARGUMENT`（終了コード 2）

候補の名前の形は検査しない。プラグインに無い名前は 3.3 で `UNKNOWN_COMMAND` になる。I は、`Parse` が `null` を返し、かつ先頭の位置引数が catalog に無い場合も、接続より前に `UNKNOWN_COMMAND` にする（D-4「未登録名も接続前に」。3.8）。

### 3.2 組み込み名 catalog

`BuiltinCommandCatalog`（`RLoop.Cli`）が、組み込みの先頭コマンド名の唯一の一覧を持つ。

- `Commands`: 2 章の全名に、I が足す `plugin` を加えた集合（大小文字を区別しない固定の集合）。`apply`・`blender`・`bundle`・`capture`・`component`・`diff`・`discover`・`doctor`・`find`・`flux`・`help`・`hierarchy`・`import`・`init`・`inspect`・`item`・`logs`・`manifest`・`observe`・`ping`・`plan`・`plugin`・`scene`・`schema`・`skills`・`slot`・`status`・`test`・`tool`・`type`・`uix`・`validate`・`version`
- `IsBuiltin(name)`: `Commands` に含まれるか
- `Reservations`: `new PluginNameReservations(Commands, BundledSkillManager.Names, UixRecipes.Catalog の名前)`。install（I が渡す）・実行時の照合（3.3）・doctor（3.6）・#99 の init・sync が同じ値を使い、導入時と実行時の判定を共通にする

組み込みを足した版に上げると、その名前を持つ導入済みのプラグインは F の照合で `PLUGIN_NAME_CONFLICT` になる（全プラグインのコマンドが止まる）。組み込みは常に先に分岐するので、乗っ取りは起きない。catalog の漏れは、I の「catalog に無い先頭名は接続前に `UNKNOWN_COMMAND`」により、その組み込みが最初の利用で動かなくなる形で表に出る。

### 3.3 プロジェクト・プラグインの解決

`PluginCommandDispatch.RunAsync(invocation, context, cancellationToken)` は次の順に進める。`context`（`PluginDispatchContext`）は本体の版・開始ディレクトリ・環境・呼び戻しの argv を持ち、CLI は `PluginDispatchContext.Current(版)`（cwd・プロセスの環境・3.4 の呼び戻しの argv）を渡す。テストは明示した値を渡す。ResoniteLink の発見・接続はしない。

1. `new PluginRegistry(invocation.Project を context.StartDirectory から解決した絶対パス, context.ResoloopVersion, BuiltinCommandCatalog.Reservations)`。`--project` が無ければ `context.StartDirectory` から上へ探す。`--project` が無くプロジェクトが見つからない（`PLUGIN_PROJECT_NOT_FOUND`）ときは `UNKNOWN_COMMAND` にする（プロジェクトの外の打ち間違いを、従来どおり未知のコマンドとして示す）。`--project` があるときの F のエラーはそのまま返す
2. 期限を決める: manifest の `timeoutSeconds`、無ければ `ConfigResolver.Resolve(プロジェクトのルート, 空の CLI 値, context.Environment の値)` の `CommandTimeoutSeconds`
3. `using var lease = registry.OpenVerified()`。照合の失敗・`PLUGIN_PROJECT_BUSY` は F のエラーのまま返す
4. `lease.Plugins` の全コマンドから、名前が候補と大小文字を区別せずに一致するものを探す（F の照合で大小文字を無視した一意性が保証される）。無ければ `UNKNOWN_COMMAND`
5. `PluginCommandRunner.RunAsync` で実行し、子の終了コードを返す。lease は、子と子孫の停止を確かめて `RunAsync` が戻るまで持つ

### 3.4 子プロセスの起動

`PluginCommandRunner.RunAsync(PluginCommandRequest, CancellationToken)`（`RLoop.Core.Plugins`）。呼出元は、`Plugin` を返した lease を戻るまで持つ。

**実行ファイル**（`program`）の解決は本体の中で行い、絶対パスで起動する。シェルを通さない。

- `./相対パス`: `PluginPathPolicy.Combine(PackageDirectory, 相対パス)` で package の中に限る（リンクは F の照合で拒否済み）。通常ファイルであること
- それ以外の名前: 親の環境の `PATH` のうち**絶対パスの要素だけ**を順に探す。相対・空の要素（cwd・プロジェクトの中を指し得る）は使わない
- Linux: 実行権限（`euidaccess(X_OK)`）のある通常ファイル
- Windows: `.exe` だけを起動する。PATH で探す名前は `.exe` で終わらなければ `.exe` を付けて探す。`./相対パス` は付け足さず、書かれたとおりのパスが `.exe` で終わらなければ起動しない（F の導入時の検査が書かれたとおりのファイルを求めるため、付け足すと package に 2 つのファイルが要る）。`.cmd`・`.bat` は `CreateProcess` が暗黙に `cmd.exe` を通してシェル解釈が入るため、PATH でも package でも起動しない。PATHEXT は使わない
- manifest に OS ごとの指定は無い（D-1）。1 つの manifest で両方の OS に対応するプラグインは、PATH のインタープリタ（`uv`・`python`・`dotnet` 等）と `${pluginRoot}` の引数で書く。`./相対パス` の実行ファイルは OS ごとのプラグインになる
- 見つからない・起動できない・未対応の OS は `PLUGIN_COMMAND_START_FAILED`（終了コード 9）。context に `plugin`・`command`・`program`

**argv** は `[実行ファイル, manifest の args を展開したもの..., 利用者の引数...]`。manifest の `args` の `${pluginRoot}` を package の絶対パス、`${pluginData}` を data の絶対パスに文字列として置き換える（F の検証で、それ以外の `${...}` は無い）。利用者の引数は置き換えない。Linux は `posix_spawn` に argv 配列で渡す。Windows は CRT の規則（F の `QuoteWindowsArgument` と同じ規則）で 1 つずつ引用した命令行と、明示した実行ファイル名を `CreateProcessW` に渡す。NUL を含む引数は `PLUGIN_COMMAND_START_FAILED`。

**作業ディレクトリ**はプロジェクトのルート。

**環境変数**: 親の環境を引き継ぎ、名前が `RESOLOOP_PLUGIN_` で始まるもの（Windows は大小文字を区別しない）をすべて除いてから、次を設定する。親（入れ子の呼び出しなど）の値が残って別のプロジェクト・プラグインを指すことを防ぐ。

| 変数 | 値 |
| --- | --- |
| `RESOLOOP_PLUGIN_NAME` | プラグインの名前 |
| `RESOLOOP_PLUGIN_COMMAND` | manifest に書かれたコマンドの名前 |
| `RESOLOOP_PLUGIN_ROOT` | package の絶対パス（`${pluginRoot}` と同じ） |
| `RESOLOOP_PLUGIN_DATA` | data の絶対パス（`${pluginData}` と同じ） |
| `RESOLOOP_PLUGIN_PROJECT_ROOT` | プロジェクトのルートの絶対パス（cwd と同じ） |
| `RESOLOOP_PLUGIN_HOST_ARGV` | 本体を呼び戻す argv の先頭部分の JSON 配列（例 `["/home/u/.dotnet/tools/resoloop"]`、`dotnet resoloop.dll` で動いているときは `["/usr/share/dotnet/dotnet","/path/resoloop.dll"]`）。プラグインはこの後ろに引数を足して起動する。CLI の `PluginDispatchContext.Current` は `Environment.ProcessPath` の名前が `dotnet` なら `[ProcessPath, 入口のアセンブリのパス]`、それ以外は `[ProcessPath]` にし、`ProcessPath` が無い・`dotnet` で入口のアセンブリのパスが無いときは空にする（決められない）。空なら runner が `PLUGIN_COMMAND_START_FAILED` で止まる。本体を別のプロセスに組み込む呼出元は、`Current` を使わず明示の値を渡す |
| `RESOLOOP_PLUGIN_HOST_VERSION` | 本体の版（`resoloop --version` と同じ文字列） |
| `PYTHONPYCACHEPREFIX` | `<data>/.cache/python`（Python のバイトコードを package に書かせない） |
| `UV_PROJECT_ENVIRONMENT` | `<data>/.venv`（`uv run` の仮想環境を package に作らせない） |

ResoniteLink の URL は渡さない。プラグインは呼び戻しで本体を使い、本体は cwd（プロジェクトのルート）と引き継いだ環境から従来どおり設定を解決する。`uv run` が lock の無い package に `uv.lock` を書く問題は、作者が lock を同梱し `uv run --frozen` か `--locked` を使う規則として #101 の文書に書く（本体は `UV_FROZEN` 等を設定しない。4 章 D7）。

**data**: 起動の前に、lease の下で data がリンクでないことを確かめ（F の `PluginPathPolicy.EnsureNoLinks`）、無ければ作る。

**標準入出力**: 子は本体の stdout・stderr をそのまま引き継ぐ（本体は読まない・包まない・加工しない）。stdin は、本体の stdin が端末なら空の入力（Linux `/dev/null`、Windows `NUL`）、リダイレクト（パイプ・ファイル）ならそのまま引き継ぐ。Linux では子が別のプロセスグループ（端末の前面ではない）になるため、端末からの読み取りで子が止まり期限まで待つことを防ぐ。両 OS で同じ規則にし、OS で挙動を分けない。

### 3.5 終了・期限・キャンセル

**閉じ込め**: Linux は `posix_spawn` の `POSIX_SPAWN_SETPGROUP` で子を新しいプロセスグループの先頭にし、親の fd は 0〜2 以外を閉じる（`closefrom(3)`、lock のファイルを子へ渡さない）。終了の検出は `waitid(WEXITED|WNOWAIT)` で先頭の PID を確保したまま行う。Windows は `CREATE_SUSPENDED` で作り、`KILL_ON_JOB_CLOSE` の Job に入れてから再開する。継承するハンドルは `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` で標準入出力だけに限る。コンソールを引き継ぐため `CREATE_NO_WINDOW` は使わない（子孫のコンソールの窓を出さない）。F の `PluginGit` の閉じ込めと同じ方式を、#98 の所有ファイルの中に持つ（4 章 D3）。

**停止**: 次のどの終わり方でも、最後にグループ（Job）全体を強制終了し（Linux `kill(-pgid, SIGKILL)`、Windows `TerminateJobObject`）、5 秒以内に先頭の終了とグループの全員（Job の active process）が居なくなったことを確かめてから戻る。確かめられなければ `PLUGIN_COMMAND_STOP_FAILED`（終了コード 7。context に `plugin`・`command`・Linux は `processGroup`）。

| 終わり方 | 戻り値 |
| --- | --- |
| 先頭が通常に終了し、キャンセルが要求されていない | 先頭の終了コード（Linux はシグナルで終われば 128＋番号）。残った子孫は止める |
| 期限（`timeoutSeconds` か `commandTimeoutSeconds`）を過ぎた | `PLUGIN_COMMAND_TIMEOUT`（終了コード 8。context に `timeoutSeconds`） |
| 呼出元のキャンセル（Ctrl+C・SIGTERM・SIGHUP・SIGQUIT） | `PLUGIN_COMMAND_CANCELLED`（終了コード 7） |

キャンセルの要求を一度でも受けたら、先頭が 0 で終わっていても `PLUGIN_COMMAND_CANCELLED` にし、成功を返さない（Windows の Ctrl+C は子にも届き、子が自分で 0 で終わることがあるため）。

**シグナル**: `PluginCommandDispatch.RunAsync` は実行中だけ `PosixSignalRegistration` で SIGINT・SIGTERM・SIGHUP・SIGQUIT を受け、既定の終了を止めて（`Cancel = true`）キャンセルに変える。Linux の子は別グループなので端末の Ctrl+C は本体だけに届き、本体がグループを止める。Windows は Job の `KILL_ON_JOB_CLOSE` により、本体が強制終了されても子孫が止まる。Linux で本体が SIGKILL されたときの子孫は対象外（1 章）。

止めるときは猶予を置かず強制終了する（Windows の Job に穏やかな停止が無く、F と同じ）。途中の出力ファイルは残り得る。

### 3.6 doctor

`PluginDoctorChecks.RunAsync(string? explicitProject, string startDirectory, string resoloopVersion, IReadOnlyDictionary<string, string?> environment, CancellationToken)` が `IReadOnlyList<DoctorCheck>` を返す。I が既存の doctor の check の後ろに足す。明示的な doctor の実行のときだけ呼ぶ。導入・修復はしない。

- プロジェクトが見つからない（`explicitProject` が null のとき）、管理領域が無い、導入済みのプラグインが無い: **空の一覧**（プラグイン無しの doctor の出力・`Ready` を変えない）
- `explicitProject` が不正、管理領域の検査の失敗・`PLUGIN_PROJECT_BUSY`: `DoctorCheck("plugins", "fail", true, メッセージ, 提案)` を 1 件
- `registry.List()` の各プラグインのうち問題があるもの: `DoctorCheck("plugin:<名前>", "fail", true, 問題のメッセージ, 提案)`。壊れたプラグインがあると `OpenVerified` が失敗し、全プラグインのコマンドが動かないため必須の失敗にする
- 問題の無いプラグインの各 `tools`: `PluginToolProbe.ProbeAsync` の結果を `DoctorCheck("plugin:<プラグイン>:<ツール>", status, tool.Required, message, suggestion)` にする

| 確認の結果 | status（required） | status（optional） |
| --- | --- | --- |
| 実行ファイルがあり、`versionArgs` が空 | `pass`（message は絶対パス） | `pass` |
| `versionArgs` を付けた実行が 0 で終わった | `pass`（message は絶対パスと最初の空でない行） | `pass` |
| 見つからない・起動できない | `fail` | `warning` |
| 0 以外で終わった・30 秒で終わらない・停止を確かめられない | `fail` | `warning` |

suggestion は manifest の `hint`、無ければ「`<executable>` を導入して PATH に置く」。

`PluginToolProbe` は 3.4 と同じ実行ファイルの解決（PATH の絶対パスの要素だけ、Windows は `.exe` だけ）と 3.5 の閉じ込めを使う。cwd はプロジェクトのルート、stdin は空、stdout・stderr はそれぞれ最大 64 KiB をパイプで読み、版の文字列は stdout（空なら stderr）の最初の空でない行を制御文字を除いて最大 200 文字にする。期限は 1 回 30 秒（Blender の起動を含めて足りる長さ）で、doctor のコマンド全体の期限・キャンセルにも従う。キャンセル（`OperationCanceledException`）はそのまま投げる（既存の doctor と同じ）。プラグインの package のコードは実行しない（`tools[].executable` は区切りの無い名前だけ）ので lease は持たない。

### 3.7 公開 API（I・#102 が使う）

```csharp
// RLoop.Cli
public sealed record PluginInvocation(string? Project, string Command, IReadOnlyList<string> Arguments);

public static class PluginCommandDispatch
{
    public static PluginInvocation? Parse(IReadOnlyList<string> args);
    public static Task<int> RunAsync(PluginInvocation invocation, PluginDispatchContext context, CancellationToken cancellationToken);
}

public sealed record PluginDispatchContext(string ResoloopVersion, string StartDirectory,
    IReadOnlyDictionary<string, string?> Environment, IReadOnlyList<string> HostArgv)
{
    public static PluginDispatchContext Current(string resoloopVersion);   // cwd・プロセスの環境・呼び戻しの argv
}

public static class BuiltinCommandCatalog
{
    public static IReadOnlySet<string> Commands { get; }
    public static bool IsBuiltin(string name);
    public static PluginNameReservations Reservations { get; }
}

public static class PluginDoctorChecks
{
    public static Task<IReadOnlyList<DoctorCheck>> RunAsync(string? explicitProject, string startDirectory,
        string resoloopVersion, IReadOnlyDictionary<string, string?> environment, CancellationToken cancellationToken);
}

// RLoop.Core.Plugins
public sealed record PluginCommandRequest(InstalledPlugin Plugin, PluginCommand Command, string ProjectRoot,
    IReadOnlyList<string> Arguments, IReadOnlyList<string> HostArgv, string HostVersion, TimeSpan Timeout,
    IReadOnlyDictionary<string, string?> BaseEnvironment);

public static class PluginCommandRunner
{
    // Caller must hold the PluginReadLease that produced request.Plugin until this returns.
    public static Task<int> RunAsync(PluginCommandRequest request, CancellationToken cancellationToken);
}

public static class PluginRuntimeEnvironment
{
    public const string Prefix = "RESOLOOP_PLUGIN_";   // 3.4 の各変数名も const で公開する
    public static IReadOnlyList<string> ExpandArguments(InstalledPlugin plugin, PluginCommand command, IReadOnlyList<string> userArguments);
    public static IReadOnlyDictionary<string, string> Create(PluginCommandRequest request);
}

public sealed record PluginToolProbeResult(string Plugin, PluginTool Tool, string Outcome, string? ExecutablePath,
    int? ExitCode, string? Version);   // Outcome: available | missing | failed | timed-out

public static class PluginToolProbe
{
    public static Task<PluginToolProbeResult> ProbeAsync(string plugin, PluginTool tool, string workingDirectory,
        IReadOnlyDictionary<string, string?> environment, TimeSpan timeout, CancellationToken cancellationToken);
}
```

`PluginCommandDispatch.RunAsync` は、子の終了コードを返すか、本体のエラーを `RLoopException` で投げる。I は `Main` の冒頭（`ParsedArguments.Parse` の前）で次のように結線する想定とする（実際の変更は I）。

```csharp
if (PluginCommandDispatch.Parse(args) is { } invocation)
{
    using var output = new OutputWriter(json: false, brief: false);   // --json はプラグインの引数
    try { return await PluginCommandDispatch.RunAsync(invocation, PluginDispatchContext.Current(ProductVersion()), userCancellation.Token); }
    catch (RLoopException ex) { output.Error(ex); return ex.ExitCode; }
}
```

本体のエラーは text の形式で stderr に出る。子の stdout は本体が出力しないので、`--json` の子の出力を本体が包むことは無い。

### 3.8 エラーコード

| コード | 終了コード | いつ |
| --- | --- | --- |
| `INVALID_ARGUMENT` | 2 | `--project` の値が空・重複（候補があるとき） |
| `UNKNOWN_COMMAND` | 2 | プロジェクトの外（`--project` 無し）、またはどのプラグインのコマンドにも無い名前。I は catalog にも `Parse` にも当たらない先頭名にも同じコードを接続前に使う |
| F の `PLUGIN_*` | F のとおり | 明示した `--project` の不正、照合の失敗、`PLUGIN_PROJECT_BUSY`、data のリンク等 |
| `PLUGIN_COMMAND_START_FAILED` | 9 | 実行ファイルが無い・実行できない・`.exe` 以外（Windows）・NUL・未対応の OS・起動の失敗・呼び戻しの argv を決められない |
| `PLUGIN_COMMAND_TIMEOUT` | 8 | 期限切れ（停止を確認済み） |
| `PLUGIN_COMMAND_CANCELLED` | 7 | キャンセル（停止を確認済み） |
| `PLUGIN_COMMAND_STOP_FAILED` | 7 | 子・子孫の停止を 5 秒以内に確かめられない |

子が自分で 2・7・8・9 などで終わった場合は、終了コードだけでは本体のエラーと区別できない。区別は stderr の本体のエラー（`error: PLUGIN_...`）で行う（文書に書く）。

## 4. 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。すべてエージェントの判断で、利用者の承認ではない。委任指示は issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D1 生 argv の分け方**: 選択 = 既存のパーサの前に `Parse` で `--project` と候補だけを読み、残りをそのまま渡す。別案 = `ParsedArguments` を拡張して `--` 以降を通す（`CommandLine.cs` は I の専有で、`--help` 等を本体が先に食う）。理由 = D-4 の生 argv の保持を、既存コマンドの構文を変えずに満たす。停止条件 = なし
- **D2 組み込み名の照合**: 選択 = catalog を唯一の一覧にし、大小文字を区別せず、プラグインより先に照合。別案 = Program.cs の分岐から自動で集める（Program.cs を変えられない）、プラグインを後に照合（接続前に分岐できない）。理由 = 乗っ取りを構造的に防ぎ、漏れは I の未知名の扱いで表に出る。停止条件 = なし
- **D3 プロセスの閉じ込めの置き場所**: 選択 = F と同じ方式（Linux のプロセスグループ、Windows の Job）を `PluginCommandRunner.cs` の internal なクラスとして持つ。別案 = F の `PluginGit` から共通部分を切り出す（F の所有ファイルの変更で親の裁定が要る）、`Process.Kill(entireProcessTree)`（F が親の先行終了後の子孫の停止を保証できないと確認済み）、`setsid` コマンド経由（Windows に無く導入も保証されない）。理由 = 所有範囲の中で、F が確かめた停止の保証を保つ。重複は #105 の上流 PR の前の整理候補として handoff に残す。停止条件 = 所有範囲の外の変更が要ると判明したら止まり、親の調整役の裁定を求める
- **D4 先頭の通常終了の後の子孫**: 選択 = グループ（Job）に残る子孫も止めてから戻る。別案 = 残す（常駐プロセスを許す）。理由 = lease を外した後に package を使い続けるプロセスを残さない。F と Windows の Job の挙動にも揃う。常駐プロセスを起動する用途は対象外にし、文書に書く。停止条件 = なし
- **D5 標準入力**: 選択 = 端末なら空、リダイレクトならそのまま。別案 = 常に引き継ぐ（Linux で端末の読み取りが止まり期限まで待つ）、常に空（パイプでデータを渡せない）、子を端末の前面にする（`tcsetpgrp` の後始末とシグナルの扱いが複雑）。理由 = 待ち続けを防ぎ、非対話の利用とパイプを両立する。OS で挙動を揃える。停止条件 = なし
- **D6 呼び戻しと環境変数の名前**: 選択 = `RESOLOOP_PLUGIN_` 接頭辞の変数、呼び戻しは JSON 配列の `RESOLOOP_PLUGIN_HOST_ARGV`、親の同じ接頭辞の値は除く。別案 = `RESOLOOP_PROJECT` 等の短い名前（既存の設定用の `RESOLOOP_*` と紛れ、将来の設定と衝突し得る）、実行ファイルのパス 1 つだけ（`dotnet resoloop.dll` の起動を表せない）。理由 = 衝突せず、どの起動方法でも正確に呼び戻せる。Python は `json.loads` で読める。停止条件 = なし
- **D7 package を変えないための環境**: 選択 = `PYTHONPYCACHEPREFIX` と `UV_PROJECT_ENVIRONMENT` を data の下に向ける。`UV_FROZEN`・`UV_LOCKED` は設定せず、lock の同梱と `--frozen`/`--locked` の利用を作者の規則にする。別案 = `UV_FROZEN=1`（プラグインが別の uv のプロジェクト・スクリプトを扱うときの挙動まで変え、PEP 723 のスクリプトの扱いを確かめていない）、何も設定しない（D-4 の「Python キャッシュや uv 環境は data/ に向け」に反する）。理由 = D-4 の範囲を満たし、ほかの挙動を変えない。作者が lock を同梱しないと、初回の `uv run` が `package/uv.lock` を書き、次回の照合が `PLUGIN_MODIFIED` で止まる（気付ける）。`UV_PROJECT_ENVIRONMENT` は子孫のすべての uv に効くので、子の cwd（プロジェクトのルート）にある `pyproject.toml`（create-reso-world のワールドにはある）を `--project` 無しの `uv run` が見つけると、その依存をプラグインの `data/.venv` に入れる（ワールドの `.venv` は変えない）。このためプラグインは `uv run --project ${pluginRoot}` で自分のプロジェクトを明示し、ワールドの uv を意図して使うときはその子プロセスの環境から `UV_PROJECT_ENVIRONMENT` を外す規則を #101・#102 に渡す（builder check の指摘）。停止条件 = なし
- **D8 ResoniteLink の URL**: 選択 = 渡さない。別案 = 設定済みの URL を変数で渡す（呼び戻しと同じ設定を二重に持つ。発見はしない）。理由 = 呼び戻しは cwd と環境から同じ設定を解決するので不要。D-4 は「渡す場合も発見・接続しない」で、渡すことを求めていない。停止条件 = なし
- **D9 期限と設定の解決**: 選択 = manifest の `timeoutSeconds`、無ければプロジェクトのルートから解決した `commandTimeoutSeconds`。本体の `--command-timeout` は受け付けない（本体の指定は `--project` だけ）。別案 = cwd から解決する（`--project` で別のプロジェクトを選んだときに食い違う）。理由 = 選んだプロジェクトの設定に揃える。停止条件 = なし
- **D10 本体のエラーの形式**: 選択 = プラグインの呼び出しでは本体のエラーを text で stderr に出す。別案 = 引数に `--json` があれば JSON（プラグインの引数を本体が解釈することになる）。理由 = D-4 の「プラグイン名より後は解釈しない」。停止条件 = なし
- **D11 Windows の実行ファイル**: 選択 = `.exe` だけ。`.cmd`・`.bat` は起動しない。別案 = PATHEXT に従う（`cmd.exe` の解釈が入り、引数の値がシェルとして解釈され得る）。理由 = D-4 の「シェルを通さない」。必要なら作者が `cmd.exe` を明示して引数を自分で引用する。停止条件 = なし
- **D12 PATH の相対の要素**: 選択 = 使わない。別案 = 本体の cwd で解決する（F の Git の方式）。理由 = 子の cwd はプロジェクトのルートで、プロジェクトや cwd の中の同名のプログラムを実行しない。停止条件 = なし
- **D13 doctor の範囲**: 選択 = プラグインが無ければ何も足さない。壊れたプラグイン・管理領域の失敗は必須の失敗。ツールは required なら fail、optional なら warning。1 回 30 秒。別案 = プラグインの節を常に出す（プラグイン無しの出力が変わる）。理由 = D-4 の「プラグイン無しの結果・必須判定は維持」と「不足を成功と報告しない」。doctor の終了コードは既存どおり 0 で、`Ready` が false になる。停止条件 = なし
- **D14 プロジェクトの外の未知名**: 選択 = `--project` が無くプロジェクトが無ければ `UNKNOWN_COMMAND`。別案 = `PLUGIN_PROJECT_NOT_FOUND`。理由 = 打ち間違いを従来どおりの未知のコマンドとして示す。提案に `--project` を書く。停止条件 = なし
- **D15 テストの偽プログラム**: 選択 = `tests/fixtures/plugins/commands/command-probe` の C# プロジェクトをテストのクラスごとに 1 回ビルドし、`dotnet` で起動する。別案 = `/bin/sh` のスクリプト（公開 CI の Windows で動かない）、PowerShell（空文字の引数の扱いが版で違う）。理由 = Linux と Windows で同じテストが実際の引数の引用を通り、F の前例と同じ方式。停止条件 = なし
- **D16 実行の担当と方式**: 選択 = `self`（雛形の既定）で、Plan の Task を自分で実装する。理由は Plan に書く。停止条件 = なし

## 5. 受け入れ基準

### 動作環境

Linux（この Dev Container、`global.json` の .NET 10.0.201）で build と全テストを実行する。Windows は公開 CI（`windows-latest`）の unit test で同じテストを実行し、PR の checks で結果を確かめる。Windows の実機での手動確認はしない。Resonite・Blender・認証情報は使わない。

### 実入力

- プロジェクトのパス `作業 ワールド`（空白と日本語）、導入元のディレクトリも空白と日本語を含む
- 利用者の引数: `""`、`日本語 引数`、`a<改行>b`、`--help`、`--version`、`--json`、`--`、`;`、`$(echo injected)`、`"quoted" \back\`
- manifest の args: `${pluginRoot}` と `${pluginData}` を含む
- 親の環境に古い `RESOLOOP_PLUGIN_PROJECT_ROOT`（別の場所）がある

### 防御範囲（S のテスト。代表 1 件ずつ、拒否には通る例を残す）

| 守り | テスト | 通る例 |
| --- | --- | --- |
| 生 argv の変形・シェル解釈、cwd・プロジェクト・data の取り違え、子の失敗の終了コードを成功にする | `RawArgumentsReachTheChildUnchanged`: 実入力の argv・cwd・`RESOLOOP_PLUGIN_*` を子が記録し、本体が子の終了コード 3 を返す | 同じテストが通る例 |
| 組み込みの乗っ取り | `BuiltinNamesNeverReachPlugins`: `import`・`IMPORT` を宣言したプラグイン（旧版で導入された想定）があっても、`Parse` は組み込みとして `null` を返し、プラグインのプログラムは動かない | 同じプロジェクトの別名のコマンドは `Parse` がプラグインの呼び出しとして返す |
| 期限切れを成功にする、子孫が残る | `TimedOutCommandsFailAndStopTheirProcessTree`（runner）: 子が孫を起動して止まらない。期限 5 秒で `PLUGIN_COMMAND_TIMEOUT`、子・孫とも動いていない | 先頭の通常終了の戻り値（下の行） |
| キャンセルを成功にする、実行中に package が消される | `CommandsHoldTheLeaseAndCancellationNeverSucceeds`（dispatch）: 実行中の remove は `PLUGIN_PROJECT_BUSY`、キャンセルで `PLUGIN_COMMAND_CANCELLED`、子・孫とも動いていない | 終わった後の remove の成功 |
| 先頭の終了後に子孫が残る | `NormalExitStopsLeftoverDescendants`: 子が孫を残して 7 で終わる。本体は 7 を返し、孫は動いていない | 戻り値 7 |
| cwd・プロジェクトの中の同名のプログラム、Windows の `.cmd` を実行する | `ProgramsResolveOnlyFromAbsolutePathOrThePackage`: PATH の相対の要素にあるプログラム（Linux）、`.cmd`（Windows）は `PLUGIN_COMMAND_START_FAILED` で、目印のファイルが作られない | `dotnet`（絶対パスの PATH）は起動する |
| required のツールの不足・失敗を準備完了にする | `RequiredToolProblemsAreNeverPassing`: 無い required は `fail`、0 以外で終わる required は `fail`、無い optional は `warning` | `dotnet --version` の required は `pass` |

### テストにしない項目（L・F・D）と代わりの検証

- Ctrl+C・SIGTERM からキャンセルへの変換（`PosixSignalRegistration`）は、I の結線後に実際のシグナルで確かめる（テストの host にシグナルを送らない）
- `PYTHONPYCACHEPREFIX`・`UV_PROJECT_ENVIRONMENT` の値（壊れると次回の照合が `PLUGIN_MODIFIED` で止まる。L）。一時の確認で値を見る
- 未知名の `UNKNOWN_COMMAND`、`--project` の誤り、doctor のプラグイン無しの空の一覧（エラー・出力の変化として気付ける。L）。一時の確認で見る
- catalog の名前の一覧そのもの（F）。漏れは I の結線で気付ける（3.2）
- ツールの確認の期限切れ（実行の期限切れと同じ閉じ込め。D）
- 検証の入口: worktree で `dotnet build ResoLoop.slnx --nologo` と `dotnet test ResoLoop.slnx --no-build --nologo`、PR の公開 CI（Windows）

## 6. 既知の制限

- 端末の対話は使えない（stdin は端末なら空）。Linux で子が端末の設定を変えようとすると止まることがあり、期限で終わる
- 常駐プロセスは残せない（D4）。プロセスグループを自分で抜けた子孫（Linux の `setsid` 等）は止められない
- Linux で本体が SIGKILL されると子孫が残る（Windows は Job で止まる）
- 停止は強制終了で、途中の出力が残り得る
- 子の終了コードと本体のエラーの終了コードは重なり得る（3.8）
- 同じプロジェクトのプラグインのコマンドは同時に 1 つだけ（F の lease が排他）。プラグインから本体の doctor・init・skills sync・プラグインのレシピ・別のプラグインのコマンドを呼び戻すと `PLUGIN_PROJECT_BUSY` になる。プラグインを使わない組み込み（`blender`・`validate`・`apply` で組み込みのレシピだけを使う場合など）は呼び戻せる
- `PluginGit` と同じ閉じ込めのコードが 2 か所にある（D3）

## 7. builder check

2026-10-30 に新しいサブエージェント（general-purpose）が Spec と対象のコードを読み、計画の前に要る問いを 3 つ返した。どれも利用者の判断を要さず、エージェントの判断で Spec に反映した。

| 問い | 区分 | 反映 |
| --- | --- | --- |
| 呼び戻しの argv を決められないのはどんなときか | 自分で決められる | 3.4 の `RESOLOOP_PLUGIN_HOST_ARGV` の行に `Current` の規則を書いた。テストは `PluginDispatchContext` で明示の値を渡す |
| `UV_PROJECT_ENVIRONMENT` が子孫のすべての uv に効くのは意図どおりか | 承認済みの D-4 で決まっている | D7 に影響と、`uv run --project ${pluginRoot}` の規則を足し、#101・#102 に渡す |
| Windows の `.exe` の規則を `./` にも適用するか | 自分で決められる | 3.4 に、`./` は書かれたとおりで `.exe` を求め、裸の名前だけ補うと書いた |

## 8. 引き渡し

- **I #298**: 3.7 の結線、`Parse` が `null` で先頭の位置引数が catalog に無いときの接続前の `UNKNOWN_COMMAND`、install・list・remove・#99 の init・sync に `BuiltinCommandCatalog.Reservations` を渡す、doctor の check の後ろに `PluginDoctorChecks.RunAsync` の結果を足す（`--project` の受け方は I が決める）、help への一覧（任意）
- **#102**: 3.4 の環境変数と argv、3.5 の終わり方とエラーコード、6 章の制限。呼び戻しは `RESOLOOP_PLUGIN_HOST_ARGV` の後ろに引数を足す。uv は `uv run --project ${pluginRoot}` で自分のプロジェクトを明示し、lock を同梱して `--frozen` か `--locked`。両 OS で動かすなら `./` の実行ファイルではなく PATH の `uv` と `${pluginRoot}` で書く
- **#101**: 3 章と 6 章を利用者・作者向けの文書にする。Windows の `.exe` だけ（`./` は書かれたとおり）、PATH の絶対パスだけ、OS をまたぐ書き方、`uv run --project ${pluginRoot}`、stdin、常駐プロセス、終了コードの重なり
- **#105**: 閉じ込めのコードの共通化（D3）を上流 PR の前の整理候補にする
- **#99**: `reservations` には `BuiltinCommandCatalog.Reservations` を渡す（コマンド・同梱スキル・組み込みレシピを含む。#99 が同梱スキルを重ねて足しても同じ集合）
