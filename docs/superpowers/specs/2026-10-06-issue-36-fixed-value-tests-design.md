# Issue #36: 固定値テストの見直し

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- 対象 Issue: #36、PR: #46（初回実装とレビュー選別の記録。公開後の結果は PR/Issue コメントを参照）
- 状態: completed
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

## 8. 完了記録（2026-10-06）

- 状態: 実装・検証・PR 作成完了。公開先: https://github.com/usaturn/create-reso-world/pull/46 （OPEN、main 向け、マージ未実施）。
- 初版の内容 SHA: `0601efbb985d21adc535b1b59e5f05654ae2d496`。この版以降の推奨方針の実行許可はセッション冒頭の利用者指示。利用者が文書を読んだ内容承認は記録しておらず、approved を経たとは扱わない。
- 検証したコード HEAD: `b084f43c753fff0bdc02f9962e534fab6ec65230`。以下の文書の状態・結果追記はコード変更ではない。
- 最終 controller 検証: root pytest **555 passed, 1 skipped**（133秒）、指定 skills pytest **487 passed, 1 skipped**（90秒）、shell runner **28 PASS**（129秒）、layout **PASS**（2秒）、Python 14 ファイル構文確認、diff check 成功。ログ: `/workspaces/reso-world/tmp/issue-36/final-b084f43/`。
- skip は既存の `SKILL_UNDER_TEST` 未指定による opt-in。機能実行テストの元の名前を AST で照合し、凍結 SHA manifest・ペルソナ保護・C の一覧を維持した。SKILL/README/ペルソナ/ワールド/過去文書は不変。
- 各 Task のレビューと修正差分の再レビュー、全差分レビューを実施。最後の残存指摘は、以下の裁定でレビュー済みの Git オブジェクトへ完全復元し、バイト一致と引用 shell payload の拒否を確認した。
- LSP の Optional Match 指摘2件は修正した。最終 active probe は診断0件だが push-only server のため clean を確定できない。compile・pytest を別の検証根拠とする。
- 隔離変異: Task1 正常/拒否47件と修正18件、Task2 設定/argv/認証の正常/拒否、Task3 の見出し/手順/期待文の言い換えと安全/schema/参照変異、最終修正54件、最後の `bash -c` 2件の拒否を確認。テスト期待値を変異に合わせて更新していない。

### A〜D の照合

| 方針 | 実装・維持の証拠 |
| --- | --- |
| A1/A3/A4/A5/A6 | `bb52cbe`・`5e708c0`。現行文面の固定を削除、説明文で参照を除外しない小さい実在検査へ変更。過去の記録は維持 |
| A2 | SHA と assertion は不変。隔離したペルソナ書換えは拒否 |
| B1/B2/B3 | `c72c352`・`fa97be5`。source JSON と配置先、source launcher/alias と実行 argv を独立比較。静的 argv accessor は既存テスト内の一か所へ集約 |
| C1/C2/C3 | ファイル/対象ブロック不変。mount/unset/ignore 許可リストは理由付きで維持 |
| D 全14行 | `1cbb20b`・`52dcb7a`・`884cf58`・`87ef030`・`b084f43`。説明文固定を除き、機能実行・構造・参照・安全検査を維持。eval 構造の重複は一つのパラメータ化テストに集約 |
| 今後の規則 | AGENTS.md の基本方針へ2項目追記。既存 TDD 規則も維持 |

### エージェントによる裁定と残る制限

1. 実行許可と内容の承認を分離し、初版を draft で保存した。誤っていれば内容の再検討が必要だが、承認の履歴は偽らない。
2. モデルは role API の定義に従い設定された tier を使用し、上流スキルの model 直接指定はしない。誤っていれば起動条件の見直しが必要になる。
3. 対象外の lock は #41 の ResoLoop lock であり、git index.lock のテストは D に含めた。誤っていれば対象範囲の再調整が必要になる。
4. 整理のための固定値テストを追加せず、既存挙動テストと隔離変異を使った。誤っていれば不足する挙動検査を追加する必要がある。
5. 明示パスや `/skill:` のような機械的な参照だけを検査し、型付けされていない裸のスキル名を説明ラベルから推測しない。見出し/ラベルの言い換えを許容する代わりに、裸の名前だけの typo は自動検出しない。
6. 最終レビューで危険 guard のコメント対応が `bash -c 'git reset --hard'` / `bash -c 'rm .git/index.lock'` を見逃したため、stale-lock contract だけをレビュー済み `884cf58` のバイト列へ復元した。一般 Bash パーサを追加して修正ループを続けず、安全側を維持する。危険コマンドの文字列を含む禁止説明コメントも拒否する既存の制約は残す（非ブロッキングの Minor）。

