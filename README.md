# 基于秘密分享的三方模型参数安全聚合系统

这是一个教学与实验用途的三方模型参数安全聚合系统。系统使用三方加法秘密分享、定点数编码和有限域运算，在不直接暴露各参与方原始模型参数的前提下，计算三方模型参数的求和结果与平均结果。

> 本项目面向课程实验和协议演示，不可直接用于生产环境。

## 项目目标

三个参与方分别持有自己的模型参数：

```text
P1: x1
P2: x2
P3: x3
```

系统需要计算：

```text
sum = x1 + x2 + x3
average = (x1 + x2 + x3) / 3
```

同时满足：

- 每个参与方只能读取自己的原始参数。
- 原始参数不得通过网络发送给其他参与方。
- 原始参数不得写入公共日志。
- 参数必须先转换为秘密份额，再通过网络发送。
- 单个秘密份额不能直接恢复原始参数。
- 三个聚合份额组合后能够恢复正确聚合结果。
- 支持正数、负数、小数和向量参数。
- 能检测维度错误、重复消息、参与方缺失和通信超时。

## 技术方案

| 项目 | 方案 |
| --- | --- |
| 开发语言 | Python 3.10+ |
| Web 服务 | Python 标准库 `http.server` |
| HTTP 客户端 | httpx |
| 数据验证 | Pydantic 兼容消息模型，未安装时使用内置校验 |
| 自动测试 | pytest |
| 秘密分享 | 三方加法秘密分享 |
| 随机数生成 | `secrets.randbelow` |
| 浮点数处理 | 定点数编码 |
| 有限域素数 | `P = 2^61 - 1` |
| 定点缩放倍数 | `SCALE = 1_000_000` |
| 参与方数量 | 固定为 3 |
| 默认端口 | Coordinator 8000，P1 8101，P2 8102，P3 8103 |

所有有限域计算应使用 Python 原生整数，避免使用可能溢出的固定宽度整数类型。

## 系统原理

每个参与方会把自己的参数编码为有限域整数，然后拆成三份秘密份额。例如某个秘密值 `x` 会被拆分为：

```text
s1 = random()
s2 = random()
s3 = (x - s1 - s2) mod P
```

满足：

```text
x = (s1 + s2 + s3) mod P
```

三方聚合流程如下：

```text
加载本地参数
  -> 定点数编码
  -> 生成三个秘密份额
  -> 分发给 P1、P2、P3
  -> 每个参与方本地累加收到的份额
  -> 向协调器提交本地聚合份额
  -> 协调器组合三个聚合份额
  -> 解码为浮点数
  -> 输出 sum 和 average
```

## 目录结构

推荐项目结构如下：

```text
secure-aggregation/
├── README.md
├── requirements.txt
├── pyproject.toml
├── configs/
│   ├── coordinator.json
│   ├── party_p1.json
│   ├── party_p2.json
│   └── party_p3.json
├── data/
│   ├── p1_params.json
│   ├── p2_params.json
│   └── p3_params.json
├── scripts/
│   ├── start_all.py
│   ├── stop_all.py
│   └── run_demo.py
├── src/
│   └── secure_agg/
│       ├── constants.py
│       ├── exceptions.py
│       ├── crypto/
│       ├── core/
│       ├── schemas/
│       ├── network/
│       └── cli/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
└── docs/
    ├── architecture.md
    ├── protocol.md
    ├── api.md
    ├── testing.md
    └── security_analysis.md
```

详细模块职责、函数签名和测试要求见 [plan.md](plan.md)。

## 环境准备

本项目建议使用 Python 3.10+。在一台新的电脑上拿到项目后，先进入项目根目录并创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 使用：

```powershell
.venv\Scripts\Activate.ps1
```

然后安装依赖：

```bash
pip install -r requirements.txt
```

确认依赖安装成功：

```bash
python -c "import httpx, pydantic, fastapi, uvicorn; print('deps ok')"
```

如果看到 `deps ok`，说明运行环境已经准备好。

## 参数文件格式

基础版本使用一维浮点数数组：

```json
{
  "shape": [3],
  "values": [1.0, 2.0, 3.0]
}
```

三个参与方分别读取：

```text
data/p1_params.json
data/p2_params.json
data/p3_params.json
```

扩展版本可以支持多层模型参数字典：

```json
{
  "layers": {
    "layer1.weight": [1.0, 2.0],
    "layer1.bias": [0.1],
    "layer2.weight": [3.0, 4.0]
  }
}
```

## 配置示例

`configs/party_p1.json`：

