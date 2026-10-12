# usaturn/reso-workshop: Resonite のアイテムを作り、工房へ反映して管理するリポジトリ

## 管理・実行許可

- 文書管理: `usaturn/create-reso-world`（ブランチ `docs/reso-workshop`）
- コード対象: 新しく作る `usaturn/reso-workshop`（GitHub の非公開リポジトリ、未作成）。ローカルの作業場所は `/workspaces/reso-world/worlds/reso-workshop`。作成は利用者が今回の会話で依頼した
- 対象 Issue・PR: なし
- 規約上の位置付け: `worlds/` の下のワールドのプロジェクトとして扱い、create-reso-world の `AGENTS.md` の「プロジェクト運用」と、プロジェクトの `AGENTS.md` に従う。PR は使わないので、「リポジトリ境界」の表にある外部リポジトリの経路（PR のレビューと修正）は使わない
- 検証した基準: create-reso-world `4d518a963dfc2301d528c748e7387de04a7e1594`、ResoLoop `0.1.0-preview.17.fork`（`resoloop --help` と、`external/resoloop` の `84c7932` の文書）
- 状態: draft
- 関連 Plan: 未作成（この Spec の承認後に writing-plans で作る）
- 会話での決定（2026-10-12）: 依頼は「新しくリポジトリを作成してください。目的はレゾナイトのワールドというか、アイテムをデプロイして管理をする」。質問への回答で、管理する対象（複数のアイテム）、種類（動かない小物・家具、仕掛けのあるガジェット）、反映先（工房のワールド → インベントリ）、リポジトリ名と公開範囲（`usaturn/reso-workshop`、非公開）、最初の版の範囲（器だけ）、方式 A を選んだ。設計の 4 節（構成、デプロイの流れ、台帳と版、運用・安全・テスト・作る手順）はそれぞれ「これでよい」と承認された
- 実行許可: この Spec の承認で許可されるのは Plan の作成だけ。実装は Plan の承認と実行方法の選択の後に行う。GitHub へのリポジトリの作成と push は外部に出る操作なので、実装と検証が済んだあと、実行の直前に利用者へ確認してから行う

## 1. 目的

Resonite で使うアイテムを ResoLoop と Blender で作り、作業用のワールド（以下「工房」）へ反映して検査し、利用者がインベントリに保存するまでを、1 つのリポジトリで繰り返せるようにする。どのアイテムのどの版を、どのコミットから反映し、インベントリに保存したかを記録して管理する。

最初の版では「器」だけを作り、アイテムは入れない。

### 成功の条件

- `workshop new` で雛形からアイテムを作れる。`workshop deploy` 1 回で、工房への反映・検査・記録まで進む
- `workshop saved` でインベントリへの保存を記録できる。`workshop list` で全アイテムの状態が分かる
- 使い捨てのアイテムで、実機の工房に対して上の流れが最後まで通る
- GitHub の非公開リポジトリ `usaturn/reso-workshop` に、ローカルの `main` が push されている

## 2. ResoLoop で確かめた事実

### できること

- **反映**: マニフェストごとに所有キー（`ownership.key`）とルートスロットを持ち、state は所有キーごとに分かれる。`apply --prune --yes` で削除できるのは、state に記録した所有ルートの中だけ
- **検査**: `validate` は接続なしでスキーマ・値の形・キー・参照を検査する。`validate --strict` は実機への接続が必要。`diff` と `plan` は、内部で両方の検証を行う
- **差分**: `diff` の JSON の `changes` には、no-op 以外の変更が必ず入る
- **持ち出し検査**: `item audit SLOT --strict` は、アイテムのルートの外を参照していないかを検査し、参照していれば `ITEM_NOT_PORTABLE` を返す
- **タグ**: `Grabbable` などを持つルートに、`AI_GeneratedContent` が自動で付く
- **ProtoFlux**: `flux validate-manifest FILE.json` と `flux deploy-manifest FILE.json [--parent SLOT] [--state WORLD_STATE]` がある
- **セッション**: 対象のセッションは `--url` で選ぶ（`auto` と `--session` で選ぶこともできる）

