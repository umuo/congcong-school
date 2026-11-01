"""云端发布扫描器的拒绝用例，不需要实际课程或数据库。"""

import importlib.util
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "cloud_artifact", root / "scripts/cloud/scan-artifact.py"
)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
with tempfile.TemporaryDirectory() as folder:
    target = Path(folder)
    for name, content in [
        ("lesson.json", '{"questions":[{"answer":"secret"}]}'),
        ("lesson.txt", '{\\"questions\\":[{\\"answer\\":\\"secret\\"}]}'),
        ("bundle.js", 'const q={question:"x",answer:5,explanation:"secret"};'),
        ("bundle.js.map", "{}"),
        ("source.ts", "export const secret = 1"),
        ("sw.js", ""),
    ]:
        file = target / name
        file.write_text(content)
        assert scanner.scan(target)["status"] == "failed", name
        file.unlink()
    (target / "audio").mkdir()
    (target / "audio/index.json").write_text("{}")
    assert scanner.scan(target)["status"] == "failed"
    (target / "audio/index.json").unlink()
    (target / "audio").rmdir()
    (target / "public.json").write_text('{"question_refs":[{"uid":"opaque"}]}')
    assert scanner.scan(target)["status"] == "passed"
print("cloud artifact scanner: 7 rejection cases and public-reference allowance passed")
