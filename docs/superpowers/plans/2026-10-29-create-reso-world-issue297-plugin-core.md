# Issue #297 Plugin Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ResoLoop 0.2.0 に、安全なコピー導入・全内容照合・削除と後続向けAPIを実装し、feat/plugin-v2宛てPRを作る。

**Architecture:** 公開manifest v1の意味を維持し、安全処理は責務別に新規実装する。パス規則を共有し、検証済みの記録・予約名スナップショット・OS解放ロックで利用/変更を直列化する。Git URLはcheckoutなしのtree/blob読取で導入する。

**Tech Stack:** C#/.NET 10.0.201系、System.Text.Json、System.IO、SHA-256、Git、xUnit。新規NuGet依存なし。

**Spec:** `../specs/2026-10-29-create-reso-world-issue297-plugin-core-design.md`（内容commit `5353ba718fc19b678f6a32fa4354030e8c27f02c`）。

## 管理・実行許可

- 状態: **draft**。対象 https://github.com/usaturn/create-reso-world/issues/297 。文書はcreate-reso-world、コードはusaturn/resoloop。
- 利用者のSpec/Plan作成・実装・PR依頼と「必要であれば、0から実装し直してください。負担が増えても構いません。また、途中で止めずに推奨案で実装まで進めてください。」により、通常の設計判断と実装を委任。内容承認は別記録。SpecのPlannotatorは応答待ちtimeoutでunavailable、承認済み扱いしない。Planも指定review bridgeへ送る。
- 実行方式: SDD、Task順次実行、タスクごとにsp-implementerと読み取り専用sp-review、最後に全体レビュー。sessionMode=lineage-only。共有worktreeへの書き込み担当は常に1人。モデル指定はroleの設定に従い、勝手なoverrideをしない。
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-297-plugin-core`、branch `feat/create-reso-world-issue-297-plugin-core`、base `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`。
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-297-plugin-core`、branch `docs/issue-297-plugin-core`、base `057c166c282ecb7ce1f00236efdd09c54f35a6fb`。
- SESSION: `/workspaces/reso-world/tmp/agents/issue-297.beqzdh2p`。SDD領域は `SESSION/sdd/2026-10-29-create-reso-world-issue297-plugin-core/`。worktree内へコミットしない成果を置かない。
- 予約はSESSION/claim.json。調整役だけがIssue/予約/push/PRを操作。編集・外部書込前にremote refが保存SHAか確認する。

## Global Constraints

- コード基準は上流0.2.0の `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`。fork/mainの取り込み・変更、旧専用機能の移植、CLI結線は禁止。
- 編集可能なのはSpecの10 Coreファイル、3 testファイル、`tests/fixtures/plugins/core/`のみ。実装とレビューへ同じSpec条件・受け入れ基準を渡す。
- manifest最大256 KiB、package最大10000ファイル/200 MiB、record最大8 MiB。名前は小文字規則2〜40文字、commands/skills/recipes各50、tools20、timeoutSeconds1〜86400。互換例は0.2.0を受け入れる。
- Gitの確認失敗を全コピーへfallbackしない。Git配下非ルートとコピー対象内nested repositoryを拒否。入口aliasは実パスにするが子linkは辿らない。
- source/record/manifestの相対パスは同じportable規則。大小文字/親子衝突を拒否。管理親・package根linkを読み書き削除しない。
- 予約名catalogは引数必須。CoreにCLIの名前一覧を持たせない。名前空間の異なるrecipeローカル名は共存可能。
- List/Loadはsnapshot。後続の実利用はOpenVerifiedのleaseを利用終了まで保持。install/removeと同じロックを取り、再入しない。
- installはstagingで検証して一度だけrename。既存導入物/recordは失敗しても不変。removeはconfirmed必須、指定pluginだけを消し、配布済みskillや外部内容を消さない。
- Gitはshellなし、環境のrepository/config注入除去、通常credential helper維持、checkout/filter/hookなし。各呼出し120秒、期限の終了を成功扱いしない。秘密をstdout/stderr/context/recordへ転載しない。
- テストはSのみ。安全拒否には成功対照が必要。F/Lと同じ守りのDを増やさない。実認証・外部有料API・実機・グローバル導入を実行しない。
- 各担当は検証を同期実行し終了コードとログを報告。実装担当のself-reviewに加えtask-reviewのspec/quality両判定を得る。レビュー子は実行せず、必要な再現はcontrollerが行う。

## 受け入れ基準

