"""
Storage Migration Script: Aliyun OSS -> Minio (or between providers)

Usage:
    python backend/scripts/storage_migration.py [--dry-run] [--resume] [--verify]

Options:
    --dry-run   Scan files only, do not migrate
    --resume    Resume from last migration state
    --verify    Verify source and destination files match
"""

import os
import sys
import json
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oss2
import psycopg2
from psycopg2.extras import RealDictCursor
from minio import Minio
from app.config.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("storage_migration")

STATE_FILE = os.path.join(os.path.dirname(__file__), "migration_state.json")
MAX_RETRIES = 3
BATCH_SIZE = 100


def get_oss_client():
    """Get Aliyun OSS client"""
    auth = oss2.Auth(
        settings.ALIYUN_OSS_ACCESS_KEY_ID,
        settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
    )
    bucket = oss2.Bucket(auth, settings.ALIYUN_OSS_ENDPOINT, settings.ALIYUN_OSS_BUCKET_NAME)
    return bucket


def get_minio_client():
    """Get Minio client"""
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    return client, settings.MINIO_BUCKET_NAME


def get_db_conn():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=settings.__dict__.get("POSTGRES_HOST", "39.107.229.30"),
        port=5432,
        database="tools",
        user="postgres",
        password="Peanut2817*#",
        cursor_factory=RealDictCursor,
    )


def load_state() -> dict:
    """Load migration state for resume"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"migrated_files": 0, "failed_files": [], "last_object_key": "", "started_at": ""}


def save_state(state: dict):
    """Save migration state"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def oss_url_to_minio_url(old_url: str) -> str:
    """Convert Aliyun OSS URL to Minio URL"""
    # Extract object key from URL
    # https://oss-peanut.oss-cn-beijing.aliyuncs.com/uploads/user1/file.png
    # or https://oss-peanut.oss-cn-beijing.aliyuncs.com:443/uploads/user1/file.png
    if old_url.startswith("http://") or old_url.startswith("https://"):
        # Find the first / after the domain
        parts = old_url.split("/", 3)
        if len(parts) >= 4:
            object_key = parts[3]
        else:
            object_key = parts[-1]
    else:
        object_key = old_url

    return f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{object_key}"


def list_oss_files(oss_bucket, start_after: str = "") -> list:
    """List all files from Aliyun OSS"""
    files = []
    iterator = oss2.ObjectIterator(oss_bucket, start_after=start_after if start_after else None, max_keys=BATCH_SIZE)
    for obj in iterator:
        files.append(obj)
    return files


def compute_md5(data: bytes) -> str:
    """Compute MD5 hash"""
    return hashlib.md5(data).hexdigest()


def migrate_file(oss_bucket, minio_client, minio_bucket, obj) -> bool:
    """Migrate a single file from OSS to Minio"""
    object_key = obj.key

    for attempt in range(MAX_RETRIES):
        try:
            # Download from OSS
            result = oss_bucket.get_object(object_key)
            content = result.read()

            # Upload to Minio
            from io import BytesIO
            minio_client.put_object(
                minio_bucket,
                object_key,
                BytesIO(content),
                length=len(content),
                content_type=obj.content_type or "application/octet-stream",
            )

            # Verify size
            stat = minio_client.stat_object(minio_bucket, object_key)
            if stat.size != obj.size:
                logger.error(f"Size mismatch for {object_key}: OSS={obj.size}, Minio={stat.size}")
                return False

            return True

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {object_key}: {e}")
            if attempt == MAX_RETRIES - 1:
                return False
            time.sleep(1)

    return False


def update_db_url(object_key: str, new_url: str):
    """Update file URL in PostgreSQL oss_files table"""
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE oss_files SET url = %s WHERE file_path = %s",
                (new_url, object_key),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update DB URL for {object_key}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def dry_run():
    """Dry run: list files without migrating"""
    oss_bucket = get_oss_client()
    logger.info("Dry run: scanning files from Aliyun OSS...")

    files = []
    marker = ""
    while True:
        batch = list_oss_files(oss_bucket, start_after=marker if marker else "")
        if not batch:
            break
        files.extend(batch)
        marker = batch[-1].key
        if len(batch) < BATCH_SIZE:
            break

    total_size = sum(f.size or 0 for f in files)
    total_mb = total_size / (1024 * 1024)

    logger.info(f"Found {len(files)} files, total size: {total_mb:.2f} MB")
    logger.info(f"Target bucket: {settings.MINIO_BUCKET_NAME}")
    logger.info(f"Target endpoint: {settings.MINIO_ENDPOINT}")

    # Show first 10 files
    for f in files[:10]:
        logger.info(f"  {f.key} ({f.size} bytes)")
    if len(files) > 10:
        logger.info(f"  ... and {len(files) - 10} more files")


