import base64
from pathlib import Path

from openai import OpenAI

from .config import Settings
from .prompts import (
    CONTENT_USER_TEMPLATE,
    PHOTO_ANALYSIS_PROMPT,
    PLAN_TEMPLATE,
    REVISION_TEMPLATE,
    SYSTEM_PROMPT,
)
from .storage import UserProfile


class OpenAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.ai_provider.lower().strip()
        if self.provider == "groq":
            self.client = self._build_groq_client()
        elif self.provider == "openai":
            self.client = self._build_openai_client()
        else:
            raise ValueError("AI_PROVIDER must be 'groq' or 'openai'.")

    def _build_groq_client(self) -> OpenAI:
        if not self.settings.groq_api_key or self.settings.groq_api_key == "replace_me":
            raise ValueError("Set GROQ_API_KEY in .env to use AI_PROVIDER=groq.")
        return OpenAI(
            api_key=self.settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    def _build_openai_client(self) -> OpenAI:
        if not self.settings.openai_api_key or self.settings.openai_api_key == "replace_me":
            raise ValueError("Set OPENAI_API_KEY in .env to use AI_PROVIDER=openai.")
        return OpenAI(api_key=self.settings.openai_api_key)

    async def transcribe(self, audio_path: Path) -> str:
        with audio_path.open("rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model=self._transcribe_model,
                file=audio_file,
            )
        return result.text.strip()

    async def generate_content(
        self,
        profile: UserProfile,
        source_text: str,
        photo_context: str | None = None,
    ) -> str:
        prompt = CONTENT_USER_TEMPLATE.format(
            niche=profile.niche,
            tone=profile.tone,
            style=profile.style,
            source_text=source_text,
            photo_context=photo_context or "Фото не приложены. Предложи AI-визуал.",
        )
        return self._text_response(prompt)

    async def revise_content(self, profile: UserProfile, last_result: str, instruction: str) -> str:
        prompt = REVISION_TEMPLATE.format(
            niche=profile.niche,
            tone=profile.tone,
            style=profile.style,
            last_result=last_result,
            instruction=instruction,
        )
        return self._text_response(prompt)

    async def generate_plan(self, profile: UserProfile, period: str, context: str | None = None) -> str:
        prompt = PLAN_TEMPLATE.format(
            niche=profile.niche,
            tone=profile.tone,
            style=profile.style,
            period=period,
            context=context or "Истории пока мало. Предложи универсальный план для ниши.",
        )
        return self._text_response(prompt)

    async def analyze_photo(self, image_path: Path) -> str:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        if self.provider == "groq":
            response = self.client.chat.completions.create(
                model=self.settings.groq_vision_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PHOTO_ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                            },
                        ],
                    },
                ],
            )
            return response.choices[0].message.content.strip()

        response = self.client.responses.create(
            model=self.settings.openai_text_model,
            instructions=SYSTEM_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PHOTO_ANALYSIS_PROMPT},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }
            ],
        )
        return response.output_text.strip()

    async def generate_image(self, prompt: str) -> bytes | None:
        if not self.settings.openai_enable_image_generation:
            return None

        response = self.client.images.generate(
            model=self.settings.openai_image_model,
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        image_b64 = response.data[0].b64_json
        if not image_b64:
            return None
        return base64.b64decode(image_b64)

    def _text_response(self, prompt: str) -> str:
        if self.provider == "groq":
            response = self.client.chat.completions.create(
                model=self.settings.groq_text_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()

        response = self.client.responses.create(
            model=self.settings.openai_text_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )
        return response.output_text.strip()

    @property
    def _transcribe_model(self) -> str:
        if self.provider == "groq":
            return self.settings.groq_transcribe_model
        return self.settings.openai_transcribe_model