以下を各実装briefと対応reviewの両方へ同じ本文で渡す。

- 動作環境: Linux Dev Container、global.jsonの.NET 10.0.201系、xUnit。一時ディレクトリと一時Git repositoryのみで検証する。Windowsも設計対象だがWindows未実行を成功としない。Resonite/Blender/実認証/グローバル導入は不要。
- 実入力: `作業 ワールド` のパス、通常パッケージ、追跡ファイル＋未追跡許可ファイル＋ignoredな偽機密、入口symlink経由のGitルート、Git内サブディレクトリ、file://URL＋ref、差し替えたpackage/親リンク、`../outside`等のrecordキー、case/prefix衝突、破損record、二つのプロセスによる同一project操作、保持したread lease中の削除拒否と解放後の成功、Git外パッケージ内のnested repository。
- 防御範囲: Git環境で別repositoryを選ばない、ignored/資格情報をコピー/保存しない、管理領域と外部リンク先を操作しない、全package差分を検出、衝突や失敗を成功にしない、失敗後に既存導入物を保持、同一projectの操作を排他。各拒否の守りには少なくとも一つ正しく通る例を含める。悪意ある同一ユーザ、署名/サンドボックス、CLI結線、Windows実機確認はこの検証の外。

## Review Focus

1. JSONのdictionary内重複、予約名の呼出後変更、SemVerの大きいprerelease番号が正常そうな誤判定を生まない（Task1のSafetyDefinitionsRemainStable）。
2. dangling link/Windows名の別名化/file-directory prefixがroot内の別ファイル操作へ変わらない（Task1のPortablePathsKeepBoundaries、Task2のUntrustedRecordNeverReadsOutside）。
3. 照合後から利用完了まで通常の他プロセスがremove/installできず、Disposeとプロセス終了後に再開できる（Task2のUsageLeaseOwnsProjectLock）。
4. sourceがGit外に見えてもnested.git/破損.gitによってignoredな秘密を全コピーしない（Task3のGitSourceClassificationFailsClosed）。
5. コピー中にmanifestやpayloadが変わっても古いname/hashを確定しない。確定後の結果構築失敗で成功済みを失敗報告しない（Task4のCommitUsesStagedIdentity）。

## ファイル責務と要件対応

| Task | 所有ファイル | Spec条件 / 観測証拠 |
| --- | --- | --- |
| 1 | SemanticVersion, PluginNames, PluginErrors, PluginManifest, PluginPathPolicy; PluginManifestTests | 型・互換・予約名・path。実入力の境界を保持し、参照先を外へ逃がさない |
| 2 | PluginInstallRecord, PluginRegistry, PluginProjectLock; PluginRegistryTests; core lock probe fixture | 独立に構成したrecordで全内容照合、#112、破損・名前衝突、snapshotとlease、別process排他 |
| 3 | PluginGit; PluginInstallerTests内Git対象テスト; core Git probe fixture | Git分類、#110、環境隔離、secret/ignored除外、exact commit/blob・実行mode、no hook/filter |
| 4 | PluginInstaller; PluginInstallerTests内導入/削除テスト; core fixtures | source→copy→record→verify→rename/rollback→load→remove。#111、既存保護、ignore管理、同時操作、全体統合 |
| 5 (controller) | 文書Spec/Plan・SESSION・handoff・Issue/PR | 条件単位の証拠照合、公開・遠隔復元・予約解放。コードは新規変更せず、必要なら担当Taskへ戻す |

順序は1→2→3→4→5。Task3はTask2のPluginSource型、Task4はすべてのAPIを消費する。共有する入力（path/name/ref）、状態（record/reservations/lock）、操作順（stage→verify→commit/lease→use→dispose）をTask4とcontrollerが全体で確認する。成功件数で未確認条件を代えない。

## Task 1: パス・manifest・予約名を一つの検証規則にする

**Files:** Create `src/RLoop.Core/Plugins/{SemanticVersion,PluginNames,PluginErrors,PluginManifest,PluginPathPolicy}.cs` and `tests/RLoop.Tests/PluginManifestTests.cs`.

