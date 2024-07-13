import requests
import logging
from logging import config as logging_config
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from my_store import conf
from my_store.exceptions import HTTPClientError

logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


class HTTPClient:
    retry_strategy = Retry(
        total=conf.ALLOWED_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    def __init__(self):
        self.adapter = HTTPAdapter(max_retries=self.retry_strategy)

    def get_session(self):
        session = requests.Session()
        session.mount("https://", self.adapter)
        session.mount("http://", self.adapter)
        return session

    def make_request(self, method, url, data, headers, auth=None):
        logger.debug(
            "Requesting [%s] %s", method.upper(), url, extra={"payload": data or {}}
        )
        try:
            session = self.get_session()
            response = session.request(method, url, json=data, headers=headers, auth=auth)
        except Exception as e:
            logger.error(
                "Request error occurred while trying to request [%s] %s",
                method,
                url,
                exc_info=e,
                extra={"payload": data or {}},
            )
            raise HTTPClientError(f"Request error occurred: {e}")
        logger.debug(
            "Received [%s] response from %s",
            response.status_code,
            url,
            extra={
                "payload": f"{response.text[:1000]}..."
                if response.text else "{}",
            }
        )
        return response

    def get(self, url, headers=None, data=None):
        response = self.make_request("GET", url, data=data, headers=headers)
        return self._deserialize_response(response)

    def post(self, url, headers=None, data=None, auth=None):
        response = self.make_request("POST", url, data=data, headers=headers, auth=auth)
        return self._deserialize_response(response)

    def put(self, url, headers=None, data=None):
        response = self.make_request("PUT", url, data=data, headers=headers)
        return self._deserialize_response(response)

    def patch(self, url, headers=None, data=None):
        response = self.make_request("PATCH", url, data=data, headers=headers)
        return self._deserialize_response(response)

    def delete(self, url, headers=None, data=None):
        response = self.make_request("DELETE", url, data=data, headers=headers)
        return self._deserialize_response(response)

    @staticmethod
    def _deserialize_response(response):
        if response.status_code >= 400:
            if isinstance(response.content, bytes):
                reason = response.content.decode("utf")
            else:
                reason = (response.content,)

            side = "Client" if response.status_code < 500 else "Server"
            error_message = (
                f"{response.status_code} {side} Error: {reason} for url: {response.url}"
            )
            logger.error(error_message)
            raise HTTPClientError(f"Request error occurred: {error_message}")

        if not response.text:
            return None

        try:
            data = response.json()
        except ValueError as err:
            err_msg = f"Failed to deserialize response content. Error: {err}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        return data
