"""Preprocesador de imágenes de facturas — Spec-17.

Valida y normaliza imágenes antes de enviarlas a los agentes multimodales.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Union

from PIL import Image, ImageOps, UnidentifiedImageError

# Límites
_MAX_INPUT_BYTES = 20 * 1024 * 1024   # 20 MB
_MAX_API_BYTES = 4 * 1024 * 1024      # 4 MB (límite Vertex / Anthropic)
_MIN_DIMENSION_PX = 300
_BLANK_PIXEL_RATIO = 0.98              # >98% píxeles uniformes = imagen en blanco/negro

_ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "TIFF"}
_JPEG_QUALITY = 92


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class ImagePreprocessorError(Exception):
    """Base para errores del preprocesador."""


class ImageFormatError(ImagePreprocessorError):
    """Formato de imagen no soportado."""


class ImageCorruptError(ImagePreprocessorError):
    """Archivo corrupto o no decodificable."""


class ImageTooLargeError(ImagePreprocessorError):
    """Archivo supera el límite de 20 MB."""


class ImageTooSmallError(ImagePreprocessorError):
    """Imagen menor a 300×300 px."""


class ImageBlankError(ImagePreprocessorError):
    """Imagen completamente en blanco o negro."""


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class ProcessedImage:
    image_bytes: bytes
    image_base64: str
    mime_type: str          # siempre "image/jpeg" tras el preprocesamiento
    width_px: int
    height_px: int
    size_bytes: int
    was_resized: bool
    was_rotated: bool
    was_converted: bool
    quality_score: float    # 0.0-1.0


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class ImagePreprocessor:
    """Valida, convierte y normaliza imágenes para los agentes multimodales."""

    def process(
        self,
        source: Union[str, bytes],
        mime_type: str = "image/jpeg",
    ) -> ProcessedImage:
        """Procesa una imagen y retorna un ProcessedImage listo para APIs.

        Args:
            source: Path de archivo (str) o bytes crudos.
            mime_type: Tipo MIME declarado por el uploader.

        Returns:
            ProcessedImage con la imagen normalizada.

        Raises:
            ImageFormatError, ImageCorruptError, ImageTooLargeError,
            ImageTooSmallError, ImageBlankError
        """
        raw_bytes = self._load_bytes(source)
        self._check_size(raw_bytes)

        img, detected_format, was_rotated = self._open_and_rotate(raw_bytes)
        self._check_dimensions(img)
        self._check_blank(img)

        was_converted = detected_format not in {"JPEG"}
        final_bytes, was_resized = self._convert_and_resize(img)

        quality = self._quality_score(img)

        b64 = base64.b64encode(final_bytes).decode("ascii")

        return ProcessedImage(
            image_bytes=final_bytes,
            image_base64=b64,
            mime_type="image/jpeg",
            width_px=img.width,
            height_px=img.height,
            size_bytes=len(final_bytes),
            was_resized=was_resized,
            was_rotated=was_rotated,
            was_converted=was_converted,
            quality_score=quality,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _load_bytes(source: Union[str, bytes]) -> bytes:
        if isinstance(source, bytes):
            return source
        with open(source, "rb") as f:
            return f.read()

    @staticmethod
    def _check_size(raw_bytes: bytes) -> None:
        if len(raw_bytes) > _MAX_INPUT_BYTES:
            raise ImageTooLargeError(
                f"Archivo de {len(raw_bytes) / 1024 / 1024:.1f} MB supera el límite de 20 MB"
            )

    @staticmethod
    def _open_and_rotate(raw_bytes: bytes):
        """Abre la imagen con Pillow, valida formato y corrige rotación EXIF."""
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            img.verify()  # verifica integridad sin cargar píxeles completos
        except (UnidentifiedImageError, Exception) as exc:
            raise ImageCorruptError(f"No se pudo decodificar la imagen: {exc}") from exc

        # Reabrir después de verify() (PIL invalida el objeto tras verify)
        img = Image.open(io.BytesIO(raw_bytes))

        fmt = (img.format or "").upper()
        if fmt not in _ACCEPTED_FORMATS:
            raise ImageFormatError(
                f"Formato '{fmt}' no soportado. Aceptados: {', '.join(_ACCEPTED_FORMATS)}"
            )

        # Corregir orientación EXIF
        was_rotated = False
        try:
            rotated = ImageOps.exif_transpose(img)
            if rotated is not img:
                was_rotated = True
            img = rotated
        except Exception:
            pass  # Si falla el EXIF transpose, continuar sin rotar

        # Convertir a RGB (elimina canal alpha o modos especiales)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        return img, fmt, was_rotated

    @staticmethod
    def _check_dimensions(img: Image.Image) -> None:
        if img.width < _MIN_DIMENSION_PX or img.height < _MIN_DIMENSION_PX:
            raise ImageTooSmallError(
                f"Imagen de {img.width}×{img.height} px es menor al mínimo de "
                f"{_MIN_DIMENSION_PX}×{_MIN_DIMENSION_PX} px"
            )

    @staticmethod
    def _check_blank(img: Image.Image) -> None:
        """Rechaza imágenes donde >98% de los píxeles son uniformes."""
        # Muestreo: thumbnail de 100×100 para eficiencia
        thumb = img.copy()
        thumb.thumbnail((100, 100))
        pixels = list(thumb.getdata())
        if not pixels:
            return
        # Tomar canal R para simplicidad
        if isinstance(pixels[0], (list, tuple)):
            channel = [p[0] for p in pixels]
        else:
            channel = list(pixels)
        total = len(channel)
        most_common = max(set(channel), key=channel.count)
        ratio = channel.count(most_common) / total
        if ratio >= _BLANK_PIXEL_RATIO:
            raise ImageBlankError(
                f"Imagen parece estar en blanco/negro uniforme "
                f"({ratio*100:.0f}% píxeles con valor {most_common})"
            )

    @staticmethod
    def _convert_and_resize(img: Image.Image):
        """Convierte a JPEG y hace resize si supera 4 MB."""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        jpeg_bytes = buf.getvalue()
        was_resized = False

        if len(jpeg_bytes) > _MAX_API_BYTES:
            # Reducir resolución proporcionalmente hasta que quepa
            scale = (_MAX_API_BYTES / len(jpeg_bytes)) ** 0.5
            new_w = max(int(img.width * scale), _MIN_DIMENSION_PX)
            new_h = max(int(img.height * scale), _MIN_DIMENSION_PX)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
            jpeg_bytes = buf.getvalue()
            was_resized = True

            # Segunda pasada si aún es grande (imagen muy densa)
            if len(jpeg_bytes) > _MAX_API_BYTES:
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75, optimize=True)
                jpeg_bytes = buf.getvalue()

        return jpeg_bytes, was_resized

    @staticmethod
    def _quality_score(img: Image.Image) -> float:
        """Estima legibilidad como 1 - ratio de píxeles uniformes en el centro."""
        try:
            w, h = img.size
            cx, cy = w // 2, h // 2
            region_size = min(w, h) // 3
            region = img.crop((
                max(0, cx - region_size),
                max(0, cy - region_size),
                min(w, cx + region_size),
                min(h, cy + region_size),
            ))
            thumb = region.copy()
            thumb.thumbnail((50, 50))
            pixels = list(thumb.getdata())
            if not pixels:
                return 1.0
            if isinstance(pixels[0], (list, tuple)):
                channel = [p[0] for p in pixels]
            else:
                channel = list(pixels)
            total = len(channel)
            most_common = max(set(channel), key=channel.count)
            ratio = channel.count(most_common) / total
            return round(1.0 - ratio, 3)
        except Exception:
            return 1.0
