# Gazebo Sim on macOS (Apple Silicon) — pixi 環境

conda-forge の Gazebo を pixi で動かす環境。Homebrew (`osrf/simulation` tap) は不要。

以下のコマンドはすべて **`~/codex/gazebo` をカレントディレクトリとして** 実行する想定で記載しています。適宜変更ください。

```bash
cd ~/codex/gazebo
```

## 動作確認済み（2026-09-18 実測）

| 項目 | 結果 |
|---|---|
| ホスト | macOS 26.5 / Apple Silicon (arm64) / pixi 0.67.0 |
| Gazebo | gz-sim **10.5.0** (Jetty), osx-arm64 ネイティブ |
| 環境サイズ | 1.8 GB / `pixi install` 約 6〜13 秒 |
| 物理エンジン | DART (`gz-physics-dartsim-plugin`), RTF **0.997** |
| GUI | Qt6 + **Metal** バックエンド、影・Entity Tree 正常 (RTF 99.94%) |
| カメラセンサー | オフスクリーン描画 OK、800x600 PNG 出力を確認 |
| 一発起動 | `gz sim -r world.sdf` でサーバー+GUI 同時起動が動く |

最後の項目は重要で、「macOS では `-s` と `-g` を別プロセスで起動しないといけない」という
従来の既知制約は Jetty + conda-forge ビルドでは解消されている。

## セットアップ

環境は構築済み。別マシンで再現する場合も `pixi.toml` と `pixi.lock` だけあればよい（7 節参照）:

```bash
pixi install --locked    # lockfile どおりに再現（--locked で toml との整合も検証される）
```

`.pixi/` は 1.8 GB あるが、lockfile から 6 秒で再構築できるので配布物に含める必要はない
（別マシンへの持ち出しは 7 節）。

## 1. まず動かす

```bash
pixi run gz sim -r shapes.sdf
```

GUI が立ち上がり、床の上に 6 つの図形が並ぶ。左下の再生ボタンで一時停止/再開。
マウス左ドラッグで回転、右ドラッグ（またはホイール）でズーム、中ドラッグでパン。

同梱ワールドの一覧:

```bash
ls .pixi/envs/default/share/gz/gz-sim/worlds/
```

## 2. 起動パターン

| やりたいこと | コマンド |
|---|---|
| GUI + サーバー（通常） | `pixi run gz sim -r shapes.sdf` |
| ヘッドレス（サーバーのみ） | `pixi run gz sim -s -r shapes.sdf` |
| GUI だけ別プロセスで起動 | `pixi run gz sim -g` |
| N ステップだけ回して終了 | `pixi run gz sim -s -r --iterations 1000 shapes.sdf` |
| ログを詳しく出す | `-v4` を足す（1=error 〜 4=debug） |

対話的に色々叩きたいときは shell に入ると楽:

```bash
pixi shell
gz sim -r shapes.sdf
gz topic -l            # トピック一覧
gz service -l          # サービス一覧
gz sim --versions
exit
```

### 走っているシミュレーションを覗く

```bash
pixi run gz topic -l                                  # トピック一覧
pixi run gz topic -e -t /world/shapes/stats -n 1      # 進行状況（RTF, iterations）
pixi run gz topic -e -t /world/shapes/pose/info -n 1  # 全エンティティの姿勢
```

## 3. カメラセンサーを試す

`worlds/camtest.sdf` は赤い箱・緑の球・指向性ライトを置き、カメラセンサーから
800x600 の画像を `output/camera/` に PNG 保存するサンプル。

**ターミナル 1** — サーバーを起動（GUI なし）:

```bash
pixi run gz sim -s -r worlds/camtest.sdf
```

**ターミナル 2** — 画像トピックを購読する（これが必須。理由は 4-4 を参照）:

```bash
cd ~/codex/gazebo
mkdir -p output/camera
pixi run gz topic -e -t /camera -n 2
```

購読した瞬間に `output/camera/camera_model::link::camera_N.png` が出力される。

```bash
open output/camera/           # Finder で確認
```

