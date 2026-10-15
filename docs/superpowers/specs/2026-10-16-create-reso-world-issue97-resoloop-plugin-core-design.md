# create-reso-world Issue #97: resoloop のプラグインの仕様と土台（manifest・導入・一覧・削除・記録）

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/97（親: #95、ボードのキー `resoloop-plugins-board`、子のキー `plugin-core`）
- 実装対象: `usaturn/resoloop`（fork）。上流 `orange3134/resoloop` への提案は #105
- 状態: draft（人の承認は得ていない。利用者の指示「途中で止めずに推奨案で PR まで作成して」（2026-10-16 JST）により、判断はエージェントが推奨案で決め、実装と PR の作成まで進める。この指示は Spec の内容の承認ではない）
- 調査したコード HEAD: resoloop 上流 `main` の `99c59be98df0f10b0a8e58781b7f4f67029016f5`（v0.1.0-preview.17）、create-reso-world `main` の `e7eb72a1602ac03e723bc50c9734773102947df1`
- Plan: `../plans/2026-10-16-create-reso-world-issue97-resoloop-plugin-core.md`
- 実装 HEAD: resoloop `a9a8427e33b14b700fdc2e558b6fbad46fd991b6`（ブランチ `feat/plugin-core`）。結果は Plan の「実施結果」
- fork PR: https://github.com/usaturn/resoloop/pull/20（2026-10-16 JST に利用者の指示により作成。マージは未実施）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-97-plugin-core-docs`（ブランチ `docs/issue-97-plugin-core`）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-97-plugin-core`（ブランチ `feat/plugin-core`、`upstream/main` から作成）

## 目的と範囲

resoloop のプラグインの仕様（manifest の形式、導入元、置き場所、記録）を決め、`resoloop plugin install|list|remove` で導入・一覧・削除できるようにする。導入済みのプラグインを読む `PluginRegistry` を、#98（コマンドの実行と `doctor`）・#99（スキルの配布）・#100（UIX レシピ）が使える形で固める。

変えるファイルは Issue の「変えてよいもの」に限る。

- `src/RLoop.Core/Plugins/`（新規）
- `src/RLoop.Cli/Program.cs` の `plugin` の節と、help のその行
- `tests/RLoop.Tests/PluginManifestTests.cs`・`PluginRegistryTests.cs`・`PluginInstallerTests.cs`、`tests/fixtures/plugins/core/`（すべて新規）

`Configuration.cs` は変えない（プラグインの設定は足さない）。コマンドの実行、スキルの配布、レシピ、README などの文書は範囲外である（#98〜#101）。resoloop の AGENTS.md は CLI を変えたら README と skills を直すよう求めるが、親 #95 の分担により `plugin` コマンドの文書は #101 が書く。この作業では help の行だけを足す。

## エージェントの判断

利用者の指示により、次の点は確認を取らずに推奨案で決めた。代案と理由を残す。

