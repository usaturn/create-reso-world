# Issue #189: レビュー修正前の要件照合と保証変更の委任確認

- 状態: completed（実装・検証とレビュー修正判断の完了。内容承認を意味しない）
- 対象: usaturn/create-reso-world / https://github.com/usaturn/create-reso-world/issues/189
- 実行許可: 利用者の指示「issue-to-pr #189 --merge --max-cycles 3」。通常の設計判断、実装、検証、commit、push、PR 作成と指定ループの実行許可であり、内容の承認ではない。
- 文書・実装先: `.worktrees/issue-189-review-requirements`、base `5b2c535` (origin/main)

## 意図・範囲

取り込む。修正方針を決める前に PR の約束・制限、既存 Spec・Plan、今回の修正と検証を対応付け、保証を狭める案を委任範囲の確認なしに選べないようにする。既存 Spec 内の対応メモと経路表を使い、新しい帳票・helper・schema は作らない。

## 条件

- C1: 分類後、「対応する」項目の経路表・修正方針の決定前に共通参照1章を読み、PR の約束・制限と既存 Spec・Plan を今回の修正方針・観測結果・検証方法へ対応付ける。既存文書が無ければ PR と依頼を基準に、その不在も記す。
- C2: 共有する入力解釈・状態・操作順・外部仕様には統合担当と検証方法を置く。担当別のテスト成功だけで共有保証を閉じない。issue-to-pr の Spec → Plan → Task の既存経路も保つ。
- C3: 保証を狭める案は、依頼・既存の承認がその変更を委任しているか確認し、根拠と許可された変更内容を既存 Spec に記録してから選ぶ。PR 説明への開示や一般的な継続指示はその許可の代わりではない。範囲外なら完遂ではその案を選ばず、元の保証を満たす案で進める（新しい結論3の理由を作らない）。計画のみでは変更案と必要な承認を Spec に書き、既存の承認手順で確認する。
- C4: implement の依頼は、対応する条件・その条件に関わる除外範囲・共有前提・統合担当の確認と必要な証拠を渡す。RoleInput の5キーは変えず prompt 内の情報とする。
- C5: 採否、計画のみ／完遂、自己レビュー最大1回、公開・マージ権限、既存の補助指示2〜6は変えない。文言一致のpytestを追加しない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由・委任指示または停止条件 |
|---|---|---|---|
| 取り込み | 既存手順に接続 | 不採用／独立した新手順 | 共通参照1章が review-fix の必須読取経路から外れ、3章が消費する要件対応の作成段が無い。実行許可に基づく通常の設計判断 |
| 共通参照 | 1章に初回実装とレビュー修正の入力・対応先を併記 | review-fix 専用参照を新設 | 共通原則を重複させず初回実装も維持 |
| 範囲外の縮小 | 完遂は保証維持、計画のみは承認対象として提示 | 独断縮小／完遂を判断待ちで停止 | 権限を広げず既存の完遂規則も維持 |
| 実行方式 | 1 TaskをSDDで同期委譲 | 3文書を別Taskで並列 | 読取順・共有用語・引き渡しが一体の変更で、分割すると中間的不整合が生じる。並列に書く独立Taskなし |
| 実装の割当 | self（雛形既定）。本セッションはsp-implementerで実行 | --implementによる置換 | check出力: agents=[self], fallback=[], self=true。利用者が担当名を指定したとは記録しない |
| レビューループ | max_cycles=3（利用者指定）、assign={}、template=.devcontainer/agent-runner.toml、config=null | 既定の置換 | check-options成功。review.inspect=[claude-opus,devin-swe,pi-deepseek], fix.implement=[claude-opus], self-review=[self], fix-check=[self]、全fallback=[] は既定の適用。起動・設定失敗時は黙って担当を変更しない |

## 検証・評価

文書の固定値検査はF、構文や参照切れはLであり、pytestを追加しない。既存検査、相対参照の実在、JSON解析、git diff --check、skill-efficiency-checkで検証する。READMEの非ワールド3コマンド（pytest、環境テスト、layout）を最終HEADで通す。

行動評価は変更前後で同じ2ケースを各1回だけ実施する。A: 共有parser・複数入口・除外範囲・期限圧力、B: 保証を狭めたくなる再発・期限・費用圧力（委任なし／あり、計画のみを比較）。実モデルCLIや有料APIの反復は行わない。変更前の回答は保証維持・統合担当を自発的に提案し、1章も自発的に読んだため、無断縮小の行動失敗は観測していない。一方、列挙した修正方針前の手順では要件対応の作成が経路表より前に独立して現れず、保証の記録は後段に置かれた。この順序の不足を構造的に補う。少数の思考実験であり、収束率・退行防止の実証とはしない。評価の出力形を整える文言micro-testではなく、参照経路と条件付き権限の接続の確認である。

## 非対象

