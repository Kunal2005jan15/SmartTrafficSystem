# traffic_predictor.py
import random
import collections

class TrafficPredictor:
    """
    Simple prototype predictor:
    - Keeps a small rolling history of integer counts
    - predict_next returns a small variation of last value
    """
    def __init__(self, name="Intersection"):
        self.name = name
        self.history = collections.deque(maxlen=50)

    def train(self):
        # Initialize with some fake historical counts (demo purpose)
        self.history.extend([random.randint(5, 25) for _ in range(12)])

    def predict_next(self):
        if not self.history:
            self.train()
        last = int(self.history[-1])
        variation = random.randint(-4, 6)
        next_val = max(0, last + variation)
        self.history.append(next_val)
        return next_val
