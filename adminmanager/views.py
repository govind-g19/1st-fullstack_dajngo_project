from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Category, Product, ProductImage, Variant, ReviewRating
from .models import ProductOffers, CategoryOffers
from orders.models import Orders, OrderItem
from authapp.models import Wallet, Transaction
# from orders.models import Payment, OrderItem
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from .forms import VariantForm
from django.db.models import Avg, Sum, Count, Q
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta
from decimal import Decimal
from .forms import UpdateOrderStatusForm, ProductOfferForm, CategoryOfferform
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.utils.dateparse import parse_date
import pandas as pd
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# Include these imports if not already included
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.platypus import TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter


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
    # Pagination
    paginator = Paginator(users, 8)
    page = request.GET.get('page')
    try:
        users_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page.
        users_page = paginator.page(1)
    except EmptyPage:
        # If the page is out of range (e.g., 9999), deliver the last page.
        users_page = paginator.page(paginator.num_pages)
    return render(request, "admin/admin-user.html", {"users": users_page})


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
@login_required(login_url='login')
@superuser_required
def add_category_offer(request):
    if request.method == "POST":
        form = CategoryOfferform(request.POST)
        try:
            if form.is_valid():
                form.save()
                messages.success(request, "Category offer added successfully.")
                return redirect('category_offers_list')
            else:
                # If form is not valid, re-render the form with error messages
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            # Log the exception or handle it appropriately
            messages.error(request, f"There was an error while saving the category offer: {e}")
    else:
        form = CategoryOfferform()

    return render(request, 'admin/add_category_offers.html', {'form': form})


@login_required(login_url='login')
@superuser_required
def category_offers_list(request):
    category_offers = CategoryOffers.objects.all().order_by('-id')
    context = {
        'category_offers': category_offers
    }
    return render(request, 'admin/category_offer_list.html', context)


@login_required(login_url='login')
def edit_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffers, id=offer_id)
    if request.method == "POST":
        form = CategoryOfferform(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'category Offer is Updated')
            return redirect('category_offers_list')
    else:
        form = CategoryOfferform(instance=offer)

    return render(request, 'admin/edit_category_offer.html', {'form': form})


@login_required(login_url='login')
def delete_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffers, id=offer_id)
    offer.active = False
    offer.save()
    messages.success(request, 'The offer is deactivated')
    return redirect('category_offers_list')


@login_required(login_url='login')
def undo_delete_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffers, id=offer_id)
    offer.active = True
    offer.save()
    messages.success(request, 'The offer is activated')

    return redirect('category_offers_list')


@superuser_required
def Category_List(request):
    category = Category.objects.all().order_by('-id')
    # Pagination
    paginator = Paginator(category, 5)
    page = request.GET.get('page')
    try:
        category_page = paginator.page(page)
    except PageNotAnInteger:
        category_page = paginator.page(1)
    except EmptyPage:
        category_page = paginator.page(paginator.num_pages)

    context = {"cat": category_page}
    return render(request, "admin/category_list.html", context)


@superuser_required
def Edit_Cat(request, id):
    cat = get_object_or_404(Category, pk=id)

    if request.method == "POST":
        category_name = request.POST.get("category_name")
        category_details = request.POST.get("category_details")
        category_offer_id = request.POST.get("category_offer_id")
        # to pass all the category offers
        if category_offer_id:
            category_offer = get_object_or_404(CategoryOffers,
                                               id=category_offer_id)
        else:
            category_offer = None
        # category offer validation
        if category_offer:
            now = timezone.now()
            valid_from_date = category_offer.valid_from
            valid_to_date = category_offer.valid_to
            # Currect time validation
            if not (valid_from_date <= now <= valid_to_date):
                messages.error(request, f'''{category_offer} offer is not valid
                                within the current date or time.''')
                return redirect('edit_category', id=id)
            if not category_offer.active:
                messages.error(request,
                               f'{category_offer} offer is not active.')
                return redirect('edit_category', id=id)
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
        cat.category_offer = category_offer
        cat.save()
        messages.success(request, 'the Category is edited')
        return redirect("category")

    category_offers = CategoryOffers.objects.all()

    context = {"cat": cat,
               'category_offers': category_offers
               }
    return render(request, "admin/edit_category.html", context)


