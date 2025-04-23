import json
import re
import pandas as pd
from pydantic import ValidationError
import requests
import snowflake.connector
from snowflake_opendic.prettyResponse import PrettyResponse
from snowflake_opendic.client import OpenDicClient
from snowflake_opendic.patterns.openDicPatterns import OpenDicPatterns 

from snowflake_opendic.model.openapi_models import (
    CreatePlatformMappingRequest,
    CreateUdoRequest,
    DefineUdoRequest,
    PlatformMapping,
    Statement,
    Udo,
)


class OpenDicSnowflakeCatalog:
    def __init__(self, config: dict, api_url: str):
        self.conn = snowflake.connector.connect(**config)
        self.cursor = self.conn.cursor()
        self.client = OpenDicClient(api_url, config.get("token"))
        self._init_patterns()

    def _init_patterns(self):
        self.opendic_patterns = {
            "create": OpenDicPatterns.create_pattern(),
            "define": OpenDicPatterns.define_pattern(),
            "drop": OpenDicPatterns.drop_pattern(),
            "add_mapping": OpenDicPatterns.add_mapping_pattern(),
            "sync": OpenDicPatterns.sync_pattern(),
            "show_types": OpenDicPatterns.show_types_pattern(),
            "show": OpenDicPatterns.show_pattern(),
            "show_platforms_all": OpenDicPatterns.show_platforms_all_pattern(),
            "show_platforms_for_object": OpenDicPatterns.show_platforms_for_object_pattern(),
            "show_mapping_for_object_and_platform": OpenDicPatterns.show_mapping_for_object_and_platform_pattern(),
            "show_mappings_for_platform": OpenDicPatterns.show_mappings_for_platform_pattern(),
            "drop_mapping_for_platform": OpenDicPatterns.drop_mapping_for_platform_pattern(),
        }

    def sql(self, sql_text: str):
        sql_cleaned = sql_text.strip()
        for command_type, pattern in self.opendic_patterns.items():
            flags = re.IGNORECASE | re.DOTALL if command_type == "add_mapping" else re.IGNORECASE
            match = re.match(pattern, sql_cleaned, flags)
            if match:
                return self._handle_opendic_command(command_type, match)
        return self.cursor.execute(sql_cleaned)
    
    def _handle_opendic_command(self, command_type: str, match: re.Match):
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
                        typeName=object_type,
                        platformName=platform,
                        syntax=syntax,
                        objectDumpMap=object_dump_map
                    )
                )
                response = self.client.post(
                    f"/objects/{object_type}/platforms/{platform}",
                    mapping_request.model_dump()
                )
                return self._pretty_print_result({"success": "Mapping added successfully", "response": response})

            elif command_type == "sync":
                object_type = match.group("object_type")
                platform = match.group("platform").lower()
                response = self.client.get(f"/objects/{object_type}/platforms/{platform}/pull")
                statements = [Statement.model_validate(item) for item in response]
                return self._dump_handler(statements)

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
                return self._pretty_print_result({"success": "Mappings for platform retrieved successfully", "response": response})

            elif command_type == "drop_mapping_for_platform":
                platform = match.group("platform")
                response = self.client.delete(f"/platforms/{platform}")
                return self._pretty_print_result({"success": "Platform's mappings dropped successfully", "response": response})
            
            return self._pretty_print_result({"error": f"Unhandled OpenDic command: {command_type}"})
        
        except json.JSONDecodeError as e:
            return self._pretty_print_result({
                "error": "Invalid JSON in PROPS",
                "details": str(e)
            })
        except ValidationError as e:
            return self._pretty_print_result({
                "error": "Pydantic validation failed",
                "details": str(e)
            })
        except requests.exceptions.HTTPError as e:
            return self._pretty_print_result({
                "error": "HTTP Error",
                "details": str(e),
                "Catalog Response": e.response.json() if e.response else None
            })
        except Exception as e:
            return self._pretty_print_result({
                "error": "Unexpected error",
                "details": str(e)
            })

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
        for statement in response:
            sql_text = statement.definition.strip()  # Extract SQL statement from the response
            if sql_text:
                try:
                    result = self.sparkSession.sql(sql_text)  # Execute in Spark
                    execution_results.append({"sql": sql_text, "status": "executed"})
                except Exception as e:
                    execution_results.append({"sql": sql_text, "status": "failed", "error": str(e)})

        return self.pretty_print_result({"success": True, "executions": execution_results})
    
    def validate_data_type(self, props: dict[str, str]) -> dict[str, str]:
        """
        Validate the data type against a predefined set of valid types.

        Args:
            proerties (dict): The properties dictionary to validate.

        Returns:
            dict: A dictionary with the validation result.
        """
        # The same set of valid data types as in the OpenDic API - UserDefinedEntitySchema (+ int and double)
        valid_data_types = {"string", "number", "boolean", "float", "date", "array", "list", "map", "object", "variant", "int", "double"}

        for key, value in props.items():
            if value.lower() not in valid_data_types:
                raise ValueError(f"Invalid data type '{value}' for key '{key}'")
            
        return {"success": "Data types validated successfully"}
    
    def _pretty_print_result(self, result: dict):
        response = result.get("response")
        if isinstance(response, list) and all(isinstance(item, dict) for item in response):
            return pd.DataFrame(response)
        elif isinstance(response, dict):
            return pd.DataFrame([response])
        else:
            return PrettyResponse(result)
