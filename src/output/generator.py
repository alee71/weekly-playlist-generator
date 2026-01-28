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
          lines.append(f"Weekly Playlist - {date_str}")
          lines.append(f"Total items: {len(items)}")
          lines.append("=" * 70)
          lines.append("")

          if priority_items:
              lines.append("### PRIORITY - Multiple Sources ###")
              lines.append("")
              for item in priority_items:
                  sources = ", ".join(item.sources)
                  lines.append(f"* {item.artist} - {item.track}")
                  lines.append(f"  Sources: {sources}")
                  lines.append(f"  Search: {item.spotify_uri}")
                  lines.append("")

          lines.append("### FULL PLAYLIST ###")
          lines.append("")

          for i, item in enumerate(items, 1):
              if "[Album:" in item.track:
                  lines.append(f"{i}. {item.artist} - {item.album}")
              else:
                  lines.append(f"{i}. {item.artist} - {item.track}")
              source = item.sources[0] if item.sources else item.source
              lines.append(f"   Source: {source}")
              lines.append(f"   Search: {item.spotify_uri}")
              lines.append("")

          content = "\n".join(lines)
          output_file.write_text(content, encoding="utf-8")
          logger.info(f"Output written to: {output_file}")
          return output_file