| 論点 | 決めたこと | 代案と、採らなかった理由 |
| --- | --- | --- |
| 実行のしかた | プラグインは別のプロセスとして動かす。本体のプロセスに .NET のアセンブリを読み込まない。導入の時点ではプラグインのコードを実行しない | アセンブリの読み込みは、Root の保護や `--yes` などの本体の安全規則を迂回でき、版の互換も壊れやすい（Issue の推奨どおり） |
| 置き場所 | プロジェクトの単位（`<project>/.resoloop/plugins/<name>/`）だけにする | 利用者の単位（`~/.resoloop/plugins/`）は、ワールドごとに版を変えられず、スキルの配布（#99）やレシピ（#100）がプロジェクトの単位であることと合わない。必要になったら v2 で足す |
| プロジェクトの決め方 | `--project DIR`、無ければ現在のディレクトリから上へ `.resoloop.json` を探す。見つからなければ止める | 現在のディレクトリへ黙って作ると、ワールドの外にプラグインが散らばる |
| 導入元 | ローカルのディレクトリと、Git の URL（`--ref` 必須） | Git の既定ブランチを暗黙に使うと、記録したコミットと利用者の意図がずれる |
| ローカルの写し方 | ディレクトリが Git の作業ツリーの中なら、`git ls-files --cached --others --exclude-standard` の一覧だけを写す。そうでなければ `.git` を除く全部を写す | 全部を写すと、開発中の `.venv`（symlink を含む）まで入って導入が失敗する |
| 記録 | `<name>/install.json` に導入元・コミット・全ファイルの SHA-256 を書く。中身は `<name>/package/` に置き、記録と分ける | 記録を中身と同じ階層に置くと、プラグインのファイル名と衝突し得る |
| 書き換えの検出 | 使うたびに `package/` の全ファイルを照合する。内容の変更、欠けたファイル、増えたファイル、symlink を `PLUGIN_MODIFIED` にする | 増えたファイルを見逃すと、Python の `json.py` のような差し込みを防げない |
| 対応する版 | manifest の `resoloop.minVersion`（必須）と `resoloop.maxVersionExclusive`（任意）。SemVer 2.0 の順序で比べる | 範囲の式（`>=1 <2`）は解析が増えるわりに得るものが少ない |
| 名前 | 小文字・数字・`-`、2〜40 文字。組み込みのコマンド、同梱スキル、`resonite-` で始まるスキル、組み込みのレシピ、導入済みの他のプラグインと同じ名前は拒否する | `resonite-` を予約しないと、上流が同梱スキルを足したときに衝突する |
| 更新 | v1 は上書きの導入をしない。`remove --yes` の後に導入し直す | 上書きの導入は、失敗したときの戻し方まで決める必要があり、v1 には要らない |
| manifest の未知の欄 | 拒否する | 綴りの誤りを黙って無視すると、壊れた manifest を見逃す。欄を足すときは `schemaVersion` を上げる |

## 構成

```
<project>/
  .resoloop.json
  .resoloop/plugins/
    <name>/
      install.json      記録（導入元、コミット、ファイルの SHA-256）
      package/          プラグインの中身（導入元の写し。導入後に変えない）
        resoloop-plugin.json
        ...
      data/             プラグインが実行時に書いてよい場所（予約のみ。#98 が作る）
    .staging-<guid>/    導入中の一時ディレクトリ（終わると消す）
```

`src/RLoop.Core/Plugins/` のファイル:

| ファイル | 役割 |
| --- | --- |
| `SemanticVersion.cs` | SemVer 2.0 の解析と比較 |
| `PluginNames.cs` | 名前の規則、予約された名前（組み込みのコマンド、同梱スキル、組み込みのレシピ）、名前の衝突の検出 |
| `PluginErrors.cs` | `PLUGIN_*` のコードと終了コードの対応 |
| `PluginManifest.cs` | manifest（v1）の型、読み込み、検証 |
| `PluginRegistry.cs` | 記録の型、ファイルの照合、`PluginRegistry` |
| `PluginInstaller.cs` | 導入（ディレクトリ・Git）、削除、`git` の呼び出し |

依存の向きは AGENTS.md のとおり Cli → Core で、Core は ResoniteLink や Flux の型を参照しない。

## manifest（v1）

プラグインのルートに `resoloop-plugin.json` を置く。UTF-8 の JSON で、256 KiB まで。

