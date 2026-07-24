from typing import Any, TypeVar

# Type alias para representar metadata arbitraria de forma más segura que dict[str, Any]
Metadata = dict[str, Any]

# Type variables para modelos de entrada y salida genéricos
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")
