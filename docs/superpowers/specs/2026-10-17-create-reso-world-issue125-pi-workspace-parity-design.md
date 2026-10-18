# Issue #125: pi の agent-workspace との共通化

## 管理・実行許可

- 状態: `completed`（PR #141 の追加レビュー修正とローカル検証が完了。内容の承認・実機の受け入れとは区別する）
- 文書・実装対象: `usaturn/create-reso-world`、https://github.com/usaturn/create-reso-world/issues/125
- 利用者の指示: `/skill:issue-to-pr #125`。同スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」を適用する。マージ・実環境の更新・認証・課金呼び出しは行わない。
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-125-pi-workspace-parity`
- branch: `feat/issue-125-pi-workspace-parity` → `main`
- 公開: https://github.com/usaturn/create-reso-world/pull/141。初回実行は完了しPRで公開したが、内容への承認とは区別して初回公開時はdraftを維持した。後続のレビュー修正結果は下段に記録する。Windows/rebuild/実providerの確認はIssue #125のchecklistに残す。
- 移植先の基準: `76f1098af9f07388f4c10d55786ea9d726654171`
- 移植元: `usaturn/agent-workspace` main `715d98168ab60011a98a42476ffea2759d4866d7`（2026-10-17 に再確認）。この SHA のファイルを読み取り専用の GitHub snapshot から取り入れる。外部 checkout の探索・clone・変更はしない。
- 先行条件: agent-workspace #713 は PR #714 でマージ済み。後続の修正 #716 / PR #717 もマージ済み。同じ Issue の open PR・担当予約・branch・worktree は無い。GitHub parent は無い（parent API の 404 は正常な不在）。#122 は rebuild 後の確認待ちだが、必要な設定の PR #129 はマージ済みで基準に含まれる。

## 安全停止と再開許可（2026-10-17）

- `4220f04` のブランチレビューで、Codexテストが移植先に存在しないDSHのstepを切り出しの終端にしている問題（F-1）を確認した。実行済みテストは導入の後続処理へ到達しており、以前の終了0はオフライン性や隔離の根拠にならない。安全規則により停止し、push/PRは行わなかった。
- 問題と影響未確定を説明した後、利用者から「安全に続行してください。」と明示指示を受けた。F-1の切り出し修正、外部通信・実領域の書き込みを拒否する隔離と実行回帰テスト、読み取り専用の影響調査を許可された範囲として再開する。内容の承認ではなく、状態はdraftを保つ。
- 再開時のmetadata調査では、実starship/herdr/.zshrc/.npmのmtime/ctimeは問題のテストより前だった。ただし削除の有無やdownload installerの全影響を復元できる記録は無く、影響無しとは断定しない。復旧・削除・実installerの再実行はしない。

## 意図・範囲

共有の `~/.pi` を使う二つの Dev Container が、作り直すたびに拡張の登録を入れ替える問題を解消する。pi の実行ファイル・setup・tier・モデル・導入の pi 節・テストを移植元と共通化し、今後の取り込みで独自修正を最小限にする。安全策を含む既存の独自実装を維持する移植ではなく、Issue が明示した置き換えを行う。

### そのままコピーする対象

- `.devcontainer/{pigo,pigod,piccg,piccd,piga,pigs,pigl,pixg,pigemf,pigemp,pigema}` と `pi-superagents-exec.zsh`
- `.devcontainer/pi-superagents/` の上記 11 本の JSON、`.devcontainer/pi-models.json`
- `scripts/{setup_pi,setup_pi_commandcode_goat,setup_pi_opencode_go,setup_pi_superagents}.zsh`
- `.pi/{mcp,settings}.json`
- `.devcontainer/install_beforehand.bash` は、移植元の `step "Installing pi"` から `step "Installing DeepSeek Harness"` の直前までを、移植先の `step "Installing pi"` から `step "Installing the shared skills (herdr / find-skills)"` の直前までに対応させる。移植先に DSH の step は無い。非 pi 部分は変えず、`STEP_TOTAL` は 28 → 30 にする（pi 節 7 → 9 step）。
- テスト `.devcontainer/{test-pi-superagents,test-pi-openai-codex}.bash`、`tools/devenv_migration/tests/{test_pi_mcp_adapter_migration,test_pi_vertex_launchers}.py`（後述の例外のみ）。

### 削除する追跡ファイル

`.devcontainer/pigou`、`.devcontainer/pi-superagents/pigou.json`、`.devcontainer/cleanup_pi_mcp.py`・`pi_json.py`・`test-pi-mcp-cleanup.bash`・`.devcontainer/tests/test_pi_mcp_cleanup.py`・`.devcontainer/tests/fake_pi_packages.py`、`.devcontainer/` にある旧 setup 4 本。`union-alpha` は移植元のモデル定義への置き換えで除く。

利用者の `~/.pi`、古いバックアップ・独自モデル・導入済み pigou は削除しない。撤去前の `pi-retired-*` バックアップを今後自動作成しないという変更であり、既存バックアップの削除を意味しない。既存モデルの同期は利用者が必要な provider の setup を選んで行う。

### 文書・設定の統合

`.devcontainer/devcontainer.json` の `containerEnv` に `PLANNOTATOR_REMOTE=0` と `PLANNOTATOR_PORT=19432-19441` を追加する。`forwardPorts` は既存の 8000 を保持し 19432〜19441 のみを足す。移植元の 3080・8788 は持ち込まない。

`.devcontainer/README.md` の pi 節は移植元を基にする。Plannotator のネットワーク、旧移植元の Issue 番号、リポジトリ固有の API トークン、テストの入口・共有先など事実の違いだけを調整する。ルート README の MCP 説明、旧 setup / cleanup の現行参照、`docs/maatlog-poc-porting.md` の判断と rebuild 手順を更新する。過去の Spec・Plan は凍結した履歴として変えない。

## 振る舞い・受け入れ条件

1. context7-pi と Plannotator は導入対象となり、撤去対象から context7-pi が外れる。登録済み・未登録の双方で、pi の導入節を fake CLI と隔離 HOME で実行し、二度実行しても両拡張が残ることを確かめる。実共有 HOME へ install / remove はしない。
2. 11 本のランチャーは regular TUI、追加引数、cwd、既存の認証案内、tier の分離を保つ。Gemini は親子とも ADC の marker overlay を使い、保存済み OAuth を更新せず、auth 以外の settings / sessions / lock を通常保存先に残す。
3. ADC の存在・有効性はランチャーが調べず Pi が解決し、無ければ Pi が理由を表示する（移植元の設計）。offline テストは Pi / SDK の通信境界を fake にし、ADC を調べない起動と受け渡しを確認する。実際の ADC 不在エラーと実モデル起動は利用者が rebuild 後に確認する。
4. Plannotator のポート範囲は `19432-19441`、各ポートを VS Code の転送対象にする。`--network=host` は維持し、`PLANNOTATOR_REMOTE=0` で loopback だけに bind する。レビュー URL の実際のパス・query を維持して Ports の Local Address を Windows で開く。自動起動は保証しない。
5. 文書・設定だけに文言検査テストを追加しない。実行ロジックの再発テスト、構文・参照先・差分・ファイルモードを検証する。
6. rebuild、共有コンテナとの交互の rebuild、Windows ブラウザーでの承認と修正要求、各実モデルの起動は未実施とし、利用者向け checklist を #125 のコメントと PR に残す。ローカル成功を実機成功と書かない。

## 決定記録・移植元との差分の例外

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| D-1 | setup 4 本を `scripts/` に移し、移植元と同一にする | `.devcontainer/` を維持して各参照を書き換える | Issue の推奨。ランチャーとテストを共通化できる | Issue #125 と issue-to-pr の通常判断の委任 |
| D-2 | pi 導入節を丸ごと取り入れ、独自 cleanup / JSON helper を削除 | 独自の保護・バックアップを維持 | 明示された置き換えと共有登録の問題解消。ResoLoop・Meshy・DSH の節は不変 | 利用者 HOME の実操作が必要になったら止める |
| D-3 | pytest の配置を移植元と同じにし、新規 `.devcontainer/test-pi-migrations.bash` から `uv run --no-project --with pytest python -m pytest` で当該2ファイルを実行 | testpaths へ追加、tests/ への移動 | ルートのスキルテストと混ぜず、既存 run-tests の自動収集から確実に実行できる。`parents[3]` を変えない | uv 必須。Python の一般的実行に python3 は使わない（bootstrap は既存例外） |
| D-4 | `.pi/APPEND_SYSTEM.md` は既存のプロジェクト・handoff・所有権・同期直列・Superpowers 内だけという制限を保持する。「サブエージェントの起動」の冒頭2項目だけを移植元の現行APIの説明にする。`agent`/`task`/`tasks` の worktree 自動作成の説明は持ち込まず、ペルソナ節は1バイトも変えない | 移植元の節を完全コピー | 移植元の #717 はワークフロー外でも委譲するが、この環境の明示ツール制限に反する。projects.toml / repository-ownership は無い | 現在のツール定義と明示 opt-in 制限を優先。制限を緩和しない |
| D-5 | Plannotator は `REMOTE=0`、port range と全10ポートの転送は共通 | REMOTE=1 の完全コピー、転送無し | host network で 0.0.0.0 待ち受けを作らない。Windows へは VS Code のローカル転送を使う。既存の8000とuv設定も保持 | 外部公開・トンネル・firewall変更はしない。実 browser は利用者が検証 |
| D-6 | source bash テストの削除変数へ `${VAR:?}` と `--` を付ける。fixture の一時 HOME は env のみ | 無変更コピー | AGENTS.md の安全規則。実行時の失敗条件を変えない | 安全規則の回避は不可 |
| D-7 | 移植元の実行テストは保持するが `test_opencode_go_tiers_use_opencode_go`（設定値の写し）を持ち込まない。構造検査と実ランチャーの実行は残す | テスト本文の完全一致 | AGENTS.md のテスト採用基準。model ID は実ランチャーから導出される。他の構造・機密情報禁止検査はユーザー所有の共有設定を守る検査 | 差分例外として PR に列記。文書テストは作らない |
| D-8 | 共有登録の保持を追加の実行テストで確認する | extension 一覧の文字列検査だけ | 元の不具合（作り直すと登録が消える）を fake pi の状態で再現する必要がある | 通信・本物の資格情報の利用はしない |
| D-9 | PR はスキル指定どおり `Closes #125` とし、実機確認が残ることを明記して同 Issue に checklist を残す | Refs のみで閉じない | この run の終了方式に従う。実機成功を偽らない | マージは行わない。必要なら利用者が実機確認後にマージ |
| D-10 | Codexの導入テストは、開始とtargetのshared-skills終端を検証し、両端が揃うまで何も出力しないhelperで切り出す。実行はbwrapのread-only root、private /tmp、書込可能な専用HOMEのみ、独立network namespaceへ限定する。回帰検査は実テストを同じ隔離と外部コマンド拒否stubで実行する | 終端文字列だけの置換、PATH stubだけ | 未知の終端でEOFまで実行する再発と、absolute command/cleanupの実領域アクセスを構造で防ぐ | 利用者の安全な再開指示。非pi導入処理を変えずtest helperだけに適用 |

## 検証

