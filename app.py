import base64
import io
import os
import tempfile

import streamlit as st

from config import AIConfig
from parsers.xmind_parser import parse_xmind
from parsers.excel_parser import parse_excel
from parsers.jar_parser import decompile_jar, extract_key_classes, prepare_code_for_ai
from ai.analyzer import TestCaseAnalyzer
from generators.excel_export import export_to_excel

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
tab_upload, tab_progress, tab_results = st.tabs(["文件上传", "分析过程", "测试用例"])

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
    start_btn = st.button("开始分析", type="primary", use_container_width=True)

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
            log_progress("正在解析历史测试用例...")
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
                log_progress(f"解析完成，共 {len(existing_cases)} 条历史用例")

            # Step 2: 处理截图
            progress_bar.progress(20)
            screenshots_b64 = []
            if screenshot_files:
                log_progress("正在处理需求截图...")
                for img_file in screenshot_files:
                    img_bytes = img_file.read()
                    screenshots_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
                log_progress(f"已处理 {len(screenshots_b64)} 张截图")

            # Step 3: 反编译 JAR
            progress_bar.progress(30)
            code_chunks = []
            if jar_file:
                log_progress("正在反编译 JAR 文件...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jar") as tmp:
                    tmp.write(jar_file.read())
                    jar_path = tmp.name
                try:
                    decompiled_dir = decompile_jar(jar_path)
                    classes = extract_key_classes(decompiled_dir)
                    code_chunks = prepare_code_for_ai(classes)
                    log_progress(f"反编译完成，提取 {len(classes)} 个关键类，分为 {len(code_chunks)} 个代码块")
                except Exception as e:
                    log_progress(f"JAR 反编译失败: {e}（将跳过代码分析）")
                finally:
                    os.unlink(jar_path)

            # Step 4: AI 分析
            progress_bar.progress(40)
            log_progress("正在调用 AI 分析...")
            try:
                analyzer = TestCaseAnalyzer(config)

                def update_progress(msg):
                    log_progress(msg)

                cases = analyzer.run_full_analysis(
                    screenshots_base64=screenshots_b64,
                    existing_cases=existing_cases,
                    code_chunks=code_chunks,
                    progress_callback=update_progress,
                )
                st.session_state.test_cases = cases
                progress_bar.progress(100)
                log_progress(f"分析完成！共生成 {len(cases)} 条测试用例")
            except Exception as e:
                log_progress(f"AI 分析失败: {e}")

            # 显示日志
            with progress_container:
                for log in st.session_state.progress_logs:
                    st.write(log)

# ----- Tab3: 测试用例展示 -----
with tab_results:
    cases = st.session_state.test_cases
    if not cases:
        st.info('暂无测试用例，请先上传文件并点击"开始分析"')
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
            label="导出 Excel",
            data=excel_data,
            file_name="test_cases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
