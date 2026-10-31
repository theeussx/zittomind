import json

from typer.testing import CliRunner

from zittomind.cli.main import app

runner = CliRunner()


def test_classify_cli():
    result = runner.invoke(app, ["classify", "Explique chmod", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["complexity"] == "SIMPLE"


def test_init_does_not_overwrite(tmp_path):
    path = tmp_path / "config.yaml"
    assert runner.invoke(app, ["init", "--path", str(path)]).exit_code == 0
    before = path.read_text()
    assert runner.invoke(app, ["init", "--path", str(path)]).exit_code != 0
    assert path.read_text() == before


def test_config_error_hides_sensitive_values(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("models: super-secret")
    result = runner.invoke(app, ["models", "--config", str(path)])
    assert result.exit_code != 0
    assert "super-secret" not in result.output
