"""Safe run-scoped artifact archiving."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def zip_directory(root: Path) -> bytes:
    """Return a ZIP containing regular files below ``root`` only."""

    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError("run artifacts are not available")
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(resolved_root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            resolved_path = path.resolve()
            if not resolved_path.is_relative_to(resolved_root):
                raise ValueError("artifact path escaped run directory")
            archive.write(resolved_path, arcname=path.relative_to(resolved_root).as_posix())
    return buffer.getvalue()
