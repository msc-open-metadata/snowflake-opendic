from datetime import datetime

import snowflake.connector
import toml


def connect(snowflake_conf: dict) -> snowflake.connector.connection.SnowflakeConnection:
    """
    Connect to Snowflake using the provided configuration.

    Args:
        snowflake_conf (dict): Snowflake connection configuration. Example:
            account=config["snowflake_conf"]["account"],
            user=config["snowflake_conf"]["user"],
            password=config["snowflake_conf"]["password"],
            database=config["snowflake_conf"]["database"],
            schema=config["snowflake_conf"]["schema"],
            warehouse=config["snowflake_conf"]["warehouse"],

    Returns:
        snowflake.connector.connection.SnowflakeConnection: Snowflake connection object.
    """
    return snowflake.connector.connect(**snowflake_conf)


def get_latency(conn: snowflake.connector.connection.SnowflakeConnection) -> tuple[float, tuple]:
    """Get the latency of a Snowflake connection."""
    with conn.cursor() as cur:
        start_time = datetime.now()
        # Fix by explicitly passing None for the callback parameters
        try:
            cur.execute("SELECT CURRENT_TIMESTAMP();")  # type: ignore
        except Exception as e:
            print(f"Error executing query: {e}")
        end_time = datetime.now()
        fetch = cur.fetchone()
    return ((end_time - start_time).total_seconds(), fetch[0].tzinfo)  # type: ignore


def snowflake_check_connection(conn: snowflake.connector.SnowflakeConnection):
    seconds, server = get_latency(conn)
    print(f"Connection Established | Server: {server} | Latency: {seconds} ✔︎")


def snowflake_connect(config_path: str = "None"):
    if config_path == "None":
        print("Config file path not provided. Attempting default connection")
        return snowflake.connector.connect()
    if config_path.split(".")[-1] != "toml":
        raise ValueError("Config file must be in TOML format")

    with open(config_path, "r") as f:
        config = toml.load(f)

    return connect(config["snowflake_conf"])