```json
{
  "schemaVersion": 1,
  "name": "meshy-glb",
  "version": "0.1.0",
  "description": "Hand a GLB from the Meshy web app to resoloop.",
  "resoloop": { "minVersion": "0.1.0-preview.17", "maxVersionExclusive": "0.2.0" },
  "commands": [
    {
      "name": "meshy-glb",
      "description": "Finish a Meshy GLB for resoloop blender export.",
      "program": "uv",
      "args": ["run", "--project", "${pluginRoot}", "--frozen", "meshy-glb"],
      "timeoutSeconds": 1800
    }
  ],
  "skills": [{ "name": "meshy-glb", "path": "skills/meshy-glb" }],
  "recipes": [
    {
      "name": "glb-preview",
      "path": "recipes/glb-preview.json",
      "prototype": "meshy.glb-preview",
      "purpose": "Preview frame for an imported GLB.",
      "parameters": { "key": "Unique stable key prefix." },
      "ports": { "root": "$slot:<key>" },
      "requirements": ["Caller owns lighting."]
    }
  ],
  "tools": [
    { "name": "uv", "executable": "uv", "versionArgs": ["--version"], "required": true, "hint": "Install uv." }
  ]
}
```

| 欄 | 必須 | 規則 | 使う子 |
| --- | --- | --- | --- |
| `schemaVersion` | 必須 | 整数 `1`。他の値は `PLUGIN_SCHEMA_UNSUPPORTED` | #97 |
| `name` | 必須 | 名前の規則（下記）。導入先のディレクトリ名になる | #97 |
| `version` | 必須 | SemVer 2.0 | #97 |
| `description` | 任意 | 1〜500 文字 | #97・#98 |
| `resoloop.minVersion` | 必須 | SemVer 2.0。本体の版がこれ以上 | #97 |
| `resoloop.maxVersionExclusive` | 任意 | SemVer 2.0。本体の版がこれ未満。`minVersion` より大きい | #97 |
| `commands[]` | 任意 | 0〜50 件。`name` は重複しない | #98 |
| `commands[].name` | 必須 | 名前の規則。`resoloop <name> ...` で呼ぶ | #98 |
| `commands[].description` | 必須 | 1〜500 文字。help の一覧に出す | #98 |
| `commands[].program` | 必須 | `./` で始まるなら `package/` の中のファイル（実在すること）。それ以外は PATH で探すコマンド名（`[A-Za-z0-9._+-]`、区切り文字を含まない） | #98 |
| `commands[].args` | 任意 | 文字列の配列（既定は空）。`${pluginRoot}`（`package/` の絶対パス）と `${pluginData}`（`data/` の絶対パス）だけを置き換えの対象にする。他の `${...}` は拒否する | #98 |
| `commands[].timeoutSeconds` | 任意 | 1〜86400。省略時の扱いは #98 が決める | #98 |
| `skills[]` | 任意 | 0〜50 件。`name` は重複しない | #99 |
| `skills[].name` | 必須 | 名前の規則。`resonite-` で始まらない。配布先のディレクトリ名になる | #99 |
| `skills[].path` | 必須 | `package/` の中のディレクトリで、直下に `SKILL.md` がある | #99 |
| `recipes[]` | 任意 | 0〜50 件。`name` は重複しない | #100 |
| `recipes[].name` | 必須 | 名前の規則 | #100 |
| `recipes[].path` | 必須 | `package/` の中の JSON ファイル。`prototypes.<prototype>` がオブジェクトであること | #100 |
| `recipes[].prototype` | 必須 | 1〜100 文字 | #100 |
| `recipes[].purpose` | 必須 | 1〜500 文字 | #100 |
| `recipes[].parameters` | 必須 | 文字列から文字列への対応。`key` を含む | #100 |
| `recipes[].ports` | 任意 | 文字列から文字列への対応（既定は空） | #100 |
| `recipes[].requirements` | 任意 | 文字列の配列（既定は空） | #100 |
| `tools[]` | 任意 | 0〜20 件。`name` は重複しない | #98 |
| `tools[].name` | 必須 | 名前の規則 | #98 |
| `tools[].executable` | 必須 | PATH で探すコマンド名（`program` の後者と同じ規則） | #98 |
| `tools[].versionArgs` | 任意 | 文字列の配列。`doctor` が版を表示するときに渡す | #98 |
| `tools[].required` | 任意 | 真偽値（既定は `true`） | #98 |
| `tools[].hint` | 任意 | 1〜500 文字。見つからないときの案内 | #98 |

共通の規則:

