"""Lambda: start_viewing - Watch YouTube via AgentCore Browser with Live View intervention."""
import json
import base64
import asyncio
import time
import boto3
from playwright.async_api import async_playwright

REGION = "us-east-1"
BROWSER_IDENTIFIER = "aws.browser.v1"
DEFAULT_DURATION = 300  # 5 minutes


def get_automation_stream_status(session_id: str) -> str:
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.get_browser_session(
        browserIdentifier=BROWSER_IDENTIFIER, sessionId=session_id
    )
    return response["streams"]["automationStream"]["streamStatus"]


def enable_automation_stream(session_id: str) -> bool:
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.update_browser_stream(
        browserIdentifier=BROWSER_IDENTIFIER,
        sessionId=session_id,
        streamUpdate={"automationStreamUpdate": {"streamStatus": "ENABLED"}},
    )
    return response["streams"]["automationStream"]["streamStatus"] == "ENABLED"


async def wait_for_automation_enabled(session_id: str, timeout: int = 300, poll_interval: int = 5):
    """Poll until user releases Live View control or timeout."""
    start = time.time()
    saw_disabled = False

    while time.time() - start < timeout:
        status = get_automation_stream_status(session_id)
        if status == "DISABLED":
            saw_disabled = True
        elif status == "ENABLED" and saw_disabled:
            return True
        await asyncio.sleep(poll_interval)

    return False


async def watch_youtube_with_live_view(video_id: str, duration: int):
    """Watch YouTube with Live View intervention for login/bot verification."""
    from bedrock_agentcore.tools.browser_client import BrowserClient

    url = f"https://www.youtube.com/watch?v={video_id}"
    client = BrowserClient(region=REGION)
    session_id = client.start(session_timeout_seconds=600)
    live_view_url = f"https://{REGION}.console.aws.amazon.com/bedrock-agentcore/builtInTools"

    async with async_playwright() as playwright:
        ws_url, headers = client.generate_ws_headers()
        browser = await playwright.chromium.connect_over_cdp(ws_url, headers=headers)
        context = browser.contexts[0]
        page = context.pages[0]

        try:
            # Navigate and take initial screenshot
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            title = await page.title()
            before_screenshot = await page.screenshot()

            # Close connection for user to take control via Live View
            await browser.close()

            # Wait for user intervention (login/bot verification)
            enabled = await wait_for_automation_enabled(session_id, timeout=300, poll_interval=5)
            if not enabled:
                enable_automation_stream(session_id)

            # Reconnect after user releases control
            await asyncio.sleep(1)
            ws_url, headers = client.generate_ws_headers()
            browser = await playwright.chromium.connect_over_cdp(ws_url, headers=headers)
            context = browser.contexts[0]
            page = context.pages[0]

            # Watch video
            await asyncio.sleep(min(duration, 60))  # Cap for Lambda timeout
            after_screenshot = await page.screenshot()
            final_title = await page.title()

            return {
                "title": final_title,
                "video_id": video_id,
                "session_id": session_id,
                "live_view_url": live_view_url,
                "screenshot": base64.b64encode(after_screenshot).decode("utf-8"),
            }
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            client.stop()


def handler(event, context):
    print(f"Event: {json.dumps(event)}")
    video_id = event.get("video_id")
    duration = event.get("duration", DEFAULT_DURATION)

    if not video_id:
        return {"statusCode": 400, "body": json.dumps({"error": "video_id required"})}

    try:
        result = asyncio.run(watch_youtube_with_live_view(video_id, duration))
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
