import os
import re
from datetime import datetime

import requests

# GitHub token is recommended to avoid rate limits
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_repo_info(url):
    # Extract owner/repo, handle cases like /issues/2068
    match = re.search(r"github\.com/([\w\-\.]+)/([\w\-\.]+)", url)
    if not match:
        return None
    owner, repo = match.groups()
    full_name = f"{owner}/{repo}"
    api_url = f"https://api.github.com/repos/{full_name}"

    try:
        response = requests.get(api_url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            return {
                "name": data["full_name"],
                "stars": data["stargazers_count"],
                "updated": data["pushed_at"][
                    :10
                ],  # pushed_at is usually more relevant for maintenance
                "status": "Archived" if data["archived"] else "Active",
                "url": f"https://github.com/{full_name}",
            }
        else:
            print(f"Error fetching {full_name}: {response.status_code}")
    except Exception as e:
        print(f"Exception for {full_name}: {e}")
    return None


def main():
    list_file = "plugins.txt"
    readme_file = "README.md"

    if not os.path.exists(list_file):
        print(f"List file not found: {list_file}")
        return

    with open(list_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Remove duplicates but keep order
    seen = set()
    unique_urls = []
    for url in urls:
        # Normalize URL to repo root
        match = re.search(r"(https://github\.com/[\w\-\.]+/[\w\-\.]+)", url)
        if match:
            base_url = match.group(1).rstrip(".")
            if base_url not in seen:
                unique_urls.append(base_url)
                seen.add(base_url)

    results = []
    for url in unique_urls:
        print(f"Fetching metadata for: {url}...")
        info = get_repo_info(url)
        if info:
            results.append(info)

    # Sort by stars descending
    results.sort(key=lambda x: x["stars"], reverse=True)

    header = "| Plugin | Stars | Last Update | Status |\n| :--- | :--- | :--- | :--- |\n"
    rows = [
        f"| [{r['name']}]({r['url']}) | {r['stars']} | {r['updated']} | {r['status']} |"
        for r in results
    ]

    table = header + "\n".join(rows)

    # Read current README to preserve other content
    if os.path.exists(readme_file):
        with open(readme_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "## awesome-nvim-treesitter\n"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    replacement = f"## awesome-nvim-treesitter\n\nLast updated: {timestamp}\n\n{table}\n"

    # If the header exists, replace it and everything after it.
    # Or more precisely, replace the section.
    if "## awesome-nvim-treesitter" in content:
        new_content = re.sub(
            r"## awesome-nvim-treesitter\n.*", replacement, content, flags=re.DOTALL
        )
    else:
        new_content = content + "\n" + replacement

    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("README.md updated successfully.")


if __name__ == "__main__":
    main()
