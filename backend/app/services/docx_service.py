"""Small dependency-free DOCX builder for accepted requirements exports."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape, quoteattr


def _p(text: str, style: str | None = None) -> str:
    safe = escape(text or "")
    style_xml = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{style_xml}<w:r><w:t xml:space=\"preserve\">{safe}</w:t></w:r></w:p>"


def _hyperlink(text: str, rel_id: str) -> str:
    safe = escape(text or "")
    return (
        f'<w:p><w:hyperlink r:id="{rel_id}" w:history="1">'
        '<w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
        f'<w:t xml:space="preserve">{safe}</w:t></w:r>'
        "</w:hyperlink></w:p>"
    )


def build_requirements_preview(session, preferences: list[dict], first_prompt: str = "", chat_url: str | None = None) -> dict:
    accepted = [p for p in preferences if p.get("status") == "accepted"]
    grouped: dict[str, list[dict]] = {}
    for pref in accepted:
        grouped.setdefault(pref.get("dimension") or "General", []).append(pref)
    return {
        "title": "Accepted Requirements",
        "chat_prompt": first_prompt or session.title or "No initial user prompt found.",
        "chat_url": chat_url,
        "topic": session.topic or "General",
        "persona": session.custom_persona_name or session.stakeholder or "Unspecified",
        "project_context": session.system_context or "",
        "accepted_count": len(accepted),
        "groups": [
            {"dimension": dimension, "items": items}
            for dimension, items in grouped.items()
        ],
    }


def build_requirements_doc(preview: dict) -> bytes:
    body: list[str] = [
        _p(preview.get("title") or "Accepted Requirements", "Title"),
    ]
    chat_url = preview.get("chat_url")
    if chat_url:
        body.append(_hyperlink(f"Open this chat: {chat_url}", "rId2"))
    body.extend([
        _p(f"Chat: {preview.get('chat_prompt') or 'No initial user prompt found.'}", "Heading1"),
        _p(f"Topic: {preview.get('topic') or 'General'}"),
        _p(f"Persona: {preview.get('persona') or 'Unspecified'}"),
    ])
    if preview.get("project_context"):
        body.append(_p(f"Project context: {preview['project_context']}"))

    if not preview.get("accepted_count"):
        body.append(_p("No accepted requirements have been selected for this chat yet.", "Heading1"))
    else:
        for group in preview.get("groups", []):
            dimension = group.get("dimension") or "General"
            items = group.get("items") or []
            body.append(_p(dimension.title(), "Heading1"))
            for idx, item in enumerate(items, start=1):
                body.append(_p(f"{idx}. {item.get('title') or 'Requirement'}", "Heading2"))
                if item.get("description"):
                    body.append(_p(item["description"]))
                body.append(_p(item.get("requirement_text") or ""))
                refs = item.get("guideline_refs") or []
                if refs:
                    ref_text = "; ".join(
                        f"{r.get('framework', '')} {r.get('article', '')}"
                        + (f" ({r.get('title')})" if r.get("title") else "")
                        for r in refs
                    )
                    body.append(_p(f"Guideline references: {ref_text}"))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {''.join(body)}
    <w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>
  </w:body>
</w:document>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
  <w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>
</w:styles>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    hyperlink_rel = ""
    if chat_url:
        hyperlink_rel = (
            f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            f'Target={quoteattr(chat_url)} TargetMode="External"/>'
        )
    doc_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  {hyperlink_rel}
</Relationships>"""

    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels)
        zf.writestr("word/styles.xml", styles_xml)
    return out.getvalue()
