"""
课程平台 API 集成测试
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from tests.conftest import override_db, TestingSessionLocal
from app.models.user import User
from app.models.course_platform import Course, Category, Enrollment
from datetime import datetime
import jwt
from app.config.config import settings

client = TestClient(app)


@pytest.fixture
def test_user():
    """创建测试用户"""
    return {
        "id": "test-user-id",
        "username": "testuser",
        "email": "test@example.com"
    }


@pytest.fixture
def test_token(test_user):
    """生成测试 JWT token"""
    payload = {
        "user_id": test_user["id"],
        "username": test_user["username"],
        "exp": datetime.utcnow().replace(year=2099)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def auth_headers(test_token):
    """返回带认证的请求头"""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def test_category():
    """创建测试分类"""
    return {
        "name": "编程开发",
        "slug": "programming",
        "icon": "💻"
    }


@pytest.fixture
def test_course():
    """创建测试课程数据"""
    return {
        "title": "测试课程",
        "slug": "test-course",
        "description": "这是一个测试课程",
        "cover_image": "https://example.com/cover.jpg",
        "is_published": True
    }


@pytest.fixture(scope="function")
def db():
    """创建测试数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def setup_test_data(db, test_user, test_category, test_course):
    """设置测试数据"""
    # 创建用户
    user = User(
        id=test_user["id"],
        username=test_user["username"],
        email=test_user["email"]
    )
    db.add(user)

    # 创建分类
    category = Category(
        name=test_category["name"],
        slug=test_category["slug"],
        icon=test_category["icon"]
    )
    db.add(category)
    db.commit()

    # 创建课程
    course = Course(
        **test_course,
        category_id=category.id
    )
    db.add(course)
    db.commit()

    return {"user": user, "category": category, "course": course}


