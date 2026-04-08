from __future__ import annotations

import base64
import json
import re
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
