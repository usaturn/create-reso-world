# PR #48: detached 整理手順のレビュー修正

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/48
- 関連 Issue: #47
- 検証したコード HEAD: `532392efa673cc983377dc91224d8b4a70a61bad`
- ブランチ: `fix/issue-47-detached-cleanup`
- 状態: completed
- 実行許可: ユーザーが `review-fix-planning #48` を指定。計画のみの制限はなく、同スキルの完遂経路として修正・検証・既存 PR への push・結果投稿まで実施する。
- 結論: 1（修正して push）。マージはこの結論では行わない。
- 文書の新規作成理由: committed な specs/plans を PR #48・Issue #47・detached 整理のテーマで照合し、該当文書が存在しないことを確認した。過去の unrelated な完了済み計画は更新しない。
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-47-detached-cleanup`（既存 worktree を clean・PR HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力と分類

入力は `reviews/#48-fix-issue-47-detached-cleanup/` の全4ファイル。各対象 HEAD は `532392efa673` で、全件について取得した PR head の祖先であることを確認した。

| ID | 入力ファイル / 元 ID | 指摘 | 分類と根拠 |
|---|---|---|---|
| R1 | `deepseek-deepseek-v4.1-flash.md` L-1 | stale-lock の旧 main 操作例 | 対応する (a,b)。実スクリプトの clear 後の案内を一時 repo で実行すると、main 不在なら作成・attach、古い main があれば更新する。利用者の了承のない ref/HEAD 操作になる。 |
| R2 | `claude-opus-5-5.md` L-1 | 同上 | 対応する (a,b)。R1 と同じ再現・修正に統合する。 |
| R3 | `SWE-2-High.md` L-1 | 同上、JSON stderr 側の列挙も旧仕様 | 対応する (a,b)。`stale_git_lock.sh:556–562` の両出力経路が復旧後の案内。通常出力の誤操作を再現した。 |
| R4 | `gpt-6.1-sol.md` M-1 | linked caller の HEAD で branch 削除を判定 | 対応する (a,b)。upstream 未設定と削除・prune 済みの2ケースで、手順3の log は空なのに実手順8が not fully merged で失敗。MAIN_ROOT を明示した -d は成功し、主要な整理処理が完了しない誤動作である。 |
| R5 | `deepseek-deepseek-v4.1-flash.md` I-1 | 最終 git status の報告先が caller | 対応しない（単独）。MAIN_ROOT clean / caller dirty の差は再現したが、読取専用の報告で、更新先の安全確認は手順7で済む。ただし R4 の同一対象指定に依存する隣接経路として報告コマンドも MAIN_ROOT に揃える。 |
| R6 | `SWE-2-High.md` L-2 | set -e / exit による永続シェル終了 | 対応しない。bash の errexit によるシェル終了は確認したが、データ損失・誤対象操作・主要処理の誤結果は確認されていない。失敗時の停止自体は意図した安全性であり、pi は呼び出しごとのシェル。ブロックの停止構造は変えない。 |
| R7 | `deepseek-deepseek-v4.1-flash.md` Test suggestions 3（IDなし） | 衝突しない ignored directory の任意追加テスト | 対応しない。将来の保険で、現行の致命的な欠陥を示していない。今回のテスト追加には含めない。 |
| R8 | 自己レビュー・反証担当 Important | 同名ローカル branch/tag の `origin/main` が remote ref を隠す | 対応しない（PR以前からの致命的な制約）。base `269f3cc` と head `532392e` の両手順7を隔離 repo で実行し、tag・branch の各入力で両版とも exit 0 なのに取得した remote main と違う古い commit に留まった。PR が持ち込んだ問題ではなく、別原因の既存問題なので直さない。PR説明の保証に条件と回避方法を明記する。 |
| R9 | 自己レビュー・反証担当 Minor | fork HEAD 保持の表現と sync の main 更新 | 対応しない。承認済み sync が clean な main を早送りするのは既存の意図した挙動（`scripts/resoloop-fork.sh:134–136`）。今回変更した手順8は削除のために HEAD を動かさないとの限定で整合する。PR説明でも手順7・8の保持と sync を区別する。 |

