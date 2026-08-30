"""Storyboard + narration for the Vexen demo video (v2).

Each scene is either a title card or a recorded browser scene. Every scene has a
list of narration lines; each line becomes one TTS clip and one burned-in
caption, so the video is understandable with the sound off.
"""

VOICE = "en-US-AndrewNeural"
RATE = "+3%"
PITCH = "+0Hz"

# Gap of silence appended after each line, in seconds.
LINE_GAP = 0.32
# Extra breathing room at the end of a scene.
SCENE_TAIL = 0.55

SCENES = [
    {
        "id": "s00_title",
        "kind": "card",
        "card": "intro",
        "chapter": None,
        "lines": [
            {
                "cap": "Your AI agents can spend your money, email your customers\nand delete your files.",
                "say": "Your AI agents can spend your money, email your customers, and delete your files.",
            },
            {
                "cap": "Vexen decides, every single time, whether they are allowed to.",
                "say": "Vexen decides, every single time, whether they are actually allowed to.",
            },
        ],
    },
    {
        "id": "s01_landing",
        "kind": "web",
        "chapter": "How it works",
        "lines": [
            {
                "cap": "Vexen sits in front of your agents. Every action goes through one call.",
                "say": "Vexen sits in front of your agents. Every action goes through one call.",
            },
            {
                "cap": "There are only ever three answers: Allowed, Blocked, or Needs your OK.",
                "say": "And there are only ever three answers to learn. Allowed. Blocked. Or, needs your OK.",
            },
        ],
    },
    {
        "id": "s02_signup",
        "kind": "web",
        "chapter": "Getting started",
        "lines": [
            {
                "cap": "Getting started is one screen. Your name, your email, a password.",
                "say": "Getting started is one screen. Your name, your email, a password.",
            },
            {
                "cap": "Your workspace begins completely locked down — nothing can act for you yet.",
                "say": "Your workspace begins completely locked down. Nothing can act on your behalf until you say so.",
            },
        ],
    },
    {
        "id": "s03_library",
        "kind": "web",
        "chapter": "Ready-made agents",
        "lines": [
            {
                "cap": "When you are ready, there are over ten thousand ready-made agents.",
                "say": "When you are ready, there are over ten thousand ready-made agents.",
            },
            {
                "cap": "Filter by the job, your field, and how much freedom you want to hand over.",
                "say": "Filter by the job, the field you work in, and how much freedom you want to hand over.",
            },
            {
                "cap": "Every one arrives already narrowed. Nobody starts from a blank page.",
                "say": "Every one of them arrives already narrowed down. Nobody starts from a blank page.",
            },
        ],
    },
    {
        "id": "s04_tryit",
        "kind": "web",
        "chapter": "Try an action",
        "lines": [
            {
                "cap": "Now the part that matters: ask what would happen if your agent tried something.",
                "say": "Now the part that matters. Ask what would happen if your agent tried something.",
            },
            {
                "cap": "$250 is over the cap — so Vexen pauses it and waits for a person.",
                "say": "Two hundred and fifty dollars is over the cap, so Vexen pauses it and waits for a person.",
            },
            {
                "cap": "Nothing has been bought.",
                "say": "Nothing has been bought.",
            },
            {
                "cap": "And it shows every check it made, in order — the same checks, every time.",
                "say": "And it shows you every check it made, in the order it made them. The same checks, every single time.",
            },
        ],
    },
    {
        "id": "s05_blocked",
        "kind": "web",
        "chapter": "Blocked outright",
        "lines": [
            {
                "cap": "Saved card details are refused outright.",
                "say": "Saved card details are refused outright.",
            },
            {
                "cap": "Even if somebody granted that permission by mistake, a rule stops it.",
                "say": "Even if somebody granted that permission by mistake, a rule stops it.",
            },
        ],
    },
    {
        "id": "s06_rules",
        "kind": "web",
        "chapter": "Rules in plain English",
        "lines": [
            {
                "cap": "You can write a safety rule the way you would say it out loud.",
                "say": "You can write a safety rule the way you would say it out loud.",
            },
            {
                "cap": "Vexen turns your sentence into a real rule and shows what it understood.",
                "say": "Vexen turns your sentence into a real rule, and shows you exactly what it understood.",
            },
            {
                "cap": "The AI writes rules. The AI never enforces them.",
                "say": "Nothing is saved until you approve it. The A I writes rules. The A I never enforces them.",
            },
        ],
    },
    {
        "id": "s07_email",
        "kind": "web",
        "chapter": "The alert",
        "lines": [
            {
                "cap": "The moment an agent is paused, everyone allowed to decide gets an email.",
                "say": "The moment an agent is paused, everyone allowed to decide gets an email.",
            },
            {
                "cap": "Which agent, what it wants, how much, and which rule stopped it.",
                "say": "Which agent, what it wants, how much, and which rule stopped it. Then two big buttons.",
            },
        ],
    },
    {
        "id": "s08_phone",
        "kind": "web",
        "chapter": "Approve from your phone",
        "lines": [
            {
                "cap": "Tapping one opens a phone-sized page. No login, no app.",
                "say": "Tapping one opens a phone sized page. No login, no app.",
            },
            {
                "cap": "The link only ever shows the decision. Approving takes a deliberate second tap.",
                "say": "The link only ever shows you the decision. Approving takes a deliberate second tap.",
            },
            {
                "cap": "So a corporate link scanner can never approve a purchase on your behalf.",
                "say": "So a corporate link scanner can never approve a purchase on your behalf.",
            },
        ],
    },
    {
        "id": "s09_approvals",
        "kind": "web",
        "chapter": "Single use, every time",
        "lines": [
            {
                "cap": "Approvals are single use, expire in thirty minutes, and are bound to that action.",
                "say": "Approvals are single use, they expire in thirty minutes, and they are bound to that exact action.",
            },
            {
                "cap": "Same permission, same item, same amount — to the cent.",
                "say": "Same permission, same item, same amount, to the cent.",
            },
        ],
    },
    {
        "id": "s10_developers",
        "kind": "web",
        "chapter": "Genuine enforcement",
        "lines": [
            {
                "cap": "For engineers it is one decorator around the function that spends the money.",
                "say": "For engineers it is one decorator around the function that spends the money.",
            },
            {
                "cap": "If Vexen blocks, that function never runs. If a human is needed, it waits.",
                "say": "If Vexen blocks, that function never runs. If a human is needed, it waits, and then runs exactly once.",
            },
            {
                "cap": "And if Vexen is unreachable, it still does not run. Fail closed is the default.",
                "say": "And if Vexen is unreachable, it still does not run. Fail closed is the default.",
            },
        ],
    },
    {
        "id": "s11_history",
        "kind": "web",
        "chapter": "Evidence",
        "lines": [
            {
                "cap": "Every decision is written down and sealed with a hash, so tampering shows up.",
                "say": "Every decision is written down and sealed with a hash, so tampering shows up.",
            },
            {
                "cap": "One click verifies the whole record.",
                "say": "One click verifies the whole record. Evidence you can hand to somebody who does not trust you.",
            },
        ],
    },
    {
        "id": "s12_team",
        "kind": "web",
        "chapter": "Your team",
        "lines": [
            {
                "cap": "A standing safety check tells you, in plain words, what is worth tightening.",
                "say": "A standing safety check tells you, in plain words, what is worth tightening.",
            },
            {
                "cap": "And your team gets four roles, enforced on the server.",
                "say": "And your team gets four roles, enforced on the server.",
            },
            {
                "cap": "So whoever approves the money never has to be whoever edits the rules.",
                "say": "So the person who approves the money never has to be the person who edits the rules.",
            },
        ],
    },
    {
        "id": "s13_outro",
        "kind": "card",
        "card": "outro",
        "chapter": None,
        "lines": [
            {
                "cap": "Give AI power. Keep control.",
                "say": "Give A I power. Keep control.",
            },
            {
                "cap": "Vexen — free to start, and locked down from the first second.",
                "say": "Vexen. Free to start, and locked down from the very first second.",
            },
        ],
    },
]


def all_lines():
    for scene in SCENES:
        for i, line in enumerate(scene["lines"]):
            yield scene["id"], i, line
