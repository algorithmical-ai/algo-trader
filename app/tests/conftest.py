import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mocker():
    from pytest_mock import MockerFixture
    return MockerFixture

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    store = {}
    mock.hset.side_effect = lambda key, mapping=None, **kwargs: store.update(mapping or kwargs)
    mock.hgetall.side_effect = lambda key: store if key in store else {}
    mock.delete.side_effect = lambda key: store.pop(key, None)
    mock.keys.side_effect = lambda pattern: [k for k in store.keys() if pattern in k]
    return mock
