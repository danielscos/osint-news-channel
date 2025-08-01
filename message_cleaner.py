import re

def fix_triple_asterisks(text: str) -> str:
    # Replace ***text*** with **text** (bold)
    # Handles both Hebrew and English, and multiline
    return re.sub(r'\*\*\*(.+?)\*\*\*', r'**\1**', text)

def remove_specific_ad_block(text: str) -> str:
    ad_block_patterns = [
        # Flexible: match ad block with bold, newlines, and Markdown links
        r"🏴‍☠️ ?\*\*אם אתה לא כאן אתה לא מעודכן\*\*\s*\*\*חפשו אותנו בטלגרם\*\*\s*\[24\*6 NEWS\]\(https://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https://t\.me/Group24x6\)",
        r"🏴‍☠️ ?\*\*לא צריך לעבור מערוץ לערוץ,\*\*\s*\*\*כל (החדשות|הידיעות) בערוץ אחד!\*\*\s*\[24\*6 NEWS\]\(https://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https://t\.me/Group24x6\)",
        r"🏴‍☠️ ?\*\*כל הדיווחים בערוץ אחד,\*\*\s*\*\*וללא צנזורה!\*\*\s*\[24\*6 NEWS\]\(https://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https://t\.me/Group24x6\)",
        r"🏴‍☠️ ?אם אתה לא כאן אתה לא מעודכן\s*חפשו אותנו בטלגרם",
        r"🏴‍☠️ ?\*\*אם אתה לא כאן\*\*, \*\*אתה לא מעודכן\*\*!\s*\[ערוץ צבע אדום מבית 24X6 NEWS\]\(https://t\.me/red_alert_24x6\)",
        # Match BOOST ad block
        r"🇮🇱 יש לכם חשבון טלגרם פרימיום ? אנחנו ממש נשמח שתתנו לנו BOOST \(https?://t\.me/boost/News24x6\)\.\s*",
        # Match multi-line ad block from pirate flag to last link (non-greedy, with or without BOOST)
        r"🏴‍☠️[\s\S]*?24\*6 NEWS \(https?://t\.me/News24x6\)\s*24\*6 NEWS DISCUSSIONS \(https?://t\.me/Group24x6\)[\d¹]*",
        r"🏴‍☠️[\s\S]*?\[24\*6 NEWS\]\(https?://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https?://t\.me/Group24x6\)[\d¹]*",
        r"🅾️🆂🅸🅽🆃Cosmos🎗️",
        # Generic: channel signature + Telegram link (any channel in SOURCE_CHANNEL_USERNAMES)
        r"([\u0590-\u05FF \w'\".\-]+)\nhttps?://t\.me/\S+",
    ]
    cleaned = text
    for pattern in ad_block_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
    # Remove any extra blank lines left after removal
    cleaned = re.sub(r'\n{2,}', '\n\n', cleaned).strip()
    return cleaned

def extract_red_alert_summary(text):
    lines = text.strip().splitlines()
    first_line = lines[0] if lines else text
    # Detect alert type
    is_exit_shelter = "ניתן לצאת מהמרחב המוגן" in text
    is_event_ended = "האירוע הסתיים" in text or "השוהים במרחב המוגן יכולים לצאת" in text
    is_rocket_fire = any(word in first_line for word in ["ירי רקטות", "ירי טילים", "שיגור", "שיגורים", "זוהו שיגורים", "זוהה שיגור"]) or "טילים" in first_line
    is_red_alert = "צבע אדום" in first_line
    if not (is_red_alert or is_rocket_fire or is_exit_shelter or is_event_ended):
        return None
    # Extract date/time from first line
    date_time_match = re.search(r"\((\d{1,2}/\d{1,2}/\d{4})\)\s*(\d{1,2}:\d{2})", first_line)
    date_time = f"{date_time_match.group(1)} {date_time_match.group(2)}" if date_time_match else ""
    # Extract only main area names from lines starting with 'אזור' (allowing for extra spaces)
    area_names = []
    seen = set()
    for line in lines:
        line_stripped = line.strip()
        match = re.match(r"^אזור\s+([\u0590-\u05FF '\"\-]+)$", line_stripped)
        if match:
            area = match.group(1).strip()
            if area and area not in seen:
                area_names.append(area)
                seen.add(area)
    regions_str = ", ".join(area_names) if area_names else "אזורים לא ידועים"
    # Extract instruction (look for 'היכנסו למרחב המוגן', 'ניתן לצאת מהמרחב המוגן', or 'השוהים במרחב המוגן יכולים לצאת')
    instruction_match = re.search(r"(היכנסו למרחב המוגן|ניתן לצאת מהמרחב המוגן|השוהים במרחב המוגן יכולים לצאת)[^\n]*", text)
    instruction = instruction_match.group(0) if instruction_match else ""
    # Build summary
    if is_event_ended:
        alert_type = "🚨 עדכון סיום אירוע (Event Ended Update)"
    elif is_exit_shelter:
        alert_type = "🚨 עדכון יציאה מהמרחב המוגן (Shelter Exit Update)"
    elif is_red_alert:
        alert_type = "🚨 צבע אדום (Red Alert)"
    elif is_rocket_fire:
        alert_type = "🚨 ירי רקטות וטילים (Rocket/Missile Fire)"
    else:
        alert_type = "📡 התרעה"
    summary = f"{alert_type}{' - ' + date_time if date_time else ''}\nאזורים עיקריים: {regions_str}"
    if instruction:
        summary += f"\n{instruction}"
    return summary

