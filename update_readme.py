import asyncio
import os
import re
from datetime import datetime

import aiohttp

# GitHub token is recommended to avoid rate limits
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


async def get_metadata(session, url):
    # Check if it's an issue URL
    issue_match = re.search(r"github\.com/([\w\-\.]+)/([\w\-\.]+)/issues/(\d+)", url)
    repo_match = re.search(r"github\.com/([\w\-\.]+)/([\w\-\.]+)", url)

    try:
        if issue_match:
            owner, repo, number = issue_match.groups()
            api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
            async with session.get(api_url, headers=HEADERS) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": f"{repo}#{number}: {data['title']}",
                        "value": data.get("reactions", {}).get("total_count", 0),
                        "value_label": "Reactions",
                        "updated": data["updated_at"][:10],
                        "status": data["state"].capitalize(),
                        "url": url,
                        "type": "Issue",
                    }
        elif repo_match:
            owner, repo = repo_match.groups()
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            async with session.get(api_url, headers=HEADERS) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": data["full_name"],
                        "value": data["stargazers_count"],
                        "value_label": "Stars",
                        "updated": data["pushed_at"][:10],
                        "status": "Archived" if data["archived"] else "Active",
                        "url": f"https://github.com/{owner}/{repo}",
                        "type": "Repo",
                    }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None


async def main():
    list_file = "plugins.txt"
    readme_file = "README.md"

    if not os.path.exists(list_file):
        print(f"List file not found: {list_file}")
        return

    with open(list_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    async with aiohttp.ClientSession() as session:
        tasks = [get_metadata(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    # Filter out None results
    results = [r for r in results if r]

    # Sort by date (updated) descending - Newest first
    results.sort(key=lambda x: x["updated"], reverse=True)

    header = "| Name | Stars/Reactions | Last Update | Status |\n| :--- | :--- | :--- | :--- |\n"
    rows = []
    for r in results:
        val_display = f"{r['value']} (Reactions)" if r["type"] == "Issue" else f"{r['value']}"
        rows.append(
            f"| [{r['name']}]({r['url']}) | {val_display} | {r['updated']} | {r['status']} |"
        )

    table = header + "\n".join(rows)

    if os.path.exists(readme_file):
        with open(readme_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "## awesome-nvim-treesitter\n"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    replacement = f"## awesome-nvim-treesitter\n\nLast updated: {timestamp}\n\n{table}\n"

    if "## awesome-nvim-treesitter" in content:
        new_content = re.sub(
            r"## awesome-nvim-treesitter\n.*", replacement, content, flags=re.DOTALL
        )
    else:
        new_content = content + "\n" + replacement

    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Done! Processed {len(results)} items. README.md updated.")


if __name__ == "__main__":
    asyncio.run(main())
