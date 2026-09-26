# 執筆入力と profile の仕様

単一 RST の作成・編集を依頼するための情報である。Python API や CLI を追加するものではない。
文書種別とリソースの対応は [document-types.md](document-types.md) を正本とする。

## 6つの入力

呼び出し元の明示値を、依頼内容からの推論や profile の既定値より優先する。
明示値同士が矛盾するときは一方を選ばず、書き込み前に必要な判断を返す。

| 入力名 | MaatLog | OSS Python Extension（予約仕様） |
|---|---|---|
| `profile` | **省略時だけ** `maatlog` | 明示値 `oss-python-extension`。現在は未接続 |
| `document_type` | 明示値を優先。省略時は依頼から procedure / explanation / operational のいずれかに一意に判断できれば採用、曖昧なら確認 | 必須。種別表の14値から指定 |
| `target_path` | 新規・省略時は選択した親の `docs_draft/<目的に合う名前>.rst`。明示値は新規・既存とも尊重 | 必須。出力先を推測したり MaatLog の既定先に置換したりしない |
| `language` | 省略時 `ja`。明示言語で執筆する | 必須。明示言語と対象設定が矛盾すれば報告 |
| `audience` | 任意。説明の粒度と用語の選択に反映 | 同左 |
| `package_name` | 任意。依頼と確認済みの資料に基づく | 同左。内容に必要なら不足を報告 |

`profile` / `document_type` / `target_path` / `language` に明示された空文字・空白だけ・null は不足情報であり、省略時の既定値へ変換しない。
未知の profile/type も省略とは扱わない。未確認のパッケージ名、バージョン対応、設定値を捏造しない。
任意値がなくても内容を確定できれば進め、内容に必要な情報が足りなければ具体的に確認する。

## 書き込み前の確認順

生成・既存編集・用語集更新・lint は、次の全段階を通ったあとに行う。

1. **明示値と組み合わせ**: 受け取った値と自然言語の条件を整理し、profile/type の組を種別表で確認する。
   たとえば `target_path=a.rst` と「b.rst を編集」が併記されていれば不整合である。
2. **必要な情報**: 空値、曖昧な種別、OSS の必須値不足を特定する。
   MaatLog の省略可能な値だけを推論・既定値で補い、補った値を記録する。
3. **利用可能性**: 現在 available なのは `maatlog` だけである。
   `oss-python-extension` は #393 の統合待ちと報告して停止する。必須値不足があればその項目も併記する。
   OSS 用ファイルが一部または全部存在していても、この表が reserved の間は有効化しない。
4. **root と変更対象**: 次節に従って所属 repository と絶対パスを確定し、編集対象・用語集・検査対象を区別する。
5. **必要なリソース**: 共通 guide、選択 profile、対応 template、対象 project と用語集の実在を確認する。
   不足したリソースを別 profile のリソースで代用しない。
   OSS profile では、対象 project の `needs_sphinx`・依存の Sphinx 制約のいずれかが 9.1 未満を許す場合、または実行中の Sphinx が 9.1 未満の場合も対象外として停止する（判定は OSS profile を正本とする）。

途中で不足・未知値・不整合・未接続・リソースの欠落が分かった場合は、ファイル作成、用語集更新、lint（`--fix` や `.bak` 作成を含む）へ進まない。
受け取った値、具体的な不足または不整合、次に必要な入力・修復を報告する。
OSS の停止時は MaatLog のリソースを読み込んで代替生成しない。

## MaatLog の root と所有関係

以下は内部で解決する名前であり、呼び出し入力を増やすものではない。

| 内部名 | 意味 |
|---|---|
| `ENV_ROOT` | スキルを所有する親 `usaturn/maatlog-poc` の選択済み checkout |
| `APP_ROOT` | 公開アプリ `usaturn/maatlog` の選択済み checkout。通常は `ENV_ROOT/public` |
| `LINT_PROJECT` | profile が選ぶ検査用 Python project。MaatLog では `APP_ROOT` |

呼び出し元が選択した checkout とスキルの配置元から `ENV_ROOT` を確認する。
作業中の公開アプリ worktree が明示されていれば、それを `APP_ROOT` とする。
共有 main checkout や共有 `public/` へ置き換えない。

親 cwd から呼ばれた場合も、書く前に読み取り専用で次を確認する。

```sh
git -C "$ENV_ROOT" rev-parse --show-toplevel
git -C "$ENV_ROOT" remote get-url origin
git -C "$ENV_ROOT" config -f .gitmodules --get submodule.public.url
git -C "$APP_ROOT" rev-parse --show-toplevel
git -C "$APP_ROOT" remote get-url origin
```

- 親 origin は `usaturn/maatlog-poc`、公開 origin は親 `.gitmodules` の `usaturn/maatlog` URL と一致すること。
- `APP_ROOT` の top-level はその公開 checkout 自身であること。
  空の `public/` 内で top-level が親を返す場合は未初期化である。ディレクトリがあるだけでは足りない。
- 外部の公開 worktree は選択元の公開 repository と Git の系統（共通 Git directory または履歴）と origin を照合する。
- `APP_ROOT/pyproject.toml` と `APP_ROOT/docs/glossary.rst` が存在すること。
  未初期化、origin 不一致、project/用語集欠落なら、その事実と必要な修復を返す。
  親 project や親 `docs/glossary.rst` への代替、依存追加による埋め合わせはしない。

### 出力先を決める

| 依頼 | 編集先 |
|---|---|
| 新規で `target_path` 省略 | `ENV_ROOT/docs_draft/` の目的に合うファイル |
| 明示された既存アプリ文書の追記・修正 | 選択した公開 checkout 内の指定ファイル |
| 明示された環境文書の追記・修正 | 選択した親 checkout 内の指定ファイル |
| 新規で `target_path` 明示 | 明示の目的と repository の所有関係に整合する指定先 |

相対 `target_path` は依頼元が明示した project/cwd を基準に解決し、勝手に `public/` を足さない。
解決した絶対パス、所属 repository、cwd、`ENV_ROOT` / `APP_ROOT` / `LINT_PROJECT` を記録する。
symlink は実体の行き先まで確認する。所属先が不明、別 repository へ出る、候補が複数、または「既存編集」の対象が不存在なら、書く前に確認する。
親 `docs/` を旧アプリ文書の出力先として復活させない。
新規作成先に既存ファイルがあれば無断で置換せず、依頼がその編集を許可しているか確認する。

### 変更するファイルを限定する

既存編集では最初に対象の内容を読み、指定された変更を加える。指定外の文・ラベルを保持する。
非対象の `docs_draft/` は参考資料として読まない。明示された資料・編集対象は読める。

指定対象以外に許される既存の例外は、本文に使った未定義語の `APP_ROOT/docs/glossary.rst` への追記である。
詳細は [MaatLog profile](profiles/maatlog.md) に従う。親の用語集は読まず、新設しない。
別の docs、toctree、conf.py、依存設定を便乗編集しない。
参照先ラベルの追加に指定外ファイルの編集が必要なら、その追加作業を不足として報告する。
lint の対象は今回作成・編集した RST と、実際に編集したときだけ用語集である。

## リソースの参照先

- 共通: [RST core](rst-core-style-guide.md)
- MaatLog: [profile](profiles/maatlog.md)、[文書種別表](document-types.md) の実在 template
- OSS 予約: `references/profiles/oss-python-extension.md`、`references/sphinx-semantic-markup.md`、`assets/oss-python-extension/`。未接続なので読み込み・生成には進まない

後続の OSS profile が自身の root と検証 project を定義する。MaatLog の親/公開配置を他 profile の既定にはしない。
