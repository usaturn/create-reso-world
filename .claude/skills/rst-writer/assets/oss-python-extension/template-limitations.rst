.. _<LABEL_NAME>:

.. authoring: limitations 用。読者が適用できる範囲を判断する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   対応しないものと「確認していない」ものを区別し、制約は現れる条件が分かる例で示す。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: 対象と、この文書が示す適用範囲を1-2文で>

.. _<LABEL_NAME>_unsupported:

非対応の対象
============

- <UNSUPPORTED_1: 対応しない機能・出力・環境>
- <UNSUPPORTED_2>

.. _<LABEL_NAME>_compatibility:

互換性
======

<COMPATIBILITY_TEXT: 動作を確認済みの版・環境とその範囲>

- <CONFIRMED_REQUIREMENT_1>
- <CONFIRMED_REQUIREMENT_2>

<UNVERIFIED_NOTE: 確認していない範囲。「非対応」とは区別して未確認と明記する>

.. _<LABEL_NAME>_conflicts:

競合
====

<CONFLICT_TEXT: 競合する対象と、競合が起きる条件>

- <CONFLICT_1_AND_CONDITION>

.. _<LABEL_NAME>_constraints:

技術的制約
==========

<CONSTRAINT_TEXT: 技術的な理由による制約を1-2文で>

.. code-block:: rst

   <CONSTRAINT_BOUNDARY_EXAMPLE: 制約が現れる条件を示す例>

<CONSTRAINT_DETAIL: なぜその条件で制約になるか>

.. _<LABEL_NAME>_workaround:

回避策と関連文書
================

- <WORKAROUND_1: 適用可能な回避策と、それが使える条件>

関連する文書:

- :ref:`<RELATED_SECTION_TITLE> <<RELATED_SECTION_LABEL>>` — <WHY_RELATED>
