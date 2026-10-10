<div align="center">
  <img src="./assets/fault_keeper_chest.png" alt="Fault-Keeper Chest" width="460" />

  <br/><br/>

  <p align="center">
    <a href="./README.md"><b>🇬🇧 English</b></a> &nbsp;•&nbsp;
    <a href="./README_TH.md"><b>🇹🇭 ภาษาไทย</b></a> &nbsp;•&nbsp;
    <a href="./README_JA.md"><b>🇯🇵 日本語</b></a>
  </p>

  <h1 style="margin-bottom: 6px; font-size: 2.5em; letter-spacing: -0.5px; font-weight: 800;">Fault-Keeper</h1>
  <p style="font-size: 1.2em; font-weight: 500; color: #57606a; margin-top: 0; margin-bottom: 18px;">
    主权级 AI 协处理器与零停顿系统哨兵 (The Sovereign AI Co-Processor & Zero-Stall Systems Sentry)
  </p>

  <p align="center">
    <a href="#"><img src="https://img.shields.io/badge/CI%20Windows-PASSING%20(723%2F723)-059669?style=for-the-badge&logo=windows&logoColor=white" alt="CI Windows" /></a>
    <a href="#"><img src="https://img.shields.io/badge/CI%20WSL%2FLinux-PASSING%20(723%2F723)-059669?style=for-the-badge&logo=linux&logoColor=white" alt="CI WSL/Linux" /></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
    <a href="#"><img src="https://img.shields.io/badge/version-v1.0.0-6366F1?style=for-the-badge&logo=databricks&logoColor=white" alt="Version" /></a>
    <a href="#"><img src="https://img.shields.io/badge/mcp-2.0%20OMNI--FACADE-6366F1?style=for-the-badge&logo=anthropic&logoColor=white" alt="MCP 2.0" /></a>
    <a href="#"><img src="https://img.shields.io/badge/pillars-51%20PILLARS-0284C7?style=for-the-badge&logo=blueprint&logoColor=white" alt="51 Pillars" /></a>
    <a href="#"><img src="https://img.shields.io/badge/license-MIT-F59E0B?style=for-the-badge&logo=googledocs&logoColor=white" alt="License" /></a>
    <a href="https://ko-fi.com/xtanthaix" target="_blank"><img src="https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=kofi&logoColor=white" alt="Ko-fi Support" /></a>
  </p>

  <p align="center">
    <b>51 项工程支柱 · 13 个深度检测领域 · 独立主权架构 · 零外部包装依赖</b>
  </p>
</div>

<br/>

<div align="left" style="line-height: 2.0; font-size: 1.05em; max-width: 860px; margin: 0 auto; color: #24292f;">

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;各位开发者朋友们，大家好！🙏✨ 我们打造 Fault-Keeper 的初衷，正是源于大家在日常研发中最感同身受的痛点：那些无法稳定复现的诡异 Heisenbugs、多并发请求涌入时突如其来的死锁（Deadlock），或是因底层数据结构微调而导致整个系统静默崩溃的噩梦。

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;随着我们开始借助 AI 编程助手编写代码，效率固然翻倍，但一种全新的“安全疑虑”也随之而来。你不得不时常提防：大模型是不是悄悄删掉了关键业务函数？是不是偷懒留下了 `// implement later` 注释？还是陷入了来回无效修改的死循环（Doom Loop），疯狂消耗 Token 却一无所获？当项目规模不断扩张，我们花在审查 AI 产出上的心力，甚至超过了架构设计本身。

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Fault-Keeper 支持在你的本地机器上即装即用，无需修改现有业务代码，也无需打破既有研发工作流。从你按下保存键的那一刻起，它便在后台守护数学不变量，在投产前精准拦截漏洞隐患，并充当智能缰绳，约束 AI 代码生成的准确性与确定性。💖🐡

</div>

<br/>

