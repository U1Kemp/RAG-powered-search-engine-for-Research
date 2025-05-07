# 
#  Uses GOOGLE GEMINI API instead of the local LLM (phi-3-mini)
# 
from flask import Flask, request, Response, render_template, jsonify
import asyncio
import multiprocessing
from time import time
from tqdm import tqdm
import json
import os
import uuid

# Import helper functions from Helper4
from Helper4 import (
    extract_keywords,
    fetch_wikipedia_content,
    fetch_arxiv_papers,
    remove_duplicate_dicts,
    store_content,
    retrieve_content,
    summarize,
    delete_collection,
    process_pdf_file,
    chunk_text
)

# Flask app initialization
app = Flask(__name__)

# Global configuration for Qdrant and collection naming
COLLECTION_PREFIX = "rag_session_"
session_id = "test"

# Create async Qdrant client (using in-memory storage)
from qdrant_client import async_qdrant_client
client = async_qdrant_client.AsyncQdrantClient(":memory:")

# Embedder for document embeddings
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Determine number of CPU threads
import multiprocessing
n_threads = multiprocessing.cpu_count()

# Switch to Google Gemini API
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Global chat state – now uses topics instead of subject/subtopic.
chat_state = {}

def initialize_chat_state(
    topics: list[str],
    use_wikipedia: bool,
    fetch_most_relevant: bool,
    fetch_most_recent: bool,
    arxiv_subject: str = "",
    arxiv_subtopic: str = "",
    file_upload: bool = False
) -> dict:
    """
    Initialize the global chat state with the provided configuration.

    Args:
        topics (list[str]): List of topics that the chatbot should be knowledgeable about.
        use_wikipedia (bool): Whether to use Wikipedia content or not.
        fetch_most_relevant (bool): Whether to fetch the most relevant arXiv papers or not.
        fetch_most_recent (bool): Whether to fetch the most recent arXiv papers or not.
        arxiv_subject (str): Optional subject filter for arXiv papers.
        arxiv_subtopic (str): Optional subtopic filter for arXiv papers.
        file_upload (bool): Whether file is upload or not.

    Returns:
        dict: The initialized chat state.
    """
    topics_str = ", ".join(topics)
    return {
        "topics": topics,
        "conversation_history": "",
        "model_context": f"Topics: {topics_str}\n\n",
        "key_phrases": [],
        "first_query": True,
        "citations": [],
        "use_wikipedia": use_wikipedia,
        "fetch_most_relevant": fetch_most_relevant,
        "fetch_most_recent": fetch_most_recent,
        "arxiv_subject": arxiv_subject,
        "arxiv_subtopic": arxiv_subtopic,
        "file_upload": file_upload
    }

# Load JSON data
with open('sub2tag.json', 'r') as f:
    sub2tag = json.load(f)

@app.route("/")
def index():
    """
    Serves the main chat interface.

    Returns:
        str: HTML template for the chat interface with the subjects dropdown populated.
    """
    
    return render_template('index.html', subjects=list(sub2tag.keys()))

@app.route('/get_subtopics', methods=['POST'])
def get_subtopics():
    """
    Returns a JSON list of subtopics for the given subject.

    The subject is expected to be provided in the JSON payload of the request.

    Returns:
        list: A list of subtopics for the given subject.
    """
    subject = request.json.get('subject')
    if subject in sub2tag:
        return jsonify(list(sub2tag[subject].keys()))
    return jsonify([])

