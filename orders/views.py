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
# Create your views here.
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line
import os
from django.core.paginator import Paginator


@login_required(login_url='login')
def myorders(request):
    # Fetch orders for the logged-in user
    orders = Orders.objects.filter(user=request.user).order_by('-order_date')

    # Paginate orders
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Fetch order items and payments related to the fetched orders
    order_items = OrderItem.objects.filter(order__in=page_obj.object_list)
    payments = Payment.objects.filter(order__in=page_obj.object_list)

    context = {
        'page_obj': page_obj,
        'order_items': order_items,
        'payments': payments,
    }

    return render(request, 'order/myorders.html', context)


def single_order(request, orderid):
    order = get_object_or_404(Orders, id=orderid)
    orderitems = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': orderitems
    }
    return render(request, 'order/single_order.html', context)


@login_required(login_url='login')
def return_orders(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid, user=request.user)
        if order.status == 'Delivered':
            order.is_active = False
            order.status = 'Returned'
            order.save()

            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                variant = get_object_or_404(Variant, id=item.variant.id)
                variant.quantity += item.quantity
                variant.save()

            if order.payment_method:
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


@login_required(login_url='login')
def place_order(request):
    if request.method == "POST":
        user = request.user
        try:
            subtotal = float(request.POST.get('subtotal'))
            shipping = float(request.POST.get('shipping'))
            tax = float(request.POST.get('tax'))
            grand_total = float(request.POST.get('grand_total'))
            payment_method = request.POST.get("payment_method")
            cart_id = request.POST.get('cart_id')
            address = Address.objects.filter(user=user, is_primary=True).first()

            if not address:
                messages.error(request, 'No primary address found.')
                return redirect('check_out')
        except (TypeError, ValueError):
            messages.error(request, 'Invalid monetary value provided.')
            return redirect('check_out')

        # Initialize coupon_discount
        coupon_discount = 0

        # Retrieve and delete coupon information from session
        if "applied_coupon_code" in request.session:
            del request.session["applied_coupon_code"]
        if "applied_coupon_discount" in request.session:
            coupon_discount = request.session.pop("applied_coupon_discount", 0)

        try:
            cart = Cart.objects.get(id=cart_id, user=user)
            cart_items = CartItem.objects.filter(cart=cart)

            # Check stock availability
            for cart_item in cart_items:
                variant = cart_item.variant
                if variant.quantity < cart_item.added_quantity:
                    messages.error(request, f'{variant.product.name} variant is out of stock.')
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

            # Calculate total discounts from product and category offers
            total_offer_discount = 0

            # Create the order object
            order_id = uuid.uuid4().hex[:8].upper()
            order = Orders.objects.create(
                user=user,
                order_id=order_id,
                delivery_address=address_data,
                order_total=subtotal,
                coupon_discount=coupon_discount,
                offer_discount=0,
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

                # Calculate offers
                offer_price, combined_discount, product_offer, category_offer = offer_calculation(variant_id=variant.id, current_time=timezone.now())

                # Update variant quantity
                variant.quantity -= cart_item.added_quantity
                variant.save()

                # Calculate discounts
                item_total_discount = (cart_item.variant.final_price - offer_price) * cart_item.added_quantity
                total_offer_discount += item_total_discount

                # Create OrderItem and assign values properly
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    quantity=cart_item.added_quantity,
                    ram=cart_item.variant.ram,
                    memmory=cart_item.variant.internal_memory,
                    price=cart_item.variant.final_price,
                    offer_price=offer_price,
                    product_discount=product_offer if product_offer else 0,
                    category_discount=category_offer if category_offer else 0
                )

            # Update the order with the total offer discount
            order.offer_discount = total_offer_discount
            # order.grand_total = subtotal + shipping + tax - total_offer_discount - coupon_discount
            order.save()

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


def offer_calculation(variant_id, current_time):
    variant = get_object_or_404(Variant, id=variant_id)
    combined_discount = 0
    offer_price = None
    product_offer = 0
    category_offer = 0
    final_price = variant.final_price

    if (final_price and
            variant.product.product_offer and
            variant.product.product_offer.active and
            variant.product.product_offer.valid_from <= current_time <= variant.product.product_offer.valid_to):

        product_offer = variant.product.product_offer.discount
        combined_discount += product_offer

    if (final_price and
            variant.product.category.category_offer and
            variant.product.category.category_offer.active and
            variant.product.category.category_offer.valid_from <= current_time <= variant.product.category.category_offer.valid_to):
        category_offer = variant.product.category.category_offer.discount
        combined_discount += category_offer

    if combined_discount > 0:
        offer_price = final_price - (final_price * combined_discount / 100)
    else:
        offer_price = final_price

    return offer_price, combined_discount, product_offer, category_offer


@login_required(login_url='login')
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

    payment = Payment.objects.get(order=order)

    context = {
        'order': order,
        'orderitems': orderitems,
        'sub_total': sub_total,
        'payment': payment
    }
    return render(request, "order/place_order.html", context)


@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
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
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            orderid = request.POST.get('orderid')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
def incompleteorder(request):
    incomplete_orders = Orders.objects.filter(
        user=request.user,
        status__in=['orderfailed', 'OrderPending']
    ).prefetch_related('orderitem_set').order_by('-order_date')

    context = {
        'incomplete_orders': incomplete_orders,
    }
    return render(request, 'order/incompleteorder.html', context)


