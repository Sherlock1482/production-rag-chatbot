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

There are two possible evidence sources:

1. Retrieved TA documents from Qdrant
2. Live interview data from the MCP tool connected to Google Calendar

Available evidence:
--------------------
{context}
--------------------

Generated answer:
--------------------
{answer}
--------------------

IMPORTANT SOURCE PRIORITY RULES:

1. For questions about interview schedules, interview dates,
   interview times, interview stages, interviewers, interview
   locations, or meeting links, the MCP Interview Data is the
   authoritative source.

2. If the MCP Interview Data contains the requested candidate
   and interview information, the answer MUST be considered
   supported by evidence.

3. Do NOT require the candidate's interview information to also
   appear in the Qdrant documents.

4. Qdrant documents may contain unrelated candidate information.
   Do NOT block an answer merely because the Qdrant documents
   do not contain the candidate mentioned in the MCP data.

5. For interview questions, ignore unrelated Qdrant candidate
   records when deciding whether the interview answer is grounded.

6. For candidate skills, experience, education, qualifications,
   or job requirements, use the Qdrant documents as evidence.

7. MCP interview data is valid evidence for interview-related
   questions.

8. Qdrant documents are valid evidence for document-related
   questions.

9. Return ALLOW if the generated answer is supported by either
   valid MCP evidence or valid Qdrant evidence.

10. Return BLOCK if the answer contains information that is not
    supported by any available evidence.

11. Small summaries or reasonable rewording are allowed.

12. Do not require the answer to use the exact wording of the
    evidence.

13. Never invent candidate information, skills, experience,
    interview dates, interview stages, interviewers, locations,
    or meeting links.

14. If MCP contains a matching interview record, information
    such as the candidate name, date, time, role, stage, and
    interviewer may be used in the answer if present in MCP.

Return ONLY:
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
        result = guardrail_chain.invoke(
            {"prompt": prompt}
        ).strip().upper()

# The guardrail model may return:
# "ALLOW"
# or "RETURN: ALLOW"
# or a sentence ending with "ALLOW".
#
# We only need to determine whether it explicitly
# contains the final ALLOW decision.

        print("\n========== OUTPUT GUARDRAIL ==========")
        print("Guardrail result:", result)
        print("======================================\n")

        allowed = "ALLOW" in result and "BLOCK" not in result

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