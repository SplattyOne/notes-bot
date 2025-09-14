import logging
import typing
import uuid

from models.vector import PageChunk

logger = logging.getLogger(__name__)


class MessageServiceProtocol(typing.Protocol):
    async def handle_messages(
        self,
        callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, None]]
    ) -> None:
        ...

    async def handle_notes_request(
        self,
        callback: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, str]]
    ) -> None:
        ...


class NotesServiceProtocol(typing.Protocol):
    delete_done_notes: bool = False
    start_words: list[str] = []

    async def create_note(self, text: str) -> None:
        ...

    async def get_undone_note_titles(self) -> list[str]:
        ...

    async def get_done_note_ids(self) -> list[uuid.UUID]:
        ...

    async def delete_note(self, id: uuid.UUID) -> None:
        ...

    async def list_pages(self, modified_since: str | None = None) -> list[dict]:
        ...

    async def get_page_blocks(self, page_id: str) -> list[dict]:
        ...


class NotesFilterProtocol(typing.Protocol):
    def __init__(self, notes_services: list[NotesServiceProtocol]) -> None:
        ...

    def get_needed_to_create_notes(self, text: str) -> list[NotesServiceProtocol]:
        ...


class SyncTrackerProtocol(typing.Protocol):
    async def get_last_sync_time(self) -> str | None:
        ...

    async def update_sync_time(self, timestamp: str) -> None:
        ...

    async def update_sync_time_if_bigger(self, timestamp: str) -> None:
        ...


class VectorStoreRepository(typing.Protocol):
    async def ensure_collection(self) -> None:
        ...

    async def upsert(self, chunks: typing.Iterable) -> None:
        ...

    async def search(self, vector: list[float], limit: int) -> list[tuple]:
        ...

    async def delete_by_page_id(self, page_id: str) -> None:
        ...

    @staticmethod
    def get_stable_id(s: str) -> str:
        ...


class AIService(typing.Protocol):
    async def embed_text(self, text: str) -> list[float]:
        ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    async def caption_images(self, image_urls: list[str]) -> str:
        ...

    async def generate_answer(self, question: str, contexts: list[str]) -> str:
        ...

    async def generate_images(self, prompt: str) -> list[str | None]:
        ...

    def chunk_text(self, text: str) -> list[str]:
        ...


