import os

replacements = {
    'from core': 'from core',
    'import core': 'import core',
    'from adapters': 'from adapters',
    'import adapters': 'import adapters',
    'from voice.audio': 'from voice.audio',
    'import voice.audio': 'import voice.audio',
    'from voice.tts': 'from voice.tts',
    'import voice.tts': 'import voice.tts',
    'from voice.stt': 'from voice.stt',
    'import voice.stt': 'import voice.stt',
    'from tools': 'from tools',
    'import tools': 'import tools',
    'from input': 'from input',
    'import input': 'import input',
    'from voice.pipeline': 'from voice.pipeline',
    'import voice.pipeline': 'import voice.pipeline',
    'from voice.hands_free': 'from voice.hands_free',
    'import voice.hands_free': 'import voice.hands_free',
    'from ': 'from ',
}

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {path}")

for root, dirs, files in os.walk('.'):
    if 'a work on bruno' in root or '.venv' in root or '.git' in root or 'temp_' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
