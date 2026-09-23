.. _<LABEL_NAME>:

.. authoring: troubleshooting 用。読者が症状から復旧し確認する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   症状が複数ある場合は <SYMPTOM_N_ID> を変えて、節ラベルごと「症状→原因と確かめ方→対処→確認」の単位を複製する。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: このページで扱う症状の範囲を1-2文で>

.. _<LABEL_NAME>_<SYMPTOM_1_ID>:

<SYMPTOM_1_TITLE>
=================

.. _<LABEL_NAME>_<SYMPTOM_1_ID>_symptom:

症状
----

.. code-block:: text

   <SYMPTOM_MESSAGE: 警告やエラーの出力例>

<WHEN_IT_OCCURS: 症状が現れる条件・操作>

.. _<LABEL_NAME>_<SYMPTOM_1_ID>_cause:

原因と確かめ方
--------------

<CAUSE_TEXT: 考えられる原因と、その切り分け方・確認箇所>

.. _<LABEL_NAME>_<SYMPTOM_1_ID>_remedy:

対処
----

<REMEDY_TEXT: 何をどう修正するか>

.. code-block:: python

   <REMEDY_CONFIG_EXAMPLE>

.. _<LABEL_NAME>_<SYMPTOM_1_ID>_verify:

確認
----

.. code-block:: console

   <VERIFY_COMMAND>

<RESOLVED_CONDITION: 解消したと判断する観察結果を具体的に>

.. _<LABEL_NAME>_related:

関連する設定
============

- :ref:`<RELATED_SECTION_TITLE> <<RELATED_SECTION_LABEL>>` — <WHY_RELATED: 症状と関係する理由>
