#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

try:
    from unittest import mock
except ImportError:
    import mock
import os
import pytest
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse
import urllib3

from tdclient import api
from tdclient import version
from tdclient.test.test_helper import *

def setup_function(function):
    unset_environ()

def test_apikey_success():
    td = api.API("apikey")
    assert td.apikey == "apikey"

def test_apikey_from_environ():
    os.environ["TD_API_KEY"] = "APIKEY"
    td = api.API()
    assert td.apikey == "APIKEY"

def test_apikey_failure():
    with pytest.raises(ValueError) as error:
        api.API()
    assert error.value.args == ("no API key given",)

def test_default_user_agent():
    td = api.API("apikey")
    assert td._user_agent.startswith("TD-Client-Python: %s" % version.__version__)

def test_user_agent_from_keyword():
    td = api.API("apikey", user_agent="user_agent")
    assert td._user_agent == "user_agent"

def test_default_endpoint():
    td = api.API("apikey")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "https://api.treasuredata.com/" == url

def test_endpoint_from_environ():
    os.environ["TD_API_SERVER"] = "http://api1.example.com"
    td = api.API("apikey")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "http://api1.example.com" == url

def test_endpoint_from_keyword():
    td = api.API("apikey", endpoint="http://api2.example.com")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "http://api2.example.com" == url

def test_endpoint_prefer_keyword():
    os.environ["TD_API_SERVER"] = "http://api1.example.com"
    td = api.API("apikey", endpoint="http://api2.example.com")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "http://api2.example.com" == url

def test_http_endpoint_with_custom_port():
    td = api.API("apikey", endpoint="http://api.example.com:8080/")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "http://api.example.com:8080/" == url

def test_https_endpoint():
    td = api.API("apikey", endpoint="https://api.example.com/")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "https://api.example.com/" == url

def test_https_endpoint_with_custom_path():
    td = api.API("apikey", endpoint="https://api.example.com/v1/")
    assert isinstance(td.http, urllib3.PoolManager)
    url, headers = td.build_request()
    assert "https://api.example.com/v1/" == url

def test_http_proxy_from_environ():
    os.environ["HTTP_PROXY"] = "proxy1.example.com:8080"
    td = api.API("apikey")
    assert isinstance(td.http, urllib3.ProxyManager)
    assert td.http.proxy.url == "http://proxy1.example.com:8080"

def test_http_proxy_from_keyword():
    td = api.API("apikey", http_proxy="proxy2.example.com:8080")
    assert isinstance(td.http, urllib3.ProxyManager)
    assert td.http.proxy.url == "http://proxy2.example.com:8080"

def test_http_proxy_prefer_keyword():
    os.environ["HTTP_PROXY"] = "proxy1.example.com:8080"
    td = api.API("apikey", http_proxy="proxy2.example.com:8080")
    assert isinstance(td.http, urllib3.ProxyManager)
    assert td.http.proxy.url == "http://proxy2.example.com:8080"

def test_http_proxy_with_scheme():
    os.environ["HTTP_PROXY"] = "http://proxy1.example.com:8080/"
    td = api.API("apikey")
    assert isinstance(td.http, urllib3.ProxyManager)
    assert td.http.proxy.url == "http://proxy1.example.com:8080/"

def test_timeout():
    with mock.patch("tdclient.api.urllib3") as urllib3:
        td = api.API("apikey", timeout=12345)
        assert urllib3.PoolManager.called
        args, kwargs = urllib3.PoolManager.call_args
        assert kwargs["timeout"] == 12345

def test_connect_timeout():
    with mock.patch("tdclient.api.urllib3") as urllib3:
        td = api.API("apikey", connect_timeout=1, read_timeout=2, send_timeout=4)
        assert urllib3.PoolManager.called
        args, kwargs = urllib3.PoolManager.call_args
        assert kwargs["timeout"] == 7

