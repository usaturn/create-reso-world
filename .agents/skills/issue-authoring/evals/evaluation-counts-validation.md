> 移植元 usaturn/agent-workspace commit 6e71fae4d25f217b23ce2409517cf602437a3cbf の過去の評価記録。以下の環境・パス・コマンド・結果は当時の履歴であり、このリポジトリでの実行手順や今回の成功を示さない。

# issue-authoring の評価集計の行動比較

実施日: 2026-11-09（UTC）。Issue #888 / Task 2。旧版と新版の `references/evaluation.md` に同じ架空入力を与え、選択済み Issue の母集団、metadata の状態、有効な run・評価の数え方、method ごとの観測の扱いを比べた。シナリオ、期待、実測の対応は [evaluation-counts-scenarios.json](evaluation-counts-scenarios.json) に置く。この文書には比較手順、実測、アクセス監査、限界を残す。

## 方法

### 比較した文書

- baseline（旧版）: commit `335c69a6c4c5d2ae9239e585108085fcd992ba5c` の `.agents/skills/issue-authoring/references/evaluation.md`。sha256 は `d102c54d84d50e722c9119d8cb6bd57a93fd00b3ced83b7ab7806ace1d7c8801`。
- green（新版）: commit `663c78053a372c4359a468cc300efed5e0f5090b` の同じファイル。sha256 は `526de689a8a97f5f46528b56cc6f683994e111f0d15cb5b44a50af1920a09f31`。現在の worktree のファイルもこの値と一致する。
- 差は Task 1 の文書変更だけである。どちらの task も、参照する評価手順以外は同じ入力と同じ局所適用の依頼を使った。

### 入力と依頼

- 入力: `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/input.json`（sha256 `f49c4ab3d28599632b1b974289ac1ab72e2ab7360cbdf4579cfbeba5d5508811`）。対応する抽出行は同ディレクトリの `observations.jsonl`（sha256 `5bfb6b6739c56021160da0bd113a3e20d42f979c2f1537c482e8f336d7da8f34`）。
- 入力は架空の 4 Issue（#900901〜#900904）で、`main`（#900888、選択 #900901・#900902、目標 4 件）と `boundary`（#900889、選択 #900901・#900903・#900904、目標 1 件）の 2 ケースを持つ。#900901 は metadata が ok で、run_records と evaluations に ok が各 1 件、broken と unknown_version が各 1 件ある。#900902 は metadata が broken、#900903 は missing、#900904 は unknown_version である。通常運用の作業ログは無い。
- 依頼: 提示済みの入力と評価手順だけを使い、追加の情報取得・ツール呼出し・ファイル読み取りをせず、case 別の Evaluation JSON を返す。10 分以内、モデル識別子を環境で確認できなければ unknown とする。
- task の完全な文面: `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/baseline-task.txt`（sha256 `004837db35f1649322f9c0a49b712e8b0060fedd4604c66f19330b9a233a1f82`）と `green-task.txt`（sha256 `c8c764ee0ffa6d64d953f6e4d5d23bcedfba3065b7d1cb6ed7530b5c22d92662`）。

### 実行と採点

- 実行は Pi の `sp-research` を非対話で 1 回ずつ。harness metadata のモデルは `deepseek-v4.1-flash`、thinking は `max`。回答自身はモデルを `unknown` としている。試行数は各版 1 回（合計 2 回）で、Claude Code は未実施である。
- 所要時間は harness metadata の `durationMs` で、baseline 216,702 ms（約 3 分 37 秒）、green 219,011 ms（約 3 分 39 秒）。
- 採点は controller が `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/score.json`（sha256 `10616c887bed5dfd0a25806c9180b42326806cb76ae35f64828ccea007cfc65c`）で行った。scorer は controller のモデル（`PI_PROVIDER=openai-codex`、`PI_MODEL=gpt-6.1-sol`）で、回答の件数・達成判定・scope の記述を確認して採点した。score.json に人による確認の記録はない。文言の一致は使っていない。実装担当は独立に再採点していない。
- 再確認するときは、同じ `input.json` と task 文面を使い、各版を 1 回ずつ実行して、回答の counts を `evaluation-counts-scenarios.json` の `expected` と照合する。実行時のツール呼出しと所要時間は harness metadata で確認する。

## 結果

| variant | 文書 sha256 | harness のモデル | 試行 | 所要時間 | main 書式 | 有効 run | 有効評価 | main 時間 | boundary 書式 | 基準 |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| baseline | `d102c54` | `deepseek-v4.1-flash` | 1 | 216,702 ms | 1/2（50.0%） | 1 | 1 | null | 1/3（33.3%） | 満たす |
| green | `526de68` | `deepseek-v4.1-flash` | 1 | 219,011 ms | 1/2（50.0%） | 1 | 1 | null | 1/3（33.3%） | 満たす |

`main` の期待は、書式適合率が #900901 の 1/2、有効な実行記録が 1 件（#900901 の id=1 のみ）、有効な評価記録が 1 件（#900901 の id=4 のみ）、通常の確認作業の平均時間が作業ログ未提供のため `achieved=null` である。`boundary` の期待は書式適合率が #900901 の 1/3 である。どちらの版も、この期待と同じ件数・達成判定を返した。

### scope と results の観測

