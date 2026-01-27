"""Main orchestrator for the weekly playlist generator."""

import logging
import sys
from pathlib import Path

from .config import TARGET_PLAYLIST_SIZE
from .filters import Deduplicator, GenreFilter
from .matching import SpotifyMatcher
from .output import OutputGenerator
from .scrapers import (
    BandcampDailyScraper,
    BrooklynVeganScraper,
    PitchforkAlbumsScraper,
    PitchforkSundayScraper,
    PitchforkTracksScraper,
)
from .state import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Main orchestration function."""
    logger.info("=" * 60)
    logger.info("Starting Weekly Playlist Generator")
    logger.info("=" * 60)

    # Initialize paths
    base_path = Path(__file__).parent.parent
    data_path = base_path / "data"

    # Initialize components
    state_manager = StateManager(data_path / "state.json")
    genre_filter = GenreFilter()
    spotify_matcher = SpotifyMatcher()
    deduplicator = Deduplicator()
    output_generator = OutputGenerator(data_path / "output")

    # Initialize scrapers
    scrapers = [
        BandcampDailyScraper(),
        PitchforkAlbumsScraper(),
        PitchforkTracksScraper(),
        PitchforkSundayScraper(),
        BrooklynVeganScraper(),
    ]

    # ========================================
    # Phase 1: Scrape all sources
    # ========================================
    logger.info("")
    logger.info("Phase 1: Scraping sources...")
    logger.info("-" * 40)

    all_releases = []
    scraper_results = {}

    for scraper in scrapers:
        try:
            logger.info(f"Scraping {scraper.SOURCE_NAME}...")
            releases = scraper.scrape()
            scraper_results[scraper.SOURCE_NAME] = len(releases)
            logger.info(f"  Found {len(releases)} releases")
            all_releases.extend(releases)
        except Exception as e:
            logger.error(f"Failed to scrape {scraper.SOURCE_NAME}: {e}")
            scraper_results[scraper.SOURCE_NAME] = 0

    logger.info(f"Total releases scraped: {len(all_releases)}")

    # Check for scraper failures
    failed_scrapers = [name for name, count in scraper_results.items() if count == 0]
    if failed_scrapers:
        logger.warning(f"WARNING: These scrapers returned no results: {failed_scrapers}")
        logger.warning("Site structures may have changed - manual review needed")

    if not all_releases:
        logger.error("No releases found from any source. Exiting.")
        return None

    # ========================================
    # Phase 2: Filter by genre
    # ========================================
    logger.info("")
    logger.info("Phase 2: Filtering by genre preferences...")
    logger.info("-" * 40)

    filtered_releases = genre_filter.filter(all_releases)
    logger.info(f"After genre filter: {len(filtered_releases)} releases")

    if not filtered_releases:
        logger.warning("No releases passed genre filter. Using all releases.")
        filtered_releases = all_releases

    # ========================================
    # Phase 3: Match to Spotify
    # ========================================
    logger.info("")
    logger.info("Phase 3: Matching to Spotify...")
    logger.info("-" * 40)

    all_items = []
    matched_count = 0
    failed_count = 0

    for release in filtered_releases:
        items = spotify_matcher.match_release(release)
        if items:
            # Check if we got real matches or search placeholders
            real_matches = [i for i in items if i.spotify_uri.startswith("spotify:track:")]
            if real_matches:
                matched_count += 1
            else:
                failed_count += 1
            all_items.extend(items)
        else:
            failed_count += 1

    logger.info(f"Matched {matched_count} releases to Spotify")
    logger.info(f"Failed to match {failed_count} releases (will need manual search)")
    logger.info(f"Total playlist items: {len(all_items)}")

    if not all_items:
        logger.error("No items matched to Spotify. Exiting.")
        return None

    # ========================================
    # Phase 4: Deduplicate and prioritize
    # ========================================
    logger.info("")
    logger.info("Phase 4: Deduplicating and prioritizing...")
    logger.info("-" * 40)

    priority_items, unique_items = deduplicator.deduplicate(all_items)
    logger.info(f"Priority tracks (multi-source): {len(priority_items)}")
    logger.info(f"Unique tracks: {len(unique_items)}")

    # Group tracks by album
    grouped_items = deduplicator.group_by_album(unique_items)

    # ========================================
    # Phase 5: Apply retention policy
    # ========================================
    logger.info("")
    logger.info("Phase 5: Applying retention policy...")
    logger.info("-" * 40)

    current_items = state_manager.apply_retention(grouped_items)

    # ========================================
    # Phase 6: Trim to target size
    # ========================================
    logger.info("")
    logger.info("Phase 6: Finalizing playlist...")
    logger.info("-" * 40)

    if len(current_items) > TARGET_PLAYLIST_SIZE:
        # Keep priority items, fill rest up to target
        priority_uris = {item.spotify_uri for item in priority_items}
        priority_in_current = [i for i in current_items if i.spotify_uri in priority_uris]
        others = [i for i in current_items if i.spotify_uri not in priority_uris]

        slots_for_others = TARGET_PLAYLIST_SIZE - len(priority_in_current)
        if slots_for_others > 0:
            current_items = priority_in_current + others[:slots_for_others]
        else:
            current_items = priority_in_current[:TARGET_PLAYLIST_SIZE]

        logger.info(f"Trimmed to target size: {len(current_items)} tracks")
    else:
        logger.info(f"Final playlist size: {len(current_items)} tracks")

    # Re-group after trimming to maintain album grouping
    final_items = deduplicator.group_by_album(current_items)

    # Filter priority items to only those in final playlist
    final_uris = {item.spotify_uri for item in final_items}
    final_priority = [p for p in priority_items if p.spotify_uri in final_uris]

    # ========================================
    # Phase 7: Generate output
    # ========================================
    logger.info("")
    logger.info("Phase 7: Generating output...")
    logger.info("-" * 40)

    output_file = output_generator.generate(final_items, final_priority)

    # Save state
    state_manager.save_state()

    # ========================================
    # Summary
    # ========================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Output file: {output_file}")
    logger.info(f"Total tracks: {len(final_items)}")
    logger.info(f"Priority tracks: {len(final_priority)}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Open the output file")
    logger.info("2. Copy the Spotify URIs")
    logger.info("3. Paste into your Spotify playlist")
    logger.info("=" * 60)

    return output_file


if __name__ == "__main__":
    main()
