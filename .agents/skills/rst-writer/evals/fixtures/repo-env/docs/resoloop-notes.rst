.. _resoloop_notes:

====================
ResoLoop の版の扱い
====================

.. _resoloop_notes_overview:

概要
====

導入する ResoLoop の版をロックファイルで決める理由と、版を変えるときの流れを示す。

.. _resoloop_notes_lock:

ロックファイル
==============

``.devcontainer/resoloop.lock`` が導入する版の正本である。
手元の導入だけを変えると、コンテナを作り直したときにロックの版へ戻る。

.. 評価用のコメント行。編集後も残ること。

.. _resoloop_notes_update:

更新の手順
==========

#. 新しい版を確かめる ::

       resoloop --version

.. _resoloop_notes_out_of_scope:

対象外の節
==========

fork のビルド手順は ``docs/resoloop-fork-workflow.md`` にある。

以上
