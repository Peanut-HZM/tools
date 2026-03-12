"""
Aliyun OSS Service - Handles file uploads to Aliyun OSS and DB persistence
"""
import oss2
import logging
from typing import Optional, BinaryIO, List, Dict, Any
import os
from datetime import datetime
from app.config.config import settings
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)

class OssService:
    """Service for Aliyun OSS operations"""
    
    def __init__(self):
        """Initialize OssService with settings"""
        self.access_key_id = settings.ALIYUN_OSS_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_OSS_ACCESS_KEY_SECRET
        self.endpoint = settings.ALIYUN_OSS_ENDPOINT
        self.bucket_name = settings.ALIYUN_OSS_BUCKET_NAME
        
        self.bucket: Optional[oss2.Bucket] = None
        
        if self.access_key_id and self.access_key_secret and self.bucket_name:
            try:
                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
                logger.info(f"OSS Service initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OSS Service: {e}")
        else:
            logger.warning("OSS configuration is missing. OSS features will be disabled.")
            
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Create oss_files table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oss_files (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        file_path VARCHAR(500) NOT NULL UNIQUE,
                        url VARCHAR(500) NOT NULL,
                        file_type VARCHAR(50),
                        size BIGINT,
                        uploaded_by VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def upload_file(self, object_name: str, data: BinaryIO, size: int, content_type: str, uploaded_by: str = "system") -> Optional[str]:
        """
        Upload a file-like object to OSS and record in DB
        """
        if not self.bucket:
            logger.error("OSS Bucket not initialized")
            return None
            
        try:
            result = self.bucket.put_object(object_name, data)
            if result.status == 200:
                url = f"https://{self.bucket_name}.{self.endpoint}/{object_name}"
                
                # Record in DB
                self._save_file_record(
                    filename=os.path.basename(object_name),
                    file_path=object_name,
                    url=url,
                    file_type=content_type,
                    size=size,
                    uploaded_by=uploaded_by
                )
                
                return url
            else:
                logger.error(f"Failed to upload file. Status: {result.status}")
                return None
        except Exception as e:
            logger.error(f"Error uploading file to OSS: {e}")
            return None

    def _save_file_record(self, filename: str, file_path: str, url: str, file_type: str, size: int, uploaded_by: str):
        """Save file record to database"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO oss_files (filename, file_path, url, file_type, size, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_path) DO UPDATE SET
                        url = EXCLUDED.url,
                        file_type = EXCLUDED.file_type,
                        size = EXCLUDED.size,
                        created_at = CURRENT_TIMESTAMP
                """, (filename, file_path, url, file_type, size, uploaded_by))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving file record: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from OSS and DB
        """
        if not self.bucket:
            logger.error("OSS Bucket not initialized")
            return False
            
        try:
            # Delete from OSS
            self.bucket.delete_object(object_name)
            
            # Delete from DB
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM oss_files WHERE file_path = %s", (object_name,))
                conn.commit()
            except Exception as e:
                logger.error(f"Error deleting file record from DB: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
                    
            return True
        except Exception as e:
            logger.error(f"Error deleting file from OSS: {e}")
            return False
    
    def list_files_db(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List files from Database
        """
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM oss_files 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                
                rows = cur.fetchall()
                files = []
                for row in rows:
                    files.append({
                        "id": row['id'],
                        "name": row['filename'],
                        "path": row['file_path'],
                        "url": row['url'],
                        "type": row['file_type'],
                        "size": row['size'],
                        "uploaded_by": row['uploaded_by'],
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None
                    })
                return files
        except Exception as e:
            logger.error(f"Error listing files from DB: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        """
        List files in OSS (Legacy / Sync usage)
        Prefer list_files_db for UI display
        """
        # ... (keep existing implementation or redirect to DB)
        return self.list_files_db(limit=max_keys)

# Singleton instance
oss_service = OssService()
