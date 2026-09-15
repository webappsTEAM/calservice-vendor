"""
Tests for proof-photo upload validation (_validate_photo_upload).

Regression cover for the defect where every stored pre- and post-service photo
in this deployment was the same 6158-byte solid-black 1280x720 JPEG: the
technician app captured frames before the <video> element had decoded one, and
because a blank frame is a structurally valid JPEG, neither the extension check
nor the Content-Type check could see anything wrong with it.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .views import _validate_photo_upload


def _jpeg(size=(1280, 720), colour=(0, 0, 0), name="photo.jpg"):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "JPEG", quality=92)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def _textured_jpeg(name="photo.jpg"):
    """A JPEG with real variation in it, standing in for an actual photo."""
    from PIL import Image
    image = Image.new("RGB", (640, 480))
    pixels = image.load()
    for y in range(480):
        for x in range(0, 640, 8):
            shade = (x * 255) // 640
            for dx in range(8):
                if x + dx < 640:
                    pixels[x + dx, y] = (shade, 120, 255 - shade)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=92)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class PhotoUploadValidationTests(TestCase):
    def test_rejects_the_solid_black_frame(self):
        error = _validate_photo_upload(_jpeg())
        self.assertIsNotNone(error)
        self.assertIn("blank", error.lower())

    def test_accepts_a_real_photo(self):
        self.assertIsNone(_validate_photo_upload(_textured_jpeg()))

    def test_accepts_a_dim_photo_with_a_highlight(self):
        """A dark room is not a blank frame -- this must not false-positive."""
        from PIL import Image
        image = Image.new("RGB", (640, 480), (6, 6, 8))
        pixels = image.load()
        for y in range(200, 260):
            for x in range(300, 380):
                pixels[x, y] = (95, 88, 70)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=92)
        upload = SimpleUploadedFile("dim.jpg", buffer.getvalue(), content_type="image/jpeg")
        self.assertIsNone(_validate_photo_upload(upload))

    def test_rejects_non_image_bytes_disguised_as_jpeg(self):
        upload = SimpleUploadedFile(
            "disguised.jpg", b"<script>alert(document.cookie)</script>", content_type="image/jpeg",
        )
        error = _validate_photo_upload(upload)
        self.assertIsNotNone(error)
        self.assertIn("not a readable image", error)

    def test_rejects_disallowed_extension(self):
        error = _validate_photo_upload(
            SimpleUploadedFile("evil.svg", b"<svg/>", content_type="image/svg+xml")
        )
        self.assertIsNotNone(error)
        self.assertIn("Unsupported file type", error)

    def test_rejects_tiny_image(self):
        error = _validate_photo_upload(_jpeg(size=(32, 32), colour=(120, 120, 120)))
        self.assertIsNotNone(error)
        self.assertIn("too small", error)

    def test_file_pointer_is_left_at_the_start_for_saving(self):
        upload = _textured_jpeg()
        _validate_photo_upload(upload)
        self.assertEqual(upload.tell(), 0)

    def test_none_is_allowed(self):
        self.assertIsNone(_validate_photo_upload(None))
