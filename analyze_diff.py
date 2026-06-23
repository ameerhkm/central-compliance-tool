# --- IMPORTS ---
import subprocess   # Built-in Python module to run terminal/shell commands
import os           # Built-in module to access environment variables
import json         # Built-in module to parse and write JSON data
from google import genai             # Google's Gemini AI SDK — the main client library
from google.genai import types       # Type definitions for structuring the AI request


# --- FUNCTION 1: Get Git Changes ---
def get_git_diff():
    """Executes git diff and captures the output string."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD", "--stat"],
            capture_output=True,  # Captures stdout and stderr into result.stdout / result.stderr
            text=True,            # Returns output as a readable string instead of raw bytes
            check=True            # Raises an exception if git exits with an error code
        )
        return result.stdout      # Returns the text output of the git command

    except subprocess.CalledProcessError as e:   # Catches errors from a non-zero exit code
        print(f"Git execution error: {e}")
        return None                               # Returns None so calling code knows something went wrong


# --- FUNCTION 2: Send to Gemini AI and Parse Response ---
def analyze_diff_with_gemini(diff_text):
    """Sends the diff to Gemini and requests a structured JSON response."""

    # genai.Client() creates an authenticated connection to the Gemini API
    # os.environ.get() safely reads the API key from environment variables — never hardcode secrets!
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # diff_text is injected into the prompt using an f-string (Python string interpolation)
    # Comments must be OUTSIDE the string — anything inside gets sent to Gemini as part of the prompt
    prompt = f"""
    Analyze the following Git file changes summary:
    {diff_text}

    Generate a security advisory and an automated release note based on the impacted files.
    You must output your answer strictly matching the requested JSON schema structure.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',             # Flash = faster and cheaper than Pro
            contents=prompt,                      # The full prompt text sent to the model

            config=types.GenerateContentConfig(
                response_mime_type="application/json",  # Forces the model to return valid JSON

                response_schema=types.Schema(           # Defines the exact JSON structure the model MUST follow
                    type=types.Type.OBJECT,
                    properties={
                        # A plain text description of what changed in this release
                        "release_summary": types.Schema(type=types.Type.STRING),

                        # Restricted to only these 3 values — prevents free-form AI answers
                        "risk_level": types.Schema(
                            type=types.Type.STRING,
                            enum=["LOW", "MEDIUM", "HIGH"]
                        ),

                        # A plain text description of any security issues the AI notices
                        "security_concerns": types.Schema(type=types.Type.STRING),
                    },
                    # All 3 fields MUST be present in the response — API errors if any are missing
                    required=["release_summary", "risk_level", "security_concerns"]
                ),

                # Controls AI creativity: 0.0 = fully deterministic, 1.0 = very random
                # 0.2 keeps outputs consistent and factual — ideal for security reports
                temperature=0.2,
            ),
        )
        return response.text   # Returns the raw JSON string from the AI response

    except Exception as e:                        # Catches any API errors (network, invalid key, quota, etc.)
        return f"API Connection Failure: {e}"


# --- ENTRY POINT ---
if __name__ == "__main__":
    print("Fetching local Git diff metrics...")
    git_changes = get_git_diff()

    if git_changes:
        print("Streaming data payload to Gemini...")
        json_report = analyze_diff_with_gemini(git_changes)

        print("\n=== AI-Generated Structured DevOps Report ===")
        print(json_report)

        # Save the report to a file so the workflow can read it in the next step
        with open("report.json", "w") as f:
            f.write(json_report)
        print("Report saved to report.json")

    else:
        # Write a safe fallback file so later workflow steps don't fail on a missing file
        fallback = json.dumps({
            "release_summary": "No changes detected",
            "risk_level": "LOW",
            "security_concerns": "None"
        })
        with open("report.json", "w") as f:
            f.write(fallback)
        print("No recent Git modifications detected or git repository uninitialized.")