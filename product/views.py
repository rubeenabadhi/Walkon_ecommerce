from django.shortcuts import render,redirect
from .models import *
from wishlist.models import *
from .forms import *
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.forms.models import modelformset_factory
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce # Import the Coalesce function for NULL handling
from django.core.paginator import Paginator
import cloudinary
import logging

admin_logger=logging.getLogger('admin_logger')
user_logger=logging.getLogger('user_logger')








# =======================================================ADMIN PANEL========================================================================

#-----------------Gender Management------------
@staff_member_required
def add_gender(request):
    if request.method == 'POST':
        form = GenderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gender added successfully!')
            return redirect('add_gender')
    else:
        form = GenderForm()
    return render(request, 'admin/add_gender.html', {'form': form})

#--------------------------------- Brand Management
@staff_member_required
def add_brand(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Brand added successfully!")
            return redirect('add_brand')
        else:
            messages.error(request, "Form is invalid!")
    else:
        form = BrandForm()
    return render(request, 'admin/add_brand.html', {'form': form})

# -----------------------------------------------Category Management
@staff_member_required
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            admin_logger.info("Category added successfully")
            messages.success(request, "Category added successfully!")
            return redirect('add_category')
        else:
            messages.error(request, "Form is invalid!")
    else:
        form = CategoryForm()
    return render(request, 'admin/add_category.html', {'form': form})   


# -----------------------------------Size Management
@staff_member_required
def add_size(request):
    if request.method =='POST':
        form= SizeForm(request.POST)
        if form.is_valid():
            form.save()
            admin_logger.info("Size added successfully")
            messages.success(request,'Size added successfully!')
            return redirect('add_size')
        else:
            messages.error(request,'Form is invalid!')
    else:
        form = SizeForm()
        return render(request, 'admin/add_size.html', {'form': form})
    
# -------------------------------------Color Management
@staff_member_required
def add_color(request):    
    if request.method == 'POST':
        form = ColorForm(request.POST)
        if form.is_valid():
            admin_logger.info("Form is valid")
            form.save()
            admin_logger.info("Color added successfully")
            messages.success(request, 'Color added successfully!')
            return redirect('add_color')
        else:
            admin_logger.error(form.errors)
            messages.error(request, 'Form is invalid!')
    else:
        form = ColorForm()
        return render(request, 'admin/add_color.html', {'form': form})
    
#--------------------------------- Product Management
@staff_member_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        gender_id = request.POST.get("gender")
        price = request.POST.get("price")
        is_available = True if request.POST.get("is_available") == "on" else False
        is_active = True if request.POST.get("is_active") == "on" else False    

        # Primary Image (Cloudinary with cropping)
        primary_image_url = None
        primary_image = request.FILES.get("primary_image")
        if primary_image:
            upload_result = cloudinary.uploader.upload(primary_image, transformation=[
                {"width": 300, "height": 300, "crop": "fill", "gravity": "auto"}
            ]) # means to automatically crop the image to fit within 300x300 while keeping the main subject in focus
            primary_image_url = upload_result['secure_url']

        #  Create Product with stock at product-level
        product = Product.objects.create(
            name=name,
            description=description,
            category_id=category_id,
            brand_id=brand_id,
            gender_id=gender_id,
            is_available=is_available,
            is_active=is_active,
            added_by=request.user,
            primary_image=primary_image_url,
            slug=slugify(name)
        )

        # Additional Images
        additional_images = request.FILES.getlist("additional_images")
        for img in additional_images:
            if img:
                upload_result = cloudinary.uploader.upload(img, transformation=[
                    {"width": 300, "height": 300, "crop": "fill", "gravity": "auto"}
                ])
                Image.objects.create(product=product, image=upload_result['secure_url'])

        # Sizes & Colors (checkboxes)
        size_ids = request.POST.getlist("sizes")
        color_ids = request.POST.getlist("colors")

        # Create variants 
        for size_id in size_ids:
            stock=int(request.POST.get(f"stock_{size_id}", 0))   # stock comes from the form for each variant
            for color_id in color_ids:
                variant = ProductVariant.objects.create(
                    product=product,
                    size_id=size_id,
                    color_id=color_id,
                    price=price,
                    stock=stock
                )

                # Variant-specific images (optional)
                variant_images = request.FILES.getlist(f"variant_images_{size_id}_{color_id}")
                for vimg in variant_images:
                    if vimg:
                        upload_result = cloudinary.uploader.upload(vimg, transformation=[
                            {"width": 500, "height": 500, "crop": "fill", "gravity": "auto"}
                        ])
                        Image.objects.create(product=product, variant=variant, image=upload_result['secure_url'])

        return redirect("products")

    context = {
        "categories": Category.objects.all(),
        "brands": Brand.objects.all(),
        "genders": Gender.objects.all(),
        "sizes": Size.objects.all(),
        "colors": Color.objects.all(),
    }
    return render(request, "admin/add_product.html", context)

#--------------------------------------- view to list all products
@staff_member_required(login_url="admin_login")
def product_list(request):

    products = Product.objects.exclude(is_deleted=True).order_by('-created_at').prefetch_related('variants')

    search_query = request.GET.get('search', '')
    selected_category = request.GET.get('category', '')
    selected_status = request.GET.get('status', '')

    # Search
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(gender__label__icontains=search_query)
        )

    # Category Filter
    if selected_category:
        products = products.filter(category_id=selected_category)

    # Status Filter
    if selected_status == "available":
        products = products.filter(is_active=True)

    elif selected_status == "unavailable":
        products = products.filter(is_active=False)

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'admin/products.html', {
        'products': products,
        'search_query': search_query,
        'categories': categories,
        'selected_category': selected_category,
        'selected_status': selected_status,
    })
