# Superpowers Spec・Plan の長期保存と公開運用

- 日付: 2026-10-03
- 状態: draft（本 Spec のレビュー待ち。規約・スキルの変更は未実施）
- brainstorming 経路: architectural
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 設計・実装対象リポジトリ: `usaturn/create-reso-world`（規約とスキルの変更）
- 対象 Issue・PR: なし（運用設計段階で未作成）
- 適用対象: すべてのリポジトリに関する Spec・Plan。ResoLoop に限定せず、親リポジトリと無関係なリポジトリの作業も含む。
- 調査時の create-reso-world HEAD: `294ff10`
- 関連 Plan: なし。本 Spec の明示承認後に作成する。

## 1. 意図と確定した条件

設計判断と実装手順を、別セッションや別エージェントが復元できる形で長期保存する。同時に、レビュー回ごとのファイル増殖、承認済み版と未承認版の混同、文書の未追跡状態での放置を避ける。

ユーザが明示した条件:

1. Spec と Plan は両方とも長期保存する。
2. 対象リポジトリを問わず、すべての Spec・Plan を親リポジトリ `usaturn/create-reso-world` に保存・コミットする。`usaturn/resoloop` と `orange3134/resoloop` だけでなく、全く別のリポジトリに関する作業も対象とする。
3. 調査時点で存在した `docs/superpowers/` 配下の文書は、すべて PR に取り込んでよい。
4. 本 Spec の作成・コミット用に、専用 worktree を使用してよい。
5. Spec・Plan の確認をユーザへ依頼する前に、コミット済みの確認対象を、親 checkout の gitignore 対象 `tmp/superpowers-review/` 配下へコピーする。親の `tmp/` 直下や文書 worktree 内の `tmp/` では代用しない。
6. 確認用コピーのパスは必要最低限とし、ファイル名で内容が分かるようにする。関連する Issue・PR がある場合は、その番号を含める。

上記以外の運用の詳細は、本 Spec のレビュー対象である。文書保存の承認は、コード変更や文書に書いた実装手順の実行を承認したことを意味しない。

## 2. 現状と問題

2026-10-03 の親 checkout の調査結果は、Spec 26 件・Plan 12 件、合計 38 件。追跡済みは Spec 4 件・Plan 9 件、未追跡は Spec 22 件・Plan 3 件である。専用 worktree は HEAD の追跡済み文書から開始しており、未追跡 25 件は親 checkout に残っている。

- `AGENTS.md` は Spec・Plan の保存先を規定し、`.gitignore` は `docs/superpowers/` を除外していない。
- `.agents/skills/review-fix-planning/SKILL.md` は ResoLoop の Spec も create-reso-world 側に保存する。一方、実装後の commit・push はコード対象のリポジトリに対する手順であり、文書側のコミット手順が明確でない。
- Spec の状態表記が揃っておらず、Plan のチェックボックスだけでは全体の状態が分からない。
- レビュー回ごとに新規 Spec が作られ、同じテーマの判断が複数ファイルへ分散している。
- `agent-handoff` は Spec・Plan のパスを参照するため、無条件の削除や移動は引き継ぎを壊す。
- 現在の `AGENTS.md` と `pr-review` は対象リポジトリを create-reso-world と ResoLoop に限定している。任意のリポジトリを扱うには、対象の明示と照合を維持したまま、その限定を改める必要がある。

## 3. 保存先とリポジトリ境界

### 3.1 文書とコードを分ける

`PARENT_ROOT`、`DOC_ROOT`、`CODE_ROOT` を別の値として扱う。

- `PARENT_ROOT`: ユーザが確認用ファイルを読む create-reso-world の親 checkout の絶対パス。この作業では `/workspaces/reso-world`。文書 worktree を作る前に記録し、別リポジトリの cwd から推測しない。
- `DOC_ROOT`: `origin` が `usaturn/create-reso-world` であることを確認した、正本を作成・コミットする checkout または worktree。`PARENT_ROOT` に対応する文書作業先として明示する。
- `CODE_ROOT`: ユーザの依頼または確認済みの引き継ぎで明示された、実装対象の checkout または worktree の絶対パス。親リポジトリ配下にある必要はない。

