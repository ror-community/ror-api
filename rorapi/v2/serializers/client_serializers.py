from rest_framework import serializers
from ..models.client import Client

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['email']
