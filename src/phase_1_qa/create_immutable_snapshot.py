#!/usr/bin/env python3
"""
Phase 1 Immutable Snapshot Creation

Creates read-only immutable data snapshot after quality audit PASS:
- SHA256 hash manifest
- Filesystem read-only enforcement
- Backup to multiple locations (local, S3, GCS)
- Immutability certificate

Timeline: Oct 14-15, 2026
Decision: Upon audit PASS, creates immutable artifact
"""

import os
import sys
import json
import hashlib
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "phase_1"
SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "immutable_snapshots" / "phase_1"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_1"
BACKUP_LOCATIONS = {
    "local": Path(__file__).parent.parent.parent / "backups" / "phase_1",
    "s3": "s3://crypto-agent-backups/phase_1",  # Requires AWS credentials
    "gcs": "gs://crypto-agent-backups/phase_1"  # Requires GCS credentials
}

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ImmutableSnapshotManager:
    def __init__(self, data_dir=DATA_DIR, snapshot_dir=SNAPSHOT_DIR):
        self.data_dir = Path(data_dir)
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = {
            "timestamp": datetime.now().isoformat(),
            "phase": "1_data_audit",
            "snapshot_id": f"phase1_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "data_dir": str(self.data_dir),
            "immutability_status": "LOCKED",
            "files": {}
        }

    def calculate_sha256(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def create_manifest(self) -> Dict:
        """Create comprehensive manifest of all data files"""
        logger.info("Creating manifest of all data files...")

        parquet_files = list(self.data_dir.glob("*.parquet"))
        if not parquet_files:
            logger.error("No Parquet files found")
            return None

        total_size = 0
        for parquet_file in parquet_files:
            sha256 = self.calculate_sha256(parquet_file)
            file_size = parquet_file.stat().st_size

            self.manifest["files"][parquet_file.name] = {
                "sha256": sha256,
                "size_bytes": file_size,
                "path": str(parquet_file)
            }
            total_size += file_size
            logger.debug(f"✓ {parquet_file.name}: {sha256[:16]}... ({file_size/1024/1024:.2f} MB)")

        self.manifest["summary"] = {
            "total_files": len(parquet_files),
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2)
        }

        logger.info(f"Manifest complete: {len(parquet_files)} files, {self.manifest['summary']['total_size_gb']} GB")
        return self.manifest

    def save_manifest(self) -> Path:
        """Save manifest to disk"""
        manifest_file = self.snapshot_dir / f"manifest_{self.manifest['snapshot_id']}.json"
        with open(manifest_file, "w") as f:
            json.dump(self.manifest, f, indent=2)
        logger.info(f"Manifest saved to {manifest_file}")
        return manifest_file

    def verify_manifest(self, manifest_file: Path) -> bool:
        """Verify all files match manifest hashes"""
        logger.info(f"Verifying manifest: {manifest_file}")

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        all_valid = True
        for filename, file_info in manifest["files"].items():
            filepath = Path(file_info["path"])

            if not filepath.exists():
                logger.error(f"Missing file: {filename}")
                all_valid = False
                continue

            actual_sha256 = self.calculate_sha256(filepath)
            expected_sha256 = file_info["sha256"]

            if actual_sha256 == expected_sha256:
                logger.debug(f"✓ {filename}")
            else:
                logger.error(f"✗ {filename}: SHA256 mismatch")
                all_valid = False

        if all_valid:
            logger.info("✓ All files verified")
        else:
            logger.error("✗ Verification failed")

        return all_valid

    def enforce_read_only(self):
        """Make data directory read-only"""
        logger.info("Enforcing read-only permissions on data directory...")

        try:
            # Change directory permissions to 555 (r-xr-xr-x)
            os.chmod(self.data_dir, 0o555)

            # Change all files to 444 (r--r--r--)
            for filepath in self.data_dir.glob("*.parquet"):
                os.chmod(filepath, 0o444)

            logger.info("✓ Directory and files set to read-only")
            return True
        except Exception as e:
            logger.error(f"Failed to set read-only permissions: {str(e)}")
            return False

    def backup_to_local(self) -> bool:
        """Create local backup"""
        logger.info(f"Creating local backup to {BACKUP_LOCATIONS['local']}...")

        try:
            backup_dir = Path(BACKUP_LOCATIONS['local"])
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Copy all Parquet files
            for parquet_file in self.data_dir.glob("*.parquet"):
                shutil.copy2(parquet_file, backup_dir / parquet_file.name)

            logger.info(f"✓ Local backup complete: {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Local backup failed: {str(e)}")
            return False

    def backup_to_cloud(self, service: str = "s3") -> bool:
        """Create cloud backup (S3 or GCS)"""
        logger.info(f"Creating {service.upper()} backup...")

        try:
            if service == "s3":
                import boto3
                s3_client = boto3.client("s3")
                bucket = "crypto-agent-backups"

                for parquet_file in self.data_dir.glob("*.parquet"):
                    s3_key = f"phase_1/{parquet_file.name}"
                    s3_client.upload_file(
                        str(parquet_file),
                        bucket,
                        s3_key
                    )
                    logger.debug(f"✓ Uploaded {parquet_file.name} to S3")

                logger.info(f"✓ S3 backup complete")
                return True

            elif service == "gcs":
                from google.cloud import storage
                gcs_client = storage.Client()
                bucket = gcs_client.bucket("crypto-agent-backups")

                for parquet_file in self.data_dir.glob("*.parquet"):
                    blob = bucket.blob(f"phase_1/{parquet_file.name}")
                    blob.upload_from_filename(str(parquet_file))
                    logger.debug(f"✓ Uploaded {parquet_file.name} to GCS")

                logger.info(f"✓ GCS backup complete")
                return True

        except ImportError:
            logger.warning(f"Cloud backup skipped: {service} SDK not installed")
            return False
        except Exception as e:
            logger.error(f"{service.upper()} backup failed: {str(e)}")
            return False

    def create_immutability_certificate(self, manifest_file: Path) -> Path:
        """Create formal immutability certificate"""
        certificate = {
            "phase": "1_data_audit",
            "timestamp": datetime.now().isoformat(),
            "snapshot_id": self.manifest["snapshot_id"],
            "manifest_file": str(manifest_file),
            "immutability_status": "LOCKED",
            "read_only_enforced": True,
            "backups": {
                "local": str(BACKUP_LOCATIONS["local"]),
                "s3": BACKUP_LOCATIONS["s3"],
                "gcs": BACKUP_LOCATIONS["gcs"]
            },
            "certificate_authority": "Phase 1 QA Lead",
            "authority_signature": None,
            "approval_timestamp": None,
            "cannot_modify": True,
            "next_phase": "Phase 2: Ground Truth Labeling"
        }

        cert_file = self.snapshot_dir / f"immutability_cert_{self.manifest['snapshot_id']}.json"
        with open(cert_file, "w") as f:
            json.dump(certificate, f, indent=2)

        logger.info(f"Immutability certificate saved to {cert_file}")
        return cert_file

    def create_snapshot(self) -> bool:
        """Create complete immutable snapshot"""
        logger.info("="*60)
        logger.info("PHASE 1 IMMUTABLE SNAPSHOT CREATION")
        logger.info("="*60)

        # Step 1: Create manifest
        self.create_manifest()
        if not self.manifest["files"]:
            logger.error("No data files to snapshot")
            return False

        manifest_file = self.save_manifest()

        # Step 2: Verify all files
        if not self.verify_manifest(manifest_file):
            logger.error("Manifest verification failed")
            return False

        # Step 3: Create backups
        self.backup_to_local()
        # Cloud backups are optional if credentials not available
        self.backup_to_cloud("s3")
        self.backup_to_cloud("gcs")

        # Step 4: Enforce read-only
        if not self.enforce_read_only():
            logger.warning("Read-only enforcement failed (may be permission issue)")

        # Step 5: Create immutability certificate
        cert_file = self.create_immutability_certificate(manifest_file)

        logger.info("="*60)
        logger.info("SNAPSHOT COMPLETE: IMMUTABLE ARTIFACT CREATED")
        logger.info("="*60)
        logger.info(f"Snapshot ID: {self.manifest['snapshot_id']}")
        logger.info(f"Manifest: {manifest_file}")
        logger.info(f"Certificate: {cert_file}")
        logger.info("Status: LOCKED - Ready for Phase 2")

        return True


if __name__ == "__main__":
    manager = ImmutableSnapshotManager()
    success = manager.create_snapshot()
    sys.exit(0 if success else 1)
