import os
import sys
import json
from google import genai
from google.genai.errors import APIError

# --- CONFIGURATION ---

api_key = os.getenv("GEMINI_API_KEY")
pr_number = os.getenv("PR_NUMBER", "N/A")
semgrep_config = os.getenv("SEMGREP_CONFIG", "auto")

if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set. LLM review cannot be generated.")
    sys.exit(1)

# INPUTS
diff_path = sys.argv[1] if len(sys.argv) > 1 else None
semgrep_path = sys.argv[2] if len(sys.argv) > 2 else None

if not diff_path:
    print("Error: PR Diff path not provided. Exiting.")
    sys.exit(1)

# --- INITIAL METADATA (prevents NameError) ---
analysis_metadata = {
    "diff_truncated": False
}

# --- READ DIFF ---

diff_content = ""

if os.path.exists(diff_path):
    try:
        with open(diff_path, "r", encoding="utf-8") as f:
            diff_content = f.read()
    except Exception as e:
        print(f"FATAL ERROR: Could not read diff file at {diff_path}: {e}")
        sys.exit(1)
else:
    print(f"FATAL ERROR: PR diff file not found at expected path: {diff_path}")
    print("Check the 'Fetch PR Diff' step output to ensure the file was created.")
    sys.exit(1)

if len(diff_content.strip()) < 10:
    print("Diff missing or too small to review. Exiting.")
    sys.exit(0)

MAX_DIFF_CHARS = 15000
if len(diff_content) > MAX_DIFF_CHARS:
    diff_content = diff_content[:MAX_DIFF_CHARS]
    analysis_metadata["diff_truncated"] = True
    print(f"Warning: Diff content truncated to {MAX_DIFF_CHARS} characters.")

# --- READ SEMGREP JSON ---

semgrep_json = {}

if semgrep_path and os.path.exists(semgrep_path):
    try:
        with open(semgrep_path, "r", encoding="utf-8") as f:
            semgrep_json = json.load(f)
    except json.JSONDecodeError:
        print("Warning: Failed to parse Semgrep JSON. Proceeding without findings.")
    except Exception as e:
        print(f"Warning: Error reading Semgrep file: {e}")
else:
    print("Warning: Semgrep file not found. Proceeding without findings.")

# --- SAFE METADATA EXTRACTION ---

results = semgrep_json.get("results")

analysis_metadata.update({
    "version": semgrep_json.get("version", "N/A"),
    "total_findings": len(results) if isinstance(results, list) else 0,
    "errors": semgrep_json.get("errors", "None"),
    "paths_scanned": semgrep_json.get("paths", {}).get("scanned", "N/A"),
    "relevant_findings": results[:5] if isinstance(results, list) and results else "No findings."
})

# --- SAVE METADATA ---

os.makedirs("analysis_output", exist_ok=True)
meta_file = "analysis_output/semgrep_metadata.json"

with open(meta_file, "w", encoding="utf-8") as f:
    json.dump(analysis_metadata, f, indent=2)

print(f"Saved Semgrep metadata → {meta_file}")

# --- GEMINI PROMPTS ---

SystemPrompt = f"""
You are an expert, meticulous technical Pull Request (PR) reviewer.
Your goal is to analyze the provided PR diff and static analysis data, and generate a concise, structured review summary.

### INPUT DATA
- **PR Diff:**
{diff_content}

- **Semgrep Metadata (relevant findings included):**
{json.dumps(analysis_metadata, indent=2)}

### CONSTRAINTS
- The total review text must be concise (strive for under 140 words).
- Your review must adhere *strictly* to the output format provided in the User Prompt.
- Do not invent information.
- Do not use any introductory sentences.
- Do not mention any tool names.
"""

UserPrompt = """
Generate the automated PR review summary based *only* on the input data above.

**Output Format (START IMMEDIATELY with '## Why It Matters' and use markdown headings in this exact order):**

## Why It Matters
[A short paragraph explaining the impact]

## Issues
[State any security/logic issues found. If none, state: 'No critical issues found.']

## Changes Required
[List 1–2 essential fixes. If none, state: 'No immediate changes required.']

## Summary
- [Bullet 1]
- [Bullet 2]
"""

# --- CALL GEMINI ---

client = genai.Client(api_key=api_key)

try:
    contents = [
    {
        "role": "user",
        "parts": [{
            "text": SystemPrompt + "\n\n" + UserPrompt
        }]
    }
]

    

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={"response_mime_type": "text/plain"}

    )

    print(response.text.strip())

except APIError as e:
    print(f"Error: Gemini API call failed: {e}")
    sys.exit(1)

except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)



