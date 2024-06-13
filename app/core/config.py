from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_DATEBASE = os.environ.get("DB_DATEBASE")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = os.environ.get("DB_PORT")

SECRET_JWT_AUTH = os.environ.get("SECRET_JWT_AUTH")
