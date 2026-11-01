"""检查云端发布目录，拒绝原题库、媒体索引、源码及答案载荷。"""

import argparse
import json
import re
from pathlib import Path

TEXT = {".html", ".txt", ".json", ".js", ".mjs", ".map", ".webmanifest"}
PRIVATE_ROOTS = {"data", "audio", "story-images", "textbook-pages", "private-content"}
BULK_QUESTIONS = re.compile(r"[\"\']?questions[\"\']?\s*:\s*\[")
PRIVATE_PAIR = re.compile(r"\banswer\s*:[\s\S]{0,800}\bexplanation\s*:")


def scan(root):
    issues, scanned = [], 0
    for file in root.rglob("*"):
        if file.is_dir():
            continue
        relative = file.relative_to(root)
        if file.is_symlink():
            issues.append(f"{relative}: 发布目录不得含符号链接")
        if relative.parts[0] in PRIVATE_ROOTS or relative.name in {
            "sw.js",
            "audio-index.json",
        }:
            issues.append(f"{relative}: 混入原公开题库、媒体或缓存脚本")
        if file.suffix in {".map", ".ts", ".tsx", ".py"}:
            issues.append(f"{relative}: 混入源码或 source map")
        if file.suffix not in TEXT:
            continue
        scanned += 1
        text = file.read_text(encoding="utf-8", errors="strict")
        # RSC、HTML 内嵌 JSON 与 JS 字符串都可能对引号多次转义。
        for _ in range(3):
            text = text.replace('\\"', '"').replace("\\u0022", '"')
        if BULK_QUESTIONS.search(text) or PRIVATE_PAIR.search(text):
            issues.append(f"{relative}: 发现私有题目数组或答案/解析结构")
    return {
        "status": "failed" if issues else "passed",
        "text_files_scanned": scanned,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    if not args.artifact.is_dir() or not (args.artifact / "login/index.html").is_file():
        parser.error("必须指向完成构建且含登录页面的 cloud out 目录")
    report = scan(args.artifact)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report["issues"] else 0)


if __name__ == "__main__":
    main()
