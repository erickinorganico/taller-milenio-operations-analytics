"""Check pinned runtime packages locally without starting pip or using the network."""
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def ready(requirements):
    for line in Path(requirements).read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([^#\s=]+)==([^\s#]+)", line)
        if match:
            try:
                if version(match[1]) != match[2]:
                    return False
            except PackageNotFoundError:
                return False
    return True


if __name__ == "__main__":
    sys.exit(0 if ready(sys.argv[1]) else 1)
