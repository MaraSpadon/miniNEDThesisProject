from flask import Flask, request, render_template
import dawg_python as dawg
import os
import pathlib
from tool.minined import MiniNED

lang_trie = {
    'nl': 'data/nlwiki-20211120.count.min2.salient.completiondawg',
    'simple': 'data/simplewiki-20211120.count.min2.salient.completiondawg',
    'it': 'data/itwiki-20211120.count.min2.salient.completiondawg'
}

basedir = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def get_matches(surface_trie, text):
    normtoks = text.lower().split()
    for i,tok in enumerate(normtoks):
        for comp in surface_trie.keys(tok):
            comp_toks = comp.lower().split()
            if normtoks[i:i+len(comp_toks)] == comp_toks:
                yield i, comp

def get_wikidata_id(entity, lang, text):
    # Files that MiniNED will use
    if lang == 'simple':
        dawgfile = pathlib.Path("tool/data/simple/index_simplewiki-20211120.dawg")
        candidatefile = pathlib.Path("tool/data/simple/clean-q0.25.json")
        modelfile = pathlib.Path("tool/data/simple/clean-q0.25.24b.vw")
    elif lang == 'nl':
        dawgfile = pathlib.Path("tool/data/nl/index_nlwiki-20220301.dawg")
        candidatefile = pathlib.Path("tool/data/nl/clean-q0.25.json")
        modelfile = pathlib.Path("tool/data/nl/clean-q0.25.24b.vw")
    elif lang == 'it':
        dawgfile = pathlib.Path("tool/data/it/index_itwiki-20220301.dawg")
        candidatefile = pathlib.Path("tool/data/it/clean-q0.25.json")
        modelfile = pathlib.Path("tool/data/it/clean-q0.25.24b.vw")
    # Create instance of the MiniNED class
    minined = MiniNED(dawgfile, candidatefile, modelfile, lang)
    # Predict the wikidata ID using MiniNED's predict function
    wikidata_id = minined.predict(text, entity, upperbound=None, all_scores=False)
    return wikidata_id

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
            wikidata_id = get_wikidata_id(w, lang, text)  # Retrieve the Wikidata ID of the entities
            if wikidata_id:
                out.append(f'<a href="https://www.wikidata.org/wiki/Q{wikidata_id}" target="_blank">{w}</a>')  # Append linked entity
            else:
                out.append(w)  # Append unlinked entity
            offset = i + len(comp)
    out.extend(normtoks[offset:])  # Append remaining words
    return ' '.join(out)

@app.route('/el')
def el():
    text = request.args.get('text', '')
    lang = request.args.get('lang', None)

    ftrie = os.path.join(basedir, lang_trie[lang])  # lang model

    surface_trie = dawg.CompletionDAWG()
    surface_trie.load(ftrie)

    return make_links(surface_trie, text, lang).replace('\n', '<br>')

if __name__ == "__main__":
    app.run(debug=True)