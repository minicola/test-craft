# TestCraft Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个基于 Streamlit 的 AI 测试用例生成工具，支持解析 XMind/Excel/截图/JAR 输入，通过可配置的大模型 API 生成 UI 操作用例和代码级补充用例，导出 Excel。

**Architecture:** Python + Streamlit 单体应用。文件解析层处理多种输入格式，AI 分析层通过三阶段 Prompt 策略生成用例，输出层支持页面展示和 Excel 导出。大模型 API 采用 OpenAI 兼容协议统一调用，Claude 单独适配。

**Tech Stack:** Python 3.9+, Streamlit, openai, anthropic, xmindparser, openpyxl, Pillow

---

### Task 1: 项目初始化与依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.gitignore`

**Step 1: 初始化 git 仓库**

```bash
cd /Users/macpro/project/tester
git init
```

**Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
venv/
.streamlit/secrets.toml
tmp/
*.jar
decompiled/
```

**Step 3: 创建 requirements.txt**

```
streamlit>=1.30.0
openai>=1.12.0
anthropic>=0.18.0
xmindparser>=1.0.0
openpyxl>=3.1.0
Pillow>=10.0.0
```

**Step 4: 创建 config.py**

```python
from dataclasses import dataclass


@dataclass
class AIConfig:
    provider: str  # "openai_compatible" or "claude"
    api_url: str
    api_key: str
    model_name: str
```

**Step 5: 安装依赖**

```bash
pip3 install -r requirements.txt
```

**Step 6: 创建目录结构**

```bash
mkdir -p parsers ai generators tests
touch parsers/__init__.py ai/__init__.py generators/__init__.py tests/__init__.py
```

**Step 7: Commit**

```bash
git add .gitignore requirements.txt config.py parsers/__init__.py ai/__init__.py generators/__init__.py tests/__init__.py
git commit -m "chore: 初始化项目结构与依赖"
```

---

### Task 2: XMind 解析器

**Files:**
- Create: `parsers/xmind_parser.py`
- Create: `tests/test_xmind_parser.py`

**Step 1: 编写 xmind_parser.py**

```python
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


def _extract_cases(node: dict, path: list[str], cases: list[dict]):
    """递归遍历 XMind 节点树，叶子节点视为用例。"""
    title = node.get("title", "").strip()
    children = node.get("topics", [])

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
```

**Step 2: 编写测试（验证结构正确性）**

```python
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
```

**Step 3: 运行测试**

```bash
python3 -m pytest tests/test_xmind_parser.py -v
```
Expected: 3 PASSED

**Step 4: Commit**

```bash
git add parsers/xmind_parser.py tests/test_xmind_parser.py
git commit -m "feat: 添加 XMind 测试用例解析器"
```

---

### Task 3: Excel 解析器

**Files:**
- Create: `parsers/excel_parser.py`
- Create: `tests/test_excel_parser.py`

**Step 1: 编写 excel_parser.py**

```python
from openpyxl import load_workbook

# 常见列名映射
COLUMN_MAPPINGS = {
    "module": ["模块", "所属模块", "功能模块", "module"],
    "title": ["用例名称", "用例标题", "测试用例", "标题", "title", "name"],
    "precondition": ["前置条件", "前提条件", "precondition"],
    "steps": ["操作步骤", "测试步骤", "步骤", "steps"],
    "expected": ["预期结果", "期望结果", "expected"],
    "priority": ["优先级", "级别", "priority"],
}


def parse_excel(file_path: str) -> list[dict]:
    """解析 Excel 文件，提取测试用例。"""
    wb = load_workbook(file_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(cell).strip() if cell else "" for cell in rows[0]]
    col_map = _match_columns(header)

    cases = []
    for row in rows[1:]:
        row_data = list(row)
        if all(cell is None for cell in row_data):
            continue

        steps_raw = _get_cell(row_data, col_map.get("steps"))
        steps = _parse_steps(steps_raw) if steps_raw else []

        cases.append({
            "id": "",
            "module": _get_cell(row_data, col_map.get("module")) or "未分类",
            "title": _get_cell(row_data, col_map.get("title")) or "",
            "precondition": _get_cell(row_data, col_map.get("precondition")) or "",
            "steps": steps,
            "expected": _get_cell(row_data, col_map.get("expected")) or "",
            "priority": _normalize_priority(_get_cell(row_data, col_map.get("priority"))),
            "source": "excel",
        })
    wb.close()
    return [c for c in cases if c["title"]]


