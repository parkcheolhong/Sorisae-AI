# FILE-ID: FILE-BACKEND-CORE-MODELS-PY
# SECTION-ID: SECTION-BACKEND-CORE-MODELS-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-CORE-MODELS-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-CORE-MODELS-PY-001

class RuntimeEvent:
    def __init__(self, event: str = 'runtime_event') -> None:
        self.event = event

class ModelRegistryEntry:
    def __init__(self, version: str = 'bootstrap') -> None:
        self.version = version
