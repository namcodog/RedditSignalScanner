from __future__ import annotations

from typing import Any, Dict, List, Sequence

def generate_demo_posts(
    profile: Any, keywords: Sequence[str]
) -> List[Dict[str, Any]]:
    posts: List[Dict[str, Any]] = []
    seed = sum(ord(c) for c in profile.name) + sum(
        ord(k[0]) for k in keywords or ["base"]
    )

    def pseudo_score(idx: int) -> int:
        return 80 + (seed % 40) + idx * 5

    focus_terms = list(keywords[:3]) or list(profile.description_keywords[:3])
    primary = focus_terms[0] if focus_terms else "workflow"
    secondary = focus_terms[1] if len(focus_terms) > 1 else "automation"
    tertiary = focus_terms[2] if len(focus_terms) > 2 else "reporting"

    competitor_pairs = [
        ("Notion", "Evernote"),
        ("Linear", "Jira"),
        ("Amplitude", "Mixpanel"),
        ("Airtable", "Coda"),
        ("Superhuman", "Outlook"),
    ]
    competitor_a, competitor_b = competitor_pairs[seed % len(competitor_pairs)]

    templates = [
        {
            "id": f"{profile.name}-pain-slow",
            "title": f"Users can't stand how slow {primary} onboarding is in {profile.name}",
            "summary": (
                f"The team finds the {primary} flow painfully slow and unreliable when trying to scale {secondary}."
            ),
        },
        {
            "id": f"{profile.name}-pain-why",
            "title": f"Why is {tertiary} so confusing for {profile.name} teams?",
            "summary": (
                f"People keep asking why {tertiary} remains broken and frustrating even after upgrades in {profile.name}."
            ),
        },
        {
            "id": f"{profile.name}-pain-cant-believe",
            "title": f"Can't believe {secondary} export still doesn't work for {profile.name} leaders",
            "summary": (
                f"It doesn't work for leadership updates and feels expensive and broken for weekly reporting."
            ),
        },
        {
            "id": f"{profile.name}-opportunity-looking",
            "title": "Looking for an automation tool that would pay for itself",
            "summary": (
                f"Our org would love a {primary} assistant that keeps {profile.name} research ops updated automatically."
            ),
        },
        {
            "id": f"{profile.name}-opportunity-need",
            "title": "Need a simple way to keep leadership updated",
            "summary": (
                f"Need a usable workflow that delivers {secondary} insights every Friday for {profile.name} leadership without manual spreadsheets."
            ),
        },
        {
            "id": f"{profile.name}-opportunity-wish",
            "title": f"Wish there was a {secondary} platform designed for {profile.name}",
            "summary": (
                f"Wish there was a {secondary} platform for {profile.name} teams that would pay for itself with {primary} wins."
            ),
        },
        {
            "id": f"{profile.name}-competitor",
            "title": f"{competitor_a} vs {competitor_b}: better alternative to {primary}?",
            "summary": (
                f"Comparing {competitor_a} versus {competitor_b} as an alternative to handle {primary} and {secondary}."
            ),
        },
    ]

    for index, template in enumerate(templates):
        posts.append(
            {
                "id": template["id"],
                "title": template["title"],
                "summary": template["summary"],
                "score": pseudo_score(index),
                "num_comments": 10 + index * 3,
                "permalink": f"https://reddit.com/r/{profile.name}/posts/{template['id']}",
                "url": f"https://reddit.com/r/{profile.name}/posts/{template['id']}",
                "subreddit": profile.name,
            }
        )

    return posts
