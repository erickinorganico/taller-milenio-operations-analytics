"""Prepare private, oriented copies of inspection and document photos."""
import hashlib
from io import BytesIO
from threading import Lock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps


# Waitress shares this process across request threads on the small VPS.
_decode_lock = Lock()


def prepare_uploaded_photo(upload, *, max_side, quality):
    if not upload:
        return None, ""
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("La foto supera 5 MB. Elige una copia más pequeña.")
    upload.seek(0)
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    try:
        with _decode_lock, Image.open(upload) as original:
            if (original.format not in {"JPEG", "PNG", "WEBP"}
                    or original.width * original.height > 20_000_000
                    or getattr(original, "n_frames", 1) != 1):
                raise ValidationError("Sube una foto fija JPG, PNG o WebP de hasta 20 megapíxeles.")
            original.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            image = ImageOps.exif_transpose(original)
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                image = Image.new("RGB", rgba.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = image.convert("RGB")
            image.info.clear()
            output = BytesIO()
            image.save(output, format="JPEG", quality=quality)
    except (ValueError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("No se pudo leer la foto. Usa JPG, PNG o WebP. En iPhone puedes elegir el formato Más compatible.") from exc
    return ContentFile(output.getvalue(), name=f"{uuid4().hex}.jpg"), digest.hexdigest()
