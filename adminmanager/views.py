from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Category, Product, ProductImage, Variant, ReviewRating
from orders.models import OrderItem, Orders, Payment
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth.decorators import login_required
from .forms import VariantForm
from django.db.models import Avg, Sum, Count
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta
from decimal import Decimal


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
# Create your views here.
def admin_loogin(request):
    if request.method == "POST":
        uname = request.POST.get("username")
        password = request.POST.get("pass1")
        user = authenticate(username=uname, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, "Logged in successfully as admin")
            return redirect("/adminmanager/admin-index")
        else:
            messages.error(request, 'Incorrect user info')
            return redirect('admin-login')

    return render(request, "admin/admin-login.html")


@never_cache
@login_required
def admin_logout(request):
    logout(request)
    messages.success(request, "Log in to enjoy more")
    return redirect("/adminmanager/admin-login")


@login_required
def admin_index(request):
    user = request.user
    context = {
        'user': user
    }
    return render(request, "admin/admin-index.html", context)


@login_required
def admin_user_list(request):
    active_filter = request.GET.get('active')
    if active_filter == 'active':
        users = User.objects.filter(is_superuser=False, is_active=True)
    elif active_filter == 'inactive':
        users = User.objects.filter(is_superuser=False, is_active=False)
    else:
        users = User.objects.filter(is_superuser=False).order_by("id")
    return render(request, "admin/admin-user.html", {"users": users})


@login_required
def block_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_active = False
    user.save()
    return redirect("/adminmanager/admin-user")


@login_required
def unblock_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_active = True
    user.save()
    return redirect("/adminmanager/admin-user")


# category
@login_required
def Category_List(request):
    context = {"cat": Category.objects.all()}
    return render(request, "admin/category_list.html", context)


@login_required
def Edit_Cat(request, id):
    cat = get_object_or_404(Category, pk=id)

    if request.method == "POST":
        category_name = request.POST.get("category_name")
        category_details = request.POST.get(
            "category_details"
        )  # Updated variable name
        if Category.objects.filter(category_name=category_name).exclude(pk=id).exists():
            messages.error(request, 'same category exists try another name')
            return redirect('category')
            # Validate category name
        if not category_name.isalnum():
            messages.warning(request, "Category can only contain letters and numbers.")
            return redirect('edit_category', id=id)

        if len(category_name) < 3:
            messages.error(request, "Category name must be at least 3 characters long.")
            return redirect('edit_category', id=id)
        cat.category_name = category_name
        cat.category_details = category_details
        cat.save()

        return redirect("/adminmanager/category")

    context = {"cat": cat}
    return render(request, "admin/edit_category.html", context)


@login_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("category_name")
        details = request.POST.get("category_details")

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin/add_category.html")
        # to check the no blank space
        if not name.isalnum():
            messages.error(request, 'Requir a Category name')
            return redirect('add_category')

        try:
            Category.objects.get(category_name=name)
            messages.warning(request, "Category already exists.")
            return render(request, "admin/add_category.html")
        except Category.DoesNotExist:
            pass

        try:
            Category.objects.create(
                category_name=name, category_details=details, is_available=True
            )
            messages.success(request, "Category added successfully.")
            return redirect("/adminmanager/category")
        except Exception as e:
            messages.error(request, f"Error occurred while adding category: {str(e)}")
            return render(request, "admin/add_category.html")

    return render(request, "admin/add_category.html")


@login_required
def soft_delete_category(request, id):
    try:
        cat = Category.objects.get(pk=id)
    except Category.DoesNotExist:
        return redirect("/adminmanager/category")

    # Soft delete logic
    if cat.soft_deleted:  # If already soft deleted, revert the changes
        cat.soft_deleted = False
        cat.is_available = True
    else:  # If not soft deleted, perform soft delete
        cat.soft_deleted = True
        cat.is_available = False

    cat.save()
    return redirect("/adminmanager/category")


@login_required
def undo_soft_delete_category(request, id):
    try:
        cat = Category.objects.get(pk=id)
    except Category.DoesNotExist:
        return redirect("/adminmanager/category")

    # Undo the soft delete by setting soft_deleted to False and availability to True
    cat.soft_deleted = False
    cat.is_available = True

    cat.save()
    return redirect("/adminmanager/category")


# product

@login_required
def Product_list(request):
    categories = Category.objects.all()
    products = Product.objects.all()  # Initially fetch all products

    selected_category_id = request.GET.get(
        "category_id"
    )  # Get selected category ID from query parameters

    if selected_category_id:
        # Filter products based on the selected category
        products = Product.objects.filter(category__id=selected_category_id)

    context = {
        "categories": categories,
        "products": products,
    }
    return render(request, "admin/product_list.html", context)


