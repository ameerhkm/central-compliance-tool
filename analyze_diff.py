# --- IMPORTS ---
import subprocess
import os
import json
import time    # NEW: needed for the retry wait
from google import genai
from google.genai import types


# --- FUNCTION 1: Get Git Changes ---
def get_git_diff():
    """Executes git diff and captures the output string."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD", "--stat"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git execution error: {e}")
        return None


# --- FUNCTION 2: Send to Gemini AI and Parse Response ---
def analyze_diff_with_gemini(diff_text, retries=3, wait=15):
    """Sends the diff to Gemini and requests a structured JSON response.
    Retries up to 3 times with a 15 second wait if the API returns 503."""

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    prompt = f"""
    Analyze the following Git file changes summary:
    {diff_text}

    Generate a security advisory and an automated release note based on the impacted files.
    You must output your answer strictly matching the requested JSON schema structure.
    """

    # NEW: retry loop — tries up to 3 times before giving up
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt} of {retries}...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "release_summary": types.Schema(type=types.Type.STRING),
                            "risk_level": types.Schema(
                                type=types.Type.STRING,
                                enum=["LOW", "MEDIUM", "HIGH"]
                            ),
                            "security_concerns": types.Schema(type=types.Type.STRING),
                        },
                        required=["release_summary", "risk_level", "security_concerns"]
                    ),
                    temperature=0.2,
                ),
            )
            return response.text  # success — return immediately

        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"Waiting {wait} seconds before retrying...")
                time.sleep(wait)  # wait before next attempt

    # NEW: all retries exhausted — return a valid JSON fallback instead of an error string
    # This ensures report.json always contains parseable JSON even when Gemini is down
    return json.dumps({
        "release_summary": "AI review unavailable — Gemini API returned 503. Please review manually.",
        "risk_level": "MEDIUM",
        "security_concerns": "Could not complete automated analysis. Manual review recommended."
    })


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
