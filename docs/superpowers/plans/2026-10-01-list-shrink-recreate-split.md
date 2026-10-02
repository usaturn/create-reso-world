# リスト縮小時の Component の作り直し（分割案）と Slot の index の保存し直し 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fork の usaturn/resoloop に、A（Component を削除した後に Slot の index を保存し直し、再読込後に文書から外した key の照合結果を保存する）と B（宣言したリストが実機より短い Component を apply が作り直す）を実装し、fork の PR 2 本で判定基準を確かめる。

**Architecture:** 変更は `src/RLoop.Core/WorldService.cs`（apply の計画と段階）と `src/RLoop.Core/ApplyWorkflow.cs`（state の記録）に限る。A は削除の後に Slot を読み直して index を保存する関数 `SaveSlotIndexesAsync` と、削除計画の照合結果の保存を加える。B は plan で縮小を検出して `recreate` にし、apply に「作り直しの検証」と「置き換え元の削除」の 2 段階を加え、途中の作り直しは state の `supersededId` を使って同じセッションの中で ID だけで再開する。

**Tech Stack:** C# / .NET 10（SDK 10.0.201、`global.json`）、xUnit 2.9.3、テスト用の偽クライアント（`tests/RLoop.Tests/ApplyWorkflowTests.cs` の `FakeResoniteClient`）

**Spec:** `/workspaces/reso-world/docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md`（create-reso-world の main。この計画と同じ PR #8 がマージされた後の版。その後に Spec を直す PR がマージされた場合はその版）。設計の理由と決定事項（D-1〜D-33）は Spec にある。この計画は Spec の 6〜10 章を実装の手順にしたもの。レビュー（R-01〜R-65）の反映の判断は `/workspaces/reso-world/docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md` にある。

## この計画のコードについて

計画に載せたコードは、上流 `b3a84ae` の使い捨てのコピーで試作し、次のとおり確かめた（2026-10-01、fork のリポジトリは未変更。レビューの反映後に確かめ直した）。

- タスクの順に変更を適用し、各タスクで「テストを先に書くと失敗し、実装すると成功する」ことと、各 Step の Expected の件数と名前を確かめた。計画のコードブロックは、この確認に使ったスクリプトから生成している。
- 最後まで適用した状態で、上流 CI と同じ restore・build・test を実行し、`RLoop.Tests` 394 件と `RLoop.IntegrationTests` 19 件がすべて成功し、警告は 0 件だった。
- ミューテーション確認: 実装の要点 33 か所をそれぞれ壊すと、対応するテストが失敗した（壊した箇所の一覧は review-fixes の Spec の 5 章）。
- A の `src/` を上流 `b3a84ae` に戻すと A で追加したテストが失敗し、B の `src/` を A の状態に戻すと B で追加したテストのうち今の挙動を固定するもの以外が失敗することを、全件の実行で確かめた（Task A4 Step 1、Task B8 Step 2）。
- PR #8 の最初のレビュー反映で、B3 の作成ブロックと B4 の `VerifyReplacementsAsync` に小さい変更を足し、テストを 2 件追加した（2026-10-02）。この分は上記の全件再生・ミューテーション33箇所の対象外である。
- 同日の第2回レビュー反映で、その2テストの引数順と書き込みカウンタを修復し、B5 の `session-changed` の案内を補正し、両候補が参照される中断を固定するテストを B7 に1件追加した。上流 `b3a84ae` の新しい一時コピーへ修正後の source/test 66操作を適用し、追加済みの2件と B7 の10ケースを filter 実行して12ケースすべてが成功した（.NET SDK 10.0.401）。自己参照の除外だけを壊すと、修復したテストが Enabled の欠落で失敗することも確認した。これは関連ケースだけの確認で、全件再生・33箇所の再確認・実機検証ではない。実装時は各 Task の Step の Expected（最終 `RLoop.Tests` 397 件）で確かめる。

「置き換え前」のコードと「直後に追加」「直前に追加」の目印は、その時点のファイルの中で 1 か所だけ一致することを確かめてある。行番号は書かない。エディタで文字列を検索して置き換えること。Markdown の「置き換え前」「直後に追加」「直前に追加」は、コードブロック末尾の改行を除いて目印を検索する。追加する内容が空行から始まらないものは、改行を入れずに目印と同じ行へ続けて書く。空行から始まるものは、目印を含む段落の後に空行を挟んで新しい段落として書く。空行で終わる「直前に追加」は、目印の前に段落の区切りを置く。C# のブロックは行単位で当てる。

## Global Constraints

- 実装を始める条件: この計画と Spec を含む create-reso-world の PR #8 がマージされ、`/workspaces/reso-world` のメインの作業ツリーに両方があること（Task 0 Step 0）。
- 作業ルートは `/workspaces/reso-world/external/resoloop`（`origin` = usaturn/resoloop、`upstream` = orange3134/resoloop）。そのメインの作業ツリー（`1ef4d18` の detached HEAD、追跡外の `reviews/`）には触らず、`.worktrees/` の下の worktree で作業する（`.worktrees/` は `.git/info/exclude` で追跡対象外）。例外として、pr-review スキルが `external/resoloop/reviews/#<PR>-<branch>/` に新しいレビューのファイルを作ることは許可する。既存のレビューのファイルとディレクトリは変えない、消さない。fork でコミットするときは `reviews/` を `git add` に含めない。
- 各 bash ブロックは 1 回の Bash 呼び出しで実行し、先頭に `set -euo pipefail` を置く（ブロックに書いてある）。サブエージェントは呼び出しのたびに cwd が戻るので、ブロックの最初の行でその Part の作業ディレクトリへ絶対パスで cd する。subagent-driven-development の implementer-prompt の「Work from:」には、Part ごとの worktree（Part A は `.worktrees/slot-index-after-removal`、Part B は `.worktrees/list-shrink-recreate-split`）を渡す。`dotnet test` は Bash ツールの既定のタイムアウト（120 秒）を超えうるので、長め（600 秒など）に指定する。
- 分岐元: A は `origin/main`（= `upstream/main` = `b3a84ae`）。B は A のブランチ。
- ブランチ: A は `fix/slot-index-after-removal`（base `main`）、B は `fix/list-shrink-recreate-split`（base `fix/slot-index-after-removal`）。
- テストは偽クライアントで行い、Resonite に接続しない。dotnet は `global.json` のあるディレクトリ（worktree の直下）で実行する。
- state の `schemaVersion` は 2 のまま。`supersededId` は null のとき書かない（`JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)`）。
- エラーコード: `APPLY_LIST_SHRINK_REFERENCED`（終了コード 6）、`APPLY_RECREATE_INTERRUPTED`（6、`reason` は `session-changed` / `key-not-declared` / `declaration-shrank` / `replacement-unverified`）、`APPLY_LIST_SHRINK_NOT_CONVERGED`（7）。保存 ID の無い key の縮小は、既存の `STABLE_COMPONENT_AMBIGUOUS`（6）で止める。
- plan の操作名は `recreate`。サマリーでは `updates` に数える。
- コミットの件名は英文の命令形。Claude Code が書くコミットの末尾には `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。最終的に A は 2 件、B は 2 件にまとめる。`Refs orange3134/resoloop#5` は、上流に出す前の最後のまとめ直し（Task C1 Step 4）で B の 2 件に付け、それまでは付けない。
- fork の Issue・PR の本文は英日併記。Issue は Summary / Reproduction / Environment and verification / Proposed fix、PR は Summary / Root cause / Verification / Known limitations の構成にする。PR の Summary に互換性と既存の規則（`--yes`）との関係を入れ、Verification に OS と SDK、実機で確かめたかどうかを書く。GitHub の番号は、コマンドで取得して `sed` で置き換える（引用付き heredoc の中で手で置き換えない）。
- 禁止事項:
  - fork の PR をマージしない。fork の main へ push しない。
  - 新しく作る fork の PR は A と B の 2 本だけ、Issue は A 用の 1 件だけ。
  - 既存のブランチ（`fix/list-shrink-recreate`、`fix/asset-url-save-migration`、`fix/slot-snapshot-dedup`）を force push・削除しない。force push してよいのは A・B の 2 本だけ。
  - レビュー修正のために別のブランチや PR を作らない（fork の規則。設計を変えるときに create-reso-world に Spec を直す PR を出すことは、ユーザの承認を得た場合に限り対象外。Task C1 Step 3）。
  - 判定基準を満たす前に、上流（orange3134/resoloop）へ Issue・PR・コメントを出さない。出すときは文面をユーザに見せて確認を取る。
  - create-reso-world のロック（`.devcontainer/resoloop.lock`）と、global に導入した resoloop を変えない。
- 実機（Resonite）の操作は、ユーザの明示的な指示があるときだけ、上流の `AGENTS.md` の安全規則に従って `ResoLoop_Test*` の Slot の下で行う。
- Python を使うときは `uv run` を使う。日本語の文章は create-reso-world の `AGENTS.md` の「日本語表現」に従う。
- create-reso-world の `AGENTS.md`（特に「リポジトリ境界」「resoloop 注意」「SDD 実行運用」）に従う。external/resoloop の worktree を cwd として起動するエージェントにも読ませる。各 Task の着手・完了の時刻を記録し、作業報告に所要時間と Task ごとの内訳を書く。
- 引き継ぎの区切りは Task A4 の完了後（PR A の作成後）と Task B8 の完了後（PR B の作成後、Part C の前）とし、agent-handoff スキルで引き継ぐ。A・B のブランチの先頭の SHA と、fork の Issue・PR の番号を残す。

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

- [ ] **Step 0: Spec と計画がマージされていることを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world
gh pr view 8 --repo usaturn/create-reso-world --json state -q .state
test -f docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md
test -f docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md
git rev-parse origin/main
```

Expected: `MERGED` が表示され、2 つのファイルがある。満たさなければ止まってユーザに報告する（メインの作業ツリーを追従させるのはユーザ。または repo-cleanup-after-merge で行う）。最後の行のコミットを作業報告と fork の PR の Verification に記録する。

- [ ] **Step 1: リモートの状態を確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop
git remote -v
git fetch origin && git fetch upstream
git rev-parse origin/main upstream/main
```

Expected: `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop。`origin/main` と `upstream/main` の行が、どちらも `b3a84ae9b4d09cb60a298879e1cf56e3cf0bd888`。コマンドがエラーになった場合や値が違う場合は、止まってユーザに報告する（分岐元が変わるため）。`external/resoloop` の checkout が無い場合は、`scripts/resoloop-fork.sh clone` を案内して止まる。

- [ ] **Step 2: A の worktree を作る**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop
git worktree add .worktrees/slot-index-after-removal -b fix/slot-index-after-removal origin/main
```

- [ ] **Step 3: 基準のテストを実行する**

```bash
set -euo pipefail
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
- Produces（以降のテストが使う補助）: `IndexedSiblings(string ownership, string[] onRoot, string[]? onChild = null)`、`AssertSavedIndexesMatchLayout(FakeResoniteClient client, string state)`（保存した index が実機の位置と一致すること。Spec の I1 の確認）、`AllSlots(FakeResoniteClient.FakeSlot slot)`

- [ ] **Step 1: 再現テストを書く**

同じ型で identityFields の無い Component 3 つから 1 つを prune、または別の Slot に移動し（子の Slot から親の Slot への移動を含む）、ワールドを再読込してから apply する。各 key に別々の値（`v1` は 1 など）を宣言しているので、ほかの key の Component に結び付くと書き込みとして現れる。

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
    [InlineData("move-up")]
    public async Task RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload(string removal)
    {
        var name = "indexes-" + removal;
        // move-up moves v1 to the parent Slot, which apply handles before the Slot that v1 leaves.
        var full = ReloadDocument(name, removal == "move-up"
            ? IndexedSiblings(name, [], ["v1", "v2", "v3"])
            : IndexedSiblings(name, ["v1", "v2", "v3"]));
        var changed = ReloadDocument(name + "-changed", removal switch
        {
            "prune" => IndexedSiblings(name, ["v2", "v3"]),
            "move" => IndexedSiblings(name, ["v2", "v3"], ["v1"]),
            _ => IndexedSiblings(name, ["v1"], ["v2", "v3"])
        });
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

    // Every saved key whose Component is on its Slot is saved at that Component's position.
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
}
```

- [ ] **Step 2: 失敗することを確かめる（D-15 の判定）**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload" || true
```

Expected: 3 件とも FAIL（`prune`・`move`・`move-up`）。`AssertSavedIndexesMatchLayout` が「`Key 'v2' is saved at index 1 but its Component is at 0.`」のように、削除の後に古い index が残っていることを示す。

成功してしまった場合（上流の main で再現しない場合）は、ここで止まってユーザに報告する（D-15: A をやめ、I1 は B の中だけで扱う）。作ったブランチと worktree は消さずに残して報告し、A をやめる場合は、B の計画（分岐元、A の補助関数、`SaveSlotIndexesAsync`）の作り直しをユーザと決める。

- [ ] **Step 3: fork に A の Issue を出す**

Spec の 3.3 の結果（A の再現と、文書から外した key の照合結果が失われる問題）をまとめる。出力された Issue の番号を作業報告に記録する（Task A4 の PR の本文は、Issue をタイトルで検索して番号を入れる）。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
gh issue create --repo usaturn/resoloop --title "Component indexes go stale after a removal, and undeclared keys lose their binding after a world reload / Component の削除後に index がずれ、再読込後に文書から外した key の照合結果が失われる" --body-file - <<'EOF'
## Summary / 概要

After apply removes a Component (the source of a Component move, or a pruned Component), the Components after it on the same Slot keep their old `componentIndex` in state. After the world is saved and reloaded, apply binds keys without `identityFields` by that index, so the next apply binds a key to a sibling's Component or stops with `STABLE_COMPONENT_AMBIGUOUS`.

Separately, after a world reload the deletion plan binds keys that the document no longer declares, but apply never saves that binding. The first apply in the reloaded session moves the checkpoint to the new session while those keys keep their old IDs, so later plans in the same session look them up by the old IDs and drop them from `--deletes-only` and `--prune`.

apply が Component を削除すると（Component の移動元、または prune した Component）、同じ Slot でその後ろにある Component の `componentIndex` が state に古いまま残ります。ワールドを保存して再読込すると、apply は `identityFields` の無い key をこの index で照合するため、次の apply で兄弟の Component に結び付くか、`STABLE_COMPONENT_AMBIGUOUS` で止まります。

これとは別に、再読込後の削除計画は文書から外した key を照合しますが、apply はその結果を保存しません。再読込後の最初の apply で checkpoint のセッションだけが新しくなり、key の ID は古いまま残るため、同じセッションの後続の plan はその ID で探して見つけられず、`--deletes-only` と `--prune` の対象から外れます。

## Reproduction / 再現手順

1. Declare three Components of the same type without `identityFields` on one Slot (keys `t1`, `t2`, `t3`) and apply.
2. Remove `t1` from the document and run `apply --prune --yes`. State keeps `t2` at index 1 and `t3` at index 2, while they are at 0 and 1.
3. Reload the world, then run `apply` again.

Expected: the apply after the reload binds every key to its own Component and writes nothing. Actual: it stops with `STABLE_COMPONENT_AMBIGUOUS`. Moving `t1` to another Slot instead of pruning it gives the same result.

For the second problem: remove a Component and a Slot from the document without `--prune`, reload the world, run `plan --prune`, run `apply`, and run `plan --prune` again. Expected: both plans list the Component and the Slot. Actual: the first plan lists both, and the second lists nothing.

1. 1 つの Slot に、`identityFields` の無い同じ型の Component を 3 つ（key `t1`・`t2`・`t3`）宣言して apply します。
2. 文書から `t1` を外して `apply --prune --yes` を実行します。state では `t2` が index 1、`t3` が index 2 のまま残りますが、実機の位置は 0 と 1 です。
3. ワールドを再読込してから `apply` を実行します。

期待する結果: 再読込後の apply は、各 key を自分の Component に結び付け、何も書き込みません。実際の結果: `STABLE_COMPONENT_AMBIGUOUS` で止まります。`t1` を prune する代わりに別の Slot へ移しても同じです。

2 つ目の問題: Component と Slot を `--prune` なしで文書から外し、ワールドを再読込して `plan --prune`、`apply`、`plan --prune` の順に実行します。期待する結果: どちらの plan も Component と Slot を挙げます。実際の結果: 1 回目は両方を挙げ、2 回目は何も挙げません。

## Environment and verification / 環境と確認方法

resoloop `main` at `b3a84ae` (0.1.0-preview.15). Reproduced offline with the test fake client, whose `ReloadWorld` assigns new IDs to every Slot and Component as a world reload does. Not yet observed on a live world.

resoloop の `main`（`b3a84ae`、0.1.0-preview.15）。テスト用の偽クライアントで再現しました。偽クライアントの `ReloadWorld` は、ワールドの再読込と同じく、すべての Slot と Component に新しい ID を付けます。実機のワールドではまだ確かめていません。

## Proposed fix / 修正案

- After each Component removal, read the Slot again and save every key whose saved ID is on it at that Component's position.
- Save the ID (and, for a Component, the index) that the deletion plan binds for each undeclared key, in the next checkpoint. Plans never write state.

- Component を削除するたびに Slot を読み直し、保存している ID が Slot 上にある key の index を、その Component の位置に保存し直す。
- 削除計画が文書から外した key に照合した ID（Component は index も）を、次の checkpoint で保存する。plan は state を書かない。
EOF
```

Expected: Issue の URL が表示される。番号を作業報告に記録する。

### Task A2: Component を削除した後の index の保存し直し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`ApplyAsync` のフィールドの段階と prune、`BuildComponentPlans`、`BuildDeletionPlans`、`ComponentRuntime`、`DeletionRuntime`、新しい `SaveSlotIndexesAsync`）
- Modify: `docs/DECLARATIVE.md`
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

**Interfaces:**
- Consumes: Task A1 の補助
- Produces: `private async Task SaveSlotIndexesAsync(PreparedApply prepared, string slotKey, string slotId, CancellationToken cancellationToken)`（Slot を読み直し、保存している ID が Slot 上にある key の `ComponentIndex` を保存し直す。その Slot に宣言した key の実行時の `ComponentRuntime.ComponentIndex` も実機の位置に合わせる。メモリ上の state だけを変え、保存は呼び出し側の次の checkpoint が行う）。`ComponentRuntime.ComponentIndex` は set 可能になる。`ComponentRuntime.RelocationSourceSlotKey` / `RelocationSourceSlotId`。`DeletionRuntime` の `SlotKey` / `SlotId`。

- [ ] **Step 1: 文書から外した兄弟の index と、prune の途中のキャンセルのテストを足す**

