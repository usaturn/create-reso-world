# issue-to-pr の明示 base 指定

## 管理・実行許可

- 状態: draft（実行許可と設計内容の承認は別）
- 対象: usaturn/create-reso-world #300
- 利用者の指示: `/skill:issue-to-pr #300 --assign inspect=claude-opus,devin-swe,pigod --merge`
- 許可範囲: 推奨案による設計・実装・検証・commit・push・PR、指定したレビュー修正ループの finalize によるマージ。
- この run の repository / remote / base: `usaturn/create-reso-world` / `origin` / `main`
- 取得した base SHA: `5dc093cc2ed6855fb15353d70c1e8bb3b12d2151`
- 作業場所: `/workspaces/reso-world/.worktrees/issue-300-explicit-base`
- 実装担当の検査結果: `assignment={agents:[self],fallback:[]}`, `self=true`（既定の適用）。
- ループ設定: 利用者指定 `inspect=[claude-opus,devin-swe,pigod]`、既定 `max_cycles=3`、fix implement は `claude-opus`、self-review / fix-check は `self`、fallback はすべて空。template は `.devcontainer/agent-runner.toml`、check-options の config は null。

## 意図と受け入れ条件

Issue の実装対象の `origin` に存在するブランチを `--base <branch>` または `--base=<branch>` で明示し、そのブランチの取得済み SHA から分岐して同じ base 宛てに PR を作る。未指定時は main。親 Issue / handoff が別 base を要求する場合は明示指定を必須にし、不一致では外部書き込み前に止まる。

Linux Dev Container、uv、Git、偽 gh とローカル bare remote で検証する。main と分岐した `feat/plugin-v2`（非 ASCII branch も代表例を確認）を用意し、main だけの内容が混入せず、base 固有の内容を失わないことを確認する。任意 remote・tag・commit 式への解釈、異なる checkout、base の移動、古い検証結果による公開・マージを防ぐ。

## 設計

### 入力と base helper

`resolve_issue.py` は `base`（未指定時 main）と `base_explicit` を既存の出力に追加する。Issue の参照の前後・等号形式を扱う。Git の branch 規則を使い、option、refs 名前空間、revision 式を branch として解釈しない。シェルの eval は使わない。

新規 `scripts/resolve_base.py` は `--checkout ROOT --repo OWNER/REPO [--base BRANCH] [--required-base BRANCH ...] [--expected-sha SHA]` を受け付ける。呼び出し側は base_explicit が真のときだけ --base を付ける。親・handoff にある required base をすべて渡す。repository の指定も矛盾していないことを呼び出し側が先に確認する。親 Issue / handoff の「統合先」「PR の向き先」「base」等の明示記述を controller が全文から意味で読み取り、根拠となる URL またはファイルと指定値を記録する（自然文の自動抽出 helper は作らない）。関連例・過去の記録を今回の指定と混同せず、複数の指定が矛盾する、または確定できない場合は停止する。

helper は追跡対象 checkout のルート、対応 repository と origin の fetch/push URL の一致を検証し、Git の環境変数による別 checkout 選択を避ける。GitHub の認証値を出力しない。完全な `refs/heads/<branch>` を取得し、remote の観測と取得した commit が一致した場合だけ `{repo, remote, branch, ref, sha}` を返す。remote は origin 固定。--expected-sha は捕捉済み SHA と違う場合に失敗する。ブランチ・worktree・PR を作る helper にはしない。

### 分岐・検査・公開

SKILL.md は helper が確定した SHA をコード用 worktree の分岐元とし、差分もその SHA を基準にする。worktree 直前・検証前・push 直前・PR 作成直前に repository / origin / branch / SHA を再確認する。base が移動したら未検証の組み合わせで続けず停止する。自動 rebase / reset / fork main 同期はしない。

`scripts/scan-before-push.sh` に任意の `--expected-base-sha SHA` を追加する。取得した base が指定 SHA と違えば検査成功を返さず、検査後にも remote の同じ heads ref が動いていないことを確かめる。既存の Gitleaks の設定・除外禁止・版検査・未公開範囲・成功時 HEAD SHA だけを返す仕様は維持する。既定の呼び出しとの互換性を保つ。

PR 作成には確定した branch 名を `--base` に渡し、作成後の `baseRefName`・base の SHA を確認する。GitHub 上の他者の更新をローカル操作と一括でロックできるとは保証しない。各境界で観測した移動は停止として報告し、PR 後のマージには後段の finalize の検証を必ず使う。PR 作成後に移動を見つけても PR を自動で閉じたり branch を消したりせず、公開済み URL と観測した差異を報告して停止する。

外部コードの文書は独立して create-reso-world / origin / main の SHA を取得する。文書用 worktree・scan・PR へコードの base を流用しない。同一 repository の場合はコードと文書を同じ PR に含める。

### マージと停止条件

後段は実 PR の base を取得する既存 review-fix-planning / finalize を維持する。HEAD 一致、base 移動、merge 第1親、CI の守りを弱めない。統合ブランチを使う代表テストでこの経路を確かめ、既存 base 移動等のテストを重複して増やさない。

main 以外への PR の `Closes` は GitHub が default branch へのマージ時のみ自動 close する点を明記し、未指定 --merge の終了範囲を変えない。既存 Refs / Closes の選択条件は維持する。

## 決定記録（Approaches）

| 項目 | 選択した案 | 検討した別案 | 理由 / 委任・停止条件 |
|---|---|---|---|
| base 確認 | 対象決定後の専用 helper | Issue resolver 内で fetch、手順文だけ | Issue repository とコード repository を混同しない。通常設計の委任による選択 |
| base 移動 | 固定 SHA との照合で停止 | 自動取り込みと再検証 | 対象の差し替えや未検証マージを避ける。停止は安全境界 |
| scan | optional expected SHA を追加 | 別の scan 実装を複製 | 検査範囲・設定を一元化し既存呼び出しを保持 |
| 後段ループ | 実 PR base の既存 guard を再利用 | 要求 base を全 helper に重複保持 | 既存実装は branch 非依存。代表テストで確かめる |
| 実行 | SDD、3 Task を同期で直列実行 | すべて inline | 入力 helper・scan・統合手順の責務を分けてレビュー可能 |
| スキル検証 | 旧手順と新手順の実行シナリオ比較 | 有料モデルでの pressure テスト | Issue は有料モデルのテスト起動を禁止。ローカル Git と偽 CLI に限定し、モデルの行動評価と称さない |

## 対象外・禁止

- 統合ブランチ新設、fork main の同期/reset/force push/削除、他者 worktree 変更。
- プラグイン機能 #98〜#100、キュー #242、ワールド cwd 対応、対象 repository / remote 拡大。
- テスト目的の実 GitHub 書き込み、実際の別 Issue 実装、有料モデル起動、新規 Actions。
- 今回の PR 自身の指定されたレビュー修正ループはテストではなく公開後の作業として実行する。

## 検証

恒久テストは S の対象取り違え・未検証公開・秘密検査範囲に限る。単なる argparse / 文言 / 一覧の固定照合は追加しない。既存正常対照と安全テストを再利用する。README の非ワールド検証3入口、diff check、最後のブランチ全体レビューを行う。
