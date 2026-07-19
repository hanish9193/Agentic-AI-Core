from dotenv import load_dotenv
load_dotenv()

from backend.config.settings import get_settings
settings = get_settings()

print("Repository Provider:", settings.repository.provider)
print("Database URL:", settings.repository.database_url)
