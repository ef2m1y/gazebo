# Gazebo Sim on macOS (Apple Silicon) — pixi 環境

Gazebo Sim (Harmonic) と ROS 2 Jazzy を pixi で動かす環境。
Homebrew (`osrf/simulation` tap) は不要。主な用途は Livox Avia 相当の点群を rosbag に記録すること。

以下のコマンドはすべて **`~/codex/gazebo` をカレントディレクトリとして** 実行する想定で記載しています。適宜変更ください。

```bash
cd ~/codex/gazebo
```

## 動作確認済み（2026-09-18 実測）

| 項目 | 結果 |
|---|---|
| ホスト | macOS 26.5 / Apple Silicon (arm64) / pixi 0.67.0 |
| Gazebo | gz-sim **8.10.0** (Harmonic), osx-arm64 ネイティブ |
| ROS 2 | Jazzy (RoboStack), osx-arm64 ネイティブ |
| 環境サイズ | 3.6 GB |
| 物理エンジン | DART (`gz-physics-dartsim-plugin`), RTF **0.997** |
| カメラセンサー | オフスクリーン描画 OK、800x600 PNG 出力を確認 |
| GPU LiDAR | `gpu_lidar` が Metal で動作。24,000 点/スキャン @ **10 Hz** |
| ROS 2 ブリッジ | `ros-jazzy-ros-gz` で `sensor_msgs/PointCloud2` 出力を確認 |
| rosbag 記録 | `.db3` で 120 秒連続記録・**欠落 0 フレーム**（1182 枚）、間隔 0.1000 s 一定 |
| GUI | `-s` と `-g` を別ターミナルで起動。Metal 描画・Visualize lidar・Entity tree 正常 (RTF 99.61%) |

