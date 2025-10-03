from typing import Optional
import typer
from . import __version__

app = typer.Typer(help="Whisper-to-Cards: lecture → dyslexia-friendly notes + Anki.")

@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", help="Show version and exit", is_eager=True
    )
):
    if version:
        typer.echo(f"whisper-to-cards {__version__}")
        raise typer.Exit()

@app.command()
def hello(name: str = "Lenise"):
    """Sanity-check command."""
    typer.echo(f"👋 Hello, {name}! Your CLI is alive.")

@app.command()
def version():
    """Show version."""
    typer.echo(f"whisper-to-cards {__version__}")

if __name__ == "__main__":
    app()
