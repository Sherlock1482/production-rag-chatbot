import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langfuse import get_client


# ============================================================
# Load .env from the project root
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    BASE_DIR / ".env"
)


# ============================================================
# Groq Client
# ============================================================

client = ChatGroq(
    model=os.getenv("GROQ_GUARDRAIL_MODEL", os.getenv("GROQ_MODEL", "allam-2-7b")),
    temperature=0,
)


# ============================================================
# Langfuse
# ============================================================

langfuse = get_client()


# ============================================================
# Output Guardrail
# ============================================================

def check_output_guardrail(
    answer: str,
    relevant_docs: list,
    mcp_context: str = ""
) -> bool:
    """
    Checks whether the generated answer is supported
    by retrieved documents or MCP data.

    Returns:
        True  -> answer is sufficiently grounded
        False -> answer contains unsupported information
    """

    # ========================================================
    # Langfuse Observation
    # ========================================================

    with langfuse.start_as_current_observation(
        as_type="generation",
        name="output-guardrail",
        input={
            "answer": answer,
            "documents_received": len(
                relevant_docs
            ),
            "has_mcp_context": bool(
                mcp_context
            )
        },
        model=os.getenv("GROQ_MODEL")
    ) as guardrail_trace:

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        if not answer:

            guardrail_trace.update(
                output={
                    "allowed": False,
                    "reason": "Empty answer"
                }
            )

            return False

        if not relevant_docs and not mcp_context:

            guardrail_trace.update(
                output={
                    "allowed": False,
                    "reason": "No supporting evidence"
                }
            )

            return False

        # ----------------------------------------------------
        # Qdrant document context
        # ----------------------------------------------------

        document_context = "\n\n".join(
            doc.get("text", "")
            for doc in relevant_docs
            if doc.get("text")
        )

        # ----------------------------------------------------
        # Combine Qdrant + MCP evidence
        # ----------------------------------------------------

        context = f"""
Retrieved TA Documents:
--------------------
{document_context}
--------------------

MCP Interview Data:
--------------------
{mcp_context}
--------------------
"""

        # ----------------------------------------------------
        # Output validation prompt
        # ----------------------------------------------------

        prompt = f"""
You are an output safety checker for a Talent Acquisition RAG system.

Your job is to determine whether the generated answer is supported
by the available evidence.

The evidence can come from:
1. Retrieved TA documents from Qdrant
2. Live interview data from an MCP tool

Available evidence:
--------------------
{context}
--------------------

Generated answer:
--------------------
{answer}
--------------------

Rules:

1. Return ALLOW if the answer is supported by the available evidence.
2. Return BLOCK if the answer contains information that is not supported
   by the available evidence.
3. Do not require the answer to use the exact wording of the evidence.
4. Small summaries or reasonable rewording are allowed.
5. If the answer makes up candidate information, companies, skills,
   experience, interview dates, interview stages, or interviewers
   that are not present in the evidence, return BLOCK.
6. MCP interview data is valid evidence for interview-related questions.
7. Qdrant documents are valid evidence for document-related questions.
8. Return ONLY:
   ALLOW
   or
   BLOCK
"""

        # ====================================================
        # Groq safety classification
        # ====================================================

        guardrail_chain = (
            ChatPromptTemplate.from_messages([("human", "{prompt}")])
            | client
            | StrOutputParser()
        )
        result = guardrail_chain.invoke({"prompt": prompt}).strip().upper()

        allowed = result == "ALLOW"

        # ====================================================
        # Record result in Langfuse
        # ====================================================

        guardrail_trace.update(
            output={
                "classification": result,
                "allowed": allowed
            }
        )

        return allowed