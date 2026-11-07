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
        ("bundle.js", 'const q={answer:response.answer,explanation:"secret"};'),
        ("bundle.js", 'const q={answer:"secret",explanation:response.explanation};'),
        ("single.json", '{"answer":"secret","explanation":"private"}'),
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
    (target / "runtime.js").write_text(
        'const q={answer:session.feedback?.answer??"",'
        'explanation:session.feedback?.explanation??""};'
    )
    assert scanner.scan(target)["status"] == "passed"
print("cloud artifact scanner: 10 rejection cases, public references and runtime mapping passed")