class TestCourseListAPI:
    """课程列表 API 测试"""

    def test_get_course_list_success(self, setup_test_data):
        """测试获取课程列表成功"""
        response = client.get("/api/courses?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
        assert "total" in data
        assert len(data["courses"]) >= 1

    def test_get_course_list_with_category(self, setup_test_data):
        """测试按分类筛选课程"""
        response = client.get("/api/courses?category=programming")
        assert response.status_code == 200
        data = response.json()
        assert len(data["courses"]) >= 1

    def test_get_course_list_with_search(self, setup_test_data):
        """测试搜索课程"""
        response = client.get("/api/courses?search=测试")
        assert response.status_code == 200
        data = response.json()
        assert len(data["courses"]) >= 1

    def test_get_course_list_sort_by_latest(self, setup_test_data):
        """测试按最新排序"""
        response = client.get("/api/courses?sort=latest")
        assert response.status_code == 200
        data = response.json()
        assert len(data["courses"]) >= 1

    def test_get_course_list_sort_by_hot(self, setup_test_data):
        """测试按热门排序"""
        response = client.get("/api/courses?sort=hot")
        assert response.status_code == 200
        data = response.json()


class TestCourseDetailAPI:
    """课程详情 API 测试"""

    def test_get_course_detail_success(self, setup_test_data):
        """测试获取课程详情成功"""
        response = client.get("/api/courses/test-course")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "test-course"
        assert data["title"] == "测试课程"
        assert "chapters" in data

    def test_get_course_detail_not_found(self):
        """测试课程不存在"""
        response = client.get("/api/courses/non-existent-course")
        assert response.status_code == 404

    def test_get_course_detail_increment_view_count(self, setup_test_data):
        """测试浏览次数累加"""
        response1 = client.get("/api/courses/test-course")
        response2 = client.get("/api/courses/test-course")
        assert response2.json()["statistics"]["view_count"] >= response1.json()["statistics"]["view_count"]


class TestCourseCategoriesAPI:
    """课程分类 API 测试"""

    def test_get_course_categories_success(self, setup_test_data):
        """测试获取课程分类"""
        response = client.get("/api/course-categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestEnrollmentAPI:
    """用户课程 API 测试"""

    def test_enroll_course_success(self, setup_test_data, auth_headers):
        """测试报名课程成功"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/courses/{course_id}/enroll",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["course_id"] == course_id
        assert data["status"] == "active"

    def test_enroll_course_duplicate(self, setup_test_data, auth_headers):
        """测试重复报名处理"""
        course_id = setup_test_data["course"].id
        # 第一次报名
        client.post(f"/api/courses/{course_id}/enroll", headers=auth_headers)
        # 第二次报名
        response = client.post(
            f"/api/courses/{course_id}/enroll",
            headers=auth_headers
        )
        assert response.status_code == 200  # 返回已报名记录

    def test_get_my_courses_success(self, setup_test_data, auth_headers):
        """测试获取我的课程"""
        course_id = setup_test_data["course"].id
        # 先报名
        client.post(f"/api/courses/{course_id}/enroll", headers=auth_headers)

        response = client.get("/api/my-courses", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
        assert len(data["courses"]) >= 1


class TestInteractionAPI:
    """互动统计 API 测试"""

    def test_like_course_success(self, setup_test_data, auth_headers):
        """测试点赞课程"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/courses/{course_id}/like",
            headers=auth_headers
        )
        assert response.status_code == 200
        # 验证统计数据更新
        detail_response = client.get("/api/courses/test-course")
        assert detail_response.json()["statistics"]["like_count"] >= 1

    def test_bookmark_course_success(self, setup_test_data, auth_headers):
        """测试收藏课程"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/courses/{course_id}/bookmark",
            headers=auth_headers
        )
        assert response.status_code == 200
        # 验证统计数据更新
        detail_response = client.get("/api/courses/test-course")
        assert detail_response.json()["statistics"]["bookmark_count"] >= 1

    def test_get_course_statistics(self, setup_test_data):
        """测试获取课程统计数据"""
        course_id = setup_test_data["course"].id
        response = client.get(f"/api/courses/{course_id}/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "view_count" in data
        assert "enroll_count" in data
        assert "like_count" in data
        assert "bookmark_count" in data


class TestReviewAPI:
    """课程评价 API 测试"""

    def test_submit_review_success(self, setup_test_data, auth_headers):
        """测试提交评价"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/courses/{course_id}/reviews",
            json={"rating": 5, "comment": "很好的课程！"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        assert data["comment"] == "很好的课程！"

    def test_get_course_reviews(self, setup_test_data, auth_headers):
        """测试获取评价列表"""
        course_id = setup_test_data["course"].id
        # 先提交评价
        client.post(
            f"/api/courses/{course_id}/reviews",
            json={"rating": 5, "comment": "测试评价"},
            headers=auth_headers
        )

        response = client.get(f"/api/courses/{course_id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_submit_review_duplicate(self, setup_test_data, auth_headers):
        """测试重复提交评价处理"""
        course_id = setup_test_data["course"].id
        # 第一次提交
        client.post(
            f"/api/courses/{course_id}/reviews",
            json={"rating": 5, "comment": "第一条评价"},
            headers=auth_headers
        )
        # 第二次提交（应该更新现有评价）
        response = client.post(
            f"/api/courses/{course_id}/reviews",
            json={"rating": 4, "comment": "更新后的评价"},
            headers=auth_headers
        )
        # 验证平均分更新
        detail_response = client.get("/api/courses/test-course")
        assert detail_response.json()["statistics"]["avg_rating"] == 4.0


class TestAdminCourseAPI:
    """课程管理 API 测试"""

    def test_admin_get_courses(self, setup_test_data, auth_headers):
        """测试管理员获取课程列表"""
        response = client.get("/api/admin/courses", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
        assert "total" in data

    def test_admin_create_course(self, setup_test_data, auth_headers):
        """测试管理员创建课程"""
        course_data = {
            "title": "新课程",
            "slug": "new-course",
            "description": "新课程描述",
            "category_id": 1,
            "is_published": False
        }
        response = client.post(
            "/api/admin/courses",
            json=course_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "新课程"
        assert data["slug"] == "new-course"

    def test_admin_update_course(self, setup_test_data, auth_headers):
        """测试管理员更新课程"""
        course_id = setup_test_data["course"].id
        update_data = {
            "title": "更新后的课程标题",
            "description": "更新后的描述"
        }
        response = client.put(
            f"/api/admin/courses/{course_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的课程标题"

    def test_admin_delete_course(self, setup_test_data, auth_headers):
        """测试管理员删除课程"""
        course_id = setup_test_data["course"].id
        response = client.delete(
            f"/api/admin/courses/{course_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        # 验证课程已删除
        get_response = client.get("/api/courses/test-course")
        assert get_response.status_code == 404

    def test_admin_publish_course(self, setup_test_data, auth_headers):
        """测试管理员发布课程"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/admin/courses/{course_id}/publish?publish=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # 验证发布状态
        detail_response = client.get("/api/courses/test-course")
        assert detail_response.json()["is_published"] is True

    def test_admin_unpublish_course(self, setup_test_data, auth_headers):
        """测试管理员取消发布课程"""
        course_id = setup_test_data["course"].id
        response = client.post(
            f"/api/admin/courses/{course_id}/publish?publish=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        # 验证发布状态
        detail_response = client.get("/api/courses/test-course")
        assert detail_response.json()["is_published"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
