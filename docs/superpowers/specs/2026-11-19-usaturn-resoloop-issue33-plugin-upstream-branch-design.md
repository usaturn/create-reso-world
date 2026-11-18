# usaturn/resoloop#33 プラグイン機構の上流提出用ブランチ 設計

## 管理・実行許可

- 状態: `draft`（コミットしただけで `approved` にしない。内容の承認は記録していない）
- 文書管理リポジトリ: usaturn/create-reso-world。対象 Issue: https://github.com/usaturn/resoloop/issues/33 （実装対象 `usaturn/resoloop`）。後続は create-reso-world#105
- 利用者の指示（2026-11-19）: 「https://github.com/usaturn/resoloop/issues/33 に着手してください。今回の方針は、既存の `feat/plugin-v2` を保持したまま、上流提出用の別ブランチを作り、`orange3134/resoloop` の最新 `main` を基点に rebase して、上流へ PR できる状態に整えることです。この指示を、Issue 本文の『rebase を行わない』『feat/plugin-v2 に merge commit で取り込む』という方針を変更する利用者決定として扱ってください。通常の設計・実装判断は推奨案で決め、調査・必要な修正・検証・fork への push・結果の記録まで自律的に進めてください。」
- 実行許可の範囲: Issue #33 の本文・メタデータの更新、この Spec・Plan の作成とコミット、`usaturn/resoloop` の上流提出用ブランチの作成・rebase・修正、Gitleaks の検査を通した SHA の fork への push、Windows CI のための検証用ブランチ・PR の作成（usaturn/resoloop 内）、Issue #33 への記録と close、`usaturn/create-reso-world:main` 宛ての文書専用 PR の作成
- 実行しないこと: `feat/plugin-v2`・fork `main` の変更、force push、検証用 PR のマージ、上流 `orange3134/resoloop` への Issue・PR・コメント、版番号の変更、NuGet への公開、Resonite・Blender を使う実機検証
- 入力（2026-11-18T19:04Z に `git fetch` で取得）:
  - `SRC_SHA`: `usaturn/resoloop:feat/plugin-v2` @ `95d115aecb42e38a25d8cddeadd8d3715f4e416b`
  - `UPSTREAM_SHA`: `orange3134/resoloop:main` @ `32309ca3deb4560e6a31a8985dba87ba5485c946`
  - fork `main`: `ff77b91d1f17c7dba861416d82f1a6c8929f2805`（上流に無いコミットは `ff77b91` の merge とその親の系列）。分岐点: `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`
- 文書 base: `usaturn/create-reso-world` `refs/heads/main` @ `e347ac69238ebc563b1e4d31331037d7899cb01f`
- issue-to-pr スキルとの差: このスキルは base へのコード PR を成果にするが、今回の成果は利用者の指示どおり「公開した提出用ブランチ」であり、コード PR は Windows CI の検証用だけを作る（マージしない）。Issue 本文の更新は、利用者が最初の手順として明示したため、案の提示後の承認待ちを置かずに `publish_issue.py` の draft → publish で行った

## 1. 目的と現状

プラグイン機構（外部コマンド・スキル・UIX レシピ・doctor と `plugin install/list/remove`）は fork の `feat/plugin-v2` に統合済みで、文書と最小例（usaturn/resoloop#32）も入っている。`SRC_SHA` は `UPSTREAM_SHA` に対して 41 コミット先行（うち merge 6、通常のコミット 35）・29 コミット遅れである。`git merge-tree --write-tree SRC_SHA UPSTREAM_SHA` は競合なしで tree `43d17f10e8adac2201a8879f366995c26357bf1c` を返す。

上流へ PR する前に、(1) 上流の最新を基点にした履歴、(2) fork・作業ブランチ・内部 Issue を前提とする記述の整理、(3) 統合した状態の Linux・Windows の検証が要る。

## 2. 設計

1. **ブランチ:** `SRC_SHA` から `feat/plugin-system` を作り、`git rebase --onto UPSTREAM_SHA` で 35 コミットを直線の履歴に載せ替える（merge commit は作り直さない）。
2. **merge commit の内容の保全:** rebase 直後の tree が、`SRC_SHA` と `UPSTREAM_SHA` の 3-way merge の tree（`43d17f10…`）と一致することを確かめる。`SRC_SHA` の tree は過去の 6 つの merge commit の解消結果をすべて含むので、この一致は「merge commit にだけある修正・競合解消」と「上流側の 29 コミットの変更」の両方が落ちていないことを示す。
3. **コミットメッセージ:** 件名末尾の `(create-reso-world#N)`・`(#N)` を除く。`(#99)` などは上流のリポジトリでは無関係な Issue・PR へのリンクになり、上流への PR に載ると相手側に誤った参照が残るためである。本文・`Co-Authored-By`・コミットの単位と順序は変えない。
4. **fork 向け記述の整理（追加コミット）:** Issue の共通検索範囲（`src tests examples skills README.md README_JA.md README-DETAILS.md docs/PLUGINS.md docs/PLUGINS.ja.md`）の `create-reso-world|usaturn|feat/plugin-v2` の一致 16 行を直す。
   - README 3 種のリンクは `https://github.com/orange3134/resoloop/blob/main/docs/PLUGINS(.ja).md` と `https://github.com/orange3134/resoloop/tree/main/examples/plugins/hello`（決定 C5 の絶対 URL。英語 README は英語ガイド、日本語 README・README-DETAILS は日本語ガイド）。
   - 「`feat/plugin-v2` の機能」「NuGet の 0.2.0 には含まれない」は、公開版番号に依存しない説明（プラグインに対応したビルドかどうかは `resoloop help` の `plugin install` の行で見分ける。無ければソースからビルドする）に置き換える。
   - ガイドの検証注記は「ソースからビルドした ResoLoop 0.2.0（Linux）で確認」という中立な表現にする。出力例そのものは変えない（再実行していない出力に差し替えない）。
   - コードコメント 2 行の内部 Issue 番号は、設計上の理由だけを残す。
