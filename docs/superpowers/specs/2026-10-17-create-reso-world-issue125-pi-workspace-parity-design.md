# Issue #125: pi の agent-workspace との共通化

## 管理・実行許可

- 状態: `completed`（PR #141 のレビュー修正・ローカル検証が完了。内容の承認や実機の受け入れ完了は意味しない）
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

## 対象外・停止条件

ccdu、DSH の launcher / installer、agent-runner、他リポジトリの変更、API 実呼び出し・ログイン・ADC 作成、rebuild・マージ・force push・タグ・リリースは対象外。同じ Issue の競合・明示の判断要求・未解消の依存・検証失敗・安全失敗が発生したら issue-to-pr に従って停止する。push / PR 作成直前に再確認する。
