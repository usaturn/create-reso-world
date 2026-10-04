# PR #27 pi 移行の追加点検・JSON保存修正方針

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象Issue／PR: #19／#27
- 検証したコードHEAD: `4ae2cb5af8cab7370b2933593ab1a3e3b8b8b19c`（R4-1）。R3-1〜R3-6は`26d8b1ca757179b9b9c3b406728f1fa1e700d664`で調査した
- 状態: completed（内容の別途承認ではなく、下記の明示的な推奨修正・検証・PR全体の再レビュー・push許可に基づいて実装・検証を完了した。コミットだけでapprovedとするものではない）
- 関連Plan: `docs/superpowers/plans/2026-10-04-pr27-pi-migration-round2-review-fixes.md`
- 今回更新するSpec: `docs/superpowers/specs/2026-10-04-pr27-pi-migration-round2-review-fixes-design.md`。PR本文と既存コメントが追加点検の後継文書として明示するこのファイルを更新する。以前のR2-1〜R2-5は`26d8b1c`版、R3の入力分類は`4ae2cb5`版をGit履歴で参照する。
- 運用: 文書ライフサイクル規約に従い、回ごとの新規文書は作らず既存Spec・Planを更新する。

## 依頼・経路・承認

### 今回（R4、調査HEAD `4ae2cb5`）

対象は `usaturn/create-reso-world` PR #27、`feat/issue-19-pi-migration`。ユーザーの依頼は、PRとレビュー結果 `reviews/#27-feat-issue-19-pi-migration/` の全指摘・変更ファイル全文・関連処理とテストを確認して修正要否を確定し、修正が必要なら推奨案を基本に修正し、検証とPR全体の再レビューを完了してpushすること。同じ原因の関連箇所はPR差分外も修正し、後続のレビュー・修正で手戻りを出さないことを求めている。この依頼が実装・検証・既存PRへのpushの具体的な許可であり、追加の承認待ちは挟まない。修正が必要だったため今回はマージしない。`pr-review`は使用しない。経路は bounded（共有JSON helperと既存provider setupの保存先検査の追加）。

### 前回（R3、調査HEAD `26d8b1c`）

ユーザーは推奨案による修正・pushまでを明示的に依頼し、差分外の関連処理の点検・修正も依頼に含めた。経路は bounded（既存のcleanup・provider setupの修正）。修正が必要なためマージせず、既存PRへ追加1コミット`4ae2cb5`で反映した。

目的は再レビューで修正が積み重ならないよう、入力の読込みからpi/npm委譲、モデル保存、再実行までを調べ、認証・独自モデル・無関係な設定を壊さず移行を完了できるようにすること。

## 入力レビューの全分類（R4）

入力は5ファイル。`SWE-2-Max.md`、`claude-opus-5-5.md`、`commandcode-deepseek-deepseek-v4.1-flash.md`、`openai-codex-gpt-6.1-sol.md` の最新対象HEADは `4ae2cb5af8ca`、`gpt-6.1-sol.md` は `26d8b1ca7571`。過去の履歴は各ファイルに保持されている。各指摘は現行HEAD `4ae2cb5` のコミット済み内容で検証した。

