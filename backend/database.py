from collections import deque

try:
    from pymongo import MongoClient
except ModuleNotFoundError:
    MongoClient = None


_memory_history = deque(maxlen=50)


if MongoClient is not None:
    client = MongoClient("mongodb+srv://admin:admin123@cluster0.xxxx.mongodb.net/")
    db = client["server_monitor"]
    collection = db["anomalies"]
else:
    collection = None


def save_anomaly(data):
    if collection is not None:
        collection.insert_one(data)
        return

    _memory_history.appendleft(data)


def get_history():
    if collection is not None:
        return list(collection.find({}, {"_id": 0}))

    return list(_memory_history)