def _match_columns(header: list[str]) -> dict[str, int]:
    """将表头列名匹配到标准字段。"""
    col_map = {}
    for field, aliases in COLUMN_MAPPINGS.items():
        for i, col_name in enumerate(header):
            if col_name.lower() in [a.lower() for a in aliases]:
                col_map[field] = i
                break
    return col_map


def _get_cell(row: list, index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    val = row[index]
    return str(val).strip() if val is not None else ""


def _parse_steps(text: str) -> list[str]:
    """解析步骤文本，支持换行和编号格式。"""
    lines = text.replace("\r\n", "\n").split("\n")
    steps = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 去掉开头的编号（如 "1." "1、" "1)" "步骤1："）
        import re
        line = re.sub(r"^[\d]+[.、)）:：]\s*", "", line)
        if line:
            steps.append(line)
    return steps


def _normalize_priority(val: str) -> str:
    if not val:
        return "P2"
    val = val.upper().strip()
    if val in ("P0", "P1", "P2", "P3"):
        return val
    if "高" in val or "high" in val.lower():
        return "P0"
    if "中" in val or "medium" in val.lower():
        return "P1"
    if "低" in val or "low" in val.lower():
        return "P3"
    return "P2"
```

**Step 2: 编写测试**

```python
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
```

**Step 3: 运行测试**

```bash
python3 -m pytest tests/test_excel_parser.py -v
```
Expected: 4 PASSED

**Step 4: Commit**

```bash
git add parsers/excel_parser.py tests/test_excel_parser.py
git commit -m "feat: 添加 Excel 测试用例解析器"
```

---

### Task 4: JAR 反编译与代码提取

**Files:**
- Create: `parsers/jar_parser.py`
- Create: `tests/test_jar_parser.py`

**Step 1: 编写 jar_parser.py**

```python
import os
import re
import subprocess
import tempfile
from pathlib import Path


def decompile_jar(jar_path: str) -> str:
    """用 cfr 反编译 JAR，返回输出目录路径。"""
    output_dir = tempfile.mkdtemp(prefix="testcraft_decompile_")
    cmd = ["java", "-jar", _get_cfr_path(), jar_path, "--outputdir", output_dir]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"反编译失败: {result.stderr}")
    return output_dir


def _get_cfr_path() -> str:
    """获取 cfr jar 路径。优先检查项目 tools 目录，其次 PATH。"""
    local_cfr = os.path.join(os.path.dirname(__file__), "..", "tools", "cfr.jar")
    if os.path.exists(local_cfr):
        return os.path.abspath(local_cfr)
    raise FileNotFoundError(
        "未找到 cfr.jar。请下载 cfr 到 tools/cfr.jar: "
        "https://github.com/leibnitz27/cfr/releases"
    )


def extract_key_classes(decompiled_dir: str) -> list[dict]:
    """从反编译目录中提取关键类（Controller/Service）的源码。"""
    results = []
    for java_file in Path(decompiled_dir).rglob("*.java"):
        filename = java_file.name
        if _is_key_class(filename):
            content = java_file.read_text(encoding="utf-8", errors="ignore")
            class_type = _classify_file(filename)
            results.append({
                "file": filename,
                "type": class_type,
                "content": content,
                "annotations": _extract_annotations(content),
                "methods": _extract_methods(content),
            })
    return results


def _is_key_class(filename: str) -> bool:
    lower = filename.lower()
    return any(
        kw in lower
        for kw in ["controller", "service", "serviceimpl", "resource", "endpoint"]
    )


def _classify_file(filename: str) -> str:
    lower = filename.lower()
    if "controller" in lower or "resource" in lower or "endpoint" in lower:
        return "controller"
    return "service"


def _extract_annotations(content: str) -> list[str]:
    """提取 Spring 相关注解。"""
    pattern = r"@(RestController|Controller|RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|Valid|NotNull|NotBlank|NotEmpty|Size|Min|Max|Pattern|PathVariable|RequestParam|RequestBody)\b"
    return list(set(re.findall(pattern, content)))