- 変更前: `bash .devcontainer/run-tests.bash` 32 本、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts` 625 件が終了コード 0。
- RED: 移植元の pytest の代表例を先に持ち込み、未移植の launcher / function が理由で失敗することを観測。追加の共有登録テストも旧導入節で context7 の撤去を観測する。
- GREEN: 上記 README の3入口と、新しい pi migrations の入口を実行。元ファイルとの diff を取り、無変更対象の一致と例外を PR に書く。
- Plannotator は導入済み拡張の `server/network.ts` と公式文書（Context7 `/backnotprop/plannotator`）で REMOTE=0 の loopback と port range 対応を確認済み。合成 Markdown と隔離設定だけで bind / port fallback / review HTTP の往復を可能なら確認する。共有状態は変えない。
- JSON / JSONC・shell の構文と Git diff / file mode / 参照先を確認する。Plannotator の移植元文書が案内する `subagent.usePlannotatorReview` は現行の引数に無いため、通常の確認では提供されている `superpowers_plan_review` ツールを案内する（文書のAPI修正の例外）。未 push commit を `scripts/scan-before-push.sh` で検査し、同じ SHA を push する。private Actions は無効のため確認しない。

## ローカル検証の結果（2026-10-17）

- Task 1: 共有登録の回帰テストは旧導入処理で context7 が消え、2件が失敗（RED）。移植後は pi の3入口すべて成功。移植元 MCP / Vertex 2ファイルの内容は同一。追加の状態遷移テストを含む migrations は149件。
- 全体: `run-tests.bash` 32本、`check-layout.sh`、スキル・script の pytest 625件が全て終了0。
- Plannotator 0.28.23: `REMOTE=0` の `127.0.0.1`、設定ポート範囲の解析を確認。現在の環境では19432〜19441が EADDRINUSE（Linuxのssに対応listenerは表示されない。Windows側の状態は未調査）。他者のserviceには触らず、一時範囲45123〜45128へ検証方法を変更し、意図的に45123を占有すると45124で起動、合成日本語Markdownの取得と合成承認のHTTP往復が成功（終了0）。これは実際のSpec / Planへの承認ではない。
- 実設定範囲での起動、Windowsブラウザー、rebuild、実モデルは未検証。現在のrangeの占有原因と到達性は利用者の実機checklistに残す。

## F-1 修正後の再検証（2026-10-17）

- 外側をread-only root/private tmp/network namespaceと実外部操作を拒否するstubにした実CodexテストでREDを確認。旧終端はfake npxへ到達して終了1、実network/download/cleanupは行っていない。
- `pi-launcher-install.bash` が開始/終端を全て検証してからbufferを出力し、targetのshared-skills手前で切る。実行はread-only root、private /tmp、専用HOME bind、networkとPID namespaceに限定する。実導入処理そのものは移植元と同一で変えていない。
- 8件の実行回帰（外部installerへの未到達、欠落/重複/逆順で出力無し、正しい範囲だけ実行、ホスト/tmpの内容保持・repo書込拒否・テスト所有のhost listenerへの接続拒否）は全て成功。
- 修正後の全体再実行: bash32本、layout、pytest625件が終了0。migrationsは既存149件＋回帰8件の157件。以前の終了0と混同せず、再検証ログを分けた。
- 限定re-reviewでは、外側のread-only rootが内側helperの退行を隠す検査上の問題を指摘された。外側では書けるテスト所有mountを`/mnt`へ追加し、外側の書込成功・内側の書込拒否を個別に確認した。専用copyのhelperからreadonlyを外すと、このfixtureへの書込だけを起こして回帰検査が失敗（RED）。実helperは8件全成功（GREEN）。実領域の保護を緩めず検出力を確認した。
- 実機・過去影響の不明点は引き続き残る。Windows/実range/rebuild/実providerの成功は主張しない。任意の悪意あるコードに対する完全なsandboxを保証する変更ではなく、テストの誤実行範囲とI/Oを隔離する。

## Builder check の裁定

2026-10-17、独立した読み取り専用 `sp-recon` が Spec と source / target を照合した。指摘3件（導入節の target 側終端・devcontainer 変更の明記・APPEND_SYSTEM の変更範囲）は全て既存のファイルと明示ルールから解決し、上記へ反映した。利用者だけが決められる未解決事項は無い。最初の `sp-review` はレビュー scope 未指定として開始前に拒否したため、builder check を `sp-recon` で行った。後のブランチレビューは正式な branch scope とテンプレートで依頼する。

## PR #141 レビュー修正（2026-10-18、完了）

### 範囲・実行許可

- `/skill:review-fix-planning` と PR #141 の指定を、同 PR の修正・検証・既存 head への push の実行許可として扱う。内容への承認は推測しない。結論は **1: 修正して push**。今回はマージしない。
- 入力は `reviews/#141-feat-issue-125-pi-workspace-parity/` の `SWE-2-Max.md`、`claude-opus-5-5.md`、`gpt-6.1-sol.md`、`grok-4.7.md`。すべて対象 HEAD は `60bcb6247e06`。現行 HEAD `60bcb6247e0696dc0fb67c14ec7c3be495d3099c` と一致し、取得した PR head との祖先照合も成功した。
- 同テーマの文書をリポジトリ・Issue/PR・本文で検索し、この Spec と既存 Plan を更新する。別 Spec は作らない。clean かつ PR head と一致する既存 worktree を再利用し、他 worktree の差分は読まない。
- 以下は以前の D-1（setup の完全一致）を、安全上必要な3本の差分に限り変更する。旧 cleanup 全体の復活はしない。移植元リポジトリの変更・実認証・rebuild・外部モデルの呼び出しは対象外。

### 全指摘の分類

S=SWE、O=claude-opus、G=gpt、K=grok。未検証候補も独立した入力として落とさず数える。**解消済み0 / 対応する11 / 対応しない5（計16）**。同一原因は F-1〜F-6 にまとめるが、入力ごとの件数は重複排除しない。

| ID | 元の指摘 | 判定 | 現行 HEAD の根拠・発生条件 |
|---|---|---|---|
| S-M1 | DeepInfra の失敗を成功扱い | 対応する (a)、F-3 | 不正JSONで実setupが終了0・validation/完了表示。案内どおりの更新結果を誤認する |
| S-L1 | shrinkwrap・manifest-only helper の検査縮小 | 対応しない | installerはrootのpackage/lockと登録済みhelperを扱う。旧cleanup撤去はD-2の意図した変更で、表示補助の残存自体は主要処理の停止を示さない |
| S-L2 | models の固定tmp、mode・リンクの切断 | 対応する (a)、F-1/F-5 | Command Code/OpenCodeの実setupで0600→0644、symlink→通常ファイルを再現。既存キーの公開範囲と共有先が変わる |
| S-I1 | /tmp checkout で移行テストが失敗 | 対応する (a)、F-6 | 規定の/tmp worktreeで隔離pytestが3失敗、他5件はhelper未読込でも通る。公式の検証経路が止まる |
| O-M1 | forwardPorts がPlannotatorを占有する疑い | 対応しない | 全10ポートのEADDRINUSEは再確認したが、Windows側所有者・forwardPortsとの因果関係は確認できず、設定変更の根拠にならない。既知の制限として記録 |
| O-L1 | /tmpの不可視・境界テストの空振り | 対応する (a)、F-6 | S-I1と同じ隔離worktreeの実行で再現。正常fixtureの実行とstderrも確認する |
| O-L2 | DeepInfra の偽成功 | 対応する (a)、F-3 | S-M1と同じ実行根拠 |
| O-I1 | Vertexテストの一覧/project固定値 | 対応しない | 運用値の転記であることは確認。現構成で一致しており、実行不具合ではなくテスト設計の論点。今回の致命的修正へ広げない |
| G-M1 | modelsのmode拡大 | 対応する (a)、F-1 | 他providerの合成apiKeyを保持したまま2本で0600→0644を再現。親が辿れる構成で秘密の公開範囲が広がる |
| G-M2 | ~/の誤保存 | 対応する (a)、F-2 | 3本ともcwd/~/配下へmodelsを作成。OpenCodeはauthも誤保存し、launcherのHOME側には届かない |
| G-M3 | DeepInfraの偽成功 | 対応する (a)、F-3 | 不正JSONで終了0、既存データ未更新のまま成功表示を再現 |
| G-M4 | BOM付きmodels/authの拒否 | 対応する (a)、F-4 | 3本ともBOM付きmodelsを更新できない。Windows共有でPiが扱う既存設定の更新経路を止める。authも同じread_text経路 |
| K-H1 | ~/配下の資格情報の誤保存 | 対応する (a)、F-2 | G-M2と同じ実行根拠。認証ファイルを意図しないcwdへ作る |
| K-M1 | DeepInfraの偽成功 | 対応する (a)、F-3 | S-M1と同じ実行根拠 |
| K-U1 | manifest-only helperの復活候補 | 対応しない | 関数はhelperの一覧だけを判定するため残存の可能性はある。S-L1と同じ意図的な範囲縮小で、致命的な誤動作の根拠は無い |
| O-U1 | 他containerの転送との競合候補 | 対応しない | O-M1と同じ観測。Windows所有者と他containerの状態は変更せず、原因の推測でforwardPortsを撤去しない |

### 守る条件・影響経路

各 F の行は上表の全「対応する」に適用する。既存呼出元はREADMEの手動provider setup、bootstrapからのtier setup、Codexのtest helperと隔離pytest。provider setup3本以外で同じ更新を行うinstallerの雛形初回配置は今回の原因と異なり、対象外とする。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
|---|---|---|---|
| F-1: models更新で既存データ・読み取り権限を失わない | 3 provider setupの更新/変更なし/新規、modelsバックアップ | 修正する。新規0600、既存mode保持、一意な0600 stagingと既存modeのbackup | 実setupで別provider保持、0600維持、新規mode、再実行の状態比較 |
| F-2: 設定の書き手とPiの読み先が一致する | 3 provider setupのPI_DIR決定、OpenCode auth | 修正する。mkdir前に~・~/だけをHOMEへ展開、相対パスはcwd基準 | 絶対/空/未指定/相対/~ /~/を実行しcwdに意図しない~が無い |
| F-2 | launcher共通helperのCodex/xAI/Vertexのagent_dir | 既に満たす。~・~/をHOMEへ展開する | 既存Codex/Vertex実行回帰 |
| F-3: 不正入力はバックアップ・auth・launcher・cacheを変更せず失敗し成功表示しない | 3 setupのmodels/source検査、OpenCodeのauthとキー確認 | 修正する。3本が使う狭いprovider更新処理へ入力検証を集め、全入力を検査してから書く | JSON構文/トップレベル/providers/auth/dest各1異常で管理状態全体を比較、外部pi呼出なし |
| F-4: Piが扱うBOM付き設定を更新できる | 3本のsource/models読取、OpenCode auth読取、Command Codeの事後読取 | 修正する。utf-8-sigで読む | BOM有無でprovider/auth保持と反映を実行確認 |
| F-5: 共有リンクや特殊ファイルを暗黙に置換しない | 全models更新、OpenCode authの新規/既存/変更なし | 修正する。single-link通常ファイルか未作成だけを許可。リンク・directory・FIFOは副作用前に拒否 | symlink（有効/切れ）/hardlink/FIFO/directoryと共有先・mode・全状態の比較 |
| F-6: 検証対象が読め、失敗理由が境界検査である | test helperのrepo bind、pytest外側sandbox、正常/不正fragment、実Codex | 修正する。private /tmpの後にrepoをro-bindしcwd固定。境界の負例は正常例と診断を併記 | /workspacesと/tmp両方で同じ実suite、readonly/network/境界guardの対照 |
| 対象外 | setup_pi_superagentsのtier更新 | 対象外。PI_DIRを使わず拡張のHOME固定仕様 | 既存回帰は維持する |

### 守る条件の設計・再発の見直し（F-6）

F-6は同じPRでc35db31とe5a77a8が扱った「対象fragmentを本当に実行しながら実領域を保護する検証」の隣の経路であり、同じ守る条件の2回目として設計を見直す。以前はread-only root/private tmpを付けたが、private tmpが対象repoを隠す停止位置と、helper未読込が負例の成功に見える経路を列挙できていなかった。

| 経路/停止位置 | 変更前の挙動 | 判定 | 確かめるassertion |
|---|---|---|---|
| 外側sandboxの/tmp置換→source | /tmp repoが消える | repoをro-bindしcwdを固定 | 正常fixtureがallowedだけを出し終了0 |
| 内側helperの/tmp置換→相対installer参照 | repoが消えHOMEへcwdが変わる | repoをro-bindしcwdを固定 | 実Codex suiteが全launcherを配置して終了0 |
| 境界の欠落/重複/逆順 | helper未読込でも負例が通る | 正常対照と境界診断を確認 | returncode非0・stdout空・境界診断、前後の全状態一致 |
| 正常fragmentのrepo/host tmp/networkアクセス | readonly/private tmp/net nsで拒否 | 保持 | テスト所有writable mountは外側で書け内側で書けない。host listenerへ接続不可 |
| staging作成/境界拒否/bwrap失敗 | 専用HOMEだけにfragmentを置く | 維持。拒否時はfragment自体を作らない | HOME・外側ファイル・auditの前後比較 |

