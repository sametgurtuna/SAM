# SAM — RAG Engine
# Semantic search over local knowledge base.
# Uses sentence-transformers + ChromaDB.
# Lazy-init: nothing is loaded until the first domain query.

import glob
import hashlib
import logging
import os
import threading

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Indexes markdown files and provides semantic retrieval.

    Design:
    - Lazy initialization: models/DB loaded only on first retrieve() call.
    - Thread-safe: initialize() runs once under lock; subsequent calls are no-ops.
    - In-memory ChromaDB: small knowledge base (~20-50 chunks).
    - Paragraph-based chunking with header context propagation.
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
        """Lazy init — load model and database on first use."""
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
        """Load embedding model and index knowledge files."""
        # Lazy import — load torch and chromadb only when needed
        from sentence_transformers import SentenceTransformer
        import chromadb

        # Check if embedding model is pre-bundled in frozen distribution
        from core import paths
        local_model_dir = paths.resource_path(
            "assets", "models", "embedding", self._embedding_model_name
        )
        model_source = (
            local_model_dir
            if os.path.isdir(local_model_dir)
            else self._embedding_model_name
        )

        logger.info("Initializing RAG engine (model: %s, source: %s)...",
                    self._embedding_model_name,
                    "bundled" if model_source == local_model_dir else "HF download")

        self._model = SentenceTransformer(model_source)

        client = chromadb.Client()  # In-memory
        self._collection = client.get_or_create_collection(
            name="knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        self._index_knowledge()
        logger.info("RAG engine ready — %d chunks indexed", self._collection.count())

    def _index_knowledge(self) -> None:
        """Chunk and index all .md files in the knowledge directory."""
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

        # Batch encode and index
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
        Paragraph-based chunking.

        Strategy:
        1. Split by double newlines into paragraphs.
        2. Subdivide long paragraphs based on chunk_size.
        3. Prepend markdown headers (#) to subsequent paragraphs for context.
        """
        paragraphs: list[str] = []
        current_heading = ""

        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue

            # Markdown heading?
            if block.startswith("#"):
                current_heading = block.split("\n")[0].strip()
                # Include content underneath heading
                rest = "\n".join(block.split("\n")[1:]).strip()
                if rest:
                    paragraphs.append(f"{current_heading}\n{rest}")
                continue

            # Standard paragraph — prepend current heading
            if current_heading:
                block = f"{current_heading}\n{block}"

            paragraphs.append(block)

        # Split oversized paragraphs to respect chunk_size
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
                # Split on sentence boundaries
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
                        # Overlap: carry over last sentence to next chunk
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
        Retrieve chunks semantically closest to the query.

        Args:
            query: User search query.
            top_k: Number of chunks to retrieve (None = default).

        Returns:
            Concatenated knowledge text or None if empty.
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

        # Join retrieved chunks
        return "\n\n---\n\n".join(documents)

    def warm(self) -> None:
        """Pre-warm embedding model and index in background."""
        self._ensure_initialized()

    @property
    def is_initialized(self) -> bool:
        return self._initialized
