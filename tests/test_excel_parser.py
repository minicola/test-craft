# tests/test_excel_parser.py
from parsers.excel_parser import _match_columns, _parse_steps, _normalize_priority


def test_match_columns():
    header = ["模块", "用例名称", "操作步骤", "预期结果", "优先级"]
    result = _match_columns(header)
    assert result["module"] == 0
    assert result["title"] == 1
    assert result["steps"] == 2
    assert result["expected"] == 3
    assert result["priority"] == 4


def test_parse_steps():
    text = "1. 点击登录按钮\n2. 输入用户名\n3. 点击确定"
    result = _parse_steps(text)
    assert result == ["点击登录按钮", "输入用户名", "点击确定"]


def test_parse_steps_chinese_numbering():
    text = "1、打开页面\n2、填写表单"
    result = _parse_steps(text)
    assert result == ["打开页面", "填写表单"]


def test_normalize_priority():
    assert _normalize_priority("P0") == "P0"
    assert _normalize_priority("高") == "P0"
    assert _normalize_priority("high") == "P0"
    assert _normalize_priority("中") == "P1"
    assert _normalize_priority("") == "P2"
    assert _normalize_priority("低") == "P3"
