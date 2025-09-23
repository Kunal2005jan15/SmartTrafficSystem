Smart Traffic Management System 🚦

An AI-powered system for vehicle detection, traffic prediction, and adaptive traffic light control.
This project combines computer vision, data analytics, and simulation models to improve road traffic efficiency and reduce congestion.

✨ Features:

🚗 Vehicle Detection – Detect and count vehicles in real-time from video or camera streams.

📈 Traffic Prediction – Forecast traffic flow using historical datasets.

🟢 Adaptive Signal Control – Dynamically adjust traffic light timing based on traffic conditions.

📊 Simulation Dashboard – Visualize traffic flow, signal states, and predictions.

🔧 Modular Design – Separate AI, simulation, and visualization modules for flexibility.





PROJECT STRUCTURE:

SmartTrafficSystem/
│── ai/
│   ├── detect_video.py        # Real-time vehicle detection
│   ├── vehicle_detection.py   # Core detection logic
│   ├── traffic_predictor.py   # Traffic forecasting module
│
│── detection/
│   ├── vehicle_detection_demo.py # Detection demo script
│
│── simulation/
│   ├── main.py                # Simulation entry point
│   ├── dashboard.py           # Traffic visualization dashboard
│   ├── traffic_light.py       # Traffic light control logic
│   ├── vehicle.py             # Vehicle model for simulation
│   ├── config.py              # Configuration settings
│   ├── data.json              # Example simulation data
│
│── data/
│   ├── traffic_history.csv    # Historical traffic dataset (sample)
│
│── requirements.txt           # Python dependencies
│── README.md                  # Documentation
