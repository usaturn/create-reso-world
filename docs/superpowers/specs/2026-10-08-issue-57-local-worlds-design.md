# Issue #57: ワールド固有コード・生成物を原則Git管理外にし、制作環境の管理と分離する 設計

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象: Issue #57「ワールド固有コード・生成物を原則Git管理外にし、制作環境の管理と分離する」
- 基準: `main` の `f3bc010`（PR #54 のマージ後）
- 経路: brainstorming の architectural 経路
- 状態: draft（内容の明示承認はまだ無い）
- 実行許可: 2026-10-08 に利用者が「#57 に対応せよ。途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」と指示した。この指示を、この Spec の推奨案で Plan の作成・実装・検証・push・PR の作成まで止まらずに進める許可として扱う。内容の確認は PR で受ける。マージは指示に含まない
- 関連 Plan: `docs/superpowers/plans/2026-10-08-issue-57-local-worlds.md`
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
| F-7 | `git rm --cached` を実行した checkout では実ファイルが残るが、追跡解除コミットを未コミット変更のある別 checkout に取り込むと git は「local changes would be overwritten」で merge を止める。変更を破棄・コミット・退避するか、先に同じ追跡解除をローカルで済ませる必要がある |
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
- 追跡解除コミットを別 checkout へ取り込む前に、その checkout の対象ディレクトリの変更状態を確かめる。未コミット変更がある場合は、変更をコミット・退避・破棄してから取り込むか、取り込み前に同じ `git rm -r --cached` をローカルで済ませる（F-7）
- `git rm --cached` は実ファイルを消さないが、管理外のファイルは Git で復元できず `git clean -fdx` 等で消えることを文書に明記する
- Git 履歴からの容量削減は本 Issue の対象外である

## 6. 対象外

- 実ファイルの削除、既存ワールドの作り直し、Resonite への変更・再適用
- Git 履歴の書き換え、Git LFS への移行
- 専用リポジトリの自動作成・clone・push・サブモジュール化
- ResoLoop 上流・fork の実装変更や同梱スキルの仕様変更
- 未完了のワールド受入確認を完了とみなすこと
