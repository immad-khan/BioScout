from pymongo import MongoClient
import sys

# Test 1: Encoded Password
uri_encoded = "mongodb://BioScout:S%21ddeeq5696@ac-ejolajp-shard-00-00.ceohmfb.mongodb.net:27017,ac-ejolajp-shard-00-01.ceohmfb.mongodb.net:27017,ac-ejolajp-shard-00-02.ceohmfb.mongodb.net:27017/bioscout_db?ssl=true&authSource=admin&retryWrites=true&w=majority"
print(f"Testing Encoded Password: ...")
try:
    client = MongoClient(uri_encoded, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("SUCCESS with ENCODED password!")
    sys.exit(0)
except Exception as e:
    print(f"FAILED with ENCODED: {e}")

# Test 2: Unencoded Password (Maybe the %21 is literal?)
uri_literal = "mongodb://BioScout:S!ddeeq5696@ac-ejolajp-shard-00-00.ceohmfb.mongodb.net:27017,ac-ejolajp-shard-00-01.ceohmfb.mongodb.net:27017,ac-ejolajp-shard-00-02.ceohmfb.mongodb.net:27017/bioscout_db?ssl=true&authSource=admin&retryWrites=true&w=majority"
print(f"Testing Literal Password: ...")
try:
    client = MongoClient(uri_literal, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("SUCCESS with LITERAL password!")
    sys.exit(0)
except Exception as e:
    print(f"FAILED with LITERAL: {e}")
