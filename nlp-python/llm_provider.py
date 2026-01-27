import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path="../.env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    # Try loading from local .env if parent not found or empty
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not found. Please set it in .env file.")

# Initialize Groq LLM
# Model options: llama3-70b-8192 (recommended), llama3-8b-8192, mixtral-8x7b-32768
llm = ChatGroq(
    temperature=0.2,
    model_name="llama-3.1-8b-instant",
    groq_api_key=GROQ_API_KEY
)
