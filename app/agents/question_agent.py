from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log
from app.sandbox.local_runner import LocalRunner


class QuestionAgent(BaseAgent):
    agent_name = "question"
    """题目生成 Agent - 支持案例分析题和个性化"""

    PROMPT_PATH = "prompts/question_prompt.txt"

    def __init__(self, db: AsyncSession = None):
        super().__init__(db)
        self.local_runner = LocalRunner()

    async def run(self, topic: str, user_id: int = None) -> Dict[str, Any]:
        """
        执行题目生成任务（先查库，有则返回，无则生成后保存）

        Args:
            topic: 知识点主题
            user_id: 用户 ID（用于缓存和个性化）

        Returns:
            包含题目列表的字典
        """
        log.info(f"QuestionAgent 开始为主题 '{topic}' 生成题目")

        # 先查库
        if user_id and self.db:
            existing = await self._get_from_db(user_id, topic)
            if existing:
                log.info(f"命中数据库缓存，主题: {topic}")
                return existing

        # 获取学生画像用于个性化
        profile = None
        if user_id and self.db:
            profile = await self._get_profile(user_id)

        prompt = self._load_and_format_prompt(topic, profile)

        result = None
        for attempt in range(2):
            response = await self._call_llm(prompt)
            if attempt == 0:
                log.info(f"QuestionAgent LLM 响应长度: {len(response)}，前300字: {response[:300]}")

            result = extract_json(response)

            if result and isinstance(result, dict) and "questions" in result:
                break
            if attempt == 0:
                log.warning(f"QuestionAgent JSON 提取失败，尝试重新生成 (attempt 1)")

        if result:
            log.info(f"QuestionAgent extract_json 成功，字段: {list(result.keys()) if isinstance(result, dict) else type(result).__name__}")
        else:
            log.warning(f"QuestionAgent extract_json 返回 None，LLM 原始响应前500字: {response[:500]}")

        # 验证结果结构
        if not result or not isinstance(result, dict) or "questions" not in result:
            log.warning(f"LLM 响应缺少 questions 字段，使用 mock 兜底。返回的字段: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            result = self._get_mock_questions(topic, profile)
        elif not isinstance(result.get("questions"), list):
            result["questions"] = []

        # 验证题目数量
        q_count = len(result.get("questions", []))
        if q_count < 3:
            log.warning(f"生成题目数量不足（{q_count}道），建议至少3道")

        log.info(f"QuestionAgent 完成，生成了 {len(result.get('questions', []))} 道题目")
        return result

    async def _get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取学生画像"""
        from app.models import StudentProfile
        try:
            result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            profile = result.scalar_one_or_none()
            if profile:
                return {
                    "major": profile.major or "",
                    "grade": profile.grade or "",
                    "goal": profile.goal or "",
                    "knowledge_level": profile.knowledge_level or "",
                    "weakness": profile.weakness or [],
                    "interests": profile.interests or []
                }
        except Exception as e:
            log.warning(f"获取学生画像失败: {e}")
        return None

    async def _get_from_db(self, user_id: int, topic: str) -> Optional[Dict[str, Any]]:
        """从 LearningResource 获取已生成的题目（缓存）"""
        from app.models import LearningResource
        from sqlalchemy import select as sa_select
        result = await self.db.execute(
            sa_select(LearningResource).where(
                LearningResource.user_id == user_id,
                LearningResource.resource_type == "question",
                LearningResource.topic == topic
            ).order_by(LearningResource.created_at.desc()).limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            questions_data = record.content
            if isinstance(questions_data, dict):
                q_list = questions_data.get("questions", [])
                if not q_list:
                    log.info(f"跳过空题目缓存，将重新生成")
                    return None
            return questions_data
        return None

    def _load_and_format_prompt(self, topic: str, profile: Dict = None) -> str:
        """加载并格式化 Prompt（注入学生画像）"""
        template = self._load_prompt(self.PROMPT_PATH)

        # 构建个性化上下文
        if profile:
            weakness_str = ", ".join(profile.get("weakness", [])) or "无"
            interests_str = ", ".join(profile.get("interests", [])) or "无"
            profile_context = f"""
## 学生画像信息（用于个性化出题）
- 专业：{profile.get('major', '未知')}
- 年级：{profile.get('grade', '未知')}
- 知识水平：{profile.get('knowledge_level', '未知')}
- 学习目标：{profile.get('goal', '未知')}
- 薄弱点：{weakness_str}
- 兴趣方向：{interests_str}

**请根据学生画像调整题目**：
- 根据学生知识水平调整题目难度分布
- 重点针对学生的薄弱点设计题目
- 使用学生专业相关的案例
"""
        else:
            profile_context = ""

        return self._format_prompt(template, topic=topic, profile_context=profile_context)


    def _get_mock_questions(self, topic: str, profile: Dict = None) -> Dict[str, Any]:
        """LLM 失败时直接构造 mock 题目数据（包含案例分析题）"""
        major = profile.get("major", "计算机科学") if profile else "计算机科学"
        return {
            "questions": [
                {
                    "question_id": 1,
                    "type": "choice",
                    "difficulty": "easy",
                    "question": f"以下哪个是 Python 中定义函数的关键字？",
                    "options": ["function", "def", "func", "define"],
                    "answer": "def",
                    "score": 10
                },
                {
                    "question_id": 2,
                    "type": "choice",
                    "difficulty": "easy",
                    "question": f"Python 中用于输出内容到控制台的函数是？",
                    "options": ["echo()", "console.log()", "print()", "output()"],
                    "answer": "print()",
                    "score": 10
                },
                {
                    "question_id": 3,
                    "type": "blank",
                    "difficulty": "medium",
                    "question": f"Python 中使用 ______ 关键字定义一个匿名函数",
                    "answer": "lambda",
                    "score": 10
                },
                {
                    "question_id": 4,
                    "type": "case_analysis",
                    "difficulty": "medium",
                    "question": f"【案例分析】在{major}领域，假设你需要处理一个学生信息管理系统。请分析以下需求，并回答问题：\n\n需求：系统需要存储学生姓名、年龄、成绩，并能计算平均分。\n\n问题：\n1. 应该使用什么数据结构存储学生信息？\n2. 如何实现计算平均分的函数？\n3. 如何处理异常输入（如成绩为负数）？",
                    "answer": "1. 使用字典或类存储\n2. 定义calc_avg(scores)函数\n3. 使用try-except和条件判断",
                    "rubric": {
                        "criteria": [
                            "数据结构选择合理（字典/类/命名元组）",
                            "平均分计算逻辑正确",
                            "异常处理完整（负数、空值、类型错误）"
                        ],
                        "max_score": 20
                    },
                    "score": 20
                },
                {
                    "question_id": 5,
                    "type": "code",
                    "difficulty": "hard",
                    "question": f"编写一个 Python 函数，判断一个字符串是否是回文串",
                    "answer": "def is_palindrome(s):\n    return s == s::-1]",
                    "test_cases": [
                        {"input": "racecar", "expected": "True"},
                        {"input": "hello", "expected": "False"}
                    ],
                    "score": 20
                }
            ]
        }

    async def evaluate_code(self, code: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """
        评估编程题答案

        Args:
            code: 学生提交的代码
            test_cases: 测试用例列表

        Returns:
            评估结果
        """
        log.info(f"开始评估编程代码，测试用例数: {len(test_cases)}")

        passed = 0
        failed = 0
        results = []

        for i, test_case in enumerate(test_cases):
            test_input = test_case.get("input", "")
            expected = str(test_case.get("expected", ""))

            test_code = self._build_test_code(code, test_input, expected)

            try:
                result = self.local_runner.run_python_code(test_code)

                if result["success"]:
                    if "PASSED" in result["stdout"]:
                        passed += 1
                        results.append({
                            "test_case": i + 1,
                            "status": "passed",
                            "output": result["stdout"]
                        })
                    else:
                        failed += 1
                        results.append({
                            "test_case": i + 1,
                            "status": "failed",
                            "output": result["stdout"],
                            "error": result["stderr"]
                        })
                else:
                    failed += 1
                    results.append({
                        "test_case": i + 1,
                        "status": "error",
                        "output": result["stdout"],
                        "error": result["stderr"]
                    })
            except Exception as e:
                failed += 1
                results.append({
                    "test_case": i + 1,
                    "status": "error",
                    "error": str(e)
                })

        score_ratio = passed / len(test_cases) if test_cases else 0

        return {
            "passed": passed,
            "failed": failed,
            "total": len(test_cases),
            "score_ratio": score_ratio,
            "results": results
        }

    def _build_test_code(self, code: str, test_input: str, expected: str) -> str:
        """构建测试代码"""
        # 先在 Python 层提取函数名
        func_name = ""
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("def ") and "(" in stripped:
                func_name = stripped.split("(")[0].replace("def ", "").strip()
                break

        if func_name:
            call_expr = f"{func_name}(input_data)"
        else:
            call_expr = "eval(code)"

        test_code = f"""
{code}

# 测试代码
import sys

def test():
    try:
        input_data = {test_input}
        result = {call_expr}
        if str(result) == "{expected}":
            print("PASSED")
        else:
            print(f"FAILED: expected {expected}, got {{result}}")
    except Exception as e:
        print(f"ERROR: {{e}}")
        sys.exit(1)

test()
"""
        return test_code.strip()


# 创建全局实例
question_agent = QuestionAgent()
