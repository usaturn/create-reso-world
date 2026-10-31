---
name: pr-review-fix-loop
description: 利用者が `/pr-review-fix-loop <PR>`（Pi は `/skill:pr-review-fix-loop <PR>`）で明示的に起動したとき、または issue-to-pr が利用者の明示した `--merge`（#158 で入る）で PR を作った後に呼ぶときだけ使う。通常の PR レビュー・修正計画・レビュー指摘への対応の依頼からは起動しない。
disable-model-invocation: true
argument-hint: "<PR番号またはURL> [--max-cycles N] [--assign ROLE=AGENT[,AGENT]] [--template PATH] [--config PATH] [--fresh-review]"
---

# PR 修正ループ

この文書では、レビュー修正ループの 1 回分を「サイクル」、レビューを行う 1 モデル分を「レビュアー」と書く。

このスキルを起動したセッション（あなた）が司令塔である。

- **レビュアー**は、helper が agent-runner で並行に起動する（workflow `review` の role `inspect`）。各レビュアーは pr-review を非対話で 1 回実行する。
- **計画と修正**は、あなたが review-fix-planning の完遂の手順で自分で行う。採否・修正・push・状況コメント・最終化（マージと関連 Issue の更新）まで含む。判断の基準（現行 HEAD で確かめた致命的な指摘だけを直す）、三択の結論、修正後の自己レビューは最大 1 回は、review-fix-planning の SKILL.md のとおりで、このスキルは変えない。実装・自己レビュー・修正の確認は、review-fix-planning が `run_roles.py` で設定の割り当てどおりに起動する。
- **helper**（`scripts/loop.py`）が、PR ごとのロック、PR の HEAD の照合、レビュアーの結果の検査、同じ commit の再レビューの省略、判断の記録の照合、資源の回収を行う。

## 守ること

- 利用者が明示的に起動したとき、または issue-to-pr が利用者の明示した `--merge` で作った PR に対して呼ぶときだけ使う。PR の URL や、通常のレビュー・修正の依頼から自動で始めない。
- helper は、成功・失敗とも標準出力に JSON を 1 つ書く（引数の書式の誤りだけは、終了コード 2 と標準エラー出力の usage）。`next` は次に実行する完全なコマンドである。コマンドを自分で組み立て直さない。`requires_input` があるときは、そこに書かれたオプションに、自分で確かめた事実を書き足してから実行する（`<...>` のような書きかけの値は拒否される）。`status` が `error` なら、`stage` と `reason` を読んで「止まったとき」に従う。
- ロックと記録（`<review_dir>/loop/`）を手で作成・編集・削除しない。
- `rejected` のレビュアーを「指摘なし」として扱わない。
- loop 自身は PR にコメントしない。PR への書き込みは、review-fix-planning の状況コメント（push の後に base が進んだときと、マージの後の照合で止まったときの補足を含む）と最終化だけである。
- 新しい PR を作らない。force push、`main` への直接の push、admin マージをしない。

## 起動

利用者が渡した PR とオプションを、そのまま `start` に渡す。オプションを足したり、既定値を作ったり、知らないオプションを外したり読み替えたりしない。`TOOL_ROOT` は親の main checkout である。feature worktree の `loop.py` を使わない（PR で変更中のスキル・helper でレビューさせない）。

```bash
TOOL_ROOT="$(uv run --no-project python .agents/scripts/agent_tmp.py root)"  # リポジトリのルート（main checkout か worktree）で実行する
uv run --project "$TOOL_ROOT" --locked python \
  "$TOOL_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" start "<PR>" \
  --controller-model "<あなたの正確なモデル ID>" --controller-runtime "<ランタイム>" \
  <利用者が指定したオプション>
```

- `<PR>` は位置引数（`190`・`#190`・PR の URL）。番号は親の origin の PR である。
- `--controller-model` は、review-fix-planning が状況コメントに使う `MODEL_NAME` と同じ値にする。`--controller-runtime` は `claude-code`・`devin`・`pi`・`codex`・`cursor` のどれか。
- `--max-cycles N`: サイクルの上限（1〜10、既定 3）。
- `--assign ROLE=AGENT[,AGENT]`（複数可）: `inspect`（レビュアー、複数可）と、`implement`・`self-review`・`fix-check`（各 1 つ。review-fix-planning の `run_roles.py` に渡す）。agent は agent-runner の設定に定義された名前。
  - `inspect`・`self-review`・`fix-check` には、runtime が `codex` の担当（`codex_openai_gpt6-sol_default` など）を一次担当にも fallback にも割り当てられない。codex は `writes=false` の役割を read-only の sandbox で起動し、helper を起動できない。`implement` には割り当てられる。
  - `start` は、`run_roles.py` が設定だけで拒否する fix の割り当て（上の codex の担当のほか、一次担当が 2 つ以上、`self-review`・`fix-check` の `writes = true` など。個人設定で決まるものを含む）と、codex の担当を含む `inspect` の割り当てを、run を作る前に終了コード 2（`config`）で止める。`reason` を利用者に伝えて止まる。別の担当や `self` に自分で切り替えない。
