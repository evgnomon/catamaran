import os
from typing_extensions import Annotated
import typer
import httpx
import asyncio

app = typer.Typer()


async def delete_image(tag: str, image_name, username):
    PAT_TOKEN = os.getenv("GITHUB_PAT")

    # GitHub Container Registry API endpoint
    api_url = f"https://api.github.com/user/{username}/packages/container/{image_name}/versions"
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"token {PAT_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Fetch image versions
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        versions = response.json()

        version_id = None
        for version in versions:
            if (
                tag in version["metadata"]["container"]["tags"]
                or version["name"] == tag
            ):
                version_id = version["id"]
                break

        if not version_id:
            print(f"Image version with tag '{tag}' not found.")
        delete_url = f"{api_url}/{version_id}"
        delete_response = await client.delete(delete_url, headers=headers)
        delete_response.raise_for_status()


@app.command()
def delete(
    tag: Annotated[str, typer.Option()],
    image_name: Annotated[str, typer.Option()],
    username: Annotated[str, typer.Option()],
):
    asyncio.run(
        delete_image(
            tag,
            image_name,
            username,
        )
    )


if __name__ == "__main__":
    app()
