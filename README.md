&#x20;Learn AI 🎓



An AI-powered personalized learning assistant designed for college students. Learn AI helps students understand concepts, prepare for exams, study from notes and PDFs, and create personalized study plans using Generative AI.



&#x20;🚀 Project Overview



Learn AI is a Generative AI-based student learning platform that provides:



\- AI-powered concept explanations

\- Beginner, Intermediate and Advanced learning levels

\- Exam-oriented answers

\- MCQ generation

\- Notes and summaries

\- Flashcards

\- Practice questions

\- Personalized study plans

\- PDF-based question answering

\- PDF summaries and notes

\- PDF flashcards

\- PDF practice questions

\- Retrieval-Augmented Generation (RAG)

\- Persistent chat history



The system is designed to provide a simple and interactive learning experience for college students.





&#x20;✨ Key Features



&#x20;📚 AI Tutor



Students can ask questions and receive explanations based on their learning level.



Available levels:



\- Beginner

\- Intermediate

\- Advanced



The AI adapts the explanation according to the selected level.





&#x20;📝 Exam Preparation



Learn AI helps students prepare exam-oriented answers.



Supported answer formats:



\- 2 Mark

\- 3 Mark

\- 5 Mark

\- 10 Mark

\- 15 Mark

\- MCQ



This allows students to practice both short-answer and long-answer questions.





&#x20;📖 Study Tools



Students can generate:



\- Notes

\- Summaries

\- Flashcards

\- Practice Questions



These tools help students revise topics quickly and effectively.





&#x20;📅 Personalized Study Planner



Students can create a personalized study plan by providing:



\- Subject

\- Topics

\- Exam Date

\- Study Hours per Day

\- Current Learning Level

\- Weak Topics



The AI generates a structured study plan based on the student's requirements.





&#x20;📄 PDF Study Assistant



Students can upload study-material PDFs and interact with them.



Supported PDF features:



\- Ask questions from PDF

\- Generate PDF summary

\- Generate PDF notes

\- Generate PDF flashcards

\- Generate PDF practice questions





&#x20;🧠 Retrieval-Augmented Generation (RAG)



Learn AI uses Retrieval-Augmented Generation to answer questions from uploaded study materials.



&#x20;RAG Workflow



PDF Upload

&#x20;   ↓

Text Extraction

&#x20;   ↓

Text Chunking

&#x20;   ↓

Gemini Embeddings

&#x20;   ↓

Vector Similarity Search

&#x20;   ↓

Relevant Chunks Retrieved

&#x20;   ↓

Context Construction

&#x20;   ↓

Gemini LLM

&#x20;   ↓

AI Generated Answer



This allows the system to generate answers based on the content of the uploaded document instead of relying only on general model knowledge.



🤖 AI Model Routing

Learn AI uses multiple Gemini models depending on the task.



Fast Model

Used for tasks that require quick responses:

\- Study tools

\- Beginner Tutor

\- Intermediate Tutor

\- 2 Mark answers

\- 3 Mark answers

\- 5 Mark answers

\- MCQs



Smart Model

Used for tasks requiring more detailed reasoning:

\- Advanced Tutor

\- 10 Mark answers

\- 15 Mark answers

\- Personalized Study Planner



A fallback mechanism is also included so that the application can use the fast model if the selected model is unavailable.





🏗️ System Architecture



&#x20;                   ┌─────────────────────┐

&#x20;                   │      Student        │

&#x20;                   └──────────┬──────────┘

&#x20;                              │

&#x20;                              ▼

&#x20;                   ┌─────────────────────┐

&#x20;                   │   Streamlit UI      │

&#x20;                   │   Learn AI Web App   │

&#x20;                   └──────────┬──────────┘

&#x20;                              │

&#x20;            ┌─────────────────┼─────────────────┐

&#x20;            │                 │                 │

&#x20;            ▼                 ▼                 ▼

&#x20;       ┌─────────┐      ┌───────────┐     ┌───────────┐

&#x20;       │ AI Tutor│      │Exam Prep  │     │Study Tools│

&#x20;       └────┬────┘      └─────┬─────┘     └─────┬─────┘

&#x20;            │                 │                 │

&#x20;            └─────────────────┼─────────────────┘

&#x20;                              │

&#x20;                              ▼

&#x20;                   ┌─────────────────────┐

&#x20;                   │   Gemini API        │

&#x20;                   │ Generative AI Model │

&#x20;                   └──────────┬──────────┘

&#x20;                              │

&#x20;                              ▼

&#x20;                   ┌─────────────────────┐

&#x20;                   │ Personalized Study  │

&#x20;                   │      Response       │

&#x20;                   └─────────────────────┘





&#x20;       PDF Upload

&#x20;            │

&#x20;            ▼

&#x20;     ┌───────────────┐

&#x20;     │ Text Extraction│

&#x20;     └───────┬───────┘

