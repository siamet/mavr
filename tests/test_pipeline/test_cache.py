"""Tests for InMemoryCache."""

import time

import pytest

from src.pipeline.cache import InMemoryCache


class TestInMemoryCache:
    @pytest.fixture
    def cache(self) -> InMemoryCache:
        return InMemoryCache()

    def test_set_and_get(self, cache: InMemoryCache) -> None:
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self, cache: InMemoryCache) -> None:
        assert cache.get("missing") is None

    def test_exists(self, cache: InMemoryCache) -> None:
        cache.set("key1", "value1")
        assert cache.exists("key1")
        assert not cache.exists("missing")

    def test_delete(self, cache: InMemoryCache) -> None:
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_missing_key(self, cache: InMemoryCache) -> None:
        # Should not raise
        cache.delete("missing")

    def test_clear(self, cache: InMemoryCache) -> None:
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_size(self, cache: InMemoryCache) -> None:
        assert cache.size == 0
        cache.set("a", 1)
        assert cache.size == 1

    def test_overwrite(self, cache: InMemoryCache) -> None:
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"

    def test_stores_various_types(self, cache: InMemoryCache) -> None:
        cache.set("str", "hello")
        cache.set("int", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        assert cache.get("str") == "hello"
        assert cache.get("int") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}