#--------------------------------------- Product Detail View
@staff_member_required
def product_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = ProductVariant.objects.filter(product=product).select_related('size', 'color').prefetch_related('images') #means to pre-fetch images for each variant from the database 
    unique_sizes = variants.values_list("size__label", flat=True).distinct()
    unique_colors = variants.values_list("color__name", flat=True).distinct()

    if request.method == 'POST':
        # Handle any form submissions related to the product details here
        pass
    
    return render(request, 'admin/product_details.html', {
        'product': product,
        'variants': variants,
        'unique_sizes': unique_sizes,
        'unique_colors': unique_colors
    })

#--------------------------------------------edit product view

@staff_member_required
def edit_product(request,slug=None):
    # Get product if editing
    product = get_object_or_404(Product, slug=slug) if slug else None

    # Preselect existing sizes/colors
    selected_sizes = set(product.variants.values_list('size_id', flat=True)) if product else set()
    selected_colors = set(product.variants.values_list('color_id', flat=True)) if product else set()

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        gender_id = request.POST.get("gender")
        is_available = True if request.POST.get("is_available") == "on" else False
        is_active = True if request.POST.get("is_active") == "on" else False
        price = request.POST.get("price")
        

        # --- Create or update product ---
        if product:
            if request.FILES.get("primary_image"):
                product.primary_image = request.FILES.get("primary_image")

            product.name = name
            product.description = description
            product.category_id = category_id
            product.brand_id = brand_id
            product.gender_id = gender_id
            product.is_available = is_available
            product.is_active = is_active
            product.slug = slugify(name)
            product.save()
        else:
            product = Product.objects.create(
                name=name,
                description=description,
                category=category_id,
                brand=brand_id,
                gender=gender_id,
                is_available=is_available,
                slug=slugify(name),
            )
            if request.FILES.get("primary_image"):
                product.primary_image = request.FILES.get("primary_image")
                product.save()

        # --- Handle additional images ---
        existing_images = product.images.all()
        for image in existing_images:
            index = list(existing_images).index(image)
            if f"delete_image_{index}" in request.POST:
                image.delete()

        new_images = request.FILES.getlist("additional_images")
        for img in new_images:
            if img:
                Image.objects.create(product=product, image=img)

        # --- Handle variants  ---
        size_ids = request.POST.getlist("sizes")
        color_ids = request.POST.getlist("colors")

        if size_ids and color_ids and price:
            # Delete old variants not in the new selection
            new_combinations = {(size_id, color_id) for size_id in size_ids for color_id in color_ids}
            for variant in product.variants.all():
                if (str(variant.size_id), str(variant.color_id)) not in new_combinations:
                    variant.delete()

            # Create or update variants
            for size_id in size_ids:
                stock=int(request.POST.get(f"stock_{size_id}", 0)) 
                for color_id in color_ids:
                    variant, created = ProductVariant.objects.get_or_create(
                        product=product,
                        size_id=size_id,
                        color_id=color_id,
                        defaults={'price': float(price), 'stock': int(stock) if stock else 0},
                        
                    )
                    if not created:
                        variant.price = float(price)
                        variant.stock = int(stock) if stock else 0
                        variant.save()

        messages.success(request, f"{'Product updated' if slug else 'New product added'} successfully!")
        return redirect('admin_product_details', slug=product.slug)

    # --- Render form context ---
    context = {
        'product': product,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'genders': Gender.objects.all(),
        'sizes': Size.objects.all(),
        'colors': Color.objects.all(),
        'selected_sizes': selected_sizes,
        'selected_colors': selected_colors,
    }
    return render(request, 'admin/add_product.html', context)

