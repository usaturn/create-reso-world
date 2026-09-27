.. _<LABEL_NAME>:

.. authoring: changelog 用。既存 Changelog の形式がある場合、この骨組みへ置き換えない。
   既存の版見出し・日付・分類・順序・ラベルを保ち、依頼された変更だけを追加する。
   以下は既存形式がないときの出発点。変更内容に不要なコード補足・移行参照は除く。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   変更種別の固定一覧や特定の分類形式は強制しない。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。
   版を追加するときは <RELEASE_ID> を変えて節ラベルごと版の単位を複製し、新しい版を先に置く。

==================
<DOCUMENT_TITLE>
==================

.. _<LABEL_NAME>_<RELEASE_ID>:

<VERSION> — <DATE>
==================

<RELEASE_SUMMARY: この版の位置付けを1文で（不要なら除く）>

.. _<LABEL_NAME>_<RELEASE_ID>_changes:

変更事項
--------

- <CHANGE_1>
- <CHANGE_2>

.. optional-start: change-example

.. _<LABEL_NAME>_<RELEASE_ID>_change_example:

変更例
------

.. code-block:: python

   <CHANGED_CONFIGURATION>

.. optional-end: change-example

.. optional-start: migration-note

.. _<LABEL_NAME>_<RELEASE_ID>_migration_note:

移行について
------------

<MIGRATION_NOTE_TEXT: 移行が必要な変更と、利用者が取るべき対応を1-2文で>

- :ref:`<MIGRATION_PAGE_TITLE> <<MIGRATION_PAGE_LABEL>>` — <WHY_MIGRATION>

.. optional-end: migration-note
