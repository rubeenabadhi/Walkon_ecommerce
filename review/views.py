from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from.models import *
from.forms import *
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from order.models import OrderItem
from product.models import Product
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

# Create your views here.
#=========================================================================USER REVIEW VIEW===============================================


@login_required(login_url="login")
def add_review(request, product_id):
    # Ensure product exists
    product = get_object_or_404(Product, id=product_id)

    # Check if item is delivered to this user
    delivered_item = OrderItem.objects.filter(
        product_variant__product_id=product_id,
        order__user=request.user,
        order__status="delivered"
    ).first()

    if not delivered_item:
        messages.error(request, "You can review a product only after it is delivered.")
        return redirect("order_details", delivered_item.order.order_id)

    # Check duplicate review
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.warning(request, "You already reviewed this product.")
        print("You already reviewed this product.")
        return redirect("order_details", delivered_item.order.order_id)

    # FORM SUBMIT
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.rating = int(request.POST["rating"])
            review.save()
            messages.success(request, "Review added successfully!")
            print("Review added successfully!", review)
            return redirect("order_details", delivered_item.order.order_id)
    return redirect("order_details", delivered_item.order.order_id)

#------------------------Edit Review View ----------------------

@login_required
def edit_review(request, review_id):
    review = Review.objects.get(id=review_id, user=request.user)

    if request.method == "POST":
        review.rating = request.POST.get("rating")
        review.review = request.POST.get("review")
        review.save()

        return JsonResponse({"status": "success", "message": "Review updated!"})

    return JsonResponse({"status": "error"})

#--------------------DELETE REVIEW JA and AJAX---------------------

@login_required(login_url="login")
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    return redirect('order_details', review.order.order_id)




#=========================================================================ADMIN REVIEW VIEW===============================================

@staff_member_required(login_url="admin_login")
def admin_review(request):
    reviews = Review.objects.all().order_by('-created_at')
    #search
    search_query = request.GET.get('search')
    if search_query:
        reviews = reviews.filter(Q(user__username__icontains=search_query) | Q(product__name__icontains=search_query))

    #pagination
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/view_reviews.html', { 'page_obj': page_obj, 'search_query': search_query})

#--------------------DELETE REVIEW JA and AJAX---------------------

@staff_member_required(login_url="admin_login")
def delete_review(request, review_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."})
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted successfully.")
    return redirect('admin_review')

