.. _<LABEL_NAME>:

.. authoring: quickstart 用。読者が最短で最初の成果を得る構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   導入手順そのものは重複させず、冒頭で導入文書へ :ref: する。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: このページで得られる最初の成果を文末の句点を含む1-2文で>
前提として :ref:`<INSTALLATION_PAGE_TITLE> <<INSTALLATION_PAGE_LABEL>>` が完了していること。

.. _<LABEL_NAME>_configuration:

設定
====

<CONFIG_INTRO: 最小設定の意味を1文で>

.. code-block:: python

   <MINIMAL_CONFIG_EXAMPLE>

.. _<LABEL_NAME>_usage:

使ってみる
==========

<USAGE_INTRO: 最小の利用例を1文で>

.. code-block:: rst

   <USAGE_RST_EXAMPLE>

.. _<LABEL_NAME>_run:

実行
====

.. code-block:: console

   <BUILD_OR_RUN_COMMAND>

.. _<LABEL_NAME>_expected:

期待される結果
==============

<EXPECTED_RESULT_TEXT: 出力ファイル・表示・状態など、確認できる期待値を具体的に>

.. _<LABEL_NAME>_next:

次の文書
========

- :ref:`<TUTORIAL_PAGE_TITLE> <<TUTORIAL_PAGE_LABEL>>` — <WHY_TUTORIAL: 段階的に学びたい読者への理由>
