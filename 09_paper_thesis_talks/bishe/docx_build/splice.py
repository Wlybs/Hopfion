#!/usr/bin/env python3
"""
Splice template cover (封面+诚信承诺) into pandoc-generated intermediate.docx.

Strategy:
- intermediate.docx already has template's STYLES (via --reference-doc)
- We prepend the template's cover/承诺 section XML before intermediate body
- Merge media files and relationships
"""
import shutil
import zipfile
import os
import re
from pathlib import Path
from copy import deepcopy
from lxml import etree

WORKDIR = Path('/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/docx_build')
TPL_PATH = Path('/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/2026届毕业设计模板及相关规定、要求/毕业设计(论文)材料模板/论文.docx')
INTER_PATH = WORKDIR / 'intermediate.docx'
OUT_PATH = WORKDIR / '论文_filled.docx'

NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'v': 'urn:schemas-microsoft-com:vml',
}

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def extract_docx(docx_path, extract_dir):
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(docx_path, 'r') as z:
        z.extractall(extract_dir)
    return extract_dir


def parse_xml(filepath):
    return etree.parse(str(filepath))


def write_xml(tree, filepath):
    tree.write(str(filepath), xml_declaration=True, encoding='UTF-8', standalone=True)


def find_cover_end(body):
    """Find the last paragraph of the 诚信承诺 section in template.
    We look for '年    月    日' which ends the 承诺 page."""
    paras = body.findall(f'{W}p')
    for i, p in enumerate(paras):
        texts = [t.text or '' for t in p.iter(f'{W}t')]
        full = ''.join(texts)
        if '年' in full and '月' in full and '日' in full and i > 10:
            return i
    return 20


def get_section_props(body):
    """Get the last sectPr in body (document-level section properties)."""
    return body.find(f'{W}sectPr')


