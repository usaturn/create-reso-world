# Issue #361: runner 共通指示の安全制限

## 管理・実行許可

- 状態: `draft`（実行指示は設計承認として扱わない）。
- Issue: https://github.com/usaturn/create-reso-world/issues/361
- 利用者の実行指示: `#361 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。
- 追加指示: 「途中で main が進んでいる場合は留意して止めずに進めてください」。ただし適用される AGENTS.md / issue-to-pr の捕捉済み base の移動時停止は維持する。未検証の新 SHA への差し替えはしない。
- issue-to-pr による通常の設計判断・検証・commit・push・PR と、指定された修正ループの finalize によるマージまでが実行範囲。
- 基準: `usaturn/create-reso-world`, `origin`, `refs/heads/main`, `1b0df1212e47857e131d6936e0510520e4fb13ef`。

## 意図・範囲

runner の担当が worktree 内だけで操作したつもりでも、共有 stash や他セッションのプロセスを壊し得る。全 workflow 共通の依頼文に禁止と理由を明記する。技術的な sandbox を追加する変更ではない。

最新の coordinator 裁定（https://github.com/usaturn/create-reso-world/issues/361#issuecomment-6764063557）に従い、コードの変更は `tools/agent_runner/runner.py` と `tools/agent_runner/tests/test_runner.py` のみ。#350 は CLOSED。#353 が所有する `.agents/skills/issue-to-pr/scripts/implement_task.py` は変更しない。

## 設計・受け入れ条件

1. `Work in this worktree only` の直後の共通指示に、`git stash` の全操作（`git stash pop` を含む）を禁止し、stash が同じ repository の全 worktree で共有される理由を記す。代わりは許可された範囲の一時コピー、または書き込み可能な担当の自分の worktree の commit。
2. パターンによる停止（`pkill -f`・`killall`）を禁止し、停止可能なのは自分が起動したプロセスを PID で指定する場合だけとする。
3. 担当による `python`・`python3` の直接実行と `python -` への heredoc を禁止し、Python は `uv run` を使う。リポジトリ付属スクリプト内部の既存の bootstrap 例外は変更しない。
4. 禁止は書き込み可否の両方に適用する。write exceptions は許可された書き込み範囲の指定であって、これらの安全制限の解除ではない。read-only の担当へコピーや commit の許可を新たに与えない。
5. 指示は従来どおり空でない2行と区切りの空行とし、禁止事項を1行目に折り込む。`writes=...` の2行目と exceptions の見出し・順序・本文を維持する。呼出元の複数行・日本語本文を変えない。
6. fake adapter が実際に受け取る依頼文に stash とプロセス停止の禁止が残ることをテストする。F∩S: 指示脱落は実行エラーにならず、他セッションの作業消失・プロセス停止になり得る。理由をテストに書く。Python の単なる規約再掲だけの固定文言テストは追加しない。
7. runner と issue-to-pr の既存テストが成功する。実モデルを使うテストは追加しない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- |
| 配置 | 共通指示の1行目へ折り込む | 各 workflow に重複追加 / 独立行を追加 | 全 workflow を覆い、2行を前提とする CLI・文書・exceptions の既存仕様と所有範囲を維持 | 最新 coordinator 裁定。範囲外編集はしない |
| 守り | 指示と fake adapter の回帰検査 | コマンドの技術的遮断 | Issue は依頼文の修正。sandbox 導入は対象外 | 技術的強制の成功とは報告しない |
| 実装 | runner の issue/implement へ Task 単位で依頼 | self / pi-superagents 実装子 | 利用者の `--implement` を優先。検査結果 `self=false`, agents=`[pi_opencode-go_deepseek4-flash_max]`, fallback=`[]` | 失敗時 self へ切り替えない |
| レビューとマージ | 指定3レビュアー、修正担当 DeepSeek、最大3サイクル | 自分だけのレビュー | 利用者の assign をその順で適用。3は既定。self-review と fix-check は既定の self、fallback はすべて空 | finalize のみマージ。他の方法へ切替不可 |

## 対象外・反例

`self` の割当は外部担当を起動せず依頼文を持たないので対象外。悪意のある担当による指示無視・Git 共有状態の監査拡張・プロセス停止処理自体の改修・設定や runtime adapter の変更はしない。実環境の stash や他セッションのプロセスで再現しない。

## 検証

- 基準版: `uv run pytest tools/agent_runner/tests .agents/skills/issue-to-pr/tests -q`、364 passed、終了0（セッションの `baseline.log`）。
- RED→GREEN は既存の依頼文検査を拡張し、fake adapter の入力で確認する。書き込み例外のある/ない依頼も既存の流れで確認する。
- 同じ repository の独立した使い捨て worktree 2つで共有 stash の挙動を手動再現し、理由の独立した根拠を記録する。利用者の repository の stash は使わない。
- 詳細と要件対応は同日の Plan に記載。Actions は無効のまま、ローカル検証を使う。
