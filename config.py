from dotenv import load_dotenv
import os
import base64

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
API_PROD_URL = os.getenv("API_PROD_URL")
IXC_SESSION = os.getenv("IXC_SESSION") or ""
TOKEN = os.getenv("TOKEN")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

def basic_auth_header():
    token = f"{TOKEN}".encode("utf-8")
    return base64.b64encode(token).decode("utf-8")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

DB_CONFIG = {
    "host": DB_HOST,
    'port': DB_PORT,
    "user": DB_USER,
    "password": DB_PASS,
    "database": DB_NAME
}

LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN") 
SECRET_KEY = os.getenv("SECRET_KEY")   
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 1))
BASE_DN = os.getenv("BASE_DN")
GROUP_DN = os.getenv("GROUP_DN")