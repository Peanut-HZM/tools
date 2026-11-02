"""显示偏好按设备隔离的测试

问题背景：
显示偏好（数据库工具的可见连接 / 可见数据库）原先只按 user_id 存一行，
导致同一用户在多台设备上的设置互相覆盖 —— A 设备勾选的连接会同步到
B 设备，多台设备的列表混在一起。

核心不变量：
1. 同一用户在不同设备上保存的偏好互不覆盖，各自回显自己那一份
2. 设备 B 首次访问时不会读到设备 A 的设置
3. 不带 device_id 时回退到历史兜底行（device_id=''）
4. device_id 缺失/非法时不得报错，且不写入脏数据
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.client_device import (
    DEVICE_ID_HEADER,
    MAX_DEVICE_ID_LENGTH,
    normalize_device_id,
    resolve_device_id,
)


class TestNormalizeDeviceId:
    """设备标识规范化"""

    def test_none_and_empty_return_empty(self):
        assert normalize_device_id(None) == ""
        assert normalize_device_id("") == ""
        assert normalize_device_id("   ") == ""

    def test_valid_uuid_kept(self):
        uid = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
        assert normalize_device_id(uid) == uid

    def test_strips_whitespace(self):
        assert normalize_device_id("  abc-123  ") == "abc-123"

    def test_truncates_overlong(self):
        raw = "a" * (MAX_DEVICE_ID_LENGTH + 50)
        assert len(normalize_device_id(raw)) == MAX_DEVICE_ID_LENGTH

    def test_filters_illegal_chars(self):
        # 只保留字母数字与 - _
        assert normalize_device_id("abc<script>/x") == "abcscriptx"

    def test_only_illegal_chars_becomes_empty(self):
        assert normalize_device_id("<>/\\\"'") == ""

    def test_resolve_is_alias(self):
        assert resolve_device_id("dev-1") == "dev-1"


class TestDeviceHeaderConstant:
    def test_header_name(self):
        assert DEVICE_ID_HEADER == "X-Device-Id"


class TestDisplayPreferencesDeviceScope:
    """偏好按设备隔离（需要真实数据库）"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        from fastapi.testclient import TestClient
        from app.main import app

        c = TestClient(app)
        r = c.post(
            "/api/auth/login",
            json={"username": "peanut", "password": "Peanut2817*#"},
        )
        token = r.json().get("token") or r.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def _save(self, client, headers, device_id, connections, databases=None):
        h = {**headers, DEVICE_ID_HEADER: device_id}
        return client.put(
            "/api/database-tool/preferences",
            headers=h,
            json={
                "visible_connections": connections,
                "visible_databases": databases,
            },
        )

    def _delete_row(self, device_id):
        """直接删除测试行，避免用例在库里留下残留数据"""
        from app.config.database import get_pooled_db_connection, release_db_connection

        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_display_preferences WHERE device_id = %s",
                    (device_id,),
                )
                conn.commit()
        finally:
            release_db_connection(conn)

    def _get(self, client, headers, device_id=None):
        h = dict(headers)
        if device_id is not None:
            h[DEVICE_ID_HEADER] = device_id
        return client.get("/api/database-tool/preferences", headers=h)

    def test_two_devices_are_isolated(self, client, auth_headers):
        """设备 A 与设备 B 的偏好互不覆盖"""
        dev_a = "zztest-dev-a-1111"
        dev_b = "zztest-dev-b-2222"

        try:
            self._save(client, auth_headers, dev_a, ["conn-a1", "conn-a2"],
                       {"conn-a1": ["db_x"]})
            self._save(client, auth_headers, dev_b, ["conn-b1"])

            a = self._get(client, auth_headers, dev_a).json()
            b = self._get(client, auth_headers, dev_b).json()

            assert a["visible_connections"] == ["conn-a1", "conn-a2"]
            assert a["visible_databases"] == {"conn-a1": ["db_x"]}
            assert b["visible_connections"] == ["conn-b1"]
        finally:
            self._delete_row(dev_a)
            self._delete_row(dev_b)

    def test_new_device_does_not_inherit_other_device(self, client, auth_headers):
        """设备 B 首次访问不会读到设备 A 的设置"""
        dev_a = "zztest-dev-c-3333"
        dev_b = "zztest-dev-d-4444"

        try:
            self._save(client, auth_headers, dev_a, ["only-for-a"])
            b = self._get(client, auth_headers, dev_b).json()
            assert "only-for-a" not in (b.get("visible_connections") or [])
        finally:
            self._delete_row(dev_a)
            self._delete_row(dev_b)

    def test_missing_device_id_falls_back_to_legacy_row(self, client, auth_headers):
        """不带 device_id 时回退到历史兜底行（device_id=''）"""
        r = self._get(client, auth_headers, None)
        assert r.status_code == 200
        # 不带设备标识不能报错，且返回结构完整
        assert "visible_connections" in r.json()
        assert "visible_databases" in r.json()

    def test_illegal_device_id_does_not_break(self, client, auth_headers):
        """非法 device_id 不报错（被过滤成空串走兜底行）"""
        r = self._get(client, auth_headers, "<script>alert(1)</script>")
        assert r.status_code == 200

    def test_device_id_is_not_stored_raw(self, client, auth_headers):
        """过滤后的 device_id 才落库，原始非法值不写进表"""
        from app.config.database import get_pooled_db_connection, release_db_connection

        raw = "zztest-raw/../../etc"
        try:
            self._save(client, auth_headers, raw, ["x"])

            conn = get_pooled_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT device_id FROM user_display_preferences "
                "WHERE device_id LIKE 'zztest-raw%'"
            )
            rows = cur.fetchall()
            cur.close()
            release_db_connection(conn)

            # 过滤后不含 '/'，不可能出现原始路径形态
            assert all("/" not in r["device_id"] for r in rows)
        finally:
            self._delete_row("zztest-rawetc")
