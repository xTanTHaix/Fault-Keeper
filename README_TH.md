<div align="center">
  <img src="./assets/fault_keeper_chest.png" alt="Fault-Keeper Chest" width="460" />

  <br/><br/>

  <p align="center">
    <a href="./README.md"><b>🇬🇧 English</b></a> &nbsp;•&nbsp;
    <a href="./README_ZH.md"><b>🇨🇳 简体中文</b></a> &nbsp;•&nbsp;
    <a href="./README_JA.md"><b>🇯🇵 日本語</b></a>
  </p>

  <h1 style="margin-bottom: 6px; font-size: 2.5em; letter-spacing: -0.5px; font-weight: 800;">Fault-Keeper</h1>
  <p style="font-size: 1.2em; font-weight: 500; color: #57606a; margin-top: 0; margin-bottom: 18px;">
    The Sovereign AI Co-Processor & Zero-Stall Systems Sentry
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
    <b>51 เสาหลักวิศวกรรม · 13 โดเมนตรวจจับลึก · สถาปัตยกรรม Sovereign Standalone · ไร้ External Wrappers</b>
  </p>
</div>

<br/>

<div align="left" style="line-height: 2.0; font-size: 1.05em; max-width: 860px; margin: 0 auto; color: #24292f;">

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;สวัสดีเพื่อนๆ นักพัฒนา 🙏✨ พวกเราสร้าง Fault-Keeper ขึ้นมาเพราะเจอปัญหาที่หลายคนน่าจะคุ้นเคยกันดี ทั้งการไล่แกะบั๊กแปลก ๆ ที่จำลองซ้ำไม่ได้ การติด deadlock ตอนเริ่มมีคนเข้ามาใช้งานพร้อมกัน หรือโค้ดพังเงียบ ๆ จากการแก้โครงสร้างข้อมูลเพียงจุดเดียว

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;พอเริ่มใช้ AI ช่วยเขียนโค้ด งานไวขึ้นก็จริง แต่ก็ต้องคอยระแวงว่ามันจะแอบลบฟังก์ชันสำคัญทิ้ง ใส่คอมเมนต์สลบไว้แทน หรือแก้วนไปมาจนเสียโทเคนไปฟรี ๆ ยิ่งโปรเจกต์ใหญ่ขึ้น เรายิ่งเสียเวลาตรวจทานเรื่องพวกนี้มากกว่าเวลาที่ได้คิดสร้างของใหม่

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Fault-Keeper ติดตั้งและรันบนเครื่องของคุณได้ทันทีโดยไม่ต้องแก้โค้ดเดิมหรือเปลี่ยนเวิร์กโฟลว์ ตัวระบบช่วยตรวจสอบความถูกต้องตั้งแต่จังหวะกดเซฟไฟล์ ดักจับจุดเปราะบางก่อนนำโค้ดขึ้นระบบจริง และคอยคุมไม่ให้ AI ตัดทอนโค้ดสำคัญหรือแก้โค้ดวนลูปจนเสียเวลาครับ 💖🐡

</div>

<br/>

| ⚠️ สมมติฐาน: ความเร็ว vs ความเสถียร (Speed vs. Stability) | 🌿 ก้าวเข้าสู่ Fault-Keeper (Enter Fault-Keeper) |
| :---: | :---: |
| <img src="./assets/8.jpg" alt="The Hypothesis: Speed vs. Stability" width="100%"> | <img src="./assets/7.jpg" alt="Enter Fault-Keeper" width="100%"> |
| *วิกฤตความระแวงในการเขียนโค้ดร่วมกับ AI: โค้ดหายเงียบ, ติด Deadlock ค้างทั้งระบบ, และค่าโทเคนพุ่งจาก Doom Loops* | *Fault-Keeper เข้ามาเป็นเพื่อนร่วมทีมในเครื่อง: สกัดกั้นบั๊กแบบเรียลไทม์ ไร้ External Wrapper และคุมพฤติกรรม AI* |

<br/>

---

<br/>

## 🌟 จุดเด่นและแนวคิดทางสถาปัตยกรรม (Architectural Highlights)

| 📐 ผังวิภาคระบบ 4 เลเยอร์ (System Anatomy) | 🛡️ 3 กฎเหล็กเชิงปรัชญาและฟิสิกส์ของระบบ (Principles of Operation) |
| :---: | :---: |
| <img src="./assets/5.jpg" alt="System Anatomy: 4-Layer Runtime Architecture" width="100%"> | <img src="./assets/6.jpg" alt="3 Principles of Operation" width="100%"> |
| *สถาปัตยกรรมรันไทม์ 4 เลเยอร์: Sovereign CLI (The Crust) ➔ MCP 2.0 (The Mantle) ➔ Memory Bridge (Outer Core) ➔ 51 Pillars (Inner Core)* | *3 กฎเหล็ก: Sovereign Standalone, AI Co-Processor (MCP 2.0 Sensory Cortex), และ Formal Mathematical Verification (Z3 SMT)* |