- 未知の欄、同じ欄の重複、型の誤りは `PLUGIN_MANIFEST_INVALID` にする。誤りは JSON のパス付きで全部集め、`context.errors` に入れる
- `path` は `/` 区切りの相対パス。空の要素・`.`・`..`・`\`・先頭の `/`・ドライブ名を拒否する
- 外部ツールの差し替え（Meshy の連携など）は、`commands` と `tools` で表す。apply・plan・test に割り込む欄は作らない（親 #95 の範囲外）

名前の規則: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` で 2〜40 文字。次と同じ名前は `PLUGIN_NAME_CONFLICT` にする。

- プラグインの名前とコマンドの名前: 組み込みのコマンド（`apply`・`blender`・`capture`・`component`・`diff`・`discover`・`doctor`・`find`・`flux`・`help`・`hierarchy`・`init`・`inspect`・`item`・`logs`・`manifest`・`observe`・`ping`・`plan`・`plugin`・`plugins`・`scene`・`schema`・`skills`・`slot`・`status`・`test`・`tool`・`type`・`uix`・`validate`・`version`）
- プラグインの名前とスキルの名前: 同梱スキル（`BundledSkillManager.Names`）。スキルの名前は `resonite-` で始まるものも拒否する
- レシピの名前: 組み込みのレシピ（`UixRecipes.Catalog` の名前）
- 導入済みの他のプラグインの名前と、そのコマンド・スキル・レシピの名前（種類ごとに比べる）

組み込みのコマンドの一覧は `PluginNames.cs` に持つ。`Program.cs` にトップレベルのコマンドを足したら、この一覧にも足す。

## 導入元と導入の流れ

`resoloop plugin install SOURCE [--ref REF] [--project DIR] [--json]`

- `SOURCE` が既存のディレクトリなら、ローカルのディレクトリとして扱う。`--ref` を付けたら `PLUGIN_SOURCE_INVALID`
- `SOURCE` が `https://`・`http://`・`ssh://`・`git://`・`file://` で始まるか、`user@host:path` の形なら Git の URL として扱う。`--ref` が無ければ `PLUGIN_GIT_REF_REQUIRED`
- どちらでもなければ `PLUGIN_SOURCE_NOT_FOUND`
- `http(s)://` の URL に利用者の情報（`user@`・`user:token@`）があれば `PLUGIN_SOURCE_INVALID`（記録にトークンを残さないため。認証は Git の credential helper を使う）
- `--ref` は `[A-Za-z0-9._/-]` だけで、`-` で始まらず `..` を含まない

流れ（どこで失敗しても `.staging-<guid>/` を消し、`<name>/` は作らない）:

1. プロジェクトのルートを決める（`--project DIR` は `DIR/.resoloop.json` が必要。省略時は上へ探す）。無ければ `PLUGIN_PROJECT_NOT_FOUND`
2. `.resoloop/plugins/.staging-<guid>/` を作る
3. 写すファイルの一覧を作る
   - ディレクトリ: 上の「ローカルの写し方」。ただし Git の一覧を使うのは、そのディレクトリが作業ツリーの最上位（`git rev-parse --show-toplevel` と一致）のときだけにする。親のリポジトリで無視された場所（`worlds/`・`tmp/` など）にあるディレクトリが空の一覧になるのを防ぐため。`git` が無い、または最上位でなければ `.git` を除く全部
   - Git: `git clone --quiet --no-checkout -- URL <staging>/checkout`、`git rev-parse --verify --quiet --end-of-options REF^{commit}`（無ければ `refs/remotes/origin/REF^{commit}`）でコミットを決める（無ければ `PLUGIN_GIT_REF_NOT_FOUND`）。`git ls-tree -r -z --full-tree COMMIT` の一覧を使い、symlink（120000）と submodule（160000）があれば `PLUGIN_SOURCE_INVALID`。`git checkout --quiet --detach COMMIT` で取り出す
   - `git` は `GIT_TERMINAL_PROMPT=0` と `-c core.fsmonitor=false` で呼ぶ。`git` が無ければ Git の導入元は `PLUGIN_GIT_FAILED`
