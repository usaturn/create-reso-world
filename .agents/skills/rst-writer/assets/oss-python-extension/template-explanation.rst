.. _<LABEL_NAME>:

.. authoring: explanation 用。読者が仕組みと選択理由を理解する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   作業順の羅列にせず、問い→構造→理由→他方式との差の順で説明する。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: この文書が答える問いを1-2文で>

.. _<LABEL_NAME>_question:

問い
====

<QUESTION_TEXT: 読者が抱く問い・知りたいことを具体的に>

.. _<LABEL_NAME>_structure:

構造
====

<STRUCTURE_TEXT: 入力から変換・出力までの流れを説明する>

.. code-block:: rst

   <STRUCTURE_RST_EXAMPLE>

<EXAMPLE_INTERPRETATION: 上の例の各部分が何を意味するか>

.. _<LABEL_NAME>_rationale:

設計の理由
==========

<RATIONALE_TEXT: この構造・方式を選んだ理由を説明する>

.. _<LABEL_NAME>_alternatives:

他方式との違い
==============

.. list-table::
   :header-rows: 1
   :widths: 2 3 3

   * - <ASPECT_HEADER: 観点>
     - <THIS_APPROACH_HEADER: この方式>
     - <ALTERNATIVE_HEADER: 他方式>
   * - <ASPECT_1>
     - <THIS_1>
     - <ALTERNATIVE_1>
   * - <ASPECT_2>
     - <THIS_2>
     - <ALTERNATIVE_2>

<TRADEOFF_TEXT: 比較から分かるトレードオフと、この方式が向く条件を1-2文で>

.. _<LABEL_NAME>_related:

関連する文書
============

- :ref:`<TUTORIAL_PAGE_TITLE> <<TUTORIAL_PAGE_LABEL>>` — <WHY_TUTORIAL: 実際に手を動かして学ぶ読者への理由>
- :ref:`<RELATED_SECTION_TITLE> <<RELATED_SECTION_LABEL>>` — <WHY_RELATED: 主題と関係する理由>
