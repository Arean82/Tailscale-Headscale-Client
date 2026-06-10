import os
import re
import sys

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Please install deep-translator: pip install deep-translator")
    sys.exit(1)

def translate_markdown(file_path, target_lang):
    print(f"[*] Translating {os.path.basename(file_path)} to '{target_lang}'...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    translator = GoogleTranslator(source='auto', target=target_lang)
    
    lines = content.split('\n')
    translated_lines = []
    
    in_code_block = False
    for line in lines:
        if line.startswith('```'):
            in_code_block = not in_code_block
            translated_lines.append(line)
            continue
            
        if in_code_block:
            translated_lines.append(line)
            continue
            
        # Skip empty lines and structural HTML/badges
        if not line.strip() or line.startswith('[![') or '<div' in line or '<img' in line or '</div>' in line or line.startswith('---'):
            translated_lines.append(line)
            continue
            
        # Protect headings
        match = re.match(r'^(#+)\s+(.*)', line)
        if match:
            heading_marks = match.group(1)
            text_to_translate = match.group(2)
            try:
                translated = translator.translate(text_to_translate)
                if translated is None:
                    translated = text_to_translate
                translated_lines.append(f"{heading_marks} {translated}")
            except Exception as e:
                print(f"[!] Error translating: {e}")
                translated_lines.append(line)
            continue
            
        # Protect list items
        match_list = re.match(r'^(\s*[-*]|\d+\.)\s+(.*)', line)
        if match_list:
            prefix = match_list.group(1)
            text_to_translate = match_list.group(2)
            try:
                translated = translator.translate(text_to_translate)
                if translated is None:
                    translated = text_to_translate
                translated_lines.append(f"{prefix} {translated}")
            except:
                translated_lines.append(line)
            continue
            
        # Translate normal text
        try:
            translated = translator.translate(line)
            if translated is None:
                translated = line
            translated_lines.append(translated)
        except:
            translated_lines.append(line)
            
    out_file = file_path.replace('.md', f'_{target_lang}.md')

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(translated_lines))
        
    print(f"    -> Successfully saved to {os.path.basename(out_file)}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'Docs')
    readme_path = os.path.join(docs_dir, 'README.md')
    
    if not os.path.exists(readme_path):
        print(f"[!] Could not find {readme_path}")
        sys.exit(1)
        
    targets = ['ar', 'fr', 'es']
    for lang in targets:
        translate_markdown(readme_path, lang)
        
    print("[*] README Translation complete!")
