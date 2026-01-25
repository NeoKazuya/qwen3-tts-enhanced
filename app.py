"""
Qwen3-TTS Enhanced
An enhanced GUI for Qwen3-TTS voice cloning.

Licensed under Apache License 2.0
Based on Qwen3-TTS by Alibaba Cloud (https://github.com/QwenLM/Qwen3-TTS)
"""

# Fix matplotlib/gradio compatibility issue
import matplotlib
matplotlib.use('Agg')

import gradio as gr
import torch
import soundfile as sf
import numpy as np
import pickle
import shutil
import os
import tempfile
from pathlib import Path
from datetime import datetime

# Models (lazy loaded)
clone_model = None
custom_model = None
design_model = None

# App name for data directories
APP_NAME = "Qwen3-TTS-Enhanced"

def get_default_data_dir():
    """Get the default platform-specific data directory."""
    try:
        from platformdirs import user_data_dir
        return Path(user_data_dir(APP_NAME, appauthor=False))
    except ImportError:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            return Path(base) / APP_NAME
        else:
            return Path.home() / ".local" / "share" / APP_NAME.lower()

def get_config_path():
    """Config file stored in default location (not custom location)."""
    return get_default_data_dir() / "config.json"

def load_config():
    """Load config from JSON file."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            import json
            with open(config_path) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    """Save config to JSON file."""
    import json
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def get_data_dir():
    """Get the user data directory for persistent storage.
    
    Priority:
    1. QWEN_TTS_DATA_DIR environment variable
    2. Custom path from config.json
    3. Platform-specific default
    """
    # Check env var first
    env_dir = os.environ.get("QWEN_TTS_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    
    # Check config file
    config = load_config()
    if config.get("data_dir"):
        return Path(config["data_dir"])
    
    # Fall back to default
    return get_default_data_dir()

# Data directories (persistent, outside app folder)
DATA_DIR = get_data_dir()
VOICES_DIR = DATA_DIR / "saved_voices"
OUTPUTS_DIR = DATA_DIR / "outputs"

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICES_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Log data location on startup
print(f"Data directory: {DATA_DIR}")

# Preset speakers for CustomVoice model
SPEAKERS = [
    "Chelsie", "Ethan", "Vivian", "Ryan", "Ayla", "Jordan",
    "Sakura", "Hiroshi", "Yuna", "Takeshi"
]

LANGUAGES = [
    "Auto", "English", "Chinese", "Japanese", "Korean", 
    "German", "French", "Russian", "Portuguese", "Spanish", "Italian"
]


def get_clone_model():
    global clone_model
    if clone_model is None:
        from qwen_tts import Qwen3TTSModel
        print("Loading Voice Clone model (1.7B-Base)...")
        clone_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="eager",  # Disable FlashAttention for Windows
        )
        print("✓ Voice Clone model loaded!")
    return clone_model


def get_custom_model():
    global custom_model
    if custom_model is None:
        from qwen_tts import Qwen3TTSModel
        print("Loading Custom Voice model (1.7B-CustomVoice)...")
        custom_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="eager",  # Disable FlashAttention for Windows
        )
        print("✓ Custom Voice model loaded!")
    return custom_model


def get_design_model():
    global design_model
    if design_model is None:
        from qwen_tts import Qwen3TTSModel
        print("Loading Voice Design model (1.7B-VoiceDesign)...")
        design_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="eager",  # Disable FlashAttention for Windows
        )
        print("✓ Voice Design model loaded!")
    return design_model


def sanitize_filename(text, max_len=30):
    """Create a safe filename from text content."""
    import re
    # Remove special characters, keep alphanumeric and spaces
    clean = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with underscores
    clean = re.sub(r'\s+', '_', clean)
    # Truncate and strip
    return clean[:max_len].strip('_')


def save_audio(wav, sr, prefix="output", text="", auto_save=True):
    """Save generated audio. If auto_save=False, saves to temp directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    text_part = f"_{sanitize_filename(text)}" if text else ""
    filename = f"{prefix}{text_part}_{timestamp}.wav"
    
    if auto_save:
        path = OUTPUTS_DIR / filename
    else:
        # Use system temp dir - Gradio's delete_cache handles cleanup
        path = Path(tempfile.gettempdir()) / filename
    
    sf.write(str(path), wav, sr)
    return str(path)


