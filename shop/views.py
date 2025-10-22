import sys
# import logging
sys.stdout.reconfigure(encoding='utf-8')
# logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.db.models import Avg
from urllib3 import request
from .forms import CouponApplyForm
from .models import Product, CartItem, Attribute, AttributeValue, ProductRating, Favorite, Order, OrderItem, Coupon, CompanyInfo, MenuItem,Banner,Category
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib import messages
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, HexColor
from django.contrib.sessions.models import Session
import os

# Create your views here.
def home_view(request):
    banners = Banner.objects.filter(is_active=True).order_by('order')
    company_info = CompanyInfo.objects.first()

    menu_items = MenuItem.objects.filter(visible=True)

    products = Product.objects.all()
    new_products = Product.objects.order_by('-created_at')[:4]

    hot_sale_products = Product.objects.filter(hot_sale=True).order_by('-id')

    featured_categories = Category.objects.filter(is_featured=True).order_by('name')

    # print("Hot Sale Products:", hot_sale_products)

    return render(request, 'shop/page/home.html', {
        'products': products,
        'new_products': new_products,
        'banners': banners,
        'company_info': company_info,
        "hot_sale_products": hot_sale_products,
        'featured_categories': featured_categories,
    })


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True )
    products = category.products.filter(categories=category, is_active=True).order_by('-created_at').distinct()

    return render(request, 'shop/page/category_products.html', {
        'category': category,
        'products': products,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'shop/page/product_list.html', {'products': products})


def add_to_cart(request, product_id):
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    product = get_object_or_404(Product, id=product_id)
    quantity_to_add = int(request.POST.get('quantity', 1))

    # 这里改掉！！
    attribute_value_ids = []
    for key in request.POST:
        if key.startswith('attribute_values_'):
            attribute_value_ids.append(request.POST[key])

    # 查现有记录
    items = CartItem.objects.filter(session_key=session_key, product=product)
    matched_item = None
    for item in items:
        existing_ids = list(item.attribute_values.values_list('id', flat=True))
        if set(existing_ids) == set(map(int, attribute_value_ids)):
            matched_item = item
            break

    if matched_item:
        matched_item.quantity += quantity_to_add
        matched_item.save()
    else:
        new_item = CartItem.objects.create(
            session_key=session_key,
            product=product,
            quantity=quantity_to_add,
        )
        if attribute_value_ids:
            new_item.attribute_values.set(attribute_value_ids)

    return redirect('cart_view')


def update_cart_item(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        item = get_object_or_404(CartItem, id=item_id)
        item.quantity = quantity
        item.save()
    return redirect('cart_view')


def cart_view(request):
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    cart_items = CartItem.objects.filter(session_key=session_key)

    total = sum(item.quantity * item.product.final_price for item in cart_items)

    discount = Decimal('0.00')
    grand_total = total - discount

    cart_product_ids = cart_items.values_list('product_id', flat=True)

    related_products = Product.objects.exclude(id__in=cart_product_ids)[:4]

    context = {
        'cart_items': cart_items,
        'total': total,
        'discount': discount,
        'grand_total': grand_total,
        'related_products': related_products,
        'quantity_range': range(1, 11),
    }
    return render(request, 'shop/page/cart.html', context)


def checkout_view(request):
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    cart_items = CartItem.objects.filter(session_key=session_key)

    total = sum(item.quantity * item.product.final_price for item in cart_items)
    discount = Decimal('0.00')
    coupon_code = None

    if request.method == 'POST' and 'apply_coupon' in request.POST:
        form = CouponApplyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            now_time = now()
            try:
                coupon = Coupon.objects.get(
                    code__iexact=code,
                    active=True,
                    valid_from__lte=now_time,
                    valid_to__gte=now_time,
                )
                coupon_code = coupon.code
                if coupon.discount_amount:
                    discount = coupon.discount_amount
                elif coupon.discount_percent:
                    discount = total * Decimal(coupon.discount_percent) / Decimal('100')
            except Coupon.DoesNotExist:
                discount = Decimal('0.00')
    else:
        form = CouponApplyForm()

    grand_total = total - discount

    context = {
        'cart_items': cart_items,
        'total': total,
        'discount': discount,
        'grand_total': grand_total,
        'coupon_code': coupon_code,
        'form': form,
    }
    return render(request, 'shop/page/checkout.html', context)


@csrf_exempt
def process_checkout(request):
    if request.method != 'POST':
        return redirect('cart_view')

    # 确保 session 存在
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    print("当前生成的 session_key:", session_key)

    # 公司资料
    company_info = CompanyInfo.objects.first()

    # 获取订单资料
    name = request.POST.get('name')
    email = request.POST.get('email')
    phone = request.POST.get('phone')
    address = request.POST.get('address')
    postcode = request.POST.get('postcode')
    city = request.POST.get('city')
    state = request.POST.get('state')
    country = request.POST.get('country')

    grand_total = Decimal(request.POST.get('grand_total', '0.00'))
    coupon_code = request.POST.get('coupon_code')
    discount = Decimal(request.POST.get('discount', '0.00'))

    # 获取购物车内容
    cart_items = CartItem.objects.filter(session_key=session_key)
    print("购物车商品数量：", cart_items.count())
    # logger.info(f"Cart items count: {cart_items.count()}") 如果换成logged方式输出

    if not cart_items.exists():
        messages.error(request, "购物车为空，无法结账。")
        return redirect('cart_view')

    # 创建订单
    order = Order.objects.create(
        name=name,
        email=email,
        phone=phone,
        address=address,
        postcode=postcode,
        city=city,
        state=state,
        country=country,
        grand_total=grand_total,
        coupon_code=coupon_code,
        discount=discount,
        session_key=session_key,
    )
    print("创建订单成功，ID：", order.id)

    # 折扣比例计算
    total = sum(item.product.final_price * item.quantity for item in cart_items)
    discount_ratio = discount / total if total > 0 else Decimal("0.00")

    for item in cart_items:
        original_unit_price = item.product.final_price
        discounted_unit_price = original_unit_price * (Decimal("1.00") - discount_ratio)
        discounted_unit_price = discounted_unit_price.quantize(Decimal("0.01"))
        subtotal = discounted_unit_price * item.quantity

        order_item = OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            subtotal=subtotal,
        )

        # ✅ attribute_values 处理
        for attr_value in item.attribute_values.all():
            order_item.attribute_values.add(attr_value)

    # 清空购物车
    cart_items.delete()

    # 安全输出 HTML 辅助
    def safe_html(text):
        return text if text else ""

    # 邮件模板准备
    logo_url = f"{settings.DOMAIN}{company_info.logo.url}" if company_info and company_info.logo else ""
    company_html = f"""
        <div style="border-bottom:1px solid #ccc; margin-bottom:10px; padding-bottom:10px;">
            {"<img src='" + logo_url + "' height='50'>" if logo_url else ""}
            <h3>{safe_html(company_info.name)}</h3>
            <p>{safe_html(company_info.address)}</p>
            <p>{safe_html(company_info.contact)}</p>
            <p>
                {"<a href='" + company_info.facebook_url + "'>Facebook</a>" if company_info.facebook_url else ""}
                {"<a href='" + company_info.instagram_url + "' style='margin-left:10px;'>Instagram</a>" if company_info.instagram_url else ""}
                {"<a href='" + company_info.tiktok_url + "' style='margin-left:10px;'>TikTok</a>" if company_info.tiktok_url else ""}
                {"<a href='" + company_info.pinterest_url + "' style='margin-left:10px;'>Pinterest</a>" if company_info.pinterest_url else ""}
            </p>
        </div>
    """ if company_info else ""

    coupon_html = f"""
        <p>Coupon Used: <strong>{coupon_code}</strong></p>
        <p>Discount: -RM {discount:.2f}</p>
    """ if coupon_code else """
        <p>Coupon Used: <strong>None</strong></p>
        <p>Discount: -RM 0.00</p>
    """

    order_items_html = ""
    for idx, item in enumerate(order.items.all(), start=1):
        order_items_html += f"""
            <tr>
                <td>{idx}</td>
                <td>{item.product.name}</td>
                <td>{item.quantity}</td>
                <td>RM {item.product.final_price:.2f}</td>
                <td>RM {item.subtotal:.2f}</td>
            </tr>
        """

    # 构造邮件正文
    message = f"""
    {company_html}
    <h3>谢谢您的订单，{name}！</h3>
    <p>订单号: <strong>{order.id}</strong></p>
    <h4>Order Items:</h4>
    <table border="1" cellspacing="0" cellpadding="5">
        <tr>
            <th>No.</th>
            <th>Product</th>
            <th>Qty</th>
            <th>Price</th>
            <th>Subtotal</th>
        </tr>
        {order_items_html}
    </table>
    {coupon_html}
    <p>应付总额：<strong>RM {grand_total:.2f}</strong></p>
    <p>我们会尽快为您处理订单。</p>
    """

    # 发送邮件
    try:
        email_msg = EmailMessage(
            subject='订单通知',
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_msg.content_subtype = 'html'
        email_msg.encoding = 'utf-8'
        email_msg.send()
        print("邮件发送成功")
    except Exception as e:
        print("邮件发送失败：", e)

    # Debug 检查订单商品是否写入成功
    if not order.items.exists():
        print("订单创建后没有 items，可能出错了！")

    return redirect(f"/shop/checkout/success/?order_id={order.id}")
        
def checkout_success(request):
    order_id = request.GET.get('order_id')
    if not order_id:
        return redirect('/')  # 没有order_id就回首页

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return redirect('/')

    # 验证当前 session 是否与订单一致
    current_session = request.session.session_key
    if not current_session:
        request.session.save()
        current_session = request.session.session_key

    if order.session_key and order.session_key != current_session:
        return render(request, 'shop/page/access_denied.html', status=403)


    # 验证通过后继续渲染页面
    order_items = order.items.all()

    return render(request, 'shop/page/checkout_success.html', {
        'name': order.name,
        'grand_total': order.grand_total,
        'order': order,
        'order_items': order.items.all(),
    })


@require_POST
def remove_from_cart(request, item_id):
    session_key = request.session.session_key
    print(f"SESSION KEY: {session_key}")
    print(f"TRY DELETE ITEM_ID: {item_id}")
    try:
        item = CartItem.objects.get(id=item_id, session_key=session_key)
        print(f"FOUND ITEM, DELETING: {item}")
        item.delete()
    except CartItem.DoesNotExist:
        print("ITEM DOES NOT EXIST")

    return redirect('cart_view')


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    attributes = product.get_attributes()
    avg_rating = ProductRating.objects.filter(product=product).aggregate(avg=Avg('score'))['avg'] or 0

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

    return render(request, 'shop/page/product_detail.html', {
        'product': product,
        'average': round(avg_rating, 1),
        'attributes': attributes,
        'is_favorited': is_favorited,
    })


def attribute_list(request):
    attributes = Attribute.objects.all()
    return render(request, 'shop/page/attribute_list.html', {'attributes': attributes})


@require_http_methods(["GET", "POST"])
def rate_product(request, product_id):
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key

    if request.method == 'GET':
        product = get_object_or_404(Product, id=product_id)
        average = product.ratings.aggregate(avg=Avg("score"))["avg"] or 0
        # 查用户之前有没有评分
        try:
            rating = ProductRating.objects.get(product_id=product_id, session_key=session_key)
            user_score = rating.score
        except ProductRating.DoesNotExist:
            user_score = 0
        return JsonResponse({"average": round(average, 1), "user_score": user_score})

    # POST 打分逻辑（原样保留）
    score = int(request.POST.get("score"))

    rating, created = ProductRating.objects.get_or_create(
        product_id=product_id,
        session_key=session_key,
        defaults={"score": score, "created_at": now()}
    )

    if not created:
        rating.score = score
        rating.created_at = now()
        rating.save()

    product = Product.objects.get(id=product_id)
    average = product.ratings.aggregate(Avg("score"))["score__avg"]

    return JsonResponse({"average": round(average or 0, 1)})


@require_POST
@login_required
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if not created:
        favorite.delete()
        return JsonResponse({'favorited': False})
    else:
        return JsonResponse({'favorited': True})


@login_required
def favorites_list(request):
    favorite_products = request.user.profile.favorites.all()
    return render(request, "shop/page/favorites_list.html", {
        "favorite_products": favorite_products
    })


def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/page/order_detail.html', {
        'order': order,
    })


