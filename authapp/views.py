from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as vkart_loogout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models import Sum
import razorpay
from razorpay.errors import SignatureVerificationError
# active user
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
# from django.urls import NoReverseMatch, reverse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.encoding import DjangoUnicodeDecodeError
from .models import Address, Coupons, UserCoupons, Wallet, Transaction
from .models import WishList, Referral
from orders.models import Razorpay_payment
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
# for the copon
# from django.db.models import Case, When, BooleanField
from django.utils import timezone
from adminmanager.models import Product, Variant
from mainapp.models import Wallet_Razorpay_payment
from decimal import Decimal
from django.shortcuts import get_object_or_404
from razorpay.errors import SignatureVerificationError
# getting tokens
from .utils import generate_token
# sending mails
from django.core.mail import EmailMessage
# for class based view
from django.views.generic import View
# password generator
from django.contrib.auth.tokens import PasswordResetTokenGenerator
# threding to reduce time
import threading
import uuid
# for validation
import re
# cart
from cartapp.models import Cart, CartItem


class EmailThread(threading.Thread):
    def __init__(self, email_message):
        self.email_message = email_message
        threading.Thread.__init__(self)

    def run(self):
        self.email_message.send()


def signup(request):
    if request.method == "POST":
        # Retrieve form data from POST request
        uname = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        password = request.POST.get("pass1")
        confirm_password = request.POST.get("pass2")
        referral_code = request.POST.get("referral_code")

        # Ensure passwords match
        if password != confirm_password:
            messages.warning(request, "Passwords do not match.")
            return render(request, "auth/signup.html")

        # Password length check
        if len(password) < 8:
            messages.warning(request,
                             "Password must be at least 8 characters long.")
            return render(request, "auth/signup.html")

        # Password complexity check
        if not re.search(r'[A-Z]', password):
            messages.warning(request, '''Password must contain at least one
                              uppercase letter.''')
            return render(request, "auth/signup.html")

        if not re.search(r'[a-z]', password):
            messages.warning(request, '''Password must contain at least one
                              lowercase letter.''')
            return render(request, "auth/signup.html")

        if not re.search(r'[0-9]', password):
            messages.warning(request,
                             "Password must contain at least one digit.")
            return render(request, "auth/signup.html")

        if not re.search(r'[@$!%*?&]', password):
            messages.warning(request, '''Password must contain at least one
                              special character (@, $, !, %, *, ?, &).''')
            return render(request, "auth/signup.html")

        # Username validation
        if len(uname) < 3 or len(uname) > 30:
            messages.warning(request,
                             "Username must be between 3 and 30 characters.")
            return render(request, "auth/signup.html")

        if not uname.isalnum():
            messages.warning(request,
                             "Username can only contain letters and numbers.")
            return render(request, "auth/signup.html")

        if not first_name.isalpha():
            messages.warning(request, "First name can only contain letters.")
            return render(request, "auth/signup.html")

        if not last_name.isalpha():
            messages.warning(request, "Last name can only contain letters.")
            return render(request, "auth/signup.html")

        # Check if username or email already exists in the database
        if User.objects.filter(username=uname).exists():
            messages.warning(request, "Username is taken.")
            return render(request, "auth/signup.html")

        if User.objects.filter(email=email).exists():
            messages.warning(request, "Email is already registered.")
            return render(request, "auth/signup.html")

        # Referral verification
        referred_by = None
        if referral_code:
            try:
                # Validate if the referral_code is a valid UUID
                uuid.UUID(referral_code)
                referral = Referral.objects.get(referral_code=referral_code)
                referred_by = referral.user

                if not referred_by.is_active:
                    messages.error(request, 'Invalid Referral Code.')
                    return render(request, "auth/signup.html")

                if uname == referred_by.username:
                    messages.error(request, 'Self Referral is not allowed.')
                    return render(request, "auth/signup.html")

            except (ValueError, Referral.DoesNotExist):
                messages.error(request, '''Invalid referral code format or
                                referral code does not exist.''')
                return render(request, "auth/signup.html")

        # Create a new User object
        user = User.objects.create_user(
            username=uname,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )

        # Save the user to the database
        user.is_active = False
        user.save()

        # Process referral rewards after user creation
        if referral_code and referred_by:
            # Reward referred_by with $100
            referred_by_wallet, created = Wallet.objects.get_or_create(
                user=referred_by)
            referred_by_wallet.balance += 100
            referred_by_wallet.save()
            Transaction.objects.create(wallet=referred_by_wallet,
                                       transaction_type='credit',
                                       amount=100)

            # Reward user with $50
            user_wallet, created = Wallet.objects.get_or_create(user=user)
            user_wallet.balance += 50
            user_wallet.save()
            Transaction.objects.create(wallet=user_wallet,
                                       transaction_type='credit',
                                       amount=50)

            # Create Referral entry
            Referral.objects.create(user=user, referred_by=referred_by)
        else:
            Referral.objects.create(user=user, referred_by=None)

        current_site = get_current_site(request)
        email_subject = "Activate Your Account"
        message = render_to_string(
            "auth/activate.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": generate_token.make_token(user),
            },
        )
        email_message = EmailMessage(
            email_subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
        )
        email_message.send()

        messages.info(request, "For activation, click the link in your email.")
        return redirect("/auth/login")

    return render(request, "auth/signup.html")


