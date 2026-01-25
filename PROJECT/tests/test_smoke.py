from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_pipeline_module():
    here = Path(__file__).resolve()
    project_root = here.parents[1]
    pipeline_path = project_root / 'src' / 'pipeline.py'
    spec = importlib.util.spec_from_file_location('pipeline', pipeline_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Python 3.13 dataclasses + string annotations expect the module
    # to be present in sys.modules during exec_module().
    import sys
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_predict_row_contract():
    pipeline = _load_pipeline_module()
    pred = pipeline.predict_row({"x1": 0.1, "x2": -0.2})
    assert 0.0 <= pred.probability <= 1.0
    assert pred.label in (0, 1)
