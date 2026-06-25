# 基于秘密分享的三方模型参数安全聚合系统开发指导书

## 文档信息

| 项目    | 内容                            |
| ----- | ----------------------------- |
| 项目名称  | 基于秘密分享的三方模型参数安全聚合系统           |
| 开发语言  | Python 3.10 及以上               |
| 核心技术  | 加法秘密分享、定点数编码、有限域运算、HTTP 通信    |
| 开发人数  | 3 人                           |
| 运行参与方 | 3 个参与方节点                      |
| 安全模型  | 半诚实模型，即参与方遵守协议，但可能尝试分析自己获得的数据 |
| 最终输出  | 三方模型参数的安全求和结果和平均结果            |
| 项目性质  | 教学与实验项目，不可直接用于生产环境            |

---

## 项目目标

本项目需要实现一个三方安全聚合系统。

三个参与方分别拥有自己的模型参数：

```text
参与方 P1：参数 x1
参与方 P2：参数 x2
参与方 P3：参数 x3
```

系统需要计算：

[
sum = x_1+x_2+x_3
]

以及：

[
average=\frac{x_1+x_2+x_3}{3}
]

但任何参与方都不能直接获得其他参与方的原始参数。

项目必须满足以下基本要求：

1. 每个参与方只能读取自己的原始模型参数。
2. 原始参数不得通过网络发送给其他参与方。
3. 原始参数不得写入公共日志。
4. 参数必须先转换为秘密份额，再通过网络发送。
5. 单个秘密份额不能直接恢复原始参数。
6. 三个聚合份额组合后能够恢复正确的聚合结果。
7. 安全聚合结果应与普通明文聚合结果基本一致。
8. 系统必须支持正数、负数、小数和多维模型参数。
9. 系统必须检测维度错误、重复消息、参与方缺失和通信超时。
10. 所有核心模块必须具有自动化测试。

---

## 项目非目标

本项目暂不解决以下问题：

* 恶意参与方故意发送错误参数。
* 参与方通过模型参数实施投毒攻击。
* 参与方在聚合中途退出。
* 对最终聚合结果进行差分隐私保护。
* 真实互联网环境中的证书管理。
* 大规模深度学习模型的高性能传输。
* 同态加密、混淆电路等更复杂协议。
* 多轮联邦学习训练和模型收敛问题。

这些内容可以写入报告的“未来改进方向”，但不得影响基础版本交付。

---

# 系统原理

## 加法秘密分享

假设参与方 P1 的某个参数为：

```text
10
```

P1 不直接发送 10，而是随机生成两个数字，例如：

```text
23
7
```

然后计算第三个数字，使三个数字在有限域中相加后等于原参数。

可以简单理解为：

```text
10 被拆成：23、7、-20
```

满足：

```text
23 + 7 - 20 = 10
```

单独查看 23、7 或 -20，都无法确定原参数是 10。

在实际代码中，所有运算都在模素数 (P) 的有限域中完成。

对于秘密 (x)，生成三个份额：

[
s_1=random()
]

[
s_2=random()
]

[
s_3=(x-s_1-s_2)\bmod P
]

因此：

[
x=(s_1+s_2+s_3)\bmod P
]

---

## 三方安全聚合流程

每个参与方都把自己的参数拆成三份。

```text
P1 的参数：拆成 P1→P1、P1→P2、P1→P3
P2 的参数：拆成 P2→P1、P2→P2、P2→P3
P3 的参数：拆成 P3→P1、P3→P2、P3→P3
```

每个参与方只保存或接收属于自己的那一份。

P1 收到：

```text
P1→P1
P2→P1
P3→P1
```

P1 计算：

```text
aggregate_share_1 = P1→P1 + P2→P1 + P3→P1
```

同理：

```text
aggregate_share_2 = P1→P2 + P2→P2 + P3→P2
aggregate_share_3 = P1→P3 + P2→P3 + P3→P3
```

最后组合三个聚合份额：

```text
aggregate_sum =
    aggregate_share_1
  + aggregate_share_2
  + aggregate_share_3
```

得到：

```text
P1 原参数 + P2 原参数 + P3 原参数
```

完整流程如下：

```text
加载本地参数
    ↓
定点数编码
    ↓
生成三个秘密份额
    ↓
向三个参与方分发秘密份额
    ↓
每个参与方计算本地聚合份额
    ↓
收集三个聚合份额
    ↓
恢复聚合总和
    ↓
解码为浮点数
    ↓
计算三方平均值
```

---

# 安全边界

## 安全假设

本项目采用半诚实安全模型：

* 所有参与方都会按照协议执行。
* 参与方可能保存并分析自己收到的消息。
* 参与方不会篡改协议或伪造消息。
* 默认不存在多个参与方联合推测第三方参数的情况。

## 能够保护的内容

系统能够防止某个参与方直接看到其他参与方通过网络发送的原始模型参数。

单个秘密份额本身不能恢复原始参数。

协调器只能看到最终的聚合份额和聚合结果，不能看到每个参与方的明文参数。

## 无法保护的内容

最终聚合结果本身可能泄露信息。

例如只有三个参与方时，P1 和 P2 如果联合起来，并且知道：

```text
总和 = P1 + P2 + P3
```

那么它们可以计算：

```text
P3 = 总和 - P1 - P2
```

这是聚合结果本身造成的信息泄露，不是秘密分享实现错误。

项目报告中必须明确写出该限制，不得声称系统能够抵抗所有形式的合谋攻击。

---

# 固定技术方案

为避免三名成员分别采用不同方案，项目统一采用以下技术决定。

