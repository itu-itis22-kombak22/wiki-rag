import os

# --- Entities ---

PEOPLE = [
    "Albert_Einstein",
    "Marie_Curie",
    "Leonardo_da_Vinci",
    "William_Shakespeare",
    "Ada_Lovelace",
    "Nikola_Tesla",
    "Lionel_Messi",
    "Cristiano_Ronaldo",
    "Taylor_Swift",
    "Frida_Kahlo",
    "Isaac_Newton",
    "Stephen_Hawking",
    "Elon_Musk",
    "Cleopatra",
    "Napoleon_Bonaparte",
    "Mahatma_Gandhi",
    "Nelson_Mandela",
    "Galileo_Galilei",
    "Charles_Darwin",
    "Wolfgang_Amadeus_Mozart",
]

PLACES = [
    "Eiffel_Tower",
    "Great_Wall_of_China",
    "Taj_Mahal",
    "Grand_Canyon",
    "Machu_Picchu",
    "Colosseum",
    "Hagia_Sophia",
    "Statue_of_Liberty",
    "Pyramids_of_Giza",
    "Mount_Everest",
    "Stonehenge",
    "Angkor_Wat",
    "Chichen_Itza",
    "Petra,_Jordan",
    "Acropolis_of_Athens",
    "Niagara_Falls",
    "Amazon_River",
    "Sahara",
    "Victoria_Falls",
    "Galápagos_Islands",
]

# Display names mapping (Wikipedia title -> readable name)
PEOPLE_DISPLAY = {p: p.replace("_", " ").replace(",_", ", ") for p in PEOPLE}
PLACES_DISPLAY = {p: p.replace("_", " ").replace(",_", ", ") for p in PLACES}

# --- Chunking ---
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks

# --- Models ---
EMBED_MODEL = "all-MiniLM-L6-v2"   # sentence-transformers model
LLM_MODEL = "llama3.2:3b"          # Ollama model
OLLAMA_URL = "http://localhost:11434/api/generate"

# --- Storage ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "wiki.db")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")

# --- Retrieval ---
TOP_K = 5
COLLECTION_NAME = "wiki_rag"

# --- Wikipedia API ---
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
