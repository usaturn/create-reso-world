# create-reso-world profile

`profile=create-reso-world`（省略時の既定）に適用する。このリポジトリで RST の文書を書くときの profile である。
RST の構造とラベルは [共通 guide](../rst-core-style-guide.md)、入力と root の解決は [入力仕様](../profile-interface.md) を読む。

## 出力先

- 新規で `target_path` を省略した場合は、リポジトリのルートの `docs_draft/<目的に合う名前>.rst` に置く。`docs_draft/` は git が追跡しないローカルの下書き置き場である（ルート `AGENTS.md` の「ファイルとドラフト」）
- 明示された `target_path` は、新規・既存とも尊重する。相対パスはリポジトリのルート基準で解決する（プロジェクトを cwd にしている場合も同じ）
- 下書きを `docs/` などの追跡される場所へ移すかは依頼者が決める。この profile は勝手に移さない

## 言語と文書構造

既定は日本語・である調とし、明示された `language` を優先する。日本語の文書は、ルート `AGENTS.md` の「日本語表現」に従う。
[文書種別表](../document-types.md) の template を使い、タイトル直後の「概要」で目的を1〜3文で述べ、最終行に装飾なしで単独の「以上」を置く。
他言語ではこの役割に相当する見出しと終端を指定言語で書く（英語なら `Overview` と `End`）。
procedure は前提条件・手順の流れ・手順・結果確認、explanation は概念・構造・比較・関連資料を軸にする。
operational は procedure の簡易版で、前提条件と手順の流れを省略できる。
template の欄は必要な内容で置き換え、無関係な節や未確認の関連 URL を埋め草として残さない。
既存編集は指定箇所の追記・修正を優先し、template で文書全体を置換しない。
句点「。」の直後で改行し、桁数を理由に文の途中を折り返さない。

## コマンドとコード

コマンドの前には、実行の意図を動詞で説明する。
シェルは zsh を前提にし、bash スクリプトの実行など bash が必要な場面だけ bash と書く。
Python の実行例は `uv run` で書き、`python3` を直接書かない。
コードは `::` のリテラルブロックで書く。言語が明確なら `.. code-block:: <言語>`（`bash`、`zsh`、`python`、`json`、`toml`、`text` など）を使ってよい。

## Sphinx を使わない

このリポジトリには Sphinx の build も用語集も無い。docutils だけで解釈できる記法で書く。

- 用語集（`glossary`）を探したり、作成・照合・追記したりしない。専門用語はその場で説明するか、箇条書きやフィールドリストで定義する
- `:ref:`、`:term:`、`:doc:` などの Sphinx の role と、`.. mermaid::` などの Sphinx 拡張の directive は使わない。図が要る場合は表や箇条書きで表す
- 共通 guide のページ・節ラベルの付け方はそのまま守る。同じページの節への参照は、docutils の名前付き参照（`` `結果確認 <page_label_results_>`_ ``）で書く。別のファイルは、リポジトリのルート基準のパスと表示名を本文に書いて示す

## 検査

作成・編集した RST の絶対パスを `TARGET` として、docutils と rstcheck で構文を検査する。
検査用の Python project は作らず、依存も追加しない。

```sh
uv run --no-project --with docutils --with rstcheck rstcheck --report-level warning "$TARGET"
```

- 終了コード 0 と `Success! No issues detected.` を確認する。`--report-level warning` を付けるのは、参照されていないラベルなどの INFO を失敗として数えないためである
- 失敗したら本文を直して再実行する。未実行や失敗した検査を成功と報告しない
- 共通 guide の4段階の静的検査（`wabun-rst-ulint`）は、この profile では実行しない。`LINT_PROJECT` を持たないためである。報告では、rstcheck による構文検査だけを行ったと明記する
- Sphinx build は行わない

## 報告

対象パス（リポジトリのルート基準と絶対パス）、実行した検査のコマンド・終了コード・出力の最終行、未実行の検査を報告する。
