-- =============================================
-- 优化问题求解系统 - SQL Server数据库建库脚本
-- 版本: 2.0
-- 说明: 在SQL Server Management Studio中执行此脚本
-- =============================================

-- 步骤1: 创建数据库
-- 如果数据库已存在则删除（注意：这会删除所有数据！）
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'OptimizationDB')
BEGIN
    ALTER DATABASE OptimizationDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE OptimizationDB;
END
GO

-- 创建新数据库
CREATE DATABASE OptimizationDB;
GO

-- 切换到新数据库
USE OptimizationDB;
GO

-- =============================================
-- 步骤2: 创建测试函数结果表
-- =============================================
CREATE TABLE test_function_results (
    id INT IDENTITY(1,1) PRIMARY KEY,              -- 自增主键
    func_name NVARCHAR(100) NOT NULL,              -- 函数名称（如：Sphere, Rastrigin）
    timestamp NVARCHAR(50) NOT NULL,               -- 求解时间
    best_value FLOAT NOT NULL,                     -- 最优值（适应度值）
    best_position NVARCHAR(MAX),                   -- 最优位置（JSON格式存储坐标）
    convergence_history NVARCHAR(MAX),             -- 收敛历史（JSON格式）
    algorithm_params NVARCHAR(MAX),                -- 算法参数（JSON格式）
    created_at DATETIME DEFAULT GETDATE()          -- 记录创建时间
);
GO

-- 为常用查询字段创建索引，提高查询速度
CREATE INDEX idx_func_name ON test_function_results(func_name);
CREATE INDEX idx_timestamp ON test_function_results(timestamp);
GO

-- =============================================
-- 步骤3: 创建背包问题结果表
-- =============================================
CREATE TABLE knapsack_results (
    id INT IDENTITY(1,1) PRIMARY KEY,              -- 自增主键
    timestamp NVARCHAR(50) NOT NULL,               -- 求解时间
    max_value INT NOT NULL,                        -- 最大价值
    selected_items NVARCHAR(MAX),                  -- 选中的物品列表（JSON格式）
    total_weight INT NOT NULL,                     -- 总重量
    optimization_history NVARCHAR(MAX),            -- 优化历史（JSON格式）
    problem_params NVARCHAR(MAX),                  -- 问题参数（JSON格式）
    created_at DATETIME DEFAULT GETDATE()          -- 记录创建时间
);
GO

-- 为时间戳创建索引
CREATE INDEX idx_knapsack_timestamp ON knapsack_results(timestamp);
GO

-- =============================================
-- 步骤4: 插入示例数据（可选）
-- =============================================

-- 插入测试函数示例数据
INSERT INTO test_function_results 
(func_name, timestamp, best_value, best_position, convergence_history, algorithm_params)
VALUES 
('SPHERE', '2024-01-01 10:00:00', 0.00123, 
 '[0.0234, -0.0156]', 
 '[{"iteration": 1, "value": 15.234}, {"iteration": 2, "value": 8.123}]',
 '{"max_iter": 100, "swarm_size": 30, "w": 0.7, "c1": 1.5, "c2": 1.5, "dims": 2}');

-- 插入背包问题示例数据
INSERT INTO knapsack_results 
(timestamp, max_value, selected_items, total_weight, optimization_history, problem_params)
VALUES 
('2024-01-01 10:05:00', 20, 
 '["笔记本电脑", "相机", "耳机"]', 
 11, 
 '[{"item": 1, "max_value": 3}, {"item": 2, "max_value": 7}]',
 '{"capacity": 20, "items": ["笔记本电脑", "平板电脑", "相机", "耳机", "无人机"], "weights": [2, 3, 4, 5, 9], "values": [3, 4, 8, 8, 10]}');
GO

-- =============================================
-- 步骤5: 创建视图（方便查询）
-- =============================================

-- 创建测试函数结果汇总视图
CREATE VIEW vw_test_results_summary AS
SELECT 
    func_name AS 函数名称,
    COUNT(*) AS 求解次数,
    MIN(best_value) AS 最优值,
    AVG(best_value) AS 平均值,
    MAX(timestamp) AS 最后求解时间
