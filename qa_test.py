#!/usr/bin/env python3
"""
End-to-End QA Test Suite for Planning Center Publishing Scripts
Tests main.py and updateyoutube.py workflows with full verification
"""

import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import datetime
import subprocess
import sys

# Load credentials
APP_ID = config('App_ID')
SECRET = config('Secret')
YTKEY = os.environ.get('YTKEY') or config('YTKEY')

# Test results storage
test_results = {
    "test_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    "main_py_execution": {},
    "updateyoutube_py_execution": {},
    "verification_results": {},
    "all_ids": {},
    "errors": []
}

def log_test(message, level="INFO"):
    """Log test messages with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = {
        "INFO": "ℹ️",
        "PASS": "✓",
        "FAIL": "✗",
        "WARN": "⚠️"
    }.get(level, "")
    print(f"[{timestamp}] {prefix} {message}")

def verify_endpoint(endpoint_url, expected_fields, description):
    """Verify an API endpoint returns expected data"""
    log_test(f"Verifying {description}...", "INFO")

    try:
        response = requests.get(endpoint_url, auth=HTTPBasicAuth(APP_ID, SECRET))

        if response.status_code != 200:
            log_test(f"FAILED: {description} - HTTP {response.status_code}", "FAIL")
            test_results["errors"].append({
                "verification": description,
                "error": f"HTTP {response.status_code}",
                "response": response.text[:500]
            })
            return None

        data = response.json()

        # Check for expected fields
        missing_fields = []
        for field_path in expected_fields:
            parts = field_path.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    missing_fields.append(field_path)
                    break

        if missing_fields:
            log_test(f"FAILED: {description} - Missing fields: {missing_fields}", "FAIL")
            test_results["errors"].append({
                "verification": description,
                "error": f"Missing fields: {missing_fields}",
                "response": json.dumps(data, indent=2)[:500]
            })
            return data

        log_test(f"PASSED: {description}", "PASS")
        return data

    except Exception as e:
        log_test(f"FAILED: {description} - Exception: {e}", "FAIL")
        test_results["errors"].append({
            "verification": description,
            "error": str(e)
        })
        return None

def main():
    log_test("=" * 80, "INFO")
    log_test("STARTING END-TO-END QA TEST SUITE", "INFO")
    log_test("=" * 80, "INFO")

    # ========== PHASE 1: Execute main.py ==========
    log_test("\n=== PHASE 1: Testing main.py (Episode Creation) ===", "INFO")

    try:
        log_test("Executing main.py...", "INFO")

        # Ensure YTKEY is available as environment variable
        env = os.environ.copy()
        if YTKEY:
            env['YTKEY'] = YTKEY

        result = subprocess.run(
            ["python3", "main.py"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        test_results["main_py_execution"]["return_code"] = result.returncode
        test_results["main_py_execution"]["stdout"] = result.stdout
        test_results["main_py_execution"]["stderr"] = result.stderr

        if result.returncode != 0:
            log_test(f"FAILED: main.py exited with code {result.returncode}", "FAIL")
            log_test(f"STDERR: {result.stderr}", "FAIL")
        else:
            log_test("PASSED: main.py executed successfully", "PASS")

        # Extract Episode ID from log file
        log_test("Extracting Episode ID from main.log...", "INFO")
        with open("main.log", "r") as f:
            log_content = f.read()
            # Look for "Episode ID: XXXXX"
            for line in log_content.split('\n'):
                if "Episode ID:" in line and "Episode time ID:" not in line:
                    episode_id = line.split("Episode ID:")[-1].strip()
                    test_results["all_ids"]["episode_id"] = episode_id
                    log_test(f"Found Episode ID: {episode_id}", "PASS")
                    break

            # Look for "Episode time ID: XXXXX"
            for line in log_content.split('\n'):
                if "Episode time ID:" in line:
                    episode_time_id = line.split("Episode time ID:")[-1].strip()
                    test_results["all_ids"]["episode_time_id"] = episode_time_id
                    log_test(f"Found Episode Time ID: {episode_time_id}", "PASS")
                    break

        if "episode_id" not in test_results["all_ids"]:
            log_test("FAILED: Could not extract Episode ID from main.log", "FAIL")
            test_results["errors"].append({
                "phase": "main.py ID extraction",
                "error": "Episode ID not found in log"
            })
            return

    except subprocess.TimeoutExpired:
        log_test("FAILED: main.py execution timed out", "FAIL")
        test_results["errors"].append({"phase": "main.py", "error": "Timeout after 30s"})
        return
    except Exception as e:
        log_test(f"FAILED: main.py execution error: {e}", "FAIL")
        test_results["errors"].append({"phase": "main.py", "error": str(e)})
        return

    # ========== PHASE 2: Verify Episode Creation ==========
    log_test("\n=== PHASE 2: Verifying Episode Creation ===", "INFO")

    episode_id = test_results["all_ids"]["episode_id"]
    episode_time_id = test_results["all_ids"]["episode_time_id"]

    # Verify episode
    episode_url = f"https://api.planningcenteronline.com/publishing/v2/episodes/{episode_id}"
    episode_data = verify_endpoint(
        episode_url,
        ["data.id", "data.attributes.title", "data.attributes.published_to_library_at"],
        "Episode creation and attributes"
    )

    if episode_data:
        test_results["verification_results"]["episode"] = {
            "id": episode_data.get("data", {}).get("id"),
            "title": episode_data.get("data", {}).get("attributes", {}).get("title"),
            "published_to_library_at": episode_data.get("data", {}).get("attributes", {}).get("published_to_library_at")
        }

        # Validate title format
        title = episode_data.get("data", {}).get("attributes", {}).get("title", "")
        today = datetime.now().date()
        expected_date_str = today.strftime('%B %d, %Y')
        if expected_date_str in title:
            log_test(f"PASSED: Episode title contains correct date: {title}", "PASS")
        else:
            log_test(f"FAILED: Episode title doesn't match expected date. Got: {title}", "FAIL")

    # Verify episode time
    episode_time_url = f"https://api.planningcenteronline.com/publishing/v2/episodes/{episode_id}/episode_times/{episode_time_id}"
    episode_time_data = verify_endpoint(
        episode_time_url,
        ["data.id", "data.attributes.starts_at", "data.attributes.video_embed_code"],
        "Episode time and initial video embed"
    )

    if episode_time_data:
        embed_code = episode_time_data.get("data", {}).get("attributes", {}).get("video_embed_code") or ""
        test_results["verification_results"]["episode_time_before_update"] = {
            "id": episode_time_data.get("data", {}).get("id"),
            "starts_at": episode_time_data.get("data", {}).get("attributes", {}).get("starts_at"),
            "video_embed_code": embed_code[:200] if embed_code else ""
        }

        # Check if initial embed has livestream URL
        if embed_code and "youtube.com/embed/live_stream" in embed_code:
            log_test("PASSED: Initial embed contains livestream URL", "PASS")
        elif embed_code:
            log_test("WARN: Initial embed doesn't contain expected livestream URL", "WARN")
        else:
            log_test("WARN: Initial embed code is empty/null", "WARN")

    # ========== PHASE 3: Execute updateyoutube.py ==========
    log_test("\n=== PHASE 3: Testing updateyoutube.py (YouTube Integration) ===", "INFO")

    try:
        log_test("Executing updateyoutube.py...", "INFO")
        log_test("NOTE: This may take up to 5 minutes if no live stream is active", "INFO")

        # Ensure YTKEY is available as environment variable
        env = os.environ.copy()
        if YTKEY:
            env['YTKEY'] = YTKEY

        result = subprocess.run(
            ["python3", "updateyoutube.py"],
            capture_output=True,
            text=True,
            timeout=360,  # 6 minutes to allow for retry logic
            env=env
        )

        test_results["updateyoutube_py_execution"]["return_code"] = result.returncode
        test_results["updateyoutube_py_execution"]["stdout"] = result.stdout
        test_results["updateyoutube_py_execution"]["stderr"] = result.stderr

        if result.returncode != 0:
            log_test(f"FAILED: updateyoutube.py exited with code {result.returncode}", "FAIL")
            log_test(f"STDERR: {result.stderr}", "FAIL")
        else:
            log_test("PASSED: updateyoutube.py executed successfully", "PASS")

        # Extract YouTube Video ID from log file
        log_test("Extracting YouTube Video ID from updateyoutube.log...", "INFO")
        with open("updateyoutube.log", "r") as f:
            log_content = f.read()
            # Look for "Found live stream: XXXXX" or "Found most recent video: XXXXX"
            for line in log_content.split('\n'):
                if "Found live stream:" in line:
                    youtube_id = line.split("Found live stream:")[-1].strip()
                    test_results["all_ids"]["youtube_video_id"] = youtube_id
                    test_results["all_ids"]["youtube_source"] = "live_stream"
                    log_test(f"Found YouTube Video ID (live): {youtube_id}", "PASS")
                    break
                elif "Found most recent video:" in line:
                    # Format: "Found most recent video: VIDEO_ID - 'Title'"
                    parts = line.split("Found most recent video:")[-1].strip().split(" - ")
                    youtube_id = parts[0].strip()
                    test_results["all_ids"]["youtube_video_id"] = youtube_id
                    test_results["all_ids"]["youtube_source"] = "most_recent"
                    if len(parts) > 1:
                        test_results["all_ids"]["youtube_video_title"] = parts[1].strip().strip("'\"")
                    log_test(f"Found YouTube Video ID (recent): {youtube_id}", "PASS")
                    break

        if "youtube_video_id" not in test_results["all_ids"]:
            log_test("FAILED: Could not extract YouTube Video ID from updateyoutube.log", "FAIL")
            test_results["errors"].append({
                "phase": "updateyoutube.py ID extraction",
                "error": "YouTube Video ID not found in log"
            })
            # Continue anyway to check other aspects

    except subprocess.TimeoutExpired:
        log_test("FAILED: updateyoutube.py execution timed out (>6 minutes)", "FAIL")
        test_results["errors"].append({"phase": "updateyoutube.py", "error": "Timeout after 6 minutes"})
    except Exception as e:
        log_test(f"FAILED: updateyoutube.py execution error: {e}", "FAIL")
        test_results["errors"].append({"phase": "updateyoutube.py", "error": str(e)})

    # ========== PHASE 4: Verify Updates ==========
    log_test("\n=== PHASE 4: Verifying YouTube Integration Updates ===", "INFO")

    # Re-verify episode time to check for updated embed code
    episode_time_data_after = verify_endpoint(
        episode_time_url,
        ["data.id", "data.attributes.video_embed_code"],
        "Episode time after YouTube update"
    )

    if episode_time_data_after:
        embed_code_after = episode_time_data_after.get("data", {}).get("attributes", {}).get("video_embed_code") or ""
        test_results["verification_results"]["episode_time_after_update"] = {
            "id": episode_time_data_after.get("data", {}).get("id"),
            "video_embed_code": embed_code_after[:200] if embed_code_after else ""
        }

        # Check if embed was updated with actual video ID
        if "youtube_video_id" in test_results["all_ids"]:
            youtube_id = test_results["all_ids"]["youtube_video_id"]
            if youtube_id in embed_code_after:
                log_test(f"PASSED: Episode time embed updated with YouTube ID: {youtube_id}", "PASS")
            else:
                log_test(f"FAILED: Episode time embed doesn't contain expected YouTube ID: {youtube_id}", "FAIL")
                log_test(f"Embed code: {embed_code_after[:200]}", "INFO")
        else:
            log_test("WARN: Cannot verify embed update - YouTube ID not extracted", "WARN")

    # Verify episode-level updates (library_video_url, description)
    episode_data_after = verify_endpoint(
        episode_url,
        ["data.id", "data.attributes.library_video_url"],
        "Episode after YouTube updates"
    )

    if episode_data_after:
        library_url = episode_data_after.get("data", {}).get("attributes", {}).get("library_video_url") or ""
        description = episode_data_after.get("data", {}).get("attributes", {}).get("description") or ""

        test_results["verification_results"]["episode_after_update"] = {
            "library_video_url": library_url,
            "description_length": len(description) if description else 0,
            "description_preview": description[:200] if description else ""
        }

        if "youtube_video_id" in test_results["all_ids"]:
            youtube_id = test_results["all_ids"]["youtube_video_id"]
            expected_url = f"https://www.youtube.com/watch?v={youtube_id}"

            if library_url == expected_url:
                log_test(f"PASSED: Library video URL set correctly: {library_url}", "PASS")
            else:
                log_test(f"FAILED: Library video URL mismatch. Expected: {expected_url}, Got: {library_url}", "FAIL")

        if len(description) > 0:
            log_test(f"PASSED: Episode description populated ({len(description)} characters)", "PASS")
        else:
            log_test("WARN: Episode description is empty", "WARN")

    # ========== PHASE 5: Generate Report ==========
    log_test("\n=== PHASE 5: Generating QA Test Report ===", "INFO")

    report_file = f"qa_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(test_results, f, indent=2)

    log_test(f"PASSED: Test report saved to {report_file}", "PASS")

    # Print summary
    log_test("\n" + "=" * 80, "INFO")
    log_test("QA TEST SUMMARY", "INFO")
    log_test("=" * 80, "INFO")

    log_test("\nCollected IDs:", "INFO")
    for id_name, id_value in test_results["all_ids"].items():
        log_test(f"  {id_name}: {id_value}", "INFO")

    log_test(f"\nTotal Errors: {len(test_results['errors'])}", "FAIL" if test_results["errors"] else "PASS")
    if test_results["errors"]:
        for i, error in enumerate(test_results["errors"], 1):
            log_test(f"  Error {i}: {error}", "FAIL")

    log_test("\nVerification Status:", "INFO")
    log_test(f"  Episode Creation: {'PASS' if 'episode' in test_results['verification_results'] else 'FAIL'}",
             "PASS" if 'episode' in test_results['verification_results'] else "FAIL")
    log_test(f"  Episode Time: {'PASS' if 'episode_time_before_update' in test_results['verification_results'] else 'FAIL'}",
             "PASS" if 'episode_time_before_update' in test_results['verification_results'] else "FAIL")
    log_test(f"  YouTube Integration: {'PASS' if 'youtube_video_id' in test_results['all_ids'] else 'FAIL'}",
             "PASS" if 'youtube_video_id' in test_results['all_ids'] else "FAIL")
    log_test(f"  Episode Updates: {'PASS' if 'episode_after_update' in test_results['verification_results'] else 'FAIL'}",
             "PASS" if 'episode_after_update' in test_results['verification_results'] else "FAIL")

    overall_status = "PASS" if len(test_results["errors"]) == 0 else "FAIL"
    log_test(f"\nOVERALL TEST STATUS: {overall_status}", overall_status.replace("PASS", "PASS").replace("FAIL", "FAIL"))
    log_test("=" * 80, "INFO")

    return 0 if len(test_results["errors"]) == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log_test("\nTest interrupted by user", "WARN")
        sys.exit(130)
    except Exception as e:
        log_test(f"\nFATAL ERROR: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        sys.exit(1)
