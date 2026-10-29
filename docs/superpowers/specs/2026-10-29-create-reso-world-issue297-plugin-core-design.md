# Issue #297: ResoLoop 0.2.0 の安全なプラグイン基盤

## 管理・許可

- 状態: **approved**。文書管理: `usaturn/create-reso-world`。コード対象: `usaturn/resoloop`。
- Issue: https://github.com/usaturn/create-reso-world/issues/297 （親 #95、`resoloop-plugins-board` / `plugin-core-refresh`）。
- 実行許可: 利用者の「では #297 の Spec 作成、Plan 作成して、実装し PR を出して」、続く「旧仕様を一部参考しても良いですが、徹底してより良い案を検討して、実装してください。必要であれば、0から実装し直してください。負担が増えても構いません。また、途中で止めずに推奨案で実装まで進めてください。」。通常の判断・再実装を委任されている。内容承認を推測しない。指定された Plannotator の Spec/Plan レビューは実施する。
- 今回は通常の Superpowers を使う。main 限定の `issue-to-pr` と自動マージループは使わない。前の `--merge` run は停止済みであり、今回の終点は PR 作成。マージ・上流投稿の許可はない。
- 親の承認済み D-1〜D-6: [親設計](2026-10-29-create-reso-world-issue95-plugin-replan-design.md)（内容承認 `d009286968a21c916bafb39b2308ebaa09d40c4c`）。本書は独立した新子 #297 の詳細設計であり、完了した旧 #97 の文書を書き換えない。
- 旧 [#97 の manifest 仕様](2026-10-16-create-reso-world-issue97-resoloop-plugin-core-design.md) は D-1 の公開形式の参照元。古いコード・Plan の安全処理は実装の基準にしない。
- コード基準: `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`（上流 0.2.0、`feat/plugin-v2`）。fork main は使わない。
- `PARENT_ROOT`: `/workspaces/reso-world`。
- `DOC_ROOT`: `/workspaces/reso-world/.worktrees/issue-297-plugin-core`、`docs/issue-297-plugin-core`。
- コード worktree: `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-297-plugin-core`、`feat/create-reso-world-issue-297-plugin-core`。
- 先行なし。最新 #297 は OPEN、コメント・blocked_by・両リポジトリの PR 全ページ・予約を確認し、同じ作業なし。予約情報は親 checkout の `tmp/agents/issue-297.beqzdh2p/claim.json` と子 Issue の開始コメントに保存。

### 内容確認と再開（2026-10-29 08:43 UTC）

利用者へ受け入れ基準・動作環境・防御範囲・対象外とSpec内容commit `5353ba718fc19b678f6a32fa4354030e8c27f02c`、Plan内容commit `5797dff20f219a7edf5145b55026ef24c3963c2d` を提示して承認を確認し、「ノンストップでPRまで作成してください。」との応答を得た。この応答を提示内容の確認および実装・PR作成の実行許可として記録する。現行文書 `3e16ad4413ea6053a7b74acc7f086ea06b1e36b5` までの差分は確認待ち記録だけで、設計内容は不変。マージ・上流投稿・fork main更新は許可に含めない。

## 1. 目的・非目的

プロジェクト単位のパッケージを安全にコピー導入し、利用直前に全内容を照合し、安全に取り除く Core API を用意する。後続 #98〜#100 と #298 が同じ API を使う。導入時にはプラグインのプログラム・依存管理・Git checkout hook/filter を実行しない。

範囲は Issue が所有する次のファイルのみ。

- `src/RLoop.Core/Plugins/{SemanticVersion,PluginNames,PluginErrors,PluginManifest,PluginInstallRecord,PluginRegistry,PluginInstaller,PluginGit,PluginPathPolicy,PluginProjectLock}.cs`
- `tests/RLoop.Tests/{PluginManifestTests,PluginRegistryTests,PluginInstallerTests}.cs`
- `tests/fixtures/plugins/core/`

`Program.cs`・`CommandLine.cs`・他の子の所有ファイル・旧 fork 専用機能・既存プロジェクトは変更しない。install/list/remove の CLI 結線は #298。作者向け文書は #101。本書は後続向け API 定義である。4機能を縮小しない。

署名・サンドボックス・悪意ある同一ユーザによる差し替えへの完全防御、ネットワーク接続先の信頼判定、自動更新・既存導入の移行は対象外。ハッシュは意図しない変更の検知である。プロセス強制終了時の staging 自動回収や永続ストレージへの fsync 保証は含めない。

## 2. 比較と決定

| 論点 | 採用案 / 理由 | 別案 / 不採用理由 |
| --- | --- | --- |
| 実装方式 | 公開 manifest の意味だけ維持し、パス・記録・Git・registry・排他・installer を責務ごとに新規実装。旧コードからの再利用は個別に妥当性を確認する | 旧コミット丸ごと移植は既知のリンク・Git・競合欠陥と古い結線を持ち込む。互換仕様も捨てた完全再設計は後続と親承認を変える |
| 導入の確定 | 同一プロジェクトの OS 解放ロックを取得し、staging でコピー・検証・記録してからディレクトリを一度だけ移す | 既存先へコピーして後から巻き戻す方式は失敗時に既存状態を壊す |
| Git URL の展開 | checkout せず、bare clone の確定コミットの tree と blob を読み出す | checkout はユーザ設定の filter/hook を動かし得る。archive の外部展開は新しい依存と展開経路の検証を増やす |
| Git 内の非ルート入力 | 明示的に拒否する（`PLUGIN_SOURCE_INVALID`）。Git ルートか Git 外のパッケージディレクトリを要求 | 全コピーへのフォールバックは ignored な機密を混入する。サブディレクトリ対応は境界・submodule・ignore の別仕様を増やすため今回は足さない |
| 予約名 | 呼出元が渡す不変スナップショット。Core に CLI 一覧を複製しない | 旧固定一覧では 0.2.0 の `bundle`・`import` 等を取り漏らす。catalog は #98 の所有 |
| レシピ衝突 | D-6 の実効名 `<plugin>:<recipe>` で区別する。異なるプラグインの同じローカル名は許す | 裸名の全体一意性は D-6 の名前空間と実入力に反する。同一 manifest の重複や予約名は拒否 |
| ロック競合 | 待ち続けず `PLUGIN_PROJECT_BUSY` を返す。ロックファイルを削除しない | 時刻による stale 判定・削除は実行中の別プロセスと競合する |

以上は利用者による推奨案の委任の範囲。親の4機能・安全境界・所有範囲を変える必要があれば停止して調整する。

## 3. データと公開 API

namespace は `RLoop.Core.Plugins`。依存は Core の既存 `RLoopException` と .NET 標準ライブラリのみ。新しい NuGet 依存は不要。

### manifest v1

`resoloop-plugin.json`: UTF-8 JSON、最大256 KiB。未知プロパティ・重複プロパティ・不正型を拒否。エラーは JSON path を持ち `context.errors` にまとめる。各オブジェクト内の重複を検出し、辞書プロパティも silent last-wins にしない。

- 必須: `schemaVersion:1`, `name`, `version`, `resoloop.minVersion`。`resoloop.maxVersionExclusive` は任意、min より大きい。
- 任意 `description` は存在するなら1〜500文字。
- `commands`（最大50）: 必須 name/description/program。任意 args（文字列配列、既定空）、timeoutSeconds（1〜86400）。program は `./<package-relative-path>` または区切りなしの `[A-Za-z0-9._+-]+`。args 内の `${...}` は `${pluginRoot}` と `${pluginData}` だけ。
- `skills`（最大50）: 必須 name/path。path はディレクトリで直下の `SKILL.md` が対象ファイルに含まれる。
- `recipes`（最大50）: 必須 name/path/prototype/purpose/parameters。prototype は1〜100文字、purpose は1〜500文字。parameters は string→string で key 必須。ports は任意の string→string、requirements は任意の文字列配列。path の JSON の `prototypes.<prototype>` がオブジェクト。
- `tools`（最大20）: 必須 name/executable（区切りなしコマンド名）。任意 versionArgs（文字列配列）、required（既定true）、hint（1〜500文字）。
- 名前は `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`、2〜40文字。連続ハイフン不可、各コレクション内で重複不可。
- SemVer 2.0 を使う。prerelease の数値比較で桁数に依存したオーバーフローを起こさず、build metadata は順序に影響しない。対応版は constructor で明示、0.2.0 を除外した旧例をコピーしない。
- `path` は `/` 区切り相対名。空要素・`.`・`..`・絶対パス・`\\`・colon・NUL・Windows の予約名/末尾dot/末尾space等、移植時に別名になる名前を拒否する。空白・日本語・通常の hidden file は許す。

`PluginManifest.Read(string packageDirectory)` は以上と参照先実在・リンク拒否を検証して型付きの読み取り専用結果を返す。`EnsureCompatible(string resoloopVersion)` で互換性を確認。`SemanticVersion.Parse` / `CompareTo` を分離する。manifest の型は後続が Commands/Skills/Recipes/Tools の宣言を利用できる public record とする。

### 予約名と照合済み結果

`PluginNameReservations`（PluginNames.cs 内）は constructor で `commands`, `skills`, `recipes` の enumerable を受け、序数・大小文字を区別しない set のスナップショットにする。呼出元からの後の変更で判定が変わらない。空集合はテストで明示できるが registry/installer の引数は省略不可。CLI の catalog は #98、結線時に実際の同梱スキル・レシピと合わせて #298 が渡す。

`PluginNames.FindConflicts(manifest, installedManifests, reservations)` は plugin 名の重複、予約コマンド/同梱スキルと plugin 名の衝突、commands/skills の同種他プラグインとの衝突、予約レシピ名、`resonite-` skill 接頭辞を検査する。レシピの他プラグイン間比較は名前空間込み。名前規則の小文字制約に加え、ファイル上の case collision も拒否。

```csharp
public sealed class PluginRegistry
{
    public PluginRegistry(string projectRoot, string resoloopVersion,
        PluginNameReservations reservations);
    public static string FindProjectRoot(string? explicitProject, string startDirectory);
    public string ProjectRoot { get; }
    public string PluginsDirectory { get; }
    public string ResoloopVersion { get; }
    public IReadOnlyList<PluginStatus> List();
    public IReadOnlyList<InstalledPlugin> LoadAll();
    public InstalledPlugin Load(string name);
    public PluginReadLease OpenVerified();
}
public sealed class PluginReadLease : IDisposable
{
    public IReadOnlyList<InstalledPlugin> Plugins { get; }
    public void Dispose();
}
public sealed record PluginProblem(string Code, string Message,
    IReadOnlyDictionary<string, object?> Details, IReadOnlyList<string> Suggestions);
public sealed record PluginStatus(string Name, string InstallDirectory,
    PluginInstallRecord? Record, PluginManifest? Manifest, PluginProblem? Problem);
public sealed record InstalledPlugin(string Name, string InstallDirectory,
    string PackageDirectory, string DataDirectory,
    PluginManifest Manifest, PluginInstallRecord Record);
```

PluginStatus は `Ok => Problem is null`。List は診断用。Load/LoadAll はその時点で照合したスナップショットであり、戻り値のパスを後から使用する期間の保証ではない。Load(name) も全体の名前衝突を回避せず検出する。

後続 #98〜#100 は `using var lease = registry.OpenVerified()` の Plugins を使い、実行・配布・レシピの読み取り完了まで lease を保持する。OpenVerified はロック下で全件照合し、そのロックを返す lease へ移譲する。失敗時は必ず解放する。通常の別プロセスによる remove/install は利用中にも BUSY となる。呼出側は同じ lease 内で再入する List/Load/Install/Remove を呼ばない。実行するプラグインが同じプロジェクトのプラグイン管理を呼び戻す場合も BUSY とする。空で管理領域が未作成の場合の lease は空スナップショットで、存在しないパッケージの将来利用を許可しない。非協調的な同一ユーザの書き換えへの完全防御は依然として対象外。

### install.json

v1 の `schemaVersion/name/version/source/commit/installedAt/resoloopVersion/files` を保つ。source は kind (`directory`/`git`), location, ref。directory の location は実パス、ref/commit は null。git は sanitized location、明示 ref と実 commit（Git の完全な40または64桁 object ID）。時刻は UTC。files は順序付き相対パス→小文字SHA-256の読み取り専用辞書。

未知欄・重複欄・名前や版の不一致・ファイル名不正・case/prefix衝突・不正hashを読む前に拒否する。ファイル数10000、合計200 MiBを上限とし、記録自体も8 MiBで上限を設ける。パス検証前に記録のキーを filesystem path に結合しない。manifest は files に必須。install.json の name/version は再検証した manifest と一致させる。

### installer

```csharp
public sealed class PluginInstaller
{
    public PluginInstaller(PluginRegistry registry);
    public InstalledPlugin Install(string source, string? gitRef = null);
    public void Remove(string name, bool confirmed);
}
```

同期 API とし、すべての失敗は意味のある RLoopException。Remove の confirmed=false は既存の `CONFIRMATION_REQUIRED`。Install の入力は既存ローカルディレクトリか、http/https/ssh/git/file URL または scp形式。ローカル＋ref は拒否、Git URL はref必須。URL中のpassword・HTTP userinfo・query・fragmentは拒否し記録しない。SSHの公開ログイン名は許し、保存locationからuserinfoを除く（接続に使う値とは分ける）。refは安全な引数として渡し、optionと誤認する先頭 `-`、制御文字・`..`等を拒否。失敗のstderrやURLをそのまま例外contextへ転載しない。

## 4. 安全なパス・Git・ロック

### パス

PluginPathPolicy に相対名検証・実パス化・リンクを辿らない列挙・検証済みrootへの結合・安全な削除を集約する。source の入口は親を含む symlink alias を実パスへ解決してよいが、その配下のリンクをコピーしない。Git top level も同じ方式で実パスにして比較する。

project の探索は既存 `.resoloop.json` を要求し、無ければ作らない。project 配下 `.resoloop`、plugins、plugin、package、install.json、lock、ignore 等にリンクがあれば読み書き前に拒否。source/project が重なる場合、コピー中に自分の staging が入り込まないよう拒否。filesystem の mount はリンクと同一視しない。

symlink/junction は `LinkTarget` を含む .NET の実ファイル情報で検出し、dangling link も見落とさない。ReparsePoint 一律拒否によって非リンクのクラウドファイルを誤拒否しない。子リンクを辿らず、削除時はリンク自体だけを外せる。指定 plugin 根・package 根・管理親のリンクは削除自体を拒否する。通常ファイル以外の特殊ファイルはコピー対象にしない。

### Git

Git は `ProcessStartInfo.ArgumentList` / `UseShellExecute=false` で引数列・子環境を構成し、stdout/stderrを並行回収して実行する。実.NET10 APIでは親の先行終了後に `Process.Kill(entireProcessTree)` だけで子孫停止を保証できなかったため、承認済みPlanのAPI前提差分へのcontingencyに従い、同じ引数列・環境を消費するprivate native launch境界（Linux process group / Windows Job Object）で既存の停止要件を維持する。追加ランチャー/NuGet依存・public API・安全範囲の変更はない。全子呼出しで GIT_DIR/WORK_TREE/INDEX_FILE/OBJECT_DIRECTORY/ALTERNATE_OBJECT_DIRECTORIES/CONFIG_COUNT/CONFIG_PARAMETERS等の repository・config 注入を除去する。原則 GIT_* を除き、認証/transportに必要な `GIT_SSH`, `GIT_SSH_COMMAND`, `GIT_ASKPASS`, `GIT_SSL_CAINFO`, `GIT_SSL_CAPATH`, `GIT_PROXY_COMMAND` のみ明示的に保持。HOMEを差し替えず、通常のglobal/system credential helperは維持。promptは無効。core.fsmonitor=false、core.hooksPathを空ディレクトリ、外部protocol helperのextは無効。ローカルのshell/global設定を変更しない。

Git判定に失敗したら全コピーしない。Gitなし/破損した.git/アクセス失敗等と、Git外のディレクトリを区別する。祖先の.git markerとGitの応答を併用し、Git管理が疑われるのに確認できない入力は拒否。bare sourceはローカルディレクトリ導入では拒否する。

作業ツリールート: `ls-files -z --cached --others --exclude-standard` の一覧（未コミットの内容も含む）を使う。ignoreされた未追跡ファイルはコピーしない。Git外は通常ファイルを列挙するが、子階層で `.git`（ファイル/ディレクトリ/リンク）を見つけた場合は nested repository としてパッケージ全体を拒否する。`.git`だけを除いて内包repositoryのignoredファイルをコピーしてはならない。Git root経由の一覧でもsubmodule/入れ子repositoryのディレクトリ項目は拒否する。非ルートは拒否。

Git URL: private staging内へbare clone、refをcommitとして解決（短いbranch名は対応するremote/heads refも確認）、`ls-tree -r -z` で regular blob のみを対象にする。symlink/submoduleは拒否。`cat-file` でblobをファイルへstreamし、200 MiB/10000件を超えて書かない。mode 100755はUnixで実行bitを保つ。checkout・filter・hook・依存取得を行わない。Git subprocess は1呼出し120秒を上限とし、期限には子孫停止と終了待ちを行い、成功としない。stderrやcredential情報を記録に残さない。

### 排他と確定

PluginProjectLock は `plugins/.lock` を FileMode.OpenOrCreate / FileAccess.ReadWrite / FileShare.None で取得。親が安全であることを先に確認し、ロックは同一プロジェクトの install/remove の全操作を覆う。プロセス終了で解放。`.lock`は削除しない。List/Loadも既存管理領域がある場合に同じロックを取り、中途状態を読まない（存在しない領域は作らず空）。内部のlock-held処理を分け、再入ロックしない。OpenVerified は同じロックを利用側の Dispose まで維持する。

`plugins/.gitignore` は `*\n` の完全一致内容をinstallerが新規作成する（.gitignore自身も含め全内容をignore）。異なる既存内容・リンクは上書きしない。既存 `.resoloop/.gitignore` は不変。

install順序: source検査 → 管理親の安全性 → lock → ignore確認 → 既存全件の照合/衝突検査 → 一意staging作成 → コピー/サイズ制限 → staged manifest検証/予約名/互換性 → staged packageのhash/record → staged全体の再照合 → 既存先が無いことを確認 → Directory.Moveによる確定。manifest名はstagingコピー後の検証値を採用し、コピー元が変わった場合の古い名前を使わない。全作業中ロックを保持する。

失敗時は既存plugin・recordを変更せず、自分のstagingだけを安全に消す。最初に作った管理親/ignore/lockは残してよい。別プロセスや以前のstagingを勝手に掃除しない。成功後の追加の失敗可能処理を避け、確定前に結果を組み立てる。

## 5. 照合・削除・エラー

照合はrecordを厳格に読んでから、package全体をリンクを辿らず列挙し、集合一致・全hash・manifest・版・予約名を確認する。recordで指されたファイルだけを読む実装にはしない。変更/欠落/追加/リンクは `PLUGIN_MODIFIED`。package根リンクの#112も同コード。record異常は `PLUGIN_RECORD_INVALID`。dataは照合しない。

Listはpluginごとの問題を返し、壊れたものを消せるようにする。管理親が危険な場合やロック競合は全体の例外にする。内部の `.lock` / `.gitignore` / `.staging-*` はplugin扱いしない。不正な公開ディレクトリ名やcase衝突は問題として見せる。LoadAllは問題や衝突をまとめて拒否。Loadも検証を省略しない。

removeは名前/confirmedを先に検証し、同じlock内で管理親とplugin根・package根を検証、指定pluginのみを子リンクを辿らず削除する。record破損は削除の妨げにしない。dataを含め削除するが配布済みスキル・外の成果物・他pluginには触れない。

既存 `PLUGIN_PROJECT_NOT_FOUND/SOURCE_NOT_FOUND/SOURCE_INVALID/GIT_REF_REQUIRED/GIT_REF_NOT_FOUND/GIT_FAILED/MANIFEST_NOT_FOUND/MANIFEST_INVALID/SCHEMA_UNSUPPORTED/INCOMPATIBLE_VERSION/NAME_CONFLICT/ALREADY_INSTALLED/NOT_INSTALLED/NAME_INVALID/RECORD_INVALID/MODIFIED/REMOVE_REFUSED` を PluginErrors で既存 ExitCodes に対応させる。追加は `PLUGIN_PROJECT_BUSY`（OperationFailed）、`PLUGIN_PATH_UNSAFE`（ValidationFailed）、`PLUGIN_IGNORE_CONFLICT`（ValidationFailed）。IOの失敗も適切な処理境界で包むが、失敗を空一覧/成功にしない。

## 6. 受け入れ基準

この本文を実装・レビュー依頼の両方へ渡す。

- 動作環境: Linux Dev Container、global.jsonの.NET 10.0.201系、xUnit。一時ディレクトリと一時Git repositoryのみで検証する。Windowsも設計対象だがWindows未実行を成功としない。Resonite/Blender/実認証/グローバル導入は不要。
- 実入力: `作業 ワールド` のパス、通常パッケージ、追跡ファイル＋未追跡許可ファイル＋ignoredな偽機密、入口symlink経由のGitルート、Git内サブディレクトリ、file://URL＋ref、差し替えたpackage/親リンク、`../outside`等のrecordキー、case/prefix衝突、破損record、二つのプロセスによる同一project操作、保持したread lease中の削除拒否と解放後の成功、Git外パッケージ内のnested repository。
- 防御範囲: Git環境で別repositoryを選ばない、ignored/資格情報をコピー/保存しない、管理領域と外部リンク先を操作しない、全package差分を検出、衝突や失敗を成功にしない、失敗後に既存導入物を保持、同一projectの操作を排他。各拒否の守りには少なくとも一つ正しく通る例を含める。悪意ある同一ユーザ、署名/サンドボックス、CLI結線、Windows実機確認はこの検証の外。

テストはS（気付けない損害）だけ。#110（alias経由Gitのignore）、#111（管理親linkからの削除）、#112（package根linkの受入れ）を各責務の代表例で再現・防御する。固定一覧/文言や単なる構文エラーのF/Lテストは追加しない。同じ守りを多数の入力・層で重複させない。manifest互換範囲の誤判定、record範囲外読取、衝突、秘密混入、既存データ喪失、lockの解放・競合はSとして実行テストを置く。

### 独立設計確認

初回 builder check の2論点を採用した。通常の協調プロセス間の照合後差し替えは悪意ある同一ユーザの除外範囲に入れず、OpenVerifiedの利用leaseを定義。Git外パッケージに内包されたrepositoryは拒否し、ignoredファイルの全コピーを防ぐ。いずれも公開APIと防御範囲の詳細化であり、4機能や所有範囲は変更しない。基準コードの `dotnet test ResoLoop.slnx --nologo` は終了0（実装前）。

## 7. 公開・引き渡し

コードはGitleaks検査したSHAをfork feature branchへpushし、base `feat/plugin-v2` のfork内PRを1件作る。base branchはまだremoteにないため、既に上流公開済みの基準SHAを同名branchへ新規公開する。既存branchが出現したら同一SHAを確認し、違えば止まる。fork/mainの更新・force push・マージはしない。

文書はcreate-reso-worldのmain宛て文書専用PRにする。互いのPRとIssueをRefsで参照し、Issueは閉じない。publicのコードPRのCIを確認する。子のSpec/API/Plan/handoff pairを遠隔の内容から復元しhashを照合して成果を公開し、自分の予約をexpected-SHA leaseで解放する。親の台帳は調整役に任せる。#110〜#112を実装前に閉じず、今回も取り込み待ちとして証拠のみ示す。

## 8. 実装結果（2026-10-29 UTC）

実装とレビューは完了。コードPR [usaturn/resoloop#26](https://github.com/usaturn/resoloop/pull/26)（base `feat/plugin-v2`、HEAD `e3a4df87a7afce735cee412a22efb73200904f20`）、文書PR [create-reso-world#299](https://github.com/usaturn/create-reso-world/pull/299)。取り込み・マージ・上流投稿は未実施。公開CI/復元/予約解放の最終記録は同じPlanとIssue #297を参照する。

調整役の最終Linux検証はbuild exit0（警告0/エラー0）、Plugin43件、全体573 unit＋22 offline integration-assembly件成功、失敗/skipなし。Gitleaksはコード8commit検査・検出なしで、その検査SHAだけをpushした。Task1〜4のspec/quality review、最終全branch review、最終修正の限定reviewに未解決指摘なし。固定一覧/文言/source-stringテスト追加なし。

最終APIは本書第3章どおり。実利用はOpenVerified leaseを保持し、同じlease中に管理APIへ再入しない。Task4のdeterministic staged-identity検証用internal constructorだけをprivate実装補助として追加し、public APIは増やしていない。Task3のnative spawnは同じshell-less引数/環境と120秒停止要件を満たすための実API前提修正で、承認SHAを変更/捏造しない。

### 公開Windows CIで判明した削除の追加修正

初回公開CI `40873464005` はBuild成功、unit566成功/7失敗、offline22成功。Gitのread-only object/packを削除できず、productionのclone清掃とfixture teardownで失敗した。新しい実環境の証拠として既存Task1/4の範囲だけを再開し、`e3a4df8` で所有ツリーの非linkエントリだけReadOnlyを解除して削除、子link先の属性/bytesを変更しないことを既存Sテストで実行確認した。公開API/所有範囲の変更なし。これは最終review指摘の2回目の修正waveではない。

追加修正のtask reviewはspec/quality承認、未解決指摘なし。調整役が最終e3a4df8でRelease build（警告/エラー0）とRelease full suite（573+22、失敗/skip0）を再実行。ログはSESSION/controller-final-build.log、controller-final-tests.log。公開Windows再実行 `40875568882` はBuild成功、unit572成功/1失敗、offline22成功。Plugin失敗はなくなったが、所有外の既存CheckpointFiles同時読取テストがsharing IOExceptionで失敗したため、全CIは未成功。所有外の推測修正や成功扱いはせず、Plan/Issueに残す。

裁定の追加: (11) 新しい公開CI失敗を既存の削除/fixture所有範囲で修正することを許可。誤った場合の負担は追加の検証/CI時間で、範囲・削除境界・未確認状態の報告は縮小しない。(12) 次のCIで判明した所有外CheckpointFiles失敗は変更せず未達として引き渡す。誤った場合の負担は全CI成功が別途確認まで保留になること。

### 条件と実行証拠

| 条件 | 実行した代表証拠 |
| --- | --- |
| #110 alias/ignore、Git外nested/非root、環境注入/秘密非保存 | GitSourceClassificationFailsClosed、GitIgnoresInjectedRepositoryState、GitSecretsNeverReachErrorsOrMetadata、InstallVerifyRemovePreservesUnrelatedData |
| #111 管理親linkの外部削除拒否 | UnsafeParentsNeverDeleteTargets、外部導入物/dataのbytes不変と復旧後成功 |
| #112 package根link拒否、追加/欠落/変更検出 | VerifyEntirePackageBeforeUse、PLUGIN_MODIFIEDと正常復旧 |
| record脱出/集合/hash/identity/版/衝突 | UntrustedRecordNeverReadsOutside、RecordIdentityAndDuplicatePropertiesFailClosed、LoadingOnePluginStillValidatesTheWholeRegistry |
| 8MiB record/200MiB packageの実効上限 | 有効な巨大JSON/一致hashのfixture。上限を個別に外すmutationでassertion失敗を確認 |
| checkout/hook/filter非実行、確定blob/commit | ExportPinsBlobsWithoutExecution、独立SHA/実行mode、GitInstallPublishesOnlyVerifiedPackageAndPinnedRecord |
| 120秒、親先行終了後の子孫停止 | GitFailuresAndTimeoutNeverBecomeSuccessfulCopies、所有子の停止を実観測 |
| staging identity、失敗時既存保護、限定削除 | CommitUsesStagedIdentity、FailedInstallKeepsExistingInstallation、InstallVerifyRemovePreservesUnrelatedData |
| lease中の実Install/Remove拒否と解放後成功 | UsageLeaseOwnsProjectLock、LeaseAndMutationSerialize |

Windows/case-insensitive filesystem/別libc/実認証/Resonite/Blenderはローカル未実行。Linux native ABIは本Dev Container（glibc2.43、x86_64）で実確認、Windowsは定義/layout/制御フローの静的確認のみ。公開CIのWindows結果を後記し、それ以外の未実行環境を確認済みにしない。

### 調整役の裁定（記録順）

| 裁定 | 誤った場合の負担 |
| --- | --- |
| manifest v1の意味を維持し安全基盤を責務別に再実装 | 互換性修正/再実装 |
| Git内非rootとGit外nested repositoryを拒否 | 利用者はrootかclean exportを用意 |
| OpenVerifiedは利用完了までproject-wide lease | 呼出側は保持/Disposeと再入回避が必要 |
| 同一SHAの以前のbaselineを再利用 | 環境差は後続focused/buildで検出 |
| 実装/レビューへ同じSpec・制約・受け入れ条件を配布 | bounded inputが少し増える |
| 特殊fileのcopy拒否をdata削除へ適用しない指摘を採用 | 誤りなら限定削除の修正が必要。無視すると部分削除 |
| 親先行終了で子孫が残る停止漏れを採用 | 無視すると失敗報告後も子が継続 |
| 追加launcherでなく同じmodule内のprivate native containmentを許可 | native相互運用の保守/修正。別libc/Windows実機は未確認 |
| Planが予定する狭いinternal staged-identity seamを許可 | internalなテスト結合の保守 |
| 最終3Minor（@path、上限テスト識別力、case能力）を1回で修正 | bounded fix/re-review/全検証の追加時間 |
