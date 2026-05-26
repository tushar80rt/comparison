"""
config.py - Centralized configuration and environment variables.
"""

import os
from dotenv import load_dotenv

# Load environmental configurations
load_dotenv(".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SCRAPEGRAPH_API_KEY = os.getenv("SCRAPEGRAPH_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Models
LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Paths
CHROMA_DIR = "chroma_db"
DB_PATH = "history.db"
