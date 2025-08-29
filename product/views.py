from django.shortcuts import render,redirect
from .models import *
from .forms import *
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.forms.models import modelformset_factory
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Min, Avg, Count, Sum, Max
from django.db.models.functions import Coalesce # Import the Coalesce function for NULL handling
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.forms.models import modelform_factory
from django.db import transaction
import cloudinary







# Create your views here.
#Gender Management
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

# Brand Management
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

# Category Management
@staff_member_required
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            print("Category added successfully")
            messages.success(request, "Category added successfully!")
            return redirect('add_category')
        else:
            messages.error(request, "Form is invalid!")
    else:
        form = CategoryForm()
    return render(request, 'admin/add_category.html', {'form': form})   


# Size Management
@staff_member_required
def add_size(request):
    if request.method =='POST':
        form= SizeForm(request.POST)
        if form.is_valid():
            form.save()
            print("Size added successfully")
            messages.success(request,'Size added successfully!')
            return redirect('add_size')
        else:
            messages.error(request,'Form is invalid!')
    else:
        form = SizeForm()
        return render(request, 'admin/add_size.html', {'form': form})
    
# Color Management
@staff_member_required
def add_color(request):    
    if request.method == 'POST':
        form = ColorForm(request.POST)
        if form.is_valid():
            print("Form is valid")
            form.save()
            print("Color added successfully")
            messages.success(request, 'Color added successfully!')
            return redirect('add_color')
        else:
            print(form.errors)
            print("Form is invalid")
            messages.error(request, 'Form is invalid!')
    else:
        form = ColorForm()
        return render(request, 'admin/add_color.html', {'form': form})
    
# Product Management
@staff_member_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        gender_id = request.POST.get("gender")
        is_available = True if request.POST.get("is_available") == "on" else False

        # Primary Image (Cloudinary with cropping)
        primary_image = request.FILES.get("primary_image")
        if primary_image:
            upload_result = cloudinary.uploader.upload(primary_image, transformation=[
                {"width": 300, "height": 300, "crop": "fill", "gravity": "auto"}
            ])
            primary_image_url = upload_result['secure_url']

        # Create Product
        product = Product.objects.create(
            name=name,
            description=description,
            category_id=category_id,
            brand_id=brand_id,
            gender_id=gender_id,
            is_available=is_available,
            added_by=request.user,
            primary_image=primary_image_url,
            slug=slugify(name)
        )

        # Additional Images (Cloudinary with cropping)
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
        price = request.POST.get("price")
        stock = request.POST.get("stock")

        # Create variants for each size-color combo
        for size_id in size_ids:
            for color_id in color_ids:
                variant = ProductVariant.objects.create(
                    product=product,
                    size_id=size_id,
                    color_id=color_id,
                    stock=stock,
                    price=price
                )

                # Variant-specific images (optional)
                variant_images = request.FILES.getlist(f"variant_images_{size_id}_{color_id}")
                for vimg in variant_images:
                    if vimg:
                        upload_result = cloudinary.uploader.upload(vimg, transformation=[
                            {"width": 300, "height": 300, "crop": "fill", "gravity": "auto"}
                        ])
                        Image.objects.create(product=product, variant=variant, image=upload_result['secure_url'])

        return redirect("products")  # Change to your product list page

    context = {
        "categories": Category.objects.all(),
        "brands": Brand.objects.all(),
        "genders": Gender.objects.all(),
        "sizes": Size.objects.all(),
        "colors": Color.objects.all(),
    }
    return render(request, "admin/add_product.html", context)

# view to list all products
@staff_member_required
def product_list(request):
    products = Product.objects.all().order_by('-created_at')

    # ---- PAGINATION ----
    paginator = Paginator(products, 2)  # 2 users per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    return render(request, 'admin/products.html', {'products': products})

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
#edit product view