file_upload = False
@app.route("/upload_files", methods=["POST"])
async def upload_files():
    """
    Handle file uploads, process them, and add their content to the Qdrant collection.
    
    Supported file types: PDF, TXT, DOCX
    
    Returns:
        JSON response with success status and list of processed files
    """
    global chat_state
    global file_upload
    
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No files provided"}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({"success": False, "error": "No files selected"}), 400
    
    # Process each file
    processed_files = []
    document_chunks = []
    
    for file in files:
        try:
            # Get the file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            # Extract content based on file type
            if file_ext == '.pdf':
                # Process PDF file
                content = await process_pdf_file(file)
            elif file_ext == '.txt':
                # Process text file
                content = file.read().decode('utf-8')
            
            # Chunk the content
            chunks = chunk_text(content, chunk_size=512, overlap=64)
            
            # Add each chunk to the document chunks list
            for i, chunk in enumerate(chunks):
                document_chunks.append({
                    "id": f"file_{uuid.uuid4().hex[:8]}",
                    "title": f"{file.filename} - Chunk {i+1}",
                    "text": chunk,
                    "source": f"Uploaded file: {file.filename}"
                })
            
            processed_files.append(file.filename)
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Error processing {file.filename}: {str(e)}"
            }), 500
    
    # Store the document chunks in Qdrant
    if document_chunks:
        await store_content(COLLECTION_PREFIX, session_id, document_chunks, batch_size=256)
    
    # Add file keywords to the chat state
    if processed_files and not chat_state["first_query"]:
        for file_name in processed_files:
            chat_state["key_phrases"].append(os.path.splitext(file_name)[0])
        file_upload = True
        chat_state['file_upload'] = True
    elif processed_files:
        file_upload = True
        chat_state['file_upload'] = True
    
    return jsonify({
        "success": True,
        "file_count": len(processed_files),
        "files": processed_files
    })

@app.route("/init", methods=["POST"])
def init_chat():
    """
    Initialize chat session using the provided topics and arXiv settings.

    The chat session is initialized with the provided topics and arXiv settings.
    The following keys are expected in the JSON payload:

    - topics: a list of topic strings.
    - use_wikipedia: a boolean flag to use Wikipedia for context.
    - fetch_most_relevant: a boolean flag to fetch the most relevant arXiv papers.
    - fetch_most_recent: a boolean flag to fetch the most recent arXiv papers.
    - arxiv_subject: an optional string to filter arXiv papers by subject.
    - arxiv_subtopic: an optional string to filter arXiv papers by subtopic.

    Returns:
        dict: A JSON object with a single key "success" set to True.
    """
    global chat_state
    # Get the JSON payload from the request
    data = request.get_json(force=True)
    # Get the topics from the JSON payload, default to ["Deepseek"] if not provided.
    topics = data.get("topics", ["Deepseek"])
    # Get the use_wikipedia flag from the JSON payload, default to True if not provided.
    use_wikipedia = data.get("use_wikipedia", False)
    # Get the fetch_most_relevant flag from the JSON payload, default to False if not provided.
    fetch_most_relevant = data.get("fetch_most_relevant", False)
    # Get the fetch_most_recent flag from the JSON payload, default to False if not provided.
    fetch_most_recent = data.get("fetch_most_recent", False)
    # Get the arxiv_subject from the JSON payload, default to None if not provided.
    arxiv_subject = data.get("arxiv_subject", "")
    # Get the arxiv_subtopic from the JSON payload, default to None if not provided.
    arxiv_subtopic = data.get("arxiv_subtopic", "")
    # Initialize the chat state with the provided topics and arXiv settings.
    file_upload = data.get("uploaded", False)
    chat_state = initialize_chat_state(topics, use_wikipedia, fetch_most_relevant, fetch_most_recent, arxiv_subject, arxiv_subtopic, file_upload)
    # Return a JSON object with a single key "success" set to True.
    return jsonify({"success": True})

