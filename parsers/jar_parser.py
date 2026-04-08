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
