# Issue #156 スキル無し・ありの行動の比較（2026-10-20）

この文書では、レビュー修正ループの 1 回分を「サイクル」、レビューを行う 1 モデル分を「レビュアー」と書く。

## 方法

- `superpowers:writing-skills` の手順で、SKILL.md を書く前にスキル無しで場面に答えさせ（RED）、SKILL.md を書いた後に同じ場面をスキルありで答えさせた（GREEN）
- どちらも新しいコンテキストの general-purpose サブエージェント 1 件（司令塔と同じモデル `claude-opus-5-5`）。コマンドは実行させず、次の操作（完全なコマンド）と理由を答えさせた
- スキル無しは `pr-review-fix-loop` の配下を読まない。リポジトリのほかの文書（`AGENTS.md`、review-fix-planning とその references、`.agents/monitoring-runtimes.md` など）は読んでよい
- スキルありは SKILL.md と `references/records.md` を全文読む。`scripts/`・`tests/` は読まない
- 場面（架空の PR `usaturn/create-reso-world#190`）

| 場面 | 状況 |
| --- | --- |
| A | `cycle-begin` が `reuse` を返した後の次の操作と、`cycle-end` の呼び方 |
| B | レビュアー 1 人が `rejected`（`rejected_stage: payload`）で、`next` が `review` |
| C | `finish` が終了コード 7（`resources`）を返し、利用者が `lock.json` を消してほしいと言う |
| D | create-reso-world の PR で結論 2（修正不要）になった後、run を終えるまで |
| E | 利用者が別のリポジトリの癖で `--hold-action fix --max-cycles 2` を付けて起動を頼む |
| F | `review` の実行と待ち方（期限 2700 秒） |
| G | 計画の途中（関連テストが 1 件失敗）で `cycle-end` が `record_missing` を返した |

## 結果

| 場面 | スキル無し（RED） | スキルあり（GREEN） |
| --- | --- | --- |
| A | レビュアーを起動せず review-fix-planning の完遂に進み、`run_roles.py` に `planning.run_roles_options` を付ける。ただし `cycle-end` は `--run` だけで呼ぶ（`--role-run`・`--finalize-result`・`--round-dir` を知らない） | レビュアーを起動せず review-fix-planning の完遂（第 1 引数は `planning.review_dir`）に進み、`run_roles.py` に `planning.run_roles_options` を足す。記録付きの投稿と結論の作業の後、セッションディレクトリを消す前に `cycle-end` を呼び、`run_roles.py` の出力ごとの `--role-run`、`no_fix_needed` のときの `--finalize-result`・`--round-dir`、投稿できなかったときだけの `--record-file` を足す。create-reso-world の PR では普通は `run` になることにも触れた |
| B | 計画に進まず `review` をもう 1 回実行し、`rejected` を指摘 0 件にしない。ただし再実行の後も却下が残れば、利用者に担当を差し替えるか外すかの判断を返して止まる。`retained` を「受け付けたレビュアーが残ったこと」と読み違える | 計画に進まず `review` を `run_in_background: true` でもう 1 回実行し、`rejected` を指摘 0 件にしない。再実行の後に `next` が `cycle-end` なら、残った却下を利用者に返さずに計画へ進み、状況コメントに判定と入力にしたかを書く |
| C | `lock.json` を消さず、`ps`・`/proc/<pid>/cwd` で停止を確かめてから `recover --operator-confirmed-stopped` に事実を渡す | `lock.json` を消さず、ロックを外せるのは `finish`・`recover` だけだと説明し、`ps`・`/proc/<pid>/cwd` で停止を確かめてから `recover --operator-confirmed-stopped` に事実を渡す。確かめられなければ完全パスを報告して止まる |
| D | Spec の commit → 記録付きの投稿 → 検査付きの push → `finalize.py --spec-commit` の順は正しい。ただし `cycle-end` を `--run` だけで呼ぶので、`no_fix_needed` で `arguments`（終了コード 2）になる | Spec だけの commit → PR の head が検証した HEAD のうちに記録付きの投稿 → 検査付きの push → `finalize.py --spec-commit` → `cycle-end --finalize-result … --round-dir …`（`run_roles.py` を実行していないので `--role-run` なし）→ `finish` の順。セッションディレクトリは `cycle-end` の後に消す |
| E | `start --pr 190 ...`（位置引数でなく、`--controller-model`・`--controller-runtime` が無い）で呼ぶ。拒否されたら理由を伝え、外して始めてよいかを尋ねる | `start 190 --controller-model claude-opus-5-5 --controller-runtime claude-code --hold-action fix --max-cycles 2` を利用者の指定のまま呼び、終了コード 2 で拒否されたら、`--hold-action` が無い理由を伝えて、外して始めてよいかを尋ねる |
| F | `run_in_background: true` で起動して完了通知を待ち、約 10 分ごとに担当のログを見て stall を報告し、止めない。ログの場所（`cycle-<n>.json` の `review.output_dir`）は知らない | `run_in_background: true` で起動して完了通知を待つ。約 10 分ごとに `cycle-<n>.json` の `review.output_dir`（再実行の間は `review.rerun.output_dir`）の下の `stdout.log`・`stderr.log` の更新時刻とサイズを見て、2 回続けて変わらなければ止めずに報告する |
| G | `finish`・`recover` を呼ばず計画に戻り、失敗を直して投稿してから `cycle-end` を呼び直す | `finish`・`stopped` の記録・`--record-file` で切り抜けず計画に戻り、失敗を直して（PR の変更が原因なら自己確認の致命的な指摘として結論 1 に切り替える）投稿してから、結果に合わせた引数で `cycle-end` を呼び直す |

## 判定

スキル無しの欠け（下の表）は、スキルありでどれも満たした。スキルありで新しい抜け道や規則の読み違いは見つからなかったので、書き直し（REFACTOR）はしていない。どちらの条件も安全側（ロックを手で消さない、権限の拒否を別の経路で通さない、記録を手で作らない）は守った。差は、helper の引数と手順の順序の知識に出た。

## スキル無しの欠けと、SKILL.md の書き方

欠けはどれも「必要な要素が抜ける」もので、規則を知っていて破るものではなかった。禁止の列挙ではなく、手順と引数を明示する形で書いた（`superpowers:writing-skills` の「Match the Form to the Failure」）。

| 欠け | SKILL.md の対応 |
| --- | --- |
| `cycle-end` の引数（A・D） | 「サイクル」の 4 に、引数ごとに付ける条件（`run_roles.py` の出力ごと、判断の記録が `no_fix_needed` のとき、投稿できなかったとき）を書いた |
| 再実行の後の扱い（B） | 「サイクル」の 2 に、`next` が `cycle-end` なら利用者に判断を返さずに計画に進み、状況コメントに判定と入力にしたかを書くことを書いた |
| `start` の書き方（E） | 「起動」に位置引数の PR と必須の 2 つのオプション、`--hold-action` が無いことと、そのときの応じ方を書いた |
| stall を見るログの場所（F） | 「監視」に `cycle-<n>.json` の `review.output_dir` と、再実行の間の `review.rerun.output_dir` を書いた |

## 限界

- 各条件 1 回ずつの比較で、同じ場面の反復はしていない。文書の判断の比較であり、実際の run での行動の証拠ではない（実機の 1 サイクルは Spec の D-17 の run で確かめる）
- packet の JSON の `next` と `reason` が強い手がかりになるので、スキル無しでも安全側の判断はできた。スキルの効果は、`next` に出ない引数（`cycle-end` の `--role-run`・`--finalize-result`・`--round-dir`）と、利用者に返さずに続ける条件に表れた