### できないこと

- インベントリへの保存・インベントリからの呼び出し、クラウドのレコードの操作、パッケージ化、ワールドやアイテムを保存するコマンドは無い
- インベントリへの保存は、ワールドの保存と同じく、利用者が Resonite の中で手で行う
- `item audit` に合格しても、保存して読み込み直したあとに壊れないことの証明にはならない（同梱スキルの注意）

## 3. 決定事項

| ID | 決定 | 理由 |
| --- | --- | --- |
| D-1 | 管理するのは複数のアイテム。最初に想定する種類は、動かない小物・家具（Meshy で作る物を含む）と、仕掛けのあるガジェット | 利用者の回答 |
| D-2 | デプロイは「工房へ反映 → 検査 → 利用者がインベントリに保存」まで。既存のワールドへ直接は置かない | 利用者の回答。ResoLoop にはインベントリを操作する機能が無い |
| D-3 | リポジトリは `usaturn/reso-workshop`（非公開）。ローカルは `worlds/reso-workshop/` に置き、create-reso-world では追跡しない | 利用者の回答。#57 の方針（継続して管理したいプロジェクトは、利用者が明示して専用のリポジトリにする） |
| D-4 | アイテムごとに所有キー・マニフェスト・state を分ける（方式 A） | 1 つのアイテムの反映や削除が、ほかのアイテムに及ばない。工房全体で 1 つにする方式 B と、アイテムごとにリポジトリを作る方式 C は採らない |
| D-5 | 最初の版は器だけ（雛形・規約・台帳・CLI・テスト）。アイテムは入れない | 利用者の回答 |
| D-6 | Git LFS は使わない。50 MiB を超えるファイルは入れない。Meshy の原本は Git の外の `worlds/reso-workshop-meshy/` に置く | GitHub は 50 MiB で警告、100 MiB で拒否する。asakusa01（#92）と同じ扱い |
| D-7 | リポジトリの外を指す symlink（`.pi`・`.claude/settings.json`・`.agents/sp-*.md`）は追跡しない。clone したあとに `scripts/new-world.sh --apply reso-workshop` で作り直す | 追跡すると、`worlds/reso-workshop` 以外の場所に clone したときにリンクが切れる |
| D-8 | アイテムのルートスロットの名前は `<表示名> v<版>` にする | インベントリに保存したときの名前になり、どの版か見分けられる |
| D-9 | アイテムの定義（`item.toml`、手で編集する）と、反映・保存の記録（`deploys.toml`、CLI だけが書く）を別のファイルにする | 記録を書いただけで「未コミットの変更あり」と判定されないようにする |
| D-10 | コミットは `main` に直接行う。push は利用者の指示があるときだけ | 1 人で使うリポジトリ。外部に出る操作は指示を受けてから行う |
| D-11 | 工房からアイテムを取り下げる機能は、最初の版に入れない | 必要になってから足す |

## 4. リポジトリの構成

```
worlds/reso-workshop/            Git（origin は usaturn/reso-workshop、ブランチ main）
├── AGENTS.md / CLAUDE.md        new-world.sh の雛形に、工房の規約（8 章）を足す
├── .gitignore
├── .resoloop.json  pyproject.toml  uv.lock
├── .agents/skills/resonite-*    ResoLoop 同梱スキル
├── .claude/skills/<name>        同梱スキルへの symlink（リポジトリの中で閉じる）
├── templates/item/              新しいアイテムの雛形（prop と gadget の共通部分、gadget だけの flux/）
├── items/<名前>/                アイテム 1 つ分（最初の版では空）
│   ├── item.toml                アイテムの定義
│   ├── deploys.toml             反映と保存の記録
│   ├── manifest.json            ResoLoop のマニフェスト（CLI が決める項目は書かない）
│   ├── flux/                    gadget だけ。ProtoFlux のマニフェストとソース
│   ├── build.py                 Blender で形を作るアイテムだけ
│   └── tests/
├── tools/workshop.py            CLI（大きくなる場合は、Plan で同じ場所のパッケージに分けてよい）
└── tests/                       CLI のテスト
```

