import json
import os
from datetime import datetime, timezone


def main() -> None:
    payload = {
        "status": "complete",
        "task": os.getenv("BATCH_TASK_NAME", "study-aws-3-batch"),
        "message": os.getenv("BATCH_MESSAGE", "ECS batch task finished successfully."),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()

