import argparse, sys, os
from flowerapp.core.engine import calculate_agency
from flowerapp.core.storage import save_project, load_project

def main():
    parser = argparse.ArgumentParser(description="FLOWERAPP")
    parser.add_argument("command", choices=["score", "web", "init"])
    parser.add_argument("--project", help="Project ID", default="default")
    args = parser.parse_args()

    proj_path = f"data/{args.project}"

    if args.command == "init":
        p = {
            "app_version": "1.0.0", "session_schema_version": 1,
            "metadata": {"project_id": args.project, "project_name": args.project},
            "intake": {"signals": [], "constraints": []},
            "scoring": {"agency_total": 0, "subscores": {}}
        }
        save_project(p, proj_path)
        print(f"Project {args.project} initialized.")
    elif args.command == "web":
        import uvicorn
        os.environ["PROJ_PATH"] = proj_path
        from flowerapp.web import app
        uvicorn.run(app, host="127.0.0.1", port=8000)
