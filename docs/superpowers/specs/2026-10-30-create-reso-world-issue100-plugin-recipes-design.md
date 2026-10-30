# #100 プラグイン UIX レシピ設計

## 管理・実行許可

- 状態: `draft`。内容承認を得たという記録ではない。
- Issue: https://github.com/usaturn/create-reso-world/issues/100 （親 #95、キー `plugin-recipes`）。
- 利用者の明示入力: `https://github.com/usaturn/create-reso-world/issues/100 --base feat/plugin-v2 --assign inspect=pi-gpt,claude-opus,devin-swe,pi-deepseek --merge`（`/skill:issue-to-pr`）。通常判断は推奨案で決め、実装・検証・commit・push・PR・指定ループを実行する許可。マージはループの finalize.py のみ。文書 PR はマージしない。
- コード対象: `usaturn/resoloop`、捕捉 ref `origin / refs/heads/feat/plugin-v2`、SHA `dd0b40fb216b0c9fbd82da44903195a885104015`。
- 文書対象: `usaturn/create-reso-world`、捕捉 `origin / refs/heads/main`、SHA `acd288c3e81a6c108136e37815e718a0fe088195`。
- 根拠: 親 #95 現行本文と https://github.com/usaturn/create-reso-world/issues/297#issuecomment-6521059117 。#297 は completed、コード PR resoloop#26 の head/merge が捕捉 base の祖先であり、公開 Spec/API・Plan が文書 main に存在する。旧 #97 の完了は実装入力にしない。
- issue helper/担当検査: 指定 base 明示。実装は既定 `self`、fallback なし。ループ inspect は利用者指定4担当、上限3サイクルは既定。fix implement=`claude-opus`、self-review/fix-check=`self` は設定の適用であり利用者指定とはしない。

## 目的・境界

プロジェクトに導入したレシピを、読み取り専用 API の一覧・説明・読取・新規ファイルへの export と宣言 `$recipe` から利用する。組み込みの Catalog・既存名・生成キーを維持する。CLI の list/describe/export 結線は後続 #298 の所有で、本 Issue はその消費可能な API を渡す。

変更を許すファイルは、新規 `src/RLoop.Core/Plugins/PluginRecipeResolver.cs`、`src/RLoop.Core/UixRecipes.cs`（Catalog 除外）、`src/RLoop.Core/ApplyDocumentCompiler.cs`、`tests/RLoop.Tests/PluginRecipeTests.cs`、`tests/fixtures/plugins/recipes/` に限定する。`ApplyDocument.cs` は捕捉版に存在せず、その型は `ApplyWorkflow.cs` にある。Compile 内で主入力を保持すれば変更不要なので、親コメント6489576253が指摘する編集権限の拡張は行わない。

既存 Plugins ファイル、Program.cs/CommandLine.cs、ApplyWorkflow.cs、同梱スキル、他子所有コード、ワールド、親 checkout、reviews/、fork main は変更しない。実行フック・署名・sandbox・悪意ある同一ユーザへの完全防御は追加しない。

## 方針・インターフェース

### 読み取り専用 resolver

`RLoop.Core.Plugins.PluginRecipeResolver : IDisposable` を新設する。

- `PluginRecipeResolver(PluginRegistry registry)`。選択済みプロジェクト/version/reservations は呼び出し側が既存 F API で与える。`string ProjectRoot { get; }`。
- `IReadOnlyList<UixRecipe> Catalog { get; }` はプラグインの修飾済み名だけを ordinal 順で返す。
- `UixRecipe Describe(string name)` と `string Read(string name)`。名前は `<plugin-name>:<recipe-name>` の完全一致のみ。未導入なら `PLUGIN_NOT_INSTALLED`（対象名を示す）、導入済みだがレシピなしなら `UIX_RECIPE_NOT_FOUND`。裸名・case fallback は探索しない。
- `static PluginRecipeResolver ForDocument(string mainInputPath, string resoloopVersion, PluginNameReservations reservations)`。主入力の絶対パスのディレクトリから `PluginRegistry.FindProjectRoot(null, directory)` を使う。include や cwd から探索しない。
- 初回プラグイン利用で `OpenVerified()` を呼び、全 JSON/metadata の読取完了まで lease を保持する。読み取った JSON は instance 内に保持し、Dispose で lease を解放。以降にファイルを無検証で読み直さない。公開 metadata/一覧は読み取り専用。失敗時にも lease を解放する。
- package path と JSON/prototype 検証は F の既存検証を再利用。JSON は実行しない。manifest metadata と JSON の対応を変更せず、Read/export は UTF-8 で読んだ元のテキスト（BOMは除去）を返す。再シリアライズしない。`UixRecipe.Name` は常に修飾済み名とし、一覧の項目をそのまま Describe/Read/Export へ渡せる。
- 例外は compiler/UixRecipes でもコードを変えずに伝える。project無しは `PLUGIN_PROJECT_NOT_FOUND`、未導入は `PLUGIN_NOT_INSTALLED`、不整合は F のコードのまま。構文不正な修飾名と resolver 未指定の修飾名は `UIX_RECIPE_NOT_FOUND` とし、cwd探索しない。単なるエラーコード照合の恒久テストは不要。