### Git に入れないもの（`.gitignore`）

- `build/`（ビルドの出力）、`items/*/manifest.rendered.json`（CLI が作るマニフェスト）
- `.resoloop/`（state・キャッシュ・Blender のラッパー）、`artifacts/`（撮影・ログ）
- `.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`
- `.pi`、`.claude/settings.json`、`.agents/sp-*.md`（D-7）

`resoloop init` が作る `content/main.json` と、プロジェクト直下の `flux/` は工房では使わないので消す。アイテムのマニフェストと ProtoFlux は `items/<名前>/` に置く。

### clone したあとの手順

1. `worlds/reso-workshop` に clone する（`.resoloop.json` の `blenderExecutable` は絶対パスなので、この場所に固定する）
2. `scripts/new-world.sh --apply reso-workshop` で、外を指す symlink と `.resoloop/` のラッパーを補う
3. `uv sync` を実行する

2 の手順が、`content/`・`flux/` の無いプロジェクトでも失敗しないことを Plan で確かめる。

## 5. アイテムの定義と記録

### 名前

アイテムの名前はディレクトリ名で、`^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` に合う 40 文字以内の文字列とする。所有キーは `workshop-<名前>` になる。

### `item.toml`

```toml
display_name = "Desk Lamp"   # 空でない文字列
kind = "gadget"              # "prop" または "gadget"
version = "1.2.0"            # X.Y.Z（それぞれ 0 以上の整数）
shelf = 3                    # 1 以上の整数。工房の中の区画。ほかのアイテムと重ならない
```

上の 4 項目以外は書かない（`check` が誤りとする）。

### 区画の位置

区画 n の位置は、ワールドの原点を基準に次のとおりとする（単位はメートル、8 区画で 1 列）。

- X = ((n − 1) mod 8) × 1.5
- Y = 1.0
- Z = 2.0 + floor((n − 1) / 8) × 1.5

### `manifest.json` と `manifest.rendered.json`

`manifest.json` は ResoLoop のスキーマ v1 のマニフェストで、手で書くか、`build.py` の出力を include する。次の項目は CLI が決めるので書かない（書いてあれば `check` が誤りとする）。

- `ownership`
- `slot.key`、`slot.name`、`slot.parent`、`slot.position`

CLI は反映の前に、同じディレクトリへ `manifest.rendered.json` を作る。同じディレクトリに置くのは、マニフェストの中の相対パスの基準を変えないため。作るときに次の値を入れる。

- `ownership.key` = `workshop-<名前>`
- `slot.key` = `root`
- `slot.name` = `<display_name> v<version>`
- `slot.parent` = `Root`
- `slot.position` = 区画の位置

### `deploys.toml`

CLI だけが書く。反映のたびに 1 件を末尾に足す。

```toml
[[deploy]]
version = "1.2.0"
commit = "<40 桁の SHA。コミットが無いときは空文字>"
dirty = false
deployed_at = "2026-10-12T21:00:00+09:00"
session = "ws://localhost:49691/"
result = "passed"            # "passed" または "failed"
failed_step = ""             # result が failed のときに、失敗した段階の名前
saved_at = ""                # workshop saved で入る
```

### state

- ワールドの state: `.resoloop/state/workshop-<名前>.json`
- ProtoFlux の配置の state: `.resoloop/flux-state/workshop-<名前>.json`

gadget の `flux/resoloop.flux.json` は、`parent` を `$slot:root` にして、上の 2 つの state を相対パスで指す。値は `workshop new` が入れる。

