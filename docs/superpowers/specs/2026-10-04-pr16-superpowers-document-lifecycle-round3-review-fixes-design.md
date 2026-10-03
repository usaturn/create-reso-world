# PR #16 第3回レビュー指摘の修正方針

- 日付: 2026-10-04（JST）
- 状態: completed（2026-10-04 のユーザの「進めて。」で R11〜R13 を明示承認。実装・必須検証・独立レビュー完了。後続の明示指示に従い既存 PR #16 へ反映。公開コミットと push の結果は同 PR の review-fix-planning コメントに記録）
- brainstorming 経路: bounded
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 対象リポジトリ・PR: [usaturn/create-reso-world #16](https://github.com/usaturn/create-reso-world/pull/16)
- 対象ブランチ: `docs/superpowers-document-lifecycle`
- 検証 HEAD: `333f4fb9bb704fb8934b9f6889453e5812a5dc29`
- 入力ディレクトリ: `reviews/#16-docs-superpowers-document-lifecycle/`
- 関連する運用設計: `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md`
- 前回の分類・実施結果: `docs/superpowers/specs/2026-10-03-pr16-superpowers-document-lifecycle-round2-review-fixes-design.md`

## 1. 目的・適用手順

指定ディレクトリにあるレビューを現行 PR HEAD のコミット済み内容で検証し、再現した誤動作だけを修正対象にする。前回までに対象外と決めた設計論点は広げない。

今回はユーザが提示した review-fix-planning の手順を適用した。計画時には Spec をこのリポジトリの `docs/superpowers/specs/` に保存して提示し、未コミット・未公開のまま明示承認を待った。レビュー対象 HEAD のスキルに追加された文書コミット・確認用コピーの手順を、計画フェーズへの追加指示として流用していない。その後ユーザが R11〜R13 を承認し、既存 PR #16 への push まで指示した。承認された版の内容 SHA-256 は `fd295dab09b9e502bf781b0a0830a9cd26d0b2b8d1a735ef4b81f108590e632b`。

**成功条件:**

1. 明示された外部 `CODE_ROOT` の remote が1件だけ一致するとき、bash・zsh の両方でその remote を返す。
2. create-reso-world の linked worktree を cwd にした ResoLoop PR レビューは、fork clone を案内する前に main checkout を案内して終了66で止まる。
3. `ssh://git@github.com/<owner>/<repo>.git` を使う正しい checkout が、URL形式だけを理由に resolver・確認用コピーから拒否されない。
4. 既存の main checkout 経路、remote の不一致・複数候補拒否、コピーの静的な衝突・編集・symlink 拒否は維持する。

新しい対象リポジトリ経路、外部 cwd 対応、ロック、文書状態の改訂、過去 Plan の同期、既存 helper の安全要件変更は行わない。

## 2. 入力と検証方法

指定ディレクトリの全4ファイルを全文読んだ。すべて冒頭の対象 HEAD は `333f4fb9bb70` で、PR API・fetch 結果・隔離 worktree の HEAD と一致した。

| 入力ファイル | 現行指摘 | 解消記録・未検証候補 |
| --- | --- | --- |
| `openai-codex-gpt-6.1-sol.md` | M-1、M-2 | 解消 M-3 |
| `deepseek-deepseek-v4.1-flash.md` | L-1、L-4、I-1、I-2 | 解消 L-2、L-3、allowed-tools 候補 |
| `claude-opus-5-5.md` | M-1、L-2、I-1 | 解消 L-1、allowed-tools 候補 |
| `opencode-go-muse-spark-1.3-contributor.md` | なし | なし |

source/test の読解根拠は `git show <検証HEAD>:<path>` で取得した blob とした。挙動検証には `mktemp -d` で作った一意なルート配下の同 SHA の detached worktree と、一時リポジトリを使用した。resolver はコミット済み SKILL.md の手順2から既存テストと同じ正規表現で抽出し、変更せず実行した。コピー helper もコミット済み blob のまま使用した。

文書・既存方針の照合は読み取り専用の調査役に委譲した。最初の委譲はコマンド実行ツールがなく HEAD を確認できなかったため、その暫定報告は根拠にしていない。調整役が取得した committed blob を渡した再調査と、調整役自身の読解で確認した。テスト・挙動検証・最終分類は調整役が担当した。

他の worktree・ブランチの未コミット差分、指定外のレビュー、`docs_draft/` は読んでいない。ネットワーク fetch を必要とするフィクスチャ操作、実際の fork clone、Resonite 操作も行っていない。

## 3. 全指摘の分類

**重複を統合した13項目: 解消済み3 / 対応する3 / 判断保留0 / 対応しない7。**

R1〜R10 は前回 Spec の分類 ID を維持し、新規指摘に R11〜R13 を割り当てる。同じ問題の解消記録と共有の未検証候補は、それぞれ1項目に統合した。Claude L-2 に含まれる remote-less の論点は R3 と重複するが、指摘全体は R4 に保持する。行番号はすべて上記検証 HEAD のもの。スキル名の短縮表記は `.agents/skills/<name>/SKILL.md` を指す。

| ID | 出典 | 内容 | 区分 | 根拠・理由 |
| --- | --- | --- | --- | --- |
| R1 | Claude L-1、DeepSeek L-2（解消記録） | linked `CODE_ROOT` を resolver が通し、helper が後から拒否する | 解消済み | `pr-review:140–146` の main checkout 検査で、linked `CODE_ROOT` は終了66、正常値出力なし。`ab28ff527f13` の修正が現行 HEAD でも機能する。 |
| R2 | Codex M-3（解消記録） | 別の `DOC_ROOT` を使うと Spec の作成・コミット先が不一致 | 解消済み | `review-fix-planning:57,62–64,183` は作成・更新・コミット先を `DOC_ROOT` に統一。別の文書 worktree の新規・更新コピーは両方終了0、blob と一致し、親の文書・Git status は未変更。 |
| R3 | DeepSeek L-1、Claude L-2 の remote-less 部分 | remote のない checkout と exact-one-remote 検査の関係 | 対応しない | `AGENTS.md:70` が一致 remote 1件を要求し、remote 0件は終了66を再確認。「明示指示があれば必ず対応する」仕様への変更は前回 R3 と同じ設計論点であり、今回も変更しない。 |
| R4 | Claude L-2 | 任意 `CODE_ROOT` の対象が2スキルに限定され、Spec・planning・handoff の広い想定と食い違う | 対応しない | `AGENTS.md:70` が pr-review と review-fix-planning 以外では停止する方針を定める。適用範囲を広げるか、他の文書を限定に合わせるかは前回 R4 と同じ設計判断。 |
| R5 | Codex M-1 | コピー先の検査から公開までの間に、別コピー・実行中の編集を上書きできる | 対応しない | `scripts/superpowers-review-copy.sh:93–115` の競合2ケースは再現した。ただし前回 Spec §7・R5 が明示的に除外した保護範囲の再設計であり、今回ロック・公開方式・注意書き・テスト補強を追加しない。未修正なので解消済みとはしない。 |
| R6 | Codex M-2 | 外部 cwd が TOPLEVEL・helper 配置元になる | 対応しない | 外部 cwd の空・明示 CODE_ROOT・remote 2件はいずれも終了0で外部 checkout を返し、helper は不存在。親 cwd では明示 CODE_ROOT を正しく解決し、remote 2件を拒否。前回 Spec §7・R6 の親 cwd 前提を維持する。 |
| R7 | DeepSeek I-1 | 過去 Plan が後続修正を反映していない | 対応しない | Plan `:777–779` に旧 TOPLEVEL 記述は残るが、`docs/superpowers/README.md:45` と運用 Spec §7 は Plan を実装過程の記録と定める。過去手順の同期や補足テストは行わない。 |
| R8 | DeepSeek・Claude の未検証候補 | 相対 allowed-tools と別パス DOC_ROOT の許可照合 | 対応しない | `review-fix-planning:4,62–69` の記載は確認したが、Claude Code で許可照合が誤動作する実証がなく、数行修正で潜在バグを除けるとも確定しない。前回と同じ未検証の互換性懸念。 |
| R9 | DeepSeek L-3（解消記録） | linked TOPLEVEL 経路が fetch 後に helper で拒否される | 解消済み | `pr-review:122–128` は linked cwd・同一リポジトリ PR を終了66と main checkout 案内で早期拒否。`333f4fb9bb70` の修正と回帰テストが現行 HEAD で機能する。fork 経路の別の抜けは R12 として扱う。 |
| R10 | Claude I-1 | Spec・Plan の approved と実施済み項目・未チェック欄の状態管理 | 対応しない | 運用 Spec `:4,263` と Plan `:6` に包括指示の承認記録があり、前回 Spec §7・R10 が状態補完を対象外にしている。後続作業の完了記録だけで歴史的文書の状態を補正するのではなく、今回も承認運用・状態追跡の設計論点として残す。 |
| R11 | Claude M-1 | zsh の CODE_ROOT 経路で remote を選べない | 対応する (a) | `pr-review:153–164` の `${matches[0]}` は bash で `upstream`、zsh で空。nounset なしなら終了0・remote 空、nounset ありなら終了1・`matches[0]: parameter not set`。正常な main checkout・一致remote 1件で再現した実行不具合。 |
| R12 | DeepSeek L-4 | linked cwd の fork 経路が不要な clone 案内になる | 対応する (a) | `pr-review:131–136` は linked cwd の `external/resoloop` 不在を fork 不備として終了65・clone 案内にする。main checkout に正常な fork がある対照は成功。既存の main checkout 要件を全既知経路で早期に伝える局所修正。 |
| R13 | DeepSeek I-2 | ssh:// 形式の GitHub remote を認識しない | 対応する (a) | `pr-review:110–117` とコピー helper `:21–26,48–50` は `ssh://git@github.com/...` を空へ変換する。外部 CODE_ROOT は一致remote 0件として終了66、正しい create-reso-world の DOC_ROOT・PARENT_ROOT も終了1。第三者だけの互換性ではなく、文書管理リポジトリ自身の通常の remote 設定でも停止する。 |

レビュー中の Test suggestions は新たな修正指示として数えない。R11〜R13 に直接対応する回帰テストだけを採用し、解消済み・対応しない項目への追加補強は行わない。

## 4. 再現・既存検証の結果

| ケース | 現行 HEAD での観測 |
| --- | --- |
| 親 main cwd・外部 main CODE_ROOT・upstream だけ一致（bash） | 終了0、`PR_REMOTE=upstream` |
| 同じ条件（zsh 5.9、nounset なし） | 終了0、`PR_REMOTE` は空 |
| 同じ条件（zsh 5.9、`set -euo pipefail`） | 終了1、`matches[0]: parameter not set` |
| 親 linked cwd・ResoLoop PR・CODE_ROOT 空 | 終了65、linked cwd 配下の fork clone を案内 |
| 親 main cwd・正常な fork（fork・上流 PR の対照） | 終了0、remote はそれぞれ origin・upstream |
| 親 linked cwd・create-reso-world PR | 終了66、main checkout 案内、正常値出力なし |
| 親 main cwd・外部 linked CODE_ROOT | 終了66、CODE_ROOT linked worktree 案内 |
| 親 main cwd・remote 0件の CODE_ROOT | 終了66、exact-one-remote の明確な拒否 |
| 親 main cwd・ssh:// remote の外部 CODE_ROOT | 終了66、誤って一致remote 0件と判定 |
| 正しい create-reso-world DOC_ROOT の origin を ssh:// にする | コピーは終了1、`--doc-root origin is not ...` |
| 独立した DOC_ROOT は HTTPS、PARENT_ROOT だけ ssh:// にする | コピーは終了1、`--parent-root origin is not ...` |
| 親とは別の DOC_ROOT の新規・更新コピー | `created:` / `replaced:`、両方0、正本blobと一致、親は未変更 |
| コピーAを公開直前で止め、Bを同名公開してA再開 | B・Aとも終了0、BがAで上書きされる |
| 旧版照合後・公開直前にユーザ注記を加える | 終了0、注記が消える |

再現は既存テストと同じ resolver 抽出方式で22ケースを約1.18秒で実行し、PARENT_ROOT の ssh:// 拒否は独立 checkout の追加対照でも確認した。DOC_ROOT を linked worktree にした場合は remote 設定を親と共有するため、そのケースだけでは親側の URL 検査を独立に証明できないことを区別した。

初回の再現スクリプトは「zsh でも終了0」を期待して中断した。根拠を調べると、テスト harness が有効にした nounset により、同じ配列添字の不具合が終了1として現れていた。対象コードは変えず、nounset あり・なしの両方を観測するようスクラッチの期待値を修正した。

既存の限定検証:

- `pr-review/tests/test_pr_review_skill_contract.py` と `review-fix-planning/tests/test_review_fix_planning_skill_contract.py`: **52 passed in 1.69s**。
- `bash tests/scripts/test-superpowers-review-copy.bash`: **PASS**。

上記は baseline の成功であって、未追加の R11〜R13 回帰テストの成功ではない。重い一括検証は計画フェーズでは実行していない。全検証ファイル・ログ・フィクスチャを一意な一時ルート内に閉じ込め、fixture の linked worktree を外し、最後に検証 worktree の remove 成功後に親の一時ルートも削除した。Spec 作成・承認待ちには残していない。teardown 前の PR API 再確認でも対象 HEAD は変わっていなかった。

## 5. 修正設計

### R11: 配列添字に依存しない remote 選択

対象:

- `.agents/skills/pr-review/SKILL.md`
- `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

一致件数と一致した remote 名をスカラー変数で保持する。remote のループ、比較対象の owner/repo、0件・複数件の終了66、MAIN_ROOT の確定方式は維持する。件数1を確認した後で、そのスカラーの remote 名を PR_REMOTE に設定する。bash/zsh の全体的な動作設定を変更せず、`${matches[0]}` だけに依存する原因を除く。

既存の明示 CODE_ROOT テストを bash・zsh で実行できる最小限の harness にする。少なくとも origin 一致、origin 不一致・upstream 一致、remote 0件・複数件の拒否を確認する。zsh のない環境では zsh ケースだけ明示的に skip し、この Dev Container では実行する。remote 空でもテストが成功したと誤認しないよう、stdout を含む結果の扱いを明確にする。

固定の `bash -c` でスキル全体を包む案は、利用者へのシェル変更要求となるため採用しない。将来の保険としての別ガード・共通 shell library も追加しない。

### R12: fork 検査の前に linked TOPLEVEL を拒否

対象は R11 と同じ2ファイル。

既存の TOPLEVEL 経路と同じ git-dir / git-common-dir の実パス比較を、fork 分岐の FORK_ROOT 検査より前にも適用する。linked worktree なら stderr に linked worktree・create-reso-world の main checkout・対象パスを示し、終了66にする。正常な MAIN_ROOT を出力せず、clone 案内・fetch・helper に到達させない。手順2の本文も、fork 経路の cwd が main checkout を要求することを短く示す。

回帰テストは `usaturn/resoloop` と `orange3134/resoloop` の両方について linked cwd を渡し、終了66、main checkout 案内、clone 案内がないこと、stdout が空であることを確認する。同じ fixture の main cwd では既存 fork を選べること、main cwd に fork が本当にない場合は従来の終了65・clone 案内を維持することも確認する。

main checkout の自動探索・自動切替、別 fork の clone、helper の main checkout 要件緩和は行わない。

### R13: 2箇所の GitHub URL 判定に ssh:// 形式を追加

対象:

- `.agents/skills/pr-review/SKILL.md`
- `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`
- `scripts/superpowers-review-copy.sh`
- `tests/scripts/test-superpowers-review-copy.bash`

両方の `github_repository` に、`ssh://git@github.com/<owner>/<repo>` と末尾 `.git` を許す同じ正規化規則を追加する。既存の HTTPS・SCP形式と同じ owner/repo を返すようにする。レビューの推奨正規表現をそのまま転記せず、既存の sed ERE の書き方に合わせる。

テストは HTTPS・SCP形式・ssh:// 形式・不一致 host の入力を比較し、resolver の main checkout・外部 CODE_ROOT・fork の正常な remote 照合と、コピーの DOC_ROOT・PARENT_ROOT の双方を確認する。コピー側の根拠では独立した main checkout を使い、片方だけ remote 形式を変えたケースも含める。不一致リポジトリ・host の拒否と、既存コピー検査を維持する。

任意 host・ポート・ユーザ・GitHub Enterprise への汎用化、2関数の共通モジュール化、依存ライブラリ追加は行わない。

## 6. 承認後の検証と反映

各項目の回帰テストを先に追加し、現行コードで失敗することを確認してから、対象の実装を変更する。

| 検証 | 合格条件 |
| --- | --- |
| `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py` | R11 の bash/zsh remote 選択、R12 の fork linked cwd、R13 の URL形式ケースと既存 resolver ケースが成功 |
| `bash tests/scripts/test-superpowers-review-copy.bash` | R13 の両rootの ssh:// ケース、不一致拒否、既存のコピー・更新・静的保護ケースが成功 |
| `bash -n scripts/superpowers-review-copy.sh tests/scripts/test-superpowers-review-copy.bash` | 構文エラーなし |
| `uv run pytest tests/skills .agents/skills` | スキル変更の必須検証が成功 |
| `bash .devcontainer/run-tests.bash` | 環境変更の必須検証が成功 |
| `bash scripts/check-layout.sh` | 配置検査が成功 |

失敗した場合は commit・push せず、原因と未実施事項を報告する。範囲外の問題を独断で修正しない。今回変更しないワールドの pytest、ResoLoop fork の全テストは commit/push の条件にしない。

成功後は origin を fetch し、PR #16 が open であること、対象ブランチの最新先端、並行更新の有無を確認する。`docs/superpowers-document-lifecycle` に Spec と修正を commit して既存 PR #16 へ push する。main・別の review-fixes ブランチ・第二PRは使わない。push 後は指定 helper で同 PR に分類・判断・結果の日本語コメントを投稿または更新する。モデル識別子は pi-model-name の手順で取得する。

## 7. 対象外の論点と作業記録

- R3・R4: remote-less checkout・他リポジトリ実装への適用範囲は、現行 AGENTS.md の限定を維持する。
- R5: 同名コピー同時実行・実行中の編集の保護範囲は変更しない。
- R6: 外部 cwd からのレビュー起動は支えず、親 cwd の前提を維持する。
- R7・R10: 歴史的文書の現行手順への同期、包括指示の承認・状態追跡の補完は行わない。
- R8: Claude Code の外部 DOC_ROOT 許可パターンは実証がなく、今回は変更しない。

### 計画フェーズのチェックリスト

- [x] レビュー全ファイル・対象HEADを確認
- [x] PR・リポジトリ・現行HEADを確定
- [x] committed blob で検証し、一時領域を撤去
- [x] 全指摘を4区分へ分類
- [x] brainstorming で bounded 経路・修正方針を決定
- [x] Spec を保存・自己確認
- [x] 本版を提示して明示承認を得る（2026-10-04、ユーザの「進めて。」）

### 所要時間

- 着手: 2026-10-04 00:59頃 JST。
- 入力・PR・規約確認、一時worktree準備: 約2分。
- 文書照合の委譲・調整役の確認: 約7分。最初の根拠取得不能の委譲と、blob を渡した再調査を含む。
- 挙動再現・限定テスト・teardown: 約5分。最小再現・pytest 自体は数秒。
- 分類・bounded設計・Spec作成・自己確認: 約5分。
- 全体: 約19分（計画のみ。経過区間の概算であり、モデル生成時間の計測ではない）。

## 8. 承認後の実装・検証記録

既存の `docs/superpowers-document-lifecycle` worktree で実装した。実装変更は §5 の4ファイルだけで、ユーザの別作業の未コミット差分は取り込んでいない。

- R11: 一致数と remote 名をスカラーで保持するよう変更。bash・zsh の既定／nounset の成功・0件・複数件を実行検証。
- R12: 同一リポジトリ経路と両 ResoLoop owner の共通 TOPLEVEL 検査を fork lookup より前へ配置。自動 checkout 切替はしない。
- R13: 両 `github_repository` に同じ ssh:// 規則を追加。resolver と独立した両コピー root の成功・不一致拒否を実行検証。

### TDD の実行証拠

実装ファイルを変える前に、次の回帰テストが期待した原因で失敗することを確認した。

| 対象 | RED 結果 | GREEN 結果 |
| --- | --- | --- |
| R11 | 4 failed / 8 passed。zsh の空remote・nounsetエラー | resolver 全59テスト成功 |
| R12 | 2 failed / 6 passed。両ownerで終了66に対し実際は65・clone案内 | resolver 全59テスト成功 |
| R13 resolver | 6 failed / 5 passed。正しいssh URLの拒否 | resolver 全59テスト成功 |
| R13 copier | 両root・末尾.gitあり／なしの独立4ケースが失敗 | 追加ケースと既存コピー保護の全検査成功 |

### 実装役の最終必須検証

| コマンド | 実行結果 | 実測秒 |
| --- | --- | ---: |
| `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py` | 59 passed、終了0 | 4.777 |
| `bash tests/scripts/test-superpowers-review-copy.bash` | PASS、終了0 | 2.550 |
| コピー helper と bash テストの個別 `bash -n` | いずれも終了0 | 各0.03未満 |
| `uv run pytest tests/skills .agents/skills` | 306 passed / 1 skipped、終了0 | 14.976 |
| `env -u TMPDIR bash .devcontainer/run-tests.bash` | 26件すべてPASS、終了0 | 59.317 |
| `bash scripts/check-layout.sh` | PASS、終了0 | 1.855 |
| `git diff --check` | 終了0 | 0.032 |

skip は既存の `test_targeted_skill_semantics` のみ（SKILL_UNDER_TEST 未指定）。zsh の回帰テストは実行され、skip していない。最終検証に警告はない。

初回の Dev Container 検証では、ログ wrapper が TMPDIR を作業リポジトリ内へ変更したため、非Git・非.venvディレクトリを前提にする herdr-status・shell-tools・check-layout の3検査が失敗した。fixture から親の .git / .venv が見つかる検証配置が原因で、対象コードや検証スクリプトは変更していない。TMPDIR 上書きを外した再実行と最終再実行では全26件成功した。初回失敗を未修正の実装不具合として扱わない。

読み取り専用の Task レビューは Spec compliance・Task quality とも Approved、Critical・Important・Minor の指摘なし。既存コピー保護の実行証拠は調整役が最終コピー検査・Dev Container 検証のログを直接確認した。LSP の能動チェックは指摘0だったが、bash系2ファイルの coverage は inconclusive のため、全ファイルの clean 確認とは扱わない。

### 調整上の判断

- bounded の承認済み Spec を実行 brief として使い、別の実装計画書は作らない。R11〜R13 は同じ resolver・テストを変更するため1タスクにまとめた。判断が不適切だった場合の影響は手順記録の再整理であり、修正範囲は変わらない。
- 必須検証の完了前に commit しない指示を優先し、実装役は未コミット差分を提出、調整役が検証・レビュー後にまとめて commit する。途中のコミットがないことによる復元負担は、確認した差分・テスト証拠で補う。

実装役の所要時間は18分33秒（読解・RED準備約5分7秒、実装約50秒、検証とfixture配置の切り分け約7分12秒、自己確認・報告約5分24秒）。

### 調整役の最終確認

- resolver の再検証: 59 passed in 4.38s、終了0。
- スキル必須検証の再実行: 306 passed / 1既存skip in 12.88s、終了0。
- コピー検査、個別 bash 構文検査、配置検査、diff check: すべて終了0。
- Dev Container 検証の再実行: 26件すべてPASS、終了0、実時間約56秒。
- skill-creator efficiency check: 終了0、構造上の Issues なし。未変更の description に対するヒューリスティック警告のみ残る。対象外のトリガー再設計は行わない。
- 最終統合レビュー: Critical・Important・Minor なし、今回の変更範囲は Ready to merge。対象外として挙げた論点は既存の R3〜R8・R10 と非標準 SSH URL 形式に限られ、§5・§7 の除外範囲を維持する。
- origin の fetch と PR API 再確認で、ローカル・remote・PR の先端は `333f4fb9bb704fb8934b9f6889453e5812a5dc29`、PR #16 は OPEN、ブランチは指定先のままであることを確認した。並行更新はなかった。

承認後の調整役の着手は01:25 JST。入力・worktree・brief準備約4分、実装委譲約19分、Taskレビュー・証拠確認約12分、再検証・最終統合レビュー・結果記録約11分。公開直前まで約46分で、commit・push・status comment の結果と最終所要時間は同 PR に記録する。経過区間の概算であり、モデル生成時間の計測ではない。