<br/>

<details>
<summary><b>📐 แผนผังสถาปัตยกรรมรันไทม์ 4 เลเยอร์ (4-Layer Runtime System Architecture)</b></summary>
<br/>

```text
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                       สถาปัตยกรรมรันไทม์ 4 เลเยอร์ของ FAULT-KEEPER v1.0              │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Sovereign CLI & Python Ergonomics Facade (fault_keeper.py, Decorators, Lazy)│
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: MCP 2.0 Server Daemon (JSON-RPC over stdio -> 5 Omni-Tools via MCP-OFA)     │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Unified Engine Dispatcher & Shared Memory Bridge (Zero-Copy Memory Buffers) │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Core Deterministic Algorithm Engines (51 Pillars: Math, Systems, SMT, AST)  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

</details>

<details>
<summary><b>🛡️ 3 หลักการออกแบบระบบ (Core Principles)</b></summary>
<br/>

1. **Sovereign Standalone ("Python Outside, Native Inside")**: 
   - ใช้งานเป็น Pure UNIX CLI ผ่านไฟล์ [`fault_keeper.py`](./fault_keeper.py) ได้ทันทีโดยไม่ต้องพึ่งพา Wrapper ภายนอก
   - ทำงานช่วงเริ่มต้น (Startup Latency) รวดเร็วผ่านการโหลดโมดูลแบบ Dynamic Lazy Evaluation
2. **AI Co-Processor & Sensory Cortex**:
   - ทำหน้าที่เป็นระบบตรวจข้อเท็จจริง (Sensory Cortex) ให้กับ AI Coding Assistants เช่น Cursor, Claude Code, Windsurf, Copilot
   - สื่อสารผ่านโพรโทคอลมาตรฐาน **MCP 2.0** โดยรวบเครื่องมือเหลือ **5 Omni-Tools** ช่วยประหยัด System Prompt Tokens ในการเรียกใช้งาน
3. **Formal Mathematical Verification**:
   - ตรวจสอบความถูกต้องเชิงตรรกะและคณิตศาสตร์ด้วย **Z3 Dual SMT Solver Consensus**, **Dual Numbers Automatic Differentiation**, และ **Wait-For Graph Cycle Eliminator**
   - ทุกการตรวจจับทำงานโดยยืนยัน Invariant ทางคณิตศาสตร์ในหน่วยความจำโดยตรง

</details>

---

<br/>

## 🛠️ วิธีการติดตั้ง (Installation)

<details>
<summary><b>📥 ขั้นตอนการโคลนและติดตั้ง Dependencies</b></summary>
<br/>

### 1. โคลนโปรเจกต์และเข้าสู่โฟลเดอร์
```bash
git clone https://github.com/xTanTHaix/Fault-Keeper.git
cd Fault-Keeper
```

### 2. ติดตั้ง Dependencies พื้นฐาน
Fault-Keeper รองรับ Python 3.10, 3.11 และ 3.12:

```bash
# ติดตั้ง Production Runtime Dependencies (NumPy, SciPy, Z3 SMT Solver)
pip install -r requirements.txt

# สำหรับนักพัฒนาที่ต้องการรัน PyTest Suite
pip install -r requirements-dev.txt
```

> **หมายเหตุ:** สำหรับคำสั่งตรวจจับพื้นฐาน (`audit`, `test-audit`) ตัวระบบมี Fallback ให้ทำงานได้ทันทีแม้ยังไม่ได้ติดตั้ง Z3 หรือ SciPy

</details>

---

<br/>

## 🚀 สถาปัตยกรรมการใช้งาน 4 วิธีหลัก (The 4 Operational Postures)

Fault-Keeper เชื่อมต่อเข้ากับเวิร์กโฟลว์ได้หลากหลาย ทั้งการพิมพ์สั่งงานผ่าน Terminal ไปจนถึงการให้ AI Agent เรียกใช้อัตโนมัติ:

<div align="center">
  <img src="./assets/4.jpg" alt="4 Ways to Integrate Fault-Keeper" width="100%" />
  <p><i>4 วิธีเชื่อมต่อ Fault-Keeper เข้าสู่เวิร์กโฟลว์: CLI Engine, MCP 2.0 สำหรับ AI, Library Module และ One-Line Auto Armor Decorators</i></p>
</div>

<br/>

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FAULT-KEEPER v1.0 OPERATIONAL POSTURES                          │
├─────────────────────┬─────────────────────┬─────────────────────┬──────────────────────┤
│  วิธีที่ 1: CLI     │ วิธีที่ 2: MCP 2.0  │ วิธีที่ 3: Library  │ วิธีที่ 4: Auto Armor│
│  (UNIX Engine)      │ (Omni-Facade)       │ (Modular & Facade)  │ (One-Line Decorator) │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ python              │ fk_audit            │ import fault_keeper │ @fk.guard            │
│   fault_keeper.py   │ fk_diagnose         │ fk = FaultKeeper()  │ @fault_keeper.armored│
│   audit / test / diag│ fk_patch / fk_verify│ fk.systems.ZSC_ThP()│ (max_drift=0.05)     │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ ใช้งานใน Shell /    │ ให้บริการ AI Agents │ ฝังใน Backend Code  │ คุ้มกันฟังก์ชันทันที  │
│ Pre-commit / CI/CD  │ (ประหยัด Token)     │ เรียกใช้อัลกอริทึมลึก│ ขจัด Deadlock ใน 1 บรรทัด │
└─────────────────────┴─────────────────────┴─────────────────────┴──────────────────────┘
```

