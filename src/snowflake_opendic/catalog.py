import ast
import json
import re
import textwrap
from typing import Any

import pandas as pd
import requests
from pydantic import ValidationError
from snowflake.connector import SnowflakeConnection

from snowflake_opendic.client import OpenDicClient
from snowflake_opendic.model.openapi_models import (
    CreatePlatformMappingRequest,
    CreateUdoRequest,
    DefineUdoRequest,
    PlatformMapping,
    Statement,
    Udo,
)
from snowflake_opendic.patterns.opendic_patterns import OpenDicPatterns
from snowflake_opendic.pretty_pesponse import PrettyResponse
from snowflake_opendic.snow_opendic import snowflake_check_connection


class OpenDicSnowflakeCatalog:
    def __init__(self, snowflake_conn: SnowflakeConnection, api_url: str, client_id: str, client_secret: str):
        self.api_url = api_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.conn: SnowflakeConnection = snowflake_conn
        snowflake_check_connection(self.conn)
        self.client: OpenDicClient = OpenDicClient(api_url, f"{client_id}:{client_secret}")
        self.opendic_patterns = OpenDicPatterns.compiled_patterns()

    def sql(self, sql_text: str):
        sql_cleaned = sql_text.strip()
        
        for command_type, pattern in self.opendic_patterns:
            match = pattern.match(sql_cleaned)
            if match:
                return self._handle_opendic_command(command_type, match, sql_text)
            
        with self.conn.cursor() as cursor:
            return cursor.execute(sql_text).fetchall()

    def _handle_opendic_command(self, command_type: str, match: re.Match, sql_text : str):
        try:
            if command_type == "create":
                object_type = match.group("object_type")
                name = match.group("name")
                alias = match.group("alias")
                properties = match.group("properties")
                create_props = json.loads(properties) if properties else None
                udo = Udo(type=object_type, name=name, props=create_props)
                create_request = CreateUdoRequest(udo=udo)
                response = self.client.post(f"/objects/{object_type}", create_request.model_dump())
                return self._pretty_print_result({"success": "Object created successfully", "response": response})
            elif command_type == "create_batch":
                object_type = match.group("object_type")
                properties_list = json.loads(match.group("properties"))  # Already a list of dicts

                udo_objects: list[dict[str, Any]] = []
                for item in properties_list:
                    name = item.pop("name")
                    udo_object = Udo(type=object_type, name=name, props=item).model_dump()
                    udo_objects.append(udo_object)

                response = self.client.post(f"/objects/{object_type}/batch", udo_objects)
                return self.pretty_print_result({"success": "Batch created", "response": response})
            elif command_type == "alter":
                object_type = match.group("object_type")
                name = match.group("name")
                properties = match.group("properties")
                alter_props: dict[str, str] = json.loads(properties) if properties else None        
                udo_object = Udo(type=object_type, name=name, props=alter_props)
                alter_request = CreateUdoRequest(udo=udo_object)
                payload = alter_request.model_dump()
                response = self.client.put(f"/objects/{object_type}/{name}", payload)
                return self._pretty_print_result({"success": "Object altered successfully", "response": response})
            elif command_type == "define":
                udoType = match.group("udoType")
                properties = match.group("properties")
                define_props = json.loads(properties) if properties else None
                self._validate_data_type(define_props)
                define_request = DefineUdoRequest(udoType=udoType, properties=define_props)
                response = self.client.post("/objects", define_request.model_dump())
                return self._pretty_print_result({"success": "Object defined successfully", "response": response})

            elif command_type == "drop":
                object_type = match.group("object_type")
                response = self.client.delete(f"/objects/{object_type}")
                return self._pretty_print_result({"success": "Object dropped successfully", "response": response})

            elif command_type == "add_mapping":
                object_type = match.group("object_type")
                platform = match.group("platform")
                syntax = match.group("syntax").strip()
                properties = match.group("props")
                if syntax.startswith('"') and syntax.endswith('"'):
                    syntax = syntax[1:-1]
                object_dump_map = json.loads(properties)
                mapping_request = CreatePlatformMappingRequest(
                    platformMapping=PlatformMapping(
                        typeName=object_type, platformName=platform, syntax=syntax, objectDumpMap=object_dump_map
                    )
                )
                response = self.client.post(f"/objects/{object_type}/platforms/{platform}", mapping_request.model_dump())
                return self._pretty_print_result({"success": "Mapping added successfully", "response": response})

            elif command_type == "sync":
                object_type = match.group("object_type")
                platform = match.group("platform").lower()
                response = self.client.get(f"/objects/{object_type}/platforms/{platform}/pull")
                statements = [Statement.model_validate(item) for item in response]
                return self.dump_handler(statements)
            elif command_type == "sync_all":
                platform: str = match.group("platform").lower()
                response = self.client.get(f"/platforms/{platform}/pull")
                statements = [Statement.model_validate(item) for item in response]
                return self.dump_handler(statements)
            
            elif command_type == "show_types":
                response = self.client.get("/objects")
                return self._pretty_print_result({"success": "Object types retrieved successfully", "response": response})

            elif command_type == "show":
                object_type = match.group("object_type")
                response = self.client.get(f"/objects/{object_type}")
                return self._pretty_print_result({"success": "Objects retrieved successfully", "response": response})

            elif command_type == "show_platforms_all":
                response = self.client.get("/platforms")
                return self._pretty_print_result({"success": "Platforms retrieved successfully", "response": response})

            elif command_type == "show_platforms_for_object":
                object_type = match.group("object_type")
                response = self.client.get(f"/objects/{object_type}/platforms")
                return self._pretty_print_result({"success": "Platforms retrieved successfully", "response": response})

            elif command_type == "show_mapping_for_object_and_platform":
                object_type = match.group("object_type")
                platform = match.group("platform")
                response = self.client.get(f"/objects/{object_type}/platforms/{platform}")
                return self._pretty_print_result({"success": "Mapping retrieved successfully", "response": response})

            elif command_type == "show_mappings_for_platform":
                platform = match.group("platform")
                response = self.client.get(f"/platforms/{platform}")
                return self._pretty_print_result(
                    {"success": "Mappings for platform retrieved successfully", "response": response}
                )

            elif command_type == "drop_mapping_for_platform":
                platform = match.group("platform")
                response = self.client.delete(f"/platforms/{platform}")
                return self._pretty_print_result({"success": "Platform's mappings dropped successfully", "response": response})

            return self._pretty_print_result({"error": f"Unhandled OpenDic command: {command_type}"})

        except json.JSONDecodeError as e:
            return self._pretty_print_result({"error": "Invalid JSON in PROPS", "details": str(e)})
        except ValidationError as e:
            return self._pretty_print_result({"error": "Pydantic validation failed", "details": str(e)})
        except requests.exceptions.HTTPError as e:
            # Check if httpcode is 401
            if e.response.status_code == 401:
                self.client.refresh_oauth_token(f"{self.client_id}:{self.client_secret}")
                self.sql(sql_text)
            else:
                return self._pretty_print_result(
                    {"error": "HTTP Error", "details": str(e), "Catalog Response": e.response.json() if e.response else None}
                )
        except Exception as e:
            return self._pretty_print_result({"error": "Unexpected error", "details": str(e)})

    # Helper method to extract SQL statements from Polaris response and execute
    def dump_handler(self, response: list[Statement]):
        """
        Extracts SQL statements from the Polaris response and executes them using Spark.

        Args:
            response (list): List of Statement objects.

        Returns:
            dict: Execution result with status.
        """
        if not response:
            return self.pretty_print_result({"error": "No statements found in response"})

        execution_results = []

        print(f"Executing {len(response)} SQL statements...\n")
        for statement in response:
            sql_text = statement.definition
            
            # Normalizes indentation (keep relative indents! - should work with the initial indentation of the SQL statement we discussed)
            formatted_sql = textwrap.dedent(sql_text).strip()
            print(f"Formatted SQL:\n{formatted_sql}")


            # Wrap in triple quotes (this just shouldnt be necessary.. xd - outcomment this first, Andreas)
            multiline_sql = f'''"""\n{formatted_sql}\n"""'''
            print(f"Executing SQL (multilined SQL): \n{multiline_sql}")
            # Execute
            
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(multiline_sql)  # Execute the SQL statement
                execution_results.append({"sql": multiline_sql, "status": "executed"})
            except Exception as e:
                execution_results.append({"sql": multiline_sql, "status": "failed", "error": str(e)})

        return self._pretty_print_result({"executions": execution_results})

    def _validate_data_type(self, props: dict[str, str]) -> dict[str, str]:
        """
        Validate the data type against a predefined set of valid types.

        Args:
            proerties (dict): The properties dictionary to validate.

        Returns:
            dict: A dictionary with the validation result.
        """
        # The same set of valid data types as in the OpenDic API - UserDefinedEntitySchema (+ int and double)
        valid_data_types = {
            "string",
            "number",
            "boolean",
            "float",
            "date",
            "array",
            "list",
            "map",
            "object",
            "variant",
            "int",
            "double",
        }

        for key, value in props.items():
            if value.lower() not in valid_data_types:
                raise ValueError(f"Invalid data type '{value}' for key '{key}'")

        return {"success": "Data types validated successfully"}

    def _pretty_print_result(self, result: dict):
        """
        Pretty print the result in a readable format.
        """
        pd.set_option("display.width", None)  # Auto-detect terminal width
        pd.set_option("display.max_colwidth", None)  # Show full content of each cell
        pd.set_option("display.max_rows", None)  # Show all rows
        pd.set_option("display.expand_frame_repr", False)  # Don't wrap to multiple lines

        response = result.get("response")

        # Polaris-spec-compliant "good" responses, so objects or lists of objects
        if isinstance(response, list) and all(isinstance(item, dict) for item in response):
            return pd.DataFrame(response)

        elif isinstance(response, dict):
            return pd.DataFrame([response])

        # Everything else — errors, messages, etc.
        return PrettyResponse(result)
