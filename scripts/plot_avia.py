#!/usr/bin/env python3
"""bag から 1 フレーム取り出して Avia 点群を 4 面図で描く。

    pixi run python scripts/plot_avia.py output/bags/avia output/plots/avia_pointcloud.png

右上のレンジ画像が最も情報量が多い。センサーのサンプリング格子がそのまま出るので、
実機 Avia の非反復 (ロゼッタ) スキャンとの違いが一目で分かる。
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sensor_msgs_py import point_cloud2

sys.path.insert(0, str(Path(__file__).parent))
from _bagutil import read_clouds

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("out")
ap.add_argument("--topic", default="/livox/avia/points")
ap.add_argument("--max-range", type=float, default=190.0,
                help="これ以上は「当たらなかったレイ」として捨てる")
a = ap.parse_args()

msg = next(read_clouds(a.bag, a.topic, limit=1), None)
if msg is None:
    sys.exit(f"{a.bag} に {a.topic} のメッセージが無い")

H, W = msg.height, msg.width
p = np.asarray(point_cloud2.read_points_numpy(msg, field_names=("x", "y", "z")),
               dtype=np.float64).reshape(H, W, 3)
rng = np.linalg.norm(p, axis=2)
hit = np.isfinite(rng) & (rng < a.max_range)
xyz, d_hit = p[hit], rng[hit]

fig = plt.figure(figsize=(16, 11))

# 1. 3D パース。遠方の地面まで入れると縦に潰れて読めないので 12 m 以内に絞る
ax = fig.add_subplot(2, 2, 1, projection="3d")
m = d_hit < 12
sc = ax.scatter(xyz[m, 0], xyz[m, 1], xyz[m, 2], c=d_hit[m], s=2.0, cmap="turbo")
ax.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]",
       title=f"3D perspective (range < 12 m) — {len(xyz):,} hits / {H*W:,} rays total")
ax.view_init(elev=26, azim=-118)
ax.set_box_aspect((2.2, 2.2, 1.0))
ax.set_zlim(-1.3, 1.3)
fig.colorbar(sc, ax=ax, label="range [m]", shrink=0.6)

# 2. レンジ画像。格子構造がそのまま見える
ax = fig.add_subplot(2, 2, 2)
im = ax.imshow(np.where(hit, rng, np.nan), cmap="turbo", aspect="auto", origin="lower")
ax.set(xlabel=f"horizontal sample ({W})", ylabel=f"vertical sample ({H})",
       title=f"Range image — {H} x {W} grid (NOT a rosette pattern)")
fig.colorbar(im, ax=ax, label="range [m]")

# 3. 上から
ax = fig.add_subplot(2, 2, 3)
sc = ax.scatter(xyz[:, 0], xyz[:, 1], c=xyz[:, 2], s=1.2, cmap="viridis")
ax.set(xlabel="x [m]", ylabel="y [m]", title="Top view — horizontal FOV", aspect="equal")
ax.grid(alpha=0.3)
fig.colorbar(sc, ax=ax, label="z [m]")

# 4. 近傍の正面図
near = xyz[d_hit < 9]
ax = fig.add_subplot(2, 2, 4)
sc = ax.scatter(near[:, 1], near[:, 2], c=near[:, 0], s=6, cmap="plasma")
ax.set(xlabel="y [m]", ylabel="z [m]",
       title="Front view, range < 9 m", aspect="equal")
ax.grid(alpha=0.3)
fig.colorbar(sc, ax=ax, label="x [m]")

fig.suptitle("Livox Avia (gpu_lidar approximation) — sensor_msgs/PointCloud2 from rosbag",
             fontsize=15)
fig.tight_layout()
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
fig.savefig(a.out, dpi=105)
print(f"hits {len(xyz)} / {H*W}  range {d_hit.min():.2f}-{d_hit.max():.2f} m -> {a.out}")
