from django.utils.deprecation import MiddlewareMixin
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

class CsrfBypassForApi(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith(("/api/", )):
            setattr(request, "_dont_enforce_csrf_checks", True)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')
        if access_token:
            try:
                token = AccessToken(access_token)
                if datetime.fromtimestamp(token['exp']) < datetime.now():
                    raise TokenError('Token expired')
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
            except TokenError:
                # Попробовать обновить access токен, если refresh токен не истек
                new_access_token = self.refresh_access_token(refresh_token)
                if new_access_token:
                    request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                    request._new_access_token = new_access_token
                else:
                    # Удалить токены из куки, если обновление не удалось
                    self.clear_cookies(request)
        elif refresh_token:
            new_access_token = self.refresh_access_token(refresh_token)
            if new_access_token:
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                request._new_access_token = new_access_token
            else:
                self.clear_cookies(request)

    def refresh_access_token(self, refresh_token):
        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            return new_access_token
        except TokenError:
            return

    def process_response(self, request, response):
        new_access_token = getattr(request, '_new_access_token', None)
        if new_access_token:
            access_expiry = AccessToken(new_access_token)['exp']
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=False,  # Используйте True для HTTPS
                samesite='Lax',
                expires=datetime.fromtimestamp(access_expiry)
            )
        return response

    def clear_cookies(self, request):
        # Метод для удаления истекших куки
        request.COOKIES.pop('access_token', None)
        request.COOKIES.pop('refresh_token', None)