4. 一覧のファイルに symlink があれば `PLUGIN_SOURCE_INVALID`。ファイル数が 10,000 を、合計が 200 MiB を超えたら `PLUGIN_SOURCE_INVALID`
5. 一覧に `resoloop-plugin.json` が無ければ `PLUGIN_MANIFEST_NOT_FOUND`。manifest を検証する（参照する `path`・`./program` は、この一覧に含まれること）
6. 本体の版が範囲外なら `PLUGIN_INCOMPATIBLE_VERSION`
7. 導入済みのプラグインを `PluginRegistry.List()` で読む。どれかに問題があれば、そのプラグインの誤りで止める（壊れたプラグインがある間は導入しない）。`<name>/` が既にあれば `PLUGIN_ALREADY_INSTALLED`。名前が衝突すれば `PLUGIN_NAME_CONFLICT`
8. 一覧のファイルを `<staging>/package/` へ写し、写した後のバイト列の SHA-256 を記録に書く。`<staging>/checkout` を消す
9. `<staging>/install.json` を書き、`Directory.Move` で `<staging>` を `<name>` へ名前を変える。先に `<name>` ができていたら `PLUGIN_ALREADY_INSTALLED`

この流れで、プラグインのコード（`commands` の program など）は実行しない。Git の clone は相手先の hook を持ち込まない。

## 記録（`install.json`）

```json
{
  "schemaVersion": 1,
  "name": "meshy-glb",
  "version": "0.1.0",
  "source": { "kind": "git", "location": "https://github.com/usaturn/resoloop-meshy.git", "ref": "v0.1.0" },
  "commit": "0123456789abcdef0123456789abcdef01234567",
  "installedAt": "2026-10-16T00:00:00Z",
  "resoloopVersion": "0.1.0-preview.17",
  "files": { "resoloop-plugin.json": "<sha256 の小文字 16 進>", "skills/meshy-glb/SKILL.md": "..." }
}
```

- `source.kind` は `directory` か `git`。`directory` の `location` は絶対パス、`ref` は `null`
- `commit` は Git の導入元だけが持つ（完全な 40 桁）。`directory` では `null`（写した中身が未コミットの変更を含み得るため）
- `files` のキーは `package/` からの `/` 区切りの相対パスで、順序は序数の昇順。値はバイト列の SHA-256（改行の正規化はしない）

## `PluginRegistry`

```csharp
public sealed class PluginRegistry
{
    public PluginRegistry(string projectRoot, string resoloopVersion);
    public static string FindProjectRoot(string? explicitProject, string startDirectory); // PLUGIN_PROJECT_NOT_FOUND
    public string ProjectRoot { get; }
    public string PluginsDirectory { get; }          // <project>/.resoloop/plugins
    public string ResoloopVersion { get; }
    public IReadOnlyList<PluginStatus> List();       // 一覧と照合。問題はプラグインごとの Problem に入れ、例外にしない
    public IReadOnlyList<InstalledPlugin> LoadAll(); // 全部が照合に通ったときだけ返す。問題があれば最初の誤りで例外（全件を context.problems に入れる）
    public InstalledPlugin Load(string name);        // 1 件。無ければ PLUGIN_NOT_INSTALLED、問題があればその誤り
}

public sealed record PluginStatus(string Name, string InstallDirectory, PluginInstallRecord? Record,
    PluginManifest? Manifest, PluginProblem? Problem) { public bool Ok => Problem is null; }
public sealed record PluginProblem(string Code, string Message, IReadOnlyDictionary<string, object?> Details,
    IReadOnlyList<string> Suggestions);
public sealed record InstalledPlugin(string Name, string InstallDirectory, string PackageDirectory,
    string DataDirectory, PluginManifest Manifest, PluginInstallRecord Record);
```

