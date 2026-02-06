"""Tests for publication state machine."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from gpp_api.db.models import Publication, Document, PublicationStatus
from gpp_api.services.state_machine import PublicationStateMachine, DocumentStateMachine


class TestPublicationStateMachine:
    """Tests for publication state transitions."""

    @pytest.fixture
    def mock_publication(self):
        """Create a mock publication with all required attributes."""
        pub = MagicMock(spec=Publication)
        pub.uuid = "test-uuid"
        pub.publicatiestatus = PublicationStatus.CONCEPT.value
        pub.gepubliceerd_op = None
        pub.ingetrokken_op = None
        pub.publisher_uuid = "publisher-uuid"  # Required for publish validation
        pub.documenten = []  # State machine uses 'documenten' not 'documents'
        return pub

    def test_initial_state_is_concept(self, mock_publication):
        """New publications start in concept state."""
        machine = PublicationStateMachine(mock_publication)

        assert machine.state == PublicationStatus.CONCEPT.value

    def test_can_publish_from_concept(self, mock_publication):
        """Can transition from concept to gepubliceerd."""
        machine = PublicationStateMachine(mock_publication)

        result = machine.publish()

        assert result is True
        assert machine.state == PublicationStatus.GEPUBLICEERD.value
        assert mock_publication.gepubliceerd_op is not None

    def test_cannot_publish_when_already_published(self, mock_publication):
        """Cannot publish when already gepubliceerd."""
        mock_publication.publicatiestatus = PublicationStatus.GEPUBLICEERD.value
        machine = PublicationStateMachine(mock_publication)

        result = machine.may_publish()

        assert result is False

    def test_can_revoke_from_published(self, mock_publication):
        """Can transition from gepubliceerd to ingetrokken."""
        mock_publication.publicatiestatus = PublicationStatus.GEPUBLICEERD.value
        machine = PublicationStateMachine(mock_publication)

        result = machine.revoke()

        assert result is True
        assert machine.state == PublicationStatus.INGETROKKEN.value
        assert mock_publication.ingetrokken_op is not None

    def test_cannot_revoke_from_concept(self, mock_publication):
        """Cannot revoke from concept state."""
        machine = PublicationStateMachine(mock_publication)

        result = machine.may_revoke()

        assert result is False

    def test_cannot_revoke_when_already_revoked(self, mock_publication):
        """Cannot revoke when already ingetrokken."""
        mock_publication.publicatiestatus = PublicationStatus.INGETROKKEN.value
        machine = PublicationStateMachine(mock_publication)

        result = machine.may_revoke()

        assert result is False

    def test_publish_cascades_to_documents(self, mock_publication):
        """Publishing also publishes all documents."""
        mock_doc1 = MagicMock(spec=Document)
        mock_doc1.publicatiestatus = PublicationStatus.CONCEPT.value
        mock_doc1.upload_complete = True
        mock_doc1.uuid = "doc-1-uuid"
        mock_doc2 = MagicMock(spec=Document)
        mock_doc2.publicatiestatus = PublicationStatus.CONCEPT.value
        mock_doc2.upload_complete = True
        mock_doc2.uuid = "doc-2-uuid"
        mock_publication.documenten = [mock_doc1, mock_doc2]

        machine = PublicationStateMachine(mock_publication)
        machine.publish()

        assert mock_doc1.publicatiestatus == PublicationStatus.GEPUBLICEERD.value
        assert mock_doc2.publicatiestatus == PublicationStatus.GEPUBLICEERD.value


class TestDocumentStateMachine:
    """Tests for document state transitions."""

    @pytest.fixture
    def mock_document(self):
        """Create a mock document."""
        doc = MagicMock(spec=Document)
        doc.publicatiestatus = PublicationStatus.CONCEPT.value
        return doc

    def test_initial_state_is_concept(self, mock_document):
        """New documents start in concept state."""
        machine = DocumentStateMachine(mock_document)

        assert machine.state == PublicationStatus.CONCEPT.value

    def test_can_publish_from_concept(self, mock_document):
        """Can transition from concept to gepubliceerd."""
        machine = DocumentStateMachine(mock_document)

        result = machine.publish()

        assert result is True
        assert machine.state == PublicationStatus.GEPUBLICEERD.value

    def test_can_revoke_from_published(self, mock_document):
        """Can transition from gepubliceerd to ingetrokken."""
        mock_document.publicatiestatus = PublicationStatus.GEPUBLICEERD.value
        machine = DocumentStateMachine(mock_document)

        result = machine.revoke()

        assert result is True
        assert machine.state == PublicationStatus.INGETROKKEN.value
