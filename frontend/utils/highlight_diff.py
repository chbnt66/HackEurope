import difflib

def highlight_additions(original: str, new: str) -> str:
    """Returns new markdown with added words wrapped in highlight spans."""
    original_words = original.split()
    new_words = new.split()
    
    matcher = difflib.SequenceMatcher(None, original_words, new_words)
    result = []
    
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == 'equal':
            result.append(' '.join(new_words[j1:j2]))
        elif opcode in ('insert', 'replace'):
            added_text = ' '.join(new_words[j1:j2])
            result.append(f'<mark>{added_text}</mark>')
    
    return ' '.join(result)