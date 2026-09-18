# gazebo

macOS (Apple Silicon) で Gazebo Sim を動かす検証環境。手順と既知の落とし穴は `README.md`。

## Pixi environment

設定: `pixi.toml` / 再構築: `pixi install --locked`

設計判断:
- conda-forge 単 channel。Homebrew の `osrf/simulation` tap は使わない（pixi-only ポリシー）
- `.pixi/` (1.8 GB) は配布に含めない。`pixi.toml` + `pixi.lock` から `pixi install --locked` で
  6 秒・バイト単位同一に再構築できる。パスを変えてコピーしても動作自体はする
  (activate script は `$CONDA_PREFIX` ベース、dylib は `@rpath` 解決) が転送量が無駄
- 起動時の `Unable to load Ogre Plugin[...RenderSystem_Metal]` は誤報。conda の
  `libgz-rendering_activate.sh` が設定する `OGRE2_RESOURCE_PATH` でフォールバック成功している。
  ただしこの依存のため **`pixi run` / `pixi shell` 経由必須** — env 内バイナリの直叩きは描画不能
- カメラセンサーは購読者ゼロだと描画がスキップされ、`<save>` の PNG 出力も走らない（gz-sensors の最適化）
