# リスト縮小時の Component の作り直し（分割案）と Slot の index の保存し直し 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fork の usaturn/resoloop に、A（Component を削除した後に Slot の index を保存し直し、再読込後に文書から外した key の照合結果を保存する）と B（宣言したリストが実機より短い Component を apply が作り直す）を実装し、fork の PR 2 本で判定基準を確かめる。

**Architecture:** 変更は `src/RLoop.Core/WorldService.cs`（apply の計画と段階）と `src/RLoop.Core/ApplyWorkflow.cs`（state の記録）に限る。A は削除の後に Slot を読み直して index を保存する関数 `SaveSlotIndexesAsync` と、削除計画の照合結果の保存を加える。B は plan で縮小を検出して `recreate` にし、apply に「作り直しの検証」と「置き換え元の削除」の 2 段階を加え、途中の作り直しは state の `supersededId` を使って同じセッションの中で ID だけで再開する。

**Tech Stack:** C# / .NET 10（SDK 10.0.201、`global.json`）、xUnit 2.9.3、テスト用の偽クライアント（`tests/RLoop.Tests/ApplyWorkflowTests.cs` の `FakeResoniteClient`）

**Spec:** `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`（create-reso-world）。設計の理由と決定事項（D-1〜D-26）は Spec にある。この計画は Spec の 6〜10 章を実装の手順にしたもの。

## この計画のコードについて

計画に載せたコードは、上流 `b3a84ae` の使い捨てのコピーで試作し、次のとおり確かめた（2026-10-01、fork のリポジトリは未変更）。

- タスクの順に変更を適用し、各タスクで「テストを先に書くと失敗し、実装すると成功する」ことを確かめた。計画のコードブロックは、この確認に使ったスクリプトから生成している。
- 最後まで適用した状態で、上流 CI と同じ restore・build・test を実行し、`RLoop.Tests` 361 件と `RLoop.IntegrationTests` 19 件がすべて成功し、警告は 0 件だった。
- ミューテーション確認: 実装の要点 13 か所（置き換え先を参照先にしない規則、取り消しの範囲、アセットの観測、削除後の index、セッション変更の停止、I3、key の宣言の確認、参照の検査、照合結果の保存 2 種、検証、移動・prune 後の index）をそれぞれ壊すと、対応するテストが失敗した。
- A のテストは上流の `src/` で、B のテストは A の `src/` で、それぞれ失敗することも確かめた。

「置き換え前」のコードは、その時点のファイルの中で 1 か所だけ一致することを確かめてある。行番号は書かない。エディタで「置き換え前」の文字列を検索して置き換えること。

## Global Constraints

- 作業ルートは `/workspaces/reso-world/external/resoloop`（`origin` = usaturn/resoloop、`upstream` = orange3134/resoloop）。そのメインの作業ツリー（`1ef4d18` の detached HEAD、追跡外の `reviews/`）には触らず、`.worktrees/` の下の worktree で作業する（`.worktrees/` は `.git/info/exclude` で追跡対象外）。
- 分岐元: A は `origin/main`（= `upstream/main` = `b3a84ae`）。B は A のブランチ。
- ブランチ: A は `fix/slot-index-after-removal`（base `main`）、B は `fix/list-shrink-recreate-split`（base `fix/slot-index-after-removal`）。
- テストは偽クライアントで行い、Resonite に接続しない。dotnet は `global.json` のあるディレクトリ（worktree の直下）で実行する。
- state の `schemaVersion` は 2 のまま。`supersededId` は null のとき書かない（`JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)`）。
- エラーコード: `APPLY_LIST_SHRINK_REFERENCED`（終了コード 6）、`APPLY_RECREATE_INTERRUPTED`（6、`reason` は `session-changed` / `key-not-declared` / `replacement-unverified`）、`APPLY_LIST_SHRINK_NOT_CONVERGED`（7）。
- plan の操作名は `recreate`。サマリーでは `updates` に数える。
- コミットの件名は英文の命令形。Claude Code が書くコミットの末尾には `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。最終的に A は 2 件、B は 2 件にまとめる。
- fork の Issue・PR の本文は英日併記で、Summary / Root cause / Verification の構成にする。
- 禁止事項:
  - fork の PR をマージしない。fork の main へ push しない。
  - 新しく作る fork の PR は A と B の 2 本だけ、Issue は A 用の 1 件だけ。
  - 既存のブランチ（`fix/list-shrink-recreate`、`fix/asset-url-save-migration`、`fix/slot-snapshot-dedup`）を force push・削除しない。force push してよいのは A・B の 2 本だけ。
  - レビュー修正のために別のブランチや PR を作らない。
  - 判定基準を満たす前に、上流（orange3134/resoloop）へ Issue・PR・コメントを出さない。出すときは文面をユーザに見せて確認を取る。
  - create-reso-world のロック（`.devcontainer/resoloop.lock`）と、global に導入した resoloop を変えない。
- 実機（Resonite）の操作は、ユーザの明示的な指示があるときだけ、上流の `AGENTS.md` の安全規則に従って `ResoLoop_Test*` の Slot の下で行う。
- Python を使うときは `uv run` を使う。日本語の文章は create-reso-world の `AGENTS.md` の「日本語表現」に従う。

## Review Focus

Spec が想定しているが、ほかのタスクのテストでは確かめていない入力のうち、使う人が最も困りそうな 5 つ。それぞれのテストを、担当のタスクに入れてある。

1. identityFields を持つ Component を作り直す → 作り直した後も identity の値が state に残り、ワールドを再読込してから apply しても書き込みは 0 件（Task B3 の `ARecreatedComponentWithIdentityFieldsBindsByIdentityAfterAWorldReload`）。
2. 管理 Component が `$member:` で、作り直す Component のメンバーを参照している → 置き換え先のメンバーに張り替わる（Task B3 の `AMemberReferenceToARecreatedComponentMovesToTheReplacement`）。
3. 途中の作り直しが残った state で `plan`・`diff` を実行する → 再開の内容を理由に示し、ワールドにも state にも書き込まない（Task B5 の `APlanDuringAnInterruptedRecreateExplainsHowItResumes`）。
4. 同じ apply の中で、同じ Slot の prune と作り直しが起きる → index が実機の位置と一致し、再読込後も結び付く（Task B3 の `APruneAndARecreateOnOneSlotKeepTheIndexesBindable`）。
5. 作り直すと `initialFields` が宣言の初期値に戻る（文書どおりの挙動であることを固定する。Task B3 の `ARecreateSetsInitialFieldsAgain`）。

---

## Part 0: 準備

### Task 0: worktree と基準の確認

**Files:** なし

- [ ] **Step 1: リモートの状態を確かめる**

```bash
cd /workspaces/reso-world/external/resoloop
git remote -v
git fetch origin && git fetch upstream
git rev-parse --short origin/main upstream/main
```

Expected: `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop。`origin/main` と `upstream/main` がどちらも `b3a84ae`。違う場合は止まってユーザに報告する（分岐元が変わるため）。

- [ ] **Step 2: A の worktree を作る**

```bash
cd /workspaces/reso-world/external/resoloop
git worktree add .worktrees/slot-index-after-removal -b fix/slot-index-after-removal origin/main
```

- [ ] **Step 3: 基準のテストを実行する**

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore
```

Expected: `RLoop.Tests` 326 件、`RLoop.IntegrationTests` 19 件がすべて成功する。失敗する場合は止まってユーザに報告する。

---

## Part A: Slot の index の保存し直し（`fix/slot-index-after-removal`）

作業ディレクトリ: `/workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal`

### Task A1: 再現テスト（D-15 の判定）と fork の Issue

**Files:**
- Create: `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

**Interfaces:**
- Produces（以降のテストが使う補助）: `IndexedSiblings(string ownership, string[] onRoot, string[]? onChild = null)`、`AssertSavedIndexesMatchLayout(FakeResoniteClient client, string state)`（I1 の確認）、`AllSlots(FakeResoniteClient.FakeSlot slot)`、`InterruptedAsync(Func<Task> apply)`（偽クライアントの `IOException` を中断として扱う）

- [ ] **Step 1: 再現テストを書く**

同じ型で identityFields の無い Component 3 つから 1 つを prune、または別の Slot に移動し、ワールドを再読込してから apply する。各 key に別々の値（`v1` は 1 など）を宣言しているので、ほかの key の Component に結び付くと書き込みとして現れる。

**新規作成:** `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

```csharp
using System.Text.Json.Nodes;
using RLoop.Core;

namespace RLoop.Tests;

public sealed partial class ApplyWorkflowTests
{
    [Theory]
    [InlineData("prune")]
    [InlineData("move")]
    public async Task RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload(string removal)
    {
        var name = "indexes-" + removal;
        var full = ReloadDocument(name, IndexedSiblings(name, ["v1", "v2", "v3"]));
        var changed = ReloadDocument(name + "-changed", removal == "prune"
            ? IndexedSiblings(name, ["v2", "v3"])
            : IndexedSiblings(name, ["v2", "v3"], ["v1"]));
        var client = new FakeResoniteClient(full);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(full, new ApplyOptions(state));
        await service.ApplyAsync(changed, new ApplyOptions(state, Prune: removal == "prune", ConfirmDeletes: removal == "prune"));
        AssertSavedIndexesMatchLayout(client, state);
        client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();

        var applied = await service.ApplyAsync(changed, new ApplyOptions(state));

        Assert.Equal(0, applied.ComponentsAdded);
        Assert.Equal(0, applied.ComponentsUpdated);
        Assert.Equal(0, client.Writes);
    }

