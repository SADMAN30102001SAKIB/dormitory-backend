import base64
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """
    A Django REST Framework field for handling image-uploads, encoded in base64.
    """

    def to_internal_value(self, data):
        # Check if the base64 string is empty
        if data == "":
            return None

        # Check if this is a base64 string
        if isinstance(data, str) and data.startswith("data:image"):
            # base64 encoded image - decode
            try:
                format, imgstr = data.split(";base64,")  # format ~= data:image/X,
                ext = format.split("/")[-1]  # guess file extension
                id = uuid.uuid4()
                data = ContentFile(
                    base64.b64decode(imgstr), name=id.urn[9:] + "." + ext
                )
            except Exception:
                raise serializers.ValidationError("Invalid image.")
        return super().to_internal_value(data)