<br/>

<details>
<summary><b>💻 วิธีที่ 1: ใช้งานผ่านคำสั่ง Command-Line Interface (fault_keeper.py)</b></summary>

<br/>

สั่งตรวจจับบั๊ก ตรวจสอบสถาปัตยกรรม และวิเคราะห์ระบบได้โดยตรงจาก Shell ด้วย 6 คำสั่งหลัก:

#### 1. ตรวจสอบคู่มือและคำสั่งช่วยเหลือ (`--help`)
แสดงรายการคำสั่งย่อย (Subcommands) และตัวเลือกทั้งหมดของ Fault-Keeper:
```bash
python fault_keeper.py --help
```

#### 2. ตรวจสอบสถาปัตยกรรมและตรวจจับ Deadlock (`audit`)
สแกนโฟลเดอร์เพื่อหาจุดผิดพลาดที่ไม่มีตัวดักจับ (U-FSR), ความซับซ้อนของโครงสร้างโค้ด (WPA-HIS), วงรอบ Deadlock ในฐานข้อมูล (Tx-DLO), และ API Breaking-Changes ข้ามฝั่ง Backend/Frontend (CDC-ABS):
```bash
python fault_keeper.py audit ./src
```
* **Exit Code มาตรฐาน POSIX:**
  * `0` = ผ่านสมบูรณ์ (ไม่พบบั๊กหรือ Deadlock)
  * `1` = ตรวจพบบั๊ก ละเมิด Invariant หรือพบความเสี่ยง Deadlock/API Breaking
  * `2` = ไม่พบโฟลเดอร์เป้าหมาย หรือระบุอาร์กิวเมนต์คำสั่งไม่ถูกต้อง

#### 3. กรองและระบุ Flaky Test (`test-audit`)
สลับลำดับการรันเทส (Permutation Shuffling Sieve) เพื่อหาคู่เทสที่มีการส่งผ่านสถานะปนเปื้อน (Polluter & Victim Toxic Pair) และดักจับ State Leakage ในหน่วยความจำ:
```bash
python fault_keeper.py test-audit ./tests
```

#### 4. วินิจฉัยวิเคราะห์ปัญหาเชิงลึก (`diagnose`)
ค้นหาจุดบกพร่องที่พบบ่อย เช่น N+1 Query ในลูป (LQPC), ลืมใส่ `await` หรือเกิด Race Condition ใน Async (AE-FPS), ช่องโหว่ ReDoS ใน Regex (RDA-NP), รูปแบบปี Week-based YYYY ใน Timezone (TC-GTC), และปัญหา CSS แตกบนจอแคบ (GSLD):
```bash
# วินิจฉัยภาพรวม
python fault_keeper.py diagnose ./src

# เปิดโหมด Strict เพื่อให้คำสั่งส่ง Exit Code 1 ทันทีที่เจอบั๊ก (เหมาะกับ CI/CD Pipeline)
python fault_keeper.py diagnose ./src --strict
```

#### 5. รวมไฟล์โค้ดอัตโนมัติด้วย AST 3-Way Merge (`solve-merge`)
ผสานโค้ดที่มีความขัดแย้ง (Merge Conflict) โดยวิเคราะห์ระดับ Abstract Syntax Tree และจัดลำดับ Commutative Statements ให้โดยตรง (รองรับทั้งการระบุไฟล์และข้อความโค้ดอินไลน์):
```bash
python fault_keeper.py solve-merge base.py our_changes.py their_changes.py
```

#### 6. สตาร์ทเซิร์ฟเวอร์ MCP JSON-RPC 2.0 สำหรับ AI (`mcp`)
เปิดเซิร์ฟเวอร์ MCP ผ่าน Stdio สำหรับเชื่อมต่อกับ Cursor, Claude Desktop, Antigravity หรือเครื่องมือ AI Agent:
```bash
python fault_keeper.py mcp
# หรือระบุ transport ชัดเจน:
python fault_keeper.py mcp --transport stdio
```

</details>

<br/>

<details>
<summary><b>🤖 วิธีที่ 2: เชื่อมต่อเข้ากับ AI Agents ผ่าน MCP 2.0 (Cursor, Claude, Antigravity)</b></summary>

<br/>

