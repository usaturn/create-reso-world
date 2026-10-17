# Issue #125: pi の agent-workspace との共通化

## 管理・実行許可

- 状態: `draft`（内容の承認は得ていない。issue-to-pr の実行許可と区別する）
- 文書・実装対象: `usaturn/create-reso-world`、https://github.com/usaturn/create-reso-world/issues/125
- 利用者の指示: `/skill:issue-to-pr #125`。同スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」を適用する。マージ・実環境の更新・認証・課金呼び出しは行わない。
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-125-pi-workspace-parity`
- branch: `feat/issue-125-pi-workspace-parity` → `main`
- 移植先の基準: `76f1098af9f07388f4c10d55786ea9d726654171`
- 移植元: `usaturn/agent-workspace` main `715d98168ab60011a98a42476ffea2759d4866d7`（2026-10-17 に再確認）。この SHA のファイルを読み取り専用の GitHub snapshot から取り入れる。外部 checkout の探索・clone・変更はしない。
- 先行条件: agent-workspace #713 は PR #714 でマージ済み。後続の修正 #716 / PR #717 もマージ済み。同じ Issue の open PR・担当予約・branch・worktree は無い。GitHub parent は無い（parent API の 404 は正常な不在）。#122 は rebuild 後の確認待ちだが、必要な設定の PR #129 はマージ済みで基準に含まれる。

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

## Builder check の裁定

2026-10-17、独立した読み取り専用 `sp-recon` が Spec と source / target を照合した。指摘3件（導入節の target 側終端・devcontainer 変更の明記・APPEND_SYSTEM の変更範囲）は全て既存のファイルと明示ルールから解決し、上記へ反映した。利用者だけが決められる未解決事項は無い。最初の `sp-review` はレビュー scope 未指定として開始前に拒否したため、builder check を `sp-recon` で行った。後のブランチレビューは正式な branch scope とテンプレートで依頼する。

## 対象外・停止条件

ccdu、DSH の launcher / installer、agent-runner、他リポジトリの変更、API 実呼び出し・ログイン・ADC 作成、rebuild・マージ・force push・タグ・リリースは対象外。同じ Issue の競合・明示の判断要求・未解消の依存・検証失敗・安全失敗が発生したら issue-to-pr に従って停止する。push / PR 作成直前に再確認する。