入力分類: **解消済み0 / 対応する4 / 対応しない3**。自己レビュー2件を加えた全件分類: **解消済み0 / 対応する4 / 対応しない5**。重複指摘は入力ごとに数え、IDなしの任意提案も含む。独立した修正原因は2つ。各 finding に付随する Test suggestions は元 finding の検証方針で判定し、二重に数えない。

R1–R3 の案内文そのものを固定するテストは作らない（AGENTS.md）。JSON schema と出力先の分離は既存の挙動を保つ。R4 は実 SKILL の実行結果で回帰を検出するテストを追加する。

## 再現・確認

検証用 worktree は `mktemp -d /tmp/review-fix-planning.XXXXXX` の配下に detached HEAD で作成し、SHA 一致を照合した。source/test は clean の専用 worktree または隔離 worktree の committed 内容だけを使った。

- R4: 古い active-feature の linked project を作り、origin/main に追加コミットを入れる。merged-feature は追加コミットを含む。upstream 未設定、remote feature 削除後の fetch --prune の2入力で、手順7成功後の実手順8が exit 1 / not fully merged。`git -C MAIN_ROOT branch -d` への対照だけで成功し、caller HEAD・既存 main は保持される。
- R1–R3: main 不在／古い main の2入力で空の index.lock を置き、実 helper の clear を実行。出力された旧例 `git switch main; git merge --ff-only origin/main` の実行は exit 0 だが、HEAD が main に attach し、main ref が origin/main に進む。
- R5: MAIN_ROOT は clean、caller は編集済みの構成で、cwd 基準 status だけが caller の変更を表示する。
- R6: 独立 bash で `set -e; false; printf alive` は exit 1、後続出力なし。安全停止を解除する変更は行わない。
- Git 2.55.0 の実行結果を根拠にした。Context7 `/git/htmldocs` の git-branch 文書でも -d が upstream または HEAD の取り込みを確認することを照合した。prune 済み upstream の結果は実行で確かめた。
- 初期再現の隔離 worktree と親ディレクトリは、Spec 作成前に worktree remove を経て削除済み。

## 修正方針と影響経路

### R1–R3: 元の失敗操作以外へ誘導しない

復旧成功時の案内を、ブランチ名を持つ別操作例ではなく「元の失敗操作だけを再実行する。cleanup 手順7から来た場合は MAIN_ROOT の clean 確認からやり直す」にする。通常出力は stdout、JSON の案内は stderr のままにする。ロック検出・削除・exit code・JSON schema は変更しない。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
|---|---|---|---|
| ロック復旧後も、了承されていない main の作成・更新や別操作への切替を案内しない | `stale_git_lock.sh` clear 成功 / text 出力 | 修正する | 実際に clear し、main 不在・古い main の refs/HEAD を保ったまま元の cleanup ブロックを再実行する |
| 同上 | 同 helper / JSON stderr 案内 | 修正する | stdout が1 JSON objectのまま、案内は stderr、clear 後に元の操作を再実行できる |
| 同上 | stale-lock SKILL の除去節・関連スキル節 | 既に満たす | 全文照合。MAIN_ROOT clean 確認から手順7へ戻す指示がある |
| 同上 | clear で removed=0 / check / holder あり・不明 | 既に満たす | 既存 stale-lock tests。成功案内の出力分岐に入らない |
| 同上 | ff_merge_keep_untracked.sh の独立した ff 復旧 | 対象外 | main 作成案内がなく、cleanup 手順7で使わないことを SKILL が明記 |

### R4: 更新・branch 削除・最終確認の対象を取り違えない