2 つ目のテストは、prune の削除が反映された直後にキャンセルされても、削除した key が state に残らないことを確かめる。

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

    [Fact]
    public async Task APruneCancelledWhileSavingIndexesKeepsTheRemovedKeyOutOfTheState()
    {
        const string name = "indexes-cancelled-prune";
        var full = ReloadDocument(name, IndexedSiblings(name, ["v1", "v2", "v3"]));
        var trimmed = ReloadDocument(name + "-trimmed", IndexedSiblings(name, ["v2", "v3"]));
        var client = new FakeResoniteClient(full);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(full, new ApplyOptions(state));
        using var cancellation = new CancellationTokenSource();
        client.Cancellation = cancellation;
        client.CancelAfterWrites = 1; // cancel right after the removal of v1 lands
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() =>
            service.ApplyAsync(trimmed, new ApplyOptions(state, Prune: true, ConfirmDeletes: true), cancellation.Token));

        Assert.Equal("APPLY_CANCELLED", error.Code);
        Assert.Equal(new[] { "v2", "v3" },
            JsonNode.Parse(File.ReadAllText(state))!["components"]!.AsObject().Select(pair => pair.Key).Order(StringComparer.Ordinal));
        client.CancelAfterWrites = null;
        await service.ApplyAsync(trimmed, new ApplyOptions(state));
        AssertSavedIndexesMatchLayout(client, state);
        client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();
        await service.ApplyAsync(trimmed, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload|FullyQualifiedName~AnUndeclaredSiblingKeepsItsIndex|FullyQualifiedName~APruneCancelledWhileSavingIndexes" || true
```

Expected: 5 件とも FAIL。Task A1 の 3 件と `AnUndeclaredSiblingKeepsItsIndexWhenAnotherComponentLeavesTheSlot` は保存した index が実機の位置と一致しない。`APruneCancelledWhileSavingIndexesKeepsTheRemovedKeyOutOfTheState` は、キャンセルが apply に届かずに成功する（`No exception was thrown`）。

- [ ] **Step 3: `SaveSlotIndexesAsync` と呼び出しを実装し、文書を更新する**

Component の移動元を削除した後と、prune で Component を削除した後に、その Slot の index を保存し直す。移動元の Slot は plan の時点で `FindStateSlot` が得たもの、prune の Slot は削除計画が照合したものを使う。フィールドの段階は実行時の `ComponentIndex` で state を書き直すので、`SaveSlotIndexesAsync` は実行時の値も合わせる（子から親への移動では、移動元の Slot の key が移動元の削除の後に処理される）。prune は、上流と同じく削除の結果を先に checkpoint してから Slot を読み直す（読み取りの失敗やキャンセルで、削除した key が state に残らないようにする）。

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
                    // Save the removal before reading the Slot again, so a cancel or a failed read cannot keep the removed key.
                    Checkpoint(prepared);
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
                        (runtime.RelocationSourceSlotKey, runtime.RelocationSourceSlotId) = (stateComponent!.SlotKey, sourceSlot!.Id);
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
    // A key whose ID is not on the Slot keeps its index. The Components declared on the Slot take the same positions in
    // this apply too, because the fields phase saves each one's index again. The caller's next checkpoint persists the result.
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
        foreach (var runtime in prepared.Components.Where(runtime => runtime.Node.StableKey == slotKey && !string.IsNullOrEmpty(runtime.Id)))
        {
            var index = layout.IndexOf(runtime.Id!);
            if (index >= 0) runtime.ComponentIndex = index;
        }
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
        public int ComponentIndex { get; } = componentIndex;
```

置き換え後:

```csharp
        public int ComponentIndex { get; set; } = componentIndex;
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
applyがComponentを削除・移動した後は、同じSlotに残るkeyのindexも実機の並びに合わせて保存し直します。
```

- [ ] **Step 4: 成功することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload|FullyQualifiedName~AnUndeclaredSiblingKeepsItsIndex|FullyQualifiedName~APruneCancelledWhileSavingIndexes"
```

Expected: 5 件とも PASS。

- [ ] **Step 5: 全件を実行してコミットする**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
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
whose saved ID is still on it at that Component's position, and moves the
runtime index of the Components declared on that Slot too, because the
fields phase saves each one's index again. A prune checkpoints its removal
before it reads the Slot, so a cancel or a failed read cannot keep the
removed key.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: 全件が PASS（`RLoop.Tests` 331 件）。

### Task A3: 文書から外した key の照合結果の保存

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`BuildDeletionPlans`）
- Modify: `tests/RLoop.Tests/ApplyWorkflowTests.cs`（偽クライアントに `LoseResponseOnWrite` を追加）
- Modify: `docs/DECLARATIVE.md`
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`

**Interfaces:**
- Consumes: Task A2 の `SaveSlotIndexesAsync`
- Produces: 偽クライアントの `public int? LoseResponseOnWrite { get; set; }`（その番号の書き込みを反映してから、応答を失ったとして `IOException` を投げる。Slot・Component の作成と削除、Slot の更新、フィールドの書き込みのすべてが対象）。テストの補助 `InterruptedAsync(Func<Task> apply)`（偽クライアントの `IOException` を中断として扱う）

- [ ] **Step 1: テストと偽クライアントの拡張を書く**

2 つ目のテストは、再読込後の最初の apply が移動を行い、文書から外した同じ Slot の key が残る流れを固定する。3 つ目のテストは、移動を含む apply を書き込みの位置ごとに止め（反映前に失敗／反映後に応答を失う）、同じセッションの次の apply の後に保存した index が実機の位置と一致し、再読込後の apply の書き込みが 0 件になることを確かめる。移動の向きは親から子と子から親の両方で、中断しなかった回は次の apply の前にも確かめる。移動の途中で止まると移動元が残ることがあるが、これは上流の既存の課題で、このテストでは index だけを確かめる。prune の削除の応答が失われた場合は既知の制限（Spec 11.1）なので、このテストには入れない。

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

    [Fact]
    public async Task TheFirstApplyAfterAReloadSavesTheIndexOfAnUndeclaredSibling()
    {
        const string name = "indexes-after-reload";
        var full = ReloadDocument(name, IndexedSiblings(name, ["v1", "v2", "v3"]));
        var moved = ReloadDocument(name + "-moved", IndexedSiblings(name, ["v2"], ["v1"]));
        var client = new FakeResoniteClient(full);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(full, new ApplyOptions(state));
        client.ReloadWorld("session-2");
        await service.ApplyAsync(moved, new ApplyOptions(state));
        AssertSavedIndexesMatchLayout(client, state);
        client.ReloadWorld("session-3");
        client.ResetWriteCounts();

        var plan = await service.PlanApplyAsync(moved, new ApplyOptions(state, Prune: true));

        Assert.Equal("v3", Assert.Single(plan.Operations, operation => operation.Action == "delete").Key);
        await service.ApplyAsync(moved, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

    // An interrupted move can leave its source Component behind (an existing upstream issue that this change does not
    // address). Wherever the apply stops, the next apply in the same session must still save indexes that bind every key
    // to its own Component after a world reload, and an apply that finished must have saved them already. A pruned
    // Component whose removal response is lost stays in the state even after later applies in the same session; that is a
    // known limitation, so this test covers only moves.
    [Theory]
    [InlineData(false, "down")]
    [InlineData(true, "down")]
    [InlineData(false, "up")]
    [InlineData(true, "up")]
    public async Task AnApplyInterruptedAtAnyWriteSavesBindableIndexesOnTheNextApply(bool responseLost, string direction)
    {
        for (var write = 1; ; write++)
        {
            var name = $"indexes-interrupted-{responseLost}-{direction}-{write}";
            // "up" moves v1 to the parent Slot, which apply handles first. A same-type Component on that Slot already stops
            // this move with an ownership conflict before this change, so the destination holds none.
            var full = ReloadDocument(name, direction == "up"
                ? IndexedSiblings(name, [], ["v1", "v2", "v3"])
                : IndexedSiblings(name, ["v1", "v2", "v3"]));
            var moved = ReloadDocument(name + "-moved", direction == "up"
                ? IndexedSiblings(name, ["v1"], ["v2", "v3"])
                : IndexedSiblings(name, ["v2"], ["v1"]));
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
            if (!interrupted) AssertSavedIndexesMatchLayout(client, state);
            await service.ApplyAsync(moved, new ApplyOptions(state));

            AssertSavedIndexesMatchLayout(client, state);
            client.ReloadWorld("session-reloaded");
            client.ResetWriteCounts();
            await service.ApplyAsync(moved, new ApplyOptions(state));
            Assert.True(client.Writes == 0, $"write {write}: the apply after the reload wrote {client.Writes} time(s).");
            if (!interrupted) break;
        }
    }

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

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~UndeclaredKeysStayInTheDeletionPlan|FullyQualifiedName~TheFirstApplyAfterAReloadSavesTheIndex|FullyQualifiedName~AnApplyInterruptedAtAnyWriteSavesBindableIndexes" || true
```

Expected: 6 件のうち 3 件が FAIL。`UndeclaredKeysStayInTheDeletionPlanAfterAnApplyInTheReloadedSession` は、2 回目の plan の削除対象が空になる（`Assert.Equal() Failure: Collections differ`）。`TheFirstApplyAfterAReloadSavesTheIndexOfAnUndeclaredSibling` は、文書から外した `v3` が Slot の Component に結び付いていない。`AnApplyInterruptedAtAnyWriteSavesBindableIndexesOnTheNextApply(responseLost: True, direction: "down")` は、削除の応答が失われた後の apply で、文書から外した `v3` の index が直らない。ほかの 3 件（`responseLost: False` の 2 件と `responseLost: True, direction: "up"`）は、Task A2 の処理で index を保存し直すので、この時点で PASS する。

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
ワールドの再読込後にapplyが照合したstaleなSlot / ComponentのIDは、そのapplyのcheckpointでstateへ保存します（plan・diffはstateを書きません）。そのため、同じセッションで続けて実行する`--deletes-only`や`--prune`でも対象から外れません。
```

- [ ] **Step 4: 成功することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~UndeclaredKeysStayInTheDeletionPlan|FullyQualifiedName~TheFirstApplyAfterAReloadSavesTheIndex|FullyQualifiedName~AnApplyInterruptedAtAnyWriteSavesBindableIndexes"
```

Expected: 6 件とも PASS。

- [ ] **Step 5: 全件を実行してコミットする**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
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

Expected: 全件が PASS（`RLoop.Tests` 337 件）。

### Task A4: 修正前との比較、push、fork の PR A

**Files:** なし（確認と公開）

- [ ] **Step 1: 修正前の `src/` で、追加したテストが失敗することを確かめる**

使い捨ての worktree で `src/` だけを修正前の基準（`BASE`）に戻し、全件を流す。テストが失敗するので終了コードは 0 以外になる（ブロックの最後で確かめる）。途中で止まって worktree が残った場合は、`git -C /workspaces/reso-world/external/resoloop worktree remove --force /workspaces/reso-world/external/resoloop/.worktrees/compare-a`（ディレクトリが無ければ `git -C /workspaces/reso-world/external/resoloop worktree prune`）で片付けてからやり直す。

```bash
set -euo pipefail
R=/workspaces/reso-world/external/resoloop
C=$R/.worktrees/compare-a
BASE=b3a84ae   # Task C3 で上流の main に追従した後は upstream/main
git -C "$R" worktree add --detach "$C" fix/slot-index-after-removal
test "$(git -C "$C" rev-parse --show-toplevel)" = "$C"
git -C "$C" checkout "$BASE" -- src
rc=0
(cd "$C" && dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release) || rc=$?
git -C "$R" worktree remove --force "$C"
test "$rc" -ne 0
```

Expected: 337 件中 FAIL 11 件、PASS 326 件。FAIL は A で追加したテストだけ（`RemovingAComponentSavesTheIndexesOfItsSiblingsForAWorldReload` の 3 件、`AnUndeclaredSiblingKeepsItsIndexWhenAnotherComponentLeavesTheSlot`、`APruneCancelledWhileSavingIndexesKeepsTheRemovedKeyOutOfTheState`、`UndeclaredKeysStayInTheDeletionPlanAfterAnApplyInTheReloadedSession`、`TheFirstApplyAfterAReloadSavesTheIndexOfAnUndeclaredSibling`、`AnApplyInterruptedAtAnyWriteSavesBindableIndexesOnTheNextApply` の 4 件）。 これ以外の組み合わせになったら先に進まずに報告する。

- [ ] **Step 2: 上流 CI に相当する確認を行う（Linux）**

上流 CI（`.github/workflows/ci.yml`）は windows-latest で restore・build・test・pack と、導入したツールでのスモークテストを行う。ここでは Linux で同じ手順を行い、Windows での確認は上流 PR の CI に任せる。global の resoloop とロックは変えない。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore
S=$(mktemp -d)
dotnet pack src/RLoop.Cli/RLoop.Cli.csproj --configuration Release --no-build --output "$S/artifacts"
VERSION=$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' src/RLoop.Cli/RLoop.Cli.csproj | head -n 1)
dotnet tool install ResoLoop --tool-path "$S/tool" --add-source "$S/artifacts" --version "$VERSION"
"$S/tool/resoloop" --version
"$S/tool/resoloop" init "$S/smoke"
"$S/tool/resoloop" skills sync "$S/smoke" --check
"$S/tool/resoloop" validate "$S/smoke/content/main.json" --json
rm -rf -- "$S"
git log --oneline origin/main..HEAD
dotnet --version
```

Expected: `RLoop.Tests` 337 件、`RLoop.IntegrationTests` 19 件がすべて PASS、警告 0 件。pack・導入・スモークテストが成功する。コミットは Task A2・A3 の 2 件。`dotnet --version` の値を PR の Verification に書く。

- [ ] **Step 3: push して PR を出す**

Issue の番号は、Task A1 の Issue をタイトルで検索して取り、本文の `ISSUE_A` を置き換える（完全な形 `usaturn/resoloop#…` で書くので、上流に貼っても上流の無関係な Issue を指さない）。本文の件数は、直前の Step の結果に合わせる。Task C1 で修正を積んだ後は `gh pr edit --body-file` で更新する。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/slot-index-after-removal
test "$(git branch --show-current)" = fix/slot-index-after-removal
ISSUE_A=$(gh issue list --repo usaturn/resoloop --state open --search '"Component indexes go stale" in:title' --json number -q '.[0].number')
test -n "$ISSUE_A"
git push -u origin fix/slot-index-after-removal
sed "s/ISSUE_A/$ISSUE_A/" <<'EOF' | gh pr create --repo usaturn/resoloop --base main --head fix/slot-index-after-removal --title "Save Component indexes after a removal and keep the bindings of undeclared keys after a world reload / Component の削除後に index を保存し直し、再読込後も文書から外した key の照合結果を保つ" --body-file -
## Summary / 概要

- After apply removes a Component (the source of a move, or a pruned Component), it reads the Slot again and saves the index of every key whose saved ID is still on it.
- After a world reload, the deletion plan's bindings for keys that the document no longer declares (Slot IDs, Component IDs and indexes) are saved in the next checkpoint, so later plans in the same session still find them.
- Compatibility: the state format does not change. Each removal adds one Slot read without Component data, and each pruned Component one more state write.

- apply が Component を削除した後（移動元、または prune）、Slot を読み直し、保存している ID が Slot 上にある key の index を保存し直します。
- ワールドの再読込後、削除計画が文書から外した key に照合した結果（Slot の ID、Component の ID と index）を次の checkpoint で保存し、同じセッションの後続の plan でも見つかるようにします。
- 互換性: state の形式は変わりません。削除 1 回につき Component のデータを含まない Slot の読み取りが 1 回、prune では state の書き出しも 1 回増えます。

Fixes usaturn/resoloop#ISSUE_A

## Root cause / 原因

- A world reload binds keys without `identityFields` by their saved `componentIndex`, but a removal shifted the Components after it without saving them again. The next apply after a reload bound a key to a sibling's Component or stopped on `STABLE_COMPONENT_AMBIGUOUS`.
- The deletion plan's bindings were never saved. The first apply in a reloaded session moved the checkpoint to the new session while undeclared keys kept their old IDs, so later plans in that session dropped them from `--deletes-only` and `--prune`.

- 再読込後は `identityFields` の無い key を保存した `componentIndex` で照合しますが、削除した Component より後ろにある Component の index を保存し直していませんでした。そのため再読込後の apply が、同じ Slot の別の Component に結び付くか、`STABLE_COMPONENT_AMBIGUOUS` で止まりました。
- 削除計画の照合結果を保存していなかったため、再読込後の最初の apply で checkpoint のセッションだけが新しくなり、文書から外した key は古い ID のまま残りました。その後の同じセッションの plan では、`--deletes-only` と `--prune` の対象から外れていました。

## Verification / 確認

- Linux Dev Container, .NET SDK 10.0.201: `dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore`: RLoop.Tests 337 and RLoop.IntegrationTests 19 passed, 0 warnings. Pack and the smoke test of the installed tool passed. Windows is left to the CI of this PR.
- New tests in `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` cover a prune and moves in both directions followed by a world reload, an undeclared sibling, a prune cancelled right after its removal, undeclared keys after an apply in the reloaded session, and an apply with a move interrupted at every write (before the write lands, and after it lands with its response lost).
- With `src/` reverted to `main`, all 11 new test cases fail, and every other test passes.
- Not checked on a live world; the reload is simulated by the fake client.

- Linux の Dev Container（.NET SDK 10.0.201）で上記のコマンドを実行し、RLoop.Tests 337 件と RLoop.IntegrationTests 19 件が成功し、警告は 0 件でした。pack と、導入したツールでのスモークテストも成功しました。Windows での確認は、この PR の CI に任せます。
- `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` に、prune と両方向の移動の後の再読込、文書から外した同じ Slot の別の key、削除の直後にキャンセルした prune、再読込後のセッションでの apply の後の照合、移動を含む apply の書き込みの位置ごとの中断（反映前の失敗と、反映後の応答の喪失）のテストを追加しました。
- `src/` を `main` に戻すと、追加した 11 件はすべて失敗し、それ以外のテストはすべて成功します。
- 実機のワールドでは確かめていません。再読込は偽クライアントで再現しています。

## Known limitations / 既知の制限

- If the response to a removal is lost and the world is reloaded before the next successful apply, the stale index stays (unchanged from before). If the response to a pruned Component's removal is lost, its key stays in the state even after later applies in the same session; after a reload it can stop apply or bind an unmanaged Component of the same type. Removing the key from the state before the reload recovers it.
- An interrupted Component move can still leave its source behind; this change does not address that existing issue.

- 削除の応答が失われ、次の apply が成功する前にワールドを再読込すると、古い index が残ります（修正前と同じ）。prune で削除した Component の応答が失われた場合は、同じセッションの後続の apply が成功しても、その key が state に残ります。再読込後は apply が止まるか、同じ型の管理外の Component に結び付くことがあります。再読込の前に state からその key を外すと復旧できます。
- Component の移動が中断すると移動元が残ることがある既存の問題は、この変更では直していません。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: PR の URL が表示される。この PR はマージしない（D-8）。push の後は agent-handoff スキルで引き継ぐ（Global Constraints の区切り）。

---

## Part B: リスト縮小時の作り直し（`fix/list-shrink-recreate-split`）

作業ディレクトリ: `/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split`

### Task B1: 偽クライアントのリストと、テストの共通処理

**Files:**
- Modify: `tests/RLoop.Tests/ApplyWorkflowTests.cs`（`FakeResoniteClient`）
- Create: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Produces（偽クライアント）: `ListMembers`（リストとして持つメンバー名。既定は `Materials`。文字列の要素は参照、それ以外の要素は値として持つ。短いリストを送ると先頭だけを置き換え、末尾を残す）、`RefillListsTo`（書き込んだリストを、この要素数まで詰め直す）、`FailRemovingComponent`（この ID の Component の削除を、反映前に失敗させる）
- Produces（テストの補助）: `RubbleWorld(string ownership, params string[] materials)`、`RubbleWorld(string ownership, string[] materials, string? rendererSlot, bool watcher = false)`（watcher は `initialFields` を持つ）、`TwoRendererWorld(...)`（`shared` では同じ型の `leftover` を文書から外す）、`PointingRenderersWorld(string ownership, int first, int second, bool mutual = false)`、`ApplyRubbleAsync(string name, string changed, string? initial = null)`、`ApplyScenarioAsync(string name, string scenario)`（`one-recreate` は watcher 付き）、`AssertListShrinkConvergedAsync(...)`（収束の判定。Test.Renderer と Test.Source がそれぞれ 1 つの key に結び付くことも見る）、`RubbleRenderers`、`Sources`、`MaterialTargets`、`StateId`

- [ ] **Step 1: B の worktree を作る**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop
git worktree add .worktrees/list-shrink-recreate-split -b fix/list-shrink-recreate-split fix/slot-index-after-removal
```

- [ ] **Step 2: 偽クライアントを拡張し、共通処理と最初のテストを書く**

偽クライアントは、Resonite `2026.9.18.82` と ResoniteLink `0.13.1` で観測したリストの挙動（`[A,B]` に `[A]` を送っても `[A,B]`、`[]` では変わらず、続けて `[B]` を送ると `[B,B]`）をまねる。最初のテストは、長くなるリストと並べ替えたリストが従来どおりその場で更新されることを確かめる。2 つ目のテストは、偽クライアントがリストを縮められないことそのものを固定する（偽クライアントを変えたときに、修正前のコードを検出する力が失われないように）。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.cs` の次の部分の直後に追加する。

```csharp
        public List<string> DescribedTypes { get; } = [];
```

追加する内容:

```csharp
        // Members kept as lists: string elements are references, other elements values. ResoniteLink 0.13.1 replaces only
        // the leading elements and cannot remove any (Resonite 2026.9.18.82): [A,B] stays [A,B] after [A], [] changes
        // nothing, and [B] then gives [B,B].
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
            var desired = (JsonNode.Parse(raw) as JsonArray ?? []).ToArray();
            var kept = current?.Elements ?? [];
            var elements = new List<MemberValue>();
            for (var i = 0; i < Math.Max(desired.Length, kept.Count); i++)
                elements.Add(i >= desired.Length ? kept[i]
                    : desired[i] is null || desired[i] is JsonValue value && value.TryGetValue<string>(out _)
                        ? new MemberValue("reference", $"{id}[{i}]", TargetId: desired[i]?.GetValue<string>())
                        : new MemberValue("field", $"{id}[{i}]", "value", desired[i]!.DeepClone()));
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

    // ResoniteLink 0.13.1 replaces only the leading elements of a list and cannot remove any. The fake client must do the
    // same, or the tests below could pass against an apply that only writes the shorter list.
    [Fact]
    public async Task TheFakeClientCannotShrinkAListLikeResoniteLink()
    {
        var client = new FakeResoniteClient();
        var renderer = await client.AddComponentAsync(client.Root.Id, "Test.Renderer", new Dictionary<string, string> { ["Materials"] = """["A","B"]""" });
        string?[] Targets() => client.Root.Components.Single(component => component.Id == renderer.Id).Members["Materials"].Elements!
            .Select(element => element.TargetId).ToArray();

        await client.SetComponentMembersAsync(renderer.Id, "Test.Renderer", new Dictionary<string, string> { ["Materials"] = """["A"]""" });
        Assert.Equal(new string?[] { "A", "B" }, Targets());
        await client.SetComponentMembersAsync(renderer.Id, "Test.Renderer", new Dictionary<string, string> { ["Materials"] = "[]" });
        Assert.Equal(new string?[] { "A", "B" }, Targets());
        await client.SetComponentMembersAsync(renderer.Id, "Test.Renderer", new Dictionary<string, string> { ["Materials"] = """["B"]""" });
        Assert.Equal(new string?[] { "B", "B" }, Targets());
    }

    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
    // the renderer. With watcher, a Source on a later Slot also points at the renderer and sets an initial-only member.
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
        var late = watcher ? """,{"slot":{"key":"late","name":"Late"},"components":[{"key":"watcher","type":"Test.Source","initialFields":{"Enabled":true},"fields":{"Target":"$ref:renderer"}}]}""" : "";
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
    // In the shared-slot scenario a sibling moves away, a same-type sibling is no longer declared, and r1 also gets a material
    // that is created later in the same apply.
    private static string TwoRendererWorld(string ownership, string[] first, string[] second, bool shared = false, bool shrunk = false)
    {
        static string List(IEnumerable<string> keys) => string.Join(",", keys.Select(key => $"\"$ref:{key}\""));
        var siblings = !shared ? "" : shrunk ? "" :
            """,{"key":"mover","type":"Test.Indexed","fields":{"Value":7}},{"key":"leftover","type":"Test.Renderer","fields":{"Materials":["$ref:m4"]}}""";
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

    // Two renderers on Rubble01 with the given numbers of materials; r2 points at r1, and with mutual r1 points at r2 too.
    private static string PointingRenderersWorld(string ownership, int first, int second, bool mutual = false)
    {
        static string Materials(int count) => string.Join(",", new[] { "m1", "m2", "m3", "m4" }.Take(count).Select(key => $"\"$ref:{key}\""));
        var target = mutual ? ",\"Target\":\"$ref:r2\"" : "";
        return $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{ownership}}}"},"slot":{"key":"root","name":"Rubble","parent":"Root"},
             "children":[
               {"slot":{"key":"materials","name":"Materials"},"components":[
                 {"key":"m1","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m2","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m3","type":"Test.Material","fields":{"Enabled":true}},
                 {"key":"m4","type":"Test.Material","fields":{"Enabled":true}}]},
               {"slot":{"key":"rubble","name":"Rubble01"},"components":[
                 {"key":"r1","type":"Test.Renderer","fields":{"Materials":[{{{Materials(first)}}}]{{{target}}} }},
                 {"key":"r2","type":"Test.Renderer","fields":{"Materials":[{{{Materials(second)}}}],"Target":"$ref:r1"}},
                 {"key":"source","type":"Test.Source","fields":{"Target":"$ref:r1"}}]}]}
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
            var (client, service, state, shrunk) = await ApplyRubbleAsync(name, RubbleWorld(name, ["m1", "m2", "m3"], "rubble", watcher: true));
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

    // Converged: no recreate is in progress, every renderer and Source in the world is bound to exactly one key, each
    // declared renderer holds the declared Materials, every Source points at a live Component or member and the managed
    // Source at the referenced key, every saved index matches the layout, and neither another apply nor an apply after a
    // world reload writes anything. Other types are not checked: a moved Component's source that an interrupted move leaves
    // behind is an existing upstream issue.
    private async Task AssertListShrinkConvergedAsync(FakeResoniteClient client, WorldService service, ApplyDocument document,
        string state, string referenced, IReadOnlyDictionary<string, string[]> expected, string context = "")
    {
        Assert.False(File.ReadAllText(state).Contains("supersededId", StringComparison.Ordinal), context + "a recreate is still in progress.");
        var keys = JsonNode.Parse(File.ReadAllText(state))!["components"]!.AsObject()
            .GroupBy(pair => pair.Value!["id"]!.GetValue<string>(), pair => pair.Key).ToDictionary(group => group.Key, group => group.Count());
        var live = AllSlots(client.Root).SelectMany(slot => slot.Components).ToDictionary(component => component.Id);
        foreach (var component in live.Values.Where(component => component.Type is "Test.Renderer" or "Test.Source"))
            Assert.True(keys.GetValueOrDefault(component.Id) == 1,
                $"{context}{component.Type} {component.Id} is bound to {keys.GetValueOrDefault(component.Id)} key(s).");
        foreach (var (key, materials) in expected)
            Assert.Equal(materials.Select(material => StateId(state, material)), MaterialTargets(live[StateId(state, key)]));
        var targets = live.Values.SelectMany(component => component.Members.Values.Select(member => member.Id).Append(component.Id))
            .OfType<string>().ToHashSet(StringComparer.Ordinal);
        foreach (var source in live.Values.Where(component => component.Type == "Test.Source"))
            Assert.True(source.Members["Target"].TargetId is { } target && targets.Contains(target),
                $"{context}Source {source.Id} points at a missing target.");
        Assert.Equal(StateId(state, referenced), live[StateId(state, "source")].Members["Target"].TargetId);
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
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AListThatDoesNotShrinkIsUpdatedInPlace|FullyQualifiedName~TheFakeClientCannotShrinkAList"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add tests/RLoop.Tests/ApplyWorkflowTests.cs tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit -m "test: model list members that ResoniteLink cannot shrink in the fake client" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 3 件とも PASS、全件も PASS（`RLoop.Tests` 340 件）。B のコミットは Task B8 で 2 件にまとめる。

### Task B2: state、縮小の検出、plan の表示、所有権の検査

**Files:**
- Modify: `src/RLoop.Core/ApplyWorkflow.cs`（`ApplyStateComponent`）
- Modify: `src/RLoop.Core/WorldService.cs`（`PlanApplyAsync`、`BuildComponentPlans`、`ListShrinkReason`、`ValidateComponentOwnership`、`CreateComponentState`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Produces: `ApplyStateComponent.SupersededId`（`string?`。null のときは書かない）。`ComponentRuntime` の `Superseded`（置き換え元の `ComponentSummary?`）、`SupersededId`、`RecreateReason`、`StateBeforeRecreate`（Task B3 で、置き換え先を作る直前に設定する）。`private static string? ListShrinkReason(ApplyComponentSpec spec, ComponentSummary existing)`（縮む list member があれば理由の文言、無ければ null）。plan の操作 `recreate`。所有権の検査の種類 `superseded`。作り直しは state に記録のある key に限る。state の `id` が空の key で縮小を検出したら、`STABLE_COMPONENT_AMBIGUOUS`（context は `candidateIds`・`type`・`componentKey`）で止める。

- [ ] **Step 1: テストを書く**

plan に `recreate` が出ること、syncObject の中のリストと移動する Component は作り直さないこと、置き換え元をほかの key が指していれば止まること、作成が中断して ID の無い key が型と位置で照合した Component を作り直さずに止まること（同じセッションと再読込後。key を state から外すと収束する）、`--adopt` の初回の plan に `recreate` が出ないことを確かめる。

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
        Assert.Contains("initialFields return to their declared values and undeclared members to their type defaults", recreate.Reason);
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

    // A key whose create was interrupted has no saved ID, so apply matches it by type and position only. A longer list there
    // may belong to unmanaged content, so apply stops instead of recreating (and removing) it, in this session and after a
    // reload. Keeping the content and dropping the key from the state lets apply create the key's Component.
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AKeyWithoutASavedIdNeverRecreatesAComponentMatchedByPosition(bool reload)
    {
        var name = "unsaved-id-" + reload;
        string World(bool extra) => RubbleWorld(name, "m1", "m2", "m3", "m4").Replace(
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""" +
            (extra ? """,{"key":"extra","type":"Test.Renderer","fields":{"Materials":["$ref:m1"]}}""" : ""), StringComparison.Ordinal);
        var (client, service, state, withExtra) = await ApplyRubbleAsync(name, World(true), World(false));
        client.FailOnWrite = 1; // creating extra fails after the state saved the key without an ID
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(withExtra, new ApplyOptions(state)));
        client.FailOnWrite = null;
        Assert.Equal("", StateId(state, "extra"));
        var rubble = AllSlots(client.Root).Single(slot => slot.Name == "Rubble01");
        await client.AddComponentAsync(rubble.Id, "Test.Renderer", new Dictionary<string, string>
            { ["Materials"] = JsonSerializer.Serialize(new[] { "m1", "m2", "m3", "m4" }.Select(key => StateId(state, key))) });
        if (reload) client.ReloadWorld("session-reloaded");
        client.ResetWriteCounts();

        var planError = await Assert.ThrowsAsync<RLoopException>(() => service.PlanApplyAsync(withExtra, new ApplyOptions(state)));
        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(withExtra, new ApplyOptions(state)));

        Assert.Equal("STABLE_COMPONENT_AMBIGUOUS", planError.Code);
        Assert.Equal("STABLE_COMPONENT_AMBIGUOUS", error.Code);
        Assert.Equal("extra", error.Context["componentKey"]);
        var unmanaged = RubbleRenderers(client)[1];
        Assert.Equal(unmanaged.Id, Assert.Single(Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["candidateIds"])));
        Assert.Equal(4, unmanaged.Members["Materials"].Elements!.Count);
        Assert.Equal(0, client.Writes);
        var checkpoint = JsonNode.Parse(File.ReadAllText(state))!;
        checkpoint["components"]!.AsObject().Remove("extra");
        File.WriteAllText(state, checkpoint.ToJsonString());
        await service.ApplyAsync(withExtra, new ApplyOptions(state));
        Assert.Equal(3, RubbleRenderers(client).Length);
        Assert.Equal(4, RubbleRenderers(client)[1].Members["Materials"].Elements!.Count);
        client.ResetWriteCounts();
        await service.ApplyAsync(withExtra, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

    // Like a move, a recreate needs a saved record, so the first adopting apply updates existing content in place.
    [Fact]
    public async Task TheFirstAdoptingApplyDoesNotRecreate()
    {
        var (client, service, _, shrunk) = await ApplyRubbleAsync("adopt-shrink", RubbleWorld("adopt-shrink", "m1", "m2", "m3"));

        var plan = await service.PlanApplyAsync(shrunk, new ApplyOptions(Path.Combine(_root, "adopt-shrink.adopted.state.json"), Adopt: true));

        Assert.Equal("update", Assert.Single(plan.Operations, operation => operation.Key == "renderer").Action);
        Assert.DoesNotContain(plan.Operations, operation => operation.Action == "recreate");
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~APlanShowsARecreate|FullyQualifiedName~AShorterListInsideASyncObject|FullyQualifiedName~AComponentMovedWithAShorterList|FullyQualifiedName~AnotherKeyClaimingTheReplaced|FullyQualifiedName~AKeyWithoutASavedIdNeverRecreates|FullyQualifiedName~TheFirstAdoptingApplyDoesNotRecreate" || true
```

Expected: 7 件のうち 4 件が FAIL。`APlanShowsARecreateWhenADeclaredListShrinks`（`recreate` が無い）、`AnotherKeyClaimingTheReplacedComponentStopsBeforeMutation`（衝突の種類が `live`）、`AKeyWithoutASavedIdNeverRecreatesAComponentMatchedByPosition` の 2 件（例外が出ない）。残りの 3 件（`AShorterListInsideASyncObjectIsNotRecreated`、`AComponentMovedWithAShorterListIsRelocatedNotRecreated`、`TheFirstAdoptingApplyDoesNotRecreate`）は今の挙動を固定するテストなので PASS。

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
    // The Component that a list-shrink recreate replaces, kept until apply removes it. Null when no recreate is in progress,
    // and then not written, so that a state without a recreate stays unchanged.
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
                // Like a move, a recreate needs a saved record: the first adopting apply updates existing content in place.
                var recreateReason = existing is null || stateComponent is null ? null : ListShrinkReason(spec, existing);
                // A key whose create was interrupted has no saved ID, so this Component was matched by type and position only.
                // It may be unmanaged content; never remove it as a replaced Component.
                if (recreateReason is not null && stateComponent?.Id is { Length: 0 })
                    throw new RLoopException("STABLE_COMPONENT_AMBIGUOUS",
                        $"Component '{stableKey}' has no saved ID, so it was matched by type and position only, and its list is longer than declared. Apply does not recreate a Component it cannot verify. No mutations were performed.",
                        ExitCodes.ValidationFailed,
                        new Dictionary<string, object?> { ["candidateIds"] = new[] { existing!.Id }, ["type"] = existing.Type, ["componentKey"] = stableKey },
                        ["If an interrupted apply created this Component, remove it with 'resoloop component remove ID --yes'; otherwise it is unmanaged content and should stay.",
                         $"Then back up the state file, remove components.{stableKey} from it, and re-run apply; apply creates the Component for this key."]);
                if (recreateReason is not null) (superseded, existing) = (existing, null);
                var componentIndex = existing is null
                    ? (node.Existing?.Components.Count ?? 0) + prepared.Components.Count(candidate => candidate.Node == node && candidate.Existing is null)
                    : node.Existing!.Components.ToList().FindIndex(candidate => candidate.Id == existing.Id);
                var runtime = new ComponentRuntime(spec, node, existing, stableKey, ordinal,
                    node.Path + "/@" + (spec.Key ?? normalizedType + "[" + ordinal + "]"), componentIndex)
                {
                    Superseded = superseded,
                    SupersededId = superseded?.Id,
                    RecreateReason = recreateReason
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
            "; ResoniteLink cannot remove list elements, so apply replaces the Component (initialFields return to their declared values and undeclared members to their type defaults)";
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
        // The saved record just before this apply creates the replacement, after the asset phase forgot the evidence of
        // re-imported assets; restored if the replacement does not converge.
        public ApplyStateComponent? StateBeforeRecreate { get; set; }
```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~APlanShowsARecreate|FullyQualifiedName~AShorterListInsideASyncObject|FullyQualifiedName~AComponentMovedWithAShorterList|FullyQualifiedName~AnotherKeyClaimingTheReplaced|FullyQualifiedName~AKeyWithoutASavedIdNeverRecreates|FullyQualifiedName~TheFirstAdoptingApplyDoesNotRecreate"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Plan a recreate when a declared list member shrinks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 7 件とも PASS、全件も PASS（`RLoop.Tests` 347 件）。

### Task B3: 1 回の apply での作り直し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`ApplyAsync` の Component の段階・新しい検証の段階・新しい置き換え元の削除の段階、`DetectSavedAssetMigrations`、新しい `VerifyReplacementsAsync`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task A2 の `SaveSlotIndexesAsync`、Task B2 の `ComponentRuntime` のプロパティ
- Produces: `ComponentRuntime.ReplacementCreated`（この apply が置き換え先を作った）、`ComponentRuntime.AwaitsVerification`（置き換え元が残っている間は true。その間、置き換え先は全件の検証が通るまで参照先にしない）、`private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates, Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey, IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)`（この時点では書き込みだけ。検証待ちの置き換え先を参照しないフィールドだけを書き、すべて書いた後に置き換え先を `byKey` に加える。Task B4 で読み直しと取り消しを加え、引数に `ApplyCounts counts` が増える）、`private static bool ReferencesComponentKeys(JsonElement value, IReadOnlySet<string> keys, string? self)`。作成時は検証待ちの置き換え先（作る Component 自身を含む）への参照だけを除いて書き、作成前・作成後の checkpoint には作成時に書いた参照の selector だけを保存する。`StateBeforeRecreate` は置き換え先を作る直前（アセットの段階の後）に控える。

- [ ] **Step 1: テストを書く**

作り直しと参照の張り替え、アセットの移行、Review Focus の 1・2・4・5、互いを参照する 2 つの作り直しが 1 回の apply で収束すること、自分の key を参照する作り直しでも参照以外の `initialFields` が作成時に渡ることを確かめる。

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

    // The index save after removing the replaced Component is covered by ShrinkingAListRecreatesTheComponentAndRepointsManagedReferences
    // and ARecreateInterruptedAtAnyWriteConvergesInTheSameSession; the later prune also rewrites these indexes.
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

    // Each recreated renderer points at the other. No replacement is a reference target until both pass, so the fields
    // phase writes both references, and the apply converges at once.
    [Fact]
    public async Task RecreatedComponentsThatReferenceEachOtherConvergeInOneApply()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("mutual", PointingRenderersWorld("mutual", 3, 2, mutual: true),
            PointingRenderersWorld("mutual", 4, 3, mutual: true));

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "r1",
            new Dictionary<string, string[]> { ["r1"] = ["m1", "m2", "m3"], ["r2"] = ["m1", "m2"] });
        var renderers = RubbleRenderers(client).ToDictionary(component => component.Id);
        Assert.Equal(StateId(state, "r2"), renderers[StateId(state, "r1")].Members["Target"].TargetId);
        Assert.Equal(StateId(state, "r1"), renderers[StateId(state, "r2")].Members["Target"].TargetId);
    }

    // A recreate that references its own key defers that reference like any other pending replacement, so the rest of
    // its initialFields still go to AddComponentAsync. Without that, a self-reference leaves every create field
    // unresolved and the replacement is created with none of them.
    [Fact]
    public async Task ARecreateReferencingItselfKeepsItsOtherInitialFields()
    {
        static string World(params string[] materials) => RubbleWorld("self-recreate", materials).Replace(
            """{"key":"renderer","type":"Test.Renderer","fields":{"Materials""",
            """{"key":"renderer","type":"Test.Renderer","initialFields":{"Enabled":true},"fields":{"Target":"$ref:renderer","Materials""",
            StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("self-recreate", World("m1", "m2", "m3"),
            World("m1", "m2", "m3", "m4"));
        var original = RubbleRenderers(client).Single().Id;
        client.LoseResponseOnWrite = 1; // the replacement's create lands, and its response is lost
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.LoseResponseOnWrite = null;

        var created = RubbleRenderers(client).Single(renderer => renderer.Id != original);
        Assert.True(created.Members["Enabled"].Value!.GetValue<bool>());
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ShrinkingAListRecreates|FullyQualifiedName~ARecreateKeepsAnAssetUrl|FullyQualifiedName~ARecreatedComponentWithIdentityFields|FullyQualifiedName~AMemberReferenceToARecreated|FullyQualifiedName~APruneAndARecreateOnOneSlot|FullyQualifiedName~ARecreateSetsInitialFieldsAgain|FullyQualifiedName~RecreatedComponentsThatReferenceEachOther|FullyQualifiedName~ARecreateReferencingItself" || true
```

Expected: 9 件とも FAIL。主な失敗は、置き換え元が削除されず Slot に同じ型の Component が残る、`legacyState: True` で例外が出ない、互いを参照する 2 つが収束しない、自己参照のある作り直しが始まらない、など。

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
            // A recreate's replacement is not a reference target until every replacement is verified.
            var byKey = prepared.Components.Where(x => !string.IsNullOrWhiteSpace(x.Spec.Key) && x.Existing is not null && !x.AwaitsVerification)
                .ToDictionary(x => x.Spec.Key!, x => x, StringComparer.Ordinal);
            var awaitingKeys = prepared.Components.Where(x => x.AwaitsVerification)
                .Select(x => x.Spec.Key).OfType<string>().ToHashSet(StringComparer.Ordinal);
            var slotsByKey = prepared.Nodes.ToDictionary(x => x.StableKey, StringComparer.Ordinal);
            foreach (var component in prepared.Components)
            {
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    var createFields = MergeCreateFields(component.Spec);
                    if (CanResolveAll(createFields, byKey, slotsByKey))
```

置き換え後:

```csharp
                    var createFields = MergeCreateFields(component.Spec);
                    // Leave out only the references to replacements that are not verified yet; the fields phase writes
                    // them. A recreate awaiting verification is itself pending, so self-references are deferred too.
                    var withoutPending = createFields.Where(field => !ReferencesComponentKeys(field.Value, awaitingKeys,
                            component.AwaitsVerification ? null : component.Spec.Key))
                        .ToDictionary(field => field.Key, field => field.Value, StringComparer.Ordinal);
                    if (withoutPending.Count < createFields.Count && CanResolveAll(withoutPending, byKey, slotsByKey)) createFields = withoutPending;
                    if (CanResolveAll(createFields, byKey, slotsByKey))
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
                    // A new Component may be created even if its response is lost. Its old source's
                    // declarations cannot prove which asset the replacement's fields now contain.
```

追加する内容:

```csharp
                    // The asset phase may already have forgotten evidence for re-imported assets; an undo must keep that.
                    if (component.RecreateReason is not null)
                        component.StateBeforeRecreate = prepared.State.Components.GetValueOrDefault(component.StableKey);
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
            // Every managed reference now points at the replacements. Remove each replaced Component, then save the
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
    // Write each replacement's declared fields before any managed reference moves to it.
    private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates,
        Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey,
        IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)
    {
        // A recreate whose replaced Component is already gone has nothing left to verify or undo.
        foreach (var component in recreates.Where(component => component.AwaitsVerification))
        {
            cancellationToken.ThrowIfCancellationRequested();
            // No replacement, this one included, is a reference target until every replacement is written, so the fields
            // that reference one are left to the fields phase.
            var resolvable = MergeCreateFields(component.Spec).Where(field => CanResolve(field.Value, byKey, slotsByKey))
                .ToDictionary(field => field.Key, field => field.Value, StringComparer.Ordinal);
            var fields = await ResolveFieldsAsync(resolvable, byKey, slotsByKey, assetUrls, cancellationToken);
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
        // Every replacement is written, so the fields phase may point references at them.
        foreach (var component in recreates.Where(component => component.AwaitsVerification && !string.IsNullOrWhiteSpace(component.Spec.Key)))
            byKey[component.Spec.Key!] = component;
    }

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直前に追加する。

```csharp
    private static bool TryResolveRawForPlan(JsonElement value,
```

追加する内容:

```csharp
    // Whether the value references one of these Component keys other than the Component's own key.
    private static bool ReferencesComponentKeys(JsonElement value, IReadOnlySet<string> keys, string? self) => value.ValueKind switch
    {
        JsonValueKind.String => StableSelectorSyntax.TryParse(value.GetString() ?? string.Empty, out var stable) &&
            stable!.Kind is "component" or "member" && stable.Key != self && keys.Contains(stable.Key),
        JsonValueKind.Array => value.EnumerateArray().Any(item => ReferencesComponentKeys(item, keys, self)),
        JsonValueKind.Object => value.EnumerateObject().Any(property => ReferencesComponentKeys(property.Value, keys, self)),
        _ => false
    };

```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
        var referenceSelectors = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var name in memberNames)
            if (TryGetReferenceSelector(component.Spec, name, out var selector)) referenceSelectors[name] = selector;
```

置き換え後:

```csharp
        // Until its fields are written, a Component this apply creates has only the references its create wrote. Matching it by
        // one it does not have yet would miss it after a lost create response, and the re-run would create another.
        var written = component.Existing is null && resolvedFields is null ? component.AppliedOnCreate ?? new Dictionary<string, string>() : null;
        var referenceSelectors = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var name in memberNames)
            if ((written is null || written.ContainsKey(name)) && TryGetReferenceSelector(component.Spec, name, out var selector))
                referenceSelectors[name] = selector;
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分の直後に追加する。

```csharp
        public ApplyStateComponent? StateBeforeRecreate { get; set; }
```

追加する内容:

```csharp
        // True once this apply has created the replacement.
        public bool ReplacementCreated { get; set; }
        // While the replaced Component is still on the Slot, its replacement is not a reference target until verified.
        public bool AwaitsVerification => SupersededId is not null && Superseded is not null;
```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ShrinkingAListRecreates|FullyQualifiedName~ARecreateKeepsAnAssetUrl|FullyQualifiedName~ARecreatedComponentWithIdentityFields|FullyQualifiedName~AMemberReferenceToARecreated|FullyQualifiedName~APruneAndARecreateOnOneSlot|FullyQualifiedName~ARecreateSetsInitialFieldsAgain|FullyQualifiedName~RecreatedComponentsThatReferenceEachOther|FullyQualifiedName~ARecreateReferencingItself"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Recreate a Component with a shrinking list within one apply" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 9 件とも PASS、全件も PASS（`RLoop.Tests` 356 件）。

### Task B4: 検証の失敗と取り消し

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`VerifyReplacementsAsync` とその呼び出し）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B3 の `VerifyReplacementsAsync`
- Produces: `VerifyReplacementsAsync` の引数に `ApplyCounts counts` を追加。宣言より長いリストが残れば、失敗した key と、この apply で作った置き換え先を取り消して `APPLY_LIST_SHRINK_NOT_CONVERGED`（7）を投げる。全件が通ったときだけ置き換え先を `byKey` に加える。context は `failures`（key・メンバー・宣言と実機の要素数）、`undone`、`inProgress`（再開して検証を通ったので残した key）。投げる前に、置き換え元がすでに無い key（`SupersededId is not null && Superseded is null`）は、段階 5 と同じく `SaveSlotIndexesAsync` → `supersededId` を消す → checkpoint で記録を片付ける（削除はしない。検証も取り消しの対象にもならない key の `supersededId` を残すと、再読込のあとの apply が `session-changed` で止まる）。`inProgress` には入れない。

- [ ] **Step 1: テストを書く**

1 つ目は、同じ apply で作った Component（`watcher`）が、取り消した置き換え先を指さないこと、`initialFields` が失われないこと、置き換え先の後ろに作った Component の index も取り消しの後に保存し直すことも確かめる。3 つ目は、取り消しで戻す state が、アセットの段階で消した根拠を復活させないことを確かめる。4 つ目は、値のリストも作り直しになり、詰め直されると取り消すことを確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    [Fact]
    public async Task AReplacementThatTheRuntimeRefillsIsUndone()
    {
        // 'extra' is created after the replacement in the same apply, so undoing the replacement moves it, and the undo must
        // save the indexes on its Slot again.
        var (client, service, state, shrunk) = await ApplyRubbleAsync("refilled",
            RubbleWorld("refilled", ["m1", "m2", "m3"], "rubble", watcher: true).Replace(
                """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
                """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}},{"key":"extra","type":"Test.Indexed","fields":{"Value":3}}""",
                StringComparison.Ordinal));
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
        // The watcher created in the same apply never pointed at the removed replacement.
        Assert.All(Sources(client), source => Assert.True(source.Members["Target"].TargetId is null || source.Members["Target"].TargetId == original));
        AssertSavedIndexesMatchLayout(client, state);

        client.RefillListsTo = null;
        await service.ApplyAsync(shrunk, new ApplyOptions(state));
        // The watcher was created with its initial values, which apply never writes again.
        Assert.True(Sources(client).Single(source => source.Id == StateId(state, "watcher")).Members["Enabled"].Value!.GetValue<bool>());
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
        Assert.Equal(originals[0], Sources(client).Single(source => source.Id == StateId(state, "source")).Members["Target"].TargetId);
        Assert.DoesNotContain("supersededId", File.ReadAllText(state));
        AssertSavedIndexesMatchLayout(client, state);
    }

    // An undo restores the record from just before the replacement was created. Evidence that the asset phase forgot for a
    // re-imported asset stays forgotten, so a world save cannot make a later apply adopt the old asset's URL; evidence that
    // nothing forgot stays, so the saved URL is adopted.
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AnUndoKeepsTheAssetEvidenceThatThisApplyForgot(bool reimported)
    {
        await File.WriteAllTextAsync(Path.Combine(_root, "crate.bin"), "first crate");
        var name = "undo-asset-" + reimported;
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
        if (reimported) await File.WriteAllTextAsync(Path.Combine(_root, "crate.bin"), "second crate");
        client.RefillListsTo = 2;

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        var assetFields = JsonNode.Parse(File.ReadAllText(state))!["components"]!["holder"]!["assetFields"]!.AsObject();
        Assert.Equal(!reimported, assetFields.ContainsKey("URL"));
        // A world save moves the original Component's URL to resdb.
        var holder = AllSlots(client.Root).Single(slot => slot.Name == "Crate").Components.Single();
        holder.Members["URL"] = holder.Members["URL"] with { Value = JsonValue.Create("resdb:///saved-crate") };
        client.ReloadWorld("session-saved");
        client.RefillListsTo = null;
        await service.ApplyAsync(shrunk, new ApplyOptions(state));
        var expected = reimported ? "local://machine/asset-2" : "resdb:///saved-crate";
        Assert.Equal(expected, AllSlots(client.Root).Single(slot => slot.Name == "Crate").Components.Single().Members["URL"].Value!.GetValue<string>());
        Assert.Equal(expected, StateAsset(state, "mesh")["url"]!.GetValue<string>());
    }

    // ResoniteLink applies a list of values the same way as a list of references, so a shorter list of values is recreated
    // too, and a replacement whose values the runtime refills is undone.
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AShorterListOfValuesIsRecreatedLikeAListOfReferences(bool refilled)
    {
        var name = "value-list-" + refilled;
        string World(params int[] weights) => $$$"""
            {"schemaVersion":"1","ownership":{"key":"{{{name}}}"},"slot":{"key":"root","name":"Weights","parent":"Root"},
             "components":[{"key":"blend","type":"Test.Blend","fields":{"Weights":[{{{string.Join(",", weights)}}}]}}]}
            """;
        var initial = ReloadDocument(name, World(1, 2, 3));
        var shrunk = ReloadDocument(name + "-shrunk", World(1, 2));
        var client = new FakeResoniteClient(initial);
        client.ListMembers.Add("Weights");
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(initial, new ApplyOptions(state));
        var original = client.Root.Children.Single().Components.Single().Id;
        client.RefillListsTo = refilled ? 3 : null;

        var plan = await service.PlanApplyAsync(shrunk, new ApplyOptions(state));
        var error = await Record.ExceptionAsync(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("recreate", Assert.Single(plan.Operations, operation => operation.Key == "blend").Action);
        var blend = client.Root.Children.Single().Components.Single();
        if (refilled)
        {
            Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", Assert.IsType<RLoopException>(error).Code);
            Assert.Equal(original, blend.Id);
            return;
        }
        Assert.Null(error);
        Assert.NotEqual(original, blend.Id);
        Assert.Equal(new[] { 1.0, 2.0 }, blend.Members["Weights"].Elements!.Select(element => element.Value!.GetValue<double>()));
        client.ResetWriteCounts();
        await service.ApplyAsync(shrunk, new ApplyOptions(state));
        Assert.Equal(0, client.Writes);
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AReplacementThatTheRuntimeRefillsIsUndone|FullyQualifiedName~EveryReplacementThisApplyCreatedIsUndone|FullyQualifiedName~AnUndoKeepsTheAssetEvidence|FullyQualifiedName~AShorterListOfValuesIsRecreated" || true
```

Expected: 6 件のうち 5 件が FAIL。`error.Code` が `APPLY_REFERENCE_NOT_RETAINED` になり（値のリストでは例外が出ず）、`APPLY_LIST_SHRINK_NOT_CONVERGED` にならない。`AShorterListOfValuesIsRecreatedLikeAListOfReferences(refilled: False)` は Task B3 の実装で通るので PASS。

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
    // Write each replacement's declared fields before any managed reference moves to it.
    private async Task VerifyReplacementsAsync(PreparedApply prepared, IReadOnlyList<ComponentRuntime> recreates,
        Dictionary<string, ComponentRuntime> byKey, IReadOnlyDictionary<string, NodeRuntime> slotsByKey,
        IReadOnlyDictionary<string, string> assetUrls, CancellationToken cancellationToken)
    {
        // A recreate whose replaced Component is already gone has nothing left to verify or undo.
        foreach (var component in recreates.Where(component => component.AwaitsVerification))
        {
            cancellationToken.ThrowIfCancellationRequested();
            // No replacement, this one included, is a reference target until every replacement is written, so the fields
            // that reference one are left to the fields phase.
            var resolvable = MergeCreateFields(component.Spec).Where(field => CanResolve(field.Value, byKey, slotsByKey))
                .ToDictionary(field => field.Key, field => field.Value, StringComparer.Ordinal);
            var fields = await ResolveFieldsAsync(resolvable, byKey, slotsByKey, assetUrls, cancellationToken);
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
        // Every replacement is written, so the fields phase may point references at them.
        foreach (var component in recreates.Where(component => component.AwaitsVerification && !string.IsNullOrWhiteSpace(component.Spec.Key)))
            byKey[component.Spec.Key!] = component;
    }

```

置き換え後:

```csharp
    // Write each replacement's declared fields and read it back before any managed reference moves to it. Runtime
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
            // No replacement, this one included, is a reference target until every replacement passes, so the fields that
            // reference one are left to the fields phase.
            var resolvable = MergeCreateFields(component.Spec).Where(field => CanResolve(field.Value, byKey, slotsByKey))
                .ToDictionary(field => field.Key, field => field.Value, StringComparer.Ordinal);
            var fields = await ResolveFieldsAsync(resolvable, byKey, slotsByKey, assetUrls, cancellationToken);
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
        if (failures.Count == 0)
        {
            // Every replacement passed, so the fields phase may point references at them.
            foreach (var component in recreates.Where(component => component.AwaitsVerification && !string.IsNullOrWhiteSpace(component.Spec.Key)))
                byKey[component.Spec.Key!] = component;
            return;
        }

        // Nothing references a replacement this apply created, not even another replacement, so removing it cannot leave a
        // dangling reference. A resumed replacement that passed stays, because an earlier apply may already have moved
        // references to it.
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
        // A resumed recreate whose replaced Component is already gone is verified by nothing and undone by nothing.
        // Settle its record the way the removal stage does, or the stranded supersededId stops the next apply after a
        // reload with session-changed.
        foreach (var component in recreates.Where(component => component.Superseded is null && component.SupersededId is not null))
        {
            cancellationToken.ThrowIfCancellationRequested();
            await SaveSlotIndexesAsync(prepared, component.Node.StableKey, component.Node.Id!, cancellationToken);
            component.SupersededId = null;
            prepared.State.Components[component.StableKey] = prepared.State.Components[component.StableKey] with { SupersededId = null };
            Checkpoint(prepared);
        }
        var inProgress = recreates.Where(component => component.AwaitsVerification && !undone.Contains(component))
            .Select(component => component.StableKey).ToArray();
        throw new RLoopException("APPLY_LIST_SHRINK_NOT_CONVERGED",
            "The runtime kept a list longer than declared on a replacement Component, so recreating it cannot converge. The undone replacements were removed and their original Components are unchanged.",
            ExitCodes.OperationFailed, new Dictionary<string, object?>
            {
                ["failures"] = failures.Select(failure => new
                {
                    componentKey = failure.Component.StableKey, member = failure.Member,
                    declared = failure.Declared, observed = failure.Observed
                }).ToArray(),
                ["undone"] = undone.Select(component => component.StableKey).ToArray(),
                // Resumed recreates that passed keep their replacements and stay in progress.
                ["inProgress"] = inProgress
            },
            new[] { "Declare the list length that the runtime keeps, or find what refills the list.",
                    "Re-run apply only after changing the declaration; re-running the same command recreates and undoes the Component again. The undone keys have no recreate in progress." }
                .Concat(inProgress.Length == 0 ? Array.Empty<string>() :
                    [$"The recreate of '{string.Join("', '", inProgress)}' stays in progress. Finish it by re-running apply in this session; after a world reload, apply stops with APPLY_RECREATE_INTERRUPTED."])
                .ToArray());
    }

```

- [ ] **Step 4: 成功することを確かめてコミットする**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AReplacementThatTheRuntimeRefillsIsUndone|FullyQualifiedName~EveryReplacementThisApplyCreatedIsUndone|FullyQualifiedName~AnUndoKeepsTheAssetEvidence|FullyQualifiedName~AShorterListOfValuesIsRecreated"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Undo replacements whose list does not converge" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 6 件とも PASS、全件も PASS（`RLoop.Tests` 362 件）。

### Task B5: 中断した作り直しの再開と停止

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`PrepareAsync`、`BuildComponentPlans`、`RecreatePlanReason`、新しい `ThrowIfRecreateInterruptedAcrossSessions`・`ValidateInterruptedRecreates`・`RecreateInterrupted`、`ComponentRuntime`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B2〜B4
- Produces: `ComponentRuntime.Resumed`。`private static string RecreatePlanReason(ComponentRuntime component)`（再開の理由を含む）。`APPLY_RECREATE_INTERRUPTED`（6。reason は `session-changed`・`key-not-declared`・`declaration-shrank`・`replacement-unverified`）。context は `reason`・`stateFile`・`componentKey`・`slotKey`・`slotPath`・`type`・`supersededId`・`savedId`・`candidates`（`id`、list メンバーごとの要素数 `lists`、`referencedBy`）。`private static object[] ReferencesTo(PreparedApply prepared, ComponentSummary target)`（apply が読んだ範囲で、その Component かそのメンバーを参照している Component）。途中の作り直しの key は、別の Slot へ移しても移動元で照合しない。置き換え元がすでに無い再開の key は、宣言がさらに短ければ新しい作り直しになる。

- [ ] **Step 1: テストを書く**

Review Focus の 3 を含む。作り直しの途中で宣言をさらに短くした場合、再開した置き換え先と取り消す置き換え先の参照、フィールドを書かずに作った置き換え先の再開、取り消しの途中の中断、管理外の同じ型の Component、同じ Slot から移動する同じ型の Component、同じ apply で作る参照元の作成応答の喪失、置き換え元がすでに無い再開の key がほかの key の検証失敗で止まる前に記録を片付けることも確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    // An interrupted recreate resumes only while the document declares the key on the same Slot. It never matches the key
    // by type or position on its old Slot, even beside a same-type sibling. Declaring the key there again finishes it.
    [Theory]
    [InlineData("undeclared")]
    [InlineData("moved")]
    [InlineData("moved-beside-a-sibling")]
    public async Task ARecreateInterruptedBeforeTheKeyLeavesItsSlotStops(string change)
    {
        var name = "leaves-" + change;
        var sibling = change == "moved-beside-a-sibling";
        var key = sibling ? "r1" : "renderer";
        var (client, service, state, shrunk) = sibling
            ? await ApplyRubbleAsync(name, TwoRendererWorld(name, ["m1", "m2", "m3"], ["m1", "m2", "m3"]),
                TwoRendererWorld(name, ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3"]))
            : await ApplyRubbleAsync(name, RubbleWorld(name, "m1", "m2", "m3"));
        client.FailOnWrite = 1; // creating the replacement fails after state saved supersededId
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        const string r1 = """{"key":"r1","type":"Test.Renderer","fields":{"Materials":["$ref:m1","$ref:m2","$ref:m3"]}}""";
        var changed = ReloadDocument(name + "-changed", change switch
        {
            "undeclared" => RubbleWorld(name, [], rendererSlot: null),
            "moved" => RubbleWorld(name, ["m1", "m2", "m3"], rendererSlot: "elsewhere"),
            _ => TwoRendererWorld(name, ["m1", "m2", "m3"], ["m1", "m2", "m3"]).Replace(r1 + ",", "", StringComparison.Ordinal).Replace(
                """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:r1"}}]}""",
                """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:r1"}}]},{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[""" + r1 + "]}",
                StringComparison.Ordinal)
        });
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(changed, new ApplyOptions(state)));

        Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
        Assert.Equal(ExitCodes.ValidationFailed, error.ExitCode);
        Assert.Equal("key-not-declared", error.Context["reason"]);
        Assert.Equal(key, error.Context["componentKey"]);
        Assert.Equal(0, client.Writes);
        // The suggested recovery: declare the key on its Slot again to finish the recreate, then remove it with --prune.
        await service.ApplyAsync(shrunk, new ApplyOptions(state));
        Assert.DoesNotContain("supersededId", File.ReadAllText(state));
        if (sibling) return;
        var removed = ReloadDocument(name + "-removed", RubbleWorld(name, [], rendererSlot: null));
        await service.ApplyAsync(removed, new ApplyOptions(state, Prune: true, ConfirmDeletes: true));
        Assert.Empty(RubbleRenderers(client));
    }

    [Theory]
    [InlineData("create")]
    [InlineData("remove")]
    [InlineData("removed")]
    public async Task APlanDuringAnInterruptedRecreateExplainsHowItResumes(string failedStep)
    {
        var name = "resume-plan-" + failedStep;
        var (client, service, state, shrunk) = await ApplyRubbleAsync(name, RubbleWorld(name, "m1", "m2", "m3"));
        var original = RubbleRenderers(client).Single().Id;
        if (failedStep == "create") client.FailOnWrite = 1;
        else if (failedStep == "remove") client.FailRemovingComponent = original;
        else client.LoseResponseOnWrite = 3; // removing the replaced Component lands, and its response is lost
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        client.FailRemovingComponent = null;
        client.LoseResponseOnWrite = null;
        client.ResetWriteCounts();
        var checkpoint = File.ReadAllBytes(state);

        var plan = await service.PlanApplyAsync(shrunk, new ApplyOptions(state));

        var recreate = Assert.Single(plan.Operations, operation => operation.Action == "recreate");
        Assert.StartsWith("resumes an interrupted recreate:", recreate.Reason);
        Assert.Contains(failedStep switch
        {
            "create" => "creates the replacement",
            "remove" => $"removes the replaced Component '{original}'",
            _ => "the replaced Component is already removed"
        }, recreate.Reason);
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
        Assert.Equal(["r1"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["inProgress"]));
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

    // A replacement that something already references cannot shrink in place and must not be undone, so a declaration that
    // became shorter during the recreate stops before mutation. Finishing the recreate first, then shortening, converges.
    [Fact]
    public async Task AShorterDeclarationStopsWhileSomethingReferencesTheResumedReplacement()
    {
        var (client, service, state, three) = await ApplyRubbleAsync("shrank-again", RubbleWorld("shrank-again", "m1", "m2", "m3"));
        client.FailRemovingComponent = RubbleRenderers(client).Single().Id; // the Source already points at the replacement
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        client.FailRemovingComponent = null;
        var two = ReloadDocument("shrank-again-two", RubbleWorld("shrank-again", "m1", "m2"));
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(two, new ApplyOptions(state)));

        Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
        Assert.Equal("declaration-shrank", error.Context["reason"]);
        Assert.Equal(0, client.Writes);
        var target = Sources(client).Single(source => source.Id == StateId(state, "source")).Members["Target"].TargetId;
        Assert.Contains(RubbleRenderers(client), renderer => renderer.Id == target);
        await service.ApplyAsync(three, new ApplyOptions(state));
        await service.ApplyAsync(two, new ApplyOptions(state));
        await AssertListShrinkConvergedAsync(client, service, two, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2"] });
    }

    // When the replaced Component is already gone, a declaration that shrank again starts a new recreate from the replacement.
    [Fact]
    public async Task AShorterDeclarationAfterTheReplacedComponentIsGoneRecreatesAgain()
    {
        var (client, service, state, three) = await ApplyRubbleAsync("shrank-after-removal", RubbleWorld("shrank-after-removal", "m1", "m2", "m3"));
        client.LoseResponseOnWrite = 3; // writes: the replacement, the Source, then the removal of the replaced Component
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(three, new ApplyOptions(state)));
        client.LoseResponseOnWrite = null;
        Assert.Single(RubbleRenderers(client));
        Assert.Contains("supersededId", File.ReadAllText(state));
        var two = ReloadDocument("shrank-after-removal-two", RubbleWorld("shrank-after-removal", "m1", "m2"));

        await service.ApplyAsync(two, new ApplyOptions(state));

        await AssertListShrinkConvergedAsync(client, service, two, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2"] });
    }

    // r2 points at r1. r2's recreate resumes after its replaced Component failed to go and its replacement passes again;
    // r1's new replacement does not converge and is undone. r2's replacement never pointed at r1's replacement.
    [Fact]
    public async Task AResumedReplacementNeverPointsAtAnUndoneReplacement()
    {
        var (client, service, state, shrinkSecond) = await ApplyRubbleAsync("resumed-target", PointingRenderersWorld("resumed-target", 4, 3),
            PointingRenderersWorld("resumed-target", 4, 4));
        var r1 = StateId(state, "r1");
        client.FailRemovingComponent = StateId(state, "r2"); // r2's recreate stops after its replacement passed
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrinkSecond, new ApplyOptions(state)));
        client.FailRemovingComponent = null;
        var shrinkBoth = ReloadDocument("resumed-target-both", PointingRenderersWorld("resumed-target", 2, 3));
        client.RefillListsTo = 3; // r1's new replacement cannot shrink to 2; r2's replacement keeps 3 as declared

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Equal(["r1"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        Assert.Equal(["r2"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["inProgress"]));
        Assert.Equal(r1, RubbleRenderers(client).Single(renderer => renderer.Id == StateId(state, "r2")).Members["Target"].TargetId);
        client.RefillListsTo = null;
        await service.ApplyAsync(shrinkBoth, new ApplyOptions(state));
        await AssertListShrinkConvergedAsync(client, service, shrinkBoth, state, "r1",
            new Dictionary<string, string[]> { ["r1"] = ["m1", "m2"], ["r2"] = ["m1", "m2", "m3"] });
    }

    // r1 references a Component that the same apply creates later, so its replacement is created without initial values and
    // first written when a later apply resumes it; that apply must read it back too.
    [Fact]
    public async Task AResumedReplacementIsReadBackAfterItsFieldsAreFirstWritten()
    {
        var (client, service, state, shrunk, _, _) = await ApplyScenarioAsync("written-on-resume", "shared-slot");
        var originals = RubbleRenderers(client).Select(component => component.Id).Order(StringComparer.Ordinal).ToArray();
        client.FailOnWrite = 4; // writes: the Elsewhere and Late Slots, r1's replacement, then r2's replacement
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        Assert.Empty(RubbleRenderers(client).Single(component => component.Id == StateId(state, "r1")).Members["Materials"].Elements!);
        client.RefillListsTo = 4;

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Contains("r1", Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        Assert.Equal(originals, RubbleRenderers(client).Select(component => component.Id).Order(StringComparer.Ordinal));
        Assert.DoesNotContain("supersededId", File.ReadAllText(state));
    }

    // Stops the undo at each of its two removals. The next apply resumes what it can, undoes r2 again, and once the runtime
    // stops refilling the list, the recreates finish.
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AnUndoInterruptedAtEitherRemovalResumesOnTheNextApply(bool responseLost)
    {
        for (var removal = 1; removal <= 2; removal++)
        {
            var name = $"undo-interrupted-{responseLost}-{removal}";
            var first = ReloadDocument(name, TwoRendererWorld(name, ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3"]));
            var shrinkBoth = ReloadDocument(name + "-both", TwoRendererWorld(name, ["m1", "m2", "m3"], ["m1", "m2"]));
            var client = new FakeResoniteClient(first);
            var service = new WorldService(client);
            var state = Path.Combine(_root, name + ".state.json");
            await service.ApplyAsync(first, new ApplyOptions(state));
            client.RefillListsTo = 3; // r1's replacement keeps 3 as declared, r2's replacement cannot shrink to 2
            client.ResetWriteCounts();
            // Writes 1 and 2 create the replacements, and the undo removes them with writes 3 and 4.
            if (responseLost) client.LoseResponseOnWrite = 2 + removal;
            else client.FailOnWrite = 2 + removal;
            await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));
            client.LoseResponseOnWrite = null;
            client.FailOnWrite = null;

            var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));

            Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
            Assert.Contains("r2", Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
            AssertSavedIndexesMatchLayout(client, state);
            client.RefillListsTo = null;
            await service.ApplyAsync(shrinkBoth, new ApplyOptions(state));
            await AssertListShrinkConvergedAsync(client, service, shrinkBoth, state, "r1",
                new Dictionary<string, string[]> { ["r1"] = ["m1", "m2", "m3"], ["r2"] = ["m1", "m2"] }, $"removal {removal}: ");
        }
    }

    // A Component that no key owns may be the replacement whose create response was lost, so apply stops without changing
    // it, even when the replacement never landed. The lists do not tell them apart either: an empty one also looks like a
    // replacement created without initial values.
    [Fact]
    public async Task AnUnmanagedSameTypeComponentStopsAResumeWithoutBeingChanged()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("unmanaged-candidate", RubbleWorld("unmanaged-candidate", "m1", "m2", "m3"));
        var rubble = AllSlots(client.Root).Single(slot => slot.Name == "Rubble01");
        var unmanaged = await client.AddComponentAsync(rubble.Id, "Test.Renderer", new Dictionary<string, string>());
        client.ResetWriteCounts();
        client.FailOnWrite = 1; // creating the replacement fails before it lands
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("replacement-unverified", error.Context["reason"]);
        var candidate = Assert.Single(JsonSerializer.SerializeToNode(error.Context["candidates"])!.AsArray())!;
        Assert.Equal(unmanaged.Id, candidate["id"]!.GetValue<string>());
        Assert.Equal(0, candidate["lists"]!["Materials"]!.GetValue<int>());
        Assert.Equal(0, client.Writes);
        Assert.Contains(RubbleRenderers(client), component => component.Id == unmanaged.Id);
    }

    // A same-type Component moving to another Slot leaves its old instance on the Slot until apply removes it. Its key owns
    // that instance, so it is never taken for a replacement whose create did not land.
    [Fact]
    public async Task AMovingSameTypeComponentIsNotTakenForALostReplacement()
    {
        const string wanderer = """{"key":"wanderer","type":"Test.Renderer","fields":{"Materials":["$ref:m1"]}}""";
        const string source = """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""";
        static string World(bool moved, params string[] materials) => moved
            ? RubbleWorld("moving-sibling", materials).Replace(source + "]}",
                source + """]},{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[""" + wanderer + "]}", StringComparison.Ordinal)
            : RubbleWorld("moving-sibling", materials).Replace(source, source + "," + wanderer, StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("moving-sibling", World(true, "m1", "m2", "m3"),
            World(false, "m1", "m2", "m3", "m4"));
        client.FailOnWrite = 2; // writes: the Elsewhere Slot, then the replacement, whose create fails before it lands
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.FailOnWrite = null;
        Assert.Equal(2, RubbleRenderers(client).Length);

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
        Assert.Single(AllSlots(client.Root).Single(slot => slot.Name == "Elsewhere").Components);
    }

    // The watcher, created in the same apply, points at a replacement, so it is created without that reference and its
    // checkpoint keeps only the references its create wrote. After its create response is lost, the re-run binds it
    // instead of creating another.
    [Fact]
    public async Task ALostCreateOfAComponentPointingAtAReplacementIsNotDuplicated()
    {
        var (client, service, state, shrunk) = await ApplyRubbleAsync("lost-watcher",
            RubbleWorld("lost-watcher", ["m1", "m2", "m3"], "rubble", watcher: true));
        client.LoseResponseOnWrite = 3; // writes: the Late Slot, the replacement, then the watcher
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.LoseResponseOnWrite = null;
        Assert.Single(AllSlots(client.Root).Single(slot => slot.Name == "Late").Components);
        Assert.Equal("", StateId(state, "watcher"));

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        var watcher = Assert.Single(AllSlots(client.Root).Single(slot => slot.Name == "Late").Components);
        Assert.Equal(StateId(state, "watcher"), watcher.Id);
        Assert.True(watcher.Members["Enabled"].Value!.GetValue<bool>());
        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

    // A resumed recreate whose replaced Component is already gone is verified by nothing and undone by nothing, but its
    // record is still settled (the supersededId cleared) before a NOT_CONVERGED stop, so a reload does not stop it with
    // session-changed.
    [Fact]
    public async Task ANotConvergedApplyStillSettlesARecreateWhoseSourceIsGone()
    {
        var name = "settle-stranded";
        var first = ReloadDocument(name, TwoRendererWorld(name, ["m1", "m2", "m3", "m4"], ["m1", "m2", "m3", "m4"]));
        var shrinkFirst = ReloadDocument(name + "-first", TwoRendererWorld(name, ["m1", "m2", "m3"], ["m1", "m2", "m3", "m4"]));
        var shrinkBoth = ReloadDocument(name + "-both", TwoRendererWorld(name, ["m1", "m2", "m3"], ["m1", "m2", "m3"]));
        var client = new FakeResoniteClient(first);
        var service = new WorldService(client);
        var state = Path.Combine(_root, name + ".state.json");
        await service.ApplyAsync(first, new ApplyOptions(state));
        var r1 = StateId(state, "r1");
        client.ResetWriteCounts();
        client.LoseResponseOnWrite = 3; // r1's replaced Component is removed, and its response is lost
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrinkFirst, new ApplyOptions(state)));
        client.LoseResponseOnWrite = null;
        var r1Replacement = StateId(state, "r1");
        Assert.NotEqual(r1, r1Replacement);
        client.RefillListsTo = 4; // r2's replacement cannot shrink to 3

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrinkBoth, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_NOT_CONVERGED", error.Code);
        Assert.Equal(["r2"], Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["undone"]));
        Assert.Empty(Assert.IsAssignableFrom<IEnumerable<string>>(error.Context["inProgress"]));
        // r1's replaced Component was already gone, so its supersededId is settled before the stop.
        var checkpoint = JsonNode.Parse(File.ReadAllText(state))!;
        Assert.Equal(r1Replacement, checkpoint["components"]!["r1"]!["id"]!.GetValue<string>());
        Assert.Null(checkpoint["components"]!["r1"]!["supersededId"]);
        Assert.Null(checkpoint["components"]!["r2"]!["supersededId"]);

        client.RefillListsTo = null;
        client.ReloadWorld("settle-stranded-2");
        await service.ApplyAsync(shrinkFirst, new ApplyOptions(state)); // no session-changed stop for r1
        await AssertListShrinkConvergedAsync(client, service, shrinkFirst, state, "r1",
            new Dictionary<string, string[]> { ["r1"] = ["m1", "m2", "m3"], ["r2"] = ["m1", "m2", "m3", "m4"] });
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedBeforeTheKeyLeavesItsSlot|FullyQualifiedName~APlanDuringAnInterruptedRecreate|FullyQualifiedName~AResumedReplacementThatPassesStays|FullyQualifiedName~AShorterDeclarationStopsWhileSomethingReferences|FullyQualifiedName~AShorterDeclarationAfterTheReplacedComponentIsGone|FullyQualifiedName~AResumedReplacementNeverPointsAtAnUndone|FullyQualifiedName~AResumedReplacementIsReadBack|FullyQualifiedName~AnUndoInterruptedAtEitherRemoval|FullyQualifiedName~AnUnmanagedSameTypeComponentStopsAResume|FullyQualifiedName~AMovingSameTypeComponentIsNotTaken|FullyQualifiedName~ALostCreateOfAComponentPointingAtAReplacement|FullyQualifiedName~ANotConvergedApplyStillSettles" || true
```

Expected: 17 件のうち 16 件が FAIL（`APPLY_RECREATE_INTERRUPTED` が出ない、再開の理由が出ない、再開せずに作り直しを始め直して同じ型の Component が残る、置き換え元が無い key の `supersededId` が残る、など）。`AShorterDeclarationAfterTheReplacedComponentIsGoneRecreatesAgain` は、再開の扱いが無いこの時点でも置き換え先から新しく作り直すので PASS。

- [ ] **Step 3: 実装する**

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                ComponentSummary? superseded = null;
                var existing = relocating || newManagedComponent ? null :
                    MatchComponent(node.Existing?.Components ?? [], spec.Type, ordinal, stateComponent, prepared.SameSession,
                        topologyTargets);
                // Like a move, a recreate needs a saved record: the first adopting apply updates existing content in place.
                var recreateReason = existing is null || stateComponent is null ? null : ListShrinkReason(spec, existing);
```

