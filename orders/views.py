from django.shortcuts import render, redirect, get_object_or_404
from .models import Orders, OrderItem, Payment, Razorpay_payment
from authapp.models import Wallet, Transaction
from django.utils import timezone
from authapp.models import Address
from cartapp.models import CartItem, Cart
from adminmanager.models import Variant
import razorpay
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.


@login_required
def myorders(request):
    # Fetch orders for the logged-in user
    orders = Orders.objects.filter(user=request.user)

    # Fetch order items related to the fetched orders
    order_items = OrderItem.objects.filter(order__in=orders)

    # Fetch payments related to the fetched orders
    payments = Payment.objects.filter(order__in=orders)

    context = {
        'orders': orders,
        'order_items': order_items,
        'payments': payments,
    }

    return render(request, 'order/myorders.html', context)


@login_required
def delete_my_order(request, orderid):
    order = Orders.objects.get(id=orderid)
    return redirect("myorders", id=order)


@login_required
def place_order(request):
    default_address = Address.objects.filter(is_primary=True).first()
    order = None

    if request.method == "POST":
        user = request.user
        try:
            subtotal = request.POST.get('Subtotal')
            discount_given = request.POST.get('discount_given')
            shipping = request.POST.get('shipping')
            tax = request.POST.get('tax')
            grand_total = request.POST.get('grand_total')
            address = default_address
            status = 'OrderPending'
            order_date = timezone.now()
            payment_method = request.POST.get("payment_method")
            cart_id = request.POST.get('cart_id')
        except (TypeError, ValueError):
            messages.error(request, 'Invalid monetary value provided.')
            return redirect('check_out')

        try:
            cart = Cart.objects.get(id=cart_id, user=user)
            cart_items = CartItem.objects.filter(cart=cart)

            for cart_item in cart_items:
                variant = cart_item.variant
                if variant.quantity < cart_item.added_quantity:
                    messages.error(request, f'''{variant.product.name}
                                   variant is out of stock.''')
                    return redirect('shop')

            # Create the order object
            order_id = uuid.uuid4().hex[:8].upper()
            order = Orders.objects.create(
                user=user,
                order_id=order_id,
                delivery_address=address,
                order_total=subtotal,
                discount_given=discount_given,
                shipping=shipping,
                tax=tax,
                grand_total=grand_total,
                status=status,
                order_date=order_date,
                payment_method=payment_method
            )
            order.save()

            # Perform actions for all payment methods
            order = Orders.objects.filter(user=request.user).last()
            for cart_item in cart_items:
                variant_id = cart_item.variant.id
                variant = Variant.objects.get(id=variant_id)
                if variant.quantity > cart_item.added_quantity:
                    variant.quantity -= cart_item.added_quantity
                    variant.save()
                else:
                    messages.error(request, f'''{variant.product.name}
                                   variant is out of stock.''')

                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    quantity=cart_item.added_quantity,
                    ram=cart_item.variant.ram,
                    memmory=cart_item.variant.internal_memory,
                    price=cart_item.variant.final_price
                )

            print(order)
            cart = get_object_or_404(Cart, id=cart_id, user=request.user)
            cart.delete()
        except Cart.DoesNotExist:
            messages.error(request, 'Cart not found.')
            return redirect('shop')
        payment = Payment.objects.create(user=request.user,
                                         payment_method=payment_method,
                                         status='NOT PAID',
                                         amount_paid=order.grand_total,
                                         order=order)
        payment.save()
    return redirect("order_page", orderid=order.id)


@login_required
def order_page(request, orderid):
    order = Orders.objects.get(id=orderid)
    orderitems = OrderItem.objects.filter(order=order)
    sub_total = sum(item.price * item.quantity for item in orderitems)
    if order.payment_method == "COD" and order.status == "OrderPending":
        return redirect("payment_cod", orderid=order.id)
    elif order.payment_method == "Razorpay" and order.status == "OrderPending":
        # Check if the payment status is pending
        return redirect("payment_razorpay", orderid=order.id)
    elif order.payment_method == 'wallet' and order.status == "OrderPending":
        return redirect("payment_wallet", orderid=order.id)

    payment = Payment.objects.filter(order=order).first()

    context = {
        'order': order,
        'orderitems': orderitems,
        'sub_total': sub_total,
        'payment': payment
    }
    return render(request, "order/place_order.html", context)


@login_required
def payment_cod(request, orderid):
    try:
        print("hi i am govind")
        order = Orders.objects.get(id=orderid)
        try:
            payment = Payment.objects.get(order=order)
            # Update the existing payment instance
            payment.payment_method = "COD"
            payment.amount_paid = 0
            payment.status = "Pending"
            payment.payment_id = None
            payment.save()
        except Payment.DoesNotExist:
            # Create a new payment instance if none exists
            Payment.objects.create(
                user=request.user,
                order=order,
                payment_method="COD",
                amount_paid=0,
                status="Pending",
                payment_id=None
            )
        # Update order status
        order.status = "Packed"
        order.save()

    except Orders.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('shop')

    return redirect('order_page', orderid=order.id)