#--------------------------------------- delete product view
@login_required
def delete_product(request, slug):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest": # means it's an AJAX request for a specific product
        product = get_object_or_404(Product, slug=slug)
        
        # delete product + variants
        product.is_deleted = True
        product.save()
        admin_logger.info(f"Product {product.name} marked as deleted.")
        
        return JsonResponse({"success": True, "message": "Product and all variants deleted successfully!"})
    return JsonResponse({"success": False, "message": "Invalid request!"}, status=400)


#--------------------------------- view for admin all master data management(size,color,category,gender,brand)
@staff_member_required(login_url="admin_login")
def admin_master_view(request):

    sections = [
        {
            "title": "Sizes",
            "items": Size.objects.all(),
            "type": "size",
            "add_url": "add_size",
        },
        {
            "title": "Colors",
            "items": Color.objects.all(),
            "type": "color",
            "add_url": "add_color",
        },
        {
            "title": "Categories",
            "items": Category.objects.all(),
            "type": "category",
            "add_url": "add_category",
        },
        {
            "title": "Gender",
            "items": Gender.objects.all(),
            "type": "gender",
            "add_url": "add_gender",
        },
        {
            "title": "Brands",
            "items": Brand.objects.all(),
            "type": "brand",
            "add_url": "add_brand",
        },
    ]

    return render(request, "admin/master_view.html", {"sections": sections})

#--------------------------------- edit for admin add size,color,category

@staff_member_required(login_url="admin_login")
def ajax_edit_variant(request):

    if request.method != "POST":
        return JsonResponse({"status": "error"})

    item_type = request.POST.get("type")
    item_id = request.POST.get("id")
    name = request.POST.get("name")

    models = {
        "size": Size,
        "color": Color,
        "category": Category,
        "gender": Gender,
        "brand": Brand,
    }

    Model = models.get(item_type)
    if not Model:
        return JsonResponse({"status": "error"})

    item = get_object_or_404(Model, id=item_id)
    item.name = name
    item.save()

    return JsonResponse({"status": "success"})


#--------------------------------- Ajax view to delete size,color,category

@staff_member_required(login_url="admin_login")
def ajax_delete_variant(request):
    if request.method == "POST":
        item_type = request.POST.get("type")
        item_id = request.POST.get("id")

        models = {
            "size": Size,
            "color": Color,
            "category": Category,
            "gender": Gender,
            "brand": Brand,
        }

        model = models.get(item_type)
        if model:
            try:
                model.objects.get(id=item_id).delete()
                return JsonResponse({"status": "success"})
            except:
                return JsonResponse({"status": "error"})

    return JsonResponse({"status": "invalid"})

