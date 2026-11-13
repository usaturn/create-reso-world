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

meshy の既知経路は共通 resolver 内に定義されていないため、呼び出し側の issue_format.py で検証済み親の固定パス `<PARENT_ROOT>/external/resoloop-meshy` だけを code_root に渡す。resolver は拡張しない。返された checkout がこの固定パスの常設 checkout であることと、origin が `usaturn/resoloop-meshy` に一致することを確認する。任意の別 checkout・別 remote による代替を認めない。固定パス不在時は既存の clone 手順を案内して停止し、自動 clone しない。

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
| A6 | 指定対象以外を黙って選ばない | 実 resolver を通した親の正常系と未登録の拒否。meshy 固定経路の正常系、別 checkout と origin 不一致の拒否。共通 resolver 自体の重複テストは増やさない |

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

### 設計レビューの記録

- 外部 helper による1回目。review_dir: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/2026-11-13-issue-431-issue-authoring-design.design-review/review-1`、review_id: `13c360f615f64b23b95f7507956c904a`。
- reviewed Spec SHA-256: `aca455623d7cfbc4a21b816fd5fda895ecb0a399a29fc747b422a1fd4c9f2632`。requested/actual agent: `claude-code_opus_default` / `claude-code_opus_default`。観測 identity: `{"model": "claude-opus-5-5", "provider": null, "effort": null, "session_id": "21b5c0c0-08c7-4932-9cc1-2f4b625b89ae", "cli_version": "2.1.323", "skill_versions": {}}`。fallback 不使用、elapsed_seconds=41.860。
- verdict=sound、指摘0件、questions_for_user/incomplete なし。D1-D6 を維持し、採否の対象はない。
- outside_changes=[]。unprotected_changes は開始前から存在する削除済みの別作業 worktree 登録6件（
  `/tmp/pr-review-376-2f0d17b0/worktree`
  `/tmp/pr-review-376-79fe98e5/worktree`
  `/tmp/pr-review-376-7f95b4e6/worktree`
  `/tmp/pr-review-376-c9a6d3e9/worktree`
  `/tmp/review-fix-planning.9AkFc2/worktree`
  `/tmp/review-fix-planning.a6ogtH/worktree`
  ）。対象 checkout の変更ではなく、記録のみとし回収しない。

### Spec レビュー1回目の記録

- review_dir: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/2026-11-13-issue-431-issue-authoring-design.spec-review/review-1`、review_id: `e7c06d8c1cf44b57a05ee985b59be933`、reviewed Spec SHA-256: `a4482ef5d8213909802282a17c6fb76824b10f5cb15d5cb089bc74cde9bc5756`。
- 外部 helper、requested/actual agent: `pi_openai-codex_gpt6-terra_xhigh` / `pi_openai-codex_gpt6-terra_xhigh`。identity: `{"model": "gpt-6.1-terra", "provider": "openai-codex", "effort": "xhigh", "session_id": "01a1d485-ca7e-71f1-bbce-ab511a4203d0", "cli_version": null, "skill_versions": {}}`。fallback 不使用、elapsed_seconds=71.245。
- S1（important）を採用。scripts/superpowers_context.py の既知経路を確認し、meshy の code_root を呼び出し側で固定し origin を確認する方針と A6 の対照検証を追加した。既存境界を具体化する修正で、許可対象を増やさない。
- outside_changes=[]、unprotected_changes は設計レビューに記載した同じ削除済み6登録。触らず記録のみ。

### Spec レビュー2回目の記録

