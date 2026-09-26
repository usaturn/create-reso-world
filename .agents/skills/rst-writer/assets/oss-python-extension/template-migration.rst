.. _<LABEL_NAME>:

.. authoring: migration 用。読者が対象版から移行する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   Before/After は変更の対応が分かる順に並べ、非推奨開始版と削除版を区別する。
   外部 sample が入力にある場合は code-block の代わりに次を使える。
   .. literalinclude:: <SAMPLE_PATH>
      :language: <CODE_LANGUAGE>
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。

==================
<DOCUMENT_TITLE>
==================

<INTRO_TEXT: 何の版から何の版への移行かを1-2文で>

.. _<LABEL_NAME>_versions:

対象バージョン
==============

- 移行元: <FROM_VERSION>
- 移行先: <TO_VERSION>

.. _<LABEL_NAME>_impact:

影響
====

<IMPACT_TEXT: 何が変わり、どの利用者・設定に影響するか>

.. _<LABEL_NAME>_before_after:

Before / After
==============

移行前（<FROM_VERSION>）:

.. code-block:: python

   <BEFORE_CONFIG_EXAMPLE>

移行後（<TO_VERSION>）:

.. code-block:: python

   <AFTER_CONFIG_EXAMPLE>

.. _<LABEL_NAME>_steps:

変更手順
========

#. <MIGRATION_STEP_1: 設定・コードの変更>

#. <MIGRATION_STEP_2: パッケージの更新>

   .. code-block:: console

      <UPDATE_COMMAND>

#. <MIGRATION_STEP_3: 再構築・再実行>

.. _<LABEL_NAME>_verify:

移行確認
========

.. code-block:: console

   <VERIFY_COMMAND>

<MIGRATED_CONDITION: 移行が完了したと判断する観察結果を具体的に>

.. _<LABEL_NAME>_deprecations:

非推奨と削除
============

- <DEPRECATED_ITEM_1>: <DEPRECATED_IN_VERSION> で非推奨、<REMOVED_IN_VERSION> で削除。後継は <SUCCESSOR_NAME>

.. _<LABEL_NAME>_related:

関連する文書
============

- :ref:`<CHANGELOG_PAGE_TITLE> <<CHANGELOG_PAGE_LABEL>>` — <WHY_CHANGELOG: 版ごとの変更一覧への理由>
- :ref:`<RELATED_SECTION_TITLE> <<RELATED_SECTION_LABEL>>` — <WHY_RELATED>