既存の `test_killed_create_reports_its_last_phase_and_leftovers` は途中で2回一過性に失敗した。`worktree-add` の journal 記録後、child が lock を継承する前に kill が起きる競合を、隔離コピーに0.5秒の遅延を挿入して同じ assertion で再現した。元のコピーと最終全検証は成功した。今回変更していない test/helper は修正せず、既知の範囲外の不安定な検査として残す。

layout の ResoLoop 同梱スキル差分警告も既存のもの。同期更新・live OAuth/catalog・CI 確認は対象外（この private repository の CI は停止中）。

### 所要時間

着手は2026-10-06 10:11 JST。実装・PR 公開確認は13:44 JST頃まで、約3時間33分。主な実装担当の実時間（レビュー/controller 待ちを除く）は、Task1 と修正23分22秒、Task2 と修正26分45秒、Task3 と全修正・安全 guard 復元約91分。初期調査/Spec・Plan は約13分、controller 最終統合4コマンドは約6分。各子の詳細は作業 report に記録し、読み取り専用レビューの概算値は実測値と混同しない。

予約解放・Issue の完了コメント・Herdr 更新の実施記録は PR/Issue コメントに残す。worktree は PR の追加修正用に維持する。

## 9. PR #46 レビュー指摘の選別（2026-10-06）

### 対象と実行許可

- 状態: completed。結論 **2: 修正不要としてマージする**。この節は初回実装のマージ禁止を変更したと推測したものではなく、別の今回の依頼による判断である。
- 実行許可: 利用者が `review-fix-planning` を明示して `#46` を指定した。計画のみの指定がないため、同スキルの完遂経路による検証、Spec の記録、既存 PR への文書反映、最終コメント、検証した HEAD のマージ、関連 Issue 更新までを対象とする。
- 検証対象 HEAD: `25deaa01110cf07d3069293ac670dc4af8eb616c`。取得した PR の head と専用 worktree の HEAD・clean 状態を照合した。既存 worktree を再利用したため、今回の片付け対象にはしない。
- 入力ディレクトリ: `/workspaces/reso-world/reviews/#46-chore-issue-36-fixed-value-tests/`。全4ファイルを読了。deepseek、claude、SWE の対象は `25deaa01110c`、gpt は `25deaa01110cf`。すべて上記 HEAD の同一コミットに解決され、祖先照合も成功した。
- 文書の選択: 対象リポジトリ・Issue #36・PR #46・固定値テストのテーマに一致する現行文書はこの Spec と対応 Plan の組だけだったため、この Spec を更新した。レビュー回別の文書は新設しない。
- CODE_ROOT / DOC_ROOT、DOC_BRANCH、PARENT_ROOT は冒頭の既存パスと `chore/issue-36-fixed-value-tests`。共通 context helper で base/head とも `origin` と照合した。

### 全指摘の分類

**解消済み 0 / 対応する 0 / 対応しない 8**。レビューの重大度や承認数ではなく、現行 HEAD での致命的な問題の有無を基準とした。検査の弱さが再現したものを「解消済み」とはしない。

