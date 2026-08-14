Central Compliance Tool is a Python-based AI-powered code review system that integrates with GitHub workflows to automatically analyze Git diffs, assess security risks, and post intelligent compliance reviews as pull request comments. It leverages Google's Gemini API to generate structured JSON reports containing release summaries, risk levels, and security concerns for every code change.

Stack
Language: Python 3.11
Runtime: GitHub Actions (workflow automation)
Framework / runtime: Google Gemini AI API (generative model for code analysis)
Notable libraries: google-genai (Gemini API client)
How it's organized
Code
.github/workflows/
  review.yml          Reusable workflow that orchestrates the analysis pipeline
analyze_diff.py       Entry point: captures git diffs and sends to Gemini for review
requirements.txt      Python dependencies (google-genai)
report.json           Generated output file with structured AI analysis
How it fits together:

When triggered by a pull request, the workflow (review.yml) checks out both the target repository and the compliance tool itself. It then runs analyze_diff.py, which:

Captures the git diff between the last two commits using git diff HEAD~1 HEAD --stat
Sends the diff payload to Google Gemini 2.5 Flash model with a structured JSON schema
Parses the response into a JSON report containing release_summary, risk_level (LOW/MEDIUM/HIGH), and security_concerns
Posts the report as a formatted PR comment with visual emoji indicators (🟢/🟡/🔴) based on risk level
The tool includes built-in retry logic (up to 3 attempts with 15-second waits) to handle API rate limits and temporary outages, and gracefully falls back to manual review warnings when Gemini is unavailable.

How to run it
Prerequisites
Python 3.11+
Git repository with commit history
Google Gemini API key
Local Testing
bash
# Clone the repository
git clone https://github.com/ameerhkm/central-compliance-tool
cd central-compliance-tool

# Install dependencies
pip install -r requirements.txt

# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Run the analyzer on your current repo's recent changes
python analyze_diff.py

# View the generated report
cat report.json
GitHub Workflows Integration
The review.yml is a reusable workflow (workflow_call) meant to be invoked by other repositories. To use it:

Add a workflow file in your target repository (.github/workflows/call-review.yml):
YAML
name: Run Central Compliance Review
on: [pull_request]

jobs:
  review:
    uses: ameerhkm/central-compliance-tool/.github/workflows/review.yml@main
    secrets:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
Add your Gemini API key as a repository secret (GEMINI_API_KEY)
Push a PR—the workflow will automatically analyze the diff and post a comment
The workflow requires these GitHub permissions to function:

contents: read — to access repo code
pull-requests: write — to post comments on PRs
