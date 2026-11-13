# create-reso-world の 3 モード評価

## 対象と手順

移植元は `usaturn/agent-workspace` commit `6e71fae4d25f217b23ce2409517cf602437a3cbf`。同ディレクトリの既存の評価文書・シナリオ・probe は移植元の履歴であり、移植元の fixture・パス・環境を前提とする。今回の実績やこのリポジトリでそのまま実行する手順ではない。

controller が同一の固定 fixture と fake GitHub CLI で、非対話の依頼を 3 モードまとめてスキル無し・あり各 1 回評価する。実 GitHub 書込みは禁止。新規案は日本語複数行、整形は元本文・管理対象・差分、評価は実測 1 件と未計測 1 件を扱う。入力と出力のディレクトリを分け、実 helper の保存物・preview・verify・承認待ち・fake 書込み 0 件を照合する。評価不能な結果は `achieved=null` とし、actual と gap に理由を残す。Gitleaks は `.devcontainer/install_gitleaks.bash` の指定版を確認する。

## スキル無し（controller の観測）

- model `gpt-6.1-terra`、provider `openai-codex`、effort `xhigh`、session `01a1d49b-c064-7448-9506-6b2dd3b04b38`、所要 200.551 秒。CLI version は未観測。
- 3 件とも案を保存。`author-draft` SHA-256 `635b2fdcaaa5efc560177c58c02d3ed925d66a2427b9284ee98c09085632d530`、`reshape-draft` `1303d221e38ffbf4459d9e52d64309c225ceb0752aba447092223875ac39a69d`、`evaluation-draft` `186da4b4c206a53918dd8845f2fda1e56aaf85787ceb2e3281df424a26c52d64`。
- 元本文と管理対象の保持を確認。評価は平均 2 分を達成、記録の無い項目は理由付き `achieved=null`。fake GitHub 書込みは 0 件。
- 初回 create draft は出力ディレクトリが存在せず失敗し、作成後に回復。既存コメントは取得せず、関連 Issue の検索も行わなかった。
- preview はそれぞれ `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/behavior-eval/without-skill/{author-draft,reshape-draft,evaluation-draft}/preview.md`。このパスは今回の controller のセッション資料で、将来の実行手順ではない。

## 未実施

スキルありの行動評価、スキル無しとの比較、および A1–A6 の実 helper・fake GitHub を使った統合照合は controller が実施予定。結果はまだない。上記の観測をもって今回の移植全体の成功とはしない。
