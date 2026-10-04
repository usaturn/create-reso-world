# PR #9 list 短縮・再開処理のレビュー修正設計

- 日付: 2026-10-02
- 経路: **architectural**（置換の検証順序・巻き戻し・参照保持が相互依存するため）
- 入力: `external/resoloop/reviews/#9-fix-list-shrink-recreate-split/` の8ファイルすべて。各ファイルの対象 HEAD は `1aeb26faece1`（Update の履歴も同じ SHA）。
- 対象: `usaturn/resoloop` PR #9、既存 head ブランチ `fix/list-shrink-recreate-split`、現行コミット `1aeb26faece1e22c1813bcd41893f1b46a1bc538`。確認時に PR は OPEN、remote head とコミットが一致。
- 目的: list 短縮による recreate が失敗した場合、旧 Component や生きた参照を失わず、state と復旧案内が実際の状態を表すようにする。`resoloop test` は apply 前に存在する Component を正しく観測する。未確認の実機挙動を保証済みとは扱わない。
- 範囲: レビューで挙がった指摘だけ。今回の設計の実装は**未承認**。他の worktree の未コミット変更は検証根拠にも実装範囲にも含めない。Spec はこのリポジトリに保存し、実装承認後のコード変更・テスト・push は既存 PR の head に限る。

## 選別結果

全18指摘: **解消済み 0 / 対応する 10 / 判断保留 0 / 対応しない 8**。ID はファイル名＋レビュー内の見出しで特定する。重複指摘も別件として数え、実装時は統合する。「対応する」の根拠区分は (a) 現行 HEAD の誤動作再現、(b) 現行 HEAD の記述誤り、(c) 削除された回帰ガード、(d) ユーザ指定。

| ID | 区分 | 根拠・判断 |
| --- | --- | --- |
| `SWE-2-Max/L-1` | 対応しない | `null` 宣言でも `APPLY_LIST_SHRINK_REFERENCED` で変更前停止することは隔離テストで確認。ただし `WorldService.cs:1574-1617` の停止は書き込み前の参照安全判定で、`null` や prune の参照消去を成功とみなすのは安全側停止を緩める仕様判断。検証前の参照消去を保証する設計ではない。 |
| `SWE-2-Max/L-2` | **対応する (a)** | `WorldService.cs:1101` は `{ Length: 0 }` だけを拒否する。隔離テストで state の `renderer.id = null` から list 短縮を apply すると `STABLE_COMPONENT_AMBIGUOUS` では止まらず、元の Component が置き換わった。 |
| `SWE-2-Max/L-3` | **対応する (a)** | `WorldService.cs:2298-2319` が遅延 list 書き込み後の長さを確認しない。`gpt-6-sol/H-1` と同じ再現経路。 |
| `SWE-2-Max/I-1` | **対応する (b)** | `docs/DECLARATIVE.md:196` は「このapplyで作った」置換だけの undo と書くが、`WorldService.cs:2333-2342` は以前の apply で作った再開中の失敗した置換も削除する。参照安全修正後も、削除される場合の説明は正確にする。 |
| `claude-opus-5-5/L-1` | **対応する (a)** | 隔離テストで、参照元のない再開中の3要素置換を2要素宣言に変更すると、1回目は `APPLY_LIST_SHRINK_NOT_CONVERGED` と「同じコマンドは繰り返し失敗」と案内し、同じコマンドの2回目は成功した。`WorldService.cs:1467-1471,2333-2363`。 |
| `claude-opus-5-5/I-1` | **対応する (a)** | 同じ隔離テストで NOT_CONVERGED に「宣言変更後だけ再実行」と汎用の「同じ apply を再実行」の両方が付く。`WorldService.cs:655-675,2362-2365`。 |
| `qwen3.8-max/L-1` | 対応しない | `--yes` 要否は relocate と共通の既存設計。`external/resoloop/AGENTS.md` は CLI の明示的 delete/remove の確認を必須とし、apply 内の recreate に追加 opt-in を要求していない。`docs/DECLARATIVE.md:193` も未宣言 member の初期化を記述済み。 |
| `qwen3.8-max/L-2` | 対応しない | `WorldService.cs:1178-1188` と既存テスト `AShorterListInsideASyncObjectIsNotRecreated` は入れ子 list 非対象を明示。文書は `fields` 直下の list member を説明し、入れ子にも対応すると断定していない。追加警告・文書は範囲拡張。 |
| `qwen3.8-max/L-3` | **対応する (a)** | 隔離テストで、旧 Component の削除時中断→管理 Source が参照する置換を再開→snapshot 後に list が延長されると、`APPLY_LIST_SHRINK_NOT_CONVERGED` で置換 ID が消え、Source は削除済み ID を参照した。`WorldService.cs:2333-2343`。 |
| `qwen3.8-max/I-1` | 対応しない | 実機確認と CI 状態は作業・運用上の未完了事項であり、現行 HEAD の再現済みバグ／誤記ではない。実機検証を済ませたと偽って PR 本文を更新しない。 |
| `claude-sonnet-5-5/L-1` | 対応しない | `WorldService.cs:574-585` の削除ごとの checkpoint・index 再読込は中断時の保存済み index を維持する実装。実測の性能障害は無く、バッチ化は回復特性を変える。 |
| `claude-sonnet-5-5/I-1` | 対応しない | snapshot 外の参照の限界と `--prune` 不要な recreate は `docs/DECLARATIVE.md:193-195` に記載済み。既存設計／安全方針の変更は今回の修正ではない。 |
| `commandcode-deepseek-deepseek-v4.1-flash/L-1` | 対応しない | `supersededId` は中断中のみ保存され、旧版でその state を再開する非互換性は PR 本文が明記。schema 3 への変更は全 state の旧版利用を止める仕様選択であり、今回の再現済み不具合ではない。 |
| `commandcode-deepseek-deepseek-v4.1-flash/L-2` | **対応する (a)** | `WorldService.cs:2292-2293,2540` は旧 Component 消失時に検証を飛ばす。隔離テストで旧 Component 削除応答喪失後、snapshot 後に置換 list を延長すると `APPLY_REFERENCE_NOT_RETAINED`、宣言より長い置換だけが残り `supersededId` は消えた。元指摘の「成功」までは再現しなかったが、読み戻さないまま state を完了にする問題は再現した。 |
| `commandcode-deepseek-deepseek-v4.1-flash/I-1` | 対応しない | `componentsAdded` / `componentsDeleted` は実行操作の件数であって純増減とは定義されていない。作成と削除を両方数える `WorldService.cs:489,2338-2339` は実際の操作を示す。 |
| `gpt-6-sol/H-1` | **対応する (a)** | 隔離テストで、2つの管理 Component が相互に参照する list を2→1に短縮し fake runtime に2要素への補充を設定。`APPLY_REFERENCE_NOT_RETAINED` で終了し、旧 ID は world に残らず state は新 ID を指した。`WorldService.cs:502-554,2298-2319`。 |
| `xai-grok-4.7/M-1` | **対応する (a)** | 隔離テストで list 短縮を宣言した既存 Component を apply 前に `TestAsync` の存在 assertion で調べると `Component existence differed.` で不合格、書き込み0回。`WorldService.cs:704-708` が `Superseded` を除外。 |
| `xai-grok-4.7/L-1` | **対応する (a)** | `claude-opus-5-5/I-1` と同じ NOT_CONVERGED の矛盾を隔離テストで確認。 |