def main():
    tpl_dir = WORKDIR / '_tpl_unpacked'
    inter_dir = WORKDIR / '_inter_unpacked'

    print("Step 1: Unpacking docx files...")
    extract_docx(TPL_PATH, tpl_dir)
    extract_docx(INTER_PATH, inter_dir)

    print("Step 2: Parsing XML...")
    tpl_doc = parse_xml(tpl_dir / 'word' / 'document.xml')
    inter_doc = parse_xml(inter_dir / 'word' / 'document.xml')

    tpl_body = tpl_doc.getroot().find(f'{W}body')
    inter_body = inter_doc.getroot().find(f'{W}body')

    cover_end = find_cover_end(tpl_body)
    print(f"  Cover ends at paragraph {cover_end}")

    tpl_paras = tpl_body.findall(f'{W}p')

    # Find template's first section break (sectPr inside a pPr)
    # The cover section typically has its own sectPr
    first_sect_pr = None
    for p in tpl_paras[:cover_end + 5]:
        ppr = p.find(f'{W}pPr')
        if ppr is not None:
            sp = ppr.find(f'{W}sectPr')
            if sp is not None:
                first_sect_pr = deepcopy(sp)
                print(f"  Found section break in template")
                break

    # Also check for sectPr after cover paragraphs but before 摘要
    # In many Chinese thesis templates, there's a section break between cover and abstract
    for p in tpl_paras[cover_end + 1: min(cover_end + 10, len(tpl_paras))]:
        ppr = p.find(f'{W}pPr')
        if ppr is not None:
            sp = ppr.find(f'{W}sectPr')
            if sp is not None:
                first_sect_pr = deepcopy(sp)
                print(f"  Found later section break")
                break

    print("Step 3: Collecting template cover elements...")
    cover_elements = []
    for i in range(cover_end + 1):
        cover_elements.append(deepcopy(tpl_paras[i]))

    # Also collect non-paragraph elements (tables, etc.) in cover range
    all_tpl_children = list(tpl_body)
    cover_child_count = 0
    p_count = 0
    for child in all_tpl_children:
        if child.tag == f'{W}p':
            p_count += 1
            if p_count > cover_end + 1:
                break
        cover_child_count += 1

    cover_elems_raw = [deepcopy(c) for c in all_tpl_children[:cover_child_count]]

    # If we found a section break, ensure it's on the last cover paragraph
    if first_sect_pr is not None:
        last_cover = cover_elems_raw[-1]
        if last_cover.tag == f'{W}p':
            ppr = last_cover.find(f'{W}pPr')
            if ppr is None:
                ppr = etree.SubElement(last_cover, f'{W}pPr')
                last_cover.insert(0, ppr)
            existing = ppr.find(f'{W}sectPr')
            if existing is None:
                ppr.append(deepcopy(first_sect_pr))
                print("  Attached section break to last cover paragraph")

    print("Step 4: Building final document...")
    # Get all intermediate body children
    inter_children = list(inter_body)
    # The last element is usually sectPr (document-level)
    inter_sect_pr = None
    if inter_children and inter_children[-1].tag == f'{W}sectPr':
        inter_sect_pr = inter_children[-1]
        inter_children = inter_children[:-1]

    # Clear intermediate body
    for child in list(inter_body):
        inter_body.remove(child)

    # Insert: cover elements + intermediate content + final sectPr
    for elem in cover_elems_raw:
        inter_body.append(elem)
    for elem in inter_children:
        inter_body.append(elem)
    if inter_sect_pr is not None:
        inter_body.append(inter_sect_pr)

    print("Step 5: Merging template media/embeddings into intermediate...")
    for subdir in ['media', 'embeddings', 'theme']:
        tpl_sub = tpl_dir / 'word' / subdir
        inter_sub = inter_dir / 'word' / subdir
        if tpl_sub.exists():
            inter_sub.mkdir(exist_ok=True)
            for f in tpl_sub.iterdir():
                dest = inter_sub / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)
                    print(f"  Copied {subdir}/{f.name}")

    # Merge template relationships for cover images
    tpl_rels_path = tpl_dir / 'word' / '_rels' / 'document.xml.rels'
    inter_rels_path = inter_dir / 'word' / '_rels' / 'document.xml.rels'

    if tpl_rels_path.exists() and inter_rels_path.exists():
        tpl_rels = etree.parse(str(tpl_rels_path))
        inter_rels = etree.parse(str(inter_rels_path))
        tpl_root = tpl_rels.getroot()
        inter_root = inter_rels.getroot()

        existing_ids = {r.get('Id') for r in inter_root}
        existing_types = {r.get('Type') for r in inter_root}
        SINGLETON_TYPES = {
            'styles', 'settings', 'webSettings', 'fontTable',
            'numbering', 'footnotes', 'endnotes', 'theme',
        }
        for rel in tpl_root:
            rid = rel.get('Id')
            target = rel.get('Target', '')
            reltype = rel.get('Type', '')
            if rid in existing_ids:
                continue
            # Skip singleton doc parts already present
            type_basename = reltype.rsplit('/', 1)[-1] if reltype else ''
            if type_basename in SINGLETON_TYPES and reltype in existing_types:
                print(f"  SKIPPED (singleton): {rid} → {target}")
                continue
            if target.startswith('http') or target.startswith('#'):
                inter_root.append(deepcopy(rel))
                print(f"  Added relationship: {rid} → {target[:50]}")
            else:
                target_path = inter_dir / 'word' / target
                if target_path.exists():
                    inter_root.append(deepcopy(rel))
                    print(f"  Added relationship: {rid} → {target}")
                else:
                    print(f"  SKIPPED (missing): {rid} → {target}")

        write_xml(inter_rels, inter_rels_path)

    print("Step 5b: Merging [Content_Types].xml...")
    tpl_ct_path = tpl_dir / '[Content_Types].xml'
    inter_ct_path = inter_dir / '[Content_Types].xml'
    if tpl_ct_path.exists() and inter_ct_path.exists():
        tpl_ct = etree.parse(str(tpl_ct_path))
        inter_ct = etree.parse(str(inter_ct_path))
        tpl_ct_root = tpl_ct.getroot()
        inter_ct_root = inter_ct.getroot()
        CT_NS = tpl_ct_root.nsmap.get(None, '')

        existing_exts = {e.get('Extension') for e in inter_ct_root
                         if e.get('Extension')}
        existing_parts = {e.get('PartName') for e in inter_ct_root
                          if e.get('PartName')}

        for elem in tpl_ct_root:
            ext = elem.get('Extension')
            part = elem.get('PartName')
            if ext and ext not in existing_exts:
                inter_ct_root.append(deepcopy(elem))
                existing_exts.add(ext)
                print(f"  Added Default ext: {ext}")
            elif part and part not in existing_parts:
                part_file = inter_dir / part.lstrip('/')
                if part_file.exists():
                    inter_ct_root.append(deepcopy(elem))
                    existing_parts.add(part)
                    print(f"  Added Override: {part}")

        write_xml(inter_ct, inter_ct_path)

    print("Step 6: Writing final document XML...")
    write_xml(inter_doc, inter_dir / 'word' / 'document.xml')

    print("Step 7: Repacking docx...")
    if OUT_PATH.exists():
        OUT_PATH.unlink()

    with zipfile.ZipFile(OUT_PATH, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root, dirs, files in os.walk(inter_dir):
            for f in files:
                full = Path(root) / f
                arcname = full.relative_to(inter_dir)
                zout.write(full, arcname)

    print(f"\nDONE: {OUT_PATH}")
    print(f"Size: {OUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    # Cleanup
    shutil.rmtree(tpl_dir, ignore_errors=True)
    shutil.rmtree(inter_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