| 入力・ID | 内容 | 分類 | 現行 HEAD での確認と理由 |
| --- | --- | --- | --- |
| `deepseek-deepseek-v4.1-flash.md` M-1 | piga/pigs/pigl/pixg の tier provider 制約がない | 対応しない | `test-pi-superagents.bash:279-315`、`test-pi-openai-codex.bash:26-44,149-182` と9個の source JSON を確認。pigs.balanced を cheap と同じ provider/model に変えた隔離入力は2本のテストで exit 0。現行 JSON は正常で、モデル/provider 更新の是非と将来の不正編集の検出範囲に関する論点であり、現行の秘密露出・誤対象操作・主要処理停止ではない。 |
| 同 I-1 | pr-review の HELPER の解決先を実行検査していない | 対応しない | 現行 `pr-review/SKILL.md:134` は `$TOPLEVEL` で helper も実在する。隔離入力で `$MAIN_ROOT` に変えても同 contract 全体が成功した。既存 D 表の共有 helper 検査は実在・symlink の保証であり、任意の将来の文章変更を拒否する保証ではない。 |
| `claude-opus-5-5.md` L-1 | 固定 remote・force remove・origin 限定の否定ガード削除 | 対応しない | 基準コミットの `review-fix-planning` contract:245-265、`repo-cleanup-after-merge` contract:92-117 の committed blob で削除を確認。現行 SKILL は検証済み remote、force なし、origin 限定のまま。既存 D 表で行・文章一致と操作手順の文章検査を削除する理由が明記され、理由なく削除した回帰ガードには当たらない。隔離入力の固定 remote、force、origin 絞り込み除去でも contract が成功する制約は事実として残す。 |
| 同 L-2 | 外部スキル名への参照をローカルと誤認 | 対応しない | `test-docs.bash:30-42`。`superpowers:writing-plans`、`/skill:superpowers:brainstorming`、`resonite-build` の3入力は、それぞれ存在しないローカルスキルとして exit 1。現行の検査対象6文書にはこの形式の参照がなく、公式の現行呼出しも通る。外部スキル名の解決範囲を広げる設計変更はしない。 |
| `SWE-2-High.md` I-1 | `--refs` の除外が argv 表記に依存 | 対応しない | `test-docs.bash:19,38-44`。`AGENTS.md` は成功、`./AGENTS.md` と絶対パスは架空例 `page-types.md` の拒否で exit 1。公式の2呼出元は固定のルート相対名であり正常。追加の表記のサポートは今回広げない。 |
| 同 I-2 | バッククォート内の末尾句読点をパスに含める | 対応しない | planning contract:50-66。実在パスへ `:` だけを付けた隔離入力はそのパスの exists assertion で失敗。現行 SKILL/session-workflow に該当形式はなく、将来の文書編集時の偽陽性である。 |
| 同 I-3 | herdr の状態 enum を文書全体の表から抽出 | 対応しない | herdr contract:20-27 とコマンドの case を比較。現行は一致。非状態の表の `unrelated` セルだけを追加すると集合の差で失敗した。将来の表追加時の偽陽性であり現行コマンドは壊れない。 |
| `gpt-6.1-sol.md` L-1 | tier 値のオブジェクト・フィールド型を検査しない | 対応しない | `test-pi-superagents.bash:304-315` と配置比較を確認。piga.cheap だけを数値にした隔離入力は2本の通常テストで exit 0。現行9個の JSON は正常。削除した検査はモデル値の一覧を読む際に付随して型破損も拒否していたもので、構造検査の独立ガードを理由なく削除した事例ではない。将来の source 編集に対する保険は追加しない。 |

deepseek の「Unverified candidates」3項目も確認したが、上の指摘8件とは別に扱う。

- stale-lock の `bash_blocks()` は bash フェンスだけを読む。隔離入力を sh フェンスへ変更した guard テストは成功した。現行は bash フェンスで guard が有効なので、将来の保険として対応しない。
- `check_refs` は参照数の下限を持たない。現行の6文書には実在検査対象があり、実在参照の正例は成功、参照切れの負例は exit 1。参照の削減自体を禁止しないため、対応しない。
- live Codex 検査で tier が全件非 Codex なら集合が空になりうるとの候補は、現在の source に Codex tier があり、さらに後段が各ランチャーの親モデルを集合へ追加するため、現行入力で空問い合わせにはならない。実物への live 接続は不要として行わない。

### 実装の保証範囲と選んだ方針

対応する項目がないため、守る条件と影響経路の修正表・失敗時ガードの修正・再発による設計の見直しは該当しない。選別中に見つかった別の致命的な PR 欠陥もない。

