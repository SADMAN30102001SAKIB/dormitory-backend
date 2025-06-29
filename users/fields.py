import base64
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """
    A custom serializer field to handle base64-encoded images.
    """

    def to_internal_value(self, data):
        """
        Decode the base64 string into a file object.
        """
        # Check if the input is a base64 string
        if isinstance(data, str) and data.startswith("data:image"):
            # 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQE...'
            # Get the format and the base64 content
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]

            # Generate a unique filename
            filename = f"{uuid.uuid4()}.{ext}"

            # Decode the base64 string
            data = ContentFile(base64.b64decode(imgstr), name=filename)

        return super().to_internal_value(data)
