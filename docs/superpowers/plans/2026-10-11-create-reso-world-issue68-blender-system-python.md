# Issue #68 Blender 起動設定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新規・既存ワールドの雛形で Blender の system-python ラッパーを設定し、uv 経由の NumPy 読み込みを直す。

**Architecture:** 既存の二段階の競合検査・適用に、実行可能ラッパーとキー単位の JSON 編集を加える。設定済みの利用者指定は保存し直さず保持する。JSON は jq で解析し、更新が必要な場合だけ一時ファイル経由で置き換える。

**Tech Stack:** Bash、jq、uv、Blender、ResoLoop。

**Spec:** `docs/superpowers/specs/2026-10-11-create-reso-world-issue68-blender-system-python-design.md`

## 管理・許可

- 文書管理・対象: `usaturn/create-reso-world` Issue #68。
- 基準 HEAD: `edaab067f47bab2ae567462544a86fb272a79674`。
- 状態: draft（文書版の SHA に対する承認は未取得）。
- ユーザーは会話で提示した六点の方針と PR 作成までを承認している。さらに既存テスト失敗を Issue #83 へ分離した後の続行を明示した。本 Plan はその方針内の実行記録であり、設計の変更や追加の作業を許可されたことにはしない。
- 実行方式: controller が記録・統合・実環境検証・push/PR を担当し、実装は sp-implementer、レビューは read-only の sp-review に同期で委譲する。子のモデル指定は pi-superagents のロール設定に従い上書きしない。

## Global Constraints

- `templates/world-project/blender-system-python` に既存の `/usr/bin/blender` 向けラッパーと同じ内容を置く。PATH の `*/.venv/bin` を外し、`VIRTUAL_ENV` を unset して引数をそのまま `exec /usr/bin/blender "$@"` に渡す。
- 新規作成・`--apply` は、`.resoloop/blender-system-python` を通常ファイルとして設置し、実行権限を付ける。未設定の `blenderExecutable` にはこのラッパーの絶対パスを設定する。
- 利用者の別の `blenderExecutable` は変更しない。現在のラッパーを指す場合も JSON を再保存しない。
- 不正 JSON、ラッパーの内容差、symlink や非通常ファイルなどの競合は、一巡目で全件を報告して exit 1 とする。競合が一つでもあれば雛形・JSON・実行権限を変更しない。
- 移動後の古い絶対パスも自動変更しない。保持を案内し、README に手動更新する方法を書く。
- jq が無ければ init や変更前に exit 3 とする。`--no-sync` は uv 不在でも使える。
- JSON は一つの object、キー欠落・null は未設定、string は保持、それ以外の型は競合。他のキーの値と元のファイル権限を維持する。
- ローカルワールド、ResoLoop 本体、Issue #83 の失敗、その他のスキル・規約は変更しない。

## Review Focus

- カスタム値・旧絶対パス・空文字は保持し、JSON のバイト列を変えない。
- wrapper の実行権限を直す予定があっても、別の競合があれば mode を変えない。
- JSON symlink、wrapper symlink、`.resoloop` 親 symlink の外側を変更しない。
- 複数 JSON、object 以外、不正な `blenderExecutable` の型で途中変更を残さない。
- root のパスに空白や引用符がある場合も jq の `--arg` 等で絶対パスを安全に保存する。

---

### Task 1: 雛形と二段階適用を統合し、利用者設定を守る

**Files:**
- Create: `templates/world-project/blender-system-python`
- Modify: `scripts/new-world.sh`
- Modify: `tests/scripts/test-new-world.bash`
- Create: `tests/scripts/test-blender-system-python.bash`
- Modify: `.devcontainer/install_beforehand.bash`（apt の基本パッケージに jq を追加する一箇所のみ）
- Modify: `README.md`（プロジェクト作成節にラッパー・jq 前提・設定保持・移動後の手動更新を説明）

**Interfaces:**
- Consumes: `new-world.sh [--apply] [--no-sync] [--root DIR] <name>`、`parent_ok`、`want_file`、`conflicts` と既存 plan 配列、一巡目では書かず二巡目で適用する既存構造。
- Produces: 実行可能な `.resoloop/blender-system-python` と、有効な `.resoloop.json` の絶対 `blenderExecutable`。CLI と既存の終了コードは維持する。
- shell 内の追加処理: `want_blender_configuration()`（引数なし、proj と conflicts に基づき JSON 更新の要否を記録する）、適用時の JSON 一時ファイル処理と実行権限付与。必要な状態の名前は実装担当が決めてよいが、既存と同じ二段階に収め、外部 helper に分割しない。

**テストの要否:** コードを実行して JSON の入出力・分岐・無変更保証・PATH の扱いを確かめるので必要。文書と apt の一覧だけのためのテストは追加しない。これらは構文・既存テスト・差分で検証する。

- [ ] **Step 1: 失敗する実行テストを追加する**

`test-new-world.bash` のモック init・一時 root を用い、追加テストは実際に new-world.sh を実行する。snapshot に mode を加える。次の値・条件を固定する理由は利用者所有部分と競合時無変更を守るため、とコメントで説明する。

