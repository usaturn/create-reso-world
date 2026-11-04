# Issue #309 Herdr の復元で Pi のペインをランチャーから再開する 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/309（#307 の持ち越し。PR #308 で範囲外とした 1 点目）
- 実行許可: 利用者の指示 `/issue-to-pr #309 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない

## 目的

Herdr がサーバーの再起動の後にセッションを復元するとき、ランチャー（`pigs` など）から起動した Pi のペインを、同じランチャーで再開する。今は Pi そのもので再開されるので、PR #308 の停止用の設定により pi-superagents が止まり、利用者は Pi を終了してランチャーで開き直す必要がある。

## 確かめた事実（2026-11-05、Herdr 0.9.5・Pi 1.5.0）

Issue の「確かめた事実」に加えて、名前付きのテスト用セッション（`herdr --session t309probe server`。既定のセッションとは別のサーバー・ソケット・`session.json`）で、実際の Pi（`pi --tui-mode regular --session-dir <一時ディレクトリ>`）と、`-e` で読み込ませた試作の拡張を使って確かめた。既定のセッションのペインには触れていない。

1. 報告は `pane.report_agent_session`（または `pane.report_agent`）の `resume_argv` で行い、Herdr は `session.json` のペインに `agent_resume: {source, agent, argv}` として保存する
2. `source` が `herdr:pi` 以外の報告は `resume_not_accepted`（"resume_argv requires the reporter to hold the pane; report its state with pane.report_agent first"）で拒否される。ペインを持つのは状態を報告した source（Herdr の Pi 連携の `herdr:pi`）なので、拡張は `source: "herdr:pi"` で報告する必要がある
3. `seq` の無い報告は `ok` を返すが保存されない
4. 同じ source のセッションの報告は `seq` の大きい順にしか受け付けない（小さい `seq` の報告は `ok` を返して捨てられる）。状態の報告（`pane.report_agent`）の `seq` は別に比べられ、セッションの報告の `seq` が大きくても、Herdr の連携の状態の報告は今までどおり反映される
5. セッションのパスを変える報告は `session_start_source`（`startup`・`new` など）が無いと捨てられる。Herdr の連携は `session_start` のときだけ `session_start_source` を付ける
6. `resume_argv` の無い報告は、保存済みの `agent_resume` を消さない。セッションのパスが変わっても `agent_resume` は前のままで、復元では `agent_session` ではなく `agent_resume` が使われる。Pi を `/new` で切り替えた後に報告し直さないと、復元で前のセッションが開く
7. Pi が終了してペインがシェルに戻ると、`agent_resume` は消える
8. 復元では、Herdr がペインの対話シェルに `resume_argv` をコマンドとして入力し、保存した cwd で実行する（`echo RESUMED-HIGH1 <path>` がプロンプトに入力されて実行された）。対話シェルの PATH に `~/.local/bin` があるので、ランチャー名で起動できる
9. `resume_argv` の検証（バイナリの文言）: 空でないこと、先頭が素のコマンド名（パスではない）であること、アポストロフィと制御文字を含まないこと、要素数に上限があること
10. Herdr の連携の Pi 拡張のモジュールは `/new` の後も読み直されず、`seq` は起動時の時刻（ミリ秒 × 1000）から 1 ずつ増える。拡張が時刻から作った大きな `seq` で報告すると、その後の Herdr の連携のセッションの報告は捨てられる（事実 4）。状態の報告は影響を受けない
11. 拡張の中で例外が起きると、Pi ごと終了する（`pi exiting due to uncaughtException`）
12. pi-superagents の子 Pi は `--mode json -p` で起動される（`src/execution/child-runner.ts`）。TUI ではない
13. 全ランチャーは引数を `"$@"` で Pi に渡すので、`<ランチャー> --session <セッションファイル>` で同じセッションを開ける。Pi の `--session` はパスか ID を受け付ける（`dist/main.js` の `resolveSessionPath`）

## 決定記録

### D1. 再開コマンドを報告する方法

- 選択した案: ランチャーが Pi に自分の名前を渡し、Herdr の連携の横（`~/.pi/agent/extensions/`）に置く Pi の拡張が、`source: "herdr:pi"` で `pane.report_agent_session` に `resume_argv: ["<ランチャー>", "--session", <セッションファイル>]` を付けて報告する
- 検討した別案:
  - `[session] resume_agents_on_restore = false`: Claude Code・Codex など、他のエージェントの再開も止まる。Issue の目的（ランチャーで再開する）を満たさない
  - Herdr の連携のファイル（`herdr-agent-state.ts`）を書き換える: 「managed by herdr」で、連携の更新・再導入で上書きされる
  - Herdr の連携の送信をフックして `resume_argv` を足す（`net` の差し替え）: Pi の全通信に影響し、壊れやすい
  - 別の source で報告する: 事実 2 のとおり拒否される。別の source で状態も報告すると、Herdr の連携とペインの持ち主を取り合う
  - ランチャーが `pi --extension <パス>` で拡張を渡す: 共有の `~/.pi` に置かないで済むが、拡張のファイルを `~/.local/bin` の共通ヘルパの横に置き、ヘルパを配置する 3 つの setup すべてで配置する必要がある。Issue の案と Herdr の案内（「add custom hooks/plugins beside this file」）は連携の横に置く形
- 選択理由: Herdr・pi-superagents 本体を変えずに（Issue の範囲外の条件）、復元の再開コマンドだけを変えられる。拡張はランチャーから起動した TUI の Pi のときだけ動き、素の `pi`・子 Pi・Herdr の外では何もしない
- 委任指示: issue-to-pr の推奨案での委任

### D2. ランチャー名の渡し方

- 選択した案: 共通ヘルパ（`pi_superagents_exec`）が bwrap に `--setenv PI_SUPERAGENTS_LAUNCHER <ランチャー>` を渡す。拡張は、この値が素のコマンド名（`^[a-z][a-z0-9_-]*$`）のときだけ動く
- 検討した別案: ヘルパで `export` する（bwrap の argv に出ないので、dry-run の argv で確かめられない）
- 選択理由: 13 個のランチャーがすべて共通ヘルパを通るので、1 か所で全ランチャーに効く。argv に出るので、既存の dry-run のテストで、各ランチャーが自分の名前を渡すことを確かめられる
- 委任指示: issue-to-pr の推奨案での委任

### D3. 報告の時点と内容

- 選択した案:
  - Pi の `session_start`（`startup`・`new`・`resume`・`fork`・`reload` など、理由を問わず）のたびに報告する。`session_start_source` に `event.reason`、`agent_session_path` に今のセッションファイルを入れる（事実 5・6）
  - `seq` は `max(前の seq + 1, Date.now() × 1000)`。Herdr の連携の `seq`（起動時の時刻 × 1000 + 回数）より大きくなる
  - 報告は `session_start` の処理を待たせずに非同期で送る。起動直後は Herdr の連携がまだ状態を報告しておらず `resume_not_accepted` になり得るので、`resume_not_accepted` と送信の失敗は間隔を空けて数回やり直す
  - 新しい `session_start` が来たら、前のセッションのやり直しを止める（遅れて届いた前のセッションの報告が、新しいセッションの再開コマンドを上書きしないように）。止める目印は `globalThis` に置き、拡張のモジュールが読み直されても共有する
  - セッションファイルのパスが `resume_argv` の検証（事実 9）を通らないとき（アポストロフィ・制御文字を含む）は、セッションの ID（英数字と `-` だけのとき）を `--session` に渡す。どちらも使えなければ報告しない
  - セッションファイルが無いとき（`--no-session`）は報告しない
  - 例外はすべて拡張の中で捕まえる（事実 11）
- 検討した別案:
  - `agent_start` のたびにも報告する: 事実 6 のとおり `agent_resume` は残るので要らない
  - `seq` を付けない: 事実 3 のとおり保存されない
  - `seq` を Herdr の連携の値に合わせる: 連携の内部の値は読めない
- 選択理由: 事実 4〜6・10 から、再開コマンドを正しく保つには、セッションが変わるたびに、Herdr の連携より大きい `seq` で、パスと `session_start_source` を付けて報告し直す必要がある。拡張の大きい `seq` のために Herdr の連携のセッションの報告は捨てられるが、拡張が同じパスを報告するので、Herdr が持つセッションのパスは正しく保たれる。状態の報告は影響を受けない（事実 4）
- 委任指示: issue-to-pr の推奨案での委任

### D4. 拡張の配置

- 選択した案: リポジトリの `.devcontainer/pi-herdr-launcher-resume.ts` を、`scripts/setup_pi_superagents.zsh` が `~/.pi/agent/extensions/herdr-launcher-resume.ts` に毎回配置する（共通ヘルパと同じく、`--if-absent` でも更新する）。postCreate は今までどおり `setup_pi_superagents.zsh --if-absent` を呼ぶので、rebuild でも配置される
- 検討した別案: `install_beforehand.bash` で配置する（rebuild しない既存の環境では setup を実行し直すので、setup に置けば両方に効く）
- 選択理由: setup はすでに `~/.pi/agent/extensions/` の下（共有の bind 先とランチャー別の設定）を管理している。ランチャーの中では setup は何も書かずに止まる（PR #308）ので、拡張の配置もランチャーの外で行われる
- 委任指示: issue-to-pr の推奨案での委任

### D5. テスト

- 選択した案（AGENTS.md の「テストの採用基準」の S）:
  - 拡張（新しい `.devcontainer/test-pi-herdr-launcher-resume.bash`。偽の Herdr のソケットに報告させる）:
    - TUI の Pi で、`source: "herdr:pi"`・`resume_argv: [<ランチャー>, "--session", <パス>]`・`session_start_source`・`agent_session_path`・`seq` を付けて報告する。`/new` に当たる 2 回目の `session_start` では新しいパスと大きい `seq` で報告し、前のセッションのやり直しは新しい報告の後に届かない（防ぐ損害: 復元で前のセッションが黙って開く。事実 6 で実際に起きた）
    - TUI でない Pi（子 Pi の `json` モード）は報告しない（防ぐ損害: 子のセッションが親のペインの再開先になり、復元で別のセッションが黙って開く）
  - 共通ヘルパ（既存の `test_launchers_wrap_pi_with_their_own_config` に追加）: 各ランチャーが bwrap に自分の名前を `PI_SUPERAGENTS_LAUNCHER` として渡す（防ぐ損害: 別のランチャーで再開され、tier の model が黙って変わる）
- 書かないもの（L）: setup が拡張を配置すること（無ければ復元で #308 の停止のメッセージが出て気付ける）、`resume_not_accepted` のやり直し（壊れても復元で同じメッセージが出る）、ランチャーの環境変数が無いときに何もしないこと（壊れても Herdr が `resume_argv` の先頭の検証で拒否する）、例外を捕まえること（壊れると Pi が終了して気付ける）。これらはテスト用の Herdr のセッションと一時 HOME での実行で確かめる
- 委任指示: issue-to-pr の推奨案での委任

### D6. 文書

- 選択した案: `.devcontainer/README.md` の「ランチャーを通さない Pi と同梱の既定 model」で、復元の後の手順と「次は扱っていない」の 1 点目を、ランチャーで再開する仕組みと既存の環境での反映手順（`zsh scripts/setup_pi_superagents.zsh --if-absent` の後にランチャーの Pi を起動し直す）に書き換える
- 選択理由: #307 の記録と同じ節にあり、復元の後に読む場所
- 委任指示: issue-to-pr の推奨案での委任

## 範囲外

- pi-superagents・Herdr 本体の変更（Issue の範囲外）
- Herdr の連携のファイル（`herdr-agent-state.ts`）の変更
- 利用者がランチャーに付けた追加の引数（`--model` など）の再現。再開は `<ランチャー> --session <セッションファイル>` だけで行う
- 素の `pi` で起動したペインの再開（今までどおり Pi で再開され、#308 の停止用の設定で pi-superagents が止まる）
- Herdr の外（`HERDR_ENV` が無い端末）でのランチャーの起動

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）、Herdr 0.9.5、Pi 1.5.0、Node 24、bubblewrap 0.11
- 実入力: Herdr のペインで `pigs` などのランチャーから起動した Pi。セッションファイルのパスは `~/.pi/agent/sessions/--workspaces-reso-world--/2026-11-04T05-45-06-950Z_<UUID>.jsonl` の形。`/new`・`/resume` でセッションが変わる。サーバーの再起動で Herdr が復元する
- 防御範囲:
  - 対象: ランチャーから起動した、Herdr の中の TUI の Pi。復元で `<ランチャー> --session <今のセッションファイル>` が実行される。セッションを切り替えた後は新しいセッションが開く
  - 対象外の反例: 素の `pi`（`PI_SUPERAGENTS_LAUNCHER` が無い）、子 Pi（`--mode json`）、Herdr の外、`--no-session` の Pi は報告しない。Herdr の連携の状態の報告（working / idle）は今までどおり反映される

## 残るリスク

- 事実 2〜6・10 は Herdr 0.9.5 の観測で、公開された仕様ではない。Herdr の更新で連携が自分で `resume_argv`（`pi --session`）を報告するようになり、その `seq` が拡張より大きいと、再開は Pi そのものに戻る（#308 の停止のメッセージで気付ける）
