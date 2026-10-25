# Issue #178: review-verify の accept の保存で I/O のエラーが起きても、以前の確認済みの一覧を壊さず、同じ run で受け取り直せるようにする

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/178（ラベル `enhancement`。親 Issue・依存・コメントは無い。関連: PR #171、#154、#177、PR #191。元の判断: https://github.com/usaturn/create-reso-world/pull/171#issuecomment-6254225617）
- 状態: `draft`。内容の承認は記録しない
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue178-accept-io-recovery.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-178-accept-io-recovery`（branch `fix/issue-178-accept-io-recovery`）。PARENT_ROOT: `/workspaces/reso-world`
- 基準: `origin/main` の `c1fdc56`。Issue の検証 commit `03d9aac7` から、`accept` の保存の処理は変わっていない（#177 で起動の前の検査が入り、行番号がずれた）
- 実行許可: 2026-10-25（JST）、利用者が `/issue-to-pr #178 --merge --max-cycles 3` を実行した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成（`Closes #178`）まで続け、PR の作成後に PR 修正ループを回し、修正不要と確かめられたらループの中の `finalize.py` がマージと関連 Issue の更新まで行う。これは実行の許可であり、この文書の内容の承認ではない。下の判断は、どれも確認を取らずに決めたエージェントの判断である
- ループの設定: `loop.py check-options --max-cycles 3` の出力は `options={"max_cycles": 3, "assign": {}, "template": "/workspaces/reso-world/.devcontainer/agent-runner.toml", "config": null}`。`--max-cycles 3` は利用者の指定、`assign: {}`・`template`・`config: null` は既定の適用。レビュアーは `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正の担当は `claude-opus`、自己レビューと修正の確認は `self`（いずれも設定のとおり）
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、`--implement` は付けていない

## 意図

review-verify の `dispatch.py accept`（mode `fix_check` の外部の担当の結果の受け取り）は、検査を通った結果を `verified/` に sidecar（`<to12>.statement-candidates.json`）→ 本体（`<to12>.fix-check.json`）の順に `os.replace` で置く。同じ `to` で受け取り直すとき（`references/fix-check.md` が認めている）に 2 件目の置き換えが `OSError` になると、以前に受け取った有効な組が「古い本体＋新しい sidecar」になって `validate` を通らなくなる。同じ run の accept は、保存先が dispatch 時と違うので拒否され、直すには外部の担当をもう一度起動するしかない。

保存の途中で捕まえられる I/O のエラーでは、以前に受け取った結果を不整合な組のまま残さず、原因を直した後に同じ run を受け取り直せるようにする。誤って受け取らない（validate が不整合を拒否する）ことは今も守られているので、セキュリティの問題としては扱わない。traceback の見た目を直すことは目的にしない（Issue の「原因と位置」）。

## 確認した事実（2026-10-25、`c1fdc56`）

- `accept`（`.agents/skills/review-verify/scripts/dispatch.py:514-572`）は、534 行と 558 行で、保存先全体を dispatch 時の snapshot と照合する（`require_unchanged_review`。違えば終了コード 1）。559-571 行で `verified/` を `mkdir(exist_ok=True)` で作り、`mkdtemp(prefix=".accept-")` の一時ディレクトリに 2 件を `write_text` で書き、sidecar → 本体の順に `os.replace` し、`finally` で一時ディレクトリを `rmtree(ignore_errors=True)` で消す。2 件目が失敗しても 1 件目は戻らず、初回の保存では作った `verified/` も残る
- `main`（577-586 行）の accept は `AcceptError` だけを捕まえるので、`OSError` は traceback で終わる
- `snapshot_review`（232-275 行）が記録するのは、root の `mode:dev:ino`、各ディレクトリの `mode`、各通常ファイルの `mode:sha256`、各リンクの `mode:リンク先の sha256`。通常ファイルの inode・mtime は記録しない。違いの検出は `review_changes`（278-284 行）で、観測できなければ `<review snapshot unavailable>` を返す
- `review_findings.py validate <fix-check.json>` は、同じディレクトリの sidecar を読んで突き合わせる（`.agents/review-findings.md` 424 行）。sidecar が無ければ終了コード 66
- `references/fix-check.md`: 53 行は終了コード 1 を「受け取らない。helper は正式な成果物を追加保存せず、理由を stderr に 1 行出す」とする。113 行・118 行は「同じ to でやり直すと既存結果を置き換える」「accept は sidecar → fix-check JSON の順で保存し、2件同時の一括置換を保証しない」とする
- 呼び出し側: review-fix-planning の `references/execution.md` 2.4 は、セッションごとに作る `$FIX_STAGING` を保存先にして accept し、「終了コード 0 のときだけ受け取る」。手順はこの変更で変わらない
- リポジトリには、公開の後の失敗で以前の状態に戻す書き方が既にある（`scripts/meshy_conversion.py` の `convert_operation`）
- 作業のファイルシステム（`/workspaces/reso-world`）は ext4
- 変更の前の基準: `uv run pytest .agents/skills/review-verify` は 66 passed（24.10 秒）

## 受け入れ条件（Issue #178）

| ID | 条件 |
| --- | --- |
| A-1 | 既存の有効な組を新しい有効な組で置き換えるとき、捕まえられる 2 件目の書き込みの失敗で、以前に受け取った結果を不整合な組のまま残さない |
| A-2 | 初回の保存の途中の失敗と既存の結果の更新の失敗を分け、何が残り、どう回復するかを定義する。同じ run を安全に受け取り直せ、外部の担当を起動し直さずに回復する経路を用意する |
| A-3 | 失敗の後の本体・sidecar・一時ファイル・既存の状態を確かめる実行の回帰テストを足す。終了コードだけを確かめない |
| A-4 | PR・skill・inventory の照合、停止の確認、snapshot の全体の条件を弱めない。他者が保存先を変えたものを、自分の途中の出力と取り違えて消したり戻したりしない |
| A-5 | 文書に、I/O のエラーで保証する回復の範囲と、保証しない突然死・最後の観測の後の競合を分けて書く |

## 設計

### 1. 保存を「置いて、失敗したら自分が置いたものだけを戻す」処理にする

`accept` の保存（今の 559-571 行）を、新しい関数 `publish(verified_dir, files)` に移す。`files` は（名前, bytes）を置く順に並べたもので、accept は sidecar → 本体の順に渡す（順序は今のまま）。

1. 準備（保存先の見える名前はまだ変えない）
   - `verified/` を `mkdir` する。既にあれば作らない。自分が作ったかを覚える
   - `mkdtemp(prefix=".accept-", dir=verified/)` で一時ディレクトリを作り、各ファイルを書く
   - 置き換える名前に既存のエントリがあれば（`lstat` で判定。`FileNotFoundError` だけを「無い」とみなす）、一時ディレクトリに `<名前>.previous` として写す（`shutil.copy2(..., follow_symlinks=False)`）
2. 置き換え: 順に、一時ファイルの inode と内容の sha256 を記録してから、`os.replace` で `verified/<名前>` に置く。記録を置き換えの前にするのは、rename が済んだ後に届く例外（Ctrl-C のシグナルなど。CPython は C の呼び出しが終わった後に、その呼び出しの場所で上げる）でも戻せるようにするため（最終レビューの I-1）
3. 準備・置き換えのどこかで例外が上がったら、記録したものを逆の順に戻す
   - 一時ファイルがまだ一時ディレクトリにあれば、その置き換えは起きていないので飛ばす
   - 置いたパスが、置いたときの inode（`st_dev`・`st_ino`）と内容の sha256 のままのときだけ戻す。写しがあれば写しを `os.replace` で元の名前に移し、無ければ（初回の保存）置いたファイルを消す
   - 戻せなかった写し、他者が変えていたので戻さなかった写しがあれば、一時ディレクトリを消さずに残す（以前のファイルの内容が写しにしか無いことがある）
   - 写しを残さないときは一時ディレクトリを消し、自分が作った `verified/` を `rmdir` する（空でなければ消えない）
   - 元の例外を上げ直す
4. 成功したら一時ディレクトリ（写しを含む）を消す。消せなくても成功とする（今と同じ。組は整っている）

本体を書く前に、2 件の JSON を accept の中で bytes にしておく（`publish` の中で失敗するのは I/O だけにする）。

### 2. 戻した後に保存先全体を照合し、終了コードを分ける

`accept` は `publish` の `OSError` を捕まえ、`review_changes(review_dir, 起動時の snapshot)` で保存先全体を照合する。

- 違いが無い: 終了コード 1。保存先は dispatch 時と同じで、原因を `review_dir` の中を変えずに直せば、同じ `--run-dir` の accept が今の照合をそのまま通る。理由の文にも、`review_dir` の中を変えずに直すこと、そうでなければ dispatch し直すことを書く
- 違いがある・照合できない: 終了コード 3。dispatch 時と違うパス（`review_changes` の結果）をエスケープして列挙する

stderr は 1 行。例外の型と errno の名前（例: `OSError EIO`）だけを出し、例外の文（パスを含む）は出さない。保存より前の検査・照合は変えない。

### 3. 失敗の時点ごとに残るものと回復の仕方

| 失敗した時点 | 初回の保存（同じ名前の結果が無い） | 既存の結果の更新 |
| --- | --- | --- |
| 置き換えの前（`verified/`・一時ディレクトリ・一時ファイル・写しの作成、sidecar の置き換え） | 作った `verified/` と一時ディレクトリを消す。何も残らない（終了コード 1） | 既存の 2 件は変わらない。一時ディレクトリを消す（終了コード 1） |
| 本体の置き換え（sidecar は置いた後） | 置いた sidecar を消し、作った `verified/` と一時ディレクトリを消す（終了コード 1） | 置いた sidecar を以前の sidecar の写しで戻し、一時ディレクトリを消す。以前の組がそのまま残る（終了コード 1） |
| 戻す操作も失敗した・他者が置いたものを変えていた | 終了コード 3。dispatch 時と違うパスを列挙する | 終了コード 3。以前の sidecar の写しを一時ディレクトリに残す |

- 終了コード 1 のとき: 原因を `review_dir` の中を変えずに直してから（`review_dir` の外の空きを作る、など）、同じ `--run-dir` で accept をやり直す。外部の担当を起動し直さない。`review_dir` の中（`verified/` の権限など）を変えて直すと、snapshot が各ディレクトリの mode と各ファイルの内容を記録しているので dispatch 時と違い、accept が拒否する。そのときは dispatch し直す（最終レビューの M-1）
- 終了コード 3 のとき: 列挙したパスを確かめる。他者の変更が無ければ、この run が置いたファイルを消し、一時ディレクトリの `<名前>.previous` を元の名前に戻し、一時ディレクトリと dispatch 時に無かった `verified/` を消す。dispatch 時と同じになれば同じ `--run-dir` でやり直せる（同じでなければ accept が拒否するので、誤って受け取らない）。他者の変更があれば、その run は使わずに dispatch し直す

### 4. 保証する範囲と保証しない範囲

- 保証する: accept の保存の処理（設計 1 の準備と置き換え）の中で上がった例外。自分が置いたものだけを戻し、`OSError` では戻せたかを保存先全体の照合で確かめる
- `OSError` 以外の例外（Ctrl-C など）: 置いたものは戻して上げ直すが、照合はせず、終了コード 1・3 にもならない。`verified/` や一時ディレクトリを作った直後に届くと、空のディレクトリが残ることがある（受け取り直しは照合で拒否されるので、誤って受け取らない）。状態は、同じ `--run-dir` で accept をやり直すと分かる
- 保証しない
  - 突然死（kill・電源断）。一時ディレクトリや、新しい sidecar と古い本体の組が残ることがある。同じ run の accept は保存先の照合で拒否されるので、一時ディレクトリの写しから手で戻す
  - 最後の観測の後の他者の変更（accept の 2 回目の照合から置き換えまで、戻す前の確認から戻すまで）
  - 2 件の置き換えの間に読む読み手が、新しい sidecar と古い本体の組を見ること（今と同じく、2 件同時の一括置換は保証しない）
  - 電源断に対する永続性（fsync しない）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-178-1 失敗したら自分の変更を戻す（ロールバック）**
  - 選択: 保存の途中の例外では、この accept が置いたものだけを置く前に戻し、保存先を dispatch 時の状態に戻す。受け取り直しは、今の accept の照合をそのまま通す
  - 別案: (a) 受け取り直すときに、dispatch 時との違いが自分の途中の出力（同じ内容）だけなら続きから保存する、(b) 置き換えの前に run のディレクトリへ手順の記録を書き、受け取り直すときに記録に従って戻す、(c) `OSError` を `AcceptError` に変えて traceback をやめるだけ、(d) 2 件を 1 回の rename で切り替える配置（ディレクトリやリンクの差し替え）にする
  - 理由: 戻せば、受け取り直しが snapshot の全体の照合を緩めずに通る（A-4）。(a) は照合に「この違いは自分の出力」という例外を入れることになり、外部の担当が保存先へ書いた（禁じた）ファイルでも、内容が同じなら見逃す。(b) は突然死にも効くが、記録と復旧の経路が増え、fsync なしでは電源断の後の順序も保証できず、Issue の範囲（処理中に捕まえられる I/O のエラー）を超える。(c) は Issue が否定している。(d) は `verified/<to12>.fix-check.json`・`.statement-candidates.json` の配置（`review-findings.md`）と validate の読み方を変える
- **D-178-2 戻す対象は、置いたときの inode と内容の両方で確かめる（A-4）**
  - 選択: 置いたパスの `st_dev`・`st_ino` と内容の sha256 が、置いたときと同じときだけ戻す。`verified/` は自分が作ったときだけ `rmdir`。一時ディレクトリは自分が `mkdtemp` で作ったものなので消してよい
  - 別案: inode だけ、内容だけ、snapshot の観測値（`mode:sha256`）だけで確かめる
  - 理由: inode だけでは、他者がその場で書き換えたファイル（同じ inode）を戻して消す。内容だけでは、同じ run の accept を並行して実行したとき、相手が置いた同じ内容のファイルを自分のものとみなして以前の sidecar を戻し、相手が整えた組を壊す
- **D-178-3 以前のファイルは一時ディレクトリへ写して退避する**
  - 選択: 置き換えの前に、既存のエントリを `shutil.copy2(follow_symlinks=False)` で一時ディレクトリの `<名前>.previous` に写す。戻すときは写しを `os.replace` で元の名前に移す
  - 別案: hard link（`os.link`）で退避する、内容をメモリに持って失敗したときに書き戻す、以前のファイルを先に一時ディレクトリへ rename する
  - 理由: snapshot は通常ファイルの inode を記録しないので、写しを戻せば dispatch 時と同じ観測値になる（mode は `copy2` が写す）。hard link はファイルシステムによって使えず、使えないと以前の結果があるときに保存が毎回失敗する。メモリから書き戻す方法は、ディスクが一杯のときに戻す書き込みが失敗する（写しは置き換えの前に作るので、作れなければ見える名前を変えずに止まる）。先に rename すると、置き換えの前に sidecar の名前が空く
- **D-178-4 戻せたら終了コード 1、戻せなかったら 3**
  - 選択: 戻した後の照合で違いが無ければ 1（理由に、dispatch 時の状態に戻したことと、同じ `--run-dir` でやり直せることを書く）。違いがある・照合できなければ 3（違うパスを列挙する）
  - 別案: どちらも 1、どちらも 2
  - 理由: 1 なら「helper は正式な成果物を追加保存しない」（fix-check.md 53 行）がそのまま成り立ち、呼び出し側は受け取り直せると分かる。戻せなかった状態は以前の結果が不整合なことがあり、ほかの拒否と同じ 1 にすると見落とす。2 は入力・環境の誤りで、保存先を変えていない（fix-check.md 54 行）
- **D-178-5 保証の範囲（A-5）**
  - 選択: 設計 4 のとおり、保存の処理の中で上がった例外だけを保証し、突然死・最後の観測の後の他者の変更・2 件の切り替えの間の読み手・永続性は保証しないと書く。`publish` は `OSError` 以外の例外（Ctrl-C など）でも戻してから上げ直すが、accept が照合して終了コードに変えるのは `OSError` だけ。`verified/`・一時ディレクトリを作った直後に届く例外で空のディレクトリが残る幅は直さない（データを失わず、受け取り直しは照合で拒否される。最終レビューも任意とした）
  - 別案: 突然死も扱う（D-178-1 の (b)）
  - 理由: Issue の範囲（「まず処理中に捕捉できる I/O 例外」「あらゆる kill・電源断・悪意ある同時変更を防ぐ sandbox を新たに求めるものではない」）
- **D-178-6 テストは S の 3 件（T3 は最終レビューで足した）**
  - 選択: `test_dispatch.py` に 3 件を足す
    - T1: 有効な組 A を受け取った後、主張の ID だけが違う有効な B を新しい run で dispatch し、B の accept の 2 件目の `os.replace` だけに `OSError(EIO)` を入れる。終了コード 1、保存先全体（`managed_state`）が accept の前と同じ、A の 2 件の bytes が同じ、一時ディレクトリが無い、A の本体が `validate` を通る、を確かめる。続けて同じ B の run を入れ直さずに accept すると終了コード 0 で、B の 2 件が `validate` を通る
    - T2: T1 と同じ失敗の直前に、他者が sidecar をその場で書き換える（同じ inode）。終了コード 3、他者の内容と A の本体が残る、以前の sidecar の写しが一時ディレクトリに残る、stderr に sidecar のパスがある、を確かめる
    - T3（最終レビューの I-1 で足した）: sidecar の rename が済んだ後に `KeyboardInterrupt` が届く。例外がそのまま上がり、保存先全体（`managed_state`）が accept の前と同じであることを確かめる。T1 の「置き換えが起きていなければ飛ばす」とは別の守り（rename が済んだかの判断と、`OSError` 以外でも戻すこと）で、壊れると以前の組と唯一の写しを黙って失う（S）
  - 別案: 失敗の時点（`mkdir`・一時ファイル・写し・1 件目・2 件目）と初回・更新の組み合わせを網羅する
  - 理由: `AGENTS.md` の「テストの採用基準」。T1 は以前に受け取った結果の保護（記録の消失）と、受け取り直しの経路の代表（S。Issue で再現した不具合の再発防止）。T2 は他者の変更を戻して消さないこと（誤った対象の上書きの拒否。S）の代表で、T1 が「正しく通る例」になる。初回の保存の戻し方（置いた sidecar と作った `verified/` を消す）が壊れても、戻した後の照合が終了コード 3 とパスの列挙で示すので L とし、一時的な確認で確かめて報告する。照合が壊れて「戻した」と誤って報告する場合は T2 が落ちる
- **D-178-7 呼び出し側の手順は変えない**
  - 選択: 変えるのは review-verify の `dispatch.py`・`tests/test_dispatch.py`・`references/fix-check.md` だけ。review-fix-planning の `references/execution.md` 2.4（終了コード 0 のときだけ受け取る）は、新しい終了コード 3 も受け取らない側に入るので変えない
  - 別案: execution.md に、終了コード 1 の I/O のエラーのときは受け取り直す手順を足す
  - 理由: Issue の範囲外（「#155/#156 の呼出側の接続や、自動マージの仕様変更は含めない」）
- **D-178-8 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は同じ 3 つのファイルへの逐次の変更で、子に文脈を渡す手間が実装より大きい。最後のブランチ全体のレビューは省かない

## 要件と経路の対応

| 経路 | 判定 | 観測する結果と確かめ方 |
| --- | --- | --- |
| 既存の組の更新で 2 件目の置き換えが失敗 | 修正する | T1: 終了コード 1、保存先全体が accept の前と同じ、A が validate を通る、同じ run の受け取り直しで B（A-1・A-2・A-3） |
| 他者が置いたものを変えていた・戻せない | 修正する | T2: 終了コード 3、他者の内容・A の本体・写しが残る（A-3・A-4） |
| 初回の保存で 2 件目の置き換えが失敗 | 修正する | 一時的な確認: 終了コード 1、`verified/` が無い、受け取り直しで 0（A-2） |
| rename が済んだ後に例外が届く（Ctrl-C、成功した後に失敗を返すファイルシステム） | 修正する（最終レビューの I-1） | T3: `KeyboardInterrupt` が上がり、保存先全体が accept の前と同じ。一時的な確認: 本体の rename の後の `OSError` で終了コード 1 |
| 保存より前の照合・PR・skill・inventory・停止の確認 | 変えない | 既存のテストを変えずに通す（A-4） |
| 成功の経路 | 変えない（写しを作って消すだけが増える） | 既存の `test_accept_saves_the_tool_output_unchanged_with_the_observed_verifier` などを通す |
| `fix-check.md` の終了コードと保存の説明 | 修正する | 差分を読み、設計 2・3・4 と一致することを確かめる（A-2・A-5）。文面のテストは足さない |

## 範囲外

- 保存より前の `OSError`（検査の helper の読み込み、git の実行など）の traceback。保存先を変えないので、表示の改善だけになる
- 突然死からの回復、同時変更の sandbox（設計 4）
- review-fix-planning の手順・`run_roles.py`、#155・#156 の呼び出し側の接続（D-178-7）
- self の確認で司令塔が保存するときの手順（`SKILL.md` の「保存と報告」）
- CI（`AGENTS.md` の「GitHub Actions」）

## 実装者に任せること

- 関数・変数の名前、docstring とコメントの文面（周りのコードに合わせる）
- stderr の文の細かい言い回し（設計 2 の内容を 1 行で書く）
