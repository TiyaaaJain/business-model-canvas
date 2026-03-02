#!/usr/bin/env python3
"""
Find trending GitHub repositories from this week that have only 1 contributor.

Uses the GitHub Search API to find repositories with high star activity this week,
then filters to only those with exactly 1 contributor.
"""

import sys
import argparse
import datetime
import urllib.request
import urllib.parse
import json


def get_this_week_date():
    """Return the date 7 days ago in YYYY-MM-DD format."""
    week_ago = datetime.date.today() - datetime.timedelta(days=7)
    return week_ago.strftime("%Y-%m-%d")


def github_api_get(url, token=None):
    """Make a GET request to the GitHub API and return parsed JSON."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "find-trending-single-contributor/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} error for {url}: {body}", file=sys.stderr)
        return None


def search_trending_repos(since_date, max_results=100, token=None):
    """Search GitHub for repositories created or pushed this week, sorted by stars."""
    query = f"created:>={since_date}"
    params = urllib.parse.urlencode({
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(max_results, 100),
    })
    url = f"https://api.github.com/search/repositories?{params}"
    data = github_api_get(url, token=token)
    if data is None:
        return []
    return data.get("items", [])


def get_contributor_count(owner, repo, token=None):
    """Return the number of contributors for a repository (capped at 2 for efficiency).

    Requesting per_page=2 is an optimisation: if the repo has exactly 1 contributor
    we get a list of length 1; if it has 2 or more we get length 2 and can skip it
    immediately without fetching the full contributor list.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=2&anon=false"
    data = github_api_get(url, token=token)
    if data is None:
        return None
    return len(data)


def find_trending_single_contributor_repos(max_results=100, token=None):
    """
    Find trending repositories from this week with exactly 1 contributor.

    Returns a list of repository dicts.
    """
    since_date = get_this_week_date()
    print(f"Searching for trending repositories created since {since_date}...\n")

    repos = search_trending_repos(since_date, max_results=max_results, token=token)
    if not repos:
        print("No repositories found or API error.", file=sys.stderr)
        return []

    results = []
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        count = get_contributor_count(owner, name, token=token)
        if count == 1:
            results.append(repo)

    return results


def print_results(repos):
    """Print the list of repositories in a readable format."""
    if not repos:
        print("No trending repositories with exactly 1 contributor found this week.")
        return

    print(f"Found {len(repos)} trending repository/repositories with exactly 1 contributor:\n")
    print(f"{'#':<4} {'Repository':<45} {'Stars':>6}  {'Language':<15} URL")
    print("-" * 100)
    for i, repo in enumerate(repos, start=1):
        full_name = repo.get("full_name", "")
        stars = repo.get("stargazers_count", 0)
        language = repo.get("language") or "N/A"
        url = repo.get("html_url", "")
        print(f"{i:<4} {full_name:<45} {stars:>6}  {language:<15} {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Find trending GitHub repositories from this week with exactly 1 contributor."
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub personal access token (increases API rate limits).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum number of trending repositories to check (default: 100).",
    )
    args = parser.parse_args()

    repos = find_trending_single_contributor_repos(
        max_results=args.max_results,
        token=args.token,
    )
    print_results(repos)


if __name__ == "__main__":
    main()