| 入力・ID | 分類 | 根拠／方針 |
| --- | --- | --- |
| DeepSeek L-2 | 対応する (a) | `setup_pi.zsh`がsymlink・hard linkの`models.json`を通常ファイルへ置き換え、共有先を更新しなくなる。旧版はリンク先を更新していた。`4ae2cb5`で3種のリンクとも成功終了・リンク切断を再現。同じ共有writerを使う関連setupにも同じ原因がある。R4-1。 |
| DeepSeek I-1 | 対応しない | pi-model-nameの`PI_DISTILL_MODEL`記述は主モデル判定に使わない否定例で機能不具合はない。Issue #19が「pi-model-nameスキルのPI_DISTILL_MODELの記述も変えない」と編集範囲から明示的に除外している。 |
| DeepSeek resolved L-1（単独サロゲート） | 解消済み | `pi_json.write_object`の`ensure_ascii=True`で保存し、`test_r3_surrogate_settings_roundtrip_backup_mode_and_noop`が成功。 |
| SWE resolved L-1（非有限数値） | 解消済み | `pi_json.load_object`の有限範囲検査がbackup・pi呼出し前に止め、`test_r3_numeric_overflow_refused_in_every_metadata_before_mutation`が成功。 |
| Claude resolved L-1（`-builtin:mcp`の扱い） | 解消済み | `cleanup_pi_mcp.enable_builtin_mcp`のdocstringと`.devcontainer/README.md`の移行節が、利用者のdisableも毎回除去する仕様と共有影響を明記。 |
| Claude resolved I-1（rebuild前のexport） | 解消済み | README の「組み込み MCP と廃止した拡張」節がrebuild後の反映と既存コンテナでのexport削除・unsetを書き分けている。 |
| GPT resolved I-1（API トークン節） | 解消済み | READMEのAPIトークン節から廃止したDistillation用`DEEPINFRA_TOKEN`要件が消えている。 |
| SWE・DeepSeek 未検証候補: 実pi・実registryの`pi update --extensions` | 対応しない（指摘なし、今回実測） | 不具合の根拠はない。Issue #19の受け入れ条件のため、今回、隔離環境で実pi・実npm registryによるend-to-endを実測した（結果は「完了結果と検証」）。 |
| SWE・DeepSeek 未検証候補: 実認証MCP接続 | 対応しない | Issue #19の仕様が実認証の接続確認をこの子の検証範囲外とする。設定内容は`test_project_builtin_mcp_settings_are_shared_with_worlds`が固定。 |
| SWE・DeepSeek 未検証候補: Dev Container rebuild | 対応しない | Issue #19がrebuildをIssue #22の担当と定める。 |

集計: 解消済み5／対応する1／判断保留0／対応しない4（うち3件は未検証候補）。Claude・Codex・GPT・SWEのactive指摘は0。

## PR全体の独立再レビューの指摘（R4）

ユーザーの「全指摘・変更ファイル全文・関連処理とテストを確認し、再レビューで見つかった問題は解消するまで繰り返す」という指示に従い、`4ae2cb5`のPR全体を読み取り専用の担当に独立レビューさせた。入力ディレクトリ外の指摘だが、同じ指示に基づき全件を分類する。検証は現行HEADのコミット済み内容と、隔離した一時HOMEでの再現で行った。

