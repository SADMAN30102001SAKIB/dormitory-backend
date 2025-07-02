import os
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class DocumentValidator:
    """Validator for document file uploads."""

    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        ".pdf": ["application/pdf"],
        ".doc": ["application/msword"],
        ".docx": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        ".ppt": ["application/vnd.ms-powerpoint"],
        ".pptx": [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ],
        ".xls": ["application/vnd.ms-excel"],
        ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        ".xlsm": ["application/vnd.ms-excel.sheet.macroEnabled.12"],
        ".xlsb": ["application/vnd.ms-excel.sheet.binary.macroEnabled.12"],
    }

    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

    def __init__(self, max_size=None):
        if max_size is not None:
            self.MAX_FILE_SIZE = max_size

    def __call__(self, file):
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE / (1024 * 1024):.1f}MB. "
                f"Current file size: {file.size / (1024 * 1024):.1f}MB"
            )

        # Get file extension
        file_extension = os.path.splitext(file.name)[1].lower()

        # Check if extension is allowed
        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed_exts = ", ".join(self.ALLOWED_EXTENSIONS.keys())
            raise ValidationError(
                f'File type "{file_extension}" is not allowed. '
                f"Allowed file types: {allowed_exts}"
            )

        # Additional validation can be added here for MIME type checking
        # Note: For production, you might want to add python-magic for more robust MIME type detection

        return file


@deconstructible
class ImageValidator:
    """Validator for image file uploads."""

    # Allowed image extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        ".jpg": ["image/jpeg"],
        ".jpeg": ["image/jpeg"],
        ".png": ["image/png"],
        ".gif": ["image/gif"],
        ".bmp": ["image/bmp"],
        ".webp": ["image/webp"],
        ".svg": ["image/svg+xml"],
        ".tiff": ["image/tiff"],
        ".tif": ["image/tiff"],
    }

    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

    def __init__(self, max_size=None):
        if max_size is not None:
            self.MAX_FILE_SIZE = max_size

    def __call__(self, file):
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE / (1024 * 1024):.1f}MB. "
                f"Current file size: {file.size / (1024 * 1024):.1f}MB"
            )

        # Get file extension
        file_extension = os.path.splitext(file.name)[1].lower()

        # Check if extension is allowed
        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed_exts = ", ".join(self.ALLOWED_EXTENSIONS.keys())
            raise ValidationError(
                f'File type "{file_extension}" is not allowed. '
                f"Allowed image types: {allowed_exts}"
            )

        return file


@deconstructible
class VideoValidator:
    """Validator for video file uploads."""

    # Allowed video extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        ".mp4": ["video/mp4"],
        ".avi": ["video/x-msvideo"],
        ".mov": ["video/quicktime"],
        ".wmv": ["video/x-ms-wmv"],
        ".flv": ["video/x-flv"],
        ".webm": ["video/webm"],
        ".mkv": ["video/x-matroska"],
        ".m4v": ["video/x-m4v"],
        ".3gp": ["video/3gpp"],
        ".ogv": ["video/ogg"],
    }

    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

    def __init__(self, max_size=None):
        if max_size is not None:
            self.MAX_FILE_SIZE = max_size

    def __call__(self, file):
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE / (1024 * 1024):.1f}MB. "
                f"Current file size: {file.size / (1024 * 1024):.1f}MB"
            )

        # Get file extension
        file_extension = os.path.splitext(file.name)[1].lower()

        # Check if extension is allowed
        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed_exts = ", ".join(self.ALLOWED_EXTENSIONS.keys())
            raise ValidationError(
                f'File type "{file_extension}" is not allowed. '
                f"Allowed video types: {allowed_exts}"
            )

        return file


@deconstructible
class AudioValidator:
    """Validator for audio file uploads."""

    # Allowed audio extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        ".mp3": ["audio/mpeg"],
        ".wav": ["audio/wav"],
        ".ogg": ["audio/ogg"],
        ".m4a": ["audio/mp4"],
        ".aac": ["audio/aac"],
        ".flac": ["audio/flac"],
        ".wma": ["audio/x-ms-wma"],
        ".opus": ["audio/opus"],
        ".webm": ["audio/webm"],
    }

    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

    def __init__(self, max_size=None):
        if max_size is not None:
            self.MAX_FILE_SIZE = max_size

    def __call__(self, file):
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE / (1024 * 1024):.1f}MB. "
                f"Current file size: {file.size / (1024 * 1024):.1f}MB"
            )

        # Get file extension
        file_extension = os.path.splitext(file.name)[1].lower()

        # Check if extension is allowed
        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed_exts = ", ".join(self.ALLOWED_EXTENSIONS.keys())
            raise ValidationError(
                f'File type "{file_extension}" is not allowed. '
                f"Allowed audio types: {allowed_exts}"
            )

        return file


def validate_document_file(file):
    """Standalone function validator for document files."""
    validator = DocumentValidator()
    return validator(file)


def validate_image_file(file):
    """Standalone function validator for image files."""
    validator = ImageValidator()
    return validator(file)


def validate_video_file(file):
    """Standalone function validator for video files."""
    validator = VideoValidator()
    return validator(file)


def validate_audio_file(file):
    """Standalone function validator for audio files."""
    validator = AudioValidator()
    return validator(file)
