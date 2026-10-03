# PR #16 レビュー指摘の修正方針（Superpowers 文書保存運用）

- 日付: 2026-10-03
- 状態: approved（2026-10-03 のユーザ指示「対応が必要な指摘があったら、推奨案でプッシュまでしておいてください。」による。推奨案は本 Spec の「修正方針」の 2 件。本版の内容確認は PR のレビューで行う）
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 対象 PR: usaturn/create-reso-world #16（`docs/superpowers-document-lifecycle`）
- 現行 HEAD: `821e82de7652984196ce187bc467f0c8ce97a194`
- 入力: `reviews/#16-docs-superpowers-document-lifecycle/`
  - `claude-opus-5-5.md`（対象 HEAD `821e82de7652`、Low 2 件、未検証候補 1 件）
  - `deepseek-deepseek-v4.1-flash.md`（対象 HEAD `821e82de7652`、Low 2 件、Info 1 件）
  - `openai-codex-gpt-6.1-sol.md`（対象 HEAD `821e82de7652`、Medium 3 件）
- 経路（brainstorming の判定）: bounded。既存の 2 スキル（pr-review の resolver、review-fix-planning の Spec 配置規則）と、その契約テストの中で閉じる修正で、他のスキルや規約とのインターフェースは変わらない
- 関連 Spec: `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md`

## 現行 HEAD での再現

3 件のレビューはいずれも現行 HEAD と同じ `821e82d` を対象にしている。現行 HEAD の隔離 worktree から pr-review の resolver ブロックを契約テストと同じ正規表現で抽出し、一時リポジトリで実行した。

| ケース | 結果 |
| --- | --- |
| `CODE_ROOT` に、origin が `other/repository` の checkout の linked worktree を渡す（cwd は親） | 終了 0。`MAIN_ROOT=<linked worktree>`、`PR_REMOTE=origin` |
| 同じ linked worktree を `pr_review_workspace.py create --repo` に渡す | 終了 2。`error: repo must be the main checkout, not a linked worktree` |
| 同じリポジトリの main checkout を `create --repo` に渡す | 終了 0。セッションを作成 |
| `CODE_ROOT` に remote の無い checkout を渡す | 終了 66。`CODE_ROOT … has 0 remotes for other/repository; exactly one is required` |
| cwd を origin が `other/repository` の checkout にし、`CODE_ROOT` を空にする | 終了 0。`MAIN_ROOT=TOPLEVEL=<その checkout>`。`$TOPLEVEL` から解決する helper は存在しない |

## 指摘の一覧と振り分け