@superuser_required
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("category_name")
        details = request.POST.get("category_details")
        category_offer_id = request.POST.get("category_offer_id")

        # Ensure category_offer_id is valid
        category_offer = None
        if category_offer_id:
            category_offer = get_object_or_404(CategoryOffers,
                                               id=category_offer_id)

        # Offer validations
        if category_offer:
            now = timezone.now()
            valid_from_date = category_offer.valid_from
            valid_to_date = category_offer.valid_to

            if not (valid_from_date <= now <= valid_to_date):
                messages.error(request,
                               f'''The offer {category_offer.category_offer}
                                 is not valid within the current date or time
                                 .''')
                return redirect('add_category')

            if not category_offer.active:
                messages.error(request, f'''The offer
                                {category_offer.category_offer}
                                  is not active.''')
                return redirect('add_category')

        # Check for blank spaces and ensure the name is alphanumeric
        if not name.isalnum():
            messages.error(request, 'Category name must be alphanumeric.')
            return redirect('add_category')

        # Check if category already exists
        if Category.objects.filter(category_name=name).exists():
            messages.warning(request, "Category already exists.")
            return redirect('add_category')

        # Create the new category
        try:
            Category.objects.create(
                category_name=name,
                category_details=details,
                is_available=True,
                category_offer=category_offer
            )
            messages.success(request, "Category added successfully.")
            return redirect('category')
        except Exception as e:
            messages.error(request,
                           f'Error occurred while adding category: {str(e)}')
            return render(request, "admin/add_category.html")

    # Handle GET request
    category_offers = CategoryOffers.objects.all()
    context = {
        'category_offers': category_offers
    }
    return render(request, "admin/add_category.html", context)


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
    products = Product.objects.all().order_by('-id')
    selected_category_id = request.GET.get(
        "category_id"
    )  # Get selected category ID from query parameters

    if selected_category_id:
        # Filter products based on the selected category
        products = Product.objects.filter(category__id=selected_category_id)
    paginator = Paginator(products, 4)
    page = request.GET.get('page')
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    context = {
        "categories": categories,
        "products": products_page,
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
        product_offer = None
        if product_offer_id:
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
            else:
                product_offer = None

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
        # To save the product
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
    variants = Variant.objects.filter(product=product).order_by('-id')
    if not variants.exists():  # Check if the QuerySet is empty
        return redirect('add_variant', product_id=product_id)
    variant_ratings = {}
    for variant in variants:
        reviews = ReviewRating.objects.filter(variant=variant)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        variant_ratings[variant.id] = average_rating
        
    context = {
        'product': product,
        'variants': variants,
        'product_id': product_id,
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
def add_variant(request, product_id):
    products = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = VariantForm(request.POST, product_id=product_id)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            existing_variant = Variant.objects.filter(
                product=products,
                ram=cleaned_data['ram'],
                internal_memory=cleaned_data['internal_memory']
            )
            if existing_variant.exists():
                form.add_error(None, '''Variant with the same RAM and internal
                                memory already exists for this product.''')
            else:
                variant = form.save(commit=False)
                variant.product = products
                variant.save()
                form.save()
                return redirect('view_variant', product_id=product_id)
    else:
        form = VariantForm()
    context = {
        'products': products,
        'form': form

    }
    return render(request, 'admin/add_varient.html', context)


def edit_varient(request, id):
    variant = get_object_or_404(Variant, pk=id)
    product = variant.product

    if request.method == 'POST':
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            existing_variant = Variant.objects.filter(
                product=product,
                ram=cleaned_data['ram'],
                internal_memory=cleaned_data['internal_memory']
            )
            if (existing_variant.exists() and
               existing_variant.first().id != variant.id):
                messages.error(request, 'variant already excists')
                return redirect('edit_varient', id=variant.id)
            else:
                variant = form.save(commit=False)
                variant.product = product
                variant.save()
                form.save()
            return redirect('view_variant', product_id=product.id)
    else:
        form = VariantForm(instance=variant)

    context = {
        'variant': variant,
        'form': form,
    }

    return render(request, "admin/edit_varient.html", context)


@superuser_required
def delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product
    variants.deleted = True
    variants.is_available = False
    variants.save()
    return redirect("view_variant",  product_id=product.id)


@superuser_required
def undo_delete_variant(request, product_id):
    variants = get_object_or_404(Variant, pk=product_id)
    product = variants.product
    variants.deleted = False
    variants.is_available = True
    variants.save()
    return redirect("view_variant",  product_id=product.id)


@superuser_required
def admin_order_view(request):
    orders = Orders.objects.all().select_related('user').prefetch_related(
        'orderitem_set').order_by('-order_date')
    orders = Orders.objects.filter(user=request.user).order_by('-order_date')

    # Paginate orders
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
        'orders': page_obj,
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
            is_active=True, order_date__range=[
                start_date, end_date]).order_by('-order_date')[:10]

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
        return HttpResponseForbidden(
            "You don't have permission to access this page.")


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
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    date_range = request.GET.get('date_range')

    if not start_date_param or not end_date_param:
        if date_range == "1 Day":
            start_date = datetime.today()
            end_date = start_date + timedelta(days=1)
        elif date_range == "1 Week":
            start_date = datetime.today() - timedelta(days=7)
            end_date = datetime.today()
        elif date_range == "1 Month":
            start_date = datetime.today() - timedelta(days=30)
            end_date = datetime.today()
        else:
            start_date = datetime.today() - timedelta(days=30)
            end_date = datetime.today()
    else:
        start_date = parse_date(start_date_param)
        end_date = parse_date(end_date_param)

    sales_data = Orders.objects.filter(order_date__range=[
        start_date, end_date])

    total_revenue = sales_data.aggregate(total_sales=Sum('grand_total'))[
        'total_sales']
    total_orders = sales_data.count()
    total_units_sold = OrderItem.objects.filter(
        order__in=sales_data).aggregate(total_units=Sum(
            'quantity'))['total_units']

    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    average_order_value = round(average_order_value, 2)

    top_products = OrderItem.objects.filter(
        order__in=sales_data).values('product__product_name').annotate(
            total_quantity=Sum('quantity')).order_by('-total_quantity')[:5]

    product_variant_sales = OrderItem.objects.filter(
        order__in=sales_data).values(
        'variant__id', 'variant__ram', 'variant__internal_memory',
        'product__product_name'
    ).annotate(
        total_revenue=Sum('price'),
        total_units=Sum('quantity')
    ).order_by('-total_revenue')

    category_sales = OrderItem.objects.filter(
        order__in=sales_data).values(
            'product__category__category_name').annotate(
                total_revenue=Sum('price'), total_units=Sum(
                    'quantity')).order_by('-total_revenue')

    items_with_offer = OrderItem.objects.filter(
        order__in=sales_data,
        product_discount__gt=0,
        category_discount__gt=0
    )

    items_with_coupons = Orders.objects.filter(
        Q(is_active=True, order_date__range=[start_date, end_date]) & (Q(coupon_discount__gt=0)))

    order_details = Orders.objects.filter(order_date__range=[start_date, end_date]).select_related('user').prefetch_related('orderitem_set')

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'sales_data': sales_data,
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'average_order_value': average_order_value,
        'top_products': top_products,
        'product_variant_sales': product_variant_sales,
        'category_sales': category_sales,
        'items_with_offer': items_with_offer,
        'items_with_coupons': items_with_coupons,
        'order_details': order_details,
        'total_orders': total_orders,
    }

    export_type = request.GET.get('export')
    if export_type == 'excel':
        return export_to_excel(context)
    elif export_type == 'pdf':
        return export_to_pdf(context)

    return render(request, 'admin/sales_report.html', context)


