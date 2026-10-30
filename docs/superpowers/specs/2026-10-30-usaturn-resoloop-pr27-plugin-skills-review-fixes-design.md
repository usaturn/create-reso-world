# usaturn/resoloop PR #27 プラグインのスキル配布のレビュー修正

## 管理・許可

- 状態: **completed**（サイクル 2 の結論 2。修正不要としてマージに進む）
- 対象 PR: https://github.com/usaturn/resoloop/pull/27 （base `feat/plugin-v2`、head ブランチ `feat/create-reso-world-issue-99-plugin-skills`）。Issue: https://github.com/usaturn/create-reso-world/issues/99
- 元の設計: [Issue #99 の Spec](2026-10-30-create-reso-world-issue99-plugin-skills-design.md)、[Plan](../plans/2026-10-30-create-reso-world-issue99-plugin-skills.md)
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/99 --base feat/plugin-v2 --assign inspect=pi-gpt,claude-opus,devin-swe,pi-deepseek --merge`。issue-to-pr の `--merge` により PR 修正ループ（pr-review-fix-loop）で review-fix-planning の完遂を行う（致命的な指摘だけを直す、三択の結論、修正後の自己レビューは 1 回）。マージはループの `finalize.py` だけが行う
- ループ: run `c0d478fe1b9c453ab309eacd383851e2`（`/workspaces/reso-world/reviews/usaturn/resoloop/#27-feat-create-reso-world-issue-99-plugin-skills/loop/c0d478fe1b9c453ab309eacd383851e2`）
- planner: Claude Code `claude-opus-5-5`（司令塔）。修正の担当 `claude-opus`（雛形 `.devcontainer/agent-runner.toml` の既定）、self-review・fix-check は `self`

## サイクル 1（reviewed_head `371a34e9f76bb8e1a276fb7a074ed1be37153086`）

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | 再実行 | Merge recommendation | 指摘 |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol` | gpt-6.1-sol | pi | `371a34e9f76b` | はい | Approve | M-1（Medium） |
| `claude-opus-5-5` | claude-opus-5-5 | claude-code | `371a34e9f76b` | はい | Approve | L-1（Low） |
| `SWE-2-Max` | SWE-2 Max | devin | `371a34e9f76b` | はい | Approve | なし |
| `deepseek-deepseek-v4.1-flash` | deepseek/deepseek-v4.1-flash | pi | `371a34e9f76b` | はい | Approve | なし |

前のサイクルの判断: なし（PR の判断の記録は空）。

### 全指摘と分類

| 判断 ID | 出典 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `gpt-6.1-sol#M-1@371a34e9f76b` | gpt-6.1-sol | 対応する | 致命的: installer が受け付ける制限内のパッケージ（日本語の長いパスの 8500 件、導入記録 7,982,027 バイト）や、取り外したプラグインの項目が積み重なった記録で、配布記録が 8 MiB を超える。update は成功を返して読めない記録を保存し、以後そのプロジェクトのプラグイン対応の sync（check・update・init）が `PLUGIN_SKILL_RECORD_INVALID` で止まり続ける（主要な処理の停止）。手で記録を消すと所有・編集保護の記録を失う。(a) レビュアーが再現し、現行 HEAD の `WriteRecord` に大きさの検査が無いことを確認 |
| `claude-opus-5-5#L-1@371a34e9f76b` | claude-opus-5-5 | 対応しない | 致命的でない: Linux で綴りの大小だけを変えた改名でも、古い綴りのファイルは上書きも削除もされない。記録を失った後、同じパスを別の内容で配ろうとすると（大小文字を無視した照合で新しい綴りの記録に当たるため）`modified-conflict` で止まる（安全側。サイクル 2 の review-verify の実測。サイクル 1 の判断の記録の理由に書いた `untracked-conflict` は誤りで、止まって上書きしない結論は変わらない）。損害は `Retained` の報告から漏れることだけ。見直す条件: 大小文字を無視した照合で利用者の内容を上書きする経路が見つかったとき、または `Retained` を掃除・削除に使う機能を足すとき |

解消済み: なし。

### 要件対応（convergence 1）

| 元の Spec の条件 | 今回の修正 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 書けなかったファイルを配布済みと記録しない／失敗を成功と返さない（Spec 5 章） | 成功を返す前に、書き込む記録が次回読めることを確かめる | 上限を超える記録になる update は、何も書かずに例外で止まる | 新しい S テスト |
| 全競合を確かめる前に何も書かない（同梱を含む） | 記録の大きさの検査も計画（書き込み前）に置く | 同梱のファイルも書かれない | 同じテスト |
| 記録は消さない（D-5） | 項目を消して上限に収める案は採らない | 保持した項目は残る | 同じテストの正しく通る例 |
| プラグイン無しの既存の生成物を変えない | 変更なし（記録の検査はプラグインが参加するときだけ） | 既存のテストが通る | `ProjectInitializerTests`・`AgentEfficiencyTests` |

共有条件: 計画（`PluginSkillPlan` のコンストラクタ）が sync の check・update と init の唯一の入口なので、検査を計画の 1 か所に置く。統合担当は司令塔で、sync と init が同じ計画を通ることをコードで確かめる。

### 守る条件と影響経路（M-1）

守る条件: 書き込む配布記録は、次回の読み込みの上限（8 MiB）を必ず満たす。満たさないなら、同梱を含めて何も書かずに、成功を返さずに止まる。記録の項目が変わらないなら記録を書き直さない。

破れた前提: 書き込み側（`WriteRecord`）は大きさを確かめず、読み込み側（`ReadRecord`）だけが 8 MiB で拒否する。配布記録は導入記録より 1 項目あたり大きい（所有者とインデント）ので、導入記録が上限内でも配布記録は上限を超え得る。さらに、記録は消さないので取り外したプラグインの項目が積み重なる。

| 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- |
| sync update: 計画→同梱の書き込み→`Apply`→`WriteRecord` | 修正する | 計画の段階で `PLUGIN_SKILL_RECORD_TOO_LARGE`、スキル・同梱・記録のバイト列が変わらない | 新しい S テスト | `4d7016a`: `OversizedRecordsAreRefusedBeforeAnyWrite` 成功（記録 62,000 項目・compact で 8 MiB 未満、update は `PLUGIN_SKILL_RECORD_TOO_LARGE`、alpha と resonite-flux の SKILL.md は作られず、記録のバイト列は不変）。ガードを外した対照（隔離 worktree で `EnsureReadable` を無効化）ではこのテストが失敗（1 件） |
| init: `Initialize(target, version, reservations)`→`Apply(init: true)`→`WriteRecord` | 修正する（同じ計画） | 同上 | コードで、init が同じ計画を通ることを確認 | `4d7016a`: `ProjectInitializer.cs:26` の新しい `Initialize` は `PluginSkillManager.Open` を通り、計画のコンストラクタで検査される（コードで確認）。init では `update-available` が conflict なので、`Apply(init: true)` が書く記録は計画で検査した集合の部分集合 |
| sync check | 修正する（同じ計画） | check でも同じ例外 | コードで確認 | `4d7016a`: `BundledSkillManager.cs:37` の新しい `Sync` は check でも `Open` を通る（コードで確認） |
| 項目が変わらない update（読める記録の書式だけが違う） | 修正する | 記録を書き直さない | 新しい S テストの正しく通る例 | `4d7016a`: 同じテストの後半（プラグインを外した後の update が成功し、compact の記録のバイト列が変わらない）。review-verify が報告した「配るファイル 0 件の update・init での書き直しによる上限超過」の経路もこれで塞がる |
| `ReadRecord` の上限 | 既に満たす | 上限を超える記録は `PLUGIN_SKILL_RECORD_INVALID` | 現行 HEAD のコード | 現行 HEAD で確認済み |
| F の `PluginInstallRecord.Write` | 対象外 | F の所有ファイルで、書く前に大きさを確かめている | — | — |

### 修正方針

- 計画の段階で、適用後の記録（既存の項目に、`missing`・`update-available`・`record-update-required` の配布先の `{plugin, packageHash}` を重ねたもの）を組み立て、項目が既存から変わるときだけ、`WriteRecord` と同じ関数でシリアライズして大きさを確かめる。超えたら新しいエラーコード `PLUGIN_SKILL_RECORD_TOO_LARGE`（`ValidationFailed`、context に `path`・`bytes`・`limit`）で止まる
- `Apply` は、記録の項目が実際に変わったときだけ記録を書く（バイト列の比較で書き直しを決めない）
- `WriteRecord` でも書く直前に同じ検査をする（二重の守り）。記録の書式は変えない

比べた案:

| 案 | 判定 | 理由 |
| --- | --- | --- |
| 計画の段階で適用後の記録を検査し、項目が変わらなければ書かない | 採用 | 書き込みの前に止まるので、同梱・スキル・記録のどれも変わらない。check でも問題が分かる |
| `WriteRecord` での検査だけ | 不採用 | ファイルを書いた後に止まる。次回も同じ大きさで止まり続け、配ったファイルが記録されないまま残る |
| 読み込みの上限を上げる・書式を詰める | 不採用 | 上限の問題を先送りするだけで、保証にならない |
| 保持した項目を消して上限に収める | 不採用 | 記録を消さない仕様（D-5）に反する |

新しいエラーコードは I #298 へ引き渡す API に加わる（元の Spec 3 章の一覧に追記する）。

### テスト

`AGENTS.md` の「テストの採用基準」の S の代表 1 件（成功と報告して次回読めない記録を保存しない）。既存の記録を、取り外したプラグインの項目を多数持つ有効でインデントの無い記録（8 MiB 未満、インデント付きに直すと 8 MiB 超）にしておき、1 ファイルを配る update が何も書かずに止まること、プラグインを外した後の update は成功し、項目が変わらないので記録を書き直さないことを確かめる。init・check 経由の同じ守りは足さない（D）。

### 実行と結果

結論: **1 修正して push**（`4d7016ad8cf42402b7a0e0cbb1f944cc31819172`）。

修正の実装（`run_roles.py --phase implement`、担当 `claude-opus`、runner の run `8c1404c186254dd7bdf15a824aefd009`、request `410a0e4ca12144d5a835062cadd6ab97`、モデル `claude-opus-5-5`、262 秒、停止を確認）: commit `e0f3a0c` を作り、司令塔が差分を確かめてから修正用の worktree へ cherry-pick した（`4d7016a`）。担当の報告: RED（修正前の `371a34e` で新しいテストが `No exception was thrown` で失敗）→ GREEN → 関連 29 件成功。

司令塔の検証（`4d7016a`、修正用の worktree、作業ツリーは clean）:

- `dotnet build ResoLoop.slnx --nologo` → 警告 0・エラー 0（終了コード 0）
- `dotnet test ResoLoop.slnx --nologo --no-build` → unit 579 件（既存 578＋新設 1）・offline integration 22 件、失敗/skip 0（終了コード 0）
- 失敗時の検証の対照: 隔離 worktree で `EnsureReadable` の上限の判定を外すと、`PluginSkillSyncTests` のうち `OversizedRecordsAreRefusedBeforeAnyWrite` だけが失敗（1 件）。比べた状態は、スキルのファイル・同梱のファイル（`resonite-flux/SKILL.md`）・記録のバイト列
- Gitleaks（push の前の検査だけ）: `dd0b40f..4d7016a` の 5 commits で検出なし

確認済みの一覧（review-verify mode cycle、サブエージェント、535 秒）: `verified/371a34e9f76b.json`。M-1・L-1 とも confirmed。M-1 は、上限内の詰めた記録が、配るファイル 0 件の update や init でもインデント付きに書き直されて上限を超える経路まで範囲が広い（今回の「項目が変わらなければ書かない」で塞いだ）。

### 修正後の自己レビュー（1 回）

`run_roles.py --phase self-review` を 1 回だけ呼び、self-review と fix-check の 2 役割を司令塔（`self`）がサブエージェントで実行した。自己レビュー後の修正は無い（再レビューもしていない）。

| 役割 | 担当 | 結果 | 成果 |
| --- | --- | --- | --- |
| self-review（PR 全体の再レビュー、`4d7016a`） | self（`claude-opus-5-5`、613 秒） | Approve。Low 1 件 | `claude-opus-5-5-commit-4d7016ad8cf42402b7a0e0cbb1f944cc31819172.md` |
| fix-check（観点 1 反証・観点 3 検出力） | self（`claude-opus-5-5`、619 秒） | 修正は条件を満たす（主張 12 件 holds、変更ファイル 2 件 passed、新しい問題 0 件） | `verified/4d7016ad8cf4.fix-check.json`・`.md`・`.statement-candidates.json` |

- 観点 1: update（9,990 ファイル）・init・check・update-available・配るファイル 0 件・上限内の正常側を、修正前と修正後で比べた。修正後はどの入口でも上限を超えると `PLUGIN_SKILL_RECORD_TOO_LARGE` で止まり、基本ファイル・同梱・スキル・記録のどれも書かない。読み書きの上限の境界は一致する
- 観点 3: 計画段階の検査を外す変異、項目が変わらなくても書き直す変異の両方で、新しいテストが失敗した

自己レビューの指摘の判定:

| 判断 ID | 区分 | 根拠 |
| --- | --- | --- |
| `claude-opus-5-5-commit-4d7016ad8cf42402b7a0e0cbb1f944cc31819172#L-1@4d7016ad8cf4` | 対応しない | `claude-opus-5-5#L-1@371a34e9f76b` と同じ原因（記録のキーが大小文字を区別しない）の別の帰結。Linux で大小だけの改名の後、後の版が旧い綴りに戻して内容を変えると、未編集でも `modified-conflict` で sync 全体が止まる。止まるのはエラーとして見え、示されたファイルを片付ければ回復でき、ファイルの上書き・消失は無い。致命的でない。既知の制限として PR の説明に書く |

未確認の事項: Windows での実行（push 後の公開 CI で確かめる）、記録がちょうど 8,388,608 バイトの境界の実行（コードで確認）、計画から書き込みまでの間に他のプロセスが記録を変える競合（協調するプロセスは lease で BUSY。非協調は元の Spec の対象外）。

### PR の説明の既知の制限に足すもの

- Linux（大小文字を区別するファイルシステム）で、プラグインの版の間にファイル名・ディレクトリ名の大小だけを変えると、旧い綴りの配布済みファイルの記録が消え、`Retained` にも出ない。ファイル自体は上書き・削除されない。後の版が旧い綴りに戻して内容を変えると、未編集でも `modified-conflict` で止まる。回避: 旧い綴りのファイルを片付けて（必要なら退避して）から `skills sync --update` を実行する

## サイクル 2（reviewed_head `4d7016ad8cf42402b7a0e0cbb1f944cc31819172`）

### レビュアーの構成

ループの `cycle-begin` は `reuse`（現在の HEAD の修正後の自己レビューがあるため、レビュアーを起動しない）。

| レビューファイル | モデル | ランタイム | レビュー HEAD | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5-commit-4d7016ad8cf42402b7a0e0cbb1f944cc31819172` | claude-opus-5-5 | claude-code | `4d7016ad8cf4` | はい | Approve |
| `gpt-6.1-sol`・`claude-opus-5-5`・`SWE-2-Max`・`deepseek-deepseek-v4.1-flash` | （サイクル 1 の表） | — | `371a34e9f76b` | いいえ（古いレビュアー。指摘は判断済み） | Approve |

前のサイクルの判断: 3 件（fix 1・skip 2）。確認済みの一覧（review-verify、636 秒）: `verified/4d7016ad8cf4.json`（M-1 not_reproduced、L-1 confirmed）。

### 判断

| 判断 ID | 区分 | 根拠 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1@371a34e9f76b` | 解消済み（前は対応する） | `4d7016a` で、サイクル 1 で再現した全入力（installer の 9990 ファイル、詰めた記録 60000 項目、init、所有の移転だけ、日本語のキー）が書き込みの前に `PLUGIN_SKILL_RECORD_TOO_LARGE` で止まり、同梱を含めて何も書かない。上限ちょうど（8,388,608 バイト）は書けて次回読め、1 バイト超は拒否。項目が変わらない update は書き直さない（review-verify・fix-check・テスト `OversizedRecordsAreRefusedBeforeAnyWrite`） |
| `claude-opus-5-5-commit-4d7016ad8cf42402b7a0e0cbb1f944cc31819172#L-1@4d7016ad8cf4` | 対応しない（引き継ぎ） | サイクル 1 の判断のまま。review-verify が再現したが、記録に無い新しい根拠（別の利用経路・結果）は無い。ファイルの上書き・消失は無く、止まるのは `modified-conflict` のエラーで見える |

解消済み 1 / 対応する 0 / 対応しない 1。実装と食い違う記述（`PluginSkillManager.cs` の記録を消さない旨のコメント、元の Spec の記録を消さない旨、PR 本文の概要）は、大小だけの改名の場合を除けば正しく、その場合は PR の説明と本書の既知の制限に書いた。致命的でないので直さない（コメントを直すには新しい commit とレビューが要る）。

### 結論 2 の検証と最終化

- 検証（`4d7016a`、修正用の worktree、作業ツリーは clean）: `dotnet build ResoLoop.slnx --nologo` 警告 0・エラー 0、`dotnet test ResoLoop.slnx --nologo --no-build` unit 579 件・integration 22 件成功（サイクル 1 の最後の検証と同じ HEAD。以後 commit は無い）
- base: `origin/feat/plugin-v2` の先端は `dd0b40fb216b0c9fbd82da44903195a885104015` で head の祖先。head 単独のツリーで検証した
- マージしてよい範囲: usaturn/resoloop の open で draft でない PR
- 最終化は `finalize.py`（`--spec-commit` 無し）が、状況の投稿・公開 CI（windows）の成功・base の先端の確認の後にマージする。結果は状況コメントと完了報告に書く
