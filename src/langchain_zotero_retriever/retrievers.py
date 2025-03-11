"""Zotero retriever"""

from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import Literal
from re import search
from os import environ



class ZoteroRetriever(BaseRetriever):
    """Zotero retriever.

    Setup:
        Install ``pyzotero`` and set environment variable ``ZOTERO_API_KEY``.

        .. code-block:: bash

            pip install -U pyzotero 
            export ZOTERO_API_KEY="your-api-key"

    Key init args:
        k: int
            Number of results to include.
        type: Literal["top", "items"] = "top"
            Type of search to perform. "Top" retrieves top level Zotero library items, "items" returns any Zotero library items.
        get_fulltext: bool = True 
            Retrieves full texts if they are attached to the items in the library. If False, or no text is attached, returns an empty string as page_content.
        library_id: str
            ID of the Zotero library to search.
        library_type: Literal["user", "group"] = "user"
            Type of library to search. "user" for personal library, "group" for shared group libraries.
        api_key: Optional[str] = None
            Zotero API key if not set as an environment variable.

    Additional search parameters:
        itemType: str
            Type of item to search for.
        tag: str
            Tag search. See the Search Syntax for details. More than one tag may be passed by passing a list of strings or a single string with operators. Note that passing a list treats these as AND search terms.
        qmode: Literal["everything", "titleCreatorYear"] = "everything"
            Search mode to use. Changes what the query searches over. "everything" includes full-text content. "titleCreatorYear" to search over title, authors and year.
        since: str
            default 0. Return only objects modified after the specified library version

    Search Syntax:
        See Zotero API Documentation: https://www.zotero.org/support/dev/web_api/v3/basics#search_syntax

    Instantiate:
        .. code-block:: python

            from ... import ZoteroRetriever #TODO: Replace with relevant package.

            retriever = ZoteroRetriever(
                k = 50,
                library_id = "your-library-id",
            )

    Usage:
        .. code-block:: python

            retriever.invoke("Author_name", qmode="titleCreatorYear", tags="tag1 || tag2", k = 20)

    Use within a chain:
        .. code-block:: python

            #TODO: add chain example, including prompt template

    """

    k: int = 50
    type: Literal["top", "items"] = "top" # potentially add other types - but use cases may be very limited
    get_fulltext: bool = False # retrieves full texts if attached to the items in the library. If False, or no full text is attached, returns an empty string as page_content
    library_id: str
    library_type: Literal["user", "group"] = "user"
    api_key: Optional[str] = None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun, **kwargs: Any
    ) -> List[Document]:
        try:
            from pyzotero import zotero
        except ImportError:
            raise ImportError(
                "Pyzotero python package not found. "
                "Please install it with `pip install pyzotero`."
            )
        
        zot = zotero.Zotero(library_id=self.library_id, 
                            library_type=self.library_type, 
                            api_key=self.api_key or environ.get("ZOTERO_API_KEY", None))

        args = {
            "q": query,
            "itemType": kwargs.get("itemType", ""),
            "tag": kwargs.get("tag", ""),
            "qmode": kwargs.get("qmode", "everything"),
            "since": kwargs.get("since", ""),
            "limit": kwargs.get("k", self.k),
        }

        if self.type == "top":
            results = zot.top(**args)
        elif self.type == "items":
            results = zot.items(**args)
        else:
            raise ValueError("Invalid type. Must be 'top' or 'item'.")
        
        if self.get_fulltext:
            
            for entry in results:

                try:
                    attachment_link = entry.get("links", "").get("attachment", "").get("href", "")
                    attachment = search(r"items/([^/]+)", attachment_link).group(1) if search(r"items/([^/]+)", attachment_link) else None
                    full_text = zot.fulltext_item(attachment).get("content", "")
                except:
                    full_text = ""
                    
                entry["text"] = full_text
        
        else:
            for entry in results:
                entry["text"] = ""

        return self._format_results(results)
    

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun, **kwargs: Any
    ) -> List[Document]:
        try:
            from pyzotero import zotero
        except ImportError:
            raise ImportError(
                "Pyzotero python package not found. "
                "Please install it with `pip install pyzotero`."
            )
        
        zot = zotero.Zotero(library_id=self.library_id, 
                            library_type=self.library_type, 
                            api_key=self.api_key or environ.get("ZOTERO_API_KEY", None))

        args = {
            "q": query,
            "itemType": kwargs.get("itemType", ""),
            "tag": kwargs.get("tag", ""),
            "qmode": kwargs.get("qmode", "everything"),
            "since": kwargs.get("since", ""),
            "limit": kwargs.get("k", self.k),
        }

        if self.type == "top":
            results = await zot.top(**args)
        elif self.type == "items":
            results = await zot.items(**args)
        else:
            raise ValueError("Invalid type. Must be 'top' or 'item'.")
        
        if self.get_fulltext:
            
            for entry in results:

                try:
                    attachment_link = entry.get("links", "").get("attachment", "").get("href", "")
                    attachment = search(r"items/([^/]+)", attachment_link).group(1) if search(r"items/([^/]+)", attachment_link) else None
                    full_text = await zot.fulltext_item(attachment).get("content", "")
                except:
                    full_text = ""
                    
                entry["text"] = full_text
        
        else:
            for entry in results:
                entry["text"] = ""
        
        return self._format_results(results)
    

    def _format_results(
            self, results: List[dict]
            ) -> List[Document]:
        docs = [
                Document(
                    page_content = entry.get("text"),
                    metadata={
                        **{
                            "key": entry.get("key", ""), # unique identifier for the document
                            "abstractNote": entry.get("data").get("abstractNote", ""),
                            "itemType": entry.get("data").get("itemType", ""),
                            "tags": ", ".join(f"{tag.get('tag', '')}" for tag in entry.get("data", {}).get("tags", [])),
                        },
                        **(  
                            {
                                "authors": ", ".join(f"{creator.get('firstName', '')} {creator.get('lastName', '')}" for creator in entry.get("data", {}).get("creators", [])),
                            }
                            if any("firstName" in creator for creator in entry.get("data", "").get("creators", "")) or 
                            any("lastName" in creator for creator in entry.get("data", "").get("creators", "")) else
                            # note that the additional "name" passed here is in case the name is not split into first and last name
                            {
                                "authors": ", ".join(f"{creator.get('name', '')}" for creator in entry.get("data", {}).get("creators", [])),
                            }
                        ),
                        **(
                            {
                                "title": entry.get("data").get("caseName", ""),
                                "court": entry.get("data").get("court", ""),
                                "date": entry.get("data").get("dateDecided", ""),
                                "publication": entry.get("data").get("reporter", ""),
                                "volume": entry.get("data").get("reporterVolume", ""),
                                "pages": entry.get("data").get("firstPage", ""),
                            } # extra scheme for case law. Potentially add more schemes later, but the standard below should be sufficient for most documents
                            if entry.get("data", {}).get("itemType", "") == "case" else
                            {
                                "title": entry.get("data").get("title", ""),
                                "publication": entry.get("data").get("publicationTitle", ""),
                                "volume": entry.get("data").get("volume", ""),
                                "issue": entry.get("data").get("issue", ""),
                                "pages": entry.get("data").get("pages", ""),
                                "date": entry.get("data").get("date", ""),
                                "DOI": entry.get("data").get("DOI", ""),
                            }
                        ),
                        **(
                            {
                                "attachment_link": entry.get("links", "").get("attachment", "").get("href", ""),
                            }
                            if "attachment" in entry.get("links") else {}
                            
                        )
                        
                    }
                )
                for entry in results
            ]
        
        return docs

