# 外部ツールリポジトリの共通管理基盤と Emission Editor の移行

- 状態: approved
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 文書作業先（DOC_ROOT）: `/workspaces/reso-world/.worktrees/emission-repo-management`
- 親 checkout（PARENT_ROOT）: `/workspaces/reso-world`
- 文書ブランチ: `docs/emission-repo-management`
- 調査基準: create-reso-world `28ef59b17a94191663597c927e66791425a3a864`。既存ツールのコードは Git 追跡外で、コードの承認済み HEAD は存在しない。
- 既存コード: `/workspaces/reso-world/worlds/tools`。移行元の候補であり、新リポジトリの CODE_ROOT ではない。
- 新リポジトリ: `usaturn/resonite-emission-editor`（名称は設計上の提案。未作成）
- 将来の CODE_ROOT: `/workspaces/reso-world/external/emission-editor`（未作成。存在・remote の検証前に既存 checkout として扱わない）
- Issue / PR: なし
- 内容承認: 利用者が改訂版 `b8c9b4253a5cd3431c9e2e6320649c2de14c15d8` に対して「Python のバージョンを最低 3.14 にして。それ以外は OK」と明示した。承認の参照版はこの SHA とし、今回の最低 Python 3.14 への変更を具体的に許可された修正として反映する。実装計画の作成へ進む許可であり、実装・repo 作成・公開の許可ではない。
- 改訂の許可範囲: 今後 `external/` に増やすツール専用リポジトリを共通の仕組みで扱い、Emission Editor もその上に載せる設計へ変更する。参考環境は読み取り調査に限り、コード転載・実行・変更の許可としない。
- 実行許可: 調査・設計・実装計画の作成まで。リポジトリ作成、コード抽出・変更、clone、公開、PR、マージ、実機作業は未許可。
- 公開: 文書のローカルコミットまで。公開未実施。

この文書は、既存のツール機能の Spec・Plan とは別テーマの管理基盤の設計である。初版のファイルを更新して共通基盤を先行させる。版ごとに別の設計書を作らず、初版と裁定は Git 履歴に残す。既存の元値保持・競合検査・書込境界、S4 以降の受け入れ条件を変更しない。機能開発の文書や失敗記録を置き換えない。

## 1. 目的と利用者が選択したこと

複数の独立したツールリポジトリを、create-reso-world の開発環境から同じ方法で開発・管理できるようにする。ツールを増やすたびに共通コードやスキルのリポジトリ名一覧、個別の取得スクリプトを増やす運用にしない。Emission Editor は最初に登録する公開ツールであり、専用の例外分岐は設けない。

順序は、共通の登録・対象判定・安全な取得・既存ワークフローへの接続を先に整備し、その後に Emission Editor のソースを選別して載せる。管理対象と編集・Issue・PR の帰属はコードを所有するリポジトリで決め、環境と文書は親に残す。

利用者は次を明示した。

1. create-reso-world 自体は公開リポジトリである。
2. 別リポジトリを作り、ローカルでは create-reso-world の配下へ置く方式を選択した。
3. ツールのリポジトリも公開する。
4. 今後同様のリポジトリを増やすため、個別対応ではなく汎用的な管理機構を作り、Emission Editor もそれを利用する。

GitHub の URL 上は `usaturn/create-reso-world` の子リポジトリではなく、同じ owner の別リポジトリになる。「配下」はローカルのディレクトリ配置を意味する。公開の選択は、未精査のファイル一式のアップロードや、この設計の承認・実行許可とは区別する。

## 2. 比較した方式

| 方式 | 利点 | 制約 | 判断 |
| --- | --- | --- | --- |
| 別リポジトリ + `external/emission-editor/` | 既存の resoloop-meshy と同様に環境とコードを分離。独立した履歴・Issue・PR を持てる | 親側の運用経路と、コードの抽出・公開範囲の整備が必要 | 利用者が選択 |
| 親のサブディレクトリを直接追跡 | 管理対象の Git リポジトリは増えない | 独立リポジトリを作るという依頼と異なり、環境とツールの履歴が混ざる | 不採用 |