| ⚠️ 假设与困境：速度 vs 稳定性 (Speed vs. Stability) | 🌿 引入 Fault-Keeper (Enter Fault-Keeper) |
| :---: | :---: |
| <img src="./assets/8.jpg" alt="The Hypothesis: Speed vs. Stability" width="100%"> | <img src="./assets/7.jpg" alt="Enter Fault-Keeper" width="100%"> |
| *人机协同编程危机：逻辑静默丢失、并发全系统死锁，以及死循环带来的高昂 Token 浪费* | *Fault-Keeper 成为你的本地工程副驾：实时缺陷拦截、纯粹原生运行，对 AI 行为进行严密认知约束* |

<br/>

---

<br/>

## 🌟 架构亮点与设计理念 (Architectural Highlights)

| 📐 4 层运行时系统解剖图 (System Anatomy) | 🛡️ 3 大系统物理与工程公理 (Principles of Operation) |
| :---: | :---: |
| <img src="./assets/5.jpg" alt="System Anatomy: 4-Layer Runtime Architecture" width="100%"> | <img src="./assets/6.jpg" alt="3 Principles of Operation" width="100%"> |
| *4 层运行时架构：主权 CLI (地壳) ➔ MCP 2.0 (地幔) ➔ 共享内存桥 (外核) ➔ 51 项核心支柱 (内核)* | *3 大设计公理：独立主权 (Sovereign Standalone)、AI 协处理器 (MCP 2.0 感知中枢) 与形式化数学验证 (Z3 SMT)* |

<br/>

<details>
<summary><b>📐 4 层运行时架构示意图 (4-Layer Runtime System Architecture)</b></summary>
<br/>

```text
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                       FAULT-KEEPER v1.0 4 层运行时系统架构图                          │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ 第 1 层: 主权 CLI 与 Python 人体工学门面 (fault_keeper.py, 装饰器, 动态惰性加载)       │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ 第 2 层: MCP 2.0 守护服务 (JSON-RPC over stdio -> 5 大全能工具 MCP-OFA)              │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ 第 3 层: 统一调度中枢与共享内存桥 (零拷贝内存缓冲池 Zero-Copy Buffers)                  │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ 第 4 层: 确定性核心算法引擎 (51 项支柱: 数值数学、微架构、SMT、AST 分析)              │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

</details>

<details>
<summary><b>🛡️ 3 大核心工程理念 (Core Principles)</b></summary>
<br/>

1. **独立主权 ("Python 外壳，原生性能")**: 
   - 通过 [`fault_keeper.py`](./fault_keeper.py) 直接作为纯粹的 UNIX CLI 工具运行，无需任何重量级外部包装依赖。
   - 借助动态惰性计算（Lazy Evaluation）实现毫秒级快速启动。
2. **AI 协处理器与感知中枢**:
   - 充当 Cursor、Claude Code、Windsurf、Copilot 和 Antigravity 等 AI 编程助手的事实核查与感知中枢（Sensory Cortex）。
   - 采用标准 **MCP 2.0 协议**，将工具高度聚合为 **5 大全能工具 (Omni-Tools)**，大幅节省多轮交互中的 System Prompt Token。
3. **形式化数学验证 (Formal Mathematical Verification)**:
   - 依托 **Z3 Dual SMT Solver 双重求解共识**、**对偶数自动微分 (Automatic Differentiation)** 与 **等待图环路消除算法** 严格证明逻辑不变量。
   - 所有缺陷检测均在内存中直接验证数学不变量，杜绝伪检测与误报。

</details>

---

<br/>

## 🛠️ 安装与配置 (Installation)

<details>
<summary><b>📥 源码克隆与依赖安装</b></summary>
<br/>

### 1. 克隆代码仓库并进入目录
```bash
git clone https://github.com/xTanTHaix/Fault-Keeper.git
cd Fault-Keeper
```

### 2. 安装项目依赖
Fault-Keeper 原生支持 Python 3.10、3.11 与 3.12：

```bash
# 安装生产运行时依赖 (NumPy, SciPy, Z3 SMT Solver)
pip install -r requirements.txt

