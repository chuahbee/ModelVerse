from .models import CompanyInfo, MenuItem, FooterLink

def company_info(request):
    return {
        'company_info': CompanyInfo.objects.first()
    }

def menu_items(request):
    return {
        'menu_items': MenuItem.objects.filter(visible=True)
    }

def footer_links(request):
    return {
        'footer_links': FooterLink.objects.filter(visible=True).order_by('order')
    }