照合（`List()` が 1 件ずつ行う。最初に見つかった問題をそのプラグインの `Problem` にする）:

1. `<name>` が名前の規則に合い、`install.json` を読めて `schemaVersion` が 1、`name` がディレクトリ名と一致する。違えば `PLUGIN_RECORD_INVALID`
2. `package/` の全ファイル（隠しファイルを含む）を記録と比べる。内容の違い・欠け・余分・リンクを `PLUGIN_MODIFIED` にし、`details` に `changed`・`missing`・`unexpected`・`links` を入れる。リンクは symlink と junction（.NET の `LinkTarget` があるもの）で、辿らない。OneDrive のファイルのようにリンクでない reparse point は通常のファイルとして扱う
3. manifest を読み直して検証する。`name`・`version` が記録と違えば `PLUGIN_RECORD_INVALID`
4. 本体の版が範囲外なら `PLUGIN_INCOMPATIBLE_VERSION`（本体を上げた後に検出する）
5. 予約された名前と衝突すれば `PLUGIN_NAME_CONFLICT`（本体が組み込みのコマンドを足した後に検出する）

`.` で始まる項目（`.staging-*` など）は一覧に含めない。`plugins/` が無ければ空の一覧を返す。`LoadAll()` は、さらにプラグインどうしの名前の衝突も `PLUGIN_NAME_CONFLICT` にする。

#98・#99・#100 は、プラグインを使う前に必ず `Load` か `LoadAll` を通す。`List()` の結果を、照合を通さずに使わない。

## 削除

`resoloop plugin remove NAME --yes [--project DIR] [--json]`

- `--yes` が無ければ `CONFIRMATION_REQUIRED`（本体の既存の規則）
- `NAME` が名前の規則に合わなければ `PLUGIN_NAME_INVALID`（パスの組み立てに使う前に止める）
- `<plugins>/NAME` が無ければ `PLUGIN_NOT_INSTALLED`。ディレクトリでなく symlink なら `PLUGIN_REMOVE_REFUSED`
- 記録や中身が壊れていても消せる（壊れたプラグインを外すため）
- 消すのは `<plugins>/NAME/`（`install.json`・`package/`・`data/`）だけ。配ったスキルなど、外のファイルには触れない。結果に「外のファイルは残る」ことを書く

## 一覧

`resoloop plugin list [--project DIR] [--json]` は `List()` の結果を出す。問題があるプラグインも一覧に出し、終了コードは 0 にする（壊れたものを見つけて消せるように）。

```json
{ "ok": true, "data": { "projectRoot": "...", "pluginsDirectory": "...", "plugins": [
  { "name": "meshy-glb", "version": "0.1.0", "ok": true,
    "source": { "kind": "git", "location": "...", "ref": "v0.1.0" }, "commit": "...",
    "installedAt": "...", "path": ".../.resoloop/plugins/meshy-glb", "problem": null } ] } }
```

## エラーコード

| コード | 終了コード | 場面 |
| --- | --- | --- |
| `PLUGIN_PROJECT_NOT_FOUND` | 3 | `.resoloop.json` が見つからない |
| `PLUGIN_SOURCE_NOT_FOUND` | 5 | 導入元がディレクトリでも Git の URL でもない |
| `PLUGIN_SOURCE_INVALID` | 6 | symlink・submodule、大きすぎる、URL の認証情報、`--ref` の誤用・不正な形 |
| `PLUGIN_GIT_REF_REQUIRED` | 2 | Git の URL に `--ref` が無い |
| `PLUGIN_GIT_REF_NOT_FOUND` | 5 | `--ref` がコミットに解決できない |
| `PLUGIN_GIT_FAILED` | 9 | `git` が無い、clone・checkout の失敗 |
| `PLUGIN_MANIFEST_NOT_FOUND` | 6 | `resoloop-plugin.json` が無い |
| `PLUGIN_MANIFEST_INVALID` | 6 | JSON・欄・値の誤り（`context.errors`） |
| `PLUGIN_SCHEMA_UNSUPPORTED` | 6 | `schemaVersion` が 1 でない |
| `PLUGIN_INCOMPATIBLE_VERSION` | 6 | 本体の版が範囲外 |
| `PLUGIN_NAME_CONFLICT` | 6 | 組み込み・同梱・他のプラグインとの衝突 |
| `PLUGIN_ALREADY_INSTALLED` | 6 | 同じ名前が導入済み |
| `PLUGIN_NOT_INSTALLED` | 5 | 指定の名前が無い |
| `PLUGIN_NAME_INVALID` | 2 | `remove` の名前が規則に合わない |
| `PLUGIN_RECORD_INVALID` | 6 | `install.json` が読めない・食い違う |
| `PLUGIN_MODIFIED` | 6 | 導入後にファイルが変わった |
| `PLUGIN_REMOVE_REFUSED` | 6 | 削除の対象が実ディレクトリでない |

