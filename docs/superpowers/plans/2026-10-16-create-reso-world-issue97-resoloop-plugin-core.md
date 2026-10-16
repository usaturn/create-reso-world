# resoloop プラグインの土台（#97）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/97
- 状態: completed（2026-10-16 JST、利用者の指示「Spec と Plan を completed にして」による。内容の明示承認は記録していない。実行は利用者の指示「途中で止めずに推奨案で PR まで作成して」（2026-10-16 JST）による。完了の根拠は末尾の「完了」）
- 実行方法: Native（executing-plans）。エージェントの判断。Task どうしが同じ型を共有して密につながり、利用者が途中で止めないことを求めたため。最後に新しいレビュアーがブランチ全体を見る
- 基準: resoloop 上流 `main` の `99c59be98df0f10b0a8e58781b7f4f67029016f5`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-97-plugin-core`（ブランチ `feat/plugin-core`。完了後に削除済み）

**Goal:** resoloop にプラグインの manifest（v1）・導入・一覧・削除・記録と `PluginRegistry` を入れ、`resoloop plugin install|list|remove` を使えるようにする。

**Architecture:** `src/RLoop.Core/Plugins/`（名前空間 `RLoop.Core.Plugins`）に、SemVer・名前の規則・エラー・manifest・registry・installer を置く。CLI は `Program.cs` に `plugin` の節を足し、Core を呼んで結果を出すだけにする。プラグインのコードは導入の時点で実行せず、`git` だけを別プロセスで呼ぶ。

**Tech Stack:** .NET 10（C#、`System.Text.Json`）、xUnit 2.9、外部の `git`（2.24 以上）

**Spec:** `../specs/2026-10-16-create-reso-world-issue97-resoloop-plugin-core-design.md`

## Global Constraints

- 変えるのは `src/RLoop.Core/Plugins/`（新規）、`src/RLoop.Cli/Program.cs` の `plugin` の節・help の行・`using RLoop.Core.Plugins;`、`tests/RLoop.Tests/Plugin{Manifest,Registry,Installer}Tests.cs`、`tests/fixtures/plugins/core/` だけ
- Core は ResoniteLink・Flux の型を参照しない
- manifest のファイル名は `resoloop-plugin.json`、`schemaVersion` は `1`、256 KiB まで
- 名前は `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` で 2〜40 文字。スキルは `resonite-` で始まらない
- 置き場所は `<project>/.resoloop/plugins/<name>/`（`install.json`・`package/`・`data/`）、一時ディレクトリは `.staging-<guid>`
- 導入の上限はファイル 10,000 個・合計 200 MiB
- `args` の置き換えの対象は `${pluginRoot}` と `${pluginData}` だけ
- `remove` は `--yes` 必須（`CONFIRMATION_REQUIRED`）
- エラーコードは `PLUGIN_` で始める。終了コードは Spec の表のとおり
- テストはオフライン。Git の場面は一時ディレクトリの `git init` と `file://` の URL で作る
- コードのコメントは英語（既存のコードに合わせる）

## Review Focus

- 導入先の中の symlink を `remove` が辿って外のファイルを消すこと。消さずにリンクだけを外すのが期待（Task 3 にテスト）
- Git の作業ツリーで無視されたファイル（`.venv` など）を写すこと。写さないのが期待（Task 3 にテスト）
- 親のリポジトリの無視された場所にあるディレクトリから導入すると manifest が見つからないこと。全部を写して導入できるのが期待（Task 3 にテスト）
- 導入が途中で失敗したときに `.staging-*` や `<name>/` が残ること。何も残らないのが期待（Task 3 にテスト）
- BOM 付きの manifest や重複した欄。BOM は読み、重複は拒否するのが期待（Task 1 にテスト）

## ファイルの構成

| ファイル | 役割 | Task |
| --- | --- | --- |
| `src/RLoop.Core/Plugins/SemanticVersion.cs` | SemVer 2.0 の解析・比較・JSON の文字列化 | 1 |
| `src/RLoop.Core/Plugins/PluginErrors.cs` | `PLUGIN_*` のコードと終了コード | 1 |
| `src/RLoop.Core/Plugins/PluginNames.cs` | 名前の規則・予約・衝突の検出 | 1 |
| `src/RLoop.Core/Plugins/PluginManifest.cs` | manifest の型・解析・検証 | 1 |
| `src/RLoop.Core/Plugins/PluginRegistry.cs` | 記録・ファイルの照合・`PluginRegistry` | 2 |
| `src/RLoop.Core/Plugins/PluginInstaller.cs` | 導入・削除・ファイルの列挙と複写 | 3 |
| `src/RLoop.Core/Plugins/PluginGit.cs` | `git` の呼び出し（作業ツリーの一覧、clone） | 3 |
| `src/RLoop.Cli/Program.cs` | `plugin` の節と help の行 | 4 |
| `tests/fixtures/plugins/core/sample-plugin/` | 正しいプラグインの見本 | 1 |
| `tests/RLoop.Tests/PluginManifestTests.cs` | manifest・SemVer・名前のテストと共通の `PluginFixture` | 1 |
| `tests/RLoop.Tests/PluginRegistryTests.cs` | registry のテスト | 2 |
| `tests/RLoop.Tests/PluginInstallerTests.cs` | 導入・削除のテスト | 3 |

コードの塊の直前にある `<!-- file: パス -->` は、そのファイルの全文であることを示す。実装ではこの塊をそのままファイルに書く（Plan と実装の食い違いを防ぐため）。

## 共通の検証コマンド

CODE_ROOT で実行する。

```bash
dotnet build ResoLoop.slnx -v q -nologo
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --no-build -nologo --filter "FullyQualifiedName~RLoop.Tests.Plugin"
```

---

### Task 1: manifest v1（SemVer・エラー・名前の規則・解析と検証）

テスト: 要る。manifest の解析・検証・SemVer の順序・名前の衝突は、コードを実行して確かめる分岐である。

**Files:**
- Create: `src/RLoop.Core/Plugins/SemanticVersion.cs`、`PluginErrors.cs`、`PluginNames.cs`、`PluginManifest.cs`
- Create: `tests/fixtures/plugins/core/sample-plugin/`（`resoloop-plugin.json`、`scripts/hello.sh`、`skills/sample-skill/SKILL.md`、`recipes/sample-card.json`）
- Test: `tests/RLoop.Tests/PluginManifestTests.cs`（後の Task も使う `PluginFixture` を含む）

**Interfaces:**
- Produces: `SemanticVersion.TryParse(string?, out SemanticVersion?)`、`CompareTo`、`Text`。`PluginErrors.Create(code, message, context?, suggestions?, inner?)` と各コードの定数。`PluginNames.IsValid(string?)`、`PluginNames.FindConflicts(PluginManifest, IEnumerable<PluginManifest>)`、`PluginNames.BuiltinCommands`。`PluginManifest.Load(string rootDirectory, IReadOnlyCollection<string> files)`、`PluginManifest.Parse(byte[])`、`manifest.EnsureCompatibleWith(string resoloopVersion)`、`PluginManifest.IsSafeRelativePath(string)`、定数 `FileName`・`PluginRootToken`・`PluginDataToken`
- Produces（テスト）: `PluginFixture.ResoloopVersion`、`CopySample(string)`、`CopyDirectory(string, string)`、`Files(string)`、`EditManifest(string, Action<JsonObject>)`、`CreateProject(string)`、`DeleteDirectory(string)`

- [ ] **Step 1: fixture を書く**

<!-- file: tests/fixtures/plugins/core/sample-plugin/resoloop-plugin.json -->
```json
{
  "schemaVersion": 1,
  "name": "sample-plugin",
  "version": "1.2.3",
  "description": "Fixture plugin for resoloop plugin tests.",
  "resoloop": { "minVersion": "0.1.0-preview.1", "maxVersionExclusive": "0.2.0" },
  "commands": [
    {
      "name": "sample-hello",
      "description": "Print a greeting.",
      "program": "./scripts/hello.sh",
      "args": ["--root", "${pluginRoot}", "--data=${pluginData}"],
      "timeoutSeconds": 60
    },
    { "name": "sample-uv", "description": "Run the sample through uv.", "program": "uv", "args": ["run", "--project", "${pluginRoot}", "sample"] }
  ],
  "skills": [{ "name": "sample-skill", "path": "skills/sample-skill" }],
  "recipes": [
    {
      "name": "sample-card",
      "path": "recipes/sample-card.json",
      "prototype": "sample.card",
      "purpose": "Fixture card prototype.",
      "parameters": { "key": "Unique stable key prefix." },
      "ports": { "root": "$slot:<key>" },
      "requirements": ["Caller owns visuals."]
    }
  ],
  "tools": [{ "name": "uv", "executable": "uv", "versionArgs": ["--version"], "required": false, "hint": "Install uv." }]
}
```

<!-- file: tests/fixtures/plugins/core/sample-plugin/scripts/hello.sh -->
```sh
#!/bin/sh
echo "hello from sample-plugin"
```

<!-- file: tests/fixtures/plugins/core/sample-plugin/skills/sample-skill/SKILL.md -->
```markdown
---
name: sample-skill
description: Fixture skill for resoloop plugin tests.
---

# Sample skill
```

<!-- file: tests/fixtures/plugins/core/sample-plugin/recipes/sample-card.json -->
```json
{
  "prototypes": {
    "sample.card": { "slot": { "key": "${key}", "name": "${key}" } }
  }
}
```

- [ ] **Step 2: 失敗するテストを書く**