案の比較: (1) /tmpだけskipする点の対処は公式worktreeで検証できず不採用。(2) private tmpと対象repo/専用HOMEのmountを両層で明示し、正常fixtureと拒否理由を対にする案を採用。(3) 隔離保証を狭めtmpfsを外す案は実/tmpを保護できず不採用。readonly/network/boundaryの中心guardを外す対照は専用の使い捨てworktreeだけで実行する。

### provider更新の設計・比較

3本へ修正を複製する案はOpenCodeがauthを先に更新する順序の漏れを招くため不採用。`.devcontainer/pi-provider-setup.py` にprovider更新だけのpreflight・BOM読取・安全な保存を集める。旧pi_json/cleanupの汎用移行処理は復活させない。キーは環境から読み、argvへ渡さない。既存定義のうち対象providerだけ更新し、他providerとauthを保持する。新規/変更なし/既存更新で同じ検査を使う。

不正入力のときは、models/auth/sourceの構文・必要なobject構造・保存先の種類を全て検証し、serializationまで済ませてからmkdir/staging/backup/置換を行う。ファイルI/O障害は入力拒否と区別する。各ファイルは一意なstagingで完成させてから置換し、元を途中まで書かない。I/O障害時は非0、未使用stagingを掃除する。複数ファイル・launcher・外部catalog更新全体のrollbackや同時setupとの排他は保証せず、完了した置換とmodelsのバックアップが残り得ることを明記する。実行中のPi・他setupを止めて使う。

### 検証予定・進捗

- RED: reviewed HEADの一時worktree（SHA照合済み）で、実setupのmode拡大・~/誤保存・偽成功・BOM拒否・リンク切断を合成キーだけで確認。最初のsandbox準備はreadonly rootに/sourceを作れず停止したため、private /tmpへrepoを明示bindして修正してから再現した。これはsetupの結果に数えない。
- RED: /tmp worktreeの隔離pytestは3 failed/5 passed。5件はhelper未読込による空振りを含む。上記一時worktreeと親ディレクトリは手順3の終了時に削除済み。
- 自動回帰はコードの分岐・ファイル操作を実行するものだけ追加。文言・一覧だけのテストは追加しない。
- 検証: providerの実行回帰、migrations全体、/tmp worktree、中心guardの対照、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、syntax/diff。スキルは変更しないためスキル全体pytestは反映条件に加えない。
- 自己レビューは反証（F-1〜6の全経路・旧版との差）、PR全体（変更ファイル・呼出元・テスト・保証）、検出力（state全体・単一異常・対照）の3観点をcontrollerが1回実施。追加の指摘は0件。調査役の同期呼出2件は結果無しで返ったため成功扱いせず、controllerが読取確認を引き継いだ。自己レビュー後のコード変更と2回目のレビューは無い。0件を実機未検証の解消とは扱わない。

### 修正後の最終検証・失敗時の検証

| 検証 | 結果 |
|---|---|
| provider setup回帰 + installer isolation | 86 passed / exit 0。うち新規provider回帰78件 |
| /tmpのSHA照合済みworktreeへ修正内容をコピーして同じ2ファイルを実行 | 86 passed / exit 0 |
| 同/tmp worktreeの `bash .devcontainer/test-pi-migrations.bash` | 235 passed / exit 0、126.07秒 |
| 専用feature worktreeの `bash .devcontainer/run-tests.bash` | 32/32 PASS / exit 0、302.1秒。migrations235件を含む |
| `bash scripts/check-layout.sh` | PASS / exit 0 |
| bash/zsh構文、Python AST、`git diff --check` | 全て成功 |
| 単一異常の拒否 | models8種×3本=24、auth7種=7、source4種×3本=12、キー不在1、境界5。計49ケースで状態保持 |
| I/O障害 | fsync/最初の置換/2番目の置換の3ケース。途中ファイル無し、未使用staging無し、許可したmodelsとbackup以外は不変 |
| storage guardを外す対照 | symlink・切れたsymlink・hardlinkの12/12負例が失敗（exit 1） |
| 境界guardを外す対照 | 5/5負例が失敗（exit 1） |
| readonly / networkをそれぞれ外す対照 | 各1件が失敗。fixture所有mountへの書込は83、fixture所有host listenerへの接続は84で検出 |

状態比較はテスト所有root全体（HOME、cwd、bin、models/auth、他provider、共有先、backup、staging、外部pi呼出audit）の有無・バイト列・mode・種類・リンク先・link数を基準にした。期待値は実行前のsnapshotから取得する。入力拒否時は更新用一時ファイル・backupも作らず、外部piを呼ばない。I/O障害時はSpecで許可した完成済みmodels/一意backupのみを差分として除き、残り全体を比較した。ネットワークはテスト所有listenerだけを使い、実キー・課金API・共有HOMEを使っていない。

対照は一意な/tmp隔離worktreeだけで行い、feature worktreeのguardは外していない。対照後に実helperへ戻して235件の成功を確認し、worktreeを外して親ディレクトリも削除した。最初の再現用worktreeも削除済み。検証ログは一時領域へ閉じ込め、要点をこの節へ転記した後に削除する。

残る確認: rebuild・共有コンテナとの交互rebuild、実provider/ADC、実ポート範囲でのPlannotator、Windowsブラウザーの往復、Windows側ポート所有者とforwardPortsの因果関係は未確認。O-M1/O-U1の原因を推測で断定せず、PRの既知の制限に残す。shrinkwrapやmanifest-only表示helperの残存、複数ファイルI/O失敗時の部分更新もPRで保証しない。

所要（commit前の集計）: 約20分。準備・全指摘の照合/再現約6分、Spec・実装・回帰約6分、通常/tmpの全体検証約7分、自己レビュー・記録約1分。公開・後片付けの時間は最終コメントと報告に記録する。

## PR #141 settings 更新のレビュー修正（2026-10-18、完了）

- 状態: `completed`。結論は **1: 修正して push**（マージしない）。今回も `/skill:review-fix-planning #141` を既存 PR への修正・検証・push の実行許可として扱い、内容の承認とは区別する。
- 入力: 同じレビュー directory の4ファイル。SWE/Opus/Grok は `52cc4a0456d2`、GPT は `60bcb6247e06`。両方とも取得した現行 PR head `52cc4a0456d21a104d23f66c05d8751ddc121d63` の祖先。clean かつ先端一致の既存 feature worktree を再利用する。
- 現行 Spec/Plan を repo・Issue/PR・テーマで照合し、この Spec のみを更新する。別世代の Spec は作らない。
- 再現: SHA照合済みの隔離 worktree で実 `remove_pi_mcp_adapter` を実行すると、symlink / hardlink の settings は終了0で別 inode の通常ファイルになり、共有先には `-builtin:mcp` が残る。隔離 worktree と親 directory は再現終了後に削除した。
- 全47変更の現行ファイル、削除元（旧cleanup・JSON helper・旧テストを含む）、関連処理・呼出元・テストを確認した。他 worktree の差分は取り込んでいない。読み取り専用の `sp-recon` / `sp-research` は同期呼出しが結果無しで返り、成功扱いせず controller が全調査と自己レビューを行った。

### 今回の全指摘の分類

S=SWE、O=Opus、G=GPT、K=Grok。active/resolved の指摘15件と、独立した未検証候補4件の **計19件: 解消済み12 / 対応する1 / 対応しない6**。見出し以外の test suggestion は同じ項目の検証案であり重複加算しない。以下の解消済みは検証開始時の現行 HEAD `52cc4a0` に対する判定であり、今回直した K-M2 を解消済みに付け替えて数えない。

| ID | 元の指摘・候補 | 分類 | 根拠・確認 |
|---|---|---|---|
| S-M1 | DeepInfra の偽成功 | 解消済み | `scripts/setup_pi.zsh:2` の errexit と helper の preflight。provider回帰78件が成功 |
| S-L1 | shrinkwrap / 隠しlock / manifest-only helper の検査縮小 | 対応しない | installerはrootの2manifestと登録済みhelperだけを見る。Spec D-2の意図した範囲縮小で、表示helper残存だけでは致命的な処理停止にならず、PRに制限・手動確認を記載済み |
| S-L2 | models の固定tmp・mode・リンク | 解消済み | helper `plain_file` / `stage` とmode保持が存在。provider回帰で共有先・mode・残骸を検査し成功 |
| S-I1 | /tmp worktree で移行テスト不能 | 解消済み | private tmp後のrepo再bind。今回も/tmpの138回帰が成功し、正常fragmentも実行できた |
| O-M1 | forwardPorts による Plannotator bind 競合の疑い | 対応しない | 全10portのEADDRINUSEとLinuxにlistener無しを再確認。Windows側所有者・転送との因果関係は未確認で、設定変更を正当化しない。既存PRの制限と一時port/手動転送の回避方法を維持 |
| O-I1 | Vertex の一覧/project 固定値 | 対応しない | 現ランチャーと期待値は一致し実行不具合ではない。テスト設計の論点として既存の判断を維持 |
| O-L1 | /tmp不可視・境界テストの空振り | 解消済み | S-I1と同じ実行根拠。境界診断・正常対照・前後状態の既存assertionも維持 |
| O-L2 | DeepInfra の偽成功 | 解消済み | S-M1と同じ実setup回帰 |
| G-M1 | models の0600→0644 | 解消済み | `stage` と既存mode保持、新規0600。別providerの合成keyを保持する実setup回帰成功 |
| G-M2 | ~/ によるcwdへの誤保存 | 解消済み | 3setupのmkdirより前のHOME展開。絶対/相対/~/~の18実行ケース成功 |
| G-M3 | DeepInfra の偽成功 | 解消済み | S-M1と同じ実行根拠 |
| G-M4 | BOM付きmodels/authの拒否 | 解消済み | `load_object` はutf-8-sig。BOM有無の3setup実行回帰成功 |
| K-M2 | settings の共有リンク切断 | 対応する (a) | 実MCP関数がsymlink/hardlinkを別inodeへ置換し終了0。通常rebuildで了承のない設定共有の変更になる。下記F-5の設計見直しで修正 |
| K-H1 | ~/ 配下の資格情報の誤保存 | 解消済み | G-M2と同じ。OpenCodeの合成authはHOME側だけに保存されmode0600 |
| K-M1 | DeepInfra の偽成功 | 解消済み | S-M1と同じ実行根拠 |
| S-U1 | 移植元privateのため一致を検証できない | 解消済み | 今回はGitHub APIで固定SHA `715d981` のtree/installerを読み取り専用取得できた。初回コミット `a24dc66` の32blob SHAとPi導入節が全一致。現行は安全修正の例外があるというPRの説明も正しい |
| S-U2 | rebuild/実共有HOME/ADC/Windowsの受け入れ | 対応しない | Spec受入条件6で初めから別枠の実機確認。offlineの共有登録・親子argv/auth/native SDK境界は全回帰で成功し、実環境障害の根拠ではない。実機未実施を維持し成功と書かない |
| S-U3 | catalog更新失敗がwarnだけ | 対応しない | 合成Piでrefresh終了7を注入し、既存の正しいmodel行があれば終了0、欠落なら終了1・完了表示無しを実行確認。後段の厳密なprovider/model照合は機能し、refreshだけの非致命化は仕様 |
| O-U1 | 別containerの転送との競合候補 | 対応しない | O-M1と同じ観測で、占有元との因果関係の根拠無し。転送・他者サービスは変更しない |


### 守る条件の設計（F-5 の適用経路の見直し）

前回 `52cc4a0` は provider setup の models/auth だけを対象として installer の settings を表から外した。同じ「共有リンクや特殊ファイルを暗黙に置換しない」条件の2回目なので、点のガード追加だけではなく、repository が直接更新する Pi JSON の境界を見直す。