class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            user = None
        if user is not None and generate_token.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Activation completed")
            return redirect("/auth/login")
        return render(request, "auth/activatefail.html")


# to change password


class RequestRestEmailView(View):
    def get(self, request):
        return render(request, "auth/request-reset-email.html")

    def post(self, request):
        email = request.POST["email"]
        user = User.objects.filter(email=email)

        if user.exists():
            get_current_site(request)
            email_subject = "Rest our Password"
            message = render_to_string(
                "auth/reset-user-password.html",
                {
                    "domain": "127.0.0.1:8000",
                    "uid": urlsafe_base64_encode(force_bytes(user[0].pk)),
                    "token": PasswordResetTokenGenerator().make_token(user[0]),
                },
            )

            email_message = EmailMessage(
                email_subject, message, settings.EMAIL_HOST_USER, [email]
            )
            EmailThread(email_message).start()
            messages.info(request, "Please check your mail")
            return render(request, "auth/request-reset-email.html")


class SetNewPasswordView(View):
    def get(self, request, uidb64, token):
        context = {"uidb64": uidb64, "token": token}
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.warning(
                    request, "Invalid link, Please try again after sometime "
                )
                return render(request, "auth/request-reset-email.html")
        except DjangoUnicodeDecodeError:
            pass
        return render(request, "auth/set-new-password.html", context)

    def post(self, request, uidb64, token):
        context = {
            "uidb64": uidb64,
            "token": token,
        }
        password = request.POST.get("pass1")
        confirm_password = request.POST.get("pass2")

        # Ensure passwords match
        if password != confirm_password:
            messages.warning(request, "Passwords do not match.")
            return render(request, "auth/set-new-password.html", context)

        # Password length check
        if len(password) < 8:
            messages.warning(request,
                             "Password must be at least 8 characters long.")
            return render(request, "auth/set-new-password.html", context)

        # Password complexity check
        if not re.search(r'[A-Z]', password):
            messages.warning(request,
                             "Password must contain at least one uppercase.")
            return render(request, "auth/set-new-password.html", context)

        if not re.search(r'[a-z]', password):
            messages.warning(request,
                             "Password must contain at least one lowercase")
            return render(request, "auth/set-new-password.html", context)

        if not re.search(r'[0-9]', password):
            messages.warning(request,
                             "Password must contain at least one digit.")
            return render(request, "auth/set-new-password.html", context)

        if not re.search(r'[@$!%*?&]', password):
            messages.warning(request,
                             '''Password must contain at least one special
                               character (@, $, !, %, *, ?, &).''')
            return render(request, "auth/set-new-password.html", context)
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()
            messages.success(request, "password successfull changed")
            return redirect("/auth/login")
        except DjangoUnicodeDecodeError:
            messages.warning(request, "somtimg went wrong")
            return render(request, "auth/set-new-password.html", context)