<!-- file: tests/RLoop.Tests/PluginManifestTests.cs -->
```csharp
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using RLoop.Core;
using RLoop.Core.Plugins;

namespace RLoop.Tests;

public sealed class PluginManifestTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "resoloop-plugin-manifest-tests-" + Guid.NewGuid().ToString("N"));

    public PluginManifestTests() => PluginFixture.CopySample(_root);

    [Fact]
    public void LoadsEveryFieldOfTheSampleManifest()
    {
        var manifest = PluginManifest.Load(_root, PluginFixture.Files(_root));

        Assert.Equal("sample-plugin", manifest.Name);
        Assert.Equal("1.2.3", manifest.Version.Text);
        Assert.Equal(["sample-hello", "sample-uv"], manifest.Commands.Select(command => command.Name));
        Assert.Equal("./scripts/hello.sh", manifest.Commands[0].Program);
        Assert.Equal(["--root", PluginManifest.PluginRootToken, "--data=" + PluginManifest.PluginDataToken], manifest.Commands[0].Args);
        Assert.Equal(60, manifest.Commands[0].TimeoutSeconds);
        Assert.Null(manifest.Commands[1].TimeoutSeconds);
        Assert.Equal("skills/sample-skill", Assert.Single(manifest.Skills).Path);
        var recipe = Assert.Single(manifest.Recipes);
        Assert.Equal("sample.card", recipe.Prototype);
        Assert.Equal("Unique stable key prefix.", recipe.Parameters["key"]);
        Assert.Equal("$slot:<key>", recipe.Ports["root"]);
        var tool = Assert.Single(manifest.Tools);
        Assert.False(tool.Required);
        Assert.Equal(["--version"], tool.VersionArgs);
        Assert.True(manifest.Resoloop.Contains(Version(PluginFixture.ResoloopVersion)));
    }

    [Fact]
    public void ReportsEveryInvalidFieldWithItsJsonPath()
    {
        PluginFixture.EditManifest(_root, json =>
        {
            json["name"] = "Bad_Name";
            json["version"] = "1.0";
            json["extra"] = true;
            json["commands"]![0]!["program"] = "/usr/bin/env";
            json["commands"]![1]!["args"] = new JsonArray("${HOME}");
            json["skills"]![0]!["path"] = "../outside";
            json["tools"]![0]!["required"] = "yes";
        });

        var errors = ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        foreach (var path in new[] { "$.name:", "$.version:", "$.extra:", "$.commands[0].program:", "$.commands[1].args[0]:",
                     "$.skills[0].path:", "$.tools[0].required:" })
            Assert.Contains(errors, error => error.StartsWith(path, StringComparison.Ordinal));
    }

    [Fact]
    public void RejectsDuplicatedFields()
    {
        var json = File.ReadAllText(Path.Combine(_root, PluginManifest.FileName));
        File.WriteAllText(Path.Combine(_root, PluginManifest.FileName), json.Replace("\"name\": \"sample-plugin\",",
            "\"name\": \"sample-plugin\", \"name\": \"other-plugin\",", StringComparison.Ordinal));

        var errors = ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Contains("$.name: is duplicated.", errors);
    }

    [Fact]
    public void RejectsDuplicatedNamesWithinAList()
    {
        PluginFixture.EditManifest(_root, json => json["commands"]![1]!["name"] = "sample-hello");

        var errors = ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Contains(errors, error => error.StartsWith("$.commands:", StringComparison.Ordinal) && error.Contains("sample-hello"));
    }

    [Fact]
    public void ReadsAManifestWithAUtf8ByteOrderMark()
    {
        var path = Path.Combine(_root, PluginManifest.FileName);
        File.WriteAllText(path, File.ReadAllText(path), new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));

        Assert.Equal("sample-plugin", PluginManifest.Load(_root, PluginFixture.Files(_root)).Name);
    }

    [Fact]
    public void RejectsMalformedJson()
    {
        File.WriteAllText(Path.Combine(_root, PluginManifest.FileName), "{ \"schemaVersion\": 1,");

        Assert.NotEmpty(ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root))));
    }

    [Fact]
    public void RejectsAnUnsupportedSchemaVersion()
    {
        PluginFixture.EditManifest(_root, json => json["schemaVersion"] = 2);

        var ex = Assert.Throws<RLoopException>(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Equal("PLUGIN_SCHEMA_UNSUPPORTED", ex.Code);
    }

    [Fact]
    public void RequiresTheManifestFile()
    {
        File.Delete(Path.Combine(_root, PluginManifest.FileName));

        var ex = Assert.Throws<RLoopException>(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Equal("PLUGIN_MANIFEST_NOT_FOUND", ex.Code);
        Assert.Equal(ExitCodes.ValidationFailed, ex.ExitCode);
    }

    [Fact]
    public void RejectsReferencedFilesThatAreNotInThePlugin()
    {
        File.Delete(Path.Combine(_root, "skills", "sample-skill", "SKILL.md"));
        PluginFixture.EditManifest(_root, json =>
        {
            json["commands"]![0]!["program"] = "./scripts/missing.sh";
            json["recipes"]![0]!["prototype"] = "sample.missing";
        });

        var errors = ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Contains(errors, error => error.StartsWith("$.commands[0].program:", StringComparison.Ordinal));
        Assert.Contains(errors, error => error.StartsWith("$.skills[0].path:", StringComparison.Ordinal));
        Assert.Contains(errors, error => error.StartsWith("$.recipes[0].path:", StringComparison.Ordinal));
    }

    [Fact]
    public void RequiresTheRecipeKeyParameterAndAnIncreasingVersionRange()
    {
        PluginFixture.EditManifest(_root, json =>
        {
            json["recipes"]![0]!["parameters"] = new JsonObject { ["size"] = "Size." };
            json["resoloop"]!["maxVersionExclusive"] = "0.1.0-preview.1";
        });

        var errors = ManifestErrors(() => PluginManifest.Load(_root, PluginFixture.Files(_root)));

        Assert.Contains(errors, error => error.StartsWith("$.recipes[0].parameters:", StringComparison.Ordinal));
        Assert.Contains(errors, error => error.StartsWith("$.resoloop.maxVersionExclusive:", StringComparison.Ordinal));
    }

    [Theory]
    [InlineData("0.1.0-preview.9", "0.1.0-preview.17")]
    [InlineData("0.1.0-preview.17", "0.1.0")]
    [InlineData("1.0.0-alpha", "1.0.0-alpha.1")]
    [InlineData("1.0.0-alpha.1", "1.0.0-alpha.beta")]
    [InlineData("1.0.0-beta.11", "1.0.0-rc.1")]
    [InlineData("1.9.0", "1.10.0")]
    public void OrdersVersionsBySemVerPrecedence(string lower, string higher)
    {
        Assert.True(Version(lower).CompareTo(Version(higher)) < 0);
        Assert.True(Version(higher).CompareTo(Version(lower)) > 0);
    }

    [Fact]
    public void IgnoresBuildMetadataWhenComparing() =>
        Assert.Equal(0, Version("1.0.0+build.1").CompareTo(Version("1.0.0+build.2")));

    [Theory]
    [InlineData("1.0")]
    [InlineData("01.0.0")]
    [InlineData("1.0.0-")]
    [InlineData("1.0.0-01")]
    [InlineData("v1.0.0")]
    [InlineData("1.0.0\n")]
    public void RejectsTextThatIsNotSemVer(string text) => Assert.False(SemanticVersion.TryParse(text, out _));

    [Theory]
    [InlineData("0.1.0-preview.17", true)]
    [InlineData("0.1.0-preview.1", true)]
    [InlineData("0.0.9", false)]
    [InlineData("0.2.0", false)]
    [InlineData("unknown", false)]
    public void ChecksTheSupportedResoloopVersion(string resoloopVersion, bool compatible)
    {
        var manifest = PluginManifest.Load(_root, PluginFixture.Files(_root));

        if (compatible) manifest.EnsureCompatibleWith(resoloopVersion);
        else Assert.Equal("PLUGIN_INCOMPATIBLE_VERSION",
            Assert.Throws<RLoopException>(() => manifest.EnsureCompatibleWith(resoloopVersion)).Code);
    }

    [Theory]
    [InlineData("ab", true)]
    [InlineData("meshy-glb", true)]
    [InlineData("a1-b2", true)]
    [InlineData("a", false)]
    [InlineData("Ab", false)]
    [InlineData("1a", false)]
    [InlineData("ab-", false)]
    [InlineData("a--b", false)]
    [InlineData("a_b", false)]
    [InlineData("ab\n", false)]
    [InlineData("abcdefghijabcdefghijabcdefghijabcdefghijk", false)]
    public void AppliesTheNameRule(string name, bool valid) => Assert.Equal(valid, PluginNames.IsValid(name));

    [Fact]
    public void FindsConflictsWithBuiltInsAndOtherPlugins()
    {
        var manifest = PluginManifest.Load(_root, PluginFixture.Files(_root));
        var conflicting = manifest with
        {
            Name = "apply",
            Commands = [manifest.Commands[0] with { Name = "doctor" }],
            Skills = [new PluginSkill("resonite-build", "skills/sample-skill"), new PluginSkill("resonite-extra", "skills/sample-skill")],
            Recipes = [manifest.Recipes[0] with { Name = "button" }]
        };
        var other = manifest with { Name = "other-plugin" };

        var conflicts = PluginNames.FindConflicts(conflicting, []);
        var withOther = PluginNames.FindConflicts(manifest, [other]);

        Assert.Contains("plugin name 'apply' is a built-in command.", conflicts);
        Assert.Contains("command 'doctor' is a built-in command.", conflicts);
        Assert.Contains("skill 'resonite-build' is a bundled skill.", conflicts);
        Assert.Contains("skill 'resonite-extra' uses the reserved prefix 'resonite-'.", conflicts);
        Assert.Contains("recipe 'button' is a built-in UIX recipe.", conflicts);
        Assert.Contains("command 'sample-hello' is also provided by plugin 'other-plugin'.", withOther);
        Assert.Contains("skill 'sample-skill' is also provided by plugin 'other-plugin'.", withOther);
        Assert.Contains("recipe 'sample-card' is also provided by plugin 'other-plugin'.", withOther);
        Assert.Empty(PluginNames.FindConflicts(manifest, []));
    }

    public void Dispose() => PluginFixture.DeleteDirectory(_root);

    private static SemanticVersion Version(string text) =>
        SemanticVersion.TryParse(text, out var version) ? version : throw new ArgumentException(text);

    private static IReadOnlyList<string> ManifestErrors(Action action)
    {
        var ex = Assert.Throws<RLoopException>(action);
        Assert.Equal("PLUGIN_MANIFEST_INVALID", ex.Code);
        return Assert.IsAssignableFrom<IReadOnlyList<string>>(ex.Context["errors"]);
    }
}

/// <summary>Shared helpers for the plugin tests. Every test works in its own temporary directory.</summary>
internal static class PluginFixture
{
    public const string ResoloopVersion = "0.1.0-preview.17";

    private static readonly EnumerationOptions AllFiles = new() { RecurseSubdirectories = true, AttributesToSkip = 0 };

    public static string SamplePath => Path.Combine(AppContext.BaseDirectory, "fixtures", "plugins", "core", "sample-plugin");

    public static string CopySample(string destination)
    {
        CopyDirectory(SamplePath, destination);
        return destination;
    }

    public static void CopyDirectory(string source, string destination)
    {
        Directory.CreateDirectory(destination);
        foreach (var file in Directory.EnumerateFiles(source, "*", AllFiles))
        {
            var target = Path.Combine(destination, Path.GetRelativePath(source, file));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(file, target);
        }
    }

    public static IReadOnlyCollection<string> Files(string root) =>
        Directory.EnumerateFiles(root, "*", AllFiles)
            .Select(path => Path.GetRelativePath(root, path).Replace(Path.DirectorySeparatorChar, '/'))
            .ToHashSet(StringComparer.Ordinal);

    public static void EditManifest(string root, Action<JsonObject> edit)
    {
        var path = Path.Combine(root, PluginManifest.FileName);
        var json = JsonNode.Parse(File.ReadAllText(path))!.AsObject();
        edit(json);
        File.WriteAllText(path, json.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
    }

    public static string CreateProject(string root)
    {
        Directory.CreateDirectory(root);
        File.WriteAllText(Path.Combine(root, ".resoloop.json"), "{}\n");
        return root;
    }

    // Removes links without following them, and clears read-only flags that git sets on Windows object files.
    public static void DeleteDirectory(string path)
    {
        var root = new DirectoryInfo(path);
        if (root.LinkTarget is not null) { File.Delete(path); return; }
        if (!root.Exists) return;
        foreach (var entry in root.EnumerateFileSystemInfos("*", new EnumerationOptions { AttributesToSkip = 0 }))
        {
            if (entry.LinkTarget is not null)
            {
                if (entry is DirectoryInfo && OperatingSystem.IsWindows()) Directory.Delete(entry.FullName);
                else File.Delete(entry.FullName);
            }
            else if (entry is DirectoryInfo) DeleteDirectory(entry.FullName);
            else
            {
                entry.Attributes = FileAttributes.Normal;
                entry.Delete();
            }
        }
        root.Delete();
    }
}
```

- [ ] **Step 3: テストが失敗することを確かめる**

Run: 共通の検証コマンド
Expected: ビルドが `SemanticVersion`・`PluginManifest`・`PluginNames` の未定義で失敗する

- [ ] **Step 4: SemVer とエラーを実装する**

<!-- file: src/RLoop.Core/Plugins/SemanticVersion.cs -->
```csharp
using System.Diagnostics.CodeAnalysis;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace RLoop.Core.Plugins;

/// <summary>SemVer 2.0.0 version. Build metadata is kept in <see cref="Text"/> and ignored when comparing.</summary>
[JsonConverter(typeof(SemanticVersionJsonConverter))]
public sealed partial class SemanticVersion : IComparable<SemanticVersion>
{
    private const int MaxLength = 128;
    private readonly string[] _core;
    private readonly string[] _prerelease;

    private SemanticVersion(string text, string[] core, string[] prerelease)
    {
        Text = text;
        _core = core;
        _prerelease = prerelease;
    }

    public string Text { get; }

    public static bool TryParse(string? text, [NotNullWhen(true)] out SemanticVersion? version)
    {
        version = null;
        if (text is null || text.Length > MaxLength) return false;
        var match = Pattern().Match(text);
        if (!match.Success) return false;
        version = new SemanticVersion(text,
            [match.Groups["major"].Value, match.Groups["minor"].Value, match.Groups["patch"].Value],
            match.Groups["pre"].Success ? match.Groups["pre"].Value.Split('.') : []);
        return true;
    }

    public int CompareTo(SemanticVersion? other)
    {
        if (other is null) return 1;
        for (var i = 0; i < _core.Length; i++)
        {
            var core = CompareNumeric(_core[i], other._core[i]);
            if (core != 0) return core;
        }
        // A version without pre-release identifiers has higher precedence than one with them.
        if (_prerelease.Length == 0 || other._prerelease.Length == 0)
            return other._prerelease.Length.CompareTo(_prerelease.Length);
        for (var i = 0; i < Math.Min(_prerelease.Length, other._prerelease.Length); i++)
        {
            var left = _prerelease[i];
            var right = other._prerelease[i];
            var leftNumeric = left.All(char.IsAsciiDigit);
            var rightNumeric = right.All(char.IsAsciiDigit);
            var result = leftNumeric && rightNumeric ? CompareNumeric(left, right)
                : leftNumeric ? -1
                : rightNumeric ? 1
                : Math.Sign(string.CompareOrdinal(left, right));
            if (result != 0) return result;
        }
        return _prerelease.Length.CompareTo(other._prerelease.Length);
    }

    public override string ToString() => Text;

    // SemVer forbids leading zeros in numeric identifiers, so a longer digit string is always the larger number.
    private static int CompareNumeric(string left, string right) =>
        left.Length != right.Length ? left.Length.CompareTo(right.Length) : Math.Sign(string.CompareOrdinal(left, right));

    [GeneratedRegex(@"^(?<major>0|[1-9][0-9]*)\.(?<minor>0|[1-9][0-9]*)\.(?<patch>0|[1-9][0-9]*)" +
                    @"(?:-(?<pre>(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?" +
                    @"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\z", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}

public sealed class SemanticVersionJsonConverter : JsonConverter<SemanticVersion>
{
    public override SemanticVersion Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options) =>
        SemanticVersion.TryParse(reader.GetString(), out var version) ? version : throw new JsonException("Expected a SemVer 2.0 version string.");

    public override void Write(Utf8JsonWriter writer, SemanticVersion value, JsonSerializerOptions options) =>
        writer.WriteStringValue(value.Text);
}
```

<!-- file: src/RLoop.Core/Plugins/PluginErrors.cs -->
```csharp
namespace RLoop.Core.Plugins;

/// <summary>Error codes of the plugin core. Every code maps to one exit code so callers cannot drift.</summary>
public static class PluginErrors
{
    public const string ProjectNotFound = "PLUGIN_PROJECT_NOT_FOUND";
    public const string SourceNotFound = "PLUGIN_SOURCE_NOT_FOUND";
    public const string SourceInvalid = "PLUGIN_SOURCE_INVALID";
    public const string GitRefRequired = "PLUGIN_GIT_REF_REQUIRED";
    public const string GitRefNotFound = "PLUGIN_GIT_REF_NOT_FOUND";
    public const string GitFailed = "PLUGIN_GIT_FAILED";
    public const string ManifestNotFound = "PLUGIN_MANIFEST_NOT_FOUND";
    public const string ManifestInvalid = "PLUGIN_MANIFEST_INVALID";
    public const string SchemaUnsupported = "PLUGIN_SCHEMA_UNSUPPORTED";
    public const string IncompatibleVersion = "PLUGIN_INCOMPATIBLE_VERSION";
    public const string NameConflict = "PLUGIN_NAME_CONFLICT";
    public const string AlreadyInstalled = "PLUGIN_ALREADY_INSTALLED";
    public const string NotInstalled = "PLUGIN_NOT_INSTALLED";
    public const string NameInvalid = "PLUGIN_NAME_INVALID";
    public const string RecordInvalid = "PLUGIN_RECORD_INVALID";
    public const string Modified = "PLUGIN_MODIFIED";
    public const string RemoveRefused = "PLUGIN_REMOVE_REFUSED";

    private static readonly IReadOnlyDictionary<string, int> ExitCodeByCode = new Dictionary<string, int>(StringComparer.Ordinal)
    {
        [ProjectNotFound] = ExitCodes.ConfigurationError,
        [SourceNotFound] = ExitCodes.NotFound,
        [SourceInvalid] = ExitCodes.ValidationFailed,
        [GitRefRequired] = ExitCodes.InvalidArguments,
        [GitRefNotFound] = ExitCodes.NotFound,
        [GitFailed] = ExitCodes.ExternalToolFailed,
        [ManifestNotFound] = ExitCodes.ValidationFailed,
        [ManifestInvalid] = ExitCodes.ValidationFailed,
        [SchemaUnsupported] = ExitCodes.ValidationFailed,
        [IncompatibleVersion] = ExitCodes.ValidationFailed,
        [NameConflict] = ExitCodes.ValidationFailed,
        [AlreadyInstalled] = ExitCodes.ValidationFailed,
        [NotInstalled] = ExitCodes.NotFound,
        [NameInvalid] = ExitCodes.InvalidArguments,
        [RecordInvalid] = ExitCodes.ValidationFailed,
        [Modified] = ExitCodes.ValidationFailed,
        [RemoveRefused] = ExitCodes.ValidationFailed
    };

    public static RLoopException Create(string code, string message, IReadOnlyDictionary<string, object?>? context = null,
        IReadOnlyList<string>? suggestions = null, Exception? innerException = null) =>
        new(code, message, ExitCodeByCode[code], context, suggestions, innerException);
}
```

- [ ] **Step 5: 名前の規則を実装する**

