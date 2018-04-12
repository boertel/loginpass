from authlib.client import OAuthClient


class OAuthBackend(OAuthClient):
    """Backend for OAuth Registry"""
    OAUTH_TYPE = None
    OAUTH_NAME = None
    OAUTH_CONFIG = None
    JWK_SET_URL = None

    def fetch_jwk_set(self, force=False):
        if not self.JWK_SET_URL:
            return None

        jwk_set = getattr(self, '_jwk_set', None)
        if jwk_set and not force:
            return jwk_set

        resp = self.get(self.JWK_SET_URL, withhold_token=True)
        self._jwk_set = resp.json()
        return self._jwk_set


def _get_oauth_client_cls(oauth):
    try:
        from authlib.flask.client import (
            OAuth as FlaskOAuth,
            RemoteApp as FlaskRemoteApp,
        )
        if isinstance(oauth, FlaskOAuth):
            return FlaskRemoteApp
    except ImportError:
        try:
            from authlib.django.client import (
                OAuth as DjangoOAuth,
                RemoteApp as DjangoRemoteApp,
            )
            if isinstance(oauth, DjangoOAuth):
                return DjangoRemoteApp
        except ImportError:
            pass


def register_to(backend, oauth, client_base=None):
    if client_base is None:
        client_base = _get_oauth_client_cls(oauth)

    config = backend.OAUTH_CONFIG.copy()
    if client_base:
        class RemoteApp(client_base, backend):
            pass
        config['client_cls'] = RemoteApp
    return oauth.register(backend.OAUTH_NAME, **config)


def create_flask_blueprint(backend, oauth, handle_authorize):
    from flask import Blueprint, url_for
    from authlib.flask.client import RemoteApp

    remote = register_to(backend, oauth, RemoteApp)
    bp = Blueprint('loginpass_' + backend.OAUTH_NAME, __name__)

    @bp.route('/auth')
    def auth():
        token = remote.authorize_access_token()
        if 'id_token' in token:
            user_info = remote.parse_openid(token)
        else:
            user_info = remote.profile()
        return handle_authorize(remote, token, user_info)

    @bp.route('/login')
    def login():
        redirect_uri = url_for('.auth', _external=True)
        return remote.authorize_redirect(redirect_uri)

    return bp