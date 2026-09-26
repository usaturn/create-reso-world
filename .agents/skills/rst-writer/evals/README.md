# rst-writer evals

rst-writer の eval セットと、それを実行・採点する手順である。
`evals.json` のケース定義、`fixtures/` の架空 project、本書の準備・実行・採点手順を一体で使う。

専用の自動 runner は存在しない。利用可能な agent harness（Claude Code / Codex / Devin 等の subagent 実行）で1件ずつ実行し、証跡を保存して採点する。`run_eval.py` は description の trigger 評価用であり、RST 生成の評価には使わない。

OSS Python Extension のケース（`oss-extension` fixture）と本書の OSS の手順は、移行元のリポジトリで作成した評価の記録である。`#393` などの番号は移行元の Issue を指す。`entrypoint_before_393` / `entrypoint_after_393` は「OSS profile の接続前 / 接続後」と読み替える。このリポジトリでは OSS profile を接続していないので、entrypoint の OSS のケースは接続前の期待（`stopped-unavailable` など）で採点する。

## 構成

```
evals/
  evals.json                  30ケースの定義（id 0・5・23〜33 は欠番）
  README.md                   本書
  fixtures/
    oss-extension/            架空 Sphinx 拡張 project（queue_ext）
      pyproject.toml, uv.lock build 環境（Sphinx 9.1.0）
      lint/pyproject.toml, lint/uv.lock  lint 環境（wabun-rst-ulint 0.0.1）
      Makefile                既存 docs wrapper（`make docs` = strict build）
      src/queue_ext/          架空 API・directive・role
      examples/basic.py       literalinclude 用の実サンプル
      docs/                   正常な Sphinx source tree
      variants/ja/docs/       日本語版 docs tree 全体
      HISTORY.txt             架空履歴の正本（0.1.0 / 0.2.0）
    repo-env/                 create-reso-world profile 用の一時リポジトリの素材
      .gitignore              /docs_draft/
      docs/resoloop-notes.rst 既存文書の編集ケース（42）の対象
    negative/*.rst.txt        7種の負例断片（正常 tree には混ぜない）
```

## evals.json の構造とメタデータ

既存の `skill_name` / `evals` / `id` / `name` / `prompt` / `expected_output` / `files` / `assertions` を維持する。加えて評価者向けのメタデータを置く。これらは rst-writer の呼び出し入力ではなく、fixture 選択と期待状態の記録である。

| フィールド | 意味 |
|---|---|
| `fixture` | `oss-extension` / `repo-env` / `none`（停止ケース等） |
| `execution_modes` | 適用する mode（下記）の配列 |
| `setup` | 評価者が実行前に case コピーへ施す準備（ページ除去・variant 適用・linter 除去等）。なければ `[]` |
| `expected_status` | mode ごとの期待状態。`component` / `entrypoint_before_393` / `entrypoint_after_393` |
| `artifact_requirements` | 採点に必要な証跡の補足。省略時は後述の標準セット |

`files` は skill root 相対で、そのケースの判定に必要な実在ファイルを列挙する。`assertions` は期待状態に応じて grader が `expectations[].text` として受け取る観測可能な文である。

## 採点 gate（期待状態・profile 別）

component では `expected_status.component`、entrypoint では統合前後に応じて `entrypoint_before_393` / `entrypoint_after_393` を選び、次の条件だけを grader に渡す。control は同じ入力で行う独立比較であり、`expected_status` に control 用の値はない。

| 期待状態 | grader に渡す条件 |
|---|---|
| `stopped-unavailable` / `stopped-input` / `stopped-blocked` | その状態に対応する停止理由と必要な修復、source の変更ゼロ、lint/build 未実行、最終報告。case 固有の assertions から停止に関する文だけを選び、生成物・lint/build 成功を前提とする文と下記の生成用 gate は渡さない。停止に関する assertion がない case 1 の統合前 entrypoint でも、この共通の停止条件を採点する。 |
| `generated` | case 固有の生成用 assertions と、profile に適用する下記の gate。 |
| `generated-with-caveat` | case 固有の assertions と、実施できた検証に適用する下記の gate。case 38 は linter 不在を明示し、未実施の検証成功を要求しない。 |
| `reported-failure` | case 固有の assertions と、下記の生成用 gate。case 39 では lint/build の実行記録と失敗の正確な報告を要求し、setup で注入した対象外警告だけを文書検証失敗として記録する。正しい報告を case の不合格にしない。 |