<!-- file: src/RLoop.Core/Plugins/PluginNames.cs -->
```csharp
using System.Text.RegularExpressions;

namespace RLoop.Core.Plugins;

public static partial class PluginNames
{
    public const int MinLength = 2;
    public const int MaxLength = 40;
    public const string ReservedSkillPrefix = "resonite-";
    public const string Rule = "^[a-z][a-z0-9]*(-[a-z0-9]+)*$ with 2..40 characters";

    // Top-level commands dispatched by RLoop.Cli Program (plus "plugins"). Add every new top-level command here.
    public static IReadOnlyList<string> BuiltinCommands { get; } =
    [
        "apply", "blender", "capture", "component", "diff", "discover", "doctor", "find", "flux", "help",
        "hierarchy", "init", "inspect", "item", "logs", "manifest", "observe", "ping", "plan", "plugin",
        "plugins", "scene", "schema", "skills", "slot", "status", "test", "tool", "type", "uix", "validate", "version"
    ];

    public static bool IsValid(string? name) =>
        name is { Length: >= MinLength and <= MaxLength } && Pattern().IsMatch(name);

    /// <summary>Names of <paramref name="manifest"/> that collide with built-ins or with another plugin's
    /// commands, skills or recipes (compared per kind).</summary>
    public static IReadOnlyList<string> FindConflicts(PluginManifest manifest, IEnumerable<PluginManifest> installed)
    {
        var conflicts = new List<string>();
        if (BuiltinCommands.Contains(manifest.Name)) conflicts.Add($"plugin name '{manifest.Name}' is a built-in command.");
        if (BundledSkillManager.Names.Contains(manifest.Name)) conflicts.Add($"plugin name '{manifest.Name}' is a bundled skill.");
        conflicts.AddRange(manifest.Commands.Where(command => BuiltinCommands.Contains(command.Name))
            .Select(command => $"command '{command.Name}' is a built-in command."));
        foreach (var skill in manifest.Skills)
        {
            if (BundledSkillManager.Names.Contains(skill.Name)) conflicts.Add($"skill '{skill.Name}' is a bundled skill.");
            else if (skill.Name.StartsWith(ReservedSkillPrefix, StringComparison.Ordinal))
                conflicts.Add($"skill '{skill.Name}' uses the reserved prefix '{ReservedSkillPrefix}'.");
        }
        conflicts.AddRange(manifest.Recipes.Where(recipe => UixRecipes.Catalog.Any(builtIn => builtIn.Name == recipe.Name))
            .Select(recipe => $"recipe '{recipe.Name}' is a built-in UIX recipe."));
        foreach (var other in installed.Where(other => other.Name != manifest.Name))
        {
            Overlap("command", manifest.Commands.Select(x => x.Name), other.Commands.Select(x => x.Name), other.Name, conflicts);
            Overlap("skill", manifest.Skills.Select(x => x.Name), other.Skills.Select(x => x.Name), other.Name, conflicts);
            Overlap("recipe", manifest.Recipes.Select(x => x.Name), other.Recipes.Select(x => x.Name), other.Name, conflicts);
        }
        return conflicts;
    }

    private static void Overlap(string kind, IEnumerable<string> names, IEnumerable<string> others, string plugin, List<string> conflicts) =>
        conflicts.AddRange(names.Intersect(others, StringComparer.Ordinal)
            .Select(name => $"{kind} '{name}' is also provided by plugin '{plugin}'."));

    [GeneratedRegex(@"^[a-z][a-z0-9]*(-[a-z0-9]+)*\z", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}
```

- [ ] **Step 6: manifest を実装する**

<!-- file: src/RLoop.Core/Plugins/PluginManifest.cs -->
```csharp
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace RLoop.Core.Plugins;

public sealed record PluginVersionRange(SemanticVersion MinVersion, SemanticVersion? MaxVersionExclusive)
{
    public bool Contains(SemanticVersion version) =>
        version.CompareTo(MinVersion) >= 0 && (MaxVersionExclusive is null || version.CompareTo(MaxVersionExclusive) < 0);

    public override string ToString() =>
        MaxVersionExclusive is null ? $">= {MinVersion}" : $">= {MinVersion} and < {MaxVersionExclusive}";
}

public sealed record PluginCommand(string Name, string Description, string Program, IReadOnlyList<string> Args, int? TimeoutSeconds);

public sealed record PluginSkill(string Name, string Path);

public sealed record PluginRecipe(string Name, string Path, string Prototype, string Purpose,
    IReadOnlyDictionary<string, string> Parameters, IReadOnlyDictionary<string, string> Ports, IReadOnlyList<string> Requirements);

public sealed record PluginTool(string Name, string Executable, IReadOnlyList<string> VersionArgs, bool Required, string? Hint);

/// <summary>resoloop-plugin.json, schema version 1. Unknown fields are rejected so typos never pass silently.</summary>
public sealed partial record PluginManifest(
    int SchemaVersion,
    string Name,
    SemanticVersion Version,
    string? Description,
    PluginVersionRange Resoloop,
    IReadOnlyList<PluginCommand> Commands,
    IReadOnlyList<PluginSkill> Skills,
    IReadOnlyList<PluginRecipe> Recipes,
    IReadOnlyList<PluginTool> Tools)
{
    public const string FileName = "resoloop-plugin.json";
    public const int CurrentSchemaVersion = 1;
    public const int MaxBytes = 256 * 1024;
    public const string PluginRootToken = "${pluginRoot}";
    public const string PluginDataToken = "${pluginData}";
    private const int MaxText = 500;
    private const int MaxPath = 260;

    /// <summary>Reads and validates the manifest of an unpacked plugin. <paramref name="files"/> lists every plugin file as a
    /// '/'-separated path relative to <paramref name="rootDirectory"/>; every path the manifest references must be listed.</summary>
    public static PluginManifest Load(string rootDirectory, IReadOnlyCollection<string> files)
    {
        if (!files.Contains(FileName))
            throw PluginErrors.Create(PluginErrors.ManifestNotFound, $"Plugin manifest '{FileName}' was not found in {rootDirectory}.",
                new Dictionary<string, object?> { ["rootDirectory"] = rootDirectory }, [$"Put {FileName} at the plugin root."]);
        var path = System.IO.Path.Combine(rootDirectory, FileName);
        byte[] bytes;
        try
        {
            if (new FileInfo(path).Length > MaxBytes) throw Invalid([$"$: the manifest is larger than {MaxBytes} bytes."]);
            bytes = File.ReadAllBytes(path);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw PluginErrors.Create(PluginErrors.ManifestInvalid, $"Cannot read plugin manifest '{path}': {ex.Message}", innerException: ex);
        }
        var manifest = Parse(bytes);
        var errors = new List<string>();
        manifest.ValidateFiles(rootDirectory, files as IReadOnlySet<string> ?? files.ToHashSet(StringComparer.Ordinal), errors);
        if (errors.Count > 0) throw Invalid(errors);
        return manifest;
    }

    /// <summary>Parses the manifest JSON and validates every field that does not depend on plugin files.</summary>
    public static PluginManifest Parse(byte[] utf8Json)
    {
        ReadOnlyMemory<byte> json = utf8Json;
        if (json.Span.StartsWith((ReadOnlySpan<byte>)[0xEF, 0xBB, 0xBF])) json = json[3..];
        JsonDocument document;
        try { document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 32 }); }
        catch (JsonException ex) { throw Invalid([$"$: not valid JSON: {ex.Message}"]); }
        using (document)
        {
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object) throw Invalid(["$: must be a JSON object."]);
            if (!root.TryGetProperty("schemaVersion", out var schema) || schema.ValueKind != JsonValueKind.Number ||
                !schema.TryGetInt32(out var schemaVersion))
                throw Invalid(["$.schemaVersion: is required and must be an integer."]);
            if (schemaVersion != CurrentSchemaVersion)
                throw PluginErrors.Create(PluginErrors.SchemaUnsupported,
                    $"Plugin manifest schemaVersion {schemaVersion} is not supported; this resoloop reads schemaVersion {CurrentSchemaVersion}.",
                    new Dictionary<string, object?> { ["schemaVersion"] = schemaVersion },
                    ["Use a plugin release written for this resoloop, or update resoloop."]);

            var errors = new List<string>();
            var node = Node.Of(root, "$", errors,
                ["schemaVersion", "name", "version", "description", "resoloop", "commands", "skills", "recipes", "tools"])!;
            var name = node.Name("name");
            var version = node.Version("version", required: true);
            var description = node.Text("description", required: false);
            var range = ParseRange(node.Object("resoloop", required: true, ["minVersion", "maxVersionExclusive"]));
            var commands = node.Objects("commands", 50, ["name", "description", "program", "args", "timeoutSeconds"]).Select(ParseCommand).ToArray();
            var skills = node.Objects("skills", 50, ["name", "path"]).Select(ParseSkill).ToArray();
            var recipes = node.Objects("recipes", 50,
                ["name", "path", "prototype", "purpose", "parameters", "ports", "requirements"]).Select(ParseRecipe).ToArray();
            var tools = node.Objects("tools", 20, ["name", "executable", "versionArgs", "required", "hint"]).Select(ParseTool).ToArray();
            RequireUnique("commands", commands.Select(x => x.Name), errors);
            RequireUnique("skills", skills.Select(x => x.Name), errors);
            RequireUnique("recipes", recipes.Select(x => x.Name), errors);
            RequireUnique("tools", tools.Select(x => x.Name), errors);
            if (errors.Count > 0) throw Invalid(errors);
            return new PluginManifest(schemaVersion, name!, version!, description, range!, commands, skills, recipes, tools);
        }
    }

    public void EnsureCompatibleWith(string resoloopVersion)
    {
        if (SemanticVersion.TryParse(resoloopVersion, out var current) && Resoloop.Contains(current)) return;
        throw PluginErrors.Create(PluginErrors.IncompatibleVersion,
            $"Plugin '{Name}' {Version} supports resoloop {Resoloop}; this is resoloop {resoloopVersion}.",
            new Dictionary<string, object?>
            {
                ["plugin"] = Name, ["minVersion"] = Resoloop.MinVersion.Text,
                ["maxVersionExclusive"] = Resoloop.MaxVersionExclusive?.Text, ["resoloopVersion"] = resoloopVersion
            },
            ["Install a plugin release that supports this resoloop version, or change resoloop."]);
    }

    /// <summary>A '/'-separated relative path that cannot leave the plugin root on any supported platform.</summary>
    public static bool IsSafeRelativePath(string path) =>
        path.Length is > 0 and <= MaxPath && !path.StartsWith('/') && !path.Contains('\\') && !path.Contains(':') &&
        !path.Any(char.IsControl) && path.Split('/').All(segment => segment.Length > 0 && segment is not "." and not "..");

    internal static bool IsCommandName(string text) => CommandNamePattern().IsMatch(text) && text.Trim('.').Length > 0;

    private void ValidateFiles(string rootDirectory, IReadOnlySet<string> files, List<string> errors)
    {
        for (var i = 0; i < Commands.Count; i++)
            if (Commands[i].Program.StartsWith("./", StringComparison.Ordinal) && !files.Contains(Commands[i].Program[2..]))
                errors.Add($"$.commands[{i}].program: '{Commands[i].Program}' is not a file in the plugin.");
        for (var i = 0; i < Skills.Count; i++)
            if (!files.Contains(Skills[i].Path + "/SKILL.md"))
                errors.Add($"$.skills[{i}].path: '{Skills[i].Path}/SKILL.md' is not a file in the plugin.");
        for (var i = 0; i < Recipes.Count; i++)
        {
            var recipe = Recipes[i];
            var where = $"$.recipes[{i}].path";
            if (!files.Contains(recipe.Path))
            {
                errors.Add($"{where}: '{recipe.Path}' is not a file in the plugin.");
                continue;
            }
            try
            {
                var full = System.IO.Path.Combine(rootDirectory, recipe.Path.Replace('/', System.IO.Path.DirectorySeparatorChar));
                if (JsonNode.Parse(File.ReadAllText(full)) is not JsonObject root ||
                    root["prototypes"] is not JsonObject prototypes || prototypes[recipe.Prototype] is not JsonObject)
                    errors.Add($"{where}: '{recipe.Path}' must be a JSON object whose prototypes.{recipe.Prototype} is an object.");
            }
            catch (Exception ex) when (ex is JsonException or ArgumentException or IOException or UnauthorizedAccessException)
            {
                errors.Add($"{where}: cannot read '{recipe.Path}' as JSON: {ex.Message}");
            }
        }
    }

    private static PluginVersionRange? ParseRange(Node? node)
    {
        if (node is null) return null;
        var min = node.Version("minVersion", required: true);
        var max = node.Version("maxVersionExclusive", required: false);
        if (min is not null && max is not null && max.CompareTo(min) <= 0)
            node.Error("maxVersionExclusive", "must be greater than minVersion.");
        return min is null ? null : new PluginVersionRange(min, max);
    }

    private static PluginCommand ParseCommand(Node node)
    {
        var name = node.Name("name");
        var description = node.Text("description", required: true);
        var program = node.Text("program", required: true, MaxPath);
        if (program is not null && !(program.StartsWith("./", StringComparison.Ordinal) ? IsSafeRelativePath(program[2..]) : IsCommandName(program)))
            node.Error("program", "must be './<relative path in the plugin>' or a command name on PATH ([A-Za-z0-9._+-], no path separators).");
        var args = node.Strings("args");
        for (var i = 0; i < args.Count; i++)
            if (args[i].Replace(PluginRootToken, "", StringComparison.Ordinal).Replace(PluginDataToken, "", StringComparison.Ordinal)
                .Contains("${", StringComparison.Ordinal))
                node.Error($"args[{i}]", $"only {PluginRootToken} and {PluginDataToken} may be substituted.");
        var timeout = node.Integer("timeoutSeconds", 1, 86400);
        return new PluginCommand(name!, description!, program!, args, timeout);
    }

    private static PluginSkill ParseSkill(Node node) => new(node.Name("name")!, node.RelativePath("path")!);

    private static PluginRecipe ParseRecipe(Node node)
    {
        var name = node.Name("name");
        var path = node.RelativePath("path");
        var prototype = node.Text("prototype", required: true, 100);
        var purpose = node.Text("purpose", required: true);
        var parameters = node.Map("parameters", required: true);
        if (node.Has("parameters") && !parameters.ContainsKey("key")) node.Error("parameters", "must include 'key'.");
        var ports = node.Map("ports", required: false);
        var requirements = node.Strings("requirements");
        return new PluginRecipe(name!, path!, prototype!, purpose!, parameters, ports, requirements);
    }

    private static PluginTool ParseTool(Node node)
    {
        var name = node.Name("name");
        var executable = node.Text("executable", required: true, 100);
        if (executable is not null && !IsCommandName(executable))
            node.Error("executable", "must be a command name on PATH ([A-Za-z0-9._+-], no path separators).");
        var versionArgs = node.Strings("versionArgs");
        var required = node.Boolean("required") ?? true;
        var hint = node.Text("hint", required: false);
        return new PluginTool(name!, executable!, versionArgs, required, hint);
    }

    private static void RequireUnique(string list, IEnumerable<string?> names, List<string> errors) =>
        errors.AddRange(names.OfType<string>().GroupBy(name => name, StringComparer.Ordinal).Where(group => group.Count() > 1)
            .Select(group => $"$.{list}: name '{group.Key}' is duplicated."));

    private static RLoopException Invalid(IReadOnlyList<string> errors) =>
        PluginErrors.Create(PluginErrors.ManifestInvalid,
            $"Plugin manifest is invalid: {errors[0]}" + (errors.Count > 1 ? $" (+{errors.Count - 1} more)" : ""),
            new Dictionary<string, object?> { ["errors"] = errors }, [$"Fix every listed field in {FileName}."]);

    [GeneratedRegex(@"^[A-Za-z0-9._+][A-Za-z0-9._+-]{0,99}\z", RegexOptions.CultureInvariant)]
    private static partial Regex CommandNamePattern();

    /// <summary>One JSON object being validated. Errors are collected with JSON paths instead of stopping at the first.</summary>
    private sealed class Node
    {
        private readonly Dictionary<string, JsonElement> _fields;
        private readonly List<string> _errors;

        private Node(string path, Dictionary<string, JsonElement> fields, List<string> errors)
        {
            Path = path;
            _fields = fields;
            _errors = errors;
        }

        public string Path { get; }

        public static Node? Of(JsonElement element, string path, List<string> errors, IReadOnlyCollection<string> allowed)
        {
            if (element.ValueKind != JsonValueKind.Object)
            {
                errors.Add($"{path}: must be an object.");
                return null;
            }
            var fields = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!allowed.Contains(property.Name)) errors.Add($"{path}.{property.Name}: is not a known field.");
                else if (!fields.TryAdd(property.Name, property.Value)) errors.Add($"{path}.{property.Name}: is duplicated.");
            }
            return new Node(path, fields, errors);
        }

        public bool Has(string name) => _fields.ContainsKey(name);

        public void Error(string field, string message) => _errors.Add($"{Path}.{field}: {message}");

        public string? Text(string name, bool required, int maxLength = MaxText)
        {
            if (!TryGet(name, required, out var value)) return null;
            if (value.ValueKind == JsonValueKind.String && value.GetString() is { Length: > 0 } text && text.Length <= maxLength) return text;
            Error(name, $"must be a string of 1..{maxLength} characters.");
            return null;
        }

        public string? Name(string name)
        {
            if (!TryGet(name, required: true, out var value)) return null;
            if (value.ValueKind == JsonValueKind.String && PluginNames.IsValid(value.GetString())) return value.GetString();
            Error(name, $"must be a string matching {PluginNames.Rule}.");
            return null;
        }

        public string? RelativePath(string name)
        {
            var path = Text(name, required: true, MaxPath);
            if (path is null || IsSafeRelativePath(path)) return path;
            Error(name, "must be a '/'-separated relative path inside the plugin (no '..', '.', '\\', ':' or leading '/').");
            return null;
        }

        public SemanticVersion? Version(string name, bool required)
        {
            var text = Text(name, required, 128);
            if (text is null) return null;
            if (SemanticVersion.TryParse(text, out var version)) return version;
            Error(name, $"'{text}' is not a SemVer 2.0 version.");
            return null;
        }

        public int? Integer(string name, int min, int max)
        {
            if (!TryGet(name, required: false, out var value)) return null;
            if (value.ValueKind == JsonValueKind.Number && value.TryGetInt32(out var number) && number >= min && number <= max) return number;
            Error(name, $"must be an integer in {min}..{max}.");
            return null;
        }

        public bool? Boolean(string name)
        {
            if (!TryGet(name, required: false, out var value)) return null;
            if (value.ValueKind is JsonValueKind.True or JsonValueKind.False) return value.GetBoolean();
            Error(name, "must be true or false.");
            return null;
        }

        public IReadOnlyList<string> Strings(string name)
        {
            if (!TryGet(name, required: false, out var value)) return [];
            if (value.ValueKind != JsonValueKind.Array)
            {
                Error(name, "must be an array of strings.");
                return [];
            }
            var result = new List<string>();
            var index = 0;
            foreach (var item in value.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String) result.Add(item.GetString()!);
                else Error($"{name}[{index}]", "must be a string.");
                index++;
            }
            return result;
        }

        public IReadOnlyDictionary<string, string> Map(string name, bool required)
        {
            var map = new Dictionary<string, string>(StringComparer.Ordinal);
            if (!TryGet(name, required, out var value)) return map;
            if (value.ValueKind != JsonValueKind.Object)
            {
                Error(name, "must be an object whose values are strings.");
                return map;
            }
            foreach (var property in value.EnumerateObject())
            {
                if (property.Value.ValueKind != JsonValueKind.String || property.Value.GetString() is not { Length: > 0 and <= MaxText } text)
                    Error($"{name}.{property.Name}", $"must be a string of 1..{MaxText} characters.");
                else if (property.Name.Length == 0 || !map.TryAdd(property.Name, text))
                    Error($"{name}.{property.Name}", "must be a unique, non-empty key.");
            }
            return map;
        }

        public Node? Object(string name, bool required, IReadOnlyCollection<string> allowed) =>
            TryGet(name, required, out var value) ? Of(value, $"{Path}.{name}", _errors, allowed) : null;

        public IReadOnlyList<Node> Objects(string name, int maxItems, IReadOnlyCollection<string> allowed)
        {
            if (!TryGet(name, required: false, out var value)) return [];
            if (value.ValueKind != JsonValueKind.Array || value.GetArrayLength() > maxItems)
            {
                Error(name, $"must be an array of at most {maxItems} objects.");
                return [];
            }
            return value.EnumerateArray().Select((item, index) => Of(item, $"{Path}.{name}[{index}]", _errors, allowed))
                .OfType<Node>().ToArray();
        }

        private bool TryGet(string name, bool required, out JsonElement value)
        {
            if (_fields.TryGetValue(name, out value)) return true;
            if (required) Error(name, "is required.");
            return false;
        }
    }
}
```

