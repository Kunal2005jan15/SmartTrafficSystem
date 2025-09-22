from flask import Flask, render_template
import random

app = Flask(__name__)

@app.route('/')
def index():
    # Simulated lane density
    lane_density = [random.randint(0,10) for _ in range(4)]
    return render_template("index.html", lane_density=lane_density)

if __name__ == "__main__":
    app.run(debug=True)
