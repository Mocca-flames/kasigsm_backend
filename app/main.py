from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.utils.security import get_current_user, require_admin
from app.routers import public, auth, admin, client, payments, search, technician

app = FastAPI(title="KasI GSM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(technician.router, prefix="/technician")
app.include_router(admin.router, prefix="/admin", dependencies=[Depends(require_admin)])
app.include_router(client.router)
app.include_router(payments.router, prefix="/payments")
app.include_router(search.router)


@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden", "redirect_to_auth": True}
    )


@app.get("/health")
def health():
    return {"status": "ok"}