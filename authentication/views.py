import random, time
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser
from django.contrib.auth import login
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .forms import EditProfileForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from product.models import Product
from offers.models import Referral
from wallet.models import Wallet, WalletTransaction
from django.views.decorators.csrf import csrf_protect
import logging

user_logger = logging.getLogger('user_logger')
admin_logger=logging.getLogger('admin_logger')
#user-defined views for signup and OTP verification,home view
#=====================HOME VIEW===============================================
def home(request):
    products = Product.objects.all().prefetch_related('variants')
    new_products = Product.objects.all().order_by('-created_at').prefetch_related('variants')

    for product in products:
        for variant in product.variants.all():
            variant.final_price = variant.get_offer_price()
    for product in new_products:
        for variant in product.variants.all():
            variant.final_price = variant.get_offer_price()

    context = {
        'products': products,
        'new_products': new_products
    }
    return render(request, 'user/index.html', context)

#=====================SIGNUP VIEW===============================================
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('password2')
        referrel_code = request.POST.get('referrel_code')

        #  Check passwords match
        if password != confirm_password:
            messages.error(request, ' Passwords do not match.')
            return redirect('signup')

        #  Validate password with Django + custom validators
        try:
            validate_password(password)
        except ValidationError as e:
            for error in e.messages:
                user_logger.error(error) # for logging errors in user_logger 
                messages.error(request, error)
            return redirect('signup')

        #  Check duplicates
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, ' Email already exists.')
            return redirect('signup')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, ' Username already exists.')
            return redirect('signup')
        
        #  Generate 6-digit OTP
        otp = random.randint(100000, 999999)

        #  Store temporarily in session
        request.session['signup_email'] = email
        request.session['signup_username'] = username
        request.session['signup_password'] = password
        request.session['signup_otp'] = str(otp)  # convert to string
        request.session['signup_referrel_code'] = referrel_code
        request.session['otp_expiry'] = time.time() + 300  # 5 minutes expiry

        #  Send OTP email
        subject = "Your OTP Code for WalkOn Signup"
        message = f"Hello {username},\n\nThank you for registering with WalkOn.\nYour One-Time Password (OTP) for account verification is:\n{otp}\n\nthis OTP is valid for 5 minutes. Please enter this code on the verification page to complete your registration.\nFor security reasons, do not share this code with anyone.\nBest regards,\nWalkOn Team"
                  
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        user_logger.info(f'OTP sent to {email}.')
        messages.success(request, f' OTP sent to {email}.')

        return redirect('verify_otp')
    # If GET request, just render signup page
    else:
        referral_code = request.GET.get('ref') or request.session.get('referral_code')


        context = {'referral_code': referral_code}
    return render(request, 'signup.html', context)

#=====================VERIFY OTP VIEW===============================================
def verify_otp_view(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('signup_otp')
        otp_expiry = request.session.get('otp_expiry')

        if not session_otp or not otp_expiry:
            messages.error(request, 'OTP not generated. Please request a new one.')
            return redirect('verify_otp')

        # Check expiry
        if time.time() > otp_expiry:
            messages.error(request, 'OTP expired. Please request a new one.')
            return redirect('verify_otp')

        if entered_otp == session_otp:
            username = request.session.get('signup_username')
            email = request.session.get('signup_email')
            password = request.session.get('signup_password')
            referrel_code = request.session.get('signup_referrel_code')

            user = CustomUser.objects.create_user(
                username=username, email=email, password=password
            )

            user.is_active = True
            user_logger.info(f'Account created for {user.username}')
            user.save()
            # Create referral code
            if referrel_code:
                try:
                    ref=Referral.objects.get(referral_code=referrel_code)
                    ref.referred_users.add(user)
                    user_logger.info(f"Added {user.username} as referred user")
                    ref.save()

                # Add referral amount to referrer's wallet
                    wallet = Wallet.objects.get(user=ref.referrer)
                    wallet.balance += settings.REFERRAL_AMOUNT
                    user_logger.info("wallet updated",wallet.balance)
                    wallet.save()

                # create a wallet transaction
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=settings.REFERRAL_AMOUNT,
                        transaction_type="credit",
                        description=f"Referral bonus added for {user.username}"
                    )
                    user_logger.info("wallet transaction created",wallet.balance)

                except Referral.DoesNotExist:
                    pass
            messages.success(request, 'Account created successfully! You can now log in.')
            request.session.flush()
            return redirect('login')

        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp')

    return render(request, 'otp_signup.html')

#=====================RESEND OTP VIEW===============================================
def resend_otp(request):
    email = request.session.get('signup_email')
    if email:
        otp = random.randint(100000, 999999)
        request.session['signup_otp'] = str(otp)
        request.session['otp_expiry'] = time.time() + 300  # 5 minute validity
        subject = "Your OTP Code for WalkOn Signup - Resend"
        message = f"Hello,\n\nYou requested a new OTP for your WalkOn signup process.\nYour new One-Time Password (OTP) is:\n{otp}\n\nThis OTP is valid for 5 minutes. Please enter this code on the verification page to complete your registration.\nIf you did not request this, please ignore this email.\nBest regards,\nWalkOn Team"
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        messages.success(request, "A new OTP has been sent to your email.")
    else:
        messages.error(request, "No email found in session. Please signup again.")
        return redirect('signup')

    return redirect('verify_otp')

