from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, RootModel
from google.cloud import bigquery
import os
from typing import Dict, Any, Literal
import json

# Initialize FastAPI app
app = FastAPI()

# Initialize BigQuery client
client = bigquery.Client()

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "your-project-id")
DATASET_ID = os.getenv("DATASET_ID", "your_dataset")
TABLE_ID = os.getenv("TABLE_ID", "your_table")

# Initialize BigQuery client and table reference once
table_ref = client.dataset(DATASET_ID, project=PROJECT_ID).table(TABLE_ID)
table = client.get_table(table_ref)


SCRIPT_MAP = {
    "getAvailableTemplates": "gat",
    "getRequestStatus": "grs",
    "getReturnRequests": "grr",
    "requestMachines": "rm",
    "requestReturnMachines": "rrm",
}

class DataModel(RootModel):
    root: Dict[str, Any]


@app.put("/{cluster}/{run}/{hostname}/{script}/{direction}/{timestamp}")
async def insert_data(
    cluster: str,
    run: str,
    hostname: str,
    script: Literal[
        "getAvailableTemplates", # gat
        "getRequestStatus", # grs
        "getReturnRequests", # grr
        "requestMachines", # rm
        "requestReturnMachines", # rrm
        "symAgetDemandRequests",
        "symAgetReturnRequests",
    ],
    direction: Literal["in", "out"],
    timestamp: str,
    payload: Any = Body(...),
):
    try:
        # Convert the data dict to a JSON string for BigQuery

        row_data = {
            "time": timestamp,
            "cluster": cluster,
            "namespace": None,
            "source": "cli",
            "run": run,
            "event": f"cli:{SCRIPT_MAP[script]}_{direction}",
            "sym_request": None,
            "container_name": None,
            "pod": None,
            "node": None,
            "acn": None,
            "detail": json.dumps(
                {
                    "hostname": hostname,
                    "payload": payload,
                }),
        }
        rows_to_insert = [row_data]
        errors = client.insert_rows_json(table, rows_to_insert)

        if errors:
            raise HTTPException(
                status_code=500, detail=f"BigQuery insert failed: {errors}"
            )

        return {"status": "success", "message": "Data inserted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