def save_multiple_audio(wavs, sr, prefix="output", text="", auto_save=True):
    """Save multiple audio variations. If auto_save=False, saves to temp directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    text_part = f"_{sanitize_filename(text)}" if text else ""
    paths = []
    
    if auto_save:
        save_dir = OUTPUTS_DIR
    else:
        # Use system temp dir - Gradio's delete_cache handles cleanup
        save_dir = Path(tempfile.gettempdir())
    
    for i, wav in enumerate(wavs):
        path = save_dir / f"{prefix}{text_part}_{timestamp}_v{i+1}.wav"
        sf.write(str(path), wav, sr)
        paths.append(str(path))
    return paths


def normalize_audio(audio, target_peak=0.9):
    """Normalize audio to target peak level (0-1). Default -1dB."""
    peak = np.abs(audio).max()
    if peak > 0:
        return audio * (target_peak / peak)
    return audio


def clean_audio(audio, sr):
    """Apply light noise reduction to audio."""
    try:
        import noisereduce as nr
        # Conservative settings - only reduce noise by 50%, target stationary noise
        cleaned = nr.reduce_noise(
            y=audio, 
            sr=sr,
            prop_decrease=0.5,  # Only reduce noise halfway (gentle)
            stationary=True,     # Only target consistent background noise
        )
        return cleaned
    except ImportError:
        print("Warning: noisereduce not installed, skipping noise reduction")
        return audio
    except Exception as e:
        print(f"Warning: noise reduction failed: {e}")
        return audio


def combine_audio_files(audio_paths, apply_noise_reduction=True):
    """Combine multiple audio files into one longer reference with normalization."""
    if not audio_paths:
        return None, None
    
    # Filter out None values
    valid_paths = [p for p in audio_paths if p is not None]
    if not valid_paths:
        return None, None
    
    combined_audio = []
    target_sr = None
    
    for path in valid_paths:
        try:
            audio, sr = sf.read(path)
            
            # Convert stereo to mono if needed
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            if target_sr is None:
                target_sr = sr
            elif sr != target_sr:
                # Resample if needed
                try:
                    import librosa
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
                except ImportError:
                    print("Warning: librosa not installed, skipping resample")
            
            # Apply noise reduction (light, conservative)
            if apply_noise_reduction:
                audio = clean_audio(audio, target_sr)
            
            # Normalize each clip to consistent level (-1dB peak)
            audio = normalize_audio(audio, target_peak=0.9)
            
            # Add small silence between clips (0.3 seconds)
            silence = np.zeros(int(target_sr * 0.3))
            combined_audio.extend(audio.tolist())
            combined_audio.extend(silence.tolist())
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
            continue
    
    if not combined_audio:
        return None, None
    
    return np.array(combined_audio), target_sr


def get_saved_voices():
    """Get list of saved voice names with metadata."""
    voices = []
    seen = set()
    # Look for both .pt (new) and .pkl (legacy) files
    for ext in ["*.pt", "*.pkl"]:
        for f in VOICES_DIR.glob(ext):
            name = f.stem
            if name in seen:
                continue
            seen.add(name)
            # Check if reference audio exists
            has_audio = (VOICES_DIR / f"{name}.wav").exists()
            label = f"{name} {'🎵' if has_audio else ''}"
            voices.append((label, name))
    return [("(None - use new audio)", "")] + sorted(voices, key=lambda x: x[0])


def get_voice_choices():
    """Get dropdown choices."""
    return [v[0] for v in get_saved_voices()]


def get_voice_value(label):
    """Convert label back to voice name."""
    for display, name in get_saved_voices():
        if display == label:
            return name
    return ""


# ==================== VOICE CLONE ====================
def clone_generate(text, language, saved_voice_label, ref_audio, ref_text, num_variations, auto_save):
    """Generate speech using saved voice or new reference."""
    if not text.strip():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "❌ Enter text to generate"
    
    saved_voice = get_voice_value(saved_voice_label)
    m = get_clone_model()
    num_variations = int(num_variations)
    
    try:
        all_wavs = []
        for i in range(num_variations):
            if saved_voice:
                # Load voice prompt (.pt preferred, fallback to .pkl)
                pt_path = VOICES_DIR / f"{saved_voice}.pt"
                pkl_path = VOICES_DIR / f"{saved_voice}.pkl"
                if pt_path.exists():
                    prompt = torch.load(pt_path, weights_only=False)
                elif pkl_path.exists():
                    with open(pkl_path, "rb") as f:
                        prompt = pickle.load(f)
                else:
                    return None, "", f"❌ Voice file not found: {saved_voice}"
                wavs, sr = m.generate_voice_clone(
                    text=text, language=language, voice_clone_prompt=prompt
                )
            else:
                if ref_audio is None:
                    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "❌ Upload reference audio or select a saved voice"
                wavs, sr = m.generate_voice_clone(
                    text=text, language=language,
                    ref_audio=ref_audio,
                    ref_text=ref_text if ref_text.strip() else None,
                )
            all_wavs.append(wavs[0])
        
        # Save all variations
        voice_name = saved_voice if saved_voice else "clone"
        paths = save_multiple_audio(all_wavs, sr, voice_name, text, auto_save=auto_save)
        
        # Return audio with visibility - only show players that have content
        results = []
        for i in range(5):
            if i < len(paths):
                results.append(gr.update(value=paths[i], visible=True))
            else:
                results.append(gr.update(value=None, visible=False))
        
        return *results, f"✅ Generated {num_variations} variation(s)!"
    except Exception as e:
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), f"❌ {e}"


def clone_save(name, ref_audio, ref_text):
    """Save a voice clone with its reference audio."""
    if not name.strip():
        return "❌ Enter a name for the voice", gr.update()
    if ref_audio is None:
        return "❌ Upload reference audio first", gr.update()
    
    m = get_clone_model()
    name = name.strip().replace(" ", "_")
    
    try:
        prompt = m.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text if ref_text.strip() else None,
            x_vector_only_mode=not bool(ref_text.strip()),
        )
        
        # Save as .pt file (PyTorch format, compatible with original)
        torch.save(prompt, VOICES_DIR / f"{name}.pt")
        
        shutil.copy(ref_audio, VOICES_DIR / f"{name}.wav")
        
        if ref_text.strip():
            with open(VOICES_DIR / f"{name}.txt", "w", encoding="utf-8") as f:
                f.write(ref_text)
        
        return f"✅ Voice '{name}' saved!", gr.update(choices=get_voice_choices())
    except Exception as e:
        return f"❌ {e}", gr.update()


def clone_delete(voice_label):
    """Delete a saved voice and its files."""
    name = get_voice_value(voice_label)
    if not name:
        return "❌ Select a voice to delete", gr.update()
    
    for ext in [".pt", ".pkl", ".wav", ".txt"]:  # Support both .pt and legacy .pkl
        path = VOICES_DIR / f"{name}{ext}"
        if path.exists():
            path.unlink()
    
    return f"✅ Deleted '{name}'", gr.update(choices=get_voice_choices(), value="(None - use new audio)")


def load_voice_info(voice_label):
    """Load saved reference audio and transcript when selecting a voice."""
    name = get_voice_value(voice_label)
    if not name:
        return None, ""
    
    audio_path = VOICES_DIR / f"{name}.wav"
    text_path = VOICES_DIR / f"{name}.txt"
    
    audio = str(audio_path) if audio_path.exists() else None
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    
    return audio, text


# ==================== CREATE VOICE FROM MULTIPLE REFERENCES ====================
def create_voice_multi_ref(name, audio1, text1, audio2, text2, audio3, text3, audio4, text4, audio5, text5, denoise):
    """Create a voice from multiple reference audio files with individual transcripts."""
    if not name.strip():
        return None, "❌ Enter a name for the voice", gr.update()
    
    # Collect all provided audio files and their transcripts
    items = [
        (audio1, text1), (audio2, text2), (audio3, text3), 
        (audio4, text4), (audio5, text5)
    ]
    audio_files = []
    transcripts = []
    for audio, text in items:
        if audio is not None:
            audio_files.append(audio)
            transcripts.append(text.strip() if text else "")
    
    if len(audio_files) == 0:
        return None, "❌ Upload at least one reference audio file", gr.update()
    
    # Combine transcripts with space separator
    combined_transcript = " ".join([t for t in transcripts if t]).strip()
    
    m = get_clone_model()
    name = name.strip().replace(" ", "_")
    
    try:
        if len(audio_files) == 1:
            # Single file - process it
            audio_data, sr = sf.read(audio_files[0])
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            if denoise:
                audio_data = clean_audio(audio_data, sr)
            audio_data = normalize_audio(audio_data, target_peak=0.9)
            combined_audio = audio_data
            combined_sr = sr
        else:
            # Multiple files - combine them
            combined_audio, combined_sr = combine_audio_files(audio_files, apply_noise_reduction=denoise)
            if combined_audio is None:
                return None, "❌ Could not combine audio files", gr.update()
        
        # Create voice clone prompt
        prompt = m.create_voice_clone_prompt(
            ref_audio=(combined_audio, combined_sr),
            ref_text=combined_transcript if combined_transcript else None,
            x_vector_only_mode=not bool(combined_transcript),
        )
        
        # Save the prompt as .pt file (PyTorch format)
        torch.save(prompt, VOICES_DIR / f"{name}.pt")
        
        # Save combined audio for reference
        sf.write(str(VOICES_DIR / f"{name}.wav"), combined_audio, combined_sr)
        
        # Save transcript if provided
        if combined_transcript:
            with open(VOICES_DIR / f"{name}.txt", "w", encoding="utf-8") as f:
                f.write(combined_transcript)
        
        num_files = len(audio_files)
        return (
            str(VOICES_DIR / f"{name}.wav"),
            f"✅ Voice '{name}' created from {num_files} reference(s)!",
            gr.update(choices=get_voice_choices())
        )
    except Exception as e:
        return None, f"❌ {e}", gr.update()


# ==================== CUSTOM VOICE ====================
def custom_generate(text, language, speaker, instruct, num_variations, auto_save):
    """Generate speech with preset speaker."""
    if not text.strip():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "❌ Enter text to generate"
    
    m = get_custom_model()
    num_variations = int(num_variations)
    
    try:
        all_wavs = []
        for i in range(num_variations):
            wavs, sr = m.generate_custom_voice(
                text=text, language=language, speaker=speaker,
                instruct=instruct if instruct.strip() else None,
            )
            all_wavs.append(wavs[0])
        
        paths = save_multiple_audio(all_wavs, sr, f"{speaker}", text, auto_save=auto_save)
        results = []
        for i in range(5):
            if i < len(paths):
                results.append(gr.update(value=paths[i], visible=True))
            else:
                results.append(gr.update(value=None, visible=False))
        return *results, f"✅ Generated {num_variations} variation(s)!"
    except Exception as e:
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), f"❌ {e}"


# ==================== VOICE DESIGN ====================
def design_generate(text, language, instruct, num_variations, auto_save):
    """Generate speech with designed voice."""
    if not text.strip():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "❌ Enter text to generate"
    if not instruct.strip():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), "❌ Enter a voice description"
    
    m = get_design_model()
    num_variations = int(num_variations)
    
    try:
        all_wavs = []
        for i in range(num_variations):
            wavs, sr = m.generate_voice_design(
                text=text, language=language, instruct=instruct,
            )
            all_wavs.append(wavs[0])
        
        paths = save_multiple_audio(all_wavs, sr, "design", text, auto_save=auto_save)
        results = []
        for i in range(5):
            if i < len(paths):
                results.append(gr.update(value=paths[i], visible=True))
            else:
                results.append(gr.update(value=None, visible=False))
        return *results, f"✅ Generated {num_variations} variation(s)!"
    except Exception as e:
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), f"❌ {e}"


def design_and_save(name, sample_text, language, instruct):
    """Design a voice and save it for reuse in Voice Clone."""
    if not name.strip():
        return None, "❌ Enter a name", gr.update()
    if not sample_text.strip():
        return None, "❌ Enter sample text", gr.update()
    if not instruct.strip():
        return None, "❌ Enter voice description", gr.update()
    
    design_m = get_design_model()
    clone_m = get_clone_model()
    name = name.strip().replace(" ", "_")
    
    try:
        wavs, sr = design_m.generate_voice_design(
            text=sample_text, language=language, instruct=instruct,
        )
        
        audio_path = VOICES_DIR / f"{name}.wav"
        sf.write(str(audio_path), wavs[0], sr)
        
        prompt = clone_m.create_voice_clone_prompt(
            ref_audio=(wavs[0], sr),
            ref_text=sample_text,
        )
        with open(VOICES_DIR / f"{name}.pkl", "wb") as f:
            pickle.dump(prompt, f)
        
        with open(VOICES_DIR / f"{name}.txt", "w", encoding="utf-8") as f:
            f.write(sample_text)
        with open(VOICES_DIR / f"{name}_design.txt", "w", encoding="utf-8") as f:
            f.write(instruct)
        
        return str(audio_path), f"✅ Voice '{name}' designed and saved!", gr.update(choices=get_voice_choices())
    except Exception as e:
        return None, f"❌ {e}", gr.update()


# ==================== BUILD UI ====================
# delete_cache: (frequency_seconds, age_seconds) - cleans cache hourly for files older than 1 hour
with gr.Blocks(title="Qwen3-TTS Enhanced", theme=gr.themes.Soft(), analytics_enabled=False, delete_cache=(3600, 3600)) as app:
    gr.Markdown("# 🎙️ Qwen3-TTS Enhanced")
    gr.Markdown("**Clone voices, create new ones, generate speech - 100% local.**")
    
    with gr.Tabs():
        # ===== VOICE CLONE TAB =====
        with gr.TabItem("🎤 Voice Clone"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Select or Upload Voice")
                    vc_saved = gr.Dropdown(
                        label="Saved Voices", 
                        choices=get_voice_choices(), 
                        value="(None - use new audio)",
                        interactive=True,
                    )
                    vc_ref_audio = gr.Audio(label="Reference Audio (3+ sec)", type="filepath")
                    vc_ref_text = gr.Textbox(label="Transcript (optional, improves quality)", lines=2)
                    
                    gr.Markdown("### 💾 Save This Voice")
                    with gr.Row():
                        vc_save_name = gr.Textbox(label="Name", scale=2, placeholder="MyVoice")
                        vc_save_btn = gr.Button("💾 Save", scale=1, variant="secondary")
                    vc_save_status = gr.Textbox(label="", interactive=False, show_label=False)
                    vc_del_btn = gr.Button("🗑️ Delete Selected Voice", variant="stop", size="sm")
                    
                with gr.Column():
                    gr.Markdown("### Generate Speech")
                    vc_text = gr.Textbox(label="Text to Speak", lines=4, placeholder="Enter what you want the voice to say...")
                    with gr.Row():
                        vc_lang = gr.Dropdown(label="Language", choices=LANGUAGES, value="English", scale=2)
                        vc_variations = gr.Slider(label="Variations", minimum=1, maximum=5, value=1, step=1, scale=1)
                    vc_auto_save = gr.Checkbox(label="💾 Auto-save", value=False, info=f"Saves to: {OUTPUTS_DIR}")
                    vc_gen_btn = gr.Button("🎤 Generate Speech", variant="primary", size="lg")
                    vc_status = gr.Textbox(label="Status", interactive=False)
                    
                    gr.Markdown("### Generated Audio")
                    vc_audio1 = gr.Audio(label="V1", type="filepath")
                    with gr.Row():
                        vc_audio2 = gr.Audio(label="V2", type="filepath", visible=False)
                        vc_audio3 = gr.Audio(label="V3", type="filepath", visible=False)
                    with gr.Row():
                        vc_audio4 = gr.Audio(label="V4", type="filepath", visible=False)
                        vc_audio5 = gr.Audio(label="V5", type="filepath", visible=False)
            
            # Wire up events
            vc_gen_btn.click(
                clone_generate, 
                [vc_text, vc_lang, vc_saved, vc_ref_audio, vc_ref_text, vc_variations, vc_auto_save], 
                [vc_audio1, vc_audio2, vc_audio3, vc_audio4, vc_audio5, vc_status]
            )
            vc_save_btn.click(clone_save, [vc_save_name, vc_ref_audio, vc_ref_text], [vc_save_status, vc_saved])
            vc_del_btn.click(clone_delete, [vc_saved], [vc_save_status, vc_saved])
            vc_saved.change(load_voice_info, [vc_saved], [vc_ref_audio, vc_ref_text])

        # ===== CUSTOM VOICE TAB =====
        with gr.TabItem("👤 Custom Voice"):
            gr.Markdown("Use preset speakers with optional style instructions.")
            with gr.Row():
                with gr.Column():
                    cv_speaker = gr.Dropdown(label="Speaker", choices=SPEAKERS, value="Vivian")
                    cv_instruct = gr.Textbox(
                        label="Style Instruction (optional)", 
                        placeholder="e.g., Speak angrily, whisper softly, sound excited...", 
                        lines=2
                    )
                with gr.Column():
                    cv_text = gr.Textbox(label="Text to Speak", lines=4)
                    with gr.Row():
                        cv_lang = gr.Dropdown(label="Language", choices=LANGUAGES, value="English", scale=2)
                        cv_variations = gr.Slider(label="Variations", minimum=1, maximum=5, value=1, step=1, scale=1)
                    cv_auto_save = gr.Checkbox(label="💾 Auto-save", value=False, info=f"Saves to: {OUTPUTS_DIR}")
                    cv_btn = gr.Button("🎤 Generate Speech", variant="primary", size="lg")
                    cv_status = gr.Textbox(label="Status", interactive=False)
            
            gr.Markdown("### Generated Audio")
            cv_audio1 = gr.Audio(label="V1", type="filepath")
            with gr.Row():
                cv_audio2 = gr.Audio(label="V2", type="filepath", visible=False)
                cv_audio3 = gr.Audio(label="V3", type="filepath", visible=False)
            with gr.Row():
                cv_audio4 = gr.Audio(label="V4", type="filepath", visible=False)
                cv_audio5 = gr.Audio(label="V5", type="filepath", visible=False)
            
            cv_btn.click(
                custom_generate, 
                [cv_text, cv_lang, cv_speaker, cv_instruct, cv_variations, cv_auto_save], 
                [cv_audio1, cv_audio2, cv_audio3, cv_audio4, cv_audio5, cv_status]
            )

        # ===== VOICE DESIGN TAB =====
        with gr.TabItem("✨ Voice Design"):
            gr.Markdown("Create a brand new voice from a text description.")
            with gr.Row():
                with gr.Column():
                    vd_instruct = gr.Textbox(
                        label="Voice Description", 
                        lines=3,
                        placeholder="e.g., Young female voice, cheerful and energetic, slight British accent..."
                    )
                with gr.Column():
                    vd_text = gr.Textbox(label="Text to Speak", lines=4)
                    with gr.Row():
                        vd_lang = gr.Dropdown(label="Language", choices=LANGUAGES, value="English", scale=2)
                        vd_variations = gr.Slider(label="Variations", minimum=1, maximum=5, value=1, step=1, scale=1)
                    vd_auto_save = gr.Checkbox(label="💾 Auto-save", value=False, info=f"Saves to: {OUTPUTS_DIR}")
                    vd_btn = gr.Button("✨ Generate Speech", variant="primary", size="lg")
                    vd_status = gr.Textbox(label="Status", interactive=False)
            
            gr.Markdown("### Generated Audio")
            vd_audio1 = gr.Audio(label="V1", type="filepath")
            with gr.Row():
                vd_audio2 = gr.Audio(label="V2", type="filepath", visible=False)
                vd_audio3 = gr.Audio(label="V3", type="filepath", visible=False)
            with gr.Row():
                vd_audio4 = gr.Audio(label="V4", type="filepath", visible=False)
                vd_audio5 = gr.Audio(label="V5", type="filepath", visible=False)
            
            vd_btn.click(
                design_generate, 
                [vd_text, vd_lang, vd_instruct, vd_variations, vd_auto_save], 
                [vd_audio1, vd_audio2, vd_audio3, vd_audio4, vd_audio5, vd_status]
            )
            
            gr.Markdown("---")
            gr.Markdown("### 💾 Design & Save as Reusable Voice")
            with gr.Row():
                vd_save_name = gr.Textbox(label="Voice Name", placeholder="MyDesignedVoice")
                vd_save_sample = gr.Textbox(
                    label="Sample Text", 
                    placeholder="This text will be spoken to create the voice sample...",
                    scale=2
                )
            vd_save_btn = gr.Button("✨ Design & Save Voice", variant="primary")
            vd_save_audio = gr.Audio(label="Voice Sample", type="filepath")
            vd_save_status = gr.Textbox(label="Status", interactive=False)
            
            vd_save_btn.click(
                design_and_save, 
                [vd_save_name, vd_save_sample, vd_lang, vd_instruct],
                [vd_save_audio, vd_save_status, vc_saved]
            )

        # ===== CREATE VOICE TAB (Multi-Reference) =====
        with gr.TabItem("🎭 Create Voice"):
            gr.Markdown("### Create Voice from Multiple References")
            gr.Markdown("Upload up to 5 audio samples with their transcripts. More samples = better quality!")
            
            cv_name = gr.Textbox(label="Voice Name", placeholder="MyVoice")
            
            gr.Markdown("**Reference Audio Files** (add transcript below each audio)")
            
            with gr.Row():
                with gr.Column():
                    cv_audio1 = gr.Audio(label="Audio 1 (required)", type="filepath")
                    cv_text1 = gr.Textbox(label="Transcript 1", placeholder="What is said in audio 1...", lines=2)
                with gr.Column():
                    cv_audio2 = gr.Audio(label="Audio 2 (optional)", type="filepath")
                    cv_text2 = gr.Textbox(label="Transcript 2", placeholder="What is said in audio 2...", lines=2)
            
            with gr.Row():
                with gr.Column():
                    cv_audio3 = gr.Audio(label="Audio 3 (optional)", type="filepath")
                    cv_text3 = gr.Textbox(label="Transcript 3", placeholder="What is said in audio 3...", lines=2)
                with gr.Column():
                    cv_audio4 = gr.Audio(label="Audio 4 (optional)", type="filepath")
                    cv_text4 = gr.Textbox(label="Transcript 4", placeholder="What is said in audio 4...", lines=2)
            
            with gr.Row():
                with gr.Column():
                    cv_audio5 = gr.Audio(label="Audio 5 (optional)", type="filepath")
                    cv_text5 = gr.Textbox(label="Transcript 5", placeholder="What is said in audio 5...", lines=2)
                with gr.Column():
                    cv_denoise = gr.Checkbox(
                        label="🔇 Clean audio (very gentle noise reduction)", 
                        value=True,
                        info="Subtle background noise removal - won't change voice quality"
                    )
                    cv_btn = gr.Button("🎭 Create Voice", variant="primary", size="lg")
            
            cv_status = gr.Textbox(label="Status", interactive=False)
            cv_preview = gr.Audio(label="Combined Reference (Preview)", type="filepath")
            
            cv_btn.click(
                create_voice_multi_ref,
                [cv_name, cv_audio1, cv_text1, cv_audio2, cv_text2, cv_audio3, cv_text3, cv_audio4, cv_text4, cv_audio5, cv_text5, cv_denoise],
                [cv_preview, cv_status, vc_saved]
            )

        # ===== SAVED VOICES TAB =====
        with gr.TabItem("📁 Saved Voices"):
            gr.Markdown("### Your Saved Voices")
            
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown(f"**Location**: `{VOICES_DIR}`")
                with gr.Column(scale=1):
                    def open_voices_folder():
                        import subprocess
                        import sys
                        if sys.platform == "win32":
                            subprocess.run(["explorer", str(VOICES_DIR)])
                        elif sys.platform == "darwin":
                            subprocess.run(["open", str(VOICES_DIR)])
                        else:
                            subprocess.run(["xdg-open", str(VOICES_DIR)])
                    voices_folder_btn = gr.Button("📂 Open Folder", size="sm")
                    voices_folder_btn.click(open_voices_folder)
            
            def list_voices():
                voices = []
                seen = set()
                for ext in ["*.pt", "*.pkl"]:
                    for f in VOICES_DIR.glob(ext):
                        name = f.stem
                        if name in seen:
                            continue
                        seen.add(name)
                        has_audio = "✅" if (VOICES_DIR / f"{name}.wav").exists() else "❌"
                        has_text = "✅" if (VOICES_DIR / f"{name}.txt").exists() else "❌"
                        voices.append([name, has_audio, has_text])
                return sorted(voices, key=lambda x: x[0]) if voices else [["(No saved voices)", "-", "-"]]
            
            voices_table = gr.Dataframe(
                headers=["Name", "Audio", "Transcript"],
                value=list_voices(),
                interactive=False,
            )
            refresh_btn = gr.Button("🔄 Refresh List")
            refresh_btn.click(list_voices, outputs=[voices_table])
            
            gr.Markdown("""