```bash
# new_root/run/expect_exit/snapshot は既存の補助を利用する。
expect_exit 0 'DONE: demo' "$r" --no-sync demo
[ -x "$r/worlds/demo/.resoloop/blender-system-python" ] || fail 'wrapper not executable'
jq -e --arg path "$r/worlds/demo/.resoloop/blender-system-python" \
  '.blenderExecutable == $path' "$r/worlds/demo/.resoloop.json" >/dev/null || fail 'absolute wrapper path'
```

追加するケースと判定:
- 新規、`--apply`、従来位置: wrapper が実行可能で絶対値が設定される。null も補う。他のキー・ファイル権限を保持する。
- 二度目: snapshot が同じ。現在の wrapper 値が設定済みの JSON はバイト列も同じ。
- カスタム、旧絶対パス、空文字: JSON のハッシュが同じで、保持を知らせる。移動したプロジェクトにも旧値を上書きしない。
- 不正 JSON、複数文書、root array、非 string/non-null のキー: exit 1、snapshot が同じ。
- JSON/wrapper/親の symlink、内容差、別ファイルの競合: exit 1、対象とリンク先の snapshot が同じ。実行権限を直す予定の wrapper も mode 不変。
- 内容が同じで非実行の wrapper: 他の競合が無い場合だけ +x。以後の適用は無変更。
- jq 不在: exit 3、init 未実行・既存プロジェクト無変更。uv 不在で `--no-sync` は成功する既存ケースを維持。
- 空白・引用符を含む root の絶対パスも、JSON として読み取った値が期待値に一致。

`test-blender-system-python.bash` は別 Bash プロセス内で元の wrapper を source し、`exec` だけを shell 関数で置き換えて外部起動境界を記録する。PATH に複数の `.venv/bin` と普通の bin を混在させ、残す bin の順序、VIRTUAL_ENV 未設定、`/usr/bin/blender` と空白・空文字を含む引数列、終了コードの引き渡しを検証する。wrapper 本文の文字列照合や別実装への書き換えはしない。

- [ ] **Step 2: RED を確認する**

Run: `bash tests/scripts/test-new-world.bash`、`bash tests/scripts/test-blender-system-python.bash`。
Expected: wrapper 未作成・設定未追加で失敗することを報告する。

- [ ] **Step 3: 最小実装と説明を追加する**

既存のラッパーは親 checkout の `worlds/slum02/.resoloop/blender-system-python` を読み、同じ内容を雛形にする。jq の前提は init 前に確認。JSON が symlink でないことと単一 object/値の型を検証して plan に積む。wrapper の比較は `want_file` と `parent_ok` を使う。JSON 更新は二巡目だけで同じディレクトリの temp + 元 mode + mv、失敗時に temp を掃除する。別値は JSON を触らず保持を表示する。chmod は競合ゲート通過後だけ。

README に wrapper の用途、jq 前提、カスタム保持、古い絶対値を手動更新し `--apply` で不足分を補う方法を書く。apt 一覧に jq を追加する。既存ワールドや Issue #83 は変更しない。

- [ ] **Step 4: GREEN と全体回帰を確認する**

Run: `bash tests/scripts/test-new-world.bash`、`bash tests/scripts/test-blender-system-python.bash`、`bash .devcontainer/run-tests.bash`、`uv run pytest -q`、`bash scripts/check-layout.sh`、`git diff --check`。
Expected: shell 全件成功、pytest は基準と同じ Issue #83 の 1 件のみ失敗、その他成功。layout は worktree にローカルワールドが無い状態で共有配置を確認。構文を `bash -n` で変更した shell 全件に実行する。

- [ ] **Step 5: 自己レビュー・commit・報告する**

範囲、テスト採用基準、RED/GREEN、差分、git mode を確認し、変更したファイルだけ commit する。レポートにコマンドと出力、既知の失敗、総時間と内訳を書く。push・PR・Issue更新・文書状態変更・別子の委譲は controller に任せる。

## Controller の統合検証・公開

- [ ] 同じ brief・実装 report・Task 全コミットの review package で、sp-review に仕様と品質の読み取り専用レビューを委譲する。Critical/Important は実装担当に戻し、修正範囲だけ再レビューする。
- [ ] worktree 内の使い捨てワールドで実際の new-world.sh を実行する。resoloop の `blender find --json` の source が configuration、絶対 wrapper であることと、`uv run` 経由の meshy doctor の `bpy_numpy` を確認する。既存ワールドは変更しない。
- [ ] branch 全体の fresh read-only review を行う。controller で最終の回帰・構文・差分を確認し、Issue #83 の既知失敗を再現・記録する。
- [ ] 実行結果と文書の状態を追記して commit。親 checkout の `docs_draft/superpowers/` と、非置換の `tmp/superpowers-review/` にコミット済みの閲覧コピーを作る。
- [ ] feature branch だけを push し、main 向けに PR を作る。`Closes #68` と既知失敗の `#83` を本文に記載する。private リポジトリの CI は規約どおり確認不要。マージせず worktree を残す。

## 自己レビュー記録

- Spec の六点は Task 1 の Step 1〜4 と Controller の実環境検証で網羅する。
- 単一 Task のため Task 間の名前やインターフェースの不一致は無い。テストは実行による保証だけを追加し、文書・一覧の文字列テストは作らない。
- Review Focus の五点を Step 1 の各ケースへ割り当てた。基準失敗は別 Issue と明示許可があり対象外。
