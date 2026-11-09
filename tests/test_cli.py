"""Humo del CLI: el paquete instalado expone el comando `ecopy`."""

import subprocess


def test_version_command_reports_package_name_and_version():
    result = subprocess.run(["ecopy", "--version"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert result.stdout.strip() == "ecopy 0.1.0"
