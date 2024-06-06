from django.shortcuts import render, redirect
from adminmanager.models import Category, Product, ProductImage
from adminmanager.models import Variant, ReviewRating
from .models import UserQuery
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django import forms
from orders.models import OrderItem
from django.db.models import Avg
# from django.db.models import F

# Create your views here.


def index(request):
    context = {
        'variants': Variant.objects.all().prefetch_related('product')
    }
    return render(request, 'index.html', context)


def shop(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    variants = Variant.objects.all().prefetch_related('product__category')

    # Get the filter values from request.GET
    ram_filter = request.GET.get('ram')
    rom_filter = request.GET.get('rom')
    category_filter = request.GET.get('category_id')
    # Get the sorting criteria from the request

    sort_by = request.GET.get('sort_by')
    # Apply filters if they are provided
    if ram_filter:
        variants = variants.filter(ram=ram_filter)
    if rom_filter:
        variants = variants.filter(internal_memory=rom_filter)
    if category_filter:
        variants = variants.filter(product__category__id=category_filter)

    # Apply sorting if a valid sorting criteria is provided
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
                request, f"No products  {ram_filter} RAM and {rom_filter} ROM")

    context = {
        'categories': categories,
        'variants': variants,
        'products': products,
        'ram': ram_filter,
        'rom': rom_filter,
        'category_id': category_filter,
        'sort_by': sort_by,  # Pass the sorting criteria to the template
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
    print("productid", product_id)
    selected_variant = None
    variant_id = request.GET.get('variant_id')
    print(variant_id)
    selected_variant = Variant.objects.filter(id=variant_id).first()
    # print("product id form varient ", selected_variant.product.id)

    if selected_variant:
        variant_form = VariantForm(instance=selected_variant)
        final_price = selected_variant.final_price
        quantity = selected_variant.quantity
    else:
        variant_form = VariantForm()
        final_price = product.price
        quantity = None
        messages.warning(request,
                         "Variant not found. Showing default product details.")
    reviews = ReviewRating.objects.filter(variant=selected_variant)
    average_rating = ReviewRating.objects.filter(
        variant=selected_variant).aggregate(Avg('rating'))['rating__avg']

    context = {
        'product': product,
        'categories': Category.objects.all(),
        'product_imgs': ProductImage.objects.filter(product=product),
        'variant_form': variant_form,
        'variant_id': variant_id,
        'final_price': final_price,
        'quantity': quantity,
        'reviews': reviews,
        'average_rating': average_rating,
    }

    return render(request, "main/product_details.html", context)


@login_required(login_url='login')
def add_review(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)

    # Check if the user has already submitted a review for this variant
    existing_review = ReviewRating.objects.filter(user=request.user, variant=variant).first()

    if existing_review:
        # If a review already exists, redirect to the edit review page
        return redirect('edit_review', review_id=existing_review.id)

    def purchase_product_checking(user, variant):
        return OrderItem.objects.filter(order__user=user, variant=variant).exists()

    if purchase_product_checking(request.user, variant):
        if request.method == 'POST':
            try:
                # Get review data from the request
                rating = int(request.POST.get('rating'))
                comment = request.POST.get('comment')
                review_text = request.POST.get('review')

                # Create a ReviewRating object
                review = ReviewRating.objects.create(
                    user=request.user,
                    variant=variant,
                    rating=rating,
                    comment=comment,
                    review=review_text
                )
                messages.success(request, 'Review added successfully.')
                # Redirect to the same product details page after review
                return redirect('my_reviews')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    else:
        messages.error(request, 'Purchase the product to make a review')
        return redirect('my_reviews')


@login_required(login_url='login')
def update_price(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = None
    if request.method == 'POST':
        selected_ram = request.POST.get('ram')
        selected_internal_memory = request.POST.get('internal_memory')

        if selected_ram and selected_internal_memory:
            variant = Variant.objects.filter(product=product, ram=selected_ram,
                                             internal_memory=selected_internal_memory).first()
            variant_id = variant.id

            if variant and variant.is_available:
                final_price = variant.final_price
                quantity = variant.quantity
            else:
                final_price = "Not Available"
        else:
            final_price = "Not Available"
        reviews = ReviewRating.objects.filter(variant=variant)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

        context = {
            'product': product,
            'categories': Category.objects.all(),
            'product_imgs': ProductImage.objects.filter(product=product),
            'variant_form': VariantForm(request.POST),
            'variant': variant,
            'final_price': final_price,
            'quantity': quantity,
            'review': reviews,
            'average_rating': average_rating,
            'variant_id': variant_id
        }

        return render(request, "main/product_details.html", context)

    return redirect('mainapp/product_details', product_id=product.id)


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
            messages.success(request, 'Your query has been received. We will respond shortly to your mail.')
            return redirect('chat_bot')
        else:
            messages.error(request, 'Query cannot be empty.')

    context = {
        'user': request.user
    }
    return render(request, 'main/chat_bot.html', context)
