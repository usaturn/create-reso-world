# Superpowers Spec・Plan の長期保存と公開運用

- 日付: 2026-10-03
- 状態: draft（本 Spec のレビュー待ち。規約・スキルの変更は未実施）
- brainstorming 経路: architectural
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 設計・実装対象リポジトリ: `usaturn/create-reso-world`（規約とスキルの変更）
- 対象 Issue・PR: なし（運用設計段階で未作成）
- 適用対象: `usaturn/create-reso-world`、`usaturn/resoloop`、`orange3134/resoloop`
- 調査時の create-reso-world HEAD: `294ff10`
- 関連 Plan: なし。本 Spec の明示承認後に作成する。

## 1. 意図と確定した条件

設計判断と実装手順を、別セッションや別エージェントが復元できる形で長期保存する。同時に、レビュー回ごとのファイル増殖、承認済み版と未承認版の混同、文書の未追跡状態での放置を避ける。

ユーザが明示した条件:

1. Spec と Plan は両方とも長期保存する。
2. `usaturn/resoloop` と `orange3134/resoloop` に関する Spec・Plan も、`usaturn/create-reso-world` にコミットする。
3. 調査時点で存在した `docs/superpowers/` 配下の文書は、すべて PR に取り込んでよい。
4. 本 Spec の作成・コミット用に、専用 worktree を使用してよい。

上記以外の運用の詳細は、本 Spec のレビュー対象である。文書保存の承認は、コード変更や文書に書いた実装手順の実行を承認したことを意味しない。

## 2. 現状と問題

2026-10-03 の親 checkout の調査結果は、Spec 26 件・Plan 12 件、合計 38 件。追跡済みは Spec 4 件・Plan 9 件、未追跡は Spec 22 件・Plan 3 件である。専用 worktree は HEAD の追跡済み文書から開始しており、未追跡 25 件は親 checkout に残っている。

- `AGENTS.md` は Spec・Plan の保存先を規定し、`.gitignore` は `docs/superpowers/` を除外していない。
- `.agents/skills/review-fix-planning/SKILL.md` は ResoLoop の Spec も create-reso-world 側に保存する。一方、実装後の commit・push はコード対象のリポジトリに対する手順であり、文書側のコミット手順が明確でない。
- Spec の状態表記が揃っておらず、Plan のチェックボックスだけでは全体の状態が分からない。
- レビュー回ごとに新規 Spec が作られ、同じテーマの判断が複数ファイルへ分散している。
- `agent-handoff` は Spec・Plan のパスを参照するため、無条件の削除や移動は引き継ぎを壊す。

## 3. 保存先とリポジトリ境界

### 3.1 文書とコードを分ける

`DOC_ROOT` と `CODE_ROOT` を別の値として扱う。

- `DOC_ROOT`: `origin` が `usaturn/create-reso-world` であることを確認した、文書作業用 checkout または worktree。
- `CODE_ROOT`: ルート `AGENTS.md` の「リポジトリ境界」に従って確認した、実装対象の checkout または worktree。

| 設計・実装の対象 | Spec・Plan の保存・コミット先 | コードの反映先 |
| --- | --- | --- |
| `usaturn/create-reso-world` | `DOC_ROOT` の create-reso-world | 対象の create-reso-world ブランチ・PR |
| `usaturn/resoloop` | `DOC_ROOT` の create-reso-world | ResoLoop fork の対象ブランチ・PR |
| `orange3134/resoloop` | `DOC_ROOT` の create-reso-world | 上流 PR の head である fork ブランチ |

ResoLoop 側のリポジトリには Spec・Plan をコミットしない。二重保存もしない。コード対象の cwd で実行した `git rev-parse --show-toplevel` を、そのまま `DOC_ROOT` とみなしてはならない。

専用の文書 worktree に `external/resoloop` が見えなくても、その場所へ別の fork を自動作成しない。文書作業とコード作業の実際のパスをそれぞれ確認する。文書管理リポジトリを特定できない場合、または上表以外のリポジトリが対象の場合は、推測せず停止して確認する。

### 3.2 ディレクトリ

- Spec: `DOC_ROOT/docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plan: `DOC_ROOT/docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
- 検討メモ、実行ログ、一時的なスクラッチ: 既存のローカル専用領域。正式な Spec・Plan の代わりにはしない。

ワールドのプロジェクトや ResoLoop のディレクトリを cwd にしていても、Spec・Plan の保存先は上記で変わらない。インストール済み Superpowers スキルの配置規則は、リポジトリの指示によって上書きする。インストール済みスキルそのものは変更しない。

## 4. 文書単位と更新

新規作成する文書は、原則として 1 テーマ 1 Spec とし、対応する Plan を関連付ける。独立した設計変更や、大きな設計の実装フェーズは別文書に分けてよい。Spec・Plan の作成が必要かどうかは、使用するスキルとユーザ指示に従う。長期保存の方針だけを理由に、すべての小さな作業で両方を作成することは要求しない。

同じテーマのレビュー修正では、原則として既存文書を更新し、過去の版を Git 履歴に残す。各版のレビュー入力、対象コード HEAD、対応・非対応の根拠は、その版だけで読める形にする。現行版には、継続して効く決定事項と対象外の範囲も残す。既に承認した版を、コミットせず上書きした状態で引き継がない。

新規の PR 関連文書の topic にはリポジトリを識別する語と PR 番号を含め、別リポジトリの同番号 PR と区別する。例: `usaturn-resoloop-pr9-list-shrink-review-fixes`。この命名は既存文書へ遡って適用しない。

完了・取りやめ・後継への置換後も削除せず、現在のパスに残す。自動アーカイブ、定期削除、既存ファイルの一括リネームは導入しない。

## 5. 状態と承認済み版