@login_required
def Add_Product(request):
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        product_image = request.FILES.get("product_images")
        more_product_images = request.FILES.getlist("more_product_images")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        price = request.POST.get("price")
        quantity = request.POST.get("quantity")

        # Check if all required fields are provided
        if not all([product_name, category_id, description, price, quantity]):
            messages.error(request, "Please provide all required fields.")
            return redirect("/adminmanager/add_product")
        if not product_name.isalnum():
            messages.error(request, 'Requir a Product name')
            return redirect("add_product")
        try:
            price = float(price)
            quantity = int(quantity)
            if price <= 0 or quantity <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Price and quantity must be positive numbers.")
            return redirect("/adminmanager/add_product")

        # Check if a product with the same name already exists
        if Product.objects.filter(product_name=product_name).exists():
            messages.error(request, f"A product with the name '{product_name}' already exists.")
            return redirect("/adminmanager/add_product")

        try:
            category = Category.objects.get(pk=category_id)
            product = Product.objects.create(
                product_name=product_name,
                category=category,
                description=description,
                price=price,
                quantity=quantity,
                available=True,
            )

            # Save the main product image
            if product_image:
                product.product_images = product_image
                product.save()

            # Save additional product images
            for image in more_product_images:
                ProductImage.objects.create(product=product, image=image)

            return redirect("/adminmanager/product_list")
        except Category.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return redirect("/adminmanager/add_product")
        except Exception as e:
            messages.error(request, f"Error occurred: {str(e)}")
            return redirect("/adminmanager/add_product")

    categories = Category.objects.all().order_by("id")
    context = {"categories": categories}
    return render(request, "admin/add_product.html", context)


@login_required
def Edit_Product(request, id):
    try:
        product = Product.objects.get(pk=id)
    except Product.DoesNotExist:
        messages.error(request, "Product does not exist.")
        return redirect("/adminmanager/product_list")

    categories = Category.objects.all().order_by("id")

    if request.method == "POST":
        product_name = request.POST.get("product_name")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        price = request.POST.get("price")
        quantity = request.POST.get("quantity")

        if not all([product_name, category_id, description, price, quantity]):
            messages.error(request, "Please provide all required fields.")
            return redirect(f"/adminmanager/edit_product/{id}/")

        try:
            price = float(price)
            quantity = int(quantity)
            if price <= 0 or quantity <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Price and quantity must be positive numbers.")
            return redirect(f"/adminmanager/edit_product/{id}/")

        if Product.objects.filter(product_name=product_name).exclude(pk=id).exists():
            messages.error(request, f"A product with the name '{product_name}' already exists.")
            return redirect(f"/adminmanager/edit_product/{id}/")

        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return redirect(f"/adminmanager/edit_product/{id}/")

        product.product_name = product_name
        product.category = category
        product.description = description
        product.price = price
        product.quantity = quantity
        product.save()

        images = request.FILES.getlist("product_images")
        if images:
            product.product_images = images[0]
            product.save()

            product.images.all().delete()

            for image in images[1:]:
                ProductImage.objects.create(product=product, image=image)

        return redirect("/adminmanager/product_list")

    context = {
        "product": product,
        "categories": categories,
    }
    return render(request, "admin/edit_product.html", context)


@login_required
def soft_delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.soft_deleted = True
    product.available = False
    product.save()
    return redirect("/adminmanager/product_list")


@login_required
def undo_soft_delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.soft_deleted = False
    product.available = True
    product.save()
    return redirect("/adminmanager/product_list")


# variants
def view_variant(request, product_id):
    # Retrieve the product instance based on the provided product_id
    product = get_object_or_404(Product, id=product_id)

    # Retrieve all variants associated with the product
    variants = Variant.objects.filter(product=product)
    if not variants.exists():  # Check if the QuerySet is empty
        return redirect('add_varient')
    variant_ratings = {}
    for variant in variants:
        reviews = ReviewRating.objects.filter(variant=variant)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        print(average_rating)
        variant_ratings[variant.id] = average_rating
        print(f"Reviews for variant {variant.id}: {reviews}")
        print(f"Average rating for variant {variant.id}: {average_rating}")
    context = {
        'product': product,
        'variants': variants,
        # 'review': reviews,
        'variant_ratings': variant_ratings,
    }
    # Render the view_variant template with the provided context
    return render(request, 'admin/view_variant.html', context)


@login_required
def admin_view_review(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)
    variant_reviews = ReviewRating.objects.filter(variant=variant)
    print(variant_reviews)

    context = {
        'variant_reviews': variant_reviews,
        'variant_id': variant_id
    }
    return render(request, "admin/admin_view_review.html", context)


