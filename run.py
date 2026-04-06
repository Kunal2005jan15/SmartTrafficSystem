"""
SmartTrafficSystem - Root CLI Entry Point
Usage:
    python run.py detect --video data/sample.mp4
    python run.py simulate
    python run.py predict
    python run.py all --video data/sample.mp4
"""

import argparse
import sys
import os

def run_detect(video_path):
    print(f"\n🚗 Starting Vehicle Detection on: {video_path}\n")
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found at '{video_path}'")
        print("   Please provide a valid path, e.g.: python run.py detect --video data/sample.mp4")
        sys.exit(1)
    # Inject video path into the detection module
    os.environ["TRAFFIC_VIDEO_PATH"] = video_path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai"))
    try:
        import detect_video
        detect_video.run(video_path)
    except AttributeError:
        # Fallback: if detect_video has no run() function, patch and import
        import importlib
        import detect_video as dv
        print("⚠️  detect_video.run() not found — running module directly.")
        # The module will use os.environ["TRAFFIC_VIDEO_PATH"]


def run_simulate():
    print("\n📊 Starting Traffic Simulation Dashboard...\n")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "simulation"))
    try:
        import main as sim_main
        sim_main.run()
    except AttributeError:
        import main  # noqa — runs on import


def run_predict():
    print("\n📈 Running Traffic Predictor...\n")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai"))
    try:
        import traffic_predictor
        traffic_predictor.run()
    except AttributeError:
        import traffic_predictor  # noqa — runs on import


def run_all(video_path):
    import threading
    print("\n🚦 SmartTrafficSystem — Full Pipeline\n")
    print("Starting detection + simulation in parallel...\n")

    t_detect   = threading.Thread(target=run_detect,   args=(video_path,), daemon=True)
    t_simulate = threading.Thread(target=run_simulate, daemon=True)
    t_predict  = threading.Thread(target=run_predict,  daemon=True)

    t_predict.start()
    t_predict.join()          # predictor trains/loads first

    t_detect.start()
    t_simulate.start()

    t_detect.join()
    t_simulate.join()


def main():
    parser = argparse.ArgumentParser(
        prog="SmartTrafficSystem",
        description="🚦 AI-powered Smart Traffic Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py detect --video data/sample.mp4
  python run.py simulate
  python run.py predict
  python run.py all --video data/sample.mp4
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect
    p_detect = subparsers.add_parser("detect", help="Run vehicle detection on a video file")
    p_detect.add_argument("--video", required=True, help="Path to input video file (e.g. data/sample.mp4)")

    # simulate
    subparsers.add_parser("simulate", help="Run the traffic simulation dashboard")

    # predict
    subparsers.add_parser("predict", help="Run the traffic flow predictor")

    # all
    p_all = subparsers.add_parser("all", help="Run full pipeline: predict + detect + simulate")
    p_all.add_argument("--video", required=True, help="Path to input video file")

    args = parser.parse_args()

    if args.command == "detect":
        run_detect(args.video)
    elif args.command == "simulate":
        run_simulate()
    elif args.command == "predict":
        run_predict()
    elif args.command == "all":
        run_all(args.video)


if __name__ == "__main__":
    main()