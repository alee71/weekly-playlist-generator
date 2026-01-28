  """Match scraped releases to Spotify search links."""

  import logging
  import urllib.parse
  from typing import List

  from ..config import TRACKS_PER_ALBUM_MAX
  from ..models import PlaylistItem, ScrapedRelease

  logger = logging.getLogger(__name__)


  class SpotifyMatcher:
      """Generate Spotify search links for scraped releases."""

      def __init__(self):
          logger.info("SpotifyMatcher initialized (search link mode)")

      def match_release(self, release: ScrapedRelease) -> List[PlaylistItem]:
          """Create playlist items with Spotify search links."""
          if release.release_type == "track":
              return self._create_track_item(release)
          else:
              return self._create_album_items(release)

      def _create_track_item(self, release: ScrapedRelease) -> List[PlaylistItem]:
          """Create a single track item."""
          search_query = f"{release.artist} {release.title}"
          search_url = self._make_search_url(search_query)

          return [PlaylistItem(
              artist=release.artist,
              track=release.title,
              album="",
              spotify_uri=search_url,
              source=release.source,
              scraped_date=release.scraped_date,
          )]

      def _create_album_items(self, release: ScrapedRelease) -> List[PlaylistItem]:
          """Create album item (user will pick tracks)."""
          search_query = f"{release.artist} {release.title}"
          search_url = self._make_search_url(search_query)

          return [PlaylistItem(
              artist=release.artist,
              track=f"[Album: {release.title}]",
              album=release.title,
              spotify_uri=search_url,
              source=release.source,
              scraped_date=release.scraped_date,
          )]

      def _make_search_url(self, query: str) -> str:
          """Create a Spotify search URL."""
          encoded = urllib.parse.quote(query)
          return f"https://open.spotify.com/search/{encoded}"
