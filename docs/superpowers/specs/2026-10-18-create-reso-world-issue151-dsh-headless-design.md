# Issue #151: DSH headless レビュアー

## 管理・実行許可

- 状態: draft（利用者による内容の承認は未取得）
- 対象: https://github.com/usaturn/create-reso-world/issues/151、親 #116、ボード `review-automation-board`、キー `dsh-headless`
- 文書・コード対象: `usaturn/create-reso-world`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-151-dsh-headless`
- branch: `feat/issue-151-dsh-headless`、base: `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`（最新の origin/main から作成）
- 実行許可: 利用者が `issue-to-pr` スキルを明示して `#151` と指定した。この入口の「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」に基づき、質問を省いて進める。マージ・rebuild・リリースは含まない。
- 先行: #149 は `CLOSED / COMPLETED`、PR #163 は main に `6ca0ec8` でマージ済み。base にその commit を含むことを確認。
- 予約: `refs/heads/agent-claims/issue-151`、SHA `5f76593cab5ae495828eff5d15bda48738f69005`、session `87a8dd52-bd2b-447a-84e2-7d84f2a34904`。開始時に競合 PR・予約・branch・worktree 無し。自分の予約だけを exact-SHA lease で解放する。
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue151-dsh-headless.md`

## 目的と制約

runner から `dsh-ccd` / `dsh-go` を非対話で使い、payload と実際のセッションで観測したモデルを回収する。呼出しごとに HOME・DSH_HOME・TMPDIR を分け、ツールのコマンドは scoped bubblewrap runner で実行する。

親 #116 冒頭の「着手するエージェントへの注意（利用者決定: 2026-10-18）」と、親 Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md` の D-1〜D-24 に従う。`tools/workspace`・`projects.toml` は導入せず、review-fix-planning の致命的な指摘だけを対象とする判断基準・三択の結論・修正後の自己レビュー最大 1 回を変更しない。

移植元は `usaturn/agent-workspace` の `a47b2065fddad76b7475752fd0088af0733de204`。runner 本体・models・adapter 登録・test_support/plugin は #149 の仕様をそのまま使う。DSH 以外の adapter、roles/workflows、AGENTS.md、対話用ランチャー、共有 cordis.patch.yml は変更しない。

## 設計

### 起動と隔離

`tools/agent_runner/adapters/dsh.py` は既存 Adapter protocol（prepare / collect / capabilities）を実装し、`ADAPTER` を公開する。provider は commandcode と opencode-go だけ、任意 args は拒否する。

prepare は attempt 配下の `dsh/{home,state,tmp}` を mode 0700 で新規作成する。既存の attempt 状態は再利用しない。CLI は `dsh --profile headless --patch <attempt>/dsh/provider.patch.yml --json -`、依頼は stdin。API key は許可された環境変数（COMMANDCODE_API_KEY または OPENCODE_API_KEY）から、毎回異なる名前の API-key 環境変数へ移す。patch・argv にキーの値を書かない。共有 profile、親 PI_*、プロジェクト .env の同名キーをモデル識別の根拠にしない。telemetry、session title の別モデル呼出し、plugin inventory の送信は無効にする。

patch の sandbox runnerCommand は Python の `dsh_sandbox.py`。bubblewrap の存在を起動準備時にも確認し、見つからなければ DSH を起動しない。sandbox helper も単独で存在確認する。helper は DSH 標準の readonly / workspace-write profile だけを受け付け、root は read-only、workspace と caller が事前指定した HOME・TMPDIR・レビュー出力等だけを writable bind にする。read-root で attempt 状態を read-only に見せる。相対・未解決・symlink・不在の grant、filesystem root の grant、任意 profile の追加は拒否する。これは書き込み範囲の制限であり、ホスト全体の読み取り隔離やネットワーク隔離を追加するものではない。

停止・子孫の終了確認・HOME の削除・TMPDIR のリンクや FIFO の除去・残す通常ファイルの redact は #149 runner にある DSH 専用処理を使う。停止未確認では状態を読んだり消したりせず sensitive_paths に残す。

### 回収と観測した識別情報

headless JSONL は session、turn_start、turn_end(completed)、final の順序と中間イベントの型を検査する。空の回答、重複キー、非有限 JSON、壊れた行、truncated な session/final、認証・承認・abort、非ゼロ終了、停止未確認は成功にしない。json の payload は非空 object または JSON fence 内の非空 object、text は文字列をそのまま保持する。

`read_session_identity(dsh_home: Path, work_dir: Path, session_id: str, *, live: bool = False) -> Identity` を公開する。stdout の sessionId に一致する `sessions/*/<id>/session.v4.jsonl` が 1 つで、通常ファイル・symlink でないディレクトリ、v4 header の id/cwd/isSeeded、連続 seq を検査する。resolved request route と interrupted でない assistant source の provider/model が一致した観測だけを返す。呼出し中の provider/model/effort の変更は、変更先の応答があっても拒否する。同じ route の複数回の応答は認める。要求したモデルや親の環境から補完しない。live=True のときだけ、追記中の改行の無い末尾を無視する。