def get_attribute_values(request):
    attribute_id = request.GET.get('attribute_id')
    values = AttributeValue.objects.filter(attribute_id=attribute_id)
    data = [
        {'id': v.id, 'text': v.value}
        for v in values
    ]
    return JsonResponse(data, safe=False)


@require_POST
@csrf_exempt
def apply_coupon_api(request):
    import json
    data = json.loads(request.body)
    code = data.get("code")

    session_key = request.session.session_key
    if not session_key:
        request.session.save()
    cart_items = CartItem.objects.filter(session_key=session_key)

    total = sum(item.quantity * item.product.final_price for item in cart_items)

    discount = Decimal("0.00")
    grand_total = total

    if code:
        now_time = now()
        try:
            coupon = Coupon.objects.get(
                code__iexact=code,
                active=True,
                valid_from__lte=now_time,
                valid_to__gte=now_time
            )
            if coupon.discount_amount:
                discount = coupon.discount_amount
            elif coupon.discount_percent:
                discount = total * Decimal(coupon.discount_percent) / Decimal("100")

            grand_total = total - discount
            if grand_total < 0:
                grand_total = 0

            return JsonResponse({
                "success": True,
                "discount": float(discount),
                "grand_total": float(grand_total)
            })
        except Coupon.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Invalid coupon code."
            })
    else:
        return JsonResponse({
            "success": False,
            "message": "Please enter a coupon code."
        })