&#x20;             │

&#x20;             ▼

&#x20;     ┌───────────────┐

&#x20;     │ Chunking +    │

&#x20;     │ Embeddings    │

&#x20;     └───────┬───────┘

&#x20;             │

&#x20;             ▼

&#x20;     ┌───────────────┐

&#x20;     │ Similarity    │

&#x20;     │ Retrieval     │

&#x20;     └───────┬───────┘

&#x20;             │

&#x20;             ▼

&#x20;     ┌───────────────┐

&#x20;     │ Gemini +      │

&#x20;     │ Retrieved     │

&#x20;     │ Context       │

&#x20;     └───────┬───────┘

&#x20;             │

&#x20;             ▼

&#x20;         PDF Answer



🛠️ Technology Stack

Frontend / UI

\- Streamlit

\- HTML

\- CSS

Backend

\- Python

\- SQLite

Generative AI

\- Google Gemini API

\- Gemini Text Generation

\- Gemini Embeddings

RAG

\- PDF text extraction

\- Text chunking

\- Embeddings

\- Cosine similarity retrieval

\- Context-based generation

Libraries

\- Streamlit

\- google-genai

\- python-dotenv

\- pypdf

\- NumPy

📂 Project Structure

Learn AI/

│

├── app.py

├── requirements.txt

├── README.md

├── .gitignore

│

├── assets/

│   └── Learn AI logo.png

│

├── backend/

│   ├── \_\_init\_\_.py

│   ├── database.py

│   ├── gemini.py

│   ├── prompts.py

│   └── rag.py

│

└── data/

&#x20;   └── uploads/







⚙️ Installation

1\. Clone the Repository

git clone https://github.com/VarunKumar2905/Learn-AI.git

cd Learn-AI



2\. Create a Virtual Environment

python -m venv .venv



3\. Activate the Virtual Environment

Windows:

.venv\\Scripts\\activate



4\. Install Dependencies

pip install -r requirements.txt



🔑 API Configuration

Create a .env file in the project root:

GEMINI\_API\_KEY=your\_gemini\_api\_key



Replace your\_gemini\_api\_key with your Google Gemini API key.

Do not upload your .env file or API key to GitHub.

▶️ Run the Application

Start the Streamlit application using:

streamlit run app.py



The application will open in the browser.

💬 Example Workflow

AI Tutor

Student

&#x20;  ↓

Select Tutor

&#x20;  ↓

Choose Learning Level

&#x20;  ↓

Ask Question

&#x20;  ↓

Gemini AI

&#x20;  ↓

Level-based Explanation



Exam Preparation

Student

&#x20;  ↓

Select Exam

&#x20;  ↓

Choose Mark Type

&#x20;  ↓

Enter Question

&#x20;  ↓

Gemini AI

&#x20;  ↓

Exam-oriented Answer



PDF Study Assistant

Student

&#x20;  ↓

Upload PDF

&#x20;  ↓

Create RAG Index

&#x20;  ↓

Ask Question

&#x20;  ↓

Retrieve Relevant Content

&#x20;  ↓

Gemini AI

&#x20;  ↓

Answer Based on PDF



💾 Data Persistence

Learn AI uses SQLite to store application data such as:

\- Chat sessions

\- Chat messages

\- Uploaded document information

RAG indexes are cached locally so that previously processed PDFs do not need to regenerate embeddings every time the application starts.

🎨 User Interface

The application provides a modern dark-themed learning interface with:

\- Sidebar navigation

\- Chat history

\- New chat option

\- Tutor / Exam / Study modules

\- Learning-level selection

\- Exam mark selection

\- PDF upload

\- Interactive study planner

\- AI-generated responses

🔐 Security

The project follows basic security practices:

\- API keys are stored in environment variables.

\- .env is excluded using .gitignore.

\- Uploaded documents and local database files are excluded from Git.

\- RAG cache files are excluded from Git.

Never commit API keys or sensitive credentials to the repository.

🎯 Project Objectives

The main objectives of Learn AI are:

1\. Provide an AI-powered learning assistant for college students.

2\. Explain difficult concepts in simple language.

3\. Support different learning levels.

4\. Generate exam-oriented answers.

5\. Provide useful study materials automatically.

6\. Help students revise using flashcards and practice questions.

7\. Create personalized study plans.

8\. Allow students to learn directly from uploaded PDF materials.

9\. Demonstrate the practical use of Generative AI and RAG.

🔮 Future Enhancements

Possible future improvements include:

\- OCR support for scanned PDFs

\- Voice-based interaction

\- Multilingual learning support

\- Advanced analytics

\- Student progress tracking

\- Mobile application

\- Cloud deployment

\- More advanced agent-based learning features

👨‍💻 Developer:

Varun Kumar

Generative AI Student Project

Project: Learn AI – AI Personalized Learning Assistant

📜 License

This project is developed for educational and academic purposes.

