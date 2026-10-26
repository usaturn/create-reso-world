# Issue #120: SDD の受け入れ基準と指摘の裁定

## 管理と実行許可

- 文書管理・対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/120
- 状態: `completed`（実行許可による実施。内容を `approved` にしたものではない）
- 開始 HEAD: `5b2c535`
- 実行許可: 利用者の `issue-to-pr #120 --merge --max-cycles 3`。通常の設計判断、実装、検証、commit・push・PR 作成を委任。マージは PR 修正ループの `finalize.py` に限る。
- 確認用コピー・追加承認待ちは issue-to-pr の手順に従い省略する。

## 意図・範囲

実装担当・タスクレビュー担当・controller が異なる条件を使って修正を繰り返さないよう、Plan の判断基準と指摘の渡し方をそろえる。変更対象は `AGENTS.md` の「SDD 実行運用」のみ。新しい Plan に適用し、既存の Spec・Plan、review-fix-planning の採否基準、共有 fixture、スキルや実行コードは変更しない。既存の実行予算・作業領域・監視・同期テストの規則を保持する。

## 選択肢

1. **採用: 共通規約に集約**。7 項目を現在の規則と整合する表現で足す。Claude Code・pi の双方に届き、スキルごとの重複管理を避ける。
2. スキルとランタイム設定にも展開する。範囲が広がり、上流との差分と二重管理が増えるため不採用。
3. 別文書への参照だけを追加する。短くなるが、重要な判断基準が brief へ渡らない危険が残るため不採用。

## 受け入れ基準

- 動作環境: Claude Code・pi の subagent-driven-development・executing-plans。Pi の読み取り専用レビューと同期実行の制限は変更しない。
- 実入力: 新しく作成する Plan、実装担当とタスクレビュー担当への brief、レビュー指摘の原文。実際の入力の形（複数行・非 ASCII 等）は各 Plan が対象に応じて記す。
- 防御範囲: Plan の動作環境・実入力・対象条件と対象外の反例/設定を明記し、同じ受け入れ基準を双方の brief に写す。指摘された文言自体の妥当性もレビュー対象とする。範囲外・Plan と矛盾する指摘は修正前に裁定・記録し、採用した指摘は原文のまま渡す。既存文書の遡及変更やレビュー後の採否基準の変更は対象外。

## 追加する規則

1. Plan に contingency 節を設ける。最初の RED で実出力・API の前提が違う場合、仕様の意味を保つ最小修正は ledger に記録して継続する。意味を変える場合は利用者の裁定を求める。安全境界・既存の停止条件を緩和しない。
2. Plan に「受け入れ基準」節を設け、動作環境・受け付けるべき実入力・防御範囲の 3 点を書く。実行可能な条件の実装前検証は「テストの採用基準」に従う（F/L の固定文言テストを強制しない）。
3. 実装担当とタスクレビュー担当の brief に同じ基準を写す。レビュー担当にだけ計画全体や Spec を追加して基準を変えない。指定された文言・条件も受け入れ基準の意図に照らす。
4. 防御範囲外・Plan と食い違う指摘は controller が修正ループの前に Plan と照合し、採否と理由を ledger に残す。
5. 指摘は原文のまま実装担当へ渡す。要約・言い換え・修正手段の指定を足さない。
6. 最終全体レビューで具体的な疑いに限り、絞ったテスト/最小再現を認める。実行できないランタイムでは controller が実行して結果を返す。複数レビュアーは入力→保存→検証の流れを通して担当する。
7. Plan 完成後、受け入れ基準・防御範囲・動作環境を提示し利用者確認を得る。issue-to-pr で着手した run だけは同スキルの委任に従い省略する。一般的な連続実行指示だけでは省略しない。

## 決定記録

| ID | 選択した案 | 検討した別案 | 理由 / 委任または停止条件 |
| --- | --- | --- | --- |
| D1 | controller・ledger・brief を維持し、初出を司令塔・進捗記録・依頼書と説明 | 全て日本語へ変更 | 既存の用語・スクリプトとの対応を保つ。通常の表現判断は委任内 |
| D2 | issue-to-pr の着手を確認省略の条件にする | #114 導入前の暫定条件 | #114 は closed、スキルは導入済み。一般的な続行指示へ例外を広げない |
| D3 | 実装前のテスト化に採用基準を適用 | 全条件のテストを必須化 | F/L を書かない既存方針と両立させる。規則の意味や安全境界変更なら停止 |
| D4 | Pi の再現は controller が実行して結果を返す | レビュー子に bash 権限を付与 | `.pi/APPEND_SYSTEM.md` と実際の read-only ツール制限を維持。権限変更は範囲外 |
| D5 | 文書のみ、1 Task を同期 SDD で実装 | 同じ節を複数 Task で並列編集 | 独立した変更単位がなく競合する。実装・タスクレビュー・全体レビューは委譲 |
| D6 | 変更前後に同じ小さな仮想 Issue を各1回、fresh context で計画させる | 固定文言の自動テスト / 大規模有料評価 | Issue が指定する行動比較を採用。統計的な保証はしない。追加評価は前後1組まで |
| D7 | `--max-cycles 3`、他は check-options の既定 | 独自のレビュアー追加 | inspect: claude-opus/devin-swe/pi-deepseek、fix implement: claude-opus、self-review/fix-check: self、fallback 空。Plan 実装は check の既定 self、runtime 指定により sp-implementer を使用 |

