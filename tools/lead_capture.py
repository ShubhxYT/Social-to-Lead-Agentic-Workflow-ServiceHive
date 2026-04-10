import csv
import os
from datetime import datetime
from langchain_core.tools import tool


def mock_lead_capture(name: str, email: str, platform: str) -> str:
    """Mock API call to register a qualified lead and save to CSV."""
    leads_file = "leads.csv"
    file_exists = os.path.exists(leads_file)
    
    # Write header if file doesn't exist
    if not file_exists:
        with open(leads_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "name", "email", "platform"])
    
    # Append lead data
    with open(leads_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), name, email, platform])
    
    print(f"Lead captured successfully: {name}, {email}, {platform} → saved to {leads_file}")
    return f"Lead captured: {name}, {email}, {platform}"


@tool
def lead_capture_tool(name: str, email: str, platform: str) -> str:
    """Capture a qualified lead. Call only after collecting name, email, and platform.

    Args:
        name: The lead's full name.
        email: The lead's email address.
        platform: The creator platform they use (YouTube, Instagram, TikTok, etc.).
    """
    return mock_lead_capture(name, email, platform)