次の表は代表例であり、対象リポジトリの許可リストではない。

| 設計・実装の対象 | Spec・Plan の正本の保存・コミット先 | コードの反映先 |
| --- | --- | --- |
| `usaturn/create-reso-world` | `DOC_ROOT` の create-reso-world | 対象の create-reso-world ブランチ・PR |
| `usaturn/resoloop` | `DOC_ROOT` の create-reso-world | ResoLoop fork の対象ブランチ・PR |
| `orange3134/resoloop` | `DOC_ROOT` の create-reso-world | 上流 PR の head である fork ブランチ |
| その他の任意のリポジトリ | `DOC_ROOT` の create-reso-world | 明示・照合した対象リポジトリのブランチ・PR |

create-reso-world 以外には Spec・Plan の正本を保存・コミットしない。二重管理もしない。コード対象の cwd で実行した `git rev-parse --show-toplevel` を、そのまま `DOC_ROOT` や `PARENT_ROOT` とみなしてはならない。

任意のリポジトリを扱うときは、対象の正確な識別子（GitHub なら `owner/repo`、それ以外ならリポジトリ URL 等）、checkout のパス、branch・HEAD、既存 PR があればその URL を確認し、remote と照合する。fork からの PR では PR の base リポジトリと head リポジトリを区別し、push 先を確認する。ローカル専用で remote が無い場合は、その checkout を対象とする明示指示を確認する。複数候補や不一致がある場合は停止し、都合のよい作業先を選ばない。

対象 checkout の `AGENTS.md` 等も適用し、コード変更の許可と検証規則を確認する。文書を集約する方針は、あらゆるリポジトリのコード変更、clone、push、PR 作成を許可したことを意味しない。新規取得や fork の作成は、この方針だけを根拠に自動実行しない。既存の ResoLoop remote 検証、PR の HEAD 整合性、隔離 worktree の利用などの安全策は維持する。

親 checkout、文書管理リポジトリ、コード対象のいずれかを特定できない場合は、推測せず停止して確認する。既知の3リポジトリ以外であることだけを理由に拒否せず、明示された作業先と対象の照合で判断する。

### 3.2 ディレクトリ

- Spec: `DOC_ROOT/docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plan: `DOC_ROOT/docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- 検討メモ、実行ログ、一時的なスクラッチ: 既存のローカル専用領域。正式な Spec・Plan の代わりにはしない。

ワールドのプロジェクト、ResoLoop、その他の無関係なリポジトリを cwd にしていても、Spec・Plan の正本の保存先は上記で変わらない。インストール済み Superpowers スキルの配置規則は、親リポジトリの指示によって上書きする。別リポジトリで起動するエージェントにも、引き継ぎでこの方針と `PARENT_ROOT`・`DOC_ROOT` を明示する。インストール済みスキルそのものは変更しない。

### 3.3 ユーザ確認用コピー

Spec・Plan をユーザへ提示して確認・承認を依頼する前に、`DOC_ROOT` でコミット済みの確認対象を、`PARENT_ROOT/tmp/superpowers-review/` へコピーする。確認用コピーはこのディレクトリの直下に置く。親の `tmp/` 直下には置かず、SHA のディレクトリや正本のディレクトリ構造を複製した追加階層も作らない。

- Spec: `PARENT_ROOT/tmp/superpowers-review/<内容が分かる短い名前>-spec.md`
- Plan: `PARENT_ROOT/tmp/superpowers-review/<内容が分かる短い名前>-plan.md`

ファイル名は主題と文書種別を表し、`spec.md`・`plan.md` のような汎用名だけにはしない。関連する Issue・PR がある場合は主対象の番号を含め、別リポジトリの同番号案件と区別するために短いリポジトリ名を添える。名前の形式は `<repo>-pr<N>-<topic>-spec.md`、`<repo>-issue<N>-<topic>-plan.md` などとする。番号のない案件では内容を表す名前だけを使い、番号を発明しない。日付や SHA をファイル名へ一律に追加しない。

命名例:

