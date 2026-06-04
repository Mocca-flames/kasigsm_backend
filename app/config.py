from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://kasi:kasi@localhost:5432/kasigsm"
    SECRET_KEY: str = "change-me-in-production-abc123xyz"
    JWT_EXPIRE_MINUTES: int = 1440
    ENCRYPTION_KEY: str = "change-me-to-a-32-byte-hex-string"
    PAYSTACK_SECRET_KEY: str = "sk_test_566a7b362057bc2ca80df97ec482290d60180ea4"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_eb846621ad62bc7df0027794c88969c04f075b06"
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    PAYSTACK_CALLBACK_URL: str = "http://localhost:3000/payment/callback"
    PAYFAST_MERCHANT_ID: str = ""
    PAYFAST_MERCHANT_KEY: str = ""
    USD_TO_ZAR_RATE: float = 16.5
    MEDIA_ROOT: str = "media"
    MEDIA_PUBLIC_URL: str = "/media"
    ALLOWED_EXTENSIONS: set[str] = {"png", "jpg", "jpeg", "webp", "gif"}
    CORS_ALLOW_ALL: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5174",
    ]
    CORS_ALLOW_NGROK: bool = True
    CORS_NGROK_PATTERNS: list[str] = []
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_user: str = ""
    brevo_smtp_password: str = ""
    brevo_sender_email: str = "noreply@yourdomain.com"
    brevo_sender_name: str = "KasI GSM"

    def get_cors_origins(self) -> list[str]:
        if self.CORS_ALLOW_ALL or self.CORS_ALLOW_NGROK:
            return ["*"]
        return list(self.CORS_ORIGINS)

    # Rate limiting defaults
    AUTH_RATE_LIMIT: int = 5
    OTP_RATE_LIMIT: int = 3
    RATE_WINDOW_SECONDS: int = 900
    LOGIN_LOCKOUT_AFTER: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 900

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