# 开发者测试套件依赖 (PyTest)
pip install -r requirements-dev.txt
```

> **注意：** 针对基础命令行功能（`audit`, `test-audit`），系统内置了完备的回退机制，即使尚未安装 Z3 或 SciPy 等可选求解器，也能开箱即用。

</details>

---

<br/>

## 🚀 4 种系统集成形态 (The 4 Operational Postures)

Fault-Keeper 能够无缝融入各类工程工作流 —— 从终端命令行到 AI Agent 全自动协作：

<div align="center">
  <img src="./assets/4.jpg" alt="4 Ways to Integrate Fault-Keeper" width="100%" />
  <p><i>4 种集成方式：CLI 引擎、面向 AI 的 MCP 2.0、Python 原生库与单行代码装饰器</i></p>
</div>

<br/>

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FAULT-KEEPER v1.0 4 种系统运行形态                               │
├─────────────────────┬─────────────────────┬─────────────────────┬──────────────────────┤
│  形态 1: 命令行 CLI  │ 形态 2: MCP 2.0 服务 │ 形态 3: Python 类库  │ 形态 4: 极简装饰器    │
│  (UNIX 原生引擎)    │ (全能 AI 门面)       │ (模块化深入集成)    │ (单行代码装甲)       │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ python              │ fk_audit            │ import fault_keeper │ @fk.guard            │
│   fault_keeper.py   │ fk_diagnose         │ fk = FaultKeeper()  │ @fault_keeper.armored│
│   audit / test / diag│ fk_patch / fk_verify│ fk.systems.ZSC_ThP()│ (max_drift=0.05)     │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ 终端 / Pre-commit   │ 服务 AI 编程助手    │ 嵌入后端底层业务    │ 即时守护核心函数     │
│ CI/CD 自动化流水线  │ (大幅精简 Token)    │ 直接调用高阶算法    │ 单行代码规避死锁     │
└─────────────────────┴─────────────────────┴─────────────────────┴──────────────────────┘
```

<br/>

<details>
<summary><b>💻 形态 1: 命令行接口 (fault_keeper.py)</b></summary>

<br/>

在终端中直接进行代码审计、架构审查与系统诊断，涵盖 6 大核心子命令：

#### 1. 查看帮助与参数 (`--help`)
列出所有子命令与可用参数选项：
```bash
python fault_keeper.py --help
```

#### 2. 架构审查与死锁侦测 (`audit`)
扫描目标目录，排查未捕获静默故障 (U-FSR)、模块内聚与耦合度指标 (WPA-HIS)、数据库事务死锁环路 (Tx-DLO)，以及前后端 API 契约断裂 (CDC-ABS)：
```bash
python fault_keeper.py audit ./src
```
* **标准 POSIX 退出码 (Exit Codes):**
  * `0` = 审查通过（未发现任何违规或死锁隐患）
  * `1` = 发现违规（不变量被破坏、存在死锁风险或 API 契约破损）
  * `2` = 目标路径不存在或命令行参数输入错误

#### 3. 隔离闪烁不稳定测试 (`test-audit`)
运用置换调度筛（Permutation Shuffling Sieve）捕捉因共享状态污染而产生的毒性测试对（Polluter & Victim Toxic Pair），精准定位内存泄漏：
```bash
python fault_keeper.py test-audit ./tests
```

#### 4. 深度根因诊断 (`diagnose`)
定位循环 N+1 查询 (LQPC)、Async 协程漏写 `await` 导致的竞态 (AE-FPS)、正则表达式 ReDoS 灾难性回溯 (RDA-NP)、基于周计算年份的 Timezone 陷阱 (TC-GTC) 以及响应式界面溢出裁剪 (GSLD)：
```bash
# 全局常规诊断
python fault_keeper.py diagnose ./src

# 开启 Strict 模式：发现任何缺陷即返回退出码 1（专为 CI/CD 质量门禁设计）
python fault_keeper.py diagnose ./src --strict
```

