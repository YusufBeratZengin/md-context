import shutil
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]


@contextmanager
def temporary_directory():
    # Keep all test writes inside the checkout, including in restricted sandboxes.
    directory = PROJECT / "is" / "test-tmp"
    directory = directory / uuid4().hex
    # Normal inherited directory permissions also work with Windows restricted
    # tokens; Python 3.13+ mkdtemp's owner-only ACL does not inherit those grants.
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)