分類: 解消済み 0 / 対応する 2 / 判断保留 0 / 対応しない 7

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| F1 | Claude L-1、DeepSeek L-2 | pr-review の resolver が linked worktree の `CODE_ROOT` を通すが、helper の `create` がそれを拒否する | 対応する (a) | 上表のとおり再現した。resolver の検査を通った値が、fetch で `refs/pr-review/<N>` を作った後の `create` で必ず失敗し、エラーも `CODE_ROOT` の指定の誤りを示さない |
| F2 | Codex M-3 | review-fix-planning が Spec を `$TOPLEVEL/docs/superpowers/specs/` に書く一方、コミットとコピー元には別 checkout になりうる `DOC_ROOT` を使う | 対応する (b) | `SKILL.md:62` の「Spec の正本は `$TOPLEVEL`（… `DOC_ROOT`）にだけ置く」は、`TOPLEVEL` と `DOC_ROOT` が同じだと述べている。しかし同じ節の 1. は「そのブランチの checkout を `DOC_ROOT` とする」と定め、ルート `AGENTS.md` も `DOC_ROOT` を「checkout または worktree」としている。PR #16 自身も、親 checkout（`TOPLEVEL`）が `fix/devcontainer-tests-ci` にあり、レビュー対象ブランチは `.worktrees/superpowers-document-lifecycle` にある。この状態で手順どおりに `$TOPLEVEL` へ書くと、`DOC_ROOT` の `git add` が pathspec の不一致で失敗する（Codex が終了 128 を確認） |
| F3 | DeepSeek L-1、Claude L-2 の後半 | AGENTS.md の「remote の無いローカル専用の checkout は、明示指示がある場合だけ扱う」に対応する経路が、pr-review・review-fix-planning のどちらにも無い | 対応しない | 「明示指示がある場合だけ」は必要条件であり、2 スキルが remote 0 件を常に止める現状と矛盾しない。止まる際のメッセージ（`has 0 remotes …; exactly one is required`）も明確で、安全側に止まる。ローカル専用 checkout を支えるかは仕様の論点（下記「残る論点」） |
| F4 | Claude L-2 の本体 | AGENTS.md は `CODE_ROOT` の経路を 2 スキルに限るが、Spec §3.1・planning-parallel-issues・agent-handoff は他リポジトリの実装作業を前提にしている | 対応しない | どちらに揃えるかは仕様・設計の是非であり、レビュー自身も【要設計判断】としている。現状は AGENTS.md の規定で止まるだけで、誤った書き込みは起きない（下記「残る論点」） |
| F5 | Codex M-1 | `superpowers-review-copy.sh` のコピー先の検査から `mv -f` までの間に、別の処理のコピーやユーザの編集を上書きできる | 対応しない | 同じ親 checkout・同じ `--name` への同時実行（検査から `mv` までの短い窓）が前提の理論上の競合で、将来の保険に当たる。Spec §3.3 の命名（repo・番号・主題）では別作業の同名衝突自体が起きにくい。ユーザの編集との競合はロックでも防げず、保護範囲の再設計になる |
| F6 | Codex M-2 | 外部リポジトリの checkout を cwd にして pr-review を実行すると、`TOPLEVEL` がコード側を指し、helper が見つからない | 対応しない | pr-review は create-reso-world を cwd にして実行し、helper を `$TOPLEVEL` から解決する前提で書かれている。`origin` が一致すれば `MAIN_ROOT=$TOPLEVEL` とする分岐と helper の解決は、PR 前の main にも同じ形であり（`external/resoloop` を cwd にした場合も同じ結果になる）、この PR で生じた退行ではない。失敗は helper の不在で止まる安全側である。外部 cwd での実行を支えるかは設計の論点（下記「残る論点」） |
| F7 | DeepSeek I-1 | Plan が最終レビュー修正 `821e82d` の 3 点を反映していない | 対応しない | Plan は実装過程の記録であり、Spec §7 は完了した Plan の手順を再実行しない前提を定めている。Info 級の追随漏れで、現行の規約・スキルの記述には影響しない |
| F8 | Claude 未検証候補 | review-fix-planning の `allowed-tools` の `Write(docs/superpowers/specs/**)` が相対パターンのため、別パスの `DOC_ROOT` では許可確認が出るおそれがある | 対応しない | 未検証で、起きても許可確認が出るだけの安全側である。F2 の修正後は `DOC_ROOT` が別パスの場合に確認が出る可能性が高まるが、誤った書き込みにはつながらない |
| F9 | Claude テスト提案 3 | `tmp` 自体が symlink の場合をコピーのテストに加える | 対応しない | レビュー自身が「指摘ではない補強」としており、スクリプトの挙動は正しい。理由なく削除された回帰ガードの復元にも当たらない |

## 修正方針

### F1: pr-review の resolver で linked worktree を早期に拒否する

対象は `.agents/skills/pr-review/SKILL.md` と、その契約テスト `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py` である。helper（`pr_review_workspace.py`）の main checkout 要件は、隔離 worktree の安全策なので変えない。

