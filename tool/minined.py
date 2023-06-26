import pathlib
import json
import logging
import pandas as pd
from vowpalwabbit import pyvw
import dawg_python as dawg

from tool.normalize import normalize
from tool.vectorize import vw_tok

class MiniNED:
    def __init__(
        self,
        dawgfile: pathlib.Path,
        candidatefile: pathlib.Path = None,
        modelfile: pathlib.Path = None,
        vectorizer: pathlib.Path = None,
        ent_feats_csv: pathlib.Path = None,
        lang: str = None,
        fallback: pathlib.Path = None,
    ):
        self.lang = lang

        self.index = dawg.IntDAWG()
        self.index.load(str(dawgfile))

        self.candidates = json.load(candidatefile.open()) if candidatefile else {}
        self.count = json.load(fallback.open()) if fallback else {}

        self.ent_feats = None
        if ent_feats_csv:
            self.ent_feats = pd.read_csv(
                ent_feats_csv, header=None, index_col=0, na_values=""
            )
            self.ent_feats = ent_feats[1].fillna("")
            logging.info(f"Loaded {len(self.ent_feats)} entity features")

        self.model = None
        if candidatefile and modelfile:
            self.model = pyvw.Workspace(
                initial_regressor=str(modelfile),
                loss_function="logistic",
                csoaa_ldf="mc",
                probabilities=True,
                testonly=True,
                quiet=True,
            )

    def _model_predict(self, text, norm, ents, all_scores=False):
        preds = {}
        ents = list(ents)
        toks = "shared |s " + " ".join(vw_tok(text))
        ns = "_".join(vw_tok(norm))
        for i, ent in enumerate(ents):
            efeats = (
                str(self.ent_feats.get(l, "")) if (self.ent_feats is not None) else ""
            )
            efeats = "|f " + efeats if efeats else ""
            cands = [f"{e} |l {ns}={e} {efeats}" for e in ents[i:] + ents[:i]]
            preds[ent] = self.model.predict([toks] + cands)
        if all_scores:
            return preds
        else:
            return max(preds.items(), key=lambda x: x[1])[0]

    def predict(self, text: str, surface: str, upperbound=None, all_scores=False):
        pred = None
        if upperbound:
            gold = str(upperbound)
            for norm in normalize(surface, language=self.lang):
                if (norm in self.count) and (gold in self.count[norm]):
                    pred = gold
            if not pred:
                if str(self.index.get(surface.replace(" ", "_"), -1)) == gold:
                    pred = gold
        else:
            for norm in normalize(surface, language=self.lang):
                ent_cand = self.candidates.get(norm, None)
                if ent_cand and self.model:  # Vowpal Wabbit model
                    pred = self._model_predict(
                        text, norm, ent_cand, all_scores=all_scores
                    )
                elif norm in self.count:  # fallback: most common meaning
                    dist = self.count[norm]
                    pred = max(dist, key=lambda x: dist[x])
                elif surface in self.count:  # fallback for surface form
                    dist = self.count[surface]
                    pred = max(dist, key=lambda x: dist[x])
        return pred