`worlds/tools` 全体の Git 化、Git submodule、subtree、親への新リポジトリの内容の二重登録は行わない。Photo Offset や実ワールドのデータを移行対象へ混ぜない。

管理機構については次を比較した。利用者から汎用化の設計判断を委ねられたため、1 案目を採る。リポジトリの分離・公開という選択は開き直さない。

| 管理機構 | 利点 | 制約・判断 |
| --- | --- | --- |
| 親の登録台帳 + 共通 resolver / CLI + リポジトリ側の開発規則 | 新ツールは登録データと自身の規則を追加すれば同じ経路を使える。信頼境界を一元化できる | 採用。既存の複数の許可リストも利用側として接続する |
| リポジトリごとの script・AGENTS の分岐を追加 | 初回は小さい | 初版の方式。追加のたびに実装と安全確認が分散するため撤回 |
| `external/` を走査して自動登録・一括準備 | 登録が不要 | 未知の checkout の操作許可や、意図しない clone / setup に繋がるため不採用 |

参考環境の実装をそのまま移植・依存するのではなく、登録と帰属の分離という考え方を参考に独立して実装する。参考コードの権利・公開範囲と、今回の公開コードの権利を混同しない。

## 3. 管理と配置

提案する配置は次のとおり。

```text
create-reso-world/
├── .devcontainer/                 # 共通の開発環境（既存）
├── docs/superpowers/              # 正式な Spec・Plan
├── external-tools.toml            # 共通: 登録と運用ポリシー
├── tools/external_tools/          # 共通: loader・resolver・CLI
├── docs/external-tools-workflow.md
├── external/emission-editor/      # 独立 Git checkout。親の追跡対象外
│   ├── .worktrees/<topic>/        # コードを編集する作業先
│   ├── scripts/emission_editor/
│   ├── flux/emission-editor/
│   ├── content/emission-editor/
│   ├── tests/
│   ├── pyproject.toml / uv.lock
│   └── README.md / AGENTS.md / .gitignore
└── worlds/tools/                  # 現在の実機作業物・状態・凍結資料を保持
```

- 新リポジトリは fork ではなく、origin は `https://github.com/usaturn/resonite-emission-editor.git`。upstream は設けない。
- 親の `/external/` は既に無視されている。submodule や gitlink を追加しない。
- checkout は親の常設 `external/` に置く。親の文書 worktree や一時レビュー worktree の中へ置かない。
- 常設 checkout は detached `origin/main` に保ち、追跡ファイルの実装は新リポジトリ自身の `.worktrees/<topic>` で行う。ローカル main を作る運用は採用しない。
- ルート相対の既存構成をできるだけ保ち、移行だけを理由に Python パッケージ名や ProtoGraph の名前を変更しない。
- 共通 Dev Container、ResoLoop/Flux-SDK/managed DLL の導入は親の手順を利用する。DLL・SDK・アバター資産を新リポジトリへ同梱しない。
- 正式な Spec・Plan は引き続き create-reso-world の `docs/superpowers/` に置く。新リポジトリの README 等から参照する。二重管理しない。
- 開発状況は「開発中」とする。リポジトリへの移行を、ツールの機能完成や安全な実機利用の証明と表示しない。

リポジトリ名と配置名は初版から維持する。今回の再検討は共通の管理方式であり、同じ名前・公開範囲を繰り返し選び直さない。

## 4. 初期公開の対象と抽出方法

### 4.1 方針

元のディレクトリを移動せず、選別したソースを新しい作業領域へコピーする。初期の履歴はこの時点のソースから始める。Git 追跡外だった過去の全履歴を復元したとは報告しない。

抽出前にファイル単位で、移行元の相対パス、内容の SHA-256、移行先、用途、由来・権利、変換の有無を記録する。全件に採用・除外・保留の判断を付ける。公開用の一覧には内部の絶対パスや実セッション情報を含めない。保留は自動で採用しない。