守る条件: models/auth/settings が単一リンクの通常ファイルまたは未作成であり、更新に必要な JSON 構造を検査できるまでは、その更新処理が管理する設定・共有先・manifest・backup・staging・外部 Pi 呼出しを変更しない。I/O 障害では完成済みの先行操作までの巻き戻しは保証せず、未使用 staging を掃除し、対象を途中まで書かない。Pi と他 setup を止めて実行する前提を維持し、同時更新の race は保証しない。

| 守る条件 | 経路・停止位置 | 変更前の挙動 | 判定 | 確かめる方法 / assertion |
|---|---|---|---|---|
| F-5 | provider helper の models/auth、新規・更新・変更なし、backup/staging/置換 | preflight と一意 staging が存在 | 既に満たす。共通 `plain_file` / `load_object` / `stage` を維持 | provider 78回帰、拒否前後の全状態とmode/link数 |
| F-5 | installer の Pi 導入開始→extension replacement/retirement/install | settings の安全確認前に外部 Pi が設定を変更し得る | 修正する。Pi節の先頭で同じ helper による settings preflight | Pi節の実 fragment + fake npm/pi で、拒否時の全状態・外部呼出し無し |
| F-5 | MCP migration の list/remove前 | settings検査はremove後、statでリンクを追う | 修正する。同じ helper のpreflightを外部Piより前に行う | 実関数で各1異常、全状態比較、リンク/共有先/manifest/audit不変 |
| F-5 | MCP cleanup の再読込→serialize→stage→replace | inline独自writer、異常時tmpが残り得る | 修正する。providerと同じ検査・stagingにまとめ、再読込してPi変更後のpackagesを保持 | 通常/BOM/欠落/no-op/再実行、入力拒否、fsync/replace障害の全状態比較 |
| F-5 | Vertex auth overlay | host authを置換せずnamespaceにread-only overlay、未作成のみ新規配置 | 既に満たす。共有先の既存内容を変更しない | 既存Vertex回帰のhost auth/state比較 |
| 対象外 | 実Pi内部のsettings lock・npm操作、tier設定、models雛形初回配置 | Pi内部の保存や別の入力・初回操作 | 対象外。外部CLI内部の実装は変更せず、Pi節入口の事前拒否で共有settingsを渡さない | 現行の回帰を維持。transaction/並行更新を保証しない |

案の比較: (1) inline Python に lstat だけを足す案は外部 `pi remove` が先行し、provider との適用漏れも繰り返すため不採用。(2) 既存の小さな JSON 更新 helper に settings preflight/cleanup を加え、同じ storage guard・BOM reader・staging を使う案を採用。歴史的なファイル名は呼出元互換のため維持する。(3) 共有リンク切断を既知の制限として許容する案は通常の rebuild による了承のない変更を残すため不採用。旧cleanupの全manifest検査・汎用移行機能は復活させない。

テストは再現した実行挙動・安全条件に必要なものだけ27件追加した。文書の検査はdiff・参照先と構文の確認に代えた。スキル本体は変更しておらずスキル全体pytestは追加の反映条件にしない。

### 今回の検証・失敗時の検証・自己レビュー

| 検証 | 結果 |
|---|---|
| RED（修正前の実関数・Pi導入fragment） | symlink/hardlinkの4例と導入前preflightの4例、計8件が誤った終了0を検出し失敗 |
| MCP / provider / isolation の関連回帰 | 136 passed / exit 0 |
| `/tmp` のHEAD照合済みworktreeへ修正をコピーして上記と共有登録を実行 | 138 passed / exit 0 |
| 共通storage guardだけを外した隔離対照 | settingsの9例 + models/authの12例、計21/21が失敗（exit 1） |
| MCPの外部Piより前のpreflightだけを外した隔離対照 | FIFO以外の単一異常16/16が失敗（exit 1）。FIFOを対照で開いて待ち続けさせず、実guardのFIFO拒否自体は通常回帰で確認 |
| 対照を復元した同worktree | 138 passed / exit 0。検証worktreeを外し、結果転記後に親directoryごと削除 |
| `PI_CODEX_LIVE_CHECK=0 PI_OFFLINE=1 UV_OFFLINE=1 bash .devcontainer/run-tests.bash` | 32/32 PASS / exit 0。migrations入口も成功し、現行の収集数は262件（従来235 + 新規27） |
| `bash scripts/check-layout.sh` | PASS / exit 0 |
| shell構文・変更PythonのAST・`git diff --check` | PASS / exit 0 |
| 移植元・catalog候補 | 初回32blobと導入節一致。refresh失敗/モデル有無の2例が意図した終了状態 |

不正入力は MCP の9種類（symlink・切れたsymlink・hardlink・directory・FIFO・JSON構文・object形・extensions形・packages形）×登録有無2条件の18例、Pi導入前4例の計22例を実行した。各負例は異常1つだけ。処理前からのsnapshotと、テスト所有root全体（HOME/settings、共有先、npm manifests、backup/stagingの有無、bin/fragment、外部Pi/npmのaudit）の種類・バイト列・mode・link先・link数が一致することを確かめた。構文エラーに合成secretを入れ、診断に内容を表示しないことも確認した。

fsync/replaceを個別に失敗させた2例では、設定本体・共有先以外も含む同じ状態全体が一致し、stagingが残らない。通常/BOM/再実行で既存modeと他の設定を保持する。欠落/空object/変更不要の3例はpreflight・cleanupの両modeで作成も再保存もしない。MCPの外部remove後は最新のpackagesを再読込し、古いsnapshotで登録を復活させない。外部removeが既に成功した後のI/O障害は、その完了した操作まで巻き戻さない。

自己レビューはcontrollerが1回、(1)F-5全経路への反証（既存/欠落/変更不要/拒否/外部remove後/各I/O停止位置）、(2)PR全体の差分・現行ファイルと削除元・呼出元、(3)検証の検出力（全状態・単一異常・21/16の対照・テスト採用基準）を確認した。追加の致命的指摘0件、追加の対応しない指摘0件。自己レビュー後のコード修正・2回目のレビューは無い。未実施の実機確認を解消したという意味ではない。

実機rebuild・共有containerとの交互rebuild・実provider/ADC・Windows側のport所有者と実ブラウザー到達は未実施。元の受け入れchecklistと既知の制限を維持する。利用者のHOME/認証・他者サービスは変更していない。

今回の所要（公開前、概算）: 約17分。準備/全入力照合・再現3分、設計/実装/回帰3分、全体/隔離対照検証6分、全文確認/候補検証/自己レビュー4分、記録1分。公開・片付けの結果はPR状況コメントと完了報告にだけ残し、記録専用commitは追加しない。

## PR #141 パス解決・Vertex共有authのレビュー修正（2026-10-18）

- 状態: `completed`。結論: **1: 修正して既存PRへpush**。`/skill:review-fix-planning #141 --hold-action skip` を同PRの修正・検証・pushの実行許可として扱う。`--hold-action` は本スキルに定義がなく独自の保留処理は追加しない。内容の承認・rebuild・実認証・マージの実施とは区別する。
- 現行HEAD: `3ec1d06e04a46124b5389c4863c57d4229418cd3`。同テーマの既存Spec/Planを内容で照合し、このSpecを更新する。cleanかつPR先端一致の既存feature worktreeを再利用し、片付けない。
- 入力: `reviews/#141-feat-issue-125-pi-workspace-parity/` 配下の全6ファイル。`Grok-4.7.md` / `SWE-2-Max.md` / `claude-opus-5-5.md` / `commandcode-deepseek-deepseek-v4.1-flash.md` は `3ec1d06e04a4`、`gpt-6.1-sol.md` は `60bcb6247e06`、`grok-4.7.md` は `52cc4a0456d2`。全対象HEADの祖先照合に成功。大小文字の異なるGrokの2ファイルを別入力として扱う。
- 調査委譲2件は同期呼出が結果なしで戻った。結果を再確認できるレポートも返らず、成功や読了には数えずcontrollerが引き継ぐ。

### 全入力の分類

N=Grok（大文字ファイル）、S=SWE、O=Opus、G=GPT、K=grok（小文字ファイル）。active/resolved指摘と独立した未検証候補の計24入力は **解消済み13 / 対応する2 / 対応しない9**。自己レビューのSR-1を加えた最終25件は **解消済み13 / 対応する3 / 対応しない9**。test suggestionsは同じ指摘の検証案なので重複加算しない。

| ID | 指摘・候補 | 分類 | 現行HEADの根拠 |
|---|---|---|---|
| N-L1 | symlink authでVertexが起動しない | 対応する (a) | 実pigemf・実bwrap・合成authで終了1、通常ファイルは終了0。既存の共有authを読む対応経路で主要ランチャーがPi到達前に止まる |
| N-L2 | printf引数からoverlayが漏れる | 解消済み | 実zsh builtinを大きな合成payloadのpipeで待機させても子cmdlineはzshの起動引数のみ。外部printfのargvとは異なり、本体の秘密をargvへ載せない |
| N-L3 | ~userの検査先とPi更新先が異なる | 対応する (a) | 実MCP関数にliteral ~vscode配下の正常な共有settingsを渡すと検査をすり抜け、fake Piが共有先を変更して終了0。了承のない共有設定変更につながる |
| S-L1 | shrinkwrap/manifest-only helperの検出縮小 | 対応しない | D-2の意図した範囲縮小。表示helperの残存だけでは致命的な処理停止にならず、PRに制限と回避方法を記載済み |
| S-I2 | staging globが実名に一致しない | 対応しない | globの不一致は事実だが、同ファイルの全状態snapshotとI/O回帰が残存を検出。回帰ガード全体の欠落や現行の誤動作ではない |
| S-M1 | DeepInfraの偽成功（resolved） | 解消済み | setupのerrexitとhelper preflight、既存の不正入力実行回帰 |
| S-L2 | modelsのmode/link/固定tmp（resolved） | 解消済み | plain_file/stageと既存mode保持、一意backup、全状態の実行回帰 |
| S-I1 | /tmp worktreeで移行テスト不能（resolved） | 解消済み | private tmp後のrepo ro-bindと正常対照を維持 |
| S-U1 | rebuild/実共有HOME/ADC/Windows受入 | 対応しない | 当初から別枠の実機確認。offlineの保証と区別されており、未実施自体は現行欠陥の根拠ではない |
| S-U2 | catalog更新失敗のwarn継続 | 対応しない | refreshはbest effort、後段で実provider/modelの存在を確認。既存catalogで起動可能なら継続する仕様で、前回の実行対照も維持 |
| S-U3 | 非list settingsをPiが書く可能性 | 対応しない | 正常なpackages/extensionsは配列。helperは異常を副作用前に拒否する設計で、正規のPi出力を誤拒否する根拠なし |
| O-M1 | forwardPortsによるbind競合の疑い | 対応しない | ポート占有と設定との因果関係は確定しておらず、既知の制限と一時範囲/手動転送の回避方法を維持。推測で設定を変更しない |
| O-I1 | Vertex一覧/project固定値 | 対応しない | 現行と一致するテスト設計の論点で、現構成の実行不具合ではない |
| O-I2 | staging globの空振り | 対応しない | S-I2と同じ。致命的な修正に付随しないテスト整理は行わない |
| O-L1 | /tmp不可視と境界テスト空振り（resolved） | 解消済み | repo再bind・正常対照・境界診断の検査を維持 |
| O-L2 | DeepInfra偽成功（resolved） | 解消済み | S-M1と同じ |
| O-U1 | 別containerのポート転送と競合 | 対応しない | O-M1と同じ観測で、占有元との因果関係の根拠なし。他サービスは操作しない |
| G-M1 | modelsの0600→0644 | 解消済み | helperが既存modeを保持し、新規0600、他providerも保持 |
| G-M2 | ~/をcwdへ誤保存 | 解消済み | 3setupがmkdirより前に~・~/をHOMEへ展開 |
| G-M3 | DeepInfra偽成功 | 解消済み | S-M1と同じ |
| G-M4 | BOM付きmodels/authの拒否 | 解消済み | helperのutf-8-sig readerと実setup回帰 |
| K-M2 | settingsの共有リンク切断 | 解消済み | 3ec1d06が共通storage guardをPi導入前/MCP操作前へ適用。ただしN-L3の別のパス解決漏れは今回対応する |
| K-H1 | ~/の資格情報誤保存（resolved） | 解消済み | G-M2と同じ |
| K-M1 | DeepInfra偽成功（resolved） | 解消済み | S-M1と同じ |

