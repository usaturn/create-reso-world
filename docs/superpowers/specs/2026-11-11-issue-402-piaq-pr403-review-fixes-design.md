# PR #403 レビュー修正（サイクル 1）: MAAS_ANTHROPIC_TOKEN の入力手順

- 状態: `completed`
- 対象: usaturn/create-reso-world PR #403（`feat/issue-402-piaq-launcher`）、Issue #402
- 実行許可: 利用者の `/issue-to-pr #402 --merge ...`（2 回目の run）による PR 修正ループ（pr-review-fix-loop）の review-fix-planning の完遂。PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可
- 結論: 1（修正して push）
- planner: `claude-opus-5-5`（claude-code）、サイクル 1、レビューした HEAD `51cdeadeb61d460e9f0f7b53ecc94bcc9572ad8d`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol（`pi_openai-codex_gpt6-sol_xhigh`） | pi | `51cdeadeb61d` | はい | Approve（Low 1 件） |
| `grok-4.7.md` | grok-4.7（`pi_xai_grok4_xhigh`） | pi | `51cdeadeb61d` | はい | Approve（指摘なし） |

確認済みの一覧: `reviews/usaturn/create-reso-world/#403-feat-issue-402-piaq-launcher/verified/51cdeadeb61d.json`（V-1 confirmed）。前のサイクルの判断: なし（初回）。

## 全指摘の振り分け

| ID | 出どころ | 区分 | 根拠 |
| --- | --- | --- | --- |
| `gpt-6.1-sol#L-1@51cdeadeb61d`（V-1） | gpt-6.1-sol | 対応する | 致命的（秘密情報の露出）かつ現行 HEAD で再現（(a)）。下記 |
| `fix-check#V-1@14a3c6b89622` | 修正の確認（self） | 対応しない | Dev Container の zsh はブラケットペーストが既定で有効（`bindkey` に `^[[200~ bracketed-paste`）で、その状態では 2 行を貼っても key は残らない（修正の確認で再現）。同じ形は base の既存の ccda の手順にもある。見直す条件: サポートする端末（VS Code・Windows Terminal・Herdr）がブラケットペーストを送らないと分かったとき |

解消済み 0 件、対応する 1 件、対応しない 1 件。

## 要件対応

PR の約束（Issue #402 の防御範囲「key の値が models.json・ログ・agent-runner の result・summary に出ない」、README の「秘密情報」の `MAAS_ANTHROPIC_TOKEN` はどのファイルにも書かない方針）と、既存の Spec `docs/superpowers/specs/2026-11-11-issue-402-piaq-token-plan-design.md`（D2・D4・D7 の key の案内）を今回の修正へつなぐ。

| 条件 | 修正方針 | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 利用者に示す key の入力手順は実値をコマンド行に書かせない | README の例・piaq と setup の案内・Plan の指定を `read -rs ... && export MAAS_ANTHROPIC_TOKEN` に揃える | `export MAAS_ANTHROPIC_TOKEN=` の直接代入が 0 件、各経路が `read -rs` | `git grep`、案内の表示 |
| key の判定・終了コードは変えない | 案内の文字列だけを変える | T1・既存テストが通る | `test-pi-superagents.bash`、pytest |

共有条件は「key の入力手順の形」1 つ。統合担当は controller で、全経路の検索と案内の表示で確かめる。

## 対応する: V-1

- 致命的である理由: Dev Container の対話 zsh は `HISTFILE=~/.zsh_history`・`SAVEHIST=10000`（oh-my-zsh の history.zsh）で履歴をファイルに保存する。README・piaq・setup の案内どおりに `export MAAS_ANTHROPIC_TOKEN="<key>"` を打つと、どのファイルにも置かない方針の key が `~/.zsh_history` に保存され、端末にも表示される。発生条件はサポートしている通常の使い方（案内を読んで対話シェルで key を設定する）
- 確認: 隔離した疑似端末で再現（直接代入は端末・履歴の両方、先頭に空白の export は端末、`read -rs` はどちらにも残らない）
- 修正方針: 既存の ccda の手順と同じ `read -rs 'MAAS_ANTHROPIC_TOKEN?Model Studio API key (非表示): ' && export MAAS_ANTHROPIC_TOKEN` にする。検討した別案: (1) 案内から export の例を消して「export する」とだけ書く（どう入力すべきかが分からず、直接代入を招く）、(2) 先頭に空白を付ける（histignorespace で履歴には残らないが端末には残る）。既存の手順と揃う推奨案を選んだ
- テスト: 書かない（案内の文言は F）。検索と表示で確かめる