| 指摘 | 分類 | 根拠／方針 |
| --- | --- | --- |
| R-1 Low: NaN・Infinity拒否のテストが`package-lock.json`と`npm-shrinkwrap.json`ではshadowed lock検査で通ってしまう | 対応する (c) | R3-4の追加で回帰ガードが弱まった。`reject_constant`を無効にした変異版で、旧テストは15件中6件を見逃し、補強後は15件すべてを検出することを確認した。R4-3。 |
| R-2 Low: `setup_pi.zsh`が入力検査の前にバックアップを作る | 対応する (a) | 数値範囲外・不正なJSON・不正な`pi-models.json`で、不要なバックアップを残して失敗することを再現した。mainからの順序だが、R3で拒否する条件が増えた。R4-2。 |
| R-3 Low: 保持する独自拡張が撤去対象のhelperに依存すると、cleanupが毎回止まる | 対応しない | `docs/superpowers/specs/2026-10-04-pr27-pi-migration-review-fixes-design.md`（R1、調査HEAD `6f0cd9e`）が「標準8拡張に依存はなく、保持する実体を削除しない理由付きの停止」として対応しないと決めた事項で、レビュー担当もregistryで標準拡張に依存が無いことを確認している。第三者拡張の構成だけで起きる。依存関係を正しく除外するにはlockの依存グラフ解析が必要で、新しい誤判定の経路が増える。 |
| R-4 Info: `setup_pi_opencode_go.zsh`が`models.json`の検査前に`auth.json`を更新する | 対応する (a) | 範囲外の数値の`models.json`でも認証が先に書き換わることを再現した。R4-2。 |
| R-5 Info: `auth.json`がsymlinkのとき、リンク先のmodeを変える | 対応する (a) | R4-1と同じ原因で、R4-1で解消する。 |
| R-6 Info: setupのエラーでパスが2回出る | 対応する | `pi_json.load_object`が付けるパスに、3つのsetupが同じ接頭辞を重ねていた。R4-2で事前検査の表示と各ブロックの表示を直す。 |
| R-7 Info: 文書と範囲の不一致（Issue #19 Specの比較表に追加ファイルが無い、ルートREADMEのnugetモードの記述、Issue #19 Spec・Planの状態欄） | 対応する (b) | 比較表は#22の集約に使われる。ルートREADMEは、nugetモードもNuGetから取得する（`install_resoloop.bash`）のにネットワーク不要と読める。状態欄は`docs/superpowers/README.md`の規約。R4-4。 |
| 未検証候補: `GOOGLE_DEV_KNOWLEDGE_API_KEY`未設定時の通知 | 対応する（記述の追加） | pi 1.0.2の同梱文書（`docs/mcp.md`）で、設定エラーと接続失敗を起動後に1回通知すること、同名のプロジェクト定義が利用者定義を置き換えること、`/mcp`の有効・無効は定義元のファイルへ保存することを確認した。利用者が追跡対象の`.pi/mcp.json`を誤ってコミットしないよう、READMEに書く。R4-4。 |
| 未検証候補: グローバル設定の`!builtin:mcp` | 対応しない | Issue #19は「settings.jsonからは`-builtin:mcp`だけを取り除く」と定めている。プロジェクトの`+builtin:mcp`が優先されるため、このリポジトリ内の動作には影響しない。 |
| 未検証候補: cleanupの`expanduser`が`~other/...`も展開する | 対応しない | mainからの既存挙動。READMEが`PI_CODING_AGENT_DIR`に安全な絶対パスか`~/...`の指定を求めている。 |
| e2e検証での観察: cleanupのstderrに`No matching package found for npm:pi-extensions-*`が出る | 対応しない | pi-distillの撤去でnpmが依存のhelperを先に消すため、未登録のhelperの`pi remove`が正確な診断行とexit 1を返す。設計どおりに許容する経路で、`test_undeclared_removal_accepts_diagnostic_line_amid_stderr_noise`などが固定している。 |

集計（独立再レビュー）: 対応する7（記述の追加1件を含む）／判断保留0／対応しない4。

## R4-1: リンクされた保存先を変更前に拒否する (a)

### 原因

R3-3で3つのprovider setupの保存を共有helper `pi_json.write_object` に揃えた。この関数は同じディレクトリの一時ファイルを`os.replace`するため、保存先がsymlinkならリンク自体を通常ファイルに置き換え、hard linkなら新しいinodeに切り離して別名側を古い内容のまま残す。dangling symlinkもリンク先を作らず置き換える。いずれも終了コード0で警告もないため、利用者は共有先が更新されないことに気付けない。調査担当が`fc5c7ea`（main）と`4ae2cb5`を隔離HOMEで比較実行した結果は次のとおり。

| 書き込み経路 | main（`fc5c7ea`） | PR（`4ae2cb5`） |
| --- | --- | --- |
| `setup_pi.zsh`の`models.json` | `Path.write_text`でsymlink・hard linkのリンク先を更新、danglingはリンク先を新規作成 | 3種とも通常ファイルへ置換（PRによる退行） |
| `setup_pi_opencode_go.zsh`・`setup_pi_commandcode_goat.zsh`の`models.json` | 固定名`.tmp`の`os.replace`で置換 | 置換（PR前から同じ原因） |
| `setup_pi_opencode_go.zsh`の`auth.json`更新 | 置換 | 置換に加え、保存前の`os.chmod`がリンク先・共有inodeのmodeを600へ変更（PRによる退行） |
| 同`auth.json`のキーが同じ場合 | シェルの`chmod 600`がリンク先のmodeを変更 | 同じ（PR前から） |
| `cleanup_pi_mcp.py`の`settings.json` | `read_object`がsymlink・hard link・非通常ファイルを拒否 | 同じ。書き込みは拒否検査の後だけ |

