# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from collections import defaultdict
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
import spacy
from spacy.language import Language

from app.models import (
    ENT_PROP_MAP,
    CombinedData,
    EntitiesByTypeData,
    EntitiesData,
    NounPhrasesData,
    RecordsRequest,
    RecordsResponse,
)
from app.skill import run_skill
from app.spacy_extractor import SpacyExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "en_core_web_sm"

EXAMPLE_REQUEST = json.loads((Path(__file__).parent / "data" / "example_request.json").read_text())

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


def analyze_with(extractor: SpacyExtractor) -> Callable[[List[str]], List[Dict[str, Any]]]:
    """Each text's entities and noun phrases from one pass, in input order."""

    def analyze(texts: List[str]) -> List[Dict[str, Any]]:
        documents = [{"id": str(index), "text": text} for index, text in enumerate(texts)]
        results = extractor.extract_entities_and_noun_phrases(documents)
        return [
            {"entities": entities["entities"], "noun_phrases": phrases["noun_phrases"]}
            for entities, phrases in zip(results["entities"], results["noun_phrases"])
        ]

    return analyze


def answer(body: RecordsRequest, extractor: SpacyExtractor, to_data: Callable[[Dict[str, Any]], Dict[str, Any]]):
    return run_skill(body.values, analyze_with(extractor), to_data, model_language=extractor.nlp.lang)


def entities_by_type(analysis: Dict[str, Any]) -> EntitiesByTypeData:
    groups = defaultdict(list)
    for entity in analysis["entities"]:
        groups[ENT_PROP_MAP.get(entity["label"], entity["label"].lower())].append(entity["name"])
    return dict(groups)


# Handlers are plain functions: FastAPI runs them in its thread pool, so spaCy's CPU work doesn't
# block the event loop the way it did inside async handlers.
EXAMPLE_BODY = Body(..., examples=[EXAMPLE_REQUEST])


@router.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse("/docs")


@router.post("/entities", response_model=RecordsResponse[EntitiesData], tags=["NER"])
def extract_entities(body: RecordsRequest = EXAMPLE_BODY, extractor: SpacyExtractor = Depends(get_extractor)):
    """Extract Named Entities from a batch of Records."""
    return answer(body, extractor, lambda analysis: {"entities": analysis["entities"]})


@router.post("/entities_by_type", response_model=RecordsResponse[EntitiesByTypeData], tags=["NER"])
def extract_entities_by_type(body: RecordsRequest = EXAMPLE_BODY, extractor: SpacyExtractor = Depends(get_extractor)):
    """Extract Named Entities from a batch of Records separated by entity label.
        This route can be used directly as a Cognitive Skill in Azure Search
        For Documentation on integration with Azure Search, see here:
        https://docs.microsoft.com/en-us/azure/search/cognitive-search-custom-skill-interface"""
    return answer(body, extractor, entities_by_type)


@router.post("/noun_phrases", response_model=RecordsResponse[NounPhrasesData], tags=["Syntax"])
def extract_noun_phrases(body: RecordsRequest = EXAMPLE_BODY, extractor: SpacyExtractor = Depends(get_extractor)):
    """Extract Noun Phrases from a batch of Records."""
    return answer(body, extractor, lambda analysis: {"noun_phrases": analysis["noun_phrases"]})


@router.post("/extract_all", response_model=RecordsResponse[CombinedData], tags=["Combined"])
def extract_all(body: RecordsRequest = EXAMPLE_BODY, extractor: SpacyExtractor = Depends(get_extractor)):
    """Extract both entities and noun phrases from a batch of Records in a single pass."""
    return answer(body, extractor, lambda analysis: analysis)


@router.get("/health", tags=["Health"])
def health_check(request: Request):
    """Health check endpoint."""
    nlp = request.app.state.nlp
    try:
        nlp("Test document")
        return {"status": "healthy", "model": f"{nlp.meta['lang']}_{nlp.meta['name']}"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


app = create_app()
