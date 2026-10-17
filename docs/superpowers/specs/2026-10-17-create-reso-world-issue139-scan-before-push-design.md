# issue-to-pr の push 前検査

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/139
- 状態: `draft`（内容の明示承認は受けていない）
- 調査時 HEAD: `50e4a6b`
- 利用者の指示: `/skill:issue-to-pr` の読み込みと引数 `#139`。
- 実行許可: issue-to-pr の委任範囲に従い、通常の判断を推奨案で決め、検証・commit・push・PR 作成まで進める。マージ、除外設定の緩和、他のリポジトリのコード変更は含まない。
- Plan: 未作成。予定先は `docs/superpowers/plans/2026-10-17-create-reso-world-issue139-scan-before-push.md`。

## 意図と範囲

PR #133 はマージ済み。AGENTS.md と検査スクリプトは存在するが、issue-to-pr の第5章はコード・文書の branch を直接 push する記述のままになっている。検査に成功した commit 以外を公開せず、検出・検査の失敗を「途中で止めずに」の例外として明確にする。

変更は `.agents/skills/issue-to-pr/SKILL.md`、同ディレクトリの `evals/`、この Spec・Plan に限定する。検査スクリプト・installer・AGENTS.md・既存の helper・他のスキル・CI は変更しない。#135 の誤検出対策も対象外。

## 必要な挙動

1. コード用・文書用の各 worktree で、stage・commit・競合の再確認の後に、`bash "$PARENT_ROOT/scripts/scan-before-push.sh" -C <worktree>` を実行する。外部コードの checkout にスクリプトがあると仮定しない。base は本スキルが対応する `origin/main`。
2. 成功時に標準出力で受け取った SHA を、空値確認付きで `git -C <worktree> push origin "${SHA}:refs/heads/<branch>"` に渡す。検査後の HEAD を再解決して push しない。更新があれば改めて検査する。
3. 各 push の成功後にのみ対応する PR を作る。コード PR の後で文書側の検査が失敗した場合、文書 PR を作らず止まり、既に作ったコード PR の URL を報告する。自動で PR を閉じたり branch を消したりしない。
4. 検出、検査の失敗、gitleaks の未導入・版不一致では、未検査の push・対応する PR 作成に進まない。誤検出を理由に `.gitleaksignore`、inline の `gitleaks:allow`、作業ツリーの `.gitleaks.toml` で回避しない。
5. SHA 指定の push では `-u` による upstream 設定を前提にしない。PR は引き続き `--repo`・`--base main`・`--head <branch>` を明示する。
6. 停止時は理由、終了コード、既に公開したものと未公開のもの、残っている worktree・branch・文書・ログと次の操作を区別する。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 検査の呼び出し | 第5章でコード・文書それぞれのコマンドを示す | AGENTS.md への参照だけ | 行動が分かれる公開直前に具体化し、外部 checkout と文書側の検査漏れを防ぐ | issue-to-pr による通常判断の委任 |
| 検査スクリプト | PARENT_ROOT の既存スクリプト | 対象 checkout へコピー／別 helper を追加 | 既存の版・安全規則を一元管理する | スクリプトの失敗では停止 |
| push の対象 | 返された SHA を `${SHA}` で展開 | `git push -u origin HEAD` | 検査対象と送信対象を一致させ、zsh の `:r` 展開を防ぐ | 検査後に変更する場合は再検査 |
| 文書側の失敗 | コード PR を残して部分公開を報告 | rollback や文書 PR の先行作成 | 既存公開物への追加操作をせず未検査の公開を防ぐ | 検出・失敗で停止 |
| 検証 | 新しい行動比較のシナリオと人手判定、既存のテスト入口 | 文面一致の pytest | 文書の文字列ではなく選ぶ操作を確かめる | AGENTS.md のテスト採用基準 |

## 停止記録（2026-10-17）

builder check の `sp-recon` と行動比較の `sp-research` は、どちらも設定された `opencode-go/deepseek-v4.1-flash` への要求で HTTP 401 `api_key_expired` となった。ツールは `(no output)` を返し、artifact metadata の `exitCode` は 0 だが、`error` に認証エラー、usage は入出力とも0、出力ファイルは空。成功や評価結果とは扱わない。モデルの上書き許可は無いため変更せず、必要なツール・API の失敗として停止する。

- builder check は未完了。Plan・評価シナリオは未作成。SKILL.md は未変更。
- テスト・行動比較の回答取得・全体レビュー・push・PR 作成は未実施。この Spec は未レビューのローカルドラフトであり、公開未実施。
- 再開条件: 設定された provider の認証を利用者が復旧するか、利用者から一時的な別モデル指定を得る。その後、Issue 状態・競合を再確認し、この run の worktree を明示的に引き継ぐ。
- 記録: `/workspaces/reso-world/tmp/agents/issue-139.n4jc4s8t/`。ツールの metadata は `9906ddba_sp-recon_0_meta.json` と `2ee5dfaf_sp-research_0_meta.json`（親 pi セッションの `subagent-artifacts/`）。

## 行動比較と受け入れ条件（未実施）

既存の評価の履歴は書き換えず、`evals/push-scenarios.json` と `evals/validation.md` の追記に残す。現行スキル（追加指示なし）と変更後のスキルを、新しい独立コンテキストで各5回、同じシナリオに適用する。実際の push、GitHub 書き込み、認証情報の使用は禁止し、読むファイルと模擬入力を限定する。評価の出力を人手で読み、コマンドの意味・停止・報告で判定する。実際の送信の証明とは区別する。

対象は通常のコード公開、外部コードと文書の2段階公開、検出、文書側での失敗、gitleaks 未導入・版不一致、検査後の HEAD 変更。時間・既投入工数・完了優先の圧力を組み合わせる。対照が既に満たす項目には不要な強調を足さない。

- 両方の push が親 checkout の検査を通り、成功した SHA を送る。
- 失敗時に未検査の push・対応する PR を作らず、部分公開を正確に報告する。
- upstream 設定がなくても PR 作成を明示引数で進められる。
- 文面一致のテストを追加せず、README の3つの検証入口、JSON 構造、参照先、diff を確認する。
