import os

from dotenv import load_dotenv
from google import genai


# Load .env
load_dotenv()

# Read Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. "
        "Please add it to your .env file."
    )


# Create Gemini client
client = genai.Client(api_key=API_KEY)


# Models
FAST_MODEL = "gemini-3.5-flash-lite"
SMART_MODEL = "gemini-3.8-flash"


def generate_text(prompt, model=FAST_MODEL):
    """
    Send a prompt to Gemini.

    If the selected model is temporarily unavailable,
    automatically try the fallback model.
    """

    models_to_try = [model]

    # Add fallback only when the first model isn't already the fast model
    if model != FAST_MODEL:
        models_to_try.append(FAST_MODEL)

    last_error = None

    for selected_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=selected_model,
                contents=prompt,
            )

            if response.text:
                return response.text

            last_error = RuntimeError(
                f"{selected_model} returned an empty response."
            )

        except Exception as error:
            last_error = error

            # Try the next model automatically
            continue

    raise RuntimeError(
        f"All available Gemini models failed. Last error: {last_error}"
    )