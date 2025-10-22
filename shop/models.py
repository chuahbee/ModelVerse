from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User
from filebrowser.fields import FileBrowseField
from filer.fields.image import FilerImageField
from django.utils.text import slugify
# Create your models here.

HOT_LEVEL_CHOICES = [(i, str(i)) for i in range(1, 6)]

class Attribute(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class AttributeValue(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values', blank=True, null=True)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('attribute', 'value')

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"
    
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    hot_level = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    hot_sale = models.BooleanField(default=False, verbose_name="Hot Sale")

    hot_level = models.PositiveIntegerField(default=0, choices=HOT_LEVEL_CHOICES, verbose_name="Hot Level")

    categories = models.ManyToManyField(Category, related_name='products', blank=True)

    image = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    size_chart = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    is_in_stock = models.BooleanField(default=True)
    is_sale = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True) 
    is_preorder = models.BooleanField(default=False)

    # discount and sale
    discount_percent = models.IntegerField(blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name
    
    @property
    def final_price(self):
        if self.is_sale:
            if self.discount_amount:
                return max(self.price - self.discount_amount, Decimal("0.00"))
            elif self.discount_percent:
                return max(self.price * (Decimal("1.00") - Decimal(self.discount_percent) / Decimal("100")), Decimal("0.00"))
        return self.price
    
    def get_attributes(self):
        from collections import defaultdict
        result = defaultdict(list)
        for pa in self.product_attributes.select_related('attribute', 'value'):
            if pa.attribute and pa.value:
                result[pa.attribute.name].append(pa.value)
        return dict(result)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')

    # ✅ browse 已有文件
    # image_filebrowse = FileBrowseField(
    #     "Image (FileBrowser)",
    #     max_length=200,
    #     directory="products/gallery/",
    #     blank=True,
    #     null=True
    # )

    image = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.alt_text or f"{self.product.name} image"
    
class ImageAsset(models.Model):
    file = models.ImageField(upload_to='products/gallery/')
    title = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title or self.file.name

class ProductRating(models.Model):
    product = models.ForeignKey(
        Product, 
        related_name="ratings", 
        on_delete=models.CASCADE
        )
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('product', 'session_key')

class CartItem(models.Model):
    session_key = models.CharField(max_length=100)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    attribute_values = models.ManyToManyField('AttributeValue', blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        attrs = ", ".join([str(v) for v in self.attribute_values.all()])
        return f"{self.quantity} x {self.product.name} ({attrs})"
 
class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_attributes')
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, null=True, blank=True)
    value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        product_name = self.product.name if self.product else ""
        attribute_name = self.attribute.name if self.attribute else ""
        value_value = self.value.value if self.value else ""
        return f"{product_name} - {attribute_name}: {value_value}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # 防止重复收藏

class Order(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField() 
    phone = models.CharField(max_length=50)
    address = models.TextField()
    postcode = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    coupon_code = models.CharField(max_length=100, blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    session_key = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    attribute_values = models.ManyToManyField(AttributeValue, blank=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.IntegerField(blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(blank=True, null=True)
    valid_to = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.code

class CompanyInfo(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    logo = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    website = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    pinterest_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name or "Company Info"
    
class MenuItem(models.Model):
    title = models.CharField(max_length=100, verbose_name="Menu Title")
    url = models.CharField(max_length=255, verbose_name="URL", blank=True, null=True)
    visible = models.BooleanField(default=True, verbose_name="Visible")
    open_in_new_window = models.BooleanField(default=False, verbose_name="Open in new window")

    class Meta:
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"

    def __str__(self):
        return self.title
    
class FooterLink(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)
    open_in_new_window = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title or f"Banner {self.id}"


