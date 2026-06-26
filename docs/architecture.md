# Architecture

The demo system runs four local HTTP services:

- Coordinator on `127.0.0.1:8000`
- Party P1 on `127.0.0.1:8101`
- Party P2 on `127.0.0.1:8102`
- Party P3 on `127.0.0.1:8103`

The coordinator creates rounds, tracks aggregate-share submissions, calls
`reconstruct_aggregation`, and stores the final sum and average. It does not
read participant parameter files.

Each party reads only its own parameter JSON file, calls member-one
`encode_vector` and `split_vector`, sends exactly one share vector to each
party, calls member-two `aggregate_received_shares` after all shares arrive,
and submits the local aggregate share to the coordinator.

## Data Flow

```text
party parameter file
  -> encode_vector
  -> split_vector
  -> POST /rounds/{round_id}/shares on each party
  -> aggregate_received_shares on each party
  -> POST /rounds/{round_id}/aggregate-shares on coordinator
  -> reconstruct_aggregation
  -> GET /rounds/{round_id}/result
```

HTTP messages contain finite-field share vectors only. They do not contain
plaintext model parameters. Logs include round IDs, party IDs, message type,
and vector length, but not full payloads.

## API Summary

Coordinator:

- `GET /health`
- `POST /rounds`
- `POST /rounds/{round_id}/aggregate-shares`
- `GET /rounds/{round_id}/result`

Party:

- `GET /health`
- `POST /rounds`
- `POST /rounds/{round_id}/distribute`
- `POST /rounds/{round_id}/shares`
- `POST /rounds/{round_id}/aggregate`
- `GET /rounds/{round_id}`

## Operational Notes

Run all services with:

```bash
python scripts/start_all.py
```

Then run:

```bash
python scripts/run_demo.py
```

Stop services with:

```bash
python scripts/stop_all.py
```

Service logs are written under `logs/` and should not contain plaintext
parameters or complete share payloads.
