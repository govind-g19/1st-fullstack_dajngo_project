from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from adminmanager.models import Product, Variant
from .models import Cart, CartItem
import uuid
from django.contrib import messages
from authapp.models import Address, Coupons, UserCoupons
from .forms import AddressForm, CouponForm
from django.utils import timezone
from django.db.models import Q
from django.db.models import Case, When, BooleanField
from django.db.models import Sum
# from django.urls import reverse


def generate_cart_id():
    return str(uuid.uuid4())


@login_required(login_url='login')
def add_to_cart(request, product_id):
    current_user = request.user
    product = get_object_or_404(Product, id=product_id)

    variant = Variant.objects.filter(
        product=product,
        ram=request.GET.get("ram"),
        internal_memory=request.GET.get("internal_memory"),
    ).first()

    if not product.available or (variant and not variant.is_available) or not product.category.is_available:
        messages.error(request, 'Out of stock')
        return redirect('shop')

    if variant and variant.is_available:
        cart, created = Cart.objects.get_or_create(user=current_user)
        cart_item, item_created = CartItem.objects.get_or_create(
            user=current_user,
            product=product,
            variant=variant,
            cart=cart,
            defaults={"added_quantity": 1},
        )

        # Calculate total number of unique items in the cart
        cart_items_count = CartItem.objects.filter(cart=cart).count()
        # Calculate the total quantity of all items in the cart
        total_cart_items = CartItem.objects.filter(cart=cart).aggregate(total_quantity=Sum('added_quantity'))['total_quantity']
        total_cart_items = total_cart_items or 0

        if cart_items_count >= 5 or total_cart_items >= 5:
            messages.error(request, "You can only add up to 5 items to your cart.")
            return redirect('cart')

        if not item_created:
            if cart_item.added_quantity + 1 > 5 or total_cart_items + 1 > 5:
                messages.error(request, 'You can only add up to 5 items of this product to your cart.')
                return redirect('cart')
            if cart_item.added_quantity < variant.quantity:
                cart_item.added_quantity += 1
                cart_item.save()
                messages.success(request, "Product added to cart")
                return redirect("cart")
            else:
                messages.warning(request, "Quantity exceeds available stock")
                return redirect("cart")
        else:
            messages.success(request, "Product added to cart")
            return redirect("cart")
    else:
        messages.error(request, "Selected variant is not available.")
        return redirect("product_details", product_id=product_id)


def product_category_availability(request, product_id):
    prodduct = get_object_or_404(Product, id=product_id)
    return True if prodduct.available and prodduct.category.is_available else False


