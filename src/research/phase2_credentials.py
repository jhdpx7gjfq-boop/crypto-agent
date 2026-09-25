"""Phase 2 credential management and validation."""

import os
import logging
from typing import Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CredentialStatus(Enum):
    """Credential validation status."""
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"


class Phase2CredentialManager:
    """Manage Phase 2 API credentials (CryptoQuant, Glassnode)."""

    REQUIRED_KEYS = {
        "CRYPTOQUANT_API_KEY": "CryptoQuant",
        "GLASSNODE_API_KEY": "Glassnode",
    }

    def __init__(self):
        self.credentials: Dict[str, str] = {}
        self.status: Dict[str, CredentialStatus] = {}
        self._load_credentials()
        self._validate_all()

    def _load_credentials(self) -> None:
        """Load credentials from environment variables."""
        for env_key, service_name in self.REQUIRED_KEYS.items():
            value = os.getenv(env_key, "").strip()
            if value:
                self.credentials[env_key] = value
                logger.info(f"Loaded {service_name} credential from environment")
            else:
                logger.warning(f"Missing {service_name} credential: {env_key}")

    def _validate_all(self) -> None:
        """Validate all credentials."""
        for env_key, service_name in self.REQUIRED_KEYS.items():
            self.status[env_key] = self._validate_credential(env_key)

    def _validate_credential(self, env_key: str) -> CredentialStatus:
        """Validate a single credential."""
        if env_key not in self.credentials:
            return CredentialStatus.MISSING

        value = self.credentials[env_key]

        # Basic validation: non-empty string, reasonable length
        if not value or len(value) < 10:
            logger.error(f"Invalid credential format: {env_key}")
            return CredentialStatus.INVALID

        return CredentialStatus.VALID

    def get(self, env_key: str) -> str:
        """Get credential value."""
        return self.credentials.get(env_key, "")

    def is_available(self, env_key: str) -> bool:
        """Check if credential is available and valid."""
        return self.status.get(env_key) == CredentialStatus.VALID

    def all_available(self) -> bool:
        """Check if all required credentials are available."""
        return all(
            self.status.get(key) == CredentialStatus.VALID
            for key in self.REQUIRED_KEYS.keys()
        )

    def missing_credentials(self) -> Dict[str, str]:
        """Return map of missing/invalid credentials."""
        missing = {}
        for env_key, service_name in self.REQUIRED_KEYS.items():
            if not self.is_available(env_key):
                missing[env_key] = service_name
        return missing

    def report(self) -> str:
        """Generate credential status report."""
        lines = [
            "\n" + "="*70,
            "PHASE 2 CREDENTIAL STATUS",
            "="*70,
        ]

        for env_key, service_name in self.REQUIRED_KEYS.items():
            status = self.status.get(env_key, CredentialStatus.MISSING)
            symbol = "✓" if status == CredentialStatus.VALID else "✗"
            lines.append(f"  {symbol} {service_name:.<40} {status.value}")

        lines.extend([
            "="*70,
            f"\nOverall Status: {'READY ✓' if self.all_available() else 'BLOCKED (missing credentials)'}",
            "",
        ])

        if not self.all_available():
            missing = self.missing_credentials()
            lines.extend([
                "Next Steps:",
                "-" * 70,
            ])
            for env_key, service_name in missing.items():
                if service_name == "CryptoQuant":
                    lines.append("  1. Visit: https://www.cryptoquant.com")
                    lines.append("     Request API key for liquidation events")
                    lines.append("     Set: export CRYPTOQUANT_API_KEY=<your_key>")
                else:
                    lines.append("  2. Visit: https://glassnode.com")
                    lines.append("     Request API key for exchange flows")
                    lines.append("     Set: export GLASSNODE_API_KEY=<your_key>")

        lines.append("="*70 + "\n")
        return "\n".join(lines)


def load_phase2_credentials() -> Tuple[str, str, bool]:
    """
    Load Phase 2 credentials from environment.

    Returns:
        (cryptoquant_key, glassnode_key, all_available)
    """
    manager = Phase2CredentialManager()
    cq_key = manager.get("CRYPTOQUANT_API_KEY")
    gn_key = manager.get("GLASSNODE_API_KEY")
    return cq_key, gn_key, manager.all_available()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = Phase2CredentialManager()
    print(manager.report())
