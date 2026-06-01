"""Build talk.pptx from talk_outline.md.

朴素布局：标题 + 文本框 + 单张图（如有）。不套配色模板。
"""
import re
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


HERE = Path(__file__).resolve().parent
OUTLINE = HERE / "talk_outline.md"
PPTX_OUT = HERE / "talk.pptx"


def split_pages(md: str):
    """Split markdown into list of (title, body) per page."""
    # Drop everything before first ## P
    pages = []
    parts = re.split(r"\n## (P\d+ — [^\n]+)\n", md)
    # parts[0] is the preamble; subsequent: title, body, title, body, ...
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        pages.append((title, body))
    return pages


def extract_image(body: str):
    """Return (image_path or None, body_without_image)."""
    m = re.search(r"!\[.*?\]\(([^)]+)\)", body)
    if not m:
        return None, body
    img_rel = m.group(1)
    img_path = HERE / img_rel if not img_rel.startswith("/") else Path(img_rel)
    body_clean = re.sub(r"!\[.*?\]\([^)]+\)\s*\n*", "", body).strip()
    return img_path if img_path.exists() else None, body_clean


def add_slide(prs, title, body):
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)

    # Title text box (top)
    tb_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.7))
    tf = tb_title.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x1F, 0x2D, 0x5A)

    img_path, body_clean = extract_image(body)

    if img_path:
        # Body on left, image on right
        tb_body = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(7.5), Inches(5.8))
        pic = slide.shapes.add_picture(str(img_path), Inches(8.3), Inches(1.4), width=Inches(4.7))
    else:
        # Full-width body
        tb_body = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.3), Inches(5.8))

    tf = tb_body.text_frame
    tf.word_wrap = True
    lines = body_clean.split("\n")
    first = True
    for line in lines:
        line = line.rstrip()
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(13)
        p.font.color.rgb = RGBColor(0x20, 0x20, 0x20)


def main():
    md = OUTLINE.read_text(encoding="utf-8")
    pages = split_pages(md)
    print(f"Parsed {len(pages)} pages.")

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    missing_images = []
    for title, body in pages:
        # Pre-check images
        img_path, _ = extract_image(body)
        if "![" in body and img_path is None:
            ref = re.search(r"!\[.*?\]\(([^)]+)\)", body)
            if ref:
                missing_images.append((title, ref.group(1)))
        add_slide(prs, title, body)

    prs.save(str(PPTX_OUT))
    print(f"Saved: {PPTX_OUT}")
    print(f"Slides: {len(prs.slides)}")

    if missing_images:
        print(f"\nMISSING images ({len(missing_images)}):")
        for t, p in missing_images:
            print(f"  - {t}: {p}")


if __name__ == "__main__":
    main()