@login_required(login_url='login')
def delete_myorder(request, orderid):
    try:
        order = get_object_or_404(Orders, id=orderid, user=request.user)
        if order.status in ['Delivered', 'Cancelled']:
            messages.error(request, 'The order cannot be cancelled')
            return redirect('myorders')
        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            variant = get_object_or_404(Variant, id=item.variant.id)
            variant.quantity += item.quantity
            variant.save()
        else:
            if order.payment_method != 'COD':
                wallet, created = Wallet.objects.get_or_create(
                    user=request.user)
                wallet.balance += Decimal(order.grand_total)
                wallet.save()
                Transaction.objects.create(wallet=wallet,
                                            transaction_type='credit',
                                            amount=Decimal(order.grand_total))
                messages.success(request, 'Order successfully cancelled')
        order.is_active = False
        order.status = 'Cancelled'
        order.save()

    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
    except Variant.DoesNotExist:
        messages.error(request, 'Variant not found.')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('myorders')


@login_required(login_url='login')
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


@login_required(login_url='login')
def download_invoice(request, order_id):
    try:
        order = get_object_or_404(Orders, id=order_id)

        if order.status in ["Cancelled", "orderfailed", "OrderPending"]:
            messages.error(request, f"Your order is {order.status}, can't download the invoice.")
            return redirect('myorders')

        order_items = OrderItem.objects.filter(order=order)
    except Orders.DoesNotExist:
        raise Http404("Order does not exist")

    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'

        # Define margins
        left_margin = 1 * inch
        right_margin = 0.5 * inch
        top_margin = 0.5 * inch
        bottom_margin = 0.5 * inch

        doc = SimpleDocTemplate(response, pagesize=landscape(letter),
                                leftMargin=left_margin, rightMargin=right_margin,
                                topMargin=top_margin, bottomMargin=bottom_margin)

        elements = []

        # Draw a colored border around the conten

        # Define styles
        styles = getSampleStyleSheet()
        heading_style = styles['Heading1']
        normal_style = styles['Normal']
        company_name_style = ParagraphStyle(
            name='V kart',
            parent=heading_style,
            alignment=1,
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.blue,
        )
        section_heading_style = ParagraphStyle(
            name='SectionHeading',
            parent=heading_style,
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=10,
        )
        sub_heading_style = ParagraphStyle(
            name='SubHeading',
            parent=heading_style,
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.darkblue,
            spaceBefore=10,
            spaceAfter=5,
        )

        # Add elements to the PDF
        elements.append(Spacer(1, top_margin))  # Add space at the top
        elements.append(Paragraph("V Kart", company_name_style))
        elements.append(Spacer(1, 0.2 * inch))

        line_drawing = Drawing(0, 20)
        line_drawing.add(Line(100, 0, 550, 0, strokeWidth=1, strokeColor=colors.black))
        elements.append(line_drawing)
        elements.append(Spacer(1, 0.1 * inch))

        user = order.user
        delivery_address = order.delivery_address
        elements.append(Paragraph("User Details", heading_style))
        elements.append(Paragraph(f"User Name: {user.username}", normal_style))
        elements.append(Paragraph(f"Email: {user.email}", normal_style))
        elements.append(Paragraph(f"Name Name:{delivery_address['first_name']} {delivery_address['second_name']}", normal_style))
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


        elements.append(Paragraph("Order Summary", section_heading_style))
        order_summary_data = [
            ['Order ID:', order.order_id],
            ['Order Status:', order.status],
            ['Total:', f"Rs. {order.order_total:.2f}"],
            ['Coupon Discount:', f"Rs. {order.coupon_discount:.2f}"],
            ['Offer Discount:', f"Rs. {order.offer_discount:.2f}"],
            ['Payment Method:', order.payment_method],
            ['Order Date:', order.order_date.strftime('%Y-%m-%d %H:%M:%S')],
            ['Last Update:', order.updated_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Shipping Cost:', f"Rs. {order.shipping:.2f}"],
            ['GST:', f"Rs. {order.tax:.2f}"],
            ['Grand Total:', f"Rs. {order.grand_total:.2f}"]
        ]

        order_summary_table = Table(order_summary_data, colWidths=[150, 400])
        order_summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.blue),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(order_summary_table)
        elements.append(Spacer(1, 0.5 * inch))

        line_drawing = Drawing(0, 20)
        line_drawing.add(Line(100, 0, 550, 0, strokeWidth=1, strokeColor=colors.black))
        elements.append(line_drawing)
        elements.append(Spacer(1, 0.5 * inch))

        elements.append(Paragraph("Order Items", heading_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Create table for order items
        data = [['Image','Product', 'Variant', 'Quantity', 'Product offer', 'Category Offer', 'Price', 'Offre Price']]
        for item in order_items:
            product_image_path = os.path.join(settings.MEDIA_ROOT, item.product.product_images.name)
            img = Image(product_image_path, width=50, height=50) if os.path.exists(product_image_path) else "Image not available"
            data.append([
                img,
                item.product.product_name,
                f"{item.variant.ram} RAM, {item.variant.internal_memory}",
                item.quantity,
                item.product_discount,
                item.category_discount,
                item.price,
                item.offer_price,
            ])

        table = Table(data, colWidths=[60, 200, 150, 50, 75])
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

        line_drawing = Drawing(0, 20)
        line_drawing.add(Line(100, 0, 550, 0, strokeWidth=1, strokeColor=colors.black))
        elements.append(line_drawing)
        elements.append(Spacer(1, 0.5 * inch))

        doc.build(elements)

        return response

    except Exception as e:
        return HttpResponse(f"An error occurred while generating the invoice: {str(e)}", content_type="text/plain")