生成する期待状態では、選択した assertions と併せて次の gate を適用する。

- **input/routing**: 6入力（`profile` / `document_type` / `target_path` / `language` / `audience` / `package_name`）を正しく解釈し、target と template の選択根拠を記録した。
- **RST/content**: 生成物が実装・fixture の事実（型・default・引数・表示）と一致する。言語・文書種別の役割を守る。
- **semantic**: OSS では参照が正しい定義先へ解決し、Sphinx `-n` で未解決・重複定義がない。create-reso-world では Sphinx の role を使っていないことを確認し、Sphinx build は要求しない。ただし case 39 の setup で対象外の toctree に注入した `nonexistent-page` の警告だけは case 不合格にせず、`document_validation=failed` に記録する。
- **scope**: 許可された source だけを変更した（どちらの profile も target 1ページ。create-reso-world は用語集を探さず、作らない）。before/after hash と diff で判断する。
- **workflow**: harness の実コマンド記録とログで、OSS は原則として対象の4段階 lint と既存 build 優先の build、create-reso-world は対象への `rstcheck --report-level warning`（`uv run --no-project --with docutils --with rstcheck`）を確認する。順序・flags・対象を確認し、列挙だけの自己申告は証拠にしない。case 38 は linter を借用せず lint 未検証と記録して build を行い、case 39 は失敗した build のログを残す。
- **reporting**: 最終報告が実際のログと一致し、未実行・失敗・環境不足を明示する。警告を黙殺しない。

選択した条件がすべて合格したときだけ `case_status=pass` とする。期待どおりの `stopped-blocked` は `case_status=pass`、`document_validation=not-run` にできる。`case_status=blocked` は期待した停止ではなく、実行前の環境不足などで採点を開始できない場合に使う。実行自体がない場合は `not-run` とし、どちらも pass に換算しない。実行したが必須の証跡が残らなかった場合は fail とする。

## 実行 mode

| mode | 意味 |
|---|---|
| `fixture-validation` | 評価者自身が fixture の正常/異常 build と診断の検出性を確認する。agent の実行ではない |
| `component` | 統合前評価。共通 guide・該当 profile・semantic guide・利用可能な template を executor に直接与える。SKILL.md 入口や template 選択機構の評価ではない |
| `entrypoint` | `SKILL.md` を入口に実行する。現行 base では OSS profile が reserved なので、正しく停止することが成功である（OSS 生成成功ではない）。#393 統合後は各ケースの `expected_status.entrypoint_after_393` に従って再実行する |
| `control` | rst-writer の資料を与えない独立実行。同じ fixture・prompt・model・権限を使う |

`expected_status` の意味:

- `generated` — 指定 target の作成/編集と検証まで完了する
- `stopped-unavailable` — OSS profile 未接続を正しく報告して停止（pre-integration gate の成功）
- `stopped-input` — 入力不足・未知値・矛盾を正しく報告して停止
- `stopped-blocked` — リソースの不足、または宣言された Sphinx 制約が 9.1 未満を許す対象外の project（case22）を正しく報告して停止
- `generated-with-caveat` — 生成は行うが lint 未検証等を正直に報告する（case38）
- `reported-failure` — 指定外の問題で build が失敗することを正しく報告する（case39）。`document_validation` は failed のまま

## 準備

fixture の正本は直接実行・編集しない。全て case ごとの一時コピーで行う。同一 case の `control` / `with-skill` / `entrypoint` も別コピーを使う（先行実行の生成物・`.venv`・`docs_draft` が後続実行の初期状態を汚染するため）。`setup` 適用後の状態が実行前 baseline であり、変更差分は「baseline と実行後」の比較で採る（fixture 正本との差分には setup 由来の差が混ざる）。

### OSS project

```sh
FIXTURES=<skill root>/evals/fixtures
OSS_CASE=$(mktemp -d /tmp/rst-writer-oss-XXXXXX)
cp -R "$FIXTURES/oss-extension/." "$OSS_CASE/"
uv sync --project "$OSS_CASE" --locked --python 3.14
uv sync --project "$OSS_CASE/lint" --locked --python 3.14
uv run --project "$OSS_CASE" sphinx-build -n -W --keep-going -b html "$OSS_CASE/docs" "$OSS_CASE/_build/html"
```

