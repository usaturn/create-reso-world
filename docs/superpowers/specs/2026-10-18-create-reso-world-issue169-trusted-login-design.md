# Issue #169: 明示した利用者の判断記録を信頼する

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/169
- 検証した開始 HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- 状態: `completed`（初回は draft。下記 PR #179 のレビュー修正・検証まで完了。実行許可は内容の承認ではない）
- 利用者の指示: `/skill:issue-to-pr` の明示呼び出しと引数 `#169`。同スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」に従う。マージしない。
- 新規文書の理由: #152 の完了後に見つかった、独立した信頼判定の修正。作成時には既存の #169 の Spec・Plan は無かった。PR #179 のレビュー修正も、この文書を更新して記録する。

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

## 実行結果（公開前）

- 実装: `85e986e`。上記 API・fold/validate の CLI・利用文書を更新した。内容承認は未取得のため状態は draft のまま。
- 記録テスト 205 件、scripts 全体 531 件、README の shell 33 本・layout・Python 2587 件が全て成功（終了 0）。信頼条件の負例・次サイクル・重複拒否を確認した。
- `1335f41..85e986e` の独立した全体レビューで修正指摘無し。後続接続は #155 の範囲として維持する。自動 brief の代わりに親 checkout の session へ記録した配置上の裁定を Plan に残した。
- 公開前時点の所要時間は約 25 分。詳細・実ログの絶対パス・公開予定は対応 Plan の実施記録に記載した。

## PR #179 レビュー修正（2026-10-19）

### 範囲・実行許可・進行

- PR: https://github.com/usaturn/create-reso-world/pull/179 、head branch `fix/issue-169-trusted-login`。
- 対象版: `4bb04e006111f05e7fe01698a17fb09223f7f543`。入力レビューは全てこの HEAD（12 桁表記 `4bb04e006111`）で、PR head との一致・祖先関係を確認した。
- 利用者の `/review-fix-planning #179` と今回限りの補助指示に基づく完遂。採否基準・自己レビュー最大 1 回・既存 PR への commit/push 権限を維持する。スキルファイルは変更しない。内容承認ではなく実行許可として記録する。
- `PARENT_ROOT`: `/workspaces/reso-world`。`CODE_ROOT` / `DOC_ROOT`: `/workspaces/reso-world/.worktrees/issue-169-trusted-login`。既存の clean な head 一致 checkout を再利用し、このセッションの削除対象にしない。
- planner: `openai-codex/gpt-6.1-sol`（pi、ランタイム環境変数で確認）。初期調査に read-only sp-recon を 1 件、修正後の自己レビューに read-only sp-review を 1 件使う。初期調査と自己レビューは別段階であり、テストは統合担当が実行する。

結論: **1 修正して既存 PR へ push**。入力・HEAD・全変更ファイルと関連経路の確認、修正前後の再現、文書修正・検証・1 回の自己レビューまで完了。今回の変更は文書 2 ファイルだけで、Spec は結果を含めて 1 回だけコミットする。push・状況コメントの実施結果は PR と完了報告へ残す。対応 Plan は初回公開前の履歴として draft のまま維持する。

### 入力・全指摘の採否

入力ディレクトリ: `reviews/usaturn/create-reso-world/#179-fix-issue-169-trusted-login/`。全 4 ファイルを全文読んだ。

| レビューファイル | 対象 HEAD | 指摘 | 判定・理由 |
| --- | --- | --- | --- |
| `SWE-2-Max.md` | `4bb04e006111` | なし | 指摘 0 件。未確認の解消根拠には使わない |
| `claude-opus-5-5.md` | `4bb04e006111` | I-1 | 対応する。6.4 の手順どおりに上流 PR の自分の先行記録を照合すると、正常なサイクル 2 を終了 65 で拒否し、同じサイクル 1 の重複を終了 0 で通すことを再現。文書どおりの操作が誤った結果になるため、Info 表記でも採用基準 (a)(b) を満たす |
| `gpt-6.1-sol.md` | `4bb04e006111` | なし | 指摘 0 件。未確認の解消根拠には使わない |
| `opencode-go-deepseek-v4.1-flash.md` | `4bb04e006111` | I-1 | 対応する。同じ 6.4 の欠落を指摘しており、上記と同一の再現・修正に対応付ける。別経路を重複扱いで除外したものではない |

分類: 解消済み 0 / 対応する 2 / 対応しない 0（入力指摘数）。修正の論点は 1 件。

### 要件と検証の対応・原因との関係

