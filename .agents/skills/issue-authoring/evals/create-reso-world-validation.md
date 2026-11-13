# create-reso-world の 3 モード評価

## 対象と手順

移植元は `usaturn/agent-workspace` commit `6e71fae4d25f217b23ce2409517cf602437a3cbf`。同ディレクトリの既存の評価文書・シナリオ・probe は移植元の履歴であり、移植元の fixture・パス・環境を前提とする。今回の実績やこのリポジトリでそのまま実行する手順ではない。

controller が同一の固定 fixture と fake GitHub CLI で、非対話の依頼を 3 モードまとめてスキル無し・あり各 1 回評価する。実 GitHub 書込みは禁止。新規案は日本語複数行、整形は元本文・管理対象・差分、評価は実測 1 件と未計測 1 件を扱う。入力と出力のディレクトリを分け、実 helper の保存物・preview・verify・承認待ち・fake 書込み 0 件を照合する。評価不能な結果は `achieved=null` とし、actual と gap に理由を残す。Gitleaks は `.devcontainer/install_gitleaks.bash` の指定版を確認する。

## スキル無し（controller の観測）

- model `gpt-6.1-terra`、provider `openai-codex`、effort `xhigh`、session `01a1d49b-c064-7448-9506-6b2dd3b04b38`、所要 200.551 秒。CLI version は未観測。
- 3 件とも案を保存。各 SHA-256 は対応する `draft.json` の値。`author-draft` SHA-256 `635b2fdcaaa5efc560177c58c02d3ed925d66a2427b9284ee98c09085632d530`、`reshape-draft` `1303d221e38ffbf4459d9e52d64309c225ceb0752aba447092223875ac39a69d`、`evaluation-draft` `186da4b4c206a53918dd8845f2fda1e56aaf85787ceb2e3281df424a26c52d64`。
- 元本文と管理対象の保持を確認。評価は平均 2 分を達成、記録の無い項目は理由付き `achieved=null`。fake GitHub 書込みは 0 件。
- 初回 create draft は出力ディレクトリが存在せず失敗し、作成後に回復。既存コメントは取得せず、関連 Issue の検索も行わなかった。
- preview はそれぞれ `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/without-skill/{author-draft,reshape-draft,evaluation-draft}/preview.md`。このパスは今回の controller のセッション資料で、将来の実行手順ではない。

## スキルあり（controller の観測）

- 評価時 HEAD `5d8fc3bcf4b6dc776a42ae015d3f252ee06da43c`。model `gpt-6.1-terra`、provider `openai-codex`、effort `xhigh`、session `01a1d4a5-7010-77cb-a44d-3eb0e20c4c7f`、所要 221.415 秒。CLI version は未観測。
- 同じ fixture の新規案・整形・評価の 3 モードで案を保存し、承認待ちで公開していない。各 `draft.json` の絶対パスと SHA-256 は次のとおり。各ディレクトリの `preview.md` も保存した。
  - 新規案: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/with-skill/run.2p3R2j/create/draft.json` — `50258cc3d968d8d4560f239a03b909a9529660a219602a83389bc5544e4b0d80`
  - 整形: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/with-skill/run.2p3R2j/update/draft.json` — `69d36636963b54d0936aed92e17ae3d9ad80066a6c48c910589a9a8bf5577a5a`
  - 評価: `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/with-skill/run.2p3R2j/comment/draft.json` — `24d849fc5c5336f3d98ee73ee1045f9bb08fcf2132a792af196ae6f4c8f5a4d0`
- 整形の verify は成功し、CRLF を含む元本文と管理対象の保持を確認。差分と保持検査の結果は `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/with-skill/run.2p3R2j/verify/diff.patch` と `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/with-skill/run.2p3R2j/verify/preservation.json`。fixture 入力も変更されなかった。
- 評価では作業時間の実測 3 件（2、3、1 分）の平均 2 分を `achieved=true`、未回収の転記ミス記録を理由付き `achieved=null` とした。fake GitHub 書込みは 0 件。実 CLI の draft で Gitleaks 8.30.1 を使用した。

## 比較と照合範囲

両条件とも 3 案を保存し、原文・管理対象を保持、未計測値を `null` とした。スキルありは既存コメントを取得し関連 Issue を検索したが、スキル無しはどちらも行わなかった。スキル無しで起きた初回の出力ディレクトリ不在による失敗は、スキルありでは観測されなかった。これは単一モデルによる各 1 回の観測であり、一般の成功率を示すものではない。

A1–A4 と A6 は controller が実 helper と既存 15 テストで照合済み。A5 の全体 pytest と最終公開は未実施であり、移植全体の完了を示すものではない。観測記録は `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-with-observed.json`、`/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-without-observed.json`、詳細報告は `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-with-report.json`。これらと保存物は今回の controller のセッション資料であり、将来の実行手順ではない。
