from dataclasses import dataclass
from pathlib import Path
from threading import Event

from backend.converter import FileConverter
from backend.exceptions import (
    ConversionCancelledError,
    SameFormatConversionError,
    UnsupportedConversionError,
    UnsupportedInputFormatError,
)


@dataclass
class ConversionResult:
    selected_count: int
    converted_count: int
    skipped_count: int
    failed_count: int
    output_files: list[str]
    errors: list[str]
    cancelled: bool


class ConversionWorker:
    def __init__(
        self,
        converter: FileConverter,
        cancel_event: Event,
    ):
        self.converter = converter
        self.cancel_event = cancel_event

    def run(
        self,
        files: list[str],
        output_format: str,
        on_log=None,
        on_progress=None,
    ) -> ConversionResult:
        converted_count = 0
        skipped_count = 0
        failed_count = 0

        output_files: list[str] = []
        errors: list[str] = []

        total = len(files)

        for index, file_path in enumerate(files, start=1):
            if self.cancel_event.is_set():
                break

            filename = Path(file_path).name

            if on_log:
                on_log(
                    f"[{index}/{total}] Converting: {filename}"
                )

            try:
                outputs = self.converter.convert(
                    input_path=file_path,
                    output_format=output_format,
                    cancel_callback=self.cancel_event.is_set,
                )

                output_files.extend(outputs)
                converted_count += 1

                if on_log:
                    if len(outputs) == 1:
                        on_log(
                            f"Saved: {Path(outputs[0]).name}"
                        )
                    else:
                        on_log(
                            f"Saved {len(outputs)} output file(s)."
                        )

            except ConversionCancelledError:
                self.cancel_event.set()

                if on_log:
                    on_log("Conversion cancelled.")

                break

            except (
                UnsupportedConversionError,
                UnsupportedInputFormatError,
                SameFormatConversionError,
            ) as error:
                skipped_count += 1
                errors.append(
                    f"{filename}: {error}"
                )

                if on_log:
                    on_log(
                        f"Skipped: {error}"
                    )

            except Exception as error:
                failed_count += 1
                errors.append(
                    f"{filename}: {error}"
                )

                if on_log:
                    on_log(
                        f"Failed: {error}"
                    )

            if on_progress:
                on_progress(
                    index,
                    total,
                )

        return ConversionResult(
            selected_count=total,
            converted_count=converted_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            output_files=output_files,
            errors=errors,
            cancelled=self.cancel_event.is_set(),
        )