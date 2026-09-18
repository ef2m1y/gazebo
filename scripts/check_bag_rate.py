#!/usr/bin/env python3
"""bag に記録された点群のフレーム欠落を検査する。

publish 側は <update_rate> 固定なので、メッセージヘッダの sim time は一定間隔で
並んでいるはず。間隔が刻み幅を超えていればレコーダが取りこぼしている。
wall-clock ベースの `ros2 bag info` の Duration では記録開始・停止のオーバーヘッドが
混ざって実レートが正しく出ないため、sim time で見る。

    pixi run python scripts/check_bag_rate.py output/bags/avia
    pixi run python scripts/check_bag_rate.py output/bags/avia --rate 10
"""
import argparse
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _bagutil import read_clouds, storage_id

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("--topic", default="/livox/avia/points")
ap.add_argument("--rate", type=float, default=10.0, help="期待するレート [Hz]")
a = ap.parse_args()

stamps = [m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
          for m in read_clouds(a.bag, a.topic)]
if not stamps:
    sys.exit(f"{a.bag} に {a.topic} のメッセージが無い")

s = np.array(sorted(stamps))
step = 1.0 / a.rate
d = np.diff(s)
missing = int(np.round(d / step - 1).clip(min=0).sum()) if len(d) else 0
span = s[-1] - s[0]

print(f"storage        : {storage_id(a.bag)}")
print(f"記録フレーム数 : {len(s)}")
print(f"sim time 範囲  : {s[0]:.3f} .. {s[-1]:.3f} s ({span:.3f} s)")
print(f"期待フレーム数 : {int(round(span / step)) + 1}  (@{a.rate:g} Hz)")
print(f"欠落フレーム数 : {missing}")
if len(d):
    print(f"間隔 min/med/max: {d.min():.4f} / {np.median(d):.4f} / {d.max():.4f} s")

sys.exit(0 if missing == 0 else 1)
