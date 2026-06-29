# 三方联邦学习安全多方计算聚合系统

这是一个教学与实验用途的三方联邦学习安全多方计算聚合系统。项目模拟 P1、P2、P3 三个客户端分别持有本地训练数据，先在本地训练线性模型，再使用三方加法秘密分享完成模型参数的安全聚合，最终更新全局模型。

> 本项目面向课程实验和协议演示，不可直接用于生产环境。

## 任务对应

任务 12：联邦学习安全多方计算聚合

| 要求 | 当前实现 |
| --- | --- |
| 输入 | 各参与方本地训练后的模型参数，经过定点编码和秘密分享后形成加密份额 |
| 输出 | 聚合后的全局模型参数总和与平均值 |
| 处理思路 | 使用三方加法秘密分享，在有限域中对份额进行加法聚合 |
| 联邦学习 | P1、P2、P3 各自持有本地数据，本地训练后提交模型参数参与聚合 |
| 安全多方计算 | 通信过程中不发送明文参数，只发送秘密份额和聚合份额 |

## 系统流程

完整联邦学习实验流程：

```text
初始化全局模型
  -> P1/P2/P3 分别使用本地数据训练线性模型
  -> 每个客户端将本地模型参数定点编码
  -> 使用三方加法秘密分享拆分为 3 份加密份额
  -> 在秘密份额状态下完成聚合
  -> 恢复全局模型参数平均值
  -> 多轮迭代并观察 loss 下降
```

HTTP 安全聚合通信流程：

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

## 核心模块

| 模块 | 路径 | 说明 |
| --- | --- | --- |
| 密码基础 | `src/secure_agg/crypto/` | 有限域、定点数编码、秘密分享 |
| 联邦学习与聚合核心 | `src/secure_agg/core/` | 本地训练、安全 MPC 聚合、参数管理、轮次状态 |
| 通信与端到端演示 | `src/secure_agg/network/`、`scripts/`、`src/secure_agg/schemas/` | 参与方服务、协调器服务、HTTP 消息、演示脚本 |

三名成员的详细验收文档：

- [member1.md](member1.md)：密码基础模块验收
- [member2.md](member2.md)：联邦学习与聚合核心模块验收
- [member3.md](member3.md)：通信与端到端系统模块验收

## 技术方案

| 项目 | 方案 |
| --- | --- |
| 开发语言 | Python 3.10+ |
| 本地模型 | 一元线性回归，参数为 `[weight, bias]` |
| 联邦学习 | 三客户端本地训练 + 多轮安全平均聚合 |
| 安全多方计算 | 三方加法秘密分享 |
| 浮点数处理 | 定点数编码，缩放倍数 `SCALE = 1_000_000` |
| 有限域素数 | `P = 2^61 - 1` |
| 随机数生成 | `secrets.randbelow` |
| Web 服务 | Python 标准库 `http.server` |
| HTTP 客户端 | `httpx` |
| 数据验证 | Pydantic 兼容消息模型，未安装时使用内置校验 |
| 自动测试 | `pytest` |
| 参与方数量 | 固定为 3：P1、P2、P3 |
| 默认端口 | Coordinator 8000，P1 8101，P2 8102，P3 8103 |

## 关键接口

联邦学习闭环：

```python
run_secure_federated_training(initial_parameters, datasets)
run_secure_federated_round(global_parameters, datasets)
train_local_linear_model(initial_parameters, examples)
```

安全 MPC 聚合：

```python
encrypt_model_parameters(party_id, parameter_values)
aggregate_encrypted_model_parameters(encrypted_parameters)
```

秘密分享与恢复：

```python
encode_vector(values)
decode_vector(values)
split_vector(secret_vector, party_count=3)
reconstruct_vector(share_vectors)
aggregate_received_shares(received_shares)
reconstruct_aggregation(aggregate_shares, participant_count=3)
```

## 安装环境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行联邦学习演示

直接运行联邦学习 + 安全 MPC 聚合演示：

```bash
python scripts/run_fl_demo.py
```

期望看到类似输出：

```text
Federated Learning + Secure MPC Aggregation Demo
Clients: P1, P2, P3
Model: y = weight * x + bias
Aggregation: additive secret sharing over encrypted model parameters
Initial loss: 51.666667
Round 1: global_parameters=[1.864715, 0.672149], loss=0.480123
...
Round 8: global_parameters=[2.012400, 0.960412], loss=0.001244
Result: PASS
```

