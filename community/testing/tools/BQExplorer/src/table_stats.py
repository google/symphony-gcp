import json
import pandas as pd

def print_stats(df: pd.DataFrame):
    print("====================")

    # Print total number of entries
    print(
        "Number of entries: ",
        len(df.index)
    )

    print("====================")

    # Print unicity to verify all events have been properly ingested.
    # Multiple events by indexer are possible because some events (such as pod:delete) repeat (with or without grace period, for example)

    print(
        "Unique `pod:create` pods:",
        len(df[df.event == "pod:create"].pod.unique())
    )

    print(
        "Unique `pod:scheduled` pods:",
        len(df[df.event == "pod:scheduled"].pod.unique())
    )

    print(
        "Unique `container:started` pods:",
        len(df[df.event == "container:started"].pod.unique())
    )

    print(
        "Unique `pod:ready_patch` pods:",
        len(df[df.event == "pod:ready_patch"].pod.unique())
    )

    print(
        "Unique `node:create` nodes:",
        len(df[df.event == "node:create"].node.unique())
    )

    print(
        "Unique `node:ready` nodes:",
        len(df[df.event == "node:ready"].node.unique())
    )

    print(
        "Unique `node:ready_patch` nodes:",
        len(df[df.event == "node:ready_patch"].node.unique())
    )

    print(
        "Unique `pod:delete` pods:",
        len(df[df.event == "pod:delete"].pod.unique())
    )

    print(
        "Unique `container:killing` pods:",
        len(df[df.event == "container:killing"].pod.unique())
    )

    print(
        "Unique `node:cordoned` nodes:",
        len(df[df.event == "node:cordoned"].node.unique())
    )

    print(
        "Unique `node:not_ready` nodes:",
        len(df[df.event == "node:not_ready"].node.unique())
    )

    # print(
    #     "Unique `node:deleted` nodes:",
    #     len(df[df.event == "node:deleted"].node.unique())
    # )

    print(
        "Unique `node:delete` nodes:",
        len(df[df.event == "node:delete"].node.unique())
    )

    print(
        "Scaledown sum:",
        sum(
            detail["node_count"] for detail in
            df[df.event == "scale_down"].detail
        )
    )

    print(
        "Scaleup sum:",
        sum(
            detail["node_count"] for detail in
            df[df.event == "scale_up"].detail
        )
    )
    
    print("====================")

    print(df.groupby("event")["time"].count())