def _extract_methods(content: str) -> list[dict]:
    """提取方法签名和关键逻辑信息。"""
    methods = []
    # 匹配 public/protected 方法
    method_pattern = r"((?:@\w+(?:\([^)]*\))?\s*\n\s*)*)(public|protected)\s+[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)"
    for match in re.finditer(method_pattern, content):
        annotations = match.group(1).strip()
        method_name = match.group(3)

        # 找到方法体（简单匹配大括号）
        start = match.end()
        body = _extract_method_body(content, start)

        methods.append({
            "name": method_name,
            "annotations": annotations,
            "has_validation": bool(re.search(r"@(Valid|NotNull|NotBlank|NotEmpty)", annotations)),
            "has_branches": bool(re.search(r"\b(if|switch)\b", body)),
            "has_exception_handling": bool(re.search(r"\b(try|throw)\b", body)),
            "body_preview": body[:500] if len(body) > 500 else body,
        })
    return methods


def _extract_method_body(content: str, start: int) -> str:
    """从起始位置提取方法体（大括号匹配）。"""
    brace_count = 0
    body_start = content.find("{", start)
    if body_start == -1:
        return ""
    for i in range(body_start, min(body_start + 5000, len(content))):
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                return content[body_start:i + 1]
    return content[body_start:body_start + 2000]


def prepare_code_for_ai(classes: list[dict], max_chars: int = 30000) -> list[str]:
    """将代码切片为适合 AI 处理的块。"""
    chunks = []
    current_chunk = ""

    for cls in classes:
        content = cls["content"]
        if len(content) > max_chars:
            # 大文件按方法切片
            for method in cls["methods"]:
                piece = f"// File: {cls['file']} - Method: {method['name']}\n{method['body_preview']}\n\n"
                if len(current_chunk) + len(piece) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = piece
                else:
                    current_chunk += piece
        else:
            if len(current_chunk) + len(content) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = f"// File: {cls['file']}\n{content}\n\n"
            else:
                current_chunk += f"// File: {cls['file']}\n{content}\n\n"

    if current_chunk:
        chunks.append(current_chunk)
    return chunks
```

**Step 2: 编写测试**

```python
# tests/test_jar_parser.py
from parsers.jar_parser import (
    _is_key_class,
    _classify_file,
    _extract_annotations,
    _extract_methods,
    prepare_code_for_ai,
)


def test_is_key_class():
    assert _is_key_class("UserController.java")
    assert _is_key_class("OrderService.java")
    assert _is_key_class("PayServiceImpl.java")
    assert not _is_key_class("UserDTO.java")
    assert not _is_key_class("Constants.java")


def test_classify_file():
    assert _classify_file("UserController.java") == "controller"
    assert _classify_file("UserResource.java") == "controller"
    assert _classify_file("UserService.java") == "service"
    assert _classify_file("UserServiceImpl.java") == "service"


def test_extract_annotations():
    code = '''
    @RestController
    @RequestMapping("/api/users")
    public class UserController {
        @PostMapping
        public User create(@Valid @RequestBody UserDTO dto) {}
    }
    '''
    annotations = _extract_annotations(code)
    assert "RestController" in annotations
    assert "RequestMapping" in annotations
    assert "Valid" in annotations
    assert "RequestBody" in annotations


def test_extract_methods():
    code = '''
    public String getName(String id) {
        if (id == null) {
            throw new IllegalArgumentException("id is null");
        }
        return "name";
    }
    '''
    methods = _extract_methods(code)
    assert len(methods) == 1
    assert methods[0]["name"] == "getName"
    assert methods[0]["has_branches"] is True
    assert methods[0]["has_exception_handling"] is True


def test_prepare_code_for_ai():
    classes = [
        {"file": "A.java", "content": "class A {}", "methods": []},
        {"file": "B.java", "content": "class B {}", "methods": []},
    ]
    chunks = prepare_code_for_ai(classes, max_chars=100)
    assert len(chunks) >= 1
    assert "A.java" in chunks[0]
```

**Step 3: 运行测试**

```bash
python3 -m pytest tests/test_jar_parser.py -v
```
Expected: 5 PASSED

**Step 4: Commit**

```bash
git add parsers/jar_parser.py tests/test_jar_parser.py
git commit -m "feat: 添加 JAR 反编译与代码提取器"
```

---

### Task 5: 统一 AI 客户端

**Files:**
- Create: `ai/client.py`

**Step 1: 编写 client.py**

```python
import base64
import json
from config import AIConfig


