from random import randint
import requests
import logging
import time
import json


class Downloader:
    """
    Minimalistic API client.
    """

    def __init__(self,
                 timeout=5,
                 wait_between_requests=None):
        """
        :param timeout: number of seconds to wait for request's response. Default: 5 seconds.
        :param wait_between_requests: tuple of waiting time between two consecutive requests.
        If set the downloader will wait up to a random number of milliseconds between min and max.
        By default the downloader does not wait between two consecutive requests.
        """
        self.timeout = timeout
        self.wait_between_requests = wait_between_requests
        self._last_req = None

    def _get(self, url, params, headers=None):
        """
        :param url: url of the request
        :param params: query parameters
        :param headers: headers
        :return: parsed json response if request succeeded None otherwise
        """
        if self._last_req is not None:
            sleep_duration = randint(*self.wait_between_requests) / 1000
            sleep_duration = self._last_req - time.time() + sleep_duration

            if sleep_duration > 0:
                time.sleep(sleep_duration)

        try:
            response = requests.get(url,
                                    params=params,
                                    headers=headers,
                                    timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            logging.exception(e)
            return

        logging.debug('content: %s' % response.text)

        if self.wait_between_requests is not None:
            self._last_req = time.time()

        if response.status_code == 200:
            return json.loads(response.text)
