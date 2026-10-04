# PR #27 pi 移行の追加点検・JSON保存修正方針

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象Issue／PR: #19／#27
- 検証したコードHEAD: `26d8b1ca757179b9b9c3b406728f1fa1e700d664`
- 状態: completed（内容の別途承認ではなく、下記の明示的な推奨修正・push許可に基づいて実装・検証を完了した。コミットだけでapprovedとするものではない）
- 関連Plan: `docs/superpowers/plans/2026-10-04-pr27-pi-migration-round2-review-fixes.md`
- 今回更新するSpec: `docs/superpowers/specs/2026-10-04-pr27-pi-migration-round2-review-fixes-design.md`。PR本文と既存コメントが追加点検の後継文書として明示するこのファイルを更新する。以前のR2-1〜R2-5と検証記録はGitの`26d8b1c`版に保持する。
- 運用変更: 調査途中でmainに文書ライフサイクル規約が入ったため、新しいround3文書は作らず既存Spec・Planを更新する。今回のユーザーの許可は、レビュー全件、PR全体と差分外の関連箇所の修正、検証、既存PRへのpushを具体的に含む。追加承認待ちや文書だけの中間コミットは挟まず、検証後の1コミットに含める。

## 依頼・経路・承認

対象は `usaturn/create-reso-world` PR #27、`feat/issue-19-pi-migration`、調査HEAD `26d8b1ca757179b9b9c3b406728f1fa1e700d664`。経路は bounded（既存のcleanup・provider setupの修正）。ユーザーは推奨案による修正・pushまでを明示的に依頼しているため、追加の承認待ちは挟まない。差分外の関連処理の点検・修正も依頼に含まれる。修正が必要なため今回はマージせず、既存PRへ追加1コミットで反映する。`pr-review`は使用しない。

目的は再レビューで修正が積み重ならないよう、入力の読込みからpi/npm委譲、モデル保存、再実行までを調べ、認証・独自モデル・無関係な設定を壊さず移行を完了できるようにすること。

## 入力レビューの全分類

全4ファイルの最新対象HEADは `26d8b1ca7571`。過去履歴は各ファイルに保持されている。

| 入力・ID | 分類 | 根拠／方針 |
| --- | --- | --- |
| SWE-2-Max L-1 | 対応する (a) | `1e999`が読込みを通り、backup／撤去後の保存で失敗する。実piではnullへの変質も再現。R3-1。 |
| DeepSeek L-1 | 対応する (a) | 有効なJSONエスケープの単独サロゲートがUTF-8保存で失敗する。キー・値・nested・実piでも再現。R3-2。 |
| DeepSeek I-1 | 対応しない | pi-model-nameの旧変数は主モデル判定に使わない否定例。Issue #19が保持を明記し、機能不具合はない。 |
| Claude resolved L-1 | 解消済み | 現HEADのdocstringとREADMEが、利用者のdisableも毎回除去する実仕様・共有影響を明記している。 |
| Claude resolved I-1 | 解消済み | 現HEAD READMEはrebuildと既存コンテナのexport削除・unsetを区別する。 |
| GPT resolved I-1 | 解消済み | 廃止したDistillation用トークン要件をREADMEから除去済み。 |

集計: 解消済み3／対応する2／判断保留0／対応しない1。Claude・GPTのactive指摘は0。未検証候補である実認証MCP、registry update、rebuildは未検証と明記し、成功扱いしない。rebuildはIssue #22の担当。

## 調査と追加の再現

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
- 関連suite、全environment suite、layoutを実行する。slum03スキル未同期はpristine mainでも再現確認し、それ以外の失敗を放置しない。
- 最新origin/mainが進んでいるため統合も確認し、最新mainの既存修正・文書を後退させない。
- 実装担当はRED→GREENを同期実行し、別担当によるTask仕様・品質レビューとPR全体最終レビューを受ける。公開前にremote HEADが調査時と同じであることを再確認する。

## 完了結果と検証

R3-1〜R3-6を実装した。小さい共通`pi_json.py`で有限範囲のobject読込み、ASCIIエスケープによる安全保存、固有モデルbackupを扱う。cleanupの既存安全策と事前検査順、setupのprovider選択・認証保護・失敗伝播は保持した。関連2setupの保存先も揃えた。

Taskの独立レビューで、backup処理の重複とDeepInfra予約ファイルによるbackup mode変化を見つけ、公開前に共通helper抽出・cp -p・回帰で修正した。限定再レビューは全指摘解消、最終PR全23ファイルのレビューはCritical/Important/Minorいずれも0だった。新しいPyrightのテスト変数束縛指摘も、実挙動を変えず明確化して再検査した。

controllerの最終検証: 全環境27/27スクリプト成功、移行・setup76テスト成功、layout成功（4ワールドの同期を含む）、スキル408成功・1skip（最新main統合後）、実PR差分検査成功。実pi 1.0.2の隔離no-prefix移行、数値の事前停止、サロゲート保持、3setup出力のNode JSON.parseとcredential-blind ModelConfig読込みも成功した。shadowed lock検査は実npmのオフライン制御で固定した。

今回取り込んだmain `4e6f1d0`にはslum03同期修正が含まれ、以前のlayout失敗は再現しなかった。その後PR #29・#31でmainが`fc5c7ea5e5bab567ecdc8d8683040203a48c87e3`へ進んだため、公開前に競合なく取り込み直した。レビュー済みの`.devcontainer/`・`.pi/`内容は不変で、最新main統合後も環境27/27、layout、スキルの全検証が成功した。mainから取り込んだ文書・スキル・ワールドの内容は独自変更していない。

active LSPの残るprimary2件は元HEADのreal-npm fixtureと同一の型推論指摘。共通parserの補助2warningは、JSON decoderの数値token callbackと外側のValueError捕捉を認識しないルールによるもの。変更した実装に新しいprimary errorはない。全ファイルLSP cleanとは報告しない。

未検証は実認証MCP/provider、live registry更新、Dev Container rebuild（#22担当）。成功と扱わない。所要時間・公開SHA・remote確認はPRの最終ステータスコメントに記録する。修正があったためpushまでとし、PRとIssueはopenのままにする。