比較した案は、(1) 指摘された検査をすべて追加する、(2) 現行の致命的な問題だけ直し、実在する制約を明示する、の2つ。現行の設定・利用手順は正常で、前者は本 PR が整理する文章・設定への追加制約や将来の保険になるため、(2) を採用する。ソース・テストは変更せず、検証結果を記録し、PR の説明の既知の制限を具体化する。

3章 B1・4章 D と8章の「維持」は、すべての tier の provider/型や、あらゆるスキル例の安全性を自動判定する意味には広げない。現在の実装が維持するのは、配置先との一致、部分 config の外側キー/tier 名、既存 OpenCode/CommandCode の provider/モデル検査、stale-lock の危険コマンド検査、skill package の委譲境界、resolver の実行・helper の実在などである。Codex/xai の provider 全一覧、tier 値の型、固定 remote・force remove・remote 候補の文面検査は対象外。本文の意味とこれらの経路の安全性は現行 SKILL とレビューで確認する。PR の説明にはこの範囲、正当な文書参照でも失敗する条件、回避方法を記載する。

### 全文確認・検証結果

- 変更23ファイルの全文、全差分3031行、関連 source tier JSON・ランチャー・setup/helper、関連 SKILL/schema・参照処理・呼出元・テストを確認した。独立調査は同期の読み取り専用 role 3件へ委譲し、実行検証は controller が行った。
- 子では git 実行が利用できず、clean 状態と HEAD を controller が照合した専用 worktree の read を使った。最初の子が親 checkout を旧版根拠にした報告部分は採用せず、controller が `git show ee1421a:<path>` で取り出した committed blob と照合し直した。変更前の working tree は根拠にしない。
- 指摘の隔離検証は18実行。provider/型の変異4実行、外部スキル参照3実行、参照の正負2実行、argv 表記3実行、句読点・非状態表2実行、HELPER・固定remote・force/origin・フェンス4実行で、それぞれ上記の結果を確認した。変異は1回ごとに元のバイト列へ復元し、再現 worktree の tracked/untracked 差分が空であることを確認した。
- 専用 worktree で `uv run pytest tests/skills .agents/skills --basetemp <隔離ルート内>`: **487 passed, 1 skipped**、exit 0、117秒。skip は既存 `SKILL_UNDER_TEST` opt-in。
- `bash .devcontainer/run-tests.bash`: **28 PASS**、exit 0、179秒。変更 lifecycle テストなどを含む環境側検証も成功。
- `bash scripts/check-layout.sh`: **PASS**、exit 0、2秒。導入済み ResoLoop のスキル同期警告だけは既存のものとして維持し、同期変更は行わない。
- base を取り直した結果、`origin/main` は `ee1421ae3efb274cb5e28c8f3a810fe24ac5a3a6` で検証 HEAD の祖先だった。新しい base の一時 merge 検証は不要。private repository の停止中 CI は規約により対象外。
- 一時ファイル・ログ・pytest 出力は `/tmp/review-fix-planning.m1I6Vz/` に閉じ込め、再現 worktree を登録解除した後に親ディレクトリを削除した。Spec 作成前の teardown は成功し、消した場所は再利用しない。
- 修正後の自己レビュー: **未実施（結論2、コード修正なし）**。今回の同期調査3件は修正後の自己レビューではない。実物への OAuth/catalog 接続は未実施だが、今回の選別・通常検証の根拠には使っていない。
- 公開は、この Spec 1ファイルだけのコミットが検証済み HEAD の直後にあることを確認して fast-forward push する。マージには `--match-head-commit` を使う。push・マージ・Issue 更新の結果はここへ追記せず公開コメントで記録する。

### 今回の所要時間

controller が取得した時刻の区間: 初期照合・独立調査2件・分類が14:27:32〜14:36:06（8分34秒）、全差分の補完調査・関連処理確認が14:36:06〜14:42:34（6分28秒）、隔離再現・規定検証・結果確認が14:42:34〜14:49:58（7分24秒）、以降は teardown・Spec と PR の記録・公開処理。規定3コマンドの実行合計は298秒。子ごとの開始/終了の厳密計測は取得できず、子の推定時間を実測値としては扱わない。全体の公開完了時刻と総所要は最終報告・公開コメントに記録する。
