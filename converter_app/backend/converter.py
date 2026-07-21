import os
from collections.abc import Callable
from pathlib import Path

import fitz
import pillow_heif
from PIL import Image

from backend.formats import SUPPORTED_IMAGE_EXTENSIONS
from backend.exceptions import (
    ConversionCancelledError,
    EmptyPdfError,
    InvalidOutputFormatError,
    SameFormatConversionError,
    UnsupportedConversionError,
    UnsupportedInputFormatError,
)


# Umożliwia Pillow otwieranie plików HEIC/HEIF.
pillow_heif.register_heif_opener()


class FileConverter:
    """
    Obsługuje lokalną konwersję plików graficznych oraz PDF.

    Metoda convert() zwraca listę utworzonych plików.
    Dla zwykłego obrazu lista zawiera jeden plik.
    Dla PDF lista może zawierać wiele obrazów — po jednym na stronę.
    """

    IMAGE_OUTPUT_FORMATS = {"jpg", "png", "webp", "heic"}
    PDF_IMAGE_OUTPUT_FORMATS = {"jpg", "png", "webp"}

    def __init__(
        self,
        pdf_zoom: float = 3.0,
        overwrite_existing: bool = False,
    ):
        if pdf_zoom <= 0:
            raise ValueError("PDF zoom must be greater than zero.")

        self.pdf_zoom = pdf_zoom
        self.overwrite_existing = overwrite_existing

    def convert(
        self,
        input_path: str,
        output_format: str,
        cancel_callback: Callable[[], bool] | None = None,
    ) -> list[str]:
        """
        Konwertuje jeden plik do wskazanego formatu.

        Args:
            input_path:
                Ścieżka do pliku wejściowego.

            output_format:
                Format bez kropki, np. "jpg", "png", "webp",
                "pdf" albo "heic".

            cancel_callback:
                Opcjonalna funkcja zwracająca True, gdy operacja
                powinna zostać anulowana.

        Returns:
            Lista ścieżek utworzonych plików.

        Raises:
            FileNotFoundError:
                Gdy plik wejściowy nie istnieje.

            ValueError:
                Gdy dana konwersja nie jest obsługiwana.

            RuntimeError:
                Gdy użytkownik anuluje operację.
        """

        input_path = os.path.abspath(
            os.path.normpath(input_path)
        )

        if not os.path.isfile(input_path):
            raise FileNotFoundError(
                f"Input file does not exist: {input_path}"
            )

        output_format = self._normalize_output_format(
            output_format
        )

        input_extension = Path(input_path).suffix.lower()

        self._check_cancelled(cancel_callback)

        if input_extension == ".pdf":
            return self._convert_pdf(
                input_path=input_path,
                output_format=output_format,
                cancel_callback=cancel_callback,
            )

        if input_extension in SUPPORTED_IMAGE_EXTENSIONS:
            return self._convert_image(
                input_path=input_path,
                input_extension=input_extension,
                output_format=output_format,
                cancel_callback=cancel_callback,
            )

        raise UnsupportedInputFormatError(
            f"Unsupported input format: {input_extension}"
        )

    # =====================================================
    # Konwersja obrazów
    # =====================================================

    def _convert_image(
        self,
        input_path: str,
        input_extension: str,
        output_format: str,
        cancel_callback: Callable[[], bool] | None,
    ) -> list[str]:
        self._check_cancelled(cancel_callback)

        if output_format == "pdf":
            output_path = self._create_output_path(
                input_path=input_path,
                output_extension="pdf",
            )

            self._image_to_pdf(
                input_path=input_path,
                output_path=output_path,
            )

            return [output_path]

        if output_format not in self.IMAGE_OUTPUT_FORMATS:
            raise UnsupportedConversionError(
                "Unsupported conversion: "
                f"{input_extension} -> {output_format}"
            )

        input_normalized_format = self._normalize_extension_format(
            input_extension
        )

        if input_normalized_format == output_format:
            raise SameFormatConversionError(
                f"Input file is already in .{output_format} format."
            )

        output_path = self._create_output_path(
            input_path=input_path,
            output_extension=output_format,
        )

        self._convert_image_format(
            input_path=input_path,
            output_path=output_path,
            output_format=output_format,
        )

        self._check_cancelled(cancel_callback)

        return [output_path]

    def _convert_image_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str,
    ) -> None:
        with Image.open(input_path) as source_image:
            source_image.load()

            if output_format == "jpg":
                converted_image = self._prepare_for_jpeg(
                    source_image
                )

                try:
                    converted_image.save(
                        output_path,
                        format="JPEG",
                        quality=95,
                        optimize=True,
                    )
                finally:
                    converted_image.close()

                return

            if output_format == "png":
                converted_image = self._prepare_for_png(
                    source_image
                )

                try:
                    converted_image.save(
                        output_path,
                        format="PNG",
                        optimize=True,
                    )
                finally:
                    converted_image.close()

                return

            if output_format == "webp":
                converted_image = self._prepare_for_webp(
                    source_image
                )

                try:
                    converted_image.save(
                        output_path,
                        format="WEBP",
                        quality=95,
                        method=6,
                    )
                finally:
                    converted_image.close()

                return

            if output_format == "heic":
                converted_image = self._prepare_for_heic(
                    source_image
                )

                try:
                    converted_image.save(
                        output_path,
                        format="HEIF",
                        quality=95,
                    )
                finally:
                    converted_image.close()

                return

        raise ValueError(
            f"Unsupported output format: {output_format}"
        )

    def _image_to_pdf(
        self,
        input_path: str,
        output_path: str,
    ) -> None:
        with Image.open(input_path) as source_image:
            source_image.load()

            converted_image = self._prepare_for_jpeg(
                source_image
            )

            try:
                converted_image.save(
                    output_path,
                    format="PDF",
                    resolution=100.0,
                )
            finally:
                converted_image.close()

    # =====================================================
    # Konwersja PDF na obrazy
    # =====================================================

    def _convert_pdf(
        self,
        input_path: str,
        output_format: str,
        cancel_callback: Callable[[], bool] | None,
    ) -> list[str]:
        if output_format not in self.PDF_IMAGE_OUTPUT_FORMATS:
            raise UnsupportedConversionError(
                f"Unsupported conversion: .pdf -> {output_format}"
            )

        output_paths: list[str] = []

        matrix = fitz.Matrix(
            self.pdf_zoom,
            self.pdf_zoom,
        )

        with fitz.open(input_path) as document:
            if document.page_count == 0:
                raise EmptyPdfError(
                    "The selected PDF does not contain any pages."
                )

            for page_index in range(document.page_count):
                self._check_cancelled(cancel_callback)

                page = document.load_page(page_index)

                pixmap = page.get_pixmap(
                    matrix=matrix,
                    alpha=False,
                )

                image = Image.frombytes(
                    "RGB",
                    (pixmap.width, pixmap.height),
                    pixmap.samples,
                )

                output_path = self._create_pdf_page_output_path(
                    input_path=input_path,
                    page_number=page_index + 1,
                    output_extension=output_format,
                )

                try:
                    self._save_pdf_page_image(
                        image=image,
                        output_path=output_path,
                        output_format=output_format,
                    )
                finally:
                    image.close()
                    pixmap = None

                output_paths.append(output_path)

        self._check_cancelled(cancel_callback)

        return output_paths

    def _save_pdf_page_image(
        self,
        image: Image.Image,
        output_path: str,
        output_format: str,
    ) -> None:
        if output_format == "jpg":
            image.save(
                output_path,
                format="JPEG",
                quality=95,
                optimize=True,
            )
            return

        if output_format == "png":
            image.save(
                output_path,
                format="PNG",
                optimize=True,
            )
            return

        if output_format == "webp":
            image.save(
                output_path,
                format="WEBP",
                quality=95,
                method=6,
            )
            return

        raise InvalidOutputFormatError(
            f"Unsupported PDF output format: {output_format}"
        )

    # =====================================================
    # Przygotowanie trybu i przezroczystości obrazu
    # =====================================================

    @staticmethod
    def _prepare_for_jpeg(
        image: Image.Image,
    ) -> Image.Image:
        """
        JPEG nie obsługuje przezroczystości.

        Przezroczyste obszary są umieszczane na białym tle,
        zamiast automatycznie zmieniać się na czarne.
        """

        if FileConverter._has_transparency(image):
            rgba_image = image.convert("RGBA")

            background = Image.new(
                "RGB",
                rgba_image.size,
                "white",
            )

            background.paste(
                rgba_image,
                mask=rgba_image.getchannel("A"),
            )

            rgba_image.close()
            return background

        return image.convert("RGB")

    @staticmethod
    def _prepare_for_png(
        image: Image.Image,
    ) -> Image.Image:
        if FileConverter._has_transparency(image):
            return image.convert("RGBA")

        return image.convert("RGB")

    @staticmethod
    def _prepare_for_webp(
        image: Image.Image,
    ) -> Image.Image:
        if FileConverter._has_transparency(image):
            return image.convert("RGBA")

        return image.convert("RGB")

    @staticmethod
    def _prepare_for_heic(
        image: Image.Image,
    ) -> Image.Image:
        return image.convert("RGB")

    @staticmethod
    def _has_transparency(
        image: Image.Image,
    ) -> bool:
        if image.mode in {"RGBA", "LA"}:
            return True

        if image.mode == "P":
            return "transparency" in image.info

        return False

    # =====================================================
    # Generowanie nazw plików
    # =====================================================

    def _create_output_path(
        self,
        input_path: str,
        output_extension: str,
    ) -> str:
        path = Path(input_path)

        requested_path = path.with_suffix(
            f".{output_extension}"
        )

        return self._resolve_output_path(
            requested_path
        )

    def _create_pdf_page_output_path(
        self,
        input_path: str,
        page_number: int,
        output_extension: str,
    ) -> str:
        path = Path(input_path)

        requested_path = path.with_name(
            f"{path.stem}_page{page_number}.{output_extension}"
        )

        return self._resolve_output_path(
            requested_path
        )

    def _resolve_output_path(
        self,
        requested_path: Path,
    ) -> str:
        """
        Jeżeli nadpisywanie jest wyłączone i plik już istnieje,
        tworzy nazwę np.:

        image.png
        image_2.png
        image_3.png
        """

        if self.overwrite_existing:
            return str(requested_path)

        if not requested_path.exists():
            return str(requested_path)

        parent = requested_path.parent
        stem = requested_path.stem
        suffix = requested_path.suffix

        counter = 2

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"

            if not candidate.exists():
                return str(candidate)

            counter += 1

    # =====================================================
    # Funkcje pomocnicze
    # =====================================================

    @staticmethod
    def _normalize_output_format(
        output_format: str,
    ) -> str:
        if not output_format:
            raise ValueError(
                "Output format cannot be empty."
            )

        normalized_format = (
            output_format
            .strip()
            .lower()
            .lstrip(".")
        )

        if normalized_format == "jpeg":
            normalized_format = "jpg"

        if normalized_format == "heif":
            normalized_format = "heic"

        allowed_formats = {
            "jpg",
            "png",
            "webp",
            "pdf",
            "heic",
        }

        if normalized_format not in allowed_formats:
            raise ValueError(
                f"Unsupported output format: {output_format}"
            )

        return normalized_format

    @staticmethod
    def _normalize_extension_format(
        extension: str,
    ) -> str:
        normalized_extension = (
            extension
            .lower()
            .lstrip(".")
        )

        if normalized_extension == "jpeg":
            return "jpg"

        if normalized_extension == "heif":
            return "heic"

        return normalized_extension

    @staticmethod
    def _check_cancelled(
        cancel_callback: Callable[[], bool] | None,
    ) -> None:
        if cancel_callback and cancel_callback():
            raise ConversionCancelledError(
                "Cancelled by user."
            )