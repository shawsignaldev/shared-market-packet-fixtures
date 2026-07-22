# Shared Market Packet Fixtures

Public-safe market packet fixtures shared across FPGA, replay, tickerplant, and market simulation research repositories.

## What This Proves

- A canonical packet contract for sanitized market-data tests.
- Deterministic CSV fixtures that can be replayed by software and hardware-facing models.
- Sequence-gap, replay, and out-of-order detection.
- Top-of-book projection from quote and trade packets.
- Fingerprints for stable fixture identity across repositories.

## Why It Matters

The flagship portfolio includes FPGA feed handlers, tickerplants, replay engines, exchange simulators, and schema validators. Those systems should not each invent a different event shape. This repository gives them a common public fixture layer so reviewers can trace one event contract through parsing, replay, risk checks, and simulation.

## Run

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Example

```python
from shared_market_packet_fixtures import project_top_of_book, sample_packets, sequence_report

packets = sample_packets()
print(sequence_report(packets).is_clean)
print(project_top_of_book(packets)["NVDA"])
```

## Review Path

- `src/shared_market_packet_fixtures/__init__.py` contains the packet model, validator, CSV round trip, sequence report, fingerprinting, and replay projection.
- `tests/test_packets.py` documents the expected behavior.
- `.github/workflows/ci.yml` runs the public test suite.

## Boundary

This is public research infrastructure. It does not contain private credentials, brokerage integration, account data, proprietary market data, trading-performance promises, or unverified hardware timing claims.

