# OSS Python Extension profile

`profile=oss-python-extension` に適用する執筆・環境確認・検証方針である。
この文書は **entrypoint が接続されたあとに使う**（現在は未接続。[文書種別表](../document-types.md) を参照）。接続前に直接この文書を使う評価・作業では、呼び出し仕様の停止条件ではなく本書の手順を適用する。

RST 構造・ラベル・4段階 lint は [共通 guide](../rst-core-style-guide.md)、6つの入力と停止条件は [入力仕様](../profile-interface.md)、document_type とリソースの対応は [文書種別表](../document-types.md) を正本とする。
role・directive の選択条件と fallback は [Sphinx semantic markup](../sphinx-semantic-markup.md) を読む。

## 入力と対象 project

- 入力は共通の6つ。OSS では `document_type` / `target_path` / `language` が必須で、`audience` / `package_name` は任意である。必須値の欠落・空値・未知値・明示値同士の矛盾は、入力仕様の停止条件に従い書き込み前に報告する。追加の呼び出しパラメータは作らない。
- Sphinx 9.1.0 以上を前提とし、版による記法の分岐はしない。前提を満たさない project は下記「環境の確認順」で停止する。
- 対象は呼び出し側が指定した project/cwd と `target_path` から確定する。相対パスはその project/cwd 基準で解決し、create-reso-world の `docs_draft/` へ読み替えない。
- 既存ページの編集では対象を先に読み、依頼範囲外の本文・ラベル・コメントを保持する。

## 書き込み先と副作用の境界

- 今回書き込んでよいのは **`target_path` の1ファイルだけ**である。例外は無い。
- toctree への登録、別ページのラベル追加・本文修正、glossary の新設・追記、conf.py・依存設定・サンプルコードの変更はすべて指定外であり、実行せず必要な作業として報告する。参照先ラベルが別ファイルに必要な場合も同様である。
- 依存の追加、sample・fixture の新設、テンプレートファイルの生成もこの単一ページ作業に含めない。
- 新規ページが toctree に登録できないことによる警告を `:orphan:` などで消して成功に見せかけない。警告を残し、toctree 登録を必要な後続作業として報告する。

## 環境の確認順

書き込み前に、次の順で対象 project を読み取り確認する。各段階の結果をまとめてから書き込む。不存在も記録する。

1. 対象 checkout・`target_path` の実体パス・編集対象を確定する。
2. `conf.py`（`docs/conf.py` 固定とは限らない。既存 build の `-c` や別 source dir も確認）→ `pyproject.toml` → `tox.ini` → `noxfile.py` → root `Makefile` → `docs/Makefile` → `requirements*.txt` と対応 lock。
3. `needs_sphinx`、依存に含まれる Sphinx 制約、docs 用環境、実際に動く Sphinx version、有効な `extensions` と既存のローカル登録を確認する。設定ファイル上の記述と実環境の確認を区別し、dynamic config を推測で補わない。
   `needs_sphinx`・依存の Sphinx 制約のいずれか1つでも下限が 9.1 未満の場合、または実行中の Sphinx が 9.1 未満の場合は、対象外として停止し、書き込み・lint・build をせずに報告する。`needs_sphinx` や依存を書き換えない。下限の宣言がなく実行版が 9.1 以上なら進める。
4. 既存文書の文体・ラベル慣習・glossary の有無と項目・changelog 形式・図表拡張の有無を読む。

## 内部で確定するパス

以下は内部で解決する名前であり、呼び出し入力を増やすものではない。報告では絶対パスと採用理由を記録する。

| 内部名 | 意味 |
|---|---|
| `PROJECT_ROOT` | 対象 project の checkout root |
| `DOCS_SOURCE` | 実際の Sphinx source dir（`docs/` 固定とは限らない） |
| `LINT_PROJECT` | `wabun-rst-ulint` を提供する確認済み Python project |
| `BUILD_CWD` / `BUILD_COMMAND` | 既存 docs build を実行する cwd とコマンド |

`LINT_PROJECT` の決定規則:

