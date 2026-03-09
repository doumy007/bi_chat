from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuración de la base de datos MySQL
DB_CONFIG = {
    "host": "50.6.61.23",
    "user": "nufjztte_admin",
    "password": "nufjztte_googleads",
    "database": "nufjztte_googleads"
}
