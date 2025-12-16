import os
import asyncio
from loguru import logger
from dotenv import load_dotenv

# RAG / Embeddings / PDF loader
import chromadb
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader

# Pipecat components
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.tts import GroqTTSService  # ✅ fixed import

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.pipeline.runner import PipelineRunner

from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

from pipecat.frames.frames import TextFrame, LLMRunFrame

load_dotenv(override=True)

logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO")

# Global rag collection
rag_collection = None


def load_pdf_documents(pdf_paths):
    """
    Loads PDF pages and returns list of dicts: {"content": text, "metadata": {...}}
    Accepts single path string or list of paths.
    """
    all_documents = []

    if not pdf_paths:
        return all_documents

    if isinstance(pdf_paths, str):
        # allow comma-separated list in env var
        if "," in pdf_paths:
            pdf_paths = [p.strip() for p in pdf_paths.split(",")]
        else:
            pdf_paths = [pdf_paths]

    for pdf_path in pdf_paths:
        try:
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF not found: {pdf_path}")
                continue

            logger.info(f"Loading PDF: {pdf_path}")
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            for i, page in enumerate(pages):
                all_documents.append({
                    "content": page.page_content,
                    "metadata": {"source": os.path.basename(pdf_path), "page": i + 1}
                })
            logger.info(f"Loaded {len(pages)} pages from {pdf_path}")
        except Exception as e:
            logger.error(f"Error loading {pdf_path}: {e}")

    return all_documents


def init_rag():
    """
    Initialize or create ChromaDB collection with PDF documents.
    Uses global rag_collection.
    """
    global rag_collection
    if rag_collection:
        return

    try:
        chroma_client = chromadb.Client()
    except Exception as e:
        logger.error(f"Failed to create Chroma client: {e}")
        return

    collection_name = "knowledge_base"

    try:
        # try existing collection
        rag_collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        logger.info("Using existing Chroma knowledge_base")
        return
    except Exception:
        # create new collection
        rag_collection = chroma_client.create_collection(
            name=collection_name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        logger.info("Created new Chroma knowledge_base collection")

    # Load PDFs from env
    pdf_path = os.getenv("PDF_PATH", "Data/Loan_Recovery.pdf")
    pdf_docs = load_pdf_documents(pdf_path)

    if not pdf_docs:
        logger.warning("No PDF docs found — RAG will be empty")
        return

    documents = [d["content"] for d in pdf_docs]
    metadatas = [d["metadata"] for d in pdf_docs]
    ids = [f"doc_{i}" for i in range(len(documents))]

    try:
        rag_collection.add(documents=documents, ids=ids, metadatas=metadatas)
        logger.info(f"Added {len(documents)} documents to Chroma collection")
    except Exception as e:
        logger.error(f"Failed to add docs to Chroma: {e}")


def get_rag_context(query: str, n_results: int = 3) -> str:
    """
    Query the rag_collection and return joined context text (n_results pages).
    """
    global rag_collection
    if not rag_collection:
        return ""

    try:
        results = rag_collection.query(query_texts=[query], n_results=n_results)
        docs = results.get("documents", [[]])[0] if results else []
        if docs:
            logger.info(f"RAG retrieved {len(docs)} docs for query: {query[:50]}...")
            return "\n\n".join(docs)
    except Exception as e:
        logger.error(f"Error querying RAG: {e}")

    return ""


async def run_bot(transport, metadata=None):
    """
    Outbound Twilio bot with RAG injection.

    Called from server.py as:
        await run_bot(transport, metadata)

    - transport: FastAPIWebsocketTransport (already configured in server.py)
    - metadata: dict of Twilio customParameters (customer_id, call_type, etc.)
    """
    logger.info("Initializing RAG...")
    init_rag()

    logger.info(f"Starting bot pipeline... metadata={metadata}")

    # Services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    llm = GroqLLMService(api_key=os.getenv("GROQ_API_KEY"))
    tts = GroqTTSService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="playai-tts",
        voice="Celeste-PlayAI",
    )

    # System prompt and context
    messages = [
        {
            "role": "system",
            "content": (
                "You are a friendly AI assistant on a phone call. "
                "Keep replies short and natural. Use the provided document "
                "context when it's relevant to the caller's question."
            ),
        }
    ]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        ),
    )

    # --- Override user push_frame to inject RAG context ---
    original_user_push = context_aggregator.user().push_frame

    async def user_push_with_rag(frame, direction=None):
        """
        If the frame is a TextFrame (user speech -> text), fetch RAG context and
        prepend it to the user message before sending to LLM.
        """
        try:
            if isinstance(frame, TextFrame) and getattr(frame, "text", None):
                user_text = frame.text.strip()
                if user_text:
                    rag_ctx = get_rag_context(user_text, n_results=3)
                    if rag_ctx:
                        enriched = (
                            f"[DOCUMENT CONTEXT]\n{rag_ctx}\n\n"
                            f"[USER QUESTION]\n{user_text}"
                        )
                        frame = TextFrame(enriched)
                        logger.debug("Injected RAG context into user frame")
        except Exception as e:
            logger.error(f"Error injecting RAG: {e}")

        # forward to original push_frame preserving signature
        if direction is not None:
            await original_user_push(frame, direction)
        else:
            await original_user_push(frame)

    # replace method
    context_aggregator.user().push_frame = user_push_with_rag

    # send initial greeting (LLMRunFrame triggers the LLM to speak greeting)
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_obj, client):
        logger.info("Client connected — queueing greeting")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_obj, client):
        logger.info("Client disconnected — cancelling task")
        await task.cancel()

    runner = PipelineRunner()
    await runner.run(task)
    