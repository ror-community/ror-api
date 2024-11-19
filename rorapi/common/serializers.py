from rest_framework import serializers


class OrganizationRelationshipsSerializer(serializers.Serializer):
    label = serializers.CharField()
    type = serializers.CharField()
    id = serializers.CharField()


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    count = serializers.IntegerField()


class ErrorsSerializer(serializers.Serializer):
    errors = serializers.StringRelatedField(many=True)
