import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env")

genai.configure(api_key=GEMINI_API_KEY)

def translate(text, from_lang="he", to_lang="en"):
    # Use Gemini to translate text from Hebrew to English
    prompt = f"Translate the following text from Hebrew to English. Only output the translation, no explanation.\n\nText: {text}"
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    # The response.text contains the translation
    return response.text.strip()

if __name__ == "__main__":
    print(translate("🇮🇱 הגרדיאן: איראן תחשוף הערב טכנולוגיית טילים חדשה ותבחן אותה על ידי ירי מספר טילים לעבר ישראל."))