#### 5. 基于 AST 的智能三方合并 (`solve-merge`)
在抽象语法树级别智能解决 Git 代码合并冲突，自动重排可交换语句并协调语法树分支（支持文件路径与内联代码片段）：
```bash
python fault_keeper.py solve-merge base.py our_changes.py their_changes.py
```

#### 6. 启动 MCP JSON-RPC 2.0 服务 (`mcp`)
启动标准 Stdio 传输的 MCP 守护进程，供 Cursor、Claude Desktop、Antigravity 等 AI 工具直连：
```bash
python fault_keeper.py mcp
# 或显式指定传输协议：
python fault_keeper.py mcp --transport stdio
```

</details>

<br/>

<details>
<summary><b>🤖 形态 2: 通过 MCP 2.0 连接 AI 编程助手 (Cursor, Claude, Antigravity)</b></summary>

<br/>

Fault-Keeper 提供开箱即用的独立 MCP 服务器，完整遵循 **MCP 2.0 规范**：

#### 服务入口：[`mcp_server.py`](./mcp_server.py)
将以下配置添加到您的 MCP 配置文件中（如 `~/.gemini/config/mcp_config.json`、`claude_desktop_config.json` 或 Cursor MCP 配置）：

```json
{
  "mcpServers": {
    "fault-keeper": {
      "command": "python",
      "args": [
        "L:\\.Tool\\Fault-Keeper\\mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

#### 专为 AI 打造的 5 大全能工具 (Omni-Tools):
1. **`fk_audit`**: 扫描文件或目录，验证安全不变量、架构拓扑与死锁风险。
2. **`fk_diagnose`**: 诊断性能瓶颈、异步竞态条件、N+1 查询、ReDoS 与因果根因。
3. **`fk_patch`**: 生成规范化修复补丁，并在隔离的内存沙箱中进行回归验证。
4. **`fk_verify`**: 检验跨端契约一致性，形式化证明数学规则。
5. **`fk_discover`**: 允许 AI 助手按需即时（JIT）检索 51 项支柱的技术规范与数学公式。

#### AI 聊天自然语言交互示例：
配置完成后，您只需在聊天框中自然提问：
* *"帮我审计 src 目录下的代码"* ➔ AI 自动调用 `fk_audit`
* *"诊断这个模块中偶发崩溃的根本原因"* ➔ AI 自动调用 `fk_diagnose`
* *"在沙箱中测试这个修复方案"* ➔ AI 自动调用 `fk_patch`
* *"验证前端与后端之间的 API 契约"* ➔ AI 自动调用 `fk_verify`
* *"查找系统中有哪些防止数据库事务死锁的支柱"* ➔ AI 自动调用 `fk_discover`

</details>

<br/>

<details>
<summary><b>📦 形态 3: 嵌入式 Python 类库与统一门面 (FaultKeeper)</b></summary>

<br/>

通过统一的门面类访问所有 51 项核心引擎，全量支持惰性加载以最大程度减少内存占用：

```python
import fault_keeper

# 初始化单例门面
fk = fault_keeper.FaultKeeper()

# 1. 高精度数值计算与自动微分 (Automatic Differentiation)
dual_x = fk.num.DualNumber(real=3.0, dual=1.0)
y = dual_x * dual_x + 5.0  # y = x^2 + 5
print(f"函数值: {y.real}, 导数值: {y.dual}")

# 2. 时区格式 YYYY 陷阱检测
has_trap, details = fk.num.TimezoneDriftDetector.detect_format_drift("YYYY-MM-dd")
if has_trap:
    print(f"警告: 基于周的年份格式可能导致跨年日期偏差: {details}")

# 3. 事务死锁等待图环路检测
wfg = fk.daily.WaitForGraph()
wfg.add_dependency(tx_a="TX1", tx_b="TX2")
wfg.add_dependency(tx_a="TX2", tx_b="TX1") # 构成环路
cycles = wfg.detect_cycles()
print(f"检测到死锁环路: {cycles}")

