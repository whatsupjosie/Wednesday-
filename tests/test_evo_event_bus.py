from modules.evo.event_bus import EventBus
from modules.evo.semantic_events import EventEnvelope


def test_event_bus_routes_exact_and_wildcard_subscribers_in_order():
    bus = EventBus()
    seen = []

    bus.subscribe("semantic.updated", lambda event: seen.append(("exact", event.event_id)))
    bus.subscribe("*", lambda event: seen.append(("wildcard", event.event_id)))

    event = EventEnvelope(
        source="runtime",
        role="system",
        event_type="semantic.updated",
        payload={"revision": 1},
    )
    result = bus.publish(event)

    assert result.delivered == 2
    assert result.failures == ()
    assert seen == [("exact", event.event_id), ("wildcard", event.event_id)]


def test_event_bus_suppresses_duplicate_event_identity():
    bus = EventBus()
    delivered = []
    bus.subscribe("tick", lambda event: delivered.append(event.event_id))

    event = EventEnvelope(source="runtime", role="system", event_type="tick")
    first = bus.publish(event)
    second = bus.publish(event)

    assert first.delivered == 1
    assert second.duplicate is True
    assert second.delivered == 0
    assert delivered == [event.event_id]


def test_event_bus_isolates_handler_failures_by_default():
    bus = EventBus()
    delivered = []

    def broken(_event):
        raise ValueError("boom")

    bus.subscribe("tick", broken)
    bus.subscribe("tick", lambda event: delivered.append(event.event_id))

    event = EventEnvelope(source="runtime", role="system", event_type="tick")
    result = bus.publish(event)

    assert result.delivered == 1
    assert len(result.failures) == 1
    assert result.failures[0].error_type == "ValueError"
    assert delivered == [event.event_id]


def test_event_envelope_children_preserve_correlation_and_bound_hops():
    root = EventEnvelope(
        source="director",
        role="director",
        event_type="scene.intent",
        max_hops=2,
    )
    child = root.child(
        source="producer",
        role="producer",
        event_type="scene.accepted",
    )
    grandchild = child.child(
        source="runtime",
        role="system",
        event_type="scene.committed",
    )

    assert child.parent_id == root.event_id
    assert child.correlation_id == root.correlation_id
    assert grandchild.hop == 2
    assert grandchild.can_forward is False

    try:
        grandchild.child(source="runtime", role="system", event_type="overflow")
    except RuntimeError as exc:
        assert "hop budget" in str(exc)
    else:
        raise AssertionError("expected hop budget exhaustion")