## 6. CLI

`uv run workshop <サブコマンド>` で呼ぶ。終了コードは、0 が成功、1 が検査や手順の失敗、2 が使い方の誤り。CLI はコミットも push もしない。

| サブコマンド | 動作 |
| --- | --- |
| `new <名前> --kind prop\|gadget --display-name <表示名>` | `templates/item/` から `items/<名前>/` を作る。版は `0.1.0`、区画は使われていない最小の番号、`deploys.toml` は空。gadget には `flux/` も作る。名前が規則に合わない、または既にあるときは何も作らずに 2 で終える |
| `list` | 全アイテムの名前・種類・版・状態・最後に保存した日時を表示する。状態は、記録が無ければ「未反映」、最後の記録が `failed` なら「反映失敗」、`passed` で未保存なら「保存待ち」、保存済みなら「保存済み」 |
| `check [<名前>...]` | 指定したアイテム（省略時は全部）の `item.toml`・`manifest.json`・`deploys.toml` を 5 章の規則で検査する。区画の重なり、gadget の `flux/resoloop.flux.json` の有無、リポジトリ内の 50 MiB を超えるファイル（追跡しているものと、無視されていない未追跡のもの）も検査する。誤りはすべて表示してから 1 で終える |
| `deploy <名前> --url <URL> [--prune]` | 7 章の流れを実行する |
| `saved <名前>` | 最後の記録に `saved_at` を入れる。条件は下のとおり |

### `saved` の条件

次のどれかに当たるときは、記録せずに理由を表示して 1 で終える。

- 記録が無い。または最後の記録の `result` が `failed`、`dirty` が true、`saved_at` が入っている
- ほかの記録が同じ版で保存済みで、その `commit` が最後の記録と違う（版を上げるよう案内する）

インベントリにある物とコミットを 1 対 1 に対応させるための条件である。

## 7. デプロイの流れ

`deploy` は次の順に実行し、失敗したらその段階で止める。

1. **準備（オフライン）**
   - そのアイテムを `check` で検査する
   - `items/<名前>/tests/` があれば pytest を実行する
   - `build.py` があれば `uv run python items/<名前>/build.py --out build/<名前>` を実行する。Blender の呼び出しは `build.py` が `.resoloop/blender-system-python` を使って行う
   - `manifest.rendered.json` を作り、`resoloop validate` を実行する
   - gadget では `resoloop flux validate-manifest` も実行する
2. **差分の確認**
   - `resoloop diff` を実行し、要約を表示する
   - 削除が含まれていて `--prune` が無ければ、削除の一覧を表示して止める
3. **反映**
   - `resoloop apply` を実行する。`--prune` のときは `--prune --yes` を付ける
   - gadget では `resoloop flux deploy-manifest` も実行する
4. **実機での検査**
   - `resoloop test` を実行する
   - `resoloop item audit '$slot:root' --strict` を実行する
   - もう一度 `resoloop diff` を実行し、`changes` が空であることを確かめる
5. **記録**: `deploys.toml` に 1 件を足す

追加の決まり:

- **未コミットの判定**: 始める前に行う。`items/*/deploys.toml` を除いて、`git status --porcelain` に何か出れば `dirty` を true にする（無視されていない未追跡のファイルも含む）。コミットが 1 つも無いときは、`commit` を空文字、`dirty` を true にする
- **失敗したときの記録**
  - 1・2 で失敗したときは、工房を変えていないので記録しない
  - 3・4 で失敗したときは、`result = "failed"` と `failed_step` を記録してから 1 で終える
- **呼び出し方**: resoloop の各コマンドには、`--url` と、5 章の state のパスを渡す

## 8. 工房の規約（`worlds/reso-workshop/AGENTS.md` に足す）