- [ ] **Step 7: テストが通ることを確かめる**

Run: 共通の検証コマンド
Expected: `PluginManifestTests` が全部 PASS

- [ ] **Step 8: Commit**

```bash
git add src/RLoop.Core/Plugins tests/RLoop.Tests/PluginManifestTests.cs tests/fixtures/plugins
git commit -m "feat(plugins): add plugin manifest v1 with name and version rules"
```

### Task 2: 記録と `PluginRegistry`（一覧と照合）

テスト: 要る。記録の読み込み、ファイルの照合（内容・欠け・余分・symlink）、版、衝突、例外の分岐を実行して確かめる。

**Files:**
- Create: `src/RLoop.Core/Plugins/PluginRegistry.cs`
- Test: `tests/RLoop.Tests/PluginRegistryTests.cs`

**Interfaces:**
- Consumes: Task 1 の `PluginManifest.Load`・`EnsureCompatibleWith`・`IsSafeRelativePath`、`PluginNames`、`PluginErrors`、テストの `PluginFixture`
- Produces: `PluginSource(string Kind, string Location, string? Ref)`（`DirectoryKind`・`GitKind`）、`PluginInstallRecord`（`Read(path)`・`Write(path)`・`FileName`）、`PluginProblem`、`PluginStatus`、`InstalledPlugin`、`PluginRegistry`（`FindProjectRoot`・`List`・`LoadAll`・`Load`・`PluginsDirectory`・`ResoloopVersion`・`PackageDirectoryName`・`DataDirectoryName`）、internal `PluginFiles.Sha256(string)`・`PluginFiles.Scan(string, Func<string, bool>?)`・`PluginFiles.Shallow`

- [ ] **Step 1: 失敗するテストを書く**

<!-- file: tests/RLoop.Tests/PluginRegistryTests.cs -->
```csharp
using RLoop.Core;
using RLoop.Core.Plugins;

namespace RLoop.Tests;

public sealed class PluginRegistryTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "resoloop-plugin-registry-tests-" + Guid.NewGuid().ToString("N"));
    private readonly string _project;
    private readonly PluginRegistry _registry;

    public PluginRegistryTests()
    {
        _project = PluginFixture.CreateProject(Path.Combine(_root, "project"));
        _registry = new PluginRegistry(_project, PluginFixture.ResoloopVersion);
    }

    [Fact]
    public void ListsNothingBeforeAnyPluginIsInstalled()
    {
        Assert.Empty(_registry.List());
        Assert.Empty(_registry.LoadAll());
    }

    [Fact]
    public void VerifiesAndLoadsAnInstalledPlugin()
    {
        var installDirectory = Install("sample-plugin");

        var status = Assert.Single(_registry.List());
        var plugin = _registry.Load("sample-plugin");

        Assert.True(status.Ok);
        Assert.Equal("1.2.3", status.Record!.Version);
        Assert.Equal(Path.Combine(installDirectory, "package"), plugin.PackageDirectory);
        Assert.Equal(Path.Combine(installDirectory, "data"), plugin.DataDirectory);
        Assert.Equal("sample-hello", plugin.Manifest.Commands[0].Name);
        Assert.Equal("sample-plugin", Assert.Single(_registry.LoadAll()).Name);
    }

    [Theory]
    [InlineData("changed", "scripts/hello.sh")]
    [InlineData("missing", "skills/sample-skill/SKILL.md")]
    [InlineData("unexpected", "json.py")]
    [InlineData("unexpected", ".hidden")]
    public void RefusesAPluginWhoseFilesChangedAfterInstall(string kind, string path)
    {
        var package = Path.Combine(Install("sample-plugin"), "package");
        var file = Path.Combine(package, path);
        if (kind == "missing") File.Delete(file);
        else File.AppendAllText(file, "print('injected')\n");

        var status = Assert.Single(_registry.List());
        var load = Assert.Throws<RLoopException>(() => _registry.Load("sample-plugin"));
        var loadAll = Assert.Throws<RLoopException>(() => _registry.LoadAll());

        Assert.Equal("PLUGIN_MODIFIED", status.Problem!.Code);
        Assert.Contains(path, Assert.IsAssignableFrom<IEnumerable<string>>(status.Problem.Details[kind]));
        Assert.Equal("PLUGIN_MODIFIED", load.Code);
        Assert.Equal("PLUGIN_MODIFIED", loadAll.Code);
        Assert.Equal(ExitCodes.ValidationFailed, load.ExitCode);
    }

    [Fact]
    public void RefusesALinkInsideThePackage()
    {
        var package = Path.Combine(Install("sample-plugin"), "package");
        var outside = Directory.CreateDirectory(Path.Combine(_root, "outside")).FullName;
        if (!TryCreateDirectoryLink(Path.Combine(package, "linked"), outside)) return; // Symlinks need privileges on some Windows hosts.

        var status = Assert.Single(_registry.List());

        Assert.Equal("PLUGIN_MODIFIED", status.Problem!.Code);
        Assert.Contains("linked", Assert.IsAssignableFrom<IEnumerable<string>>(status.Problem.Details["links"]));
    }

    [Fact]
    public void ReportsAnUnreadableOrMismatchedRecord()
    {
        File.WriteAllText(Path.Combine(Install("sample-plugin"), "install.json"), "{ not json");
        var renamed = Install("other-plugin");
        Directory.Move(renamed, Path.Combine(_registry.PluginsDirectory, "third-plugin"));

        var statuses = _registry.List();

        Assert.All(statuses, status => Assert.Equal("PLUGIN_RECORD_INVALID", status.Problem!.Code));
        Assert.Equal(["sample-plugin", "third-plugin"], statuses.Select(status => status.Name));
    }

    [Fact]
    public void ReportsAPluginThatNoLongerSupportsTheRunningResoloop()
    {
        Install("sample-plugin");

        var upgraded = new PluginRegistry(_project, "0.2.0");

        Assert.Equal("PLUGIN_INCOMPATIBLE_VERSION", Assert.Single(upgraded.List()).Problem!.Code);
        Assert.Equal("PLUGIN_INCOMPATIBLE_VERSION", Assert.Throws<RLoopException>(() => upgraded.LoadAll()).Code);
    }

    [Fact]
    public void IgnoresStagingDirectories()
    {
        Directory.CreateDirectory(Path.Combine(_registry.PluginsDirectory, ".staging-0123"));

        Assert.Empty(_registry.List());
    }

    [Fact]
    public void LoadReportsMissingAndInvalidNames()
    {
        Assert.Equal("PLUGIN_NOT_INSTALLED", Assert.Throws<RLoopException>(() => _registry.Load("absent-plugin")).Code);
        Assert.Equal("PLUGIN_NAME_INVALID", Assert.Throws<RLoopException>(() => _registry.Load("../outside")).Code);
    }

    [Fact]
    public void LoadAllRefusesPluginsThatProvideTheSameNames()
    {
        Install("sample-plugin");
        Install("other-plugin");

        Assert.All(_registry.List(), status => Assert.True(status.Ok));
        var ex = Assert.Throws<RLoopException>(() => _registry.LoadAll());

        Assert.Equal("PLUGIN_NAME_CONFLICT", ex.Code);
    }

    [Fact]
    public void FindsTheNearestProjectOrTheExplicitOne()
    {
        var nested = Directory.CreateDirectory(Path.Combine(_project, "content", "deep")).FullName;
        var outside = Directory.CreateDirectory(Path.Combine(_root, "not-a-project")).FullName;

        Assert.Equal(_project, PluginRegistry.FindProjectRoot(null, nested));
        Assert.Equal(_project, PluginRegistry.FindProjectRoot(_project, outside));
        var ex = Assert.Throws<RLoopException>(() => PluginRegistry.FindProjectRoot(outside, nested));
        Assert.Equal("PLUGIN_PROJECT_NOT_FOUND", ex.Code);
        Assert.Equal(ExitCodes.ConfigurationError, ex.ExitCode);
    }

    public void Dispose() => PluginFixture.DeleteDirectory(_root);

    // Builds an install directory by hand so these tests do not depend on PluginInstaller.
    private string Install(string name)
    {
        var installDirectory = Path.Combine(_registry.PluginsDirectory, name);
        var package = PluginFixture.CopySample(Path.Combine(installDirectory, "package"));
        PluginFixture.EditManifest(package, json => json["name"] = name);
        var files = PluginFixture.Files(package).Order(StringComparer.Ordinal)
            .ToDictionary(file => file, file => PluginFiles.Sha256(Path.Combine(package, file)), StringComparer.Ordinal);
        new PluginInstallRecord(1, name, "1.2.3", new PluginSource(PluginSource.DirectoryKind, PluginFixture.SamplePath, null), null,
            "2026-10-16T00:00:00Z", PluginFixture.ResoloopVersion, files).Write(Path.Combine(installDirectory, "install.json"));
        return installDirectory;
    }

    private static bool TryCreateDirectoryLink(string path, string target)
    {
        try
        {
            Directory.CreateSymbolicLink(path, target);
            return true;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }
}
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: 共通の検証コマンド
Expected: ビルドが `PluginRegistry`・`PluginInstallRecord`・`PluginFiles` の未定義で失敗する

- [ ] **Step 3: 記録と registry を実装する**

<!-- file: src/RLoop.Core/Plugins/PluginRegistry.cs -->
```csharp
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace RLoop.Core.Plugins;

public sealed record PluginSource(string Kind, string Location, string? Ref)
{
    public const string DirectoryKind = "directory";
    public const string GitKind = "git";
}