def export_to_excel(context):
    summary_data = {
        'Metric': ['Total Revenue', 'Total Units Sold', 'Average Order Value', 'Total Orders'],
        'Value': [
            context['total_revenue'],
            context['total_units_sold'],
            context['average_order_value'],
            context['total_orders']
        ]
    }

    top_products_data = {
        'Product': [product['product__product_name'] for product in context['top_products']],
        'Total Quantity Sold': [product['total_quantity'] for product in context['top_products']]
    }

    product_variant_data = {
        'Product': [variant['product__product_name'] for variant in context['product_variant_sales']],
        'Variant (RAM)': [variant['variant__ram'] for variant in context['product_variant_sales']],
        'Variant (Internal Memory)': [variant['variant__internal_memory'] for variant in context['product_variant_sales']],
        'Total Revenue': [variant['total_revenue'] for variant in context['product_variant_sales']],
        'Total Units Sold': [variant['total_units'] for variant in context['product_variant_sales']]
    }

    category_sales_data = {
        'Category': [category['product__category__category_name'] for category in context['category_sales']],
        'Total Revenue': [category['total_revenue'] for category in context['category_sales']],
        'Total Units Sold': [category['total_units'] for category in context['category_sales']]
    }

    order_data = []
    for order in context['order_details']:
        for item in order.orderitem_set.all():
            order_data.append([
                order.order_id, order.user.username, order.grand_total, order.status, order.payment_method,
                order.order_date.strftime('%Y-%m-%d %H:%M'),
                f"{item.product.product_name} - {item.variant} - {item.quantity} - ₹{item.price}",
                item.product_discount, item.category_discount
            ])
    summary_data = {
        'Metric': ['Total Revenue', 'Total Units Sold', 'Average Order Value', 'Total Orders'],
        'Value': [
            context['total_revenue'],
            context['total_units_sold'],
            context['average_order_value'],
            context['total_orders']
        ]
    }

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=sales_report.xlsx'

    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(top_products_data).to_excel(writer, sheet_name='Top Selling Products', index=False)
        pd.DataFrame(product_variant_data).to_excel(writer, sheet_name='Product Variant Sales', index=False)
        pd.DataFrame(category_sales_data).to_excel(writer, sheet_name='Category Sales', index=False)
        pd.DataFrame(order_data, columns=[
            'Order ID', 'User', 'Total', 'Status', 'Payment Method', 'Order Date', 'Items', 'Product Discount', 'Category Discount'
        ]).to_excel(writer, sheet_name='Order Details', index=False)

    return response


