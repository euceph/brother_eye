import os
import tempfile
import logging
from typing import Optional

# set up logging
logger = logging.getLogger(__name__)


def create_temp_directory() -> str:
    """create temporary directory.

    returns:
        path to temp directory
    """
    temp_home = tempfile.mkdtemp()
    logger.debug(f"created temp dir: {temp_home}")
    return temp_home


def cleanup_temp_directory(dir_path: Optional[str]) -> bool:
    """clean up temporary directory.

    args:
        dir_path: dir to clean up

    returns:
        true if successful, false otherwise
    """
    if dir_path and os.path.exists(dir_path):
        try:
            import shutil
            shutil.rmtree(dir_path)
            logger.debug(f"cleaned up temp dir: {dir_path}")
            return True
        except Exception as e:
            logger.error(f"error cleaning temp dir: {e}")
            return False
    return False