/// <summary>install.json: where a plugin came from and the SHA-256 of every file copied into package/.</summary>
public sealed record PluginInstallRecord(
    int SchemaVersion,
    string Name,
    string Version,
    PluginSource Source,
    string? Commit,
    string InstalledAt,
    string ResoloopVersion,
    IReadOnlyDictionary<string, string> Files)
{
    public const string FileName = "install.json";
    public const int CurrentSchemaVersion = 1;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    public static PluginInstallRecord Read(string path)
    {
        PluginInstallRecord? record;
        try
        {
            record = JsonSerializer.Deserialize<PluginInstallRecord>(File.ReadAllBytes(path), JsonOptions);
        }
        catch (Exception ex) when (ex is JsonException or NotSupportedException or IOException or UnauthorizedAccessException)
        {
            throw Invalid(path, ex.Message, ex);
        }
        var problem = record is null ? "the record is empty." : record.Problem();
        if (problem is not null) throw Invalid(path, problem);
        return record!;
    }

    public void Write(string path)
    {
        var sorted = this with { Files = new SortedDictionary<string, string>(Files.ToDictionary(), StringComparer.Ordinal) };
        File.WriteAllText(path, JsonSerializer.Serialize(sorted, JsonOptions) + "\n", new UTF8Encoding(false));
    }

    // Deserialization does not enforce non-nullable members, so every field is checked here.
    private string? Problem()
    {
        if (SchemaVersion != CurrentSchemaVersion) return $"schemaVersion {SchemaVersion} is not supported.";
        if (!PluginNames.IsValid(Name)) return "name is invalid.";
        if (!SemanticVersion.TryParse(Version, out _)) return "version is invalid.";
        if (Source is null || Source.Kind is not (PluginSource.DirectoryKind or PluginSource.GitKind) || string.IsNullOrWhiteSpace(Source.Location))
            return "source is invalid.";
        if (Source.Kind == PluginSource.GitKind && (Commit is null || Commit.Length is not (40 or 64) || !Commit.All(char.IsAsciiHexDigitLower)))
            return "commit is invalid.";
        if (Files is null || Files.Count == 0) return "files is empty.";
        foreach (var (file, hash) in Files)
            if (!PluginManifest.IsSafeRelativePath(file) || hash is not { Length: 64 } || !hash.All(char.IsAsciiHexDigitLower))
                return $"files entry '{file}' is invalid.";
        return null;
    }

    private static RLoopException Invalid(string path, string reason, Exception? innerException = null) =>
        PluginErrors.Create(PluginErrors.RecordInvalid, $"Cannot use plugin record '{path}': {reason}",
            new Dictionary<string, object?> { ["path"] = path },
            ["Remove the plugin with resoloop plugin remove NAME --yes and install it again."], innerException);
}

public sealed record PluginProblem(string Code, string Message, IReadOnlyDictionary<string, object?> Details,
    IReadOnlyList<string> Suggestions);

public sealed record PluginStatus(string Name, string InstallDirectory, PluginInstallRecord? Record, PluginManifest? Manifest,
    PluginProblem? Problem)
{
    public bool Ok => Problem is null;
}

public sealed record InstalledPlugin(string Name, string InstallDirectory, string PackageDirectory, string DataDirectory,
    PluginManifest Manifest, PluginInstallRecord Record);

/// <summary>Plugins installed in one project under .resoloop/plugins. Use <see cref="Load"/> or <see cref="LoadAll"/> before
/// using a plugin: both verify every file against install.json and never return a modified plugin.</summary>
public sealed class PluginRegistry
{
    public const string PackageDirectoryName = "package";
    public const string DataDirectoryName = "data";

    public PluginRegistry(string projectRoot, string resoloopVersion)
    {
        ProjectRoot = Path.GetFullPath(projectRoot);
        PluginsDirectory = Path.Combine(ProjectRoot, ".resoloop", "plugins");
        ResoloopVersion = resoloopVersion;
    }

    public string ProjectRoot { get; }
    public string PluginsDirectory { get; }
    public string ResoloopVersion { get; }

    public static string FindProjectRoot(string? explicitProject, string startDirectory)
    {
        if (explicitProject is not null)
        {
            var root = Path.GetFullPath(explicitProject, Path.GetFullPath(startDirectory));
            if (File.Exists(Path.Combine(root, ConfigResolver.ProjectFileName))) return root;
            throw ProjectNotFound($"--project {root} has no {ConfigResolver.ProjectFileName}.", root);
        }
        var config = ConfigResolver.FindProjectConfigPath(startDirectory);
        return config is not null
            ? Path.GetDirectoryName(config)!
            : throw ProjectNotFound($"No {ConfigResolver.ProjectFileName} was found in {Path.GetFullPath(startDirectory)} or its parents.",
                Path.GetFullPath(startDirectory));
    }

    /// <summary>Every installed plugin with the result of verification. Problems are reported per plugin, never thrown.</summary>
    public IReadOnlyList<PluginStatus> List()
    {
        if (!Directory.Exists(PluginsDirectory)) return [];
        return new DirectoryInfo(PluginsDirectory).EnumerateFileSystemInfos("*", PluginFiles.Shallow)
            .Where(entry => !entry.Name.StartsWith('.'))
            .OrderBy(entry => entry.Name, StringComparer.Ordinal)
            .Select(Inspect)
            .ToArray();
    }

    /// <summary>All plugins, only when every one of them is verified and no two provide the same name.</summary>
    public IReadOnlyList<InstalledPlugin> LoadAll()
    {
        var statuses = List();
        var broken = statuses.Where(status => !status.Ok).ToArray();
        if (broken.Length > 0) throw ToException(broken[0], broken);
        var plugins = statuses.Select(ToInstalled).ToArray();
        for (var i = 1; i < plugins.Length; i++)
        {
            var conflicts = PluginNames.FindConflicts(plugins[i].Manifest, plugins.Take(i).Select(plugin => plugin.Manifest));
            if (conflicts.Count > 0)
                throw PluginErrors.Create(PluginErrors.NameConflict,
                    $"Plugin '{plugins[i].Name}' conflicts with another installed plugin: {conflicts[0]}",
                    new Dictionary<string, object?> { ["plugin"] = plugins[i].Name, ["conflicts"] = conflicts },
                    ["Remove one of the conflicting plugins with resoloop plugin remove NAME --yes."]);
        }
        return plugins;
    }

    public InstalledPlugin Load(string name)
    {
        if (!PluginNames.IsValid(name))
            throw PluginErrors.Create(PluginErrors.NameInvalid, $"'{name}' is not a plugin name ({PluginNames.Rule}).");
        var path = Path.Combine(PluginsDirectory, name);
        FileSystemInfo entry = Directory.Exists(path) ? new DirectoryInfo(path) : new FileInfo(path);
        if (!entry.Exists && entry.LinkTarget is null)
            throw PluginErrors.Create(PluginErrors.NotInstalled, $"Plugin '{name}' is not installed in {ProjectRoot}.",
                new Dictionary<string, object?> { ["plugin"] = name }, ["Run resoloop plugin list --json."]);
        var status = Inspect(entry);
        return status.Ok ? ToInstalled(status) : throw ToException(status, [status]);
    }

    private PluginStatus Inspect(FileSystemInfo entry)
    {
        PluginInstallRecord? record = null;
        PluginManifest? manifest = null;
        try
        {
            if (entry is not DirectoryInfo || entry.LinkTarget is not null)
                throw RecordInvalid(entry.Name, "the entry is not a real directory.");
            if (!PluginNames.IsValid(entry.Name))
                throw RecordInvalid(entry.Name, $"the directory name does not match {PluginNames.Rule}.");
            record = PluginInstallRecord.Read(Path.Combine(entry.FullName, PluginInstallRecord.FileName));
            if (record.Name != entry.Name) throw RecordInvalid(entry.Name, $"{PluginInstallRecord.FileName} names '{record.Name}'.");
            var package = Path.Combine(entry.FullName, PackageDirectoryName);
            VerifyFiles(entry.Name, package, record.Files);
            manifest = PluginManifest.Load(package, record.Files.Keys.ToHashSet(StringComparer.Ordinal));
            if (manifest.Name != record.Name || manifest.Version.Text != record.Version)
                throw RecordInvalid(entry.Name,
                    $"the manifest declares {manifest.Name} {manifest.Version}, but {PluginInstallRecord.FileName} records {record.Name} {record.Version}.");
            manifest.EnsureCompatibleWith(ResoloopVersion);
            var conflicts = PluginNames.FindConflicts(manifest, []);
            if (conflicts.Count > 0)
                throw PluginErrors.Create(PluginErrors.NameConflict, $"Plugin '{entry.Name}' uses a reserved name: {conflicts[0]}",
                    new Dictionary<string, object?> { ["plugin"] = entry.Name, ["conflicts"] = conflicts },
                    ["Remove the plugin and install a release that does not use built-in names."]);
            return new PluginStatus(entry.Name, entry.FullName, record, manifest, null);
        }
        catch (RLoopException ex) when (ex.Code.StartsWith("PLUGIN_", StringComparison.Ordinal))
        {
            return new PluginStatus(entry.Name, entry.FullName, record, manifest,
                new PluginProblem(ex.Code, ex.Message, ex.Context, ex.Suggestions));
        }
    }

    private static void VerifyFiles(string name, string package, IReadOnlyDictionary<string, string> expected)
    {
        List<string> files = [], links = [];
        try
        {
            if (Directory.Exists(package)) (files, links) = PluginFiles.Scan(package);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            throw PluginErrors.Create(PluginErrors.Modified, $"Cannot read plugin '{name}' files in {package}: {ex.Message}",
                new Dictionary<string, object?> { ["plugin"] = name }, innerException: ex);
        }
        var changed = new List<string>();
        foreach (var file in files.Where(expected.ContainsKey))
        {
            try
            {
                if (PluginFiles.Sha256(Path.Combine(package, file)) != expected[file]) changed.Add(file);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                changed.Add(file);
            }
        }
        var missing = expected.Keys.Except(files, StringComparer.Ordinal).Order(StringComparer.Ordinal).ToArray();
        var unexpected = files.Where(file => !expected.ContainsKey(file)).ToArray();
        if (changed.Count + missing.Length + unexpected.Length + links.Count == 0) return;
        throw PluginErrors.Create(PluginErrors.Modified,
            $"Plugin '{name}' changed after it was installed ({changed.Count} changed, {missing.Length} missing, " +
            $"{unexpected.Length} unexpected, {links.Count} links).",
            new Dictionary<string, object?>
            {
                ["plugin"] = name, ["changed"] = changed, ["missing"] = missing, ["unexpected"] = unexpected, ["links"] = links
            },
            [$"Reinstall it: resoloop plugin remove {name} --yes, then resoloop plugin install SOURCE.",
             "Plugins must write runtime files under their data directory, never under package/."]);
    }

    private static InstalledPlugin ToInstalled(PluginStatus status) => new(status.Name, status.InstallDirectory,
        Path.Combine(status.InstallDirectory, PackageDirectoryName), Path.Combine(status.InstallDirectory, DataDirectoryName),
        status.Manifest!, status.Record!);

    private static RLoopException ToException(PluginStatus status, IReadOnlyList<PluginStatus> all)
    {
        var problem = status.Problem!;
        var context = new Dictionary<string, object?>(problem.Details)
        {
            ["plugin"] = status.Name,
            ["problems"] = all.Select(item => new Dictionary<string, object?>
            {
                ["name"] = item.Name, ["code"] = item.Problem!.Code, ["message"] = item.Problem.Message
            }).ToArray()
        };
        return PluginErrors.Create(problem.Code, problem.Message, context, problem.Suggestions);
    }

    private static RLoopException RecordInvalid(string name, string reason) =>
        PluginErrors.Create(PluginErrors.RecordInvalid, $"Plugin '{name}' has an invalid install record: {reason}",
            new Dictionary<string, object?> { ["plugin"] = name },
            [$"Remove it with resoloop plugin remove {name} --yes and install it again."]);

    private static RLoopException ProjectNotFound(string message, string directory) =>
        PluginErrors.Create(PluginErrors.ProjectNotFound, message, new Dictionary<string, object?> { ["directory"] = directory },
            ["Run the command inside a resoloop project, pass --project DIR, or create one with resoloop init."]);
}

internal static class PluginFiles
{
    public static readonly EnumerationOptions Shallow = new() { AttributesToSkip = 0, RecurseSubdirectories = false };

    public static string Sha256(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        return Convert.ToHexStringLower(SHA256.HashData(stream));
    }

    /// <summary>Files below <paramref name="root"/> as sorted '/'-separated relative paths. Links (symlinks, junctions) are never
    /// followed and are returned separately so callers can refuse them. <paramref name="skip"/> drops entries by relative path.</summary>
    public static (List<string> Files, List<string> Links) Scan(string root, Func<string, bool>? skip = null)
    {
        var files = new List<string>();
        var links = new List<string>();
        void Walk(DirectoryInfo directory, string prefix)
        {
            foreach (var entry in directory.EnumerateFileSystemInfos("*", Shallow))
            {
                var relative = prefix + entry.Name;
                if (skip?.Invoke(relative) == true) continue;
                if (entry.LinkTarget is not null || entry.Attributes.HasFlag(FileAttributes.ReparsePoint)) links.Add(relative);
                else if (entry is DirectoryInfo child) Walk(child, relative + "/");
                else files.Add(relative);
            }
        }
        Walk(new DirectoryInfo(root), "");
        files.Sort(StringComparer.Ordinal);
        links.Sort(StringComparer.Ordinal);
        return (files, links);
    }
}
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: 共通の検証コマンド
Expected: `PluginManifestTests` と `PluginRegistryTests` が全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Core/Plugins/PluginRegistry.cs tests/RLoop.Tests/PluginRegistryTests.cs
git commit -m "feat(plugins): add install records and a verifying plugin registry"
```

### Task 3: 導入と削除（ディレクトリ・Git）

テスト: 要る。導入元の判定、Git の解決、写すファイルの選び方、導入前の拒否、失敗後の後始末、削除の範囲を実行して確かめる。Git はテストの中で `git init` した一時リポジトリを `file://` で使い、ネットワークを使わない。

**Files:**
- Create: `src/RLoop.Core/Plugins/PluginGit.cs`、`src/RLoop.Core/Plugins/PluginInstaller.cs`
- Test: `tests/RLoop.Tests/PluginInstallerTests.cs`

**Interfaces:**
- Consumes: Task 1・2 の型と `PluginFiles`、テストの `PluginFixture`
- Produces: `PluginInstaller.InstallAsync(PluginRegistry, string source, string? gitRef, CancellationToken)` → `PluginInstallResult(Name, Version, Source, Commit, InstallDirectory, FileCount)`、`PluginInstaller.Remove(PluginRegistry, string name)` → `PluginRemoveResult(Name, RemovedDirectory, Note)`、internal `PluginInstaller.DeleteTree(string)`、internal `PluginGit.RunAsync`・`ListWorkTreeFilesAsync`・`CheckoutAsync`

- [ ] **Step 1: 失敗するテストを書く**

