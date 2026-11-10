# Issue #359: 定期掃除の導入先から helper を解決する

## 管理・実行許可

- 状態: `completed`。実装・レビュー指摘の採否・必要な検証を完了した記録であり、設計承認を得たという記録ではない。実環境の rebuild 後確認は引き続き未実施。
- Issue: https://github.com/usaturn/create-reso-world/issues/359
- 利用者の明示入口: `issue-to-pr`、`#359 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。
- 通常の設計判断・検証・commit・push・PR・指定ループ内の finalize によるマージまで実行する指示。利用者は「途中で main が進んでいる場合は留意して止めずに進めてください」と明示し、停止後にもこの指示を再確認した。前回 controller がスキルの一般的な停止条件をこの具体指示より優先したのは誤判断だった。旧・新 SHA を記録し、新 base と PR head を組み合わせたツリーを再検証して継続する。検証前の成功の流用や、無検証で checks の base だけを差し替えることは許可しない。
- 対象と文書: `usaturn/create-reso-world`、origin、`refs/heads/main`、捕捉 SHA `1b0df1212e47857e131d6936e0510520e4fb13ef`。親 checkout は編集せず、`fix/issue-359-cleanup-symlink` の worktree で作業する。

## 目的・現状

`install_beforehand.bash` は cleanup-workspace を ~/bin にコピーする。cleanup の helper 探索は `readlink -f` したスクリプト実体が `.devcontainer/` にある場合だけ repository 相対パスを使うため、コピーからの定期実行は全セッションを保持してしまう。

導入先をスクリプト実体への絶対 symlink に変更し、既存コピーも置換する。定期実行が、保存済みセッションだけを helper の `reap-check` → `cleanup --strict-reap` 経由で退役させられるようにする。cleanup 本体は git モード 100755 のため、リンク先の chmod は不要である。

## 確定した所有・除外

裁定: https://github.com/usaturn/create-reso-world/issues/359#issuecomment-6764063174 。#349 の「ボード外の follow-up と所有」にも同じ範囲がある。#359 に native parent はなく、blocked_by は空。#351 の PR #358 は main にマージ済み。

- コード変更は `.devcontainer/install_beforehand.bash` の cleanup 配置と `.devcontainer/test-install-beforehand.bash` だけ。
- 他の Herdr helper の配置は変更しない。
- `.devcontainer/zshrc.txt`、cleanup 本体の helper 探索規則、`.devcontainer/test-cleanup-workspace.bash` の既存ケースは変更しない。
- cwd・HOME・掃除対象データから helper を推測しない。実 PR、実セッション、実 HOME の掃除・再導入はしない。
- #347 と `run-tests.bash` を同時実行しない。実行直前に既知の実行を確認する。
- rebuild・実環境の定期起動は自動実行しない。マージ後の利用者確認として残し、PR は `Refs #359` にする。

## 設計と決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 / 委任・停止条件 |
| --- | --- | --- | --- |
| helper 解決の復旧 | cleanup だけを絶対 symlink にする | zshrc で helper env を設定 | Issue の明示裁定。#347 と所有が分離し、既存の実体解決を再利用できる |
| 既存コピー | symlink 作成時に置換する | コピーを残す / 再コピー | 現行の安全側コピーからも移行可能にする。ディレクトリにリンクを作る誤操作は避け、失敗を既存の return 1 で伝える |
| テスト | 配置関数を抽出し偽 HOME で実行、実 helper をローカル fixture に使う | 本番 postCreate / 実 PR / symlink 有無だけの照合 | 破壊操作を避け、実際の探索・退役と保持まで観測する。既知の気付きにくい不具合の再発防止は S |
| helper 不在 | 現行の保持動作を維持 | 探索先を増やす | 不明なコードの無人実行と未保存データの削除を避ける。不在の負例は既存 cleanup テストで代表させ重複させない |
| 実装方式 | runner 担当で 1 Task を順次実装、SDD の Task / 全体レビュー | self で実装 | `implement_task.py check` は self=false、一次担当は利用者指定の `pi_opencode-go_deepseek4-flash_max`、fallback は空。失敗時に self へ切り替えない |
| PR 修正ループ | 指定 implement と inspect 3 担当 | 既定レビュアー | 利用者指定。inspect は claude-code_opus_default / devin_swe2_max / pi_opencode-go_deepseek4-flash_max。max_cycles=3 は既定適用。fix の self-review / fix-check は既定の self、fallback は空 |

