from django.shortcuts import render
from .models import *
from django.contrib.auth.decorators import login_required


# Create your views here.
#================================================USER WALLET VIEW===============================================

@login_required(login_url="login")
def wallet(request):
    
    return render(request, "user/wallet.html")
