"""AI Client service for real LLM calls with provider fallback"""
import os
import json
import httpx
from typing import Optional, List
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.settings import AppSettings


@dataclass
class AIProvider:
    id: str
    provider: str
    model: str
    key_env: str
    enabled: bool
    priority: int


@dataclass
class AIResponse:
    content: str
    tokens_used: int
    model_used: str
    provider_id: str


class AIClientError(Exception):
    """Raised when all providers fail"""
    def __init__(self, message: str, errors: List[dict]):
        super().__init__(message)
        self.errors = errors


class AIClient:
    """Client for calling LLM providers with fallback support"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._providers_cache: Optional[List[AIProvider]] = None

    async def _get_providers_from_db(self) -> List[AIProvider]:
        """Get providers from database settings"""
        result = await self.db.execute(select(AppSettings).where(AppSettings.id == 1))
        settings = result.scalar_one_or_none()

        if not settings:
            # Return default Nvidia provider if configured in env
            nvidia_key = os.getenv("NVIDIA_API_KEY")
            if nvidia_key:
                return [
                    AIProvider(
                        id="nvidia-nim-1",
                        provider="nvidia",
                        model="nvidia/nemotron-3-ultra-550b-a55b",
                        key_env="NVIDIA_API_KEY",
                        enabled=True,
                        priority=1,
                    )
                ]
            return []

        providers_data = json.loads(settings.ai_providers)
        providers = []
        for p in providers_data:
            if p.get("enabled"):
                providers.append(AIProvider(
                    id=p["id"],
                    provider=p["provider"],
                    model=p["model"],
                    key_env=p["key_env"],
                    enabled=p["enabled"],
                    priority=p["priority"],
                ))
        return sorted(providers, key=lambda p: p.priority)

    async def get_providers(self) -> List[AIProvider]:
        """Get enabled providers sorted by priority"""
        if self._providers_cache is None:
            self._providers_cache = await self._get_providers_from_db()
        return self._providers_cache

    async def _call_nvidia(self, provider: AIProvider, messages: List[dict],
                          temperature: float, max_tokens: int) -> AIResponse:
        """Call Nvidia NIM API"""
        api_key = os.getenv(provider.key_env)
        if not api_key:
            raise ValueError(f"API key not found in env: {provider.key_env}")

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Explicitly configure proxy to avoid httpx's buggy trust_env parsing of no_proxy (e.g., IPv6 ::1 with brackets)
        proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        async with httpx.AsyncClient(timeout=120.0, proxy=proxy_url, trust_env=False, verify=False) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content and token usage
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            return AIResponse(
                content=content,
                tokens_used=tokens_used,
                model_used=provider.model,
                provider_id=provider.id,
            )

    async def generate(self, messages: List[dict],
                      temperature: float = 0.7, max_tokens: int = 4000) -> AIResponse:
        """Generate content using providers with fallback"""
        providers = await self.get_providers()
        if not providers:
            raise AIClientError("No AI providers configured", [])

        errors = []
        for provider in providers:
            try:
                if provider.provider == "nvidia":
                    return await self._call_nvidia(provider, messages, temperature, max_tokens)
                else:
                    errors.append({"provider": provider.id, "error": f"Unknown provider: {provider.provider}"})
                    continue
            except httpx.HTTPStatusError as e:
                errors.append({"provider": provider.id, "error": f"HTTP {e.response.status_code}: {e.response.text}"})
                # Continue to next provider on 429, 5xx, or quota errors
                if e.response.status_code in (429, 500, 502, 503, 504):
                    continue
                # For 401 (unauthorized), treat as provider failure and fallback
                if e.response.status_code == 401:
                    continue
                # For other errors (403, etc.), don't fallback
                raise
            except Exception as e:
                errors.append({"provider": provider.id, "error": str(e)})
                # Continue to next provider on network/timeout errors
                continue

        # All providers failed
        raise AIClientError("All AI providers failed", errors)


async def get_ai_client(db: AsyncSession) -> AIClient:
    """Get AI client instance with database session"""
    return AIClient(db)