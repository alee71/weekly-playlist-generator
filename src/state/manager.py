"""State management for playlist history and retention."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

from ..config import RETENTION_WEEKS
from ..models import PlaylistItem

logger = logging.getLogger(__name__)


class StateManager:
    """Manage playlist state with 2-week retention policy."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    logger.info(
                        f"Loaded state with {len(state.get('track_history', {}))} tracks"
                    )
                    return state
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load state file: {e}")

        return {
            "track_history": {},  # uri -> first_added_date
            "last_run": None,
        }

    def save_state(self):
        """Persist state to JSON file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            logger.info(f"State saved to {self.state_file}")
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    def apply_retention(self, items: List[PlaylistItem]) -> List[PlaylistItem]:
        """
        Apply retention policy to playlist items.

        - Remove tracks older than RETENTION_WEEKS
        - Update track ages
        - Return items that should be in current playlist
        """
        cutoff_date = datetime.now() - timedelta(weeks=RETENTION_WEEKS)
        history = self.state["track_history"]

        # Clean up expired entries
        expired_uris = []
        for uri, date_str in history.items():
            try:
                added_date = datetime.fromisoformat(date_str)
                if added_date < cutoff_date:
                    expired_uris.append(uri)
            except ValueError:
                expired_uris.append(uri)

        for uri in expired_uris:
            del history[uri]
            logger.debug(f"Expired track removed: {uri}")

        if expired_uris:
            logger.info(f"Removed {len(expired_uris)} expired tracks from history")

        # Process items
        current_items = []
        now = datetime.now()
        now_str = now.isoformat()

        for item in items:
            uri = item.spotify_uri

            # Skip search URIs (these are manual search placeholders)
            if uri.startswith("spotify:search:"):
                current_items.append(item)
                continue

            # Add new tracks to history
            if uri not in history:
                history[uri] = now_str

            # Check if within retention window
            try:
                added_date = datetime.fromisoformat(history[uri])
                if added_date >= cutoff_date:
                    # Calculate weeks in playlist
                    item.weeks_in_playlist = (now - added_date).days // 7
                    current_items.append(item)
                else:
                    logger.debug(f"Skipping expired track: {item.artist} - {item.track}")
            except ValueError:
                # Invalid date, treat as new
                history[uri] = now_str
                item.weeks_in_playlist = 0
                current_items.append(item)

        self.state["last_run"] = now_str

        logger.info(
            f"Retention applied: {len(items)} items -> {len(current_items)} current"
        )

        return current_items

    def get_track_history(self) -> Set[str]:
        """Get set of URIs currently in rotation."""
        return set(self.state["track_history"].keys())

    def get_last_run(self) -> datetime | None:
        """Get the datetime of the last run."""
        last_run = self.state.get("last_run")
        if last_run:
            try:
                return datetime.fromisoformat(last_run)
            except ValueError:
                pass
        return None
