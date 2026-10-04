# PR #5 round 6: recreate の checkpoint index 修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** list-shrink recreate の途中停止後に保存される Component index を、その checkpoint が表す Slot 配置（current / final）とそろえ、reload・再開後に正しい Component へ再束縛して収束させる。

**Architecture:** `WorldService.ApplyAsync` の Component ループは、Slot の最初の `supersededId` を保存するまで既存 Component を current index で保存している。修正 A はこれを新規作成 Component にも広げ、空 ID key の照合（`BuildComponentPlans`）も同じフェーズ判定（永続 state に `supersededId` があるか）で current / final の候補配列を選ぶ。修正 B は、apply 開始時点で `supersededId` を保存済みの Slot を「最初の superseded 保存待ち」に再登録しない。永続 state schema・公開 API・エラーコードは増やさない。

**Tech Stack:** C# / .NET（`dotnet test`）、xUnit、`FakeResoniteClient`（`tests/RLoop.Tests/ApplyWorkflowTests.cs`）

**Spec:** `/workspaces/reso-world/docs/superpowers/specs/2026-09-30-list-shrink-recreate-round6-review-fixes-design.md`（§5 A/B、§6、§7）

**作業場所:** `/workspaces/reso-world/external/resoloop/.worktrees/fix-list-shrink-recreate`（branch `fix/list-shrink-recreate`、PR usaturn/resoloop#5 の head。開始時 HEAD `485e508e8c651fc701f0a36c4889feeeb86a8228`）。以下のパスはこの worktree 基準。

## Global Constraints

- 変更してよいファイルは `src/RLoop.Core/WorldService.cs` と `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` のみ。
- 永続 state schema（`ApplyStateComponent`）、公開 CLI/API、新しいエラーコードを追加しない。runtime 内の補助値（`NodeRuntime` / `ComponentRuntime` のプロパティ）は可。
- 「現在の配置の index」と「作り直し完了後の index」を混同しない。plan の最終 index を全 checkpoint へ無条件に流用しない。
- 現在の配置の index は Slot 全体の index（型別 ordinal ではない）。Slot の snapshot と、同じ Slot でこの apply が先に作成した Component を数える。
- 最初の `supersededId` を保存する同じ checkpoint（同じ保存操作）で、既存 Component とこの apply で作成済みの key を final index へ更新する。
- 保存側と照合側のフェーズ判定は同じ条件（apply 開始時の永続 state で、その Slot の key に `supersededId` があるか）から導く。
- 維持するもの: 保存済み ID による同一 session 照合の優先、held による他 key 保護、保存 ID のない長い list 候補を削除しない（`UnsavedMatchWithALongerList`）、ownership conflict 時の変更前停止、reload 後の `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` 停止と候補・復旧ヒント。
- 候補照合が先に `STABLE_COMPONENT_AMBIGUOUS` で止まる構成（例: create 前停止 + 同型 sibling 2 件の同一 session 再開）を自動採用へ変えない。
- 位置・member 等の証拠による採用方針（D-H1/D-M1/C-U3）、relocate の削除元追跡・移動元 index（S-L3/S-I3/S-U3/C-U2/Q-I2）、非同期 refill、adapter、文書・警告・エラーコード一覧は変更しない。既存の不整合 checkpoint の自動 migration はしない。
- テストは隔離した TMPDIR で同期実行する（下記「テストの実行」）。実機 Resonite・ソリューション全体・fork 全テスト・無関係な world テストは実行条件にしない。
- コードのコメントは英語で、周囲と同じ密度・語調にする。commit メッセージは既存履歴と同じ英語の命令形 subject + 挙動を説明する本文にし、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。

## テストの実行

