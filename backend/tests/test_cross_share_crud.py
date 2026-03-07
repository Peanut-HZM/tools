"""
Integration tests for CrossShare CRUD operations
"""
import pytest
import os
import sys
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers by registering and logging in"""
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a test user
    register_response = client.post("/api/auth/register", json={
        "username": unique_username,
        "email": f"{unique_username}@example.com",
        "password": "testpassword123"
    })

    if register_response.status_code == 200:
        token = register_response.json().get("token")
    else:
        # User might already exist, try login
        login_response = client.post("/api/auth/login", json={
            "username": unique_username,
            "password": "testpassword123"
        })
        token = login_response.json().get("token")

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def device_id(client, auth_headers):
    """Register a test device and return device ID"""
    response = client.post(
        "/api/cross-share/devices",
        json={
            "device_name": "Test Device",
            "device_type": "desktop",
            "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
        },
        headers=auth_headers
    )
    if response.status_code == 200:
        return response.json().get("id")
    return None


class TestCrossShareMessageCRUD:
    """Integration tests for CrossShare message CRUD operations"""

    def test_send_message(self, client, auth_headers, device_id):
        """Test sending a text message"""
        request_headers = auth_headers.copy()
        if device_id:
            request_headers["X-Device-Id"] = device_id

        response = client.post(
            "/api/cross-share/messages",
            json={
                "content": "Test message content",
                "message_type": "text"
            },
            headers=request_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Test message content"
        assert data["message_type"] == "text"
        assert "id" in data

    def test_get_messages(self, client, auth_headers):
        """Test getting message list"""
        # Send a message first
        client.post(
            "/api/cross-share/messages",
            json={"content": "Test message", "message_type": "text"},
            headers=auth_headers
        )

        # Get messages
        response = client.get(
            "/api/cross-share/messages",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_update_message(self, client, auth_headers):
        """Test editing a message"""
        # Send a message first
        send_response = client.post(
            "/api/cross-share/messages",
            json={"content": "Original content", "message_type": "text"},
            headers=auth_headers
        )
        message_id = send_response.json().get("id")

        # Update message
        update_response = client.put(
            f"/api/cross-share/messages/{message_id}",
            json={"content": "Updated content"},
            headers=auth_headers
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["content"] == "Updated content"

    def test_delete_message(self, client, auth_headers):
        """Test deleting a message"""
        # Send a message first
        send_response = client.post(
            "/api/cross-share/messages",
            json={"content": "Message to delete", "message_type": "text"},
            headers=auth_headers
        )
        message_id = send_response.json().get("id")

        # Delete message
        delete_response = client.delete(
            f"/api/cross-share/messages/{message_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        # Verify message is deleted
        get_response = client.get("/api/cross-share/messages", headers=auth_headers)
        messages = get_response.json().get("messages", [])
        message_ids = [msg["id"] for msg in messages]
        assert message_id not in message_ids

    def test_mark_message_read(self, client, auth_headers):
        """Test marking a message as read"""
        # Send a message first
        send_response = client.post(
            "/api/cross-share/messages",
            json={"content": "Unread message", "message_type": "text"},
            headers=auth_headers
        )
        message_id = send_response.json().get("id")

        # Mark as read
        read_response = client.post(
            f"/api/cross-share/messages/{message_id}/read",
            headers=auth_headers
        )

        assert read_response.status_code == 200
        data = read_response.json()
        assert data["is_read"] == True

    def test_update_message_unauthorized(self, client, auth_headers):
        """Test that user cannot update another user's message"""
        # Send a message with first user
        send_response = client.post(
            "/api/cross-share/messages",
            json={"content": "Message", "message_type": "text"},
            headers=auth_headers
        )
        message_id = send_response.json().get("id")

        # Create another user
        unique_username = f"otheruser_{uuid.uuid4().hex[:8]}"
        client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        other_headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': unique_username, 'password': 'testpassword123'}).json().get('token')}"}

        # Try to update with other user - should fail
        update_response = client.put(
            f"/api/cross-share/messages/{message_id}",
            json={"content": "Hacked content"},
            headers=other_headers
        )

        assert update_response.status_code == 404  # Returns 404 because message not found for other user