Command Codeレビューは指摘/未検証候補0件。個別の誤動作を含まない未実施の実機確認はS-U1で記録する。

### 守る条件の設計・影響経路

N-L3は前々回F-2（書き手とPiの読み先の一致）の2回目であり、前回3ec1d06のsettings preflightがPython expanduserを導入したことでF-5を迂回する経路にもなった。前回は保存先の種類だけを集約し、パス解決を3つのheredocとhelperに残した点が足りなかった。今回の条件は、repositoryが対応するPOSIXパス（未指定/空/絶対/相対/~ /~/ /literal ~user）について、検査・manifest探索・cleanupがPiと同じファイルを扱い、不正なsettingsでは外部変更前に全状態を保持すること。同時更新・全操作rollbackは従来どおり保証しない。

N-L1の条件は、通常ファイルへのauth symlinkを保持したまま、Piが辿る実体へnamespace内だけのreadonly overlayを重ね、親子が同じoverlayを読むこと。ホストのauth・共有先・mode/link数は変えない。

| 条件 | 経路/停止位置 | 変更前の挙動 | 判定 | 確かめる方法/assertion |
|---|---|---|---|---|
| N-L3/F-2/F-5 | settings-check/cleanの既定/明示agent引数 | Python expanduserが~userを別HOMEへ展開 | 共通resolverへ集約して修正 | 各パス形式で実check/clean、fixture全体の変更が実対象だけであることを確認 |
| 同上 | MCP/distill/lensのmanifest解決 | 3つのheredocが同じ誤展開 | 同じresolverのCLIへ集約 | 各実関数でliteral ~userのmanifest-only撤去・事後残存拒否 |
| 同上 | subagentsのmanifest検査 | HOME固定でcustom agentと異なる | 同じresolverへ集約 | 実関数のcustom/literal ~userのmanifest-only撤去・拒否 |
| 同上 | Pi導入開始/MCP remove前/cleanup再読込 | 誤ったsettingsが正常なら外部Piが先行 | 同じパス規則でpreflight | symlink/hardlink/JSON異常各1条件でroot全体snapshot一致、外部audit無し、誤展開へ戻した対照は失敗 |
| 同上 | 3provider setup・Codex/xAI/Vertexのパス解決 | ~・~/のみ展開、~userはliteral | 既に満たす。規則を照合し既存回帰維持 | provider/Vertex/Codex実行suite。URI入力への対応追加は行わない |
| N-L1 | auth読取→mount先→親子Pi | symlinkをbwrapに渡し起動失敗 | mount先だけ実体の絶対パスへ解決 | 実bwrap、絶対/相対symlinkとhardlink、親子overlay/readonly、ホスト全状態保持 |
| N-L1 | 欠落auth/不正auth/dry-run | 既存は読取、欠落のみ0600作成、dry-runは無操作 | 既に満たす。挙動を維持 | 既存Vertex suiteで欠落/不正/並行起動/非auth状態保持 |
| SR-1/F-6 | 新しいパス回帰のhelper/check/clean/実関数subprocess、旧版・変異版の実行 | 異常なresolverがfixture外のHOMEを指してもOS境界が無い | 共通のtest-only namespace呼出へ集約 | readonly root・private tmp・repo ro-bind・fixtureだけrw・network/PID隔離。外側で書ける専用/mntは内側で書けず、readonlyだけを外した隔離対照で検出 |
| 対象外 | HOME固定のtierとmodels初回雛形 | 拡張の固定HOME仕様/従来の初回配置 | 従来の範囲を維持 | 既存導入suite。URI・Windows専用パスの対応を増やさない |

比較: (1)4箇所のexpanduserを各々置換する点の修正は再発を防げない。(2)既存JSON helperへ小さなagent path resolverとCLIを置き、全installerの探索先とsettings処理を同じ規則にする案を採用。(3)~userや相対パスを拒否して保証を狭める案はPiが扱う既存の保存先を不要に拒否するため不採用。Vertexはリンク拒否で保証を狭めるより、読み取り先とmount先を一致させる案を選ぶ。authの内容の再保存や共有方法の変更はしない。

### 自己レビューの裁定・再発の見直し

controllerが1回、反証（パスの全入口・リンク先と親子namespace）、PR全体（全変更ファイルと削除元、関連caller/テスト/文書）、検出力（単一異常、全状態snapshot、対照）を確認した。同期の調査委譲は結果が無く本体で引き継いだ。追加はSR-1の1件で、設計論点・文言整理だけの修正は追加しない。

| ID | 出どころ・指摘 | 分類 | 根拠・対応 |
|---|---|---|---|
| SR-1 | 自己レビュー: 新しいpath回帰の旧版/変異版にOS隔離がない | 対応する (a) | resolverをexpanduserへ戻すとfixture外の実HOME配下を指し、そこに同名settingsがあれば検証が変更し得る。以前のF-6と同じ検証境界の適用漏れ。全新規path subprocessをtest-only namespace helperへまとめ、fixtureだけを書込可にする |

守る条件は、resolverの正否・check/clean/migration/installの入口・拒否/成功/対照にかかわらず、検証がfixture外の設定・共有先・manifest・キャッシュ・外部通信を変更できないこと。以前のc35db31/e5a77a8/52cc4a0はlauncher installerの範囲だけを隔離し、新設したpath検証へその境界を引き継いでいなかった。各caseのPATH stubだけを増やす案は絶対パスの書込みを防げず不採用、namespaceを共通test utilityへ集約する案を採用、旧版/対照を止め検出力の保証を狭める案は不採用。外側で書ける専用/mntのfixtureを内側だけreadonlyにし、実領域に触れず独立して境界を確かめる。初回RED/対照で誤展開した実HOME直下の候補ディレクトリは読み取り専用の存在確認で全て不在だった。実HOMEへテストデータを作ったり削除したりはしていない。

SR-1は「自己レビューでの再発」として設計を見直して修正した。**この修正後は再レビューせず、検証だけをやり直す。** 実機rebuild/ADC/Windowsの未確認を、自己レビュー0件やテスト成功で解消扱いにしない。

### 実行チェックリスト・予算

- [x] 入力全件・HEAD・隔離worktreeのSHAを照合し、N-L1/N-L3とN-L2の反証を実行。再現worktreeと親directoryは削除済み。
- [x] 実行回帰を先に追加しREDを確認（テスト要: 実際の起動/保存境界の不具合）。最小修正後にGREEN。
- [x] 全経路の通常/負例と隔離対照を実行。文書/設定値だけのテストは追加しない。
- [x] 環境suite/layout/構文/diffを実行し、自己レビュー3観点を1回、SR-1を裁定して最終検証を完了。公開の結果はPR状況コメントに記録する。

### 最終検証・失敗時の検証

| 検証 | 結果 |
|---|---|
| 初回RED | 39新規ケース中21 failed / 18 passed。named/unknown tildeの誤解決、preflight迂回、4manifest経路の残存/偽成功、絶対auth symlinkのbwrap失敗を検出 |
| 修正後の関連6ファイル | 301 passed / exit 0（SR-1修正前）。/tmpのSHA照合済みworktreeへコピーした同じ6ファイルも301 passed |
| 最初のGREENでの診断assertion | 4件は実装の正しい相対パス診断に絶対パスを要求して失敗。期待値を与えたraw pathに直し、実装を変更せず解消。失敗を隠していない |
| path resolverをexpanduserへ戻した最終隔離対照 | 新設の6負例すべてが失敗 / exit 1。settings以外の状態や外部auditの変化も通常版では拒否する |
| test namespaceのreadonlyだけを外した隔離対照 | 1/1が失敗、専用/mntの書込みで終了83。変化するのはテスト所有fixtureだけ |
| 両対照を復元した/tmp worktree | 31 passed / exit 0。一時worktreeを外し、親directoryも削除済み |
| SR-1修正後のpath+MCP | 81 passed / exit 0 |
| SR-1修正後の最終環境suite | `PI_CODEX_LIVE_CHECK=0 PI_XAI_LIVE_CHECK=0 PI_OFFLINE=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash .devcontainer/run-tests.bash` が32/32 PASS / exit 0。TMPDIRは一意な検証root内。migrationsは302件（元262 + 新規40）を収集し同入口で実行 |
| layout・bash/zsh構文・Python AST・diff | すべてPASS / exit 0。スキルを変更していないためスキル全体pytestは追加の反映条件にしない |
| ポート再確認 | 現在19432/19441の2個だけがEADDRINUSE、他8個はbind可能。別のephemeral loopbackも成功。以前の全10個の占有とは分けて記録し、Windows所有者/転送との因果関係やブラウザー往復は未確認 |

失敗時の6負例は、symlink/hardlink/不正JSONの各1異常をPi節入口とMCP操作前に与える。比較はfixture root全体の有無・バイト列・mode・種類・link先・link数で、HOME/settings、共有先、両npm manifest、backup/stagingの有無、bin/fragment、外部Pi/npm auditを含む。期待値は実行前snapshotから取得し、診断へ合成secretを出さない。通常版は全状態不変で外部callなし。check/cleanの8パス形式ではcheckが無操作、cleanは実対象settingsのextensions以外を変えずmodeを保持する。4つの実関数はcustom絶対/literal named tildeの双方でmanifest-only撤去と撤去後の残存拒否を確認。Vertexの絶対/相対symlink・hardlink×3launcherは、実bwrapとnative auth consumerの親子でmarker/他provider/readonlyを確認し、ホストroot全体のsnapshotが一致した。

新しいI/O処理は加えず既存stage/replaceを維持する。既存fsync/replace障害・BOM・不正構造・欠落/no-op・provider拒否の回帰も最終suiteで通る。複数ファイルや完了済み外部操作のrollback、並行更新の排他は従来どおり保証しない。自己レビュー後のSR-1修正は再レビューしていない。実機rebuild、実provider/ADC、Windowsブラウザーは未実施。private Actionsは規約により確認対象外。

公開前の所要は概算33分（入力/範囲固定・再現8、設計/実装7、実行検証11、全文確認/自己レビュー/記録7）。検証の既知の失敗を再試行で隠していない。2件の調査workerは結果なしで戻り、同条件の再試行はしていない。

今回の能動時間の目安は60分（調査/再現15、実装10、検証20、自己レビュー/記録/公開15）。同期workerは結果なしを成功扱いせずcontrollerへ切替、同条件再試行なし。検証の既存タイミング失敗は原因を確認したうえで再試行1回まで。安全失敗は停止。RED後/全体検証後/公開前にcheckpointを置き、全体の汎用移行処理を復活させず今回のpath/mount境界に絞る。実機rebuild・API/ADC・Windowsブラウザーは実施しない。

## PR #141 解決済みパスの再解釈の修正（2026-10-18）

### 範囲・実行許可・現行文書

- 状態: `completed`。結論は **1: 修正して既存 PR へ push**。利用者の「通常どおり、レビュー結果を確認して、問題があれば、修正」「プッシュして、PRを投稿」を実行許可とし、先の全作業スキップ指定を取り消す。新しい PR は作らず、既存 #141 へ結果コメントを投稿する。内容の承認・マージ・rebuild・実認証は行わない。
- 対象: `usaturn/create-reso-world` PR #141、Issue #125、開始 HEAD `e35fb6b89c9dadb217a6ec72caf360f6208e936a`。同じテーマの現行 Spec/Plan はこの文書と既存 Plan だけであり、この Spec を更新する。clean かつ先端一致の既存専用 worktree を再利用する。
- 入力は `reviews/#141-feat-issue-125-pi-workspace-parity/` の全7ファイル。N=`Grok-4.7.md`、S=`SWE-2-Max.md`、O=`claude-opus-5-5.md`、D=`deepseek-deepseek-v4.1-flash.md` は `e35fb6b89c9d`、C=`commandcode-deepseek-deepseek-v4.1-flash.md` は `3ec1d06e04a4`、G=`gpt-6.1-sol.md` は `60bcb6247e06`、K=`grok-4.7.md` は `52cc4a0456d2`。全対象 HEAD が取得した現行 PR head の祖先であることを確認した。
- 同期の調査委譲2件（sp-recon / sp-research）は結果もレポートの参照先も返らず、成功・読了には数えない。同条件で再試行せず controller が調査・実装・検証を引き継ぐ。

