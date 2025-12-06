import secrets
from typing import List, Optional, Type, TypeVar
from urllib.parse import urlparse

from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from starlette.middleware.sessions import SessionMiddleware
from supabase import Client, create_client

load_dotenv()


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    consentkeys_client_id: Optional[str] = Field(None, alias="CONSENTKEYS_CLIENT_ID")
    consentkeys_client_secret: Optional[str] = Field(
        None, alias="CONSENTKEYS_CLIENT_SECRET"
    )
    consentkeys_issuer: str = Field("https://consentkeys.com", alias="CONSENTKEYS_ISSUER")
    consentkeys_redirect_path: str = Field(
        "https://meritboard.vercel.app/auth/callback",
        alias="CONSENTKEYS_REDIRECT_PATH",
    )
    app_host: str = Field("https://meritboard.vercel.app", alias="APP_HOST")
    session_secret: str = Field(default_factory=lambda: secrets.token_hex(32), alias="SESSION_SECRET")
    supabase_url: Optional[str] = Field(None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(
        None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    supabase_jobs_table: str = Field("jobs", alias="SUPABASE_JOBS_TABLE")
    supabase_candidates_table: str = Field(
        "candidates", alias="SUPABASE_CANDIDATES_TABLE"
    )
    
    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def redirect_uri(self) -> str:
        if self.consentkeys_redirect_path.startswith("http"):
            return self.consentkeys_redirect_path
        return f"{self.app_host}{self.consentkeys_redirect_path}"

    @property
    def redirect_route_path(self) -> str:
        """Ensure the callback route is always a valid path for FastAPI."""

        if self.consentkeys_redirect_path.startswith("http"):
            parsed = urlparse(self.consentkeys_redirect_path)
            return parsed.path or "/auth/callback"

        if not self.consentkeys_redirect_path.startswith("/"):
            return f"/{self.consentkeys_redirect_path}"
        return self.consentkeys_redirect_path

    def require_consentkeys_credentials(self) -> None:
        if not self.consentkeys_client_id or not self.consentkeys_client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ConsentKeys client configuration is missing. Set CONSENTKEYS_CLIENT_ID and CONSENTKEYS_CLIENT_SECRET.",
            )


settings = Settings()

app = FastAPI(title="MeritBoard", description="Meritocratic job board with ConsentKeys OIDC")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.app_host.startswith("https"),
)

templates = Jinja2Templates(directory="templates")

oauth = OAuth()
supabase_client: Optional[Client] = None


def ensure_consentkeys_client() -> None:
    """Ensure the ConsentKeys OAuth client is registered with valid credentials."""

    settings.require_consentkeys_credentials()
    if not hasattr(oauth, 'consentkeys'):
        oauth.register(
            name="consentkeys",
            server_metadata_url=f"{settings.consentkeys_issuer}/.well-known/openid-configuration",
            client_id=settings.consentkeys_client_id,
            client_secret=settings.consentkeys_client_secret,
            client_kwargs={"scope": "openid profile email"},
        )


def ensure_supabase_client() -> Client:
    """Initialize a Supabase client when credentials are provided."""

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Supabase configuration is missing. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            ),
        )

    global supabase_client
    if supabase_client is None:
        supabase_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return supabase_client


class CandidateProfile(BaseModel):
    id: str = Field(default_factory=lambda: secrets.token_hex(8))
    region: str
    skills: List[str]
    experience_years: float = Field(ge=0)
    desired_roles: List[str]
    portfolio_link: Optional[str] = None


class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: secrets.token_hex(8))
    employer: str
    title: str
    region: str
    description: str
    incentive_eligible: bool = False


T = TypeVar("T", bound=BaseModel)


def fetch_records(table: str, model: Type[T]) -> List[T]:
    client = ensure_supabase_client()
    response = client.table(table).select("*").execute()
    if response.error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase error: {getattr(response.error, 'message', response.error)}",
        )
    return [model(**row) for row in response.data or []]


def insert_record(table: str, record: T, model: Type[T]) -> T:
    client = ensure_supabase_client()
    response = client.table(table).insert(record.dict()).execute()
    if response.error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase error: {getattr(response.error, 'message', response.error)}",
        )
    payload = response.data[0] if response.data else record.dict()
    return model(**payload)


def demo_jobs() -> List[JobPosting]:
    return [
        JobPosting(
            employer="Pacific Inclusive Partners",
            title="Data Analyst",
            region="Lower Mainland",
            description="Advance evidence-based hiring programs for WorkBC with Python and SQL.",
            incentive_eligible=True,
        ),
        JobPosting(
            employer="Northern Tech Co-op",
            title="Full Stack Developer",
            region="Cariboo",
            description="Ship accessible services for WorkBC participants across BC regions.",
            incentive_eligible=False,
        ),
    ]


def demo_candidates() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            region="Vancouver Island",
            skills=["React", "TypeScript", "Figma"],
            experience_years=3,
            desired_roles=["Frontend Developer", "Product Designer"],
            portfolio_link="https://example.com/portfolio",
        ),
        CandidateProfile(
            region="Kootenays",
            skills=["Python", "FastAPI", "Supabase"],
            experience_years=5,
            desired_roles=["Backend Developer", "Data Engineer"],
        ),
    ]


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "consentkeys_configured": bool(
            settings.consentkeys_client_id and settings.consentkeys_client_secret
        ),
        "supabase_configured": bool(
            settings.supabase_url and settings.supabase_service_role_key
        ),
    }


async def get_current_user(request: Request) -> Optional[dict]:
    return request.session.get("user")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: Optional[dict] = Depends(get_current_user)):
    try:
        jobs = fetch_records(settings.supabase_jobs_table, JobPosting)
        candidates = fetch_records(settings.supabase_candidates_table, CandidateProfile)
    except Exception as exc:
        # Fall back to demo data if Supabase is not configured or has errors
        jobs = demo_jobs()
        candidates = demo_candidates()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "jobs": jobs,
            "candidates": candidates,
        },
    )


@app.get("/login")
async def login(request: Request):
    try:
        ensure_consentkeys_client()
        return await oauth.consentkeys.authorize_redirect(request, settings.redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@app.get(settings.redirect_route_path)
async def auth_callback(request: Request):
    ensure_consentkeys_client()
    try:
        token = await oauth.consentkeys.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_info = token.get("userinfo")
    if not user_info:
        user_info = await oauth.consentkeys.parse_id_token(request, token)

    request.session["user"] = {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
    }
    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/api/jobs", response_model=List[JobPosting])
async def list_jobs():
    return fetch_records(settings.supabase_jobs_table, JobPosting)


@app.post("/api/jobs", response_model=JobPosting, status_code=status.HTTP_201_CREATED)
async def create_job(job: JobPosting, user: Optional[dict] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required to post jobs")
    return insert_record(settings.supabase_jobs_table, job, JobPosting)


@app.get("/api/candidates", response_model=List[CandidateProfile])
async def list_candidates():
    return fetch_records(settings.supabase_candidates_table, CandidateProfile)


@app.post("/api/candidates", response_model=CandidateProfile, status_code=status.HTTP_201_CREATED)
async def create_candidate(profile: CandidateProfile):
    return insert_record(settings.supabase_candidates_table, profile, CandidateProfile)
