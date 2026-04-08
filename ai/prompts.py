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
          "covered": true,
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
