from rest_framework.exceptions import NotFound
from .models import Business


def get_business_or_404(random_code):
    business = Business.objects.filter(random_code=random_code, is_active=True).first()
    if not business:
        raise NotFound("آرایشگاهی با این کد یافت نشد.")
    return business