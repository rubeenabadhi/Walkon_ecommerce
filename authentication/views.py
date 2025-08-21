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
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from product.models import Product  # 
from django.views.decorators.cache import never_cache



#user-defined views for signup and OTP verification,home view
def home(request):
    products = Product.objects.all()  # Assuming you have a Product model
    context = {
        'products': products,
    }
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
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(request, username=email, password=password)
        # If you use custom user with EMAIL as USERNAME_FIELD, then 'username=email' is correct

        if user is not None:
            if user.is_active and not user.is_staff and not user.is_superuser:
                auth.login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Only normal users can log in here.")
                return redirect('login')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('login')

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
@login_required(login_url='admin_login' or 'login')
@never_cache
def logout_view(request):  
    # Save whether the current user is staff before logging them out
    was_staff = request.user.is_staff
    auth.logout(request)
    if was_staff :
        # Redirect to admin login page
        return redirect('admin_login')
    else:
        # Redirect to home page
        return redirect('home')

# Admin User Management


@staff_member_required
def admin_user_management(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    # ---- SEARCH ----
    query = request.GET.get('q')# Get search query from GET request
    if query:
        users = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) | 
            Q(is_active__in=[True if query.lower() == "active" else False if query.lower() == "blocked" else None])
        , is_staff=False, is_superuser=False).order_by('-date_joined')    
    else:
        users = CustomUser.objects.filter(is_staff=False,is_superuser=False).order_by('-date_joined')  # Latest first

    # ---- PAGINATION ----
    paginator = Paginator(users, 2)  # 2 users per page
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    context = {
        "users": users,
        "query": query,
    }
    return render(request, "admin/user_management.html", context)

# active or inactive user 
@staff_member_required
@require_POST
def toggle_user_status(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({"success": True, "is_active": user.is_active})
    return JsonResponse({"success": False, "error": "Invalid request"})