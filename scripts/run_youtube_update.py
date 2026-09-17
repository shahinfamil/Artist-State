"""Run YouTube updater from command line for debugging.

Usage:
    python scripts/run_youtube_update.py

This will create the Flask app context and run `update_all_tracks_for_platform(app, 'youtube')`.
Logs are written to `logs/updater.log`.
"""
from app import create_app, update_all_tracks_for_platform

if __name__ == '__main__':
    app = create_app()
    print('Starting YouTube update (this may take a while). See logs/updater.log for progress.')
    update_all_tracks_for_platform(app, 'youtube')
    print('Done.')
