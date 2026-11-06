# Emission Editor の独立リポジトリ管理への移行

- 状態: draft
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 文書作業先（DOC_ROOT）: `/workspaces/reso-world/.worktrees/emission-repo-management`
- 親 checkout（PARENT_ROOT）: `/workspaces/reso-world`
- 文書ブランチ: `docs/emission-repo-management`
- 調査基準: create-reso-world `28ef59b17a94191663597c927e66791425a3a864`。既存ツールのコードは Git 追跡外で、コードの承認済み HEAD は存在しない。
- 既存コード: `/workspaces/reso-world/worlds/tools`。移行元の候補であり、新リポジトリの CODE_ROOT ではない。
- 新リポジトリ: `usaturn/resonite-emission-editor`（名称は設計上の提案。未作成）
- 将来の CODE_ROOT: `/workspaces/reso-world/external/emission-editor`（未作成。存在・remote の検証前に既存 checkout として扱わない）
- Issue / PR: なし
- 内容承認: 未受領。方式と公開範囲の選択だけを受領。
- 実行許可: 調査・設計・実装計画の作成まで。リポジトリ作成、コード抽出・変更、clone、公開、PR、マージ、実機作業は未許可。
- 公開: 文書のローカルコミットまで。公開未実施。

この文書は、既存のツール機能の Spec・Plan とは別テーマの管理基盤の設計である。既存の元値保持・競合検査・書込境界、S4 以降の受け入れ条件を変更しない。機能開発の文書や失敗記録を置き換えない。

## 1. 目的と利用者が選択したこと

Emission Editor のソース・テスト・通常の開発手順を独立した公開 GitHub リポジトリで管理し、開発環境は create-reso-world を利用する。変更履歴、Issue、PR をツール単位で追えるようにする。

利用者は次を明示した。

1. create-reso-world 自体は公開リポジトリである。
2. 別リポジトリを作り、ローカルでは create-reso-world の配下へ置く方式を選択した。
3. ツールのリポジトリも公開する。

GitHub の URL 上は `usaturn/create-reso-world` の子リポジトリではなく、同じ owner の別リポジトリになる。「配下」はローカルのディレクトリ配置を意味する。公開の選択は、未精査のファイル一式のアップロードや、この設計の承認・実行許可とは区別する。

## 2. 比較した方式

| 方式 | 利点 | 制約 | 判断 |
| --- | --- | --- | --- |
| 別リポジトリ + `external/emission-editor/` | 既存の resoloop-meshy と同様に環境とコードを分離。独立した履歴・Issue・PR を持てる | 親側の運用経路と、コードの抽出・公開範囲の整備が必要 | 利用者が選択 |
| 親のサブディレクトリを直接追跡 | 管理対象の Git リポジトリは増えない | 独立リポジトリを作るという依頼と異なり、環境とツールの履歴が混ざる | 不採用 |

`worlds/tools` 全体の Git 化、Git submodule、subtree、親への新リポジトリの内容の二重登録は行わない。Photo Offset や実ワールドのデータを移行対象へ混ぜない。

## 3. 管理と配置

提案する配置は次のとおり。

