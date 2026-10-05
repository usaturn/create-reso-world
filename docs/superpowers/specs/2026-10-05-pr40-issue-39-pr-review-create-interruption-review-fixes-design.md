# PR #40 issue-39-pr-review-create-interruption のレビュー指摘の選別と修正

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/40
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `fix/issue-39-pr-review-create-interruption`
- 指摘を検証した HEAD: `a882bfdc3989edb182162c10cb9427014e32af92`
- 入力: `reviews/#40-fix-issue-39-pr-review-create-interruption/` 配下の全 4 ファイル
- 作成日: 2026-10-05
- 結論: **1（修正が必要）**。致命的な指摘 1 件（O-M1。G-M1 と同じ指摘）を、同じ条件に頼る経路（D-I1 の `failed` を含む）とあわせて直し、自己レビューで見つかった同じ条件の経路（stderr の読み手が閉じた中断）も直して、既存 PR へ push する
- 状態: completed（2026-10-05。修正・検証・自己レビューまで完了。push・状況コメントの結果は PR のコメントに書く）
- 経路: bounded。helper の中断時の出力 1 行の接頭辞と、スキル・設計 Spec の分類の文を揃える変更で、新しいサブコマンドや状態を足さない
- 実行許可: 2026-10-05 の利用者の依頼。PR とレビュー結果を確認して修正要否を三択で確定し、修正が必要なら推奨案を基本に修正・検証・PR 全体の再レビュー（自己レビューは 1 回まで。複数のサブエージェントに別々の観点で同時に担当させてよい）を経て push する。致命的な指摘だけを直し、同じ原因の箇所は PR の差分外も直す。`pr-review` は使わず、専用の worktree で作業する
- 作業場所: 既存の worktree `.worktrees/issue-39-create-interruption`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致）を専用の worktree として使った
- 関連: 設計 `docs/superpowers/specs/2026-10-05-issue-39-pr-review-create-interruption-design.md`

## 1. レビュー入力

| ファイル | 対象 HEAD | 指摘 | 判定 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `a882bfdc3989` | Medium 1・Info 1 | Approve |
| `gpt-6.1-sol.md` | `a882bfdc3989` | Medium 1 | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `a882bfdc3989` | Low 1・Info 1・未検証候補 1 | Approve |
| `SWE-2-Max.md` | `a882bfdc3989` | Low 1・Info 2 | Approve |

対象 HEAD はすべて、選別時点の PR の head（`gh pr view 40 --json headRefOid`）と同じである。選別を始めた時点の base（`origin/main`）は `a6e2c41` で、PR の分岐点と同じだった。作業中に `e6edcf8` へ進んだ（5.2 節）。

## 2. 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 2（O-M1、G-M1。同じ指摘） |
| 対応しない | 7 |

判定は、致命的かどうか（秘密情報の露出、データの消失、了承の無い操作・誤った対象への操作、手順どおりで誤った結果・主要な処理が止まる、セキュリティ）と、現行 HEAD での確認で行った。重大度ラベル・票数・Approve では決めていない。