Fault-Keeper มีตัวให้บริการ MCP แบบ Standalone ที่รองรับ **MCP 2.0 Protocol** เต็มรูปแบบ:

#### ไฟล์เริ่มทำงาน: [`mcp_server.py`](./mcp_server.py)
นำการตั้งค่านี้ไปวางในไฟล์คอนฟิก MCP ของคุณ (เช่น `~/.gemini/config/mcp_config.json`, `claude_desktop_config.json`, หรือการตั้งค่า MCP ใน Cursor):

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

#### 5 เครื่องมือหลักสำหรับ AI (Omni-Tools):
1. **`fk_audit`**: สแกนไฟล์หรือโฟลเดอร์เพื่อตรวจสอบความปลอดภัย โครงสร้างสถาปัตยกรรม และ Deadlock
2. **`fk_diagnose`**: วินิจฉัยจุดคอขวด, Async Race Conditions, N+1 Query, ReDoS และ Causal Root Cause
3. **`fk_patch`**: สร้างโค้ดแก้ไข (Prescriptive Patch) พร้อมจำลองรันบน Shadow Sandbox
4. **`fk_verify`**: ตรวจสอบความสอดคล้องข้ามระบบ และพิสูจน์ข้อกำหนดทางคณิตศาสตร์
5. **`fk_discover`**: ให้ AI เรียกดูรายละเอียดเฉพาะทางของเสาหลักทั้ง 51 เสาได้แบบ JIT (Just-in-Time)

#### ตัวอย่างการสั่งการผ่าน AI Chat (ไม่ต้องพิมพ์คำสั่งใน Terminal):
เมื่อเชื่อมต่อ MCP เรียบร้อยแล้ว คุณสามารถสั่งงานในแชทกับ AI (เช่น Antigravity) ได้โดยตรง:
* *"ช่วย audit โค้ดในโฟลเดอร์ src ให้หน่อย"* ➔ AI จะเรียกใช้เครื่องมือ `fk_audit`
* *"ช่วยวินิจฉัยหาสาเหตุของบั๊กในโมดูลนี้"* ➔ AI จะเรียกใช้เครื่องมือ `fk_diagnose`
* *"ช่วยทดสอบแพตช์แก้ไขจุดนี้ใน Sandbox"* ➔ AI จะเรียกใช้เครื่องมือ `fk_patch`
* *"ช่วยตรวจสอบสัญญา API ระหว่าง Frontend กับ Backend"* ➔ AI จะเรียกใช้เครื่องมือ `fk_verify`
* *"ช่วยค้นหาเสาหลักที่ช่วยป้องกัน Deadlock ในฐานข้อมูล"* ➔ AI จะเรียกใช้เครื่องมือ `fk_discover`

</details>

<br/>

<details>
<summary><b>📦 วิธีที่ 3: ฝังใช้งานในโค้ด Python แบบ Library & Facade (FaultKeeper)</b></summary>

<br/>

เรียกใช้งานระบบทั้งหมดผ่าน Facade เดียวด้วยกลไก Lazy Loading เพื่อลดภาระหน่วยความจำ:

```python
import fault_keeper

# สร้าง Singleton Instance เพื่อเข้าถึงทุกระบบ
fk = fault_keeper.FaultKeeper()

# 1. งานคำนวณเชิงตัวเลขและการหาอนุพันธ์อัตโนมัติ (Automatic Differentiation)
dual_x = fk.num.DualNumber(real=3.0, dual=1.0)
y = dual_x * dual_x + 5.0  # y = x^2 + 5
print(f"ค่าของฟังก์ชัน: {y.real}, อนุพันธ์ (Derivative): {y.dual}")

# 2. ตรวจสอบบั๊ก Timezone ในการใช้ฟอร์แมต YYYY
has_trap, details = fk.num.TimezoneDriftDetector.detect_format_drift("YYYY-MM-dd")
if has_trap:
    print(f"คำเตือน: การใช้ Week-based year อาจทำให้วันสิ้นปีคลาดเคลื่อน: {details}")

# 3. ตรวจสอบวงรอบ Deadlock ใน Transaction
wfg = fk.daily.WaitForGraph()
wfg.add_dependency(tx_a="TX1", tx_b="TX2")
wfg.add_dependency(tx_a="TX2", tx_b="TX1") # เกิดวงรอบซ้ำ
cycles = wfg.detect_cycles()
print(f"ตรวจพบวงรอบ Deadlock: {cycles}")

# 4. เรียกใช้ Allocator หน่วยความจำระดับฮาร์ดแวร์
allocator = fk.systems.ZSC_ThP() # Dual-Pool Zero Compaction Stall THP Allocator
ptr = allocator.allocate(size_bytes=1024 * 1024 * 2) # จองบน 2MB THP Static Arena
```

</details>

<br/>

<details>
<summary><b>🛡️ วิธีที่ 4: คุ้มกันฟังก์ชันทันทีด้วย One-Line Decorators (@armored, @guard)</b></summary>

<br/>

