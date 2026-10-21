# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from collections import defaultdict
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Callable, List, Dict

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import spacy
from spacy.language import Language
import srsly

from app.models import (
    ENT_PROP_MAP,
    RecordsRequest,
    RecordsResponse,
    RecordsEntitiesByTypeResponse,
    RecordsNounPhrasesResponse,
    RecordsCombinedResponse,
)
from app.spacy_extractor import SpacyExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "en_core_web_sm"

example_request = srsly.read_json(Path(__file__).parent / "data" / "example_request.json")

router = APIRouter()


def load_default_nlp() -> Language:
    """Load the spaCy model the service runs with."""
    logger.info("Loading spaCy model %s...", MODEL_NAME)
    try:
        return spacy.load(MODEL_NAME)
    except OSError:
        logger.error("Please ensure you have installed the spaCy model: python -m spacy download %s", MODEL_NAME)
        raise


def create_app(load_nlp: Callable[[], Language] = load_default_nlp) -> FastAPI:
    """Build the API. The model loads when the app starts, not when this module is imported,
    so tests can pass their own loader."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        nlp = load_nlp()
        application.state.nlp = nlp
        application.state.extractor = SpacyExtractor(nlp)
        logger.info("spaCy model %s_%s ready", nlp.meta["lang"], nlp.meta["name"])
        yield

    application = FastAPI(
        title="rgpl-spacy-api",
        version="1.0",
        description="spaCy FastAPI for Custom Cognitive Skills in Azure Search",
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(router)
    return application


def get_extractor(request: Request) -> SpacyExtractor:
    return request.app.state.extractor


def prepare_documents(values: List) -> List[Dict[str, str]]:
    """Prepare documents for processing to avoid redundant operations."""
    return [{"id": val.recordId, "text": val.data.text} for val in values]

@router.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(f"/docs")

@router.post("/entities", response_model=RecordsResponse, tags=["NER"])
async def extract_entities(
    body: RecordsRequest = Body(..., example=example_request), extractor: SpacyExtractor = Depends(get_extractor)
):
    """Extract Named Entities from a batch of Records."""

    try:
        documents = prepare_documents(body.values)
        entities_res = extractor.extract_entities(documents)

        res = [
            {"recordId": er["id"], "data": {"entities": er["entities"]}, "errors": None, "warnings": None}
            for er in entities_res
        ]

        return {"values": res}
    except Exception as e:
        logger.error(f"Error in extract_entities: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post(
    "/entities_by_type", response_model=RecordsEntitiesByTypeResponse, tags=["NER"]
)
async def extract_entities_by_type(
    body: RecordsRequest = Body(..., example=example_request), extractor: SpacyExtractor = Depends(get_extractor)
):
    """Extract Named Entities from a batch of Records separated by entity label.
        This route can be used directly as a Cognitive Skill in Azure Search
        For Documentation on integration with Azure Search, see here:
        https://docs.microsoft.com/en-us/azure/search/cognitive-search-custom-skill-interface"""

    try:
        documents = prepare_documents(body.values)
        entities_res = extractor.extract_entities(documents)
        res = []

        for er in entities_res:
            groupby = defaultdict(list)
            for ent in er["entities"]:
                ent_prop = ENT_PROP_MAP.get(ent["label"], ent["label"].lower())
                groupby[ent_prop].append(ent["name"])
            record = {"recordId": er["id"], "data": dict(groupby)}
            res.append(record)

        return {"values": res}
    except Exception as e:
        logger.error(f"Error in extract_entities_by_type: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post("/noun_phrases", response_model=RecordsNounPhrasesResponse, tags=["Syntax"])
async def extract_noun_phrases(
    body: RecordsRequest = Body(..., example=example_request), extractor: SpacyExtractor = Depends(get_extractor)
):
    """Extract Noun Phrases from a batch of Records."""

    try:
        documents = prepare_documents(body.values)
        noun_phrases_res = extractor.extract_noun_phrases(documents)

        res = [
            {"recordId": np["id"], "data": {"noun_phrases": np["noun_phrases"]}, "errors": None, "warnings": None}
            for np in noun_phrases_res
        ]

        return {"values": res}
    except Exception as e:
        logger.error(f"Error in extract_noun_phrases: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post("/extract_all", response_model=RecordsCombinedResponse, tags=["Combined"])
async def extract_all(
    body: RecordsRequest = Body(..., example=example_request), extractor: SpacyExtractor = Depends(get_extractor)
):
    """Extract both entities and noun phrases from a batch of Records in a single optimized pass."""

    try:
        documents = prepare_documents(body.values)
        results = extractor.extract_entities_and_noun_phrases(documents)

        # Combine results into the expected format
        combined_results = []
        entities_dict = {er["id"]: er["entities"] for er in results["entities"]}
        noun_phrases_dict = {np["id"]: np["noun_phrases"] for np in results["noun_phrases"]}

        for doc_id in entities_dict.keys():
            combined_results.append({
                "recordId": doc_id,
                "data": {
                    "entities": entities_dict[doc_id],
                    "noun_phrases": noun_phrases_dict.get(doc_id, [])
                },
                "errors": None,
                "warnings": None
            })

        return {"values": combined_results}
    except Exception as e:
        logger.error(f"Error in extract_all: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/health", tags=["Health"])
async def health_check(request: Request):
    """Health check endpoint."""
    nlp = request.app.state.nlp
    try:
        # Test spaCy model
        nlp("Test document")
        return {"status": "healthy", "model": f"{nlp.meta['lang']}_{nlp.meta['name']}"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


app = create_app()