| 既存の約束・制限 | 修正・維持する内容 | 根拠・検証 |
| --- | --- | --- |
| PR 本文、Spec API・CLI と受け入れ 1・4・5、Plan Task 1: 自分の CONTRIBUTOR 記録を継続し、fold と validate の信頼判定を揃える | 6.4 の手動 validate でも同じ非空の認証済み login を渡す | 修正前の CLI 対照、修正後の実文書の shell 例と独立入力のシナリオ照合 |
| 受け入れ 2・3: 他人や空 login を追加信頼せず、既存三区分・除外・PR/記録/マーカー検査を維持 | API・CLI 実装は変更しない。文書修正で保証を狭めない | 記録テスト 205 件と、同じ入力での login 有無・別人・三区分・重複・更新除外の対照 |
| 取得は呼び出し側、失敗・空で停止、推測しない | 6.4 の単独実行例にも 8.1 と同じ認証取得・停止を示す。fold 後は取得済みの同じ値を再利用する | fake gh の正常/失敗/空と呼出し順、入力・認証 sentinel・共有リンクを含む前後比較、ガードを外した隔離対照 |
| Spec 意図・範囲、Plan Global Constraints: upsert/run_roles の接続は #155 | 後続接続の実装は追加しない。7.4 の将来規則と現行未接続を区別する | 7.4・7.6・8.1 の相互参照と現行 helper 全文、全呼出元検索 |

破れた前提: 「6.4 の過去記録照合も 8.1 の fold と同じ投稿者集合を読む」。6.4 の shell → validate CLI の境界で login が落ち、API の既定値 `""` により、自分の CONTRIBUTOR コメントが集約前に除外された。コメント取得や JSON 変換の失敗ではなく、引数の伝播漏れである。

履歴との関係（採否とは別軸）: **既存原因の適用漏れ**。`85e986e` は API・CLI・7.4・7.6・8.1 を更新したが、同じ条件に頼る 6.4 の例を更新していなかった。新しい要求でも、今回の修正が作った回帰でもない。`1335f41..4bb04e0` の履歴は設計・計画・初回実装・検証記録のみで、以前の致命的レビュー修正は無い。したがって設計見直しのきっかけ 1・2 は非該当。自己レビューで同条件の再発が出れば、きっかけ 3 として表を仕組みから見直す（再レビューはしない）。

### 守る条件と影響経路

守る条件: **同じ PR の過去記録を読む fold と validate は、既存三区分に加えて同じ非空の認証済み login だけを信頼し、次サイクル・重複・更新対象の照合を欠落なく行う。取得失敗・空では、照合や投稿へ進まない。**

| 経路（差分外を含む） | 判定 | 観測すべき結果・確かめる方法 | 証拠・実施結果 |
| --- | --- | --- | --- |
| 6.4 認証取得 → 単体 validate → コメント取得 → 過去照合 | 修正する | 8.1 と同じ取得/停止を示し、照合に `--trusted-login`。正常な次サイクル 0、同じサイクルの重複 65、初回の空履歴 0 | 修正前は次サイクル 65・重複 0（E1）。修正後は次サイクル 0・重複 65・初回 0（E3） |
| 6.4 更新時 `--exclude-comment`（差分外） | 修正する（同じ例に含む） | 先行と現在の自分の記録がある場合、現在を除外すれば 0、除外なしは重複で 65 | 実例に除外 202 を追加すると 0、除外なしは `round 2 is already recorded`（65）（E3）。除外の規則は不変 |
| 6.4 の取得失敗・空、失敗後の次操作 | 修正する | 終了 1、コメント取得と validate は未実行、管理状態が不変。その後正常な認証で同じ入力の照合が成功 | 失敗・空とも終了 1、gh の user 取得以外は未実行、管理状態は不変。同じ入力・保存先で正常認証に戻すと 0（E3）。ガード欠落の検出も確認（E4） |
| 8.1 認証取得 → fold、validate への同値指定の説明（差分内） | 既に満たす | 同じ自分の記録から rounds `[1]`。取得失敗/空は停止。6.4 から実在する節へ参照する | 全文・引数照合済み。実例の rounds `[1]`、失敗/空は各 1、同じ値を再利用した fold → validate は 0・認証取得 1 回（E3） |
| CLI fold/validate → comments_from_api → read_state → collect_records → fold/check_against | 既に満たす | 明示 login の自分は読む、別人/空は読まない。既存三区分は維持。信頼しても PR・記録・マーカー・除外・重複検査を迂回しない | E1・E2・E3・E5。変換は API の `user.login` と `author_association` を使い、本文から信頼先を作らないことを全文で確認 |
| validate 単体、render（過去記録を読まない入口） | 対象外 | 過去コメントの信頼集合が存在しない。単体の schema 検査・描画だけで、login の取得や必須化は不要 | 6.4 の単体検査と 7.6 の責務に一致。CLI の単体 validate/render 分岐・既存テストを確認 |
| 7.4 記録付き/なしの照合、run_roles 接続 | 対象外（実装）／文書は既に満たす | 現行 helper に records 接続は無く、#155 が同じ認証済み login を渡す仕様。今回実装済みとは記さない | helper 全文・リポジトリ全体の呼出元検索・Spec/Plan の範囲と一致 |
| review_findings の stats（差分外、fold 出力の読取） | 既に満たす | fold 済み JSON を消費するだけで独自の投稿者判定をしない | `review_findings.py` の参照箇所と 8.1 の出力仕様を照合。login の再解釈は不要 |