```json
{
  "party_id": "P1",
  "host": "127.0.0.1",
  "port": 8101,
  "parameter_file": "data/p1_params.json",
  "coordinator_url": "http://127.0.0.1:8000",
  "party_urls": {
    "P1": "http://127.0.0.1:8101",
    "P2": "http://127.0.0.1:8102",
    "P3": "http://127.0.0.1:8103"
  }
}
```

P2 和 P3 只需要修改 `party_id`、`port` 和 `parameter_file`。

## 快速运行

最简单的完整演示流程如下：

```bash
python scripts/start_all.py
python scripts/run_demo.py
python scripts/stop_all.py
```

成功时 `run_demo.py` 会输出：

```text
Secure sum:     [6.0, 12.0, 18.0]
Secure average: [2.0, 4.0, 6.0]
Plain average:  [2.0, 4.0, 6.0]
Maximum error:  0.000000

Result: PASS
```

也可以手动分别启动协调器和三个参与方：

```bash
PYTHONPATH=src python -m secure_agg.cli.coordinator --config configs/coordinator.json
PYTHONPATH=src python -m secure_agg.cli.party --config configs/party_p1.json
PYTHONPATH=src python -m secure_agg.cli.party --config configs/party_p2.json
PYTHONPATH=src python -m secure_agg.cli.party --config configs/party_p3.json
```

停止后台服务：

```bash
python scripts/stop_all.py
```

## 项目验收流程

不看代码时，可以按下面流程确认项目是否完成。

### 1. 环境验收

```bash
source .venv/bin/activate
python --version
python -c "import httpx, pydantic, fastapi, uvicorn; print('deps ok')"
```

期望 Python 版本为 3.10+，并输出 `deps ok`。

### 2. 文件结构验收

确认关键目录存在：

```bash
ls src/secure_agg/crypto
ls src/secure_agg/core
ls src/secure_agg/network
ls src/secure_agg/schemas
ls src/secure_agg/cli
ls configs data scripts docs tests
```

应能看到：

- 成员一模块：有限域、定点数、秘密分享。
- 成员二模块：参数处理、聚合逻辑、轮次状态、消息模型。
- 成员三模块：HTTP 客户端、参与方服务、协调器服务、CLI、启动脚本、配置和文档。

### 3. 核心流程验收

项目应满足以下流程：

```text
P1/P2/P3 参数文件存在
每个参与方只读取自己的 data/*_params.json
参数先调用 encode_vector
再调用 split_vector
每方收到三份 share 后调用 aggregate_received_shares
协调器收到三份 aggregate share 后调用 reconstruct_aggregation
最终输出 sum 和 average
```

对应重点文件：

```text
data/p1_params.json
data/p2_params.json
data/p3_params.json
src/secure_agg/network/party_server.py
src/secure_agg/network/coordinator_server.py
```

### 4. 服务启动验收

```bash
python scripts/start_all.py
```

期望输出：

```text
coordinator: OK
P1: OK
P2: OK
P3: OK
All services are running.
```

### 5. 演示结果验收

```bash
python scripts/run_demo.py
```

期望输出包含：

```text
Secure sum:     [6.0, 12.0, 18.0]
Secure average: [2.0, 4.0, 6.0]
Plain average:  [2.0, 4.0, 6.0]
Maximum error:  0.000000
Result: PASS
```

安全聚合结果与明文基线的最大绝对误差应不超过 `1e-5`。验收结束后停止服务：

```bash
python scripts/stop_all.py
```

### 6. 安全验收

人工检查以下约束：

- 协调器不读取 `data/p1_params.json`、`data/p2_params.json`、`data/p3_params.json`。
- HTTP 消息只发送秘密份额 `payload`，不发送原始参数 `values`。
- 日志只记录 `round_id`、`party_id`、消息类型、向量长度和状态，不打印完整参数或完整份额。
- `digest` 是 SHA-256 完整性校验，不是数字签名或身份认证机制。

### 7. 常见运行问题

端口被占用时可能看到 `address already in use`，先执行：

```bash
python scripts/stop_all.py
```

如果仍然失败，需要关闭占用 `8000`、`8101`、`8102`、`8103` 的其他程序。

如果出现 `ModuleNotFoundError`，通常是没有激活虚拟环境或没有安装依赖：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

如果出现 `service is not reachable`，先确认服务已启动，再查看 `logs/` 下的服务日志。

## HTTP 接口

### 参与方服务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/rounds` | 创建本地聚合轮次 |
| `POST` | `/rounds/{round_id}/distribute` | 读取本地参数并分发秘密份额 |
| `POST` | `/rounds/{round_id}/shares` | 接收其他参与方发送的秘密份额 |
| `POST` | `/rounds/{round_id}/aggregate` | 计算本地聚合份额并提交协调器 |
| `GET` | `/rounds/{round_id}` | 查询本地轮次状态 |