pi本体（1.0.2）は`auth.json`・`settings.json`を`writeFileSync`でリンクを辿って書き、`models.json`には書かない（読み取りのみ）。リポジトリ内に、agent directory配下のファイルをリンクにする運用・記述は無い（ワールドの`.pi -> ../.pi`はプロジェクト設定で、agent directoryではない）。

### 方針

Issue #19とPlanのGlobal Constraintsが維持を求める「設定・パッケージ保存先のsymlink・hard link拒否」と同じ方針を、setupが書くファイルにも適用する。

- `pi_json.require_plain_file(path)`を追加する。`lstat`で、存在しなければ許可し、symlink（danglingを含む）、通常ファイル以外（FIFO・ディレクトリなど）、リンク数が1でないファイルを、パスを含む`ValueError`で拒否する。
- `write_object`は最初にこの検査を行い、一時ファイルを作る前に止める。どの呼出し元もリンクを置き換えない。
- `cleanup_pi_mcp.read_object`の同じ検査（非通常ファイル・hard link）はこの関数を使い、規則を1か所にまとめる。祖先を含むsymlink検査`safe_storage`はcleanup固有のまま維持する。
- 3つのsetupは、書く可能性のある全ファイル（DeepInfra・CommandCodeは`models.json`、OpenCode Goは`auth.json`と`models.json`）を、バックアップ・chmod・認証やモデルの変更より前にまとめて検査し、`ERROR: <理由>: <path>`で非ゼロ終了する。OpenCode Goで`models.json`がリンクでも`auth.json`を先に更新しない。この事前検査はR4-2の入力検査と同じブロックで行う。
- 検査対象は書くファイル自身に限る。agent directory自体がsymlinkでも、ファイルの置き換えでリンクは外れないため、従来どおり動作させる（main以前からの挙動を維持）。cleanupはagent directoryと祖先のsymlinkを拒否する既存仕様を維持する。

### 採用しなかった案

- リンク先を辿って更新する案（レビューの推奨(a)、pi本体と同じ書き方）: hard linkは一時ファイルの置き換えでは保てず、保つには上書き保存に戻す必要があり、書き込み途中のI/Oエラーや中断で内容が欠ける危険が戻る（R3-3で一時ファイルの置き換えにした理由）。symlinkではリンク先がagent directory外の任意の場所になり得て、一時ファイルを置くリンク先ディレクトリの書き込み権限、dangling・ループの扱いという新しい判断が増える。cleanupが「リンクされた保存先は変更しない」と決めている既存方針とも食い違う。
- 置き換えを仕様としてREADMEに書くだけの案: 共有先が黙って更新されなくなる不具合を残す。Issue #19の「失敗したときは理由を出して止まり、利用者の設定を壊さない」に反する。

この判断により、`setup_pi.zsh`はmainでは辿っていたsymlink・hard linkの`models.json`を、置き換えずに理由付きで停止するようになる。リポジトリにリンクで運用する手順は無く、黙って壊すよりも停止して案内する方を仕様とし、READMEのsetup節に明記する。

### 対象外とした関連箇所

- `install_beforehand.bash`の`models.json`配置は、通常ファイルとして存在しないときだけ`cp`する。既存リンクを置き換えず（dangling symlinkでは`cp`が書き込みを拒否して停止する。mainから同じ）、`pi_json`も使わないため同じ原因ではない。
- `setup_pi_superagents.zsh`の`extensions/subagent.d/*/config.json`配置は、リポジトリ管理の設定ファイルを`install`で丸ごと配置する別の仕組みで、`pi_json`を使わずPRでも変更していない（Issue #20の担当）。
- pi本体による`auth.json`等の保存方式は外部実装であり変更しない。

### 検証（R4-1）