    // Same-type siblings without identityFields: after a world reload only their saved indexes tell them apart.
    // Each key "vN" declares Value N, so binding a key to a sibling's Component shows up as a field write.
    private static string IndexedSiblings(string ownership, string[] onRoot, string[]? onChild = null)
    {
        static string Components(IEnumerable<string> keys) => string.Join(",", keys.Select(key =>
            $$$"""{"key":"{{{key}}}","type":"Test.Indexed","fields":{"Value":{{{key[1..]}}}}}"""));
        var child = onChild is null ? "" :
            $$$""","children":[{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[{{{Components(onChild)}}}]}]""";
        return $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{ownership}}}"},"slot":{"key":"root","name":"Owned","parent":"Root"},
             "components":[{{{Components(onRoot)}}}]{{{child}}}}
            """;
    }

    // I1: every saved key whose Component is on its Slot is saved at that Component's position.
    private static void AssertSavedIndexesMatchLayout(FakeResoniteClient client, string state)
    {
        var checkpoint = JsonNode.Parse(File.ReadAllText(state))!;
        var slots = AllSlots(client.Root).ToDictionary(slot => slot.Id, StringComparer.Ordinal);
        foreach (var (key, component) in checkpoint["components"]!.AsObject())
        {
            var slotId = checkpoint["slots"]![component!["slotKey"]!.GetValue<string>()]!["id"]!.GetValue<string>();
            var layout = slots[slotId].Components.Select(candidate => candidate.Id).ToList();
            var index = layout.IndexOf(component["id"]!.GetValue<string>());
            Assert.True(index >= 0, $"Key '{key}' is not bound to a Component on its Slot.");
            Assert.True(index == component["componentIndex"]!.GetValue<int>(),
                $"Key '{key}' is saved at index {component["componentIndex"]} but its Component is at {index}.");
        }
    }

    private static IEnumerable<FakeResoniteClient.FakeSlot> AllSlots(FakeResoniteClient.FakeSlot slot) =>
        new[] { slot }.Concat(slot.Children.SelectMany(AllSlots));

    // The fake client reports an injected failure or a lost response as an IOException.
    private static async Task<bool> InterruptedAsync(Func<Task> apply)
    {
        try
        {
            await apply();
            return false;
        }
        catch (IOException)
        {
            return true;
        }
    }
}
```

- [ ] **Step 2: 失敗することを確かめる（D-15 の判定）**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload"
```

Expected: 2 件とも FAIL。`AssertSavedIndexesMatchLayout` が「`Key 'v2' is saved at index 1 but its Component is at 0.`」のように、削除の後に古い index が残っていることを示す。

成功してしまった場合（上流の main で再現しない場合）は、ここで止まってユーザに報告する（D-15: A をやめ、I1 は B の中だけで扱う）。

- [ ] **Step 3: fork に A の Issue を出す**

Spec の 3.3 の結果（A の再現と、文書から外した key の照合結果が失われる問題）をまとめる。出力された Issue の URL の番号を、Task A4 の PR の本文で使う。

```bash
gh issue create --repo usaturn/resoloop --title "Component indexes go stale after a removal, and undeclared keys lose their binding after a world reload / Component の削除後に index がずれ、再読込後に文書から外した key の照合結果が失われる" --body-file - <<'EOF'
## Summary / 概要

After apply removes a Component (the source of a Component move, or a pruned Component), the Components after it on the same Slot keep their old `componentIndex` in state. After the world is saved and reloaded, apply binds keys without `identityFields` by that index, so the next apply binds a key to a sibling's Component or stops with `STABLE_COMPONENT_AMBIGUOUS`.

Separately, after a world reload the deletion plan binds keys that the document no longer declares, but apply never saves that binding. The first apply in the reloaded session moves the checkpoint to the new session while those keys keep their old IDs, so later plans in the same session look them up by the old IDs and drop them from `--deletes-only` and `--prune`.

apply が Component を削除すると（Component の移動元、または prune した Component）、同じ Slot でその後ろにある Component の `componentIndex` が state に古いまま残ります。ワールドを保存して再読込すると、apply は `identityFields` の無い key をこの index で照合するため、次の apply で兄弟の Component に結び付くか、`STABLE_COMPONENT_AMBIGUOUS` で止まります。

これとは別に、再読込後の削除計画は文書から外した key を照合しますが、apply はその結果を保存しません。再読込後の最初の apply で checkpoint のセッションだけが新しくなり、key の ID は古いまま残るため、同じセッションの後続の plan はその ID で探して見つけられず、`--deletes-only` と `--prune` の対象から外れます。

## Reproduction / 再現手順

1. Declare three Components of the same type without `identityFields` on one Slot (keys `t1`, `t2`, `t3`) and apply.
2. Remove `t1` from the document and run `apply --prune --yes`. State keeps `t2` at index 1 and `t3` at index 2, while they are at 0 and 1.
3. Save and reload the world, then run `apply` again. It stops with `STABLE_COMPONENT_AMBIGUOUS`.

For the second problem: remove a Component and a Slot from the document without `--prune`, reload the world, run `plan --prune` (it lists both), run `apply`, and run `plan --prune` again. The second plan lists nothing.

1. 1 つの Slot に、`identityFields` の無い同じ型の Component を 3 つ（key `t1`・`t2`・`t3`）宣言して apply します。
2. 文書から `t1` を外して `apply --prune --yes` を実行します。state では `t2` が index 1、`t3` が index 2 のまま残りますが、実機の位置は 0 と 1 です。
3. ワールドを保存・再読込してから `apply` を実行すると、`STABLE_COMPONENT_AMBIGUOUS` で止まります。

2 つ目の問題: Component と Slot を `--prune` なしで文書から外し、ワールドを再読込して `plan --prune` を実行すると両方が挙がります。続けて `apply` を実行してから `plan --prune` を実行すると、何も挙がりません。

## Proposed fix / 修正案

- After each Component removal, read the Slot again and save every key whose saved ID is on it at that Component's position.
- Save the ID (and, for a Component, the index) that the deletion plan binds for each undeclared key, in the next checkpoint. Plans never write state.

- Component を削除するたびに Slot を読み直し、保存している ID が Slot 上にある key の index を、その Component の位置に保存し直す。
- 削除計画が文書から外した key に照合した ID（Component は index も）を、次の checkpoint で保存する。plan は state を書かない。
EOF
```

Expected: Issue の URL が表示される（例: `https://github.com/usaturn/resoloop/issues/7`）。

### Task A2: Component を削除した後の index の保存し直し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`ApplyAsync` のフィールドの段階と prune、`BuildComponentPlans`、`BuildDeletionPlans`、`ComponentRuntime`、`DeletionRuntime`、新しい `SaveSlotIndexesAsync`）
- Modify: `docs/DECLARATIVE.md`
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

**Interfaces:**
- Consumes: Task A1 の補助
- Produces: `private async Task SaveSlotIndexesAsync(PreparedApply prepared, string slotKey, string slotId, CancellationToken cancellationToken)`（Slot を読み直し、保存している ID が Slot 上にある key の `ComponentIndex` を保存し直す。メモリ上の state だけを変え、保存は呼び出し側の次の checkpoint が行う）。`ComponentRuntime.RelocationSourceSlotKey` / `RelocationSourceSlotId`。`DeletionRuntime` の `SlotKey` / `SlotId`。

- [ ] **Step 1: 文書から外した兄弟の index のテストを足す**

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` の次の部分の直前に追加する。

```csharp
    // Same-type siblings without identityFields: after a world reload only their saved indexes tell them apart.
```

追加する内容:

```csharp
    [Fact]
    public async Task AnUndeclaredSiblingKeepsItsIndexWhenAnotherComponentLeavesTheSlot()
    {
        const string name = "indexes-undeclared";
        var full = ReloadDocument(name, IndexedSiblings(name, ["v1", "v2", "v3"]));
        // v1 moves to another Slot and v3 is no longer declared, but apply keeps it without --prune.
        var moved = ReloadDocument(name + "-moved", IndexedSiblings(name, ["v2"], ["v1"]));
        var client = new FakeResoniteClient(full);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(full, new ApplyOptions(state));
        await service.ApplyAsync(moved, new ApplyOptions(state));
        AssertSavedIndexesMatchLayout(client, state);
        client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();

        var plan = await service.PlanApplyAsync(moved, new ApplyOptions(state, Prune: true));

        Assert.Equal("v3", Assert.Single(plan.Operations, operation => operation.Action == "delete").Key);
        await service.ApplyAsync(moved, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload|FullyQualifiedName~AnUndeclaredSiblingKeepsItsIndex"
```

Expected: 3 件とも FAIL（保存した index が実機の位置と一致しない）。

- [ ] **Step 3: `SaveSlotIndexesAsync` と呼び出しを実装し、文書を更新する**

Component の移動元を削除した後と、prune で Component を削除した後に、その Slot の index を保存し直す。移動元の Slot は plan の時点で `FindStateSlot` が得たもの、prune の Slot は削除計画が照合したものを使う。

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    await client.RemoveComponentAsync(component.RelocationSource.Id, cancellationToken);
                    counts.ComponentsDeleted++;
                    component.RelocationSource = null;
                }
```

置き換え後:

```csharp
                    await client.RemoveComponentAsync(component.RelocationSource.Id, cancellationToken);
                    counts.ComponentsDeleted++;
                    component.RelocationSource = null;
                    await SaveSlotIndexesAsync(prepared, component.RelocationSourceSlotKey!, component.RelocationSourceSlotId!,
                        cancellationToken);
                }
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    await client.RemoveComponentAsync(deletion.Id, cancellationToken);
                    prepared.State.Components.Remove(deletion.Key);
                    counts.ComponentsDeleted++;
                    Checkpoint(prepared);
```

置き換え後:

```csharp
                    await client.RemoveComponentAsync(deletion.Id, cancellationToken);
                    prepared.State.Components.Remove(deletion.Key);
                    counts.ComponentsDeleted++;
                    await SaveSlotIndexesAsync(prepared, deletion.SlotKey!, deletion.SlotId!, cancellationToken);
                    Checkpoint(prepared);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
                    if (runtime.RelocationSource?.Id == existing?.Id) runtime.RelocationSource = null;
```

追加する内容:

```csharp
                    if (runtime.RelocationSource is not null)
                        (runtime.RelocationSourceSlotKey, runtime.RelocationSourceSlotId) = (stateComponent.SlotKey, sourceSlot!.Id);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            var deletion = new DeletionRuntime("component", stateComponent.Key, component.Id,
                slot.Path + "/@" + stateComponent.Key, "stable key is no longer declared inside the owned boundary");
```

置き換え後:

```csharp
            var deletion = new DeletionRuntime("component", stateComponent.Key, component.Id,
                slot.Path + "/@" + stateComponent.Key, "stable key is no longer declared inside the owned boundary",
                SlotKey: stateComponent.Value.SlotKey, SlotId: slot.Id);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static void Checkpoint(PreparedApply prepared)
    {
```

追加する内容:

```csharp
    // Removing a Component moves the ones after it, and after a world reload a key without identity values is bound by
    // its saved index. Read the Slot again and save every key whose saved ID is on it at that Component's position.
    // A key whose ID is not on the Slot keeps its index. The caller's next checkpoint persists the result.
    private async Task SaveSlotIndexesAsync(PreparedApply prepared, string slotKey, string slotId,
        CancellationToken cancellationToken)
    {
        var layout = (await client.GetSlotAsync(slotId, 0, false, cancellationToken)).Components
            .Select(component => component.Id).ToList();
        foreach (var (key, saved) in prepared.State.Components.Where(pair => pair.Value.SlotKey == slotKey).ToArray())
        {
            var index = string.IsNullOrEmpty(saved.Id) ? -1 : layout.IndexOf(saved.Id);
            if (index >= 0 && saved.ComponentIndex != index)
                prepared.State.Components[key] = saved with { ComponentIndex = index };
        }
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        public ComponentSummary? RelocationSource { get; set; }
```

追加する内容:

```csharp
        public string? RelocationSourceSlotKey { get; set; }
        public string? RelocationSourceSlotId { get; set; }
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
    private sealed record DeletionRuntime(string Kind, string Key, string Id, string Path, string Reason,
        IReadOnlyList<string>? CoveredSlotKeys = null, IReadOnlyList<string>? CoveredComponentKeys = null);
```

置き換え後:

```csharp
    private sealed record DeletionRuntime(string Kind, string Key, string Id, string Path, string Reason,
        IReadOnlyList<string>? CoveredSlotKeys = null, IReadOnlyList<string>? CoveredComponentKeys = null,
        string? SlotKey = null, string? SlotId = null);
```

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
複数候補が残る場合は`STABLE_COMPONENT_AMBIGUOUS`として停止します。
```

追加する内容:

```markdown
applyがComponentを削除・移動した後は、同じSlotに残るkeyのindexも保存し直すため、ワールドの再読込後もindexで正しく照合できます。
```

- [ ] **Step 4: 成功することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload|FullyQualifiedName~AnUndeclaredSiblingKeepsItsIndex"
```

Expected: 3 件とも PASS。

- [ ] **Step 5: 全件を実行してコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add src/RLoop.Core/WorldService.cs docs/DECLARATIVE.md tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs
git commit -F - <<'EOF'
Save the indexes of the Components left on a Slot after a removal

After a world reload, apply binds a key without identity values by its
saved componentIndex. Apply saved that index only for the Components it
planned, so removing a Component (the source of a move, or a pruned one)
shifted the Components after it without saving them again. The next apply
after a world reload then bound a key to a sibling's Component or stopped
on STABLE_COMPONENT_AMBIGUOUS.

After each removal, apply now reads the Slot again and saves every key
whose saved ID is still on it at that Component's position. The checkpoint
that follows the removal persists them.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: 全件が PASS（`RLoop.Tests` 329 件）。

### Task A3: 文書から外した key の照合結果の保存

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`BuildDeletionPlans`）
- Modify: `tests/RLoop.Tests/ApplyWorkflowTests.cs`（偽クライアントに `LoseResponseOnWrite` を追加）
- Modify: `docs/DECLARATIVE.md`
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

**Interfaces:**
- Consumes: Task A2 の `SaveSlotIndexesAsync`
- Produces: 偽クライアントの `public int? LoseResponseOnWrite { get; set; }`（その番号の書き込みを反映してから、応答を失ったとして `IOException` を投げる。Slot・Component の作成と削除、Slot の更新、フィールドの書き込みのすべてが対象）

- [ ] **Step 1: テストと偽クライアントの拡張を書く**

2 つ目のテストは、移動を含む apply を書き込みの位置ごとに止め（反映前に失敗／反映後に応答を失う）、同じセッションの次の apply の後に I1 が成り立ち、再読込後の apply の書き込みが 0 件になることを確かめる。移動の途中で止まると移動元が残ることがあるが、これは上流の既存の課題で、このテストでは index だけを確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分の直後に追加する。

```csharp
        public int? FailOnWrite { get; set; }
```

追加する内容:

```csharp
        // The write with this number lands, and then its response is lost.
        public int? LoseResponseOnWrite { get; set; }
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
                throw new OperationCanceledException("Simulated lost create response.");
            }
            return Task.FromResult(id);
```

置き換え後:

```csharp
                throw new OperationCanceledException("Simulated lost create response.");
            }
            Acknowledge();
            return Task.FromResult(id);
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            if (request.Scale is not null) slot.Scale = request.Scale;
            return Task.CompletedTask;
```

置き換え後:

```csharp
            if (request.Scale is not null) slot.Scale = request.Scale;
            Acknowledge();
            return Task.CompletedTask;
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            RemoveSlotTree(slot);
            return Task.CompletedTask;
```

置き換え後:

```csharp
            RemoveSlotTree(slot);
            Acknowledge();
            return Task.CompletedTask;
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            _slots[slotId].Components.Add(component);
            return Task.FromResult(new ComponentCreateResult(id, componentType));
```

置き換え後:

```csharp
            _slots[slotId].Components.Add(component);
            Acknowledge();
            return Task.FromResult(new ComponentCreateResult(id, componentType));
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
                _components[componentId].Members["Target"] = new MemberValue("reference", componentId + ":Target");
            return Task.CompletedTask;
```

置き換え後:

```csharp
                _components[componentId].Members["Target"] = new MemberValue("reference", componentId + ":Target");
            Acknowledge();
            return Task.CompletedTask;
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            _components.Remove(componentId);
            return Task.CompletedTask;
```

置き換え後:

```csharp
            _components.Remove(componentId);
            Acknowledge();
            return Task.CompletedTask;
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分の直後に追加する。

```csharp
            if (CancelAfterWrites == Writes) Cancellation?.Cancel();
        }
```

追加する内容:

```csharp

        // Called once a write has landed in the fake world.
        private void Acknowledge()
        {
            if (LoseResponseOnWrite == Writes) throw new IOException("Simulated lost response after the write landed.");
        }
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` の次の部分の直前に追加する。

```csharp
    // Same-type siblings without identityFields: after a world reload only their saved indexes tell them apart.
```

追加する内容:

```csharp
    [Fact]
    public async Task UndeclaredKeysStayInTheDeletionPlanAfterAnApplyInTheReloadedSession()
    {
        var document = ReloadDocument("bindings", ReloadedWorld);
        var trimmed = ReloadDocument("bindings-trimmed", """
            {"schemaVersion":"1","ownership":{"key":"reload"},"slot":{"key":"root","name":"OwnedWorld","parent":"Root"},
             "children":[{"slot":{"key":"terrain","name":"Terrain"}}]}
            """);
        var client = new FakeResoniteClient(document);
        var service = new WorldService(client);
        var state = Path.Combine(_root, "bindings.state.json");
        await service.ApplyAsync(document, new ApplyOptions(state));
        client.ReloadWorld("session-reloaded");
        var first = await service.PlanApplyAsync(trimmed, new ApplyOptions(state, Prune: true));
        await service.ApplyAsync(trimmed, new ApplyOptions(state));

        var second = await service.PlanApplyAsync(trimmed, new ApplyOptions(state, Prune: true));

        string[] Deletions(ApplyPlanResult plan) => plan.Operations.Where(operation => operation.Action == "delete")
            .Select(operation => operation.Kind + ":" + operation.Key).Order(StringComparer.Ordinal).ToArray();
        Assert.Equal(["component:renderer", "slot:foundation"], Deletions(first));
        Assert.Equal(Deletions(first), Deletions(second));
        await service.ApplyAsync(trimmed, new ApplyOptions(state, Prune: true, ConfirmDeletes: true));
        var owned = client.Root.Children.Single();
        Assert.Empty(owned.Components);
        Assert.Empty(owned.Children.Single().Children);
    }

    // An interrupted move can leave its source Component behind (an existing upstream issue that this change does not
    // address). Wherever the apply stops, the next apply in the same session must still save indexes that bind every key
    // to its own Component after a world reload.
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AnApplyInterruptedAtAnyWriteSavesBindableIndexesOnTheNextApply(bool responseLost)
    {
        for (var write = 1; ; write++)
        {
            var name = $"indexes-interrupted-{responseLost}-{write}";
            var full = ReloadDocument(name, IndexedSiblings(name, ["v1", "v2", "v3"]));
            var moved = ReloadDocument(name + "-moved", IndexedSiblings(name, ["v2"], ["v1"]));
            var client = new FakeResoniteClient(full);
            var service = new WorldService(client);
            var state = Path.Combine(_root, name + ".state.json");
            await service.ApplyAsync(full, new ApplyOptions(state));
            client.ResetWriteCounts();
            if (responseLost) client.LoseResponseOnWrite = write;
            else client.FailOnWrite = write;

            var interrupted = await InterruptedAsync(() => service.ApplyAsync(moved, new ApplyOptions(state)));
            client.LoseResponseOnWrite = null;
            client.FailOnWrite = null;
            await service.ApplyAsync(moved, new ApplyOptions(state));

            AssertSavedIndexesMatchLayout(client, state);
            client.ReloadWorld("session-reloaded");
            client.ResetWriteCounts();
            await service.ApplyAsync(moved, new ApplyOptions(state));
            Assert.True(client.Writes == 0, $"write {write}: the apply after the reload wrote {client.Writes} time(s).");
            if (!interrupted) break;
        }
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~UndeclaredKeysStayInTheDeletionPlan|FullyQualifiedName~AnApplyInterruptedAtAnyWriteSavesBindableIndexes"
```

Expected: 3 件のうち 2 件が FAIL。`UndeclaredKeysStayInTheDeletionPlanAfterAnApplyInTheReloadedSession` は、2 回目の plan の削除対象が空になる（`Assert.Equal() Failure: Collections differ`）。`AnApplyInterruptedAtAnyWriteSavesBindableIndexesOnTheNextApply(responseLost: True)` は、削除の応答が失われた後の apply で、文書から外した `v3` の index が直らない。反映前に失敗する場合（`responseLost: False`）は、次の apply が削除をやり直して Task A2 の処理で index を保存し直すので、この時点で PASS する。

- [ ] **Step 3: 削除計画の照合結果を保存し、文書を更新する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            staleSlots.Add((stateSlot.Key, stateSlot.Value, slot, slot.Path ?? stateSlot.Value.Path));
        }
```

置き換え後:

```csharp
            staleSlots.Add((stateSlot.Key, stateSlot.Value, slot, slot.Path ?? stateSlot.Value.Path));
            // Keep the binding: once a checkpoint records this session, a stale ID would hide the Slot from later plans.
            if (stateSlot.Value.Id != slot.Id) prepared.State.Slots[stateSlot.Key] = stateSlot.Value with { Id = slot.Id };
        }
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            if (component is null) continue;
            var deletion = new DeletionRuntime("component", stateComponent.Key, component.Id,
```

置き換え後:

```csharp
            if (component is null) continue;
            // Keep the binding and its position, so later plans in this session and SaveSlotIndexesAsync still find it.
            var index = slot.Components.ToList().FindIndex(candidate => candidate.Id == component.Id);
            if (stateComponent.Value.Id != component.Id || stateComponent.Value.ComponentIndex != index)
                prepared.State.Components[stateComponent.Key] = stateComponent.Value with { Id = component.Id, ComponentIndex = index };
            var deletion = new DeletionRuntime("component", stateComponent.Key, component.Id,
```

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
delete候補はstateに記録されたownership root内の対象だけです。
```

追加する内容:

```markdown
ワールドの再読込後に照合したstaleなSlot / ComponentのIDはstateへ保存するため、同じセッションで続けて実行する`--deletes-only`や`--prune`でも対象から外れません。
```

- [ ] **Step 4: 成功することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~UndeclaredKeysStayInTheDeletionPlan|FullyQualifiedName~AnApplyInterruptedAtAnyWriteSavesBindableIndexes"
```

Expected: 3 件とも PASS。

- [ ] **Step 5: 全件を実行してコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add src/RLoop.Core/WorldService.cs docs/DECLARATIVE.md tests/RLoop.Tests/ApplyWorkflowTests.cs tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs
git commit -F - <<'EOF'
Keep the bindings of undeclared keys after a world reload

After a world reload the deletion plan binds the Slots and Components
that the document no longer declares, but apply never saved those
bindings. The first apply in the reloaded session moved the checkpoint
to the new session while those keys kept their old IDs, so later plans in
the same session looked them up by the old IDs, found nothing, and dropped
them from --deletes-only and --prune. Their indexes were not saved again
either, so an interrupted removal could leave them stale.

The deletion plan now saves the ID it binds for each such Slot and
Component, and the Component's index, and the next checkpoint persists
them. Plans and tests still never write state.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: 全件が PASS（`RLoop.Tests` 332 件）。

### Task A4: 修正前との比較、push、fork の PR A

**Files:** なし（確認と公開）

- [ ] **Step 1: 修正前の `src/` で、追加したテストが失敗することを確かめる**

```bash
cd /workspaces/reso-world/external/resoloop
git worktree add --detach .worktrees/compare-a fix/slot-index-after-removal
cd .worktrees/compare-a
git checkout origin/main -- src
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ApplyWorkflowTests.RemovingAComponentSaves|FullyQualifiedName~AnUndeclaredSiblingKeeps|FullyQualifiedName~UndeclaredKeysStay|FullyQualifiedName~SavesBindableIndexes"
cd .. && git worktree remove --force compare-a
```

Expected: 6 件とも FAIL。

- [ ] **Step 2: 上流 CI と同じ確認を行う**

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore
git log --oneline origin/main..HEAD
```

Expected: `RLoop.Tests` 332 件、`RLoop.IntegrationTests` 19 件がすべて PASS、警告 0 件。コミットは Task A2・A3 の 2 件。

- [ ] **Step 3: push して PR を出す**

`#7` の部分は、Task A1 で作成した Issue の番号に置き換える。

```bash
git push -u origin fix/slot-index-after-removal
gh pr create --repo usaturn/resoloop --base main --head fix/slot-index-after-removal --title "Save Component indexes after a removal and keep undeclared bindings after a world reload / Component の削除後に index を保存し直し、再読込後も文書から外した key の照合結果を保つ" --body-file - <<'EOF'
## Summary / 概要

- After apply removes a Component (the source of a move, or a pruned Component), it reads the Slot again and saves the index of every key whose saved ID is still on it.
- After a world reload, the deletion plan's bindings for keys that the document no longer declares (Slot IDs, Component IDs and indexes) are saved in the next checkpoint, so later plans in the same session still find them.

- apply が Component を削除した後（移動元、または prune）、Slot を読み直し、保存している ID が Slot 上にある key の index を保存し直します。
- ワールドの再読込後、削除計画が文書から外した key に照合した結果（Slot の ID、Component の ID と index）を次の checkpoint で保存し、同じセッションの後続の plan でも見つかるようにします。

Fixes #7

## Root cause / 原因

- A world reload binds keys without `identityFields` by their saved `componentIndex`, but a removal shifted the Components after it without saving them again. The next apply after a reload bound a key to a sibling's Component or stopped on `STABLE_COMPONENT_AMBIGUOUS`.
- The deletion plan's bindings were never saved. The first apply in a reloaded session moved the checkpoint to the new session while undeclared keys kept their old IDs, so later plans in that session dropped them from `--deletes-only` and `--prune`.

- 再読込後は `identityFields` の無い key を保存した `componentIndex` で照合しますが、削除の後ろにある Component の index を保存し直していませんでした。そのため再読込後の apply が、兄弟の Component に結び付くか、`STABLE_COMPONENT_AMBIGUOUS` で止まりました。
- 削除計画の照合結果を保存していなかったため、再読込後の最初の apply で checkpoint のセッションだけが新しくなり、文書から外した key は古い ID のまま残りました。その後の同じセッションの plan では、`--deletes-only` と `--prune` の対象から外れていました。

## Verification / 確認

- `dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore`: RLoop.Tests 332 and RLoop.IntegrationTests 19 passed, 0 warnings.
- New tests in `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` cover a prune and a move followed by a world reload, an undeclared sibling, undeclared keys after an apply in the reloaded session, and an apply interrupted at every write (before the write lands, and after it lands with its response lost).
- With `src/` reverted to `main`, all 6 new test cases fail.

- 上記のコマンドで、RLoop.Tests 332 件と RLoop.IntegrationTests 19 件が成功し、警告は 0 件でした。
- `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` に、prune・移動の後の再読込、文書から外した兄弟、再読込後のセッションでの apply の後の照合、書き込みの位置ごとの中断（反映前の失敗と、反映後の応答の喪失）のテストを追加しました。
- `src/` を `main` に戻すと、追加した 6 件はすべて失敗します。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: PR の URL が表示される。この PR はマージしない（D-8）。

---

## Part B: リスト縮小時の作り直し（`fix/list-shrink-recreate-split`）

作業ディレクトリ: `/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split`

### Task B1: 偽クライアントのリストと、テストの共通処理

**Files:**
- Modify: `tests/RLoop.Tests/ApplyWorkflowTests.cs`（`FakeResoniteClient`）
- Create: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Produces（偽クライアント）: `ListMembers`（参照のリストとして持つメンバー名。既定は `Materials`。短いリストを送ると先頭だけを置き換え、末尾を残す）、`RefillListsTo`（書き込んだリストを、この要素数まで詰め直す）、`FailRemovingComponent`（この ID の Component の削除を、反映前に失敗させる）
- Produces（テストの補助）: `RubbleWorld(string ownership, params string[] materials)`、`RubbleWorld(string ownership, string[] materials, string? rendererSlot, bool watcher = false)`、`TwoRendererWorld(...)`、`ApplyRubbleAsync(string name, string changed, string? initial = null)`、`ApplyScenarioAsync(string name, string scenario)`、`AssertListShrinkConvergedAsync(...)`（収束の判定）、`RubbleRenderers`、`Sources`、`MaterialTargets`、`StateId`

- [ ] **Step 1: B の worktree を作る**

```bash
cd /workspaces/reso-world/external/resoloop
git worktree add .worktrees/list-shrink-recreate-split -b fix/list-shrink-recreate-split fix/slot-index-after-removal
cd .worktrees/list-shrink-recreate-split
```

- [ ] **Step 2: 偽クライアントを拡張し、共通処理と最初のテストを書く**

偽クライアントは、Resonite `2026.9.18.82` と ResoniteLink `0.13.1` で観測したリストの挙動（`[A,B]` に `[A]` を送っても `[A,B]`、`[]` では変わらず、続けて `[B]` を送ると `[B,B]`）をまねる。最初のテストは、長くなるリストと並べ替えたリストが従来どおりその場で更新されることを確かめる（偽クライアントの回帰の確認）。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分の直後に追加する。

```csharp
        public List<string> DescribedTypes { get; } = [];
```

追加する内容:

```csharp
        // Members kept as lists of references. ResoniteLink 0.13.1 replaces only the leading elements and cannot remove any
        // (Resonite 2026.9.18.82): [A,B] stays [A,B] after [A], [] changes nothing, and [B] then gives [B,B].
        public HashSet<string> ListMembers { get; } = new(StringComparer.Ordinal) { "Materials" };
        // When set, every written list is padded back to this many elements, as runtime logic that refills a list would.
        public int? RefillListsTo { get; set; }
        // Removing this Component fails before it lands.
        public string? FailRemovingComponent { get; set; }
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            foreach (var member in _knownMembers.GetValueOrDefault(componentType) ?? [])
                component.Members[member] = new MemberValue("field", id + ":" + member, "bool", JsonValue.Create(false));
```

置き換え後:

```csharp
            foreach (var member in _knownMembers.GetValueOrDefault(componentType) ?? [])
                component.Members[member] = InitialMember(id, member);
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
        public Task RemoveComponentAsync(string componentId, CancellationToken cancellationToken = default)
        {
            Write();
```

置き換え後:

```csharp
        public Task RemoveComponentAsync(string componentId, CancellationToken cancellationToken = default)
        {
            if (componentId == FailRemovingComponent) throw new IOException("Simulated failure while removing a Component.");
            Write();
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
                new MemberDefinitionInfo(name, name is "Target" or "Mesh" or "TargetValue" ? "reference" : "field",
```

置き換え後:

```csharp
                new MemberDefinitionInfo(name, name is "Target" or "Mesh" or "TargetValue" ? "reference" : ListMembers.Contains(name) ? "list" : "field",
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
            foreach (var member in _knownMembers.GetValueOrDefault(type) ?? [])
                component.Members[member] = new MemberValue("field", component.Id + ":" + member, "bool", JsonValue.Create(false));
```

置き換え後:

```csharp
            foreach (var member in _knownMembers.GetValueOrDefault(type) ?? [])
                component.Members[member] = InitialMember(component.Id, member);
```

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分を置き換える。

置き換え前:

```csharp
        private static void SetFields(FakeComponent component, IReadOnlyDictionary<string, string> fields)
        {
            foreach (var field in fields)
            {
                var id = component.Id + ":" + field.Key;
```

置き換え後:

```csharp
        private MemberValue InitialMember(string componentId, string member) => ListMembers.Contains(member)
            ? new MemberValue("list", componentId + ":" + member, Elements: [])
            : new MemberValue("field", componentId + ":" + member, "bool", JsonValue.Create(false));

        private MemberValue WriteList(MemberValue? current, string id, string raw)
        {
            var desired = (JsonNode.Parse(raw) as JsonArray ?? []).Select(node => node?.GetValue<string>()).ToArray();
            var kept = current?.Elements ?? [];
            var elements = new List<MemberValue>();
            for (var i = 0; i < Math.Max(desired.Length, kept.Count); i++)
                elements.Add(i < desired.Length ? new MemberValue("reference", $"{id}[{i}]", TargetId: desired[i]) : kept[i]);
            while (RefillListsTo is { } refill && elements.Count > 0 && elements.Count < refill)
                elements.Add(elements[^1] with { Id = $"{id}[{elements.Count}]" });
            return new MemberValue("list", id, Elements: elements);
        }

        private void SetFields(FakeComponent component, IReadOnlyDictionary<string, string> fields)
        {
            foreach (var field in fields)
            {
                var id = component.Id + ":" + field.Key;
                if (ListMembers.Contains(field.Key))
                {
                    component.Members[field.Key] = WriteList(component.Members.GetValueOrDefault(field.Key), id, field.Value);
                    continue;
                }
```

**新規作成:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

```csharp
using System.Text.Json;
using System.Text.Json.Nodes;
using RLoop.Core;

namespace RLoop.Tests;

public sealed partial class ApplyWorkflowTests
{
    [Theory]
    [InlineData("grow")]
    [InlineData("reorder")]
    public async Task AListThatDoesNotShrinkIsUpdatedInPlace(string change)
    {
        var name = "in-place-" + change;
        var (client, service, state, changed) = await ApplyRubbleAsync(name,
            change == "grow" ? RubbleWorld(name, "m1", "m2", "m3", "m4") : RubbleWorld(name, "m2", "m1"),
            RubbleWorld(name, "m1", "m2"));
        var original = RubbleRenderers(client).Single().Id;

        var plan = await service.PlanApplyAsync(changed, new ApplyOptions(state));
        await service.ApplyAsync(changed, new ApplyOptions(state));

        Assert.Equal("update", Assert.Single(plan.Operations, operation => operation.Key == "renderer").Action);
        Assert.Equal(original, RubbleRenderers(client).Single().Id);
        var expected = change == "grow" ? new[] { "m1", "m2", "m3", "m4" } : ["m2", "m1"];
        Assert.Equal(expected.Select(key => StateId(state, key)), MaterialTargets(RubbleRenderers(client).Single()));
    }

    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
    // the renderer. With watcher, a Source on a later Slot also points at the renderer.
    private static string RubbleWorld(string ownership, params string[] materials) =>
        RubbleWorld(ownership, materials, "rubble");

    private static string RubbleWorld(string ownership, string[] materials, string? rendererSlot, bool watcher = false)
    {
        var list = string.Join(",", materials.Select(material => $"\"$ref:{material}\""));
        var renderer = rendererSlot is null ? "" :
            $$$"""{"key":"renderer","type":"Test.Renderer","fields":{"Materials":[{{{list}}}]}},""";
        var source = rendererSlot is null ? "" : """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""";
        var rubble = rendererSlot == "elsewhere"
            ? $$$"""{"slot":{"key":"rubble","name":"Rubble01"},"components":[{{{source}}}]},{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[{{{renderer.TrimEnd(',')}}}]}"""
            : $$$"""{"slot":{"key":"rubble","name":"Rubble01"},"components":[{{{renderer}}}{{{source}}}]}""";
        var late = watcher ? """,{"slot":{"key":"late","name":"Late"},"components":[{"key":"watcher","type":"Test.Source","fields":{"Target":"$ref:renderer"}}]}""" : "";
        return $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{ownership}}}"},"slot":{"key":"root","name":"Rubble","parent":"Root"},
             "children":[
               {"slot":{"key":"materials","name":"Materials"},"components":[
                 {"key":"m1","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m2","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m3","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m4","type":"Test.Material","fields":{"Enabled":true}}]},
               {{{rubble}}}{{{late}}}]}
            """;
    }

    // Two same-type renderers on one Slot without identityFields, so a world reload binds them by their saved indexes.
    // In the shared-slot scenario a sibling moves away, another is no longer declared, and r1 also gets a material that is
    // created later in the same apply.
    private static string TwoRendererWorld(string ownership, string[] first, string[] second, bool shared = false, bool shrunk = false)
    {
        static string List(IEnumerable<string> keys) => string.Join(",", keys.Select(key => $"\"$ref:{key}\""));
        var siblings = !shared ? "" : shrunk ? "" :
            """,{"key":"mover","type":"Test.Indexed","fields":{"Value":7}},{"key":"leftover","type":"Test.Indexed","fields":{"Value":8}}""";
        var extra = !shared || !shrunk ? "" :
            """,{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[{"key":"mover","type":"Test.Indexed","fields":{"Value":7}}]},{"slot":{"key":"late-slot","name":"Late"},"components":[{"key":"late","type":"Test.Material","fields":{"Enabled":true}}]}""";
        return $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{ownership}}}"},"slot":{"key":"root","name":"Rubble","parent":"Root"},
             "children":[
               {"slot":{"key":"materials","name":"Materials"},"components":[
                 {"key":"m1","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m2","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m3","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m4","type":"Test.Material","fields":{"Enabled":true}}]},
               {"slot":{"key":"rubble","name":"Rubble01"},"components":[
                 {"key":"r1","type":"Test.Renderer","fields":{"Materials":[{{{List(first)}}}]}},
                 {"key":"r2","type":"Test.Renderer","fields":{"Materials":[{{{List(second)}}}]}}{{{siblings}}},
                 {"key":"source","type":"Test.Source","fields":{"Target":"$ref:r1"}}]}{{{extra}}}]}
            """;
    }

    // Applies the initial world (four materials unless given), then returns the changed document for the test to apply.
    private async Task<(FakeResoniteClient Client, WorldService Service, string State, ApplyDocument Changed)> ApplyRubbleAsync(
        string name, string changed, string? initial = null)
    {
        var first = ReloadDocument(name, initial ?? RubbleWorld(name, "m1", "m2", "m3", "m4"));
        var second = ReloadDocument(name + "-changed", changed);
        var client = new FakeResoniteClient(second);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(first, new ApplyOptions(state));
        client.ResetWriteCounts();
        return (client, service, state, second);
    }

    private async Task<(FakeResoniteClient Client, WorldService Service, string State, ApplyDocument Shrunk, string Referenced,
        Dictionary<string, string[]> Expected)> ApplyScenarioAsync(string name, string scenario)
    {
        if (scenario == "one-recreate")
        {
            var (client, service, state, shrunk) = await ApplyRubbleAsync(name, RubbleWorld(name, "m1", "m2", "m3"));
            return (client, service, state, shrunk, "renderer", new() { ["renderer"] = ["m1", "m2", "m3"] });
        }
        var initial = ReloadDocument(name, TwoRendererWorld(name, ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3"], shared: true));
        var shrunkShared = ReloadDocument(name + "-shrunk", TwoRendererWorld(name, ["m1", "m2", "late"], ["m1", "m2"], shared: true, shrunk: true));
        var sharedClient = new FakeResoniteClient(shrunkShared);
        var sharedService = new WorldService(sharedClient);
        var sharedState = Path.Combine(_root, name + ".state.json");
        await sharedService.ApplyAsync(initial, new ApplyOptions(sharedState));
        sharedClient.ResetWriteCounts();
        return (sharedClient, sharedService, sharedState, shrunkShared, "r1", new() { ["r1"] = ["m1", "m2", "late"], ["r2"] = ["m1", "m2"] });
    }

    // Converged: each declared renderer is the only Component bound to its key and holds the declared Materials, the
    // managed Source points at it, no recreate is in progress, every saved index matches the layout (I1), and neither
    // another apply nor an apply after a world reload writes anything.
    private async Task AssertListShrinkConvergedAsync(FakeResoniteClient client, WorldService service, ApplyDocument document,
        string state, string referenced, IReadOnlyDictionary<string, string[]> expected, string context = "")
    {
        Assert.False(File.ReadAllText(state).Contains("supersededId", StringComparison.Ordinal), context + "a recreate is still in progress.");
        var renderers = RubbleRenderers(client);
        Assert.True(renderers.Length == expected.Count, $"{context}Rubble01 has {renderers.Length} renderer(s).");
        foreach (var (key, materials) in expected)
        {
            var renderer = Assert.Single(renderers, component => component.Id == StateId(state, key));
            Assert.Equal(materials.Select(material => StateId(state, material)), MaterialTargets(renderer));
        }
        Assert.Equal(StateId(state, referenced), Sources(client).Single(source => source.Id == StateId(state, "source")).Members["Target"].TargetId);
        AssertSavedIndexesMatchLayout(client, state);
        client.ResetWriteCounts();
        await service.ApplyAsync(document, new ApplyOptions(state));
        Assert.True(client.Writes == 0, $"{context}the next apply wrote {client.Writes} time(s).");
        client.ReloadWorld("session-after-convergence");
        await service.ApplyAsync(document, new ApplyOptions(state));
        Assert.True(client.Writes == 0, $"{context}the apply after a world reload wrote {client.Writes} time(s).");
    }

    private static FakeResoniteClient.FakeComponent[] RubbleRenderers(FakeResoniteClient client) =>
        AllSlots(client.Root).Single(slot => slot.Name == "Rubble01").Components
            .Where(component => component.Type == "Test.Renderer").ToArray();

    private static FakeResoniteClient.FakeComponent[] Sources(FakeResoniteClient client) =>
        AllSlots(client.Root).SelectMany(slot => slot.Components).Where(component => component.Type == "Test.Source").ToArray();

    private static string?[] MaterialTargets(FakeResoniteClient.FakeComponent renderer) =>
        renderer.Members["Materials"].Elements!.Select(element => element.TargetId).ToArray();

    private static string StateId(string state, string key) =>
        JsonNode.Parse(File.ReadAllText(state))!["components"]![key]!["id"]!.GetValue<string>();
}
```

- [ ] **Step 3: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AListThatDoesNotShrinkIsUpdatedInPlace"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add tests/RLoop.Tests/ApplyWorkflowTests.cs tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit -m "test: model list members that ResoniteLink cannot shrink in the fake client" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 2 件とも PASS、全件も PASS（`RLoop.Tests` 334 件）。B のコミットは Task B8 で 2 件にまとめる。

### Task B2: state、縮小の検出、plan の表示、所有権の検査

**Files:**
- Modify: `src/RLoop.Core/ApplyWorkflow.cs`（`ApplyStateComponent`）
- Modify: `src/RLoop.Core/WorldService.cs`（`PlanApplyAsync`、`BuildComponentPlans`、`ListShrinkReason`、`ValidateComponentOwnership`、`CreateComponentState`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Produces: `ApplyStateComponent.SupersededId`（`string?`。null のときは書かない）。`ComponentRuntime` の `Superseded`（置き換え元の `ComponentSummary?`）、`SupersededId`、`RecreateReason`、`StateBeforeRecreate`。`private static string? ListShrinkReason(ApplyComponentSpec spec, ComponentSummary existing)`（縮む list member があれば理由の文言、無ければ null）。plan の操作 `recreate`。所有権の検査の種類 `superseded`。

- [ ] **Step 1: テストを書く**

plan に `recreate` が出ること、syncObject の中のリストと移動する Component は作り直さないこと、置き換え元をほかの key が指していれば止まることを確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Fact]
    public async Task APlanShowsARecreateWhenADeclaredListShrinks()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("shrink-plan", RubbleWorld("shrink-plan", "m1", "m2", "m3"));

        var plan = await service.PlanApplyAsync(shrunk, new ApplyOptions(state));

        var recreate = Assert.Single(plan.Operations, operation => operation.Action == "recreate");
        Assert.Equal("renderer", recreate.Key);
        Assert.Contains("list member 'Materials' shrinks from 4 to 3 elements", recreate.Reason);
        Assert.Contains("initialFields and undeclared members return to their defaults", recreate.Reason);
        Assert.Equal(StateId(state, "m4"), Assert.Single(Assert.Single(recreate.Diffs!).Removed!)!.GetValue<string>());
        Assert.Equal(0, plan.Creates);
        Assert.Equal(2, plan.Updates); // the recreate and the Source that will point at the replacement
        Assert.Equal(0, client.Writes);
    }

    [Fact]
    public async Task AShorterListInsideASyncObjectIsNotRecreated()
    {
        var document = ReloadDocument("nested-list", """
            {"schemaVersion":"1","ownership":{"key":"nested-list"},"slot":{"key":"root","name":"Nested","parent":"Root"},
             "components":[{"key":"holder","type":"Test.Holder","fields":{"Nested":{"Items":["a"]}}}]}
            """);
        var client = new FakeResoniteClient(document);
        var service = new WorldService(client);
        var state = Path.Combine(_root, "nested-list.state.json");
        await service.ApplyAsync(document, new ApplyOptions(state));
        var holder = client.Root.Children.Single().Components.Single();
        holder.Members["Nested"] = new MemberValue("syncObject", holder.Id + ":Nested", Members: new Dictionary<string, MemberValue>
        {
            ["Items"] = new("list", holder.Id + ":Nested.Items",
                Elements: [new MemberValue("field", null, "string", JsonValue.Create("a")), new MemberValue("field", null, "string", JsonValue.Create("b"))])
        });
        client.ResetWriteCounts();

        var plan = await service.PlanApplyAsync(document, new ApplyOptions(state));

        Assert.Equal("update", Assert.Single(plan.Operations, operation => operation.Key == "holder").Action);
        Assert.Equal(0, client.Writes);
    }

    [Fact]
    public async Task AComponentMovedWithAShorterListIsRelocatedNotRecreated()
    {
        var (client, service, state, moved) = await ApplyRubbleAsync("moved-shrink",
            RubbleWorld("moved-shrink", ["m1", "m2", "m3"], rendererSlot: "elsewhere"));

        var plan = await service.PlanApplyAsync(moved, new ApplyOptions(state));
        await service.ApplyAsync(moved, new ApplyOptions(state));

        Assert.Equal("relocate", Assert.Single(plan.Operations, operation => operation.Key == "renderer").Action);
        Assert.Empty(RubbleRenderers(client));
        var renderer = AllSlots(client.Root).Single(slot => slot.Name == "Elsewhere").Components.Single();
        Assert.Equal(new[] { "m1", "m2", "m3" }.Select(key => StateId(state, key)), MaterialTargets(renderer));
    }

    [Fact]
    public async Task AnotherKeyClaimingTheReplacedComponentStopsBeforeMutation()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("claimed", RubbleWorld("claimed", "m1", "m2", "m3"));
        var checkpoint = JsonNode.Parse(File.ReadAllText(state))!;
        checkpoint["components"]!["alias"] = checkpoint["components"]!["renderer"]!.DeepClone();
        File.WriteAllText(state, checkpoint.ToJsonString());

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_COMPONENT_OWNERSHIP_CONFLICT", error.Code);
        Assert.Contains("superseded", JsonSerializer.Serialize(error.Context["conflicts"]));
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~APlanShowsARecreate|FullyQualifiedName~AShorterListInsideASyncObject|FullyQualifiedName~AComponentMovedWithAShorterList|FullyQualifiedName~AnotherKeyClaimingTheReplaced"
```

Expected: `APlanShowsARecreateWhenADeclaredListShrinks` と `AnotherKeyClaimingTheReplacedComponentStopsBeforeMutation` が FAIL（`recreate` が無い、衝突の種類が `live`）。残りの 2 件は今の挙動を固定するテストなので PASS。

- [ ] **Step 3: 実装する**

この時点では plan だけが作り直しを扱い、apply の段階は Task B3 で加える（Task B3 の前に、縮むリストを持つ文書を apply しないこと）。

**変更:** `src/RLoop.Core/ApplyWorkflow.cs` の次の部分を置き換える。

置き換え前:

```csharp
    // Declared fields that reference $asset: when the fields were last applied. Null means an older state.
    IReadOnlyDictionary<string, JsonElement>? AssetFields = null);
```

置き換え後:

```csharp
    // Declared fields that reference $asset: when the fields were last applied. Null means an older state.
    IReadOnlyDictionary<string, JsonElement>? AssetFields = null,
    // The Component that a list-shrink recreate replaces, kept until apply removes it. Null when no recreate is in progress.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? SupersededId = null);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            prepared.Entries.Count(x => x.Action is "update" or "rename" or "relocate"),
```

置き換え後:

```csharp
            prepared.Entries.Count(x => x.Action is "update" or "rename" or "relocate" or "recreate"),
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                var existing = relocating || newManagedComponent ? null :
                    MatchComponent(node.Existing?.Components ?? [], spec.Type, ordinal, stateComponent, prepared.SameSession,
                        topologyTargets);
                var componentIndex = existing is null
                    ? (node.Existing?.Components.Count ?? 0) + prepared.Components.Count(candidate => candidate.Node == node && candidate.Existing is null)
                    : node.Existing!.Components.ToList().FindIndex(candidate => candidate.Id == existing.Id);
                var runtime = new ComponentRuntime(spec, node, existing, stableKey, ordinal,
                    node.Path + "/@" + (spec.Key ?? normalizedType + "[" + ordinal + "]"), componentIndex);
```

置き換え後:

```csharp
                ComponentSummary? superseded = null;
                var existing = relocating || newManagedComponent ? null :
                    MatchComponent(node.Existing?.Components ?? [], spec.Type, ordinal, stateComponent, prepared.SameSession,
                        topologyTargets);
                var recreateReason = existing is null ? null : ListShrinkReason(spec, existing);
                if (recreateReason is not null) (superseded, existing) = (existing, null);
                var componentIndex = existing is null
                    ? (node.Existing?.Components.Count ?? 0) + prepared.Components.Count(candidate => candidate.Node == node && candidate.Existing is null)
                    : node.Existing!.Components.ToList().FindIndex(candidate => candidate.Id == existing.Id);
                var runtime = new ComponentRuntime(spec, node, existing, stableKey, ordinal,
                    node.Path + "/@" + (spec.Key ?? normalizedType + "[" + ordinal + "]"), componentIndex)
                {
                    Superseded = superseded,
                    SupersededId = superseded?.Id,
                    RecreateReason = recreateReason,
                    StateBeforeRecreate = recreateReason is null ? null : stateComponent
                };
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            var action = component.RelocationSource is not null ? "relocate" : component.Existing is null ? "create" : "no-op";
            var reason = component.RelocationSource is not null
                ? $"stable key '{component.StableKey}' moves the Component to Slot '{component.Node.StableKey}'"
                : component.Existing is null ? "managed Component does not exist" : "Component and fields already match";
            var diffs = new List<ApplyMemberDiff>();
            if (component.Existing is not null)
            {
                foreach (var field in component.Spec.Fields ?? new Dictionary<string, JsonElement>())
                {
                    var resolvable = TryResolveRawForPlan(field.Value, existingByKey, slotsByKey, assetUrls, out var raw);
                    MemberValue? current = null;
                    var found = component.Existing.Members?.TryGetValue(field.Key, out current) == true;
                    if (!resolvable || !found || !MemberMatchesRaw(current!, raw))
                    {
                        action = "update";
                        reason = "one or more fields differ or depend on a new target";
```

置き換え後:

```csharp
            var action = component.RelocationSource is not null ? "relocate" : component.SupersededId is not null ? "recreate" :
                component.Existing is null ? "create" : "no-op";
            var reason = component.RelocationSource is not null
                ? $"stable key '{component.StableKey}' moves the Component to Slot '{component.Node.StableKey}'"
                : component.SupersededId is not null ? component.RecreateReason!
                : component.Existing is null ? "managed Component does not exist" : "Component and fields already match";
            var diffs = new List<ApplyMemberDiff>();
            var observed = component.Existing ?? component.Superseded;
            if (observed is not null)
            {
                foreach (var field in component.Spec.Fields ?? new Dictionary<string, JsonElement>())
                {
                    var resolvable = TryResolveRawForPlan(field.Value, existingByKey, slotsByKey, assetUrls, out var raw);
                    MemberValue? current = null;
                    var found = observed.Members?.TryGetValue(field.Key, out current) == true;
                    if (!resolvable || !found || !MemberMatchesRaw(current!, raw))
                    {
                        if (action != "recreate") (action, reason) = ("update", "one or more fields differ or depend on a new target");
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static ApplyMemberDiff ListDiff(string member, MemberValue current, string desiredRaw)
```

追加する内容:

```csharp
    // ResoniteLink 0.13.1 replaces only the leading elements of a list and cannot remove any (observed on Resonite
    // 2026.9.18.82), so a declared list shorter than the runtime list never converges in place.
    private static string? ListShrinkReason(ApplyComponentSpec spec, ComponentSummary existing)
    {
        var shrinks = (spec.Fields ?? new Dictionary<string, JsonElement>())
            .Where(field => field.Value.ValueKind == JsonValueKind.Array &&
                            existing.Members?.GetValueOrDefault(field.Key) is { Kind: "list" } current &&
                            (current.Elements?.Count ?? 0) > field.Value.GetArrayLength())
            .Select(field => $"list member '{field.Key}' shrinks from {existing.Members![field.Key].Elements!.Count} to {field.Value.GetArrayLength()} elements")
            .ToArray();
        return shrinks.Length == 0 ? null : string.Join("; ", shrinks) +
            "; ResoniteLink cannot remove list elements, so apply replaces the Component (initialFields and undeclared members return to their defaults)";
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            .Concat(prepared.Components.Where(component => component.RelocationSource is not null)
                .Select(component => (Id: component.RelocationSource!.Id, Key: component.StableKey, Kind: "relocation")))
            .Concat(prepared.Deletions.Where(deletion => deletion.Kind == "component")
```

置き換え後:

```csharp
            .Concat(prepared.Components.Where(component => component.RelocationSource is not null)
                .Select(component => (Id: component.RelocationSource!.Id, Key: component.StableKey, Kind: "relocation")))
            .Concat(prepared.Components.Where(component => component.Superseded is not null)
                .Select(component => (Id: component.Superseded!.Id, Key: component.StableKey, Kind: "superseded")))
            .Concat(prepared.Deletions.Where(deletion => deletion.Kind == "component")
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            referenceSelectors.Count == 0 ? null : referenceSelectors, assetFields);
```

置き換え後:

```csharp
            referenceSelectors.Count == 0 ? null : referenceSelectors, assetFields, component.SupersededId);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        public string? RelocationSourceSlotId { get; set; }
```

追加する内容:

```csharp
        // A list-shrink recreate: the Component it replaces while that is still on the Slot, and its ID until it is removed.
        public ComponentSummary? Superseded { get; set; }
        public string? SupersededId { get; set; }
        public string? RecreateReason { get; set; }
        // The saved record of a recreate this plan starts, restored if the replacement does not converge.
        public ApplyStateComponent? StateBeforeRecreate { get; set; }
```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~APlanShowsARecreate|FullyQualifiedName~AShorterListInsideASyncObject|FullyQualifiedName~AComponentMovedWithAShorterList|FullyQualifiedName~AnotherKeyClaimingTheReplaced"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Plan a recreate when a declared list member shrinks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 4 件とも PASS、全件も PASS（`RLoop.Tests` 338 件）。

### Task B3: 1 回の apply での作り直し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`ApplyAsync` の Component の段階・新しい検証の段階・新しい置き換え元の削除の段階、`DetectSavedAssetMigrations`、新しい `VerifyReplacementsAsync`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task A2 の `SaveSlotIndexesAsync`、Task B2 の `ComponentRuntime` のプロパティ
- Produces: `ComponentRuntime.ReplacementCreated`（この apply が置き換え先を作った）、`ComponentRuntime.AwaitsVerification`（置き換え元が残っている間は true。その間、置き換え先は参照先にしない。I4）、`private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates, Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey, IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)`（この時点では書き込みだけ。Task B4 で読み直しと取り消しを加え、引数に `ApplyCounts counts` が増える）

- [ ] **Step 1: テストを書く**

作り直しと参照の張り替え、アセットの移行、Review Focus の 1・2・4・5 を確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Fact]
    public async Task ShrinkingAListRecreatesTheComponentAndRepointsManagedReferences()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("shrink", RubbleWorld("shrink", "m1", "m2", "m3"));
        var original = RubbleRenderers(client).Single().Id;

        var applied = await service.ApplyAsync(shrunk, new ApplyOptions(state));

        Assert.Equal(1, applied.ComponentsAdded);
        Assert.Equal(1, applied.ComponentsDeleted);
        Assert.DoesNotContain(RubbleRenderers(client), component => component.Id == original);
        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ARecreateKeepsAnAssetUrlThatAWorldSaveMigrated(bool legacyState)
    {
        await File.WriteAllTextAsync(Path.Combine(_root, "crate.bin"), "first crate");
        var name = "recreate-asset-" + legacyState;
        string World(int materials) => $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{name}}}"},"slot":{"key":"root","name":"Assets","parent":"Root"},
             "assets":{"mesh":{"kind":"mesh","source":"crate.bin"}},
             "children":[
               {"slot":{"key":"materials","name":"Materials"},"components":[
                 {"key":"m1","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m2","type":"Test.Material","fields":{"Enabled":true}}]},
               {"slot":{"key":"crate","name":"Crate"},"components":[
                 {"key":"holder","type":"Test.AssetList","fields":{"URL":"$asset:mesh","Materials":[{{{string.Join(",", new[] { "\"$ref:m1\"", "\"$ref:m2\"" }.Take(materials))}}}]}}]}]}
            """;
        var initial = ReloadDocument(name, World(2));
        var shrunk = ReloadDocument(name + "-shrunk", World(1));
        var client = new FakeResoniteClient(initial) { ImportUrlPrefix = "local://machine/asset-" };
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(initial, new ApplyOptions(state));
        var holder = AllSlots(client.Root).Single(slot => slot.Name == "Crate").Components.Single();
        holder.Members["URL"] = holder.Members["URL"] with { Value = JsonValue.Create("resdb:///saved-crate") };
        client.ReloadWorld("session-saved");
        client.ResetWriteCounts();
        if (legacyState) RemoveRecordedAssetFields(state);

        if (legacyState)
        {
            var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
            Assert.Equal("APPLY_ASSET_MIGRATION_UNVERIFIED", error.Code);
            Assert.Equal(0, client.Writes);
            return;
        }
        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        var replacement = AllSlots(client.Root).Single(slot => slot.Name == "Crate").Components.Single();
        Assert.NotEqual(holder.Id, replacement.Id);
        Assert.Equal("resdb:///saved-crate", replacement.Members["URL"].Value!.GetValue<string>());
        Assert.Equal("resdb:///saved-crate", StateAsset(state, "mesh")["url"]!.GetValue<string>());
    }

    [Fact]
    public async Task ARecreatedComponentWithIdentityFieldsBindsByIdentityAfterAWorldReload()
    {
        static string World(params string[] first) => $$$"""
            {"schemaVersion":"1","ownership":{"key":"identity-recreate"},"slot":{"key":"root","name":"Rubble","parent":"Root"},
             "children":[
               {"slot":{"key":"materials","name":"Materials"},"components":[
                 {"key":"m1","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m2","type":"Test.Material","fields":{"Enabled":true}}]},
               {"slot":{"key":"rubble","name":"Rubble01"},"components":[
                 {"key":"r1","type":"Test.Renderer","fields":{"Label":"first","Materials":[{{{string.Join(",", first.Select(key => $"\"$ref:{key}\""))}}}]},"identityFields":["Label"]},
                 {"key":"r2","type":"Test.Renderer","fields":{"Label":"second","Materials":["$ref:m1"]},"identityFields":["Label"]},
                 {"key":"source","type":"Test.Source","fields":{"Target":"$ref:r1"}}]}]}
            """;
        var (client, service, state, shrunk) = await ApplyRubbleAsync("identity-recreate", World("m2"), World("m1", "m2"));

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        Assert.Equal("first", JsonNode.Parse(File.ReadAllText(state))!["components"]!["r1"]!["identityValues"]!["Label"]!.GetValue<string>());
        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "r1",
            new Dictionary<string, string[]> { ["r1"] = ["m2"], ["r2"] = ["m1"] });
    }

    [Fact]
    public async Task AMemberReferenceToARecreatedComponentMovesToTheReplacement()
    {
        static string World(params string[] materials) => RubbleWorld("member-recreate", materials).Replace(
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}},{"key":"probe","type":"Test.Source","fields":{"Target":"$member:renderer.Materials"}}""",
            StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("member-recreate", World("m1", "m2", "m3"), World("m1", "m2", "m3", "m4"));

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        var replacement = RubbleRenderers(client).Single();
        Assert.Equal(replacement.Members["Materials"].Id,
            Sources(client).Single(source => source.Id == StateId(state, "probe")).Members["Target"].TargetId);
        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

    [Fact]
    public async Task APruneAndARecreateOnOneSlotKeepTheIndexesBindable()
    {
        static string World(bool extra, params string[] materials) => RubbleWorld("prune-recreate", materials).Replace(
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
            (extra ? """{"key":"extra","type":"Test.Renderer","fields":{"Materials":["$ref:m4"]}},""" : "") +
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
            StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("prune-recreate", World(false, "m1", "m2", "m3"),
            World(true, "m1", "m2", "m3", "m4"));

        await service.ApplyAsync(shrunk, new ApplyOptions(state, Prune: true, ConfirmDeletes: true));

        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

    [Fact]
    public async Task ARecreateSetsInitialFieldsAgain()
    {
        static string World(params string[] materials) => RubbleWorld("initial-recreate", materials).Replace(
            """{"key":"renderer","type":"Test.Renderer","fields":{""",
            """{"key":"renderer","type":"Test.Renderer","initialFields":{"Enabled":true},"fields":{""", StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("initial-recreate", World("m1", "m2", "m3"),
            World("m1", "m2", "m3", "m4"));
        var original = RubbleRenderers(client).Single();
        // Runtime logic changed an initial-only member after the Component was created.
        original.Members["Enabled"] = original.Members["Enabled"] with { Value = JsonValue.Create(false) };

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        Assert.True(RubbleRenderers(client).Single().Members["Enabled"].Value!.GetValue<bool>());
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ShrinkingAListRecreates|FullyQualifiedName~ARecreateKeepsAnAssetUrl|FullyQualifiedName~ARecreatedComponentWithIdentityFields|FullyQualifiedName~AMemberReferenceToARecreated|FullyQualifiedName~APruneAndARecreateOnOneSlot|FullyQualifiedName~ARecreateSetsInitialFieldsAgain"
```

Expected: FAIL（置き換え元が削除されず、Slot に同じ型の Component が 2 つ残る、など）。

- [ ] **Step 3: 実装する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            var byKey = prepared.Components.Where(x => !string.IsNullOrWhiteSpace(x.Spec.Key) && x.Existing is not null)
                .ToDictionary(x => x.Spec.Key!, x => x, StringComparer.Ordinal);
            var slotsByKey = prepared.Nodes.ToDictionary(x => x.StableKey, StringComparer.Ordinal);
            foreach (var component in prepared.Components)
            {
```

置き換え後:

```csharp
            // A recreate's replacement is not a reference target until it is verified (I4).
            var byKey = prepared.Components.Where(x => !string.IsNullOrWhiteSpace(x.Spec.Key) && x.Existing is not null && !x.AwaitsVerification)
                .ToDictionary(x => x.Spec.Key!, x => x, StringComparer.Ordinal);
            var slotsByKey = prepared.Nodes.ToDictionary(x => x.StableKey, StringComparer.Ordinal);
            foreach (var component in prepared.Components)
            {
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    component.Id = created.Id;
                    component.ResolvedType = created.Type;
                    counts.ComponentsAdded++;
                }
                if (!string.IsNullOrWhiteSpace(component.Spec.Key)) byKey[component.Spec.Key!] = component;
```

置き換え後:

```csharp
                    component.Id = created.Id;
                    component.ResolvedType = created.Type;
                    counts.ComponentsAdded++;
                    component.ReplacementCreated = component.SupersededId is not null;
                }
                if (!string.IsNullOrWhiteSpace(component.Spec.Key) && !component.AwaitsVerification) byKey[component.Spec.Key!] = component;
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    component.Existing is null ? "created Component" : "resolved Component"));
            }

            foreach (var component in prepared.Components)
            {
```

置き換え後:

```csharp
                    component.Existing is null ? "created Component" : "resolved Component"));
            }

            var recreates = prepared.Components.Where(component => component.SupersededId is not null).ToArray();
            await VerifyReplacementsAsync(prepared, recreates, byKey, slotsByKey, assetUrls, cancellationToken);

            foreach (var component in prepared.Components)
            {
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
                    changed.Count == 0 ? "no field changes" : $"updated {changed.Count} field(s)"));
            }

```

追加する内容:

```csharp
            // Every managed reference now points at the replacements (I4). Remove each replaced Component, then save the
            // Slot's final indexes and clear the recreate in one checkpoint.
            foreach (var component in recreates)
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (component.Superseded is not null)
                {
                    await client.RemoveComponentAsync(component.Superseded.Id, cancellationToken);
                    counts.ComponentsDeleted++;
                    component.Superseded = null;
                }
                await SaveSlotIndexesAsync(prepared, component.Node.StableKey, component.Node.Id!, cancellationToken);
                component.SupersededId = null;
                prepared.State.Components[component.StableKey] = prepared.State.Components[component.StableKey] with { SupersededId = null };
                Checkpoint(prepared);
                options.Progress?.Invoke(new ApplyProgress("fields", completed, total, component.Path,
                    "removed the Component that the recreate replaced"));
            }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
    // A relocated Component is observed through the live Component it replaces.
```

置き換え後:

```csharp
    // A relocated or recreated Component is observed through the live Component it replaces.
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            var live = component.Existing ?? component.RelocationSource;
```

置き換え後:

```csharp
            var live = component.Existing ?? component.RelocationSource ?? component.Superseded;
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    // Removing a Component moves the ones after it, and after a world reload a key without identity values is bound by
```

追加する内容:

```csharp
    // Write each replacement's declared fields before any managed reference moves to it (I4).
    private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates,
        Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey,
        IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)
    {
        // A recreate whose replaced Component is already gone has nothing left to verify or undo.
        foreach (var component in recreates.Where(component => component.AwaitsVerification))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!string.IsNullOrWhiteSpace(component.Spec.Key)) byKey[component.Spec.Key!] = component;
            var fields = await ResolveFieldsAsync(MergeCreateFields(component.Spec), byKey, slotsByKey, assetUrls, cancellationToken);
            var unwritten = fields.Where(field => component.AppliedOnCreate is null ||
                                                  !component.AppliedOnCreate.TryGetValue(field.Key, out var applied) || applied != field.Value)
                .Where(field => component.Existing?.Members is null ||
                                !component.Existing.Members.TryGetValue(field.Key, out var current) ||
                                !MemberMatchesRaw(current, field.Value)).ToDictionary(StringComparer.Ordinal);
            if (unwritten.Count > 0)
            {
                ForgetComponentAssetEvidence(prepared, component.StableKey, unwritten.Keys);
                Checkpoint(prepared);
                await client.SetComponentMembersAsync(component.Id!, component.ResolvedType ?? component.Spec.Type, unwritten, cancellationToken);
            }
            // The fields phase must not write these again.
            component.AppliedOnCreate = fields;
        }
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        public ApplyStateComponent? StateBeforeRecreate { get; set; }
```

追加する内容:

```csharp
        // True once this apply has created the replacement.
        public bool ReplacementCreated { get; set; }
        // While the replaced Component is still on the Slot, its replacement is not a reference target until verified (I4).
        public bool AwaitsVerification => SupersededId is not null && Superseded is not null;
```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ShrinkingAListRecreates|FullyQualifiedName~ARecreateKeepsAnAssetUrl|FullyQualifiedName~ARecreatedComponentWithIdentityFields|FullyQualifiedName~AMemberReferenceToARecreated|FullyQualifiedName~APruneAndARecreateOnOneSlot|FullyQualifiedName~ARecreateSetsInitialFieldsAgain"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Recreate a Component with a shrinking list within one apply" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 7 件とも PASS、全件も PASS（`RLoop.Tests` 345 件）。

### Task B4: 検証の失敗と取り消し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`VerifyReplacementsAsync` とその呼び出し）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B3 の `VerifyReplacementsAsync`
- Produces: `VerifyReplacementsAsync` の引数に `ApplyCounts counts` を追加。宣言より長いリストが残れば、失敗した key と、この apply で作った置き換え先を取り消して `APPLY_LIST_SHRINK_NOT_CONVERGED`（7）を投げる。context は `failures`（key・メンバー・宣言と実機の要素数）と `undone`。

- [ ] **Step 1: テストを書く**

1 つ目は、同じ apply で作った Component（`watcher`）が、取り消した置き換え先を指さないこと（I4）も確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Fact]
    public async Task AReplacementThatTheRuntimeRefillsIsUndone()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("refilled",
            RubbleWorld("refilled", ["m1", "m2", "m3"], "rubble", watcher: true));
        var original = RubbleRenderers(client).Single().Id;
        client.RefillListsTo = 4;

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Equal(ExitCodes.OperationFailed, error.ExitCode);
        Assert.Equal(["renderer"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        var renderer = Assert.Single(RubbleRenderers(client));
        Assert.Equal(original, renderer.Id);
        Assert.Equal(4, renderer.Members["Materials"].Elements!.Count);
        Assert.Equal(original, StateId(state, "renderer"));
        Assert.DoesNotContain("supersededId", File.ReadAllText(state));
        Assert.Equal(original, Sources(client).Single(source => source.Id == StateId(state, "source")).Members["Target"].TargetId);
        // I4: the watcher created in the same apply never pointed at the removed replacement.
        Assert.All(Sources(client), source => Assert.True(source.Members["Target"].TargetId is null || source.Members["Target"].TargetId == original));
        AssertSavedIndexesMatchLayout(client, state);

        client.RefillListsTo = null;
        await service.ApplyAsync(shrunk, new ApplyOptions(state));
        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

    [Fact]
    public async Task EveryReplacementThisApplyCreatedIsUndoneWhenOneDoesNotConverge()
    {
        var first = ReloadDocument("undo-all", TwoRendererWorld("undo-all", ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3"]));
        var shrinkBoth = ReloadDocument("undo-all-both", TwoRendererWorld("undo-all", ["m1", "m2", "m3"], ["m1", "m2"]));
        var client = new FakeResoniteClient(first);
        var service = new WorldService(client);
        var state = Path.Combine(_root, "undo-all.state.json");
        await service.ApplyAsync(first, new ApplyOptions(state));
        var originals = RubbleRenderers(client).Select(component => component.Id).ToArray();
        client.RefillListsTo = 3; // r1's replacement keeps 3 as declared, r2's replacement cannot shrink to 2

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Equal(["r1", "r2"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        Assert.Equal(originals, RubbleRenderers(client).Select(component => component.Id));
        Assert.Equal(originals, new[] { StateId(state, "r1"), StateId(state, "r2") });
        Assert.DoesNotContain("supersededId", File.ReadAllText(state));
        AssertSavedIndexesMatchLayout(client, state);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AReplacementThatTheRuntimeRefillsIsUndone|FullyQualifiedName~EveryReplacementThisApplyCreatedIsUndone"
```

Expected: FAIL（`APPLY_LIST_SHRINK_NOT_CONVERGED` が出ない）。

- [ ] **Step 3: 実装する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
            await VerifyReplacementsAsync(prepared, recreates, byKey, slotsByKey, assetUrls, cancellationToken);
```

置き換え後:

```csharp
            await VerifyReplacementsAsync(prepared, recreates, byKey, slotsByKey, assetUrls, counts, cancellationToken);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
    // Write each replacement's declared fields before any managed reference moves to it (I4).
    private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates,
        Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey,
        IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)
    {
        // A recreate whose replaced Component is already gone has nothing left to verify or undo.
        foreach (var component in recreates.Where(component => component.AwaitsVerification))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!string.IsNullOrWhiteSpace(component.Spec.Key)) byKey[component.Spec.Key!] = component;
            var fields = await ResolveFieldsAsync(MergeCreateFields(component.Spec), byKey, slotsByKey, assetUrls, cancellationToken);
            var unwritten = fields.Where(field => component.AppliedOnCreate is null ||
                                                  !component.AppliedOnCreate.TryGetValue(field.Key, out var applied) || applied != field.Value)
                .Where(field => component.Existing?.Members is null ||
                                !component.Existing.Members.TryGetValue(field.Key, out var current) ||
                                !MemberMatchesRaw(current, field.Value)).ToDictionary(StringComparer.Ordinal);
            if (unwritten.Count > 0)
            {
                ForgetComponentAssetEvidence(prepared, component.StableKey, unwritten.Keys);
                Checkpoint(prepared);
                await client.SetComponentMembersAsync(component.Id!, component.ResolvedType ?? component.Spec.Type, unwritten, cancellationToken);
            }
            // The fields phase must not write these again.
            component.AppliedOnCreate = fields;
        }
    }

```

置き換え後:

```csharp
    // Write each replacement's declared fields and read it back before any managed reference moves to it (I4). Runtime
    // logic that refills a list would make every apply recreate the Component again, so a list still longer than declared
    // undoes the replacements that nothing can reference yet and stops.
    private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates,
        Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey,
        IReadOnlyDictionary<string, string> assetUrls, ApplyCounts counts, CancellationToken cancellationToken)
    {
        var failures = new List<(ComponentRuntime Component, string Member, int Declared, int Observed)>();
        // A recreate whose replaced Component is already gone has nothing left to verify or undo.
        foreach (var component in recreates.Where(component => component.AwaitsVerification))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!string.IsNullOrWhiteSpace(component.Spec.Key)) byKey[component.Spec.Key!] = component;
            var fields = await ResolveFieldsAsync(MergeCreateFields(component.Spec), byKey, slotsByKey, assetUrls, cancellationToken);
            var unwritten = fields.Where(field => component.AppliedOnCreate is null ||
                                                  !component.AppliedOnCreate.TryGetValue(field.Key, out var applied) || applied != field.Value)
                .Where(field => component.Existing?.Members is null ||
                                !component.Existing.Members.TryGetValue(field.Key, out var current) ||
                                !MemberMatchesRaw(current, field.Value)).ToDictionary(StringComparer.Ordinal);
            if (unwritten.Count > 0)
            {
                ForgetComponentAssetEvidence(prepared, component.StableKey, unwritten.Keys);
                Checkpoint(prepared);
                await client.SetComponentMembersAsync(component.Id!, component.ResolvedType ?? component.Spec.Type, unwritten, cancellationToken);
            }
            // The fields phase must not write these again.
            component.AppliedOnCreate = fields;
            var replacement = await client.GetComponentAsync(component.Id!, cancellationToken);
            foreach (var field in component.Spec.Fields ?? new Dictionary<string, JsonElement>())
                if (field.Value.ValueKind == JsonValueKind.Array &&
                    replacement.Members.GetValueOrDefault(field.Key) is { Kind: "list" } list &&
                    (list.Elements?.Count ?? 0) > field.Value.GetArrayLength())
                    failures.Add((component, field.Key, field.Value.GetArrayLength(), list.Elements!.Count));
        }
        if (failures.Count == 0) return;

        // Nothing references a replacement this apply created, so removing it cannot leave a dangling reference. A resumed
        // replacement that passed stays, because an earlier apply may already have moved references to it.
        var failed = failures.Select(failure => failure.Component).ToHashSet();
        var undone = recreates.Where(component => component.AwaitsVerification &&
                                                  (component.ReplacementCreated || failed.Contains(component))).ToArray();
        foreach (var component in undone)
        {
            cancellationToken.ThrowIfCancellationRequested();
            await client.RemoveComponentAsync(component.Id!, cancellationToken);
            counts.ComponentsDeleted++;
            var restored = component.StateBeforeRecreate ??
                prepared.State.Components[component.StableKey] with { AssetFields = new Dictionary<string, JsonElement>() };
            prepared.State.Components[component.StableKey] = restored with { Id = component.SupersededId!, SupersededId = null };
        }
        foreach (var node in undone.Select(component => component.Node).Distinct())
            await SaveSlotIndexesAsync(prepared, node.StableKey, node.Id!, cancellationToken);
        Checkpoint(prepared);
        throw new RLoopException("APPLY_LIST_SHRINK_NOT_CONVERGED",
            "The runtime kept a list longer than declared on the replacement Component, so recreating it cannot converge. The replacement was removed and the original Component is unchanged.",
            ExitCodes.OperationFailed, new Dictionary<string, object?>
            {
                ["failures"] = failures.Select(failure => new
                {
                    componentKey = failure.Component.StableKey, member = failure.Member,
                    declared = failure.Declared, observed = failure.Observed
                }).ToArray(),
                ["undone"] = undone.Select(component => component.StableKey).ToArray()
            },
            ["Declare the list length that the runtime keeps, or find what refills the list.",
             "Re-run apply after changing the declaration. The undone keys have no recreate in progress."]);
    }

```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AReplacementThatTheRuntimeRefillsIsUndone|FullyQualifiedName~EveryReplacementThisApplyCreatedIsUndone"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Undo replacements whose list does not converge" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 2 件とも PASS、全件も PASS（`RLoop.Tests` 347 件）。

### Task B5: 中断した作り直しの再開と停止

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`PrepareAsync`、`BuildComponentPlans`、`RecreatePlanReason`、新しい `ThrowIfRecreateInterruptedAcrossSessions`・`ValidateInterruptedRecreates`・`RecreateInterrupted`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B2〜B4
- Produces: `ComponentRuntime.Resumed`。`private static string RecreatePlanReason(ComponentRuntime component)`（再開の理由を含む）。`APPLY_RECREATE_INTERRUPTED`（6）。context は `reason`・`stateFile`・`componentKey`・`slotKey`・`slotPath`・`type`・`supersededId`・`savedId`・`candidates`（`id` と、list メンバーごとの要素数 `lists`）。

- [ ] **Step 1: テストを書く**

Review Focus の 3 を含む。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Theory]
    [InlineData("undeclared")]
    [InlineData("moved")]
    public async Task ARecreateInterruptedBeforeTheKeyLeavesItsSlotStops(string change)
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("leaves-" + change, RubbleWorld("leaves-" + change, "m1", "m2", "m3"));
        client.FailOnWrite = 1; // creating the replacement fails after state saved supersededId
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        var changed = ReloadDocument("leaves-" + change + "-changed", change == "undeclared"
            ? RubbleWorld("leaves-" + change, [], rendererSlot: null)
            : RubbleWorld("leaves-" + change, ["m1", "m2", "m3"], rendererSlot: "elsewhere"));
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(changed, new ApplyOptions(state)));

        Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
        Assert.Equal("key-not-declared", error.Context["reason"]);
        Assert.Equal("renderer", error.Context["componentKey"]);
        Assert.Equal(0, client.Writes);
    }

    [Theory]
    [InlineData("create")]
    [InlineData("remove")]
    public async Task APlanDuringAnInterruptedRecreateExplainsHowItResumes(string failedStep)
    {
        var name = "resume-plan-" + failedStep;
        var (client, service, state, shrunk) = await ApplyRubbleAsync(name, RubbleWorld(name, "m1", "m2", "m3"));
        var original = RubbleRenderers(client).Single().Id;
        if (failedStep == "create") client.FailOnWrite = 1;
        else client.FailRemovingComponent = original;
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        client.FailRemovingComponent = null;
        client.ResetWriteCounts();
        var checkpoint = File.ReadAllBytes(state);

        var plan = await service.PlanApplyAsync(shrunk, new ApplyOptions(state));

        var recreate = Assert.Single(plan.Operations, operation => operation.Action == "recreate");
        Assert.StartsWith("resumes an interrupted recreate:", recreate.Reason);
        Assert.Contains(failedStep == "create" ? "creates the replacement" : $"removes the replaced Component '{original}'", recreate.Reason);
        Assert.Equal(checkpoint, File.ReadAllBytes(state));
        Assert.Equal(0, client.Writes);
    }

    [Fact]
    public async Task AResumedReplacementThatPassesStaysWhenAnotherRecreateIsUndone()
    {
        var first = ReloadDocument("resumed-stays", TwoRendererWorld("resumed-stays", ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3"]));
        var shrinkFirst = ReloadDocument("resumed-stays-first", TwoRendererWorld("resumed-stays", ["m1", "m2", "m3"], ["m1", "m2", "m3"]));
        var shrinkBoth = ReloadDocument("resumed-stays-both", TwoRendererWorld("resumed-stays", ["m1", "m2", "m3"], ["m1", "m2"]));
        var client = new FakeResoniteClient(first);
        var service = new WorldService(client);
        var state = Path.Combine(_root, "resumed-stays.state.json");
        await service.ApplyAsync(first, new ApplyOptions(state));
        var r1 = StateId(state, "r1");
        var r2 = StateId(state, "r2");
        client.FailRemovingComponent = r1; // r1's recreate stops after the references moved to its replacement
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrinkFirst, new ApplyOptions(state)));
        client.FailRemovingComponent = null;
        var replacement = StateId(state, "r1");
        Assert.NotEqual(r1, replacement);
        client.RefillListsTo = 3; // r1's replacement keeps 3 as declared, r2's replacement cannot shrink to 2

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Equal(["r2"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        var checkpoint = JsonNode.Parse(File.ReadAllText(state))!;
        Assert.Equal(replacement, checkpoint["components"]!["r1"]!["id"]!.GetValue<string>());
        Assert.Equal(r1, checkpoint["components"]!["r1"]!["supersededId"]!.GetValue<string>());
        Assert.Equal(r2, checkpoint["components"]!["r2"]!["id"]!.GetValue<string>());
        Assert.Null(checkpoint["components"]!["r2"]!["supersededId"]);
        Assert.Equal(new[] { r1, r2, replacement }.Order(StringComparer.Ordinal),
            RubbleRenderers(client).Select(component => component.Id).Order(StringComparer.Ordinal));

        client.RefillListsTo = null;
        await service.ApplyAsync(shrinkFirst, new ApplyOptions(state));
        await AssertListShrinkConvergedAsync(client, service, shrinkFirst, state, "r1",
            new Dictionary<string, string[]> { ["r1"] = ["m1", "m2", "m3"], ["r2"] = ["m1", "m2", "m3"] });
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedBeforeTheKeyLeavesItsSlot|FullyQualifiedName~APlanDuringAnInterruptedRecreate|FullyQualifiedName~AResumedReplacementThatPassesStays"
```

Expected: FAIL（`APPLY_RECREATE_INTERRUPTED` が出ない、再開の理由が出ない、など）。

- [ ] **Step 3: 実装する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                ComponentSummary? superseded = null;
                var existing = relocating || newManagedComponent ? null :
                    MatchComponent(node.Existing?.Components ?? [], spec.Type, ordinal, stateComponent, prepared.SameSession,
                        topologyTargets);
                var recreateReason = existing is null ? null : ListShrinkReason(spec, existing);
```

置き換え後:

```csharp
                // An interrupted recreate resumes by ID only: never by type or position (I2, I3).
                var resumed = !relocating && !string.IsNullOrEmpty(stateComponent?.SupersededId);
                ComponentSummary? superseded = null;
                ComponentSummary? existing;
                if (resumed)
                {
                    var components = node.Existing?.Components ?? [];
                    superseded = components.FirstOrDefault(candidate => candidate.Id == stateComponent!.SupersededId);
                    existing = string.IsNullOrEmpty(stateComponent!.Id) || stateComponent.Id == stateComponent.SupersededId ? null :
                        components.FirstOrDefault(candidate => candidate.Id == stateComponent.Id);
                }
                else
                {
                    existing = relocating || newManagedComponent ? null :
                        MatchComponent(node.Existing?.Components ?? [], spec.Type, ordinal, stateComponent, prepared.SameSession,
                            topologyTargets);
                }
                var recreateReason = resumed || existing is null ? null : ListShrinkReason(spec, existing);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    SupersededId = superseded?.Id,
                    RecreateReason = recreateReason,
```

置き換え後:

```csharp
                    SupersededId = resumed ? stateComponent!.SupersededId : superseded?.Id,
                    RecreateReason = recreateReason,
                    Resumed = resumed,
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                : component.SupersededId is not null ? component.RecreateReason!
```

置き換え後:

```csharp
                : component.SupersededId is not null ? RecreatePlanReason(component)
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static ApplyMemberDiff ListDiff(string member, MemberValue current, string desiredRaw)
```

追加する内容:

```csharp
    private static string RecreatePlanReason(ComponentRuntime component) => component.RecreateReason ??
        (component.Existing, component.Superseded) switch
        {
            (null, null) => "resumes an interrupted recreate: the replaced Component is already removed; apply creates the replacement",
            (null, { } replaced) => $"resumes an interrupted recreate: creates the replacement, then removes the replaced Component '{replaced.Id}'",
            (_, null) => "resumes an interrupted recreate: the replaced Component is already removed; apply saves the final Component indexes",
            (_, { } replaced) => $"resumes an interrupted recreate: removes the replaced Component '{replaced.Id}' after managed references point at the replacement"
        };

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
        BuildAssetPlans(prepared);
        BuildComponentPlans(prepared);
        BuildDeletionPlans(prepared);
        ValidateSlotOwnership(prepared);
```

置き換え後:

```csharp
        BuildAssetPlans(prepared);
        ThrowIfRecreateInterruptedAcrossSessions(prepared);
        BuildComponentPlans(prepared);
        BuildDeletionPlans(prepared);
        ValidateInterruptedRecreates(prepared);
        ValidateSlotOwnership(prepared);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static void ValidateSlotOwnership(PreparedApply prepared)
```

追加する内容:

```csharp
    // An interrupted recreate resumes only by ID. In another session those IDs no longer name the replaced Component and
    // its replacement, so stop before mutation (I2).
    private static void ThrowIfRecreateInterruptedAcrossSessions(PreparedApply prepared)
    {
        if (prepared.SameSession) return;
        foreach (var (key, saved) in prepared.State.Components.Where(pair => !string.IsNullOrEmpty(pair.Value.SupersededId)))
            throw RecreateInterrupted(prepared, "session-changed", key, saved);
    }

    // I2: resume only while the document declares the key on the same Slot. I3: create a lost replacement again only
    // when no same-type Component on the Slot could be it; never pick one by position.
    private static void ValidateInterruptedRecreates(PreparedApply prepared)
    {
        var declared = prepared.Components.ToDictionary(component => component.StableKey, StringComparer.Ordinal);
        foreach (var (key, saved) in prepared.State.Components.Where(pair => !string.IsNullOrEmpty(pair.Value.SupersededId)))
            if (!declared.TryGetValue(key, out var component) || component.Node.StableKey != saved.SlotKey)
                throw RecreateInterrupted(prepared, "key-not-declared", key, saved);
        var owned = prepared.Components
            .SelectMany(component => new[] { component.Existing?.Id, component.RelocationSource?.Id, component.Superseded?.Id })
            .Concat(prepared.Deletions.Where(deletion => deletion.Kind == "component").Select(deletion => deletion.Id))
            .OfType<string>().ToHashSet(StringComparer.Ordinal);
        foreach (var component in prepared.Components.Where(component => component.Resumed && component.Existing is null))
        {
            var unowned = (component.Node.Existing?.Components ?? [])
                .Where(candidate => TypeNamesEquivalent(candidate.Type, component.Spec.Type) && !owned.Contains(candidate.Id)).ToArray();
            if (unowned.Length > 0)
                throw RecreateInterrupted(prepared, "replacement-unverified", component.StableKey,
                    prepared.State.Components[component.StableKey], unowned);
        }
    }

    private static RLoopException RecreateInterrupted(PreparedApply prepared, string reason, string key, ApplyStateComponent saved,
        IReadOnlyList<ComponentSummary>? candidates = null)
    {
        candidates ??= (prepared.Nodes.FirstOrDefault(node => node.StableKey == saved.SlotKey)?.Existing?.Components ?? [])
            .Where(component => TypeNamesEquivalent(component.Type, saved.Type)).ToArray();
        var (message, suggestions) = reason switch
        {
            "session-changed" => (
                $"A list-shrink recreate of '{key}' was interrupted and the world session changed, so the replaced Component and its replacement can no longer be told apart by ID. No mutations were performed.",
                new[] { $"Keep exactly one same-type Component for the key, preferably removing the one whose list is longer than declared, with 'resoloop component remove ID --yes'. Then delete supersededId from components.{key} in the state file and re-run apply." }),
            "key-not-declared" => (
                $"A list-shrink recreate of '{key}' was interrupted, and the document no longer declares the key on its Slot. No mutations were performed.",
                new[] { "Declare the key again on the same Slot and re-run apply in this session to finish the recreate.",
                        $"Or keep exactly one same-type Component for the key, remove the other with 'resoloop component remove ID --yes', and delete supersededId from components.{key} in the state file." }),
            _ => (
                $"A list-shrink recreate of '{key}' was interrupted before its replacement ID was saved, and the Slot holds a same-type Component that no key owns. No mutations were performed.",
                new[] { "If a candidate's lists match the declaration, it is most likely the replacement that the interrupted apply created. Remove it with 'resoloop component remove ID --yes' and re-run apply; apply creates the replacement again.",
                        $"If every candidate is unrelated content, set components.{key}.id back to its supersededId, delete supersededId, and re-run apply to start the recreate again." })
        };
        return new RLoopException("APPLY_RECREATE_INTERRUPTED", message, ExitCodes.ValidationFailed, new Dictionary<string, object?>
        {
            ["reason"] = reason,
            ["stateFile"] = prepared.StatePath,
            ["componentKey"] = key,
            ["slotKey"] = saved.SlotKey,
            ["slotPath"] = prepared.State.Slots.GetValueOrDefault(saved.SlotKey)?.Path,
            ["type"] = saved.Type,
            ["supersededId"] = saved.SupersededId,
            ["savedId"] = saved.Id,
            ["candidates"] = candidates.Select(component => new
            {
                id = component.Id,
                lists = (component.Members ?? new Dictionary<string, MemberValue>()).Where(member => member.Value.Kind == "list")
                    .ToDictionary(member => member.Key, member => member.Value.Elements?.Count ?? 0, StringComparer.Ordinal)
            }).ToArray()
        }, suggestions);
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        public string? RecreateReason { get; set; }
```

追加する内容:

```csharp
        // True when the recreate was already in progress in state, false when this plan starts it.
        public bool Resumed { get; set; }
```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedBeforeTheKeyLeavesItsSlot|FullyQualifiedName~APlanDuringAnInterruptedRecreate|FullyQualifiedName~AResumedReplacementThatPassesStays"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Resume an interrupted recreate by ID in the same session, and stop otherwise" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 5 件とも PASS、全件も PASS（`RLoop.Tests` 352 件）。

### Task B6: 置き換え元への参照の検査

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`PrepareAsync`、新しい `ValidateRecreateReferences`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B5 の `RecreatePlanReason`
- Produces: `APPLY_LIST_SHRINK_REFERENCED`（6）。context は `stateFile`・`recreates`（`key`・`id`・`reason`）・`references`（`componentKey`・`targetId`・`referencedBy`・`type`・`member`・`slotId`・`slotPath`）。

- [ ] **Step 1: テストを書く**

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Fact]
    public async Task AnUnmanagedReferenceToTheReplacedComponentStopsBeforeMutation()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("referenced", RubbleWorld("referenced", "m1", "m2", "m3"));
        var rubble = AllSlots(client.Root).Single(slot => slot.Name == "Rubble01");
        var unmanaged = await client.AddComponentAsync(rubble.Id, "Test.Source",
            new Dictionary<string, string> { ["Target"] = RubbleRenderers(client).Single().Id });
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_REFERENCED", error.Code);
        Assert.Equal(ExitCodes.ValidationFailed, error.ExitCode);
        var reference = Assert.Single(JsonSerializer.SerializeToNode(error.Context["references"])!.AsArray())!;
        Assert.Equal(unmanaged.Id, reference["referencedBy"]!.GetValue<string>());
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AnUnmanagedReferenceToTheReplacedComponent"
```

Expected: FAIL（停止せずに作り直す）。

- [ ] **Step 3: 実装する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        ValidateComponentOwnership(prepared);
```

追加する内容:

```csharp
        ValidateRecreateReferences(prepared);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static void ValidateSlotOwnership(PreparedApply prepared)
```

追加する内容:

```csharp
    // Recreating gives the Component and its members new IDs. Apply re-points only the declared reference fields of managed
    // Components, so stop before mutation when anything else in the snapshots that apply read points at a replaced Component.
    private static void ValidateRecreateReferences(PreparedApply prepared)
    {
        var recreates = prepared.Components.Where(component => component.Superseded is not null).ToArray();
        if (recreates.Length == 0) return;
        var targets = new Dictionary<string, ComponentRuntime>(StringComparer.Ordinal);
        void CollectIds(MemberValue member, ComponentRuntime owner)
        {
            if (!string.IsNullOrWhiteSpace(member.Id)) targets[member.Id] = owner;
            foreach (var child in member.Members?.Values ?? []) CollectIds(child, owner);
            foreach (var element in member.Elements ?? []) CollectIds(element, owner);
        }
        foreach (var component in recreates)
        {
            targets[component.Superseded!.Id] = component;
            foreach (var member in component.Superseded.Members?.Values ?? []) CollectIds(member, component);
        }
        static IEnumerable<string> ReferenceTargets(MemberValue member) =>
            (member.Kind == "reference" && member.TargetId is { } target ? [target] : Enumerable.Empty<string>())
                .Concat((member.Members?.Values ?? []).SelectMany(ReferenceTargets))
                .Concat((member.Elements ?? []).SelectMany(ReferenceTargets));
        var removed = recreates.Select(component => component.Superseded!.Id)
            .Concat(prepared.Components.Where(component => component.RelocationSource is not null).Select(component => component.RelocationSource!.Id))
            .ToHashSet(StringComparer.Ordinal);
        var managed = prepared.Components.Where(component => component.Existing is not null)
            .ToDictionary(component => component.Existing!.Id, StringComparer.Ordinal);
        var references = new List<object>();
        void Check(SlotInfo slot, string ownerId, string ownerType, IReadOnlyDictionary<string, MemberValue>? members)
        {
            foreach (var (name, member) in members ?? new Dictionary<string, MemberValue>())
                foreach (var target in ReferenceTargets(member).Where(targets.ContainsKey))
                {
                    if (managed.TryGetValue(ownerId, out var owner) && owner.Spec.Fields?.TryGetValue(name, out var declared) == true &&
                        ContainsWorldReference(declared)) continue;
                    references.Add(new { componentKey = targets[target].StableKey, targetId = target, referencedBy = ownerId,
                        type = ownerType, member = name, slotId = slot.Id, slotPath = slot.Path });
                }
        }
        foreach (var slot in prepared.SnapshotSlots)
        {
            Check(slot, slot.Id, "[FrooxEngine]FrooxEngine.Slot", slot.Members);
            foreach (var component in slot.Components.Where(component => !removed.Contains(component.Id)))
                Check(slot, component.Id, component.Type, component.Members);
        }
        if (references.Count > 0)
            throw new RLoopException("APPLY_LIST_SHRINK_REFERENCED",
                "A declared list member must shrink, which requires recreating its Component, but something other than a declared managed reference points at the Component or its members. No mutations were performed.",
                ExitCodes.ValidationFailed, new Dictionary<string, object?>
                {
                    ["stateFile"] = prepared.StatePath,
                    ["recreates"] = recreates.Select(component => new
                        { key = component.StableKey, id = component.Superseded!.Id, reason = RecreatePlanReason(component) }).ToArray(),
                    ["references"] = references
                },
                ["Declare the referencing member as a managed field with a $component/$member selector so apply can re-point it, or remove the reference.",
                 "Only the snapshots this apply read were checked. Inspect other references to the Component before applying."]);
    }

```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AnUnmanagedReferenceToTheReplacedComponent"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Stop a recreate when something unmanaged references the replaced Component" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: PASS、全件も PASS（`RLoop.Tests` 353 件）。

### Task B7: 書き込みの位置ごとの網羅テスト

**Files:**
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B1 の `ApplyScenarioAsync`・`AssertListShrinkConvergedAsync`、Task A1 の `InterruptedAsync`

- [ ] **Step 1: 網羅テストを書く**

シナリオは 2 つ。`one-recreate`（S1）は Component を 1 つ作り直し、それを管理 Component が参照する。`shared-slot`（S2）は同じ Slot で 2 つを作り直し、その Slot から別の Component を移動し、文書から外した key を残し、同じ apply で後から作る material を参照する。書き込みの位置 k を 1 から最後まで、反映前の失敗と、反映後の応答の喪失で止め、同じセッションでの再開と、再読込の後の停止を確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    // Stops the shrinking apply at each write in turn, before the write lands or after it lands with its response lost.
    // The next apply in the same session must converge, or stop on replacement-unverified until the documented recovery.
    [Theory]
    [InlineData("one-recreate", false)]
    [InlineData("one-recreate", true)]
    [InlineData("shared-slot", false)]
    [InlineData("shared-slot", true)]
    public async Task ARecreateInterruptedAtAnyWriteConvergesInTheSameSession(string scenario, bool responseLost)
    {
        for (var write = 1; ; write++)
        {
            var (client, service, state, shrunk, referenced, expected) = await ApplyScenarioAsync($"{scenario}-resume-{responseLost}-{write}", scenario);
            if (responseLost) client.LoseResponseOnWrite = write;
            else client.FailOnWrite = write;

            var interrupted = await InterruptedAsync(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
            client.LoseResponseOnWrite = null;
            client.FailOnWrite = null;
            try
            {
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
            }
            catch (RLoopException error) when (error.Code == "APPLY_RECREATE_INTERRUPTED" && Equals(error.Context["reason"], "replacement-unverified"))
            {
                Assert.True(responseLost, $"write {write}: only a lost create response can leave an unverified replacement.");
                // The documented recovery: the candidate is the replacement whose create response was lost.
                foreach (var candidate in JsonSerializer.SerializeToNode(error.Context["candidates"])!.AsArray())
                    await client.RemoveComponentAsync(candidate!["id"]!.GetValue<string>());
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
            }

            await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"write {write}: ");
            if (!interrupted) break;
        }
    }

    // A world reload while a recreate is in progress must stop before any write; otherwise the apply converges.
    [Theory]
    [InlineData("one-recreate", false)]
    [InlineData("one-recreate", true)]
    [InlineData("shared-slot", false)]
    [InlineData("shared-slot", true)]
    public async Task AWorldReloadDuringARecreateStopsBeforeAnyWrite(string scenario, bool responseLost)
    {
        for (var write = 1; ; write++)
        {
            var (client, service, state, shrunk, referenced, expected) = await ApplyScenarioAsync($"{scenario}-reload-{responseLost}-{write}", scenario);
            if (responseLost) client.LoseResponseOnWrite = write;
            else client.FailOnWrite = write;

            var interrupted = await InterruptedAsync(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
            client.LoseResponseOnWrite = null;
            client.FailOnWrite = null;
            var inProgress = File.ReadAllText(state).Contains("\"supersededId\"", StringComparison.Ordinal);
            client.ReloadWorld("session-reloaded");
            client.ResetWriteCounts();

            if (inProgress)
            {
                var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
                Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
                Assert.Equal("session-changed", error.Context["reason"]);
                Assert.True(client.Writes == 0, $"write {write}: the stopped apply wrote {client.Writes} time(s).");
            }
            else
            {
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
                await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"write {write}: ");
            }
            if (!interrupted) break;
        }
    }

```

- [ ] **Step 2: 成功することを確かめてコミットする**

この時点では実装がそろっているので、最初から PASS する。失敗した場合は、失敗したメッセージの `write k` が示す書き込みの位置から原因を調べる（設計の見直しが要るかは、Spec の 10.3 のレビューの規則に従って判断する）。

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedAtAnyWriteConverges|FullyQualifiedName~AWorldReloadDuringARecreateStops"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit -m "test: interrupt a list-shrink recreate at every write" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 8 件とも PASS、全件も PASS（`RLoop.Tests` 361 件）。

### Task B8: 文書、修正前との比較、コミットの整理、fork の PR B

**Files:**
- Modify: `README.md`、`README_JA.md`、`README-DETAILS.md`、`docs/DECLARATIVE.md`、`skills/codex/resonite-build/SKILL.md`、`skills/codex/resonite-debug/SKILL.md`

- [ ] **Step 1: 文書を更新する**

上流の `AGENTS.md` は、CLI の挙動を変えたら README と `skills/codex/*/SKILL.md` も更新するよう求めている。

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
`initialFields`へ置くと、新規作成時だけ初期化され、adopt・再applyでは上書きされません。
```

追加する内容:

```markdown
ただし、list memberの宣言要素数が実機より少ないためにComponentを作り直すapply（planの`recreate`）では、新しいComponentへ`initialFields`を設定し直すため値は初期値に戻り、宣言していないmemberも型の既定値に戻ります。
```

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
旧driverがtargetを占有する場合は明示pruneの計画を確認してください。自動でpruneを有効化することはありません。
```

追加する内容:

```markdown

ResoniteLinkはlistの要素を削除できません（短いlistを送っても先頭の要素が置き換わるだけです）。`fields`で宣言したlist memberの要素数が実機より少ない既存Componentは、planで`recreate`となります。applyは同じSlotに新しいComponentを作って宣言したfieldを書き、listを読み直して確かめてから、管理Componentの参照を張り替え、旧Componentを削除します。Componentの移動と同じく、この削除に`--prune`は不要です。新しいComponentでは`initialFields`と宣言していないmemberが既定値に戻ります。次の場合は停止します。

- `APPLY_LIST_SHRINK_REFERENCED`（変更前）: applyが読んだ範囲で、管理Componentの宣言済み参照以外のものが旧Componentやそのmemberを参照しています。参照元を`$component:`などで管理対象として宣言するか、参照を外してください。
- `APPLY_LIST_SHRINK_NOT_CONVERGED`（検証時）: 新しいComponentでもlistが宣言より長いまま残りました。applyは新しいComponentを削除してstateを元に戻します。runtimeが保つ要素数を宣言するか、listを詰め直す原因を確認してください。
- `APPLY_RECREATE_INTERRUPTED`（変更前）: 作り直しが途中で止まり、自動では再開できません。`reason`が`session-changed`なら、ワールドの再読込などでIDが変わっています。同じ型のComponentを1つだけ残し（宣言より長いlistを持つ方を`resoloop component remove ID --yes`で削除）、stateの`components.<key>.supersededId`を消してから再実行してください。`key-not-declared`なら、同じセッションのうちにkeyを元のSlotへ戻して再実行すると完了します。`replacement-unverified`なら、候補のうちlistが宣言と一致するものは中断したapplyが作った新しいComponentなので、削除してから再実行してください。
```

**変更:** `README-DETAILS.md` の次の部分の直後に追加する。

```markdown
stable Componentの親Slot変更は作成・参照再解決・旧Component削除としてplan/applyされます。
```

追加する内容:

```markdown
ResoniteLinkがlist要素を削除できないため、宣言したlist memberの要素数が実機より少ない既存Componentも、同じSlotでの作成・参照再解決・旧Component削除（planの`recreate`）として扱います。
```

**変更:** `README-DETAILS.md` の次の部分を置き換える。

置き換え前:

```markdown
`initialFields`はComponent新規作成時だけ設定してruntime dataを上書きしない値です。
```

置き換え後:

```markdown
`initialFields`はComponent新規作成時だけ設定してruntime dataを上書きしない値です（list memberの要素数を減らす再applyではComponentを作り直すため、初期値に戻ります）。
```

**変更:** `README.md` の次の部分の直後に追加する。

```markdown
Interrupted field writes invalidate their old asset evidence before the remote mutation; rerun the same manifest to converge.
```

追加する内容:

```markdown

ResoniteLink cannot remove list elements. When a declared list member such as `MeshRenderer.Materials` is shorter than the runtime list, `diff` shows `recreate`, and apply replaces the Component on the same Slot: it creates the replacement with the declared fields, verifies the list, re-points managed references, and then removes the old Component without `--prune`. The replacement starts from `initialFields` and type defaults for undeclared members. Apply stops before mutation with `APPLY_LIST_SHRINK_REFERENCED` when something other than a managed declared reference points at the old Component, stops with `APPLY_LIST_SHRINK_NOT_CONVERGED` after removing the replacement when the runtime keeps the list longer, and stops before mutation with `APPLY_RECREATE_INTERRUPTED` when an interrupted recreate cannot resume in the same session. Follow the suggestions in the error.
```

**変更:** `README_JA.md` の次の部分の直後に追加する。

```markdown
フィールド書き込みが中断した場合は checkpoint を保持し、同じ manifest で再実行します。
```

追加する内容:

```markdown

ResoniteLink は list の要素を削除できません。`MeshRenderer.Materials` などの list member を実機より短く宣言すると、`diff` は `recreate` を示し、apply は同じ Slot で Component を作り直します。宣言した field で新しい Component を作って list を確かめ、管理 Component の参照を張り替えてから、旧 Component を `--prune` なしで削除します。新しい Component では `initialFields` と宣言していない member が既定値に戻ります。旧 Component を管理 Component の宣言済み参照以外が参照している場合は変更前に `APPLY_LIST_SHRINK_REFERENCED`、runtime が list を元の長さに戻す場合は新しい Component を削除したうえで `APPLY_LIST_SHRINK_NOT_CONVERGED`、中断した作り直しを同じセッションで再開できない場合は変更前に `APPLY_RECREATE_INTERRUPTED` で停止します。エラーの suggestions に従って復旧してください。
```

**変更:** `skills/codex/resonite-build/SKILL.md` の次の部分を置き換える。

置き換え前:

```markdown
so reapply does not erase them.
```

置き換え後:

```markdown
so reapply does not erase them; a reapply that shrinks a declared list recreates the Component, which resets them and every undeclared member.
```

**変更:** `skills/codex/resonite-build/SKILL.md` の次の部分を置き換える。

置き換え前:

```markdown
review create/update/rename/delete targets and reasons.
```

置き換え後:

```markdown
review create/update/rename/recreate/delete targets and reasons. A `recreate` replaces the Component on its Slot without `--prune` because ResoniteLink cannot remove list elements.
```

**変更:** `skills/codex/resonite-debug/SKILL.md` の次の部分の直前に追加する。

```markdown
Explain the evidence and root cause. Do not mutate the world during a diagnosis-only request.
```

追加する内容:

```markdown
`APPLY_LIST_SHRINK_REFERENCED` stops a list-shrink recreate before mutation because something other than a managed declared reference points at the Component; declare that reference with a stable selector or remove it. `APPLY_LIST_SHRINK_NOT_CONVERGED` means the runtime kept the replacement's list longer than declared, so apply removed the replacement; declare the length that the runtime keeps. `APPLY_RECREATE_INTERRUPTED` means an interrupted recreate cannot resume automatically; follow the suggestions for its `reason` and never pick a candidate by position.

```

- [ ] **Step 2: A の `src/` で、B のテストが失敗することを確かめる**

```bash
cd /workspaces/reso-world/external/resoloop
git worktree add --detach .worktrees/compare-b fix/list-shrink-recreate-split
cd .worktrees/compare-b
git checkout fix/slot-index-after-removal -- src
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~Recreate|FullyQualifiedName~ShrinkingAList"
cd .. && git worktree remove --force compare-b
```

Expected: 作り直しに関するテストが FAIL する（今の挙動を固定する回帰のテストは PASS する）。

- [ ] **Step 3: 上流 CI と同じ確認を行う**

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore
```

Expected: `RLoop.Tests` 361 件、`RLoop.IntegrationTests` 19 件がすべて PASS、警告 0 件。

- [ ] **Step 4: コミットを 2 件にまとめる**

Task B1〜B7 のコミットを「実装とテスト」の 1 件にまとめ、文書を 2 件目にする。

```bash
git reset --soft fix/slot-index-after-removal
git restore --staged README.md README_JA.md README-DETAILS.md docs/DECLARATIVE.md skills/codex/resonite-build/SKILL.md skills/codex/resonite-debug/SKILL.md
git commit -F - <<'EOF'
Recreate a managed Component when a declared list member shrinks

ResoniteLink 0.13.1 cannot remove list elements. On Resonite 2026.9.18.82,
sending [A] to a MeshRenderer.Materials list that holds [A,B] leaves
[A,B], sending [] leaves it unchanged, and sending [B] afterwards gives
[B,B]. A declared list shorter than the runtime list therefore never
converged, and apply stopped with APPLY_REFERENCE_NOT_RETAINED after its
other changes were already written.

When a declared list member of a managed Component is shorter than the
observed list, plan the Component as "recreate". Apply creates the
replacement on the same Slot, writes its declared fields and reads it
back, re-points the declared references of managed Components, and only
then removes the replaced Component. State keeps the replaced ID as
supersededId until the removal, and the Slot's indexes are saved again
in the same checkpoint.

The replacement is not a reference target while the replaced Component
is still on the Slot and the replacement is unverified. If the runtime
keeps the list longer than declared, apply removes every replacement
that nothing references yet, restores their state, and stops with
APPLY_LIST_SHRINK_NOT_CONVERGED.

An interrupted recreate resumes by ID only, in the same session, and only
while the document declares its key on the same Slot. Otherwise apply
stops before mutation with APPLY_RECREATE_INTERRUPTED. A replacement whose
ID was not saved is created again only when no same-type Component on the
Slot could be the lost one. Apply also stops before mutation with
APPLY_LIST_SHRINK_REFERENCED when something other than a managed declared
reference points at the replaced Component, and observes the replaced
Component when it detects asset URLs that a world save migrated.

The test fake keeps trailing list elements the way the runtime does.

Refs orange3134/resoloop#5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add README.md README_JA.md README-DETAILS.md docs/DECLARATIVE.md skills/codex/resonite-build/SKILL.md skills/codex/resonite-debug/SKILL.md
git commit -F - <<'EOF'
Document list-shrink recreates and their stop codes

A recreate resets initialFields and every undeclared member, and removes
the replaced Component without --prune. Describe the plan action and the
three stop codes with their recovery in the READMEs, the declarative
guide and the resonite-build and resonite-debug skills.

Refs orange3134/resoloop#5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline fix/slot-index-after-removal..HEAD
dotnet build ResoLoop.slnx --configuration Release && dotnet test ResoLoop.slnx --configuration Release --no-build
```

Expected: コミットは 2 件。テストはすべて PASS。

- [ ] **Step 5: push して PR を出す**

```bash
git push -u origin fix/list-shrink-recreate-split
gh pr create --repo usaturn/resoloop --base fix/slot-index-after-removal --head fix/list-shrink-recreate-split --title "Recreate a managed Component when a declared list member shrinks / 宣言したリスト型メンバーが縮む Component を作り直す" --body-file - <<'EOF'
> Stacked on the index fix (`fix/slot-index-after-removal`). Merge that one first.
> インデックスの修正（`fix/slot-index-after-removal`）の上に積んでいます。先にそちらをマージしてください。

## Summary / 概要

- When a declared list member such as `MeshRenderer.Materials` is shorter than the runtime list, `diff` shows `recreate`, and apply replaces the Component on the same Slot: it creates the replacement, writes and verifies its declared fields, re-points managed references, and then removes the old Component without `--prune`.
- An interrupted recreate resumes by ID in the same session. Otherwise apply stops before mutation with `APPLY_RECREATE_INTERRUPTED` and explains the recovery.
- Apply stops before mutation with `APPLY_LIST_SHRINK_REFERENCED` when something other than a managed declared reference points at the old Component, and with `APPLY_LIST_SHRINK_NOT_CONVERGED` (after removing the replacement) when the runtime keeps the list longer than declared.

- `MeshRenderer.Materials` などの list member を実機より短く宣言すると、`diff` は `recreate` を示し、apply は同じ Slot で Component を作り直します。新しい Component を作って宣言した field を書いて確かめ、管理 Component の参照を張り替えてから、旧 Component を `--prune` なしで削除します。
- 中断した作り直しは、同じセッションの中で ID を使って再開します。それ以外は変更前に `APPLY_RECREATE_INTERRUPTED` で止まり、復旧手順を示します。
- 旧 Component を管理 Component の宣言済み参照以外が参照している場合は変更前に `APPLY_LIST_SHRINK_REFERENCED` で、runtime が list を元の長さに戻す場合は新しい Component を削除したうえで `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まります。

Refs orange3134/resoloop#5 (option (a): apply recreates automatically / 選択肢 (a): apply が自動で作り直す)

## Root cause / 原因

ResoniteLink 0.13.1 cannot remove list elements. On Resonite 2026.9.18.82, sending `[A]` to a list that holds `[A,B]` leaves `[A,B]`, sending `[]` leaves it unchanged, and sending `[B]` afterwards gives `[B,B]`. A shorter declaration therefore never converged in place, and apply stopped with `APPLY_REFERENCE_NOT_RETAINED` after its other changes were already written.

ResoniteLink 0.13.1 には list の要素を削除する操作がありません。Resonite 2026.9.18.82 で、`[A,B]` を持つ list に `[A]` を送っても `[A,B]` のまま、`[]` では変わらず、続けて `[B]` を送ると `[B,B]` になりました。そのため短い宣言はその場では収束せず、apply はほかの変更を書き込んだ後に `APPLY_REFERENCE_NOT_RETAINED` で止まっていました。

## Verification / 確認

- `dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore`: RLoop.Tests 361 and RLoop.IntegrationTests 19 passed, 0 warnings.
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` stops the shrinking apply at every write, before the write lands and after it lands with its response lost, in two scenarios. Each time the next apply in the same session converges (or stops on `replacement-unverified` until the documented recovery), and a world reload during a recreate stops before any write. Convergence means one Component per key with the declared list, managed references on it, saved indexes that match the Slot, and no writes on the next apply or after a world reload.
- With `src/` reverted to the index fix, the recreate tests fail.
- Real Resonite: (to be filled in after the check on a `ResoLoop_Test*` Slot)

- 上記のコマンドで、RLoop.Tests 361 件と RLoop.IntegrationTests 19 件が成功し、警告は 0 件でした。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` は、2 つのシナリオで、作り直しの apply を書き込みの位置ごとに止めます（反映前の失敗と、反映後の応答の喪失）。そのたびに、同じセッションの次の apply が収束する（または `replacement-unverified` で止まり、記載の復旧手順の後に収束する）こと、作り直しの途中で再読込すると書き込みの前に止まることを確かめます。収束とは、key ごとに Component が 1 つで list が宣言どおり、管理 Component の参照がそれを指し、保存した index が Slot と一致し、次の apply と再読込後の apply の書き込みが 0 件になることです。
- `src/` をインデックスの修正の状態に戻すと、作り直しのテストは失敗します。
- 実機での確認:（`ResoLoop_Test*` の Slot で確認した後に記入）

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: PR の URL が表示される。この PR はマージしない（D-8）。

- [ ] **Step 6: 古い fork PR #5 に、作り直したことをコメントして close する**

`#N` の部分は、Step 5 で作成した PR の番号に置き換える。ブランチ `fix/list-shrink-recreate` は残す（D-12）。

```bash
gh pr comment 5 --repo usaturn/resoloop --body-file - <<'EOF'
Rebuilt from upstream main as #N with the split scope (recreate and resume within one session; stop before mutation otherwise), stacked on the Component index fix. Closing this PR; the branch `fix/list-shrink-recreate` stays for reference.

上流の main から #N として作り直しました（範囲は分割案: 同じセッションの中での作り直しと再開。それ以外は変更前に停止）。Component の index の修正の上に積んでいます。この PR は close し、ブランチ `fix/list-shrink-recreate` は参照用に残します。
EOF
gh pr close 5 --repo usaturn/resoloop
```

---

## Part C: 判定基準（ユーザの判断が要る作業を含む）

### Task C1: レビュー（PR ごとに 1 ラウンド）

**Files:** 指摘に応じて Part A・B と同じファイル

- [ ] **Step 1:** PR A と PR B を、それぞれ 1 ラウンドだけレビューする。レビューの方法（どのモデル・スキルで行うか）はユーザに確認する。
- [ ] **Step 2:** 修正するのは、現行の HEAD で再現する High と Medium の指摘だけ。修正はそれぞれのブランチに積む（別のブランチや PR は作らない）。Low はまとめてユーザに判断を仰ぐ。
- [ ] **Step 3:** 同じ不変条件（I1〜I4）が 2 回破れたら、修正を止めて設計を見直す（Spec の 10.3）。
- [ ] **Step 4:** 修正した後は Task A4・B8 の確認を繰り返し、上流に出す前にコミットを A 2 件・B 2 件にまとめ直す（`git push --force-with-lease` は A・B のブランチだけ）。

### Task C2: 実機での確認（ユーザの明示的な指示があるときだけ）

**Files:** なし（`ResoLoop_Test*` の Slot だけを使う）

- [ ] **Step 1:** ユーザに、実機での確認の実施と、使うワールドを確認する。ユーザのワールドの既存の内容には apply しない。
- [ ] **Step 2:** B の worktree で CLI をビルドし、global の resoloop やロックを変えずに、ビルドした DLL を直接実行する（以降の `dotnet "$RESOLOOP_DLL"` は、シェルを開くたびに変数を設定し直してから使う）。

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet build src/RLoop.Cli/RLoop.Cli.csproj --configuration Release
RESOLOOP_DLL=/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split/src/RLoop.Cli/bin/Release/net10.0/resoloop.dll
dotnet "$RESOLOOP_DLL" --version
dotnet "$RESOLOOP_DLL" status --json
```

- [ ] **Step 3:** 上流の `AGENTS.md` に従い、型とメンバー名を推測しない。次の確認用の文書の型とメンバー名を、`dotnet "$RESOLOOP_DLL" type search` / `type describe` / `type specialize` で確かめ、違えば直す。文書は scratchpad に置く（create-reso-world のプロジェクトには置かない）。Materials が 4 つの MeshRenderer と、それを参照する管理 Component を作る。

```json
{"schemaVersion":"1","ownership":{"key":"resoloop-test-list-shrink"},
 "slot":{"key":"root","name":"ResoLoop_Test_ListShrink","parent":"Root"},
 "children":[
   {"slot":{"key":"materials","name":"Materials"},"components":[
     {"key":"m1","type":"[FrooxEngine]FrooxEngine.PBS_Metallic"},
     {"key":"m2","type":"[FrooxEngine]FrooxEngine.PBS_Metallic"},
     {"key":"m3","type":"[FrooxEngine]FrooxEngine.PBS_Metallic"},
     {"key":"m4","type":"[FrooxEngine]FrooxEngine.PBS_Metallic"}]},
   {"slot":{"key":"rubble","name":"Rubble"},"components":[
     {"key":"mesh","type":"[FrooxEngine]FrooxEngine.BoxMesh"},
     {"key":"renderer","type":"[FrooxEngine]FrooxEngine.MeshRenderer",
      "fields":{"Mesh":"$ref:mesh","Materials":["$ref:m1","$ref:m2","$ref:m3","$ref:m4"]}},
     {"key":"holder","type":"[FrooxEngine]FrooxEngine.ReferenceField<[FrooxEngine]FrooxEngine.MeshRenderer>",
      "fields":{"Reference":"$ref:renderer"}}]}]}
```

```bash
dotnet "$RESOLOOP_DLL" validate /tmp/claude-1000/<scratchpad>/list-shrink-4.json --strict --json
dotnet "$RESOLOOP_DLL" diff /tmp/claude-1000/<scratchpad>/list-shrink-4.json --json
dotnet "$RESOLOOP_DLL" apply /tmp/claude-1000/<scratchpad>/list-shrink-4.json --json
```

`<scratchpad>` は実行するセッションの scratchpad のパスに置き換える。state は、文書のあるディレクトリの `.resoloop/state/` に作られる。

- [ ] **Step 4:** `Materials` を `["$ref:m1","$ref:m2","$ref:m3"]` にした文書（`list-shrink-3.json`）で `diff` を実行し、`renderer` が `recreate` になることを確かめる。続けて `apply` を実行して収束すること（`renderer` の Materials が 3 つ、`holder` の `Reference` が新しい Component を指す）を `inspect` で確かめ、もう一度 `apply` して書き込みが 0 件になることを確かめる。
- [ ] **Step 5:** ユーザにワールドの保存と再読込を依頼する。再読込の後に `apply` を実行し、書き込みが 0 件になることを確かめる。
- [ ] **Step 6:** 確認用の root Slot（`ResoLoop_Test_ListShrink`）の ID を `inspect` で確かめてから、`dotnet "$RESOLOOP_DLL" slot delete ID --yes` で削除する。結果（実行したコマンド、Resonite と ResoniteLink の版、書き込みの件数）を PR B の Verification の「Real Resonite」に記入する。

### Task C3: 上流への提出（D-11、文面をユーザに確認）

- [ ] **Step 1:** Task C1・C2 が済み、判定基準（Spec の 10.3）を満たしたことをユーザに報告する。
- [ ] **Step 2:** 次の文面をユーザに見せて確認を取る。上流の Issue（fork の A の Issue を流用）、上流の PR A（`main` 向け）、上流の PR B（A のコミットを含めて `main` 向け、「A を先にマージ」と明記）、上流 Issue #5 へのコメント（B を出したことと、選択肢 (a) を選んだこと）。
- [ ] **Step 3:** 確認を取った後、一度に出す。上流でマージ・リリースされたら、create-reso-world のロックの切り替え、fork の PR の close、各プロジェクトでの `resoloop skills sync` を行う（Spec の 10.5）。
