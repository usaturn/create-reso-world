# Issue #243: DSH 担当の撤去

- 文書管理: `usaturn/create-reso-world`
- 対象: `usaturn/create-reso-world#243`
- 着手時のコード: `7cf60715caf0026f7a4c95c72cdc2527e8075e2c`
- 状態: `draft`。内容の承認を受けた記録ではない
- 実行許可: 利用者の「`$issue-to-pr https://github.com/usaturn/create-reso-world/issues/243 --merge`」。推奨案で設計・実装・検証・PR 作成・指定のレビュー修正ループまで進める指示として扱う
- 追加指示: 利用者の「廃止したことについて、テストを書かないこと。TDD で実装しないこと。」を優先する

## 目的と範囲

使っていない DSH の担当と、そのためだけの親入力・bundle・隔離・成果照合・導入処理を撤去する。既定の `review.inspect` から `dsh-ccd` を外し、既存の `pi-deepseek` を使う。共通のレビュー保存、書き込み監査、停止確認、他のランタイムの挙動は維持する。

対象は `tools/agent_runner/`、`pr-review`、`pr-review-fix-loop`、`review-fix-planning`、Dev Container の設定・導入・現行の運用説明である。DSH 専用のテストと fixture は、対応する機能と一緒に削除する。共通の安全性テストは、残る機能の検証に必要なものを保持・整理する。

過去の `docs/superpowers/` の Spec・Plan、過去のレビュー結果・評価記録、利用者の個人設定と資格情報は変更しない。DSH 以外の adapter、Pi 経由の DeepSeek、Codex に対する既存の拒否規則は維持する。Dev Container の再構築、既存環境のアンインストールは行わない。

## 設計

### agent_runner と設定

`Runtime`、adapter の登録、`dsh.py` と `dsh_*.py`、専用の write path と receipt の処理を撤去する。`confined_writes` に基づく限定監査をなくし、起動前と実行後はすべての登録済み checkout を監査する。監査不能なら外部担当の起動前に拒否する。共通の停止・秘密情報除去・成果受け取り・後片付けの保証は残す。

個人設定の agent 定義に `runtime = "dsh"` が残る場合、設定の読み込み時点で DSH を撤去したことが分かるエラーにする。別のランタイムへ暗黙に置き換えない。古い `finalize-parent` hook や担当・fallback の移行は、最小限の案内として文書に残す。個人設定は自動編集しない。

### PR レビューと修正ループ

`prepare-parent`、`finalize-parent`、`pr_review_parent.py`、親からの bundle を使う private clone、DSH の観測 identity と staged 成果の親保存を撤去する。通常の checkout を使う prepare・complete・保存・cleanup は維持する。浅い checkout でも元の Git の shallow 境界・ref・FETCH_HEAD を書き換えずに PR 全体をレビューできるよう、必要な履歴は使い捨ての所有領域へ直接取得する。修正ループの DSH 用プロンプト、書き込み例外、成果照合、失敗分類、run_roles の DSH 拒否を撤去する。Codex の拒否と他のレビュアーの判定は維持する。

### Dev Container と文書

`install_beforehand.bash` の DSH 導入、対応する導入テスト、README の headless 手順を撤去する。雛形の `[agents.dsh-*]` と `finalize-parent` hook を外す。Dev Container の既存の bubblewrap など他用途の設定は残す。履歴文書の記述は書き換えず、現行手順の DSH 参照だけを整理する。

## 決定記録

| 論点 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 撤去の粒度 | DSH 専用経路を呼び出し元まで削除する | adapter だけ残す、または互換 stub を置く | 孤立した bundle・hook の保守を残さず、Issue の目的を満たす | Issue #243 の推奨案への委任。共通経路に用途があれば残して確認する |
| 既定 inspect | `dsh-ccd` を既存の `pi-deepseek` に置き換える | DSH を外して 3 担当だけにする | 現行の個人設定と同じ構成の DeepSeek 担当を維持できる | Issue の選択委任。重複モデルなどで設定が無効なら見直す |
| 監査 | 常に全登録を監査する | `confined_writes` を一般機構として保持する | DSH 以外に利用者がなく、限定監査の前提がなくなる | Issue #243 の決定事項。監査の安全条件が弱くなるなら停止する |
| 個人設定 | 読み込み前半で旧 runtime を明示エラーにする | 一般的な `invalid_value` に任せる、または自動移行する | 黙った変更を避け、必要な利用者操作を示せる | Issue #243 の決定事項。秘密の値をエラーへ出さない |
| テスト | DSH 専用テストを削除し、新しい廃止確認テストも TDD 工程も設けない。実行・静的解析・差分で確かめる | Issue に書かれた DSH 拒否の新規テスト 1 件 | 利用者の後続の明示指示と AGENTS.md のテスト採用基準を優先する | 利用者の追加指示。共通の安全性テストは残る保証に限り保持する |
| レビュー修正ループ | 既定の最大 3 サイクル、個人設定のレビュアー・修正担当を使う | 追加の `--assign` や上限指定 | 利用者は `--merge` だけを指定した。`check-options` はこの既定構成を受理した | 利用者の指定と既定の適用を区別する。ループの停止条件に当たれば成功扱いしない |
| Plan の実装担当 | 既定の `self` | `--implement` で外部担当を指定する | `implement_task.py check` が `self=true` を返し、利用者は上書きしていない | 雛形・個人設定の既定。Task の独立性に応じて実装方式を選ぶ |

## 受け入れと確認

1. 現行コード・設定・運用説明の DSH 参照は撤去され、検索の残りは過去の記録、この Spec・Plan、最小限の移行案内だけである。検索結果を写したテストは作らない。
2. 雛形と現行の個人設定を使う PR 修正ループを確認し、指定のレビュー修正ループを 1 サイクル以上実行して結果を観測する。実モデルの起動はループに必要な範囲に限る。
3. 一時的な設定に `runtime = "dsh"` を含めて読み込み、外部担当を起動する前に分かりやすいエラーで停止することを確認する。正常な設定の読み込みも対にして確認する。
4. README の「テスト」の入口のうち追跡対象向けの `run-tests.bash`、`check-layout.sh`、`pytest` と、関連する静的解析を通す。
5. 作業完了後、#175・#211 を理由付きで not planned として閉じ、#116 に撤去を記録する。#243 と PR の状態を再確認する。

## 制限

Issue にない別リポジトリへの反映、利用者設定の編集、追加の実モデル評価は行わない。`--merge` のマージは review-fix-planning の `finalize.py` だけが行う。
