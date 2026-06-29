# 成员三验收文档：通信与端到端系统模块

## 负责范围

成员三负责系统通信层和端到端演示：参与方服务、协调器服务、HTTP 客户端、消息模型、启动脚本和完整流程验收。

核心目标：

- 本地启动 3 个参与方服务和 1 个协调器服务。
- 协调器能够创建聚合轮次。
- 参与方能够分发秘密份额、接收秘密份额并提交聚合份额。
- 协调器能够收集 3 个聚合份额并恢复结果。
- HTTP 消息中不出现明文模型参数数组。

## 对应文件

| 文件 | 说明 |
| --- | --- |
| `src/secure_agg/network/client.py` | HTTP 请求工具和消息发送 |
| `src/secure_agg/network/party_server.py` | 参与方服务，负责份额分发和本地聚合份额提交 |
| `src/secure_agg/network/coordinator_server.py` | 协调器服务，负责轮次创建、聚合份额接收和结果查询 |
| `src/secure_agg/network/http_utils.py` | HTTP JSON 读写和错误响应 |
| `src/secure_agg/schemas/messages.py` | 消息模型、摘要校验、字段验证 |
| `src/secure_agg/cli/party.py` | 参与方命令行入口 |
| `src/secure_agg/cli/coordinator.py` | 协调器命令行入口 |
| `scripts/start_all.py` | 一键启动协调器和三个参与方 |
| `scripts/stop_all.py` | 停止本地服务 |
| `scripts/run_demo.py` | HTTP 安全聚合端到端演示 |
| `scripts/run_fl_demo.py` | 联邦学习 + 安全 MPC 聚合演示 |
| `tests/integration/test_http_communication.py` | HTTP 通信集成测试 |
| `tests/integration/test_message_validation.py` | 消息校验测试 |
| `tests/security/test_no_plaintext_in_messages.py` | 通信消息不含明文参数测试 |

## 系统服务

本地运行时包含 4 个服务：

| 服务 | 默认地址 |
| --- | --- |
| Coordinator | `127.0.0.1:8000` |
| P1 | `127.0.0.1:8101` |
| P2 | `127.0.0.1:8102` |
| P3 | `127.0.0.1:8103` |

参与方与开发成员不是同一个概念。P1、P2、P3 是运行时客户端；成员一、二、三是开发分工。

## HTTP 流程

```text
Coordinator 创建 round
  -> P1/P2/P3 创建本地 round
  -> P1/P2/P3 读取各自参数文件
  -> 每个参与方拆分秘密份额并分别发送给 P1/P2/P3
  -> 每个参与方收齐 3 份后计算本地聚合份额
  -> P1/P2/P3 向 Coordinator 提交聚合份额
  -> Coordinator 收齐 3 个聚合份额并恢复 sum 和 average
```

## 验收命令

通信集成测试：

```bash
pytest -q tests/integration tests/security/test_no_plaintext_in_messages.py
```

端到端 HTTP 演示：

```bash
python scripts/start_all.py
python scripts/run_demo.py
python scripts/stop_all.py
```

联邦学习演示：

```bash
python scripts/run_fl_demo.py
```

## 通过标准

- `scripts/start_all.py` 能启动 1 个协调器和 3 个参与方。
- `/health` 接口可正常返回。
- `scripts/run_demo.py` 输出 `Result: PASS`。
- 端到端聚合结果中 `Maximum error` 不超过 `1e-5`。
- 重复消息、错误摘要、未知参与方、维度错误能够被拒绝。
- `ShareMessage` 序列化后不包含 `"values"` 或明文参数数组。
- 服务日志只记录轮次 ID、参与方 ID、消息类型、向量长度等元信息，不打印完整明文参数。

## 答辩说明

成员三可以这样说明：

> 我负责系统通信与端到端演示。项目本地启动一个协调器和三个参与方服务，参与方之间只传输秘密份额，协调器只接收聚合份额。通过 `run_demo.py` 可以验证 HTTP 通信链路，通过 `run_fl_demo.py` 可以验证联邦学习训练和安全聚合的整体效果。

## 与其他成员的接口

成员一生成秘密份额，成员二提供聚合函数。成员三在 HTTP 服务中调用：

```python
split_vector(...)
aggregate_received_shares(...)
reconstruct_aggregation(...)
send_share(...)
send_aggregate_share(...)
```

成员三不重新实现密码算法和聚合算法，只负责把它们接入服务与通信流程。
