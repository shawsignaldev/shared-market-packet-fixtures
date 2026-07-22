# Architecture

## Contract

`MarketPacket` is the canonical public event shape:

- `venue`
- `channel`
- `message_type`
- `symbol`
- `sequence`
- `timestamp_ns`
- `price`
- `size`
- `side`
- `flags`

The fields are intentionally small enough for software tests, Verilog fixture generation, replay systems, and market simulation examples.

## Data Flow

1. A packet fixture is created or loaded from CSV.
2. `validate_packet` checks public-safe contract rules.
3. `sequence_report` identifies gaps, replayed sequence numbers, and out-of-order arrivals.
4. `project_top_of_book` replays quote and trade events into a minimal top-of-book state.
5. `packet_fingerprint` gives stable fixture identity for cross-repository references.

## Integration Targets

- FPGA feed handlers can use the rows as parser test vectors.
- Tickerplant and replay repos can use the sequence report to validate state transitions.
- Market simulation repos can use the same packet rows as deterministic exchange events.
- Schema contract repos can reuse the field contract for validation examples.

## Limitations

The fixture contract is intentionally compact. It is not a full exchange protocol, not a substitute for proprietary feeds, and not a latency measurement artifact. It is a shared test contract for public research repositories.

