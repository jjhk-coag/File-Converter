class ConverterError(Exception):
    """Bazowy wyjątek dla błędów aplikacji File Converter."""


class UnsupportedInputFormatError(ConverterError):
    """Plik wejściowy ma nieobsługiwany format."""


class UnsupportedConversionError(ConverterError):
    """Wybrana konwersja pomiędzy formatami nie jest obsługiwana."""


class SameFormatConversionError(ConverterError):
    """Plik wejściowy jest już zapisany w wybranym formacie."""


class EmptyPdfError(ConverterError):
    """Plik PDF nie zawiera żadnych stron."""


class ConversionCancelledError(ConverterError):
    """Operacja konwersji została anulowana przez użytkownika."""


class OutputFileError(ConverterError):
    """Nie udało się utworzyć lub zapisać pliku wynikowego."""


class InvalidOutputFormatError(ConverterError):
    """Podany format wyjściowy jest nieprawidłowy."""


class ImageMergeError(ConverterError):
    """Nie udało się połączyć obrazów w jeden plik PDF."""


class NoSupportedImagesError(ImageMergeError):
    """Nie wybrano żadnych obsługiwanych plików graficznych."""