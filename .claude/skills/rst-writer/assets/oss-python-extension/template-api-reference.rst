.. _<LABEL_NAME>:

.. authoring: api-reference 用。
   対象の公開 API を、確認した仕様どおりに記述する構成。
   <UPPER_SNAKE_CASE> は具体値または具体的な文へ置換し、このコメントを除く。
   見出し・本文は入力の language に合わせ、先頭ラベルは出力ファイル stem を基本に一意にする。
   optional-start/end の範囲は採用時に境界コメントだけを、非採用時はラベル・見出し・本文・参照を含む範囲全体を除く。
   :ref: の target は参照先文書の実在ラベルを確認して置き換える。
   関連項目の参照は対象ごとに1種類だけ選び、Python domain 等で定義済みの object は
   :py:func: 等の domain role、明示ラベルを持つページ・節は :ref:、どちらもなければ literal にする。
   用語・CLI option・環境変数など他の対象は sphinx-semantic-markup.md の
   対象別の選択表にある role を1種類だけ選ぶ。
   記述の前に実ソース（公開 API 一覧・signature・docstring）・conf.py・依存制約・既存文書の正本定義を確認し、
   有効な拡張を記録する。
   signature・型・default・例外・版番号は確認した値だけを書く。
   :type: / :rtype: / :raises: の値と signature の引数・戻り値の型注釈は py:class / py:exc の参照を生成するため、
   autodoc が docstring から生成するこれらのフィールドも含めて、組み込みの型・例外か対象 docs 内の定義、
   または有効な intersphinx inventory で -n の参照が解決することを確認する。
   解決できない確認済みの値はフィールドや signature の注釈に残さず、通常の説明文で literal として記す。
   長い Tutorial は既存ページの実在ラベルへ案内し、このページに複写しない。
   API が複数ある場合は「API」節の対象単位を複製し、ラベルを一意にする。
   対象は function に限らない。
   対象 object に合う py directive / auto directive（py:class・autoclass 等）を選ぶ。
   定義ブロックは対象ごとに次のいずれか1つだけを選び、同じ object を二重定義しない。
   - 既に正本定義がある: define-reference の範囲に正本への参照と必要な補足だけを書き、
     定義ブロックを新設しない。
     正本が semantic 定義なら :py:func: 等の domain role、明示ラベルの定義なら :ref: で参照する。
   - autodoc が有効で対象を import でき、生成される signature の注釈と docstring の情報フィールドの参照がすべて解決する:
     autofunction 等を使い、短い人手の説明を添える。
   - autodoc が無効、または生成される signature の注釈か docstring の情報フィールドに解決できない参照がある（正本もない）:
     手書きの py directive で定義する。
     autodoc を新たに有効化しない。
   - Python domain の記法が使えない: 明示ラベル + 小見出し + literal signature + フィールド/表で同じ仕様を記す。
   - API が存在しない・情報が足りない・import が未解決: 不足・失敗を明示して報告する。
     架空の signature、mock、警告抑制で成功にしない。
   autosummary を使う場合も拡張が有効な環境だけで短い一覧に留め、新しい :toctree: や stub 生成は起こさない。
   napoleon・viewcode・intersphinx は対象環境で既に有効な場合に限り、その解釈・リンク・外部参照を利用する。
   これらを有効化する手順や conf.py 変更をこのページに書かない。
   外部 object は inventory に項目が実在する場合だけ semantic で参照し、なければ確認済み URL または literal にする。
   版情報は対象の定義ブロック内の version-info 範囲に置き、versionchanged / deprecated も
   確認できた場合は同じ位置に追加する。
   fallback では対象を定義する object directive がないため version directive を使わず、
   version-info 範囲に :版: フィールドで確認できた版を書く。
   版情報が確認できない場合は版を示す行と空の版節を残さず、不明であることを作業報告へ記録する。
   inline 記法の境界空白は記述時点で正しく入れる。
   バッククォートが隣接する箇所や literal 内の role 記法では split guard により
   --fix が拒否または部分適用になり得るため、修正後は同じ検査の再実行で残存違反を確認する

================
<DOCUMENT_TITLE>
================

<INTRO_TEXT: このページが扱う API の範囲を1-2文で>

.. _<LABEL_NAME>_spec:

API
===

.. optional-start: define-reference

<REFERENCE_AND_NOTE: :py:func:`<QUALIFIED_PUBLIC_API>` 等の domain role または :ref:`<TITLE> <<LABEL>>` で正本を参照し、
必要な補足だけを確認した範囲で書く。
定義ブロックは新設しない>

.. optional-end: define-reference

.. optional-start: define-autodoc

.. autofunction:: <QUALIFIED_PUBLIC_API>

   <DESCRIPTION: docstring を補う短い説明。確認した範囲で>

   .. optional-start: version-info

   .. versionadded:: <CONFIRMED_VERSION>

   .. optional-end: version-info

.. optional-end: define-autodoc

.. optional-start: define-py

.. py:function:: <CONFIRMED_SIGNATURE>

   <PURPOSE: API の用途を確認した範囲で>

   :param <PARAMETER_NAME>: <PARAMETER_MEANING>
   :returns: <RETURN_VALUE_MEANING>
   :rtype: <CONFIRMED_RETURN_TYPE>

   .. optional-start: raises

   :raises <CONFIRMED_EXCEPTION>: <RAISE_CONDITION>

   .. optional-end: raises

   .. optional-start: version-info

   .. versionadded:: <CONFIRMED_VERSION>

   .. optional-end: version-info

.. optional-end: define-py

.. optional-start: define-fallback

.. _<LABEL_NAME>_<API_KEY>:

<API_NAME>
----------

構文 ::

    <CONFIRMED_SIGNATURE>

:引数: <PARAMETERS_MEANING>
:戻り値: <RETURN_VALUE_MEANING>

.. optional-start: raises

:例外: <RAISE_CONDITION>

.. optional-end: raises

<PURPOSE: API の用途を確認した範囲で>

.. optional-start: version-info

:版: <CONFIRMED_VERSION>

.. optional-end: version-info

.. optional-end: define-fallback

.. _<LABEL_NAME>_example:

使用例
======

<EXAMPLE_INTRO: どんな呼び出しかを1文で>

.. code-block:: python

   <USAGE_EXAMPLE: 結果をソースまたは呼び出しで確認した短い例>

.. _<LABEL_NAME>_related:

関連項目
========

- <RELATED_REF_1> — <WHY_RELATED: この API と関係する理由>
