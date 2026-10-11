# Issue #68: ワールド雛形の Blender system-python ラッパー

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/68
- 検証した基準 HEAD: `edaab067f47bab2ae567462544a86fb272a79674`
- 状態: completed（会話で承認された方針の実行が完了。文書版の SHA に対する個別の承認は記録していない）
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

## 実行結果・公開（2026-10-11）

- 実装コミット: `1ab5e39`。独立したタスクレビューとブランチ全体レビューは、仕様・品質とも承認、Critical/Important/Minor の指摘なし。
- controller の最終検証: Shell 29 件成功。pytest 482 件成功、Issue #83 の既存失敗だけ 1 件。配置、変更した Shell の構文、差分、実行権限の検査も成功。#83 の対象ファイルを変更していないことを差分で確認した。
- 実際の `new-world.sh` で使い捨てワールドを作成し、絶対ラッパーが `source: configuration` で選ばれた。`uv run` でプロジェクトの `.venv/bin` が PATH の先頭に入り、その環境で同梱 doctor が `bpy_numpy=true`、全チェック成功になった。
- 既定の Python 3.12 `.venv` では直接起動の失敗が再現しなかったため、追加確認としてこの使い捨て `.venv` だけをシステム Python 3.14.4 へ同期した。NumPy 未導入の一致版 `.venv` では直接 Blender が `ModuleNotFoundError` / exit 1、ラッパーではシステム NumPy 2.3.5 の import / exit 0 を確認した。
- 実際の `--apply` の再実行で JSON とラッパーの内容・権限は変わらなかった。検証用ワールドは確認後に削除し、既存のローカルワールドとツール導入状態は変更していない。
- 公開先: https://github.com/usaturn/create-reso-world/pull/84 。`fix/issue-68-blender-system-python` を push し、main 向けに PR を作成した。マージはしていない。フィードバック用 worktree を残す。
- private リポジトリの CI は停止中のため、規約どおり確認対象外。ローカルの既知失敗は PR 本文に明記した。

### 所要時間

- 実装担当: 21 分 23 秒（調査 39 秒、RED/GREEN・実装 4 分 10 秒、全体回帰と調整 14 分 01 秒、自己レビューと commit 50 秒、報告 1 分 43 秒）。
- タスクレビュー: 2 分 01 秒。ブランチ全体レビュー: 2 分 11 秒。
- controller の実環境検証: 2 分 13 秒。最終回帰は 14:55:45 開始、15:01 頃終了（pytest 146.35 秒）。
- controller 全体の計測開始: 14:00:36、PR 作成と結果記録: 15:03 頃（ユーザー確認待ちと同期委譲・検証の待ち時間を含む約 63 分）。

## PR #84 レビュー指摘の選別（2026-10-11）

### 対象・実行許可

- 対象: `usaturn/create-reso-world` PR #84、`fix/issue-68-blender-system-python`。
- 現行の検証対象 HEAD: `42f4c8b83e3369b535779dbf0822f50eec1a0738`。全レビューの対象 `42f4c8b83e33` はこのコミットと一致する。
- 入力: 親 checkout の `reviews/#84-fix-issue-68-blender-system-python/` 配下の全4ファイル（`openai-codex-gpt-6.1-sol.md`、`deepseek-deepseek-v4.1-flash.md`、`claude-opus-5-5.md`、`SWE-2-High.md`）。OpenAI / Claude は指摘なし。
- 状態: completed（全指摘の確認・分類・必要な検証を完了。公開操作の結果は PR コメントと作業報告に残す）。
- 実行許可: ユーザーが `review-fix-planning` と `#84` を指定した完遂依頼。現行で致命的な指摘だけを修正し、修正不要なら最終コメント・検証した HEAD のマージ・関連 Issue の更新まで進める。以前の実装時の「マージしない」は、その時点の公開手順の記録として残す。
- 既存の Issue #68 の Spec と関連 Plan をリポジトリ・Issue/PR・テーマ・参照パスで照合し、本 Spec に追記する。レビュー回ごとの新規文書は作らない。
- 調査中は clean で現行 HEAD と一致する既存の専用 worktree を再利用した。他の作業ツリーの未コミット差分や、既存ローカルワールドは入力にしていない。

### 全指摘の分類

**解消済み 0 / 対応する 0 / 対応しない 3。** 同じ名前の ID を区別するためレビュアーの接頭辞を付ける。