@login_required
def admin_block_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)
    review.status = False
    review.save()
    messages.success(request, 'Review Blocked successfully.')
    return redirect('admin_view_review', variant_id=review.variant_id)


@login_required
def admin_unblock_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)
    review.status = True
    review.save()
    messages.success(request, 'Review Unblocked successfully.')
    return redirect('admin_view_review', variant_id=review.variant_id)


@login_required
def add_varient(request):
    if request.method == 'POST':
        form = VariantForm(request.POST)
        if form.is_valid(): 
            form.save()
            return redirect('product_list')
    else:
        form = VariantForm()
    products = Product.objects.all()
    context = {
        'products': products,
        'form': form

    }
    return render(request, 'admin/add_varient.html', context)


# @login_required
# def edit_varient(request, id):
#     variant = Variant.objects.get(pk=id)
#     if request.method == 'POST':
#         form = VariantForm(request.POST, instance=variant)
#         if form.is_valid():
#             form.save()
#             return redirect('view_variant', product_id=variant.product.first().id)
#     else:
#         form = VariantForm(instance=variant)

#     context = {
#         'variant': variant,
#         'form': form,
#         'products': Product.objects.all()
#     }

#     return render(request, "admin/edit_varient.html", context)


def edit_varient(request, id):
    variant = get_object_or_404(Variant, pk=id)
    if request.method == 'POST':
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            return redirect('view_variant', product_id=variant.product.first().id)
    else:
        form = VariantForm(instance=variant)

    context = {
        'variant': variant,
        'form': form,
        'products': Product.objects.all()  # This may not be necessary if the form handles product selection.
    }

    return render(request, "admin/edit_varient.html", context)


@login_required
def delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product.first()
    variants.deleted = True
    print("delete=true")
    variants.is_available = False
    variants.save()
    return redirect("view_variant",  product_id=product.id)


@login_required
def undo_delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product.first()
    variants.deleted = False
    variants.is_available = True
    variants.save()
    return redirect("view_variant",  product_id=product.id)

@login_required
def admin_order_view(request):
    orders = Orders.objects.all().select_related('user', 'delivery_address').prefetch_related('orderitem_set')
    context = {
        'orders': orders
    }
    return render(request, 'admin/order_view.html', context)

@login_required
def admin_delete_order(request, orderid):
    order = Orders.objects.get(id=orderid)
    order.status = 'Cancelled'
    order.save()
    return redirect('admin_order_view')


@login_required
def dashboard(request):
    if request.user.is_superuser:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        recent_orders = Orders.objects.filter(is_active=True).order_by('-order_date')[:10]

        last_year = end_date - timedelta(days=365)
        yearly_order_counts = (
            Orders.objects
            .filter(order_date__range=(last_year, end_date), is_active=True)
            .values('order_date__year')
            .annotate(order_count=Count('id'))
            .order_by('order_date__year')
        )

        month = end_date - timedelta(days=30)
        monthly_earnings = (
            Orders.objects
            .filter(order_date__range=(month, end_date), is_active=True)
            .aggregate(total_order_total=Sum('order_total'))
        )['total_order_total'] or Decimal('0.00')

        monthly_earnings = Decimal(monthly_earnings).quantize(Decimal('0.00'))

        daily_order_counts = (
            Orders.objects
            .filter(order_date__range=(start_date, end_date), is_active=True)
            .values('order_date__date')
            .annotate(order_count=Count('id'))
            .order_by('order_date__date')
        )

        dates = [entry['order_date__date'].strftime('%Y-%m-%d') for entry in daily_order_counts]
        counts = [entry['order_count'] for entry in daily_order_counts]

        context = {
            'admin_name': request.user.username,
            'dates': dates,
            'counts': counts,
            'orders': recent_orders,
            'yearly_order_counts': yearly_order_counts,
            'monthly_earnings': monthly_earnings,
            'order_count': len(recent_orders),
        }

        return render(request, 'admin/dashboard.html', context)
    else:
        return HttpResponseForbidden("You don't have permission to access this page.")


# def product_sale_page(request):
#     variants = Product.objects.all()
#     product_data = []
#     for product in products:
#         variants = Variant.objects.filter(product=product)
#         variant_data = []
#         for variant in variants:
#             orders = OrderItem.objects.filter(variant=variant)
#             total_sales = sum(order.quantity for order in orders)
#             total_revenue = sum(order.quantity * order.price for order in orders)
#             variant_data.append({
#                 'variant': variant,
#                 'total_sales': total_sales,
#                 'total_revenue': total_revenue
#             })
#         product_data.append({
#             'product': product,
#             'variants': variant_data
#         })
#     return render(request, 'admin/product_sale_page.html',
#                   {'product_data': product_data})