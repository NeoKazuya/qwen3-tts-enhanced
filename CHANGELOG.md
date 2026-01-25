# Changelog

## 1.1.0 - 2026-01-24

- Settings tab with custom data folder (GUI-configurable, no env vars needed)
- Auto-save checkbox shows actual save location
- Saved Voices tab shows folder path with "Open Folder" button
- Settings explains what's in the data folder
- Auto-save is now opt-in (off by default)
- Data stored in user folder, persists across updates
- Automatic temp file cleanup (hourly)
- Docker uses single volume mount (`./data`)
- Fixed Docker to use Python 3.10

## 1.0.0 - 2026-01-20

Initial release with voice cloning, multi-reference support, preset speakers, and voice design.