| 项目       | 固定方案                             |
| -------- | -------------------------------- |
| 编程语言     | Python                           |
| 通信方式     | HTTP + JSON                      |
| Web 框架   | FastAPI                          |
| HTTP 客户端 | httpx                            |
| 数据验证     | Pydantic                         |
| 自动测试     | pytest                           |
| 秘密分享     | 三方加法秘密分享                         |
| 随机数生成    | Python `secrets` 模块              |
| 浮点数处理    | 定点数编码                            |
| 有限域素数    | (P=2^{61}-1)                     |
| 定点缩放倍数   | `SCALE = 1_000_000`              |
| 参与方数量    | 固定为 3                            |
| 聚合操作     | 求和、平均                            |
| 默认端口     | 协调器 8000，P1 8101，P2 8102，P3 8103 |
| MVP 参数类型 | 一维浮点数数组                          |
| 扩展参数类型   | 多层模型参数字典                         |

所有涉及有限域的计算必须使用 Python 原生整数，不得直接使用可能溢出的 NumPy `int64`。

---

# 定点数编码规则

秘密分享只能直接处理整数，因此需要把浮点数转换为整数。

## 编码

对浮点数 (x)：

[
encoded=\operatorname{round}(x\times SCALE)\bmod P
]

Python 接口：

```python
def encode_float(value: float) -> int:
    ...
```

例如：

```text
value = 1.234567
SCALE = 1_000_000
encoded = 1234567
```

## 解码

先判断有限域中的整数是否表示负数：

```python
if value > P // 2:
    value = value - P
```

然后除以缩放倍数：

```python
decoded = value / SCALE
```

Python 接口：

```python
def decode_int(value: int) -> float:
    ...
```

## 数组接口

```python
def encode_vector(values: list[float]) -> list[int]:
    ...

def decode_vector(values: list[int]) -> list[float]:
    ...
```

## 精度要求

安全聚合结果与普通浮点聚合结果之间的最大绝对误差必须满足：

```text
max_absolute_error <= 1e-5
```

---

# 项目目录结构

三名成员必须严格按照以下目录组织代码。

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
│       ├── __init__.py
│       ├── constants.py
│       ├── exceptions.py
│       ├── crypto/
│       │   ├── __init__.py
│       │   ├── field.py
│       │   ├── fixed_point.py
│       │   └── secret_sharing.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── model_params.py
│       │   ├── aggregation.py
│       │   └── round_state.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── messages.py
│       ├── network/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── party_server.py
│       │   └── coordinator_server.py
│       └── cli/
│           ├── __init__.py
│           ├── party.py
│           └── coordinator.py
├── tests/
│   ├── unit/
│   │   ├── test_field.py
│   │   ├── test_fixed_point.py
│   │   ├── test_secret_sharing.py
│   │   ├── test_model_params.py
│   │   ├── test_aggregation.py
│   │   └── test_round_state.py
│   ├── integration/
│   │   ├── test_message_validation.py
│   │   ├── test_three_party_round.py
│   │   └── test_http_communication.py
│   └── security/
│       ├── test_no_plaintext_in_messages.py
│       └── test_share_randomness.py
└── docs/
    ├── architecture.md
    ├── protocol.md
    ├── api.md
    ├── testing.md
    └── security_analysis.md
```

---

# 三名成员的总体分工

| 成员  | 主要职责                        | 核心目录                         |
| --- | --------------------------- | ---------------------------- |
| 成员一 | 有限域、定点数、秘密分享和安全性测试          | `crypto/`、`tests/security/`  |
| 成员二 | 模型参数、聚合逻辑、轮次状态和正确性测试        | `core/`、部分 `schemas/`        |
| 成员三 | HTTP 通信、协调器、参与方服务、启动脚本和系统集成 | `network/`、`cli/`、`scripts/` |

三名开发成员与运行时的 P1、P2、P3 不是同一个概念。

开发分工按模块划分。最终演示时，三名成员可以分别启动 P1、P2、P3 节点。

---

# 成员一指导书：密码学基础与秘密分享模块

## 角色定位

成员一负责建立整个系统可信赖的数学基础。

成员一交付的代码必须能够独立完成：

```text
浮点参数
  → 定点整数
  → 有限域秘密份额
  → 重构整数
  → 恢复浮点参数
```

成员一不负责 HTTP 服务、协调器或完整聚合业务。

## 负责文件

```text
src/secure_agg/constants.py
src/secure_agg/exceptions.py
src/secure_agg/crypto/field.py
src/secure_agg/crypto/fixed_point.py
src/secure_agg/crypto/secret_sharing.py
tests/unit/test_field.py
tests/unit/test_fixed_point.py
tests/unit/test_secret_sharing.py
tests/security/test_share_randomness.py
docs/protocol.md
docs/security_analysis.md
```

## constants.py

必须定义：

```python
PRIME = (1 << 61) - 1
SCALE = 1_000_000
PARTY_COUNT = 3
PARTY_IDS = ("P1", "P2", "P3")
```

禁止在其他模块重复编写这些常量。

## field.py

必须实现：

```python
def mod_add(a: int, b: int, prime: int = PRIME) -> int:
    """返回有限域加法结果。"""

def mod_sub(a: int, b: int, prime: int = PRIME) -> int:
    """返回有限域减法结果。"""

def vector_mod_add(
    left: list[int],
    right: list[int],
    prime: int = PRIME,
) -> list[int]:
    """逐元素执行有限域加法，长度不同必须抛出异常。"""

def normalize(value: int, prime: int = PRIME) -> int:
    """把任意整数规范化到 [0, prime) 范围。"""
