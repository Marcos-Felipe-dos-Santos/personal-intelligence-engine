"""Exercise wheel resources and CLI away from the source checkout.

Usage: python tests/smoke_installed_wheel.py dist/<package>.whl
Dependencies must already be installed in the invoking Python environment.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

SMOKE_CODE = r'''
import os
import sys
from pathlib import Path

target = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(target))
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
for name in list(os.environ):
    if name.startswith("PIE_"):
        os.environ.pop(name)
os.environ["PIE_HOME"] = str(Path.cwd() / "data")

from click.testing import CliRunner
from personal_intelligence_engine.app import config
from personal_intelligence_engine.app.adapters.local_llm_extractor import _PROMPT_PATH
from personal_intelligence_engine.app.cli.commands import cli

assert Path(config.__file__).resolve().is_relative_to(target), config.__file__
assert len(list(config.Config().migrations_dir.glob("*.sql"))) == 5
assert _PROMPT_PATH.is_file(), "Versioned LLM prompt missing from installed package"
runner = CliRunner()
for args in [
    ["--version"],
    ["doctor"],
    ["add", "Decidi testar o pacote instalado", "--project", "Teste", "--type", "decision"],
    ["entries", "list"],
    ["search", "pacote"],
    ["report", "project", "--project", "Teste"],
    ["backup", "create"],
    ["export", "json"],
    ["evaluate", "extraction", "--backend", "fake", "--min-score", "0.5"],
]:
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, (args, result.output, result.exception)
print("Installed wheel smoke passed: migrations, prompt, CLI, reports, backup, export and evaluation.")
'''


def main():
    wheel = Path(sys.argv[1]).resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError("Pass a built .whl file.")
    with tempfile.TemporaryDirectory(prefix="pie_wheel_") as work:
        target = Path(work) / "installed"
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
            check=True,
        )
        subprocess.run([sys.executable, "-I", "-c", SMOKE_CODE, str(target)], cwd=work, check=True)


if __name__ == "__main__":
    main()
