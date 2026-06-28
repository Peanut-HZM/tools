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
    """测试 get_used_categories 只返回被在线工具引用的分类"""

    def test_only_used_categories_returned(self):
        from app.services.tools_service import tools_service
        from app.models import Category

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [  # SELECT DISTINCT c.* FROM tool_categories c JOIN tools t ...
                {"id": "c1", "name": "AI工具", "description": None,
                 "icon": None, "sort_order": 1,
                 "created_at": None, "updated_at": None},
                {"id": "c2", "name": "实用工具", "description": None,
                 "icon": None, "sort_order": 2,
                 "created_at": None, "updated_at": None},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            # 绕过缓存
            from app.services.tools_service import _tools_cache
            _tools_cache.invalidate("used_categories")

            result = tools_service.get_used_categories()

        assert [c.name for c in result] == ["AI工具", "实用工具"]
        # SQL 必须 JOIN tools 且过滤 status='online'
        sql = fake_cursor.calls[0][0]
        assert "JOIN tools" in sql
        assert "t.status = 'online'" in sql

    def test_empty_when_no_tools(self):
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [[]]  # 没有工具 → 没有分类

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            from app.services.tools_service import _tools_cache
            _tools_cache.invalidate("used_categories")
            result = tools_service.get_used_categories()

        assert result == []


class TestDeleteCategoryProtection:
    """测试 delete_category 的 409 保护"""

    def test_delete_category_with_tools_raises_409(self):
        from fastapi import HTTPException
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"name": "AI工具"}],
            [{"count": 3}],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            with pytest.raises(HTTPException) as exc_info:
                tools_service.delete_category("some-id")
            assert exc_info.value.status_code == 409

        write_calls = [c for c in fake_cursor.calls
                       if c[0].startswith("UPDATE tool_categories SET deleted")]
        assert write_calls == []

    def test_delete_category_without_tools_succeeds(self):
        from app.services.tools_service import tools_service, _tools_cache

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"name": "AI工具"}],
            [{"count": 0}],
            [],
        ]
        fake_cursor.rowcount = 1

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             patch.object(_tools_cache, "invalidate") as mock_inv:
            result = tools_service.delete_category("some-id")

        assert result is True
        mock_inv.assert_any_call("used_categories")
        mock_inv.assert_any_call("categories")


class TestUpdateCategoryCascade:
    """测试 update_category 改名级联"""

    def test_rename_without_cascade_raises_409(self):
        from fastapi import HTTPException
        from app.services.tools_service import tools_service
        from app.models import CategoryCreateRequest

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"name": "AI工具"}],
            [{"count": 2}],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            with pytest.raises(HTTPException) as exc_info:
                tools_service.update_category("c1", CategoryCreateRequest(name="AI工具2"))
            assert exc_info.value.status_code == 409

    def test_rename_with_cascade_updates_tools(self):
        from app.services.tools_service import tools_service, _tools_cache
        from app.models import CategoryCreateRequest

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [{"name": "AI工具"}],
            [{"count": 2}],
            [],
            [{"id": "c1", "name": "AI工具2", "description": None, "icon": None, "sort_order": 0}],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"), \
             patch.object(_tools_cache, "invalidate") as mock_inv:
            result = tools_service.update_category("c1", CategoryCreateRequest(name="AI工具2"), cascade=True)

        assert result is not None
        assert result.name == "AI工具2"
        update_tool_calls = [c for c in fake_cursor.calls
                             if c[0].startswith("UPDATE tools SET category")]
        assert len(update_tool_calls) == 1
        assert update_tool_calls[0][1] == ("AI工具2", "AI工具")
        mock_inv.assert_any_call("used_categories")


class TestGetCategoriesWithToolCount:
    """测试 get_categories_with_tool_count 返回使用计数"""

    def test_returns_all_categories_with_counts(self):
        from app.services.tools_service import tools_service

        fake_cursor = FakeCursor()
        fake_cursor.next_results = [
            [
                {"id": "c1", "name": "AI工具", "sort_order": 1, "tool_count": 3},
                {"id": "c2", "name": "实用工具", "sort_order": 2, "tool_count": 0},
            ],
        ]

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("app.services.tools_service.get_pooled_db_connection", return_value=fake_conn), \
             patch("app.services.tools_service.release_db_connection"):
            result = tools_service.get_categories_with_tool_count()

        assert len(result) == 2
        assert result[0]["name"] == "AI工具"
        assert result[0]["tool_count"] == 3
        assert result[1]["tool_count"] == 0
