# TestCraft - AI 驱动的测试用例生成工具

## 概述

为测试工程师打造的 AI 测试用例生成工具。通过分析历史测试用例、需求截图和 Java JAR 包，自动生成可执行的 UI 测试用例，并从代码层面补充完善用例覆盖。

## 技术决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| 应用形式 | Web 应用 | 测试工程师通过浏览器使用 |
| AI 能力 | 大模型 API | 需要 Vision 理解截图 + 代码语义分析 |
| 技术栈 | Python + Streamlit | 快速搭建，AI 生态最强 |
| 大模型 | 可配置多模型 | 用户提供 API Key 和 URL |
| 输出格式 | 页面展示 + Excel 导出 | 方便导入测试管理工具 |
| JAR 分析深度 | 深度分析（Controller + Service） | 提取校验规则、分支逻辑、异常处理 |

## 架构

### 核心流程

```
用户上传文件（XMind/Excel/截图/JAR）
        ↓
    文件解析层
    ├── XMind → 提取测试用例树形结构
    ├── Excel → 提取测试用例表格数据
    ├── 截图 → 转 base64 供 AI Vision 分析
    └── JAR → cfr 反编译 → 提取 Controller/Service 源码
        ↓
    AI 分析层（可配置模型）
    ├── 分析需求截图 → 识别 UI 元素、页面流程
    ├── 分析历史用例 → 理解已有覆盖范围
    └── 分析反编译代码 → 提取接口、校验规则、分支逻辑、异常处理
        ↓
    用例生成层
    ├── UI 操作用例（点击、输入、断言步骤）
    └── 代码级补充用例（边界值、异常路径、参数校验）
        ↓
    输出：页面展示 + 导出 Excel
```

### 目录结构

```
tester/
├── app.py                  # Streamlit 主入口
├── config.py               # 模型配置（API Key/URL）
├── parsers/
│   ├── xmind_parser.py     # XMind 文件解析
│   ├── excel_parser.py     # Excel 文件解析
│   └── jar_parser.py       # JAR 反编译 + 代码提取
├── ai/
│   ├── client.py           # 统一 AI 客户端（支持多模型）
│   ├── prompts.py          # Prompt 模板
│   └── analyzer.py         # AI 分析编排逻辑
├── generators/
│   └── excel_export.py     # Excel 导出
└── requirements.txt
```

## 文件解析层

### XMind 解析
- 使用 `xmindparser` 库，将 `.xmind` 文件解析为树形 JSON 结构
- 提取：用例标题、步骤描述、优先级标签
- 输出统一的用例数据结构供 AI 分析

### Excel 解析
- 使用 `openpyxl` 库，支持 `.xlsx` 格式
- 自动识别常见列名映射（如"用例名称"、"前置条件"、"操作步骤"、"预期结果"）
- 容错处理：列名不标准时，让 AI 辅助识别列含义

### 截图处理
- 接收 `.png/.jpg/.jpeg` 格式
- 转为 base64 编码，直接传递给大模型的 Vision 接口
- 支持多张截图上传，按上传顺序组织为页面流程

### JAR 反编译与代码提取
- 调用 `cfr`（Java 反编译器）将 JAR 解包为 `.java` 源码
- 智能过滤：优先提取 `*Controller.java`、`*Service.java`、`*ServiceImpl.java`
- 识别 Spring 注解（`@RestController`、`@RequestMapping`、`@Valid`、`@NotNull` 等）
- 提取校验规则、条件分支（if/switch）、异常处理（try/catch/throw）
- 代码切片：按类分片发给 AI，单文件超 2000 行按方法级别切片

### 统一数据结构

```python
TestCase = {
    "id": str,
    "module": str,        # 所属模块
    "title": str,         # 用例标题
    "precondition": str,  # 前置条件
    "steps": [str],       # 操作步骤列表
    "expected": str,      # 预期结果
    "priority": str,      # 优先级 P0-P3
    "source": str         # 来源：xmind/excel/ai_generated
}
```

## AI 分析层

### 统一客户端设计

用户在侧边栏配置：
- API 提供商：下拉选择（OpenAI 兼容 / Claude / 自定义）
- API URL：文本输入
- API Key：密码输入
- 模型名称：文本输入

底层统一使用 OpenAI 兼容格式调用，Claude 单独适配。

### Prompt 策略（三阶段）

**阶段一：需求理解**
- 输入：需求截图 + 历史用例
- 任务：分析截图中的 UI 页面结构，对比历史用例，识别已覆盖/未覆盖功能点
- 输出：功能点清单 + 覆盖标记

**阶段二：代码分析**
- 输入：反编译后的 Controller + Service 代码
- 任务：提取接口路径、请求参数、参数校验规则、业务逻辑分支、异常处理和错误码
- 输出：接口清单 + 校验规则 + 分支条件 + 异常场景

**阶段三：用例生成**
- 输入：阶段一功能清单 + 阶段二代码分析结果 + 历史用例
- 任务：生成 UI 操作用例 + 代码级补充用例，标注来源，按模块分组，设定优先级
- 输出：严格按 TestCase 结构的 JSON 数组

### Token 管理
- 单个 Service 文件超过 2000 行时，按方法级别切片
- 多轮调用结果在本地拼合
- Streamlit 界面显示 AI 调用进度条

## 界面设计

### Streamlit 布局
- 侧边栏：API 配置
- Tab1 文件上传：历史用例、需求截图、JAR 文件上传区 + 开始分析按钮
- Tab2 分析过程：实时进度展示
- Tab3 测试用例：筛选器（模块/来源/优先级）+ 可展开用例表格 + Excel 导出按钮

### Excel 导出格式

| 列 | 说明 |
|---|---|
| 用例编号 | 自动编号 TC-001 |
| 所属模块 | 功能模块名 |
| 用例标题 | 用例简述 |
| 优先级 | P0/P1/P2/P3 |
| 前置条件 | 执行前需要满足的条件 |
| 操作步骤 | 编号步骤，每步一行 |
| 预期结果 | 期望的系统响应 |
| 用例来源 | 截图推导 / 代码补充 / 历史增强 |

导出时自动设置列宽、冻结首行、添加筛选器。
