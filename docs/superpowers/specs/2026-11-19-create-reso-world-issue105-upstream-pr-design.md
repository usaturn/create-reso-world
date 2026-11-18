# Issue #105: 汎用プラグイン機構の上流PR

- 文書の状態: draft（文書内容への approved の記録とは分ける）
- 対象: https://github.com/usaturn/create-reso-world/issues/105
- 作成日: 2026-11-19 JST
- コードの提出元: usaturn/resoloop:feat/plugin-system
- PRの宛先: orange3134/resoloop:main
- 実行許可: 2026-11-19 の利用者の明示指示「上流への投稿の実行許可を求めなくてよいです。準備ができたら上流に直接 PR を出してください」。準備と投稿を自律的に進め、投稿直前の確認を改めて求めない。上流マージの判断は作者に委ねる。

## 目的

前段 usaturn/resoloop#33 が公開した検証済みの汎用プラグイン機構を上流へ提案する。4機能（外部コマンド・スキル・UIXレシピ・doctor）と plugin install/list/remove、文書・最小例をまとめて届ける。

今回の実行の到達点は、上流PRの作成と提出内容・検証根拠の記録である。Issue #105 全体は、必要な上流PRの実際のマージを確認するまで open とする。

## 入力と根拠

| 対象 | 確認した値 |
| --- | --- |
| 提出head | c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b |
| 提出tree | 9d1fa089f93de4e0c74afb63da64a83ca439b6a6 |
| 上流main | 32309ca3deb4560e6a31a8985dba87ba5485c946 |
| 差分 | 38コミット先行・遅れ0。53ファイル、7,949行追加・33行削除 |
| Linuxの検証 | #33 の最終headで build（警告0・エラー0）、RLoop.Tests 639件とRLoop.IntegrationTests 24件、失敗0 |
| Windowsの検証 | https://github.com/usaturn/resoloop/actions/runs/44378694937/job/135064676520 。build/test/pack/installed-tool smoke test成功 |
| Windows検証merge commit | ea338405917e893dfe5b00ed78c7e65eb9ec8a6b。treeは提出候補と一致 |
| .NET | global.json: 10.0.201、rollForward latestPatch |

前段完了記録: https://github.com/usaturn/resoloop/issues/33#issuecomment-6989057906

#101 と #33 は completed。旧 feat/plugin-v2 は保持されており、提出元に使わない。#33 の検証用PR #34 は未マージcloseが予定された成果であり、そのマージを待たない。#471 は前段の文書専用PRで、#105 の文書の代わりにせず、マージ待ちを追加の先行条件にしない。#470 は別件で、未完了でも本提出を止めない。

## 提出方法の比較と採用

### 採用: 検証済み候補を1本のPRにする

4機能は共通のmanifest・registry・照合・CLI統合を使う。helloの最小例と FourFeaturesWorkThroughTheRealCli は4機能の連携を実際のCLIを通して検証する。候補を変更せず使えば、既存のLinux・Windows検証のtreeとの対応を維持できる。差分の読取順と既存38コミットをPR本文で示す。

### 比較した案: 機能ごとに複数PRへ分割

個別の差分を小さくできるが、共通基盤とCLI・文書・例の依存が増え、途中の各組合せに追加の検証が必要になる。現時点では検証済みの統合候補を崩す利点が小さいため採用しない。上流作者が分割を求めたときは、その具体的な要望に応じて検討する。

以上はエージェントの実装上の判断であり、利用者が個別の分割案を承認したという記録にはしない。

## 範囲と制約

