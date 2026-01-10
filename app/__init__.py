"""SkillProof AI package initialization."""

import logging


def _configure_logging() -> None:
	logger = logging.getLogger("skillproof")
	if logger.handlers:
		return
	handler = logging.StreamHandler()
	handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)
	logger.propagate = False


_configure_logging()