### 协调器服务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/rounds` | 创建全局聚合轮次 |
| `POST` | `/rounds/{round_id}/aggregate-shares` | 接收参与方聚合份额 |
| `GET` | `/rounds/{round_id}/result` | 查询聚合结果 |

未完成时，结果接口返回轮次状态；完成后返回：

```json
{
  "round_id": "...",
  "status": "completed",
  "sum_values": [6.0, 12.0, 18.0],
  "average_values": [2.0, 4.0, 6.0],
  "participant_count": 3
}
```

## 核心接口

密码学模块需要提供：

```python
encode_vector(values: list[float]) -> list[int]
decode_vector(values: list[int]) -> list[float]
split_vector(secret_vector: list[int], party_count: int = 3) -> list[list[int]]
reconstruct_vector(share_vectors: list[list[int]]) -> list[int]
```

聚合模块需要提供：

```python
aggregate_received_shares(received_shares: list[list[int]]) -> list[int]
reconstruct_aggregation(
    aggregate_shares: list[list[int]],
    participant_count: int = 3,
) -> AggregationResult
```

`split_vector` 返回顺序固定为：

```text
index 0 -> P1
index 1 -> P2
index 2 -> P3
```

## 测试与自动化验收

运行全部测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest
```

按模块运行：

```bash
pytest tests/unit
pytest tests/integration
pytest tests/security
```

在限制本地 socket 的沙箱中，HTTP 集成测试会自动跳过；在普通本机环境中，它们会启动真实本地 HTTP 服务并验证完整网络流程。

最低测试范围包括：

- 有限域加法、减法和向量加法。
- 定点数编码和解码。
- 正数、负数、小数、零值和向量秘密分享。
- 三方聚合结果与明文基线一致。
- 参数长度不一致时失败。
- 重复消息、未知参与方和错误摘要被拒绝。
- HTTP 消息和日志中不出现原始参数。
- 秘密份额随机性检查。

## 安全边界

本项目采用半诚实安全模型：

- 参与方会按照协议执行。
- 参与方可能保存并分析自己收到的消息。
- 参与方不会篡改协议或伪造消息。
- 默认不存在多个参与方联合推测第三方参数的情况。

系统能够防止单个参与方直接看到其他参与方通过网络发送的原始参数。单个秘密份额不能恢复原始参数，协调器只接收聚合份额和最终聚合结果。

系统不解决以下问题：

- 恶意参与方故意发送错误参数。
- 参数投毒攻击。
- 参与方在聚合中途退出。
- 差分隐私保护。
- 真实互联网环境中的证书管理。
- 多个参与方通过最终聚合结果合谋推测其他参与方输入。

特别注意：最终聚合结果本身可能泄露信息。例如 P1 和 P2 如果知道自己的输入和最终总和，就可以计算出 P3 的输入。这是聚合结果本身带来的限制，不是秘密分享实现错误。

## 开发分工

| 成员 | 主要职责 | 核心目录 |
| --- | --- | --- |
| 成员一 | 有限域、定点数、秘密分享和安全性测试 | `crypto/`、`tests/security/` |
| 成员二 | 模型参数、聚合逻辑、轮次状态和正确性测试 | `core/`、`schemas/` |
| 成员三 | HTTP 通信、协调器、参与方服务、启动脚本和系统集成 | `network/`、`cli/`、`scripts/` |

开发成员与运行时的 P1、P2、P3 不是同一个概念。开发按模块分工，最终演示时可以由三名成员分别启动三个参与方节点。

## 验收标准

项目完成时应满足：

- 三个参与方和协调器均可独立启动。
- 每个参与方只读取自己的参数文件。
- 网络中不发送原始模型参数。
- 公共日志中不打印原始模型参数或完整秘密份额。
- 使用 `secrets.randbelow` 生成随机份额。
- 协调器能够恢复聚合总和并输出平均值。
- 安全结果与明文结果误差不超过 `1e-5`。
- 维度错误、重复消息、错误摘要和超时能够被明确处理。
- 所有单元测试、集成测试和安全测试通过。
- `python scripts/start_all.py` 能启动四个服务。
- `python scripts/run_demo.py` 能输出 `Result: PASS`。
- `python scripts/stop_all.py` 能停止后台服务。

## 参考文档

- [plan.md](plan.md)：完整开发指导书。
- `docs/protocol.md`：协议细节。
- `docs/security_analysis.md`：安全假设与限制。
- `docs/api.md`：消息格式和 API 说明。
- `docs/testing.md`：测试设计与结果记录。