### 全入力の分類

active/resolved 指摘と独立した未検証候補は **計27件: 解消済み15 / 対応する1 / 対応しない11**。test suggestions は同じ指摘の検証案なので重複加算しない。C は指摘0件。今回修正する O-I3 を「解消済み」へ数え直さない。

| ID | 指摘・候補 | 判定 | 開始 HEAD での根拠 |
|---|---|---|---|
| N-L1 | symlink auth で Vertex が起動できない（resolved） | 解消済み | mount 先を `${auth_file:A}` とし、実 bwrap の絶対/相対 symlink・hardlink と親子の回帰が成功 |
| N-L2 | builtin printf の引数に overlay が露出（resolved） | 解消済み | 現行は zsh builtin と FD 3 を使用。外部 printf の argv とは異なるという前回の対照を維持し、外部コマンド化していない |
| N-L3 | installer の ~user 展開が Pi とずれる（resolved） | 解消済み | resolver は ~ / ~/ だけを展開。named/unknown の実 check/clean・manifest 回帰が成功 |
| S-L1 | npm 残骸検査の対象縮小 | 対応しない | D-2 の意図した範囲縮小。表示 helper の残存だけでは致命的でなく、PR に制限と手動除去手順がある |
| S-I2 | staging glob が実名と一致しない | 対応しない | 不一致は事実だが全状態 snapshot と I/O 回帰が残存を検出し、回帰ガード全体の欠落ではない |
| S-M1 | DeepInfra の偽成功（resolved） | 解消済み | errexit と共通 preflight、実 setup の不正入力回帰が成功 |
| S-L2 | models の mode/link/固定 tmp（resolved） | 解消済み | plain_file/stage と mode 保持、一意 backup、共有先を含む実行回帰が成功 |
| S-I1 | /tmp checkout で移行テスト不能（resolved） | 解消済み | repo 再 bind と cwd 固定を維持し、今回の /tmp worktree で302件成功 |
| S-U1 | rebuild/共有 HOME/ADC/Windows の受け入れ | 対応しない | 当初から別枠の実機確認。未実施を維持し、ローカル成功と同一視しない |
| S-U2 | catalog 更新失敗が warn のみ | 対応しない | refresh 終了7で、モデル行が残る対照は終了0、モデル行無しは終了1・完了表示無しを再確認。後段の検証は機能する |
| S-U3 | 非 list settings が Pi の正規出力か | 対応しない | packages/extensions は配列を受理し、非配列を副作用前に拒否する仕様。正規出力を誤拒否する根拠がない |
| S-U4 | 相対 agent dir を別 cwd から使うと保存先が変わる | 対応しない | 相対パスは起動時 cwd 基準という Pi と同じ仕様。installer 内は同じ cwd で処理し、絶対パスなら cwd の違いを避けられる |
| O-M1 | forwardPorts による Plannotator bind 競合の疑い | 対応しない | 今回全10ポートが EADDRINUSE、Linux listener 無しを観測したが、Windows 所有者と転送との因果関係は未確認。PR の既知の制限と一時ポート/手動転送の案内を維持する |
| O-I1 | Vertex 一覧/project をテストに転記 | 対応しない | 現構成と一致するテスト設計の論点で、実行不具合ではない |
| O-I2 | staging glob の空振り | 対応しない | S-I2 と同じ。非致命的なテスト整理は追加しない |
| O-I3 | ./~ パスの解決結果を渡し直すと HOME 側を更新 | 対応する (a) | `PI_CODING_AGENT_DIR='./~/x'` で実 MCP 関数が終了0、選択先の -builtin:mcp を残し、別の `$HOME/x/settings.json` を書き換えることを隔離 fixture で再現。サポートする相対パス入力で誤ったファイルへ操作するため、頻度や Info ラベルによらず対応する |
| O-L1 | /tmp 不可視と境界テストの空振り（resolved） | 解消済み | repo 再 bind・正常対照・拒否診断を維持。今回も isolation 全件成功 |
| O-L2 | DeepInfra の偽成功（resolved） | 解消済み | S-M1 と同じ |
| O-U1 | 別コンテナの転送との競合 | 対応しない | O-M1 と同じ観測で、占有元は確定できない。他者サービス・転送は変更しない |
| G-M1 | models の0600→0644 | 解消済み | 既存 mode と他 provider の保持、新規0600の実 setup 回帰が成功 |
| G-M2 | ~/ を cwd に誤保存 | 解消済み | 3 setup が mkdir より前に ~ / ~/ を HOME へ展開し、実行回帰が成功 |
| G-M3 | DeepInfra の偽成功 | 解消済み | S-M1 と同じ |
| G-M4 | BOM 付き models/auth を拒否 | 解消済み | utf-8-sig reader と BOM 有無の実 setup 回帰が成功 |
| K-M2 | settings のリンク切断 | 解消済み | Pi 導入前・MCP 操作前・cleanup の共通 storage guard と全状態回帰が成功。O-I3 は別の再解釈経路として対応 |
| K-H1 | ~/ の資格情報誤保存（resolved） | 解消済み | G-M2 と同じ |
| K-M1 | DeepInfra の偽成功（resolved） | 解消済み | S-M1 と同じ |
| D-L1 | dangling auth symlink の起動失敗と汎用診断 | 対応しない | 未作成の共有先という不完全な構成で、現行 overlay が終了1・stdout空・ホスト全状態不変を確認。リンク先の自動作成や診断の詳細化は仕様/利便性の論点で、正常な共有 auth の回帰ではない |

### 守る条件の設計と再発の見直し

O-I3 は e35fb6b が導入した resolver の再解釈による回帰で、F-2（書き手と Pi の読み先の一致）の再発でもある。前回は tilde の展開規則だけを共通化し、`Path('./~/x')` が先頭 `./` を落とした文字列を再入力すると「未解決の ~/」と区別できなくなる状態を検討できていなかった。

守る条件: 対応する POSIX パスの未解決入力を1回だけ展開し、同じ cwd の検査・npm manifest 探索・cleanup は常に同じ保存先を扱う。解決結果は絶対パスとして受け渡し、何回渡し直しても選択先が変わらない。symlink や `..` の OS の辿り方は勝手に正規化しない。不正な選択先では、設定・共有先・manifest・backup/staging・外部 audit を変える前に拒否する。

| 守る条件 | 経路・停止位置 | 変更前の挙動 | 判定 | 確かめる方法 / assertion |
|---|---|---|---|---|
| 解決の冪等性 | `agent_directory` の未指定/空/絶対/相対/~ /~/ /named /unknown /./~ /./~/x | 相対 Path の表示で ./ が落ち、次の入力で意味が変わる | 修正する。1つの resolver が全分岐で絶対 Path を返す | 実 CLI の直接入力と `--agent-dir` 出力の再入力で、同じ settings だけを更新。別 HOME の decoy を含め全状態比較 |
| 同上 | `--settings-check` の env/明示引数、`--settings-clean` の env/明示引数 | 直接入力と再入力で検査先/書込先が異なる | 同じ resolver で修正 | check が無操作、clean が選択先の extensions 以外を保持。二度目の解決も同じ保存先 |
| 同上・拒否前の状態保持 | Pi 節先頭の preflight、MCP の解決→preflight→list/remove→再読込→cleanup | 先頭では正しく拒否しても、MCP 単独の再入力は別 HOME を検査する | 同じ resolver で修正。外部操作の順序は維持 | 各入口の symlink/hardlink/不正 JSON 各1異常で fixture 全状態一致、呼出 audit 無し。中心の絶対化だけを外した対照で MCP の3負例が失敗すること |
| 同上 | subagents/MCP/distill/lens の4つの manifest 探索と事後残存検査 | shell は相対の ~/ を literal 扱いする | 共通 CLI の絶対化を全4経路で使う | 各関数を絶対/named/./~/x で実行し、manifest-only 撤去と残存拒否を確認 |
| OS の保存先を保持 | symlink を含む相対 path/.. | OS の symlink→.. の順で辿る | 保持。resolve/abspath で symlink や .. を潰さない | symlink 親を含む相対パスの直接/再入力を実行し、選択先と decoy の全状態を比較 |
| 同じ入力規則 | 3 provider setup の PI_DIR と helper.setup | zsh が1回展開し Path を直接 setup に渡す。再解釈しない | 既に満たす。変更しない | provider の全既存回帰を再実行 |
| 同じ入力規則 | Codex/xAI の auth 読取、Vertex の起動時絶対化/子 cwd | それぞれ1回展開。Vertex は親で絶対化済み | 既に満たす。変更しない | Codex/superagents/Vertex の既存実行回帰を維持 |
| 対象外 | HOME 固定の tier と models 初回配置、URI/Windows 専用パス、並行更新 | 拡張仕様/従来の別経路 | 対象外。保証を拡大しない | 既存 suite を維持。排他/全操作 rollback は保証しない |

案の比較: (1) MCP の呼出しだけ変える点の修正は、解決結果が意味を失う共通 API を残すため不採用。(2) 共通 resolver が1回展開した絶対パスを返す形を採用し、全呼出元に同じ不変条件を与える。`.absolute()` を使い、symlink の解決や `..` の圧縮はしない。(3) 相対パスを拒否して保証を狭める案は、Pi が扱う指定を不必要に拒否するため不採用。新しい汎用移行処理や旧 cleanup の復活は行わない。

### 実行チェックリスト・検証

- [x] 全7レビュー、対象 HEAD、共通 context、PR 先端、再利用 worktree の clean を確認。
- [x] 変更48ファイルの現行内容と削除元、関係する呼出元・テスト・既存 Spec/Plan を読む。隔離 worktree で302回帰成功、O-I3 と未対応候補の対照を確認。再現用 worktree と親 directory は削除済み。
- [x] 27件の分類、再発の根拠、全呼出経路と代替案をこの既存 Spec に記録。文書だけのテストは不要。
- [x] 回帰テストを先に変更し RED を確認。テスト要: 実 CLI と installer 関数による対象設定の変更/保持/拒否を検証する。
- [x] 共通 resolver の構造を修正し、全経路の GREEN と中心境界の隔離対照を確認。
- [x] migrations・環境 suite・layout・構文/AST・diff を実行。スキルの変更は無く、無関係なワールド/fork 全体の検証は追加しない。
- [x] 反証・PR全体・検出力を1回だけ自己レビューし、追加指摘0件を確認。自己レビュー後のコード修正・2回目のレビューは無い。
- [x] Spec を completed にし、件数・参照先・保証と PR の記載を照合。公開時は先端再確認、commit、Gitleaks、同一 SHA の push と状況投稿を行い、結果は状況コメントにだけ残す。

事前検証: `/tmp` の SHA 照合済み worktree の migrations 6ファイルは **302 passed / exit 0（142.68秒）**。catalog の best-effort 更新はモデル有無で期待する終了状態を確認。dangling auth の拒否ではリンク・共有先を含む全状態を保持。ポートは全10個 EADDRINUSE、Windows 所有者・転送との因果関係は未確認のまま。実機 rebuild、実 provider/ADC、Windows ブラウザーは実施しない。

今回の目安は45分（調査/分類15、実装/回帰10、検証/自己レビュー/記録/公開20）。既存の Issue 実装予算とは別の review-fix 作業であり ledger は追加しない。同条件の失敗した委譲は再試行しない。同期の検証が戻るまで待ち、結果無しを成功扱いしない。

### 最終検証・失敗時の検証・自己レビュー

