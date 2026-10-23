# Issue #243: DSH 担当の撤去

- 文書管理: `usaturn/create-reso-world`
- 対象: `usaturn/create-reso-world#243`
- 着手時のコード: `7cf60715caf0026f7a4c95c72cdc2527e8075e2c`
- 状態: `completed`。実行・検証結果を記録した状態であり、内容の承認を受けた記録ではない
- 実行許可: 利用者の「`$issue-to-pr https://github.com/usaturn/create-reso-world/issues/243 --merge`」。推奨案で設計・実装・検証・PR 作成・指定のレビュー修正ループまで進める指示として扱う
- 追加指示: 利用者の「廃止したことについて、テストを書かないこと。TDD で実装しないこと。」を優先する

## 目的と範囲

使っていない DSH の担当と、そのためだけの親入力・bundle・隔離・成果照合・導入処理を撤去する。既定の `review.inspect` から `dsh-ccd` を外し、既存の `pi-deepseek` を使う。共通のレビュー保存、書き込み監査、停止確認、他のランタイムの挙動は維持する。

対象は `tools/agent_runner/`、`pr-review`、`pr-review-fix-loop`、`review-fix-planning`、Dev Container の設定・導入・現行の運用説明である。DSH 専用のテストと fixture は、対応する機能と一緒に削除する。共通の安全性テストは、残る機能の検証に必要なものを保持・整理する。

過去の `docs/superpowers/` の Spec・Plan、保存済みの PR レビュー結果、利用者の個人設定と資格情報は変更しない。現行ファイルに残る過去の評価入力・移植比較の DSH 専用記述は縮約し、元の詳細は Git 履歴で参照できるようにする。過去に別の担当を使ったと書き換えない。DSH 以外の adapter、Pi 経由の DeepSeek、Codex に対する既存の拒否規則は維持する。Dev Container の再構築、既存環境のアンインストールは行わない。

## 設計

### agent_runner と設定

`Runtime`、adapter の登録、`dsh.py` と `dsh_*.py`、専用の write path と receipt の処理を撤去する。`confined_writes` に基づく限定監査をなくし、起動前と実行後はすべての登録済み checkout を監査する。監査不能なら外部担当の起動前に拒否する。共通の停止・秘密情報除去・成果受け取り・後片付けの保証は残す。

個人設定の agent 定義に `runtime = "dsh"` が残る場合、設定の読み込み時点で DSH を撤去したことが分かるエラーにする。別のランタイムへ暗黙に置き換えない。古い `finalize-parent` hook や担当・fallback の移行は、最小限の案内として文書に残す。個人設定は自動編集しない。

### PR レビューと修正ループ

`prepare-parent`、`finalize-parent`、`pr_review_parent.py`、親からの bundle を使う private clone、DSH の観測 identity と staged 成果の親保存を撤去する。通常の checkout を使う prepare・complete・保存・cleanup は維持する。浅い checkout でも元の Git の shallow 境界・ref・FETCH_HEAD を書き換えずに PR 全体をレビューできるよう、必要な履歴は使い捨ての所有領域へ直接取得する。修正ループの DSH 用プロンプト、書き込み例外、成果照合、失敗分類、run_roles の DSH 拒否を撤去する。Codex の拒否と他のレビュアーの判定は維持する。

### Dev Container と文書

`install_beforehand.bash` の DSH 導入、対応する導入テスト、README の headless 手順を撤去する。雛形の `[agents.dsh-*]` と `finalize-parent` hook を外す。Dev Container の既存の bubblewrap など他用途の設定は残す。過去の Spec・Plan と保存済みの PR レビュー結果を変更せず、現行の評価資料と移植記録から DSH 専用の入力・旧手順を整理する。評価の日時と結果を別の構成で実施したと読み取れる表現にはしない。

## 決定記録

