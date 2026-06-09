import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def fake_dwg(tmp_path):
    dwg = tmp_path / "FILE000.dwg"
    dwg.write_bytes(b"fake dwg content")
    return dwg


def test_oda_called_with_correct_arguments(fake_dwg, tmp_path):
    """ODA is invoked with tmp_in, tmp_out, ACAD2018, DXF."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()
    # Pre-create the expected DXF so the existence check passes
    (tmp_out / "FILE000.dxf").write_bytes(b"")

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _run_oda(fake_dwg, tmp_in, tmp_out)

        args = mock_run.call_args[0][0]
        assert str(tmp_in) in args
        assert str(tmp_out) in args
        assert "DXF" in args
        assert "ACAD2018" in args


def test_oda_nonzero_exit_raises(fake_dwg, tmp_path):
    """RuntimeError is raised when ODA exits non-zero."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=1, stderr="ODA exploded")

        with pytest.raises(RuntimeError, match="ODA failed"):
            _run_oda(fake_dwg, tmp_in, tmp_out)


def test_missing_output_dxf_raises(fake_dwg, tmp_path):
    """RuntimeError is raised when ODA exits 0 but produces no DXF."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()
    # Do NOT create the DXF file

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with pytest.raises(RuntimeError, match="did not produce"):
            _run_oda(fake_dwg, tmp_in, tmp_out)
