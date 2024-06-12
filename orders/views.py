from django.shortcuts import render, redirect, get_object_or_404
from .models import Orders, OrderItem, Payment, Razorpay_payment
from authapp.models import Wallet, Transaction
from django.utils import timezone
from authapp.models import Address
from cartapp.models import CartItem, Cart
from adminmanager.models import Variant
import razorpay
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.utils.timezone import now
# Create your views here.
import reportlab
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.doctemplate import PageTemplate, Frame
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle


@login_required
def myorders(request):
    # Fetch orders for the logged-in user
    orders = Orders.objects.filter(user=request.user)
    print(reportlab.__version__)

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
def return_orders(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid, user=request.user)
        # Check if the order status is 'Delivered' and it was made within the last 30 days
        # and (now() - order.order_date).days <= 30
        if order.status == 'Delivered':
            order.is_active = False
            order.status = 'Returned'
            order.save()

            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                variant = get_object_or_404(Variant, id=item.variant.id)
                variant.quantity += item.quantity
                variant.save()

            if order.payment_method != 'COD':
                wallet, created = Wallet.objects.get_or_create(
                    user=request.user)
                wallet.balance += Decimal(order.grand_total)
                wallet.save()

                Transaction.objects.create(wallet=wallet,
                                           transaction_type='credit',
                                           amount=Decimal(order.grand_total))

            messages.success(request, 'Order successfully cancelled')
            return redirect('myorders')
        else:
            if order.status != 'Delivered':
                messages.error(request, 'Only Delivered items can be returned')
            else:
                messages.error(request, 'Orders older than 30 days cannot be returned')

    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
    except Variant.DoesNotExist:
        messages.error(request, 'Variant not found.')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")


@login_required
def place_order(request):
    if request.method == "POST":
        user = request.user
        try:
            subtotal = float(request.POST.get('subtotal'))
            discount_given = float(request.POST.get('discount_given'))
            shipping = float(request.POST.get('shipping'))
            tax = float(request.POST.get('tax'))
            grand_total = float(request.POST.get('grand_total'))
            payment_method = request.POST.get("payment_method")
            cart_id = request.POST.get('cart_id')
            address = Address.objects.filter(is_primary=True).first()

            if not address:
                messages.error(request, 'No primary address found.')
                return redirect('check_out')
        except (TypeError, ValueError):
            messages.error(request, 'Invalid monetary value provided.')
            return redirect('check_out')

        try:
            cart = Cart.objects.get(id=cart_id, user=user)
            cart_items = CartItem.objects.filter(cart=cart)

            # Check stock availability
            for cart_item in cart_items:
                variant = cart_item.variant
                if variant.quantity < cart_item.added_quantity:
                    messages.error(request, f'''{variant.product.name}
                                    variant is out of stock.''')
                    return redirect('shop')

            # Prepare address data
            address_data = {
                "first_name": address.first_name,
                "second_name": address.second_name,
                "house_address": address.house_address,
                "phone_number": address.phone_number,
                "city": address.city,
                "state": address.state,
                "pin_code": address.pin_code,
                "land_mark": address.land_mark
            }

            # Create the order object
            order_id = uuid.uuid4().hex[:8].upper()
            order = Orders.objects.create(
                user=user,
                order_id=order_id,
                delivery_address=address_data,
                order_total=subtotal,
                discount_given=discount_given,
                shipping=shipping,
                tax=tax,
                grand_total=grand_total,
                status='OrderPending',
                order_date=timezone.now(),
                payment_method=payment_method
            )

            # Update inventory and create order items
            for cart_item in cart_items:
                variant = cart_item.variant
                variant.quantity -= cart_item.added_quantity
                variant.save()

                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    quantity=cart_item.added_quantity,
                    ram=cart_item.variant.ram,
                    memmory=cart_item.variant.internal_memory,
                    price=cart_item.variant.final_price
                )

            # Delete the cart after order is created
            cart.delete()

            # Create payment entry
            Payment.objects.create(
                user=user,
                payment_method=payment_method,
                status='NOT PAID',
                amount_paid=order.grand_total,
                order=order
            )

            messages.success(request, 'Order placed successfully!')
            return redirect("order_page", orderid=order.id)

        except Cart.DoesNotExist:
            messages.error(request, 'Cart not found.')
            return redirect('shop')
        except Variant.DoesNotExist:
            messages.error(request, 'One of the product variants does not exist.')
            return redirect('shop')

    messages.error(request, 'Invalid request method.')
    return redirect('check_out')


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

    payment = Payment.objects.filter(order=order)

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
        order.payment_method = "COD"
        order.status = "Ordered"
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

                order.payment_method = 'wallet'
                order.status = "Ordered"
                order.save()

                messages.success(request,
                                 'Payment successful and order status updated')
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
def check_order_status(request, orderid):
    try:
        order = Orders.objects.get(id=orderid)
        if order.status in ['Cancelled', 'Returned']:
            return JsonResponse({'status': 'error',
                                 'message': 'Order was canceled'})
        else:
            return JsonResponse({'status': 'success'})
    except Orders.DoesNotExist:
        return JsonResponse({'status': 'error',
                             'message': 'Order not found'})