def download_invoice(request, order_id):
    from .models import Order, CompanyInfo

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return redirect('/')

    if order.session_key != request.session.session_key:
        return render(request, 'shop/page/access_denied.html', status=403)

    company = CompanyInfo.objects.first()

    # 创建内存缓冲
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # ✅ Logo 和公司名称
    if company and company.logo:
        logo_path = company.logo.path
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=40*mm, height=40*mm)
            elements.append(logo)
    company_name = company.name if company and company.name else "ModelVerse"
    elements.append(Paragraph(f"<b>{company_name}</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    invoice_number = f"INV-{order.id:06d}" 
    order_date = order.created_at.strftime("%d %b %Y, %I:%M %p") if order.created_at else now().strftime("%d %b %Y")

    # ✅ 发票标题与客户信息
    elements.append(Paragraph("<b>INVOICE</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>Invoice No:</b> {invoice_number}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Order Date:</b> {order_date}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Customer:</b> {order.name}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Email:</b> {order.email}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Address:</b> {order.address}", styles["Normal"]))
    elements.append(Paragraph(f"City: {order.city}", styles["Normal"]))
    elements.append(Paragraph(f"Country: {order.country}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # ✅ 商品明细表格
    data = [["Product", "Qty", "Price", "Subtotal"]]
    for item in order.items.all():
        data.append([
            item.product.name,
            str(item.quantity),
            f"RM {item.product.final_price:.2f}",
            f"RM {item.subtotal:.2f}"
        ])

    # ✅ 添加总额行
    data.append([
        "",
        "",
        Paragraph("<b>Total</b>", styles["Normal"]),
        Paragraph(f"<b>RM {order.grand_total:.2f}</b>", styles["Normal"])
    ])

    table = Table(data, colWidths=[70*mm, 20*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 24))

    # 页脚
    footer_text = f"Thank you for shopping with {company.name if company and company.name else 'Your Company'}!"

    if company:
        if company.address:
            footer_text += f"<br/>{company.address}"
        if company.email:
            footer_text += f"<br/>{company.email}"
        if company.contact:
            footer_text += f"<br/>{company.contact}"

        # 从 admin 数据取网站网址（有填才显示）
        if getattr(company, "website", None) and company.website.strip():
            footer_text += f"<br/><a href='{company.website}'>{company.website}</a>"

    elements.append(Paragraph(footer_text, styles["Normal"]))

    pdf.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"invoice_order_{order.id}.pdf")


def my_orders(request):
    session_key = request.session.session_key
    if not session_key:
        # 如果用户没有 session（例如没加购物车就访问）
        request.session.create()
        session_key = request.session.session_key

    orders = Order.objects.filter(session_key=session_key).order_by('-created_at')
    return render(request, 'shop/page/my_orders.html', {'orders': orders})


def terms_of_service_view(request):
    return render(request, 'shop/page/terms_of_service.html')


def privacy_policy_view(request):
    return render(request, 'shop/page/privacy_policy.html')


def company_profile_view(request):
    return render(request, 'shop/page/company_profile.html')


def about_us_view(request):
    return render(request, 'shop/page/about_us.html')


