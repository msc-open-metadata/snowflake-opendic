import re
import pandas as pd
import requests
import snowflake.connector
from snowflake_opendic.prettyResponse import PrettyResponse
from snowflake_opendic.client import OpenDicClient
from snowflake_opendic.patterns.openDicPatterns import OpenDicPatterns 

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
            match = re.match(pattern, sql_cleaned, re.IGNORECASE)
            if match:
                return self._handle_opendic_command(command_type, match)
        return self.cursor.execute(sql_cleaned)
    
    def _handle_opendic_command(self, command_type: str, match: re.Match):
        try:
            if command_type == "show_types":
                response = self.client.get("/objects")
                return self._pretty_print_result({"success": "Object types retrieved", "response": response})

            elif command_type == "show":
                object_type = match.group("object_type")
                response = self.client.get(f"/objects/{object_type}")
                return self._pretty_print_result({"success": f"{object_type}s retrieved", "response": response})

            elif command_type == "show_platforms_all":
                response = self.client.get("/platforms")
                return self._pretty_print_result({"success": "All platforms retrieved", "response": response})

            elif command_type == "show_platforms_for_object":
                object_type = match.group("object_type")
                response = self.client.get(f"/objects/{object_type}/platforms")
                return self._pretty_print_result({"success": f"Platforms for {object_type}", "response": response})

            elif command_type == "sync":
                object_type = match.group("object_type")
                platform = match.group("platform").lower()
                response = self.client.get(f"/objects/{object_type}/platforms/{platform}/pull")
                return self._pretty_print_result({"success": "Sync retrieved", "response": response})

            return self._pretty_print_result({"error": f"Unhandled OpenDic command: {command_type}"})
        
        except requests.exceptions.HTTPError as e:
            return self._pretty_print_result({
                "error": "HTTP Error",
                "message": str(e),
                "Catalog Response": e.response.json() if e.response else None
            })

        except Exception as e:
            return self._pretty_print_result({"error": "Unexpected error", "message": str(e)})


    def _pretty_print_result(self, result: dict):
        response = result.get("response")
        if isinstance(response, list) and all(isinstance(item, dict) for item in response):
            return pd.DataFrame(response)
        elif isinstance(response, dict):
            return pd.DataFrame([response])
        else:
            return PrettyResponse(result)