验收重点：

- 初始 loss 明显下降。
- 最终模型参数接近真实关系 `y = 2x + 1`。
- 聚合阶段调用秘密分享接口，不直接平均明文参数。

## 运行 HTTP 安全聚合演示

启动四个本地服务：

```bash
python scripts/start_all.py
```

运行通信聚合实验：

```bash
python scripts/run_demo.py
```

停止服务：

```bash
python scripts/stop_all.py
```

期望输出包含：

```text
Secure sum:     [6.0, 12.0, 18.0]
Secure average: [2.0, 4.0, 6.0]
Maximum error:  0.000000
Result: PASS
```

## HTTP 接口

参与方服务：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/rounds` | 创建本地聚合轮次 |
| `POST` | `/rounds/{round_id}/distribute` | 读取本地参数并分发秘密份额 |
| `POST` | `/rounds/{round_id}/shares` | 接收其他参与方发送的秘密份额 |
| `POST` | `/rounds/{round_id}/aggregate` | 计算本地聚合份额并提交协调器 |
| `GET` | `/rounds/{round_id}` | 查询本地轮次状态 |

协调器服务：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/rounds` | 创建全局聚合轮次 |
| `POST` | `/rounds/{round_id}/aggregate-shares` | 接收参与方聚合份额 |
| `GET` | `/rounds/{round_id}/result` | 查询聚合结果 |

## 测试与验收

运行全部测试：

```bash
pytest -q
```

按模块验收：

```bash
pytest -q tests/unit/test_field.py tests/unit/test_fixed_point.py tests/unit/test_secret_sharing.py tests/security
pytest -q tests/unit/test_federated_learning.py tests/unit/test_federated_mpc.py tests/unit/test_aggregation.py tests/unit/test_model_params.py tests/unit/test_round_state.py
pytest -q tests/integration tests/unit/test_federated_mpc.py tests/security/test_no_plaintext_in_messages.py
```

当前项目应满足：

- 三个客户端均有本地训练数据并参与联邦训练。
- 全局模型经过多轮训练后 loss 下降。
- 本地模型参数进入聚合前会被定点编码和秘密分享。
- 网络通信中不发送明文模型参数数组。
- 协调器只接收聚合份额并输出聚合结果。
- 安全聚合结果与明文基线误差不超过 `1e-5`。
- 维度错误、重复消息、错误摘要、未知参与方能够被明确处理。
- 单元测试、集成测试、安全测试全部通过。

## 安全边界

本项目采用半诚实安全模型：

- 参与方会按照协议执行。
- 参与方可能保存并分析自己收到的消息。
- 参与方不会篡改协议或伪造消息。
- 单个参与方不能从单个秘密份额恢复其他参与方参数。

系统不解决以下问题：

- 恶意参与方发送错误参数或进行模型投毒。
- 参与方在聚合中途退出。
- 差分隐私保护。
- 真实互联网环境中的证书管理。
- 多个参与方通过最终聚合结果合谋推测其他参与方输入。

特别注意：最终聚合结果本身可能泄露信息。例如 P1 和 P2 如果知道自己的输入和最终总和，就可以计算出 P3 的输入。这是精确聚合结果本身带来的限制，不是秘密分享实现错误。

## 项目结构

```text
.
├── configs/                 # 协调器和参与方配置
├── data/                    # HTTP 演示使用的本地参数文件
├── docs/                    # 协议、API、测试、安全说明
├── scripts/
│   ├── run_fl_demo.py       # 联邦学习 + 安全 MPC 聚合演示
│   ├── run_demo.py          # HTTP 安全聚合演示
│   ├── start_all.py
│   └── stop_all.py
├── src/secure_agg/
│   ├── crypto/              # 有限域、定点数、秘密分享
│   ├── core/                # 联邦学习、MPC 聚合、轮次状态
│   ├── network/             # 参与方和协调器 HTTP 服务
│   ├── schemas/             # 消息模型和摘要校验
│   └── cli/                 # 服务启动入口
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── member1.md
├── member2.md
└── member3.md
```

## 参考文档

- [docs/protocol.md](docs/protocol.md)：协议细节
- [docs/security_analysis.md](docs/security_analysis.md)：安全假设与限制
- [docs/api.md](docs/api.md)：消息格式和 API 说明
- [docs/testing.md](docs/testing.md)：测试设计与结果记录
- [plan.md](plan.md)：原始开发指导书
