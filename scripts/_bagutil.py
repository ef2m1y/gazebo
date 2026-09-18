"""bag 読み出しの共通処理。

storage_id は metadata.yaml から読む。mcap / sqlite3 のどちらで録った bag でも
同じスクリプトが通るようにするため（rosbag2_py は storage_id の指定が必須で、
間違えると無言で 0 メッセージを返す）。
"""
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2


def storage_id(bag: str) -> str:
    meta = Path(bag) / "metadata.yaml"
    for line in meta.read_text().splitlines():
        if "storage_identifier:" in line:
            return line.split(":", 1)[1].strip()
    raise SystemExit(f"storage_identifier が {meta} に見つからない")


def read_clouds(bag: str, topic: str, limit: int | None = None):
    """bag 内の PointCloud2 を順に yield する。"""
    r = rosbag2_py.SequentialReader()
    r.open(
        rosbag2_py.StorageOptions(uri=bag, storage_id=storage_id(bag)),
        rosbag2_py.ConverterOptions("", ""),
    )
    n = 0
    while r.has_next():
        t, data, _ = r.read_next()
        if t != topic:
            continue
        yield deserialize_message(data, PointCloud2)
        n += 1
        if limit is not None and n >= limit:
            return