| 候補 | 初期公開での扱い |
| --- | --- |
| `scripts/emission_editor/` の汎用処理 | 機能と依存を確認して採用。実機操作を伴わないテストで再現できること |
| `flux/emission-editor/` の現行ソース | 利用側が選択する実ソースを特定して採用。旧 `.pg` と `current/` の使い分けを失わない |
| `staged-s6/` のソース | 採用する場合も未反映候補と明示。現行ソースとして昇格しない |
| 汎用の宣言・fixture | 現セッションの ID・実アバター情報を持たないものを選別。未検証の生成や自動反映を入口にしない |
| Emission 固有のテスト | 移行先で実行できる S / F∩S を維持。実機の保存記録や親の tmp がないと動かないものは、そのまま移さない |
| README・AGENTS・依存定義 | 新リポジトリ用に整備し、環境・作業境界・未完成範囲を説明 |

### 4.2 調査で分かった依存と対処

- `ui.py::native_source_path` はルートの PG と `current/` を選択する。`current/` だけをコピーして全依存が揃ったとみなさない。`CURRENT_NATIVE_SOURCES` の変更はこの移行で行わない。
- `resoloop_io.py` の実機向けポート・state は 59125 に固定されている。新リポジトリに置いたことを理由に 3569 へ変更・自動接続しない。
- `runtime_59125.py` は絶対パスの履歴 baseline を参照し、汎用定義を `recovery_33046.py` から import している。履歴用ファイルを単純に除外すると依存が壊れる。
- 一部テストもローカルの `tmp/agents/` や `artifacts/` 内の実行用スクリプトを読む。全テストの単純コピーは独立性を保証しない。

汎用部品が履歴専用モジュールへ依存する箇所は、新しいコピー内で必要な部品だけを分離し、既存 S の意味を fake 入力で維持する。広範な API 再設計や新しい live runner は作らない。履歴専用の入口・固定セッションの実行記録は初期公開の操作手順から除外する。必要な汎用部品を安全に切り出せなければ、その採用項目を保留し、欠けた状態で「移行完了」としない。

新リポジトリのオフラインテストは、旧 world、親の tmp、実セッションの state、ネットワークを必要としないことを確認する。旧環境依存の安全テストについては、検証項目が同等の新しいテストへ移ったか、履歴専用で新しい実装の防御対象外なのかを記録する。S の守りを移行の都合で黙って落とさない。

### 4.3 公開しないもの

- `.resoloop/` の実 state、deploy checkpoint、接続・登録 capture、実機 session / ID の対応資料。
- `artifacts/`、`tmp/`、ログ、スクリーンショット、ワールドの保存物、過去の handoff と native raw 証拠。
- 実アバター・第三者のモデル・テクスチャ・購入素材・認証情報。
- `.venv/`、キャッシュ、`.brson` 等の再生成できる出力とコンパイラ作業物。
- Photo Offset、その他のワールド・ツール、既存の凍結履歴を含む一括コピー。

`.gitignore` だけに依存せず、初回にコミットするファイルを明示した一覧と実際の index/tree を照合する。除外対象を一度コミットして後から削除する手順は使わない。

## 5. 共通の登録・対象判定・操作の仕組み

### 5.1 親の登録台帳

親リポジトリで `external-tools.toml` を追跡する。これは管理するツールの識別・配置・既定 base・CI の扱いを定義するデータであり、コマンドやスクリプトの実行元にはしない。例は実装する形式の提案であり、まだファイルは作成していない。

```toml
schema_version = 1

[tools.emission-editor]
repository = "usaturn/resonite-emission-editor"
path = "external/emission-editor"
base_branch = "main"
ci = "disabled"
```