- `--template`・`--config`: agent-runner の雛形と個人設定。既定は雛形 `.devcontainer/agent-runner.toml` と既存の個人設定。
- `--fresh-review`: 現在の HEAD のレビューの成果があっても、レビュアーを起動する。
- `--hold-action` は無い。移植元（usaturn/agent-workspace）のループにはあるが、このリポジトリの review-fix-planning には判断保留（Hold）が無いので受け付けない。付いていれば `start` が終了コード 2 で拒否する。外して続けず、理由を伝えて、外して始めてよいかを利用者に尋ねる。
- `check-options`: `start` と同じオプション（`--fresh-review` を除く）と agent-runner の設定だけを、`start` と同じ関数で検査する。PR・ロック・run・GitHub・Herdr に触れず、記録を書かない。成功の出力の `options`・`assignments` は `start` が `run.json` に保存するものと同じで、`next` は null。issue-to-pr の `--merge` は、worktree を作る前にこれを呼ぶ。終了コード 2 なら `reason` を利用者に伝えて止まる。
- 扱う PR は、Git 操作の対象の checkout を `CODE_ROOT` なしで決められるものだけ（create-reso-world と、`external/resoloop` の usaturn/resoloop・orange3134/resoloop）。それ以外（usaturn/resoloop-meshy など）は `start` が終了コード 2（`arguments`）で止める。マージは review-fix-planning の「マージしてよい範囲」のまま。
- 終了コード 3（`lock_held`）は、別の run がこの PR を使っていることを示す。`next`（`status`）で持ち主を確かめ、利用者に報告して止まる。古く見えても消さない。
- `warnings` に未 commit の変更があるときは、レビュアーが作業ツリーのスキルと helper（未 commit の変更を含む）を読むことを利用者に伝える。
- Herdr のペインの中（`HERDR_ENV=1` で `HERDR_PANE_ID` がある）で起動すると、`start` は run を始めた後で、現在のペインの名前を `PR#<番号>` に変える。結果は出力と `run.json` の `herdr_pane` にある。`herdr` を自分で呼ばない。名前を変えられなくても run は続き、理由が `warnings` に入るので、利用者に伝える。

## サイクル

1. **`cycle-begin`**: 返った `review.mode` を見る。
   - `run`: `next`（`review`）を実行する。
   - `reuse`: 現在の HEAD のレビューの成果が、すでにレビューディレクトリにある（前のサイクルの push 前の PR 全体レビューなど）。レビュアーを起動せずに 3 へ進む。
   - create-reso-world の PR では、結論 1 で自己レビューの後に Spec の commit を載せて push するので、次のサイクルの HEAD は自己レビューした commit と違い、`run` になる（レビュアーを起動し直す）。
2. **`review`**: 全レビュアーが終わるまで同期で待つ（「監視」）。出力の `accepted` と `rejected` を確かめる。`rejected` は失敗したレビュアーで、指摘 0 件ではない。`rejected_stage` は却下した段階（`runner`・`payload`・`binding`・`head`・`artifacts`）である。
   - 返った `next` が `review` のとき（再実行待ち。対象は `rerun.agents`）は、runner は成功したが結果を受け付けられなかったレビュアーを、同じサイクルで 1 回だけ起動し直す。計画に進まず、その `next` を同じように同期で待って実行する。次に何を実行するかは `next` だけで決める（`rerun` は再実行を終えた後の出力にも残る）。runner の失敗（期限切れ・認証待ち・起動失敗）は再実行しない。
   - 返った `next` が `cycle-end` なら、受け付けたレビュアーが 1 人以上いて、停止を確かめられない試行が無い。停止を確かめられない試行があれば、受け付けたレビュアーがいても計画に進まず、終了コード 7 で止まる（「止まったとき」）。再実行の後も `rejected` のレビュアーが残っていても、利用者に判断を返さずに 3 へ進む。状況コメントには、loop の判定（`rejected` と理由）と、そのレビュアーの成果を計画の入力にしたかを書く。保存の後に失敗した（後片付けの失敗、`response_failed` など）レビュアーの成果は、このサイクルの HEAD のままレビューディレクトリに残ることがあり、review-fix-planning はそれも読む。
   - `retained` は消さずに残したパスで、最終報告に書く。終了コード 6 は全員の失敗である（「終わり方」）。
   - 失敗した担当がいるレビュアーには、試行ごとの診断（`diagnostic_file`）がある（終了コード 6 のエラーの出力の `rejected` にもある）。runner のログは回収で消えるので、失敗の原因（`cause`）・上書きの前の状態（`reported_state`）・取得できなかった情報（`unavailable`）は診断で調べる（[records.md](references/records.md) の 4.1 節）。`diagnostic_error` があれば診断を保存できなかったので、その理由と、ログを含めて残した出力（`retained`）を利用者に伝える。
