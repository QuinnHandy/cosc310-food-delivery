"""The shared JSON storage used by the repositories (#108)."""

import json
import os

import pytest
from pydantic import BaseModel

from app.repositories import json_store
from app.repositories.json_store import DataAccessError, JsonStore, next_id, write_json_atomic


class Thing(BaseModel):
    id: int
    name: str


def store(tmp_path, **kwargs):
    return JsonStore(tmp_path / "things.json", Thing, "thing", **kwargs)


def test_save_then_load_round_trip(tmp_path):
    s = store(tmp_path)
    s.save([Thing(id=1, name="a"), Thing(id=2, name="b")])
    assert store(tmp_path).load() == [Thing(id=1, name="a"), Thing(id=2, name="b")]


def test_ids_stay_stable_after_reload_and_are_not_reused(tmp_path):
    s = store(tmp_path)
    things = [Thing(id=1, name="a"), Thing(id=2, name="b")]
    s.save(things)
    s.save([t for t in things if t.id != 2])  # remove the newest
    reloaded = store(tmp_path).load()
    assert [t.id for t in reloaded] == [1]
    assert next_id([Thing(id=1, name="a"), Thing(id=5, name="e")]) == 6
    assert next_id([]) == 1


def test_failed_serialization_leaves_the_old_file_intact(tmp_path):
    path = tmp_path / "things.json"
    write_json_atomic(path, [{"id": 1, "name": "kept"}])
    before = path.read_bytes()
    with pytest.raises(DataAccessError):
        write_json_atomic(path, [{"id": 2, "name": object()}])  # not JSON-serializable
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []  # no temp file left behind


def test_failed_swap_leaves_old_file_and_removes_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "things.json"
    write_json_atomic(path, [{"id": 1, "name": "kept"}])
    before = path.read_bytes()

    def broken_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(json_store.os, "replace", broken_replace)
    with pytest.raises(DataAccessError):
        write_json_atomic(path, [{"id": 2, "name": "new"}])
    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []


def test_missing_file_is_an_error_unless_missing_ok(tmp_path):
    with pytest.raises(DataAccessError):
        store(tmp_path).load()
    assert store(tmp_path, missing_ok=True).load() == []


@pytest.mark.parametrize(
    "content, message",
    [
        ("{not json", "Thing data file is not valid JSON"),
        (json.dumps({"id": 1}), "Thing data file must contain a JSON list"),
        (json.dumps([{"id": "x", "name": "a"}]), "Thing record does not match the Thing model"),
    ],
)
def test_invalid_files_raise_data_access_error(tmp_path, content, message):
    (tmp_path / "things.json").write_text(content)
    with pytest.raises(DataAccessError, match=message):
        store(tmp_path).load()


def test_duplicate_ids_are_reported(tmp_path):
    s = store(tmp_path)
    with pytest.raises(DataAccessError, match="duplicate IDs"):
        s.require_unique_ids([Thing(id=1, name="a"), Thing(id=1, name="b")])


def test_custom_dump_controls_what_is_written(tmp_path):
    s = store(tmp_path, dump=lambda t: {"name": t.name, "id": t.id})
    s.save([Thing(id=1, name="a")])
    assert list(json.loads((tmp_path / "things.json").read_text())[0]) == ["name", "id"]


def test_unreadable_file_is_a_data_access_error(tmp_path):
    (tmp_path / "things.json").mkdir()  # a folder where the file should be
    with pytest.raises(DataAccessError):
        store(tmp_path).load()


@pytest.mark.parametrize(
    "module",
    ["restaurant_repository", "menu_repository", "cart_repository", "session_repository"],
)
def test_repositories_use_the_shared_store(module):
    source = (json_store.__file__.replace("json_store.py", f"{module}.py"))
    text = open(source, encoding="utf-8").read()
    assert "JsonStore(" in text
    assert "json.loads" not in text and "tempfile" not in text  # no copied load/save code left


def test_old_import_paths_still_work():
    from app.repositories.restaurant_repository import DataAccessError as OldError
    from app.repositories.restaurant_repository import write_json_atomic as old_write

    assert OldError is DataAccessError
    assert old_write is write_json_atomic
    assert os.path.exists(json_store.__file__)
