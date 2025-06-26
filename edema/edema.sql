-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主機： 127.0.0.1
-- 產生時間： 2025-06-26 05:44:40
-- 伺服器版本： 10.4.32-MariaDB
-- PHP 版本： 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 資料庫： `edema`
--

-- --------------------------------------------------------

--
-- 資料表結構 `device_table`
--

CREATE TABLE `device_table` (
  `test_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `device_table`
--

INSERT INTO `device_table` (`test_id`) VALUES
(5);

-- --------------------------------------------------------

--
-- 資料表結構 `foot_data`
--

CREATE TABLE `foot_data` (
  `id` int(11) NOT NULL,
  `patient_id` int(11) NOT NULL,
  `measurement_time` datetime DEFAULT current_timestamp(),
  `notified` int(10) DEFAULT NULL,
  `point` varchar(767) DEFAULT NULL,
  `point2` varchar(767) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `foot_data`
--

INSERT INTO `foot_data` (`id`, `patient_id`, `measurement_time`, `notified`, `point`, `point2`) VALUES
(1, 1, '2025-05-11 17:13:12', 0, '[120,20.1,22.6,33.5,66.3]', NULL),
(2, 1, '2025-05-26 17:45:17', 0, '[23,50,63.6,98.5,20.1,66,3.1]', NULL),
(3, 2, '2025-06-06 00:19:42', 0, '[123.33,54.45,64.454,23.32]', NULL),
(4, 2, '2025-06-06 00:21:31', 0, '[12.15,26,56,66,22,25,66,52,35]', NULL);

-- --------------------------------------------------------

--
-- 資料表結構 `patients`
--

CREATE TABLE `patients` (
  `patient_id` int(11) NOT NULL,
  `line_id` varchar(100) DEFAULT NULL,
  `name` varchar(50) DEFAULT NULL,
  `height` float DEFAULT NULL,
  `gender` enum('Male','Female','Other') DEFAULT NULL,
  `level` varchar(20) DEFAULT NULL,
  `weight` int(10) DEFAULT NULL,
  `start` int(100) NOT NULL,
  `correction` int(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `patients`
--

INSERT INTO `patients` (`patient_id`, `line_id`, `name`, `height`, `gender`, `level`, `weight`, `start`, `correction`) VALUES
(1, 'U8c2ec195f1507afe1d59302ee3c2b99c', '嗨', NULL, NULL, NULL, 60, 1, 0),
(3, 'U8c2ec195f1507afe1d59302ee3c2b99c', '帥哥', NULL, NULL, NULL, NULL, 1, 0),
(4, 'U8c2ec195f1507afe1d59302ee3c2b99c', '你好', NULL, NULL, NULL, NULL, 0, 0),
(5, 'U8c2ec195f1507afe1d59302ee3c2b99c', '哈哈', NULL, NULL, NULL, NULL, 1, 0),
(6, 'U8c2ec195f1507afe1d59302ee3c2b99c', '哈哈哈', NULL, NULL, NULL, NULL, 0, 0),
(7, 'U8c2ec195f1507afe1d59302ee3c2b99c', '哈哈哈哈', NULL, NULL, NULL, NULL, 0, 0),
(8, 'U8c2ec195f1507afe1d59302ee3c2b99c', '他', NULL, NULL, NULL, NULL, 0, 0);

-- --------------------------------------------------------

--
-- 資料表結構 `questionnaire_results`
--

CREATE TABLE `questionnaire_results` (
  `patient_id` int(11) NOT NULL,
  `submission_time` datetime NOT NULL,
  `q1_a` int(11) DEFAULT NULL,
  `q1_b` int(11) DEFAULT NULL,
  `q2_a` int(11) DEFAULT NULL,
  `q2_b` int(11) DEFAULT NULL,
  `q3_a` int(11) DEFAULT NULL,
  `q3_b` int(11) DEFAULT NULL,
  `q4_a` int(11) DEFAULT NULL,
  `q5_a` int(11) DEFAULT NULL,
  `q5_b` int(11) DEFAULT NULL,
  `q6_a` int(11) DEFAULT NULL,
  `q6_b` int(11) DEFAULT NULL,
  `q7_a` int(11) DEFAULT NULL,
  `q7_b` int(11) DEFAULT NULL,
  `q8_a` int(11) DEFAULT NULL,
  `q8_b` int(11) DEFAULT NULL,
  `q9_a` int(11) DEFAULT NULL,
  `q10_a` int(11) DEFAULT NULL,
  `q10_b` int(11) DEFAULT NULL,
  `q11_a` int(11) DEFAULT NULL,
  `q11_b` int(11) DEFAULT NULL,
  `q12_a` int(11) DEFAULT NULL,
  `q12_b` int(11) DEFAULT NULL,
  `q13_a` int(11) DEFAULT NULL,
  `q13_b` int(11) DEFAULT NULL,
  `q14_a` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `questionnaire_results`
--

INSERT INTO `questionnaire_results` (`patient_id`, `submission_time`, `q1_a`, `q1_b`, `q2_a`, `q2_b`, `q3_a`, `q3_b`, `q4_a`, `q5_a`, `q5_b`, `q6_a`, `q6_b`, `q7_a`, `q7_b`, `q8_a`, `q8_b`, `q9_a`, `q10_a`, `q10_b`, `q11_a`, `q11_b`, `q12_a`, `q12_b`, `q13_a`, `q13_b`, `q14_a`) VALUES
(1, '2025-05-26 17:16:29', NULL, NULL, NULL, 2, NULL, NULL, 0, NULL, 1, NULL, 1, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, NULL, 3, NULL, NULL, 3),
(1, '2025-05-27 12:19:59', NULL, NULL, NULL, NULL, NULL, 3, 0, NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, 4, NULL, 1, NULL, NULL, NULL, NULL, 3),
(1, '2025-05-27 12:27:24', NULL, 1, NULL, 1, NULL, 1, 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 5),
(1, '2025-05-27 12:43:16', NULL, 5, NULL, 1, NULL, 5, 1, NULL, 5, NULL, NULL, NULL, 5, NULL, 5, 1, NULL, 5, NULL, 5, NULL, 5, NULL, 5, 5),
(1, '2025-05-27 15:07:40', NULL, 5, NULL, 5, NULL, 5, 5, NULL, 5, NULL, NULL, NULL, 5, NULL, 5, 5, NULL, 5, NULL, 5, NULL, 5, NULL, 5, 5),
(1, '2025-05-27 15:16:44', NULL, NULL, NULL, 5, NULL, 5, 5, NULL, 5, NULL, 5, NULL, 5, NULL, 5, 5, NULL, 5, NULL, 5, NULL, 5, NULL, NULL, 5);

--
-- 已傾印資料表的索引
--

--
-- 資料表索引 `device_table`
--
ALTER TABLE `device_table`
  ADD PRIMARY KEY (`test_id`);

--
-- 資料表索引 `foot_data`
--
ALTER TABLE `foot_data`
  ADD PRIMARY KEY (`id`),
  ADD KEY `patient_id` (`patient_id`);

--
-- 資料表索引 `patients`
--
ALTER TABLE `patients`
  ADD PRIMARY KEY (`patient_id`);

--
-- 資料表索引 `questionnaire_results`
--
ALTER TABLE `questionnaire_results`
  ADD KEY `patient_id` (`patient_id`);

--
-- 在傾印的資料表使用自動遞增(AUTO_INCREMENT)
--

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `foot_data`
--
ALTER TABLE `foot_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `patients`
--
ALTER TABLE `patients`
  MODIFY `patient_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