- 既存の汎用4機能と承認済み D-1〜D-6 を維持する。本体コードは変更しない。
- fork main、旧 feat/plugin-v2、公開済み提出元の履歴は変更しない。force pushをしない。
- Meshy、fork mainだけの変更、版番号変更、NuGet公開を含めない。
- 上流への事前相談Issue・Discussion・コメントを作らず、準備できたPRを直接投稿する。
- PRはdraftではなくレビュー可能な状態で作成する。重複PRが存在すれば新規作成を繰り返さず、現状を確認する。
- Issue #105 はPRを作成しただけでは閉じず、#102 を開始しない。上流マージとNuGet公開は別である。
- ハッシュ照合を署名・配布者の真正性・サンドボックスと説明しない。コマンドとdoctorプローブが利用者権限で実行されることを示す。
- Resonite・Blender・実サービスの認証情報を使う検証は実行しない。実機未検証を明示する。
- READMEの上流絶対リンクは候補treeの存在で確認し、上流のマージ後に公開URLを確認する。

## 検証方針と受け入れ基準

動作環境は既存検証のLinux Dev ContainerとWindows CI、.NET SDK 10.0.201。今回のPR準備では、本体コードや提出treeを変更しないため、記録済みのテストを新規実行したように報告しない。

実入力は現在のfork head・上流main・両者のcompare、既存上流PR、CI job、Git commitのtree、#101/#33のcompleted、英日ガイドと最小例である。投稿直前にhead/baseと重複を再確認する。

防御範囲は、誤ったrepo/base/headへの投稿、重複PR作成、異なるtreeへの検証結果の流用、未マージのIssue完了を防ぐこと。既存候補への追加の静的レビューでは、導入からコマンド/doctor利用、スキル同期、UIXレシピ利用までを分担して読取確認した。確認範囲に提出を止める重大な問題は見つからなかった。コードの新規テストは追加せず、公開APIの読戻しと差分・tree・検証証拠の照合で確認する。

上流PR作成後はURL、repo、base/head、draft=false、open、bodyの一致、差分のファイル数とheadを確認する。Actionsが動く場合は実行状況を記録する。今回の実行での作成成功と、上流作者による後日のマージを区別する。

## 既知の制限

usaturn/resoloop#32 の4件をPR本文に引き継ぐ。既存編集済みプロジェクトのinit、組み込みrecipe describe/exportのproject検証、dataのsymlink削除、空versionArgs/照合失敗時のdoctorの挙動である。これらを今回の提出準備で再設計しない。

## PRタイトル

Add project-scoped plugins for commands, skills, UIX recipes and doctor

## PR本文（英語・日本語）

## Summary

Add project-scoped plugin packages so integrations and reusable resources can be developed outside ResoLoop while using the existing CLI and project model.

A package declares its identity, compatible ResoLoop versions and optional capabilities in `resoloop-plugin.json`:

| Capability | Behavior |
| --- | --- |
| External commands | Invoke a program directly, without a shell; forward trailing arguments, stdout/stderr and normal exit codes. Stdin is forwarded only when redirected. Built-in commands retain precedence. |
| Skills | Distribute plugin skills through `init` and `skills sync`, with a separate ownership record and preservation of user edits. |
| UIX recipes | Discover and expand namespaced `plugin:recipe` resources through `uix recipe` and declaration files. Unqualified names continue to select built-in recipes. |
| Doctor checks | Check declared external tools when `doctor` is invoked, distinguishing required failures from optional warnings. |

The management commands are `plugin install`, `plugin list` and `plugin remove NAME --yes`. Sources can be local package directories or Git URLs with an explicit `--ref`; Git installs record the resolved commit. Installation copies and validates the package without executing plugin code or installing its dependencies.

## Design and review guide

- Packages and mutable data are scoped to the project under `.resoloop/plugins/<name>/`.
- The manifest, registry and verification path are shared by all four capabilities. Installation is staged before publishing the package, and a per-project lock serializes ResoLoop's plugin operations.
- Package verification compares the recorded file set and SHA-256 contents before use. Mutable `data/` is separate.
- Commands use the project root as their working directory and receive explicit plugin paths through `RESOLOOP_PLUGIN_*`. They do not automatically connect to ResoniteLink.
- Recipes expand JSON resources; this does not introduce hooks into the core plan/apply/test pipeline.
- This includes English/Japanese guides and a `hello` example covering all four capabilities without a live Resonite connection. There is no Meshy-specific integration, version bump or release change.