- キー、owner/repo、正規化したパスを一意にする。大小文字を同一視した repository の重複、親子で重なる checkout、予約済みの既存リポジトリとの衝突を拒否する。
- path は親 checkout の `external/` 配下だけを許す。絶対パス、`..`、親のルート、Git 管理領域、worktree の内部や symlink を介した範囲外を許さない。最終要素だけでなく祖先も確認する。
- parent / DOC_ROOT の GitHub identity は bootstrap の固定条件として残す。台帳で親や文書保存先を別リポジトリへ差し替えられるようにしない。
- 実操作は採用済みの親 checkout のコミット済み台帳を使い、使用した commit を記録する。親の機能 branch や外部 repo にある候補台帳は読取検証できても、未採用の項目を操作許可にしない。外部 repo の PR が自分を登録・昇格することはできない。
- 初期の登録は Emission Editor。将来の通常ツールは台帳の項目と、そのリポジトリ自身の AGENTS / README を追加して同じ仕組みを利用する。個別の Python 分岐、shell script、共通スキル内の名前一覧を追加しない。
- 非公開 repo の名前も台帳へ書けば公開情報になる。資格情報や認証付き URL は保存せず、将来の登録時にも公開範囲を確認する。

### 5.2 共通 resolver と対象の同一性

`tools/external_tools/` に共有 loader / resolver を置き、既存の `scripts/superpowers_context.py` からも同じ判定を使う。判定の入力は対象 owner/repo、操作の種類、必要なら明示 CODE_ROOT である。出力は選択された checkout / common-dir、base remote と branch、文書・レビューの保存先、必要な規則、台帳 commit と、停止理由を含む。

- 登録済みツールは台帳の常設 checkout と期待 origin を照合する。ディレクトリ名や同じ origin だけで、別の場所の clone を同じ管理対象としない。
- 明示 CODE_ROOT がある場合も整合性を照合する。操作が linked worktree を許す場合は、検証済み常設 checkout と Git common-dir が同一のものだけを受け入れる。main checkout を要する読み取り経路との区別を維持する。
- Git の検査は周囲の `GIT_*` によって別の checkout を読まないよう隔離する。ネットワーク操作の認証は検査用環境と区別し、資格情報をログへ出さない。
- 論理的な origin と、pushurl / URL 書換えを含む実際の送り先を混同しない。取得・push の前にはその操作に使う宛先を照合し、別の repo / host / 未確認の mirror へ送らない。読取判定で認識できることだけを送信許可としない。
- 未登録・checkout 不在・remote 不一致・候補が複数のときに、親 checkout や近くの repo へ fallback しない。対象と理由を示して停止する。resolve 自体は clone / fetch / checkout / 修復を行わない。
- 既存の ResoLoop fork は origin / upstream / 上流 PR base 等の特殊条件を維持する。既存 resoloop-meshy を含む既知の経路を、この変更で暗黙に再登録・移動しない。
- 未登録でも明示 CODE_ROOT を与える既存の PR レビューと、その承認済み PR review-fix 実装は維持する。ただし、その例外経路から新規の一般実装を許可しない。

### 5.3 共通 CLI：調べる操作と作る操作を分離

共通の入口は `uv run --project <PARENT_ROOT> --locked python -m tools.external_tools` とする。CLI に個別 repo 名の分岐を作らない。

| 操作 | 副作用と結果 |
| --- | --- |
| `list` / `show <key>` | 台帳の情報を読む。ネットワーク・外部 repo の作成・変更なし |
| `check <key>` | 実 checkout の identity / 状態をローカルで確認。変更なし。missing / mismatch は ready としない |
| `clone <key>` | 明示した 1 件のみ取得。呼出し自体の許可が必要。既存 checkout は検証だけで、fetch / reset / checkout / setup はしない |

- 引数なしの全件 clone、`external/` の走査による自動登録、Dev Container の起動時の全件準備は採用しない。
- 取得には、検証済み親の同じ common-dir に紐付く対象ごとの排他を使い、別の親 worktree やセッションからの同時取得を防ぐ。ロックの有無を見ただけで stale とみなして消さない。
- 作成中の領域は helper 自身が作った一意の staging に限定する。最終位置が依然未使用であることと checkout の同一性を確認してから配置し、既存物を置換しない。失敗時は未完了と所有範囲を記録し、未知の残骸を自動削除・再利用しない。
- 新しい checkout は初期化・取得・detached checkout の手順で用意し、既存 branch の削除やローカル main の作成を前提としない。
- 台帳には shell / argv の setup、verify、post-clone hook を保存しない。clone に各 repo のセットアップを混ぜない。Git checkout 時の hook も実行しないようにし、Git の認証 helper 等の信頼境界を明示する。この CLI を任意プログラムの sandbox と説明しない。
- JSON の結果と終了状態を分け、missing / skipped / failed を成功・使用可能と報告しない。check の成功範囲はローカル checkout の同一性・状態だけであり、公開許可・ライセンス・実機利用の準備完了にはしない。再実行は既存物の確認であって、自動 resume や修復ではない。

