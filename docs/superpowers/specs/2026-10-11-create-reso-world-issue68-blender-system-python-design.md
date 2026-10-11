# Issue #68: ワールド雛形の Blender system-python ラッパー

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/68
- 検証した基準 HEAD: `edaab067f47bab2ae567462544a86fb272a79674`
- 状態: draft（文書版の SHA に対する承認は未取得）
- 関連 Plan: `docs/superpowers/plans/2026-10-11-create-reso-world-issue68-blender-system-python.md`
- 会話での承認・実行許可: 2026-10-11、下記の方針を提示し、ユーザーが「提案どおりに進めて、PRまで作成してください」と指示した。コード実装、隔離 worktree、commit、push、PR 作成まで許可されている。新しい設計の追加ではなく、その承認済みの小規模変更を文書に記録する。
- 基準テストの既存失敗は Issue #83 に分離した。ユーザーの「今回の修正対象には含めない」「Issueを上げたら作業の続きを」の指示により、修正せず記録して続行する。

## 意図と確認済みの原因

`uv run --no-project` でも、cwd や親に見つかった `.venv` を実行環境に使う。Blender は PATH の `.venv/bin/python3` を拾うとシステムの NumPy を読めなくなる。NumPy 未導入の一時 `.venv` を PATH の先頭に置いた `/usr/bin/blender --background --python-exit-code 1 --python-expr 'import numpy'` は exit 1、既存の system-python ラッパーを使うと exit 0 で `/usr/lib/python3/dist-packages/numpy` を読めた。

既存ワールドには手動の回避策があるが、新規雛形には無い。新規作成と `--apply` の両方で設定を補い、利用者の指定と既存ファイルを守る。

## 承認された方針

1. `templates/world-project/blender-system-python` に既存の `/usr/bin/blender` 向けラッパーと同じ内容を置く。PATH の `*/.venv/bin` を外し、`VIRTUAL_ENV` を unset して引数をそのまま `exec /usr/bin/blender "$@"` に渡す。
2. `scripts/new-world.sh` の新規作成・`--apply` は、`.resoloop/blender-system-python` を通常ファイルとして設置し、実行権限を付ける。`.resoloop.json` の `blenderExecutable` が未設定ならこのラッパーの絶対パスを設定する。
3. 利用者の別の `blenderExecutable` は変更しない。現在のラッパーを指す場合も JSON を再保存しない。
4. 不正 JSON、ラッパーの内容差、symlink や非通常ファイルなどの競合は、既存の一巡目で集め、全件を報告して exit 1 とする。競合が一つでもあれば雛形・JSON・実行権限を変更しない。新規作成で既に行った `resoloop init` の結果が残る既存の仕様は維持する。
5. 移動後の古い絶対パスも利用者指定と区別できないので自動変更しない。保持を案内し、README に `.resoloop.json` を現在の絶対パスへ手動更新する方法を書く。
6. JSON の解析・編集は `jq` を使う。Dev Container の apt 導入対象にも明記し、見つからなければ init や変更前に exit 3 で案内する。`--no-sync` は引き続き uv 不在でも使える。

## 実装担当に残す細部と判断

- 判断: JSON は文書が一つだけで root が object の場合を受け付ける。キー欠落・null は未設定として補う。string は利用者指定として保持（空文字を含む）、それ以外の型は競合とする。
- 判断: 既存ラッパーと同じ内容で実行権限だけ無い場合は、競合検査後に実行権限を補える。違う内容や symlink のラッパーを上書き・chmod しない。
- 判断: JSON を編集する場合は、他のキーの値と元のファイル権限を維持し、同じディレクトリの一時ファイルから置き換えて途中の JSON を残さない。編集不要の場合はバイト列も変更しない。
- 既存のローカルワールドには自動適用しない。実際の Blender の検証には、worktree 内に専用の使い捨てプロジェクトを作り、その範囲だけ片付ける。

## 範囲外・避けたいこと

- ResoLoop 本体・同梱 meshy スクリプトの変更（Issue #56 の範囲）。
- 基準テストの失敗（Issue #83）の修正、既存ワールドの変更、Blender や ResoLoop の再インストール、main の作成やマージ。
- 移動前の値の推測による上書き、JSON を sed で解析する実装、文書の文言だけを照合する追加テスト。

## 検証と完了条件

- 新規作成、既存・従来位置への適用、二度目の無変更、利用者設定の保持、他の JSON 値の保持、不正 JSON、symlink、内容差、jq 不在、競合時のファイル・mode 無変更を実行テストで守る。
- ラッパーの PATH 除去、VIRTUAL_ENV 解除、引数・終了コードの引き渡しを実行テストで守る。
- 実際に作った使い捨てプロジェクトで `resoloop blender find --json` が configuration の絶対ラッパーを選び、`uv run` の meshy doctor で `bpy_numpy` が成功する。
- Shell の全テスト、pytest 全体、配置検査、構文と差分を確認する。Issue #83 の既知の失敗は分離して報告し、新しい失敗が無いことを確認する。

## 基準検証（変更前）

- `bash .devcontainer/run-tests.bash`: 28 件成功。
- `uv run pytest -q`: 482 件成功、Issue #83 の 1 件失敗。対象テスト単体でも 1 failed / 8 passed を再現。
- 使用中 ResoLoop: `0.1.0-preview.17.fork.20261009.g84c7932`。今回のために版を変更していない。