- `test_r4_shared_writer_refuses_linked_or_special_destinations`: symlink・dangling symlink・hard link・FIFO・ディレクトリで`write_object`が一時ファイルを作らずパス付きの`ValueError`を出し、agent directoryと共有先のエントリ（リンクの向き、mode、リンク数、バイト列）が不変。
- `test_r4_provider_setups_refuse_linked_destinations_before_changes`: 3setup × 書く各ファイル × symlink・dangling・hard linkの15ケースで、成功表示なしの非ゼロ終了、エラーにパスとリンク種別、agent directoryと共有先の全エントリ不変（バックアップ・一時ファイルなし、OpenCode Goのもう一方のファイルも不変、共有先のmode不変）。
- `test_r4_provider_setups_accept_symlinked_agent_directory`: agent directory自体がsymlinkなら3setupとも成功し、実体側の`models.json`を更新して他providerを保持し、リンクを保つ（過剰な拒否の防止）。
- 既存のcleanupのリンク・hard link・FIFO拒否テストと、setupの保存・バックアップ・mode・tildeの全テストが引き続き成功すること。

## R4-2: 入力の事前検査をバックアップ・認証更新より前に行う (a)

`setup_pi.zsh`はシェルで`models.json`をバックアップしてからPythonで入力を検査し、`setup_pi_opencode_go.zsh`は`auth.json`を更新してから`models.json`を検査する。どちらもmainからの順序だが、R3で数値範囲などの拒否条件が増え、失敗時に不要なバックアップや更新済みの認証が残る。

- R4-1の事前検査ブロックで、`pi-models.json`と、setupが書く各ファイル（存在する場合）を`pi_json.load_object`で読み、バックアップ・chmod・変更より前に止める。表示は`ERROR: <load_objectのメッセージ>`とし、パスは1回だけ出す。
- 各setupの本体ブロックの検査は防御として残し、エラー表示の重複した接頭辞だけを外す。
- 変えないもの: DeepInfraが実行のたびにバックアップを作る挙動、`cp -p`の失敗伝播、`pi-models.json`にproviderが無い場合の扱い（リポジトリ側の定義の誤り）、provider選択・認証0600・認証のバックアップを作らない仕様。

検証: `test_r3_provider_models_reject_unsafe_numbers_preserving_original`（3setup × 7種の数値・定数）と`test_r3_provider_invalid_source_preserves_models`（3setup × 5種の不正な`pi-models.json`）は、agent directory全体のエントリ（バックアップ・`auth.json`・一時ファイルの有無を含む）が不変であることを検査し、前者はエラー中のパスが1回であることも検査する。`test_setup_invalid_models_json_fails_without_success_banner`はバックアップが無いことを検査する。実装前はDeepInfraのバックアップ作成、OpenCode Goの認証更新、3setupのパスの二重表示で32件が失敗した。

## R4-3: shadowed lock検査に隠れた回帰ガードを戻す (c)

`test_nonstandard_json_constants_stop_before_mutation`は、準備した`npm-shrinkwrap.json`と`package-lock.json`の両方に撤去対象があるため、`package-lock.json`・`npm-shrinkwrap.json`の6ケースではR3-4のshadowed lock検査でも同じassertが通っていた。stderrに`Invalid JSON constant`が含まれることを検査し、どの検査で止まったかを区別する。準備は変えない（両方の検査が同時に成り立つ状態でも、厳格なJSON検査が先に止めることを固定する）。

## R4-4: 文書の修正 (b)

- ルート`README.md`: ResoLoopはどちらのモードもネットワークから導入し、forkモードはビルドに数分かかると直す。
- `docs/superpowers/specs/2026-10-04-issue-19-pi-migration-design.md`の比較表（#22の集約用）に、`pi_json.py`、関連setup 2種、ルート`README.md`の行を足す。Issue #19のSpec・Planの冒頭に、`docs/superpowers/README.md`が求める文書管理・対象・検証HEAD・状態と、実行許可・内容承認の区別を書く。Planのチェックボックスは作成時のまま残し、その旨を書く。
- `.devcontainer/README.md`: setupの入力検査とリンク拒否の説明（R4-1・R4-2）、同じディレクトリの一時ファイル「で」元ファイルを置き換えるという記述の修正、`GOOGLE_DEV_KNOWLEDGE_API_KEY`未設定時の通知と無効化の注意を書く。