期待: 最後の build が exit 0・warning なし。

- build project: `$OSS_CASE`（Sphinx 9.1.0、`needs_sphinx="9.1"`）
- LINT_PROJECT: `$OSS_CASE/lint`（呼び出し側が明示する検査用 project）
- 既存 build wrapper: `make -C "$OSS_CASE" docs`（`SPHINXOPTS` に `-n -W --keep-going` が既定）
- sample: `PYTHONPATH="$OSS_CASE/src" uv run --project "$OSS_CASE" python "$OSS_CASE/examples/basic.py"` → `task:alpha`

### variant（case ごとの fresh copy への適用）

| variant | 準備操作 | 対象 case |
|---|---|---|
| ja | `rm -rf "$OSS_CASE/docs" && cp -R "$OSS_CASE/variants/ja/docs" "$OSS_CASE/docs"`（conf.py ごと差し替え、`language="ja"`） | 3 |
| no-wrapper | `rm "$OSS_CASE/Makefile"`。build は `uv run --project "$OSS_CASE" sphinx-build -n -W --keep-going -b html "$OSS_CASE/docs" "$OSS_CASE/_build/html"` を直接実行 | 12 |
| no-glossary | `rm "$OSS_CASE/docs/glossary.rst"` し、`docs/index.rst` の toctree から `glossary` 行を除去 | 14 |
| new-page | `rm "$OSS_CASE/docs/<target>"`（toctree は保持。開始時の missing document は既知、完了後の解消を要求） | 15 |
| no-linter | `rm -rf "$OSS_CASE/lint"`（linter を提供しない project。兄弟 copy には存在する）。この case では共通準備の `LINT_PROJECT=$OSS_CASE/lint` を executor に指定しない | 38 |
| objects-canonical-split | `docs/objects.rst` から当該 object の定義ブロックを除去し、対象 reference ページを正本にする | 4, 6, 7, 8 |

### create-reso-world の一時リポジトリ

```sh
REPO_CASE=$(mktemp -d /tmp/rst-writer-repo-XXXXXX)
cp -R "$FIXTURES/repo-env/." "$REPO_CASE/"
git -C "$REPO_CASE" init -q
git -C "$REPO_CASE" remote add origin https://github.com/usaturn/create-reso-world.git
git -C "$REPO_CASE" add -A
git -C "$REPO_CASE" -c user.name=eval -c user.email=eval@example.com commit -qm fixture
uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$REPO_CASE/docs/resoloop-notes.rst"
```

最後の検査が exit 0 であることを確認する。remote は skill の root 確認を通すためのローカル設定であり、fetch/push は行わない。executor の cwd は `$REPO_CASE`（case 41 は setup で作る `$REPO_CASE/slum02`）とし、実リポジトリへ戻らないことを監査する。

- 既定 draft 先: `$REPO_CASE/docs_draft/`（実行前は無くてよい）

## 負例（fixture-validation）

`fixtures/negative/*.rst.txt` は正常 source tree に混ぜない。case ごとの fresh copy に1種ずつ適用し、strict build が非0かつ該当診断を出すことを確認する。6種はファイルごと `docs/` へコピーして toctree へ登録する専用ページ、`missing-document` は `docs/index.rst` の toctree に1行追加する（各ファイル冒頭のコメントに手順を記載）。

| 負例 | 期待診断（意味ベース。全文一致は要求しない） |
|---|---|
| unresolved-reference | `undefined label` 系の未解決参照 |
| unknown-role | `Unknown interpreted text role` |
| unknown-directive | `Unknown directive type` |
| duplicate-label | `objects` ラベルの重複（両位置が示される） |
| missing-document | toctree の `nonexistent-page` 不整合 |
| autodoc-import-failure | autodoc の import failure |
| invalid-option | `queue-summary` の unknown option |

各負例で非0を確認したあと、改めて fresh normal copy で exit 0 を再確認する。`set -e` 環境では `if command; then status=0; else status=$?; fi` で終了値を保持し、`tee` へ流すなら `PIPESTATUS[0]` を記録する。