GUI 側で見たい場合は、ターミナル 2 で `pixi run gz sim -g` を起動し、
右上メニューから **Image Display** プラグインを追加してトピック `/camera` を選ぶ。

## 4. ハマりポイント

### 4-1. 起動時の OGRE エラーは無視してよい

毎回これが出るが、**実際には描画できている**:

```
[error] [Ogre2RenderEngine.cc:765] Unable to load Ogre Plugin
[.../lib/OGRE-Next                    /RenderSystem_Metal]. Rendering will not be possible.
```

パス中の長い空白は conda のプレフィックス置換で生じたパディング残り。
この直後に、conda の activate script が設定する環境変数 `OGRE2_RESOURCE_PATH` から
ロードし直して成功している。"Rendering will not be possible" は誤報。

確認方法:

```bash
pixi run env | grep OGRE
# OGRE2_RESOURCE_PATH=/.../.pixi/envs/default/lib/OGRE-Next
```

### 4-2. 必ず `pixi run` / `pixi shell` 経由で起動する

4-1 のフォールバックは activate script が設定する環境変数に依存している。
`.pixi/envs/default/bin/gz` を素のシェルから直接叩くと activate が走らず、
**本当にレンダリング不能になる**。

### 4-3. `-r` を付けないと一時停止状態で起動する

`-r` (`--run`) なしだと pause 状態で起動する。GUI があれば再生ボタンを押せばよいが、
ヘッドレスで `--iterations N` と併用すると **N に永遠に到達せず終わらない**。
（最初この状態を数分間ハングと勘違いした。`sample <pid>` で見るとメインスレッドの
92% が `sleep_for` にいて、これが一時停止アイドルループの正体。）

### 4-4. カメラは購読者がいないと描画されない

gz-sensors には「購読者がゼロのカメラはレンダリングをスキップする」最適化がある。
このため `<always_on>1</always_on>` を書いていても、誰も `/camera` を購読していない間は
**`<save enabled="true">` による PNG 出力も一切行われない**。

```bash
# これだけでは画像は 1 枚も出ない（10 秒回しても 0 枚だった）
pixi run gz sim -s -r --iterations 10000 worlds/camtest.sdf
```

別プロセスで `gz topic -e -t /camera` するか、GUI の Image Display を開くこと。

### 4-5. 保存先ディレクトリは先に作っておく

`<save><path>` のディレクトリは自動作成されないことがある。`mkdir -p output/camera` を先に。
相対パスは実行時のカレントディレクトリ基準で解決される。

### 4-6. 初回起動は遅い

OGRE のシェーダーキャッシュ生成のため、カメラセンサーを含むワールドの初回実行は
10 秒ぶんのシミュレーションに 76 秒かかった。2 回目以降は 13 秒（RTF 0.77）。
GUI の初回起動も 10 秒程度かかる。フリーズではないので待つ。

### 4-7. スクリーンショットを撮るなら画面収録権限が必要

ターミナルから `screencapture` を使う場合、
**システム設定 → プライバシーとセキュリティ → 画面収録** でターミナル（または Claude Code）に
許可が必要。無いと `could not create image from display` で失敗する。

GUI ツールバーのカメラアイコンからも撮れるが、保存先パスの扱いに癖がある
（指定したパスをディレクトリとして扱い、その下にタイムスタンプ名で保存しようとする）。

## 5. バージョンの選び方

現在は Jetty (`gz-sim` 10.x) が入っている。切り替えるなら `pixi.toml` の依存を差し替えて
`pixi install`:

| パッケージ | リリース | 備考 |
|---|---|---|
| `gz-sim` 10.5.0 | Jetty | 最新。いま入っているもの |
| `gz-sim9` 9.5.0 | Ionic | |
| `gz-sim8` 8.10.0 | **Harmonic (LTS)** | 長期運用・チーム共有ならこちら |
| `gz-harmonic` / `gz-ionic` / `gz-jetty` 1.0.0 | メタパッケージ | gz-launch 等のツール一式が付く |

