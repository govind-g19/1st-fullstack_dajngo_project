from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
# Catagory


class Category(models.Model):
    category_name = models.CharField(max_length=150, unique=True)
    soft_deleted = models.BooleanField(default=False)
    category_details = models.TextField(null=True, blank=True)
    is_available = models.BooleanField(default=True, blank=True, null=True)

    def __str__(self):
        return self.category_name


# Product

class ProductOffers(models.Model):
    product_offer = models.CharField(max_length=100)
    discount = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.product_offer

    def discount_percent(self):
        self.discount = self.discount/100
        return self.discount


class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    product_images = models.ImageField(upload_to="images/products")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(max_length=500, blank=True)
    create_date = models.DateField(auto_now_add=True)
    modified_date = models.DateField(auto_now=True)
    available = models.BooleanField(default=True)
    soft_deleted = models.BooleanField(default=False)
    product_offer = models.ForeignKey(ProductOffers, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product_name}"


class Variant(models.Model):
    RAM_CHOICES = [
        ("4GB", "4GB"),
        ("8GB", "8GB"),
        ("16GB", "16GB"),
        # Add more choices as needed
    ]
    INTERNAL_MEMORY_CHOICES = [
        ("64GB", "64GB"),
        ("128GB", "128GB"),
        ("256GB", "256GB"),
        # Add more choices as needed
    ]

    ram = models.CharField(max_length=50, choices=RAM_CHOICES)
    internal_memory = models.CharField(max_length=50,
                                       choices=INTERNAL_MEMORY_CHOICES)
    final_price = models.FloatField(null=True, blank=True)
    product = models.ManyToManyField(Product)
    is_available = models.BooleanField(default=True)
    quantity = models.IntegerField(default=1000)
    deleted = models.BooleanField(default=False, null=True, blank=True)
    low_stock_threshold = models.IntegerField(default=50,
                                              null=True, blank=True)

    def __str__(self):
        products_str = ", ".join(
            [product.product_name for product in self.product.all()]
        )
        return f"{products_str} {self.ram} RAM, {self.internal_memory}  Memory"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="photos/product",)

    def __str__(self):
        return f"Image of {self.product.product_name}"


# class CategoryOffers(models.Model):
#     category_offer_name = models.CharField(max_length=100)
#     discount = models.IntegerField(default=0)
#     valid_from = models.DateTimeField()
#     valid_to = models.DateTimeField()


# to rate the varient

class ReviewRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1),
                                             MaxValueValidator(5)])
    comment = models.CharField(max_length=20)
    review = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"user-{self.user.username}, comment -{self.comment}"