<!-- file: tests/RLoop.Tests/PluginInstallerTests.cs -->
```csharp
using System.Diagnostics;
using System.Text.Json.Nodes;
using RLoop.Core;
using RLoop.Core.Plugins;

namespace RLoop.Tests;

public sealed class PluginInstallerTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "resoloop-plugin-installer-tests-" + Guid.NewGuid().ToString("N"));
    private readonly string _project;
    private readonly PluginRegistry _registry;

    public PluginInstallerTests()
    {
        _project = PluginFixture.CreateProject(Path.Combine(_root, "project"));
        _registry = new PluginRegistry(_project, PluginFixture.ResoloopVersion);
    }

    [Fact]
    public async Task InstallsFromADirectoryAndRecordsEveryFile()
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, "source"));

        var result = await PluginInstaller.InstallAsync(_registry, source, null);

        var plugin = _registry.Load("sample-plugin");
        Assert.Equal("1.2.3", result.Version);
        Assert.Equal(Path.Combine(_registry.PluginsDirectory, "sample-plugin"), result.InstallDirectory);
        Assert.Equal(new PluginSource("directory", Path.GetFullPath(source), null), plugin.Record.Source);
        Assert.Null(plugin.Record.Commit);
        Assert.Equal(PluginFixture.Files(source).Order(StringComparer.Ordinal), plugin.Record.Files.Keys);
        Assert.Equal(PluginFixture.ResoloopVersion, plugin.Record.ResoloopVersion);
        Assert.Equal(["sample-plugin"], PluginsDirectoryEntries());
    }

    [Fact]
    public async Task CopiesOnlyFilesGitWouldTrackFromAWorkTree()
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, "source"));
        Git(source, "init", "-q", "-b", "main");
        File.WriteAllText(Path.Combine(source, ".gitignore"), ".venv/\nignored.txt\n");
        Directory.CreateDirectory(Path.Combine(source, ".venv", "bin"));
        File.WriteAllText(Path.Combine(source, ".venv", "bin", "python"), "binary");
        File.WriteAllText(Path.Combine(source, "ignored.txt"), "local only");
        File.WriteAllText(Path.Combine(source, "untracked.txt"), "new file");

        await PluginInstaller.InstallAsync(_registry, source, null);

        var files = _registry.Load("sample-plugin").Record.Files.Keys.ToArray();
        Assert.Contains("untracked.txt", files);
        Assert.Contains(".gitignore", files);
        Assert.DoesNotContain("ignored.txt", files);
        Assert.DoesNotContain(files, file => file.StartsWith(".venv/", StringComparison.Ordinal) || file.StartsWith(".git/", StringComparison.Ordinal));
    }

    [Fact]
    public async Task CopiesEveryFileFromADirectoryThatAnEnclosingRepositoryIgnores()
    {
        var outer = Directory.CreateDirectory(Path.Combine(_root, "outer")).FullName;
        Git(outer, "init", "-q", "-b", "main");
        File.WriteAllText(Path.Combine(outer, ".gitignore"), "plugins/\n");
        var source = PluginFixture.CopySample(Path.Combine(outer, "plugins", "sample"));

        await PluginInstaller.InstallAsync(_registry, source, null);

        Assert.Equal(PluginFixture.Files(source).Order(StringComparer.Ordinal), _registry.Load("sample-plugin").Record.Files.Keys);
    }

    [Theory]
    [InlineData("v1", "first")]
    [InlineData("main", "second")]
    [InlineData("feature", "first")]
    [InlineData("<first-commit>", "first")]
    public async Task InstallsFromAGitUrlPinnedByTagBranchOrCommit(string gitRef, string expected)
    {
        var (url, first, second) = CreateRepository();
        if (gitRef == "<first-commit>") gitRef = first;

        var result = await PluginInstaller.InstallAsync(_registry, url, gitRef);

        var plugin = _registry.Load("sample-plugin");
        Assert.Equal(expected == "first" ? first : second, result.Commit);
        Assert.Equal(expected == "first" ? "1.2.3" : "1.3.0", plugin.Manifest.Version.Text);
        Assert.Equal(new PluginSource("git", url, gitRef), plugin.Record.Source);
        Assert.Equal(result.Commit, plugin.Record.Commit);
        Assert.False(Directory.Exists(Path.Combine(plugin.PackageDirectory, ".git")));
        Assert.Equal(["sample-plugin"], PluginsDirectoryEntries());
    }

    [Theory]
    [InlineData("https://example.invalid/plugin.git", null, "PLUGIN_GIT_REF_REQUIRED")]
    [InlineData("git@example.invalid:owner/plugin.git", null, "PLUGIN_GIT_REF_REQUIRED")]
    [InlineData("https://user:secret-token@example.invalid/plugin.git", "v1", "PLUGIN_SOURCE_INVALID")]
    [InlineData("https://example.invalid/plugin.git", "-c", "PLUGIN_SOURCE_INVALID")]
    [InlineData("https://example.invalid/plugin.git", "v1..v2", "PLUGIN_SOURCE_INVALID")]
    [InlineData("<source>", "v1", "PLUGIN_SOURCE_INVALID")]
    [InlineData("no-such-directory", null, "PLUGIN_SOURCE_NOT_FOUND")]
    public async Task RejectsBadSourcesBeforeContactingGit(string source, string? gitRef, string code)
    {
        if (source == "<source>") source = PluginFixture.CopySample(Path.Combine(_root, "source"));

        var ex = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, source, gitRef));

        Assert.Equal(code, ex.Code);
        Assert.DoesNotContain("secret-token", ex.Message);
        Assert.Empty(PluginsDirectoryEntries());
    }

    [Fact]
    public async Task ReportsAMissingRefAndAFailedCloneWithoutLeavingFiles()
    {
        var (url, _, _) = CreateRepository();
        var missing = new Uri(Path.Combine(_root, "no-such-repository")).AbsoluteUri;

        var missingRef = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, url, "v9"));
        var failedClone = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, missing, "v1"));

        Assert.Equal("PLUGIN_GIT_REF_NOT_FOUND", missingRef.Code);
        Assert.Equal("PLUGIN_GIT_FAILED", failedClone.Code);
        Assert.Equal(ExitCodes.ExternalToolFailed, failedClone.ExitCode);
        Assert.Empty(PluginsDirectoryEntries());
    }

    [Fact]
    public async Task RefusesSymlinksCommittedToAGitSource()
    {
        var (url, _, _) = CreateRepository();
        var repository = new Uri(url).LocalPath;
        var blob = Git(repository, "hash-object", "-w", Path.Combine(repository, PluginManifest.FileName));
        Git(repository, "update-index", "--add", "--cacheinfo", $"120000,{blob},linked");
        Git(repository, "commit", "-q", "-m", "add a symlink");
        Git(repository, "tag", "v2");

        var ex = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, url, "v2"));

        Assert.Equal("PLUGIN_SOURCE_INVALID", ex.Code);
        Assert.Empty(PluginsDirectoryEntries());
    }

    [Fact]
    public async Task RefusesSymlinksInADirectorySource()
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, "source"));
        if (!TryCreateFileLink(Path.Combine(source, "linked.txt"), Path.Combine(source, PluginManifest.FileName))) return;

        var ex = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, source, null));

        Assert.Equal("PLUGIN_SOURCE_INVALID", ex.Code);
        Assert.Empty(PluginsDirectoryEntries());
    }

    [Theory]
    [InlineData("built-in-command", "PLUGIN_NAME_CONFLICT")]
    [InlineData("bundled-skill", "PLUGIN_NAME_CONFLICT")]
    [InlineData("broken-manifest", "PLUGIN_MANIFEST_INVALID")]
    [InlineData("unsupported-version", "PLUGIN_INCOMPATIBLE_VERSION")]
    public async Task RefusesUnusablePluginsBeforeInstalling(string problem, string code)
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, "source"));
        if (problem == "broken-manifest") File.WriteAllText(Path.Combine(source, PluginManifest.FileName), "{ \"schemaVersion\": 1, ");
        else PluginFixture.EditManifest(source, json =>
        {
            if (problem == "built-in-command") json["commands"]![0]!["name"] = "doctor";
            if (problem == "bundled-skill") json["skills"]![0]!["name"] = "resonite-build";
            if (problem == "unsupported-version") json["resoloop"]!["minVersion"] = "9.0.0";
            if (problem == "unsupported-version") json["resoloop"]!.AsObject().Remove("maxVersionExclusive");
        });

        var ex = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, source, null));

        Assert.Equal(code, ex.Code);
        Assert.Empty(PluginsDirectoryEntries());
    }

    [Fact]
    public async Task RefusesASecondCopyAndAPluginWithTheSameNames()
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, "source"));
        var sameNames = PluginFixture.CopySample(Path.Combine(_root, "same-names"));
        PluginFixture.EditManifest(sameNames, json => json["name"] = "other-plugin");
        await PluginInstaller.InstallAsync(_registry, source, null);

        var again = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, source, null));
        var conflict = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, sameNames, null));

        Assert.Equal("PLUGIN_ALREADY_INSTALLED", again.Code);
        Assert.Equal("PLUGIN_NAME_CONFLICT", conflict.Code);
        Assert.Equal(["sample-plugin"], PluginsDirectoryEntries());
    }

    [Fact]
    public async Task RefusesToInstallWhileAnInstalledPluginIsModified()
    {
        var installed = await PluginInstaller.InstallAsync(_registry, PluginFixture.CopySample(Path.Combine(_root, "source")), null);
        File.AppendAllText(Path.Combine(installed.InstallDirectory, "package", "scripts", "hello.sh"), "echo changed\n");

        var ex = await Assert.ThrowsAsync<RLoopException>(() => PluginInstaller.InstallAsync(_registry, CreateDistinctSource("other-plugin"), null));

        Assert.Equal("PLUGIN_MODIFIED", ex.Code);
    }

    [Fact]
    public async Task RemoveDeletesOnlyTheInstallDirectory()
    {
        var removed = await PluginInstaller.InstallAsync(_registry, PluginFixture.CopySample(Path.Combine(_root, "source")), null);
        await PluginInstaller.InstallAsync(_registry, CreateDistinctSource("other-plugin"), null);
        Directory.CreateDirectory(Path.Combine(removed.InstallDirectory, "data"));
        File.WriteAllText(Path.Combine(removed.InstallDirectory, "data", "cache.txt"), "runtime");
        var distributed = Path.Combine(_project, ".agents", "skills", "sample-skill", "SKILL.md");
        Directory.CreateDirectory(Path.GetDirectoryName(distributed)!);
        File.WriteAllText(distributed, "distributed by a later sync");

        var result = PluginInstaller.Remove(_registry, "sample-plugin");

        Assert.Equal(removed.InstallDirectory, result.RemovedDirectory);
        Assert.False(Directory.Exists(removed.InstallDirectory));
        Assert.True(File.Exists(distributed));
        Assert.Equal("other-plugin", Assert.Single(_registry.LoadAll()).Name);
    }

    [Fact]
    public async Task RemoveDoesNotFollowLinksInsideThePackage()
    {
        var installed = await PluginInstaller.InstallAsync(_registry, PluginFixture.CopySample(Path.Combine(_root, "source")), null);
        var outside = Directory.CreateDirectory(Path.Combine(_root, "outside")).FullName;
        File.WriteAllText(Path.Combine(outside, "keep.txt"), "user file");
        if (!TryCreateDirectoryLink(Path.Combine(installed.InstallDirectory, "package", "linked"), outside)) return;

        PluginInstaller.Remove(_registry, "sample-plugin");

        Assert.False(Directory.Exists(installed.InstallDirectory));
        Assert.True(File.Exists(Path.Combine(outside, "keep.txt")));
    }

    [Fact]
    public void RemoveRefusesInvalidNamesMissingPluginsAndLinks()
    {
        Assert.Equal("PLUGIN_NAME_INVALID", Assert.Throws<RLoopException>(() => PluginInstaller.Remove(_registry, "../project")).Code);
        Assert.Equal("PLUGIN_NOT_INSTALLED", Assert.Throws<RLoopException>(() => PluginInstaller.Remove(_registry, "absent-plugin")).Code);
        var outside = Directory.CreateDirectory(Path.Combine(_root, "outside")).FullName;
        Directory.CreateDirectory(_registry.PluginsDirectory);
        if (!TryCreateDirectoryLink(Path.Combine(_registry.PluginsDirectory, "linked-plugin"), outside)) return;

        Assert.Equal("PLUGIN_REMOVE_REFUSED", Assert.Throws<RLoopException>(() => PluginInstaller.Remove(_registry, "linked-plugin")).Code);
        Assert.True(Directory.Exists(outside));
    }

    public void Dispose() => PluginFixture.DeleteDirectory(_root);

    private string[] PluginsDirectoryEntries() => Directory.Exists(_registry.PluginsDirectory)
        ? Directory.EnumerateFileSystemEntries(_registry.PluginsDirectory).Select(Path.GetFileName).OfType<string>().Order(StringComparer.Ordinal).ToArray()
        : [];

    private string CreateDistinctSource(string name)
    {
        var source = PluginFixture.CopySample(Path.Combine(_root, name));
        PluginFixture.EditManifest(source, json =>
        {
            json["name"] = name;
            foreach (var list in new[] { "commands", "skills", "recipes" })
                foreach (var item in json[list]!.AsArray())
                    item!["name"] = name + "-" + item["name"]!.GetValue<string>();
        });
        return source;
    }

    // A repository with v1 (1.2.3) on the first commit, a "feature" branch there, and main at the second commit (1.3.0).
    private (string Url, string First, string Second) CreateRepository()
    {
        var repository = PluginFixture.CopySample(Path.Combine(_root, "repository"));
        Git(repository, "init", "-q", "-b", "main");
        Git(repository, "add", "-A");
        Git(repository, "commit", "-q", "-m", "first");
        Git(repository, "tag", "v1");
        Git(repository, "branch", "feature");
        var first = Git(repository, "rev-parse", "HEAD");
        PluginFixture.EditManifest(repository, json => json["version"] = "1.3.0");
        Git(repository, "commit", "-q", "-a", "-m", "second");
        return (new Uri(repository).AbsoluteUri, first, Git(repository, "rev-parse", "HEAD"));
    }

    private static string Git(string directory, params string[] arguments)
    {
        var start = new ProcessStartInfo("git") { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
        string[] all = ["-C", directory, "-c", "user.name=resoloop-tests", "-c", "user.email=tests@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", .. arguments];
        foreach (var argument in all) start.ArgumentList.Add(argument);
        using var process = Process.Start(start)!;
        var error = process.StandardError.ReadToEndAsync();
        var output = process.StandardOutput.ReadToEnd();
        process.WaitForExit();
        if (process.ExitCode != 0) throw new InvalidOperationException($"git {string.Join(' ', arguments)} failed: {error.Result}");
        return output.Trim();
    }

    private static bool TryCreateDirectoryLink(string path, string target)
    {
        try
        {
            Directory.CreateSymbolicLink(path, target);
            return true;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return false; // Symlinks need privileges on some Windows hosts.
        }
    }

    private static bool TryCreateFileLink(string path, string target)
    {
        try
        {
            File.CreateSymbolicLink(path, target);
            return true;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }
}
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: 共通の検証コマンド
Expected: ビルドが `PluginInstaller` の未定義で失敗する

- [ ] **Step 3: `git` の呼び出しを実装する**

<!-- file: src/RLoop.Core/Plugins/PluginGit.cs -->
```csharp
using System.ComponentModel;
using System.Diagnostics;
using System.Text;

namespace RLoop.Core.Plugins;

internal sealed record GitResult(int ExitCode, string StandardOutput, string StandardError);

