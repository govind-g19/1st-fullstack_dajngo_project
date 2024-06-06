from mainapp import views
from django.urls import path


urlpatterns = [
    path('index', views.index, name='index'),
    path('base', views.base, name='base'),
    path('shop', views.shop, name='shop'),
    path('product_details/<int:product_id>/', views.product_details,
         name='product_details'),
    path('update_price/<int:product_id>/', views.update_price,
         name='update_price'),
    path('add_review/<int:variant_id>/', views.add_review, name='add_review'),
    path('my_reviews', views.my_reviews, name='my_reviews'),
    path('edit_review/<int:review_id>/', views.edit_review,
         name='edit_review'),
    path('delete_review/<int:review_id>/', views.delete_review,
         name='delete_review'),
    path('chat_bot', views.chat_bot, name='chat_bot'),
]
