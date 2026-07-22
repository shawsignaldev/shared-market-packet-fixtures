from shared_market_packet_fixtures import (
    MarketPacket,
    csv_round_trip,
    packet_fingerprint,
    project_top_of_book,
    sample_packets,
    sequence_report,
    validate_packet,
)


def test_sample_packets_are_public_safe_and_deterministic() -> None:
    packets = sample_packets()

    assert [packet.sequence for packet in packets] == [1, 2, 3, 4, 5, 6]
    assert {packet.symbol for packet in packets} == {"NVDA", "SPY"}
    assert all(packet.venue == "SIM" for packet in packets)
    assert all(packet.timestamp_ns > 0 for packet in packets)
    assert all(packet.side in {"B", "A", "T"} for packet in packets)

    fingerprints = [packet_fingerprint(packet) for packet in packets]
    assert fingerprints == [packet_fingerprint(packet) for packet in sample_packets()]
    assert len(set(fingerprints)) == len(fingerprints)
    assert not any("key" in field.lower() or "account" in field.lower() for field in packets[0].to_row())


def test_validate_packet_reports_contract_violations() -> None:
    bad = MarketPacket(
        venue="",
        channel="ITCH-A",
        message_type="quote",
        symbol="nvda",
        sequence=0,
        timestamp_ns=-1,
        price=-100.0,
        size=0,
        side="X",
        flags=("private",),
    )

    errors = validate_packet(bad)

    assert "venue is required" in errors
    assert "message_type must be uppercase" in errors
    assert "symbol must be uppercase alphanumeric" in errors
    assert "sequence must be positive" in errors
    assert "timestamp_ns must be positive" in errors
    assert "price must be positive" in errors
    assert "size must be positive" in errors
    assert "side must be B, A, or T" in errors
    assert "flags cannot contain sensitive labels" in errors


def test_sequence_report_detects_gaps_replays_and_out_of_order_packets() -> None:
    packets = [
        MarketPacket("SIM", "ITCH-A", "QUOTE", "NVDA", 1, 100, 100.0, 10, "B"),
        MarketPacket("SIM", "ITCH-A", "QUOTE", "NVDA", 3, 110, 100.5, 10, "A"),
        MarketPacket("SIM", "ITCH-A", "TRADE", "NVDA", 3, 120, 100.25, 5, "T"),
        MarketPacket("SIM", "ITCH-A", "QUOTE", "NVDA", 2, 130, 100.1, 8, "B"),
    ]

    report = sequence_report(packets)

    assert report.expected_count == 4
    assert report.gaps == [(2, 2)]
    assert report.replays == [3]
    assert report.out_of_order == [(3, 2)]
    assert report.is_clean is False


def test_csv_round_trip_preserves_packets_and_rows_are_stable() -> None:
    packets = sample_packets()

    text, restored = csv_round_trip(packets)

    assert text.splitlines()[0] == "venue,channel,message_type,symbol,sequence,timestamp_ns,price,size,side,flags"
    assert restored == packets
    assert csv_round_trip(restored)[0] == text


def test_project_top_of_book_replays_quotes_and_trades() -> None:
    book = project_top_of_book(sample_packets())

    assert book["NVDA"].best_bid == 875.25
    assert book["NVDA"].best_ask == 875.75
    assert book["NVDA"].last_trade == 875.5
    assert book["SPY"].best_bid == 621.1
    assert book["SPY"].best_ask is None
    assert book["SPY"].last_trade == 621.3