### 守る条件と影響経路

| 経路 | 変更前の挙動 | 修正 | 確かめる方法 |
| --- | --- | --- | --- |
| `.devcontainer/README.md`（agent-runner の節の例） | 直接代入 | する | `git grep` |
| `.devcontainer/README.md`（#402 の節の例） | 直接代入 | する | `git grep` |
| `.devcontainer/piaq`（key が無いときの案内） | 直接代入を表示 | する | 一時 HOME で key 無しの piaq を起動し stderr を見る |
| `scripts/setup_pi_alibaba.zsh`（key が無いときの案内・Summary） | 直接代入を表示 | する | `git grep`、`zsh -n` |
| `docs/superpowers/plans/2026-11-11-issue-402-piaq-token-plan.md`（Task 1 の案内の指定） | 直接代入を指定 | する | `git grep` |
| `.devcontainer/README.md`（ccda の既存の手順） | `read -rs` | しない（基準） | — |

## 修正の実装

- 担当: `run_roles.py --phase implement`、`--assign implement=pi_xai_grok4_xhigh`（ループの割り当て）。観測した identity は `grok-4.7`・xai・xhigh、所要 423 秒、停止確認済み
- commit `14a3c6b89622458560702e7fabd148e59e4a7426`（親 `51cdeade`）を差分の確認の後に fast-forward で取り込んだ。README の 2 例（各例の後に入力値が表示されず履歴にも残らない旨の 1 文）、piaq の案内、setup の案内と Summary（貼れるよう接頭辞なしの `print -r`）、Plan の Task 1 の指定を `read -rs` の形にした

## 実行した検証と結果

- `14a3c6b8`（未 commit の変更なし）: `bash .devcontainer/test-pi-superagents.bash`・`uv run pytest tools/devenv_migration/tests/test_pi_provider_setup.py -q`・`bash .devcontainer/test-readme.bash`・`zsh -n .devcontainer/piaq scripts/setup_pi_alibaba.zsh`・`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh` がすべて終了コード 0。`git grep -n 'export MAAS_ANTHROPIC_TOKEN='` は 0 件。key 無しの piaq が表示した案内の行をそのまま zsh に貼ると、偽の key を読んで export できた。`scan-before-push.sh`: no leaks found
- 自己レビューの後に `origin/main` が `65b7800c` から `030fa791`（#404、`zshrc.txt` の ccda の tier のモデル 2 行）へ進んだ。利用者の指示（main が進んだら止まらずに追随する）で feature branch に merge した（merge commit `85379673`、競合なし、rebase・force push なし）。merge 後の検証は下に記す
- merge 後（`85379673`）の検証は、利用者の指示（「検証はやり直さなくていいです。」）でやり直していない。始めた検証は途中で止め、結果を根拠にしていない。merge した変更は `zshrc.txt` の ccda の 2 行だけで、上の検証の対象の経路に触れない

## 要件対応の照合（3. 検証と閉じ方）

- 修正する経路 5 行はすべて `read -rs` になり、直接代入は 0 件（検索）。判定の両側: 直接代入（from）は端末・履歴に残り、`read -rs`（to）は残らない（pty の対照、修正の確認）
- key の判定・終了コードは変えていない（T1 と既存テストが通る）
- 独立した根拠: 修正の確認は from の直接代入で漏れを検出し、to では検出しなかった。テストは足していない（文言は F）
- merge した main の変更は `zshrc.txt` の ccda の tier だけで、この PR の経路（README の piaq の節・piaq・setup・Plan）に触れない

## 自己レビュー（1 回）

- `run_roles.py --phase self-review` を 1 回（self-review・fix-check とも `self`。工程の記録に `pre_push_review` を予約）。司令塔の責任で、別 context のサブエージェント（claude-opus-5-5）2 つに並行で任せた
- self-review（PR 全体、`14a3c6b8`）: `claude-opus-5-5-commit-14a3c6b89622458560702e7fabd148e59e4a7426.md`、指摘 0 件、Approve
- fix-check（V-1）: `verified/14a3c6b89622.fix-check.json`、主張 8 件 holds、変更 4 ファイル passed。新しい観察 fix-check#V-1 を 1 件（上の振り分けで対応しない）
- 自己レビューの後の変更は main の merge だけで、再レビューしていない（次のサイクルのレビュアーが merge 後の HEAD をレビューする）
