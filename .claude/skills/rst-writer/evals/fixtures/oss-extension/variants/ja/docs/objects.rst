.. _objects:

オブジェクトリファレンス
========================

Queue Extension のオブジェクトの正本定義である。
他のページはこれらの項目へリンクし、再定義しない

Python API
----------

.. py:module:: queue_ext

.. py:function:: format_badge(name, prefix='task')
   :module: queue_ext

   キュー名の表示用バッジを返す

   :param name: 空文字・空白のみを許さないキュー名
   :type name: str
   :param prefix: バッジの接頭辞
   :type prefix: str
   :returns: ``prefix:name`` 形式のバッジ
   :rtype: str
   :raises ValueError: ``name`` が空または空白のみの場合

   .. versionchanged:: 0.2.0
      ``prefix`` 引数を追加した。

.. py:function:: setup(app)
   :module: queue_ext

   Sphinx 拡張のエントリポイントとして設定値と ``queue-summary`` directive と ``queue-name`` role を登録する

.. py:function:: main(argv=None)
   :module: queue_ext

   キュー集計を確認するコンソールエントリポイント

設定値
------

.. confval:: queue_limit
   :type: ``int``
   :default: ``3``

   Sphinx 設定値として登録されるが、現在の ``queue-summary`` directive は参照しない

.. confval:: queue_prefix
   :type: ``str``
   :default: ``'task'``

   Sphinx 設定値として登録されるが、バッジ表示は参照しない

マークアップ
------------

.. rst:directive:: queue-summary

   1つのキューのエントリを集計して表示する

   .. rst:directive:option:: max-items
      :type: integer

      先頭 ``max-items`` 件まで表示を制限する。
      既定は ``3`` である

.. rst:role:: queue-name

   キュー名をインラインリテラルで表示する

コマンドライン
--------------

.. program:: queue-ext

.. option:: --limit N

   集計の表示を ``N`` 件に制限する。

環境変数
--------

.. envvar:: QUEUE_EXT_DEBUG

   設定すると ``queue-ext`` コマンドのデバッグログを有効にする。