def create_client(config: AIConfig):
    """根据配置创建 AI 客户端。"""
    if config.provider == "claude":
        return ClaudeClient(config)
    return OpenAICompatibleClient(config)


class OpenAICompatibleClient:
    """OpenAI 兼容协议客户端（支持大多数国产模型）。"""

    def __init__(self, config: AIConfig):
        from openai import OpenAI
        self.client = OpenAI(api_key=config.api_key, base_url=config.api_url)
        self.model = config.model_name

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def chat_with_images(self, text: str, images_base64: list[str], temperature: float = 0.3) -> str:
        content = [{"type": "text", "text": text}]
        for img in images_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"},
            })
        messages = [{"role": "user", "content": content}]
        return self.chat(messages, temperature)


class ClaudeClient:
    """Anthropic Claude 客户端。"""

    def __init__(self, config: AIConfig):
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.api_key)
        self.model = config.model_name

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        # 将 OpenAI 格式的 messages 转换为 Claude 格式
        claude_messages = []
        system_text = ""
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                claude_messages.append(msg)

        kwargs = {"model": self.model, "max_tokens": 8192, "messages": claude_messages, "temperature": temperature}
        if system_text:
            kwargs["system"] = system_text.strip()

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def chat_with_images(self, text: str, images_base64: list[str], temperature: float = 0.3) -> str:
        content = [{"type": "text", "text": text}]
        for img in images_base64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img},
            })
        messages = [{"role": "user", "content": content}]
        return self.chat(messages, temperature)
```

**Step 2: Commit**

```bash
git add ai/client.py
git commit -m "feat: 添加统一 AI 客户端（OpenAI 兼容 + Claude）"
```

---

### Task 6: Prompt 模板

**Files:**
- Create: `ai/prompts.py`

**Step 1: 编写 prompts.py**

```python
PHASE1_REQUIREMENT_ANALYSIS = """你是一名资深测试工程师。请分析以下需求信息，输出功能点清单。

## 历史测试用例
{existing_cases}

## 任务
1. 分析需求截图中的 UI 页面结构（菜单、按钮、表单字段、表格列、弹窗等）
2. 列出所有可识别的功能点
3. 对比历史用例，标记每个功能点的覆盖状态

## 输出格式（严格 JSON）
```json
{{
  "pages": [
    {{
      "name": "页面名称",
      "elements": ["元素1", "元素2"],
      "functions": [
        {{
          "name": "功能点名称",
          "description": "功能描述",
          "covered": true/false,
          "coverage_note": "已有用例XXX覆盖 / 未覆盖"
        }}
      ]
    }}
  ]
}}
```"""

PHASE2_CODE_ANALYSIS = """你是一名资深 Java 测试工程师。请分析以下反编译的 Java 代码，提取测试关键信息。

## 代码
{code_chunk}

## 任务
1. 提取所有 API 接口（路径、HTTP方法、请求参数、返回类型）
2. 提取参数校验规则（@Valid、@NotNull、@Size 等注解约束）
3. 识别业务逻辑分支（if/switch 条件及其含义）
4. 识别异常处理（catch 的异常类型、throw 的场景）
5. 识别关键业务规则

## 输出格式（严格 JSON）
```json
{{
  "apis": [
    {{
      "path": "/api/xxx",
      "method": "POST",
      "params": [{{"name": "字段名", "type": "类型", "validation": "校验规则"}}],
      "description": "接口描述"
    }}
  ],
  "validations": ["规则1", "规则2"],
  "branches": [{{"condition": "条件", "description": "分支说明"}}],
  "exceptions": [{{"type": "异常类型", "scenario": "触发场景"}}],
  "business_rules": ["规则描述"]
}}
```"""

