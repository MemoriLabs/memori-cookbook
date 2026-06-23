import subprocess
from pathlib import Path


def get_current_branch(repo_path: str = ".") -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "detached"


def get_repo_name(repo_path: str = ".") -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return url.rstrip("/").split("/")[-1].removesuffix(".git")
    except Exception:
        pass
    return Path(repo_path).resolve().name


def get_context_id(repo_path: str = ".") -> str:
    """Unique entity_id scoped to repo + branch — switches automatically with git checkout."""
    repo = get_repo_name(repo_path)
    branch = get_current_branch(repo_path)
    return f"{repo}/{branch}"


def get_recent_commits(repo_path: str = ".", n: int = 5) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        return []


def get_changed_files(repo_path: str = ".") -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [f for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError:
        return []