create-reso-world の手順8は `git -C "$MAIN_ROOT" branch -d <branch>` とする。既存の手順7を変更せず、-D への逃げ道を作らない。fork の手順7省略と HEAD 保持は変えず、fork で削除・報告するときの -C は対象 fork root にすることを同じ箇所で明示する。手順11の status も同一条件の経路として MAIN_ROOT を明示する。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
|---|---|---|---|
| create-reso-world の branch 削除は更新済み MAIN_ROOT の HEAD を基準にし、caller や他 repo を削除先にしない | SKILL 手順8 | 修正する | 実手順7・8のブロックを linked project cwd から実行。upstream 未設定／prune 済み2入力で branch 削除・caller HEAD/ref・既存 main を比較 |
| 同上 | `run_step7` の following_delete 合成 | 修正する | 合成した独自 -C コマンドをやめ、実手順8を抽出して実行。旧実装で新規テストが失敗することを確認 |
| 同上 | 手順7 dirty/status/checkout 失敗時の後続削除 | 既に満たす | 実手順8を接続した既存の失敗テストを再実行 |
| 同上 | 手順3の origin/main マージ判定 | 既に満たす | refsは共通。R4の各ケースで origin/main..branch が空なのを比較 |
| 同上 | 本当に未マージの branch | 既に満たす | 実手順8で -d が拒否し、candidate ref/HEAD が残る負例 |
| 同上 | fork の branch 削除 | 既に満たす（全 Git 操作に git -C external/resoloop を指定する既存規定） | 手順8の経路分離の読解、可能なら別 repo の同名 branch を保持する挙動確認。fork の HEAD を動かさない |
| 更新対象の status を最終報告する | 手順11 / R5の隣接経路 | 修正する | linked project から実 status コマンドを実行し、MAIN_ROOT と caller の異なる状態を識別する |
| 上記の fork 版 | 手順11 fork経路 | 既に満たす | 冒頭の fork対象 root 指定と一致することを確認 |
| 同じ Git repo の共通情報を読む | worktree list / branch -a / remote refs | 既に満たす | これらは worktree固有HEADの更新済み状態に依存しない |

## 選択肢と再発判定

- 採用: 対象 root を既存ブロックで明示し、復旧出力は元の手順に戻す。2つの原因を小さく直し、fork の HEAD 保持や安全停止を変更しない。
- 不採用: 全 cleanup 手順を新 helper と共通 state に移す。今回の欠陥には不要で、削除の承認や gate A/B まで変更範囲が広がる。
- 不採用: linked caller を非対応にして保証を狭める。PR と既存テストが対応する経路であり、対象 root の明示で解決できる。
- 設計見直しのきっかけ: なし。PR履歴は `fd75e21` と `532392e` の初期実装・説明順変更だけで、以前のレビュー修正コミット／同テーマSpecは存在しない。
- 失敗時の扱いを新設・変更する修正ではないため、ガードを外す全状態の変異検証は適用外。既存の dirty・ignored衝突・lock失敗時停止は実ブロックとの結合で再検証する。

## 実装・検証タスク

- [x] 全入力・各対象HEADとPRの対応、context、専用worktreeを確認
- [x] 全指摘の再現・分類、同条件の経路と既存文書・PR履歴を確認
- [x] R4の挙動テストを先に追加し、旧ブロックで不具合を検出
- [x] R1–R4と同条件の報告経路を修正
- [x] 関連pytest、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、diff check
- [x] 自己レビュー1回（反証 / PR全体 / テストの検出力）、全指摘を判定
- [x] 最後のコード修正後の検証・記録を照合し、completedに更新

後続の公開工程はSpecを1回だけcommitして既存PRへ通常pushし、専用helperで状況コメントを投稿する。公開結果は本Specへ追記せずPRコメントと作業報告に残す。再利用worktreeは保持する。

## 検証結果

実装担当が同期実行を完了し、controller は変更差分と各ログの終了コード・結果を確認した。自己レビュー後のコード変更はない。レビューに渡した差分 snapshot と公開前の差分が一致することを cmp で照合した。

