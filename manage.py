#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from django.core.management import execute_from_command_line

# Add Rust library path to Python sys.path
rust_lib_path = os.path.abspath("rust/target/release")
sys.path.insert(0, rust_lib_path)

# Import RustTokioRuntime from Rust library
from myrustlib import RustTokioRuntime

# Define a Python module
MODULE_NAME = "bigbot.rusttokioruntime"

# Ensure that the RustTokioRuntime class is available
if not hasattr(sys.modules[__name__], "RustTokioRuntime"):
    raise ImportError(
        f"{MODULE_NAME} is missing the RustTokioRuntime class."
    )

# Export RustTokioRuntime as a Python module
RustTokioRuntimePy = RustTokioRuntime.into_py(MODULE_NAME, "RustTokioRuntime")

# Export RustTokioRuntimePy to be used in other Python modules
__all__ = ["RustTokioRuntimePy"]


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.development')
    try:
        execute_from_command_line(sys.argv)
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc


if __name__ == '__main__':
    main()