**Interfaces:**
- `SemanticVersion.Parse(string)`、`CompareTo(SemanticVersion)`。SemVer2.0比較、build無視、prerelease数値をintに押し込まない。
- `PluginNameReservations(IEnumerable<string> commands, IEnumerable<string> skills, IEnumerable<string> recipes)`、3種の読み取り専用snapshot。
- `PluginNames.IsValid(string?)`、`FindConflicts(PluginManifest, IEnumerable<PluginManifest>, PluginNameReservations)`。
- `PluginErrors.Create(string code,string message,IReadOnlyDictionary<string,object?>? context=null,IReadOnlyList<string>? suggestions=null,Exception? innerException=null)`、Specのコード定義。
- `PluginManifest.Read(string packageDirectory)`、`EnsureCompatible(string resoloopVersion)`。Specの全プロパティを持つpublic immutable record類。Commands/Skills/Recipes/Toolsは読み取り専用。
- internal `PluginPathPolicy`: `ResolveDirectory(string path,string code)`（入口の祖先linkも実パス化）、`ValidateRelativePath(string relative,string code)`、`Combine(string root,string relative,string code)`（検証とlink拒否）、`EnsureNoLinks(string path,string code,bool allowMissing=false)`、`EnumerateFiles(string root,string code,bool rejectNestedGit=false)`（相対path一覧、子link/特殊file拒否、非再帰の明示stackでもよい）、`DeleteTree(string path,string code)`（rootは安全な実directoryのみ、子linkはlinkそのものだけ削除）。追加private helperは担当裁量。

**Tests:** S（誤った互換範囲・名前衝突・path脱出はもっともらしい結果や外部操作を残す）。単なる不正JSONのerror一覧網羅はLで追加しない。

- [ ] Step1: `PortablePathsKeepBoundaries` を書く。実在する日本語/空白packageとskill/recipe/program参照は通り、同じ入力の参照を `../outside`、子link、Windows別名に変えた代表例は参照前に拒否。外のsentinelは不変。`SafetyDefinitionsRemainStable` で巨大prerelease番号の順序、0.2.0受入れと上限拒否、元の予約collection変更後も衝突拒否、dictionary重複の拒否、異なるpluginの同じrecipeローカル名の許可をそれぞれ独立した守りとして確認。
- [ ] Step2: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter FullyQualifiedName~PluginManifestTests`。未実装のREDを確認、必要なstub後に境界が守られないassertion失敗も確認する。ログをSESSIONへ保存。
- [ ] Step3: 指定5ファイルを実装。厳格JSON読みとpath検証を分離。安全判定をmanifest以外でも再利用できるようにする。独立エラーをcollectし、unsafe pathを使ってから検証しない。
- [ ] Step4: 同じテストをGREENにし、`dotnet build src/RLoop.Core/RLoop.Core.csproj --no-restore --nologo`。F/Lはこのbuildと一時probeで検証。git diff --checkと差分自己レビュー。
- [ ] Step5: 明示6パスをstageし `feat: add validated plugin manifests and path policy` でcommit。reportにexact API、RED/GREEN、所要時間、concerns。controllerがtask-review後に次へ。

## Task 2: 導入記録・全体照合・利用lease

**Files:** Create `src/RLoop.Core/Plugins/{PluginInstallRecord,PluginRegistry,PluginProjectLock}.cs`, `tests/RLoop.Tests/PluginRegistryTests.cs`; optional create `tests/fixtures/plugins/core/lock-probe/`.

**Interfaces:**
- SpecのPluginRegistry/PluginStatus/PluginProblem/InstalledPlugin/PluginReadLease public APIをそのまま実装。
- public `PluginSource(string Kind,string Location,string? Ref)` と `PluginInstallRecord(int SchemaVersion,string Name,string Version,PluginSource Source,string? Commit,DateTimeOffset InstalledAt,string ResoloopVersion,IReadOnlyDictionary<string,string> Files)`。static `Read(string path)` と instance `Write(string path)` は厳格JSON/上限/鍵検証後だけ読む/書く。
- internal `PluginProjectLock.Acquire(string pluginsDirectory)` → IDisposable。安全な既存親だけに`.lock`をOpenOrCreate/ReadWrite/FileShare.Noneで開き、競合はBUSY。closeするがunlinkしない。
- Registryのinternal lock-held操作を用意しTask4が利用できるようreportに記載（推奨 `ListUnderLock()` / `LoadAllUnderLock()`）。public操作は必ず自身で取得、OpenVerifiedはleaseへ譲渡。再入を避ける。

**Tests:** S（未検証利用、外部読取、誤ったproject選択、別process削除/競合）。record fixtureは実装のWriteではなく独立にJSON/hashを構成し、同じ不具合で期待値を生成しない。

- [ ] Step1: `UntrustedRecordNeverReadsOutside`：安全なrecord/packageから正常Load、recordキーの脱出/大小文字・親子衝突を代表入力で拒否。`VerifyEntirePackageBeforeUse`：変更・追加・欠落という異なる経路を一つのライフサイクルで順に検証し正常復旧も確認。#112 package根linkでMODIFIED、data変更は許可。`UsageLeaseOwnsProjectLock`：lease保持中に別processの同一project取得がBUSY、別projectは通る、Dispose/子process終了後に同じproject取得が通る。単なる存在やerror文言をassertしない。
- [ ] Step2: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter FullyQualifiedName~PluginRegistryTests` でRED。process probeが必要ならfixture内に小さな.NET consoleソースを置き、bin/objは一時dirへ指定し、専用コマンドだけを実行。実テスト中に本物のagent/Resoniteを呼ばない。
- [ ] Step3: record→path集合→hash→manifest→互換性→予約名の順に検査。Listはpluginごとのproblem、Load/LoadAllは名前衝突を含めfail closed。公開rootの危険とBUSYは例外。FindProjectRootはcwd/explicit/祖先markerを扱い、別projectへfallbackしない。OpenVerified失敗時はlock解放。
- [ ] Step4: 対象テストGREENとTask1回帰（`--filter FullyQualifiedName~Plugin`）。実機Windowsは未実行と明記。自己レビューでdata/外部skill不変、記録上限、正常対照を確認。
- [ ] Step5: 担当パスだけcommit `feat: verify plugin records under project usage leases`。APIとlock-held内部手順をreportへ固定しtask-review。

