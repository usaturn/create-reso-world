# usaturn/resoloop Issue #12 hostPathMap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** コンテナの CLI から Windows の Resonite へテクスチャを取り込めるよう、CLI のパスを Resonite が読めるパスへ変換する設定 `hostPathMap` と、plan の警告・取り込み失敗の案内を足す。

**Architecture:** 変換は Core の `HostPathMap` に置き、`WorldService` が texture・audio のファイルにだけ使ってからアダプターへ渡す。警告とエラーの読み替えも `WorldService` で行う。アダプター（`RLoop.ResoniteLink`）は変更しない。

**Tech Stack:** .NET 10（C#）、xUnit、ResoniteLink 0.13.1

**Spec:** `docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-12-host-path-map-design.md`

- 状態: approved（Spec と同じく、ユーザーの「途中で止めずに推奨案で進めて PR して」による事前の許可。実行方法はユーザーの選択が無いため、Native（このセッションで実装）とする。タスクが同じファイルに積み重なり、数が少ないため）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-12-host-path-map`（ブランチ `fix/issue-12-host-path-map`、起点 `4c70365`）

## Global Constraints

- 設定名: CLI `--host-path-map`、環境変数 `RESOLOOP_HOST_PATH_MAP`、JSON `hostPathMap`。値は `FROM=TO` の 1 組
- エラー・警告コード: `INVALID_HOST_PATH_MAP`（exit 3）、`ASSET_HOST_PATH_UNMAPPED`（plan の warning）、`ASSET_HOST_PATH_UNREACHABLE`（exit 3）
- 変換するのは `texture`・`texture2d`・`audio`・`audioclip` のファイルだけ。mesh と URI の asset は変換しない
- Core は ResoniteLink の型を参照しない（resoloop の `AGENTS.md`）
- dotnet test は CI で Windows で動く。テストのパスは `Path.GetTempPath()` から作る
- テストは `HostPathMap` の単体テストだけ。それ以外は実機と build・既存テストで確かめる

## Review Focus

1. `FROM` の接頭辞が別ディレクトリの先頭と一致する（`/a/repo` と `/a/repo-other`）→ 変換しない。Task 1 のテストで確かめる
2. Windows の CLI で `C:\` のパスを使う → 警告を出さない（`/` 始まりだけを対象にする条件をコードで確かめる）
3. 設定を変えた後の再 apply → 内容の hash が同じなら再取り込みしない（state に変換後のパスを入れない）
4. 取り込みが 30 秒でタイムアウトする → `REQUEST_TIMEOUT` のまま、`context` に `asset`・`hostPath`、対処に `--timeout 90` が入る。Task 4 の実機で確かめる
5. Resonite が別の理由で失敗する（画像の形式など）→ `ASSET_IMPORT_FAILED` のまま、`context` だけ増える

---

### Task 1: HostPathMap

**Files:**
- Create: `src/RLoop.Core/HostPathMap.cs`
- Test: `tests/RLoop.Tests/HostPathMapTests.cs`

**テストの要否:** 書く。接頭辞の区切り位置での一致、区切り文字の変換、解析の誤りはロジックの分岐であり、誤ると取り込みのたびに約 50 秒待って失敗する。

**Interfaces:**
- Produces: `HostPathMap.Parse(string? value, string? source = null) : HostPathMap?`、`bool Covers(string path)`、`string Map(string path)`、`static bool AppliesTo(string kind)`、`string From`、`string To`、`string? Source`、`ToString() => "FROM=TO"`

- [x] **Step 1: 失敗するテストを書く**

```csharp
using RLoop.Core;

namespace RLoop.Tests;

public sealed class HostPathMapTests
{
    private static readonly string Project = Path.Combine(Path.GetTempPath(), "resoloop-host-path", "repo");
    private const string Share = @"\\wsl.localhost\Distro\home\user\repo";

