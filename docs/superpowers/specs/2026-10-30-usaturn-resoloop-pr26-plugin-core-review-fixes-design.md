# usaturn/resoloop#26 プラグイン基盤のレビュー修正（サイクル 2）

## 管理

- 状態: **completed**
- 対象: [usaturn/resoloop#26](https://github.com/usaturn/resoloop/pull/26)（`feat/create-reso-world-issue-297-plugin-core` → `feat/plugin-v2`）。Issue [create-reso-world#297](https://github.com/usaturn/create-reso-world/issues/297)、文書 PR [create-reso-world#299](https://github.com/usaturn/create-reso-world/pull/299)
- 設計の基準: [#297 の設計](2026-10-29-create-reso-world-issue297-plugin-core-design.md)（承認 `5353ba7`）と [Plan](../plans/2026-10-29-create-reso-world-issue297-plugin-core.md)。本書はその上のレビュー修正の記録で、設計の約束は変えない
- サイクル 1（`openai-codex/gpt-6-astra`、2026-10-29、停止）の記録は #297 の設計の 9 章にある。サイクル 2 からは本書に書く。#297 の設計の状態は、承認された設計内容の状態（approved）に戻した
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/26` を指定した（完遂の既定の経路）。その PR の承認済み実装修正、結論 2 のマージ・関連 Issue の更新までを含む。一般的な外部実装・別 PR には広げない
- planner: `claude-opus-5-5`（runtime `claude-code`、Claude Code 2.1.312）。サイクル: 2。現行 HEAD: `e3a4df87a7afce735cee412a22efb73200904f20`、base: `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`
- 確認済みの一覧: `PARENT_ROOT/reviews/usaturn/resoloop/#26-feat-create-reso-world-issue-297-plugin-core/verified/e3a4df87a7af.json`（confirmed 5、not_reproduced 0、unverified 0）

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| claude-opus-5-5.md | claude-opus-5-5 | claude-code | e3a4df87a7af | はい | Approve |
| SWE-2-Max.md | SWE-2 Max | devin | e3a4df87a7af | はい | Approve |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | e3a4df87a7af | はい | Approve |

入力から外したファイルは無い。claude-opus-5-5 の runs の記録には保存の段階の HTTP 503 が残るが、レビューファイルと findings の JSON は `validate`・`check-pair` を通った。

## 1. 全指摘と分類

前のサイクルの判断は 5 件すべて `unverified`（サイクル 1 の停止）で、このサイクルで全件を判断し直した（`changed`）。

| 判断 ID | 指摘 | 確認 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| claude-opus-5-5#M-1@e3a4df87a7af | global 設定の `safe.bareRepository=explicit` で Git URL の導入が `PLUGIN_GIT_REF_NOT_FOUND` | V-2 confirmed | **対応する** | 下記 2.1 |
| claude-opus-5-5#U-1@e3a4df87a7af | `/proc` 走査中のプロセスの回収で `IOException`（ESRCH）になり、成功した Git が `PLUGIN_GIT_FAILED` | V-5 confirmed | **対応する** | 下記 2.2 |
| SWE-2-Max#M-1@e3a4df87a7af | host 付きの file URL が project との重なり検査を通らない | V-1 confirmed | 対応しない | 重なり拒否が防ぐ損害（staging の再帰コピー、ignored・未コミットの内容の混入）は Git URL の経路では起きない。導入されるのは名指しした repository のコミット済み blob だけで、同じ project の ignore 済みの管理領域に置かれる（再現で、ignored の偽の秘密・未追跡のファイル・staging・`.resoloop/plugins` が入らず、管理領域の外が不変であることを確かめた）。秘密の露出・データの消失・誤った対象への操作に当たらない |
| claude-opus-5-5#L-1@e3a4df87a7af | Git ルートの ignore 済みの入れ子 repository で導入を拒否する | V-3 confirmed | 対応しない | 明示のエラーで止まる fail-closed の拒否で、ファイルをコピーしない。ignore 済みの入れ子 repository をどう扱うかは仕様の是非（Spec に明記が無い）。回避は入れ子の repository を外すか clean export を使う |
| claude-opus-5-5#L-2@e3a4df87a7af | 端末から ssh の確認が要ると 120 秒止まってから失敗する | V-4 confirmed | 対応しない | 「prompt は無効」の設計どおり最後は失敗し、期限の後にプロセスは残らない（再現で確認）。違いは待ち時間とタイムアウトの表示だけで、致命的な結果に当たらない |

区分の件数: 解消済み 0 / 対応する 2 / 対応しない 3（ほかに自己レビューの指摘 1 件を対応しないとした。3 章）。

仕様の論点（1 行）: L-1 は「Git ルートの入力で、一覧に現れない入れ子の repository も拒否するか」。L-2 は「端末から実行したとき ssh の確認を即時の失敗にするか」。どちらも #298 の CLI 結線で利用者の経路が決まったときに見直す。

## 2. 対応する項目

### 要件対応（PR・#297 の設計・Plan と今回の修正）

| 条件（基準の文書） | 今回の修正方針 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| Git URL＋明示 ref で導入できる（設計 6 章・PR 本文の「Git URL＋明示ref」） | bare clone への操作を `--git-dir` で明示する（2.1） | 利用者の global 設定に `safe.bareRepository=explicit` があっても、5 種の ref で導入が成功し、記録の commit が一致する | 一時のテストを `XDG_CONFIG_HOME` 付きで実行 |
| HOME を差し替えず、global/system の設定を維持する（設計 4 章 Git） | 維持する。利用者の安全設定を `-c` で上書きしない | 修正は利用者の設定を変えない | 差分の確認 |
| Git 環境で別の repository を選ばない（設計 6 章の防御範囲） | `--git-dir` は Export が作った bare clone の絶対パスだけを指す | 既存テスト `GitIgnoresInjectedRepositoryState` が通る | Plugin のテスト |
| 期限・子孫の停止を確認し、成功としない（設計 4 章 Git、Plan Task 3） | 終了確認で、読み取り中に回収されたプロセス（ESRCH）だけを「居ない」として飛ばす（2.2）。ほかの失敗は従来どおり止める | 負荷の下でも成功した Git が成功を返す。期限・子孫の停止のテストは通る | 負荷の一時テスト、`GitFailuresAndTimeoutNeverBecomeSuccessfulCopies` |
| テストは S だけ（設計 6 章、`AGENTS.md` の「テストの採用基準」） | 2 件ともテストを足さない（下記） | 追加のテスト無し | 差分の確認 |

共有する条件: 2 件とも `PluginGit.cs` の Git の子プロセスの実行（`GitProcess`・`LinuxProcess`）を通る。統合担当は planner で、修正後の HEAD の Plugin の全テストと、2 件の一時テストを同じ HEAD で実行して照合する。

### 2.1 claude-opus-5-5#M-1: bare clone の操作対象を明示する

- 致命的である理由: Git URL の導入は PR の Core API の主要な 2 経路の 1 つで、設計は利用者の global 設定を意図して保つ。Git が用意している安全設定 `safe.bareRepository=explicit` を global 設定に入れた利用者は、どの ref を指定しても導入できず、原因も「ref が無い」と誤って示される（主要な処理が止まる）。(a) 再現した誤動作
- 守る条件: 導入用に作った bare clone への Git 操作は、利用者の Git 設定で対象の探索が変わらないよう、操作対象を明示して実行する
- 原因: `Export` が bare clone への `rev-parse`・`ls-tree`・`cat-file` を cwd からの自動探索に任せていたため、利用者の global 設定の `safe.bareRepository=explicit` の下で Git が探索した bare repository の使用を拒否し（終了 128）、`ResolveCommit` がその失敗を ref の不在に読み替えた
- 修正方針: bare clone を対象にする呼び出しに、グローバルオプション `--git-dir=<bare clone の絶対パス>` を付ける。bare clone を対象にする呼び出しを 1 か所の helper に通し、今後の呼び出しで付け忘れない形にする（例: `GitProcess` に bare repository 用の `Read`/`Stream` を足す）。cwd は従来どおり bare clone にしてよい
- 採らない案: `-c safe.bareRepository=all`（利用者の安全設定を上書きする）、環境変数 `GIT_DIR`（`GIT_*` を除く隔離の規則と混ざる）、`ResolveCommit` で Git 自体の失敗と ref の不在を区別する追加の検査（原因は `--git-dir` で無くなり、ほかの原因は仮定の範囲）
- テスト: 足さない。壊れたときは、その設定の利用者の初回の導入がエラーで止まる（`AGENTS.md`「テストの採用基準」の L）。一時のテストで確かめる

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| bare clone への操作は対象を明示する | `ResolveCommit` の `rev-parse --verify`（`PluginGit.cs:147`） | 修正する | explicit の下で 5 種の ref が同じ commit に解決し、曖昧な名前は従来どおり拒否 | 一時テスト（explicit）、`ExplicitCommitPrefixesAndAmbiguousNamesDoNotSelectAnotherCommit` | `81df319`: explicit の下で main・refs/heads/main・HEAD・完全な SHA・tag v1 の 5 種が導入に成功（一時テスト）。explicit の下の Plugin 43 件（`ExplicitCommitPrefixesAndAmbiguousNamesDoNotSelectAnotherCommit` を含む）成功。修正前（`e3a4df8`）は 5 種すべて `PLUGIN_GIT_REF_NOT_FOUND` |
| 同上 | `ls-tree -r -z -l --full-tree`（`PluginGit.cs:75`） | 修正する | explicit の下で tree を読める | 一時テスト（explicit）で導入が成功 | `81df319`: explicit の下で導入が成功し、記録の files が package と一致（一時テスト、`GitInstallPublishesOnlyVerifiedPackageAndPinnedRecord` 成功） |
| 同上 | `cat-file blob`（`PluginGit.cs:93`） | 修正する | explicit の下で blob の bytes と実行 bit が一致 | 一時テスト（explicit）、`ExportPinsBlobsWithoutExecution` | `81df319`: explicit の下の `ExportPinsBlobsWithoutExecution`（独立した SHA と実行 bit の照合）成功 |
| 同上 | `clone --bare --no-local`（`PluginGit.cs:72`） | 既に満たす | 対象の URL と保存先を引数で明示し、cwd の探索に頼らない。修正前の再現でも clone は成功し、失敗は ref の解決だった | 一時テスト（explicit）で導入が成功 | 修正前の再現: clone 成功・`rev-parse` で失敗（V-2） |
| 同上 | `GetLocalFiles` の `rev-parse --show-toplevel` ほか（`PluginGit.cs:33-50`） | 既に満たす | 非 bare の作業ツリーの探索は `safe.bareRepository` の対象外。bare のローカル入力は explicit の下でも拒否される | explicit の下で `GitSourceClassificationFailsClosed` を実行 | `81df319`: explicit の下の `GitSourceClassificationFailsClosed`（bare のローカル入力の拒否を含む）成功 |
| 同上 | 既定の設定の導入（変更前の挙動を保つ） | 既に満たす | 既定の設定の結果は変わらない | Plugin の全テスト | `81df319`: 既定の設定で RLoop.Tests 全体 573 件成功 |
| 同上 | 注入された `GIT_DIR` などの環境 | 既に満たす | `GIT_*` は除いたまま。`--git-dir` は Export が作ったパスだけ | `GitIgnoresInjectedRepositoryState` | `81df319`: `GitIgnoresInjectedRepositoryState` が既定・explicit の両方で成功 |

### 2.2 claude-opus-5-5#U-1: 終了確認で回収済みのプロセスを飛ばす

- 致命的である理由: Git の呼び出しのたびに、Git が成功していても、同じ機械の無関係なプロセスの回収の時期によって導入が `PLUGIN_GIT_FAILED` になる。中程度の負荷（約 100 回/秒のプロセスの終了）で `GetLocalFiles` が 2481 回中 3 回、強い負荷で 2021 回中 12 回失敗した。Git URL の導入は blob ごとに `cat-file` を起動するので、ファイルの多い package ほど失敗しやすく、並列にプロセスを起動するテストの CI でも起こり得る（主要な処理や CI が止まる）。(a) 再現した誤動作
- 守る条件: Git のプロセスグループの終了確認は、無関係なプロセスの終了・回収の時期に左右されず、グループの member が残っていなければ成功し、残っているときだけ待つ・失敗する
- 原因: `GroupHasExecutingMembers` が `/proc` を列挙してから各 `/proc/<pid>/stat` を読むまでの間に、そのプロセスが回収されると読み取りが ESRCH の `IOException`（`HResult` 3、No such process）になり、それを「居ない」として扱わずに伝播させた
- 修正方針: `/proc/<pid>/stat` の読み取りで、ESRCH の `IOException`（`(HResult & 0xffff) == 3`。PR の `PluginProjectLock` も同じく `HResult` の errno で判定している）だけを、`FileNotFoundException`・`DirectoryNotFoundException` と同じく「そのプロセスは居ない」として次へ進む。ほかの `IOException`・読めない内容・解析できない stat は従来どおり失敗にする（fail-closed を保つ）。検証で、回収中（状態 `X`）のプロセスの stat が pgrp を `-1` と報告し、`NumberStyles.None` の解析で失敗することが分かった（同じ原因の適用漏れ）。状態 `Z`・`X` の判定を pgrp の解析より前に置き、実行中でない entry として飛ばす（変更前も `Z`・`X` は member に数えていなかった）
- 採らない案: `IOException` をすべて飛ばす（権限など別の原因で確認を素通りさせる）、`/proc/<pid>/stat` の代わりに `waitid` などで確かめる（グループの全 member を待つ仕組みに作り直す変更で、範囲が広い）
- テスト: 足さない。壊れたときは `PLUGIN_GIT_FAILED` のエラーとして現れる（L）。負荷の一時テストで、修正前と同じ条件で失敗が 0 になることを確かめる

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 終了確認は無関係なプロセスの回収に左右されない | `GroupHasExecutingMembers` の `/proc/<pid>/stat` の読み取り（`PluginGit.cs:479`） | 修正する | 読み取り中に回収されたプロセスは「居ない」になり、Git の成功が成功のまま返る | 負荷の一時テスト（強い負荷 30 秒）で失敗 0 | `81df319`: 強い負荷で 2289・2352・2496 回、中程度の負荷で 2532 回、失敗 0。修正前（`e3a4df8`）は強い負荷 2021 回中 12 回・中程度 2481 回中 3 回失敗（すべて `PluginGit.cs:480` の ESRCH） |
| 同上 | 同じ読み取りの ESRCH 以外の `IOException` | 既に満たす（変えない） | 従来どおり例外になり `PLUGIN_GIT_FAILED` | 差分の確認（ESRCH だけを条件にしている） | `81df319` の差分: `when ((error.HResult & 0xffff) == UnixNative.NoSuchProcess)` の 1 種類だけを飛ばす |
| 同上 | 回収中（状態 `X`）のプロセスの stat の解析（`PluginGit.cs:482-485`） | 修正する（検証で判明した適用漏れ） | 状態 `X` の stat は pgrp が `-1` になり、`NumberStyles.None` の解析が失敗して `PLUGIN_GIT_FAILED` になる。状態 `Z`・`X` を pgrp の解析の前に「実行中でない」として飛ばす。それ以外の状態で解析できない stat は従来どおり失敗にする | 負荷の一時テスト（強い負荷 30 秒）で失敗 0 | 修正 1 回目（`a33445e`）の後の強い負荷で 2187 回中 1 回 `Could not verify Git process group termination.`。`/proc` 走査の単独の計測で、解析できない 3 件はすべて状態 `X`・pgrp `-1` の stat（`894233 (date) X 0 -1 -1 0 -1 ...`）。`81df319`（`Z`・`X` を解析の前に飛ばす）の後は、強い負荷 3 回・中程度 1 回で失敗 0 |
| 同上 | 状態 `Z`・`X` 以外で解析できない stat | 既に満たす（変えない） | 従来どおり `PLUGIN_GIT_FAILED`（fail-closed） | 差分の確認 | `81df319` の差分: 欄が 3 つ未満、または `Z`・`X` 以外で pgrp を解析できなければ従来どおり throw |
| 同上 | グループの member が残っているときの待ちと 5 秒の期限（`PluginGit.cs:458-462`） | 既に満たす（変えない） | 期限・子孫の停止のテストが通る | `GitFailuresAndTimeoutNeverBecomeSuccessfulCopies`・`ContainedLaunchDoesNotExecuteAGitFromThePackage` | `81df319`: 両テストを含む Plugin 43 件と全体 573 件が成功 |
| 同上 | 終了確認の前のグループへの SIGKILL（`PluginGit.cs:455`） | 既に満たす（変えない） | 包含の境界は変わらない | 差分の確認 | `81df319` の差分: SIGKILL・期限・`waitpid` は変わっていない |
| 同上 | Windows の Job Object の経路（`WindowsProcess.CompleteCoreAsync`） | 対象外 | `/proc` を使わず Job の計数で確かめるので、この原因と関係しない | ― | 対象外（理由のとおり） |

「失敗時の検証」: 2.2 の守る条件は失敗を正しく返す側ではなく、成功を誤って失敗にする側の修正で、拒否の範囲を広げも狭めもしない（ESRCH の 1 種類だけを「居ない」に加える）。状態の比較・負例の追加は行わず、拒否側が変わらないことは差分の確認と既存の停止のテストで確かめる。

### 実行した検証

修正は 2 つの commit になった。`a33445e`（2.1 と 2.2 の ESRCH）と、検証で判明した適用漏れを直した `81df319`（2.2 の状態 `X`）。どちらも `src/RLoop.Core/Plugins/PluginGit.cs` だけを変え、テストは足していない。

| 対象版 | コマンド | 結果 |
| --- | --- | --- |
| `a33445e`（実装担当） | `dotnet build tests/RLoop.Tests/RLoop.Tests.csproj --nologo` / `dotnet test ... --no-build --filter FullyQualifiedName~Plugin` / `git diff --check` | 終了 0、警告 0・エラー 0 / 43 件成功 / 出力なし |
| `a33445e`（planner） | 強い負荷の下の一時テスト（30 秒） | 2187 回中 1 回 `Could not verify Git process group termination.`。原因を `/proc` 走査の単独の計測で状態 `X`・pgrp `-1` と特定し、`81df319` で直した |
| `81df319`（実装担当） | 上と同じ build / Plugin のテスト / `git diff --check` | 終了 0、警告 0・エラー 0 / 43 件成功 / 出力なし |
| `81df319`（planner） | `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --no-build`（既定の配置） | 573 件成功（ビルド出力をリポジトリの外に置くと、fixture のパスを相対で探す `ApplyWorkflowTests` の 2 件が `/tmp/examples/house-world.json` を見つけられずに失敗する。PR と関係しない配置の問題で、既定の配置では成功する） |
| `81df319`（planner） | `env XDG_CONFIG_HOME=<explicit> dotnet test ... --filter FullyQualifiedName~RLoop.Tests.Plugin` | 43 件成功 |
| `81df319`（planner） | explicit の下の一時テスト（5 種の ref・ignore 済みの入れ子・host 付きの file URL） | 5 種の ref が導入に成功。L-1・SWE M-1 は変わらない（対応しない） |
| `81df319`（planner） | 強い負荷 3 回・中程度の負荷 1 回の一時テスト（各 30 秒） | 2289・2352・2496・2532 回、失敗 0 |
| `81df319` | `bash scripts/scan-before-push.sh -C <worktree> --base origin/feat/plugin-v2` | 10 commit、検出なし |

一時テストは `PARENT_ROOT/tmp/agents/review-fix-planning-pr26.*/repro/` に置いた写しを、`mktemp -d` の展開ツリーにだけ入れて実行した（コミットしない）。

## 3. 自己レビュー（1 回）

`run_roles.py --phase self-review` の 1 回の呼び出しで、self-review と fix-check の 2 つの役割を同時に動かした（割り当てはどちらも `self`。工程の記録に `pre_push_review` の枠を 1 件予約）。自己レビューの後の修正は無く、再レビューはしていない。

| 役割 | 担当 | 対象 | 結果 |
| --- | --- | --- | --- |
| self-review（観点 2: PR 全体） | 司令塔のサブエージェント（claude-opus-5-5、claude-code）が pr-review の非対話の入口で実行。16:38:43Z〜16:56:06Z（1043 秒） | 固定の全体差分 `a7be2dd..81df319`（17 ファイル・3523 行）と前回の修正の範囲 `e3a4df8..81df319` | Low 1 件（下）。Critical・High・Medium 0。Merge recommendation は Approve。このサイクルの skip 3 件は新しい根拠なしで Decided findings。保存: `claude-opus-5-5-commit-81df3196b9fdc18a46b5dcc481496e48cbe57d45.md` と findings の JSON（validate・check-pair 済み） |
| fix-check（観点 1: 反証、観点 3: 検証の検出力） | 司令塔（claude-opus-5-5）。16:37:56Z〜16:41:00Z（184 秒） | from `e3a4df8` → to `81df319`、Fix 2 件 | 主張 7 件すべて holds、変更ファイル 1 件 passed、文書の候補 0 件、新しい問題 0 件。同じ一時テストが from で失敗・to で成功する対照を確かめた。保存: `verified/81df3196b9fd.fix-check.json`・`.statement-candidates.json`・`.fix-check.md` |

自己レビューの指摘の判定:

| 指摘 | 判定 | 根拠 |
| --- | --- | --- |
| claude-opus-5-5-commit-81df3196b9fdc18a46b5dcc481496e48cbe57d45#L-1@81df3196b9fd: `/proc` を `hidepid=noaccess`（1）でマウントし別ユーザのプロセスが見える Linux では、`GroupHasExecutingMembers` が別ユーザの stat を読めず（EPERM の `UnauthorizedAccessException`）、Git を使う導入がすべて `PLUGIN_GIT_FAILED` になる | 対応しない | 発生条件が `hidepid=noaccess` の `/proc` に限られ、PR の動作環境（Linux Dev Container・Windows）の既定では起きない。硬化設定で一般的な `hidepid=invisible`（2）では起きない（自己レビューの対照で確認）。失敗は明示のエラーで止まり、既存の導入物・データは変わらない。修正前の `e3a4df8` から同じで、このサイクルの修正が原因ではない。U-1 の原因（読み取り中の回収の時期）とは別の原因（`/proc` の権限）で、同じ経路の同じ守る条件の再発ではない。PR 本文の既知の制限に書いた |

この判定により、「同じ条件の再発と設計の見直し」のきっかけ 3（自己レビューでの再発）には当たらない。2.2 の状態 `X` の修正は、自己レビューの前の司令塔の検証で見つけた同じ原因の適用漏れで、経路表に戻して同じサイクルで直した（Spec の 2.2 の経路表）。最初の Spec で解析の失敗の経路を「既に満たす」とした判断の誤りであり、実装担当の誤りではないので、工程の記録の rework には数えない。

## 4. 結論

- 結論: **1 修正して push**（`81df3196b9fdc18a46b5dcc481496e48cbe57d45` を既存 PR の head `feat/create-reso-world-issue-297-plugin-core` へ fast-forward で push する）
- 対応する 2 件（M-1・U-1）を直し、対応しない 4 件（SWE M-1・L-1・L-2・自己レビューの L-1）は PR 本文の「未実行・制限」に条件と回避方法を書いた
- 役割と回数: implement は `claude-opus`（agent-runner、claude-code）を 2 回（`a33445e`: request `6bcc5a81c29d48079489489584266e1b`・237 秒、`81df319`: request `383cbb50937646189a39f100b38e8974`・208 秒）。自己レビューは `run_roles.py` の 1 回（self-review・fix-check とも `self`）
- 未確認の事項: Windows（`--git-dir` の引数の引用、Job Object）と異なる libc は実行環境が無い。push 後の公開 Windows CI で確かめる
- 工程の記録: `verified/e3a4df87a7af.planning.json`。確認済みの一覧: `verified/e3a4df87a7af.json`
