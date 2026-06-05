from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://skillara_user:Skillara%4036@cluster0.hlpsi18.mongodb.net/?appName=Cluster0"
)

try:
    client.admin.command("ping")
    print("Connected to Atlas Successfully!")
except Exception as e:
    print(e)