3. **計画**: review-fix-planning の SKILL.md を読み、`planning.review_dir`（レビューディレクトリの完全パス）を第 1 引数にして、完遂の手順を最後まで行う。
   - `run_roles.py` の呼び出しには、`planning.run_roles_options`（`--template`・`--config`・`--assign`）をそのまま足す。
   - 関連検証が失敗したら、review-fix-planning の規則どおり原因を診断して直す。loop は計画の結果を待ち、サイクルを終えない。
   - review-fix-planning は、状況コメント（判断の記録）を投稿して、`fixes_pushed`・`no_fix_needed`・`stopped` のどれかで終わる。create-reso-world の PR の結論 2 は、Spec だけの commit を載せて `finalize.py --spec-commit` でマージする（`.agents/skills/review-fix-planning/references/execution.md` の 3 章）。`finalize.py` の待てば進む停止（`wait_for`）と base の前進（`base_moved`）による再実行は、review-fix-planning の結論 2 の手順 7 のとおり計画の中で行い、終わってから `cycle-end` を呼ぶ。マージの後の照合で止まったとき（結果に `merge_parent`）は、計画の中で再検証せずに `cycle-end` に渡す（run は `stopped`・`merged: true` で終わる）。
4. **`cycle-end`**: `next` のコマンドに、この計画の結果に合わせて次の引数を足して呼ぶ。
   - `--role-run <dir>`: この計画で実行した `run_roles.py` の出力ディレクトリ（`--output-dir`）ごとに 1 つ。実際の割り当ての記録に使う。`run_roles.py` を実行しなかったサイクルでは付けない。
   - `--finalize-result <file>` と `--round-dir <dir>`: 判断の記録の結果が `no_fix_needed` のとき（finalize.py が `stopped` を返したときも含む）。finalize.py の `--result-file` と、finalize.py に渡した記録・本文・検証記録を置いたディレクトリ（review-fix-planning のセッションディレクトリ）。
   - `--record-file <file>`: 状況コメントを投稿できなかったときだけ。投稿しようとした記録の JSON。
   - ここで渡すディレクトリとファイルは、review-fix-planning のセッションディレクトリの中にある。review-fix-planning の後片付け（`.agents/skills/review-fix-planning/references/execution.md` の 4 章のセッションディレクトリの削除）は、`cycle-end` が終わった後に行う。
5. `next` が `cycle-begin` なら 1 へ戻る。`finish` なら「終わり方」へ進む。

`cycle-end` が返す主な拒否:

| 終了コード・`stage` | 意味と対応 |
| --- | --- |
| 4 `record_missing` | このサイクルの HEAD の判断の記録が、まだ PR に無い。計画を最後まで進めて投稿してから呼び直す。状態は変わらない |
| 4 `record_inconsistent` | 記録が前の判断と食い違う（引き継いだ判断の状態を根拠なく変えた、など）。review-fix-planning の規則で記録を直して投稿し直す |
| 4 `pushed_head_mismatch`・`merge_mismatch` | 記録と PR の実際の状態（HEAD・マージ）が合わない。実際の状態を確かめて利用者に報告する |
| 2 `arguments` | `no_fix_needed` なのに `--finalize-result` が無い、など。正しい引数で呼び直す |
| 5 `github` | 認証済みの login（`gh api user`）や PR のコメントを読めない。`gh` の認証と GitHub の状態を確かめ、直せなければ利用者に報告して止まる |

finalize.py を実行した後の拒否は、「止まったとき」の「finalize の後の `cycle-end` の停止」も読む。

## 終わり方

ループの結果は、最後のサイクルの結果である。

