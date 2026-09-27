.. _<LABEL_NAME>:

.. authoring: role-reference 用。
   対象拡張が提供する role の仕様を、確認した内容どおりに記述する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。
   関連項目の参照は対象ごとに1種類だけ選び、rst:role で定義済みの role は :rst:role:、
   明示ラベルを持つページ・節は :ref:、どちらもなければ literal にする。
   用語・CLI option・環境変数など他の対象は sphinx-semantic-markup.md の
   対象別の選択表にある role を1種類だけ選ぶ。
   記述の前に実ソース（role 関数・add_role の登録）・conf.py・依存制約・呼び出し側の確かな入力・
   既存文書の正本定義を確認する。
   構文・描画結果・版番号は確認した値だけを書く。
   role が複数ある場合は「仕様」節の対象単位を複製し、ラベルを一意にする。
   定義ブロックは対象ごとに次のいずれか1つだけを選び、同じ object を二重定義しない。
   - 既に正本定義がある: define-reference の範囲に正本への参照と必要な補足だけを書き、
     定義ブロックを新設しない。
     正本が semantic 定義なら :rst:role:、明示ラベルの定義なら :ref: で参照する。
   - semantic: RST domain が有効な場合に .. rst:role:: を使う。
   - fallback: RST domain 自体が使えない場合は、明示ラベル + 小見出し + 構文の literal + 同じ本文構造に切り替える。
   記述用の RST domain 定義と、利用例として実際に role を実行することは別の判断である。
   利用例を live の role にできるのは、対象拡張が conf.py で有効化されていて描画結果を確認できる場合だけ。
   未有効なら code-block:: rst の記述例と、ソースで裏付けた描画結果の説明にする。
   構文をインラインで示す場合、literal の中に `` :name:`...` `` 形式の role 記法を入れない
   （role 記法が literal の区切りへ直接接すると、lint の split guard が --fix を拒否する）。
   構文例は code-block:: rst に置き、
   インラインでは role 名だけを literal にする。
   inline 記法の境界空白は記述時点で正しく入れる。
   バッククォートが隣接する箇所や literal 内の role 記法では split guard により
   --fix が拒否または部分適用になり得るため、修正後は同じ検査の再実行で残存違反を確認する。
   版情報は対象の定義ブロック内の version-info 範囲に置き、versionchanged / deprecated も
   確認できた場合は同じ位置に追加する。
   fallback では対象を定義する object directive がないため version directive を使わず、
   version-info 範囲に :版: フィールドで確認できた版を書く。
   版情報が確認できない場合は版を示す行と空の版節を残さず、不明であることを作業報告へ記録する

================
<DOCUMENT_TITLE>
================

<INTRO_TEXT: このページが扱う role と拡張を1-2文で>

.. _<LABEL_NAME>_spec:

仕様
====

.. optional-start: define-reference

<REFERENCE_AND_NOTE: :rst:role:`<ROLE_NAME>` または :ref:`<TITLE> <<LABEL>>` で正本を参照し、
必要な補足だけを確認した範囲で書く。
定義ブロックは新設しない>

.. optional-end: define-reference

.. optional-start: define-semantic

.. rst:role:: <ROLE_NAME>

   <DESCRIPTION: role の役割。
   入力文字列・必要なエスケープ・描画されるノードを確認した範囲で>

   .. optional-start: version-info

   .. versionadded:: <CONFIRMED_VERSION>

   .. optional-end: version-info

.. optional-end: define-semantic

.. optional-start: define-fallback

.. _<LABEL_NAME>_<ROLE_KEY>:

<ROLE_NAME>
-----------

構文 ::

    :<ROLE_NAME>:`<TEXT>`

<DESCRIPTION: role の役割。
入力文字列・必要なエスケープ・描画されるノードを確認した範囲で>

.. optional-start: version-info

:版: <CONFIRMED_VERSION>

.. optional-end: version-info

.. optional-end: define-fallback

.. _<LABEL_NAME>_example:

使用例
======

<EXAMPLE_INTRO: どんな使い方かを1文で>

.. code-block:: rst

   <EXAMPLE_SOURCE: role を使う行>

.. optional-start: example-live

描画結果は次のとおり

<LIVE_EXAMPLE_LINE: 実際に role を使う行。
拡張が有効な場合だけ>

.. optional-end: example-live

.. optional-start: example-result

<RENDERED_RESULT: 上の例が出力するノード・見た目をソースの裏付けで説明する>

.. optional-end: example-result

.. _<LABEL_NAME>_related:

関連項目
========

- <RELATED_REF_1> — <WHY_RELATED: この role と関係する理由>
