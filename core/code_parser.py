import os
import re
import datetime
import logging

logger = logging.getLogger(__name__)

# Basic map of markdown language hints to file extensions
LANG_TO_EXT = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "csharp": ".cs",
    "cs": ".cs",
    "c#": ".cs",
    "cpp": ".cpp",
    "c++": ".cpp",
    "c": ".c",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "bash": ".sh",
    "sh": ".sh",
    "powershell": ".ps1",
    "ps1": ".ps1",
    "java": ".java",
    "ruby": ".rb",
    "rb": ".rb",
    "go": ".go",
    "rust": ".rs",
    "rs": ".rs",
    "php": ".php",
    "swift": ".swift",
    "sql": ".sql",
    "xml": ".xml",
    "yaml": ".yaml",
    "yml": ".yml"
}

def extract_and_save_code(text: str) -> str:
    """
    Finds markdown code blocks in the text, saves them to the Desktop,
    and replaces them with a short spoken placeholder for TTS.
    """
    # Regex to match markdown code blocks
    # Group 1: language (optional)
    # Group 2: code content
    pattern = re.compile(r'```(\w*)\s*\n(.*?)```', re.DOTALL)
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    def replacer(match):
        lang = match.group(1).strip().lower()
        code = match.group(2).strip()
        
        if not code:
            return ""
            
        ext = LANG_TO_EXT.get(lang, ".txt")
        
        # Generate filename: sam_script_YYYYMMDD_HHMMSS.ext
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sam_script_{timestamp}{ext}"
        filepath = os.path.join(desktop_path, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info("Saved generated code to %s", filepath)
            return " [İstediğiniz kod masaüstüne kaydedildi.] "
        except Exception as e:
            logger.error("Failed to save code to desktop: %s", e)
            return " [Kodu masaüstüne kaydederken bir hata oluştu.] "

    # Replace all code blocks and return the cleaned text
    cleaned_text = pattern.sub(replacer, text)
    return cleaned_text
