"""spaCy-backed normalization and explicit skill phrase extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher

TECHNICAL_TERMS = re.compile(r"(?i)(c\+\+|c#|\.net|fastapi|scikit-learn|aws|nlp|rag|sql|python|java)")


@dataclass(frozen=True)
class NLPProcessor:
    """Reusable processor that records whether a full spaCy model is available."""

    nlp: Language
    model_name: str
    used_fallback: bool

    @classmethod
    def create(cls, model_name: str = "en_core_web_sm") -> "NLPProcessor":
        try:
            return cls(spacy.load(model_name), model_name, False)
        except OSError:
            return cls(spacy.blank("en"), "blank:en", True)

    def clean_text(self, text: str) -> str:
        """Normalize whitespace and preserve technical terms and punctuation."""
        return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()

    def doc(self, text: str):
        """Create a spaCy document from cleaned text."""
        return self.nlp(self.clean_text(text))

    def extract_phrases(
        self,
        text: str,
        terminology: Mapping[str, Iterable[str]],
    ) -> list[str]:
        """Extract explicit configured phrases and return canonical names."""
        matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        canonical: dict[str, str] = {}
        for name, aliases in terminology.items():
            phrases = [name, *aliases]
            matcher.add(name, [self.nlp.make_doc(value) for value in phrases])
            canonical[name.lower()] = name
            canonical.update({value.lower(): name for value in phrases})
        matches = matcher(self.doc(text))
        found: list[str] = []
        for match_id, start, end in matches:
            value = self.doc(text)[start:end].text.lower()
            name = canonical.get(value, self.nlp.vocab.strings[match_id])
            if name not in found:
                found.append(name)
        return found

    def warnings(self) -> list[str]:
        """Explain when the full statistical model was not loaded."""
        if self.used_fallback:
            return ["spaCy model en_core_web_sm is unavailable; using blank English tokenization and phrase matching. Install it with: python -m spacy download en_core_web_sm"]
        return []
