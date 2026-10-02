from __future__ import annotations
import os, sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH=Path(os.getenv('DATABASE_PATH','/data/hausmonitor.db'))
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','/data/uploads'))
LEVEL_UPLOAD_DIR=UPLOAD_DIR/'nivellement'
CRACK_UPLOAD_DIR=UPLOAD_DIR/'cracks'
SCHEMA='''
CREATE TABLE IF NOT EXISTS campaigns(
 id INTEGER PRIMARY KEY AUTOINCREMENT, measured_at TEXT NOT NULL,
 air_temp REAL, wall_temp_sw REAL, wall_temp_so REAL, groundwater REAL,
 rainfall_14d REAL, weather TEXT, light_mode TEXT, notes TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS readings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
 point TEXT NOT NULL CHECK(point IN ('SW','SO','ANB','TSW','TSO')),
 sequence INTEGER NOT NULL CHECK(sequence BETWEEN 1 AND 10), value REAL NOT NULL,
 UNIQUE(campaign_id,point,sequence));
CREATE TABLE IF NOT EXISTS photos(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
 point TEXT NOT NULL, filename TEXT NOT NULL, caption TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_points(
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
 location TEXT, description TEXT, unit TEXT NOT NULL DEFAULT 'mm',
 reference_value REAL, active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_measurements(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 crack_point_id INTEGER NOT NULL REFERENCES crack_points(id) ON DELETE CASCADE,
 measured_at TEXT NOT NULL, air_temp REAL, value REAL NOT NULL, notes TEXT,
 photo_filename TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_readings_campaign ON readings(campaign_id);
CREATE INDEX IF NOT EXISTS idx_photos_campaign ON photos(campaign_id);
CREATE INDEX IF NOT EXISTS idx_crack_measurements_point_date ON crack_measurements(crack_point_id,measured_at);
'''

def init_db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    LEVEL_UPLOAD_DIR.mkdir(parents=True,exist_ok=True); CRACK_UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute('PRAGMA foreign_keys=ON'); con.executescript(SCHEMA)
        # Safe, additive migrations for databases from prior versions.
        cols={r[1] for r in con.execute('PRAGMA table_info(campaigns)')}
        for name,kind in [('rainfall_14d','REAL'),('light_mode','TEXT')]:
            if name not in cols: con.execute(f'ALTER TABLE campaigns ADD COLUMN {name} {kind}')

@contextmanager
def connection():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
    try: yield con; con.commit()
    finally: con.close()
