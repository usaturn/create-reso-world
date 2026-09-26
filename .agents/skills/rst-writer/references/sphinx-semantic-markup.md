# Sphinx semantic markup

Sphinx 拡張機能など OSS Python project のドキュメントで、意味的 role / directive（`py:func`、`confval`、`option`、`term` など）をいつ使い、いつ代替へ落とすかを決める手順。この文書は `oss-python-extension` profile の記法選択ルールであり、共通の見た目・構造ルールは `rst-core-style-guide.md`、このリポジトリの文書の記法は `profiles/create-reso-world.md` を参照する。

この guide は一度読むだけでなく、リンクした文書を含めて全ルールを個別ページへ適用する。Sphinx 9.1.0 以上を前提とし、記法を選ぶ前に必ず対象 project の登録と参照先を調べる。「Sphinx 文書に存在するから」だけで role / directive を選ばない。

## 判定順序

各記法候補は次の2条件を順に検査し、両方が成立した場合だけ使う。1つでも成立しなければ、その候補の代替記法を使う。

1. **project が登録・有効化しているか**: 標準・RST・Python domain の組み込み記法か、`extensions` / `setup()` / `add_object_type` で project が登録した記法か。同名でも別物（独自登録の object type）なら、その登録の仕様に従う。
2. **参照先が解決できるか**: 対象 object・label・用語・inventory 項目が実在し、`-n`（nitpick）で解決されるか。

両方が成立する場合のみ意味的記法を使う。どれかが成立しなければ、その分岐の代替（literal、`.. _label:` + `:ref:`、確認済み公式 URL への外部リンク、または普通の説明）を使い、選んだ根拠を出力で説明する。

## 対象ごとの選択表

| 対象 | 定義時の記法 | 参照時の記法 | 意味的記法を使える条件 | 成立しない場合の代替 |
|---|---|---|---|---|
| Python object（module / class / function / method / attribute / exception / data） | `.. py:module::` / `.. py:class::` / `.. py:function::` / `.. py:method::` / `.. py:attribute::` / `.. py:exception::` / `.. py:data::`（`py:currentmodule` で修飾可） | `:py:mod:` `:py:class:` `:py:func:` `:py:meth:` `:py:attr:` `:py:exc:` `:py:data:`、または `:py:obj:` | 対象 object が実在し、公開 API として定義・参照対象登録されていること（autodoc が有効で取り込める、または手書き py directive が正本として登録済み）。外部 package は intersphinx inventory に存在すること | 実在するが参照対象登録がないなら ``` ``literal`` ```。外部 object で inventory が引けないなら公式 URL への外部リンク。存在しない object には role を張らず、要求された対象の不存在を報告する |
| 設定値（`conf.py` の設定項目） | `.. confval::`（`:type:` / `:default:` などの options） | `:confval:` | `confval` が project で有効（標準または独自登録）。独自 `add_object_type` 登録の場合はその object type の仕様に従う（下記「同名の独自登録」） | 定義記法が使えない場合は見出しレベルを下げた見出し + `.. _label:`、型・default・説明をフィールドまたは表で記述し、参照は `:ref:`。独自 object type 登録はその登録名とフィールド仕様に従う |
| reStructuredText directive | `.. rst:directive::` | `:rst:dir:` | RST domain が有効（組み込み）。記述する directive が実在すること | ``` ``.. directive::`` ``` の literal と必要に応じ `:ref:` |
| directive option | `.. rst:directive:option::` | `:rst:dir:` からの参照 | RST domain が有効。option がその directive で実在すること | directive 名と option 名を literal で併記 |
| reStructuredText role | `.. rst:role::` | `:rst:role:` | RST domain が有効（組み込み）。role が実在すること | ``` ``:role:`` ``` の literal |
| CLI program / option | `.. program::` + `.. option::` | `:option:`（program 修飾可）、`:program:` | std domain の `program`/`option` が有効（組み込み） | コマンド名・option 名の literal（`console` block での使用例を添えてもよい） |
| 環境変数 | `.. envvar::` | `:envvar:` | std domain の `envvar` が有効（組み込み） | 変数名の literal |
| event / hook / callback | なし（標準 domain に event 用記法はない） | なし | project が独自 object type や role を登録している場合のみ、その記法を使う | `setup(app)` の docstring 相当の説明 + `app.connect("event", ...)` の literal、または API 側の `py` 記法への `:ref:` / `:py:obj:`。独自の `event` 記法を標準にあるように見せかけて使わない |
| 用語（concept） | `.. glossary::` 内の `term` 項目 | `:term:` | 既存 glossary に対象項目が実在し、`:term:` が解決すること | 項目がない・ glossary 自体がない場合は普通の説明文 + 必要なら `.. _label:` + `:ref:`。ページ単独のために glossary を新設・追記しない |
| 文書・節 | なし | `:ref:`（`.. _label:` が必要） | 参照先 label が実在すること | label を新設してよいのは自分が書くページ内のみ。外部・未作成ページへは URL または不存在の報告 |
| 外部 object（intersphinx） | なし | `:py:obj:` 等 + `domain:objtype` 形式の `:external:` role | `sphinx.ext.intersphinx` が有効で、対象 inventory が取得でき、対象項目が inventory に存在すること | 確認済み公式 URL への外部リンク（通常は匿名参照 `` `text <URL>`__ ``）、または literal |
| 版履歴 | `.. versionadded::` / `.. versionchanged::` / `.. deprecated::` | なし | 記載する版番号が対象 object・API の実履歴として確認済みであること | 版番号が確認できないなら directive を使わず、確認できる事実だけを普通に書くか版情報の不明を報告する |

## 詳細ルール

### 同名の独自登録

