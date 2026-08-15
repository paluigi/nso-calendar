"""Tests for ForexFactory proxy configuration."""
from app.collectors.forexfactory_collector import ForexFactoryCollector
from app.config import settings


def test_no_proxy_by_default():
    collector = ForexFactoryCollector()
    assert collector._proxies is None


def test_explicit_proxy_used():
    proxy = "http://user:pwd@10.0.0.1:8080"
    collector = ForexFactoryCollector(proxy_url=proxy)
    assert collector._proxies == {"http": proxy, "https": proxy}


def test_empty_string_means_no_proxy():
    """compose passes an empty env var when unset — must not enable a proxy."""
    collector = ForexFactoryCollector(proxy_url="")
    assert collector._proxies is None


def test_proxy_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "ff_proxy_url", "http://u:p@10.0.0.2:3128")
    collector = ForexFactoryCollector()
    assert collector._proxies == {"http": "http://u:p@10.0.0.2:3128", "https": "http://u:p@10.0.0.2:3128"}


def test_mask_credentials():
    assert ForexFactoryCollector._mask_credentials("http://user:pwd@10.0.0.1:8080") == "http://10.0.0.1:8080"
    assert ForexFactoryCollector._mask_credentials("http://10.0.0.1:8080") == "http://10.0.0.1:8080"
