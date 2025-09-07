from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionContentPartParam


class OpenAIService():
    def __init__(self, openai_api_key: str, openai_embed_model: str,
                 openai_model: str, openai_image_model: str) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.embed_model = openai_embed_model
        self.chat_model = openai_model
        self.image_model = openai_image_model

    async def embed_text(self, text: str) -> list[float]:
        resp = await self.client.embeddings.create(model=self.embed_model, input=text)
        return list(resp.data[0].embedding)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = await self.client.embeddings.create(model=self.embed_model, input=texts)
        return [list(d.embedding) for d in resp.data]

    async def caption_images(self, image_urls: list[str], temperature: float = 0.0) -> str:
        if not image_urls:
            return ""
        content: list[ChatCompletionContentPartParam] = [{
            "type": "text",
            "text": (
                "Ты — эксперт по компьютерному зрению."
                "Проанализируй изображение и выдай максимально подробное описание."
                "Не упускай мелкие детали. Пиши конкретно и без абстракций."
                "Обязательно анализируй цифры и графики на изображении, если они есть, и добавляй их в описание."
                "Если что-то непонятно — делай логичное предположение и явно отмечай это."
            )
        }]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})
        messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": content}
        ]
        chat = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=temperature,
        )
        return chat.choices[0].message.content or ""

    async def generate_answer(self, question: str, contexts: list[str], temperature: float = 0.2) -> str:
        prompt = (
            "Ты — полезный ассистент. Отвечай на вопрос, используя ТОЛЬКО предоставленный контекст.\n\n" +
            "Контекст:\n" + "\n\n".join(contexts) + "\n\nВопрос: " + question + "\nОтвет:"
        )
        chat = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return chat.choices[0].message.content or ""

    async def generate_images(self, prompt: str) -> list[str | None]:
        img = await self.client.images.generate(model=self.image_model, prompt=prompt, size="1024x1024")
        return [d.url for d in img.data if getattr(d, "url", None)]

    @staticmethod
    def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - chunk_overlap
            if start < 0:
                start = 0
        return chunks
