import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / ".claude" / "scripts"))


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test so os.chdir() calls don't leak."""
    original = os.getcwd()
    yield
    os.chdir(original)