## 検証と限界

文書の固定文言テストは F なので追加しない。writing-skills の変更前/後比較で、同じ小さな Issue の Plan と双方の brief、範囲外指摘・実出力差への判断を観測する。行動比較は Pi の子で行うため、Claude Code の実運用や全入力を実証するものではない。7 項目の文書照合と既存規則の不変確認、`git diff --check`、README のワールド以外の全検証を行う。マージ後でなければ確認できない受け入れ項目は無い。

## PR #281 レビュー選別・最終化前の結果（サイクル1）

- 対象: https://github.com/usaturn/create-reso-world/pull/281、レビューHEAD `2928a904ed238a7207a6676bded8181c7d9e2221`。planner: `openai-codex/gpt-6.1-sol`（pi）。実行許可は冒頭の `--merge --max-cycles 3`、review-fix-planning の完遂に従う。
- 対象の現行Specはこのファイル1件。新しいround別文書は作らず更新した。Planは元のTask実施記録として保持する。

| レビューファイル | モデル | runtime | HEAD | 再実行 | 推奨 |
| --- | --- | --- | --- | --- | --- |
| claude-opus-5-5.md | claude-opus-5-5 | claude-code | 2928a904ed23 | true | Approve |
| SWE-2-Max.md | SWE-2 Max | devin | 2928a904ed23 | true | Approve |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | 2928a904ed23 | true | Approve |

全3件の入力を受け付け、却下・古い世代・前の判断は無い。review-verify による確認済み一覧は `reviews/usaturn/create-reso-world/#281-feat-issue-120-sdd-acceptance/verified/2928a904ed23.json`、工程の記録は同stemの `.planning.json`。

| 指摘 | 分類 | 現行HEADでの根拠と理由 |
| --- | --- | --- |
| claude-opus-5-5#L-1@2928a904ed23 | 対応しない | `AGENTS.md:191` は指定文言と実入力・実出力の意味照合を求めるが、Planの指定した条件そのものと受け入れ基準の意図の照合を明示していない。Specの規則3との静的な差異は確認した。実在の構成・利用経路で致命的な誤結果・損害・停止につながる根拠は確認されず、列挙・表現の不足としてreview-fix-planningの採用条件を満たさない。ラベルや多数決は根拠にしない。 |

解消済み0／対応する0／対応しない1。条件・照合基準の明確さに留保があるため、「7項目のあらゆる意図が明文で充足」とは保証しない。回避はタスクレビューでPlan/Specの意図も併読して指定条件自体を照合すること。具体的な致命的影響の根拠または利用者の名指しがあれば再判定する。PR説明にも制限を残す。採否基準は変えず、非致命的な追記修正はしない。対応する項目が無いため影響経路の修正表・設計の見直しは不要。

結論は2（追加修正不要、最終化へ進む）。規約の実装修正0、run_rolesによる修正・自己レビュー・fix-checkは未実施（各0回。不要な工程を成功とは記録しない）。既定割当てはD7のとおり。review-verifyの確認は候補の真偽確認で、修正後の自己レビューではない。

検証: 最後の実装・記録commit後のclean HEAD `2928a90` でREADMEの3検証（bash23、layout、pytest1237）とdiff検査はすべて終了0。baseが `5b2c535` から `a0ada37ddf7d82c6a06650ddf5ddbe6ce139c944` へ進んだため、同HEADにこのbaseを競合なくmergeした隔離ツリーでも3検証を実行し、bash23・layout・pytest1237がすべて終了0だった。一時mergeはpushせず、検証worktreeは削除済み。記録は `/workspaces/reso-world/tmp/agents/review-fix-planning-pr281.yxm4937h/checks.json` と `merge-verification.json`、実ログは同ディレクトリ `merge-check-1..3.log`。元のHEADの証拠は `/workspaces/reso-world/tmp/agents/issue-120.frs5sdx4/verification.json`。

未実施・限界: 指定条件自体を指摘する新規の行動比較、Claude Code実運用・統計的保証は未確認。元の比較の全文コピーの省略はPlanの結果どおり保持する。review-verifyが未読とした移植元はcontrollerが `e80433a` の差分を取得済み。変更ファイル全文・関連規則・既存テスト採用基準は読み終えており、確認済み一覧の未再実行範囲を未確認の致命的指摘とは扱わない。

所要時間: ループ開始18:34 UTC、3レビュー終了18:44、候補確認18:45〜18:50、base統合検証18:53〜18:59。能動時間はIssue予算内。マージ・Issue更新が済んだとはここでは記録せず、最終化の結果と状況コメントで確認する。