## 受け入れ基準

- **動作環境:** Ubuntu Dev Container、Bash・GNU coreutils・git・uv。リポジトリの絶対パスには空白を含めてもよい。検証は一意の一時 HOME / git repo / TMP_ROOT の中だけで行う。
- **実入力:** 偽 HOME の `bin/cleanup-workspace.bash` に旧コピーを置き、実際の配置関数で置換後、その導入先を直接実行する。実 helper が作成した保存済み review（複数行・日本語を含む本文）と未保存 draft を使い、helper env の明示なしで保存済みだけが退役し、未保存本文と保存先の review は残ること、git worktree 登録も退役分だけ外れることを観測する。再配置・再実行も成立する。
- **防御範囲:** helper が見つからない場合は削除せず理由を報告する（既存 cleanup テスト）。実 HOME・実 PR・既存の /tmp セッションには触れない。postCreate 全体の実行、他 helper の配置変更、壊れたスクリプト symlink 自体の実行成功は保証対象外である。

## 検証・公開

配置と cleanup の既存テストをまず実行し、変更前は 2 本とも成功（baseline.log）。新しい導入経路の動作検証を変更前に失敗させ、変更後に成功させる。静的確認は bash -n、差分・編集範囲・chmod の副作用の確認。README の入口で全 shell テスト、check-layout、スキル・tools の pytest を実行する。実環境の rebuild 後確認は別に残す。

Spec → Plan の Task 1 → 実行証拠を条件単位で対応させ、PR 前に統合担当が探索・保存・退役・保持の順序と証拠を照合する。PR 前に全体レビュー、Gitleaks、base / Issue / 競合を再確認する。base の SHA を無検証で差し替えない。

## PR #381 のレビュー判断（判断記録サイクル 2）

- planner: `openai-codex/gpt-6.1-sol`（pi、実行環境から取得）。既存のこの Spec を更新し、回ごとの新規文書は作らない。
- 実行許可: 元の issue-to-pr 指示と、main が進んでも留意して継続する具体指示の再確認。前回停止の記録（判断サイクル 1）は履歴として残す。
- 新 loop run: `6ee28b5e6f974c35862e297748239361`。loop 内のサイクル 1 は同じ head の成果を `reuse` と判定した。判断記録のサイクル番号は前回に続けて 2。

| レビューファイル | モデル / runtime | 対象 HEAD | 今回の扱い |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `6fc8ae64340d` | 同一 HEAD の成果を helper 判定で再利用。原文 recommendation は Approve に理由を添えた文 |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash / pi | `6fc8ae64340d` | 同上 |
| 成果なし | devin_swe2_max / モデル未確認 | 前回起動は同じ head | 前 run で rate_limit / response_failed / exit 1、停止確認済み。成功成果・指摘なしとは扱わず、今回の計画入力にも含めない |

### 全指摘と採否

| 出典 | 確認結果 | 区分と根拠 |
| --- | --- | --- |
| `claude-opus-5-5#I-1@6fc8ae64340d`、`deepseek-v4.1-flash#I-1@6fc8ae64340d` | 同じ文書の性質 1 件に統合。`.agents/skills/pr-review/references/noninteractive.md:63` と `docs/maatlog-poc-porting.md:120` に旧コピー方式の説明が残ることを committed blob と現行配置・探索コードで確認 | 対応しない。説明の追随漏れは事実だが、手動の誤操作を指示する記述ではなく、実際の退役は helper が保存済みと確認したものだけを対象にするため、主要処理の停止・誤った対象操作・データ損失・秘密露出につながる経路はない。致命的でない文書追記は review-fix-planning の既定で採用しない。名称を挙げた修正依頼もない。安全な退役条件や操作手順を誤らせる具体的な利用経路が示された場合に見直す |

