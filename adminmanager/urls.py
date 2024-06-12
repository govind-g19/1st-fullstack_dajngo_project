from adminmanager import views
from django.urls import path

urlpatterns = [
    path('admin-login',
         views.admin_loogin,
         name='admin-login'),

    path('admin-logout',
         views.admin_logout,
         name='admin-logout'),

    path('admin-index',
         views.admin_index,
         name='admin-index'),
    # users 
    path('admin-user',
         views.admin_user_list,
         name='admin-user'),

    path('block_user/<int:id>/',
         views.block_user,
         name='block_user'),

    path('unblock_user/<int:id>/',
         views.unblock_user,
         name='unblock_user'),

    path('promote_user/<int:id>/',
         views.promote_user,
         name='promote_user'),
    path('depromote_user/<int:id>/',
         views.depromote_user,
         name='depromote_user'),

    path('add_category',
         views.add_category,
         name='add_category'),

    path('category',
         views.Category_List,
         name='category'),

    path('edit_category/<int:id>/',
         views.Edit_Cat,
         name='edit_category'),

    path('soft_delete_category/<int:id>/',
         views.soft_delete_category,
         name='soft_delete_category'),

    path('undo_soft_delete_category/<int:id>/',
         views.undo_soft_delete_category,
         name='undo_soft_delete_category'),


    # product
    path('product_list',
         views.Product_list,
         name='product_list'),

    path('add_product',
         views.Add_Product,
         name='add_product'),

    path('edit_product/<int:id>/',
         views.Edit_Product,
         name='edit_product'),

    path('soft_delete_product/<int:product_id>/',
         views.soft_delete_product,
         name='soft_delete_product'),

    path('undo_soft_delete_product/<int:product_id>/',
         views.undo_soft_delete_product,
         name='undo_soft_delete_product'),


    # varients

    path('view_variant/<int:product_id>/',
         views.view_variant,
         name='view_variant'),

    path('edit_varient/<int:id>/',
         views.edit_varient,
         name='edit_varient'),

    path('delete_variant/<int:product_id>/',
         views.delete_variant,
         name='delete_variant'),

    path('undo_delete_variant/<int:product_id>/',
         views.undo_delete_variant,
         name='undo_delete_variant'),

    path('add_varient/',
         views.add_varient,
         name='add_varient'),

    path('admin_view_review/<int:variant_id>/', views.admin_view_review,
         name='admin_view_review'),

    path('admin_block_review/<int:review_id>/', views.admin_block_review,
         name='admin_block_review'),

    path('admin_unblock_review/<int:review_id>/', views.admin_unblock_review,
         name='admin_unblock_review'),

    path('admin_order_view/',
         views.admin_order_view,
         name='admin_order_view'),
    path('admin_delete_order/<int:orderid>/',
         views.admin_delete_order,
         name='admin_delete_order'),
    path('update_order_status/<int:order_id>/', views.update_order_status,
         name='update_order_status'),
    path('detail_order/<int:orderid>/',
         views.detail_order,
         name='detail_order'),
    path('dashboard',
         views.dashboard,
         name='dashboard'),
    path('sales_report/', views.sales_report, name='sales_report'),
    # To add product offers
    path('add_product_offer', views.add_product_offer,
         name='add_product_offer'),
    path('product_offers_list', views.product_offers_list,
         name='product_offers_list'),
    path('edit_product_offer/<int:offer_id>/', views.edit_product_offer,
         name='edit_product_offer'),
    path('delete_product_offer/<int:offer_id>/', views.delete_product_offer,
         name='delete_product_offer'),
    path('undo_delete_product_offer/<int:offer_id>/',
         views.undo_delete_product_offer, name='undo_delete_product_offer')


]
