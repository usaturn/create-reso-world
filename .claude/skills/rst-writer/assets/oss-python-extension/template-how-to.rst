.. _<LABEL_NAME>:

.. authoring: how-to 用。読者が特定の作業を終えるための構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   目的に直結する手順だけを書き、基礎概念の長い説明は含めない。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: この作業で達成することを1-2文で>

.. _<LABEL_NAME>_outcome:

達成条件
========

<TARGET_OUTCOME: 完了したと判断できる状態を具体的に>

.. _<LABEL_NAME>_prerequisites:

前提
====

- <PREREQUISITE_1: 既存状態・導入済みなど>
- <PREREQUISITE_2: 必要な権限・知識など>

.. _<LABEL_NAME>_steps:

手順
====

#. <STEP_1: 何をするかを1文で>

   .. code-block:: python

      <STEP_1_CODE_EXAMPLE>

#. <STEP_2: 次に何をするかを1文で>

   .. code-block:: console

      <STEP_2_COMMAND>

.. _<LABEL_NAME>_verify:

完了確認
========

<VERIFY_INTRO: 何を確認するかを1文で>

.. code-block:: console

   <VERIFY_COMMAND>

<COMPLETION_CONDITION: 達成条件を満たしたと判断できる観察結果を具体的に>

.. _<LABEL_NAME>_related:

関連する設定
============

- :ref:`<RELATED_SECTION_TITLE> <<RELATED_SECTION_LABEL>>` — <WHY_RELATED: この作業と関係する理由>
