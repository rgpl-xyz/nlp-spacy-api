# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


ENT_PROP_MAP = {
    "CARDINAL": "cardinals",
    "DATE": "dates",
    "EVENT": "events",
    "FAC": "facilities",
    "GPE": "gpes",
    "LANGUAGE": "languages",
    "LAW": "laws",
    "LOC": "locations",
    "MONEY": "money",
    "NORP": "norps",
    "ORDINAL": "ordinals",
    "ORG": "organizations",
    "PERCENT": "percentages",
    "PERSON": "people",
    "PRODUCT": "products",
    "QUANTITY": "quantities",
    "TIME": "times",
    "WORK_OF_ART": "worksOfArt",
}


class RecordDataRequest(BaseModel):
    text: str
    language: str = "en"


class RecordRequest(BaseModel):
    recordId: str
    data: RecordDataRequest


class RecordsRequest(BaseModel):
    values: List[RecordRequest]


class RecordDataResponse(BaseModel):
    entities: List[Dict[str, Any]]


class RecordDataNounPhrasesResponse(BaseModel):
    noun_phrases: List[str]


class RecordDataCombinedResponse(BaseModel):
    entities: List[Dict[str, Any]]
    noun_phrases: List[str]


class Message(BaseModel):
    message: str


class RecordResponse(BaseModel):
    recordId: str
    data: RecordDataResponse
    errors: Optional[List[Message]] = None
    warnings: Optional[List[Message]] = None


class RecordNounPhrasesResponse(BaseModel):
    recordId: str
    data: RecordDataNounPhrasesResponse
    errors: Optional[List[Message]] = None
    warnings: Optional[List[Message]] = None


class RecordCombinedResponse(BaseModel):
    recordId: str
    data: RecordDataCombinedResponse
    errors: Optional[List[Message]] = None
    warnings: Optional[List[Message]] = None


class RecordsResponse(BaseModel):
    values: List[RecordResponse]


class RecordsNounPhrasesResponse(BaseModel):
    values: List[RecordNounPhrasesResponse]


class RecordsCombinedResponse(BaseModel):
    values: List[RecordCombinedResponse]


class RecordEntitiesByTypeResponse(BaseModel):
    recordId: str
    data: Dict[str, List[str]]


class RecordsEntitiesByTypeResponse(BaseModel):
    values: List[RecordEntitiesByTypeResponse]
