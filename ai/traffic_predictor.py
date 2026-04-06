"""
ai/traffic_predictor.py  — IMPROVED VERSION
--------------------------------------------
Changes over original:
  • Saves trained model to models/traffic_predictor.pkl  (persistence)
  • Loads saved model on subsequent runs — no retraining needed
  • Prints model accuracy metrics (MAE, R²)
  • Exposes run() so CLI can call it directly
  • Gracefully handles missing CSV with a helpful message
"""

import os
import sys
import pickle
import numpy  as np
import pandas as pd

from sklearn.ensemble         import RandomForestRegressor
from sklearn.model_selection  import train_test_split
from sklearn.metrics          import mean_absolute_error, r2_score
from sklearn.preprocessing    import LabelEncoder

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "..", "data", "traffic_history.csv")
MODEL_DIR   = os.path.join(BASE_DIR, "..", "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "traffic_predictor.pkl")


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        print(f"❌ Dataset not found at: {DATA_PATH}")
        print("   Please place traffic_history.csv in the data/ folder.")
        print("   Expected columns: hour, day_of_week, vehicle_count (at minimum)")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"✅ Loaded dataset: {len(df)} rows, columns: {list(df.columns)}")
    return df


def preprocess(df: pd.DataFrame):
    """Auto-detect feature columns and encode categoricals."""
    # Encode string columns
    le = LabelEncoder()
    for col in df.select_dtypes(include="object").columns:
        df[col] = le.fit_transform(df[col].astype(str))

    # Try to find a 'vehicle_count' or similar target column
    target_candidates = [c for c in df.columns if "count" in c.lower() or "volume" in c.lower() or "flow" in c.lower()]
    if not target_candidates:
        print("⚠️  Could not find a 'vehicle_count' column. Using last column as target.")
        target_col = df.columns[-1]
    else:
        target_col = target_candidates[0]

    print(f"🎯 Target column: '{target_col}'")
    feature_cols = [c for c in df.columns if c != target_col]
    print(f"📊 Feature columns: {feature_cols}")

    X = df[feature_cols].values
    y = df[target_col].values
    return X, y, feature_cols, target_col


def train(X, y) -> RandomForestRegressor:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)
    print(f"\n📈 Model trained successfully!")
    print(f"   MAE : {mae:.2f}  (mean absolute error in vehicle count)")
    print(f"   R²  : {r2:.4f}  (1.0 = perfect)")
    return model


def save_model(model):
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"💾 Model saved → {MODEL_PATH}")


def load_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print(f"✅ Loaded saved model from {MODEL_PATH}")
    return model


def predict_sample(model, feature_cols: list):
    """Show a quick sample prediction for demonstration."""
    print("\n🔮 Sample predictions (hour=8, day=1 = Monday morning rush):")
    sample_inputs = [
        [8,  1],   # 8am Monday
        [13, 3],   # 1pm Wednesday
        [18, 5],   # 6pm Friday (rush hour)
        [2,  6],   # 2am Sunday (quiet)
    ]
    labels = ["8am Monday", "1pm Wednesday", "6pm Friday (rush)", "2am Sunday (quiet)"]

    for inp, lbl in zip(sample_inputs, labels):
        # Pad or trim to match feature count
        padded = inp[:len(feature_cols)] + [0] * max(0, len(feature_cols) - len(inp))
        pred   = model.predict([padded])[0]
        print(f"   {lbl:<28} → predicted vehicles: {pred:.1f}")


def run():
    print("\n📈 Traffic Predictor\n" + "─" * 40)

    if os.path.exists(MODEL_PATH):
        print("♻️  Found saved model — loading instead of retraining.")
        model = load_model()
        # Still load data to get feature columns
        df = load_data()
        _, _, feature_cols, _ = preprocess(df)
    else:
        print("🏋️  No saved model found — training from scratch...")
        df                        = load_data()
        X, y, feature_cols, _    = preprocess(df)
        model                    = train(X, y)
        save_model(model)

    predict_sample(model, feature_cols)
    print("\n✅ Predictor ready. Model persisted for future runs.\n")
    return model


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()