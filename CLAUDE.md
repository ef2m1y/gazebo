# gazebo

macOS (Apple Silicon) で Gazebo Sim + ROS 2 を動かす検証環境。
主な用途は Livox Avia 相当の点群を rosbag に記録すること。手順と既知の落とし穴は `README.md`。

## Pixi environment

設定: `pixi.toml` / 再構築: `pixi install --locked`

設計判断:
- Homebrew の `osrf/simulation` tap は使わない（pixi-only ポリシー）。channel は
  `robostack-jazzy` + `conda-forge` の 2 つ
- **Harmonic (gz-sim8) を使うのは Jetty 対応の `ros-gz` が存在しないから**。Jetty も LTS で
  EOL は 2031-05 と Harmonic の 2029-05 より長い。「古い方が安定」という判断ではない。
  gz-transport がメジャー差 (15 vs 13) で通信できないのが直接の理由
- 単一 environment に統一している。Jetty と Harmonic を同居させると `gz sim` が
  どちらを起動するか不定になり、`pixi run` に毎回 `-e` が要るだけで利点が無い
- `.pixi/` (3.6 GB) は配布に含めない。`pixi.toml` + `pixi.lock` から `pixi install --locked` で
  バイト単位同一に再構築できる。パスを変えてコピーしても動作自体はする
  (activate script は `$CONDA_PREFIX` ベース、dylib は `@rpath` 解決) が転送量が無駄
- ROS 2 の discovery は `[activation.env]` で `LOCALHOST` + `ROS_DOMAIN_ID=42` に固定。
  Jazzy 既定の `SUBNET` のままだと同一サブネットの他マシンと相互に見える

## 挙動の注意

- 起動時の `Unable to load Ogre Plugin[...RenderSystem_Metal]` は誤報。conda の
  `libgz-rendering_activate.sh` が設定する `OGRE2_RESOURCE_PATH` でフォールバック成功している。
  ただしこの依存のため **`pixi run` / `pixi shell` 経由必須** — env 内バイナリの直叩きは描画不能
- macOS では `gz sim -s` と `gz sim -g` を別ターミナルで起動する必要がある（gz-sim#44）。
  Jetty では一発起動できたが Harmonic では拒否される。ダウングレードで失った数少ない機能
- カメラセンサーは購読者ゼロだと描画がスキップされ、`<save>` の PNG 出力も走らない（gz-sensors の最適化）
- `worlds/livox_avia_gpu.sdf` は Avia の **FOV とレンジと点数だけ**を合わせた近似。
  非反復（ロゼッタ）スキャンは再現していない。gz-sim にレイ方向を個別指定する手段が無いため
- rosbag は `.db3` (sqlite3) が既定。Jazzy の rosbag2 自体の既定は mcap だが、
  ここでは明示的に `-s sqlite3` を指定している。7.35 MiB/s = 26 GiB/時 で無圧縮になるが、
  120 秒連続記録で欠落 0 フレーム・間隔 0.1000 s を実測確認済み
- 容量を抑えたいときは `avia-record-mcap` (mcap + zstd で約 1/5)。`.db3` は
  `--storage-preset-profile` に zstd が無く圧縮できない
- `scripts/check_bag_rate.py` が欠落フレームの検査ツール。sim time ベースで見る
  (`ros2 bag info` の Duration は wall-clock で記録開始・停止のオーバーヘッドが混ざる)