@login_required(login_url='login')
def cart_view(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        total_discount = 0  # Total discount for all items
        cart_item_details = []  # List to hold details for each cart item
        if "applied_coupon_code" in request.session:
            # Retrieve the coupon code from the session
            applied_coupon_code = request.session["applied_coupon_code"]

            # Get the UserCoupons object with the applied coupon code
            user_coupon = UserCoupons.objects.get(
                coupon__coupon_code=applied_coupon_code,
                user=request.user
            )

            # Update the is_used status to False if it is currently True
            if user_coupon.is_used:
                user_coupon.is_used = False
                user_coupon.save()

            # Remove the coupon code from the session
            del request.session["applied_coupon_code"]

            # Remove the applied coupon discount from the session if it exists
            if "applied_coupon_discount" in request.session:
                del request.session["applied_coupon_discount"]

            messages.success(request, "Coupon is removed.")

        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=generate_cart_id()(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            if not product_category_availability(request, cart_item.variant.product.id):
                messages.error(request, f'The product "{cart_item.product.product_name}" is no longer available.')
                cart_item.delete()
                continue

            current_time = timezone.now()
            offer_price, combined_discount, product_offer, category_offer = offer_calculaton(cart_item.variant.id, current_time)

            
            item_total_price = offer_price * cart_item.added_quantity if offer_price else cart_item.variant.final_price * cart_item.added_quantity
            item_discount = (cart_item.variant.final_price - offer_price) * cart_item.added_quantity if offer_price else 0

            total += item_total_price
            total_discount += item_discount
            quantity += cart_item.added_quantity

            cart_item_details.append({
                'cart_item': cart_item,
                'offer_price': offer_price,
                'sub_total': item_total_price,
                'combined_discount': combined_discount,
            })

        tax = (18 * total) / 100
        grand_total = total + tax
    except Cart.DoesNotExist:
        pass
    except CartItem.DoesNotExist:
        pass

    context = {
        "total": total,
        "quantity": quantity,
        "cart_item_details": cart_item_details,
        "tax": tax,
        "grand_total": grand_total,
        'total_discount': total_discount
    }
    return render(request, "main/add_to_cart.html", context)


def offer_calculaton(variant_id, current_time):
    variant = get_object_or_404(Variant, id=variant_id)
    combined_discount = 0
    offer_price = 0
    product_offer = 0
    category_offer = 0
    final_price = variant.final_price

    if (final_price and
            variant.product.product_offer and
            variant.product.product_offer.active and
            variant.product.product_offer.valid_from <= current_time <= variant.product.product_offer.valid_to):
        product_offer = variant.product.product_offer.discount

    if (final_price and
            variant.product.category.category_offer and
            variant.product.category.category_offer.active and
            variant.product.category.category_offer.valid_from <= current_time <= variant.product.category.category_offer.valid_to):
        category_offer = variant.product.category.category_offer.discount

    combined_discount = product_offer + category_offer

    if combined_discount > 0:
        offer_price = final_price - (final_price * combined_discount / 100)
    else:
        offer_price = final_price

    return offer_price, combined_discount, product_offer, category_offer


@login_required(login_url='login')
def reduce_quantity(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)

        if cart_item.added_quantity > 1:
            cart_item.added_quantity -= 1
            cart_item.variant.quantity += 1
            cart_item.save()
            messages.success(request, "Quantity reduced successfully.")
        else:
            messages.warning(request, "Cannot reduce quantity below 1.")

        return redirect("cart")

    except CartItem.DoesNotExist:
        messages.error(request, "Cart item not found.")
        return redirect("cart")


@login_required(login_url='login')
def add_quantity(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart = cart_item.cart
        product_id = request.GET.get('product_id')

        if product_id:
            product = get_object_or_404(Product, id=product_id)

            # Check if the product is available
            if not product.available:
                messages.error(request, 'The selected product is out of stock.')
                return redirect("cart")
        # to chack the quantity
        total_cart_items = CartItem.objects.filter(cart=cart).aggregate(total_quantity=Sum('added_quantity'))['total_quantity']
        cart_items_count = CartItem.objects.filter(cart=cart).count()
        if cart_items_count > 5 or cart_item.added_quantity > 5 or total_cart_items >5:
            messages.error(request, "You can only add up to 6 items to your cart.")
            return redirect('cart')

        if cart_item.added_quantity < cart_item.variant.quantity:
            cart_item.added_quantity += 1
            cart_item.save()
            messages.success(request, "Quantity added successfully.")
        else:
            messages.warning(request, "Cannot add quantity out of stock.")

        return redirect("cart")

    except CartItem.DoesNotExist:
        messages.error(request, "Cart item not found.")
        return redirect("cart")


@login_required(login_url='login')
def remove_cart(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        # quantity_to_add_back = cart_item.added_quantity
        # variant = cart_item.variant
        # variant.quantity += quantity_to_add_back
        # variant.save()
        cart_item.delete()
        messages.success(request, "Product removed from cart.")
    except CartItem.DoesNotExist:
        messages.error(request, "Cart item not found.")
    return redirect("cart")


@login_required(login_url='login')
def check_out(request):
    total = 0
    quantity = 0
    tax = 0
    shipping = 0
    grand_total = 0
    cart_items = None
    coupon_discount=0
    discount_amount = 0
    total_discount = 0
    offer_price = 0

    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
            cart = Cart.objects.get(user=request.user)
        else:
            cart = Cart.objects.get(cart_id=generate_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            if not product_category_availability(request, cart_item.variant.product.id):
                messages.error(request, f'The product "{cart_item.variant.product.product_name}" is no longer available.')
                cart_item.delete()
                return redirect("cart")

            if not cart_item.variant.is_available:
                messages.error(request, f'The product "{cart_item.variant.product.product_name}" is out of stock.')
                return redirect("cart")

            if cart_item.added_quantity > cart_item.variant.quantity:
                messages.error(request, f'Product variant {cart_item.variant} is out of stock.')
                return redirect("cart")

            # Check for offers
            current_time = timezone.now()
            offer_price, combined_discount, product_offer, category_offer = offer_calculaton(cart_item.variant.id, current_time)
            print('combined_discount', cart_item.product, offer_price, combined_discount)

            cart_item.offer_price = offer_price
            cart_item.product_offer = product_offer
            cart_item.category_offer = category_offer

            if offer_price:
                print(offer_price)
                item_total_price = offer_price * cart_item.added_quantity
                item_discount = (cart_item.variant.final_price - offer_price) * cart_item.added_quantity
            else:
                item_total_price = cart_item.variant.final_price * cart_item.added_quantity
                item_discount = 0

            total += item_total_price
            total_discount += item_discount
            quantity += cart_item.added_quantity

        tax = (18 * total) / 100

        default_address = Address.objects.filter(user=request.user, is_primary=True).first()
        if default_address and default_address.state.lower() == "kerala":
            shipping = 0
        else:
            shipping = 500

        applied_coupon_code = request.session.get("applied_coupon_code")
        if applied_coupon_code:
            applied_coupons = UserCoupons.objects.filter(
                user=request.user, coupon__coupon_code=applied_coupon_code, is_used=True
            )
            coupon_discount = applied_coupons.aggregate(coupon_discount=Sum("coupon__discount"))["coupon_discount"] or 0

        discount = total - coupon_discount

        discount_amount = total_discount + coupon_discount

        grand_total = discount + tax + shipping

    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass

    current_datetime = timezone.now()
    address_list = Address.objects.filter(user=request.user)
    default_address = address_list.filter(is_primary=True).first()

    valid_coupons = Coupons.objects.filter(valid_from__lte=current_datetime,
                                           valid_to__gte=current_datetime
                                           )
    used_coupon = UserCoupons.objects.filter(user=request.user, is_used=True).values_list('coupon', flat=True)

    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "cart": cart,
        "tax": tax,
        "shipping": shipping,
        "grand_total": grand_total,
        "address_list": address_list,
        "default_address": default_address,
        "valid_coupons": valid_coupons,
        'used_coupon': used_coupon,
        'coupon_discount': coupon_discount,
        "discount_amount": discount_amount,
        "redirect_page": "check_out",
        'total_discount': total_discount
    }
    return render(request, "main/check_out.html", context)


@login_required(login_url='login')
def apply_coupon(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")

        # Check if a coupon is already applied
        if request.session.get("applied_coupon_code"):
            print(request.session.get("applied_coupon_code"))
            messages.error(request, "A coupon is already applied. Only one coupon can be used at a time.")
            return redirect("check_out")

        # Fetch the coupon or return 404 if not found
        coupon = get_object_or_404(Coupons, coupon_code=coupon_code)

        # Check if the coupon is valid
        if not coupon.is_valid():
            messages.error(request, "Coupon is not valid")
            return redirect("check_out")

        # Check if the coupon has already been used
        if UserCoupons.objects.filter(user=request.user, coupon=coupon, is_used=True).exists():
            messages.error(request, "Coupon has already been used")
            return redirect("check_out")

        # Check if the order total meets the minimum amount requirement
        cart_total = CartItem.objects.filter(user=request.user, is_active=True).aggregate(total=Sum('variant__final_price'))['total'] or 0
        if cart_total < coupon.minimum_amount:
            messages.error(request, "Minimum amount requirement not met")
            return redirect("check_out")

        # Check if the coupon is within the valid time range
        current_time = timezone.now()
        if not (coupon.valid_from <= current_time <= coupon.valid_to):
            messages.error(request, "Coupon is not within the valid time range")
            return redirect("check_out")

        # Apply the coupon
        user_coupon, created = UserCoupons.objects.get_or_create(user=request.user, coupon=coupon)
        user_coupon.is_used = True
        user_coupon.save()

        # Store the applied coupon code in the session
        request.session["applied_coupon_code"] = coupon_code
        request.session["applied_coupon_discount"] = coupon.discount
        messages.success(request, "Coupon applied successfully")

    return redirect("check_out")


def remove_coupon(request):
    if "applied_coupon_code" in request.session:
        try:
            applied_coupon_code = request.session["applied_coupon_code"]

            if applied_coupon_code:
                user_coupon = UserCoupons.objects.get(
                    user=request.user,
                    coupon__coupon_code=applied_coupon_code)
            if user_coupon:
                user_coupon.is_used = False
                user_coupon.save()
                del request.session["applied_coupon_code"]
                if "applied_coupon_discount" in request.session:
                    del request.session["applied_coupon_discount"]
                messages.error(request, ' The Coupon is removed ')
        except UserCoupons.DoesNotExist:
            messages.error(request, 'No Coupon Applied')
    return redirect('check_out')

@login_required(login_url='login')
def delete_cart(request, cart_id):
    try:
        # Retrieve the cart to delete
        cart = get_object_or_404(Cart, id=cart_id, user=request.user)

        # Check if the cart has an associated coupon that was used
        if "applied_coupon_code" in request.session:
            # Undo the usage of the coupon
            coupon_code = request.session.pop("applied_coupon_code")
            user_coupon = UserCoupons.objects.filter(
                user=request.user, coupon__coupon_code=coupon_code
            ).first()
            if user_coupon:
                user_coupon.is_used = False
                user_coupon.save()

        # Delete the cart
        cart.delete()
        messages.success(request, "cart deleted fell fre to use the coupon ")

        # Redirect back to the checkout page or any other appropriate page
        return redirect("shop")
    except Cart.DoesNotExist:
        # Redirect back to the checkout page with an error message
        messages.error(request,
                       "Cart does not exist or has already been deleted.")
        return redirect("check_out")


@login_required(login_url='login')
def add_address(request):
    if request.method == "POST":
        current_user = request.user
        first_name = request.POST.get("first_name")
        second_name = request.POST.get("second_name")
        house_address = request.POST.get("house_address")
        phone_number = request.POST.get("phone_number")
        city = request.POST.get("city")
        state = request.POST.get("state")
        land_mark = request.POST.get("land_mark")
        pin_code = request.POST.get("pin_code")

        # Basic validation
        if not first_name or len(first_name) < 3 or len(first_name) > 30:
            messages.warning(
                request, "First name must be between 3 and 30 characters long."
            )
            return redirect("add_address")

        if not first_name.isalnum():
            messages.warning(
                request, "First name can only contain letters and numbers."
            )
            return redirect("add_address")

        if not phone_number.isdigit() or len(phone_number) not in [10, 11]:
            messages.warning(request,
                             "Phone number must be 10 or 11 digits long.")
            return redirect("add_address")

        if not pin_code.isdigit() or len(pin_code) != 6:
            messages.warning(request, "Pin code must be 6 digits long.")
            return redirect("add_address")

        if not house_address or not city or not state or not pin_code:
            messages.warning(request, "Please fill in all required fields.")
            return redirect("add_address")

        try:
            address = Address(
                user=current_user,
                first_name=first_name,
                second_name=second_name,
                house_address=house_address,
                phone_number=phone_number,
                city=city,
                state=state,
                pin_code=pin_code,
                land_mark=land_mark,
            )
            address.save()

            if request.user.is_authenticated:
                Address.objects.filter(user=request.user, is_primary=True).update(
                    is_primary=False
                )
                address.is_primary = True
                address.save()

            source = request.POST.get("source")
            print(source)
            messages.success(request, "New address added successfully.")
            if source == "check_out":
                print("checkout")
                return redirect("check_out")
            else:
                print("manage")
                return redirect("view_profile")

        except Exception as e:
            messages.error(
                request, f"An error occurred while adding the address: {str(e)}"
            )
            return redirect("add_address")

    return render(request, "auth/add_address.html")


def page_direct(request):
    context = {"redirect_page": "check_out"}
    return render(request, "auth/add_address.html", context)


@login_required(login_url='login')
def default_address(request, address_id):
    Address.objects.filter(user=request.user).update(is_primary=False)
    address = Address.objects.get(id=address_id)
    address.is_primary = True
    address.save()
    return redirect("check_out")

@login_required(login_url='login')
def edit_address(request, address_id):
    address = get_object_or_404(Address, pk=address_id)

    if request.method == "POST":
        source = request.POST.get(
            "source", "manage_address"
        )  # Default to 'manage_address' if not provided
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            if source == "manage_address":
                return redirect("view_profile")
            else:
                return redirect("check_out")
    else:
        source = request.GET.get(
            "source", "manage_address"
        )  # Default to 'manage_address' if not provided
        form = AddressForm(instance=address)
    return render(request, "main/edit_address.html", {"form": form, "source": source})


@login_required(login_url='login')
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if address.is_primary:
        # Find another address to set as primary, excluding the current one
        secondary_address = (
            Address.objects.filter(user=request.user).exclude(id=address_id).first()
        )
        if secondary_address:
            secondary_address.is_primary = True
            secondary_address.save()
    address.delete()
    return redirect("manage_address")


# To add coupon
@login_required(login_url='login')
def view_coupons(request):
    coupons = Coupons.objects.all()
    user_coupons = UserCoupons.objects.filter(
        Q(usercoupons__is_used=False) | Q(usercoupons__isnull=True)
    )
    context = {"coupons": coupons, "user_coupons": user_coupons}
    return render(request, "main/check_out.html", context)


def add_coupon(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon added successfully!")
            return redirect("add_coupon")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm()
    return render(request, "auth/add_coupon.html", {"form": form})


@login_required(login_url='login')
def view_coupon_admin(request):
    coupons = Coupons.objects.all()
    return render(request, "auth/view_coupon_admin.html", {"coupons": coupons})


def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupons, pk=coupon_id)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon editeded successfully.")
            return redirect("view_coupon_admin")
    else:
        form = CouponForm(instance=coupon)

    return render(request, "auth/edit_coupon.html", {"form": form})


def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupons, id=coupon_id)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully.")
    return redirect("view_coupon_admin")