- 対象 project 自身が `wabun-rst-ulint` を提供するなら `PROJECT_ROOT` を使う。
- 呼び出し側が検査用 project を明示した場合は、その絶対パスと指定根拠を記録して使う。
- 上記以外の project（親・兄弟・共有環境）は、存在し linter を提供していても **暗黙に採用しない**。
- 対象提供でも呼び出し側の明示でもない場合に、作業者側で新しい検査環境を新設して lint 済みとしない。一時的な `uv run --with` 等で実行しても `LINT_PROJECT` 確定の扱いにはしない。
- いずれも得られなければ lint は未検証とし、lint 合格とは報告しない。

`BUILD_CWD` / `BUILD_COMMAND` は対象 project の既存 wrapper（Makefile/tox/nox/uv）が用意するものを優先し、lint project と build project が別なら両方を記録する。

## 執筆方針

- `language` と対象の既存スタイルを使う。日本語・である調、固定の「概要」、末尾の単独「以上」、zsh などの create-reso-world profile の決まりは持ち込まない。ページ・節ラベル、一意性、RST 構造、`:doc:` 不使用、4段階 lint は共通 guide に従い維持する。
- 言語・用途が明確なら `.. code-block::` に `console` / `python` / `rst` / `json` / `yaml` / `toml` / `text` を使う。shell 固有機能にだけ shell 系を明示する。
- 実在する sample は `.. literalinclude::` を優先する。包含元 RST からの相対パス、選択範囲（`:lines:` 等）、対象ファイルの実在を確認する。短い説明用の例は `code-block` を使う。
- 実行可能な Python 例は、対象の既存 doctest 環境が使える場合だけ実行を検討する。表示だけの例を実行済みとはしない。
- 図表は対象の既存図表拡張が有効な場合にその記法を使う。ない場合はテキストや表で説明するか、拡張導入を別途提案する（この作業では導入しない）。
- Python object、設定値、directive、role、CLI option、環境変数は glossary に登録しない。概念は、既存 glossary に解決可能な項目がある場合だけ `:term:` で参照する。用語集がない・項目がない場合は普通の説明を使う。

## 記法の選択

- semantic markup の対象別の定義・参照・版条件・fallback は [Sphinx semantic markup](../sphinx-semantic-markup.md) に従う。
- 専用 role/directive は、project が登録・有効化しており参照ターゲットが解決できる場合に使う。環境確認で記録した登録済み機能を根拠にする。
- `:doc:` は使わない。参照ターゲットが存在しない・解決できない場合は semantic guide の fallback に従う。

## 検査手順

1. 変更した RST の絶対パスを `TARGET` として、共通 guide の4段階 lint を `uv run --project "$LINT_PROJECT"` で指定順・指定フラグのまま実行する。`LINT_PROJECT` が得られない場合は lint 未検証として進め、報告で明示する。
2. 対象 project の既存 docs build を優先して実行する。wrapper が用意する生成処理・import path・環境を維持し、wrapper 流の option 渡し方（`SPHINXOPTS` 等）を読んで、warning を失敗として扱う診断有りの検査にする。既存の警告抑制設定を把握し、新しい警告の抑制で成功にしない。
3. 既存 build がない場合だけ、確認済みの Sphinx 環境で `sphinx-build -n -W --keep-going -b html SOURCE BUILD` を候補にする。uv project のない対象に `uv run --project` を決め打ちしない。
4. 拡張を import できない、ネットワーク・既存警告・環境差異に起因する問題は、対象とコマンド・終了値を保存して blocker として報告する。`conf.py` や依存を直して回復しない（指定外の変更）。

完了判定:

- warning、未解決参照、未知 role/directive、重複ラベル、missing document、autodoc import failure、invalid option、RST error は未解決なら完了としない。
- 本文を修正したら、変更した RST の4段階 lint と build を再実行する。影響した検査を未実行のまま成功としない。
- lint の終了値 0 と Sphinx build 成功を混同しない。

## 報告

次を含めて報告する: 対象ページ、解決した `PROJECT_ROOT` / `DOCS_SOURCE` / `LINT_PROJECT` / `BUILD_CWD` / `BUILD_COMMAND` と採用理由、宣言された Sphinx 制約と実行版、変更ファイル、実コマンドと終了値、警告と未検証事項、指定外だが必要と判明した作業。
