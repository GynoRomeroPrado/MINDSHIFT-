"""
Integrations Module
HRIS and third-party integrations
"""
from .hris import HRISConnector, BambooHRConnector, WorkdayConnector, GustoConnector

__all__ = ['HRISConnector', 'BambooHRConnector', 'WorkdayConnector', 'GustoConnector']