レビュー冒頭の active な見出しのみを指摘として数えた。レビュー中の `Unverified candidates`、追加テストの提案、Merge recommendation は新しい指摘として数えない。方針論点として、`--yes` を apply の recreate に要求するか、schema を3に上げるか、入れ子 list の収束まで対象を広げるかは、この Spec では変更しない。

## 設計の選択

- **採用: 旧 Component を保持したまま、参照を移す前に解決可能な置換間 list も最終値で書いて読み戻す。** 置換 ID がすべて揃った段階で相互参照を解決し、宣言 list の長さを確認する。失敗時は参照を切らない置換だけを取り消し、安全に消せない再開中の置換は `inProgress` として保持する。旧 Component が既に無い場合は取り消し先が無いことを明示して停止し、成功扱い／誤った巻き戻しをしない。
- 不採用: 現行どおり fields フェーズと事後の `APPLY_REFERENCE_NOT_RETAINED` に任せる方法。旧 Component を失ってから失敗する。
- 不採用: `recreate` の全面禁止や全 apply への `--yes` 追加。レビュー対象以外の既存仕様を広く変更する。

### 実装境界と失敗時の保証

1. `src/RLoop.Core/WorldService.cs` の置換フローを、置換 ID の作成、保留していた参照 list の書き込み・読み戻し、旧 Component 参照の張り替え、旧 Component の削除、の順に整理する。検証を移動するときは既存の checkpoint・asset evidence・`initialFields`・再開時の fields も保持する。宣言された参照 list の検証前には旧 Component を削除しない。相互参照先が未検証でも ID を使用できる局面と、外部の管理参照を張り替えてよい局面を分ける。失敗時には相互参照する置換全体の undo 範囲を安全に決め、残す置換へ削除済み ID を向けない。
2. 置換の失敗時、再開中の置換を参照する Component が snapshot にあればその置換は削除しない。状態に `supersededId` を維持し、`inProgress` および復旧手順を実際に残る参照に合わせる。参照が無い再開分は安全に取り消せる。旧 Component が既に無い再開分も必要な list を検証し、undo 先が無い場合には置換を保持したまま収束失敗を明示する。snapshot 外参照を保証したとは説明しない。
3. state の保存 ID が null／欠損／空文字列なら、位置だけで照合した Component を recreate せず `STABLE_COMPONENT_AMBIGUOUS` で変更前に停止する。`TestAsync` だけは recreate 予定の `Superseded` を「今存在する Component」として解決する。apply の未検証置換を通常参照に使う安全規則は変えない。
4. `APPLY_LIST_SHRINK_NOT_CONVERGED` の再開＋宣言再短縮は runtime の再補充と区別して案内し、取り消し後に同じ宣言で作り直せる場合はそう記述する。汎用 catch は専用 `recovery` を上書きせず、矛盾する suggestions を足さない。`docs/DECLARATIVE.md` は前 apply で作った再開置換も undo され得ることと、削除不能な置換の復旧を正確に記述する。その他の README・スキルは変更した CLI の挙動に関係する箇所だけ更新する。