## Task 3: Gitの入力を安全に分類・展開する

**Files:** Create `src/RLoop.Core/Plugins/PluginGit.cs`, `tests/RLoop.Tests/PluginInstallerTests.cs`（この時点はGitモジュールだけ）; optional `tests/fixtures/plugins/core/git-probe/`.

**Interfaces:** internal `PluginGit.GetLocalFiles(string sourceDirectory)` → `IReadOnlyList<string>`（相対path）。`PluginGit.Export(string url,string gitRef,string checkoutDirectory,string packageDirectory)` → `PluginGitExport(PluginSource Source,string Commit,IReadOnlyList<string> Files)`。Task1 path/Task2 PluginSourceを消費。exportは許可されたstagingの空directoryだけに書く。internal helperは既存InternalsVisibleTo(RLoop.Tests)を利用しpublic APIをテスト都合で増やさない。

**Tests:** S（ignored/credential漏えい、wrong repo、別commit、導入時コード実行）。一時Git repositoryと偽secret、file://のみ。

- [ ] Step1: `GitSourceClassificationFailsClosed`：#110のalias経由repoでtrackedとuntracked-nonignoredは一覧にありignored偽secretはない。非root/壊れた.git/nested.gitは拒否、Git外通常directoryは通る。`GitIgnoresInjectedRepositoryState`：別processのGIT_DIR/WORK_TREE/INDEX/config注入が別repoを選ばず、正常なローカルsourceと同じ結果。親processの環境は変更しない。`ExportPinsBlobsWithoutExecution`：file://＋明示refからrecord commitと元blobの独立SHAが一致し、hook/filterのsentinelが作られない。Unix実行bitを保つ。userinfo等を含むfake URLは拒否され、例外とrecordへfakeの秘密部分を残さない。参照違い/非ゼロ/時間切れは成功としない。
- [ ] Step2: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter FullyQualifiedName~PluginInstallerTests` でRED。process境界はTask2のprobe方式を再利用できるが未許可ファイルの変更が要る場合はcontrollerへ報告。
- [ ] Step3: GIT_* deny/default＋Specのauth allowlist、shellなしArgumentList、drain、120秒上限、停止確認。stderrやURLの生値を例外へ入れない。bare clone後treeをNUL区切りでparseし、mode100644/100755だけを受け入れ、サイズ制限下のblob streamで展開。ローカルGit外判断は単一のexit codeやstderr文言で決めない。
- [ ] Step4: 対象テストGREEN、全Plugin回帰。秘密検査を壊さないよう偽secretは実行時に構成し、固定tokenらしい値をcommitしない。git diff --check、自己レビュー。
- [ ] Step5: 担当パスだけcommit `feat: isolate plugin git sources and export pinned blobs`。task-reviewを受ける。

## Task 4: トランザクション導入・安全な削除と統合

**Files:** Create `src/RLoop.Core/Plugins/PluginInstaller.cs`; extend `tests/RLoop.Tests/PluginInstallerTests.cs`, `tests/fixtures/plugins/core/`。Task1〜3の不具合が判明したらcontrollerの裁定を経てその所有ファイルを最小修正してよい（Issueの許可範囲は広げない）。

**Interfaces:** Specどおり `PluginInstaller(PluginRegistry)` / `Install(string,string?=null)` / `Remove(string,bool)`。Task1〜3のexact APIはreportで確認し、意味を変えずSpec/Planとの表記差をledgerへ記す。動かすprojectには既存.resoloop.jsonが必要。

**Tests:** S（既存導入物喪失、外部削除、誤成功、衝突、同時操作）。共有条件の統合確認をこのTaskが所有する。

- [ ] Step1: `InstallVerifyRemovePreservesUnrelatedData`：日本語/空白projectへlocal source導入→record+package検証→lease→dispose→壊したrecordでもconfirmed remove成功。外のsentinel、配布済みskill、他pluginは不変。confirmed=falseは削除しない。`UnsafeParentsNeverDeleteTargets`：#111管理親linkでRemove/Installを拒否し外部sentinel不変、通常親で成功。重複テストにせず同じguardを所有モジュールで代表確認。
- [ ] Step2: `FailedInstallKeepsExistingInstallation`：既存正常pluginありで新規stageがinvalid/incompatible/conflictingな場合、既存package/record hash不変、自分のstagingだけ消える。異なる既存ignore内容は不変で拒否。正常installでは管理ignoreがpackage/data/record/stagingをGitから除外し既存.resoloop/.gitignoreは不変。`CommitUsesStagedIdentity`：コピー元の読取とstaged検証の順序を検査できる狭いinternal seamが必要ならcontroller裁定で導入し、staged manifestのidentity/hashだけが確定に使われることを確認。`LeaseAndMutationSerialize`：別processの同一project導入/削除がlease中は拒否、解放後成功。Task2のlock primitiveの網羅を再実装しない。
- [ ] Step3: 対象InstallerTestsでRED。constructor/IO exceptionだけの検査にせず、失われてはいけないファイルのbytesと許可側成功をassertする。
- [ ] Step4: source前処理、safe parents、lock、ignore、既存照合、stage、copy、検証、hash/record、再照合、renameの順に実装。既存先は上書きせず、成功後の失敗可能処理を置かない。sourceとprojectの重なりを拒否。Removeは安全な指定根からchild linksを辿らず削除。消す対象は固定した自分のstageか指定pluginだけ。
- [ ] Step5: 全PluginテストGREEN→ `dotnet build ResoLoop.slnx --nologo` → `dotnet test ResoLoop.slnx --no-build --nologo`。基準は530 unit+22 integration-test assemblyのoffline tests（live環境変数なし）。件数だけで正しさを判断しない。自己レビュー・diff --check。
- [ ] Step6: 担当パスをcommit `feat: install and remove plugins transactionally`、reportへSpec→実行証拠表、API例、#110〜#112の対応、Windows未確認を記載。task-review。

## Task 5: 全体レビュー・公開・引き渡し（controller）

**Files:** 本Spec/Plan、SESSIONの検証ログとSDD ledger、`tmp/docs_draft/claude_handoffs/`の新規pair、GitHubの自分の子/PRのみ。

**Tests:** 新規テスト不要（文書F、既存同じ守りのD）。既存テストの対象SHAでの実行、差分/参照の構造検査、遠隔復元のbyte/hash照合で検証する。コード不具合が出たら該当Taskの担当が必要なS回帰を扱う。

- [ ] Step1: SDD final-reviewの手順で全コードbase..HEADをsp-reviewへ渡す。具体的な疑いの最小再現はcontrollerが同期実行。taskレビューを繰り返すだけでなくinput→保存→検証→利用lease→削除のつながりを確認。
- [ ] Step2: 指摘はSpec/範囲/テスト基準で裁定し、採用原文のまま担当へ渡す。指摘対応後は影響経路の検証をやり直す。未解消の安全条件は成功にしない。
- [ ] Step3: 最終HEAD・clean status、build/testのargv/exit/logをSESSIONに保存。Specの全受入れ条件へ証拠を対応させ、Windows/CLI/実機未実行を明記。検証はlive用環境変数が無いことを確認する。
- [ ] Step4: 文書の完了記録/実装API差分を同じSpec/Planへ追記。内容承認/実行許可/実装完了/PR取り込み待ちを分ける。各文書の明示パスだけをcommit。未pushのcommitをPARENT_ROOTのscan-before-push.shで全公開worktreeについて検査。
- [ ] Step5: 最新Issue OPEN/所有予約/同じIssueのPR・branchを再確認。forkのbase branchが存在しなければ既に上流公開済みのa7be2ddをfeat/plugin-v2へ新規push（origin/mainを変えない）。既存remote refがあれば同SHAを確認。コード検査はbase `upstream/main`（a7be2ddと一致確認）または公開後の`origin/feat/plugin-v2`を明示し、検査SHAそのものだけfeature branchへpush。文書も検査SHAだけpush。
- [ ] Step6: fork内code PR（base feat/plugin-v2）とcreate-reso-world文書PR（base main）を作り相互参照。Refs Issue URL、決定理由、実行方法、検証結果/未実行、作業時間、API引き渡しを記載。マージ/タグ/リリース/上流投稿はしない。publicのcode CIの実在checksを待ち失敗なら原因対応。private docs CIは停止中。
- [ ] Step7: agent-handoffのschema v2 pairと復元manifestを作る。Spec/Planはpush済みcommit URL、handoffは子コメントから遠隔だけで新規directoryへ復元しhash/byte/JSON/整合を確認。PR取り込み待ちで子IssueはOPEN。子に結果と次の手順を記録して、自分の予約を保存SHAのleaseで解放し不在確認。親台帳は変更しない。
- [ ] Step8: Herdr完了、code/doc PR、実在Spec/Plan/handoff/logパス、所要時間、未確認と取り込み待ちを報告。不要SESSIONは要点転記後に回収、残す場合は完全パスを報告。

## 実行予算

能動時間300分（利用者は負担増を許容。安全境界を持つ新規10モジュール、4実装Task＋レビューを想定）。準備/Spec/Plan60、Task1 35、Task2 40、Task3 50、Task4 50、全体検証/公開45、予備20。利用者を待ってターンを終える区間はbudget ledgerで除外する。

- 各実装workerは目安35〜60分、予約枠最後5分で成果整理。共有feature worktreeを書いているworkerと検証commandは時間だけでkillしない。同期subagent終了を待ち、停止不能なら保留。role toolにないtimeout/async/actionは指定しない。
- 調査/reviewは目安15分、最後3分で報告。今回の同期role APIには途中停止手段がないため絶対期限でのkillを宣言しない。自発的に完了/不足を報告し、controllerは同期終了後に判断する。
- 同一信頼性失敗は再試行1回まで。安全の失敗は全体停止。レビュー修正上限はSDD fix-loop、最終レビューはfinal-reviewの上限に従う。
- checkpointは準備→実装、各Taskレビュー後、失敗直後、50%/100%。100%は自動延長せず残りを報告する。
- ledgerはSESSION/budget.jsonlとSDD/progress.md。副次的な広範囲調査が増えたら受入れ条件に戻し、未確認条件を落として成功にはしない。

## contingency（代替策）

- 最初のREDで実API/出力の前提だけが違う場合、意味を保つ最小修正をledgerへ記し続行。公開仕様の変更・所有範囲拡大は止めて裁定を得る。
- .NETが非リンクreparseやspecial fileを十分判定できない場合、限定的なOS固有実装をPluginPathPolicy内に閉じる案を検討する。Windows未実行を偽の文字列テストで埋めない。危険な入力を正常扱いして回避しない。
- Git bare blob exportが性能面で詰まるならcat-file --batchへ切替可能。checkout/filterを実行する方式へ戻さない。外部tar依存を足さない。
- probeプロセス構成が重ければ既存InternalsVisibleToと小さなfixture consoleを使い、専用tmp出力に限定。親環境/Git設定の変更で簡略化しない。
- PR base `feat/plugin-v2` が別SHAへ進んだ、他者予約、Issue close、未知の編集があれば停止し他者の状態を変更しない。マージで解消しない。
- Plannotator unavailableは承認ではない。利用者の設計委任を記録し、Planの提示・確認はAGENTS.mdとruntimeの通常text承認経路を維持する。

## 実装前自己点検

Spec→Taskの対応を上表で照合済み。型名/constructor/lock ownership/固定上限/recipe namespaceを揃えた。各S guardの担当と正常対照を特定し、F/L文言テストを排除。共有前提と操作順の統合責任はTask4/controller。コードのテスト成功は現時点では基準branchのみであり、新機能の成功は未確認。
