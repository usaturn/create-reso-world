---
name: rst-writer
description: Use when creating or editing a single reStructuredText (.rst) document, including a procedure, explanation, or short operational guide. 文書群全体の構成ではなく、単一の RST ページの作成・追記・修正が対象。
---

# RST の作成・編集

単一ページを、入力仕様と選択した profile に従って書く。
現在利用可能なのは **MaatLog** の3種である。OSS Python Extension は予約仕様であり、#393 の統合までは生成に使えない。

## 入力を確認する

最初に [profile-interface.md](references/profile-interface.md) と [document-types.md](references/document-types.md) を読む。
`profile` / `document_type` / `target_path` / `language`、任意の `audience` / `package_name` を受け取る。
自然言語依頼も同じ仕様で整理し、明示値を推論・既定値より優先する。

入力仕様の順に、明示値の整合、必要情報、profile の利用可能性、root と変更対象、必要なリソースを確認する。
省略時の `profile` は `maatlog`。空値や未知値を省略扱いしない。
不足・不整合・未接続・リソースの欠落では、具体的な問題と必要な次の入力を返し、文書生成・用語集更新・lint を行わない。

## 利用可能なリソースを読む

MaatLog の確認を通った場合だけ、以下を読む。

1. [共通 RST guide](references/rst-core-style-guide.md): ページ・節ラベル、構造、参照、表・リスト、インライン記法、4段階の静的検査
2. [MaatLog profile](references/profiles/maatlog.md): 文体、出力先、用語集、コード・図、検査方針
3. [文書種別表](references/document-types.md) が指定する `assets/maatlog/` の template

`procedure` と `operational` は手順書 template、`explanation` は解説書 template を使う。
既存編集では指定ファイルを読み、その内容を保持して依頼の変更を加える。

## 作成・編集と検査

1. 確定した言語・種別・対象パスに従って作成または編集する。
   新規・出力先省略時の draft は選択した **親 checkout** の `docs_draft/` に置く。
2. MaatLog profile に従って本文の全出現の専門用語をマークし、選択した **公開 checkout** の `docs/glossary.rst` と照合する。
   今回本文で使った未定義語だけ既存用語集へ追記する。
3. 公開 checkout を uv project に指定し、作成・編集した RST の絶対パスに共通 guide の4検査を実行する。
   用語集にも同じ検査を行うのは、今回用語集を編集した場合だけである。
4. 最終差分と終了値を確認し、対象パス、用語集の変更有無、実行した検査と結果を報告する。
   解決した親 root・公開 root・cwd・uv project を記録し、未実行・失敗・不足を区別する。

## 取り違えやすい点

| 状況 | 判断 |
|---|---|
| 親 cwd から呼び出された | draft の親 root と用語集・lint の公開 root を分けて確認する |
| 出力先や言語が明示された | profile の既定値で置換しない |
| OSS 用ファイルが存在する | 種別表が reserved の間は統合待ちで停止する |
| 旧 guide を指定された | [移行案内](references/rst-style-guide.md) から共通 guide と MaatLog profile を読む |
