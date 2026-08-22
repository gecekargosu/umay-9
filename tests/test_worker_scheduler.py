"""Tests for BackgroundWorker, EventBus, Scheduler."""
from core.worker import BackgroundWorker, EventBus, Event
from core.scheduler import Scheduler, ScheduledTask


class TestEventBus:
    def test_emit_and_receive(self):
        bus = EventBus()
        received = []
        bus.on("test", lambda e: received.append(e))
        bus.emit(Event("test", {"key": "value"}))
        assert len(received) == 1
        assert received[0].data["key"] == "value"

    def test_wildcard(self):
        bus = EventBus()
        received = []
        bus.on("*", lambda e: received.append(e))
        bus.emit(Event("a"))
        bus.emit(Event("b"))
        assert len(received) == 2

    def test_history(self):
        bus = EventBus()
        bus.emit(Event("a"))
        bus.emit(Event("b"))
        assert len(bus.get_history("a")) == 1
        assert len(bus.get_history()) == 2


class TestBackgroundWorker:
    def test_register(self):
        w = BackgroundWorker()
        w.register_task("t", lambda: None, interval_seconds=60)
        assert "t" in w.get_status()["tasks"]

    def test_run_now(self):
        counter = {"n": 0}
        w = BackgroundWorker()
        w.register_task("inc", lambda: counter.__setitem__("n", counter["n"] + 1))
        w.run_task_now("inc")
        assert counter["n"] == 1

    def test_event(self):
        w = BackgroundWorker()
        events = []
        w.event_bus.on("task_completed", lambda e: events.append(e))
        w.register_task("ok", lambda: None)
        w.run_task_now("ok")
        assert len(events) == 1


class TestScheduledTask:
    def test_to_dict(self):
        t = ScheduledTask("t1", "Test", "noop", interval_seconds=60)
        d = t.to_dict()
        assert d["task_id"] == "t1"
        assert d["interval_seconds"] == 60

    def test_from_dict(self):
        d = {"task_id": "t1", "name": "Test", "func_name": "noop",
             "interval_seconds": 60, "enabled": True, "one_time": False,
             "run_count": 0, "error_count": 0}
        t = ScheduledTask.from_dict(d)
        assert t.task_id == "t1"
        assert t.interval_seconds == 60
