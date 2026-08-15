# backend/tests/test_monitor_models.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pydantic import ValidationError
import pytest
from app.models.monitor_models import (
    CreateMonitorServerRequest, MonitorServerResponse, ImportSSHRequest,
    AlertRuleCreateRequest, AlertRuleResponse, MonitorSettings,
)

def test_create_server_request_validation():
    req = CreateMonitorServerRequest(
        name="测试服务器", host="192.168.1.10", port=22,
        username="root", password="secret")
    assert req.server_type == "ssh"
    assert req.port == 22

def test_create_server_request_rejects_bad_port():
    with pytest.raises(ValidationError):
        CreateMonitorServerRequest(name="x", host="h", port=99999, username="u")

def test_import_ssh_request():
    assert ImportSSHRequest(ssh_config_id="abc").ssh_config_id == "abc"

def test_alert_rule_create():
    rule = AlertRuleCreateRequest(metric="cpu_percent", operator=">", threshold=90, duration=3)
    assert rule.server_id == "all"
    assert rule.duration == 3

def test_monitor_settings_defaults():
    s = MonitorSettings()
    assert s.webhook_url == ""
    assert s.collect_interval == 30