def test_get_success():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(200, b"body"),
    ]
    td.http.request.side_effect = responses
    with td.get("/foo", {"bar": "baz"}) as response:
        args, kwargs = td.http.request.call_args
        assert args == ("GET", "https://api.treasuredata.com/foo")
        assert kwargs["fields"] == {"bar": "baz"}
        assert sorted(kwargs["headers"].keys()) == ["accept-encoding", "authorization", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"body"
    assert not td.sleep.called

def test_get_error():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(404, b"not found"),
    ]
    td.http.request.side_effect = responses
    with td.get("/foo", {"bar": "baz"}) as response:
        args, kwargs = td.http.request.call_args
        assert args == ("GET", "https://api.treasuredata.com/foo")
        assert kwargs["fields"] == {"bar": "baz"}
        assert sorted(kwargs["headers"].keys()) == ["accept-encoding", "authorization", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 404
        assert body == b"not found"
    assert not td.sleep.called

def test_get_retry_success():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(500, b"failure1"),
        make_raw_response(503, b"failure2"),
        make_raw_response(200, b"success1"),
    ]
    td.http.request.side_effect = responses
    with td.get("/foo", {"bar": "baz"}) as response:
        args, kwargs = td.http.request.call_args
        assert args == ("GET", "https://api.treasuredata.com/foo")
        assert kwargs["fields"] == {"bar": "baz"}
        assert sorted(kwargs["headers"].keys()) == ["accept-encoding", "authorization", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"success1"
        assert td.sleep.called
        sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
        assert len(sleeps) == len(responses) - 1
        assert sum(sleeps) < td._max_cumul_retry_delay

def test_get_failure():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    td.http.request.return_value = make_raw_response(500, b"failure")
    with pytest.raises(api.APIError) as error:
        with td.get("/foo", {"bar": "baz"}) as response:
            pass
    assert td.sleep.called
    sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
    assert td._max_cumul_retry_delay < sum(sleeps)

def test_post_success():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(200, b"body"),
    ]
    td.http.request.side_effect = responses
    with td.post("/foo", {"bar": "baz"}) as response:
        args, kwargs = td.http.request.call_args
        assert args == ("POST", "https://api.treasuredata.com/foo")
        assert kwargs["fields"] == {"bar": "baz"}
        assert sorted(kwargs["headers"].keys()) == ["authorization", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"body"
    assert not td.sleep.called

def test_post_retry_success():
    td = api.API("APIKEY", retry_post_requests=True)
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(500, b"failure1"),
        make_raw_response(503, b"failure2"),
        make_raw_response(200, b"success1"),
    ]
    td.http.request.side_effect = responses
    with td.post("/foo", {"bar": "baz"}) as response:
        args, kwargs = td.http.request.call_args
        assert args == ("POST", "https://api.treasuredata.com/foo")
        assert kwargs["fields"] == {"bar": "baz"}
        assert sorted(kwargs["headers"].keys()) == ["authorization", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"success1"
        assert td.sleep.called
        sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
        assert len(sleeps) == len(responses) - 1
        assert sum(sleeps) < td._max_cumul_retry_delay

def test_post_never_retry():
    td = api.API("APIKEY", retry_post_requests=False)
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    responses = [
        make_raw_response(500, b"failure"),
    ]
    td.http.request.side_effect = responses
    with pytest.raises(api.APIError) as error:
        with td.post("/foo", {"bar": "baz"}) as response:
            pass
    assert not td.sleep.called

def test_post_failure():
    td = api.API("APIKEY", retry_post_requests=True)
    td.sleep = mock.MagicMock()
    td.http.request = mock.MagicMock()
    td.http.request.return_value = make_raw_response(500, b"failure")
    with pytest.raises(api.APIError) as error:
        with td.post("/foo", {"bar": "baz"}) as response:
            pass
    assert td.sleep.called
    sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
    assert td._max_cumul_retry_delay < sum(sleeps)

def test_put_success():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.urlopen = mock.MagicMock()
    responses = [
        make_raw_response(200, b"body"),
    ]
    td.http.urlopen.side_effect = responses
    with td.put("/foo", b"body", 7) as response:
        args, kwargs = td.http.urlopen.call_args
        assert args == ("PUT", "https://api.treasuredata.com/foo")
        assert sorted(kwargs["headers"].keys()) == ["authorization", "content-length", "content-type", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"body"
    assert not td.sleep.called

def test_put_retry_success():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.urlopen = mock.MagicMock()
    responses = [
        make_raw_response(500, b"failure1"),
        make_raw_response(503, b"failure2"),
        make_raw_response(200, b"success1"),
    ]
    td.http.urlopen.side_effect = responses
    with td.put("/foo", b"body", 7) as response:
        args, kwargs = td.http.urlopen.call_args
        assert args == ("PUT", "https://api.treasuredata.com/foo")
        assert sorted(kwargs["headers"].keys()) == ["authorization", "content-length", "content-type", "date", "user-agent"]
        status, body = response.status, response.read()
        assert status == 200
        assert body == b"success1"
        assert td.sleep.called
        sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
        assert len(sleeps) == len(responses) - 1
        assert sum(sleeps) < td._max_cumul_retry_delay

def test_put_failure():
    td = api.API("APIKEY")
    td.sleep = mock.MagicMock()
    td.http.urlopen = mock.MagicMock()
    td.http.urlopen.return_value = make_raw_response(500, b"error")
    with pytest.raises(api.APIError) as error:
        with td.put("/foo", b"body", 7) as response:
            pass
    assert td.sleep.called
    sleeps = [ args[0] for (args, kwargs) in td.sleep.call_args_list ]
    assert td._max_cumul_retry_delay < sum(sleeps)
