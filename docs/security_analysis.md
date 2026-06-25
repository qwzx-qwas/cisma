# Security Analysis

This document covers the security assumptions and limitations of the
member-one cryptographic foundation.

## Security Assumptions

- The implementation is for teaching and experimentation, not production use.
- Parties follow the protocol and provide correctly shaped share vectors.
- Random shares are generated with `secrets.randbelow(P)`.
- A single additive share does not reveal the original secret by itself.
- Full reconstruction requires collecting all intended aggregate shares at the
  business protocol layer.

## Randomness

Secret splitting uses Python's `secrets` module:

```python
secrets.randbelow(PRIME)
```

The code does not use `random.randint` or `numpy.random` for share generation.
Repeated splitting of the same secret should produce different share sets with
overwhelming probability.

## Correctness Bounds

Fixed-point encoding rejects non-finite floats and values whose scaled integer
is outside:

```text
[-(P - 1) // 2, (P - 1) // 2]
```

This ensures that negative values can be decoded unambiguously from the finite
field representation.

## Known Limitations

- Additive sharing provides privacy against holders of fewer than all shares,
  but it does not provide authentication or malicious-party detection.
- The member-one module does not enforce network-level sender identity,
  duplicate-message prevention, timeout handling, or quorum rules.
- The module does not implement threshold reconstruction. It uses simple
  additive sharing, so the business layer must decide when reconstruction is
  allowed.
- Floating-point values are rounded to the nearest integer after scaling, so
  precision is limited to approximately `1 / SCALE`.
