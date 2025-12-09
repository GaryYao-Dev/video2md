import logging
import re
from urllib.parse import urlencode, quote
from typing import Optional, Dict, Any
import httpx

from .abogus import ABogus

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

class LinkExtractor:
    DETAIL_LINK = re.compile(r"\S*?https://www\.douyin\.com/(?:video|note|slides)/([0-9]{19})\S*?")
    DETAIL_SHARE = re.compile(r"\S*?https://www\.iesdouyin\.com/share/(?:video|note|slides)/([0-9]{19})/\S*?")
    DETAIL_MODAL = re.compile(r"modal_id=([0-9]{19})")
    
    @staticmethod
    def get_id(text: str) -> str | None:
        if match := LinkExtractor.DETAIL_LINK.search(text):
            return match.group(1)
        if match := LinkExtractor.DETAIL_SHARE.search(text):
            return match.group(1)
        if match := LinkExtractor.DETAIL_MODAL.search(text):
            return match.group(1)
        return None

class DouyinAPI:
    DOMAIN = "https://www.douyin.com/"
    API_URL = f"{DOMAIN}aweme/v1/web/aweme/detail/"
    
    def __init__(self, cookie: Optional[str] = None, timeout: int = 20):
        self.headers = DEFAULT_HEADERS.copy()
        if cookie:
            self.headers["Cookie"] = cookie
            
        self.abogus = ABogus(user_agent=self.headers["User-Agent"])
        self.client = httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=timeout)

    async def initialize(self):
        """Visit homepage to initialize cookies if no config cookie is provided."""
        if self.headers.get("Cookie"):
            return

        url = "https://www.douyin.com/?recommend=1"
        try:
            logger.info(f"Initializing cookies from {url}...")
            await self.client.get(url)
            logger.info(f"Cookies initialized: {len(self.client.cookies)}")
        except Exception as e:
            logger.warning(f"Failed to initialize cookies: {e}")

    async def get_video_data(self, video_id: str) -> dict | None:
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "aweme_id": video_id,
            "version_code": "190500",
            "version_name": "19.5.0",
            "cookie_enabled": "true",
            "platform": "PC",
            "downlink": "10",
        }
        
        # Determine referer based on video ID context if possible, otherwise generic
        self.client.headers["Referer"] = f"https://www.douyin.com/video/{video_id}"

        query = urlencode(params, quote_via=quote)
        signed_query = query + f"&a_bogus={self.abogus.get_value(query)}"
        
        url = f"{self.API_URL}?{signed_query}"
        logger.info(f"Requests API: {url}")
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Debug logging
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            logger.debug(f"Cookies: {self.client.cookies}")
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON. Content-Type: {response.headers.get('content-type')}")
                logger.error(f"Response Text (first 500 chars): {response.text[:500]!r}")
                if not response.text:
                     logger.error("Response text is empty.")
                raise e
        except Exception as e:
            logger.error(f"API request failed: {e}")
            if 'response' in locals():
                 logger.error(f"Response Status: {response.status_code}")
                 logger.error(f"Response Content Length: {len(response.content)}")
            return None
        
        if not data.get("aweme_detail"):
            logger.warning(f"API returned data but no aweme_detail: {data}")
            return None
            
        return data.get("aweme_detail")

    async def close(self):
        await self.client.aclose()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
