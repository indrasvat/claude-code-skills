#!/usr/bin/env python3
"""Storing a grokery run in SQLite for cross-run trend monitoring.

Mirrors last30days' ``--store``: append-only log of (topic, slug, timestamp,
raw-markdown path, byte size) so later runs can diff what changed. Stdlib only.

Usage: store.py --db PATH --topic STR --slug STR --file PATH
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sqlite3
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    size = os.path.getsize(args.file) if os.path.exists(args.file) else 0
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    con = sqlite3.connect(args.db)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS runs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, topic TEXT, "
            "slug TEXT, path TEXT, bytes INTEGER)"
        )
        con.execute(
            "INSERT INTO runs (ts, topic, slug, path, bytes) VALUES (?,?,?,?,?)",
            (ts, args.topic, args.slug, args.file, size),
        )
        con.commit()
    finally:
        con.close()
    print(f"stored: {args.slug} @ {ts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