### 5.4 既存ワークフローを共通の判定につなぐ

resolver だけを足して他の名前一覧を残すと、新ツールは後段で拒否される。最初の実装で、以下を同じ管理対象の判定へ接続する。

- 承認済み Plan の SDD 実装：登録先の worktree で編集し、コードはその repo にコミットする。DOC_ROOT / PARENT_ROOT と CODE_ROOT を区別する。
- `issue-to-pr`：入力解決 helper の固定 allowlist と手順中の個別表を共通判定へ置き換える。登録済みの通常ツールで Issue -> 実装 -> 検証 -> PR を進められるようにする。base の明示・固定・再確認、担当予約と既存 PR での停止、Gitleaks は維持する。
- `pr-review` / `review-fix-planning`：共通 resolver の target root を使い、レビュー記録は既存の `PARENT_ROOT/reviews/<owner>/<repo>/...` に保存する。外部 repo にレビュー記録や正式な Spec・Plan を二重配置しない。
- `repo-cleanup-after-merge`：登録先の common-dir / branch / worktree / PR のマージを確認して対象だけを整理する。親への追従と fork sync は別の処理であり、新ツールから実行しない。
- 初期の通常ツール profile は手動マージとする。`--merge` 等の自動マージ入口は、未対応なら副作用の前に明確に拒否する。既存 parent / fork の finalize / merge 経路は弱めず、未知 repo が resolver を通ったことだけでマージ可能にしない。

登録は「この機構が扱える対象」を定義するだけである。repo 作成・clone・実装・push・PR・マージ・release・実機操作の実行許可は、利用者の指示と各ワークフローで別に確認する。台帳に `release=true` や任意権限を記述して外部操作を一括許可する方式にはしない。

CI は公開・非公開から推測せず、台帳の profile と実際の repo 設定を照合する。今回作成する repo は規約どおり Actions を無効化する。既存の CI 必須対象の検査を免除しない。

### 5.5 共通規約と repo 固有の規則

`AGENTS.md` は登録済みツールの共通経路を定義し、台帳を参照する。新ツールごとの行や詳細な検証コマンド表を増やさない。`docs/external-tools-workflow.md` に、登録・取得・開発・レビュー・片付けと新ツールを追加する手順をまとめる。

テスト・lint・build の選び方、必要な依存、利用方法は各 repo の AGENTS / README に置く。同一性を検証してから読み、親の安全規則・文書保存先・許可範囲を上書きする権限にはしない。言語やツールチェーンは固定せず、親の機構が登録されたプログラムを勝手に実行しない形で拡張性を保つ。

Emission Editor 用の `scripts/emission-editor.sh` や共通機構の代わりとなる個別取得手順は作らない。Emission の固有事項は、既存実機データとの移行境界と、ツール自身の利用・検証手順に限定する。README の環境とツールの関係、親の公開状態についての古い記述を対象を限定して訂正し、他 repo の公開状態や設定は変更しない。

## 6. GitHub 作成と初回 push の安全な順序

この節は将来の実行計画の制約であり、現時点の実行指示ではない。各外部操作は、承認済み Plan と具体的な実行許可を得てから行う。

