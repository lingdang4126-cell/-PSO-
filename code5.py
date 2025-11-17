"""
优化问题求解系统 - 增强版
功能：
1. 支持SQL Server和SQLite双数据库
2. 可调节优化算法参数
3. 可自定义背包问题参数
4. 详细的代码注释
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime
import json

# ===== 修复 Matplotlib 中文/符号显示为方框 =====
import matplotlib
# 优先使用系统自带的微软字体（Windows 完美支持中文 + ¥ + 部分emoji）
matplotlib.rcParams['font.sans-serif'] = [
    'Microsoft YaHei',    # Windows 简体中文主力字体
    'SimHei',             # 黑体（备用）
    'Arial Unicode MS',   # 含大量符号
    'DejaVu Sans'         # Matplotlib 默认，保底
]
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['axes.unicode_minus'] = False  # 负号正常显示，防止 - 变成方框

# ============================================
# 尝试导入SQL Server库（如果没安装也能运行）
try:
    import pyodbc
    HAS_SQLSERVER = True
except ImportError:
    HAS_SQLSERVER = False
    print("未安装pyodbc，SQL Server功能不可用，仅使用SQLite")


# ==================== 数据库管理类 ====================
class DatabaseManager:
    """
    数据库管理器
    功能：统一管理SQLite和SQL Server两种数据库
    """
    def __init__(self):
        self.db_type = 'sqlite'  # 默认使用SQLite
        self.connection = None
        self.connected = False
        
    def init_sqlite(self):
        """初始化SQLite数据库（本地文件数据库）"""
        try:
            conn = sqlite3.connect('optimization_results.db')
            cursor = conn.cursor()
            
            # 创建测试函数结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_function_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    func_name TEXT,
                    timestamp TEXT,
                    best_value REAL,
                    best_position TEXT,
                    convergence_history TEXT,
                    algorithm_params TEXT
                )
            ''')
            
            # 创建背包问题结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knapsack_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    max_value INTEGER,
                    selected_items TEXT,
                    total_weight INTEGER,
                    optimization_history TEXT,
                    problem_params TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            self.db_type = 'sqlite'
            self.connected = True
            return True, "SQLite数据库初始化成功"
        except Exception as e:
            return False, f"SQLite初始化失败: {str(e)}"
    
    def connect_sqlserver(self, server, database, username, password):
        """
        连接SQL Server数据库
        参数说明：
        - server: 服务器地址，如 'localhost' 或 '127.0.0.1'
        - database: 数据库名称
        - username: 用户名
        - password: 密码
        """
        if not HAS_SQLSERVER:
            return False, "未安装pyodbc库，无法连接SQL Server"
        
        try:
            # 构建连接字符串
            conn_str = (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={server};'
                f'DATABASE={database};'
                f'UID={username};'
                f'PWD={password}'
            )
            
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # 创建测试函数结果表
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='test_function_results' AND xtype='U')
                CREATE TABLE test_function_results (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    func_name NVARCHAR(100),
                    timestamp NVARCHAR(50),
                    best_value FLOAT,
                    best_position NVARCHAR(MAX),
                    convergence_history NVARCHAR(MAX),
                    algorithm_params NVARCHAR(MAX)
                )
            ''')
            
            # 创建背包问题结果表
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='knapsack_results' AND xtype='U')
                CREATE TABLE knapsack_results (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    timestamp NVARCHAR(50),
                    max_value INT,
                    selected_items NVARCHAR(MAX),
                    total_weight INT,
                    optimization_history NVARCHAR(MAX),
                    problem_params NVARCHAR(MAX)
                )
            ''')
            
            conn.commit()
            self.connection = conn
            self.db_type = 'sqlserver'
            self.connected = True
            return True, "SQL Server连接成功"
        except Exception as e:
            return False, f"SQL Server连接失败: {str(e)}"
    
    def save_test_result(self, func_name, best_value, best_position, history, params):
        """保存测试函数优化结果到数据库"""
        if not self.connected:
            return False, "未连接数据库"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            if self.db_type == 'sqlite':
                conn = sqlite3.connect('optimization_results.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO test_function_results 
                    (func_name, timestamp, best_value, best_position, convergence_history, algorithm_params)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (func_name, timestamp, float(best_value), 
                      json.dumps(best_position), json.dumps(history), json.dumps(params)))
                conn.commit()
                conn.close()
            else:  # SQL Server
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO test_function_results 
                    (func_name, timestamp, best_value, best_position, convergence_history, algorithm_params)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (func_name, timestamp, float(best_value),
                      json.dumps(best_position), json.dumps(history), json.dumps(params)))
                self.connection.commit()
            
            return True, "保存成功"
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    def save_knapsack_result(self, max_value, selected_items, total_weight, history, params):
        """保存背包问题优化结果到数据库"""
        if not self.connected:
            return False, "未连接数据库"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            if self.db_type == 'sqlite':
                conn = sqlite3.connect('optimization_results.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO knapsack_results 
                    (timestamp, max_value, selected_items, total_weight, optimization_history, problem_params)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, max_value, json.dumps(selected_items),
                      total_weight, json.dumps(history), json.dumps(params)))
                conn.commit()
                conn.close()
            else:  # SQL Server
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO knapsack_results 
                    (timestamp, max_value, selected_items, total_weight, optimization_history, problem_params)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, max_value, json.dumps(selected_items),
                      total_weight, json.dumps(history), json.dumps(params)))
                self.connection.commit()
            
            return True, "保存成功"
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    def load_test_results(self, limit=10):
        """从数据库加载测试函数历史结果"""
        if not self.connected:
            return []
        
        try:
            if self.db_type == 'sqlite':
                conn = sqlite3.connect('optimization_results.db')
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT timestamp, func_name, best_value, best_position, algorithm_params
                    FROM test_function_results 
                    ORDER BY id DESC LIMIT {limit}
                ''')
                results = cursor.fetchall()
                conn.close()
            else:  # SQL Server
                cursor = self.connection.cursor()
                cursor.execute(f'''
                    SELECT TOP {limit} timestamp, func_name, best_value, best_position, algorithm_params
                    FROM test_function_results 
                    ORDER BY id DESC
                ''')
                results = cursor.fetchall()
            
            return results
        except Exception as e:
            print(f"加载数据失败: {str(e)}")
            return []


# ==================== 测试函数定义 ====================
class TestFunctions:
    """
    优化测试函数集合
    这些函数用于测试优化算法的性能
    """
    @staticmethod
    def sphere(x):
        """
        球函数 (Sphere Function)
        特点：单峰函数，全局最优解在原点(0,0,...,0)
        公式：f(x) = Σ(xi^2)
        """
        return np.sum(x**2)
    
    @staticmethod
    def rastrigin(x):
        """
        Rastrigin函数
        特点：多峰函数，有很多局部最优解
        公式：f(x) = 10n + Σ[xi^2 - 10cos(2πxi)]
        """
        n = len(x)
        return 10*n + np.sum(x**2 - 10*np.cos(2*np.pi*x))
    
    @staticmethod
    def rosenbrock(x):
        """
        Rosenbrock函数（香蕉函数）
        特点：最优解在一个狭长的抛物线山谷中，难以优化
        公式：f(x) = Σ[100(x[i+1] - xi^2)^2 + (1-xi)^2]
        """
        return np.sum(100*(x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2)
    
    @staticmethod
    def ackley(x):
        """
        Ackley函数
        特点：多峰函数，有大量局部最优解
        """
        n = len(x)
        sum1 = np.sum(x**2)
        sum2 = np.sum(np.cos(2*np.pi*x))
        return -20*np.exp(-0.2*np.sqrt(sum1/n)) - np.exp(sum2/n) + 20 + np.e
    
    @staticmethod
    def griewank(x):
        """
        Griewank函数
        特点：多峰函数，有大量周期性局部最优解
        公式：f(x) = 1 + Σ(xi^2)/4000 - Π(cos(xi/√i))
        """
        sum_part = np.sum(x**2) / 4000
        prod_part = np.prod(np.cos(x / np.sqrt(np.arange(1, len(x) + 1))))
        return sum_part - prod_part + 1
    
    @staticmethod
    def schwefel(x):
        """
        Schwefel函数
        特点：欺骗性强，全局最优远离局部最优
        公式：f(x) = 418.9829n - Σ(xi*sin(√|xi|))
        """
        n = len(x)
        return 418.9829 * n - np.sum(x * np.sin(np.sqrt(np.abs(x))))
    
    @staticmethod
    def levy(x):
        """
        Levy函数
        特点：多峰函数，有多个局部最优
        """
        w = 1 + (x - 1) / 4
        term1 = np.sin(np.pi * w[0])**2
        term2 = np.sum((w[:-1] - 1)**2 * (1 + 10 * np.sin(np.pi * w[:-1] + 1)**2))
        term3 = (w[-1] - 1)**2 * (1 + np.sin(2 * np.pi * w[-1])**2)
        return term1 + term2 + term3
    
    @staticmethod
    def zakharov(x):
        """
        Zakharov函数
        特点：单峰函数，比Sphere稍复杂
        公式：f(x) = Σ(xi^2) + (Σ(0.5*i*xi))^2 + (Σ(0.5*i*xi))^4
        """
        sum1 = np.sum(x**2)
        sum2 = np.sum(0.5 * np.arange(1, len(x) + 1) * x)
        return sum1 + sum2**2 + sum2**4
    
    @staticmethod
    def dixon_price(x):
        """
        Dixon-Price函数
        特点：单峰函数，对角线形状的山谷
        """
        n = len(x)
        term1 = (x[0] - 1)**2
        term2 = np.sum(np.arange(2, n + 1) * (2 * x[1:]**2 - x[:-1])**2)
        return term1 + term2
    
    @staticmethod
    def michalewicz(x):
        """
        Michalewicz函数
        特点：多峰函数，峰的数量取决于维度
        """
        m = 10
        i = np.arange(1, len(x) + 1)
        return -np.sum(np.sin(x) * np.sin(i * x**2 / np.pi)**(2 * m))
    
    @staticmethod
    def styblinski_tang(x):
        """
        Styblinski-Tang函数
        特点：多峰函数，全局最优为负值
        公式：f(x) = Σ(xi^4 - 16xi^2 + 5xi) / 2
        """
        return np.sum(x**4 - 16 * x**2 + 5 * x) / 2


# ==================== PSO粒子群优化算法 ====================
class PSO:
    """
    粒子群优化算法 (Particle Swarm Optimization)
    
    原理：
    模拟鸟群觅食行为，每个粒子代表一个解
    粒子根据自己的经验（个体最优）和群体经验（全局最优）更新位置
    
    参数说明：
    - func: 目标函数
    - dims: 维度（变量个数）
    - bounds: 搜索范围，如(-5, 5)
    - max_iter: 最大迭代次数
    - swarm_size: 粒子群大小（粒子数量）
    - w: 惯性权重（控制上一次速度的影响）
    - c1: 个体学习因子（向个体最优位置移动的程度）
    - c2: 社会学习因子（向全局最优位置移动的程度）
    """
    def __init__(self, func, dims=2, bounds=(-5, 5), max_iter=100, 
                 swarm_size=30, w=0.7, c1=1.5, c2=1.5):
        self.func = func
        self.dims = dims
        self.bounds = bounds
        self.max_iter = max_iter
        self.swarm_size = swarm_size
        self.w = w
        self.c1 = c1
        self.c2 = c2
        
    def optimize(self):
        """执行PSO优化"""
        # 步骤1: 随机初始化粒子群的位置和速度
        positions = np.random.uniform(self.bounds[0], self.bounds[1], 
                                     (self.swarm_size, self.dims))
        velocities = np.random.uniform(-abs(self.bounds[1]-self.bounds[0]), 
                                      abs(self.bounds[1]-self.bounds[0]),
                                      (self.swarm_size, self.dims))
        
        # 步骤2: 初始化个体最优位置和值
        pbest_positions = positions.copy()
        pbest_values = np.array([self.func(p) for p in positions])
        
        # 步骤3: 初始化全局最优位置和值
        gbest_idx = np.argmin(pbest_values)
        gbest_position = pbest_positions[gbest_idx].copy()
        gbest_value = pbest_values[gbest_idx]
        
        history = []  # 记录每次迭代的最优值
        
        # 步骤4: 迭代优化
        for iteration in range(self.max_iter):
            for i in range(self.swarm_size):
                r1, r2 = np.random.rand(2)  # 随机数，增加随机性
                
                # 步骤5: 更新速度（核心公式）
                # v = w*v + c1*r1*(pbest - x) + c2*r2*(gbest - x)
                velocities[i] = (self.w * velocities[i] + 
                               self.c1 * r1 * (pbest_positions[i] - positions[i]) +
                               self.c2 * r2 * (gbest_position - positions[i]))
                
                # 步骤6: 更新位置
                positions[i] += velocities[i]
                # 确保位置在搜索范围内
                positions[i] = np.clip(positions[i], self.bounds[0], self.bounds[1])
                
                # 步骤7: 评估新位置的适应度
                current_value = self.func(positions[i])
                
                # 步骤8: 更新个体最优
                if current_value < pbest_values[i]:
                    pbest_values[i] = current_value
                    pbest_positions[i] = positions[i].copy()
                    
                    # 步骤9: 更新全局最优
                    if current_value < gbest_value:
                        gbest_value = current_value
                        gbest_position = positions[i].copy()
            
            # 记录本次迭代的结果
            history.append({'iteration': iteration + 1, 'value': gbest_value})
        
        return {
            'best_position': gbest_position,
            'best_value': gbest_value,
            'history': history
        }


# ==================== 背包问题求解器 ====================
class KnapsackSolver:
    """
    0-1背包问题求解器（动态规划算法）
    
    问题描述：
    有n个物品，每个物品有重量weight[i]和价值value[i]
    背包容量为capacity
    求：在不超过容量的前提下，能装入背包的最大价值
    
    动态规划思路：
    dp[i][w] 表示前i个物品，背包容量为w时的最大价值
    转移方程：
    - 如果不装第i个物品：dp[i][w] = dp[i-1][w]
    - 如果装第i个物品：dp[i][w] = dp[i-1][w-weight[i]] + value[i]
    取两者中的最大值
    """
    def __init__(self, weights, values, capacity):
        self.weights = weights
        self.values = values
        self.capacity = capacity
        self.n = len(weights)
        
    def solve(self):
        """使用动态规划求解背包问题"""
        # 创建DP表，dp[i][w]表示前i个物品在容量为w时的最大价值
        dp = np.zeros((self.n + 1, self.capacity + 1), dtype=int)
        history = []  # 记录优化过程
        
        # 填充DP表
        for i in range(1, self.n + 1):
            for w in range(self.capacity + 1):
                # 如果当前物品重量小于等于背包容量
                if self.weights[i-1] <= w:
                    # 选择装或不装，取最大值
                    dp[i][w] = max(dp[i-1][w],  # 不装
                                  dp[i-1][w - self.weights[i-1]] + self.values[i-1])  # 装
                else:
                    # 装不下，只能不装
                    dp[i][w] = dp[i-1][w]
            
            # 记录考虑到第i个物品时的最大价值
            history.append({'item': i, 'max_value': dp[i][self.capacity]})
        
        # 回溯找出选中的物品
        selected = []
        w = self.capacity
        for i in range(self.n, 0, -1):
            # 如果dp[i][w] != dp[i-1][w]，说明第i个物品被选中
            if dp[i][w] != dp[i-1][w]:
                selected.append(i-1)
                w -= self.weights[i-1]
        
        selected.reverse()  # 按照物品顺序排列
        
        return {
            'max_value': dp[self.n][self.capacity],
            'selected': selected,
            'history': history
        }


# ==================== 主应用程序 ====================
class OptimizationApp:
    """优化问题求解系统主界面"""
    def __init__(self, root):
        self.root = root
        self.root.title("优化问题求解系统 - 增强版")
        self.root.geometry("1300x850")
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        success, msg = self.db_manager.init_sqlite()
        if not success:
            messagebox.showwarning("警告", msg)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建标签页
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建四个标签页
        self.test_frame = ttk.Frame(self.notebook)
        self.knapsack_frame = ttk.Frame(self.notebook)
        self.results_frame = ttk.Frame(self.notebook)
        self.db_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.test_frame, text='📊 测试函数优化')
        self.notebook.add(self.knapsack_frame, text='🎒 背包问题优化')
        self.notebook.add(self.results_frame, text='📈 结果数据库查看')
        self.notebook.add(self.db_frame, text='💾 数据库管理')
        
        # 初始化各个模块
        self.setup_test_function_tab()
        self.setup_knapsack_tab()
        self.setup_results_view_tab()
        self.setup_database_tab()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def setup_database_tab(self):
        """设置数据库管理标签页"""
        # 数据库状态显示
        status_frame = ttk.LabelFrame(self.db_frame, text="数据库状态", padding=20)
        status_frame.pack(fill='x', padx=10, pady=10)
        
        self.db_status_label = ttk.Label(status_frame, 
                                         text=f"当前使用: SQLite (本地数据库)\n状态: 已连接",
                                         font=('Arial', 11))
        self.db_status_label.pack()
        
        # SQL Server连接面板
        sqlserver_frame = ttk.LabelFrame(self.db_frame, text="SQL Server连接配置", padding=20)
        sqlserver_frame.pack(fill='x', padx=10, pady=10)
        
        if not HAS_SQLSERVER:
            ttk.Label(sqlserver_frame, 
                     text="⚠️ 未安装pyodbc库，无法使用SQL Server功能\n"
                          "安装命令: pip install pyodbc",
                     foreground='red',
                     font=('Arial', 10)).pack()
        
        # 服务器地址
        ttk.Label(sqlserver_frame, text="服务器地址:").grid(row=0, column=0, sticky='w', pady=5)
        self.server_entry = ttk.Entry(sqlserver_frame, width=30)
        self.server_entry.insert(0, "localhost")
        self.server_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # 数据库名称
        ttk.Label(sqlserver_frame, text="数据库名称:").grid(row=1, column=0, sticky='w', pady=5)
        self.database_entry = ttk.Entry(sqlserver_frame, width=30)
        self.database_entry.insert(0, "OptimizationDB")
        self.database_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # 用户名
        ttk.Label(sqlserver_frame, text="用户名:").grid(row=2, column=0, sticky='w', pady=5)
        self.username_entry = ttk.Entry(sqlserver_frame, width=30)
        self.username_entry.insert(0, "sa")
        self.username_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # 密码
        ttk.Label(sqlserver_frame, text="密码:").grid(row=3, column=0, sticky='w', pady=5)
        self.password_entry = ttk.Entry(sqlserver_frame, width=30, show='*')
        self.password_entry.grid(row=3, column=1, padx=10, pady=5)
        
        # 连接按钮
        btn_frame = ttk.Frame(sqlserver_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="连接 SQL Server", 
                  command=self.connect_sqlserver).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="切换到 SQLite", 
                  command=self.switch_to_sqlite).pack(side='left', padx=5)
        
        # 使用说明
        help_frame = ttk.LabelFrame(self.db_frame, text="使用说明", padding=20)
        help_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        help_text = """
