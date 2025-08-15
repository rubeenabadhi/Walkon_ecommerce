import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth import login
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib import auth

#user-defined views for signup and OTP verification,home view
def home(request):
    return render(request, 'user/index.html')
def signup(request):
    if request.method == 'POST':
        username=request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('password2')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('signup')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('signup')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('signup')

        # Generate 6-digit OTP
        otp = random.randint(100000, 999999)

        # Store in session temporarily
        request.session['signup_email'] = email #email for OTP verification
        request.session['signup_username'] = username
        request.session['signup_password'] = password
        request.session['signup_otp'] = str(otp) # convert to string for easy comparison

        # Send OTP via email
        send_mail(
            "Your OTP Code",
            f"Your OTP is {otp}. It is valid for 5 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False, # Fail silently if email sending fails
        )

        messages.success(request, f'OTP sent to {email}.')
        return redirect('verify_otp')

    return render(request, 'signup.html')


def verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('signup_otp')
        if not session_otp:
            messages.error(request, 'Session expired. Please sign up again.')
            return redirect('signup')
        if not entered_otp:
            messages.error(request, 'Please enter the OTP.')
            return redirect('verify_otp')
        if len(entered_otp) != 6 or not entered_otp.isdigit():
            messages.error(request, 'Invalid OTP format. Please enter a 6-digit number.')
            return redirect('verify_otp')
        # Get email and password from session
        username = request.session.get('signup_username')
        email = request.session.get('signup_email')
        password = request.session.get('signup_password')

        if entered_otp == session_otp:
            # Create user
            user = CustomUser.objects.create_user(username=username, email=email, password=password)
            user.is_active = True
            user.save()

            messages.success(request, 'Account created successfully! You can now log in.')

            # Clear session
            request.session.flush()

            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp')

    return render(request, 'otp_signup.html')
def resend_otp(request):
    email = request.session.get('signup_email')
    if email:
        otp = random.randint(100000, 999999)
        request.session['signup_otp'] = str(otp)

        send_mail(
            "Your OTP Code",
            f"Your new OTP is {otp}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        messages.success(request, "New OTP sent to your email.")
    else:
        messages.error(request, "No email found in session.")
        return redirect('signup')

    return redirect('verify_otp')
def user_login(request):
    if request.method=='POST':
        email=request.POST['email']
        password= request.POST['password']
        user= auth.authenticate(email=email,password=password,is_active=True,is_staff=False, is_superuser=False)
        print(user)
        if user is not None:
            auth.login(request,user)
            return redirect('home')
        else:
            messages.info(request,'Invalid details')
            return redirect('user_login')
    return render(request, 'user/user_login.html')

def forgot_password_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email) 
            otp = random.randint(100000, 999999)
            request.session['reset_email'] = email
            request.session['reset_otp'] = str(otp)

            send_mail(
                'Password Reset OTP',
                f'Your OTP is {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
            return redirect('verify_reset_otp')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Email not found')
    return render(request, 'user/forgot_password.html')
# Step 2: Verify OTP
def verify_reset_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('reset_otp'):
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP')
    return render(request, 'user/otp_forgotpassword.html')
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return redirect('reset_password')

        email = request.session.get('reset_email')
        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            print("Password reset successfully")
            messages.success(request, 'Password reset successfully')
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found')
    return render(request, 'user/reset_password.html')

#admin login view

def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:  # Check if admin/staff
                print("Admin logged in")
                return redirect('dashboard')  # Django admin dashboard
            else:
                return redirect('home')  # Your normal user homepage
        else:
            messages.error(request, "Invalid username or password")
            return redirect('admin_login')

    return render(request, "admin/admin_login.html")

#logut view
def logout_view(request):
    
    # Save whether the current user is staff before logging them out
    was_staff = request.user.is_staff

    auth.logout(request)

    if was_staff:
        # Redirect to admin login page
        return redirect('admin_login')
    else:
        # Redirect to home page
        return redirect('home')



    