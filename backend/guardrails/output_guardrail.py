import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def check_output_guardrail(answer: str, relevant_docs: list) -> bool:
    """
    Checks whether the generated answer is supported
    by the retrieved documents.

    Returns:
        True  -> answer is sufficiently grounded
        False -> answer contains unsupported information
    """

    if not answer or not relevant_docs:
        return False

    context = "\n\n".join(
        doc.get("text", "")
        for doc in relevant_docs
        if doc.get("text")
    )

    prompt = f"""
You are an output safety checker for a Talent Acquisition RAG system.

Your job is to determine whether the generated answer is supported
by the retrieved documents.

Retrieved documents:
--------------------
{context}
--------------------

Generated answer:
--------------------
{answer}
--------------------

Rules:

1. Return ALLOW if the answer is supported by the retrieved documents.
2. Return BLOCK if the answer contains information that is not supported
   by the retrieved documents.
3. Do not require the answer to use the exact wording of the documents.
4. Small summaries or reasonable rewording are allowed.
5. If the answer makes up candidate information, companies, skills,
   experience, or other facts not present in the documents, return BLOCK.
6. Return ONLY:
   ALLOW
   or
   BLOCK
"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL"),
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    result = response.choices[0].message.content.strip().upper()

    return result == "ALLOW"
