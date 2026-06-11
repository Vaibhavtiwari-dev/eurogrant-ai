import json
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from .. import models
from ..config import settings

ALLOWED_NODES = {
    "doc",
    "paragraph",
    "heading",
    "bulletList",
    "orderedList",
    "listItem",
    "blockquote",
    "hardBreak",
    "text",
}
ALLOWED_MARKS = {"bold", "italic", "strike", "code", "link"}
MAX_DEPTH = 12
MAX_NODES = 5000
MAX_TEXT_LENGTH = 100000


class InvalidTipTapDocument(ValueError):
    pass


def empty_tiptap_document() -> dict[str, Any]:
    return {"type": "doc", "content": [{"type": "paragraph"}]}


def validate_and_normalize_tiptap_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidTipTapDocument("TipTap content must be a JSON object")
    try:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidTipTapDocument("TipTap content must be JSON serializable") from exc
    if len(encoded) > settings.PROPOSAL_SECTION_MAX_JSON_BYTES:
        raise InvalidTipTapDocument("TipTap content exceeds the configured size limit")

    node_count = 0
    text_length = 0

    def normalize_node(node: object, depth: int) -> dict[str, Any]:
        nonlocal node_count, text_length
        if depth > MAX_DEPTH:
            raise InvalidTipTapDocument("TipTap content exceeds the maximum nesting depth")
        if not isinstance(node, dict):
            raise InvalidTipTapDocument("Every TipTap node must be an object")
        node_type = node.get("type")
        if node_type not in ALLOWED_NODES:
            raise InvalidTipTapDocument(f"Unsupported TipTap node: {node_type!r}")
        node_count += 1
        if node_count > MAX_NODES:
            raise InvalidTipTapDocument("TipTap content contains too many nodes")

        normalized: dict[str, Any] = {"type": node_type}
        if node_type == "text":
            text = node.get("text")
            if not isinstance(text, str):
                raise InvalidTipTapDocument("Text nodes require string content")
            text_length += len(text)
            if text_length > MAX_TEXT_LENGTH:
                raise InvalidTipTapDocument("TipTap content contains too much text")
            normalized["text"] = text
            marks = node.get("marks", [])
            if not isinstance(marks, list):
                raise InvalidTipTapDocument("Text marks must be an array")
            normalized_marks = [_normalize_mark(mark) for mark in marks]
            if normalized_marks:
                normalized["marks"] = normalized_marks
        elif node_type == "heading":
            attrs = node.get("attrs", {})
            if not isinstance(attrs, dict) or attrs.get("level") not in {1, 2, 3}:
                raise InvalidTipTapDocument("Headings require a level from 1 through 3")
            normalized["attrs"] = {"level": attrs["level"]}
        elif node_type == "orderedList":
            attrs = node.get("attrs", {})
            start = attrs.get("start", 1) if isinstance(attrs, dict) else 1
            if not isinstance(start, int) or start < 1 or start > 10000:
                raise InvalidTipTapDocument("Ordered list start must be a positive integer")
            normalized["attrs"] = {"start": start}

        content = node.get("content")
        if content is not None:
            if not isinstance(content, list):
                raise InvalidTipTapDocument("Node content must be an array")
            normalized["content"] = [normalize_node(child, depth + 1) for child in content]
        return normalized

    normalized = normalize_node(value, 0)
    if normalized["type"] != "doc":
        raise InvalidTipTapDocument("The root TipTap node must be a doc")
    return normalized


