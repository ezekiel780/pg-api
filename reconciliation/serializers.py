from django.conf import settings
from rest_framework import serializers


class ReconcileSerializer(serializers.Serializer):
    file_a = serializers.FileField()
    file_b = serializers.FileField()

    def validate_file_a(self, file):
        return self._validate_csv_file(file, field_name="file_a")

    def validate_file_b(self, file):
        return self._validate_csv_file(file, field_name="file_b")

    def validate(self, data):
        file_a = data.get("file_a")
        file_b = data.get("file_b")
        if file_a and file_b:
            if file_a.name == file_b.name and file_a.size == file_b.size:
                raise serializers.ValidationError(
                    "file_a and file_b appear to be the same file. "
                    "Please upload one CSV from each source system."
                )

        return data

    def _validate_csv_file(self, file, field_name: str):
        """
        Run all single-file validations and raise field-keyed errors.

        Checks (in order):
          1. File must not be empty.
          2. File extension must be .csv (case-insensitive).
          3. File size must not exceed MAX_UPLOAD_SIZE from settings.
        """
        if file.size == 0:
            raise serializers.ValidationError(
                f"{field_name} is empty (0 bytes). Please upload a valid CSV file."
            )
        
        if not file.name.lower().endswith(".csv"):
            raise serializers.ValidationError(
                f"{field_name} must be a CSV file (.csv). "
                f"Received: '{file.name}'"
            )

        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 500 * 1024 * 1024)

        if file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = file.size / (1024 * 1024)
            raise serializers.ValidationError(
                f"{field_name} is too large ({actual_mb:.1f} MB). "
                f"Maximum allowed size is {max_mb:.0f} MB."
            )

        return file
    