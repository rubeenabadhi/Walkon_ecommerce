from django.shortcuts import render

# Create your views here.
#======about us view======
def about_us(request):
    return render(request, 'user/about_us.html')

#======contact us view======
def contact_us(request):
    return render(request, 'user/contact_us.html')

