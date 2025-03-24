from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.utils.timezone import now
from rorapi.v2.models import Client
from rorapi.v2.serializers import ClientSerializer

# class ClientRegistrationView(APIView):
#     def post(self, request):
#         # Initialize serializer with request data
#         serializer = ClientSerializer(data=request.data)
        
#         # Check if the data is valid
#         if serializer.is_valid():
#             # Save the client instance
#             client = serializer.save()

#             # Send a registration email to the client
#             subject = 'Your ROR API Client ID'
#             message = f'Thank you for registering. Your Client ID is: {client.client_id}'
#             from_email = 'support@ror.org'
#             recipient_list = [client.email]
            
#             send_mail(
#                 subject,
#                 message,
#                 from_email,
#                 recipient_list,
#                 fail_silently=False,
#             )

#             # Return response with client ID
#             return Response({'client_id': client.client_id}, status=status.HTTP_201_CREATED)

#         # Return validation errors if serializer is not valid
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidateClientView(APIView):
    def get(self, request, client_id):
        # Check if the client_id exists in the database
        client_exists = Client.objects.filter(client_id=client_id).exists()

        # Return response indicating whether client ID is valid
        return Response({'valid': client_exists}, status=status.HTTP_200_OK)