**macOS では `-s` と `-g` を別ターミナルで起動する必要がある。** 同時起動しようとすると
gz-sim 側が明示的に拒否する（[gazebosim/gz-sim#44](https://github.com/gazebosim/gz-sim/issues/44)）:

```
On macOS `gz sim` currently only works with either the -s argument
or the -g argument, you cannot run both server and gui in one terminal.
```

この制約は Jetty (gz-sim 10) では解消されていて一発起動できたが、Harmonic では残っている。
ROS 2 対応と引き換えに失う数少ない機能のひとつ。

## セットアップ

環境は構築済み。別マシンで再現する場合も `pixi.toml` と `pixi.lock` だけあればよい（8 節参照）:

```bash
pixi install --locked    # lockfile どおりに再現（--locked で toml との整合も検証される）
```

`.pixi/` は 3.6 GB あるが、lockfile から再構築できるので配布物に含める必要はない
（別マシンへの持ち出しは 8 節）。

## リポジトリ構成

```
pixi.toml / pixi.lock   環境定義（これだけあれば再現できる）
worlds/
  camtest.sdf           カメラセンサーの動作確認用
  livox_avia_gpu.sdf    Livox Avia 近似の gpu_lidar ワールド
scripts/
  check_bag_rate.py     bag のフレーム欠落を検査（欠落ありなら exit 1）
  plot_avia.py          bag から点群を 4 面図で描画
  _bagutil.py           上記 2 本の共通処理（storage 自動判別）
output/                 生成物。git 管理外
  bags/                 rosbag
  plots/                点群の描画
  camera/               camtest.sdf の PNG
```

## 1. まず動かす

ターミナルを 2 つ使う（macOS では 1 コマンドでサーバー + GUI を起動できない。上記参照）。

```bash
pixi run gz sim -s -r shapes.sdf   # ターミナル 1: サーバー
pixi run gz sim -g                 # ターミナル 2: GUI
```

GUI が立ち上がり、床の上に 6 つの図形が並ぶ。左下の再生ボタンで一時停止/再開。
マウス左ドラッグで回転、右ドラッグ（またはホイール）でズーム、中ドラッグでパン。
GUI の起動には 10 秒程度かかる（4-6 参照）。

同梱ワールドの一覧:

```bash
ls .pixi/envs/default/share/gz/gz-sim8/worlds/
```

## 2. 起動パターン

| やりたいこと | コマンド |
|---|---|
| GUI + サーバー | **1 コマンドでは不可**。下の 2 行を別ターミナルで |
| ヘッドレス（サーバーのみ） | `pixi run gz sim -s -r shapes.sdf` |
| GUI を繋ぐ | `pixi run gz sim -g` |
| N ステップだけ回して終了 | `pixi run gz sim -s -r --iterations 1000 shapes.sdf` |
| ログを詳しく出す | `-v4` を足す（1=error 〜 4=debug） |

対話的に色々叩きたいときは shell に入ると楽:

```bash
pixi shell
gz sim -s -r shapes.sdf &   # サーバー（GUI は別ターミナルで gz sim -g）
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

### 4-8. ROS 2 の discovery は既定で LAN に漏れる

ROS 2 Jazzy の既定は `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`。何もしないと同一サブネット上の
他マシンの ROS 2 システムと相互に見える。実際、ローカルに ROS プロセスが 1 つも無い状態で
`/obstacle_detector` `/ekf/*` `/merged_points` など無関係な 13 トピックが見えた。

`pixi.toml` の `[activation.env]` で `LOCALHOST` + `ROS_DOMAIN_ID=42` に隔離してある。
他マシンへ流したい場合はこの 2 つを外す。

### 4-9. `ros2 topic list` は daemon のキャッシュを返す

discovery 設定を変えた直後は `--no-daemon` を付けるか `ros2 daemon stop` する。
付けないと古い設定のままの結果が返り、**ブリッジが動いていてもトピックが見えない**。
（この状態を 1 回ブリッジの故障と誤認した。）

### 4-10. pixi task の中で `[` は glob 展開される

ブリッジの引数 `/livox/avia/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked` は、
pixi の task shell が `[` を glob として解釈して `invalid range pattern` で落ちる。
task 定義側でシングルクォートで囲む必要がある。

## 5. バージョンの選び方

現在は **Harmonic (`gz-sim8` 8.10.0)** が入っている。

| パッケージ | リリース | EOL | 備考 |
|---|---|---|---|
| `gz-sim8` 8.10.0 | **Harmonic (LTS)** | 2029-05 | いま入っているもの。ROS 2 Jazzy の公式ペア |
| `gz-sim9` 9.5.0 | Ionic | 2026-12 | 非 LTS |
| `gz-sim` 10.5.0 | **Jetty (LTS)** | 2031-05 | 最新。ただし対応する ros-gz が無い（6 節） |
| `gz-harmonic` / `gz-ionic` / `gz-jetty` 1.0.0 | メタパッケージ | | gz-launch 等のツール一式が付く |

すべて osx-arm64 ビルドあり。

**Harmonic を選んだ理由は「古いから安定」ではない。** Jetty も LTS で、EOL は 2031-05 と
Harmonic の 2029-05 より 2 年長い。純粋に **Jetty 対応の `ros-gz` がどのチャンネルにも
存在しない**ためで、ROS 2 に繋ぐ要件がある限り Jetty は選べない（詳細は 6 節）。
将来 RoboStack が Jetty 対応の ros-gz を出したら、`pixi.toml` の依存を差し替えて
`pixi install` するだけで上げられる。

`gazebo` 11.15.1（Gazebo Classic）も conda-forge の osx-arm64 にあるが、
2025 年 1 月に EOL 済みなので新規採用は避ける。

### Jetty での動作確認記録（履歴）

ROS 2 要件が出る前、このリポジトリは Jetty (`gz-sim` 10.5.0) 単体で構築されていた。
その時点で以下を実測済み:

- 環境サイズ 1.8 GB / `pixi install` 6〜13 秒
- 物理 DART で RTF 0.997、GUI は Qt6 + Metal で影・Entity Tree とも正常 (RTF 99.94%)
- カメラセンサーのオフスクリーン描画と 800x600 PNG 出力
- `gz sim -r world.sdf` の一発起動（サーバー + GUI 同時）
- `gpu_lidar` が Metal で動作し 24,000 点/スキャン @ 10 Hz

つまり Jetty 自体は macOS 上で問題なく動く。4 節のハマりポイントも Jetty で洗い出したもので、
Harmonic でもそのまま当てはまる。Jetty に戻す場合は `pixi.toml` の `gz-sim8` を
`gz-sim = ">=10.5.0,<11"` に替え、ROS 2 関連の依存と channel を外す。

## 6. ROS 2 と繋ぐ

`ros_gz` ブリッジは conda-forge には無く、RoboStack チャンネルにある。いずれも osx-arm64 対応。
**ただし Jetty (gz-sim 10) 対応の ros-gz はどのチャンネルにも無い**（2026-09-18 実測）:

| チャンネル | パッケージ | バージョン | gz-transport / gz-msgs | 対応 Gazebo |
|---|---|---|---|---|
| `robostack-jazzy` | `ros-jazzy-ros-gz` | 1.0.23 | 13 / 10 | **Harmonic (gz-sim8)** |
| `robostack-kilted` | `ros-kilted-ros-gz` | 2.1.15 | 14 / 11 | Ionic (gz-sim9) |
| `robostack-humble` | `ros-humble-ros-gz` | 0.244.24 | — | Fortress (gz-sim6) |
| — | （Jetty 用は無い） | — | 15 / 12 | Jetty (gz-sim10) |

`robostack-rolling` は存在しない。gz-transport はメジャーバージョンが違うと通信できないため、
**ROS 2 に繋ぐなら Harmonic 一択**になる。Jazzy と Harmonic はどちらも LTS で、これが公式ペアリング。

必要な依存は `pixi.toml` にまとまっている:

| パッケージ | 用途 |
|---|---|
| `gz-sim8` | シミュレータ本体 (Harmonic) |
| `ros-jazzy-ros-gz` | gz ↔ ROS 2 ブリッジ |
| `ros-jazzy-ros2run` | `ros2 run` サブコマンド（これが無いとブリッジを起動できない） |
| `ros-jazzy-ros2bag` | `ros2 bag` サブコマンド |
| `ros-jazzy-rosbag2-storage-mcap` | mcap ストレージ（zstd 圧縮に必要） |

### discovery の隔離

ROS 2 Jazzy の discovery 既定は `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`。`pixi.toml` の
`[activation.env]` で `LOCALHOST` + `ROS_DOMAIN_ID=42` に固定してある。理由は 4-8 を参照。
他マシンへ流したい場合はこの 2 つを外す。

## 7. Livox Avia の点群を rosbag に記録する

`worlds/livox_avia_gpu.sdf` は Livox Avia を `gpu_lidar` で近似したワールド。
ターミナルを 3 つ開いて順に起動する。

```bash
pixi run avia-sim       # 1. シミュレータ（ヘッドレス）
pixi run avia-bridge    # 2. gz -> ROS 2 ブリッジ
pixi run avia-record    # 3. rosbag 記録（output/bags/avia、.db3 形式）
```

記録を止めるのは Ctrl-C。確認:

```bash
pixi run ros2 bag info output/bags/avia
pixi run ros2 topic echo --once --no-daemon /livox/avia/points   # 生データを見る

# フレーム欠落の検査（sim time ベース。欠落があれば exit 1）
pixi run python scripts/check_bag_rate.py output/bags/avia

# 点群を 4 面図で描画
pixi run python scripts/plot_avia.py output/bags/avia output/plots/avia_pointcloud.png
```

`scripts/` の 2 本はどちらも `metadata.yaml` から storage を自動判別するので、
`.db3` / `.mcap` のどちらで録った bag にもそのまま使える。

実測（2026-09-18）:

| 項目 | 値 |
|---|---|
| ROS 2 型 | `sensor_msgs/msg/PointCloud2` |
| frame_id | `livox_avia/link/avia` |
| 点数 | 120 × 200 = **24,000 点/スキャン** |
| フィールド | x, y, z, intensity, ring |
| レート | **10 Hz**（sim time 間隔 0.1000 s 一定、欠落 0 フレーム） |
| 1 メッセージ | 768,000 byte (0.73 MiB) |
| bag サイズ | **7.35 MiB/s**（`.db3` 既定）/ 1.47 MiB/s（mcap + zstd） |

うち実際に物体に当たるのは 24,000 レイ中 14,076 点（58.6%）。残りは上向きで無限遠になる。

### 7-1. 実機との違い（重要）

**これはロゼッタスキャンではない。** Avia 実機は非反復スキャンで、積分時間を延ばすほど
FOV 内のカバレッジが上がるのが最大の特徴だが、`gpu_lidar` は等間隔の球面グリッドしか撃てない。
レイごとに任意方向を指定する機能は
[gazebosim/gz-sim#1958](https://github.com/gazebosim/gz-sim/issues/1958) で要望されているが、
2023 年 4 月から OPEN のまま。

実機に合わせてあるのは以下のスペックだけ（出典は
[Livox-SDK/livox_laser_simulation](https://github.com/Livox-SDK/livox_laser_simulation) の README）:

| パラメータ | 値 |
|---|---|
| horizontal_fov | 70.4° |
| vertical_fov | 77.2° |
| range | 0.1 – 200 m |
| samples | 24000 点/スキャン |

SLAM や障害物回避のジオメトリ検証には足りるが、非反復性そのものを使う検証には向かない。

### 7-2. 本家プラグインが使えない理由

`Livox-SDK/livox_laser_simulation` は **Gazebo Classic 9.x + ROS Melodic + Ubuntu 18.04 専用**。
プラグイン本体が `gazebo::RayPlugin` を継承し、`livox_ode_multiray_shape.cpp` で Gazebo Classic の
ODE 内部 API を直接叩いているため、gz-sim への移植は書き直しに近い。
Gazebo Classic 自体が 2025 年 1 月に EOL 済み。

任意レイパターンに対応する
[Robotec GPU Lidar](https://github.com/RobotecAI/RobotecGPULidar) は
NVIDIA Turing 以降 + CUDA + OptiX 必須で Linux/Windows のみ。macOS ARM では選択肢にならない。

ロゼッタパターンまで再現したい場合は、本家の `scan_mode/avia.csv`
（33 MB / 960,000 行 / `Time,Azimuth,Zenith` / 240 kHz・4 秒ぶん、MIT）を持ってきて、
高密度グリッドで回した `gpu_lidar` の出力から最近傍レイを引く後処理を書くことになる。
**33 MB の CSV をそのまま git に入れないこと**（git-lfs か間引きが要る）。

### 7-3. bag のフォーマット（`.db3` と `.mcap`）

ROS 2 Jazzy の rosbag2 は **既定が `mcap`** に変わっている。`.db3`（sqlite3）は旧来の既定で、
いまも `-s sqlite3` で使える。`avia-record` task は **`.db3` を既定**にしてある。

```
-s {sqlite3,mcap}, --storage {sqlite3,mcap}
                      Storage identifier to be used, defaults to 'mcap'.
```

| | 1 メッセージ | データレート | 圧縮 |
|---|---|---|---|
| `.db3` (sqlite3) — `avia-record` | 0.735 MiB | **7.35 MiB/s** ≈ 26 GiB/時 | 不可 |
| `.mcap` + zstd — `avia-record-mcap` | 0.149 MiB | 1.47 MiB/s ≈ 5.2 GiB/時 | チャンク単位 zstd |

**`.db3` でも 10 Hz は維持される。** 120 秒の連続記録（868 MiB / 7.35 MiB/s）で
sim time 間隔は min/med/max とも 0.1000 s、**欠落 0 フレーム（1182 枚）**だった。
`scripts/check_bag_rate.py` で再現できる。

容量が問題になるときだけ `avia-record-mcap` に切り替える。約 1/5 になり、
可逆（両形式のデータ部 768,000 byte は SHA-256 が一致）でシークも効いたまま。

**`.db3` では圧縮オプションが使えない。** `--storage-preset-profile` の選択肢が
`none, resilient` だけで zstd が無い:

```
ros2 bag record: error: argument --storage-preset-profile:
invalid choice: 'zstd_fast' (choose from none, resilient)
```

`--compression-format zstd` も選択肢が空で通らない（別パッケージ
`ros-jazzy-rosbag2-compression-zstd` が要る）。仮に入れても、そちらは**ファイル単位圧縮**で
読むたびに bag 全体を展開する必要があり、mcap のチャンク単位圧縮のようにシークが効かない。

データ量をさらに削るなら `<update_rate>` を下げるか `<samples>` を減らす。

## 8. 別マシンに持っていく

**`.pixi/` は zip に含めない。** 環境本体は 3.6 GB あるが、`pixi.lock` から
完全に同じものを再構築できるので、運ぶ必要がない。

### 送る側

```bash
cd ~/codex
zip -ry gazebo.zip gazebo -x "gazebo/.pixi/*" "gazebo/output/*" "gazebo/.git/*"
```

これで **105 KB**（`pixi.toml` / `pixi.lock` / `README.md` / `CLAUDE.md` / `worlds/`）になる。
大半は `pixi.lock` の 440 KB 分（圧縮後）。

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
| ネットワーク | conda-forge + robostack-jazzy から **717 パッケージ**をダウンロード |
| 所要時間 | キャッシュ済みなら 1 秒未満、初回ダウンロードありなら回線次第 |
| ディスク | 展開後 3.6 GB |

### 相手がオフラインの場合

そのときだけ `.pixi/` ごと固める。**`-y` を必ず付ける**（symlink が 3208 個あり、
`-y` なしだと全部実体化してサイズが倍近くに膨らむ）。

```bash
cd ~/codex && zip -ry gazebo-full.zip gazebo -x "gazebo/output/*" "gazebo/.git/*"   # 1.08 GB / 約 1 分半
```

展開先のパスは元と違ってよい。ホームディレクトリ外の全く違う階層に展開しても動くことを確認済み
（activate script が `$CONDA_PREFIX` ベースで、dylib も `@rpath` 解決のため）。
展開後に `pixi install --locked` を実行しても 0.04 秒で「インストール済み」と判定され、
ネットワークアクセスは発生しない。

ダウンロード経由で受け取って `"..." は開発元を検証できません` と言われた場合は:

```bash
xattr -dr com.apple.quarantine ~/codex/gazebo
```

## 9. 片付け

```bash
pkill -f gz-sim              # 残ったサーバー/GUI プロセスを止める
pkill -f parameter_bridge    # ROS 2 ブリッジを止める
pkill -f "bag record"        # rosbag 記録を止める
rm -rf output/               # 生成した画像・bag を消す
pixi clean                   # .pixi/envs を削除（pixi install で再構築できる）
```

Gazebo の設定・ログは `~/.gz/` に溜まる。GUI レイアウトをリセットしたいときは
`rm -rf ~/.gz/sim/8/gui.config`。

## 参考

- Gazebo 公式ドキュメント: https://gazebosim.org/docs
- conda-forge の gz-* feedstock（Silvio Traversaro らが保守）: https://github.com/conda-forge/gz-sim-feedstock
- RoboStack: https://robostack.github.io/