def stream_response(user_input):
    """
    Generator function to stream status and response tokens via SSE.
    It uses Wikipedia and arXiv content based on the provided topics and arXiv filter options.
    """
    global chat_state

    # First query: fetch initial content
    if chat_state["first_query"]:
        key_phrases = extract_keywords(user_input, top_n=5, threshold=0.50)
        key_phrases += chat_state["topics"]
        if len(user_input.split()) < 4:
            key_phrases += [user_input]
        chat_state["key_phrases"] = list(set(key_phrases))

        wiki_content = []
        start = time()
        if chat_state["use_wikipedia"]:
            yield "event: status\ndata: Fetching Wikipedia content...\n\n"
            wiki_content = asyncio.run(fetch_wikipedia_content(queries=chat_state["key_phrases"], num_results=10, max_sections=15))
            yield "event: status\ndata: Wikipedia content fetched in {:.2f} seconds.\n\n".format(time() - start)

        arxiv_content = []
        if chat_state["fetch_most_recent"] or chat_state["fetch_most_relevant"]:
            yield "event: status\ndata: Fetching arXiv content...\n\n"
            start = time()
            arxiv_query = chat_state["key_phrases"]
            
            if chat_state["fetch_most_relevant"]:
                arxiv_content += asyncio.run(fetch_arxiv_papers(subject=chat_state["arxiv_subject"], subtopic=chat_state["arxiv_subtopic"], queries=arxiv_query, max_results=20, priority="relevance"))
            if chat_state["fetch_most_recent"]:
                arxiv_content += asyncio.run(fetch_arxiv_papers(subject=chat_state["arxiv_subject"], subtopic=chat_state["arxiv_subtopic"], queries=arxiv_query, max_results=20, priority="submitted"))
            yield "event: status\ndata: arXiv content fetched in {:.2f} seconds.\n\n".format(time() - start)

        if len(wiki_content) != 0 or len(arxiv_content) != 0:
            yield "event: status\ndata: Removing duplicates and storing content in Qdrant...\n\n"
            start = time()
            documents = remove_duplicate_dicts(wiki_content) + remove_duplicate_dicts(arxiv_content)
            asyncio.run(store_content(COLLECTION_PREFIX, session_id, documents, batch_size=256))
            yield "event: status\ndata: Content stored in Qdrant in {:.2f} seconds.\n\n".format(time() - start)
        chat_state["first_query"] = False
    else:
        new_keywords = extract_keywords(user_input, top_n=5, threshold=0.25)
        if len(user_input.split()) < 4:
            new_keywords += [user_input]
        new_keywords = [kw for kw in new_keywords if kw not in chat_state["key_phrases"]]
        if not set(new_keywords).issubset(set(chat_state["key_phrases"])):
            yield "event: status\ndata: Fetching additional content for new keywords...\n\n"
            start = time()
            all_docs = []
            if chat_state["fetch_most_relevant"]:
                all_docs.extend(asyncio.run(fetch_arxiv_papers(subject=chat_state["arxiv_subject"], subtopic=chat_state["arxiv_subtopic"], queries=new_keywords, max_results=25, priority="relevance")))
            if chat_state["fetch_most_recent"]:
                all_docs.extend(asyncio.run(fetch_arxiv_papers(subject=chat_state["arxiv_subject"], subtopic=chat_state["arxiv_subtopic"], queries=new_keywords, max_results=25, priority="submitted")))
            if chat_state["use_wikipedia"]:
                all_docs.extend(asyncio.run(fetch_wikipedia_content(new_keywords, num_results=10, max_sections=15, chunk_size=512, overlap=64)))
            if all_docs != []:
                asyncio.run(store_content(COLLECTION_PREFIX, session_id, documents=all_docs, batch_size=256))
            chat_state["key_phrases"].extend([kw for kw in new_keywords if kw not in chat_state["key_phrases"]])

            if chat_state["fetch_most_recent"] or chat_state["fetch_most_relevant"] or chat_state["use_wikipedia"] or chat_state["file_upload"]:
                yield "event: status\ndata: Additional content stored in Qdrant in {:.2f} seconds.\n\n".format(time() - start)

    # Retrieve relevant documents
    if chat_state["fetch_most_relevant"] or chat_state["fetch_most_recent"] or chat_state["use_wikipedia"] or chat_state["file_upload"]:
        yield "event: status\ndata: Retrieving relevant documents...\n\n"
        start = time()
        relevant_docs = asyncio.run(retrieve_content(COLLECTION_PREFIX, session_id, user_input, top_k=20, threshold=0.35))
    
    else:
        relevant_docs = []
        chat_state["model_context"] += "<|user|>\n"

    if len(relevant_docs) > 0:
        yield "event: status\ndata: Retrieved documents in {:.2f} seconds.\n\n".format(time() - start)
        chat_state["model_context"] += "<|user|>\nUse the following context and your own knowledge to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Keep the answer as detailed, lucid and to the point as possible. Answer should be at most of 1250 words.\n\n"

    # Update conversation context with retrieved documents
    chat_state["conversation_history"] += f"User: {user_input}\n"
    
    new_context = ""
    chat_state["citations"] = []
    for doc in tqdm(relevant_docs):
        new_context += f"{doc['title']}\n{doc['text']}\n\n"
        chat_state["citations"].append(f"- {doc['title']} ({doc['source']})")
    if len(new_context) > 0:
        new_context = summarize(new_context, max_input_tokens=1024, max_output_tokens=1024)
        chat_state["model_context"] += new_context
        chat_state["model_context"] += f"Question: {user_input}\n<|end|>\n<|assistant|>\n"
    else:
        chat_state["model_context"] += f"<|user|>\n{user_input}\n<|end|>\n<|assistant|>\n"
    chat_state["conversation_history"] += "Assistant: "

    # Trim context if exceeding model token limits
    while len(chat_state["model_context"].split()) > 1e6:
        user_start = chat_state["model_context"].find("<|user|>")
        assistant_start = chat_state["model_context"].find("<|assistant|>", user_start + 1)
        if user_start == -1 or assistant_start == -1:
            break
        chat_state["model_context"] = chat_state["model_context"][assistant_start:].strip()

    yield "event: status\ndata: Generating response...\n\n"
    generated_text = ""
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    chat = model.start_chat(history=[])
    first = True
    for part in chat.send_message(
        chat_state["model_context"],
        stream=True,
        generation_config=genai.types.GenerationConfig(
        temperature=0.15,
        max_output_tokens=1920,
        top_p=0.9,
        top_k=40,
        stop_sequences=["<|end|>", "<|assistant|>"]
        )
    ):
    
        token = part.text.replace("\n\n", "<br><br>").replace("\n", "<br>")
        
        if first:
            first = False
            yield "event: clearStatus\ndata: \n\n"
        yield f"data: {token}\n\n"
        generated_text += token

    chat_state["model_context"] += f"{generated_text}\n"
    chat_state["conversation_history"] += generated_text

    if len(chat_state["citations"]) > 0:
        yield f"event: citation\ndata: References: <br>\n"
        for citation in set(chat_state["citations"]):
            yield f"event: citation\ndata: {citation}\n\n"

    yield "event: end\ndata: \n\n"

@app.route("/chat", methods=["GET"])
def chat():
    """
    Chat endpoint: expects query parameter 'prompt' and streams SSE response.
    """
    user_input = request.args.get("prompt", "")
    if not user_input:
        return "No prompt provided", 400
    return Response(stream_response(user_input), mimetype="text/event-stream")

@app.route("/shutdown", methods=["POST"])
def shutdown():
    """
    Clear session data and delete the Qdrant collection.
    """
    global chat_state
    try:
        asyncio.run(delete_collection(COLLECTION_PREFIX, session_id))
    except Exception as e:
        return f"Error deleting collection: {e}", 500
    chat_state = initialize_chat_state(
        chat_state.get("topics", []),
        chat_state.get("use_wikipedia", True),
        chat_state.get("fetch_most_relevant", True),
        chat_state.get("fetch_most_recent", False),
        chat_state.get("arxiv_subject", ""),
        chat_state.get("arxiv_subtopic", ""),
        chat_state.get("file_upload", False)
    )
    chat_state["file_upload"] = False
    return "Session data cleared", 200

if __name__ == "__main__":
    # Run the Flask app with debugging enabled.
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