### 2.1 全指摘一覧

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| O-M1（Opus Medium） | シグナルで中断した `create` が `error:` 行を出し、スキルでは helper のエラーに分類されて `inspect`・`abandon` の復旧経路に進まない | **対応する** | 手順どおりで誤った結果になる。PR が直す対象の中断（設計 D-4 が想定する「ツールのタイムアウトは SIGTERM の後に SIGKILL」、GNU `timeout`、Ctrl-C）で、スキルどおりに進むと片付けられる試行を「helper のエラー」として停止し、worktree を残す。Issue #39 の受け入れ条件 3（手動の復旧を要しない取り扱い）がこの経路で満たされない。現行 HEAD で再現した（5.1 節） |
| G-M1（GPT Medium） | SIGTERM 中断が helper のエラー扱いになり復旧手順に入れない | **対応する** | O-M1 と同じ |
| D-I1（DeepSeek Info） | 手順 2 の「`absent` 以外なら `abandon`」と「helper のエラーなら `abandon` しない」が `inspect` の `failed` で食い違う | 対応しない（同じ修正で解消） | 単独では致命的でない（`failed` の試行を `abandon` しても、draft があれば拒否され、消えるのは helper が作ったものだけ）。ただし O-M1 の守る条件（3 章）に頼る経路なので、表の「修正する」の行として同じ PR で直した |
| O-I1（Opus Info） | `initializing` ロックの判定が git の翻訳に依存する | 対応しない | 翻訳のあるロケールでは `abandon` が「利用者のロック」として拒否し、何も消さない側に倒れる。この Dev Container の git には翻訳カタログが無い（5.1 節） |
| S-L1（SWE Low） | 契約テストが `create` の `--attempt-id` 必須化を固定していない | 対応しない | SKILL.md から `--attempt-id` が抜けても、`create` は argparse の終了コード 2 で即座に失敗し、worktree を作らない。誤った結果は起きない。文言の存在確認のテストは足さない方針（`AGENTS.md`、設計 8 章） |
| S-I1（SWE Info） | 試行 ID の照合がリポジトリを見ず、別リポジトリの同じ PR 番号・同じ試行 ID で相互に操作できない | 対応しない | 拒否は何も消さない側に倒れる。起きるのは、同じ一時ルートで別リポジトリの同じ PR 番号に、ナノ秒の時刻が同じ試行 ID が重なったときだけ |
| S-I2（SWE Info） | `mkdtemp` から journal の `started` 確定までの間、実行中の `create` が `inspect` で `absent` に見える | 対応しない | D-L1 と同じ（下記） |
| D-L1（DeepSeek Low） | `create` の起動直後（journal 作成前）に `inspect` が `absent` を返し、スキルが再試行を許すため、生きている試行が残り得る | 対応しない | 窓は起動から `started` の記録までの 70〜108 ms（モデル名・main checkout・commit の確認）で、ツール呼び出しがその間に helper を止めずに終わり、すぐ `inspect` する必要がある（5.1 節）。起きても、先の試行は `session.json` まで作る通常のセッションとして残り、記録済みの試行 ID で `inspect`・`abandon` できる。データは失われない |
| D-U1（DeepSeek 未検証候補） | `test_abandon_waits_for_a_checkout_that_outlives_create` が高負荷時に落ち得る | 対応しない | 高負荷では再現した（5.1 節）が、原因は候補の PID ファイルではなく、テストが `worktree-add` の記録（git を起動する前に書く）を見た直後に `create` を止める待ち合わせ方である。helper とスキルの挙動は正しく、負荷が無ければ落ちない。CI は停止中（`AGENTS.md`）で、マージの判断を誤らせない |

## 3. 守る条件と影響経路

守る条件: `create` が結果の JSON を返さずに終わったとき、スキルが「helper のエラー」として停止するのは helper のエラー（終了コード 2、journal では `failed`）だけで、シグナルやツールのタイムアウトによる中断は `inspect`・`abandon` の復旧経路に進む。どの経路でも、二つの判定材料（ツールの出力の接頭辞と `inspect` の `status`）が同じ結論を出す。