PHASE3_TESTCASE_GENERATION = """你是一名资深测试工程师，擅长编写可执行的 UI 测试用例。

## 需求分析结果
{requirement_analysis}

## 代码分析结果
{code_analysis}

## 历史测试用例
{existing_cases}

## 任务
基于以上信息，生成完整的测试用例集。要求：
1. **UI 操作用例**：每个步骤必须明确"点击/输入/选择"等具体操作和目标元素
2. **代码级补充用例**：基于代码分支和校验规则补充边界测试、异常测试
3. 避免与历史用例重复
4. 按功能模块分组
5. 设定合理的优先级（P0=核心流程，P1=重要功能，P2=边界条件，P3=异常场景）

## 用例步骤格式示例
好的步骤：
- 点击"规则管理"菜单
- 在"规则包名称"输入框输入"测试规则包"
- 点击"确定"按钮

不好的步骤：
- 进行操作（太模糊）
- 测试功能（没有具体动作）

## 输出格式（严格 JSON 数组）
```json
[
  {{
    "module": "模块名",
    "title": "用例标题",
    "precondition": "前置条件",
    "steps": ["步骤1", "步骤2", "步骤3"],
    "expected": "预期结果",
    "priority": "P0",
    "source": "screenshot/code/enhanced"
  }}
]
```

生成尽可能完整的用例，包括正向流程、反向测试、边界值测试、异常场景。"""
```

**Step 2: Commit**

```bash
git add ai/prompts.py
git commit -m "feat: 添加三阶段 Prompt 模板"
```

---

### Task 7: AI 分析编排器

**Files:**
- Create: `ai/analyzer.py`

**Step 1: 编写 analyzer.py**

```python
import base64
import json
from ai.client import create_client
from ai.prompts import PHASE1_REQUIREMENT_ANALYSIS, PHASE2_CODE_ANALYSIS, PHASE3_TESTCASE_GENERATION
from config import AIConfig