### UixRecipes 合成 API

既存メソッドを維持し、次の overload/API を追加する（Catalog 本体は不変）。

- `IReadOnlyList<UixRecipe> List(PluginRecipeResolver? resolver = null)` は組み込み順の後へプラグインを ordinal 順で加える。
- `UixRecipe Describe(string name, PluginRecipeResolver? resolver)`。
- `string Read(string name, PluginRecipeResolver? resolver)`。
- `string Export(string name, string output, PluginRecipeResolver? resolver)`。

裸名は組み込みだけ、修飾名は指定 resolver だけ。resolver なしで修飾名を使っても cwd で勝手に探索しない。export は検証/読取後、既存の FileMode.CreateNew で新規ファイルだけに書く。既存出力を破壊しない。

### コンパイラの文脈

既存 `Compile(string path)` を維持し、`Compile(string path, string resoloopVersion, PluginNameReservations reservations)` を追加する。任意プロジェクト resolver の注入は受け付けず、必ず主入力から探索する。

- Compile 開始時に主入力を絶対パスへ固定し、instance の Context が resolver factory を持つ。include の merge によってこの入力は変えない。Compile が Context/resolver を所有し、成功・例外いずれでも呼び出し終了前に Dispose する。返す Result に lease を持ち越さない。
- `$recipe` の修飾名が実際に展開される場合だけ resolver を作る。組み込みだけの Compile では project/version/plugin area の読取をしない。ワールド外の従来利用、壊れたプラグインがあるプロジェクトでの組み込み利用を保つ。
- 既存1引数版の version は、CLI entry assembly（assembly名 `resoloop`）の informational version（`+` の後を除外）、なければ同 assembly の3桁 versionを使う。Core の既定版1.0.0を ResoLoop版として使わない。非CLIホストがプラグインを使う場合は明示版 overload を使用する。版不明は `PLUGIN_INCOMPATIBLE_VERSION` で停止し、推測しない。可変 global は作らない。
- 自動文脈の reservations は空の immutable snapshot。これは読み取り専用レシピ消費であり、#98/#298 の導入/コマンド予約 catalog を所有しない。修飾名は組み込みの裸名と衝突しないため Recipes に裸の Catalog 名を渡さない。選択プロジェクトを扱う CLI は registry の実 reservations を渡せる。
- プラグイン生成キー基点: `uix-plugin--<plugin-name>--<recipe-name>--<caller-key>`。既存の `uix-<builtin-name>--<caller-key>` は変えない。manifest 名規則は既存 PluginNames を使い連続 `--` を認めない。caller key の既存規則は維持する。
- parameter 照合・override の caller 所有・展開制限・重複キー検査は既存経路を使う。同じ入力/導入状態は同じ出力。未導入・不整合・非対応版は Compile 時に例外となりワールド操作より先に止まる。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| instance resolver + verified lease | Catalog に混合、可変 static | プロジェクト間を隔離し既存組み込みを不変にする | issue-to-pr の推奨判断委任 |
| Compile 内で主入力固定、遅延解決 | Load への注入、cwd/include 起点 | 所有範囲内で default CLI Load を支え、別ワールドを選ばない | ApplyWorkflow.cs が必要になれば親裁定前に停止 |
| CLI entry 版、非CLIは明示版 | Core version、固定0.2.0 | 実ホストの ResoLoop 版との整合を守り将来版を固定しない | 版を特定できない plugin 利用は停止 |
| 名前空間付きレシピ、Recipes空予約 | builtin裸名を予約 | 同じローカル名の別pluginを区別できる | F APIを変更しない |
| APIまで、CLI結線は#298 | Program.csを直接変更 | 親の所有境界と4機能の統合順序を守る | CLI結線完了とは報告しない |
| inline / executing-plans | Taskごと別実装子 | 2 Task が同じ tests と resolver API を逐次変更するため | 最後の独立全体レビューは必須 |