---
**Tip**: Voices are saved when you:
- Use **Save Voice** in Voice Clone tab
- Use **Create Voice** tab to combine multiple samples
- Use **Design & Save** in Voice Design tab
            """)

        # ===== SETTINGS TAB =====
        with gr.TabItem("⚙️ Settings"):
            gr.Markdown("### Data Storage")
            gr.Markdown(f"Current location:")
            gr.Code(str(DATA_DIR), language=None, label="Data Folder")
            
            def open_data_folder():
                import subprocess
                import sys
                if sys.platform == "win32":
                    subprocess.run(["explorer", str(DATA_DIR)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(DATA_DIR)])
                else:
                    subprocess.run(["xdg-open", str(DATA_DIR)])
                return "📂 Opened"
            
            open_btn = gr.Button("📂 Open Folder", variant="secondary")
            open_status = gr.Textbox(label="", visible=False)
            open_btn.click(open_data_folder, outputs=[open_status])
            
            gr.Markdown("---")
            gr.Markdown("### Change Location")
            
            config = load_config()
            current_custom = config.get("data_dir", "")
            
            custom_path = gr.Textbox(
                label="Custom Data Folder", 
                value=current_custom,
                placeholder="Leave empty to use default location",
                info="Enter a folder path, or leave empty for default"
            )
            
            def save_custom_path(path):
                path = path.strip()
                config = load_config()
                if path:
                    # Validate path is writable
                    try:
                        test_dir = Path(path)
                        test_dir.mkdir(parents=True, exist_ok=True)
                        config["data_dir"] = str(test_dir)
                        save_config(config)
                        return "✅ Saved! Restart app to apply changes."
                    except Exception as e:
                        return f"❌ Invalid path: {e}"
                else:
                    if "data_dir" in config:
                        del config["data_dir"]
                        save_config(config)
                    return "✅ Reset to default. Restart app to apply."
            
            def reset_to_default():
                config = load_config()
                if "data_dir" in config:
                    del config["data_dir"]
                    save_config(config)
                return "", "✅ Reset to default. Restart app to apply."
            
            with gr.Row():
                save_path_btn = gr.Button("💾 Save", variant="primary")
                reset_path_btn = gr.Button("🔄 Reset to Default", variant="secondary")
            
            path_status = gr.Textbox(label="Status", interactive=False)
            
            save_path_btn.click(save_custom_path, [custom_path], [path_status])
            reset_path_btn.click(reset_to_default, outputs=[custom_path, path_status])
            
            gr.Markdown(f"""
---
### What's in the data folder?
- **saved_voices/** - Your cloned and designed voice files
- **outputs/** - Generated audio (when "Save generated audio" is enabled)
- **config.json** - Your settings

**Default location**: `{get_default_data_dir()}`
            """)


if __name__ == "__main__":
    print("=" * 50)
    print("  Qwen3-TTS Enhanced")
    print("  Browser will open automatically when ready...")
    print("=" * 50)
    app.launch(server_name="0.0.0.0", server_port=8000, inbrowser=True)
