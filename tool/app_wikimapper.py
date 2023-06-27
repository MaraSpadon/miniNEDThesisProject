from flask import Flask, request, render_template
import dawg_python as dawg
import os
from threading import local
from wikimapper import WikiMapper

lang_trie = {
    'nl': 'data/nlwiki-20211120.count.min2.salient.completiondawg',
    'simple': 'data/simplewiki-20211120.count.min2.salient.completiondawg',
    'it': 'data/itwiki-20211120.count.min2.salient.completiondawg'
}

basedir = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
local_data = local()

@app.route('/')
def index():
    return render_template('index.html')

def get_matches(surface_trie, text):
    normtoks = text.lower().split()
    for i, tok in enumerate(normtoks):
        for comp in surface_trie.keys(tok):
            comp_toks = comp.lower().split()
            if normtoks[i:i+len(comp_toks)] == comp_toks:
                yield i, comp

def get_wikidata_id(entity, lang):
    if not hasattr(local_data, 'mapper'):
        if lang == 'simple':
            local_data.mapper = WikiMapper("data/simple/index_simplewiki-20211120.db")
        elif lang == 'nl':
            local_data.mapper = WikiMapper("data/nl/index_nlwiki-20220301.db")
        elif lang == 'it':
            local_data.mapper = WikiMapper("data/it/index_itwiki-20220301.db")
    converted_entity = convert_entity(entity)
    wikidata_id = local_data.mapper.title_to_id(converted_entity)
    return wikidata_id

# Convert entity such that it starts with a capital letter and has underscores between multiple words
# This way, the Wikimapper is able to work correctly
def convert_entity(entity):
    words = entity.split()
    if len(words) == 1:
        if not words[0].isupper():
            return words[0].capitalize()
        else:
            return words[0]
    else:
        first_word = words[0]
        if not first_word.isupper():
            first_word = first_word.capitalize()
        return first_word + '_' + '_'.join(words[1:])

def make_links(surface_trie, text, lang):
    normtoks = text.split()
    matches = {}
    for i, m in get_matches(surface_trie, text):
        matches.setdefault(i, set()).add(m)

    offset, out = 0, []
    for i, m in sorted(matches.items()):
        if i >= offset:
            comp = max(m, key=len).split()
            out.extend(normtoks[offset:i])  # Append words before the entity
            w = ' '.join(normtoks[i:i + len(comp)])  # Entity word(s)
            wikidata_id = get_wikidata_id(w, lang)  # Retrieve the Wikidata ID of the entities
            if wikidata_id:
                out.append(f'<a href="https://www.wikidata.org/wiki/{wikidata_id}" target="_blank">{w}</a>')  # Append linked entity
            else:
                out.append(w)  # Append unlinked entity
            offset = i + len(comp)
    out.extend(normtoks[offset:])  # Append remaining words
    return ' '.join(out)

@app.route('/el')
def el():
    text = request.args.get('text', '')
    lang = request.args.get('lang', None)

    ftrie = os.path.join(basedir, lang_trie[lang])

    surface_trie = dawg.CompletionDAWG()
    surface_trie.load(ftrie)

    return make_links(surface_trie, text, lang).replace('\n', '<br>')

if __name__ == "__main__":
    app.run(debug=True)