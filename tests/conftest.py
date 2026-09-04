"""Shared fixtures for the chronicle test suite.

The script under test (`chronicle`) has no `.py` extension, since it's meant
to be symlinked onto PATH rather than imported. It's loaded here via
`SourceFileLoader` and registered in `sys.modules` so every test module can
just `import chronicle`.
"""

import datetime
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT_PATH = Path(__file__).parent.parent / "chronicle"
_loader = importlib.machinery.SourceFileLoader("chronicle", str(_SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("chronicle", _loader)
chronicle = importlib.util.module_from_spec(_spec)
sys.modules["chronicle"] = chronicle
_spec.loader.exec_module(chronicle)


@pytest.fixture(autouse=True)
def _isolate_from_real_environment(monkeypatch, tmp_path):
    """Prevent any test from touching the developer's real config.

    Without this, a test that doesn't pass an explicit --config would
    resolve this machine's real ~/.config/chronicle/chronicle.conf and
    read/write into whatever journal it points at.
    """
    monkeypatch.setattr(
        chronicle, "DEFAULT_CONFIG_PATH", tmp_path / "unused-default-config.conf"
    )
    monkeypatch.setattr(chronicle.sys, "stdin", SimpleNamespace(isatty=lambda: False))


@pytest.fixture
def freeze_date(monkeypatch):
    """Factory fixture: pin chronicle's notion of "today" to a fixed date."""

    def _freeze(year, month, day):
        fixed = datetime.date(year, month, day)

        class FrozenDate(datetime.date):
            @classmethod
            def today(cls):
                return fixed

        monkeypatch.setattr(chronicle.datetime, "date", FrozenDate)
        return fixed

    return _freeze
