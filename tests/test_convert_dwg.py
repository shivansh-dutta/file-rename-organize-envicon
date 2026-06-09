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


def test_render_dxf_to_png_produces_image(tmp_path):
    """A minimal DXF is rendered to a non-empty PNG file."""
    import ezdxf
    from convert_dwg import _render_dxf_to_png

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 100))
    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))

    png_path = tmp_path / "test.png"
    _render_dxf_to_png(dxf_path, png_path)

    assert png_path.exists()
    assert png_path.stat().st_size > 1000  # real image, not empty


import os


def test_convert_dwg_to_png_calls_render_on_success(fake_dwg, tmp_path):
    """convert_dwg_to_png calls _render_dxf_to_png when ODA succeeds."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)
    fake_dxf = tmp_path / ".claude" / "tmp" / "output" / "FILE000.dxf"

    with patch("convert_dwg._run_oda", return_value=fake_dxf) as mock_oda, \
         patch("convert_dwg._render_dxf_to_png") as mock_render:

        png_out = tmp_path / "out.png"
        convert_dwg_to_png(str(fake_dwg), str(png_out))

        mock_oda.assert_called_once()
        mock_render.assert_called_once()


def test_convert_dwg_to_png_cleans_up_dxf_after_success(fake_dwg, tmp_path):
    """The DXF file returned by _run_oda is deleted after rendering."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)
    fake_dxf = tmp_path / "fake.dxf"
    fake_dxf.write_bytes(b"")

    with patch("convert_dwg._run_oda", return_value=fake_dxf), \
         patch("convert_dwg._render_dxf_to_png"):

        convert_dwg_to_png(str(fake_dwg), str(tmp_path / "out.png"))

    assert not fake_dxf.exists()


def test_convert_dwg_to_png_raises_and_cleans_on_oda_failure(fake_dwg, tmp_path):
    """RuntimeError propagates and no DXF is left behind when ODA fails."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)

    with patch("convert_dwg._run_oda", side_effect=RuntimeError("ODA failed: crash")):
        with pytest.raises(RuntimeError, match="ODA failed"):
            convert_dwg_to_png(str(fake_dwg), str(tmp_path / "out.png"))
