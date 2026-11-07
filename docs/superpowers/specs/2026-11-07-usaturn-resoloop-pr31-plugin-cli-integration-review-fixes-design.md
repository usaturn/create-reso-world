# usaturn/resoloop PR #31 プラグイン CLI 統合 レビュー修正 設計

## 管理・実行許可

- 状態: `completed`（サイクル 1 の結論 1。push・状況コメントの結果は PR の状況コメントに書く）
- 対象: usaturn/resoloop#31（`feat/create-reso-world-issue-298-cli-integration` → `feat/plugin-v2`）、create-reso-world#298
- 実行許可: 利用者の指示 `/issue-to-pr #298 --base feat/plugin-v2 --merge` による PR 修正ループ（pr-review-fix-loop）の完遂（review-fix-planning の既定）。内容の承認ではない
- 元の設計: `docs/superpowers/specs/2026-11-07-create-reso-world-issue298-plugin-cli-integration-design.md`、Plan: `docs/superpowers/plans/2026-11-07-create-reso-world-issue298-plugin-cli-integration.md`
- サイクル: 1。planner: claude-opus-5-5（claude-code）。ループの run は `claude-sonnet-5-5` を司令塔のモデルとして開始したが、run の途中で利用者がモデルを Opus 5.5 に切り替えたため、この計画以降の判断は claude-opus-5-5 が行っている

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `c18f17822dc7` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `c18f17822dc7` | はい | Approve |
| （なし） | pi_commandcode_deepseek4-flash_max | pi | ― | 失敗（runner の timed_out、終了コード -15。loop が rejected とした。レビューファイルは無く、計画の入力にしていない） | ― |

確認済みの一覧: `reviews/usaturn/resoloop/#31-feat-create-reso-world-issue-298-cli-integration/verified/c18f17822dc7.json`（V-1 confirmed）。

## 全指摘と振り分け

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `gpt-6.1-sol#M-1@c18f17822dc7` | `--json` などのオプションをコマンド名の前に書くと、未知名が ResoniteLink の発見・接続へ進む | 対応する | 下記 |

SWE-2 Max の指摘は 0 件。修正後の自己レビューの指摘（下の「自己レビュー」）を含めて、解消済み 0 / 対応する 1 / 対応しない 1。

### M-1 を対応する理由

- 致命的である理由（発生条件）: エージェント向けに文書化された `--json`・`--brief` を、打ち間違えた名前やプラグインのコマンド名の前に置く（通常の使い方）。CLI は頼んでいない ResoniteLink への接続を行い、Resonite が起動していなければ `UNKNOWN_COMMAND` ではなく `CONNECTION_FAILED`（終了コード 4）を返す。利用者・エージェントは構文の誤りではなく接続の問題として調べることになり、ツールのとおりに使うと誤った結果になる。D-4 の「本体は外部コマンドのためだけに接続しない」「未登録名も接続前に `UNKNOWN_COMMAND`」にも反する
- (a) 再現した誤動作: 確認済みの一覧 V-1。`--json`・`--brief`・`--verbose`・`--url URL` の前置で接続 4 回・終了コード 4。前置なし・`--project .` 前置は接続 0 回・終了コード 2
- PR 起因: 既存（base には分離そのものが無い）だが、#98 Spec 3.1（68 行目）がこの拒否を #298 に引き渡しており、この PR の受け入れ条件の実装漏れである

## 要件対応

| 要件（出所） | 今回の扱い | 統合担当と確かめ方 |
| --- | --- | --- |
| 未登録名も接続前に `UNKNOWN_COMMAND`（親 Spec D-4、#98 Spec 3.1、Issue #298 受け入れ条件） | 既存パーサへ戻った経路にも拒否を足す | 司令塔。統合テストの見直しと、実 CLI での前置オプションの再現 |
| ホストが解釈するのはコマンド前の `--project` だけ（D-4） | 変えない。`--json PLUGIN_COMMAND` はプラグイン呼び出しの構文ではないので実行しない | 同上 |
| 組み込みコマンドの構文・出力を維持（D-4、元の Spec 決定 1） | 組み込み名（`BuiltinCommandCatalog`）の経路は変えない | `--json schema list` の正例と全体テスト |
| `help`・`--help`・`--version` の既存の早期終了 | 拒否はその後に置く | 全体テストと手動実行 |