移植元 collect はログ不在でも成功にするが、この子では **成功に観測した provider/model が必須**。ログ不在なら response_failed / payload=None にする。ただし認証・承認待ち・interrupted の既知の診断はログ欠落で上書きしない。ログ内の不一致や破損は response_failed。観測値を設定値へ置き換えず、設定値との違いだけで偽の観測値を返さない。

`tools.test_support.dsh.write_session(home, cwd, *, session_id='session-test', provider='observed-provider', model='observed-model', effort='high') -> Path` は移植元の名前・引数・v4 形式を保つ。#153 と #156 が使う。

### 導入・設定・文書

`.devcontainer/agent-runner.toml` に `[agents.dsh-ccd]` / `[agents.dsh-go]` だけを追加する。移植元と同じ command `['dsh']`、effort `max`、commandcode は model `deepseek/deepseek-v4.1-flash`、opencode-go は `deepseek-v4.1-flash`。env は PATH と該当 API key だけ。workflow は #153 の担当なので追加しない。

postCreate の `install_beforehand.bash` に dsh CLI の導入段を追加。`@deepseek-ai/dsh@0.2.0-rc.2` に固定し、移植元と同じ native install script allowlist `@deepseek-ai/dsh-subprocess-local,koffi,node-pty` を使う。npm 失敗・CLI 不在・version コマンド失敗・版不一致は失敗を返して postCreate を打ち切る。共有 ~/.dsh の準備、plugin install、pi-tui、pnpm、3080 は追加しない。

README の DSH 全体の除外を、対話用は除外・headless CLI だけ再導入と区別する。既存の個人 agent-runner 設定は上書きされないため、rebuild 後も古い設定に agent が無ければ追加するか明示 --config を使う。maatlog の #17/#18 の撤去履歴は消さず、#151 での再導入と R-2/R-3 の期待値を区別し、過去の実測列を成功したように書き換えない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-1 | upstream を #149 protocol に適応 | 新 adapter を別設計 | upstream の既存の安全処理と後続の公開 API を保つ | 通常判断は issue-to-pr の委任 |
| D-2 | 成功には観測した識別が必要 | upstream のログ欠落でも成功を維持 | #151 の欠落・不一致を失敗にする受け入れ条件 | 通常判断の委任 |
| D-3 | bubblewrap 不在を prepare/helper 両方で拒否 | 実ツール呼出しまで不在を保留 | 隔離無しの起動を事前に防ぐ | 不在を回避しない |
| D-4 | CLI のみ固定版導入 | 共有 profile / web plugin / TUI を再導入 | D-14、headless に余分な導入を持ち込まない | 実機で追加が必要なら理由を記録、禁止範囲が必要なら停止 |
| D-5 | inline 2 Task と独立した最終レビュー | Task ごとに同期委譲 | 小さい port と導入の 2 Task。調査子の結果は取得できなかったが、最終レビューは `Review scope: branch` を明示した sp-review で取得できた | 実行方式は委任。使えない子を成功扱いしない |
| D-6 | fake CLI と実 bubblewrap を先に検証、rebuild 後の実機は利用者 | rebuild をこの run で実施 | D-21。利用者が rebuild する前の結果を捏造しない | 必要なツール/API や検証の解消不能な失敗では停止 |

## 検証と受け入れ

- 実行コードを通るテストだけを移植。repository fixture は独立した一時 git repository にし、projects.toml を作らない。Git の GIT_* は fixture の subprocess 環境から除く。テストは実モデルを起動しない。
- adapter の strict JSONL、durable identity、不在・曖昧・不正なログ、認証・承認・timeout・cancellation、秘密の redact、HOME/TMPDIR cleanup と stop_confirmed を確認。
- 実 bubblewrap で許可パスへの書き込み成功・隣接パスの拒否、helper 単独と prepare の bubblewrap 不在時の fail-closed を確認。
- installer は shell の stub npm/dsh を実行し、固定された package の版と version 出力の一致、各失敗と後続処理の非実行を確認。文書・設定一覧の固定文言テストは作らない。
- `uv run pytest tools/agent_runner/tests/adapters/dsh tools/test_support`
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`
- `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check`、雛形に対する runner check。
- 実機: 利用者が rebuild した後に `dsh --version` と、使い捨て対象に対する dsh-ccd の短い依頼を runner で 1 回起動し payload と観測したモデルを確認する。workflow 未導入の期間は一時 config に inspect の割り当てを追加して --config で指定する（親 #116 のコメント）。実機結果を #151 に記録するまで、この子の最終の completed は宣言しない。

## 設計確認

upstream と #149 の protocol を直接確認し、観測の欠落、fake CLI の durable log 不在、移植元の create_workspace 依存、後片付けの所有者、workflow 未定義、既存個人設定の優先を確認した。subagent の結果が取得できないため builder check は自己確認で代替し、実行方式と制約を D-5 に記録した。未解決の利用者判断は無い。実機確認は実装 PR の作成と分けて記録する。

最終の独立レビュー（base `a024a22`、head `8f73624`）で、応答を伴う route 変更が最後の観測で上書きされる問題を指摘された。provider/model/effort の変更と、途中で変更して元へ戻る場合を RED→GREEN で確認し、header を読む時点で route の変更を拒否した。実機・読み取り/ネットワーク隔離の対象外という判断は上の制約どおりである。修正後の再レビューは行わず、回帰テストと全体検証で確かめる。
