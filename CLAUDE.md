# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

TestCraft —— AI 驱动的测试用例生成工具。分析历史测试用例、需求截图、Java JAR 包，自动生成可执行的 UI 测试用例并补充代码级覆盖。

- 语言：Python 3.9+
- UI 框架：Streamlit
- JAR 反编译依赖 Java 运行时 + CFR（需手动下载到 `tools/cfr.jar`）

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run app.py

# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_xmind_parser.py -v

# 运行单个测试函数
python -m pytest tests/test_excel_parser.py::test_parse_excel_basic -v
```

## 架构

四层架构，数据从上到下单向流动：

```
用户输入 (XMind / Excel / 截图 / JAR)
  → 解析层 parsers/        统一输出 TestCase dict 列表
  → AI 层 ai/              三阶段分析（需求理解 → 代码分析 → 用例生成）
  → 输出层 generators/     Excel 导出
  → 展示层 app.py          Streamlit UI + 筛选 + 导出
```

### 核心数据结构

所有模块围绕统一的 `TestCase` dict 协作：

```python
{
    "id": "TC-001",
    "module": str,
    "title": str,
    "precondition": str,
    "steps": [str],
    "expected": str,
    "priority": "P0" | "P1" | "P2" | "P3",
    "source": "xmind" | "excel" | "screenshot" | "code" | "enhanced" | "ai_generated"
}
```

### 关键模块职责

- **`parsers/xmind_parser.py`** — 递归遍历 XMind 树，叶节点为用例，从 marker 提取优先级
- **`parsers/excel_parser.py`** — 模糊匹配中英文列名，支持多种步骤编号格式和优先级别名
- **`parsers/jar_parser.py`** — 调用 CFR 反编译 → 筛选 Controller/Service 等关键类 → 提取注解和方法 → 按 30KB 分块
- **`ai/client.py`** — 工厂模式，`create_client()` 生产 OpenAI 兼容或 Claude 客户端
- **`ai/analyzer.py`** — 三阶段编排器：阶段1 需求理解（含截图视觉分析）→ 阶段2 代码分析 → 阶段3 用例生成
- **`ai/prompts.py`** — 三阶段的结构化 JSON Prompt 模板
- **`generators/excel_export.py`** — openpyxl 生成带样式/冻结/筛选的 Excel
- **`app.py`** — Streamlit 主入口，三 Tab 布局（上传 / 进度 / 结果），通过 `st.session_state` 管理状态

### AI 三阶段分析

1. **需求理解**：截图(base64) + 历史用例 → 页面结构、功能点、覆盖缺口
2. **代码分析**：反编译 Java 代码块 → API、校验规则、分支、异常、业务规则
3. **用例生成**：前两阶段结果 + 已有用例 → 新增 UI 操作用例 + 代码级补充用例

AI 响应为 Markdown 包裹的 JSON，客户端负责提取。

## 注意事项

- 项目全部使用中文：注释、文档、UI 文案、Prompt 模板均为中文
- AI 提供商支持两种：`openai_compatible`（兼容 GPT-4o / DeepSeek / 通义千问等）和 `claude`
- JAR 分析功能需要 `tools/cfr.jar` 存在且系统有 `java` 命令；缺失时该功能不可用但不影响其他流程
