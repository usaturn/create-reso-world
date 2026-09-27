# 文書種別とリソース

`profile` と `document_type` の組で選ぶ。入力の解決と停止条件は [入力仕様](profile-interface.md) に従う。
**available は create-reso-world の3種だけ**である。ファイルが存在することと、profile が利用可能であることを区別する。

## create-reso-world — available

`profile` 省略時と明示 `create-reso-world` は同じ表を使う。
共通 guide と [create-reso-world profile](profiles/create-reso-world.md) を読み、該当する template を選ぶ。

| document_type | 選択基準・構造 | template（skill root 基準） |
|---|---|---|
| `procedure` | 構築・変更・復元。前提条件、手順の流れ、実施手順と結果確認 | [assets/create-reso-world/template-procedure.rst](../assets/create-reso-world/template-procedure.rst) |
| `explanation` | 概念・アーキテクチャ。概念、構造、比較、関連資料 | [assets/create-reso-world/template-explanation.rst](../assets/create-reso-world/template-explanation.rst) |
| `operational` | 短い確認・操作。procedure を共用し、前提条件と手順の流れは省略可 | [assets/create-reso-world/template-procedure.rst](../assets/create-reso-world/template-procedure.rst) |

## OSS Python Extension — reserved / unavailable

明示 `profile=oss-python-extension` 用の予約仕様であり、現在の生成には使用できない。移行元のリポジトリで用意したもので、このリポジトリでは接続していない。
以下は全て skill root からの予定パスである。`landing-page` の template 名だけが `index` であり、`index` は document_type の別名ではない。

| document_type | 予定パス |
|---|---|
| `landing-page` | `assets/oss-python-extension/template-index.rst` |
| `installation` | `assets/oss-python-extension/template-installation.rst` |
| `quickstart` | `assets/oss-python-extension/template-quickstart.rst` |
| `tutorial` | `assets/oss-python-extension/template-tutorial.rst` |
| `how-to` | `assets/oss-python-extension/template-how-to.rst` |
| `explanation` | `assets/oss-python-extension/template-explanation.rst` |
| `configuration-reference` | `assets/oss-python-extension/template-configuration-reference.rst` |
| `directive-reference` | `assets/oss-python-extension/template-directive-reference.rst` |
| `role-reference` | `assets/oss-python-extension/template-role-reference.rst` |
| `api-reference` | `assets/oss-python-extension/template-api-reference.rst` |
| `troubleshooting` | `assets/oss-python-extension/template-troubleshooting.rst` |
| `limitations` | `assets/oss-python-extension/template-limitations.rst` |
| `migration` | `assets/oss-python-extension/template-migration.rst` |
| `changelog` | `assets/oss-python-extension/template-changelog.rst` |

`changelog` は対象の既存形式を優先したうえでの fallback template である。
両 profile の `explanation` は別のリソースであり、OSS の代わりに create-reso-world の template を使わない。

OSS profile を接続するときは、`SKILL.md`・この表・[入力仕様](profile-interface.md) の利用可能性を同時に更新し、`evals/` の OSS のケースを entrypoint で再実行する。
それまでは、予定ファイルが部分的または全て揃っても reserved のままとする。
