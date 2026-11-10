# Issue #360: strict retirement の submodule 保全

## 管理・実行許可

- 状態: `draft`。利用者の内容承認は記録していない。
- Issue: https://github.com/usaturn/create-reso-world/issues/360
- 利用者の指示: `#360 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`（原文の改行を空白へ置換）。「途中で main が進んでいる場合は留意して止めずに進めてください」。
- 許可: issue-to-pr による設計判断、指定担当への実装依頼、検証、commit、scan、push、PR、レビュー修正ループの finalize によるマージ。captured base の移動で停止する上位の運用規則は維持する。
- repository/origin/ref/base: `usaturn/create-reso-world` / `https://github.com/usaturn/create-reso-world.git` / `refs/heads/main` / `1f20820f0b628c707784aa6f7f55146225139fd2`。
- #360 は親 Issue 無し、コメント無し。前提 #351 は CLOSED、PR #358 は MERGED。#360 の競合 PR・branch・claim・worktree は検出されなかった。

## 目的と原因

保存済み・停止確認済みという理由で submodule の利用者作業を消さない。現在の `_require_clean_worktree` は初期化済み submodule を再帰して status と ignored を調べるが、HEAD と gitlink の一致および submodule 自身の index flags を調べない。`ignore=all` により親 status が変更を隠すと、ローカル commit または flags で隠した変更が削除ゲートを通過する。

## 採用する仕様

1. strict な退役判定で、各初期化済み submodule の HEAD を直近の親の HEAD に記録した gitlink と照合し、不一致を保持する。`ignore=all` で免除しない。
2. submodule の status、ignored（既存の再生成可能キャッシュだけ許可）、skip-worktree / assume-unchanged を直接検査し、利用者作業を保持する。入れ子にも同じ条件を適用する。
3. gitlink と一致し clean な submodule は従来どおり `reap-check` が eligible、`cleanup --strict-reap` が retired を返す。比較・Git 検査の失敗は成功扱いしない。
4. `_require_clean_worktree` の呼出元・保存ロック内の再判定・CLI JSON / 終了コード・既存の pin / ownership / stop / draft ガードを変えない。

## 範囲と対象外

変更するコードとテストは `.agents/skills/pr-review/scripts/pr_review_workspace.py` と `.agents/skills/pr-review/tests/test_pr_review_workspace.py`。設計と計画は本 PR に含める。実 PR の削除実験、定期掃除スクリプト変更、非 strict cleanup の意味の変更、未初期化 submodule に関する新たな仕様、汎用 submodule 走査の作り直しは対象外。作業物の削除実験はローカルの一意な一時 fixture に限る。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由 / 委任または停止条件 |
| --- | --- | --- | --- |
| 検査の構造 | 既存の foreach 再帰を必要最小限補強 | Python で gitlink ツリー全体を走査し直す | 既存の検査・失敗時の保持を活かし、今回の原因に絞る。通常設計は issue-to-pr の委任で選択 |
| 比較基準 | 直近の親 HEAD の gitlink と submodule HEAD | status のみに依存、remote への push の有無を調べる | ignore 設定やネットワークに依存せずローカル成果を守る。Git の仕様・実入力と食い違えば意味を保つ最小修正、意味の変更なら停止 |
| 実装方式 | runner に Task 1 を依頼し、controller が統合 | controller が直接実装 | check の assignment は agents=`[pi_opencode-go_deepseek4-flash_max]`, fallback=`[]`, self=false（利用者指定）。失敗を理由に self へ切り替えない |
| PR 後 | 修正ループ、最大3サイクル | PR 作成だけ | 利用者の --merge。implement と inspect は指示どおり。max_cycles=3、fix.self-review=self、fix.fix-check=self は既定の適用。検証・base・scan ガードを維持 |
| テスト | 実 Git の拒否2例＋通過1例 | 固定文字列テスト、全組合せ | ローカル成果の削除は S。HEAD 不一致と flags は別の守り。入れ子・空白/非ASCIIの path は代表例の fixture に組み込む |

## 受け入れ条件

Dev Container の Git / uv / pytest で、一時ローカル親 repo と初期化済み submodule を使う。`ignore=all` の submodule にローカル commit がある場合、および入れ子 submodule の index の印で変更が隠れる場合、`reap-check` と strict cleanup が終了コード1で保持し、ファイルと commit が残る。gitlink と一致する clean な submodule は終了コード0で退役でき、保存レビューは残る。既存テストを維持する。

## 根拠

Context7 `/git/htmldocs` の git-submodule は foreach の `$toplevel` / `$sm_path` と直近 superproject、および recursive の挙動を定義する。git-ls-files は `-v` の小文字（assume-unchanged）と `S`（skip-worktree）を定義する。取得結果はセッションログに保存。変更前の対象テスト: 107 passed, exit 0。