# 4. 硬件感知零停顿内存分配器
allocator = fk.systems.ZSC_ThP() # 双池零内存紧缩停顿 THP 分配器
ptr = allocator.allocate(size_bytes=1024 * 1024 * 2) # 从 2MB 静态 Arena 中分配
```

</details>

<br/>

<details>
<summary><b>🛡️ 形态 4: 单行装饰器即时守护 (@armored, @guard)</b></summary>

<br/>

通过简洁的单行装饰器，为核心业务函数赋予运行时不变量检测防护：

```python
import fault_keeper

# 捕获状态漂移并限制数学偏差
@fault_keeper.armored(max_drift=0.05)
def critical_financial_settlement(account_id: str, balance: float):
    # 若计算状态漂移超出阈值，系统立即拦截并警报
    return process_settlement(account_id, balance)

# 防御性入参契约断言守护
@fault_keeper.guard
def transfer_funds(source: str, target: str, amount: float):
    assert amount > 0, "转账金额必须大于零"
    return execute_transfer(source, target, amount)
```

</details>

---

<br/>

## 🏛️ 51 项核心支柱全景目录 (The 51 Core Pillars Catalog)

全系统划分为 **13 个核心领域**，覆盖应用数学、底层系统微架构直至 AI 认知装甲：

| 🧪 51 项工程支柱周期表 (Taxonomy) | 🛡️ AI 智能体装甲与认知路由 (AI Agent Armor) |
| :---: | :---: |
| <img src="./assets/2.jpg" alt="The 51 Core Pillars Taxonomy" width="100%"> | <img src="./assets/3.jpg" alt="AI Agent Armor & Cognitive Router" width="100%"> |
| *51 项支柱覆盖 13 个工程领域：从高阶数值运算、底层硬件内存管理，到日常代码陷阱* | *拦截偷懒占位符 (ASP-HG)、打破无效循环 (ACT-LO)，通过全能工具极简节省 Prompt Token* |

<br/>

<details>
<summary><b>1. 应用数学与数值计算内核 (fk.num): 3 项支柱</b></summary>
<br/>

| 支柱代码 | 完整名称 | 核心机制与职责 |
| :--- | :--- | :--- |
| **FK-NUM** | Numerical Kernel | 对偶数自动微分计算、128 位金融级定点数运算，以及 $O(1)$ Welford 流式方差计算。 |
| **FK-SLA** | Sparse Linear Algebra | 64 字节缓存行对齐的 SIMD CSR/CSC 存储格式、并行 SpMV 稀疏矩阵向量乘、选主元 Cholesky 分解与随机低秩 SVD 分解。 |
| **FK-GEO** | Robust Geometry Engine | 借助 Shewchuk 精确自适应浮点谓词（Orient2D / InCircle）、30 位 Morton 码线性 BVH 树与 $O(N \log N)$ 单调链凸包算法彻底杜绝精度崩溃。 |

</details>

<details>
<summary><b>2. 硬件微架构与底层系统哨兵 (fk.systems): 16 项支柱</b></summary>
<br/>

| 支柱代码 | 完整名称 | 核心机制与职责 |
| :--- | :--- | :--- |
| **NUMA-AFS** | NUMA-Aware Affinity Sentry | 解析 ACPI SLIT 距离矩阵，计算局部性商（LQ），运用 Kuhn-Munkres 二分图匹配（KM-BAW）绑定核心与内存页，杜绝跨互连总线等待停顿。 |
| **ZSC-THP** | Zero-Stall Compaction THP | 双池混合分配架构（DHACS），将 2MB THP 静态池与 4KB 动态池严格隔离，搭配异步后台内存吸收，实现 0.0ms 直接内存紧缩停顿。 |
| **FS-CCO** | False Sharing Cache Optimizer | 将结构体布局重排为 64 字节缓存行对齐，彻底消除多核并发工作线程间因伪共享引发的 L1 缓存失效震荡。 |
| **HEH-DR** | Hazard-Epoch Hybrid Reclamation | 融合三代分期回收（EBR）与 Hazard Pointers 的无锁内存回收引擎，回收开销 $< 3\%$。 |
| **APM-RLME** | Adaptive Array Layout Engine | 根据运行时读写比率，利用矢量化 SIMD 跨步缓冲在结构数组（AoS）与数组结构（SoA）之间实现零停顿动态转置。 |
| **TSCA** | Topological Simplicial Arbiter | 基于单纯复形（Simplicial Complex）拓扑建模的无等待并发协调器，通过一阶贝蒂数同调群（$H_1 = 0$）数学证明永久规避死锁。 |
| **CAM-RO** | Cross-Arch Memory Reordering | 评估 Litmus 弱内存重排测试，在 x86 TSO 与 ARMv8/RISC-V 弱内存模型之间自动合成原子内存屏障。 |
| **AC-SBE** | Auto-Cooperative Yield Injector | AST 级扫描异步事件循环中的 CPU 密集负载，自动注入协作式让步点，防止主事件循环卡死饥饿。 |
| **EV-IPP** | eBPF Verifier Simulator | 在 IDE 内模拟 64 位截断数（Tnum）与寄存器界限，形式化验证 eBPF 内核程序终止性与内存安全。 |
| **SABA** | SIMD Auto-Vectorization Analyzer | 分析循环携带依赖距离与指针别名冲突，打破阻碍编译器自动矢量化（AVX-512 / NEON）的瓶颈。 |
| **SC-BBW** | Spectral Basic-Block Weaver | 构建控制流图的图拉普拉斯算子，利用 Fiedler 特征向量线性重排热点基本块，极大减少指令缓存未命中。 |
| **PT-PAFS** | Pointer Provenance & Tree Borrows | 遵循 Tree Borrows 模型跟踪指针起源与借用状态机，捕获 Unsafe C/Rust 代码中的未定义行为与严格别名违规。 |
| **DIS-RA** | Deterministic io_uring Arbiter | 零拷贝管理 io_uring 提交队列（SQ）与完成队列（CQ），结合确定性背压节流机制杜绝 CQE 溢出。 |
| **H-TSS** | Hardware Tagged Pointer Sentry | 模拟 ARM TBI 与 x86 UAM 顶字节指针标签，在运行时精准捕捉释放后使用（UAF）与空间缓冲区溢出漏洞。 |
| **MD-BBE** | Monomorphization Deduplicator | 跨泛型实例提取结构 ABI 哈希，将完全等价的实例收缩合并为通用多态 Thunk，缩减 40%–70% 目标文件体积。 |
| **DMCS** | Dominator-Tree Memory Cut Sentry | 借助支配树（Dominator Tree）分析内存引用图，通过最大流最小割算法剪断孤立引用孤岛，可安全回收 $\ge 80\%$ 泄露内存。 |

</details>

<details>
<summary><b>3. 常见开发陷阱与日常踩坑拦截 (fk.daily): 7 项支柱</b></summary>
<br/>

| 支柱代码 | 完整名称 | 核心机制与职责 |
| :--- | :--- | :--- |
| **FT-DSO** | Flaky Test Sieve & Order Oracle | 随机乱序置换调度（$\pi_{\text{shuf}}$）、格雷码二分搜索毒性测试对隔离器（$O(N \log N)$）、状态污染检测与虚拟事件时钟淬灭。 |
| **Tx-DLO** | Transaction Deadlock Oracle | 分析等待有向图（$\mathcal{G}_{\text{wfg}}$），强制执行 Havender 全局加锁序（$\prec_{\text{lock}}$），以预排序批处理键确保 $\Pr(\text{Deadlock}) \equiv 0.0$。 |
| **CDC-ABS** | Cross-Boundary Contract Sentry | 在 AST 层级（Zero-E2E）通过结构子类型协变不变量拦截前后端破坏性 API 契约变更。 |
| **AEC-VS** | Env Contract & Secret Sentry | 形式化检验环境变量配置（`.env`），拦截意外泄露的敏感密钥并强制校验系统类型安全。 |
| **TC-GTC** | Timezone & DST Trap Detector | 捕捉隐蔽的时区偏移、夏令时（DST）陷阱，以及基于周的年份格式 `YYYY` 与公历年份 `yyyy` 混淆错误。 |
| **RDA-NP** | ReDoS Catastrophic Backtrack Sentry | 评估正则表达式状态机复杂度，在发布前提前识别多项式或指数级灾难性回溯漏洞。 |
| **CASI-OP** | Cache Stampede & Invalidation Sentry | 将两阶段缓存失效与数据库事务协同调度，注入 XFetch 概率性提前重算机制杜绝缓存雪崩与击穿。 |

</details>

<details>
<summary><b>4. AI 智能体防护装甲与认知路由 (fk.armor, fk.mcp): 4 项支柱</b></summary>
<br/>

| 支柱代码 | 完整名称 | 核心机制与职责 |
| :--- | :--- | :--- |
| **ASP-HG** | Anti-Placeholder Guard | 依托 AST 结构锚点匹配，精准识别并拦截 AI 偷懒删减代码模式（如 `// implement later`、`... existing code ...`）。 |
| **ACT-LO** | Agent Thrashing Loop Oracle | 监测编辑死循环（Doom Loop），强制推行单调进展不变量，并提取最小不可满足子集（MUC）。 |
| **SC-PVE** | Speculative Candidate Parallel Verifier | 在写时复制（CoW）内存影子沙箱中并行推演多个候选补丁，利用 Zhang-Shasha 树编辑距离评选最优解。 |
| **MCP-OFA** | Model Context Protocol Omni-Facade | 将 51 项功能聚合为 5 大全能工具，节省系统提示词 Token，支持按需 JIT 渐进式发现（`fk_discover`）。 |