新規作成・今後更新する正式文書の冒頭には、既存スキルが要求する項目に加えて、以下を記載する。

- 文書管理リポジトリ: `usaturn/create-reso-world`
- 設計・実装対象の `owner/repo`、対象 Issue・PR の URL（未作成ならその旨）
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

承認する際は、文書リポジトリのコミット SHA とファイルパスを提示し、承認をその版へ結び付ける。承認済み版の SHA はチャット・承認記録・handoff に記録する。コミット自身の SHA を同じコミット内の文書へ埋め込むことは要求しない。

設計・対応範囲・検証条件などの実質的な変更は再承認を必要とする。承認記録の追記、状態変更、誤字訂正だけでは、承認された設計内容を変更しない。Spec の承認と Plan の承認、実行方法の選択は、Superpowers の各段階のゲートとして引き続き分ける。

## 6. コミット、公開、引き継ぎ

正式な Spec・Plan の作成または更新がまとまったら、承認前でも `draft` のまま `DOC_ROOT` の文書作業ブランチへコミットする。文書を提示して承認待ちになる時点、または引き継ぐ時点で、正式文書を未追跡・未コミットのまま放置しない。draft のコミットは、実装開始の許可ではない。

文書のコミットは create-reso-world だけで行う。文書とコードが別リポジトリにある場合は、片方の成功をもう片方の成功とみなさず、それぞれの SHA・反映先・結果を報告する。文書のコミットに失敗した場合は、失敗と残存パスを報告し、保存完了や引き継ぎ完了を宣言しない。

公開方法:

1. create-reso-world 自身の変更に伴う文書は、対象作業ブランチ・PR に含める。
2. ResoLoop の変更に伴う文書は、create-reso-world の文書用ブランチ・文書専用 PR で公開する。同じテーマの文書 PR が既にあれば更新し、レビュー回ごとに新しい文書 PR を作らない。ResoLoop のコード PR と相互参照する。
3. 文書専用 PR は文書管理リポジトリ側の公開経路であり、コード修正用の第二 PR ではない。`review-fix-planning` の「既存コード PR に反映する」規則は維持し、別リポジトリの文書専用 PR だけを明示的な例外として扱う。
4. コミット、push、PR 作成、マージは別の段階である。この保存方針は、push・PR 作成・マージを自動で許可しない。ユーザまたは選択したワークフローの明示指示に従う。

ローカルコミットだけの場合は、報告と handoff に「公開未実施」と記載する。公開済みの文書は、ブランチ先端だけでなくコミットを指定したリンクで参照する。未公開コミットの GitHub リンクを、第三者が読めるものとして提示しない。

handoff は、文書管理リポジトリ、実際の文書 worktree、文書のコミット SHA・パスと、コード側のリポジトリ・worktree・ブランチ・HEAD・PR を区別して記録する。別環境への受け渡しでは、文書コミットが取得可能な公開 ref または、既存の引き継ぎ手順が認める復元可能なアーティファクトを用意し、復元を検証する。ローカルパスだけでは別環境での再開可能性を保証しない。

## 7. 履歴と現行仕様

Spec・Plan は判断と実装過程の記録であり、完了後も保存する。ただし、完了した Plan の手順を現在の環境で再実行してよいという意味ではない。

現在の操作方法・対応範囲など、利用者が参照する必要がある仕様は、各対象リポジトリの通常の README やドキュメントへ反映する。通常のドキュメントを更新することは、Spec・Plan を ResoLoop 側へ保存することとは異なる。

`docs/superpowers/README.md` に保存先、状態、承認済み版の扱い、公開先、履歴と現行仕様の違いを短く記載する。全履歴を手作業で列挙する索引は作成しない。

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

- `AGENTS.md`: 長期保存、固定した文書管理リポジトリ、コードとの境界、コミット・公開段階を明文化する。
- `docs/superpowers/README.md`: 運用の簡潔な案内を追加する。
- `.agents/skills/review-fix-planning/`: Spec 更新と文書側コミット・公開経路を、コード反映手順と分離する。
- `.agents/skills/agent-handoff/`: 文書とコードの復元元を区別する記録・検証を整合させる。
- `.agents/skills/planning-parallel-issues/`: 固定した文書管理リポジトリと、既存のアーティファクト公開・復元手順の参照を整合させる。
- 上記規約の既存テストと、必要な回帰テスト。
- 第8節の既存未追跡文書の取り込み。

対象外:

- ResoLoop のコード・設定の変更、ResoLoop 側への Spec・Plan のコミット。
- インストール済み Superpowers スキルの直接変更。
- 自動コミット・自動 PR 作成ツール、定期掃除、全履歴の索引生成。
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
2. ResoLoop fork と upstream の案件: 両方の Spec・Plan の保存・コミット先が create-reso-world となり、コードの反映先と混同しない。
3. 文書の承認・更新・完了: コミットだけで承認済みにせず、承認された版を復元でき、過去版を再実行しない。
4. ローカルのみの保存、公開済みの保存、コミット失敗: 公開状態と復元可能性を区別し、失敗を完了扱いしない。
5. 既存文書取り込み: 対象一覧の件数・内容を照合し、既存ファイル、親 checkout、既存リンクを変更しない。参照切れを検出した場合は一覧と対応判断を残す。

完了条件は、規約と関連スキルの記述が一致し、既存文書の取り込みが確認され、上記検証が通り、文書とコードの保存・公開先を明示できることである。push・PR 作成が許可されていない場合はローカルコミットまでを報告し、公開作業は未実施と明記する。

## 11. 次のゲート

本 Spec を create-reso-world の専用ブランチへコミットして提示し、書かれた内容への明示承認を待つ。承認後は `writing-plans` で実装 Plan を作成し、Plan のレビューと実行方法の選択を経てから規約・スキルの変更へ進む。
