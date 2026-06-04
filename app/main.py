from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.utils.security import get_current_user, require_admin
from app.routers import public, auth, admin, client, payments, search, technician, wallet, analytics
from app.config import settings

app = FastAPI(title="KasI GSM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

app.include_router(public.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(technician.router, prefix="/technician")
app.include_router(admin.router, prefix="/admin", dependencies=[Depends(require_admin)])
app.include_router(client.router)
app.include_router(payments.router, prefix="/payments")
app.include_router(wallet.router, prefix="/wallet")
app.include_router(search.router)
app.include_router(analytics.router, prefix="/admin/analytics", dependencies=[Depends(require_admin)])


@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden", "redirect_to_auth": True}
    )


@app.get("/health")
def health():
    return {"status": "ok"}
