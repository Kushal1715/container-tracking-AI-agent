import logging
import time
from datetime import datetime
from temporalio import activity
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

PNCT_API_BASE_URL = "https://twpapi.pachesapeake.com/api/track/GetContainers"
PNCT_SITE_ID = "PNCT_NJ"

@activity.defn
async def scrape_pnct_activity(container_id: str, intent: str) -> Dict[str, Any]:
    activity.logger.info(f"Starting PNCT API call: container_id={container_id}, intent={intent}")
    
    if not container_id or len(container_id) < 4:
        raise ValueError(f"Invalid container ID format: {container_id}")
    
    try:
        container_data = await _fetch_container_from_api(container_id)
        
        if not container_data:
            raise ValueError(f"Container {container_id} not found in PNCT system")
        
        scraped_data = _extract_data_by_intent(container_data, intent)
        
        return {
            "container_id": container_id,
            "intent": intent,
            "data": scraped_data,
            "scraped_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        import httpx
        
        if isinstance(e, httpx.HTTPStatusError):
            activity.logger.error(f"HTTP error calling PNCT API for container {container_id}: {e}")
            if e.response.status_code == 404:
                raise ValueError(f"Container {container_id} not found")
            raise Exception(f"API error: {e.response.status_code} - {e.response.text}")
        elif isinstance(e, httpx.RequestError):
            activity.logger.error(f"Network error calling PNCT API for container {container_id}: {e}")
            raise Exception(f"Network error: {str(e)}")
        else:
            activity.logger.error(f"Error scraping PNCT.net for container {container_id}: {e}")
            raise

async def _fetch_container_from_api(container_id: str) -> Dict[str, Any]:
    import httpx
    
    timestamp = int(time.time() * 1000)
    url = f"{PNCT_API_BASE_URL}?siteId={PNCT_SITE_ID}&key={container_id}&_={timestamp}"
    
    activity.logger.info(f"Calling PNCT API: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data
        else:
            return None

def _extract_data_by_intent(container_data: Dict[str, Any], intent: str) -> Dict[str, Any]:
    def _has_holds(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        holds = []
        if data.get("CarrierReleaseStatus") == "HOLD":
            holds.append("Carrier Hold")
        if data.get("CustomReleaseStatus") != "RELEASED":
            holds.append("Customs Hold")
        if data.get("UsdaStatus") != "RELEASED":
            holds.append("USDA Hold")
        if data.get("YardReleaseStatus") and data.get("YardReleaseStatus") != "RELEASED":
            holds.append("Yard Hold")
        if data.get("MiscHoldStatus"):
            holds.append(f"Misc Hold: {data.get('MiscHoldStatus')}")
        if data.get("IsTerminalHold"):
            holds.append("Terminal Hold")
        return (len(holds) > 0, holds)
    
    has_holds, hold_types = _has_holds(container_data)
    
    if intent == "status":
        return {
            "status": container_data.get("State", "Unknown"),
            "container_state": container_data.get("ContainerState", "Unknown"),
            "location": container_data.get("Location", "Unknown"),
            "available": container_data.get("Available", 0) == 2,
            "availability_display_status": container_data.get("AvailabilityDisplayStatus", "Unknown"),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    elif intent == "location":
        location_data = {
            "location": container_data.get("Location", "Unknown"),
            "yard_name": container_data.get("YardName"),
            "block": container_data.get("Block"),
            "bay": container_data.get("Bay"),
            "position": container_data.get("Position"),
            "state": container_data.get("State", "Unknown"),
            "container_state": container_data.get("ContainerState", "Unknown"),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        if container_data.get("Block") and container_data.get("Bay"):
            location_data["coordinates"] = {
                "lat": 40.7032,
                "lon": -74.1468
            }
        return location_data
    
    elif intent == "availability":
        available = container_data.get("Available", 0) == 2
        return {
            "available": available,
            "availability_display_status": container_data.get("AvailabilityDisplayStatus", "No"),
            "available_for_pickup": available and not has_holds,
            "order_of_accessibility": container_data.get("OrderOfAccessibility"),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    elif intent == "holds":
        return {
            "has_holds": has_holds,
            "hold_types": hold_types,
            "carrier_release_status": container_data.get("CarrierReleaseStatus"),
            "custom_release_status": container_data.get("CustomReleaseStatus"),
            "usda_status": container_data.get("UsdaStatus"),
            "yard_release_status": container_data.get("YardReleaseStatus"),
            "misc_hold_status": container_data.get("MiscHoldStatus"),
            "misc_hold_detail": container_data.get("MiscHoldDetail"),
            "is_terminal_hold": container_data.get("IsTerminalHold", False),
            "carrier_hold": container_data.get("CarrierHold", 0),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    elif intent == "last_free_day":
        last_free_date = container_data.get("LastFreeDate") or container_data.get("LastFreeDt")
        line_last_free_date = container_data.get("LineLastFreeDate") or container_data.get("LineLastFreeDt")
        free_days = container_data.get("FreeDays", "0")
        
        return {
            "last_free_date": last_free_date,
            "line_last_free_date": line_last_free_date,
            "free_days": free_days,
            "first_free_date": container_data.get("FirstFreeDate"),
            "demurrage_due_flag": container_data.get("DemurrageDueFlag"),
            "demurrage_amount": container_data.get("DemurrageAmount", 0.0),
            "line_demurrage_amount": container_data.get("LineDemurrageAmount", 0.0),
            "is_on_demurrage_warning": container_data.get("IsOnDemurrageWarning", False),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    elif intent == "all":
        has_holds, hold_types = _has_holds(container_data)
        available = container_data.get("Available", 0) == 2
        last_free_date = container_data.get("LastFreeDate") or container_data.get("LastFreeDt")
        line_last_free_date = container_data.get("LineLastFreeDate") or container_data.get("LineLastFreeDt")
        
        return {
            "status": {
                "status": container_data.get("State", "Unknown"),
                "container_state": container_data.get("ContainerState", "Unknown"),
                "location": container_data.get("Location", "Unknown"),
                "available": available,
                "availability_display_status": container_data.get("AvailabilityDisplayStatus", "Unknown"),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            },
            "location": {
                "location": container_data.get("Location", "Unknown"),
                "yard_name": container_data.get("YardName"),
                "block": container_data.get("Block"),
                "bay": container_data.get("Bay"),
                "position": container_data.get("Position"),
                "state": container_data.get("State", "Unknown"),
                "container_state": container_data.get("ContainerState", "Unknown"),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            },
            "availability": {
                "available": available,
                "availability_display_status": container_data.get("AvailabilityDisplayStatus", "No"),
                "available_for_pickup": available and not has_holds,
                "order_of_accessibility": container_data.get("OrderOfAccessibility"),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            },
            "holds": {
                "has_holds": has_holds,
                "hold_types": hold_types,
                "carrier_release_status": container_data.get("CarrierReleaseStatus"),
                "custom_release_status": container_data.get("CustomReleaseStatus"),
                "usda_status": container_data.get("UsdaStatus"),
                "yard_release_status": container_data.get("YardReleaseStatus"),
                "misc_hold_status": container_data.get("MiscHoldStatus"),
                "misc_hold_detail": container_data.get("MiscHoldDetail"),
                "is_terminal_hold": container_data.get("IsTerminalHold", False),
                "carrier_hold": container_data.get("CarrierHold", 0),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            },
            "last_free_day": {
                "last_free_date": last_free_date,
                "line_last_free_date": line_last_free_date,
                "free_days": container_data.get("FreeDays", "0"),
                "first_free_date": container_data.get("FirstFreeDate"),
                "demurrage_due_flag": container_data.get("DemurrageDueFlag"),
                "demurrage_amount": container_data.get("DemurrageAmount", 0.0),
                "line_demurrage_amount": container_data.get("LineDemurrageAmount", 0.0),
                "is_on_demurrage_warning": container_data.get("IsOnDemurrageWarning", False),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }
    
    else:
        return {
            "raw_data": container_data,
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
