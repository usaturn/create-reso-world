.. _<LABEL_NAME>:

.. authoring: directive-reference 用。
   対象拡張が提供する directive の仕様を、確認した内容どおりに記述する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。
   関連項目の参照は対象ごとに1種類だけ選び、rst:directive で定義済みの directive は :rst:dir:、
   明示ラベルを持つページ・節は :ref:、どちらもなければ literal にする。
   用語・CLI option・環境変数など他の対象は sphinx-semantic-markup.md の
   対象別の選択表にある role を1種類だけ選ぶ。
   記述の前に実ソース（Directive クラス・add_directive・option_spec）・conf.py・依存制約・呼び出し側の確かな入力・
   既存文書の正本定義を確認する。
   引数・option・default・版番号は確認した値だけを書く。
   directive が複数ある場合は「仕様」節の対象単位を複製し、ラベルを一意にする。
   定義ブロックは対象ごとに次のいずれか1つだけを選び、同じ object を二重定義しない。
   - 既に正本定義がある: define-reference の範囲に正本への参照と必要な補足だけを書き、
     定義ブロックを新設しない。
     正本が semantic 定義なら :rst:dir:、明示ラベルの定義なら :ref: で参照する。
   - semantic: RST domain が有効な場合に .. rst:directive:: を使う。
     各 option の定義は option が実在する場合だけ rst:directive:option を使う。
   - fallback: RST domain 自体が使えない場合は、明示ラベル + 小見出し + 構文の literal + 同じ本文構造に切り替える。
   記述用の RST domain 定義と、利用例として実際に directive を実行することは別の判断である。
   利用例を live の directive にできるのは、対象拡張が conf.py で有効化されていて描画結果を確認できる場合だけ。
   未有効なら code-block:: rst の記述例と、ソースで裏付けた描画結果の説明にする。
   code-block の例を実行済みとは書かない。
   option が実際に存在しない場合は「option なし」をソース確認のうえ明示し、知らない場合と区別する。
   その場合、構文・使用例・live 例の option 行は除き、:option: フィールドには「なし」と書く。
   版情報は対象の定義ブロック内の version-info 範囲に置き（option 単位の版はその
   rst:directive:option の body 内）、versionchanged / deprecated も確認できた場合は
   同じ位置に追加する。
   fallback では対象を定義する object directive がないため version directive を使わず、
   version-info 範囲に :版: フィールドで確認できた版を書く。
   版情報が確認できない場合は版を示す行と空の版節を残さず、不明であることを作業報告へ記録する。
   構文をインラインで示す場合、literal の中に `` :name:`...` `` 形式の role 記法を入れない
   （role 記法が literal の区切りへ直接接すると、lint の split guard が --fix を拒否する）。
   構文例は code-block:: rst に置き、
   インラインでは directive 名・option 名だけを literal にする。
   inline 記法の境界空白は記述時点で正しく入れる。
   バッククォートが隣接する箇所や literal 内の role 記法では split guard により
   --fix が拒否または部分適用になり得るため、修正後は同じ検査の再実行で残存違反を確認する

================
<DOCUMENT_TITLE>
================

<INTRO_TEXT: このページが扱う directive と拡張を1-2文で>

.. _<LABEL_NAME>_spec:

仕様
====

.. optional-start: define-reference

<REFERENCE_AND_NOTE: :rst:dir:`<DIRECTIVE_NAME>` または :ref:`<TITLE> <<LABEL>>` で正本を参照し、
必要な補足だけを確認した範囲で書く。
定義ブロックは新設しない>

.. optional-end: define-reference

.. optional-start: define-semantic

.. rst:directive:: .. <DIRECTIVE_NAME>:: <CONFIRMED_ARGUMENTS>

   <DESCRIPTION: directive の役割。
   引数の個数と意味、content の要否と形式を確認した範囲で>

   .. optional-start: version-info

   .. versionadded:: <CONFIRMED_VERSION>

   .. optional-end: version-info

   .. optional-start: directive-options

   .. rst:directive:option:: <OPTION_NAME>
      :type: <CONFIRMED_OPTION_TYPE>

      <OPTION_MEANING_AND_DEFAULT: option の意味・取りうる値・省略時の扱い>

      .. optional-start: version-info

      .. versionadded:: <CONFIRMED_OPTION_VERSION>

      .. optional-end: version-info

   .. optional-end: directive-options

.. optional-end: define-semantic

.. optional-start: define-fallback

.. _<LABEL_NAME>_<DIRECTIVE_KEY>:

<DIRECTIVE_NAME>
----------------

構文 ::

    .. <DIRECTIVE_NAME>:: <CONFIRMED_ARGUMENTS>
       :<OPTION_NAME>: <OPTION_VALUE>

       <CONTENT_FORM>

:引数: <ARGUMENTS_MEANING>
:本文: <CONTENT_REQUIREMENT>
:option: <OPTION_MEANING_AND_DEFAULT>

<DESCRIPTION: directive の役割を確認した範囲で>

.. optional-start: version-info

:版: <CONFIRMED_VERSION>

.. optional-end: version-info

.. optional-end: define-fallback

.. _<LABEL_NAME>_example:

使用例
======

<EXAMPLE_INTRO: どんな呼び出しかを1文で>

.. code-block:: rst

   .. <DIRECTIVE_NAME>:: <EXAMPLE_ARGUMENTS>
      :<OPTION_NAME>: <OPTION_VALUE>

      <EXAMPLE_CONTENT>

.. optional-start: example-live

描画結果は次のとおり

.. <DIRECTIVE_NAME>:: <EXAMPLE_ARGUMENTS>
   :<OPTION_NAME>: <OPTION_VALUE>

   <EXAMPLE_CONTENT>

.. optional-end: example-live

.. optional-start: example-result

<RENDERED_RESULT: 上の例が出力するノード・class・見た目をソースの裏付けで説明する>

.. optional-end: example-result

.. _<LABEL_NAME>_related:

関連項目
========

- <RELATED_REF_1> — <WHY_RELATED: この directive と関係する理由>
