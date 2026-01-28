  """Output generation for playlist files."""

  import logging
  from datetime import datetime
  from pathlib import Path
  from typing import List

  from ..models import PlaylistItem

  logger = logging.getLogger(__name__)


  class OutputGenerator:
      """Generate playlist output file."""

      def __init__(self, output_dir: Path):
          self.output_dir = output_dir
          self.output_dir.mkdir(parents=True, exist_ok=True)

      def generate(
          self,
          items: List[PlaylistItem],
          priority_items: List[PlaylistItem],
      ) -> Path:
          """Generate playlist output file."""
          date_str = datetime.now().strftime("%Y-%m-%d")
          output_file = self.output_dir / f"playlist_{date_str}.txt"

          lines = []

          # Header
          lines.append(f"Weekly Playlist - {date_str}")
          lines.append(f"Total items: {len(items)}")
          lines.append(f"Priority (multiple sources): {len(priority_items)}")
          lines.append("=" * 70)
          lines.append("")

          # Priority section
          if priority_items:
              lines.append("### PRIORITY - Recommended by Multiple Sources ###")
              lines.append("")
              for item in priority_items:
                  sources = ", ".join(item.sources)
                  lines.append(f"* {item.artist} - {item.track}")
                  lines.append(f"  Sources: {sources}")
                  lines.append(f"  Search: {item.spotify_uri}")
                  lines.append("")
              lines.append("=" * 70)
              lines.append("")

          # Full playlist grouped by album
          lines.append("### FULL PLAYLIST ###")
          lines.append("")
          lines.append("Click the search links to find each item on Spotify.")
          lines.append("For albums, search and pick 3-5 tracks you like.")
          lines.append("")

          current_album = None

          for i, item in enumerate(items, 1):
              album_key = (item.artist.lower(), item.album.lower()) if item.album else None

              # Album header
              if album_key and album_key != current_album:
                  if current_album is not None:
                      lines.append("")
                  lines.append(f"--- {item.artist} - {item.album} ---")
                  current_album = album_key

              # Item line
              week_info = f" (week {item.weeks_in_playlist + 1})" if item.weeks_in_playlist > 0 else ""

              if "[Album:" in item.track:
                  lines.append(f"{i}. {item.artist} - {item.album}{week_info}")
              else:
                  lines.append(f"{i}. {item.artist} - {item.track}{week_info}")

              source = item.sources[0] if item.sources else item.source
              lines.append(f"   Source: {source}")
              lines.append(f"   Search: {item.spotify_uri}")
              lines.append("")

          # Write file
          content = "\n".join(lines)
          output_file.write_text(content, encoding="utf-8")

          logger.info(f"Output written to: {output_file}")
          return output_file
