from django.contrib import admin
from .models import Product, Attribute, AttributeValue, ProductAttribute, ProductImage, Order, OrderItem, CompanyInfo, MenuItem, FooterLink, Banner, AttributeValue,Coupon
from filebrowser.fields import FileBrowseField
from django import forms
from filer.fields.image import FilerImageField
from django.forms.widgets import Select
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.forms import ModelForm

class AttributeValueSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        # 如果是有效 value，查询对应 attribute_id
        try:
            attribute_value = AttributeValue.objects.get(pk=value)
            option['attrs']['data-attribute'] = str(attribute_value.attribute_id)
        except (AttributeValue.DoesNotExist, ValueError, TypeError):
            pass

        return option

class AttributeValueForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        attribute = cleaned_data.get('attribute')
        value = cleaned_data.get('value')

        if attribute and value:
            exists = AttributeValue.objects.filter(
                attribute=attribute,
                value=value
            )
            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise ValidationError("This Attribute + Value already exists.")

        return cleaned_data
    
# Attribute and AttributeValue filters
class AttributeFilter(admin.SimpleListFilter):
    title = 'Attribute'
    parameter_name = 'attribute'

    def lookups(self, request, model_admin):
        # 给 dropdown 提供选项
        attributes = Attribute.objects.filter(
            productattribute__isnull=False
        ).distinct()
        return [(attr.id, attr.name) for attr in attributes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(product_attributes__attribute_id=self.value())
        return queryset

class AttributeValueFilter(admin.SimpleListFilter):
    title = 'Attribute Value'
    parameter_name = 'attribute_value'

    def lookups(self, request, model_admin):
        values = AttributeValue.objects.all()
        return [(val.id, f"{val.attribute.name}: {val.value}") for val in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(product_attributes__value_id=self.value())
        return queryset
   
    # AttributeValue

class ProductAttributeInlineForm(forms.ModelForm):
    class Meta:
        model = ProductAttribute
        fields = ['attribute', 'value']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        attribute_id = None

        if self.instance and self.instance.attribute_id:
            attribute_id = self.instance.attribute_id

        if not attribute_id and self.data:
            prefix = self.prefix
            key = f"{prefix}-attribute"
            if key in self.data:
                attribute_id = self.data.get(key)

        if attribute_id:
            values_qs = AttributeValue.objects.filter(attribute_id=attribute_id)

            # ✅ 确保旧 value 存在于 queryset
            if self.instance and self.instance.value and self.instance.value not in values_qs:
                values_qs = AttributeValue.objects.filter(
                    Q(attribute_id=attribute_id) | Q(pk=self.instance.value_id)
                )

            self.fields['value'].queryset = values_qs

            # ✅ 设置 initial value
            if self.instance and self.instance.value_id:
                self.fields['value'].initial = self.instance.value_id

        else:
            self.fields['value'].queryset = AttributeValue.objects.none()

        # ✅ 存 data-selected-value 给 js
        if self.instance and self.instance.value_id:
            self.fields['value'].widget.attrs['data-selected-value'] = self.instance.value_id
        else:
            self.fields['value'].widget.attrs['data-selected-value'] = ''

class ProductAttributeInline(admin.TabularInline):
    # model = ProductAttribute
    # form = ProductAttributeInlineForm

    # extra = 0
    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     if db_field.name == "value":
    #         # 如果有 attribute 的值，从 GET 请求中读取
    #         try:
    #             attribute_id = int(request.GET.get('attribute'))
    #             kwargs["queryset"] = AttributeValue.objects.filter(attribute_id=attribute_id)
    #         except (TypeError, ValueError):
    #             kwargs["queryset"] = AttributeValue.objects.none()  # 不显示任何
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # max_num = None
    # can_delete = True
    # show_change_link = True
    model = ProductAttribute
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "value" and request is not None:
            if "_popup" not in request.GET:
                try:
                    obj_id = request.resolver_match.kwargs.get("object_id")
                    if obj_id:
                        product = Product.objects.get(pk=obj_id)
                        attribute_id = request.POST.get("productattribute_set-0-attribute")
                        if attribute_id:
                            field.queryset = AttributeValue.objects.filter(attribute_id=attribute_id)
                except:
                    pass  # 在新增页面还拿不到 object_id

        return field

# ProductImage inline
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductAttributeInline, ProductImageInline]
    list_filter = ['is_in_stock', 'is_sale', 'is_preorder']
    list_editable = ['is_in_stock', 'is_sale', 'is_preorder']
    search_fields = ['name', 'description', 'price']
    list_display = ['name', 'price', 'is_in_stock', 'is_sale', 'is_preorder']

if not admin.site.is_registered(Product):
    admin.site.register(Product, ProductAdmin)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    readonly_fields = ['attribute_values_display']
    fields = ['product', 'quantity', 'subtotal', 'attribute_values_display']

    def attribute_values_display(self, obj):
        return ", ".join(str(v) for v in obj.attribute_values.all())
    attribute_values_display.short_description = "Attribute Values"

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']

@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    form = AttributeValueForm  # ✅ 使用你定义的 form
    list_display = ['attribute', 'value']
    search_fields = ['value']
    list_filter = ['attribute']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'grand_total', 'created_at']
    inlines = [OrderItemInline]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'discount_amount', 'active', 'valid_from', 'valid_to']
    search_fields = ['code']

@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'contact']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'visible')
    list_editable = ('visible',)

@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "order", "visible")
    list_editable = ("url", "order", "visible")
    ordering = ("order",)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')
    list_editable = ('is_active', 'order')