## R3の調査と修正（調査HEAD `26d8b1c`、維持）

新規の隔離worktreeを固定SHAから作り、debug担当が本体・全テスト・fake・caller・関連setup・導入済みpi 1.0.2/npm 11.19.0の公式同梱文書と実装を確認した。別の読み取り専用担当がPR全20ファイル、削除helper、関連する差分外処理を再点検した。元58テストは全成功。debug担当は隔離cleanup 108ケース、setup 7ケース、全2048サロゲートの文字列／キーround-tripを検査した。controllerもoverflow、surrogate、実npm二重lock、setup3種のtilde保存先、固定dateのbackup上書きを独立再実行した。いずれも実ユーザー設定・実認証・registryを使用していない。

調査worktreeとその一時親は調査終了後に削除し、新しい実装worktreeを作る。他のworktreeの未コミット内容は根拠に使用しない。

### R3-1: 数値の有限範囲を変更前に検査 (a)

`parse_constant`はNaN/Infinity等だけを捕捉し、指数overflowや指数なしの巨大整数を捕捉しない。実pi/npmのJSON.parse→JSON.stringifyで無関係な値がnullに変わる。settingsと全4マニフェストを読む共通経路で、浮動小数表記だけでなく整数表記もpi/npmが扱える有限Number範囲か検査する。受理した整数はPython intのまま返し、通常の精度を不必要に落とさない。非標準定数の拒否を維持する。対象pathと数値範囲のエラーを表示し、backup・pi呼出し・cache unlinkより前に停止する。

検証: ±1e999、±10^309の整数、nested、全metadata配置、disable-only／settings-only／cache-only、実piのnull変質経路。元バイト列、mode、cache、backup数、pi呼出しなしを検査する。最大有限値、0e999、subnormal、quoted数値、通常整数・Unicodeは受理する。2^53のsafe integer制限やDecimal/raw token editorは追加しない。

### R3-2: 有効なサロゲートをエスケープして保持 (a)

cleanupは`ensure_ascii=True`でJSON保存し、厳格UTF-8に不正なコード単位を渡さない。UTF-8、indent、末尾改行、allow_nan=False、mode、最新settingsの読込み、一時ファイル置換と失敗時掃除を維持する。有効なJSONエスケープを入力で禁止しない。

検証: high/low単独サロゲート、nested文字列・キー・配列、Japanese/emoji/paired/literal backslash、BOM、disable-onlyと撤去あり、再実行の不変、元backupとmode、実pi。raw不正UTF-8は引き続き変更前に拒否。

### R3-3: 関連provider setupのモデル保存を保護 (a)

DeepInfra setupの直接write_textはUnicodeEncodeErrorでmodels.jsonを0バイトにし、overflowをInfinityとして保存して偽の成功を出す。OpenCode Go／CommandCodeの関連writerにも同じparse・serializeパターンがある。共通の小さいJSON helperを`.devcontainer/`に置き、3setupの入力JSONを同じ有限数値・非標準定数の規則で読み、文字列・キーを保持可能なJSONを最後までserializeしてから固有一時ファイルへ保存し置換する。既存modeを保持し、新規ファイルは0600とする。失敗時に元モデルと他providerを保持し、一時ファイルを残さない。OpenCode auth writerも同じJSON規則を使用し、0600と認証backupを作らない仕様を維持する。providerの選択・上書き仕様、ランチャーとtier・catalog処理は変更しない。

検証: 各setupのsurrogate値／キー保存、±overflow／巨大整数／NaN拒否、元モデル保持・成功バナーなし、source側の不正JSON、保存失敗とmode、実piのcredential-blind ModelConfig読込み。実値でないAPIキーだけを使用。

### R3-4: shadowed root lockの事前停止 (a)