class TestCaseAnalyzer:
    """三阶段 AI 分析编排器。"""

    def __init__(self, config: AIConfig):
        self.client = create_client(config)

    def analyze_requirements(
        self,
        screenshots_base64: list[str],
        existing_cases: list[dict],
        progress_callback=None,
    ) -> dict:
        """阶段一：需求理解。"""
        if progress_callback:
            progress_callback("正在分析需求截图...")

        cases_text = self._format_existing_cases(existing_cases)
        prompt = PHASE1_REQUIREMENT_ANALYSIS.format(existing_cases=cases_text)

        if screenshots_base64:
            response = self.client.chat_with_images(prompt, screenshots_base64)
        else:
            response = self.client.chat([{"role": "user", "content": prompt}])

        return self._parse_json_response(response)

    def analyze_code(
        self,
        code_chunks: list[str],
        progress_callback=None,
    ) -> dict:
        """阶段二：代码分析。"""
        all_results = {
            "apis": [],
            "validations": [],
            "branches": [],
            "exceptions": [],
            "business_rules": [],
        }

        for i, chunk in enumerate(code_chunks):
            if progress_callback:
                progress_callback(f"正在分析代码... ({i + 1}/{len(code_chunks)})")

            prompt = PHASE2_CODE_ANALYSIS.format(code_chunk=chunk)
            response = self.client.chat([{"role": "user", "content": prompt}])
            result = self._parse_json_response(response)

            for key in all_results:
                all_results[key].extend(result.get(key, []))

        return all_results

    def generate_test_cases(
        self,
        requirement_analysis: dict,
        code_analysis: dict,
        existing_cases: list[dict],
        progress_callback=None,
    ) -> list[dict]:
        """阶段三：用例生成。"""
        if progress_callback:
            progress_callback("正在生成测试用例...")

        prompt = PHASE3_TESTCASE_GENERATION.format(
            requirement_analysis=json.dumps(requirement_analysis, ensure_ascii=False, indent=2),
            code_analysis=json.dumps(code_analysis, ensure_ascii=False, indent=2),
            existing_cases=self._format_existing_cases(existing_cases),
        )

        response = self.client.chat([{"role": "user", "content": prompt}])
        cases = self._parse_json_response(response)

        if isinstance(cases, list):
            return self._assign_ids(cases)
        if isinstance(cases, dict) and "test_cases" in cases:
            return self._assign_ids(cases["test_cases"])
        return []

    def run_full_analysis(
        self,
        screenshots_base64: list[str],
        existing_cases: list[dict],
        code_chunks: list[str],
        progress_callback=None,
    ) -> list[dict]:
        """运行完整的三阶段分析。"""
        # 阶段一
        req_analysis = self.analyze_requirements(screenshots_base64, existing_cases, progress_callback)

        # 阶段二（如果有代码）
        code_analysis = {}
        if code_chunks:
            code_analysis = self.analyze_code(code_chunks, progress_callback)

        # 阶段三
        return self.generate_test_cases(req_analysis, code_analysis, existing_cases, progress_callback)

    def _format_existing_cases(self, cases: list[dict]) -> str:
        if not cases:
            return "无历史用例"
        lines = []
        for c in cases[:50]:  # 限制数量避免超出 token
            steps = " -> ".join(c.get("steps", []))
            lines.append(f"- [{c.get('module', '')}] {c.get('title', '')}: {steps}")
        return "\n".join(lines)

    def _parse_json_response(self, response: str) -> dict | list:
        """从 AI 响应中提取 JSON。"""
        # 尝试从 markdown 代码块中提取
        import re
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        text = json_match.group(1) if json_match else response

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到第一个 { 或 [ 开始的 JSON
            for i, char in enumerate(text):
                if char in ("{", "["):
                    try:
                        return json.loads(text[i:])
                    except json.JSONDecodeError:
                        continue
            return {}

    def _assign_ids(self, cases: list[dict]) -> list[dict]:
        for i, case in enumerate(cases, 1):
            case["id"] = f"TC-{i:03d}"
        return cases
```

**Step 2: Commit**

```bash
git add ai/analyzer.py
git commit -m "feat: 添加三阶段 AI 分析编排器"
```

---

### Task 8: Excel 导出

**Files:**
- Create: `generators/excel_export.py`
- Create: `tests/test_excel_export.py`

**Step 1: 编写 excel_export.py**

```python
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


def export_to_excel(test_cases: list[dict]) -> io.BytesIO:
    """将测试用例导出为 Excel 文件（BytesIO 对象）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "测试用例"

    # 表头
    headers = ["用例编号", "所属模块", "用例标题", "优先级", "前置条件", "操作步骤", "预期结果", "用例来源"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # 数据行
    source_map = {"screenshot": "截图推导", "code": "代码补充", "enhanced": "历史增强",
                  "xmind": "XMind导入", "excel": "Excel导入", "ai_generated": "AI生成"}

    for row_idx, case in enumerate(test_cases, 2):
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(case.get("steps", [])))
        source = source_map.get(case.get("source", ""), case.get("source", ""))

        values = [
            case.get("id", ""),
            case.get("module", ""),
            case.get("title", ""),
            case.get("priority", "P2"),
            case.get("precondition", ""),
            steps_text,
            case.get("expected", ""),
            source,
        ]

        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = thin_border

    # 设置列宽
    col_widths = [12, 15, 30, 8, 20, 45, 30, 12]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # 冻结首行
    ws.freeze_panes = "A2"

    # 添加筛选器
    ws.auto_filter.ref = f"A1:H{len(test_cases) + 1}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
```

**Step 2: 编写测试**

```python
# tests/test_excel_export.py
from generators.excel_export import export_to_excel
from openpyxl import load_workbook
import io


def test_export_basic():
    cases = [
        {
            "id": "TC-001",
            "module": "登录模块",
            "title": "正常登录",
            "priority": "P0",
            "precondition": "用户已注册",
            "steps": ["打开登录页", "输入用户名", "输入密码", "点击登录"],
            "expected": "跳转到首页",
            "source": "screenshot",
        }
    ]
    output = export_to_excel(cases)
    assert isinstance(output, io.BytesIO)

    # 验证 Excel 内容
    wb = load_workbook(output)
    ws = wb.active
    assert ws.cell(row=1, column=1).value == "用例编号"
    assert ws.cell(row=2, column=1).value == "TC-001"
    assert ws.cell(row=2, column=3).value == "正常登录"
    assert "1. 打开登录页" in ws.cell(row=2, column=6).value
    assert ws.cell(row=2, column=8).value == "截图推导"


def test_export_empty():
    output = export_to_excel([])
    assert isinstance(output, io.BytesIO)
    wb = load_workbook(output)
    ws = wb.active
    assert ws.cell(row=1, column=1).value == "用例编号"
    assert ws.cell(row=2, column=1).value is None
```

**Step 3: 运行测试**

```bash
python3 -m pytest tests/test_excel_export.py -v
```
Expected: 2 PASSED

**Step 4: Commit**

```bash
git add generators/excel_export.py tests/test_excel_export.py
git commit -m "feat: 添加 Excel 导出功能"
```

---

### Task 9: Streamlit 主界面

**Files:**
- Create: `app.py`

**Step 1: 编写 app.py**

```python
import base64
import io
import streamlit as st
from config import AIConfig
from parsers.xmind_parser import parse_xmind
from parsers.excel_parser import parse_excel
from parsers.jar_parser import decompile_jar, extract_key_classes, prepare_code_for_ai
from ai.analyzer import TestCaseAnalyzer
from generators.excel_export import export_to_excel
import tempfile
import os

st.set_page_config(page_title="TestCraft - AI 测试用例生成", layout="wide")
st.title("TestCraft - AI 测试用例生成工具")

# ===== 侧边栏：API 配置 =====
with st.sidebar:
    st.header("API 配置")
    provider = st.selectbox("API 提供商", ["OpenAI 兼容", "Claude"], index=0)
    api_url = st.text_input(
        "API URL",
        value="https://api.openai.com/v1" if provider == "OpenAI 兼容" else "https://api.anthropic.com",
    )
    api_key = st.text_input("API Key", type="password")
    model_name = st.text_input("模型名称", value="gpt-4o" if provider == "OpenAI 兼容" else "claude-sonnet-4-20250514")

    st.divider()
    st.caption("配置说明：大多数国产模型（通义千问、DeepSeek 等）选择 'OpenAI 兼容'，填入对应的 API URL 即可。")

config = AIConfig(
    provider="claude" if provider == "Claude" else "openai_compatible",
    api_url=api_url,
    api_key=api_key,
    model_name=model_name,
)

# ===== 主区域：Tab 布局 =====
tab_upload, tab_progress, tab_results = st.tabs(["📁 文件上传", "⏳ 分析过程", "📋 测试用例"])

# ----- Tab1: 文件上传 -----
with tab_upload:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("历史测试用例")
        history_files = st.file_uploader(
            "上传 XMind 或 Excel 文件",
            type=["xmind", "xlsx"],
            accept_multiple_files=True,
            key="history",
        )

    with col2:
        st.subheader("需求截图")
        screenshot_files = st.file_uploader(
            "上传需求截图",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="screenshots",
        )
        if screenshot_files:
            for img in screenshot_files:
                st.image(img, caption=img.name, width=300)

    with col3:
        st.subheader("JAR 文件")
        jar_file = st.file_uploader("上传 JAR 文件", type=["jar"], key="jar")

    st.divider()
    start_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

# ----- 初始化 session state -----
if "test_cases" not in st.session_state:
    st.session_state.test_cases = []
if "progress_logs" not in st.session_state:
    st.session_state.progress_logs = []

# ----- 执行分析 -----
if start_btn:
    if not api_key:
        st.error("请先在侧边栏配置 API Key")
    elif not screenshot_files and not history_files and not jar_file:
        st.error("请至少上传一种文件")
    else:
        st.session_state.progress_logs = []
        st.session_state.test_cases = []

        with tab_progress:
            progress_container = st.container()
            progress_bar = st.progress(0)
            status_text = st.empty()

            def log_progress(msg):
                st.session_state.progress_logs.append(msg)
                status_text.text(msg)

            # Step 1: 解析历史用例
            log_progress("📂 正在解析历史测试用例...")
            progress_bar.progress(10)
            existing_cases = []
            if history_files:
                for f in history_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as tmp:
                        tmp.write(f.read())
                        tmp_path = tmp.name
                    try:
                        if f.name.endswith(".xmind"):
                            existing_cases.extend(parse_xmind(tmp_path))
                        elif f.name.endswith(".xlsx"):
                            existing_cases.extend(parse_excel(tmp_path))
                    finally:
                        os.unlink(tmp_path)
                log_progress(f"✅ 解析完成，共 {len(existing_cases)} 条历史用例")

            # Step 2: 处理截图
            progress_bar.progress(20)
            screenshots_b64 = []
            if screenshot_files:
                log_progress("🖼️ 正在处理需求截图...")
                for img_file in screenshot_files:
                    img_bytes = img_file.read()
                    screenshots_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
                log_progress(f"✅ 已处理 {len(screenshots_b64)} 张截图")

            # Step 3: 反编译 JAR
            progress_bar.progress(30)
            code_chunks = []
            if jar_file:
                log_progress("🔧 正在反编译 JAR 文件...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jar") as tmp:
                    tmp.write(jar_file.read())
                    jar_path = tmp.name
                try:
                    decompiled_dir = decompile_jar(jar_path)
                    classes = extract_key_classes(decompiled_dir)
                    code_chunks = prepare_code_for_ai(classes)
                    log_progress(f"✅ 反编译完成，提取 {len(classes)} 个关键类，分为 {len(code_chunks)} 个代码块")
                except Exception as e:
                    log_progress(f"⚠️ JAR 反编译失败: {e}（将跳过代码分析）")
                finally:
                    os.unlink(jar_path)

            # Step 4: AI 分析
            progress_bar.progress(40)
            log_progress("🤖 正在调用 AI 分析...")
            try:
                analyzer = TestCaseAnalyzer(config)

                def update_progress(msg):
                    log_progress(f"🤖 {msg}")

                cases = analyzer.run_full_analysis(
                    screenshots_base64=screenshots_b64,
                    existing_cases=existing_cases,
                    code_chunks=code_chunks,
                    progress_callback=update_progress,
                )
                st.session_state.test_cases = cases
                progress_bar.progress(100)
                log_progress(f"🎉 分析完成！共生成 {len(cases)} 条测试用例")
            except Exception as e:
                log_progress(f"❌ AI 分析失败: {e}")

            # 显示日志
            with progress_container:
                for log in st.session_state.progress_logs:
                    st.write(log)

# ----- Tab3: 测试用例展示 -----
with tab_results:
    cases = st.session_state.test_cases
    if not cases:
        st.info("暂无测试用例，请先上传文件并点击"开始分析"")
    else:
        # 筛选器
        col_f1, col_f2, col_f3 = st.columns(3)
        modules = sorted(set(c.get("module", "未分类") for c in cases))
        sources = sorted(set(c.get("source", "") for c in cases))
        priorities = sorted(set(c.get("priority", "P2") for c in cases))

        with col_f1:
            sel_module = st.selectbox("模块筛选", ["全部"] + modules)
        with col_f2:
            sel_source = st.selectbox("来源筛选", ["全部"] + sources)
        with col_f3:
            sel_priority = st.selectbox("优先级筛选", ["全部"] + priorities)

        # 筛选
        filtered = cases
        if sel_module != "全部":
            filtered = [c for c in filtered if c.get("module") == sel_module]
        if sel_source != "全部":
            filtered = [c for c in filtered if c.get("source") == sel_source]
        if sel_priority != "全部":
            filtered = [c for c in filtered if c.get("priority") == sel_priority]

        st.write(f"共 **{len(filtered)}** 条用例（总计 {len(cases)} 条）")

        # 用例展示
        for case in filtered:
            with st.expander(f"**{case.get('id', '')}** | {case.get('title', '')} [{case.get('priority', '')}]"):
                st.write(f"**模块：** {case.get('module', '')}")
                st.write(f"**来源：** {case.get('source', '')}")
                if case.get("precondition"):
                    st.write(f"**前置条件：** {case.get('precondition')}")
                st.write("**操作步骤：**")
                for i, step in enumerate(case.get("steps", []), 1):
                    st.write(f"  {i}. {step}")
                st.write(f"**预期结果：** {case.get('expected', '')}")

        # 导出
        st.divider()
        excel_data = export_to_excel(filtered)
        st.download_button(
            label="📥 导出 Excel",
            data=excel_data,
            file_name="test_cases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
```

**Step 2: 手动测试运行**

```bash
cd /Users/macpro/project/tester && streamlit run app.py
```
Expected: 浏览器打开，显示 TestCraft 界面，侧边栏有 API 配置，主区域有三个 Tab。

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: 添加 Streamlit 主界面"
```

---

### Task 10: 集成验证与收尾

**Step 1: 运行所有测试**

```bash
cd /Users/macpro/project/tester && python3 -m pytest tests/ -v
```
Expected: All tests PASSED

**Step 2: 下载 cfr 反编译器**

```bash
mkdir -p tools
# 用户需手动下载 cfr.jar 到 tools/ 目录
# https://github.com/leibnitz27/cfr/releases
```

**Step 3: 创建 README 启动说明（可选，用户要求时创建）**

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: 集成验证完成"
```