- project が `add_object_type` や `setup()` で `confval` など同名の object type を登録している場合、標準記法の options（`:type:`、`:default:` など）が使えるとは限らない。その登録の `option_spec` / フィールド仕様を確認し、使える形式だけを使う。
- 独自登録の directive / role は、その登録が project の拡張コードで実在すると確認できた場合に限り使う。名前だけを推測して張らない。

### Python object

- `:py:*` role は、参照先 object が実際に Python domain に登録されているときだけ使う。autodoc（`sphinx.ext.autodoc`）が有効で対象が取り込まれているか、手書きの `py` directive が正本として存在するかを確認する。
- 対象 object が存在するが参照対象登録がない（autodoc 未設定・未記載）場合、role を張って `-n` で未解決にするより ``` ``literal`` ``` を選ぶ。未解決参照を残したまま完了しない。
- 同じ object の手書き定義と autodoc が重複すると「duplicate object description」警告になる。既存の正本（autodoc または既存 `py` directive）を残し、新規ページでは `:py:` role で参照する形にする。正本の移動・`:no-index:` の追加は、すでに重複が存在し解消が必要な場合に限り検討し、不用意に使わない。
- `demo_ext.setup` など extension の entry point を書く場合、対象関数が実在することを source で確認する。存在しない公開 API を捏造しない。

### 設定値

- `confval` を使う場合、`:type:` / `:default:` の値は project の `add_config_value` 呼び出しまたは実装で確認した値を書く。型・default を推測しない。
- project が `confval` 相当を独自 object type として登録している場合（例: `localconf`）、その登録が `option_spec` を持つか確認する。options を持たない汎用 object type には `:type:` / `:default:` options を付けず、本文のフィールドリストで書く。

### directive / role / option

- `rst:directive` / `rst:role` / `rst:directive:option` は、記述対象が実在する（project の拡張コードまたは依存で定義済み）場合にだけ使う。fixture やスタブ実装で仕様が不明な場合、存在する使用形式だけを記述し、未確認の option や引数を裏付けなしに足さない。
- CLI option は `.. program::` でコマンド名を限定し、同名 option が複数 program にある場合は `` :option:`prog --opt` `` のように修飾して参照を一意にする。`option` directive の body に説明を書く（`program` は body を持たない）。
- std domain の option 参照は、対象 project で実際に解決される形（`:option:`、`--opt`、`` :option:`prog --opt` `` など）を確認してから使う。

### event / hook

- 標準・RST・Python domain に event 専用の意味的記法はない。`.. event::` や `:event:` を標準にあるものとして使わない。
- event/hook の記述は、公開されている登録 API（`app.connect` など）か project が定義した hook 名を使い、存在しない event 名を作らない。project が独自 object type を登録している場合のみその記法を使い、そうでなければ literal + 説明、または API 側への `:ref:` / `:py:obj:` にする。

### 用語

- `:term:` は既存 glossary に対象項目が実在すると確認できた場合にだけ使う。項目がない場合は `:term:` を張らず、普通の説明文にする。
- 対象外の glossary を編集して項目を足すことで `:term:` を「解決可能にする」ことをしない。同様に、ページ内に `.. glossary::` block を新設して見せかけの用語集を作らない。用語の定義が必要ならページ内に `.. _label:` + 説明を書き、参照は `:ref:` にする。

### Intersphinx

- `:py:` / `:external:` などで外部 object を参照するのは、`sphinx.ext.intersphinx` が `extensions` にあり、対象 inventory が取得でき、対象項目がその inventory に存在すると確認できた場合だけ。
- inventory が取れない・項目がない場合は、確認済み公式 URL への匿名外部リンク（`` `text <URL>`__ ``）か literal に落とす。`:doc:` は使わない（`rst-core-style-guide.md` 参照）。
- 外部参照が「存在しないので張れない」場合は、その旨を報告し、role を張ったままにしない。

### 版履歴 directive

- `versionadded` / `versionchanged` / `deprecated` は、記載する版番号・変更内容が対象の実履歴として確認済みの場合だけ使う。版番号を推測で書かない。
- `versionchanged` / `deprecated` の本文は確認できた事実だけを書く。具体的な新旧値・代替 API が確認できないなら、その文だけを書く（例: 「default が変更された」「deprecated」）か、不明を報告する。裏付けのない詳細を補わない。
- これらは対象 object を定義する directive（`py:function` など）の body 内に置き、その object に紐付ける。独立した記法としてだけでなく、正本となる定義に付随させる。

## 代替記法の選び方

意味的記法が使えない場合、理由ごとに次を選ぶ。

- **project が記法を登録していない**: literal、または独自登録があればその記法（登録仕様に従う）。
- **参照先が存在しない・解決できない**: literal、または確認済み公式 URL への外部リンク。role を張って未解決警告を残さない。
- **参照先が一意でない**: `program` / `py:module` / `py:currentmodule` などで修飾して一意にする。曖昧なまま role を張らない。

代替を選んだら、なぜ意味的記法にしなかったか（未登録・未解決・未確認）を出力で一言説明する。代替記法でも `rst-core-style-guide.md` の構造・コード block・lint ルールはそのまま適用する。

## やってはいけないこと

- `:doc:` を使うこと。内部参照は `.. _label:` + `:ref:`。
- 参照先が存在しない・解決できない role（`:py:`、`:term:`、`:option:` 等）を張ること。
- project が登録していない独自記法（`event` など）を標準にあるように使うこと。
- 版番号・型・default・引数などを裏付けなしに記述すること。
- `:term:` を解決させるためだけに glossary を編集・新設すること。
- 意味的記法を解決させるためだけに対象外ファイル（`conf.py`、glossary、autodoc 設定など）を変更すること。必要な変更は「必要な後続作業」として報告する。
- 同じ object を autodoc と手書き directive で二重定義すること。