| 結果 | 意味 |
| --- | --- |
| `no_fix_needed` | 修正不要を確かめ、マージと関連 Issue の更新まで終えた |
| `stopped` | 権限・環境・外部の具体的な障害で止まった（`stop_reason`） |
| `fixes_pushed`（`ended_by: cycle_limit`） | 修正を push したが、サイクルの上限に達した。マージしていない |

- `next` の `finish` を実行する。ロックを解放し、要約を返す。
- サイクルの途中で続けられなくなったとき（全レビュアーの失敗、計画を実行できない障害など）は、`finish --run <run_dir> --abort "<permission|environment|external>: <具体的な障害>"` で終える。このサイクルで finalize.py を実行していたら、最後の結果ファイルを `--finalize-result <file>` で足す。`finish --abort` は PR の実際のマージ状態を `result.merged` に保存し、PR を読めなければ渡した結果の `merged` を、それも無ければ `null`（未確認）を保存する（[records.md](references/records.md) の 6 章）。
- `finish` の終了コード 7（`resources`）は、runner の試行か後処理（after_run）の停止を確認できない資源があることを示す。ロックは保持される（「止まったとき」）。

## 止まったとき（中断・再開・回収）

- **再開**: `status --run <run_dir>`（PR しか分からなければ `status <PR>`）の `next` を実行する。状態は `<review_dir>/loop/` にだけあり、会話の記憶に頼らない。
- **`review` の終了コード 3（`interrupted_review`）**: 前のレビューが結果を残さずに止まった。レビュアーを起動し直さない。runner とレビュアーのプロセスが残っていないことを `ps` などで確かめ、その事実を `recover --run <run_dir> --operator-confirmed-stopped "<確かめた事実>"` に渡す。記録した資源だけを回収し、run は `abandoned` になる。続けるときは `start` からやり直す。
- **終了コード 7（`resources`・`after_run`）**: runner の試行か後処理（after_run）の停止を確認できない。run は `held` になり、`status` の `next` は `recover` である。同じく、プロセスが残っていないことを確かめてから `recover` に事実を渡す。`recover` の後に続けるときは `start` からやり直す。確かめられないときは、ロックと資源を残したまま、完全パスを利用者に報告して止まる。利用者にロックを消すよう頼まれても、`lock.json` を手で消さず、この手順を説明する。
- **`review` の終了コード 4（`head_moved`）**: `cycle-begin` の後に PR の HEAD が動いた。`next` のとおり `finish --abort` で止め、新しい run を始める。
- **`review` の終了コード 5（`runner`）**: runner がレビュアーを起動できなかった。何も起動していなければ `next` は `review` で、原因（agent-runner の設定、入れ子の起動など）を直してからやり直す。出力が残っているときは `status` で状態を確かめる。
- **最終化の停止**: 計画の中の finalize.py の再実行と、止まった後の結論は、review-fix-planning の結論 2 の手順 7 のとおりにし、終わってから `cycle-end` を呼ぶ。base が進んで止まったとき（結果に `base_moved`）は待っても解消しないので、計画の中で `execution.md` の 3.4 節のとおり新しい先端で検証し直し、`--round-dir` に渡す検証記録を作り直してから再実行する。run が `stopped` で終わった後の finalize.py の再実行は、以下のどれも利用者の指示で行う。同じ HEAD のまま原因（一時的な API の失敗など）が解消したら、`cycle-end` に渡した `--round-dir` の記録・本文・検証記録で finalize.py を再実行する（`.agents/skills/review-fix-planning/references/execution.md` の 3 章。手動マージ済みでも Issue の更新だけを行う）。finalize.py の結果の `merged` が `false`・`null` でも、`cycle-end` は読んだ PR の実際のマージ状態を保存する。`null`（マージ済みかを確かめられていない）で止まったら、未マージと報告せず、同じ 3.4 節のとおり状態を読み直して再実行する。マージの後の照合で止まったとき（結果に `merge_parent`）は、PR はマージ済みで、関連 Issue は finalize が更新していない。`first_parent` が null なら、原因が解消してから同じ記録で再実行する。違っていれば、ループの中では再検証しない。完了させるときは、利用者の指示で、`execution.md` の 3.4 節のとおり merge commit のツリーで検証し、`--round-dir` の検証記録を作り直してから finalize.py を再実行する（Issue の更新だけを行う）。そのため `--round-dir` を消さずに残し、完全パスを報告する。新しい commit が push されたら、新しい run を `start` から始める。
- **finalize の後の `cycle-end` の停止**: finalize.py を実行した後に `cycle-end` が止まったら（5 `github`、4 `merge_mismatch` など）、やり直すか `finish --abort` で終えるかを決める前に、`--finalize-result` に渡した結果ファイルの `merged` を確かめる。`true` は finalize がマージ済みを観測した記録で、マージは取り消せないので、PR に commit を足さない。abort するときは、`merged` が `false`・`null` でも同じファイルを `--finalize-result` で渡す（`finish` が PR を読めなくても、観測したマージ状態が run に残る）。`null` は未確認で、未マージと報告しない。
- 他の run のロック・資源・worktree を消さない。glob や `rm -rf` で推測して消さない。

