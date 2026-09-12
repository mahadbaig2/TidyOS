"""TidyOS Storage Package."""

from tidyos.storage.models import (
    ManagedRoot,
    DirectoryRecord,
    FileRecord,
    ProtectedRoot,
    ActionRecord,
)
from tidyos.storage.roots import (
    RootValidationError,
    validate_candidate_root,
    normalize_root_path,
    is_path_in_managed_scope,
)
from tidyos.storage.schema import init_db, SCHEMA_VERSION
from tidyos.storage.repository import StorageRepository

__all__ = [
    "ManagedRoot",
    "DirectoryRecord",
    "FileRecord",
    "ProtectedRoot",
    "ActionRecord",
    "RootValidationError",
    "validate_candidate_root",
    "normalize_root_path",
    "is_path_in_managed_scope",
    "init_db",
    "SCHEMA_VERSION",
    "StorageRepository",
]
