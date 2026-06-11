from io import BytesIO
from zipfile import BadZipFile, ZipFile

MAX_DOCX_MEMBERS = 512
MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE = 50 * 1024 * 1024
MAX_DOCX_MEMBER_UNCOMPRESSED_SIZE = 20 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 100
REQUIRED_DOCX_MEMBERS = {"[Content_Types].xml", "word/document.xml"}


class UnsafeDocumentError(ValueError):
    pass


def validate_docx_archive(file_content: bytes) -> None:
    try:
        with ZipFile(BytesIO(file_content)) as archive:
            members = archive.infolist()
            member_names = {member.filename for member in members}

            if not REQUIRED_DOCX_MEMBERS.issubset(member_names):
                raise UnsafeDocumentError("DOCX archive is missing required document parts")
            if len(members) > MAX_DOCX_MEMBERS:
                raise UnsafeDocumentError("DOCX archive contains too many members")

            total_uncompressed = 0
            for member in members:
                if member.flag_bits & 0x1:
                    raise UnsafeDocumentError("Encrypted DOCX archives are not supported")
                if member.file_size > MAX_DOCX_MEMBER_UNCOMPRESSED_SIZE:
                    raise UnsafeDocumentError("DOCX archive member is too large")

                total_uncompressed += member.file_size
                if total_uncompressed > MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE:
                    raise UnsafeDocumentError("DOCX expanded size exceeds the safety limit")

                compressed_size = max(member.compress_size, 1)
                if member.file_size / compressed_size > MAX_DOCX_COMPRESSION_RATIO:
                    raise UnsafeDocumentError("DOCX archive has an unsafe compression ratio")
    except BadZipFile as exc:
        raise UnsafeDocumentError("DOCX content is not a valid ZIP archive") from exc
