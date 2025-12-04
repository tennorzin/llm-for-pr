import os
import sys
import requests
from github import Github
from google import genai

# --- Configuration & Environment Setup ---

# LLM Model Choice: Fast and cost-effective for summarization
GEMINI_MODEL = 'gemini-2.5-flash'  

# Persona and task definition for the model
SYSTEM_PROMPT = (
    "You are an expert technical editor and PR summarizer. Your goal is to provide a "
    "concise, structured summary of the Pull Request (PR) based on the provided code diff. "
    "Your response must focus on the following:\n"
    "1. **Intent:** What problem does this PR solve?\n"
    "2. **Key Changes:** List 3-5 major files/functions modified.\n"
    "3. **Risk Level:** Assign a risk of LOW, MEDIUM, or HIGH based on the complexity and scope.\n"
    "Respond ONLY in clear Markdown format, using headers as listed."
)

# Load environment variables passed from GitHub Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_FULL_NAME = os.environ.get("REPO_FULL_NAME")

# Basic validation
REQUIRED_ENVS = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "GITHUB_TOKEN": GITHUB_TOKEN,
    "PR_NUMBER": PR_NUMBER,
    "REPO_FULL_NAME": REPO_FULL_NAME
}
missing_envs = [name for name, value in REQUIRED_ENVS.items() if not value]

if missing_envs:
    print(f"Error: Missing core environment variables: {', '.join(missing_envs)}. Cannot proceed.")
    sys.exit(1)
try:
    PR_NUMBER = int(PR_NUMBER)
except ValueError:
    print("Error: PR_NUMBER is not a valid integer.")
    sys.exit(1)

# --- Core Functions ---

def fetch_pr_diff():
    """
    Fetches the raw unified diff for the Pull Request using the GitHub REST API.
    """
    diff_url = f"https://api.github.com/repos/{REPO_FULL_NAME}/pulls/{PR_NUMBER}"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}', 
        'Accept': 'application/vnd.github.v3.diff'
    }
    
    try:
        response = requests.get(diff_url, headers=headers)
        response.raise_for_status() # Raises HTTPError if the status is 4xx or 5xx
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching diff from GitHub API: {e}"

def generate_summary(diff_content):
    """
    Sends the diff content to the Gemini API for summarization.
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Construct the contents array with the system prompt and the diff
        contents = [
            {"role": "user", "parts": [
                {"text": SYSTEM_PROMPT},
                {"text": f"Analyze the following Git Diff:\n\n```diff\n{diff_content}\n```"}
            ]}
        ]
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents
        )
        return response.text

    except Exception as e:
        # Catch and report any API-related failures (e.g., rate limits)
        return f"Error calling Gemini API: {e}"

def post_review(review_text):
    """
    Posts the generated summary as a comment on the Pull Request.
    """
    try:
        # Initialize PyGithub client using the Actions token
        github_client = Github(GITHUB_TOKEN)
        repo_obj = github_client.get_repo(REPO_FULL_NAME)
        pr = repo_obj.get_pull(PR_NUMBER)
        
        # Add a clear header for the bot's comment
        final_comment = f"## 🤖 Gemini Automated PR Summary\n\n{review_text}"
        
        pr.create_issue_comment(final_comment)
        print("Successfully posted PR summary to GitHub.")

    except Exception as e:
        print(f"Error posting comment to GitHub: {e}")
        sys.exit(1)


# --- Execution Start ---

if __name__ == "__main__":
    print(f"Starting review process for PR #{PR_NUMBER} in {REPO_FULL_NAME}...")
    
    # 1. Fetch data
    pr_diff = fetch_pr_diff()
    
    if pr_diff.startswith("Error"):
        post_review(f"🚨 **PR Agent Failure:** Could not retrieve PR changes.\nDetails: {pr_diff}")
        sys.exit(1)
        
    if not pr_diff or "No such file or directory" in pr_diff:
        post_review("✅ **PR Agent Summary:** No significant code changes detected to summarize.")
        sys.exit(0)

    # 2. Generate summary
    summary = generate_summary(pr_diff)
    
    # 3. Post result
    post_review(summary)