```

要求：

* 空数组可以正常处理。
* 长度不一致必须抛出 `DimensionMismatchError`。
* 所有返回值必须位于 `[0, PRIME)`。
* 不得修改输入数组。

## fixed_point.py

必须实现：

```python
def encode_float(
    value: float,
    scale: int = SCALE,
    prime: int = PRIME,
) -> int:
    ...

def decode_int(
    value: int,
    scale: int = SCALE,
    prime: int = PRIME,
) -> float:
    ...

def encode_vector(
    values: list[float],
    scale: int = SCALE,
    prime: int = PRIME,
) -> list[int]:
    ...

def decode_vector(
    values: list[int],
    scale: int = SCALE,
    prime: int = PRIME,
) -> list[float]:
    ...
```

必须检查：

* `NaN` 不允许编码。
* 正无穷和负无穷不允许编码。
* 缩放后数值不能超出安全范围。
* 超出范围时抛出 `EncodingOverflowError`。
* 必须正确支持负数和零。

## secret_sharing.py

必须实现：

```python
def split_secret(
    secret: int,
    party_count: int = PARTY_COUNT,
    prime: int = PRIME,
) -> list[int]:
    """
    将一个有限域整数拆分为 party_count 个秘密份额。
    必须使用 secrets.randbelow。
    """

def reconstruct_secret(
    shares: list[int],
    prime: int = PRIME,
) -> int:
    """恢复一个秘密整数。"""

def split_vector(
    secret_vector: list[int],
    party_count: int = PARTY_COUNT,
    prime: int = PRIME,
) -> list[list[int]]:
    """
    返回形式：
    [
        share_for_p1,
        share_for_p2,
        share_for_p3,
    ]
    每个 share 均为与输入等长的整数数组。
    """

def reconstruct_vector(
    share_vectors: list[list[int]],
    prime: int = PRIME,
) -> list[int]:
    """从多个向量份额恢复原向量。"""
```

## 随机数要求

只允许使用：

```python
import secrets
secrets.randbelow(PRIME)
```

禁止使用：

```python
random.randint(...)
numpy.random...
```

原因是普通伪随机接口不适合生成安全秘密份额。

## 成员一测试要求

至少覆盖以下情况：

| 测试         | 预期结果          |
| ---------- | ------------- |
| 正整数拆分与恢复   | 恢复值等于原值       |
| 负数编码后拆分与恢复 | 解码值等于原值       |
| 小数编码与解码    | 误差不超过 `1e-6`  |
| 零值拆分       | 正确恢复零         |
| 向量拆分与恢复    | 每个元素均正确       |
| 多次拆分同一个秘密  | 生成的份额通常不同     |
| 少于三个份额     | 不允许在业务层执行完整恢复 |
| 数组长度不同     | 抛出维度异常        |
| NaN 和无穷    | 抛出编码异常        |
| 超大参数       | 抛出溢出异常        |

## 成员一验收标准

成员一任务完成必须同时满足：

```text
pytest tests/unit/test_field.py
pytest tests/unit/test_fixed_point.py
pytest tests/unit/test_secret_sharing.py
pytest tests/security/test_share_randomness.py
```

全部通过。

同时必须提供以下演示：

```python
values = [1.25, -2.5, 3.75]

encoded = encode_vector(values)
shares = split_vector(encoded)
reconstructed = reconstruct_vector(shares)
decoded = decode_vector(reconstructed)
```

输出应近似为：

```text
[1.25, -2.5, 3.75]
```

---

# 成员二指导书：模型参数与安全聚合核心

## 角色定位

成员二负责把成员一提供的秘密分享能力组合成可使用的安全聚合业务。

成员二需要实现：

```text
模型参数加载
参数形状校验
明文聚合基线
秘密份额聚合
聚合结果恢复
轮次状态管理
```

成员二不负责底层随机份额生成，也不负责 HTTP 服务器。

## 负责文件

```text
src/secure_agg/core/model_params.py
src/secure_agg/core/aggregation.py
src/secure_agg/core/round_state.py
src/secure_agg/schemas/messages.py
tests/unit/test_model_params.py
tests/unit/test_aggregation.py
tests/unit/test_round_state.py
tests/integration/test_message_validation.py
docs/api.md
```

## model_params.py

必须定义模型参数数据结构：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelParameters:
    values: list[float]
    shape: tuple[int, ...]
    names: tuple[str, ...] | None = None
```

必须实现：

```python
def load_parameters(path: str) -> ModelParameters:
    """从 JSON 文件读取模型参数。"""

def save_parameters(
    parameters: ModelParameters,
    path: str,
) -> None:
    """把模型参数保存为 JSON。"""

def flatten_parameters(
    parameter_groups: dict[str, list[float]],
) -> tuple[list[float], dict]:
    """把多组参数展平，并返回恢复所需元数据。"""

def restore_parameters(
    flat_values: list[float],
    metadata: dict,
) -> dict[str, list[float]]:
    """根据元数据恢复原始参数分组。"""

def validate_same_shape(
    parameter_sets: list[ModelParameters],
) -> None:
    """校验多个参与方参数形状是否相同。"""
```

JSON 参数格式统一为：

```json
{
  "shape": [4],
  "values": [1.0, 2.0, 3.0, 4.0]
}
```

扩展格式可以为：

```json
{
  "layers": {
    "layer1.weight": [1.0, 2.0],
    "layer1.bias": [0.1],
    "layer2.weight": [3.0, 4.0]
  }
}
```

基础版本必须首先支持第一种格式。

## aggregation.py

必须实现明文基线：