@staff_member_required
def edit_product(request, slug=None):
    if slug:
        product = get_object_or_404(Product, slug=slug)
    else:
        product = None  # For adding a new product

    # Get existing selected sizes and colors for pre-selection
    selected_sizes = set(product.variants.values_list('size_id', flat=True)) if product else set()
    selected_colors = set(product.variants.values_list('color_id', flat=True)) if product else set()

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        gender_id = request.POST.get("gender")
        is_available = True if request.POST.get("is_available") == "on" else False

        # Handle product creation or update
        if product:
            primary_image = request.FILES.get("primary_image")
            if primary_image:
                product.primary_image = primary_image
            product.name = name
            product.description = description
            product.category_id = category_id
            product.brand_id = brand_id
            product.gender_id = gender_id
            product.is_available = is_available
            product.slug = slugify(name)
            product.save()
        else:
            product = Product.objects.create(
                name=name,
                description=description,
                category_id=category_id,
                brand_id=brand_id,
                gender_id=gender_id,
                is_available=is_available,
                slug=slugify(name)
            )
            if request.FILES.get("primary_image"):
                product.primary_image = request.FILES.get("primary_image")
                product.save()

        # Handle additional images
        existing_images = product.images.all()
        for image in existing_images:
            index = list(existing_images).index(image)
            if f"delete_image_{index}" in request.POST:
                image.delete()

        new_images = request.FILES.getlist("additional_images")
        print(f"New images received: {len(new_images)} files - {[img.name for img in new_images]}")
        for img in new_images:
            if img:
                Image.objects.create(product=product, image=img)

        # Handle variants with single price and stock
        size_ids = request.POST.getlist("sizes")
        color_ids = request.POST.getlist("colors")
        price = request.POST.get("price")
        stock = request.POST.get("stock")

        print(f"Received Size IDs: {size_ids}, Received Color IDs: {color_ids}, Price: {price}, Stock: {stock}")
        if size_ids and color_ids and (price or stock):
            # Delete existing variants not in the new selection
            new_combinations = {(size_id, color_id) for size_id in size_ids for color_id in color_ids}
            for variant in product.variants.all():
                if (variant.size_id, variant.color_id) not in new_combinations:
                    variant.delete()

            # Create or update variants
            for size_id in size_ids:
                for color_id in color_ids:
                    variant, created = ProductVariant.objects.get_or_create(
                        product=product,
                        size_id=size_id,
                        color_id=color_id,
                        defaults={'price': price, 'stock': stock}
                    )
                    if not created:
                        if price:
                            variant.price = float(price)
                        if stock:
                            variant.stock = int(stock)
                        variant.save()

        messages.success(request, f"{'Product, variants, and images updated' if slug else 'New product, variants, and images added'} successfully!")
        return redirect('admin_product_details', slug=product.slug)

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
    return render(request, 'admin/add_product.html', context)#delete product 
@login_required
def delete_product(request, slug):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest": # means it's an AJAX request for a specific product
        product = get_object_or_404(Product, slug=slug)
        
        # delete product + variants
        product.delete()
        print(f"Product {product.name} and all its variants have been deleted")
        
        return JsonResponse({"success": True, "message": "Product and all variants deleted successfully!"})
    return JsonResponse({"success": False, "message": "Invalid request!"}, status=400)


                             ####   User views  ####

def user_product_list(request):
    products = Product.objects.all()
    filter_form = ProductFilterForm(request.GET or None)
    genders = Gender.objects.all()

    if filter_form.is_valid():
        category = filter_form.cleaned_data.get("category")
        brand = filter_form.cleaned_data.get("brand")
        gender = filter_form.cleaned_data.get("gender")
        min_price = filter_form.cleaned_data.get("min_price")
        max_price = filter_form.cleaned_data.get("max_price")
        sort_by = filter_form.cleaned_data.get("sort_by")

        # Apply filters
        if category:
            products = products.filter(category=category)
        if brand:
            products = products.filter(brand=brand)
        if gender:
            products = products.filter(gender=gender)
        if min_price:
            products = products.filter(variants__price__gte=min_price)
        if max_price:
            products = products.filter(variants__price__lte=max_price)

        # Sorting
        if sort_by == "price_low":
            products = products.order_by("variants__price")
        elif sort_by == "price_high":
            products = products.order_by("-variants__price")
        elif sort_by == "latest":
            products = products.order_by("-created_at")
        elif sort_by == "popular":
            products = products.order_by("-views")

    products = products.distinct()

    # Pagination
    paginator = Paginator(products, 3)  # 3 products per page if needed
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    return render(request, "user/all_products.html", {
        "products": products,
        "filter_form": filter_form,
        "genders": genders,
    })
#product details view

def product_details(request, slug):
    product = get_object_or_404(Product, slug=slug)

    # All variants of the product with related color and size
    variants = ProductVariant.objects.filter(product=product).prefetch_related('images') 

    # Unique colors for this product
    colors = {v.color.id: v.color for v in variants if v.color}.values()

    # Unique sizes for this product
    sizes = Size.objects.filter(variants__product=product).distinct()

    if request.method == 'POST':
        # Handle any form submissions (e.g., adding to cart, selecting variant)
        pass

    return render(request, 'user/product_details.html', {
        'product': product,
        'variants': variants,
        'colors': colors,
        'sizes': sizes,
    })
#kids products
def kids_products(request):
    products = Product.objects.filter(gender__label='Kids')
    categories = Category.objects.all()

    Category_params = request.GET.get("category")
    if Category_params:
        products = products.filter(category__name__iexact=Category_params)
    return render(request, 'user/kids.html', {'products': products, 'categories': categories})
