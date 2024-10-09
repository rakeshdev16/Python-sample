from django.db import transaction
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from utility.helpers import success, error
from utility.fast_api import call_auth_microservice
from utility.emailTemplates import send_verify_email, send_forgot_password_email

from .models import CustomUser
from .serializers import CustomUserSerializer
from .permission import IsTokenValid
from employee.models import InviteEmployee, Employee
from office.models import OfficeEmployee, Company, CompanyRole

# Define Django views that communicate with FastAPI endpoints

class RegisterUser(APIView):
    """
    API endpoint for user registration.
    """
    def post(self, request):
        data = request.data

        if not 'first_name' in data and not 'last_name' in data:
            # Name is required
            return Response(error("First Name and Last Name is required", {}), status=status.HTTP_400_BAD_REQUEST)
        
        if not 'email' in data:
            # Email is required
            return Response(error("Email is required", {}), status=status.HTTP_400_BAD_REQUEST)
        
        if data.get('password') != data.get('confirm_password'):
            # Password should same to confirm password
            return Response(error("confirm password does not match password", {}), status=status.HTTP_400_BAD_REQUEST)
        
        #hit request to auth microservice
        response = call_auth_microservice('/signup', data)
        # Check if the response is successful
        if response.status_code == 200:
            response_data = response.json()
            user_id = response_data.get('id')
            email = response_data.get('email')
            first_name = data.get('first_name')
            last_name = data.get('last_name')

            #create user wih response User-ID.
            user, created = CustomUser.objects.update_or_create(user_id=user_id,
                                                                defaults={
                                                                        'email': email,
                                                                        'first_name': first_name,
                                                                        'last_name': last_name,
                                                                        'is_onboarding':True
                                                                    })

            # Send OTP to user for email verification
            send_verify_email('Confirm your email', [response_data.get('email')],
                              response_data.get('otp'), response_data.get('first_name'))

            # Registration Successful
            return Response(success("Registration Successful", {}), status=status.HTTP_200_OK)
        else:
            # Return error from the authentication microservice
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)


class VerifyEmail(APIView):
    """
    API endpoint for verifying user email.
    """
    def post(self, request):
        data = request.data
        data = data.copy()
        data['type'] = 'verify'
        if not 'otp' in data:
            # Otp is required
            return Response(error("Otp is required.", {}), status=status.HTTP_400_BAD_REQUEST)
        
        if not 'email' in data:
            # Email is required
            return Response(error("Email is required", {}), status=status.HTTP_400_BAD_REQUEST)

        #hit request to auth microservice
        response = call_auth_microservice('/verify-otp', data)

        # Check if the response is successful
        if response.status_code == 200:
            response_data = response.json()
            message = response_data.get('message')
            # Registration Successful
            return Response(success(message, {}), status=status.HTTP_200_OK)
        else:
            # Return error from the authentication microservice
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)
        

