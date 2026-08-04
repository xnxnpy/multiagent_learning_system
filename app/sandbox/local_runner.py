import subprocess
import tempfile
import os
import sys
import re
from typing import Dict, Any
from app.core.logger import log


# 禁止的模块和函数（防止读取敏感信息、访问网络、执行系统命令）
BLOCKED_PATTERNS = [
    r'\bimport\s+os\b',
    r'\bfrom\s+os\s+import\b',
    r'\bimport\s+subprocess\b',
    r'\bfrom\s+subprocess\b',
    r'\bimport\s+socket\b',
    r'\bfrom\s+socket\b',
    r'\bimport\s+urllib\b',
    r'\bfrom\s+urllib\b',
    r'\bimport\s+requests\b',
    r'\bimport\s+http\b',
    r'\bfrom\s+http\b',
    r'\bimport\s+ftplib\b',
    r'\bimport\s+smtplib\b',
    r'\bimport\s+ctypes\b',
    r'\bimport\s+shutil\b',
    r'\bos\.(system|popen|exec|spawn|remove|rmdir|unlink)',
    r'\bos\.environ',
    r'\b__import__\b',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bopen\s*\([^)]*["\']\/',
]

# 安全的环境变量（白名单，小写匹配，兼容 Windows 大小写不敏感）
SAFE_ENV_KEYS = {
    'path', 'pythonpath', 'pythondontwritebytecode', 'pythonunbuffered',
    'home', 'user', 'temp', 'tmp', 'lang', 'lc_all', 'tz',
    'systemroot', 'pathext', 'userprofile', 'appdata', 'windir',  # Windows
    'conda_default_env', 'conda_prefix', 'virtual_env',  # 虚拟环境
}


def _check_code_safety(code: str) -> str:
    """检查代码安全性，返回错误信息（安全则返回空字符串）"""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return f"代码包含禁止的操作: {pattern}"
    return ""


class LocalRunner:
    """本地 Python 代码执行沙箱（带安全限制）"""

    def __init__(self, timeout: int = 10, max_memory_mb: int = 256):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

    def run_python_code(self, code: str, files: Dict[str, str] = None) -> Dict[str, Any]:
        """运行 Python 代码（带安全检查和资源限制）"""
        files = files or {}

        # 安全检查
        safety_error = _check_code_safety(code)
        if safety_error:
            log.warning(f"代码安全检查未通过: {safety_error}")
            return {
                "stdout": "",
                "stderr": safety_error,
                "exit_code": 1,
                "success": False,
            }

        # 构建安全的环境变量（大小写不敏感匹配，兼容 Windows）
        safe_env = {k: v for k, v in os.environ.items() if k.lower() in SAFE_ENV_KEYS}
        safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
        safe_env["PYTHONUNBUFFERED"] = "1"

        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.py")
            with open(main_file, "w", encoding="utf-8") as f:
                f.write(code)

            for filename, content in files.items():
                file_path = os.path.join(temp_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            try:
                log.info(f"在沙箱中运行代码，超时: {self.timeout}s")

                result = subprocess.run(
                    [sys.executable, main_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=temp_dir,
                    env=safe_env,
                )

                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                    "success": result.returncode == 0,
                }

            except subprocess.TimeoutExpired:
                log.warning(f"代码执行超时 ({self.timeout}s)")
                return {
                    "stdout": "",
                    "stderr": f"执行超时（{self.timeout}秒限制）",
                    "exit_code": 124,
                    "success": False,
                }
            except Exception as e:
                log.error(f"代码执行出错: {e}")
                return {
                    "stdout": "",
                    "stderr": f"执行错误: {str(e)}",
                    "exit_code": 1,
                    "success": False,
                }


# 创建全局实例
local_runner = LocalRunner()
