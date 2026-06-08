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
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_path: Path) -> str:
        with audio_path.open("rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model=self.settings.openai_transcribe_model,
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
        response = self.client.responses.create(
            model=self.settings.openai_text_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )
        return response.output_text.strip()