| 経路（`create` の終わり方） | エージェントに見えるもの（修正後） | 判定 |
| --- | --- | --- |
| pi の bash ツールのタイムアウト（プロセスグループに SIGKILL） | 途中の進捗行と `Command timed out after N seconds`。`error:` 行なし | 既に満たす: 復旧経路。`inspect` は `running`（git が生き残る）か `vanished` |
| Claude Code の Bash のタイムアウト | コマンドは止まらずバックグラウンドへ移る | 既に満たす: helper は完了まで動く。結果を受け取れなければ `inspect` が `running`・`completed` を返す |
| GNU `timeout`（既定 SIGTERM）、ランタイムの SIGTERM、端末を閉じた SIGHUP | 修正前は `error: create interrupted by SIGTERM`。修正後は `interrupted: create interrupted by SIGTERM`、終了コード 143（`timeout` は 124） | 修正する: helper が `interrupted:` で始める。スキルの入口の条件に「シグナルによる中断は `interrupted:` 行を出す」と書く |
| Ctrl-C・`timeout -s INT`（SIGINT） | 修正前は `error: interrupted by SIGINT`。修正後は `interrupted: create interrupted by SIGINT`、終了コード 130 | 修正する: 同上 |
| helper のエラー（`WorkspaceError`・`OSError` など） | `error: ...`、終了コード 2。journal があれば `inspect` は `failed` | 修正する: スキルの手順 2 で `failed` を `abandon` の対象から外し、helper のエラーと同じく停止する |
| 結果が出力されずに終わった（出力の消失など）が、helper は完了していた | 出力なし。`inspect` は `completed` | 既に満たす: `abandon` して作り直す（設計 D-6・D-7） |
| `uv run` 自身のエラー | `error: ...`（uv の出力） | 既に満たす: helper は動いておらずセッションも無い。helper のエラーと同じく停止する |
| SKILL.md の `SESSION_JSON` を読む項の「ヘルパーが失敗した場合は…停止」 | 中断も「失敗」と読める | 修正する: `create` が結果を返さずに中断した場合は上の `inspect`・`abandon` の手順に従う、と限定を足す |
| ツールが helper を止めずに出力の読み手だけを閉じた（パイプを閉じた）中断 | 修正前は次の進捗行の書き込みが `BrokenPipeError` になり、journal が `failed` になる。手順 2 の新しい `failed` の扱いでは停止する（`a882bfd` の手順では `abandon` して回復していた） | 修正する（自己レビューで追加）: 進捗行の stderr への書き込みの `OSError` を無視し、journal を正とする。`create` は最後まで進み `completed` になる |
| `save`・`cleanup` など `create` 以外のサブコマンドの SIGINT | 修正後は `interrupted: save interrupted by SIGINT` など | 対象外: スキルは `create` 以外の中断の復旧手順を持たず、結果の JSON が無ければ失敗として停止する（設計 2 章の範囲外）。接頭辞は判定に使っていない |

## 4. 修正内容

- `.agents/skills/pr-review/scripts/pr_review_workspace.py` の `main()`: `CreateInterrupted` と `KeyboardInterrupt` の stderr を `error:` ではなく `interrupted:` で始める（`interrupted: create interrupted by SIGTERM`、`interrupted: <サブコマンド> interrupted by SIGINT`）。終了コード（128＋シグナル番号）と journal の記録は変えない
- `.agents/skills/pr-review/tests/test_pr_review_workspace.py` の `test_terminated_create_records_the_signal`: SIGTERM で中断した `create` の stderr に `error:` で始まる行が無いことを確かめる 1 行を足した。修正前の helper では `['error: create interrupted by SIGTERM']` で失敗し、修正後は成功する
- `.agents/skills/pr-review/scripts/pr_review_workspace.py` の `CreateJournal.record`（自己レビューで追加）: 進捗行を stderr へ書くときの `OSError` を無視する。journal への書き込みの失敗は従来どおり `create` を止める
- `.agents/skills/pr-review/tests/test_pr_review_workspace.py` の `test_create_outlives_a_reader_that_closed_its_stderr`（自己レビューで追加）: stderr が `BrokenPipeError` を返す状態で `create` が完了し、journal の終端が `completed` になることを確かめる。修正前の helper では `BrokenPipeError` で失敗した
- `.agents/skills/pr-review/SKILL.md` の手順 2: 入口の条件に「シグナルによる中断は `interrupted:` で始まる行を出す」を足し、2 番目の手順を「`absent`・`failed` 以外なら `abandon`」にして `failed` は helper のエラーと同じく扱うと書いた。最後の段落の helper のエラーに「`error:` で始まる行。journal があれば `inspect` の `status` は `failed`」を足した。`SESSION_JSON` を読む項の「ヘルパーが失敗した場合は…停止」に、結果を返さずに中断した `create` は上の手順に従うと限定を足した
- `.agents/skills/pr-review/references/time-budget.md`: S23 の条件をシグナルによる中断と `interrupted:` 行を含む形にし、S27（`inspect` が `failed`）を足した
- 設計 Spec: 冒頭にこの文書への参照、D-3 に stderr の書き込みが失敗しても続けること、D-4 に中断時の接頭辞、D-7 に入口の条件と `failed` の扱いを書いた。7 章の検証シナリオの範囲（S23〜S27）と 8 章のテスト方針に合わせた。Plan と 9 章は変更前の記録として残す