| 論点 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 撤去の粒度 | DSH 専用経路を呼び出し元まで削除する | adapter だけ残す、または互換 stub を置く | 孤立した bundle・hook の保守を残さず、Issue の目的を満たす | Issue #243 の推奨案への委任。共通経路に用途があれば残して確認する |
| 既定 inspect | `dsh-ccd` を既存の `pi-deepseek` に置き換える | DSH を外して 3 担当だけにする | 現行の個人設定と同じ構成の DeepSeek 担当を維持できる | Issue の選択委任。重複モデルなどで設定が無効なら見直す |
| 監査 | 常に全登録を監査する | `confined_writes` を一般機構として保持する | DSH 以外に利用者がなく、限定監査の前提がなくなる | Issue #243 の決定事項。監査の安全条件が弱くなるなら停止する |
| 個人設定 | 読み込み前半で旧 runtime を明示エラーにする | 一般的な `invalid_value` に任せる、または自動移行する | 黙った変更を避け、必要な利用者操作を示せる | Issue #243 の決定事項。秘密の値をエラーへ出さない |
| 過去の評価資料 | 現行ファイルの DSH 専用記述を縮約し、詳細は Git 履歴に残す | 現行ファイルにも旧担当一覧・導入観測をすべて残す | Issue #243 は過去の Spec・Plan の保存と、検索結果を最小限の撤去説明に絞ることを指定している。評価の日時・結果と、現在の構成で実施したかの区別は残す | Issue #243 の受け入れ条件を優先する。過去の評価を別の担当で実施したと読める変更はしない |
| テスト | DSH 専用テストを削除し、新しい廃止確認テストも TDD 工程も設けない。実行・静的解析・差分で確かめる | Issue に書かれた DSH 拒否の新規テスト 1 件 | 利用者の後続の明示指示と AGENTS.md のテスト採用基準を優先する | 利用者の追加指示。共通の安全性テストは残る保証に限り保持する |
| レビュー修正ループ | 既定の最大 3 サイクル、個人設定のレビュアー・修正担当を使う | 追加の `--assign` や上限指定 | 利用者は `--merge` だけを指定した。`check-options` はこの既定構成を受理した | 利用者の指定と既定の適用を区別する。ループの停止条件に当たれば成功扱いしない |
| Plan の実装担当 | 既定の `self` | `--implement` で外部担当を指定する | `implement_task.py check` が `self=true` を返し、利用者は上書きしていない | 雛形・個人設定の既定。Task の独立性に応じて実装方式を選ぶ |

## 受け入れと確認

1. 現行コード・設定・運用説明の DSH 参照は撤去され、`git grep -il dsh` の残りは過去の Spec・Plan、この Spec・Plan、最小限の撤去・移行案内だけである。検索結果を写したテストは作らない。
2. 雛形と現行の個人設定を使う PR 修正ループを確認し、指定のレビュー修正ループを 1 サイクル以上実行して結果を観測する。実モデルの起動はループに必要な範囲に限る。
3. 一時的な設定に `runtime = "dsh"` を含めて読み込み、外部担当を起動する前に分かりやすいエラーで停止することを確認する。正常な設定の読み込みも対にして確認する。
4. README の「テスト」の入口のうち追跡対象向けの `run-tests.bash`、`check-layout.sh`、`pytest` と、関連する静的解析を通す。
5. 作業完了後、#175・#211 を理由付きで not planned として閉じ、#116 に撤去を記録する。#243 と PR の状態を再確認する。

## 制限

Issue にない別リポジトリへの反映、利用者設定の編集、追加の実モデル評価は行わない。`--merge` のマージは review-fix-planning の `finalize.py` だけが行う。

## PR #249 レビュー修正サイクル 1（計画）

- 対象 HEAD: `2b2fc1181cb798ae4d3d8f3926accc3f80aefc18`
- 確認済み一覧: `reviews/usaturn/create-reso-world/#249-feat-issue-243-remove-dsh/verified/2b2fc1181cb7.json`。元の4指摘を3原因にまとめ、すべて現行 HEAD で確認した
- 実行許可: 利用者の `--merge` 指示に含まれるレビュー修正とマージの実行。文書の内容を承認済みにする指示ではない
- 結論: 対応する指摘が2件あるため、修正して既存 PR へ push する。修正後はループで再レビューする
- planner: `gpt-6-sol` / `codex`。レビューサイクル番号: 1

