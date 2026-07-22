# Production Integration Guide

This document describes exactly what a production deployment must wire
to move from pilot-ready to production-ready. Each section names the
abstraction interface, the current pilot implementation, and the
production integration path.

## 1. Signing: KMS / HSM

### Current state
- **Algorithm**: Ed25519 (EdDSA) — real asymmetric signing
- **Backend**: `pilot_local_eddsa` — private key on disk
- **Readiness**: `pilot_ready` (truthfully marked in `readiness.yaml`)

### Production integration

Implement `SigningKeyBackend.external_managed` by wiring one of:

**AWS KMS**:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import boto3

class AwsKmsSigner:
    def __init__(self, key_id: str):
        self.kms = boto3.client("kms")
        self.key_id = key_id

    def sign(self, message: bytes) -> bytes:
        response = self.kms.sign(
            KeyId=self.key_id,
            Message=message,
            SigningAlgorithm="ED25519",
        )
        return response["Signature"]

    def verify(self, message: bytes, signature: bytes) -> bool:
        # KMS does not verify; use the public key locally.
        ...
```

**GCP KMS**: Use `google-cloud-kms` with `CryptoKeyVersion` + `asymmetricSign`.

**Azure Key Vault**: Use `azure-keyvault-keys` with `KeyClient.sign()`.

**HSM (PKCS#11)**: Use `python-pkcs11` to sign via a hardware HSM.

### What to set
- `ACTENON_SIGNING_BACKEND=external_managed`
- `ACTENON_KMS_ENDPOINT=<your-kms-endpoint>`
- `ACTENON_KMS_KEY_ID=<your-key-id>`
- Remove `ACTENON_ALLOW_PILOT_LOCAL_EDDSA_IN_PRODUCTION`

### What NOT to do
- Do NOT set `ACTENON_ALLOW_PILOT_LOCAL_EDDSA_IN_PRODUCTION=1` in production.
  This flag exists for emergency/demo use only.

---

## 2. Credential master key: Vault / KMS

### Current state
- **Encryption**: AES-256-GCM with per-tenant derived keys
- **Master key**: Supplied by deployment via `ACTENON_CREDENTIAL_MASTER_KEY` env var
- **Readiness**: `production_ready` (the encryption is real; the master-key
  management is the deployment's responsibility)

### Production integration

Supply the master key from a secrets manager:

**HashiCorp Vault**:
```bash
export ACTENON_CREDENTIAL_MASTER_KEY=$(vault kv get -field=master_key secret/actenon/credentials)
```

**AWS Secrets Manager**:
```bash
export ACTENON_CREDENTIAL_MASTER_KEY=$(aws secretsmanager get-secret-value --secret-id actenon/credential-master-key --query SecretString --output text)
```

**GCP Secret Manager**:
```bash
export ACTENON_CREDENTIAL_MASTER_KEY=$(gcloud secrets versions access latest --secret=actenon-credential-master-key)
```

### What to do
- Rotate the master key periodically (re-encrypt all credentials with the new key)
- The `EncryptedCredentialStore` supports `key_version` for rotation
- Audit all credential access via the `credential_access_audit` table

---

## 3. Evidence storage: S3 / GCS

### Current state
- **Storage**: Local filesystem (`evidence_storage_root` setting)
- **Readiness**: `pilot_ready` (truthfully marked — NOT durable production storage)

### Production integration

Replace the local filesystem backend with an S3/GCS backend:

**AWS S3**:
```python
import boto3

class S3EvidenceStore:
    def __init__(self, bucket: str, prefix: str = "evidence/"):
        self.s3 = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix

    def store(self, key: str, data: bytes) -> str:
        self.s3.put_object(Bucket=self.bucket, Key=f"{self.prefix}{key}", Body=data)
        return f"s3://{self.bucket}/{self.prefix}{key}"
```

**GCS**: Use `google-cloud-storage` with `Blob.upload_from_string()`.

### What to set
- `ACTENON_EVIDENCE_BACKEND=s3`
- `ACTENON_EVIDENCE_S3_BUCKET=<your-bucket>`
- Configure S3 lifecycle policies for retention + transition to Glacier

---

## 4. Async execution: Celery / RQ

### Current state
- **Execution**: Synchronous (`ExecutionWorker.run_job()` blocks)
- **Readiness**: `production_ready` (the worker is correct; async is an
  architecture choice for higher throughput)

### Production integration (optional — only if throughput requires it)

Wrap `ExecutionWorker.run_job()` in a Celery task:

```python
from celery import Celery

app = Celery("actenon", broker="redis://localhost:6379")

@app.task(bind=True, max_retries=3)
def execute_job(self, job_id: str):
    from app.services.execution_worker import ExecutionWorker
    with database.session() as session:
        worker = ExecutionWorker(session)
        worker.run_job(job_id, executor)
```

### When to do this
- Only when you have >10 concurrent executions
- The synchronous worker is correct for pilot/early-stage workloads
- The durable job table ensures no work is lost even without Celery

---

## 5. OIDC authentication

### Current state
- **Auth**: Bearer token (service-to-service)
- **Readiness**: `stub` for OIDC (truthfully marked)

### Production integration

Wire an external IdP (Auth0, Okta, Keycloak) by implementing
`AuthService.authenticate_bearer_token()` to validate JWTs from the IdP:

```python
from jose import jwt

def authenticate_bearer_token(self, token: str) -> AuthenticatedSession:
    # Validate JWT from Auth0/Okta/Keycloak
    claims = jwt.decode(
        token,
        key=self.idp_jwks,
        algorithms=["RS256"],
        audience=self.audience,
    )
    # Map IdP claims to tenant_ids + permissions
    ...
```

### What to set
- `ACTENON_AUTH_MODE=external_managed_bearer`
- `ACTENON_IDP_JWKS_URL=<your-idp-jwks-url>`
- `ACTENON_IDP_AUDIENCE=<your-audience>`

---

## 6. Multi-region deployment

### Current state
- **Deployment**: Single-region
- **Readiness**: Not applicable (infrastructure concern)

### Production path
- Deploy Cloud in 2+ regions with read replicas
- Use a global load balancer (AWS ALB, GCP LB) for failover
- Use multi-region Postgres (AWS Aurora Global, CockroachDB, or Patroni)
- The application code is stateless — multi-region is purely infra

---

## 7. Backup / restore

### Current state
- **Backups**: Manual (`pg_dump`)
- **Readiness**: Not applicable (operations concern)

### Production path
- Use managed database backups (AWS RDS automated backups, GCP Cloud SQL)
- Configure point-in-time recovery
- Test restore procedures quarterly
- Back up the evidence storage (S3 cross-region replication)

---

## Summary: what's code vs what's infra

| Component | Code (done) | Infra (deployment) |
|---|---|---|
| Credential encryption | ✅ AES-256-GCM | Master key from Vault/KMS |
| Signing | ✅ Ed25519 + backend abstraction | KMS/HSM integration |
| Execution worker | ✅ Durable jobs + retries | Celery (optional) |
| Evidence storage | ✅ Local backend | S3/GCS backend |
| Auth | ✅ Bearer token + permissions | OIDC IdP integration |
| RLS | ✅ Postgres policies | Multi-region Postgres |
| Backups | ✅ `pg_dump` works | Managed backups |
