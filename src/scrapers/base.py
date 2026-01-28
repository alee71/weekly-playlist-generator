"""Base scraper class."""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import RATE_LIMITS
from ..models import ScrapedRelease


class ScraperError(Exception):
      pass


class BaseScraper(ABC):
      SOURCE_NAME: str = ""
      BASE_URL: str = ""
      RATE_LIMIT_KEY: str = "default"

      def __init__(self):
          self.session = requests.Session()
          self.session.headers.update({
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
              "Accept": "text/html,application/xhtml+xml",
              "Accept-Language": "en-US,en;q=0.9",
          })
          self.logger = logging.getLogger(self.__class__.__name__)
          self._last_request_time = 0

      @abstractmethod
      def scrape(self) -> List[ScrapedRelease]:
          pass

      def _get_rate_limit(self) -> float:
          return RATE_LIMITS.get(self.RATE_LIMIT_KEY, RATE_LIMITS["default"])

      def _rate_limit(self):
          elapsed = time.time() - self._last_request_time
          delay = self._get_rate_limit() + random.uniform(0.5, 2.0)
          if elapsed < delay:
              time.sleep(delay - elapsed)
          self._last_request_time = time.time()

      def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
          self._rate_limit()
          try:
              self.logger.debug(f"Fetching: {url}")
              response = self.session.get(url, timeout=30)
              response.raise_for_status()
              return BeautifulSoup(response.text, "lxml")
          except requests.RequestException as e:
              self.logger.error(f"Failed to fetch {url}: {e}")
              return None

      def _normalize_genres(self, genres: List[str]) -> List[str]:
          normalized = []
          for genre in genres:
              g = genre.lower().strip()
              if g and len(g) < 30:
                  normalized.append(g)
          return list(set(normalized))

      def _validate_results(self, results: List[ScrapedRelease]) -> bool:
          if not results:
              self.logger.warning(f"{self.SOURCE_NAME}: No results found")
              return False
          return True