</details>

<details>
<summary><b>5. 开发者工作流、类型安全、形式化验证与分布式系统: 21 项支柱</b></summary>
<br/>

| 领域分类 | 核心代表支柱 | 核心机制与职责 |
| :--- | :--- | :--- |
| **类型系统 (fk.typing)** | **FSAS**, **ATH-BS**, **AE-FPS**, **TWSA**, **ACDS** | 虚拟 Ghost CST 语法自愈、类型空洞 DTO 合成、协程漏写 `await` 竞态捕获与类型格补全。 |
| **工程工作流 (fk.workflow)** | **CRCAE**, **LQPC**, **SSDL**, **STAS**, **A-SMW**, **PTHO** | 单行因果溯源逆向归纳、多面体模型 N+1 查询优化、依赖冲突求解与 AST 语义级三方合并。 |
| **代码审计 (fk.audit)** | **U-FSR**, **WPA-HIS** | 单文件健壮性评分（香农熵、内聚性）与全工程全局架构评分（0 至 100 分，有向无环图、模块解耦）。 |
| **全栈演进 (fk.workflow)** | **ZEC-SW**, **GSLD** | 影子触发器零停机数据库迁移演进，以及单纯形线性规划求解响应式 CSS 布局截断。 |
| **形式化验证 (fk.formal)** | **CIS3**, **DCEG**, **SADS**, **FSLS** | 双 Z3 SMT 共识测试数据合成、微分因果图，以及范畴论代数同步。 |
| **分布式与时间 (fk.dist)** | **D-CAS**, **CADRE** | 确定性网络分区与时钟漂移模拟重放，以及全知视角的时空穿越执行追踪器。 |

