"""Default root agent — delegates to csv_transformer for playground compatibility."""

from .csv_transformer.agent import root_agent

__all__ = ["root_agent"]
