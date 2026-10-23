# Issue #248: flux-sdk の扱いを「必要に応じて導入する」に改める Design

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/248
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/248 --merge`。PR の作成後に PR 修正ループを回し、修正不要なら `finalize.py` がマージする。内容の承認（approved）ではない
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-248-flux-sdk-readme`（branch `docs/issue-248-flux-sdk-readme`、基準 `origin/main` の `7cf6071`）
- ループ・担当の設定: ループは既定（サイクルの上限 3、レビュアー・担当は雛形のとおり。利用者の指定なし）。Plan の実装は `self`（雛形の既定。利用者の指定なし）

## 目的と範囲

`.devcontainer/README.md` の「ProtoFlux 用の flux-sdk はこの環境の対象外で、導入しない。」を、必要になったときの導入手順と確認方法が分かる記述に改める。既定のセットアップで自動導入しない点は変えない。

変えるのは次の 3 か所だけ。

- `.devcontainer/README.md`: 導入手順の節を足し、断定の 1 行を置き換える
- `README.md` の「対象外」: 「flux-sdk の導入」を外す
- `docs/resoloop-fork-workflow.md` の「対象外」: flux-sdk の 1 文を、導入手順の参照に置き換える

対象外: コンテナ作成時の自動導入、CI、ワールド側の ProtoFlux 実装、完了済みの Spec・Plan（履歴として書き換えない）。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 導入の方法 | 文書だけにする | `.devcontainer/install_flux_sdk.bash` を足す | 導入は `dotnet tool install` の 1 行で、成否は Resonite の managed data（ホスト側）に左右される。スクリプトにしても、コンテナ内では成功を確かめられない。`initialize.bash`・mount のテストとの関係も増える | 推奨案で進める |
| 版 | 固定しない。`resoloop flux status`・`resoloop doctor` が案内する版に合わせる（2026-10-24 時点は 1.9.0）と書く | README に 1.9.0 を固定する | 案内する版は ResoLoop の更新で変わる。README に固定すると、またずれる。Resonite の版との組み合わせで互換が変わるので、未検証の組は `resoloop doctor` の警告に従うと書く | 推奨案で進める |
| ルート README・fork 運用の「対象外」 | 同じ回で直す | 別 Issue にする | 古い断定が残らないことが受け入れ基準で、直す文は 1 文ずつ。別 Issue にすると不一致の期間が残る | 推奨案で進める |
| 実機での確認 | PR では行わない。未確認と書く | 導入して確かめる | この環境には Resonite の managed data が無い。Issue の検証欄も、導入手順を書いた人が確かめ、Issue に記録するとしている | 確認できなかったことを PR・最終報告に書く |

## 書く内容（`.devcontainer/README.md`）

1. 既定のセットアップ（postCreate）では flux-sdk を導入しない。ProtoFlux を使うときだけ導入する
2. 導入: `dotnet tool install --global Papaltine.FluxSDK --version <resoloop が案内する版>`。更新は `dotnet tool update --global Papaltine.FluxSDK --version <版>`
3. 前提: Resonite 本体の managed data をコンテナから読めること（ホストの Resonite は Windows 側にあり、既定のコンテナには mount されない）。`RESONITE_MANAGED_DATA_PATH` で場所を指定する。実行ファイル名・場所が違うときは `RESOLOOP_FLUX_EXECUTABLE`
4. 確認: `resoloop flux status` が成功すること。`resoloop doctor` の `flux-sdk`・`resonite-managed-data` が warning でなくなること
5. 参照: ワールド側の使い方は `resonite-flux` スキル

## 検証

文書の変更なので、テストは足さない（採用基準の F）。次で代える。

- `rg -n "flux-sdk" .devcontainer/README.md README.md docs/resoloop-fork-workflow.md` で、新しい記述だけが出ること
- `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`
- `git diff` で、変更が上の 3 か所と Spec・Plan だけであること
