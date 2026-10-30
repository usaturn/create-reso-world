# Issue #99: プラグインのスキルを init・skills sync で配る

## 管理・許可

- 状態: **draft**（内容の承認なし。issue-to-pr の委任により推奨案で決めたエージェントの判断であり、利用者の承認を推測しない）。文書管理: `usaturn/create-reso-world`。コード対象: `usaturn/resoloop`。
- Issue: https://github.com/usaturn/create-reso-world/issues/99 （親 #95、ボードのキー `resoloop-plugins-board`、子のキー `plugin-skills`）。
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/99 --base feat/plugin-v2 --assign inspect=pi-gpt,claude-opus,devin-swe,pi-deepseek --merge`。issue-to-pr の定めにより、通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで続け、`--merge` のため PR 修正ループで修正不要を確かめたら、ループの `finalize.py` がコードの PR を `feat/plugin-v2` へマージする。文書の PR はマージしない。上流への投稿・fork main の更新・Windows 実機確認の主張は許可に含まない。
- 親の承認済み D-1〜D-6: [親設計](2026-10-29-create-reso-world-issue95-plugin-replan-design.md)（内容承認 `d009286968a21c916bafb39b2308ebaa09d40c4c`）の D-5 を本書で詳細化する。4機能・D-1〜D-6・所有範囲は縮小・再設計しない。
- 先行: F #297（`closed`・`completed`）。Core API は [F の Spec](2026-10-29-create-reso-world-issue297-plugin-core-design.md) の 3 章。コード PR usaturn/resoloop#26 の merge `dd0b40fb216b0c9fbd82da44903195a885104015` が `origin/feat/plugin-v2` の先端であることを確認した。
- コード base: `usaturn/resoloop` `refs/heads/feat/plugin-v2` `dd0b40fb216b0c9fbd82da44903195a885104015`。文書 base: `usaturn/create-reso-world` `refs/heads/main` `acd288c3e81a6c108136e37815e718a0fe088195`。
- `PARENT_ROOT`: `/workspaces/reso-world`。`DOC_ROOT`: `/workspaces/reso-world/.worktrees/create-reso-world-issue-99-plugin-skills`（`docs/create-reso-world-issue-99-plugin-skills`）。`CODE_ROOT`: `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-99-plugin-skills`（`feat/create-reso-world-issue-99-plugin-skills`）。
- 予約: `refs/heads/agent-claims/issue-99` / `2e3ea301e035b55842eeaa327506b1a3658c2906`（session `10442310-e25a-4f1e-b336-9060461b5215`、[開始の記録](https://github.com/usaturn/create-reso-world/issues/99#issuecomment-6521349746)）。ループの終了後に結果を子 Issue に書いてから、保存した SHA の lease で解放する。
- ベースライン（実装前、`CODE_ROOT`）: `dotnet build ResoLoop.slnx --nologo` 警告 0・エラー 0、`dotnet test ResoLoop.slnx --nologo --no-build` unit 573 件・offline integration 22 件成功、失敗/skip 0。

## 1. 目的・非目的

導入済みで照合を通ったプラグインが manifest の `skills` で宣言したスキルを、`init`・`skills sync --check|--update` の Core API で `.agents/skills/<skill-name>/` へ配る。同梱スキルと同じく、利用者が編集したファイルや所有の記録がないファイルを上書きしない。配布の記録は同梱の `.resoloop-bundled.json` と分けて `.agents/skills/.resoloop-plugins.json` に持つ。

範囲は Issue が所有する次のファイルだけ。

- `src/RLoop.Core/Plugins/PluginSkillManager.cs`（新設）
- `src/RLoop.Core/BundledSkillManager.cs`
- `src/RLoop.Core/ProjectInitializer.cs`
- `tests/RLoop.Tests/PluginSkillSyncTests.cs`（新設）
- `tests/fixtures/plugins/skills/`（今回は使わない。テストのパッケージは一時ディレクトリに生成する）

非目的・変えないもの:

- `Program.cs`・`CommandLine.cs` の CLI 結線は I #298 が専有する。本書の API は I が呼ぶ。今回の PR では CLI の挙動は変わらない。
- F の `src/RLoop.Core/Plugins/` の既存ファイル（registry・installer・manifest・path policy 等）、#98 の所有ファイル、レシピのコード、`.claude/` の操作。
- 既存の `BundledSkillManager.Sync(string, bool)` と `ProjectInitializer.Initialize(string)` の挙動・生成物・結果の形。プラグイン無しの `init`・`sync` の生成物と同梱の記録形式。
- remove でスキルを消す機能、データを保持する更新、配布済みファイルの自動削除・掃除。
- 署名・サンドボックス・悪意ある同一ユーザの差し替えへの完全な防御。ハッシュは意図しない変更の検知である。
- Claude 用リンクは create-reso-world の既存 `scripts/new-world.sh --apply <world>` が担当する。

## 2. 決定記録

すべて issue-to-pr の委任（「通常の設計判断は推奨案で決め」）によるエージェントの判断。親 D-5・4機能・所有範囲・安全境界を変える必要が出たら停止して親で裁定する。

| 論点 | 選択した案 | 検討した別案 | 選択理由 |
| --- | --- | --- | --- |
| API の入口 | `BundledSkillManager.Sync` と `ProjectInitializer.Initialize` に、版と予約名を受け取るオーバーロードを足す。プラグインの計画・適用は `PluginSkillManager` の internal にし、公開するのは結果の型と記録のパスだけ | (a) `PluginSkillManager.Sync(registry, update)` を公開し、I が同梱と別々に呼ぶ。(b) `PluginRegistry` を引数にとる | (a) は同梱と全プラグインの競合をまとめて事前確認できず、I の呼び順の誤りで片方だけ書かれる。(b) は I が祖先探索の registry を渡すと別プロジェクトのスキルを配り得る。版と予約名を受け取り、対象ディレクトリそのものを明示のプロジェクトとして開けば取り違えない |
| プラグインを参加させる条件 | 対象ディレクトリ直下に `.resoloop.json` があり、かつ `.resoloop/plugins` が存在するときだけ registry を開く（明示のプロジェクトとして。祖先を探さない）。それ以外はプラグイン無しで、記録も読まない | marker だけで判断する | プラグイン無しのプロジェクトで、新しい API でも既存と同じファイルだけを読み書きする。`plugins` が無ければ導入物は無い |
| 照合の lease | `PluginRegistry.OpenVerified()` の lease を計画の前に取り、すべての書き込みが終わるまで保持する | 照合の結果だけを取ってロックを外す | F の Spec が後続に求める使い方。配布中に別プロセスの install/remove が BUSY になる |
| 照合に失敗したプラグインがあるとき | `OpenVerified` の例外をそのまま返し、同梱を含めて何も書かない | 壊れたプラグインを飛ばして残りを配る | F の LoadAll は問題をまとめて拒否する。変更されたパッケージのスキルを配らない。remove は壊れた導入でも実行でき、回復手段がある |
| 予約名 | 受け取った予約名のスキル名に `BundledSkillManager.Names` を足した `PluginNameReservations` で registry を開く。さらに配布の計画でも `resonite-` 接頭辞と同梱名を拒否する | 呼出元が渡した予約名だけを使う | 同梱名の予約を I の渡し忘れに依存させない。`resonite-` は F の `FindConflicts` も拒否するが、記録・配布の層でも境界を持つ |
| 配る対象 | `skills[].path` の下にある、照合済みの `install.json` の `files` に載った通常ファイルすべて（`SKILL.md`・参照文書・スクリプト等）を、相対パスを保って `.agents/skills/<name>/` へ | `SKILL.md` だけ | D-5 の「宣言する skills/ の通常ファイル」。参照文書・スクリプトを含むスキルが動かない |
| 比較と書き込み | バイト列のまま比較・書き込みし、ハッシュは小文字 16 進の SHA-256（`install.json` と同じ） | 同梱と同じく改行を正規化したテキストのハッシュ | プラグインのスキルは画像・スクリプト等のバイナリを含み得る。改行だけの違いは利用者の編集として扱い、上書きしない側に倒す（下の「既知の制限」） |
| 記録の単位 | `.agents/skills/` からの相対パスごとに、所有するプラグイン名と最後に配った SHA-256 | スキル単位の記録 | 利用者がスキルのディレクトリにファイルを足しても、宣言していないファイルには触れない。編集の判定はファイルごとに行う |
| 記録を消すか | 消さない。宣言から外れた記録（remove 後・版の更新で無くなったファイル）は「保持」として残し、報告する | 存在しないファイルの記録を掃除する | D-5「アンインストール後も配ったファイルと、その保護に必要な記録は残す」。check と update の判定を一致させる（update だけが記録を変える状態を作らない） |
| 別プラグインが所有するパス | ファイルが存在すれば `owner-conflict`。存在しなければ書いて所有を移す。内容が配る内容と同じなら所有を移すだけ | 内容が記録と同じなら上書きを許す | 取り外したプラグインの残したファイルを、別プラグインが黙って置き換えない。ファイルを消せば利用者が解決できる |
| 失敗と記録 | 計画で全競合を確かめた後、同梱（ファイル→同梱の記録）→プラグインのファイル→プラグインの記録の順に書く。プラグインの記録は最後に一度だけ書き、書けたファイルと採用したファイルの項目だけを更新する | 記録を先に書く、ファイルごとに記録を書く | 途中で失敗しても、書いていないファイルを配布済みと記録しない。書けたファイルは次回、内容が同じなので記録に採用される |
| ファイルの書き込み方 | 計画でリンク・特殊ファイル・ディレクトリの位置を拒否した後、`File.WriteAllBytes` で直接書く（同梱と同じ） | 一時ファイル＋rename | 同梱の書き方と揃える。途中で強制終了したときの部分書き込みは次回 `modified-conflict` として止まり、上書きしない側に倒れる。一時ファイルの残骸を利用者のスキルのディレクトリに残さない |
| init での扱い | init は既存ファイルを上書きしない規則を保つ。プラグインのファイルは、無ければ作り、同じなら変更なし（記録に採用）。`update-available` と各種 conflict は `INIT_FILE_EXISTS` として、何も書かずに止まる | init でも `update-available` を更新する | 同梱スキルの init と同じ扱い（版が上がった同梱スキルも init は上書きしない）。更新は `skills sync --update` で行う |
| 結果の形 | 既存の `SkillSyncResult` と `ProjectInitResult` の最後に、省略時 `null` の `Plugins` を足す。プラグインが参加しない・宣言も記録も無いときは `null` | 新しい包む型を返す | CLI の出力は `null` を書かない設定なので、プラグイン無しの JSON 出力は変わらない。I は呼ぶ関数を差し替えるだけで既存の表示が動く |
| 実装の担当 | このセッション（`self`）。`implement_task.py check` は `{"agents": ["self"], "fallback": []}`、雛形 `.devcontainer/agent-runner.toml` の既定の適用（利用者の指定ではない） | runner の担当に Task を依頼する | 既定のとおり |
| 実行方式 | `superpowers:executing-plans`（inline）。最後にブランチ全体のレビューを別のサブエージェントに依頼する | `subagent-driven-development` | Task は同じ 3 ファイルを順に変える結合した変更で、独立していない |
| PR 修正ループ | `--merge` で `loop.py check-options --assign inspect=pi-gpt,claude-opus,devin-swe,pi-deepseek` を確認済み。`inspect` のレビュアー `pi-gpt`・`claude-opus`・`devin-swe`・`pi-deepseek` は利用者の指定。サイクルの上限 3、修正の担当 `claude-opus`、自己レビュー・fix-check の担当 `self` は既定の適用 | — | 利用者が書いたオプションだけをループへ渡す |

## 3. 公開 API

namespace `RLoop.Core`（既存の型）と `RLoop.Core.Plugins`（新しい型）。I #298 はこの API だけを使う。

```csharp
namespace RLoop.Core.Plugins;