実npmはshrinkwrapが存在するとpackage-lockを無視し、両者に撤去対象がある場合、settings・実体・active lockだけが変わってpostconditionで止まる。shrinkwrapがありshadowed package-lockに撤去対象が残る組合せを変更前に検出して、両pathと利用者がlockを整合させてから再実行する診断で停止する。任意lockの自動削除・prune・rollbackは行わない。shadowed lockに対象がない場合と単一lockは通常どおり移行する。

検証: 実npmの双lockでpi呼出し・backup・全バイト変更なし。settings宣言あり／manifest-only。単一shrinkwrapと単一package-lock成功。既存backup全metadataテストはshadowed lockを対象なしにしてbackupの元バイト保存という元の回帰観点を維持する。fakeが両lockを掃除する挙動を成功根拠にしない。

### R3-5: モデルbackup世代を上書きしない (a)

DeepInfraは秒単位のcp先が衝突すると元backupを上書きすることを固定dateで再現。関連2setupも同形式を持つ。DeepInfraのcp失敗伝播の既存回帰を維持し、衝突時は固有suffix／連番で世代を保存する。他setupも固有名を使用する。認証backupは作らない。

検証: 同一時刻の再実行でも元世代が不変、複数backupは各実行前バイトと対応、cp失敗時は元モデル不変・成功なし。backup名をtimestampのみと仮定しない。

### R3-6: provider setupの保存先を揃える (a)

OpenCode GoとCommandCodeは`PI_CODING_AGENT_DIR='~/custom agent'`を展開せず、cwdの文字列`~`へ書くことをcontrollerが再現。DeepInfraと同じexact `~`／`~/`のみのHOME展開を行う。eval・他ユーザーのtilde展開は使わない。

検証: `~`、`~/`、空白を含む`~/...`、absolute、未設定／空、`~other`の3setup。期待するmodels/auth配置、他provider保持、cwdの不要な`~`不在。superagentsのHOME固定仕様は変更しない。

## 保持する判断・検証境界

- cleanup前にpiを終了する既存運用を維持し、新しい同時実行lockは作らない。
- 利用者の-builtin:mcp除去、既存provider保持、pi-model-name否定例は既存仕様を維持。
- auth/native MCP/共有設定・スキル・ワールド・ResoLoop版は変更しない。
- 関連setup2種の差分外修正は今回のユーザー指示を根拠とする。保護されるproviderと呼出し順を変更しない。
- R4: setupはリンクされた保存先を置き換えず、変更前に停止する。検査は書くファイル自身に限り、cleanupの祖先を含むsymlink拒否はcleanup固有として維持し、setupへ広げない。setupの保存方式（一時ファイルの置き換え・mode・backup・auth 0600）は変えない。
- 関連suite、全environment suite、layoutを実行する。slum03スキル未同期はpristine mainでも再現確認し、それ以外の失敗を放置しない。
- 最新origin/mainが進んでいるため統合も確認し、最新mainの既存修正・文書を後退させない。
- 実装担当はRED→GREENを同期実行し、別担当によるTask仕様・品質レビューとPR全体最終レビューを受ける。公開前にremote HEADが調査時と同じであることを再確認する。

## 完了結果と検証

### R4（今回）

R4-1〜R4-4を実装した。`pi_json.require_plain_file`がリンク・特殊ファイルの拒否を一元化し、`write_object`とcleanupの`read_object`が使う。3つのsetupは、書くファイルのリンク検査と全入力のJSON検査をバックアップ・chmod・変更の前にまとめて行う。cleanupの事前検査順、setupの保存方式・provider選択・認証保護・失敗伝播は変えていない。