#=====================LOGIN VIEW===============================================
@never_cache
@csrf_protect
def user_login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(request, username=email, password=password)
        # If  use custom user with EMAIL as USERNAME_FIELD, then 'username=email' is correct

        if user is not None:
            if user.is_active and not user.is_staff and not user.is_superuser:
                auth.login(request, user)
                user_logger.info(f"User {user.username} logged in.")
                return redirect('home')
            else:
                messages.error(request, "Only normal users can log in here.")
                return redirect('login')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('login')

    return render(request, 'user/user_login.html')
#=====================FORGOT PASSWORD VIEW===============================================
@never_cache
def forgot_password_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email) 
            otp = random.randint(100000, 999999)
            request.session['reset_email'] = email
            request.session['reset_otp'] = str(otp)
            request.session['otp_expiry'] = time.time() + 300  # OTP valid for 5 minutes
            subject = "Your OTP for WalkOn Password Reset"
            message = f"Hello,\n\nYou requested a password reset for your WalkOn account.\nYour One-Time Password (OTP) for password reset is:\n{otp}\n\nThis OTP is valid for 5 minutes. Please enter this code on the reset password page to complete your password reset.\nIf you did not request this, please ignore this email.\nBest regards,\nWalkOn Team"

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
            return redirect('verify_reset_otp')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Email not found')
    return render(request, 'user/forgot_password.html')
#=====================RESET PASSWORD VIEW===============================================
def verify_reset_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('reset_otp'):
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP')
    return render(request, 'user/otp_forgotpassword.html')
#=====================RESET PASSWORD VIEW===============================================
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        #  Check password match
        if new_password != confirm_password:
            messages.error(request, ' Passwords do not match.')
            return redirect('reset_password')

        #  Validate password (with custom + Django validators)
        try:
            validate_password(new_password)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return redirect('reset_password')

        #  Get user from session
        email = request.session.get('reset_email')
        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            user_logger.info(" Password reset successfully")
            messages.success(request, ' Password reset successfully. Please login with your new password.')
            return redirect('login')

        except CustomUser.DoesNotExist:
            messages.error(request, ' User not found. Please try again.')

    return render(request, 'user/reset_password.html')


#=====================USER PROFILE VIEW===============================================
@login_required(login_url='login')
def user_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    # referral code
    referral = None
    try:
        referral = Referral.objects.get(referrer=user)
    except Referral.DoesNotExist:
        referral=None
    return render(request, 'user/profile.html', {'user': user, 'referral': referral})

#=====================EDIT PROFILE VIEW===============================================

@login_required(login_url="login")
def edit_profile(request):
    user = request.user
    if request.method == "POST":
        form = EditProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            user_logger.info(f"User {user.username} updated profile.")
            return redirect("user_profile", user.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EditProfileForm(instance=user)

    return render(request, "user/edit_profile.html", {"form": form, "user": user})

#=====================REQUEST EMAIL CHANGE VIEW===============================================
@login_required(login_url="login")
def request_email_change(request):
    if request.method == "POST":
        new_email = request.POST.get("new_email")

        # check email already exists
        if CustomUser.objects.filter(email=new_email).exists():
            messages.error(request, "This email is already in use.")
            return redirect("request_email_change")

        # generate OTP
        otp = str(random.randint(100000, 999999))

        # save otp + email in session
        request.session["email_otp"] = otp
        request.session["pending_email"] = new_email  # Store the new email in session to use during verification
        request.session["otp_expiry"] = time.time() + 300  # 5 minute validity
        subject = "Your OTP for WalkOn Email Change Request"
        message = f"Hello,\n\nYou requested to change your email for your WalkOn account.\nYour One-Time Password (OTP) for email change verification is:\n{otp}\n\nThis OTP is valid for 5 minutes. Please enter this code on the verification page to complete your email change.\nIf you did not request this, please ignore this email.\nBest regards,\nWalkOn Team"

        # send OTP to new email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],  # Send to current email for security
            fail_silently=False,
        )

        send_mail(
            "Email Change Requested for WalkOn Account",
            f"Hello,\n\nAn email change request was made for your WalkOn account to the email address: {new_email}.\nIf you made this request, please check your current email for the OTP to confirm the change.\nIf not, you can safely ignore this email.\nBest regards,\nWalkOn Team",
            settings.DEFAULT_FROM_EMAIL,
            [new_email],
            fail_silently=False,
        )

        messages.info(request, f"OTP has been sent to {request.user.email}.")
        return redirect("verify_email_change_otp")

    return render(request, "user/request_email_change.html")

