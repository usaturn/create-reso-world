.. _<LABEL_NAME>:

.. authoring: tutorial 用。読者が段階的に学びながら完成させる構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   各段階は「やること→実行→観察できる結果」の順にし、作業手順だけの羅列にしない。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: このチュートリアルで作るものと学ぶことを1-2文で>

.. _<LABEL_NAME>_goal:

学習目標
========

- <LEARNING_GOAL_1>
- <LEARNING_GOAL_2>

.. _<LABEL_NAME>_prerequisites:

前提
====

- <PREREQUISITE_1: 例 導入文書の完了>
- <PREREQUISITE_2: 必要な知識・設定>

.. _<LABEL_NAME>_first_result:

最初の成果
==========

<FIRST_STEP_TEXT: 何を作るかを1-2文で>

.. code-block:: rst

   <FIRST_RST_EXAMPLE>

.. code-block:: console

   <FIRST_RUN_COMMAND>

<FIRST_OBSERVATION: この段階で観察できる結果を具体的に>

.. _<LABEL_NAME>_extend:

拡張する
========

<EXTEND_STEP_TEXT: 次に何を足すかを1-2文で>

.. code-block:: rst

   <EXTEND_RST_EXAMPLE>

.. code-block:: console

   <EXTEND_RUN_COMMAND>

<SECOND_OBSERVATION: 拡張後に変わる点・見える差を具体的に>

.. optional-start: extra-practice

.. _<LABEL_NAME>_extra_practice:

追加の練習
==========

<PRACTICE_TASK_AND_EXPECTED_OBSERVATION: 練習課題と期待される観察>

.. optional-end: extra-practice

.. _<LABEL_NAME>_reflect:

振り返りと次の学習
==================

<REFLECT_TEXT: このチュートリアルでできたこと・覚えた書き方を1-2文で>

- :ref:`<HOW_TO_PAGE_TITLE> <<HOW_TO_PAGE_LABEL>>` — <WHY_HOW_TO: 特定の作業を短時間で終えたい読者への理由>
