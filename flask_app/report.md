## 🧠 RAG Search Engine — Project Summary Report

This project was centered around building a **Retrieval-Augmented Generation (RAG) search engine** — a system where a language model is enhanced with external information retrieval to answer queries more accurately and contextually.

The idea is simple on paper: don’t let the model guess — **let it read first.** Here's how we pulled it off.

---

### 🔍 1. Information Sources

We used two main sources of knowledge:

- **Wikipedia** — for general, human-readable explanations.
- **ArXiv** — for more technical and research-heavy content, especially useful in academic queries.

The user gets to choose which of these to use when submitting their question, giving them some control over the "tone" and depth of the retrieved context.

---

### 💡 2. Keyphrase-Based Search

Instead of just querying raw user input, we **extract keyphrases** to make our search smarter and more focused. For this we used:

- **KeyBERT** along with **KeyBERTVectorizer**.

This helps us distill the essence of a question and generate high-quality search queries. These keyphrases are then used to search Wikipedia and/or ArXiv for relevant passages.

---

### 📄 3. PDF Upload Support

As the project evolved, we realized sometimes users might want to search *their own material*. So we added support for **PDF upload** — the uploaded documents are treated like another source of knowledge, chunked and indexed just like Wikipedia/ArXiv content.

---

### 🧠 4. Chunking, Embedding, and Vector DB

All content — whether from Wikipedia, ArXiv, or uploaded PDFs — goes through the same pipeline:

1. **Chunked** using a sliding window approach to preserve context.
2. **Embedded** using the `all-MiniLM-L6-v2` model from SentenceTransformers.
3. **Stored** in a vector database — we use **Qdrant**, which gives fast similarity search over embeddings.

This lets us efficiently retrieve the most relevant content chunks for any new query based on **cosine similarity**.

---

### 🧲 5. Retrieval and Summarization

When a user sends a query, here's what happens:

1. Relevant chunks are retrieved from Qdrant using the query's embedding.
2. Initially, we **directly fed all the retrieved chunks** into the prompt for the LLM. However, this quickly ran into **context window issues** (especially with smaller models like `phi-3-mini`).
3. So we upgraded our pipeline to **summarize the retrieved chunks** first using a **DistilBERT summarizer**, which dramatically reduced the input size while preserving key information.

This helped both with **faster inference** and **better prompt quality** for the final generation.

---

### 🗣️ 6. Generation via LLM

For the actual answer generation, we used **phi-3-mini** — a compact yet capable language model. To keep things efficient and predictable:

- We used **low temperature** for deterministic outputs.
- Set **`max_tokens`** to avoid runaway generations.
- Monitored the **total context window** carefully to prevent truncation errors.

The final summary + query are passed to the model, and the answer is generated and displayed.

---

### ⚙️ 7. Engineering Considerations

We took several steps to optimize speed and user experience:

- **Asynchronous programming** was used to parallelize fetch operations (especially for ArXiv/Wikipedia).
- Embeddings and metadata are **persistently stored in Qdrant**, enabling quick future retrieval.
- Context windows are carefully monitored to avoid overflows or cutoff generations.
- The frontend is built to be user-friendly, with options for configuration, file uploads, and dynamic message streaming.

---

### 🐢 8. Performance Bottlenecks

Despite the effort, there is **noticeable latency** during query execution — particularly in:

- Keyphrase generation and multi-source fetching
- PDF parsing (if large)
- Final model inference, depending on summarization time and LLM speed

While everything is reasonably optimized, the nature of RAG systems — especially with summarization + LLM steps — means some lag is expected. Potential optimizations could include caching, background pre-fetching, or switching to more performant models/APIs.

---

### 📦 9. Codebase Overview

The code is modular and extensible:

- `app2.py` and `app3.py` handles routing, SSE-based streaming, and query dispatch.
- `app2.py` uses phi-3-mini and runs locally.
- `app3.py` uses GOOGLE GEMINI API to access gemini-2.0-flash.
- `Helper4.py` contains the core logic for chunking, embedding, storing and retrieving from Qdrant.
- Async routines are used throughout to make the app responsive, especially during content fetching and vector operations.
- `test.py` contains unit tests for the core logic of various helper functions.

The backend is already well-structured for future extensions like:
- Adding more document formats
- Caching summaries
- Switching to LLM APIs or serverless models for better latency
---

### ✅ Final Thoughts

This project demonstrates a complete, working **retrieval-augmented pipeline**, blending:

- **IR (Information Retrieval)** — via Wikipedia/ArXiv/Documents
- **NLP** — via KeyBERT, summarization, embeddings
- **LLMs** — for final generation
---