## 後続の子への申し送り

- #98: `data/` を作り、プラグインの実行時の書き込み（`__pycache__`、uv の環境など）を `data/` に向ける（例: `PYTHONDONTWRITEBYTECODE=1`、`UV_PROJECT_ENVIRONMENT`）。`package/` に書くと、次に使うときに `PLUGIN_MODIFIED` になる。`data/` を Git の対象外にするかは #98 が決める
- #98: コマンドの解決は組み込みのコマンドを先に見る。プラグインのコマンドは `LoadAll()` を通してから探す
- #99・#100: 配る・読むファイルは `InstalledPlugin.PackageDirectory` の下の manifest の `path` から得る

## テスト

コードを実行して確かめる挙動（解析・検証・分岐・安全条件）があるので、オフラインのテストを書く（AGENTS.md の「テストの採用基準」）。Git の場面は、テストの中で一時ディレクトリに `git init` したリポジトリを `file://` で導入する（ネットワークを使わない）。

| テスト | 確かめること |
| --- | --- |
| `PluginManifestTests` | 正しい manifest の読み込み、欄ごとの誤り（未知の欄、重複、型、名前、パス、`${...}`、版の範囲、件数）、`schemaVersion`、SemVer の順序 |
| `PluginRegistryTests` | 一覧、照合（内容の変更・欠け・余分・symlink）、記録の誤り、版の範囲外、`Load` と `LoadAll` の例外、`.staging-*` の無視 |
| `PluginInstallerTests` | ディレクトリからの導入と記録、Git（タグ・ブランチ・コミット）からの導入とコミットの記録、`--ref` 無し、無い ref、組み込み・同梱・他のプラグインとの衝突、壊れた manifest、範囲外の版、symlink、導入済み、失敗後に何も残らないこと、Git の作業ツリーから無視されたファイルを写さないこと、`remove` が導入先だけを消すこと |

`Program.cs` の `plugin` の節は、テストを書かずに `dotnet run --project src/RLoop.Cli -- plugin ...` の実行で確かめる（既存のテストに `Program.Main` を呼ぶ仕組みが無く、節は Core の呼び出しと表示だけのため）。

## 検証

```bash
dotnet build ResoLoop.slnx
dotnet test ResoLoop.slnx --no-build
```

加えて、一時プロジェクトで `plugin install`（ディレクトリと `file://` の Git）、`plugin list --json`、ファイルを書き換えた後の `plugin list`、`plugin remove --yes` を実行し、出力を記録する。実機（Resonite）は使わない。

## 反映先

- コード: fork `usaturn/resoloop` のブランチ `feat/plugin-core`（`upstream/main` の `99c59be` から）。fork へ push し、fork の `main` を対象に PR を作る。fork の `main` へのマージは利用者の指示による
- 文書: create-reso-world のブランチ `docs/issue-97-plugin-core` から、この Spec と Plan の文書専用 PR を作る
- 上流への PR は #105 で扱う。この作業では上流に書き込まない