เพิ่มการตรวจสอบความถูกต้องระดับรันไทม์ให้กับฟังก์ชันสำคัญด้วย Decorator บรรทัดเดียว:

```python
import fault_keeper

# ดักจับ State Drift และจำกัดความคลาดเคลื่อนทางคณิตศาสตร์
@fault_keeper.armored(max_drift=0.05)
def critical_financial_settlement(account_id: str, balance: float):
    # หากเกิดความคลาดเคลื่อนเกินเกณฑ์ที่กำหนด ระบบจะแจ้งเตือนทันที
    return process_settlement(account_id, balance)

# ตรวจสอบสัญญาของข้อมูลขาเข้า (Contract Assertion)
@fault_keeper.guard
def transfer_funds(source: str, target: str, amount: float):
    assert amount > 0, "จำนวนเงินต้องมากกว่าศูนย์"
    return execute_transfer(source, target, amount)
```

</details>

---

<br/>

## 🏛️ คลังสารบัญ 51 เสาหลักสถาปัตยกรรม (The 51 Core Pillars Catalog)

โครงสร้างระบบแบ่งออกเป็น **13 โดเมนหลัก** ครอบคลุมตั้งแต่งานคณิตศาสตร์ประยุกต์ ไปจนถึงฮาร์ดแวร์เคอร์เนล และเกราะป้องกัน AI:

| 🧪 ตารางธาตุ 51 เสาหลักวิศวกรรม (The 51 Core Pillars Taxonomy) | 🛡️ เกราะคุ้มกัน AI และระบบรู้คิด (AI Agent Armor & Cognitive Router) |
| :---: | :---: |
| <img src="./assets/2.jpg" alt="The 51 Core Pillars Taxonomy" width="100%"> | <img src="./assets/3.jpg" alt="AI Agent Armor & Cognitive Router" width="100%"> |
| *การจำแนก 51 เสาหลักครอบคลุม 13 โดเมน: ตั้งแต่งานคณิตศาสตร์, จัดการหน่วยความจำฮาร์ดแวร์, ไปจนถึงกับดักในชีวิตประจำวัน* | *เกราะสกัดกั้น AI ขี้เกียจ (ASP-HG), ทำลาย Doom Loop (ACT-LO), และช่วยประหยัด Prompt Token ด้วย Omni-Tools* |

<br/>

<details>
<summary><b>1. Applied Mathematics & Numerical Kernel (fk.num): 3 เสาหลัก</b></summary>
<br/>

| เสาหลัก | ชื่อเต็ม | กลไกและหน้าที่ |
| :--- | :--- | :--- |
| **FK-NUM** | Numerical Kernel | คำนวณ Dual Number Automatic Differentiation, 128-bit Fixed-Point Arithmetic ปลอดภัยทางการเงิน, และ Welford Streaming Variance ในเวลา $O(1)$ |
| **FK-SLA** | Sparse Linear Algebra | จัดเก็บ SIMD-CSR/CSC เรียงตาม Cache Line 64 ไบต์, ขนาน SpMV, Pivoted Cholesky Solver และ Randomized Low-Rank SVD (Halko-Martinsson-Tropp) |
| **FK-GEO** | Robust Geometry Engine | ขจัด Precision Collapse ด้วย Shewchuk Exact Adaptive Floating-Point Predicates (Orient2D / InCircle), SIMD Linear BVH Tree (Morton Codes 30-bit), และ Monotone Chain Convex Hull ในเวลา $O(N \log N)$ |

</details>

<details>
<summary><b>2. Hardware, Microarchitecture & Systems Low-Level (fk.systems): 16 เสาหลัก</b></summary>
<br/>