def migrate(resume: bool = False):
    """Execute migration"""
    oss_bucket = get_oss_client()
    minio_client, minio_bucket = get_minio_client()

    state = load_state() if resume else {
        "started_at": datetime.now().isoformat(),
        "total_files": 0,
        "migrated_files": 0,
        "failed_files": [],
        "last_object_key": "",
    }

    # Ensure Minio bucket exists
    if not minio_client.bucket_exists(minio_bucket):
        minio_client.make_bucket(minio_bucket)
        logger.info(f"Created Minio bucket: {minio_bucket}")

    # Set public read policy
    import json as _json
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{minio_bucket}/*"],
        }],
    }
    minio_client.set_bucket_policy(minio_bucket, _json.dumps(policy))
    logger.info(f"Set public read policy for bucket: {minio_bucket}")

    logger.info("Starting migration...")
    start_time = time.time()

    # List all files
    all_files = []
    marker = ""
    while True:
        batch = list_oss_files(oss_bucket, start_after=marker if marker else "")
        if not batch:
            break
        all_files.extend(batch)
        marker = batch[-1].key
        if len(batch) < BATCH_SIZE:
            break

    state["total_files"] = len(all_files)
    logger.info(f"Total files to migrate: {len(all_files)}")

    # Skip already-migrated files if resuming
    if resume and state["last_object_key"]:
        skip_until = False
        new_files = []
        for f in all_files:
            if f.key == state["last_object_key"]:
                skip_until = True
                continue
            if skip_until:
                new_files.append(f)
        all_files = new_files
        logger.info(f"Resuming from: skipping files before {state['last_object_key']}, {len(all_files)} remaining")

    success_count = state.get("migrated_files", 0)
    fail_count = len(state.get("failed_files", []))

    for obj in all_files:
        object_key = obj.key
        logger.info(f"Migrating: {object_key} ({obj.size} bytes)")

        result = migrate_file(oss_bucket, minio_client, minio_bucket, obj)

        if result:
            # Update DB URL
            new_url = f"https://{settings.MINIO_ENDPOINT}/{minio_bucket}/{object_key}"
            update_db_url(object_key, new_url)
            success_count += 1
            logger.info(f"  OK: {object_key}")
        else:
            fail_count += 1
            state["failed_files"].append(object_key)
            logger.error(f"  FAILED: {object_key}")

        state["last_object_key"] = object_key
        state["migrated_files"] = success_count
        save_state(state)

    elapsed = time.time() - start_time
    logger.info(f"Migration complete in {elapsed:.1f}s")
    logger.info(f"Success: {success_count}, Failed: {fail_count}")
    logger.info(f"State saved to: {STATE_FILE}")


def verify():
    """Verify migration: compare OSS and Minio files"""
    oss_bucket = get_oss_client()
    minio_client, minio_bucket = get_minio_client()

    logger.info("Verifying migration...")

    # List files from both
    oss_files = {}
    marker = ""
    while True:
        batch = list_oss_files(oss_bucket, start_after=marker if marker else "")
        if not batch:
            break
        for obj in batch:
            oss_files[obj.key] = obj.size
        marker = batch[-1].key
        if len(batch) < BATCH_SIZE:
            break

    minio_files = {}
    for obj in minio_client.list_objects(minio_bucket, recursive=True):
        minio_files[obj.object_name] = obj.size

    # Compare
    oss_only = set(oss_files.keys()) - set(minio_files.keys())
    minio_only = set(minio_files.keys()) - set(oss_files.keys())
    common = set(oss_files.keys()) & set(minio_files.keys())

    size_mismatch = []
    for key in common:
        if oss_files[key] != minio_files[key]:
            size_mismatch.append((key, oss_files[key], minio_files[key]))

    logger.info(f"OSS files: {len(oss_files)}")
    logger.info(f"Minio files: {len(minio_files)}")
    logger.info(f"Files only in OSS: {len(oss_only)}")
    logger.info(f"Files only in Minio: {len(minio_only)}")
    logger.info(f"Size mismatches: {len(size_mismatch)}")

    if oss_only:
        logger.warning("Files missing from Minio:")
        for k in list(oss_only)[:20]:
            logger.warning(f"  {k}")
    if minio_only:
        logger.warning("Extra files in Minio:")
        for k in list(minio_only)[:20]:
            logger.warning(f"  {k}")
    if size_mismatch:
        logger.warning("Size mismatches:")
        for k, oss_size, minio_size in size_mismatch[:20]:
            logger.warning(f"  {k}: OSS={oss_size}, Minio={minio_size}")

    if not oss_only and not size_mismatch:
        logger.info("Verification PASSED: All files match")
    else:
        logger.warning("Verification FAILED: There are discrepancies")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Storage Migration: Aliyun OSS -> Minio")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not migrate")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.verify:
        verify()
    else:
        migrate(resume=args.resume)


if __name__ == "__main__":
    main()