#=====================VERIFY EMAIL CHANGE OTP VIEW===============================================
@login_required(login_url="login")
def verify_email_otp(request):
    user = request.user
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("email_otp")
        new_email = request.session.get("pending_email")

        if not saved_otp or not new_email:
            messages.error(request, "No OTP session found. Please request again.")
            return redirect("request_email_change")

        #  Always compare as string
        if str(entered_otp) == str(saved_otp): # for security reason
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                user_logger.warning(f"User {user.username} attempted to change email to {new_email}, but it is already in use.")
                messages.error(request, "This email is already registered. Please use another one.")
                return redirect("verify_email_change_otp")

            user.email = new_email
            user.save()
            send_mail(
                "Email Changed Successfully for WalkOn Account",
                f"Hello,\n\nYour email has been successfully changed to {new_email}.\nIf you did not make this change, please contact support immediately.\nBest regards,\nWalkOn Team",
                settings.DEFAULT_FROM_EMAIL,
                [new_email],
                fail_silently=False,
            )

            # Clear session
            request.session.pop("email_otp", None)
            request.session.pop("pending_email", None)

            messages.success(request, "Your email has been updated successfully.")
            user_logger.info(f"User {user.username} updated email to {new_email} successfully.")
            return redirect("user_profile", user.id)
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "user/verify_email_otp.html")

#=====================RESEND EMAIL CHANGE OTP VIEW===============================================

@login_required(login_url="login")
def resend_email_change_otp(request):
    new_email = request.session.get("pending_email")
    if not new_email:
        messages.error(request, "No pending email change request.")
        return redirect("edit_profile")

    otp = str(random.randint(100000, 999999))
    request.session["email_otp"] = otp
    request.session["otp_expiry"] = time.time() + 300  # 5 minute validity
    subject = "Your OTP for WalkOn Email Change Request - Resend"
    message = f"Hello,\n\nYou requested to change your email for your WalkOn account.\nYour new One-Time Password (OTP) for email change verification is:\n{otp}\n\nThis OTP is valid for 5 minutes. Please enter this code on the verification page to complete your email change.\nIf you did not request this, please ignore this email.\nBest regards,\nWalkOn Team"

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],  # Send to current email for security
        fail_silently=False,
    )

    messages.success(request, f"New OTP has been sent to {new_email}.")
    return redirect("verify_email_change_otp")

#=====================CHANGE PASSWORD VIEW===============================================

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user  # logged-in user

        #  Check old password
        if not user.check_password(old_password):
            messages.error(request, ' Old password is incorrect')
            return redirect('change_password')

        #  Check new passwords match
        if new_password != confirm_password:
            messages.error(request, ' New passwords do not match')
            return redirect('change_password')

        #  Run Django + custom password validators
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            for error in e.messages:
                user_logger.error(error)
                messages.error(request, error)
            return redirect('change_password')

        #  Update password
        user.set_password(new_password)
        user.save()
        user_logger.info(f'Password changed successfully for user: {user.username}')

        #  Keep user logged in
        update_session_auth_hash(request, user)

        messages.success(request, ' Password changed successfully!')
        return redirect('user_profile', user.id)

    return render(request, 'user/change_password.html')

#soft delete user
@login_required(login_url='login')
def delete_account(request):
    user = request.user
    user.is_active = False
    user.save()
    user_logger.info(f"User {user.username} deleted their account.")
    messages.success(request, "Your account has been deleted successfully.")
    return redirect('home')

#================================================================================Admin views=================================================================================
#admin login view
def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:  # Check if admin/staff
                admin_logger.info("Admin logged in")
                return redirect('dashboard')  # Django admin dashboard
            else:
                return redirect('home')  # Your normal user homepage
        else:
            messages.error(request, "Invalid username or password")
            return redirect('admin_login')

    return render(request, "admin/admin_login.html")

#logut view
@never_cache
def logout_view(request):  
    is_staff = request.user.is_staff  
    logout(request)
    request.session.flush()  
    
    if is_staff:
        return redirect('admin_login')
    return redirect('home')


# Admin User Management


@staff_member_required(login_url="admin_login")
def admin_user_management(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    query = request.GET.get('q')
    users = CustomUser.objects.filter(is_staff=False, is_superuser=False)

    if query:
        q_lower = query.lower()
        search_filter = Q(username__icontains=query) | Q(email__icontains=query) | Q(id__icontains=query)
        if q_lower == "active":
            search_filter |= Q(is_active=True)
        elif q_lower == "blocked":
            search_filter |= Q(is_active=False)
        users = users.filter(search_filter)

    users = users.order_by('-date_joined')

    paginator = Paginator(users, 10)  # 3 users per page
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    context = {
        "users": users,
        "query": query,
    }
    return render(request, "admin/user_management.html", context)
# active or inactive user 
@staff_member_required(login_url="admin_login")
@require_POST # Only allow POST requests for this view
def toggle_user_status(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(CustomUser, id=user_id)
        user.is_active = not user.is_active
        user.save()
        admin_logger.info(f"User {user.username} status changed to {user.is_active}")
        return JsonResponse({"success": True, "is_active": user.is_active})
    return JsonResponse({"success": False, "error": "Invalid request"})