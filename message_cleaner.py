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
        # New pattern for OSINTCosmos ad
        r"🅾️🆂🅸🅽🆃Cosmos🎗️",
    ]
    cleaned = text
    for pattern in ad_block_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
    # Remove any extra blank lines left after removal
    cleaned = re.sub(r'\n{2,}', '\n\n', cleaned).strip()
    return cleaned

# If you want to test interactively:
if __name__ == "__main__":
    print("Paste your test message (end with Ctrl+D):")
    import sys
    input_text = sys.stdin.read()
    print("\n--- Original ---\n" + input_text)
    cleaned = remove_specific_ad_block(fix_triple_asterisks(input_text))
    print("\n--- After cleaning ---\n" + cleaned)