#====================stock update view========================
@staff_member_required(login_url='admin_login')
def stock_management(request):

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':

        variant_id = request.POST.get('variant_id')
        stock = request.POST.get('stock')

        if not variant_id or stock is None:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request.'
            })

        try:
            variant = ProductVariant.objects.filter(
                id=variant_id,
                product__is_deleted=False
            ).first()

            if not variant:
                return JsonResponse({
                    'success': False,
                    'error': 'Variant not found.'
                })

            variant.stock = int(stock)
            variant.save()

            return JsonResponse({
                'success': True
            })

        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Stock must be a number.'
            })

        except Exception as e:
            admin_logger.error(f"Error updating stock: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    # -------- GET PART --------
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    variants = ProductVariant.objects.exclude(product__is_deleted=True)

    if query:
        variants = variants.filter(product__name__icontains=query)

    if status_filter == 'low':
        variants = variants.filter(stock__lte=5, stock__gt=0)
    elif status_filter == 'out':
        variants = variants.filter(stock=0)
    elif status_filter == 'in':
        variants = variants.filter(stock__gt=5)

    context = {
        'variants': variants.order_by('stock'),
        'query': query,
        'status_filter': status_filter,
        'low_stock_count': variants.filter(stock__lte=5, stock__gt=0).count(),
        'out_stock_count': variants.filter(stock=0).count(),
        'total_variants': variants.count(),
    }

    return render(request, 'admin/stock_management.html', context)

#============================================================================= USER VIEW==============================================================

#----------apply filters
def apply_product_filters(request, products):
    filter_form = ProductFilterForm(request.GET or None)

    if filter_form.is_valid():
        category = filter_form.cleaned_data.get("category")
        brand = filter_form.cleaned_data.get("brand")
        gender = filter_form.cleaned_data.get("gender")
        min_price = filter_form.cleaned_data.get("min_price")
        max_price = filter_form.cleaned_data.get("max_price")
        sort_by = filter_form.cleaned_data.get("sort_by")

        if category:
            products = products.filter(category=category)

        if brand:
            products = products.filter(brand=brand)

        if gender:
            products = products.filter(gender=gender)

        if min_price is not None:
            products = products.filter(variants__price__gte=min_price)

        if max_price is not None:
            products = products.filter(variants__price__lte=max_price)

        if sort_by == "price_low":
            products = products.order_by("variants__price")
        elif sort_by == "price_high":
            products = products.order_by("-variants__price")
        elif sort_by == "latest":
            products = products.order_by("-created_at")
        elif sort_by == "oldest":
            products = products.order_by("created_at")

    return products.distinct(), filter_form


# Product Listing with Filters, Sorting, Pagination, Wishlist Integration
def user_product_list(request):

    products = Product.objects.exclude(is_deleted=True).order_by('created_at').prefetch_related('variants')

    genders = Gender.objects.all()
    # apply filters
    products, filter_form = apply_product_filters(request, products)
    # wishlist
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).values_list("product_variant__product_id", flat=True)

    products = products.distinct() 
    paginator = Paginator(products, 6)  # Show 6 products per page
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    return render(request, "user/all_products.html", {
        "products": products,
        "filter_form": filter_form,
        "genders": genders,
        "wishlist_ids": list(wishlist_ids),
    })


# Product Detail View
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    variants = ProductVariant.objects.filter(
        product=product
    ).select_related('color', 'size').prefetch_related('images')

    colors = {v.color.id: v.color for v in variants if v.color}.values()
    sizes = Size.objects.filter(variants__product=product).distinct()

    return render(request, 'user/product_details.html', {
        'product': product,
        'variants': variants,
        'colors': colors,
        'sizes': sizes,
    })

# -------------------
# Fetch available sizes for a product (Ajax)
@login_required(login_url="login")
def product_sizes(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        sizes = [
            {"id": v.id, "label": v.size.label if v.size else "N/A"}
            for v in product.variants.all()
        ]
        return JsonResponse({"sizes": sizes})
    except Product.DoesNotExist:
        return JsonResponse({"sizes": []})


#new arrivals
def new_arrivals(request):
    products = Product.objects.exclude(is_deleted=True).filter(is_active=True).distinct().order_by('-created_at')  # 
    # apply filters
    products, filter_form = apply_product_filters(request, products)

    paginator= Paginator(products, 6)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    return render(request, 'user/new_arrivals.html', {'products': products, 'filter_form': filter_form})

# products by gender with pagination
def products_by_gender(request, gender_label):
    gender = get_object_or_404(Gender, label=gender_label)
    products = Product.objects.filter(gender=gender).exclude(is_deleted=True).order_by('-created_at')
    # apply filters 
    products, filter_form = apply_product_filters(request, products)
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')   
    products = paginator.get_page(page_number)
    return render(request, 'user/products_by_gender.html', {'products': products, 'gender': gender, 'filter_form': filter_form})    