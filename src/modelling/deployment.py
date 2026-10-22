from pathlib import Path

from main import main

DATA_PATH = Path(__file__).parents[2] / "data" / "abalone.csv"

if __name__ == "__main__":
    # retrain the model every sunday at midnight
    main.serve(
        name="weekly-training",
        cron="0 0 * * 0",
        parameters={"trainset_path": str(DATA_PATH)},
        # by default the schedule is paused when this process stops (e.g. docker stop)
        pause_on_shutdown=False,
    )
