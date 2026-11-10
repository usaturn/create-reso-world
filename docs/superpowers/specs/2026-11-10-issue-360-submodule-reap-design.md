# Issue #360: strict retirement の submodule 保全

## 管理・実行許可

- 状態: `completed`。利用者の内容承認は記録していない。issue-to-pr と修正ループの明示的な実行許可により、実装・検証・修正要否の確認を完了した。マージ・Issue更新の実施結果はPRの記録に残す。
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

## 復旧・実装記録

- 2026-11-10 の利用者の追加指示: 「途中まで実行していたが、$HOME が他のセッションに削除された為、続行不可能となっている。リポジトリ内に救出可能なものがあれば、それを使って作業を続行してください」。担当指定と `--merge` は維持する。内容承認とは区別し、復旧時点では状態を `draft` のまま維持した。
- 旧担当はコードを commit したが、runner の最終判定は `awaiting_authentication` / `failed`。この記録を成功へ変更せず、停止確認後にログと commit を保全した。
- 同じ指定担当へ復旧依頼を1回実施。救出 commit を再利用し、内容が同一の `99ba96a9ba873d13a759aff14ed0c71257110c13` で関連110件・対象3件、構文検査、diff検査が成功。新runnerは `success` / `stop_confirmed=true`、helperで再判定して正式に受領した。
- Task review と全体 review は修正指摘なし。既存のロック内再判定、pin・ownership・stop・draft の経路も確認した。対象外の未初期化 module・非strict cleanup・全refs/stashの保全保証は追加しない。
- 最終文書 commit を含む HEAD `8040a56c8440dd2b436b67e8062757327f4779a7` で全体検証を実施。`bash .devcontainer/run-tests.bash` は27本成功、`bash scripts/check-layout.sh` はPASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools` は1390 passed、すべて終了コード0。開始・終了ともclean。検証と秘密情報検査、捕捉base・Issue状態・競合の再確認を経てPR #383を作成した。

## PR #383 修正ループ・サイクル1の結論

- planner: `gpt-6.1-sol`（runtime `pi`、provider `openai-codex`、runtime環境変数とセッション照合で確認）。実行許可は利用者の `--merge` 指定。内容承認は発明しない。
- 判断記録: `review-records/v2`、PR `usaturn/create-reso-world#383`、サイクル1、reviewed_head `8040a56c8440dd2b436b67e8062757327f4779a7`。前サイクルなし、引継ぎ0件。

| レビューファイル | 実モデル | runtime | review HEAD | 再実行 | 推奨 |
| --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus-5-5 | claude-code | `8040a56c8440` | はい（Initial） | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `8040a56c8440` | はい（Initial） | Approve |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash | pi | `8040a56c8440` | はい（Initial） | Approve |

全3担当が成功・停止確認済み。active、Pending、Unverified候補はいずれも0件。入力から外したレビューなし。全指摘の分類は解消済み0／対応する0／対応しない0。結論2（修正不要としてマージへ進む）であり、票数ではなく、変更4ファイルの全文・共有ゲート・関連処理とテスト・実行証拠の照合を根拠とする。修正不要なのでrun_rolesによる実装・自己レビュー・fix-checkは未実施（各0回）。自己レビューの成功を発明しない。

確認済み一覧は `reviews/usaturn/create-reso-world/#383-fix-issue-360-submodule-reap/verified/8040a56c8440.json`、工程記録は同stemの `.planning.json`。候補一覧3件のvalidate/check-pairが成功。各レビュアーの未実施範囲について、全体検証はcontrollerの同一HEAD・clean記録で確認し、base版REDは救出した2failed/1passedの実出力と受領版の内容一致を照合した。初期化されていないmodule・全refs/stash・実PR削除実験は対象外であり、成功とは報告しない。未確認の受け入れ条件は残っていない。

| 要件・共有条件 | 確認結果・証拠 |
| --- | --- |
| ignore=allのHEAD不一致保持 | 実Gitの拒否例で両入口1、commit/内容/session/保存レビュー残存。修正前REDと修正後GREEN、受領版の110件を照合 |
| index flags・入れ子の保持 | 入れ子skip-worktreeの拒否と内容保持。assume-unchangedは一時実Gitシナリオと各レビュアーの実行結果で確認 |
| cleanな正常退役 | 両入口0、session/worktree削除と保存レビュー残存 |
| 共通判定とロック内再判定 | `_require_clean_worktree`→`validate_reapable_session`を両入口が利用。`strict_cleanup`は保存ロック取得後にも同じ検査を実施し、既存のlate writer回帰テスト成功 |

検証済みbase `1f20820f0b628c707784aa6f7f55146225139fd2` はreviewed_headの祖先であり、再取得したorigin/mainも同SHA。同一HEADの最終検証をissue-to-prの1サイクル目の再利用条件に従って使う。コード変更なしのため新たな再現・変異検査は追加しない。検証記録・実ログは `/workspaces/reso-world/tmp/agents/issue-360-recovery.ywtgkr2k/verification.json` と同ディレクトリの3ログ、最終化入力は `/workspaces/reso-world/tmp/agents/review-fix-planning-pr383.qzk7zxu1/`。

選択肢は、不要な実装変更を追加せず既存ガードと証拠を維持する案を採用。汎用走査・対象外の保全仕様追加・テスト網羅の拡張は本Issueの原因と異なるため選ばない。新しい設計見直しのきっかけに当たる修正指摘はない。マージはfinalize.pyによるbase/head/記録/merge第1親の照合に限る。

## 根拠

Context7 `/git/htmldocs` の git-submodule は foreach の `$toplevel` / `$sm_path` と直近 superproject、および recursive の挙動を定義する。git-ls-files は `-v` の小文字（assume-unchanged）と `S`（skip-worktree）を定義する。取得結果はセッションログに保存。変更前の対象テスト: 107 passed, exit 0。