解消済み 0 / 対応する 0 / 対応しない 1（元の指摘 2 出典）。前回 `unverified` の判断を、現行版の静的照合後に `skip` へ変更した。Info という重大度や賛成の数で採否を決めたわけではない。

### 要件・証拠の照合

統合担当は controller。配置関数 → 導入先の実体 → helper 解決 → 保存済み退役 / 未保存保持の共有条件は同じ Task の実 helper テストで確認する。新 main による変更は runner の起動設定と共通指示で、cleanup の信頼境界や保存/退役処理は変更していないが、組み合わせたツリーでも関連テストを含む全 shell 検証を再実行した。

| 条件 | 今回の扱い | 観測結果・証拠 |
| --- | --- | --- |
| 旧コピー置換・再配置・helper 解決 | 既に満たす | 結合ツリーの `test-install-beforehand.bash` を含む全 shell 27 本が成功。保存済みだけ退役し、未保存 draft / 登録・保存本文を保持する assertion が成功 |
| helper 不在の保持 | 既に満たす | 同じ全 shell 実行の既存 `test-cleanup-workspace.bash` が成功 |
| main 前進との統合 | 新しい先端ごとに検証 | 下記 2 回の結合ツリーで検証。変更のない head の旧検証を新 base の成功へ読み替えていない |
| 文書の旧説明 | 対応しない | 上の採否根拠と PR の既知の制限で開示。追加コード・テストなし |
| 実環境 rebuild 後 | 対象外・利用者確認が残る | 未実施。実 HOME や実セッションに触れていない。PR は引き続き `Refs #359` |

### 実行した検証

元の PR head `6fc8ae64340d6e5e4ef2aaadd0cc464d0c1607e6` は変更していない。

1. base `5df1b0a0935067384b1ec59d9541b2785aa60a7e` を head に結合した一時 commit `bb0f363792c8eafde2c5506c60397b74f998b6cc` で、全 shell 27 本、layout、Claude Code adapter / parser の pytest 33 件がすべて exit 0。その後 main が再び進んだため、この結果ではマージせず次を実施した。
2. base `f20b7c275a5768714c959968987e23e861e34224` を head に結合した一時 commit `59c2016a126dff4eb1f566195f388763dd8a179c` で、`bash .devcontainer/run-tests.bash`（27 本）、`bash scripts/check-layout.sh`（PASS）、`uv run pytest tools/agent_runner/tests/test_runner.py tools/agent_runner/tests/adapters/claude_code tools/agent_runner/tests/adapters/test_parser_regressions.py`（82 passed）がすべて exit 0。実行前後 clean。

一時 worktree は検証後に登録から外して削除済みであり、結合 commit は push しない。元の base SHA と旧検証はそのまま保持した。

- 証拠・checks: `/workspaces/reso-world/tmp/agents/pr381-resume.6zovri_z/verification.json`、`checks.json`
- 実ログ: 同ディレクトリの `merge-shell-2.log` / `merge-layout-2.log` / `merge-runner-pytest-2.log`
- 確認済み一覧: `reviews/usaturn/create-reso-world/#381-fix-issue-359-cleanup-symlink/verified/6fc8ae64340d.json`。文書の静的 confirmed 1、未確認指摘 0。実環境 rebuild は別の coverage.remaining として明記。
- 工程の記録: 同じ `verified/6fc8ae64340d.planning.json` に、状況投稿後に実施した工程と時間だけを保存する。
- 結論: 2（追加修正不要）。修正をしないため `run_roles.py` の implement / self-review / fix-check は未実施、自己レビュー枠の使用は 0 回。既存の実装 Task / branch review と指定レビュアーの成果を自己レビューの実行として数えない。
- マージ前の最終化だけをこれから行う。push・マージ・Issue 更新の結果はこの Spec に先取りして書かず、PR 状況コメントと完了報告に記録する。