| レビューファイル | レビュアー・ランタイム | 対象 HEAD | 今回の入力 |
| --- | --- | --- | --- |
| `gpt-6.1-sol.md` | `gpt-6.1-sol` / `pi` | `2b2fc1181cb7` | 再実行 |
| `SWE-2-Max.md` | `SWE-2 Max` / `devin` | `2b2fc1181cb7` | 再実行 |
| `deepseek-deepseek-v4.1-flash.md` | `deepseek/deepseek-v4.1-flash` / `pi` | `2b2fc1181cb7` | 再実行 |
| `Grok-4.7.md` | `Grok 4.7` / `cursor` | `2b2fc1181cb7` | 再実行 |

| 元指摘 | 区分 | 現行 HEAD での根拠と判断 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1@2b2fc1181cb7` | 対応する | 旧 Pi の成功・期限切れ `BatchResult` には空の `unrelated_checkout_audit` が保存される。新しい厳格なモデルはその欄だけで4つの読取入口を拒否し、停止確認済みの資源も未確認として残す。保存済み run の再開という主要経路が止まる |
| `SWE-2-Max#I-1@2b2fc1181cb7` | 対応する（上と同じ原因） | 同じ旧結果の読取拒否を指す。別の修正を重複して作らず、上の1つの安全条件で閉じる |
| `Grok-4.7#M-1@2b2fc1181cb7` | 対応する | 外部の浅い checkout では PR レビューの Git 操作をセッション内の所有 Git で行うのに、担当への許可文は元 checkout の Git を書き込み先に列挙する。実行者に対象外の Git 変更を許す危険がある |
| `deepseek-deepseek-v4.1-flash#L-1@2b2fc1181cb7` | 対応しない | `step` 28回に対して `STEP_TOTAL=29` で最後が `[28/29]` と表示される。利用・検証・保存の主要処理は止まらず、今回の致命的な修正条件に当たらない。表示が実際の制御や失敗判定に使われると判明したときに見直す |

### 守る条件と影響経路: 保存済み結果

原因は DSH 専用欄をモデルから除いた後も、非 DSH の旧実行で保存された空欄を読み込む経路が残ったこと。**旧版の空配列だけを読み取り時に受け入れ、現行形式の出力では復活させず、空以外や未知の欄は拒否する。** 入力境界の `BatchResult` に限定した移行で、各呼出元に別々の変換を置かない。全件を許す `extra=allow` は予期しない記録の取り違えを隠すため採らない。過去の結果を一括で書き換える案は、保存済み成果を変更し失敗時の途中状態を生むため採らない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 旧版の空欄だけ受け入れる | `tools/agent_runner/models.py` の `BatchResult` 入力境界 | 修正する | 空配列付きの旧結果を受理し、空以外・未知欄を拒否する。現行の serialize に旧欄を出さない | 独立に構成した旧/現行/不正 JSON の入出力を照合する安全性テストと実行 | `f12c400`: 旧/現行の対照10ケースが期待どおり。代表テストは正常と観測ありの拒否を確認。変換を外す対照・無条件に捨てる対照で各1件失敗。担当結果 `implement-run/roles.json` |
| 停止確認済み資源を再開時に誤って未確認としない | `pr-review-fix-loop/loop.py` の保存結果・役割結果 | 既に満たす（共通の入力境界に依存） | 旧結果を読み、停止状態を元の記録どおり扱う | 旧結果の再開と資源監査を隔離実行 | `f12c400`: 旧結果の停止済み資源は `removed`。旧欄を除いた対照と同じ結果。10ケースの隔離実行に含む |
| 保存済み結果を正しい担当に結び付ける | `pr-review/review_run_record.py`、`issue-to-pr/implement_task.py` の読取入口 | 既に満たす（共通の入力境界に依存） | 旧結果の run と担当を読める | 旧結果で各入口を実行し、空以外は拒否する | `f12c400`: loop の2入口、attach-runner、issue-to-pr の全4入口で空欄を受理し、非空・null・未知欄を拒否 |
| 現行形式の厳格さを維持する | `StrictModel` と現行 `BatchResult` 出力 | 既に満たす | 無関係な追加欄は拒否され、旧欄を出力しない | モデルの serialize と不正 JSON の対照 | `f12c400`: `model_dump_json` に旧欄なし。未知欄は4入口で拒否。`tools/agent_runner` テストを含む1725件成功 |

### 守る条件と影響経路: レビュアーの書き込み先