/// <summary>Runs the git CLI without prompts. Installation runs git only; it never runs plugin code.</summary>
internal static class PluginGit
{
    public static async Task<GitResult> RunAsync(string? workingDirectory, IEnumerable<string> arguments, CancellationToken cancellationToken)
    {
        var start = new ProcessStartInfo("git")
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = new UTF8Encoding(false), StandardErrorEncoding = new UTF8Encoding(false)
        };
        start.Environment["GIT_TERMINAL_PROMPT"] = "0";
        start.ArgumentList.Add("-c");
        start.ArgumentList.Add("core.fsmonitor=false");
        if (workingDirectory is not null)
        {
            start.ArgumentList.Add("-C");
            start.ArgumentList.Add(workingDirectory);
        }
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        using var process = new Process { StartInfo = start };
        try { process.Start(); }
        catch (Exception ex) when (ex is Win32Exception or IOException)
        {
            throw PluginErrors.Create(PluginErrors.GitFailed, $"Cannot start git: {ex.Message}",
                suggestions: ["Install git and make sure it is on PATH."], innerException: ex);
        }
        process.StandardInput.Close();
        var stdout = process.StandardOutput.ReadToEndAsync(CancellationToken.None);
        var stderr = process.StandardError.ReadToEndAsync(CancellationToken.None);
        try { await process.WaitForExitAsync(cancellationToken); }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
            catch (InvalidOperationException) { }
            await process.WaitForExitAsync(CancellationToken.None);
            await Task.WhenAll(stdout, stderr);
            throw;
        }
        return new GitResult(process.ExitCode, await stdout, await stderr);
    }

    /// <summary>Tracked files plus untracked files that are not ignored, when <paramref name="directory"/> is the top level of a
    /// work tree. Null when git is missing or the directory is not a work tree top level (for example a folder that an
    /// enclosing repository ignores), so the caller copies the directory as it is.</summary>
    public static async Task<IReadOnlyList<string>?> ListWorkTreeFilesAsync(string directory, CancellationToken cancellationToken)
    {
        GitResult top;
        try { top = await RunAsync(directory, ["rev-parse", "--show-toplevel"], cancellationToken); }
        catch (RLoopException ex) when (ex.Code == PluginErrors.GitFailed) { return null; }
        if (top.ExitCode != 0 || !SamePath(top.StandardOutput.Trim(), directory)) return null;
        var files = await RunAsync(directory, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], cancellationToken);
        if (files.ExitCode != 0) throw Failed("git ls-files", files, directory);
        return files.StandardOutput.Split('\0', StringSplitOptions.RemoveEmptyEntries).Distinct(StringComparer.Ordinal).ToArray();
    }

    /// <summary>Clones <paramref name="url"/> into <paramref name="checkout"/>, resolves <paramref name="gitRef"/> to a commit and
    /// checks it out. Symlinks and submodules are refused before any file is written to the work tree.</summary>
    public static async Task<(string Commit, IReadOnlyList<string> Files)> CheckoutAsync(string url, string gitRef, string checkout,
        CancellationToken cancellationToken)
    {
        var clone = await RunAsync(null, ["clone", "--quiet", "--no-checkout", "--", url, checkout], cancellationToken);
        if (clone.ExitCode != 0) throw Failed("git clone", clone, url);
        var commit = await ResolveAsync(checkout, gitRef, cancellationToken) ?? throw PluginErrors.Create(PluginErrors.GitRefNotFound,
            $"'{gitRef}' is not a tag, branch or commit of {url}.", new Dictionary<string, object?> { ["url"] = url, ["ref"] = gitRef },
            ["List the refs with git ls-remote URL and pass an existing one to --ref."]);
        var tree = await RunAsync(checkout, ["ls-tree", "-r", "-z", "--full-tree", commit], cancellationToken);
        if (tree.ExitCode != 0) throw Failed("git ls-tree", tree, url);
        var files = new List<string>();
        var refused = new List<string>();
        foreach (var entry in tree.StandardOutput.Split('\0', StringSplitOptions.RemoveEmptyEntries))
        {
            var path = entry[(entry.IndexOf('\t') + 1)..];
            if (entry.StartsWith("100644 ", StringComparison.Ordinal) || entry.StartsWith("100755 ", StringComparison.Ordinal)) files.Add(path);
            else refused.Add(path);
        }
        if (refused.Count > 0)
            throw PluginErrors.Create(PluginErrors.SourceInvalid,
                $"{url} at {commit} contains symlinks or submodules, which plugins cannot use: {string.Join(", ", refused.Take(5))}",
                new Dictionary<string, object?> { ["url"] = url, ["commit"] = commit, ["refused"] = refused },
                ["Replace symlinks with regular files and copy submodule content into the plugin repository."]);
        var result = await RunAsync(checkout, ["-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", commit], cancellationToken);
        if (result.ExitCode != 0) throw Failed("git checkout", result, url);
        files.Sort(StringComparer.Ordinal);
        return (commit, files);
    }

    private static async Task<string?> ResolveAsync(string checkout, string gitRef, CancellationToken cancellationToken)
    {
        // Tags, full or short commits and the default branch resolve directly; other branches exist only as origin/<name>.
        foreach (var candidate in new[] { gitRef, "refs/remotes/origin/" + gitRef })
        {
            var result = await RunAsync(checkout, ["rev-parse", "--verify", "--quiet", "--end-of-options", candidate + "^{commit}"],
                cancellationToken);
            if (result.ExitCode == 0) return result.StandardOutput.Trim();
        }
        return null;
    }

    private static bool SamePath(string left, string right) => string.Equals(
        Path.TrimEndingDirectorySeparator(Path.GetFullPath(left)), Path.TrimEndingDirectorySeparator(Path.GetFullPath(right)),
        OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);

    private static RLoopException Failed(string operation, GitResult result, string location) =>
        PluginErrors.Create(PluginErrors.GitFailed, $"{operation} failed with exit code {result.ExitCode}: {result.StandardError.Trim()}",
            new Dictionary<string, object?> { ["location"] = location, ["exitCode"] = result.ExitCode },
            ["Check the URL, network access and credentials (use a git credential helper)."]);
}
```

- [ ] **Step 4: 導入と削除を実装する**

<!-- file: src/RLoop.Core/Plugins/PluginInstaller.cs -->
```csharp
using System.Globalization;
using System.Text.RegularExpressions;

namespace RLoop.Core.Plugins;

public sealed record PluginInstallResult(string Name, string Version, PluginSource Source, string? Commit, string InstallDirectory,
    int FileCount);

public sealed record PluginRemoveResult(string Name, string RemovedDirectory, string Note);

/// <summary>Installs plugins into .resoloop/plugins/NAME without running plugin code, and removes exactly that directory.</summary>
public static partial class PluginInstaller
{
    public const int MaxFiles = 10_000;
    public const long MaxTotalBytes = 200L * 1024 * 1024;

    public static async Task<PluginInstallResult> InstallAsync(PluginRegistry registry, string source, string? gitRef,
        CancellationToken cancellationToken = default)
    {
        var kind = Classify(source, gitRef);
        Directory.CreateDirectory(registry.PluginsDirectory);
        // Everything is assembled in a staging directory and renamed into place last, so a failure leaves no plugin behind.
        var staging = Path.Combine(registry.PluginsDirectory, ".staging-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            string sourceRoot;
            IReadOnlyList<string> files;
            PluginSource pluginSource;
            string? commit = null;
            if (kind == PluginSource.DirectoryKind)
            {
                sourceRoot = Path.GetFullPath(source);
                files = await ListDirectoryAsync(sourceRoot, cancellationToken);
                pluginSource = new PluginSource(kind, sourceRoot, null);
            }
            else
            {
                sourceRoot = Path.Combine(staging, "checkout");
                (commit, files) = await PluginGit.CheckoutAsync(source, gitRef!, sourceRoot, cancellationToken);
                pluginSource = new PluginSource(kind, source, gitRef);
            }
            CheckFiles(sourceRoot, files);
            var manifest = PluginManifest.Load(sourceRoot, files.ToHashSet(StringComparer.Ordinal));
            manifest.EnsureCompatibleWith(registry.ResoloopVersion);
            EnsureInstallable(registry, manifest);
            var hashes = Copy(sourceRoot, files, Path.Combine(staging, PluginRegistry.PackageDirectoryName));
            if (kind == PluginSource.GitKind) DeleteTree(sourceRoot);
            new PluginInstallRecord(PluginInstallRecord.CurrentSchemaVersion, manifest.Name, manifest.Version.Text, pluginSource, commit,
                    DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture), registry.ResoloopVersion, hashes)
                .Write(Path.Combine(staging, PluginInstallRecord.FileName));
            var target = Path.Combine(registry.PluginsDirectory, manifest.Name);
            try { Directory.Move(staging, target); }
            catch (IOException ex) when (Directory.Exists(target) || File.Exists(target))
            {
                throw AlreadyInstalled(manifest.Name, ex);
            }
            return new PluginInstallResult(manifest.Name, manifest.Version.Text, pluginSource, commit, target, hashes.Count);
        }
        finally
        {
            if (Directory.Exists(staging)) DeleteTree(staging);
        }
    }

    public static PluginRemoveResult Remove(PluginRegistry registry, string name)
    {
        if (!PluginNames.IsValid(name))
            throw PluginErrors.Create(PluginErrors.NameInvalid, $"'{name}' is not a plugin name ({PluginNames.Rule}).");
        var target = Path.Combine(registry.PluginsDirectory, name);
        var directory = new DirectoryInfo(target);
        if (directory.LinkTarget is not null || File.Exists(target))
            throw PluginErrors.Create(PluginErrors.RemoveRefused,
                $"{target} is not a real directory; resoloop removes only plugin directories that it created.",
                new Dictionary<string, object?> { ["path"] = target }, ["Inspect the entry and remove it by hand."]);
        if (!directory.Exists)
            throw PluginErrors.Create(PluginErrors.NotInstalled, $"Plugin '{name}' is not installed in {registry.ProjectRoot}.",
                new Dictionary<string, object?> { ["plugin"] = name }, ["Run resoloop plugin list --json."]);
        DeleteTree(target);
        return new PluginRemoveResult(name, target,
            "Only the install directory was removed. Files distributed outside it (for example skills) were left in place.");
    }

    /// <summary>Deletes a directory tree without following links: a link is removed, never the files it points to.</summary>
    internal static void DeleteTree(string path)
    {
        var directory = new DirectoryInfo(path);
        foreach (var entry in directory.EnumerateFileSystemInfos("*", PluginFiles.Shallow))
        {
            if (entry.LinkTarget is not null || entry.Attributes.HasFlag(FileAttributes.ReparsePoint))
            {
                if (entry is DirectoryInfo && OperatingSystem.IsWindows()) Directory.Delete(entry.FullName);
                else File.Delete(entry.FullName);
            }
            else if (entry is DirectoryInfo) DeleteTree(entry.FullName);
            else
            {
                // git marks object files read-only on Windows.
                if (entry.Attributes.HasFlag(FileAttributes.ReadOnly)) entry.Attributes &= ~FileAttributes.ReadOnly;
                entry.Delete();
            }
        }
        directory.Delete();
    }

    internal static string Classify(string source, string? gitRef)
    {
        if (Directory.Exists(source))
        {
            if (gitRef is not null)
                throw SourceInvalid("--ref applies only to Git URLs; a local directory is copied as it is.", source);
            return PluginSource.DirectoryKind;
        }
        if (!GitUrlPattern().IsMatch(source))
            throw PluginErrors.Create(PluginErrors.SourceNotFound, $"'{source}' is neither an existing directory nor a Git URL.",
                new Dictionary<string, object?> { ["source"] = source },
                ["Pass a plugin directory, or a Git URL (https://, ssh://, git@host:path, file://) with --ref."]);
        if (gitRef is null)
            throw PluginErrors.Create(PluginErrors.GitRefRequired, "Installing from a Git URL requires --ref TAG|BRANCH|COMMIT.",
                suggestions: ["Pin the release you want, for example --ref v0.1.0."]);
        if (!RefPattern().IsMatch(gitRef) || gitRef.Contains("..", StringComparison.Ordinal))
            throw SourceInvalid($"--ref '{gitRef}' is not a tag, branch or commit name.", null);
        // Never record a token in install.json or in an error message.
        if (Uri.TryCreate(source, UriKind.Absolute, out var uri) && uri.Scheme is "http" or "https" && uri.UserInfo.Length > 0)
            throw SourceInvalid("Git URLs must not contain user names or tokens; use a git credential helper instead.", null);
        return PluginSource.GitKind;
    }

    private static async Task<IReadOnlyList<string>> ListDirectoryAsync(string root, CancellationToken cancellationToken)
    {
        var listed = await PluginGit.ListWorkTreeFilesAsync(root, cancellationToken);
        if (listed is null)
        {
            var (files, links) = PluginFiles.Scan(root, relative => Path.GetFileName(relative) == ".git");
            RefuseLinks(root, links);
            return files;
        }
        var result = new List<string>();
        var refused = new List<string>();
        foreach (var file in listed)
        {
            var info = new FileInfo(Path.Combine(root, file));
            if (info.LinkTarget is not null || Directory.Exists(info.FullName)) refused.Add(file); // symlink, submodule or nested repository
            else if (info.Exists) result.Add(file); // tracked files deleted from the work tree are skipped
        }
        RefuseLinks(root, refused);
        result.Sort(StringComparer.Ordinal);
        return result;
    }

    private static void RefuseLinks(string root, IReadOnlyList<string> links)
    {
        if (links.Count > 0)
            throw SourceInvalid($"The plugin contains symlinks or nested repositories, which plugins cannot use: {string.Join(", ", links.Take(5))}",
                root, links);
    }

    private static void CheckFiles(string root, IReadOnlyList<string> files)
    {
        var unsafePaths = files.Where(file => !PluginManifest.IsSafeRelativePath(file)).ToArray();
        if (unsafePaths.Length > 0)
            throw SourceInvalid($"These paths cannot be installed portably: {string.Join(", ", unsafePaths.Take(5))}", root, unsafePaths);
        if (files.Count > MaxFiles) throw SourceInvalid($"The plugin has {files.Count} files; at most {MaxFiles} are allowed.", root);
        var total = files.Sum(file => new FileInfo(Path.Combine(root, file)).Length);
        if (total > MaxTotalBytes) throw SourceInvalid($"The plugin has {total} bytes; at most {MaxTotalBytes} are allowed.", root);
    }

    private static void EnsureInstallable(PluginRegistry registry, PluginManifest manifest)
    {
        var statuses = registry.List();
        if (statuses.FirstOrDefault(status => !status.Ok) is { Problem: { } problem } broken)
            throw PluginErrors.Create(problem.Code, $"Cannot install while plugin '{broken.Name}' is unusable: {problem.Message}",
                new Dictionary<string, object?>(problem.Details) { ["plugin"] = broken.Name }, problem.Suggestions);
        var target = Path.Combine(registry.PluginsDirectory, manifest.Name);
        if (statuses.Any(status => status.Name == manifest.Name) || Directory.Exists(target) || File.Exists(target))
            throw AlreadyInstalled(manifest.Name);
        var conflicts = PluginNames.FindConflicts(manifest, statuses.Select(status => status.Manifest!));
        if (conflicts.Count > 0)
            throw PluginErrors.Create(PluginErrors.NameConflict, $"Plugin '{manifest.Name}' cannot be installed: {conflicts[0]}",
                new Dictionary<string, object?> { ["plugin"] = manifest.Name, ["conflicts"] = conflicts },
                ["Rename the conflicting commands, skills or recipes in the plugin, or remove the other plugin."]);
    }

    private static SortedDictionary<string, string> Copy(string sourceRoot, IReadOnlyList<string> files, string package)
    {
        var hashes = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var file in files)
        {
            var target = Path.Combine(package, file.Replace('/', Path.DirectorySeparatorChar));
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                File.Copy(Path.Combine(sourceRoot, file.Replace('/', Path.DirectorySeparatorChar)), target);
            }
            catch (IOException ex)
            {
                throw SourceInvalid($"Cannot copy '{file}' (two paths may differ only in case): {ex.Message}", sourceRoot);
            }
            hashes[file] = PluginFiles.Sha256(target);
        }
        return hashes;
    }

    private static RLoopException SourceInvalid(string message, string? source, IReadOnlyList<string>? paths = null) =>
        PluginErrors.Create(PluginErrors.SourceInvalid, message,
            new Dictionary<string, object?> { ["source"] = source, ["paths"] = paths });

    private static RLoopException AlreadyInstalled(string name, Exception? innerException = null) =>
        PluginErrors.Create(PluginErrors.AlreadyInstalled, $"Plugin '{name}' is already installed.",
            new Dictionary<string, object?> { ["plugin"] = name },
            [$"To replace it, run resoloop plugin remove {name} --yes, then install again."], innerException);

    [GeneratedRegex(@"^(?:(?:https?|ssh|git|file)://\S+|[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*:\S+)\z",
        RegexOptions.CultureInvariant | RegexOptions.IgnoreCase)]
    private static partial Regex GitUrlPattern();

    [GeneratedRegex(@"^[A-Za-z0-9._/][A-Za-z0-9._/-]{0,199}\z", RegexOptions.CultureInvariant)]
    private static partial Regex RefPattern();
}
```

- [ ] **Step 5: テストが通ることを確かめる**

Run: 共通の検証コマンド
Expected: `PluginManifestTests`・`PluginRegistryTests`・`PluginInstallerTests` が全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/RLoop.Core/Plugins/PluginGit.cs src/RLoop.Core/Plugins/PluginInstaller.cs tests/RLoop.Tests/PluginInstallerTests.cs
git commit -m "feat(plugins): install plugins from directories or pinned Git refs and remove them"
```

