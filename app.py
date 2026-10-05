"""
Learn AI - AI Personalized Learning Assistant (UI version)

Run with:  streamlit run app.py

Session-state architecture (ready for a real backend later):
    chats            dict   chat_id -> {id, title, created_at, module, option,
                                        messages, documents, pending}
    chat_order       list   chat ids, newest first
    active_chat_id   str    currently opened chat (None = new-chat home screen)
    module_pills     str    module chosen on the home screen (widget state)
    module_options   dict   module -> last selected option

The module / option chips are shown ONLY on the new-chat home screen. When the
first message is sent, the chosen module and option are stored on the chat and
the chips are hidden for the rest of that conversation.
"""

import html
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from backend.database import (
    init_db,
    save_chat,
    load_chats,
    delete_chat as delete_chat_db,
    save_message,
    load_messages,
    save_document,
    load_documents,
)
from backend.gemini import generate_text, FAST_MODEL, SMART_MODEL
from backend.prompts import (
    build_prompt,
    build_pdf_prompt,
    build_study_plan_prompt,
)
from backend.rag import (
    build_document_index,
    retrieve_from_documents,
    build_context,
    format_sources,
    save_document_index,
    load_document_index,
)

st.set_page_config(
    page_title="Learn AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
TAGLINE = "Your personalized AI learning assistant"
GREETING = "What do you want to learn today?"
SUPPORT_TEXT = (
    "Learn concepts, prepare for exams, study smarter, "
    "and learn from your study materials."
)
COMPOSER_PLACEHOLDER = "Ask anything you want to learn, or attach a PDF…"
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "Learn AI logo.png"

# PDF / study material is NOT a module chip: it is handled only through the
# paperclip attachment inside the chat composer.
MODULES = {
    "Tutor": {
        "icon": "📚",
        "hint": "Clear explanations matched to your level.",
        "options": ["Beginner", "Intermediate", "Advanced"],
        "default_option": "Beginner",
    },
    "Exam": {
        "icon": "📝",
        "hint": "Exam-ready answers and MCQs.",
        "options": ["2 Mark", "3 Mark", "5 Mark", "10 Mark", "15 Mark", "MCQ"],
        "default_option": "5 Mark",
    },
    "Study": {
        "icon": "📖",
        "hint": "Notes, summaries, flashcards, practice questions and study plans.",
        "options": [
            "Notes",
            "Summary",
            "Flashcards",
            "Practice Questions",
            "Study Planner",
        ],
        "default_option": "Notes",
    },
}
DEFAULT_MODULE = "Tutor"

OPTION_DESCRIPTIONS = {
    "Beginner": "a simple, jargon-free explanation with everyday analogies",
    "Intermediate": "a structured explanation with key terms and worked examples",
    "Advanced": "an in-depth, technically rigorous explanation",
    "2 Mark": "a crisp 2-mark answer",
    "3 Mark": "a short 3-mark answer with the key points",
    "5 Mark": "a structured 5-mark answer",
    "10 Mark": "a detailed 10-mark answer with headings and examples",
    "15 Mark": "a comprehensive 15-mark answer",
    "MCQ": "multiple-choice questions with answers and explanations",
    "Notes": "well-organised study notes",
    "Summary": "a concise summary of the key ideas",
    "Flashcards": "question-and-answer flashcards",
    "Practice Questions": "practice questions to test your understanding",
}

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
CSS = """
<style>
:root {
  --la-bg: #0c0d0f;
  --la-sidebar: #111215;
  --la-surface: #15161a;
  --la-surface-2: #1b1c21;
  --la-surface-3: #23242a;
  --la-border: #2a2c32;
  --la-border-strong: #3b3e46;
  --la-text: #ececf0;
  --la-text-dim: #b6b9c2;
  --la-muted: #868a95;
  --la-accent: #6cc3b0;
  --la-accent-soft: rgba(108, 195, 176, 0.12);
  --la-accent-line: rgba(108, 195, 176, 0.45);
}

/* =====================================================================
   APP SHELL
   ===================================================================== */
html, body { background: var(--la-bg) !important; }
.stApp, [data-testid="stApp"] {
  background:
    radial-gradient(900px 420px at 50% -90px, rgba(108, 195, 176, 0.11), transparent 70%),
    radial-gradient(620px 320px at 92% 8%, rgba(91, 155, 213, 0.06), transparent 70%),
    var(--la-bg) !important;
  color: var(--la-text);
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }

html, body, .stApp, .stApp button, .stApp input, .stApp textarea,
.stApp [data-testid="stMarkdownContainer"] {
  font-family: "Inter", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif !important;
}
::selection { background: rgba(108, 195, 176, 0.3); }

[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent !important; }
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stToolbarActions"],
footer { display: none !important; }

/* Sidebar open / close controls: always reachable */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] button { color: var(--la-text-dim) !important; }
[data-testid="stExpandSidebarButton"] {
  background: var(--la-surface) !important;
  border: 1px solid var(--la-border) !important;
  border-radius: 10px !important;
}

[data-testid="stMainBlockContainer"], .block-container {
  max-width: 820px !important;
  padding: 2rem 1.5rem 9rem 1.5rem !important;
}

/* =====================================================================
   TYPOGRAPHY
   ===================================================================== */
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stMarkdownContainer"] strong,
.stApp [data-testid="stMarkdownContainer"] em,
.stApp [data-testid="stMarkdownContainer"] h1,
.stApp [data-testid="stMarkdownContainer"] h2,
.stApp [data-testid="stMarkdownContainer"] h3,
.stApp [data-testid="stMarkdownContainer"] h4,
.stApp label { color: var(--la-text); }
.stApp [data-testid="stMarkdownContainer"] h1,
.stApp [data-testid="stMarkdownContainer"] h2,
.stApp [data-testid="stMarkdownContainer"] h3 { letter-spacing: -0.01em; font-weight: 650; }
.stApp [data-testid="stMarkdownContainer"] blockquote {
  border-left: 3px solid var(--la-accent-line);
  color: var(--la-text-dim);
  padding-left: .9rem;
  margin: .2rem 0;
}
.stApp [data-testid="stMarkdownContainer"] code {
  background: var(--la-surface-3);
  color: var(--la-text);
  border-radius: 6px;
}
.stApp [data-testid="stMarkdownContainer"] table { border-collapse: collapse; width: 100%; }
.stApp [data-testid="stMarkdownContainer"] th,
.stApp [data-testid="stMarkdownContainer"] td {
  border: 1px solid var(--la-border); padding: .5rem .75rem; color: var(--la-text);
}
.stApp [data-testid="stMarkdownContainer"] th { background: var(--la-surface-2); }
.stApp [data-testid="stCode"], .stApp pre {
  background: var(--la-surface-2) !important;
  border: 1px solid var(--la-border);
  border-radius: 12px;
}
.stApp hr, .stApp [data-testid="stDivider"] hr { border-color: var(--la-border) !important; }
.stApp [data-testid="stSpinner"], .stApp [data-testid="stSpinner"] * { color: var(--la-muted) !important; }

/* =====================================================================
   SIDEBAR
   ===================================================================== */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
  background: var(--la-sidebar) !important;
}
[data-testid="stSidebar"] { border-right: 1px solid var(--la-border); }
[data-testid="stSidebarHeader"] { height: 2.4rem !important; min-height: 0 !important; padding-bottom: 0 !important; }
[data-testid="stSidebarUserContent"] { padding: .4rem 1rem 1.2rem 1rem !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .4rem; }

/* make every sidebar control span the full column width */
[data-testid="stSidebar"] [data-testid="stElementContainer"],
[data-testid="stSidebar"] .stButton,
[data-testid="stSidebar"] [data-testid="stButton"] { width: 100% !important; }
[data-testid="stSidebar"] .stButton button { width: 100% !important; }

.stApp .la-side-brand { display: flex; align-items: center; gap: .75rem; padding: .3rem .2rem 1rem; }
.stApp .la-logo-img {
  width: 42px;
  height: 42px;
  object-fit: contain;
  flex: 0 0 42px;
  border-radius: 11px;
  display: block;
  filter: drop-shadow(0 4px 12px rgba(94, 231, 255, 0.14));
}
.stApp .la-side-brand { align-items: center; }
.stApp .la-logo {
  width: 40px; height: 40px; border-radius: 12px; flex: 0 0 40px;
  display: grid; place-items: center; font-size: 1.3rem;
  background: linear-gradient(135deg, rgba(108, 195, 176, 0.38), rgba(91, 155, 213, 0.26));
  border: 1px solid var(--la-accent-line);
}
.stApp .la-side-name {
  font-size: 1.12rem;
  font-weight: 700;
  color: var(--la-text);
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.stApp .la-side-sub {
  font-size: .73rem;
  color: var(--la-muted);
  margin-top: 3px;
  line-height: 1.3;
}
.stApp .la-side-label {
  display: flex;
  align-items: center;
  justify-content: space-between;

  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .1em;
  font-weight: 650;
  color: var(--la-muted);

  padding: 1.2rem .35rem .55rem;
  margin-bottom: .35rem;

  position: relative;
}
.stApp .la-side-label::after {
  content: "";
  position: absolute;
  left: .35rem;
  right: .35rem;
  bottom: 0;

  height: 1px;
  background: var(--la-border);
  opacity: .65;
}
.stApp .la-count {
  background: var(--la-surface-3); color: var(--la-text-dim);
  border-radius: 999px; padding: 1px 8px; font-size: .68rem; letter-spacing: 0;
}
.stApp .la-side-empty {
  text-align: center; color: var(--la-muted); font-size: .86rem;
  border: 1px dashed var(--la-border-strong); border-radius: 14px; padding: 1.1rem .8rem;
}
.stApp .la-side-empty-icon { font-size: 1.4rem; margin-bottom: .25rem; filter: grayscale(.6); }
.stApp .la-side-empty small { display: block; margin-top: .25rem; font-size: .76rem; color: var(--la-muted); }

/* =====================================================================
   BUTTONS
   ===================================================================== */
.stApp .stButton button {
  border-radius: 12px;
  border: 1px solid var(--la-border);
  background: var(--la-surface-2);
  color: var(--la-text-dim);
  font-weight: 500;
  transition: background .15s ease, border-color .15s ease, color .15s ease, transform .1s ease;
}
.stApp .stButton button:hover {
  background: var(--la-surface-3);
  border-color: var(--la-border-strong);
  color: var(--la-text);
}
.stApp .stButton button:focus,
.stApp .stButton button:active { outline: none !important; box-shadow: none !important; }
.stApp .stButton button:focus-visible { box-shadow: 0 0 0 3px var(--la-accent-soft) !important; }
.stApp .stButton button p, .stApp .stButton button span { color: inherit !important; }

.stApp .stButton button[data-testid="stBaseButton-primary"],
.stApp .stButton button[kind="primary"] {
  background: var(--la-accent) !important;
  border-color: var(--la-accent) !important;
  color: #06201a !important;
  font-weight: 650;
}
.stApp .stButton button[data-testid="stBaseButton-primary"]:hover,
.stApp .stButton button[kind="primary"]:hover { filter: brightness(1.07); }

.st-key-new_chat_wrap button {
  min-height: 2.7rem;
  justify-content: center;
  font-weight: 650 !important;
  color: var(--la-text) !important;
  background: linear-gradient(135deg, rgba(108, 195, 176, 0.24), rgba(108, 195, 176, 0.09)) !important;
  border: 1px solid var(--la-accent-line) !important;
}
.st-key-new_chat_wrap button:hover { filter: brightness(1.12); }

/* =====================================================================
   CHAT HISTORY ROWS
   ===================================================================== */
[class*="st-key-hist_row_"] {
  border-radius: 12px;
  border: 1px solid transparent;
  transition: background .15s ease, border-color .15s ease;
}
[class*="st-key-hist_row_"] {
  margin-top: .35rem;
}
[class*="st-key-hist_row_"]:hover { background: var(--la-surface-2); }
[class*="st-key-hist_row_active_"] {
  background: var(--la-surface-3);
  border-color: var(--la-border-strong);
  box-shadow: inset 3px 0 0 var(--la-accent);
}
[class*="st-key-hist_row_"] [data-testid="stVerticalBlock"] { gap: 0; }
[class*="st-key-hist_row_"] [data-testid="stHorizontalBlock"] {
  gap: .15rem !important;
  align-items: center !important;
  flex-wrap: nowrap !important;
}
[class*="st-key-hist_row_"] [data-testid="stColumn"]:first-child,
[class*="st-key-hist_row_"] [data-testid="column"]:first-child {
  flex: 1 1 0 !important; width: auto !important; min-width: 0 !important;
}
[class*="st-key-hist_row_"] [data-testid="stColumn"]:last-child,
[class*="st-key-hist_row_"] [data-testid="column"]:last-child {
  flex: 0 0 2.3rem !important; width: 2.3rem !important; min-width: 2.3rem !important;
}
[class*="st-key-hist_row_"] .stButton button {
  background: transparent !important;
  border-color: transparent !important;
  box-shadow: none !important;
  justify-content: flex-start;
  text-align: left;
  min-height: 2.5rem;
}
[class*="st-key-hist_row_"] .stButton button:hover { background: transparent !important; color: var(--la-text) !important; }
[class*="st-key-hist_row_active_"] .stButton button { color: var(--la-text) !important; }
[class*="st-key-hist_row_"] .stButton button [data-testid="stMarkdownContainer"] { width: 100%; }
[class*="st-key-hist_row_"] .stButton button p {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; font-size: .92rem;
}
[class*="st-key-del_"] button {
  padding: 0 !important; min-width: 0 !important; width: 2.2rem !important;
  justify-content: center !important; opacity: .5;
}
[class*="st-key-del_"] button p { filter: grayscale(1) brightness(1.5); font-size: .92rem; }
[class*="st-key-del_"] button:hover { opacity: 1; background: rgba(255, 110, 110, 0.12) !important; }

/* =====================================================================
   PILLS: module segmented control + option chips
   ===================================================================== */
.stApp [data-testid="stButtonGroup"] button {
  border-radius: 999px !important;
  background: var(--la-surface) !important;
  border: 1px solid var(--la-border) !important;
  color: var(--la-text-dim) !important;
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.stApp [data-testid="stButtonGroup"] button:hover {
  background: var(--la-surface-3) !important;
  border-color: var(--la-border-strong) !important;
  color: var(--la-text) !important;
}
.stApp [data-testid="stButtonGroup"] button:focus,
.stApp [data-testid="stButtonGroup"] button:active { outline: none !important; box-shadow: none !important; }
.stApp [data-testid="stButtonGroup"] button:focus-visible { box-shadow: 0 0 0 3px var(--la-accent-soft) !important; }
.stApp [data-testid="stButtonGroup"] button p,
.stApp [data-testid="stButtonGroup"] button span { color: inherit !important; }

.st-key-module_bar_home,
.st-key-option_bar_home,
.st-key-module_bar_home [data-testid="stVerticalBlock"],
.st-key-option_bar_home [data-testid="stVerticalBlock"] { align-items: center; }

/* module chips: segmented control */
.st-key-module_bar_home [data-testid="stButtonGroup"] {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 4px;
  width: fit-content; max-width: 100%; margin: 0 auto;
  padding: 5px; border-radius: 999px;
  background: var(--la-surface); border: 1px solid var(--la-border);
}
.st-key-module_bar_home [data-testid="stButtonGroup"] button {
  background: transparent !important;
  border: 1px solid transparent !important;
  padding: .5rem 1.4rem !important;
  font-size: .95rem; font-weight: 600;
}
.st-key-module_bar_home [data-testid="stButtonGroup"] button:hover { background: var(--la-surface-3) !important; }
.st-key-module_bar_home [data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"],
.st-key-module_bar_home [data-testid="stButtonGroup"] button[kind="pillsActive"],
.st-key-module_bar_home [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-module_bar_home [data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: var(--la-accent) !important;
  border-color: transparent !important;
  color: #06201a !important;
  box-shadow: 0 4px 16px rgba(108, 195, 176, 0.28) !important;
}

/* option chips */
.st-key-option_bar_home [data-testid="stButtonGroup"] {
  display: flex; flex-wrap: wrap; justify-content: center; gap: .45rem;
  width: fit-content; max-width: 100%; margin: 0 auto;
}
/* ---------- Smooth option pills ---------- */

.st-key-option_bar_home [data-testid="stButtonGroup"] button {
  background: transparent !important;
  font-size: .84rem;
  font-weight: 500;
  padding: .3rem .95rem !important;

  transform: translateY(0) scale(1);
  transition:
    background .22s ease,
    border-color .22s ease,
    color .22s ease,
    transform .22s cubic-bezier(.2,.8,.2,1),
    box-shadow .22s ease;
}

.st-key-option_bar_home [data-testid="stButtonGroup"] button:hover {
  background: var(--la-surface-2) !important;
  transform: translateY(-1px);
}

.st-key-option_bar_home
[data-testid="stButtonGroup"]
button[data-testid="stBaseButton-pillsActive"],
.st-key-option_bar_home
[data-testid="stButtonGroup"]
button[kind="pillsActive"],
.st-key-option_bar_home
[data-testid="stButtonGroup"]
button[aria-checked="true"],
.st-key-option_bar_home
[data-testid="stButtonGroup"]
button[aria-pressed="true"] {
  background: var(--la-accent-soft) !important;
  border-color: var(--la-accent) !important;
  color: #d9f4ed !important;

  transform: translateY(-1px) scale(1.025);

  box-shadow:
    0 4px 14px rgba(108, 195, 176, 0.16);

  animation: la-option-select .22s ease-out;
}

/* Selected option animation */

@keyframes la-option-select {
  0% {
    transform: translateY(0) scale(.96);
    opacity: .72;
  }

  60% {
    transform: translateY(-1px) scale(1.035);
    opacity: 1;
  }

  100% {
    transform: translateY(-1px) scale(1.025);
  }
}

.st-key-module_bar_home
[data-testid="stButtonGroup"]
button[data-testid="stBaseButton-pillsActive"],
.st-key-module_bar_home
[data-testid="stButtonGroup"]
button[kind="pillsActive"],
.st-key-module_bar_home
[data-testid="stButtonGroup"]
button[aria-checked="true"],
.st-key-module_bar_home
[data-testid="stButtonGroup"]
button[aria-pressed="true"] {
  animation: la-module-select .22s ease-out;
}

@keyframes la-module-select {
  0% {
    transform: scale(.96);
  }

  60% {
    transform: scale(1.035);
  }

  100% {
    transform: scale(1);
  }
}

.st-key-module_bar_home { margin-top: .4rem; }

.stApp .la-mode-note {
  display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: .5rem;
  margin-top: .7rem; font-size: .86rem; color: var(--la-muted); text-align: center;
}
.stApp .la-mode-note b { color: var(--la-text-dim); font-weight: 600; }

/* =====================================================================
   HERO
   ===================================================================== */
.stApp .la-hero { text-align: center; margin: clamp(.5rem, 5vh, 3.5rem) auto 1.4rem; max-width: 720px; }
.stApp .la-brand {
  display: inline-flex; align-items: center; gap: .6rem;
  padding: .35rem 1.05rem .35rem .4rem;
  border: 1px solid var(--la-border); border-radius: 999px;
  background: rgba(255, 255, 255, 0.03);
  font-size: .98rem; font-weight: 650; letter-spacing: .01em; color: var(--la-text);
}
.stApp .la-brand-icon {
  width: 1.9rem; height: 1.9rem; border-radius: 50%;
  display: inline-grid; place-items: center; font-size: 1rem;
  background: linear-gradient(135deg, rgba(108, 195, 176, 0.38), rgba(91, 155, 213, 0.26));
  border: 1px solid var(--la-accent-line);
}
.stApp .la-hero-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
  display: block;
  filter: drop-shadow(0 4px 12px rgba(94, 231, 255, 0.14));
}
.stApp .la-tagline { margin-top: .95rem; color: var(--la-muted); font-size: .95rem; }
.stApp .la-greeting {
  margin: 1rem 0 .75rem;
  font-size: clamp(1.9rem, 4.2vw, 2.7rem);
  font-weight: 700; line-height: 1.12; letter-spacing: -0.025em;
  background: linear-gradient(180deg, #ffffff 35%, #98a1ab 140%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}
.stApp .la-support {
  color: var(--la-muted); font-size: 1rem; line-height: 1.6;
  max-width: 540px; margin: 0 auto;
}
.stApp .la-footnote { text-align: center; color: var(--la-muted); font-size: .8rem; margin-top: .3rem; }

/* =====================================================================
   COMPOSER (st.chat_input)
   ===================================================================== */
[data-testid="stChatInput"] {
  background: var(--la-surface) !important;
  border: 1px solid var(--la-border-strong) !important;
  border-radius: 20px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.03);
  transition: border-color .15s ease, box-shadow .15s ease;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--la-accent-line) !important;
  box-shadow: 0 0 0 3px var(--la-accent-soft), 0 12px 40px rgba(0, 0, 0, 0.45);
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
  color: var(--la-text) !important;
  background: transparent !important;
  caret-color: var(--la-accent);
  font-size: 1rem;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--la-muted) !important; opacity: 1; }
[data-testid="stChatInputSubmitButton"] { border-radius: 12px !important; }
[data-testid="stChatInputSubmitButton"]:not(:disabled) {
  background: var(--la-accent) !important;
  color: #08221c !important;
}
[data-testid="stChatInputSubmitButton"]:not(:disabled) svg { color: #08221c !important; fill: #08221c !important; }

/* Attachment button: paperclip icon instead of "+" */
button[data-testid="stChatInputFileUploadButton"] > *,
[data-testid="stChatInputFileUploadButton"] button > *,
[data-testid="stChatInput"] button[aria-label*="ttach" i] > *,
[data-testid="stChatInput"] button[aria-label*="pload" i] > * { display: none !important; }
button[data-testid="stChatInputFileUploadButton"]::before,
[data-testid="stChatInputFileUploadButton"] button::before,
[data-testid="stChatInput"] button[aria-label*="ttach" i]::before,
[data-testid="stChatInput"] button[aria-label*="pload" i]::before {
  content: "";
  display: block;
  width: 20px; height: 20px;
  background-color: var(--la-muted);
  -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'/%3E%3C/svg%3E") center / contain no-repeat;
}
button[data-testid="stChatInputFileUploadButton"]:hover::before,
[data-testid="stChatInputFileUploadButton"] button:hover::before,
[data-testid="stChatInput"] button[aria-label*="ttach" i]:hover::before,
[data-testid="stChatInput"] button[aria-label*="pload" i]:hover::before { background-color: var(--la-accent); }

.st-key-home_composer { max-width: 760px; width: 100%; margin: .6rem auto 0; }
.st-key-home_composer [data-testid="stChatInput"] textarea { min-height: 52px; }

[data-testid="stBottom"], [data-testid="stBottom"] > div { background: var(--la-bg) !important; }
[data-testid="stBottomBlockContainer"] {
  max-width: 820px !important;
  margin: 0 auto;
  padding: 1rem 1.5rem 1.6rem 1.5rem !important;
}

/* =====================================================================
   CONVERSATION
   ===================================================================== */
.stApp .la-chat-title {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding-bottom: .85rem; margin-bottom: 1.1rem;
  border-bottom: 1px solid var(--la-border);
}
.stApp .la-chat-name {
  font-size: 1.1rem; font-weight: 650; color: var(--la-text); letter-spacing: -0.01em;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.stApp .la-chat-title .la-badge { white-space: nowrap; flex: 0 0 auto; }
.stApp .la-badge {
  display: inline-block; font-size: .76rem; padding: .22rem .75rem; border-radius: 999px;
  background: var(--la-accent-soft); border: 1px solid var(--la-accent-line); color: #cfeee6;
}

[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: .6rem 0 !important;
  gap: .85rem;
}
[data-testid="stChatMessage"] p { line-height: 1.7; font-size: .98rem; }
[data-testid="stChatMessageAvatarAssistant"] {
  background: linear-gradient(135deg, rgba(108, 195, 176, 0.32), rgba(91, 155, 213, 0.22)) !important;
  border: 1px solid var(--la-accent-line);
}
/* user messages: compact bubble aligned to the right */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  flex-direction: row-reverse;
  width: fit-content;
  max-width: 86%;
  margin-left: auto;
  padding: .75rem 1.1rem !important;
  background: var(--la-surface-2) !important;
  border: 1px solid var(--la-border) !important;
  border-radius: 18px 18px 6px 18px;
}
[data-testid="stChatMessageAvatarUser"] { display: none !important; }

.stApp .la-files { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .5rem; }
.stApp .la-file {
  display: inline-flex; align-items: center; gap: .4rem; font-size: .8rem;
  padding: .28rem .75rem; border-radius: 999px;
  background: var(--la-surface-3); border: 1px solid var(--la-border); color: var(--la-text-dim);
}
.stApp .la-file-size { color: var(--la-muted); }

/* =====================================================================
   WIDGETS (inputs, selects, expanders, radios, alerts)
   ===================================================================== */
[data-testid="stWidgetLabel"] p {
  color: var(--la-text-dim) !important; font-size: .84rem; font-weight: 600;
}
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stTextArea"] [data-baseweb="textarea"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: var(--la-surface-2) !important;
  border: 1px solid var(--la-border) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
[data-testid="stNumberInput"] [data-baseweb="input"]:focus-within,
[data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
[data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--la-accent-line) !important;
  box-shadow: 0 0 0 3px var(--la-accent-soft) !important;
}
[data-testid="stTextInput"] [data-baseweb="base-input"],
[data-testid="stNumberInput"] [data-baseweb="base-input"],
[data-testid="stDateInput"] [data-baseweb="base-input"] { background: transparent !important; }
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {
  color: var(--la-text) !important;
  background: transparent !important;
  -webkit-text-fill-color: var(--la-text);
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: var(--la-muted) !important; -webkit-text-fill-color: var(--la-muted); opacity: 1; }
[data-testid="stSelectbox"] [data-baseweb="select"] div { color: var(--la-text); }
[data-testid="stNumberInput"] button {
  background: transparent !important; color: var(--la-text-dim) !important; border: none !important;
}
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul {
  background: var(--la-surface-2) !important;
  border: 1px solid var(--la-border);
  border-radius: 12px;
}
[data-baseweb="popover"] li { color: var(--la-text) !important; background: transparent !important; }
[data-baseweb="popover"] li:hover { background: var(--la-surface-3) !important; }
[data-baseweb="calendar"] { background: var(--la-surface-2) !important; }

[data-testid="stExpander"] {
  border: 1px solid var(--la-border) !important;
  border-radius: 14px !important;
  background: var(--la-surface) !important;
  overflow: hidden;
  margin-bottom: .4rem;
}
[data-testid="stExpander"] details { border: none !important; background: transparent !important; }
[data-testid="stExpander"] summary { padding: .8rem 1rem; }
[data-testid="stExpander"] summary:hover { background: var(--la-surface-2); }
[data-testid="stExpander"] summary p { color: var(--la-text) !important; font-weight: 600; }

[data-testid="stRadio"] [role="radiogroup"] { gap: .5rem; }
[data-testid="stRadio"] label[data-baseweb="radio"] {
  width: 100%; margin: 0; padding: .65rem .9rem; border-radius: 12px;
  background: var(--la-surface-2); border: 1px solid var(--la-border);
  transition: border-color .15s ease, background .15s ease;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:hover { border-color: var(--la-border-strong); }
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
  border-color: var(--la-accent-line); background: var(--la-accent-soft);
}
[data-testid="stRadio"] label[data-baseweb="radio"] p { color: var(--la-text) !important; }

[data-testid="stAlert"] {
  background: var(--la-surface-2) !important;
  border: 1px solid var(--la-border);
  border-radius: 12px;
}

/* =====================================================================
   STUDY PLANNER
   ===================================================================== */
.st-key-planner_card {
  width: 100%; max-width: 760px; margin: .6rem auto 0;
  background: var(--la-surface);
  border: 1px solid var(--la-border);
  border-radius: 20px;
  padding: 1.6rem 1.7rem 1.8rem;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  gap: 1rem;
}
.st-key-planner_card .stButton,
.st-key-planner_card [data-testid="stButton"],
.st-key-planner_card [data-testid="stElementContainer"] { width: 100% !important; }
.st-key-planner_card .stButton button { width: 100% !important; min-height: 2.9rem; }
.stApp .la-planner-head { display: flex; align-items: center; gap: .9rem; margin-bottom: .3rem; }
.stApp .la-planner-icon {
  width: 46px; height: 46px; border-radius: 14px; flex: 0 0 46px;
  display: grid; place-items: center; font-size: 1.4rem;
  background: linear-gradient(135deg, rgba(108, 195, 176, 0.3), rgba(91, 155, 213, 0.2));
  border: 1px solid var(--la-accent-line);
}
.stApp .la-planner-title { font-size: 1.25rem; font-weight: 700; color: var(--la-text); letter-spacing: -0.01em; }
.stApp .la-planner-sub { font-size: .9rem; color: var(--la-muted); margin-top: 2px; line-height: 1.5; }
.st-key-plan_result {
  width: 100%; max-width: 760px; margin: 1rem auto 0;
  background: var(--la-surface);
  border: 1px solid var(--la-border);
  border-radius: 20px;
  padding: 1.4rem 1.7rem;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--la-surface-3); border-radius: 10px; }
::-webkit-scrollbar-track { background: transparent; }

@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1.5rem 1rem 9rem 1rem !important; }
  [data-testid="stBottomBlockContainer"] { padding: .8rem 1rem 1.2rem 1rem !important; }
  .stApp .la-hero { margin-top: .5rem; }
  .st-key-module_bar_home [data-testid="stButtonGroup"] button { padding: .45rem 1rem !important; }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { max-width: 94%; }
  .st-key-planner_card { padding: 1.2rem 1.1rem 1.4rem; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def mode_label(module, option):
    if not module or module not in MODULES:
        return ""
    label = f"{MODULES[module]['icon']} {module}"
    if option:
        label += f" · {option}"
    return label


def files_html(attachments):
    if not attachments:
        return ""
    chips = "".join(
        f'<span class="la-file">📄 {html.escape(a["name"])} '
        f'<span class="la-file-size">{format_size(a["size"])}</span></span>'
        for a in attachments
    )
    return f'<div class="la-files">{chips}</div>'


def parse_submission(submission):
    """Normalise the value returned by st.chat_input(accept_file=True)."""
    if submission is None:
        return "", []
    if isinstance(submission, str):
        return submission.strip(), []
    text = getattr(submission, "text", None)
    files = getattr(submission, "files", None)
    if isinstance(submission, dict):
        if text is None:
            text = submission.get("text", "")
        if files is None:
            files = submission.get("files", [])
    return (text or "").strip(), list(files or [])


# ----------------------------------------------------------------------------
# Automatic chat-title generation (offline heuristic; swap for an LLM later)
# ----------------------------------------------------------------------------
_LEADING_PHRASES = sorted(
    [
        "can you please", "could you please", "can you", "could you", "would you", "will you",
        "please", "kindly", "hey", "hello", "hi",
        "i want to learn about", "i want to learn", "i want to understand", "i want to know about",
        "i need to learn about", "i need to learn", "help me understand", "help me with",
        "explain to me", "explain", "describe", "define", "discuss", "summarize", "summarise",
        "elaborate on", "elaborate", "teach me about", "teach me", "tell me about", "tell me",
        "what is", "what are", "what was", "what were", "what's", "whats", "who is", "who was",
        "how does", "how do", "how did", "how is", "how are", "how can i", "how can", "how to",
        "why is", "why are", "why does", "why do",
        "give me", "show me", "generate", "create", "make", "write", "solve", "derive", "compare",
        "the", "a", "an", "about", "some",
    ],
    key=len,
    reverse=True,
)
_TOPIC_PREFIX = re.compile(
    r"^(?:\d+\s*[- ]?\s*(?:marks?)?\s*)?(?:short\s+)?"
    r"(?:notes|summary|summaries|questions?|answers?|mcqs?|flashcards?|practice\s+questions?)"
    r"\s+(?:on|about|for|of)\s+",
    re.IGNORECASE,
)
_TRAILING_FILLER = re.compile(
    r"\s+(?:in\s+detail|in\s+depth|with\s+examples?|with\s+an?\s+example|"
    r"in\s+simple\s+(?:words|terms|language)|in\s+short|simply|briefly|"
    r"step\s+by\s+step|for\s+beginners|for\s+exams?|please)$",
    re.IGNORECASE,
)
_TRAILING_NOUN = re.compile(r"\s+(?:scores?|metrics?|concepts?|topics?)$", re.IGNORECASE)
_SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "with"}
_ACRONYMS = {
    "ai", "ml", "dl", "nlp", "dbms", "sql", "os", "cpu", "gpu", "api", "html", "css", "http",
    "https", "tcp", "ip", "oop", "oops", "dsa", "cnn", "rnn", "llm", "rag", "pdf", "ui", "ux",
    "iot", "aws", "ide",
}
_SUBJECTS = {"python", "java", "javascript", "c", "c++", "cpp", "react", "django", "flask", "pandas", "numpy", "linux", "git"}


def _strip_leading(text):
    changed = True
    while changed:
        changed = False
        lowered = text.lower()
        for phrase in _LEADING_PHRASES:
            if lowered.startswith(phrase + " "):
                text = text[len(phrase):].lstrip()
                changed = True
                break
    return text


def _smart_title(text):
    out = []
    for index, word in enumerate(text.split()):
        bare = word.lower()
        if bare in _ACRONYMS:
            out.append(bare.upper())
        elif any(ch.isupper() for ch in word):
            out.append(word)
        elif index > 0 and bare in _SMALL_WORDS:
            out.append(bare)
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


def _looks_like_code(token):
    return " " not in token and len(token) <= 4 and any(ch.isdigit() for ch in token)


def _format_topic(topic):
    match = re.match(r"^(.+?)\s+(?:and|&)\s+(.+)$", topic, re.IGNORECASE)
    if not match:
        return _smart_title(topic)
    left, right = match.group(1).strip(), match.group(2).strip()
    if "," in left:
        items = [part.strip() for part in left.split(",") if part.strip()] + [right]
    elif len(left.split()) == 2 and _looks_like_code(right):
        items = left.split() + [right]
    else:
        items = [left, right]
    titled = [_smart_title(item) for item in items]
    if len(titled) == 1:
        return titled[0]
    return ", ".join(titled[:-1]) + " & " + titled[-1]


def _sanitize_title(title, fallback="New Chat"):
    title = re.sub(r"[*_`~$<>\[\]{}|#\\]", "", title)
    title = " ".join(title.split())
    if not title:
        return fallback
    if len(title) > 40:
        title = title[:40].rsplit(" ", 1)[0].rstrip(",&- ") + "…"
    return title


def generate_title(text, fallback="New Chat"):
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return fallback
    topic = re.sub(r"[\"“”]", "", lines[0].strip()[:200])
    topic = _strip_leading(topic)
    topic = _TOPIC_PREFIX.sub("", topic)
    topic = topic.strip(" \t?!.:;,")

    previous = None
    while previous != topic:
        previous = topic
        topic = _TRAILING_FILLER.sub("", topic).strip(" \t?!.:;,")
    trimmed = _TRAILING_NOUN.sub("", topic).strip()
    if trimmed:
        topic = trimmed
    if not topic:
        return fallback

    diff = re.match(r"^(?:the\s+)?differences?\s+between\s+(.+?)\s+and\s+(.+)$", topic, re.IGNORECASE)
    if diff:
        title = f"{_smart_title(diff.group(1))} vs {_smart_title(diff.group(2))}"
    else:
        swap = re.match(r"^(.+?)\s+in\s+([A-Za-z][\w+#.\-]*)$", topic)
        if swap:
            context = swap.group(2)
            if context.isupper() or context.lower() in (_ACRONYMS | _SUBJECTS):
                topic = f"{context} {swap.group(1)}"
        title = _format_topic(topic)

    return _sanitize_title(title, fallback)


def title_from_filename(name):
    stem = re.sub(r"\.pdf$", "", name or "", flags=re.IGNORECASE)
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return _sanitize_title(_smart_title(stem), "PDF Upload") if stem else "PDF Upload"


# ----------------------------------------------------------------------------
# State management
# ----------------------------------------------------------------------------
def init_state():
    ss = st.session_state

    # ---------------------------------------------------------
    # Initialize SQLite and restore saved data
    # ---------------------------------------------------------
    if not ss.get("_db_initialized", False):

        init_db()

        saved_chats = load_chats()

        ss["chats"] = {}
        ss["chat_order"] = []

        base_dir = Path(__file__).resolve().parent

        # -----------------------------------------------------
        # Restore every saved chat
        # -----------------------------------------------------
        for saved_chat in saved_chats:

            chat_id = saved_chat["id"]

            # -------------------------------------------------
            # Restore messages
            # -------------------------------------------------
            messages = load_messages(chat_id)

            # -------------------------------------------------
            # Restore PDF documents
            # -------------------------------------------------
            documents = []

            saved_documents = load_documents(chat_id)

            for document in saved_documents:

                file_path = document.get("file_path")

                pdf_data = None

                # ---------------------------------------------
                # Resolve saved PDF path
                # ---------------------------------------------
                if file_path:

                    saved_file = Path(file_path)

                    # Handle old relative paths
                    if not saved_file.is_absolute():
                        saved_file = base_dir / saved_file

                    if saved_file.exists():
                        pdf_data = saved_file.read_bytes()

                # ---------------------------------------------
                # Find saved RAG cache
                # ---------------------------------------------
                rag_index = None

                if file_path:

                    pdf_path = Path(file_path)

                    if not pdf_path.is_absolute():
                        pdf_path = base_dir / pdf_path

                    cache_path = Path(
                        str(pdf_path) + ".rag.pkl"
                    )

                else:

                    cache_path = None

                # ---------------------------------------------
                # Load cached RAG index
                # ---------------------------------------------
                if cache_path and cache_path.exists():

                    rag_index = load_document_index(
                        cache_path
                    )

                # ---------------------------------------------
                # Build restored document
                # ---------------------------------------------
                restored_document = {
                    "id": document.get("id"),
                    "name": document.get("name"),
                    "size": document.get("size"),
                    "type": (
                        document.get("file_type")
                        or "application/pdf"
                    ),
                    "file_path": file_path,
                    "data": pdf_data,
                    "rag_index": rag_index,
                    "rag_cache_path": (
                        str(cache_path)
                        if cache_path
                        else None
                    ),
                }

                # ---------------------------------------------
                # If cache is missing, don't rebuild automatically
                # ---------------------------------------------
                if pdf_data and rag_index is None:

                    restored_document["rag_error"] = (
                        "RAG cache not found. "
                        "Please upload the PDF again."
                    )

                elif not pdf_data:

                    restored_document["rag_error"] = (
                        "Saved PDF file could not be found."
                    )

                documents.append(restored_document)

            # -------------------------------------------------
            # Recreate chat
            # -------------------------------------------------
            chat = {
                "id": chat_id,
                "title": saved_chat["title"],
                "created_at": saved_chat["created_at"],
                "module": saved_chat.get("module"),
                "option": saved_chat.get("option"),
                "messages": messages,
                "documents": documents,
                "pending": False,
            }

            ss["chats"][chat_id] = chat
            ss["chat_order"].append(chat_id)

        ss["_db_initialized"] = True

    # ---------------------------------------------------------
    # Normal Streamlit session state
    # ---------------------------------------------------------

    ss.setdefault(
        "active_chat_id",
        None,
    )

    ss.setdefault(
        "module_options",
        {
            name: meta["default_option"]
            for name, meta in MODULES.items()
        },
    )

    ss.setdefault(
        "_last_module",
        DEFAULT_MODULE,
    )

    ss.setdefault(
        "module_pills",
        ss["_last_module"],
    )


def get_active_chat():
    cid = st.session_state.active_chat_id
    return st.session_state.chats.get(cid) if cid else None


def create_chat(first_text, files, module, option):
    cid = uuid.uuid4().hex[:10]

    if first_text.strip():
        title = generate_title(first_text)
    elif files:
        title = title_from_filename(files[0].name)
    else:
        title = "New Chat"

    created_at = datetime.now().isoformat(timespec="seconds")

    chat = {
        "id": cid,
        "title": title,
        "created_at": created_at,
        "module": module,
        "option": option,
        "messages": [],
        "documents": [],
        "pending": False,
    }

    # Save chat permanently to SQLite
    save_chat(
        chat_id=cid,
        title=title,
        created_at=created_at,
        module=module,
        option=option,
    )

    st.session_state.chats[cid] = chat
    st.session_state.chat_order.insert(0, cid)
    st.session_state.active_chat_id = cid

    return chat


def start_new_chat():
    st.session_state.active_chat_id = None


def open_chat(cid):
    if cid in st.session_state.chats:
        st.session_state.active_chat_id = cid


def delete_chat(cid):
    """Delete a chat from memory, SQLite, and stored PDF files."""

    chat = st.session_state.chats.get(cid)

    # Delete permanently from SQLite
    delete_chat_db(cid)

    # Delete uploaded PDF folder
    if chat:
        base_dir = Path(__file__).resolve().parent

        upload_dir = (
            base_dir
            / "data"
            / "uploads"
            / cid
        )

        if upload_dir.exists():
            for file_path in upload_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()

            upload_dir.rmdir()

    # Remove from Streamlit memory
    st.session_state.chats.pop(cid, None)

    if cid in st.session_state.chat_order:
        st.session_state.chat_order.remove(cid)

    if st.session_state.active_chat_id == cid:
        st.session_state.active_chat_id = None


def on_module_change():
    """Keep exactly one module selected (clicking the active chip does not clear it)."""
    value = st.session_state.get("module_pills")
    if value is None:
        st.session_state["module_pills"] = st.session_state.get("_last_module", DEFAULT_MODULE)
    else:
        st.session_state["_last_module"] = value


def sync_option(module):
    """Remember the chosen option per module (clicking the active option does not clear it)."""
    key = f"opt_{module}"
    value = st.session_state.get(key)
    if value is None:
        st.session_state[key] = (
            st.session_state.module_options.get(module) or MODULES[module]["default_option"]
        )
    else:
        st.session_state.module_options[module] = value


# ----------------------------------------------------------------------------
# Backend integration
# ----------------------------------------------------------------------------
def detect_pdf_task(text):
    """
    Detect what the student wants to do with the uploaded PDF.
    """
    request = (text or "").lower().strip()

    if any(
        word in request
        for word in [
            "flashcard",
            "flash cards",
            "study cards",
        ]
    ):
        return "flashcards"

    if any(
        phrase in request
        for phrase in [
            "practice questions",
            "practice question",
            "quiz me",
            "generate questions",
            "generate question",
            "test me",
        ]
    ):
        return "practice"

    if any(
        word in request
        for word in [
            "notes",
            "note",
        ]
    ):
        return "notes"

    if any(
        word in request
        for word in [
            "summarize",
            "summarise",
            "summary",
            "summarization",
            "summarisation",
        ]
    ):
        return "summary"

    return "qna"


def collect_pdf_context(documents, max_chars=60000):
    """
    Collect indexed text from uploaded PDFs.

    Used for summary, notes, flashcards and practice questions.
    """
    parts = []
    total_chars = 0

    for document in documents:
        index = document.get("rag_index")

        if not index:
            continue

        source_name = index.get(
            "source_name",
            document.get("name", "Study PDF"),
        )

        for chunk in index.get("chunks", []):
            page = chunk.get("page", "?")
            text = (chunk.get("text") or "").strip()

            if not text:
                continue

            block = (
                f"[Source: {source_name} | Page {page}]\n"
                f"{text}\n"
            )

            remaining = max_chars - total_chars

            if remaining <= 0:
                return "\n\n".join(parts)

            if len(block) > remaining:
                block = block[:remaining]

            parts.append(block)
            total_chars += len(block)

            if total_chars >= max_chars:
                return "\n\n".join(parts)

    return "\n\n".join(parts)


def generate_response(chat, user_msg):
    module = user_msg.get("module")
    option = user_msg.get("option")
    text = (user_msg.get("content") or "").strip()

    # PDF / RAG mode
    documents = chat.get("documents", [])
    if documents:
        indexed_documents = [
            document for document in documents
            if document.get("rag_index")
        ]

        if not text:
            if indexed_documents:
                return (
                    "📄 **PDF uploaded successfully!**\n\n"
                    "You can ask me to summarize it, create notes, "
                    "make flashcards, generate practice questions, "
                    "or answer questions from the PDF."
                )

            processing_errors = "\n".join(
                f"- {document['name']}: {document['rag_error']}"
                for document in documents
                if document.get("rag_error")
            )
            return (
                "⚠️ I couldn't process the uploaded PDF. "
                "Please try uploading a readable PDF again."
                + (f"\n\n{processing_errors}" if processing_errors else "")
            )

        pdf_task = user_msg.get("pdf_task") or detect_pdf_task(text)

        if not indexed_documents:
            processing_errors = "\n".join(
                f"- {document['name']}: {document['rag_error']}"
                for document in documents
                if document.get("rag_error")
            )
            return (
                "⚠️ I couldn't search the uploaded PDF because no document "
                "was successfully indexed. Please try uploading it again."
                + (f"\n\n{processing_errors}" if processing_errors else "")
            )

        if pdf_task == "qna":
            results = retrieve_from_documents(
                query=text,
                documents=chat["documents"],
                top_k=5,
            )

            if not results:
                return (
                    "⚠️ I couldn't find relevant information "
                    "in the uploaded PDF."
                )

            context = build_context(results)
            prompt = build_pdf_prompt(
                task="qna",
                user_request=text,
                context=context,
            )

            try:
                answer = generate_text(
                    prompt,
                    model=SMART_MODEL,
                )
                sources = format_sources(results)

                if sources:
                    answer += (
                        "\n\n---\n"
                        f"**📄 Sources:** {sources}"
                    )

                return answer
            except Exception as error:
                return (
                    "⚠️ I couldn't generate the PDF answer.\n\n"
                    f"Error: {error}"
                )

        context = collect_pdf_context(chat["documents"])

        if not context:
            return (
                "⚠️ No indexed PDF content is available. "
                "Please upload the PDF again."
            )

        prompt = build_pdf_prompt(
            task=pdf_task,
            user_request=text,
            context=context,
        )

        try:
            return generate_text(
                prompt,
                model=FAST_MODEL,
            )
        except Exception as error:
            return (
                "⚠️ I couldn't process the PDF right now.\n\n"
                f"Error: {error}"
            )

    # Use recent conversation as context
    conversation = chat.get("messages", [])[-10:]

    # Build the appropriate prompt
    prompt = build_prompt(
        module=module,
        option=option,
        user_question=text,
        conversation=conversation,
    )

    # Internal model routing
    if module == "Study":
        selected_model = FAST_MODEL
    elif module == "Tutor":
        if option in ["Beginner", "Intermediate"]:
            selected_model = FAST_MODEL
        else:
            selected_model = SMART_MODEL
    elif module == "Exam":
        if option in ["2 Mark", "3 Mark", "5 Mark", "MCQ"]:
            selected_model = FAST_MODEL
        else:
            selected_model = SMART_MODEL
    else:
        selected_model = FAST_MODEL

    # Generate response
    try:
        return generate_text(
            prompt,
            model=selected_model,
        )
    except Exception as error:
        return (
            "⚠️ I couldn't generate the answer right now.\n\n"
            f"Error: {error}"
        )


# ----------------------------------------------------------------------------
# Submission handling
# ----------------------------------------------------------------------------
def handle_submission(submission):
    text, files = parse_submission(submission)
    if not text and not files:
        return

    chat = get_active_chat()
    if chat is None:
        # New chat: lock in the module / option chosen on the home screen.
        module = st.session_state.get("module_pills")
        option = st.session_state.module_options.get(module) if module else None
        chat = create_chat(text, files, module, option)

    attachments = []
    for uploaded in files:
        data = uploaded.getvalue()

        meta = {
            "name": uploaded.name,
            "size": len(data),
            "type": uploaded.type or "application/pdf",
        }

        BASE_DIR = Path(__file__).resolve().parent

        upload_dir = (
            BASE_DIR
            / "data"
            / "uploads"
            / chat["id"]
        )

        upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_name = f"{uuid.uuid4().hex}_{uploaded.name}"

        file_path = upload_dir / safe_name

        file_path.write_bytes(data)

        # Keep the PDF in memory for the current RAG workflow.
        document = {
            **meta,
            "data": data,
            "file_path": str(file_path),
        }

        attachments.append(meta)

        # Save PDF metadata to SQLite
        save_document(
            chat_id=chat["id"],
            name=uploaded.name,
            size=len(data),
            file_type=uploaded.type or "application/pdf",
            file_path=str(file_path),
        )

        try:
            # ---------------------------------------------------------
            # Create cache path for the RAG index
            # ---------------------------------------------------------
            cache_path = upload_dir / f"{safe_name}.rag.pkl"

            # ---------------------------------------------------------
            # Build RAG index for the newly uploaded PDF
            # ---------------------------------------------------------
            with st.spinner(f"Processing {uploaded.name}..."):

                rag_index = build_document_index(
                    pdf_bytes=data,
                    source_name=uploaded.name,
                )

            # ---------------------------------------------------------
            # Save RAG index for future app restarts
            # ---------------------------------------------------------
            save_document_index(
                rag_index=rag_index,
                cache_path=cache_path,
            )

            document["rag_index"] = rag_index
            document["rag_cache_path"] = str(cache_path)

        except Exception as error:

            document["rag_index"] = None
            document["rag_error"] = str(error)

            st.warning(
                f"Could not process {uploaded.name}: {error}"
            )

        chat["documents"].append(document)

    pdf_task = None

    if chat["documents"] and text:
        pdf_task = detect_pdf_task(text)

    chat["messages"].append(
        {
            "role": "user",
            "content": text,
            "module": chat["module"],
            "option": chat["option"],
            "attachments": attachments,
            "pdf_task": pdf_task,
        }
    )

    # Save user message to SQLite
    save_message(
        chat_id=chat["id"],
        role="user",
        content=text,
        module=chat["module"],
        option=chat["option"],
        attachments=attachments,
    )

    chat["pending"] = True
    st.rerun()


# ----------------------------------------------------------------------------
# UI components
# ----------------------------------------------------------------------------
def get_logo_data_uri():
    if not LOGO_PATH.exists():
        return ""

    try:
        import base64

        encoded = base64.b64encode(
            LOGO_PATH.read_bytes()
        ).decode("utf-8")

        return f"data:image/png;base64,{encoded}"

    except Exception:
        return ""


def render_sidebar():
    with st.sidebar:
        logo_uri = get_logo_data_uri()

        if logo_uri:
            st.markdown(
                f"""
                <div class="la-side-brand">
                    <img
                        class="la-logo-img"
                        src="{logo_uri}"
                        alt="Learn AI"
                    >
                    <div>
                        <div class="la-side-name">Learn AI</div>
                        <div class="la-side-sub">
                            AI Personalized Learning Assistant
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="la-side-brand">'
                '<span>🎓</span> Learn AI'
                '</div>',
                unsafe_allow_html=True,
            )

        with st.container(key="new_chat_wrap"):
            st.button("＋  New Chat", key="new_chat_btn", on_click=start_new_chat)

        order = st.session_state.chat_order
        count_html = f'<span class="la-count">{len(order)}</span>' if order else ""
        st.markdown(
            f'<div class="la-side-label"><span>Chat History</span>{count_html}</div>',
            unsafe_allow_html=True,
        )

        if not order:
            st.markdown(
                '<div class="la-side-empty">'
                '<div class="la-side-empty-icon">💬</div>'
                "<div>No conversations yet</div>"
                "<small>Start a new chat and it will appear here.</small>"
                "</div>",
                unsafe_allow_html=True,
            )

        for cid in order:
            chat = st.session_state.chats[cid]
            active = cid == st.session_state.active_chat_id
            row_key = f"hist_row_active_{cid}" if active else f"hist_row_{cid}"
            with st.container(key=row_key):
                col_title, col_delete = st.columns([5, 1], gap="small", vertical_alignment="center")
                with col_title:
                    st.button(
                        chat["title"],
                        key=f"open_{cid}",
                        on_click=open_chat,
                        args=(cid,),
                        help=chat["title"],
                    )
                with col_delete:
                    st.button("🗑", key=f"del_{cid}", on_click=delete_chat, args=(cid,), help="Delete conversation")


