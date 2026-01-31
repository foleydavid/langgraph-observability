import os
import re
from pathlib import Path


def safely_get_env(env_var_name: str) -> str:
    """Return environment variable value or raise verbose error."""

    if env_var_value := os.getenv(env_var_name):
        return env_var_value
    raise EnvironmentError(f"Environment Variable Missing: {env_var_name}")


def get_validated_oracle_password(env_var_name: str = "ORACLE_AGENT_PASSWORD") -> str:
    """Return Oracle password from env var after validating it meets policy requirements.

    Oracle Autonomous Database enforces password policies. This function validates
    the password before attempting to create a user, providing a clear error message
    instead of a cryptic ORA-28219 error.

    Requirements:
        - At least 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
    """
    password = safely_get_env(env_var_name)

    errors = []
    if len(password) < 12:
        errors.append(f"at least 12 characters (got {len(password)})")
    if not re.search(r"[A-Z]", password):
        errors.append("at least 1 uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least 1 lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("at least 1 digit")

    if errors:
        raise ValueError(
            f"Invalid {env_var_name}: Oracle password policy requires {', '.join(errors)}. "
            f"Example valid password: MovieAgent_2024"
        )

    return password


def resolve_absolute_path(relative_location: str) -> str:
    """Resolve path relative to project root (assumes helpers.py is in shared/)."""

    project_root = Path(__file__).parent.parent
    return str(project_root / relative_location)