```python
def plaintext_sum(
    parameter_vectors: list[list[float]],
) -> list[float]:
    ...

def plaintext_average(
    parameter_vectors: list[list[float]],
) -> list[float]:
    ...
```

必须实现秘密份额本地聚合：

```python
def aggregate_received_shares(
    received_shares: list[list[int]],
    prime: int = PRIME,
) -> list[int]:
    """
    一个参与方把收到的 P1、P2、P3 三个秘密份额逐元素相加。
    返回该参与方的 aggregate share。
    """
```

必须实现聚合结果恢复：

```python
@dataclass(frozen=True)
class AggregationResult:
    encoded_sum: list[int]
    sum_values: list[float]
    average_values: list[float]
    participant_count: int

def reconstruct_aggregation(
    aggregate_shares: list[list[int]],
    participant_count: int = PARTY_COUNT,
) -> AggregationResult:
    ...
```

正确流程必须是：

```text
三个 aggregate share
    ↓
有限域求和
    ↓
得到 encoded_sum
    ↓
定点数解码
    ↓
得到 sum_values
    ↓
除以参与方数量
    ↓
得到 average_values
```

不得先对秘密份额直接执行普通浮点除法。

## round_state.py

必须定义每一轮聚合的状态。

推荐状态：

```python
class RoundStatus(str, Enum):
    CREATED = "created"
    COLLECTING_SHARES = "collecting_shares"
    SHARES_READY = "shares_ready"
    AGGREGATED = "aggregated"
    COMPLETED = "completed"
    FAILED = "failed"
```

必须定义：

```python
@dataclass
class AggregationRound:
    round_id: str
    participant_ids: tuple[str, ...]
    vector_length: int
    status: RoundStatus
    received_shares: dict[str, list[int]]
    aggregate_shares: dict[str, list[int]]
    error_message: str | None
```

必须支持：

```python
def add_received_share(
    self,
    sender_id: str,
    share: list[int],
) -> None:
    ...

def all_shares_received(self) -> bool:
    ...

def add_aggregate_share(
    self,
    party_id: str,
    share: list[int],
) -> None:
    ...

def all_aggregate_shares_received(self) -> bool:
    ...

def fail(self, message: str) -> None:
    ...
```

必须拒绝：

* 未知参与方。
* 重复提交。
* 错误轮次。
* 错误向量长度。
* 已完成轮次继续写入数据。
* 已失败轮次继续执行。

## messages.py

必须定义以下 Pydantic 数据模型。

```python
class RoundCreateRequest(BaseModel):
    round_id: str
    participant_ids: list[str]
    vector_length: int
    scale: int
    modulus: int

class ShareMessage(BaseModel):
    round_id: str
    sender_id: str
    receiver_id: str
    vector_length: int
    payload: list[int]
    digest: str

class AggregateShareMessage(BaseModel):
    round_id: str
    party_id: str
    vector_length: int
    payload: list[int]
    digest: str

class AggregationResultMessage(BaseModel):
    round_id: str
    sum_values: list[float]
    average_values: list[float]
    participant_count: int
    status: str
```

`digest` 使用 SHA-256 计算，用于发现消息损坏。

它不是数字签名，不得在报告中把它描述成身份认证机制。

## 成员二测试要求

必须覆盖：

| 测试         | 预期结果    |
| ---------- | ------- |
| 三组明文参数求和   | 结果正确    |
| 三组明文参数平均   | 结果正确    |
| 三组秘密份额本地聚合 | 结果维度正确  |
| 三个聚合份额恢复   | 与明文基线一致 |
| 正负小数混合     | 正确处理    |
| 空数组        | 明确定义行为  |
| 参数长度不同     | 抛出维度异常  |
| 未知参与方提交    | 拒绝      |
| 重复提交       | 拒绝      |
| 错误轮次提交     | 拒绝      |
| 轮次状态转换     | 符合状态机   |
| 已完成轮次再次写入  | 拒绝      |

## 成员二验收标准

以下代码必须能够完成完整的纯本地聚合：

```python
p1 = [1.0, 2.0, 3.0]
p2 = [2.0, 4.0, 6.0]
p3 = [3.0, 6.0, 9.0]
```

安全聚合结果：

```text
sum     = [6.0, 12.0, 18.0]
average = [2.0, 4.0, 6.0]
```

误差不得超过：

```text
1e-5
```

---

# 成员三指导书：通信、节点服务与系统集成

## 角色定位

成员三负责把成员一和成员二的模块连接成一个能够运行的三方网络系统。

成员三需要实现：

* 三个参与方 HTTP 服务。
* 一个聚合协调器。
* 参与方之间的秘密份额发送。
* 聚合轮次启动。
* 聚合份额提交。
* 最终结果查询。
* 超时、错误和日志处理。
* 一键启动和演示脚本。

成员三不得重新实现秘密分享和聚合算法，必须调用成员一、成员二提供的公开接口。

## 负责文件

```text
src/secure_agg/network/client.py
src/secure_agg/network/party_server.py
src/secure_agg/network/coordinator_server.py
src/secure_agg/cli/party.py
src/secure_agg/cli/coordinator.py
scripts/start_all.py
scripts/stop_all.py
scripts/run_demo.py
configs/
tests/integration/test_three_party_round.py
tests/integration/test_http_communication.py
tests/security/test_no_plaintext_in_messages.py
README.md
docs/architecture.md
docs/testing.md
```

## 系统节点

系统包含四个进程：

```text
Coordinator：端口 8000
P1：端口 8101
P2：端口 8102
P3：端口 8103
```

协调器负责：

