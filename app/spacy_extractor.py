# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Dict, List
import spacy
from spacy.language import Language
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class SpacyExtractor:
    """class SpacyExtractor encapsulates logic to pipe Records with an id and text body
    through a spacy model and return entities separated by Entity Type
    """

    def __init__(
        self, nlp: Language, input_id_col: str = "id", input_text_col: str = "text"
    ):
        """Initialize the SpacyExtractor pipeline.
        
        nlp (spacy.language.Language): pre-loaded spacy language model
        input_text_col (str): property on each document to run the model on
        input_id_col (str): property on each document to correlate with request

        RETURNS (EntityRecognizer): The newly constructed object.
        """
        self.nlp = nlp
        self.input_id_col = input_id_col
        self.input_text_col = input_text_col

    @lru_cache(maxsize=1000)
    def _name_to_id(self, text: str) -> str:
        """Utility function to do a messy normalization of an entity name
        Cached for better performance on repeated entity names.

        text (str): text to create "id" from
        """
        return "-".join([s.lower() for s in text.split()])

    def _process_entities(self, spacy_doc) -> Dict:
        """Process entities from a spaCy document and return structured entity data.
        
        Args:
            spacy_doc: A spaCy document object containing entities.
            
        Returns:
            dict: Dictionary mapping entity IDs to entity data with name, label, and matches.
        """
        entities = {}
        
        for ent in spacy_doc.ents:
            ent_id = ent.kb_id or ent.ent_id or self._name_to_id(ent.text)

            if ent_id not in entities:
                # Normalize entity name
                ent_name = ent.text.capitalize() if ent.text.lower() == ent.text else ent.text
                entities[ent_id] = {
                    "name": ent_name,
                    "label": ent.label_,
                    "matches": [],
                }
            
            entities[ent_id]["matches"].append({
                "start": ent.start_char, 
                "end": ent.end_char, 
                "text": ent.text
            })
        
        return entities

    def extract_entities(self, records: List[Dict[str, str]]) -> List[Dict]:
        """Apply the pre-trained model to a batch of records using spaCy's pipe for efficiency
        
        records (list): The list of "document" dictionaries each with an
            `id` and `text` property
        
        RETURNS (list): List of responses containing the id of 
            the correlating document and a list of entities.
        """
        if not records:
            return []

        try:
            ids = [doc[self.input_id_col] for doc in records]
            texts = [doc[self.input_text_col] for doc in records]

            res = []
            # Use spaCy's pipe for efficient batch processing
            for doc_id, spacy_doc in zip(ids, self.nlp.pipe(texts, batch_size=1000)):
                entities = self._process_entities(spacy_doc)
                res.append({"id": doc_id, "entities": list(entities.values())})
            
            return res
            
        except Exception as e:
            logger.error(f"Error in extract_entities: {e}")
            raise

    def extract_noun_phrases(self, documents: List[Dict[str, str]]) -> List[Dict]:
        """Extract noun phrases from a batch of documents using spaCy's pipe for efficiency.

        Args:
            documents (list): A list of dictionaries, each containing an id and text 
                representing the document to process.

        Returns:
            list: A list of dictionaries, each containing the document ID and a list of 
                noun phrases identified within the document text.
        """
        if not documents:
            return []

        try:
            ids = [doc[self.input_id_col] for doc in documents]
            texts = [doc[self.input_text_col] for doc in documents]
            
            results = []
            
            # Use spaCy's pipe for efficient batch processing
            for doc_id, spacy_doc in zip(ids, self.nlp.pipe(texts, batch_size=1000)):
                noun_phrases = [chunk.text for chunk in spacy_doc.noun_chunks]
                
                results.append({
                    "id": doc_id,
                    "noun_phrases": noun_phrases
                })

            return results
            
        except Exception as e:
            logger.error(f"Error in extract_noun_phrases: {e}")
            raise

    def extract_entities_and_noun_phrases(self, documents: List[Dict[str, str]]) -> Dict[str, List[Dict]]:
        """Extract both entities and noun phrases in a single pass for maximum efficiency.
        
        Args:
            documents (list): A list of dictionaries, each containing an id and text.
            
        Returns:
            dict: Dictionary containing 'entities' and 'noun_phrases' results.
        """
        if not documents:
            return {"entities": [], "noun_phrases": []}

        try:
            ids = [doc[self.input_id_col] for doc in documents]
            texts = [doc[self.input_text_col] for doc in documents]
            
            entities_results = []
            noun_phrases_results = []
            
            # Single pass through spaCy's pipe
            for doc_id, spacy_doc in zip(ids, self.nlp.pipe(texts, batch_size=1000)):
                # Extract entities using the common method
                entities = self._process_entities(spacy_doc)
                entities_results.append({"id": doc_id, "entities": list(entities.values())})
                
                # Extract noun phrases
                noun_phrases = [chunk.text for chunk in spacy_doc.noun_chunks]
                noun_phrases_results.append({
                    "id": doc_id,
                    "noun_phrases": noun_phrases
                })
            
            return {
                "entities": entities_results,
                "noun_phrases": noun_phrases_results
            }
            
        except Exception as e:
            logger.error(f"Error in extract_entities_and_noun_phrases: {e}")
            raise