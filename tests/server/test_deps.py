from pathlib import Path

from atlas.server.deps import create_engine_set, EngineSet, EventBus


def test_create_engine_set(tmp_path):
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw/untracked", "raw/ingested"]:
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Wiki Index\n")

    engines = create_engine_set(tmp_path)
    assert isinstance(engines, EngineSet)
    assert engines.storage is not None
    assert engines.graph is not None
    assert engines.wiki is not None
    assert engines.linker is not None
    assert engines.analyzer is not None
    assert engines.scanner is not None
    assert engines.cache is not None
    assert engines.ingest is not None


def test_engine_set_graph_path(tmp_path):
    for d in ["wiki/projects", "wiki/concepts", "wiki/decisions", "wiki/sources", "raw"]:
        (tmp_path / d).mkdir(parents=True)
    engines = create_engine_set(tmp_path)
    assert engines.graph_path == tmp_path / "atlas-out" / "graph.json"


def test_event_bus_subscribe_and_emit():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("wiki.changed", handler)
    bus.emit("wiki.changed", {"page": "auth.md"})
    assert len(received) == 1
    assert received[0]["page"] == "auth.md"


def test_event_bus_multiple_subscribers():
    bus = EventBus()
    a_received = []
    b_received = []

    bus.subscribe("graph.updated", lambda e: a_received.append(e))
    bus.subscribe("graph.updated", lambda e: b_received.append(e))
    bus.emit("graph.updated", {"nodes": 42})
    assert len(a_received) == 1
    assert len(b_received) == 1


def test_event_bus_no_crosstalk():
    bus = EventBus()
    received = []

    bus.subscribe("wiki.changed", lambda e: received.append(e))
    bus.emit("graph.updated", {"nodes": 42})
    assert len(received) == 0


def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("wiki.changed", handler)
    bus.unsubscribe("wiki.changed", handler)
    bus.emit("wiki.changed", {"page": "auth.md"})
    assert len(received) == 0
