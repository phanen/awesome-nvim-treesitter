import os
import re
from datetime import datetime

import requests

# GitHub token is recommended to avoid rate limits
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_metadata(url):
    # Check if it's an issue URL
    issue_match = re.search(r"github\.com/([\w\-\.]+)/([\w\-\.]+)/issues/(\d+)", url)
    repo_match = re.search(r"github\.com/([\w\-\.]+)/([\w\-\.]+)", url)

    if issue_match:
        owner, repo, number = issue_match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        try:
            response = requests.get(api_url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": f"{repo}#{number}: {data['title']}",
                    "value": data.get("reactions", {}).get("total_count", 0),
                    "value_label": "Reactions",
                    "updated": data["updated_at"][:10],
                    "status": data["state"].capitalize(),
                    "url": url,
                    "type": "Issue",
                    "sort_val": data.get("reactions", {}).get("total_count", 0),
                }
        except Exception as e:
            print(f"Error fetching issue {owner}/{repo}#{number}: {e}")

    elif repo_match:
        owner, repo = repo_match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            response = requests.get(api_url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data["full_name"],
                    "value": data["stargazers_count"],
                    "value_label": "Stars",
                    "updated": data["pushed_at"][:10],
                    "status": "Archived" if data["archived"] else "Active",
                    "url": f"https://github.com/{owner}/{repo}",
                    "type": "Repo",
                    "sort_val": data["stargazers_count"],
                }
        except Exception as e:
            print(f"Error fetching repo {owner}/{repo}: {e}")

    return None


def main():
    list_file = "plugins.txt"
    readme_file = "README.md"

    if not os.path.exists(list_file):
        print(f"List file not found: {list_file}")
        return

    with open(list_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    for url in urls:
        print(f"Fetching metadata for: {url}...")
        info = get_metadata(url)
        if info:
            results.append(info)

    # Sort: Repos first (by stars), then Issues (by reactions)
    results.sort(key=lambda x: (x["type"] == "Issue", -x["sort_val"]))

    header = "| Name | Stars/Reactions | Last Update | Status |\n| :--- | :--- | :--- | :--- |\n"
    rows = []
    for r in results:
        val_display = f"{r['value']} (Reactions)" if r["type"] == "Issue" else f"{r['value']}"
        rows.append(
            f"| [{r['name']}]({r['url']}) | {val_display} | {r['updated']} | {r['status']} |"
        )

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
