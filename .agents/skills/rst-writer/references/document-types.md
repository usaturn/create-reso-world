# 文書種別とリソース

`profile` と `document_type` の組で選ぶ。入力の解決と停止条件は [入力仕様](profile-interface.md) に従う。
**available は MaatLog の3種だけ**である。ファイルが存在することと、profile が利用可能であることを区別する。

## MaatLog — available

`profile` 省略時と明示 `maatlog` は同じ表を使う。
共通 guide と [MaatLog profile](profiles/maatlog.md) を読み、該当する template を選ぶ。

| document_type | 選択基準・構造 | template（skill root 基準） |
|---|---|---|
| `procedure` | 構築・変更・復元。前提条件、手順の流れ、実施手順と結果確認 | [assets/maatlog/template-procedure.rst](../assets/maatlog/template-procedure.rst) |
| `explanation` | 概念・アーキテクチャ。概念、構造、比較、関連資料 | [assets/maatlog/template-explanation.rst](../assets/maatlog/template-explanation.rst) |
| `operational` | 短い確認・操作。procedure を共用し、前提条件と手順の流れは省略可 | [assets/maatlog/template-procedure.rst](../assets/maatlog/template-procedure.rst) |

## OSS Python Extension — reserved / unavailable

明示 `profile=oss-python-extension` 用の予約仕様であり、現在の生成には使用できない。
以下は全て skill root からの予定パスである。`landing-page` の template 名だけが `index` であり、`index` は document_type の別名ではない。

| document_type | 予定パス | リソースの所有者 |
|---|---|---|
| `landing-page` | `assets/oss-python-extension/template-index.rst` | #386 |
| `installation` | `assets/oss-python-extension/template-installation.rst` | #386 |
| `quickstart` | `assets/oss-python-extension/template-quickstart.rst` | #386 |
| `tutorial` | `assets/oss-python-extension/template-tutorial.rst` | #386 |
| `how-to` | `assets/oss-python-extension/template-how-to.rst` | #386 |
| `explanation` | `assets/oss-python-extension/template-explanation.rst` | #386 |
| `configuration-reference` | `assets/oss-python-extension/template-configuration-reference.rst` | #388 |
| `directive-reference` | `assets/oss-python-extension/template-directive-reference.rst` | #388 |
| `role-reference` | `assets/oss-python-extension/template-role-reference.rst` | #388 |
| `api-reference` | `assets/oss-python-extension/template-api-reference.rst` | #388 |
| `troubleshooting` | `assets/oss-python-extension/template-troubleshooting.rst` | #386 |
| `limitations` | `assets/oss-python-extension/template-limitations.rst` | #386 |
| `migration` | `assets/oss-python-extension/template-migration.rst` | #386 |
| `changelog` | `assets/oss-python-extension/template-changelog.rst` | #386 |

`changelog` は対象の既存形式を優先したうえでの fallback template である。
両 profile の `explanation` は別のリソースであり、OSS の代わりに MaatLog template を使わない。
OSS の profile と semantic guide は #384、eval は #390、最終接続は #393 が所有する。

#393 が先行実装の完了・main への取り込み・統合検証を確認してから、entrypoint とこの表を更新する。
その時点まで、予定ファイルが部分的または全て揃っても reserved のままとする。
`SKILL.md` とこの表の編集担当は #382 の実装が main に取り込まれた後に #393 へ移る。
外部 #379/#402 は #361 全体の完了を待つ。