1. resolver の `elif [[ -n "$CODE_ROOT" ]]` の分岐で、checkout のルートであることを確かめた直後に、helper の `require_main_checkout` と同じ判定を行う。`git -C "$CODE_ROOT" rev-parse --path-format=absolute --git-dir` と `--git-common-dir` を `realpath -e` で比べ、一致しなければ `CODE_ROOT is a linked worktree; name the main checkout of <repo>: <path>` を出して `exit 66` で止める。fetch より前に止まるので、対象リポジトリに `refs/pr-review/<N>` を作らない。
2. 手順 2 の本文の「その他のリポジトリは…`CODE_ROOT` に入れてから次を実行する」に、pr-review の `CODE_ROOT` は対象リポジトリの main checkout とすること、linked worktree は helper が扱わないため resolver で止めることを 1 文加える。Spec §3.1 と handoff schema の「checkout または worktree」は、worktree から動く review-fix-planning などにも当てはまるので変えない。
3. `test_pr_review_resolver_rejects_an_unverified_code_root` に `linked-worktree` のケースを加える。`build_checkout` で作った checkout から `git worktree add` した worktree を `CODE_ROOT` に渡し、終了 66 と stderr の `CODE_ROOT` を確かめる。

### F2: review-fix-planning の Spec の作成・更新先を `DOC_ROOT` に揃える

対象は `.agents/skills/review-fix-planning/SKILL.md` と、その契約テスト `.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py` である。

1. 「Spec のコミットと確認用コピー」の冒頭を、Spec の正本は create-reso-world の `DOC_ROOT` にだけ置くこと、`DOC_ROOT` は `$TOPLEVEL` と同じとは限らないこと、`$TOPLEVEL` はスキル helper と `scripts/superpowers-review-copy.sh` の配置元として使うこと、に書き換える。
2. 同じ節の 1. を、Spec を書く前に `DOC_ROOT` を確定する手順にする。確定の規則（create-reso-world の PR ならレビュー対象ブランチの checkout、それ以外ならテーマごとの文書用ブランチの checkout、特定できなければ停止）は変えない。
3. 手順 6「Spec を書く」に、`DOC_ROOT` を確定してから `$DOC_ROOT/docs/superpowers/specs/` に書くことを加える。
4. 「Spec は経路に関わらず必須」の配置を `$DOC_ROOT/docs/superpowers/specs/` にする。`MAIN_ROOT` が `external/resoloop` や他のリポジトリの checkout でも、そちらへ置かない旨は残す。
5. 契約テストの配置指定を `$DOC_ROOT/docs/superpowers/specs/` に変え、スキル本文に `$TOPLEVEL/docs/superpowers/specs/` が残っていないことも確かめる。

## 検証方法

| 対象 | 方法 | 期待結果 |
| --- | --- | --- |
| F1 | `uv run pytest .agents/skills/pr-review` | PASS。`linked-worktree` のケースが終了 66 で止まる |
| F2 | `uv run pytest .agents/skills/review-fix-planning` | PASS |
| 環境の変更（スキル） | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills` | 本 PR の変更による失敗が無い。PR 説明に記載した main 由来の既存の失敗（`test-instructions.bash` の `.pi/APPEND_SYSTEM.md lacks: async: false` など）は、変更前後で同じであることを確かめる |

## 残る論点（対応しない項目のうち仕様に関わるもの）

- F3・F4: 他リポジトリの `CODE_ROOT` 経路をどの作業に開くか。AGENTS.md の 2 スキルへの限定を維持して Spec §3.1・planning-parallel-issues の記述を限定に合わせるか、確認済みの handoff の `git.code` を使う実装作業にも経路を開くか。あわせて、ローカル専用 checkout の条項を残すか。
- F6: 外部リポジトリの checkout を cwd にした pr-review の実行を支えるか。支える場合は、create-reso-world のルートをコード側の cwd と独立に確定・照合する必要がある。
- F5: 確認用コピーの保護範囲に、同時実行とユーザの編集との競合を含めるか。
