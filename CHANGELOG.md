# Changelog

## 1.2.1 - 2026-01-25

- Fixed embedded Python install (venv module not included in embeddable package)

## 1.2.0 - 2026-01-25

- Portable Python auto-installer (downloads Python 3.12.8 if needed)
- SHA256 hash verification for Python download security
- Fixed matplotlib missing error (#2)
- Fixed Python 3.14 compatibility issue (#1)
- Docker now uses Python 3.12 (matches Windows)
- Better install progress messages and error handling

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