- review_dir: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/2026-11-13-issue-431-issue-authoring-design.spec-review/review-2`、review_id: `e1c22c7ef5794abba20c4b94cfdc17dd`、reviewed Spec SHA-256: `86b47b82fe19bae16b618818e3d7582adc1545d260b2ec3fc7027cdaf999eb89`。
- 外部 helper、requested/actual agent: `pi_openai-codex_gpt6-terra_xhigh` / `pi_openai-codex_gpt6-terra_xhigh`。identity: `{"model": "gpt-6.1-terra", "provider": "openai-codex", "effort": "xhigh", "session_id": "01a1d489-6300-7605-a381-5b98ac4375da", "cli_version": null, "skill_versions": {}}`。fallback 不使用、elapsed_seconds=33.297。
- 指摘0件、incompleteなし。採否の対象なし。outside_changes=[]、unprotected_changes は同じ削除済み6登録。

## 実装・統合の記録（2026-11-13）

- Task1/2/3を指定Terraで実装し、Claude OpusによるTaskレビューはいずれも仕様適合・品質を合格と判定した。Task1/2の軽微な文書参照・テスト診断の指摘をTask3で修正し、Task3の指摘は0件。共有resolverやhelperの保護範囲は設計どおり維持した。
- A1: 実helperのcreate/update/commentが各1件のdraftとpreviewを保存。source checkoutを実行時に使わず、Gitleaks実版8.30.1とfake GitHub応答を使った。
- A2: 承認後改変・元Issueの競合・秘密検出・非対話で書込み0件、正常な承認相当入力で1回のfake投稿、再送防止を対象テストで確認。モデル評価も案の保存だけで止まった。
- A3: 独立に作ったfixtureの元本文と復元結果がバイト一致し、管理対象も保持された。旧metadataと後から追加した管理対象が保存済み原文を壊さないSテストを補完した。
- A4: 作業時間2/3/1分は平均2分で達成。未回収の転記ミス記録はactual/gapに理由を記しachieved=null。0・成功・失敗に置換していない。
- A5: ルートlocked環境の対象pytestは15件成功。最終全体検証は実装計画の必須3コマンドで行い、公開HEADと固定baseに結び付けてSESSIONのchecks.jsonへ保存する。
- A6: 実際の親resolverの正常系と未知repoの拒否、実Git/contextを使うmeshy固定checkoutの正常系・origin不一致・別checkoutへのsymlinkの拒否を確認した。

行動比較は同じTerraで各条件1回のみ。スキル無しでも3つの案を保存できたが、既存コメント取得と関連検索が省かれた。導入後は両方を実行した。今回の結果を一般の成功率や速度向上の根拠にはしない。記録は `.agents/skills/issue-authoring/evals/create-reso-world-validation.md`、実行証拠は `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/` に保存した。

## PR #433 のレビュー修正（サイクル1）

対象は公開 HEAD `f9347d1fc607a38eefbbf4a1edfee066ccafcc4b`、取り込んだ修正は `e67a669a67d0eaa2866d5c370f2e405eb51650ee`。planner は `gpt-6-astra`（codex）。利用者の `--merge` と review-fix-planning の完遂に基づく実行許可で進め、内容の承認を受けたとは記録しない。

指定された3レビュアーのうち、`claude-code_opus_default`（実際 `claude-opus-5-5`、220.229秒）は指摘0件、`pi_opencode-go_deepseek4-flash_max`（実際 `deepseek-v4.1-flash`、1636.253秒）は2件を保存した。双方の Merge recommendation は Needs manual verification で、未読・未実行とされた範囲を司令塔が変更ファイル全文、関連コード、検証証拠に照合した。

`devin_swe2_max` は response_failed・終了コード1、停止確認済み、成果なし。診断の cause は unknown で、stderr はプランに関する拒否を示した。成果なしを指摘0件とみなさず入力から除外した。利用者から復旧した旨と再依頼の指示を受けたため、次のサイクルでも Devin を含む元の3担当を使う。診断は `/workspaces/reso-world/reviews/usaturn/create-reso-world/#433-feat-issue-431-issue-authoring/loop/aee0e36c433441a992e37de2c1f994e9/cycle-1/diagnostics/aced397c02ef4605844b7575901dff80.json`。

### 採否・原因・修正方針

- 対応する: `deepseek-v4.1-flash#M-1@f9347d1fc607`（Medium）。本文PATCH後にラベル追加が失敗し、その間に他の利用者が本文・タイトルを変更すると、再実行がラベルを書き換えて `published` を返す。実helper・実Gitleaksとfake GitHubによる旧版の再現で、本文/タイトル各例で追加書込み2件と承認案との不一致を観測した。誤った成功と承認内容から外れた書込みなので分類(a)に当たる。
- 対応しない: `deepseek-v4.1-flash#L-1@f9347d1fc607`（Low）。初回create/updateの恒久的な正常系テスト不足は事実だが、司令塔の実行では両方成功し、独立した致命的な誤動作はない。AGENTS.mdのS基準に従い一般的な網羅は追加しない。M-1の拒否に対する正常再開は今回のS回帰テストで対にした。create/update/関連付けの実利用経路で気付かない損害が再現するか、欠ける守りの具体例が出たら見直す。

