"""Lazy LLM construction shared by optimization and the example notebook."""
import os


def init_llm(model: str | None = None, temperature: float = 0.5):
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()
    key = (os.getenv("OPENAI_API_KEY") or os.getenv("FP2MP_API_KEY")
           or os.getenv("CHAT_API_KEY") or os.getenv("API_KEY"))
    name = (model or os.getenv("URBANOMY_LLM_MODEL") or os.getenv("FP2MP_MODEL")
            or os.getenv("CHAT_MODEL") or os.getenv("MODEL_NAME"))
    if not key:
        raise ValueError("LLM_NOT_CONFIGURED: set OPENAI_API_KEY or API_KEY, or use_llm=false.")
    if not name:
        raise ValueError("LLM_NOT_CONFIGURED: set URBANOMY_LLM_MODEL.")
    return ChatOpenAI(
        model=name,
        api_key=key,
        base_url=(os.getenv("OPENAI_BASE_URL") or os.getenv("FP2MP_CHAT_URL")
                  or os.getenv("CHAT_URL") or None),
        temperature=temperature,
        timeout=60,
        max_retries=1,
    )
