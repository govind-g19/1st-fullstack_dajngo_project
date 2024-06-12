from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Category, Product, ProductImage, Variant, ReviewRating
from .models import ProductOffers
from orders.models import Orders, OrderItem
from authapp.models import Wallet, Transaction
# from orders.models import Payment, OrderItem
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from .forms import VariantForm
from django.db.models import Avg, Sum, Count
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta, date
from decimal import Decimal
from .forms import UpdateOrderStatusForm, ProductOfferForm
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

def superuser_required(function=None):
    """
    Decorator for views that checks if the user is a superuser.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url='/admin-login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


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
@superuser_required
def admin_logout(request):
    logout(request)
    messages.success(request, "Log in to enjoy more")
    return redirect("/adminmanager/admin-login")


@superuser_required
def admin_index(request):
    user = request.user
    context = {
        'user': user
    }
    return render(request, "admin/admin-index.html", context)


@superuser_required
def admin_user_list(request):
    active_filter = request.GET.get('active')
    if active_filter == 'active':
        users = User.objects.filter(is_active=True)
    elif active_filter == 'inactive':
        users = User.objects.filter(is_active=False)
    elif active_filter == 'superuser':
        users = User.objects.filter(is_superuser=True)
    else:
        users = User.objects.all().order_by("id").exclude(id=request.user.id)
    return render(request, "admin/admin-user.html", {"users": users})


@superuser_required
def block_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_active = False
    user.save()
    return redirect("/adminmanager/admin-user")


@superuser_required
def promote_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_superuser = True
    user.save()
    return redirect("/adminmanager/admin-user")


@superuser_required
def depromote_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_superuser = False
    user.save()
    return redirect("/adminmanager/admin-user")


@superuser_required
def unblock_user(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return redirect("/adminmanager/admin-user")
    user.is_active = True
    user.save()
    return redirect("/adminmanager/admin-user")


# category
@superuser_required
def Category_List(request):
    context = {"cat": Category.objects.all()}
    return render(request, "admin/category_list.html", context)


@superuser_required
def Edit_Cat(request, id):
    cat = get_object_or_404(Category, pk=id)

    if request.method == "POST":
        category_name = request.POST.get("category_name")
        category_details = request.POST.get(
            "category_details"
        )  # Updated variable name
        if Category.objects.filter(category_name=category_name).exclude(
                pk=id).exists():
            messages.error(request, 'same category exists try another name')
            return redirect('category')
            # Validate category name
        if not category_name.isalnum():
            messages.warning(request, '''Category can only contain
                              letters and numbers.''')
            return redirect('edit_category', id=id)

        if len(category_name) < 3:
            messages.error(request, '''Category name must be at
                            least 3 characters long.''')
            return redirect('edit_category', id=id)
        cat.category_name = category_name
        cat.category_details = category_details
        cat.save()

        return redirect("/adminmanager/category")

    context = {"cat": cat}
    return render(request, "admin/edit_category.html", context)


@superuser_required
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
            messages.error(request, f'''Error occurred while
                            adding category: {str(e)}''')
            return render(request, "admin/add_category.html")

    return render(request, "admin/add_category.html")


@superuser_required
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


@superuser_required
def undo_soft_delete_category(request, id):
    try:
        cat = Category.objects.get(pk=id)
    except Category.DoesNotExist:
        return redirect("/adminmanager/category")

    cat.soft_deleted = False
    cat.is_available = True

    cat.save()
    return redirect("/adminmanager/category")


# product

@superuser_required
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


@superuser_required
def Add_Product(request):
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        product_image = request.FILES.get("product_images")
        more_product_images = request.FILES.getlist("more_product_images")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        product_offer_id = request.POST.get("product_offer_id")

        product_offer = get_object_or_404(ProductOffers, id=product_offer_id)
        # offer validations
        if product_offer:
            now = timezone.now()
            valid_from_date = product_offer.valid_from
            valid_to_date = product_offer.valid_to

            if not (valid_from_date <= now <= valid_to_date):
                messages.error(request, f'''{product_offer} offer is not valid
                                within the current date or time.''')
                return redirect("/adminmanager/add_product")
            if not product_offer.active:
                messages.error(request,
                               f'{product_offer} offer is not active.')
                return redirect("/adminmanager/add_product")

        # Check if all required fields are provided
        if not all([product_name, category_id, description]):
            messages.error(request, "Please provide all required fields.")
            return redirect("/adminmanager/add_product")
        if not product_name.isalnum():
            messages.error(request, 'Requir a Product name')
            return redirect("add_product")

        # Check if a product with the same name already exists
        if Product.objects.filter(product_name=product_name).exists():
            messages.error(request, f'''A product with the name
                            '{product_name}' already exists.''')
            return redirect("/adminmanager/add_product")

        try:
            category = Category.objects.get(pk=category_id)
            product = Product.objects.create(
                product_name=product_name,
                category=category,
                description=description,
                available=True,
                product_offer=product_offer
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
        
    product_offers = ProductOffers.objects.all()
    categories = Category.objects.all().order_by("id")
    context = {"categories": categories,
               'product_offers': product_offers
               }
    return render(request, "admin/add_product.html", context)


@superuser_required
def Edit_Product(request, id):
    try:
        product = Product.objects.get(pk=id)
    except Product.DoesNotExist:
        messages.error(request, "Product does not exist.")
        return redirect("/adminmanager/product_list")

    categories = Category.objects.all().order_by("id")
    product_offers = ProductOffers.objects.all()

    if request.method == "POST":
        product_name = request.POST.get("product_name")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        product_offer_id = request.POST.get("product_offer_id")

        product_offer = get_object_or_404(ProductOffers, id=product_offer_id)
        # product offer validation
        if product_offer:
            now = timezone.now()
            valid_from_date = product_offer.valid_from
            valid_to_date = product_offer.valid_to
            # Currect time validation
            if not (valid_from_date <= now <= valid_to_date):
                messages.error(request, f'''{product_offer} offer is not valid
                                within the current date or time.''')
                return redirect('edit_product', id=id)
            if not product_offer.active:
                messages.error(request,
                               f'{product_offer} offer is not active.')
                return redirect('edit_product', id=id)
        
        if not all([product_name, category_id, description]):
            messages.error(request, "Please provide all required fields.")
            return redirect(f"/adminmanager/edit_product/{id}/")
        if Product.objects.filter(product_name=product_name).exclude(
                pk=id).exists():
            messages.error(request, f'''A product with the name
                            '{product_name}' already exists.''')
            return redirect(f"/adminmanager/edit_product/{id}/")

        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
            return redirect(f"/adminmanager/edit_product/{id}/")

        product.product_name = product_name
        product.category = category
        product.description = description
        product.product_offer = product_offer
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
        'product_offers': product_offers
    }
    return render(request, "admin/edit_product.html", context)


@superuser_required
def soft_delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.soft_deleted = True
    product.available = False
    product.save()
    return redirect("/adminmanager/product_list")


@superuser_required
def undo_soft_delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.soft_deleted = False
    product.available = True
    product.save()
    return redirect("/adminmanager/product_list")


# variants
@superuser_required
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


@superuser_required
def admin_view_review(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)
    variant_reviews = ReviewRating.objects.filter(variant=variant)

    # Get the rating filter from the query parameters
    rating_filter = request.GET.get('rating')

    # Filter the reviews based on the rating filter if provided
    if rating_filter:
        variant_reviews = variant_reviews.filter(rating=rating_filter)

    # Get the sorting option from the query parameters
    sort_by = request.GET.get('sort_by')

    # Sort the reviews based on the selected sorting option
    if sort_by == 'rating_asc':
        variant_reviews = variant_reviews.order_by('rating')
    elif sort_by == 'rating_desc':
        variant_reviews = variant_reviews.order_by('-rating')

    context = {
        'variant_reviews': variant_reviews,
        'variant_id': variant_id,
        'rating_filter': rating_filter,
        'sort_by': sort_by
    }
    return render(request, "admin/admin_view_review.html", context)


@superuser_required
def admin_block_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)
    review.status = False
    review.save()
    messages.success(request, 'Review Blocked successfully.')
    return redirect('admin_view_review', variant_id=review.variant_id)


@superuser_required
def admin_unblock_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)
    review.status = True
    review.save()
    messages.success(request, 'Review Unblocked successfully.')
    return redirect('admin_view_review', variant_id=review.variant_id)


@superuser_required
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


def edit_varient(request, id):
    variant = get_object_or_404(Variant, pk=id)
    if request.method == 'POST':
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            return redirect('view_variant',
                            product_id=variant.product.first().id)
    else:
        form = VariantForm(instance=variant)

    context = {
        'variant': variant,
        'form': form,
        'products': Product.objects.all()
        # This may not be necessary if the form handles product selection.
    }

    return render(request, "admin/edit_varient.html", context)


@superuser_required
def delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product.first()
    variants.deleted = True
    print("delete=true")
    variants.is_available = False
    variants.save()
    return redirect("view_variant",  product_id=product.id)


@superuser_required
def undo_delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product.first()
    variants.deleted = False
    variants.is_available = True
    variants.save()
    return redirect("view_variant",  product_id=product.id)


@superuser_required
def admin_order_view(request):
    orders = Orders.objects.all().select_related('user').prefetch_related(
        'orderitem_set')

    if request.method == 'POST':
        form = UpdateOrderStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            # Retrieve the order ID from the URL parameters
            order_id = request.POST.get('order_id')
            if order_id:
                order = get_object_or_404(Orders, id=order_id)
                order.status = new_status
                order.save()
                # Optionally, add a success message
                return redirect('admin_order_view')
            else:
                messages.error(request, 'Order ID not provided in form data')
                redirect('admin_order_view')
    else:
        form = UpdateOrderStatusForm()

    context = {
        'orders': orders,
        'form': form,
    }
    return render(request, 'admin/order_view.html', context)


@superuser_required
def admin_delete_order(request, orderid):
    try:
        order = Orders.objects.get(id=orderid)
        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            variant = get_object_or_404(Variant, id=item.variant.id)
            variant.quantity += item.quantity
            variant.save()
        if order.payment_method != 'COD':
            wallet, created = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += Decimal(order.grand_total)
            wallet.save()

            Transaction.objects.create(wallet=wallet,
                                       transaction_type='credit',
                                       amount=Decimal(order.grand_total))

        order.status = 'Cancelled'
        order.save()
        messages.success(request, 'Order successfully cancelled ')
        return redirect('admin_order_view')
    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('admin_order_view')
    except Variant.DoesNotExist:
        messages.error(request, 'Variant not found.')
        return redirect('admin_order_view')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_order_view')


@superuser_required
def dashboard(request):
    if request.user.is_superuser:
        # Get start and end dates from request parameters
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')

        # Calculate start and end dates if not provided
        if start_date_param and end_date_param:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d')
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

        recent_orders = Orders.objects.filter(
            is_active=True, order_date__range=[start_date, end_date]).order_by('-order_date')[:10]

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

        dates = [entry['order_date__date'].strftime(
            '%Y-%m-%d') for entry in daily_order_counts]
        counts = [entry['order_count'] for entry in daily_order_counts]

        context = {
            'admin_name': request.user.username,
            'dates': dates,
            'counts': counts,
            'orders': recent_orders,
            'yearly_order_counts': yearly_order_counts,
            'monthly_earnings': monthly_earnings,
            'order_count': len(recent_orders),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

        return render(request, 'admin/dashboard.html', context)
    else:
        return HttpResponseForbidden("You don't have permission to access this page.")


def update_order_status(request, order_id):
    order = get_object_or_404(Orders, id=order_id)
    if order.status == 'Cancelled':
        messages.error(request, "Cancelled orders can't be Updated")
        return redirect('admin_order_view')

    if request.method == 'POST':

        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        # Optionally, add a success message
        return redirect('admin_order_view')

    context = {'order': order}
    return render(request, 'admin/update_order_status.html', context)


@superuser_required
def detail_order(request, orderid):
    order = get_object_or_404(Orders, id=orderid)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items
    }
    return render(request, 'admin/single_ordetr_details.html', context)


@superuser_required
def sales_report(request):
    # Retrieve start and end dates from request parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Default to the last 30 days if no dates are provided
    if not start_date or not end_date:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    else:
        start_date = date.fromisoformat(start_date)
        end_date = date.fromisoformat(end_date)

    # Retrieve sales data from the database
    sales_data = Orders.objects.filter(is_active=True, order_date__range=[start_date, end_date])

    # Calculate total sales revenue
    total_revenue = sales_data.aggregate(total_sales=Sum('order_total'))['total_sales']

    # Calculate total number of orders
    total_orders = sales_data.count()

    # Calculate number of units sold
    total_units_sold = OrderItem.objects.filter(order__in=sales_data).aggregate(total_units=Sum('quantity'))['total_units']

    # Calculate average order value
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Format to have a maximum of 2 decimal points
    average_order_value = round(average_order_value, 2)

    # Retrieve top selling products
    top_products = OrderItem.objects.filter(order__in=sales_data).values('product__product_name').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity')[:5]

    # Sales by product variant
    product_variant_sales = OrderItem.objects.filter(order__in=sales_data).values(
        'variant__id', 'variant__ram', 'variant__internal_memory', 'product__product_name'
    ).annotate(
        total_revenue=Sum('price'),
        total_units=Sum('quantity')
    ).order_by('-total_revenue')

    # Sales by category
    category_sales = OrderItem.objects.filter(order__in=sales_data).values('product__category__category_name').annotate(total_revenue=Sum('price'), total_units=Sum('quantity')).order_by('-total_revenue')

    # Prepare context for rendering the template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'average_order_value': average_order_value,
        'top_products': top_products,
        'product_variant_sales': product_variant_sales,
        'category_sales': category_sales
    }

    # Render the template with the context
    return render(request, 'admin/sales_report.html', context)


def add_product_offer(request):
    if request.method == "POST":
        form = ProductOfferForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                messages.success(request, "Product offer added successfully.")
                return redirect('product_offers_list')
           
            else:
                # If form is not valid, re-render the form with error messages
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            # Log the exception or handle it appropriately
            messages.error(request, f"There was an error while saving the product offer: {e}")
    else:
        form = ProductOfferForm()

    return render(request, 'admin/add_product_offers.html', {'form': form})


def product_offers_list(request):
    product_offers = ProductOffers.objects.all()
    context = {
        'product_offers': product_offers
    }
    return render(request, 'admin/product_offer_list.html', context)


def edit_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffers, id=offer_id)
    if request.method == "POST":
        form = ProductOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product Offer is Updated')
            return redirect('product_offers_list')
    else:
        form = ProductOfferForm(instance=offer)

    return render(request, 'admin/edit_product_offer.html', {'form': form})


def delete_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffers, id=offer_id)
    offer.active = False
    offer.save()
    messages.success(request, 'The offer is deactivated')
    return redirect('product_offers_list')


def undo_delete_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffers, id=offer_id)
    offer.active = True
    offer.save()
    messages.success(request, 'The offer is activated')

    return redirect('product_offers_list')