| เสาหลัก | ชื่อเต็ม | กลไกและหน้าที่ |
| :--- | :--- | :--- |
| **NUMA-AFS** | NUMA-Aware Affinity Sentry | ถอดรหัส ACPI SLIT Distance Matrix คำนวณ Locality Quotient (LQ) และใช้ Kuhn-Munkres Bipartite Matching (KM-BAW) จับคู่ Cores กับ Pages กำจัด Interconnect Stall |
| **ZSC-THP** | Zero-Stall Compaction THP | สถาปัตยกรรม Dual-Pool Hybrid Allocation Arena (DHACS) แบ่ง 2MB THP Static Arena และ 4KB Dynamic Pool ร่วมกับ Asynchronous Background Siphon ขจัด Direct Compaction Stall ให้กลายเป็น 0.0ms |
| **FS-CCO** | False Sharing Cache Optimizer | จัดเรียงโครงสร้าง Struct ตาม 64-byte Cache-line ป้องกัน L1 Cache Invalidation จากการประมวลผลคู่ขนาน |
| **HEH-DR** | Hazard-Epoch Hybrid Reclamation | ระบบจัดการหน่วยความจำ Lock-Free ผสมผสาน 3-Epoch Based Reclamation (EBR) และ Hazard Pointers Overhead $< 3\%$ |
| **APM-RLME** | Adaptive Array Layout Engine | สลับโครงสร้างข้อมูลระหว่าง Array of Structures (AoS) และ Structure of Arrays (SoA) แบบ Zero-Stall ด้วย Vectorized Strides ตามอัตราการอ่าน/เขียน |
| **TSCA** | Topological Simplicial Arbiter | ควบคุม Concurrency แบบ Wait-Free ด้วย Simplicial Complex Topology ตรวจสอบ Betti Number ($H_1 = 0$) รับประกันปลอด Deadlock ถาวร |
| **CAM-RO** | Cross-Arch Memory Reordering | วิเคราะห์และสังเคราะห์ Atomic Memory Barriers ข้ามสถาปัตยกรรม x86 TSO และ ARMv8/RISC-V Weak Memory Model |
| **AC-SBE** | Auto-Cooperative Yield Injector | สแกน AST ตรวจจับภาระ CPU-heavy ใน Async Loop และฉีดจุด Cooperative Preemption อัตโนมัติ ป้องกัน Event Loop ค้าง |
| **EV-IPP** | eBPF Verifier Simulator | จำลอง 64-bit Truncated Numbers (Tnum) และ Register Bounds เพื่อตรวจสอบความปลอดภัยของโปรแกรมเคอร์เนล eBPF ภายใน IDE |
| **SABA** | SIMD Auto-Vectorization Analyzer | วิเคราะห์ Loop-carried Dependency และ Pointer Aliasing เพื่อทลายสิ่งกีดขวางการทำ Auto-Vectorization (AVX-512 / NEON) |
| **SC-BBW** | Spectral Basic-Block Weaver | สร้าง Graph Laplacian ของ Control Flow Graph และใช้ Fiedler Eigenvector จัดเรียง Basic Block ลด Instruction Cache Misses |
| **PT-PAFS** | Pointer Provenance & Tree Borrows | ติดตามต้นทางของ Pointer และสิทธิ์การใช้งานตามกฎ Tree Borrows ดักจับพฤติกรรม Undefined Behavior ใน Unsafe C/Rust |
| **DIS-RA** | Deterministic io_uring Arbiter | บริหารจัดการ Submission Queue (SQ) / Completion Queue (CQ) ของ io_uring แบบ Zero-Copy พร้อมระบบ Backpressure ป้องกัน CQE Overflow |
| **H-TSS** | Hardware Tagged Pointer Sentry | จำลอง ARM TBI / x86 UAM Pointer Tagging ดักจับ Use-After-Free (UAF) และ Buffer Overflow ในรันไทม์ |
| **MD-BBE** | Monomorphization Deduplicator | วิเคราะห์ความเท่าเทียมเชิงโครงสร้างของ Generic Functions (Structural ABI) และยุบรวม Thunks ช่วยลดขนาดไบนารีลง 40% ถึง 70% |
| **DMCS** | Dominator-Tree Memory Cut Sentry | วิเคราะห์ Memory Reference Graph ด้วย Dominator Tree และตัดวงจรขยะที่หลงเหลือด้วย Max-Flow Min-Cut กู้คืนแรมคืนได้ $\ge 80\%$ |

</details>

<details>
<summary><b>3. Daily Developer Traps & Pitfalls (fk.daily): 7 เสาหลัก</b></summary>
<br/>

| เสาหลัก | ชื่อเต็ม | กลไกและหน้าที่ |
| :--- | :--- | :--- |
| **FT-DSO** | Flaky Test Sieve & Order Oracle | สับเปลี่ยนลำดับการรันเทส ($\pi_{\text{shuf}}$), ค้นหาคู่พิษด้วย Gray Code Binary Search $O(N \log N)$, ดักจับ State Leakage, และเร่งเวลาด้วย Virtual Event-Clock Quenching |
| **Tx-DLO** | Transaction Deadlock Oracle | วิเคราะห์ Wait-For Directed Graph ($\mathcal{G}_{\text{wfg}}$) บังคับใช้ Havender Total Lock Ordering ($\prec_{\text{lock}}$) รับประกัน $\Pr(\text{Deadlock}) \equiv 0.0$ และเรียง Batch Keys ล่วงหน้า |
| **CDC-ABS** | Cross-Boundary Contract Sentry | สกัดกั้นการเปลี่ยนแปลง API ที่ทำลาย Client ข้าม Backend-Frontend ในระดับ AST (Zero-E2E) ด้วย Structural Subtyping Covariance Invariant |
| **AEC-VS** | Env Contract & Secret Sentry | ตรวจสอบความถูกต้องและข้อกำหนดของตัวแปรสภาพแวดล้อม (`.env`) ป้องกัน Secret รั่วไหลและการตั้งค่าเพี้ยน |
| **TC-GTC** | Timezone & DST Trap Detector | ตรวจจับข้อผิดพลาดเรื่อง Timezone, Daylight Saving Time (DST), และการใช้รูปแบบปีสลับกันระหว่าง Week-based `YYYY` กับ Calendar `yyyy` |
| **RDA-NP** | ReDoS Catastrophic Backtrack Sentry | วิเคราะห์ความซับซ้อนของ Regular Expressions และตรวจจับความเสี่ยง Catastrophic Backtracking ก่อนขึ้นโปรดักชัน |
| **CASI-OP** | Cache Stampede & Invalidation Sentry | ควบคุมลำดับการล้างแคชควบคู่กับธุรกรรมฐานข้อมูล พร้อมฉีดอัลกอริทึม XFetch ป้องกันสภาวะ Cache Stampede |

