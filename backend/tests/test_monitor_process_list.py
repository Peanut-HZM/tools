"""进程列表：类型判定与顶部汇总口径

覆盖两个真实缺陷：
1. ``_detect_project_type`` 用 ``startswith("go")`` 判定 Go，
   把 "Google Chrome" / "Google Chrome Helper" 全部误判成 Go。
2. 原实现只返回 ``type_summary`` 且过滤掉 Other / 单进程类型，
   前端拿不到任何「全量汇总」，页面顶部空着，看不出当前进程整体情况。
"""

import pytest

from app.services import system_monitor_service as svc


class _FakeProc:
    """最小可用的 psutil 进程替身"""

    def __init__(self, pid, name, cmdline=None, cpu=0.0, rss=1024, threads=1,
                 username="tester", create_time=1_700_000_000):
        self.pid = pid
        self._name = name
        self._cmdline = cmdline or []
        self._cpu = cpu
        self._rss = rss
        self._threads = threads
        self.info = {
            "pid": pid,
            "name": name,
            "username": username,
            "status": "running",
            "create_time": create_time,
            "memory_percent": 0.5,
            "memory_info": type("M", (), {"rss": rss, "vms": rss * 2})(),
            "num_threads": threads,
        }

    def cmdline(self):
        return list(self._cmdline)

    def cpu_percent(self, interval=None):
        return self._cpu


# ---------------------------------------------------------------- 类型判定


@pytest.mark.parametrize(
    "name,cmdline,expected",
    [
        # 回归：Google Chrome 曾被 startswith("go") 误判成 Go
        ("Google Chrome", [], "Browser"),
        ("Google Chrome Helper (Aperitif Renderer)", [], "Browser"),
        ("Google Chrome Helper", [], "Browser"),
        ("Chromium", [], "Browser"),
        # Electron 系
        ("Paseo Helper (Renderer)", [], "Electron"),
        ("Open Design Helper", [], "Electron"),
        # 真正的 Go 工具
        ("go", [], "Go"),
        ("gofmt", [], "Go"),
        # macOS .app 内进程：Electron 应用与普通桌面应用
        ("Open Design", ["/Applications/Open Design.app/Contents/MacOS/Open Design"], "Desktop"),
        ("Paseo", ["/Applications/Paseo.app/Contents/MacOS/Paseo"], "Desktop"),
        # 常见运行时
        ("python3.12", ["python3.12", "-m", "uvicorn", "app.main:app"], "FastAPI"),
        ("node", ["node", "vite.js"], "Vite"),
        ("java", ["java", "-jar", "app.jar"], "Java"),
    ],
)
def test_detect_project_type(name, cmdline, expected):
    assert svc._detect_project_type(name, _FakeProc(1, name, cmdline)) == expected


# ---------------------------------------------------------------- 汇总口径


def _install_fake_processes(monkeypatch, procs):
    """让 process_iter 返回给定替身（并让预热用的 sleep 立即返回）"""
    monkeypatch.setattr(svc.psutil, "process_iter", lambda attrs=None: list(procs))
    monkeypatch.setattr(svc.time, "sleep", lambda _s: None)
    monkeypatch.setattr(svc.psutil, "cpu_count", lambda logical=True: 8)


def test_summary_totals_cover_all_processes(monkeypatch):
    procs = [
        _FakeProc(1, "Google Chrome", cpu=30.0, rss=100 * 1024 * 1024),
        _FakeProc(2, "python3.12", ["python3.12", "-m", "uvicorn"], cpu=20.0, rss=50 * 1024 * 1024),
        _FakeProc(3, "some-binary", cpu=10.0, rss=10 * 1024 * 1024),
    ]
    _install_fake_processes(monkeypatch, procs)

    data = svc.get_process_list(page_size=50)
    summary = data["summary"]

    assert summary["process_count"] == 3
    assert summary["cpu_percent_total"] == pytest.approx(60.0)
    # 单核口径 60% ÷ 8 核 = 整机 7.5%
    assert summary["cpu_percent_of_machine"] == pytest.approx(7.5)
    assert summary["memory_rss_total"] == 160 * 1024 * 1024
    assert summary["logical_cpus"] == 8
    assert len(summary["top_cpu"]) == 3
    assert summary["top_cpu"][0]["name"] == "Google Chrome"


def test_type_summary_keeps_other_and_single_process_types(monkeypatch):
    """类型汇总不能过滤 Other / 单进程类型，否则份额之和与总数对不上"""
    procs = [
        _FakeProc(1, "Google Chrome", cpu=30.0),
        _FakeProc(2, "some-binary", cpu=5.0),  # 会被判成 Other，且只有 1 个
    ]
    _install_fake_processes(monkeypatch, procs)

    data = svc.get_process_list(page_size=50)
    types = {t["type"]: t for t in data["type_summary"]}

    assert "Other" in types, "Other 必须出现在类型汇总里"
    assert types["Other"]["count"] == 1
    assert types["Browser"]["count"] == 1
    # 份额之和应等于 summaries 的总 CPU
    assert sum(t["cpu_percent"] for t in data["type_summary"]) == pytest.approx(
        data["summary"]["cpu_percent_total"]
    )


def test_summary_reflects_filters(monkeypatch):
    """搜索 / 类型筛选后，汇总必须跟着变（否则顶部数字与列表内容不一致）"""
    procs = [
        _FakeProc(1, "Google Chrome", cpu=30.0, rss=100 * 1024 * 1024),
        _FakeProc(2, "python3.12", ["python3.12", "-m", "uvicorn"], cpu=20.0, rss=50 * 1024 * 1024),
    ]
    _install_fake_processes(monkeypatch, procs)

    only_browser = svc.get_process_list(page_size=50, project_type="Browser")
    assert only_browser["summary"]["process_count"] == 1
    assert only_browser["summary"]["cpu_percent_total"] == pytest.approx(30.0)
    assert [t["type"] for t in only_browser["type_summary"]] == ["Browser"]

    searched = svc.get_process_list(page_size=50, search="python")
    assert searched["summary"]["process_count"] == 1
    assert searched["summary"]["cpu_percent_total"] == pytest.approx(20.0)


def test_search_matches_command_line(monkeypatch):
    """搜索应同时匹配命令行（原来只匹配进程名）"""
    procs = [
        _FakeProc(1, "python3.12", ["python3.12", "-m", "uvicorn", "app.main:app"], cpu=1.0),
        _FakeProc(2, "node", ["node", "vite.js"], cpu=1.0),
    ]
    _install_fake_processes(monkeypatch, procs)

    hit = svc.get_process_list(page_size=50, search="uvicorn")
    assert hit["total"] == 1
    assert hit["processes"][0]["pid"] == 1
