# Issue #375: 正確なモデル識別子から安全なコメント ID を導出する

- 状態: draft
- 対象: https://github.com/usaturn/create-reso-world/issues/375
- 実行許可: 利用者は `/skill:issue-to-pr` 相当の明示入口から `#375 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max` を指示した。通常の設計判断、実装・検証・commit・push・PR、指定ループ内の finalize によるマージを委任している。内容の承認とは区別する。
- 利用者は main の進行時の継続も希望したが、捕捉後の base 移動で停止する既存の安全規則は維持する。
- 捕捉 base: usaturn/create-reso-world / origin / refs/heads/main / `1f20820f0b628c707784aa6f7f55146225139fd2`

## 意図・原因

正確なモデル ID `deepseek-v4.1-flash:1017[1m]` は現在の `agent_id_for()` の許可文字に収まらず、レビュー後の状況コメントで停止する。モデル自体を手で短縮すると実際の担当を追跡できない。原因は、正確な識別値とマーカー向けの導出値を、旧変換で表せる範囲だけに限定していることにある。

## 仕様

1. `planner.model`、ループの controller model、コメント見出しには入力の正確なモデル名を保持する。追加の CLI 引数やモデルの手動置換は不要。
2. `agent_id_for(model: str) -> str` は既存の `/`・半角空白から `-` への置換と連続 `-` の圧縮を最初に試し、結果が既存の許可形式に収まるなら、その値を変えない。旧 v1/v2 記録とマーカーを引き続き読み取れる。
3. 旧変換で表現できないが既存の単一行識別値として有効なモデル名は、`model--` + 元の文字列の UTF-8 バイト列に対する SHA-256 の小文字16進64桁へ変換する。旧変換は `--` を残さないため新旧の名前空間は交わらない。新形式間は SHA-256 の衝突耐性を利用する。絶対的・数学的な一意性は主張しない。
4. 空・空白のみ・制御文字・改行・HTML コメントの開始/終了マーカーは、既存の識別値検査で拒否する。山括弧だけを含む単一行名はその検査が許す範囲で受け入れる。
5. `agent_id_for()` の引数は常にモデル名であり、導出済み ID を再び変換しない。特に record-less コメントの compose→find→PATCH が同じ ID を使う。`model--...` 自体をモデル名として渡した場合は旧変換され、対応する拡張モデルの ID と衝突しない。
6. record 付きコメントも既存の compose→validate→extract/fold→upsert を通し、正確なモデル名と導出 ID の対応を保持する。信頼する投稿者・PR/head・サイクルの検査や公開前の安全検査は緩めない。

## 範囲・対象外

変更範囲は共有導出関数、コメントの導出呼出し、規則を定義する `.agents/review-records.md`、必要な回帰テスト。レビュー用ファイル名の変換、記録スキーマ、ランナーのモデル選択、マーカーの構文は変更しない。既存の `/`・空白・連続ハイフンによる旧形式同士の衝突の全面解消は対象外（互換性を保つため）。外部 API 送信を増やすこともない。

## 決定記録

|項目|選択した案|検討した別案|理由|委任指示・停止条件|
|---|---|---|---|---|
|導出|旧形式を維持し、未対応文字だけ専用名前空間+SHA-256|単純置換、全モデルをハッシュ化|単純置換は別モデルの同一視、全変更は過去記録の検査・更新を壊す|通常の設計判断の委任。履歴の破壊は不可|
|入口|正確なモデル名をそのまま受理|起動前拒否、別 agent-id 引数|拒否は目的の機能停止を解消せず、別引数は不要な運用負荷|既存の安全な識別値の拒否は維持|
|実装担当|runner の pi_opencode-go_deepseek4-flash_max、fallbackなし|self|利用者の --implement。check の self=false|失敗を理由に self へ切り替えない|
|実行方式|SDD の1実装Taskを runner に依頼し統合担当が検証|inline|明示担当を守り変更範囲を一括で扱う|各依頼後に accept/cleanup。失敗は規則どおり停止|
|ループ|上限3サイクル（既定）、inspect は指定3担当、implement は指定担当|既定レビュアー|check-options 成功。template は .devcontainer/agent-runner.toml、config 指定なし。fix の self-review/fix-check は既定 self|既定値を利用者指定とは記録しない|

## 検証

旧形式と新形式の名前空間分離、同じ見た目に置換される異なるモデル名の区別、正確なモデル情報の保存、別コメントの誤更新を防ぐ実行テストは S（取り違え・上書きの防止）として残す。単に未対応名で例外を出さなくなること、制御文字拒否の単独確認、文書文言などは L/F のため新規の恒久テストを増やさず、実行確認と差分確認で代える。実 GitHub はこの run の PR/レビューでのみ使用し、回帰テストは fake GitHub を使う。