### 推奨方針・テストの要否

- 推奨: 6.4 を単独で使えるように、既存 8.1 と同じ認証取得と失敗時停止を実例へ足し、過去照合の validate に login を渡す。fold に続く実行では取得済みの同じ値を使うと明記する。
- 別案: オプションだけ足して取得を読者に任せる案は、未設定なら空になり同じ誤判定を残すため採らない。API の既定 login を暗黙取得する案はモジュールの非通信・既定互換の保証を破るため採らない。上流の過去照合を非対応とする案は既存の保証を狭めるため採らない。
- 文書のみの修正なので、新規の永続テストは不要。既存の記録テストと、構文・参照先・実文書の手順のシナリオ照合を行う。文書の文字列一致テストは作らない。
- 検証の独立性: 追加の一時シナリオはテスト fixture や実装の compose/render 関数を使わず、公開 v1 形式に従う架空 PR `example/upstream#900` の最小記録（判断なし）と API 形のコメントを手書きする。期待値は 6.4 のサイクル規則から決め、同一入力の login 有無と修正前後を比較する。fake gh は認証結果と API 形の JSON だけを返し、信頼判定は実 CLI を通す。実 GitHub 投稿・有料実機の反復は不要。

### 修正前の証拠

- E1: SHA `4bb04e006111f05e7fe01698a17fb09223f7f543` の隔離 worktree で、`uv run --no-project python <REPRO_ROOT>/verify_manual.py <WT> baseline` を実行、終了 0。入力は上記の独立記録と `user.login=self-user` / `author_association=CONTRIBUTOR` の先行コメント 101。実文書の 6.4 の shell 例は次サイクル 2 を `round: must be 1`（65）で拒否し、重複サイクル 1 は成功（0）。同じ CLI に `--trusted-login self-user` だけを足すと、それぞれ 0 / 65（`already recorded`）となった。別 login では次サイクル 65。無指定でも OWNER/MEMBER/COLLABORATOR の各々で次サイクル 0。直接 CLI は入力・auth sentinel・その hard link/symlink のバイト列/有無/mode/リンク種類・参照先を変えず、失敗後の正常指定も 0。実例のコメントファイルは取得結果で置き換わる（既存手順の一時出力であり、認証前不変を保証する箇所とは分ける）。
- E2: 同じ隔離版で `uv run --project /workspaces/reso-world pytest -p no:cacheprovider <WT>/.agents/scripts/tests/test_review_records.py --basetemp <REPRO_ROOT>/pytest-tmp -q` → `205 passed in 0.50s`、終了 0。追加されていたテストは実コードの振る舞いを検査し、テスト採用基準に反する追加は無かった。
- 隔離 worktree と検証ルートは手順 3 の完了時に撤去済み。初期調査子の clean/committed 確認はツール制約で未実施だったが、統合担当が着手前の clean・完全 SHA と調査終了後の clean を照合し、全変更 5 ファイルの全文と関連ソースを独自に確認した。

### 修正後の検証・自己レビュー・結論