実装コード・helper・設定・frontmatter・分類基準の変更、補助指示2〜6の再設計、過去の検証記録の書き換え、実運用のサイクル数測定は対象外。既存の評価文書に今回の限定評価を追記するだけで、過去の未実施を実施済みにしない。

## 実施記録

Task 1 の `627402a` でC1〜C4の参照経路・委任境界・promptの接続を実装し、C5の維持を差分で確認した。関連pytest697件、全体1237件が成功し、task reviewは仕様適合・品質Approved（Critical/Importantなし）。最終HEADでの検証は公開前に別途行う。

変更後の同一2ケース1回では、Aが方針前の要件対応と共有担当を挙げ、Bが未委任の縮小を拒否した。ただしAは分類前に要件対応を置く順序不一致があり、全面的な遵守は未確認。限定pilotは行動改善・収束率・費用・退行防止の実証とはせず、評価文書に限界を残した。

## PR #280 レビュー修正判断（サイクル1）

- 実行許可: 冒頭の利用者指示の `--merge --max-cycles 3` によるループ。planner は `gpt-6.1-sol` / pi（PI_PROVIDER=`openai-codex`、PI_MODEL=`gpt-6.1-sol` をbashツールで確認）。手順とhelperは親checkout `5b2c535` のものを使用。
- 対象HEAD: `0ae24f674f4c16cd22b2164c6f4217e9d5dafdc3`、レビューのmerge-baseは `5b2c535d4da20387958b66f0ab71d361b039f5cc`。レビューは全員このHEADのInitial、再実行あり。前の判断記録は無し。

| レビューファイル | モデル | runtime | HEAD | このサイクルで再実行 | Merge recommendation |
|---|---|---|---|---|---|
| claude-opus-5-5.md | claude-opus-5-5 | claude-code | 0ae24f674f4c | はい | Approve |
| SWE-2-Max.md | SWE-2 Max | devin | 0ae24f674f4c | はい | Approve |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | 0ae24f674f4c | はい | Approve |

全3レビューファイル・候補JSON・対象差分と関連参照を照合。validate/check-pair成功、対象の祖先確認成功。active・未確認候補とも0件で、解消済み0／対応する0／対応しない0、全指摘の一覧は空。自己確認で追加すべき致命的欠陥も無い。実在する制約の未開示は無く、PR本文は限定評価の順序不一致と未実証を既に記載している。新しい保証の縮小・設計変更はしていない。

C1〜C5と既存の要件対応を再照合し、文書の参照順・要件対応スロット・委任境界・prompt情報・維持範囲が一致することを確認した。統合担当はcontroller。対応する項目が無いため修正方針・原因経路表・設計見直しの新規行は対象無し。候補0件の照合と既存ログの確認は相互に独立した再現タスクが無いのでcontrollerが行い、追加の子や実モデルCLIは起動していない。

結論2（修正不要として最終化）。修正実装・修正後自己レビュー・fix-checkは未実施（修正不要のため、run_rolesの起動0回）。確認済み一覧は `reviews/usaturn/create-reso-world/#280-fix-issue-189-review-requirements/verified/0ae24f674f4c.json`、工程記録は同stemの `.planning.json`。当初は実行前後cleanの同一HEADの検証記録を再利用する予定だったが、投稿前のbase再取得で `a49b37221839be2268a8ae3e7c3f6e72c0fc9886` への前進を検出した。まだコメント・pushは行っていない。対象HEADに新baseをmergeした一時ツリー `64fc9e9e5d0be456af5d9712f08b7f9fa0ddbcdc`（親は対象HEADと新base）を隔離worktreeで作り、同じ検証をすべて再実行した。merge自体はpushせず、Specだけの未公開commitを記録更新のため作り直す。base前進のやり直し1回目。

- `uv run pytest tests/skills .agents/skills .agents/scripts tools`: 初回head検証1237 passed / exit0 / 359.88秒、新baseとの一時mergeツリーも1237 passed / exit0 / 346.81秒。
- `bash .devcontainer/run-tests.bash`: 23 test(s) PASS / exit0。
- `bash scripts/check-layout.sh`: PASS / exit0。
- `git diff --check origin/main...HEAD`、JSON/ID・参照実在、skill-efficiency-check: exit0。既存description warningとuvの親VIRTUAL_ENV無視warningはPR本文に記載。
- ログは親checkoutの `tmp/agents/issue-189.rfny9g8t/final-*.log`、HEAD・clean状態・argv・終了コードは同じ場所の `verification.json` と `checks.json` に保存した。新baseとの一時mergeツリーのログは親checkoutの `tmp/agents/review-fix-planning-pr280.ms0rcmkt/merge-*.log`、検証記録は同じ場所の `merge-verification.json` と `checks.json` に保存した。マージ・Issue更新を先に実施済みとは書かず、実行結果は状況コメントとループ記録へ残す。
