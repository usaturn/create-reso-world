---
name: rst-writer
description: Use when creating or editing a single reStructuredText (.rst) document, including a procedure, explanation, or short operational guide. 文書群全体の構成ではなく、単一の RST ページの作成・追記・修正が対象。
---

# RST の作成・編集

単一ページを、入力仕様と選択した profile に従って書く。
現在利用可能なのは、このリポジトリの文書を書く **create-reso-world** の3種である。OSS Python Extension は予約仕様であり、生成には使えない。

## 入力を確認する

最初に [profile-interface.md](references/profile-interface.md) と [document-types.md](references/document-types.md) を読む。
`profile` / `document_type` / `target_path` / `language`、任意の `audience` / `package_name` を受け取る。
自然言語依頼も同じ仕様で整理し、明示値を推論・既定値より優先する。

入力仕様の順に、明示値の整合、必要情報、profile の利用可能性、root と変更対象、必要なリソースを確認する。
省略時の `profile` は `create-reso-world`。空値や未知値を省略扱いしない。
不足・不整合・未接続・リソースの欠落では、具体的な問題と必要な次の入力を返し、文書生成・検査を行わない。

## 利用可能なリソースを読む

create-reso-world の確認を通った場合だけ、以下を読む。

1. [共通 RST guide](references/rst-core-style-guide.md): ページ・節ラベル、構造、参照、表・リスト、インライン記法
2. [create-reso-world profile](references/profiles/create-reso-world.md): 出力先、文体、コード、Sphinx を使わない書き方、検査
3. [文書種別表](references/document-types.md) が指定する `assets/create-reso-world/` の template

`procedure` と `operational` は手順書 template、`explanation` は解説書 template を使う。
既存編集では指定ファイルを読み、その内容を保持して依頼の変更を加える。

## 作成・編集と検査

1. 確定した言語・種別・対象パスに従って作成または編集する。
   新規・出力先省略時の draft は、リポジトリのルート（`git rev-parse --show-toplevel`）の `docs_draft/` に置く。
2. 用語集は探さず、作成・照合もしない。専門用語はその場で説明する。
3. 作成・編集した RST の絶対パスに、profile の検査 `uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning` を実行する。
4. 最終差分と終了値を確認し、対象パスと、実行した検査と結果を報告する。
   解決したリポジトリのルートと cwd を記録し、未実行・失敗・不足を区別する。

## 取り違えやすい点

| 状況 | 判断 |
|---|---|
| ワールドのプロジェクト（`slum02/` など）を cwd にして呼び出された | draft の置き場はリポジトリのルートの `docs_draft/` である |
| 出力先や言語が明示された | profile の既定値で置換しない |
| OSS 用ファイルが存在する | 種別表が reserved の間は未接続として停止する |
| `:ref:` や `:term:` を使いたくなった | Sphinx は無い。profile の「Sphinx を使わない」に従う |