1. owner/repo 名の利用可否と権限を確認する。既存の同名リポジトリを見つけたら、勝手に再利用・変更しない。
2. ソースの権利・由来を確認し、利用者がライセンスを選択する。親の GitHub メタデータで licenseInfo は null だったので、親と同じライセンスや MIT を自動で付けない。第三者のコードが含まれる場合はその条件も確認する。未確定ならソース公開は停止する。
3. 公開リポジトリを、GitHub が生成する名前・説明だけの README を付けて作成する。既存 world を source にせず、作成時の `--push` は使用しない。README/説明も事前確認する。
4. 作成直後に新リポジトリの GitHub Actions を無効化し、取得した設定が `enabled=false` であることを確認する。失敗・不明ならソースを push しない。既存の親リポジトリの Actions は変更しない。CI workflow は作らない。
5. 実際の owner/repo、URL、PUBLIC、台帳の base branch の基準 commit を観測する。今回の Emission は main とし、default branch が一致しなければ停止する。無断で branch 設定を変えない。将来のツールの base は共通コードの main 固定ではなく、台帳とその作業の明示条件で決める。
6. 親の共通基盤と Emission の台帳登録が採用されていることを確認する。共通 CLI で常設 checkout を取得し、初期移行用 worktree を作り、main の README commit からソース・テスト・ライセンス・通常文書をコミットする。server 作成の README だけで「コード移行済み」としない。
7. 親の `scripts/scan-before-push.sh -C <code-worktree>` を使い、実際の `origin/main` から初回ソース commit までを検査する。検査済みの SHA だけを、明示した新リポジトリの作業 branch へ push する。検査後に HEAD が変われば検証・検査をやり直す。
8. 初期ソースの PR とローカル検証結果を確認する。PR 作成とマージは別許可とし、未完了・未検証の項目を明記する。

既存の scan-before-push は実在する remote base が必要である。上記の README bootstrap により `origin/main` を先に作るため、空 remote のために秘密情報検査を迂回したり、ローカルの未検査ファイルを先に push したりしない。GitHub 上に生成する README は審査済みの公開メタデータのみであり、ローカル由来のソースを含まない。

repo 作成・設定変更の結果が通信断で不明になった場合は、同じ作成操作を繰り返さず、読み取りで対象 ID・URL・設定を確認する。新 repo の削除、公開済み履歴の書き換え、force push を切り戻し手段にしない。誤公開が疑われたら操作全体を止めて利用者へ報告する。

## 7. 実機開発との切り分け・切り戻し

- 初期の公開コード整備はオフラインで行い、Resonite の前面化は要求しない。接続・discover・撮影も行わない。
- 旧 `/workspaces/reso-world/worlds/tools` と既存証拠は変更・削除しない。sealed source/hash/manifest/state、G0、SourceMap を移行のために書き換えない。symlink や自動同期で旧実行先を新コードへ差し替えない。
- 新リポジトリが独立開発の編集対象になった後も、旧コピーは現在の実機試験専用の凍結領域として残す。両方を手で並行編集する運用にはしない。旧試験を再開する前には、新側で変更した機能を旧側の試験済みとして扱わない。
- 新リポジトリでの実機作業は、現在の実機試験の安全な停止位置と所有 fixture の状態を確認し、新しい実行対象・source・state・証拠・current session の対応を別途レビューした後だけ再開する。その具体的な継続計画と利用者の前面化・実行許可を別ゲートにする。
- この移行の完了条件に、S4 全体の成功、S5/S6 以降、実 UI、二人操作、save/reload の成功を混ぜない。従来の未完了・失敗を保持する。
- オフライン抽出やテストに失敗したら新側で停止し、移行元と旧資料を残す。新側を実機の source として採用しないことが切り戻しであり、旧 state の再生や world の修復は行わない。
- 親の共通基盤・台帳登録の採用前、ライセンス未選択、公開候補未精査、実機切替未レビューの各段階は、個別に blocked と記録する。公開リポジトリが存在するだけで後段へ進めない。

## 8. 受け入れ基準・検証方針

### 動作環境と入力