## 修正方針

`Main` の既存パーサの経路で、help/version の早期終了の後、ResoniteLink 設定の解決より前に、先頭の位置引数が `BuiltinCommandCatalog.IsBuiltin` でなければ `UNKNOWN_COMMAND`（終了コード 2）で止める。メッセージの提案には、プラグインのコマンドではコマンド名の前に `--project DIR` だけを書けることを示す。`PluginCommandDispatch`・`BuiltinCommandCatalog` など先行の API は変えない（所有範囲は `Program.cs` とテスト）。

テスト: 既存の `UnknownCommandStopsBeforeConnecting` に、`--json` を前置した未知名（接続 0 回・`UNKNOWN_COMMAND`・終了コード 2）と、正例の `--json schema list`（接続 0 回・終了コード 0）を加える。前置なしの経路は別のガード（`PluginCommandDispatch`）なので同じテストに残す。各グローバルオプションの総当たりはしない（`AGENTS.md`「テストの採用基準」の D）。

## 守る条件と影響経路

守る条件: 先頭の位置引数が組み込み名でない呼び出しは、ResoniteLink の発見・接続より前に `UNKNOWN_COMMAND` で止まる。破れた前提: `PluginCommandDispatch.Parse` が先頭のオプションで null を返した後、既存パーサの経路が未知名を最後の `RunResonite` まで運ぶ（接続の後でしか名前を判定しない）。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 未知名は接続前に止まる | `Main` → `Parse` 非 null → `PluginCommandDispatch.RunAsync`（前置なし・`--project` 前置） | 既に満たす（PR の分離） | 接続 0 回、終了コード 2 | `UnknownCommandStopsBeforeConnecting` の前置なしの例、repro.py | c18f1782・edf710c とも接続 0 回・終了コード 2（verified V-1、repro2.py） |
| 同上 | `Main` → `Parse` null（`--json`・`--brief`・`--verbose`・`--url X`・`--report X` を前置）→ 既存パーサ → 未知名 | 修正する | 接続 0 回、終了コード 2、`UNKNOWN_COMMAND` | 見直したテストの `--json` 前置の例、repro.py の全前置 | edf710c: テスト成功。repro2.py で 5 種の前置とも接続 0 回・終了コード 2・UNKNOWN_COMMAND（修正前の c18f1782 は接続 4 回・終了コード 4） |
| 同上 | `--project X --json NAME`（`Parse` は `--json` で null） | 修正する（上と同じ拒否で閉じる） | 接続 0 回、終了コード 2 | repro.py に追加 | edf710c: repro2.py で接続 0 回・終了コード 2・UNKNOWN_COMMAND |
| 組み込みの構文・出力を変えない | 組み込み名（大小文字を区別しない catalog）の全経路 | 既に満たす（拒否は catalog に無い名前だけ） | `--json schema list` が接続 0 回・終了コード 0、全体テスト | 見直したテストの正例、`dotnet test` | edf710c: テストの正例が成功、全体テスト 592＋22 件が成功。fix-check で catalog が Main と RunResonite の分岐するすべての名前を含むことを確認 |
| 早期終了を変えない | `--version`・`version`・`--help`・`help`・`-h`・位置引数なし | 既に満たす（拒否はその後に置く） | 出力と終了コード 0 | 手動実行 | edf710c: repro2.py で `--json --version`・`--json help`・`-h` が接続 0 回・終了コード 0。自己レビューで `--json version`・引数なしも終了コード 0 |
| 対象外 | 組み込み名の大文字の別表記（`Bundle` など）が既存の `==` 比較で接続の経路へ進むこと | 対象外（base からの組み込みの挙動で、未登録名ではない） | ― | ― | ― |

