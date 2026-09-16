import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from utils.retriever import search_and_rerank

app = FastAPI(title="TA RAG Chatbot API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq Client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    top_n: int = 3

@app.get("/")
def health_check():
    return {"status": "healthy", "domain": "Talent Acquisition (TA)"}

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """
    RAG Chat endpoint for Talent Acquisition:
    1. Retrieves relevant candidate/job description chunks using vector search & reranker.
    2. Constructs a grounded prompt with source citations.
    3. Generates responses using Groq (Llama-3).
    """
    try:
        # Step 1: Retrieve and Rerank TA documents
        relevant_docs = search_and_rerank(
            query=request.query, 
            top_k=request.top_k, 
            top_n=request.top_n
        )
        
        if not relevant_docs:
            return {
                "response": "I'm sorry, but I couldn't find any relevant candidate profiles or job descriptions matching your query in the TA database.",
                "sources": []
            }

        # Step 2: Build Context and Source Citations map
        context_blocks = []
        sources = []
        for idx, doc in enumerate(relevant_docs):
            source_name = doc.get("source", "Unknown Source")
            text_content = doc.get("text", "")
            context_blocks.append(f"Source [{idx+1}] ({source_name}):\n{text_content}")
            sources.append({"id": idx + 1, "source": source_name, "text": text_content[:150] + "..."})

        combined_context = "\n\n".join(context_blocks)

        # Step 3: Construct System Prompt with Guardrails & Citation Rules
        system_prompt = (
            "You are an expert Talent Acquisition (TA) AI assistant. "
            "Answer the recruiter's question accurately using ONLY the provided context blocks below. "
            "Always cite the source ID (e.g., [1], [2]) when stating candidate qualifications or job requirements. "
            "If the answer cannot be found in the context, state clearly that the information is missing from the database."
        )

        user_prompt = f"Context Documents:\n{combined_context}\n\nRecruiter Query: {request.query}"

        # Step 4: Call Groq API (Llama-3-8B-Instant)
        chat_completion = groq_client.chat.completions.create(
            model="allam-2-7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # Low temperature for factual, grounded answers
            max_tokens=1024
        )

        ai_response = chat_completion.choices[0].message.content

        return {
            "response": ai_response,
            "sources": sources
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)