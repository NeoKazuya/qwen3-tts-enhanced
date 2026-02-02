# Changelog

## [Unreleased]

## 1.3.5 - 2026-02-02

- Fixed microphone recording and playback by removing dependency on system ffmpeg (uses torchaudio's bundled codec support instead)
- Fixed crash when generating speech from mic recording without a transcript
- Fixed generated audio playback failing when auto-save is off (temp directory was not in Gradio's allowed paths)
- Fixed generated audio temp files never being cleaned up (now properly managed by Gradio's cache cleanup)

## 1.3.4 - 2026-02-02

- Fixed microphone/live recording broken on Gradio 6.x (browser records WebM but backend expected WAV; all audio inputs now auto-convert)
- Fixed clone_generate crash when selected voice file doesn't exist
- Added path traversal protection to voice name inputs
- Fixed design_generate crash when variation slider is set below 1
- Improved audio normalization with minimum peak threshold (avoids amplifying near-silence)
- Improved combine_audio_files performance
- Added .dockerignore for faster Docker builds, cleaned up .gitignore
- Improved internal test coverage and Docker test infrastructure

## 1.3.3 - 2026-01-31

- Fixed preset speaker names to match Qwen3-TTS CustomVoice model (#7 by @CoLorenzo)
- Fixed Windows `ConnectionResetError: [WinError 10054]` by switching to `WindowsSelectorEventLoopPolicy`

## 1.3.2 - 2026-01-28

- PyTorch and matplotlib caches now stay in `cache/` folder instead of user home directory (#5)
- Consolidated cache setup into a shared helper for cache configuration
- Fixed bare except clause in config loading that could swallow KeyboardInterrupt
- Improved load_config() error handling for clearer, safe failure paths
- Voice files now consistently use .pt format (design_and_save was using .pkl)
- Strengthened tests to validate real runtime behavior
- Fixed Gradio 6.0 theme deprecation warning

## 1.3.1 - 2026-01-26

- Bumped CUDA from 12.6 to 12.8 (adds Blackwell/RTX 50 series support) (#3)
- Log Flash Attention availability at startup (#4)
- Added GTX 10 series compatibility note to README

## 1.3.0 - 2026-01-26

- SDPA attention for faster inference and lower VRAM (built-in Flash Attention 2)
- Bumped CUDA from 12.4 to 12.6, supporting PyTorch 2.7+

## 1.2.3 - 2026-01-25

- Fixed portable Python hash verification parsing (#3)

## 1.2.2 - 2026-01-25

- Fixed Gradio 6.0 file access error for saved voices
- Fixed Gradio 6.0 theme deprecation warning
- Suppressed pip PATH warnings during install

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
