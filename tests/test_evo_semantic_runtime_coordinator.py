from modules.evo.event_bus import EventBus
from modules.evo.mutation import StateMutationRequest
from modules.evo.semantic_runtime import SemanticRuntime


def test_runtime_commits_one_revision_and_emits_changed_paths():
    bus = EventBus()
    events = []
    bus.subscribe("semantic.updated", events.append)
    runtime = SemanticRuntime(event_bus=bus)

    commit = runtime.apply(
        [
            StateMutationRequest(
                source="vdi_engine",
                role="system",
                path="audience.engagement",
                value=0.8,
                priority=50,
            ),
            StateMutationRequest(
                source="director",
                role="director",
                path="scene.pacing",
                value=0.7,
                priority=20,
            ),
        ]
    )

    assert commit.changed is True
    assert commit.state.revision == 1
    assert commit.changed_paths == ("audience.engagement", "scene.pacing")
    assert commit.dispatch is not None
    assert commit.dispatch.delivered == 1
    assert len(events) == 1
    assert events[0].payload["revision"] == 1
    assert events[0].payload["changed_paths"] == commit.changed_paths


def test_runtime_does_not_commit_or_emit_for_noop_batch():
    bus = EventBus()
    events = []
    bus.subscribe("semantic.updated", events.append)
    runtime = SemanticRuntime(event_bus=bus)

    commit = runtime.apply(
        [
            StateMutationRequest(
                source="jeremy",
                role="observer",
                path="scene.tension",
                value=0.9,
                priority=100,
            )
        ]
    )

    assert commit.changed is False
    assert commit.state.revision == 0
    assert commit.dispatch is None
    assert events == []