共通基盤と新しい Emission Editor リポジトリの Python は最低 3.14（`requires-python = ">=3.14"`）とする。既存の Dev Container と uv、親が導入する ResoLoop / Flux-SDK を使う。既存の凍結済み world の依存定義・実機試験資料・過去の記録は、このバージョン指定のために変更しない。インストール済み版は実行時に記録し、この移行で旧実機試験の依存や DLL を更新しない。ソース・通常文書には日本語や複数行の文字列があり、登録・UI の fake 入力にも非 ASCII と複数行を含める。

1. 新ソースのオフライン検査は、旧 world / tmp / state を参照しない隔離した一時領域で実行できる。world 呼出しは 0。新 package の import / 構文 / 参照、必要な PG の隔離 check/build を実行して確認する。
2. 移行対象一覧と新 Git tree が対応し、対象外の実機データ・第三者資産・秘密情報がない。権利の不明なファイルは保留し、ライセンス確定前にソースを push しない。
3. 元コードと凍結証拠は不変である。既存の保全検査を元の cwd で行い、旧試験の pin を変更しない。別ツールの動的 state は凍結・検査対象へ広げない。
4. 共通 resolver / 取得 CLI は正しい登録先の独立 checkout と許可された linked worktree を受け入れ、別 repo・別 common-dir・親のサブディレクトリ・台帳候補を誤った操作対象として使わない。既存ファイルを上書きせず、親 worktree から呼んでも常設の同じ位置を使う。
5. Emission とは異なる名前・owner/repo の通常ツールを一時 fixture の台帳に追加しても、共通コードやスキルのリポジトリ名を変更せず、対象解決から Issue/PR・レビュー・cleanup の各利用側へ同じ identity が届く。実在 repo の追加作成やネットワークをテストに使わない。
6. 新リポジトリの PUBLIC、Actions=false、default branch / origin の同一性を実設定の読み取りで確認できる。fake/API 記録だけで実際の GitHub 設定確認に代えない。
7. 移行後のコード・文書・テストの所在と未実施の実機条件が明確で、GitHub 作成、ソース初回公開、PR、マージ、実機切替の成否を別々に記録できる。

### 防御範囲とテストの採用

- S として、誤った checkout / common-dir・周囲の GIT 環境による対象すり替え・パスや祖先 symlink の境界脱出・既存データ上書き・同時取得の競合を、それぞれを防ぐ共通モジュールの代表例で確認する。拒否に対応する正例も残す。同じ守りを多層で重複テストしない。
- 採用済み台帳と未採用の候補の違い、登録済みの通常実装と未登録の明示 CODE_ROOT review-fix の違い、未対応自動マージの副作用前停止を S として確認する。既存 fork の origin / upstream / base の区別を保持する。
- 通常ツールの追加が個別コードなしで利用側まで届くことは、代表の fake の一連の経路で確認する。台帳に書いた現在のリポジトリ名やドキュメント表を写して比べるテストにはしない。
- 再利用する既存 S は、対象取り違え、元値・復元記録の保持、競合時の拒否、失敗後の書込停止、コンパイラ出力の隔離等の意味を維持する。既存 F∩S は消さない。
- 文書本文・構成一覧・ツール名・今の設定値を写す F、import や構文エラーだけの L を新たな永続テストにしない。文書の確認は差分・参照検査で代える。
- 公開ファイル選別は初回の人による精査と Git tree / Gitleaks 検査を基準にする。汎用の自動エクスポート基盤は今回作らない。
- GitHub の操作手順は実行時の readonly 照合で確認し、本物の repo 作成・push・実機操作を自動テストに使わない。必要な実装テストはローカル一時 Git / fake CLI を使う。
- この防御は、資格情報を意図的に全ファイルへ複写する攻撃や GitHub アカウントの侵害まで保証しない。Gitleaks は権利・個人情報・world 完全保存の確認の代わりにならない。

## 9. 対象外と未決事項

### 対象外

ツールの新機能、UI 変更、Preview/Commit の完成、既存実機試験の合格化、実アバターの登録・色変更、state の転送、他の既存ツールや fork の移行、Dev Container の独立配布、CI の追加、未登録 repo の一般実装の許可、任意の setup / release / デプロイの自動実行、通常ツールの自動マージ機能の追加、公開済み履歴の書き換え、既存資料の削除。

