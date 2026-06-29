# 成员二验收文档：联邦学习与聚合核心模块

## 负责范围

成员二负责项目的算法核心：本地模型训练、联邦学习轮次、安全 MPC 聚合封装、明文基线对比、模型参数管理和聚合轮次状态。

核心目标：

- 三个客户端各自使用本地数据训练模型。
- 每轮训练后，本地模型参数通过秘密分享进入安全聚合。
- 聚合结果作为新的全局模型参数。
- 多轮训练后全局 loss 下降。
- 安全聚合结果与明文平均基线一致。

## 对应文件

| 文件 | 说明 |
| --- | --- |
| `src/secure_agg/core/federated_learning.py` | 联邦学习本地训练、多轮训练和 loss 计算 |
| `src/secure_agg/core/federated_mpc.py` | 加密模型参数封装和安全 MPC 聚合入口 |
| `src/secure_agg/core/aggregation.py` | 明文求和/平均、份额聚合和聚合结果恢复 |
| `src/secure_agg/core/model_params.py` | 模型参数加载、保存、展平和形状校验 |
| `src/secure_agg/core/round_state.py` | 聚合轮次状态管理 |
| `tests/unit/test_federated_learning.py` | 联邦学习训练闭环测试 |
| `tests/unit/test_federated_mpc.py` | 安全 MPC 聚合接口测试 |
| `tests/unit/test_aggregation.py` | 聚合正确性测试 |
| `tests/unit/test_model_params.py` | 模型参数管理测试 |
| `tests/unit/test_round_state.py` | 轮次状态测试 |

## 模块流程

联邦学习闭环：

```text
global_parameters
  -> P1/P2/P3 local training
  -> local_parameters
  -> encrypt_model_parameters
  -> aggregate_encrypted_model_parameters
  -> new global_parameters
  -> next round
```

安全聚合闭环：

```text
local model parameters
  -> fixed-point encoding
  -> secret sharing
  -> aggregate shares
  -> reconstruct sum and average
```

## 核心接口

联邦学习：

```python
train_local_linear_model(initial_parameters, examples)
run_secure_federated_round(global_parameters, datasets)
run_secure_federated_training(initial_parameters, datasets)
mean_squared_error(parameters, datasets)
```

安全 MPC 聚合：

```python
encrypt_model_parameters(party_id, parameter_values)
aggregate_encrypted_model_parameters(encrypted_parameters)
```

聚合恢复：

```python
plaintext_sum(parameter_vectors)
plaintext_average(parameter_vectors)
aggregate_received_shares(received_shares)
reconstruct_aggregation(aggregate_shares)
```

## 验收命令

```bash
pytest -q tests/unit/test_federated_learning.py tests/unit/test_federated_mpc.py tests/unit/test_aggregation.py tests/unit/test_model_params.py tests/unit/test_round_state.py
```

运行联邦学习演示：

```bash
python scripts/run_fl_demo.py
```

## 通过标准

- `run_secure_federated_training` 能完成多轮联邦训练。
- `scripts/run_fl_demo.py` 输出 `Result: PASS`。
- 初始 loss 明显高于最终 loss。
- 最终线性模型参数接近演示数据对应的 `y = 2x + 1`。
- 每轮全局参数等于三个本地模型参数经过安全聚合后的平均值。
- 缺失参与方、重复参与方、参数维度不一致时能够抛出明确异常。
- 聚合结果与明文求和/平均基线误差不超过 `1e-5`。

## 答辩说明

成员二可以这样说明：

> 我负责联邦学习算法核心。P1、P2、P3 分别在本地数据上训练线性模型，得到本地模型参数后，不直接做明文平均，而是调用安全 MPC 聚合接口。聚合得到的平均参数作为下一轮全局模型。演示中 loss 从初始值持续下降，说明联邦学习训练闭环有效。

## 与其他成员的接口

成员一提供密码基础：

```python
encode_vector(...)
split_vector(...)
reconstruct_vector(...)
decode_vector(...)
```

成员三通过 HTTP 服务调用核心聚合逻辑：

```python
aggregate_received_shares(...)
reconstruct_aggregation(...)
```
