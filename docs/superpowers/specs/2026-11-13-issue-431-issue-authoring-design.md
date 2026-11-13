# Issue #431: issue-authoring の移植

## 管理と実行許可

- 状態: draft。内容承認を得たとは記録しない。
- 対象: [usaturn/create-reso-world#431](https://github.com/usaturn/create-reso-world/issues/431)。コードと文書を同じ PR に含める。
- 利用者の指示: `$issue-to-pr #431 --merge --design-review claude-code_opus_default --spec-review pi_openai-codex_gpt6-terra_xhigh --implement pi_openai-codex_gpt6-terra_xhigh --assign implement=pi_openai-codex_gpt6-terra_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`（元の改行を省いて引用）。
- 許可: issue-to-pr に従う通常の設計判断、Task の実装・検証・commit・push・PR 作成、指定のレビュー修正ループ、同ループの finalize.py によるマージ。移植するスキルの試験として実 Issue・ラベルを作成・変更する許可は含めない。
- 固定 base: `usaturn/create-reso-world / origin / refs/heads/main / 768c7c410558c1b4b705e82ac0c4687c35b51734`。
- 親 Issue・コメント・先行依存・同 Issue の既存 PR・予約・要求 base は検出されなかった。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-431-issue-authoring`、branch `feat/issue-431-issue-authoring`。
- 記録: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7`。確認用コピーは issue-to-pr の規則により作らない。

## 目的と現状

新しい Issue の案、既存 Issue の情報を保った整形差分、目標と実測値を照合する評価コメントの案を、この Dev Container 内で作れるようにする。作成済み Issue の実装は既存の issue-to-pr が担い、本スキルから実装や PR 作成を始めない。

移植元は `usaturn/agent-workspace` のコミット `6e71fae4d25f217b23ce2409517cf602437a3cbf`。対象は `.agents/skills/issue-authoring/` の全ファイルと `.agents/issue-format.md`、`.agents/scripts/issue_format.py`、そのテストの計 24 ファイル。GitHub から読み取って記録ディレクトリの `upstream/` に保存し、Git blob SHA を照合した。移植元の checkout は実行時に必要としない。

移植元は pydantic と標準ライブラリを使う。移植先のルートには pydantic・pytest・pyyaml と `uv.lock` があり、pytest は `.agents/scripts` と `.agents/skills` を既に収集する。`scripts/check-layout.sh` は追跡されたスキルと `.claude/skills` の相対リンクを検査するため、設定や checker の拡張を前提にしない。

## 採用する構成

### 共有書式とリポジトリ境界

見出し・ラベル・metadata・実行記録・評価コメントの定義を `.agents/issue-format.md` に置き、`issue_format.py` が表から読み込む。ブロックの読み書き、HTML コメント境界、目標と metadata の対応、壊れたブロックを成功扱いしない検査を維持する。

`projects.toml`・`repository-ownership`・`.agents/projects/<name>.md` は持ち込まない。`--repo owner/repo` を明示し、GitHub の大文字小文字の規則で正規化した後、移植先の共通 resolver を使って対象を確認する。親 checkout は既存の agent_tmp/context の仕組みで求め、feature worktree を常設親や採用済み台帳と誤認しない。継承した Git 環境の除去も既存の仕組みに合わせる。

まず `usaturn/create-reso-world` で全モードを動かす。外部を解決する場合は AGENTS.md の既存経路（ResoLoop fork/upstream、resoloop-meshy、採用済み external-tools の通常ツール）に限り、常設 checkout・remote・必要な実送信先を共通 resolver で照合する。未登録 repo の任意 CODE_ROOT 指定を新しい投稿経路に使わない。不在・不一致・未採用・壊れた台帳・曖昧さは拒否し、clone・探索・登録・別対象への切替をしない。書式を読む処理が新たな実装・release・実機操作の許可を作らない。

ラベルは共通書式の表に集約する。移植元だけに存在する tools/devenv、tools/workspace、projects.toml、repository-ownership の説明を、ルートの Python 環境、external-tools、現在の review/issue/skill/Dev Container の領域に合わせる。必要に応じて Resonite/Blender の領域を記す。既存ラベルを一括変更せず、不足ラベルの作成も投稿案に含めて承認後に行う。外部対象にもこの書式を使う場合はその旨を案に明示し、repo 固有の AGENTS.md/README を先に読む。既存の issue-to-pr や planning-parallel-issues がこの新書式を既に使用していると記述しない。

### 投稿・整形・抽出 helper

- `publish_issue.py`: create/update/comment の `draft` で preview・差分・hash を保存し、案を提示した後の利用者の返答で承認された SHA だけを `publish` に渡す。最初の依頼や非対話実行は承認の代用にならない。
- publish 前に、下書きの同一性、対象 Issue（PR 番号を拒否）、元本文・タイトル・ラベルとの競合、秘密情報を検査する。失敗時は書込みを行わない。送信結果が不明なときの再送防止と journal を保持する。
- Gitleaks の版は `.devcontainer/install_gitleaks.bash` の `GITLEAKS_VERSION` から読む。独自の版固定や bypass を追加せず、canary、redact、環境からの検査設定上書きの排除を維持する。検出値をログや公開文書へ転載しない。
- `reshape_issue.py`: snapshot → prepare → build → draft update → verify の順で、元本文、機械管理ブロック、保存用 archive を保持する。非 ASCII、複数行、CRLF、コードフェンスを含む元本文を復元して一致を確認する。情報削除で長さ制限を回避しない。
- `extract_issues.py`: 壊れた metadata を失敗情報として残し、他の Issue や記録を落とさず抽出する。
- 既存の分割・統合の手順も移植するが、別 repo への自動投稿、承認の省略、実データでの試験は追加しない。承認済みの限定 URL 置換は、移植元の比較・再 verify の条件を維持する。

### 手順と実行環境

`SKILL.md`、3 モードの references、agents/openai.yaml、評価シナリオを配置し、`.claude/skills/issue-authoring` から `../../.agents/skills/issue-authoring` を参照する。過去の評価資料をコピーしただけでこの環境で検証済みとは記録しない。移植元の実績は出典付きの履歴として区別し、今回の実行結果を別に記す。

すべての Python コマンドはルートの `uv run --locked` または必要な `uv run --project <root> --locked` を使う。保存する下書き・検証資料は `agent_tmp.py mkdir` が作る常設親の `tmp/agents/` 配下に置く。同 helper に無い `rm` は呼ばず、自分が作成した領域・停止状態・保存不要を確認して、AGENTS.md の空値ガードを付けた削除を使う。途中停止・承認待ち・非対話の下書きは保持して完全パスを報告する。使い捨て scanner 出力は一意の一時ディレクトリで回収する。

## 受け入れ基準と検証

| ID | 条件 | 観測する証拠 |
|---|---|---|
| A1 | この Dev Container で create-reso-world 向けの新規案・整形差分・評価案を各 1 件作れる | 実 helper を使った保存物と preview。外部 clone 不要。GitHub 応答だけを fake にする |
| A2 | 投稿前に内容を確認でき、承認された案だけを公開する | SHA 同一性と publish の正常系、非対話・案改変・元 Issue の競合・秘密検出時の GitHub 書込 0 件 |
| A3 | 整形が元本文の情報を保つ | snapshot と復元結果の一致、管理ブロックの保持、verify の正常系と改変拒否 |
| A4 | 未計測を実測・成功と扱わない評価案を作る | 目標・実測値・データ源を含む評価案と、測れなかった項目の理由付き未計測 |
| A5 | shared format/helper のテストをルートで実行できる | `uv run --locked pytest .agents/scripts/tests/test_issue_format.py .agents/skills/issue-authoring/tests -q`、全体 pytest、layout の終了コードとログ |
| A6 | 指定対象以外を黙って選ばない | 実 resolver を通した親の正常系と未登録・不一致の拒否。共通 resolver 自体の重複テストは増やさない |

テストは AGENTS.md の S に限る。秘密の漏れ、誤投稿、誤対象、競合による上書き、元本文や抽出記録の欠落、未計測の成功扱いを守る代表例を採用し、拒否には正常系を対にする。文言・見出し・ラベル一覧やパスの存在だけを照合する F/L のテストは追加しない。リンク・参照・CLI の実行・構造確認・diff は一時検証と layout に任せる。移植元テストも基準に照らして選ぶ。

`superpowers:writing-skills` に従い、スキル無し/ありで同じ非対話の3モードの依頼を実行し、案の保存・承認待ち・未計測の扱いを比較する。実 GitHub 書込みを禁止した fake CLI/fixture の評価であり、実 Issue の起票はしない。文字列を探すだけのテストで動作比較を代えない。未実行・失敗はそのまま記録する。

## 対象外

ワールド内の作業、既存 Issue の一括整形、実ラベルの移行、CI の有効化、新しい repository 登録・clone、issue-to-pr/planning-parallel-issues 全体への新書式の強制、課金 API・実機の試験、移植元への変更は行わない。依存や layout 設定は既存で足りる限り変えない。

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由・委任または停止条件 |
|---|---|---|---|
| D1 | 指定コミットの helper と書式を移植し、環境依存を置換する | 新しい小型 helper を書き直す | 元本文保存や投稿 journal の既存の守りを維持する。通常の実装方針として委任済み |
| D2 | 既存のリポジトリ境界と共通 resolver を再利用する | projects.toml と repository-ownership 一式を移植する | 二重の対象管理を避ける。未知・不一致を成功にせず停止する |
| D3 | 共有書式 → helper → 手順と統合確認の逐次 Task | 全体を一括依頼、同一ファイルを並行編集 | 共有前提を先に固め、1 Task ずつ runner に渡す。指定担当を失敗時に self へ切り替えない |
| D4 | fake GitHub で投稿ガードと3モードを検証する | 試験用の実 Issue を公開する | Issue が求める検証範囲を満たし、今回の許可外の投稿をしない |
| D5 | 明示された設計レビュー→Specレビュー→Plan の順 | builder check のみ | 利用者指定。Specレビューが builder check を代替する。設計の意味を変える指摘や利用者判断は helper の停止条件に従う |
| D6 | Task ごとのレビュー、PR 後のループで全体レビュー | PR 前後で全体レビューを重複する | issue-to-pr の --merge の規則。最大3サイクルは既定値で、利用者が指定した数ではない |

担当の検査結果: 設計 `claude-code_opus_default`、Spec と Task 実装 `pi_openai-codex_gpt6-terra_xhigh` は利用者の明示値。いずれも fallback は設定上空、self は false。PR 後の inspect は明示された `devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`、fix implement は明示された `pi_openai-codex_gpt6-terra_xhigh`。fix self-review/fix-check の self は設定の既定。loop の max_cycles=3 と template は既定の適用で、config override はない。各 check は終了コード 0。

レビュー結果と採否は、実際に受け取った後にこの節へ追記する。
