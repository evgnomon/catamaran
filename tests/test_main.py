from typer.testing import CliRunner
from catamaran.main import app

runner = CliRunner()

def test_hello():
    result = runner.invoke(app, ["hello", "--name", "Test"])
    assert result.exit_code == 0
    assert "Hello Test!" in result.output
