import os
import certifi
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["skillara"]

students = db["students"]
companies_collection = db["companies"]
resources_collection = db["resources"]
questions_collection = db["questions"]
notifications_collection = db["notifications"]
mcq_collection = db["mcq_questions"]