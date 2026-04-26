from rest_framework import serializers

class ReconcileSerializer(serializers.Serializer):
    file_a = serializers.FileField()
    file_b = serializers.FileField()

    def validate(self, data):
        file_a = data.get("file_a")
        file_b = data.get("file_b")

        if not file_a.name.endswith(".csv"):
            raise serializers.ValidationError("file_a must be CSV")

        if not file_b.name.endswith(".csv"):
            raise serializers.ValidationError("file_b must be CSV")

        return data
       