選んだ案と他の案:

- スキル側で終了コードによって helper のエラーと中断を見分ける案（GPT の推奨）もあった。pi はタイムアウト時に終了コードを返さず、`SESSION_JSON=$(...)` の形では終了コードを読む手順が増える。エージェントが確実に見られるのは出力の行なので、helper 側で接頭辞を分け、スキルの「`error:` で始まる行＝helper のエラー」をそのまま成り立たせた。そのうえで、出力が見えなかった場合にも `inspect` の `status`（`failed` と `interrupted`）で同じ結論になるようにした

## 5. 検証

### 5.1 修正前（PR の head `a882bfd`）の再現

サブエージェント 2 体に独立に委譲した（指摘の再現を `a882bfd` の隔離 worktree と使い捨てリポジトリで行う担当、Spec・Plan・time-budget.md・SKILL.md・helper の全行を照合する担当）。

- O-M1・G-M1: `timeout -s TERM|INT|HUP 3` で `create` を中断した 18 通り（このコンテナの `/usr/bin/timeout`（uutils）と GNU 版、`--preserve-status` の有無、`uv run` 経由と直接の python）すべてで、stderr の最後の行が `error: create interrupted by SIGTERM`・`error: create interrupted by SIGHUP`・`error: interrupted by SIGINT` になった（helper の終了コードは 143・129・130、`timeout` で包むと 124）。`error:` で始まる行はこの 1 行だけで、進捗行は `pr-review create <ATTEMPT_ID>: <時刻> <phase>` の形である。続く `inspect` は `interrupted`（`uv run` とフックの経路では git の子がロックを持つ間 `running`、`--wait` で `interrupted`）、`abandon` はすべて成功した。uutils の `timeout` は直接の子（uv）にだけシグナルを送り、uv が helper へ転送するので、このコンテナで `timeout 600 uv run ... create` と包むとこの経路に入る。修正後のテスト（4 章）も、修正前の helper では `['error: create interrupted by SIGTERM']` で失敗した
- D-I1: helper のエラーで終わる 3 経路（journal 作成前の不正な commit、worktree 作成前の保存先の親が通常ファイル、worktree 作成後の main checkout の変化・保存先がディレクトリ）を再現した。終了コードは 2、journal があれば終端は `failed` で、`create` は自分では片付けない。`abandon` は `failed` を拒否せずに消す。捕捉されない例外は Traceback と終了コード 1 で、`error:` 行は出ないが journal は `failed` になる
- D-L1・S-I2: 起動から `started` の記録まで `uv run` 経由で 82〜108 ms、直接で 70〜78 ms（各 5 回）。`rev-parse --verify` を 3 秒遅らせるスタブで、`create` の実行中に `inspect` が `absent` を返し、その後 `create` が `completed` になることを再現した
- O-I1: この Dev Container の git 2.55.0 の翻訳カタログ（`/usr/local/share/locale/*/LC_MESSAGES/git.mo`）は 20 言語で ja は無く、`LANG=ja_JP.utf8` では英語になる。`LANGUAGE=de` で checkout 中に中断すると、ロックの理由が `initialisiere` になり、`abandon` は拒否した（何も消さない）
- S-I1: 別リポジトリの同じ PR 番号・同じ試行 ID で、`inspect`・`abandon`・`create` がいずれも終了コード 2 で拒否し、元のセッションは無傷だった
- D-U1: `yes` を 8 本（nproc）で 1/10、32 本で 9/40 失敗した（`DID NOT RAISE WorkspaceError`。このとき `inspect` は `vanished`）。負荷なしでは 0/10。取り残された `sleep 60` は 0 本で、候補の PID ファイルの順序では起きていない
- S-L1: `test_pr_review_skill_contract.py` に `attempt`・`inspect`・`abandon` の検査が無いことを確認した。`--attempt-id` が無い `create` は argparse の終了コード 2 で終わり、セッションを作らない
- 修正前の `uv run pytest .agents/skills/pr-review -q`: 206 passed

