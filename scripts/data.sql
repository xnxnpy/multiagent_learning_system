/*
SQLyog Community v13.1.6 (64 bit)
MySQL - 8.0.40 : Database - ai_learning
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`ai_learning` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `ai_learning`;

/*Table structure for table `assignment_submissions` */

DROP TABLE IF EXISTS `assignment_submissions`;

CREATE TABLE `assignment_submissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint NOT NULL,
  `student_id` bigint NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `submitted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `score` bigint DEFAULT NULL,
  `feedback` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_assignment_submissions_id` (`id`),
  KEY `ix_assignment_submissions_student_id` (`student_id`),
  KEY `ix_assignment_submissions_assignment_id` (`assignment_id`),
  CONSTRAINT `assignment_submissions_ibfk_1` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`),
  CONSTRAINT `assignment_submissions_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `assignment_submissions` */

/*Table structure for table `assignments` */

DROP TABLE IF EXISTS `assignments`;

CREATE TABLE `assignments` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `teacher_id` bigint NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `due_date` datetime DEFAULT NULL,
  `target_students` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `assigned_at` datetime DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_assignments_id` (`id`),
  KEY `ix_assignments_teacher_id` (`teacher_id`),
  CONSTRAINT `assignments_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `assignments` */

/*Table structure for table `courses` */

DROP TABLE IF EXISTS `courses`;

CREATE TABLE `courses` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `teacher_id` bigint NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `knowledge_tree` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `teacher_id` (`teacher_id`),
  KEY `ix_courses_id` (`id`),
  CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `courses` */

/*Table structure for table `evaluation_reports` */

DROP TABLE IF EXISTS `evaluation_reports`;

CREATE TABLE `evaluation_reports` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `overall_grade` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `total_score` float DEFAULT NULL,
  `accuracy_rate` float DEFAULT NULL,
  `mastery_level` float DEFAULT NULL,
  `report_data` json NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_evaluation_reports_id` (`id`),
  KEY `ix_er_user_created` (`user_id`,`created_at`),
  CONSTRAINT `evaluation_reports_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `evaluation_reports` */

/*Table structure for table `knowledge_documents` */

DROP TABLE IF EXISTS `knowledge_documents`;

CREATE TABLE `knowledge_documents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `filename` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_size` int NOT NULL COMMENT '文件大小（字节）',
  `file_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型：pdf/docx/txt/md',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'processing/completed/failed',
  `chunk_count` int DEFAULT NULL COMMENT '分块数量',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '处理失败时的错误信息',
  `uploaded_by` bigint NOT NULL COMMENT '上传者用户 ID',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `completed_at` datetime DEFAULT NULL COMMENT '处理完成时间',
  PRIMARY KEY (`id`),
  KEY `ix_knowledge_documents_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `knowledge_documents` */

/*Table structure for table `learning_paths` */

DROP TABLE IF EXISTS `learning_paths`;

CREATE TABLE `learning_paths` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stages` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `completed_stages` json DEFAULT (json_array()),
  `path_version` bigint DEFAULT '1' COMMENT '路径版本号，每次更新 +1',
  `profile_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lp_user_profile` (`user_id`,`profile_id`),
  KEY `ix_learning_paths_id` (`id`),
  KEY `ix_learning_paths_user_id` (`user_id`),
  KEY `ix_learning_paths_profile_id` (`profile_id`),
  CONSTRAINT `learning_paths_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `learning_paths` */

/*Table structure for table `learning_records` */

DROP TABLE IF EXISTS `learning_records`;

CREATE TABLE `learning_records` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `resource_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_id` bigint DEFAULT NULL,
  `correct` tinyint(1) DEFAULT NULL,
  `score` float DEFAULT NULL,
  `duration_seconds` int DEFAULT NULL,
  `behavior_data` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_learning_records_id` (`id`),
  CONSTRAINT `learning_records_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `learning_records` */

/*Table structure for table `learning_resources` */

DROP TABLE IF EXISTS `learning_resources`;

CREATE TABLE `learning_resources` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `resource_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `topic` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` json NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `stage_id` bigint DEFAULT NULL,
  `profile_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lr_res_profile_stage_type_topic` (`user_id`,`profile_id`,`stage_id`,`resource_type`,`topic`),
  KEY `ix_learning_resources_id` (`id`),
  KEY `ix_lr_user_type_created` (`user_id`,`resource_type`,`created_at`),
  KEY `ix_lr_user_stage_type_created` (`user_id`,`stage_id`,`resource_type`,`created_at`),
  KEY `ix_learning_resources_profile_id` (`profile_id`),
  KEY `ix_lr_lookup` (`user_id`,`profile_id`,`stage_id`,`resource_type`,`created_at`),
  CONSTRAINT `learning_resources_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `learning_resources` */

