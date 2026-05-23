"""
OSS Version History Service

Manages version history for Markdown files stored in OSS.
Versions are stored in a separate prefix: versions/{user_id}/{original_path}/{timestamp}_{version_id}.md
"""

import os
import io
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from app.services.oss_service import oss_service

logger = logging.getLogger(__name__)


class OssVersionService:
    """Service for managing OSS file version history"""

    def __init__(self):
        self.max_versions = 100  # Maximum versions per file
        self.version_prefix = "versions"

    def _get_version_path(self, user_id: str, file_path: str, version_id: str) -> str:
        """Generate version storage path"""
        return f"{self.version_prefix}/{user_id}/{file_path}/{version_id}.md"

    def create_version(
        self,
        user_id: str,
        file_path: str,
        content: str,
        content_preview: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Create a new version of a file.

        Returns:
            Tuple of (success: bool, version_id: str)
        """
        if not oss_service.is_available():
            return False, ""

        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            version_id = f"{timestamp}_{os.urandom(4).hex()}"
            version_path = self._get_version_path(user_id, file_path, version_id)

            preview = content_preview or content[:200] if content else ""
            metadata = {
                "created-at": timestamp,
                "content-preview": preview[:200],
                "original-path": file_path,
            }

            content_bytes = content.encode("utf-8")
            file_obj = io.BytesIO(content_bytes)

            oss_service.upload_file(
                object_name=version_path,
                data=file_obj,
                size=len(content_bytes),
                content_type="text/markdown",
                uploaded_by="system",
                metadata=metadata,
            )

            # Cleanup old versions if needed
            self._cleanup_old_versions(user_id, file_path)

            return True, version_id

        except Exception as e:
            logger.error("Error creating version: %s", e)
            return False, ""

    def list_versions(
        self, user_id: str, file_path: str, limit: int = 20, offset: int = 0
    ) -> List[dict]:
        """
        List all versions for a file.

        Returns:
            List of version info dicts
        """
        if not oss_service.is_available():
            return []

        try:
            prefix = f"{self.version_prefix}/{user_id}/{file_path}/"
            versions = []

            for item in oss_service.list_files(prefix=prefix, max_keys=1000):
                version_id = os.path.splitext(os.path.basename(item["key"]))[0]

                # Parse version ID (timestamp_random)
                parts = version_id.split("_")
                timestamp = parts[0] if parts else ""

                # Get metadata via head_object
                preview = ""
                head = oss_service.head_object(item["key"])
                if head:
                    preview = head.get("x-oss-meta-content-preview", "")

                versions.append(
                    {
                        "version_id": version_id,
                        "created_at": self._format_timestamp(timestamp),
                        "size": item["size"],
                        "content_preview": preview,
                    }
                )

            # Sort by version_id (descending - newest first)
            versions.sort(key=lambda x: x["version_id"], reverse=True)

            # Apply pagination
            return versions[offset : offset + limit]

        except Exception as e:
            logger.error("Error listing versions: %s", e)
            return []

    def read_version(
        self, user_id: str, file_path: str, version_id: str
    ) -> Tuple[bool, str]:
        """
        Read a specific version's content.

        Returns:
            Tuple of (success: bool, content: str)
        """
        if not oss_service.is_available():
            return False, ""

        try:
            version_path = self._get_version_path(user_id, file_path, version_id)
            result = oss_service.get_object(version_path)
            content = result.read().decode("utf-8")
            return True, content

        except Exception as e:
            logger.error("Error reading version: %s", e)
            return False, ""

    def rollback_to_version(
        self, user_id: str, file_path: str, version_id: str
    ) -> Tuple[bool, str]:
        """
        Rollback to a specific version.
        Creates a new version with the rolled-back content.

        Returns:
            Tuple of (success: bool, new_version_id: str)
        """
        if not oss_service.is_available():
            return False, ""

        try:
            # Read the version content
            success, content = self.read_version(user_id, file_path, version_id)
            if not success:
                return False, ""

            # Restore the file content
            content_bytes = content.encode("utf-8")
            file_obj = io.BytesIO(content_bytes)

            oss_service.upload_file(
                object_name=file_path,
                data=file_obj,
                size=len(content_bytes),
                content_type="text/markdown",
                uploaded_by=user_id,
            )

            # Create a new version recording the rollback
            rollback_preview = f"[Rollback to version {version_id}] {content[:150]}"
            success, new_version_id = self.create_version(
                user_id, file_path, content, content_preview=rollback_preview
            )

            return success, new_version_id

        except Exception as e:
            logger.error("Error rolling back: %s", e)
            return False, ""

    def delete_version(self, user_id: str, file_path: str, version_id: str) -> bool:
        """
        Delete a specific version.

        Returns:
            True if successful
        """
        if not oss_service.is_available():
            return False

        try:
            version_path = self._get_version_path(user_id, file_path, version_id)
            oss_service.delete_file(version_path)
            return True

        except Exception as e:
            logger.error("Error deleting version: %s", e)
            return False

    def _cleanup_old_versions(self, user_id: str, file_path: str):
        """Remove old versions if exceeding max_versions limit"""
        try:
            prefix = f"{self.version_prefix}/{user_id}/{file_path}/"
            versions = []

            for item in oss_service.list_files(prefix=prefix, max_keys=1000):
                versions.append(item["key"])

            if len(versions) > self.max_versions:
                versions.sort()
                versions_to_delete = versions[: len(versions) - self.max_versions]

                for version_key in versions_to_delete:
                    try:
                        oss_service.delete_file(version_key)
                    except Exception:
                        pass

        except Exception as e:
            logger.error("Error cleaning up old versions: %s", e)

    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp string to ISO format"""
        try:
            if len(timestamp) >= 14:
                dt = datetime.strptime(timestamp[:14], "%Y%m%d%H%M%S")
                return dt.isoformat()
        except Exception:
            pass
        return timestamp


# Singleton instance
oss_version_service = OssVersionService()
