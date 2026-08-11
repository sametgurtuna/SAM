# SAM — RAG Engine
# Lokal bilgi tabani uzerinde semantik arama.
# sentence-transformers + ChromaDB kullanir.
# Lazy-init: ilk FENERBAHCE sorgusuna kadar hicbir sey yuklenmez.

import glob
import hashlib
import logging
import os
import threading

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Markdown dosyalarindan bilgi alip semantik arama yapar.

    Tasarim:
    - Lazy initialization: ilk retrieve() cagrisina kadar model/DB yuklenmez.
    - Thread-safe: initialize() bir kez calisir, sonraki cagrilar no-op.
    - In-memory ChromaDB: bilgi tabani kucuk (~20 chunk), persistent gereksiz.
    - Paragraf bazli chunking: kisa chunk'lar 3B model icin ideal.
    """

    def __init__(self, knowledge_path: str, embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 800, chunk_overlap: int = 80, top_k: int = 3) -> None:
        self._knowledge_path = knowledge_path
        self._embedding_model_name = embedding_model
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._top_k = top_k

        self._model = None
        self._collection = None
        self._initialized = False
        self._init_lock = threading.Lock()

    def _ensure_initialized(self) -> bool:
        """Lazy init — ilk kullanimda model ve DB'yi yukle."""
        if self._initialized:
            return True

        with self._init_lock:
            if self._initialized:
                return True

            try:
                self._do_initialize()
                self._initialized = True
                return True
            except Exception as e:
                logger.error("RAG initialization failed: %s", e)
                return False

    def _do_initialize(self) -> None:
        """Model yukle, bilgi dosyalarini indexle."""
        # Lazy import — torch ve chromadb sadece gerektiginde yuklenir
        from sentence_transformers import SentenceTransformer
        import chromadb

        logger.info("Initializing RAG engine (model: %s)...", self._embedding_model_name)

        self._model = SentenceTransformer(self._embedding_model_name)

        client = chromadb.Client()  # In-memory
        self._collection = client.get_or_create_collection(
            name="knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        self._index_knowledge()
        logger.info("RAG engine ready — %d chunks indexed", self._collection.count())

    def _index_knowledge(self) -> None:
        """knowledge/ dizinindeki tum .md dosyalarini chunk'la ve indexle."""
        if not os.path.isdir(self._knowledge_path):
            logger.warning("Knowledge path not found: %s", self._knowledge_path)
            return

        all_chunks: list[dict] = []
        md_pattern = os.path.join(self._knowledge_path, "**", "*.md")

        for md_file in glob.glob(md_pattern, recursive=True):
            try:
                with open(md_file, encoding="utf-8") as f:
                    text = f.read()
            except OSError as e:
                logger.warning("Could not read %s: %s", md_file, e)
                continue

            source = os.path.relpath(md_file, self._knowledge_path)
            chunks = self._chunk_text(text, source)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("No knowledge chunks found in %s", self._knowledge_path)
            return

        # Batch encode ve indexle
        texts = [c["text"] for c in all_chunks]
        ids = [c["id"] for c in all_chunks]
        sources = [{"source": c["source"]} for c in all_chunks]

        embeddings = self._model.encode(texts)

        self._collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=sources,
        )

    def _chunk_text(self, text: str, source: str) -> list[dict]:
        """
        Paragraf bazli chunking.

        Strateji:
        1. Bos satirlardan paragraflara bol.
        2. Cok uzun paragraflari chunk_size'a gore kes.
        3. Baslik satirlarini (#) bir sonraki paragrafa ekle (context icin).
        """
        paragraphs: list[str] = []
        current_heading = ""

        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue

            # Markdown baslik mi?
            if block.startswith("#"):
                current_heading = block.split("\n")[0].strip()
                # Baslik altinda icerik varsa onu da al
                rest = "\n".join(block.split("\n")[1:]).strip()
                if rest:
                    paragraphs.append(f"{current_heading}\n{rest}")
                continue

            # Normal paragraf — basligi one ekle
            if current_heading:
                block = f"{current_heading}\n{block}"

            paragraphs.append(block)

        # Uzun paragraflari chunk_size'a gore bol
        chunks: list[dict] = []
        for para in paragraphs:
            if len(para) <= self._chunk_size:
                chunk_id = hashlib.md5(para.encode()).hexdigest()[:12]
                chunks.append({
                    "id": f"{source}_{chunk_id}",
                    "text": para,
                    "source": source,
                })
            else:
                # Cumle sinirlarindan bol
                sentences = para.replace(". ", ".\n").split("\n")
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 > self._chunk_size and current:
                        chunk_id = hashlib.md5(current.encode()).hexdigest()[:12]
                        chunks.append({
                            "id": f"{source}_{chunk_id}",
                            "text": current.strip(),
                            "source": source,
                        })
                        # Overlap: son cumleyi yeni chunk'a tasi
                        overlap_text = current.rsplit(".", 1)[-1].strip()
                        current = overlap_text + " " + sent if overlap_text else sent
                    else:
                        current = (current + " " + sent).strip() if current else sent

                if current.strip():
                    chunk_id = hashlib.md5(current.encode()).hexdigest()[:12]
                    chunks.append({
                        "id": f"{source}_{chunk_id}",
                        "text": current.strip(),
                        "source": source,
                    })

        return chunks

    def retrieve(self, query: str, top_k: int | None = None) -> str | None:
        """
        Sorguya en yakin chunk'lari getir.

        Args:
            query: Kullanici sorusu.
            top_k: Dondurilecek chunk sayisi (None = varsayilan).

        Returns:
            Birlesmis bilgi metni veya None (RAG hazir degilse/sonuc yoksa).
        """
        if not self._ensure_initialized():
            return None

        k = top_k or self._top_k

        try:
            query_embedding = self._model.encode([query])
            results = self._collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=k,
            )
        except Exception as e:
            logger.error("RAG retrieval failed: %s", e)
            return None

        documents = results.get("documents", [[]])[0]
        if not documents:
            return None

        # Chunk'lari birlestir, kaynak bilgisiyle
        return "\n\n---\n\n".join(documents)

    @property
    def is_initialized(self) -> bool:
        return self._initialized