def render_module_selector():
    """Module + option chips. Rendered on the new-chat home screen only."""
    with st.container(key="module_bar_home"):
        module = st.pills(
            "Learning module",
            list(MODULES.keys()),
            selection_mode="single",
            format_func=lambda name: f"{MODULES[name]['icon']} {name}",
            key="module_pills",
            label_visibility="collapsed",
            on_change=on_module_change,
        )

    if not module or module not in MODULES:
        return

    meta = MODULES[module]
    selected_option = None

    if meta["options"]:
        option_key = f"opt_{module}"
        if option_key not in st.session_state:
            st.session_state[option_key] = (
                st.session_state.module_options.get(module) or meta["default_option"]
            )
        with st.container(key="option_bar_home"):
            selected_option = st.pills(
                f"{module} options",
                meta["options"],
                selection_mode="single",
                key=option_key,
                label_visibility="collapsed",
                on_change=sync_option,
                args=(module,),
            )

    selected_option = (
        selected_option
        or st.session_state.module_options.get(module)
        or meta["default_option"]
    )

    st.markdown(
        '<div class="la-mode-note">'
        f"<b>{html.escape(mode_label(module, selected_option))}</b>"
        "<span>·</span>"
        f'<span>{html.escape(meta["hint"])}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_composer():
    return st.chat_input(
        COMPOSER_PLACEHOLDER,
        accept_file=True,
        file_type=["pdf"],
        key="composer",
    )


def render_flashcards(content):
    """
    Convert Gemini's CARD/QUESTION/ANSWER format
    into expandable flashcards.
    """
    pattern = re.compile(
        r"CARD\s+\d+\s*"
        r"QUESTION:\s*(.*?)\s*"
        r"ANSWER:\s*(.*?)(?=\s*CARD\s+\d+\s*QUESTION:|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    cards = pattern.findall(content)

    if not cards:
        st.markdown(content)
        return

    st.markdown("### 🧠 Flashcards")

    for index, (question, answer) in enumerate(cards, start=1):
        question = question.strip()
        answer = answer.strip()

        with st.expander(f"🃏 Card {index}: {question}"):
            st.markdown("**Answer**")
            st.write(answer)


def render_mcqs(content, message_id):
    """
    Display Gemini-generated MCQs as an interactive quiz
    and keep track of the student's score.
    """
    pattern = re.compile(
        r"QUESTION\s+(\d+)\s*"
        r"QUESTION:\s*(.*?)\s*"
        r"A\)\s*(.*?)\s*"
        r"B\)\s*(.*?)\s*"
        r"C\)\s*(.*?)\s*"
        r"D\)\s*(.*?)\s*"
        r"ANSWER:\s*([A-D])\s*"
        r"EXPLANATION:\s*(.*?)(?=\s*QUESTION\s+\d+\s*QUESTION:|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    questions = pattern.findall(content)

    if not questions:
        st.markdown(content)
        return

    # Unique state for this particular quiz message
    results_key = f"mcq_results_{message_id}"

    if results_key not in st.session_state:
        st.session_state[results_key] = {}

    results = st.session_state[results_key]

    total_questions = len(questions)
    answered_questions = len(results)
    score = sum(1 for value in results.values() if value)

    # Quiz header
    st.markdown("### 📝 MCQ Practice")

    st.markdown(
        f"**Score: {score} / {total_questions}**  "
        f"· Answered: {answered_questions} / {total_questions}"
    )

    # Display every question
    for (
        number,
        question,
        a,
        b,
        c,
        d,
        answer,
        explanation,
    ) in questions:
        number = number.strip()
        question = question.strip()
        correct_answer = answer.strip().upper()

        options = [
            f"A) {a.strip()}",
            f"B) {b.strip()}",
            f"C) {c.strip()}",
            f"D) {d.strip()}",
        ]

        st.markdown(f"**Question {number}**")
        st.write(question)

        submitted = number in results

        selected = st.radio(
            "Choose an answer:",
            options,
            key=f"mcq_option_{message_id}_{number}",
            disabled=submitted,
            label_visibility="collapsed",
        )

        if not submitted:
            if st.button(
                "Show Answer",
                key=f"mcq_submit_{message_id}_{number}",
            ):
                selected_letter = selected[0].upper()
                results[number] = selected_letter == correct_answer
                st.session_state[results_key] = results
                st.rerun()
        else:
            if results[number]:
                st.success("✅ Correct!")
            else:
                st.error(
                    f"❌ Incorrect. Correct answer: {correct_answer}"
                )

            st.info(
                explanation.strip()
            )

        st.divider()

    # Final score
    if len(results) == total_questions:
        final_score = sum(
            1 for value in results.values() if value
        )
        percentage = (
            final_score / total_questions
        ) * 100

        st.success("🎉 Quiz Complete!")

        st.markdown(
            f"### Final Score: {final_score} / {total_questions}"
        )

        st.write(
            f"**Percentage: {percentage:.0f}%**"
        )

        if percentage >= 80:
            st.success(
                "Excellent performance! 🎯"
            )
        elif percentage >= 60:
            st.info(
                "Good performance. Keep practising! 👍"
            )
        else:
            st.warning(
                "You need more revision. Keep practising! 📚"
            )

def render_practice_questions(content):
    """
    Convert Gemini's QUESTION/DIFFICULTY format
    into expandable practice questions.
    """
    pattern = re.compile(
        r"QUESTION\s+\d+\s*"
        r"DIFFICULTY:\s*(.*?)\s*"
        r"QUESTION:\s*(.*?)(?=\s*QUESTION\s+\d+\s*DIFFICULTY:|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    questions = pattern.findall(content)

    if not questions:
        st.markdown(content)
        return

    st.markdown("### ✍️ Practice Questions")

    for index, (difficulty, question) in enumerate(questions, start=1):
        difficulty = difficulty.strip()
        question = question.strip()

        with st.expander(f"❓ Question {index} · {difficulty}"):
            st.write(question)


def render_message(msg, message_id):
    is_user = msg["role"] == "user"

    with st.chat_message(
        msg["role"],
        avatar="👤" if is_user else "🎓"
    ):
        content = msg.get("content") or ""

        if (
            not is_user
            and msg.get("module") == "Study"
            and msg.get("option") == "Flashcards"
        ):
            render_flashcards(content)
        elif (
            not is_user
            and msg.get("module") == "Study"
            and msg.get("option") == "Practice Questions"
        ):
            render_practice_questions(content)
        elif (
            not is_user
            and msg.get("module") == "Exam"
            and msg.get("option") == "MCQ"
        ):
            render_mcqs(content, message_id)
        elif not is_user and msg.get("pdf_task") == "flashcards":
            render_flashcards(content)
        elif not is_user and msg.get("pdf_task") == "practice":
            render_practice_questions(content)
        elif content:
            st.markdown(content)

        if msg.get("attachments"):
            st.markdown(
                files_html(msg["attachments"]),
                unsafe_allow_html=True
            )


def respond_to_pending(chat):
    user_msg = chat["messages"][-1]
    with st.spinner("Thinking…"):
        reply = generate_response(chat, user_msg)  # <- plug a real model / streaming here
    assistant_msg = {
        "role": "assistant",
        "content": reply,
        "module": chat["module"],
        "option": chat["option"],
        "pdf_task": user_msg.get("pdf_task"),
        "attachments": [],
    }
    chat["messages"].append(assistant_msg)

    # Save assistant response to SQLite
    save_message(
        chat_id=chat["id"],
        role="assistant",
        content=assistant_msg["content"],
        module=assistant_msg["module"],
        option=assistant_msg["option"],
        attachments=[],
    )

    chat["pending"] = False
    render_message(assistant_msg, len(chat["messages"]) - 1)


def render_study_planner():
    with st.container(key="planner_card"):
        st.markdown(
            '<div class="la-planner-head">'
            '<div class="la-planner-icon">📚</div>'
            "<div>"
            '<div class="la-planner-title">Personalized Study Planner</div>'
            '<div class="la-planner-sub">Create a personalized study plan based on your exam date, '
            "available study time, current level, and weak topics.</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )

        col_subject, col_date = st.columns(2, gap="medium")
        with col_subject:
            subject = st.text_input(
                "Subject",
                placeholder="Example: Cloud Computing",
            )
        with col_date:
            exam_date = st.date_input("Exam Date")

        col_topics, col_weak = st.columns(2, gap="medium")
        with col_topics:
            topics = st.text_area(
                "Topics",
                placeholder=(
                    "Example:\n"
                    "Cloud Service Models\n"
                    "Virtualization\n"
                    "Cloud Security\n"
                    "Cloud Architecture"
                ),
                height=150,
            )
        with col_weak:
            weak_topics = st.text_area(
                "Weak Topics",
                placeholder="Example:\nCloud Security\nVirtualization",
                height=150,
            )

        col_hours, col_level = st.columns(2, gap="medium")
        with col_hours:
            daily_hours = st.number_input(
                "Study hours per day",
                min_value=1,
                max_value=12,
                value=3,
                step=1,
            )
        with col_level:
            current_level = st.selectbox(
                "Current Level",
                ["Beginner", "Intermediate", "Advanced"],
            )

        generate_clicked = st.button("🚀 Generate Study Plan", type="primary")

    if generate_clicked:
        if not subject.strip():
            st.warning("Please enter the subject.")
            return

        if not topics.strip():
            st.warning("Please enter the topics.")
            return

        if not weak_topics.strip():
            weak_topics = "No specific weak topics provided."

        prompt = build_study_plan_prompt(
            subject=subject,
            topics=topics,
            exam_date=str(exam_date),
            daily_hours=daily_hours,
            current_level=current_level,
            weak_topics=weak_topics,
        )

        with st.spinner("Creating your personalized study plan..."):
            try:
                response = generate_text(
                    prompt,
                    model=SMART_MODEL,
                )

                with st.container(key="plan_result"):
                    st.markdown("### 📖 Your Study Plan")
                    st.markdown(response)

            except Exception as error:
                st.error(
                    f"Could not generate study plan: {error}"
                )


def render_home():
    logo_uri = get_logo_data_uri()

    if logo_uri:
        brand_html = (
            f'<div class="la-brand">'
            f'<img class="la-hero-logo" src="{logo_uri}" alt="Learn AI">'
            f'<span>Learn AI</span>'
            f'</div>'
        )
    else:
        brand_html = (
            '<div class="la-brand">'
            '<span class="la-brand-icon">🎓</span> Learn AI'
            '</div>'
        )

    st.markdown(
        '<div class="la-hero">'
        f'{brand_html}'
        f'<div class="la-tagline">{html.escape(TAGLINE)}</div>'
        f'<div class="la-greeting">{html.escape(GREETING)}</div>'
        f'<div class="la-support">{html.escape(SUPPORT_TEXT)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    render_module_selector()

    if (
        st.session_state.get("module_pills") == "Study"
        and st.session_state.get("module_options", {}).get("Study")
        == "Study Planner"
    ):
        render_study_planner()
        return None

    with st.container(key="home_composer"):
        submission = render_composer()

    st.markdown(
        '<div class="la-footnote">📎 Attach a PDF with the paperclip to learn from your own study material.</div>',
        unsafe_allow_html=True,
    )

    return submission


def render_conversation(chat):
    label = mode_label(chat.get("module"), chat.get("option"))
    badge = f'<span class="la-badge">{html.escape(label)}</span>' if label else ""
    st.markdown(
        f'<div class="la-chat-title"><span class="la-chat-name">{html.escape(chat["title"])}</span>{badge}</div>',
        unsafe_allow_html=True,
    )

    if chat["documents"]:
        st.markdown(files_html(chat["documents"]), unsafe_allow_html=True)

    for message_index, msg in enumerate(chat["messages"]):
        render_message(msg, message_index)

    submission = render_composer()

    if submission is None and chat.get("pending"):
        respond_to_pending(chat)

    return submission


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    init_state()
    inject_css()
    render_sidebar()

    chat = get_active_chat()
    submission = render_home() if chat is None else render_conversation(chat)

    if submission:
        handle_submission(submission)


main()