This is submitted as one integrated feature because the capabilities share the same installation and verification model, CLI integration and end-to-end example. Splitting them would require intermediate combinations to be rebuilt and validated. The existing commit sequence can be used to review the feature in smaller units.

Suggested reading order:

1. `src/RLoop.Core/Plugins/`: manifest, installation, registry, paths, locking and verification.
2. `src/RLoop.Cli/PluginManagementCommands.cs`, `PluginCommandDispatch.cs`, `PluginDoctorChecks.cs` and the integration in `Program.cs`.
3. `PluginSkillManager.cs`, `PluginRecipeResolver.cs`, `BundledSkillManager.cs`, `UixRecipes.cs` and `ApplyDocumentCompiler.cs`.
4. `tests/RLoop.Tests/PluginCliIntegrationTests.cs` (`FourFeaturesWorkThroughTheRealCli`) and the focused plugin tests.
5. [English guide](https://github.com/usaturn/resoloop/blob/c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b/docs/PLUGINS.md), [Japanese guide](https://github.com/usaturn/resoloop/blob/c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b/docs/PLUGINS.ja.md) and [hello example](https://github.com/usaturn/resoloop/tree/c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b/examples/plugins/hello).

## Validation

Submission head: `c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b`  
Base checked: `32309ca3deb4560e6a31a8985dba87ba5485c946`  
Submission tree: `9d1fa089f93de4e0c74afb63da64a83ca439b6a6`

The branch contains the checked upstream base, with no commits behind it. The difference is 53 files (44 added, 9 modified), 7,949 additions and 33 deletions.

- **Linux / .NET SDK 10.0.201:** the final candidate's recorded `dotnet build ResoLoop.slnx` completed with zero warnings/errors; `dotnet test ResoLoop.slnx --no-build` reported 639 RLoop.Tests and 24 RLoop.IntegrationTests, with zero failures.
- **Windows:** [CI run](https://github.com/usaturn/resoloop/actions/runs/44378694937/job/135064676520) passed restore, build, tests, pack and installed-tool smoke testing. Its validation merge commit `ea338405917e893dfe5b00ed78c7e65eb9ec8a6b` has the same tree as the submitted head.
- The refs, validation result and tree identity were rechecked before submission. These are the existing runs for this exact candidate, not newly executed tests during PR preparation.
- **Live Resonite/Blender testing was not performed.** `RESOLOOP_RUN_INTEGRATION` was not enabled; the integration-project count above does not establish live-world coverage.
- README links intentionally point at the upstream `main` paths. The target files exist in this candidate; those links become available upstream after merge.

## Trust model and known limitations

Only install packages whose source you trust. File hashes detect differences from the installation record; they are not signatures, publisher verification or a sandbox. Commands and doctor probes run with the user's permissions and inherited environment. A doctor probe may execute before any plugin command has been run. This does not promise isolation from malicious same-user processes or universal containment of descendant processes.

The guides currently have these qualifications:

1. For an existing edited project, skip the quick start's `init` step. Reinitialization can stop with `INIT_FILE_EXISTS` without changing existing files.
2. Built-in `uix recipe describe` and `export` do not validate `--project`. Use `uix recipe list --project DIR` or `plugin list --project DIR` to check project selection.
3. If `data` is a symbolic link, `plugin remove NAME --yes` removes the link itself without modifying its target; other plugin-use paths reject the unsafe layout.
4. A doctor tool with empty `versionArgs` is located but not executed. Tools from plugins that fail verification are not executed. Doctor reports readiness in its output/JSON; a failing plugin check does not imply a nonzero process exit code.

---

## 日本語

### 目的と変更内容

外部コマンド・スキル・UIXレシピ・doctorのツール確認を、プロジェクト単位のプラグインとして追加できるようにします。任意の連携機能や再利用するリソースを、ResoLoop本体とは別のパッケージで開発できます。

`resoloop-plugin.json` に名前・バージョン・対応するResoLoopのバージョン範囲と、必要な機能を宣言します。`plugin install/list/remove` で管理し、ローカルディレクトリと `--ref` を明示したGit URLを導入元にできます。Gitから導入した場合は解決済みのcommitを記録します。導入時にプラグインのコードや依存関係のインストールは実行しません。

- **外部コマンド:** シェルを介さずプログラムを起動し、後続の引数・標準出力・標準エラー・通常の終了コードを引き継ぎます。標準入力はリダイレクト時のみ引き継ぎます。組み込みコマンドを優先し、ResoniteLinkへの自動接続は行いません。
- **スキル:** `init` と `skills sync` から配布します。プラグイン用の所有記録を分け、利用者の編集を保護します。
- **UIXレシピ:** `plugin:recipe` という名前で一覧・取得・宣言ファイルからの展開に対応します。名前空間のない名前は既存の組み込みレシピを指します。
- **doctor:** 明示的に `doctor` を実行した際に宣言済みツールを確認し、必須項目の失敗と任意項目の警告を区別します。

4機能が同じmanifest・導入管理・照合処理を共有し、最小例とCLI統合テストも4機能を通して確認しているため、1本のPRにまとめています。英語・日本語のガイドと、Resoniteへの接続が不要な `hello` 例を含みます。Meshy固有の処理、coreのplan/apply/testへのフック、版番号・リリースの変更は含みません。

### 検証

上記のheadとtreeに対する既存の検証結果を、投稿前に再確認しました。

- Linux（.NET SDK 10.0.201）: buildは警告・エラーとも0、testはRLoop.Tests 639件とRLoop.IntegrationTests 24件で失敗0。
- Windows CI: build・test・pack・インストール後のスモークテストまで成功。CIの検証用merge commitのtreeが提出候補と一致しています。
- 今回のPR準備でテストを再実行したという意味ではありません。Resonite・Blenderの実機検証は未実施で、`RESOLOOP_RUN_INTEGRATION` は有効にしていません。
- READMEの上流向け絶対リンクは、提出候補にリンク先が存在することを確認しています。上流の公開URLはマージ後に有効になります。

### 信頼と制限

導入記録とのファイル集合・SHA-256の照合は、署名やサンドボックスではありません。コマンドとdoctorの検査プログラムは利用者の権限・環境変数で動きます。プラグインコマンドをまだ実行していなくても、doctorが検査プログラムを起動する場合があります。信頼できる配布元のコードを確認してから利用してください。

ガイドには次の補足が必要です。

1. 編集済みの既存プロジェクトでは、クイックスタートの `init` を省略します。`INIT_FILE_EXISTS` で停止する場合がありますが、既存ファイルは変更しません。
2. 組み込みレシピの `describe/export` は `--project` を確認しません。プロジェクトの確認には `uix recipe list --project DIR` または `plugin list --project DIR` を使います。
3. `data` がシンボリックリンクの場合、`plugin remove NAME --yes` はリンク自体を削除し、リンク先は変更しません。他の利用経路はこの配置を拒否します。
4. doctorは `versionArgs` が空なら実行せず場所を確認し、プラグインの照合に失敗した場合もツールを起動しません。成否は出力・JSONのreadyで判断し、プラグインの検査失敗を非0の終了コードで判定しないでください。


## 実行記録

- #101/#33の完了、提出head/base、compare、Windows CIと検証treeを再確認した。
- 4機能の利用経路を2担当で読取レビューし、提出を止める重大な問題がないことを確認した。ビルド・テストの再実行はしていない。
- 本文の旧「投稿直前に再度許可を求める」条件は、上記の利用者指示で置き換え、Issue #105に記録した。
- この文書をcreate-reso-worldの文書専用ブランチ・PRに公開し、内容を読み戻してから上流PRを作成する。
- 上流PR URLと作成後の状態は、作成後にこの文書とIssue #105へ追記する。