* 创建聚合轮次。
* 保存参与方列表。
* 接收三个聚合份额。
* 调用聚合恢复函数。
* 保存最终结果。
* 向客户端返回聚合状态和结果。

协调器不得：

* 接收参与方原始模型参数。
* 接收每个参与方生成的完整三份秘密份额。
* 读取 `p1_params.json`、`p2_params.json` 或 `p3_params.json`。
* 在日志中输出秘密份额完整内容。

参与方负责：

* 读取自己的本地参数。
* 编码自己的参数。
* 生成三份秘密份额。
* 向 P1、P2、P3 分别发送对应份额。
* 保存其他参与方发送给自己的份额。
* 收齐份额后计算本地聚合份额。
* 把本地聚合份额提交给协调器。

## client.py

必须实现：

```python
async def post_json(
    url: str,
    payload: dict,
    timeout_seconds: float = 10.0,
) -> dict:
    """发送 HTTP POST 请求，并统一处理错误。"""

async def send_share(
    target_base_url: str,
    message: ShareMessage,
) -> None:
    ...

async def send_aggregate_share(
    coordinator_base_url: str,
    message: AggregateShareMessage,
) -> None:
    ...

async def get_round_status(
    coordinator_base_url: str,
    round_id: str,
) -> dict:
    ...
```

要求：

* 非 2xx 响应必须转为明确异常。
* 请求必须设置超时。
* 超时后不得无限重试。
* 默认最多重试 3 次。
* 重试间隔应逐次增加。
* 同一条消息重复发送时，服务端应能识别重复消息。

## party_server.py

必须提供以下接口。

### 健康检查

```http
GET /health
```

响应：

```json
{
  "party_id": "P1",
  "status": "ok"
}
```

### 创建本地轮次

```http
POST /rounds
```

作用：

* 初始化本地轮次状态。
* 记录 `round_id`。
* 记录参与方列表和参数长度。
* 不立即生成秘密份额。

### 启动参数分享

```http
POST /rounds/{round_id}/distribute
```

作用：

1. 读取本地参数。
2. 编码参数。
3. 生成三份秘密份额。
4. 向三个参与方发送份额。
5. 本地份额也通过统一的接收逻辑写入状态。

### 接收秘密份额

```http
POST /rounds/{round_id}/shares
```

必须执行：

* 校验 `round_id`。
* 校验 `receiver_id` 与当前节点一致。
* 校验发送方是否在参与方列表。
* 校验向量长度。
* 校验 `digest`。
* 拒绝重复发送方。
* 保存秘密份额。
* 不在日志中打印完整 `payload`。

### 计算本地聚合份额

```http
POST /rounds/{round_id}/aggregate
```

只有收齐三方秘密份额后才允许执行。

执行过程：

```text
received share from P1
+ received share from P2
+ received share from P3
= local aggregate share
```

然后把本地聚合份额发送给协调器。

### 查询本地状态

```http
GET /rounds/{round_id}
```

响应中允许包含：

* 轮次状态。
* 已收到哪些参与方的份额。
* 是否已经提交聚合份额。
* 错误信息。

响应中禁止包含：

* 原始模型参数。
* 完整秘密份额。
* 完整聚合份额。

## coordinator_server.py

必须提供以下接口。

### 健康检查

```http
GET /health
```

### 创建全局轮次

```http
POST /rounds
```

协调器生成或接收唯一的 `round_id`。

推荐使用：

```python
import uuid
round_id = str(uuid.uuid4())
```

创建后，协调器通知 P1、P2、P3 创建对应本地轮次。

### 接收聚合份额

```http
POST /rounds/{round_id}/aggregate-shares
```

必须执行：

* 检查轮次是否存在。
* 检查参与方是否合法。
* 检查长度。
* 检查摘要。
* 拒绝重复提交。
* 保存聚合份额。

收到三个聚合份额后：

1. 调用 `reconstruct_aggregation`。
2. 生成 `AggregationResultMessage`。
3. 将轮次状态更新为 `completed`。

### 查询聚合结果

```http
GET /rounds/{round_id}/result
```

未完成时：

```json
{
  "round_id": "...",
  "status": "collecting"
}
```

完成后：

```json
{
  "round_id": "...",
  "status": "completed",
  "sum_values": [6.0, 12.0, 18.0],
  "average_values": [2.0, 4.0, 6.0],
  "participant_count": 3
}
```

## 配置文件

`party_p1.json` 示例：

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

P2、P3 只修改：

* `party_id`
* `port`
* `parameter_file`

## 日志要求

允许记录：

```text
round_id
party_id
消息类型
向量长度
发送时间
接收时间
状态
错误原因
```

禁止记录：

```text
本地原始参数
完整秘密份额
完整聚合份额
其他参与方输入
```

正确日志示例：

```text
INFO round=abc123 party=P1 received_share sender=P2 length=1024
```

错误日志示例：

```text
INFO received payload=[19382, 82932, ...]
```

## 一键演示脚本

`run_demo.py` 必须完成：

1. 检查协调器和三个参与方是否在线。
2. 请求协调器创建轮次。
3. 通知三个参与方分发份额。
4. 等待份额发送完成。
5. 通知三个参与方计算本地聚合份额。
6. 轮询协调器结果。
7. 读取三个本地参数，仅用于演示程序计算明文基线。
8. 比较安全聚合与明文聚合。
9. 输出误差。
10. 输出测试是否通过。

演示输出格式：

