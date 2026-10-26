# Dev Container のテクスチャ転送を data に切り替える設計

## 管理と実行許可

- 文書管理・対象: `usaturn/create-reso-world`、Issue #277
- 状態: `draft`（実行許可であり、内容の承認ではない）
- 利用者の指示: `issue-to-pr #277 --merge --max-cycles 3`
- 許可: 通常の設計判断を推奨案で決め、検証・commit・push・PR 作成後、最大 3 サイクルの PR 修正ループを実行する。マージはループの `finalize.py` のみ。
- 調査した基準: `origin/main` = `5b2c535d4da20387958b66f0ab71d361b039f5cc`
- 関連: [Issue #277 の owner コメント](https://github.com/usaturn/create-reso-world/issues/277#issuecomment-6415325364)、[usaturn/resoloop#22](https://github.com/usaturn/resoloop/pull/22)（マージ済み）
- create-reso-world#278 は resoloop#21 の文書専用 PR。本変更とは別テーマであり、編集・マージしない。

## 意図と原因

Windows の Resonite はコンテナの `/workspaces/...` を開けない。現在の `initialize.bash` は WSL で `RESOLOOP_HOST_PATH_MAP` を生成するが、その機能は現行の上流公開版に無く、fork も上流へ合わせ直したため、パス変換の案内は現状と一致しない。

fork の resoloop#22 は `textureTransfer=data` で画像を CLI 側で復号し、画素を送る経路を実装・実機検証している。#277 の残作業は、この経路をコンテナの設定と案内に反映すること。ワールドや ResoLoop 本体を変更する作業ではない。

## 条件と除外範囲

1. `initialize.bash` は WSL の有無・checkout の場所によらず、生成する `.devcontainer/resonite-screenshots.env` に `RESOLOOP_TEXTURE_TRANSFER=data` を書く。`RESOLOOP_HOST_PATH_MAP` の生成と UNC パス計算は削除する。
2. 同ファイルは従来どおり毎回作り直す。前回の自動生成値は残さず、写真フォルダのリンクがあるときの `RESOLOOP_SCREENSHOTS_DIR` は維持する。
3. mount の一覧・env-file の場所・権限・写真リンクの検証、利用者所有の `~/.config/create-reso-world/env` は変えない。生成 env の実物やワールドは編集しない。
4. README は生成→`--env-file`→rebuild の流れ、CLI > 環境変数 > プロジェクト設定 > ユーザー設定の優先順位、`--texture-transfer file` による明示指定を説明する。
5. 公開版の自動導入・版固定なしの方針は変えない。機能が公開版に入るまでは rebuild 後に `bash scripts/resoloop-fork.sh install origin/main` が必要で、次の rebuild・公開版の再導入で戻ることを明記する。環境変数の存在だけで公開版が対応したと判断しない。`resoloop apply --help` の `--texture-transfer` で対応を確認する。
6. `data` は audio の転送を変えない。WebP/HDR は非対応で、16 bit PNG は 8 bit になることを短く案内し、fork の `docs/TEXTURE-TRANSFER.md` に詳細をリンクする。
7. 実機の apply・rebuild は本変更では実行しない。既存の実機検証は fork PR #22 の記録として参照し、本変更で再検証したと報告しない。反映確認はマージ後の利用者作業として残し、PR は `Refs #277` とする。

## 検討した案と決定記録

| ID | 選択した案 | 検討した別案 | 理由・委任範囲 |
| --- | --- | --- | --- |
| D1 | コンテナで常に `data` を生成 | WSL のときだけ生成、旧パス変換を継続 | コンテナと Resonite の境界が原因で、WSL 判定や `/mnt` の例外は不要。通常判断の委任により選択。CLI の明示指定で `file` に戻せる。 |
| D2 | installer は公開版のまま、fork は明示導入 | 自動的に fork を導入、版を固定 | AGENTS.md の公開最新版の方針を守り、環境設定と fork の導入を混同しない。 |
| D3 | 生成ファイルの再生成で移行 | 利用者の env を自動編集 | 利用者所有部分を守る。手動で足した古い設定は必要に応じ利用者が削除する。 |
| D4 | 1 Task に実装・案内・一時検証をまとめる | ファイル別の並列実装 | 数行の設定変更とそれを説明する文書で、独立に出せる機能ではない。SDD の新規担当と Task/branch レビューで実行する。 |
| D5 | 新規の常設テストなし | env の文字列・文書の固定値テストを追加 | 設定の欠落は apply の明示エラーになる L、文言は F。既存の S/F∩S のテストを保持し、一時的な動作確認を行う。 |
| D6 | PR 修正ループを最大 3 回 | PR 作成だけで終了 | 利用者が `--merge --max-cycles 3` を明示。安全上の停止条件や予算超過は継続の例外。 |

### 解決した割り当て

`check-options` の既定適用: review.inspect = `claude-opus, devin-swe, pi-deepseek`、fix.implement = `claude-opus`、self-review / fix-check = `self`。fallback は全て空。max_cycles = 3 は利用者指定、assign は未指定、template は `.devcontainer/agent-runner.toml`、ループ config は未指定。

`implement_task.py check`: assignment.agents = `[self]`、fallback = `[]`、self = true。これは設定の既定適用であり利用者のモデル指定ではない。ランタイムの `useSubagents=true` に従い、Task 実装を `sp-implementer` に委譲する。

## 検証と残る確認

一時 HOME にコピーした initializer を使い、WSL 有無・古い生成値・写真リンク有無と再実行を確認する。利用者所有 env の sentinel を保持する。常設テストは増やさない。構文検査、既存 initializer/README テスト、README のルート向け全検証 3 コマンド、差分確認を行う。

マージ後はホストから rebuild し、コンテナで `RESOLOOP_TEXTURE_TRANSFER=data` と対応 CLI のヘルプを確認する。公開版未対応なら fork を導入する。実ワールドへの新規画像の apply と diff は、そのワールドを cwd にして利用者が行う。本 run では追跡外ワールドを触らない。