- PR に関する Spec: `tmp/superpowers-review/resoloop-pr9-list-shrink-spec.md`
- Issue に関する Plan: `tmp/superpowers-review/<repo>-issue<N>-<topic>-plan.md`
- 本 Spec の確認用コピー: `tmp/superpowers-review/superpowers-doc-storage-spec.md`（Issue・PR は未作成）

同じ repo 名・番号・主題が別 owner や別作業で衝突する場合は、そのときだけ owner 等の短い識別子を加える。複数版を同時に確認する必要がある場合は、そのときだけ `-r2` 等の版識別子を加える。確認中のファイルを無断で差し替えない。既存のコピーを更新できるのは、以前提示したコミット版と一致する同じ作業のコピーであり、旧版の確認が終了し、修正・更新が明示された場合だけとする。別作業のファイルやユーザの編集内容を上書きしない。

確認対象の完全な文書コミット SHA と正本のリポジトリ相対パスは、確認依頼・承認記録に記載する。SHA はパスではなく記録で保持する。文書の SHA はコード対象の HEAD と区別し、Spec の初回・再レビューと Plan のレビューのすべてで、コピーと正本の版を対応付ける。コピー先には正本と同じバイト列を置き、内容やリンクを確認用に書き換えない。相対リンクが短いコピー先で成立しない場合は、参照する正本と、必要な関連文書の確認用コピーを別途案内する。

手順は、正本のコミット、親 checkout のコピー先に対する `git check-ignore` の確認、コミット済み blob からのコピー、内容一致の検証、短いコピー先パスと正本の SHA・相対パスの提示、の順とする。コピーは対象コミットを元に作成し、未コミットの作業ツリーをそのまま提示しない。コピー作成や検証に失敗したら、worktree のパスだけを代わりに提示してレビュー開始済みとは扱わず、失敗を報告する。

既存の異なる内容や symlink を無条件で上書きしない。コピー先の親ディレクトリも確認し、symlink 等によって親 checkout の `tmp/superpowers-review/` 外へ解決される場合は停止する。確認用コピーは Git の追跡対象にせず、`git add -f` で追加しない。正本のコミットは `docs/superpowers/` 側で行い、`tmp/` は長期保存や引き継ぎの正本として扱わない。ユーザがコピーを編集した場合は差分を確認し、正本へ反映・再コミット・再コピーしてから、更新版の確認を依頼する。コピーの編集だけで正本が変更・承認されたとは扱わない。

## 4. 文書単位と更新

新規作成する文書は、原則として 1 テーマ 1 Spec とし、対応する Plan を関連付ける。独立した設計変更や、大きな設計の実装フェーズは別文書に分けてよい。Spec・Plan の作成が必要かどうかは、使用するスキルとユーザ指示に従う。長期保存の方針だけを理由に、すべての小さな作業で両方を作成することは要求しない。

同じテーマのレビュー修正では、原則として既存文書を更新し、過去の版を Git 履歴に残す。各版のレビュー入力、対象コード HEAD、対応・非対応の根拠は、その版だけで読める形にする。現行版には、継続して効く決定事項と対象外の範囲も残す。既に承認した版を、コミットせず上書きした状態で引き継がない。

新規の Issue・PR 関連文書の topic には、リポジトリを識別する語、関連する主対象の番号、内容を表す語を含め、別リポジトリの同番号案件と区別する。例: `usaturn-resoloop-pr9-list-shrink-review-fixes`。この正本の命名は既存文書へ遡って適用しない。確認用コピーは第3.3節の短い命名を使う。

完了・取りやめ・後継への置換後も削除せず、現在のパスに残す。自動アーカイブ、定期削除、既存ファイルの一括リネームは導入しない。

## 5. 状態と承認済み版

新規作成・今後更新する正式文書の冒頭には、既存スキルが要求する項目に加えて、以下を記載する。

- 文書管理リポジトリ: `usaturn/create-reso-world`
- 設計・実装対象の正確なリポジトリ識別子（GitHub なら `owner/repo`）、対象 Issue・PR の URL（未作成ならその旨）
- 対象コードの HEAD（コードを検証した文書の場合）
- 文書の状態
- 関連する Spec・Plan。置換した場合は後継文書への参照。