| 検証 | 結果 |
|---|---|
| 追加前の現行 HEAD、隔離 worktree の6ファイル | 302 passed / exit 0 |
| テストを先に変更した RED | 5 failed / 54 passed / exit 1。誤った HOME への更新2例と preflight 迂回3例を検出 |
| 修正後の path/MCP/provider | 187 passed / exit 0（38.55秒） |
| 修正済みファイルをコピーした SHA 照合済み /tmp worktree の path 回帰 | 59 passed / exit 0（15.54秒） |
| 絶対化の1行だけを外した隔離対照 | 対象の5/5が失敗 / exit 1。うち拒否の3負例すべてが全状態比較で失敗し、2正常例は誤ったファイルの更新を検出 |
| 対照を復元した同 worktree | 59 passed / exit 0（23.95秒）。worktree を外し親 directory も削除済み |
| 最終 migrations 全6ファイル | 330 passed / exit 0（154.55秒）。元302件に実行ケース28件を追加 |
| 最終環境 suite | `PI_CODEX_LIVE_CHECK=0 PI_XAI_LIVE_CHECK=0 PI_OFFLINE=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash .devcontainer/run-tests.bash` が32/32 PASS / exit 0。TMPDIR は一意な検証 root 内 |
| layout・bash/zsh 構文・Python AST7ファイル・diff | すべて PASS / exit 0 |

path の59例は、11形式×直接/再入力の22例、2種類の相対 tilde×2入口×3異常の12負例、4関数×3パス形式×撤去成功/残存拒否の24例、fixture 外 readonly 境界の1例である。通常例は選択した settings の extensions 以外を変えない期待値を実行前 snapshot から作り、HOME の別設定（decoy）や symlink 親を含む別経路も比較する。check/CLI 出力は何も更新しない。各負例には symlink・hardlink・不正 JSON のどれか1異常だけを与え、HOME/settings、共有先、両 npm manifest、bin/fragment、backup/staging、外部 pi/npm audit の有無・バイト列・mode・種類・リンク先・link数を全て比較した。入力拒否の前に外部コマンドが走った場合も audit の差分で検出する。

中心境界の対照は `.absolute()` だけを外し、実装用 worktree の guard は一度も外していない。変異版にも既存の readonly root/private tmp/fixture のみ rw/network・PID 隔離を適用した。不正 JSON の負例が stderr だけで失敗しないよう、全状態比較を診断の照合より先に行い、実際に外部 list の audit を検出した。新しい I/O 処理は追加せず、既存の fsync/replace 障害回帰も通過した。完了済み外部操作の rollback・並行更新の排他は保証しない。

controller が1回、(1)全 resolver 入口と全4 caller、旧版との差、symlink/.. と別 HOME への反証、(2)PR 全体の変更内容・現行ファイル/削除元・呼出元・文書の保証、(3)全状態 assertion・単一異常・5件の対照・隔離 utility・テスト採用基準の3観点で自己レビューした。追加指摘0件、自己レビュー後のコード修正は無い。2回目のレビューはしない。実機受け入れ・Windows 側ポートの所有者の未確認を解消したという意味ではない。

公開準備まで約22分（準備/全文確認/再現7、設計/実装2、検証10、自己レビュー/記録3）。開始は2026-10-18T04:03:20Z。公開と片付けの結果・総所要時間は最終コメントと報告に残し、この Spec に記録専用コミットは足さない。

## PR #141 Pi の字句的パス解決への一致（2026-10-18）

### 範囲・実行許可

- 状態: `completed`。今回の `/skill:review-fix-planning #141` を、同 PR の修正・検証・既存 head への push の実行許可とする。結論1を選び、マージ・実認証・rebuild は行わない。内容の承認・実機受け入れの完了とは区別する。
- 開始 HEAD: `f61289e62619edd0b963f6687ee5b8f86079f204`。既存の clean な専用 worktree、同じ Spec/Plan を再利用する。他 worktree の未コミット差分は読まない。
- 入力8ファイル: N=`Grok-4.7.md`、P=`openai-codex-gpt-6.1-sol.md`、S=`SWE-2-Max.md`、O=`claude-opus-5-5.md` は `f61289e62619`、D=`deepseek-deepseek-v4.1-flash.md` は `e35fb6b89c9d`、C=`commandcode-deepseek-deepseek-v4.1-flash.md` は `3ec1d06e04a4`、G=`gpt-6.1-sol.md` は `60bcb6247e06`、K=`grok-4.7.md` は `52cc4a0456d2`。全 HEAD の祖先照合に成功した。
- SHA を照合した `/tmp` 隔離 worktree で、helper は `real/agent/settings.json` だけを掃除し、Pi の `FileSettingsStorage` が選ぶ `agent/settings.json` の共有リンクを検査しないことを再現した。既存330回帰も成功し、現行 `symlink-parent` の誤った期待値が欠陥を固定していると確認した。再現用 worktree と親 directory は Spec 更新前に削除した。

### 全入力の分類

**計29件: 解消済み16 / 対応する2 / 対応しない11**。同一原因の N-M1 / P-M1 は入力として別々に数える。C は指摘0件。Test suggestions は対応する指摘の検証案として扱い、重複加算しない。

| ID | 指摘・候補 | 判定 | 開始 HEAD の根拠 |
|---|---|---|---|
| N-M1 | symlink/.. で settings と manifest の対象が Pi とずれる | 対応する (a) | `alias -> real/nested`、`alias/../agent` で別設定だけを書き換え、実対象の共有 settings を preflight が見逃す。誤った対象への操作に該当 |
| P-M1 | 同じパスによる共有 settings の事前検査迂回 | 対応する (a) | 同じ隔離再現。native `resolvePath(getAgentDir())` と helper の選択先が異なる |
| N-L1 | 既存 auth symlink の Vertex 起動失敗 | 解消済み | `${auth_file:A}` の mount、共有リンクと親子 overlay の既存回帰が成功 |
| N-L2 | builtin printf の argv への overlay 露出 | 解消済み | 現行も zsh builtin と FD 3。外部 printf への変更はなく、既存の反証根拠を維持 |
| N-L3 | ~user の誤展開 | 解消済み | ~ / ~/ だけを展開する共通 resolver、named/unknown 回帰成功。今回の .. は別の入力条件 |
| S-L1 | npm 残骸検査の対象縮小 | 対応しない | D-2 の意図した範囲縮小。表示 helper の残存だけでは致命的でなく、PR に制限と回避方法を記載済み |
| S-I2 | staging glob の不一致 | 対応しない | 全状態 snapshot と fsync/replace 回帰が残存を検出する。致命的なガード全体の欠落ではない |
| S-M1 | DeepInfra の偽成功 | 解消済み | errexit と共通 preflight、不正入力の実 setup 回帰成功 |
| S-L2 | models の mode/link/固定 tmp | 解消済み | plain_file/stage、mode 保持、一意 backup の実行回帰成功 |
| S-I1 | /tmp checkout の検証不能 | 解消済み | repo 再 bind と cwd 固定。今回も隔離 worktree の330件成功 |
| S-U1 | rebuild/共有 HOME/ADC/Windows の受け入れ | 対応しない | 当初から別枠の実機確認。未実施を維持し、ローカル結果と混同しない |
| S-U2 | catalog 更新失敗が warn のみ | 対応しない | refresh 終了7を注入し、モデル行ありは終了0、なしは終了1・完了表示なし。後段の検証が機能する仕様 |
| S-U3 | 非 list settings の拒否 | 対応しない | 正常な packages/extensions は配列。必要構造を外部操作前に検査する仕様で、正規出力の誤拒否を示さない |
| S-U4 | 相対 agent dir と別 cwd | 対応しない | 起動時 cwd 基準は Pi と同じ仕様。installer は同じ cwd。固定したい場合は絶対パスを使う |
| O-M1 | forwardPorts と Plannotator の bind 競合 | 対応しない | 今回も全10ポート EADDRINUSE。Windows 所有者・転送との因果関係を確定できず、推測で設定を変えない。PR の制限・一時範囲/手動転送を維持 |
| O-I1 | Vertex 一覧/project の転記 | 対応しない | 現構成で一致し実行回帰も成功。非致命的なテスト設計の論点 |
| O-I2 | staging glob の空振り | 対応しない | S-I2 と同じ |
| O-I3 | ./~ の再解釈による別 HOME 更新 | 解消済み | f61289e の絶対化と直接/再入力の回帰が成功。今回も1回だけの tilde 展開を保つ |
| O-L1 | /tmp 不可視と境界テストの空振り | 解消済み | repo 再 bind・正常対照・拒否診断、隔離 suite 成功 |
| O-L2 | DeepInfra の偽成功 | 解消済み | S-M1 と同じ |
| O-U1 | 別コンテナのポート転送との競合 | 対応しない | O-M1 と同じ。所有者不明のサービスや転送を操作しない |
| G-M1 | models の0600→0644 | 解消済み | 既存 mode/他 provider、新規0600を実 setup で検査し成功 |
| G-M2 | ~/ の cwd への誤保存 | 解消済み | 3 setup の ~ / ~/ 展開回帰成功 |
| G-M3 | DeepInfra の偽成功 | 解消済み | S-M1 と同じ |
| G-M4 | BOM 付き models/auth の拒否 | 解消済み | utf-8-sig reader と BOM 有無の実 setup 回帰成功 |
| K-M2 | settings の共有リンク切断 | 解消済み | 通常のパスは導入前/MCP前の storage guard と全状態回帰が成功。.. による対象ずれは今回の2入力として対応 |
| K-H1 | ~/ の資格情報の誤保存 | 解消済み | G-M2 と同じ |
| K-M1 | DeepInfra の偽成功 | 解消済み | S-M1 と同じ |
| D-L1 | dangling auth symlink の起動失敗と汎用診断 | 対応しない | 終了1・stdout空・ホスト全状態不変を再確認。不完全な保存先の自動作成/診断詳細化は仕様・利便性の論点 |

### 守る条件の設計と影響経路

F-2/F-5 の同じ条件の再発であり、f61289e の「OS の辿り順を保持する」設計判断が誤っていた。e35fb6b は tilde の展開だけ、f61289e は再入力の安定性だけを見て、native Pi の consumer と照合していなかった。前節の OS 順序を保持する設計は履歴であり、今回の設計に置き換える。

守る条件: 対応する POSIX 入力について、~ / ~/ を1回だけ展開し、cwd 基準の絶対パスへ字句的に . / .. を畳んでから I/O する。symlink を先に実体化しない。全 installer・provider setup・launcher の事前確認と、その後の Pi が同じ保存先を使う。再入力・子 cwd 変更で対象を変えず、不正な実対象なら設定・共有先・manifest・backup/staging・外部 audit を変更する前に拒否する。

| 条件 | 経路・停止位置 | 変更前の挙動 | 判定 | 検証 / assertion |
|---|---|---|---|---|
| F-2/F-5 | Python resolver と settings check/clean の env/明示/再入力 | absolute() は .. を保持し OS 側へ迂回 | 修正する。字句的絶対化を共通化 | native Pi の FileSettingsStorage の保存先と一致、実対象だけを更新、decoy を含む全状態比較 |
| 同上 | Pi 節入口、MCP の解決→preflight→list/remove→cleanup | 実対象が共有リンクでも正常な decoy を検査する | 同じ resolver で修正 | symlink/hardlink/JSON の単一異常×2入口、全状態不変・外部 audit なし |
| 同上 | subagents/MCP/distill/lens の manifest 探索・事後検査 | OS 側を grep、Pi は字句的対象を操作 | 共通 resolver で修正 | 4関数×撤去/残存拒否、Pi 選択先の manifest と decoy を比較 |
| 同上 | 3 provider setup の PI_DIR、helper.setup、OpenCode auth、後段 Pi | zsh は未正規化の文字列を渡し、別 models/auth を更新し得る | Python の --agent-dir へ集約 | 実3 setup の反映/拒否、別設定・共有先・backup・外部auditを比較 |
| 同上 | Codex/xAI の OAuth 読取、piccg/piccd の models 確認 | 生の alias/.. を OS に渡す | launcher 共通の字句的 resolver へ集約 | 有効な Pi 側/無効な decoy と逆の配置で起動/拒否を確認、全状態保持 |
| 同上 | Vertex の agent 絶対化→auth読取→mount→親子 | :A は字句的絶対化後に実体化し、この入力は既に一致 | 共通 resolver へ接続し、auth の mount 先だけ :A を維持 | 既存親子/共有auth回帰と alias/.. の native path 対照 |
| F-5 | serialization/stage/backup/replace の失敗位置 | 既存の検査・完成後置換・finally掃除 | 既に満たす。変更しない | 既存 provider/settings I/O 回帰。全操作 rollback/並行更新の排他は保証しない |
| 対象外 | HOME 固定の tier・models 雛形、URI/Windows パス | 拡張固有仕様/従来の別処理 | 対象外。保証を増やさない | 既存 suite を維持 |