```text
==================================================
Secure Aggregation Demo
==================================================
Round ID: 8a7f...

Participants: P1, P2, P3
Vector length: 3

[1/5] Creating aggregation round... OK
[2/5] Distributing secret shares... OK
[3/5] Computing local aggregate shares... OK
[4/5] Reconstructing aggregation result... OK
[5/5] Comparing with plaintext baseline... OK

Secure sum:     [6.0, 12.0, 18.0]
Secure average: [2.0, 4.0, 6.0]
Plain average:  [2.0, 4.0, 6.0]
Maximum error:  0.000000

Result: PASS
==================================================
```

---

# 三方统一接口约定

以下接口一旦确定，不得由单个成员擅自修改。

## 密码学接口

```python
encode_vector(values: list[float]) -> list[int]

decode_vector(values: list[int]) -> list[float]

split_vector(
    secret_vector: list[int],
    party_count: int = 3,
) -> list[list[int]]

reconstruct_vector(
    share_vectors: list[list[int]],
) -> list[int]
```

## 聚合接口

```python
aggregate_received_shares(
    received_shares: list[list[int]],
) -> list[int]

reconstruct_aggregation(
    aggregate_shares: list[list[int]],
    participant_count: int = 3,
) -> AggregationResult
```

## 数据顺序

`split_vector` 返回值的顺序固定为：

```text
index 0 → P1
index 1 → P2
index 2 → P3
```

必须在 `constants.py` 中建立映射：

```python
PARTY_TO_INDEX = {
    "P1": 0,
    "P2": 1,
    "P3": 2,
}
```

不得依赖字典遍历顺序判断份额属于哪个参与方。

## 异常类型

统一定义：

```python
class SecureAggregationError(Exception):
    pass

class DimensionMismatchError(SecureAggregationError):
    pass

class EncodingOverflowError(SecureAggregationError):
    pass

class InvalidShareError(SecureAggregationError):
    pass

class DuplicateMessageError(SecureAggregationError):
    pass

class UnknownParticipantError(SecureAggregationError):
    pass

class InvalidRoundStateError(SecureAggregationError):
    pass

class CommunicationError(SecureAggregationError):
    pass

class RoundTimeoutError(SecureAggregationError):
    pass
```

HTTP 服务需要将异常映射为合理状态码：

| 异常     | HTTP 状态码 |
| ------ | -------: |
| 参数格式错误 |      400 |
| 未知参与方  |      403 |
| 轮次不存在  |      404 |
| 重复提交   |      409 |
| 状态不允许  |      409 |
| 向量长度错误 |      422 |
| 服务内部错误 |      500 |
| 上游通信超时 |      504 |

---

# Git 协作规范

## 分支结构

```text
main
└── develop
    ├── feat/member-a-crypto
    ├── feat/member-b-core
    └── feat/member-c-network
```

所有开发必须在个人功能分支完成。

禁止直接向 `main` 提交代码。

## 合并顺序

推荐顺序：

```text
成员一 crypto
    ↓
合并到 develop
    ↓
成员二 core
    ↓
合并到 develop
    ↓
成员三 network
    ↓
全员集成测试
    ↓
develop 合并到 main
```

成员二可以在成员一开发期间使用临时接口桩，但最终必须删除接口桩并调用真实实现。

成员三可以在成员二开发期间使用模拟返回值，但正式提交前必须替换为真实模块。

## 提交信息格式

```text
feat(crypto): implement vector secret sharing
feat(core): add secure aggregation reconstruction
feat(network): add party share endpoint
test(crypto): add negative fixed-point tests
fix(core): reject duplicate aggregate shares
docs(protocol): document security assumptions
```

## Pull Request 要求

每个 PR 必须包含：

```text
修改内容
负责模块
新增接口
修改接口
测试命令
测试结果
已知限制
是否影响其他成员
```

修改公共接口时，必须获得另外两名成员确认。

---

# 集成顺序

## 第一阶段：接口冻结

三名成员共同确认：

* 常量。
* 函数名称。
* 参数类型。
* 返回类型。
* 异常类型。
* JSON 消息格式。
* 目录结构。

完成后建立空文件和函数声明。

## 第二阶段：成员一交付密码学模块

成员一完成：

```text
field.py
fixed_point.py
secret_sharing.py
```

成员二和成员三只通过公开接口调用，不得访问模块内部变量。

## 第三阶段：成员二交付聚合核心

成员二完成纯本地测试：

```text
三方明文参数
→ 秘密分享
→ 本地聚合份额
→ 重构聚合结果
```

此阶段不依赖 HTTP。

## 第四阶段：成员三接入 HTTP

成员三将本地函数调用替换为真实网络消息。

先实现单轮、单机、三个端口的演示。

## 第五阶段：系统测试

全员共同执行：

```bash
pytest
```

以及：

```bash
python scripts/run_demo.py
```

---

# 测试总方案

## 单元测试

单元测试必须验证每个函数自身逻辑，不启动 HTTP 服务。

必须包含：

* 有限域运算。
* 定点数编码。
* 定点数解码。
* 秘密拆分。
* 秘密恢复。
* 数组聚合。
* 状态机转换。
* 参数格式校验。

## 集成测试

集成测试验证多个模块协同工作。

必须包含：

### 正常三方聚合

```text
P1 = [1.0, 2.0, 3.0]
P2 = [2.0, 4.0, 6.0]
P3 = [3.0, 6.0, 9.0]
```

预期：

```text
sum = [6.0, 12.0, 18.0]
average = [2.0, 4.0, 6.0]
```

### 正负数聚合

```text
P1 = [-1.5, 2.25]
P2 = [3.0, -4.5]
P3 = [0.5, 1.25]
```

预期：

```text
sum = [2.0, -1.0]
average ≈ [0.666667, -0.333333]
```

### 零参数

