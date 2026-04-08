# tests/test_xmind_parser.py
from parsers.xmind_parser import _extract_cases, _extract_priority


def test_extract_cases_leaf_node():
    node = {"title": "验证登录成功", "topics": []}
    cases = []
    _extract_cases(node, ["登录模块"], cases)
    assert len(cases) == 1
    assert cases[0]["title"] == "验证登录成功"
    assert cases[0]["module"] == "登录模块"
    assert cases[0]["source"] == "xmind"


def test_extract_cases_nested():
    node = {
        "title": "根节点",
        "topics": [
            {
                "title": "模块A",
                "topics": [
                    {"title": "用例1", "topics": []},
                    {"title": "用例2", "topics": []},
                ],
            }
        ],
    }
    cases = []
    _extract_cases(node, [], cases)
    assert len(cases) == 2
    assert cases[0]["module"] == "根节点"


def test_extract_priority():
    assert _extract_priority({"markers": ["priority-1"]}) == "P0"
    assert _extract_priority({"markers": ["priority-2"]}) == "P1"
    assert _extract_priority({"markers": []}) == "P2"