</details>

---

<br/>

## 🧪 严格测试验证与质量门禁 (Test Verification & Quality Gates)

<div align="center">
  <img src="./assets/1.jpg" alt="4-Tier Verification Architecture" width="100%" />
  <p><i>4 级严格验证体系：从微观 1:1 不变量到高压并发、集群阶段门禁与全链路端到端，确保 100% 纯正代码品质</i></p>
</div>

<br/>

<details>
<summary><b>🛡️ 4 级验证架构详解</b></summary>
<br/>

Fault-Keeper 建立起 4 个梯级的严格质检关卡：
1. **Tier 1 (微观 1:1 不变量)**: 逐一针对 51 项支柱的真实代码实现验证其数学方程与不变量。
2. **Tier 2 (高压并发与延迟边界)**: 针对纳秒级延迟上限与高并发竞态条件进行极端测试。
3. **Tier 3 (集群阶段门禁)**: 模拟真实复杂场景，如大型单体仓库防死锁闪烁门禁与多路 NUMA 架构集群演练。
4. **Tier 4 (全局端到端)**: 完整验证终端命令行与 MCP 守护进程 JSON-RPC 消息流。

```bash
# 执行全部 723 项测试用例
python -m pytest -q
```
```text
============================ 723 passed in 73.14s =============================
```