```text
P1 = [0.0, 0.0]
P2 = [0.0, 0.0]
P3 = [0.0, 0.0]
```

预期全部为零。

### 长度不一致

P3 参数长度与 P1、P2 不同时，轮次必须失败，并返回明确错误。

### 重复份额

同一发送方重复提交份额时，服务端必须返回 409。

### 未知参与方

`P4` 提交数据时必须被拒绝。

### 错误摘要

篡改 `payload` 但不更新 `digest` 时必须被拒绝。

### 参与方超时

某个参与方未提交时，轮次不得错误地产生最终结果。

## 安全性测试

安全测试至少验证：

1. HTTP 消息中不存在明文参数数组。
2. 日志中不存在明文参数数组。
3. 同一个参数多次拆分时，生成的秘密份额不同。
4. 单个参与方获得的份额不能直接等于原始编码参数。
5. 协调器没有读取本地原始参数文件。
6. 秘密份额生成未使用 `random` 模块。

---

# 验收标准

项目最终通过验收必须满足以下全部条件。

## 功能验收

* 三个参与方均能独立启动。
* 协调器能够创建聚合轮次。
* 每个参与方能够加载自己的参数。
* 每个参与方能够生成三份秘密份额。
* 秘密份额能够发送给对应参与方。
* 每个参与方能够计算本地聚合份额。
* 协调器能够恢复聚合总和。
* 协调器能够输出平均结果。
* 安全结果与明文结果误差不超过 `1e-5`。

## 安全验收

* 网络中不发送原始模型参数。
* 公共日志中不打印原始模型参数。
* 使用 `secrets.randbelow` 生成份额。
* 单个秘密份额不能恢复原始参数。
* 文档明确写出威胁模型和安全限制。

## 工程验收

* 项目目录符合规范。
* 所有公开函数具有类型标注。
* 所有公开函数具有文档字符串。
* 异常被明确处理。
* 不使用裸 `except:`。
* HTTP 请求设置超时。
* 所有测试能够通过。
* README 提供完整启动步骤。
* 新环境可以根据 README 复现实验。

## 代码质量验收

不得出现：

```python
except:
    pass
```

不得出现：

```python
print(secret_share)
print(raw_parameters)
```

不得把端口、素数或缩放倍数散落在多个文件中。

不得为了通过测试直接写死：

```python
return [2.0, 4.0, 6.0]
```

---

# 推荐开发进度

| 时间    | 成员一       | 成员二         | 成员三              |
| ----- | --------- | ----------- | ---------------- |
| 第 1 天 | 确认协议和接口   | 确认参数格式和状态机  | 确认网络接口和配置        |
| 第 2 天 | 完成有限域和定点数 | 完成模型参数模块    | 完成 HTTP 客户端和健康检查 |
| 第 3 天 | 完成秘密分享    | 完成明文聚合和安全聚合 | 完成参与方服务器         |
| 第 4 天 | 完成安全测试    | 完成轮次状态和消息模型 | 完成协调器服务器         |
| 第 5 天 | 修复接口问题    | 完成聚合单元测试    | 完成一键启动脚本         |
| 第 6 天 | 参与集成测试    | 参与集成测试      | 运行三节点集成测试        |
| 第 7 天 | 安全分析文档    | 实验结果与误差分析   | README、演示和答辩材料   |

---

# 最终演示流程

答辩时按照以下顺序操作。

## 展示原始参数文件

只展示每个参与方拥有独立文件，不需要长时间展示具体参数。

```text
data/p1_params.json
data/p2_params.json
data/p3_params.json
```

## 启动四个服务

```bash
python -m secure_agg.cli.coordinator
python -m secure_agg.cli.party --config configs/party_p1.json
python -m secure_agg.cli.party --config configs/party_p2.json
python -m secure_agg.cli.party --config configs/party_p3.json
```

也可以使用：

```bash
python scripts/start_all.py
```

## 运行聚合

```bash
python scripts/run_demo.py
```

## 展示结果

重点展示：

* 聚合成功。
* 安全结果与明文结果一致。
* 网络消息中没有原始参数。
* 每次生成的秘密份额都不同。
* 最终仍能得到相同聚合结果。

## 答辩核心表述

可以使用以下说明：

> 本项目使用三方加法秘密分享。每个参与方先将自己的模型参数编码为有限域整数，再拆分为三个随机秘密份额。各参与方只接收其中一个份额，并在秘密份额上完成局部求和。最后组合三个局部聚合份额，恢复模型参数总和和平均值。在整个过程中，原始模型参数不会直接发送给其他参与方或协调器。

---

# 项目风险与处理方法

| 风险          | 原因         | 处理方式                   |
| ----------- | ---------- | ---------------------- |
| 浮点数无法直接秘密分享 | 有限域只处理整数   | 使用定点数编码                |
| 负数解码错误      | 有限域数值均为非负  | 大于 `P // 2` 时减去 `P`    |
| 整数溢出        | 固定宽度整数范围有限 | 使用 Python 原生整数         |
| 三方参数长度不同    | 模型结构不一致    | 开始聚合前校验长度              |
| 消息重复        | 网络重试导致重复请求 | 使用发送方和轮次进行去重           |
| 轮次数据混淆      | 多轮消息同时存在   | 所有消息必须携带 `round_id`    |
| 服务未启动       | 节点连接失败     | 聚合前执行健康检查              |
| 某参与方迟迟不发送   | 节点异常       | 设置超时并将轮次标记为失败          |
| 日志泄露数据      | 调试时打印数组    | 只记录长度和摘要               |
| 份额可预测       | 使用普通随机数    | 使用 `secrets.randbelow` |
| 最终结果泄露单方输入  | 参与方数量过少    | 在安全分析中明确输出泄露限制         |