    [Fact]
    public void MapsOnlyPathsUnderTheCliPrefixIntoTheHostSeparatorStyle()
    {
        var source = Path.Combine(Project, "content", "tex.png");
        var map = HostPathMap.Parse(Project + Path.DirectorySeparatorChar + "=" + Share + @"\")!;

        Assert.Equal(Share + @"\content\tex.png", map.Map(source));
        Assert.Equal("/srv/repo/content/tex.png", HostPathMap.Parse(Project + "=/srv/repo")!.Map(source));
        // A sibling directory that merely starts with the same text is not under the prefix.
        var sibling = Path.Combine(Project + "-other", "tex.png");
        Assert.False(map.Covers(sibling));
        Assert.Equal(sibling, map.Map(sibling));
    }

    [Fact]
    public void RejectsValuesWithoutAnAbsoluteCliPrefixOrATarget()
    {
        foreach (var value in new[] { "no-separator", "relative/path=/srv/repo", "=/srv/repo", Project + "=" })
            Assert.Equal("INVALID_HOST_PATH_MAP", Assert.Throws<RLoopException>(() => HostPathMap.Parse(value, "cli")).Code);
    }
}
```

- [x] **Step 2: 失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~HostPathMapTests`
Expected: `HostPathMap` が無いためビルドが失敗する

- [x] **Step 3: 実装する**

```csharp
namespace RLoop.Core;

// Resonite opens texture and audio import paths on its own host (ImportTexture2DFile / ImportAudioClipFile),
// while mesh data is read by the CLI and sent. This rewrites a CLI path prefix into one that host can read.
public sealed class HostPathMap
{
    private static readonly char[] Separators = ['/', '\\'];

    private HostPathMap(string from, string to, string? source) => (From, To, Source) = (from, to, source);

    public string From { get; }
    public string To { get; }
    public string? Source { get; }

    public static bool AppliesTo(string kind) => kind.ToLowerInvariant() is "texture" or "texture2d" or "audio" or "audioclip";

    public static HostPathMap? Parse(string? value, string? source = null)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var separator = value.IndexOf('=');
        var from = separator > 0 ? value[..separator] : string.Empty;
        var to = separator >= 0 ? value[(separator + 1)..] : string.Empty;
        if (!Path.IsPathFullyQualified(from) || string.IsNullOrWhiteSpace(to))
            throw new RLoopException("INVALID_HOST_PATH_MAP",
                $"Host path map must be FROM=TO with an absolute CLI path prefix FROM, got '{value}'.", ExitCodes.ConfigurationError,
                new Dictionary<string, object?> { ["value"] = value, ["source"] = source },
                [@"Example: /workspaces/repo=\\wsl.localhost\<distro>\home\<user>\repo"]);
        return new HostPathMap(from, to, source);
    }

    public bool Covers(string path) => Remainder(path) is not null;

    public string Map(string path)
    {
        if (Remainder(path) is not { } remainder) return path;
        var separator = To.Contains('\\') || To.Length >= 2 && To[1] == ':' ? '\\' : '/';
        return To.TrimEnd(Separators) +
               remainder.Replace(Path.DirectorySeparatorChar, separator).Replace(Path.AltDirectorySeparatorChar, separator);
    }

    public override string ToString() => From + "=" + To;

    private string? Remainder(string path)
    {
        var prefix = From.TrimEnd(Separators);
        if (!path.StartsWith(prefix, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
            return null;
        if (path.Length == prefix.Length) return string.Empty;
        var next = path[prefix.Length];
        return next == Path.DirectorySeparatorChar || next == Path.AltDirectorySeparatorChar ? path[prefix.Length..] : null;
    }
}
```

- [x] **Step 4: 成功を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~HostPathMapTests`
Expected: PASS（2 件）

- [x] **Step 5: コミット**

```bash
git add src/RLoop.Core/HostPathMap.cs tests/RLoop.Tests/HostPathMapTests.cs
git commit -m "feat: add host path map for Resonite-side asset paths"
```

### Task 2: 設定・CLI・apply への組み込み

**Files:**
- Modify: `src/RLoop.Core/Configuration.cs`（`RLoopConfig` に `HostPathMap`、`Resolve` に `Pick`）
- Modify: `src/RLoop.Core/WorldService.cs`（コンストラクタ、`BuildAssetPlans`、`PlanApplyAsync` の警告、取り込みの例外の扱い、`AssetRuntime.HostSource`）
- Modify: `src/RLoop.Cli/Program.cs`（`cliConfig`、`WorldService` の生成、help）

**テストの要否:** 書かない。優先順位は既存の `Pick` で、他の設定のテストが確かめている。警告は `/` 始まりのパスでしか出ず Windows の CI では動かない。読み替えは Task 4 の実機で確かめる。代わりに build と既存テストの全件を実行する。

**Interfaces:**
- Consumes: Task 1 の `HostPathMap`
- Produces: `RLoopConfig.HostPathMap : string?`、`WorldService(IResoniteClient client, string? generatedContentSource = null, HostPathMap? hostPathMap = null)`

- [x] **Step 1: 設定**

`RLoopConfig` の末尾に `string? HostPathMap = null` を足す。`Resolve` に次を足し、`new RLoopConfig(...)` の末尾に `hostPathMap` を渡す。

```csharp
var hostPathMap = Pick("host-path-map", "RESOLOOP_HOST_PATH_MAP", x => x.HostPathMap, "hostPathMap");
```

- [x] **Step 2: WorldService**

コンストラクタに `HostPathMap? hostPathMap = null` を足す。`AssetRuntime` に `public string? HostSource { get; init; }` を足す。`BuildAssetPlans(PreparedApply prepared, HostPathMap? hostPathMap)` で次のように作る（呼び出しも直す）。

```csharp
var hostSource = direct is null && HostPathMap.AppliesTo(pair.Value.Kind) ? hostPathMap?.Map(resolved) ?? resolved : null;
var runtime = new AssetRuntime(pair.Key, pair.Value, resolved, hash, direct, unchanged ? "no-op" : "create") { HostSource = hostSource };
```

`PlanApplyAsync` の警告を `{ Warnings = [.. ComponentIdentityDiagnostics.Analyze(document), .. UnmappedHostPathWarnings(prepared)] }` にする。

```csharp
// A Windows Resonite resolves a POSIX path against C:\ and reports the failure only after about 50 seconds.
private IReadOnlyList<ApplyValidationIssue> UnmappedHostPathWarnings(PreparedApply prepared)
{
    var unmapped = prepared.Assets.Where(asset => asset.Action == "create" && asset.HostSource is not null &&
        asset.HostSource.StartsWith('/') && hostPathMap?.Covers(asset.ResolvedSource) != true).ToArray();
    return unmapped.Length == 0 ? [] :
    [
        new ApplyValidationIssue("ASSET_HOST_PATH_UNMAPPED",
            $"{unmapped.Length} texture/audio import(s) pass a POSIX path such as '{unmapped[0].HostSource}' to Resonite, which a Windows Resonite cannot open. Set hostPathMap (--host-path-map FROM=TO) unless Resonite runs natively on this host.",
            "$assets", "warning")
    ];
}
```

apply の取り込みの呼び出しを `await ImportAssetAsync(asset, cancellationToken)` にし、次を足す。

```csharp
private async Task<string> ImportAssetAsync(AssetRuntime asset, CancellationToken cancellationToken)
{
    try
    {
        return await client.ImportAssetAsync(asset.Spec, asset.HostSource ?? asset.ResolvedSource, cancellationToken);
    }
    catch (RLoopException ex)
    {
        var context = new Dictionary<string, object?>(ex.Context, StringComparer.Ordinal)
        {
            ["asset"] = asset.Key,
            ["kind"] = asset.Spec.Kind,
            ["source"] = asset.ResolvedSource
        };
        if (asset.HostSource is null) throw new RLoopException(ex.Code, ex.Message, ex.ExitCode, context, ex.Suggestions, ex);
        context["hostPath"] = asset.HostSource;
        context["hostPathMap"] = hostPathMap?.ToString();
        // plan checked that the source exists here, so a missing path means the Resonite host cannot see it.
        if (ex.Code == "ASSET_IMPORT_FAILED" && (ex.Message.Contains("DirectoryNotFoundException", StringComparison.Ordinal) ||
                                                 ex.Message.Contains("FileNotFoundException", StringComparison.Ordinal)))
        {
            context["resoniteError"] = ex.Message;
            throw new RLoopException("ASSET_HOST_PATH_UNREACHABLE",
                $"Resonite could not open '{asset.HostSource}' for asset '{asset.Key}'. Resonite reads texture and audio files on its own host.",
                ExitCodes.ConfigurationError, context, HostPathSuggestions(), ex);
        }
        if (ex.Code == "REQUEST_TIMEOUT")
            throw new RLoopException(ex.Code, ex.Message, ex.ExitCode, context,
            [
                "Resonite can take about 50 seconds to report a path it cannot open, longer than the default request timeout; retry once with --timeout 90 to receive its error.",
                .. HostPathSuggestions(), .. ex.Suggestions
            ], ex);
        throw new RLoopException(ex.Code, ex.Message, ex.ExitCode, context, ex.Suggestions, ex);
    }
}

private string[] HostPathSuggestions() => hostPathMap is null
    ?
    [
        @"If Resonite cannot read hostPath, set hostPathMap FROM=TO (--host-path-map, RESOLOOP_HOST_PATH_MAP or .resoloop.json) so the CLI prefix FROM becomes a path the Resonite host can read, for example /workspaces/repo=\\wsl.localhost\<distro>\home\<user>\repo.",
        "Or run apply on the Resonite host."
    ]
    :
    [
        $"Check that hostPathMap '{hostPathMap}' covers the source and that its target is readable on the Resonite host.",
        "Or run apply on the Resonite host."
    ];
```

- [x] **Step 3: CLI**

`cliConfig` に `["host-path-map"] = parsed.Option("host-path-map")` を足す。接続するコマンドの `var uri = await ResolveConnectionUrlAsync(...)`（`RunResonite` の直前）の前で解析し、`WorldService` に渡す。

```csharp
var hostPathMap = HostPathMap.Parse(resolution.Config.HostPathMap, resolution.Sources.GetValueOrDefault("hostPathMap"));
...
var world = new WorldService(client, GeneratedContentMetadata.SourceForVersion(ProductVersion()), hostPathMap);
```

help の Global options に `--host-path-map FROM=TO` の 1 行、Environment に `RESOLOOP_HOST_PATH_MAP` を足す。

- [x] **Step 4: 検証**

Run: `dotnet build ResoLoop.slnx && dotnet test ResoLoop.slnx --no-build`
Expected: 警告・エラーなしでビルドでき、既存テストを含めて全件成功する

- [x] **Step 5: コミット**

```bash
git add src/RLoop.Core/Configuration.cs src/RLoop.Core/WorldService.cs src/RLoop.Cli/Program.cs
git commit -m "feat: translate texture import paths and explain unreachable host paths"
```

### Task 3: 文書と同梱スキル

**Files:**
- Modify: `README-DETAILS.md`（設定の優先順位、Blender／asset の節）
- Modify: `docs/BLENDER.md:58`、`docs/DECLARATIVE.md:107`
- Modify: `skills/codex/resonite-blender/SKILL.md:90`

**テストの要否:** 書かない（文書と SKILL.md の文面だけ）。代わりに `git diff` で、設定名・コード名が Task 1・2 と一致することを確かめる。

- [x] **Step 1:** README-DETAILS の設定の優先順位に `--host-path-map`・`RESOLOOP_HOST_PATH_MAP` を足し、Blender の節にコンテナ・別ホストの手順（`hostPathMap` の例、`ASSET_HOST_PATH_UNMAPPED`・`ASSET_HOST_PATH_UNREACHABLE`、タイムアウトの案内）を書く
- [x] **Step 2:** BLENDER.md・DECLARATIVE.md の「同じ絶対パス」の記述に `hostPathMap` を足す
- [x] **Step 3:** SKILL.md の別ホストの記述を `hostPathMap` に合わせ、2 つのコードを見たら同じ apply を繰り返さず利用者に設定を依頼すると書く
- [x] **Step 4:** `git diff` を確認してコミット

```bash
git add README-DETAILS.md docs/BLENDER.md docs/DECLARATIVE.md skills/codex/resonite-blender/SKILL.md
git commit -m "docs: describe hostPathMap for container and remote Resonite hosts"
```

### Task 4: 実機の確認（ポート 40778）

**テストの要否:** 書かない（実機の確認。Spec「テスト」の 1〜4）。

作業場所は `/workspaces/reso-world/tmp/resoloop-12-probe/`（WSL から `\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world\tmp\resoloop-12-probe` で見える）。CLI は CODE_ROOT のビルド（`dotnet src/RLoop.Cli/bin/Debug/net10.0/resoloop.dll`）を使う。

- [x] **Step 1:** `probe.apply.json` を作る。Root 直下に `ResoLoop_Test_HostPathMap_<日時>` の Slot を 1 つ、`StaticTexture2D`（`URL` に `$asset:tex`）を 1 つ、asset `tex`（`kind: texture`、`source: probe-texture.png`）を宣言する。state は同じディレクトリ
- [x] **Step 2:** 設定なしの `plan` で `ASSET_HOST_PATH_UNMAPPED` が出る
- [x] **Step 3:** 設定なしの `apply`（既定 30 秒）で `REQUEST_TIMEOUT`、`context` に `asset`・`hostPath`、`slotsCreated` が 0
- [x] **Step 4:** 設定なしの `apply --timeout 90` で `ASSET_HOST_PATH_UNREACHABLE`（exit 3）
- [x] **Step 5:** `--host-path-map '/workspaces/reso-world=\\wsl.localhost\Gentoo\home\usaturn\repo\reso-world'` の `plan` で警告が出ず、`apply` が成功する。作った Slot を `inspect` して StaticTexture2D の URL を確かめる
- [x] **Step 6:** 作った Slot を、apply の結果の正確な ID で `slot delete ID --yes` する。`find --name ResoLoop_Test_HostPathMap` で残っていないことを確かめる

### Task 5: 公開

- [x] **Step 1:** fork のブランチを push し、usaturn/resoloop へ PR を作る（本文に実機の結果、対象外、`Fixes #12`）
- [x] **Step 2:** PR の CI（パブリック）の結果を確かめる
- [x] **Step 3:** Spec・Plan に実装の HEAD・PR・実機の結果を記録し、create-reso-world の文書専用 PR を作る

## 実施結果（2026-10-09）

- 実行方法: Native（このセッションで実装）。作業記録は CODE_ROOT の `.superpowers/sdd/2026-10-09-usaturn-resoloop-issue-12-host-path-map/progress.md`（git の追跡対象外）
- コミット: `170b177`（Task 1）、`13dbed2`（Task 2）、`709d57d`（Task 3）。レビュー後の修正は無し
- 判断（Ruling）: Task 4（実機）を Task 3（文書）より先に行った。実機の結果を文書の文面に反映するため
- テスト: Task 1 は RED（`HostPathMap` が無くビルド失敗）→ GREEN（2 件）。Debug・Release とも build は警告 0 件、RLoop.Tests 456 件・RLoop.IntegrationTests 19 件（実機なし）がすべて成功
- 実機（Resonite 2026.9.18.82 / ResoniteLink 0.13.1.0、ポート 40778）: Spec「テスト」の 1〜4 をすべて確認した
  1. 設定なしの plan で `ASSET_HOST_PATH_UNMAPPED`（1 件、path `$assets`）
  2. 設定なしの apply（30 秒）で `REQUEST_TIMEOUT`（exit 8）。`context` に `asset: tex`・`hostPath`・`slotsCreated: 0`、対処の先頭に `--timeout 90`
  3. 設定なしの apply `--timeout 90` で `ASSET_HOST_PATH_UNREACHABLE`（exit 3）、`resoniteError` に Resonite の `DirectoryNotFoundException`
  4. `--host-path-map` ありの plan で警告なし、apply 成功（Slot `Reso_A682`、StaticTexture2D の URL に `local://…png`）。設定を外した plan で asset は `no-op`
  - 追加: `.resoloop.json` の `hostPathMap` を読み、`--verbose` の `configSources` に指定元が出る。不正な `RESOLOOP_HOST_PATH_MAP` で `INVALID_HOST_PATH_MAP`（`source: environment:RESOLOOP_HOST_PATH_MAP`）
  - 作った Slot `Reso_A682`（`ResoLoop_Test_HostPathMap_20261009`）は ID 指定で削除し、`find` で残っていないことを確認した
- ブランチ全体のレビュー: 新しいコンテキストのレビュアー（opus）が `4c70365..709d57d` を確認し、Critical・Important は 0 件、Review Focus の 1〜5 はすべて成り立つ。Minor 4 件（`FROM` を正規化しない、POSIX の `FROM` を書いた共有の `.resoloop.json` は Windows で `INVALID_HOST_PATH_MAP` になる、help の例が shell の引用符で囲まれていない、`FileNotFoundException` の照合が広い）は、致命的でないため対応しない（PR 本文に記載）
- 公開: fork PR https://github.com/usaturn/resoloop/pull/16 を作成。head `709d57d` の CI（run 37923742478）は windows（build・test・pack・導入の smoke test）と linux-offline-python の両方が成功。文書は create-reso-world の文書専用 PR で公開する
