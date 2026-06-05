from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://skillara_user:Skillara%4036@cluster0.hlpsi18.mongodb.net/?appName=Cluster0"
)

db = client["skillara"]

students = db["students"]
companies_collection = db["companies"]
resources_collection = db["resources"]
questions_collection = db["questions"]
notifications_collection = db["notifications"]
mcq_collection = db["mcq_questions"]