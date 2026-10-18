# Issue #169: 明示した利用者の判断記録を信頼する

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/169
- 検証した開始 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- 状態: `draft`（実行許可は内容の承認ではない）
- 利用者の指示: `/skill:issue-to-pr` の明示呼び出しと引数 `#169`。同スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」に従う。マージしない。
- 新規文書の理由: #152 の完了後に見つかった、独立した信頼判定の修正。既存の #169 の Spec・Plan は無い。

## 意図・範囲

上流 PR で認証済み利用者が `CONTRIBUTOR` でも、自分の記録を次のサイクルへ引き継げるようにする。第三者の `CONTRIBUTOR` を一律に信頼してはいけない。

対象は `.agents/scripts/review_records.py`、その既存テスト、`.agents/review-records.md`。#155 が担当する upsert・run_roles の実装やスキル、記録の schema、既存の判断基準・マーカー・除外処理は変えない。#169 を独立の先行修正として扱い、#155 側で接続すべき内容を文書化する。ボードの予約・他 Issue の状態は変更しない。

## API・CLI

- `collect_records(comments, *, exclude_comment_ids=(), trusted_login: str = "")`
- `read_state(comments, *, expected_pr=None, exclude_comment_ids=(), trusted_login: str = "")`
- 読む投稿者は `author_association in TRUSTED_ASSOCIATIONS` または `bool(trusted_login) and comment.author == trusted_login`。完全一致とし、空文字・欠落した author で信頼を与えない。
- `TRUSTED_ASSOCIATIONS` は `OWNER`・`MEMBER`・`COLLABORATOR` のまま。login の指定を省くと既存挙動を維持する。
- `fold --trusted-login LOGIN` を追加し、API が整えた投稿者 login と照合する。CLI の既定値は空文字。
- 同じ `read_state` を使う `validate --comments-file` にも `--trusted-login LOGIN` を渡せるようにする。検査経路による信頼判定の食い違いを防ぐ、小さな付随修正である。
- モジュールは `gh` を実行しない。呼び出し元が `gh api user --jq .login` の成功と空でない結果を確認して渡す。取得失敗は止め、PR author・コメント本文からの推測や任意の投稿者への切り替えはしない。
- #155 の upsert は認証済み login を一度取得し、記録付き・記録なし両方のコメント照合と `read_state` に同じ値を使う。run_roles の fold 呼び出しも同じ利用者を指定する。現行 helper が既にこれを実装しているとは記載しない。

## 受け入れ条件・検証

1. 正常な同じ記録を使い、明示 login と同じ `CONTRIBUTOR` の投稿を読む。異なる login の投稿は `ignored_comments` に入る。
2. 指定省略・空文字では `CONTRIBUTOR` を読まず、既存の三つの区分は読み続ける。空/欠落 author も新しい信頼対象にならない。
3. 信頼した投稿にも、除外 ID、PR 一致、マーカー・記録検査が従来どおり適用される。壊れた記録はエラーとなる。
4. 1 回目の `CONTRIBUTOR` の記録を `read_state` で読み、2 回目の `check_against` が成功する。1 回目の重複記録は拒否する。
5. fold の標準入力→JSON と validate のファイル→終了コードで login の伝播を確かめる。無指定での既存挙動も維持する。
6. `uv run pytest .agents/scripts`、README のワールド以外の三つの検証入口を実行し、終了コードと実ログを確認する。

安全条件と回帰を実コードの実行でテストする。文書の固定文言を照合するテストは追加しない。実 GitHub コメント投稿や本物のモデルを使う評価は不要。CI は private リポジトリで停止中なので確認しない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 信頼する対象 | Issue の (a)、単一の明示 login | (b) CONTRIBUTOR 全員 / (c) 上流だけ記録なし | 自分の履歴を読め、第三者全員を信頼しない | issue-to-pr による通常判断の委任。権限・外部送信の拡大なら停止 |
| 照合 | 空でない login の完全一致 | 大小文字の正規化・複数 login | API の login をそのまま渡す最小変更 | 記録内の値で信頼先を決めない |
| 検査 CLI | validate にも同じ引数を追加 | fold だけ変更 | 同じ過去記録を使う二つの入口で挙動を揃える | 通常判断として選択。schema や投稿の実装には広げない |
| #155 との境界 | 文書で後続の接続条件を明記 | 今回 upsert/run_roles を実装 | #155 の所有範囲と混在させない | 他 Issue や予約の更新はしない |
| 実行方式 | executing-plans による inline、最後に独立レビュー | Task ごとの実装委譲 | 変更は一つの信頼判定にまとまり、同じファイルを順に変更する | 明示スキルの方式選択規則に従う |

## 開始時の証拠

- Issue は open、コメント・親 Issue・blocked_by は無し。open PR・予約 ref・同番号の branch/worktree は無し。
- `origin/main` から新規 worktree を作成。既存の `test_review_records.py` は `187 passed`、終了コード 0。
- #155 は open だが今回の先行依存ではない。今回の API を使う接続は #155 の作業となる。
