import json, os
from datetime import date
from openai import OpenAI

REPO_HISTORY = "history.json"
OUT_TODAY = "today.json"

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def collect_banned_words(history, days=14):
    # history: [{"date":"YYYY-MM-DD","items":[{"word":...}, ...]}...]
    recent = history[-days:]
    banned = set()
    for day in recent:
        for item in day.get("items", []):
            w = (item.get("word") or "").strip()
            if w:
                banned.add(w)
    return banned

SYSTEM = """You generate daily language cards for a Korean user.
Return ONLY valid JSON (no markdown, no extra text).
Return an array of exactly 3 objects:
1) English short (lang=en, length=short)
2) English long  (lang=en, length=long)
3) Japanese N3+  (lang=jp, level=N3+)

Each object must include:
lang, word, situation, example, sentence, meaning
Additionally:
- English cards must include length: short/long
- Japanese card must include level: N3+

Rules:
- Very common, natural, polite/neutral (not rude, no profanity).
- Domain: everyday + business conversation.
- Format meaning: one-line Korean meaning close to the sentence.
- situation: general state (neutral)
- example: one concrete real-life scene (ONLY ONE).
- sentence: one natural line.
- JP must be JLPT N3+ level vocabulary/phrasing (not textbooky, still realistic spoken Japanese).
"""

def build_prompt(banned_list):
    banned_text = "\n".join(f"- {w}" for w in banned_list) if banned_list else "(none)"
    return f"""Create today's set.

Constraints:
- English short sentence: 3–6 words.
- English long sentence: 10–18 words.
- Japanese: N3+ level.
- Do NOT reuse any of these words (exact match) from the last 14 days:
{banned_text}

Keep examples vivid but realistic (elevator, meeting, email, schedule, awkward silence, etc.).
"""

def validate(items, banned):
    if not isinstance(items, list) or len(items) != 3:
        return "Output must be an array of 3 objects."
    # basic checks
    required = ["lang", "word", "situation", "example", "sentence", "meaning"]
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            return f"Item {i} is not an object."
        for k in required:
            if k not in it or not str(it[k]).strip():
                return f"Item {i} missing/empty field: {k}"
        w = str(it["word"]).strip()
        if w in banned:
            return f"BANNED word reused: {w}"
    # enforce structure
    if items[0].get("lang") != "en" or items[0].get("length") != "short":
        return "Item 0 must be English short with length=short."
    if items[1].get("lang") != "en" or items[1].get("length") != "long":
        return "Item 1 must be English long with length=long."
    if items[2].get("lang") != "jp" or not str(items[2].get("level","")).startswith("N3"):
        return "Item 2 must be Japanese with level starting N3."
    return None

def main():
    history = load_json(REPO_HISTORY, [])
    banned = collect_banned_words(history, days=14)

    # Try a few times in case of collisions
    for attempt in range(1, 6):
        prompt = build_prompt(sorted(banned))
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        text = resp.output_text.strip()
        try:
            items = json.loads(text)
        except Exception:
            continue

        err = validate(items, banned)
        if err is None:
            # save today.json
            save_json(OUT_TODAY, items)

            # append to history and keep last 14
            today = date.today().isoformat()
            history.append({"date": today, "items": [{"word": it["word"]} for it in items]})
            history = history[-14:]
            save_json(REPO_HISTORY, history)
            print("OK")
            return

    raise RuntimeError("Failed to generate valid cards after retries.")

if __name__ == "__main__":
    main()
