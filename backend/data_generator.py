import random

def generate_data(mode="normal"):
    if mode == "high":
        return {
            "cpu": random.randint(80, 95),
            "ram": random.randint(70, 90),
            "disk": random.randint(60, 85)
        }
    else:
        return {
            "cpu": random.randint(20, 60),
            "ram": random.randint(30, 70),
            "disk": random.randint(20, 60)
        }