4段階 lint の不動点も、負例や agent 実行とは別の fresh copy で確認する。OSS の通常 `docs/` と ja variant の `docs/` は、それぞれ全 `.rst` の実行前 hash を記録し、`LINT_PROJECT=$OSS_CASE/lint` で共通 guide の4コマンドを各ファイルに指定順・flags のまま実行する。全コマンドが exit 0 で、実行後の hash と差分が各 baseline と一致することを確認する。ja variant は別 copy に適用し、通常 tree を上書きしない。

## 実行手順（component / entrypoint / control）

1件ずつ: id 選択 → fresh copy → variant/`setup` 適用 → 入力 hash 記録 → executor 起動 → 完了待ち → 成果物取得 → grader → 結果保存。

executor へ渡す指示文（`CASE_ROOT` / `RUN_DIR` は起動時に実在絶対パスへ置換する評価者変数であり、rst-writer の新パラメータではない）:

```text
選択した eval の prompt と files を使って1ページ作業を実行する。
作業先は評価者が用意した CASE_ROOT のみ。PROJECT_ROOT/cwd は CASE_ROOT。
control は rst-writer を読まない。with-skill は指定した snapshot と mode の資料を読む。
mode=component では共通 guide、該当 profile、semantic guide、利用可能 template を直接読む。
mode=entrypoint では指定 snapshot の SKILL.md から開始する。
採点基準は渡さない。実コマンドと stdout/stderr/exit を保持し、未実行は明記する。
指定以外の source を変更しない。観測成果物は評価者が指定する RUN_DIR に保存する。
対象 source の before/after、最終 RST、diff、ログ、最終報告を残して終了する。
```

上記に実際の eval prompt・files・版（Python/Sphinx/linter）・`LINT_PROJECT` の指定根拠（case 38 では未指定の理由）を添える。control と with-skill は同じ入力 bytes・model・権限を使う。skill snapshot の比較は保存してよいが、#390 は skill 本体を変えないため旧版と候補版の改善率を捏造しない。

### 保存する証跡（RUN_DIR ごと）

- `eval_metadata.json`: eval id、mode、skill snapshot の SHA、model、fixture の hash、版、準備内容
- `transcript`: harness の生の実行記録
- `commands.jsonl`: 1件ごとに sequence・cwd・argv（配列）・exit_code・stdout/stderr 保存先・開始/終了時刻。tool 記録または subprocess 実出力から採取し、自己申告の一覧は代用にしない。subagent harness 等で tool 記録が取得できない場合は、検証コマンドを必ず記録ラッパー（argv/cwd/exit/stdout/stderr を JSONL とファイルへ保存する薄い wrapper）経由で実行するよう executor 指示へ書く
- `before/`, `outputs/`, `changes.diff`: 対象 source の前後と最終差分
- `logs/lint-*`, `logs/sphinx-*`: 実ログ
- `grading.json`: 下記形式の採点結果
- `timing.json`: 開始/終了時刻（評価者側が記録。省略可）

記録用ファイルと build/.bak は承認済み観測物として列挙するが、指定外 source の編集は許可しない。

### grading.json

```json
{
  "case_status": "pass|fail|blocked|not-run",
  "document_validation": "passed|failed|not-run",
  "expectations": [{"text": "assertion または共通 gate の文言", "passed": false, "evidence": "証跡パスと観測"}],
  "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0}
}
```

`case_status` は agent 行動の合否、`document_validation` は文書そのものの検証状態である。期待どおりの停止は case が pass しても生成成功率へ数えず、文書検証は `not-run` とする。証拠が欠落する expectation は pass にしない。生成ケースでは RST/HTML を実際に読み、リンク先の object・型・default・既存本文保持を判断する。JSON の構文検査と文字列一致はデータ整合の確認に限る。

## #393 への引き渡し

- 本 bundle の component 結果は「統合前に profile 資料を直接与えた場合」のものである。`assets/oss-python-extension/` に #388 の reference 系 template（configuration-reference / directive-reference / role-reference / api-reference）が未存在の間、reference 系 case の template 選択は未検証とする。
- entrypoint は統合前 `stopped-unavailable` が正解。#393 後は各ケースの `expected_status.entrypoint_after_393` に従って再実行する。case 22 は `stopped-blocked`、case 38 は `generated-with-caveat`、case 39 は `reported-failure` を期待する。
- eval 実行・証跡・失敗ログの保存先は評価者が明示して渡す。