## 監視

`review` は、全レビュアーの終了と停止の確認まで戻らない（役割の期限に停止の猶予を足した時間。雛形の `inspect` は 2700 秒（45 分））。`monitoring-long-tasks` に従う。

- 完了通知のあるランタイム（Claude Code の Bash の `run_in_background: true` など）は、`review` をバックグラウンドで実行し、終了コード付きの通知を待つ。
- 完了通知の無いランタイム（Pi など）は、bash ツールの `timeout` を付けずに前景で実行する。期限は runner が守る（`.agents/monitoring-runtimes.md`）。
- stall は、`<run_dir>/cycle-<n>.json` の `review.output_dir` の下の、担当ごとの `stdout.log`・`stderr.log` の更新時刻で判定する。再実行の間（`review.rerun` があり、その `batch` が無い）は `review.rerun.output_dir` の下を見る（1 回目の出力は回収済み）。10 分間隔の確認で 2 回続けて変わらなければ stall を疑い、プロセスを止めずに利用者へ報告する。
- 計画の工程はあなた自身の作業である。その中で起動する `run_roles.py` の待ち方は review-fix-planning に従う。

## 最終報告

- PR の URL、run ID、`<review_dir>/loop/<run_id>/` の完全パス
- 現在の Herdr ペインの名前を変えた結果（`run.json` の `herdr_pane` の `state`。`skipped`・`failed` は `reason` も）
- サイクルごとに: HEAD、レビューの `mode`、レビュアーごとの状態・実際の担当・モデル、判断の記録（round とコメントの URL）、結果、push した commit
- 失敗したレビュアーの診断のパスと試行ごとの原因の分類（`cause`）。保存できなかったときは理由（`diagnostic_error`）
- 最終の結果、`ended_by`、マージしたか（`result.merged`。`null` は未確認で、未マージと書かず、PR の状態を読み直して書く）、`stop_reason`。finalize の結果に `error_detail`（`gh` の失敗の要点）があればそれも
- 関連 Issue は、finalize の結果に含まれる、更新後に観測した state を書く。GitHub 側の自動 close を含め、Issue が閉じたことを要件が完了したことの証明として扱わない（要件の評価は review-fix-planning の記録に従う）
- finalize の結果に `merge_parent` があれば、3 つの SHA（`verified`・`merge_commit`・`first_parent`）と、関連 Issue を finalize が更新していないこと（`Closes` による GitHub の自動の close は別。#138）、再検証の手順（`.agents/skills/review-fix-planning/references/execution.md` の 3.4 節）を書く
- 残した資源（`retained`）の完全パスと、回収の操作
- 所要時間（全体とサイクルごと）

## 記録

loop の記録の形式・置き場所・終了コードは [references/records.md](references/records.md) にある。記録は進行と参考データの索引で、レビュー・確認・判断の中身は既存の成果（レビューファイル、`findings/`、`verified/`、判断の記録）をパスと SHA-256 で参照する。

## ランタイムごとの違い

- **起動**: Claude Code は `/pr-review-fix-loop <PR> ...`、Pi は `/skill:pr-review-fix-loop <PR> ...`。そのほかのランタイムは、このスキル（`.agents/skills/pr-review-fix-loop`）を明示して呼ぶ。
- **`disable-model-invocation: true`**: Claude Code がモデルの判断でこのスキルを起動しないようにする設定。ほかのランタイムでも、本文の「明示的に起動したときだけ使う」を守る。issue-to-pr が `--merge` で呼ぶときは、Skill ツールで起動できないので、親の main checkout のこのファイルを読んで従う。
- **`--controller-model`**: Pi は pi-model-name で `PI_PROVIDER` と `PI_MODEL` を確かめる。ほかのランタイムも、現在提示されている正確なモデル ID を使い、設定や過去の記録から推測しない。
- **監視の手段**: 上の「監視」と `.agents/monitoring-runtimes.md`。
