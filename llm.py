import os
import sys
import json
from google import genai

# ENV VARS
api_key = os.getenv("GEMINI_API_KEY")
pr_number = int(os.getenv("PR_NUMBER"))
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

# INPUTS
diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

# READ DIFF
diff_content = ""
if diff_path and os.path.exists(diff_path):
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

if len(diff_content) < 10:
    print("Diff missing or too small. Exiting.")
    sys.exit(0)

# READ SEMGREP JSON
semgrep_json = {}
if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
    except:
        semgrep_json = {}

# ONLY METADATA
analysis_metadata = {
    "version": semgrep_json.get("version"),
    "configs": semgrep_json.get("configs"),
    "rules": semgrep_json.get("rules"),
    "paths_scanned": semgrep_json.get("paths", {}).get("scanned"),
    "errors": semgrep_json.get("errors"),
    "total_findings": len(semgrep_json.get("results", [])),
}

os.makedirs("analysis_output", exist_ok=True)

meta_file = f"analysis_output/semgrep_metadata.json"
with open(meta_file, "w", encoding="utf-8") as f:
    json.dump(analysis_metadata, f, indent=2)

print(f"Saved Semgrep metadata → {meta_file}")

# GEMINI SYSTEM PROMPT
SystemPrompt = f"""
You are an expert technical PR reviewer.

### DIFF
{diff_content}

### SEMGREP METADATA
{json.dumps(analysis_metadata, indent=2)}

### OUTPUT FORMAT (max 140 words)

### Summary
- 2–3 bullets (exact PR changes).

### Why It Matters
- Real reasoning based only on diff.

### Issues
- Real issues found in diff.

### Changes Required
- 1–2 essential fixes.

RULES:
- No hallucinations
- Use only diff + metadata
"""

# CALL GEMINI
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=SystemPrompt,
)

print(response.text.strip())