5. **統合の修正:** rebase 後に build・test が失敗した場合だけ、上流の変更とプラグインの挙動を両立させる最小の修正を足す。
6. **Windows の検証:** 上流の `ci.yml` は `pull_request` で動き、PR の merge ref（base と head の merge）を検証する。fork 内に `UPSTREAM_SHA` を指す検証用の base ブランチ `ci/issue-33-upstream-base` を作り、最終候補を head にした PR を出す。base が head の祖先なので、merge ref の tree は最終候補の tree と一致する。run が checkout した merge commit の tree を GitHub API で取得し、最終候補の tree と照合する。検証用 PR はマージせず close する。
7. **公開:** `scripts/scan-before-push.sh --base upstream/main` で検査した SHA を `refs/heads/feat/plugin-system` へ push する（新規ブランチなので force は不要）。CI の後に修正が要るときは、上にコミットを足して通常の push で更新する（公開後は履歴を書き換えない）。

## 3. 決定記録

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
|---|---|---|---|---|---|
| D1 | ブランチ名 | `feat/plugin-system` | `feat/issue-33-…`、`feat/plugin-v2-upstream` | 上流への PR の head になるので、fork の Issue 番号や作業ブランチ名を含めない | 「通常の設計・実装判断は推奨案で決め」 |
| D2 | 履歴の形 | 35 コミットを直線にし、単位と順序を保つ | 1 コミットへの squash、機能別の再分割 | PR の分割・組み直しは #105 の範囲（Issue の対象外）。単位を保てば元の PR と対応を追える | 同上 |
| D3 | コミットメッセージ | 件名末尾の内部 Issue 参照だけを除く | そのまま残す | `(#N)` が上流の無関係な Issue に結び付く。新しいブランチの初回 push 前なので公開済みの履歴は書き換えない | 「新しい提出用ブランチの履歴は、初回 push 前に整えてください」 |
| D4 | fork 向け記述の修正の置き方 | rebase した履歴の上に追加コミット | 元のコミットへ fixup | rebase 直後の tree を merge の tree と照合してから修正を足すと、保全の確認と文書修正を分けて検証できる | 推奨案 |
| D5 | Windows CI | `UPSTREAM_SHA` を指す検証用 base ブランチへの fork 内 PR | `feat/plugin-v2`・fork `main` を base にする、検証用ワークフローを足す | 既存ブランチを base にすると merge ref の tree が最終候補と異なる。ワークフローを足すと検証専用の変更が要る | 「実際に検証した SHA・tree を確認」。tree が一致しなければ成功として扱わない |
| D6 | テスト | 追加しない（統合で S に当たる不具合が見つかった場合だけ足す） | リンク・文言の検査テスト | テストの採用基準の F に当たる。検索と tree の照合で代える | 利用者の指示 |
| D7 | 版番号に触れる説明 | 「NuGet の 0.2.0 には含まれない」を版番号に依存しない説明にする | 残す | 上流での公開版は未決定。取り込み後に誤りになる記述を残さない | 利用者の指示（未決定のリリース番号は書かない） |

## 4. 受け入れ条件

- **動作環境:** Linux の Dev Container（上流の `global.json` に従う .NET）と、fork の GitHub Actions の `windows`。`RESOLOOP_RUN_INTEGRATION` は有効にしない。Resonite・Blender を使う実機検証は対象外で、未実施と記録する。
- **実入力:** `SRC_SHA` と `UPSTREAM_SHA`（上記）。README 3 種、英日のガイド、コードコメント 2 行。
- **防御範囲:** 変更するのは `feat/plugin-system`、検証用の `ci/issue-33-upstream-base` と検証用 PR、create-reso-world の文書用ブランチだけ。`feat/plugin-v2`・fork `main`・上流は変更しない（着手時と完了時の SHA が同じ）。fork `main` だけにあるコミットを含めない。
- **完了条件:**
  1. `UPSTREAM_SHA` が最終候補の祖先で、`最終候補..UPSTREAM_SHA` が 0 コミット。
  2. rebase 直後の tree が `43d17f10e8adac2201a8879f366995c26357bf1c` と一致する。
  3. 共通検索範囲の一致が 0 件（残すものは理由を記録）。README の絶対 URL のパスが最終候補の tree に存在する。
  4. `UPSTREAM_SHA..最終候補` の差分が、プラグイン機構・その文書・統合に必要な修正だけである。fork `main` 固有のコミットとの共通部分が 0 件。
  5. Linux で `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build` が成功する。
  6. Windows CI が成功し、検証された merge commit の tree が最終候補の tree と一致する。
  7. fork の `feat/plugin-system` の先端が最終候補の SHA と一致し、Issue #33 に結果を記録して close している。