### 対応する項目別の検証方法

| ID | 回帰テスト・検証 |
| --- | --- |
| `SWE-2-Max/L-2` | `id:null` と `id` 欠損の state から list 短縮を実行し、`STABLE_COMPONENT_AMBIGUOUS`、書き込み0回、旧 ID 維持。既存 `AKeyWithoutASavedIdNeverRecreatesAComponentMatchedByPosition` と併せて実行。 |
| `SWE-2-Max/L-3`, `gpt-6-sol/H-1` | 相互参照する置換 list を fake runtime が補充するテストで、旧 ID が検証失敗時には残り、state も旧 ID を維持。補充なしでは1回で収束する既存 `RecreatedComponentsThatReferenceEachOtherConvergeInOneApply` も通す。 |
| `SWE-2-Max/I-1` | `docs/DECLARATIVE.md` の undo 記述と再開失敗時の実装・テストを突き合わせ、この apply で新規作成した置換だけに限定しない。 |
| `claude-opus-5-5/L-1` | 参照元の無い中断置換を3要素から2要素に宣言変更し、1回目は理由に合う案内、2回目の同じ apply は収束。plan reason も中断先が新宣言より長い場合を誤って「単純な削除」としない。 |
| `claude-opus-5-5/I-1`, `xai-grok-4.7/L-1` | fake refill で NOT_CONVERGED を発生させ、`recovery` と suggestions に無変更再実行の誤案内が無く、原因変更後の復旧が一貫する。 |
| `qwen3.8-max/L-3` | 旧 Component 削除失敗→参照張り替え済み→snapshot 後に list 延長→再開失敗を作り、Source の Target が生きた置換を指し続け、`inProgress` と `supersededId` が保たれる。 |
| `commandcode-deepseek-deepseek-v4.1-flash/L-2` | 旧 Component 削除応答喪失後に list が長くなる経路、旧・新 Component が消失した経路を検査。読み戻しで収束失敗を検出し、存在しない旧 ID に戻さず、復旧可能な state を残す。 |
| `xai-grok-4.7/M-1` | apply 前の list 短縮文書を `TestAsync` に渡し、`$component:key` 存在判定・他 member の `$ref:key`・対象 key の probe が旧 ID を参照して正常に走り、書き込み0回。既存の `TestSupportsComponentExistenceAndFilteredChildCount` も通す。 |

実装承認後は上の絞り込みテストと変更した `RLoop.Tests` に関連する `dotnet test` をまず通し、README・スキルを変えた場合はその関連検証を行う。fork のコード変更なので関連する `dotnet test` が反映条件。全 solution／実機テストの成功を今回の隔離 fake 再現から推定しない。対象の既存 PR が open か改めて確認してから、その head へ commit / push し、review-fix-planning の PR コメントを投稿する。現段階ではどれも行わない。

## 再現と制約

確認はコミット済み HEAD の blob（`git show 1aeb26faece1:<path>`）と、HEAD を照合した `/tmp/review-fix-planning.XXXXXX/worktree` でのみ行った。隔離テストは `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ReviewProbe'` で実行。各検証後、専用 worktree を `git worktree remove --force` で外して親の一時ディレクトリも削除済み。fake の refill と snapshot 後の外部変更で経路を検証したが、実機 Resonite で同じ refill が起きることは確認していない。通常 apply の安全境界は、読み取った snapshot 内に限られる。

本書を承認するまでは実装しない。設計に修正が必要なら、この Spec を直してから実装計画とコードに進む。
