# Issue #36: 固定値テストの見直し

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: #36
- 状態: draft
- 基準 HEAD: `ee1421ae3efb274cb5e28c8f3a810fe24ac5a3a6`（#41・#43 のマージ後）
- 関連 Plan: `docs/superpowers/plans/2026-10-06-issue-36-fixed-value-tests.md`
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-36-fixed-value-tests`
- PARENT_ROOT: `/workspaces/reso-world`

## 1. 目的と実行許可

文書の言い換え・節の追加・モデル設定の更新によって、実際の不具合がないのに失敗する検査を減らす。一方、誤った checkout の操作、秘密情報の混入、設定の配置漏れ、壊れた参照、実行手順の不具合を検出する検査は残す。

利用者はこのセッションで「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」と明示した。これは推奨案の選択、文書作成、実装、検証、作業ブランチへの push、PR 作成の実行許可である。未作成の文書を利用者が読んで承認したとは扱わない。Spec・Plan は draft としてまずコミットし、その内容のコミット SHA と実行許可を記録して進める。マージは許可に含まれない。

## 2. 判断基準と比較案

推奨は「変更される設定・文章」と「検出したい誤り」を分けて判断する案である。

| 案 | 利点 | 欠点 | 判断 |
| --- | --- | --- | --- |
| 文書・モデル名の固定を全廃 | 最も少ない保守負担 | 利用者所有のペルソナ、移植元混入、安全上の一覧まで守れなくなる | 不採用 |
| 固定値をすべて定義元参照に置換 | 設定更新が一か所になる | 文面の定義元を増やすだけでは実際の不具合を検出せず、検査自身と同じ値を比べる危険もある | 設定の配置・起動に限って採用 |
| 文面を削除、参照と挙動を維持、保護境界は例外として説明 | 不要な制約を減らし、検査の目的を維持できる | 文書の意味の妥当性はレビュー・eval で確認する必要がある | 推奨・採用 |

「変わり得る値」は、文書のタイトル・見出し・節の順番・説明文、モデル名・thinking、現行設定のコピーである。テストが自分で用意する入力、公開済みの履歴の SHA、API・スキーマのキー、安全な操作範囲、認証の隔離、ファイル種別・権限などの仕様は同じ群にしない。

静的な文章の一致は意味を検証できない。削除した語句検査を、別の同義語一覧、別ファイルに移した語句、件数の固定、弱い恒真の検査で置き換えない。本文から抜き出した bash/zsh を実行する検査は、抽出に見出し名を使っている場合でも文面検査と区別して残す。

## 3. 候補 A〜C の扱い

表の各行が採用判断である。混在するファイルでは、行で指した検査のみ変更する。

| ID | 候補 | 扱い・推奨 | 理由と残すもの |
| --- | --- | --- | --- |
| A1 | `tests/scripts/test-docs.bash` の README 見出し一覧・タイトル | 削除する | 文書構成は API ではない。節を増減・改称しても検査は失敗させない |
| A2 | `tests/scripts/test-instructions.bash` のペルソナ SHA | 固定値のまま残す | 利用者所有部分の意図しない変更を検出する保護境界。値を現行文書から自動生成すると書換え検出が消える。利用者が意図して変更した場合だけハッシュ更新を別変更として確認する |
| A3 | `tests/scripts/test-instructions.bash` の文言・見出し・タイトルの `has`、文で位置を切り出す検査 | 削除する | 言い換えを拒否するだけの検査。`CLAUDE.md` 冒頭の `@AGENTS.md` は実際の読み込み指定なので残す。参照するリポジトリ内ファイル・スキルは、その記載を列挙し直さず実在を確認する |
| A4 | `tests/scripts/test-docs.bash` の README・現行運用文書の `has` / 文言の `lacks` | 文面検査を削除し、参照先の実在を見る | 本文の案内・節の表示名は固定しない。リポジトリ内 Markdown リンクやバッククォートで示した実ファイル参照のうち検査対象とするパスを解決し、存在を検査する。コマンド引数・サンプルパス・glob・外部パスは対象外。過去 Spec/Plan の固定履歴と #41 対象のロック関連検査は変更しない |
| A5 | `.devcontainer/test-readme.bash` の導入ツール行の固定一覧と説明文の `has` / 文言の `lacks` | 文面検査を削除する | mounts・initialize・zshrc・update の表と実装の比較は残す。表の HTML マーカーは解析インターフェースであり維持する |
| A6 | 上記 3 ファイルの移植元名・撤去ツール・無効設定・旧 API・秘密情報に関する `lacks` | 固定値のまま残す | 名前の混入や危険な案内の復活は具体的な誤り。純粋な文章の禁止とは区別する。ペルソナ部分には新しい文言検査を追加しない |
| B1 | `.devcontainer/test-pi-superagents.bash` の tier モデル名と thinking 一覧 | 削除し、既存の設定配置比較・構造検査を使う | `.devcontainer/pi-superagents/*.json` が定義元。既存の配置・収束テストは配置先と定義元を比較している。モデルの存在・provider の制約・部分 config の構造検査は残す |
| B2 | `.devcontainer/test-pi-openai-codex.bash` の tier モデル名と thinking | 定義元の JSON と配置先を比較する | モデル名・thinking をテストへ写さず、配置が定義元と一致することを検査する。親ランチャーのモデル・thinking は tier と必ずしも同じでないため、ランチャーの実際の呼出し定義を独立に読み、実行した argv と比較する。実行結果自身を期待値にしない |
| B3 | `.devcontainer/test-herdr-migration.bash` の `ccdo`・`ccds` モデル指定 | alias の定義と実行 argv を比較する | `zshrc.txt` の alias を独立に読み、引数転送（空文字・空白・改行・glob・利用者の後続 `--model`）を検証する。実行 probe に使う `sonnet` はテスト入力なので維持してよい。ほかの provider 関数の認証・role 対応の検査はこの変更で拡張しない |
| C1 | `.devcontainer/test-initialize-mounts.bash` の mount 一覧 | 固定値のまま残す | mount の増減はホストの永続領域と秘密情報の露出に関わる仕様変更。相互比較だけだと initialize と mount を同時に誤変更しても検出できない。実行・冪等性・権限・不整合の検査も維持 |
| C2 | `.devcontainer/test-herdr-migration.bash` の unset 環境変数一覧 | 固定値のまま残す | provider 切替時の認証漏れ・親の設定混入を防ぐ。実装のリストをそのまま期待値にしない |
| C3 | `tests/scripts/test-gitignore.bash` の tracked-but-ignored 例外 | 固定値のまま残す | 許可した例外以外の誤追跡を検出するための許可リスト。実データの自己比較にはしない |

A3・A4 の参照検査は既存テストファイル内に小さく置く。汎用 Markdown パーサ、文面ルールエンジン、本文の新しいマーカーは作らない。参照の検査が不要な文面削除だけの箇所は新しいテストを作らない。

## 4. 候補 D の扱い（ファイル単位の全件）

共通: スキルの節・手順名、説明文の一致は削除する。frontmatter の構造、CLI の権限指定、実ファイル・リンク・symlink、スキーマのキー、fixture の存在、実行可能な手順の検査は残す。混在する関数は残す目的だけへ縮める。固定見出しで切り出すことが不必要ならリンク・構造・コマンドマーカーから探す。

| 候補 | 扱い・推奨 | 残す検査と理由 |
| --- | --- | --- |
| `tests/scripts/test_superpowers_lifecycle.py` | 現行指示・README・Spec/Plan の説明文一致を削除。混在は構造部分だけ残す | 履歴インポート SHA manifest とその portability、resolver/review-copy/handoff の実行、runner 配線、schema。凍結した履歴と現在の文面を区別する。continuation gates は機械キーで解析 |
| `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py` | スキルの節・文言の一致を削除。参照実在の部分だけ維持 | resolver の bash/zsh 実行、誤った親・コード checkout の停止、共有 helper/symlink、frontmatter・interpolation、review budget 参照の実在 |
| `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py` | 見出し・1〜7 手順名・最初の例の行・文章一致を削除。eval 5 の説明文字列一致を削除 | bash/zsh 共通 context と status 投稿の実行、helper・symlink、frontmatter、eval JSON の構造。eval は内容の文章固定でなく評価の入力資料 |
| `.agents/skills/agent-handoff/tests/test_agent_handoff_skill_contract.py` | 説明文・見出しの一致を削除。schema 検査は列とフィールドを使う | schema version/fields/nullability/enum、実在参照・eval JSON、frontmatter・symlink。機械フィールド名は仕様 |
| `.agents/skills/repo-cleanup-after-merge/tests/test_repo_cleanup_after_merge_contract.py` | 操作手順を文章で検査する部分を削除 | allowed-tools・リンク・fixture/eval 構造・symlink。eval の期待文を固定一覧で縛らない |
| `.agents/skills/simplify-in-subagent/tests/test_simplify_in_subagent_contract.py` | runtime note・routing・例の文言を削除 | interpolation/frontmatter/symlink の構造 |
| `.agents/skills/rst-writer/tests/test_rst_writer_contract.py` | profile の文面・手順・見出しの固定を削除 | profile/template/fixture の実在、リンク、eval 構造・symlink |
| `.agents/skills/planning-parallel-issues/tests/test_planning_parallel_issues_contract.py` | 文面・節の固定を削除 | 手順・スキル参照の実在、実在する検証コマンドの参照、eval/validation 構造・symlink |
| `.agents/skills/monitoring-long-tasks/tests/test_monitoring_long_tasks_skill_contract.py` | controller/deadline/liveness の説明文を固定する部分を削除 | runtime skill の byte 一致、CLAUDE の読み込み指定、撤去済みパスの禁止。説明文の意味はレビュー・eval で評価する |
| `.agents/skills/pi-model-name/tests/test_pi_model_name_contract.py` | 説明文と本文内の絶対パスの一致を削除 | モデル名抽出スクリプトの全実行テスト・実行権限・frontmatter |
| `.agents/skills/stale-git-lock-recovery/tests/test_stale_git_lock_recovery_contract.py` | 安全規則の説明文一致だけ削除 | 回復スクリプトの全実行テスト、bash の危険コマンド禁止・zsh 特殊変数、frontmatter/symlink。#41 の ResoLoop lock ではなく git index.lock のため対象内 |
| `.agents/skills/find-docs/tests/test_find_docs_contract.py` | CLI・秘密情報の置き場所などの文章一致を削除 | 共通指示のツール固有パス禁止・symlink。参照を残す場合は実在を見る |
| `.agents/skills/herdr-agent-task/tests/test_herdr_agent_task_contract.py`（追加候補） | コマンド掲載文の一致を削除。状態表は見出しによらず読む | スクリプト実在、状態 enum と実装の比較、symlink |
| `tests/skills/test_skill_packages.py` | `COMMON_BOUNDARIES`・`REQUIRED_TERMS` の文面検査を削除。混在は構造だけ残す | frontmatter/packaging/link/provenance/license/layout、委譲境界の意味的 guard とその正負 fixture。具体的な危険な実行案内の guard は安全上の禁止として残す |

文面検査を削除するために `SKILL.md`、schema、eval JSON の本文は変えない。削除後に使われない定数・抽出 helper・imports はテストファイルから除く。実行テストは数を固定せず、削除前後のテスト名・差分で保存を確認する。

## 5. 今後のテストの基準

`AGENTS.md` の「基本方針」にある TDD 規則を補う。文書の構成・説明文・モデル名など変更される内容を写しただけのテストは作らない。検出したい不具合を説明できる場合だけ、実行結果、配置と定義元の比較、参照の実在を検査する。安全な操作範囲・schema・凍結した履歴・利用者所有部分の保護は、必要な固定値を理由付きで使ってよい。意味のないテストを追加しないという既存規則を維持する。これは TDD 以外にも適用する。

## 6. 範囲・検証・完了条件

編集対象は表で指定したテスト、Spec・Plan、AGENTS.md の基本方針だけ。SKILL.md・README.md・ペルソナ・ワールド・#41 のロック関連検査・過去 Spec/Plan は編集しない。

テストの整理なので検査を検査する固定値テストは作らない。必要な挙動検査の改善には、隔離コピーでの変異検証を先に使い、許容すべき変更が旧検査で失敗することと、改修後に成功することを確かめる。検出すべき不具合が改修後も失敗することを確認する。

- 正常: `uv run pytest tests/skills .agents/skills`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`。必要に応じルート `uv run pytest` も実行する。
- 許容変更: README/指示/スキルの見出し改称と節追加、モデル・thinking の更新、alias のモデル更新（隔離コピーのみ）。本文とテストを同時に期待値更新しない。
- 拒否: リポジトリ内参照のリンク切れ、移植元名の混入、ペルソナ書換え、配置済み config の不一致、認証隔離/危険操作 guard の退行。採用した変換の検出対象を代表ケースで検証する。
- 各タスクの fresh review と全差分レビュー、`git diff --check`、変更 Python の LSP probe（対応 server がなければその事実と pytest/compile の結果を記録）。

完了条件: A〜D の各行を実装差分または維持理由で照合し、検証成功・変異検証の根拠・作業時間を記録し、Spec・Plan を含む `Closes #36` の PR を main 向けに 1 本作る。予約 ref は自分の SHA を確認して条件付きで解放する。PR はマージしない。

## 7. 基準版の検証記録

2026-10-06 に基準 HEAD の worktree で実行した。

- pytest: 548 passed, 1 skipped（約101秒）
- シェル runner: PASS 28 tests（約120秒）
- layout: exit 0。導入済み ResoLoop の同梱スキルが新しいという既存警告はあり、同期更新は範囲外。
- D の読み取り専用調査: harness の所要時間は約316秒（子の自己申告の概算とは区別）。