置き換え後:

```csharp
                // An interrupted recreate resumes by ID only: never by type or position.
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
                // Like a move, a recreate needs a saved record: the first adopting apply updates existing content in place.
                // A resumed recreate whose replaced Component is already gone starts again if the declaration shrank further.
                var recreateReason = existing is null || stateComponent is null || (resumed && superseded is not null) ? null :
                    ListShrinkReason(spec, existing);
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    SupersededId = superseded?.Id,
                    RecreateReason = recreateReason
                };
```

置き換え後:

```csharp
                    SupersededId = recreateReason is not null ? superseded!.Id : resumed ? stateComponent!.SupersededId : null,
                    RecreateReason = recreateReason,
                    Resumed = resumed && recreateReason is null
                };
```

**変更:** `src/RLoop.Core/WorldService.cs` の次の部分を置き換える。

置き換え前:

```csharp
                    runtime.RelocationSource = sourceSlot is null ? null :
                        MatchComponent(sourceSlot.Components, spec.Type, ordinal, stateComponent, prepared.SameSession,
                            topologyTargets);
```

置き換え後:

```csharp
                    // An interrupted recreate never matches by type or position on its old Slot; ValidateInterruptedRecreates
                    // stops it with key-not-declared.
                    runtime.RelocationSource = sourceSlot is null || !string.IsNullOrEmpty(stateComponent!.SupersededId) ? null :
                        MatchComponent(sourceSlot.Components, spec.Type, ordinal, stateComponent, prepared.SameSession,
                            topologyTargets);
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
    // its replacement, so stop before mutation.
    private static void ThrowIfRecreateInterruptedAcrossSessions(PreparedApply prepared)
    {
        if (prepared.SameSession) return;
        foreach (var (key, saved) in prepared.State.Components.Where(pair => !string.IsNullOrEmpty(pair.Value.SupersededId)))
            throw RecreateInterrupted(prepared, "session-changed", key, saved);
    }

    // Resume only while the document declares the key on the same Slot, and never undo a replacement that something may
    // already reference. Create a lost replacement again only when no same-type Component on the Slot could be it; never
    // pick one by position.
    private static void ValidateInterruptedRecreates(PreparedApply prepared)
    {
        var declared = prepared.Components.ToDictionary(component => component.StableKey, StringComparer.Ordinal);
        foreach (var (key, saved) in prepared.State.Components.Where(pair => !string.IsNullOrEmpty(pair.Value.SupersededId)))
            if (!declared.TryGetValue(key, out var component) || component.Node.StableKey != saved.SlotKey)
                throw RecreateInterrupted(prepared, "key-not-declared", key, saved);
        // A resumed replacement cannot shrink in place, and undoing it would break the references that an earlier apply
        // moved to it, so a declaration shorter than the replacement stops while anything apply read references it.
        foreach (var component in prepared.Components.Where(component => component.Resumed && component.Existing is not null &&
                     component.Superseded is not null && ListShrinkReason(component.Spec, component.Existing) is not null))
            if (ReferencesTo(prepared, component.Existing!).Length > 0)
                throw RecreateInterrupted(prepared, "declaration-shrank", component.StableKey,
                    prepared.State.Components[component.StableKey], [component.Existing!]);
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
        // After a reload, nothing tells the recreate's Components apart from those of another same-type key on the Slot.
        var sameTypeKeys = prepared.State.Components.Any(pair => pair.Key != key && pair.Value.SlotKey == saved.SlotKey &&
            TypeNamesEquivalent(pair.Value.Type, saved.Type));
        var multipleReferencedCandidates = candidates.Count(component => ReferencesTo(prepared, component).Length > 0) > 1;
        var (message, suggestions) = reason switch
        {
            "session-changed" => (
                $"A list-shrink recreate of '{key}' was interrupted and the world session changed, so the replaced Component and its replacement can no longer be told apart by ID. No mutations were performed.",
                sameTypeKeys
                    ? new[] { "Another key on this Slot has the same type, so the candidates include its Components and apply cannot tell the recreate's Components apart. Keep the state file as it is, check in Resonite what each candidate references and what references it, and do not repair this by guessing IDs." }
                    : multipleReferencedCandidates
                        ? new[] { "More than one candidate is referenced, so removing either can break a managed reference. Keep the state file as it is and do not remove a candidate or clear supersededId yet. Inspect the Components in each candidate's referencedBy, check their intended targets in Resonite, and re-point those references as needed. Then re-run apply to inspect the candidates again; do not choose a Component by its list length or by an ID from the earlier session." }
                        : new[] { "Keep the candidate that the Components in its referencedBy point at, or either one if none is referenced, and remove the other with 'resoloop component remove ID --yes'. Use only the IDs in candidates; supersededId and savedId are IDs from the earlier session.",
                              $"Then back up the state file, set components.{key}.id to its supersededId if the ID is empty, delete supersededId, and re-run apply." }),
            "key-not-declared" => (
                $"A list-shrink recreate of '{key}' was interrupted, and the document no longer declares the key on its Slot. No mutations were performed.",
                new[] { "Declare the key again on the same Slot and re-run apply in this session to finish the recreate. Then remove the key and apply with --prune --yes if you no longer want it." }),
            "declaration-shrank" => (
                $"A list-shrink recreate of '{key}' was interrupted, and the document now declares a list shorter than its replacement holds while something references the replacement. No mutations were performed.",
                new[] { "Declare at least as many elements as the replacement holds (see candidates) and re-run apply in this session to finish the recreate, then shorten the list again." }),
            _ => (
                $"A list-shrink recreate of '{key}' was interrupted before its replacement ID was saved, and the Slot holds a same-type Component that no key owns. No mutations were performed.",
                new[] { "If a candidate's lists match the declaration, it is most likely the replacement that the interrupted apply created. If the declaration references a Component that the same apply creates later, apply creates the replacement without initial values, so its lists are all empty; a Component with empty lists that you added looks the same. Inspect each candidate with 'resoloop component inspect ID', remove only one you can confirm the interrupted apply created with 'resoloop component remove ID --yes', and re-run apply; apply creates the replacement again.",
                        $"If no candidate fits that description, back up the state file, set components.{key}.id back to its supersededId, delete supersededId, and re-run apply to start the recreate again." })
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
                    .ToDictionary(member => member.Key, member => member.Value.Elements?.Count ?? 0, StringComparer.Ordinal),
                referencedBy = ReferencesTo(prepared, component)
            }).ToArray()
        }, suggestions);
    }

    // The Components in the snapshots that apply read whose members point at this Component or at one of its members.
    private static object[] ReferencesTo(PreparedApply prepared, ComponentSummary target)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal) { target.Id };
        void CollectIds(MemberValue member)
        {
            if (!string.IsNullOrWhiteSpace(member.Id)) ids.Add(member.Id);
            foreach (var child in member.Members?.Values ?? []) CollectIds(child);
            foreach (var element in member.Elements ?? []) CollectIds(element);
        }
        foreach (var member in target.Members?.Values ?? []) CollectIds(member);
        static IEnumerable<string> Targets(MemberValue member) =>
            (member.Kind == "reference" && member.TargetId is { } id ? [id] : Enumerable.Empty<string>())
                .Concat((member.Members?.Values ?? []).SelectMany(Targets))
                .Concat((member.Elements ?? []).SelectMany(Targets));
        return prepared.SnapshotSlots.DistinctBy(slot => slot.Id).SelectMany(slot => slot.Components)
            .Where(component => component.Id != target.Id)
            .SelectMany(component => (component.Members ?? new Dictionary<string, MemberValue>())
                .Where(member => Targets(member.Value).Any(ids.Contains))
                .Select(member => (object)new { id = component.Id, type = component.Type, member = member.Key }))
            .ToArray();
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
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedBeforeTheKeyLeavesItsSlot|FullyQualifiedName~APlanDuringAnInterruptedRecreate|FullyQualifiedName~AResumedReplacementThatPassesStays|FullyQualifiedName~AShorterDeclarationStopsWhileSomethingReferences|FullyQualifiedName~AShorterDeclarationAfterTheReplacedComponentIsGone|FullyQualifiedName~AResumedReplacementNeverPointsAtAnUndone|FullyQualifiedName~AResumedReplacementIsReadBack|FullyQualifiedName~AnUndoInterruptedAtEitherRemoval|FullyQualifiedName~AnUnmanagedSameTypeComponentStopsAResume|FullyQualifiedName~AMovingSameTypeComponentIsNotTaken|FullyQualifiedName~ALostCreateOfAComponentPointingAtAReplacement|FullyQualifiedName~ANotConvergedApplyStillSettles"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Resume an interrupted recreate by ID in the same session, and stop otherwise" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 17 件とも PASS、全件も PASS（`RLoop.Tests` 379 件）。

### Task B6: 置き換え元への参照の検査

**Files:**
- Modify: `src/RLoop.Core/WorldService.cs`（`PrepareAsync`、新しい `ValidateRecreateReferences`）
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B5 の `RecreatePlanReason`
- Produces: `APPLY_LIST_SHRINK_REFERENCED`（6）。context は `stateFile`・`recreates`（`key`・`id`・`reason`）・`references`（`componentKey`・`targetId`・`referencedBy`・`type`・`member`・`slotId`・`slotPath`）。

- [ ] **Step 1: テストを書く**

管理外の Component からの参照（置き換え元、そのメンバー、リストの要素）と、管理 Component の宣言していないメンバーからの参照で止まること、syncObject の部分宣言では同じ位置に参照の指定がある場合だけ張り替わること、移動元からの参照では止まらないことを確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    // Recreating gives the Component and its members new IDs, so apply stops for every reference that it does not re-point:
    // one to the Component, to one of its members or to a list element, and one from a member that a managed Component
    // leaves undeclared.
    [Theory]
    [InlineData("component")]
    [InlineData("member")]
    [InlineData("element")]
    [InlineData("undeclared-member")]
    public async Task AnUnmanagedReferenceToTheReplacedComponentStopsBeforeMutation(string reference)
    {
        var name = "referenced-" + reference;
        var (client, service, state, shrunk) = await ApplyRubbleAsync(name, RubbleWorld(name, "m1", "m2", "m3"));
        var rubble = AllSlots(client.Root).Single(slot => slot.Name == "Rubble01");
        var renderer = RubbleRenderers(client).Single();
        var target = reference switch
        {
            "member" => renderer.Members["Materials"].Id!,
            "element" => renderer.Members["Materials"].Elements![1].Id!,
            _ => renderer.Id
        };
        string referencedBy;
        if (reference == "undeclared-member")
        {
            // The managed Source declares only Target; its undeclared member Spare points at the renderer too.
            var source = Sources(client).Single(component => component.Id == StateId(state, "source"));
            source.Members["Spare"] = new MemberValue("reference", source.Id + ":Spare", TargetId: target);
            referencedBy = source.Id;
        }
        else
        {
            referencedBy = (await client.AddComponentAsync(rubble.Id, "Test.Source", new Dictionary<string, string> { ["Target"] = target })).Id;
        }
        client.ResetWriteCounts();

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_LIST_SHRINK_REFERENCED", error.Code);
        Assert.Equal(ExitCodes.ValidationFailed, error.ExitCode);
        var found = Assert.Single(JsonSerializer.SerializeToNode(error.Context["references"])!.AsArray())!;
        Assert.Equal(referencedBy, found["referencedBy"]!.GetValue<string>());
        Assert.Equal(target, found["targetId"]!.GetValue<string>());
        Assert.Equal(0, client.Writes);
    }

    // A partial syncObject declaration writes only its declared children, so apply re-points a reference there only when the
    // declaration puts a selector at the same path; otherwise it stops.
    [Theory]
    [InlineData("undeclared-child")]
    [InlineData("declared-child")]
    [InlineData("no-reference")]
    public async Task APartlyDeclaredSyncObjectIsCheckedChildByChild(string child)
    {
        var name = "partial-" + child;
        var snapPositions = child == "declared-child"
            ? "{\"LocalSpace\":\"$slot:rubble\",\"Target\":\"$ref:renderer\"}"
            : "{\"LocalSpace\":\"$slot:rubble\"}";
        string World(params string[] materials) => RubbleWorld(name, materials).Replace(
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""",
            """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}},{"key":"consumer","type":"Test.Slider","fields":{"SnapPositions":""" +
            snapPositions + "}}", StringComparison.Ordinal);
        var (client, service, state, shrunk) = await ApplyRubbleAsync(name, World("m1", "m2", "m3"), World("m1", "m2", "m3", "m4"));
        var rubble = AllSlots(client.Root).Single(slot => slot.Name == "Rubble01");
        var renderer = RubbleRenderers(client).Single();
        var consumer = rubble.Components.Single(component => component.Type == "Test.Slider");
        // The fake writes a JSON object as one field value, so give the consumer the runtime's syncObject shape.
        var children = new Dictionary<string, MemberValue> { ["LocalSpace"] = new("reference", consumer.Id + ":LocalSpace", TargetId: rubble.Id) };
        if (child != "no-reference") children["Target"] = new("reference", consumer.Id + ":Target", TargetId: renderer.Id);
        consumer.Members["SnapPositions"] = new MemberValue("syncObject", consumer.Id + ":SnapPositions", Members: children);
        client.ResetWriteCounts();

        var error = await Record.ExceptionAsync(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        if (child == "undeclared-child")
        {
            Assert.Equal("APPLY_LIST_SHRINK_REFERENCED", Assert.IsType<RLoopException>(error).Code);
            Assert.Equal(0, client.Writes);
            Assert.Contains(RubbleRenderers(client), component => component.Id == renderer.Id);
            return;
        }
        Assert.Null(error);
        Assert.DoesNotContain(RubbleRenderers(client), component => component.Id == renderer.Id);
        if (child == "declared-child")
            Assert.Contains(StateId(state, "renderer"), consumer.Members["SnapPositions"].Value!.ToJsonString());
    }

    // A Source moving to another Slot leaves its old instance behind until apply removes it, so that instance's reference to
    // the replaced Component does not stop the recreate.
    [Fact]
    public async Task ASourceMovingAwayDoesNotStopTheRecreateItPointsAt()
    {
        const string source = """{"key":"source","type":"Test.Source","fields":{"Target":"$ref:renderer"}}""";
        static string World(bool moved, params string[] materials) => moved
            ? RubbleWorld("moving-source", materials).Replace("," + source + "]}",
                """]},{"slot":{"key":"elsewhere","name":"Elsewhere"},"components":[""" + source + "]}", StringComparison.Ordinal)
            : RubbleWorld("moving-source", materials);
        var (client, service, state, shrunk) = await ApplyRubbleAsync("moving-source", World(true, "m1", "m2", "m3"),
            World(false, "m1", "m2", "m3", "m4"));

        await service.ApplyAsync(shrunk, new ApplyOptions(state));

        await AssertListShrinkConvergedAsync(client, service, shrunk, state, "renderer",
            new Dictionary<string, string[]> { ["renderer"] = ["m1", "m2", "m3"] });
    }

```

