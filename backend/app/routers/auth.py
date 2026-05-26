from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
import httpx
import secrets

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import UserRegister, UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Returns the current user if a valid token is provided, otherwise None."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Require authentication — raises 401 if not logged in."""
    user = get_current_user(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login with username and password."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(require_current_user)):
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(user)


# ── GitHub OAuth ──────────────────────────────────────────

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _github_redirect_uri() -> str:
    return f"{settings.BACKEND_URL.rstrip('/')}/auth/github/callback"


@router.get("/github/login")
def github_login():
    """Redirect user to GitHub OAuth consent page."""
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": _github_redirect_uri(),
        "scope": "user:email",
    }
    return RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback: exchange code for token, get user, issue JWT."""
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    gh_access_token = token_data.get("access_token")
    if not gh_access_token:
        raise HTTPException(status_code=400, detail="Failed to get GitHub access token")

    # Get GitHub user profile
    headers = {"Authorization": f"Bearer {gh_access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(GITHUB_USER_URL, headers=headers)
        gh_user = user_resp.json()

        # Get primary email
        emails_resp = await client.get(GITHUB_EMAILS_URL, headers=headers)
        gh_emails = emails_resp.json()

    gh_id = str(gh_user["id"])
    gh_username = gh_user.get("login", "")
    gh_email = next(
        (e["email"] for e in gh_emails if e.get("primary")),
        gh_user.get("email") or f"{gh_username}@github.oauth",
    )

    # Find or create user
    user = db.query(User).filter(User.oauth_provider == "github", User.oauth_id == gh_id).first()
    if not user:
        # Check if username/email already taken, make unique if needed
        username = gh_username
        if db.query(User).filter(User.username == username).first():
            username = f"{gh_username}_{secrets.token_hex(3)}"
        if db.query(User).filter(User.email == gh_email).first():
            # Link to existing account with same email
            user = db.query(User).filter(User.email == gh_email).first()
            user.oauth_provider = "github"
            user.oauth_id = gh_id
            db.commit()
            db.refresh(user)
        else:
            user = User(
                username=username,
                email=gh_email,
                oauth_provider="github",
                oauth_id=gh_id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token = create_access_token(user.id)
    user_json = UserResponse.model_validate(user).model_dump_json()

    # Redirect to frontend with token
    frontend_url = settings.FRONTEND_URL
    return RedirectResponse(
        f"{frontend_url}/auth/callback?token={token}&user={user_json}"
    )


# ── Google OAuth ──────────────────────────────────────────

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _google_redirect_uri() -> str:
    return f"{settings.BACKEND_URL.rstrip('/')}/auth/google/callback"


@router.get("/google/login")
def google_login():
    """Redirect user to Google OAuth consent page."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback: exchange code, fetch profile, issue JWT."""
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _google_redirect_uri(),
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(
                status_code=400,
                detail=f"Google token exchange failed: {token_resp.text[:300]}",
            )
        token_data = token_resp.json()

    g_access_token = token_data.get("access_token")
    if not g_access_token:
        raise HTTPException(status_code=400, detail="Failed to get Google access token")

    async with httpx.AsyncClient(timeout=15) as client:
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {g_access_token}"},
        )
        if user_resp.status_code >= 400:
            raise HTTPException(
                status_code=400,
                detail=f"Google userinfo failed: {user_resp.text[:300]}",
            )
        g_user = user_resp.json()

    g_id = str(g_user.get("sub") or "")
    g_email = g_user.get("email") or ""
    g_email_verified = bool(g_user.get("email_verified"))
    g_name = g_user.get("name") or ""
    if not g_id or not g_email:
        raise HTTPException(status_code=400, detail="Google profile missing id/email")

    # Find or create user
    user = (
        db.query(User)
        .filter(User.oauth_provider == "google", User.oauth_id == g_id)
        .first()
    )
    if not user:
        # Build a username candidate from email local-part or display name.
        base_username = (
            g_email.split("@", 1)[0]
            or "".join(ch for ch in g_name.lower() if ch.isalnum())
            or "google_user"
        )[:40] or "google_user"
        username = base_username
        if db.query(User).filter(User.username == username).first():
            username = f"{base_username}_{secrets.token_hex(3)}"

        existing_by_email = db.query(User).filter(User.email == g_email).first()
        if existing_by_email and g_email_verified:
            # Link Google account to the existing local account with same verified email.
            existing_by_email.oauth_provider = "google"
            existing_by_email.oauth_id = g_id
            db.commit()
            db.refresh(existing_by_email)
            user = existing_by_email
        elif existing_by_email and not g_email_verified:
            raise HTTPException(
                status_code=409,
                detail="An account with this email exists but the Google email is not verified.",
            )
        else:
            user = User(
                username=username,
                email=g_email,
                oauth_provider="google",
                oauth_id=g_id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token = create_access_token(user.id)
    user_json = UserResponse.model_validate(user).model_dump_json()
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(
        f"{frontend_url}/auth/callback?token={token}&user={user_json}"
    )
