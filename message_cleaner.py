import re

def remove_specific_ad_block(text: str) -> str:
    ad_block_patterns = [
        # Flexible: match both plain and Markdown/link formats, including bold and newlines
        r"🏴‍☠️ ?\*\*?כל הדיווחים בערוץ אחד,\*\*?\s*\*\*?וללא צנזורה!\*\*?\s*\[24\*6 NEWS\]\(https://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https://t\.me/Group24x6\)",
        r"🏴‍☠️ ?\*\*?לא צריך לעבור מערוץ לערוץ,\*\*?\s*\*\*?כל (החדשות|הידיעות) בערוץ אחד!\*\*?\s*\[24\*6 NEWS\]\(https://t\.me/News24x6\)\s*\[24\*6 NEWS DISCUSSIONS\]\(https://t\.me/Group24x6\)",
        r"🏴‍☠️ ?אם אתה לא כאן אתה לא מעודכן\s*חפשו אותנו בטלגרם",
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
    cleaned = remove_specific_ad_block(input_text)
    print("\n--- After remove_specific_ad_block ---\n" + cleaned)