from ..azure_clients import get_openai_client

class TranslationError(Exception):
    pass

def translate_text(text: str, to_lang: str, from_lang: str) -> str:
    """Translate text using OpenAI."""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following text from {from_lang} to {to_lang}. Maintain the original meaning and tone."},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        translated = response.choices[0].message.content.strip()
        return translated
    except Exception as e:
        raise TranslationError(f"Translation failed: {str(e)}")