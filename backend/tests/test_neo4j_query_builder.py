"""Cypher 查询构建器纯函数测试。

断言返回的 Cypher 字符串包含预期子句、参数全部为 dict、动态片段经白名单校验。
"""
import pytest

from app.services.neo4j import query_builder


class TestBuildSampleQuery:
    def test_single_label(self):
        cypher, params = query_builder.build_sample_query(
            labels=["Person"], rel_types=[], node_limit_per_label=200, rel_limit=500
        )
        assert "MATCH (n:Person)" in cypher
        assert "LIMIT 200" in cypher
        assert "LIMIT 500" in cypher
        assert isinstance(params, dict)

    def test_multiple_labels_union(self):
        cypher, params = query_builder.build_sample_query(
            labels=["Person", "Movie"], rel_types=[], node_limit_per_label=100, rel_limit=50
        )
        assert "MATCH (n:Person)" in cypher
        assert "MATCH (n:Movie)" in cypher
        assert "UNION" in cypher
        assert isinstance(params, dict)

    def test_empty_labels_samples_all(self):
        cypher, params = query_builder.build_sample_query(
            labels=[], rel_types=[], node_limit_per_label=10, rel_limit=20
        )
        assert "MATCH (n) RETURN n" in cypher
        assert isinstance(params, dict)

    def test_rel_type_filter(self):
        cypher, params = query_builder.build_sample_query(
            labels=["Person"], rel_types=["ACTED_IN"], node_limit_per_label=5, rel_limit=10
        )
        assert "MATCH (a)-[r:ACTED_IN]->(b)" in cypher
        assert isinstance(params, dict)

    def test_rel_type_filter_union(self):
        cypher, params = query_builder.build_sample_query(
            labels=["Person"], rel_types=["ACTED_IN", "DIRECTED"], node_limit_per_label=5, rel_limit=10
        )
        assert "MATCH (a)-[r:ACTED_IN|DIRECTED]->(b)" in cypher
        assert isinstance(params, dict)

    def test_internal_relationships_only(self):
        """只返回已采样节点之间的内部边（WHERE elementId(a) IN ...）。"""
        cypher, _ = query_builder.build_sample_query(
            labels=["Person"], rel_types=[], node_limit_per_label=5, rel_limit=10
        )
        assert "elementId(a) IN" in cypher
        assert "elementId(b) IN" in cypher

    def test_rejects_injection_in_label(self):
        with pytest.raises(ValueError):
            query_builder.build_sample_query(
                labels=["Person` DELETE ALL"], rel_types=[], node_limit_per_label=5, rel_limit=10
            )

    def test_rejects_injection_in_rel_type(self):
        with pytest.raises(ValueError):
            query_builder.build_sample_query(
                labels=["Person"], rel_types=["T` DELETE ALL"], node_limit_per_label=5, rel_limit=10
            )


class TestBuildExpandQuery:
    def test_direction_in(self):
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="in", rel_types=None, limit=50, offset=0
        )
        assert "MATCH (m)-[r]->(n)" in cypher
        assert "elementId(n) = $node_id" in cypher
        assert params == {"node_id": "abc", "offset": 0, "limit": 50}

    def test_direction_out(self):
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="out", rel_types=None, limit=50, offset=0
        )
        assert "MATCH (n)-[r]->(m)" in cypher

    def test_direction_both(self):
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="both", rel_types=None, limit=50, offset=0
        )
        assert "MATCH (n)-[r]-(m)" in cypher

    def test_rel_types_filter(self):
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="in", rel_types=["T"], limit=50, offset=0
        )
        assert "MATCH (m)-[r:T]->(n)" in cypher

    def test_expand_main_query_has_no_count(self):
        """主查询不含 count 子查询（total 单独统计，超时降级 null）。"""
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="both", rel_types=None, limit=50, offset=0
        )
        assert "count {" not in cypher
        assert "SKIP $offset LIMIT $limit" in cypher

    def test_expand_count_query(self):
        cypher, params = query_builder.build_expand_count_query(
            node_id="abc", direction="in", rel_types=None
        )
        assert "count(r) AS total" in cypher
        assert "MATCH (m)-[r]->(n)" in cypher
        assert params == {"node_id": "abc"}

    def test_expand_count_query_with_rel_types(self):
        cypher, params = query_builder.build_expand_count_query(
            node_id="abc", direction="out", rel_types=["T"]
        )
        assert "MATCH (n)-[r:T]->(m)" in cypher

    def test_skip_limit_params(self):
        cypher, params = query_builder.build_expand_query(
            node_id="abc", direction="both", rel_types=None, limit=10, offset=20
        )
        assert "SKIP $offset LIMIT $limit" in cypher
        assert params["offset"] == 20
        assert params["limit"] == 10

    def test_rejects_invalid_direction(self):
        with pytest.raises(ValueError):
            query_builder.build_expand_query(
                node_id="abc", direction="invalid", rel_types=None, limit=10, offset=0
            )


class TestBuildSearchQuery:
    def test_contains_and_limit(self):
        cypher, params = query_builder.build_search_query(q="Tom", limit=20)
        assert "CONTAINS $q" in cypher
        assert "LIMIT $limit" in cypher
        assert params == {"q": "Tom", "limit": 20}
