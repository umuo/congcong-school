import json
from pathlib import Path

import pytest

from app.learning.grading import GRADING_RULE_VERSION, grade_answer

VECTORS = json.loads(
    (Path(__file__).resolve().parents[3] / "packages/core/spec/grading-vectors.json").read_text()
)


def test_explicit_grading_rule_version():
    assert GRADING_RULE_VERSION == VECTORS["version"]


@pytest.mark.parametrize("vector", VECTORS["cases"], ids=lambda v: v["id"])
def test_shared_grading_vectors(vector):
    assert grade_answer(vector, vector["input"]) is vector["expected"]
