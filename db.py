
# Honestly, i dont even know why this file exists... 
# will have to make some error handlers and exceptions later

from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv; load_dotenv()

db = MongoClient(os.getenv("DATABASE"), server_api=ServerApi('1'))
