import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.agents.base import BaseAgent
from app.agents.utils import extract_json
from app.core.logger import log
from app.models import LearningRecord, StudentProfile
from app.agents.learning_path_agent import LearningPathAgent


class EvaluationAgent(BaseAgent):
    agent_name = "evaluation"
    """学生评估 Agent"""

    PROMPT_PATH = "prompts/evaluation_prompt.txt"
    
    MASTERY_THRESHOLD = 0.2
    MIN_RECORDS_THRESHOLD = 5

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def run(self, user_id: int) -> Dict[str, Any]:
        """
        执行学生评估

        Args:
            user_id: 用户 ID

        Returns:
            评估结果
        """
        log.info(f"EvaluationAgent 开始评估学生 {user_id}")

        student_profile = await self._get_student_profile(user_id)
        learning_records = await self._get_learning_records(user_id)

        if not learning_records:
            log.info(f"学生 {user_id} 暂无学习记录")
            return self._generate_empty_report(student_profile)

        learning_stats = self._calculate_stats(learning_records)

        # 新增：按阶段分组的趋势统计
        stage_trend = await self._calculate_stage_trend(user_id, learning_records)
        learning_stats["stage_trend"] = stage_trend
        learning_stats["accuracy_trend"] = self._get_trend_direction(stage_trend)

        # 获取当前阶段的知识点，传给 LLM 让它为每个知识点生成评估
        stage_kps = await self._get_stage_knowledge_points(user_id)

        prompt = self._build_prompt(student_profile, learning_stats, learning_records, stage_kps)
        evaluation_result = await self._call_llm(prompt)

        result = extract_json(evaluation_result)
        if not result:
            log.error(f"LLM 响应不是有效 JSON: {evaluation_result}")
            result = self._generate_fallback_result(learning_stats)

        # 补全 LLM 遗漏的知识点，按正确率均匀分配分数
        if stage_kps:
            existing_kps = {kp.get("topic", "") for kp in result.get("knowledge_points", [])}
            total_kps = len(stage_kps)
            total_score = result.get("total_score", 0)
            total_attempts = result.get("total_attempts", 0)
            avg_score_per_kp = total_score // max(total_kps, 1) if total_kps else 0
            avg_attempts_per_kp = total_attempts // max(total_kps, 1) if total_kps else 0

            for kp_name in stage_kps:
                if kp_name not in existing_kps:
                    result.setdefault("knowledge_points", []).append({
                        "topic": kp_name,
                        "score": avg_score_per_kp,
                        "total": avg_attempts_per_kp * 10,
                        "mastery": learning_stats.get("accuracy_rate", 0),
                        "status": "学习中"
                    })

        # 确保 summary 字段存在（LLM 可能漏掉）
        if "summary" not in result or not result["summary"]:
            result["summary"] = self._build_auto_summary(result, stage_trend)

        await self._update_student_profile(user_id, result)

        # 保存评估报告到数据库
        await self._save_report_to_db(user_id, result)

        log.info(f"EvaluationAgent 完成评估，学生 {user_id} 评估等级: {result.get('overall_grade')}")
        return result

    async def _update_path_incrementally(self, user_id: int, eval_result: Dict) -> bool:
        """根据评估结果增量更新学习路径

        更新条件（满足任一即更新）：
        1. 掌握度变化 ≥ 15%
        2. 薄弱点列表变化 ≥ 2 个
        3. 路径剩余阶段 < 2

        Returns: True=路径已更新，False=无需更新
        """
        from app.models import AsyncSessionLocal, LearningPath, EvaluationReport

        try:
            async with AsyncSessionLocal() as db:
                # 查询当前画像（上次评估结果）
                profile_result = await db.execute(
                    select(StudentProfile).where(
                        StudentProfile.user_id == user_id,
                        StudentProfile.is_active == True,
                    )
                )
                profile = profile_result.scalar_one_or_none()

                # 查询上次评估的掌握度
                last_eval_result = await db.execute(
                    select(EvaluationReport).where(
                        EvaluationReport.user_id == user_id
                    ).order_by(EvaluationReport.created_at.desc()).limit(1)
                )
                last_eval = last_eval_result.scalar_one_or_none()
                last_mastery = last_eval.mastery_level if last_eval and last_eval.mastery_level else 0

                # 当前掌握度
                current_mastery = eval_result.get("mastery_level", 0)
                mastery_change = abs(current_mastery - last_mastery)

                # 薄弱点变化
                old_weaknesses = set(profile.weakness or []) if profile else set()
                new_weaknesses = set(eval_result.get("analysis", {}).get("weaknesses", []))
                weakness_change = len(new_weaknesses.symmetric_difference(old_weaknesses))

                # 判断是否需要更新
                should_update = (
                    mastery_change >= 0.15 or       # 掌握度变化 ≥15%
                    weakness_change >= 2 or          # 薄弱点变化 ≥2
                    len(new_weaknesses - old_weaknesses) > 0  # 出现新的薄弱点
                )

                if not should_update:
                    log.info(f"学生 {user_id} 评估结果无显著变化（掌握度变化{mastery_change:.1%}，薄弱点变化{weakness_change}），跳过路径更新")
                    return False

                # 需要更新 → 调用路径规划 Agent 重新生成
                path_query = select(LearningPath).where(LearningPath.user_id == user_id)
                if profile:
                    path_query = path_query.where(LearningPath.profile_id == profile.id)
                path_result = await db.execute(path_query)
                path = path_result.scalar_one_or_none()
                if not path or not path.stages:
                    return False

                completed = path.completed_stages or []
                stages = path.stages

                # 锁定已完成阶段，只重新规划后续阶段
                locked_stages = [s for s in stages if s.get("stage_id") in completed]
                current_stages = [s for s in stages if s.get("stage_id") not in completed]

                if not current_stages:
                    return False

                # 调用路径规划 Agent 重新生成后续阶段
                from app.agents.learning_path_agent import LearningPathAgent
                path_agent = LearningPathAgent(db)
                new_path_data = await path_agent.run(user_id, profile=self._profile_to_dict(profile))

                if new_path_data and new_path_data.get("stages"):
                    new_stages = new_path_data["stages"]
                    # 重新编号新阶段的 stage_id，避免与已完成阶段冲突
                    max_existing_id = max((s.get("stage_id", 0) for s in stages), default=0)
                    for i, s in enumerate(new_stages):
                        s["stage_id"] = max_existing_id + i + 1
                    updated_stages = locked_stages + new_stages
                    path.stages = updated_stages
                    path.path_version = (path.path_version or 1) + 1
                    db.add(path)
                    await db.commit()
                    log.info(f"学生 {user_id} 路径已增量更新（版本 {path.path_version}），新增阶段 id {max_existing_id+1}-{max_existing_id+len(new_stages)}")
                    return True

                return False

        except Exception as e:
            log.error(f"增量路径更新失败: {e}")
            return False

    def _profile_to_dict(self, profile) -> Dict:
        """将 StudentProfile ORM 对象转为字典"""
        if not profile:
            return {}
        return {
            "major": profile.major or "",
            "grade": profile.grade or "",
            "goal": profile.goal or "",
            "knowledge_level": profile.knowledge_level or "",
            "learning_style": profile.learning_style or "",
            "weakness": profile.weakness or [],
            "interests": profile.interests or [],
            "coding_ability": profile.coding_ability or "",
        }

    async def _get_stage_knowledge_points(self, user_id: int) -> List[str]:
        """从学习路径获取当前阶段的知识点名称列表"""
        from app.models import LearningPath
        try:
            result = await self.db.execute(
                select(LearningPath).where(LearningPath.user_id == user_id)
                .order_by(LearningPath.created_at.desc()).limit(1)
            )
            path = result.scalar_one_or_none()
            if not path or not path.stages:
                return []
            stage = path.stages[0]
            kps = stage.get("knowledge_points", [])
            if not kps:
                return []
            if isinstance(kps[0], dict):
                return [kp.get("name", "") for kp in kps if kp.get("name")]
            return [str(kp) for kp in kps if kp]
        except Exception:
            return []

    async def _save_report_to_db(self, user_id: int, report_data: Dict):
        """保存评估报告到数据库"""
        from app.models import EvaluationReport
        try:
            record = EvaluationReport(
                user_id=user_id,
                overall_grade=report_data.get("overall_grade"),
                total_score=report_data.get("total_score"),
                accuracy_rate=report_data.get("accuracy_rate"),
                mastery_level=report_data.get("mastery_level"),
                report_data=report_data
            )
            self.db.add(record)
            await self.db.commit()
            log.info(f"评估报告已保存到数据库，用户 {user_id}")
        except Exception as e:
            log.error(f"保存评估报告到数据库失败: {e}")
            await self.db.rollback()

    async def _get_student_profile(self, user_id: int) -> Dict[str, Any]:
        """获取学生画像"""
        result = await self.db.execute(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id,
                StudentProfile.is_active == True,
            )
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            return {
                "major": profile.major or "未知",
                "grade": profile.grade or "未知",
                "goal": profile.goal or "未设定",
                "knowledge_level": profile.knowledge_level or "未知",
                "learning_style": profile.learning_style or "未知",
                "interests": profile.interests or [],
                "weakness": profile.weakness or [],
                "coding_ability": profile.coding_ability or "未知"
            }
        return {}

    async def _get_learning_records(self, user_id: int, limit: int = 50) -> List[LearningRecord]:
        """获取学习记录（仅答题记录）"""
        result = await self.db.execute(
            select(LearningRecord)
            .where(
                LearningRecord.user_id == user_id,
                LearningRecord.resource_type == "question"
            )
            .order_by(desc(LearningRecord.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    def _calculate_stats(self, records: List[LearningRecord]) -> Dict[str, Any]:
        """计算学习统计数据（含行为追踪新维度）"""
        if not records:
            return {
                "total_attempts": 0,
                "total_score": 0,
                "max_score": 0,
                "accuracy_rate": 0.0,
                "average_score": 0.0,
                "recent_accuracy": 0.0,
                "topics_covered": [],
                "activity_days": 0,
                "total_study_time": 0,
                "avg_session_duration": 0.0,
                "learning_streak": 0,
                "event_type_counts": {},
            }

        # 按 resource_id 去重：同一题目多次提交只保留最高分
        best_by_resource: Dict[int, LearningRecord] = {}
        for r in records:
            rid = r.resource_id
            if rid is None:
                # 非题目记录（如 code_execute），保留最新一条
                key = f"non_q_{r.id}"
                best_by_resource[key] = r
            elif rid not in best_by_resource or (r.score or 0) > (best_by_resource[rid].score or 0):
                best_by_resource[rid] = r

        deduped = list(best_by_resource.values())

        total_attempts = len(deduped)
        total_score = sum(r.score for r in deduped if r.score is not None)
        max_score = sum(10 for _ in deduped)
        correct_count = sum(1 for r in deduped if r.correct)
        accuracy_rate = correct_count / total_attempts if total_attempts > 0 else 0.0

        recent_records = records[:min(10, len(records))]
        recent_correct = sum(1 for r in recent_records if r.correct)
        recent_accuracy = recent_correct / len(recent_records) if recent_records else 0.0

        topics = set()
        for r in records:
            behavior = r.behavior_data
            if isinstance(behavior, dict) and "topic" in behavior:
                topics.add(behavior["topic"])

        # ── 学习时长统计（从答题记录的 behavior_data 中提取） ──
        total_study_time = sum(r.duration_seconds or 0 for r in records if r.duration_seconds)
        avg_session_duration = total_study_time / len(records) if records else 0.0

        # 活跃天数（过滤 None created_at）
        active_dates = set()
        for r in records:
            if r.created_at is not None:
                active_dates.add(r.created_at.date())
        activity_days = len(active_dates)

        # 连续学习天数（从最近一天往前数）
        from datetime import date, timedelta
        learning_streak = 0
        if active_dates:
            sorted_dates = sorted(active_dates, reverse=True)
            most_recent = sorted_dates[0]
            # 如果最近活跃日不是今天，从今天开始倒推，允许今天还没学习
            today = date.today()
            expected = today if most_recent >= today else most_recent
            for d in sorted_dates:
                if d == expected:
                    learning_streak += 1
                    expected = expected - timedelta(days=1)
                elif d < expected:
                    break

        # 事件类型分布（过滤 None resource_type）
        event_type_counts = {}
        for r in records:
            if r.resource_type is not None:
                event_type_counts[r.resource_type] = event_type_counts.get(r.resource_type, 0) + 1

        return {
            "total_attempts": total_attempts,
            "total_score": total_score,
            "max_score": max_score,
            "accuracy_rate": accuracy_rate,
            "average_score": total_score / total_attempts if total_attempts > 0 else 0.0,
            "recent_accuracy": recent_accuracy,
            "topics_covered": list(topics),
            "activity_days": activity_days,
            "total_study_time": total_study_time,
            "avg_session_duration": round(avg_session_duration, 1),
            "learning_streak": learning_streak,
            "event_type_counts": event_type_counts,
        }

    async def _calculate_stage_trend(self, user_id: int, records: List[LearningRecord]) -> List[Dict]:
        """按阶段分组计算答题趋势，返回最近3个阶段的统计"""
        from app.models import LearningResource, LearningPath

        # 获取 resource_id → stage_id 的映射
        resource_ids = list({r.resource_id for r in records if r.resource_id})
        if not resource_ids:
            return []

        result = await self.db.execute(
            select(LearningResource.id, LearningResource.stage_id, LearningResource.topic)
            .where(LearningResource.id.in_(resource_ids))
        )
        resource_map = {}  # resource_id → {stage_id, topic}
        for row in result.all():
            resource_map[row.id] = {"stage_id": row.stage_id, "topic": row.topic}

        # 按 stage_id 分组统计
        stage_data: Dict[int, Dict] = {}
        for r in records:
            if r.resource_id and r.resource_id in resource_map:
                info = resource_map[r.resource_id]
                sid = info["stage_id"]
                if sid is None:
                    continue
                if sid not in stage_data:
                    stage_data[sid] = {
                        "stage_id": sid,
                        "stage_title": info["topic"] or f"阶段{sid}",
                        "total": 0,
                        "correct": 0,
                    }
                stage_data[sid]["total"] += 1
                if r.correct:
                    stage_data[sid]["correct"] += 1

        # 按 stage_id 排序，取最近3个
        sorted_stages = sorted(stage_data.values(), key=lambda x: x["stage_id"])
        recent = sorted_stages[-3:] if len(sorted_stages) > 3 else sorted_stages

        # 计算每个阶段的正确率
        for s in recent:
            s["accuracy"] = round(s["correct"] / s["total"], 2) if s["total"] > 0 else 0

        return recent

    def _get_trend_direction(self, stage_trend: List[Dict]) -> str:
        """判断正确率趋势方向"""
        if len(stage_trend) < 2:
            return "stable"
        accuracies = [s["accuracy"] for s in stage_trend]
        if accuracies[-1] > accuracies[-2] + 0.05:
            return "improving"
        elif accuracies[-1] < accuracies[-2] - 0.05:
            return "declining"
        return "stable"

    def _build_auto_summary(self, result: Dict, stage_trend: List[Dict]) -> str:
        """当 LLM 未生成 summary 时，自动构建摘要"""
        grade = result.get("overall_grade", "未知")
        accuracy = result.get("accuracy_rate", 0)
        weaknesses = result.get("analysis", {}).get("weaknesses", [])

        parts = [f"📊 评估结果：{grade}（正确率 {accuracy*100:.0f}%）"]

        if len(stage_trend) >= 2:
            prev = stage_trend[-2]["accuracy"]
            curr = stage_trend[-1]["accuracy"]
            diff = curr - prev
            if diff > 0:
                parts.append(f"比上一阶段提升了 {diff*100:.0f}%，继续保持！")
            elif diff < 0:
                parts.append(f"比上一阶段下降了 {abs(diff)*100:.0f}%，需要加强复习。")
            else:
                parts.append("与上一阶段持平。")

        if weaknesses:
            parts.append(f"薄弱点：{'、'.join(weaknesses[:3])}，建议重点复习。")

        return " ".join(parts)

    def _build_prompt(self, profile: Dict, stats: Dict, records: List[LearningRecord], stage_kps: List[str] = None) -> str:
        """构建评估 Prompt"""
        student_profile_str = json.dumps(profile, ensure_ascii=False)
        learning_stats_str = json.dumps(stats, ensure_ascii=False)
        
        records_list = []
        for r in records[:20]:
            record_dict = {
                "id": r.id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "correct": r.correct,
                "score": r.score,
                "behavior_data": r.behavior_data,
                "created_at": str(r.created_at)
            }
            records_list.append(record_dict)
        learning_records_str = json.dumps(records_list, ensure_ascii=False)

        stage_kps_str = "、".join(stage_kps) if stage_kps else "暂无"

        template = self._load_prompt(self.PROMPT_PATH)
        return template.format(
            student_profile=student_profile_str,
            stage_knowledge_points=stage_kps_str,
            learning_stats=learning_stats_str,
            learning_records=learning_records_str
        )


    async def _update_student_profile(self, user_id: int, eval_result: Dict[str, Any]):
        """更新学生画像"""
        try:
            db_result = await self.db.execute(
                select(StudentProfile).where(
                    StudentProfile.user_id == user_id,
                    StudentProfile.is_active == True,
                )
            )
            profile = db_result.scalar_one_or_none()

            if profile:
                if "mastery_level" in eval_result:
                    new_level = self._get_knowledge_level(eval_result["mastery_level"])
                    profile.knowledge_level = new_level

                if "analysis" in eval_result and "weaknesses" in eval_result["analysis"]:
                    weaknesses = eval_result["analysis"]["weaknesses"]
                    if weaknesses:
                        profile.weakness = weaknesses

                await self.db.commit()
                log.info(f"学生 {user_id} 画像已更新")
        except Exception as e:
            log.error(f"更新学生画像失败: {e}")

    def _get_knowledge_level(self, mastery: float) -> str:
        """根据掌握度获取知识水平等级"""
        if mastery >= 0.9:
            return "高级"
        elif mastery >= 0.7:
            return "中级"
        elif mastery >= 0.5:
            return "初级"
        else:
            return "入门"

    def _generate_empty_report(self, profile: Dict) -> Dict[str, Any]:
        """生成空评估报告"""
        return {
            "overall_grade": "需努力",
            "total_score": 0,
            "total_attempts": 0,
            "accuracy_rate": 0.0,
            "mastery_level": 0.0,
            "analysis": {
                "strengths": [],
                "weaknesses": [],
                "suggestions": ["开始学习以获取评估数据"]
            },
            "knowledge_points": [],
            "report": "学生暂无学习记录，请开始学习后再进行评估。",
            "summary": "暂无学习记录，请先完成一些练习后再来查看评估结果。",
            "should_update_path": False
        }

    def _should_update_path(self, stats: Dict) -> bool:
        """判断是否需要更新学习路径（基于学习统计数据）"""
        accuracy = stats.get("accuracy_rate", 0)
        total = stats.get("total_attempts", 0)
        # 正确率低于 50% 且有一定练习量时，建议更新路径
        return accuracy < 0.5 and total >= 3

    def _generate_fallback_result(self, stats: Dict) -> Dict[str, Any]:
        """生成降级评估结果"""
        accuracy = stats["accuracy_rate"]

        if accuracy >= 0.9:
            grade = "优秀"
        elif accuracy >= 0.7:
            grade = "良好"
        elif accuracy >= 0.5:
            grade = "中等"
        else:
            grade = "需努力"

        mastery = accuracy

        return {
            "overall_grade": grade,
            "total_score": stats["total_score"],
            "total_attempts": stats["total_attempts"],
            "accuracy_rate": accuracy,
            "mastery_level": mastery,
            "analysis": {
                "strengths": ["学习积极"],
                "weaknesses": ["需要更多练习"],
                "suggestions": ["继续保持学习，多做练习"]
            },
            "knowledge_points": [],
            "report": f"学生已完成 {stats['total_attempts']} 次练习，正确率 {accuracy*100:.1f}%。",
            "summary": f"📊 评估等级：{grade}（正确率 {accuracy*100:.0f}%），继续保持学习！",
            "should_update_path": self._should_update_path(stats)
        }


# 创建工厂函数
def create_evaluation_agent(db: AsyncSession) -> EvaluationAgent:
    """创建评估 Agent"""
    return EvaluationAgent(db)