原因は、進行記録の `body=done` を現在の本文・タイトルの一致とみなしたこと。本文・タイトルの承認案との一致と、ラベルの正当な途中状態を同じ読取りで確認する `_require_update_state` を導入した。再開前、各ラベル書込み前、完了判定前に使う。自分が既に適用したラベルは認め、外部変更だけで拒否する。本文更新前の `_body_applied` を常に再利用する案は、ラベル追加済みの正当な再開を拒否するので選ばなかった。再試行の一律禁止、新しい永続ロック、journal全体の作り替えも不要と判断した。

守る条件は、不一致を読んだ後の追加書込みと誤成功を防ぎ、正常な途中状態から復旧できること。すでに完了した書込みを巻き戻すものではない。GitHubの読取りと後続書込みの間に発生する同時編集を不可分に防ぐ保証は追加しない。

### 要件と経路の検証結果

統合担当は司令塔 `gpt-6-astra`。A2の競合時停止と正しい成功報告を回復し、A1/A3/A4/A6は今回の2ファイル修正で前提を変えない。共通の本文更新・ラベル進行・journalの読書き順を、同じコミットの隔離worktreeで確認した。

| 経路 | 対象版での観測 |
|---|---|
| body doneからの再開、本文/タイトル/ラベルの外部変更 | 3例ともconflict、追加書込み0。remote全状態とdraft/preview/journalのbytes・modeが不変 |
| add失敗からの正常再開、add成功/remove失敗からの再開 | 残りだけ処理してpublished。承認案の本文・タイトル・最終ラベルに一致 |
| 初回updateとcreate | それぞれpublished。承認案に一致。create/commentの処理は変更していない |
| 同じ実行中、add後の外部本文変更 | DELETEへ進まずconflict。既に成功したPATCH/POSTだけが残る |
| 全step done、finish前中断後の外部タイトル変更 | 再開はconflict。書込み0・全管理状態不変 |
| 本文PATCH成功の応答だけを喪失 | 再開は再PATCHせずpublished |

代表のS回帰テストを1件追加し、拒否と正当な途中状態からの再開を含めた。修正後の隔離worktreeで本文/タイトルの一致ガードだけを外した対照では、その負例1件が `published != conflict` で失敗した。共有featureは変異させていない。実GitHubへの書込みは使っていない。

実装担当は指定 `pi_openai-codex_gpt6-terra_xhigh`、観測モデル `gpt-6.1-terra` / `openai-codex` / `xhigh`。1回164.863秒、fallbackなし、commit `f778beffa19da31cc2422fc71ec336b471c477b8` を停止確認と差分照合の後に取り込み、`e67a669a` になった。今回が初回の修正で、同条件の再発・修正による回帰の設計見直し条件には当たらない。

司令塔の検証は修正コミットで、`uv run --locked pytest tests/skills .agents/skills -q` が846 passed（789.84秒）、`env -u CODEX_THREAD_ID bash .devcontainer/run-tests.bash` が27件成功（112.528秒）、配置検査とdiff検査が終了コード0。前後とも作業ツリーに変更なし。CODEX_THREAD_IDの除外は、初回公開前にbaseでも再現した一時HOMEとの干渉を隔離するための指定である。自己レビュー前のGitleaks 8.30.1は14コミットを検査し検出なし。

詳細と全状態比較は `/workspaces/reso-world/tmp/agents/review-fix-433.hb8vc9hg/` の `fixed-reproduction/`、`accepted-checks/`、`controller-fix-evidence.json` に保存した。必須検証中にmainが `c120e59fc2a69cc7bc1640fafee13286b9b9c627` へ進んだことを確認した。最終化では最新baseを含むツリーを別途検証する。

### 自己レビューで判明した別ホストへの送信

`run_roles.py --phase self-review` を1回だけ予約し、self-review と fix-check をそれぞれ1回実施した。self-review は `gpt-6-astra` / codex、1504.328秒、対象 `e67a669a67d0eaa2866d5c370f2e405eb51650ee` のPR全体を読み、Medium 1件、Merge recommendation は Approve。fix-check は同モデル / codex、877.917秒で、修正の主張15件、変更2ファイル、関連する文書の候補15件を確認し、元の再開時の競合を再現せず、未確認・追加指摘とも0件だった。fix-check はこの時点の再開修正を確認したもので、後の送信先修正を確認した記録ではない。

