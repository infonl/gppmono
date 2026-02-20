"""State machine for Publication and Document transitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from transitions import Machine

from gpp_api.db.models.publication import PublicationStatus
from gpp_api.utils.logging import get_logger

if TYPE_CHECKING:
    from gpp_api.db.models.publication import Document, Publication

logger = get_logger(__name__)


# State definitions
STATES = [
    PublicationStatus.CONCEPT.value,
    PublicationStatus.GEPUBLICEERD.value,
    PublicationStatus.INGETROKKEN.value,
]

# Transition definitions for Publication
PUBLICATION_TRANSITIONS = [
    {
        "trigger": "publish",
        "source": [PublicationStatus.CONCEPT.value, ""],
        "dest": PublicationStatus.GEPUBLICEERD.value,
        "before": "before_publish",
        "after": "after_publish",
    },
    {
        "trigger": "revoke",
        "source": PublicationStatus.GEPUBLICEERD.value,
        "dest": PublicationStatus.INGETROKKEN.value,
        "before": "before_revoke",
        "after": "after_revoke",
    },
]

# Transition definitions for Document
DOCUMENT_TRANSITIONS = [
    {
        "trigger": "publish",
        "source": [PublicationStatus.CONCEPT.value, ""],
        "dest": PublicationStatus.GEPUBLICEERD.value,
        "before": "before_publish",
        "after": "after_publish",
    },
    {
        "trigger": "revoke",
        "source": PublicationStatus.GEPUBLICEERD.value,
        "dest": PublicationStatus.INGETROKKEN.value,
        "before": "before_revoke",
        "after": "after_revoke",
    },
]


class PublicationStateMachine:
    """State machine wrapper for Publication transitions."""

    def __init__(self, publication: Publication) -> None:
        self.publication = publication
        self._tasks_to_enqueue: list[dict[str, Any]] = []

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=STATES,
            transitions=PUBLICATION_TRANSITIONS,
            initial=publication.publicatiestatus or PublicationStatus.CONCEPT.value,
            model_attribute="state",
            auto_transitions=False,
        )

    @property
    def state(self) -> str:
        """Get current state from publication."""
        return self.publication.publicatiestatus or PublicationStatus.CONCEPT.value

    @state.setter
    def state(self, value: str) -> None:
        """Set state on publication."""
        self.publication.publicatiestatus = value

    def before_publish(self) -> None:
        """Pre-publish validation."""
        if not self.publication.publisher_uuid:
            raise ValueError("Cannot publish without a publisher")
        logger.info(
            "publication_before_publish",
            uuid=str(self.publication.uuid),
        )

    def after_publish(self) -> None:
        """Post-publish actions."""
        now = datetime.now(timezone.utc)
        self.publication.gepubliceerd_op = now

        # Cascade publish to all documents
        for doc in self.publication.documenten:
            doc_sm = DocumentStateMachine(doc)
            if doc_sm.may_publish():
                doc_sm.publish()

        # Queue indexing task
        self._tasks_to_enqueue.append({
            "type": "index_publication",
            "payload": {"publication_uuid": str(self.publication.uuid)},
        })

        # Also queue indexing for all documents
        for doc in self.publication.documenten:
            if doc.upload_complete:
                self._tasks_to_enqueue.append({
                    "type": "index_document",
                    "payload": {"document_uuid": str(doc.uuid)},
                })

        logger.info(
            "publication_published",
            uuid=str(self.publication.uuid),
            gepubliceerd_op=now.isoformat(),
        )

    def before_revoke(self) -> None:
        """Pre-revoke validation."""
        logger.info(
            "publication_before_revoke",
            uuid=str(self.publication.uuid),
        )

    def after_revoke(self) -> None:
        """Post-revoke actions."""
        now = datetime.now(timezone.utc)
        self.publication.ingetrokken_op = now

        # Cascade revoke to all published documents
        for doc in self.publication.documenten:
            doc_sm = DocumentStateMachine(doc)
            if doc_sm.may_revoke():
                doc_sm.revoke()

        # Queue removal from index
        self._tasks_to_enqueue.append({
            "type": "remove_from_index",
            "payload": {
                "model": "publication",
                "uuid": str(self.publication.uuid),
            },
        })

        # Also remove all documents from index
        for doc in self.publication.documenten:
            self._tasks_to_enqueue.append({
                "type": "remove_from_index",
                "payload": {
                    "model": "document",
                    "uuid": str(doc.uuid),
                },
            })

        logger.info(
            "publication_revoked",
            uuid=str(self.publication.uuid),
            ingetrokken_op=now.isoformat(),
        )

    def get_pending_tasks(self) -> list[dict[str, Any]]:
        """Get tasks that should be enqueued after transition.

        Returns:
            List of task dicts with type and payload
        """
        tasks = self._tasks_to_enqueue.copy()
        self._tasks_to_enqueue.clear()
        return tasks


class DocumentStateMachine:
    """State machine wrapper for Document transitions."""

    def __init__(self, document: Document) -> None:
        self.document = document
        self._tasks_to_enqueue: list[dict[str, Any]] = []

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=STATES,
            transitions=DOCUMENT_TRANSITIONS,
            initial=document.publicatiestatus or PublicationStatus.CONCEPT.value,
            model_attribute="state",
            auto_transitions=False,
        )

    @property
    def state(self) -> str:
        """Get current state from document."""
        return self.document.publicatiestatus or PublicationStatus.CONCEPT.value

    @state.setter
    def state(self, value: str) -> None:
        """Set state on document."""
        self.document.publicatiestatus = value

    def before_publish(self) -> None:
        """Pre-publish validation."""
        logger.info(
            "document_before_publish",
            uuid=str(self.document.uuid),
        )

    def after_publish(self) -> None:
        """Post-publish actions."""
        now = datetime.now(timezone.utc)
        self.document.gepubliceerd_op = now

        # Queue indexing if upload is complete
        if self.document.upload_complete:
            self._tasks_to_enqueue.append({
                "type": "index_document",
                "payload": {"document_uuid": str(self.document.uuid)},
            })

        logger.info(
            "document_published",
            uuid=str(self.document.uuid),
            gepubliceerd_op=now.isoformat(),
        )

    def before_revoke(self) -> None:
        """Pre-revoke validation."""
        logger.info(
            "document_before_revoke",
            uuid=str(self.document.uuid),
        )

    def after_revoke(self) -> None:
        """Post-revoke actions."""
        now = datetime.now(timezone.utc)
        self.document.ingetrokken_op = now

        # Queue removal from index
        self._tasks_to_enqueue.append({
            "type": "remove_from_index",
            "payload": {
                "model": "document",
                "uuid": str(self.document.uuid),
            },
        })

        logger.info(
            "document_revoked",
            uuid=str(self.document.uuid),
            ingetrokken_op=now.isoformat(),
        )

    def get_pending_tasks(self) -> list[dict[str, Any]]:
        """Get tasks that should be enqueued after transition.

        Returns:
            List of task dicts with type and payload
        """
        tasks = self._tasks_to_enqueue.copy()
        self._tasks_to_enqueue.clear()
        return tasks
