import os
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageOps

from backend.exceptions import (
    ConversionCancelledError,
    ImageMergeError,
    NoSupportedImagesError,
    OutputFileError,
)
from backend.formats import (
    SUPPORTED_IMAGE_EXTENSIONS,
    get_file_extension,
)


class PdfService:
    """
    Obsługuje tworzenie jednego dokumentu PDF z wielu obrazów.

    Każdy obraz zostaje zapisany jako osobna strona PDF.
    Obsługiwane są formaty JPG, JPEG, PNG, WEBP, HEIC i HEIF.
    """

    def __init__(
        self,
        overwrite_existing: bool = False,
        default_resolution: float = 100.0,
    ):
        if default_resolution <= 0:
            raise ValueError(
                "PDF resolution must be greater than zero."
            )

        self.overwrite_existing = overwrite_existing
        self.default_resolution = default_resolution

    def merge_images(
        self,
        image_paths: list[str],
        output_path: str | None = None,
        cancel_callback: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> str:
        """
        Łączy wiele obrazów w jeden dokument PDF.

        Args:
            image_paths:
                Lista ścieżek do obrazów. Kolejność plików
                odpowiada kolejności stron w pliku PDF.

            output_path:
                Ścieżka zapisu PDF. Jeżeli nie zostanie podana,
                plik otrzyma nazwę pierwszego obrazu z dopiskiem
                "_merged.pdf".

            cancel_callback:
                Opcjonalna funkcja zwracająca True, gdy operacja
                powinna zostać anulowana.

            progress_callback:
                Opcjonalna funkcja przyjmująca:
                liczba przygotowanych obrazów, liczba wszystkich obrazów.

            log_callback:
                Opcjonalna funkcja przyjmująca komunikaty tekstowe.

        Returns:
            Ścieżka utworzonego dokumentu PDF.

        Raises:
            NoSupportedImagesError:
                Gdy nie przekazano żadnych obsługiwanych obrazów.

            ConversionCancelledError:
                Gdy operacja została anulowana.

            OutputFileError:
                Gdy nie udało się utworzyć pliku wynikowego.

            ImageMergeError:
                Gdy nie udało się otworzyć lub przetworzyć obrazu.
        """

        valid_paths = self._validate_image_paths(
            image_paths
        )

        if output_path is None:
            output_path = self._create_default_output_path(
                valid_paths[0]
            )
        else:
            output_path = self._prepare_output_path(
                output_path
            )

        total = len(valid_paths)
        prepared_images: list[Image.Image] = []

        try:
            for index, image_path in enumerate(
                valid_paths,
                start=1,
            ):
                self._check_cancelled(
                    cancel_callback
                )

                if log_callback:
                    log_callback(
                        f"[{index}/{total}] Preparing: "
                        f"{os.path.basename(image_path)}"
                    )

                prepared_image = self._load_image_for_pdf(
                    image_path
                )

                prepared_images.append(
                    prepared_image
                )

                if progress_callback:
                    progress_callback(
                        index,
                        total,
                    )

            self._check_cancelled(
                cancel_callback
            )

            if log_callback:
                log_callback(
                    "Saving merged PDF..."
                )

            self._save_pdf(
                images=prepared_images,
                output_path=output_path,
            )

            if log_callback:
                log_callback(
                    f"Created PDF: {output_path}"
                )

            return output_path

        except ConversionCancelledError:
            self._remove_incomplete_file(
                output_path
            )
            raise

        except (
            NoSupportedImagesError,
            OutputFileError,
            ImageMergeError,
        ):
            self._remove_incomplete_file(
                output_path
            )
            raise

        except Exception as error:
            self._remove_incomplete_file(
                output_path
            )

            raise ImageMergeError(
                f"Failed to merge images into PDF: {error}"
            ) from error

        finally:
            for image in prepared_images:
                try:
                    image.close()
                except Exception:
                    pass

    # =====================================================
    # Walidacja plików wejściowych
    # =====================================================

    def _validate_image_paths(
        self,
        image_paths: list[str],
    ) -> list[str]:
        if not image_paths:
            raise NoSupportedImagesError(
                "No image files were selected."
            )

        valid_paths: list[str] = []
        invalid_files: list[str] = []

        for image_path in image_paths:
            if not image_path:
                continue

            normalized_path = os.path.abspath(
                os.path.normpath(image_path)
            )

            extension = get_file_extension(
                normalized_path
            )

            if extension not in SUPPORTED_IMAGE_EXTENSIONS:
                invalid_files.append(
                    os.path.basename(normalized_path)
                )
                continue

            if not os.path.isfile(normalized_path):
                invalid_files.append(
                    os.path.basename(normalized_path)
                )
                continue

            valid_paths.append(
                normalized_path
            )

        if not valid_paths:
            raise NoSupportedImagesError(
                "No supported image files were selected."
            )

        if invalid_files:
            invalid_names = ", ".join(
                invalid_files[:5]
            )

            if len(invalid_files) > 5:
                invalid_names += (
                    f", ... +{len(invalid_files) - 5} more"
                )

            raise NoSupportedImagesError(
                "Some selected files are missing or unsupported: "
                f"{invalid_names}"
            )

        return valid_paths

    # =====================================================
    # Przygotowanie obrazów
    # =====================================================

    def _load_image_for_pdf(
        self,
        image_path: str,
    ) -> Image.Image:
        try:
            with Image.open(image_path) as source_image:
                source_image.load()

                corrected_image = ImageOps.exif_transpose(
                    source_image
                )

                try:
                    return self._convert_to_rgb(
                        corrected_image
                    )
                finally:
                    if corrected_image is not source_image:
                        corrected_image.close()

        except Exception as error:
            raise ImageMergeError(
                f"Failed to open image "
                f"'{os.path.basename(image_path)}': {error}"
            ) from error

    @staticmethod
    def _convert_to_rgb(
        image: Image.Image,
    ) -> Image.Image:
        """
        Przygotowuje obraz do zapisu w PDF.

        Przezroczyste obszary są nakładane na białe tło,
        ponieważ PDF zapisywany przez Pillow używa obrazów RGB.
        """

        if PdfService._has_transparency(image):
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
    def _has_transparency(
        image: Image.Image,
    ) -> bool:
        if image.mode in {"RGBA", "LA"}:
            return True

        if image.mode == "P":
            return "transparency" in image.info

        return False

    # =====================================================
    # Zapisywanie PDF
    # =====================================================

    def _save_pdf(
        self,
        images: list[Image.Image],
        output_path: str,
    ) -> None:
        if not images:
            raise NoSupportedImagesError(
                "There are no prepared images to save."
            )

        first_image = images[0]
        remaining_images = images[1:]

        try:
            first_image.save(
                output_path,
                format="PDF",
                save_all=True,
                append_images=remaining_images,
                resolution=self.default_resolution,
            )

        except PermissionError as error:
            raise OutputFileError(
                "The PDF could not be saved. "
                "The file may be open in another program "
                "or the application does not have permission "
                "to write to this folder."
            ) from error

        except OSError as error:
            raise OutputFileError(
                f"Failed to save PDF: {error}"
            ) from error

        if not os.path.isfile(output_path):
            raise OutputFileError(
                "The output PDF was not created."
            )

    # =====================================================
    # Ścieżka pliku wynikowego
    # =====================================================

    def _create_default_output_path(
        self,
        first_image_path: str,
    ) -> str:
        first_path = Path(
            first_image_path
        )

        requested_path = first_path.with_name(
            f"{first_path.stem}_merged.pdf"
        )

        return self._resolve_output_path(
            requested_path
        )

    def _prepare_output_path(
        self,
        output_path: str,
    ) -> str:
        normalized_path = Path(
            os.path.abspath(
                os.path.normpath(output_path)
            )
        )

        if normalized_path.suffix.lower() != ".pdf":
            normalized_path = normalized_path.with_suffix(
                ".pdf"
            )

        parent_directory = normalized_path.parent

        if not parent_directory.exists():
            try:
                parent_directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )
            except OSError as error:
                raise OutputFileError(
                    "Failed to create the output directory: "
                    f"{parent_directory}"
                ) from error

        return self._resolve_output_path(
            normalized_path
        )

    def _resolve_output_path(
        self,
        requested_path: Path,
    ) -> str:
        if self.overwrite_existing:
            return str(requested_path)

        if not requested_path.exists():
            return str(requested_path)

        parent = requested_path.parent
        stem = requested_path.stem
        suffix = requested_path.suffix

        counter = 2

        while True:
            candidate = (
                parent
                / f"{stem}_{counter}{suffix}"
            )

            if not candidate.exists():
                return str(candidate)

            counter += 1

    # =====================================================
    # Anulowanie i sprzątanie
    # =====================================================

    @staticmethod
    def _check_cancelled(
        cancel_callback: Callable[[], bool] | None,
    ) -> None:
        if cancel_callback and cancel_callback():
            raise ConversionCancelledError(
                "Cancelled by user."
            )

    @staticmethod
    def _remove_incomplete_file(
        output_path: str,
    ) -> None:
        if not output_path:
            return

        try:
            if os.path.isfile(output_path):
                os.remove(output_path)
        except OSError:
            pass