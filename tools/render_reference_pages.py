"""把参考书 PDF 的指定页渲染成 PNG，便于读图查阅公式。

两本参考书都是**纯扫描图像、无文本层**，无法用 `pypdf` 提取文字，只能渲染成
图片后再阅读。因为所有公式都必须溯源到书，这个脚本是日常高频工具。

依赖：``pymupdf``（仅本工具需要，不在项目运行依赖里）::

    pip install pymupdf

用法::

    # python tools/render_reference_pages.py <book> <start> <end> [dpi]
    python tools/render_reference_pages.py 0 29 39 160

    book: 0 = 李为吉《飞机总体设计》（印刷页 = PDF 页 − 13）
          1 = 刘虎《飞机总体设计》
    输出: output/reference_pages/book<N>/p<PDF页码>.png
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import pymupdf

REPO_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = REPO_ROOT / "参考文献"
OUT_DIR = REPO_ROOT / "output" / "reference_pages"

BOOKS = {
    0: "李为吉《飞机总体设计》（印刷页 = PDF 页 − 13）",
    1: "刘虎《飞机总体设计》",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染参考书页面为 PNG")
    parser.add_argument("book", type=int, choices=sorted(BOOKS), help="书序号，见文件头说明")
    parser.add_argument("start", type=int, help="起始 PDF 页码（0 起）")
    parser.add_argument("end", type=int, help="结束 PDF 页码（含）")
    parser.add_argument("--dpi", type=int, default=150, help="渲染分辨率，默认 150")
    args = parser.parse_args()

    pdfs = sorted(glob.glob(str(REF_DIR / "*.pdf")))
    if len(pdfs) <= args.book:
        print(f"参考文献目录下只找到 {len(pdfs)} 个 PDF，无法打开第 {args.book} 本")
        return 1

    doc = pymupdf.open(pdfs[args.book])
    out_dir = OUT_DIR / f"book{args.book + 1}"
    out_dir.mkdir(parents=True, exist_ok=True)

    end = min(args.end, doc.page_count - 1)
    matrix = pymupdf.Matrix(args.dpi / 72.0, args.dpi / 72.0)

    for page_no in range(args.start, end + 1):
        pix = doc.load_page(page_no).get_pixmap(matrix=matrix)
        target = out_dir / f"p{page_no:03d}.png"
        pix.save(str(target))
        print(f"{target}  ({pix.width}x{pix.height})")

    print(f"\n{BOOKS[args.book]}")
    print(f"共渲染 {end - args.start + 1} 页 -> {out_dir}")
    print(f"该 PDF 总页数：{doc.page_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