/*Table structure for table `profile_chat_messages` */

DROP TABLE IF EXISTS `profile_chat_messages`;

CREATE TABLE `profile_chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `profile_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_profile_chat_messages_session_id` (`session_id`),
  KEY `ix_profile_chat_messages_user_id` (`user_id`),
  KEY `ix_profile_chat_messages_id` (`id`),
  KEY `ix_profile_chat_messages_profile_id` (`profile_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `profile_chat_messages` */

/*Table structure for table `resource_reviews` */

DROP TABLE IF EXISTS `resource_reviews`;

CREATE TABLE `resource_reviews` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `resource_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator_id` bigint NOT NULL,
  `reviewer_id` bigint DEFAULT NULL,
  `review_comment` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `reviewed_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `creator_id` (`creator_id`),
  KEY `reviewer_id` (`reviewer_id`),
  KEY `ix_resource_reviews_id` (`id`),
  CONSTRAINT `resource_reviews_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `users` (`id`),
  CONSTRAINT `resource_reviews_ibfk_2` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `resource_reviews` */

/*Table structure for table `student_profiles` */

DROP TABLE IF EXISTS `student_profiles`;

CREATE TABLE `student_profiles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `major` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grade` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `goal` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `knowledge_level` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `learning_style` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `weakness` json DEFAULT NULL,
  `interests` json DEFAULT NULL,
  `coding_ability` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `profile_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '默认画像',
  `is_active` tinyint(1) DEFAULT '1',
  `is_archived` tinyint(1) DEFAULT '0',
  `archived_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_student_profiles_id` (`id`),
  KEY `ix_student_profiles_is_active` (`is_active`),
  KEY `ix_student_profiles_is_archived` (`is_archived`),
  KEY `ix_student_profiles_user_id` (`user_id`),
  KEY `idx_student_profiles_user_active` (`user_id`,`is_active`),
  CONSTRAINT `student_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `student_profiles` */

/*Table structure for table `system_config` */

DROP TABLE IF EXISTS `system_config`;

CREATE TABLE `system_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_system_config_config_key` (`config_key`),
  KEY `ix_system_config_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `system_config` */

/*Table structure for table `tutor_chat_messages` */

DROP TABLE IF EXISTS `tutor_chat_messages`;

CREATE TABLE `tutor_chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '给大模型用的完整内容（含 OCR 文本）',
  `display_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '给用户显示的原始输入（不含 OCR 文本）',
  `image_base64` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户上传的题目图片 base64（仅 role=user 时有值）',
  `image_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '图片文件名',
  `image_size` bigint DEFAULT NULL COMMENT '图片文件大小（字节）',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_tutor_chat_messages_id` (`id`),
  KEY `ix_tutor_chat_messages_session_id` (`session_id`),
  KEY `ix_tutor_chat_messages_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `tutor_chat_messages` */

/*Table structure for table `users` */

DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `real_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `users` */

/*Table structure for table `workflow_states` */

DROP TABLE IF EXISTS `workflow_states`;

CREATE TABLE `workflow_states` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint NOT NULL,
  `state_data` json NOT NULL COMMENT '工作流状态 JSON',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_workflow_states_session_id` (`session_id`),
  KEY `ix_workflow_states_id` (`id`),
  KEY `ix_workflow_states_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `workflow_states` */

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
