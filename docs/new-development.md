# 新規開発の入口

このリポジトリで新しく開発を始めるときに、最初に読む文書。開発の種類ごとに、手順の文書へ案内する。

このリポジトリが対象にするのは、Resonite 向けのワールド・ツールの作成、Blender などを使ったモデルの作成、VR 環境に関するツールやモデルの開発である。どれも基本的に Resonite が関与する（例: Resonite 側からツールやモデルを取り込んで変換する）。

作業場所、Spec・Plan の置き場所、push の前の検査などの共通の決まりは、ルートの [AGENTS.md](../AGENTS.md) にある。

## ワールド・モデル

Resonite のワールドと、Blender などで作るモデル（ResoLoop のプロジェクト）を新しく作る。手順は [#323](https://github.com/usaturn/create-reso-world/issues/323) で準備中。

## ツール

Resonite 内のツール（装備ツール・操作 UI・ProtoFlux）と、Resonite と連携する外部ツール（独立したリポジトリ）を新しく作る。手順は [#324](https://github.com/usaturn/create-reso-world/issues/324) で準備中。

## ResoLoop プラグイン

ResoLoop のプラグインのリポジトリを新しく作る。準備中: プラグイン機構が上流にマージされ（[#105](https://github.com/usaturn/create-reso-world/issues/105)）、公開版の ResoLoop で使えるようになってから、[#328](https://github.com/usaturn/create-reso-world/issues/328) で手順をまとめる。

## そのほかの開発

新規開発の手順の対象ではないが、既に手順がある開発。

- ResoLoop 本体とプラグイン機構: [resoloop-fork-workflow.md](resoloop-fork-workflow.md)（fork の usaturn/resoloop の運用）と、[#95](https://github.com/usaturn/create-reso-world/issues/95) のボード
- 既存の Meshy プラグイン（usaturn/resoloop-meshy）: [resoloop-meshy-workflow.md](resoloop-meshy-workflow.md)
- Meshy で作る素材: [meshy-resoloop.md](meshy-resoloop.md)
- 登録済みの外部ツールの運用: [external-tools-workflow.md](external-tools-workflow.md)
