from __future__ import annotations

from asyncio import run
from dataclasses import asdict, dataclass, is_dataclass
from json import dump, load
from json.encoder import JSONEncoder
from os import environ
from pathlib import Path
from time import time
from typing import Any

from alfred import AlfredClient
from github import Github


class EnhancedJSONEncoder(JSONEncoder):

    def default(self, o: object):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


def dataclass_hook(data: dict[str, Any]) -> Any:
    if "repos" in data:
        data["repos"] = [Repo(**repo) for repo in data["repos"]]
    return data


@dataclass(frozen=True, slots=True)
class Repo:

    name: str
    description: str
    url: str


def fetch_repos() -> list[Repo]:
    dbpath = Path("db.json")
    if not dbpath.exists():
        dbpath.touch()
        dbcontent: dict[str, Any] = {"timestamp": time(), "repos": []}
    else:
        with dbpath.open("r") as dbfile:
            dbcontent = load(dbfile, object_hook=dataclass_hook)
        if time() - dbcontent["timestamp"] > 1 * 24 * 60 * 60:
            dbcontent: dict[str, Any] = {"timestamp": time(), "repos": []}
    if dbcontent["repos"] == []:
        try:
            if not environ.get("GITHUB_TOKEN"):
                client.add_result(
                    "Github token not found", "Please set GITHUB_TOKEN environment variable for private repositories"
                )
                github = Github()
                for repo in github.search_repositories(client.query)[:20]:
                    record = Repo(name=repo.name, description=repo.description, url=repo.html_url)
                    dbcontent["repos"].append(record)
            else:
                github = Github(environ["GITHUB_TOKEN"])
                for repo in github.get_user().get_repos():
                    record = Repo(name=repo.name, description=repo.description, url=repo.html_url)
                    dbcontent["repos"].append(record)
            dbcontent["timestamp"] = time()
        except Exception as e:
            client.add_result("Unexpected error", str(e), icon_path="alfred/icons/failed.png")
    with dbpath.open("w") as dbfile:
        dump(dbcontent, dbfile, cls=EnhancedJSONEncoder)
    return dbcontent["repos"]


async def main():
    await client.update("yedhrab", "github-alfred")
    repos = fetch_repos()
    for repo in repos:
        is_exist = client.query.lower() in repo.name.lower()
        is_exist |= repo.description is not None and client.query.lower() in repo.description.lower()
        if is_exist:
            client.add_result(title=repo.name, subtitle=repo.description, arg=repo.url)
    client.response()


if __name__ == '__main__':
    client = AlfredClient()
    run(main())