原因は `helper_write_exceptions` が Git の実操作先を checkout の浅さに関係なく `source_git` として説明していたこと。**許可文には実際に helper が書く Git だけを列挙し、浅い checkout では元 Git への書き込みを許さない。** 入口ごとに独自の文面を作らず、共通関数へ浅い状態を明示して呼ぶ案を選ぶ。安全性テストは許可範囲を守るために必要であり、DSH の廃止確認を目的としない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 浅い元 Git に書き込みを許可しない | `pr-review/review_run.py` の `helper_write_exceptions` | 修正する | shallow なら source Git の worktree/refs/objects を許可しない。通常 checkout なら必要な許可を保つ | shallow/通常の両側で許可文と実操作先を独立に照合する安全性テスト | `f12c400`: 同一/別 Git × shallow/通常の4ケース成功。過大許可ガードを外す3種類の対照で計4件失敗。実 prepare/complete の一時テスト2件で書き込み先と許可文を照合 |
| ループの許可文が実操作先と一致する | `pr-review-fix-loop/loop.py` の `review_write_exceptions` | 修正する | checkout の shallow 状態が共通関数に渡り、元 Git の過大な許可が消える | 浅い外部 checkout のプロンプト生成を隔離実行 | `f12c400`: 通常と depth=1 の clone で同一/別 Git の許可文を生成。浅い元 Git 全体の許可は消え、保存ロックだけが残る |
| 自己レビューの許可文が実操作先と一致する | `review-fix-planning/run_roles.py` の `write_exceptions` | 修正する | 同じ shallow 判定が使われる | 外部担当の依頼文を隔離実行 | `f12c400`: 通常と depth=1 の clone で別/同一 Git の許可文を生成し、同じ結果を確認 |
| Git 履歴を元 checkout に書き込まない | `pr-review/pr_review_workspace.py` の shallow 分岐 | 既に満たす | 一時所有 Git に取得し、元の shallow 境界・ref・FETCH_HEAD が変わらない | 既存の浅い checkout 検証と差分を照合 | `f12c400`: 実 prepare/complete の一時テスト2件で浅い元 Git の変更は0件。既存の浅い checkout テストも含む全 Python 1725件成功 |

同じ条件の過去のレビュー修正はこの PR の履歴に無く、設計見直しのきっかけには当たらない。修正担当は既定の `claude-opus`。隔離 worktree の commit `41c6e53` を差分・停止を確かめて `f12c400` として取り込んだ。runner の終了コードは1で、理由は別作業の checkout の変更・撤去を全登録監査が検出したこと。担当自身は終了コード0・停止確認済みで、対象 branch の差分は無かった。controller は取り込み後に `run-tests.bash` 23件、`check-layout.sh`、全 Python 1725件を完走した。Gitleaks は修正後の13 commitで検出0件。

### 修正後の自己レビューと結論

`run_roles.py --phase self-review` を1回だけ呼び、既定の `self` で PR 全体の自己レビューと fix-check を実施した。自己レビューは指定 commit `f12c400` の全体差分を対象に指摘0件で、関連テスト9件が成功した。fix-check は修正の9主張がすべて成立し、8変更ファイルの検査、文書候補181件の判定、関連テスト83件と安全性テストの変異対照を完了した。未確認は0件。結果は `reviews/usaturn/create-reso-world/#249-feat-issue-243-remove-dsh/verified/f12c400fc2e4.fix-check.json` と同じ接頭辞の要約・文書候補に保存した。レビュー後にコードを変更していないため、自己レビューを繰り返していない。

fix-check の `V-1` は `tools/agent_runner/runtimes/cursor.rst:49` の説明が、shallow checkout でも共有 Git に worktree 登録を書き込むように読めるという文書の不一致である。旧版にも同じ説明があり、修正後の helper の許可文と実際の prepare/complete は、浅い元 Git を書き換えずに動く。既存の不正確な説明ではあるが、現行の利用手順や安全境界を破る致命的な問題ではないので、このサイクルでは対応しない。文書を根拠に実際の書き込み先を広げる運用が生じた場合、または新しい証拠で操作結果への影響が示された場合に見直す。自己レビューと fix-check に新たな致命的な指摘は無く、結論は既存 PR への修正 push と次サイクルの再レビューとする。
