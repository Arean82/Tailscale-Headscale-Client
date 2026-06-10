import os
import xml.etree.ElementTree as ET

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("ERROR: Missing translation library.")
    print("Please run: pip install deep-translator")
    exit(1)

def translate_ts(file_path, target_lang):
    print(f"[*] Translating {os.path.basename(file_path)} to '{target_lang}'...")
    tree = ET.parse(file_path)
    root = tree.getroot()
    translator = GoogleTranslator(source='en', target=target_lang)
    
    translated_count = 0
    for message in root.iter('message'):
        source = message.find('source')
        translation = message.find('translation')
        
        if source is not None and source.text and translation is not None:
            # Only translate if unfinished or empty
            if translation.get('type') == 'unfinished' or not translation.text:
                try:
                    translated_text = translator.translate(source.text)
                    translation.text = translated_text
                    # Remove type attribute to mark as finished
                    if 'type' in translation.attrib:
                        del translation.attrib['type']
                    translated_count += 1
                except Exception as e:
                    print(f"    [!] Failed to translate: {source.text} - Error: {e}")
                    
    if translated_count > 0:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"    -> Successfully translated {translated_count} strings and saved file.\n")
    else:
        print(f"    -> No unfinished strings found. Skipping.\n")

if __name__ == '__main__':
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
            translate_ts(file_path, target_lang)
        else:
            print(f"[!] File not found: {file_path}")
            
    print("[*] Translation process complete!")
