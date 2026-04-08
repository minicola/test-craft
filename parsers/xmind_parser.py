import json
from xmindparser import xmind_to_dict


def parse_xmind(file_path: str) -> list[dict]:
    """解析 XMind 文件，提取测试用例结构。"""
    sheets = xmind_to_dict(file_path)
    test_cases = []
    for sheet in sheets:
        topic = sheet.get("topic", {})
        _extract_cases(topic, [], test_cases)
    return test_cases


def _extract_cases(node, path: list[str], cases: list[dict]):
    """递归遍历 XMind 节点树，叶子节点视为用例。"""
    if not isinstance(node, dict):
        return
    title = (node.get("title") or "").strip()
    children = node.get("topics") or []

    if not children and title:
        # 叶子节点 = 测试用例
        module = path[0] if path else "未分类"
        cases.append({
            "id": "",
            "module": module,
            "title": title,
            "precondition": "",
            "steps": [],
            "expected": "",
            "priority": _extract_priority(node),
            "source": "xmind",
        })
    else:
        current_path = path + [title] if title else path
        for child in children:
            _extract_cases(child, current_path, cases)


def _extract_priority(node: dict) -> str:
    """从 XMind 标记中提取优先级。"""
    markers = node.get("markers", [])
    for marker in markers:
        marker_str = str(marker).lower()
        if "priority-1" in marker_str:
            return "P0"
        if "priority-2" in marker_str:
            return "P1"
        if "priority-3" in marker_str:
            return "P2"
    return "P2"