## 検証

修正後の HEAD で: `dotnet build ResoLoop.slnx`、`dotnet test ResoLoop.slnx --no-build`、repro.py（前置オプション 4 種・`--project` との組み合わせ・前置なし・正例）、help/version の手動実行。失敗時の扱いの修正なので、拒否のガードを外した対照（隔離 worktree）で、見直したテストの `--json` 前置の例が失敗することを確かめる。

## 結論・結果

- 結論: 1（修正して push）。対応する 1 件（M-1）を直した
- 修正の担当: `run_roles.py --phase implement` の `claude-code_opus_default`（観測したモデル claude-opus-5-5、session `369b4bd3-8f8b-41de-9f6e-5b52e59dd2d0`、397 秒）。担当の commit `4750200` を停止の確認（`stop_confirmed: true`）と差分の確認（`Program.cs` +10、テスト +11/-1 の 2 ファイルだけ）の後に cherry-pick し、`edf710c97767699fe4cd4b49e7a3c282435d5205` にした
- 実行した検証（edf710c、司令塔が実行）:
  - `dotnet build ResoLoop.slnx`: 終了コード 0（警告 0・エラー 0）
  - `dotnet test ResoLoop.slnx --no-build`: 終了コード 0（RLoop.Tests 592 件・IntegrationTests 22 件が成功）
  - 実 CLI の再現（接続を数える待ち受け）: 上の経路表のとおり
  - 失敗時の検証: 比べた状態は、終了コード・エラーコード・待ち受けへの接続数（3 回の実行の合計）。負例の異常は未知名の 1 つだけで、ほかは正常（同じ待ち受け、同じプロジェクト）。ガードの 1 か所（`IsBuiltin` の検査）を外した隔離 worktree の対照で、`UnknownCommandStopsBeforeConnecting` が失敗した（Expected 2 / Actual 4。負例 1 件が失敗、ほかの 2 件は成功）
  - push 前の検査（`scan-before-push.sh`、base origin/feat/plugin-v2）: 検出なし
- 自己レビュー: `run_roles.py --phase self-review` の 1 回。self-review・fix-check とも割り当ては `self` で、司令塔（claude-opus-5-5）のサブエージェント 2 つが並行して実行した
  - self-review（PR 全体、edf710c）: `claude-opus-5-5-commit-edf710c97767699fe4cd4b49e7a3c282435d5205.md`、Approve。M-1 の解消を実 CLI で確認。指摘は L-1（Low）だけ
  - fix-check: `verified/edf710c97767.fix-check.json`、指摘 0 件。claims 11 件 holds、files 2 件 passed、文書候補 20 件（consistent 6・unrelated 14）
  - 自己レビューの後に修正していない（L-1 は対応しない）。2 回目の自己レビューはしていない

### 自己レビューの指摘の判定

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `claude-opus-5-5-commit-edf710c97767699fe4cd4b49e7a3c282435d5205#L-1@edf710c97767` | doctor の統合テストの `"ready":false` は接続の失敗だけで成り立ち、プラグインの必須チェックが ready に数えられることを確かめていない | 対応しない | テストの検出力の不足（保守性）で、利用者の挙動は変わらない。現在の実装は ready を全チェックの required から計算し、プラグインのチェックもその中に入る（Program.cs の `checks.AddRange` が `DoctorReport` の前）。doctor の結線そのものは同じテストの `plugin:integ-plugin:missing` の検査が守り、外す変異で落ちることを PR の作成前に確認した。致命的ではない |

## 記録の参照

- 確認済みの一覧: `reviews/usaturn/resoloop/#31-feat-create-reso-world-issue-298-cli-integration/verified/c18f17822dc7.json`
- 修正の確認: 同 `verified/edf710c97767.fix-check.json`
- 工程の記録: 同 `verified/c18f17822dc7.planning.json`（自己レビューの予約 `pre_push_review` 1 件）