def _normalize_mark(mark: object) -> dict[str, Any]:
    if not isinstance(mark, dict):
        raise InvalidTipTapDocument("TipTap marks must be objects")
    mark_type = mark.get("type")
    if mark_type not in ALLOWED_MARKS:
        raise InvalidTipTapDocument(f"Unsupported TipTap mark: {mark_type!r}")
    normalized: dict[str, Any] = {"type": mark_type}
    if mark_type == "link":
        attrs = mark.get("attrs", {})
        href = attrs.get("href") if isinstance(attrs, dict) else None
        if not isinstance(href, str) or not href.strip():
            raise InvalidTipTapDocument("Link marks require an href")
        parsed = urlparse(href)
        if parsed.scheme.lower() not in {"http", "https", "mailto"}:
            raise InvalidTipTapDocument("Unsupported link protocol")
        normalized["attrs"] = {
            "href": href,
            "target": "_blank",
            "rel": "noopener noreferrer nofollow",
        }
    return normalized


def markdown_to_tiptap(markdown: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines).strip()
            content.append(
                {"type": "paragraph", "content": [{"type": "text", "text": text}]}
                if text
                else {"type": "paragraph"}
            )
            paragraph_lines.clear()

    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.rstrip()
        if not line:
            flush_paragraph()
            continue
        stripped = line.lstrip()
        heading_level = len(stripped) - len(stripped.lstrip("#"))
        if 1 <= heading_level <= 3 and stripped[heading_level:].startswith(" "):
            flush_paragraph()
            text = stripped[heading_level + 1 :].strip()
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": heading_level},
                    "content": [{"type": "text", "text": text}],
                }
            )
        else:
            paragraph_lines.append(line)
    flush_paragraph()
    return validate_and_normalize_tiptap_document(
        {"type": "doc", "content": content or [{"type": "paragraph"}]}
    )


def tiptap_to_markdown(document: dict[str, Any]) -> str:
    normalized = validate_and_normalize_tiptap_document(document)

    def render(node: dict[str, Any], indent: int = 0) -> str:
        node_type = node["type"]
        children = node.get("content", [])
        if node_type == "text":
            text = node["text"]
            for mark in node.get("marks", []):
                mark_type = mark["type"]
                if mark_type == "bold":
                    text = f"**{text}**"
                elif mark_type == "italic":
                    text = f"*{text}*"
                elif mark_type == "strike":
                    text = f"~~{text}~~"
                elif mark_type == "code":
                    text = f"`{text}`"
                elif mark_type == "link":
                    text = f"[{text}]({mark['attrs']['href']})"
            return text
        if node_type == "hardBreak":
            return "  \n"
        rendered_children = "".join(render(child, indent) for child in children)
        if node_type == "heading":
            return f"{'#' * node['attrs']['level']} {rendered_children.strip()}\n\n"
        if node_type == "paragraph":
            return f"{rendered_children.strip()}\n\n"
        if node_type == "blockquote":
            lines = rendered_children.strip().splitlines()
            return "\n".join(f"> {line}" for line in lines) + "\n\n"
        if node_type in {"bulletList", "orderedList"}:
            parts: list[str] = []
            start = node.get("attrs", {}).get("start", 1)
            for index, child in enumerate(children):
                body = render(child, indent + 1).strip()
                prefix = "- " if node_type == "bulletList" else f"{start + index}. "
                parts.append(f"{'  ' * indent}{prefix}{body}")
            return "\n".join(parts) + "\n\n"
        if node_type == "listItem":
            return rendered_children.strip()
        return rendered_children

    return render(normalized).strip()


def rebuild_proposal_content(db: Session, proposal_id: int) -> str:
    proposal = db.query(models.Proposal).filter(models.Proposal.id == proposal_id).first()
    if not proposal:
        raise ValueError(f"Proposal with id {proposal_id} not found")
    sections = (
        db.query(models.ProposalSection)
        .filter(models.ProposalSection.proposal_id == proposal_id)
        .order_by(models.ProposalSection.order, models.ProposalSection.id)
        .all()
    )
    rendered: list[str] = []
    for section in sections:
        body = tiptap_to_markdown(section.content_json).strip()
        rendered.append(f"## {section.name}\n\n{body}".strip())
    snapshot = "\n\n".join(rendered)
    proposal.content = snapshot
    db.flush()
    return snapshot
