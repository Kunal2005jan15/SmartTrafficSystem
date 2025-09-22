# traffic_predictor.py
import random

class TrafficPredictor:
    def __init__(self, name="Intersection"):
        self.name = name
        self.history = []

    def train(self):
        self.history = [random.randint(20, 50) for _ in range(10)]
        print(f"[{self.name}] AI predictor initialized with fake historical data.")

    def predict_next(self):
        if not self.history:
            self.train()
        next_val = max(5, min(60, self.history[-1] + random.randint(-8, 8)))
        self.history.append(next_val)
        if len(self.history) > 50:
            self.history.pop(0)
        return next_val