- E3（修正版の実例）: 親 HEAD `4bb04e0` ＋ `.agents/review-records.md` の SHA-256 `65618318442eda2cb2f35ff379850bf1ad29e46acb54e0dcfb4001f753e67149`。`uv run --no-project python <REPRO_ROOT>/verify_manual.py <CODE_ROOT> verified` → 19 シナリオすべて期待結果、終了 0。実例は文書の 6.4 と 8.1 から抽出して実行し、`bash -n` も両方成功。入力は E1 と同じ独立した v1 記録・GitHub API 形コメントである。次サイクル 0 / 重複 65、初回 0、更新は除外あり 0 / なし 65、fold は rounds `[1]`。6.4 と 8.1 のそれぞれで認証取得失敗/空は 1、呼出し列は `gh api user --jq '.login // empty'` のみで、validate・コメント取得は無い。各々で同じ入力・同じ保存先のまま認証を正常に戻すと成功。取得済み値を使う fold → validate は取得 1 回、終了 0。
- E3 の状態比較: 記録・既存コメントファイル・auth sentinel・その hard link/symlink について、有無・バイト列・mode・種類・リンク参照先・リンク数を前後比較した。認証失敗 4 ケースは全て不変、直接の validate は成功/失敗とも不変。通常の 6.4 実例はコメント取得時に一時 `COMMENTS_JSON` を置き換えるので、内容検査の拒否まで無変更とは主張しない。永続状態の更新・外部投稿は無い。中断時もこれらの読取処理に取り消す永続変更は無く、一時コメントファイルは次回再取得する。API 取得中のネットワーク中断の仕様を新しく追加するものではない。
- E4（検出力）: 修正後の文書だけを `4bb04e0` の隔離 worktree へ写し、6.4 の認証失敗/空のガードだけを外した。`uv run --no-project python <REPRO_ROOT>/verify_manual.py <WT> guard-control` の対照で、対象の負例 2/2 が失敗した（両方とも終了 1 で止まる期待に対し、照合まで進んで `round: must be 1` の 65）。専用 checkout のガードは外していない。隔離 worktree は撤去済み。
- E5（回帰）: 上記文書版で、記録テスト `uv run --project /workspaces/reso-world pytest -p no:cacheprovider <CODE_ROOT>/.agents/scripts/tests/test_review_records.py --basetemp <REPRO_ROOT>/pytest-tmp -q` → 205 passed in 0.30s。`CODE_ROOT` で `uv run pytest .agents/scripts -p no:cacheprovider --basetemp <REPRO_ROOT>/scripts-tmp -q` → 531 passed in 11.57s、`bash .devcontainer/run-tests.bash` → 33 本 PASS、`bash scripts/check-layout.sh` → PASS。全て終了 0。スキルファイルは変更していないため skills 追加検証は対象外。private の停止中 Actions は確認対象外。
- 構造・参照照合: 6.4 から参照する 8.1 が実在し、取得のコマンド・停止条件・照合へ渡す値が一致。7.4 の後続実装の責務、7.6 の API、既存 Spec/Plan の受け入れ条件とも一致。実文書のコマンド、復旧・除外のシナリオで保証を維持しており、固定文言のテストは追加していない。
- 自己レビュー: read-only sp-review が反証・PR 全体・検証の検出力を 1 回で確認し、Critical / Important / Minor の指摘はいずれも 0。全差分と変更 5 ファイルの全文、関連経路、独立入力、ガード対照、検証ログを確認した。初回 dispatch は必須の `Review scope` 不足で NEEDS_CONTEXT となりレビュー未実施。指定を補って実施した 1 回だけを数え、2 回目の自己レビューはしていない。
- レビュアーが範囲外としたもの: upsert/run_roles 接続（既存 Spec と #155 の境界に一致）、コメント取得中断・並行投稿対策の追加（今回変更していない別の原因/新しい要求なので無断追加しない）、実 GitHub 投稿・有料モデル確認（この読取・検証用変更の機能確認には不要）。新しい欠陥の指摘ではなく、入力指摘 2 件の採否は変わらない。
- 最終証拠の維持: 自己レビュー後の機能修正は無く、この Spec の結果記録だけを更新した。文書の SHA-256 と API・CLI・テストのバイト列は検証時から変わらないため E3〜E5 の前提は維持される。04:39 UTC に `uv run --no-project python <REPRO_ROOT>/verify_manual.py <CODE_ROOT> final` の 19 シナリオ（E3 と同じ期待結果）と、`CODE_ROOT` で `uv run pytest .agents/scripts/tests/test_review_records.py -p no:cacheprovider --basetemp <REPRO_ROOT>/final-pytest-tmp -q`（205 passed in 0.26s）を再実行し、終了 0。文書ハッシュの同一性、文書参照・経路表との照合と `git diff --check` の成功も確認した。最後の編集はこの結果記録だけで、検証対象の文書例・ソース・テストに変更は無い。レビューの指摘ゼロや上限到達は、経路の確認済み判定の根拠には使っていない。
- 作業時間: 04:19 UTC 開始。04:39 時点で約 20 分（入力・HEAD・全体精読と再現約 7 分、設計・文書修正と検証約 10 分、自己レビュー約 3 分）。最終検証・公開・片付けを含む所要時間は PR 状況コメントと完了報告に残す。