- [ ] **Step 2: 失敗することを確かめる**

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AnUnmanagedReferenceToTheReplacedComponent|FullyQualifiedName~APartlyDeclaredSyncObjectIsChecked|FullyQualifiedName~ASourceMovingAwayDoesNotStop" || true
```

Expected: 8 件のうち 5 件が FAIL（停止せずに作り直す）。`AnUnmanagedReferenceToTheReplacedComponentStopsBeforeMutation` の 4 件と `APartlyDeclaredSyncObjectIsCheckedChildByChild(child: "undeclared-child")`。残りの 3 件（`APartlyDeclaredSyncObjectIsCheckedChildByChild` の `declared-child`・`no-reference` と `ASourceMovingAwayDoesNotStopTheRecreateItPointsAt`）は止まらないことを確かめるテストなので PASS。

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
        // Apply re-points a reference only where the declaration puts a selector at the same path: a partial syncObject
        // declaration writes only its declared children, so a child it leaves out keeps pointing at the replaced Component.
        static IEnumerable<(string Target, bool Repointed)> References(MemberValue member, JsonElement? declared)
        {
            if (member.Kind == "reference" && member.TargetId is { } target)
                yield return (target, declared is { } value && ContainsWorldReference(value));
            foreach (var (name, child) in member.Members ?? new Dictionary<string, MemberValue>())
            {
                JsonElement? declaredChild = declared is { ValueKind: JsonValueKind.Object } parent &&
                    parent.TryGetProperty(name, out var property) ? property : null;
                foreach (var reference in References(child, declaredChild)) yield return reference;
            }
            var elements = member.Elements ?? [];
            for (var i = 0; i < elements.Count; i++)
            {
                JsonElement? declaredElement = declared is { ValueKind: JsonValueKind.Array } array && i < array.GetArrayLength() ? array[i] : null;
                foreach (var reference in References(elements[i], declaredElement)) yield return reference;
            }
        }
        var removed = recreates.Select(component => component.Superseded!.Id)
            .Concat(prepared.Components.Where(component => component.RelocationSource is not null).Select(component => component.RelocationSource!.Id))
            .ToHashSet(StringComparer.Ordinal);
        var managed = prepared.Components.Where(component => component.Existing is not null)
            .ToDictionary(component => component.Existing!.Id, StringComparer.Ordinal);
        var references = new List<object>();
        void Check(SlotInfo slot, string ownerId, string ownerType, IReadOnlyDictionary<string, MemberValue>? members)
        {
            var declaredFields = managed.TryGetValue(ownerId, out var owner) ? owner.Spec.Fields : null;
            foreach (var (name, member) in members ?? new Dictionary<string, MemberValue>())
            {
                JsonElement? declared = declaredFields?.TryGetValue(name, out var field) == true ? field : null;
                foreach (var (target, _) in References(member, declared).Where(reference => !reference.Repointed && targets.ContainsKey(reference.Target)))
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
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~AnUnmanagedReferenceToTheReplacedComponent|FullyQualifiedName~APartlyDeclaredSyncObjectIsChecked|FullyQualifiedName~ASourceMovingAwayDoesNotStop"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add -A src tests
git commit -m "Stop a recreate when something unmanaged references the replaced Component" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 8 件とも PASS、全件も PASS（`RLoop.Tests` 387 件）。

### Task B7: 書き込みの位置ごとの網羅テスト

**Files:**
- Test: `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`

**Interfaces:**
- Consumes: Task B1 の `ApplyScenarioAsync`・`AssertListShrinkConvergedAsync`、Task A1 の `InterruptedAsync`

- [ ] **Step 1: 網羅テストを書く**

既存のシナリオは 2 つ。`one-recreate`（S1）は Component を 1 つ作り直し、それを管理 Component が参照し、同じ apply で作る参照元（watcher）もそれを参照する。`shared-slot`（S2）は同じ Slot で 2 つを作り直し、その Slot から別の Component を移動し、文書から外した同じ型の key を残し、同じ apply で後から作る material を参照する。書き込みの位置 k を 1 から最後まで、反映前の失敗と、反映後の応答の喪失で止め、同じセッションでの再開と、再読込の後の停止を確かめる。`replacement-unverified` で止まった場合は、書き込み 0 件で止まったことと、suggestions の基準で選んだ候補が 1 つで中断した apply が作ったものであることを確かめてから、それだけを削除する。再読込の後は、plan も止まり、2 回の apply が止まり、state が変わらないことを確かめ、S1 では suggestions の手順（`referencedBy` で参照されている候補を残す）で収束させ、S2 では自動では区別できないことを示す suggestion を確かめる。S1 では、進捗の通知ごとのキャンセルも確かめる。収束の判定は、作り直す型（Test.Renderer）と参照元（Test.Source）の各 Component が state の key にちょうど 1 つずつ結び付いていること、参照、state の index に限る。移動の中断で移動元（Test.Indexed の mover）が残る問題は上流の既存の課題（範囲外）で、判定の対象外。

加えて、既存の管理参照が2件ある状態で一方だけが置き換え先へ張り替わってから中断し、再読込した場合を1件固定する。両候補に参照が残るため、state を変えず、候補の削除や supersededId の除去を早まらず、参照元の確認・張り替え・再検査を案内することを確かめる。

**変更:** `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` の次の部分の直前に追加する。

```csharp
    // A Materials slot with m1..m4, and Rubble01 whose renderer declares its Materials and whose managed Source points at
