import typer
import orjson
import yaml

app = typer.Typer()

@app.command()
def hello(name: str = "World"):
    print(f"Hello {name}!")

@app.command()
def json_greet(name: str = "World"):
    print(orjson.dumps({"greeting": f"Hello {name}!"}).decode())

@app.command()
def yaml_greet(name: str = "World"):
    print(yaml.dump({"greeting": f"Hello {name}!"}))

if __name__ == "__main__":
    app()
