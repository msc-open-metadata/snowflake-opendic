class OpenDicPatterns:

    @staticmethod
    def create_pattern():
        return (
            r"^create"
            r"(?:\s+or\s+replace)?"
            r"(?:\s+temporary)?"
            r"\s+open\s+(?P<object_type>\w+)"
            r"\s+(?P<name>\w+)"
            r"(?:\s+if\s+not\s+exists)?"
            r"(?:\s+as\s+(?P<alias>\w+))?"
            r"(?:\s+props\s*(?P<properties>\{[\s\S]*\}))?"
        )

    @staticmethod
    def define_pattern():
        return (
            r"^define"
            r"\s+open\s+(?P<udoType>\w+)"
            r"(?:\s+props\s*(?P<properties>\{[\s\S]*\}))?"
            r"$"
        )

    @staticmethod
    def drop_pattern():
        return (
            r"^drop"
            r"\s+open\s+(?P<object_type>\w+)"
        )

    @staticmethod
    def add_mapping_pattern():
        return (
            r"^add"
            r"\s+open\s+mapping"
            r"\s+(?P<object_type>\w+)"
            r"\s+platform\s+(?P<platform>\w+)"
            r"\s+syntax\s*\{\s*(?P<syntax>[\s\S]*?)\s*\}"
            r"\s+props\s*(?P<props>\{[\s\S]*?\})"
            r"$"
        )

    @staticmethod
    def sync_pattern():
        return (
            r"^sync"
            r"\s+open\s+(?P<object_type>\w+)\s+for"
            r"\s+(?P<platform>\w+)"
            r"$"
        )

    @staticmethod
    def show_types_pattern():
        return (
            r"^show"
            r"\s+open\s+types$"
        )

    @staticmethod
    def show_pattern():
        return (
            r"^show"
            r"\s+open\s+(?P<object_type>(?!types$)\w+)"
            r"s?$"
        )

    @staticmethod
    def show_platforms_all_pattern():
        return (
            r"^show"
            r"\s+open\s+platforms$"
            r"$"
        )

    @staticmethod
    def show_platforms_for_object_pattern():
        return (
            r"^show"
            r"\s+open\s+platforms\s+for"
            r"\s+(?P<object_type>\w+)"
            r"$"
        )

    @staticmethod
    def show_mapping_for_object_and_platform_pattern():
        return (
            r"^show"
            r"\s+open\s+mapping"
            r"\s+(?P<object_type>\w+)"
            r"\s+platform\s+(?P<platform>\w+)"
            r"$"
        )

    @staticmethod
    def show_mappings_for_platform_pattern():
        return (
            r"^show"
            r"\s+open\s+mappings?\s+for\s+(?P<platform>\w+)"
            r"$"
        )

    @staticmethod
    def drop_mapping_for_platform_pattern():
        return (
            r"^drop"
            r"\s+open\s+mappings?\s+"
            r"for\s+(?P<platform>\w+)"
            r"$"
        )
