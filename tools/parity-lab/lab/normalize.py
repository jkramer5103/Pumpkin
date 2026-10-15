"""Narrow semantic normalization; evidence always retains the original string.

Only recognized console sender wrappers at the start of a line are removed: [Rcon], [Server],
[RCON], and the optional [Not Secure] wrapper. Coordinate values, UUIDs, counts,
whitespace, ordering, case, localization and all other output remain significant.
This applies to chat and command feedback, including terminal execute probes.
No general square-bracket, timestamp, UUID or whitespace removal is performed.
"""

import re

_SENDER = re.compile(r"^(?:\[Not Secure\] )?\[(?:Rcon|RCON|Server)\] ")


def strip_sender(line: str) -> str:
    return _SENDER.sub("", line, count=1)


def normalize_response(raw: str, command: str = "") -> str:
    return "".join(strip_sender(line) for line in raw.splitlines(keepends=True))


_UNSUPPORTED = re.compile(
    r"^(?:Unknown (?:or incomplete )?command|Unknown command at|"
    r"Command (?:not found|not implemented)|(?:This )?[Cc]ommand .*(?:not supported|not implemented)|"
    r"(?:Unsupported|Unimplemented) command|.*<--\[HERE\])", re.IGNORECASE)
_FAILED = re.compile(
    r"^(?:Incorrect argument|Invalid argument|Expected |Test failed(?:\b|,)|"
    r"Failed to |Could not |Cannot |Can't |An unexpected error occurred|"
    r"An unknown error occurred|You do not have permission|"
    r"No (?:entity|entities|player|players|blocks) (?:was |were )?found)", re.IGNORECASE)
_ENVIRONMENT = re.compile(
    r"^(?:(?:That|The) position is not loaded|(?:Some|The specified) chunks? (?:is|are) not loaded|"
    r"Cannot access blocks outside of the world|An (?:unexpected|unknown) error occurred)", re.IGNORECASE)


def command_problem(raw: str) -> str | None:
    lines = [strip_sender(line) for line in raw.splitlines()]
    if any(_ENVIRONMENT.search(line) for line in lines):
        return "environment_error"
    if any(_UNSUPPORTED.search(line) for line in lines):
        return "unsupported"
    if any(_FAILED.search(line) for line in lines):
        return "command_failed"
    return None