| variant | case | scope の観測 | results の観測 |
|---|---|---|---|
| baseline | main | 対象は事前確認済みの #900901・#900902 の 2 件。有効な実行記録・評価記録は、抽出 `status=ok` かつ対象 Issue 一致・対応版として計数。通常運用のログは未提供。 | 書式 1/2 で `achieved=false`、有効な実行記録 1 件で `true`、有効な評価記録 1 件で `true`、平均時間は `achieved=null`。 |
| baseline | boundary | 対象は #900901・#900903・#900904 の 3 件。 | 書式 1/3 で `achieved=false`。 |
| green | main | 対象は別 API で 2026-11-09 作成と確認した #900901・#900902 の 2 件。metadata の状態で対象を絞らず、run_records・evaluations は `extraction.status=ok` だけを有効とする。ログは未提供。 | 書式 1/2 で `achieved=false`、有効な実行記録 1 件で `true`、有効な評価記録 1 件で `true`、平均時間は `achieved=null`。 |
| green | boundary | 対象は #900901・#900903・#900904 の 3 件。missing・unknown_version も選択済み Issue として保持。 | 書式 1/3 で `achieved=false`。 |

### 読み取れたこと

- baseline は #900902 を metadata broken のまま分母に残し、#900902 の `check.complete=false` を不適合として 1/2 にした。#900903 の missing と #900904 の unknown_version も boundary の分母に残した。選択済み Issue を metadata の状態で落とす誤りは、この入力では再現しなかった。
- baseline の run_records は配列長 3 ではなく `extraction.status=ok` の 1 件だけを数え、broken と unknown_version を除外した。evaluations も同じく 1 件だけを数えた。平均時間は通常運用ログが無いため null とし、run-record の `active_minutes` を代用しなかった。
- 旧文書には「`check` は評価の判定には使わない」と読める記述があったが、対象の method が `check.complete` を明示していたため、baseline は method に従って check を使った。つまり旧文書の矛盾する記述は実行されず、数値の誤判定も観測されなかった。これは旧文書が安全であることの証明ではなく、この入力で誤判定が再現しなかったという記録である。
- green は、選択済み Issue を metadata の状態で絞らないこと、run_records・evaluations は `extraction.status=ok` だけを数えること、method が書式検査を指定したときに `check.complete` を観測根拠にすることを scope・actual・notes で説明した。今回の入力では、baseline と green の件数・達成判定に差は無かった。
- 日時の暫定値と回答内の `model=unknown` は、score.json に記録されている。green の notes では今回の局所比較の判定対象外とされ、baseline でも counts の誤りとしては扱われていない。

## アクセス監査と生ログ

- baseline: `baseline-audit.json` の harness metadata は `toolCount=0`、`turns=1`、`exitCode=0`、`allowedInputOnly=true`、model `deepseek-v4.1-flash`、thinking `max`、`durationMs=216702`。子セッションの成果物は `5c5b3b8c_sp-research_0_meta.json` と `5c5b3b8c_sp-research_0_output.md`。
- green: `green-audit.json` は同じく `toolCount=0`、`turns=1`、`exitCode=0`、`allowedInputOnly=true`、model `deepseek-v4.1-flash`、thinking `max`、`durationMs=219011`。成果物は `eb2a5475_sp-research_0_meta.json` と `eb2a5475_sp-research_0_output.md`。
- どちらも standalone の子セッションは個別に保存されていない。`toolCount=0` は harness metadata の記録で、提示した入力以外を読んでいないことの根拠として使った。OS の filesystem/network sandbox ではない。
- 生ログと成果の完全パス:
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/input.json`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/observations.jsonl`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/baseline-task.txt`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/green-task.txt`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/baseline-result.txt`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/green-result.txt`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/baseline-audit.json`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/green-audit.json`
  - `/workspaces/agent-workspace/tmp/agents/issue-888-behavior.0p0nn9np/score.json`
  - `/home/vscode/.pi/agent/sessions/--workspaces-agent-workspace--/subagent-artifacts/5c5b3b8c_sp-research_0_meta.json`
  - `/home/vscode/.pi/agent/sessions/--workspaces-agent-workspace--/subagent-artifacts/5c5b3b8c_sp-research_0_output.md`
  - `/home/vscode/.pi/agent/sessions/--workspaces-agent-workspace--/subagent-artifacts/eb2a5475_sp-research_0_meta.json`
  - `/home/vscode/.pi/agent/sessions/--workspaces-agent-workspace--/subagent-artifacts/eb2a5475_sp-research_0_output.md`
- `baseline-result.txt` と `5c5b3b8c_sp-research_0_output.md`、`green-result.txt` と `eb2a5475_sp-research_0_output.md` は、それぞれ同じ内容であることを比較で確認した。

## 限界

- 各版 1 試行、モデルは `deepseek-v4.1-flash` の 1 つだけ。試行間のばらつき、他のモデル、Claude Code の挙動は未確認である。
- これは架空入力に対する評価 JSON の局所適用であり、ランタイムのエンドツーエンド比較ではない。draft の保存、承認ゲート、publish、実在 Issue への投稿は実行していない。投稿の有無や承認前の投稿禁止は、この比較では確かめていない。
- 実在の Issue や通常運用の作業ログは使っていない。実運用の誤判定頻度、改善率、時間短縮は測っていない。
- 確認したのは `main` と `boundary` の 2 ケースだけである。metadata の他の組み合わせ、日付による選択、複数の run が再開する場合などは未確認である。
- 旧版に誤判定が無かったのは、旧文書の矛盾する記述が method 明示の check 使用によって実行されなかったためである。旧文書が一般に安全であることや、新旧のどちらが優れるかは、この 1 回の比較だけでは判断できない。
- モデルと所要時間は harness metadata の記録で、回答自身はモデルを `unknown` としている。独立したモデル識別や OS レベルのアクセス監査はしていない。
- 採点は controller の `score.json` に基づく。実装担当は結果文と件数を照合したが、独立に再採点はしていない。
- 生ログは上記の tmp と session artifacts に依存する。これらが削除されると、同じ結果を後から再確認できない。

この比較は、#875 の既存の評価記録（`evaluation-validation.md` と `evaluation-scenarios.json`）を置き換えるものではない。既存記録は変更していない。
