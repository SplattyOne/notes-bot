import asyncio

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionContentPartParam

from config.settings import OpenaiSettings
from utils.limits import limit_concurrency


class OpenAIService():
    def __init__(self, settings: OpenaiSettings) -> None:
        self._settings = settings
        self.client = AsyncOpenAI(api_key=self._settings.api_key)
        self._semaphore = asyncio.Semaphore(self._settings.max_concurrent_requests)

    @limit_concurrency
    async def embed_text(self, text: str) -> list[float]:
        resp = await self.client.embeddings.create(model=self._settings.embed_model, input=text)
        return list(resp.data[0].embedding)

    @limit_concurrency
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = await self.client.embeddings.create(model=self._settings.embed_model, input=texts)
        return [list(d.embedding) for d in resp.data]

    @limit_concurrency
    async def caption_images(self, image_urls: list[str], temperature: float = 0.0) -> str:
        if not image_urls:
            return ""
        content: list[ChatCompletionContentPartParam] = [{
            "type": "text",
            "text": (
                "Ты — эксперт по компьютерному зрению.\n"
                "Проанализируй изображение и выдай максимально подробное описание.\n"
                "Не упускай мелкие детали. Пиши конкретно и без абстракций.\n"
                "Обязательно анализируй цифры и графики на изображении, если они есть, и добавляй их в описание.\n"
                "Если что-то непонятно — делай логичное предположение и явно отмечай это.\n"
            )
        }]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": content}
        ]
        chat = await self.client.chat.completions.create(
            model=self._settings.main_model,
            messages=messages,
            temperature=temperature,
        )
        return chat.choices[0].message.content or ""

    @limit_concurrency
    async def generate_answer(self, question: str, contexts: list[str], temperature: float = 0.2) -> str:
        prompt = (
            "Ты — полезный ассистент. Отвечай на вопрос, используя ТОЛЬКО предоставленный контекст.\n\n" +
            "Контекст:\n" + "\n\n".join(contexts) + "\n\nВопрос: " + question + "\nОтвет:"
        )
        chat = await self.client.chat.completions.create(
            model=self._settings.main_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return chat.choices[0].message.content or ""

    @limit_concurrency
    async def generate_images(self, prompt: str) -> list[str | None]:
        img = await self.client.images.generate(model=self._settings.image_model, prompt=prompt, size="1024x1024")
        return [d.url for d in img.data if getattr(d, "url", None)]

    def chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self._settings.chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - self._settings.chunk_overlap
            if start < 0:
                start = 0
        return chunks
