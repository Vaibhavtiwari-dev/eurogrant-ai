import io
import zipfile

import docx


def _make_high_compression_docx() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", b"0" * (2 * 1024 * 1024))
    return output.getvalue()


def _make_valid_docx() -> bytes:
    output = io.BytesIO()
    document = docx.Document()
    document.add_paragraph("Valid company profile")
    document.save(output)
    return output.getvalue()


def test_list_documents(authenticated_client):
    response = authenticated_client.get("/api/v1/uploads/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_upload_document_success(authenticated_client, mock_s3, mock_worker):
    file_content = b"%PDF-1.4\nfake pdf content"
    file_name = "test.pdf"
    response = authenticated_client.post(
        "/api/v1/uploads/company-document",
        files={"file": (file_name, file_content, "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == file_name
    assert data["status"] == "pending"

    # Verify S3 upload and Worker trigger
    assert mock_s3.called
    assert mock_worker.called


def test_upload_document_invalid_extension(authenticated_client):
    file_content = b"fake text content"
    file_name = "test.txt"

    response = authenticated_client.post(
        "/api/v1/uploads/company-document", files={"file": (file_name, file_content, "text/plain")}
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_document_too_large(authenticated_client):
    # MAX_FILE_SIZE is 25MB
    large_content = b"a" * (26 * 1024 * 1024)
    file_name = "large.pdf"

    response = authenticated_client.post(
        "/api/v1/uploads/company-document",
        files={"file": (file_name, large_content, "application/pdf")},
    )

    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


def test_upload_rejects_high_compression_docx(authenticated_client, mock_s3, mock_worker):
    response = authenticated_client.post(
        "/api/v1/uploads/company-document",
        files={
            "file": (
                "compressed.docx",
                _make_high_compression_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert "unsafe archive" in response.json()["detail"].lower()
    assert not mock_s3.called
    assert not mock_worker.called


def test_upload_accepts_normal_docx(authenticated_client, mock_s3, mock_worker):
    response = authenticated_client.post(
        "/api/v1/uploads/company-document",
        files={
            "file": (
                "company.docx",
                _make_valid_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    assert mock_s3.called
    assert mock_worker.called
