.. _<LABEL_NAME>:

.. authoring: installation 用。読者が利用環境を整えて有効化を確認する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   「有効化」は対象が有効化手順を持つ場合だけ残し、Sphinx 拡張以外では対象の有効化方法へ置き換える。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: このページで整える環境と、導入後にできることを1-2文で>

.. _<LABEL_NAME>_requirements:

要件
====

- <REQUIREMENT_1: 例 Python バージョン>
- <REQUIREMENT_2: 例 Sphinx バージョン>

.. _<LABEL_NAME>_install:

導入
====

<INSTALL_INTRO: 導入方法を1文で>

.. code-block:: console

   <INSTALL_COMMAND>

.. optional-start: enable

.. _<LABEL_NAME>_enable:

有効化
======

<ENABLE_TEXT: 有効化が必要な理由と方法を1-2文で。Sphinx 拡張なら conf.py の extensions 追加など>

.. code-block:: python

   <ENABLE_CONFIG_EXAMPLE>

.. optional-end: enable

.. _<LABEL_NAME>_verify:

導入確認
========

<VERIFY_INTRO: 何を確認するかを1文で>

.. code-block:: console

   <VERIFY_COMMAND>

<EXPECTED_VERIFY_RESULT: 期待される出力や確認結果を具体的に>

.. _<LABEL_NAME>_next:

次の文書
========

- :ref:`<QUICKSTART_PAGE_TITLE> <<QUICKSTART_PAGE_LABEL>>` — <WHY_QUICKSTART: 導入直後に進む理由>
