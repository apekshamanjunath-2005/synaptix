"""
Firestore Tools Adapter & Re-export
Exposes firestore_service and FirestoreService under app.tools.firestore.
"""

from app.database.firestore import firestore_service, FirestoreService

__all__ = ["firestore_service", "FirestoreService"]
