#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CYCLE-45 截图复核：独立重算 PNG sha256 + 从 render_report 取像素自检。

用法：python3 v2/evidence/CYCLE-45-cases/check_shots.py
"""
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rc = 0
    for rep in sorted(glob.glob(os.path.join(SHOTS, "render_report_*.json"))):
        d = json.load(open(rep, encoding="utf-8"))
        print("=" * 78)
        print("REPORT %s" % os.path.basename(rep))
        print("REPORT_SHA256 %s" % sha256_file(rep))
        print("BATCH_ID %s  ok=%s fail=%s" % (d.get("batch_id"), d.get("ok_count"), d.get("fail_count")))
        print("LOG %s" % d.get("log"))
        print("LOG_SHA256 %s" % d.get("log_sha256"))
        for v in d.get("views", []):
            png = v["png"]
            rec_sha = v.get("png_sha256")
            real_sha = sha256_file(png) if os.path.isfile(png) else None
            sc = v.get("pixel_selfcheck") or {}
            stamp_ok = (real_sha == rec_sha)
            rc = rc or (0 if stamp_ok else 1)
            print("-- view=%s rc=%s" % (v.get("view"), v.get("rc")))
            print("   png %s" % png)
            print("   png_sha256(record)=%s" % rec_sha)
            print("   png_sha256(recompute)=%s  match=%s" % (real_sha, stamp_ok))
            print("   pixels %sx%s distinct_colors=%s top_color_frac=%s non_bg_frac=%s status=%s"
                  % (sc.get("width"), sc.get("height"), sc.get("distinct_colors"),
                     sc.get("top_color_frac"), sc.get("non_bg_frac"), sc.get("status")))
    print("=" * 78)
    print("CHECK_RC=%d" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
