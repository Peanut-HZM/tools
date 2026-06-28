"""
Tests for tools_service category dedup / validation / get_used_categories.

注意：这些测试是逻辑级单元测试，通过 mock psycopg2 连接来隔离业务逻辑。
"""
from unittest.mock import MagicMock, patch
import pytest


class FakeCursor:
    """模拟 psycopg2 DictCursor，记录所有 execute 调用"""

    def __init__(self):
        self.calls = []
        self.next_results = []
        self._rowcount = 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if self.next_results:
            self._result = self.next_results.pop(0)
        else:
            self._result = []

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None

    @property
    def rowcount(self):
        return self._rowcount

    @rowcount.setter
    def rowcount(self, value):
        self._rowcount = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestNormalizeCategoryVariants:
    """测试 _normalize_category_variants 合并空格变体的逻辑"""

    def test_merge_space_variant(self):
        """存在「AI工具」和「AI 工具」两条，应合并到 sort_order 较小的"""
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [  # SELECT id, name, sort_order FROM tool_categories
                {"id": "c1", "name": "AI工具", "sort_order": 1},
                {"id": "c2", "name": "AI 工具", "sort_order": 5},
            ],
            [],  # UPDATE tools 之后
            [],  # DELETE FROM tool_categories 之后
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            tools_service._normalize_category_variants(fake_conn)

        update_calls = [c for c in fake_cursor.calls if c[0].startswith("UPDATE tools SET category")]
        assert len(update_calls) == 1
        sql, params = update_calls[0]
        assert params[0] == "AI工具"
        assert set(params[1]) == {"AI 工具"}

        delete_calls = [c for c in fake_cursor.calls if c[0].startswith("DELETE FROM tool_categories")]
        assert len(delete_calls) == 1
        _, params = delete_calls[0]
        assert params[0] == ["c2"]

    def test_no_variants_noop(self):
        """没有变体时不应执行任何写入操作"""
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [
                {"id": "c1", "name": "AI工具", "sort_order": 1},
                {"id": "c3", "name": "实用工具", "sort_order": 2},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            tools_service._normalize_category_variants(fake_conn)

        write_calls = [c for c in fake_cursor.calls
                       if c[0].startswith("UPDATE tools SET category")
                       or c[0].startswith("DELETE FROM tool_categories")]
        assert write_calls == []


class TestValidateToolCategoryRefs:
    """测试 _validate_tool_category_refs 悬空引用校验"""

    def test_logs_error_for_dangling(self, caplog):
        """存在指向不存在分类的工具时，应记录 ERROR 日志"""
        import logging
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"category": "未分类X"}, {"category": "未分类Y"}],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             caplog.at_level(logging.ERROR, logger="app.services.tools_service"):
            tools_service._validate_tool_category_refs(fake_conn)

        assert any("未分类X" in r.message and "不存在的分类" in r.message for r in caplog.records)
        assert any("未分类Y" in r.message for r in caplog.records)

    def test_no_dangling_no_error(self, caplog):
        """没有悬空引用时不应记录 ERROR 日志"""
        import logging
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [[]]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             caplog.at_level(logging.ERROR, logger="app.services.tools_service"):
            tools_service._validate_tool_category_refs(fake_conn)

        assert not any("不存在的分类" in r.message for r in caplog.records)


class TestGetUsedCategories:
    """测试 get_used_categories 返回有在线工具的分类列表"""

    def test_returns_used_categories(self):
        """返回在线的、非空分类的去重列表"""
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [
                {"category": "文本工具"},
                {"category": "AI工具"},
                {"category": "开发工具"},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            result = tools_service.get_used_categories()

        assert result == ["文本工具", "AI工具", "开发工具"]

    def test_caches_result(self):
        """第二次调用应走缓存，不查询数据库"""
        from app.services.tools_service import tools_service, _tools_cache

        _tools_cache.invalidate("used_categories")

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [
                {"category": "文本工具"},
                {"category": "AI工具"},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            result1 = tools_service.get_used_categories()
            assert result1 == ["文本工具", "AI工具"]
            assert len(fake_cursor.calls) == 1

            # 第二次调用应走缓存，不产生新的 execute 调用
            result2 = tools_service.get_used_categories()
            assert result2 == ["文本工具", "AI工具"]
            assert len(fake_cursor.calls) == 1

    def test_returns_empty_when_no_online_tools(self):
        """没有在线工具时返回空列表"""
        from app.services.tools_service import tools_service, _tools_cache

        _tools_cache.invalidate("used_categories")

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [[]]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            result = tools_service.get_used_categories()

        assert result == []