- アイテムの作業は `worlds/reso-workshop` を cwd にして行う。テストは `uv run pytest` で実行する
- アイテムを足すときは `uv run workshop new` を使う。`items/` を手で複製しない
- 工房への反映は `uv run workshop deploy` だけで行う。resoloop の `apply` を直接実行しない
- 削除（`--prune`）は、`diff` で削除の内容を利用者に見せてから実行する
- Resonite は、接続が必要になる直前に起動を頼む。ポートは毎回変わるので、その都度確認する
- インベントリへの保存は利用者が行う。保存したと聞いてから `uv run workshop saved` を実行する
- Meshy の有料の操作は、操作ごとに承認をもらう。原本は `worlds/reso-workshop-meshy/` に置く
- コミットは `main` に直接行う。push は利用者の指示があるときだけ行う
- `git clean` は使わない
- Spec・Plan は create-reso-world の `docs/superpowers/` に置く（create-reso-world の `AGENTS.md` の規則のとおり）

## 9. テスト

create-reso-world の「テストの採用基準」に従う。CLI の挙動を実行して確かめるテストだけを書き、文書の文言を照合するテストは書かない。

- `item.toml`・`manifest.json`・`deploys.toml` の検査（正しい例と、誤りの例）
- 区画の割り当てと位置の計算
- `manifest.rendered.json` に入る値
- `saved` の条件（5 つの拒否の場合と、受け付ける場合）
- 未コミットの判定。一時ディレクトリに実際の git リポジトリを作り、`deploys.toml` だけの変更・ほかのファイルの変更・未追跡のファイル・コミットが無い場合を確かめる
- `deploy` の手順の順序、失敗したときに止まること、記録するかどうか。`resoloop` を、呼ばれた引数を書き残す偽のコマンドに差し替えて確かめる
- 50 MiB を超えるファイルの検出

## 10. 検証と完了の条件

1. `worlds/reso-workshop` で `uv run pytest` が合格する
2. `uv run workshop new` で使い捨てのアイテム（箱 1 つの prop）を作り、`check` と `list` が期待どおりに動く
3. 利用者に Resonite の起動とポートを確かめてから、使い捨てのアイテムで `deploy` を実機の工房に対して最後まで実行し、記録が `passed` になる。続けて同じアイテムを `deploy` し、反映後の差分が 0 件であることを確かめる
4. 使い捨てのアイテムは、工房のセッションから利用者に手で消してもらう。リポジトリにはコミットせず、`items/<名前>/`・`build/<名前>/`・`.resoloop/` の中のそのアイテムの state も消す
5. `git status` がクリーンで、50 MiB を超えるファイルが無く、秘密の形（`msy_`・`sk-`・`ghp_`・`github_pat_`・AWS のキー・秘密鍵）が見つからない
6. 利用者の確認を得てから、`gh repo create usaturn/reso-workshop --private` でリポジトリを作り、`main` を push する
7. この Spec と Plan を completed にし、結果と検証の根拠を書く

## 11. 範囲外

- アバター、既存のワールドへの直接の配置（D-2）
- 工房からの取り下げ（D-11）、`tool audit` による道具の検査
- インベントリへの保存の自動化（ResoLoop に機能が無い）
- Git LFS（D-6）、公開リポジトリにすること
- GitHub Actions の CI
- create-reso-world の雛形・スクリプトの変更（必要だと分かったら、別の Issue にする）
- 見本のアイテム（D-5）

## 12. Plan で確かめて決めること

- `scripts/new-world.sh --apply reso-workshop` が、`content/`・`flux/` を消したプロジェクトと、外を指す symlink の無い clone で使えるか。使えない場合は、clone したあとの手順を工房の README に書く方法に切り替える（create-reso-world は変えない）
- resoloop の `diff`・`test`・`item audit` の JSON 出力の形（合否の読み取り方）と、`--url` の渡し方
- `deploys.toml` の書き込みに使う依存（`tomlkit` など）
- gadget の雛形に入れる `.pg` の中身