すべて osx-arm64 ビルドあり。

`gazebo` 11.15.1（Gazebo Classic）も conda-forge の osx-arm64 にあるが、
2025 年 1 月に EOL 済みなので新規採用は避ける。

## 6. ROS 2 と繋ぐ

`ros_gz` ブリッジは conda-forge には無く、RoboStack チャンネルにある。いずれも osx-arm64 対応:

| チャンネル | パッケージ | バージョン |
|---|---|---|
| `robostack-jazzy` | `ros-jazzy-ros-gz` | 1.0.23 |
| `robostack-kilted` | `ros-kilted-ros-gz` | 2.1.15 |
| `robostack-humble` | `ros-humble-ros-gz` | 0.244.24 |

```toml
# pixi.toml に足す場合
[workspace]
channels = ["robostack-jazzy", "conda-forge"]

[dependencies]
ros-jazzy-desktop = "*"
ros-jazzy-ros-gz = "*"
```

ROS 2 側が要求する Gazebo バージョンと `gz-sim` のバージョンが食い違うと solver が失敗するので、
その場合は `gz-sim` の明示指定を外して ros-gz に任せる。

## 7. 別マシンに持っていく

**`.pixi/` は zip に含めない。** 環境本体は 1.8 GB あるが、`pixi.lock` から
6 秒で完全に同じものを再構築できるので、運ぶ必要がない。

### 送る側

```bash
cd ~/codex
zip -ry gazebo.zip gazebo -x "gazebo/.pixi/*" "gazebo/output/*"
```

これで **44 KB**（`pixi.toml` / `pixi.lock` / `README.md` / `CLAUDE.md` / `worlds/`）になる。

### 受け取る側

```bash
unzip gazebo.zip
cd gazebo
pixi install --locked     # ← これだけ
pixi run gz sim -r shapes.sdf
```

`pixi install --locked` は lockfile どおりのバージョンを取ってくるため、
**送り主とバイト単位で同一の環境**が再現される（`--locked` を付けると
pixi.toml と lockfile の整合も同時に検証される）。

受け取り側に必要なもの:

| | |
|---|---|
| pixi | 事前にインストールしておく |
| ネットワーク | conda-forge から **252 パッケージ / 446 MB** をダウンロード |
| 所要時間 | キャッシュ済みなら 6 秒、初回ダウンロードありなら回線次第 |
| ディスク | 展開後 1.8 GB |

### 相手がオフラインの場合

そのときだけ `.pixi/` ごと固める。**`-y` を必ず付ける**（symlink が 2673 個あり、
`-y` なしだと全部実体化してサイズが倍近くに膨らむ）。

```bash
cd ~/codex && zip -ry gazebo-full.zip gazebo -x "gazebo/output/*"   # 593 MB
```

展開先のパスは元と違ってよい。ホームディレクトリ外の全く違う階層に展開しても動くことを確認済み
（activate script が `$CONDA_PREFIX` ベースで、dylib も `@rpath` 解決のため）。
展開後に `pixi install --locked` を実行しても 0.04 秒で「インストール済み」と判定され、
ネットワークアクセスは発生しない。

ダウンロード経由で受け取って `"..." は開発元を検証できません` と言われた場合は:

```bash
xattr -dr com.apple.quarantine ~/codex/gazebo
```

## 8. 片付け

```bash
pkill -f gz-sim              # 残ったサーバー/GUI プロセスを止める
rm -rf output/               # 生成した画像を消す
pixi clean                   # .pixi/envs を削除（pixi install で再構築できる）
```

Gazebo の設定・ログは `~/.gz/` に溜まる。GUI レイアウトをリセットしたいときは
`rm -rf ~/.gz/sim/10/gui.config`。

## 参考

- Gazebo 公式ドキュメント: https://gazebosim.org/docs
- conda-forge の gz-* feedstock（Silvio Traversaro らが保守）: https://github.com/conda-forge/gz-sim-feedstock
- RoboStack: https://robostack.github.io/