比較: (1) settings の1行と期待値だけを直す案は同じ条件の setup/launcher を残すため不採用。(2) Python は既存 helper の resolver、zsh は既存 launcher helper の resolver へ集約し、native Pi を独立した比較先にする案を採用。(3) 相対パス/symlink 親を全面拒否して保証を狭める案は Pi が扱う構成を不必要に止めるため不採用。旧 cleanup や汎用移行機能は復活させない。

### 実行チェックリスト・検証

- [x] 全入力・現行 HEAD・祖先・context・既存文書・再現を確認。既存330回帰は終了0。
- [x] 行動テストを先に修正/追加して RED を観測し、同じ条件の全経路を修正する。テスト要: 実処理の保存先・拒否・変更/保持を確かめる。文書だけのテストは不要。
- [x] 全状態比較、中心の字句的正規化を外す隔離対照、関連回帰と環境 suite/layout/構文/diff を実行する。
- [x] 反証・PR全体・検出力の自己レビューを1回実施して判定を揃え、最終検証後に completed とする。Spec は公開前に1回だけ commit する。
- [ ] head/context再確認、検査付きpush、状況コメント。実機受入・Windows所有者の未確認は成功へ読み替えない。

調査委譲 sp-recon は同期呼出が結果・レポート参照なしで戻り、成功/読了に数えず controller が引き継いだ。同条件で再試行しない。

### 自己レビューの裁定・設計の見直し

読み取り専用 sp-review に反証・PR全体・検出力を1回依頼した。最初は git を使えないため判定前に NEEDS_CONTEXT と返った。controller が全文差分（削除元を含む9310行）・修正差分・base/head/全変更一覧を読取可能な artifact へ保存し、同じレビューを完了した。全差分の未読なし、追加2件を報告。controller が実行テストで **34 failed / 30 passed / 82 deselected** を観測し、2件とも採用した。最終分類は **計31件: 解消済み16 / 対応する4 / 対応しない11**。

| ID | 出どころ・指摘 | 判定 | 再現・対応 |
|---|---|---|---|
| SR-PATH1 | 自己レビュー: コマンド置換がパス末尾のLFを失う | 対応する (a) | 末尾LF2文字を含む agent と除去後の decoy を置き、setup3本の誤更新、MCPの事前検査迂回、4manifestの探索ずれを再現。native Piと異なる対象への設定・資格情報保存になる |
| SR-UPDATE1 | 自己レビュー: provider setup単独では新launcherと旧helperが非互換 | 対応する (a) | 旧公開APIだけのhelperと既存tierを持つHOMEでsetup→配置済みlauncherを実行。Command Codeはpi_agent_directory未定義で停止、OpenCodeも旧helperを使う。4ケースがPiへ届かない |

SR-PATH1はF-2/F-5の自己レビューでの再発、SR-UPDATE1はこの回の新launcher依存が生んだ回帰である。**以下の修正後は再レビューせず、検証だけを再実行する。**

守る条件の設計を「同じ意味のパス」だけでなく「受け渡す文字列全体を失わない」「配布単位に互換な依存を含める」へ見直す。PythonのCLIが付けた改行とパス自身のLFを区別し、全7箇所のshell受信（setup3、installer4）で成功時だけ末尾sentinelを付け、受信後に追加した区切り改行とsentinelだけを除く。zsh内はREPLYで受け渡し、コマンド置換しない。テストもrstrip/stripを使わずCLI自身の改行1文字だけを除く。

| 条件 | 経路・停止位置 | 変更前の挙動 | 判定 | 検証 / assertion |
|---|---|---|---|---|
| F-2/F-5・文字列全体の保持 | settingsの直接/明示/再入力、setup3本とinstaller4関数のstdout受信 | $()がパス自身のLFも削除、正常decoyを検査/更新 | 全受信へsentinel方式を適用 | native保存先一致、LF付き実対象/decoy/共有先/auditの全状態比較。各拒否は異常1つだけ |
| 同上 | zshのOAuth/model読取、Vertex mount、Pi起動環境 | REPLYではLFを保持する | 既に満たす。変更しない | 実launcherのLF付き環境受け渡し、既存gate/overlay回帰 |
| 配布後の互換性 | Command Code/OpenCodeの事前入力検査→models/auth更新→bin/helper→launcher | launcherだけ配布し新依存を置かない | helper sourceの存在を事前検査し、tierを触らず同じ版のhelperも配布 | 旧helperからprovider単独setup→実配置済み4launcherがPiへ到達。起動前後の状態不変 |
| 同上・拒否前の状態保持 | helper欠落、不正models/auth/sourceの各入力拒否 | helper配布を後から足すと不正入力で先にhelperを置き換え得る | helper配布は全preflightの後。欠落sourceも副作用前に拒否 | 単一異常の全状態比較、既存provider全回帰 |
| 対象外 | DeepInfra setupのlauncher/helper配布 | もともとモデル定義のみを更新 | 対象外。配布機能を増やさない | 既存setup/環境回帰 |

比較: 末尾LFだけを禁止する保証縮小はPiが扱うPOSIXパスを不必要に拒否するため不採用。7箇所へ個別の文字置換を足す案も、改行の連続数で失うため不採用。成功時sentinelという共通の受渡方式を採用する。新launcherへ旧helper用のfallbackを複製する案はresolver分散を復活させるため不採用。providerからtier setup全体を呼ぶ案は利用者tierを不要に扱うため不採用。互換なhelperだけをlauncherと一緒に配布する案を採用する。I/O障害時の先行したモデル更新のrollbackは従来どおり保証しない。

レビューで挙げた判断対象外の項目は、実機受入、ポートの因果関係、D-2の撤去範囲、全体rollback/排他、運用値/glob/表示テストの整理、dangling自動修復、既存OAuthのBOM、symlink cwd/類似package名の未確定候補、移植元snapshotの再照合。実機/所有者は未確認を維持、意図した設計・非致命的な整理は採用しない。移植元の初回一致は既存記録を維持するだけで今回再検証したとは書かない。

### 最終検証・失敗時の検証

| 検証 | 結果 |
|---|---|
| 開始HEADの隔離 worktree | migrations 330 passed / exit 0。誤った symlink-parent の期待値を直す前の結果 |
| 最初のRED | 40 failed / 58 passed / exit 1。対象ずれ・事前検査迂回・誤った認証/model gateを検出 |
| 解決済みパスの環境固定のRED | 8 failed / 98 deselected / exit 1 |
| 初回修正後のpath/provider/MCP | 226 passed / exit 0。pathは106件、同内容の/tmpも106件成功 |
| Pythonの字句的正規化だけを外した隔離対照 | settings/providerの対象負例18/18が失敗 / exit 1 |
| zshの字句的正規化だけを外した隔離対照 | 誤ったauth/modelを許す4/4負例が失敗 / exit 1。復元後106件成功 |
| 自己レビュー2件のRED | 34 failed / 30 passed / 82 deselected。LF付き入力とprovider単独更新の破綻を検出 |
| 自己レビュー修正後のpath/provider/MCP | 274 passed / exit 0。その後、helper欠落の事前拒否2回帰を追加し、下の最終suiteで検証 |
| 成功時sentinelだけを各setupで1箇所ずつ外す隔離対照 | DeepInfra3/3、Command Code3/3、OpenCode6/6、計12/12負例が失敗 / exit 1 |
| MCPの成功時sentinelだけを外す隔離対照 | MCPのLF付き3/3負例が失敗、同時選択された無変更の導入入口3例は成功 / exit 1 |
| helper欠落の事前検査だけを各setupで1箇所ずつ外す隔離対照 | 2/2負例が、後段installの終了コードではなく全状態の変化で失敗 / exit 1 |
| 対照をすべて復元した/tmp worktree | 最終path146件 + provider80件 = 226 passed / exit 0。worktreeと親directoryは削除済み |
| 最後のコード変更後の環境suite | `PI_CODEX_LIVE_CHECK=0 PI_XAI_LIVE_CHECK=0 PI_OFFLINE=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash .devcontainer/run-tests.bash` が32/32 PASS / exit 0。migrationsは最終収集数419件（開始330 + 今回89）で同入口から実行 |
| layout・bash/zsh構文・Python AST・diff | すべてPASS / exit 0 |

不正入力は、選択したsettings/models/authにsymlink・hardlink・不正JSONのうち異常1つだけを与える。比較する状態はテスト所有root全体のファイル有無・バイト列・mode・種類・リンク先・link数で、HOME、別settings/models/authと共有先、npm manifests、bin/既存helper、backup/staging、外部Pi/npm auditを含む。各期待値は実行前snapshotから取る。新しいhelper欠落も、他のsource/入力を正常にした単一異常で検証し、models/authやhelper配布より前に拒否することを確かめた。正常な設定更新は対象providerとextensionsだけを変更し、decoy・他provider・modeを保持する。

中心境界の負例の対照は **計39件（18 + 4 + 12 + 3 + 2）** が意図した失敗を示した。いずれもSHA照合済みの使い捨てworktreeで1箇所ずつ保護を外し、readonly root/private tmp/fixtureのみrw/network・PID隔離を維持した。実装用worktreeでは保護を外していない。正常版の再検証後にworktreeを外し、親directoryを削除した。追加した89ケースは実処理の分岐・I/O・環境受け渡し・旧版からの更新を検証するもので、文書・一覧・設定値だけのテストは追加していない。

I/O失敗のrollback範囲は変更していない。既存fsync/replaceの全状態回帰も最終suiteで成功した。設定更新後のhelper/launcher配布でI/O障害が起きた場合は、完了済みモデル更新やbackupが残り得る。全操作rollback・並行更新の排他は保証しない。symlink cwdの追加候補は、テスト所有のaliasへcdしたzshの:aとnative Node path.resolveが同じphysical cwd基準の保存先になることを局所確認し、この条件の新規指摘にはしない。

自己レビューは1回、追加2件とも修正した。**自己レビュー後に変更したsentinel・helper配布・関連テストは再レビューしていない。** 実機rebuild・交互rebuild・実provider/ADC・Windowsブラウザー/所有者は未確認のまま。全10ポートのEADDRINUSEは観測事実でありforwardPortsが原因とは断定しない。既存PRの制限と回避方法を維持する。private Actionsは規約により対象外。Specの公開・pushの結果はPR状況コメントと完了報告へ記録し、記録だけのcommitを追加しない。

公開前までの能動時間は約48分（準備/全入力・全文確認/再現9、設計/実装/局所回帰12、環境/隔離対照などの検証17、自己レビュー/裁定/記録10）。レビューworkerは所要を未計測と報告したため推測で補わない。最初のNEEDS_CONTEXTは判定前の入力不足で、読取用artifactを渡して同じ1回のレビューを完了した。最初の調査workerの結果なしを成功扱いしていない。

## 対象外・停止条件

ccdu、DSH の launcher / installer、agent-runner、他リポジトリの変更、API 実呼び出し・ログイン・ADC 作成、rebuild・マージ・force push・タグ・リリースは対象外。同じ Issue の競合・明示の判断要求・未解消の依存・検証失敗・安全失敗が発生したら issue-to-pr に従って停止する。push / PR 作成直前に再確認する。
