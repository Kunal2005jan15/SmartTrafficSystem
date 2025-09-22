import sys
import os

# Add parent folder (SmartTrafficSystem) to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai.traffic_predictor import TrafficPredictor
from simulation.vehicle import vehicles
from simulation.traffic_light import lights

predictor = TrafficPredictor("Dashboard Intersection")
predictor.train()

lane_history = {"N":[], "S":[], "E":[], "W":[]}

def get_lane_counts():
    counts = {"N":0, "S":0, "E":0, "W":0}
    for v in vehicles:
        counts[v.direction] += 1
    for dir in counts:
        lane_history[dir].append(counts[dir])
        if len(lane_history[dir]) > 50:
            lane_history[dir].pop(0)
    return counts

def get_predicted_density():
    return {dir: predictor.predict_next() for dir in ["N","S","E","W"]}

def get_traffic_lights():
    return {light.direction: light.state for light in lights}

def check_emergency():
    return any(v.is_emergency for v in vehicles)

def get_lane_history():
    return lane_history

def get_vehicle_positions():
    # Return simplified vehicle positions for mini-map
    pos = []
    for v in vehicles:
        pos.append({"x": v.x, "y": v.y, "color": "yellow" if v.is_emergency else "blue"})
    return pos
