# Testing

Run all tests:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest
```

In restricted sandboxes that forbid local sockets, HTTP integration tests are
skipped automatically. In a normal local environment they exercise real
loopback HTTP services.

Run only HTTP integration tests:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/integration/test_http_communication.py
```

Run the end-to-end demo:

```bash
python scripts/start_all.py
python scripts/run_demo.py
python scripts/stop_all.py
```

Expected demo result:

```text
Secure sum:     [6.0, 12.0, 18.0]
Secure average: [2.0, 4.0, 6.0]
Plain average:  [2.0, 4.0, 6.0]
Maximum error:  0.000000
Result: PASS
```

Covered cases include:

- finite-field arithmetic and fixed-point encoding;
- vector secret sharing and reconstruction;
- plaintext sum and average baselines;
- secure aggregation matching the plaintext baseline within `1e-5`;
- round-state duplicate, unknown participant, wrong length, and completed-state rejection;
- message digest validation;
- HTTP round creation, share distribution, local aggregation, aggregate-share submission, and result query.

Common failures:

- `service is not reachable`: run `python scripts/start_all.py` first.
- `address already in use`: run `python scripts/stop_all.py`, or stop the process using ports 8000, 8101, 8102, or 8103.
- `digest does not match payload`: the payload was changed after digest calculation; recompute it with `compute_payload_digest`.