## 受け入れ基準・検証

動作環境: 本 Linux Dev Container、global.json に従う .NET 10。Windows は公開CIの結果を区別して記録。Resonite/Blender/実認証は使わない。

実入力: 一時プロジェクト「主 ワールド」と「別 ワールド」、主入力が別プロジェクト内JSONをincludeし、cwdも別ワールドの形。`aa-plugin:sample-card` と `bb-plugin:sample-card`、`$with.key=panel_1`、複数行/日本語を含むレシピ・metadataを使う。expected key は仕様文字列から直接記す。

防御範囲: 主入力のproject取り違え、bare名の暗黙探索、別pluginの同ローカル名、既存exportの上書き、不整合・未導入のままの展開、組み込み利用の回帰。package/link/hash/lock安全性は既存Fの守りを再実装/網羅しない。悪意ある同一ユーザの同時差替え、runtime UIX動作、CLI統合は本Issueの完了主張に含めない。

S テストのみを代表例で追加し、拒否には正しく通る例を残す。S: namespace/key取り違え、main/include/cwd取り違え、無検証read、export上書き。単なる文言・存在・構文・一覧固定値F/Lは追加しない。既存テストと dotnet build/test、差分確認、実CLI offline validateで補う。

## builder check の決定

読み取り専用の builder check で提示された5点は、raw text保持・metadataの修飾済みName・エラーコード透過・Compile内のfinally解放・不正名/null resolverのnot-foundという上記のエージェント判断で確定した。仕様の意味・編集範囲・実行許可は変更していない。最初の sp-review dispatch は必要なコードレビュー形式を欠くとして NEEDS_CONTEXT で終了し、設計調査の sp-research で builder check を行った。人の内容承認として記録しない。

## 停止記録（2026-10-30）

実装前の `recheck_bases` が終了コード2で停止した。`origin/refs/heads/feat/plugin-v2` は捕捉 `dd0b40fb216b0c9fbd82da44903195a885104015` から `454b54cd961e078dac2a71fe1270529ebff11cd2` に進んだ（resoloop#27、2026-10-30T13:02:12Z merge）。新SHAをbaseとして採用せず、実装・push・PR・ループは未実施。コードworktreeは旧baseのcleanなまま。

移動差分は BundledSkillManager.cs、PluginSkillManager.cs、ProjectInitializer.cs、PluginSkillSyncTests.cs の4ファイル（618追加/14削除）。レシピの直接所有ファイルは変わっていないが、共有スキル資源/初期化との統合検証は必要であり、旧版の成功を新版へ流用しない。旧baseの `dotnet test ResoLoop.slnx --nologo` は終了0、573 unit +22 offline成功（live opt-in/URLをchild環境から除去）。新版は未検証。

このdraft Spec/Planは部分成果としてローカルcommitし、公開未実施。Issueへの復元資料公開はGit ref/PRの公開とは区別する。再開にはbase移動を踏まえた新baseの捕捉・既存worktree/文書の再利用を明示する継続指示が必要。自動で旧捕捉値を書き換えない。

## 公開・終了

コード PR は `feat/plugin-v2` 宛て、文書専用 PR は create-reso-world/main 宛てで相互リンク。両方 `Refs https://github.com/usaturn/create-reso-world/issues/100`。子Issueのcloseと親更新は調整役に残す。全未push commitを親のscan-before-push.shで検査し、捕捉baseが移動したら差し替えず停止する。PR後は指定レビュー修正ループのみでコード変更/mergeを行う。

handoff pair・復元manifestの正確な内容を公開し、遠隔から新規directoryへ復元してhash/bytes/JSONを検証する。子の実状態・結果・再開方法のコメント後、自分の予約SHAだけをexpected leaseで解放する。検証・公開・マージの実績は後から追記し、現時点では未実行とする。
