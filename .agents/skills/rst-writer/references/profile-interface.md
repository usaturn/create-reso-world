# 執筆入力と profile の仕様

単一 RST の作成・編集を依頼するための情報である。Python API や CLI を追加するものではない。
文書種別とリソースの対応は [document-types.md](document-types.md) を正本とする。

## 6つの入力

呼び出し元の明示値を、依頼内容からの推論や profile の既定値より優先する。
明示値同士が矛盾するときは一方を選ばず、書き込み前に必要な判断を返す。

| 入力名 | create-reso-world | OSS Python Extension（予約仕様） |
|---|---|---|
| `profile` | **省略時だけ** `create-reso-world` | 明示値 `oss-python-extension`。現在は未接続 |
| `document_type` | 明示値を優先。省略時は依頼から procedure / explanation / operational のいずれかに一意に判断できれば採用、曖昧なら確認 | 必須。種別表の14値から指定 |
| `target_path` | 新規・省略時はリポジトリのルートの `docs_draft/<目的に合う名前>.rst`。明示値は新規・既存とも尊重 | 必須。出力先を推測したり create-reso-world の既定先に置換したりしない |
| `language` | 省略時 `ja`。明示言語で執筆する | 必須。明示言語と対象設定が矛盾すれば報告 |
| `audience` | 任意。説明の粒度と用語の選択に反映 | 同左 |
| `package_name` | 任意。依頼と確認済みの資料に基づく | 同左。内容に必要なら不足を報告 |

`profile` / `document_type` / `target_path` / `language` に明示された空文字・空白だけ・null は不足情報であり、省略時の既定値へ変換しない。
未知の profile/type も省略とは扱わない。未確認のパッケージ名、バージョン対応、設定値を捏造しない。
任意値がなくても内容を確定できれば進め、内容に必要な情報が足りなければ具体的に確認する。

## 書き込み前の確認順

生成・既存編集・検査は、次の全段階を通ったあとに行う。

1. **明示値と組み合わせ**: 受け取った値と自然言語の条件を整理し、profile/type の組を種別表で確認する。
   たとえば `target_path=a.rst` と「b.rst を編集」が併記されていれば不整合である。
2. **必要な情報**: 空値、曖昧な種別、OSS の必須値不足を特定する。
   create-reso-world の省略可能な値だけを推論・既定値で補い、補った値を記録する。
3. **利用可能性**: 現在 available なのは `create-reso-world` だけである。
   `oss-python-extension` は未接続と報告して停止する。必須値不足があればその項目も併記する。
   OSS 用ファイルが一部または全部存在していても、種別表が reserved の間は有効化しない。
4. **root と変更対象**: 次節に従って絶対パスを確定し、編集対象と検査対象を区別する。
5. **必要なリソース**: 共通 guide、選択 profile、対応 template の実在を確認する。
   不足したリソースを別 profile のリソースで代用しない。
   OSS profile では、対象 project の `needs_sphinx`・依存の Sphinx 制約のいずれかが 9.1 未満を許す場合、または実行中の Sphinx が 9.1 未満の場合も対象外として停止する（判定は OSS profile を正本とする）。

途中で不足・未知値・不整合・未接続・リソースの欠落が分かった場合は、ファイル作成や検査（lint の `--fix` や `.bak` 作成を含む）へ進まない。
受け取った値、具体的な不足または不整合、次に必要な入力・修復を報告する。
OSS の停止時は create-reso-world のリソースを読み込んで代替生成しない。

## create-reso-world の root と変更対象

リポジトリのルート `REPO_ROOT` は `git rev-parse --show-toplevel` で求める。ワールドのプロジェクト（`slum02/` など）を cwd にしていても、同じルートが返る。
`external/resoloop` は別のリポジトリであり、その中の文書はこの profile の対象外として書く前に確認する。

| 依頼 | 編集先 |
|---|---|
| 新規で `target_path` 省略 | `REPO_ROOT/docs_draft/` の目的に合うファイル |
| 明示された既存文書の追記・修正 | 指定ファイル |
| 新規で `target_path` 明示 | 指定先 |

相対 `target_path` は `REPO_ROOT` 基準で解決する（ルート `AGENTS.md` の冒頭にある規則と同じ）。
解決した絶対パス、cwd、`REPO_ROOT` を記録する。
symlink は実体の行き先まで確認する。リポジトリの外へ出る、候補が複数、または「既存編集」の対象が不存在なら、書く前に確認する。
新規作成先に既存ファイルがあれば無断で置換せず、依頼がその編集を許可しているか確認する。

### 変更するファイルを限定する

既存編集では最初に対象の内容を読み、指定された変更を加える。指定外の文・ラベルを保持する。
非対象の `docs_draft/` は参考資料として読まない。明示された資料・編集対象は読める。
変更してよいのは対象の1ファイルだけである。別の docs、設定、依存を便乗編集しない。
参照先ラベルの追加に指定外ファイルの編集が必要なら、その追加作業を不足として報告する。
検査の対象は今回作成・編集した RST だけである。

## リソースの参照先

- 共通: [RST core](rst-core-style-guide.md)
- create-reso-world: [profile](profiles/create-reso-world.md)、[文書種別表](document-types.md) の実在 template
- OSS 予約: `references/profiles/oss-python-extension.md`、`references/sphinx-semantic-markup.md`、`assets/oss-python-extension/`。未接続なので読み込み・生成には進まない

OSS profile は自身の root と検証 project を定義する。create-reso-world の配置を他 profile の既定にはしない。