### 5.2 修正後（専用の worktree）

| 時点 | `uv run pytest .agents/skills/pr-review -q` | `uv run pytest tests/skills .agents/skills -q` | `bash .devcontainer/run-tests.bash` | `bash scripts/check-layout.sh` |
| --- | --- | --- | --- | --- |
| `b59af75`（修正） | 206 passed（exit 0） | 547 passed・1 skipped（exit 0） | 27 本 PASS（exit 0） | PASS（exit 0） |
| 自己レビュー後の修正（stderr の書き込み） | 207 passed（exit 0） | 548 passed・1 skipped（exit 0） | 27 本 PASS（exit 0） | PASS（exit 0） |

- 足した assertion は、`a882bfd` の helper に差し替えると `AssertionError: assert not ['error: create interrupted by SIGTERM']` で失敗し、`b59af75` の helper で成功した
- 既存の固定文字列の検査で失敗したものは無い。`b59af75` では新しいテスト関数を足さず、既存の SIGTERM のテストに、スキルの判定に使う接頭辞の 1 行を足した。自己レビュー後の修正では、stderr が閉じても `create` が完了することを確かめるテストを 1 件足した（修正前の helper では `BrokenPipeError` で失敗した）
- base（`origin/main`）は作業中に PR #38 のマージで `e6edcf8` へ進んだ。進んだ分（`review-fix-planning` とその文書）は PR #40 の変更ファイルと重ならない

## 6. 修正後の自己レビュー

`b59af75` に対して 1 回だけ行った。新しい文脈のサブエージェント 3 体に、別々の観点を同時に担当させた。各担当には、守る条件と影響経路の表（3 章）、修正の差分、実行した検証、未確認の事項を渡した。`pr-review` スキルは使っていない。

| 観点 | 結果 |
| --- | --- |
| 反証 | 致命的な指摘なしの判定。Low 1 件・Info 2 件。uv 経由のグループへのシグナル 320 回（0〜200 ms の任意の時点、SIGTERM・SIGINT・SIGHUP）で `error:` 行も `failed` も 0 件。uutils `timeout` 経由も `interrupted:` 行・`interrupted`・`abandon` 成功 |
| PR 全体 | 致命的な指摘なし。`abandon` の拒否条件と直接削除の経路、ロックの順序（デッドロックなし）、手順 2 の分岐、`save`・`verify`・`cleanup` の安全条件を確認。中断の負荷試験 60 回と、他のレビューの `create` と同時に `abandon` する試験 40 回で、`abandon` はすべて成功し、相手の worktree は壊れなかった |
| 検証の検出力 | 致命的な指摘なし。足した assertion は `a882bfd` の helper で失敗し、`b59af75` で 15 回とも成功。起動方法 4 通り × シグナル 3 種 × 止める工程 2 か所の 24 通りで、`b59af75` は `error:` 行 0・`interrupted:` 行 1、`a882bfd` は全通りで `error:` 行が出た |

