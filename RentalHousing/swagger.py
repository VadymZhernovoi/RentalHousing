from drf_yasg import openapi

swagger_info = openapi.Info(
    title="RentalHousing API",
    default_version="v1",
    description="Backend for rental housing service",
    terms_of_service="https://example.com/terms/",
    contact=openapi.Contact(                 # ← автор/контакты
        name="Vadym Zhernovoi",
        email="you@example.com",
        url="https://your-site-or-github"
    ),
    license=openapi.License(name="BSD-3-Clause"),
)