@login_required(login_url='login')
def export_to_pdf(context):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=sales_report.pdf'

    pdf = SimpleDocTemplate(response, pagesize=letter)
    page_width = letter[0]
    table_width = 0.8 * page_width
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph('Sales Report', styles['Title']))
    elements.append(Paragraph('Report initialized date  ', styles['Heading2']))
    elements.append(Paragraph(f"From {context['start_date'].strftime('%d-%m-%Y')} to {context['end_date'].strftime('%d-%m-%Y')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Function to create tables with specified width
    def create_table(data, col_widths):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        return table

    # Summary Table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Revenue', context['total_revenue']],
        ['Total Units Sold', context['total_units_sold']],
        ['Average Order Value', context['average_order_value']],
        ['Total Orders', context['total_orders']],
    ]
    elements.append(Paragraph('Summary', styles['Heading2']))
    summary_col_widths = [table_width * 0.5, table_width * 0.5]
    summary_table = create_table(summary_data, summary_col_widths)
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Top Products Table
    elements.append(Paragraph('Top Selling Products', styles['Heading2']))
    top_products_data = [['Product', 'Total Quantity Sold']]
    for product in context['top_products']:
        top_products_data.append([product['product__product_name'], product['total_quantity']])
    top_products_col_widths = [table_width * 0.5, table_width * 0.5]
    top_products_table = create_table(top_products_data, top_products_col_widths)
    elements.append(top_products_table)
    elements.append(Spacer(1, 12))

    # Items with Offer Table
    elements.append(Paragraph('Items with Offer', styles['Heading2']))
    items_with_offer_data = [['Order ID', 'User', 'Product', 'Ram', 'ROM', 'Quantity', 'Offer', 'P-Discount', 'C-discount']]
    for item in context['items_with_offer']:
        items_with_offer_data.append([
            item.order.order_id,
            item.order.user.username,
            item.product.product_name,
            item.variant.ram,
            item.variant.internal_memory,
            item.quantity,
            item.offer_price,
            item.product_discount,
            item.category_discount,
        ])
    items_with_offer_col_widths = [
        table_width * 0.1, table_width * 0.1, table_width * 0.15,table_width * 0.1,
        table_width * 0.1, table_width * 0.125, table_width * 0.125,
        table_width * 0.125, table_width * 0.125
    ]
    items_with_offer_table = create_table(items_with_offer_data, items_with_offer_col_widths)
    elements.append(items_with_offer_table)
    elements.append(Spacer(1, 12))

    # Items with Coupons Table
    elements.append(Paragraph('Items with Coupons', styles['Heading2']))
    items_with_coupons_data = [['Order ID', 'User Name', 'Coupon Discount']]
    for order in context['items_with_coupons']:
        items_with_coupons_data.append([
            order.order_id,
            order.user.username,
            order.coupon_discount,
        ])
    items_with_coupons_col_widths = [table_width * 0.33, table_width * 0.33, table_width * 0.33]
    items_with_coupons_table = create_table(items_with_coupons_data, items_with_coupons_col_widths)
    elements.append(items_with_coupons_table)
    elements.append(Spacer(1, 12))

    # Order Details Table
    elements.append(Paragraph('Order Details', styles['Heading2']))
    order_details_data = [['Order ID', 'User', 'Total', 'Status', 'Payment', 'Order Date', 'Product', 'Quantity', 'Price', 'Offer Price']]

    for order in context['order_details']:
        for item in order.orderitem_set.all():
            # Append each item detail as a separate row
            order_details_data.append([
                order.order_id,
                order.user.username,
                order.grand_total,
                order.status,
                order.payment_method,
                order.order_date.strftime('%Y-%m-%d'),
                item.product.product_name,
                item.quantity,
                f"{item.price}",
                f"{item.offer_price}"
            ])

    # Define column widths
    page_width = letter[0]  # Width of the letter-sized page
    table_width = .8 * page_width
    order_details_col_widths = [
        table_width * 0.1, table_width * 0.15, table_width * 0.1, 
        table_width * 0.1, table_width * 0.1, table_width * 0.15, 
        table_width * 0.15, table_width * 0.1, table_width * 0.1, table_width * 0.1
    ]

    # Create the table
    order_details_table = Table(order_details_data, colWidths=order_details_col_widths)
    order_details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(order_details_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph('Items', styles['Heading2']))

    # Prepare data for Items Table
    items_table_data = [['Order ID', 'Product Name', 'Variant', 'Product Discount', 'Category Discount']]

    for order in context['order_details']:
        for item in order.orderitem_set.all():
            items_table_data.append([
                order.order_id,
                item.product.product_name,
                f"{item.variant.internal_memory} - {item.variant.ram}",  # Example of combining variant details
                item.product_discount,
                item.category_discount,
            ])

    # Define column widths for Items Table
    items_table_col_widths = [
        table_width * 0.2, table_width * 0.2, table_width * 0.2,
        table_width * 0.2, table_width * 0.2
    ]

    # Create the Items Table
    items_table = Table(items_table_data, colWidths=items_table_col_widths)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Append Items Table to elements list
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    # Build the PDF
    pdf.build(elements)
    return response


# Product Offer
@login_required(login_url='login')
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


@login_required(login_url='login')
def product_offers_list(request):
    product_offers = ProductOffers.objects.all()
    context = {
        'product_offers': product_offers
    }
    return render(request, 'admin/product_offer_list.html', context)


@login_required(login_url='login')
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


@login_required(login_url='login')
def delete_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffers, id=offer_id)
    offer.active = False
    offer.save()
    messages.success(request, 'The offer is deactivated')
    return redirect('product_offers_list')


@login_required(login_url='login')
def undo_delete_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffers, id=offer_id)
    offer.active = True
    offer.save()
    messages.success(request, 'The offer is activated')

    return redirect('product_offers_list')
