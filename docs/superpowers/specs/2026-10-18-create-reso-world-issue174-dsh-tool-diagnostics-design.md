# Issue #174: DSH ツール結果と API 認証診断の分離

## 管理・実行許可

- 状態: draft（内容の承認は受けていない）
- 文書・実装対象: usaturn/create-reso-world
- Issue: https://github.com/usaturn/create-reso-world/issues/174
- 調査した HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- 利用者の指示: `/skill:issue-to-pr #174`（issue-to-pr スキルの明示読み込みと `#174`）
- 実行許可: スキルの委任に従い通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで実施する。Spec/Plan の承認を推測しない。マージしない。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-174-dsh-tool-diagnostics`
- branch: `fix/issue-174-dsh-tool-diagnostics`
- 確認用コピーは作らず、Spec/Plan を作業 PR に含める。

## 意図と根拠

DSH がファイル読み取りエラーから回復し、有効な final を返した場合に、行数やファイル名の 401/403 を API 認証エラーと誤認して回答を捨てないようにする。fallback なしの実行でも完成した回答を取得し、fallback ありでも不要な追加実行を避ける。

`_classify` は `tool_result(status=error).result` を `_diagnostic` に渡す。`_AUTH` は単独の 401/403 に一致し、構造・completed/final の確認前に `awaiting_authentication, None` を返す。HEAD 上の最小再現で 402 行は success、403 行は awaiting_authentication を確認した。変更前の DSH テストは 124 件成功した。

## 仕様

1. ファイル操作等のツール結果は任意の内容を含む。ツール結果中の数値・認証に見える文字列は、DSH のモデル API 認証失敗の証拠として使用しない。
2. `tool_result(status=error)` では既存の `_APPROVAL` による承認拒否・承認待ちの検出だけを残す。401/403 を同時に含む承認拒否も awaiting_approval とし、成功にはしない。
3. top-level `error`、非 completed の `turn_end.reason`、失敗ストリームに対する stderr の既存診断は変更しない。真の API 認証エラーは、有効な final が後続しても成功にしない。
4. completed/final・JSON payload・イベント構造・観測 identity の検証は維持する。非ゼロ終了や停止未確認を成功にしない runner の処理も変更しない。
5. 403 行、401 行、ファイル名 `401.py`、ファイル名 `403.py` の読み取りエラーを、それぞれ一つだけ含む実行で確認する。402 行を正常対照とする。
6. 実プロセスの偽 CLI が既存の session v4 fixture と有効な final を出す。上記各入力について、fallback なしで batch success と payload 保持、fallback ありでも primary 成功の 1 試行となることを確認する。
7. top-level 認証エラー、承認拒否、非ゼロ終了、identity 欠落・不一致の失敗条件を保つ。テストは実モデル・課金 API を一切使用しない。

## 変更する部分

- `tools/agent_runner/adapters/dsh.py`: tool_result の診断を承認に限定する。
- `tools/agent_runner/tests/adapters/dsh/test_adapter.py`: collector の payload 保持と真の診断の回帰。
- `tools/agent_runner/tests/adapters/dsh/fake_cli.py`: ファイルエラーを出す偽 CLI mode。
- `tools/agent_runner/tests/adapters/dsh/test_runner.py`: fallback 有無の実プロセス回帰。
- 本 Spec と対応 Plan。

## 対象外・編集禁止

全プロセスの sandbox 強化、output-dir の symlink 対応、実機 rebuild、DSH 更新、他の adapter、runner 全体、設定や共有認証情報には手を加えない。O-M1/G-M1 の診断ラベル問題は本 Issue では不採用とし、独立した持ち越し候補のまま維持する。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| ツール結果では承認診断だけを行う | 全経路の `_AUTH` を HTTP 文脈付き正規表現へ変更する | ツール本文と API の信頼境界を分ける最小修正。top-level の認証判定を弱めない | issue-to-pr の通常設計委任。真の認証エラーを成功にする必要が生じたら停止 |
| completed/final の既存検証へ進む | 有効な final があれば全エラーを無視する | final は認証・承認・終了・identity の失敗を覆せない | Issue の受け入れ条件 |
| 偽 CLI を実プロセスとして起動する回帰 | 実モデルで再現する／文字列検査のみ | batch/fallback の挙動を課金や資格情報なしで確認できる | 実モデル禁止。想定外の外部送信は停止 |
| inline の executing-plans | SDD による実装委譲 | 1 Task で fixture とテストを逐次変更する小さな修正。独立調査・最終レビューは別担当へ委譲 | issue-to-pr の実行方式選択規則 |

## 検証

- 新しい挙動テストが修正前に失敗し、修正後に成功することを確認する。
- DSH 全 124 既存ケースと新規ケースを実行する。
- README の入口（ワールドを除く）: `.devcontainer/run-tests.bash`、`scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。
- `git diff --check` とブランチ全体の読み取り専用レビューを実施する。
- 公開前に親 checkout の `scripts/scan-before-push.sh` を使い、検査した SHA のみを push する。private リポジトリの停止済み CI は確認しない。
