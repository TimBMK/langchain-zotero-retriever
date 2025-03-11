from typing import Type

from langchain_zotero_retriever.retrievers import ZoteroRetriever
from langchain_tests.integration_tests import (
    RetrieversIntegrationTests,
)


class TestZoteroRetriever(RetrieversIntegrationTests):
    @property
    def retriever_constructor(self) -> Type[ZoteroRetriever]:
        """Construct a test retriever"""
        return ZoteroRetriever

    @property
    def retriever_constructor_params(self) -> dict:
        return {"k": 5, 
                "library_id": "2319375",
                "library_type": "group",}

    @property
    def retriever_query_example(self) -> str:
        """
        Returns a str representing the "query" of an example retriever call.
        """
        return "Data"