### 利用者の確認が必要な事項

- 共通基盤を先行させる設計は、最低 Python 3.14 への変更と合わせて承認済み。リポジトリの分離・公開と初版からの名称・配置は維持し、再選択を求めない。
- ソースの権利確認後のライセンス選択。実装計画内の公開前の停止ゲートとして扱い、選択を推測しない。
- 後続 Plan の内容・実行範囲と、repo 作成 / push / PR / マージ / 実機切替の各許可。

### 実装担当に委ねる事項

採用候補の詳細な依存一覧、汎用部品の分離が必要な最小箇所、共通モジュール内の分割、排他と staging の具体的な実装、同じ守りを代表する S テストの具体例。台帳 schema の意味・受け入れ条件・操作許可・公開境界・実機への切替条件を変更する判断は委ねない。

## 10. 調査と設計確認の記録

- `gh repo view usaturn/create-reso-world --json nameWithOwner,visibility,url,licenseInfo,defaultBranchRef` の読み取りで PUBLIC / main / licenseInfo=null を確認。リポジトリ設定の書き込みはしていない。
- `docs/resoloop-meshy-workflow.md`、既存 helper、root `.gitignore`、`scripts/scan-before-push.sh`、`scripts/superpowers_context.py` と Emission のソース/テストの依存を読み取りで調査した。
- Context7 CLI で GitHub CLI の `repo create` / `repo view` / `api` と、Actions permissions API を確認した。リポジトリ作成や Actions の設定変更はしていない。
- 読み取り調査の subagent を 2 件 dispatch したが、いずれもツール応答が無出力で、予定のレポートもなかった。結果・独立確認の成功・子の終了状態は認定しない。controller が限定した読み取り調査を代行した。設計確認で子を使えない場合は、その制約を明記して自己点検する。
- 初版の読み取り専用 builder check は `sp-review` へ委譲し、応答は `nothing important left` だった。これは初版の計画作成に必要な質問の確認であり、この汎用化改訂のレビューや承認ではない。先の無出力の調査の成功・終了状態を認定する根拠にも使わない。
- 汎用化の追加調査では、共通 resolver のほかに Issue 解決 helper・手順、CI / merge の gate、cleanup 等に独立した固定対象があることを確認した。resolver だけの追加や個別 script の増設では足りないため、5.4 の利用側まで接続する設計に変更した。
- 利用者が指定した別環境を、固定した版のファイルを読み取って比較した。非公開の参照資料なので、ソース・登録内容・具体的な内部運用や未再現の問題点を公開文書へ転載しない。参照コードは実行・import・変更せず、今回の実装の依存にも加えない。調査の詳細はローカル資料に残す。
- 参照から採るのは登録台帳とリポジトリの帰属を明示する考え方である。一括準備・任意 setup 実行、origin だけを頼りにする操作先判定、実行許可と登録の混同は、この環境の要件に合わせて独立した設計で避ける。参照環境に実害や根本的な欠陥が再現されたと主張するものではない。
- 汎用化改訂後の読み取り専用 builder check も `sp-review` に依頼し、応答は `nothing important left`（計画作成前に解決が必要な重要な質問なし）だった。これは利用者の内容承認や、共通基盤の実装・実機検証の完了ではない。
- 利用者の明示確認に従い、最低 Python 3.14 に修正して設計の承認を記録した。親の `pyproject.toml` は既に `requires-python = ">=3.14"` であり、この設計修正でコード・依存や既存 world の定義を変更していない。
- この設計文書だけの変更には永続テストを追加しない（F/L）。コミット前に文書差分、参照先、`git diff --check` を確認する。承認済み設計に基づいて実装計画を作成し、Plan の確認と実行許可は別に求める。

参照:

- [GitHub CLI: gh repo create](https://cli.github.com/manual/gh_repo_create)
- [GitHub CLI: gh api](https://cli.github.com/manual/gh_api)
- [GitHub REST: Actions permissions](https://docs.github.com/en/rest/actions/permissions)
