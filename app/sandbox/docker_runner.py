import docker
import tempfile
import os
from typing import Dict, Any
from app.core.logger import log


class DockerRunner:
    """Docker 代码执行沙箱"""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout: int = 30,
        memory_limit: str = "128m",
        cpu_limit: float = 0.5,
    ):
        self.client = docker.from_env()
        self.image = image
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def run_python_code(self, code: str, files: Dict[str, str] = None) -> Dict[str, Any]:
        """
        运行 Python 代码

        Args:
            code: 要运行的 Python 代码
            files: 附加文件，键为文件名，值为文件内容

        Returns:
            包含 stdout, stderr, exit_code 的字典
        """
        files = files or {}

        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建主代码文件
            main_file = os.path.join(temp_dir, "main.py")
            with open(main_file, "w", encoding="utf-8") as f:
                f.write(code)

            # 创建附加文件
            for filename, content in files.items():
                file_path = os.path.join(temp_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            try:
                log.info(f"在 Docker 中运行代码，超时: {self.timeout}s")

                # 运行容器
                container = self.client.containers.run(
                    self.image,
                    command=["python", "/app/main.py"],
                    volumes={temp_dir: {"bind": "/app", "mode": "ro"}},
                    working_dir="/app",
                    detach=True,
                    mem_limit=self.memory_limit,
                    cpu_quota=int(self.cpu_limit * 100000),
                    network_mode="none",  # 禁止网络访问
                    read_only=True,
                    tmpfs={"/tmp": "rw"},
                )

                # 等待容器完成
                result = container.wait(timeout=self.timeout)
                exit_code = result["StatusCode"]

                # 获取输出
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

                # 清理容器
                container.remove(force=True)

                log.info(f"代码执行完成，退出码: {exit_code}")

                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "success": exit_code == 0,
                }

            except docker.errors.TimeoutError:
                # 超时处理
                if "container" in locals():
                    container.kill()
                    container.remove(force=True)
                log.warning(f"代码执行超时 ({self.timeout}s)")
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {self.timeout} seconds",
                    "exit_code": 124,
                    "success": False,
                }
            except Exception as e:
                if "container" in locals():
                    try:
                        container.kill()
                        container.remove(force=True)
                    except:
                        pass
                log.error(f"代码执行出错: {e}")
                return {
                    "stdout": "",
                    "stderr": f"Error: {str(e)}",
                    "exit_code": 1,
                    "success": False,
                }