追加で対応した指摘は `gpt-6-astra-commit-e67a669a67d0eaa2866d5c370f2e405eb51650ee#M-1@e67a669a67d0`。共通 resolver が GitHub.com の repo を照合しても、相対 endpoint の `gh api` が `GH_HOST` を継承し、別ホストへの update/comment を `published` と報告する。抽出も別ホストの記録を指定 repo の JSONL として返す。実 gh と loopback TLS fixture を使う司令塔の独立再現でも観測した。誤対象への書込み・記録の取り違えなので分類(a)として採用した。重大度や Approve の表記だけで除外しない。元の再開修正とは別原因で、修正による回帰ではない。

原因は、repo 識別と API ホストを別々に決めていたこと。publish と extract の各API入口に `--hostname github.com` を明示し、現行の直接操作手順も API のホスト指定または GitHub.com の完全な repo URL にそろえた。親シェルの `GH_HOST` やユーザの永続設定を変更せず、GitHub Enterprise 対応は追加しない。draft 時だけの環境検査では、公開までの環境変化を防げないので採用しなかった。

統合担当は司令塔 `gpt-6-astra`。A2の承認された投稿先、A4の記録の帰属、A6の誤対象防止を、repo とホストの組で照合した。

| 経路 | 最新の実装コミット `77d0993ee51415fff05059b32969fade8b230b0f` での観測 |
|---|---|
| publish共通API入口（読取り・create・update・comment・ラベル） | 実gh・実helperを2つのローカルTLS fixtureにつなぎ、GH_HOST未設定の正常update、別ホスト設定下のupdate/create、draft後に設定を変更したcommentを確認。すべてGitHub.com用fixtureだけに届き成功、別ホストへの要求0件 |
| extractの独立したAPI入口 | 同じ実CLIの別ホスト設定下でIssue/コメントをGitHub.com用fixtureから抽出。別ホスト由来の記録0件 |
| SKILL・3モード・共通書式の直接CLI手順 | API、issue view/edit/close、label createの5種類について実ghの引数受理とホスト選択を確認。試験用プロキシで接続を403拒否し、すべてapi.github.comを選択。実操作の成功を示す試験ではなく、外部への転送0件 |
| 先の再開修正 | 最新コミットで7ケースと操作順3ケースを再実行。外部編集時の追加書込み停止、正常再開、応答喪失後の復旧を維持 |
| ローカルの書式・reshape・archive処理 | HTTPを呼ばず今回の変更対象外。既存の保存処理を変更せず、対象テストを含む共通検証で確認 |

送信先を守るSテストをpublishとextractの独立した入口に各1件追加した。正しい公開・抽出を含め、隔離したworktreeでホスト指定だけを片方ずつ外すと、対応する負例がそれぞれ1件失敗した。同じ入口のaction組合せや文書の固定文言のテストは追加していない。実GitHubへの試験書込みは全検証を通して0件。

追加修正の担当も指定 `pi_openai-codex_gpt6-terra_xhigh`、実際 `gpt-6.1-terra` / `openai-codex` / `xhigh`。1回209.554秒、fallbackなし。workerの `7e00b46b76dac9075848502325a0c698f7add273` を停止確認と全差分の照合後に取り込み `77d0993e` となった。自己レビューの枠は既に使用したため、この追加修正を再レビューしていない。司令塔が新しいコミットで検証し、push後の次サイクルでDevinを含む指定3モデルへ全体レビューを依頼する。

このサイクルの採否は対応する2件・対応しない1件、未確認0件。自己レビュー・fix-checkの再予約はしていない。内容の承認は受けていないため、利用者の issue-to-pr に関する文書保存規則に従い Spec・Plan の状態は draft を維持し、この節でレビュー修正作業の完了を記録する。

証拠: `/workspaces/reso-world/tmp/agents/review-fix-433.hb8vc9hg/host-fix-evidence-summary.json`、同ディレクトリの `final-routing/`、`doc-cli-eq5o4ufy/`、`host-checks/`。自己レビューと修正確認は `reviews/usaturn/create-reso-world/#433-feat-issue-431-issue-authoring/` 内の commitレビュー、`verified/e67a669a67d0.fix-check.json`。サイクルの状況コメントはPR #433にreview-records v2のサイクル1として投稿する。

最新の共通検証（上記77d0993e、前後clean）: `uv run --locked pytest tests/skills .agents/skills -q` は848 passed（843.70秒）、シェル共通テスト27件、配置検査、diff検査はすべてexit 0。シェルには既存の一時HOMEとの干渉を除く `env -u CODEX_THREAD_ID` を適用した。実行argv・時間・ログSHAは `host-checks/checks.json` に保存した。