### Task 4: CLI の `plugin` の節と help の行

テスト: 書かない。節は引数の数の確認と Core の呼び出し・表示だけで、分岐の中身は Task 1〜3 のテストが確かめる。既存のテストに `Program.Main` を呼ぶ仕組みも無い。代わりに、一時プロジェクトで CLI を実行して出力と終了コードを記録する（Step 3）。

**Files:**
- Modify: `src/RLoop.Cli/Program.cs`（`using`、`commandToken` の直後の分岐、`RunUixRecipe` の後のメソッド、help の「Project setup:」の 3 行）

**Interfaces:**
- Consumes: `PluginRegistry.FindProjectRoot`・`List`、`PluginInstaller.InstallAsync`・`Remove`、`RequireYes`・`UnknownCommand`・`ProductVersion`（既存）

- [ ] **Step 1: `Program.cs` を変える**

`using RLoop.Core;` の次の行に足す:

```csharp
using RLoop.Core.Plugins;
```

`if (parsed.Has("verbose")) Console.Error.WriteLine(...);` の直後に足す（設定の解決と `--command-timeout` の後、接続の前）:

```csharp
            if (parsed.Positionals[0].Equals("plugin", StringComparison.OrdinalIgnoreCase))
                return await RunPlugin(parsed, output, commandToken);
```

`RunUixRecipe` の後に足す:

```csharp
    private static async Task<int> RunPlugin(ParsedArguments args, OutputWriter output, CancellationToken token)
    {
        var command = args.Positional(1, "plugin subcommand (install, list, remove)").ToLowerInvariant();
        var expected = command switch { "install" or "remove" => 3, "list" => 2, _ => throw UnknownCommand("plugin " + command) };
        if (args.Positionals.Count != expected)
            throw new RLoopException("UNEXPECTED_ARGUMENT", "Use plugin install SOURCE [--ref REF], plugin list, or plugin remove NAME --yes.",
                ExitCodes.InvalidArguments);
        if (command == "remove") RequireYes(args, "plugin remove");
        var registry = new PluginRegistry(PluginRegistry.FindProjectRoot(args.Option("project"), Environment.CurrentDirectory), ProductVersion());
        if (command == "install")
        {
            var installed = await PluginInstaller.InstallAsync(registry, args.Positionals[2], args.Option("ref"), token);
            output.Success(installed, writer =>
                writer.WriteLine($"installed {installed.Name} {installed.Version} ({installed.FileCount} files) -> {installed.InstallDirectory}"));
        }
        else if (command == "remove")
        {
            var removed = PluginInstaller.Remove(registry, args.Positionals[2]);
            output.Success(removed, writer =>
            {
                writer.WriteLine($"removed {removed.Name} ({removed.RemovedDirectory})");
                writer.WriteLine($"  note: {removed.Note}");
            });
        }
        else
        {
            var plugins = registry.List().Select(status => new
            {
                name = status.Name, version = status.Record?.Version, ok = status.Ok, source = status.Record?.Source,
                commit = status.Record?.Commit, installedAt = status.Record?.InstalledAt, path = status.InstallDirectory, problem = status.Problem
            }).ToArray();
            output.Success(new { projectRoot = registry.ProjectRoot, pluginsDirectory = registry.PluginsDirectory, plugins }, writer =>
            {
                writer.WriteLine($"plugins in {registry.PluginsDirectory}: {plugins.Length}");
                foreach (var plugin in plugins)
                {
                    var origin = plugin.source is null ? "" : $"{plugin.source.Kind} {plugin.source.Location}" +
                        (plugin.source.Ref is null ? "" : $" @ {plugin.source.Ref}") + (plugin.commit is null ? "" : $" ({plugin.commit[..12]})");
                    writer.WriteLine($"  {(plugin.ok ? "ok" : plugin.problem!.Code),-28} {plugin.name} {plugin.version} {origin}");
                }
            });
        }
        return ExitCodes.Success;
    }
```

help の `resoloop skills sync ...` の行の後に足す:

```text
  resoloop plugin install DIRECTORY|GIT_URL [--ref TAG|BRANCH|COMMIT] [--project DIR] [--json]
  resoloop plugin list [--project DIR] [--json]
  resoloop plugin remove NAME --yes [--project DIR] [--json]
```

- [ ] **Step 2: ビルドする**

Run: `dotnet build ResoLoop.slnx -v q -nologo`
Expected: 警告 0・エラー 0

- [ ] **Step 3: 一時プロジェクトで CLI を確かめる**

スクラッチパッド（`$S`）で実行し、各コマンドの出力と終了コードを記録する。

```bash
CODE_ROOT=/workspaces/reso-world/external/resoloop/.worktrees/issue-97-plugin-core
RL() { dotnet "$CODE_ROOT/src/RLoop.Cli/bin/Debug/net10.0/resoloop.dll" "$@"; }
RL init "$S/world" --json >/dev/null && cd "$S/world"
RL plugin list --json                                                      # 0 件
RL plugin install "$CODE_ROOT/tests/fixtures/plugins/core/sample-plugin" --json
RL plugin list --json                                                      # ok、source.kind=directory、commit=null
echo tampered >> .resoloop/plugins/sample-plugin/package/scripts/hello.sh
RL plugin list --json                                                      # ok=false、problem.code=PLUGIN_MODIFIED、終了コード 0
RL plugin remove sample-plugin --json; echo "exit=$?"                      # CONFIRMATION_REQUIRED、exit=6
RL plugin remove sample-plugin --yes --json                                # 削除
cp -r "$CODE_ROOT/tests/fixtures/plugins/core/sample-plugin" "$S/repo" && git -C "$S/repo" init -q -b main && git -C "$S/repo" add -A &&
  git -C "$S/repo" -c user.name=t -c user.email=t@example.invalid commit -q -m first && git -C "$S/repo" tag v1
RL plugin install "file://$S/repo" --json; echo "exit=$?"                  # PLUGIN_GIT_REF_REQUIRED、exit=2
RL plugin install "file://$S/repo" --ref v1 --json                         # commit が記録される
RL plugin list                                                             # 人向けの表示
cd "$S" && RL plugin list --json; echo "exit=$?"                           # PLUGIN_PROJECT_NOT_FOUND、exit=3
RL help | grep "plugin "                                                   # help の 3 行
```

- [ ] **Step 4: Commit**

```bash
git add src/RLoop.Cli/Program.cs
git commit -m "feat(cli): add resoloop plugin install, list and remove"
```

### Task 5: 全体の検証、レビュー、公開

テスト: 新しく書かない。全体のビルドとテスト、ブランチ全体のレビューで確かめる。

- [ ] **Step 1: 全体のビルドとテスト**

Run: `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build`
Expected: 警告 0・エラー 0。基準（`99c59be`: RLoop.Tests 448 件、RLoop.IntegrationTests 19 件）に新しいテストを足した数がすべて PASS

- [ ] **Step 2: 範囲の確認**

Run: `git diff --stat upstream/main...HEAD`
Expected: Global Constraints の「変えるのは」のファイルだけ

- [ ] **Step 3: ブランチ全体のレビュー**

新しいレビュアー（サブエージェント）に、Spec と Plan と `upstream/main...HEAD` の差分を渡してレビューさせる。致命的な指摘（受け入れ条件・安全条件の違反、データの消失、誤った仕様）だけを直し、Info は記録に残す。直したらビルドとテストをやり直す。

- [ ] **Step 4: 公開**

- fork へ push する: `git push -u origin feat/plugin-core`
- fork の `main` を対象に PR を作る（`gh pr create --repo usaturn/resoloop --base main --head feat/plugin-core`）。本文に、Issue（usaturn/create-reso-world#97）、Spec・Plan、検証の結果、fork の `main`（`84c7932`）との差（上流から作ったため fork 独自の変更を含まない）を書く
- create-reso-world の `docs/issue-97-plugin-core` を push し、文書専用 PR を作る。コードの PR と相互に参照する
- マージはしない（利用者の指示による）

- [ ] **Step 5: 記録**

Spec・Plan に実施結果（HEAD、テストの数、CLI の確認、レビュー、PR の URL、所要時間）を追記し、状態はマージまで `draft` のままにする。#97 に handoff と manifest を公開し、予約を解放する。

## 実施結果

2026-10-16（JST）に Native（executing-plans）で実施した。台帳の記録をまとめる。

| Task | コミット | 結果 |
| --- | --- | --- |
| 1 manifest v1 | `6c8b430` | RED（`RLoop.Core.Plugins` が無い）→ GREEN。Plugin のテスト 40 件 |
| 2 registry | `a4c1e85` | RED（`PluginRegistry` が無い）→ GREEN。53 件 |
| 3 導入と削除 | `27a97d5` | RED（`PluginInstaller` が無い）→ GREEN。79 件 |
| 4 CLI | `6443d70` | ビルド 警告 0。CLI の確認は下記 |
| 最終レビューの修正 | `a9a8427` | リンクの判定を `LinkTarget` だけにした |

- 全体（`a9a8427`）: `dotnet build ResoLoop.slnx` 警告 0・エラー 0、`dotnet test ResoLoop.slnx --no-build` で RLoop.Tests 527 件（448＋新規 79）、RLoop.IntegrationTests 19 件がすべて PASS
- fork の `main`（`84c7932`）との試しのマージ: 衝突なし。ビルド 警告 0、RLoop.Tests 535 件、IntegrationTests 19 件が PASS。一時 worktree は削除済み
- 差分の範囲: Global Constraints の「変えるのは」のファイルだけ（15 ファイル、2088 行の追加）
- CLI の確認（`resoloop init` で作った一時プロジェクト）: `list` 0 件（終了 0）、ディレクトリから `install`（4 ファイル）、`list` が ok、導入後にファイルを書き換えると `list` が `ok: false`・`PLUGIN_MODIFIED`・`changed: [scripts/hello.sh]`（終了 0）、`--yes` なしの `remove` が `CONFIRMATION_REQUIRED`（終了 6）、`remove --yes` で削除、`--ref` なしの Git の URL が `PLUGIN_GIT_REF_REQUIRED`（終了 2）、`--ref v1` でコミットを記録、2 回目の導入が `PLUGIN_ALREADY_INSTALLED`（終了 6）、プロジェクトの外で `PLUGIN_PROJECT_NOT_FOUND`（終了 3）、`plugin upgrade` が `UNKNOWN_COMMAND`（終了 2）、help に 3 行。導入したスクリプトの実行権限は保たれた
- 最終レビュー: 新しいサブエージェントは立てず、実装したエージェントが別の回として行った（このセッションではサブエージェントの起動を利用者の明示の依頼に限るため）。作成者自身のレビューなので、独立したレビューより弱い
- fork PR: https://github.com/usaturn/resoloop/pull/20

### 判断（Ruling）

- Task 4: `plugin list --json` は、ディレクトリの導入元で `commit`・`ref` が null のとき欄を出さない。CLI の出力は全コマンドで null を省く（`OutputWriter` の `WhenWritingNull`）ためで、#97 の `Program.cs` の節の外を変えないことを優先した。誤りだった場合の影響: 利用側が「欄が無い」を null として扱う必要がある
- 最終レビュー: リンクを `LinkTarget` または `FileAttributes.ReparsePoint` で判定していたため、Windows の OneDrive のファイル（リンクでない reparse point）があると、導入が拒否され、照合が `PLUGIN_MODIFIED` になり、削除も失敗する。`LinkTarget`（symlink と junction）だけで判定するよう直した。Linux ではリンクでない reparse point を作れないので、失敗するテストは書けなかった。既存のリンクのテストは通る。誤りだった場合の影響: 珍しい種類の reparse point が中身として写される

### 見送った軽微な指摘

- `.resoloop/plugins/` の直下に通常のファイルを置くと `PLUGIN_RECORD_INVALID` になり、手で消すまで導入が止まる（提案文は `plugin remove` を示すが、`remove` はディレクトリ以外を拒否する）
- 強制終了で残った `.staging-*` は無視されるが、片付けられない
- SSH のホスト鍵やパスフレーズの確認は端末から読むため、`--command-timeout` まで待つことがある
- `plugin list --json` が null の `commit`・`ref` を省く（上の判断）

### 所要時間

着手 2026-10-15T18:38Z（UTC）、fork PR の作成まで約 50 分。

| 段階 | 時間 |
| --- | --- |
| 予約・調査・Spec | 約 9 分（18:38〜18:47） |
| Plan（コードを含む） | 約 31 分（18:47〜19:18） |
| Task 1〜4 の実装とテスト | 約 4 分（19:18〜19:22） |
| 最終レビューと修正 | 約 4 分（19:22〜19:26） |
| 全体の検証・fork の main との試しのマージ・PR | 約 3 分（19:26〜19:29） |

## 完了

2026-10-16 JST に完了した。

- コード: usaturn/resoloop#20 を 2026-10-16T04:48Z に fork の `main` へマージした（マージコミット `39db994`。検証した head `a9a8427` を指定）。fork の `main` の CI（`39db994`）は成功
- 文書: この Spec・Plan を含む #109 を 2026-10-16T05:00Z に `main` へマージした（マージコミット `6f93999`）
- レビュー: 両 PR のレビュー指摘は致命的でないと判定し、修正なしでマージした。判定の記録は `../specs/2026-10-16-usaturn-resoloop-pr20-plugin-core-review-fixes-design.md`（PR #20）と `../specs/2026-10-16-create-reso-world-pr109-plugin-core-docs-review-fixes-design.md`（#109）。この Plan の全文ブロックのうち `PluginRegistry.cs`・`PluginInstaller.cs` の 2 個は最終レビューの修正（`a9a8427`）の前の版で、最終の内容は fork の `main` にある
- 残した制約: PR #20 の既知の制限のうち 3 件を #110・#111・#112 に起票した（未着手。ボードへの登録は #95 の調整役）
- Issue: #97 を 2026-10-16 に completed で close した。#98・#99・#100 が着手できる
- worktree: DOC_ROOT・CODE_ROOT は完了後に削除した