```

追加する内容:

```csharp
    // Stops the shrinking apply at each write in turn, before the write lands or after it lands with its response lost.
    // The next apply in the same session must converge, or stop on replacement-unverified before any write until the
    // recovery in its suggestions. Convergence covers the renderers, the Sources, the references and the saved indexes; a
    // moved Component's source that an interrupted move leaves behind is an existing upstream issue and not checked.
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
            var before = RubbleRenderers(client).Select(component => component.Id).ToHashSet();
            if (responseLost) client.LoseResponseOnWrite = write;
            else client.FailOnWrite = write;

            var interrupted = await InterruptedAsync(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
            client.LoseResponseOnWrite = null;
            client.FailOnWrite = null;
            var created = RubbleRenderers(client).Select(component => component.Id).Where(id => !before.Contains(id)).ToArray();
            client.ResetWriteCounts();
            try
            {
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
            }
            catch (RLoopException error) when (error.Code == "APPLY_RECREATE_INTERRUPTED" && Equals(error.Context["reason"], "replacement-unverified"))
            {
                Assert.True(responseLost, $"write {write}: only a lost create response can leave an unverified replacement.");
                Assert.True(client.Writes == 0, $"write {write}: the stopped apply wrote {client.Writes} time(s).");
                // The recovery in the suggestions: remove the candidate whose lists match the declaration, or whose lists are
                // all empty when the declaration references a Component that the same apply creates later.
                var declared = expected[(string)error.Context["componentKey"]!];
                var candidate = Assert.Single(JsonSerializer.SerializeToNode(error.Context["candidates"])!.AsArray(), candidate =>
                    candidate!["lists"]!["Materials"]!.GetValue<int>() is var count &&
                    (count == declared.Length || declared.Contains("late") && count == 0))!["id"]!.GetValue<string>();
                Assert.Contains(candidate, created);
                await client.RemoveComponentAsync(candidate);
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
            }

            await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"write {write}: ");
            if (!interrupted) break;
        }
    }

    // A world reload while a recreate is in progress must stop plan and apply before any write and keep the state, or the
    // apply converges. With no other key of the same type on the Slot, the recovery in the suggestions converges; with one,
    // the suggestions say that apply cannot tell the Components apart.
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
                var checkpoint = File.ReadAllBytes(state);
                var planError = await Assert.ThrowsAsync<RLoopException>(() => service.PlanApplyAsync(shrunk, new ApplyOptions(state)));
                Assert.Equal("session-changed", planError.Context["reason"]);
                RLoopException error = null!;
                for (var attempt = 0; attempt < 2; attempt++)
                {
                    error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
                    Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
                    Assert.Equal("session-changed", error.Context["reason"]);
                }
                Assert.True(client.Writes == 0, $"write {write}: the stopped apply wrote {client.Writes} time(s).");
                Assert.Equal(checkpoint, File.ReadAllBytes(state));
                var candidates = JsonSerializer.SerializeToNode(error.Context["candidates"])!.AsArray();
                if (scenario == "shared-slot")
                {
                    Assert.Contains("cannot tell the recreate's Components apart", Assert.Single(error.Suggestions));
                }
                else
                {
                    // The recovery in the suggestions: keep the candidate that something references, remove the other, and
                    // clear the recreate in the state.
                    Assert.True(candidates.Count(candidate => candidate!["referencedBy"]!.AsArray().Count > 0) <= 1,
                        $"write {write}: more than one candidate is referenced.");
                    var kept = candidates.FirstOrDefault(candidate => candidate!["referencedBy"]!.AsArray().Count > 0) ?? candidates[0];
                    foreach (var candidate in candidates.Where(candidate => candidate != kept))
                        await client.RemoveComponentAsync(candidate!["id"]!.GetValue<string>());
                    var saved = JsonNode.Parse(File.ReadAllText(state))!;
                    var record = saved["components"]![(string)error.Context["componentKey"]!]!.AsObject();
                    if (record["id"]!.GetValue<string>().Length == 0) record["id"] = record["supersededId"]!.GetValue<string>();
                    record.Remove("supersededId");
                    File.WriteAllText(state, saved.ToJsonString());
                    await service.ApplyAsync(shrunk, new ApplyOptions(state));
                    await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"write {write}: ");
                }
            }
            else
            {
                await service.ApplyAsync(shrunk, new ApplyOptions(state));
                await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"write {write}: ");
            }
            if (!interrupted) break;
        }
    }

    // Cancelling at each progress notification leaves states that the two injected failures cannot, because a cancel can land
    // right after a checkpoint. The next apply in the same session must converge.
    [Fact]
    public async Task ARecreateCancelledAtAnyProgressConvergesInTheSameSession()
    {
        for (var notification = 1; ; notification++)
        {
            var (client, service, state, shrunk, referenced, expected) = await ApplyScenarioAsync($"cancel-{notification}", "one-recreate");
            using var cancellation = new CancellationTokenSource();
            var seen = 0;
            await Record.ExceptionAsync(() => service.ApplyAsync(shrunk,
                new ApplyOptions(state, Progress: _ => { if (++seen == notification) cancellation.Cancel(); }), cancellation.Token));

            await service.ApplyAsync(shrunk, new ApplyOptions(state));

            await AssertListShrinkConvergedAsync(client, service, shrunk, state, referenced, expected, $"notification {notification}: ");
            if (seen < notification) break;
        }
    }

    // A lost field response can leave managed references split between the old and new Components. After a reload,
    // neither referenced candidate can be deleted safely until those references have been checked and re-pointed.
    [Fact]
    public async Task AWorldReloadWithBothRecreateCandidatesReferencedDoesNotSuggestDeletingEither()
    {
        var name = "split-references";
        var (client, service, state, shrunk) = await ApplyRubbleAsync(name,
            RubbleWorld(name, ["m1", "m2", "m3"], "rubble", watcher: true),
            RubbleWorld(name, ["m1", "m2", "m3", "m4"], "rubble", watcher: true));
        client.LoseResponseOnWrite = 2; // create lands, then source's re-point lands and its response is lost
        await Assert.ThrowsAsync<IOException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));
        client.LoseResponseOnWrite = null;
        Assert.Equal(2, RubbleRenderers(client).Count());
        client.ReloadWorld("split-references-reloaded");
        client.ResetWriteCounts();
        var before = File.ReadAllText(state);

        var error = await Assert.ThrowsAsync<RLoopException>(() => service.ApplyAsync(shrunk, new ApplyOptions(state)));

        Assert.Equal("APPLY_RECREATE_INTERRUPTED", error.Code);
        Assert.Equal("session-changed", error.Context["reason"]);
        Assert.Equal(0, client.Writes);
        Assert.Equal(before, File.ReadAllText(state));
        var candidates = System.Text.Json.JsonSerializer.SerializeToNode(error.Context["candidates"])!.AsArray();
        Assert.Equal(2, candidates.Count);
        Assert.All(candidates, candidate => Assert.Single(candidate!["referencedBy"]!.AsArray()));
        Assert.DoesNotContain(error.Suggestions, suggestion => suggestion.Contains("remove the other", StringComparison.Ordinal));
        Assert.DoesNotContain(error.Suggestions, suggestion => suggestion.Contains("delete supersededId", StringComparison.Ordinal));
        Assert.Contains(error.Suggestions, suggestion => suggestion.Contains("re-point", StringComparison.Ordinal));
    }