@login_required
def payment_razorpay(request, orderid):
    try:
        order = Orders.objects.get(id=orderid)
    except Orders.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('shop')

    if order.status in ['Cancelled', 'Returned']:
        messages.error(request, 'Order was canceled or returned')
        return redirect('shop')

    request.session['orderid'] = orderid
    orderamount = order.grand_total

    razorpay_client = razorpay.Client(auth=(settings.KEY, settings.SECRET))

    currency = 'INR'
    try:
        razorpay_order = razorpay_client.order.create(dict(
            amount=int(orderamount) * 100,
            currency=currency,
            payment_capture='0'
        ))
    except Exception as e:
        messages.error(request, 'Razorpay order creation failed: {}'.format(e))
        return redirect('shop')

    razorpay_order_id = razorpay_order['id']
    razorpay_amount = razorpay_order['amount']
    callback_url = request.build_absolute_uri(reverse('paymenthandler'))

    try:
        razorpay_payment = Razorpay_payment.objects.create(
            razorpay_payment_id=razorpay_order_id,
            amount=razorpay_amount,
            order=order
        )
    except Exception as e:
        messages.error(request, 'Payment record creation failed: {}'.format(e))
        return redirect('shop')

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
            orderid = request.POST.get('orderid')
            print("the order id is", orderid)
            # verify the payment signature.
            razorpay_client.utility.verify_payment_signature(
                params_dict)
            # Signature verification successful
            try:
                razorpay_payment = Razorpay_payment.objects.get(
                    razorpay_payment_id=razorpay_order_id)
                order = razorpay_payment.order
            except Razorpay_payment.DoesNotExist:
                messages.error(request,
                               f'''Razorpay payment with ID
                               {razorpay_order_id} does not exist.''')
                return redirect('order_failure', orderid=order.id)

            # Update order status to "Ordered"
            order.payment_method = "Razorpay"
            order.status = "Ordered"
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
        messages.error(request, "Only POST requests are allowed")
        return redirect('order_failer', orderid=request.POST.get('orderid'))


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
        status__in=['orderfailed', 'OrderPending']
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

        messages.success(request, 'Order successfully cancelled')
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

# to download the invoice

@login_required
def download_invoice(request, order_id):
    try:
        order = get_object_or_404(Orders, id=order_id)
        # if order.user != request.user or request.user.is_superuser:
        #     messages.error(request, "You do not have permission to view this invoice.")
        #     return redirect('myorders')

        if order.status in ["Cancelled", "orderfailed", "OrderPending"]:
            messages.error(request, f"Yoou order is {order.status}, Can't download the invoice .")
            return redirect('myorders')

        order_items = OrderItem.objects.filter(order=order)
    except Orders.DoesNotExist:
        raise Http404("Order does not exist")

    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []

        # Define custom styles
        styles = getSampleStyleSheet()
        heading_style = styles['Heading1']
        heading_style.alignment = 0
        normal_style = styles['Normal']
        company_name_style = ParagraphStyle(
            name='V kart',
            parent=heading_style,  # Inherits from the existing heading_style
            alignment=1,  # Center alignment
            fontName='Helvetica-Bold',  # Specify the font name
            fontSize=14,  # Specify the font size
            textColor=colors.blue,  # Specify the text color
        )
    
        # Add elements to the PDF
        elements.append(Paragraph("V Kart", company_name_style))

        elements.append(Spacer(1, 0.2 * inch))

        user = order.user
        delivery_address = order.delivery_address
        elements.append(Paragraph("User Details", heading_style))
        elements.append(Paragraph(f"User Name: {user.username}", normal_style))
        elements.append(Paragraph(f"Email: {user.email}", normal_style))
        elements.append(Paragraph(f"First Name: {user.first_name}", normal_style))
        elements.append(Paragraph(f"Last Name: {user.last_name}", normal_style))
        elements.append(Paragraph(f"Phone Number: {delivery_address['phone_number']}", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Retrieve admin details from settings
        admin_details = settings.ADMIN_DETAILS
        elements.append(Paragraph("Point of Delivery", heading_style))
        elements.append(Paragraph(f"Company Name: {admin_details['company_name']}", normal_style))
        elements.append(Paragraph(f"Address: {admin_details['address']}", normal_style))
        elements.append(Paragraph(f"Contact Email: {admin_details['contact_email']}", normal_style))
        elements.append(Paragraph(f"Phone: {admin_details['phone']}", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Standardizing delivery address
        address = f"{delivery_address['house_address']}, {delivery_address['city']}, {delivery_address['state']} - {delivery_address['pin_code']}\n"
        address += f"Landmark: {delivery_address['land_mark']}"
        elements.append(Paragraph("Delivery Address", heading_style))
        elements.append(Paragraph(address, normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        elements.append(Paragraph("Order Items", heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Create table for order items
        data = [['Product', 'Variant', 'Quantity', 'Price']]
        for item in order_items:
            data.append([
                item.product.product_name,
                f"{item.variant.ram} RAM, {item.variant.internal_memory}",
                item.quantity,
                item.price
            ])

        table = Table(data, colWidths=[200, 150, 50, 75])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5 * inch))

        # Add grand total
        elements.append(Paragraph(f"Order Status: {order.status}", normal_style))
        elements.append(Paragraph(f"Order Date: {order.order_date.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Paragraph(f"Last Update: {order.updated_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Paragraph(f"Shipping Cost: {order.shipping}", normal_style))
        elements.append(Paragraph(f"GST : {order.tax}", normal_style))
        elements.append(Paragraph(f"Grand Total: {order.grand_total}", normal_style))
        elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)

        return response
    except Exception as e:
        return HttpResponse(f"An error occurred while generating the invoice: {str(e)}", content_type="text/plain")