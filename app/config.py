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
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    USD_TO_ZAR_RATE: float = 16.5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()