📖 数据库使用说明：

1. SQLite模式（默认）:
   - 无需配置，自动创建本地数据库文件
   - 数据保存在 optimization_results.db 文件中
   - 适合个人使用和测试

2. SQL Server模式:
   - 需要先安装SQL Server
   - 需要安装pyodbc库: pip install pyodbc
   - 填写服务器信息后点击"连接 SQL Server"
   - 适合团队使用和大数据量存储

3. 数据库表结构:
   - test_function_results: 存储测试函数优化结果
   - knapsack_results: 存储背包问题求解结果

4. 即使不连接数据库，程序也能正常运行
   只是无法保存历史记录
        """
        
        help_label = ttk.Label(help_frame, text=help_text, justify='left', 
                              font=('Arial', 10))
        help_label.pack()
    
    def connect_sqlserver(self):
        """连接SQL Server"""
        server = self.server_entry.get()
        database = self.database_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not all([server, database, username, password]):
            messagebox.showwarning("警告", "请填写完整的连接信息")
            return
        
        success, msg = self.db_manager.connect_sqlserver(server, database, username, password)
        
        if success:
            self.db_status_label.config(
                text=f"当前使用: SQL Server ({server})\n状态: 已连接"
            )
            messagebox.showinfo("成功", msg)
            self.load_test_results()
        else:
            messagebox.showerror("错误", msg)
    
    def switch_to_sqlite(self):
        """切换到SQLite"""
        success, msg = self.db_manager.init_sqlite()
        if success:
            self.db_status_label.config(
                text=f"当前使用: SQLite (本地数据库)\n状态: 已连接"
            )
            messagebox.showinfo("成功", "已切换到SQLite数据库")
            self.load_test_results()
        else:
            messagebox.showerror("错误", msg)
    
    def setup_test_function_tab(self):
        """设置测试函数优化标签页"""
        # 左侧控制面板
        left_frame = ttk.Frame(self.test_frame)
        left_frame.pack(side='left', fill='both', expand=False, padx=10, pady=10)
        
        # 函数选择
        func_frame = ttk.LabelFrame(left_frame, text="函数选择", padding=10)
        func_frame.pack(fill='x', pady=5)
        
        self.func_var = tk.StringVar(value="sphere")
        functions = [("Sphere (球函数)", "sphere"),
                    ("Rastrigin (多峰)", "rastrigin"),
                    ("Rosenbrock (香蕉)", "rosenbrock"),
                    ("Ackley (多峰)", "ackley"),
                    ("Griewank (周期多峰)", "griewank"),
                    ("Schwefel (欺骗性)", "schwefel"),
                    ("Levy (复杂多峰)", "levy"),
                    ("Zakharov (单峰)", "zakharov"),
                    ("Dixon-Price (山谷)", "dixon_price"),
                    ("Michalewicz (高维多峰)", "michalewicz"),
                    ("Styblinski-Tang (负值)", "styblinski_tang")]
        
        for text, value in functions:
            ttk.Radiobutton(func_frame, text=text, variable=self.func_var, 
                           value=value).pack(anchor='w', pady=2)
        
        # PSO参数设置
        param_frame = ttk.LabelFrame(left_frame, text="PSO算法参数", padding=10)
        param_frame.pack(fill='x', pady=5)
        
        # 迭代次数
        ttk.Label(param_frame, text="迭代次数:").grid(row=0, column=0, sticky='w', pady=3)
        self.max_iter_var = tk.IntVar(value=100)
        ttk.Spinbox(param_frame, from_=10, to=500, textvariable=self.max_iter_var, 
                   width=15).grid(row=0, column=1, padx=5, pady=3)
        
        # 粒子数量
        ttk.Label(param_frame, text="粒子数量:").grid(row=1, column=0, sticky='w', pady=3)
        self.swarm_size_var = tk.IntVar(value=30)
        ttk.Spinbox(param_frame, from_=10, to=100, textvariable=self.swarm_size_var, 
                   width=15).grid(row=1, column=1, padx=5, pady=3)
        
        # 惯性权重
        ttk.Label(param_frame, text="惯性权重(w):").grid(row=2, column=0, sticky='w', pady=3)
        self.w_var = tk.DoubleVar(value=0.7)
        ttk.Spinbox(param_frame, from_=0.1, to=1.0, increment=0.1, 
                   textvariable=self.w_var, width=15).grid(row=2, column=1, padx=5, pady=3)
        
        # 个体学习因子
        ttk.Label(param_frame, text="个体因子(c1):").grid(row=3, column=0, sticky='w', pady=3)
        self.c1_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(param_frame, from_=0.5, to=3.0, increment=0.1, 
                   textvariable=self.c1_var, width=15).grid(row=3, column=1, padx=5, pady=3)
        
        # 社会学习因子
        ttk.Label(param_frame, text="社会因子(c2):").grid(row=4, column=0, sticky='w', pady=3)
        self.c2_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(param_frame, from_=0.5, to=3.0, increment=0.1, 
                   textvariable=self.c2_var, width=15).grid(row=4, column=1, padx=5, pady=3)
        
        # 维度
        ttk.Label(param_frame, text="维度:").grid(row=5, column=0, sticky='w', pady=3)
        self.dims_var = tk.IntVar(value=2)
        ttk.Spinbox(param_frame, from_=2, to=10, textvariable=self.dims_var, 
                   width=15).grid(row=5, column=1, padx=5, pady=3)
        
        # 开始按钮
        ttk.Button(left_frame, text="🚀 开始求解", 
                  command=self.run_test_function,
                  style='Accent.TButton').pack(pady=15, fill='x')
        
        # 函数信息显示
        info_frame = ttk.LabelFrame(left_frame, text="函数信息", padding=10)
        info_frame.pack(fill='both', expand=True, pady=5)
        self.test_info_text = scrolledtext.ScrolledText(info_frame, height=8, width=30, 
                                                        wrap=tk.WORD, font=('Arial', 9))
        self.test_info_text.pack(fill='both', expand=True)
        
        # 右侧显示区域
        right_frame = ttk.Frame(self.test_frame)
        right_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # 收敛曲线
        plot_frame = ttk.LabelFrame(right_frame, text="收敛曲线", padding=10)
        plot_frame.pack(fill='both', expand=True, pady=5)
        
        self.test_fig = Figure(figsize=(8, 4), dpi=100)
        self.test_ax = self.test_fig.add_subplot(111)
        self.test_canvas = FigureCanvasTkAgg(self.test_fig, plot_frame)
        self.test_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 结果表格
        result_frame = ttk.LabelFrame(right_frame, text="历史结果", padding=10)
        result_frame.pack(fill='both', expand=True, pady=5)
        
        columns = ('时间', '函数', '最优值', '最优位置', '参数')
        self.test_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=6)
        
        widths = [130, 100, 100, 200, 150]
        for col, width in zip(columns, widths):
            self.test_tree.heading(col, text=col)
            self.test_tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.test_tree.yview)
        self.test_tree.configure(yscrollcommand=scrollbar.set)
        
        self.test_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.load_test_results()
    
    def setup_knapsack_tab(self):
        """设置背包问题标签页"""
        # 左侧控制面板
        left_frame = ttk.Frame(self.knapsack_frame)
        left_frame.pack(side='left', fill='both', expand=False, padx=10, pady=10)
        
        # 背包参数设置
        param_frame = ttk.LabelFrame(left_frame, text="背包参数设置", padding=10)
        param_frame.pack(fill='x', pady=5)
        
        ttk.Label(param_frame, text="背包容量(kg):").grid(row=0, column=0, sticky='w', pady=3)
        self.capacity_var = tk.IntVar(value=20)
        ttk.Spinbox(param_frame, from_=10, to=100, textvariable=self.capacity_var, 
                   width=15).grid(row=0, column=1, padx=5, pady=3)
        
        # 物品列表编辑
        items_frame = ttk.LabelFrame(left_frame, text="物品列表", padding=10)
        items_frame.pack(fill='both', expand=True, pady=5)
        
        # 默认物品数据
        self.default_items = [
            ['笔记本电脑', 2, 3],
            ['平板电脑', 3, 4],
            ['相机', 4, 8],
            ['耳机', 5, 8],
            ['无人机', 9, 10]
        ]
        
        # 物品表格
        item_columns = ('物品名称', '重量(kg)', '价值(¥)')
        self.item_tree = ttk.Treeview(items_frame, columns=item_columns, 
                                      show='headings', height=8)
        
        for col in item_columns:
            self.item_tree.heading(col, text=col)
            self.item_tree.column(col, width=80)
        
        for item in self.default_items:
            self.item_tree.insert('', 'end', values=item)
        
        self.item_tree.pack(side='left', fill='both', expand=True)
        
        item_scrollbar = ttk.Scrollbar(items_frame, orient='vertical', 
                                       command=self.item_tree.yview)
        self.item_tree.configure(yscrollcommand=item_scrollbar.set)
        item_scrollbar.pack(side='right', fill='y')
        
        # 物品编辑按钮
        edit_btn_frame = ttk.Frame(left_frame)
        edit_btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(edit_btn_frame, text="添加", command=self.add_item, 
                  width=10).pack(side='left', padx=2)
        ttk.Button(edit_btn_frame, text="修改", command=self.edit_item, 
                  width=10).pack(side='left', padx=2)
        ttk.Button(edit_btn_frame, text="删除", command=self.delete_item, 
                  width=10).pack(side='left', padx=2)
        ttk.Button(edit_btn_frame, text="重置", command=self.reset_items, 
                  width=10).pack(side='left', padx=2)
        
        # 求解按钮
        ttk.Button(left_frame, text="🎯 开始优化", 
                  command=self.run_knapsack,
                  style='Accent.TButton').pack(pady=15, fill='x')
        
        # 右侧显示区域
        right_frame = ttk.Frame(self.knapsack_frame)
        right_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # 优化过程图
        plot_frame = ttk.LabelFrame(right_frame, text="优化过程", padding=10)
        plot_frame.pack(fill='both', expand=True, pady=5)
        
        self.knapsack_fig = Figure(figsize=(8, 4), dpi=100)
        self.knapsack_ax = self.knapsack_fig.add_subplot(111)
        self.knapsack_canvas = FigureCanvasTkAgg(self.knapsack_fig, plot_frame)
        self.knapsack_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 结果显示
        result_frame = ttk.LabelFrame(right_frame, text="优化结果", padding=15)
        result_frame.pack(fill='x', pady=5)
        
        self.knapsack_result_text = scrolledtext.ScrolledText(result_frame, height=10, 
                                                              wrap=tk.WORD, 
                                                              font=('Arial', 10))
        self.knapsack_result_text.pack(fill='both', expand=True)
    
    def add_item(self):
        """添加物品"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加物品")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="物品名称:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        name_entry = ttk.Entry(dialog, width=20)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="重量(kg):").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        weight_entry = ttk.Entry(dialog, width=20)
        weight_entry.grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="价值(¥):").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        value_entry = ttk.Entry(dialog, width=20)
        value_entry.grid(row=2, column=1, padx=10, pady=5)
        
        def save():
            name = name_entry.get()
            try:
                weight = int(weight_entry.get())
                value = int(value_entry.get())
                if name and weight > 0 and value > 0:
                    self.item_tree.insert('', 'end', values=[name, weight, value])
                    dialog.destroy()
                else:
                    messagebox.showwarning("警告", "请输入有效的数据")
            except:
                messagebox.showwarning("警告", "重量和价值必须是正整数")
        
        ttk.Button(dialog, text="确定", command=save).grid(row=3, column=0, 
                                                          columnspan=2, pady=10)
    
    def edit_item(self):
        """修改物品"""
        selection = self.item_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要修改的物品")
            return
        
        item = self.item_tree.item(selection[0])
        values = item['values']
        
        dialog = tk.Toplevel(self.root)
        dialog.title("修改物品")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="物品名称:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        name_entry = ttk.Entry(dialog, width=20)
        name_entry.insert(0, values[0])
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="重量(kg):").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        weight_entry = ttk.Entry(dialog, width=20)
        weight_entry.insert(0, values[1])
        weight_entry.grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="价值(¥):").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        value_entry = ttk.Entry(dialog, width=20)
        value_entry.insert(0, values[2])
        value_entry.grid(row=2, column=1, padx=10, pady=5)
        
        def save():
            name = name_entry.get()
            try:
                weight = int(weight_entry.get())
                value = int(value_entry.get())
                if name and weight > 0 and value > 0:
                    self.item_tree.item(selection[0], values=[name, weight, value])
                    dialog.destroy()
                else:
                    messagebox.showwarning("警告", "请输入有效的数据")
            except:
                messagebox.showwarning("警告", "重量和价值必须是正整数")
        
        ttk.Button(dialog, text="确定", command=save).grid(row=3, column=0, 
                                                          columnspan=2, pady=10)
    
    def delete_item(self):
        """删除物品"""
        selection = self.item_tree.selection()
        if selection:
            self.item_tree.delete(selection[0])
        else:
            messagebox.showwarning("警告", "请先选择要删除的物品")
    
    def reset_items(self):
        """重置物品列表"""
        for item in self.item_tree.get_children():
            self.item_tree.delete(item)
        
        for item in self.default_items:
            self.item_tree.insert('', 'end', values=item)
    
    def run_test_function(self):
        """运行测试函数优化"""
        func_name = self.func_var.get()
        
        # 获取函数和参数
        func_info = {
            'sphere': (TestFunctions.sphere, (-5, 5), 0, "单峰函数，最优解在原点"),
            'rastrigin': (TestFunctions.rastrigin, (-5.12, 5.12), 0, "多峰函数，有大量局部最优"),
            'rosenbrock': (TestFunctions.rosenbrock, (-2, 2), 0, "香蕉函数，最优解在狭长山谷中"),
            'ackley': (TestFunctions.ackley, (-5, 5), 0, "多峰函数，中心有深谷"),
            'griewank': (TestFunctions.griewank, (-600, 600), 0, "周期性多峰函数"),
            'schwefel': (TestFunctions.schwefel, (-500, 500), 0, "欺骗性函数，全局最优远离局部最优"),
            'levy': (TestFunctions.levy, (-10, 10), 0, "复杂多峰函数"),
            'zakharov': (TestFunctions.zakharov, (-5, 10), 0, "单峰函数，比Sphere复杂"),
            'dixon_price': (TestFunctions.dixon_price, (-10, 10), 0, "单峰函数，对角山谷"),
            'michalewicz': (TestFunctions.michalewicz, (0, np.pi), -1.8013, "多峰函数，峰数随维度变化"),
            'styblinski_tang': (TestFunctions.styblinski_tang, (-5, 5), -39.16599*2, "多峰函数，全局最优为负")
        }
        
        func, bounds, optimal, description = func_info[func_name]
        
        # 获取PSO参数
        params = {
            'max_iter': self.max_iter_var.get(),
            'swarm_size': self.swarm_size_var.get(),
            'w': self.w_var.get(),
            'c1': self.c1_var.get(),
            'c2': self.c2_var.get(),
            'dims': self.dims_var.get()
        }
        
        # 更新函数信息
        info_text = f"函数名称: {func_name.upper()}\n"
        info_text += f"描述: {description}\n"
        info_text += f"定义域: {bounds}\n"
        info_text += f"理论最优值: {optimal}\n"
        info_text += f"维度: {params['dims']}D\n\n"
        info_text += f"算法参数:\n"
        info_text += f"- 迭代次数: {params['max_iter']}\n"
        info_text += f"- 粒子数量: {params['swarm_size']}\n"
        info_text += f"- 惯性权重: {params['w']}\n"
        info_text += f"- 个体因子: {params['c1']}\n"
        info_text += f"- 社会因子: {params['c2']}\n"
        
        self.test_info_text.delete(1.0, tk.END)
        self.test_info_text.insert(1.0, info_text)
        
        # 运行PSO
        self.root.config(cursor="wait")
        self.root.update()
        
        try:
            pso = PSO(func, dims=params['dims'], bounds=bounds, 
                     max_iter=params['max_iter'], swarm_size=params['swarm_size'],
                     w=params['w'], c1=params['c1'], c2=params['c2'])
            result = pso.optimize()
            
            # 绘制收敛曲线
            self.test_ax.clear()
            iterations = [h['iteration'] for h in result['history']]
            values = [h['value'] for h in result['history']]
            self.test_ax.plot(iterations, values, 'b-', linewidth=2, marker='o', 
                            markersize=3, markevery=max(1, len(iterations)//20))
            self.test_ax.set_xlabel('迭代次数', fontsize=10)
            self.test_ax.set_ylabel('适应度值', fontsize=10)
            self.test_ax.set_title(f'{func_name.upper()} 函数收敛曲线', fontsize=12)
            self.test_ax.grid(True, alpha=0.3)
            self.test_canvas.draw()
            
            # 保存到数据库
            if self.db_manager.connected:
                success, msg = self.db_manager.save_test_result(
                    func_name.upper(),
                    result['best_value'],
                    result['best_position'].tolist(),
                    result['history'],
                    params
                )
                
                if success:
                    self.load_test_results()
                else:
                    print(f"保存失败: {msg}")
            
            self.root.config(cursor="")
            messagebox.showinfo("优化完成", 
                              f"最优值: {result['best_value']:.8f}\n"
                              f"最优位置: {[f'{x:.4f}' for x in result['best_position']]}")
        
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("错误", f"优化过程出错: {str(e)}")
    
    def run_knapsack(self):
        """运行背包问题优化"""
        # 获取物品数据
        items_data = []
        for item in self.item_tree.get_children():
            values = self.item_tree.item(item)['values']
            items_data.append(values)
        
        if not items_data:
            messagebox.showwarning("警告", "请先添加物品")
            return
        
        items = [item[0] for item in items_data]
        weights = [int(item[1]) for item in items_data]
        values = [int(item[2]) for item in items_data]
        capacity = self.capacity_var.get()
        
        # 运行求解器
        self.root.config(cursor="wait")
        self.root.update()
        
        try:
            solver = KnapsackSolver(weights, values, capacity)
            result = solver.solve()
            
            # 绘制优化过程
            self.knapsack_ax.clear()
            items_count = [h['item'] for h in result['history']]
            max_values = [h['max_value'] for h in result['history']]
            self.knapsack_ax.plot(items_count, max_values, 'g-o', linewidth=2, markersize=8)
            self.knapsack_ax.set_xlabel('考虑物品数', fontsize=10)
            self.knapsack_ax.set_ylabel('最大价值 (¥)', fontsize=10)
            self.knapsack_ax.set_title('动态规划优化过程', fontsize=12)
            self.knapsack_ax.grid(True, alpha=0.3)
            self.knapsack_ax.fill_between(items_count, max_values, alpha=0.3, color='green')
            self.knapsack_canvas.draw()
            
            # 显示结果
            selected_items = [items[i] for i in result['selected']]
            total_weight = sum(weights[i] for i in result['selected'])
            
            result_text = f"{'='*50}\n"
            result_text += f"🎯 背包问题优化结果\n"
            result_text += f"{'='*50}\n\n"
            result_text += f"📅 求解时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result_text += f"📦 背包容量: {capacity} kg\n"
            result_text += f"💰 最大价值: ¥{result['max_value']}\n"
            result_text += f"⚖️  总重量: {total_weight} kg / {capacity} kg\n"
            result_text += f"📊 容量利用率: {total_weight/capacity*100:.1f}%\n\n"
            result_text += f"✅ 选中物品 ({len(selected_items)}件):\n"
            for i, idx in enumerate(result['selected'], 1):
                result_text += f"   {i}. {items[idx]}: 重{weights[idx]}kg, 值¥{values[idx]}\n"
            
            result_text += f"\n❌ 未选中物品:\n"
            unselected = [i for i in range(len(items)) if i not in result['selected']]
            for idx in unselected:
                result_text += f"   - {items[idx]}: 重{weights[idx]}kg, 值¥{values[idx]}\n"
            
            self.knapsack_result_text.delete(1.0, tk.END)
            self.knapsack_result_text.insert(1.0, result_text)
            
            # 保存到数据库
            if self.db_manager.connected:
                problem_params = {
                    'capacity': capacity,
                    'items': items,
                    'weights': weights,
                    'values': values
                }
                success, msg = self.db_manager.save_knapsack_result(
                    result['max_value'],
                    selected_items,
                    total_weight,
                    result['history'],
                    problem_params
                )
                
                if not success:
                    print(f"保存失败: {msg}")
            
            self.root.config(cursor="")
            messagebox.showinfo("优化完成", 
                              f"最大价值: ¥{result['max_value']}\n"
                              f"选中 {len(selected_items)} 件物品")
        
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("错误", f"优化过程出错: {str(e)}")
    
    def load_test_results(self):
        """加载测试函数历史结果"""
        for item in self.test_tree.get_children():
            self.test_tree.delete(item)
        
        results = self.db_manager.load_test_results(10)
        
        for row in results:
            timestamp, func_name, best_value, best_position, params_str = row
            position = json.loads(best_position)
            params = json.loads(params_str) if params_str else {}
            
            position_str = f"[{', '.join([f'{x:.4f}' for x in position[:3]])}...]" if len(position) > 3 else f"[{', '.join([f'{x:.4f}' for x in position])}]"
            params_str_short = f"iter={params.get('max_iter', 'N/A')}"
            
            self.test_tree.insert('', 'end', values=(
                timestamp, func_name, f"{best_value:.6f}", position_str, params_str_short
            ))
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🎓 优化问题求解系统 - 使用说明

【测试函数优化】
1. 选择测试函数（Sphere、Rastrigin、Rosenbrock、Ackley）
2. 调整PSO算法参数：
   - 迭代次数：算法运行的代数
   - 粒子数量：同时搜索的解的数量
   - 惯性权重(w)：控制粒子保持原速度的程度
   - 个体因子(c1)：向个体最优位置靠近的程度
   - 社会因子(c2)：向全局最优位置靠近的程度
   - 维度：问题的变量个数
3. 点击"开始求解"运行优化
4. 查看收敛曲线和历史结果

【背包问题优化】
1. 设置背包容量
2. 添加/修改/删除物品（名称、重量、价值）
3. 点击"开始优化"运行动态规划算法
4. 查看优化过程图和详细结果

【数据库管理】
- 默认使用SQLite本地数据库
- 可选择连接SQL Server进行团队协作
- 所有优化结果自动保存
- 支持不连接数据库独立运行

💡 提示：
- 参数越大，求解越精确但耗时越长
- 多峰函数建议增加粒子数量和迭代次数
- 背包问题可自定义任意物品组合
        """
        
        dialog = tk.Toplevel(self.root)
        dialog.title("使用说明")
        dialog.geometry("600x500")
        
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=('Arial', 10))
        text.pack(fill='both', expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state='disabled')
        
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
优化问题求解系统 v2.0

✨ 功能特性：
• 多种经典测试函数优化
• 粒子群算法(PSO)实现
• 0-1背包问题求解
• 双数据库支持（SQLite/SQL Server）
• 可视化结果展示
• 参数可调节

🛠️ 技术栈：
• Python 3.x
• Tkinter (GUI)
• NumPy (数值计算)
• Matplotlib (数据可视化)
• SQLite / SQL Server (数据存储)

📧 如有问题请联系技术支持
        """
        messagebox.showinfo("关于", about_text)
    
    def setup_results_view_tab(self):
        """设置结果数据库查看标签页"""
        # 顶部控制面板
        control_frame = ttk.Frame(self.results_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(control_frame, text="数据表选择:", font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        
        self.result_table_var = tk.StringVar(value="test_function")
        ttk.Radiobutton(control_frame, text="测试函数结果", 
                       variable=self.result_table_var, 
                       value="test_function",
                       command=self.refresh_results_view).pack(side='left', padx=10)
        ttk.Radiobutton(control_frame, text="背包问题结果", 
                       variable=self.result_table_var, 
                       value="knapsack",
                       command=self.refresh_results_view).pack(side='left', padx=10)
        
        ttk.Button(control_frame, text="🔄 刷新", 
                  command=self.refresh_results_view).pack(side='left', padx=20)
        ttk.Button(control_frame, text="🗑️ 清空所有数据", 
                  command=self.clear_all_data).pack(side='left', padx=5)
        ttk.Button(control_frame, text="📊 查看统计", 
                  command=self.show_statistics).pack(side='left', padx=5)
        
        # 测试函数结果表格
        self.test_results_frame = ttk.LabelFrame(self.results_frame, 
                                                 text="测试函数优化结果数据库", 
                                                 padding=10)
        
        # 创建表格
        columns = ('ID', '函数名称', '时间戳', '最优值', '最优位置', '算法参数')
        self.results_tree = ttk.Treeview(self.test_results_frame, 
                                         columns=columns, 
                                         show='headings', 
                                         height=20)
        
        # 设置列宽和标题
        widths = [50, 120, 150, 120, 300, 250]
        for col, width in zip(columns, widths):
            self.results_tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.results_tree.column(col, width=width)
        
        # 添加滚动条
        y_scrollbar = ttk.Scrollbar(self.test_results_frame, orient='vertical', 
                                    command=self.results_tree.yview)
        x_scrollbar = ttk.Scrollbar(self.test_results_frame, orient='horizontal', 
                                    command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=y_scrollbar.set, 
                                   xscrollcommand=x_scrollbar.set)
        
        # 布局
        self.results_tree.grid(row=0, column=0, sticky='nsew')
        y_scrollbar.grid(row=0, column=1, sticky='ns')
        x_scrollbar.grid(row=1, column=0, sticky='ew')
        
        self.test_results_frame.grid_rowconfigure(0, weight=1)
        self.test_results_frame.grid_columnconfigure(0, weight=1)
        self.test_results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 背包问题结果表格
        self.knapsack_results_frame = ttk.LabelFrame(self.results_frame, 
                                                     text="背包问题优化结果数据库", 
                                                     padding=10)
        
        columns_knapsack = ('ID', '时间戳', '最大价值', '总重量', '选中物品', '问题参数')
        self.knapsack_results_tree = ttk.Treeview(self.knapsack_results_frame, 
                                                   columns=columns_knapsack, 
                                                   show='headings', 
                                                   height=20)
        
        widths_knapsack = [50, 150, 100, 100, 400, 300]
        for col, width in zip(columns_knapsack, widths_knapsack):
            self.knapsack_results_tree.heading(col, text=col)
            self.knapsack_results_tree.column(col, width=width)
        
        y_scrollbar_k = ttk.Scrollbar(self.knapsack_results_frame, orient='vertical', 
                                      command=self.knapsack_results_tree.yview)
        x_scrollbar_k = ttk.Scrollbar(self.knapsack_results_frame, orient='horizontal', 
                                      command=self.knapsack_results_tree.xview)
        self.knapsack_results_tree.configure(yscrollcommand=y_scrollbar_k.set,
                                            xscrollcommand=x_scrollbar_k.set)
        
        self.knapsack_results_tree.grid(row=0, column=0, sticky='nsew')
        y_scrollbar_k.grid(row=0, column=1, sticky='ns')
        x_scrollbar_k.grid(row=1, column=0, sticky='ew')
        
        self.knapsack_results_frame.grid_rowconfigure(0, weight=1)
        self.knapsack_results_frame.grid_columnconfigure(0, weight=1)
        
        # 状态栏
        status_frame = ttk.Frame(self.results_frame)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.results_status_label = ttk.Label(status_frame, 
                                              text="数据库记录数: 0", 
                                              font=('Arial', 10))
        self.results_status_label.pack(side='left')
        
        # 初始加载数据
        self.refresh_results_view()
    
    def refresh_results_view(self):
        """刷新结果视图"""
        if not self.db_manager.connected:
            messagebox.showwarning("警告", "数据库未连接")
            return
        
        table_type = self.result_table_var.get()
        
        if table_type == "test_function":
            # 显示测试函数结果
            self.test_results_frame.pack(fill='both', expand=True, padx=10, pady=10)
            self.knapsack_results_frame.pack_forget()
            
            # 清空现有数据
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # 从数据库加载
            try:
                if self.db_manager.db_type == 'sqlite':
                    conn = sqlite3.connect('optimization_results.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, func_name, timestamp, best_value, best_position, algorithm_params
                        FROM test_function_results 
                        ORDER BY id DESC
                    ''')
                    results = cursor.fetchall()
                    conn.close()
                else:
                    cursor = self.db_manager.connection.cursor()
                    cursor.execute('''
                        SELECT id, func_name, timestamp, best_value, best_position, algorithm_params
                        FROM test_function_results 
                        ORDER BY id DESC
                    ''')
                    results = cursor.fetchall()
                
                # 插入数据到表格
                for row in results:
                    row_id, func_name, timestamp, best_value, best_position, params = row
                    
                    # 格式化最优位置
                    try:
                        position = json.loads(best_position)
                        if len(position) <= 3:
                            pos_str = f"[{', '.join([f'{x:.4f}' for x in position])}]"
                        else:
                            pos_str = f"[{', '.join([f'{x:.4f}' for x in position[:3]])}...]"
                    except:
                        pos_str = "N/A"
                    
                    # 格式化参数
                    try:
                        params_dict = json.loads(params) if params else {}
                        params_str = f"iter={params_dict.get('max_iter', 'N/A')}, " \
                                   f"size={params_dict.get('swarm_size', 'N/A')}, " \
                                   f"w={params_dict.get('w', 'N/A')}"
                    except:
                        params_str = "N/A"
                    
                    self.results_tree.insert('', 'end', values=(
                        row_id,
                        func_name,
                        timestamp,
                        f"{best_value:.8f}",
                        pos_str,
                        params_str
                    ))
                
                self.results_status_label.config(
                    text=f"测试函数结果记录数: {len(results)}"
                )
                
            except Exception as e:
                messagebox.showerror("错误", f"加载数据失败: {str(e)}")
        
        else:  # knapsack
            # 显示背包问题结果
            self.test_results_frame.pack_forget()
            self.knapsack_results_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # 清空现有数据
            for item in self.knapsack_results_tree.get_children():
                self.knapsack_results_tree.delete(item)
            
            # 从数据库加载
            try:
                if self.db_manager.db_type == 'sqlite':
                    conn = sqlite3.connect('optimization_results.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, timestamp, max_value, total_weight, selected_items, problem_params
                        FROM knapsack_results 
                        ORDER BY id DESC
                    ''')
                    results = cursor.fetchall()
                    conn.close()
                else:
                    cursor = self.db_manager.connection.cursor()
                    cursor.execute('''
                        SELECT id, timestamp, max_value, total_weight, selected_items, problem_params
                        FROM knapsack_results 
                        ORDER BY id DESC
                    ''')
                    results = cursor.fetchall()
                
                # 插入数据到表格
                for row in results:
                    row_id, timestamp, max_value, total_weight, selected_items, params = row
                    
                    # 格式化选中物品
                    try:
                        items = json.loads(selected_items)
                        items_str = ", ".join(items[:5])
                        if len(items) > 5:
                            items_str += "..."
                    except:
                        items_str = "N/A"
                    
                    # 格式化参数
                    try:
                        params_dict = json.loads(params) if params else {}
                        params_str = f"容量={params_dict.get('capacity', 'N/A')}kg, " \
                                   f"物品数={len(params_dict.get('items', []))}"
                    except:
                        params_str = "N/A"
                    
                    self.knapsack_results_tree.insert('', 'end', values=(
                        row_id,
                        timestamp,
                        f"¥{max_value}",
                        f"{total_weight}kg",
                        items_str,
                        params_str
                    ))
                
                self.results_status_label.config(
                    text=f"背包问题结果记录数: {len(results)}"
                )
                
            except Exception as e:
                messagebox.showerror("错误", f"加载数据失败: {str(e)}")
    
    def sort_column(self, col):
        """排序列"""
        # 这里可以添加排序功能
        pass
    
    def clear_all_data(self):
        """清空所有数据"""
        if not self.db_manager.connected:
            messagebox.showwarning("警告", "数据库未连接")
            return
        
        result = messagebox.askyesno("确认", 
                                     "确定要清空所有数据吗？\n此操作不可恢复！",
                                     icon='warning')
        if not result:
            return
        
        try:
            if self.db_manager.db_type == 'sqlite':
                conn = sqlite3.connect('optimization_results.db')
                cursor = conn.cursor()
                cursor.execute('DELETE FROM test_function_results')
                cursor.execute('DELETE FROM knapsack_results')
                conn.commit()
                conn.close()
            else:
                cursor = self.db_manager.connection.cursor()
                cursor.execute('DELETE FROM test_function_results')
                cursor.execute('DELETE FROM knapsack_results')
                self.db_manager.connection.commit()
            
            messagebox.showinfo("成功", "所有数据已清空")
            self.refresh_results_view()
            self.load_test_results()
            
        except Exception as e:
            messagebox.showerror("错误", f"清空失败: {str(e)}")
    
    def show_statistics(self):
        """显示统计信息"""
        if not self.db_manager.connected:
            messagebox.showwarning("警告", "数据库未连接")
            return
        
        try:
            stats_text = "📊 数据库统计信息\n"
            stats_text += "=" * 50 + "\n\n"
            
            # 统计测试函数结果
            if self.db_manager.db_type == 'sqlite':
                conn = sqlite3.connect('optimization_results.db')
                cursor = conn.cursor()
                
                # 总记录数
                cursor.execute('SELECT COUNT(*) FROM test_function_results')
                test_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM knapsack_results')
                knapsack_count = cursor.fetchone()[0]
                
                # 按函数统计
                cursor.execute('''
                    SELECT func_name, COUNT(*), AVG(best_value), MIN(best_value)
                    FROM test_function_results
                    GROUP BY func_name
                ''')
                func_stats = cursor.fetchall()
                
                conn.close()
            else:
                cursor = self.db_manager.connection.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM test_function_results')
                test_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM knapsack_results')
                knapsack_count = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT func_name, COUNT(*), AVG(best_value), MIN(best_value)
                    FROM test_function_results
                    GROUP BY func_name
                ''')
                func_stats = cursor.fetchall()
            
            stats_text += f"测试函数优化记录: {test_count} 条\n"
            stats_text += f"背包问题优化记录: {knapsack_count} 条\n"
            stats_text += f"总计: {test_count + knapsack_count} 条\n\n"
            
            if func_stats:
                stats_text += "各函数统计:\n"
                stats_text += "-" * 50 + "\n"
                for func_name, count, avg_val, min_val in func_stats:
                    stats_text += f"{func_name}:\n"
                    stats_text += f"  运行次数: {count}\n"
                    stats_text += f"  平均值: {avg_val:.6f}\n"
                    stats_text += f"  最优值: {min_val:.6f}\n\n"
            
            # 显示统计信息
            dialog = tk.Toplevel(self.root)
            dialog.title("统计信息")
            dialog.geometry("500x400")
            
            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=('Courier', 10))
            text.pack(fill='both', expand=True, padx=10, pady=10)
            text.insert(1.0, stats_text)
            text.config(state='disabled')
            
            ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取统计信息失败: {str(e)}")


# ==================== 程序入口 ====================
if __name__ == "__main__":
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    app = OptimizationApp(root)
    root.mainloop()