@login_required
def payment_wallet(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid)
        wallet = get_object_or_404(Wallet, user=request.user)

        if order.status != 'Cancelled' or order.status != 'Returned':
            if wallet.balance >= Decimal(order.grand_total):
                wallet.balance -= Decimal(order.grand_total)
                wallet.save()

                transacton = Transaction.objects.create(
                    wallet=wallet,
                    amount=Decimal(order.grand_total),
                    transaction_type='debit'
                )

                payments, created = Payment.objects.get_or_create(order=order)

                payments.payment_method = "wallet"
                payments.amount_paid = str(Decimal(order.grand_total))
                payments.status = "Success"
                payments.payment_id = transacton.id
                payments.save()

                order.status = "Packed"
                order.save()

                messages.success(request, 'Payment successful and order status updated to Packed.')
            else:
                messages.error(request, 'Insufficient funds in wallet.')
                return redirect('order_failer', orderid=order.id)
        else:
            messages.error(request, 'Order was cancelled')
            return redirect('shop')

    except Wallet.DoesNotExist:
        messages.error(request, 'Wallet not found.')
        return redirect('order_failer', orderid=order.id)
    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('order_failer', orderid=order.id)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('order_failer', orderid=order.id)

    return redirect('order_page', orderid=order.id)


@login_required
def payment_razorpay(request, orderid):
    request.session['orderid'] = orderid
    order = Orders.objects.get(id=orderid)
    orderamount = order.grand_total
    # if order.status == 'Cancelled' or order.status == 'orderfailed':
    #     messages.error(request, 'order was cancleed')
    #     return redirect('shop')
    razorpay_client = razorpay.Client(auth=(settings.KEY, settings.SECRET))
 
    currency = 'INR'
    razorpay_order = razorpay_client.order.create(dict(
        amount=int(orderamount) * 100,
        currency=currency,
        payment_capture='0'
    ))
    razorpay_order_id = razorpay_order['id']
    print("razorpay_order_id", razorpay_order['id'])
    razorpay_amount = razorpay_order['amount']
    print("razorpay_amount", razorpay_order['amount'])
    callback_url = request.build_absolute_uri(reverse('paymenthandler'))
    razorpay_payment = Razorpay_payment.objects.create(
        razorpay_payment_id=razorpay_order_id,
        amount=razorpay_amount,
        order=order


    )

    # Pass these details to the frontend
    context = {
        'order': order,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_merchant_key': settings.KEY,
        'razorpay_amount': razorpay_amount,
        'currency': currency,
        'razorpay_payment': razorpay_payment,
        'callback_url': callback_url
    }

    return render(request, 'order/payment_razorpay.html', context)


@csrf_exempt
def paymenthandler(request):
    if request.method == "POST":
        try:
            # Verify the payment signature
            razorpay_client = razorpay.Client(auth=(settings.KEY,
                                                    settings.SECRET))
            payment_id = request.POST.get('razorpay_payment_id', '')
            print("payment_id", payment_id)
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            print("razorpay_order_id", razorpay_order_id)
            signature = request.POST.get('razorpay_signature', '')
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            # verify the payment signature.
            result = razorpay_client.utility.verify_payment_signature(
                params_dict)

            # Signature verification successful
            try:
                razorpay_payment = Razorpay_payment.objects.get(razorpay_payment_id=razorpay_order_id)
                order = razorpay_payment.order
            except Razorpay_payment.DoesNotExist:
                messages.error(request, f'Razorpay payment with ID {razorpay_order_id} does not exist.')
                return redirect('order_failure', orderid=order.id)

            # Update order status to "Packed"
            order.status = "Packed"
            order.save()

            # Retrieve the payment object associated with the order
            payment = Payment.objects.get(order=order)

            # Update payment details
            payment.payment_method = "Razorpay"
            payment.status = "Success"
            payment.amount_paid = str(order.grand_total)
            payment.payment_id = request.POST.get('razorpay_payment_id', '')
            payment.save()

            # Redirect to the order page
            return redirect('order_page', orderid=order.id)

        except Exception as e:
            # Handle any exceptions
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('order_failer', orderid=order.id)

    else:
        messages.error(request, "Only POST requests are allowed for this endpoint.")
        return redirect('order_failer', orderid=order.id)


@login_required
def order_failer(request, orderid):
    order = Orders.objects.get(id=orderid)
    # order.status = 'orderfailed'
    # order.payment_method = None
    # order.save()
    orderitem = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'orderitem': orderitem
    }
    return render(request, 'order/order_failer.html', context)


@login_required
def incompleteorder(request):
    incomplete_orders = Orders.objects.filter(
        user=request.user,
        status__in=['orderfailed', 'OrderPending', 'Cancelled']
    ).prefetch_related('orderitem_set')

    context = {
        'incomplete_orders': incomplete_orders,
    }
    return render(request, 'order/incompleteorder.html', context)


@login_required
def delete_myorder(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid, user=request.user)
        order.is_active = False
        order.status = 'Cancelled'
        order.save()

        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            variant = get_object_or_404(Variant, id=item.variant.id)
            variant.quantity += item.quantity
            variant.save()

        if order.payment_method != 'COD':
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += Decimal(order.grand_total)
            wallet.save()

            Transaction.objects.create(wallet=wallet,
                                       transaction_type='credit',
                                       amount=Decimal(order.grand_total))

        messages.success(request, 'Order successfully cancelled and amount refunded if applicable.')
        return redirect('myorders')

    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('myorders')
    except Variant.DoesNotExist:
        messages.error(request, 'Variant not found.')
        return redirect('myorders')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('myorders')


@login_required
def del_incomplete_order(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid, user=request.user)
        order.is_active = False
        order.status = 'Cancelled'
        order.save()

        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            variant = get_object_or_404(Variant, id=item.variant.id)
            variant.quantity += item.quantity
            variant.save()

        messages.success(request, 'Order successfully cancelled.')
        return redirect('incompleteorder')

    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('incompleteorder')
    except Variant.DoesNotExist:
        messages.error(request, 'Variant not found.')
        return redirect('incompleteorder')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('incompleteorder')