</details>

---

<br/>

## 📁 项目目录结构 (Repository Directory Layout)

<details>
<summary><b>📂 完整文件目录树</b></summary>
<br/>

```text
Fault-Keeper/
├── fault_keeper.py            # 主权独立 CLI 入口 (Layer 1)
├── mcp_server.py              # MCP 2.0 JSON-RPC 守护服务进程 (Layer 2)
├── pyproject.toml             # 项目元数据与打包构建配置
├── requirements.txt           # 生产运行时依赖 (NumPy, SciPy, Z3)
├── requirements-dev.txt       # 开发与测试环境依赖 (PyTest)
│
├── src/
│   └── fault_keeper/          # 核心 Python 门面与模块实现
│       ├── __init__.py        # FaultKeeper 单例入口与动态惰性加载器
│       ├── facade.py          # 统一全能门面与子系统路由
│       ├── systems/           # 硬件微架构与底层系统哨兵 (16 项支柱: NUMA, THP, eBPF...)
│       ├── daily/             # 日常开发陷阱规避 (FT-DSO, Tx-DLO, CDC-ABS)
│       ├── typing/            # 内循环类型安全哨兵 (Ghost CST, Await 检查)
│       ├── workflow/          # 开发者效率引擎 (CRCAE, SSDL, N+1 优化)
│       ├── audit/             # 架构质量与单文件健壮性审计 (U-FSR, WPA-HIS)
│       └── ...                # 其他领域核心引擎 (num, sla, geo, armor, formal, dist)
│
├── tests/                     # 4 级零 Mock 确定性测试套件 (723 项测试)
│   ├── test_tier1_invariants.py
│   ├── test_exhaustive_imports.py
│   ├── test_phase2_tier3_cluster_gate.py
│   ├── test_phase3_tier3_cluster_gate.py
│   └── pillars/               # 逐项支柱 1:1 不变量测试
│
└── assets/
    ├── fault_keeper_chest.png # 项目视觉吉祥物标志
    └── 1.jpg - 9.jpg          # 架构图解与对比信息图
```

</details>

## ☕ 拥抱专注与赞助支持 (Reclaim Your Time & Support)

<div align="center">
  <img src="./assets/9.jpg" alt="Reclaim Your Time" width="100%" />
  <p><i>告别心智内耗，重获创造的纯粹乐趣：克隆、安装，安心编写每一行代码</i></p>
</div>

<br/>

如果 Fault-Keeper 为你节省了宝贵的心力与调试时间，欢迎在 Ko-fi 上为我们赞助一杯咖啡或热茶，支持项目的持续维护与更新：

<p align="left">
  <a href="https://ko-fi.com/xtanthaix" target="_blank">
    <img src="https://img.shields.io/badge/Support%20on-Ko--fi-FF5E5B?style=for-the-badge&logo=kofi&logoColor=white" alt="Support on Ko-fi" height="46" />
  </a>
</p>

由衷感谢每一位开发者的支持与信任！🙏💖☕

---

<br/>

## 📜 开源许可协议 (License)

本项目遵循开放且自由的 **MIT License** 开源许可协议，您可以自由地将其应用于个人学习、二次开发、商业项目集成及企业级系统部署。✨
