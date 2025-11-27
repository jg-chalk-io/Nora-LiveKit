"""Pet breed corpus loader and search functionality.

Loads the pets corpus JSON and provides fuzzy search capabilities
for breed identification from voice input.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Global corpus instance
_corpus: Optional["PetsCorpus"] = None


@dataclass
class PetMatch:
    """Result from a corpus search."""

    found: bool
    species: Optional[str] = None
    breed: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    match_type: Optional[str] = None  # "exact_breed", "common_name", "partial"

    def to_dict(self) -> dict:
        """Convert to dictionary for tool response."""
        if not self.found:
            return {"found": False}
        return {
            "found": True,
            "species": self.species,
            "breed": self.breed,
            "category": self.category,
            "size": self.size,
            "match_type": self.match_type,
        }


class PetsCorpus:
    """Pet breed corpus with search functionality."""

    def __init__(self, corpus_path: Optional[Path] = None):
        """Initialize corpus from JSON file.

        Args:
            corpus_path: Path to pets_corpus.json. Defaults to bundled corpus.
        """
        if corpus_path is None:
            corpus_path = Path(__file__).parent / "pets_corpus.json"

        self._pets: list[dict] = []
        self._breed_index: dict[str, dict] = {}  # lowercase breed -> pet data
        self._common_name_index: dict[str, dict] = {}  # lowercase common name -> pet data
        self._species_index: dict[str, list[dict]] = {}  # species -> list of pets

        self._load_corpus(corpus_path)
        self._build_indices()

    def _load_corpus(self, path: Path) -> None:
        """Load corpus from JSON file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self._pets = data.get("pets", [])
                logger.info(
                    "pets_corpus.loaded",
                    total_entries=len(self._pets),
                    path=str(path),
                )
        except Exception as e:
            logger.error("pets_corpus.load_failed", error=str(e), path=str(path))
            self._pets = []

    def _build_indices(self) -> None:
        """Build search indices for fast lookup."""
        for pet in self._pets:
            breed = pet.get("breed", "").lower()
            species = pet.get("species", "").lower()

            # Index by breed name
            if breed:
                self._breed_index[breed] = pet

            # Index by common names
            for common_name in pet.get("commonNames", []):
                if common_name:
                    self._common_name_index[common_name.lower()] = pet

            # Index by species
            if species not in self._species_index:
                self._species_index[species] = []
            self._species_index[species].append(pet)

        logger.debug(
            "pets_corpus.indices_built",
            breeds=len(self._breed_index),
            common_names=len(self._common_name_index),
            species=len(self._species_index),
        )

    def search(self, query: str) -> PetMatch:
        """Search for a pet breed by name.

        Searches in order:
        1. Exact breed match (case-insensitive)
        2. Exact common name match (case-insensitive)
        3. Partial breed match (contains)
        4. Partial common name match (contains)

        Args:
            query: Breed name or nickname (e.g., "Yorkie", "Lab", "Golden Retriever")

        Returns:
            PetMatch with breed info if found, otherwise found=False
        """
        if not query:
            return PetMatch(found=False)

        query_lower = query.lower().strip()

        # 1. Exact breed match
        if query_lower in self._breed_index:
            pet = self._breed_index[query_lower]
            return PetMatch(
                found=True,
                species=pet.get("species"),
                breed=pet.get("breed"),
                category=pet.get("category"),
                size=pet.get("size"),
                match_type="exact_breed",
            )

        # 2. Exact common name match
        if query_lower in self._common_name_index:
            pet = self._common_name_index[query_lower]
            return PetMatch(
                found=True,
                species=pet.get("species"),
                breed=pet.get("breed"),
                category=pet.get("category"),
                size=pet.get("size"),
                match_type="common_name",
            )

        # 3. Partial breed match (query is contained in breed name)
        for breed_key, pet in self._breed_index.items():
            if query_lower in breed_key or breed_key in query_lower:
                return PetMatch(
                    found=True,
                    species=pet.get("species"),
                    breed=pet.get("breed"),
                    category=pet.get("category"),
                    size=pet.get("size"),
                    match_type="partial",
                )

        # 4. Partial common name match
        for common_name, pet in self._common_name_index.items():
            if query_lower in common_name or common_name in query_lower:
                return PetMatch(
                    found=True,
                    species=pet.get("species"),
                    breed=pet.get("breed"),
                    category=pet.get("category"),
                    size=pet.get("size"),
                    match_type="partial",
                )

        # Not found
        logger.debug("pets_corpus.no_match", query=query)
        return PetMatch(found=False)

    def get_species_breeds(self, species: str) -> list[str]:
        """Get all breeds for a species.

        Args:
            species: Species name (e.g., "Dog", "Cat")

        Returns:
            List of breed names
        """
        species_lower = species.lower()
        pets = self._species_index.get(species_lower, [])
        return [p.get("breed", "") for p in pets]

    @property
    def total_entries(self) -> int:
        """Total number of pets in corpus."""
        return len(self._pets)


def get_pets_corpus() -> PetsCorpus:
    """Get or create the global pets corpus instance.

    Returns:
        PetsCorpus singleton instance
    """
    global _corpus
    if _corpus is None:
        _corpus = PetsCorpus()
    return _corpus


def reset_pets_corpus() -> None:
    """Reset the global pets corpus (for testing)."""
    global _corpus
    _corpus = None
