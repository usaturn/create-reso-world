# Dev Container による Resonite 開発ツールのセットアップ

## 目的と対象範囲

Ubuntu 26.04 の Dev Container を作成すると、ResoLoop と Blender を用いた Resonite ワールド開発に必要なコマンドラインツールが揃うようにする。開発者とコーディングエージェントが .NET 10 SDK、プレビュー版を含む最新版の ResoLoop、GUI を使わずに実行できる Blender を利用できる状態を目指す。

今回は第1段階として、コンテナ内の開発ツールだけを対象とする。Resonite 本体と ResoniteLink は Windows ホスト側に置き、その設定は別途行う。

セットアップ成功の判定条件は、コンテナ内で .NET 10 SDK が確認でき、`resoloop --version` が実行でき、Blender が画面表示なしで簡単なスクリプトを実行できることとする。ResoLoop が Resonite に接続できることや、Blender の GUI が起動できることは今回の判定条件に含めない。

## 既存構成との接点

- `.devcontainer/devcontainer.json` は `mcr.microsoft.com/devcontainers/base:ubuntu26.04` をベースにしており、Dev Container Feature の導入後、`postCreateCommand` で `.devcontainer/install_beforehand.bash` を実行する。
- 既存のインストールスクリプトは apt の更新と基本パッケージの導入を行い、番号付きの進捗表示と `fail` による必須処理の中断を採用している。手順を増やす場合は進捗表示の総数も更新する。
- `.devcontainer/zshrc.txt` はセットアップ中にユーザーの zsh 設定へ追記される。ただし、セットアップ中の bash やエージェントが起動するプロセスは、その設定を読み込むとは限らない。

## 構成とセットアップの流れ

1. `.devcontainer/devcontainer.json` に公式の .NET Dev Container Feature（`ghcr.io/devcontainers/features/dotnet:2`）を追加し、.NET 10 SDK を導入する。既存の Node と GitHub CLI の Feature は維持する。Feature の導入は `postCreateCommand` より前に行われる。
2. 既存の apt によるパッケージ導入へ Ubuntu の `blender` を追加する。デスクトップ環境、画面転送、GUI 用のホストマウントは追加しない。
3. ResoLoop の導入処理を独立してテストできる小さなスクリプトに分け、前提ツールを利用できるようになった後で `.devcontainer/install_beforehand.bash` から呼び出す。初回はグローバル .NET ツールとしてインストールし、再実行時は更新する。どちらも `--prerelease` を付け、`--version` は指定しない。これによりプレビュー版を含む利用可能な最新版を対象とし、現在公開中のプレビュー版に固定しない。
4. セットアップ実行中のシェルから ResoLoop を呼べるようにし、通常の開発者用シェルとエージェントにも、Linux のグローバル .NET ツール配置先（`$HOME/.dotnet/tools`）への PATH を通す。セットアップ用シェルの一時的な PATH 設定だけには依存しない。
5. ResoLoop の導入とツールの実行確認は、それぞれ進捗が分かる必須手順にする。番号付き手順の総数を合わせ、既存の「必須処理は失敗時に中断し、作業領域の掃除だけは失敗しても続行する」方針を維持する。

ResoLoop の公開手順には Windows 10/11 が必要環境として記載されており、Linux 対応は保証されていない。.NET 10 のグローバルツールとしてインストールできた場合でも、Ubuntu 上で CLI が実行できるとは限らない。この設計ではコンテナ内で確認できる範囲を実際に検証し、Windows と同等の動作やホスト側の Resonite 設定までは保証しない。

## 失敗時の扱いとバージョン更新

- .NET 10 が見つからない、ResoLoop の取得・更新に失敗する、またはインストール後の CLI が起動できない場合は、該当手順が分かるエラーを表示してセットアップを失敗として終了する。必須ツールを任意扱いにしたり、ホストへの導入だけで成功扱いにしたりしない。
- Blender を apt で導入できない場合や、画面表示なしで実行できない場合は、Blender の問題だと分かるエラーを表示して終了する。
- コンテナを新しく作成するたびに、プレビュー版を含む新しい ResoLoop が導入される可能性がある。更新による不具合は隠さず、進捗ログと CLI のバージョンから調査できるようにする。この変更では ResoLoop のバージョンを固定せず、ロックファイルにも記録しない。
- `resoloop doctor` は今回の必須検証から外す。ホスト側で Resonite と ResoniteLink を設定し、ワールドを起動する必要があり、コンテナ内のツール導入の成否とは別だからである。

## 検証

- 既存の `.devcontainer/test-*.bash` に合わせたシェルテストを追加する。必要に応じて `dotnet` と `resoloop` を差し替え、初回導入、再実行時の更新、バージョン固定なしの `--prerelease` 指定、CLI の実行失敗、PATH の設定を確認する。
- 変更したシェルスクリプトと `devcontainer.json` の構文を確認し、Resonite を起動せずに新しいセットアップ処理をテストする。
- Dev Container の再作成が可能な環境では、`dotnet --list-sdks` に .NET 10 が含まれること、通常の開発者用シェルから `resoloop --version` が成功すること、Blender が GUI なしで簡単な処理を実行できることを確認する。再作成できない場合や Linux 上で ResoLoop が動かない場合は、未確認・失敗した項目を明記し、検証済みとは扱わない。
- 現在のリポジトリには `scripts/ci/verify-devenv.sh` がない。そのスクリプトを実行したとは報告せず、実在する関連テストと実環境での確認結果を報告する。

## 今回は扱わないこと

Resonite 本体のコンテナ内インストール、ResoniteLink やホスト側ネットワークの設定、`RESONITE_LINK_URL` の設定、GUI の画面転送、Blender のアドオン導入、Resonite ワールド用プロジェクトの作成は対象外とする。これらはコンテナ内の開発ツールが利用できるようになってから別途検討する。
