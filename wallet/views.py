from .models import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
import logging

user_logger = logging.getLogger('user_logger')


# Create your views here.
#================================================USER WALLET VIEW===============================================

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


#=========User wallet view==============
@login_required(login_url='login')
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')

    paginator=Paginator(transactions,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    
    context = {
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj
    }
    return render(request, "user/wallet.html", context)

#=======================add money view========================
@login_required(login_url='login')
def add_money(request):
    if request.method == "POST":
        amount = int(request.POST.get('amount')) * 100  # amount in paisa
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        # Create Razorpay order
        razorpay_order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        # Store in session for payment success
        request.session['wallet_amount'] = amount / 100 # amount in rupees 
        request.session['razorpay_order_id'] = razorpay_order['id']

        # Return JSON (AJAX response)
        return JsonResponse({
            "order_id": razorpay_order['id'],
            "amount": amount,
            "key_id": settings.RAZORPAY_KEY_ID,
            "user_email": request.user.email,
            "user_name": request.user.username
        })
    return JsonResponse({"error": "Invalid request"}, status=400)

#=======================wallet payment success view======================== 
@csrf_exempt
@login_required(login_url='login')
def wallet_payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            # Update wallet
            amount = request.session.get('wallet_amount', 0)
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += Decimal(amount)
            wallet.save()
            user_logger.info(f"[DEBUG] Wallet balance after payment: ₹{wallet.balance}")

            # Add wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                amount=Decimal(amount),
                purpose="topup",
                description=f"Added via Razorpay (Payment ID: {payment_id})"
            )

            # Clear session
            request.session.pop('wallet_amount', None)
            request.session.pop('razorpay_order_id', None)

            return JsonResponse({"status": "success", "message": f"₹{amount} added to wallet"})

        except razorpay.errors.SignatureVerificationError:
            user_logger.error("Payment verification failed")
            return JsonResponse({"status": "failure", "message": "Payment verification failed"})
        except Exception as e:
            user_logger.error(str(e))
            return JsonResponse({"status": "failure", "message": str(e)})

    return JsonResponse({"status": "failure", "message": "Invalid request"})



#==========================================================================================ADMIN WALLET VIEW============================================


@login_required(login_url='admin_login')
def admin_wallets(request):
    wallets = Wallet.objects.select_related('user').all().order_by('-updated_at')

    # Search by username or email
    search_query = request.GET.get('search', '')
    if search_query:
        wallets = wallets.filter(user__username__icontains=search_query) | wallets.filter(user__email__icontains=search_query)

    # Pagination
    paginator = Paginator(wallets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wallets': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin/wallet_user.html', context)

#==user wallet detail view for admin to see transactions==  
@login_required(login_url='admin_login')
def admin_wallet_detail(request, wallet_id):   
    wallet = get_object_or_404(Wallet, id=wallet_id)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wallet': wallet,
        'transactions': page_obj,
        'user': wallet.user,
    }
    return render(request, 'admin/wallet_details.html', context)