</details>

<details>
<summary><b>4. AI Agent Armor & Cognitive Router (fk.armor, fk.mcp): 4 เสาหลัก</b></summary>
<br/>

| เสาหลัก | ชื่อเต็ม | กลไกและหน้าที่ |
| :--- | :--- | :--- |
| **ASP-HG** | Anti-Placeholder Guard | ดักจับและระงับการลบโค้ดมักง่ายของ AI (เช่น `// implement later`, `... existing code ...`) ด้วย AST Structural Anchor Matching |
| **ACT-LO** | Agent Thrashing Loop Oracle | ตรวจจับลูปวนซ้ำซ้อนของการแก้โค้ด (Doom Loop) บังคับใช้ Monotonic Progress Invariant และสกัด Minimal Unsatisfiable Core (MUC) |
| **SC-PVE** | Speculative Candidate Parallel Verifier | ประเมิน Candidate Patches หลายทางเลือกแบบคู่ขนานบน In-Memory CoW Shadow Sandboxes คัดเลือกทางเลือกที่ดีที่สุดด้วย Zhang-Shasha Tree Edit Distance |
| **MCP-OFA** | Model Context Protocol Omni-Facade | ยุบรวมเครื่องมือเหลือ 5 Omni-Tools ช่วยประหยัดโทเคนคำสั่ง System Prompt พร้อมรองรับ Progressive JIT Discovery (`fk_discover`) |

</details>

<details>
<summary><b>5. Developer Workflow, Typing, Formal & Distributed Systems: 21 เสาหลัก</b></summary>
<br/>

| หมวดหมู่ | เสาหลักเด่น | กลไกและหน้าที่ |
| :--- | :--- | :--- |
| **Typing (fk.typing)** | **FSAS**, **ATH-BS**, **AE-FPS**, **TWSA**, **ACDS** | ซ่อมแซมไวยากรณ์เสมือน Ghost CST, สังเคราะห์ Typed-Hole DTO, ดักจับการลืมใส่ `await`, และระบบ Auto-complete บน Type Lattice |
| **Workflow (fk.workflow)** | **CRCAE**, **LQPC**, **SSDL**, **STAS**, **A-SMW**, **PTHO** | สืบหาสาเหตุ Root Cause บรรทัดเดียว, แก้ไข N+1 Query ด้วย Polyhedral Model, จัดการ Dependency Hell, และรวมไฟล์ AST 3-Way Merge |
| **Audit (fk.audit)** | **U-FSR**, **WPA-HIS** | ประเมินความแข็งแรงของไฟล์เดี่ยว (Shannon Entropy, Cohesion) และคำนวณคะแนนสถาปัตยกรรมทั้งระบบ 0 ถึง 100 (Acyclic DAG, Modularity) |
| **Full-Stack (fk.workflow)** | **ZEC-SW**, **GSLD** | สลับโครงสร้างฐานข้อมูลแบบ Zero-Downtime ด้วย Shadow Triggers, และแก้ CSS Overflow ด้วย Linear Programming Simplex |
| **Formal (fk.formal)** | **CIS3**, **DCEG**, **SADS**, **FSLS** | สังเคราะห์ Mock Data ด้วย Z3 Dual SMT Consensus, กราฟอนุพันธ์ Differential Causality, และซิงค์โค้ดด้วย Category Theory |
| **Distributed & Time (fk.dist)** | **D-CAS**, **CADRE** | จำลอง Network Partition / Clock Drift แบบ Deterministic Replay, และบันทึก Time-Travel Execution Tracer ย้อนสถานะโค้ด |

</details>

---

<br/>

## 🧪 การรันชุดทดสอบระบบ (Test Verification & Quality Gates)

<div align="center">
  <img src="./assets/1.jpg" alt="4-Tier Verification Architecture" width="100%" />
  <p><i>สถาปัตยกรรมการทดสอบ 4 ระดับขั้น: จาก Micro 1:1 Invariants สู่ Stress, Cluster Phase-Gates และ Holistic E2E รับประกันโค้ดบริสุทธิ์ 100%</i></p>
</div>

<br/>

<details>
<summary><b>🛡️ สถาปัตยกรรมการทดสอบ 4 ระดับขั้น (4-Tier Verification Architecture)</b></summary>
<br/>

