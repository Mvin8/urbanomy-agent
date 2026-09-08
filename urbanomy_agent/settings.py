from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")).resolve())
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("URBANOMY_OUTPUT_DIR", "outputs/server")).resolve())
    host: str = field(default_factory=lambda: os.getenv("URBANOMY_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("URBANOMY_PORT", "8080")))
    public_url: str = field(default_factory=lambda: os.getenv("URBANOMY_PUBLIC_URL", "http://localhost:8080"))
    token: str = field(default_factory=lambda: os.getenv("URBANOMY_API_TOKEN", ""), repr=False)
    max_jobs: int = field(default_factory=lambda: int(os.getenv("URBANOMY_MAX_JOBS", "2")))
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("URBANOMY_JOB_TIMEOUT", "3600")))

    def __post_init__(self):
        if self.max_jobs < 1 or self.timeout_seconds < 1:
            raise ValueError("Job limits must be positive.")
