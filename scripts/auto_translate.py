"""Auto-translates the unfinished entries of the .ts catalogs.

Design notes:
* Stylesheet strings (CSS) and keyboard shortcuts are never translated — a
  translated "color: #569cd6;" or "Ctrl+Return" would break the UI at runtime,
  so they are intentionally left unfinished and fall back to the source text.
* Texts are sent with `translate_batch` instead of one request per string,
  which is what triggers Google's 5-requests-per-second throttle.
* Throttling is retried with a backoff, and the final summary reports exactly
  how many strings were translated, skipped and left unfinished.
"""

import argparse
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    from deep_translator.exceptions import BaseError, RequestError, TooManyRequests
except ImportError:
    print("ERROR: Missing translation library.")
    print("Please run: pip install deep-translator")
    sys.exit(1)

# Google is the primary engine; MyMemory covers its rate-limit refusals.
MYMEMORY_TARGETS = {"ar": "ar-SA", "fr": "fr-FR", "es": "es-ES"}

# Never translate: stylesheet fragments and keyboard accelerators
CSS_MARKERS = (
    "color:", "background:", "border:", "font-size:", "padding:", "margin:",
    "transparent", "background-color:", "outline:", "border-radius:", "font-weight:",
)
# Shortcut shapes only. The pattern is deliberately free of nested quantifiers:
# `(?:\s*\+\s*\S+)+` backtracks exponentially on adversarial input (CodeQL
# py/redos #103), so spaces are normalised out before matching instead.
SHORTCUT_RE = re.compile(r"^(?:Ctrl|Alt|Shift|Cmd|Meta|Win|Super)(?:\+[^\s+]+)+$|^F\d{1,2}$", re.IGNORECASE)

BATCH_SIZE = 25
MAX_RETRIES = 2
RETRY_SLEEP = 1.0
MYMEMORY_PAUSE = 0.2  # MyMemory limits characters per day, not requests per second


def _looks_like_shortcut(text):
    """True for accelerator labels such as 'Ctrl+Shift+S', 'Ctrl+,' or 'F1'."""
    return bool(SHORTCUT_RE.match(text.replace(" ", "")))


def is_translatable(text):
    """False for blank, stylesheet and shortcut strings."""
    stripped = text.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    if any(marker in lowered for marker in CSS_MARKERS):
        return False
    return not _looks_like_shortcut(stripped)


def _google_batch(translator, texts, failures):
    """Batched Google call: one request per BATCH_SIZE texts, retried on throttle."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return translator.translate_batch(texts)
        except (TooManyRequests, RequestError) as e:
            if attempt == MAX_RETRIES:
                failures.append(f"google: {len(texts)} strings after {attempt} attempts: {e}")
                return None
            time.sleep(RETRY_SLEEP * attempt)
        except (OSError, BaseError) as e:
            failures.append(f"google: {len(texts)} strings: {e}")
            return None
    return None


def _mymemory_each(translator, texts, failures, progress=None):
    """MyMemory caps query length, so it is called per string with light pacing."""
    results = []
    for index, text in enumerate(texts, start=1):
        try:
            results.append(translator.translate(text))
        except (OSError, BaseError) as e:
            failures.append(f"mymemory: {text[:24]!r}: {e}")
            results.append(None)
        if progress:
            progress(index, len(texts))
        time.sleep(MYMEMORY_PAUSE)
    return results if any(results) else None


def translate_ts(file_path, target_lang, engine="auto"):
    print(f"[*] Translating {os.path.basename(file_path)} to '{target_lang}' (engine={engine})...", flush=True)
    tree = ET.parse(file_path)  # noqa: S314 (parses this project's own checked-in translation XML, not untrusted input)
    root = tree.getroot()

    translator = None
    if engine in ("auto", "google"):
        translator = GoogleTranslator(source='en', target=target_lang)
    fallback = None
    if engine in ("auto", "mymemory"):
        try:
            fallback = MyMemoryTranslator(source='en-US', target=MYMEMORY_TARGETS[target_lang])
        except Exception as e:  # noqa: BLE001 — any backend init failure just disables the fallback
            print(f"    (MyMemory unavailable: {type(e).__name__})", flush=True)

    pending = []      # (source, translation_element)
    skipped = 0
    for message in root.iter('message'):
        source = message.find('source')
        translation = message.find('translation')
        if source is None or not source.text or translation is None:
            continue
        unfinished = translation.get('type') == 'unfinished' or not translation.text
        if not unfinished:
            continue
        if not is_translatable(source.text):
            skipped += 1
            continue
        pending.append((source.text, translation))

    if not pending:
        print(f"    -> nothing to translate ({skipped} stylesheet/shortcut strings left as-is)\n")
        return

    translated = 0
    providers_used = set()
    failures = []
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        texts = [text for text, _ in batch]

        result = _google_batch(translator, texts, failures) if translator is not None else None
        provider = "google"
        if result is None and fallback is not None:
            def progress(done, total, _offset=start):
                print(f"      mymemory {_offset + done}/{len(pending)}", flush=True)
            result = _mymemory_each(fallback, texts, failures, progress=progress)
            provider = "mymemory"
        if not result:
            continue
        providers_used.add(provider)

        for (_, translation), translated_text in zip(batch, result, strict=False):
            if translated_text:
                translation.text = translated_text
                translation.attrib.pop('type', None)
                translated += 1

    if translated:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    engines = ", ".join(sorted(providers_used)) or "none"
    print(f"    -> translated {translated} string(s) via {engines}; {skipped} stylesheet/shortcut "
          f"skipped; {len(pending) - translated} still unfinished", flush=True)
    for failure in failures[:4]:
        print(f"    [!] {failure}", flush=True)
    print(flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Translate unfinished .ts entries.")
    parser.add_argument("--engine", choices=("auto", "google", "mymemory"), default="auto",
                        help="auto = Google first, MyMemory on refusal (default); "
                             "mymemory = skip Google entirely (fast, uses its daily character quota)")
    args = parser.parse_args()

    locales_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')

    # Map the .ts files to their Google Translate language codes
    mappings = {
        'ar_SA.ts': 'ar',
        'fr_FR.ts': 'fr',
        'es_ES.ts': 'es'
    }

    for filename, target_lang in mappings.items():
        file_path = os.path.join(locales_dir, filename)
        if os.path.exists(file_path):
            translate_ts(file_path, target_lang, engine=args.engine)
        else:
            print(f"[!] File not found: {file_path}")

    print("[*] Translation process complete!", flush=True)
