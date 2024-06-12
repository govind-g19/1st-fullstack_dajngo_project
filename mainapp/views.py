from django.shortcuts import render, redirect
from adminmanager.models import Category, Product, ProductImage
from adminmanager.models import Variant, ReviewRating
from authapp.models import WishList
from .models import UserQuery
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django import forms
from orders.models import OrderItem
from django.db.models import Avg
from django.http import QueryDict
from django.urls import reverse
# from django.db.models import Q
from django.db.models import Q
# Create your views here.


def index(request):
    variants = Variant.objects.all().prefetch_related('product')
    search_query = request.GET.get('q')
    if search_query:
        # Search in both product name and description using OR condition
        variants = variants.filter(
            Q(product__product_name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__category__category_name__icontains=search_query)
        )
    context = {
        'variants': variants
    }
    return render(request, 'index.html', context)


def shop(request):
    # Retrieve all categories, products, and variants
    categories = Category.objects.all()
    products = Product.objects.all()
    variants = Variant.objects.all().prefetch_related('product__category')

    # Retrieve filter values from request.GET
    ram_filter = request.GET.get('ram')
    rom_filter = request.GET.get('rom')
    category_filter = request.GET.get('category_id')
    search_query = request.GET.get('q')
    # Retrieve sorting criteria from the request
    sort_by = request.GET.get('sort_by')

    # Apply filters if provided
    if ram_filter:
        variants = variants.filter(ram=ram_filter)
    if rom_filter:
        variants = variants.filter(internal_memory=rom_filter)
    if category_filter:
        variants = variants.filter(product__category__id=category_filter)

    # Apply search if a query is provided
    if search_query:
        # Search in both product name and description using OR condition
        variants = variants.filter(
            Q(product__product_name__icontains=search_query) |
            Q(product__description__icontains=search_query) |
            Q(product__category__category_name__icontains=search_query)
        )

    # Apply sorting if provided
    if sort_by == 'name_asc':
        variants = variants.order_by('product__product_name')
    elif sort_by == 'name_desc':
        variants = variants.order_by('-product__product_name')
    elif sort_by == 'price_asc':
        variants = variants.order_by('final_price')
    elif sort_by == 'price_desc':
        variants = variants.order_by('-final_price')

    # Check if any products found after filtering
    if not variants.exists():
        if ram_filter and rom_filter:
            messages.warning(
                request, f"No products with {ram_filter} RAM and {rom_filter} ROM")

    context = {
        'categories': categories,
        'variants': variants,
        'products': products,
        'ram': ram_filter,
        'rom': rom_filter,
        'category_id': category_filter,
        'sort_by': sort_by,  # Pass the sorting criteria to the template
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'main/shop.html', context)


def base(request):
    return render(request, 'base.html')


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ['ram', 'internal_memory']


''' product id is paased with the request and variant id is taken from the
session in add to cart is pass the ram and rom with the link '''


@login_required(login_url='login')
def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = None
    wishlist = None
    variant_id = request.GET.get('variant_id')
    selected_variant = Variant.objects.filter(id=variant_id).first()
    variant_form = VariantForm()

    if request.method == 'POST':
        selected_ram = request.POST.get('ram')
        selected_internal_memory = request.POST.get('internal_memory')

        if selected_ram and selected_internal_memory:
            selected_variant = Variant.objects.filter(
                product=product, ram=selected_ram,
                internal_memory=selected_internal_memory).first()

            if selected_variant and selected_variant.is_available:
                final_price = selected_variant.final_price
                quantity = selected_variant.quantity
                variant_id = selected_variant.id
            else:
                final_price = "Not Available"
                quantity = None
        else:
            final_price = "Not Available"
            quantity = None
    else:
        if selected_variant:
            final_price = selected_variant.final_price
            quantity = selected_variant.quantity
            variant_id = selected_variant.id
        else:
            final_price = None
            quantity = None

    if selected_variant:
        variant_form = VariantForm(instance=selected_variant)

    reviews = ReviewRating.objects.filter(variant=selected_variant)
    user_review = reviews.filter(user=request.user).first()
    other_reviews = reviews.exclude(user=request.user)
    reviews_ordered = [user_review] + list(
        other_reviews) if user_review else list(other_reviews)

    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    wishlist = WishList.objects.filter(user=request.user,
                                       product=product,
                                       variant=selected_variant).first()

    context = {
        'product': product,
        'categories': Category.objects.all(),
        'product_imgs': ProductImage.objects.filter(product=product),
        'variant_form': variant_form,
        'variant_id': variant_id,
        'selected_variant': selected_variant,
        'final_price': final_price,
        'user_review': user_review,
        'quantity': quantity,
        'reviews': reviews_ordered,
        'average_rating': average_rating,
        'wishlist': wishlist
    }

    return render(request, "main/product_details.html", context)


@login_required(login_url='login')
def add_review(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)

    # Check if the user has already submitted a review for this variant
    existing_review = ReviewRating.objects.filter(user=request.user,
                                                  variant=variant).first()

    if existing_review:
        # If a review already exists, redirect to the edit review page
        return redirect('edit_review', review_id=existing_review.id)

    def purchase_product_checking(user, variant):
        return OrderItem.objects.filter(order__user=user,
                                        variant=variant).exists()

    if purchase_product_checking(request.user, variant):
        if request.method == 'POST':
            try:
                # Get review data from the request
                rating = int(request.POST.get('rating'))
                comment = request.POST.get('comment')
                review_text = request.POST.get('review')
                product_id = request.POST.get('product_id')

                # Create a ReviewRating object
                ReviewRating.objects.create(
                    user=request.user,
                    variant=variant,
                    rating=rating,
                    comment=comment,
                    review=review_text
                )
                messages.success(request, 'Review added successfully.')
                query_string = QueryDict(mutable=True)
                query_string['variant_id'] = variant.id
                redirect_url = f'''{reverse('product_details',
                                          args=[product_id])}?{
                                              query_string.urlencode()}'''
                # Redirect to the same product details page after review
                return redirect(redirect_url)
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    else:
        messages.error(request, 'Purchase the product to make a review')
        return redirect('shop')


@login_required(login_url='login')
def my_reviews(request):
    user_review = ReviewRating.objects.filter(user=request.user)
    context = {
        "user_rview": user_review
    }
    return render(request, "main/my_review.html", context)


@login_required(login_url='login')
def delete_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)
    review.status = False
    review.save()
    messages.success(request, 'Review deleted successfully.')
    return redirect('my_reviews')


@login_required(login_url='login')
def edit_review(request, review_id):
    review = get_object_or_404(ReviewRating, id=review_id)

    if request.method == 'POST':
        # Get updated review data from the request
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')
        review_text = request.POST.get('review')

        # Update the review object
        review.rating = rating
        review.comment = comment
        review.review = review_text
        review.save()

        messages.success(request, 'Review updated successfully.')
        return redirect('my_reviews')

    return render(request, 'main/edit_review.html', {'review': review})


@login_required(login_url='login')
def chat_bot(request):
    if request.method == 'POST':
        query_text = request.POST.get('query')
        if query_text:
            user_query = UserQuery(user=request.user, query=query_text)
            user_query.save()
            messages.success(request, '''Your query has been received.
                             We will respond shortly to your mail.''')
            return redirect('chat_bot')
        else:
            messages.error(request, 'Query cannot be empty.')

    context = {
        'user': request.user
    }
    return render(request, 'main/chat_bot.html', context)
