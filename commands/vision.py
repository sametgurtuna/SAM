import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

def capture_screen_base64() -> str | None:
    """
    Captures the primary screen, resizes it to a manageable resolution,
    and returns it as a base64 encoded JPEG string.
    """
    try:
        from PIL import ImageGrab
        
        # Grab the primary screen
        image = ImageGrab.grab()
        
        # Resize if too large to save memory/tokens
        image.thumbnail((1920, 1080))
        
        # Convert to RGB (in case of RGBA)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        logger.debug("Screen captured and encoded to base64 successfully.")
        return img_str
    except ImportError:
        logger.error("Pillow library not installed. Cannot capture screen.")
        return None
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return None
