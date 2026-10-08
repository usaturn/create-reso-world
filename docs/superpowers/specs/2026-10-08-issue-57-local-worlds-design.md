# Issue #57: ワールド固有コード・生成物を原則Git管理外にし、制作環境の管理と分離する 設計

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象: Issue #57「ワールド固有コード・生成物を原則Git管理外にし、制作環境の管理と分離する」
- 基準: `main` の `f3bc010`（PR #54 のマージ後）
- 経路: brainstorming の architectural 経路
- 状態: completed（実行許可に基づき実装・検証済み。内容の承認は PR #58 のレビューで受ける）
- 実行許可: 2026-10-08 に利用者が「#57 に対応せよ。途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」と指示した。この指示を、この Spec の推奨案で Plan の作成・実装・検証・push・PR の作成まで止まらずに進める許可として扱う。内容の確認は PR で受ける。マージは指示に含まない
- 関連 Plan: `docs/superpowers/plans/2026-10-08-issue-57-local-worlds.md`
- 関連 PR: https://github.com/usaturn/create-reso-world/pull/58
- 検証: `bash .devcontainer/run-tests.bash` PASS（28 本）、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills` PASS（475 件）、`git diff --check` clean
- 作成: 2026-10-08

## 1. 目的と前提

`MyResoniteProject/`、`akichi/`、`slum02/`、`slum03/` の 4 ディレクトリ全体を Git の管理外にし、ワールド制作を本リポジトリの Git 運用から切り離す。本リポジトリは制作環境・共通ツール・共有スキル・雛形の管理に専念する。Issue #57 の管理方針・対応範囲・安全条件を前提とする。

- 追跡解除は `git rm --cached` 系で行い、実ファイル・未コミット変更・未追跡ファイルは消さない
- 新しいワールドも既定で Git の管理外になる。4 ディレクトリだけを個別除外して新規ワールドが追跡対象に戻る運用にはしない
- 継続的な履歴管理が要るワールドは、利用者が明示的に専用リポジトリを作る。本リポジトリへの再追加・サブモジュール化は既定の運用としない
- 「管理しない」は制作中ファイルの即削除や、安全条件（所有範囲・有料操作・外部送信・Resonite 適用の承認）の省略を意味しない

## 2. 調べた事実

| # | 事実 |
| --- | --- |
| F-1 | 4 プロジェクトの追跡ファイルは計 3312 件（MyResoniteProject 164・akichi 528・slum02 387・slum03 2233）。このうち 26 件は同梱スキルの更新差分など未コミット変更を持ち、`MyResoniteProject/.agents/skills/resonite-model-preproduction/` などの未追跡ファイルもある |
| F-2 | `scripts/new-world.sh` は `<root>/<name>` に `resoloop init` し、ルート `.gitignore` で無視される名前は終了コード 2 で拒否する（「git からも check-layout からも見えない」ため）。symlink の行き先は `../../.` 固定で、プロジェクトがルート直下にある前提になっている |
| F-3 | `scripts/check-layout.sh` は `git ls-files` で「`.resoloop.json` を追跡している直下のディレクトリ」をプロジェクトとみなし、必須ファイル・symlink・`.claude/skills` の 1:1 対応を index から検査する。`resoloop skills sync --check` も同じ一覧で実行する |
| F-4 | `.devcontainer/report-resoloop-skills.bash` も同じ `git ls-files` 定義でプロジェクトを検出する。postCreate から呼ばれ、失敗しても常に 0 で終わる |
| F-5 | ルート `.gitignore` には `MyResoniteProject/content/tokyo-nova/city/export-static/`・`export-refinement/` の個別除外があり、`MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` は `**/.resoloop/**` の規則に対する追跡中の例外として check-layout と test-gitignore に固定値で載っている |
| F-6 | プロジェクトの symlink は 2 系統ある。ルート共有物を指す `.claude/settings.json`・`.pi`・`.agents/sp-*.md`（プロジェクトの深さに依存する）と、プロジェクト内部を指す `.claude/skills/<name> -> ../../.agents/skills/<name>`（深さに依存しない） |
| F-7 | `git rm --cached` は実行した checkout の実ファイルを残すが、別 checkout の更新では変更の無い追跡ファイルも削除される。事前の `git rm --cached` だけでは未追跡削除ガードで停止し、ignore を足して通す通常 checkout は別の ignored ファイルを上書きし得る。自動整理（この変更を取り込んだ後の版）は削除を検出して停止する。取り込む前の checkout にある旧版のスキルや `gitm` は停止しないので、初回移行はそれらより先に、README「追跡解除コミットを取り込む」の、Git の共通ディレクトリ配下への保全・復帰で行う |
| F-8 | CI（`.github/workflows/ci.yml`）はパブリックで稼働しており、`check-layout.sh` と `.devcontainer/run-tests.bash` を新規 clone（ローカルプロジェクト無し）で実行する。検査はローカルプロジェクトの存在に依存できない |

## 3. 検討した案

- **A（推奨）: 専用の作業領域 `worlds/` を新設し、既存4ディレクトリはルートに残す**。新規ワールドは `worlds/<name>` に作り、`/worlds/` を ignore する。既存4ディレクトリは `/MyResoniteProject/` など個別に ignore して追跡を外す。プロジェクト検出は「`worlds/` の直下 + 移行済み4名」という明示した作業領域だけを走査する。既存の実ファイル・symlink・エージェントの cwd 運用を一切動かさずに済み、新規作成は深さ 2 の symlink に対応させるだけでよい
- **B: 既存4ディレクトリを `worlds/` へ移動する**。検出規則が `worlds/*/` の 1 種で済むが、`.pi` などルートを指す symlink の深さが変わり全リンクの張り直しが要る。`new-world.sh --apply` は行き先違いを conflict として報告して直さないため、移行は手作業になる。利用者の進行中作業や cwd の前提も壊れる。Issue は移動を必須としないため採用しない
- **C: ルート直下のまま、新規ワールドも個別に ignore 規則を足す**。作成のたびに `.gitignore` を自動編集することになり、「任意の除外ディレクトリへの書き込みを許可する変更にはしない」に反しやすい。検出対象の境界も曖昧になる。採用しない

## 4. 設計判断

### 4.1 管理外の範囲と作業領域（`.gitignore`）

- **D-1**: ルート `.gitignore` に `/MyResoniteProject/`、`/akichi/`、`/slum02/`、`/slum03/`、`/worlds/` を追加する。`/worlds/` が今後のワールドの作る場所である
- **D-2**: `MyResoniteProject/content/tokyo-nova/` の個別除外と、`pipeline.json` の追跡例外（check-layout の許可リストと test-gitignore の固定値）は、ディレクトリ全体の除外に吸収されるため削除する
- **D-3**: `**/.resoloop/**`、`**/flux/build/`、`*.brson` などの汎用規則は残す。ワールドが誤って別の場所へ追跡されても state・生成物が紛れ込まない防護として意味を持つ
- **D-4**: 既存4ディレクトリの追跡解除は `git rm -r --cached` で行い、`.gitignore` 更新と同じコミットにする。worktree の実ファイルは残り、`git status` も clean に保たれる

### 4.2 ローカルプロジェクトの定義と検出

- **D-5**: ローカルプロジェクトとは、作業領域の直下にあって `.resoloop.json` を持つディレクトリ。作業領域は `worlds/` と移行済み4名（`MyResoniteProject`・`akichi`・`slum02`・`slum03`）の 2 系統とする。`external/`、`private/`、worktree、深い階層は走査しない
- **D-6**: 検出は git の index に依存せずファイルシステムで行う。`check-layout.sh` と `report-resoloop-skills.bash` に同じ定義を持たせ、両者のコメントで相互参照する。利用者が `slum02` を `worlds/slum02` へ手で移しても検出は成立する（`worlds/*/` がカバーするため）

### 4.3 `scripts/new-world.sh`

- **D-7**: 作成先は `$root/worlds/<name>`。`--apply` は `worlds/<name>` とルート直下の `<name>`（移行済み4名の従来位置）の両方を候補にし、片方だけがあればそれを対象にし、両方あれば曖昧さとして拒否する。新規作成では、どちらかの場所に同名があれば「already exists」で拒否する（`external` など追跡中の名前との衝突もこれで防ぐ）
- **D-8**: 「git に無視される名前は拒否する」規則を削除する。`worlds/` への作成は無視されるのが正常である。代わりに予約名 `worlds`（作業領域自身と同名のプロジェクトは作れない）と、`$root/worlds` が実ディレクトリでない場合の拒否を入れる。symlink の `worlds/` は認めない。プロジェクトからルートの共有物へ張る相対 symlink はリンク先基準で解決されるため、symlink 越しでは届かなくなる。別ドライブへ置きたい場合はワールドごと専用リポジトリ化するか bind mount する
- **D-9**: ルートを指す symlink の行き先をプロジェクトの深さで計算する。深さ 1（ルート直下）は従来どおり `../.pi`・`../../.claude/...`、深さ 2（`worlds/<name>`）は `../../.pi`・`../../../.claude/...`。プロジェクト内部の `.claude/skills/<name> -> ../../.agents/skills/<name>` は変えない。名前・パスの検証、既存ファイルとの競合検出、上書き防止の既存動作は維持する

### 4.4 `scripts/check-layout.sh`

- **D-10**: 追跡ファイルの検査（禁止ファイル、追跡 symlink の解決、追跡＋ignore、ルートの `.claude/skills` 1:1、スキル衛生、mount 一致）は index 基準のまま維持する
- **D-11**: 「追跡＋ignore」の既知の例外 `MyResoniteProject/.resoloop/tokyo-nova/pipeline.json` を削除する。追跡解除後は tracked-but-ignored の集合が空になるのが正しい状態である
- **D-12**: 作業領域（`worlds/` と4名）の下に追跡ファイルが無いことを検査する。追跡解除の回帰と `git add -f` による再混入を防ぐ
- **D-13**: ローカルプロジェクトの検査は作業ツリーで行う。必須ファイルの存在（symlink 不可）、`CLAUDE.md` の内容、AGENTS.md の固有節、`.resoloop/.gitignore` の `cache/`、symlink の行き先（深さ対応）、`.claude/skills` の 1:1 対応を、index 基準の検査と同じ規則で確かめる。ローカルプロジェクトが 0 件なら何も検査せず通過する（新規 clone で成立する）
- **D-14**: `resoloop skills sync --check` は検出したローカルプロジェクトで実行する。引数は `./worlds/demo` のようなルート相対パス。SKILL_SYNC_REQUIRED は warn、それ以外の失敗は FAIL の従来の扱いを維持する

### 4.5 `.devcontainer/report-resoloop-skills.bash`

- **D-15**: プロジェクト検出を `git ls-files` からファイルシステム走査（D-5・D-6 と同じ定義）に変える。git の有無や追跡状態に依存せず、postCreate・新規 clone どちらでも成立する

### 4.6 規約・文書

- **D-16**: `AGENTS.md` と `README.md` を更新する。「プロジェクトをリポジトリで追跡する」前提を「ワールドはローカル作業物で追跡しない」に変え、作る場所（`worlds/`、既存4名の現位置）、`git clean -fdx` で消えること、専用リポジトリを選ぶ条件と相対 symlink を持ち出せない注意を書く。`.devcontainer/README.md` のテスト実行例と report-resoloop-skills の説明も合わせる
- **D-17**: 共通環境の設計・計画（`docs/superpowers/`）は従来どおり追跡・コミットする。ワールドの制作記録はローカルに留められる。確定済みの過去の Spec・Plan は履歴として残し、書き換えも一括削除もしない
- **D-18**: 移行時の注意（別 checkout への取り込み前の保全確認、`git clean -fdx`、専用リポジトリ化の条件）は README の「プロジェクトを作る」付近に記録し、PR 本文にも転記する

### 4.7 テスト

- **D-19**: `test-gitignore.bash` は新しい追跡方針（4名と `worlds/` の全体除外、汎用規則の維持、tracked-but-ignored が空）に合わせる。`test-new-world.bash` は `worlds/<name>` への作成・深さ 2 の symlink・legacy 位置への `--apply`・予約名の拒否を検査する。`test-check-layout.bash` はローカルプロジェクトの検出と検査、作業領域の追跡混入の検出を検査する。`test-report-resoloop-skills.bash` はファイルシステム検出を検査する。いずれも実際の git 判定・作成・検出の挙動を実行して確かめる

## 5. 移行時の安全条件

- 実装は worktree で行い、親 checkout（PARENT_ROOT）の未コミット変更には触れない。PARENT_ROOT 側には26件の同梱スキル更新差分と未追跡ファイルがあり、取り込みの前に保全を確認する必要がある（F-1・F-7）
- 追跡解除コミットを別 checkout へ取り込む前に、その checkout の対象ディレクトリ全体を保全する（F-7）。staged 版を先にローカルコミットへ保存し、未stage変更・未追跡・ignored ファイルを含む5領域（従来4名と `worlds/`）の実ディレクトリを、Git の共通ディレクトリ（`git rev-parse --git-common-dir`）の下に作る一意なディレクトリへ移す。checkout も worktree の削除も触れない場所で、同一ファイルシステムであることは保全先を作る前に検査する。checkout の親は Dev Container では書き込めないため使わない（8章）。取り込み先に5領域配下の追跡ファイルが無いことを検査し、`--no-overwrite-ignore` で更新してからディレクトリを戻す。失敗時は保全先を削除せず、戻す先の不存在を確認して復帰する。具体的なコマンドは README「追跡解除コミットを取り込む」に定義する
- マージ前の checkout にある旧版の `repo-cleanup-after-merge`（エージェントは作業ツリーのスキルを読む）・`gitm`・通常の checkout/merge は、追跡ワールドの削除を止めない。この PR では旧版を変えられないため、初回移行が終わるまでそれらで更新しないことを README と PR 本文に明記する（8.5）
- `git rm --cached` は実ファイルを消さないが、管理外のファイルは Git で復元できず `git clean -fdx` 等で消えることを文書に明記する
- Git 履歴からの容量削減は本 Issue の対象外である

## 6. 対象外

- 実ファイルの削除、既存ワールドの作り直し、Resonite への変更・再適用
- Git 履歴の書き換え、Git LFS への移行
- 専用リポジトリの自動作成・clone・push・サブモジュール化
- ResoLoop 上流・fork の実装変更や同梱スキルの仕様変更
- 未完了のワールド受入確認を完了とみなすこと

## 7. PR #58 レビュー修正（2026-10-08）

- 状態: completed（修正・検証・自己レビューと全指摘の判定完了。初回実装の記録は上記に残す）
- 対象: `usaturn/create-reso-world` PR #58、`feat/issue-57-local-worlds`
- 検証対象 HEAD: `7f4c1affca4b083016357e33be3c64e8f3188a03`
- 実行許可: 利用者が `review-fix-planning` を `#58` で起動した。計画のみの指定は無く、同スキルの完遂に従い、必要な修正・検証・自己レビュー・既存 PR への commit/push・状況投稿を行う。今回は結論1であり、マージしない。
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-57-local-worlds`（既存の clean な PR head worktree を再利用）。PARENT_ROOT: `/workspaces/reso-world`。親のワールド・他worktreeの差分は読まず、編集しない。
- 文書の選択: Issue #57・PR #58・テーマ・文書相互参照を照合し、既存のこの Spec と関連 Plan を更新する。別のレビュー回文書は作らない。

### 7.1 入力と分類

入力は `reviews/#58-feat-issue-57-local-worlds/` 内の全4ファイル。いずれも対象 HEAD は `7f4c1affca4b` で、現行 PR head と一致する。以下の ID はファイルと元 ID を対応させる。重複指摘も落とさず数える。

- C: `claude-opus-5-5.md`
- D: `commandcode-deepseek-deepseek-v4.1-flash.md`
- G: `xai-grok-4.7.md`
- S: `SWE-2-High.md`

**入力14件の分類: 解消済み 0 / 対応する 2 / 対応しない 12。自己レビュー SR-1 を含む最終分類: 解消済み 0 / 対応する 3 / 対応しない 12（計15件）。**

| ID | 分類 | 現行 HEAD の根拠と判断 |
| --- | --- | --- |
| C-M-1 | 対応する | README の事前 `git rm --cached` 手順は実行すると未追跡削除ガードで停止し、コミット・stash だけで更新すると追跡ワールドが消える。公式の別 checkout 取り込みで到達する実ファイル消失と誤った保全手順（分類(a)(b)）。一時Gitで再現。 |
| C-L-1 | 対応しない | `.gitignore:33` の手移動では相対リンクが切れるが、検査・`--apply` は安全に停止する。Spec 3章案Bは手作業の張り直しを前提に非採用。自動移設の新仕様は追加しない。 |
| C-L-2 | 対応しない | ワールド制作の worktree の是非は規約の運用論点。`AGENTS.md`「プロジェクト運用」と Issue #57 はワールド制作に branch/worktree/commit/PR を要求しない。文書用 worktree と直接制作を混同する変更は行わない。 |
| C-I-1 | 対応しない | F-8 の CI 公開稼働という記述は誤りだが、停止方針は `AGENTS.md` が定義し、新規 clone に依存しない設計結論とローカル検証は変わらない。情報記録の訂正だけを対応にしない。 |
| D-M-1 | 対応する | cleanup 手順7の clean 確認と `--no-overwrite-ignore` は、旧 HEAD で追跡中のファイル削除を防がない。clean な checkout を自動更新すると実ワールドが消え、未追跡cacheだけ残る（分類(a)）。現行ブロックを実行して再現。 |
| D-L-1 | 対応しない | `new-world.sh:233` の既存lockへの案内は不正確だが、雛形適用の結果は正常。案内文だけの不正確さ。 |
| D-L-2 | 対応しない | C-L-1と同じ手移動時のリンク張り直し。既存位置を保持する推奨運用は正常。 |
| D-I-1 | 対応しない | 初回の `completed` と内容承認の区別は状態記録・運用の論点。実行許可と検証の事実は別に記録され、今回の選別と実行を止める根拠にしない。 |
| D-U-1 | 対応しない | 作業ツリーglobで未追跡ロールを検査する挙動は実在するが、公式導入はユーザースコープのパッケージ内に置きroot `.agents/`へロールを生成しない（`install_beforehand.bash` と `setup_pi_superagents.zsh`）。手動追加時も `--apply` が同じglobでリンクを補える。公式経路の致命的欠陥でない。 |
| G-L-1 | 対応しない | 改行名は行区切り列挙から漏れるが、公式の `new-world.sh` は `name_re` で拒否する。任意の外部名対応を追加しない。 |
| S-L-1 | 対応しない | 任意名のルート直下への `--apply` は可能だが、作業領域は D-5 の5経路に意図的に限定する。利用者が別位置へ追跡する場合まで保証を拡張しない。 |
| S-I-1 | 対応しない | D-L-1と同じ既存lockへの案内。実処理の結果に影響しない。 |
| S-I-2 | 対応しない | 非プロジェクトの同名エントリで `use --apply` の案内が不適切でも、実行は書込み前に拒否する。上書き・誤対象操作は起こらない。 |
| S-I-3 | 対応しない | C-I-1と同じ F-8 の記録。停止方針を変更したり、CI を有効化したりしない。 |
| SR-1（自己レビュー・反証） | 対応する | 今回のREADME修正は従来4領域だけを保全し、cleanupが案内する5つ目の `worlds/` を取り込むと追跡ファイルを削除した。cleanな `worlds/source` の追跡解除でexit0かつ実体消失を一時Gitで再現（分類(a)）。この回の保全条件の再発として設計を見直し、5領域を共通の配列で検査・移動・復帰するよう修正。 |

変更された15ファイルは全員の分担で全文を読んだ。スクリプト3本・変更テスト4本・規約/README・環境文書・starship・Meshy文書・Spec/Planを含む。呼出元、共通の検出/深さ判定、cleanup関連テストと導入設定も確認した。削除3312件は全パス・削除種別を検査し、すべて4ワールド配下で他の削除は0件。追跡解除のみのワールドデータ・コードの各削除blobの全文は読まず、個別ワールドの挙動はレビュー対象に含めない。

### 7.2 守る条件と設計

**守る条件:** 追跡解除を含む更新で、制作中のワールドの実ファイル・未コミット内容・未追跡/ignoredデータ・リンクを、保全確認なしに削除または上書きしない。

C-M-1/D-M-1は同じ条件の異なる入口である。`7f4c1af` は初回レビューより前の自己修正で、既存 Spec/PRレビュー履歴に以前の致命的指摘への対応記録は無い。したがって設計見直しのきっかけ1/2は該当しない。ただし入口を一括して確認し、次の選択肢を比較した。

| 案 | 判断 |
| --- | --- |
| READMEの `git rm --cached` にローカルignoreを足す点の修正 | 不採用。`--no-overwrite-ignore` では依然拒否され、通常checkoutで通すと他のignoredファイルの上書き保護を失う。自動整理経路も残る。 |
| 自動更新の前後でワールドをバックアップ・復元する共通helper | 不採用。容量・保存先・部分失敗・共有リンクの復旧まで自動整理に持ち込み、利用者所有のデータを無断で移動する。 |
| 自動整理の保証を狭め、追跡削除をread-onlyで検出して拒否。明示的な初回移行は全ディレクトリの外部保全で行う | **採用。** 通常更新は従来どおり。clean/no-overwriteだけでは守れない削除を事前に遮断し、移行の判断と実データ移動は利用者が行う。 |

PR説明には、自動移行しないこと、手移動で相対リンクの張り直しが要ること、公式の作業領域・名前制約を既知の制限として記す。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| 保全なしに追跡ワールドを消さない | cleanup手順7から手順8のcheckout/branch削除 | 修正する | 実ブロック実行。5領域の削除、rename、diff取得失敗で状態全体が一致し後続削除が呼ばれない。 |
| 同上 | cleanupの通常の追加/変更・ignored衝突・dirty/lock失敗 | 既に満たす。削除だけ新しいゲートを追加し既存条件は維持 | 既存25ケースと削除以外の変更1ケース。 |
| 同上 | READMEの別checkout取り込み | 修正する | 記載したbashブロックを一時Gitで実行。clean/未stage変更/保存済staged版/一部ディレクトリ不在で実体を保持する。 |
| 同上 | READMEのstaged未保存・取り込み先に追跡ワールドが残る入力 | 修正する | 退避作成/移動前に拒否。HEAD/index/実体が変わらない。 |
| 同上 | READMEのignored衝突によるcheckout失敗 | 修正する | `--no-overwrite-ignore` の拒否後に退避を戻し、私有ファイル/HEAD/index/実体の一致を確認。 |
| 同上 | このSpec F-7/安全条件、関連Plan Task5、PR説明 | 修正する | 誤った `rm --cached` 単独/コミット・stashだけの保証を保全手順への参照に置き換え、差分を確認。文面を固定するテストは追加しない。 |
| 同上 | 実装checkoutでの初回 `git rm --cached` | 既に満たす。実データを削除しない操作 | HEADの追跡解除範囲を検査。今回親checkoutで実行しない。 |
| 同上 | forkのcleanup更新 | 対象外。既存方針で手順7を実行しない | fork運用節の非変更を確認。 |
| 同上 | ワールドの手動移設・専用repo作成・利用者の任意Git操作 | 対象外。利用者の明示操作であり、PRは自動移行を保証しない | PRの既知の制限に条件を記載。 |

#### 自己レビューでの再発を受けた設計の見直し（SR-1）

きっかけ3「自己レビューでの再発」に該当する。初回の今回修正では、自動ゲートが守る5領域からではなく、元レビューの従来4領域からREADMEの手動経路を設計したため、案内先に `worlds/` が漏れた。保全条件を、cleanupで拒否した削除の案内先・移行のすべての入力状態・停止位置まで含む性質として定義し直した。

- **条件:** 自動更新は5領域の追跡削除を一切実行しない。案内先の手動更新は、同じ5領域が取り込み先で追跡されていないことを確認し、存在する全ディレクトリがcheckout外に移った場合だけcheckoutする。復帰では元の場所に既存エントリが無い場合だけ戻す。拒否・部分I/O失敗でも保全先/元の場所のデータを消さない。
- **点の修正を続ける案:** `worlds/` の削除だけ別のifで拒否する案。手動案内と復帰の領域集合が再び食い違う構造が残るため不採用。
- **条件を一か所で保つ案（採用）:** READMEブロックの `dirs=(MyResoniteProject akichi slum02 slum03 worlds)` 一つを、取り込み先検査・staged検査・型/デバイス検査・退避・復帰の全段で使用する。checkout前に対象全体が退避済みとなり、Gitが消せるワールド実体を作業ツリーからなくす。cleanupは同じ5領域を検査してこの手順だけを案内する。
- **保証をさらに狭める案:** `worlds/` が存在するだけで初回移行を拒否する案。管理外の通常の新規ワールドも不要に止めるため不採用。取り込み先に5領域の追跡ファイルが残る場合は拒否する、という既存の必要な制限は維持する。

表を保全の仕組み全体から作り直した。Git refsを動かすのはcheckoutだけ、実データを動かすのは退避/復帰のmvだけで、その他の停止位置はread-only検査または保全先への記録である。

| 状態・停止位置/経路 | 変更前の挙動 | 判定 | 確かめる assertion・方法 |
| --- | --- | --- | --- |
| cleanupのstatus失敗/dirty | checkout前に拒否 | 既に満たす | 既存テストでHEAD・refs・実体保持。 |
| cleanupの削除query失敗 | 初回HEADではcheckoutへ進む | 修正する | diffだけ異常、全状態一致とstatus→diffだけのコマンドログ。 |
| cleanupの5領域削除/R100 rename | 初回HEADでは実体が削除される | 修正する | 各領域+renameの6負例で全状態snapshot一致、ガード無効化では6件とも不一致。 |
| cleanupの削除以外/ignored衝突/lock失敗 | 通常の更新/拒否 | 既に満たす | 既存/追加の実ブロック実行テスト。通常変更は成功、拒否では無損失。 |
| 手動の取り込み先に5領域trackedが残る | 今回初版ではworldsを検査しない | 修正する | akichiとworlds各1異常でexit非0、HEAD/index/実体一致。 |
| 手動のstaged未保存 | 保存の案内で拒否 | 既に満たす | 移動前の拒否、HEAD/index/実体一致。保存済committed版は旧HEADから取出せる。 |
| 手動の型/同一FS検査 | 従来4領域だけ検査 | 修正する | symlink1件、device不一致1件を別々に拒否。退避前の全実体保持。 |
| 手動の退避mv前/途中 | 従来4領域だけ移動 | 修正する | 共通配列の全領域を移す。I/O失敗なら既に移動した分は保全先、未移動分は元の場所に保持し停止。force/上書き/削除なし。 |
| 手動のcheckout成功 | worlds tracked実体が残り削除される | 修正する | clean/未stage変更/保存済stage/一部不在/worlds削除/worldsのみの6ケースで全実体・リンク・refsの保持。 |
| 手動のcheckout失敗 | 退避対象だけ戻す | 修正する | ignored衝突では5領域を戻しHEAD/index/私有ファイルの一致。 |
| 手動の復帰先が存在/I/O失敗 | データを保全先に残し停止 | 既に満たす | `-e/-L`検査を全5領域に適用。mv前の存在確認・set-e・保全先を消さない分岐を静的確認。障害注入は未実施。 |
| Spec/Plan/PR本文/cleanup案内 | 4領域を保全する手順へ案内 | 修正する | READMEの共通配列と5領域保証への参照をそろえ差分確認。 |
| 同時制作/refs変更、任意Git、fork更新 | 本移行とは別の条件 | 対象外 | 制作/refs停止の前提、任意操作は保証外、forkはcheckoutを実行しない。 |

この見直しは自己レビュー後に実施したため、再レビューしていない。下記の最終検証だけをやり直す。

### 7.3 失敗時の扱いと検証

- 自動整理の負例はcleanかつ正しいremoteを持ち、異常は削除1件（5領域各1件）、rename1件、またはdiff取得失敗1件だけ。ワールドのsource/symlink/cache、mode、hardlinkの相手、index内容/mode、exclude、HEAD、ローカルrefs、reflogを前後snapshotで比較する。期待値は実行前から取得。statusが更新するindexのinode/時刻と読取りのatimeはデータ保証に含めない。
- read-only status/diffのあとにだけcheckoutを許す。diff失敗の外部コマンドログはstatus→diffのみで、checkout/branch削除は呼ばれない。
- 削除ガードだけを無効化した対照を修正内容のコピーを置いた隔離worktreeで実行し、5領域とrenameの全6負例が状態snapshotの差で失敗した。修正用worktreeのガードは外していない。
- README手順は5領域を一つの配列で定義し、Gitツリー、staged版、保存先の型/同一ファイルシステムを移動前に検査する。staged版は事前にローカルコミットで保存する。staged版が残る場合は移動せず拒否する。
- 移動途中のI/O失敗は自動ロールバックしない。移動済みの全データは一意な保全先に残し、未移動分は元の位置に残す。checkoutに失敗したときは戻す先の不存在を確かめて復帰し、失敗コードを保持する。復帰先が存在する/I/Oに失敗する場合は保全先を残して停止する。保全先の削除、上書き、force/clean/resetでの回避は行わない。
- 自己レビュー前はREADMEブロックの一時Git7ケースが成功4件・安全拒否3件だったが、worldsを含まず漏れがあった。SR-1を再現後、最終ブロックを12ケースで実行: clean、未stage変更、staged未保存拒否、staged版を事前コミット済み＋未stage変更、一部ディレクトリ不在、ignored衝突拒否、akichiにtarget trackedが残る拒否、worldsの追跡解除、worldsだけ存在、worldsにtarget trackedが残る拒否、領域のsymlink拒否、device不一致拒否。成功6件・安全な拒否6件。全ケースで5領域のバイト列/mode/symlink文字列/inode/hardlink数とローカルbranchを保持し、拒否時はHEAD/indexも一致した。旧HEADの保存と事前コミット版の取出しも確認した。
- 一時検証は `mktemp` が返す `/tmp/review-fix-planning.<suffix>/` 以下に閉じ込め、隔離worktreeを `worktree remove --force` で外してから親を削除済み。実ワールドの更新・移動は未実施。

### 7.4 実装・検証タスク

- [x] 入力全件・PR/HEAD/context・既存文書の照合。
- [x] コミット済み変更・関連処理の調査と一時Gitでの再現。
- [x] TDDでcleanupの削除ゲートと実行テスト8ケースを追加。初回RED7失敗→関連GREEN33成功。snapshot調整後の旧版対照でも7失敗。
- [x] README保全手順、Spec F-7/安全条件、Planの同じ誤記を修正。文書だけの文言照合テストは追加しない。
- [x] 削除ガード無効化の対照6失敗、README手順7ケースの成功/安全拒否、隔離worktreeのteardown。
- [x] 自己レビュー後の最終検証（`run-tests.bash` 28本 / `check-layout.sh` PASS / `uv run pytest tests/skills .agents/skills` 483件）。
- [x] 自己レビュー1回（反証・PR全体・検証の検出力）。SR-1は対応する。他seatからの既報言及は同一指摘として扱う。
- [x] SR-1の再現と設計見直し、README最終12ケース検証。自己レビュー後の修正は再レビューしない。
- [x] 最後の検証・件数・参照先・保証の照合。公開前の実装作業は完了。結論1としてこのSpecを1回コミットし、既存headへのpush・状況投稿の結果はPRコメントと完了報告に記録する。

**テストの要否:** cleanupのbashブロックは実行して確かめる安全ゲートなので回帰テストを追加する。README/Spec/Planは文面を固定するテストを追加せず、記載コマンドの隔離実行、参照確認、差分で代える。

### 7.5 自己レビュー・結果・所要時間

結論は **1 修正してpush**。push/投稿の成否はこのSpecへ追記せず、PR状況コメントと完了報告に記録する。

- 自己レビューは3観点を別々の読み取り専用 `sp-review` に直列委譲した1回。反証が SR-1 を報告。PR全体seatは追加の致命的指摘なし、検出力seatは同じ SR-1 の検証を推奨し追加指摘なし。SR-1 を設計見直しで修正し、再レビューせず最終検証を実行した。
- 見送った範囲: 同時制作/refs変更は停止前提に反する。I/O失敗の完全自動ロールバックは保証しない。fork更新は手順7を実行しない。手移設時のリンク自動修復、改行名、任意のルート直下プロジェクト、lock案内は入力指摘の対応しない判断を維持する。
- 最終検証: `bash .devcontainer/run-tests.bash` **28本成功**、`bash scripts/check-layout.sh` **PASS**（4プロジェクトに同梱スキル更新のwarnのみ。自動同期はしない）、`uv run pytest tests/skills .agents/skills` **483件成功**（自己レビュー後の実行は93.27秒）、`git diff --check` clean。変更Pythonへのactive LSP診断は1ファイル確認・0件。
- テスト採用: 追加8ケースは実bash/Gitの処理・安全境界を実行するもので、文面文字列を固定する追加テストは無い。READMEの検証は保存するテストを増やさず、記載ブロックそのものを隔離実行した。
- 未確認の範囲: 実ワールドの移行、削除3312blobの個別全文・個別ワールドの動作、移動/復帰のI/O失敗注入、新規LLM文言microtest。自己レビューで指摘が無かったことを、これらの確認済みの根拠にはしない。失敗時のデータ保持は分岐と実コマンドの検査で確認し、実ワールド操作は利用者の保全確認を伴う別作業とする。
- 所要時間: controller着手17:02 JST〜自己レビュー後の最終検証完了18:22 JST、約80分。調査/照合・再現約16分、実装担当約16分、README/Specと検証約14分、自己レビュー3観点約25分、SR-1の再現/設計見直し/再検証約9分。実装担当は実測15分37秒（RED/fixture3分39秒、実装/診断/GREEN3分26秒、関連/全体/静的検証/報告8分32秒）。公開操作の時間は完了報告に含める。

## 8. PR #58 レビュー修正 2 回目（2026-10-08）

- 状態: completed（修正・検証・自己レビューと全指摘の判定完了。結論 1）
- 対象: `usaturn/create-reso-world` PR #58、`feat/issue-57-local-worlds`
- 検証対象 HEAD: `5c8b4032f7301176cbf4631a8b2b219d7671fa12`
- 実行許可: 利用者が `review-fix-planning` を `#58` で起動した。計画のみの指定は無く、同スキルの完遂（修正・検証・自己レビュー・既存 PR への commit/push・状況投稿）として扱う。
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-57-local-worlds`（clean で PR head と一致する既存 worktree を再利用）。PARENT_ROOT: `/workspaces/reso-world`。親のワールドと他 worktree の差分は読まず、編集しない。
- 文書の選択: Issue #57・PR #58・テーマで照合した現行の Spec はこの 1 件だけなので、7 章と同じくこの Spec を更新する。

### 8.1 入力と分類

入力は `reviews/#58-feat-issue-57-local-worlds/` の全 6 ファイル。対象 HEAD は `7f4c1affca4b`（D・G）と `5c8b4032f730`（C・S・DS・GR）で、どちらも現行 PR head の祖先である。C・S は両方の HEAD を見た更新版。7 章の ID を引き継ぎ、新しいファイルを DS（`deepseek-deepseek-v4.1-flash.md`）、GR（`grok-4.7.md`）とする。未検証候補（U）も 1 件として数える。

**入力 24 件の分類: 解消済み 3 / 対応する 1 / 対応しない 20。自己レビューの SR2-1〜3 を含む最終分類: 解消済み 3 / 対応する 2 / 対応しない 22（計 27 件）。**

| ID | 分類 | 現行 HEAD の根拠と判断 |
| --- | --- | --- |
| C-M-1 | 解消済み | `5c8b403` で README の事前 `git rm --cached` を保全手順に置き換え、cleanup 手順 7 に削除ガードを入れた（`SKILL.md:183-191`、`test_detached_update.py` の 5 領域・rename・diff 失敗の負例）。 |
| D-M-1 | 解消済み | 同じ削除ガードで、cleanup 手順 7 は 5 領域の追跡削除を checkout 前に止める。 |
| GR-U-2 | 解消済み | 追跡側の実行コードで world 4 名を参照するものは無い（`git grep` の一致はテストの fixture だけ）。削除 blob を入力に要求するツールは無い。 |
| C-M-2 | 対応する | README の保全先 `mktemp -d "$(dirname "$root")/..."` は、Dev Container の main checkout（`/workspaces/reso-world`）では親 `/workspaces` が root 所有で書けず（別デバイスでもある）、必ず `mktemp` で止まる。cleanup 手順 7 がこの手順だけを案内するので、main checkout を `origin/main` へ追従させる主要な処理が手順どおりでは完了しない（分類 (a)、再現済み）。 |
| C-L-1 | 対応しない | 7 章と同じ。手移動で相対リンクは切れるが、`check-layout.sh` が FAIL、`--apply` が変更せずに停止し、PR の既知の制限に張り直しを記載済み。 |
| C-L-2 | 対応しない | 7 章と同じ運用論点。`AGENTS.md`「プロジェクト運用」がワールド作業に branch・commit・PR を求めない。 |
| C-L-3 | 対応しない | 対話 zsh に貼ると `set -e` と `exit` で端末が閉じる（再現済み）。拒否と途中失敗ではデータは元の場所か保全先に残り、保全先の場所は README 手順 3 に書く。表示が消えるだけで誤った結果にはならない。 |
| C-I-1 | 対応しない | 7 章と同じ。F-8 の CI の記述は誤りだが設計の結論は変わらない。 |
| S-L-1 | 対応しない | 境界は変わっていない。作業領域を D-5 の 5 経路に限る判断を 7 章と PR の既知の制限に記載済み（S は解消とした）。 |
| S-I-1 | 対応しない | 7 章 D-L-1 と同じ案内文の不正確さ。 |
| S-I-2 | 対応しない | 7 章と同じ。書き込む前に拒否する。 |
| S-I-3 | 対応しない | C-I-1 と同じ。 |
| S-I-4 | 対応しない | 型・デバイス・復帰先の拒否が理由を出さない。どれも安全側の停止で、データは元の場所か保全先に残る。 |
| DS-M-1 | 対応しない | ff マージで追跡ワールドが消えるのは利用者が始めた merge 自体の挙動で、README と PR 本文が「通常の checkout/merge は追跡ワールドを削除する」と注意している。`stale-git-lock-recovery` は元の操作を再実行するだけで、cleanup 手順 7 から来た場合は手順 7（削除ガード）に戻る。`ff_merge_keep_untracked.sh` は取り込み先が追加するパスの未追跡ファイルを守る helper で、手順 7 では使わない。自動の更新経路は守られている。 |
| DS-I-1 | 対応しない | `rst-writer` の例が `slum02/` のまま。従来位置も有効で、誤った結果にならない。 |
| DS-I-2 | 対応しない | `docs/worlds/` の not-ignored の固定値が外れた。現状は ignore されず、混入しても `check_tracked_ignored` が FAIL にする。 |
| GR-M-1 | 対応しない | ブロックをサブディレクトリから実行すると、pathspec が cwd 相対なので追跡残存・staged の検査が働かない（再現済み）。README は「対象 checkout のルートで」実行するよう求めている。外れた使い方でも、復帰の段が既存エントリを上書きせずに止まり、データは保全先に残る（GR-U-1 で確認）。PR の既知の制限に条件を書き足す。 |
| GR-L-1 | 対応しない | S-I-4 と同じ。 |
| GR-U-1 | 対応しない | サブディレクトリから、取り込み先がまだ違う版の `akichi` を追跡している状態で実行した。HEAD は取り込み先に進み、ルートには追跡版が置かれたが、復帰は exit 1 で止まり、利用者の本文と未追跡ファイルは保全先にバイト単位で残った。GR-M-1 と同じ扱い。 |
| D-L-1 | 対応しない | 7 章と同じ。 |
| D-L-2 | 対応しない | 7 章と同じ（C-L-1 と同じ論点）。 |
| D-I-1 | 対応しない | 7 章と同じ状態記録の論点。 |
| D-U-1 | 対応しない | 7 章と同じ。公式の導入はルートの `.agents/` にロールを作らない。 |
| G-L-1 | 対応しない | 7 章と同じ。公式の `new-world.sh` は改行を含む名前を拒否する。 |
| SR2-1（自己レビュー・反証） | 対応しない | リポジトリ外の FS に作った worktree や、`.git` が別 FS への symlink の構成では、旧ブロックで成功していた移行が、状態を変える前の拒否に変わる。安全側の停止で、実環境の main と `.worktrees/*` は共通ディレクトリと同じデバイスにある。8.2 の表に行を足した。 |
| SR2-2（自己レビュー・反証） | 対応しない | 保全先に元の checkout の記録が無い。データは残り、修正前も `.worktrees/` の保全先は共有だった。 |
| SR2-3（自己レビュー・PR 全体） | 対応する | マージ前の checkout では旧版の `repo-cleanup-after-merge` と `gitm` が追跡ワールドを削除する（再現済み）。D-M-1 と同じ結果で、PR 本文の保証が初回の取り込みで成り立たない（分類 (a)・(b)）。8.5 で設計を見直し、保証を狭めた。 |

PR の変更 17 ファイルを全文または差分で読み、差分外では `stale-git-lock-recovery`（SKILL.md・`ff_merge_keep_untracked.sh`）、`.devcontainer/cleanup-workspace.bash` の削除対象、checkout・merge を行う経路（`git grep`）、`docs/integration.md` の ff マージ手順（PR #2 の完了した移行手順で、現行の経路ではない）を確認した。削除 3312 件は 7 章と同じく全パスが 4 ワールド配下であり、個々の blob の本文は読んでいない。

### 8.2 設計の見直し（C-M-2、きっかけ 2「修正が生んだ回帰」）

C-M-2 の原因は、7 章のレビュー修正コミット `5c8b403` が入れた README ブロックの保全先の行である。スキルのきっかけ 2 に当たるので、点の修正ではなく保全先の仕組みから見直した。

**守る条件:** README の初回移行ブロックは、このリポジトリが前提にする構成（Dev Container の main checkout `/workspaces/reso-world`、`.worktrees/` 配下の linked worktree、通常の clone）で書かれたとおりに実行すると完了する。保全先は、(1) 実行者が書き込め、(2) 5 領域と同じファイルシステムにあり、(3) checkout・`git worktree remove`・prune・gc・`cleanup-workspace.bash` が触れず、(4) 端末の出力を失っても場所が分かる、の 4 つを満たす。満たせない構成では、どの状態も変える前に停止する。

**以前の回で足りなかった理由:** `5c8b403` は「checkout 外」として `dirname "$root"` を選び、検証は親に書き込める `/tmp` 配下の一時 Git だけで行った。bind mount の main checkout と、root 所有の親という実際の配置を経路として列挙していなかった。また、保全先を作ってからデバイスを検査していたため、デバイス不一致の拒否でも空の保全先が残っていた。

**比べた直し方:**

| 案 | 判断 |
| --- | --- |
| 点の修正: 保全先の親を Git の共通ディレクトリ（`git rev-parse --path-format=absolute --git-common-dir`）にし、デバイス検査を保全先の作成より前に移す | **採用。** (1) checkout・fetch に書き込みが要る場所なので書ける、(2) main checkout と `.worktrees/` では作業ツリーと同じ bind mount にある（実環境はどちらもデバイス 2096）、(3) checkout は git dir の未知のディレクトリに触れず、worktree の削除・prune は `.git/worktrees/<name>` だけ、gc は未知のディレクトリを消さず、`cleanup-workspace.bash` は `/tmp` の `pr-review-*`・`review-fix-planning.*` だけを対象にする。(4) 場所を README 手順 2・3 に書く。共通ディレクトリが別のファイルシステムにある構成（`--separate-git-dir` など）は、何も作る前にデバイス検査で止まる。 |
| worktree ごとの git dir（`--absolute-git-dir`） | 不採用。linked worktree では `.git/worktrees/<name>` になり、途中失敗で残した保全先が worktree の削除・prune で消える。 |
| checkout のルート直下（作業ツリー内） | 不採用。`git status` に未追跡として出て cleanup 手順 7 の clean 確認を止め、`git clean -fdx` の対象にもなる。 |
| 手順を追跡するスクリプトにまとめ、テストで固定する | 不採用。旧 HEAD の checkout にはスクリプトが無く、`origin/main` から取り出す手順が増えて、その手順自体が誤りの元になる。移行は checkout ごとに 1 回で、ブロックの隔離実行で確かめられる。 |
| 保証を狭める（保全先を利用者に指定させる、Dev Container の main checkout を対象外にする） | 不採用。ワールドの実データが最も多い main checkout の移行こそが目的で、利用者に場所の判断を押し付けると誤りの元になる。 |

**影響経路（保全先の仕組みから列挙）:**

| 状態・停止位置／経路 | 変更前の挙動 | 判定 | 確かめる assertion・方法 |
| --- | --- | --- | --- |
| Dev Container の main checkout（親が root 所有・別デバイス） | `mktemp` が Permission denied で停止し、移行できない | 修正する | 親を `chmod 555` にした一時 Git で exit 0、HEAD が取り込み先、5 領域とhard link の相手の型・mode・inode・nlink・バイト列が実行前と一致、保全先が共通ディレクトリにあり `before-head` が旧 HEAD。実環境は読み取りだけで、共通ディレクトリ `/workspaces/reso-world/.git` が書き込め、デバイスが 4 ワールドと同じ 2096 であることを確認 |
| `worlds/` だけがある checkout | 同上 | 修正する | 同じ条件で exit 0、データ一致、`git status --short` が空 |
| `.worktrees/` 配下の linked worktree | 親 `.worktrees/` に保全先を作って成功 | 修正する（場所が変わる） | exit 0、データ一致、保全先が main の `.git` にあり `.git/worktrees/<name>` には無い。保全先に置いた印が `worktree remove --force`・`worktree prune`・`gc --prune=now` の後も残る |
| リポジトリ外の FS（`/tmp` など）に作った worktree、`.git` が別 FS への symlink | 親が同じ FS なら成功していた | 対象外（安全側の停止に変わる。自己レビュー SR2-1） | 反証担当が `/tmp` の worktree と `/dev/shm` の `.git` で、修正後は exit 1 で状態不変、修正前は成功を確認。実環境の main と `.worktrees/*` はすべて共通ディレクトリと同じデバイス 2096 |
| 共通ディレクトリが別デバイス | 保全先を作ってから検査し、空の保全先を残して停止 | 修正する（順序） | `stat` を差し替えて共通ディレクトリだけ別デバイスにした負例（他は正常）で exit 1、状態全体（5 領域・hard link の相手・HEAD・index・refs・共通ディレクトリの保全先一覧・親の一覧）が実行前と一致 |
| 取り込み先に追跡が残る・staged 未保存・symlink 領域 | 保全先を作る前に拒否 | 既に満たす | 各 1 異常の負例で exit 1、状態全体が一致、保全先は作られない |
| checkout が ignored の上書きを拒否 | 5 領域を戻して失敗コードで終了 | 既に満たす（保全先の場所だけ変わる） | exit 1、保全先の一覧以外の状態全体が一致、私有ファイルが残り、保全先には `before-head` だけが残る |
| 復帰先が存在・I/O 失敗 | データを保全先に残して停止 | 既に満たす | 復帰の判定（`-e`・`-L`）は変えていない。GR-U-1 の再現で、復帰先が存在すると exit 1 で止まり、データが保全先に残ることを確認 |
| 保全先を残した後の自動整理 | 親に残るので Git の操作は触れない | 既に満たす | 共通ディレクトリでも `worktree remove`・prune・gc が消さないこと（上の linked worktree の行）、cleanup 手順 7 の clean 確認は `.git` の中を見ない、`cleanup-workspace.bash` の対象は `/tmp` だけ（静的確認） |
| 端末を失ったときの保全先の場所 | 実行時の表示だけ | 修正する（文書） | README 手順 2・3 に「Git の共通ディレクトリの `local-worlds-backup.*`」を書き、`git diff` で確認 |
| この Spec の F-7・5 章、PR 本文 | 「checkout 外」「同一FSのcheckout外」と記載 | 修正する（文書） | `git diff` と PR 本文の確認。文面を固定するテストは追加しない |
| ルート以外の cwd（GR-M-1・GR-U-1） | 検査が働かずに進み、復帰で停止 | 対象外（README がルートでの実行を求める。データは保全先に残る） | PR の既知の制限に条件を記載 |
| 対話シェルの終了（C-L-3） | 端末が閉じる | 対象外（データは残り、場所は文書に書く） | — |
| 利用者が始めた checkout・merge、ロック復旧の再実行（DS-M-1） | 追跡ワールドを削除する | 対象外（README と PR 本文が注意、自動経路は手順 7 のガード） | — |

### 8.3 失敗時の検証

- 比べた状態: 5 領域とその外の hard link の相手の型・mode・inode・nlink・サイズ・symlink の行き先・ファイルのバイト列、HEAD、`git ls-files -s`、`git for-each-ref`、共通ディレクトリの `local-worlds-backup.*` の一覧、checkout の親の一覧。期待値は実行前に取った。
- 負例は異常を 1 つだけ入れた: 共通ディレクトリだけ別デバイス、staged 未保存、取り込み先に `akichi` の追跡が残る、`slum02` が symlink。どれも exit 1 で状態全体が一致し、保全先は作られなかった。
- 対照: 修正後のブロックからデバイス検査のループだけを外した版を隔離ディレクトリで実行すると、別デバイスの負例は exit 0 で HEAD と 5 領域が動き、状態の比較で失敗した（負例 1 件中 1 件が失敗）。修正用の worktree ではガードを外していない。
- 修正前のブロックは、親に書き込めない 2 ケース（main checkout 相当・`worlds/` だけ）で `mktemp: Permission denied` の exit 1 になった。

### 8.4 実行した検証

- README ブロックの隔離実行（`mktemp` の `/tmp/review-fix-planning.*` 配下。終了後に削除）: 修正後 8 ケースすべて期待どおり（成功 3、安全な拒否 5）。内訳は 8.2 の表の各行。
- 実環境の読み取り確認: `/workspaces` は `root:root` 755 で書き込めない（デバイス 87、overlay）。`/workspaces/reso-world` とその `.git`・4 ワールドはデバイス 2096（ext4 の bind mount）で、`.git` は書き込める。

### 8.5 自己レビューと設計の見直し（SR2-3、きっかけ 1「同じ守る条件の 2 回目」）

自己レビューの PR 全体の観点で、SR2-3 が見つかった。#58 のマージ後、マージ前の checkout のルートで `repo-cleanup-after-merge` を使うと、エージェントは作業ツリーにある旧版（`f3bc010` の手順 7、削除ガード無し）を読む。その手順 7 は clean な checkout を `origin/main` へ checkout し、追跡ワールドを削除する。一時 Git で再現した結果は次のとおり。

- 旧版の手順 7: exit 0。`akichi/a.txt` と symlink が消え、ignored の `.venv` だけが残った
- 新版の手順 7: exit 1 で停止し、すべて残った
- 同梱のエイリアス `gitm`（`git fetch -p && git checkout origin/main`。`.devcontainer/zshrc.txt:58`、利用者の `~/.zshrc` にもある）: clean な checkout では追跡ワールドを削除し、変更がある checkout では git が拒否した

結果は 7 章で致命的とした D-M-1 と同じで、PR 本文と README が「cleanup は停止する」としている経路で起きる。分類は「対応する」（分類 (a)・(b)）。7 章の守る条件（保全確認なしに追跡ワールドを消さない）と同じ条件で、7 章の表が漏らした隣の経路なので、きっかけ 1 に当たる。

**守る条件:** #58 より前の HEAD にある checkout を #58 以降へ動かすどの経路でも、README の保全手順を経ずに追跡ワールドを消さない。リポジトリが提供する経路（自動整理のスキル、同梱エイリアス、ロック復旧の再実行、文書の手順）も含む。この PR で挙動を変えられない経路では、利用者がその経路を使わずに済むよう、マージ前に読む PR 本文と、移行時に読む README で案内する。

**7 章で足りなかった理由:** 7 章の表は cleanup 手順 7 を「修正する」とし、直した SKILL.md が実行されることを前提にしていた。しかし、#58 を初めて取り込むときに実行されるのは、マージ前の checkout の作業ツリーにある旧版である。`gitm` は「利用者の任意 Git 操作」にまとめており、リポジトリが配る経路として数えていなかった。

**比べた直し方:**

| 案 | 判断 |
| --- | --- |
| 新版の手順 7 のガードをさらに強める（点の修正） | 不採用。初回の取り込みで動くのは旧版なので効かない。 |
| 追跡解除コミット自体で旧ツールの checkout を失敗させる（条件を 1 か所で保つ） | 不採用。git が checkout を拒否するのは、変更のある追跡ファイルか、未追跡・ignored ファイルとの衝突だけである。どの checkout にもある ignored パスへ追跡ファイルを置くような仕掛けは不確実で、配置も壊す。 |
| 削除ガードだけを先行 PR に分けてマージし、各 checkout をその版へ更新してから #58 をマージする | 構造的には最も確実（ガードの版への更新ではワールドは消えない）。ただし第二の PR になるので、このスキルの範囲では行わない。利用者が選べる他の案として状況コメントに残す。 |
| PR の保証を狭める（採用） | 「cleanup は停止する」を「この PR の版の cleanup は停止する」に直す。マージ後は各 checkout を最初に README の手順で移行し、それまで旧版の `repo-cleanup-after-merge`・`gitm`・通常の checkout/merge で更新しないことを、PR 本文の「取り込む側の注意」の先頭、既知の制限、README「追跡解除コミットを取り込む」の冒頭、この Spec の F-7・5 章に書く。 |

**影響経路（checkout を追跡解除コミットの前から後へ動かす経路から列挙）:**

| 経路 | 変更前の挙動 | 判定 | 確かめる assertion・方法 |
| --- | --- | --- | --- |
| 新版の cleanup 手順 7（この PR を取り込んだ後のスキル） | 5 領域の削除・rename・diff 失敗で停止 | 既に満たす | 一時 Git で新版の手順 7 が exit 1 で HEAD とワールドを保つ。7 章の `test_detached_update.py`（変更なし） |
| 旧版の cleanup 手順 7（マージ前の checkout の作業ツリーにあるスキル） | clean な checkout の追跡ワールドを削除 | 修正する（保証を狭め、使わないことを案内） | 一時 Git で旧版が exit 0 で削除することを再現。README・PR 本文・Spec の記載は `git diff` と PR 本文で確認 |
| `gitm` | clean なら削除、変更があれば git が拒否 | 修正する（名指しで案内） | 一時 Git で両方を再現。エイリアス自体は変えない（移行後はワールドが追跡されないので無害。マージ前のコンテナには旧版が残る） |
| 通常の checkout・merge・pull、`stale-git-lock-recovery` の再実行と `ff_merge_keep_untracked.sh`（DS-M-1） | 追跡ワールドを削除 | 既に満たす（PR 本文の注意）。README の冒頭にも明記する | `git diff` |
| README の保全手順 | 8.2 | 修正済み | 8.4 |
| 利用者の親 checkout の現状（`/workspaces/reso-world`、`f3bc010`） | world 配下に 28 件の変更と 8 件の未追跡があるので、旧版の手順 7 は clean 確認で、`gitm` は git の拒否で止まる | 既に満たす（現状に依存する） | `git -C /workspaces/reso-world status --short` が空でないことを読み取りで確認。状態に頼らず、案内で防ぐ |
| cleanup 手順 4・5 の linked worktree 削除 | ignored・未追跡を確かめてから削除する | 既に満たす | 7 章 |
| `pr-review`・`review-fix-planning` が作る新しい worktree | 追跡内容しか持たない | 対象外 | — |
| fork（`external/resoloop`） | 別リポジトリ | 対象外 | — |

コードは変えず、文書で保証を狭めたので、「失敗時の検証」の対照は該当しない。この見直しは自己レビューの後に行ったため、再レビューしていない。

### 8.6 自己レビュー・結果・所要時間

結論は **1 修正して push**。push・投稿の結果はこの Spec に追記せず、PR の状況コメントと完了報告に書く。

- 自己レビューは 1 回。3 観点を別々の読み取り専用サブエージェントに同時に任せた
  - 反証: 致命的な指摘なし。SR2-1・SR2-2（どちらも対応しない）。zsh での実行、`mv` の失敗注入（移動の途中・復帰の途中）、保全先が残った状態での再実行、保全先に触れる処理が無いことも確認した
  - PR 全体: SR2-3（致命的）。8.5 の設計の見直しで直した
  - 検証の検出力: 担当が 19:35 JST 以降応答せず報告が無かった（停止はさせていない）。controller が同じ観点を 1 回だけ自分で見た。移動をコピーに変えて inode を壊した欠陥版で、成功系の比較が失敗することを確認した。デバイス不一致の負例が、デバイス検査の行（`stat` の差し替えは共通ディレクトリだけ）で止まることを `bash -x` で確認した。指摘なし
- 自己レビュー後の修正（SR2-3 の README・Spec・PR 本文）は再レビューしていない。
- 最終検証: `bash .devcontainer/run-tests.bash` **28 本成功**、`bash scripts/check-layout.sh` **PASS**（4 プロジェクトに同梱スキル更新の warn のみ）、`git diff --check` clean。README のブロックは 8.4 の 8 ケースと対照で確認した。`uv run pytest tests/skills .agents/skills` は、今回 Python とスキルを変えていないので実行していない。
- テスト採用: 変更は README と Spec の文書だけなので、保存するテストは追加しない。README のブロックは記載どおりに抜き出して隔離実行した。
- 未確認の範囲: 実環境の main checkout での実際の移行（利用者のワールドを動かすため実行していない）、submodule やワールド内の入れ子の Git がある構成、移行の途中の I/O 失敗の実障害。自己レビューの指摘が少ないことを、これらの確認済みの根拠にはしない。
- 所要時間: 着手 19:13 JST 〜 公開前の記録 19:57 JST、約 44 分。入力・PR・差分の読み込み約 7 分、再現（C-M-2・GR-M-1・C-L-3 ほか）約 4 分、修正と隔離検証約 3 分、検証スイートと GR-U-1・Spec 約 8 分、自己レビュー（担当の実行約 6 分、待機を含む）・SR2-3 の再現と設計の見直し・文書修正・再検証約 15 分、検出力の自己確認と記録約 7 分。
