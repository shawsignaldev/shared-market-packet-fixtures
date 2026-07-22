from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from io import StringIO
from typing import Iterable


SENSITIVE_FLAG_TERMS = ("account", "api", "broker", "credential", "key", "private", "secret")


@dataclass(frozen=True)
class MarketPacket:
    venue: str
    channel: str
    message_type: str
    symbol: str
    sequence: int
    timestamp_ns: int
    price: float
    size: int
    side: str
    flags: tuple[str, ...] = ()

    def to_row(self) -> dict[str, str]:
        return {
            "venue": self.venue,
            "channel": self.channel,
            "message_type": self.message_type,
            "symbol": self.symbol,
            "sequence": str(self.sequence),
            "timestamp_ns": str(self.timestamp_ns),
            "price": f"{self.price:.6f}".rstrip("0").rstrip("."),
            "size": str(self.size),
            "side": self.side,
            "flags": "|".join(self.flags),
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "MarketPacket":
        flags = tuple(flag for flag in row.get("flags", "").split("|") if flag)
        return cls(
            venue=row["venue"],
            channel=row["channel"],
            message_type=row["message_type"],
            symbol=row["symbol"],
            sequence=int(row["sequence"]),
            timestamp_ns=int(row["timestamp_ns"]),
            price=float(row["price"]),
            size=int(row["size"]),
            side=row["side"],
            flags=flags,
        )


@dataclass(frozen=True)
class SequenceReport:
    expected_count: int
    gaps: list[tuple[int, int]]
    replays: list[int]
    out_of_order: list[tuple[int, int]]

    @property
    def is_clean(self) -> bool:
        return not self.gaps and not self.replays and not self.out_of_order


@dataclass(frozen=True)
class TopOfBook:
    best_bid: float | None = None
    best_ask: float | None = None
    last_trade: float | None = None


def validate_packet(packet: MarketPacket) -> list[str]:
    errors: list[str] = []
    if not packet.venue:
        errors.append("venue is required")
    if not packet.channel:
        errors.append("channel is required")
    if packet.message_type != packet.message_type.upper():
        errors.append("message_type must be uppercase")
    if not packet.symbol.isalnum() or packet.symbol != packet.symbol.upper():
        errors.append("symbol must be uppercase alphanumeric")
    if packet.sequence <= 0:
        errors.append("sequence must be positive")
    if packet.timestamp_ns <= 0:
        errors.append("timestamp_ns must be positive")
    if packet.price <= 0:
        errors.append("price must be positive")
    if packet.size <= 0:
        errors.append("size must be positive")
    if packet.side not in {"B", "A", "T"}:
        errors.append("side must be B, A, or T")
    if any(term in flag.lower() for flag in packet.flags for term in SENSITIVE_FLAG_TERMS):
        errors.append("flags cannot contain sensitive labels")
    return errors


def packet_fingerprint(packet: MarketPacket) -> str:
    encoded = json.dumps(packet.to_row(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def sample_packets() -> list[MarketPacket]:
    return [
        MarketPacket("SIM", "ITCH-A", "QUOTE", "NVDA", 1, 1_000_000_000, 875.25, 100, "B", ("open-drive",)),
        MarketPacket("SIM", "ITCH-A", "QUOTE", "NVDA", 2, 1_000_000_250, 875.75, 90, "A", ("open-drive",)),
        MarketPacket("SIM", "ITCH-A", "TRADE", "NVDA", 3, 1_000_000_500, 875.5, 25, "T", ("print",)),
        MarketPacket("SIM", "ITCH-B", "QUOTE", "SPY", 4, 1_000_001_000, 621.1, 200, "B", ("liquid-index",)),
        MarketPacket("SIM", "ITCH-B", "TRADE", "SPY", 5, 1_000_001_250, 621.3, 50, "T", ("print",)),
        MarketPacket("SIM", "ITCH-B", "TRADE", "SPY", 6, 1_000_001_500, 621.3, 10, "T", ("closing-fixture",)),
    ]


def sequence_report(packets: Iterable[MarketPacket]) -> SequenceReport:
    seen: set[int] = set()
    gaps: list[tuple[int, int]] = []
    replays: list[int] = []
    out_of_order: list[tuple[int, int]] = []
    last_sequence: int | None = None
    count = 0

    for packet in packets:
        count += 1
        if packet.sequence in seen:
            replays.append(packet.sequence)
        if last_sequence is not None and packet.sequence < last_sequence:
            out_of_order.append((last_sequence, packet.sequence))
        if last_sequence is not None and packet.sequence > last_sequence + 1:
            gaps.append((last_sequence + 1, packet.sequence - 1))
        seen.add(packet.sequence)
        last_sequence = packet.sequence

    return SequenceReport(expected_count=count, gaps=gaps, replays=replays, out_of_order=out_of_order)


def csv_round_trip(packets: Iterable[MarketPacket]) -> tuple[str, list[MarketPacket]]:
    rows = [packet.to_row() for packet in packets]
    columns = ["venue", "channel", "message_type", "symbol", "sequence", "timestamp_ns", "price", "size", "side", "flags"]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    text = output.getvalue()
    restored = [MarketPacket.from_row(row) for row in csv.DictReader(StringIO(text))]
    return text, restored


def project_top_of_book(packets: Iterable[MarketPacket]) -> dict[str, TopOfBook]:
    mutable: dict[str, dict[str, float | None]] = {}
    for packet in packets:
        state = mutable.setdefault(packet.symbol, {"best_bid": None, "best_ask": None, "last_trade": None})
        if packet.side == "B":
            state["best_bid"] = packet.price
        elif packet.side == "A":
            state["best_ask"] = packet.price
        elif packet.side == "T":
            state["last_trade"] = packet.price
    return {symbol: TopOfBook(**state) for symbol, state in mutable.items()}