class VerifyOtp(APIView):
    """
    API endpoint for verifying user email.
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        data = data.copy()
        type = self.kwargs.get('type')
        data['type'] = type
        
        if not 'otp' in data:
            # Otp is required
            return Response(error("Otp is required.", {}), status=status.HTTP_400_BAD_REQUEST)
        
        if not 'email' in data:
            # Email is required
            return Response(error("Email is required", {}), status=status.HTTP_400_BAD_REQUEST)

        #hit request to auth microservice
        response = call_auth_microservice('/verify-otp', data)

        # Check if the response is successful
        if response.status_code == 200:
            response_data = response.json()
            message = response_data.get('message')
            # Registration Successful
            return Response(success(message, {}), status=status.HTTP_200_OK)
        else:
            # Return error from the authentication microservice
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)


class Login(APIView):
    """
    API endpoint for user login.
    """
    def post(self, request):
        data = request.data

        if not 'password' in data:
            # password is required
            return Response(error("Password is required.", {}), status=status.HTTP_400_BAD_REQUEST)
        
        if not 'email' in data:
            # Email is required
            return Response(error("Email is required", {}), status=status.HTTP_400_BAD_REQUEST)

        #hit request to auth microservice
        response = call_auth_microservice('/login', data)
        
        # Check if the response is successful
        if response.status_code == 200:
            response_data = response.json()
            user_id = response_data['user']['id']
            email = response_data['user']['email']
            user, created = CustomUser.objects.get_or_create(
                user_id=user_id,  # Lookup field
                defaults={'email': email}  # Field to set if the object is created
            )
            
            user_serliaze_data = CustomUserSerializer(user)
            response_data['user']=user_serliaze_data.data
            
            # Registration Successful
            return Response(success("Login sucessfully", response_data), status=status.HTTP_200_OK)
        else:
            # Return error from the authentication microservice
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)
        

class ChangePassword(APIView):
    """
    API endpoint for change user password.
    """
    permission_classes = (IsTokenValid,)
    
    def post(self, request):
        data = request.data
        # Extract token from the request header
        token = request.headers.get('Authorization', '').split(' ')[-1]
        
        # Prepare data for the change password request
        data = {
            'old_password': data.get('old_password'),
            'new_password': data.get('new_password'),
            'confirm_password': data.get('confirm_password')
        }
        
        # Make a POST request to the FastAPI microservice
        response = call_auth_microservice('/change-password', data, token)
        
        # Check the response from the FastAPI microservice
        if response.status_code == 200:
            response_data = response.json()
            message = response_data.get('message')
            # Change password successfully Successful
            return Response(success(message, {}), status=status.HTTP_200_OK)
        else:
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)


class SendOtp(APIView):
    """
    API endpoint for send otp to the user for
    reset his password.
    """

    def post(self, request, *args, **kwargs):
        data = request.data
        otp_type = self.kwargs.get('type')

        # Prepare data for the change password request
        data = {
            'email': data.get('email'),
            'type': otp_type
        }
        
        # Make a POST request to the FastAPI microservice
        response = call_auth_microservice('/send-otp', data)
        
        # Check the response from the FastAPI microservice
        if response.status_code == 200:
            response_data = response.json()
            email = response_data.get('email')
            otp = response_data.get('otp')
            first_name = response_data.get('first_name')

            if otp_type == 'forgot':
                # Send OTP to user for reset password.
                send_forgot_password_email('Forgot password', [email],
                                otp, first_name)
                
            elif otp_type == "verify":
                # Send OTP to user for email verification
                send_verify_email('Confirm your email', [response_data.get('email')],
                              response_data.get('otp'), response_data.get('first_name'))

            # Otp send successfully 
            return Response(success("Otp send successfully", {}), status=status.HTTP_200_OK)
        else:
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)
        

class ForgotPassword(APIView):
    """
    API endpoint for change user password with otp.
    """
    def post(self, request):
        data = request.data
        # Prepare data for the change password request
        data = {
            'email': str(data.get('email')),
            'password': str(data.get('password')),
            'confirm_password': str( data.get('confirm_password'))
        }
        
        # Make a POST request to the FastAPI microservice
        response = call_auth_microservice('/reset-password', data)
        
        # Check the response from the FastAPI microservice
        if response.status_code == 200:
            response_data = response.json()
            message = response_data.get('message')
            # Change password successfully Successful
            return Response(success(message, {}), status=status.HTTP_200_OK)
        else:
            error_message = response.json().get('detail', 'Unknown error')
            return Response(error(error_message, {}), status=response.status_code)
    

class SetupAccount(APIView):
    
    def post(self, request, *args, **kwargs):
        
        data = request.data.copy()
        # get invite employee objet
        invite_token = request.query_params.get('token')
        
        with transaction.atomic():        
            invite_employe = InviteEmployee.objects.filter(token=invite_token).first()
            invite_employe.status = "accepted"
            invite_employe.save()
            if invite_employe:
                email = invite_employe.recipient_email
            
                data['email'] = email
                data['email_verified'] = True
                #hit request to auth microservice
                response = call_auth_microservice('/signup', data)

                print(data, "datadatadata")
                # Check if the response is successful
                if response.status_code == 200:
                    response_data = response.json()
                    user_id = response_data.get('id')
                    email = response_data.get('email')
                    
                    try:
                        with transaction.atomic():
                            #create user wih response User-ID.
                            user = CustomUser.objects.create(user_id=user_id,
                                                             role="user",
                                                             email=email,
                                                             first_name = data['first_name'],
                                                             last_name = data['last_name'],
                                                             phone_number = data['phone_number']
                                                             )
                            
                            # get or create employee obj with company
                            employee, created = Employee.objects.get_or_create(user=user, company=invite_employe.sender.company)
                            employee.role = invite_employe.role
                            # employee.company = invite_employe.sender.company
                            employee.save()
                            
                            # assign employee to office
                            OfficeEmployee.objects.get_or_create(employee=employee, office=invite_employe.sender)
                            
                            # set-up sucessfully
                            return Response(success("Account Set-up Successfully", {}), status=status.HTTP_200_OK)
                    except Exception as e:
                        return Response(error("Something went wrong while setu-up account", {}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    # Return error from the authentication microservice
                    error_message = response.json().get('detail', 'Unknown error')
                    return Response(error(error_message, {}), status=response.status_code)
            else:
                return Response(error("Invalid invitation", {}), status=status.HTTP_401_UNAUTHORIZED)
        

class UserDeleteView(APIView):
    queryset = CustomUser.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        user = request.user
        user.soft_delete()
        return Response({"success": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
    

class GetUserByEmail(APIView):
    '''
    this api check the user existence based on email
    '''
    
    def post(self, request, *args, **kwargs):
        data = request.data
        # fetch user with email
        if 'email' not in data:
            return Response(error('Email is required', {}), status=status.HTTP_400_BAD_REQUEST)
        try:
            user = CustomUser.objects.get(email=data.get('email'))
            if user:
                return Response(error('User already exist', {}), status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response(success('success', {}), status=status.HTTP_200_OK)
            

class UserDetail(APIView):
    '''
    this api is used to get detail of current user
    '''
    permission_classes = (IsTokenValid,)
    
    def get(self,request,*args, **kwargs):
        user = request.user
        user_serliaze_data = CustomUserSerializer(user)
        return Response(success("success", user_serliaze_data.data), status=status.HTTP_200_OK)