.. _<LABEL_NAME>:

.. authoring: landing-page 用。読者が導入する価値と次の一歩を判断する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。API の列挙欄は作らない。

==================
<DOCUMENT_TITLE>
==================

<PURPOSE_TEXT: 対象が何をするかと導入する価値を1-3文で>

.. _<LABEL_NAME>_features:

主な機能
========

- <FEATURE_1>
- <FEATURE_2>

.. _<LABEL_NAME>_example:

最小例
======

<EXAMPLE_INTRO: 最小例が何を示すかを1文で>

.. code-block:: rst

   <MINIMAL_RST_EXAMPLE>

.. _<LABEL_NAME>_next:

次の文書
========

- :ref:`<INSTALLATION_PAGE_TITLE> <<INSTALLATION_PAGE_LABEL>>` — <WHY_INSTALLATION: 導入手順へ進む理由>
- :ref:`<QUICKSTART_PAGE_TITLE> <<QUICKSTART_PAGE_LABEL>>` — <WHY_QUICKSTART: 最短で結果を確認する理由>
