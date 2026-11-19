"""Config tests (future-dev 3b): .env is resolved relative to the
backend/ directory, never relative to the process working directory."""
from pathlib import Path

import app.core.config as config_mod


def test_env_file_is_absolute_backend_env():
    """The Settings env_file points at backend/.env, absolutely."""
    env_file = config_mod.Settings.model_config.get("env_file")
    assert env_file is not None
    expected = Path(config_mod.__file__).resolve().parents[2] / ".env"
    assert Path(env_file) == expected
    assert Path(env_file).is_absolute()


def test_env_file_independent_of_cwd(tmp_path, monkeypatch):
    """Changing the working directory must not move the .env lookup."""
    monkeypatch.chdir(tmp_path)
    env_file = Path(config_mod.Settings.model_config["env_file"])
    assert env_file.is_absolute()
    assert env_file.name == ".env"
    assert env_file.parent.name == "backend"
