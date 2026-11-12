# issue-to-pr: レビュー runner 実行中の対象 checkout 書き込み禁止の明示 設計仕様

- 状態: `completed`（サイクル 1 の修正・検証・自己レビュー完了。push・マージ・Issue 更新の結果は状況コメントと完了報告に記録し、本文書には追記しない）
- 日付: 2026-11-13
- Issue: [usaturn/create-reso-world#417](https://github.com/usaturn/create-reso-world/issues/417)
- 対象: `.agents/skills/issue-to-pr/SKILL.md`（`.claude/skills/issue-to-pr` は symlink）
- 関連: #382 / PR #411（発生した run）、#350・#364（監査実装側。本 Issue とは別テーマ）、#378 / PR #421（同じ SKILL.md の 2 章 6・5 章を編集済み・マージ済み）

## 管理・実行許可

利用者の指示（2026-11-13、スラッシュコマンドの原文）:

```
/issue-to-pr #417 --merge --spec-review devin_swe2_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max
```

- 許可された範囲: issue-to-pr スキルに従い、推奨案での設計判断、Spec・Plan の作成と commit、実装、検証、push、PR 作成、PR 修正ループ（`--merge`。ループの `finalize.py` によるマージと関連 Issue の更新まで）
- Spec レビュー担当: `devin_swe2_max`（明示指定。個人設定の `fallback` は無し）
- ループの割り当て: `inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max`（明示指定）。サイクル上限 3 は既定の適用
- Plan の Task の実装担当: `self`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。`--implement` 指定なし）
- この文書は `draft` のまま commit する。実行許可は内容の承認（`approved`）ではない

## 意図と背景

issue-to-pr の Spec・設計レビューで、レビュー runner の実行中に controller がレビュー対象 checkout（`CODE_ROOT`）へ書き込むと、runner の checkout 監査が内容変化を検知し、helper が受け取りを拒否する（`state: failed` / `outside_changes`）。PR #411（Issue #382）の run では、Spec レビュー実行中に controller が Plan 草案を `CODE_ROOT/docs/superpowers/plans/` に書いた（untracked ファイル 1 件）だけで、完了した有料レビュー（434.98 秒・findings 2 件）が失われ、再実行（514.70 秒）が必要になった。

runner の batch 自体は success でも、受け取り入口は `outside_changes` があれば拒否する（`tools/agent_runner/interfaces.rst`「期限と保持」）。監査ガードは正しく機能しており、修正すべきは利用側スキルのガイダンスである。スキル本文にはレビュー開始時の HEAD 照合と `outside_changes` の失敗扱いの記述はあるが、**実行中**の書き込み・コミットを禁止する記述が無い。一方 monitoring-long-tasks は待機中の並行作業を奨励するため、Spec レビュー待機中に Plan を準備する自然な行動が罠になる。

同型の罠は設計レビュー・Spec レビュー・再レビューのすべてで起きる。実装 Task の依頼（`implement_task.py run`）でも runner は同じ監査を行うため、依頼実行中の feature worktree 書き込みも同様に拒否される（`rejected`）。

## 受け入れ条件

Issue #417 の「対応時に決めること・受け入れ条件」をそのまま採用する。

1. issue-to-pr の「Spec・設計レビュー」節に、次を明示する。
   - レビュー runner の実行中は、レビュー対象 checkout（`CODE_ROOT`・同一なら `DOC_ROOT`）への書き込み・コミットをしない
   - 準備は `SESSION` で行う
   - コミットは受け取り後に行う
2. 「Task の実装を runner の担当に依頼する」節に、`implement_task.py run` の実行中も feature worktree を変更しないことを明示する（既存の「未 commit の変更を残さない」と整合させる）
3. 文書の変更であり、テストは不要（AGENTS.md の採用基準 F）。検証は `bash scripts/check-layout.sh` と文面の照合で代える
4. 編集対象は `.agents/skills/issue-to-pr/SKILL.md` のみ（`.claude/skills/` は symlink なので追従する）

## 設計（推奨案）

### 追加 A: 「Spec・設計レビュー」節の実行中書き込み禁止

節内の「依頼 JSON は…review の直前に今の HEAD で作り直す」の段落と JSON 例の直後、「**設計レビュー（`--design-review` があるときだけ）。**」の直前に、次の段落を追加する。この位置は、開始時 HEAD 照合（既存）と各レビューの helper 起動手順（後続）の間にあり、設計レビュー・Spec レビュー・再レビューのすべてに適用される。

> **レビュー runner の実行中は対象 checkout を変更しない。** `review` の起動から結果の受け取り（外部は `review` の完了、`self` は `submit` 成功）まで、レビュー対象 checkout（`CODE_ROOT`。`DOC_ROOT` が同一の checkout ならその `DOC_ROOT`）への書き込み・コミットをしない。runner の checkout 監査は実行の開始前に登録されていた checkout の HEAD・index・tracked ファイル・非 ignored untracked ファイルを終了後の状態と比較する（`tools/agent_runner/interfaces.rst`「期限と保持」）ため、Plan 草案のような untracked ファイル 1 件でも `outside_changes` の拒否になり、完了した有料レビューが失われて再実行が必要になる。待機中の準備（Plan 草案・調査メモなど）は `SESSION` の下で行い、並行作業は対象 checkout の読み取りと `SESSION` への書き込みに限る。対象 checkout への書き込み・コミットはレビュー結果の受け取り後に行う。これは設計レビュー・Spec レビュー・再レビューのいずれでも同じである。

### 追加 B: 「Task の実装を runner の担当に依頼する」節の実行中書き込み禁止

項目 3（**依頼:** 終わるまで待つ…）の段落に、待機の指示に続けて次の文を追加する。

> 依頼の実行中は feature worktree（`CODE_ROOT`）への書き込み・コミットをしない。runner はレビューと同じ checkout 監査を行うため、実行中の書き込み（untracked ファイルを含む）は `outside_changes` の拒否（`rejected`）になる。これは項目 2 の起動前の「未 commit の変更を残さない」に加えて、実行中の条件である。次の依頼の準備・ledger への記録は `SESSION` / `IMPLEMENT_SESSION` の下で行い、feature worktree への書き込み・コミットは依頼が終わって verdict の処理（`accept` を含む）が済んでから行う。

### 変更しないもの

- runner の監査実装（`tools/agent_runner/`）、helper（`review_spec.py`・`review_design.py`・`implement_task.py`）は変更しない。ガードは正しく機能している
- monitoring-long-tasks スキルは変更しない。並行作業の奨励自体は健全であり、issue-to-pr 側の対象 checkout 限定の制約で整合させる
- review-verify・review-fix-planning など他スキルの同型の罠は、本 Issue の編集範囲に含めない（Issue の受け入れ条件は issue-to-pr の 2 節に限定）
- SKILL.md の frontmatter・既存の段落の文言は変更しない（追加のみ）
- `rejected` の verdict 行など、`outside_changes` に既に言及している箇所は変更しない

## 決定記録

### D1: レビュー側のガイダンスの置き場所と範囲

- 選択した案: 「Spec・設計レビュー」節の依頼 JSON の段落・JSON 例の直後に、実行中の書き込み禁止・`SESSION` での準備・受け取り後のコミットを 1 段落で明示する（追加 A）
- 検討した別案: (a) 「採否を記録する」段落に追記する（受け取り直前の注意になり、実行中の待機行動に届かない）、(b) 設計レビュー・Spec レビュー・再レビューの各手順に個別に追記する（3 箇所の重複になり、再レビューの記述は `decide` の段落に埋もれている）、(c) 節の冒頭に箇条書きで置く（依頼 JSON の HEAD 照合との関係が分かりにくい）
- 選択理由: 開始時 HEAD 照合（既存の冒頭側）と実行中禁止（追加）が読み順でつながり、節全体に 1 回書くだけで 3 種類のレビューすべてを覆える。Issue の「同型の罠はすべてで起きる」への対応として重複がない
- 委任指示または停止条件: 推奨案で決める委任の範囲。文面が監査仕様（interfaces.rst「期限と保持」）と矛盾する場合は停止する

### D2: 実装 Task 側のガイダンスの置き場所

- 選択した案: 項目 3（依頼・待機）の段落に追記し、項目 2 の「未 commit の変更を残さない」との関係（起動前の条件＋実行中の条件）を明示する（追加 B）
- 検討した別案: (a) 項目 2 の `revision` の bullet に追記する（起動前の準備の話に実行中の禁止が混ざる）、(b) verdict 表の `rejected` 行に追記する（失敗後の対処であり、予防のガイダンスにならない）、(c) 節の冒頭に置く（待機の指示から離れる）
- 選択理由: 「終わるまで待つ」の直後が待機中の行動を定める自然な位置であり、Issue の「該当作業の節に明示」「既存記述と整合」を満たす。書き込み再開の時点は `accept` を含む verdict 処理の完了後とし、項目 4 の「取り込んだ後」のテスト実行と矛盾しない
- 委任指示または停止条件: 推奨案で決める委任の範囲

### D3: 編集範囲

- 選択した案: `.agents/skills/issue-to-pr/SKILL.md` への 2 段落の追加のみ。監査実装・他スキル・frontmatter は変更しない
- 検討した別案: monitoring-long-tasks 側に「runner 待機中は対象 checkout に書かない」を追記する、review-verify・review-fix-planning にも同じ注意を足す
- 選択理由: Issue の受け入れ条件と「この Issue を起票しただけでは編集範囲を広げない」の所有の記録に従う。他スキルへの展開は別 Issue のテーマ
- 委任指示または停止条件: 編集範囲を広げる必要が生じたら停止して確認する

### D4: テストと検証

- 選択した案: テストは追加しない（F: SKILL.md 本文の固定文言）。検証は `bash scripts/check-layout.sh`（symlink・配置の検査）、`uv run pytest`（既存テストの回帰。frontmatter・パッケージ構造の検査が SKILL.md を読む）、追加文面と受け入れ条件の照合（`git diff` の確認）
- 検討した別案: 追加文面の存在を固定値で照合するテストを書く
- 選択理由: AGENTS.md の採用基準で F（文書の文言の照合）は書かない。F∩S に当たる損害（権限・削除範囲などの固定値）をこの追加は守らない。既存テストの回帰で構造の破壊を検出できる
- 委任指示または停止条件: Issue の「検証は check-layout.sh と文面の照合で代える」に従う。pytest は既存検査の回帰として追加で実行する

### D5: 実行方式

- 選択した案: `self`（このセッション）が `superpowers:executing-plans` で実装する
- 検討した別案: runner の担当に依頼する（`--implement` 指定なし・雛形の既定は `self`）、サブエージェント委譲（SDD）
- 選択理由: 同一ファイルへの 2 箇所の追加という 1 Task の逐次変更であり、executing-plans の条件（同じファイルの逐次変更、1–2 Task）に当たる
- 委任指示または停止条件: 2 章の 3 の `implement_task.py check` の結果（`self: true`）に従う

### D6: 所有・競合の調整

- 選択した案: 続行する。#378（同じ SKILL.md の 2 章 6・5 章を編集）は PR #421 でマージ済みであり、本 Issue の編集箇所（4 章の 2 節）とは重ならない。coordinator のコメント（2026-11-12）の「重ならない場合は並列可」を満たす
- 検討した別案: #378 の完了を待って停止する
- 選択理由: #378 は既にマージ済みで、base（`main` @ `bce027ba`）に統合済み。open PR・claim ref・issue-417 の branch/worktree は存在しないことを確認した
- 委任指示または停止条件: 新しい競合・close を検出したら停止する

### Spec レビュー記録（1 回目）

- helper: `review_spec.py`（external runner）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-417.usgohlf8/2026-11-13-issue-417-review-runner-write-guard-design.spec-review/review-1`
- `review_id`: `1e4055a4cd6a4aadac94f00b7a040bc8`。reviewed の SHA（`spec_sha256`）: `5f28bee0d450ffd05b696cafaf56818c91b2f08be8d6f6ab2b913a05dbba5d99`
- 担当: `devin_swe2_max`（明示指定）。`requested_agent`: `devin_swe2_max`、`actual_agent`: `devin_swe2_max`、`identity`: model `SWE-2 Max`・CLI `3000.12.43`・session `stupendous-dresser`。fallback の使用: なし
- 回数: 1 回目。`elapsed_seconds`: 262.45。`outside_changes`: なし。`unprotected_changes`: `/tmp/pr-review-376-2f0d17b0/worktree`・`/tmp/pr-review-376-79fe98e5/worktree`・`/tmp/pr-review-376-7f95b4e6/worktree`・`/tmp/pr-review-376-c9a6d3e9/worktree`・`/tmp/review-fix-planning.9AkFc2/worktree`・`/tmp/review-fix-planning.a6ogtH/worktree`（他セッションの使い捨て worktree の観測。報告のみで失敗の理由にしない）
- 採否: S1（minor・追加 A の監査比較時点の表現）を採用し、追加 A の文面を「実行の開始前に登録されていた checkout の…を終了後の状態と比較する」に修正した（監査仕様 interfaces.rst「期限と保持」と一致）。禁止ルール自体の変更はない

## レビュー修正（サイクル 1・PR #422）

- 実行許可: issue-to-pr の `--merge` 委任（PR 修正ループ）と review-fix-planning の完遂（承認済み実装修正・結論 2 のマージ／関連 Issue 更新の実行許可を含む）
- planner: qwen4-max-preview（claude-code・self）。サイクル: 1。現行 HEAD: `cc70fd576a9e143da774d7f1c4adb9e5c44240a9`
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#422-fix-issue-417-runner-write-guard`
- 確認済みの一覧: `verified/cc70fd576a9e.json`（review-verify mode cycle・self・V-1/V-2 とも confirmed）

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| SWE-2-Max.md | SWE-2 Max | devin | cc70fd576a9e | はい（Initial） | Approve |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash | pi | cc70fd576a9e | はい（Initial） | Approve |

入力から外したファイル: なし（findings/・verified/・runs/ はレビュアーではない）

### 分類（全 2 件）

| 区分 | 件数 | 内訳 |
| --- | --- | --- |
| 解消済み | 0 | — |
| 対応する | 1 | V-1（deepseek-v4.1-flash#L-1） |
| 対応しない | 1 | V-2（deepseek-v4.1-flash#I-1） |

- V-1（対応する）: 追加 A が書き込み禁止の終了条件を「`submit` 成功」と書いているが、`submit` は self 専用（`review_spec.py:868` が mode != self を拒否。`review_design.py` も同じ submit に委譲）。外部レビューは `review` の完了（review.json・state completed）で結果を受け取る。致命的である理由: 外部 Spec レビューは本 Issue が保護する主要な有料経路であり、文面をそのまま辿ると存在しない `submit` の成功を待つか、submit を呼んで exit 2 拒否→スキル停止規則で停止し、完了した有料レビューの再実行（まさに本 Issue の損失）を招く。(b) 事実誤認の記述でそのとおりに進めると誤った結果（実在する構成: `--spec-review` の外部担当）。実行再現: 実外部レビューディレクトリへの submit が exit 2・review.json 不変
- V-2（対応しない）: Spec・Plan の冒頭の管理情報不足（README「状態」節の規約）。事実として正しいが、記録の書き方の完全性であり致命的ではない（誤った結果・データ消失・停止を生まない）。見直す条件: 利用者が header 規約の整備を依頼したとき、または文書管理のツールが状態を必須にする変更が入ったとき

### 要件対応（既存 Spec・Plan と今回の修正）

| 条件 | 今回の修正方針 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 受け入れ条件 1（レビュー側の禁止・準備・受け取り後コミット） | 終了条件の括弧を「外部は `review` の完了、`self` は `submit` 成功」に直す（禁止の意味は保つ） | SKILL.md:403 の文面が両モードの受け取り経路と一致 | review_spec.py / review_design.py の submit 制限との照合・diff |
| 受け入れ条件 2（実装側） | 変更なし（追加 B は verdict 処理基准で正しい） | 追加 B に submit への参照なし | diff・grep |
| 受け入れ条件 3（テスト不要・検証で代える） | 変更なし | テスト追加なし | check-layout・run-tests・pytest |
| 受け入れ条件 4（編集対象の限定） | 修正は SKILL.md と Spec・Plan の写しのみに限定 | 変更ファイルが既存の 3 ファイルのみ | git diff --stat |

共有条件: 「結果の受け取り時点」の語義（外部=review 完了、self=submit 成功）は SKILL.md・Spec・Plan の 4 箇所で共有する。統合担当は planner（self）が経路表の全行を修正後の HEAD で照合する。

### 守る条件と影響経路（V-1）

守る条件: runner 実行中の書き込み禁止の終了時点が、実際の結果受け取り経路（外部は review 完了、self は submit 成功）と一致し、controller が受け取り後に書き込みを再開できること。
破れた前提: 追加 A が終了条件を self 専用の `submit` 成功だけに結び付け、外部レビューの受け取り経路（review 完了）を落とた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 終了条件が外部の受け取り経路と一致 | SKILL.md:403（追加 A） | 修正する | 括弧が「外部は review の完了、self は submit 成功」 | diff・submit 制限との照合 | 97ddedfa で修正済み。fix-check が fake 実行 4 ケースで external/design の submit 拒否・self の記録を確認 |
| 同上（写しの一致） | Spec:49（追加 A 引用） | 修正する | SKILL.md と同じ文面 | diff | 作業ツリーで更新済み（本 Spec commit で committed tree に反映）。push 前に committed tree の一致を確認し状況コメント・ledger に記録 |
| 同上（写しの一致） | Plan:56（Step 1 引用） | 修正する | SKILL.md と同じ文面 | diff | 97ddedfa で修正済み。SKILL.md 段落と完全一致を照合 |
| 同上（照合基準の一致） | Plan:30（Review Focus 5） | 修正する | 「レビューは結果の受け取り（外部は review の完了、self は submit 成功）後」 | diff | 97ddedfa で修正済み |
| 終了条件が self の受け取り経路と一致 | SKILL.md:434（既存の self/external 区別） | 既に満たす | 「state: completed なら外部担当のレビューが完了している」の既存記述 | git show で確認 | cc70fd57 の SKILL.md:434 で確認済み |
| 実装側の終了条件 | SKILL.md:494（追加 B） | 既に満たす | verdict 処理（accept を含む）完了後。submit への参照なし | grep | cc70fd57 で submit 参照なしを確認済み |
| 他スキルへの波及 | review-verify・review-fix-planning・pr-review-fix-loop | 対象外 | 「submit 成功」の文面なし | git grep | Issue の編集範囲外・該当文面なし（確認済み） |

きっかけ（同じ条件の 2 回目／修正が生んだ回帰／自己レビューでの再発）: いずれも該当なし。S1（Spec レビュー）は監査比較時点の表現で終了条件とは別の条件。submit 文面は S1 修正前の初版から存在。点の修正で直す。

### 修正方針

追加 A の終了条件の括弧を「（`submit` 成功）」から「（外部は `review` の完了、`self` は `submit` 成功）」に直す。SKILL.md・Spec 引用・Plan 引用・Plan Review Focus 5 の 4 箇所を同じ表現にそろえる。禁止の区間（review 起動から受け取りまで）・準備の置き場所（SESSION）・受け取り後のコミットの意味は保つ。テストは追加しない（F。文面の修正）。

検証: `bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run pytest tests/skills .agents/skills`（スキル変更の検証入口）。加えて submit 制限との語義照合と 4 箇所の文面一致を diff で確認する。

### 実行した検証（修正 commit 97ddedfa・feature worktree）

- `bash .devcontainer/run-tests.bash`: exit 0・PASS: 27 test(s)
- `bash scripts/check-layout.sh`: exit 0・PASS: check-layout
- `uv run pytest tests/skills .agents/skills`: exit 0・832 passed in 688.97s
- 文面照合: SKILL.md:403・Plan:56 引用の段落完全一致、Plan:30 更新、旧文面の残存なし（作業ツリー。Spec 引用は本 Spec commit で反映）
- `scan-before-push.sh`: exit 0・no leaks（5 commits・push はまだ）
- fix-check の隔離 worktree 再実行: run-tests PASS 27 / check-layout PASS / pytest subset 832 passed（638.77s）/ scan no leaks — すべて exit 0

### 修正後の自己レビュー（1 回・run_roles.py --phase self-review）

- 呼び出し 1 回（枠予約済み・2 回目はしない）。役割はどちらも self（司令塔がサブエージェントに並行委譲・各 1 回）
- self-review: qwen4-max-preview（claude-code）・525.4 秒・PR 全体（bce027ba..97ddedfa）を再レビュー・Approve・active 1 件（M-1 Medium: committed HEAD の Spec:49 引用が旧文面）。保存: `qwen4-max-preview-commit-97ddedfa3a0c6fdf9e0db837b767a382e5666400.md`
- fix-check: qwen4-max-preview（claude-code）・1301 秒（待ち 172 秒）・confirmed 1 件（V-1 = M-1 と同一問題）・claims 12 holds / 3 violates（C-2・C-8・C-14・コミット済み内容と Fix 節主張の照合）・文書候補 16 件判定済み・検証再実行全合格。保存: `verified/97ddedfa3a0c.fix-check.json`（caller が実観測識別情報を付与・validate 済み）
- 判定: M-1 と fix-check#V-1 は同一問題に統合（sources に両参照）。**対応しない**（非致命）。理由: Spec は設計文書であり運用ガイダンス（SKILL.md）は reviewed HEAD で正しい。Spec の引用更新と本節は作業ツリーに反映済みで、review-fix-planning の設計上 Spec は自己レビュー後・push 前に 1 回だけ commit するため、self-review がレビューした committed fix HEAD に Spec commit が含まれないのは設計どおり。写しの不一致はツール利用の誤った結果・停止を生まない。見直す条件: push 後の tree に引用の不一致が残ったとき、または Spec commit を省略したとき
- 致命的な指摘なし → 修正パスなし。自己レビュー後の修正は再レビューしていない（本節と状況コメントに記録）
- push 前の揃え確認: Spec commit 後に committed tree で 4 箇所の文面一致・旧文面残存なしを確認し、結果を状況コメントと ledger に記録する

## レビュー修正（サイクル 2・PR #422）

- 現行 HEAD: `c38785a73fc215c6ed8a28999480654058f6ca02`（サイクル 1 の修正 97ddedfa＋Spec commit）。planner: qwen4-max-preview（claude-code・self）
- レビュアーの構成: SWE-2-Max.md（SWE-2 Max・devin・226.5 秒・Update・Approve・Info 1）/ deepseek-v4.1-flash.md（deepseek-v4.1-flash・pi・888.3 秒・Update・Approve・Info 3）。両者とも現行 HEAD を再実行（rerun）
- サイクル 1 の fix（L-1）: 両レビュアーが現行 HEAD で解消を確認（4 箇所の文面が実装と一致）。判断は `resolved` に変更
- 分類: 解消済み 1（L-1）/ 対応する 0 / 対応しない 4
  - `SWE-2-Max#I-1@c38785a73fc2` と `deepseek-v4.1-flash#I-4@c38785a73fc2`（統合）: Spec:149「基准」・Spec:158「落とた」の誤字。表記の揺れであり致命的ではない（ツールの誤った結果・データ消失・停止を生まない）
  - `deepseek-v4.1-flash#I-2@c38785a73fc2`: サイクル 1 の分類表がレビュアー 2 件の指摘のみを数え、自己レビューの M-1（対応しない）を表外の段落で扱っている。記録の書き方・集計範囲の表記であり、M-1 の判断は判断の記録と本文書 192 行目に記録済みで失われていない。致命的ではない
  - `deepseek-v4.1-flash#I-3@c38785a73fc2`: Plan Task 1 Step 3 の Expected「diff は追加行のみ」が、項目 3 行末への追記（1 行の変更）と一致しない。Task 1 実行時に ledger で裁定済み（Ruling: 既存文の先頭一致を確認・追記 329 文字）。歴史的文書の期待値の表記であり、executing-plans の裁定機構が扱う。致命的ではない
  - 見直す条件（共通）: 利用者が表記・記録の整備を依頼したとき
- 結論: 2（修正不要）。対応する 0 件・全指摘と変更ファイル全文・関連処理の確認済み
- 検証（現行 HEAD・clean tree・feature worktree）: run-tests.bash PASS 27（exit 0）/ check-layout PASS（exit 0）/ uv run pytest tests/skills .agents/skills 832 passed in 614.51s（exit 0）。ログ: tmp/agents/review-fix-planning-pr422.3571315y/{run-tests-c2,check-layout-c2,pytest-subset-c2}.log
- base: `bce027ba003a4090fee3f4a2e9c85a6383009e51`（取り直し・head の祖先）
- 自己レビュー: 未実施（修正がないため）

## 編集禁止

- `.agents/skills/issue-to-pr/SKILL.md` の frontmatter・既存段落の文言（追加のみ行う）
- `tools/agent_runner/`・`.agents/skills/issue-to-pr/scripts/` の実装
- monitoring-long-tasks・review-verify・review-fix-planning・pr-review-fix-loop の各スキル
- ワールドのプロジェクト（`worlds/` と従来位置）

## 検証計画

1. `bash scripts/check-layout.sh`（worktree で実行。symlink・配置の検査）
2. `uv run pytest`（worktree で実行。既存テストの回帰。ベースラインは変更前に同一 worktree で実行して比較する）
3. `git diff` で追加文面を確認し、受け入れ条件 1・2 の各要素（実行中の書き込み・コミット禁止／`SESSION` での準備／受け取り後のコミット／「未 commit の変更を残さない」との整合）と照合する
4. テストは追加しない（D4）

## 証拠・参照

- Issue #417 本文の「手元の証拠」: `/workspaces/reso-world/tmp/agents/issue-382.mbplkg1i/2026-11-12-issue-382-claude-bash-timeout-cap-design.spec-review/review-1/review.json`（state failed・reasons outside_changes・batch は success）、同 `review-2/review.json`（再実行・completed・514.70 秒）
- 監査仕様: `tools/agent_runner/interfaces.rst`「期限と保持」（監査の比較対象・保護範囲・outside_changes / unprotected_changes の扱い）
- coordinator の所有調整コメント: Issue #417 の 2026-11-12T06:55:32Z のコメント（#378 との並列条件）