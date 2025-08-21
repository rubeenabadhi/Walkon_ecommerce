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
from django.db.models import Q, Min, Avg, Count, Sum
from django.db.models.functions import Coalesce # Import the Coalesce function for NULL handling
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.forms.models import modelform_factory







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
    Categories = Category.objects.all()
    Brands = Brand.objects.all()
    Genders = Gender.objects.all()

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)

        if product_form.is_valid():
            product = product_form.save(commit=False)# commit=False means we don't save the product yet
            print("Product form is valid")
            product.added_by = request.user   # Assign the current correct admin user
            product.save()
            print("Product saved successfully")
            messages.success(request, 'Product added successfully!')
            return redirect('add_variant', slug=product.slug)
        else:
            print(product_form.errors)
            messages.error(request, 'Please correct the errors below.')

    else:
        product_form = ProductForm()
        
    return render(request, 'admin/add_product.html', {
        'product_form': product_form,
        'categories': Categories,
        'brands': Brands,
        'genders': Genders
    })

# Variant Management
@staff_member_required
def add_variant(request, slug):
    product = get_object_or_404(Product, slug=slug)
    ImageFormSet = modelformset_factory(Image, form=ImageForm, extra=3)
    VariantFormSet = modelformset_factory(ProductVariant, form=ProductVariantForm, extra=2)
    sizes = Size.objects.all()
    colors = Color.objects.all()

    if request.method == 'POST':
        variant_formset = VariantFormSet(request.POST, queryset=ProductVariant.objects.filter(product=product))
        image_formset = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.filter(variant__product=product))

        if variant_formset.is_valid() and image_formset.is_valid():
            variants = variant_formset.save(commit=False)# means we don't save the variants yet
            print("Variants are valid and ready to be saved")
            # Save each variant and associate it with the product
            images = image_formset.save(commit=False) #means we don't save the images yet
            print("Images are valid and ready to be saved")

            for variant in variants:
                variant.product = product
                variant.save()
            print('Variants saved successfully')

            for idx, variant in enumerate(variants):
                variant.product = product
                variant.save()
                if idx < len(images):
                    images[idx].variant = variant
                    images[idx].save()

            print("Images saved successfully")
            messages.success(request, 'Variants and images added successfully!')
            return redirect('add_variant', slug=product.slug)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        variant_formset = VariantFormSet(queryset=ProductVariant.objects.filter(product=product))
        image_formset = ImageFormSet(queryset=Image.objects.filter(variant__product=product))
    return render(request, 'admin/add_variant.html', {
        'product': product,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
        'sizes': sizes,
        'colors': colors
    })
# view to list all products
@staff_member_required
def product_list(request):
    products = Product.objects.all().order_by('-created_at')

    # ---- PAGINATION ----
    paginator = Paginator(products, 1)  # 2 users per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    return render(request, 'admin/products.html', {'products': products})

@staff_member_required
def product_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = ProductVariant.objects.filter(product=product).prefetch_related('images')
    
    if request.method == 'POST':
        # Handle any form submissions related to the product details here
        pass
    
    return render(request, 'admin/product_details.html', {
        'product': product,
        'variants': variants
    })
#edit product view
@staff_member_required
def edit_product(request, slug): 
    product = get_object_or_404(Product, slug=slug)

    ProductFormCls = modelform_factory(Product, fields=['name', 'description', 'is_available', 'is_listed', 'category', 'brand', 'gender'])
    VariantFormSet = modelformset_factory(ProductVariant, form=ProductVariantForm, extra=1, can_delete=True)
    ImageFormSet = modelformset_factory(Image, form=ImageForm, extra=3, can_delete=True)  #  3 extra images form

    if request.method == 'POST':
        product_form = ProductFormCls(request.POST, instance=product)
        variant_formset = VariantFormSet(request.POST, queryset=product.variants.all(), prefix='variants')
        image_formset = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.filter(variant__product=product), prefix='images')  
        # request.FILES adds support for file uploads

        if product_form.is_valid() and variant_formset.is_valid() and image_formset.is_valid():
            product_form.save()  # save product update

        variants = variant_formset.save(commit=False)
        for variant in variants:
            variant.product = product
            variant.save()

        #  Save images
        images = image_formset.save(commit=False)
        for image in images:
            if not image.variant:  
                # auto-assign to first variant
                first_variant = product.variants.first()
                if first_variant:
                    image.variant = first_variant
            image.save()

        # delete removed images
        for obj in image_formset.deleted_objects:
            obj.delete()

        messages.success(request, "Product, variants and images updated successfully!")
        return redirect('edit_product', slug=product.slug)
    else:
        product_form = ProductFormCls(instance=product)
        variant_formset = VariantFormSet(queryset=product.variants.all(), prefix='variants')
        image_formset = ImageFormSet(queryset=Image.objects.filter(variant__product=product), prefix='images')

    return render(request, 'admin/edit_product.html', {
        'product_form': product_form,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
        'product': product,
    })


#delete product 
@login_required
def delete_product(request, slug):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        product = get_object_or_404(Product, slug=slug)
        
        # delete product + variants
        product.delete()
        print(f"Product {product.name} and all its variants have been deleted")
        
        return JsonResponse({"success": True, "message": "Product and all variants deleted successfully!"})
    return JsonResponse({"success": False, "message": "Invalid request!"}, status=400)


                             ####User views
#all products list view
def user_product_list(request):
    products = (Product.objects
                .all()
                .prefetch_related('variants__images')  # Pre-fetch variants and images
                .select_related('category', 'brand', 'gender'))
    return render(request, 'user/all_products.html', {'products': products})  

#product details view
def product_details(request, slug):
    product = get_object_or_404(Product, slug=slug)

    # All variants of the product
    variants = ProductVariant.objects.filter(product=product).select_related('color', 'size')

    # Unique colors for this product
    colors = {v.color.id: v.color for v in variants if v.color}.values()

    # Unique sizes for this product (optional, if needed)
    sizes = Size.objects.filter(variants__product=product).distinct()

    return render(request, 'user/product_details.html', {
        'product': product,
        'variants': variants,
        'colors': colors,
        'sizes': sizes,
    })