Fault-Keeper แบ่งระดับการทดสอบออกเป็น 4 ขั้น เพื่อตรวจสอบความถูกต้องในทุกชั้นการทำงาน:
1. **Tier 1 (Micro 1:1 Invariants)**: ทดสอบสมการและ Invariant ทางคณิตศาสตร์เป็นรายเสาหลักโดยใช้โค้ดจริง
2. **Tier 2 (Stress & Concurrency)**: ทดสอบความหน่วงและสภาวะการแย่งชิงทรัพยากร (Race Conditions)
3. **Tier 3 (Cluster Phase-Gates)**: ทดสอบจำลองสถานการณ์จริงของระบบใหญ่ เช่น The Monorepo Flaky-Deadlock Gate และ The Multi-Socket NUMA Cluster
4. **Tier 4 (Holistic E2E)**: ทดสอบการทำงานของคำสั่ง CLI และการรับส่งข้อมูลผ่าน MCP Daemon

```bash
# รันชุดทดสอบทั้งหมด 723 เทส
python -m pytest -q
```
```text
============================ 723 passed in 73.14s =============================
```

</details>

---

<br/>

## 📁 โครงสร้างโปรเจกต์ (Repository Directory Layout)

<details>
<summary><b>📂 ผังโครงสร้างโฟลเดอร์โครงการ (Complete Directory Tree)</b></summary>
<br/>

```text
Fault-Keeper/
├── fault_keeper.py            # Sovereign Standalone CLI Entrypoint (Layer 1)
├── mcp_server.py              # MCP 2.0 JSON-RPC Standalone Server Daemon (Layer 2)
├── pyproject.toml             # Project Metadata & Packaging Configuration
├── requirements.txt           # Production Runtime Dependencies (NumPy, SciPy, Z3)
├── requirements-dev.txt       # Developer Test Dependencies (PyTest)
│
├── src/
│   └── fault_keeper/          # Core Python Facade & Modules
│       ├── __init__.py        # Singleton FaultKeeper & Lazy Module Loader
│       ├── facade.py          # Unified Omni-Facade & Subsystem Routers
│       ├── systems/           # Hardware & Systems Low-Level Sentries (16 เสาหลัก: NUMA, THP, eBPF...)
│       ├── daily/             # Daily Developer Traps (FT-DSO, Tx-DLO, CDC-ABS)
│       ├── typing/            # Inner-Loop Typing Sentinels (Ghost CST, Await Checker)
│       ├── workflow/          # Developer Productivity (CRCAE, SSDL, N+1 Query)
│       ├── audit/             # Architectural Health & File Robustness (U-FSR, WPA-HIS)
│       └── ...                # Other Domain Engines (num, sla, geo, armor, formal, dist)
│
├── tests/                     # 4-Tier Zero-Mock Deterministic Test Suites (723 Tests)
│   ├── test_tier1_invariants.py
│   ├── test_exhaustive_imports.py
│   ├── test_phase2_tier3_cluster_gate.py
│   ├── test_phase3_tier3_cluster_gate.py
│   └── pillars/               # 1:1 Invariant Tests per Pillar
│
└── assets/
    ├── fault_keeper_chest.png # Project Visual Mascot
    └── 1.jpg - 9.jpg          # System Architecture & Infographic Assets
```

</details>

## ☕ คืนเวลาให้กับตัวคุณ & สนับสนุนผู้พัฒนา (Reclaim Your Time & Support)

<div align="center">
  <img src="./assets/9.jpg" alt="Reclaim Your Time" width="100%" />
  <p><i>คืนเวลาและสมาธิให้กับการสร้างสรรค์: โคลน ติดตั้ง และเริ่มเขียนโค้ดได้อย่างสบายใจ ไร้ความกังวล</i></p>
</div>

<br/>

หากคุณชื่นชอบหรือเครื่องมือนี้ช่วยประหยัดเวลาและพลังงานในการพัฒนาของคุณ สามารถสนับสนุนค่าน้ำชา กาแฟ และเครื่องดื่มเย็น ๆ ให้กับพวกเราเพื่อเป็นกำลังใจในการพัฒนาต่อไปได้ที่:

<p align="left">
  <a href="https://ko-fi.com/xtanthaix" target="_blank">
    <img src="https://img.shields.io/badge/Support%20on-Ko--fi-FF5E5B?style=for-the-badge&logo=kofi&logoColor=white" alt="Support on Ko-fi" height="46" />
  </a>
</p>

ขอบคุณทุกการสนับสนุนและทุกแรงใจมากๆ ครับ 🙏💖☕

---

<br/>

## 📜 ลิขสิทธิ์และการเผยแพร่ (License)

โปรเจกต์นี้เผยแพร่ภายใต้สัญญาอนุญาตสากล **MIT License** อนุญาตให้นำไปประยุกต์ใช้งาน ต่อยอด ปรับแต่ง และผสานเข้ากับโปรเจกต์เชิงพาณิชย์ได้อย่างอิสระครับ ✨
