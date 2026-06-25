# Secure Aggregation Protocol

This document describes the member-one cryptographic foundation for the
three-party secure aggregation demo.

## Constants

- Finite field prime: `P = (1 << 61) - 1`
- Fixed-point scale: `SCALE = 1_000_000`
- Party count: `3`
- Party identifiers: `P1`, `P2`, `P3`

All field values are normalized into `[0, P)`.

## Fixed-Point Encoding

Each floating-point parameter is encoded as:

```text
encoded = round(value * SCALE) mod P
```

The scaled integer must fit in the signed interval:

```text
[-(P - 1) // 2, (P - 1) // 2]
```

Values outside this interval are rejected to avoid ambiguity when decoding.
`NaN`, positive infinity, and negative infinity are rejected.

Decoding first normalizes the field element. Values in the upper half of the
field are interpreted as negative signed integers:

```text
signed = value - P if value > (P - 1) // 2 else value
decoded = signed / SCALE
```

## Additive Secret Sharing

For one encoded secret `x`, the splitter samples two random shares and derives
the final share:

```text
s1 = secrets.randbelow(P)
s2 = secrets.randbelow(P)
s3 = (x - s1 - s2) mod P
```

The invariant is:

```text
x = (s1 + s2 + s3) mod P
```

Vector sharing applies this process independently to each element and returns
one vector per party:

```text
[
  share_for_p1,
  share_for_p2,
  share_for_p3,
]
```

Reconstruction sums corresponding shares modulo `P`.

## Demonstration

```python
from secure_agg.crypto.fixed_point import decode_vector, encode_vector
from secure_agg.crypto.secret_sharing import reconstruct_vector, split_vector

values = [1.25, -2.5, 3.75]

encoded = encode_vector(values)
shares = split_vector(encoded)
reconstructed = reconstruct_vector(shares)
decoded = decode_vector(reconstructed)

print(decoded)
```

Expected output:

```text
[1.25, -2.5, 3.75]
```