```text
create-reso-world/
├── .devcontainer/                 # 共通の開発環境（既存）
├── docs/superpowers/              # 正式な Spec・Plan
├── scripts/emission-editor.sh     # 新規: 明示実行する取得・状態確認
├── docs/emission-editor-workflow.md
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

リポジトリ名と配置名はこの設計で提案している値であり、これまでの選択で名称まで承認されたとは記録しない。設計確認時に合わせて確認する。

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

## 5. 親リポジトリ側に追加する運用経路

現在の `AGENTS.md` では、一般的な外部リポジトリの新規実装は非対応である。文書があるだけでは外部実装を始められないため、今回の特定のリポジトリに限った運用経路を先に整備・採用する。

- `AGENTS.md` に新リポジトリの owner/repo、常設 checkout、origin 検証、worktree、コード側と文書側の役割を追加する。他の外部リポジトリへの実装許可は広げない。
- `docs/emission-editor-workflow.md` に、初期取得、オフライン開発、review / push / PR、実機作業への別ゲートを定義する。
- `scripts/emission-editor.sh` は取得と状態表示だけに限定する。repo 作成、push、実機反映、同期・上書き・修復・自動 cleanup は行わない。
- 既存の場所が空でない、自分自身の checkout でない、origin が違う、symlink の解決先が管理境界から外れる等は、上書きせず停止する。通常の既存 checkout では変更を加えず検証だけ行う。親 worktree から呼んでも常設の親 checkout の下を使う。
- PR レビューは既存の明示 CODE_ROOT の経路を使う。実際の不具合が確認されない限り、汎用の review resolver を作り替えない。
- 初期対象は、承認済み計画からの通常の開発と、既存の明示 CODE_ROOT を使う PR レビュー・修正である。Issue 自動選択などのスキル拡張は含めない。
- 新リポジトリの `AGENTS.md` にも親の共通安全規則・文書保存先・uv 利用・実機操作の境界を明記する。独立した checkout の実装が無条件の実機操作許可になるとは扱わない。
- README に環境とツールの関係を追加する。親の公開状態についての古い記述は対象を限定して訂正するが、他リポジトリの公開状態や CI の設定は変更しない。

## 6. GitHub 作成と初回 push の安全な順序

この節は将来の実行計画の制約であり、現時点の実行指示ではない。各外部操作は、承認済み Plan と具体的な実行許可を得てから行う。

1. owner/repo 名の利用可否と権限を確認する。既存の同名リポジトリを見つけたら、勝手に再利用・変更しない。
2. ソースの権利・由来を確認し、利用者がライセンスを選択する。親の GitHub メタデータで licenseInfo は null だったので、親と同じライセンスや MIT を自動で付けない。第三者のコードが含まれる場合はその条件も確認する。未確定ならソース公開は停止する。
3. 公開リポジトリを、GitHub が生成する名前・説明だけの README を付けて作成する。既存 world を source にせず、作成時の `--push` は使用しない。README/説明も事前確認する。
4. 作成直後に新リポジトリの GitHub Actions を無効化し、取得した設定が `enabled=false` であることを確認する。失敗・不明ならソースを push しない。既存の親リポジトリの Actions は変更しない。CI workflow は作らない。
5. 実際の owner/repo、URL、PUBLIC、main の基準 commit を観測する。default branch が main でなければ停止し、無断で branch 設定を変えない。
6. 常設 checkout と初期移行用 worktree を用意し、main の README commit からレビュー対象のソース・テスト・ライセンス・通常文書をコミットする。server 作成の README だけで「コード移行済み」としない。
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
- 親の運用経路の採用前、ライセンス未選択、公開候補未精査、実機切替未レビューの各段階は、個別に blocked と記録する。公開リポジトリが存在するだけで後段へ進めない。

## 8. 受け入れ基準・検証方針

### 動作環境と入力

既存の Dev Container と uv/Python（最低 3.12）、親が導入する ResoLoop / Flux-SDK を使う。インストール済み版は実行時に記録し、この移行で旧実機試験の依存や DLL を更新しない。ソース・通常文書には日本語や複数行の文字列があり、登録・UI の fake 入力にも非 ASCII と複数行を含める。

1. 新ソースのオフライン検査は、旧 world / tmp / state を参照しない隔離した一時領域で実行できる。world 呼出しは 0。新 package の import / 構文 / 参照、必要な PG の隔離 check/build を実行して確認する。
2. 移行対象一覧と新 Git tree が対応し、対象外の実機データ・第三者資産・秘密情報がない。権利の不明なファイルは保留し、ライセンス確定前にソースを push しない。
3. 元コードと凍結証拠は不変である。既存の保全検査を元の cwd で行い、旧試験の pin を変更しない。別ツールの動的 state は凍結・検査対象へ広げない。
4. 取得 helper は正しい origin の独立 checkout を受け入れ、別リポジトリや親のサブディレクトリを誤った対象として操作しない。既存ファイルを上書きせず、worktree からの呼出しでも常設の親の同じ位置を使う。
5. 新リポジトリの PUBLIC、Actions=false、default branch / origin の同一性を実設定の読み取りで確認できる。fake/API 記録だけで実際の GitHub 設定確認に代えない。
6. 移行後のコード・文書・テストの所在と未実施の実機条件が明確で、GitHub 作成、ソース初回公開、PR、マージ、実機切替の成否を別々に記録できる。

### 防御範囲とテストの採用

- S として、誤った checkout の選択・既存利用者データの上書き拒否と正例を、取得 helper のテストで確認する。必要なら親の複数 worktree から同じ常設領域を指す経路を含める。同じ守りを多層で重複テストしない。
- 再利用する既存 S は、対象取り違え、元値・復元記録の保持、競合時の拒否、失敗後の書込停止、コンパイラ出力の隔離等の意味を維持する。既存 F∩S は消さない。
- 文書本文・構成一覧・ツール名・今の設定値を写す F、import や構文エラーだけの L を新たな永続テストにしない。文書の確認は差分・参照検査で代える。
- 公開ファイル選別は初回の人による精査と Git tree / Gitleaks 検査を基準にする。汎用の自動エクスポート基盤は今回作らない。
- GitHub の操作手順は実行時の readonly 照合で確認し、本物の repo 作成・push・実機操作を自動テストに使わない。必要な実装テストはローカル一時 Git / fake CLI を使う。
- この防御は、資格情報を意図的に全ファイルへ複写する攻撃や GitHub アカウントの侵害まで保証しない。Gitleaks は権利・個人情報・world 完全保存の確認の代わりにならない。

## 9. 対象外と未決事項

### 対象外

ツールの新機能、UI 変更、Preview/Commit の完成、既存実機試験の合格化、実アバターの登録・色変更、state の転送、他ツールの移行、Dev Container の独立配布、CI の追加、汎用の外部実装許可の拡張、公開済み履歴の書き換え、既存資料の削除。

### 利用者の確認が必要な事項

- この設計全体と、提案するリポジトリ名 `usaturn/resonite-emission-editor`。
- ソースの権利確認後のライセンス選択。実装計画内の公開前の停止ゲートとして扱い、選択を推測しない。
- 後続 Plan の内容・実行範囲と、repo 作成 / push / PR / マージ / 実機切替の各許可。

### 実装担当に委ねる事項

採用候補の詳細な依存一覧、汎用部品の分離が必要な最小箇所、helper の内部構成、同じ守りを代表する S テストの具体例。受け入れ条件・公開境界・実機への切替条件を変更する判断は委ねない。

## 10. 調査と設計確認の記録

- `gh repo view usaturn/create-reso-world --json nameWithOwner,visibility,url,licenseInfo,defaultBranchRef` の読み取りで PUBLIC / main / licenseInfo=null を確認。リポジトリ設定の書き込みはしていない。
- `docs/resoloop-meshy-workflow.md`、既存 helper、root `.gitignore`、`scripts/scan-before-push.sh`、`scripts/superpowers_context.py` と Emission のソース/テストの依存を読み取りで調査した。
- Context7 CLI で GitHub CLI の `repo create` / `repo view` / `api` と、Actions permissions API を確認した。リポジトリ作成や Actions の設定変更はしていない。
- 読み取り調査の subagent を 2 件 dispatch したが、いずれもツール応答が無出力で、予定のレポートもなかった。結果・独立確認の成功・子の終了状態は認定しない。controller が限定した読み取り調査を代行した。設計確認で子を使えない場合は、その制約を明記して自己点検する。
- 設計作成後の読み取り専用 builder check は `sp-review` へ委譲し、応答は `nothing important left`（計画作成に必要な重要な追加質問なし）だった。これは設計承認やコード監査・実機確認ではない。先の無出力の調査 2 件の成功・終了状態を後から認定する根拠にも使わない。所要時間・子の session ID は応答に含まれず、推測して記録しない。
- この設計文書だけの変更には永続テストを追加しない（F/L）。コミット前に文書差分、参照先、`git diff --check` を確認する。設計承認後に実装計画を作成する。

参照:

- [GitHub CLI: gh repo create](https://cli.github.com/manual/gh_repo_create)
- [GitHub CLI: gh api](https://cli.github.com/manual/gh_api)
- [GitHub REST: Actions permissions](https://docs.github.com/en/rest/actions/permissions)