```

- [ ] **Step 2: 成功することを確かめてコミットする**

この時点では実装がそろっているので、最初から PASS する。失敗した場合は、失敗したメッセージの `write k` が示す書き込みの位置から原因を調べる。設計の見直しが要りそうな場合は、Task C1 Step 3 と同じく、修正を止めてユーザに報告し、判断を仰ぐ。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release --filter "FullyQualifiedName~ARecreateInterruptedAtAnyWriteConverges|FullyQualifiedName~AWorldReloadDuringARecreateStops|FullyQualifiedName~AWorldReloadWithBothRecreateCandidatesReferenced|FullyQualifiedName~ARecreateCancelledAtAnyProgress"
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release
git add tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs
git commit -m "test: interrupt a list-shrink recreate at every write" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: 10 件とも PASS、全件も PASS（`RLoop.Tests` 397 件）。実行時間の目安は既存の 9 件で合計 20 秒前後。

### Task B8: 文書、修正前との比較、コミットの整理、fork の PR B

**Files:**
- Modify: `README.md`、`README_JA.md`、`README-DETAILS.md`、`docs/DECLARATIVE.md`、`skills/codex/resonite-build/SKILL.md`、`skills/codex/resonite-debug/SKILL.md`

- [ ] **Step 1: 文書を更新する**

上流の `AGENTS.md` は、CLI の挙動を変えたら README と `skills/codex/*/SKILL.md` も更新するよう求めている。state の編集が要る復旧手順は、上流の回答が出るまで文書に載せず、「エラーの suggestions に従う（state の編集が要る）」とだけ書く（Spec の D-31）。Markdown の目印の当て方は「この計画のコードについて」の規則に従う。

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
`initialFields`へ置くと、新規作成時だけ初期化され、adopt・再applyでは上書きされません。
```

追加する内容:

```markdown
ただし、list memberの宣言要素数が実機より少ないためにComponentを作り直すapply（planの`recreate`）では、新しいComponentへ`initialFields`を設定し直すため値は初期値に戻り、宣言していないmemberも型の既定値に戻ります。
```

**変更:** `docs/DECLARATIVE.md` の次の部分を置き換える。

置き換え前:

```markdown
`diff`はcreate/update/rename/delete/no-op、
```

置き換え後:

```markdown
`diff`はcreate/update/rename/recreate/delete/no-op、
```

**変更:** `docs/DECLARATIVE.md` の次の部分の直後に追加する。

```markdown
旧driverがtargetを占有する場合は明示pruneの計画を確認してください。自動でpruneを有効化することはありません。
```

追加する内容:

```markdown

ResoniteLinkはlistの要素を削除できません（短いlistを送っても先頭の要素が置き換わるだけです）。`fields`で宣言したlist memberの要素数が実機より少ない既存Componentは、planで`recreate`となります。applyは同じSlotに新しいComponentを作って宣言したfieldを書き、listを読み直して確かめてから、管理Componentの参照を張り替え、旧Componentを削除します。Componentの移動と同じく、この削除に`--prune`は不要です。新しいComponentでは、`initialFields`は宣言の初期値に、宣言していないmemberは型の既定値に戻ります。stateに記録の無いComponent（adoptの初回のapplyで取り込むもの）は作り直さず、その場で更新します。保存したIDで確かめられないComponent（作成が中断したkeyに型と位置で照合したもの）も作り直さず、`STABLE_COMPONENT_AMBIGUOUS`で停止します。次の場合は停止します。

- `APPLY_LIST_SHRINK_REFERENCED`（変更前）: 旧Componentやそのmemberを、管理Componentが同じ位置に参照を宣言していないもの（syncObjectの一部だけを宣言した場合の、宣言していない子を含む）が参照しています。調べるのはapplyが読んだ階層（`slot.parent`以下、applyが読み取る深さまで）だけで、その外からの参照は旧Componentの削除で切れます。参照元を`$component:`などで管理対象として宣言するか、参照を外してください。
- `APPLY_LIST_SHRINK_NOT_CONVERGED`（検証時）: 新しいComponentでもlistが宣言より長いまま残りました。applyはこのapplyで作った新しいComponentを削除してstateを元に戻します。runtimeが保つ要素数を宣言するか、listを詰め直す原因を確認してください。前のapplyから再開して検証を通った作り直しは、途中のまま残ります（contextの`inProgress`）。
- `APPLY_RECREATE_INTERRUPTED`（変更前）: 作り直しが途中で止まり、自動では再開できません。`reason`が`session-changed`なら、ワールドの再読込などでIDが変わっています。エラーのsuggestionsと`stateFile`に従ってください（stateの編集が要ります）。同じSlotに同じ型のkeyがほかにある場合は自動では区別できないので、stateをそのまま残し、各候補の参照先を確かめてください。`key-not-declared`なら、同じセッションのうちにkeyを元のSlotへ戻して再実行すると完了します。keyが不要なら、その後keyを外して`--prune`で削除してください。`declaration-shrank`なら、新しいComponentが持つ要素数以上を宣言して同じセッションで再実行し、作り直しを終えてから宣言を短くしてください。`replacement-unverified`なら、`candidates`のうちlistが宣言と一致するものは、中断したapplyが作った新しいComponentである可能性が高いものです。宣言が同じapplyで後から作るComponentを参照している場合は、applyが初期値なしで作るので、listがすべて空のものもその可能性があります。ただし、listが空の、利用者が置いたComponentとは見分けられません。`resoloop component inspect ID`で確かめ、中断したapplyが作ったと確かめられたものだけを`resoloop component remove ID --yes`で削除し、再実行してください。当てはまる候補が無い場合は、エラーのsuggestionsに従ってください（stateの編集が要ります）。
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

ResoniteLink cannot remove list elements. When a declared list member such as `MeshRenderer.Materials` is shorter than the runtime list, `diff` shows `recreate`, and apply replaces the Component on the same Slot: it creates the replacement with the declared fields, verifies the list, re-points managed references, and then removes the old Component without `--prune`. The replacement starts from `initialFields` and type defaults for undeclared members. Apply stops before mutation with `APPLY_LIST_SHRINK_REFERENCED` when something in the hierarchy apply read, other than a managed declared reference, points at the old Component, stops with `APPLY_LIST_SHRINK_NOT_CONVERGED` after removing the replacement when the runtime keeps the list longer, and stops before mutation with `APPLY_RECREATE_INTERRUPTED` when an interrupted recreate cannot resume in the same session. Follow the suggestions in the error.
```

**変更:** `README_JA.md` の次の部分の直後に追加する。

```markdown
フィールド書き込みが中断した場合は checkpoint を保持し、同じ manifest で再実行します。
```

追加する内容:

```markdown

ResoniteLink は list の要素を削除できません。`MeshRenderer.Materials` などの list member を実機より短く宣言すると、`diff` は `recreate` を示し、apply は同じ Slot で Component を作り直します。宣言した field で新しい Component を作って list を確かめ、管理 Component の参照を張り替えてから、旧 Component を `--prune` なしで削除します。新しい Component では、`initialFields` は宣言の初期値に、宣言していない member は型の既定値に戻ります。apply が読んだ範囲で、旧 Component を管理 Component の宣言済み参照以外が参照している場合は変更前に `APPLY_LIST_SHRINK_REFERENCED`、runtime が list を宣言より長いまま残す場合は新しい Component を削除したうえで `APPLY_LIST_SHRINK_NOT_CONVERGED`、中断した作り直しを同じセッションで再開できない場合は変更前に `APPLY_RECREATE_INTERRUPTED` で停止します。エラーの suggestions に従って復旧してください。
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
review create/update/rename/recreate/delete targets and reasons. A `recreate` replaces the Component on its Slot without `--prune` because ResoniteLink cannot remove list elements; apply checks other references to the Component only within the hierarchy it read, so inspect references from elsewhere before applying a `recreate`.
```

**変更:** `skills/codex/resonite-debug/SKILL.md` の次の部分の直前に追加する。

```markdown
Explain the evidence and root cause. Do not mutate the world during a diagnosis-only request.
```

追加する内容:

```markdown
`APPLY_LIST_SHRINK_REFERENCED` stops a list-shrink recreate before mutation because something in the hierarchy apply read, other than a managed declared reference, points at the Component; declare that reference with a stable selector or remove it. `APPLY_LIST_SHRINK_NOT_CONVERGED` means the runtime kept a replacement's list longer than declared, so apply removed the replacements it created; declare the length that the runtime keeps. `APPLY_RECREATE_INTERRUPTED` means an interrupted recreate cannot resume automatically; follow the suggestions for its `reason` and never pick a candidate by position.

```

- [ ] **Step 2: A の `src/` で、B のテストが失敗することを確かめる**

使い捨ての worktree で `src/` だけを A のブランチに戻し、全件を流す。テストが失敗するので終了コードは 0 以外になる（ブロックの最後で確かめる）。途中で止まって worktree が残った場合は、`git -C /workspaces/reso-world/external/resoloop worktree remove --force /workspaces/reso-world/external/resoloop/.worktrees/compare-b`（ディレクトリが無ければ `git -C /workspaces/reso-world/external/resoloop worktree prune`）で片付けてからやり直す。

```bash
set -euo pipefail
R=/workspaces/reso-world/external/resoloop
C=$R/.worktrees/compare-b
BASE=fix/slot-index-after-removal
git -C "$R" worktree add --detach "$C" fix/list-shrink-recreate-split
test "$(git -C "$C" rev-parse --show-toplevel)" = "$C"
git -C "$C" checkout "$BASE" -- src
rc=0
(cd "$C" && dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --configuration Release) || rc=$?
git -C "$R" worktree remove --force "$C"
test "$rc" -ne 0
```

Expected: 397 件中 FAIL 53 件、PASS 344 件。FAIL は B で追加したテストだけ。B で追加した 60 件のうち PASS するのは次の 7 件だけ（今の挙動を固定するテストと、上流の既存の停止を確かめるテスト）: `AListThatDoesNotShrinkIsUpdatedInPlace`（grow・reorder）、`TheFakeClientCannotShrinkAListLikeResoniteLink`、`AShorterListInsideASyncObjectIsNotRecreated`、`AComponentMovedWithAShorterListIsRelocatedNotRecreated`、`TheFirstAdoptingApplyDoesNotRecreate`、`ARecreateKeepsAnAssetUrlThatAWorldSaveMigrated(legacyState: True)`。 作り直しのテストの多くは、PR B の Root cause と同じ `APPLY_REFERENCE_NOT_RETAINED` で失敗する（偽クライアントがリストを縮められないことの確認を兼ねる）。これ以外の組み合わせになったら先に進まずに報告する。Task C1 でテストを足した・削った場合は、この件数と PASS する一覧を更新してから確かめる。

- [ ] **Step 3: 上流 CI に相当する確認を行う（Linux）**

上流 CI は windows-latest で restore・build・test・pack と、導入したツールでのスモークテストを行う。ここでは Linux で同じ手順を行い、Windows での確認は上流 PR の CI に任せる。B は `skills/codex/` を変えるので、パッケージに新しい文書が入ることも確かめる。global の resoloop とロックは変えない。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore
S=$(mktemp -d)
dotnet pack src/RLoop.Cli/RLoop.Cli.csproj --configuration Release --no-build --output "$S/artifacts"
VERSION=$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' src/RLoop.Cli/RLoop.Cli.csproj | head -n 1)
dotnet tool install ResoLoop --tool-path "$S/tool" --add-source "$S/artifacts" --version "$VERSION"
"$S/tool/resoloop" --version
"$S/tool/resoloop" init "$S/smoke"
"$S/tool/resoloop" skills sync "$S/smoke" --check
"$S/tool/resoloop" validate "$S/smoke/content/main.json" --json
unzip -p "$S/artifacts/ResoLoop.$VERSION.nupkg" '*resonite-debug/SKILL.md' | grep -c APPLY_RECREATE_INTERRUPTED
rm -rf -- "$S"
```

Expected: `RLoop.Tests` 397 件、`RLoop.IntegrationTests` 19 件がすべて PASS、警告 0 件。pack・導入・スモークテストが成功し、最後の `grep -c` が 1 以上。

- [ ] **Step 4: コミットを 2 件にまとめる**

Task B1〜B7 のコミットを「実装とテスト」の 1 件にまとめ、文書を 2 件目にする。B を A の上へ載せ直していないまま A を変えていると、まとめたコミットが A の修正を打ち消す（`reset --soft` の後では検出できない）ので、reset の前に確かめる。`Refs orange3134/resoloop#5` はここでは付けない（Task C1 Step 4 の最後のまとめ直しで付ける）。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
test "$(git branch --show-current)" = fix/list-shrink-recreate-split
git merge-base --is-ancestor fix/slot-index-after-removal HEAD || { echo 'STOP: B を A の上へ載せ直してから（Task C1 Step 4）'; exit 1; }
git reset --soft fix/slot-index-after-removal
git restore --staged README.md README_JA.md README-DETAILS.md docs/DECLARATIVE.md skills/codex/resonite-build/SKILL.md skills/codex/resonite-debug/SKILL.md
git commit -F - <<'EOF'
Recreate a managed Component when a declared list member shrinks

ResoniteLink 0.13.1 cannot remove list elements. On Resonite 2026.9.18.82,
sending [A] to a MeshRenderer.Materials list that holds [A,B] leaves
[A,B], sending [] leaves it unchanged, and sending [B] afterwards gives
[B,B]. A declared list shorter than the runtime list therefore never
converged. For a list of world references apply stopped with
APPLY_REFERENCE_NOT_RETAINED after its other changes were already
written; any other list was written again on every apply.

When a declared list member of a managed Component with a saved record
is shorter than the observed list, plan the Component as "recreate".
Apply creates the replacement on the same Slot, writes its declared
fields and reads it back, re-points the declared references of managed
Components, and only then removes the replaced Component. State keeps the
replaced ID as supersededId until the removal, and the Slot's indexes are
saved again in the same checkpoint.

No replacement is a reference target until every replacement in the
apply is verified, and Components created in the same apply leave out
only their references to unverified replacements. If the runtime keeps
the list longer than declared, apply removes every replacement that
nothing references yet, restores the state saved just before each was
created, and stops with APPLY_LIST_SHRINK_NOT_CONVERGED.

An interrupted recreate resumes by ID only, in the same session, and only
while the document declares its key on the same Slot. Otherwise apply
stops before mutation with APPLY_RECREATE_INTERRUPTED, whose reason and
suggestions explain the recovery. A replacement whose ID was not saved is
created again only when no same-type Component on the Slot could be the
lost one. A key whose create was interrupted is never recreated from a
Component matched by type and position. Apply also stops before mutation
with APPLY_LIST_SHRINK_REFERENCED when something in the hierarchy it read
points at the replaced Component where the declaration does not re-point
it, and observes the replaced Component when it detects asset URLs that a
world save migrated.

Checkpoints taken before a created Component's fields are written keep
only the reference selectors that its create wrote, so a retry after a
lost create response binds it instead of creating another.

The test fake keeps trailing list elements the way the runtime does.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add README.md README_JA.md README-DETAILS.md docs/DECLARATIVE.md skills/codex/resonite-build/SKILL.md skills/codex/resonite-debug/SKILL.md
git commit -F - <<'EOF'
Document list-shrink recreates and their stop codes

A recreate resets initialFields to their declared values and every
undeclared member to its type default, and removes the replaced Component
without --prune. Describe the plan action, the scope of the reference
check, and the three stop codes with their recovery in the READMEs, the
declarative guide and the resonite-build and resonite-debug skills.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git log --oneline fix/slot-index-after-removal..HEAD
git diff --stat fix/slot-index-after-removal HEAD
dotnet build ResoLoop.slnx --configuration Release && dotnet test ResoLoop.slnx --configuration Release --no-build
```

Expected: コミットは 2 件。`git diff --stat` に出るのは B のファイル（`src/RLoop.Core/WorldService.cs`、`src/RLoop.Core/ApplyWorkflow.cs`、`tests/RLoop.Tests/ApplyWorkflowTests.cs`、`tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` と文書 6 件）だけで、A のファイル（`tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs`）が無い。テストはすべて PASS。

- [ ] **Step 5: push して PR を出す**

PR A の番号はブランチ名で取って、本文の `PR_A` を置き換える。本文の件数は Step 2・3 の結果に合わせる。Task C1 で修正を積んだ後は `gh pr edit --body-file` で更新する。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
test "$(git branch --show-current)" = fix/list-shrink-recreate-split
PR_A=$(gh pr view fix/slot-index-after-removal --repo usaturn/resoloop --json number -q .number)
test -n "$PR_A"
git push -u origin fix/list-shrink-recreate-split
sed "s/PR_A/$PR_A/g" <<'EOF' | gh pr create --repo usaturn/resoloop --base fix/slot-index-after-removal --head fix/list-shrink-recreate-split --title "Recreate a managed Component when a declared list member shrinks / 宣言したリスト型メンバーが縮む Component を作り直す" --body-file -
> Includes the commits of usaturn/resoloop#PR_A (the index fix). Merge that one first; after it merges, this PR's diff is only the recreate change.
> usaturn/resoloop#PR_A（index の修正）のコミットを含みます。先にそちらをマージしてください。マージ後は、この PR の差分は作り直しの変更だけになります。

## Summary / 概要

- When a declared list member such as `MeshRenderer.Materials` is shorter than the runtime list, `diff` shows `recreate`, and apply replaces the Component on the same Slot: it creates the replacement, writes and verifies its declared fields, re-points managed references, and then removes the old Component.
- The replacement starts from `initialFields` (their declared values) and type defaults for undeclared members; the plan's `recreate` reason says so.
- Like a Component move, the old Component is removed without `--prune` or `--yes`: the `--yes` rule in `AGENTS.md` is about commands whose purpose is deletion, and the plan shows the replacement in advance. Because the replacement is implicit, apply stops before mutation with `APPLY_LIST_SHRINK_REFERENCED` when something in the hierarchy it read points at the old Component where the declaration does not re-point it. Only keys with a saved record are recreated, so the first adopting apply does not remove existing content.
- The read-back after writing the replacement guards against runtime logic that keeps a list longer than declared. We have not observed this for `MeshRenderer.Materials`; without it, every apply would recreate such a Component, and for a list without references or an empty declaration apply would even report success, because the reference re-check does not read those fields. In that case apply stops with `APPLY_LIST_SHRINK_NOT_CONVERGED` after removing the replacements it created.
- An interrupted recreate resumes by ID in the same session. Otherwise apply stops before mutation with `APPLY_RECREATE_INTERRUPTED` and explains the recovery for its `reason`.
- Compatibility: state gains an optional `components.{key}.supersededId`, written only while a recreate is in progress; `schemaVersion` stays 2. The new codes use the existing exit codes 6 and 7. Applying a state with a recreate in progress with an older resoloop is not supported.
- Reading order: detection and plan (`ListShrinkReason`, `BuildComponentPlans`), the recreate stages in `ApplyAsync`, verification and undo (`VerifyReplacementsAsync`), resume and stops (`ValidateInterruptedRecreates`, `RecreateInterrupted`), and the reference check (`ValidateRecreateReferences`).

- `MeshRenderer.Materials` などの list member を実機より短く宣言すると、`diff` は `recreate` を示し、apply は同じ Slot で Component を作り直します。新しい Component を作って宣言した field を書いて確かめ、管理 Component の参照を張り替えてから、旧 Component を削除します。
- 新しい Component では、`initialFields` は宣言の初期値に、宣言していない member は型の既定値に戻ります。plan の `recreate` の理由にもそう表示します。
- Component の移動と同じく、旧 Component は `--prune` も `--yes` も無しで削除します。`AGENTS.md` の `--yes` の規則は削除そのものが目的のコマンドについての規則で、置き換えは plan で事前に示します。暗黙の置き換えなので、apply が読んだ範囲で、宣言が張り替えない位置から旧 Component を参照しているものがあれば、変更前に `APPLY_LIST_SHRINK_REFERENCED` で止まります。作り直すのは state に記録のある key だけなので、adopt の初回の apply は既存の内容を削除しません。
- 新しい Component を書いた後の読み直しは、runtime が list を宣言より長いまま残す場合への備えです。`MeshRenderer.Materials` では観測していませんが、これが無いと apply のたびにその Component を作り直し、参照を含まない list や空の宣言では、参照の再確認の対象にならないため成功を返し続けます。この場合は、この apply で作った新しい Component を削除したうえで `APPLY_LIST_SHRINK_NOT_CONVERGED` で止まります。
- 中断した作り直しは、同じセッションの中で ID を使って再開します。それ以外は変更前に `APPLY_RECREATE_INTERRUPTED` で止まり、`reason` ごとの復旧手順を示します。
- 互換性: state に、作り直しの途中だけ書く省略できる `components.{key}.supersededId` を足します。`schemaVersion` は 2 のままです。新しいコードは既存の終了コード 6 と 7 を使います。作り直しの途中の state を古い版の resoloop で apply することには対応しません。
- 読む順序: 検出と plan（`ListShrinkReason`、`BuildComponentPlans`）、`ApplyAsync` の作り直しの段階、検証と取り消し（`VerifyReplacementsAsync`）、再開と停止（`ValidateInterruptedRecreates`、`RecreateInterrupted`）、参照の検査（`ValidateRecreateReferences`）。

Refs orange3134/resoloop#5 (option (a): apply recreates automatically / 選択肢 (a): apply が自動で作り直す)

## Root cause / 原因

ResoniteLink 0.13.1 cannot remove list elements. On Resonite 2026.9.18.82, sending `[A]` to a list that holds `[A,B]` leaves `[A,B]`, sending `[]` leaves it unchanged, and sending `[B]` afterwards gives `[B,B]`. ResoniteLink can call sync methods, but `MeshRenderer` exposes only `AutoRig`, `SplitSubmeshes` and `MergeByMaterial`, and none of them takes a list element to remove. A shorter declaration therefore never converged in place: for a list of world references such as `Materials`, apply stopped with `APPLY_REFERENCE_NOT_RETAINED` after its other changes were already written. The pre-write checkpoints of a Component created in an apply now keep only the reference selectors written at creation, so a retry after a lost create response can still bind the created Component instead of creating another.

ResoniteLink 0.13.1 には list の要素を削除する操作がありません。Resonite 2026.9.18.82 で、`[A,B]` を持つ list に `[A]` を送っても `[A,B]` のまま、`[]` では変わらず、続けて `[B]` を送ると `[B,B]` になりました。ResoniteLink は同期メソッドを呼べますが、`MeshRenderer` の同期メソッドは `AutoRig`・`SplitSubmeshes`・`MergeByMaterial` だけで、list の要素を指定して削除するものはありません。そのため短い宣言はその場では収束せず、`Materials` のようにワールドの参照を要素に持つ list では、apply はほかの変更を書き込んだ後に `APPLY_REFERENCE_NOT_RETAINED` で止まっていました。また、apply で作る Component の、フィールドを書く前の checkpoint には、作成時に書いた参照の selector だけを保存するようにしました。作成応答を失った後の再実行が、作成済みの Component を見つけられずにもう 1 つ作ることを防ぐためです。

## Verification / 確認

- Linux Dev Container, .NET SDK 10.0.201: `dotnet restore ResoLoop.slnx && dotnet build ResoLoop.slnx --configuration Release --no-restore && dotnet test ResoLoop.slnx --configuration Release --no-build --no-restore`: RLoop.Tests 397 and RLoop.IntegrationTests 19 passed, 0 warnings. Pack and the smoke test of the installed tool passed. Windows is left to the CI of the upstream PR; the CI of this fork has not run.
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` stops the shrinking apply at every write, before the write lands and after it lands with its response lost, in two scenarios, and cancels it at every progress notification in one. Each time the next apply in the same session converges (or stops before any write on `replacement-unverified` until the recovery in its suggestions), and a world reload during a recreate stops plan and apply before any write without changing the state. Convergence means that every renderer and Source is bound to exactly one key, the declared lists, managed references on the replacement, saved indexes that match the Slot, and no writes on the next apply or after a world reload. A moved Component's source that an interrupted move leaves behind is an existing issue and not checked.
- With `src/` reverted to the index fix, 53 of the 60 new test cases fail, and every other test passes. The other 7 pin behavior this PR keeps: a list that grows or is reordered, the fake client that cannot shrink a list, a shorter list inside a sync object, a moved Component with a shorter list, the first adopting apply, and the asset migration stop with a legacy state.
- Real Resonite: (to be filled in after the check on a `ResoLoop_Test*` Slot)

- Linux の Dev Container（.NET SDK 10.0.201）で上記のコマンドを実行し、RLoop.Tests 397 件と RLoop.IntegrationTests 19 件が成功し、警告は 0 件でした。pack と、導入したツールでのスモークテストも成功しました。Windows での確認は上流 PR の CI に任せます。この fork の CI は動かしていません。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` は、2 つのシナリオで作り直しの apply を書き込みの位置ごとに止め（反映前の失敗と、反映後の応答の喪失）、1 つのシナリオで進捗の通知ごとにキャンセルします。そのたびに、同じセッションの次の apply が収束する（または `replacement-unverified` で書き込みの前に止まり、suggestions の復旧手順の後に収束する）こと、作り直しの途中で再読込すると plan と apply が書き込みの前に止まり、state が変わらないことを確かめます。収束とは、renderer と Source がそれぞれちょうど 1 つの key に結び付き、list が宣言どおりで、管理 Component の参照が新しい Component を指し、保存した index が Slot と一致し、次の apply と再読込後の apply の書き込みが 0 件になることです。移動の中断で移動元が残る既存の問題は確かめていません。
- `src/` を index の修正の状態に戻すと、追加した 60 件のうち 53 件が失敗し、それ以外のテストはすべて成功します。残りの 7 件は、この PR が保つ挙動（長くなる list と並べ替えた list、list を縮められない偽クライアント、sync object の中の短い list、短い list を持つ Component の移動、adopt の初回の apply、古い state でのアセット移行の停止）を固定するテストです。
- 実機での確認:（`ResoLoop_Test*` の Slot で確認した後に記入）

## Known limitations / 既知の制限

- A recreate interrupted and followed by a world reload stops with `session-changed`. When another key of the same type shares the Slot, apply cannot tell the Components apart, and the suggestions only say what to check.
- These recoveries need a manual edit of the state file, which the suggestions describe and the docs do not: `session-changed`, the second suggestion of `replacement-unverified`, and a key whose create was interrupted that matched unmanaged content (`STABLE_COMPONENT_AMBIGUOUS`). Are suggestions fine for these, or would you prefer CLI operations?
- `APPLY_LIST_SHRINK_REFERENCED` checks only the hierarchy that apply read; a reference from elsewhere breaks when the old Component is removed.
- An asynchronous refill after the read-back is not detected until the next apply. A list inside a sync object is not recreated.
- A key with a saved ID whose managed Component was removed by hand can match an unmanaged Component of the same type at its index and recreate it.
- The limitations of the index fix (usaturn/resoloop#PR_A) apply too.

- 作り直しの途中で中断してワールドを再読込すると、`session-changed` で止まります。同じ Slot に同じ型の key がほかにある場合は、apply は Component を区別できず、suggestions は確かめる点を示すだけです。
- 次の復旧には state の手編集が要り、suggestions には書いていますが文書には書いていません: `session-changed`、`replacement-unverified` の 2 つ目の手順、作成が中断した key が管理外の内容に照合された場合（`STABLE_COMPONENT_AMBIGUOUS`）。suggestions での案内のままでよいか、CLI の操作を望むかを教えてください。
- `APPLY_LIST_SHRINK_REFERENCED` が調べるのは apply が読んだ階層だけです。その外からの参照は、旧 Component の削除で切れます。
- 読み直しの後の非同期の詰め直しは、次の apply まで検出しません。sync object の中の list は作り直しません。
- 保存 ID のある key で、管理 Component が手で削除されていると、同じ index の同じ型の管理外の Component に照合され、作り直しの対象になることがあります。
- index の修正（usaturn/resoloop#PR_A）の既知の制限も当てはまります。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Expected: PR の URL が表示される。この PR はマージしない（D-8）。

- [ ] **Step 6: 古い fork PR #5 に、作り直したことをコメントして close する**

PR B の番号はブランチ名で取って、本文の `PR_B` を置き換える。コメントに失敗したら close しない。ブランチ `fix/list-shrink-recreate` は残す（D-12）。その後、agent-handoff スキルで引き継ぐ（Global Constraints の区切り）。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
PR_B=$(gh pr view fix/list-shrink-recreate-split --repo usaturn/resoloop --json number -q .number)
test -n "$PR_B"
sed "s/PR_B/$PR_B/g" <<'EOF' | gh pr comment 5 --repo usaturn/resoloop --body-file -
Rebuilt from upstream main as #PR_B with the split scope (recreate and resume within one session; stop before mutation otherwise), stacked on the Component index fix. Closing this PR; the branch `fix/list-shrink-recreate` stays for reference.

上流の main から #PR_B として作り直しました（範囲は分割案: 同じセッションの中での作り直しと再開。それ以外は変更前に停止）。Component の index の修正の上に積んでいます。この PR は close し、ブランチ `fix/list-shrink-recreate` は参照用に残します。
EOF
gh pr close 5 --repo usaturn/resoloop
```

---

## Part C: 判定基準（ユーザの判断が要る作業を含む）

### Task C1: レビュー（PR ごとに 1 ラウンド）

**Files:** 指摘に応じて Part A・B と同じファイル

- [ ] **Step 1:** PR A と PR B を、それぞれ 1 ラウンドだけレビューする。レビューの方法（どのモデル・スキルで行うか）はユーザに確認する。pr-review スキルがレビュー結果を `external/resoloop/reviews/#<PR>-<branch>/` に書くことは許可されている（Global Constraints）。
- [ ] **Step 2:** 修正の対象は、現行の HEAD で再現し、Spec の I1〜I6 のどれかを破る指摘。それ以外は Spec 10.3 の重大度の定義で判断し、レビュアーが付けた重大度はこの定義に照らして付け直してよい。修正はそれぞれのブランチに積む（別のブランチや PR は作らない）。Low はまとめてユーザに判断を仰ぐ。修正の後は全体を再レビューせず、修正の差分と回帰テストだけを確かめる。
- [ ] **Step 3:** 同じ不変条件（I1〜I6）を破る指摘、または同じ問題群（create-reso-world#5 のコメント「原因調査」の 4.1 index の意味、4.2 初期化・検証の完了、4.3 所有権の根拠）に属する指摘が 2 件目になったら、修正を止め、どの不変条件・問題群がどの入力で破れたかをユーザに報告し、「既知の制限とする」「PR を分ける」「設計を見直す」のどれにするかの判断を仰ぐ。設計を変える場合は、ユーザの承認を得てから、create-reso-world に Spec（と計画）を直す PR を別に出し、Spec の 12 章に理由を残す。その PR がマージされてから実装を再開する。
- [ ] **Step 4:** A に修正を積むとき、A を変えたら B を A の上へ載せ直す。上流に出す前に、A を 2 件、B を 2 件にまとめ直す（この環境のエージェントは対話式の `git rebase -i` を使えないので、`fixup!` と `--autosquash` を使う）。

```bash
set -euo pipefail
R=/workspaces/reso-world/external/resoloop
A=$R/.worktrees/slot-index-after-removal
B=$R/.worktrees/list-shrink-recreate-split
# A を変える前に、A の先頭を記録する
OLD_A=$(git -C "$A" rev-parse HEAD)
# A へのレビュー修正は、対象のコミット（Task A2 か A3 のコミット）を指定して積む
git -C "$A" commit --fixup=<A2 か A3 のコミットの SHA>
# まとめ直し（非対話。git 2.44 以降は -i なしでも --autosquash が fixup をまとめる）
git -C "$A" rebase --autosquash origin/main
# A を変えたら、B を新しい A の上へ載せ直す
git -C "$B" rebase --onto fix/slot-index-after-removal "$OLD_A" fix/list-shrink-recreate-split
```

載せ直した後は、Task A4 Step 1〜2 と Task B8 Step 2〜4 をやり直す（Task B8 Step 1 の文書の置き換えと、PR の作成（A4 Step 3、B8 Step 5）、PR #5 へのコメント（B8 Step 6）は繰り返さない）。テストを足した・削った場合は、A4 Step 1 と B8 Step 2 の Expected の件数と一覧を直してから確かめる。push の前に `git fetch origin` と `git log HEAD..origin/<branch>` で他者のコミットが無いことを確かめ、`git push --force-with-lease=<branch>:<確かめた SHA>` を使う（上流に出す前の A・B の force push は Spec 10.4 で認められている）。PR の本文の件数は `gh pr edit --body-file` で更新する。上流に出す前の最後のまとめ直しでは、Task B8 Step 4 の 2 件のコミット本文に `Refs orange3134/resoloop#5` の行（`Co-Authored-By` の前）を足す。

### Task C2: 実機での確認（ユーザの明示的な指示があるときだけ）

**Files:** なし（`ResoLoop_Test*` の Slot だけを使う）

- [ ] **Step 1:** ユーザに、実機での確認の実施と、使うワールドを確認する。保存と再読込を伴うので、使い捨ての新しいワールドを勧める。ユーザのワールドを使う場合は、ほかの未保存の変更も一緒に保存されることを伝えて了承を得る。ユーザのワールドの既存の内容には apply しない。
- [ ] **Step 2:** B の worktree で CLI をビルドし、global の resoloop やロックを変えずに、ビルドした DLL を直接実行する（以降の `dotnet "$RESOLOOP_DLL"` は、シェルを開くたびに変数を設定し直してから使う）。告知されているワールドを `discover` で表示し、SessionName・SessionId・Url をユーザに見せて、使うワールドを選んでもらう。以降のコマンドには接続先を付ける。第一候補は `--url auto --session <SessionId>`（1 件だけ一致しなければ止まる）。UDP の告知がコンテナに届かない場合は、ユーザから `ws://<host>:<port>` を聞いて接続先のワールドを画面で確かめてもらう。この経路では、以降のすべての `--url auto --session <SessionId>` を同じ確認済みの `--url ws://<host>:<port>` に置き換える。環境変数だけに頼って接続先を省略しない。

```bash
set -euo pipefail
cd /workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split
dotnet build src/RLoop.Cli/RLoop.Cli.csproj --configuration Release
RESOLOOP_DLL=/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split/src/RLoop.Cli/bin/Release/net10.0/resoloop.dll
git rev-parse HEAD
dotnet "$RESOLOOP_DLL" --version
dotnet "$RESOLOOP_DLL" discover --json
```

`--version` は NuGet 版と同じ値を返すので、ビルドしたコミットは `git rev-parse HEAD` で記録する。接続先を決めたら `dotnet "$RESOLOOP_DLL" status --url auto --session <SessionId> --json` で ResoniteVersion と ResoniteLinkVersion を記録する。

- [ ] **Step 3:** 上流の `AGENTS.md` に従い、型とメンバー名を推測しない。次の確認用の文書の型とメンバー名を、`dotnet "$RESOLOOP_DLL" type search` / `type describe` / `type specialize` で確かめ、違えば直す。これらの型確認のコマンドにも、Step 2 で選んだ `--url auto --session <SessionId>`（明示 URL の経路なら同じ確認済み URL）を付ける。文書は scratchpad に置く（create-reso-world のプロジェクトには置かない）。Materials が 4 つの MeshRenderer と、それを参照する管理 Component を作る。値のリストを持つ Component（例: `ValueMultiplexer<float>` の `Values`）と、syncObject を要素とするリストを持つ Component（例: `ValueGradientDriver<float>` の `Points`）も 1 つずつ足す（どちらも型とメンバー名は推測なので、`type describe` で確かめてから使う。`SkinnedMeshRenderer.BlendShapeWeights` のように runtime が長さを決めるリストは使わない）。

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
set -euo pipefail
RESOLOOP_DLL=/workspaces/reso-world/external/resoloop/.worktrees/list-shrink-recreate-split/src/RLoop.Cli/bin/Release/net10.0/resoloop.dll
DOC=/tmp/claude-1000/<scratchpad>/list-shrink-4.json
dotnet "$RESOLOOP_DLL" validate "$DOC" --strict --url auto --session <SessionId> --json
dotnet "$RESOLOOP_DLL" diff "$DOC" --url auto --session <SessionId> --json
dotnet "$RESOLOOP_DLL" apply "$DOC" --url auto --session <SessionId> --json --profile
```

`<scratchpad>` は実行するセッションの scratchpad のパスに、`<SessionId>` は Step 2 で選んだ値に置き換える。明示 URL の経路では、validate・diff・apply のすべてに同じ `--url ws://<host>:<port>` を渡す。state は、文書のあるディレクトリの `.resoloop/state/` に作られる。Step 4 の diff・apply・inspect にも、同じ接続先を明示する。

- [ ] **Step 4:** `Materials` を `["$ref:m1","$ref:m2","$ref:m3"]` にした文書（`list-shrink-3.json`。値のリストと syncObject のリストも 1 つずつ短くする）で `diff` を実行し、`renderer` などが `recreate` になることを確かめる。続けて `apply` を実行して収束すること（`renderer` の Materials が 3 つ、`holder` の `Reference` が新しい Component を指す）を `inspect` で確かめ、もう一度 `apply` して書き込みが 0 件になることを確かめる。書き込み 0 件は、`apply --json --profile` の `data.profile.mutations` が 0、または `created` が false で `slotsCreated`・`slotsUpdated`・`slotsDeleted`・`componentsAdded`・`componentsUpdated`・`componentsDeleted`・`assetsImported` がすべて 0 であることで判定する。apply の前に `diff --json` で変更が無いことも見る。値のリストか syncObject のリストがその場で縮んだ場合（`recreate` にならず収束した場合）は、止まってユーザに報告する（検出の範囲を種類で絞るかを判断してもらう。Spec 10.3）。
- [ ] **Step 5:** ユーザにワールドの保存と再読込を依頼する。再読込の後に `discover` で接続先を決め直し（セッションやポートが変わることがある）、ユーザに接続先を再確認する。以降の `<SessionId>` または明示 URL は、この新しく選んだ値に置き換える。`apply --url auto --session <SessionId>` を実行して、書き込みが 0 件になることを確かめる。明示 URL の経路では同じ新しい URL を渡す。
- [ ] **Step 6:** 確認用の root Slot（`ResoLoop_Test_ListShrink`）の ID を `dotnet "$RESOLOOP_DLL" inspect ID --url auto --session <SessionId> --json` で確かめてから、同じ宛先に `dotnet "$RESOLOOP_DLL" slot delete ID --yes --url auto --session <SessionId>` で削除する。再読込後は Step 5 で再確認した接続先を使う。明示 URL の経路では inspect と slot delete の両方に同じ新しい URL を渡す。ユーザにワールドの保存をもう一度依頼し、保存データからテストの Slot を消す。結果（実行したコマンド、ビルドしたコミット、Resonite と ResoniteLink の版、判定に使った件数）を PR B の Verification の「Real Resonite」に記入する。
- [ ] **失敗したとき:** Step 3〜5 のどこで止まっても、エラーの JSON、`inspect ID --url auto --session <SessionId> --json`、state のコピーを残してから、Step 6 と同じ宛先確認・削除手順で `ResoLoop_Test_ListShrink` の ID だけを削除する。明示 URL の経路でも inspect と削除に同じ確認済み URL を渡す。接続先を再確認できない場合は削除せず止まる。

### Task C3: 上流への提出（D-11、文面をユーザに確認）

- [ ] **Step 0（前提）:** Task C1・C2 が済み、判定基準（Spec の 10.3）を満たしていなければ、止まってユーザに報告する（C2 を実施しない場合も止まり、判断を仰ぐ）。`git -C /workspaces/reso-world/external/resoloop fetch --multiple upstream origin` を実行し、`upstream/main` がまだ `b3a84ae` か確かめる。進んでいれば、A を `upstream/main` に rebase し、B を Task C1 Step 4 の `--onto` で載せ直し、Task A4 Step 1〜2（`BASE=upstream/main`）と Task B8 Step 2〜3 をやり直してから push する。衝突が大きい場合は止まってユーザに報告する。
- [ ] **Step 1（文面）:** fork の Issue・PR の本文を scratchpad に書き出し、次を書き換えた文面をユーザに見せて確認を取る。`Fixes usaturn/resoloop#…` を `Fixes #<上流の Issue>` に、PR B の冒頭を「Includes the commits of #<上流の PR A>. Merge #<上流の PR A> first; after it merges, this PR's diff is only the recreate change.」（英日併記）に、「Real Resonite」を Task C2 の結果に。`grep -nE 'usaturn/resoloop#|ISSUE_A|PR_A|PR_B|to be filled in'` で書き換え漏れが無いことを確かめる。A のコミットに上流の Issue の `Refs` は足さない（PR 本文の `Fixes` で足りる）。上流 Issue #5 へのコメントは、Spec 10.5 の要点 3 つ（回答が無いまま (a) で出したこと、(a) を選んだ理由、(b)・(c) を望む場合に PR B を絞れること）と、state の手編集を要する復旧手順の扱いの問いを含める。
- [ ] **Step 2（順に出す）:** 確認を取った後、(a) `gh issue create --repo orange3134/resoloop --body-file ...` → (b) `gh pr create --repo orange3134/resoloop --base main --head usaturn:fix/slot-index-after-removal --body-file ...` → (c) `gh pr create --repo orange3134/resoloop --base main --head usaturn:fix/list-shrink-recreate-split --body-file ...` → (d) `gh issue comment 5 --repo orange3134/resoloop --body-file ...` の順に出す。各段の出力の番号を次の本文に入れる。fork の PR の本文に、上流の PR の URL を追記する。
- [ ] **Step 3（提出後）:** Spec 10.4 の「上流に出した後」に従う。A に上流のレビュー修正やメンテナーのコミットが積まれたら fetch してその上にコミットを足す。A が変わって B と食い違ったら、ユーザの確認を取ってから B を Task C1 Step 4 の `rebase --onto` で載せ直し、Task B8 Step 2・3 をやり直してから `--force-with-lease` で push し、PR B にコメントする。Task B8 Step 4 のまとめ直しは行わない。A が変わらずにマージされた場合は何もしない。
- [ ] **Step 4（リリース後）:** `docs/resoloop-fork-workflow.md` の「上流のリリース後の切り替え」に従い、ロックの `RESOLOOP_NUGET_VERSION` を更新し、`bash .devcontainer/install_resoloop.bash` と `bash scripts/check-layout.sh` を実行してコミットする。各プロジェクトで `resoloop skills sync --check` → 差分の確認 → `resoloop skills sync --update` を行う。fork の PR A・B と fork の Issue A を close する（D-8）。引き継ぎの正本だった fork の Issue usaturn/resoloop#6 にも、Spec・計画（create-reso-world#8）と上流の PR・Issue のリンクをコメントしてから close する（どれも close の前にユーザに確認する）。
