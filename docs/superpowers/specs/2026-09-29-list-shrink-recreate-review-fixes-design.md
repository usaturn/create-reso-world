# list-shrink-recreate レビュー指摘の修正設計

- 日付: 2026-09-29
- 対象 PR: usaturn/resoloop #5（`fix/list-shrink-recreate` → `fix/asset-url-save-migration`）
- 現行 HEAD: `d615eebc0bfa1b98df678e26e6609433a002173d`（レビュー対象 HEAD と同じ）
- 入力: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`
  - `claude-opus-5-5.md`（対象 HEAD `d615eebc0bfa`）
  - `SWE-2-Max.md`（対象 HEAD `d615eebc0bfa`）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（対象 HEAD `d615eebc0bfa`）
  - `qwen3.8-max.md`（対象 HEAD `d615eebc0bfa`）
- brainstorming の経路: **bounded**（既存の plan/apply パイプライン `src/RLoop.Core/WorldService.cs` の修正で、新しいサブシステムやインターフェースの変更は無い）

## 検証の方法

`git -C external/resoloop worktree add --detach` で `d615eeb` を一時 worktree に取り出し、指摘ごとに最小の再現テスト（`ApplyWorkflowTests` の偽クライアントを使用）を追加して `dotnet test --filter` で実行した。7 件すべてで指摘どおりの誤動作を確認した。worktree と一時ディレクトリは検証後に削除済み。

| 再現 | 結果 |
| --- | --- |
| O-M1 | `initialFields.Note` を runtime で `runtime-updated` に変えたあと 4→3 要素に縮めると、作り直し後の値が `initial` に戻る。plan の `recreate` の diff は `Materials` だけ |
| O-L1 | `identityFields` なしの同型 sibling があり refill で `APPLY_LIST_SHRINK_NOT_CONVERGED` になると、sibling の state `componentIndex=0` に対し実際の位置は 1。再読込後に宣言を 4 要素へ戻した plan が `APPLY_COMPONENT_OWNERSHIP_CONFLICT`（sibling が旧 renderer を superseded として奪い合う） |
| O-L2 / S-L2 | 旧 Component 削除前に中断（`FailOnWrite=2`）→ renderer を文書から外して `--prune --yes` → 削除計画は置換側だけで、旧 Component `C5` が Slot に残り、state からも key が消える |
| Q-M1（同一セッション） | 同じ中断のあと renderer を別 Slot `Debris` へ移す → apply は成功し、旧 `C5` が `Rubble` に管理外で残る。state には `supersededId` が無い |
| Q-M1（再読込後） | 同じ中断 → `ReloadWorld` → 別 Slot へ移す → 停止せず、index の tie-break で旧側を移動元に選び、置換側（3 要素）が `Rubble` に管理外で残る |
| S-M1 | refill 環境で、同じ apply で新規作成する `source2`（`Target: "$ref:renderer"`）を追加 → `NOT_CONVERGED` 後、`source2.Target` が削除済みの置換 Component `C6` を指す |
| Q-M2 | refill 環境で、置換 Component 作成後・検証前に中断（後続の新規 Component の作成で `FailOnWrite=2`）→ 同一セッションで再実行すると検証が飛ばされ、旧 `C5` が削除される。置換 `C6` は 4 要素のまま残り、`APPLY_REFERENCE_NOT_RETAINED` で停止 |

## 分類

解消済み 0 / 対応する 8 / 判断保留 0 / 対応しない 14（計 22）。ID の接頭辞は O = claude-opus-5-5、S = SWE-2-Max、D = deepseek、Q = qwen3.8-max、U = 各レビューの Unverified candidates。O-M1 は挙動とドキュメントの 2 件に分けて数える。

### 対応する

| ID | 区分 | 修正 | 一行 |
| --- | --- | --- | --- |
| O-L2 | (a) | G1 | 中断した recreate の key を外して prune すると旧 Component が残る |
| S-L2 | (a) | G1 | `SupersededId` が残ったまま relocate / 宣言削除すると旧 Component が残る |
| Q-M1 | (a) | G1 | 中断した recreate の続きで別 Slot へ移すと片方が管理外で残る（同一セッション・再読込後とも） |
| O-U1 | (a) | G1 | O の未検証候補（relocate）。Q-M1 と同じ再現で確認した |
| Q-M2 | (a) | G2 | 置換作成後の中断を再開すると refill 検証が飛ばされ、旧 Component が削除される |
| S-M1 | (a) | G3 | `NOT_CONVERGED` のロールバックで、後続の新規 Component に焼き込まれた置換 ID が宙吊りになる |
| O-L1 | (a) | G4 | refill のロールバック後、同じ Slot の sibling の `componentIndex` が実レイアウトとずれ、再読込後に停止する |
| O-M1b | (b) | G5 | `docs/DECLARATIVE.md:57` などの「`initialFields` は再 apply で上書きされない」が、リスト縮小の作り直しでは成り立たない |

### 判断保留

なし。

### 対応しない

| ID | 理由 |
| --- | --- |
| O-M1a | 作り直し時に `initialFields` の runtime 値や未宣言 member を引き継ぐか、plan に表示するかは仕様の判断。挙動は変えず、ドキュメント（O-M1b）だけ実際の挙動に合わせる |
| O-L3 | 実機で非同期に refill されるリストがあるかは未確認で、偽クライアントでは再現できない。対策には state への作り直し履歴の記録という設計が要る |
| O-I1 / S-I1 / D-I1 / Q-I1 | `recreate` と新しいエラーコード 3 件の記載漏れ（Info）。fork の `AGENTS.md` は CLI の挙動を変えたら README の例と影響する skill を更新するとしているが、README の例に action の一覧は無く、skill は「workflows, not command mirrors」とされる。事実誤認の箇所は G5 で直す |
| S-L1 | `--prune` で消える Component からの参照も違反として数えるのは、変更前に止まる安全側の停止。検査を緩めるかは仕様の判断で、prune を先に単独で実行すれば回避できる |
| S-I2 | 偽クライアント `SetFields` の `JsonNode.Parse` は、現行テストに該当する入力が無い。テスト基盤に対する将来の保険 |
| S-U1 | 未検証。中断 + 手動削除 + 同型混在 + フィールド無しの組み合わせに限られる |
| S-U2 | 作成時に参照を解決できず空で作った Component が中断すると再開時に `initialFields` が適用されないのは、本 PR 以前の通常作成にもある挙動で、本 PR が導入したものではない |
| S-U3 | 実機の ResoniteLink が作成直後に member を完全に返すかは実機での確認事項 |
| D-L1 | 再読込後は旧 Component がすでに消えていても停止するのは fail-closed の設計判断。state の `supersededId` を消せば回復できる |
| D-I2 | 参照検査が観測済み snapshot に限られる旨の plan 警告は機能追加の提案 |
| D-U1 | レビュアー自身が実害を確認できなかった未検証候補 |

## 修正方針

変更はすべて `fix/list-shrink-recreate` に載せる。`external/resoloop` のメイン checkout は PR #4（`fix/asset-url-save-migration`）の作業で使われているため、実装は `fix/list-shrink-recreate` を checkout した専用の worktree で行う。テストは `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs` に既存テストと同じ作法で追加する。

補助として、次の意味で「検証対象の作り直し」を定義する: `Superseded is not null && RelocationSource is null` で、かつ旧 Component がその Component の Slot 上にあること（`ComponentRuntime.VerifiesRecreate`）。新規に作り直す Component と、中断から再開した作り直しの両方が該当する。relocate に伴う旧 Component の削除（G1）と、中断した relocate の再開で別 Slot に残った旧 Component の削除は該当しない。

### G1: 中断した recreate の旧 Component を relocate と宣言削除でも扱う

`BuildComponentPlans`（`WorldService.cs:1063-1104`）と `BuildDeletionPlans`（`WorldService.cs:1366-1385`）、prune ループ（`WorldService.cs:567-578`）を変える。

- 同一セッション
  - 旧 Component（`stateComponent.SupersededId`）は、`node.Existing` に限らず `prepared.SnapshotSlots` の全 Component から ID で探す。relocate 中も探す。見つけた旧 Component は、移動先の照合候補からも移動元（`RelocationSource`）の照合候補からも除く。
  - relocate の場合は、見つけた旧 Component を `Superseded` に入れる。フィールド更新のあとの既存の削除ループが旧 Component を削除し、state の `supersededId` を消す。plan の `relocate` の reason に、中断した作り直しの旧 Component も削除することを 1 文加える。検証対象の作り直しには当たらないため、refill 検証とロールバックの対象にはしない。置換側が見つからない場合は、旧 Component を移動元として扱い、通常の relocate と同じく移動先に作成して旧 Component を削除する（実装時に変更。検証対象にするとロールバックで state の Slot が合わなくなるため）。
  - 宣言から外した key の場合は、`BuildDeletionPlans` で旧 Component の削除を置換側の削除より**前**に計画に加える。prune ループでは、削除した ID がその key の `supersededId` と一致するとき、state の key を消さずに `supersededId` だけを消して checkpoint する。これで置換側の削除前に中断しても、置換側は key で追跡されたまま残る。plan には同じ key の `delete` が 2 件（旧 Component と置換側）出る。
- 再読込後（別セッション）
  - `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` の停止条件から `!relocating` を外し、relocate でも変更前に停止する。候補の列挙は、relocate のときは移動元 Slot の Component から行う。
  - 宣言から外した key に `supersededId` が残っている場合も、`BuildDeletionPlans` で同じエラーで停止する。例外の組み立ては 1 つのヘルパーにまとめる。
  - 停止は `--prune` の有無によらない（宣言中の key に対する既存の停止と同じ扱い）。

検証: 再現テストを反転させた次のテストを追加する。

1. 同一セッション・宣言削除: 中断 → key を外して `--prune --yes` → `Rubble` に `Test.Renderer` が 0 件、state に `renderer` が無い
2. 同一セッション・宣言削除・置換側の削除前に中断: state の `renderer` が置換側の ID を持ち、`supersededId` が無い。再実行で 0 件に収束する
3. 同一セッション・relocate: 中断 → `Debris` へ移す → `Rubble` に 0 件、`Debris` に 1 件、`supersededId` が無い。再 apply の書き込みが 0
4. 再読込後・relocate と 再読込後・宣言削除: plan と apply が `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` で停止し、書き込み 0、state のハッシュが変わらない

### G2: 再開した作り直しも refill を検証する

refill 検証ループ（`WorldService.cs:484-507`）の対象を、検証対象の作り直し全体に広げる。

- 新規に作り直した Component（`Existing is null`）は現状どおり、作成時に設定できなかったフィールドを設定してから観測する。
- 再開した作り直し（`Existing` が置換側）はフィールドを設定せず、`GetComponentAsync` で観測だけ行う。
- リストが宣言より長ければ、現状と同じロールバック（置換側を削除し、state を旧 Component に戻して `supersededId` を消し、`APPLY_LIST_SHRINK_NOT_CONVERGED` で停止）を行う。state の `componentIndex` は G4 の計算で直す。
- 残る制約: 置換側を参照未解決のまま空で作成した直後に中断し、runtime がフィールド設定の後でだけ refill する場合は、再開時の観測では検出できない。この場合は次の apply で通常の作り直しとして検出され、`NOT_CONVERGED` で停止する（作り直しは 1 回だけ余分に起きる）。

検証: refill を有効にし、置換作成後・検証前に中断（後続の新規 Component の作成で `FailOnWrite`）→ 同一セッションで再実行すると `APPLY_LIST_SHRINK_NOT_CONVERGED` で停止し、旧 Component が残り、置換側が削除され、state の `id` が旧 Component で `supersededId` が無いことを確かめる。

### G3: 検証前の置換 Component を新規 Component の作成時参照に使わせない

`ApplyAsync` の `byKey`（`WorldService.cs:447-448`、`474`）を変える。

- 検証対象の作り直しは、初期の `byKey` にも作成ループでの登録にも入れない。そのため、同じ apply で後から作成する新規 Component がその key を参照していても `CanResolveAll` が成立せず、参照フィールドは作成時に焼き込まれない。検証後のフィールド更新ループで設定される（前方参照と同じ既存の経路）。
- 検証ループの直前に、検証対象の作り直しをすべて `byKey` に登録する。作り直した Component 自身の作成時フィールドの解決と、後続のフィールド更新ループはこれを使う。
- 残る制約: 同じ apply で作り直す 2 つの Component が互いを参照し、片方だけがロールバックされた場合は、もう片方が削除済みの ID を持つ。次の apply でフィールドを解決し直せば直る（`initialFields` 経由の参照は直らない）。
- 成功経路でも、作り直し対象を参照する新規 Component は「空で作成 → フィールド設定」の 2 回の書き込みになる。

検証: refill を有効にし、同じ apply で新規 `source2`（`Target: "$ref:renderer"`）を作成 → `NOT_CONVERGED` 後、`source2.Target` が削除済みの ID を指さない。宣言を 4 要素に戻して apply すると `source2.Target` が旧 Component を指して収束する。

### G4: ロールバック後に同じ Slot の `componentIndex` を実レイアウトに合わせる

`BuildComponentPlans` の再計算（`WorldService.cs:1109-1117`）を関数に切り出し、plan 時とロールバック時の両方で使う。

- ロールバック時は、取り消した後の最終レイアウトで同じ Node の全管理 Component の `componentIndex` を計算し直して state に書き、checkpoint してから停止する。
  - 元の snapshot の並びから、同じ Node で保留中の他の作り直しの旧 Component を除く
  - 取り消した Component は旧 Component の位置
  - そのほかの既存 Component は元の位置
  - 今回作成した他の Component は作成順に末尾
- G2 の再開時ロールバックでは、取り消した Component 自身の state（前回の中断時に最終レイアウトで保存した値）もこの計算で直る。

検証: `identityFields` なしの同型 sibling を置いて refill で停止させ、停止直後の state の `componentIndex` が `renderer`・`sibling` とも実際の位置と一致すること、`ReloadWorld` 後に宣言を 4 要素へ戻した plan / apply が衝突せずに収束し、再 apply の書き込みが 0 であることを確かめる。

### G5: `initialFields` の説明を実際の挙動に合わせる（O-M1b）

次の 3 か所に、リスト要素数を減らす apply（plan の `recreate`）では Component を作り直すため `initialFields` が初期値に戻り、宣言していない member は型の既定値に戻ることを 1 文ずつ加える。挙動は変えない。

- `docs/DECLARATIVE.md:57`（「adopt・再applyでは上書きされません」）
- `README-DETAILS.md:181`（「`initialFields`はComponent新規作成時だけ設定してruntime dataを上書きしない値です」）
- `skills/codex/resonite-build/SKILL.md:33`（「put runtime-owned defaults in `initialFields` so reapply does not erase them」）

検証: 差分を読んで 3 か所の記述が一致していることを確かめ、`ProjectInitializerTests`（同梱 skill の扱い）を含む `tests/RLoop.Tests` を通す。

## 反映の手順（承認後）

1. 関連テスト: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~ApplyWorkflowTests"`
2. 変更の種類に応じた検証（resoloop fork の変更）: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj`
3. `fix/list-shrink-recreate` に commit し、`git push origin HEAD` で既存 PR #5 に反映する。新しい PR や `*-review-fixes` ブランチは作らない
4. PR #5 に review-fix-planning のコメントを作成または更新する

`scripts/resoloop-fork.sh test` による全テストと、ワールドのプロジェクトの `uv run pytest` は反映の条件にしない。

## 範囲外と注意

- PR #5 のベースブランチ `fix/asset-url-save-migration` は、PR #5 の分岐後に `DetectSavedAssetMigrations` と `CreateComponentState` を変えるコミット（`e61d83d`、`bf8616e` など）が入り、さらに先へ進んでいる。PR #5 は同じ箇所を変えているため、ベースへの追従時に競合する見込みが高い。今回の修正ではベースへの追従（rebase / merge）を行わず、別作業とする。
- 作り直し時に runtime 値を引き継ぐかどうか（O-M1a）と、非同期 refill の実機確認（O-L3）は、別途判断が必要な論点として残す。
