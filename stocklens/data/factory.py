"""Factory to instantiate data providers seamlessly."""
from typing import Optional, Dict, Type
from stocklens.config import DEFAULT_PROVIDER
from stocklens.data.base import BaseDataProvider
from stocklens.data.yfinance_provider import YFinanceProvider
from stocklens.data.demo_provider import DemoDataProvider
from stocklens.data.moneycontrol_scraper import MoneycontrolScraperProvider

_PROVIDER_MAP: Dict[str, Type[BaseDataProvider]] = {
    "yfinance": YFinanceProvider,
    "moneycontrol": MoneycontrolScraperProvider,
    "demo": DemoDataProvider,
}


def get_data_provider(name: Optional[str] = None) -> BaseDataProvider:
    """Return an instance of the requested data provider.
    
    Supported names: 'yfinance', 'moneycontrol', 'demo'.
    Defaults to configuration if not specified.
    """
    provider_name = (name or DEFAULT_PROVIDER).lower().strip()
    provider_class = _PROVIDER_MAP.get(provider_name)
    if not provider_class:
        available = ", ".join(_PROVIDER_MAP.keys())
        raise ValueError(f"Unknown data provider '{provider_name}'. Available providers: {available}")
    return provider_class()