状態は次の意味で使う。

| 状態 | 意味 |
| --- | --- |
| draft | 文書の明示承認をまだ得ていない |
| approved | 指定された版の内容について明示承認を得た |
| completed | その文書の作業が完了した。結果と検証根拠を併記する |
| superseded | 後継文書へ置き換えた。後継を参照する |
| cancelled | 取りやめた。理由を残す |

`completed` はコードのマージ済み・リリース済みを意味しない。マージ・公開の状態は、対象 PR や結果の記録で区別する。文書をコミットしただけで `approved` にしてはならない。

承認する際は、第3.3節の親 checkout の `tmp/superpowers-review/` にある確認用コピーを案内し、文書リポジトリのコミット SHA と正本のファイルパスも提示する。承認は内容一致を確認したその版へ結び付ける。承認済み版の SHA はチャット・承認記録・handoff に記録する。コミット自身の SHA を同じコミット内の文書へ埋め込むことは要求しない。

設計・対応範囲・検証条件などの実質的な変更は再承認を必要とする。承認記録の追記、状態変更、誤字訂正だけでは、承認された設計内容を変更しない。Spec の承認と Plan の承認、実行方法の選択は、Superpowers の各段階のゲートとして引き続き分ける。

## 6. コミット、公開、引き継ぎ

正式な Spec・Plan の作成または更新がまとまったら、承認前でも `draft` のまま `DOC_ROOT` の文書作業ブランチへコミットする。文書を提示して承認待ちになる時点、または引き継ぐ時点で、正式文書を未追跡・未コミットのまま放置しない。draft のコミットは、実装開始の許可ではない。

文書のコミットは create-reso-world だけで行う。文書とコードが別リポジトリにある場合は、片方の成功をもう片方の成功とみなさず、それぞれの SHA・反映先・結果を報告する。文書のコミットに失敗した場合は、失敗と残存パスを報告し、保存完了や引き継ぎ完了を宣言しない。

公開方法:

1. create-reso-world 自身の変更に伴う文書は、対象作業ブランチ・PR に含める。
2. create-reso-world 以外の任意のリポジトリの変更に伴う文書は、create-reso-world の文書用ブランチ・文書専用 PR で公開する。同じテーマの文書 PR が既にあれば更新し、レビュー回ごとに新しい文書 PR を作らない。コード側に PR があれば相互参照し、PR が無い場合は対象リポジトリ・ブランチ・コミットを記録する。
3. 文書専用 PR は文書管理リポジトリ側の公開経路であり、コード修正用の第二 PR ではない。`review-fix-planning` の「既存コード PR に反映する」規則は維持し、別リポジトリの文書専用 PR だけを明示的な例外として扱う。
4. コミット、push、PR 作成、マージは別の段階である。この保存方針は、push・PR 作成・マージを自動で許可しない。ユーザまたは選択したワークフローの明示指示に従う。

ローカルコミットだけの場合は、報告と handoff に「公開未実施」と記載する。公開済みの文書は、ブランチ先端だけでなくコミットを指定したリンクで参照する。未公開コミットの GitHub リンクを、第三者が読めるものとして提示しない。

handoff は、文書管理リポジトリ、`PARENT_ROOT`、実際の `DOC_ROOT`、文書のコミット SHA・正本のパスと、コード側のリポジトリ・`CODE_ROOT`・ブランチ・HEAD・PR を区別して記録する。`tmp/superpowers-review/` の確認用コピーは閲覧補助としてのみ記録し、復元元はコミット済みの正本とする。別環境への受け渡しでは、文書コミットが取得可能な公開 ref または、既存の引き継ぎ手順が認める復元可能なアーティファクトを用意し、復元を検証する。ローカルパスだけでは別環境での再開可能性を保証しない。

## 7. 履歴と現行仕様

Spec・Plan は判断と実装過程の記録であり、完了後も保存する。ただし、完了した Plan の手順を現在の環境で再実行してよいという意味ではない。