class TestCrossShareFileCRUD:
    """Integration tests for CrossShare file CRUD operations"""

    def test_get_files_empty(self, client, auth_headers):
        """Test getting empty file list"""
        response = client.get(
            "/api/cross-share/files",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert isinstance(data["files"], list)

    def test_get_upload_token(self, client, auth_headers):
        """Test getting upload token"""
        response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "test.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "upload_url" in data
        assert "file_id" in data

    def test_get_file_stats(self, client, auth_headers):
        """Test getting storage stats"""
        response = client.get(
            "/api/cross-share/files/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_size" in data
        assert "used_quota" in data
        assert "available_quota" in data

    def test_update_file_name(self, client, auth_headers):
        """Test renaming a file"""
        # Create file record first
        upload_response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "original.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )
        file_id = upload_response.json().get("file_id")

        # Update file name
        update_response = client.put(
            f"/api/cross-share/files/{file_id}",
            json={"file_name": "renamed.txt"},
            headers=auth_headers
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["file_name"] == "renamed.txt"

    def test_delete_file(self, client, auth_headers):
        """Test deleting a file"""
        # Create file record first
        upload_response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "to_delete.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )
        file_id = upload_response.json().get("file_id")

        # Delete file
        delete_response = client.delete(
            f"/api/cross-share/files/{file_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        # Verify file is deleted (soft delete - should not appear in list)
        get_response = client.get("/api/cross-share/files", headers=auth_headers)
        files = get_response.json().get("files", [])
        file_ids = [f["id"] for f in files]
        assert file_id not in file_ids

    def test_get_file_unauthorized(self, client, auth_headers):
        """Test that user cannot access another user's file"""
        # Create file with first user
        upload_response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "private.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )
        file_id = upload_response.json().get("file_id")

        # Create another user
        unique_username = f"otheruser_{uuid.uuid4().hex[:8]}"
        client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        other_headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': unique_username, 'password': 'testpassword123'}).json().get('token')}"}

        # Try to get file with other user - should fail
        get_response = client.get(
            f"/api/cross-share/files/{file_id}",
            headers=other_headers
        )

        assert get_response.status_code == 404  # Returns 404 because file not found for other user

    def test_update_file_unauthorized(self, client, auth_headers):
        """Test that user cannot update another user's file"""
        # Create file with first user
        upload_response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "original.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )
        file_id = upload_response.json().get("file_id")

        # Create another user
        unique_username = f"otheruser_{uuid.uuid4().hex[:8]}"
        client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        other_headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': unique_username, 'password': 'testpassword123'}).json().get('token')}"}

        # Try to update with other user - should fail
        update_response = client.put(
            f"/api/cross-share/files/{file_id}",
            json={"file_name": "hacked.txt"},
            headers=other_headers
        )

        assert update_response.status_code == 404

    def test_delete_file_unauthorized(self, client, auth_headers):
        """Test that user cannot delete another user's file"""
        # Create file with first user
        upload_response = client.post(
            "/api/cross-share/files/upload",
            json={
                "file_name": "private.txt",
                "file_size": 1024,
                "file_type": "text/plain"
            },
            headers=auth_headers
        )
        file_id = upload_response.json().get("file_id")

        # Create another user
        unique_username = f"otheruser_{uuid.uuid4().hex[:8]}"
        client.post("/api/auth/register", json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123"
        })
        other_headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': unique_username, 'password': 'testpassword123'}).json().get('token')}"}

        # Try to delete with other user - should fail
        delete_response = client.delete(
            f"/api/cross-share/files/{file_id}",
            headers=other_headers
        )

        assert delete_response.status_code == 404


class TestCrossShareDeviceCRUD:
    """Integration tests for CrossShare device CRUD operations"""

    def test_register_device(self, client, auth_headers):
        """Test registering a device"""
        response = client.post(
            "/api/cross-share/devices",
            json={
                "device_name": "Test Device",
                "device_type": "desktop",
                "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["device_name"] == "Test Device"

    def test_get_devices(self, client, auth_headers):
        """Test getting device list"""
        # Register a device first
        client.post(
            "/api/cross-share/devices",
            json={
                "device_name": "Test Device",
                "device_type": "desktop",
                "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
            },
            headers=auth_headers
        )

        # Get devices
        response = client.get(
            "/api/cross-share/devices",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "total" in data

    def test_update_device(self, client, auth_headers):
        """Test updating a device"""
        # Register device first
        register_response = client.post(
            "/api/cross-share/devices",
            json={
                "device_name": "Original Name",
                "device_type": "desktop",
                "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
            },
            headers=auth_headers
        )
        device_id = register_response.json().get("id")

        # Update device
        update_response = client.put(
            f"/api/cross-share/devices/{device_id}",
            json={"device_name": "Updated Name"},
            headers=auth_headers
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["device_name"] == "Updated Name"

    def test_ping_device(self, client, auth_headers):
        """Test pinging a device to update last seen time"""
        # Register device first
        register_response = client.post(
            "/api/cross-share/devices",
            json={
                "device_name": "Ping Test",
                "device_type": "desktop",
                "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
            },
            headers=auth_headers
        )
        device_id = register_response.json().get("id")

        # Ping device
        ping_response = client.post(
            f"/api/cross-share/devices/{device_id}/ping",
            headers=auth_headers
        )

        assert ping_response.status_code == 200

    def test_delete_device(self, client, auth_headers):
        """Test deleting a device"""
        # Register device first
        register_response = client.post(
            "/api/cross-share/devices",
            json={
                "device_name": "To Delete",
                "device_type": "desktop",
                "device_token": f"test-token-{uuid.uuid4().hex[:16]}"
            },
            headers=auth_headers
        )
        device_id = register_response.json().get("id")

        # Delete device
        delete_response = client.delete(
            f"/api/cross-share/devices/{device_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        # Verify device is deleted
        get_response = client.get("/api/cross-share/devices", headers=auth_headers)
        devices = get_response.json().get("devices", [])
        device_ids = [d["id"] for d in devices]
        assert device_id not in device_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
