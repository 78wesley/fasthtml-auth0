from fasthtml.common import *
from dotenv import load_dotenv
from urllib.parse import urlencode, quote_plus
from auth0.authentication import GetToken, Users
from auth0.management import Auth0
import time
from cachetools import TTLCache
from threading import Lock
import os
import secrets
import jwt
import requests

load_dotenv()

AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")

for var in ["AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET", "AUTH0_DOMAIN", "AUTH0_CALLBACK_URL", "AUTH0_AUDIENCE"]:
    if not os.getenv(var):
        raise EnvironmentError(f"{var} is missing.")


OIDC_CONFIG_URL = f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration"
OIDC_CONFIG = requests.get(OIDC_CONFIG_URL).json()
AUTHORIZATION_ENDPOINT = OIDC_CONFIG["authorization_endpoint"]
TOKEN_ENDPOINT = OIDC_CONFIG["token_endpoint"]
USERINFO_ENDPOINT = OIDC_CONFIG["userinfo_endpoint"]
LOGOUT_ENDPOINT = OIDC_CONFIG["end_session_endpoint"]

ACTIVE_SESSIONS = []

_token_cache = {}
_token_lock = Lock()


def get_management_token() -> str:
    """
    Returns a cached Auth0 Management API token.
    Refreshes if expired.
    Thread-safe.
    """
    with _token_lock:
        token_info = _token_cache.get("token")

        # Check if token is still valid
        if token_info and token_info["expires_at"] > time.time():
            return token_info["access_token"]

        # Get a new token
        get_token = GetToken(AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET)
        token = get_token.client_credentials(audience=AUTH0_AUDIENCE)
        access_token = token["access_token"]
        expires_in = token.get("expires_in", 3600)  # default to 1 hour if not provided

        _token_cache["token"] = {"access_token": access_token, "expires_at": time.time() + expires_in - 60}  # subtract 60s buffer

        return access_token


def is_user_blocked(user_id: str) -> bool:
    auth0 = Auth0(AUTH0_DOMAIN, get_management_token())
    user = auth0.users.get(user_id)
    return user.get("blocked", False)


def before(request, session: dict):
    print("\033[93m[Beforeware triggered]\033[0m for request:", request.url)

    session_id = session.get("session_id")
    auth = session.get("auth")

    if not session_id or not auth:
        session.clear()
        return Redirect("/?error=session&error_description=session is not found")

    if session_id not in ACTIVE_SESSIONS:
        session.clear()
        return Redirect("/?error=session&error_description=session is not found")

    access_token = auth.get("access_token", "")
    token_data: dict = jwt.decode(access_token, options={"verify_signature": False})
    if token_data.get("exp") and time.time() >= token_data["exp"]:
        session.clear()
        return Redirect("/?error=expired&error_description=authorization is expired")

    user_id = token_data.get("sub")
    if is_user_blocked(user_id):
        session.clear()
        if session_id in ACTIVE_SESSIONS:
            ACTIVE_SESSIONS.remove(session_id)
        return Redirect("/?error=unauthorized&error_description=user is blocked")


hdrs = (
    Link(rel="icon", type="image/x-ico", href="/favicon/dark.ico", media="(prefers-color-scheme: dark)"),
    Link(rel="icon", type="image/x-ico", href="/favicon/light.ico", media="(prefers-color-scheme: light)"),
    Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"),
    Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.colors.css"),
    Style(":root { --pico-font-size: 100%; }"),
)
SKIP_AUTH_LIST = [r".*\\.css", r".*\\.js", "/", "/login", "/logout", "/callback", r"/favicon/.*"]

app = FastHTML(before=Beforeware(before, skip=SKIP_AUTH_LIST), hdrs=hdrs, default_hdrs=False)
route = app.route


@app.route("/{filepath:path}/{fname:path}.{ext:static}")
async def static_files(filepath: str, fname: str, ext: str):
    return FileResponse(f"fh_app/static/{filepath}/{fname}.{ext}")


@route("/")
def index(request, session, error: str = "", error_description: str = ""):
    auth = session.get("auth")
    if auth:
        return Redirect("/dashboard")
    content = [Div(H1("Welcome to FastHTML with Auth0"), A("Login", role="button", href="/login"))]
    if error:
        content.insert(0, Card(error.capitalize(), ": ", error_description.capitalize(), cls="pico-background-red-500"))
    return Titled("Home", *content)


@route("/dashboard")
def dashboard(request, session):
    auth = session.get("auth", {})
    user = auth.get("userinfo", {})
    return Titled(
        "Dashboard",
        H1(f"Welcome, {user['name']}!"),
        P(f"Session Id: {session.get('session_id')}"),
        P(f"User Id: {user['sub']}"),
        Div(
            A("Active Sessions", type="button", href="/active-sessions"),
            A("User Info", type="button", href="/userinfo"),
            A("Logout", type="button", href="/logout", cls="secondary"),
            cls="grid",
        ),
    )


@route("/active-sessions")
def active_sessions(request):
    return Titled("Active Sessions Id's", Div(Ul(*[Li(session) for session in ACTIVE_SESSIONS])))


@route("/userinfo")
def userinfo(request, session):
    access_token = session.get("auth", {}).get("access_token", "")
    user_info = Users(AUTH0_DOMAIN).userinfo(access_token)
    if user_info.get("blocked"):
        session.clear()
        Redirect("/?error=UserBlocked")
    return Titled("User Info", Div(Textarea(str(user_info), readonly=True, rows=10)))


@route("/login")
def login(request):
    params = {
        "client_id": AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": AUTH0_CALLBACK_URL,
        "scope": "openid profile email",
        "audience": AUTH0_AUDIENCE,
    }
    url = AUTHORIZATION_ENDPOINT + "?" + urlencode(params, quote_via=quote_plus)
    return RedirectResponse(url)


@route("/callback")
def callback(request, session, code: str = "", state: str = "", error: str = "", error_description: str = ""):
    if error:
        return Redirect(f"/?error={error}&error_description={error_description}")

    token = GetToken(AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET).authorization_code(code=code, redirect_uri=AUTH0_CALLBACK_URL)
    access_token = token["access_token"]
    id_token = token.get("id_token")
    user_info = Users(AUTH0_DOMAIN).userinfo(access_token)
    session_id = secrets.token_urlsafe(32)
    session["session_id"] = session_id
    session["auth"] = {
        "access_token": access_token,
        "id_token": id_token,
        "userinfo": user_info,
    }
    ACTIVE_SESSIONS.append(session_id)
    return RedirectResponse("/dashboard")


@route("/logout")
def logout(request, session):
    session_id = session.get("session_id", "")
    session_auth = session.get("auth", {})
    id_token = session_auth.get("id_token", "")
    session.clear()
    if session_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(session_id)

    logout_url = LOGOUT_ENDPOINT + "?" + urlencode({"client_id": AUTH0_CLIENT_ID, "post_logout_redirect_uri": f"http://{request.url.netloc}/", "id_token_hint": id_token})
    return RedirectResponse(logout_url)


serve()
