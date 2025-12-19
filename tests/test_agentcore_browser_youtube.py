"""Test AgentCore Browser for watching YouTube videos using Playwright (no strands-agents-tools)."""

import asyncio
import boto3
import pytest
from pathlib import Path
from playwright.async_api import async_playwright, Playwright, BrowserType
from bedrock_agentcore.tools.browser_client import browser_session, BrowserClient

YOUTUBE_URL = "https://www.youtube.com/watch?v=JeUpUK0nhC0"
REGION = "us-east-1"
BROWSER_IDENTIFIER = "aws.browser.v1"


async def watch_youtube_video(playwright: Playwright, url: str, watch_seconds: int = 10):
    """Navigate to YouTube and watch video for specified duration."""
    with browser_session(REGION) as client:
        ws_url, headers = client.generate_ws_headers()
        chromium: BrowserType = playwright.chromium
        browser = await chromium.connect_over_cdp(ws_url, headers=headers)
        context = browser.contexts[0]
        page = context.pages[0]

        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            title = await page.title()
            print(f"Page title: {title}")
            print(f"Current URL: {page.url}")

            # Take screenshot
            screenshot_path = Path("tests/youtube_screenshot.png")
            await page.screenshot(path=str(screenshot_path))
            print(f"Screenshot saved: {screenshot_path}")

            # Try to click play button
            try:
                await page.click("button.ytp-large-play-button", timeout=3000)
                print("Clicked play button")
            except Exception:
                print("Video may be auto-playing")

            await asyncio.sleep(watch_seconds)
            return {"title": title, "url": page.url, "watched_seconds": watch_seconds}
        finally:
            await page.close()
            await browser.close()


def get_automation_stream_status(session_id: str) -> str:
    """Get current automation stream status."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.get_browser_session(
        browserIdentifier=BROWSER_IDENTIFIER,
        sessionId=session_id
    )
    return response["streams"]["automationStream"]["streamStatus"]


def enable_automation_stream(session_id: str):
    """Re-enable automation stream after manual Live View intervention."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.update_browser_stream(
        browserIdentifier=BROWSER_IDENTIFIER,
        sessionId=session_id,
        streamUpdate={"automationStreamUpdate": {"streamStatus": "ENABLED"}}
    )
    status = response["streams"]["automationStream"]["streamStatus"]
    print(f"Automation stream status: {status}")
    return status == "ENABLED"


async def wait_for_automation_enabled(session_id: str, timeout: int = 300, poll_interval: int = 3):
    """Poll until automation stream is ENABLED (user released control) or timeout."""
    import time
    start = time.time()
    saw_disabled = False
    
    while time.time() - start < timeout:
        status = get_automation_stream_status(session_id)
        elapsed = int(time.time() - start)
        
        if status == "DISABLED":
            saw_disabled = True
            print(f"  [{elapsed}s] User has taken control (DISABLED)")
        elif status == "ENABLED":
            if saw_disabled:
                print(f"  [{elapsed}s] User released control (ENABLED) - resuming automation")
                return True
            else:
                print(f"  [{elapsed}s] Waiting for user to take control... (still ENABLED)")
        
        await asyncio.sleep(poll_interval)
    
    return False


async def watch_youtube_with_live_view(playwright: Playwright, url: str):
    """
    Open YouTube and wait for manual intervention via AWS Console Live View.
    
    Flow:
    1. Start browser session and navigate to YouTube
    2. Wait for user to complete bot verification via Live View
    3. User presses Enter in terminal when done
    4. Re-enable automation stream and continue
    """
    client = BrowserClient(region=REGION)
    session_id = client.start(session_timeout_seconds=600)
    
    print(f"\n{'='*60}")
    print(f"Session ID: {session_id}")
    print("LIVE VIEW URL:")
    print(f"https://{REGION}.console.aws.amazon.com/bedrock-agentcore/builtInTools")
    print(f"{'='*60}\n")
    
    ws_url, headers = client.generate_ws_headers()
    chromium: BrowserType = playwright.chromium
    browser = await chromium.connect_over_cdp(ws_url, headers=headers)
    context = browser.contexts[0]
    page = context.pages[0]

    try:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        title = await page.title()
        print(f"Page loaded: {title}")
        await page.screenshot(path="tests/youtube_before_intervention.png")
        
        # Close current connection before user takes over
        await browser.close()
        
        # Wait for user to complete intervention and release control
        print("\n>>> Go to Live View, complete bot verification.")
        print(">>> When done, click 'Release control' in Live View.")
        print(f">>> Polling for automation stream to be ENABLED (timeout: 5 min)...\n")
        
        enabled = await wait_for_automation_enabled(session_id, timeout=300, poll_interval=5)
        if not enabled:
            print("Timeout waiting for user to release control. Forcing re-enable...")
            enable_automation_stream(session_id)
        
        # Reconnect to browser with fresh references
        await asyncio.sleep(1)
        ws_url, headers = client.generate_ws_headers()
        browser = await chromium.connect_over_cdp(ws_url, headers=headers)
        context = browser.contexts[0]
        page = context.pages[0]  # Fresh page reference
        
        # Take screenshot after intervention
        await asyncio.sleep(2)
        await page.screenshot(path="tests/youtube_after_intervention.png")
        final_title = await page.title()
        print(f"After intervention - Title: {final_title}")
        print("Reconnection successful - test complete!")
        
        return {"title": final_title, "url": page.url}
    finally:
        try:
            await browser.close()
        except Exception:
            pass
        try:
            client.stop()
        except Exception as e:
            print(f"Session cleanup warning: {e}")
            pass


@pytest.mark.asyncio
async def test_watch_youtube_video():
    """Test watching a YouTube video via AgentCore Browser."""
    async with async_playwright() as playwright:
        result = await watch_youtube_video(playwright, YOUTUBE_URL, watch_seconds=10)

    assert "youtube.com" in result["url"]
    assert result["watched_seconds"] == 10
    print(f"Successfully watched: {result['title']}")


@pytest.mark.asyncio
async def test_watch_youtube_with_manual_login():
    """Test with manual intervention via Live View for bot verification."""
    async with async_playwright() as playwright:
        result = await watch_youtube_with_live_view(playwright, YOUTUBE_URL)
    
    assert "youtube.com" in result["url"]
    print(f"Result: {result['title']}")
