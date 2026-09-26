.. _<LABEL_NAME>:

.. authoring: configuration-reference 用。
   対象 project の設定値を、確認した仕様どおりに記述する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。
   関連項目の参照は対象ごとに1種類だけ選び、confval で定義済みの設定値は :confval:、
   明示ラベルを持つページ・節は :ref:、どちらもなければ literal にする。
   用語・CLI option・環境変数など他の対象は sphinx-semantic-markup.md の
   対象別の選択表にある role を1種類だけ選ぶ。
   記述の前に conf.py・依存制約・実ソース（add_config_value / setup() / 登録コード）・呼び出し側の確かな入力・
   既存文書の正本定義を確認する。
   型・default・版番号は確認した値だけを書く。
   confval の :type: / :default: と fallback の :型: / :デフォルト: の値はインライン記法として解釈される。
   値に * など記法の文字を含む場合は値全体を literal（``…``）にし、引用符で囲むだけで済ませない。
   設定値が複数ある場合は「設定値」節の対象単位（ラベル + 定義ブロック）を複製し、ラベルを一意にする。
   定義ブロックは対象ごとに次のいずれか1つだけを選び、同じ object を二重定義しない。
   - 既に正本定義がある: define-reference の範囲に正本への参照と必要な補足だけを書き、
     定義ブロックを新設しない。
     正本が semantic 定義なら :confval:、明示ラベルの定義なら :ref: で参照する。
   - semantic（confval）: 標準 confval では :type: / :default: options を使う。
     project が同名 object type を独自登録している場合は、その登録の option_spec を確認する。
     options を持たない登録では :type: / :default: を付けず、登録名の directive の本文をフィールド形式で書く。
     標準 confval または options を持つ独自登録では confval-fields の範囲を除き、
     options を持たない独自登録では :type: / :default: options を除いて同範囲のフィールドを本文に残す。
   - fallback: 標準 confval が独自登録で置き換えられ、
     その登録でも定義できない場合など、confval 相当の定義記法が使えない場合に採用する。
     見出し + 明示ラベル + 型/default のフィールドで semantic と同じ情報を残し、参照は :ref: にする。
   版情報は対象の定義ブロック内の version-info 範囲に置き、versionchanged / deprecated も
   確認できた場合は同じ位置に追加する。
   fallback では対象を定義する object directive がないため version directive を使わず、
   version-info 範囲に :版: フィールドで確認できた版を書く。
   版情報が確認できない場合は版を示す行と空の版節を残さず、不明であることを作業報告へ記録する。
   設定値・API・directive・role を :term: にしない。
   glossary の新設・追記も行わない。
   inline 記法の境界空白は記述時点で正しく入れる。
   バッククォートが隣接する箇所や literal 内の role 記法では split guard により
   --fix が拒否または部分適用になり得るため、修正後は同じ検査の再実行で残存違反を確認する

================
<DOCUMENT_TITLE>
================

<INTRO_TEXT: このページが扱う拡張と設定値の範囲を1-2文で>

.. _<LABEL_NAME>_values:

設定値
======

.. optional-start: define-reference

<REFERENCE_AND_NOTE: :confval:`<CONFIG_NAME>` または :ref:`<TITLE> <<LABEL>>` で正本を参照し、
必要な補足だけを確認した範囲で書く。
定義ブロックは新設しない>

.. optional-end: define-reference

.. optional-start: define-semantic

.. confval:: <CONFIG_NAME>
   :type: <CONFIRMED_TYPE>
   :default: <CONFIRMED_DEFAULT>

   <DESCRIPTION: 設定値の意味と効果。ソースで確認した範囲で>

   .. optional-start: confval-fields

   :型: <CONFIRMED_TYPE>
   :デフォルト: <CONFIRMED_DEFAULT>

   .. optional-end: confval-fields

   .. optional-start: version-info

   .. versionadded:: <CONFIRMED_VERSION>

   .. optional-end: version-info

.. optional-end: define-semantic

.. optional-start: define-fallback

.. _<LABEL_NAME>_<CONFIG_KEY>:

<CONFIG_NAME>
-------------

:型: <CONFIRMED_TYPE>
:デフォルト: <CONFIRMED_DEFAULT>

<DESCRIPTION: 設定値の意味と効果。
ソースで確認した範囲で>

.. optional-start: version-info

:版: <CONFIRMED_VERSION>

.. optional-end: version-info

.. optional-end: define-fallback

.. _<LABEL_NAME>_example:

設定例
======

<EXAMPLE_INTRO: 何を設定する例かを1文で>

.. code-block:: python

   <CONF_PY_EXAMPLE>

.. _<LABEL_NAME>_related:

関連する設定
============

- <RELATED_REF_1> — <WHY_RELATED: この設定値と関係する理由>

.. optional-start: related-more

- <RELATED_REF_2> — <WHY_RELATED_2: この設定値と関係する理由>

.. optional-end: related-more
