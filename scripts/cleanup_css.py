import os
import xml.etree.ElementTree as ET

def clean_css_translations(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    cleaned_count = 0
    # Common CSS keywords that identify inline styling
    css_markers = ['color:', 'background:', 'border:', 'font-size:', 'padding:', 'margin:', 'transparent', 'background-color:']
    
    for message in root.iter('message'):
        source = message.find('source')
        translation = message.find('translation')
        
        if source is not None and source.text and translation is not None:
            text = source.text.lower().strip()
            # If it contains CSS properties or looks like a strict CSS block "{...}"
            if any(marker in text for marker in css_markers) or (text.endswith(';') and ':' in text):
                if translation.text and translation.get('type') != 'unfinished':
                    # Erase the bad translation and mark it as unfinished
                    translation.text = None
                    translation.set('type', 'unfinished')
                    cleaned_count += 1
                    
    if cleaned_count > 0:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"[*] Cleaned {cleaned_count} broken CSS translations in {os.path.basename(file_path)}")
    else:
        print(f"[*] No CSS strings needed cleaning in {os.path.basename(file_path)}")

if __name__ == '__main__':
    locales_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')
    
    for filename in ['ar_SA.ts', 'fr_FR.ts', 'es_ES.ts', 'en_US.ts']:
        file_path = os.path.join(locales_dir, filename)
        if os.path.exists(file_path):
            clean_css_translations(file_path)
    
    print("\nCleanup complete! All CSS is protected.")
