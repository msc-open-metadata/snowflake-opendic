import argparse

import snowflake.connector

from .snow_opendic import get_latency, snowflake_connect


def cli():
    ## take a --flag point to a json file
    parser = argparse.ArgumentParser(prog="snow-opendic-cli")
    parser.add_argument(
        "-c",
        "--config-path",
        type=str,
        help="Path to a TOML file with snowflake config. Keys: snowflake_conf.account, snowflake_conf.user, snowflake_conf.password, snowflake_conf.database, snowflake_conf.schema, snowflake_conf.warehouse",
    )
    args = parser.parse_args()

    if args.config_path:
        print(f"Parsing snowflake config at: {args.config_path}")
        conn = snowflake_connect(args.config_path)
    else:
        print("Config file path not provided. Attempting default connection")
        try:
            conn = snowflake.connector.connect()
        except Exception as e:
            print("No successful connection with ~/.snowflake/connection.yml")
            print(f"Error: {e}")
            exit(1)

    try:
        seconds, server = get_latency(conn)
        print(f"Connection Established | Server: {server} | Latency: {seconds} ✔︎")
    except Exception as e:
        print(f"Error connecting to snowflake: {e}")
        exit(1)
