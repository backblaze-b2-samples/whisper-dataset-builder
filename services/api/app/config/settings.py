from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (Standard #3 env var names) ---
    # Region drives the S3 endpoint; we never store the full endpoint URL,
    # so there is no hardcoded region string anywhere in source.
    b2_region: str = "us-west-004"
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits — long-form source recordings can be large.
    max_file_size: int = 500 * 1024 * 1024  # 500MB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- Dataset builder pipeline ---
    # Uploaded long-form recordings land here; the build form and the bulk
    # CLI both list this prefix to find sources.
    source_prefix: str = "sources/"
    # Generated datasets (manifest, clip wavs, transcript metadata) live here.
    dataset_prefix: str = "datasets/"

    # Free HuggingFace token, used ONLY to download pyannote's gated
    # segmentation weights. Empty => VAD degrades to the token-free energy
    # fallback, so the app runs end-to-end with B2 credentials alone.
    hf_token: str = ""

    # Local ML engine knobs — CPU-friendly defaults so a short clip runs
    # without a GPU. The device is auto-detected (CUDA -> MPS -> CPU) at
    # runtime; this is only the floor / explicit override.
    whisper_model: str = "base"
    # "auto" lets the engine pick CUDA -> MPS -> CPU. Set "cpu"/"cuda"/"mps"
    # to force a device.
    device: str = "auto"
    whisper_compute_type: str = "int8"
    # VAD engine: "auto" uses pyannote when HF_TOKEN is set, else the
    # token-free energy fallback. Force with "pyannote" or "energy".
    vad_engine: str = "auto"
    segmentation_model: str = "pyannote/segmentation-3.0"

    # Default clip quality / shape filters (overridable per dataset build).
    min_clip_sec: float = 1.0
    max_clip_sec: float = 20.0
    min_snr_db: float = 10.0
    # All clips are resampled to this mono sample rate (standard for ASR/TTS).
    target_sample_rate: int = 16000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def b2_endpoint(self) -> str:
        """Derive the S3-compatible endpoint from the region.

        Keeping only the region in config means no hardcoded endpoint /
        region string lives anywhere else in the source tree.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"


settings = Settings()
