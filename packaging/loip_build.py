"""PEP 517 backend: setuptools with clamped tar/gzip metadata for bit-identical sdists."""

from __future__ import annotations

import gzip
import io
import os
import tarfile

_EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1700000000"))
os.environ["SOURCE_DATE_EPOCH"] = str(_EPOCH)


def _install_tar_clamps() -> None:
    orig_gettarinfo = tarfile.TarFile.gettarinfo

    def gettarinfo(self, name=None, arcname=None, fileobj=None):
        info = orig_gettarinfo(self, name, arcname, fileobj)
        if info is None:
            return None
        info.mtime = float(_EPOCH)
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        if info.pax_headers:
            info.pax_headers.pop("atime", None)
            info.pax_headers.pop("ctime", None)
            info.pax_headers.pop("mtime", None)
        if info.isdir():
            info.mode = 0o755
        elif info.isreg() or info.issym():
            info.mode = 0o644
        return info

    tarfile.TarFile.gettarinfo = gettarinfo  # type: ignore[method-assign]


_install_tar_clamps()

from setuptools import build_meta as _st_meta  # noqa: E402
from setuptools.build_meta import *  # noqa: E402,F403


def _rewrite_gzip_header(path: str) -> None:
    with gzip.open(path, "rb") as src:
        payload = src.read()
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=_EPOCH) as out:
        out.write(payload)
    with open(path, "wb") as dst:
        dst.write(buf.getvalue())


def build_sdist(sdist_directory, config_settings=None):
    filename = _st_meta.build_sdist(sdist_directory, config_settings)
    _rewrite_gzip_header(os.path.join(sdist_directory, filename))
    return filename