public sealed record PluginSkillFileStatus(string Plugin, string Skill, string Path, string Status,
    string PackageHash, string? InstalledHash, string? RecordedHash, string? RecordedPlugin);
public sealed record PluginSkillRetainedFile(string Plugin, string Path, string RecordedHash);
public sealed record PluginSkillSyncResult(string Mode, bool Synchronized, IReadOnlyList<string> Updated,
    IReadOnlyList<PluginSkillFileStatus> Files, IReadOnlyList<PluginSkillRetainedFile> Retained);

public static class PluginSkillManager
{
    public const string RecordRelativePath = ".agents/skills/.resoloop-plugins.json";
}
```

```csharp
namespace RLoop.Core;

public sealed record SkillSyncResult(string RootDirectory, string Mode, bool Synchronized,
    IReadOnlyList<string> Updated, IReadOnlyList<SkillSyncEntry> Skills,
    PluginSkillSyncResult? Plugins = null);
public sealed record ProjectInitResult(string RootDirectory, string ProjectName,
    IReadOnlyList<string> Created, IReadOnlyList<string> Unchanged, IReadOnlyList<string> NextSteps,
    PluginSkillSyncResult? Plugins = null);

public static class BundledSkillManager
{
    public static SkillSyncResult Sync(string targetDirectory, bool update);               // 既存。変更なし
    public static SkillSyncResult Sync(string targetDirectory, bool update,
        string resoloopVersion, PluginNameReservations reservations);                      // 新設
}
public static class ProjectInitializer
{
    public static ProjectInitResult Initialize(string targetDirectory);                    // 既存。変更なし
    public static ProjectInitResult Initialize(string targetDirectory,
        string resoloopVersion, PluginNameReservations reservations);                      // 新設
}
```

- `resoloopVersion` は I が渡す本体の版（`PluginRegistry` の互換判定に使う）。`reservations` は I が #98 の catalog から作る予約名。スキル名には同梱名を必ず足す。
- 新設の 2 つは、プラグインが参加しないとき（2 章の条件）、既存の関数と同じ結果・同じ生成物・`Plugins = null` を返す。
- 新設の `Sync` の `Synchronized` は同梱とプラグインの両方が同期済みのとき真。`Updated` は同梱・プラグインのファイル・両方の記録のうち書いたものすべて（書いた順）。`Plugins.Updated` はそのうちプラグインのファイルと記録だけ。`Mode` は `check`・`update`。
- 新設の `Initialize` の `Created`・`Unchanged` は既存どおり基本ファイルと同梱スキルだけ。プラグインの分は `Plugins`（`Mode = "init"`）に入る。
- `Plugins` が `null` になるのは、プラグインが参加しないか、照合済みのプラグインがスキルを宣言せず、記録ファイルも無いとき。

## 4. 配布の仕様

### 計画（書き込み前）

lease 内の各プラグインの各 `skills[]`（名前 `S`、パス `P`）について、`install.json` の `files` のうち `P + "/"` で始まる相対パス `R` を集め、配布先 `S/<R から P/ を除いた部分>`（`.agents/skills/` からの相対）を作る。パッケージの内容のハッシュは照合済みの `files[R]`。

スキル名が `resonite-` で始まる、または同梱名と一致する（大小文字を区別しない）なら、そのプラグインのスキル全体を `reserved-conflict` とする。

配布先ごとに次の順で状態を決める（`I` = 現在のファイルの SHA-256、無ければ null。`H` = パッケージ。記録の項目 = 所有者 `O` とハッシュ `RH`）。

1. 安全でない経路 → `unsafe-path-conflict`。プロジェクトのルート（registry の解決済みの実パス）から配布先までのどこかがリンク・特殊ファイル、途中の階層が通常ファイル、配布先がディレクトリ。このときファイルを読まない。
2. `I` が null → `missing`（書く）。記録が別のプラグインでも書き、所有を移す。
3. `I == H` → 記録が同じプラグインで `RH == H` なら `current`、そうでなければ `record-update-required`（記録だけ更新。所有の採用を含む）。
4. `I != H` で記録が無い → `untracked-conflict`。
5. `I != H` で `O` が別のプラグイン → `owner-conflict`。
6. `I != H` で `I == RH` → `update-available`（書く）。
7. それ以外 → `modified-conflict`。

宣言から外れた記録の項目は `Retained`（所有者・パス・記録のハッシュ）として報告する。ファイルは読まない。状態の判定・書き込みに影響しない。

### 記録ファイル

```json
{
  "schemaVersion": 1,
  "files": {
    "alpha-guide/SKILL.md": { "plugin": "alpha-plugin", "sha256": "<小文字 16 進 64 桁>" }
  }
}
```

- UTF-8（BOM なし）、インデント付き、LF、末尾の改行。キーは序数順。最大 8 MiB。
- 読むときは、リンクを拒否し、F の bounded JSON reader で UTF-8・重複プロパティを検査し、`schemaVersion == 1`、未知のプロパティなし、キーが移植可能な相対パスで 2 要素以上かつ先頭がスキル名の規則に合い、大小文字を無視して重複しない、`plugin` が名前の規則に合う、`sha256` が小文字 64 桁であることを確かめる。違えば `PLUGIN_SKILL_RECORD_INVALID`（`ValidationFailed`）で何も書かずに止まる。壊れた記録を空として扱わない。
- 書くのは、新しい内容が既存と違い、かつ項目が 1 つ以上あるときだけ。プラグイン無しや宣言が無いときに空の記録を作らない。

### 書き込み（`--update`・init）

1. 同梱の衝突とプラグインの conflict を合わせて確かめる。1 つでもあれば何も書かずに止まる。sync は既存の `SKILL_SYNC_CONFLICT`（`context.conflicts` は同梱の項目、プラグインの項目があれば `context.pluginConflicts`）。init は既存の `INIT_FILE_EXISTS`（`context.conflicts` にプラグインのパスも加え、`context.pluginConflicts` に詳細）。check でも conflict は同じ例外（同梱と同じ）。
2. 同梱を既存どおりに書く（init は基本ファイル、sync は同梱のファイルと記録）。
3. プラグインの `missing`・`update-available` を書く。パッケージのファイルを読み、ハッシュが `files[R]` と一致しなければ `PLUGIN_MODIFIED` で止まる。親ディレクトリを作り、バイト列をそのまま書く。
4. 書けたファイルと `record-update-required` の項目を記録に反映し、記録を最後に書く。途中の例外では記録を書かない。
5. init では `update-available` も conflict として 1 で止まる。

### 既知の制限

- 改行だけを変えたファイル（Windows の Git の `autocrlf` など）は `modified-conflict` になる。上書きしないので安全だが、利用者が解決する必要がある。
- 非協調の同一ユーザによる計画後の差し替え（TOCTOU）は対象外。協調するプロセスの install/remove/sync は lease で BUSY になる。
- 強制終了による部分書き込みは次回 `modified-conflict` で止まる。自動回復はしない。

## 5. 受け入れ基準

この本文を実装・レビューの依頼の両方に渡す。

- **動作環境**: Linux の本 Dev Container、`global.json` の .NET（10.0.201 系）、xUnit。一時ディレクトリと一時プロジェクトだけで確かめる。Windows も利用対象（公開 CI は windows-latest）だが、Windows で実行していない状態を確認済みと報告しない。Resonite・Blender・認証情報・グローバル導入は不要。
- **実入力**: 空白と日本語を含むプロジェクト `作業 ワールド`、日本語のファイル名を含むスキル（`references/手順.md`）、`SKILL.md` と参照文書を持つ 2 版のプラグイン、利用者が編集した配布済みファイル、記録の無い同名のスキル、外部ディレクトリへのリンクになった `.agents/skills/<name>`、remove 後に残ったスキル、読み取り専用で書けない配布先。
- **防御範囲**: 利用者の編集・記録の無い既存ファイル・リンク先を上書きしない。全競合を確かめる前に何も書かない（同梱を含む）。書けなかったファイルを配布済みと記録しない。remove 後も配ったファイルと記録を残し、再導入でも編集を守る。プラグイン無しのプロジェクトでは、新しい API でも記録を作らず、既存と同じ生成物にする。各拒否には正しく通る例を残す（編集の無いファイルは更新される、編集を戻せば更新できる、記録の無い別名のスキルには触れない）。
- **対象外の反例**: 悪意ある同一ユーザの差し替え、署名、CLI の結線（I）、Windows 実機。改行だけの違いを同じとみなすこと（制限として残す）。

## 6. テスト方針

`AGENTS.md` の「テストの採用基準」の S（気付けない損害）だけを、`tests/RLoop.Tests/PluginSkillSyncTests.cs` に代表例で書く。プラグインのパッケージは一時ディレクトリに生成し、実際の `PluginInstaller` で導入する。

| テスト | 守り（S） | 正しく通る例 |
| --- | --- | --- |
| 編集の保護と remove・再導入 | 利用者の編集を上書きしない、全競合の確認前に書かない（同梱を含む）、remove 後もファイルと記録を残す | 編集の無いファイルの更新、編集を戻した後の更新 |
| 記録の無いファイルとリンク先 | 所有の記録の無い同名ファイル・リンク先の外部ディレクトリを書き換えない | 衝突を取り除いた後の配布 |
| 書き込みの失敗 | 書けなかったファイルを配布済みと記録しない、失敗を成功と返さない | 書けるようにした後の更新 |
| init とプラグイン無し | init が利用者の編集を上書きしない、プラグイン無しで記録を作らない | init が欠けたスキルを作る |

書かないもの: 状態の文字列・記録の書式・予約名の一覧の固定値（F）、不正な記録が例外になるだけの経路（L）、同じ守りの組み合わせの網羅（D）、`owner-conflict`（記録の無いファイルの守りと同じ層の組み合わせ）。既存の同梱スキルのテストは変更しない。

## 7. 公開・引き渡し

- コード: Gitleaks の検査を通した SHA を `feat/create-reso-world-issue-99-plugin-skills` へ push し、base `feat/plugin-v2` の fork 内 PR を 1 件作る。本文は `Refs https://github.com/usaturn/create-reso-world/issues/99`（Issue は別のリポジトリ）。
- 文書: Spec・Plan だけを含む `usaturn/create-reso-world` の main 宛ての文書専用 PR。マージしない。
- `--merge`: コードの PR で PR 修正ループを回し、修正不要ならループの `finalize.py` が `feat/plugin-v2` へマージする。ボードの子なので Issue の close・親の台帳の更新は調整役に任せ、子 Issue に結果・再開の方法を書いてから予約を解放する。
- 引き渡し: I #298 に、3 章の API・プラグインが参加する条件・`Plugins` の `null` の規則・エラーコードを渡す。I は text 出力でプラグインの項目を表示する責務を持つ。