---

# 可直接交给成员一 LLM 的执行指令

你是本项目的密码学基础模块开发者。请严格按照本指导书实现 `src/secure_agg/crypto/` 目录。

你的任务范围仅包括：

```text
constants.py
exceptions.py
field.py
fixed_point.py
secret_sharing.py
对应单元测试
对应安全测试
protocol.md
security_analysis.md
```

必须遵守以下规则：

1. 使用三方加法秘密分享。
2. 有限域素数固定为 `(1 << 61) - 1`。
3. 定点缩放倍数固定为 `1_000_000`。
4. 随机份额必须使用 `secrets.randbelow`。
5. 使用 Python 原生整数。
6. 所有公开函数必须具有类型标注和文档字符串。
7. 不得实现网络服务。
8. 不得改变指导书规定的函数名称和参数。
9. 必须支持正数、负数、小数、零和向量。
10. 必须提供 pytest 测试。

请按照以下顺序工作：

```text
先创建异常类型
再实现有限域运算
再实现定点数编码
再实现单个秘密的拆分与恢复
再实现向量拆分与恢复
最后编写测试和文档
```

每完成一个文件，都需要检查：

```text
输入是否合法
是否修改了输入对象
输出是否始终位于有限域
异常是否明确
测试是否覆盖边界情况
```

最终输出：

* 所有文件的完整代码。
* 文件路径。
* 测试命令。
* 预期测试结果。
* 安全假设和已知限制。

---

# 可直接交给成员二 LLM 的执行指令

你是本项目的安全聚合核心模块开发者。请严格按照本指导书实现 `src/secure_agg/core/` 和 `src/secure_agg/schemas/messages.py`。

你的任务范围包括：

```text
model_params.py
aggregation.py
round_state.py
messages.py
对应单元测试
消息验证测试
api.md
```

你必须调用成员一提供的以下接口：

```python
encode_vector
decode_vector
split_vector
reconstruct_vector
vector_mod_add
```

不得重新实现秘密分享算法。

必须完成：

1. 模型参数 JSON 加载和保存。
2. 参数形状校验。
3. 明文求和与平均基线。
4. 收到的秘密份额局部聚合。
5. 三个聚合份额的结果恢复。
6. 聚合轮次状态机。
7. Pydantic 消息模型。
8. 重复提交和错误状态检测。
9. 单元测试和集成测试。

实现时必须保证：

* 参数长度不同立即报错。
* 未收齐份额时不能聚合。
* 未收齐聚合份额时不能恢复结果。
* 已完成轮次不能再次写入。
* 安全聚合结果与明文结果误差不超过 `1e-5`。
* 所有公共函数具有类型标注和文档字符串。

最终输出：

* 所有文件完整代码。
* 使用到的成员一接口列表。
* 测试命令。
* 正常案例和异常案例测试结果。
* 与网络模块对接所需说明。

---

# 可直接交给成员三 LLM 的执行指令

你是本项目的网络通信与系统集成开发者。请严格按照本指导书实现 HTTP 服务和完整运行流程。

你的任务范围包括：

```text
network/client.py
network/party_server.py
network/coordinator_server.py
cli/party.py
cli/coordinator.py
scripts/start_all.py
scripts/stop_all.py
scripts/run_demo.py
configs/
HTTP 集成测试
README.md
architecture.md
testing.md
```

你必须调用成员一和成员二提供的公开接口，不得重新实现以下算法：

```text
定点数编码
秘密分享
有限域运算
秘密份额聚合
聚合结果恢复
```

系统必须运行四个服务：

```text
Coordinator：8000
P1：8101
P2：8102
P3：8103
```

必须提供：

```text
健康检查接口
创建轮次接口
分发秘密份额接口
接收秘密份额接口
本地聚合接口
提交聚合份额接口
结果查询接口
```

安全要求：

1. 协调器不能读取参与方原始参数文件。
2. HTTP 消息不能包含原始参数。
3. 日志不能输出完整参数和完整份额。
4. 每个请求必须携带 `round_id`。
5. 所有 HTTP 请求必须设置超时。
6. 重复请求必须被正确处理。
7. 消息摘要错误必须被拒绝。
8. 未知参与方必须被拒绝。

最终必须保证以下命令能够运行：

```bash
python scripts/start_all.py
python scripts/run_demo.py
```

并输出：

```text
安全求和结果
安全平均结果
明文基线结果
最大误差
PASS 或 FAIL
```

最终交付：

* 所有文件完整代码。
* 环境安装命令。
* 服务启动命令。
* 演示命令。
* API 说明。
* 集成测试结果。
* 常见错误及解决方法。

---

# 最终交付清单

项目提交前逐项检查：

```text
[ ] 成员一密码学模块测试全部通过
[ ] 成员二聚合核心测试全部通过
[ ] 成员三 HTTP 集成测试全部通过
[ ] 三个参与方可以独立启动
[ ] 协调器可以独立启动
[ ] 一键演示脚本运行成功
[ ] 正数聚合正确
[ ] 负数聚合正确
[ ] 小数聚合正确
[ ] 维度错误能够检测
[ ] 重复消息能够检测
[ ] 错误摘要能够检测
[ ] 日志中没有原始参数
[ ] 网络消息中没有原始参数
[ ] 安全结果与明文结果误差不超过 1e-5
[ ] README 能让新成员复现项目
[ ] 安全分析明确说明系统限制
[ ] 最终报告包含架构图、流程图和实验结果
[ ] 答辩演示已经完整排练
```