def extract_flash_alert_summary(text):
    """
    Summarize 'מבזק' (flash alert) messages to only the main affected regions.
    """
    lines = text.strip().splitlines()
    first_line = lines[0] if lines else text
    if not (first_line.startswith('🚨 מבזק') or 'מבזק' in first_line):
        return None
    # Extract date/time from first line
    date_time_match = re.search(r"\((\d{1,2}/\d{1,2}/\d{4})\)\s*(\d{1,2}:\d{2})", first_line)
    date_time = f"{date_time_match.group(1)} {date_time_match.group(2)}" if date_time_match else ""
    # Find all lines that start with 'אזור' (main regions)
    region_lines = [line.strip() for line in lines if re.match(r"^אזור ", line.strip())]
    # Extract region names (e.g., 'אזור גולן דרום')
    region_names = []
    seen = set()
    for line in region_lines:
        # Fix regex: dash should be last or escaped, and quotes do not need to be escaped
        match = re.match(r"^אזור ([\u0590-\u05FF '\"-]+)", line)
        if match:
            region = match.group(1).strip()
            if region and region not in seen:
                region_names.append(region)
                seen.add(region)
    regions_str = ", ".join(region_names) if region_names else "אזורים לא ידועים"
    summary = f"🚨 מבזק (Flash Alert){' - ' + date_time if date_time else ''}\nבדקות הקרובות צפויות להתקבל התרעות באזורך\nאזורים עיקריים: {regions_str}"
    return summary

def extract_area_alert_summary(text):
    """
    Summarize area alert messages that start with the instruction and list regions.
    """
    lines = text.strip().splitlines()
    if not lines:
        return None
    # Detect the instruction line
    if not lines[0].startswith("בדקות הקרובות צפויות להתקבל התרעות באזורך"):
        return None
    # Find all lines that start with 'אזור' (main regions)
    region_lines = [line.strip() for line in lines if re.match(r"^אזור ", line.strip())]
    region_names = []
    seen = set()
    for line in region_lines:
        match = re.match(r"^אזור ([\u0590-\u05FF '\"-]+)", line)
        if match:
            region = match.group(1).strip()
            if region and region not in seen:
                region_names.append(region)
                seen.add(region)
    regions_str = ", ".join(region_names) if region_names else "אזורים לא ידועים"
    summary = f"בדקות הקרובות צפויות להתקבל התרעות באזורך\nאזורים עיקריים: {regions_str}"
    return summary

def clean_message(text: str) -> str:
    # First, fix triple asterisks
    text = fix_triple_asterisks(text)
    # Flash alert summary takes precedence
    flash_alert = extract_flash_alert_summary(text)
    if flash_alert:
        return flash_alert
    # Area alert summary for generic alerts with region headers
    area_alert = extract_area_alert_summary(text)
    if area_alert:
        return area_alert
    # Red Alert summary next
    red_alert = extract_red_alert_summary(text)
    if red_alert:
        return red_alert
    # Otherwise, remove ads
    return remove_specific_ad_block(text)

# If you want to test interactively:
if __name__ == "__main__":
    print("Paste your test message (end with Ctrl+D):")
    import sys
    input_text = sys.stdin.read()
    print("\n--- Original ---\n" + input_text)
    cleaned = clean_message(input_text)
    print("\n--- After cleaning ---\n" + cleaned)
