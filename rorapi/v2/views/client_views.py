from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models.client import Client
from ..serializers.client_serializers import ClientSerializer
from django.core.mail import send_mail
from django.utils.timezone import now

class ClientRegistrationView(APIView):
    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()
            send_mail(
                'Your ROR API Client ID',
                f'Thank you for registering. Your Client ID is: {client.client_id}',
                'support@ror.org',
                [client.email],
                fail_silently=False,
            )
            return Response({'client_id': client.client_id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ValidateClientView(APIView):
    def get(self, request, client_id):
        client_exists = Client.objects.filter(client_id=client_id).exists()
        return Response({'valid': client_exists}, status=status.HTTP_200_OK)