各 Step の `dotnet test` は次の隔離の下で実行する（fake が `Path.GetTempPath()` 配下に state を書くため）。

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/fix-list-shrink-recreate
VERIFY_ROOT="$(mktemp -d)"; mkdir -p "$VERIFY_ROOT/tmp"
TMPDIR="$VERIFY_ROOT/tmp" dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter '<filter>'
# タスクの最後に
rm -rf -- "$VERIFY_ROOT"
```

## Review Focus

- 新 key を recreate より**後**に宣言し、その作成応答を失った同一 session 再開（Slot は final フェーズ）で、作った Component に束縛する — 既存 `ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated(false)` が Task 1 後も成功すること。
- recreate より前に作った新 key は、recreate が最初の `supersededId` を保存した checkpoint で final index に切り替わる — Task 1 の `NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex`。
- 同型 sibling を宣言順と逆の位置に持つ Slot で superseded 保存前に停止した場合の収束 — 既存 `ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` 3 ケースが両 Task 後も成功すること。
- reload 後のヒント復旧（sibling 1/2 件、savedId 有無）— 既存 `InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` 5 ケースが両 Task 後も成功すること。
- 収束後の次の apply が書き込み 0 件 — 新規テストすべての末尾で `client.Writes == 0` を確認する。

---

### Task 1: 修正 A — recreate 前に作る新 key を current index で保存し、空 ID 照合も同じ基準にする

対応 ID: G-H1 / O-L10 / S-U5（Spec §5 A）。

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（Component ループ 447–495 行付近、`BuildComponentPlans` 1073–1131 行付近、`HeldByOtherKeys` のコメント 1231–1235 行、`NodeRuntime` 2307–2322 行、`ComponentRuntime` 2324–2346 行）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`（`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の直後、726 行の後に追加）

**Interfaces:**
- Consumes: なし
- Produces:
  - `NodeRuntime.SavedFinalIndexes`（`bool`、get/set）— `BuildComponentPlans` がノードごとに、apply 開始時の永続 state でその Slot（`state.SlotKey == node.StableKey`）の key に空でない `SupersededId` があれば `true` にする。Task 2 が `recreatingNodes` の初期化で使う。
  - `ComponentRuntime.CurrentIndex`（`int`、get のみ）— コンストラクタ引数 `componentIndex`（`AssignComponentIndexes` で上書きされる前の、現在の配置での index）を保持する。
  - テストヘルパー `LabeledRenderer(FakeResoniteClient client, string label)` — Rubble 上で指定 Label を持つ唯一の `Test.Renderer` を返す。Task 2 のテストも使う。

- [ ] **Step 1: 失敗するテストを書く**

`ApplyWorkflowTests.ListShrink.cs` の `ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` の直後に追加する。

```csharp
    private static FakeResoniteClient.FakeComponent LabeledRenderer(FakeResoniteClient client, string label) =>
        Assert.Single(Rubble(client).Components, component => component.Type == "Test.Renderer" &&
            component.Members["Label"].Value!.GetValue<string>() == label);

    // A new key created before the Slot's recreate saves supersededId sits after the Component the recreate replaces.
    // Until that checkpoint it is saved at its index in the layout the Slot has, so after a world reload it binds what it
    // created and the recreate converges instead of stopping on an ownership conflict or an ambiguity.
    [Theory]
    [InlineData("write-failure")]
    [InlineData("cancel")]
    [InlineData("lost-add-response")]
    public async Task NewKeyCreatedBeforeARecreateConvergesAfterWorldReload(string failure)
    {
        const string extra = """{"key":"extra","type":"Test.Renderer","fields":{"Materials":["$ref:m4"],"Label":"east"}},""";
        const string marker = """{"key":"marker","type":"Test.Material","fields":{"Tint":9}},""";
        var name = "shrink-reload-new-key-" + failure;
        var (client, service, state, _) = await ApplyFourMaterialsAsync(name);
        var three = ShrinkDocument(name, 3, leadingComponents: extra + (failure == "write-failure" ? marker : ""));
        using var cancellation = new CancellationTokenSource();
        if (failure == "write-failure") client.FailOnWrite = 2;
        else if (failure == "cancel") { client.Cancellation = cancellation; client.CancelAfterWrites = 1; }
        else client.LoseNextComponentCreateResponse = true;

        Assert.NotNull(await Record.ExceptionAsync(() => service.ApplyAsync(three, new ApplyOptions(state), cancellation.Token)));
        client.FailOnWrite = null;
        client.CancelAfterWrites = null;
        client.Cancellation = null;
        Assert.Null(StateComponent(state, "renderer")["supersededId"]);
        var createdId = LabeledRenderer(client, "east").Id;
        Assert.Equal(Rubble(client).Components.FindIndex(component => component.Id == createdId),
            StateComponent(state, "extra")["componentIndex"]!.GetValue<int>());
        client.ReloadWorld("session-reloaded");
        var extraId = LabeledRenderer(client, "east").Id;
        client.ResetWriteCounts();

        await service.ApplyAsync(three, new ApplyOptions(state));

        var renderer = Renderer(client);
        Assert.Equal(MaterialIds(client, 3), MaterialTargets(renderer));
        Assert.Equal([extraId, renderer.Id], RendererIds(Rubble(client)));
        Assert.Equal(extraId, StateComponent(state, "extra")["id"]!.GetValue<string>());
        Assert.Equal(renderer.Id, StateComponent(state, "renderer")["id"]!.GetValue<string>());
        Assert.Null(StateComponent(state, "renderer")["supersededId"]);
        client.ResetWriteCounts();
        await service.ApplyAsync(three, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

    // Resuming a new key's lost create in the same session matches it in the layout its saved index describes. With a
    // same-type sibling the index, not a single remaining candidate, has to point at the Component it created.
    [Fact]
    public async Task ResumedCreateOfANewKeyBeforeARecreateNextToASameTypeSiblingBindsWhatItCreated()
    {
        const string extra = """{"key":"extra","type":"Test.Renderer","fields":{"Materials":["$ref:m4"],"Label":"east"}},""";
        const string sibling = """,{"key":"sibling","type":"Test.Renderer","fields":{"Materials":["$ref:m1","$ref:m2","$ref:m3","$ref:m4"],"Label":"south"}}""";
        const string name = "shrink-resume-new-key-sibling";
        var (client, service, state, oldId) = await ApplyFourMaterialsAsync(name, extraComponents: sibling);
        var siblingId = StateComponent(state, "sibling")["id"]!.GetValue<string>();
        var three = ShrinkDocument(name, 3, extraComponents: sibling, leadingComponents: extra);
        client.LoseNextComponentCreateResponse = true;

        Assert.NotNull(await Record.ExceptionAsync(() => service.ApplyAsync(three, new ApplyOptions(state))));
        var createdId = LabeledRenderer(client, "east").Id;
        Assert.Equal(Rubble(client).Components.FindIndex(component => component.Id == createdId),
            StateComponent(state, "extra")["componentIndex"]!.GetValue<int>());

        await service.ApplyAsync(three, new ApplyOptions(state));

        var renderer = Renderer(client);
        Assert.NotEqual(oldId, renderer.Id);
        Assert.Equal(MaterialIds(client, 3), MaterialTargets(renderer));
        Assert.Equal([siblingId, createdId, renderer.Id], RendererIds(Rubble(client)));
        Assert.Equal(createdId, StateComponent(state, "extra")["id"]!.GetValue<string>());
        Assert.Equal(siblingId, StateComponent(state, "sibling")["id"]!.GetValue<string>());
        Assert.Equal(renderer.Id, StateComponent(state, "renderer")["id"]!.GetValue<string>());
        Assert.Null(StateComponent(state, "renderer")["supersededId"]);
        client.ResetWriteCounts();
        await service.ApplyAsync(three, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

    // Once the recreate saves the Slot's first supersededId, a new key created before it is saved at its final index in
    // the same checkpoint, so following the reload hint leaves the layout that index describes.
    [Fact]
    public async Task NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex()
    {
        const string extra = """{"key":"extra","type":"Test.Renderer","fields":{"Materials":["$ref:m4"],"Label":"east"}},""";
        const string name = "shrink-new-key-final-index";
        var (client, service, state, oldId) = await ApplyFourMaterialsAsync(name);
        var three = ShrinkDocument(name, 3, leadingComponents: extra);
        client.FailOnWrite = 2;

        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        client.FailOnWrite = null;
        Assert.Equal(oldId, StateComponent(state, "renderer")["supersededId"]!.GetValue<string>());
        Assert.Equal(0, StateComponent(state, "extra")["componentIndex"]!.GetValue<int>());
        client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();
        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        Assert.Equal("APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION", error.Code);
        Assert.Equal(0, client.Writes);

        // The replacement's ID was not saved: remove every candidate with this key's fields, then the key.
        await client.RemoveComponentAsync(Renderer(client).Id);
        var saved = JsonNode.Parse(File.ReadAllText(state))!;
        saved["components"]!.AsObject().Remove("renderer");
        File.WriteAllText(state, saved.ToJsonString());
        var extraId = LabeledRenderer(client, "east").Id;
        await service.ApplyAsync(three, new ApplyOptions(state));

        var renderer = Renderer(client);
        Assert.Equal(MaterialIds(client, 3), MaterialTargets(renderer));
        Assert.Equal([extraId, renderer.Id], RendererIds(Rubble(client)));
        Assert.Equal(extraId, StateComponent(state, "extra")["id"]!.GetValue<string>());
        client.ResetWriteCounts();
        await service.ApplyAsync(three, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }
```

- [ ] **Step 2: テストを実行し、red を確認する**

Run（「テストの実行」の隔離下）: `--filter 'FullyQualifiedName~NewKeyCreatedBeforeARecreateConvergesAfterWorldReload|FullyQualifiedName~ResumedCreateOfANewKeyBeforeARecreateNextToASameTypeSiblingBindsWhatItCreated|FullyQualifiedName~NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex'`

Expected:
- `NewKeyCreatedBeforeARecreateConvergesAfterWorldReload` の 3 ケースが FAIL（extra の `componentIndex` が 0、実位置は 1）。
- `ResumedCreateOfANewKeyBeforeARecreateNextToASameTypeSiblingBindsWhatItCreated` が FAIL（保存 index 1、実位置 2）。
- `NewKeyCreatedBeforeAnInterruptedRecreateIsSavedAtItsFinalIndex` は現行 HEAD でも PASS する（final 切り替えの回帰ガード）。

red の失敗理由が上記と違う場合は実装に進まず、理由を報告に書く。

- [ ] **Step 3: runtime の補助値を追加する**

`NodeRuntime` に追加:

```csharp
        // A checkpoint saved a recreate's supersededId on this Slot before this apply, so its keys are saved at their
        // indexes in the layout the recreates leave.
        public bool SavedFinalIndexes { get; set; }
```

`ComponentRuntime` に追加（`ComponentIndex` の直後）:

```csharp
        // The index in the layout the Slot has until its recreates save supersededId, counting the Components this apply
        // creates on it before this one. ComponentIndex holds the index in the layout the recreates leave.
        public int CurrentIndex { get; } = componentIndex;
```

- [ ] **Step 4: 照合側を永続フェーズにそろえる**

`BuildComponentPlans` のノードループ先頭（`var recreatedOnNode = RecreatedOnNode(prepared, node);` の直後）で:

```csharp
            node.SavedFinalIndexes = prepared.State.Components.Values
                .Any(state => state.SlotKey == node.StableKey && state.SupersededId is { Length: > 0 });
```

1101–1104 行の空 ID 照合を、final フェーズの Slot に限って recreate が除く Component を外すように変える:

```csharp
                // A key without a saved ID was saved at its index in the layout the Slot had until a recreate saved supersededId
                // on it, and in the layout this Slot's recreates leave after that, so match it in the same layout.
                var held = HeldByOtherKeys(prepared, stableKey, stateComponent);
                var candidates = Without(node.Existing?.Components ?? [], superseded);
                if (held is not null && node.SavedFinalIndexes)
                    candidates = candidates.Where(component => !recreatedOnNode.Contains(component.Id)).ToArray();
```

`HeldByOtherKeys` 上のコメント末尾「Only a Component a recreate removes is left out, as the saved index counts the layout without it.」を、final フェーズの Slot でだけ外す意味に直す（例: 「Only a Component a recreate removes is left out, and only once the Slot's saved indexes count the layout without it.」）。

- [ ] **Step 5: 保存側で新規 Component も current index にし、最初の superseded checkpoint で作成済み key も final へ更新する**

Component ループ（447–495 行付近）を次のように変える。`recreatingNodes` の初期化行自体は Task 2 で変えるので、ここでは触らない。

1. 最初の superseded での一括更新（461–464 行）を、既存 Component だけでなく、その Slot に state を持つすべての key（この apply で作成済みの key、前回作成が中断した key を含む）へ広げる。移動元 Slot の state を持つ key（`saved.SlotKey != node.StableKey`）は書き換えない。

```csharp
                if (component.Superseded is not null && recreatingNodes.Remove(component.Node))
                    foreach (var bound in prepared.Components.Where(bound => bound.Node == component.Node))
                        if (prepared.State.Components.TryGetValue(bound.StableKey, out var saved) && saved.SlotKey == component.Node.StableKey)
                            prepared.State.Components[bound.StableKey] = saved with { ComponentIndex = bound.ComponentIndex };
```

2. 作成前 checkpoint（479 行）と作成後 checkpoint（487–490 行）で、`recreatingNodes` に残っている Slot では既存・新規を問わず `CurrentIndex` を保存する。既存の `FindIndex` による再計算（488–490 行）はこれに置き換える（既存 Component の `CurrentIndex` は同じ値）。ループの前に次のローカル関数を置き、両 checkpoint で使う:

```csharp
            // Until the Slot's first supersededId is saved, a Component is saved at its index in the layout the Slot has.
            ApplyStateComponent AtSavedLayout(ComponentRuntime component, ApplyStateComponent state) =>
                recreatingNodes.Contains(component.Node) ? state with { ComponentIndex = component.CurrentIndex } : state;
```

```csharp
                    prepared.State.Components[component.StableKey] = AtSavedLayout(component, CreateComponentState(component, string.Empty));
                    Checkpoint(prepared);
```

```csharp
                if (!string.IsNullOrWhiteSpace(component.Spec.Key) && !component.VerifiesRecreate) byKey[component.Spec.Key!] = component;
                prepared.State.Components[component.StableKey] = AtSavedLayout(component, CreateComponentState(component, component.Id!));
                Checkpoint(prepared);
```

3. 452–456 行のコメントを、新規 Component も current index で保存し、最初の `supersededId` の checkpoint で作成済みの key も含めて final へ更新する内容に直す。

- [ ] **Step 6: 追加テストが通ることを確認する**

Run: Step 2 と同じ filter。
Expected: 5 ケースすべて PASS。

- [ ] **Step 7: 既存の回帰を確認する**

Run: `--filter 'FullyQualifiedName~ApplyWorkflowTests'`
Expected: 全件 PASS（開始時点 153 件 + 追加 5 件）。特に `ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated` 2 ケース、`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` 3 ケース、`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` 5 ケース。

- [ ] **Step 8: Commit**

```bash
git add src/RLoop.Core/WorldService.cs tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit
```

メッセージは既存履歴の書式（英語の命令形 subject、挙動を説明する本文、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）。本文には、recreate が `supersededId` を保存する前に作った同型の新 key が final index で保存され、reload 後に ownership conflict / ambiguity で止まっていたこと、今は現在の配置の index で保存し最初の `supersededId` の checkpoint で final へ切り替えること、空 ID key の照合も同じ配置で行うことを書く。

---

### Task 2: 修正 B — supersededId 保存済みの Slot を current フェーズへ戻さない

対応 ID: S-L4 / O-U2 / D-U1（Spec §5 B）。

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（Component ループ前の `recreatingNodes` 初期化とそのコメント、452–457 行付近）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`（Task 1 で追加したテストの直後）

**Interfaces:**
- Consumes: Task 1 の `NodeRuntime.SavedFinalIndexes`（apply 開始時の永続 state でその Slot に `supersededId` がある）、テストヘルパー `LabeledRenderer(FakeResoniteClient client, string label)`。
- Produces: なし

- [ ] **Step 1: 失敗するテストを書く**

```csharp
    // A resumed recreate on a Slot that already saved supersededId keeps every key there at its final index: an apply that
    // stops again at a sibling's checkpoint must not save the sibling back at its index in the layout the Slot still has.
    // The sibling is declared first but added by a later apply, so it sits after the renderer on the Slot.
    [Theory]
    [InlineData("before-add")]
    [InlineData("before-remove")]
    public async Task ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload(string failure)
    {
        const string sibling = """{"key":"sibling","type":"Test.Renderer","fields":{"Materials":["$ref:m1","$ref:m2","$ref:m3","$ref:m4"],"Label":"south"}},""";
        var name = "shrink-resume-stopped-at-sibling-" + failure;
        var (client, service, state, oldId) = await ApplyFourMaterialsAsync(name);
        await service.ApplyAsync(ShrinkDocument(name, 4, leadingComponents: sibling), new ApplyOptions(state));
        var three = ShrinkDocument(name, 3, leadingComponents: sibling);
        client.ResetWriteCounts();
        client.FailOnWrite = failure == "before-add" ? 1 : 2;
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        client.FailOnWrite = null;
        Assert.Equal(oldId, StateComponent(state, "renderer")["supersededId"]!.GetValue<string>());
        Assert.Equal(0, StateComponent(state, "sibling")["componentIndex"]!.GetValue<int>());

        using var cancellation = new CancellationTokenSource();
        var stopAtSibling = new ApplyOptions(state, Progress: progress =>
        {
            if (progress.Stage == "components" && progress.Path?.EndsWith("/@sibling", StringComparison.Ordinal) == true) cancellation.Cancel();
        });
        Assert.NotNull(await Record.ExceptionAsync(() => service.ApplyAsync(three, stopAtSibling, cancellation.Token)));
        Assert.Equal(0, StateComponent(state, "sibling")["componentIndex"]!.GetValue<int>());
        Assert.Equal(oldId, StateComponent(state, "renderer")["supersededId"]!.GetValue<string>());

        client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();
        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        Assert.Equal("APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION", error.Code);
        Assert.Equal(0, client.Writes);

        var siblingId = LabeledRenderer(client, "south").Id;
        var north = Rubble(client).Components.Where(component => component.Type == "Test.Renderer" &&
            component.Members["Label"].Value!.GetValue<string>() == "north").ToArray();
        var saved = JsonNode.Parse(File.ReadAllText(state))!;
        if (failure == "before-add")
        {
            // The replacement's ID was not saved: remove every candidate with this key's fields, then the key.
            foreach (var component in north) await client.RemoveComponentAsync(component.Id);
            saved["components"]!.AsObject().Remove("renderer");
        }
        else
        {
            // Remove only the replaced Component, whose list is longer than declared, then supersededId.
            await client.RemoveComponentAsync(north.MaxBy(component => MaterialTargets(component).Length)!.Id);
            saved["components"]!["renderer"]!.AsObject().Remove("supersededId");
        }
        File.WriteAllText(state, saved.ToJsonString());
        await service.ApplyAsync(three, new ApplyOptions(state));

        var renderer = Renderer(client);
        Assert.Equal(MaterialIds(client, 3), MaterialTargets(renderer));
        Assert.Equal([siblingId, renderer.Id], RendererIds(Rubble(client)));
        Assert.Equal(siblingId, StateComponent(state, "sibling")["id"]!.GetValue<string>());
        Assert.Equal(4, MaterialTargets(LabeledRenderer(client, "south")).Length);
        Assert.Equal(renderer.Id, StateComponent(state, "renderer")["id"]!.GetValue<string>());
        Assert.Null(StateComponent(state, "renderer")["supersededId"]);
        client.ResetWriteCounts();
        await service.ApplyAsync(three, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }
```

- [ ] **Step 2: テストを実行し、red を確認する**

Run: `--filter 'FullyQualifiedName~ResumedRecreateStoppedAtASiblingKeepsItsFinalIndexAcrossWorldReload'`
Expected: 2 ケースとも FAIL。キャンセル直後の sibling の `componentIndex` が 1（現在の配置の index）に戻っている。

- [ ] **Step 3: 最小の実装**

Component ループ前の `recreatingNodes` の初期化を、apply 開始時に `supersededId` を保存済みの Slot を除くように変える:

```csharp
            var recreatingNodes = prepared.Components.Where(component => component.Superseded is not null && !component.Node.SavedFinalIndexes)
                .Select(component => component.Node).ToHashSet();
```

直前のコメント（452–456 行付近。Task 1 で書き直したもの）に、apply 開始時点で `supersededId` を保存済みの Slot はすでに final index で保存されているので、再開する recreate がその Slot の key を current index へ戻さないことを 1–2 文で足す。

- [ ] **Step 4: 追加テストが通ることを確認する**

Run: Step 2 と同じ filter。
Expected: 2 ケースとも PASS。

- [ ] **Step 5: 既存の回帰と関連プロジェクトの検証**

Run: `--filter 'FullyQualifiedName~ApplyWorkflowTests'`、続けて filter なしで `TMPDIR="$VERIFY_ROOT/tmp" dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
Expected: どちらも全件 PASS、exit 0。特に `ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload` 3 ケースと `InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint` 5 ケース。

- [ ] **Step 6: Commit**

```bash
git add src/RLoop.Core/WorldService.cs tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit
```

本文には、`supersededId` を保存済みの Slot で recreate を再開すると、先に処理した sibling の checkpoint が現在の配置の index へ戻り、再度止まって reload した後のヒント復旧で ownership conflict になっていたこと、今はその Slot を final index のまま保存することを書く。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

---

## 反映（controller が最終レビュー後に行う。サブエージェントのタスクではない）

review-fix-planning の「実装後」に従う。

1. `git fetch origin` し、`origin/fix/list-shrink-recreate` が開始時 HEAD `485e508e8c651fc701f0a36c4889feeeb86a8228` のままであることを確認する。更新されていたら関連部分を照合し、前提の変更を報告する。
2. `git -C /workspaces/reso-world/external/resoloop/.worktrees/fix-list-shrink-recreate push origin HEAD:fix/list-shrink-recreate` で既存 PR #5 へ反映する。新しい PR・`*-review-fixes` branch は作らない。
3. push 成功後、TOPLEVEL（`/workspaces/reso-world`）から `upsert_pr_comment.py --pr 5 --repo usaturn/resoloop --model-name claude-opus-5-5` で日本語の status comment を作成または更新する。他エージェントのコメントは編集しない。
