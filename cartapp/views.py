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


@login_required
def add_to_cart(request, product_id):
    current_user = request.user
    product = Product.objects.get(id=product_id)

    if current_user.is_authenticated:
        variant = Variant.objects.filter(
            product=product,
            ram=request.GET.get("ram"),
            internal_memory=request.GET.get("internal_memory"),
        ).first()

        # to check the Availability
        if not product.available or (variant and not variant.is_available):
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

            if not item_created:
                if cart_item.added_quantity < variant.quantity:
                    cart_item.added_quantity += 1
                    cart_item.save()
                    messages.success(request, "Product Added to Cart")
                    return redirect("cart")
                else:
                    messages.warning(request, "quantity exceeds,not available")
                    return redirect("cart")
            else:
                messages.success(request, "Product Added to Cart")
                return redirect("cart")
        else:
            messages.error(request, "Selected variant is not available.")
            return redirect("product_details")
    else:
        cart, created = Cart.objects.get_or_create(
            cart_id=generate_cart_id()(request))
        variant = Variant.objects.filter(
            product=product,
            ram=request.GET.get("ram"),
            internal_memory=request.GET.get("internal_memory"),
        ).first()
        if variant and variant.is_available:
            cart_item, item_created = CartItem.objects.get_or_create(
                product=product,
                variant=variant,
                cart=cart,
                defaults={"added_quantity": 1},
            )

            if not item_created:
                if cart_item.added_quantity < variant.quantity:
                    cart_item.added_quantity += 1
                    variant.quantity -= 1
                    cart_item.save()
                    messages.success(request, "Product Added to Cart")
                    return redirect("cart")
                else:
                    messages.warning(request, "this quantity is not available")
            else:
                messages.success(request, "Product Added to Cart")
                return redirect("product_details")
        else:
            messages.error(request, "Selected variant is not available.")
            return redirect("product_details")


@login_required
def cart_view(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        shipping = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user,
                                                 is_active=True)
        else:
            cart = Cart.objects.get(cart_id=generate_cart_id()(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += cart_item.variant.final_price * cart_item.added_quantity
            quantity += cart_item.added_quantity
        tax = (18 * total) / 100
        shipping = 0
        grand_total = total + tax + shipping
    except Cart.DoesNotExist:
        pass
    except CartItem.DoesNotExist:
        pass
    context = {
        "total": total,
        "quantity": quantity,
        "cart_items": cart_items,
        "tax": tax,
        "shipping": shipping,
        "grand_total": grand_total,
    }
    return render(request, "main/add_to_cart.html", context)


@login_required
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


def add_quantity(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        product_id = request.GET.get('product_id')

        if product_id:
            product = get_object_or_404(Product, id=product_id)

            # Check if the product is available
            if not product.available:
                messages.error(request, 'The selected product is out of stock.')
                return redirect("cart")

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


@login_required
def check_out(request):
    total = 0
    quantity = 0
    tax = 0
    shipping = 0
    grand_total = 0
    cart_items = None
    discount_amount = 0

    # Retrieve the applied coupon code from the session
    applied_coupon_code = request.session.get("applied_coupon_code")

    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user,
                                                 is_active=True)
            cart = Cart.objects.get(user=request.user)
        else:
            cart = Cart.objects.get(cart_id=generate_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:

            if not cart_item.product.available or not cart_item.variant.is_available:
                messages.error(request, f'The product "{cart_item.product.product_name}" is out of stock.')
                return redirect("cart")
            if cart_item.added_quantity > cart_item.variant.quantity:
                messages.error(
                    request, f'''Product variant
                    {cart_item.variant} is out of stock.'''
                )
                return redirect("cart")

            total += cart_item.variant.final_price * cart_item.added_quantity
            quantity += cart_item.added_quantity

        tax = (18 * total) / 100

        default_address = Address.objects.filter(
            user=request.user, is_primary=True
        ).first()
        if default_address:

            if default_address.state.lower() == "kerala":
                shipping = 0
            else:
                shipping = 500
        else:
            return redirect("page_direct")

        # Calculate discounted total after applying coupons
        if applied_coupon_code:
            applied_coupons = UserCoupons.objects.filter(
                user=request.user, coupon__coupon_code=applied_coupon_code,
                is_used=True
            )
            discount_amount = (
                applied_coupons.aggregate(
                    discount_amount=Sum("coupon__discount"))[
                    "discount_amount"
                ]
                or 0
            )

        discount = total - discount_amount

        grand_total = discount + tax + shipping
        if "applied_coupon_code" in request.session:
            del request.session["applied_coupon_code"]

    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass

    current_datetime = timezone.now()
    address_list = Address.objects.filter(user=request.user)
    default_address = address_list.filter(is_primary=True).first()

    # Fetch all valid coupons
    valid_coupons = Coupons.objects.filter(
        valid_from__lte=current_datetime, valid_to__gte=current_datetime
    )

    # Annotate valid coupons with the is_used status for the current user
    valid_coupons = valid_coupons.annotate(
        is_used=Case(
            When(usercoupons__user=request.user, usercoupons__is_used=True,
                 then=True),
            default=False,
            output_field=BooleanField(),
        )
    )

    # Clear the applied coupon code from the session if present

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
        "discount_amount": discount_amount,
        "redirect_page": "check_out",
    }
    return render(request, "main/check_out.html", context)

@login_required
def apply_coupon(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")
        cartitem = CartItem.objects.filter(user=request.user, is_active=True).first()
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
        if cartitem.variant.final_price < coupon.minimum_amount:
            messages.error(request, "Minimum amount requirement not met")
            return redirect("check_out")

        # Check if the user has already used this coupon
        user_coupon, created = UserCoupons.objects.get_or_create(user=request.user, coupon=coupon)
        if user_coupon.is_used:
            messages.error(request, "Coupon has already been used")
            return redirect("check_out")

        # Mark the coupon as used
        user_coupon.is_used = True
        user_coupon.save()

        # Store the applied coupon code in the session
        request.session["applied_coupon_code"] = coupon_code
        messages.success(request, "Coupon applied successfully")

    return redirect("check_out")


@login_required
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


@login_required
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


@login_required
def default_address(request, address_id):
    Address.objects.filter(user=request.user).update(is_primary=False)
    address = Address.objects.get(id=address_id)
    address.is_primary = True
    address.save()
    return redirect("check_out")


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


@login_required
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
@login_required
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


@login_required
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
