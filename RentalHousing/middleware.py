from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

class CsrfBypassForApi(MiddlewareMixin):
    """
    Middleware, disabling CSRF validation for API routes.
    """
    def process_request(self, request: HttpRequest) -> None:
        """
        If the requested path starts with `/api/`, skip CSRF validation.
        """
        if request.path.startswith(("/api/", )):
            setattr(request, "_dont_enforce_csrf_checks", True)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware that injects `Authorization: Bearer <access>` header from httpOnly cookies.

    Flow:
        1. Read `access_token` and `refresh_token` from request cookies.
        2. If `access_token` present:
            - Try to parse it via `AccessToken(...)`;
            - If not expired -> put it into `request.META["HTTP_AUTHORIZATION"]`.
            - If expired -> try to mint a new access token from `refresh_token` (if valid).
              On success, store it in `request._new_access_token` and also proxy as `Authorization` header.
              On failure -> clear cookies (so the client can re-authenticate).
        3. If no `access_token` but `refresh_token` present -> try to mint a new access token.
        4. In `process_response`, if `_new_access_token` was minted, set it into httpOnly cookie.
    """
    def process_request(self, request: HttpRequest) -> None:
        """
        Inspect incoming cookies, validate or refresh JWT, and set `Authorization` header if possible.
        """
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')
        if access_token:
            try:
                token = AccessToken(access_token)
                # token['exp'] is a UNIX timestamp (UTC). `fromtimestamp` uses local time.
                if datetime.fromtimestamp(token['exp']) < datetime.now():
                    raise TokenError('Token expired')

                # Valid access token -> proxy to DRF as Authorization header
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
            except TokenError:
                # Try refresh if we have refresh_token
                new_access_token = self.refresh_access_token(refresh_token)
                if new_access_token:
                    request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                    request._new_access_token = new_access_token
                else:
                    # Refresh failed -> mark cookies for clearing
                    self.clear_cookies(request)
        elif refresh_token:
            # No access token, try to mint a new one from refresh
            new_access_token = self.refresh_access_token(refresh_token)
            if new_access_token:
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                request._new_access_token = new_access_token
            else:
                self.clear_cookies(request)

    def refresh_access_token(self, refresh_token):
        """
        Attempt to create a new access token from a given refresh token.
        """
        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            return new_access_token
        except TokenError:
            return

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        If 'process_request' minted a new access token, persist it as httpOnly cookie in the response.
        """
        new_access_token = getattr(request, '_new_access_token', None)
        if new_access_token:
            access_expiry = AccessToken(new_access_token)['exp']
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                expires=datetime.fromtimestamp(access_expiry)
            )
        return response

    def clear_cookies(self, request: HttpRequest) -> None:
        """
        Mark auth cookies for deletion (or clear local request snapshot).
        """
        request.COOKIES.pop('access_token', None)
        request.COOKIES.pop('refresh_token', None)
