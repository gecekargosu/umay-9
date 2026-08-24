"""Optional Gemini adapter. Importing this module does not require a key.

UMAY core does not depend on Gemini; Ollama remains the default local engine.
"""
import os

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


def ask_gemini(prompt: str) -> str:
    if not API_KEY:
        return "Gemini API anahtarı tanımlı değil. Bu modül isteğe bağlıdır."
    from google import genai
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text or ""


if __name__ == "__main__":
    print("UMAY Gemini Agent")
    soru = input("Sen: ")
    print("\nGemini:")
    print(ask_gemini(soru))
