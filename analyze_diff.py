# --- IMPORTS ---
import subprocess   # Built-in Python module to run terminal/shell commands (like running "git diff" from Python)
import os           # Built-in module to access environment variables (like secret API keys stored in your terminal)
from google import genai             # Google's Gemini AI SDK — the main client library
from google.genai import types       # Type definitions for structuring the AI request (schema, config, etc.)


# --- FUNCTION 1: Get Git Changes ---
def get_git_diff():
    """Executes git diff and captures the output string."""
    try:
        result = subprocess.run(        # subprocess.run() executes a shell command from within Python
            ["git", "diff", "HEAD~1", "HEAD", "--stat"],
            # "git diff"       → compare two points in git history
            # "HEAD~1"         → the commit BEFORE your latest one (one step back)
            # "HEAD"           → your most recent commit
            # "--stat"         → show a summary (files changed, lines added/removed) instead of full code diff

            capture_output=True,  # Captures stdout and stderr into result.stdout / result.stderr (instead of printing to terminal)
            text=True,            # Returns output as a readable string instead of raw bytes
            check=True            # Raises an exception automatically if git exits with an error code (e.g., not a git repo)
        )
        return result.stdout      # Returns just the text output of the git command (the file change summary)

    except subprocess.CalledProcessError as e:   # Catches errors thrown when check=True detects a non-zero exit code
        print(f"Git execution error: {e}")        # Prints the error message for debugging
        return None                               # Returns None so the calling code knows something went wrong


# --- FUNCTION 2: Send to Gemini AI and Parse Response ---
def analyze_diff_with_gemini(diff_text):
    """Sends the diff to Gemini and requests a structured JSON response."""

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    # genai.Client()           → creates an authenticated connection to the Gemini API
    # os.environ.get(...)      → safely reads the API key from your environment variables (never hardcode secrets in code!)
    # "GEMINI_API_KEY"         → the name of the env variable you set with: export GEMINI_API_KEY="your-key"

    prompt = f"""
    Analyze the following Git file changes summary:
    {diff_text}
    # {diff_text} → injects the actual git output into the prompt using an f-string (Python string interpolation)

    Generate a security advisory and an automated release note based on the impacted files.
    You must output your answer strictly matching the requested JSON schema structure.
    # This instruction tells the AI to behave like a DevOps analyst and constrains its output format
    """

    try:
        response = client.models.generate_content(   # Calls the Gemini API to generate a response
            model='gemini-2.5-flash',                 # Specifies which Gemini model to use (Flash = faster, cheaper)
            contents=prompt,                          # The full text prompt sent to the model

            config=types.GenerateContentConfig(       # Configuration object that controls how the model responds
                response_mime_type="application/json",
                # Forces the model to return valid JSON — critical for parsing in automated pipelines

                response_schema=types.Schema(         # Defines the exact JSON structure the model MUST follow
                    type=types.Type.OBJECT,           # The top-level response must be a JSON object {}
                    properties={
                        "release_summary": types.Schema(type=types.Type.STRING),
                        # A plain text description of what changed in this release

                        "risk_level": types.Schema(
                            type=types.Type.STRING,
                            enum=["LOW", "MEDIUM", "HIGH"]
                            # Restricts the value to only these 3 options — prevents free-form AI answers
                        ),
                        "security_concerns": types.Schema(type=types.Type.STRING),
                        # A plain text description of any security issues the AI notices
                    },
                    required=["release_summary", "risk_level", "security_concerns"]
                    # All 3 fields MUST be present — the API will error if any are missing
                ),

                temperature=0.2,
                # Controls AI "creativity": 0.0 = fully deterministic, 1.0 = very random
                # 0.2 keeps outputs consistent and factual — ideal for security/technical reports
            ),
        )
        return response.text   # Returns the raw JSON string from the AI response

    except Exception as e:                          # Catches any API errors (network issues, invalid key, quota exceeded, etc.)
        return f"API Connection Failure: {e}"       # Returns a readable error string instead of crashing


# --- ENTRY POINT ---
if __name__ == "__main__":
    print("Fetching local Git diff metrics...")
    git_changes = get_git_diff()

    if git_changes:
        print("Streaming data payload to Gemini...")
        json_report = analyze_diff_with_gemini(git_changes)

        print("\n=== AI-Generated Structured DevOps Report ===")
        print(json_report)

        # NEW: save the report to a file so the workflow can read it
        with open("report.json", "w") as f:
            f.write(json_report)
        print("Report saved to report.json")

    else:
        # NEW: write a safe fallback file so later steps don't fail on missing file
        fallback = json.dumps({
            "release_summary": "No changes detected",
            "risk_level": "LOW",
            "security_concerns": "None"
        })
        with open("report.json", "w") as f:
            f.write(fallback)
        print("No recent Git modifications detected or git repository uninitialized.")