現在の操作方法・対応範囲など、利用者が参照する必要がある仕様は、各対象リポジトリの通常の README やドキュメントへ反映する。通常のドキュメントを更新することは、Spec・Plan の正本を親以外のリポジトリへ保存することとは異なる。

`docs/superpowers/README.md` に保存先、状態、承認済み版の扱い、公開先、`tmp/superpowers-review/` の確認用コピー、履歴と現行仕様の違いを短く記載する。全履歴を手作業で列挙する索引は作成しない。

## 8. 既存文書の取り込み

調査時点の既存 38 件は、削除・統合・リネーム・本文の一括修正をせず保持する。親 checkout の未追跡 25 件は、下記の対象一覧を固定して create-reso-world の文書 PR に取り込む。既に追跡済みの 13 件を重複追加しない。

取り込み前に、親 checkout と文書作業ブランチの同名ファイルの有無・内容を照合する。コピーとコミットの前後で内容を確認し、元ファイルを削除しない。同名の異なる内容や作業中の変更が見つかった場合は、勝手に上書きせず停止して確認する。一覧外の新しい文書を一括ステージしてはならない。取り込む内容について、機密情報と参照切れも確認する。問題を見つけた場合は報告し、承認済みの保存方針を理由に無条件で公開しない。

既存文書に `draft` 等のヘッダーを遡って追加することは、取り込みの条件にしない。過去文書の存在は、実装済みや承認済みを意味しない。状態の補足は、後からその文書を更新する場合に確認できた事実だけを記録する。

### 未追跡 25 件の取り込み対象

以下は親 checkout のリポジトリルート基準のパス。新しい文書 worktree にまだ存在しないことは、取り込み前の状態として意図したものである。

```text
docs/superpowers/plans/2026-09-30-list-shrink-recreate-round6-review-fixes.md
docs/superpowers/plans/2026-10-02-pr9-list-shrink-round2-review-fixes.md
docs/superpowers/plans/2026-10-03-pr9-list-shrink-round3-review-fixes.md
docs/superpowers/specs/2026-09-29-asset-url-save-migration-review-fixes-design.md
docs/superpowers/specs/2026-09-29-asset-url-save-migration-round2-review-fixes-design.md
docs/superpowers/specs/2026-09-29-asset-url-save-migration-round3-review-fixes-design.md
docs/superpowers/specs/2026-09-29-list-shrink-recreate-review-fixes-design.md
docs/superpowers/specs/2026-09-29-list-shrink-recreate-round2-review-fixes-design.md
docs/superpowers/specs/2026-09-29-list-shrink-recreate-round3-review-fixes-design.md
docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-review-fixes-design.md
docs/superpowers/specs/2026-09-29-slot-snapshot-dedup-round2-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round4-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round5-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round6-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round7-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round8-review-fixes-design.md
docs/superpowers/specs/2026-09-30-list-shrink-recreate-round9-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pi-gpt-6.1-sol-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr8-round2-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr8-round3-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr8-round4-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr8-round7-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr9-list-shrink-review-fixes-design.md
docs/superpowers/specs/2026-10-02-pr9-list-shrink-round2-review-fixes-design.md
docs/superpowers/specs/2026-10-03-pr9-list-shrink-round3-review-fixes-design.md
```

## 9. 実装対象と対象外

本 Spec の承認後に作成する Plan では、次の変更を扱う。

- `AGENTS.md`: 全リポジトリの文書の長期保存、固定した文書管理リポジトリ、`PARENT_ROOT`・`DOC_ROOT`・`CODE_ROOT` の区別、任意の明示された対象 checkout の照合、コミット・公開段階、レビュー前の `tmp/superpowers-review/` へのコピーを明文化する。
- `docs/superpowers/README.md`: 運用の簡潔な案内を追加する。
- `.agents/skills/pr-review/`: 明示された任意の GitHub PR 対象 checkout を解決する経路を加え、既存の remote・HEAD・隔離 worktree 等の安全策と整合させる。文書保存の集約をレビュー出力やコードの保存先変更と混同しない。
- `.agents/skills/review-fix-planning/`: 任意対象の識別、Spec 更新、文書側コミット・公開経路、レビュー前の確認用コピーを、コード反映手順と分離する。
- `.agents/skills/agent-handoff/`: 親 checkout、文書とコードの復元元、閲覧補助コピーを区別する記録・検証を整合させる。handoff 自体の保存先は今回変更しない。
- `.agents/skills/planning-parallel-issues/`: 任意対象の識別、固定した文書管理リポジトリと確認用コピー、既存のアーティファクト公開・復元手順の参照を整合させる。Issue・claim の管理先は今回変更しない。
- 上記規約の既存テストと、任意対象 checkout の照合、親 `tmp/superpowers-review/` の ignore・コピー一致・レビュー順序を検証する回帰テスト。
- 第8節の既存未追跡文書の取り込み。

