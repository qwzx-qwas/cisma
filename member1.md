# 成员一验收文档：密码基础模块

## 负责范围

成员一负责安全多方计算的密码基础能力，保证模型参数能够在有限域中安全编码、拆分、恢复，并且秘密份额具备随机性。

核心目标：

- 浮点模型参数可以稳定转换为有限域整数。
- 有限域中的加法、减法、向量加法正确。
- 一个秘密值或参数向量可以拆成 3 份秘密份额。
- 只有收齐全部份额才能恢复原始值。
- 每次拆分同一秘密时，份额应不同，避免固定泄露模式。

## 对应文件

| 文件 | 说明 |
| --- | --- |
| `src/secure_agg/constants.py` | 有限域素数、缩放倍数、参与方数量和 ID |
| `src/secure_agg/crypto/field.py` | 有限域规范化、加法、减法、向量加法 |
| `src/secure_agg/crypto/fixed_point.py` | 浮点数定点编码与解码 |
| `src/secure_agg/crypto/secret_sharing.py` | 三方加法秘密分享与恢复 |
| `tests/unit/test_field.py` | 有限域运算测试 |
| `tests/unit/test_fixed_point.py` | 定点数编码测试 |
| `tests/unit/test_secret_sharing.py` | 秘密分享正确性测试 |
| `tests/security/test_share_randomness.py` | 份额随机性与安全随机源测试 |

## 模块原理

项目使用三方加法秘密分享。对有限域中的秘密值 `x`，随机生成前两个份额：

```text
s1 = random()
s2 = random()
s3 = (x - s1 - s2) mod P
```

满足：

```text
x = (s1 + s2 + s3) mod P
```

其中 `P = 2^61 - 1`。浮点模型参数会先乘以 `SCALE = 1_000_000` 转成整数，再进入有限域。

## 验收命令

```bash
pytest -q tests/unit/test_field.py tests/unit/test_fixed_point.py tests/unit/test_secret_sharing.py tests/security/test_share_randomness.py
```

也可以运行成员一相关安全测试：

```bash
pytest -q tests/security
```

## 通过标准

- 正数、负数、小数、零值都能正确编码和解码。
- 有限域加法、减法和向量加法符合取模规则。
- `split_secret` 和 `split_vector` 能生成 3 份秘密份额。
- `reconstruct_secret` 和 `reconstruct_vector` 能恢复原始有限域值。
- 同一个秘密多次拆分产生的份额通常不同。
- 代码使用 `secrets.randbelow`，不使用 `random.randint` 或 `numpy.random`。
- 参数超出可编码范围时能抛出明确异常。

## 答辩说明

成员一可以这样说明：

> 我负责底层密码基础。模型参数先经过定点编码进入有限域，然后通过三方加法秘密分享拆成 3 份。单个份额不能恢复原始参数，只有三份相加才能恢复秘密值。随机份额由 `secrets.randbelow` 生成，保证每次拆分结果不同。

## 与其他成员的接口

成员二调用：

```python
encode_vector(values)
decode_vector(values)
split_vector(secret_vector, party_count=3)
reconstruct_vector(share_vectors)
```

成员三通过消息接口传输成员一生成的整数份额，不直接处理明文模型参数。
