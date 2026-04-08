# TestCraft - AI 驱动的测试用例生成工具

TestCraft 是一款面向测试工程师的 AI 测试用例生成工具。通过分析历史测试用例、需求截图和 Java JAR 包，自动生成可执行的 UI 测试用例，并从代码层面补充完善用例覆盖。

## 功能特性

- **多格式输入**：支持 XMind、Excel 历史用例导入，需求截图上传，JAR 文件反编译分析
- **AI 智能分析**：三阶段 AI 分析流程（需求理解 → 代码分析 → 用例生成）
- **可配置大模型**：支持 OpenAI、Claude、通义千问、DeepSeek 等任意 OpenAI 兼容 API
- **UI 操作用例**：生成明确的点击/输入/选择步骤，可直接用于手工测试执行
- **代码级补充**：基于 Controller/Service 层的校验规则、分支逻辑、异常处理补充边界测试
- **Excel 导出**：格式化导出，支持筛选器和冻结首行，方便导入测试管理工具

## 快速开始

### 环境要求

- Python 3.9+
- Java Runtime（JAR 反编译功能需要）

### 安装

```bash
git clone https://github.com/你的用户名/testcraft.git
cd testcraft
pip install -r requirements.txt
```

### 下载 cfr 反编译器（JAR 分析功能需要）

从 [cfr releases](https://github.com/leibnitz27/cfr/releases) 下载最新版 `cfr.jar`，放到 `tools/` 目录：

```bash
mkdir -p tools
# 将下载的 cfr-xxx.jar 重命名为 cfr.jar 放入 tools 目录
mv ~/Downloads/cfr-*.jar tools/cfr.jar
```

### 启动

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 使用说明

### 1. 配置 API

在左侧边栏填写：

| 配置项 | 说明 |
|--------|------|
| API 提供商 | 选择 "OpenAI 兼容" 或 "Claude" |
| API URL | API 地址（如 `https://api.deepseek.com/v1`） |
| API Key | 你的 API 密钥 |
| 模型名称 | 模型 ID（如 `deepseek-chat`、`gpt-4o`、`claude-sonnet-4-20250514`） |

> 大多数国产模型（通义千问、DeepSeek、智谱等）选择 "OpenAI 兼容" 即可。

### 2. 上传文件

| 输入类型 | 格式 | 用途 |
|----------|------|------|
| 历史测试用例 | `.xmind` / `.xlsx` | 提供已有用例，AI 会避免重复并补充覆盖盲区 |
| 需求截图 | `.png` / `.jpg` | AI 通过 Vision 识别 UI 元素和页面流程 |
| JAR 文件 | `.jar` | 反编译后分析 Controller/Service 代码 |

### 3. 生成用例

点击"开始分析"，AI 将执行三阶段分析：

1. **需求理解**：分析截图 UI 结构 + 对比历史用例覆盖情况
2. **代码分析**：提取接口、校验规则、分支逻辑、异常处理
3. **用例生成**：生成 UI 操作用例 + 代码级补充用例

### 4. 查看与导出

- 在"测试用例"页签中按模块/来源/优先级筛选
- 点击"导出 Excel"下载格式化的测试用例文件

## 生成用例示例

```
用例标题：新建规则包
优先级：P0
前置条件：用户已登录系统

操作步骤：
1. 点击"规则管理"菜单
2. 点击"新建规则包"按钮
3. 在"规则包名称"输入框输入"测试规则包"
4. 在"规则包编码"输入框输入"test"
5. 点击"确定"按钮

预期结果：规则包创建成功，列表中显示新建的规则包
```

## 项目结构

```
testcraft/
├── app.py                  # Streamlit 主入口
├── config.py               # AI 配置
├── requirements.txt        # Python 依赖
├── parsers/
│   ├── xmind_parser.py     # XMind 文件解析
│   ├── excel_parser.py     # Excel 文件解析
│   └── jar_parser.py       # JAR 反编译与代码提取
├── ai/
│   ├── client.py           # 统一 AI 客户端
│   ├── prompts.py          # Prompt 模板
│   └── analyzer.py         # 三阶段分析编排
├── generators/
│   └── excel_export.py     # Excel 导出
├── tests/                  # 单元测试
└── tools/                  # cfr.jar 存放目录
```

## 运行测试

```bash
python -m pytest tests/ -v
```

## License

MIT
