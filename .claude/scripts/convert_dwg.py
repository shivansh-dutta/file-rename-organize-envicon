# ============================================================
# CONFIGURATION — update ODA_EXE to match your installation
# ============================================================
ODA_EXE = r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
# ============================================================

import shutil
import subprocess
import sys
from pathlib import Path


def _run_oda(dwg_path: Path, tmp_in: Path, tmp_out: Path) -> Path:
    """Copy DWG to tmp_in, run ODA converter, return path to output DXF."""
    shutil.copy2(dwg_path, tmp_in / dwg_path.name)
    result = subprocess.run(
        [ODA_EXE, str(tmp_in), str(tmp_out), "ACAD2018", "DXF", "0", "1"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ODA failed: {result.stderr}")
    dxf = tmp_out / (dwg_path.stem + ".dxf")
    if not dxf.exists():
        raise RuntimeError(f"ODA did not produce {dxf.name}")
    return dxf


def _render_dxf_to_png(dxf_path: Path, png_path: Path) -> None:
    """Render a DXF file to PNG using ezdxf + matplotlib."""
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend, safe on headless systems
    import matplotlib.pyplot as plt

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)
    fig.savefig(str(png_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def convert_dwg_to_png(dwg_path: str, png_path: str) -> None:
    """Convert a DWG file to PNG. Raises RuntimeError on failure."""
    dwg = Path(dwg_path)
    png = Path(png_path)
    tmp_in = Path(".claude/tmp/input")
    tmp_out = Path(".claude/tmp/output")
    tmp_in.mkdir(parents=True, exist_ok=True)
    tmp_out.mkdir(parents=True, exist_ok=True)

    dxf = None
    try:
        dxf = _run_oda(dwg, tmp_in, tmp_out)
        _render_dxf_to_png(dxf, png)
    finally:
        (tmp_in / dwg.name).unlink(missing_ok=True)
        if dxf and dxf.exists():
            dxf.unlink()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_dwg.py <dwg_path> <png_output_path>", file=sys.stderr)
        sys.exit(1)
    try:
        convert_dwg_to_png(sys.argv[1], sys.argv[2])
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