対象外:

- 文書運用と無関係な対象リポジトリのコード・設定の変更、create-reso-world 以外への Spec・Plan の正本の保存・コミット。
- インストール済み Superpowers スキルの直接変更。
- 自動コミット・自動 PR 作成ツール、定期掃除、全履歴の索引生成。
- checkout の自動探索・clone、非 GitHub サービス向けの新規 PR 連携、Issue・claim の管理先変更。
- `.gitignore` で `docs/superpowers/` を一括除外すること。
- 既存文書の一括再編集、ローカル handoff やレビュー成果物の一括 Git 管理への変更。
- 本 Spec の承認を省略した規約・スキルの実装。

## 10. 検証と完了条件

実装時は既存の環境・スキル変更の検証規則に従い、関連するテストに加えて、以下を同期実行して結果を確認する。

- `bash .devcontainer/run-tests.bash`
- `bash scripts/check-layout.sh`
- `uv run pytest tests/skills .agents/skills`

規約・テスト・手順の確認では、少なくとも以下の経路を扱う。

1. create-reso-world 自身の案件: Spec・Plan とコードを対象 PR へ含め、別テーマの未追跡文書を混入させない。
2. ResoLoop fork と upstream、親とは無関係なリポジトリの案件: すべての Spec・Plan の保存・コミット先が create-reso-world となり、コードの反映先と混同しない。親の外にある checkout、remote の不一致、複数候補、明示されたローカル専用 checkout も扱う。
3. 文書の承認・更新・完了: コミットだけで承認済みにせず、承認された版を復元でき、過去版を再実行しない。
4. ローカルのみの保存、公開済みの保存、コミット失敗: 公開状態と復元可能性を区別し、失敗を完了扱いしない。
5. 既存文書取り込み: 対象一覧の件数・内容を照合し、既存ファイル、親 checkout、既存リンクを変更しない。参照切れを検出した場合は一覧と対応判断を残す。
6. Spec と Plan の初回・再レビュー: 依頼前に親 checkout の `tmp/superpowers-review/` 直下に、内容と文書種別が分かる短いファイル名の確認用コピーが存在し、gitignore 対象で、提示した文書コミットの blob と一致する。関連する Issue・PR の番号があればファイル名に含め、番号がなければ発明しない。親の `tmp/` 直下、文書 worktree 内、コード checkout 内のコピーは代用しない。SHA 等の追加階層を作らない。コピー失敗、別 owner の同番号案件の衝突、確認中の版の差し替え、異なる既存内容、symlink、未コミット内容の混入を検出し、確認用コピーをステージしない。

完了条件は、規約と関連スキルの記述が一致し、既存文書の取り込みが確認され、上記検証が通り、全リポジトリの文書の保存・公開先と、親 `tmp/superpowers-review/` のレビュー経路を明示できることである。push・PR 作成が許可されていない場合はローカルコミットまでを報告し、公開作業は未実施と明記する。

## 11. 次のゲート

本 Spec を create-reso-world の専用ブランチへコミットし、その版を親 checkout の gitignore 対象 `tmp/superpowers-review/` へコピーして内容一致を検証した後、コピー先を案内して書かれた内容への明示承認を待つ。承認後は `writing-plans` で実装 Plan を作成する。Plan もコミット・親 `tmp/superpowers-review/` へのコピー・検証後にレビューを依頼し、Plan の承認と実行方法の選択を経てから規約・スキルの変更へ進む。