class NotesHandler:
    _sync_notes_service: NotesServiceProtocol
    _sync_ai_service: AIService
    _sync_tracker_service: SyncTrackerProtocol
    _sync_vector_store: VectorStoreRepository

    def __init__(self, message_service: MessageServiceProtocol, filter_class: type[NotesFilterProtocol]) -> None:
        self._message_service = message_service
        self._filter_class = filter_class
        self._notes_services: list[NotesServiceProtocol] = []

    def with_notes_service(self, notes_service: NotesServiceProtocol,
                           delete_done_notes: bool, start_words: list[str]) -> typing.Self:
        notes_service.delete_done_notes = delete_done_notes
        notes_service.start_words = start_words
        self._notes_services += [notes_service]
        return self

    async def _create_notes(self, text: str) -> None:
        for notes_service in self._filter_class(self._notes_services).get_needed_to_create_notes(text):
            await notes_service.create_note(text)

    async def _get_notes(self) -> str:
        notes = []
        for notes_service in self._notes_services:
            notes += [notes_service.__class__.__name__ + ':']
            notes += await notes_service.get_undone_note_titles()
        return '\n'.join(notes)

    async def transmit_messages(self) -> None:
        await self._message_service.handle_messages(self._create_notes)
        await self._message_service.handle_notes_request(self._get_notes)
        logger.info(
            'Message handlers initialized (%s) => {%s}.',
            self._message_service.__class__.__name__,
            list(map(lambda x: x.__class__.__name__, self._notes_services)),
        )

    async def delete_done_notes(self) -> None:
        logger.debug('Delete done notes')
        for notes_service in self._notes_services:
            if notes_service.delete_done_notes:
                note_ids = await notes_service.get_done_note_ids()
                for note_id in note_ids:
                    await notes_service.delete_note(note_id)

    def with_sync_knowledge(self, notes_service: NotesServiceProtocol, vector_store: VectorStoreRepository,
                            ai_service: AIService, tracker_service: SyncTrackerProtocol) -> None:
        self._sync_notes_service = notes_service
        self._sync_vector_store = vector_store
        self._sync_ai_service = ai_service
        self._sync_tracker_service = tracker_service

    async def etl_knowledge_to_vector_db(self) -> int:
        logger.debug('ETL knowledge to vector DB')
        await self._sync_vector_store.ensure_collection()
        # Get last sync time for incremental updates
        last_sync = await self._sync_tracker_service.get_last_sync_time()
        if last_sync:
            logger.debug(f"Fetching pages modified since: {last_sync}")
            pages = await self._sync_notes_service.list_pages(modified_since=last_sync)
        else:
            logger.debug("First sync: fetching all pages")
            pages = await self._sync_notes_service.list_pages()

        # Save to vector DB
        upserted = 0
        for page in pages[:1]:
            await self._sync_tracker_service.update_sync_time_if_bigger(
                page.get("last_edited_time", "")
            )
            chunks = await self._save_to_vector_db(page)
            upserted += len(chunks)
        return upserted

    async def _save_to_vector_db(self, page: dict) -> list:
        chunks: list[PageChunk] = []
        page_id = page.get("id", "")
        last_edited = page.get("last_edited_time", "")
        title = self._get_page_title(page)
        logger.debug(f'{page_id=} {title=} ({last_edited})')
        blocks = await self._sync_notes_service.get_page_blocks(page_id)
        text, image_urls = self._extract_text_and_images(blocks)
        image_caption = await self._sync_ai_service.caption_images(image_urls) if image_urls else ""
        full_text = (title + "\n" + text + ("\nImages: " + image_caption if image_caption else "")).strip()
        logger.debug(full_text)
        if not full_text:
            return chunks
        chunks_text = self._sync_ai_service.chunk_text(full_text)
        vectors = await self._sync_ai_service.embed_texts(chunks_text)
        for idx, (ct, vec) in enumerate(zip(chunks_text, vectors)):
            cid = self._sync_vector_store.get_stable_id(f"{page_id}:{last_edited}:{idx}:{len(ct)}")
            logger.debug(cid)
            chunks.append(PageChunk(
                id=cid,
                page_id=page_id,
                title=title,
                text=ct,
                image_urls=image_urls,
                last_edited_time=last_edited,
                metadata={},
                vector=vec,
            ))
        logger.debug(f"Deleted existing chunks for page: {page_id=} {title=}")
        await self._sync_vector_store.delete_by_page_id(page_id)
        logger.debug(f"Insert existing chunks for page: {page_id=} ({len(chunks)})")
        await self._sync_vector_store.upsert(chunks)
        return chunks

    @staticmethod
    def _get_page_title(page: dict) -> str:
        props = page.get("properties", {})
        for v in props.values():
            if v.get("type") == "title":
                title_parts = v.get("title", [])
                return "".join([t.get("plain_text", "") for t in title_parts])
        return "Untitled"

    @staticmethod
    def _extract_text_and_images(blocks: list[dict]) -> tuple[str, list[str]]:
        texts: list[str] = []
        images: list[str] = []
        for b in blocks:
            typ = b.get("type")
            if typ in {
                "paragraph", "heading_1", "heading_2", "heading_3", "quote",
                "bulleted_list_item", "numbered_list_item", "callout"
            }:
                rich = b.get(typ, {}).get("rich_text", [])
                texts.append("".join([r.get("plain_text", "") for r in rich]))
            elif typ == "image":
                d = b.get("image", {})
                if "file" in d:
                    images.append(d["file"].get("url", ""))
                elif "external" in d:
                    images.append(d["external"].get("url", ""))
        return "\n".join([t for t in texts if t]), [u for u in images if u]
