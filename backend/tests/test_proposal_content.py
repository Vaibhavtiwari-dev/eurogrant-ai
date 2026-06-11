from datetime import UTC, datetime

import pytest

from app import models
from app.services.proposal_content import (
    InvalidTipTapDocument,
    markdown_to_tiptap,
    rebuild_proposal_content,
    tiptap_to_markdown,
    validate_and_normalize_tiptap_document,
)


def test_empty_document_is_valid():
    assert validate_and_normalize_tiptap_document(
        {"type": "doc", "content": [{"type": "paragraph"}]}
    ) == {"type": "doc", "content": [{"type": "paragraph"}]}


@pytest.mark.parametrize(
    "document",
    [
        {"type": "doc", "content": [{"type": "image", "attrs": {"src": "x"}}]},
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x", "marks": [{"type": "script"}]}],
                }
            ],
        },
    ],
)
def test_unknown_nodes_and_marks_are_rejected(document):
    with pytest.raises(InvalidTipTapDocument):
        validate_and_normalize_tiptap_document(document)


@pytest.mark.parametrize("href", ["javascript:alert(1)", "data:text/html,x", "//evil.test/x"])
def test_unsafe_link_protocols_are_rejected(href):
    document = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "link",
                        "marks": [{"type": "link", "attrs": {"href": href}}],
                    }
                ],
            }
        ],
    }
    with pytest.raises(InvalidTipTapDocument):
        validate_and_normalize_tiptap_document(document)


def test_safe_link_is_normalized():
    document = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "source",
                        "marks": [
                            {
                                "type": "link",
                                "attrs": {
                                    "href": "https://example.com",
                                    "onclick": "alert(1)",
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }
    normalized = validate_and_normalize_tiptap_document(document)
    attrs = normalized["content"][0]["content"][0]["marks"][0]["attrs"]
    assert attrs == {
        "href": "https://example.com",
        "target": "_blank",
        "rel": "noopener noreferrer nofollow",
    }


@pytest.mark.parametrize(
    "document",
    [
        [],
        {"type": "doc", "content": "not-a-list"},
        {"type": "doc", "content": [{"type": "heading", "attrs": {"level": 8}}]},
        {
            "type": "doc",
            "content": [{"type": "orderedList", "attrs": {"start": 0}, "content": []}],
        },
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x", "marks": "bold"}],
                }
            ],
        },
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x", "marks": [1]}],
                }
            ],
        },
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x", "marks": [{"type": "link"}]}],
                }
            ],
        },
    ],
)
def test_malformed_documents_are_rejected(document):
    with pytest.raises(InvalidTipTapDocument):
        validate_and_normalize_tiptap_document(document)


def test_excessive_depth_is_rejected():
    node = {"type": "paragraph"}
    for _ in range(14):
        node = {"type": "blockquote", "content": [node]}
    with pytest.raises(InvalidTipTapDocument, match="nesting"):
        validate_and_normalize_tiptap_document({"type": "doc", "content": [node]})


def test_non_serializable_document_is_rejected():
    with pytest.raises(InvalidTipTapDocument, match="serializable"):
        validate_and_normalize_tiptap_document({"type": "doc", "bad": {object()}})


def test_markdown_round_trip_is_deterministic():
    markdown = "## Impact\n\nThis project creates measurable impact."
    document = markdown_to_tiptap(markdown)
    assert tiptap_to_markdown(document) == markdown


def test_markdown_conversion_supports_plain_paragraphs_and_empty_input():
    assert markdown_to_tiptap("") == {
        "type": "doc",
        "content": [{"type": "paragraph"}],
    }
    assert tiptap_to_markdown(markdown_to_tiptap("Line one\nline two")) == "Line one line two"


def test_tiptap_render_supports_marks_lists_quotes_and_breaks():
    document = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Bold",
                        "marks": [{"type": "bold"}],
                    },
                    {"type": "hardBreak"},
                    {
                        "type": "text",
                        "text": "Link",
                        "marks": [
                            {
                                "type": "link",
                                "attrs": {"href": "https://example.com"},
                            }
                        ],
                    },
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Item"}],
                            }
                        ],
                    }
                ],
            },
            {
                "type": "blockquote",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Quote"}],
                    }
                ],
            },
        ],
    }
    markdown = tiptap_to_markdown(document)
    assert "**Bold**" in markdown
    assert "[Link](https://example.com)" in markdown
    assert "- Item" in markdown
    assert "> Quote" in markdown


def test_rebuild_proposal_content_uses_section_order(db_session, test_user):
    grant = models.Grant(
        external_id="CONTENT-1",
        title="Content Test",
        description="Test",
        deadline=datetime(2027, 1, 1, tzinfo=UTC),
    )
    db_session.add(grant)
    db_session.commit()
    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
    )
    db_session.add(proposal)
    db_session.commit()
    db_session.add_all(
        [
            models.ProposalSection(
                proposal_id=proposal.id,
                section_key="impact",
                name="Impact",
                content_json=markdown_to_tiptap("Second"),
                order=1,
            ),
            models.ProposalSection(
                proposal_id=proposal.id,
                section_key="summary",
                name="Summary",
                content_json=markdown_to_tiptap("First"),
                order=0,
            ),
        ]
    )
    db_session.commit()

    snapshot = rebuild_proposal_content(db_session, proposal.id)

    assert snapshot == "## Summary\n\nFirst\n\n## Impact\n\nSecond"
    assert proposal.content == snapshot


def test_rebuild_missing_proposal_raises(db_session):
    with pytest.raises(ValueError, match="not found"):
        rebuild_proposal_content(db_session, 999999)