def OtpVerification(request):
    return render(request, "auth/otpverification.html")


def loogin(request):
    if request.method == "POST":
        uname = request.POST.get("username")
        password = request.POST.get("pass1")
        user = authenticate(username=uname, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Log in success")
            request.session["is_authenticated"] = True

            '''  Redirect to the product details page or a
            default URL if 'next' not present'''
            next_param = request.GET.get("next")

            if next_param:
                return redirect(next_param)
            else:
                return redirect("/mainapp/index")

        else:
            messages.warning(request, "Incorrect User Information")
            return redirect("/auth/login")

    return render(request, "auth/login.html")


def loogout(request):
    vkart_loogout(request)
    messages.success(request, "Log in to enjoy more")
    return redirect("/auth/login")


@login_required(login_url='login')
# user profile
def view_profile(request):
    current_user = request.user
    try:
        referral = Referral.objects.get(user=current_user)
    except Referral.DoesNotExist:
        referral = None
    addresses = Address.objects.filter(user=current_user,
                                       is_primary=True).first()
    address_list = Address.objects.filter(user=current_user)
    coupons = Coupons.objects.all()

    # Check if each coupon is used by the current user
    coupon_status = []
    for coupon in coupons:
        used = UserCoupons.objects.filter(coupon=coupon, is_used=True).exists()
        coupon_status.append((coupon, used))

    context = {
        'current_user': current_user,
        'addresses': addresses,
        'address_list': address_list,
        'coupon_status': coupon_status,
        'referral': referral,
    }
    return render(request, 'auth/view_profile.html', context)


@login_required(login_url='login')
def edit_profile(request):
    current_user = request.user
    address = Address.objects.filter(user=current_user,
                                     is_primary=True).first()

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        second_name = request.POST.get("second_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone_number = request.POST.get("phone_number")

        # Validate first name and second name fields
        if not re.match("^[a-zA-Z]+$", first_name):
            messages.error(request, "First name should contain only letters.")
            return redirect("edit_profile")

        if not re.match("^[a-zA-Z]+$", second_name):
            messages.error(request, "Second name should contain only letters.")
            return redirect("edit_profile")

        # Validate username field
        if not re.match("^[a-zA-Z0-9_]+$", username):
            messages.error(request, '''Username should contain only letters,
                           numbers, or underscores.''')
            return redirect("edit_profile")

        # Check if username is already taken
        if User.objects.filter(username=username).exclude(
                id=current_user.id).exists():
            messages.error(request, "Username already taken")
            return redirect('edit_profile')

        # Check if email is already in use
        if User.objects.filter(
                email=email).exclude(id=current_user.id).exists():
            messages.error(request, 'This email is already in use')
            return redirect('edit_profile')

        # Check if phone number is already in use
        if phone_number:
            if not re.match("^\d{10}$", phone_number):
                messages.error(request,
                               "Please enter a valid 10-digit phone number.")
                return redirect("edit_profile")

            if Address.objects.filter(~Q(user=current_user),
                                      phone_number=phone_number).exists():
                messages.error(request, "Phone number already in use")
                return redirect("edit_profile")
        else:
            messages.error(request, "Enter a valid Number")
            return redirect("edit_profile")

        # Update user's username and email
        current_user.username = username
        current_user.email = email
        current_user.save()

        # Update user's address if it exists
        if address:
            address.phone_number = phone_number
            address.first_name = first_name
            address.second_name = second_name
            address.save()
        else:
            messages.error(request, 'To complete the Profile fill the address')
            return redirect('manage_address')

        messages.success(request, "Profile updated successfully.")
        return redirect('view_profile')

    context = {
        'address': address,
        'current_user': current_user
    }

    return render(request, 'auth/edit_profile.html', context)


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confrom_new_password = request.POST.get('confrom_password')
        user = authenticate(username=request.user.username, password=password)

        if len(password) < 8:
            messages.warning(request,
                             "Password must be at least 8 characters long.")
            return render(request, "auth/change_password.html")
        # Password complexity check
        if not re.search(r'[A-Z]', password):
            messages.warning(request, '''Password must contain at
                             least one uppercase letter.''')
            return render(request, "auth/change_password.html")

        if not re.search(r'[a-z]', password):
            messages.warning(request, '''Password must contain at
                             least one lowercase letter.''')
            return render(request, "auth/change_password.html")

        if not re.search(r'[0-9]', password):
            messages.warning(request,
                             "Password must contain at least one digit.")
            return render(request, "auth/change_password.html")

        if not re.search(r'[@$!%*?&]', password):
            messages.warning(request, '''Password must contain at least one
                              special character (@, $, !, %, *, ?, &).''')
            return render(request, "auth/change_password.html")

        if user is not None:
            if new_password == confrom_new_password:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('login')
            else:
                messages.error(request, 'new password does not match')
                return redirect(request, 'change_password')
        else:
            messages.error(request, "old password does not match")
            return redirect(request, 'change_password')
    return render(request, 'auth/change_password.html')


# View coupon
@login_required(login_url='login')
def user_view_coupons(request):
    current_datetime = timezone.now()

    # Fetch all valid coupons
    valid_coupons = Coupons.objects.filter(
        valid_from__lte=current_datetime, valid_to__gte=current_datetime)

    # Fetch used coupons for the current user
    used_coupons = UserCoupons.objects.filter(
        user=request.user, is_used=True).values_list('coupon', flat=True)

    context = {
        'valid_coupons': valid_coupons,
        'used_coupons': used_coupons,
    }

    return render(request, 'auth/user_view_coupons.html', context)


# Address
@login_required(login_url='login')
def manage_address(request):
    current_user = request.user
    main_addresses = Address.objects.filter(user=current_user,
                                            is_primary=True).first()
    addresses = Address.objects.filter(user=current_user)
    context = {
        'addresses': addresses,
        'redirect_page': 'manage_address',
        'main_addresses': main_addresses
    }
    return render(request, 'auth/manage_address.html', context)


@login_required(login_url='login')
def my_wallet(request):
    if request.method == "POST":
        if 'add' in request.POST:
            return add_to_wallet(request)
        elif 'withdraw' in request.POST:
            return withdraw_funds(request)
    # Retrieve the wallet and transactions to display on the page
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=request.user, balance=0)

    transactions = Transaction.objects.filter(
        wallet=wallet).order_by('-timestamp')

    context = {
        'my_wallet': wallet,
        'transactions': transactions
    }
    return render(request, 'auth/my_wallet.html', context)


@login_required(login_url='login')
def add_to_wallet(request):
    if request.method == "POST":
        try:
            amount = request.POST.get('amount')
            if not amount:
                messages.error(request, 'Amount not specified')
                return redirect('my_wallet')
            if Decimal(amount) <= 0:
                messages.error(request, 'Amount should be greater than zero')
                return redirect('my_wallet')

            # Using get_or_create to fetch or create a wallet for the user
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += Decimal(amount)
            wallet.save()

            # Creating a transaction
            Transaction.objects.create(wallet=wallet,
                                       transaction_type='credit',
                                       amount=Decimal(amount))
            messages.success(request, 'Amount added successfully')
            return redirect('my_wallet')

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('my_wallet')

    return redirect('my_wallet')


@login_required(login_url='login')
def add_to_wallet_view(request):
    user = request.user
    currency = 'INR'
    context = {
        'user': user,
        'currency': currency
    }
    return render(request, 'auth/add_to_wallet_form.html', context)


@login_required(login_url='login')
def add_to_wallet_razorpay(request):
    if request.method == "POST":
        razorpay_client = razorpay.Client(auth=(settings.KEY, settings.SECRET))
        user = request.user
        currency = 'INR'
        amount = request.POST.get('amount')

        if not amount:
            messages.error(request, 'Enter a valid amount')
            return redirect('my_wallet')

        try:
            amount = Decimal(amount)
            print("type of amount", type(amount))
        except ValueError:
            messages.error(request, 'Enter a valid amount')
            return redirect('my_wallet')

        if amount <= 0 or amount > 10000:
            messages.error(request,
                           'Amount should be greater than 0 and less than 10000 ')
            return redirect('my_wallet')

        razorpay_amount = float(amount) * 100
        razorpay_order = razorpay_client.order.create(dict(
            amount=razorpay_amount,
            currency=currency,
            payment_capture='0'
        ))

        razorpay_order_id = razorpay_order['id']
        callback_url = request.build_absolute_uri(reverse('wallet_paymenthandler'))
        print(callback_url)

        if razorpay_order_id:
            Wallet_Razorpay_payment.objects.create(
                razorpay_payment_id=razorpay_order_id,
                amount=razorpay_amount / 100,
                user=user
            )
        else:
            messages.error(request, 'Failed to create Razorpay order')
            return redirect('my_wallet')

        context = {
            'razorpay_merchant_key': settings.KEY,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_amount': razorpay_amount,
            'callback_url': callback_url,
            'currency': currency,
            'amount': amount,
            'user': user
        }
        return render(request, 'auth/add_to_wallet_razorpay.html', context)

    return redirect('add_to_wallet_view')


@csrf_exempt
def wallet_paymenthandler(request):
    if request.method == "POST":
        try:
            razorpay_client = razorpay.Client(auth=(settings.KEY, settings.SECRET))
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')

            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            razorpay_client.utility.verify_payment_signature(params_dict)

            try:
                razorpay_payment = Wallet_Razorpay_payment.objects.get(razorpay_payment_id=razorpay_order_id)
            except Wallet_Razorpay_payment.DoesNotExist:
                messages.error(request, f"Razorpay payment with ID {payment_id} does not exist.")
                return redirect('my_wallet')

            amount = razorpay_payment.amount
            user = razorpay_payment.user
            if user.is_authenticated:
                wallet, created = Wallet.objects.get_or_create(user=user)
                wallet.balance += Decimal(amount)
                wallet.save()

                Transaction.objects.create(wallet=wallet, transaction_type='credit', amount=Decimal(amount))
                messages.success(request, 'Amount added successfully')
                return redirect('my_wallet')

        except SignatureVerificationError as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('my_wallet')

    else:
        messages.error(request, "Only POST requests are allowed")
        return redirect('my_wallet')


@login_required(login_url='login')
def withdraw_funds(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        if not amount:
            messages.error(request, 'No valid amount')
            return redirect('my_wallet')
        if Decimal(amount) <= 0:
            messages.error(request, 'Enter a valid amount')
            return redirect('my_wallet')
        try:
            wallet = Wallet.objects.get(user=request.user)
            if Decimal(amount) <= wallet.balance:
                wallet.balance -= Decimal(amount)
                wallet.save()
                # Creating a transaction for withdrawal
                Transaction.objects.create(wallet=wallet,
                                           transaction_type='debit',
                                           amount=Decimal(amount))
                messages.success(request, 'Amount withdrawn successfully')
                return redirect('my_wallet')
            else:
                messages.warning(request, 'Insufficient funds in the wallet')
                return redirect('my_wallet')
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet not found')
            return redirect('my_wallet')
    return redirect('my_wallet')


# wishlist
@login_required(login_url='login')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.GET.get('variant_id')
    if variant_id:
        try:
            variant_id = int(variant_id)
            variant = get_object_or_404(Variant, id=variant_id)
            wishlist_item, created = WishList.objects.get_or_create(
                user=request.user, product=product, variant=variant)
            if created:
                messages.success(request, 'Product added to wishlist.')
            else:
                messages.info(request, 'Product already in wishlist.')
        except ValueError:
            messages.error(request, 'Invalid variant ID.')
    else:
        messages.error(request, 'Variant ID not provided.')
    return redirect('view_wishlist')


@login_required(login_url='login')
def view_wishlist(request):
    wishlist_items = WishList.objects.filter(user=request.user)
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'auth/view_wishlist.html', context)


@login_required(login_url='login')
def add_to_cart_from_wishlist(request, wishlist_item_id):
    current_user = request.user
    wishlist_item = get_object_or_404(WishList,
                                      id=wishlist_item_id,
                                      user=current_user)
    product = wishlist_item.product
    variant = wishlist_item.variant

    if variant.is_available and product.available and variant.quantity > 0:
        cart, created = Cart.objects.get_or_create(user=current_user)
        cart_items_count = CartItem.objects.filter(cart=cart).count()
        total_cart_items = CartItem.objects.filter(cart=cart).aggregate(
            total_quantity=Sum('added_quantity'))['total_quantity']
        total_cart_items = total_cart_items or 0

        if cart_items_count >= 5 or total_cart_items >= 5:
            messages.error(request,
                           "You can only add up to 5 items to your cart.")
            return redirect('cart')

        cart_item, item_created = CartItem.objects.get_or_create(
            user=current_user,
            product=product,
            variant=variant,
            cart=cart,
            defaults={"added_quantity": 1},
        )

        if not item_created:
            if cart_item.added_quantity < variant.quantity:
                if (cart_item.added_quantity + 1 > 5 or
                   total_cart_items + 1 > 5):
                    messages.error(request,
                                   "You can only add up to 5 items to cart.")
                    return redirect('cart')
                cart_item.added_quantity += 1
                cart_item.save()
                # Remove the item from the wishlist after adding to the cart
                wishlist_item.delete()
                messages.success(request,
                                 '''Product added to cart and removed from
                                 wishlist''')
                return redirect("cart")
            else:
                messages.warning(request,
                                 "Quantity exceeds available stock")
                return redirect("wishlist")
        else:
            # Remove the item from the wishlist after adding to the cart
            wishlist_item.delete()
            messages.success(request,
                             "Product added to cart and removed from wishlist")
            return redirect("cart")
    else:
        if not variant.is_available or variant.quantity <= 0:
            messages.error(request, "Selected variant is not available.")
        if not product.available:
            messages.error(request, "Product is not available.")
        return redirect("wishlist")


@login_required(login_url='login')
def add_all_to_cart(request):
    current_user = request.user
    wishlist_items = WishList.objects.filter(user=current_user)

    if wishlist_items:
        cart, created = Cart.objects.get_or_create(user=current_user)
        cart_items_count = CartItem.objects.filter(cart=cart).count()
        total_cart_items = CartItem.objects.filter(
            cart=cart).aggregate(total_quantity=Sum(
                'added_quantity'))['total_quantity']
        total_cart_items = total_cart_items or 0

        for wishlist_item in wishlist_items:
            if cart_items_count >= 5 or total_cart_items >= 5:
                messages.error(request,
                               "You can only add up to 5 items to your cart.")
                break

            product = wishlist_item.product
            variant = wishlist_item.variant

            if (variant and variant.is_available and
               product.available and variant.quantity > 0):
                cart_item, item_created = CartItem.objects.get_or_create(
                    user=current_user,
                    product=product,
                    variant=variant,
                    cart=cart,
                    defaults={"added_quantity": 1},
                )
                messages.success(request, "All available items added to cart")

                if not item_created:
                    if cart_item.added_quantity < variant.quantity:
                        if (cart_item.added_quantity + 1 > 5 or
                           total_cart_items + 1 > 5):
                            messages.error(request,
                                           "Add only up to 5 items to cart.")
                            break
                        cart_item.added_quantity += 1
                        cart_item.save()
                        messages.success(request,
                                         "All available items added to cart")
                    else:
                        messages.warning(request,
                                         f'''Quantity for
                                         {product.product_name} exceeds
                                         available stock''')
                        continue

                cart_items_count = CartItem.objects.filter(cart=cart).count()
                total_cart_items = CartItem.objects.filter(
                    cart=cart).aggregate(total_quantity=Sum(
                        'added_quantity'))['total_quantity']
                total_cart_items = total_cart_items or 0

                wishlist_item.delete()
    else:
        messages.warning(request, "No items in your wishlist")

    return redirect("cart")


def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.GET.get('variant_id')
    variant = get_object_or_404(Variant, id=variant_id)

    wishlist_item = get_object_or_404(WishList, user=request.user,
                                      product=product,
                                      variant=variant)

    wishlist_item.delete()
    messages.success(request, "Item removed from wishlist.")

    return redirect('view_wishlist')
