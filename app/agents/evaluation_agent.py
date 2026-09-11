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

        # 用真实答题数据按知识点分组计算掌握度，覆盖 LLM 虚构的知识点分数
        kp_stats = self._calculate_kp_stats(learning_records, stage_kps)
        result["knowledge_points"] = kp_stats

        # 修正知识点分数：确保总和不超过实际总分
        result = self._fix_kp_scores(result, learning_stats)

        # ── 确定性覆盖：mastery_level 与 weaknesses 不信 LLM ──
        # mastery = 按题目分值加权的真实掌握度（纯数学）
        det_mastery = self._calc_deterministic_mastery(kp_stats)
        if learning_stats.get("total_attempts", 0) > 0:
            result["mastery_level"] = det_mastery
        # weakness = 答题数据中 status=="薄弱" 的知识点（非自由文本；即使为空也覆盖，清掉 LLM 幻觉）
        det_weaknesses = [kp["topic"] for kp in kp_stats if kp.get("status") == "薄弱" and kp.get("topic")]
        analysis = result.get("analysis")
        if not isinstance(analysis, dict):
            analysis = {}
        analysis["weaknesses"] = det_weaknesses
        # strengths/suggestions 仍保留 LLM 的叙述性内容
        if isinstance((result.get("analysis") or {}).get("strengths"), list):
            analysis["strengths"] = result["analysis"]["strengths"]
        if isinstance((result.get("analysis") or {}).get("suggestions"), list):
            analysis["suggestions"] = result["analysis"]["suggestions"]
        result["analysis"] = analysis

        # 路径调整建议：基于确定性数据的三条规则（供 API 层裁决，Agent 不直接改路径）
        result["should_update_path"] = self._should_update_path_deterministic(learning_stats, det_mastery, det_weaknesses)

        # 确保 summary 字段存在（LLM 可能漏掉）
        if "summary" not in result or not result["summary"]:
            result["summary"] = self._build_auto_summary(result, stage_trend)

        await self._update_student_profile(user_id, result)

        # 记录当前已完成阶段数，供后续判断是否需要重新评估
        result["_completed_stages_count"] = await self._get_completed_stages_count(user_id)

        # 保存评估报告到数据库
        await self._save_report_to_db(user_id, result)

        log.info(f"EvaluationAgent 完成评估，学生 {user_id} 评估等级: {result.get('overall_grade')}")
        return result

    def _calc_deterministic_mastery(self, kp_stats: List[Dict]) -> float:
        """按题目分值加权的真实掌握度（纯数学，无 LLM 参与）"""
        weighted = 0.0
        total_w = 0.0
        for kp in kp_stats:
            w = float(kp.get("total") or 0)
            if w <= 0:
                continue
            weighted += float(kp.get("mastery") or 0) * w
            total_w += w
        return round(weighted / total_w, 4) if total_w > 0 else 0.0

    def _should_update_path_deterministic(
        self, stats: Dict, mastery: float, weaknesses: List[str]
    ) -> bool:
        """路径调整建议：三条确定性规则（输入全部来自真实答题数据）

        满足任一即建议更新：
        1. 总正确率 < 50% 且练习量 ≥ 3
        2. 出现「薄弱」状态的知识点 ≥ 2 个
        3. 掌握度 < 40% 且已有练习
        """
        attempts = stats.get("total_attempts", 0)
        accuracy = stats.get("accuracy_rate", 0)
        if attempts >= 3 and accuracy < 0.5:
            return True
        if len(weaknesses) >= 2:
            return True
        if attempts > 0 and mastery < 0.4:
            return True
        return False

    async def maybe_adjust_path(self, user_id: int, eval_result: Dict) -> bool:
        """根据确定性评估结果增量更新学习路径（由 API 层调用，Agent 不在 run 内直调）

        更新条件（与 _should_update_path_deterministic 同源，二次校验）：
        1. should_update_path 标志为真
        2. 或薄弱点集合相对画像发生实质变化

        Returns: True=路径已更新，False=无需更新
        """
        from app.models import AsyncSessionLocal, LearningPath, StudentProfile

        if not eval_result.get("should_update_path"):
            log.info(f"用户 {user_id} 评估未建议路径更新，跳过")
            return False

        try:
            async with AsyncSessionLocal() as db:
                profile_result = await db.execute(
                    select(StudentProfile).where(
                        StudentProfile.user_id == user_id,
                        StudentProfile.is_active == True,
                    )
                )
                profile = profile_result.scalar_one_or_none()

                # 薄弱点相对画像是否有新增（信息日志用；裁决已由 should_update_path 完成）
                old_weaknesses = set(profile.weakness or []) if profile else set()
                new_weaknesses = set(
                    (eval_result.get("analysis") or {}).get("weaknesses") or []
                )
                has_new_weakness = bool(new_weaknesses - old_weaknesses)
                if has_new_weakness:
                    log.info(f"用户 {user_id} 出现新薄弱点: {new_weaknesses - old_weaknesses}")

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

                # 路径规划由独立 Agent 执行（决策与执行分离）
                from app.agents.learning_path_agent import LearningPathAgent
                path_agent = LearningPathAgent(db)
                new_path_data = await path_agent.run(user_id, profile=self._profile_to_dict(profile))

                if new_path_data and new_path_data.get("stages"):
                    new_stages = new_path_data["stages"]
                    max_existing_id = max((s.get("stage_id", 0) for s in stages), default=0)
                    for i, s in enumerate(new_stages):
                        s["stage_id"] = max_existing_id + i + 1
                    updated_stages = locked_stages + new_stages
                    path.stages = updated_stages
                    path.path_version = (path.path_version or 1) + 1
                    db.add(path)
                    await db.commit()
                    log.info(
                        f"用户 {user_id} 路径已增量更新（版本 {path.path_version}），"
                        f"新增阶段 id {max_existing_id + 1}-{max_existing_id + len(new_stages)}"
                    )
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

    async def _get_completed_stages_count(self, user_id: int) -> int:
        """获取当前已完成阶段数"""
        from app.models import LearningPath
        try:
            result = await self.db.execute(
                select(LearningPath).where(LearningPath.user_id == user_id)
                .order_by(LearningPath.created_at.desc()).limit(1)
            )
            path = result.scalar_one_or_none()
            return len(path.completed_stages) if path and path.completed_stages else 0
        except Exception:
            return 0

    def _calculate_kp_stats(self, records: List[LearningRecord], stage_kps: List[str] = None) -> List[Dict]:
        """按知识点分组计算掌握度，直接从答题记录中提取，不依赖 LLM"""
        # 按 knowledge_point 分组统计
        kp_data: Dict[str, Dict] = {}

        for r in records:
            behavior = r.behavior_data if isinstance(r.behavior_data, dict) else {}
            kp = behavior.get("knowledge_point") or behavior.get("topic") or "通用"

            if kp not in kp_data:
                kp_data[kp] = {"total": 0, "correct": 0, "score": 0, "max_score": 0}

            kp_data[kp]["total"] += 1
            kp_data[kp]["max_score"] += 10  # 每题满分10分
            if r.correct:
                kp_data[kp]["correct"] += 1
            if r.score is not None:
                kp_data[kp]["score"] += r.score

        # 构建知识点评估列表
        result_kps = []
        for kp_name, data in kp_data.items():
            mastery = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            score = data["score"]
            total = data["max_score"]

            if mastery >= 0.8:
                status = "掌握"
            elif mastery >= 0.3:
                status = "学习中"
            else:
                status = "薄弱"

            result_kps.append({
                "topic": kp_name,
                "score": score,
                "total": total,
                "mastery": round(mastery, 2),
                "status": status,
            })

        # 补充未考查的知识点（标记为"未考查"而非"未学习"）
        if stage_kps:
            existing = {kp["topic"] for kp in result_kps}
            for kp_name in stage_kps:
                if kp_name not in existing:
                    result_kps.append({
                        "topic": kp_name,
                        "score": 0,
                        "total": 10,
                        "mastery": 0.0,
                        "status": "未考查",
                    })

        return result_kps

    def _fix_kp_scores(self, result: Dict, stats: Dict) -> Dict:
        """修正知识点分数：确保单项不超过满分，总和不超过实际总分"""
        kps = result.get("knowledge_points", [])
        if not kps:
            return result

        actual_total_score = stats.get("total_score", 0)

        # 确保每个知识点的 score 不超过 total
        for kp in kps:
            if kp.get("score", 0) > kp.get("total", 10):
                kp["score"] = kp.get("total", 10)

        # 确保所有知识点分数总和不超过实际总分
        final_total = sum(kp.get("score", 0) for kp in kps)
        if final_total > actual_total_score and actual_total_score >= 0:
            diff = final_total - actual_total_score
            # 从最高分知识点开始扣减
            sorted_indices = sorted(range(len(kps)), key=lambda i: kps[i].get("score", 0), reverse=True)
            for idx in sorted_indices:
                if diff <= 0:
                    break
                deduct = min(diff, kps[idx].get("score", 0))
                kps[idx]["score"] = kps[idx].get("score", 0) - deduct
                diff -= deduct

        # 更新 result 中的 total_score 为实际值
        result["total_score"] = actual_total_score

        return result

    async def _get_stage_knowledge_points(self, user_id: int) -> List[str]:
        """从学习路径获取所有已完成阶段 + 当前阶段的知识点名称列表"""
        from app.models import LearningPath
        try:
            result = await self.db.execute(
                select(LearningPath).where(LearningPath.user_id == user_id)
                .order_by(LearningPath.created_at.desc()).limit(1)
            )
            path = result.scalar_one_or_none()
            if not path or not path.stages:
                return []

            completed_ids = path.completed_stages or []
            kps_set = set()

            # 收集所有已完成阶段的知识点
            if completed_ids:
                for stage in path.stages:
                    if stage.get("stage_id") in completed_ids:
                        for kp in stage.get("knowledge_points", []):
                            if isinstance(kp, dict):
                                name = kp.get("name", "")
                                if name:
                                    kps_set.add(name)
                            elif kp:
                                kps_set.add(str(kp))

            # 也收集当前（最近完成或第一个）阶段的知识点
            if not completed_ids:
                target_stage = path.stages[0]
            else:
                last_completed_id = completed_ids[-1]
                target_stage = None
                for stage in path.stages:
                    if stage.get("stage_id") == last_completed_id:
                        target_stage = stage
                        break
                if target_stage is None:
                    target_stage = path.stages[0]

            if target_stage:
                for kp in target_stage.get("knowledge_points", []):
                    if isinstance(kp, dict):
                        name = kp.get("name", "")
                        if name:
                            kps_set.add(name)
                    elif kp:
                        kps_set.add(str(kp))

            return list(kps_set)
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