自己レビューで出た指摘の判定（3 章と同じ基準）:

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| 出力の読み手だけが閉じると、次の進捗行の書き込みが `BrokenPipeError` になり、試行が `failed` になって停止する（反証 Low、PR 全体 N-1。2 体が独立に再現） | **対応する** | 3 章の守る条件（中断を helper のエラーとして止めない）が破れる経路で、今回の `failed` の扱いが `a882bfd` の手順（`abandon` して回復）より悪くした。到達条件はツールが helper を止めずにパイプだけを閉じることで、pi（グループに SIGKILL）・Claude Code（バックグラウンドへ移す）・Cursor では起きず、Codex・Devin は未確認。データは失われないが、修正の守る条件として直した（4 章） |
| 設計 Spec が参照する review-fixes Spec が `b59af75` に入っていない（反証 Info、PR 全体 N-4） | 対応しない（push 前にコミットする） | この文書は結論 1 の手順どおり、自己レビューの後に 1 回だけコミットする |
| `started`・`completed` の記録の書き込み失敗（容量不足など）で、`error:` 行が出るのに journal に終端が無く `vanished` になる。中断の後に 2 回目の SIGTERM がハンドラを戻した後に届くと `interrupted:` 行が出ない（反証 Info） | 対応しない | どちらもスキルの結論は変わらない（前者は `error:` 行で停止、後者は `error:` 行が無いので復旧経路）。後者は 320 回中 2 回 |
| SIGINT・SIGHUP・`uv run` 経由の中断を見るテストが無い。`interrupted:` 行があることは確かめていない（検出力 N-1〜N-3） | 対応しない | テスト追加の提案。現行の挙動は 24 通りの実行で確認した。SIGINT は親が無視していると届かない環境があり、テストにすると環境で結果が変わる |
| 同時のレビューが同じ管理ディレクトリ名を使うと、`abandon` が「worktree record belongs to another worktree」で拒否する（PR 全体 N-2） | 対応しない | 何も消さない側に倒れる。設計 D-6 の拒否条件どおり |
| Codex の `exec_command`・Devin の `exec` は長い処理を自動でバックグラウンドへ回すので、「結果を返さずに終わった」と読むと完了するはずの `create` を `abandon` する（PR 全体 N-3） | 対応しない | ツールはプロセスが動き続けていることと続きの読み方を返し、手順 2 の条件は呼び出しが「終わった」場合である。誤って読んでも `inspect` が `running` を返して待ち、`completed` の試行の `abandon` で消えるのは helper が作ったものだけ。PR の変更前からの設計（Opus のレビューも Codex の挙動を確認して指摘していない） |
| Claude Code の Bash は呼び出しの間でシェル変数を引き継がないので、`ATTEMPT_ID=$(date ...)` だけを実行すると値が失われる（PR 全体 N-5） | 対応しない | 手順 2 の他の変数（`PR_URL`・`MAIN_ROOT`・`PR_HEAD` など）と同じ扱いで、スキルは試行 ID を進捗記録に残すと定めている。空の試行 ID は helper が worktree を作る前に拒否する |
| 翻訳のある git でロックの理由が訳され `abandon` が拒否する（PR 全体 N-5） | 対応しない | O-I1 と同じ |

自己レビューの後の修正（stderr の書き込みの `OSError` を無視する）は再レビューしていない。修正後の helper に対し、使い捨てリポジトリで `git worktree add` を post-checkout フックで止め、進捗行を 1 行読んでから stdout・stderr の読み手を閉じた。`create` は最後まで進み（終了コード 120。stdout の書き出しに失敗したため）、`inspect` は `completed`、`abandon` は成功した。

## 7. 所要時間（UTC）

| 区間 | 時刻 | 所要 |
| --- | --- | --- |
| レビュー 4 件・PR・Issue・変更ファイル全文（helper・SKILL.md・time-budget.md・設計 Spec・テスト）の確認、指摘の再現と Spec・Plan の照合を 2 体に委譲 | 14:40〜14:50 | 約 10 分 |
| 修正（`b59af75`）、テストの赤→緑の確認、検証一式 2 回、委譲の結果の反映 | 14:50〜15:03 | 約 13 分 |
| 自己レビュー（3 体を同時に） | 15:03〜15:19 | 約 16 分 |
| 自己レビュー後の修正と検証、この文書の記入 | 15:19〜15:28 | 約 9 分 |
