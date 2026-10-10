from modules.evo.arbitration import ArbitrationEngine
from modules.evo.mutation import StateMutationRequest
from modules.evo.semantic_field import SemanticField, SemanticStore


def test_arbitration_prefers_priority_and_allows_one_write_per_path():
    engine = ArbitrationEngine()
    state = SemanticField()

    result = engine.resolve(
        state,
        [
            StateMutationRequest(
                source="performer-a",
                role="performer",
                path="emotion.intensity",
                value=0.4,
                priority=5,
                confidence=1.0,
            ),
            StateMutationRequest(
                source="anchor",
                role="anchor",
                path="emotion.intensity",
                value=0.2,
                priority=10,
                confidence=1.0,
            ),
        ],
    )

    assert result.emotion.intensity == 0.2


def test_observer_cannot_mutate_shared_state():
    engine = ArbitrationEngine()
    state = SemanticField()

    result = engine.resolve(
        state,
        [
            StateMutationRequest(
                source="jeremy",
                role="observer",
                path="scene.tension",
                value=0.9,
                priority=100,
                confidence=1.0,
            )
        ],
    )

    assert result == state


def test_semantic_values_are_normalized():
    engine = ArbitrationEngine()
    state = SemanticField()

    result = engine.resolve(
        state,
        [
            StateMutationRequest(
                source="director",
                role="director",
                path="scene.pacing",
                value=5.0,
            )
        ],
    )

    assert result.scene.pacing == 1.0


def test_store_uses_optimistic_revision_guard():
    store = SemanticStore()
    initial = store.read()
    committed = store.commit(initial, expected_revision=0)

    assert committed.revision == 1

    try:
        store.commit(initial, expected_revision=0)
    except RuntimeError as exc:
        assert "revision conflict" in str(exc)
    else:
        raise AssertionError("expected revision conflict")
