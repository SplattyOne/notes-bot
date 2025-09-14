from typing import Iterable
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from config.settings import QdrantSettings
from models.vector import PageChunk


class QdrantVectorStore():
    def __init__(self, settings: QdrantSettings) -> None:
        self._settings = settings
        self.client = AsyncQdrantClient(url=self._settings.url)
        self.collection = self._settings.collection
        self.vector_size = 3072  # text-embedding-3-large

    async def ensure_collection(self) -> None:
        collections = await self.client.get_collections()
        if not any(c.name == self.collection for c in collections.collections):
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.vector_size, distance=qm.Distance.COSINE),
            )

    async def upsert(self, chunks: Iterable[PageChunk]) -> None:
        points = []
        for ch in chunks:
            if ch.vector is None:
                raise ValueError("Chunk missing vector")
            points.append(
                qm.PointStruct(
                    id=ch.id,
                    vector=ch.vector,
                    payload={
                        "page_id": ch.page_id,
                        "title": ch.title,
                        "text": ch.text,
                        "image_urls": ch.image_urls,
                        "last_edited_time": ch.last_edited_time,
                        **ch.metadata,
                    },
                )
            )
        await self.client.upsert(collection_name=self.collection, points=points)

    async def search(self, vector: list[float], limit: int) -> list[tuple[PageChunk, float]]:
        res = await self.client.search(collection_name=self.collection, query_vector=vector, limit=limit)
        items: list[tuple[PageChunk, float]] = []
        for p in res:
            pl = p.payload or {}
            items.append(
                (PageChunk(
                    id=str(p.id),
                    page_id=str(pl.get("page_id", "")),
                    title=str(pl.get("title", "")),
                    text=str(pl.get("text", "")),
                    image_urls=list(pl.get("image_urls", []) or []),
                    last_edited_time=str(pl.get("last_edited_time", "")),
                    metadata={k: v for k, v in pl.items() if k not in {
                        "page_id", "title", "text", "image_urls", "last_edited_time"}},
                ), float(p.score))
            )
        return items

    async def delete_by_page_id(self, page_id: str) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="page_id",
                            match=qm.MatchValue(value=page_id)
                        )
                    ]
                )
            )
        )

    @staticmethod
    def get_stable_id(s: str) -> str:
        # Deterministic UUIDv5 acceptable by Qdrant
        return str(uuid.uuid5(uuid.NAMESPACE_URL, s))
