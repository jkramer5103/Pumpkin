"""Strict, dependency-free validation of the shared version 1 interfaces."""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path


class SchemaError(ValueError):
    pass


def _fail(location: str, message: str) -> None:
    raise SchemaError(f"{location}: {message}")


def _object(value, location, required, optional=()):
    if not isinstance(value, dict):
        _fail(location, "must be an object")
    if any(not isinstance(key, str) for key in value):
        _fail(location, "object keys must be strings")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing:
        _fail(location, "missing fields: " + ", ".join(sorted(missing)))
    if extra:
        _fail(location, "unknown fields: " + ", ".join(sorted(extra)))


def _string(value, location, *, nonempty=True):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        _fail(location, "must be a nonempty string" if nonempty else "must be a string")
    if "\x00" in value:
        _fail(location, "NUL is not allowed")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _fail(location, "must contain valid UTF-8 text")


def _command(value, location):
    _string(value, location)
    if "\n" in value or "\r" in value:
        _fail(location, "commands must occupy one line")
    if len(value.encode("utf-8")) > 65536:
        _fail(location, "command exceeds 65536 bytes")


def _version(value, location):
    if type(value) is not int or value != 1:
        _fail(location, "only schema_version 1 is supported")


def validate_scenario(value: dict, location="scenario") -> dict:
    _object(value, location,
            ("schema_version", "id", "title", "category", "description", "tags", "setup", "steps", "cleanup"),
            ("notes",))
    _version(value["schema_version"], location)
    if not isinstance(value["id"], str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value["id"]):
        _fail(location + ".id", "must be lowercase and hyphenated")
    for field in ("title", "category", "description"):
        _string(value[field], location + "." + field)
    if "notes" in value:
        _string(value["notes"], location + ".notes", nonempty=False)
    tags = value["tags"]
    if not isinstance(tags, list):
        _fail(location + ".tags", "must be an array")
    for tag in tags:
        _string(tag, location + ".tags[]")
    if len(set(tags)) != len(tags):
        _fail(location + ".tags", "duplicate tags")
    for field in ("setup", "cleanup"):
        if not isinstance(value[field], list):
            _fail(location + "." + field, "must be an array")
        for index, command in enumerate(value[field]):
            _command(command, f"{location}.{field}[{index}]")
    if not isinstance(value["steps"], list) or not value["steps"]:
        _fail(location + ".steps", "must be a nonempty array")
    positive = False
    for index, step in enumerate(value["steps"]):
        loc = f"{location}.steps[{index}]"
        _object(step, loc, ("command",), ("observe", "expect_contains", "wait_ticks"))
        _command(step["command"], loc + ".command")
        if type(step.get("observe", False)) is not bool:
            _fail(loc + ".observe", "must be a boolean")
        ticks = step.get("wait_ticks", 0)
        if type(ticks) is not int or ticks < 0:
            _fail(loc + ".wait_ticks", "must be a nonnegative integer")
        if "expect_contains" in step:
            _string(step["expect_contains"], loc + ".expect_contains")
            if not step.get("observe", False):
                _fail(loc, "expect_contains requires observe=true")
            positive = True
    if not positive:
        _fail(location, "needs an observed step with a nonempty positive expect_contains")
    return value


def validate_targets(value: dict, location="targets") -> dict:
    _object(value, location, ("schema_version", "minecraft_version", "targets"))
    _version(value["schema_version"], location)
    _string(value["minecraft_version"], location + ".minecraft_version")
    _object(value["targets"], location + ".targets", ("vanilla", "pumpkin"))
    endpoints = []
    for name, target in value["targets"].items():
        loc = location + ".targets." + name
        _object(target, loc, ("host", "port", "password"))
        _string(target["host"], loc + ".host")
        # Literal loopback addresses prevent DNS rebinding or accidental public RCON.
        try:
            loopback = ipaddress.ip_address(target["host"]).is_loopback
        except ValueError:
            loopback = target["host"] == "localhost"
        if not loopback:
            _fail(loc + ".host", "must be a loopback address or localhost")
        if type(target["port"]) is not int or not 1 <= target["port"] <= 65535:
            _fail(loc + ".port", "must be an integer from 1 to 65535")
        _string(target["password"], loc + ".password")
        if "\n" in target["password"] or "\r" in target["password"]:
            _fail(loc + ".password", "must occupy one line")
        canonical_host = "127.0.0.1" if target["host"] == "localhost" else str(ipaddress.ip_address(target["host"]))
        endpoints.append((canonical_host, target["port"]))
    if endpoints[0] == endpoints[1]:
        _fail(location, "vanilla and pumpkin must use distinct endpoints")
    return value


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SchemaError("JSON object contains duplicate keys")
        value[key] = item
    return value


def read_json(path: str | Path) -> dict:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_unique_pairs,
                              parse_constant=lambda _: _fail("JSON", "non-finite number"))
        if not isinstance(value, dict):
            _fail("JSON", "root must be an object")
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # Do not echo JSON lines: targets files contain credentials.
        raise SchemaError(f"{path}: cannot read valid JSON ({type(exc).__name__})") from exc


def load_targets(path: str | Path) -> dict:
    return validate_targets(read_json(path), str(path))


def load_scenarios(directory: str | Path, scenario_id: str | list[str] | None = None) -> list[dict]:
    directory = Path(directory)
    if not directory.is_dir():
        raise SchemaError(f"{directory}: scenario directory does not exist")
    found = []
    ids = set()
    selected = None if scenario_id is None else set([scenario_id] if isinstance(scenario_id, str) else scenario_id)
    for path in sorted(directory.glob("*.json")):
        value = validate_scenario(read_json(path), str(path))
        if value["id"] in ids:
            raise SchemaError(f"{path}: duplicate scenario id {value['id']}")
        ids.add(value["id"])
        if selected is None or value["id"] in selected:
            found.append(value)
    if selected is not None and selected - ids:
        raise SchemaError(f"{directory}: no scenarios matching " + ", ".join(sorted(selected - ids)))
    if not found:
        raise SchemaError(f"{directory}: no scenarios")
    return sorted(found, key=lambda scenario: scenario["id"])
