from pathlib import Path


# =====================================================
# Obsługiwane rozszerzenia plików wejściowych
# =====================================================

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
}

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
}

SUPPORTED_EXTENSIONS = (
    SUPPORTED_IMAGE_EXTENSIONS
    | SUPPORTED_DOCUMENT_EXTENSIONS
)


# =====================================================
# Obsługiwane formaty wyjściowe
# =====================================================

IMAGE_OUTPUT_FORMATS = {
    "jpg",
    "png",
    "webp",
    "heic",
}

PDF_OUTPUT_FORMATS = {
    "pdf",
}

SUPPORTED_OUTPUT_FORMATS = (
    IMAGE_OUTPUT_FORMATS
    | PDF_OUTPUT_FORMATS
)


# =====================================================
# Dozwolone konwersje
# =====================================================

IMAGE_TO_IMAGE_FORMATS = {
    "jpg",
    "png",
    "webp",
    "heic",
}

IMAGE_TO_DOCUMENT_FORMATS = {
    "pdf",
}

PDF_TO_IMAGE_FORMATS = {
    "jpg",
    "png",
    "webp",
}


# =====================================================
# Mapowanie aliasów formatów
# =====================================================

FORMAT_ALIASES = {
    "jpeg": "jpg",
    "jpg": "jpg",
    "heif": "heic",
    "heic": "heic",
    "png": "png",
    "webp": "webp",
    "pdf": "pdf",
}


# =====================================================
# Mapowanie formatów Pillow
# =====================================================

PIL_SAVE_FORMATS = {
    "jpg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "heic": "HEIF",
    "pdf": "PDF",
}


# =====================================================
# File dialog filters
# =====================================================

ALL_SUPPORTED_FILE_PATTERN = (
    "*.jpg *.jpeg *.png *.webp *.heic *.heif *.pdf"
)

IMAGE_FILE_PATTERN = (
    "*.jpg *.jpeg *.png *.webp *.heic *.heif"
)

PDF_FILE_PATTERN = "*.pdf"


FILE_DIALOG_TYPES = [
    (
        "All Supported Files",
        ALL_SUPPORTED_FILE_PATTERN,
    ),
    (
        "Image Files",
        IMAGE_FILE_PATTERN,
    ),
    (
        "PDF Files",
        PDF_FILE_PATTERN,
    ),
    (
        "All Files",
        "*.*",
    ),
]


IMAGE_DIALOG_TYPES = [
    (
        "Image Files",
        IMAGE_FILE_PATTERN,
    ),
    (
        "All Files",
        "*.*",
    ),
]


PDF_SAVE_DIALOG_TYPES = [
    (
        "PDF File",
        "*.pdf",
    ),
]


# =====================================================
# Funkcje pomocnicze
# =====================================================

def normalize_format(format_name: str) -> str:
    """
    Normalizuje nazwę formatu.

    Przykłady:
        ".JPEG" -> "jpg"
        "jpeg"  -> "jpg"
        ".HEIF" -> "heic"
    """

    if not format_name:
        return ""

    normalized = (
        format_name
        .strip()
        .lower()
        .lstrip(".")
    )

    return FORMAT_ALIASES.get(
        normalized,
        normalized,
    )


def normalize_extension(extension: str) -> str:
    """
    Normalizuje rozszerzenie do postaci z kropką.

    Przykłady:
        "jpg"   -> ".jpg"
        ".JPEG" -> ".jpg"
        "heif"  -> ".heic"
    """

    normalized_format = normalize_format(extension)

    if not normalized_format:
        return ""

    return f".{normalized_format}"


def get_file_extension(file_path: str) -> str:
    """
    Zwraca rozszerzenie pliku zapisane małymi literami.
    """

    return Path(file_path).suffix.lower()


def get_file_format(file_path: str) -> str:
    """
    Zwraca znormalizowany format pliku bez kropki.

    Przykłady:
        obraz.jpeg -> jpg
        obraz.heif -> heic
    """

    extension = get_file_extension(file_path)

    return normalize_format(extension)


def is_supported_file(file_path: str) -> bool:
    """
    Sprawdza, czy plik ma obsługiwane rozszerzenie.
    """

    extension = get_file_extension(file_path)

    return extension in SUPPORTED_EXTENSIONS


def is_supported_image(file_path: str) -> bool:
    """
    Sprawdza, czy plik jest obsługiwanym obrazem.
    """

    extension = get_file_extension(file_path)

    return extension in SUPPORTED_IMAGE_EXTENSIONS


def is_pdf(file_path: str) -> bool:
    """
    Sprawdza, czy plik jest dokumentem PDF.
    """

    return get_file_extension(file_path) == ".pdf"


def is_supported_output_format(
    output_format: str,
) -> bool:
    """
    Sprawdza, czy wybrany format wyjściowy jest obsługiwany.
    """

    normalized_format = normalize_format(
        output_format
    )

    return normalized_format in SUPPORTED_OUTPUT_FORMATS


def can_convert(
    input_path: str,
    output_format: str,
) -> bool:
    """
    Sprawdza, czy dana konwersja jest obsługiwana.
    """

    input_format = get_file_format(input_path)
    output_format = normalize_format(output_format)

    if not input_format or not output_format:
        return False

    if input_format == output_format:
        return False

    if input_format == "pdf":
        return output_format in PDF_TO_IMAGE_FORMATS

    if (
        normalize_extension(input_format)
        in SUPPORTED_IMAGE_EXTENSIONS
    ):
        return output_format in (
            IMAGE_TO_IMAGE_FORMATS
            | IMAGE_TO_DOCUMENT_FORMATS
        )

    return False