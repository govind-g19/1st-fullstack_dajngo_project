from orders import views
from django.urls import path


urlpatterns = [
    path('myorders', views.myorders, name='myorders'),
    path('place_order', views.place_order, name='place_order'),
    path('order_page/<int:orderid>/', views.order_page, name='order_page'),
    path('payment_cod/<int:orderid>/', views.payment_cod, name='payment_cod'),
    path('payment_wallet/<int:orderid>/',
         views.payment_wallet, name='payment_wallet'),

    path('payment_razorpay/<int:orderid>/', views.payment_razorpay,
         name='payment_razorpay'),
    path('paymenthandler/', views.paymenthandler, name='paymenthandler'),
    path('order_failer/<int:orderid>/', views.order_failer,
         name='order_failer'),
    path('incompleteorder', views.incompleteorder,
         name='incompleteorder'),
    path('delete_myorder/<int:orderid>/', views.delete_myorder,
         name='delete_myorder'),
    path('return_orders/<int:orderid>/', views.return_orders,
         name='return_orders'),
    path('del_incomplete_order/<int:orderid>/', views.del_incomplete_order,
         name='del_incomplete_order'),
    path('check_order_status/<int:orderid>/', views.check_order_status,
         name='check_order_status'),

    path('download_invoice/<int:order_id>/', views.download_invoice,
         name='download_invoice'),

]