| 検証 | 結果 |
|---|---|
| 実手順7→8 / status の旧コード RED | 3 failed / 15 passed。linked branch削除の unset/pruned と caller status が意図した理由で失敗 |
| 修正後の同一テスト | 18 passed、exit 0。controllerが自己レビュー後にも再実行し18 passed（3.23秒）を確認 |
| controllerの公開前確認 | docs/instructionsのshell検査、helper bash -n、diff check成功。自己レビューsnapshotからコード差分不変 |
| cleanup・stale-lock の関連 pytest | 129 passed、exit 0 |
| `bash .devcontainer/run-tests.bash` | 28 suites passed、exit 0 |
| `bash scripts/check-layout.sh` | PASS、exit 0。4プロジェクトの同梱スキル同期警告は保持 |
| `uv run pytest tests/skills .agents/skills -ra` | 505 passed / 1 skipped、exit 0 |
| リポジトリ既定の `uv run pytest -ra` | 573 passed / 1 skipped、exit 0。各 world の独立pytestは実行していない |
| stale clear→元の手順7再実行 | text/JSON × main不在/古いmainの4ケース成功。clear前後のHEAD/refs/reflogs保持、JSON stdout1object・案内stderrを確認 |
| skill-efficiency checker | cleanupの変更前後ともissue/warningなし。既存suggestion2件は同じ |
| helper `bash -n`・`git diff --check` | exit 0 |
| R8 の旧版・現行版対照 | base/head × tag/branch の4ケースとも同じ誤参照を再現。PR以前からの制約と確定し、隔離worktreeはremove後に親ごと削除 |

R1–R3 の案内文の意味はソースと実出力の読解による確認であり、4ケースの復旧検査が案内文の意味を自動判定したとは主張しない。

skip は `tests/skills/test_skill_packages.py::SkillPackageTests::test_targeted_skill_semantics`（`SKILL_UNDER_TEST` 未指定の任意検査）。fork実checkout/dotnet、LLMによるeval実行は未実施。変更したPython/bashのactive LSP probeは2pathともinconclusiveであり、診断0件をcleanの根拠にしない。実行検証とsyntax checkを根拠にした。対象外の4プロジェクトの同梱スキルは更新していない。

検証ログはセッションの一時領域 `/tmp/review-fix-planning.tzjdlu/` に保存して公開前に確認した。ログやscratchはGitに追加しない。

## 自己レビュー

修正後の自己レビューは1回。ランタイムの同期委譲規定に従って3担当を直列に起動した。

| 観点 | 結果 | 判定 |
|---|---|---|
| 反証 | Important1（R8）・Minor1（R9） | R8はbase対照で既存問題と確定し、R9は既存syncの説明論点。両件を対応しないとし制限をPR説明へ記録 |
| PR全体 | 指摘0。baseからの全差分・全変更ファイル・本Specを読了 | 未確認事項を解消したとは扱わない |
| 検証の検出力 | 指摘0。3ケースのREDの理由と18件GREEN、復旧4ケースのassertionを照合 | 案内の意味は手動読解と区別して記録 |

反証担当の初回dispatchはscope/template不足、次のdispatchはGit差分未提供で実差分レビュー未着手となった。controllerがfilled upstream templateと差分snapshotを提供してから実レビューを1回実施した。2回目の自己レビューは行っていない。自己レビュー後のコード修正はなし。R8は今回直した条件の再発ではなくPR以前の別原因の問題なので、設計見直しのきっかけには該当しない。

各担当が判断外に置いた事項もcontrollerで確認した。独立ff復旧は手順7で使わず対象外、syncの挙動変更は既存仕様を維持、全手順のroot再設計は今回の同条件表を超えるため行わない、既存失敗gateの全状態mutationと任意ignored追加は変更要件外、world同期・fork/dotnet・LLM eval・LSPは上記の未実施/未確認として記録する。恒久シェルの論点はR6に含む。

## 所要時間

- controllerセッション開始: 2026-10-06T08:48:42.694Z。公開前の最終検証完了は09:34:58Z（46分15秒）。最終成果提出までの所要時間は作業報告で示す。
- 調査・全入力/HEAD/context・隔離再現: 開始〜08:57:29（約9分）。初期調査sp-reconを含む。
- Spec設計・実装委譲準備: 08:57:29〜08:59:48（2分19秒）。
- 実装担当: 08:59:48〜09:14:26、878秒。準備107秒、RED54秒、修正/GREEN4秒、関連pytest60秒、shell130秒、layout2秒、skills98秒、全pytest147秒、復旧確認10秒。残りは読解・報告。
- レビューパケット整備・ログ照合: 09:14:26〜09:18:29（4分3秒）。context不足による未着手のdispatchを含む。
- 自己レビュー: 反証09:18:29〜09:23:29（300秒）、全体09:23:50〜09:27:16（206秒）、検出力09:27:27〜09:30:23（176秒）。
- 自己レビューの分類・base対照・記録/公開準備: 09:30:23以降。