| ID | 指摘 | 分類 | 現行 HEAD での確認・判定根拠 |
| --- | --- | --- | --- |
| DS-L1 | 相対 `.venv/bin` が PATH に残り NumPy import に失敗する（別名 venv も関連論点） | 対応しない | wrapper:4–6 を実行し相対形の保持と実 Blender の exit 1 を再現した。ただし承認された方針1は `*/.venv/bin` の除去と既存 wrapper と同じ内容に限定される。実際の `uv run` は絶対 `.venv/bin` を先頭に置き、wrapper で NumPy import / exit 0 を確認した。相対形・別名 venv への拡張は対応範囲の是非であり、公式経路の障害ではない。 |
| SWE-L1 | venv だけの PATH が空になり、改行を含む PATH が先頭行までに縮む | 対応しない | wrapper:4–8 を実行し `/sample/.venv/bin` → 空文字、`/a\n/b:/c:/usr/bin` → `/a` を再現した。システム bin を含む通常の Dev Container / uv 経路で、この縮退入力は使っていない。任意の PATH 全体の保持やフォールバック追加は設計拡張であり、確認した主要経路の障害ではない。なお空 PATH は必ずしも「検索先0個」を意味せず、全コマンドが必ず失敗するとは結論しない。 |
| SWE-I1 | カスタム値を保持するときも古い絶対パスの手動更新を案内する | 対応しない | `new-world.sh:168–172,245` と実行テスト39で、カスタム・旧絶対値・空文字の保持と snapshot 不変を確認した。案内は余分だが、利用者設定の変更や誤った対象への操作を実行しない。README:148–151 も、移動後の古い値に限って手動更新を案内している。 |

- Test suggestions は上記 DS-L1 / SWE-L1 と同じ提案として判定した。対応する致命的な欠陥がないため、保険のテストや軽微な文書修正は追加しない。
- 「対応する」がないため、修正用の守る条件・影響経路の表、再発による設計の見直し、ガードを外した対照検証は該当しない。
- PR の説明には、相対・別名 venv、改行・システム bin が無い PATH を保証しないことと、通常の `uv run` / システム bin を含む絶対パスを使う回避方法を明示する。

### 確認範囲・選んだ方針

- PR の全差分と変更8ファイルの全文、new-world の呼出元、JSON の型・保持分岐、親ディレクトリ・ファイル・symlink の検査、競合ゲート、chmod と一時 JSON の更新順、終了時の一時ファイル処理、path helper・テスト登録・関連雛形を確認した。
- 独立した `sp-recon` に読み取り専用の全差分・全変更ファイル・関連経路の確認を委譲した。致命的な欠陥なしとの結果は、controller のコード確認と実行検証に照合した。子にはテスト・編集・Git/GitHub の更新をさせていない。
- 現行と同一 SHA の隔離 worktree で committed wrapper を実行した。NumPy 未導入の Python 3.14.4 `.venv` では直接 Blender が exit 1、絶対 `.venv/bin` の wrapper が exit 0、相対 `.venv/bin` の wrapper が exit 1、通常の `uv run --no-project --no-sync` の wrapper が exit 0。成功時は `/usr/lib/python3/dist-packages/numpy/__init__.py` を読み込んだ。
- 方針は、承認済みの限定した PATH 処理を保ってマージする。相対形対応・別名 venv の正規化・汎用 PATH パーサーへの変更は、今回の致命的な指摘だけを扱う依頼から外れるため採用しない。
- テスト追加は不要（修正対象の挙動がない）。既存の実行テスト・構文・配置・差分検査で代える。既存の追加テストは実際のスクリプトと生成物・環境・引数・終了コードを調べており、文書や実装本文の文字列だけを照合するものはない。
- 再現用 worktree と親の一意な一時ディレクトリは、再現と関連テストの終了後に `worktree remove` を先に行って削除した。

### 検証・結論

- 関連テスト: `bash tests/scripts/test-blender-system-python.bash` と `bash tests/scripts/test-new-world.bash` はともに exit 0（29秒）。後者の47ケースで設定保持・無変更・競合・権限・jq不在等を確認した。
- 変更 Shell 5ファイルの `bash -n`、PR 差分の `git diff --check`: exit 0。
- 必須検証: `bash .devcontainer/run-tests.bash` は29件すべて成功 / exit 0、`bash scripts/check-layout.sh` は成功 / exit 0（約143秒）。実行ログは一意な `review-fix-planning.XXXXXX` 配下に閉じ込め、終了後に削除した。
- 記録追記時の `git diff --check` が末尾の余分な空行1行を検出したため、その空行を取り除いた。最終版の `bash tests/scripts/test-docs.bash` と `git diff --check` はともに exit 0。実装・テストへの修正はない。
- base の取得結果は `edaab067f47bab2ae567462544a86fb272a79674` で、検証対象 HEAD の祖先。base が先に進んでいないため一時 merge の検証は不要。
- private リポジトリの CI は `AGENTS.md` の規定により確認不要。Issue #83 の既存 pytest 失敗は今回変更していない。変更対象がスキルではないため pytest 全体の再実行を反映条件にしない。
- 修正後の自己レビュー: 未実施（結論2、コード修正なし）。独立調査は、修正後の自己レビューとして数えていない。
- 結論: 2 修正不要としてマージする。未確認の指摘はない。Dev Container rebuild、Resonite live 操作、meshy doctor 全体は今回未実施であり、過去の実装時の実行記録と区別する。
- 所要時間: 15:23頃着手、15:34頃に分類と必須検証を完了（約11分）。主要 Task は入力・境界・独立調査・精読が約6分、再現と関連テストが約1分、分類・記録が約1分、必須検証が約2分23秒。公開・Issue更新に要した時間は完了報告に記す。