FROM test_function_results
GROUP BY func_name;
GO

-- 创建背包问题结果汇总视图
CREATE VIEW vw_knapsack_results_summary AS
SELECT 
    MAX(max_value) AS 历史最大价值,
    AVG(CAST(max_value AS FLOAT)) AS 平均价值,
    AVG(CAST(total_weight AS FLOAT)) AS 平均重量,
    COUNT(*) AS 求解次数
FROM knapsack_results;
GO

-- =============================================
-- 步骤6: 创建存储过程（可选的高级功能）
-- =============================================

-- 存储过程：获取指定函数的最佳结果
CREATE PROCEDURE sp_get_best_result
    @func_name NVARCHAR(100)
AS
BEGIN
    SELECT TOP 1 
        id,
        func_name,
        timestamp,
        best_value,
        best_position,
        algorithm_params
    FROM test_function_results
    WHERE func_name = @func_name
    ORDER BY best_value ASC;
END;
GO

-- 存储过程：清理旧数据（保留最近N条记录）
CREATE PROCEDURE sp_cleanup_old_records
    @keep_count INT = 100
AS
BEGIN
    -- 清理测试函数结果
    DELETE FROM test_function_results
    WHERE id NOT IN (
        SELECT TOP (@keep_count) id 
        FROM test_function_results 
        ORDER BY id DESC
    );
    
    -- 清理背包问题结果
    DELETE FROM knapsack_results
    WHERE id NOT IN (
        SELECT TOP (@keep_count) id 
        FROM knapsack_results 
        ORDER BY id DESC
    );
    
    -- 返回清理的记录数
    SELECT @@ROWCOUNT AS deleted_rows;
END;
GO

-- =============================================
-- 步骤7: 创建用户和授权（生产环境推荐）
-- =============================================

-- 创建专用登录账户（请修改密码）
-- CREATE LOGIN OptimizationUser WITH PASSWORD = 'YourStrongPassword123!';
-- GO

-- 创建数据库用户
-- USE OptimizationDB;
-- CREATE USER OptimizationUser FOR LOGIN OptimizationUser;
-- GO

-- 授予权限
-- GRANT SELECT, INSERT, UPDATE, DELETE ON test_function_results TO OptimizationUser;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON knapsack_results TO OptimizationUser;
-- GO

-- =============================================
-- 步骤8: 验证安装
-- =============================================

-- 查看所有表
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE';
GO

-- 查看测试函数结果表结构
EXEC sp_help 'test_function_results';
GO

-- 查看背包问题结果表结构
EXEC sp_help 'knapsack_results';
GO

-- 查询示例数据
SELECT * FROM test_function_results;
SELECT * FROM knapsack_results;
GO

-- 查看视图
SELECT * FROM vw_test_results_summary;
SELECT * FROM vw_knapsack_results_summary;
GO

-- =============================================
-- 常用查询语句
-- =============================================

-- 1. 查询最近10条测试结果
-- SELECT TOP 10 * FROM test_function_results ORDER BY id DESC;

-- 2. 查询某个函数的所有结果
-- SELECT * FROM test_function_results WHERE func_name = 'SPHERE';

-- 3. 查询最优值小于某个阈值的结果
-- SELECT * FROM test_function_results WHERE best_value < 0.01;

-- 4. 查询背包问题中价值最高的结果
-- SELECT TOP 1 * FROM knapsack_results ORDER BY max_value DESC;

-- 5. 按日期统计求解次数
-- SELECT CAST(timestamp AS DATE) AS date, COUNT(*) AS count
-- FROM test_function_results
-- GROUP BY CAST(timestamp AS DATE)
-- ORDER BY date DESC;

PRINT '数据库创建成功！';
PRINT '请在Python程序中使用以下连接信息：';
PRINT '服务器: localhost';
PRINT '数据库: OptimizationDB';
PRINT '用户名: sa（或你创建的用户）';
GO