- RED→GREEN: R4-1は実装前に、writerの5種すべてで一時ファイルが作られ、setupの15ケースすべてが成功終了した。実装後は全件成功。R4-2は実装前に32件が失敗し、実装後は成功。R4-3は`reject_constant`を無効にした変異版で、旧テストが6件を見逃し、補強後は15件すべてを検出した。リンクされたagent directoryの対照テストは実装前後とも成功（既存挙動の維持）。
- 最終版での検証: 移行・setupテスト79件（従来76件＋新規3件）成功、全environment 27/27、layout成功、スキル408成功・1skip、`git diff --check`成功。関連の個別検査（README・導入順・指示文・docs・agent-config・file-modes）も成功。
- 実pi 1.0.2・実npm registryでのend-to-end（調査HEAD `4ae2cb5`。隔離したHOME・agent directory・npm設定で、install scriptは実行しない）: `pi install`で5種と保持拡張を入れた旧状態から、cleanup、`pi update --extensions`（通常実行、npm installを強制する経路、保持拡張の版更新）の順に実行し、5種の登録・マニフェスト・`node_modules`は復活せず、保持拡張は残った。マニフェストを残した陰性対照では復活を検出できた。cleanupの再実行ではagent directory全体のバイト列とバックアップ数が変わらない。provisioning片の初回環境・既存環境・再実行でも同じ結果だった。R4でcleanupの撤去処理は変えておらず（`read_object`の検査を共有関数へ移しただけ）、移行テスト79件でも確認している。
- 調査担当（リンク挙動の比較・pi本体の書き方）、独立レビュー担当（PR全体）、e2e担当の3つのサブエージェントは、いずれも専用の一時worktreeを使い、終了時に撤去した。ホストの実際の`~/.pi`は使っていない（独立レビュー担当が最初に`pi --version`を実HOMEで1回実行したため、`settings.json.lock`が残っていないことを確認した）。

未検証は実認証のMCP/provider接続とDev Container rebuild（#22の担当）。成功と扱わない。PR全体の最終再レビューの結果、公開SHA、所要時間はPRの最終ステータスコメントに記録する。修正があったためpushまでとし、PRとIssueはopenのままにする。

### R3（前回）

R3-1〜R3-6を実装した。小さい共通`pi_json.py`で有限範囲のobject読込み、ASCIIエスケープによる安全保存、固有モデルbackupを扱う。cleanupの既存安全策と事前検査順、setupのprovider選択・認証保護・失敗伝播は保持した。関連2setupの保存先も揃えた。

Taskの独立レビューで、backup処理の重複とDeepInfra予約ファイルによるbackup mode変化を見つけ、公開前に共通helper抽出・cp -p・回帰で修正した。限定再レビューは全指摘解消、最終PR全23ファイルのレビューはCritical/Important/Minorいずれも0だった。新しいPyrightのテスト変数束縛指摘も、実挙動を変えず明確化して再検査した。

controllerの最終検証: 全環境27/27スクリプト成功、移行・setup76テスト成功、layout成功（4ワールドの同期を含む）、スキル408成功・1skip（最新main統合後）、実PR差分検査成功。実pi 1.0.2の隔離no-prefix移行、数値の事前停止、サロゲート保持、3setup出力のNode JSON.parseとcredential-blind ModelConfig読込みも成功した。shadowed lock検査は実npmのオフライン制御で固定した。

今回取り込んだmain `4e6f1d0`にはslum03同期修正が含まれ、以前のlayout失敗は再現しなかった。その後PR #29・#31でmainが`fc5c7ea5e5bab567ecdc8d8683040203a48c87e3`へ進んだため、公開前に競合なく取り込み直した。レビュー済みの`.devcontainer/`・`.pi/`内容は不変で、最新main統合後も環境27/27、layout、スキルの全検証が成功した。mainから取り込んだ文書・スキル・ワールドの内容は独自変更していない。

active LSPの残るprimary2件は元HEADのreal-npm fixtureと同一の型推論指摘。共通parserの補助2warningは、JSON decoderの数値token callbackと外側のValueError捕捉を認識しないルールによるもの。変更した実装に新しいprimary errorはない。全ファイルLSP cleanとは報告しない。

未検証は実認証MCP/provider、live registry更新、Dev Container rebuild（#22担当）。成功と扱わない。所要時間・公開SHA・remote確認はPRの最終ステータスコメントに記録する。修正があったためpushまでとし、PRとIssueはopenのままにする。
