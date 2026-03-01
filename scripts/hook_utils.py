import json
import sys


def parse_hook_input(raw: str) -> dict:
    return json.loads(raw)


def read_stdin() -> dict:
    return parse_hook_input(sys.stdin.read())
