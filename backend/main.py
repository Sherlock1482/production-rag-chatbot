import os
from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path
from guardrails.output_guardrail import check_output_guardrail
from guardrails.output_guardrail import check_output_guardrail
from guardrails.evidence_guardrail import check_evidence_guardrail
from guardrails.input_guardrail import check_input_guardrail
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from utils.retriever import search_and_rerank
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

MCP_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"


async def call_interview_mcp(candidate_name: str = ""):
    """
    Connect to the TA MCP server and call the interview schedule tool.
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_interview_schedule",
                arguments={
                    "candidate_name": candidate_name
                }
            )

            return result

@app.get("/")
def health_check():
    return {"status": "healthy", "domain": "Talent Acquisition (TA)"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    RAG Chat endpoint for Talent Acquisition:
    1. Retrieves relevant candidate/job description chunks using vector search & reranker.
    2. Constructs a grounded prompt with source citations.
    3. Generates responses using Groq (Llama-3).
    """
    try:

                # Step 0: Check whether the question needs live interview data
        # Step 0: Check whether the question needs live interview data
        query_lower = request.query.lower()

        mcp_data = None
        mcp_context = ""

        interview_keywords = [
            "interview",
            "schedule",
            "scheduled",
            "stage",
            "status"
        ]

        if any(keyword in query_lower for keyword in interview_keywords):

            candidate_names = [
                "priya",
                "arjun",
                "jane"
            ]

            for name in candidate_names:
                if name in query_lower:
                    mcp_data = await call_interview_mcp(name)
                    break

            if mcp_data is None and "all" in query_lower:
                mcp_data = await call_interview_mcp("")

        if mcp_data:
            mcp_context = f"\nLive Interview Data from MCP:\n{mcp_data}\n"
            #input guardrail check
        if not check_input_guardrail(request.query):
            return {
                "response": "I can only help with Talent Acquisition and recruitment-related questions.",
                "sources": []
            }
        # Step 1: Retrieve and Rerank TA documents
        relevant_docs = search_and_rerank(
            query=request.query, 
            top_k=request.top_k, 
            top_n=request.top_n
        )

        if not mcp_data and not check_evidence_guardrail(relevant_docs):
            return {
                "response": (
                    "I couldn't find enough relevant information in the "
                    "Talent Acquisition documents to answer this question accurately."
                ),
                "sources": []
            }
        
        if not relevant_docs and not mcp_data:
            return {
                "response": "I'm sorry, but I couldn't find relevant information in the TA database.",
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
            "Answer the recruiter's question using the provided information. "
            "The information may come from either the TA document database "
            "or live interview data provided by an MCP tool. "
            "Use the live MCP interview data when answering questions about "
            "candidate interview schedules, stages, dates, or interviewers. "
            "Do not invent information. "
            "When using candidate qualifications or job requirements from documents, "
            "cite the source ID such as [1] or [2]. "
            "If the requested information is not available, clearly state that "
            "the information is missing from the database."
            "For interview questions, give a concise answer using the candidate's "
            "date, stage, and interviewer when available. Do not say information "
            "is missing if it is present in the MCP data. "
        )

        user_prompt = (
            f"Context Documents:\n{combined_context}\n"
            f"{mcp_context}\n"
            f"Recruiter Query: {request.query}"
        )

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

        if not check_output_guardrail(ai_response, relevant_docs,mcp_context):
            return {
                "response": (
                    "I couldn't verify that the generated answer is fully "
                    "supported by the available Talent Acquisition documents."
                ),
                "sources": []
            }

        return {
            "response": ai_response,
            "sources": sources
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)